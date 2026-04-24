"""Olympus MCP Server — Aether Agents orchestrator.

Exposes two MCP tools:
- talk_to(agent, action, prompt, session_id, timeout) — communicate with Daimons
- discover() — list available agents and their capabilities

Runs as an MCP stdio server. Hermes (or any MCP-compatible agent) connects
via config.yaml and uses these tools to orchestrate the Aether ecosystem.

Architecture:
    Hermes (or any MCP client)
        → MCP stdio
            → Olympus Server (this file)
                → ACP (Agent Client Protocol)
                    → Daimons (hermes acp processes)
"""

from __future__ import annotations

import asyncio
import json
import logging
import sys
from pathlib import Path
from typing import Any

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp import types as mcp_types

from .acp_client import ACPManager
from .config import get_config, reset_config, OlympusConfig
from .discovery import discover_agents
from .registry import AgentStatus, OlympusRegistry, SessionStatus
from .workflows.runner import WorkflowRunner
import aiosqlite

from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver

# Configure logging to stderr (stdout is reserved for MCP protocol)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    stream=sys.stderr,
)
logger = logging.getLogger("olympus")

# Global state
registry = OlympusRegistry()
acp_manager: ACPManager | None = None

# Lazy-initialized AsyncSqliteSaver — created on first access so config is available
_workflow_checkpointer: AsyncSqliteSaver | None = None
_checkpointer_cm: Any = None  # keeps the async context manager alive


async def _get_workflow_checkpointer() -> AsyncSqliteSaver:
    """Return (and lazily create) a persistent AsyncSqliteSaver checkpointer.

    The SQLite database is stored at {AETHER_HOME}/.olympus_checkpoints.db
    so checkpoint data survives server restarts, enabling HITL workflow resumes.
    """
    global _workflow_checkpointer, _checkpointer_cm
    if _workflow_checkpointer is None:
        config = get_config()
        db_path = str(Path(config.aether_home) / ".olympus_checkpoints.db")
        logger.info(f"Creating persistent workflow checkpointer: {db_path}")
        _checkpointer_cm = AsyncSqliteSaver.from_conn_string(db_path)
        _workflow_checkpointer = await _checkpointer_cm.__aenter__()
    return _workflow_checkpointer


async def _shutdown_checkpointer():
    """Close the AsyncSqliteSaver connection on server shutdown."""
    global _workflow_checkpointer, _checkpointer_cm
    if _checkpointer_cm is not None:
        try:
            await _checkpointer_cm.__aexit__(None, None, None)
        except Exception as e:
            logger.warning(f"Error closing checkpointer: {e}")
        _workflow_checkpointer = None
        _checkpointer_cm = None


def create_server() -> Server:
    """Create and configure the Olympus MCP Server with tool handlers."""
    server = Server("olympus-mcp")

    @server.list_tools()
    async def list_tools(request: mcp_types.ListToolsRequest | None = None) -> list[mcp_types.Tool]:
        """Return the list of available tools."""
        return [
            mcp_types.Tool(
                name="talk_to",
                description=(
                    "Canal de comunicación con sub-agentes via Olympus MCP. "
                    "Flujo: discover → open → message → poll/wait → close. "
                    "Message es async por defecto — usa poll para consultar progreso o wait para bloquear."
                ),
                inputSchema={
                    "type": "object",
                    "properties": {
                        "agent": {
                            "type": "string",
                            "description": "Nombre del agente o '?' para discover",
                        },
                        "action": {
                            "type": "string",
                            "enum": ["discover", "open", "message", "poll", "wait", "cancel", "close"],
                            "description": (
                                "Acción a ejecutar. "
                                "discover: lista agentes. "
                                "open: crea sesión ACP. "
                                "message: envía prompt (async). "
                                "poll: consulta estado con progreso real. "
                                "wait: bloquea hasta respuesta. "
                                "cancel: aborta sesión. "
                                "close: cierra sesión."
                            ),
                        },
                        "prompt": {
                            "type": "string",
                            "description": "Mensaje. Solo con action=message",
                        },
                        "session_id": {
                            "type": "string",
                            "description": "ID de sesión (retornado por open). Requerido para poll, wait, cancel, close.",
                        },
                        "timeout": {
                            "type": "integer",
                            "description": "Timeout en segundos para wait. Default 120s, max 300s.",
                        },
                    },
                    "required": ["agent", "action"],
                },
            ),
            mcp_types.Tool(
                name="discover",
                description="Lista los agentes Daimon disponibles y sus capabilities.",
                inputSchema={
                    "type": "object",
                    "properties": {},
                },
            ),
            mcp_types.Tool(
                name="run_workflow",
                description=(
                    "Ejecuta un flujo de trabajo multi-agente predefinido con soporte HITL (Human-in-the-Loop).\n"
                    "Workflows disponibles: project-init, feature, bug-fix, security-review, research, refactor.\n\n"
                    "COMPORTAMIENTO SEGÚN RESULTADO:\n\n"
                    "1. Si status == 'interrupted': El workflow se pausó para que el usuario confirme.\n"
                    "   DEBES: Presentar la pregunta y contexto al usuario en formato conversacional y natural.\n"
                    "   Mostrar el contenido de interrupt[].context de forma legible (no como JSON crudo).\n"
                    "   Preguntar al usuario su decisión entre las opciones disponibles.\n"
                    "   Luego reanudar llamando run_workflow con el mismo workflow, thread_id, y resume=<decisión_del_usuario>.\n"
                    "   NO resumas sin confirmación explícita del usuario.\n\n"
                    "2. Si status == 'success': El workflow completó. Presentar el resultado final al usuario.\n\n"
                    "3. Si status == 'error': Hubo un error. Informar al usuario y sugerir siguiente paso.\n\n"
                    "HITL significa Human-in-the-Loop — el workflow NO continúa sin la decisión del usuario.\n"
                    "Los puntos de confirmación varían por workflow:\n"
                    "- feature: research_review, design_review, audit_review\n"
                    "- bug-fix: diagnosis_review\n"
                    "- security-review: findings_review\n"
                    "- refactor: scope_review\n"
                    "- project-init, research: sin HITL (corren directo)\n\n"
                    "Para reanudar un workflow interrumpido, proporciona thread_id y resume con la decisión del usuario."
                ),
                inputSchema={
                    "type": "object",
                    "properties": {
                        "workflow": {
                            "type": "string",
                            "enum": ["project-init", "feature", "bug-fix", "security-review", "research", "refactor"],
                            "description": "Nombre del workflow a ejecutar",
                        },
                        "prompt": {
                            "type": "string",
                            "description": "Descripción de la tarea a realizar (no requerido si se usa resume)",
                        },
                        "max_review_cycles": {
                            "type": "integer",
                            "description": "Máximo de ciclos de revisión Hefesto <-> Athena (default: 3)",
                        },
                        "params": {
                            "type": "object",
                            "description": "Parámetros específicos del workflow (needs_research, has_ui, workflow_type, etc.)",
                        },
                        "thread_id": {
                            "type": "string",
                            "description": "ID del hilo para reanudar un workflow interrumpido (requerido con resume)",
                        },
                        "resume": {
                            "type": "string",
                            "description": "Decisión del usuario para reanudar (approve, reject, confirm, modify, accept_risk)",
                        },
                    },
                    "required": ["workflow"],
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
        elif name == "run_workflow":
            return await _handle_run_workflow(arguments)
        else:
            return [mcp_types.TextContent(type="text", text=f"Unknown tool: {name}")]

    return server


async def _handle_discover() -> list[mcp_types.TextContent]:
    """Handle discover action — list all available Daimons."""
    agents = registry.list_agents()
    if not agents:
        # Discovery may not have been run yet
        config = get_config()
        profiles = discover_agents(config)
        registry.register_discovery(profiles)
        agents = registry.list_agents()

    result = {
        "agents": agents,
        "total": len(agents),
    }
    return [mcp_types.TextContent(type="text", text=json.dumps(result, indent=2))]


async def _handle_talk_to(args: dict[str, Any]) -> list[mcp_types.TextContent]:
    """Handle talk_to action — the main communication channel with Daimons."""
    global acp_manager

    agent_name = args.get("agent", "")
    action = args.get("action", "")
    prompt_text = args.get("prompt", "")
    session_id = args.get("session_id", "")
    timeout = args.get("timeout", 120)

    # discover action — shortcut
    if action == "discover" or agent_name == "?":
        return await _handle_discover()

    # Validate agent name
    if not agent_name or agent_name == "?":
        return await _handle_discover()

    # Self-talk prevention (D10)
    if agent_name == "hermes" or agent_name == "olympus":
        return [mcp_types.TextContent(
            type="text",
            text=json.dumps({"error": "Self-talk prevention: an agent cannot talk to itself or to Olympus."}),
        )]

    # Ensure ACP manager is initialized
    if acp_manager is None:
        acp_manager = ACPManager(registry)

    # Validate agent exists
    agent = registry.get_agent(agent_name)
    if agent is None:
        # Try discovery first
        config = get_config()
        profiles = discover_agents(config)
        registry.register_discovery(profiles)
        agent = registry.get_agent(agent_name)
        if agent is None:
            available = list(registry.agents.keys())
            return [mcp_types.TextContent(
                type="text",
                text=json.dumps({"error": f"Unknown agent: {agent_name}. Available: {available}"}),
            )]

    if action == "open":
        return await _action_open(agent_name)

    elif action == "message":
        if not prompt_text:
            return [mcp_types.TextContent(
                type="text",
                text=json.dumps({"error": "prompt is required for action=message"}),
            )]
        return await _action_message(session_id, prompt_text)

    elif action == "poll":
        return await _action_poll(session_id)

    elif action == "wait":
        clamp = min(max(timeout, 1), 300)
        return await _action_wait(session_id, clamp)

    elif action == "cancel":
        return await _action_cancel(session_id)

    elif action == "close":
        return await _action_close(session_id)

    else:
        return [mcp_types.TextContent(
            type="text",
            text=json.dumps({"error": f"Unknown action: {action}. Valid: discover, open, message, poll, wait, cancel, close"}),
        )]


async def _action_open(agent_name: str) -> list[mcp_types.TextContent]:
    """Open a new session on a Daimon."""
    try:
        session = await acp_manager.open_session(agent_name)
        return [mcp_types.TextContent(
            type="text",
            text=json.dumps({
                "status": "open",
                "session_id": session.session_id,
                "agent": agent_name,
            }),
        )]
    except Exception as e:
        logger.error(f"Error opening session with {agent_name}: {e}", exc_info=True)
        return [mcp_types.TextContent(
            type="text",
            text=json.dumps({"error": f"Failed to open session with {agent_name}: {str(e)}"}),
        )]


async def _action_message(session_id: str, prompt_text: str) -> list[mcp_types.TextContent]:
    """Send a prompt to a session (async — returns immediately)."""
    if not session_id:
        return [mcp_types.TextContent(
            type="text",
            text=json.dumps({"error": "session_id is required for action=message"}),
        )]

    try:
        result = await acp_manager.send_prompt(session_id, prompt_text)
        return [mcp_types.TextContent(
            type="text",
            text=json.dumps(result),
        )]
    except Exception as e:
        logger.error(f"Error sending prompt to session {session_id}: {e}", exc_info=True)
        return [mcp_types.TextContent(
            type="text",
            text=json.dumps({"error": f"Failed to send prompt: {str(e)}"}),
        )]


async def _action_poll(session_id: str) -> list[mcp_types.TextContent]:
    """Poll session state — return current thoughts, messages, tool calls."""
    session = registry.get_session(session_id)
    if session is None:
        return [mcp_types.TextContent(
            type="text",
            text=json.dumps({"error": f"Unknown session: {session_id}"}),
        )]

    result = {
        "session_id": session.session_id,
        "agent": session.agent_name,
        "status": session.status.value,
        "thoughts": session.thoughts[-5:],  # Last 5 thoughts
        "messages": session.messages[-3:],  # Last 3 messages
        "tool_calls": session.tool_calls[-5:],  # Last 5 tool calls
        "last_updated": session.last_updated,
    }

    if session.status in (SessionStatus.DONE, SessionStatus.ERROR, SessionStatus.CANCELLED):
        result["response"] = session.final_response
        result["stop_reason"] = session.stop_reason

    return [mcp_types.TextContent(type="text", text=json.dumps(result, indent=2))]


async def _action_wait(session_id: str, timeout: int) -> list[mcp_types.TextContent]:
    """Block until the session completes or timeout."""
    session = registry.get_session(session_id)
    if session is None:
        return [mcp_types.TextContent(
            type="text",
            text=json.dumps({"error": f"Unknown session: {session_id}"}),
        )]

    try:
        await asyncio.wait_for(session.completion_event.wait(), timeout=timeout)
    except asyncio.TimeoutError:
        return [mcp_types.TextContent(
            type="text",
            text=json.dumps({
                "session_id": session.session_id,
                "status": "timeout",
                "thoughts": session.thoughts[-5:],
                "messages": session.messages[-3:],
            }),
        )]

    return [mcp_types.TextContent(
        type="text",
        text=json.dumps({
            "session_id": session.session_id,
            "agent": session.agent_name,
            "status": session.status.value,
            "response": session.final_response,
            "stop_reason": session.stop_reason,
        }),
    )]


async def _action_cancel(session_id: str) -> list[mcp_types.TextContent]:
    """Cancel a running session."""
    try:
        result = await acp_manager.cancel_session(session_id)
        return [mcp_types.TextContent(type="text", text=json.dumps(result))]
    except Exception as e:
        return [mcp_types.TextContent(
            type="text",
            text=json.dumps({"error": f"Failed to cancel session: {str(e)}"}),
        )]


async def _action_close(session_id: str) -> list[mcp_types.TextContent]:
    """Close a session (agent stays alive for keep-alive)."""
    try:
        result = await acp_manager.close_session(session_id)
        return [mcp_types.TextContent(type="text", text=json.dumps(result))]
    except Exception as e:
        return [mcp_types.TextContent(
            type="text",
            text=json.dumps({"error": f"Failed to close session: {str(e)}"}),
        )]


async def _handle_run_workflow(args: dict[str, Any]) -> list[mcp_types.TextContent]:
    """Handle run_workflow action - execute a LangGraph predefined workflow."""
    global acp_manager
    if acp_manager is None:
        acp_manager = ACPManager(registry)
        
    workflow_name = args.get("workflow", "")
    prompt_text = args.get("prompt", "")
    max_review_cycles = args.get("max_review_cycles", 3)
    params = args.get("params", None)
    thread_id = args.get("thread_id", None)
    resume = args.get("resume", None)
    
    # For resume calls, prompt is not required — only thread_id and resume are needed
    if resume is None and (not workflow_name or not prompt_text):
        return [mcp_types.TextContent(
            type="text",
            text=json.dumps({"error": "workflow and prompt are required (or use thread_id + resume to resume)"}),
        )]
        
    config = get_config()
    checkpointer = await _get_workflow_checkpointer()
    runner = WorkflowRunner(registry, acp_manager, checkpointer=checkpointer)
    
    try:
        # Run workflow, passing the project root from configuration
        result = await runner.run(
            workflow_name=workflow_name,
            prompt=prompt_text,
            project_root=str(config.project_root),
            max_review_cycles=max_review_cycles,
            params=params,
            thread_id=thread_id,
            resume=resume,
        )
        
        # If workflow was interrupted, format a clear conversational response
        if result.get("status") == "interrupted":
            interrupts = result.get("interrupt", [])
            thread_id = result.get("thread_id", "")
            workflow_type = ""
            question = ""
            options = []
            context = ""
            
            if interrupts and isinstance(interrupts, list) and len(interrupts) > 0:
                first_interrupt = interrupts[0]
                if isinstance(first_interrupt, dict):
                    question = first_interrupt.get("question", "Se requiere tu confirmación")
                    options = first_interrupt.get("options", [])
                    workflow_type = first_interrupt.get("workflow_type", "")
                    context = first_interrupt.get("context", "")
            
            # Build a clear, conversational response for the calling agent
            hitl_msg = (
                f"🛑 WORKFLOW INTERRUPTADO — Se requiere tu decisión\n\n"
                f"**Workflow:** {workflow_type or workflow_name}\n"
                f"**Thread ID:** {thread_id}\n"
                f"**Punto de confirmación:** {question}\n"
                f"**Opciones disponibles:** {', '.join(options) if options else 'approve, reject'}\n\n"
            )
            if context:
                hitl_msg += f"**Contexto del agente:**\n{context}\n\n"
            hitl_msg += (
                f"**Para continuar:** Lama run_workflow con:\n"
                f"- workflow: \"{workflow_name}\"\n"
                f"- thread_id: \"{thread_id}\"\n"
                f"- resume: tu decisión (una de: {', '.join(options) if options else 'approve, reject'})\n\n"
                f"NO continúes sin confirmación explícita del usuario."
            )
            return [mcp_types.TextContent(type="text", text=hitl_msg)]
        
        # Format successful completion
        if result.get("status") == "success":
            final_response = result.get("result", "")
            return [mcp_types.TextContent(type="text", text=f"✅ Workflow completado exitosamente.\n\n{final_response}")]
        
        # Error or other status — return as-is
        return [mcp_types.TextContent(type="text", text=json.dumps(result, indent=2))]
    except Exception as e:
        logger.exception("Error during workflow execution")
        return [mcp_types.TextContent(
            type="text", 
            text=json.dumps({"error": f"Workflow exception: {str(e)}"})
        )]


async def _run_server() -> None:
    """Initialize and run the Olympus MCP Server."""
    global acp_manager

    config = get_config()
    logger.info(f"Olympus MCP Server starting — AETHER_HOME={config.aether_home}")
    logger.info(f"Profiles directory: {config.profiles_dir}")

    # Discover agents on startup
    profiles = discover_agents(config)
    registry.register_discovery(profiles)
    logger.info(f"Discovered {len(profiles)} Daimon(s): {list(profiles.keys())}")

    # Initialize ACP manager
    acp_manager = ACPManager(registry)

    # Create and run MCP server
    server = create_server()

    # Initialize options — explicitly disable prompts and resources
    # so clients don't try to call list_prompts/list_resources (not implemented)
    init_options = server.create_initialization_options()
    # Override capabilities to only expose tools
    if hasattr(init_options, 'capabilities'):
        init_options.capabilities.prompts = None
        init_options.capabilities.resources = None

    async with stdio_server() as (read_stream, write_stream):
        logger.info("Olympus MCP Server running on stdio")
        try:
            await server.run(
                read_stream,
                write_stream,
                init_options,
            )
        finally:
            # Cleanup: close the AsyncSqliteSaver connection
            await _shutdown_checkpointer()


def main() -> None:
    """Entry point for the Olympus MCP Server."""
    asyncio.run(_run_server())


if __name__ == "__main__":
    main()