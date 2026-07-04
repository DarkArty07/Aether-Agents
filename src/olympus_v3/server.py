"""Olympus v3 MCP Server — ACP + Plugin hooks + SQLite.

Exposes 3 MCP tools to Hermes:
- talk_to: open, message, poll, close, cancel, delegate, steer Daimon sessions
- discover: list available Daimon profiles
- consult: consulting workflow (start, run, sign, add_agent, status, complete)

Architecture overview:
    Hermes (MCP client)
        -> MCP stdio
            -> server.py (this file)
                -> ACPManager (subprocess lifecycle via agent-client-protocol)
                -> OlympusDB (async SQLite reads/writes)
                -> consult_action.py (consult workflow)

Poll reads from SQLite (not ACP streaming). Plugin hooks on the Daimon side
write per-turn data to the same SQLite database.
"""

from __future__ import annotations

import asyncio
import json
import logging
import sys
import time
from datetime import datetime
from pathlib import Path

from mcp import types as mcp_types
from mcp.server import Server
from mcp.server.stdio import stdio_server

from .acp_manager import ACPManager
from .aether_db import AetherDB, resolve_aether_db, resolve_aether_dir
from .db import OlympusDB, get_db_path

logger = logging.getLogger("olympus_v3")

# ---------------------------------------------------------------------------
# Poll / stall detection constants
# ---------------------------------------------------------------------------

POLL_INTERVAL = 15  # seconds between polls when delegating
STALL_TIMEOUT = 120  # seconds with zero activity before considering stalled
MAX_POLL_ITERATIONS = 200  # safety limit for delegate loops

# ---------------------------------------------------------------------------
# Server setup
# ---------------------------------------------------------------------------

app = Server("olympus-v3")

# Global state — initialized in main()
_db: OlympusDB | None = None
_manager: ACPManager | None = None


def _get_db() -> OlympusDB:
    """Get the global database instance."""
    global _db
    if _db is None:
        raise RuntimeError("Database not initialized. Call init_server() first.")
    return _db


def _get_manager() -> ACPManager:
    """Get the global ACP manager instance."""
    global _manager
    if _manager is None:
        raise RuntimeError("Manager not initialized. Call init_server() first.")
    return _manager


async def init_server() -> None:
    """Initialize database connection and ACP manager."""
    global _db, _manager

    db_path = get_db_path()
    _db = OlympusDB(db_path=db_path)
    await _db.connect()
    logger.info("Database connected: %s", db_path)

    from .config_loader import get_config
    config = get_config()
    _manager = ACPManager(profiles_dir=config.profiles_dir, db=_db)
    logger.info("ACP manager initialized with profiles_dir: %s", config.profiles_dir)


# ---------------------------------------------------------------------------
# Helper: build progress dict from SQLite
# ---------------------------------------------------------------------------

async def _build_response(session_id: str) -> dict:
    """Build a response dict from SQLite for a session.

    Returns dict with: session_id, status, thoughts, messages,
    tool_calls, response, elapsed_seconds.
    """
    db = _get_db()
    progress = await db.get_session_progress(session_id)

    return {
        "session_id": session_id,
        "status": progress.get("status", "unknown"),
        "thoughts": progress.get("thoughts", 0),
        "messages": progress.get("messages", 0),
        "tool_calls": progress.get("tool_calls", 0),
        "response": progress.get("last_turn"),
    }


# ---------------------------------------------------------------------------
# Tool: talk_to
# ---------------------------------------------------------------------------

@app.list_tools()
async def list_tools() -> list[mcp_types.Tool]:
    return [
        mcp_types.Tool(
            name="talk_to",
            description=(
                "Communicate with Aether Daimon agents via ACP. "
                "Actions: open (spawn agent), message (send prompt), "
                "poll (check progress), close (end session), "
                "cancel (force-terminate), delegate (auto-poll until done), "
                "steer (inject directive into Daimon context)."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "agent": {
                        "type": "string",
                        "description": "Daimon profile name, or '?' to discover available agents.",
                    },
                    "action": {
                        "type": "string",
                        "enum": ["open", "message", "poll", "close", "cancel", "delegate", "steer"],
                        "description": "Action to perform.",
                    },
                    "session_id": {
                        "type": "string",
                        "description": "Session ID (required for message, poll, close, cancel).",
                    },
                    "prompt": {
                        "type": "string",
                        "description": "Prompt text (required for message and delegate).",
                    },
                    "poll_interval": {
                        "type": "integer",
                        "description": "Seconds between polls for delegate action (default 15).",
                        "default": 15,
                    },
                    "timeout": {
                        "type": "integer",
                        "description": "Max seconds for delegate action (default 300).",
                        "default": 300,
                    },
                    "project_root": {
                        "type": "string",
                        "description": "Absolute path to the project root. Forces the Daimon to work in this directory and sets AETHER_HOME. Required for open and delegate actions.",
                    },
                    "directive": {
                        "type": "string",
                        "description": "Directive text to inject into Daimon's context (required for steer action).",
                    },
                    "priority": {
                        "type": "integer",
                        "description": "Priority for steering directive (default 0, higher = more important).",
                        "default": 0,
                    },
                },
                "required": ["action"],
            },
        ),
        mcp_types.Tool(
            name="discover",
            description="List available Daimon agents and their capabilities.",
            inputSchema={"type": "object", "properties": {}, "required": []},
        ),
        mcp_types.Tool(
            name="aether_status",
            description=(
                "Query the .aether continuity database for project state. "
                "Returns hot state, session/issue/decision counts (summary), "
                "or full detail with recent sessions, file changes, decisions, and issues."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "project_root": {
                        "type": "string",
                        "description": "Absolute path to the project root. Used to resolve the .aether database path. REQUIRED.",
                    },
                    "detail": {
                        "type": "string",
                        "enum": ["summary", "full"],
                        "default": "summary",
                        "description": "Detail level: 'summary' for counts, 'full' for recent records.",
                    },
                },
                "required": ["project_root"],
            },
        ),
        mcp_types.Tool(
            name="aether_update",
            description=(
                "Update the .aether continuity database: set phase/task, manage blockers, "
                "add decisions and issues, resolve issues."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "project_root": {
                        "type": "string",
                        "description": "Absolute path to the project root. Used to resolve the .aether database path. REQUIRED.",
                    },
                    "action": {
                        "type": "string",
                        "enum": [
                            "set_phase", "set_task", "add_blocker", "remove_blocker",
                            "add_decision", "add_issue", "resolve_issue",
                        ],
                        "description": "Action to perform.",
                    },
                    "phase": {"type": "string", "description": "New phase (for set_phase)."},
                    "task": {"type": "string", "description": "New task (for set_task)."},
                    "blocker": {"type": "string", "description": "Blocker text (for add_blocker / remove_blocker)."},
                    "title": {"type": "string", "description": "Decision title (for add_decision)."},
                    "decision": {"type": "string", "description": "Decision text (for add_decision)."},
                    "rationale": {"type": "string", "description": "Decision rationale (for add_decision, optional)."},
                    "alternatives": {"type": "string", "description": "Decision alternatives (for add_decision, optional)."},
                    "description": {"type": "string", "description": "Issue description (for add_issue)."},
                    "error_type": {"type": "string", "description": "Issue error type (for add_issue, optional)."},
                    "session_id": {"type": "string", "description": "Issue session ID (for add_issue, optional)."},
                    "issue_id": {"type": "integer", "description": "Issue ID (for resolve_issue)."},
                    "resolution": {"type": "string", "description": "Resolution text (for resolve_issue)."},
                    "resolved_by": {"type": "string", "description": "Who resolved it (for resolve_issue, default 'hermes')."},
                },
                "required": ["action", "project_root"],
            },
        ),
        mcp_types.Tool(
            name="aether_curate",
            description=(
                "Invoke Ariadna to curate raw .aether data into a CONTEXT.md file. "
                "Ariadna reads aether.db, synthesizes project state, and writes .aether/CONTEXT.md. "
                "The curated context is then injected into Daimon sessions instead of raw data."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "project_root": {
                        "type": "string",
                        "description": "Absolute path to the project root. The .aether/ directory must exist here. REQUIRED.",
                    },
                    "focus": {
                        "type": "string",
                        "enum": ["full", "recent", "decisions"],
                        "default": "recent",
                        "description": "Focus area for curation: full (all data), recent (last 5 sessions), decisions (architectural decisions only).",
                    },
                },
                "required": ["project_root"],
            },
        ),
    ]


# ---------------------------------------------------------------------------
# talk_to handler
# ---------------------------------------------------------------------------

@app.call_tool()
async def call_tool(name: str, arguments: dict) -> list[mcp_types.TextContent]:
    if name == "talk_to":
        return await _handle_talk_to(arguments)
    elif name == "discover":
        return await _handle_discover()
    elif name == "aether_status":
        return await _handle_aether_status(arguments)
    elif name == "aether_update":
        return await _handle_aether_update(arguments)
    elif name == "aether_curate":
        return await _handle_aether_curate(arguments)
    else:
        return [mcp_types.TextContent(type="text", text=f"Unknown tool: {name}")]


async def _handle_talk_to(args: dict) -> list[mcp_types.TextContent]:
    """Handle talk_to tool calls."""
    action = args.get("action", "")
    manager = _get_manager()

    # ------------------------------------------------------------------
    # OPEN — spawn agent and create session
    # ------------------------------------------------------------------
    if action == "open":
        agent = args.get("agent", "")
        if not agent:
            return [mcp_types.TextContent(type="text", text="Error: 'agent' is required for open action.")]

        try:
            session_id = await manager.spawn_agent(
                agent_name=agent,
                project_root=args.get("project_root"),
            )
            result = await _build_response(session_id)
            return [mcp_types.TextContent(type="text", text=json.dumps(result, indent=2))]
        except Exception as e:
            logger.error("Failed to open session for %s: %s", agent, e)
            return [mcp_types.TextContent(type="text", text=f"Error opening session: {e}")]

    # ------------------------------------------------------------------
    # MESSAGE — send prompt to active session
    # ------------------------------------------------------------------
    elif action == "message":
        session_id = args.get("session_id", "")
        prompt = args.get("prompt", "")
        if not session_id:
            return [mcp_types.TextContent(type="text", text="Error: 'session_id' is required for message action.")]
        if not prompt:
            return [mcp_types.TextContent(type="text", text="Error: 'prompt' is required for message action.")]

        try:
            result = await manager.send_message(session_id, prompt)
            return [mcp_types.TextContent(type="text", text=json.dumps(result, indent=2))]
        except Exception as e:
            logger.error("Failed to send message to %s: %s", session_id, e)
            return [mcp_types.TextContent(type="text", text=f"Error sending message: {e}")]

    # ------------------------------------------------------------------
    # POLL — read progress from SQLite
    # ------------------------------------------------------------------
    elif action == "poll":
        session_id = args.get("session_id", "")
        if not session_id:
            return [mcp_types.TextContent(type="text", text="Error: 'session_id' is required for poll action.")]

        try:
            result = await manager.poll(session_id)
            return [mcp_types.TextContent(type="text", text=json.dumps(result, indent=2))]
        except Exception as e:
            logger.error("Failed to poll session %s: %s", session_id, e)
            return [mcp_types.TextContent(type="text", text=f"Error polling session: {e}")]

    # ------------------------------------------------------------------
    # CLOSE — end session gracefully
    # ------------------------------------------------------------------
    elif action == "close":
        session_id = args.get("session_id", "")
        if not session_id:
            return [mcp_types.TextContent(type="text", text="Error: 'session_id' is required for close action.")]

        try:
            result = await manager.close(session_id)
            status = await _build_response(session_id)
            # Merge close result with final status
            status.update(result)
            return [mcp_types.TextContent(type="text", text=json.dumps(status, indent=2))]
        except Exception as e:
            logger.error("Failed to close session %s: %s", session_id, e)
            return [mcp_types.TextContent(type="text", text=f"Error closing session: {e}")]

    # ------------------------------------------------------------------
    # CANCEL — force-terminate session
    # ------------------------------------------------------------------
    elif action == "cancel":
        session_id = args.get("session_id", "")
        if not session_id:
            return [mcp_types.TextContent(type="text", text="Error: 'session_id' is required for cancel action.")]

        try:
            result = await manager.cancel(session_id)
            return [mcp_types.TextContent(type="text", text=json.dumps(result, indent=2))]
        except Exception as e:
            logger.error("Failed to cancel session %s: %s", session_id, e)
            return [mcp_types.TextContent(type="text", text=f"Error cancelling session: {e}")]

    # ------------------------------------------------------------------
    # STEER — inject directive into Daimon context
    # ------------------------------------------------------------------
    elif action == "steer":
        session_id = args.get("session_id", "")
        directive = args.get("directive", "")
        if not session_id:
            return [mcp_types.TextContent(type="text", text="Error: 'session_id' is required for steer action.")]
        if not directive:
            return [mcp_types.TextContent(type="text", text="Error: 'directive' is required for steer action.")]
        try:
            db = _get_db()
            row_id = await db.insert_steering(session_id, directive, args.get("priority", 0))
            return [mcp_types.TextContent(type="text", text=json.dumps({"status": "steered", "steering_id": row_id, "session_id": session_id}, indent=2))]
        except Exception as e:
            logger.error("Steer error for session %s: %s", session_id, e)
            return [mcp_types.TextContent(type="text", text=f"Error steering session: {e}")]

    # ------------------------------------------------------------------
    # DELEGATE — open + message + auto-poll until done
    # ------------------------------------------------------------------
    elif action == "delegate":
        agent = args.get("agent", "")
        prompt = args.get("prompt", "")
        poll_interval = args.get("poll_interval", POLL_INTERVAL)
        timeout = args.get("timeout", 300)

        if not agent:
            return [mcp_types.TextContent(type="text", text="Error: 'agent' is required for delegate action.")]
        if not prompt:
            return [mcp_types.TextContent(type="text", text="Error: 'prompt' is required for delegate action.")]

        start_time = time.time()

        # Spawn agent
        try:
            session_id = await manager.spawn_agent(
                agent_name=agent,
                project_root=args.get("project_root"),
            )
        except Exception as e:
            logger.error("Delegate: failed to spawn %s: %s", agent, e)
            return [mcp_types.TextContent(type="text", text=f"Error spawning agent: {e}")]

        # Send prompt
        try:
            await manager.send_message(session_id, prompt)
        except Exception as e:
            logger.error("Delegate: failed to send prompt to %s: %s", session_id, e)
            return [mcp_types.TextContent(type="text", text=json.dumps({
                "session_id": session_id,
                "status": "error",
                "error": f"Failed to send prompt: {e}",
                "elapsed_seconds": time.time() - start_time,
            }, indent=2))]

        # Auto-poll loop
        poll_iterations = 0
        last_thoughts = 0
        last_messages = 0
        last_tool_calls = 0
        stall_count = 0

        while True:
            await asyncio.sleep(poll_interval)
            poll_iterations += 1
            elapsed = time.time() - start_time

            # Read from SQLite
            try:
                progress = await manager.poll(session_id)
            except Exception as e:
                logger.warning("Delegate: poll error for %s: %s", session_id, e)
                continue

            status = progress.get("status", "unknown")

            # Check for completion
            if status in ("completed", "error", "cancelled"):
                progress["timed_out"] = False
                progress["elapsed_seconds"] = round(elapsed, 1)
                progress["poll_iterations"] = poll_iterations
                progress["session_id"] = session_id

                # Detect CLARIFICATION NEEDED pattern
                last_turn = progress.get("last_turn") or ""
                if status == "completed" and "CLARIFICATION" in last_turn.upper() and "NEEDED" in last_turn.upper():
                    progress["status"] = "clarification_needed"
                    progress["clarification_needed"] = True
                    # Session stays open for follow-up
                    return [mcp_types.TextContent(type="text", text=json.dumps(progress, indent=2))]

                # Don't auto-close session on completion — Hermes can continue with message() or close it explicitly
                # Only auto-close on error or cancelled (safety)
                if status == "error":
                    try:
                        await manager.close(session_id)
                    except Exception:
                        pass
                return [mcp_types.TextContent(type="text", text=json.dumps(progress, indent=2))]

            # Check for timeout
            if elapsed >= timeout:
                progress["timed_out"] = True
                progress["elapsed_seconds"] = round(elapsed, 1)
                progress["poll_iterations"] = poll_iterations
                progress["session_id"] = session_id
                return [mcp_types.TextContent(type="text", text=json.dumps(progress, indent=2))]

            # Check for stall (no progress for STALL_TIMEOUT seconds)
            current_thoughts = progress.get("thoughts", 0)
            current_messages = progress.get("messages", 0)
            current_tool_calls = progress.get("tool_calls", 0)

            if (current_thoughts == last_thoughts and
                current_messages == last_messages and
                current_tool_calls == last_tool_calls):
                stall_count += 1
                # Active session: give more time (2x STALL_TIMEOUT) since
                # hooks write data after completion, not during processing
                active_stall_limit = STALL_TIMEOUT * 2 if status == "active" else STALL_TIMEOUT
                if stall_count * poll_interval >= active_stall_limit:
                    progress["timed_out"] = False
                    progress["stalled"] = True
                    progress["elapsed_seconds"] = round(elapsed, 1)
                    progress["poll_iterations"] = poll_iterations
                    progress["session_id"] = session_id
                    return [mcp_types.TextContent(type="text", text=json.dumps(progress, indent=2))]
            else:
                stall_count = 0

            last_thoughts = current_thoughts
            last_messages = current_messages
            last_tool_calls = current_tool_calls

            # Safety limit
            if poll_iterations >= MAX_POLL_ITERATIONS:
                progress["session_id"] = session_id
                progress["timed_out"] = True
                progress["elapsed_seconds"] = round(elapsed, 1)
                progress["poll_iterations"] = poll_iterations
                progress["reason"] = "max_poll_iterations_reached"
                return [mcp_types.TextContent(type="text", text=json.dumps(progress, indent=2))]

    else:
        return [mcp_types.TextContent(type="text", text=f"Unknown action: {action}")]


# ---------------------------------------------------------------------------
# discover handler
# ---------------------------------------------------------------------------

async def _handle_discover() -> list[mcp_types.TextContent]:
    """List available Daimon profiles."""
    manager = _get_manager()
    profiles = manager.discover()

    result = {
        "agents": profiles,
        "count": len(profiles),
    }
    return [mcp_types.TextContent(type="text", text=json.dumps(result, indent=2))]


# ---------------------------------------------------------------------------
# aether_status handler
# ---------------------------------------------------------------------------

async def _handle_aether_status(args: dict) -> list[mcp_types.TextContent]:
    """Query the .aether continuity database for project state."""
    project_root = args.get("project_root", "")
    if not project_root:
        return [mcp_types.TextContent(type="text", text="Error: 'project_root' is required for aether_status.")]

    try:
        db_path = resolve_aether_db(project_root)
        db = AetherDB(db_path=db_path)
        await db.connect()
        try:
            hot_state = await db.get_hot_state()

            # Counts in a single query
            cursor = await db._execute(
                """
                SELECT
                    (SELECT COUNT(*) FROM sessions),
                    (SELECT COUNT(*) FROM issues),
                    (SELECT COUNT(*) FROM decisions)
                """
            )
            row = await cursor.fetchone()
            sessions_count = row[0]
            issues_count = row[1]
            decisions_count = row[2]

            detail = args.get("detail", "summary")

            if detail == "summary":
                result = {
                    "hot_state": hot_state,
                    "sessions_count": sessions_count,
                    "issues_count": issues_count,
                    "decisions_count": decisions_count,
                }
            else:  # full
                recent_sessions = await db.get_recent_sessions(limit=5)
                recent_files = await db.get_recent_files(limit=10)

                cursor = await db._execute(
                    "SELECT * FROM decisions ORDER BY created_at DESC LIMIT 5"
                )
                rows = await cursor.fetchall()
                recent_decisions = [dict(row) for row in rows]

                cursor = await db._execute(
                    "SELECT * FROM issues WHERE status = 'open' ORDER BY created_at DESC"
                )
                rows = await cursor.fetchall()
                open_issues = [dict(row) for row in rows]

                cursor = await db._execute(
                    "SELECT * FROM issues ORDER BY created_at DESC LIMIT 5"
                )
                rows = await cursor.fetchall()
                recent_issues = [dict(row) for row in rows]

                result = {
                    "hot_state": hot_state,
                    "recent_sessions": recent_sessions,
                    "recent_file_changes": recent_files,
                    "recent_decisions": recent_decisions,
                    "open_issues": open_issues,
                    "recent_issues": recent_issues,
                }

            return [mcp_types.TextContent(type="text", text=json.dumps(result, indent=2, default=str))]
        finally:
            await db.close()
    except Exception as e:
        logger.error("aether_status error: %s", e)
        return [mcp_types.TextContent(type="text", text=f"Error querying aether status: {e}")]


# ---------------------------------------------------------------------------
# aether_update handler
# ---------------------------------------------------------------------------

async def _handle_aether_update(args: dict) -> list[mcp_types.TextContent]:
    """Update the .aether continuity database."""
    project_root = args.get("project_root", "")
    if not project_root:
        return [mcp_types.TextContent(type="text", text="Error: 'project_root' is required for aether_update.")]

    try:
        db_path = resolve_aether_db(project_root)
        db = AetherDB(db_path=db_path)
        await db.connect()
        try:
            action = args.get("action", "")

            if action == "set_phase":
                phase = args.get("phase", "")
                await db.update_hot_state(current_phase=phase)
                return [mcp_types.TextContent(type="text", text=f"Phase updated to: {phase}")]

            elif action == "set_task":
                task = args.get("task", "")
                await db.update_hot_state(current_task=task)
                return [mcp_types.TextContent(type="text", text=f"Task updated to: {task}")]

            elif action == "add_blocker":
                blocker = args.get("blocker", "")
                hot_state = await db.get_hot_state()
                blockers_raw = hot_state.get("blockers", "[]") if hot_state else "[]"
                blockers = json.loads(blockers_raw) if blockers_raw else []
                blockers.append(blocker)
                await db.update_hot_state(blockers=json.dumps(blockers))
                return [mcp_types.TextContent(type="text", text=f"Blocker added: {blocker}")]

            elif action == "remove_blocker":
                blocker = args.get("blocker", "")
                hot_state = await db.get_hot_state()
                blockers_raw = hot_state.get("blockers", "[]") if hot_state else "[]"
                blockers = json.loads(blockers_raw) if blockers_raw else []
                blockers = [b for b in blockers if b != blocker]
                await db.update_hot_state(blockers=json.dumps(blockers))
                return [mcp_types.TextContent(type="text", text=f"Blocker removed: {blocker}")]

            elif action == "add_decision":
                title = args.get("title", "")
                decision = args.get("decision", "")
                rationale = args.get("rationale")
                alternatives = args.get("alternatives")
                row_id = await db.insert_decision(
                    title=title, decision=decision,
                    rationale=rationale, alternatives=alternatives,
                )
                return [mcp_types.TextContent(type="text", text=f"Decision added (id={row_id}): {title}")]

            elif action == "add_issue":
                description = args.get("description", "")
                error_type = args.get("error_type")
                session_id = args.get("session_id")
                row_id = await db.insert_issue(
                    description=description, error_type=error_type,
                    session_id=session_id,
                )
                return [mcp_types.TextContent(type="text", text=f"Issue added (id={row_id}): {description}")]

            elif action == "resolve_issue":
                issue_id = args.get("issue_id")
                resolution = args.get("resolution", "")
                resolved_by = args.get("resolved_by", "hermes")
                await db.resolve_issue(
                    issue_id=int(issue_id), resolution=resolution,
                    resolved_by=resolved_by,
                )
                return [mcp_types.TextContent(type="text", text=f"Issue {issue_id} resolved by {resolved_by}")]

            else:
                return [mcp_types.TextContent(type="text", text=f"Unknown action: {action}")]
        finally:
            await db.close()
    except Exception as e:
        logger.error("aether_update error: %s", e)
        return [mcp_types.TextContent(type="text", text=f"Error updating aether: {e}")]


async def _handle_aether_curate(args: dict) -> list[mcp_types.TextContent]:
    """Curate .aether data into CONTEXT.md by spawning Ariadna."""
    project_root = args.get("project_root", "")
    if not project_root:
        return [mcp_types.TextContent(type="text", text="Error: 'project_root' is required for aether_curate.")]

    focus = args.get("focus", "recent")
    aether_dir = resolve_aether_dir(project_root)

    # Read current aether status for context
    try:
        db_path = resolve_aether_db(project_root)
        db = AetherDB(db_path=db_path)
        await db.connect()
        try:
            hot_state = await db.get_hot_state()
            recent_sessions = await db.get_recent_sessions(limit=5)

            cursor = await db._execute("SELECT * FROM decisions WHERE status = 'active' ORDER BY created_at DESC LIMIT 10")
            rows = await cursor.fetchall()
            decisions = [dict(row) for row in rows]

            cursor = await db._execute("SELECT * FROM issues WHERE status = 'open' ORDER BY created_at DESC")
            rows = await cursor.fetchall()
            open_issues = [dict(row) for row in rows]
        finally:
            await db.close()
    except Exception as e:
        logger.error("aether_curate error reading DB: %s", e)
        return [mcp_types.TextContent(type="text", text=f"Error reading aether.db: {e}")]

    # Build context summary for Ariadna
    context_parts = []
    if hot_state:
        context_parts.append(f"Project: {hot_state.get('project_name', 'Unknown')}")
        context_parts.append(f"Phase: {hot_state.get('current_phase', 'unknown')}")
        context_parts.append(f"Current Task: {hot_state.get('current_task', 'unknown')}")
        context_parts.append(f"Total Sessions: {hot_state.get('total_sessions', 0)}")
        if hot_state.get('blockers'):
            context_parts.append(f"Blockers: {hot_state['blockers']}")

    if recent_sessions:
        context_parts.append("\nRecent Sessions:")
        for s in recent_sessions:
            agent = s.get('agent', '?')
            status = s.get('status', '?')
            summary = (s.get('result_summary') or 'No summary')[:100]
            context_parts.append(f"  - {agent} ({status}): {summary}")

    if decisions:
        context_parts.append("\nActive Decisions:")
        for d in decisions:
            context_parts.append(f"  - {d.get('title', '?')}: {d.get('decision', '?')[:100]}")

    if open_issues:
        context_parts.append(f"\nOpen Issues: {len(open_issues)}")
        for i in open_issues[:5]:
            context_parts.append(f"  - #{i.get('id')}: {i.get('description', '?')[:80]}")

    context_summary = "\n".join(context_parts)

    # Spawn Ariadna to curate
    manager = _get_manager()

    # Read CONTEXT_SCHEMA if it exists for reference
    schema_path = aether_dir / "CONTEXT_SCHEMA.md"

    # Sessions count for footer
    sessions_count = hot_state.get('total_sessions', 0) if hot_state else 0

    prompt = (
        f"PROJECT_ROOT: {project_root}\n\n"
        f"You are curating the .aether project continuity data for this project.\n\n"
        f"Here is the current raw project state from aether.db:\n\n{context_summary}\n\n"
        f"TASK: Write a CONTEXT.md file at {aether_dir}/CONTEXT.md that synthesizes "
        f"this raw data into an actionable project brief for incoming sessions.\n\n"
        f"Focus: {focus}\n\n"
        f"STRICT FORMAT RULES:\n"
        f"1. MAX 1500 CHARACTERS. If your output exceeds 1500 chars, cut it down.\n"
        f"2. Exactly 5 sections: Title+Phase, Estado actual, Archivos recientes, "
        f"Decisiones activas, Proximo paso.\n"
        f"3. End with footer: — Curated: {datetime.now().strftime('%Y-%m-%d')} | "
        f"focus: {focus} | sessions: {sessions_count}\n"
        f"4. No tables, no JSON, no HTML. Plain markdown only.\n"
        f"5. No project root path. No Overview section.\n"
        f"6. Actionable, not historical. A cold Daimon needs to know what to DO.\n"
        f"7. Write in the project's working language (Spanish if project uses Spanish).\n\n"
        f"FORMAT:\n"
        f"# [Project Name] — Phase: [phase] | Task: [task]\n\n"
        f"## Estado actual\n"
        f"[2-4 sentences about current state]\n\n"
        f"## Archivos recientes\n"
        f"- `path/file.py` — one-line description\n\n"
        f"## Decisiones activas\n"
        f"- **[Title]**: one-line summary\n\n"
        f"## Proximo paso\n"
        f"1. [Most urgent]\n"
        f"2. [Second]\n\n"
        f"— Curated: YYYY-MM-DD | focus: {focus} | sessions: N\n\n"
        f"Write the file using write_file tool. Path: {aether_dir}/CONTEXT.md"
    )

    try:
        session_id = await manager.spawn_agent(agent_name="ariadna", project_root=project_root)
        await manager.send_message(session_id, prompt)
        # Close the session after curation
        try:
            await manager.close_session(session_id)
        except Exception:
            pass

        # Post-curate staleness sync removed: CONTEXT.md is now always injected
        # if it exists and has content, regardless of mtime vs updated_at.
        # Freshness is managed by aether_curate — Hermes decides when to re-curate.

        return [mcp_types.TextContent(
            type="text",
            text=f"Curated context written to {aether_dir}/CONTEXT.md",
        )]
    except Exception as e:
        logger.error("aether_curate spawn error: %s", e)
        return [mcp_types.TextContent(type="text", text=f"Error spawning Ariadna: {e}")]


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

async def main() -> None:
    """Start the Olympus v3 MCP server."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
        stream=sys.stderr,
    )

    logger.info("Starting Olympus v3 MCP server...")

    await init_server()

    async with stdio_server() as (read_stream, write_stream):
        logger.info("Olympus v3 MCP server running on stdio")
        await app.run(read_stream, write_stream, app.create_initialization_options())


if __name__ == "__main__":
    asyncio.run(main())
