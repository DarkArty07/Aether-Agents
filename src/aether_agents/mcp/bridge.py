"""Generic tool bridge. Every operational call shares this path."""

from __future__ import annotations

import uuid
from typing import Any, Callable

from aether_agents.mcp.contracts import (
    MORFEO_CONTEXT_REQUIRED,
    PROFILE_NAME,
    MorfeoMcpError,
    visible_tool_names,
)
from aether_agents.mcp.session import MorfeoMcpSession, SessionTable

Invoke = Callable[[Any, str, dict[str, Any], str, str], str]


class ToolBridge:
    """Bootstrap gate plus one invoke path for the discovered Morfeo surface."""

    def __init__(
        self,
        *,
        sessions: SessionTable,
        definitions: list[dict[str, Any]],
        mode: str,
        invoke: Invoke,
        on_bootstrap: Callable[[MorfeoMcpSession], dict[str, Any]],
        on_close: Callable[[MorfeoMcpSession], None] | None = None,
    ) -> None:
        self.sessions = sessions
        self.mode = mode
        self._invoke = invoke
        self._on_bootstrap = on_bootstrap
        self._on_close = on_close
        names = set()
        self.definitions: list[dict[str, Any]] = []
        for item in definitions:
            function = item.get("function") or {}
            name = function.get("name")
            if isinstance(name, str):
                names.add(name)
                self.definitions.append(item)
        self.visible = visible_tool_names(names, mode)

    def published(self) -> list[dict[str, Any]]:
        selected = []
        for item in self.definitions:
            name = item["function"]["name"]
            if name in self.visible:
                selected.append(item)
        return selected

    def ensure(self, client_key: str, *, project_id: str, project_root: Any) -> MorfeoMcpSession:
        current = self.sessions.get(client_key)
        if current is not None:
            return current
        session = MorfeoMcpSession(
            client_key=client_key,
            mode=self.mode,
            project_id=project_id,
            project_root=project_root,
        )
        self.sessions.put(session)
        return session

    def bootstrap(self, session: MorfeoMcpSession) -> dict[str, Any]:
        if session.bootstrapped and session.snapshot is not None:
            return session.snapshot
        snapshot = self._on_bootstrap(session)
        session.snapshot = snapshot
        session.context_revision = str(snapshot.get("context_revision"))
        session.bootstrapped = True
        return snapshot

    def call(self, session: MorfeoMcpSession, name: str, arguments: dict[str, Any]) -> str:
        if name != "morfeo_bootstrap" and not session.bootstrapped:
            raise MorfeoMcpError(MORFEO_CONTEXT_REQUIRED, MORFEO_CONTEXT_REQUIRED)
        if name not in self.visible and name != "morfeo_bootstrap":
            raise MorfeoMcpError("MORFEO_TOOL_UNAVAILABLE", f"{name} is not on this surface")
        if session.task_id is None:
            raise MorfeoMcpError(MORFEO_CONTEXT_REQUIRED, MORFEO_CONTEXT_REQUIRED)
        tool_call_id = uuid.uuid4().hex
        return self._invoke(session.agent, name, arguments, session.task_id, tool_call_id)

    def close(self, client_key: str) -> None:
        session = self.sessions.drop(client_key)
        if session is not None and self._on_close is not None:
            self._on_close(session)


def bootstrap_payload(snapshot: dict[str, Any]) -> dict[str, Any]:
    """Public bootstrap body. Role stays Morfeo; the host model is not renamed."""

    return {
        "role": PROFILE_NAME,
        "mode": snapshot.get("mode"),
        "project_id": snapshot.get("project_id"),
        "project_root": snapshot.get("project_root"),
        "context_revision": snapshot.get("context_revision"),
        "sections": snapshot.get("sections"),
        "tools": snapshot.get("tools"),
    }
