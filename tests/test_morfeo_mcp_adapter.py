"""Exercise the Hermes adapter and runtime with stand-ins, not a live provider."""

from __future__ import annotations

import sys
import types
from pathlib import Path

import pytest

from aether_agents.launcher import ActivationError
from aether_agents.mcp import hermes_adapter
from aether_agents.mcp.morfeo_server import install_tools, main, prepare_bridge


def _module(name: str, **attrs: object) -> types.ModuleType:
    module = types.ModuleType(name)
    for key, value in attrs.items():
        setattr(module, key, value)
    sys.modules[name] = module
    return module


def test_discovery_filters_external_mcp_names(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)
    _module("hermes_cli")
    _module("hermes_cli.config", load_config=lambda: {"toolsets": []})
    _module("hermes_cli.plugins", discover_plugins=lambda: None)
    _module(
        "hermes_cli.tools_config",
        _get_platform_tools=lambda *_args, **_kwargs: ["memory"],
    )
    _module(
        "model_tools",
        get_tool_definitions=lambda **_kwargs: [
            {"type": "function", "function": {"name": "memory", "parameters": {}}},
            {"type": "function", "function": {"name": "mcp__context7__resolve", "parameters": {}}},
            {"type": "not-a-tool"},
        ],
    )
    definitions, toolsets = hermes_adapter.discover_effective_tools(tmp_path)
    assert toolsets == ["memory"]
    assert [item["function"]["name"] for item in definitions] == ["memory"]


def test_context_agent_delegate_is_synchronous(tmp_path: Path) -> None:
    calls: list[bool] = []

    class Agent:
        def __init__(self, **_kwargs: object) -> None:
            pass

    def delegate_task(**kwargs: object) -> str:
        calls.append(bool(kwargs["background"]))
        return "child-done"

    _module("run_agent", AIAgent=Agent)
    _module("tools")
    _module(
        "tools.memory_tool", MemoryStore=lambda: types.SimpleNamespace(load_from_disk=lambda: None)
    )
    _module(
        "tools.delegate_tool",
        delegate_task=delegate_task,
        _strip_model_hidden_task_fields=lambda tasks: tasks,
    )
    agent = hermes_adapter.create_context_agent(
        session_id="s",
        session_db=object(),
        task_id="t",
        project=tmp_path,
        toolsets=["memory"],
    )
    assert agent._get_session_db_for_recall() is agent.session_db
    assert agent._dispatch_delegate_task({"goal": "look"}) == "child-done"
    assert calls == [False]


def test_invoke_forwards_to_the_runtime_helper() -> None:
    seen: dict[str, object] = {}

    def invoke_tool(agent, name, arguments, task_id, tool_call_id):  # noqa: ANN001
        seen.update(name=name, task_id=task_id, tool_call_id=tool_call_id)
        agent._current_turn_id = tool_call_id
        return "ok"

    _module("agent")
    _module("agent.agent_runtime_helpers", invoke_tool=invoke_tool)
    agent = types.SimpleNamespace(_current_turn_id="")
    assert hermes_adapter.invoke(agent, "memory", {}, "task", "call") == "ok"
    assert seen["name"] == "memory"


def test_runtime_installs_bootstrap_and_visible_tools(tmp_path: Path) -> None:
    class Context:
        session = object()

    class FastMCP:
        def __init__(self) -> None:
            self.tools: list[str] = []

        def tool(self, **kwargs: object):
            def decorate(fn):
                self.tools.append(str(kwargs["name"]))
                return fn

            return decorate

    _module("mcp")
    _module("mcp.server")
    _module("mcp.server.fastmcp", Context=Context, FastMCP=FastMCP)
    bridge = types.SimpleNamespace(
        published=lambda: [
            {"function": {"name": "memory", "description": "mem", "parameters": {"properties": {}}}}
        ],
        ensure=lambda *_args, **_kwargs: None,
        call=lambda *_args, **_kwargs: "ok",
        bootstrap=lambda _session: {"role": "morfeo"},
    )
    server = FastMCP()
    install_tools(server, bridge, "project", tmp_path)
    assert "morfeo_bootstrap" in server.tools
    assert "memory" in server.tools


def test_serve_refuses_a_missing_runtime_python(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        "aether_agents.commands.mcp._resolve_project",
        lambda _project: (tmp_path, "12027989-a08f-41cd-a82c-54ff1bfb6b03"),
    )
    monkeypatch.setattr(
        "aether_agents.commands.mcp._resolve_component_paths",
        lambda _repo: (tmp_path, tmp_path / "hermes", tmp_path),
    )
    monkeypatch.setattr(
        "aether_agents.commands.mcp._resolve_target_python",
        lambda *_args: tmp_path / "missing-python",
    )
    monkeypatch.setattr(
        "aether_agents.commands.mcp._resolve_target_source_root",
        lambda *_args: None,
    )
    import argparse

    from aether_agents.commands.mcp import run_mcp

    code = run_mcp(
        argparse.Namespace(
            mcp_command="morfeo",
            morfeo_command="serve",
            host="127.0.0.1",
            mode="harness",
            transport=None,
            project=str(tmp_path),
            port=1,
        )
    )
    assert code == 2


def test_prepare_bridge_is_not_called_for_public_host(tmp_path: Path) -> None:
    assert (
        main(
            [
                "--mode",
                "harness",
                "--transport",
                "stdio",
                "--project",
                str(tmp_path),
                "--project-id",
                "12027989-a08f-41cd-a82c-54ff1bfb6b03",
                "--profile",
                str(tmp_path),
                "--host",
                "0.0.0.0",
            ]
        )
        == 2
    )
    assert prepare_bridge.__name__ == "prepare_bridge"
    assert ActivationError is not None
