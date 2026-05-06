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

import time as _time

def _build_progress(buffer: SessionBuffer) -> dict:
    """Build progress metadata matching V1 format for stall detection."""
    return {
        "total_thoughts": buffer.thoughts_count,
        "substantive_thoughts": buffer.thoughts_count,  # In V2 all thoughts are substantive (no spinners in RPC)
        "total_messages": 1 if buffer.accumulated_text else 0,
        "total_tool_calls": buffer.tool_calls_count,
        "elapsed_seconds": round(_time.time() - buffer.started_at, 1),
    }

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
                            "enum": ["open", "message", "poll", "cancel", "close", "delegate"],
                            "description": (
                                "Action to execute. "
                                "open: spawn Pi process, create session. "
                                "message: send prompt (async). "
                                "poll: read events, check status. "
                                "cancel: abort session. "
                                "close: terminate process, cleanup. "
                                "delegate: open + message + auto-poll until done or timeout."
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
                        "poll_interval": {
                            "type": "integer",
                            "description": "Seconds between polls. Only with action=delegate",
                            "default": 15,
                        },
                        "timeout": {
                            "type": "integer",
                            "description": "Max seconds to wait for completion. Only with action=delegate",
                            "default": 300,
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
            mcp_types.Tool(
                name="consult",
                description=(
                    "Consulting workflow with Pi Agent Daimons.\n"
                    "Actions:\n"
                    "- start: Create a new consulting session with selected agents\n"
                    "- run: Consult a specific agent for enrichments + contract\n"
                    "- sign: Get an agent to sign a final contract\n"
                    "- add_agent: Add an agent to an ongoing session\n"
                    "- status: Get current session status\n"
                    "- complete: Close a consulting session"
                ),
                inputSchema={
                    "type": "object",
                    "properties": {
                        "action": {
                            "type": "string",
                            "enum": ["start", "run", "sign", "add_agent", "status", "complete"],
                            "description": (
                                "Action to execute. "
                                "start: create session. "
                                "run: consult agent. "
                                "sign: agent signs contract. "
                                "add_agent: add agent to session. "
                                "status: get session status. "
                                "complete: close session."
                            ),
                        },
                        "session_id": {
                            "type": "string",
                            "description": "Session ID (required for run, sign, status, complete, add_agent)",
                        },
                        "plan": {
                            "type": "string",
                            "description": "Plan text (required for start)",
                        },
                        "agents": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "List of agent names for start (e.g. [\"daedalus\", \"athena\"])",
                        },
                        "context": {
                            "type": "string",
                            "description": "Additional context for the plan (optional, for start)",
                        },
                        "project_root": {
                            "type": "string",
                            "description": "Project root path (optional)",
                        },
                        "agent": {
                            "type": "string",
                            "description": "Agent name for run/sign (e.g. \"daedalus\" or \"athena\")",
                        },
                        "tasks": {
                            "type": "array",
                            "description": "List of task dicts for sign action",
                        },
                        "new_agent": {
                            "type": "string",
                            "description": "Agent name to add (for add_agent action)",
                        },
                        "role": {
                            "type": "string",
                            "description": "Role for the new agent (for add_agent action)",
                        },
                        "reason": {
                            "type": "string",
                            "description": "Reason for adding the agent (for add_agent action)",
                        },
                    },
                    "required": ["action"],
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
        elif name == "consult":
            return await _handle_consult(arguments)
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

    elif action == "delegate":
        return await _action_delegate(args)

    else:
        return [mcp_types.TextContent(
            type="text",
            text=json.dumps({"error": f"Unknown action: {action}. Valid: open, message, poll, cancel, close"}),
        )]


async def _action_delegate(arguments: dict) -> list[mcp_types.TextContent]:
    """Delegate: open, message, and auto-poll until done or timeout.

    One-shot action that spawns a session, sends a prompt, and polls
    automatically until the session completes or the timeout is reached.
    """
    agent_name = arguments.get("agent", "")
    prompt_text = arguments.get("prompt", "")
    poll_interval = max(1, arguments.get("poll_interval", 15))
    timeout = min(1200, max(1, arguments.get("timeout", 1200)))

    logger.info(
        f"[olympus_v2] delegate start: agent={agent_name}, "
        f"timeout={timeout}s, poll_interval={poll_interval}s"
    )

    # Open session
    open_result = await _action_open(agent_name, "")
    open_data = json.loads(open_result[0].text)
    if "error" in open_data:
        logger.error(f"[olympus_v2] delegate open failed: {open_data['error']}")
        return open_result

    session_id = open_data.get("session_id")
    if not session_id:
        return [mcp_types.TextContent(
            type="text",
            text=json.dumps({"error": "delegate failed: open did not return session_id"}),
        )]

    # Send message
    message_result = await _action_message(session_id, prompt_text)
    message_data = json.loads(message_result[0].text)
    if "error" in message_data:
        logger.error(f"[olympus_v2] delegate message failed: {message_data['error']}")
        return message_result

    # Poll loop
    start_time = _time.time()
    last_result_data: dict = {}
    iteration = 0

    while True:
        await asyncio.sleep(poll_interval)
        iteration += 1
        elapsed = _time.time() - start_time
        logger.info(
            f"[olympus_v2] delegate poll iteration={iteration}, "
            f"elapsed={elapsed:.1f}s, session_id={session_id}"
        )

        poll_result = await _action_poll(session_id)
        poll_data = json.loads(poll_result[0].text)
        last_result_data = poll_data

        # Detailed diagnostic log for delegate poll iteration
        _buf = buffers.get(session_id)
        if _buf:
            logger.info(
                f"[olympus_v2] delegate {agent_name} poll iter={iteration} "
                f"elapsed={elapsed:.1f}s events=poll "
                f"text={len(_buf.accumulated_text)}c reasoning={len(_buf.accumulated_reasoning)}c "
                f"thoughts={_buf.thoughts_count} tool_calls={_buf.tool_calls_count} "
                f"done={_buf.is_done} stop={_buf.stop_reason or '-'}"
            )
        else:
            # Buffer cleaned up (process died / session closed)
            logger.info(
                f"[olympus_v2] delegate {agent_name} poll iter={iteration} "
                f"elapsed={elapsed:.1f}s events=poll "
                f"text={len(poll_data.get('response', ''))}c reasoning=0c "
                f"thoughts={poll_data.get('thoughts', 0)} tool_calls={poll_data.get('tool_calls', 0)} "
                f"done=True stop={poll_data.get('stop_reason', '-')}"
            )

        if poll_data.get("status") == "done":
            logger.info(
                f"[olympus_v2] delegate complete: session_id={session_id}, "
                f"elapsed={elapsed:.1f}s"
            )
            await _action_close(session_id)
            poll_data["delegate"] = {
                "timed_out": False,
                "elapsed_seconds": round(elapsed, 1),
                "poll_iterations": iteration,
            }
            return [mcp_types.TextContent(type="text", text=json.dumps(poll_data))]

        if elapsed >= timeout:
            logger.info(
                f"[olympus_v2] delegate timeout reached: session_id={session_id}, "
                f"elapsed={elapsed:.1f}s"
            )
            last_result_data["delegate"] = {
                "timed_out": True,
                "elapsed_seconds": round(elapsed, 1),
                "poll_iterations": iteration,
            }
            return [mcp_types.TextContent(type="text", text=json.dumps(last_result_data))]


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
        # Distinguish between expired and never-existed sessions
        session_exists = session_id in adapter.sessions
        if session_exists:
            return [mcp_types.TextContent(
                type="text",
                text=json.dumps({
                    "error": f"Session expired or process terminated: {session_id}",
                    "status": "expired",
                }),
            )]
        else:
            return [mcp_types.TextContent(
                type="text",
                text=json.dumps({
                    "error": f"Unknown session: {session_id}. Never opened or already closed.",
                    "status": "unknown",
                }),
            )]

    # For multi-turn: check Pi state before sending
    # If the previous turn ended (buffer was reset), verify Pi is ready
    if buffer.thoughts_count == 0 and buffer.tool_calls_count == 0 and not buffer.accumulated_text:
        # This might be a new turn in an existing session — check Pi state
        try:
            state = adapter.send_get_state(session_id)
            if state is not None:
                is_streaming = state.get("isStreaming", False)
                logger.info(
                    f"[olympus_v2] Pi state before multi-turn prompt: "
                    f"streaming={is_streaming}, "
                    f"messages={state.get('messageCount', '?')}"
                )
                # If Pi is still streaming, use follow_up semantics
                # (we still send prompt, but Pi will queue it)
                if is_streaming:
                    logger.warning(
                        f"[olympus_v2] Pi is still streaming for session {session_id}, "
                        f"sending prompt anyway"
                    )
        except Exception as e:
            logger.debug(f"[olympus_v2] get_state failed (may be first turn): {e}")

    # Reset buffer for new turn (multi-turn support)
    buffer.is_done = False
    buffer.accumulated_text = ""
    buffer.accumulated_reasoning = ""
    buffer.thoughts_count = 0
    buffer.tool_calls_count = 0
    buffer.final_response = ""
    buffer.last_turn_response = ""
    buffer.turn_count = 0
    buffer.stop_reason = ""
    buffer.tool_calls_detail = []

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

    # Give Pi a moment to start processing the prompt and drain any
    # stale events left over from a previous turn.  Without this, the
    # next poll can pick up leftover events that contaminate the new
    # turn's response (causing 0 thoughts / 0 tool_calls echo).
    await asyncio.sleep(0.5)
    stale_events = adapter.read_events(session_id)
    if stale_events:
        logger.info(
            f"[olympus_v2] Drained {len(stale_events)} stale events "
            f"before new turn for session {session_id}"
        )

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
        # Distinguish between expired and never-existed sessions
        session_exists = session_id in adapter.sessions
        if session_exists:
            return [mcp_types.TextContent(
                type="text",
                text=json.dumps({
                    "error": f"Session expired or process terminated: {session_id}",
                    "status": "expired",
                }),
            )]
        else:
            return [mcp_types.TextContent(
                type="text",
                text=json.dumps({
                    "error": f"Unknown session: {session_id}. Never opened or already closed.",
                    "status": "unknown",
                }),
            )]

    # Check if the process is still alive
    # With --session-dir, Pi stays alive between prompts. Process death is unexpected.
    if not adapter.is_process_alive(session_id):
        # Process died unexpectedly — drain remaining events and mark done
        events = adapter.read_events(session_id)
        if events:
            translate_events_batch(events, buffer)

        buffer.is_done = True
        # Final response priority: last_turn_response (clean, from Pi Agent structured event)
        # > accumulated_text (may contain tool output from current turn, useful as fallback)
        # > accumulated_reasoning (available for debugging only, never used as response)
        if not buffer.final_response:
            if buffer.last_turn_response:
                buffer.final_response = buffer.last_turn_response
            elif buffer.accumulated_text:
                buffer.final_response = buffer.accumulated_text

        # Clean up session (terminate + remove session dir)
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
                "stop_reason": buffer.stop_reason or "process_terminated",
                "progress": _build_progress(buffer),
            }),
        )]

    # Read new events from the adapter
    events = adapter.read_events(session_id) if session_id in adapter.sessions else []

    if events:
        event_types = {}
        for ev in events:
            ev_type = ev.get("type", "unknown")
            event_types[ev_type] = event_types.get(ev_type, 0) + 1
        logger.info(
            f"[olympus_v2] poll {session_id} events breakdown: {event_types}"
        )

    if not events and not buffer.is_done:
        # No new events — return current state
        response_text = buffer.accumulated_text
        truncated_response = response_text
        truncated = False
        total_len = 0
        if response_text and len(response_text) > 4000:
            truncated_response = response_text[:4000] + f"\n... [TRUNCATED: {len(response_text)} total chars]"
            truncated = True
            total_len = len(response_text)

        result_data = {
            "status": "active",
            "session_id": session_id,
            "thoughts": buffer.thoughts_count,
            "tool_calls": buffer.tool_calls_count,
            "response": truncated_response,
            "poll_interval": _get_config().poll_interval,
            "progress": _build_progress(buffer),
        }
        if truncated:
            result_data["response_truncated"] = True
            result_data["response_total_length"] = total_len
        return [mcp_types.TextContent(type="text", text=json.dumps(result_data))]

    # Translate all new events
    result = translate_events_batch(events, buffer)

    # Truncate response to avoid sending 20KB+ payloads
    MAX_RESPONSE_LEN = 4000
    response_text = result.get("response", "")
    if response_text and len(response_text) > MAX_RESPONSE_LEN:
        result["response"] = response_text[:MAX_RESPONSE_LEN] + f"\n... [TRUNCATED: {len(response_text)} total chars]"
        result["response_truncated"] = True
        result["response_total_length"] = len(response_text)

    # Add session_id to result
    result["session_id"] = session_id
    result["poll_interval"] = _get_config().poll_interval
    result["progress"] = _build_progress(buffer)

    return [mcp_types.TextContent(
        type="text",
        text=json.dumps(result),
    )]


async def _action_cancel(session_id: str) -> list[mcp_types.TextContent]:
    """Cancel (abort) an active Pi Agent session."""
    buffer = buffers.get(session_id)
    if buffer is None:
        # Distinguish between expired and never-existed sessions
        session_exists = session_id in adapter.sessions
        if session_exists:
            return [mcp_types.TextContent(
                type="text",
                text=json.dumps({
                    "error": f"Session expired or process terminated: {session_id}",
                    "status": "expired",
                }),
            )]
        else:
            return [mcp_types.TextContent(
                type="text",
                text=json.dumps({
                    "error": f"Unknown session: {session_id}. Never opened or already closed.",
                    "status": "unknown",
                }),
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
        # Distinguish between expired and never-existed sessions
        session_exists = session_id in adapter.sessions
        if session_exists:
            return [mcp_types.TextContent(
                type="text",
                text=json.dumps({
                    "error": f"Session expired or process terminated: {session_id}",
                    "status": "expired",
                }),
            )]
        else:
            return [mcp_types.TextContent(
                type="text",
                text=json.dumps({
                    "error": f"Unknown session: {session_id}. Never opened or already closed.",
                    "status": "unknown",
                }),
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


async def _handle_consult(arguments: dict[str, Any]) -> list[mcp_types.TextContent]:
    """Handle consult action — consulting workflow with Pi-backed Daimons."""
    from .consult_action import handle_consult_action

    result = await handle_consult_action(
        action=arguments.get("action", ""),
        adapter=adapter,
        buffers=buffers,
        session_id=arguments.get("session_id"),
        plan=arguments.get("plan"),
        agents=arguments.get("agents"),
        context=arguments.get("context"),
        project_root=arguments.get("project_root"),
        agent=arguments.get("agent"),
        tasks=arguments.get("tasks"),
        new_agent=arguments.get("new_agent"),
        role=arguments.get("role"),
        reason=arguments.get("reason"),
    )
    return [mcp_types.TextContent(type="text", text=json.dumps(result, indent=2))]


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