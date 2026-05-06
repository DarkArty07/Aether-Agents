"""Olympus v2 Pi Adapter — subprocess manager for Pi Agent JSONL RPC communication.

Manages the lifecycle of Pi Agent processes running in --mode rpc:
- Spawning processes with configured arguments
- Sending JSONL commands via stdin
- Reading JSONL events from stdout (non-blocking, thread-based)
- Aborting and terminating sessions
- Proper subprocess cleanup (no zombies, no leaked file descriptors)

The JSONL RPC protocol for Pi Agent:
- Input (stdin): {"type": "prompt", "message": "...", "id": "..."} or {"type": "abort"}
- Output (stdout): {"type": "agent_start|message_update|message_end|agent_end|response", ...}
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import subprocess
import threading
import time
import tempfile
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .config_loader import PiDaimonConfig, get_config

logger = logging.getLogger("olympus_v2.pi_adapter")


def _load_dotenv(env_dict: dict[str, str]) -> dict[str, str]:
    """Load AETHER_HOME/.env into env_dict if it exists.
    
    Hermes resolves ${VAR} in config.yaml internally, but the MCP server
    process doesn't have these vars in os.environ. Pi Agent's extension
    needs OPENCODE_GO_API_KEY in the environment to register the provider.
    """
    aether_home = env_dict.get("AETHER_HOME") or os.environ.get("AETHER_HOME", "")
    if not aether_home:
        # Fallback: derive from this file's location
        aether_home = str(Path(__file__).resolve().parent.parent.parent.parent / "home")
    
    dotenv_path = Path(aether_home) / ".env"
    if not dotenv_path.exists():
        logger.debug(f"[pi_adapter] No .env found at {dotenv_path}")
        return env_dict
    
    loaded = 0
    with open(dotenv_path) as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "=" in line:
                key, _, value = line.partition("=")
                key = key.strip()
                value = value.strip()
                # Remove surrounding quotes if present
                if value.startswith('"') and value.endswith('"'):
                    value = value[1:-1]
                elif value.startswith("'") and value.endswith("'"):
                    value = value[1:-1]
                # Don't override existing env vars
                if key not in env_dict:
                    env_dict[key] = value
                    loaded += 1
    
    logger.info(f"[pi_adapter] Loaded {loaded} vars from {dotenv_path}")
    return env_dict




@dataclass
class PiSession:
    """Tracks a single Pi Agent RPC subprocess session."""

    session_id: str
    agent_name: str
    process: subprocess.Popen
    config: PiDaimonConfig
    created_at: float = field(default_factory=time.time)
    # Thread-safe buffer for stdout events
    events: list[dict[str, Any]] = field(default_factory=list)
    events_lock: threading.Lock = field(default_factory=threading.Lock)
    # Reader thread
    reader_thread: threading.Thread | None = None
    reader_stop: threading.Event = field(default_factory=threading.Event)
    # Accumulated text for this session
    accumulated_text: str = ""
    accumulated_reasoning: str = ""
    thoughts_count: int = 0
    tool_calls_count: int = 0
    # Session directory (for --session-dir cleanup)
    session_dir: str | None = None
    # Status tracking
    is_done: bool = False
    final_response: str = ""


class PiAdapter:
    """Manages Pi Agent RPC subprocesses.

    This is the core adapter that bridges Olympus v2 with Pi Agent processes.
    It handles spawning, communication, and lifecycle management.
    """

    def __init__(self) -> None:
        self.sessions: dict[str, PiSession] = {}
        self._lock = asyncio.Lock()

    def spawn_agent(self, agent_config: PiDaimonConfig) -> PiSession:
        """Spawn a Pi Agent process in RPC mode with persistent sessions.

        Uses --session-dir instead of --no-session so Pi stays alive for
        multi-turn conversations and tool execution.

        Args:
            agent_config: Configuration for the agent to spawn.

        Returns:
            A PiSession object tracking the subprocess.

        Raises:
            RuntimeError: If the process fails to start.
        """
        session_id = f"pi_{agent_config.name}_{uuid.uuid4().hex[:8]}"

        # Create a session directory for Pi to persist state
        # This keeps Pi alive between prompts (no --no-session ephemeral mode)
        session_dir = tempfile.mkdtemp(prefix=f"pi_session_{agent_config.name}_")
        spawn_args = agent_config.build_spawn_args(session_dir=session_dir)

        logger.info(f"[pi_adapter] Spawning Pi Agent: {' '.join(spawn_args)}")

        # Set up environment — inherit current env, then load .env for API keys
        # Hermes resolves ${VAR} in config.yaml internally, but the MCP server
        # subprocess doesn't have these vars. _load_dotenv loads AETHER_HOME/.env.
        env = _load_dotenv(os.environ.copy())
        # Pi Agent reads API keys from environment or auth.json
        # The extension will use OPENCODE_GO_API_KEY from env

        try:
            process = subprocess.Popen(
                spawn_args,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                env=env,
                # Use the project root or configured cwd as working directory
                cwd=str(agent_config.cwd) if agent_config.cwd else None,
            )
        except Exception as e:
            logger.error(f"[pi_adapter] Failed to spawn Pi Agent: {e}")
            raise RuntimeError(f"Failed to spawn Pi Agent for {agent_config.name}: {e}")

        session = PiSession(
            session_id=session_id,
            agent_name=agent_config.name,
            process=process,
            config=agent_config,
            session_dir=session_dir,
        )

        # Start the stdout reader thread
        session.reader_thread = threading.Thread(
            target=self._stdout_reader,
            args=(session,),
            daemon=True,
            name=f"pi-reader-{session_id}",
        )
        session.reader_thread.start()

        # Start the stderr reader thread for debugging
        stderr_thread = threading.Thread(
            target=self._stderr_reader,
            args=(session,),
            daemon=True,
            name=f"pi-stderr-{session_id}",
        )
        stderr_thread.start()

        self.sessions[session_id] = session
        logger.info(
            f"[pi_adapter] Spawned {agent_config.name} as session {session_id} "
            f"(PID={process.pid})"
        )
        return session

    def send_command(self, session_id: str, command: dict[str, Any]) -> None:
        """Send a JSONL command to the Pi Agent process stdin.

        Args:
            session_id: The session to send the command to.
            command: Dict to serialize as JSON and send.

        Raises:
            KeyError: If session_id is not found.
            RuntimeError: If the process is not running or stdin is closed.
        """
        session = self.sessions.get(session_id)
        if session is None:
            raise KeyError(f"Unknown session: {session_id}")

        if session.process.poll() is not None:
            raise RuntimeError(
                f"Pi process for session {session_id} has exited "
                f"(returncode={session.process.returncode})"
            )

        if session.process.stdin is None:
            raise RuntimeError(f"Session {session_id} stdin is not available")

        command_line = json.dumps(command) + "\n"
        try:
            session.process.stdin.write(command_line.encode("utf-8"))
            session.process.stdin.flush()
            logger.debug(f"[pi_adapter] Sent to {session_id}: {command}")
        except BrokenPipeError:
            logger.error(f"[pi_adapter] Broken pipe writing to {session_id}")
            # Read stderr to get error details
            stderr_output = ""
            if session.process.stderr:
                try:
                    stderr_output = session.process.stderr.read(4096).decode("utf-8", errors="replace")
                except Exception:
                    pass
            raise RuntimeError(
                f"Broken pipe sending to session {session_id}. "
                f"Process may have crashed. stderr: {stderr_output[:500]}"
            )

    def send_get_state(self, session_id: str) -> dict[str, Any] | None:
        """Send get_state command and read the response.
        
        Returns the state dict if successful, None on error.
        Used before sending multi-turn prompts to verify Pi is ready.
        """
        session = self.sessions.get(session_id)
        if session is None:
            raise KeyError(f"Unknown session: {session_id}")

        if session.process.poll() is not None:
            return None

        # Send get_state command
        self.send_command(session_id, {"type": "get_state"})
        
        # Wait briefly for response
        time.sleep(0.2)
        
        # Read events to find the response
        events = self.read_events(session_id)
        for event in events:
            if event.get("type") == "response" and event.get("command") == "get_state":
                result = event.get("result", {})
                if result.get("success", False):
                    return result.get("state", {})
        
        return None

    def read_events(self, session_id: str) -> list[dict[str, Any]]:
        """Read and drain all accumulated events from the session's stdout buffer.

        This is non-blocking — it returns events that have been received since
        the last call. Events are buffered by the reader thread.

        Args:
            session_id: The session to read events from.

        Returns:
            List of event dicts (may be empty if no new events).
        """
        session = self.sessions.get(session_id)
        if session is None:
            return []

        with session.events_lock:
            events = session.events.copy()
            session.events.clear()

        return events

    def abort(self, session_id: str) -> None:
        """Send an abort command to the Pi Agent process.

        Args:
            session_id: The session to abort.
        """
        try:
            self.send_command(session_id, {"type": "abort"})
            logger.info(f"[pi_adapter] Sent abort to session {session_id}")
        except (KeyError, RuntimeError) as e:
            logger.warning(f"[pi_adapter] Could not abort session {session_id}: {e}")

    def terminate(self, session_id: str, timeout: float = 5.0) -> None:
        """Terminate a Pi Agent process and clean up.

        Args:
            session_id: The session to terminate.
            timeout: Seconds to wait for graceful termination before killing.
        """
        session = self.sessions.pop(session_id, None)
        if session is None:
            logger.warning(f"[pi_adapter] Session {session_id} not found for termination")
            return

        # Stop the reader thread
        session.reader_stop.set()

        # Close stdin to signal the process
        if session.process.stdin:
            try:
                session.process.stdin.close()
            except Exception:
                pass

        # Wait for the process to exit
        try:
            session.process.wait(timeout=timeout)
        except subprocess.TimeoutExpired:
            logger.warning(
                f"[pi_adapter] Pi process for {session_id} did not exit "
                f"within {timeout}s, killing"
            )
            session.process.kill()
            try:
                session.process.wait(timeout=2.0)
            except subprocess.TimeoutExpired:
                pass

        # Wait for the reader thread to finish
        if session.reader_thread and session.reader_thread.is_alive():
            session.reader_thread.join(timeout=2.0)

        logger.info(
            f"[pi_adapter] Terminated session {session_id} "
            f"(exit_code={session.process.returncode})"
        )

    def terminate_all(self) -> None:
        """Terminate all active Pi Agent sessions. Called on server shutdown."""
        session_ids = list(self.sessions.keys())
        for sid in session_ids:
            self.terminate(sid)
        logger.info(f"[pi_adapter] Terminated all {len(session_ids)} sessions")

    def _stderr_reader(self, session: PiSession) -> None:
        """Background thread that reads stderr from Pi Agent for debugging.

        Logs stderr output at WARNING level so crash messages are visible.
        """
        process = session.process
        if process.stderr is None:
            return

        try:
            while not session.reader_stop.is_set():
                line = process.stderr.readline()
                if not line:
                    break
                line = line.strip().decode("utf-8", errors="replace")
                if line:
                    logger.warning(
                        f"[pi_adapter] stderr({session.session_id}): {line}"
                    )
        except Exception as e:
            if not session.reader_stop.is_set():
                logger.error(
                    f"[pi_adapter] Error reading stderr for {session.session_id}: {e}"
                )

    def _stdout_reader(self, session: PiSession) -> None:
        """Background thread that reads JSONL lines from Pi Agent's stdout.

        Parses each line as JSON and appends to the session's event buffer.
        Stops when the reader_stop event is set or when stdout reaches EOF.
        """
        process = session.process
        if process.stdout is None:
            logger.error(f"[pi_adapter] No stdout for session {session.session_id}")
            return

        try:
            while not session.reader_stop.is_set():
                line = process.stdout.readline()
                if not line:
                    # EOF — process has exited
                    logger.debug(
                        f"[pi_adapter] Stdout EOF for session {session.session_id}"
                    )
                    break

                line = line.strip()
                if not line:
                    continue

                try:
                    event = json.loads(line)
                except json.JSONDecodeError:
                    # Not JSON — might be a status line from Pi. Log and skip.
                    logger.debug(
                        f"[pi_adapter] Non-JSON from {session.session_id}: "
                        f"{line[:200]}"
                    )
                    continue

                with session.events_lock:
                    session.events.append(event)

                logger.debug(
                    f"[pi_adapter] Event from {session.session_id}: "
                    f"type={event.get('type', 'unknown')}"
                )

        except Exception as e:
            if not session.reader_stop.is_set():
                logger.error(
                    f"[pi_adapter] Error reading from {session.session_id}: {e}"
                )
        finally:
            logger.debug(
                f"[pi_adapter] Reader thread exiting for {session.session_id}"
            )

    def get_session(self, session_id: str) -> PiSession | None:
        """Return the session object, or None if not found."""
        return self.sessions.get(session_id)

    def is_process_alive(self, session_id: str) -> bool:
        """Check if the Pi process for a session is still running."""
        session = self.sessions.get(session_id)
        if session is None:
            return False
        return session.process.poll() is None