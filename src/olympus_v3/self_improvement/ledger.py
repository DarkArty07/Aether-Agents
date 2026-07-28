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

_SCHEMA = """
CREATE TABLE IF NOT EXISTS cycle_sessions (
    session_id TEXT PRIMARY KEY,
    runtime_instance TEXT NOT NULL,
    process_id INTEGER NOT NULL,
    project_root TEXT NOT NULL,
    candidate_version TEXT NOT NULL,
    manifest_digest TEXT NOT NULL,
    baseline_commit TEXT NOT NULL,
    logical_provider TEXT NOT NULL,
    requested_model TEXT NOT NULL,
    platform TEXT NOT NULL,
    status TEXT NOT NULL CHECK (status IN ('active', 'reconciliation_required', 'finalized')),
    last_turn_outcome TEXT,
    next_version_signal TEXT NOT NULL DEFAULT 'REQUIRES_MORE_EVIDENCE',
    started_at REAL NOT NULL,
    updated_at REAL NOT NULL,
    finalized_at REAL
);
CREATE TABLE IF NOT EXISTS tool_calls (
    tool_call_id TEXT PRIMARY KEY,
    session_id TEXT NOT NULL REFERENCES cycle_sessions(session_id),
    tool_name TEXT NOT NULL,
    duration_ms INTEGER,
    outcome TEXT NOT NULL CHECK (outcome IN ('success', 'error', 'unknown')),
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
    event_id TEXT PRIMARY KEY,
    session_id TEXT NOT NULL REFERENCES cycle_sessions(session_id),
    system TEXT NOT NULL,
    action TEXT NOT NULL,
    phase TEXT NOT NULL CHECK (phase IN ('pre_admission', 'post_admission', 'unknown')),
    outcome TEXT NOT NULL,
    duration_ms INTEGER,
    created_at REAL NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_tool_calls_session ON tool_calls(session_id);
CREATE INDEX IF NOT EXISTS idx_model_calls_session ON model_calls(session_id);
CREATE INDEX IF NOT EXISTS idx_coordination_events_session ON coordination_events(session_id);
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
            connection.executescript(_SCHEMA)

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
    ) -> bool:
        self.ensure_schema()
        now = time.time()
        with self._connect() as connection:
            cursor = connection.execute(
                """
                INSERT OR IGNORE INTO cycle_sessions (
                    session_id, runtime_instance, process_id,
                    project_root, candidate_version, manifest_digest,
                    baseline_commit, logical_provider, requested_model, platform,
                    status, started_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'active', ?, ?)
                """,
                (
                    self._safe_text(session_id) or "unknown",
                    self._safe_text(runtime_instance) or "unknown",
                    process_id if process_id is not None else os.getpid(),
                    str(Path(project_root).resolve()),
                    self._safe_text(candidate_version) or "unknown",
                    self._safe_text(manifest_digest) or "unknown",
                    self._safe_text(baseline_commit) or "unknown",
                    self._safe_text(logical_provider) or "unknown",
                    self._safe_text(requested_model) or "unknown",
                    self._safe_text(platform) or "unknown",
                    now,
                    now,
                ),
            )
            return cursor.rowcount == 1

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
    ) -> bool:
        return self.record_tool_observation(
            session_id=session_id,
            tool_call_id=tool_call_id,
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
    ) -> bool:
        """Commit a tool metric and optional coordination classification atomically."""

        self.ensure_schema()
        normalized_outcome = outcome if outcome in {"success", "error", "unknown"} else "unknown"
        with self._connect() as connection:
            cursor = connection.execute(
                """
                INSERT OR IGNORE INTO tool_calls (
                    tool_call_id, session_id, tool_name, duration_ms, outcome, created_at
                ) VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    self._safe_text(tool_call_id) or "unknown",
                    self._safe_text(session_id) or "unknown",
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
                        event_id, session_id, system, action, phase, outcome, duration_ms, created_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        self._safe_text(tool_call_id) or "unknown",
                        self._safe_text(session_id) or "unknown",
                        self._safe_text(coordination.get("system")) or "unknown",
                        self._safe_text(coordination.get("action")) or "unknown",
                        normalized_phase,
                        self._safe_text(coordination.get("outcome")) or "unknown",
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
    ) -> bool:
        self.ensure_schema()
        normalized_phase = phase if phase in {"pre_admission", "post_admission", "unknown"} else "unknown"
        with self._connect() as connection:
            cursor = connection.execute(
                """
                INSERT OR IGNORE INTO coordination_events (
                    event_id, session_id, system, action, phase, outcome, duration_ms, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    self._safe_text(event_id) or "unknown",
                    self._safe_text(session_id) or "unknown",
                    self._safe_text(system) or "unknown",
                    self._safe_text(action) or "unknown",
                    normalized_phase,
                    self._safe_text(outcome) or "unknown",
                    self._optional_int(duration_ms),
                    time.time(),
                ),
            )
            return cursor.rowcount == 1

    def record_turn_outcome(self, session_id: str, *, completed: bool, interrupted: bool) -> None:
        self.ensure_schema()
        if interrupted:
            outcome = "interrupted"
            status = "reconciliation_required"
        elif completed:
            outcome = "completed"
            status = "active"
        else:
            outcome = "failed"
            status = "reconciliation_required"
        with self._connect() as connection:
            connection.execute(
                """
                UPDATE cycle_sessions
                SET last_turn_outcome = ?,
                    status = CASE WHEN status = 'active' THEN ? ELSE status END,
                    updated_at = ?
                WHERE session_id = ?
                """,
                (outcome, status, time.time(), session_id),
            )

    def finalize_session(self, session_id: str, *, next_version_signal: str = "REQUIRES_MORE_EVIDENCE") -> None:
        self.ensure_schema()
        signal = next_version_signal if next_version_signal in _SIGNALS else "REQUIRES_MORE_EVIDENCE"
        now = time.time()
        with self._connect() as connection:
            connection.execute(
                """
                UPDATE cycle_sessions
                SET status = CASE WHEN status = 'active' THEN 'finalized' ELSE status END,
                    next_version_signal = ?, finalized_at = ?, updated_at = ?
                WHERE session_id = ?
                """,
                (signal, now, now, session_id),
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
                       baseline_commit, logical_provider, requested_model, platform
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
            return {
                "session_statuses": session_statuses,
                "tool_calls": int(connection.execute("SELECT COUNT(*) FROM tool_calls").fetchone()[0]),
                "model_calls": int(model_total or 0),
                "model_calls_missing_route": int(missing_routes or 0),
                "coordination_outcomes": coordination_outcomes,
            }

    def checkpoint(self) -> None:
        self.ensure_schema()
        with self._connect() as connection:
            connection.execute("PRAGMA wal_checkpoint(TRUNCATE)")
