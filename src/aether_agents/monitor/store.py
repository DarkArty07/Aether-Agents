"""Private SQLite state for the Telegram monitor.

This module owns only monitor records.  It never opens a source SessionDB, Kanban DB or
observation projection.  Transactions are intentionally limited to local state claims
and receipts; callers perform model/network work after a claim has committed and before
they submit a separate receipt transaction.
"""

from __future__ import annotations

import hashlib
import json
import os
import secrets
import sqlite3
import stat
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Callable, Iterator, Mapping, Sequence

from aether_agents.paths import (
    FILE_MODE,
    UnsafeObservationPath,
    _open_private_directory,
    ensure_private_dir,
    harden_file,
)
from aether_agents.paths import state_root as resolve_state_root

from .models import (
    Delivery,
    DeliveryLease,
    DeliveryState,
    Lease,
    MonitorSettings,
    Narrative,
    Snapshot,
    WorkItem,
)

__all__ = [
    "DuplicateRecordError",
    "IdentityConflictError",
    "ImmutableRecordError",
    "LeaseLostError",
    "MonitorStore",
    "MonitorStoreError",
    "UnsafeMonitorPath",
]


UnsafeMonitorPath = UnsafeObservationPath

_SCHEMA_VERSION = "aether.telegram-monitor.state.v1"
_RETENTION_DAYS = 30
_MAX_SNAPSHOT_BYTES = 24_000
_MAX_NARRATIVE_BYTES = 24_000
_MAX_CURSOR_BYTES = 8_000
_MAX_ERROR_CLASS = 160
_MAX_ERROR_MESSAGE = 1_000
_MAX_ID = 160

_TERMINAL_DELIVERY_STATES = frozenset(
    {DeliveryState.CONFIRMED.value, DeliveryState.SUPPRESSED.value}
)
_UNRESOLVED_DELIVERY_STATES = frozenset(
    {
        DeliveryState.PENDING.value,
        DeliveryState.SENDING.value,
        DeliveryState.FAILED.value,
        DeliveryState.UNCERTAIN.value,
    }
)


class MonitorStoreError(RuntimeError):
    """Base class for monitor-owned state failures."""


class DuplicateRecordError(MonitorStoreError):
    """A unique monitor identity is already used by a different record."""


class ImmutableRecordError(MonitorStoreError):
    """An immutable monitor record was submitted with different content."""


class IdentityConflictError(MonitorStoreError):
    """A stable work key was presented with a different source identity."""


class LeaseLostError(MonitorStoreError):
    """A stale or duplicated worker attempted to commit a lease-owned receipt."""


_SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS settings (
    singleton INTEGER PRIMARY KEY CHECK (singleton = 1),
    schema_version TEXT NOT NULL,
    enabled INTEGER NOT NULL CHECK (enabled IN (0, 1)),
    native_job_id TEXT,
    profile_binding TEXT,
    destination_ref TEXT,
    first_enabled_at_utc TEXT,
    timezone TEXT NOT NULL,
    last_cutoff_utc TEXT,
    paused_at_utc TEXT,
    updated_at_utc TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS work_items (
    work_key TEXT PRIMARY KEY,
    project_id TEXT NOT NULL,
    project_name TEXT,
    origin_session_id TEXT NOT NULL,
    origin_session_title TEXT NOT NULL,
    contract_id TEXT,
    contract_version TEXT,
    contract_title TEXT,
    board_binding_json TEXT,
    first_seen_utc TEXT NOT NULL,
    started_at_utc TEXT,
    ended_at_utc TEXT,
    observed_state TEXT NOT NULL,
    source_cursor_json TEXT,
    final_outcome_delivery_marker TEXT,
    active INTEGER NOT NULL CHECK (active IN (0, 1)),
    last_seen_utc TEXT
);
CREATE INDEX IF NOT EXISTS idx_monitor_work_project ON work_items(project_id);
CREATE INDEX IF NOT EXISTS idx_monitor_work_active ON work_items(active);

CREATE TRIGGER IF NOT EXISTS monitor_work_identity_immutable
BEFORE UPDATE OF work_key, project_id, origin_session_id, contract_id,
                 contract_version, board_binding_json, first_seen_utc ON work_items
BEGIN
    SELECT RAISE(ABORT, 'monitor work identity is immutable');
END;

CREATE TABLE IF NOT EXISTS snapshots (
    report_id TEXT PRIMARY KEY,
    cutoff_utc TEXT NOT NULL UNIQUE,
    previous_cutoff_utc TEXT,
    collected_at_utc TEXT NOT NULL,
    watermarks_json TEXT NOT NULL,
    payload_json TEXT NOT NULL,
    coverage_gaps_json TEXT NOT NULL,
    digest TEXT NOT NULL,
    resolved_at_utc TEXT
);
CREATE INDEX IF NOT EXISTS idx_monitor_snapshots_cutoff ON snapshots(cutoff_utc);

CREATE TRIGGER IF NOT EXISTS monitor_snapshot_immutable
BEFORE UPDATE OF report_id, cutoff_utc, previous_cutoff_utc, collected_at_utc,
                 watermarks_json, payload_json, coverage_gaps_json, digest ON snapshots
BEGIN
    SELECT RAISE(ABORT, 'monitor snapshot is immutable');
END;

CREATE TABLE IF NOT EXISTS narratives (
    report_id TEXT PRIMARY KEY REFERENCES snapshots(report_id) ON DELETE CASCADE,
    structured_result_json TEXT,
    narrator_session_id TEXT,
    attempt_status TEXT NOT NULL,
    created_at_utc TEXT NOT NULL,
    updated_at_utc TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS deliveries (
    report_id TEXT NOT NULL REFERENCES snapshots(report_id) ON DELETE CASCADE,
    part_index INTEGER NOT NULL CHECK (part_index >= 0),
    text_hash TEXT NOT NULL,
    state TEXT NOT NULL CHECK (state IN ('pending', 'sending', 'confirmed', 'failed', 'uncertain', 'suppressed')),
    attempts INTEGER NOT NULL CHECK (attempts >= 0),
    created_at_utc TEXT NOT NULL,
    updated_at_utc TEXT NOT NULL,
    last_error_class TEXT,
    last_error_message TEXT,
    message_id TEXT,
    lease_owner TEXT,
    lease_token TEXT,
    PRIMARY KEY (report_id, part_index)
);
CREATE INDEX IF NOT EXISTS idx_monitor_deliveries_state ON deliveries(state);

CREATE TRIGGER IF NOT EXISTS monitor_delivery_identity_immutable
BEFORE UPDATE OF report_id, part_index, text_hash ON deliveries
BEGIN
    SELECT RAISE(ABORT, 'monitor delivery identity is immutable');
END;

CREATE TABLE IF NOT EXISTS leases (
    lease_key TEXT PRIMARY KEY,
    lease_kind TEXT NOT NULL,
    owner_id TEXT NOT NULL,
    token TEXT NOT NULL UNIQUE,
    acquired_at_utc TEXT NOT NULL,
    expires_at_utc TEXT NOT NULL,
    owner_pid INTEGER NOT NULL,
    report_id TEXT,
    part_index INTEGER
);
CREATE INDEX IF NOT EXISTS idx_monitor_leases_expiry ON leases(expires_at_utc);
"""


def _safe_text(
    value: Any, field: str, *, allow_none: bool = False, limit: int = _MAX_ID
) -> str | None:
    if value is None and allow_none:
        return None
    if not isinstance(value, str) or not value or len(value) > limit:
        raise ValueError(f"{field} must be a non-empty string of at most {limit} characters")
    if any(ord(character) < 0x20 or ord(character) == 0x7F for character in value):
        raise ValueError(f"{field} contains a control character")
    return value


def _safe_id(value: Any, field: str) -> str:
    result = _safe_text(value, field)
    assert result is not None
    if "/" in result or "\\" in result or result in {".", ".."}:
        raise UnsafeMonitorPath(f"{field} cannot contain a path separator")
    return result


def _utc_text(value: str | datetime | None, field: str, *, allow_none: bool = False) -> str | None:
    if value is None and allow_none:
        return None
    if isinstance(value, datetime):
        parsed = value
    elif isinstance(value, str) and value:
        try:
            parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError as exc:
            raise ValueError(f"{field} must be an ISO-8601 timestamp") from exc
    else:
        raise ValueError(f"{field} must be a timezone-aware timestamp")
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError(f"{field} must include a timezone")
    return parsed.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ")


def _parse_utc(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError("timestamp must include a timezone")
    return parsed.astimezone(timezone.utc)


def _json_text(value: Any, field: str, *, limit: int) -> str:
    try:
        encoded = json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        )
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{field} must be finite JSON") from exc
    if len(encoded) > limit:
        raise ValueError(f"{field} exceeds its bounded size")
    return encoded


def _json_object_text(value: Any, field: str, *, limit: int) -> str:
    if not isinstance(value, Mapping) or any(not isinstance(key, str) or not key for key in value):
        raise ValueError(f"{field} must be a JSON object with string keys")
    return _json_text(value, field, limit=limit)


def _json_value(encoded: str | None, field: str, *, default: Any = None) -> Any:
    if encoded is None:
        return default
    try:
        return json.loads(encoded)
    except json.JSONDecodeError as exc:  # pragma: no cover - only corrupt on-disk state
        raise MonitorStoreError(f"invalid persisted {field}") from exc


def _canonical_digest(encoded: str) -> str:
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def _now_from(clock: Callable[[], datetime]) -> str:
    value = clock()
    result = _utc_text(value, "clock")
    assert result is not None
    return result


def _process_alive(process_id: int | None) -> bool:
    """Return whether a lease owner's process still exists on this host."""
    if not isinstance(process_id, int) or process_id <= 0:
        return False
    if os.name != "posix":  # pragma: no cover - Windows has no POSIX lease probe
        return process_id == os.getpid()
    if process_id == os.getpid():
        return True
    try:
        os.kill(process_id, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    except OSError:
        return False
    return True


def _delivery_state(value: str) -> DeliveryState:
    try:
        return DeliveryState(value)
    except ValueError as exc:  # pragma: no cover - protected by SQLite CHECK
        raise MonitorStoreError("invalid persisted delivery state") from exc


class MonitorStore:
    """A private, transactionally fenced monitor state database.

    Each operation opens a short-lived connection.  In particular, lease claims and
    receipts commit before a caller performs any external model or transport call.
    """

    def __init__(
        self,
        state_root: Path | str | None = None,
        *,
        clock: Callable[[], datetime] | None = None,
        retention_days: int = _RETENTION_DAYS,
    ) -> None:
        if retention_days < 1:
            raise ValueError("retention_days must be positive")
        self.state_root = resolve_state_root(state_root)
        self.monitor_dir = self.state_root / "monitor"
        self.db_path = self.monitor_dir / "monitor.sqlite3"
        self.clock = clock or (lambda: datetime.now(timezone.utc))
        self.retention_days = retention_days
        ensure_private_dir(self.state_root)
        ensure_private_dir(self.monitor_dir)
        self._bootstrap()
        self.recover_expired()

    # -- secure SQLite opening -------------------------------------------------

    def _harden_sidecars(self) -> None:
        for suffix in ("-wal", "-shm"):
            candidate = self.db_path.with_name(self.db_path.name + suffix)
            harden_file(candidate)

    def _connect(self) -> sqlite3.Connection:
        """Connect through a verified singly-linked inode on POSIX."""
        self._harden_sidecars()
        connection: sqlite3.Connection | None = None
        if os.name != "posix":  # pragma: no cover - release CI exercises POSIX
            if not self.db_path.exists():
                self.db_path.touch(mode=FILE_MODE)
            harden_file(self.db_path)
            connection = sqlite3.connect(str(self.db_path), timeout=5.0, check_same_thread=False)
        else:
            parent_descriptor = _open_private_directory(self.db_path.parent)
            descriptor = -1
            try:
                flags = os.O_RDWR | getattr(os, "O_CLOEXEC", 0) | getattr(os, "O_NOFOLLOW", 0)
                try:
                    descriptor = os.open(self.db_path.name, flags, dir_fd=parent_descriptor)
                except FileNotFoundError:
                    descriptor = os.open(
                        self.db_path.name,
                        flags | os.O_CREAT | os.O_EXCL,
                        FILE_MODE,
                        dir_fd=parent_descriptor,
                    )
                opened = os.fstat(descriptor)
                named = os.stat(self.db_path.name, dir_fd=parent_descriptor, follow_symlinks=False)
                if (
                    not stat.S_ISREG(opened.st_mode)
                    or opened.st_nlink != 1
                    or (named.st_dev, named.st_ino) != (opened.st_dev, opened.st_ino)
                ):
                    raise UnsafeMonitorPath("monitor database is not a private singly-linked file")
                os.fchmod(descriptor, FILE_MODE)
                proc_path = Path("/proc/self/fd") / str(descriptor)
                connection = sqlite3.connect(
                    f"file:{proc_path}?mode=rw",
                    uri=True,
                    timeout=5.0,
                    check_same_thread=False,
                )
                reopened = os.fstat(descriptor)
                current = os.stat(
                    self.db_path.name,
                    dir_fd=parent_descriptor,
                    follow_symlinks=False,
                )
                if (current.st_dev, current.st_ino) != (reopened.st_dev, reopened.st_ino):
                    raise UnsafeMonitorPath("monitor database changed during SQLite open")
                connection.row_factory = sqlite3.Row
            except OSError as exc:
                if connection is not None:
                    connection.close()
                raise UnsafeMonitorPath("monitor database is not a safe regular file") from exc
            except Exception:
                if connection is not None:
                    connection.close()
                raise
            finally:
                if descriptor >= 0:
                    os.close(descriptor)
                os.close(parent_descriptor)
            assert connection is not None

        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        connection.execute("PRAGMA busy_timeout = 5000")
        return connection

    def _bootstrap(self) -> None:
        connection = self._connect()
        try:
            connection.execute("PRAGMA journal_mode = WAL")
            connection.executescript(_SCHEMA_SQL)
            now = _now_from(self.clock)
            connection.execute(
                """
                INSERT OR IGNORE INTO settings
                (singleton, schema_version, enabled, timezone, updated_at_utc)
                VALUES (1, ?, 0, 'UTC', ?)
                """,
                (_SCHEMA_VERSION, now),
            )
            connection.commit()
        finally:
            connection.close()
        self._harden_sidecars()
        harden_file(self.db_path)

    @contextmanager
    def _read(self) -> Iterator[sqlite3.Connection]:
        connection = self._connect()
        try:
            yield connection
        finally:
            connection.close()

    @contextmanager
    def _write(self) -> Iterator[sqlite3.Connection]:
        connection = self._connect()
        try:
            connection.execute("BEGIN IMMEDIATE")
            yield connection
            connection.commit()
        except BaseException:
            connection.rollback()
            raise
        finally:
            connection.close()

    # -- settings -------------------------------------------------------------

    @staticmethod
    def _settings_from_row(row: sqlite3.Row) -> MonitorSettings:
        return MonitorSettings(
            schema_version=row["schema_version"],
            enabled=bool(row["enabled"]),
            native_job_id=row["native_job_id"],
            profile_binding=row["profile_binding"],
            destination_ref=row["destination_ref"],
            first_enabled_at_utc=row["first_enabled_at_utc"],
            timezone=row["timezone"],
            last_cutoff_utc=row["last_cutoff_utc"],
            paused_at_utc=row["paused_at_utc"],
            updated_at_utc=row["updated_at_utc"],
        )

    def get_settings(self) -> MonitorSettings:
        with self._read() as connection:
            row = connection.execute("SELECT * FROM settings WHERE singleton = 1").fetchone()
        if row is None:  # pragma: no cover - bootstrap always installs the singleton
            raise MonitorStoreError("monitor settings row is missing")
        return self._settings_from_row(row)

    def configure(
        self,
        *,
        native_job_id: str | None,
        profile_binding: str | None,
        destination_ref: str | None,
        timezone_name: str = "UTC",
        timezone: str | None = None,
    ) -> MonitorSettings:
        """Persist the exact native binding without changing enabled state."""
        job = _safe_text(native_job_id, "native_job_id", allow_none=True)
        profile = _safe_text(profile_binding, "profile_binding", allow_none=True)
        destination = _safe_text(destination_ref, "destination_ref", allow_none=True)
        selected_timezone = timezone if timezone is not None else timezone_name
        zone = _safe_text(selected_timezone, "timezone", limit=128)
        assert zone is not None
        now = _now_from(self.clock)
        with self._write() as connection:
            connection.execute(
                """
                UPDATE settings
                SET native_job_id = ?, profile_binding = ?, destination_ref = ?,
                    timezone = ?, updated_at_utc = ?
                WHERE singleton = 1
                """,
                (job, profile, destination, zone, now),
            )
            row = connection.execute("SELECT * FROM settings WHERE singleton = 1").fetchone()
        assert row is not None
        return self._settings_from_row(row)

    def set_enabled(self, enabled: bool) -> MonitorSettings:
        """Commit the monitor switch before any caller pauses/resumes native scheduling."""
        if not isinstance(enabled, bool):
            raise TypeError("enabled must be a bool")
        now = _now_from(self.clock)
        with self._write() as connection:
            row = connection.execute("SELECT * FROM settings WHERE singleton = 1").fetchone()
            if row is None:  # pragma: no cover
                raise MonitorStoreError("monitor settings row is missing")
            first_enabled = row["first_enabled_at_utc"] or (now if enabled else None)
            paused_at = None if enabled else now
            connection.execute(
                """
                UPDATE settings
                SET enabled = ?, first_enabled_at_utc = ?, paused_at_utc = ?,
                    updated_at_utc = ?
                WHERE singleton = 1
                """,
                (int(enabled), first_enabled, paused_at, now),
            )
            result = connection.execute("SELECT * FROM settings WHERE singleton = 1").fetchone()
        assert result is not None
        return self._settings_from_row(result)

    disable_before_pause = set_enabled

    def set_last_cutoff(self, cutoff_utc: str | datetime | None) -> MonitorSettings:
        cutoff = _utc_text(cutoff_utc, "cutoff_utc", allow_none=True)
        now = _now_from(self.clock)
        with self._write() as connection:
            row = connection.execute(
                "SELECT last_cutoff_utc FROM settings WHERE singleton = 1"
            ).fetchone()
            if row is None:  # pragma: no cover
                raise MonitorStoreError("monitor settings row is missing")
            existing = row["last_cutoff_utc"]
            if existing is not None and (
                cutoff is None or _parse_utc(cutoff) < _parse_utc(existing)
            ):
                raise ValueError("last cutoff cannot move backwards")
            connection.execute(
                "UPDATE settings SET last_cutoff_utc = ?, updated_at_utc = ? WHERE singleton = 1",
                (cutoff, now),
            )
        return self.get_settings()

    update_last_cutoff = set_last_cutoff

    # -- work items -----------------------------------------------------------

    @staticmethod
    def _work_from_row(row: sqlite3.Row) -> WorkItem:
        board_binding = _json_value(row["board_binding_json"], "board binding")
        if board_binding is not None and not isinstance(board_binding, Mapping):
            raise MonitorStoreError("persisted board binding is not an object")
        return WorkItem(
            work_key=row["work_key"],
            project_id=row["project_id"],
            project_name=row["project_name"],
            origin_session_id=row["origin_session_id"],
            origin_session_title=row["origin_session_title"],
            contract_id=row["contract_id"],
            contract_version=row["contract_version"],
            contract_title=row["contract_title"],
            board_binding=board_binding,
            first_seen_utc=row["first_seen_utc"],
            started_at_utc=row["started_at_utc"],
            ended_at_utc=row["ended_at_utc"],
            observed_state=row["observed_state"],
            source_cursor=_json_value(row["source_cursor_json"], "source cursor"),
            final_outcome_delivery_marker=row["final_outcome_delivery_marker"],
            active=bool(row["active"]),
            last_seen_utc=row["last_seen_utc"],
        )

    @staticmethod
    def _validate_work(item: WorkItem) -> tuple[Any, ...]:
        work_key = _safe_id(item.work_key, "work_key")
        project_id = _safe_id(item.project_id, "project_id")
        project_name = _safe_text(item.project_name, "project_name", allow_none=True)
        session_id = _safe_id(item.origin_session_id, "origin_session_id")
        session_title = _safe_text(item.origin_session_title, "origin_session_title")
        first_seen = _utc_text(item.first_seen_utc, "first_seen_utc")
        started = _utc_text(item.started_at_utc, "started_at_utc", allow_none=True)
        ended = _utc_text(item.ended_at_utc, "ended_at_utc", allow_none=True)
        state = _safe_text(item.observed_state, "observed_state", limit=80)
        marker = _safe_text(
            item.final_outcome_delivery_marker,
            "final_outcome_delivery_marker",
            allow_none=True,
        )
        last_seen = _utc_text(item.last_seen_utc, "last_seen_utc", allow_none=True)
        if not isinstance(item.active, bool):
            raise TypeError("active must be a bool")
        board_json = None
        if item.board_binding is not None:
            if not isinstance(item.board_binding, Mapping):
                raise ValueError("board_binding must be a JSON object")
            board_json = _json_object_text(
                item.board_binding, "board_binding", limit=_MAX_CURSOR_BYTES
            )
        cursor_json = (
            None
            if item.source_cursor is None
            else _json_text(item.source_cursor, "source_cursor", limit=_MAX_CURSOR_BYTES)
        )
        values = (
            work_key,
            project_id,
            project_name,
            session_id,
            session_title,
            _safe_id(item.contract_id, "contract_id") if item.contract_id is not None else None,
            _safe_text(item.contract_version, "contract_version", allow_none=True, limit=64),
            _safe_text(item.contract_title, "contract_title", allow_none=True),
            board_json,
            first_seen,
            started,
            ended,
            state,
            cursor_json,
            marker,
            int(item.active),
            last_seen,
        )
        return values

    def upsert_work_item(self, item: WorkItem) -> WorkItem:
        values = self._validate_work(item)
        work_key = values[0]
        with self._write() as connection:
            existing = connection.execute(
                "SELECT * FROM work_items WHERE work_key = ?", (work_key,)
            ).fetchone()
            if existing is not None:
                immutable_columns = (
                    "project_id",
                    "origin_session_id",
                    "contract_id",
                    "contract_version",
                    "board_binding_json",
                    "first_seen_utc",
                )
                incoming = dict(
                    zip(
                        (
                            "work_key",
                            "project_id",
                            "project_name",
                            "origin_session_id",
                            "origin_session_title",
                            "contract_id",
                            "contract_version",
                            "contract_title",
                            "board_binding_json",
                            "first_seen_utc",
                            "started_at_utc",
                            "ended_at_utc",
                            "observed_state",
                            "source_cursor_json",
                            "final_outcome_delivery_marker",
                            "active",
                            "last_seen_utc",
                        ),
                        values,
                    )
                )
                for column in immutable_columns:
                    if existing[column] != incoming[column]:
                        raise IdentityConflictError(
                            f"work key {work_key!r} changed its immutable {column}"
                        )
                connection.execute(
                    """
                    UPDATE work_items
                    SET project_name = ?, origin_session_title = ?, contract_title = ?,
                        started_at_utc = ?, ended_at_utc = ?, observed_state = ?,
                        source_cursor_json = ?, final_outcome_delivery_marker = ?,
                        active = ?, last_seen_utc = ?
                    WHERE work_key = ?
                    """,
                    (
                        values[2],
                        values[4],
                        values[7],
                        values[10],
                        values[11],
                        values[12],
                        values[13],
                        values[14],
                        values[15],
                        values[16],
                        work_key,
                    ),
                )
            else:
                connection.execute(
                    """
                    INSERT INTO work_items
                    (work_key, project_id, project_name, origin_session_id, origin_session_title,
                     contract_id, contract_version, contract_title, board_binding_json,
                     first_seen_utc, started_at_utc, ended_at_utc, observed_state,
                     source_cursor_json, final_outcome_delivery_marker, active, last_seen_utc)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    values,
                )
            row = connection.execute(
                "SELECT * FROM work_items WHERE work_key = ?", (work_key,)
            ).fetchone()
        assert row is not None
        return self._work_from_row(row)

    enroll_work_item = upsert_work_item

    def get_work_item(self, work_key: str) -> WorkItem | None:
        key = _safe_id(work_key, "work_key")
        with self._read() as connection:
            row = connection.execute(
                "SELECT * FROM work_items WHERE work_key = ?", (key,)
            ).fetchone()
        return None if row is None else self._work_from_row(row)

    def list_work_items(self, *, active_only: bool = False) -> tuple[WorkItem, ...]:
        query = "SELECT * FROM work_items"
        parameters: tuple[Any, ...] = ()
        if active_only:
            query += " WHERE active = 1"
        query += " ORDER BY first_seen_utc, work_key"
        with self._read() as connection:
            rows = connection.execute(query, parameters).fetchall()
        return tuple(self._work_from_row(row) for row in rows)

    def mark_final_outcome_delivery(self, work_key: str, marker: str | None) -> WorkItem:
        key = _safe_id(work_key, "work_key")
        safe_marker = _safe_text(marker, "marker", allow_none=True)
        with self._write() as connection:
            connection.execute(
                "UPDATE work_items SET final_outcome_delivery_marker = ? WHERE work_key = ?",
                (safe_marker, key),
            )
            row = connection.execute(
                "SELECT * FROM work_items WHERE work_key = ?", (key,)
            ).fetchone()
        if row is None:
            raise KeyError(key)
        return self._work_from_row(row)

    # -- snapshots and narratives --------------------------------------------

    @staticmethod
    def _snapshot_from_row(row: sqlite3.Row) -> Snapshot:
        watermarks = _json_value(row["watermarks_json"], "watermarks")
        payload = _json_value(row["payload_json"], "snapshot payload")
        gaps = _json_value(row["coverage_gaps_json"], "coverage gaps")
        if not isinstance(watermarks, Mapping) or not isinstance(payload, Mapping):
            raise MonitorStoreError("persisted snapshot object is not a mapping")
        if not isinstance(gaps, list) or not all(isinstance(item, str) for item in gaps):
            raise MonitorStoreError("persisted coverage gaps are invalid")
        return Snapshot(
            report_id=row["report_id"],
            cutoff_utc=row["cutoff_utc"],
            previous_cutoff_utc=row["previous_cutoff_utc"],
            collected_at_utc=row["collected_at_utc"],
            watermarks=watermarks,
            payload=payload,
            coverage_gaps=tuple(gaps),
            digest=row["digest"],
            resolved_at_utc=row["resolved_at_utc"],
        )

    def create_snapshot(
        self,
        *,
        cutoff_utc: str | datetime,
        previous_cutoff_utc: str | datetime | None,
        collected_at_utc: str | datetime,
        watermarks: Mapping[str, Any],
        payload: Mapping[str, Any],
        coverage_gaps: Sequence[str] = (),
        report_id: str | None = None,
        lease: Lease | str | None = None,
    ) -> Snapshot:
        cutoff = _utc_text(cutoff_utc, "cutoff_utc")
        previous = _utc_text(previous_cutoff_utc, "previous_cutoff_utc", allow_none=True)
        collected = _utc_text(collected_at_utc, "collected_at_utc")
        assert cutoff is not None and collected is not None
        if previous is not None and _parse_utc(previous) >= _parse_utc(cutoff):
            raise ValueError("previous cutoff must precede the snapshot cutoff")
        if not isinstance(watermarks, Mapping):
            raise ValueError("watermarks must be a JSON object")
        if not isinstance(payload, Mapping):
            raise ValueError("payload must be a JSON object")
        if not isinstance(coverage_gaps, Sequence) or isinstance(coverage_gaps, (str, bytes)):
            raise ValueError("coverage_gaps must be a sequence of strings")
        gaps = tuple(_safe_text(item, "coverage_gap", limit=1_200) for item in coverage_gaps)
        if any(item is None for item in gaps):  # pragma: no cover - _safe_text rejects it
            raise ValueError("coverage_gaps cannot contain null")
        payload_json = _json_object_text(payload, "snapshot payload", limit=_MAX_SNAPSHOT_BYTES)
        watermarks_json = _json_object_text(watermarks, "watermarks", limit=_MAX_CURSOR_BYTES)
        gaps_json = _json_text(gaps, "coverage_gaps", limit=_MAX_CURSOR_BYTES)
        digest = _canonical_digest(payload_json)
        identifier = (
            _safe_id(report_id, "report_id")
            if report_id is not None
            else ("rpt_" + secrets.token_hex(16))
        )
        token: str | None = None
        owner_id: str | None = None
        if isinstance(lease, Lease):
            if lease.lease_kind != "collection":
                raise ValueError("snapshot persistence requires a collection lease")
            token = lease.token
            owner_id = lease.owner_id
        elif isinstance(lease, str) and lease:
            token = lease
        now = _now_from(self.clock)
        with self._write() as connection:
            existing = connection.execute(
                "SELECT * FROM snapshots WHERE report_id = ?", (identifier,)
            ).fetchone()
            if existing is not None:
                raise ImmutableRecordError(f"snapshot {identifier!r} already exists")
            cutoff_existing = connection.execute(
                "SELECT report_id FROM snapshots WHERE cutoff_utc = ?", (cutoff,)
            ).fetchone()
            if cutoff_existing is not None:
                raise DuplicateRecordError(f"cutoff {cutoff!r} already has a snapshot")
            if token is None:
                raise LeaseLostError("snapshot persistence requires a current collection lease")
            setting = connection.execute(
                "SELECT enabled FROM settings WHERE singleton = 1"
            ).fetchone()
            if setting is None or not setting["enabled"]:
                raise LeaseLostError("monitor is disabled")
            self._recover_expired_in_tx(connection, now)
            lease_key = f"collection:{cutoff}"
            lease_row = connection.execute(
                "SELECT * FROM leases WHERE lease_key = ?", (lease_key,)
            ).fetchone()
            if lease_row is None:
                raise LeaseLostError("collection lease is no longer owned by this worker")
            if lease_row["token"] != token:
                raise LeaseLostError("collection lease has been acquired by another worker")
            if owner_id is not None and lease_row["owner_id"] != owner_id:
                raise LeaseLostError("collection lease owner mismatch")
            if _parse_utc(lease_row["expires_at_utc"]) <= _parse_utc(now):
                raise LeaseLostError("collection lease has expired")
            connection.execute(
                """
                INSERT INTO snapshots
                (report_id, cutoff_utc, previous_cutoff_utc, collected_at_utc,
                 watermarks_json, payload_json, coverage_gaps_json, digest, resolved_at_utc)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, NULL)
                """,
                (
                    identifier,
                    cutoff,
                    previous,
                    collected,
                    watermarks_json,
                    payload_json,
                    gaps_json,
                    digest,
                ),
            )
            connection.execute(
                "DELETE FROM leases WHERE lease_key = ? AND token = ?",
                (lease_key, token),
            )
            row = connection.execute(
                "SELECT * FROM snapshots WHERE report_id = ?", (identifier,)
            ).fetchone()
        assert row is not None
        return self._snapshot_from_row(row)

    def commit_snapshot(
        self,
        lease: Lease | str,
        *,
        cutoff_utc: str | datetime,
        previous_cutoff_utc: str | datetime | None,
        collected_at_utc: str | datetime,
        watermarks: Mapping[str, Any],
        payload: Mapping[str, Any],
        coverage_gaps: Sequence[str] = (),
        report_id: str | None = None,
    ) -> Snapshot:
        return self.create_snapshot(
            cutoff_utc=cutoff_utc,
            previous_cutoff_utc=previous_cutoff_utc,
            collected_at_utc=collected_at_utc,
            watermarks=watermarks,
            payload=payload,
            coverage_gaps=coverage_gaps,
            report_id=report_id,
            lease=lease,
        )

    commit_collection = commit_snapshot

    def get_snapshot(self, report_id: str) -> Snapshot | None:
        identifier = _safe_id(report_id, "report_id")
        with self._read() as connection:
            row = connection.execute(
                "SELECT * FROM snapshots WHERE report_id = ?", (identifier,)
            ).fetchone()
        return None if row is None else self._snapshot_from_row(row)

    def list_snapshots(self, *, limit: int | None = None) -> tuple[Snapshot, ...]:
        if limit is not None and (not isinstance(limit, int) or limit < 1):
            raise ValueError("limit must be positive")
        query = "SELECT * FROM snapshots ORDER BY cutoff_utc DESC"
        parameters: tuple[Any, ...] = ()
        if limit is not None:
            query += " LIMIT ?"
            parameters = (limit,)
        with self._read() as connection:
            rows = connection.execute(query, parameters).fetchall()
        return tuple(self._snapshot_from_row(row) for row in rows)

    def mark_snapshot_resolved(
        self,
        report_id: str,
        *,
        resolved_at_utc: str | datetime | None = None,
    ) -> Snapshot:
        """Mark an interval resolved only after every delivery is terminal."""
        identifier = _safe_id(report_id, "report_id")
        requested = (
            _utc_text(resolved_at_utc, "resolved_at_utc") if resolved_at_utc is not None else None
        )
        now = _now_from(self.clock)
        with self._write() as connection:
            row = connection.execute(
                "SELECT * FROM snapshots WHERE report_id = ?", (identifier,)
            ).fetchone()
            if row is None:
                raise KeyError(identifier)
            unresolved = connection.execute(
                """
                SELECT 1 FROM deliveries
                WHERE report_id = ? AND state IN ('pending', 'sending', 'failed', 'uncertain')
                LIMIT 1
                """,
                (identifier,),
            ).fetchone()
            if unresolved is not None:
                raise MonitorStoreError("snapshot has unresolved delivery parts")
            existing = row["resolved_at_utc"]
            target = requested or existing or now
            if existing is not None and target < existing:
                raise ValueError("snapshot resolution cannot move backwards")
            connection.execute(
                "UPDATE snapshots SET resolved_at_utc = ? WHERE report_id = ?",
                (target, identifier),
            )
            resolved_row = connection.execute(
                "SELECT * FROM snapshots WHERE report_id = ?", (identifier,)
            ).fetchone()
        assert resolved_row is not None
        return self._snapshot_from_row(resolved_row)

    resolve_snapshot = mark_snapshot_resolved

    @staticmethod
    def _narrative_from_row(row: sqlite3.Row) -> Narrative:
        result = _json_value(row["structured_result_json"], "narrative")
        if result is not None and not isinstance(result, Mapping):
            raise MonitorStoreError("persisted narrative is not an object")
        return Narrative(
            report_id=row["report_id"],
            structured_result=result,
            narrator_session_id=row["narrator_session_id"],
            attempt_status=row["attempt_status"],
            created_at_utc=row["created_at_utc"],
            updated_at_utc=row["updated_at_utc"],
        )

    def put_narrative(
        self,
        report_id: str,
        *,
        structured_result: Mapping[str, Any] | None,
        narrator_session_id: str | None,
        attempt_status: str,
    ) -> Narrative:
        identifier = _safe_id(report_id, "report_id")
        session_id = _safe_text(narrator_session_id, "narrator_session_id", allow_none=True)
        status = _safe_text(attempt_status, "attempt_status", limit=80)
        result_json = (
            None
            if structured_result is None
            else _json_object_text(
                structured_result, "structured_result", limit=_MAX_NARRATIVE_BYTES
            )
        )
        now = _now_from(self.clock)
        with self._write() as connection:
            if (
                connection.execute(
                    "SELECT 1 FROM snapshots WHERE report_id = ?", (identifier,)
                ).fetchone()
                is None
            ):
                raise KeyError(identifier)
            existing = connection.execute(
                "SELECT created_at_utc FROM narratives WHERE report_id = ?", (identifier,)
            ).fetchone()
            created = existing["created_at_utc"] if existing is not None else now
            connection.execute(
                """
                INSERT INTO narratives
                (report_id, structured_result_json, narrator_session_id, attempt_status,
                 created_at_utc, updated_at_utc)
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(report_id) DO UPDATE SET
                  structured_result_json = excluded.structured_result_json,
                  narrator_session_id = excluded.narrator_session_id,
                  attempt_status = excluded.attempt_status,
                  updated_at_utc = excluded.updated_at_utc
                """,
                (identifier, result_json, session_id, status, created, now),
            )
            row = connection.execute(
                "SELECT * FROM narratives WHERE report_id = ?", (identifier,)
            ).fetchone()
        assert row is not None
        return self._narrative_from_row(row)

    save_narrative = put_narrative

    def get_narrative(self, report_id: str) -> Narrative | None:
        identifier = _safe_id(report_id, "report_id")
        with self._read() as connection:
            row = connection.execute(
                "SELECT * FROM narratives WHERE report_id = ?", (identifier,)
            ).fetchone()
        return None if row is None else self._narrative_from_row(row)

    # -- outbox and leases ----------------------------------------------------

    @staticmethod
    def _delivery_from_row(row: sqlite3.Row) -> Delivery:
        return Delivery(
            report_id=row["report_id"],
            part_index=int(row["part_index"]),
            text_hash=row["text_hash"],
            state=_delivery_state(row["state"]),
            attempts=int(row["attempts"]),
            created_at_utc=row["created_at_utc"],
            updated_at_utc=row["updated_at_utc"],
            last_error_class=row["last_error_class"],
            last_error_message=row["last_error_message"],
            message_id=row["message_id"],
            lease_owner=row["lease_owner"],
            lease_token=row["lease_token"],
        )

    @staticmethod
    def _lease_from_row(row: sqlite3.Row) -> Lease:
        return Lease(
            lease_key=row["lease_key"],
            lease_kind=row["lease_kind"],
            owner_id=row["owner_id"],
            token=row["token"],
            acquired_at_utc=row["acquired_at_utc"],
            expires_at_utc=row["expires_at_utc"],
            report_id=row["report_id"],
            part_index=row["part_index"],
            owner_process_id=row["owner_pid"],
        )

    def enqueue_deliveries(self, report_id: str, parts: Sequence[str]) -> tuple[Delivery, ...]:
        identifier = _safe_id(report_id, "report_id")
        if isinstance(parts, (str, bytes)):
            raise ValueError("parts must be a sequence of strings")
        values = tuple(parts)
        for part in values:
            if not isinstance(part, str) or not part:
                raise ValueError("delivery parts must be non-empty strings")
            if len(part) > 3_500:
                raise ValueError("delivery parts must be at most 3500 Unicode characters")
        now = _now_from(self.clock)
        with self._write() as connection:
            if (
                connection.execute(
                    "SELECT 1 FROM snapshots WHERE report_id = ?", (identifier,)
                ).fetchone()
                is None
            ):
                raise KeyError(identifier)
            changed = False
            for index, part in enumerate(values):
                digest = hashlib.sha256(part.encode("utf-8")).hexdigest()
                existing = connection.execute(
                    """
                    SELECT text_hash FROM deliveries
                    WHERE report_id = ? AND part_index = ?
                    """,
                    (identifier, index),
                ).fetchone()
                if existing is not None:
                    if existing["text_hash"] != digest:
                        raise ImmutableRecordError(
                            f"delivery part {identifier!r}/{index} changed its text hash"
                        )
                    continue
                connection.execute(
                    """
                    INSERT INTO deliveries
                    (report_id, part_index, text_hash, state, attempts, created_at_utc, updated_at_utc)
                    VALUES (?, ?, ?, 'pending', 0, ?, ?)
                    """,
                    (identifier, index, digest, now, now),
                )
                changed = True
            if changed:
                connection.execute(
                    "UPDATE snapshots SET resolved_at_utc = NULL WHERE report_id = ?",
                    (identifier,),
                )
            rows = connection.execute(
                "SELECT * FROM deliveries WHERE report_id = ? ORDER BY part_index", (identifier,)
            ).fetchall()
        return tuple(self._delivery_from_row(row) for row in rows)

    def get_delivery(self, report_id: str, part_index: int) -> Delivery | None:
        identifier = _safe_id(report_id, "report_id")
        if not isinstance(part_index, int) or part_index < 0:
            raise ValueError("part_index must be a non-negative integer")
        with self._read() as connection:
            row = connection.execute(
                "SELECT * FROM deliveries WHERE report_id = ? AND part_index = ?",
                (identifier, part_index),
            ).fetchone()
        return None if row is None else self._delivery_from_row(row)

    def list_deliveries(self, report_id: str) -> tuple[Delivery, ...]:
        identifier = _safe_id(report_id, "report_id")
        with self._read() as connection:
            rows = connection.execute(
                "SELECT * FROM deliveries WHERE report_id = ? ORDER BY part_index", (identifier,)
            ).fetchall()
        return tuple(self._delivery_from_row(row) for row in rows)

    def _lease_times(self, ttl_seconds: float) -> tuple[str, str]:
        if not isinstance(ttl_seconds, (int, float)) or ttl_seconds <= 0:
            raise ValueError("lease TTL must be positive")
        acquired = _now_from(self.clock)
        parsed = _parse_utc(acquired)
        expires = _utc_text(parsed + timedelta(seconds=float(ttl_seconds)), "expires_at_utc")
        assert expires is not None
        return acquired, expires

    def acquire_collection_lease(
        self,
        cutoff_utc: str | datetime,
        *,
        owner_id: str,
        ttl_seconds: float = 120,
    ) -> Lease | None:
        cutoff = _utc_text(cutoff_utc, "cutoff_utc")
        assert cutoff is not None
        owner = _safe_id(owner_id, "owner_id")
        acquired, expires = self._lease_times(ttl_seconds)
        key = f"collection:{cutoff}"
        return self._acquire_lease(
            key,
            kind="collection",
            owner=owner,
            acquired=acquired,
            expires=expires,
            report_id=None,
            part_index=None,
            require_enabled=True,
        )

    def _acquire_lease(
        self,
        key: str,
        *,
        kind: str,
        owner: str,
        acquired: str,
        expires: str,
        report_id: str | None,
        part_index: int | None,
        require_enabled: bool,
    ) -> Lease | None:
        with self._write() as connection:
            self._recover_expired_in_tx(connection, acquired)
            if require_enabled:
                setting = connection.execute(
                    "SELECT enabled FROM settings WHERE singleton = 1"
                ).fetchone()
                if setting is None or not setting["enabled"]:
                    return None
            existing = connection.execute(
                "SELECT * FROM leases WHERE lease_key = ?", (key,)
            ).fetchone()
            if existing is not None and _parse_utc(existing["expires_at_utc"]) > _parse_utc(
                acquired
            ):
                return None
            if existing is not None:
                connection.execute("DELETE FROM leases WHERE lease_key = ?", (key,))
            token = secrets.token_hex(16)
            connection.execute(
                """
                INSERT INTO leases
                (lease_key, lease_kind, owner_id, token, acquired_at_utc, expires_at_utc,
                 owner_pid, report_id, part_index)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (key, kind, owner, token, acquired, expires, os.getpid(), report_id, part_index),
            )
            row = connection.execute("SELECT * FROM leases WHERE token = ?", (token,)).fetchone()
        assert row is not None
        return self._lease_from_row(row)

    def claim_delivery(
        self,
        report_id: str,
        part_index: int,
        *,
        owner_id: str,
        ttl_seconds: float = 120,
    ) -> DeliveryLease | None:
        identifier = _safe_id(report_id, "report_id")
        if not isinstance(part_index, int) or part_index < 0:
            raise ValueError("part_index must be a non-negative integer")
        owner = _safe_id(owner_id, "owner_id")
        acquired, expires = self._lease_times(ttl_seconds)
        key = f"delivery:{identifier}:{part_index}"
        with self._write() as connection:
            self._recover_expired_in_tx(connection, acquired)
            setting = connection.execute(
                "SELECT enabled FROM settings WHERE singleton = 1"
            ).fetchone()
            if setting is None or not setting["enabled"]:
                return None
            delivery = connection.execute(
                """
                SELECT * FROM deliveries WHERE report_id = ? AND part_index = ?
                """,
                (identifier, part_index),
            ).fetchone()
            if delivery is None:
                raise KeyError(f"{identifier}/{part_index}")
            if delivery["state"] in {
                DeliveryState.CONFIRMED.value,
                DeliveryState.SUPPRESSED.value,
                DeliveryState.UNCERTAIN.value,
            }:
                return None
            existing = connection.execute(
                "SELECT * FROM leases WHERE lease_key = ?", (key,)
            ).fetchone()
            if existing is not None and _parse_utc(existing["expires_at_utc"]) > _parse_utc(
                acquired
            ):
                return None
            if existing is not None:
                connection.execute("DELETE FROM leases WHERE lease_key = ?", (key,))
            token = secrets.token_hex(16)
            connection.execute(
                """
                INSERT INTO leases
                (lease_key, lease_kind, owner_id, token, acquired_at_utc, expires_at_utc,
                 owner_pid, report_id, part_index)
                VALUES (?, 'delivery', ?, ?, ?, ?, ?, ?, ?)
                """,
                (key, owner, token, acquired, expires, os.getpid(), identifier, part_index),
            )
            connection.execute(
                """
                UPDATE deliveries
                SET state = 'sending', attempts = attempts + 1, updated_at_utc = ?,
                    lease_owner = ?, lease_token = ?, last_error_class = NULL,
                    last_error_message = NULL
                WHERE report_id = ? AND part_index = ?
                """,
                (acquired, owner, token, identifier, part_index),
            )
            connection.execute(
                "UPDATE snapshots SET resolved_at_utc = NULL WHERE report_id = ?", (identifier,)
            )
            row = connection.execute("SELECT * FROM leases WHERE token = ?", (token,)).fetchone()
        assert row is not None
        return self._lease_from_row(row)

    def can_dispatch_delivery(self, lease: Lease) -> bool:
        if lease.lease_kind != "delivery":
            raise ValueError("can_dispatch_delivery requires a delivery lease")
        now = _now_from(self.clock)
        with self._read() as connection:
            setting = connection.execute(
                "SELECT enabled FROM settings WHERE singleton = 1"
            ).fetchone()
            row = connection.execute(
                """
                SELECT d.state, d.lease_owner, d.lease_token,
                       l.owner_id, l.token, l.expires_at_utc,
                       l.report_id, l.part_index
                FROM deliveries AS d
                JOIN leases AS l ON l.report_id = d.report_id AND l.part_index = d.part_index
                WHERE l.lease_key = ?
                """,
                (lease.lease_key,),
            ).fetchone()
        return bool(
            setting is not None
            and setting["enabled"]
            and row is not None
            and row["state"] == DeliveryState.SENDING.value
            and row["lease_owner"] == lease.owner_id
            and row["lease_token"] == lease.token
            and row["owner_id"] == lease.owner_id
            and row["token"] == lease.token
            and row["report_id"] == lease.report_id
            and row["part_index"] == lease.part_index
            and _parse_utc(row["expires_at_utc"]) > _parse_utc(now)
        )

    def complete_delivery(
        self,
        lease: Lease,
        *,
        outcome: str | DeliveryState,
        message_id: str | None = None,
        error_class: str | None = None,
        error_message: str | None = None,
    ) -> Delivery:
        if lease.lease_kind != "delivery" or lease.report_id is None or lease.part_index is None:
            raise ValueError("complete_delivery requires a delivery lease")
        try:
            state = DeliveryState(outcome)
        except ValueError as exc:
            raise ValueError("invalid delivery outcome") from exc
        if state in {DeliveryState.PENDING, DeliveryState.SENDING}:
            raise ValueError("delivery receipt must be a terminal outcome")
        safe_message_id = _safe_text(message_id, "message_id", allow_none=True)
        if state is DeliveryState.CONFIRMED and safe_message_id is None:
            raise ValueError("confirmed delivery requires a message id")
        if state is not DeliveryState.CONFIRMED and safe_message_id is not None:
            raise ValueError("only a confirmed delivery may store a message id")
        safe_error_class = _safe_text(
            error_class, "error_class", allow_none=True, limit=_MAX_ERROR_CLASS
        )
        safe_error_message = _safe_text(
            error_message, "error_message", allow_none=True, limit=_MAX_ERROR_MESSAGE
        )
        now = _now_from(self.clock)
        updated: sqlite3.Row | None = None
        lease_lost = False
        with self._write() as connection:
            self._recover_expired_in_tx(connection, now)
            lease_row = connection.execute(
                "SELECT * FROM leases WHERE lease_key = ?", (lease.lease_key,)
            ).fetchone()
            if (
                lease_row is None
                or lease_row["token"] != lease.token
                or lease_row["owner_id"] != lease.owner_id
                or lease_row["report_id"] != lease.report_id
                or lease_row["part_index"] != lease.part_index
                or _parse_utc(lease_row["expires_at_utc"]) <= _parse_utc(now)
            ):
                lease_lost = True
            else:
                row = connection.execute(
                    "SELECT * FROM deliveries WHERE report_id = ? AND part_index = ?",
                    (lease.report_id, lease.part_index),
                ).fetchone()
                if row is None or row["state"] != DeliveryState.SENDING.value:
                    lease_lost = True
                else:
                    receipt_cursor = connection.execute(
                        """
                        UPDATE deliveries
                        SET state = ?, updated_at_utc = ?, last_error_class = ?,
                            last_error_message = ?, message_id = ?, lease_owner = NULL,
                            lease_token = NULL
                        WHERE report_id = ? AND part_index = ? AND lease_token = ?
                        """,
                        (
                            state.value,
                            now,
                            safe_error_class,
                            safe_error_message,
                            safe_message_id,
                            lease.report_id,
                            lease.part_index,
                            lease.token,
                        ),
                    )
                    if receipt_cursor.rowcount != 1:
                        lease_lost = True
                    else:
                        connection.execute(
                            "DELETE FROM leases WHERE lease_key = ?", (lease.lease_key,)
                        )
                        self._mark_snapshot_resolved_in_tx(connection, lease.report_id, now)
                        updated = connection.execute(
                            "SELECT * FROM deliveries WHERE report_id = ? AND part_index = ?",
                            (lease.report_id, lease.part_index),
                        ).fetchone()
        if lease_lost:
            raise LeaseLostError("delivery lease is no longer owned by this worker")
        assert updated is not None
        return self._delivery_from_row(updated)

    def suppress_delivery(self, lease: Lease, *, reason: str) -> Delivery:
        return self.complete_delivery(
            lease,
            outcome=DeliveryState.SUPPRESSED,
            error_class="monitor-disabled",
            error_message=reason,
        )

    def release_collection_lease(self, lease: Lease) -> bool:
        if lease.lease_kind != "collection":
            raise ValueError("release_collection_lease requires a collection lease")
        with self._write() as connection:
            cursor = connection.execute(
                "DELETE FROM leases WHERE lease_key = ? AND token = ?",
                (lease.lease_key, lease.token),
            )
        return cursor.rowcount == 1

    def _recover_expired_in_tx(
        self,
        connection: sqlite3.Connection,
        now: str,
        *,
        recover_dead: bool = True,
    ) -> int:
        rows = connection.execute("SELECT * FROM leases").fetchall()
        recovered = 0
        for lease in rows:
            expired = _parse_utc(lease["expires_at_utc"]) <= _parse_utc(now)
            dead = recover_dead and not _process_alive(lease["owner_pid"])
            if not expired and not dead:
                continue
            if lease["lease_kind"] == "delivery" and lease["report_id"] is not None:
                cursor = connection.execute(
                    """
                    UPDATE deliveries
                    SET state = 'uncertain', updated_at_utc = ?,
                        last_error_class = 'dispatch-uncertain',
                        last_error_message = 'delivery lease expired before receipt',
                        lease_owner = NULL, lease_token = NULL
                    WHERE report_id = ? AND part_index = ? AND state = 'sending'
                      AND lease_token = ?
                    """,
                    (now, lease["report_id"], lease["part_index"], lease["token"]),
                )
                recovered += cursor.rowcount
                if cursor.rowcount:
                    connection.execute(
                        "UPDATE snapshots SET resolved_at_utc = NULL WHERE report_id = ?",
                        (lease["report_id"],),
                    )
            connection.execute("DELETE FROM leases WHERE lease_key = ?", (lease["lease_key"],))
        orphaned = connection.execute(
            """
            UPDATE deliveries
            SET state = 'uncertain', updated_at_utc = ?,
                last_error_class = 'dispatch-uncertain',
                last_error_message = 'sending delivery had no recoverable lease',
                lease_owner = NULL, lease_token = NULL
            WHERE state = 'sending'
              AND NOT EXISTS (
                  SELECT 1 FROM leases
                  WHERE leases.report_id = deliveries.report_id
                    AND leases.part_index = deliveries.part_index
                    AND leases.token = deliveries.lease_token
              )
            """,
            (now,),
        )
        recovered += orphaned.rowcount
        return recovered

    def recover_expired(self) -> int:
        now = _now_from(self.clock)
        with self._write() as connection:
            return self._recover_expired_in_tx(connection, now)

    # -- bounded retention ----------------------------------------------------

    def _mark_snapshot_resolved_in_tx(
        self, connection: sqlite3.Connection, report_id: str, now: str
    ) -> None:
        counts = connection.execute(
            """
            SELECT COUNT(*) AS total,
                   SUM(CASE WHEN state IN ('pending', 'sending', 'failed', 'uncertain') THEN 1 ELSE 0 END)
                     AS unresolved
            FROM deliveries WHERE report_id = ?
            """,
            (report_id,),
        ).fetchone()
        if counts is not None and counts["total"] and not counts["unresolved"]:
            connection.execute(
                "UPDATE snapshots SET resolved_at_utc = ? WHERE report_id = ?",
                (now, report_id),
            )
        else:
            connection.execute(
                "UPDATE snapshots SET resolved_at_utc = NULL WHERE report_id = ?",
                (report_id,),
            )

    def purge_resolved(self, *, now: str | datetime | None = None) -> int:
        current = _utc_text(now, "now") if now is not None else _now_from(self.clock)
        assert current is not None
        parsed = _parse_utc(current)
        threshold = _utc_text(parsed - timedelta(days=self.retention_days), "retention threshold")
        assert threshold is not None
        removed = 0
        with self._write() as connection:
            candidates = connection.execute(
                """
                SELECT report_id FROM snapshots
                WHERE resolved_at_utc IS NOT NULL AND resolved_at_utc < ?
                ORDER BY resolved_at_utc, cutoff_utc
                """,
                (threshold,),
            ).fetchall()
            for candidate in candidates:
                report_id = candidate["report_id"]
                unresolved = connection.execute(
                    """
                    SELECT 1 FROM deliveries
                    WHERE report_id = ? AND state IN ('pending', 'sending', 'failed', 'uncertain')
                    LIMIT 1
                    """,
                    (report_id,),
                ).fetchone()
                if unresolved is not None:
                    continue
                cursor = connection.execute(
                    "DELETE FROM snapshots WHERE report_id = ?", (report_id,)
                )
                removed += cursor.rowcount
            work_cursor = connection.execute(
                """
                DELETE FROM work_items
                WHERE active = 0
                  AND final_outcome_delivery_marker IS NOT NULL
                  AND ended_at_utc IS NOT NULL
                  AND ended_at_utc < ?
                  AND NOT EXISTS (
                      SELECT 1 FROM deliveries
                      WHERE deliveries.report_id = work_items.final_outcome_delivery_marker
                        AND deliveries.state IN ('pending', 'sending', 'failed', 'uncertain')
                  )
                """,
                (threshold,),
            )
            removed += work_cursor.rowcount
        return removed

    purge = purge_resolved
