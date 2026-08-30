"""Persistent Morfeo qualification primitives.

The one-shot runner is intentionally never accepted as proof of persistent wake. This
module launches an explicitly supplied native command under PTY and reconciles only
bounded SessionDB/Kanban metadata for a separate, owner-authorized live probe.
"""

from __future__ import annotations

import json
import os
import pty
import select
import sqlite3
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping, Sequence


@dataclass(frozen=True, slots=True)
class PersistentProbeResult:
    status: str
    reason: str
    native_surface: str
    same_session: bool
    native_same_session_wake: bool
    durable_report: bool
    owner_messages: int
    continuation_source: str = "native"

    @property
    def qualified(self) -> bool:
        return self.status == "PASS"

    def to_evidence(self) -> dict[str, Any]:
        return {
            "schema_version": "aether.lab.evidence.v1",
            "kind": "persistent",
            "status": self.status,
            "mode": "live-persistent",
            "continuation_source": self.continuation_source,
            "reason": self.reason,
            "native_same_session_wake": self.native_same_session_wake,
            "durable_report": self.durable_report,
            "owner_messages": self.owner_messages,
            "same_session": self.same_session,
        }


def qualify_persistent_evidence(receipts: Mapping[str, Any]) -> PersistentProbeResult:
    """Apply the strict E2E-15 proof rule to safe native receipt metadata."""
    source = str(receipts.get("continuation_source", "native"))
    surface = str(receipts.get("native_surface", "cli"))
    owner_messages = receipts.get("owner_messages", 0)
    if not isinstance(owner_messages, int) or isinstance(owner_messages, bool):
        owner_messages = 0
    if source != "native":
        evidence_source = source if source in {"harness", "one-shot"} else "harness"
        return PersistentProbeResult(
            "CAPABILITY_WALL",
            "one_shot_continuation_non_qualifying",
            surface,
            False,
            False,
            False,
            owner_messages,
            evidence_source,
        )
    session_id = receipts.get("session_id")
    wake_session_id = receipts.get("wake_session_id", session_id)
    same_session = (
        isinstance(session_id, str) and session_id == wake_session_id
        if "session_id" in receipts or "wake_session_id" in receipts
        else receipts.get("same_session") is True
    )
    explicit_same_session_wake = receipts.get("native_same_session_wake")
    native_event = receipts.get("native_board_event") is True
    if "native_board_event" not in receipts:
        native_event = explicit_same_session_wake is True
    native_wake = (
        explicit_same_session_wake is True and same_session
        if explicit_same_session_wake is not None
        else native_event and same_session
    )
    durable_report = receipts.get("durable_report") is True
    if not native_event:
        reason = "native_same_session_wake_unobserved"
    elif not native_wake or owner_messages != 1 or not durable_report:
        reason = "same_session_or_owner_message_requirement_failed"
    else:
        return PersistentProbeResult(
            "PASS",
            "native_same_session_wake_verified",
            surface,
            True,
            True,
            True,
            owner_messages,
            source,
        )
    return PersistentProbeResult(
        "CAPABILITY_WALL",
        reason,
        surface,
        same_session,
        native_wake,
        durable_report,
        owner_messages,
        source,
    )


def run_persistent_session(
    argv: Sequence[str],
    *,
    owner_message: str,
    timeout_seconds: float = 120.0,
    cwd: Path | None = None,
    env: Mapping[str, str] | None = None,
    session_db: Path | None = None,
    kanban_db: Path | None = None,
    poll_seconds: float = 0.25,
) -> dict[str, Any]:
    """Run one native Hermes turn under PTY and reconcile its durable wake.

    The PTY is only the input transport.  Qualification never parses terminal output:
    it selects the newly-created Morfeo session from ``state.db``, records the event
    cursor in the Kanban DB, and accepts only a later ``flow_terminal`` event whose
    task affinity points to that same session and whose later assistant report is
    durable in ``state.db``.  Once that proof is present the native process is
    terminated without sending a second input.  Missing or malformed observations
    fail closed as a capability wall.
    """
    if not argv:
        raise ValueError("native surface command is required")
    if not owner_message:
        raise ValueError("owner message is required")
    if timeout_seconds <= 0:
        raise ValueError("timeout_seconds must be positive")
    poll_seconds = max(0.01, poll_seconds)

    session_path = Path(session_db) if session_db is not None else None
    board_path = Path(kanban_db) if kanban_db is not None else None
    session_ids_before = _session_ids(session_path)
    event_cursor = _event_cursor(board_path)
    master, slave = pty.openpty()
    child_env = dict(env) if env is not None else os.environ.copy()
    # The harness itself may run inside an agent delegation context. The
    # persistent PTY is the new owner-facing root session, not a delegated
    # worker; leaking this marker would make its native Kanban mutations fail.
    child_env.pop("HERMES_DELEGATED_CHILD_CONTEXT", None)
    child_env.setdefault("TERM", "xterm-256color")
    process = subprocess.Popen(
        [str(item) for item in argv],
        stdin=slave,
        stdout=slave,
        stderr=slave,
        cwd=cwd,
        env=child_env,
        close_fds=True,
    )
    os.close(slave)
    started = time.monotonic()
    observed_session: str | None = None
    owner_messages = 0
    assistant_at_event = 0
    nonempty_assistant_at_event = 0
    native_event = False
    event_created_at: float | None = None
    durable_report = False
    same_session = False
    try:
        tui_ready = _wait_for_tui_ready(
            master,
            process,
            timeout_seconds=min(30.0, timeout_seconds),
        )
        if tui_ready:
            # Exactly one owner write. No continuation, slash command, or synthetic
            # wake is sent after this point. Prompt-toolkit binds submit to CR; LF
            # is reserved for multiline input under the default Hermes config.
            os.write(master, owner_message.encode("utf-8") + b"\r")
        while tui_ready and process.poll() is None and time.monotonic() - started < timeout_seconds:
            session_state = _session_state(session_path, session_ids_before, owner_message)
            if observed_session is None and len(session_state["candidates"]) == 1:
                observed_session = session_state["candidates"][0]
                owner_messages = session_state["owner_messages"][observed_session]
                # The pre-event assistant count is captured only when the native
                # event is first observed. This prevents a report written before
                # that event from satisfying the post-event proof.
            elif observed_session is not None:
                owner_messages = session_state["owner_messages"].get(observed_session, 0)

            if observed_session is not None and not native_event:
                event = _native_event_for_session(
                    board_path,
                    event_cursor,
                    observed_session,
                )
                if event is not None:
                    assistant_at_event = session_state["assistant_messages"].get(
                        observed_session, 0
                    )
                    nonempty_assistant_at_event = session_state["nonempty_assistant_messages"].get(
                        observed_session, 0
                    )
                    native_event = True
                    event_created_at = event.get("created_at")
                    same_session = event["session_id"] == observed_session

            if observed_session is not None and native_event:
                current = _session_state(session_path, session_ids_before, owner_message)
                owner_messages = current["owner_messages"].get(observed_session, 0)
                durable_report = _durable_report_after_event(
                    current,
                    observed_session,
                    event_created_at=event_created_at,
                    assistant_at_event=assistant_at_event,
                    nonempty_assistant_at_event=nonempty_assistant_at_event,
                )
                if same_session and owner_messages == 1 and durable_report:
                    break

            read_ready, _, _ = select.select([master], [], [], 0.1)
            if read_ready:
                try:
                    os.read(master, 4096)
                except OSError:
                    break
    finally:
        os.close(master)

    # The final read is deliberately database-only.  A native surface may have
    # flushed its last assistant row just as it exits or just after the PTY loop
    # notices EOF, so reconcile one more time before deciding.
    if observed_session is None:
        session_state = _session_state(session_path, session_ids_before, owner_message)
        if len(session_state["candidates"]) == 1:
            observed_session = session_state["candidates"][0]
            owner_messages = session_state["owner_messages"][observed_session]
    if observed_session is not None:
        event = _native_event_for_session(board_path, event_cursor, observed_session)
        if event is not None:
            current = _session_state(session_path, session_ids_before, owner_message)
            if not native_event:
                assistant_at_event = current["assistant_messages"].get(observed_session, 0)
                nonempty_assistant_at_event = current["nonempty_assistant_messages"].get(
                    observed_session, 0
                )
            native_event = True
            event_created_at = event.get("created_at")
            same_session = event["session_id"] == observed_session
        current = _session_state(session_path, session_ids_before, owner_message)
        owner_messages = current["owner_messages"].get(observed_session, 0)
        durable_report = native_event and _durable_report_after_event(
            current,
            observed_session,
            event_created_at=event_created_at,
            assistant_at_event=assistant_at_event,
            nonempty_assistant_at_event=nonempty_assistant_at_event,
        )

    if process.poll() is None:
        process.terminate()
        try:
            process.wait(timeout=2)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=2)
    result = qualify_persistent_evidence(
        {
            "continuation_source": "native",
            "native_surface": Path(str(argv[0])).name,
            "native_board_event": native_event,
            "native_same_session_wake": native_event and same_session,
            "durable_report": durable_report,
            "owner_messages": owner_messages,
            "session_id": observed_session,
            "wake_session_id": observed_session if same_session else None,
        }
    )
    return result.to_evidence()


def _wait_for_tui_ready(
    master: int,
    process: subprocess.Popen[bytes],
    *,
    timeout_seconds: float,
) -> bool:
    """Wait until prompt-toolkit rendered its input-ready surface."""
    deadline = time.monotonic() + timeout_seconds
    recent = b""
    while process.poll() is None and time.monotonic() < deadline:
        ready, _, _ = select.select([master], [], [], 0.1)
        if not ready:
            continue
        try:
            recent = (recent + os.read(master, 65536))[-131072:]
        except OSError:
            return False
        if b"\x1b[?2004h" in recent and b"\x1b]2;" in recent and b"/help for commands" in recent:
            return True
    return False


def _connect_read_only(path: Path | None) -> sqlite3.Connection | None:
    """Open an existing SQLite file without creating or mutating it."""
    if path is None or not path.is_file():
        return None
    try:
        connection = sqlite3.connect(f"file:{path.resolve()}?mode=ro", uri=True, timeout=0.2)
        connection.row_factory = sqlite3.Row
        return connection
    except sqlite3.Error:
        return None


def _durable_report_after_event(
    state: Mapping[str, Any],
    session_id: str,
    *,
    event_created_at: float | None,
    assistant_at_event: int,
    nonempty_assistant_at_event: int,
) -> bool:
    """Require a non-empty assistant row durably ordered after the event."""
    latest = state["latest_nonempty_assistant_at"].get(session_id)
    if isinstance(event_created_at, (int, float)) and isinstance(latest, (int, float)):
        return float(latest) > float(event_created_at)
    return (
        state["assistant_messages"].get(session_id, 0) > assistant_at_event
        and state["nonempty_assistant_messages"].get(session_id, 0) > nonempty_assistant_at_event
    )


def _table_columns(connection: sqlite3.Connection, table: str) -> set[str]:
    try:
        return {str(row[1]) for row in connection.execute(f"PRAGMA table_info({table})")}
    except sqlite3.Error:
        return set()


def _session_ids(path: Path | None) -> set[str]:
    connection = _connect_read_only(path)
    if connection is None:
        return set()
    try:
        if not _table_columns(connection, "sessions"):
            return set()
        return {
            str(row[0])
            for row in connection.execute("SELECT id FROM sessions WHERE id IS NOT NULL")
        }
    except sqlite3.Error:
        return set()
    finally:
        connection.close()


def _session_state(
    path: Path | None,
    before: set[str],
    owner_message: str | None = None,
) -> dict[str, Any]:
    """Return bounded session/message counts, never message content."""
    state: dict[str, Any] = {
        "candidates": [],
        "owner_messages": {},
        "assistant_messages": {},
        "nonempty_assistant_messages": {},
        "latest_nonempty_assistant_at": {},
    }
    connection = _connect_read_only(path)
    if connection is None:
        return state
    try:
        session_columns = _table_columns(connection, "sessions")
        message_columns = _table_columns(connection, "messages")
        if "id" not in session_columns or "source" not in session_columns:
            return state
        archived = " AND COALESCE(archived, 0) = 0" if "archived" in session_columns else ""
        sessions = [
            str(row[0])
            for row in connection.execute(
                f"SELECT id FROM sessions WHERE id IS NOT NULL "
                f"AND COALESCE(source, '') != 'kanban'{archived}"
            )
        ]
        if (
            not message_columns
            or "session_id" not in message_columns
            or "role" not in message_columns
        ):
            return state
        content = "content" in message_columns
        timestamp = "timestamp" in message_columns
        selected = ["session_id", "role"]
        if content:
            selected.append("content")
        if timestamp:
            selected.append("timestamp")
        placeholders = ",".join("?" for _ in sessions)
        rows = []
        if sessions:
            rows = connection.execute(
                f"SELECT {', '.join(selected)} FROM messages WHERE session_id IN ({placeholders})",
                sessions,
            ).fetchall()
        for session_id in sessions:
            state["owner_messages"][session_id] = 0
            state["assistant_messages"][session_id] = 0
            state["nonempty_assistant_messages"][session_id] = 0
            state["latest_nonempty_assistant_at"][session_id] = None
        for row in rows:
            session_id = str(row["session_id"])
            role = str(row["role"]).casefold()
            if role == "user":
                if owner_message is None or (content and row["content"] == owner_message):
                    state["owner_messages"][session_id] += 1
            elif role == "assistant":
                state["assistant_messages"][session_id] += 1
                if not content or (isinstance(row["content"], str) and row["content"].strip()):
                    state["nonempty_assistant_messages"][session_id] += 1
                    if timestamp and isinstance(row["timestamp"], (int, float)):
                        state["latest_nonempty_assistant_at"][session_id] = max(
                            state["latest_nonempty_assistant_at"][session_id] or float("-inf"),
                            float(row["timestamp"]),
                        )
        state["candidates"] = [
            session_id
            for session_id in sessions
            if session_id not in before and state["owner_messages"][session_id] >= 1
        ]
        return state
    except sqlite3.Error:
        return state
    finally:
        connection.close()


def _event_cursor(path: Path | None) -> int:
    connection = _connect_read_only(path)
    if connection is None:
        return 0
    try:
        if "id" not in _table_columns(connection, "task_events"):
            return 0
        return int(connection.execute("SELECT COALESCE(MAX(id), 0) FROM task_events").fetchone()[0])
    except (sqlite3.Error, TypeError, ValueError):
        return 0
    finally:
        connection.close()


def _native_event_for_session(
    path: Path | None,
    cursor: int,
    session_id: str,
) -> dict[str, Any] | None:
    """Find a post-cursor native terminal event tied to ``session_id``."""
    connection = _connect_read_only(path)
    if connection is None:
        return None
    try:
        event_columns = _table_columns(connection, "task_events")
        if not {"id", "task_id", "kind"}.issubset(event_columns):
            return None
        selected = ["id", "task_id", "kind"]
        if "payload" in event_columns:
            selected.append("payload")
        if "created_at" in event_columns:
            selected.append("created_at")
        events = connection.execute(
            f"SELECT {', '.join(selected)} FROM task_events "
            "WHERE id > ? AND kind = 'flow_terminal' ORDER BY id ASC",
            (cursor,),
        ).fetchall()
        for row in events:
            task_id = str(row["task_id"])
            payload = _json_object(row["payload"]) if "payload" in event_columns else {}
            result = {
                "session_id": session_id,
                "event_id": str(row["id"]),
                "created_at": (
                    float(row["created_at"])
                    if "created_at" in event_columns and isinstance(row["created_at"], (int, float))
                    else None
                ),
            }
            payload_session = _payload_session(payload)
            if payload_session is not None and payload_session != session_id:
                continue
            if payload_session == session_id:
                return result
            if session_id in _task_session_ids(connection, task_id, payload):
                return result
        return None
    except sqlite3.Error:
        return None
    finally:
        connection.close()


def _json_object(value: object) -> dict[str, Any]:
    if not isinstance(value, str):
        return {}
    try:
        parsed = json.loads(value)
    except (TypeError, ValueError, json.JSONDecodeError):
        return {}
    return parsed if isinstance(parsed, dict) else {}


def _payload_session(payload: Mapping[str, Any]) -> str | None:
    for key in ("session_id", "wake_session_id"):
        value = payload.get(key)
        if isinstance(value, str) and value:
            return value
    return None


def _task_session_ids(
    connection: sqlite3.Connection,
    task_id: str,
    payload: Mapping[str, Any] | None = None,
) -> set[str]:
    identities: set[str] = set()
    task_columns = _table_columns(connection, "tasks")
    if "id" in task_columns and "session_id" in task_columns:
        row = connection.execute("SELECT session_id FROM tasks WHERE id = ?", (task_id,)).fetchone()
        if row and isinstance(row[0], str) and row[0]:
            identities.add(row[0])
    affinity_columns = _table_columns(connection, "kanban_session_affinity")
    if {"owner_task_id", "session_id"}.issubset(affinity_columns):
        rows = connection.execute(
            "SELECT session_id FROM kanban_session_affinity "
            "WHERE owner_task_id = ? AND session_id IS NOT NULL",
            (task_id,),
        ).fetchall()
        identities.update(str(row[0]) for row in rows if row[0])
    flow_id = payload.get("flow_id") if payload else None
    if (
        not identities
        and isinstance(flow_id, str)
        and flow_id
        and {"flow_id", "session_id"}.issubset(affinity_columns)
    ):
        rows = connection.execute(
            "SELECT session_id FROM kanban_session_affinity "
            "WHERE flow_id = ? AND session_id IS NOT NULL",
            (flow_id,),
        ).fetchall()
        identities.update(str(row[0]) for row in rows if row[0])
    return identities


# Explicit aliases keep the Python-level API discoverable without introducing another
# CLI or service surface.
persistent_session_probe = qualify_persistent_evidence
probe_persistent_session = qualify_persistent_evidence
persistent_session_run = run_persistent_session
