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
import contextlib
import hashlib
import logging
import os
import re
import shutil
import tempfile
import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from acp import PROTOCOL_VERSION
from acp.interfaces import Client
from acp.schema import (
    AllowedOutcome,
    ClientCapabilities,
    DeniedOutcome,
    Implementation,
    PermissionOption,
    RequestPermissionResponse,
    ToolCall,
)

from olympus_v3.db import get_db_path

try:
    from acp import spawn_agent_process, text_block
except ImportError:
    spawn_agent_process = None
    text_block = None

logger = logging.getLogger("olympus_v3.acp_manager")

# Match ACP 0.9's finite agent-side stdio default without importing a newer
# compatibility symbol that older supported agent-client-protocol releases lack.
DEFAULT_ACP_STREAM_LIMIT = 50 * 1024 * 1024
DEFAULT_SESSION_OPEN_TIMEOUT = 30.0


# ---------------------------------------------------------------------------
# Agent state tracking
# ---------------------------------------------------------------------------

@dataclass
class AgentState:
    """Track a live Daimon process and its ACP connection."""
    name: str
    profile_path: Path
    connection: Any = None  # acp Connection
    process_context: Any = None  # async context manager from spawn_agent_process
    process: Any = None  # actual subprocess yielded by process_context
    pid: int | None = None
    acp_session_ids: dict[str, str] = field(default_factory=dict)  # olympus_id -> acp_id
    prompt_tasks: dict[str, asyncio.Task[Any]] = field(default_factory=dict)
    prompt_lock: asyncio.Lock = field(default_factory=asyncio.Lock)
    mapping_lock: asyncio.Lock = field(default_factory=asyncio.Lock)
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
        """Select an offered allow option, never inventing a permission ID."""
        tool_title = getattr(tool_call, "title", None) or getattr(tool_call, "name", None) or "unknown"
        tool_call_id = getattr(tool_call, "tool_call_id", None) or getattr(tool_call, "toolCallId", None)
        logger.debug(
            "Auto-handling permission for tool title=%s tool_call_id=%s",
            tool_title,
            tool_call_id or "unknown",
        )

        for allowed_kind in ("allow_always", "allow_once"):
            selected = next((option for option in options if option.kind == allowed_kind), None)
            if selected is not None:
                logger.debug(
                    "Selected ACP permission option %s (%s) for tool_call_id=%s",
                    selected.option_id,
                    selected.kind,
                    tool_call_id or "unknown",
                )
                return RequestPermissionResponse(
                    outcome=AllowedOutcome(optionId=selected.option_id, outcome="selected"),
                )

        logger.warning(
            "Denying ACP permission because no allow option was offered for tool_call_id=%s",
            tool_call_id or "unknown",
        )
        return RequestPermissionResponse(outcome=DeniedOutcome(outcome="cancelled"))

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

    def __init__(
        self,
        profiles_dir: Path | None = None,
        db: Any = None,
        *,
        acp_stream_limit: int = DEFAULT_ACP_STREAM_LIMIT,
        session_open_timeout: float = DEFAULT_SESSION_OPEN_TIMEOUT,
    ):
        if not isinstance(acp_stream_limit, int) or acp_stream_limit < 64 * 1024:
            raise ValueError("acp_stream_limit must be an integer of at least 65536 bytes")
        if not isinstance(session_open_timeout, (int, float)) or session_open_timeout <= 0:
            raise ValueError("session_open_timeout must be positive")

        self.agents: dict[tuple[str, str], AgentState] = {}
        self.sessions: dict[str, SessionInfo] = {}
        self._spawn_locks: dict[tuple[str, str], asyncio.Lock] = {}
        self._reserved_session_ids: set[str] = set()
        self.profiles_dir = profiles_dir or self._default_profiles_dir()
        self.db = db  # OlympusDB instance (set later via set_db)
        self.acp_stream_limit = acp_stream_limit
        self.session_open_timeout = float(session_open_timeout)

    @staticmethod
    def _default_profiles_dir() -> Path:
        """Default profiles directory.

        Priority: HERMES_HOME parent > AETHER_HOME/profiles > ~/.hermes parent
        HERMES_HOME points to the home dir (e.g., .../home),
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

    @staticmethod
    def _agent_key(agent_name: str, project_root: str | None) -> tuple[str, str]:
        """Build the compound key for the agents dict: (agent_name, project_root)."""
        root = Path(project_root).expanduser().resolve() if project_root else Path.cwd().resolve()
        return (agent_name, str(root))

    @staticmethod
    def _canonical_project_root(project_root: str | None) -> str:
        """Return the one identity path used by all lifecycle state."""
        return str(Path(project_root).expanduser().resolve() if project_root else Path.cwd().resolve())

    def _lifecycle_lock(self, key: tuple[str, str]) -> asyncio.Lock:
        return self._spawn_locks.setdefault(key, asyncio.Lock())

    def get_agent(self, agent_name: str, project_root: str | None = None) -> AgentState | None:
        """Look up an agent by name and project_root."""
        key = self._agent_key(agent_name, project_root)
        return self.agents.get(key)

    @staticmethod
    def _agent_is_healthy(agent: AgentState) -> bool:
        """Return whether an agent can safely receive another ACP request."""
        if agent.status == "dead" or agent.connection is None:
            return False
        if getattr(agent.connection, "_closed", False):
            return False
        receive_task = getattr(agent.connection, "_recv_task", None)
        if receive_task is not None and receive_task.done():
            return False
        if agent.process is not None and getattr(agent.process, "returncode", None) is not None:
            return False
        return True

    @staticmethod
    async def _dispose_agent_transport(agent: AgentState) -> None:
        """Close the owning context and bound fallback process termination."""
        async def _dispose() -> None:
            fallback_terminate = agent.process_context is None
            try:
                if agent.process_context is not None:
                    try:
                        await asyncio.wait_for(
                            agent.process_context.__aexit__(None, None, None), timeout=5.0
                        )
                    except Exception:
                        fallback_terminate = True
                elif agent.connection is not None:
                    with contextlib.suppress(Exception):
                        await agent.connection.close()

                process = agent.process
                if fallback_terminate and process is not None and hasattr(process, "terminate"):
                    try:
                        process.terminate()
                        try:
                            await asyncio.wait_for(process.wait(), timeout=5.0)
                        except asyncio.TimeoutError:
                            process.kill()
                            await asyncio.wait_for(process.wait(), timeout=5.0)
                    except ProcessLookupError:
                        pass
                    except Exception as e:
                        logger.warning("Failed fallback termination for %s: %s", agent.name, e)
            finally:
                agent.connection = None
                agent.process_context = None
                agent.process = None
                agent.pid = None

        cleanup = asyncio.create_task(_dispose())
        try:
            await asyncio.shield(cleanup)
        except asyncio.CancelledError:
            with contextlib.suppress(asyncio.TimeoutError, Exception):
                await asyncio.wait_for(asyncio.shield(cleanup), timeout=5.0)
            raise

    @staticmethod
    async def _run_cleanup_to_completion(
        cleanup_coro: Any,
        *,
        timeout: float = 15.0,
    ) -> None:
        """Finish bounded cleanup before propagating caller cancellation."""
        cleanup = asyncio.create_task(cleanup_coro)
        deadline = asyncio.get_running_loop().time() + timeout
        caller_cancelled = False
        while not cleanup.done():
            remaining = deadline - asyncio.get_running_loop().time()
            if remaining <= 0:
                cleanup.cancel()
                with contextlib.suppress(asyncio.CancelledError, Exception):
                    await cleanup
                raise TimeoutError(f"Lifecycle cleanup exceeded {timeout:g}s")
            try:
                async with asyncio.timeout(remaining):
                    await asyncio.shield(cleanup)
            except asyncio.CancelledError:
                caller_cancelled = True
                continue
            except asyncio.TimeoutError:
                cleanup.cancel()
                with contextlib.suppress(asyncio.CancelledError, Exception):
                    await cleanup
                raise TimeoutError(f"Lifecycle cleanup exceeded {timeout:g}s")

        cleanup.result()
        if caller_cancelled:
            raise asyncio.CancelledError

    async def _rollback_unpublished_session(
        self,
        key: tuple[str, str],
        agent: AgentState,
        acp_session_id: str,
    ) -> None:
        """Release a raw ACP session and any otherwise unowned transport."""
        try:
            if agent.connection is not None:
                await asyncio.wait_for(
                    agent.connection.close_session(acp_session_id),
                    timeout=5.0,
                )
        except BaseException as exc:
            logger.warning("Failed unpublished ACP session cleanup %s: %s", acp_session_id, exc)
        finally:
            if not agent.acp_session_ids and self.agents.get(key) is agent:
                agent.status = "dead"
                await self._dispose_agent_transport(agent)
                if self.agents.get(key) is agent:
                    self.agents.pop(key, None)

    async def _invalidate_agent(
        self,
        key: tuple[str, str],
        agent: AgentState,
        *,
        reason: str,
        session_status: str = "error",
    ) -> None:
        """Fail all sessions and dispose a broken agent without deleting a replacement."""
        logger.warning("Invalidating agent %s for project %s: %s", agent.name, key[1], reason)
        agent.status = "dead"
        if self.agents.get(key) is agent:
            self.agents.pop(key, None)

        current_task = asyncio.current_task()
        tasks = list(agent.prompt_tasks.values())
        for task in tasks:
            if task is not current_task and not task.done():
                task.cancel()
        for task in tasks:
            if task is not current_task:
                with contextlib.suppress(asyncio.CancelledError, Exception):
                    await task
        agent.prompt_tasks.clear()

        for sid in list(agent.acp_session_ids):
            session = self.sessions.get(sid)
            if session is not None and session.status not in ("completed", "cancelled"):
                session.status = session_status
                if self.db:
                    try:
                        await self.db.update_session_status(sid, session_status)
                    except Exception as exc:
                        logger.warning("Failed to persist invalidated session %s: %s", sid, exc)

        await self._dispose_agent_transport(agent)

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
        """Reserve one globally unique logical ID, then open its ACP session."""
        sid = session_id or str(uuid.uuid4())
        if sid in self.sessions or sid in self._reserved_session_ids:
            raise ValueError(f"Session already exists: {sid}")
        # The check and add contain no await, so they are atomic within the
        # manager's event loop even when different project locks are used.
        self._reserved_session_ids.add(sid)
        try:
            return await self._spawn_agent_reserved(
                agent_name=agent_name,
                session_id=sid,
                project_root=project_root,
            )
        finally:
            self._reserved_session_ids.discard(sid)

    async def _spawn_agent_reserved(
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
        cwd = self._canonical_project_root(project_root)
        key = self._agent_key(agent_name, cwd)

        # Find profile directory
        profile_path = self.profiles_dir / agent_name
        if not profile_path.exists():
            raise ValueError(f"Profile not found: {agent_name} at {profile_path}")

        # Serialize lookup/spawn/session-open for one agent+project key. Locks
        # differ across projects, so independent work still starts in parallel.
        lock = self._lifecycle_lock(key)
        async with lock:
            if sid in self.sessions:
                raise ValueError(f"Session already exists: {sid}")
            agent = self.agents.get(key)
            if agent is not None and not self._agent_is_healthy(agent):
                await self._invalidate_agent(key, agent, reason="failed pre-reuse health check")
                agent = None

            if agent is None:
                agent = AgentState(
                    name=agent_name,
                    profile_path=profile_path,
                    status="spawning",
                )
                self.agents[key] = agent
                try:
                    await self._spawn_process(agent, project_root=cwd)
                except BaseException:
                    await self._invalidate_agent(key, agent, reason="process spawn failed")
                    raise
            else:
                logger.info(
                    "Reusing healthy agent %s for project %s (status=%s)",
                    agent_name,
                    project_root,
                    agent.status,
                )

            if agent.connection is None:
                await self._invalidate_agent(key, agent, reason="spawn produced no ACP connection")
                raise RuntimeError(f"Agent {agent_name} has no ACP connection after spawn")

            try:
                session_resp = await asyncio.wait_for(
                    agent.connection.new_session(cwd=cwd, mcp_servers=[]),
                    timeout=self.session_open_timeout,
                )
            except asyncio.TimeoutError as exc:
                await self._invalidate_agent(key, agent, reason="new_session timeout")
                raise TimeoutError(
                    f"Agent {agent_name} new_session timed out after "
                    f"{self.session_open_timeout:g}s"
                ) from exc
            except BaseException:
                await self._invalidate_agent(key, agent, reason="new_session failed")
                raise

            acp_session_id = session_resp.session_id
            if self.agents.get(key) is not agent or agent.status == "dead":
                await self._run_cleanup_to_completion(
                    self._rollback_unpublished_session(key, agent, acp_session_id)
                )
                raise RuntimeError("Agent ownership changed while opening ACP session")
            session = SessionInfo(
                session_id=sid,
                agent_name=agent_name,
                acp_session_id=acp_session_id,
                project_root=cwd,
            )
            try:
                if self.db:
                    await self.db.insert_session(
                        session_id=sid,
                        agent=agent_name,
                        metadata={
                            "acp_session_id": acp_session_id,
                            "profile": agent_name,
                            "project_root": cwd,
                        },
                    )
            except BaseException:
                await self._run_cleanup_to_completion(
                    self._rollback_unpublished_session(key, agent, acp_session_id)
                )
                raise

            self.sessions[sid] = session
            agent.acp_session_ids[sid] = acp_session_id
            agent.status = "busy"

            logger.info("Session opened: %s (ACP: %s) on agent %s", sid, acp_session_id, agent_name)
            return sid

    async def _spawn_process(self, agent: AgentState, project_root: str | None = None) -> None:
        """Spawn a hermes-agent process with ACP server mode."""
        if spawn_agent_process is None:
            raise RuntimeError("agent-client-protocol package not installed")
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
            cm = spawn_agent_process(
                client,
                command,
                *args,
                env={**os.environ, **env_extra},
                transport_kwargs={"limit": self.acp_stream_limit},
            )
            conn, proc = await cm.__aenter__()
        except Exception as e:
            agent.status = "dead"
            logger.error("spawn_agent_process failed for %s: %s", agent.name, e)
            raise

        agent.connection = conn
        agent.process_context = cm
        agent.process = proc
        agent.pid = proc.pid if hasattr(proc, "pid") else None

        try:
            init_resp = await conn.initialize(
                protocol_version=PROTOCOL_VERSION,
                client_capabilities=ClientCapabilities(),
                client_info=Implementation(
                    name="olympus-v3",
                    title="Olympus v3 MCP Server",
                    version="0.1.0",
                ),
            )
        except BaseException:
            agent.status = "dead"
            await self._dispose_agent_transport(agent)
            raise

        logger.info("Agent %s initialized (protocol=%s)",
                     agent.name, init_resp.protocol_version)

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

    def _write_session_mapping(
        self,
        agent: AgentState,
        session: SessionInfo,
        session_id: str,
    ) -> None:
        """Publish one prompt's PID-scoped plugin mapping or fail closed."""
        pid = agent.pid or os.getpid()
        paths = (
            (agent.profile_path / f".olympus_session.{pid}", session_id),
            (agent.profile_path / f".olympus_db_path.{pid}", str(get_db_path())),
            (
                agent.profile_path / f".aether_home.{pid}",
                session.project_root or os.environ.get("AETHER_HOME") or str(Path.cwd().resolve()),
            ),
        )
        try:
            for path, content in paths:
                self._atomic_write(path, content)
        except BaseException:
            for path, _ in paths:
                with contextlib.suppress(OSError):
                    path.unlink(missing_ok=True)
            raise
        logger.debug("Published PID-scoped session mapping for %s (PID %d)", agent.name, pid)

    @staticmethod
    def _remove_pid_mappings(
        agent: AgentState,
        pid: int | None,
        *,
        session_id: str | None = None,
    ) -> None:
        if pid is None:
            return
        session_path = agent.profile_path / f".olympus_session.{pid}"
        if session_id is not None:
            try:
                if session_path.read_text() != session_id:
                    return
            except OSError:
                return
        for suffix in (
            f".olympus_session.{pid}",
            f".olympus_db_path.{pid}",
            f".aether_home.{pid}",
        ):
            with contextlib.suppress(OSError):
                (agent.profile_path / suffix).unlink(missing_ok=True)

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

        agent = self.agents.get(self._agent_key(session.agent_name, session.project_root))
        if agent is None or agent.connection is None:
            raise RuntimeError(f"Agent for session {session_id} has no connection")

        existing_task = agent.prompt_tasks.get(session_id)
        if existing_task is not None and not existing_task.done():
            raise RuntimeError(f"Session {session_id} already has an active prompt")
        if not self._agent_is_healthy(agent):
            key = self._agent_key(session.agent_name, session.project_root)
            await self._invalidate_agent(key, agent, reason="failed pre-prompt health check")
            raise RuntimeError(f"Agent for session {session_id} is not healthy")

        acp_session_id = session.acp_session_id
        if acp_session_id is None:
            raise RuntimeError(f"Session {session_id} has no ACP session ID")

        # Send prompt as background task
        async def _execute_prompt():
            try:
                response = await agent.connection.prompt(
                    session_id=acp_session_id,
                    prompt=[text_block(message)],
                )
                stop_reason = getattr(response, "stop_reason", None)
                reason_value = getattr(stop_reason, "value", stop_reason)
                reason_value = getattr(reason_value, "name", reason_value)
                reason = str(reason_value).strip().lower()
                if reason == "end_turn":
                    terminal_status = "completed"
                elif reason == "cancelled":
                    terminal_status = "cancelled"
                else:
                    terminal_status = "error"

                logger.info(
                    "Prompt ended for session %s (stop_reason=%r, status=%s)",
                    session_id,
                    stop_reason,
                    terminal_status,
                )
                # Update both in-memory and SQLite state so poll() cannot turn a
                # non-normal ACP termination into a successful completion.
                if session_id in self.sessions:
                    self.sessions[session_id].status = terminal_status
                if self.db:
                    await self.db.update_session_status(session_id, terminal_status)
            except Exception as e:
                logger.error("Prompt error for session %s: %s", session_id, e)
                if not self._agent_is_healthy(agent):
                    key = self._agent_key(session.agent_name, session.project_root)
                    await self._invalidate_agent(
                        key,
                        agent,
                        reason=f"prompt transport failed: {e}",
                    )
                else:
                    if session_id in self.sessions:
                        self.sessions[session_id].status = "error"
                    if self.db:
                        await self.db.update_session_status(session_id, "error")

        async def _run_prompt():
            async with agent.prompt_lock:
                if (
                    self.sessions.get(session_id) is not session
                    or agent.acp_session_ids.get(session_id) != acp_session_id
                    or self.agents.get(self._agent_key(session.agent_name, session.project_root)) is not agent
                ):
                    return
                if not self._agent_is_healthy(agent):
                    key = self._agent_key(session.agent_name, session.project_root)
                    await self._invalidate_agent(key, agent, reason="connection died before queued prompt")
                    return
                try:
                    async with agent.mapping_lock:
                        self._write_session_mapping(agent, session, session_id)
                except Exception as e:
                    logger.error("Session mapping failed for %s: %s", session_id, e)
                    if session_id in self.sessions:
                        self.sessions[session_id].status = "error"
                    if self.db:
                        await self.db.update_session_status(session_id, "error")
                    return
                try:
                    await _execute_prompt()
                finally:
                    async with agent.mapping_lock:
                        self._remove_pid_mappings(
                            agent,
                            agent.pid,
                            session_id=session_id,
                        )

        task = asyncio.create_task(_run_prompt())
        agent.prompt_tasks[session_id] = task

        def _forget_prompt(done_task: asyncio.Task[Any]) -> None:
            if agent.prompt_tasks.get(session_id) is done_task:
                agent.prompt_tasks.pop(session_id, None)

        task.add_done_callback(_forget_prompt)

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

    async def close(self, session_id: str, *, terminal_status: str | None = None) -> dict:
        """Close a session under the canonical per-agent/project lifecycle lock."""
        if terminal_status not in (None, "completed", "error", "cancelled"):
            raise ValueError("terminal_status must be completed, error, or cancelled")
        session = self.sessions.get(session_id)
        if session is None:
            raise ValueError(f"Unknown session: {session_id}")
        key = self._agent_key(session.agent_name, session.project_root)
        async with self._lifecycle_lock(key):
            return await self._close_locked(session_id, session, terminal_status)

    async def _close_locked(
        self, session_id: str, session: SessionInfo, terminal_status: str | None
    ) -> dict:
        """Close a session; caller holds the canonical lifecycle lock."""
        agent = self.agents.get(self._agent_key(session.agent_name, session.project_root))
        prompt_task = agent.prompt_tasks.get(session_id) if agent else None
        prompt_was_active = prompt_task is not None and not prompt_task.done()

        # Closing active work must cancel it and must never manufacture success.
        if prompt_was_active:
            assert agent is not None and prompt_task is not None
            if agent.connection and session.acp_session_id:
                try:
                    await agent.connection.cancel(session.acp_session_id)
                except Exception as exc:
                    logger.warning("Error cancelling ACP session %s: %s", session.acp_session_id, exc)
            prompt_task.cancel()
            await asyncio.gather(prompt_task, return_exceptions=True)

        if agent and agent.connection and session.acp_session_id:
            try:
                await agent.connection.close_session(session.acp_session_id)
            except Exception as exc:
                logger.warning("Error closing ACP session %s: %s", session.acp_session_id, exc)

        # Never overwrite an ACP-reported failure with a successful cleanup.
        if session.status in ("error", "cancelled"):
            final_status = session.status
        elif terminal_status is not None:
            final_status = terminal_status
        elif prompt_was_active:
            final_status = "cancelled"
        elif session.status == "completed":
            final_status = "completed"
        else:
            final_status = "cancelled"
        persistence_error: BaseException | None = None
        try:
            if self.db:
                await self.db.update_session_status(session_id, final_status)
        except BaseException as exc:
            persistence_error = exc

        # PID and in-memory ownership cleanup must run even when persistence fails.
        session.status = final_status
        if agent:
            async with agent.mapping_lock:
                self._remove_pid_mappings(
                    agent,
                    agent.pid,
                    session_id=session_id,
                )
            agent.acp_session_ids.pop(session_id, None)
            agent.prompt_tasks.pop(session_id, None)
        self.sessions.pop(session_id, None)

        if agent and not agent.acp_session_ids:
            agent.status = "idle" if self._agent_is_healthy(agent) else "dead"

        if persistence_error is not None:
            raise persistence_error

        logger.info("Session closed: %s (status=%s)", session_id, final_status)
        return {"status": final_status, "session_id": session_id}

    async def cleanup_persisted(self, session_id: str, *, terminal_status: str, project_id: str) -> dict:
        """Public, project-scoped cleanup boundary for durable runtime bindings."""
        if not isinstance(session_id, str) or not session_id or not isinstance(project_id, str) or not project_id:
            raise ValueError("invalid persisted cleanup authority")
        if terminal_status not in {"completed", "error", "cancelled"}:
            raise ValueError("invalid terminal status")
        session = self.sessions.get(session_id)
        if session is None:
            raise ValueError("unknown persisted session")
        if not isinstance(session.project_root, str) or not session.project_root:
            raise ValueError("session project binding unavailable")
        canonical_root = str(Path(session.project_root).expanduser().resolve())
        expected_project_id = hashlib.sha256(
            ("olympus-project-v1\0" + canonical_root).encode("utf-8")
        ).hexdigest()
        if project_id != expected_project_id:
            raise ValueError("session project binding mismatch")
        acp_session_id = session.acp_session_id or session_id
        key = self._agent_key(session.agent_name, session.project_root)
        agent = self.agents.get(key)
        pid = agent.pid if agent else None
        result = await self.close(session_id, terminal_status=terminal_status)
        agent = self.agents.get(key)
        session_mapping_survives = False
        if agent is not None and pid is not None:
            mapping = agent.profile_path / f".olympus_session.{pid}"
            try:
                session_mapping_survives = mapping.read_text() == session_id
            except OSError:
                session_mapping_survives = False
        return {
            **result,
            "project_id": project_id,
            "acp_session_id": acp_session_id,
            "survivors": {
                "logical_manager_session": session_id in self.sessions,
                "acp_mapping": bool(agent and session_id in agent.acp_session_ids),
                "prompt_task": bool(agent and session_id in agent.prompt_tasks),
                "pid_session_mapping": session_mapping_survives,
            },
        }

    async def cancel(self, session_id: str) -> dict:
        """Force-cancel a stuck session."""
        result = await self.close(session_id, terminal_status="cancelled")
        logger.info("Session cancelled: %s", session_id)
        return result

    # -------------------------------------------------------------------
    # Delegate — open + message + auto-poll until done
    # -------------------------------------------------------------------

    @staticmethod
    def _has_completion_evidence(progress: dict[str, Any]) -> bool:
        """Accept only structurally valid persisted completion evidence."""
        for field_name in ("last_turn", "last_reasoning"):
            value = progress.get(field_name)
            if isinstance(value, str) and value.strip():
                return True
        tool_calls = progress.get("recent_tool_calls")
        return isinstance(tool_calls, list) and any(isinstance(item, dict) and item for item in tool_calls)

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
        empty_completion_polls = 0

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
                # ACP adapters can surface provider failures as end_turn with no
                # assistant turn. Allow one poll for asynchronous hooks to
                # settle, then fail closed instead of reporting empty success.
                if status == "completed" and not self._has_completion_evidence(progress):
                    empty_completion_polls += 1
                    if empty_completion_polls < 2:
                        logger.warning(
                            "[delegate] %s completed without a persisted turn; waiting for hooks",
                            agent_name,
                        )
                        continue
                    status = "error"
                    progress["status"] = status
                    progress["reason"] = "completed_without_response_evidence"
                    session = self.sessions.get(session_id)
                    if session is not None:
                        session.status = status
                    if self.db:
                        await self.db.update_session_status(session_id, status)

                progress["session_id"] = session_id
                progress["timed_out"] = False
                progress["elapsed_seconds"] = round(elapsed, 1)
                progress["poll_iterations"] = poll_iterations

                # Detect CLARIFICATION NEEDED pattern in last response
                last_turn = progress.get("last_turn") or ""
                if status == "completed" and re.search(r"CLARIFICATION\s+NEEDED", last_turn, re.IGNORECASE):
                    progress["status"] = "clarification_needed"
                    progress["clarification_needed"] = True
                    logger.info(
                        "[delegate] %s needs clarification (iterations=%d)",
                        agent_name, poll_iterations,
                    )
                    # Session stays open — Hermes can send follow-up message
                    return progress

                # Normal completion — session stays open for follow-up
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

    async def shutdown_agent(self, name: str, project_root: str | None = None) -> dict:
        """Gracefully shut down a Daimon process.

        If project_root is provided, shut down the specific agent for that project.
        If project_root is None, shut down ALL agents with the given name across
        all projects.
        """
        if project_root is not None:
            # Shut down specific agent for this project
            key = self._agent_key(name, project_root)
            agent = self.agents.get(key)
            if agent is None:
                return {"status": "already_dead", "agent": name}
            agents_to_shutdown = [(key, agent)]
        else:
            # Shut down ALL agents with this name across all projects
            agents_to_shutdown = [
                (k, v) for k, v in self.agents.items() if k[0] == name
            ]
            if not agents_to_shutdown:
                return {"status": "already_dead", "agent": name}

        results = []
        for key, agent in agents_to_shutdown:
            assert agent is not None
            async with self._lifecycle_lock(key):
                # Re-check ownership after waiting: a replacement must not be disposed.
                if self.agents.get(key) is not agent:
                    continue

                # Close all sessions while holding the same lock as spawn.
                for sid in list(agent.acp_session_ids.keys()):
                    try:
                        session = self.sessions.get(sid)
                        if session is not None:
                            await self._close_locked(sid, session, None)
                    except Exception as exc:
                        logger.warning("Error closing session %s during shutdown: %s", sid, exc)

                pid = agent.pid
                agent.status = "dead"
                await self._dispose_agent_transport(agent)
                self._remove_pid_mappings(agent, pid)
                if self.agents.get(key) is agent:
                    self.agents.pop(key, None)
                logger.info("Agent %s (project %s) shut down", name, key[1])
                results.append({"status": "shutdown", "agent": name, "project_root": key[1]})

        # Return single result if only one agent was shut down, otherwise list
        if len(results) == 1:
            return results[0]
        return {"status": "shutdown", "agent": name, "shutdown_count": len(results), "details": results}
