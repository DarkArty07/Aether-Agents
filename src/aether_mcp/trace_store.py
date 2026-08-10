"""Transactional SQLite trace store for M2.4 operation authority and receipts."""

from __future__ import annotations

import hashlib
import json
import os
import re
import sqlite3
import uuid
from pathlib import Path
from typing import Any, NoReturn

_SCHEMA_VERSION = 2
_DIGEST_RE = re.compile(r"^[0-9a-f]{64}$")
_TOKEN_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:/-]{0,511}$")
_PHASES = {"INTENT", "RECEIPT", "RECONCILE"}
_OUTCOMES = {"PREPARED", "SUCCEEDED", "FAILED", "UNKNOWN", "NOT_APPLIED"}
_ZERO_DIGEST = "0" * 64
_SECRET_RE = re.compile(
    r"(?i)(authorization\s*:\s*bearer\s+\S+|\b(?:ghp|github_pat)_[A-Za-z0-9_]{20,}\b|\bsk-[A-Za-z0-9_-]{16,}\b)"
)
_RECORD_FIELDS = (
    "schema_version",
    "sequence",
    "previous_hash",
    "record_hash",
    "operation_id",
    "project_id",
    "capability",
    "phase",
    "outcome",
    "request_digest",
    "response_digest",
    "provider_request_id",
    "resource_ids",
    "error_code",
)


class StoreError(RuntimeError):
    """Stable trace-store failure."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


def _fail(code: str, message: str) -> NoReturn:
    raise StoreError(code, message)


def _canonical(value: Any) -> bytes:
    try:
        return json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
            allow_nan=False,
        ).encode()
    except (TypeError, ValueError):
        _fail("TRACE_INTEGRITY_FAILURE", "Trace payload is not canonical JSON")


def _validate_uuid(value: str) -> None:
    try:
        parsed = uuid.UUID(value)
    except (TypeError, ValueError, AttributeError):
        _fail("TRACE_INTEGRITY_FAILURE", "Trace identity is invalid")
    if str(parsed) != value:
        _fail("TRACE_INTEGRITY_FAILURE", "Trace identity is not canonical")


def _record_hash(record: dict[str, Any]) -> str:
    payload = {key: value for key, value in record.items() if key != "record_hash"}
    return hashlib.sha256(_canonical(payload)).hexdigest()


def _is_busy(exc: sqlite3.Error) -> bool:
    return getattr(exc, "sqlite_errorcode", None) in {sqlite3.SQLITE_BUSY, sqlite3.SQLITE_LOCKED} or "locked" in str(exc).lower()


class TraceStore:
    """Append-only event authority; it never mirrors Orca Run/Task state."""

    def __init__(self, root: Path) -> None:
        if root.is_symlink():
            _fail("TRACE_INTEGRITY_FAILURE", "Trace root cannot be a symlink")
        root.mkdir(mode=0o700, parents=True, exist_ok=True)
        os.chmod(root, 0o700)
        self.root = root.resolve(strict=True)
        self.path = self.root / "trace.sqlite3"
        self._migrate()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.path, timeout=0.25, isolation_level=None)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA busy_timeout = 250")
        connection.execute("PRAGMA foreign_keys = ON")
        return connection

    def _migrate(self) -> None:
        try:
            with self._connect() as connection:
                connection.execute("BEGIN EXCLUSIVE")
                version = int(connection.execute("PRAGMA user_version").fetchone()[0])
                if version > _SCHEMA_VERSION:
                    _fail("TRACE_INTEGRITY_FAILURE", "Trace schema is newer than this build")
                if version == 0:
                    connection.execute(
                        """CREATE TABLE events (
                            sequence INTEGER PRIMARY KEY AUTOINCREMENT,
                            schema_version INTEGER NOT NULL,
                            previous_hash TEXT NOT NULL,
                            record_hash TEXT NOT NULL,
                            operation_id TEXT NOT NULL,
                            project_id TEXT NOT NULL,
                            capability TEXT NOT NULL,
                            phase TEXT NOT NULL,
                            outcome TEXT NOT NULL,
                            request_digest TEXT NOT NULL,
                            response_digest TEXT,
                            provider_request_id TEXT,
                            resource_ids TEXT NOT NULL,
                            error_code TEXT
                        )"""
                    )
                    connection.execute("CREATE INDEX events_operation_idx ON events(operation_id, sequence)")
                    connection.execute("CREATE UNIQUE INDEX events_intent_idx ON events(operation_id) WHERE phase='INTENT'")
                if version <= 1:
                    connection.execute(
                        """CREATE TABLE semantic_events (
                            sequence INTEGER PRIMARY KEY AUTOINCREMENT,
                            project_id TEXT NOT NULL,
                            run_id TEXT,
                            operation_id TEXT NOT NULL,
                            kind TEXT NOT NULL,
                            payload_json TEXT NOT NULL,
                            previous_hash TEXT NOT NULL,
                            record_hash TEXT NOT NULL
                        )"""
                    )
                    connection.execute(
                        "CREATE INDEX semantic_project_idx ON semantic_events(project_id, run_id, sequence)"
                    )
                connection.execute(f"PRAGMA user_version = {_SCHEMA_VERSION}")
                connection.execute("COMMIT")
                connection.execute("PRAGMA journal_mode = WAL")
                connection.execute("PRAGMA synchronous = FULL")
            os.chmod(self.path, 0o600)
        except StoreError:
            raise
        except sqlite3.Error as exc:
            if _is_busy(exc):
                _fail("TRACE_STORE_BUSY", "Trace store is busy")
            _fail("TRACE_INTEGRITY_FAILURE", "Trace store migration failed")

    @property
    def schema_version(self) -> int:
        try:
            with self._connect() as connection:
                return int(connection.execute("PRAGMA user_version").fetchone()[0])
        except sqlite3.Error as exc:
            if _is_busy(exc):
                _fail("TRACE_STORE_BUSY", "Trace store is busy")
            _fail("TRACE_INTEGRITY_FAILURE", "Trace schema cannot be read")

    @staticmethod
    def _row(row: sqlite3.Row) -> dict[str, Any]:
        record = {key: row[key] for key in _RECORD_FIELDS if key != "resource_ids"}
        try:
            resources = json.loads(row["resource_ids"])
        except (TypeError, json.JSONDecodeError):
            _fail("TRACE_INTEGRITY_FAILURE", "Trace resource identities are malformed")
        record["resource_ids"] = resources
        return record

    @staticmethod
    def _validate_common(
        *,
        operation_id: str,
        project_id: str,
        capability: str,
        request_digest: str,
    ) -> None:
        _validate_uuid(operation_id)
        _validate_uuid(project_id)
        if not isinstance(capability, str) or _TOKEN_RE.fullmatch(capability) is None:
            _fail("TRACE_INTEGRITY_FAILURE", "Trace capability is invalid")
        if not isinstance(request_digest, str) or _DIGEST_RE.fullmatch(request_digest) is None:
            _fail("TRACE_INTEGRITY_FAILURE", "Trace request digest is invalid")

    @staticmethod
    def _make_record(
        *,
        sequence: int,
        previous_hash: str,
        operation_id: str,
        project_id: str,
        capability: str,
        phase: str,
        outcome: str,
        request_digest: str,
        response_digest: str | None,
        provider_request_id: str | None,
        resource_ids: tuple[str, ...],
        error_code: str | None,
    ) -> dict[str, Any]:
        record: dict[str, Any] = {
            "schema_version": _SCHEMA_VERSION,
            "sequence": sequence,
            "previous_hash": previous_hash,
            "record_hash": "",
            "operation_id": operation_id,
            "project_id": project_id,
            "capability": capability,
            "phase": phase,
            "outcome": outcome,
            "request_digest": request_digest,
            "response_digest": response_digest,
            "provider_request_id": provider_request_id,
            "resource_ids": list(resource_ids),
            "error_code": error_code,
        }
        record["record_hash"] = _record_hash(record)
        return record

    @staticmethod
    def _insert(connection: sqlite3.Connection, record: dict[str, Any]) -> None:
        connection.execute(
            """INSERT INTO events (
                sequence, schema_version, previous_hash, record_hash, operation_id,
                project_id, capability, phase, outcome, request_digest,
                response_digest, provider_request_id, resource_ids, error_code
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                record["sequence"],
                record["schema_version"],
                record["previous_hash"],
                record["record_hash"],
                record["operation_id"],
                record["project_id"],
                record["capability"],
                record["phase"],
                record["outcome"],
                record["request_digest"],
                record["response_digest"],
                record["provider_request_id"],
                json.dumps(record["resource_ids"], separators=(",", ":")),
                record["error_code"],
            ),
        )

    def prepare_intent(
        self,
        *,
        operation_id: str,
        project_id: str,
        capability: str,
        request_digest: str,
    ) -> tuple[bool, dict[str, Any]]:
        self._validate_common(
            operation_id=operation_id,
            project_id=project_id,
            capability=capability,
            request_digest=request_digest,
        )
        try:
            with self._connect() as connection:
                connection.execute("BEGIN IMMEDIATE")
                existing = connection.execute(
                    "SELECT * FROM events WHERE operation_id=? ORDER BY sequence", (operation_id,)
                ).fetchall()
                if existing:
                    first = self._row(existing[0])
                    if (
                        first["project_id"] != project_id
                        or first["capability"] != capability
                        or first["request_digest"] != request_digest
                    ):
                        _fail("IDEMPOTENCY_CONFLICT", "Operation identity has different canonical input")
                    latest = self._row(existing[-1])
                    connection.execute("COMMIT")
                    return False, latest
                tail = connection.execute("SELECT sequence, record_hash FROM events ORDER BY sequence DESC LIMIT 1").fetchone()
                sequence = 1 if tail is None else int(tail["sequence"]) + 1
                previous = _ZERO_DIGEST if tail is None else str(tail["record_hash"])
                record = self._make_record(
                    sequence=sequence,
                    previous_hash=previous,
                    operation_id=operation_id,
                    project_id=project_id,
                    capability=capability,
                    phase="INTENT",
                    outcome="PREPARED",
                    request_digest=request_digest,
                    response_digest=None,
                    provider_request_id=None,
                    resource_ids=(),
                    error_code=None,
                )
                self._insert(connection, record)
                connection.execute("COMMIT")
                return True, record
        except StoreError:
            raise
        except sqlite3.Error as exc:
            if _is_busy(exc):
                _fail("TRACE_STORE_BUSY", "Trace store is busy")
            _fail("TRACE_INTEGRITY_FAILURE", "Trace intent could not be committed")

    def append_event(
        self,
        *,
        operation_id: str,
        project_id: str,
        capability: str,
        phase: str,
        outcome: str,
        request_digest: str,
        response_digest: str | None = None,
        provider_request_id: str | None = None,
        resource_ids: tuple[str, ...] = (),
        error_code: str | None = None,
    ) -> dict[str, Any]:
        self._validate_common(
            operation_id=operation_id,
            project_id=project_id,
            capability=capability,
            request_digest=request_digest,
        )
        if phase not in _PHASES - {"INTENT"} or outcome not in _OUTCOMES:
            _fail("TRACE_INTEGRITY_FAILURE", "Trace phase or outcome is invalid")
        if response_digest is not None and _DIGEST_RE.fullmatch(response_digest) is None:
            _fail("TRACE_INTEGRITY_FAILURE", "Trace response digest is invalid")
        if provider_request_id is not None and _TOKEN_RE.fullmatch(provider_request_id) is None:
            _fail("TRACE_INTEGRITY_FAILURE", "Provider request identity is invalid")
        if len(resource_ids) > 64 or any(_TOKEN_RE.fullmatch(value) is None for value in resource_ids):
            _fail("TRACE_INTEGRITY_FAILURE", "Resource identity is invalid")
        if error_code is not None and _TOKEN_RE.fullmatch(error_code) is None:
            _fail("TRACE_INTEGRITY_FAILURE", "Trace error code is invalid")
        try:
            with self._connect() as connection:
                connection.execute("BEGIN IMMEDIATE")
                intent = connection.execute(
                    "SELECT * FROM events WHERE operation_id=? AND phase='INTENT'", (operation_id,)
                ).fetchone()
                if intent is None:
                    _fail("TRACE_INTEGRITY_FAILURE", "Receipt has no durable intent")
                first = self._row(intent)
                if (
                    first["project_id"] != project_id
                    or first["capability"] != capability
                    or first["request_digest"] != request_digest
                ):
                    _fail("IDEMPOTENCY_CONFLICT", "Receipt does not match its intent")
                tail = connection.execute("SELECT sequence, record_hash FROM events ORDER BY sequence DESC LIMIT 1").fetchone()
                record = self._make_record(
                    sequence=int(tail["sequence"]) + 1,
                    previous_hash=str(tail["record_hash"]),
                    operation_id=operation_id,
                    project_id=project_id,
                    capability=capability,
                    phase=phase,
                    outcome=outcome,
                    request_digest=request_digest,
                    response_digest=response_digest,
                    provider_request_id=provider_request_id,
                    resource_ids=resource_ids,
                    error_code=error_code,
                )
                self._insert(connection, record)
                connection.execute("COMMIT")
                return record
        except StoreError:
            raise
        except sqlite3.Error as exc:
            if _is_busy(exc):
                _fail("TRACE_STORE_BUSY", "Trace store is busy")
            _fail("TRACE_INTEGRITY_FAILURE", "Trace receipt could not be committed")

    def append_reconcile_once(
        self,
        *,
        operation_id: str,
        project_id: str,
        capability: str,
        outcome: str,
        request_digest: str,
        response_digest: str | None = None,
        provider_request_id: str | None = None,
        resource_ids: tuple[str, ...] = (),
        error_code: str | None = None,
    ) -> tuple[bool, dict[str, Any]]:
        """CAS one terminal reconciliation result under the journal transaction."""

        self._validate_common(
            operation_id=operation_id,
            project_id=project_id,
            capability=capability,
            request_digest=request_digest,
        )
        if outcome not in _OUTCOMES or outcome == "PREPARED":
            _fail("TRACE_INTEGRITY_FAILURE", "Reconciliation outcome is invalid")
        if response_digest is not None and _DIGEST_RE.fullmatch(response_digest) is None:
            _fail("TRACE_INTEGRITY_FAILURE", "Trace response digest is invalid")
        if provider_request_id is not None and _TOKEN_RE.fullmatch(provider_request_id) is None:
            _fail("TRACE_INTEGRITY_FAILURE", "Provider request identity is invalid")
        if len(resource_ids) > 64 or any(_TOKEN_RE.fullmatch(value) is None for value in resource_ids):
            _fail("TRACE_INTEGRITY_FAILURE", "Resource identity is invalid")
        if error_code is not None and _TOKEN_RE.fullmatch(error_code) is None:
            _fail("TRACE_INTEGRITY_FAILURE", "Trace error code is invalid")
        try:
            with self._connect() as connection:
                connection.execute("BEGIN IMMEDIATE")
                rows = connection.execute(
                    "SELECT * FROM events WHERE operation_id=? ORDER BY sequence",
                    (operation_id,),
                ).fetchall()
                if not rows:
                    _fail("TRACE_INTEGRITY_FAILURE", "Reconciliation has no durable intent")
                first = self._row(rows[0])
                if (
                    first["project_id"] != project_id
                    or first["capability"] != capability
                    or first["request_digest"] != request_digest
                ):
                    _fail("IDEMPOTENCY_CONFLICT", "Reconciliation does not match its intent")
                latest = self._row(rows[-1])
                if latest["outcome"] in {"SUCCEEDED", "FAILED", "NOT_APPLIED"}:
                    connection.execute("COMMIT")
                    return False, latest
                tail = connection.execute(
                    "SELECT sequence, record_hash FROM events ORDER BY sequence DESC LIMIT 1"
                ).fetchone()
                record = self._make_record(
                    sequence=int(tail["sequence"]) + 1,
                    previous_hash=str(tail["record_hash"]),
                    operation_id=operation_id,
                    project_id=project_id,
                    capability=capability,
                    phase="RECONCILE",
                    outcome=outcome,
                    request_digest=request_digest,
                    response_digest=response_digest,
                    provider_request_id=provider_request_id,
                    resource_ids=resource_ids,
                    error_code=error_code,
                )
                self._insert(connection, record)
                connection.execute("COMMIT")
                return True, record
        except StoreError:
            raise
        except sqlite3.Error as exc:
            if _is_busy(exc):
                _fail("TRACE_STORE_BUSY", "Trace store is busy")
            _fail("TRACE_INTEGRITY_FAILURE", "Trace reconciliation could not be committed")

    def records(self) -> list[dict[str, Any]]:
        try:
            with self._connect() as connection:
                rows = connection.execute("SELECT * FROM events ORDER BY sequence").fetchall()
            return [self._row(row) for row in rows]
        except StoreError:
            raise
        except sqlite3.Error as exc:
            if _is_busy(exc):
                _fail("TRACE_STORE_BUSY", "Trace store is busy")
            _fail("TRACE_INTEGRITY_FAILURE", "Trace records cannot be read")

    def records_for(self, operation_id: str) -> list[dict[str, Any]]:
        _validate_uuid(operation_id)
        try:
            with self._connect() as connection:
                rows = connection.execute(
                    "SELECT * FROM events WHERE operation_id=? ORDER BY sequence",
                    (operation_id,),
                ).fetchall()
            return [self._row(row) for row in rows]
        except StoreError:
            raise
        except sqlite3.Error as exc:
            if _is_busy(exc):
                _fail("TRACE_STORE_BUSY", "Trace store is busy")
            _fail("TRACE_INTEGRITY_FAILURE", "Trace records cannot be read")

    def verify_integrity(self) -> dict[str, Any]:
        previous = _ZERO_DIGEST
        records = self.records()
        for expected, record in enumerate(records, start=1):
            if set(record) != set(_RECORD_FIELDS):
                _fail("TRACE_INTEGRITY_FAILURE", "Trace record shape is invalid")
            if record["sequence"] != expected or record["schema_version"] != _SCHEMA_VERSION:
                _fail("TRACE_INTEGRITY_FAILURE", "Trace sequence is invalid")
            if record["previous_hash"] != previous or record["record_hash"] != _record_hash(record):
                _fail("TRACE_INTEGRITY_FAILURE", "Trace hash chain is invalid")
            previous = record["record_hash"]
        return {"events": len(records), "head": previous, "schema_version": self.schema_version}

    @staticmethod
    def _semantic_record(row: sqlite3.Row) -> dict[str, Any]:
        try:
            payload = json.loads(row["payload_json"])
        except (TypeError, json.JSONDecodeError):
            _fail("TRACE_INTEGRITY_FAILURE", "Semantic payload is malformed")
        return {
            "sequence": row["sequence"],
            "project_id": row["project_id"],
            "run_id": row["run_id"],
            "operation_id": row["operation_id"],
            "kind": row["kind"],
            "payload": payload,
            "previous_hash": row["previous_hash"],
            "record_hash": row["record_hash"],
        }

    @staticmethod
    def _semantic_hash(record: dict[str, Any]) -> str:
        payload = {key: value for key, value in record.items() if key != "record_hash"}
        return hashlib.sha256(_canonical(payload)).hexdigest()

    def append_semantic_event(
        self,
        *,
        operation_id: str,
        project_id: str,
        run_id: str | None,
        kind: str,
        payload: dict[str, Any],
    ) -> dict[str, Any]:
        _validate_uuid(operation_id)
        _validate_uuid(project_id)
        if run_id is not None:
            _validate_uuid(run_id)
        if kind not in {"DECISION", "EVIDENCE"} or not isinstance(payload, dict):
            _fail("TRACE_INTEGRITY_FAILURE", "Semantic event shape is invalid")
        payload_bytes = _canonical(payload)
        if len(payload_bytes) > 65_536 or _SECRET_RE.search(payload_bytes.decode("ascii")):
            _fail("PRIVACY_POLICY_VIOLATION", "Semantic event is oversized or secret-shaped")
        try:
            with self._connect() as connection:
                connection.execute("BEGIN IMMEDIATE")
                tail = connection.execute(
                    "SELECT sequence, record_hash FROM semantic_events ORDER BY sequence DESC LIMIT 1"
                ).fetchone()
                sequence = 1 if tail is None else int(tail["sequence"]) + 1
                previous = _ZERO_DIGEST if tail is None else str(tail["record_hash"])
                record = {
                    "sequence": sequence,
                    "project_id": project_id,
                    "run_id": run_id,
                    "operation_id": operation_id,
                    "kind": kind,
                    "payload": payload,
                    "previous_hash": previous,
                    "record_hash": "",
                }
                record["record_hash"] = self._semantic_hash(record)
                connection.execute(
                    """INSERT INTO semantic_events (
                        sequence, project_id, run_id, operation_id, kind,
                        payload_json, previous_hash, record_hash
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                    (
                        sequence,
                        project_id,
                        run_id,
                        operation_id,
                        kind,
                        payload_bytes.decode("ascii"),
                        previous,
                        record["record_hash"],
                    ),
                )
                connection.execute("COMMIT")
                return record
        except StoreError:
            raise
        except sqlite3.Error as exc:
            if _is_busy(exc):
                _fail("TRACE_STORE_BUSY", "Trace store is busy")
            _fail("TRACE_INTEGRITY_FAILURE", "Semantic event could not be committed")

    def query_semantic(
        self,
        *,
        project_id: str,
        run_id: str | None,
        kinds: tuple[str, ...],
        cursor: str | None,
        limit: int,
    ) -> dict[str, Any]:
        _validate_uuid(project_id)
        if run_id is not None:
            _validate_uuid(run_id)
        if any(kind not in {"DECISION", "EVIDENCE"} for kind in kinds):
            _fail("TRACE_INTEGRITY_FAILURE", "Semantic event filter is invalid")
        if not isinstance(limit, int) or not 1 <= limit <= 200:
            _fail("TRACE_INTEGRITY_FAILURE", "Semantic query limit is invalid")
        if cursor is None:
            after = 0
        elif isinstance(cursor, str) and cursor.isascii() and cursor.isdigit() and len(cursor) <= 20:
            after = int(cursor)
        else:
            _fail("TRACE_INTEGRITY_FAILURE", "Semantic query cursor is invalid")
        clauses = ["project_id=?", "sequence>?"]
        parameters: list[Any] = [project_id, after]
        if run_id is not None:
            clauses.append("run_id=?")
            parameters.append(run_id)
        if kinds:
            clauses.append(f"kind IN ({','.join('?' for _ in kinds)})")
            parameters.extend(kinds)
        parameters.append(limit + 1)
        try:
            with self._connect() as connection:
                rows = connection.execute(
                    f"SELECT * FROM semantic_events WHERE {' AND '.join(clauses)} ORDER BY sequence LIMIT ?",
                    parameters,
                ).fetchall()
        except sqlite3.Error as exc:
            if _is_busy(exc):
                _fail("TRACE_STORE_BUSY", "Trace store is busy")
            _fail("TRACE_INTEGRITY_FAILURE", "Semantic events cannot be queried")
        has_more = len(rows) > limit
        selected = rows[:limit]
        events = [self._semantic_record(row) for row in selected]
        next_cursor = str(events[-1]["sequence"]) if has_more and events else None
        return {"events": events, "next_cursor": next_cursor}

    def verify_semantic_integrity(self) -> dict[str, Any]:
        try:
            with self._connect() as connection:
                rows = connection.execute("SELECT * FROM semantic_events ORDER BY sequence").fetchall()
        except sqlite3.Error as exc:
            if _is_busy(exc):
                _fail("TRACE_STORE_BUSY", "Trace store is busy")
            _fail("TRACE_INTEGRITY_FAILURE", "Semantic events cannot be read")
        previous = _ZERO_DIGEST
        for expected, row in enumerate(rows, start=1):
            record = self._semantic_record(row)
            if (
                record["sequence"] != expected
                or record["previous_hash"] != previous
                or record["record_hash"] != self._semantic_hash(record)
            ):
                _fail("TRACE_INTEGRITY_FAILURE", "Semantic trace hash chain is invalid")
            previous = record["record_hash"]
        return {"events": len(rows), "head": previous, "schema_version": self.schema_version}
