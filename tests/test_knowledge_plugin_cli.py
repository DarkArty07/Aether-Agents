"""Exact native plugin registration and identity-safe CLI/tool dispatch."""

from __future__ import annotations

import json
import os
import sqlite3
from pathlib import Path

import pytest
from test_project_knowledge_engine import OTHER, PROJECT, project

from aether_agents.cli import _build_parser
from aether_agents.commands.knowledge import run_knowledge
from aether_agents.knowledge.bindings import bind_session, context_for_session
from aether_agents.knowledge.common import KnowledgeError, atomic_json
from aether_agents.knowledge.component import configure, disable
from aether_agents.knowledge.context import resolve_context
from aether_agents.knowledge.service import KnowledgeService, parameters, validate_arguments


def test_identical_tool_schema_rejects_identity_injection() -> None:
    memory_schema = parameters("work_memory")
    assert "role" not in memory_schema["properties"]
    assert "idempotency_key" in memory_schema["properties"]
    with pytest.raises(KnowledgeError):
        validate_arguments(
            "work_memory",
            {
                "action": "save",
                "situation": "missing operation identity",
                "lesson": "retry safety is required",
                "applicability": "every save",
                "outcome": "useful",
                "evidence": [],
            },
        )
    for key in ("role", "project_id", "graph_path", "memory_dir", "project_path", "python"):
        with pytest.raises(KnowledgeError):
            validate_arguments("project_knowledge", {"action": "status", key: "injected"})
    with pytest.raises(KnowledgeError):
        validate_arguments("work_memory", {"action": "correct", "note_id": "wn_" + "1" * 32})


@pytest.mark.skipif(os.name != "posix", reason="POSIX subprocess timeout fixture")
@pytest.mark.parametrize("action", ["save", "reflect"])
def test_memory_honors_configured_timeout_before_publishing(tmp_path: Path, action: str) -> None:
    _root, state = project(tmp_path)
    component = tmp_path / "delayed-component"
    component.write_text(
        '#!/bin/sh\nsleep 2\nprintf \'%s\' \'{"ok":true,"content":"delayed test fixture","count":0}\'\n'
    )
    component.chmod(0o700)
    service = KnowledgeService(state, tmp_path / "cache")
    atomic_json(
        service.config_path,
        {
            "schema_version": 1,
            "enabled": True,
            "python": str(component),
            "timeout_seconds": 1,
        },
    )
    ctx = resolve_context(PROJECT, "morfeo", state_root=state)
    args = {"action": action}
    if action == "save":
        args.update(
            {
                "idempotency_key": "configured-timeout",
                "situation": "Slow test component",
                "lesson": "Keep the configured limit",
                "applicability": "Subprocess writes",
                "outcome": "useful",
                "evidence": [],
            }
        )
    with pytest.raises(KnowledgeError) as failure:
        service.execute(ctx, "work_memory", args)
    assert failure.value.code == "TIMEOUT"
    assert not list(state.rglob("record.json"))
    assert not list(state.rglob("reflection.json"))


def test_operator_binding_conflicts_with_native_session(tmp_path: Path) -> None:
    first, state = project(tmp_path)
    second, _ = project(tmp_path, OTHER, "beta")
    bind_session(state, PROJECT, "morfeo", "s1", root=first)
    assert context_for_session(state, "morfeo", "s1").root == first
    home = tmp_path / "hermes"
    home.mkdir()
    with sqlite3.connect(home / "state.db") as connection:
        connection.execute("CREATE TABLE sessions (id TEXT PRIMARY KEY, cwd TEXT)")
        connection.execute("INSERT INTO sessions VALUES (?, ?)", ("s1", str(second)))
    with pytest.raises(KnowledgeError) as conflict:
        context_for_session(state, "morfeo", "s1", hermes_home=home)
    assert conflict.value.code == "PROJECT_CONFLICT"
    with pytest.raises(KnowledgeError):
        context_for_session(state, "supervisor", "s1")


def test_native_workspace_binding_tracks_exact_session_not_last(tmp_path: Path) -> None:
    first, state = project(tmp_path)
    second, _ = project(tmp_path, OTHER, "beta")
    home = tmp_path / "hermes"
    home.mkdir()
    with sqlite3.connect(home / "state.db") as connection:
        connection.execute("CREATE TABLE sessions (id TEXT PRIMARY KEY, cwd TEXT)")
        connection.executemany(
            "INSERT INTO sessions VALUES (?, ?)", [("s1", str(first)), ("s2", str(second))]
        )
    for _ in range(3):
        assert context_for_session(state, "morfeo", "s2", hermes_home=home).project_id == OTHER
        assert context_for_session(state, "morfeo", "s1", hermes_home=home).project_id == PROJECT
    with pytest.raises(KnowledgeError):
        context_for_session(state, "morfeo", "unknown", hermes_home=home)


def test_disabled_register_has_no_tools_or_imports() -> None:
    from aether_agents.knowledge.hermes_plugin import register

    class Context:
        profile_name = "morfeo"

        def get_config(self, key, default=None):
            return default

        def register_tool(self, **_kwargs):
            raise AssertionError("A disabled plugin must not register tools")

    register(Context())


@pytest.mark.parametrize("role", ["morfeo", "supervisor", "implementer"])
def test_native_hermes_register_dispatch_unload(role, tmp_path: Path, monkeypatch) -> None:
    pytest.importorskip("hermes_cli.plugins")
    root, state = project(tmp_path)
    home = tmp_path / "profiles" / role
    home.mkdir(parents=True)
    import yaml

    (home / "config.yaml").write_text(
        yaml.safe_dump(
            {
                "plugins": {
                    "entries": {
                        "aether-project-knowledge": {
                            "settings": {
                                "enabled": True,
                                "state_root": str(state),
                                "cache_root": str(tmp_path / "cache"),
                            }
                        }
                    }
                }
            }
        )
    )
    with sqlite3.connect(home / "state.db") as connection:
        connection.execute("CREATE TABLE sessions (id TEXT PRIMARY KEY, cwd TEXT)")
        connection.execute("INSERT INTO sessions VALUES (?, ?)", ("native-session", str(root)))
    monkeypatch.setenv("HERMES_HOME", str(home))
    from hermes_cli.plugins import PluginContext, PluginManager, PluginManifest
    from tools.registry import registry

    from aether_agents.knowledge.hermes_plugin import register

    manager = PluginManager(scope_key=str(home))
    manifest = PluginManifest(
        name="aether-project-knowledge", key="aether-project-knowledge", source="entrypoint"
    )
    context = PluginContext(manifest, manager)
    assert context.profile_name == role
    register(context)
    for tool in ("project_knowledge", "work_memory"):
        entry = registry.get_entry(tool, scope=manager.scope_key)
        assert entry is not None
        assert entry.schema["parameters"] == parameters(tool)
    entry = registry.get_entry("project_knowledge", scope=manager.scope_key)
    result = json.loads(entry.handler({"action": "status"}, session_id="native-session"))
    assert result["ok"] and result["project_id"] == PROJECT
    assert not result["available"]
    forged = json.loads(
        entry.handler({"action": "status", "project_id": OTHER}, session_id="native-session")
    )
    assert not forged["ok"] and forged["error"]["code"] == "ARGUMENT_INVALID"
    assert manager.unload(manifest)
    assert registry.get_entry("project_knowledge", scope=manager.scope_key) is None
    assert registry.get_entry("work_memory", scope=manager.scope_key) is None


def test_cli_real_component_configure_update_query_and_disable(tmp_path: Path, capsys) -> None:
    raw = os.environ.get("AETHER_GRAPHIFY_PYTHON")
    if not raw:
        pytest.skip("Native Graphify fixture required")
    _root, state = project(tmp_path)
    service = KnowledgeService(state, tmp_path / "cache")
    configure(service, Path(raw))
    parser = _build_parser()
    for operation in (["update"], ["query", "--question", "process_order"]):
        args = parser.parse_args(["knowledge", *operation, "--project-id", PROJECT, "--json"])
        assert run_knowledge(args, service) == 0
        result = json.loads(capsys.readouterr().out)
        assert result["ok"]
        if operation[0] == "query":
            assert "process_order" in result["content"]
    disable(service)
    ctx = resolve_context(PROJECT, "morfeo", state_root=state)
    assert service.execute(ctx, "project_knowledge", {"action": "status"})["available"]
    with pytest.raises(KnowledgeError):
        service.execute(ctx, "project_knowledge", {"action": "query", "question": "anything"})


def test_corrupt_configuration_is_not_treated_as_enabled(tmp_path: Path) -> None:
    service = KnowledgeService(tmp_path / "state", tmp_path / "cache")
    atomic_json(service.config_path, {"schema_version": 999, "enabled": True})
    with pytest.raises(KnowledgeError):
        service.configuration()
