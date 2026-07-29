"""SQLite ledger for redacted, project-scoped self-improvement evidence."""

from __future__ import annotations

import os
import re
import sqlite3
import time
from pathlib import Path
from typing import Any, Callable, Iterable

_SECRET_LIKE = re.compile(r"(?i)(bearer\s+|sk-[a-z0-9]|api[_-]?key|token=|auth(?:orization)?\s*[=:])")
_SIGNALS = {"NONE", "PATCH_CANDIDATE", "MINOR_CAPABILITY_SIGNAL", "REQUIRES_MORE_EVIDENCE"}

# Bumped whenever the durable shape changes. A ledger written by a different
# version is refused loudly: `CREATE TABLE IF NOT EXISTS` against an older shape
# silently no-ops and then every INSERT fails, which produced a healthy-looking
# session with zero evidence.
SCHEMA_VERSION = 4


class LedgerSchemaError(RuntimeError):
    """The ledger on disk was written by an incompatible schema version."""


_SCHEMA = """
CREATE TABLE IF NOT EXISTS cycle_sessions (
    session_id TEXT PRIMARY KEY,
    runtime_instance TEXT NOT NULL,
    process_id INTEGER NOT NULL,
    project_root TEXT NOT NULL,
    candidate_version TEXT NOT NULL,
    manifest_digest TEXT NOT NULL,
    baseline_commit TEXT NOT NULL,
    baseline_dirty_digest TEXT NOT NULL DEFAULT 'unknown',
    logical_provider TEXT NOT NULL,
    requested_model TEXT NOT NULL,
    platform TEXT NOT NULL,
    status TEXT NOT NULL CHECK (status IN ('active', 'reconciliation_required', 'finalized')),
    last_turn_outcome TEXT,
    next_version_signal TEXT NOT NULL DEFAULT 'REQUIRES_MORE_EVIDENCE',
    manifest_drifted INTEGER NOT NULL DEFAULT 0,
    started_at REAL NOT NULL,
    updated_at REAL NOT NULL,
    finalized_at REAL
);
CREATE TABLE IF NOT EXISTS tool_calls (
    session_id TEXT NOT NULL REFERENCES cycle_sessions(session_id),
    turn_id TEXT NOT NULL DEFAULT '',
    api_request_id TEXT NOT NULL DEFAULT '',
    tool_call_id TEXT NOT NULL,
    tool_name TEXT NOT NULL,
    duration_ms INTEGER,
    outcome TEXT NOT NULL CHECK (outcome IN ('success', 'error', 'unknown')),
    created_at REAL NOT NULL,
    PRIMARY KEY (session_id, turn_id, api_request_id, tool_call_id)
);
CREATE TABLE IF NOT EXISTS turn_outcomes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT NOT NULL REFERENCES cycle_sessions(session_id),
    outcome TEXT NOT NULL CHECK (outcome IN ('completed', 'interrupted', 'failed')),
    created_at REAL NOT NULL
);
CREATE TABLE IF NOT EXISTS model_calls (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT NOT NULL REFERENCES cycle_sessions(session_id),
    turn_id TEXT NOT NULL,
    api_request_id TEXT,
    requested_model TEXT NOT NULL,
    resolved_route TEXT,
    resolved_model TEXT,
    latency_ms INTEGER,
    input_tokens INTEGER,
    output_tokens INTEGER,
    reported_cost REAL,
    error_code TEXT,
    created_at REAL NOT NULL,
    UNIQUE(session_id, turn_id)
);
CREATE TABLE IF NOT EXISTS coordination_events (
    session_id TEXT NOT NULL REFERENCES cycle_sessions(session_id),
    turn_id TEXT NOT NULL DEFAULT '',
    api_request_id TEXT NOT NULL DEFAULT '',
    event_id TEXT NOT NULL,
    system TEXT NOT NULL,
    action TEXT NOT NULL,
    phase TEXT NOT NULL CHECK (phase IN ('pre_admission', 'post_admission', 'unknown')),
    outcome TEXT NOT NULL,
    uncertainty TEXT,
    duration_ms INTEGER,
    created_at REAL NOT NULL,
    PRIMARY KEY (session_id, turn_id, api_request_id, event_id)
);
CREATE TABLE IF NOT EXISTS improvement_tasks (
    task_id TEXT PRIMARY KEY,
    statement TEXT NOT NULL,
    acceptance_criterion TEXT NOT NULL,
    baseline_commit TEXT NOT NULL,
    baseline_dirty_digest TEXT NOT NULL,
    evaluation_digest TEXT NOT NULL,
    created_at REAL NOT NULL
);
CREATE TABLE IF NOT EXISTS evaluation_runs (
    task_id TEXT NOT NULL REFERENCES improvement_tasks(task_id),
    phase TEXT NOT NULL CHECK (phase IN ('baseline', 'candidate')),
    commit_id TEXT NOT NULL,
    evaluation_digest TEXT NOT NULL,
    passed INTEGER NOT NULL,
    failed INTEGER NOT NULL,
    metric REAL,
    duration_ms INTEGER,
    created_at REAL NOT NULL,
    PRIMARY KEY (task_id, phase)
);
CREATE INDEX IF NOT EXISTS idx_tool_calls_session ON tool_calls(session_id);
CREATE INDEX IF NOT EXISTS idx_model_calls_session ON model_calls(session_id);
CREATE INDEX IF NOT EXISTS idx_coordination_events_session ON coordination_events(session_id);
CREATE INDEX IF NOT EXISTS idx_turn_outcomes_session ON turn_outcomes(session_id);
"""


class SelfImprovementLedger:
    """Small synchronous ledger with one connection per atomic operation."""

    def __init__(self, path: Path) -> None:
        self.path = Path(path).expanduser().absolute()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(str(self.path), timeout=5.0)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        connection.execute("PRAGMA busy_timeout = 5000")
        return connection

    def ensure_schema(self) -> None:
        if self.path.parent.is_symlink():
            raise RuntimeError("self-improvement ledger directory must not be a symlink")
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if self.path.is_symlink():
            raise RuntimeError("self-improvement ledger must not be a symlink")
        try:
            descriptor = os.open(self.path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
        except FileExistsError:
            pass
        else:
            os.close(descriptor)
        self.path.chmod(0o600)
        with self._connect() as connection:
            connection.execute("PRAGMA journal_mode = WAL")
            found = int(connection.execute("PRAGMA user_version").fetchone()[0])
            populated = connection.execute(
                "SELECT COUNT(*) FROM sqlite_master WHERE type = 'table' AND name = 'cycle_sessions'"
            ).fetchone()[0]
            if populated and found != SCHEMA_VERSION:
                raise LedgerSchemaError(
                    f"{self.path} was written by ledger schema v{found}, but this build requires "
                    f"v{SCHEMA_VERSION}. Move the file aside to start a new ledger; it is not migrated "
                    "automatically because its rows are release evidence."
                )
            connection.executescript(_SCHEMA)
            connection.execute(f"PRAGMA user_version = {SCHEMA_VERSION}")

    @staticmethod
    def _safe_text(value: Any, *, limit: int = 256) -> str | None:
        if value is None:
            return None
        text = str(value).strip()[:limit]
        if not text:
            return None
        if _SECRET_LIKE.search(text):
            return "[redacted]"
        return text

    @staticmethod
    def _optional_int(value: Any) -> int | None:
        if value is None or isinstance(value, bool):
            return None
        try:
            parsed = int(value)
        except (TypeError, ValueError):
            return None
        return parsed if parsed >= 0 else None

    @staticmethod
    def _optional_float(value: Any) -> float | None:
        if value is None or isinstance(value, bool):
            return None
        try:
            parsed = float(value)
        except (TypeError, ValueError):
            return None
        return parsed if parsed >= 0 else None

    def start_session(
        self,
        *,
        session_id: str,
        project_root: Path,
        candidate_version: str,
        manifest_digest: str,
        baseline_commit: str,
        logical_provider: str,
        requested_model: str,
        platform: str,
        runtime_instance: str = "direct",
        process_id: int | None = None,
        baseline_dirty_digest: str = "unknown",
    ) -> bool:
        self.ensure_schema()
        now = time.time()
        with self._connect() as connection:
            cursor = connection.execute(
                """
                INSERT OR IGNORE INTO cycle_sessions (
                    session_id, runtime_instance, process_id,
                    project_root, candidate_version, manifest_digest,
                    baseline_commit, baseline_dirty_digest,
                    logical_provider, requested_model, platform,
                    status, started_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'active', ?, ?)
                """,
                (
                    self._safe_text(session_id) or "unknown",
                    self._safe_text(runtime_instance) or "unknown",
                    process_id if process_id is not None else os.getpid(),
                    str(Path(project_root).resolve()),
                    self._safe_text(candidate_version) or "unknown",
                    self._safe_text(manifest_digest) or "unknown",
                    self._safe_text(baseline_commit) or "unknown",
                    self._safe_text(baseline_dirty_digest) or "unknown",
                    self._safe_text(logical_provider) or "unknown",
                    self._safe_text(requested_model) or "unknown",
                    self._safe_text(platform) or "unknown",
                    now,
                    now,
                ),
            )
            if cursor.rowcount == 1:
                return True
            # A reused identifier must never silently attach new evidence to a
            # prior session's manifest and baseline.
            row = connection.execute(
                "SELECT manifest_digest, baseline_commit FROM cycle_sessions WHERE session_id = ?",
                (self._safe_text(session_id) or "unknown",),
            ).fetchone()
            if row is not None and (
                str(row["manifest_digest"]) != (self._safe_text(manifest_digest) or "unknown")
                or str(row["baseline_commit"]) != (self._safe_text(baseline_commit) or "unknown")
            ):
                raise LedgerSchemaError(
                    f"session id {session_id!r} already exists under a different manifest digest or "
                    "baseline commit; refusing to merge evidence from two distinct sessions"
                )
            return False

    @staticmethod
    def _process_alive(process_id: int) -> bool:
        if process_id <= 0:
            return False
        try:
            os.kill(process_id, 0)
        except ProcessLookupError:
            return False
        except PermissionError:
            return True
        return True

    def mark_abandoned_sessions(
        self,
        *,
        current_session_id: str,
        current_runtime_instance: str = "direct",
        current_process_id: int | None = None,
        protected_session_ids: Iterable[str] = (),
        process_alive: Callable[[int], bool] | None = None,
    ) -> int:
        """Mark only provably stale sessions; preserve known or live concurrent owners."""

        self.ensure_schema()
        current_pid = current_process_id if current_process_id is not None else os.getpid()
        is_alive = process_alive or self._process_alive
        protected = set(protected_session_ids)
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT session_id, runtime_instance, process_id
                FROM cycle_sessions
                WHERE session_id != ? AND status = 'active'
                """,
                (current_session_id,),
            ).fetchall()
            stale_ids: list[str] = []
            for row in rows:
                session_id = str(row["session_id"])
                if session_id in protected:
                    continue
                owner_pid = int(row["process_id"])
                owner_runtime = str(row["runtime_instance"])
                replaced_in_process = owner_pid == current_pid and owner_runtime != current_runtime_instance
                dead_process = owner_pid != current_pid and not is_alive(owner_pid)
                if replaced_in_process or dead_process:
                    stale_ids.append(session_id)
            if not stale_ids:
                return 0
            placeholders = ",".join("?" for _ in stale_ids)
            cursor = connection.execute(
                f"""
                UPDATE cycle_sessions
                SET status = 'reconciliation_required',
                    last_turn_outcome = 'abandoned', updated_at = ?
                WHERE session_id IN ({placeholders}) AND status = 'active'
                """,
                (time.time(), *stale_ids),
            )
            return cursor.rowcount

    def record_tool_call(
        self,
        *,
        session_id: str,
        tool_call_id: str,
        tool_name: str,
        duration_ms: Any,
        outcome: str,
        turn_id: str = "",
        api_request_id: str = "",
    ) -> bool:
        return self.record_tool_observation(
            session_id=session_id,
            tool_call_id=tool_call_id,
            turn_id=turn_id,
            api_request_id=api_request_id,
            tool_name=tool_name,
            duration_ms=duration_ms,
            outcome=outcome,
            coordination=None,
        )

    def record_tool_observation(
        self,
        *,
        session_id: str,
        tool_call_id: str,
        tool_name: str,
        duration_ms: Any,
        outcome: str,
        coordination: dict[str, Any] | None,
        turn_id: str = "",
        api_request_id: str = "",
    ) -> bool:
        """Commit a tool metric and optional coordination classification atomically.

        Identity is `(session_id, turn_id, api_request_id, tool_call_id)`. Hermes
        may derive a tool_call_id from call content, and the per-response index
        resets on each model request. The request identity distinguishes a real
        retry inside one turn while an exact duplicate hook delivery remains
        idempotent.
        """

        self.ensure_schema()
        normalized_outcome = outcome if outcome in {"success", "error", "unknown"} else "unknown"
        scoped_turn = self._safe_text(turn_id) or ""
        scoped_request = self._safe_text(api_request_id) or ""
        with self._connect() as connection:
            cursor = connection.execute(
                """
                INSERT OR IGNORE INTO tool_calls (
                    session_id, turn_id, api_request_id, tool_call_id,
                    tool_name, duration_ms, outcome, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    self._safe_text(session_id) or "unknown",
                    scoped_turn,
                    scoped_request,
                    self._safe_text(tool_call_id) or "unknown",
                    self._safe_text(tool_name) or "unknown",
                    self._optional_int(duration_ms),
                    normalized_outcome,
                    time.time(),
                ),
            )
            if cursor.rowcount == 1 and coordination is not None:
                phase = coordination.get("phase")
                normalized_phase = phase if phase in {"pre_admission", "post_admission", "unknown"} else "unknown"
                connection.execute(
                    """
                    INSERT INTO coordination_events (
                        session_id, turn_id, api_request_id, event_id,
                        system, action, phase, outcome, uncertainty,
                        duration_ms, created_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        self._safe_text(session_id) or "unknown",
                        scoped_turn,
                        scoped_request,
                        self._safe_text(tool_call_id) or "unknown",
                        self._safe_text(coordination.get("system")) or "unknown",
                        self._safe_text(coordination.get("action")) or "unknown",
                        normalized_phase,
                        self._safe_text(coordination.get("outcome")) or "unknown",
                        self._safe_text(coordination.get("uncertainty")),
                        self._optional_int(duration_ms),
                        time.time(),
                    ),
                )
            return cursor.rowcount == 1

    def record_model_call(
        self,
        *,
        session_id: str,
        turn_id: str,
        requested_model: str,
        api_request_id: Any = None,
        resolved_route: Any = None,
        resolved_model: Any = None,
        latency_ms: Any = None,
        input_tokens: Any = None,
        output_tokens: Any = None,
        reported_cost: Any = None,
        error_code: Any = None,
    ) -> bool:
        self.ensure_schema()
        with self._connect() as connection:
            cursor = connection.execute(
                """
                INSERT OR IGNORE INTO model_calls (
                    session_id, turn_id, api_request_id, requested_model,
                    resolved_route, resolved_model, latency_ms, input_tokens,
                    output_tokens, reported_cost, error_code, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    self._safe_text(session_id) or "unknown",
                    self._safe_text(turn_id) or "unknown",
                    self._safe_text(api_request_id),
                    self._safe_text(requested_model) or "unknown",
                    self._safe_text(resolved_route),
                    self._safe_text(resolved_model),
                    self._optional_int(latency_ms),
                    self._optional_int(input_tokens),
                    self._optional_int(output_tokens),
                    self._optional_float(reported_cost),
                    self._safe_text(error_code),
                    time.time(),
                ),
            )
            return cursor.rowcount == 1

    def record_coordination_event(
        self,
        *,
        session_id: str,
        event_id: str,
        system: str,
        action: str,
        phase: str,
        outcome: str,
        duration_ms: Any,
        turn_id: str = "",
        uncertainty: Any = None,
    ) -> bool:
        self.ensure_schema()
        normalized_phase = phase if phase in {"pre_admission", "post_admission", "unknown"} else "unknown"
        with self._connect() as connection:
            cursor = connection.execute(
                """
                INSERT OR IGNORE INTO coordination_events (
                    session_id, turn_id, event_id, system, action, phase,
                    outcome, uncertainty, duration_ms, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    self._safe_text(session_id) or "unknown",
                    self._safe_text(turn_id) or "",
                    self._safe_text(event_id) or "unknown",
                    self._safe_text(system) or "unknown",
                    self._safe_text(action) or "unknown",
                    normalized_phase,
                    self._safe_text(outcome) or "unknown",
                    self._safe_text(uncertainty),
                    self._optional_int(duration_ms),
                    time.time(),
                ),
            )
            return cursor.rowcount == 1

    def record_turn_outcome(self, session_id: str, *, completed: bool, interrupted: bool) -> None:
        """Append one turn result and derive session status from it.

        `on_session_end` fires once per turn, not once per session. Latching the
        status meant a single interrupted turn marked a session as needing
        reconciliation permanently, even after hours of successful work. Every
        turn is now kept in `turn_outcomes`; the session reflects its latest one
        and can recover, while the interruption stays visible in the history.
        """

        self.ensure_schema()
        if interrupted:
            outcome, status = "interrupted", "reconciliation_required"
        elif completed:
            outcome, status = "completed", "active"
        else:
            outcome, status = "failed", "reconciliation_required"
        now = time.time()
        with self._connect() as connection:
            connection.execute(
                "INSERT INTO turn_outcomes (session_id, outcome, created_at) VALUES (?, ?, ?)",
                (self._safe_text(session_id) or "unknown", outcome, now),
            )
            connection.execute(
                """
                UPDATE cycle_sessions
                SET last_turn_outcome = ?,
                    status = CASE WHEN status = 'finalized' THEN status ELSE ? END,
                    updated_at = ?
                WHERE session_id = ?
                """,
                (outcome, status, now, session_id),
            )

    def turn_outcomes(self, session_id: str) -> list[str]:
        self.ensure_schema()
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT outcome FROM turn_outcomes WHERE session_id = ? ORDER BY id", (session_id,)
            ).fetchall()
            return [str(row["outcome"]) for row in rows]

    def finalize_session(
        self,
        session_id: str,
        *,
        next_version_signal: str = "REQUIRES_MORE_EVIDENCE",
        manifest_drifted: bool = False,
    ) -> None:
        self.ensure_schema()
        signal = next_version_signal if next_version_signal in _SIGNALS else "REQUIRES_MORE_EVIDENCE"
        now = time.time()
        with self._connect() as connection:
            connection.execute(
                """
                UPDATE cycle_sessions
                SET status = CASE WHEN status = 'active' THEN 'finalized' ELSE status END,
                    next_version_signal = ?, manifest_drifted = ?,
                    finalized_at = ?, updated_at = ?
                WHERE session_id = ?
                """,
                (signal, 1 if manifest_drifted else 0, now, now, session_id),
            )

    def get_session(self, session_id: str) -> dict[str, Any] | None:
        self.ensure_schema()
        with self._connect() as connection:
            row = connection.execute("SELECT * FROM cycle_sessions WHERE session_id = ?", (session_id,)).fetchone()
            return dict(row) if row else None

    def session_count(self) -> int:
        self.ensure_schema()
        with self._connect() as connection:
            return int(connection.execute("SELECT COUNT(*) FROM cycle_sessions").fetchone()[0])

    def tool_calls(self, session_id: str) -> list[dict[str, Any]]:
        self.ensure_schema()
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT tool_call_id, tool_name, duration_ms, outcome
                FROM tool_calls WHERE session_id = ? ORDER BY created_at, tool_call_id
                """,
                (session_id,),
            ).fetchall()
            return [dict(row) for row in rows]

    def model_calls(self, session_id: str) -> list[dict[str, Any]]:
        self.ensure_schema()
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT turn_id, api_request_id, requested_model, resolved_route,
                       resolved_model, latency_ms, input_tokens, output_tokens,
                       reported_cost, error_code
                FROM model_calls WHERE session_id = ? ORDER BY id
                """,
                (session_id,),
            ).fetchall()
            return [dict(row) for row in rows]

    def coordination_events(self, session_id: str) -> list[dict[str, Any]]:
        self.ensure_schema()
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT event_id, system, action, phase, outcome, duration_ms
                FROM coordination_events WHERE session_id = ? ORDER BY created_at, event_id
                """,
                (session_id,),
            ).fetchall()
            return [dict(row) for row in rows]

    def sessions(self) -> list[dict[str, Any]]:
        self.ensure_schema()
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT session_id, status, last_turn_outcome, next_version_signal,
                       baseline_commit, baseline_dirty_digest, manifest_drifted,
                       logical_provider, requested_model, platform
                FROM cycle_sessions ORDER BY started_at, session_id
                """
            ).fetchall()
            return [dict(row) for row in rows]

    def evidence_counts(self) -> dict[str, Any]:
        self.ensure_schema()
        with self._connect() as connection:
            session_statuses = {
                str(row[0]): int(row[1])
                for row in connection.execute(
                    "SELECT status, COUNT(*) FROM cycle_sessions GROUP BY status ORDER BY status"
                ).fetchall()
            }
            coordination_outcomes = {
                str(row[0]): int(row[1])
                for row in connection.execute(
                    "SELECT outcome, COUNT(*) FROM coordination_events GROUP BY outcome ORDER BY outcome"
                ).fetchall()
            }
            model_total, missing_routes = connection.execute(
                """
                SELECT COUNT(*), SUM(CASE WHEN resolved_route IS NULL THEN 1 ELSE 0 END)
                FROM model_calls
                """
            ).fetchone()
            integrity = connection.execute(
                """
                SELECT
                    SUM(CASE WHEN baseline_dirty_digest = 'clean' THEN 0 ELSE 1 END),
                    SUM(manifest_drifted)
                FROM cycle_sessions
                """
            ).fetchone()
            uncertain = connection.execute(
                "SELECT COUNT(*) FROM coordination_events WHERE uncertainty IS NOT NULL"
            ).fetchone()[0]
            return {
                "session_statuses": session_statuses,
                "tool_calls": int(connection.execute("SELECT COUNT(*) FROM tool_calls").fetchone()[0]),
                "model_calls": int(model_total or 0),
                "model_calls_missing_route": int(missing_routes or 0),
                "coordination_outcomes": coordination_outcomes,
                "sessions_without_clean_baseline": int((integrity[0] if integrity else 0) or 0),
                "sessions_with_manifest_drift": int((integrity[1] if integrity else 0) or 0),
                "coordination_events_with_uncertain_effect": int(uncertain or 0),
            }

    def checkpoint(self) -> None:
        self.ensure_schema()
        with self._connect() as connection:
            connection.execute("PRAGMA wal_checkpoint(TRUNCATE)")
