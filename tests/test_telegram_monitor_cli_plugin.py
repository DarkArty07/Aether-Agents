"""``aether monitor`` CLI, native control tool and plugin packaging (MON-05).

The deterministic half uses a Hermes-free manager interpreter and a disposable monitor
state root.  The ``hermes_exact`` half runs against the release-locked public Hermes
checkout to prove the real cron/plugin/toolset interfaces the monitor registers.
"""

from __future__ import annotations

import configparser
import importlib.util
import json
import os
import subprocess
import sys
import textwrap
import zipfile
from pathlib import Path
from typing import Any

import pytest

from aether_agents.lifecycle import HERMES_BASELINE, verify_clean_checkout
from aether_agents.monitor import commands as commands_module
from aether_agents.monitor import hermes_plugin
from aether_agents.monitor import runtime as runtime_module
from aether_agents.monitor.service import ACTIONS, MonitorService
from aether_agents.monitor.store import MonitorStore

ROOT = Path(__file__).parents[1]
MONITOR_ENTRY_POINT = ("aether-telegram-monitor", "aether_agents.monitor.hermes_plugin")


class FakePluginContext:
    """Small public-PluginContext-shaped facade; no private Hermes surface."""

    def __init__(self, profile_name: str = "morfeo", enabled: bool = True) -> None:
        self.profile_name = profile_name
        self.settings = {"enabled": enabled, "language": "Spanish"}
        self.tools: list[dict[str, Any]] = []
        self.hooks: dict[str, list[Any]] = {}

    def get_config(self, key: str, default: Any = None) -> Any:
        return self.settings.get(key, default)

    def register_tool(self, **kwargs: Any) -> None:
        self.tools.append(dict(kwargs))

    def register_hook(self, name: str, callback: Any) -> None:
        self.hooks.setdefault(name, []).append(callback)


@pytest.fixture
def hermes_free(monkeypatch: pytest.MonkeyPatch) -> None:
    """Force the manager-without-Hermes boundary even in the exact-Hermes test lane."""

    monkeypatch.setattr(runtime_module, "hermes_available", lambda: False)
    monkeypatch.setattr(commands_module, "runtime_interpreter", lambda: None)


@pytest.fixture
def isolated_environment(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Disposable Aether state root plus an inherited Hermes/Kanban-free environment."""

    monkeypatch.setenv("XDG_STATE_HOME", str(tmp_path / "xdg-state"))
    for name in [key for key in os.environ if key.startswith("HERMES_KANBAN_")]:
        monkeypatch.delenv(name, raising=False)
    for name in ("HERMES_HOME", "AETHER_HERMES_PYTHON", "AETHER_MONITOR_LANGUAGE", "PYTHONPATH"):
        monkeypatch.delenv(name, raising=False)
    return tmp_path / "xdg-state" / "aether"


# ---------------------------------------------------------------------------
# Hermes-free manager boundary
# ---------------------------------------------------------------------------


def test_cli_parser_and_help_are_hermes_free_and_expose_the_fixed_surface() -> None:
    script = textwrap.dedent(
        """
        from aether_agents.cli import _build_parser, main

        parser = _build_parser()
        assert "monitor" in parser.format_help()
        # `main` never raises: argparse's own --help/usage exits become return codes.
        assert main(["monitor", "--help"]) == 0
        import sys

        assert "cron" not in sys.modules and "hermes_cli" not in sys.modules
        print("HERMES-FREE-OK")
        """
    )
    completed = subprocess.run(
        [sys.executable, "-c", script],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
        env={"PATH": os.environ.get("PATH", ""), "PYTHONPATH": str(ROOT / "src")},
    )
    assert completed.returncode == 0, completed.stderr
    assert "HERMES-FREE-OK" in completed.stdout

    help_result = subprocess.run(
        [sys.executable, "-m", "aether_agents.cli", "monitor", "--help"],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
        env={"PATH": os.environ.get("PATH", ""), "PYTHONPATH": str(ROOT / "src")},
    )
    assert help_result.returncode == 0
    for action in ACTIONS:
        assert action in help_result.stdout


def test_cli_actions_read_the_durable_state_without_hermes(
    isolated_environment: Path, hermes_free: None, capsys: pytest.CaptureFixture[str]
) -> None:
    store = MonitorStore()
    store.configure(
        native_job_id="job-monitor-1",
        profile_binding="morfeo",
        destination_ref="telegram-home-" + "a" * 64,
        timezone_name="UTC",
    )
    store.set_enabled(True)

    from aether_agents.cli import main

    assert main(["monitor", "status", "--json"]) == 0
    envelope = json.loads(capsys.readouterr().out)
    assert envelope["schema_version"] == "aether.telegram-monitor.v1"
    assert envelope["ok"] is True and envelope["action"] == "status"
    assert envelope["result"]["enabled"] is True
    assert envelope["result"]["runtime"]["available"] is False
    assert envelope["result"]["runtime"]["job_error"] == "RUNTIME_UNAVAILABLE"

    assert main(["monitor", "history", "--json", "--limit", "3"]) == 0
    history = json.loads(capsys.readouterr().out)
    assert history["result"] == {"limit": 3, "count": 0, "reports": []}

    # Without a Hermes runtime the control actions fail closed and change nothing.
    assert main(["monitor", "on", "--json"]) == 1
    error = json.loads(capsys.readouterr().out)
    assert error["ok"] is False
    assert error["error"]["code"] == "RUNTIME_UNAVAILABLE"
    assert store.get_settings().enabled is True


def test_cli_malformed_inputs_fail_closed(capsys: pytest.CaptureFixture[str]) -> None:
    from aether_agents.cli import main

    assert main(["monitor"]) == 2
    assert main(["monitor", "unknown-action"]) == 2
    assert main(["monitor", "history", "--limit", "not-a-number"]) == 2
    capsys.readouterr()

    assert main(["monitor", "history", "--limit", "500", "--json"]) == 1
    envelope = json.loads(capsys.readouterr().out)
    assert envelope["ok"] is False and envelope["error"]["code"] == "INVALID_LIMIT"


def test_runtime_subprocess_boundary_validates_and_fails_closed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    envelope = json.dumps(
        {
            "schema_version": "aether.telegram-monitor.v1",
            "ok": True,
            "action": "status",
            "result": {"enabled": True},
        }
    )

    def _interpreter(name: str, body: str) -> Path:
        script = tmp_path / name
        script.write_text(f"#!/bin/sh\n{body}\n", encoding="utf-8")
        script.chmod(0o755)
        return script

    real_probe = commands_module._probe_runtime
    good = _interpreter(
        "hermes-python",
        f"case \"$*\" in *\"-c\"*) exit 0;; esac\nprintf '%s\\n' '{envelope}'",
    )
    monkeypatch.setenv(commands_module.RUNTIME_PYTHON_ENV, str(good))
    # The real probe accepts an interpreter that answers the interface import.
    assert commands_module.runtime_interpreter() == good
    assert commands_module._run_runtime_subprocess("status", None) == json.loads(envelope)

    refused = _interpreter("refused-python", "exit 1")
    monkeypatch.setenv(commands_module.RUNTIME_PYTHON_ENV, str(refused))
    assert commands_module.runtime_interpreter() is None

    # The returned envelope is what decides success, not the probe alone.
    monkeypatch.setattr(commands_module, "_probe_runtime", real_probe)
    for name, body, expected in (
        ("not-json", "printf 'not json\\n'", None),
        (
            "wrong-schema",
            'printf \'%s\\n\' \'{"ok": true, "action": "status", "result": {}}\'',
            None,
        ),
        (
            "wrong-action",
            f"printf '%s\\n' '{envelope.replace('status', 'on')}'",
            None,
        ),
        ("crashing", "exit 3", None),
    ):
        candidate = _interpreter(name, body)
        monkeypatch.setenv(commands_module.RUNTIME_PYTHON_ENV, str(candidate))
        assert commands_module._run_runtime_subprocess("status", None) == expected

    # The boundary forwards the action and the bounded history limit exactly.
    recorder = tmp_path / "recorded-args"
    history_envelope = envelope.replace('"action": "status"', '"action": "history"')
    candidate = _interpreter(
        "recording-python",
        f"printf '%s\\n' \"$*\" > {recorder}\nprintf '%s\\n' '{history_envelope}'",
    )
    monkeypatch.setenv(commands_module.RUNTIME_PYTHON_ENV, str(candidate))
    assert commands_module._run_runtime_subprocess("history", 7) == json.loads(history_envelope)
    forwarded = recorder.read_text(encoding="utf-8").split()
    assert forwarded[:3] == ["-m", "aether_agents.monitor.runtime", "--action"]
    assert forwarded[3] == "history" and forwarded[4:6] == ["--limit", "7"]

    monkeypatch.delenv(commands_module.RUNTIME_PYTHON_ENV)
    isolated = commands_module._isolated_environment()
    assert not any(name.startswith("HERMES_KANBAN_") for name in isolated)
    assert "PYTHONPATH" not in isolated


# ---------------------------------------------------------------------------
# Native tool surface
# ---------------------------------------------------------------------------


def _monitor_store() -> MonitorStore:
    store = MonitorStore()
    store.configure(
        native_job_id="job-monitor-1",
        profile_binding="morfeo",
        destination_ref="telegram-home-" + "a" * 64,
        timezone_name="UTC",
    )
    store.set_enabled(True)
    return store


def test_control_tool_matches_the_cli_envelope_and_rejects_bad_arguments(
    isolated_environment: Path, hermes_free: None
) -> None:
    store = _monitor_store()
    context = FakePluginContext()
    hermes_plugin.register(context)

    assert [tool["name"] for tool in context.tools] == [
        runtime_module.CONTROL_TOOL,
        runtime_module.REPORTER_TOOL,
    ]
    assert {tool["toolset"] for tool in context.tools} == {
        runtime_module.CONTROL_TOOLSET,
        runtime_module.REPORTER_TOOLSET,
    }
    control = next(tool for tool in context.tools if tool["name"] == runtime_module.CONTROL_TOOL)
    assert control["schema"]["parameters"]["properties"]["action"]["enum"] == list(ACTIONS)

    payload = json.loads(control["handler"]({"action": "status"}))
    cli_envelope = MonitorService(store=store, native=None).execute("status")
    assert payload["schema_version"] == cli_envelope["schema_version"]
    assert payload["action"] == cli_envelope["action"]
    assert payload["result"].keys() == cli_envelope["result"].keys()

    for arguments, code in (
        ({"action": "status", "limit": 5}, "INVALID_ARGUMENT"),
        ({"action": "status", "extra": 1}, "INVALID_ARGUMENT"),
        ({"action": "destroy"}, "INVALID_ARGUMENT"),
        ({"action": "history", "limit": 0}, "INVALID_LIMIT"),
    ):
        error = json.loads(control["handler"](arguments))
        assert error["ok"] is False and error["error"]["code"] == code, arguments

    refused = json.loads(
        control["handler"]({"action": "off"}, session_id="cron_job-monitor-1_20260910_120000")
    )
    assert refused["error"]["code"] == "MONITOR_RUN_CONTROL_REFUSED"
    assert store.get_settings().enabled is True


def test_reporter_tool_is_restricted_to_the_dedicated_toolset_and_exact_run(
    isolated_environment: Path,
) -> None:
    _monitor_store()
    context = FakePluginContext()
    hermes_plugin.register(context)
    reporter = next(tool for tool in context.tools if tool["name"] == runtime_module.REPORTER_TOOL)
    assert reporter["toolset"] == runtime_module.REPORTER_TOOLSET
    assert reporter["schema"]["parameters"]["properties"] == {}

    outside = json.loads(reporter["handler"]({}, session_id="session-ordinary"))
    assert outside["error"]["code"] == "REPORTER_CONTEXT_REQUIRED"

    session_id = "cron_job-monitor-1_20260910_120000"
    empty = json.loads(reporter["handler"]({}, session_id=session_id))
    assert empty["ok"] is False
    assert empty["error"]["code"] in {"NO_PENDING_REPORT", "SNAPSHOT_UNAVAILABLE"}

    # Only the monitor's own two tools exist; nothing expands to the default surface.
    registered = {(tool["name"], tool["toolset"]) for tool in context.tools}
    assert registered == {
        (runtime_module.CONTROL_TOOL, runtime_module.CONTROL_TOOLSET),
        (runtime_module.REPORTER_TOOL, runtime_module.REPORTER_TOOLSET),
    }
    assert sorted(context.hooks) == ["on_session_end", "post_llm_call", "post_tool_call"]


def test_tool_registration_is_morfeo_only_and_opt_in() -> None:
    for profile, enabled in (("implementer", True), ("supervisor", True), ("morfeo", False)):
        context = FakePluginContext(profile_name=profile, enabled=enabled)
        hermes_plugin.register(context)
        assert context.tools == [], (profile, enabled)


def test_morfeo_portable_opt_in_is_the_only_profile_that_enables_the_monitor() -> None:
    profiles = ROOT / "src" / "aether_agents" / "resources" / "profiles"
    import yaml

    morfeo = yaml.safe_load((profiles / "morfeo" / "config.yaml").read_text(encoding="utf-8"))
    entry = morfeo["plugins"]["entries"]["aether-telegram-monitor"]
    assert "aether-telegram-monitor" in morfeo["plugins"]["enabled"]
    assert entry["settings"]["enabled"] is True
    assert entry["settings"]["language"] == "Spanish"

    for other in ("supervisor", "implementer"):
        data = yaml.safe_load((profiles / other / "config.yaml").read_text(encoding="utf-8"))
        assert "aether-telegram-monitor" not in (data["plugins"].get("enabled") or [])
        assert "aether-telegram-monitor" not in (data["plugins"].get("entries") or {})


def test_only_one_plugin_entry_point_is_declared_for_the_monitor() -> None:
    import tomllib

    project = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    entry_points = project["project"]["entry-points"]["hermes_agent.plugins"]
    assert entry_points[MONITOR_ENTRY_POINT[0]] == MONITOR_ENTRY_POINT[1]
    assert len([value for value in entry_points.values() if "monitor" in value]) == 1


# ---------------------------------------------------------------------------
# Release-locked native runtime
# ---------------------------------------------------------------------------


def _unrelated_job(cron_jobs: Any, home: Path) -> dict[str, Any]:
    """Create one unrelated native job directly in the disposable cron store."""

    store = home / "cron"
    store.mkdir(parents=True, exist_ok=True)
    job = {
        "id": "job-unrelated",
        "name": "Unrelated",
        "prompt": "unrelated",
        "schedule": {"kind": "interval", "minutes": 5, "display": "every 5m"},
        "enabled": True,
        "paused": False,
        "deliver": "local",
        "no_agent": False,
        "attach_to_session": False,
    }
    (store / "jobs.json").write_text(json.dumps({"jobs": [job]}), encoding="utf-8")
    with cron_jobs.use_cron_store(home):
        loaded = cron_jobs.get_job("job-unrelated")
    assert loaded is not None
    return job


def _exact_checkout() -> Path:
    configured = os.environ.get("AETHER_EXACT_HERMES_CHECKOUT")
    if configured:
        return Path(configured).expanduser()
    cache_home = Path(os.environ.get("XDG_CACHE_HOME", Path.home() / ".cache"))
    return cache_home / "aether-agents" / "hermes" / HERMES_BASELINE.tag


@pytest.mark.hermes_exact
def test_exact_hermes_interfaces_hooks_toolset_and_owned_cron_job(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    checkout = _exact_checkout()
    if not checkout.exists():
        pytest.skip(f"exact Hermes checkout unavailable at {checkout}")
    verify_clean_checkout(
        checkout,
        expected_tag=HERMES_BASELINE.tag,
        expected_commit=HERMES_BASELINE.commit,
        expected_tag_object=HERMES_BASELINE.tag_object,
    )
    monkeypatch.syspath_prepend(str(checkout))

    home = tmp_path / "profile"
    home.mkdir()
    (home / "config.yaml").write_text(
        "\n".join(
            (
                "plugins:",
                "  enabled:",
                "    - aether-telegram-monitor",
                "  entries:",
                "    aether-telegram-monitor:",
                "      settings:",
                "        enabled: true",
                "        language: Spanish",
                "",
            )
        ),
        encoding="utf-8",
    )
    monkeypatch.setenv("HERMES_HOME", str(home))

    from cron import jobs as cron_jobs
    from hermes_cli import profiles as hermes_profiles
    from hermes_cli.plugins import (
        VALID_HOOKS,
        PluginContext,
        PluginManager,
        PluginManifest,
    )

    # The monitor's own runtime preflight passes on the release-locked runtime.
    assert runtime_module._module_problems() == []
    for hook in ("post_tool_call", "post_llm_call", "on_session_end"):
        assert hook in VALID_HOOKS

    # The wake gate contract the packaged pre-check relies on is native behavior.
    from cron import scheduler

    assert scheduler._parse_wake_gate('{"wakeAgent": false}') is False
    assert scheduler._parse_wake_gate('{"wakeAgent": false, "reason": "idle"}') is False
    assert scheduler._parse_wake_gate('{"wakeAgent": true}') is True
    assert scheduler._parse_wake_gate("no gate here") is True

    # Real plugin registration through the public PluginContext/PluginManager surface.
    monkeypatch.setattr(hermes_profiles, "get_active_profile_name", lambda: "morfeo", raising=True)
    manager = PluginManager(scope_key=str(home))
    manifest = PluginManifest(
        name="aether-telegram-monitor", key="aether-telegram-monitor", source="entrypoint"
    )
    context = PluginContext(manifest, manager)
    hermes_plugin.register(context)

    from tools.registry import registry

    assert set(registry.get_tool_names_for_toolset(runtime_module.CONTROL_TOOLSET)) == {
        runtime_module.CONTROL_TOOL
    }
    assert set(registry.get_tool_names_for_toolset(runtime_module.REPORTER_TOOLSET)) == {
        runtime_module.REPORTER_TOOL
    }
    for hook in ("post_tool_call", "post_llm_call", "on_session_end"):
        assert hook in manager._hooks and manager._hooks[hook], hook

    # The owned job is created through the real native cron API with the fixed shape.
    runtime = runtime_module.HermesRuntime()
    captured: list[dict[str, Any]] = []
    real_create = cron_jobs.create_job
    real_get = cron_jobs.get_job
    real_list = cron_jobs.list_jobs

    def recording_create(**kwargs: Any) -> dict[str, Any]:
        captured.append(dict(kwargs))
        return {
            "id": "job-captured",
            "name": kwargs.get("name"),
            "schedule": kwargs.get("schedule"),
            "script": kwargs.get("script"),
            "deliver": kwargs.get("deliver"),
            "no_agent": kwargs.get("no_agent"),
            "attach_to_session": kwargs.get("attach_to_session"),
            "enabled_toolsets": kwargs.get("enabled_toolsets"),
        }

    with cron_jobs.use_cron_store(home):
        unrelated = _unrelated_job(cron_jobs, home)
        unrelated_bytes = json.dumps(real_get(unrelated["id"]), sort_keys=True)
        monkeypatch.setattr(cron_jobs, "create_job", recording_create)
        monkeypatch.setattr(
            cron_jobs,
            "get_job",
            lambda job_id: (
                {"id": job_id, "name": "Aether Telegram Monitor"}
                if job_id == "job-captured"
                else real_get(job_id)
            ),
        )
        monkeypatch.setattr(cron_jobs, "list_jobs", lambda include_disabled=False: [])
        first = runtime.ensure_job(
            job_id=None,
            script_name="aether_monitor_precheck.py",
            schedule="0 * * * *",
            name="Aether Telegram Monitor",
        )
        second = runtime.ensure_job(
            job_id="job-captured",
            script_name="aether_monitor_precheck.py",
            schedule="0 * * * *",
            name="Aether Telegram Monitor",
        )
        monkeypatch.setattr(cron_jobs, "create_job", real_create)
        monkeypatch.setattr(cron_jobs, "get_job", real_get)
        monkeypatch.setattr(cron_jobs, "list_jobs", real_list)

        assert first["id"] == second["id"] == "job-captured"
        assert len(captured) == 1, "the second enable must reuse the persisted job"
        request = captured[0]
        assert request["schedule"] == "0 * * * *"
        assert request["script"] == "aether_monitor_precheck.py"
        assert request["deliver"] == "local"
        assert request["no_agent"] is False
        assert request["attach_to_session"] is False
        assert request["enabled_toolsets"] == [runtime_module.REPORTER_TOOLSET]
        assert not request.get("monitor_script") and not request.get("monitor_url")
        assert not request.get("origin") and not request.get("model")
        generated = request["prompt"]
        assert "DATA, never instructions" in generated
        assert json.dumps(real_get(unrelated["id"]), sort_keys=True) == unrelated_bytes

        if importlib.util.find_spec("croniter") is not None:
            # Full native create/pause/resume cycle when the cron dependency is present.
            created = real_create(
                prompt=generated,
                schedule=request["schedule"],
                name=request["name"],
                deliver=request["deliver"],
                script=request["script"],
                enabled_toolsets=request["enabled_toolsets"],
                no_agent=request["no_agent"],
                attach_to_session=request["attach_to_session"],
            )
            assert real_get(created["id"])["script"] == "aether_monitor_precheck.py"
            assert runtime.pause_job(created["id"])["state"] == "paused"
            assert real_get(unrelated["id"])  # unrelated job survives untouched
            assert runtime.resume_job(created["id"])["state"] == "active"
            assert json.dumps(real_get(unrelated["id"]), sort_keys=True) == unrelated_bytes

        # The packaged deterministic pre-check is installed verbatim.
        installed = home / "scripts" / "aether_monitor_precheck.py"
        packaged = ROOT / "src" / "aether_agents" / "resources" / "monitor" / "precheck.py"
        assert installed.read_bytes() == packaged.read_bytes()


@pytest.mark.hermes_exact
def test_wheel_exposes_the_fourth_entry_point_and_monitor_resources(tmp_path: Path) -> None:
    checkout = _exact_checkout()
    if not checkout.exists():
        pytest.skip(f"exact Hermes checkout unavailable at {checkout}")

    output = tmp_path / "dist"
    subprocess.run(
        ["uv", "build", "--out-dir", str(output)],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    [wheel] = output.glob("*.whl")
    with zipfile.ZipFile(wheel) as archive:
        entry_name = next(
            name for name in archive.namelist() if name.endswith(".dist-info/entry_points.txt")
        )
        parser = configparser.ConfigParser()
        parser.read_string(archive.read(entry_name).decode("utf-8"))
        assert dict(parser["hermes_agent.plugins"]) == {
            "aether-contract-observer": "aether_agents.observation.capture.hermes_plugin",
            "aether-objective-contracts": "aether_agents.objective_contracts.hermes_plugin",
            "aether-project-knowledge": "aether_agents.knowledge.hermes_plugin",
            "aether-telegram-monitor": "aether_agents.monitor.hermes_plugin",
        }
        for name in (
            "aether_agents/resources/monitor/precheck.py",
            "aether_agents/resources/monitor/narration-context.md",
            "aether_agents/monitor/runtime.py",
            "aether_agents/monitor/commands.py",
            "aether_agents/monitor/hermes_plugin.py",
        ):
            assert name in archive.namelist(), name
        precheck = archive.read("aether_agents/resources/monitor/precheck.py")
        assert (
            precheck
            == (
                ROOT / "src" / "aether_agents" / "resources" / "monitor" / "precheck.py"
            ).read_bytes()
        )
