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


def test_control_tool_returns_a_bounded_envelope_when_the_runtime_raises(
    isolated_environment: Path, hermes_free: None, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A raw native failure never escapes the control tool's fixed JSON envelope."""

    _monitor_store()
    context = FakePluginContext()
    hermes_plugin.register(context)
    control = next(tool for tool in context.tools if tool["name"] == runtime_module.CONTROL_TOOL)

    def explode(action: str, *, limit: int | None = None, store: Any = None) -> None:
        raise RuntimeError("raw native failure")

    monkeypatch.setattr(runtime_module, "execute_action", explode)

    envelope = json.loads(control["handler"]({"action": "on"}))

    assert envelope["schema_version"] == "aether.telegram-monitor.v1"
    assert envelope["ok"] is False and envelope["action"] == "on"
    assert envelope["error"]["code"] == "RUNTIME_UNAVAILABLE"


def test_cli_control_action_returns_the_envelope_when_the_runtime_raises(
    isolated_environment: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The in-process CLI boundary converts a raw native failure into the fixed envelope."""

    monkeypatch.setattr(runtime_module, "hermes_available", lambda: True)
    monkeypatch.setattr(commands_module, "runtime_interpreter", lambda: None)

    def explode(action: str, *, limit: int | None = None) -> None:
        raise RuntimeError("raw native failure")

    monkeypatch.setattr(runtime_module, "execute_action", explode)

    envelope = commands_module.execute_action("status")

    assert envelope["schema_version"] == "aether.telegram-monitor.v1"
    assert envelope["ok"] is False and envelope["action"] == "status"
    assert envelope["error"]["code"] == "RUNTIME_UNAVAILABLE"


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

    # The owned job is reconciled through the real native cron API.  (This runtime
    # lacks the optional `croniter` dependency, so a cron-expression create cannot run
    # here; creation fidelity is covered by the fixed-shape validation in
    # `tests/test_telegram_monitor_runtime.py` plus the drift/update cycle below.)
    runtime = runtime_module.HermesRuntime()
    owned_id = "job-monitor-owned"
    with cron_jobs.use_cron_store(home):
        unrelated = _unrelated_job(cron_jobs, home)
        unrelated_bytes = json.dumps(cron_jobs.get_job(unrelated["id"]), sort_keys=True)
        store_dir = home / "cron"
        jobs = json.loads((store_dir / "jobs.json").read_text(encoding="utf-8"))
        jobs["jobs"].append(
            {
                "id": owned_id,
                "name": "Aether Telegram Monitor",
                "prompt": "hijacked prompt",
                "skills": ["some-skill"],
                "skill": "some-skill",
                "model": "some/model",
                "provider": "some-provider",
                "provider_snapshot": None,
                "model_snapshot": None,
                "base_url": "https://example.invalid",
                "script": "aether_monitor_precheck.py",
                "no_agent": False,
                "monitor_script": None,
                "monitor_url": None,
                "monitor_state": None,
                "context_from": ["other-job"],
                "schedule": {"kind": "cron", "expr": "0 * * * *", "display": "0 * * * *"},
                "schedule_display": "0 * * * *",
                "repeat": {"times": None, "completed": 0},
                "enabled": True,
                "state": "scheduled",
                "paused_at": None,
                "paused_reason": None,
                "created_at": "2026-09-10T00:00:00+00:00",
                "next_run_at": None,
                "last_run_at": None,
                "last_status": None,
                "last_error": None,
                "last_delivery_error": None,
                "failure_streak": 0,
                "deliver": "local",
                "origin": {"platform": "telegram"},
                "enabled_toolsets": ["terminal"],
                "workdir": str(tmp_path / "unrelated-workdir"),
                "attach_to_session": False,
            }
        )
        (store_dir / "jobs.json").write_text(json.dumps(jobs), encoding="utf-8")
        assert cron_jobs.get_job(owned_id)["prompt"] == "hijacked prompt"

        first = runtime.ensure_job(
            job_id=owned_id,
            script_name="aether_monitor_precheck.py",
            schedule="0 * * * *",
            name="Aether Telegram Monitor",
        )
        assert first["id"] == owned_id and first["created"] is False
        repaired = cron_jobs.get_job(owned_id)
        assert repaired["prompt"] == runtime_module._JOB_PROMPT
        assert "DATA, never instructions" in repaired["prompt"]
        assert repaired["model"] is None and repaired["provider"] is None
        assert repaired["base_url"] is None
        assert repaired["origin"] is None
        assert not repaired["skills"] and repaired["skill"] is None
        assert repaired["context_from"] is None
        assert repaired["workdir"] is None
        assert repaired["enabled_toolsets"] == [
            runtime_module.REPORTER_TOOLSET,
            runtime_module.NO_MCP_SENTINEL,
        ]
        assert repaired["attach_to_session"] is False and repaired["no_agent"] is False
        assert repaired["deliver"] == "local" and repaired["script"] == "aether_monitor_precheck.py"

        # The native scheduler resolves only the reporter toolset for this job: the
        # `no_mcp` sentinel is load-bearing, because without it the same per-job list
        # silently gains every provisioned MCP server.
        cfg = {"mcp_servers": {"provisioned-mcp": {"enabled": True}}}
        assert scheduler._merge_mcp_into_per_job_toolsets(
            [runtime_module.REPORTER_TOOLSET], cfg
        ) == [runtime_module.REPORTER_TOOLSET, "provisioned-mcp"]
        resolved = scheduler._resolve_cron_enabled_toolsets(repaired, cfg)
        assert resolved == [runtime_module.REPORTER_TOOLSET]
        from toolsets import validate_toolset

        assert all(validate_toolset(name) for name in resolved)

        # Reuse is idempotent and never creates a duplicate.
        owned_before = json.dumps(cron_jobs.get_job(owned_id), sort_keys=True)
        second = runtime.ensure_job(
            job_id=owned_id,
            script_name="aether_monitor_precheck.py",
            schedule="0 * * * *",
            name="Aether Telegram Monitor",
        )
        assert second["id"] == owned_id and second["created"] is False
        assert json.dumps(cron_jobs.get_job(owned_id), sort_keys=True) == owned_before
        assert (
            len(
                [
                    job
                    for job in cron_jobs.list_jobs(include_disabled=True)
                    if job.get("name") == "Aether Telegram Monitor"
                ]
            )
            == 1
        )

        # A foreign record at a persisted id is never paused; the real inventory is
        # otherwise untouched.
        with pytest.raises(runtime_module.MonitorActionError) as conflict:
            runtime.pause_job(unrelated["id"])
        assert conflict.value.code == "JOB_CONFLICT"
        assert cron_jobs.get_job(unrelated["id"])["enabled"] is True

        # The real native pause/resume cycle works for the owned job only.
        assert runtime.pause_job(owned_id)["state"] == "paused"
        assert cron_jobs.get_job(owned_id)["enabled"] is False
        assert runtime.resume_job(owned_id)["state"] == "active"
        assert cron_jobs.get_job(owned_id)["enabled"] is True
        assert json.dumps(cron_jobs.get_job(unrelated["id"]), sort_keys=True) == unrelated_bytes

        # Behavior drift that lands after reconciliation is refused at resume time by
        # the real release-locked store, and the refused resume mutates nothing.
        cron_jobs.update_job(
            owned_id, {"prompt": "FOREIGN BEHAVIOR", "enabled_toolsets": ["terminal"]}
        )
        latest_drift = cron_jobs.get_job(owned_id)
        assert latest_drift["prompt"] == "FOREIGN BEHAVIOR"
        with pytest.raises(runtime_module.MonitorActionError) as late_conflict:
            runtime.resume_job(owned_id)
        assert late_conflict.value.code == "JOB_CONFLICT"
        untouched = cron_jobs.get_job(owned_id)
        assert untouched["prompt"] == "FOREIGN BEHAVIOR"
        assert untouched["enabled_toolsets"] == ["terminal"]
        assert untouched["enabled"] is True

        # The packaged deterministic pre-check is installed verbatim.
        installed = home / "scripts" / "aether_monitor_precheck.py"
        packaged = ROOT / "src" / "aether_agents" / "resources" / "monitor" / "precheck.py"
        assert installed.read_bytes() == packaged.read_bytes()


def _runtime_test_helpers():
    """Load the monitor runtime test helpers for reuse in this exact lane."""

    spec = importlib.util.spec_from_file_location(
        "monitor_runtime_helpers", ROOT / "tests" / "test_telegram_monitor_runtime.py"
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.mark.hermes_exact
def test_exact_packaged_precheck_child_hands_the_lease_to_the_reporter(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The installed packaged pre-check runs as a real child and the reporter still wins.

    The child's narration lease owner dies with it; the private handoff is the only
    evidence that lets the exact reporter session take the pending report over.
    """

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

    helpers = _runtime_test_helpers()
    home = tmp_path / "profile"
    home.mkdir()
    (home / "config.yaml").write_text("plugins: {}\n", encoding="utf-8")
    xdg = tmp_path / "xdg"
    monkeypatch.setenv("HERMES_HOME", str(home))
    monkeypatch.setenv("XDG_STATE_HOME", str(xdg))

    from aether_agents.monitor import runtime as monitor_runtime
    from aether_agents.monitor.store import MonitorStore

    store = MonitorStore()
    store.configure(
        native_job_id=helpers.JOB_ID,
        profile_binding=helpers.PROFILE,
        destination_ref=helpers.TARGET_REF,
        timezone_name="UTC",
    )
    store.set_enabled(True)
    helpers._seed_report(store, narrative_status="pending")
    cutoff_text = store.get_snapshot("report-alpha").cutoff_utc

    monitor_runtime.HermesRuntime().install_precheck()
    installed = home / "scripts" / monitor_runtime.PRECHECK_SCRIPT_NAME
    assert installed.exists()

    completed = subprocess.run(
        [sys.executable, str(installed)],
        cwd=str(home),
        env={
            "PATH": os.environ.get("PATH", ""),
            "PYTHONPATH": os.pathsep.join((str(checkout), str(ROOT / "src"))),
            "HERMES_HOME": str(home),
            "XDG_STATE_HOME": str(xdg),
        },
        capture_output=True,
        text=True,
        timeout=120,
    )
    assert completed.returncode == 0, completed.stderr
    lines = [line for line in completed.stdout.splitlines() if line.strip()]
    assert lines, completed.stderr
    gate = json.loads(lines[-1])
    assert gate["wakeAgent"] is True
    assert gate["reason"] == "pending-report"
    assert gate["report_id"] == "report-alpha"
    assert gate["cutoff_utc"] == cutoff_text

    # The native scheduler executes the same packaged script and never reads an idle
    # gate out of it, whatever the child runtime can resolve.
    from cron import scheduler

    ok, output = scheduler._run_job_script(monitor_runtime.PRECHECK_SCRIPT_NAME)
    assert ok is True
    assert scheduler._parse_wake_gate(output) is True

    # The child is gone; the handoff carries the report to the exact reporter session.
    parent = MonitorStore()
    handoff = monitor_runtime._read_handoff(parent, "report-alpha")
    assert handoff is not None

    response = json.dumps(helpers._narrative("report-alpha"))
    accepted = monitor_runtime.handle_post_llm_call(
        helpers._reporter_payload(assistant_response=response),
        store=parent,
        profile_name=helpers.PROFILE,
    )
    assert accepted == "report-alpha"

    sender = helpers._Sender()
    run = monitor_runtime.handle_session_end(
        helpers._reporter_payload(completed=True),
        store=parent,
        profile_name=helpers.PROFILE,
        delivery=helpers._adapter(parent, sender),
    )
    assert run is not None
    expected_parts = helpers.reporting.render_parts(
        helpers._payload("report-alpha", helpers.ANCHOR), helpers._narrative("report-alpha")
    )
    assert sender.calls == expected_parts

    repeat = helpers._Sender()
    assert (
        monitor_runtime.handle_session_end(
            helpers._reporter_payload(completed=True),
            store=parent,
            profile_name=helpers.PROFILE,
            delivery=helpers._adapter(parent, repeat),
        )
        is None
    )
    assert repeat.calls == []


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


# ---------------------------------------------------------------------------
# Offline qualification harness (MON-06)
# ---------------------------------------------------------------------------

QUALIFICATION = ROOT / "scripts" / "qualify_telegram_monitor.py"
FORBIDDEN_QUALIFICATION_OPTIONS = (
    "--token",
    "--bot-token",
    "--chat-id",
    "--destination",
    "--recipient",
    "--provider",
    "--model",
    "--api-key",
    "--credential",
)


def _qualification_environment(tmp_path: Path, *, poison_native: bool) -> dict[str, str]:
    """A disposable state root plus optional native-import tripwires."""

    environment = {
        "PATH": os.environ.get("PATH", ""),
        "HOME": os.environ.get("HOME", ""),
        "PYTHONDONTWRITEBYTECODE": "1",
        "XDG_STATE_HOME": str(tmp_path / "state-home"),
        # The live lane must never run from a test process; make that explicit here so a
        # Hermes-capable test lane cannot turn a qualification test into a live effect.
        "PYTEST_CURRENT_TEST": "tests/test_telegram_monitor_cli_plugin.py",
    }
    if poison_native:
        shim = tmp_path / "native-shim"
        shim.mkdir(parents=True, exist_ok=True)
        for name in ("cron", "hermes_cli", "gateway"):
            (shim / f"{name}.py").write_text(
                "raise ImportError('offline qualification imported a native module')\n",
                encoding="utf-8",
            )
        environment["PYTHONPATH"] = str(shim)
    return environment


def _run_qualification(
    tmp_path: Path, *arguments: str, poison_native: bool = False
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(QUALIFICATION), *arguments],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
        env=_qualification_environment(tmp_path, poison_native=poison_native),
        timeout=300,
    )


def _qualification_module() -> Any:
    spec = importlib.util.spec_from_file_location("qualify_telegram_monitor", QUALIFICATION)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_qualification_options_are_exactly_the_fixed_contract(tmp_path: Path) -> None:
    """The harness accepts --live/--json/--output/--wait-hourly-boundaries and nothing else."""

    module = _qualification_module()

    parser = module._build_parser()
    options = sorted(
        option
        for action in parser._actions
        for option in action.option_strings
        if option not in {"-h", "--help"}
    )
    assert options == ["--json", "--live", "--output", "--wait-hourly-boundaries"]
    defaults = {action.dest: action.default for action in parser._actions}
    assert defaults["wait_hourly_boundaries"] == 2
    assert defaults["live"] is False
    assert not [option for option in options if option in FORBIDDEN_QUALIFICATION_OPTIONS]


def test_offline_qualification_makes_no_model_or_sender_call(tmp_path: Path) -> None:
    """No --live run passes with native imports poisoned and live state untouched."""

    completed = _run_qualification(tmp_path, "--json", poison_native=True)

    assert completed.returncode == 0, completed.stderr
    summary = json.loads(completed.stdout)
    assert summary["schema_version"] == "aether.telegram-monitor.qualification.v1"
    assert summary["mode"] == "offline" and summary["ok"] is True
    assert summary["external_effects"] == {"model_calls": 0, "telegram_sends": 0}
    assert [record["status"] for record in summary["checks"]] == ["pass"] * len(summary["checks"])
    checks = {record["check"] for record in summary["checks"]}
    assert {"harness-options", "cli-surface", "plugin-surface", "packaged-precheck"} <= checks
    assert not (tmp_path / "state-home" / "aether" / "monitor").exists()
    assert "real provisioned model narration and Telegram delivery" in summary["unqualified_scope"]


def test_live_qualification_refuses_unsafe_invocations_without_effects(tmp_path: Path) -> None:
    """Missing output, invalid bounds and repository-internal output all fail closed."""

    missing_output = _run_qualification(tmp_path, "--live", "--json")
    assert missing_output.returncode == 2
    assert "--live requires --output" in missing_output.stderr

    for value in ("0", "25", "not-a-number"):
        bounded = _run_qualification(tmp_path, "--wait-hourly-boundaries", value, "--json")
        assert bounded.returncode == 2, value

    inside = ROOT / "qualification-should-not-exist.json"
    repository_output = _run_qualification(tmp_path, "--live", "--output", str(inside), "--json")
    assert repository_output.returncode == 1
    envelope = json.loads(repository_output.stdout)
    assert envelope["ok"] is False
    assert envelope["error"]["code"] in {"output-inside-repository", "runtime-unavailable"}
    assert not inside.exists()

    outside = tmp_path / "private" / "receipts.json"
    no_runtime = _run_qualification(tmp_path, "--live", "--output", str(outside), "--json")
    # The live lane must fail closed in a test process and write nothing.
    assert no_runtime.returncode == 1
    envelope = json.loads(no_runtime.stdout)
    assert envelope["ok"] is False
    assert envelope["error"]["code"] in {
        "test-process-refused",
        "runtime-unavailable",
    }
    assert not outside.exists()


def test_live_public_summary_excludes_private_handles_and_private_paths() -> None:
    """Only sanitized timings, counts and case results may leave a live run."""

    module = _qualification_module()
    record = {
        "candidate_revision": "0" * 40,
        "runtime_interpreter": "/private/operator/runtime/python3",
        "boundaries": {
            "boundaries": [
                {
                    "cutoff_utc": "2026-09-10T13:00:00Z",
                    "report_id": "monitor-report-1",
                    "message_ids": ["424242"],
                    "delivery_states": ["confirmed"],
                    "narration_count": 1,
                }
            ]
        },
        "idle": {"idle_confirmed": True},
        "restore": {"scope_removed": True, "enabled_restored": True},
        "errors": [],
    }

    public = module._public_live_summary(record)

    rendered = json.dumps(public)
    for private in ("424242", "monitor-report-1", "/private/operator", "2026-09-10T13:00:00Z"):
        assert private not in rendered, private
    assert public["boundaries_observed"] == 1
    assert public["confirmed_deliveries"] == 1
    assert public["narration_counts"] == [1]
    assert public["idle_confirmed"] is True
    assert public["scope_restored"] is True
    assert "Bot API acceptance" in public["acceptance_notice"]
