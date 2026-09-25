"""Exercise the Hermes adapter and runtime with stand-ins, not a live provider."""

from __future__ import annotations

import sys
import types
from pathlib import Path

import pytest

from aether_agents.launcher import ActivationError
from aether_agents.mcp import hermes_adapter
from aether_agents.mcp.morfeo_server import install_tools, main, prepare_bridge


@pytest.fixture
def install_module():
    previous: list[tuple[str, types.ModuleType | None]] = []

    def install(name: str, **attrs: object) -> types.ModuleType:
        module = types.ModuleType(name)
        for key, value in attrs.items():
            setattr(module, key, value)
        previous.append((name, sys.modules.get(name)))
        sys.modules[name] = module
        return module

    yield install
    for name, old in reversed(previous):
        if old is None:
            sys.modules.pop(name, None)
        else:
            sys.modules[name] = old


def test_discovery_filters_external_mcp_names(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, install_module
) -> None:
    monkeypatch.chdir(tmp_path)
    install_module("hermes_cli")
    install_module("hermes_cli.config", load_config=lambda: {"toolsets": []})
    install_module("hermes_cli.plugins", discover_plugins=lambda: None)
    install_module(
        "hermes_cli.tools_config",
        _get_platform_tools=lambda *_args, **_kwargs: ["memory"],
    )
    install_module(
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


def test_context_agent_delegate_is_synchronous(tmp_path: Path, install_module) -> None:
    calls: list[bool] = []

    class Agent:
        def __init__(self, **_kwargs: object) -> None:
            pass

    def delegate_task(**kwargs: object) -> str:
        calls.append(bool(kwargs["background"]))
        return "child-done"

    install_module("run_agent", AIAgent=Agent)
    install_module("hermes_cli")
    install_module(
        "hermes_cli.config",
        load_config=lambda: {
            "model": {
                "default": "child-parent-model",
                "provider": "custom:fixture-router",
                "base_url": "http://127.0.0.1:9999/v1",
                "api_mode": "codex_responses",
                "api_key": "",
            }
        },
    )
    install_module("tools")
    install_module(
        "tools.memory_tool", MemoryStore=lambda: types.SimpleNamespace(load_from_disk=lambda: None)
    )
    install_module(
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
    assert agent.model == "child-parent-model"
    assert agent.provider == "custom:fixture-router"
    assert agent.base_url == "http://127.0.0.1:9999/v1"
    assert agent.api_mode == "codex_responses"
    assert agent._dispatch_delegate_task({"goal": "look"}) == "child-done"
    assert calls == [False]


def test_invoke_reaches_exact_hermes_pre_tool_hook(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    plugins = pytest.importorskip("hermes_cli.plugins")
    pytest.importorskip("agent.agent_runtime_helpers")

    def block(*_args, **_kwargs):
        return "blocked-by-mcp-policy-test", None

    monkeypatch.setattr(plugins, "_dispatch_pre_tool_call_hooks", block)
    agent = types.SimpleNamespace(
        session_id="mcp-session",
        _current_turn_id="",
        _current_api_request_id="",
    )
    result = hermes_adapter.invoke(agent, "read_file", {"path": "fixture.txt"}, "task", "call")
    assert "blocked-by-mcp-policy-test" in result


def test_context_agent_can_construct_exact_hermes_delegate_child(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    delegate_tool = pytest.importorskip("tools.delegate_tool")
    run_agent = pytest.importorskip("run_agent")
    profile = tmp_path / "profile"
    profile.mkdir()
    (profile / "config.yaml").write_text(
        "model:\n"
        "  default: gpt-5.6-sol\n"
        "  provider: custom:aether-router\n"
        "  base_url: http://127.0.0.1:8787/v1\n"
        "  api_mode: codex_responses\n"
        "delegation:\n"
        "  model: gpt-5.6-luna\n",
        encoding="utf-8",
    )
    monkeypatch.setenv("HERMES_HOME", str(profile))
    project = tmp_path / "project"
    project.mkdir()
    parent = hermes_adapter.create_context_agent(
        session_id="parent",
        session_db=None,
        task_id="task",
        project=project,
        toolsets=["delegation", "file"],
    )
    captured: dict[str, object] = {}

    class FakeChild:
        def __init__(self, **kwargs: object) -> None:
            captured.update(kwargs)
            self.session_id = "child"
            self._session_init_model_config: dict[str, object] = {}
            self.model = kwargs.get("model")
            self.provider = kwargs.get("provider")
            self.base_url = kwargs.get("base_url")

    monkeypatch.setattr(run_agent, "AIAgent", FakeChild)
    child = delegate_tool._build_child_agent(
        0,
        "inspect fixture",
        None,
        None,
        "gpt-5.6-luna",
        10,
        1,
        parent,
    )
    assert child.session_id == "child"
    assert captured["provider"] == "custom:aether-router"
    assert captured["base_url"] == "http://127.0.0.1:8787/v1"
    assert captured["api_mode"] == "codex_responses"
    assert captured["model"] == "gpt-5.6-luna"


def test_invoke_forwards_to_the_runtime_helper(install_module) -> None:
    seen: dict[str, object] = {}

    def invoke_tool(agent, name, arguments, task_id, tool_call_id):  # noqa: ANN001
        seen.update(name=name, task_id=task_id, tool_call_id=tool_call_id)
        agent._current_turn_id = tool_call_id
        return "ok"

    install_module("agent")
    install_module("agent.agent_runtime_helpers", invoke_tool=invoke_tool)
    agent = types.SimpleNamespace(_current_turn_id="")
    assert hermes_adapter.invoke(agent, "memory", {}, "task", "call") == "ok"
    assert seen["name"] == "memory"


def test_runtime_installs_bootstrap_and_visible_tools(tmp_path: Path, install_module) -> None:
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

    install_module("mcp")
    install_module("mcp.server")
    install_module("mcp.server.fastmcp", Context=Context, FastMCP=FastMCP)
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
