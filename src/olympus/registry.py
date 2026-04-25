"""Olympus registry — in-memory session and agent state tracking."""

from __future__ import annotations

import asyncio
import logging
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from .config import DaimonProfile

logger = logging.getLogger("olympus.registry")


class AgentStatus(str, Enum):
    """Status of a Daimon process."""
    IDLE = "idle"        # Process alive, no active session
    BUSY = "busy"        # Process alive, active session
    DEAD = "dead"        # Process not running
    SPAWNING = "spawning"  # Process being started


class SessionStatus(str, Enum):
    """Status of an ACP session."""
    ACTIVE = "active"      # Session open, agent working
    DONE = "done"          # Session completed, response available
    ERROR = "error"        # Session errored out
    CANCELLED = "cancelled"  # Session was cancelled
    CLOSED = "closed"      # Session explicitly closed


@dataclass
class SessionState:
    """Tracks the state of a single ACP session."""
    session_id: str
    agent_name: str
    status: SessionStatus = SessionStatus.ACTIVE
    created_at: float = field(default_factory=time.time)
    last_updated: float = field(default_factory=time.time)

    # Streaming state captured from session_updates
    thoughts: list[str] = field(default_factory=list)
    messages: list[str] = field(default_factory=list)
    tool_calls: list[dict] = field(default_factory=list)

    # Final response when session completes
    final_response: str | None = None
    stop_reason: str | None = None

    # ACP connection object (not serialized)
    acp_connection: Any = None

    # Event to signal completion
    completion_event: asyncio.Event = field(default_factory=asyncio.Event)

    def update_from_thought(self, text: str) -> None:
        self.thoughts.append(text)
        self.last_updated = time.time()

    def update_from_message(self, text: str) -> None:
        self.messages.append(text)
        self.last_updated = time.time()

    def update_from_tool_call(self, call_info: dict) -> None:
        self.tool_calls.append(call_info)
        self.last_updated = time.time()

    def mark_done(self, response: str, stop_reason: str = "end_turn") -> None:
        self.status = SessionStatus.DONE
        self.final_response = response
        self.stop_reason = stop_reason
        self.last_updated = time.time()

        # Diagnostic: detect empty response scenarios
        # The ACP protocol sends response text via AgentMessageChunk streaming.
        # If messages is empty but the agent completed, something went wrong
        # in the streaming collection — likely a race condition or a provider
        # that streams via AgentThoughtChunk instead of AgentMessageChunk.
        if not response and not self.messages:
            logger.warning(
                f"Session {self.session_id} completed with empty response "
                f"(messages={len(self.messages)}, thoughts={len(self.thoughts)}, "
                f"stop_reason={stop_reason})"
            )

        self.completion_event.set()

    def mark_error(self, error: str) -> None:
        self.status = SessionStatus.ERROR
        self.final_response = error
        self.stop_reason = "error"
        self.last_updated = time.time()
        self.completion_event.set()

    def mark_cancelled(self) -> None:
        self.status = SessionStatus.CANCELLED
        self.stop_reason = "cancelled"
        self.last_updated = time.time()
        self.completion_event.set()


@dataclass
class AgentState:
    """Tracks the state of a live Daimon process."""
    name: str
    profile: DaimonProfile
    status: AgentStatus = AgentStatus.DEAD
    pid: int | None = None
    process: Any = None  # subprocess.Process
    connection: Any = None  # ACP ClientSideConnection

    # Active sessions on this agent
    sessions: dict[str, SessionState] = field(default_factory=dict)

    # Session counter for generating Olympus-side IDs
    _session_counter: int = 0

    def next_session_id(self) -> str:
        self._session_counter += 1
        return f"olympus_{self.name}_{self._session_counter}"


class OlympusRegistry:
    """In-memory registry for all agents and sessions managed by Olympus."""

    def __init__(self) -> None:
        self.agents: dict[str, AgentState] = {}

    def register_discovery(self, profiles: dict[str, DaimonProfile]) -> None:
        """Register discovered agent profiles."""
        for name, profile in profiles.items():
            if name not in self.agents:
                self.agents[name] = AgentState(name=name, profile=profile)

    def get_agent(self, name: str) -> AgentState | None:
        """Get agent state by name."""
        return self.agents.get(name)

    def get_session(self, session_id: str) -> SessionState | None:
        """Find a session by ID across all agents."""
        for agent in self.agents.values():
            if session_id in agent.sessions:
                return agent.sessions[session_id]
        return None

    def list_agents(self) -> list[dict]:
        """List all discovered agents with their status."""
        result = []
        for name, state in self.agents.items():
            result.append({
                "name": name,
                "role": state.profile.role,
                "description": state.profile.description,
                "capabilities": state.profile.capabilities,
                "keep_alive": state.profile.keep_alive,
                "status": state.status.value,
                "pid": state.pid,
                "active_sessions": len([
                    s for s in state.sessions.values()
                    if s.status == SessionStatus.ACTIVE
                ]),
            })
        return result