from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path
from typing import Any

import pytest
from observation_helpers import PROJECT_ID, TRACE_ID, complete_trace

from aether_agents.observation import brief, query
from aether_agents.observation.capture.journal import JournalWriter
from aether_agents.observation.context import ProjectRegistry
from aether_agents.observation.contracts import canonical_json_bytes
from aether_agents.observation.identity import summary_id as make_summary_id
from aether_agents.paths import ObservationPaths


def _project(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> tuple[Path, ObservationPaths]:
    monkeypatch.setenv("XDG_STATE_HOME", str(tmp_path / "state"))
    project = tmp_path / "project"
    marker = project / ".aether" / "project.toml"
    marker.parent.mkdir(parents=True)
    marker.write_text(f'project_id = "{PROJECT_ID}"\n', encoding="utf-8")
    assert ProjectRegistry().register(PROJECT_ID, project, "brief")
    return project, ObservationPaths.for_project(PROJECT_ID)


def _journal(paths: ObservationPaths) -> None:
    fixture = complete_trace()
    writer = JournalWriter(paths=paths, producer_epoch=fixture.epoch)
    writer.open()
    try:
        for event in fixture.events:
            assert writer.append(event).accepted
    finally:
        writer.close()


def test_status_is_curated_bounded_and_contains_no_raw_payload(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    project, paths = _project(monkeypatch, tmp_path)
    _journal(paths)
    value = brief.observe(
        {"action": "status", "project": str(project), "ref": TRACE_ID},
        profile_name="morfeo",
    )
    assert value["schema_version"] == brief.SCHEMA_VERSION
    assert value["state"] == "ready"
    summary = query.load_summary(paths, TRACE_ID)
    assert value["completion_state"] == summary["completion_state"]
    assert value["runtime_state"] == summary["runtime_state"]
    assert value["work"]["all_required_done"] == summary["work_graph"]["all_required_done"]
    assert value["acceptance"]["complete"] == summary["acceptance"]["complete"]
    encoded = json.dumps(value, sort_keys=True)
    assert len(encoded.encode()) <= 2048
    for forbidden in ("raw", "prompt", "response", "command", "output", "diff", "reasoning"):
        assert forbidden not in encoded.lower()
    assert summary["summary_id"] == value["summary_id"]


def test_diagnose_returns_only_bounded_codes(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    project, _paths = _project(monkeypatch, tmp_path)
    _journal(_paths)
    value = brief.observe(
        {"action": "diagnose", "project": str(project), "ref": TRACE_ID},
        profile_name="morfeo",
    )
    assert value["action"] == "diagnose"
    assert len(value["coverage"]["reason_codes"]) <= 5
    assert len(value["finding_codes"]) <= 5
    assert len(value["bottleneck_classes"]) <= 5
    assert len(value["defect_classes"]) <= 5
    assert len(json.dumps(value).encode()) <= 4096


def test_changes_uses_existing_semantic_diff_and_requires_since(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    project, paths = _project(monkeypatch, tmp_path)
    _journal(paths)
    current = query.load_summary(paths, TRACE_ID)
    previous = deepcopy(current)
    previous["review_brief"]["verdict"] = "work_remaining"
    previous["summary_id"] = make_summary_id(previous)
    paths.summaries.mkdir(parents=True, exist_ok=True)
    previous_path = paths.summary_file(previous["summary_id"])
    previous_path.write_bytes(canonical_json_bytes(previous))
    previous_path.chmod(0o600)
    value = brief.observe(
        {
            "action": "changes",
            "project": str(project),
            "ref": TRACE_ID,
            "since_summary_id": previous["summary_id"],
        },
        profile_name="morfeo",
    )
    assert value["comparable"] is True
    assert "verdict" in value["change_classes"]
    assert "details" not in value
    with pytest.raises(brief.BriefError, match="requires since_summary_id"):
        brief.observe(
            {"action": "changes", "project": str(project), "ref": TRACE_ID},
            profile_name="morfeo",
        )


def test_empty_unknown_and_role_gate_are_explicit(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    project, _paths = _project(monkeypatch, tmp_path)
    value = brief.observe({"action": "status", "project": str(project)}, profile_name="morfeo")
    assert value == {
        "schema_version": brief.SCHEMA_VERSION,
        "action": "status",
        "state": "empty",
        "project_id": PROJECT_ID,
        "trace_id": None,
        "contract_id": None,
        "summary_id": None,
    }
    with pytest.raises(brief.BriefError) as denied:
        brief.observe({"action": "status", "project": str(project)}, profile_name="supervisor")
    assert denied.value.code == "AETHER-OBSERVE-ROLE-DENIED"


def test_plugin_registers_tool_only_for_enabled_morfeo(monkeypatch: pytest.MonkeyPatch) -> None:
    from aether_agents.observation.capture import hermes_plugin

    registered: dict[str, Any] = {}

    class Context:
        profile_name = "morfeo"

        def get_config(self, key: str, default: object = None) -> object:
            return True if key == "curated_tool" else default

        def register_tool(self, **kwargs: Any) -> None:
            registered.update(kwargs)

        def register_hook(self, _name: str, _callback: Any) -> None:
            pass

        def on_unload(self, _callback: Any) -> None:
            pass

    ctx = Context()
    monkeypatch.setattr(hermes_plugin, "_REGISTERED", set())
    monkeypatch.setattr(hermes_plugin, "_REGISTERED_FALLBACK", set())
    hermes_plugin.register(ctx)
    assert registered["name"] == "aether_observe"
    assert registered["toolset"] == "aether_observation"
    handler = registered["handler"]
    ctx.profile_name = "supervisor"
    denied = json.loads(handler({"action": "status"}))
    assert denied["error"]["code"] == "AETHER-OBSERVE-ROLE-DENIED"

    class Supervisor(Context):
        profile_name = "supervisor"

    other: dict[str, Any] = {}
    sup = Supervisor()
    sup.register_tool = lambda **kwargs: other.update(kwargs)  # type: ignore[method-assign]
    hermes_plugin.register(sup)
    assert other == {}

    failing: dict[str, Any] = {}
    broken = Context()
    broken.get_config = lambda *_args, **_kwargs: (_ for _ in ()).throw(RuntimeError("config"))  # type: ignore[method-assign]
    broken.register_tool = lambda **kwargs: failing.update(kwargs)  # type: ignore[method-assign]
    hermes_plugin.register(broken)
    assert failing == {}


def test_real_plugin_context_registers_and_unloads_curated_tool(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    pytest.importorskip("hermes_cli.plugins")
    home = tmp_path / "profiles" / "morfeo"
    home.mkdir(parents=True)
    (home / "config.yaml").write_text(
        "plugins:\n"
        "  entries:\n"
        "    aether-contract-observer:\n"
        "      settings:\n"
        "        curated_tool: true\n",
        encoding="utf-8",
    )
    monkeypatch.setenv("HERMES_HOME", str(home))
    from hermes_cli.plugins import PluginContext, PluginManager, PluginManifest
    from tools.registry import registry

    from aether_agents.observation.capture import hermes_plugin

    manager = PluginManager(scope_key=str(home))
    manifest = PluginManifest(
        name="aether-contract-observer",
        key="aether-contract-observer",
        source="entrypoint",
    )
    context = PluginContext(manifest, manager)
    monkeypatch.setattr(hermes_plugin, "_REGISTERED", set())
    monkeypatch.setattr(hermes_plugin, "_REGISTERED_FALLBACK", set())
    hermes_plugin.register(context)
    entry = registry.get_entry("aether_observe", scope=manager.scope_key)
    assert entry is not None
    assert entry.toolset == "aether_observation"
    assert manager.unload(manifest)
    assert registry.get_entry("aether_observe", scope=manager.scope_key) is None
