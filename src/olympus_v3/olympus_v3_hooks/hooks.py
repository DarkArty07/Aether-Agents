"""Olympus v3 hooks — hermes-agent plugin that writes per-turn data to SQLite.

This plugin registers 4 hooks in the hermes-agent lifecycle:
- post_llm_call: writes complete turn content + reasoning to SQLite
- post_tool_call: writes tool call + result to SQLite
- on_session_end: marks session as completed in SQLite
- pre_llm_call: reads steering directives from SQLite and injects context

Session ID resolution (priority order):
1. OLYMPUS_SESSION_ID env var (set at spawn time)
2. {HERMES_HOME}/.olympus_session file (written by MCP server before each message)

DB path resolution (priority order):
1. OLYMPUS_DB_PATH env var
2. {AETHER_HOME}/.olympus_db_path file
3. get_db_path() fallback

The plugin runs INSIDE the hermes-agent process. It uses synchronous
sqlite3 (not aiosqlite) because hooks are called synchronously.
"""

from __future__ import annotations

import json
import logging
import os
import time
from pathlib import Path
from typing import Any

from olympus_v3.db import OlympusDBSync, get_db_path

logger = logging.getLogger("olympus_v3.hooks")

# ---------------------------------------------------------------------------
# Module-level state
# ---------------------------------------------------------------------------

_db: OlympusDBSync | None = None
_session_id: str | None = None
_turn_counter: int = 0


def _get_db() -> OlympusDBSync:
    """Lazy-init the sync database connection.
    
    DB path resolution: OLYMPUS_DB_PATH env > {AETHER_HOME}/.olympus_db_path file > get_db_path().
    """
    global _db
    if _db is None:
        # Priority 1: env var
        db_path = os.environ.get("OLYMPUS_DB_PATH")
        if db_path:
            logger.debug("Using OLYMPUS_DB_PATH from env: %s", db_path)
        else:
            # Priority 2: file fallback
            aether_home = os.environ.get("AETHER_HOME")
            if aether_home:
                db_path_file = Path(aether_home) / ".olympus_db_path"
                try:
                    file_path = db_path_file.read_text().strip()
                    if file_path:
                        db_path = file_path
                        logger.debug("Using DB path from file: %s", db_path)
                except FileNotFoundError:
                    pass
                except Exception as e:
                    logger.debug("Could not read DB path file %s: %s", db_path_file, e)
        
        # Priority 3: fallback
        if not db_path:
            db_path = get_db_path()
        
        _db = OlympusDBSync(db_path=Path(db_path) if db_path else None)
        _db.ensure_tables()
        logger.info("Olympus v3 hooks initialized with DB: %s", db_path)
    return _db


def _get_session_id() -> str | None:
    """Read session ID from env var, PID-suffixed file, or file fallback.

    Priority:
    1. OLYMPUS_SESSION_ID env var
    2. {HERMES_HOME}/.olympus_session.{PID} (written by acp_manager)
    3. {HERMES_HOME}/.olympus_session (legacy fallback)
    """
    # Priority 1: env var
    sid = os.environ.get("OLYMPUS_SESSION_ID")
    if sid:
        return sid

    # Priority 2: PID-suffixed file (written by acp_manager for ACP sessions)
    hermes_home = os.environ.get("HERMES_HOME")
    if hermes_home:
        pid = os.getpid()
        pid_file = Path(hermes_home) / f".olympus_session.{pid}"
        try:
            content = pid_file.read_text().strip()
            if content:
                logger.debug("Read OLYMPUS_SESSION_ID from PID file %s: %s", pid_file, content)
                return content
        except FileNotFoundError:
            pass
        except Exception as e:
            logger.debug("Could not read PID session file %s: %s", pid_file, e)

    # Priority 3: legacy non-suffixed file
    if hermes_home:
        session_file = Path(hermes_home) / ".olympus_session"
        try:
            content = session_file.read_text().strip()
            if content:
                logger.debug("Read OLYMPUS_SESSION_ID from file: %s", content)
                return content
        except FileNotFoundError:
            pass
        except Exception as e:
            logger.debug("Could not read session file %s: %s", session_file, e)

    return None


# ---------------------------------------------------------------------------
# Hook implementations
# ---------------------------------------------------------------------------


def on_post_llm_call(
    session_id: str,
    user_message: str,
    assistant_response: str,
    conversation_history: list,
    model: str,
    platform: str,
    **kwargs: Any,
) -> None:
    """Hook: write complete turn content + reasoning to SQLite.

    Called after each LLM turn completes. Extracts reasoning from the
    conversation history (last assistant message's reasoning field).
    """
    global _turn_counter

    olympus_sid = _get_session_id()
    if not olympus_sid:
        logger.debug("No OLYMPUS_SESSION_ID, skipping post_llm_call")
        return

    _turn_counter += 1

    # Extract reasoning from the last assistant message in history
    reasoning = None
    for msg in reversed(conversation_history):
        if msg.get("role") == "assistant" and msg.get("reasoning"):
            reasoning = msg["reasoning"]
            break

    # Extract token info if available in kwargs
    metadata = {"model": model, "platform": platform}

    try:
        db = _get_db()
        db.insert_turn(
            session_id=olympus_sid,
            turn_num=_turn_counter,
            role="assistant",
            content=assistant_response,
            reasoning=reasoning,
            metadata=metadata,
        )
        logger.debug(
            "post_llm_call: wrote turn %d for session %s (%d chars)",
            _turn_counter, olympus_sid, len(assistant_response or ""),
        )
    except Exception as e:
        logger.warning("post_llm_call hook failed: %s", e)


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
    """Hook: write tool call + result to SQLite.

    Called after each tool dispatch completes.
    """
    olympus_sid = _get_session_id()
    if not olympus_sid:
        logger.debug("No OLYMPUS_SESSION_ID, skipping post_tool_call")
        return

    # Normalize args to JSON string
    if isinstance(args, dict):
        args_json = json.dumps(args, default=str)
    else:
        args_json = str(args) if args else None

    # Truncate result if very large (keep first 10KB)
    result_str = str(result) if result else None
    if result_str and len(result_str) > 10000:
        result_str = result_str[:10000] + "...[truncated]"

    try:
        db = _get_db()
        db.insert_tool_call(
            call_id=tool_call_id or f"tool_{int(time.time()*1000)}",
            session_id=olympus_sid,
            tool_name=tool_name,
            arguments=args_json,
            result=result_str,
            status="completed",
        )
        logger.debug(
            "post_tool_call: wrote tool %s for session %s (%dms)",
            tool_name, olympus_sid, duration_ms,
        )
    except Exception as e:
        logger.warning("post_tool_call hook failed: %s", e)


def on_session_end(
    session_id: str,
    completed: bool,
    interrupted: bool,
    model: str,
    platform: str,
    **kwargs: Any,
) -> None:
    """Hook: mark session as completed or error in SQLite.

    Called when the hermes-agent session ends (normally or interrupted).
    """
    olympus_sid = _get_session_id()
    if not olympus_sid:
        logger.debug("No OLYMPUS_SESSION_ID, skipping on_session_end")
        return

    status = "completed" if completed else ("cancelled" if interrupted else "error")

    try:
        db = _get_db()
        db.update_session_status(olympus_sid, status)
        logger.info("on_session_end: session %s marked as %s", olympus_sid, status)
    except Exception as e:
        logger.warning("on_session_end hook failed: %s", e)


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
    """Hook: read steering directives from SQLite and inject as context.

    Returns a dict with 'context' key or a string to be injected into
    the user message. Returns None if no pending directives.

    This enables the orchestrator (Hermes) to steer a Daimon mid-execution
    by writing directives to the steering table.
    """
    olympus_sid = _get_session_id()
    if not olympus_sid:
        logger.debug("No OLYMPUS_SESSION_ID, skipping pre_llm_call")
        return None

    try:
        db = _get_db()
        directives = db.consume_steering(olympus_sid)
        if directives:
            context = "\n".join(directives)
            logger.info(
                "pre_llm_call: injected %d steering directive(s) for session %s",
                len(directives), olympus_sid,
            )
            return {"context": f"[Olympus Steering]\n{context}"}
    except Exception as e:
        logger.warning("pre_llm_call hook failed: %s", e)

    return None


# ---------------------------------------------------------------------------
# Plugin registration
# ---------------------------------------------------------------------------


def register(ctx):
    """Register Olympus v3 hooks into the hermes-agent plugin system.

    Usage in profile's plugin config:
        plugins:
          - name: olympus_v3_hooks
            path: /path/to/olympus_v3_hooks
    """
    ctx.register_hook("post_llm_call", on_post_llm_call)
    ctx.register_hook("post_tool_call", on_post_tool_call)
    ctx.register_hook("on_session_end", on_session_end)
    ctx.register_hook("pre_llm_call", on_pre_llm_call)

    logger.info("Olympus v3 hooks registered (post_llm_call, post_tool_call, "
                 "on_session_end, pre_llm_call)")
