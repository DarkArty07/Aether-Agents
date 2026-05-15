"""Aether continuity hooks — hermes-agent plugin that reads/writes project context.

This plugin registers 5 hooks in the hermes-agent lifecycle:
- on_pre_llm_call: injects [.aether Hot Start] context at session start
- on_session_start: creates session row in aether.db
- on_post_tool_call: records file changes (write_file, patch, git commit)
- on_post_llm_call: updates hot_state.last_request on first turn
- on_session_end: updates session status, hot_state in aether.db

Session ID resolution (priority order):
1. OLYMPUS_SESSION_ID env var (set at spawn time)
2. {HERMES_HOME}/.olympus_session.{pid} file (PID-suffixed, concurrent-safe)
3. {HERMES_HOME}/.olympus_session file (generic, backward compatible)

DB path resolution (priority order):
1. {HERMES_HOME}/.aether_home.{pid} — PID-suffixed file (concurrent-safe)
2. AETHER_HOME env var → .aether/aether.db
3. {HERMES_HOME}/.aether_home file → {path}/.aether/aether.db
4. cwd → .aether/aether.db

The plugin runs INSIDE the hermes-agent process. It uses synchronous
sqlite3 (not aiosqlite) because hooks are called synchronously.
"""

from __future__ import annotations

import logging
import os
import re
import time
from pathlib import Path
from typing import Any

from olympus_v3.aether_db import AetherDBSync, get_aether_db_path

logger = logging.getLogger("olympus_v3.aether_hooks")

# ---------------------------------------------------------------------------
# Module-level state
# ---------------------------------------------------------------------------

_aether_db: AetherDBSync | None = None
_turn_counter: int = 0
_session_id: str | None = None
_agent_name: str | None = None
_request: str | None = None


def _get_aether_db() -> AetherDBSync:
    """Lazy-init the sync database connection using get_aether_db_path().

    Priority for path resolution:
    1. PID-suffixed .aether_home.{pid} file in HERMES_HOME (concurrent-safe)
    2. Standard get_aether_db_path() resolution (AETHER_HOME env, .aether_home, cwd)
    """
    global _aether_db
    if _aether_db is None:
        # Try PID-suffixed .aether_home file first (concurrent-safe)
        hermes_home = os.environ.get("HERMES_HOME")
        if hermes_home:
            pid = os.getpid()
            pid_home_file = Path(hermes_home) / f".aether_home.{pid}"
            if pid_home_file.exists():
                try:
                    content = pid_home_file.read_text().strip()
                    if content:
                        db_path = Path(content) / ".aether" / "aether.db"
                        _aether_db = AetherDBSync(db_path=db_path)
                        _aether_db.ensure_tables()
                        logger.info(".aether hooks initialized with DB: %s (from PID file)", db_path)
                        return _aether_db
                except Exception as e:
                    logger.debug("Could not read PID aether_home file %s: %s", pid_home_file, e)

        # Fall back to standard resolution
        db_path = get_aether_db_path()
        _aether_db = AetherDBSync(db_path=db_path)
        _aether_db.ensure_tables()
        logger.info(".aether hooks initialized with DB: %s", db_path)
    return _aether_db


def _get_session_id(kwargs: dict[str, Any] | None = None) -> str | None:
    """Read session ID from env var, PID-suffixed file, generic file, or kwargs.

    Priority:
    1. OLYMPUS_SESSION_ID env var
    2. {HERMES_HOME}/.olympus_session.{pid} — PID-suffixed file (concurrent-safe)
    3. {HERMES_HOME}/.olympus_session — generic file (backward compatible)
    4. Previously cached value
    """
    global _session_id

    # Priority 1: env var
    sid = os.environ.get("OLYMPUS_SESSION_ID")
    if sid:
        _session_id = sid
        return sid

    # Priority 2: PID-suffixed file (concurrent-safe)
    hermes_home = os.environ.get("HERMES_HOME")
    if hermes_home:
        pid = os.getpid()
        pid_session_file = Path(hermes_home) / f".olympus_session.{pid}"
        if pid_session_file.exists():
            try:
                content = pid_session_file.read_text().strip()
                if content:
                    logger.debug("Read OLYMPUS_SESSION_ID from PID file: %s", content)
                    _session_id = content
                    return content
            except Exception as e:
                logger.debug("Could not read PID session file %s: %s", pid_session_file, e)

    # Priority 3: generic file (backward compatible)
    if hermes_home:
        session_file = Path(hermes_home) / ".olympus_session"
        try:
            content = session_file.read_text().strip()
            if content:
                logger.debug("Read OLYMPUS_SESSION_ID from file: %s", content)
                _session_id = content
                return content
        except FileNotFoundError:
            pass
        except Exception as e:
            logger.debug("Could not read session file %s: %s", session_file, e)

    # Priority 4: previously cached value
    if _session_id:
        return _session_id

    return None


def _detect_agent_name() -> str:
    """Detect the agent name from SOUL.md first line or profile directory name."""
    global _agent_name
    if _agent_name is not None:
        return _agent_name

    hermes_home = os.environ.get("HERMES_HOME")
    if hermes_home:
        # Try SOUL.md
        soul_file = Path(hermes_home) / "SOUL.md"
        try:
            first_line = soul_file.read_text().split("\n")[0].strip()
            if first_line:
                # Strip markdown heading markers
                name = first_line.lstrip("#").strip()
                if name:
                    _agent_name = name
                    return name
        except Exception:
            pass

        # Fallback: use profile directory name
        _agent_name = Path(hermes_home).name
        return _agent_name

    _agent_name = "unknown"
    return "unknown"


def _make_relative(file_path: str) -> str:
    """Make a file path relative to the project root detected from hot_state."""
    try:
        db = _get_aether_db()
        state = db.get_hot_state()
        if state and state.get("project_root"):
            root = state["project_root"]
            if file_path.startswith(root):
                return os.path.relpath(file_path, root)
    except Exception:
        pass
    return file_path


def _time_ago(updated_at: float) -> str:
    """Format a timestamp as a human-readable 'time ago' string."""
    if not updated_at or updated_at == 0:
        return "never"
    diff = time.time() - updated_at
    if diff < 60:
        return "just now"
    if diff < 3600:
        minutes = int(diff / 60)
        return f"{minutes}m ago"
    if diff < 86400:
        hours = int(diff / 3600)
        return f"{hours}h ago"
    days = int(diff / 86400)
    return f"{days}d ago"


def _format_hot_start(state: dict[str, Any], sessions: list[dict[str, Any]]) -> str:
    """Format the [.aether Hot Start] injection string.

    Builds a compact context string (max ~2000 chars) summarizing project
    state and recent session history for injection at the start of a new session.
    """
    lines = ["[.aether Hot Start]"]

    # Line 2: compact project info
    project_name = state.get("project_name") or "unknown"
    phase = state.get("current_phase") or "idea"
    total_sessions = state.get("total_sessions") or 0
    lines.append(f"Project: {project_name} | Phase: {phase} | {total_sessions} sessions")

    # Line 3: last agent and time
    last_agent = state.get("last_agent") or ""
    updated_at = state.get("updated_at") or 0
    time_str = _time_ago(updated_at)
    if last_agent:
        lines.append(f"Last: {last_agent}, {time_str}")

    # Request and result previews
    last_request = state.get("last_request") or ""
    last_result = state.get("last_result") or ""
    if last_request:
        lines.append(f"  Request: {last_request[:100]}")
    if last_result:
        lines.append(f"  Result: {last_result[:100]}")

    # Recent files
    recent_files = state.get("recent_files") or ""
    if recent_files:
        lines.append(f"Recent files: {recent_files}")

    # Current task
    current_task = state.get("current_task") or ""
    if current_task:
        lines.append(f"Task: {current_task}")

    # Blockers
    blockers = state.get("blockers") or ""
    lines.append(f"Blockers: {blockers or 'None'}")

    # Open issues count
    try:
        db = _get_aether_db()
        issue_count = db.get_open_issue_count()
        lines.append(f"Open issues: {issue_count}")
    except Exception:
        lines.append("Open issues: ?")

    # Recent sessions summary
    if sessions:
        lines.append("")
        for s in sessions:
            agent = s.get("agent") or "?"
            status = s.get("status") or "?"
            summary = s.get("result_summary") or ""
            summary_preview = summary[:80] + "..." if len(summary) > 80 else summary
            lines.append(f"  {agent} ({status}): {summary_preview}")

    result = "\n".join(lines)

    # Cap at ~2000 chars
    if len(result) > 2000:
        result = result[:1997] + "..."

    return result


# ---------------------------------------------------------------------------
# Hook implementations
# ---------------------------------------------------------------------------


def on_pre_llm_call(
    session_id: str,
    user_message: str,
    conversation_history: list,
    is_first_turn: bool,
    model: str,
    platform: str,
    sender_id: str,
    **kwargs: Any,
) -> dict | str | None:
    """Hook: inject [.aether Context] at the beginning of a session.

    On the first turn, if aether.db exists and CONTEXT.md exists and has
    content, returns it as context injection. Freshness is managed by
    aether_curate — Hermes decides when to re-curate. Otherwise returns
    None. Never crashes the agent — all logic wrapped in try/except.
    """
    if not is_first_turn:
        return None

    try:
        db_path = get_aether_db_path()
        if not db_path.exists():
            logger.debug(".aether database does not exist, skipping hot start injection")
            return None

        # Check CONTEXT.md: always inject if it exists and has content.
        # Freshness is managed by aether_curate — Hermes decides when to re-curate.
        context_md_path = db_path.parent / "CONTEXT.md"
        if context_md_path.exists():
            try:
                context_md_content = context_md_path.read_text().strip()
                if context_md_content:
                    logger.info(
                        "pre_llm_call: using CONTEXT.md (%d chars)",
                        len(context_md_content),
                    )
                    return {"context": f"[.aether Context]\n{context_md_content}"}
            except Exception as e:
                logger.debug("Failed to read CONTEXT.md, skipping injection: %s", e)

        # No CONTEXT.md available — skip injection entirely
        return None
    except Exception as e:
        logger.warning("pre_llm_call hook failed: %s", e)
        return None


def on_session_start(
    session_id: str,
    **kwargs: Any,
) -> None:
    """Hook: create a session row in aether.db when a session begins.

    Try/except silently — never crash the agent.
    """
    try:
        olympus_sid = _get_session_id(kwargs)
        if not olympus_sid:
            return

        db = _get_aether_db()
        agent = _detect_agent_name()
        model = kwargs.get("model")
        platform = kwargs.get("platform")

        db.insert_session(
            session_id=olympus_sid,
            agent=agent,
            model=model,
            platform=platform,
        )
        logger.info("on_session_start: session %s created for agent %s", olympus_sid, agent)
    except Exception as e:
        logger.warning("on_session_start hook failed: %s", e)


def on_post_tool_call(
    tool_name: str,
    args: dict | str,
    result: str,
    task_id: str,
    session_id: str,
    tool_call_id: str,
    duration_ms: int,
    **kwargs: Any,
) -> None:
    """Hook: detect file changes from write_file, patch, and git commit tools.

    Records file changes in aether.db for continuity tracking.
    Try/except silently — never crash the agent.
    """
    try:
        olympus_sid = _get_session_id(kwargs)
        if not olympus_sid:
            return

        db = _get_aether_db()
        agent = _detect_agent_name()

        # Detect write_file / patch file changes
        if tool_name in ("write_file", "patch"):
            if isinstance(args, dict):
                file_path = args.get("path") or args.get("file_path") or ""
            else:
                # args may be a string; try to extract path heuristically
                file_path = str(args)[:200] if args else ""

            if file_path:
                action = "write" if tool_name == "write_file" else "patch"
                file_path_rel = _make_relative(file_path)
                db.insert_file_change(
                    session_id=olympus_sid,
                    agent=agent,
                    file_path=file_path_rel,
                    action=action,
                )
                logger.debug(
                    "on_post_tool_call: recorded %s on %s for session %s",
                    action, file_path_rel, olympus_sid,
                )

        # Detect git commit in terminal
        elif tool_name == "terminal":
            result_str = str(result) if result else ""
            # Check for git commit info in the result
            if "git commit" in result_str or "commit " in result_str.lower():
                # Try to extract changed files from git output
                # Look for patterns like "create mode", "delete mode", "rewrite"
                file_patterns = re.findall(
                    r'(?:create|delete|rewrite)\s+mode\s+\d+\s+(.+)',
                    result_str,
                )
                if file_patterns:
                    for fp in file_patterns:
                        fp_rel = _make_relative(fp.strip())
                        db.insert_file_change(
                            session_id=olympus_sid,
                            agent=agent,
                            file_path=fp_rel,
                            action="commit",
                        )
                else:
                    # Record a generic commit entry
                    db.insert_file_change(
                        session_id=olympus_sid,
                        agent=agent,
                        file_path="(git commit)",
                        action="commit",
                    )
                logger.debug(
                    "on_post_tool_call: recorded git commit for session %s",
                    olympus_sid,
                )

    except Exception as e:
        logger.warning("on_post_tool_call hook failed: %s", e)


def on_post_llm_call(
    session_id: str,
    user_message: str,
    assistant_response: str,
    conversation_history: list,
    model: str,
    platform: str,
    **kwargs: Any,
) -> None:
    """Hook: update hot_state.last_request on first turn.

    On _turn_counter == 0: update hot_state.last_request with first ~200 chars
    of user_message. Then increment _turn_counter.
    Try/except silently — never crash the agent.
    """
    global _turn_counter, _request

    try:
        if _turn_counter == 0:
            request_preview = (user_message or "")[:200]
            db = _get_aether_db()
            updates = {"last_request": request_preview}
            # Write project_root from AETHER_HOME to hot_state for project identity
            aether_home = os.environ.get("AETHER_HOME")
            if aether_home:
                updates["project_root"] = aether_home
            db.update_hot_state(**updates)
            _request = request_preview
            logger.debug("on_post_llm_call: updated hot_state.last_request")

        _turn_counter += 1
    except Exception as e:
        logger.warning("on_post_llm_call hook failed: %s", e)


def on_session_end(
    session_id: str,
    completed: bool,
    interrupted: bool,
    model: str,
    platform: str,
    **kwargs: Any,
) -> None:
    """Hook: update session status and hot_state at session end.

    Update session status (completed/interrupted/failed).
    Try to get last turn result from olympus_v3 db for result_summary.
    Update hot_state: last_agent, last_session_id, last_result, updated_at,
    total_sessions++.
    Try/except silently — never crash the agent.
    """
    try:
        olympus_sid = _get_session_id(kwargs)
        if not olympus_sid:
            return

        status = "completed" if completed else ("cancelled" if interrupted else "error")

        db = _get_aether_db()

        # Update session status
        db.update_session(
            session_id=olympus_sid,
            status=status,
        )

        # Try to get result summary from olympus_v3.db last turn
        result_summary = None
        try:
            from olympus_v3.db import OlympusDBSync, get_db_path

            olympus_db = OlympusDBSync(db_path=get_db_path())
            progress = olympus_db.get_session_progress(olympus_sid)
            if progress and progress.get("last_turn"):
                result_summary = progress["last_turn"][:500]
        except Exception as e:
            logger.debug("Could not read olympus_v3.db for result summary: %s", e)

        # Update session with result if available
        if result_summary:
            db.update_session(
                session_id=olympus_sid,
                result_summary=result_summary,
            )

        # Update hot_state: last_agent, last_session_id, last_result,
        # updated_at, total_sessions++
        state = db.get_hot_state()
        total = (state.get("total_sessions") or 0) if state else 0

        hot_state_updates = {
            "last_agent": _detect_agent_name(),
            "last_session_id": olympus_sid,
            "last_result": result_summary or status,
            "total_sessions": total + 1,
        }
        if interrupted:
            hot_state_updates["last_error"] = "Session interrupted"

        # Write project_root from AETHER_HOME to hot_state for project identity
        aether_home = os.environ.get("AETHER_HOME")
        if aether_home:
            hot_state_updates["project_root"] = aether_home

        db.update_hot_state(**hot_state_updates)

        logger.info("on_session_end: session %s marked as %s", olympus_sid, status)
    except Exception as e:
        logger.warning("on_session_end hook failed: %s", e)


# ---------------------------------------------------------------------------
# Plugin registration
# ---------------------------------------------------------------------------


def register(ctx):
    """Register .aether continuity hooks into the hermes-agent plugin system.

    Usage in profile's plugin config:
        plugins:
          - name: aether_hooks
            path: /path/to/aether_hooks
    """
    ctx.register_hook("pre_llm_call", on_pre_llm_call)
    ctx.register_hook("on_session_start", on_session_start)
    ctx.register_hook("post_tool_call", on_post_tool_call)
    ctx.register_hook("post_llm_call", on_post_llm_call)
    ctx.register_hook("on_session_end", on_session_end)

    logger.info(
        ".aether continuity hooks registered "
        "(pre_llm_call, on_session_start, post_tool_call, post_llm_call, on_session_end)"
    )
