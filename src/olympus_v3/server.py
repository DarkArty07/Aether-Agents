"""Olympus v3 MCP Server — ACP + Plugin hooks + SQLite.

Exposes 3 MCP tools to Hermes:
- talk_to: open, message, poll, close, cancel, delegate Daimon sessions
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
import os
import sys
import time
import uuid
from pathlib import Path
from typing import Any

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp import types as mcp_types

from .acp_manager import ACPManager
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
    session = await db.get_session(session_id)

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
                "cancel (force-terminate), delegate (auto-poll until done)."
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
                        "enum": ["open", "message", "poll", "close", "cancel", "delegate"],
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
                },
                "required": ["action"],
            },
        ),
        mcp_types.Tool(
            name="discover",
            description="List available Daimon agents and their capabilities.",
            inputSchema={"type": "object", "properties": {}, "required": []},
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
                return [mcp_types.TextContent(type="text", text=json.dumps(progress, indent=2))]

            # Check for timeout
            if elapsed >= timeout:
                progress["timed_out"] = True
                progress["elapsed_seconds"] = round(elapsed, 1)
                progress["poll_iterations"] = poll_iterations
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
                    return [mcp_types.TextContent(type="text", text=json.dumps(progress, indent=2))]
            else:
                stall_count = 0

            last_thoughts = current_thoughts
            last_messages = current_messages
            last_tool_calls = current_tool_calls

            # Safety limit
            if poll_iterations >= MAX_POLL_ITERATIONS:
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
