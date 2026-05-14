"""Olympus v3 ACP Manager — manages Daimon processes via Agent Client Protocol.

Replaces v1's acp_client.py. Key differences:
- No session_update callback (replaced by plugin hooks -> SQLite)
- No in-memory registry (replaced by SQLite db)
- No event streaming (poll reads from SQLite, not ACP events)
- OlympusSessionIDs injected as env vars for plugin hooks
- Discover reads from hermes-agent profiles directory

Usage:
    manager = ACPManager()
    session_id = await manager.spawn_agent("hefesto")
    await manager.send_message(session_id, "Implement X")
    progress = await manager.poll(session_id)  # reads from SQLite
    await manager.close(session_id)
"""

from __future__ import annotations

import asyncio
import time

from olympus_v3.db import get_db_path
import logging
import os
import shutil
import tempfile
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from acp import PROTOCOL_VERSION
from acp.interfaces import Client
from acp.schema import (
    ClientCapabilities,
    Implementation,
    PermissionOption,
    RequestPermissionResponse,
    ToolCall,
)

try:
    from acp import spawn_agent_process, text_block
except ImportError:
    spawn_agent_process = None
    text_block = None

logger = logging.getLogger("olympus_v3.acp_manager")


# ---------------------------------------------------------------------------
# Agent state tracking
# ---------------------------------------------------------------------------

@dataclass
class AgentState:
    """Track a live Daimon process and its ACP connection."""
    name: str
    profile_path: Path
    connection: Any = None  # acp Connection
    process: Any = None  # subprocess context manager
    pid: int | None = None
    acp_session_ids: dict[str, str] = field(default_factory=dict)  # olympus_id -> acp_id
    status: str = "dead"  # dead, spawning, idle, busy


@dataclass
class SessionInfo:
    """Minimal session tracking (full state is in SQLite)."""
    session_id: str
    agent_name: str
    acp_session_id: str | None = None
    project_root: str | None = None  # cwd used for session, needed for .aether_home
    status: str = "active"  # active, completed, error, cancelled


# ---------------------------------------------------------------------------
# ACP Client (receives permission requests, no session_update)
# ---------------------------------------------------------------------------

class OlympusACPClient(Client):
    """Minimal ACP client that auto-approves permission requests.

    v3 does NOT implement session_update — plugin hooks write to SQLite instead.
    """

    async def request_permission(
        self,
        options: list[PermissionOption],
        session_id: str,
        tool_call: ToolCall | None = None,
        **kwargs: Any,
    ) -> RequestPermissionResponse:
        """Auto-approve all permission requests from Daimons."""
        logger.debug("Auto-approving permission for tool: %s", tool_call.name if tool_call else "unknown")
        return RequestPermissionResponse(
            permitted=True,
            reason="Auto-approved by Olympus v3 orchestrator",
        )

    async def session_update(self, session_id: str, update: Any, **kwargs: Any) -> None:
        """No-op in v3. Plugin hooks handle all data flow via SQLite."""
        pass


# ---------------------------------------------------------------------------
# ACP Manager
# ---------------------------------------------------------------------------

class ACPManager:
    """Manages Daimon processes via ACP.

    Lifecycle:
        1. spawn_agent() -> hermes -p <profile> --acp-server
        2. send_message() -> ACP prompt
        3. poll() -> reads SQLite (not ACP streaming)
        4. close() / cancel() -> terminate + update SQLite
    """

    def __init__(self, profiles_dir: Path | None = None, db: Any = None):
        self.agents: dict[str, AgentState] = {}
        self.sessions: dict[str, SessionInfo] = {}
        self.profiles_dir = profiles_dir or self._default_profiles_dir()
        self.db = db  # OlympusDB instance (set later via set_db)

    @staticmethod
    def _default_profiles_dir() -> Path:
        """Default profiles directory.
        
        Priority: HERMES_HOME parent > AETHER_HOME/profiles > ~/.hermes parent
        HERMES_HOME points to the profile dir itself (e.g., .../profiles/hermes),
        so its parent is the profiles directory.
        """
        hermes_home = os.environ.get("HERMES_HOME")
        if hermes_home:
            return Path(hermes_home).parent
        aether_home = os.environ.get("AETHER_HOME")
        if aether_home:
            return Path(aether_home) / "profiles"
        return Path(os.path.expanduser("~/.hermes")).parent

    def set_db(self, db: Any) -> None:
        """Set the OlympusDB instance for poll operations."""
        self.db = db

    # -------------------------------------------------------------------
    # Discovery
    # -------------------------------------------------------------------

    def discover(self) -> list[dict[str, Any]]:
        """List available Daimon profiles from the profiles directory.

        Returns list of dicts with name, profile_path, and config info.
        """
        profiles = []
        if not self.profiles_dir.exists():
            logger.warning("Profiles directory not found: %s", self.profiles_dir)
            return profiles

        for profile_dir in sorted(self.profiles_dir.iterdir()):
            if not profile_dir.is_dir():
                continue
            config_path = profile_dir / "config.yaml"
            soul_path = profile_dir / "SOUL.md"
            if not (config_path.exists() or soul_path.exists()):
                continue

            profiles.append({
                "name": profile_dir.name,
                "profile_path": str(profile_dir),
                "has_config": config_path.exists(),
                "has_soul": soul_path.exists(),
            })

        logger.info("Discovered %d profiles in %s", len(profiles), self.profiles_dir)
        return profiles

    # -------------------------------------------------------------------
    # Agent lifecycle
    # -------------------------------------------------------------------

    async def spawn_agent(
        self,
        agent_name: str,
        session_id: str | None = None,
        project_root: str | None = None,
    ) -> str:
        """Spawn a Daimon process with ACP and register in SQLite.

        Args:
            agent_name: Profile name (e.g., 'hefesto')
            session_id: Optional session ID (generated if not provided)
            project_root: Working directory for the Daimon session

        Returns:
            session_id for tracking in SQLite
        """
        if spawn_agent_process is None:
            raise RuntimeError("agent-client-protocol package not installed")

        sid = session_id or str(uuid.uuid4())

        # Find profile directory
        profile_path = self.profiles_dir / agent_name
        if not profile_path.exists():
            raise ValueError(f"Profile not found: {agent_name} at {profile_path}")

        # Create or reuse agent state
        agent = self.agents.get(agent_name)
        if agent is None or agent.status in ("dead",):
            agent = AgentState(
                name=agent_name,
                profile_path=profile_path,
                status="spawning",
            )
            self.agents[agent_name] = agent

        # If agent is already idle, reuse it
        if agent.status in ("idle",) and agent.connection is not None:
            logger.info("Reusing existing agent %s (idle)", agent_name)
        else:
            # Spawn new process
            await self._spawn_process(agent, project_root=project_root)

        # Create ACP session
        if agent.connection is None:
            raise RuntimeError(f"Agent {agent_name} has no ACP connection after spawn")

        cwd = project_root or os.environ.get("AETHER_HOME", str(Path.cwd()))
        session_resp = await agent.connection.new_session(
            cwd=cwd,
            mcp_servers=[],
        )
        acp_session_id = session_resp.session_id

        # Track session
        session = SessionInfo(
            session_id=sid,
            agent_name=agent_name,
            acp_session_id=acp_session_id,
            project_root=cwd,
        )
        self.sessions[sid] = session
        agent.acp_session_ids[sid] = acp_session_id
        agent.status = "busy"

        # Register in SQLite
        if self.db:
            await self.db.insert_session(
                session_id=sid,
                agent=agent_name,
                metadata={"acp_session_id": acp_session_id, "profile": agent_name},
            )

        logger.info("Session opened: %s (ACP: %s) on agent %s", sid, acp_session_id, agent_name)
        return sid

    async def _spawn_process(self, agent: AgentState, project_root: str | None = None) -> None:
        """Spawn a hermes-agent process with ACP server mode."""
        hermes_bin = (
            shutil.which("hermes")
            or os.path.expanduser("~/.local/bin/hermes")
            or "hermes"
        )

        # Build command: hermes acp --profile <name>
        command = hermes_bin
        args = ["acp", "--profile", agent.name]

        # Environment: HERMES_HOME + AETHER_HOME + PYTHONPATH + OLYMPUS vars
        env_extra = {
            "HERMES_HOME": str(agent.profile_path),
        }
        # AETHER_HOME: always set to project_root (cwd of the session)
        # This ensures Daimon plugin hooks can find .aether/ regardless of
        # whether the server has AETHER_HOME in its own environment.
        aether_home = project_root or os.environ.get("AETHER_HOME") or str(Path.cwd())
        env_extra["AETHER_HOME"] = str(aether_home)
        # PYTHONPATH so the Daimon process can import olympus_v3 modules (plugin hooks)
        pythonpath = os.environ.get("PYTHONPATH", "")
        src_dir = str(Path(__file__).parent.parent)  # olympus_v3/src -> src
        if pythonpath:
            env_extra["PYTHONPATH"] = f"{src_dir}:{pythonpath}"
        else:
            env_extra["PYTHONPATH"] = src_dir

        # OLYMPUS_DB_PATH so plugin hooks can find the database at spawn time
        db_path = get_db_path()
        env_extra["OLYMPUS_DB_PATH"] = str(db_path)

        # Load .env if it exists
        env_file = agent.profile_path / ".env"
        if env_file.exists():
            env_extra.update(self._load_env_file(env_file))

        # Create ACP client
        client = OlympusACPClient()

        logger.info("Spawning %s: %s %s (HERMES_HOME=%s)",
                     agent.name, command, " ".join(args), agent.profile_path)

        try:
            cm = spawn_agent_process(client, command, *args, env={**os.environ, **env_extra})
            conn, proc = await cm.__aenter__()
        except Exception as e:
            agent.status = "dead"
            logger.error("spawn_agent_process failed for %s: %s", agent.name, e)
            raise

        # Initialize ACP connection
        init_resp = await conn.initialize(
            protocol_version=PROTOCOL_VERSION,
            client_capabilities=ClientCapabilities(),
            client_info=Implementation(
                name="olympus-v3",
                title="Olympus v3 MCP Server",
                version="0.1.0",
            ),
        )

        logger.info("Agent %s initialized (protocol=%s)",
                     agent.name, init_resp.protocol_version)

        agent.connection = conn
        agent.process = cm
        agent.pid = proc.pid if hasattr(proc, "pid") else None
        agent.status = "idle"

    @staticmethod
    def _load_env_file(path: Path) -> dict[str, str]:
        """Load key=value pairs from a .env file."""
        env = {}
        try:
            for line in path.read_text().splitlines():
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                if "=" in line:
                    key, _, value = line.partition("=")
                    key = key.strip()
                    value = value.strip().strip("'\"")
                    if key and value:
                        env[key] = value
        except Exception as e:
            logger.warning("Failed to load .env file %s: %s", path, e)
        return env

    # -------------------------------------------------------------------
    # Atomic file helpers
    # -------------------------------------------------------------------

    @staticmethod
    def _atomic_write(path: Path, content: str) -> None:
        """Write content to a file atomically (temp file + rename).

        Avoids partial reads if the Daimon process reads the file while
        we are still writing.
        """
        path.parent.mkdir(parents=True, exist_ok=True)
        fd, tmp_path = tempfile.mkstemp(dir=str(path.parent))
        try:
            with os.fdopen(fd, "w") as f:
                f.write(content)
            os.replace(tmp_path, path)
        except BaseException:
            # Clean up temp file on any error (including cancellation)
            try:
                os.unlink(tmp_path)
            except OSError:
                pass
            raise

    # -------------------------------------------------------------------
    # Messaging
    # -------------------------------------------------------------------

    async def send_message(self, session_id: str, message: str) -> dict:
        """Send a prompt to an active Daimon session.

        Returns immediately with status='sent'. Response is captured
        by plugin hooks writing to SQLite.
        """
        session = self.sessions.get(session_id)
        if session is None:
            raise ValueError(f"Unknown session: {session_id}")

        agent = self.agents.get(session.agent_name)
        if agent is None or agent.connection is None:
            raise RuntimeError(f"Agent for session {session_id} has no connection")

        acp_session_id = session.acp_session_id
        if acp_session_id is None:
            raise RuntimeError(f"Session {session_id} has no ACP session ID")

        # Write session mapping files so the Daimon's plugin hooks can
        # discover the current session ID and DB path.  This is the
        # fallback mechanism when OLYMPUS_SESSION_ID is not set in env
        # (which it cannot be — the process is spawned before any session
        # exists, and env vars cannot be injected into a running process).
        try:
            self._atomic_write(agent.profile_path / ".olympus_session", session_id)
            logger.debug("Wrote .olympus_session for %s: %s", agent.name, session_id)
        except Exception as e:
            logger.warning("Failed to write .olympus_session for %s: %s", agent.name, e)

        try:
            db_path = str(get_db_path())
            self._atomic_write(agent.profile_path / ".olympus_db_path", db_path)
            logger.debug("Wrote .olympus_db_path for %s: %s", agent.name, db_path)
        except Exception as e:
            logger.warning("Failed to write .olympus_db_path for %s: %s", agent.name, e)

        # Write .aether_home so Daimon plugin hooks can find the project root
        try:
            aether_home_value = session.project_root or os.environ.get("AETHER_HOME") or str(Path.cwd().resolve())
            aether_home_file = Path(agent.profile_path) / ".aether_home"
            aether_home_file.write_text(aether_home_value)
            logger.debug("Wrote .aether_home for %s: %s", agent.name, aether_home_value)
        except Exception as e:
            logger.warning("Failed to write .aether_home for %s: %s", agent.name, e)

        # Send prompt as background task
        async def _run_prompt():
            try:
                response = await agent.connection.prompt(
                    session_id=acp_session_id,
                    prompt=[text_block(message)],
                )
                logger.info("Prompt completed for session %s (stop_reason=%s)",
                            session_id, response.stop_reason)
                # Update in-memory session status so poll() can detect completion
                if session_id in self.sessions:
                    self.sessions[session_id].status = "completed"
            except Exception as e:
                logger.error("Prompt error for session %s: %s", session_id, e)
                if session_id in self.sessions:
                    self.sessions[session_id].status = "error"
                if self.db:
                    await self.db.update_session_status(session_id, "error")

        asyncio.create_task(_run_prompt())

        return {"status": "sent", "session_id": session_id}

    # -------------------------------------------------------------------
    # State queries (read from SQLite, NOT from ACP)
    # -------------------------------------------------------------------

    async def poll(self, session_id: str) -> dict:
        """Read latest state from SQLite, enriched with in-memory session status.

        SQLite holds turn/tool_call data written by plugin hooks.
        In-memory SessionInfo tracks prompt completion for real-time status.

        Returns dict with: thoughts, messages, tool_calls, status,
        last_turn, last_reasoning.
        """
        if self.db is None:
            raise RuntimeError("No database configured for poll")

        # Get data from SQLite (turns, tool_calls, last_turn)
        progress = await self.db.get_session_progress(session_id)

        # Merge in-memory session status if available
        session = self.sessions.get(session_id)
        if session:
            # In-memory status is more up-to-date than SQLite for completion
            # because on_session_end hook writes to SQLite asynchronously
            # while the callback in _run_prompt sets session.status immediately.
            if session.status in ("completed", "error", "cancelled"):
                progress["status"] = session.status

        return progress

    # -------------------------------------------------------------------
    # Session lifecycle
    # -------------------------------------------------------------------

    async def close(self, session_id: str) -> dict:
        """Close a session and mark it completed in SQLite."""
        session = self.sessions.get(session_id)
        if session is None:
            raise ValueError(f"Unknown session: {session_id}")

        agent = self.agents.get(session.agent_name)

        # Close ACP session
        if agent and agent.connection and session.acp_session_id:
            try:
                await agent.connection.close_session(session.acp_session_id)
            except Exception as e:
                logger.warning("Error closing ACP session %s: %s", session.acp_session_id, e)

        # Update SQLite
        if self.db:
            await self.db.update_session_status(session_id, "completed")

        # Cleanup
        session.status = "completed"
        if agent and session_id in agent.acp_session_ids:
            del agent.acp_session_ids[session_id]
        if session_id in self.sessions:
            del self.sessions[session_id]

        # Mark agent idle if no more sessions
        if agent and not agent.acp_session_ids:
            agent.status = "idle"

        logger.info("Session closed: %s", session_id)
        return {"status": "completed", "session_id": session_id}

    async def cancel(self, session_id: str) -> dict:
        """Force-cancel a stuck session."""
        session = self.sessions.get(session_id)
        if session is None:
            raise ValueError(f"Unknown session: {session_id}")

        agent = self.agents.get(session.agent_name)

        # Cancel via ACP
        if agent and agent.connection and session.acp_session_id:
            try:
                await agent.connection.cancel(session.acp_session_id)
            except Exception as e:
                logger.warning("Error cancelling ACP session %s: %s", session.acp_session_id, e)

        # Update SQLite
        if self.db:
            await self.db.update_session_status(session_id, "cancelled")

        session.status = "cancelled"
        if agent and session_id in agent.acp_session_ids:
            del agent.acp_session_ids[session_id]
        if session_id in self.sessions:
            del self.sessions[session_id]

        if agent and not agent.acp_session_ids:
            agent.status = "idle"

        logger.info("Session cancelled: %s", session_id)
        return {"status": "cancelled", "session_id": session_id}

    # -------------------------------------------------------------------
    # Delegate — open + message + auto-poll until done
    # -------------------------------------------------------------------

    async def delegate(
        self,
        agent_name: str,
        prompt: str,
        project_root: str | None = None,
        poll_interval: int = 15,
        timeout: int = 300,
    ) -> dict[str, Any]:
        """Spawn an agent, send a prompt, and auto-poll until completion.

        This is a convenience method that combines spawn, send_message, and
        a poll loop into a single call.  It waits for the agent to finish
        (or time out) and returns the full progress dict enriched with
        session_id and elapsed_seconds.

        Args:
            agent_name: Daimon profile name to spawn.
            prompt: The prompt text to send.
            project_root: Working directory for the Daimon session.
            poll_interval: Seconds between poll iterations.
            timeout: Maximum seconds to wait for completion.

        Returns:
            Dict with keys: session_id, status, thoughts, messages,
            tool_calls, last_turn, last_reasoning, elapsed_seconds,
            timed_out (bool), poll_iterations (int).
        """
        from .config_loader import get_config

        config = get_config()
        stall_timeout = config.stall_timeout
        max_poll_iterations = config.max_poll_iterations

        start_time = time.monotonic()

        # 1. Spawn agent
        session_id = await self.spawn_agent(
            agent_name=agent_name,
            project_root=project_root,
        )
        logger.info("[delegate] Spawned %s as session %s", agent_name, session_id)

        # 2. Send prompt
        await self.send_message(session_id, prompt)
        logger.info("[delegate] Prompt sent to session %s", session_id)

        # 3. Auto-poll loop
        poll_iterations = 0
        last_thoughts = 0
        last_messages = 0
        last_tool_calls = 0
        stall_count = 0

        while True:
            await asyncio.sleep(poll_interval)
            poll_iterations += 1
            elapsed = time.monotonic() - start_time

            try:
                progress = await self.poll(session_id)
            except Exception as e:
                logger.warning("[delegate] Poll error for %s: %s", session_id, e)
                continue

            status = progress.get("status", "unknown")

            # Completion
            if status in ("completed", "error", "cancelled"):
                progress["session_id"] = session_id
                progress["timed_out"] = False
                progress["elapsed_seconds"] = round(elapsed, 1)
                progress["poll_iterations"] = poll_iterations
                logger.info(
                    "[delegate] %s completed in %.1fs (iterations=%d)",
                    agent_name, elapsed, poll_iterations,
                )
                return progress

            # Timeout
            if elapsed >= timeout:
                progress["session_id"] = session_id
                progress["timed_out"] = True
                progress["elapsed_seconds"] = round(elapsed, 1)
                progress["poll_iterations"] = poll_iterations
                logger.error("[delegate] %s TIMED OUT after %ds", agent_name, timeout)
                try:
                    await self.close(session_id)
                except Exception:
                    pass
                return progress

            # Stall detection
            current_thoughts = progress.get("thoughts", 0)
            current_messages = progress.get("messages", 0)
            current_tool_calls = progress.get("tool_calls", 0)

            if (current_thoughts == last_thoughts
                    and current_messages == last_messages
                    and current_tool_calls == last_tool_calls):
                stall_count += 1
                active_stall_limit = stall_timeout * 2 if status == "active" else stall_timeout
                if stall_count * poll_interval >= active_stall_limit:
                    progress["session_id"] = session_id
                    progress["timed_out"] = False
                    progress["stalled"] = True
                    progress["elapsed_seconds"] = round(elapsed, 1)
                    progress["poll_iterations"] = poll_iterations
                    logger.warning("[delegate] %s STALLED after %.1fs", agent_name, elapsed)
                    try:
                        await self.close(session_id)
                    except Exception:
                        pass
                    return progress
            else:
                stall_count = 0

            last_thoughts = current_thoughts
            last_messages = current_messages
            last_tool_calls = current_tool_calls

            # Safety limit
            if poll_iterations >= max_poll_iterations:
                progress["session_id"] = session_id
                progress["timed_out"] = True
                progress["elapsed_seconds"] = round(elapsed, 1)
                progress["poll_iterations"] = poll_iterations
                progress["reason"] = "max_poll_iterations_reached"
                logger.error("[delegate] %s hit max poll iterations", agent_name)
                try:
                    await self.close(session_id)
                except Exception:
                    pass
                return progress

    async def shutdown_agent(self, name: str) -> dict:
        """Gracefully shut down a Daimon process."""
        agent = self.agents.get(name)
        if agent is None:
            return {"status": "already_dead", "agent": name}

        if agent.status == "dead":
            return {"status": "already_dead", "agent": name}

        # Close all sessions
        for sid in list(agent.acp_session_ids.keys()):
            try:
                await self.close(sid)
            except Exception as e:
                logger.warning("Error closing session %s during shutdown: %s", sid, e)

        # Close ACP connection
        if agent.connection:
            try:
                await agent.connection.close()
            except Exception as e:
                logger.warning("Error closing ACP connection for %s: %s", name, e)

        # Terminate process
        agent.status = "dead"
        if agent.process is not None:
            try:
                agent.process.terminate()
                try:
                    await asyncio.wait_for(agent.process.wait(), timeout=5.0)
                except asyncio.TimeoutError:
                    agent.process.kill()
                    await agent.process.wait()
                logger.info("Terminated process for %s (PID: %s)", name, agent.pid)
            except ProcessLookupError:
                logger.info("Process for %s already terminated", name)
            except Exception as e:
                logger.warning("Error terminating process for %s: %s", name, e)

        self.agents.pop(name, None)
        logger.info("Agent %s shut down", name)
        return {"status": "shutdown", "agent": name}
