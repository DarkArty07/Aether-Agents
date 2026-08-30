"""Persistent Morfeo qualification primitives.

The one-shot runner is intentionally never accepted as proof of persistent wake. This
module launches an explicitly supplied native command under PTY and reconciles only
bounded SessionDB/Kanban metadata for a separate, owner-authorized live probe.
"""

from __future__ import annotations

import json
import os
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
    """Run one native TUI-gateway session and reconcile its durable wake.

    The visual TUI is a JSON-RPC client of ``tui_gateway.entry``. The laboratory uses
    that same native contract directly: wait for ``gateway.ready``, call
    ``session.create`` once, and submit exactly one owner prompt. Qualification parses
    no model/terminal text; it accepts only SessionDB and Kanban evidence.
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
    child_env = dict(env) if env is not None else os.environ.copy()
    child_env.pop("HERMES_DELEGATED_CHILD_CONTEXT", None)
    child_env.pop("HERMES_UI_SESSION_ID", None)
    child_env.pop("HERMES_GATEWAY_SESSION", None)
    child_env.pop("HERMES_CRON_SESSION", None)
    child_env.pop("HERMES_TUI_ACTIVE_SESSION_FILE", None)
    for key in tuple(child_env):
        if key.startswith("HERMES_SESSION_"):
            child_env.pop(key, None)
    profile = _profile_from_argv(argv)
    if profile:
        child_env["HERMES_PROFILE"] = profile
    if session_path is not None:
        child_env["HERMES_HOME"] = str(session_path.parent)
    command = _tui_gateway_command(argv)
    process = subprocess.Popen(
        command,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        cwd=cwd,
        env=child_env,
        close_fds=True,
    )
    started = time.monotonic()
    rpc_buffer = bytearray()
    observed_session: str | None = None
    owner_messages = 0
    assistant_at_event = 0
    nonempty_assistant_at_event = 0
    native_event = False
    durable_report = False
    same_session = False
    rpc_handle_id: str | None = None
    rpc_session_id: str | None = None
    submit_accepted = False
    try:
        ready = _rpc_wait(
            process,
            rpc_buffer,
            lambda item: (
                item.get("method") == "event"
                and (item.get("params") or {}).get("type") == "gateway.ready"
            ),
            timeout_seconds=min(30.0, timeout_seconds),
        )
        if ready is not None:
            _rpc_write(
                process,
                {
                    "jsonrpc": "2.0",
                    "id": "e2e15-create",
                    "method": "session.create",
                    "params": {
                        "cols": 120,
                        "cwd": str(cwd) if cwd is not None else "",
                        "source": "tui",
                    },
                },
            )
            created = _rpc_wait(
                process,
                rpc_buffer,
                lambda item: item.get("id") == "e2e15-create",
                timeout_seconds=min(30.0, timeout_seconds),
            )
            result = (created or {}).get("result") or {}
            handle = result.get("session_id") if isinstance(result, dict) else None
            stored = result.get("stored_session_id") if isinstance(result, dict) else None
            rpc_handle_id = handle if isinstance(handle, str) and handle else None
            rpc_session_id = stored if isinstance(stored, str) and stored else rpc_handle_id
        if rpc_handle_id is not None:
            _rpc_write(
                process,
                {
                    "jsonrpc": "2.0",
                    "id": "e2e15-submit",
                    "method": "prompt.submit",
                    "params": {"session_id": rpc_handle_id, "text": owner_message},
                },
            )
            submitted = _rpc_wait(
                process,
                rpc_buffer,
                lambda item: item.get("id") == "e2e15-submit",
                timeout_seconds=min(30.0, timeout_seconds),
            )
            submit_result = (submitted or {}).get("result") or {}
            submit_accepted = (
                isinstance(submit_result, dict)
                and submit_result.get("status") == "streaming"
                and not (submitted or {}).get("error")
            )
        while (
            submit_accepted
            and rpc_session_id is not None
            and process.poll() is None
            and time.monotonic() - started < timeout_seconds
        ):
            _rpc_read(process, rpc_buffer, timeout_seconds=0.0)
            session_state = _session_state(session_path, session_ids_before, owner_message)
            if observed_session is None:
                if rpc_session_id in session_state["candidates"]:
                    observed_session = rpc_session_id
                elif len(session_state["candidates"]) == 1:
                    observed_session = session_state["candidates"][0]
                if observed_session is not None:
                    owner_messages = session_state["owner_messages"][observed_session]
            else:
                owner_messages = session_state["owner_messages"].get(observed_session, 0)

            if observed_session is not None and not native_event:
                event = _native_event_for_session(board_path, event_cursor, observed_session)
                if event is not None:
                    assistant_at_event = session_state["assistant_messages"].get(
                        observed_session, 0
                    )
                    nonempty_assistant_at_event = session_state["nonempty_assistant_messages"].get(
                        observed_session, 0
                    )
                    native_event = True
                    same_session = event["session_id"] == observed_session

            if observed_session is not None and native_event:
                current = _session_state(session_path, session_ids_before, owner_message)
                owner_messages = current["owner_messages"].get(observed_session, 0)
                durable_report = (
                    current["assistant_messages"].get(observed_session, 0) > assistant_at_event
                    and current["nonempty_assistant_messages"].get(observed_session, 0)
                    > nonempty_assistant_at_event
                )
                if same_session and owner_messages == 1 and durable_report:
                    break
            time.sleep(poll_seconds)
    finally:
        if process.poll() is None:
            process.terminate()
            try:
                process.wait(timeout=3)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=3)

    if observed_session is None:
        state = _session_state(session_path, session_ids_before, owner_message)
        if rpc_session_id in state["candidates"]:
            observed_session = rpc_session_id
        elif len(state["candidates"]) == 1:
            observed_session = state["candidates"][0]
        if observed_session is not None:
            owner_messages = state["owner_messages"][observed_session]
    if observed_session is not None:
        event = _native_event_for_session(board_path, event_cursor, observed_session)
        if event is not None:
            native_event = True
            same_session = event["session_id"] == observed_session
        current = _session_state(session_path, session_ids_before, owner_message)
        owner_messages = current["owner_messages"].get(observed_session, 0)
        durable_report = native_event and (
            current["assistant_messages"].get(observed_session, 0) > assistant_at_event
            and current["nonempty_assistant_messages"].get(observed_session, 0)
            > nonempty_assistant_at_event
        )
    return qualify_persistent_evidence(
        {
            "continuation_source": "native",
            "native_surface": "tui-rpc",
            "native_board_event": native_event,
            "native_same_session_wake": native_event and same_session,
            "durable_report": durable_report,
            "owner_messages": owner_messages,
            "session_id": observed_session,
            "wake_session_id": observed_session if same_session else None,
        }
    ).to_evidence()


def _profile_from_argv(argv: Sequence[str]) -> str | None:
    for index, item in enumerate(argv[:-1]):
        if item in {"-p", "--profile"}:
            value = str(argv[index + 1]).strip()
            return value or None
    return None


def _tui_gateway_command(argv: Sequence[str]) -> tuple[str, ...]:
    executable = Path(str(argv[0]))
    if executable.name.startswith("python"):
        return tuple(str(item) for item in argv)
    try:
        first = executable.read_text(encoding="utf-8", errors="replace").splitlines()[0]
    except (OSError, IndexError):
        first = ""
    if not first.startswith("#!"):
        raise ValueError("Hermes executable has no Python interpreter shebang")
    return (first[2:].strip(), "-m", "tui_gateway.entry")


def _rpc_write(process: subprocess.Popen[bytes], payload: Mapping[str, Any]) -> None:
    if process.stdin is None:
        raise RuntimeError("TUI gateway stdin is unavailable")
    process.stdin.write((json.dumps(dict(payload), separators=(",", ":")) + "\n").encode())
    process.stdin.flush()


def _rpc_read(
    process: subprocess.Popen[bytes],
    buffer: bytearray,
    *,
    timeout_seconds: float,
) -> dict[str, Any] | None:
    if process.stdout is None:
        return None
    deadline = time.monotonic() + max(0.0, timeout_seconds)
    while True:
        if b"\n" in buffer:
            raw, _, remainder = buffer.partition(b"\n")
            buffer[:] = remainder
            try:
                value = json.loads(raw.decode("utf-8"))
            except (UnicodeError, json.JSONDecodeError):
                continue
            return value if isinstance(value, dict) else None
        wait = max(0.0, deadline - time.monotonic())
        if timeout_seconds <= 0:
            wait = 0.0
        ready, _, _ = select.select([process.stdout.fileno()], [], [], wait)
        if not ready:
            return None
        chunk = os.read(process.stdout.fileno(), 65536)
        if not chunk:
            return None
        buffer.extend(chunk)


def _rpc_wait(
    process: subprocess.Popen[bytes],
    buffer: bytearray,
    predicate,
    *,
    timeout_seconds: float,
) -> dict[str, Any] | None:
    deadline = time.monotonic() + timeout_seconds
    while process.poll() is None and time.monotonic() < deadline:
        item = _rpc_read(
            process,
            buffer,
            timeout_seconds=min(0.5, max(0.0, deadline - time.monotonic())),
        )
        if item is not None and predicate(item):
            return item
    return None


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
