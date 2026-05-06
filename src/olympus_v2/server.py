"""Olympus v2 MCP Server — Pi Agent RPC-based Daimon orchestration.

This is the main entry point for the Olympus v2 MCP server. It exposes the
same talk_to tool interface as Olympus v1, but uses Pi Agent's JSONL RPC
protocol instead of ACP for subprocess communication.

Exposes 5 tool handlers:
- talk_to_open(agent, prompt) → spawn Pi process, return session_id
- talk_to_message(session_id, prompt) → send prompt command to stdin
- talk_to_poll(session_id) → read events, translate, return status
- talk_to_cancel(session_id) → send abort command
- talk_to_close(session_id) → terminate process, cleanup

Architecture:
    Hermes (MCP client)
        → MCP stdio
            → Olympus v2 Server (this file)
                → Pi Adapter (subprocess management)
                    → Pi Agent (--mode rpc)
                        → LLM (via provider/model from config)
"""

from __future__ import annotations

import asyncio
import json
import logging
import sys
import uuid
from pathlib import Path
from typing import Any

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp import types as mcp_types

from .config_loader import OlympusV2Config, get_config, reset_config, PiDaimonConfig, BACKEND_PI_RPC
from .event_translator import SessionBuffer, translate_events_batch
from .pi_adapter import PiAdapter, PiSession
from .soul_to_system import find_system_prompt

# Configure logging to stderr (stdout is reserved for MCP protocol)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    stream=sys.stderr,
)
logger = logging.getLogger("olympus_v2")

# Global state
adapter = PiAdapter()
buffers: dict[str, SessionBuffer] = {}
config: OlympusV2Config | None = None


def _get_config() -> OlympusV2Config:
    """Get or load the global configuration."""
    global config
    if config is None:
        config = get_config()
    return config


def _resolve_agent(agent_name: str) -> PiDaimonConfig | None:
    """Look up a Daimon by name in the configuration.

    Returns the PiDaimonConfig if found, None otherwise.
    """
    cfg = _get_config()
    return cfg.daimons.get(agent_name)


def create_server() -> Server:
    """Create and configure the Olympus v2 MCP Server with tool handlers."""
    server = Server("olympus-v2-mcp")

    @server.list_tools()
    async def list_tools(request: mcp_types.ListToolsRequest | None = None) -> list[mcp_types.Tool]:
        """Return the list of available tools."""
        return [
            mcp_types.Tool(
                name="talk_to",
                description=(
                    "Communication channel with Pi-backed Daimons via Olympus v2 MCP. "
                    "Flow: discover → open → message → poll → close. "
                    "Message is async by default — use poll to check progress. "
                    "Poll interval: wait at least poll_interval seconds between poll calls. "
                    "The open and poll responses include the recommended poll_interval value."
                ),
                inputSchema={
                    "type": "object",
                    "properties": {
                        "agent": {
                            "type": "string",
                            "description": "Agent name or '?' to discover available agents",
                        },
                        "action": {
                            "type": "string",
                            "enum": ["open", "message", "poll", "cancel", "close"],
                            "description": (
                                "Action to execute. "
                                "open: spawn Pi process, create session. "
                                "message: send prompt (async). "
                                "poll: read events, check status. "
                                "cancel: abort session. "
                                "close: terminate process, cleanup."
                            ),
                        },
                        "prompt": {
                            "type": "string",
                            "description": "Message text. Only with action=message",
                        },
                        "session_id": {
                            "type": "string",
                            "description": "Session ID (returned by action=open)",
                        },
                    },
                    "required": ["agent", "action"],
                },
            ),
            mcp_types.Tool(
                name="discover",
                description="List available Pi-backed Daimon agents and their capabilities.",
                inputSchema={
                    "type": "object",
                    "properties": {},
                },
            ),
        ]

    @server.call_tool()
    async def call_tool(name: str, arguments: dict[str, Any]) -> list[mcp_types.TextContent]:
        """Handle tool calls from MCP clients."""
        if name == "discover":
            return await _handle_discover()
        elif name == "talk_to":
            return await _handle_talk_to(arguments)
        else:
            return [mcp_types.TextContent(type="text", text=f"Unknown tool: {name}")]

    return server


async def _handle_discover() -> list[mcp_types.TextContent]:
    """Handle discover action — list all configured Pi-backed Daimons."""
    cfg = _get_config()
    agents = []
    for name, daimon_cfg in cfg.daimons.items():
        agents.append({
            "name": name,
            "role": daimon_cfg.role,
            "description": daimon_cfg.description,
            "backend": daimon_cfg.backend,
            "provider": daimon_cfg.provider,
            "model": daimon_cfg.model,
        })

    result = {
        "agents": agents,
        "total": len(agents),
    }
    return [mcp_types.TextContent(type="text", text=json.dumps(result, indent=2))]


async def _handle_talk_to(args: dict[str, Any]) -> list[mcp_types.TextContent]:
    """Handle talk_to action — the main communication channel with Pi-backed Daimons."""
    agent_name = args.get("agent", "")
    action = args.get("action", "")
    prompt_text = args.get("prompt", "")
    session_id = args.get("session_id", "")

    # Discover shortcut
    if agent_name == "?" or not agent_name:
        return await _handle_discover()

    # Self-talk prevention
    if agent_name in ("hermes", "olympus", "olympus_v2"):
        return [mcp_types.TextContent(
            type="text",
            text=json.dumps({"error": "Self-talk prevention: an agent cannot talk to itself or to Olympus."}),
        )]

    # Route to action handlers
    if action == "open":
        return await _action_open(agent_name, prompt_text)

    elif action == "message":
        if not prompt_text:
            return [mcp_types.TextContent(
                type="text",
                text=json.dumps({"error": "prompt is required for action=message"}),
            )]
        return await _action_message(session_id, prompt_text)

    elif action == "poll":
        return await _action_poll(session_id)

    elif action == "cancel":
        return await _action_cancel(session_id)

    elif action == "close":
        return await _action_close(session_id)

    else:
        return [mcp_types.TextContent(
            type="text",
            text=json.dumps({"error": f"Unknown action: {action}. Valid: open, message, poll, cancel, close"}),
        )]


async def _action_open(agent_name: str, initial_prompt: str = "") -> list[mcp_types.TextContent]:
    """Open a new session with a Pi-backed Daimon.

    Spawns a Pi Agent process in RPC mode and optionally sends an initial prompt.
    """
    cfg = _get_config()

    # Resolve agent config
    daimon_cfg = _resolve_agent(agent_name)
    if daimon_cfg is None:
        available = list(cfg.daimons.keys())
        return [mcp_types.TextContent(
            type="text",
            text=json.dumps({
                "error": f"Unknown Pi-backed agent: {agent_name}. "
                          f"Available Pi agents: {available}",
            }),
        )]

    # Spawn the Pi Agent process
    try:
        session = adapter.spawn_agent(daimon_cfg)
    except RuntimeError as e:
        return [mcp_types.TextContent(
            type="text",
            text=json.dumps({"error": str(e)}),
        )]

    # Create event buffer for this session
    buffer = SessionBuffer(session_id=session.session_id)
    buffers[session.session_id] = buffer

    # Wait briefly for the process to initialize and send agent_start
    await asyncio.sleep(0.5)

    # Read any initial events (agent_start, etc.)
    events = adapter.read_events(session.session_id)
    if events:
        translate_events_batch(events, buffer)

    # Send initial prompt if provided
    if initial_prompt:
        try:
            adapter.send_command(session.session_id, {
                "type": "prompt",
                "message": initial_prompt,
                "id": str(uuid.uuid4()),
            })
        except RuntimeError as e:
            # Clean up on send failure
            adapter.terminate(session.session_id)
            buffers.pop(session.session_id, None)
            return [mcp_types.TextContent(
                type="text",
                text=json.dumps({"error": f"Failed to send initial prompt: {e}"}),
            )]

    return [mcp_types.TextContent(
        type="text",
        text=json.dumps({
            "status": "open",
            "session_id": session.session_id,
            "agent": agent_name,
            "backend": "pi_rpc",
            "poll_interval": cfg.poll_interval,
        }),
    )]


async def _action_message(session_id: str, prompt_text: str) -> list[mcp_types.TextContent]:
    """Send a prompt to an active Pi Agent session."""
    buffer = buffers.get(session_id)
    if buffer is None:
        return [mcp_types.TextContent(
            type="text",
            text=json.dumps({"error": f"Unknown session: {session_id}"}),
        )]

    try:
        adapter.send_command(session_id, {
            "type": "prompt",
            "message": prompt_text,
            "id": str(uuid.uuid4()),
        })
    except (KeyError, RuntimeError) as e:
        return [mcp_types.TextContent(
            type="text",
            text=json.dumps({"error": f"Failed to send prompt: {e}"}),
        )]

    return [mcp_types.TextContent(
        type="text",
        text=json.dumps({
            "status": "active",
            "session_id": session_id,
            "message": "Prompt sent",
        }),
    )]


async def _action_poll(session_id: str) -> list[mcp_types.TextContent]:
    """Poll for new events from a Pi Agent session."""
    buffer = buffers.get(session_id)
    if buffer is None:
        return [mcp_types.TextContent(
            type="text",
            text=json.dumps({"error": f"Unknown session: {session_id}"}),
        )]

    # Check if the process is still alive
    if not adapter.is_process_alive(session_id):
        # Process has exited — drain remaining events and mark done
        events = adapter.read_events(session_id)
        if events:
            translate_events_batch(events, buffer)

        buffer.is_done = True
        if not buffer.final_response:
            buffer.final_response = buffer.accumulated_text

        adapter.terminate(session_id)
        buffers.pop(session_id, None)

        return [mcp_types.TextContent(
            type="text",
            text=json.dumps({
                "status": "done",
                "session_id": session_id,
                "thoughts": buffer.thoughts_count,
                "tool_calls": buffer.tool_calls_count,
                "response": buffer.final_response or "",
            }),
        )]

    # Read new events from the adapter
    events = adapter.read_events(session_id) if session_id in adapter.sessions else []

    if not events and not buffer.is_done:
        # No new events — return current state
        return [mcp_types.TextContent(
            type="text",
            text=json.dumps({
                "status": "active",
                "session_id": session_id,
                "thoughts": buffer.thoughts_count,
                "tool_calls": buffer.tool_calls_count,
                "response": buffer.accumulated_text,
                "poll_interval": _get_config().poll_interval,
            }),
        )]

    # Translate all new events
    result = translate_events_batch(events, buffer)

    # Add session_id to result
    result["session_id"] = session_id
    result["poll_interval"] = _get_config().poll_interval

    # If done, clean up the session
    if buffer.is_done:
        adapter.terminate(session_id)
        buffers.pop(session_id, None)

    return [mcp_types.TextContent(
        type="text",
        text=json.dumps(result),
    )]


async def _action_cancel(session_id: str) -> list[mcp_types.TextContent]:
    """Cancel (abort) an active Pi Agent session."""
    buffer = buffers.get(session_id)
    if buffer is None:
        return [mcp_types.TextContent(
            type="text",
            text=json.dumps({"error": f"Unknown session: {session_id}"}),
        )]

    # Send abort command
    adapter.abort(session_id)

    # Mark as cancelled
    buffer.is_done = True
    buffer.stop_reason = "cancelled"

    # Give the process a moment to shut down, then terminate
    await asyncio.sleep(0.5)
    adapter.terminate(session_id)
    buffers.pop(session_id, None)

    return [mcp_types.TextContent(
        type="text",
        text=json.dumps({
            "status": "cancelled",
            "session_id": session_id,
            "response": buffer.accumulated_text or "",
        }),
    )]


async def _action_close(session_id: str) -> list[mcp_types.TextContent]:
    """Close a Pi Agent session and clean up."""
    buffer = buffers.get(session_id)
    if buffer is None:
        return [mcp_types.TextContent(
            type="text",
            text=json.dumps({"error": f"Unknown session: {session_id}"}),
        )]

    # Terminate the process
    adapter.terminate(session_id)
    buffers.pop(session_id, None)

    return [mcp_types.TextContent(
        type="text",
        text=json.dumps({
            "status": "closed",
            "session_id": session_id,
            "response": buffer.accumulated_text or "",
        }),
    )]


async def main() -> None:
    """Main entry point — run the Olympus v2 MCP server via stdio."""
    global config
    config = get_config()

    logger.info(
        f"[olympus_v2] Starting server "
        f"(daimons: {list(config.daimons.keys())}, "
        f"poll_interval: {config.poll_interval}s)"
    )

    server = create_server()

    try:
        async with stdio_server() as (read_stream, write_stream):
            await server.run(read_stream, write_stream, server.create_initialization_options())
    except Exception as e:
        logger.error(f"[olympus_v2] Server error: {e}")
        raise
    finally:
        # Clean up all Pi processes on shutdown
        adapter.terminate_all()
        logger.info("[olympus_v2] Server shut down")


def run_server() -> None:
    """Synchronous entry point for the MCP server."""
    asyncio.run(main())


if __name__ == "__main__":
    run_server()