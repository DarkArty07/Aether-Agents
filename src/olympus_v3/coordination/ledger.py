"""Default-off authenticated coordination ledger backed by a separate SQLite file.

HMAC helpers are test/integrity helpers only. They do not establish Aether proof of
possession, Olympus binding, key custody, rotation, or revocation (R4).
"""

from __future__ import annotations

import hashlib
import hmac
import json
import os
import re
import sqlite3
import tempfile
import time
import uuid
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
from typing import Any, Callable, Mapping, Protocol

from .contracts import ContractAmendment, ContractState, ExecutionContract
from .projections import ProjectionReducer

_ID = re.compile(r"^[a-z0-9][a-z0-9._:-]{0,127}$")
MAX_EVENT_PAYLOAD_BYTES = 16_384
MAX_ERROR_BYTES = 4_096
MAX_SQLITE_INTEGER = (1 << 63) - 1
_BUDGET_EVENT_KINDS = frozenset(
    {
        "budget.reserved",
        "budget.committed",
        "budget.spent",
        "budget.released",
        "budget.retry_admitted",
        "budget.retry_task",
        "budget.replan_task",
    }
)
_WORKFLOW_EVENT_KINDS = frozenset(
    {
        "run.created",
        "task.created",
        "task.released",
        "task.admitted",
        "task.ready",
        "task.dispatched",
        "attempt.started",
        "session.bound",
        "dispatch.staged",
        "dispatch.unknown",
        "cancel.intent",
        "attempt.orphaned",
        "attempt.superseded",
        "observation.accepted",
        "reconciliation.completed",
        "close.requested",
        "cleanup.receipt.recorded",
        "task.closed",
        "close.failed",
        "close.reconciliation_required",
    }
)
_LIFECYCLE_EVENT_KINDS = frozenset(
    {
        "runtime.terminal.observed",
        "cleanup.requested",
        "cleanup.completed",
        "cleanup.failed",
        "cleanup.unknown",
        "evidence.receipt.recorded",
    }
)
_CLOSURE_LIFECYCLE_KINDS = frozenset({"cleanup.requested", "cleanup.completed", "cleanup.failed", "cleanup.unknown"})
_AUTHORITY_BOUND_EVENT_KINDS = _WORKFLOW_EVENT_KINDS | _BUDGET_EVENT_KINDS | _LIFECYCLE_EVENT_KINDS


class InvalidInputError(ValueError):
    pass


def _valid_identifier(value: Any) -> bool:
    return isinstance(value, str) and value == value.strip() and bool(_ID.fullmatch(value))


def _valid_positive_integer(value: Any, *, now: int = 0) -> bool:
    return (
        isinstance(value, int)
        and not isinstance(value, bool)
        and value > 0
        and now >= 0
        and value <= MAX_SQLITE_INTEGER - now
    )


def _canonical_payload(payload: Any) -> str:
    if not isinstance(payload, Mapping):
        raise InvalidInputError("invalid payload")
    try:
        encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), allow_nan=False)
    except (TypeError, ValueError, OverflowError) as exc:
        raise InvalidInputError("invalid payload") from exc
    if len(encoded.encode()) > MAX_EVENT_PAYLOAD_BYTES:
        raise InvalidInputError("payload exceeds size limit")
    return encoded


class Result(StrEnum):
    APPLIED = "APPLIED"
    DUPLICATE = "DUPLICATE"
    IDEMPOTENCY_CONFLICT = "IDEMPOTENCY_CONFLICT"
    CAS_CONFLICT = "CAS_CONFLICT"
    CONTENDED = "CONTENDED"
    AUTHENTICATION_FAILED = "AUTHENTICATION_FAILED"
    STALE_FENCE = "STALE_FENCE"
    LEASE_EXPIRED = "LEASE_EXPIRED"
    INVALID_SCOPE = "INVALID_SCOPE"
    ANCHOR_UNAVAILABLE = "ANCHOR_UNAVAILABLE"
    ANCHOR_ROLLBACK = "ANCHOR_ROLLBACK"
    INTEGRITY_FAILURE = "INTEGRITY_FAILURE"
    NOT_LEASE_OWNER = "NOT_LEASE_OWNER"
    RETRY_SCHEDULED = "RETRY_SCHEDULED"
    POISON_TERMINATED = "POISON_TERMINATED"
    TRANSPORT_ACKNOWLEDGED = "TRANSPORT_ACKNOWLEDGED"
    PROJECTION_MISMATCH = "PROJECTION_MISMATCH"
    RESTORE_INVALID = "RESTORE_INVALID"
    STALE_AUTHORITY = "STALE_AUTHORITY"
    INVALID_INPUT = "INVALID_INPUT"


class InvalidScopeError(ValueError):
    pass


@dataclass(frozen=True, slots=True)
class StoreScope:
    installation_id: str
    project_id: str

    def __post_init__(self) -> None:
        for value, label in ((self.installation_id, "installation"), (self.project_id, "project")):
            if not isinstance(value, str) or value != value.strip() or not _ID.fullmatch(value):
                raise InvalidScopeError(f"invalid {label}")


@dataclass(frozen=True, slots=True)
class WriterContext:
    scope: StoreScope
    writer_id: str
    key_id: str
    resource: str
    fence: int
    expires_at: int

    def __post_init__(self) -> None:
        if (
            not isinstance(self.scope, StoreScope)
            or not _valid_identifier(self.writer_id)
            or not _valid_identifier(self.key_id)
            or not _valid_identifier(self.resource)
            or isinstance(self.fence, bool)
            or not isinstance(self.fence, int)
            or self.fence <= 0
            or isinstance(self.expires_at, bool)
            or not isinstance(self.expires_at, int)
            or self.expires_at <= 0
        ):
            raise InvalidScopeError("invalid writer context")


@dataclass(frozen=True, slots=True)
class SignedEventDraft:
    scope: StoreScope
    aggregate: str
    kind: str
    payload: Mapping[str, Any]
    writer_id: str
    key_id: str
    resource: str
    fence: int
    proof: str = ""
    expected_version: int = 0
    contract_generation: int | None = None
    revocation_epoch: int | None = None

    def __post_init__(self) -> None:
        optional_integers = (self.contract_generation, self.revocation_epoch)
        if (
            not isinstance(self.scope, StoreScope)
            or not _valid_identifier(self.aggregate)
            or not _valid_identifier(self.kind)
            or not _valid_identifier(self.writer_id)
            or not _valid_identifier(self.key_id)
            or not _valid_identifier(self.resource)
            or not _valid_positive_integer(self.fence)
            or not isinstance(self.proof, str)
            or len(self.proof) > 256
            or not isinstance(self.expected_version, int)
            or isinstance(self.expected_version, bool)
            or self.expected_version < 0
            or any(
                value is not None and (not isinstance(value, int) or isinstance(value, bool) or value < 0)
                for value in optional_integers
            )
        ):
            raise InvalidInputError("invalid signed event draft")
        _canonical_payload(self.payload)

    def canonical(self) -> bytes:
        value = {
            "encoding_version": 1,
            "installation_id": self.scope.installation_id,
            "project_id": self.scope.project_id,
            "aggregate": self.aggregate,
            "kind": self.kind,
            "payload": self.payload,
            "writer_id": self.writer_id,
            "key_id": self.key_id,
            "resource": self.resource,
            "fence": self.fence,
            "expected_version": self.expected_version,
            "contract_generation": self.contract_generation,
            "revocation_epoch": self.revocation_epoch,
        }
        return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()


@dataclass(frozen=True, slots=True)
class LedgerEvent:
    installation_id: str
    project_id: str
    sequence: int
    event_id: str
    server_time: int
    aggregate: str
    version: int
    kind: str
    payload: str
    previous_hash: str
    event_hash: str
    writer_id: str
    key_id: str
    resource: str
    writer_proof: str
    fence: int
    auth_tag: str
    encoding_version: int = 1


@dataclass(frozen=True, slots=True)
class Checkpoint:
    installation_id: str
    project_id: str
    checkpoint_id: str
    encoding_version: int
    sequence: int
    event_hash: str
    projection_digest: str
    key_id: str
    created_at: int
    signature: str


class WriterAuthenticator(Protocol):
    def verify(self, draft: SignedEventDraft, context: WriterContext) -> bool: ...


class IntegritySigner(Protocol):
    key_id: str

    def sign(self, value: bytes) -> str: ...
    def verify(self, value: bytes, signature: str) -> bool: ...


class HMACWriterAuthenticator:
    def __init__(self, keys: Mapping[Any, bytes]):
        self._keys = {
            (key if isinstance(key, tuple) else (key, "default")): bytes(value) for key, value in keys.items()
        }

    def sign(self, draft: SignedEventDraft, context: WriterContext) -> SignedEventDraft:
        key = self._keys.get((context.writer_id, context.key_id))
        if key is None:
            raise ValueError("unknown writer key")
        return SignedEventDraft(
            draft.scope,
            draft.aggregate,
            draft.kind,
            dict(draft.payload),
            draft.writer_id,
            draft.key_id,
            draft.resource,
            draft.fence,
            hmac.new(key, draft.canonical(), hashlib.sha256).hexdigest(),
            draft.expected_version,
            draft.contract_generation,
            draft.revocation_epoch,
        )

    def verify(self, draft: SignedEventDraft, context: WriterContext) -> bool:
        key = self._keys.get((draft.writer_id, draft.key_id))
        return bool(
            key
            and draft.writer_id == context.writer_id
            and draft.key_id == context.key_id
            and hmac.compare_digest(draft.proof, hmac.new(key, draft.canonical(), hashlib.sha256).hexdigest())
        )


class HMACIntegritySigner:
    def __init__(self, key: bytes, key_id: str = "integrity"):
        self._key = bytes(key)
        self.key_id = key_id

    def sign(self, value: bytes) -> str:
        return hmac.new(self._key, value, hashlib.sha256).hexdigest()

    def verify(self, value: bytes, signature: str) -> bool:
        return hmac.compare_digest(self.sign(value), signature)


class TrustedAnchorStore:
    def __init__(self):
        self._anchors: dict[tuple[str, str], tuple[int, str]] = {}

    def get(self, scope: StoreScope) -> tuple[int, str] | None:
        return self._anchors.get((scope.installation_id, scope.project_id))

    def put(self, scope: StoreScope, sequence: int, event_hash: str) -> None:
        current = self.get(scope)
        if current and (sequence < current[0] or (sequence == current[0] and event_hash != current[1])):
            raise ValueError("anchor rollback")
        self._anchors[(scope.installation_id, scope.project_id)] = (sequence, event_hash)


@dataclass(frozen=True, slots=True)
class PreparedRestore:
    artifact: Path
    digest: str
    installation_id: str
    project_id: str
    quiescence_token: str


@dataclass(frozen=True, slots=True)
class AppendResult:
    status: Result
    event: LedgerEvent | None = None


class SQLiteLedger:
    def __init__(
        self,
        path: str | Path,
        scope: StoreScope,
        *,
        writer_authenticator: WriterAuthenticator,
        integrity_signer: IntegritySigner,
        reducer: ProjectionReducer | None = None,
        clock: Callable[[], int] | None = None,
        busy_timeout_ms: int = 250,
    ) -> None:
        if not isinstance(scope, StoreScope):
            raise InvalidScopeError("complete scope required")
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.scope = scope
        self._closed = False
        self.writer_authenticator = writer_authenticator
        self.integrity_signer = integrity_signer
        self.reducer = reducer or ProjectionReducer()
        self.clock = clock or time.time_ns
        self.fault: Callable[[str], None] | None = None
        self.conn = sqlite3.connect(self.path, timeout=busy_timeout_ms / 1000, isolation_level=None)
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("PRAGMA foreign_keys=ON")
        self.conn.execute("PRAGMA journal_mode=WAL")
        self.conn.execute("PRAGMA synchronous=FULL")
        self.conn.execute(f"PRAGMA busy_timeout={int(busy_timeout_ms)}")
        self._schema()
        self._chmod()

    def _chmod(self) -> None:
        for suffix in ("", "-wal", "-shm"):
            try:
                os.chmod(str(self.path) + suffix, 0o600)
            except FileNotFoundError:
                pass

    def _schema(self) -> None:
        self.conn.executescript("""
        CREATE TABLE IF NOT EXISTS events(installation_id TEXT NOT NULL, project_id TEXT NOT NULL, sequence INTEGER NOT NULL,
          event_id TEXT NOT NULL, server_time INTEGER NOT NULL, aggregate TEXT NOT NULL, version INTEGER NOT NULL, kind TEXT NOT NULL,
          payload TEXT NOT NULL, previous_hash TEXT NOT NULL, event_hash TEXT NOT NULL, writer_id TEXT NOT NULL, key_id TEXT NOT NULL,
          resource TEXT NOT NULL, fence INTEGER NOT NULL, writer_proof TEXT NOT NULL, auth_tag TEXT NOT NULL, encoding_version INTEGER NOT NULL DEFAULT 1,
          PRIMARY KEY(installation_id,project_id,sequence), UNIQUE(installation_id,project_id,event_id), UNIQUE(installation_id,project_id,aggregate,version), CHECK(sequence > 0), CHECK(version > 0), CHECK(fence > 0));
        CREATE TABLE IF NOT EXISTS projections(installation_id TEXT NOT NULL, project_id TEXT NOT NULL, aggregate TEXT NOT NULL, version INTEGER NOT NULL,
          value TEXT NOT NULL, reducer_version TEXT NOT NULL, source_sequence INTEGER NOT NULL, source_hash TEXT NOT NULL, PRIMARY KEY(installation_id,project_id,aggregate));
        CREATE TABLE IF NOT EXISTS leases(installation_id TEXT NOT NULL, project_id TEXT NOT NULL, resource TEXT NOT NULL, owner TEXT NOT NULL, epoch INTEGER NOT NULL, expires_at INTEGER NOT NULL, token TEXT NOT NULL, PRIMARY KEY(installation_id,project_id,resource));
        CREATE TABLE IF NOT EXISTS outbox(installation_id TEXT NOT NULL, project_id TEXT NOT NULL, message_id TEXT NOT NULL, event_id TEXT NOT NULL,
          status TEXT NOT NULL CHECK(status IN ('PENDING','LEASED','RETRY_WAIT','SENT','POISON','UNKNOWN')), attempts INTEGER NOT NULL DEFAULT 0, last_error TEXT,
          lease_owner TEXT, lease_epoch INTEGER, lease_token TEXT, lease_until INTEGER, transport_ack_at INTEGER, semantic_completion_event_id TEXT,
          contract_id TEXT, contract_generation INTEGER, revocation_epoch INTEGER, reconciliation_required INTEGER NOT NULL DEFAULT 0,
          PRIMARY KEY(installation_id,project_id,message_id));
        CREATE TABLE IF NOT EXISTS inbox(installation_id TEXT NOT NULL, project_id TEXT NOT NULL, message_id TEXT NOT NULL, applied_event_id TEXT NOT NULL, applied_at INTEGER NOT NULL,
          contract_id TEXT, contract_generation INTEGER, revocation_epoch INTEGER, authority_state TEXT NOT NULL DEFAULT 'CURRENT', PRIMARY KEY(installation_id,project_id,message_id));
        CREATE TABLE IF NOT EXISTS checkpoints(installation_id TEXT NOT NULL, project_id TEXT NOT NULL, checkpoint_id TEXT NOT NULL, encoding_version INTEGER NOT NULL DEFAULT 1, sequence INTEGER NOT NULL, event_hash TEXT NOT NULL, projection_digest TEXT NOT NULL, key_id TEXT NOT NULL, created_at INTEGER NOT NULL, signature TEXT NOT NULL, PRIMARY KEY(installation_id,project_id,checkpoint_id), UNIQUE(installation_id,project_id,sequence));
        CREATE TABLE IF NOT EXISTS contract_versions(installation_id TEXT NOT NULL, project_id TEXT NOT NULL, contract_id TEXT NOT NULL, generation INTEGER NOT NULL, document TEXT NOT NULL, revocation_epoch INTEGER NOT NULL, PRIMARY KEY(installation_id,project_id,contract_id,generation));
        CREATE TABLE IF NOT EXISTS contract_heads(installation_id TEXT NOT NULL, project_id TEXT NOT NULL, contract_id TEXT NOT NULL, generation INTEGER NOT NULL, revocation_epoch INTEGER NOT NULL, PRIMARY KEY(installation_id,project_id,contract_id));
        CREATE TRIGGER IF NOT EXISTS immutable_events_update BEFORE UPDATE ON events BEGIN SELECT RAISE(ABORT,'immutable event'); END;
        CREATE TRIGGER IF NOT EXISTS immutable_events_delete BEFORE DELETE ON events BEGIN SELECT RAISE(ABORT,'immutable event'); END;
        CREATE TRIGGER IF NOT EXISTS immutable_checkpoints_update BEFORE UPDATE ON checkpoints BEGIN SELECT RAISE(ABORT,'immutable checkpoint'); END;
        CREATE TRIGGER IF NOT EXISTS immutable_checkpoints_delete BEFORE DELETE ON checkpoints BEGIN SELECT RAISE(ABORT,'immutable checkpoint'); END;
        CREATE TRIGGER IF NOT EXISTS immutable_contract_versions_update BEFORE UPDATE ON contract_versions BEGIN SELECT RAISE(ABORT,'immutable contract version'); END;
        CREATE TRIGGER IF NOT EXISTS immutable_contract_versions_delete BEFORE DELETE ON contract_versions BEGIN SELECT RAISE(ABORT,'immutable contract version'); END;
        """)
        # Additive migration for stores created before the R3 inbox/outbox contract.
        # The legacy rebuild is one transaction: SQLite otherwise permits a crash
        # between RENAME/CREATE/COPY to leave an apparently valid but empty store.
        self.conn.execute("BEGIN IMMEDIATE")
        try:
            for table, columns in {
                "outbox": (
                    "lease_epoch INTEGER",
                    "lease_token TEXT",
                    "contract_id TEXT",
                    "contract_generation INTEGER",
                    "revocation_epoch INTEGER",
                    "reconciliation_required INTEGER NOT NULL DEFAULT 0",
                ),
                "inbox": (
                    "contract_id TEXT",
                    "contract_generation INTEGER",
                    "revocation_epoch INTEGER",
                    "authority_state TEXT NOT NULL DEFAULT 'CURRENT'",
                ),
                "events": ("contract_id TEXT", "contract_generation INTEGER", "revocation_epoch INTEGER"),
            }.items():
                existing = {row[1] for row in self.conn.execute(f"PRAGMA table_info({table})")}
                for column in columns:
                    if column.split()[0] not in existing:
                        self.conn.execute(f"ALTER TABLE {table} ADD COLUMN {column}")
            sql_row = self.conn.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name='outbox'").fetchone()
            if sql_row and "'UNKNOWN'" not in sql_row[0]:
                indexes = [
                    row[0]
                    for row in self.conn.execute(
                        "SELECT sql FROM sqlite_master WHERE type='index' AND tbl_name='outbox' AND sql IS NOT NULL"
                    )
                ]
                self.conn.execute("ALTER TABLE outbox RENAME TO outbox_legacy")
                self.conn.execute("""CREATE TABLE outbox(installation_id TEXT NOT NULL, project_id TEXT NOT NULL, message_id TEXT NOT NULL, event_id TEXT NOT NULL,
                  status TEXT NOT NULL CHECK(status IN ('PENDING','LEASED','RETRY_WAIT','SENT','POISON','UNKNOWN')), attempts INTEGER NOT NULL DEFAULT 0, last_error TEXT,
                  lease_owner TEXT, lease_epoch INTEGER, lease_token TEXT, lease_until INTEGER, transport_ack_at INTEGER, semantic_completion_event_id TEXT,
                  contract_id TEXT, contract_generation INTEGER, revocation_epoch INTEGER, reconciliation_required INTEGER NOT NULL DEFAULT 0,
                  PRIMARY KEY(installation_id,project_id,message_id))""")
                target = [row[1] for row in self.conn.execute("PRAGMA table_info(outbox)")]
                source = {row[1] for row in self.conn.execute("PRAGMA table_info(outbox_legacy)")}
                columns = [name for name in target if name in source]
                names = ",".join(columns)
                self.conn.execute(f"INSERT INTO outbox({names}) SELECT {names} FROM outbox_legacy")
                self._stage("after_outbox_legacy_copy")
                self.conn.execute("DROP TABLE outbox_legacy")
                for index_sql in indexes:
                    self.conn.execute(index_sql)
            self.conn.commit()
        except Exception:
            self.conn.rollback()
            raise

    def close(self) -> None:
        self.conn.close()
        self._closed = True

    def acquire_lease(self, resource: str, owner: str, *, ttl: int):
        import secrets

        from .leases import Lease, LeaseOutcome, LeaseResult

        now = self.clock()
        if not _valid_identifier(resource) or not _valid_identifier(owner) or not _valid_positive_integer(ttl, now=now):
            return LeaseOutcome(LeaseResult.INVALID_INPUT)
        try:
            self.conn.execute("BEGIN IMMEDIATE")
            row = self.conn.execute(
                "SELECT * FROM leases WHERE installation_id=? AND project_id=? AND resource=?",
                (self.scope.installation_id, self.scope.project_id, resource),
            ).fetchone()
            if row and row["expires_at"] > now and row["owner"] != owner:
                self.conn.rollback()
                return LeaseOutcome(LeaseResult.CONTENDED)
            same = row and row["owner"] == owner and row["expires_at"] > now
            epoch = row["epoch"] if same else (row["epoch"] + 1 if row else 1)
            token = row["token"] if same else secrets.token_hex(32)
            expires = now + ttl
            self.conn.execute(
                "INSERT OR REPLACE INTO leases VALUES(?,?,?,?,?,?,?)",
                (self.scope.installation_id, self.scope.project_id, resource, owner, epoch, expires, token),
            )
            self.conn.commit()
            return LeaseOutcome(LeaseResult.ACQUIRED, Lease(self.scope, resource, owner, epoch, expires, token))
        except sqlite3.OperationalError as exc:
            self.conn.rollback()
            if "locked" in str(exc).lower():
                return LeaseOutcome(LeaseResult.CONTENDED)
            raise
        except Exception:
            self.conn.rollback()
            raise

    def release_lease(self, lease: Any, owner: str):
        """Atomically release exactly the live lease represented by ``lease``."""
        from .leases import Lease, LeaseOutcome, LeaseResult

        if not isinstance(lease, Lease) or not _valid_identifier(owner):
            return LeaseOutcome(LeaseResult.INVALID_INPUT)
        try:
            self.conn.execute("BEGIN IMMEDIATE")
            row = self.conn.execute(
                "SELECT * FROM leases WHERE installation_id=? AND project_id=? AND resource=?",
                (self.scope.installation_id, self.scope.project_id, lease.resource),
            ).fetchone()
            if not row or row["owner"] != owner or row["epoch"] != lease.epoch or row["token"] != lease.token:
                self.conn.rollback()
                return LeaseOutcome(LeaseResult.STALE_FENCE)
            if row["expires_at"] <= self.clock():
                self.conn.rollback()
                return LeaseOutcome(LeaseResult.LEASE_EXPIRED)
            deleted = self.conn.execute(
                "DELETE FROM leases WHERE installation_id=? AND project_id=? AND resource=? AND owner=? AND epoch=? AND token=? AND expires_at>?",
                (
                    self.scope.installation_id,
                    self.scope.project_id,
                    lease.resource,
                    owner,
                    lease.epoch,
                    lease.token,
                    self.clock(),
                ),
            )
            if deleted.rowcount != 1:
                self.conn.rollback()
                return LeaseOutcome(LeaseResult.STALE_FENCE)
            self.conn.commit()
            return LeaseOutcome(LeaseResult.ACQUIRED)
        except sqlite3.OperationalError as exc:
            self.conn.rollback()
            if "locked" in str(exc).lower():
                return LeaseOutcome(LeaseResult.CONTENDED)
            raise
        except Exception:
            self.conn.rollback()
            raise

    def renew_lease(self, lease: Any, owner: str, *, ttl: int, token: str | None = None):
        from .leases import Lease, LeaseOutcome, LeaseResult

        now = self.clock()
        if not isinstance(lease, Lease) or not _valid_identifier(owner) or not _valid_positive_integer(ttl, now=now):
            return LeaseOutcome(LeaseResult.INVALID_INPUT)
        try:
            self.conn.execute("BEGIN IMMEDIATE")
            row = self.conn.execute(
                "SELECT * FROM leases WHERE installation_id=? AND project_id=? AND resource=?",
                (self.scope.installation_id, self.scope.project_id, lease.resource),
            ).fetchone()
            if not row or row["owner"] != owner or row["epoch"] != lease.epoch:
                self.conn.rollback()
                return LeaseOutcome(LeaseResult.STALE_FENCE)
            if token is not None and token != row["token"]:
                self.conn.rollback()
                return LeaseOutcome(LeaseResult.NOT_LEASE_OWNER)
            if row["expires_at"] <= now:
                self.conn.rollback()
                return LeaseOutcome(LeaseResult.LEASE_EXPIRED)
            expires = now + ttl
            updated = self.conn.execute(
                "UPDATE leases SET expires_at=? WHERE installation_id=? AND project_id=? AND resource=? AND owner=? AND epoch=? AND token=?",
                (
                    expires,
                    self.scope.installation_id,
                    self.scope.project_id,
                    lease.resource,
                    owner,
                    lease.epoch,
                    row["token"],
                ),
            )
            if updated.rowcount != 1:
                self.conn.rollback()
                return LeaseOutcome(LeaseResult.STALE_FENCE)
            self.conn.commit()
            return LeaseOutcome(
                LeaseResult.ACQUIRED, Lease(self.scope, lease.resource, owner, lease.epoch, expires, row["token"])
            )
        except sqlite3.OperationalError as exc:
            self.conn.rollback()
            if "locked" in str(exc).lower():
                return LeaseOutcome(LeaseResult.CONTENDED)
            raise
        except Exception:
            self.conn.rollback()
            raise

    def check_lease(self, lease: Any, owner: str | None = None):
        from .leases import Lease, LeaseOutcome, LeaseResult

        row = self.conn.execute(
            "SELECT * FROM leases WHERE installation_id=? AND project_id=? AND resource=?",
            (self.scope.installation_id, self.scope.project_id, lease.resource),
        ).fetchone()
        if not row or row["epoch"] != lease.epoch or row["token"] != lease.token or (owner and row["owner"] != owner):
            return LeaseOutcome(LeaseResult.STALE_FENCE)
        if row["expires_at"] <= self.clock():
            return LeaseOutcome(LeaseResult.LEASE_EXPIRED)
        return LeaseOutcome(
            LeaseResult.ACQUIRED,
            Lease(self.scope, lease.resource, row["owner"], row["epoch"], row["expires_at"], row["token"]),
        )

    def draft(
        self,
        aggregate: str,
        kind: str,
        payload: Mapping[str, Any],
        *,
        writer: WriterContext,
        expected_version: int = 0,
        contract_generation: int | None = None,
        revocation_epoch: int | None = None,
    ) -> SignedEventDraft:
        if writer.scope != self.scope:
            raise InvalidScopeError("scope mismatch")
        _canonical_payload(payload)
        return SignedEventDraft(
            self.scope,
            aggregate,
            kind,
            dict(payload),
            writer.writer_id,
            writer.key_id,
            writer.resource,
            writer.fence,
            expected_version=expected_version,
            contract_generation=contract_generation,
            revocation_epoch=revocation_epoch,
        )

    def _check(self, draft: SignedEventDraft, context: WriterContext) -> Result | None:
        if draft.scope != self.scope or context.scope != self.scope or draft.writer_id != context.writer_id:
            return Result.INVALID_SCOPE
        if (draft.key_id, draft.resource, draft.fence) != (context.key_id, context.resource, context.fence):
            return Result.STALE_FENCE
        try:
            verified = self.writer_authenticator.verify(draft, context)
        except Exception:
            return Result.INTEGRITY_FAILURE
        if not verified:
            return Result.AUTHENTICATION_FAILED
        return None

    def _authority_status(self, draft: SignedEventDraft) -> Result | None:
        if draft.kind in _AUTHORITY_BOUND_EVENT_KINDS:
            if draft.contract_generation is None or draft.revocation_epoch is None:
                return Result.INVALID_INPUT
            contract_id = draft.payload.get("contract_id") if isinstance(draft.payload, Mapping) else None
            if not isinstance(contract_id, str):
                return Result.INVALID_INPUT
        elif draft.contract_generation is None and draft.revocation_epoch is None:
            return None
        elif (draft.contract_generation is None) != (draft.revocation_epoch is None):
            return Result.INVALID_INPUT
        contract_id = draft.payload.get("contract_id") if isinstance(draft.payload, Mapping) else None
        if not isinstance(contract_id, str):
            contract_id = draft.aggregate
        row = self.conn.execute(
            "SELECT h.generation,h.revocation_epoch,v.document FROM contract_heads h JOIN contract_versions v ON v.installation_id=h.installation_id AND v.project_id=h.project_id AND v.contract_id=h.contract_id AND v.generation=h.generation WHERE h.installation_id=? AND h.project_id=? AND h.contract_id=?",
            (self.scope.installation_id, self.scope.project_id, contract_id),
        ).fetchone()
        if not row or row[0] != draft.contract_generation or row[1] != draft.revocation_epoch:
            return Result.STALE_AUTHORITY
        if draft.kind in _AUTHORITY_BOUND_EVENT_KINDS:
            try:
                status = ExecutionContract.from_dict(json.loads(row[2])).status
            except Exception:
                return Result.INTEGRITY_FAILURE
            if status is not ContractState.ACTIVE:
                return Result.STALE_AUTHORITY
        return None

    def _message_replay_status(self, message_id: str, draft: SignedEventDraft) -> Result | None:
        row = self.conn.execute(
            "SELECT e.aggregate,e.kind,e.payload FROM inbox i JOIN events e "
            "ON e.installation_id=i.installation_id AND e.project_id=i.project_id "
            "AND e.event_id=i.applied_event_id WHERE i.installation_id=? AND i.project_id=? AND i.message_id=?",
            (self.scope.installation_id, self.scope.project_id, message_id),
        ).fetchone()
        if row is None:
            return None
        incoming = _canonical_payload(draft.payload)
        if (row["aggregate"], row["kind"], row["payload"]) == (draft.aggregate, draft.kind, incoming):
            return Result.DUPLICATE
        return Result.IDEMPOTENCY_CONFLICT

    def _evidence_prerequisite_status(self, draft: SignedEventDraft) -> Result | None:
        if draft.kind != "evidence.receipt.recorded":
            return None
        receipt = draft.payload
        matches = []
        for row in self.conn.execute(
            "SELECT payload FROM events WHERE installation_id=? AND project_id=? AND kind=?",
            (self.scope.installation_id, self.scope.project_id, "runtime.terminal.observed"),
        ):
            terminal = json.loads(row["payload"])
            if terminal.get("message_id") == receipt["message_id"]:
                matches.append(terminal)
        if len(matches) != 1:
            return Result.INVALID_INPUT
        terminal = matches[0]
        shared = (
            "run_id",
            "task_id",
            "attempt",
            "contract_id",
            "contract_generation",
            "revocation_epoch",
            "message_id",
            "logical_session",
            "acp_session_id",
        )
        if any(terminal.get(field) != receipt.get(field) for field in shared):
            return Result.INVALID_INPUT
        if terminal.get("status") != receipt["terminal"]["technical_status"]:
            return Result.INVALID_INPUT
        return None

    def _receipt_input_status(self, draft: SignedEventDraft, message_id: str | None) -> Result | None:
        if draft.kind != "evidence.receipt.recorded":
            return None
        from .evidence import EvidenceVerificationError, validate_evidence_receipt_payload

        try:
            validate_evidence_receipt_payload(draft.payload)
        except EvidenceVerificationError:
            return Result.INVALID_INPUT
        expected_message_id = "evidence:" + draft.payload["message_id"]
        if (
            draft.payload["installation_id"] != self.scope.installation_id
            or draft.payload["project_id"] != self.scope.project_id
            or draft.aggregate != expected_message_id
            or message_id != expected_message_id
        ):
            return Result.INVALID_INPUT
        return None

    def _insert_draft(
        self,
        draft: SignedEventDraft,
        message_id: str | None,
        *,
        batch_index: int | None = None,
    ) -> tuple[Result | None, str | None]:
        current = self.conn.execute(
            "SELECT COALESCE(MAX(version),0) FROM events WHERE installation_id=? AND project_id=? AND aggregate=?",
            (self.scope.installation_id, self.scope.project_id, draft.aggregate),
        ).fetchone()[0]
        if current != draft.expected_version:
            return Result.CAS_CONFLICT, None
        last = self.conn.execute(
            "SELECT event_hash FROM events WHERE installation_id=? AND project_id=? ORDER BY sequence DESC LIMIT 1",
            (self.scope.installation_id, self.scope.project_id),
        ).fetchone()
        previous = last[0] if last else "GENESIS"
        sequence = self.conn.execute(
            "SELECT COALESCE(MAX(sequence),0)+1 FROM events WHERE installation_id=? AND project_id=?",
            (self.scope.installation_id, self.scope.project_id),
        ).fetchone()[0]
        event_id = uuid.uuid4().hex
        now = self.clock()
        payload = json.dumps(draft.payload, sort_keys=True, separators=(",", ":"), allow_nan=False)
        fields = [
            1,
            self.scope.installation_id,
            self.scope.project_id,
            sequence,
            now,
            event_id,
            draft.aggregate,
            current + 1,
            draft.kind,
            payload,
            previous,
            draft.writer_id,
            draft.key_id,
            draft.resource,
            draft.fence,
            draft.proof,
        ]
        event_hash = hashlib.sha256(json.dumps(fields, separators=(",", ":")).encode()).hexdigest()
        auth_tag = self.integrity_signer.sign(json.dumps(fields + [event_hash], separators=(",", ":")).encode())
        contract_id = draft.payload.get("contract_id") if isinstance(draft.payload, Mapping) else None
        self.conn.execute(
            "INSERT INTO events(installation_id,project_id,sequence,event_id,server_time,aggregate,version,kind,payload,previous_hash,event_hash,writer_id,key_id,resource,fence,writer_proof,auth_tag,encoding_version,contract_id,contract_generation,revocation_epoch) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (
                self.scope.installation_id,
                self.scope.project_id,
                sequence,
                event_id,
                now,
                draft.aggregate,
                current + 1,
                draft.kind,
                payload,
                previous,
                event_hash,
                draft.writer_id,
                draft.key_id,
                draft.resource,
                draft.fence,
                draft.proof,
                auth_tag,
                1,
                contract_id,
                draft.contract_generation,
                draft.revocation_epoch,
            ),
        )
        self._stage("after_event_insert")
        old = self.conn.execute(
            "SELECT value FROM projections WHERE installation_id=? AND project_id=? AND aggregate=?",
            (self.scope.installation_id, self.scope.project_id, draft.aggregate),
        ).fetchone()
        value = self.reducer.reduce(json.loads(old[0]) if old else None, draft.kind, draft.payload)
        self.conn.execute(
            "INSERT OR REPLACE INTO projections VALUES(?,?,?,?,?,?,?,?)",
            (
                self.scope.installation_id,
                self.scope.project_id,
                draft.aggregate,
                current + 1,
                json.dumps(value, sort_keys=True, separators=(",", ":")),
                self.reducer.version,
                sequence,
                event_hash,
            ),
        )
        self._stage("after_projection")
        self._stage("after_event")
        if message_id:
            self.conn.execute(
                "INSERT INTO inbox(installation_id,project_id,message_id,applied_event_id,applied_at,contract_id,contract_generation,revocation_epoch,authority_state) VALUES(?,?,?,?,?,?,?,?,?)",
                (
                    self.scope.installation_id,
                    self.scope.project_id,
                    message_id,
                    event_id,
                    now,
                    contract_id,
                    draft.contract_generation,
                    draft.revocation_epoch,
                    "CURRENT",
                ),
            )
            self._stage("after_inbox")
        self.conn.execute(
            "INSERT INTO outbox(installation_id,project_id,message_id,event_id,status,attempts,last_error,lease_owner,lease_epoch,lease_token,lease_until,transport_ack_at,semantic_completion_event_id,contract_id,contract_generation,revocation_epoch,reconciliation_required) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (
                self.scope.installation_id,
                self.scope.project_id,
                message_id or event_id,
                event_id,
                "PENDING",
                0,
                None,
                None,
                None,
                None,
                None,
                None,
                None,
                contract_id,
                draft.contract_generation,
                draft.revocation_epoch,
                0,
            ),
        )
        self._stage("after_outbox")
        if batch_index is not None:
            self._stage(f"batch_after_item_{batch_index}")
        return None, event_id

    def append(self, draft: SignedEventDraft, context: WriterContext, *, message_id: str | None = None) -> AppendResult:
        if message_id is not None and not _valid_identifier(message_id):
            return AppendResult(Result.INVALID_INPUT)
        if draft.kind in {"contract.advance", "dispatch.unknown"}:
            return AppendResult(Result.INVALID_INPUT)
        failure = self._check(draft, context)
        if failure:
            return AppendResult(failure)
        receipt_status = self._receipt_input_status(draft, message_id)
        if receipt_status is not None:
            return AppendResult(receipt_status)
        try:
            self.conn.execute("BEGIN IMMEDIATE")
            replay = self._message_replay_status(message_id, draft) if message_id else None
            if replay is not None:
                self.conn.rollback()
                return AppendResult(replay)
            lease = self.conn.execute(
                "SELECT * FROM leases WHERE installation_id=? AND project_id=? AND resource=? AND owner=? AND epoch=?",
                (self.scope.installation_id, self.scope.project_id, context.resource, context.writer_id, context.fence),
            ).fetchone()
            if not lease or lease["expires_at"] <= self.clock():
                self.conn.rollback()
                return AppendResult(Result.LEASE_EXPIRED if lease else Result.STALE_FENCE)
            authority_status = self._authority_status(draft)
            if authority_status is not None:
                self.conn.rollback()
                return AppendResult(authority_status)
            evidence_status = self._evidence_prerequisite_status(draft)
            if evidence_status is not None:
                self.conn.rollback()
                return AppendResult(evidence_status)
            if (
                draft.kind in _WORKFLOW_EVENT_KINDS
                or draft.kind in _BUDGET_EVENT_KINDS
                or draft.kind == "evidence.receipt.recorded"
                or draft.kind in _CLOSURE_LIFECYCLE_KINDS
            ):
                from .budget import BudgetError, validate_budget_history
                from .workflow import AuthorityError, InvalidTransition, validate_workflow_history

                try:
                    history = self.events()
                    history.append({"aggregate": draft.aggregate, "kind": draft.kind, "payload": dict(draft.payload)})
                    if (
                        draft.kind in _WORKFLOW_EVENT_KINDS
                        or draft.kind == "evidence.receipt.recorded"
                        or draft.kind in _CLOSURE_LIFECYCLE_KINDS
                    ):
                        validate_workflow_history(history)
                    else:
                        contract_row = self.conn.execute(
                            "SELECT v.document FROM contract_versions v JOIN contract_heads h ON h.installation_id=v.installation_id AND h.project_id=v.project_id AND h.contract_id=v.contract_id AND v.generation=h.generation WHERE h.installation_id=? AND h.project_id=? AND h.contract_id=?",
                            (self.scope.installation_id, self.scope.project_id, draft.payload.get("contract_id")),
                        ).fetchone()
                        authorized = json.loads(contract_row[0])["limits"]["model_budget"] if contract_row else 0
                        validate_budget_history(history, authorized=authorized)
                except AuthorityError:
                    self.conn.rollback()
                    return AppendResult(Result.STALE_AUTHORITY)
                except (InvalidTransition, BudgetError, KeyError, TypeError, ValueError):
                    self.conn.rollback()
                    return AppendResult(Result.INVALID_INPUT)
            insert_status, event_id = self._insert_draft(draft, message_id)
            if insert_status is not None or event_id is None:
                self.conn.rollback()
                return AppendResult(insert_status or Result.INTEGRITY_FAILURE)
            self._stage("before_commit")
            self.conn.commit()
            return AppendResult(
                Result.APPLIED,
                self._event_from_row(
                    self.conn.execute("SELECT * FROM events WHERE event_id=?", (event_id,)).fetchone()
                ),
            )
        except sqlite3.IntegrityError:
            self.conn.rollback()
            replay = self._message_replay_status(message_id, draft) if message_id else None
            if replay is not None:
                return AppendResult(replay)
            return AppendResult(Result.CAS_CONFLICT)
        except sqlite3.OperationalError as exc:
            self.conn.rollback()
            return AppendResult(Result.CONTENDED if "locked" in str(exc).lower() else Result.INTEGRITY_FAILURE)
        except Exception:
            self.conn.rollback()
            raise

    def append_evidence_release_batch(
        self,
        receipt_draft: SignedEventDraft,
        context: WriterContext,
        message_id: str,
        releases: tuple[tuple[SignedEventDraft, str], ...],
    ) -> AppendResult:
        """Atomically persist one verified receipt and its deterministic releases."""
        items = ((receipt_draft, message_id), *releases)
        if (
            receipt_draft.kind != "evidence.receipt.recorded"
            or not releases
            or any(draft.kind != "task.released" for draft, _ in releases)
            or tuple(draft.aggregate for draft, _ in releases)
            != tuple(sorted(draft.aggregate for draft, _ in releases))
            or len({item_message_id for _, item_message_id in items}) != len(items)
            or any(not _valid_identifier(item_message_id) for _, item_message_id in items)
        ):
            return AppendResult(Result.INVALID_INPUT)
        for draft, item_message_id in items:
            failure = self._check(draft, context)
            if failure is not None:
                return AppendResult(failure)
            receipt_status = self._receipt_input_status(draft, item_message_id)
            if receipt_status is not None:
                return AppendResult(receipt_status)
        try:
            self.conn.execute("BEGIN IMMEDIATE")
            replay_states = [self._message_replay_status(item_message_id, draft) for draft, item_message_id in items]
            if any(state is Result.IDEMPOTENCY_CONFLICT for state in replay_states):
                self.conn.rollback()
                return AppendResult(Result.IDEMPOTENCY_CONFLICT)
            if all(state is Result.DUPLICATE for state in replay_states):
                self.conn.rollback()
                return AppendResult(Result.DUPLICATE)
            if any(state is not None for state in replay_states):
                self.conn.rollback()
                return AppendResult(Result.INTEGRITY_FAILURE)
            now = self.clock()
            for draft, _ in items:
                lease = self.conn.execute(
                    "SELECT * FROM leases WHERE installation_id=? AND project_id=? AND resource=? AND owner=? AND epoch=?",
                    (
                        self.scope.installation_id,
                        self.scope.project_id,
                        context.resource,
                        context.writer_id,
                        context.fence,
                    ),
                ).fetchone()
                if not lease or lease["expires_at"] <= now:
                    self.conn.rollback()
                    return AppendResult(Result.LEASE_EXPIRED if lease else Result.STALE_FENCE)
                authority_status = self._authority_status(draft)
                if authority_status is not None:
                    self.conn.rollback()
                    return AppendResult(authority_status)
                evidence_status = self._evidence_prerequisite_status(draft)
                if evidence_status is not None:
                    self.conn.rollback()
                    return AppendResult(evidence_status)
            from .workflow import AuthorityError, InvalidTransition, validate_workflow_history

            history = self.events()
            history.extend(
                {"aggregate": draft.aggregate, "kind": draft.kind, "payload": dict(draft.payload)} for draft, _ in items
            )
            try:
                validate_workflow_history(history)
            except AuthorityError:
                self.conn.rollback()
                return AppendResult(Result.STALE_AUTHORITY)
            except (InvalidTransition, KeyError, TypeError, ValueError):
                self.conn.rollback()
                return AppendResult(Result.INVALID_INPUT)
            event_ids = []
            for index, (draft, item_message_id) in enumerate(items, 1):
                insert_status, event_id = self._insert_draft(
                    draft,
                    item_message_id,
                    batch_index=index,
                )
                if insert_status is not None or event_id is None:
                    self.conn.rollback()
                    return AppendResult(insert_status or Result.INTEGRITY_FAILURE)
                event_ids.append(event_id)
            self._stage("before_commit")
            self.conn.commit()
            return AppendResult(
                Result.APPLIED,
                self._event_from_row(
                    self.conn.execute("SELECT * FROM events WHERE event_id=?", (event_ids[0],)).fetchone()
                ),
            )
        except sqlite3.IntegrityError:
            self.conn.rollback()
            replay_states = [self._message_replay_status(item_message_id, draft) for draft, item_message_id in items]
            if all(state is Result.DUPLICATE for state in replay_states):
                return AppendResult(Result.DUPLICATE)
            if any(state is Result.IDEMPOTENCY_CONFLICT for state in replay_states):
                return AppendResult(Result.IDEMPOTENCY_CONFLICT)
            return AppendResult(Result.CAS_CONFLICT)
        except sqlite3.OperationalError as exc:
            self.conn.rollback()
            return AppendResult(Result.CONTENDED if "locked" in str(exc).lower() else Result.INTEGRITY_FAILURE)
        except Exception:
            self.conn.rollback()
            raise

    def _stage(self, name: str) -> None:
        if self.fault:
            self.fault(name)

    def _event_from_row(self, row: sqlite3.Row) -> LedgerEvent:
        return LedgerEvent(
            row["installation_id"],
            row["project_id"],
            row["sequence"],
            row["event_id"],
            row["server_time"],
            row["aggregate"],
            row["version"],
            row["kind"],
            row["payload"],
            row["previous_hash"],
            row["event_hash"],
            row["writer_id"],
            row["key_id"],
            row["resource"],
            row["fence"],
            row["writer_proof"],
            row["auth_tag"],
            row["encoding_version"],
        )

    def events(self) -> list[dict[str, Any]]:
        return [dict(r) for r in self.conn.execute("SELECT * FROM events ORDER BY sequence")]

    def projection(self, aggregate: str) -> dict[str, Any] | None:
        if not _valid_identifier(aggregate):
            raise InvalidInputError("invalid input")
        row = self.conn.execute(
            "SELECT value,version FROM projections WHERE installation_id=? AND project_id=? AND aggregate=?",
            (self.scope.installation_id, self.scope.project_id, aggregate),
        ).fetchone()
        return (json.loads(row[0]) | {"version": row[1]}) if row else None

    def verify_chain(self, anchor_store: TrustedAnchorStore | None = None) -> bool:
        events = self.events()
        anchor = anchor_store.get(self.scope) if anchor_store else None
        if anchor_store and anchor is None:
            raise ValueError(Result.ANCHOR_UNAVAILABLE.value)
        previous = "GENESIS"
        for expected, event in enumerate(events, 1):
            if (
                event["sequence"] != expected
                or event["previous_hash"] != previous
                or event["installation_id"] != self.scope.installation_id
                or event["project_id"] != self.scope.project_id
            ):
                raise ValueError(Result.INTEGRITY_FAILURE.value)
            fields = [
                event["encoding_version"],
                event["installation_id"],
                event["project_id"],
                event["sequence"],
                event["server_time"],
                event["event_id"],
                event["aggregate"],
                event["version"],
                event["kind"],
                event["payload"],
                event["previous_hash"],
                event["writer_id"],
                event["key_id"],
                event["resource"],
                event["fence"],
                event["writer_proof"],
            ]
            material = json.dumps(fields, separators=(",", ":")).encode()
            signed = json.dumps(fields + [event["event_hash"]], separators=(",", ":")).encode()
            if event["event_hash"] != hashlib.sha256(material).hexdigest() or not self.integrity_signer.verify(
                signed, event["auth_tag"]
            ):
                raise ValueError(Result.INTEGRITY_FAILURE.value)
            previous = event["event_hash"]
        if anchor and (len(events) < anchor[0] or events[anchor[0] - 1]["event_hash"] != anchor[1]):
            raise ValueError(Result.ANCHOR_ROLLBACK.value)
        return True

    def _projection_digest(self) -> str:
        rows = [
            dict(row)
            for row in self.conn.execute(
                "SELECT aggregate,version,value,reducer_version,source_sequence,source_hash FROM projections WHERE installation_id=? AND project_id=? ORDER BY aggregate",
                (self.scope.installation_id, self.scope.project_id),
            )
        ]
        return hashlib.sha256(json.dumps(rows, sort_keys=True, separators=(",", ":")).encode()).hexdigest()

    def _projection_digest_at(self, sequence: int) -> str:
        events = [event for event in self.events() if event["sequence"] <= sequence]
        rebuilt = self.reducer.rebuild(events)
        rows = []
        for aggregate in sorted(rebuilt):
            event = next(row for row in reversed(events) if row["aggregate"] == aggregate)
            rows.append(
                {
                    "aggregate": aggregate,
                    "version": event["version"],
                    "value": json.dumps(rebuilt[aggregate], sort_keys=True, separators=(",", ":")),
                    "reducer_version": self.reducer.version,
                    "source_sequence": event["sequence"],
                    "source_hash": event["event_hash"],
                }
            )
        return hashlib.sha256(json.dumps(rows, sort_keys=True, separators=(",", ":")).encode()).hexdigest()

    def verify_projections(self) -> bool:
        row = self.conn.execute(
            "SELECT MAX(sequence) FROM events WHERE installation_id=? AND project_id=?",
            (self.scope.installation_id, self.scope.project_id),
        ).fetchone()
        if row[0] is not None and self._projection_digest() != self._projection_digest_at(row[0]):
            raise ValueError(Result.PROJECTION_MISMATCH.value)
        return True

    def checkpoint(self) -> Checkpoint:
        row = self.conn.execute(
            "SELECT sequence,event_hash FROM events WHERE installation_id=? AND project_id=? ORDER BY sequence DESC LIMIT 1",
            (self.scope.installation_id, self.scope.project_id),
        ).fetchone()
        if row is None:
            raise ValueError("cannot checkpoint empty ledger")
        signed_values = [
            1,
            self.scope.installation_id,
            self.scope.project_id,
            uuid.uuid4().hex,
            row[0],
            row[1],
            self._projection_digest(),
            self.integrity_signer.key_id,
            self.clock(),
        ]
        signature = self.integrity_signer.sign(json.dumps(signed_values, separators=(",", ":")).encode())
        (
            encoding_version,
            installation_id,
            project_id,
            checkpoint_id,
            sequence,
            event_hash,
            projection_digest,
            key_id,
            created_at,
        ) = signed_values
        self.conn.execute(
            "INSERT INTO checkpoints(installation_id,project_id,checkpoint_id,encoding_version,sequence,event_hash,projection_digest,key_id,created_at,signature) VALUES(?,?,?,?,?,?,?,?,?,?)",
            (
                installation_id,
                project_id,
                checkpoint_id,
                encoding_version,
                sequence,
                event_hash,
                projection_digest,
                key_id,
                created_at,
                signature,
            ),
        )
        self.conn.commit()
        return Checkpoint(
            installation_id,
            project_id,
            checkpoint_id,
            encoding_version,
            sequence,
            event_hash,
            projection_digest,
            key_id,
            created_at,
            signature,
        )

    def verify_checkpoints(self) -> bool:
        for row in self.conn.execute(
            "SELECT * FROM checkpoints WHERE installation_id=? AND project_id=?",
            (self.scope.installation_id, self.scope.project_id),
        ):
            event = self.conn.execute(
                "SELECT event_hash FROM events WHERE installation_id=? AND project_id=? AND sequence=?",
                (self.scope.installation_id, self.scope.project_id, row["sequence"]),
            ).fetchone()
            values = [
                row["encoding_version"],
                row["installation_id"],
                row["project_id"],
                row["checkpoint_id"],
                row["sequence"],
                row["event_hash"],
                row["projection_digest"],
                row["key_id"],
                row["created_at"],
            ]
            if (
                row["encoding_version"] != 1
                or row["key_id"] != self.integrity_signer.key_id
                or not event
                or event[0] != row["event_hash"]
                or row["projection_digest"] != self._projection_digest_at(row["sequence"])
                or not self.integrity_signer.verify(
                    json.dumps(values, separators=(",", ":")).encode(), row["signature"]
                )
            ):
                raise ValueError(Result.INTEGRITY_FAILURE.value)
        self.verify_projections()
        return True

    def claim_outbox(
        self,
        owner: str,
        *,
        lease: Any | None = None,
        message_id: str | None = None,
        now: int | None = None,
        lease_ns: int = 30_000_000_000,
        max_attempts: int = 5,
    ) -> list[dict[str, Any]]:
        now = self.clock() if now is None else now
        if (
            not _valid_identifier(owner)
            or not isinstance(now, int)
            or isinstance(now, bool)
            or now < 0
            or not _valid_positive_integer(lease_ns, now=now)
            or not _valid_positive_integer(max_attempts)
            or (message_id is not None and not _valid_identifier(message_id))
        ):
            raise InvalidInputError("invalid input")
        if lease is None:
            return []
        self.conn.execute("BEGIN IMMEDIATE")
        try:
            lease_failure = self._outbox_lease_failure(lease, owner)
            if lease_failure:
                self.conn.rollback()
                return []
            query = (
                "SELECT * FROM outbox WHERE installation_id=? AND project_id=? "
                "AND attempts<? AND (status='PENDING' OR "
                "(status IN ('LEASED','RETRY_WAIT') AND lease_until<=?))"
            )
            args: list[Any] = [self.scope.installation_id, self.scope.project_id, max_attempts, now]
            if message_id is not None:
                query += " AND message_id=?"
                args.append(message_id)
            rows = self.conn.execute(query + " ORDER BY message_id", args).fetchall()
            result = []
            for row in rows:
                attempt = row["attempts"] + 1
                self.conn.execute(
                    "UPDATE outbox SET status='LEASED',attempts=?,lease_owner=?,lease_epoch=?,lease_token=?,lease_until=? WHERE installation_id=? AND project_id=? AND message_id=?",
                    (
                        attempt,
                        owner,
                        lease.epoch,
                        lease.token,
                        now + lease_ns,
                        self.scope.installation_id,
                        self.scope.project_id,
                        row["message_id"],
                    ),
                )
                result.append(
                    dict(row)
                    | {
                        "status": "LEASED",
                        "attempts": attempt,
                        "lease_owner": owner,
                        "lease_epoch": lease.epoch,
                        "lease_token": lease.token,
                        "lease_until": now + lease_ns,
                    }
                )
            self.conn.commit()
            return result
        except Exception:
            self.conn.rollback()
            raise

    def _append_poison_event(
        self,
        row: sqlite3.Row,
        message_id: str,
        error: str,
        now: int,
        *,
        kind: str = "outbox.poison",
        event_payload: Mapping[str, Any] | None = None,
        aggregate: str = "outbox",
    ) -> None:
        source = self.conn.execute(
            "SELECT * FROM events WHERE installation_id=? AND project_id=? AND event_id=?",
            (self.scope.installation_id, self.scope.project_id, row["event_id"]),
        ).fetchone()
        if source is None:
            raise ValueError(Result.INTEGRITY_FAILURE.value)
        last = self.conn.execute(
            "SELECT event_hash FROM events WHERE installation_id=? AND project_id=? ORDER BY sequence DESC LIMIT 1",
            (self.scope.installation_id, self.scope.project_id),
        ).fetchone()
        sequence = self.conn.execute(
            "SELECT COALESCE(MAX(sequence),0)+1 FROM events WHERE installation_id=? AND project_id=?",
            (self.scope.installation_id, self.scope.project_id),
        ).fetchone()[0]
        poison_payload = (
            dict(event_payload)
            if event_payload is not None
            else {"message_id": message_id, "attempts": row["attempts"], "error": error}
        )
        payload = _canonical_payload(poison_payload)
        previous = last[0] if last else "GENESIS"
        version = self.conn.execute(
            "SELECT COALESCE(MAX(version),0)+1 FROM events WHERE installation_id=? AND project_id=? AND aggregate=?",
            (self.scope.installation_id, self.scope.project_id, aggregate),
        ).fetchone()[0]
        event_id = uuid.uuid4().hex
        internal_writer = "ledger-internal"
        internal_key = self.integrity_signer.key_id
        internal_resource = "ledger-integrity"
        internal_fence = 1
        proof_material = json.dumps(
            [
                1,
                self.scope.installation_id,
                self.scope.project_id,
                sequence,
                now,
                event_id,
                aggregate,
                version,
                kind,
                payload,
                previous,
                internal_writer,
                internal_key,
                internal_resource,
                internal_fence,
            ],
            separators=(",", ":"),
        ).encode()
        internal_proof = self.integrity_signer.sign(proof_material)
        fields = [
            1,
            self.scope.installation_id,
            self.scope.project_id,
            sequence,
            now,
            event_id,
            aggregate,
            version,
            kind,
            payload,
            previous,
            internal_writer,
            internal_key,
            internal_resource,
            internal_fence,
            internal_proof,
        ]
        event_hash = hashlib.sha256(json.dumps(fields, separators=(",", ":")).encode()).hexdigest()
        auth_tag = self.integrity_signer.sign(json.dumps(fields + [event_hash], separators=(",", ":")).encode())
        self.conn.execute(
            "INSERT INTO events(installation_id,project_id,sequence,event_id,server_time,aggregate,version,kind,payload,previous_hash,event_hash,writer_id,key_id,resource,fence,writer_proof,auth_tag,encoding_version,contract_id,contract_generation,revocation_epoch) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (
                self.scope.installation_id,
                self.scope.project_id,
                sequence,
                event_id,
                now,
                aggregate,
                version,
                kind,
                payload,
                previous,
                event_hash,
                internal_writer,
                internal_key,
                internal_resource,
                internal_fence,
                internal_proof,
                auth_tag,
                1,
                row["contract_id"],
                row["contract_generation"],
                row["revocation_epoch"],
            ),
        )
        prior = self.conn.execute(
            "SELECT value FROM projections WHERE installation_id=? AND project_id=? AND aggregate=?",
            (self.scope.installation_id, self.scope.project_id, aggregate),
        ).fetchone()
        value = self.reducer.reduce(
            json.loads(prior[0]) if prior else None,
            kind,
            poison_payload,
        )
        self.conn.execute(
            "INSERT OR REPLACE INTO projections VALUES(?,?,?,?,?,?,?,?)",
            (
                self.scope.installation_id,
                self.scope.project_id,
                aggregate,
                version,
                json.dumps(value, sort_keys=True, separators=(",", ":")),
                self.reducer.version,
                sequence,
                event_hash,
            ),
        )

    def mark_outbox_retry(
        self,
        message_id: str,
        owner: str,
        *,
        lease: Any | None = None,
        now: int | None = None,
        backoff_ns: int = 1_000_000_000,
        error: str = "transport failure",
        max_attempts: int = 5,
    ) -> Result:
        now = self.clock() if now is None else now
        if (
            not _valid_identifier(message_id)
            or not _valid_identifier(owner)
            or not isinstance(error, str)
            or len(error.encode()) > MAX_ERROR_BYTES
            or not isinstance(now, int)
            or isinstance(now, bool)
            or now < 0
            or not _valid_positive_integer(backoff_ns, now=now)
            or not _valid_positive_integer(max_attempts)
        ):
            return Result.INVALID_INPUT
        self.conn.execute("BEGIN IMMEDIATE")
        lease_failure = self._outbox_lease_failure(lease, owner)
        if lease_failure:
            self.conn.rollback()
            return lease_failure
        assert lease is not None
        row = self.conn.execute(
            "SELECT * FROM outbox WHERE installation_id=? AND project_id=? AND message_id=?",
            (self.scope.installation_id, self.scope.project_id, message_id),
        ).fetchone()
        lease_epoch, lease_token = lease.epoch, lease.token
        if (
            not row
            or row["status"] != "LEASED"
            or row["lease_owner"] != owner
            or row["lease_epoch"] != lease_epoch
            or row["lease_token"] != lease_token
            or (row["lease_until"] is not None and row["lease_until"] <= now)
        ):
            self.conn.rollback()
            return lease_failure or (
                Result.LEASE_EXPIRED
                if row and row["lease_until"] is not None and row["lease_until"] <= now
                else Result.STALE_FENCE
            )
        status = "POISON" if row["attempts"] >= max_attempts else "RETRY_WAIT"
        until = None if status == "POISON" else now + backoff_ns
        if status == "POISON":
            try:
                self._append_poison_event(row, message_id, error, now)
            except sqlite3.OperationalError as exc:
                self.conn.rollback()
                return Result.CONTENDED if "locked" in str(exc).lower() else Result.INTEGRITY_FAILURE
            except Exception:
                self.conn.rollback()
                return Result.INTEGRITY_FAILURE
        self.conn.execute(
            "UPDATE outbox SET status=?,last_error=?,lease_owner=NULL,lease_until=?,reconciliation_required=0 WHERE installation_id=? AND project_id=? AND message_id=?",
            (status, error, until, self.scope.installation_id, self.scope.project_id, message_id),
        )
        self.conn.commit()
        return Result.POISON_TERMINATED if status == "POISON" else Result.RETRY_SCHEDULED

    def mark_outbox_sent(self, message_id: str, owner: str, *, lease: Any | None = None) -> Result:
        if not _valid_identifier(message_id) or not _valid_identifier(owner):
            return Result.INVALID_INPUT
        self.conn.execute("BEGIN IMMEDIATE")
        now = self.clock()
        lease_failure = self._outbox_lease_failure(lease, owner)
        if lease_failure:
            self.conn.rollback()
            return lease_failure
        cur = self.conn.execute(
            "UPDATE outbox SET status='SENT',transport_ack_at=?,lease_owner=NULL,lease_epoch=NULL,lease_token=NULL,lease_until=NULL,reconciliation_required=0 WHERE installation_id=? AND project_id=? AND message_id=? AND status='LEASED' AND lease_owner=? AND lease_epoch=? AND lease_token=? AND lease_until> ?",
            (
                now,
                self.scope.installation_id,
                self.scope.project_id,
                message_id,
                owner,
                lease.epoch if lease else -1,
                lease.token if lease else "",
                now,
            ),
        )
        self.conn.commit()
        return Result.TRANSPORT_ACKNOWLEDGED if cur.rowcount else Result.STALE_FENCE

    def mark_outbox_effect_started(self, message_id: str, owner: str, *, lease: Any) -> Result:
        """Durably fence a possibly accepted external effect before awaiting it."""
        if not _valid_identifier(message_id) or not _valid_identifier(owner):
            return Result.INVALID_INPUT
        self.conn.execute("BEGIN IMMEDIATE")
        try:
            failure = self._outbox_lease_failure(lease, owner)
            if failure:
                self.conn.rollback()
                return failure
            cur = self.conn.execute(
                "UPDATE outbox SET reconciliation_required=1 WHERE installation_id=? AND project_id=? AND message_id=? AND status='LEASED' AND reconciliation_required=0 AND lease_owner=? AND lease_epoch=? AND lease_token=? AND lease_until> ?",
                (
                    self.scope.installation_id,
                    self.scope.project_id,
                    message_id,
                    owner,
                    lease.epoch,
                    lease.token,
                    self.clock(),
                ),
            )
            self.conn.commit()
            return Result.APPLIED if cur.rowcount == 1 else Result.STALE_FENCE
        except Exception:
            self.conn.rollback()
            raise

    def mark_outbox_unknown(
        self,
        message_id: str,
        owner: str,
        *,
        lease: Any,
        reason: str = "unknown transport outcome",
        authority: Mapping[str, Any] | None = None,
    ) -> Result:
        self.conn.execute("BEGIN IMMEDIATE")
        try:
            failure = self._outbox_lease_failure(lease, owner)
            row = self.conn.execute(
                "SELECT * FROM outbox WHERE installation_id=? AND project_id=? AND message_id=?",
                (self.scope.installation_id, self.scope.project_id, message_id),
            ).fetchone()
            if failure and not (row and row["status"] == "UNKNOWN" and row["reconciliation_required"] == 1):
                self.conn.rollback()
                return failure
            if not row:
                self.conn.rollback()
                return Result.STALE_FENCE
            if row["status"] == "LEASED" and (
                tuple((row["lease_owner"], row["lease_epoch"], row["lease_token"])) != (owner, lease.epoch, lease.token)
            ):
                self.conn.rollback()
                return Result.STALE_FENCE
            if row["status"] not in {"LEASED", "UNKNOWN"}:
                self.conn.rollback()
                return Result.STALE_FENCE
            self._stage("before_unknown_event")
            payload = (
                {
                    "run_id": authority["run_id"],
                    "task_id": authority["task_id"],
                    "attempt": authority["attempt"],
                    "contract_id": authority["contract_id"],
                    "message_id": message_id,
                    "reason": reason,
                }
                if authority is not None
                else None
            )
            self._append_poison_event(
                row,
                message_id,
                reason,
                self.clock(),
                kind="dispatch.unknown",
                event_payload=payload,
                aggregate="dispatch:" + message_id,
            )
            self._stage("after_unknown_event")
            self.conn.execute(
                "UPDATE outbox SET status='UNKNOWN',reconciliation_required=1,lease_owner=NULL,lease_epoch=NULL,lease_token=NULL,lease_until=NULL WHERE installation_id=? AND project_id=? AND message_id=?",
                (self.scope.installation_id, self.scope.project_id, message_id),
            )
            self._stage("after_unknown_outbox")
            self.conn.commit()
            return Result.APPLIED
        except Exception:
            self.conn.rollback()
            raise

    def reconcile_outbox(self, message_id: str, *, authority: Mapping[str, Any]) -> Result:
        row = self.conn.execute(
            "SELECT * FROM outbox WHERE installation_id=? AND project_id=? AND message_id=?",
            (self.scope.installation_id, self.scope.project_id, message_id),
        ).fetchone()
        if not row or row["status"] != "UNKNOWN" or row["reconciliation_required"] != 1:
            return Result.INVALID_INPUT
        if any(row[name] != authority.get(name) for name in ("contract_id", "contract_generation", "revocation_epoch")):
            return Result.STALE_AUTHORITY
        self.conn.execute(
            "UPDATE outbox SET reconciliation_required=0,status='SENT' WHERE installation_id=? AND project_id=? AND message_id=?",
            (self.scope.installation_id, self.scope.project_id, message_id),
        )
        self.conn.commit()
        return Result.APPLIED

    def _outbox_lease_failure(self, lease: Any | None, owner: str) -> Result | None:
        if lease is None or getattr(lease, "resource", None) != "outbox" or getattr(lease, "scope", None) != self.scope:
            return Result.STALE_FENCE
        row = self.conn.execute(
            "SELECT owner,epoch,token,expires_at FROM leases WHERE installation_id=? AND project_id=? AND resource=?",
            (self.scope.installation_id, self.scope.project_id, "outbox"),
        ).fetchone()
        if not row or row["owner"] != owner or row["epoch"] != lease.epoch or row["token"] != lease.token:
            return Result.STALE_FENCE
        if row["expires_at"] <= self.clock():
            return Result.LEASE_EXPIRED
        return None

    def complete_outbox(self, message_id: str, completion_event_id: str) -> Result:
        if not _valid_identifier(message_id) or not _valid_identifier(completion_event_id):
            return Result.INVALID_INPUT
        # R10a has no semantic completion event kind or authenticated binding
        # contract.  Until one exists, this public API must fail closed rather
        # than accepting an arbitrary string as execution evidence.
        return Result.INVALID_INPUT

    def outbox(self) -> list[dict[str, Any]]:
        return [
            dict(row)
            for row in self.conn.execute(
                "SELECT * FROM outbox WHERE installation_id=? AND project_id=? ORDER BY message_id",
                (self.scope.installation_id, self.scope.project_id),
            )
        ]

    def outbox_message(self, message_id: str) -> dict[str, Any] | None:
        if not _valid_identifier(message_id):
            return None
        row = self.conn.execute(
            "SELECT * FROM outbox WHERE installation_id=? AND project_id=? AND message_id=?",
            (self.scope.installation_id, self.scope.project_id, message_id),
        ).fetchone()
        return dict(row) if row else None

    def aggregate_version(self, aggregate: str) -> int:
        if not isinstance(aggregate, str) or not aggregate:
            raise InvalidInputError("invalid aggregate")
        return int(
            self.conn.execute(
                "SELECT COALESCE(MAX(version),0) FROM events WHERE installation_id=? AND project_id=? AND aggregate=?",
                (self.scope.installation_id, self.scope.project_id, aggregate),
            ).fetchone()[0]
        )

    def lease(self, resource: str) -> Any | None:
        from .leases import Lease

        if not _valid_identifier(resource):
            return None
        row = self.conn.execute(
            "SELECT * FROM leases WHERE installation_id=? AND project_id=? AND resource=?",
            (self.scope.installation_id, self.scope.project_id, resource),
        ).fetchone()
        return Lease(self.scope, resource, row["owner"], row["epoch"], row["expires_at"], row["token"]) if row else None

    def create_contract(
        self,
        document: ExecutionContract,
        *,
        contract_id: str | None = None,
        generation: int | None = None,
        revocation_epoch: int | None = None,
    ) -> Result:
        """Install the one trusted genesis contract for this ledger scope.

        Subsequent authority changes must use ``advance_contract`` with an
        authenticated amendment; this bootstrap path cannot manufacture a
        non-genesis head.
        """
        if not isinstance(document, ExecutionContract) or document.project_id != self.scope.project_id:
            return Result.INVALID_SCOPE
        if (
            document.generation != 0
            or document.revocation_epoch != 0
            or document.status not in {ContractState.PROPOSED, ContractState.ACTIVE}
        ):
            return Result.INVALID_INPUT
        if contract_id is not None and contract_id != document.contract_id:
            return Result.CAS_CONFLICT
        if generation is not None and generation != document.generation:
            return Result.CAS_CONFLICT
        if revocation_epoch is not None and revocation_epoch != document.revocation_epoch:
            return Result.CAS_CONFLICT
        encoded = json.dumps(document.to_dict(), sort_keys=True, separators=(",", ":"), allow_nan=False)
        try:
            self.conn.execute("BEGIN IMMEDIATE")
            initialized = self.conn.execute(
                "SELECT EXISTS(SELECT 1 FROM contract_heads WHERE installation_id=? AND project_id=? UNION SELECT 1 FROM events WHERE installation_id=? AND project_id=?)",
                (
                    self.scope.installation_id,
                    self.scope.project_id,
                    self.scope.installation_id,
                    self.scope.project_id,
                ),
            ).fetchone()[0]
            if initialized:
                self.conn.rollback()
                return Result.CAS_CONFLICT
            self.conn.execute(
                "INSERT INTO contract_versions(installation_id,project_id,contract_id,generation,document,revocation_epoch) VALUES(?,?,?,?,?,?)",
                (
                    self.scope.installation_id,
                    self.scope.project_id,
                    document.contract_id,
                    document.generation,
                    encoded,
                    document.revocation_epoch,
                ),
            )
            self._stage("after_contract_version")
            self.conn.execute(
                "INSERT INTO contract_heads(installation_id,project_id,contract_id,generation,revocation_epoch) VALUES(?,?,?,?,?)",
                (
                    self.scope.installation_id,
                    self.scope.project_id,
                    document.contract_id,
                    document.generation,
                    document.revocation_epoch,
                ),
            )
            self._stage("after_contract_head")
            self.conn.commit()
            return Result.APPLIED
        except sqlite3.IntegrityError:
            self.conn.rollback()
            return Result.CAS_CONFLICT
        except Exception:
            self.conn.rollback()
            raise

    def read_contract(self, contract_id: str) -> ExecutionContract | None:
        row = self.conn.execute(
            "SELECT v.document,h.revocation_epoch FROM contract_versions v JOIN contract_heads h ON h.installation_id=v.installation_id AND h.project_id=v.project_id AND h.contract_id=v.contract_id AND h.generation=v.generation WHERE v.installation_id=? AND v.project_id=? AND v.contract_id=?",
            (self.scope.installation_id, self.scope.project_id, contract_id),
        ).fetchone()
        if not row:
            return None
        document = json.loads(row[0])
        document["revocation_epoch"] = row[1]
        return ExecutionContract.from_dict(document)

    def contract(self, contract_id: str | None = None) -> dict[str, Any] | None:
        query = "SELECT v.document FROM contract_versions v JOIN contract_heads h ON h.installation_id=v.installation_id AND h.project_id=v.project_id AND h.contract_id=v.contract_id AND h.generation=v.generation WHERE v.installation_id=? AND v.project_id=?"
        args = [self.scope.installation_id, self.scope.project_id]
        if contract_id is not None:
            query += " AND v.contract_id=?"
            args.append(contract_id)
        row = self.conn.execute(query, args).fetchone()
        return json.loads(row[0]) if row else None

    def _amendment_draft(self, amendment: ContractAmendment, context: WriterContext) -> SignedEventDraft:
        payload = {
            "contract_id": amendment.new_contract.contract_id,
            "prior_contract": amendment.prior_contract.to_dict(),
            "new_contract": amendment.new_contract.to_dict(),
            "prior_generation": amendment.prior_generation,
            "revocation_epoch": amendment.revocation_epoch,
            "rationale": amendment.rationale,
            "issuer": amendment.issuer.to_dict(),
            "affected_identities": list(amendment.affected_identities),
        }
        return self.draft(
            "contract",
            "contract.advance",
            payload,
            writer=context,
            expected_version=0,
            contract_generation=amendment.prior_generation,
            revocation_epoch=amendment.prior_contract.revocation_epoch,
        )

    def advance_contract(
        self,
        amendment: ContractAmendment,
        context: WriterContext,
        *,
        expected_generation: int,
        expected_revocation_epoch: int,
        proof: str | SignedEventDraft | None = None,
    ) -> Result:
        if not isinstance(amendment, ContractAmendment):
            return Result.AUTHENTICATION_FAILED
        if (
            amendment.prior_generation != expected_generation
            or amendment.prior_contract.revocation_epoch != expected_revocation_epoch
        ):
            return Result.CAS_CONFLICT
        if (
            amendment.issuer != amendment.prior_contract.amendment_authority
            or amendment.issuer.actor_id != context.writer_id
        ):
            return Result.AUTHENTICATION_FAILED
        intent = self._amendment_draft(amendment, context)
        signed = (
            proof
            if isinstance(proof, SignedEventDraft)
            else SignedEventDraft(
                intent.scope,
                intent.aggregate,
                intent.kind,
                intent.payload,
                intent.writer_id,
                intent.key_id,
                intent.resource,
                intent.fence,
                proof or "",
                intent.expected_version,
                intent.contract_generation,
                intent.revocation_epoch,
            )
        )
        if (
            signed.canonical() != intent.canonical()
            or self._check(signed, context) is not None
            or not self.writer_authenticator.verify(signed, context)
        ):
            return Result.AUTHENTICATION_FAILED
        try:
            self.conn.execute("BEGIN IMMEDIATE")
            lease = self.conn.execute(
                "SELECT * FROM leases WHERE installation_id=? AND project_id=? AND resource=? AND owner=? AND epoch=?",
                (self.scope.installation_id, self.scope.project_id, context.resource, context.writer_id, context.fence),
            ).fetchone()
            if not lease or lease["expires_at"] <= self.clock():
                self.conn.rollback()
                return Result.LEASE_EXPIRED if lease else Result.STALE_FENCE
            head = self.conn.execute(
                "SELECT generation,revocation_epoch FROM contract_heads WHERE installation_id=? AND project_id=? AND contract_id=?",
                (self.scope.installation_id, self.scope.project_id, amendment.new_contract.contract_id),
            ).fetchone()
            stored = self.conn.execute(
                "SELECT document FROM contract_versions WHERE installation_id=? AND project_id=? AND contract_id=? AND generation=?",
                (
                    self.scope.installation_id,
                    self.scope.project_id,
                    amendment.new_contract.contract_id,
                    expected_generation,
                ),
            ).fetchone()
            if (
                not head
                or tuple(head) != (expected_generation, expected_revocation_epoch)
                or not stored
                or json.loads(stored[0]) != amendment.prior_contract.to_dict()
            ):
                self.conn.rollback()
                return Result.CAS_CONFLICT
            last = self.conn.execute(
                "SELECT event_hash FROM events WHERE installation_id=? AND project_id=? ORDER BY sequence DESC LIMIT 1",
                (self.scope.installation_id, self.scope.project_id),
            ).fetchone()
            previous = last[0] if last else "GENESIS"
            sequence = self.conn.execute(
                "SELECT COALESCE(MAX(sequence),0)+1 FROM events WHERE installation_id=? AND project_id=?",
                (self.scope.installation_id, self.scope.project_id),
            ).fetchone()[0]
            event_id = uuid.uuid4().hex
            now = self.clock()
            payload = json.dumps(intent.payload, sort_keys=True, separators=(",", ":"))
            fields = [
                1,
                self.scope.installation_id,
                self.scope.project_id,
                sequence,
                now,
                event_id,
                "contract",
                expected_generation + 1,
                "contract.advance",
                payload,
                previous,
                context.writer_id,
                context.key_id,
                context.resource,
                context.fence,
                signed.proof,
            ]
            event_hash = hashlib.sha256(json.dumps(fields, separators=(",", ":")).encode()).hexdigest()
            auth_tag = self.integrity_signer.sign(json.dumps(fields + [event_hash], separators=(",", ":")).encode())
            self.conn.execute(
                "INSERT INTO events(installation_id,project_id,sequence,event_id,server_time,aggregate,version,kind,payload,previous_hash,event_hash,writer_id,key_id,resource,fence,writer_proof,auth_tag,encoding_version,contract_id,contract_generation,revocation_epoch) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                (
                    self.scope.installation_id,
                    self.scope.project_id,
                    sequence,
                    event_id,
                    now,
                    "contract",
                    expected_generation + 1,
                    "contract.advance",
                    payload,
                    previous,
                    event_hash,
                    context.writer_id,
                    context.key_id,
                    context.resource,
                    context.fence,
                    signed.proof,
                    auth_tag,
                    1,
                    amendment.new_contract.contract_id,
                    amendment.new_contract.generation,
                    amendment.new_contract.revocation_epoch,
                ),
            )
            self._stage("after_event_insert")
            self.conn.execute(
                "INSERT OR REPLACE INTO projections VALUES(?,?,?,?,?,?,?,?)",
                (
                    self.scope.installation_id,
                    self.scope.project_id,
                    "contract",
                    expected_generation + 1,
                    json.dumps(intent.payload, sort_keys=True, separators=(",", ":")),
                    self.reducer.version,
                    sequence,
                    event_hash,
                ),
            )
            self._stage("after_projection")
            self._stage("after_event")
            encoded = json.dumps(amendment.new_contract.to_dict(), sort_keys=True, separators=(",", ":"))
            self.conn.execute(
                "INSERT INTO contract_versions VALUES(?,?,?,?,?,?)",
                (
                    self.scope.installation_id,
                    self.scope.project_id,
                    amendment.new_contract.contract_id,
                    amendment.new_contract.generation,
                    encoded,
                    amendment.new_contract.revocation_epoch,
                ),
            )
            self._stage("after_contract_version")
            self.conn.execute(
                "UPDATE contract_heads SET generation=?,revocation_epoch=? WHERE installation_id=? AND project_id=? AND contract_id=? AND generation=? AND revocation_epoch=?",
                (
                    amendment.new_contract.generation,
                    amendment.new_contract.revocation_epoch,
                    self.scope.installation_id,
                    self.scope.project_id,
                    amendment.new_contract.contract_id,
                    expected_generation,
                    expected_revocation_epoch,
                ),
            )
            self._stage("after_contract_head")
            self.conn.execute(
                "UPDATE inbox SET authority_state='STALE' WHERE installation_id=? AND project_id=? AND contract_id=? AND (contract_generation<? OR revocation_epoch<?)",
                (
                    self.scope.installation_id,
                    self.scope.project_id,
                    amendment.new_contract.contract_id,
                    amendment.new_contract.generation,
                    amendment.new_contract.revocation_epoch,
                ),
            )
            self.conn.execute(
                "UPDATE outbox SET status=CASE WHEN status IN ('PENDING','RETRY_WAIT') THEN 'POISON' ELSE status END,reconciliation_required=CASE WHEN status='LEASED' THEN 1 ELSE reconciliation_required END WHERE installation_id=? AND project_id=? AND contract_id=? AND (contract_generation<? OR revocation_epoch<?) AND status NOT IN ('SENT','POISON')",
                (
                    self.scope.installation_id,
                    self.scope.project_id,
                    amendment.new_contract.contract_id,
                    amendment.new_contract.generation,
                    amendment.new_contract.revocation_epoch,
                ),
            )
            self._stage("after_authority_reconciliation")
            self.conn.execute(
                "INSERT INTO outbox(installation_id,project_id,message_id,event_id,status,attempts,contract_id,contract_generation,revocation_epoch,reconciliation_required) VALUES(?,?,?,?,?,?,?,?,?,?)",
                (
                    self.scope.installation_id,
                    self.scope.project_id,
                    event_id,
                    event_id,
                    "PENDING",
                    0,
                    amendment.new_contract.contract_id,
                    amendment.new_contract.generation,
                    amendment.new_contract.revocation_epoch,
                    0,
                ),
            )
            self._stage("after_outbox")
            self._stage("before_commit")
            self.conn.commit()
            return Result.APPLIED
        except sqlite3.IntegrityError:
            self.conn.rollback()
            return Result.CAS_CONFLICT
        except Exception:
            self.conn.rollback()
            raise

    def rebuild_projections(self) -> None:
        self.verify_chain()
        versions = {
            row[0]
            for row in self.conn.execute(
                "SELECT DISTINCT reducer_version FROM projections WHERE installation_id=? AND project_id=?",
                (self.scope.installation_id, self.scope.project_id),
            )
        }
        if versions and versions != {self.reducer.version}:
            raise ValueError("reducer version mismatch")
        events = self.events()
        rebuilt = self.reducer.rebuild(events)
        self.conn.execute("BEGIN IMMEDIATE")
        try:
            self.conn.execute("CREATE TEMP TABLE rebuild_projection AS SELECT * FROM projections WHERE 0")
            for aggregate, value in rebuilt.items():
                event = next(row for row in reversed(events) if row["aggregate"] == aggregate)
                self.conn.execute(
                    "INSERT INTO rebuild_projection VALUES(?,?,?,?,?,?,?,?)",
                    (
                        self.scope.installation_id,
                        self.scope.project_id,
                        aggregate,
                        event["version"],
                        json.dumps(value, sort_keys=True, separators=(",", ":")),
                        self.reducer.version,
                        event["sequence"],
                        event["event_hash"],
                    ),
                )
            self.conn.execute(
                "DELETE FROM projections WHERE installation_id=? AND project_id=?",
                (self.scope.installation_id, self.scope.project_id),
            )
            self.conn.execute("INSERT INTO projections SELECT * FROM rebuild_projection")
            self.conn.execute("DROP TABLE rebuild_projection")
            self.conn.commit()
        except Exception:
            self.conn.rollback()
            raise

    def receive(self, message_id: str, draft: SignedEventDraft, context: WriterContext) -> AppendResult:
        return self.append(draft, context, message_id=message_id)

    def backup(self, target: str | Path, anchor_store: TrustedAnchorStore | None = None) -> Path:
        self.verify_chain(anchor_store)
        self.rebuild_projections()
        target = Path(target)
        if target.exists():
            raise FileExistsError(target)
        fd, tmp = tempfile.mkstemp(prefix=".backup-", dir=target.parent)
        os.close(fd)
        try:
            with sqlite3.connect(tmp) as dest:
                self.conn.backup(dest)
                if dest.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
                    raise ValueError(Result.RESTORE_INVALID.value)
            probe = SQLiteLedger(
                tmp,
                self.scope,
                writer_authenticator=self.writer_authenticator,
                integrity_signer=self.integrity_signer,
                reducer=self.reducer,
                clock=self.clock,
            )
            try:
                probe.verify_chain(anchor_store)
                probe.verify_checkpoints()
                probe.verify_projections()
            finally:
                probe.close()
            os.chmod(tmp, 0o600)
            os.link(tmp, target)
            os.unlink(tmp)
            return target
        except Exception:
            try:
                os.unlink(tmp)
            except FileNotFoundError:
                pass
            raise

    def prepare_restore(self, artifact: str | Path, anchor_store: TrustedAnchorStore | None = None) -> PreparedRestore:
        artifact = Path(artifact)
        if not artifact.is_file() or artifact == self.path:
            raise ValueError(Result.RESTORE_INVALID.value)
        try:
            probe = sqlite3.connect(f"file:{artifact}?mode=ro", uri=True)
            try:
                if probe.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
                    raise ValueError(Result.RESTORE_INVALID.value)
                row = probe.execute(
                    "SELECT installation_id,project_id FROM events ORDER BY sequence LIMIT 1"
                ).fetchone()
                if row and tuple(row) != (self.scope.installation_id, self.scope.project_id):
                    raise ValueError(Result.RESTORE_INVALID.value)
            finally:
                probe.close()
            verification = SQLiteLedger(
                artifact,
                self.scope,
                writer_authenticator=self.writer_authenticator,
                integrity_signer=self.integrity_signer,
                reducer=self.reducer,
                clock=self.clock,
            )
            try:
                verification.verify_chain(anchor_store)
                verification.verify_checkpoints()
                verification.verify_projections()
            finally:
                verification.close()
        except Exception as exc:
            raise ValueError(Result.RESTORE_INVALID.value) from exc
        digest = hashlib.sha256(artifact.read_bytes()).hexdigest()
        return PreparedRestore(
            artifact,
            digest,
            self.scope.installation_id,
            self.scope.project_id,
            uuid.uuid4().hex,
        )

    def activate_restore(self, prepared: PreparedRestore, quiescence_token: str) -> None:
        if (
            not self._closed
            or not isinstance(prepared, PreparedRestore)
            or not hmac.compare_digest(quiescence_token, prepared.quiescence_token)
        ):
            raise ValueError(Result.RESTORE_INVALID.value)
        if hashlib.sha256(prepared.artifact.read_bytes()).hexdigest() != prepared.digest:
            raise ValueError(Result.RESTORE_INVALID.value)
        os.replace(prepared.artifact, self.path)
        os.chmod(self.path, 0o600)


__all__ = [
    "AppendResult",
    "Checkpoint",
    "HMACIntegritySigner",
    "HMACWriterAuthenticator",
    "InvalidScopeError",
    "LedgerEvent",
    "Result",
    "SQLiteLedger",
    "SignedEventDraft",
    "StoreScope",
    "TrustedAnchorStore",
    "WriterContext",
]
