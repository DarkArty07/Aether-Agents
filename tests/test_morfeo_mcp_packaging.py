"""Morfeo MCP stays inside the aether-agents wheel."""

from __future__ import annotations

import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_mcp_is_not_a_core_dependency_and_the_blocked_name_is_absent() -> None:
    project = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))["project"]
    dependencies = " ".join(project.get("dependencies") or [])
    assert "mcp" not in dependencies
    for path in (ROOT / "src").rglob("*"):
        assert "aether_mcp" not in path.name
    assert (ROOT / "src/aether_agents/mcp/morfeo_server.py").is_file()


def test_delegate_spawn_is_synchronous_in_the_adapter() -> None:
    source = (ROOT / "src/aether_agents/mcp/hermes_adapter.py").read_text(encoding="utf-8")
    assert "background=False" in source
    assert "invoke_tool" in source
    from aether_agents.mcp.contracts import mcp_delegate_runs_synchronously

    assert mcp_delegate_runs_synchronously()
