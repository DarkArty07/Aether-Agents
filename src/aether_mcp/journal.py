"""Append-only, hash-chained operation journal for the default-off Orca adapter."""

from __future__ import annotations

import fcntl
import hashlib
import json
import os
import re
import stat
from pathlib import Path
from typing import Any, NoReturn

DIGEST_RE = re.compile(r"^[0-9a-f]{64}$")
UUID_RE = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$")
TOKEN_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:/-]{0,511}$")
ZERO_DIGEST = "0" * 64
PHASES = frozenset({"INTENT", "RECEIPT", "RECONCILE"})
OUTCOMES = frozenset({"PREPARED", "SUCCEEDED", "FAILED", "UNKNOWN", "NOT_APPLIED"})
RECORD_FIELDS = frozenset(
    {
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
    }
)


class JournalError(ValueError):
    """Stable operation-journal failure."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


def _fail(code: str, message: str) -> NoReturn:
    raise JournalError(code, message)


def _canonical(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("utf-8")


def _record_hash(record: dict[str, Any]) -> str:
    payload = {key: value for key, value in record.items() if key != "record_hash"}
    return hashlib.sha256(_canonical(payload)).hexdigest()


def _safe_optional_token(value: str | None, *, field: str) -> None:
    if value is None:
        return
    if TOKEN_RE.fullmatch(value) is None:
        _fail("ERR_JOURNAL_RECORD", f"Journal {field} is invalid")


def _validate_record(record: Any, *, sequence: int, previous_hash: str) -> dict[str, Any]:
    if not isinstance(record, dict) or set(record) != RECORD_FIELDS:
        _fail("ERR_JOURNAL_TAMPERED", "Journal record shape is invalid")
    if record["schema_version"] != 1 or record["sequence"] != sequence:
        _fail("ERR_JOURNAL_TAMPERED", "Journal sequence is invalid")
    if record["previous_hash"] != previous_hash:
        _fail("ERR_JOURNAL_TAMPERED", "Journal hash-chain predecessor is invalid")
    if not isinstance(record["record_hash"], str) or record["record_hash"] != _record_hash(record):
        _fail("ERR_JOURNAL_TAMPERED", "Journal record hash is invalid")
    if not isinstance(record["operation_id"], str) or UUID_RE.fullmatch(record["operation_id"]) is None:
        _fail("ERR_JOURNAL_TAMPERED", "Journal operation identity is invalid")
    if not isinstance(record["project_id"], str) or UUID_RE.fullmatch(record["project_id"]) is None:
        _fail("ERR_JOURNAL_TAMPERED", "Journal project identity is invalid")
    if not isinstance(record["capability"], str) or TOKEN_RE.fullmatch(record["capability"]) is None:
        _fail("ERR_JOURNAL_TAMPERED", "Journal capability is invalid")
    if record["phase"] not in PHASES or record["outcome"] not in OUTCOMES:
        _fail("ERR_JOURNAL_TAMPERED", "Journal phase or outcome is invalid")
    for field in ("request_digest", "previous_hash", "record_hash"):
        if not isinstance(record[field], str) or DIGEST_RE.fullmatch(record[field]) is None:
            _fail("ERR_JOURNAL_TAMPERED", f"Journal {field} is invalid")
    response_digest = record["response_digest"]
    if response_digest is not None and (
        not isinstance(response_digest, str) or DIGEST_RE.fullmatch(response_digest) is None
    ):
        _fail("ERR_JOURNAL_TAMPERED", "Journal response digest is invalid")
    try:
        _safe_optional_token(record["provider_request_id"], field="provider_request_id")
        _safe_optional_token(record["error_code"], field="error_code")
    except JournalError:
        _fail("ERR_JOURNAL_TAMPERED", "Journal optional token is invalid")
    resource_ids = record["resource_ids"]
    if not isinstance(resource_ids, list) or len(resource_ids) > 64:
        _fail("ERR_JOURNAL_TAMPERED", "Journal resource identities are invalid")
    for resource_id in resource_ids:
        if not isinstance(resource_id, str) or TOKEN_RE.fullmatch(resource_id) is None:
            _fail("ERR_JOURNAL_TAMPERED", "Journal resource identity is invalid")
    return record


def _decode_records(raw: bytes) -> list[dict[str, Any]]:
    if not raw:
        return []
    if not raw.endswith(b"\n"):
        _fail("ERR_JOURNAL_TAMPERED", "Journal does not end on a record boundary")
    records: list[dict[str, Any]] = []
    previous = ZERO_DIGEST
    for sequence, line in enumerate(raw.splitlines(), start=1):
        try:
            value = json.loads(line.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            _fail("ERR_JOURNAL_TAMPERED", "Journal contains malformed JSON")
        record = _validate_record(value, sequence=sequence, previous_hash=previous)
        records.append(record)
        previous = record["record_hash"]
    return records


class OperationJournal:
    """One local append-only journal; no runtime Run/Task state is mirrored here."""

    def __init__(self, root: Path) -> None:
        self.root = root
        self.path = root / "operations.jsonl"
        if root.is_symlink():
            _fail("ERR_JOURNAL_SCOPE", "Journal root cannot be a symlink")
        if root.exists() and not root.is_dir():
            _fail("ERR_JOURNAL_SCOPE", "Journal root is not a directory")
        root.mkdir(mode=0o700, parents=True, exist_ok=True)
        if self.path.is_symlink():
            _fail("ERR_JOURNAL_SCOPE", "Journal file cannot be a symlink")
        if not self.path.exists():
            descriptor = os.open(self.path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
            os.close(descriptor)
        info = self.path.stat(follow_symlinks=False)
        if not stat.S_ISREG(info.st_mode):
            _fail("ERR_JOURNAL_SCOPE", "Journal path is not a regular file")

    def records(self) -> list[dict[str, Any]]:
        with self.path.open("rb") as stream:
            fcntl.flock(stream.fileno(), fcntl.LOCK_SH)
            try:
                return _decode_records(stream.read())
            finally:
                fcntl.flock(stream.fileno(), fcntl.LOCK_UN)

    def records_for(self, operation_id: str) -> list[dict[str, Any]]:
        return [record for record in self.records() if record["operation_id"] == operation_id]

    @staticmethod
    def _make_record(
        records: list[dict[str, Any]],
        *,
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
        sequence = len(records) + 1
        previous_hash = records[-1]["record_hash"] if records else ZERO_DIGEST
        record: dict[str, Any] = {
            "schema_version": 1,
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
    def _write_record(stream: Any, record: dict[str, Any]) -> None:
        stream.seek(0, os.SEEK_END)
        stream.write(_canonical(record) + b"\n")
        os.fsync(stream.fileno())

    def prepare_intent(
        self,
        *,
        operation_id: str,
        project_id: str,
        capability: str,
        request_digest: str,
    ) -> tuple[bool, dict[str, Any]]:
        """Atomically append one intent or return the existing operation record."""
        if UUID_RE.fullmatch(operation_id) is None or UUID_RE.fullmatch(project_id) is None:
            _fail("ERR_JOURNAL_RECORD", "Journal identity is invalid")
        if TOKEN_RE.fullmatch(capability) is None or DIGEST_RE.fullmatch(request_digest) is None:
            _fail("ERR_JOURNAL_RECORD", "Journal intent classification is invalid")
        with self.path.open("r+b", buffering=0) as stream:
            fcntl.flock(stream.fileno(), fcntl.LOCK_EX)
            try:
                stream.seek(0)
                records = _decode_records(stream.read())
                existing = [record for record in records if record["operation_id"] == operation_id]
                if existing:
                    if existing[0]["request_digest"] != request_digest:
                        _fail("ERR_OPERATION_CONFLICT", "Operation identity has a different request digest")
                    return False, existing[-1]
                record = self._make_record(
                    records,
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
                self._write_record(stream, record)
                return True, record
            finally:
                fcntl.flock(stream.fileno(), fcntl.LOCK_UN)

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
        if UUID_RE.fullmatch(operation_id) is None or UUID_RE.fullmatch(project_id) is None:
            _fail("ERR_JOURNAL_RECORD", "Journal identity is invalid")
        if TOKEN_RE.fullmatch(capability) is None or phase not in PHASES or outcome not in OUTCOMES:
            _fail("ERR_JOURNAL_RECORD", "Journal event classification is invalid")
        if DIGEST_RE.fullmatch(request_digest) is None:
            _fail("ERR_JOURNAL_RECORD", "Journal request digest is invalid")
        if response_digest is not None and DIGEST_RE.fullmatch(response_digest) is None:
            _fail("ERR_JOURNAL_RECORD", "Journal response digest is invalid")
        _safe_optional_token(provider_request_id, field="provider_request_id")
        _safe_optional_token(error_code, field="error_code")
        if len(resource_ids) > 64 or any(TOKEN_RE.fullmatch(item) is None for item in resource_ids):
            _fail("ERR_JOURNAL_RECORD", "Journal resource identity is invalid")

        with self.path.open("r+b", buffering=0) as stream:
            fcntl.flock(stream.fileno(), fcntl.LOCK_EX)
            try:
                stream.seek(0)
                records = _decode_records(stream.read())
                record = self._make_record(
                    records,
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
                self._write_record(stream, record)
                return record
            finally:
                fcntl.flock(stream.fileno(), fcntl.LOCK_UN)
