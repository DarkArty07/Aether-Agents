"""Olympus ACP client — manages Daimon processes via Agent Client Protocol.

This module wraps the ACP SDK to:
- Spawn Daimon processes (hermes acp with HERMES_HOME pointing to each profile)
- Initialize connections and create sessions
- Send prompts and collect session_updates (thoughts, messages, tool calls)
- Poll session state from the in-memory registry
- Wait for completion with timeout
- Cancel or close sessions gracefully

Designed for keep-alive: agents stay running between sessions. Only the first
talk_to(action="open") spawns a new process. Subsequent opens create new sessions
on the existing process.
"""

from __future__ import annotations

import asyncio
import logging
import os
import shutil
from typing import Any

from acp import (
    PROTOCOL_VERSION,
    InitializeResponse,
    NewSessionResponse,
    PromptResponse,
    spawn_agent_process,
    text_block,
    update_agent_message,
    update_agent_thought,
    update_plan,
)
from acp.interfaces import Client
from acp.schema import (
    AgentCapabilities,
    AgentMessageChunk,
    AgentPlanUpdate,
    AgentThoughtChunk,
    ClientCapabilities,
    Implementation,
    PermissionOption,
    RequestPermissionResponse,
    TextContentBlock,
    ToolCall,
)

from .config import DaimonProfile, get_config
from .registry import AgentState, AgentStatus, OlympusRegistry, SessionState, SessionStatus

logger = logging.getLogger("olympus.acp")


class OlympusACPClient(Client):
    """ACP Client that captures session_updates and sends them to the registry.

    This class implements the Client interface required by ACP. When a Daimon
    sends session_updates (thoughts, messages, plans), this client receives them
    and routes them to the corresponding SessionState in the registry.
    """

    def __init__(self, registry: OlympusRegistry, agent_name: str) -> None:
        self.registry = registry
        self.agent_name = agent_name

    async def request_permission(
        self,
        options: list[PermissionOption],
        session_id: str,
        tool_call: ToolCall,
        **kwargs: Any,
    ) -> RequestPermissionResponse:
        """Handle permission requests from Daimons — auto-approve for MVP."""
        logger.info(f"[OlympusClient] Permission request from {self.agent_name} (session={session_id}): {tool_call.name}")
        # Auto-approve for MVP — in production this could ask Hermes
        return RequestPermissionResponse(outcome={"outcome": "approved"})

    async def session_update(self, session_id: str, update: Any, **kwargs: Any) -> None:
        """Route ACP session_updates to the registry.

        This is the key bridge: ACP sends streaming updates (thoughts, messages,
        plans, tool calls) and we capture them in the SessionState for poll().
        """
        # Find the session in the registry
        # ACP session_ids may differ from Olympus session_ids, so we match
        # by looking up the session in the agent's active sessions
        agent = self.registry.get_agent(self.agent_name)
        if not agent:
            logger.warning(f"Session update for unknown agent: {self.agent_name}")
            return

        # Find the session that matches this ACP session_id
        session = None
        for s in agent.sessions.values():
            if s.session_id == session_id or session_id in s.session_id:
                session = s
                break

        if not session:
            # Create a mapping entry if needed — this handles the case where
            # ACP assigns its own session_id that differs from ours
            logger.debug(f"Session update for unknown session: {session_id}, searching by agent")
            # Try to find by the fact that there should be exactly one active session
            for s in agent.sessions.values():
                if s.status == SessionStatus.ACTIVE:
                    session = s
                    break

        if isinstance(update, AgentThoughtChunk):
            content = update.content
            text = content.text if isinstance(content, TextContentBlock) else str(content)
            if session:
                session.update_from_thought(text)
            logger.debug(f"[OlympusClient] THOUGHT from {self.agent_name}: {text[:100]}")

        elif isinstance(update, AgentMessageChunk):
            content = update.content
            text = content.text if isinstance(content, TextContentBlock) else str(content)
            if session:
                session.update_from_message(text)
            logger.debug(f"[OlympusClient] MESSAGE from {self.agent_name}: {text[:100]}")

        elif isinstance(update, AgentPlanUpdate):
            entries = [f"  {e.content} [{e.status}]" for e in update.entries]
            logger.debug(f"[OlympusClient] PLAN from {self.agent_name}: {entries}")

        else:
            logger.debug(f"[OlympusClient] UPDATE from {self.agent_name}: {type(update).__name__}")


class ACPManager:
    """Manages the lifecycle of Daimon processes via ACP.

    Responsible for:
    - Spawning Daimon processes when they haven't been started yet (lazy spawn)
    - Initializing ACP connections and creating sessions
    - Sending prompts and collecting responses
    - Keeping track of which agents are alive and their sessions
    """

    def __init__(self, registry: OlympusRegistry) -> None:
        self.registry = registry
        self._config = get_config()

    async def ensure_agent(self, name: str) -> AgentState:
        """Ensure a Daimon process is alive. Spawn if dead, return if alive.

        This implements lazy universal startup (D16): no agents run at start.
        First talk_to(action="open") spawns the agent. Keep_alive keeps it running
        between sessions.
        """
        agent = self.registry.get_agent(name)
        if agent is None:
            raise ValueError(f"Unknown agent: {name}. Run discovery first.")

        if agent.status in (AgentStatus.IDLE, AgentStatus.BUSY):
            logger.info(f"Agent {name} already alive (status={agent.status.value})")
            return agent

        # Need to spawn
        logger.info(f"Spawning agent {name}...")
        agent.status = AgentStatus.SPAWNING

        try:
            await self._spawn_agent(agent)
        except Exception as e:
            agent.status = AgentStatus.DEAD
            logger.error(f"Failed to spawn agent {name}: {e}")
            raise

        return agent

    async def _spawn_agent(self, agent: AgentState) -> None:
        """Spawn a Daimon process and initialize the ACP connection."""
        profile = agent.profile

        # Build the command and environment
        hermes_bin = (
            shutil.which("hermes")
            or os.path.expanduser("~/.local/bin/hermes")
            or "hermes"
        )
        command_parts = profile.launch_command.split()
        command = command_parts[0] if command_parts else "hermes"
        args = command_parts[1:] if len(command_parts) > 1 else []

        # If launch_command is just "hermes acp", use the hermes binary
        if command == "hermes":
            command = hermes_bin

        # Add --profile flag so hermes CLI doesn't fall back to active_profile
        # (which would override HERMES_HOME and load the wrong SOUL.md)
        if "--profile" not in args and "-p" not in args:
            args = args + ["--profile", agent.name]

        # Set HERMES_HOME to the profile directory
        env_extra = {
            "HERMES_HOME": str(profile.profile_path),
        }

        # Also pass through any .env file if it exists
        env_file = profile.profile_path / ".env"
        if env_file.exists():
            env_extra.update(self._load_env_file(env_file))

        # Create the OlympusClient for this agent
        client = OlympusACPClient(self.registry, agent.name)

        logger.info(f"Spawning {agent.name}: {command} {' '.join(args)} (HERMES_HOME={profile.profile_path})")

        try:
            cm = spawn_agent_process(client, command, *args, env={**os.environ, **env_extra})
            conn, proc = await cm.__aenter__()
        except Exception as e:
            logger.error(f"spawn_agent_process failed for {agent.name}: {e}")
            raise

        # Initialize the ACP connection
        logger.info(f"Initializing ACP connection for {agent.name}...")
        init_resp: InitializeResponse = await conn.initialize(
            protocol_version=PROTOCOL_VERSION,
            client_capabilities=ClientCapabilities(),
            client_info=Implementation(
                name="olympus-mcp",
                title="Olympus MCP Server",
                version="0.1.0",
            ),
        )

        logger.info(
            f"Agent {agent.name} initialized — "
            f"protocol={init_resp.protocol_version}, "
            f"info={init_resp.agent_info.name if init_resp.agent_info else 'unknown'}"
        )

        # Update agent state
        agent.connection = conn
        agent.process = cm  # Keep the context manager alive
        agent.pid = proc.pid if hasattr(proc, 'pid') else None
        agent.status = AgentStatus.IDLE

        logger.info(f"Agent {agent.name} spawned and initialized (PID={agent.pid})")

    def _load_env_file(self, path) -> dict[str, str]:
        """Load key=value pairs from a .env file."""
        env = {}
        try:
            with open(path) as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith("#") and "=" in line:
                        key, _, value = line.partition("=")
                        env[key.strip()] = value.strip()
        except Exception as e:
            logger.warning(f"Could not load .env file {path}: {e}")
        return env

    async def open_session(self, agent_name: str) -> SessionState:
        """Open a new ACP session on a live agent.

        If the agent isn't alive yet, ensure_agent will spawn it first.
        Returns a SessionState tracking the session.
        """
        agent = await self.ensure_agent(agent_name)

        if agent.connection is None:
            raise RuntimeError(f"Agent {agent_name} has no ACP connection")

        # Create ACP session — cwd is the project root, not AETHER_HOME.
        # This is where the project's .eter/ directory lives and where
        # Daimons should read/write their state files.
        project_root = str(self._config.project_root)
        session_resp: NewSessionResponse = await agent.connection.new_session(
            cwd=project_root,
            mcp_servers=[],  # Daimons don't need Olympus MCP — they talk TO us, not through another MCP server
        )

        acp_session_id = session_resp.session_id

        # Create our tracking session
        olympus_session_id = agent.next_session_id()
        session = SessionState(
            session_id=olympus_session_id,
            agent_name=agent_name,
        )
        # Store ACP session ID for mapping
        session.acp_connection = acp_session_id
        agent.sessions[olympus_session_id] = session

        # Update agent status
        agent.status = AgentStatus.BUSY

        logger.info(f"Session opened: {olympus_session_id} (ACP: {acp_session_id}) on agent {agent_name}")
        return session

    async def send_prompt(self, session_id: str, prompt_text: str) -> dict:
        """Send a prompt to an active session.

        Returns immediately with status='sent'. The response will be
        collected via session_updates and poll/wait.
        """
        session = self.registry.get_session(session_id)
        if session is None:
            raise ValueError(f"Unknown session: {session_id}")

        agent = self.registry.get_agent(session.agent_name)
        if agent is None or agent.connection is None:
            raise RuntimeError(f"Agent for session {session_id} has no connection")

        # Get the ACP session ID
        acp_session_id = session.acp_connection
        if acp_session_id is None:
            raise RuntimeError(f"Session {session_id} has no ACP session ID")

        # Send the prompt asynchronously — we collect the response via session_updates
        # Use asyncio.create_task to not block the MCP server
        async def _run_prompt():
            try:
                response: PromptResponse = await agent.connection.prompt(
                    session_id=acp_session_id,
                    prompt=[text_block(prompt_text)],
                )

                # Yield to event loop — ensure all pending session_update
                # callbacks (AgentMessageChunk/AgentThoughtChunk) are processed
                # before we collect the response. The ACP protocol sends the
                # response text via streaming notifications, and the PromptResponse
                # only contains stop_reason (no text). Without this yield,
                # the final messages may not yet be in session.messages.
                await asyncio.sleep(0)

                # Collect the final response from session messages
                full_response = "".join(session.messages) if session.messages else ""
                session.mark_done(
                    response=full_response,
                    stop_reason=response.stop_reason,
                )
                agent.status = AgentStatus.IDLE
                logger.info(f"Prompt completed for session {session_id}: stop_reason={response.stop_reason}, response_len={len(full_response)}")

            except Exception as e:
                logger.error(f"Prompt error for session {session_id}: {e}")
                session.mark_error(str(e))
                agent.status = AgentStatus.IDLE

        # Start the prompt as a background task
        asyncio.create_task(_run_prompt())

        return {
            "status": "sent",
            "session_id": session_id,
        }

    async def close_session(self, session_id: str) -> dict:
        """Close a session on the agent. The agent process stays alive (keep-alive)."""
        session = self.registry.get_session(session_id)
        if session is None:
            raise ValueError(f"Unknown session: {session_id}")

        agent = self.registry.get_agent(session.agent_name)
        if agent is None:
            raise ValueError(f"Unknown agent for session {session_id}")

        # Try to close the ACP session
        if agent.connection and session.acp_connection:
            try:
                await agent.connection.close_session(session.acp_connection)
            except Exception as e:
                logger.warning(f"Error closing ACP session {session.acp_connection}: {e}")

        session.status = SessionStatus.CLOSED
        session.completion_event.set()

        # Remove from agent's sessions
        if session_id in agent.sessions:
            del agent.sessions[session_id]

        logger.info(f"Session closed: {session_id}")
        return {"status": "closed", "session_id": session_id}

    async def cancel_session(self, session_id: str) -> dict:
        """Cancel a running session."""
        session = self.registry.get_session(session_id)
        if session is None:
            raise ValueError(f"Unknown session: {session_id}")

        agent = self.registry.get_agent(session.agent_name)
        if agent is None:
            raise ValueError(f"Unknown agent for session {session_id}")

        # Cancel via ACP
        if agent.connection and session.acp_connection:
            try:
                await agent.connection.cancel(session.acp_connection)
            except Exception as e:
                logger.warning(f"Error cancelling ACP session {session.acp_connection}: {e}")

        session.mark_cancelled()

        logger.info(f"Session cancelled: {session_id}")
        return {"status": "cancelled", "session_id": session_id}

    async def shutdown_agent(self, name: str) -> dict:
        """Gracefully shut down a Daimon process (SIGTERM)."""
        agent = self.registry.get_agent(name)
        if agent is None:
            raise ValueError(f"Unknown agent: {name}")

        if agent.status == AgentStatus.DEAD:
            return {"status": "already_dead", "agent": name}

        # Close all sessions first
        for session_id in list(agent.sessions.keys()):
            await self.close_session(session_id)

        # Close the ACP connection
        if agent.connection:
            try:
                await agent.connection.close()
            except Exception as e:
                logger.warning(f"Error closing ACP connection for {name}: {e}")

        # Terminate the process
        if agent.process:
            try:
                # The context manager should handle cleanup
                agent.status = AgentStatus.DEAD
            except Exception as e:
                logger.warning(f"Error terminating process for {name}: {e}")

        logger.info(f"Agent {name} shut down")
        return {"status": "shutdown", "agent": name}