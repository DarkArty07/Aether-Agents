"""Per-client Morfeo MCP session state. No process-global bootstrap flag."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class MorfeoMcpSession:
    """One MCP connection's Hermes identity and frozen bootstrap snapshot."""

    client_key: str
    mode: str
    project_id: str
    project_root: Path
    bootstrapped: bool = False
    session_id: str | None = None
    task_id: str | None = None
    context_revision: str | None = None
    snapshot: dict[str, Any] | None = None
    agent: Any = None
    child_ids: set[str] = field(default_factory=set)


class SessionTable:
    """Isolated sessions keyed by MCP client identity."""

    def __init__(self) -> None:
        self._sessions: dict[str, MorfeoMcpSession] = {}

    def get(self, client_key: str) -> MorfeoMcpSession | None:
        return self._sessions.get(client_key)

    def put(self, session: MorfeoMcpSession) -> None:
        self._sessions[session.client_key] = session

    def require(self, client_key: str) -> MorfeoMcpSession:
        session = self.get(client_key)
        if session is None:
            raise KeyError(client_key)
        return session

    def drop(self, client_key: str) -> MorfeoMcpSession | None:
        return self._sessions.pop(client_key, None)
