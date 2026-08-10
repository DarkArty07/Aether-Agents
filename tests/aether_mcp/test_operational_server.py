"""Operational M1 MCP facade contract."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from aether_mcp import protocol, server

TOOLS = (
    "project_admit", "project_inspect", "swarm_validate", "swarm_start",
    "swarm_status", "swarm_dispatch", "swarm_message", "swarm_reconcile",
    "swarm_retry", "swarm_cancel", "swarm_close", "swarm_trace",
    "orca_search", "orca_describe", "orca_call",
)


def test_operational_server_registers_only_the_approved_tools_without_bootstrapping(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("AETHER_STATE_ROOT", str(tmp_path / "state"))
    before = set(tmp_path.iterdir())

    operational = server.create_server()

    assert tuple(tool.name for tool in operational._tool_manager.list_tools()) == TOOLS
    assert protocol.CALLABLE_TOOL_NAMES == frozenset(TOOLS)
    assert set(tmp_path.iterdir()) == before


@pytest.mark.anyio
async def test_facade_returns_a_stable_secret_safe_error_envelope(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("AETHER_STATE_ROOT", str(tmp_path / "state"))
    operational = server.create_server()
    request = {"project_id": "SYNTHETIC-SECRET-DO-NOT-ECHO", "unexpected": "SYNTHETIC-SECRET-DO-NOT-ECHO"}

    response = await operational._tool_manager.call_tool("project_inspect", request)

    assert response["ok"] is False
    assert response["error"]["code"] == "INVALID_INPUT"
    assert "SYNTHETIC-SECRET-DO-NOT-ECHO" not in json.dumps(response)


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"
