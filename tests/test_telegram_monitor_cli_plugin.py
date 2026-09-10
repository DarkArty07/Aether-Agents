"""``aether monitor`` CLI, native control tool and plugin packaging (MON-05).

The deterministic half uses a Hermes-free manager interpreter and a disposable monitor
state root.  The ``hermes_exact`` half runs against the release-locked public Hermes
checkout to prove the real cron/plugin/toolset interfaces the monitor registers.
"""

from __future__ import annotations

import configparser
import hashlib
import importlib.util
import json
import os
import shutil
import sqlite3
import stat
import subprocess
import sys
import textwrap
import zipfile
from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace
from typing import Any, Mapping, Sequence

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
    boundary_action = next(
        action for action in parser._actions if "--wait-hourly-boundaries" in action.option_strings
    )
    assert module.REQUIRED_WAIT_HOURLY_BOUNDARIES == 2
    assert not hasattr(module, "MAX_WAIT_HOURLY_BOUNDARIES")
    assert "1-24" not in boundary_action.help
    assert "fixed at exactly 2" in boundary_action.help


def test_output_help_states_the_bounded_directory_binding() -> None:
    """The `--output` help names both bounded outcomes (round-9 review finding).

    The help text may not promise that every parent rename or replacement ends with no
    write: a rename after the write's directory descriptor is bound leaves the receipt
    inside the established directory and fails the run with ``private-output``.
    """

    module = _qualification_module()
    action = next(
        item for item in module._build_parser()._actions if "--output" in item.option_strings
    )
    help_text = " ".join((action.help or "").split())

    assert "output-unsafe-target" in help_text
    assert "private-output" in help_text
    assert "cannot redirect the write" in help_text
    # The audited absolute claim must not return: only the pre-binding case is refused
    # without a write.
    assert (
        "renamed or replaced at the same name fails the run with output-unsafe-target"
        not in help_text
    )


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
    """Missing output, invalid bounds, unsafe targets and repo-internal output fail closed."""

    missing_output = _run_qualification(tmp_path, "--live", "--json")
    assert missing_output.returncode == 2
    assert "--live requires --output" in missing_output.stderr

    relative_output = _run_qualification(
        tmp_path, "--live", "--output", "receipts/should-not-exist.json", "--json"
    )
    assert relative_output.returncode == 1
    relative_envelope = json.loads(relative_output.stdout)
    assert relative_envelope["ok"] is False
    assert relative_envelope["error"]["code"] == "output-not-absolute"
    assert not (ROOT / "receipts").exists()

    for value in ("0", "1", "3", "24", "25", "not-a-number"):
        bounded = _run_qualification(tmp_path, "--wait-hourly-boundaries", value, "--json")
        assert bounded.returncode == 2, value

    inside = ROOT / "qualification-should-not-exist.json"
    repository_output = _run_qualification(tmp_path, "--live", "--output", str(inside), "--json")
    assert repository_output.returncode == 1
    envelope = json.loads(repository_output.stdout)
    assert envelope["ok"] is False
    assert envelope["error"]["code"] in {"output-inside-repository", "runtime-unavailable"}
    assert not inside.exists()

    other_repo = tmp_path / "another-repo"
    other_repo.mkdir()
    subprocess.run(["git", "init", "-q", str(other_repo)], check=True)
    foreign_output = _run_qualification(
        tmp_path, "--live", "--output", str(other_repo / "receipts.json"), "--json"
    )
    assert foreign_output.returncode == 1
    assert json.loads(foreign_output.stdout)["error"]["code"] == "output-inside-repository"
    assert not (other_repo / "receipts.json").exists()

    # The complete private receipt target is validated before the lane: a non-literal
    # spelling, an operator-owned directory that is not already private, and an existing
    # file are all refused in the child process without creating or changing anything.
    traversal = tmp_path / "escape" / ".." / "receipts.json"
    traversal_output = _run_qualification(tmp_path, "--live", "--output", str(traversal), "--json")
    assert traversal_output.returncode == 1
    assert json.loads(traversal_output.stdout)["error"]["code"] == "output-unsafe-target"
    assert not (tmp_path / "receipts.json").exists()

    shared = tmp_path / "shared-parent"
    shared.mkdir()
    os.chmod(shared, 0o755)
    shared_output = _run_qualification(
        tmp_path, "--live", "--output", str(shared / "receipts.json"), "--json"
    )
    assert shared_output.returncode == 1
    assert json.loads(shared_output.stdout)["error"]["code"] == "output-parent-not-private"
    assert stat.S_IMODE(os.stat(shared).st_mode) == 0o755
    assert not (shared / "receipts.json").exists()

    occupied = tmp_path / "operator-receipt.json"
    occupied.write_text("operator receipt\n", encoding="utf-8")
    occupied_output = _run_qualification(tmp_path, "--live", "--output", str(occupied), "--json")
    assert occupied_output.returncode == 1
    assert json.loads(occupied_output.stdout)["error"]["code"] == "output-target-exists"
    assert occupied.read_text(encoding="utf-8") == "operator receipt\n"

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


def test_boundary_count_is_fixed_at_two_at_the_entry_point(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """Only exactly two boundaries reaches the live lane; every other count is refused."""

    module = _qualification_module()
    calls: list[int] = []

    def tripwire(args: Any, stream: Any) -> dict[str, Any]:
        calls.append(int(args.wait_hourly_boundaries))
        return {"public_summary": {"qualified": False}}

    monkeypatch.setattr(module, "run_live", tripwire)
    scratch = tmp_path / "scratch-tmp"
    scratch.mkdir()
    monkeypatch.setenv("TMPDIR", str(scratch))
    output = tmp_path / "private" / "receipt.json"

    for value in ("-1", "0", "1", "3", "24", "25"):
        code = module.main(
            ["--live", "--output", str(output), "--wait-hourly-boundaries", value, "--json"]
        )
        captured = capsys.readouterr()
        assert code == 2, value
        assert "wait-hourly-boundaries is fixed at exactly 2" in captured.err, value
        assert captured.out == "", value
    assert calls == []
    assert not output.exists()
    assert not (tmp_path / "private").exists()
    assert not list(scratch.iterdir())

    # Positive control: the tripwire is reachable, so the refusals above are real.
    accepted = module.main(
        ["--live", "--output", str(output), "--wait-hourly-boundaries", "2", "--json"]
    )
    assert accepted == 1  # the stub is not a real qualification
    assert calls == [2]
    assert not output.exists()
    assert not list(scratch.iterdir())


def test_git_containment_rejects_every_worktree_or_repository(tmp_path: Path) -> None:
    """A receipt inside any Git worktree (not only this checkout) is refused."""

    module = _qualification_module()

    assert module._inside_repository(tmp_path / "private" / "receipts.json") is False
    assert module._inside_repository(ROOT) is True
    assert module._inside_repository(ROOT / "scripts") is True

    repo = tmp_path / "another-repo"
    nested = repo / "work" / "nested"
    nested.mkdir(parents=True)
    subprocess.run(["git", "init", "-q", str(repo)], check=True)
    assert module._inside_repository(nested / "receipts.json") is True

    primary = module._primary_checkout_root()
    if primary is not None:
        # The linked worktree's primary checkout is not an ancestor of this path; it
        # must still be refused.
        assert module._inside_repository(primary / "private" / "receipts.json") is True


def test_live_entry_point_never_prints_private_paths_or_handles(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """The real entry point prints only the sanitized public summary."""

    module = _qualification_module()
    private_output = tmp_path / "private" / "receipts.json"
    record: dict[str, Any] = {
        "schema_version": "aether.telegram-monitor.qualification.v1",
        "mode": "live",
        "candidate_revision": "0" * 40,
        "runtime_interpreter": "/private/operator/runtime/python3",
        "output_file": str(private_output),
        "environment": {"gaps": []},
        "enable": {
            "job_id": "native-job-7",
            "shape_ok": True,
            "second_enable_same_job": True,
            "named_job_count": 1,
        },
        "boundaries": [
            {
                "cutoff_utc": "2026-09-10T14:00:00.000000Z",
                "collected_at_utc": "2026-09-10T14:00:40.000000Z",
                "collected_lateness_seconds": 40.0,
                "narration_status": "accepted",
                "narration_writes": 1,
                "narration_lateness_seconds": 60.0,
                "ack_lateness_seconds": 90.0,
                "delivery_states": ["confirmed"],
                "part_count": 1,
                "message_ids": ["424242"],
                "report_id": "monitor-report-1",
                "work_keys": ["pipeline:private", "direct:private"],
                "native_run_files": 1,
                "payload_items": {"pipeline:private": {"work_key": "pipeline:private"}},
                "narrative_items": {},
                "source_facts": {},
            }
        ],
        "cases": [{"id": "direct-no-contract", "status": "observed", "detail": "ok"}],
        "semantic_adjudication": {
            "required": True,
            "certified": False,
            "cases": ["direct-no-contract"],
            "retained_private_comparison": True,
        },
        "idle": {"idle_confirmed": True},
        "off": {"job_paused": True, "enabled_after_off": False},
        "restore": {
            "scope_removed": True,
            "registry_restored": "byte-identical",
            "enabled_restored": True,
            "unrelated_jobs_preserved": True,
        },
        "errors": [],
        "ok": True,
    }
    record["public_summary"] = module._public_live_summary(record)
    monkeypatch.setattr(module, "run_live", lambda args, stream: record)

    code = module.main(["--live", "--json", "--output", str(private_output)])
    captured = capsys.readouterr()

    assert code == 0, captured.err
    payload = json.loads(captured.out)
    rendered = json.dumps(payload)
    assert payload["ok"] is True and payload["qualified"] is True
    for private in (
        "424242",
        "monitor-report-1",
        "/private/operator",
        str(private_output),
        "native-job-7",
        "2026-09-10T14:00:00.000000Z",
        "pipeline:private",
        "qualification-origin",
    ):
        assert private not in rendered, private

    code = module.main(["--live", "--output", str(private_output)])
    captured = capsys.readouterr()
    assert code == 0, captured.err
    assert str(private_output) not in captured.out
    assert "private receipts written to the operator-selected --output file" in captured.out


# ---------------------------------------------------------------------------
# Live lane oracles (fake store and native evidence)
# ---------------------------------------------------------------------------

EXPECTED_CUT = "2026-09-10T14:00:00.000000Z"
BASELINE_REPORTS = frozenset({"rpt_baseline"})
PROJECT_ID = "11111111-1111-4111-8111-111111111111"
CONTRACT_ID = "oc_abcdef0123456789"
ORIGIN_SESSION = "qualification-origin-unit-a"


class _FakeSettings:
    def __init__(self, *, enabled: bool = True, last_cutoff_utc: str | None = None) -> None:
        self.enabled = enabled
        self.last_cutoff_utc = last_cutoff_utc
        self.native_job_id = "native-job-1"
        self.first_enabled_at_utc = None


def _fake_snapshot(
    report_id: str,
    cutoff: str,
    *,
    collected: str | None = None,
    payload: Mapping[str, Any] | None = None,
    gaps: tuple[str, ...] = (),
    resolved: str | None = None,
    previous: str | None = None,
) -> Any:
    return SimpleNamespace(
        report_id=report_id,
        cutoff_utc=cutoff,
        previous_cutoff_utc=previous,
        collected_at_utc=collected or cutoff,
        payload=payload if payload is not None else {"items": []},
        coverage_gaps=gaps,
        resolved_at_utc=resolved,
    )


def _fake_narrative(
    report_id: str,
    *,
    status: str = "accepted",
    created: str = "2026-09-10T14:00:20.000000Z",
    updated: str | None = None,
    result: Mapping[str, Any] | None = None,
) -> Any:
    return SimpleNamespace(
        report_id=report_id,
        structured_result=(
            result
            if result is not None
            else {
                "schema_version": "aether.telegram-monitor.narrative.v1",
                "report_id": report_id,
                "items": [],
            }
        ),
        narrator_session_id="cron_native-job-1_test",
        attempt_status=status,
        created_at_utc=created,
        updated_at_utc=updated or created,
    )


def _fake_delivery(
    index: int,
    state: str,
    *,
    message_id: str | None = "424242",
    updated: str = "2026-09-10T14:00:40.000000Z",
    text_hash: str = "0" * 64,
) -> Any:
    return SimpleNamespace(
        part_index=index,
        state=state,
        attempts=1,
        updated_at_utc=updated,
        message_id=message_id,
        text_hash=text_hash,
        report_id="rpt_new",
    )


class _FakeMonitorStore:
    def __init__(
        self,
        *,
        settings: _FakeSettings,
        snapshots: Sequence[Any],
        narratives: Mapping[str, Any] | None = None,
        deliveries: Mapping[str, Sequence[Any]] | None = None,
    ) -> None:
        self._settings = settings
        self._snapshots = tuple(snapshots)
        self._narratives = dict(narratives or {})
        self._deliveries = {key: tuple(value) for key, value in (deliveries or {}).items()}

    def get_settings(self) -> Any:
        return self._settings

    def list_snapshots(self, *, limit: int | None = None) -> tuple[Any, ...]:
        return self._snapshots

    def get_narrative(self, report_id: str) -> Any:
        return self._narratives.get(report_id)

    def list_deliveries(self, report_id: str) -> tuple[Any, ...]:
        return self._deliveries.get(report_id, ())


def test_boundary_gate_rejects_stale_scopes_and_mixed_deliveries() -> None:
    """Only a fresh, fully confirmed, correctly bound real cut can count."""

    module = _qualification_module()
    baseline = BASELINE_REPORTS

    historical = _FakeMonitorStore(
        settings=_FakeSettings(last_cutoff_utc="2026-09-10T13:00:00.000000Z"),
        snapshots=[
            _fake_snapshot("rpt_13", "2026-09-10T13:00:00.000000Z"),
            _fake_snapshot("rpt_12", "2026-09-10T12:00:00.000000Z"),
        ],
    )
    decision = module._inspect_boundary(
        historical,
        expected_cutoff_utc=EXPECTED_CUT,
        baseline_report_ids=baseline,
        enable_time_utc="2026-09-10T12:30:00Z",
    )
    assert decision["state"] == "waiting"

    preexisting = _FakeMonitorStore(
        settings=_FakeSettings(last_cutoff_utc=EXPECTED_CUT),
        snapshots=[_fake_snapshot("rpt_baseline", EXPECTED_CUT)],
    )
    decision = module._inspect_boundary(
        preexisting,
        expected_cutoff_utc=EXPECTED_CUT,
        baseline_report_ids=baseline,
        enable_time_utc="2026-09-10T12:30:00Z",
    )
    assert decision["state"] == "waiting"

    collected_before_enable = _FakeMonitorStore(
        settings=_FakeSettings(last_cutoff_utc=EXPECTED_CUT),
        snapshots=[
            _fake_snapshot("rpt_old", EXPECTED_CUT, collected="2026-09-10T12:00:30.000000Z")
        ],
    )
    decision = module._inspect_boundary(
        collected_before_enable,
        expected_cutoff_utc=EXPECTED_CUT,
        baseline_report_ids=baseline,
        enable_time_utc="2026-09-10T12:30:00Z",
    )
    assert decision["state"] == "missed"

    missed = _FakeMonitorStore(
        settings=_FakeSettings(last_cutoff_utc="2026-09-10T15:00:00.000000Z"),
        snapshots=[],
    )
    decision = module._inspect_boundary(
        missed,
        expected_cutoff_utc=EXPECTED_CUT,
        baseline_report_ids=baseline,
        enable_time_utc="2026-09-10T12:30:00Z",
    )
    assert decision["state"] == "missed"

    pending = _FakeMonitorStore(
        settings=_FakeSettings(last_cutoff_utc=EXPECTED_CUT),
        snapshots=[_fake_snapshot("rpt_new", EXPECTED_CUT)],
        narratives={"rpt_new": _fake_narrative("rpt_new", status="pending")},
    )
    decision = module._inspect_boundary(
        pending,
        expected_cutoff_utc=EXPECTED_CUT,
        baseline_report_ids=baseline,
        enable_time_utc="2026-09-10T12:30:00Z",
    )
    assert decision["state"] == "waiting"

    for status in ("rejected", "failed"):
        broken = _FakeMonitorStore(
            settings=_FakeSettings(last_cutoff_utc=EXPECTED_CUT),
            snapshots=[_fake_snapshot("rpt_new", EXPECTED_CUT)],
            narratives={"rpt_new": _fake_narrative("rpt_new", status=status)},
        )
        decision = module._inspect_boundary(
            broken,
            expected_cutoff_utc=EXPECTED_CUT,
            baseline_report_ids=baseline,
            enable_time_utc="2026-09-10T12:30:00Z",
        )
        assert decision["state"] == "narration-failed", status

    mixed = _FakeMonitorStore(
        settings=_FakeSettings(last_cutoff_utc=EXPECTED_CUT),
        snapshots=[_fake_snapshot("rpt_new", EXPECTED_CUT)],
        narratives={"rpt_new": _fake_narrative("rpt_new")},
        deliveries={"rpt_new": [_fake_delivery(0, "confirmed"), _fake_delivery(1, "failed")]},
    )
    decision = module._inspect_boundary(
        mixed,
        expected_cutoff_utc=EXPECTED_CUT,
        baseline_report_ids=baseline,
        enable_time_utc="2026-09-10T12:30:00Z",
    )
    assert decision["state"] == "delivery-failed"

    confirmed = _FakeMonitorStore(
        settings=_FakeSettings(last_cutoff_utc=EXPECTED_CUT),
        snapshots=[_fake_snapshot("rpt_new", EXPECTED_CUT)],
        narratives={"rpt_new": _fake_narrative("rpt_new")},
        deliveries={"rpt_new": [_fake_delivery(0, "confirmed")]},
    )
    decision = module._inspect_boundary(
        confirmed,
        expected_cutoff_utc=EXPECTED_CUT,
        baseline_report_ids=baseline,
        enable_time_utc="2026-09-10T12:30:00Z",
    )
    assert decision["state"] == "ready"


def _live_payload(
    *,
    report_id: str = "rpt_" + "a" * 32,
    cutoff: str = EXPECTED_CUT,
    previous: str = "2026-09-10T13:00:00.000000Z",
    collected: str = "2026-09-10T14:00:30.000000Z",
) -> dict[str, Any]:
    from aether_agents.monitor.collector import build_bounded_snapshot
    from aether_agents.monitor.sources import SourceCollection, SourceItem

    ref = "board:oc-unit:task:t_00000001:title"
    item = SourceItem(
        work_key=f"pipeline:{PROJECT_ID}:{CONTRACT_ID}:{ORIGIN_SESSION}",
        project_id=PROJECT_ID,
        project_name="Synthetic qualification (unit)",
        origin_session_id=ORIGIN_SESSION,
        origin_session_title="Synthetic qualification origin session A",
        contract={
            "id": CONTRACT_ID,
            "version": "v1",
            "title": "Synthetic qualification objective A",
        },
        observed_state="running",
        current=(
            {
                "ref": ref,
                "text": "Synthetic root decomposition is active.",
                "provenance": "observed",
                "status": "verified",
            },
        ),
        active=True,
    )
    return build_bounded_snapshot(
        report_id=report_id,
        cutoff_utc=cutoff,
        collected_at_utc=collected,
        previous_cutoff_utc=previous,
        source=SourceCollection(items=(item,), watermarks={}, coverage_gaps=()),
    )


def _live_narrative(payload: Mapping[str, Any]) -> dict[str, Any]:
    item = payload["items"][0]
    claim = item["current"][0]
    return {
        "schema_version": "aether.telegram-monitor.narrative.v1",
        "report_id": payload["report_id"],
        "items": [
            {
                "work_key": item["work_key"],
                "resolved": [],
                "current": [{"ref": claim["ref"], "text": claim["text"]}],
                "next": [],
                "complications": [],
                "pending": [],
                "status": "running",
            }
        ],
    }


def _confirmed_decision(payload: Mapping[str, Any], narrative: Mapping[str, Any]) -> Any:
    module = _qualification_module()
    from aether_agents.monitor import reporting as reporting_module

    parts = reporting_module.render_parts(payload, narrative)
    deliveries = [
        _fake_delivery(
            index,
            "confirmed",
            text_hash=hashlib.sha256(part.encode("utf-8")).hexdigest(),
        )
        for index, part in enumerate(parts)
    ]
    snapshot = _fake_snapshot(
        payload["report_id"], EXPECTED_CUT, payload=payload, collected=payload["collected_at_utc"]
    )
    return {
        "state": "ready",
        "snapshot": snapshot,
        "narrative": _fake_narrative(payload["report_id"], result=narrative),
        "deliveries": deliveries,
        "module": module,
    }


def _run_evidence(report_id: str, *, count: int = 1, silent: bool = False) -> dict[str, Any]:
    return {
        "available": True,
        "count": count,
        "silent": silent,
        "contents": [{"name": "run.md", "text": f"digest {report_id}"}] * count,
    }


def _job_record(**overrides: Any) -> dict[str, Any]:
    record = {
        "last_run_at": "2026-09-10T14:00:05.000000Z",
        "last_status": "ok",
        "last_error": None,
        "paused": False,
    }
    record.update(overrides)
    return record


def test_boundary_record_binds_a_real_run_and_a_single_narration() -> None:
    """A boundary is certified only by its own native run, single narration and parts."""

    module = _qualification_module()
    payload = _live_payload()
    narrative = _live_narrative(payload)
    work_key = payload["items"][0]["work_key"]
    expected_items = {work_key: "running"}

    decision = _confirmed_decision(payload, narrative)
    boundary = module._boundary_record(
        decision,
        expected_items=expected_items,
        expected_gaps=frozenset(),
        language=None,
        job_record=_job_record(),
        run_evidence=_run_evidence(payload["report_id"]),
        expected_cutoff_utc=EXPECTED_CUT,
    )
    assert boundary["narration_writes"] == 1
    assert boundary["delivery_states"] == ["confirmed"]
    assert boundary["work_keys"] == [work_key]
    assert boundary["part_count"] == 1
    assert boundary["native_run_files"] == 1
    assert boundary["message_ids"] == ["424242"]

    def fail_with(**changes: Any) -> str:
        decision_value = _confirmed_decision(payload, narrative)
        expected = dict(expected_items)
        gaps = frozenset()
        job = _job_record()
        evidence = _run_evidence(payload["report_id"])
        if "expected" in changes:
            expected = changes["expected"]
        if "gaps" in changes:
            gaps = changes["gaps"]
        if "job" in changes:
            job = changes["job"]
        if "evidence" in changes:
            evidence = changes["evidence"]
        if "narrative" in changes:
            decision_value["narrative"] = changes["narrative"]
        if "deliveries" in changes:
            decision_value["deliveries"] = changes["deliveries"]
        with pytest.raises(module.QualificationError) as error:
            module._boundary_record(
                decision_value,
                expected_items=expected,
                expected_gaps=gaps,
                language=None,
                job_record=job,
                run_evidence=evidence,
                expected_cutoff_utc=EXPECTED_CUT,
            )
        return error.value.code

    assert fail_with(expected={work_key: "review"}) == "scope-state"
    assert fail_with(expected={"pipeline:other": "running"}) == "scope-items"
    assert fail_with(gaps=frozenset({"UNEXPECTED_GAP"})) == "scope-gaps"
    assert (
        fail_with(
            narrative=_fake_narrative(
                payload["report_id"],
                result=narrative,
                created="2026-09-10T14:00:20.000000Z",
                updated="2026-09-10T14:00:35.000000Z",
            )
        )
        == "multiple-narrations"
    )
    assert (
        fail_with(deliveries=[_fake_delivery(0, "confirmed", message_id=None)])
        == "delivery-unconfirmed"
    )
    assert fail_with(evidence={"available": False, "count": 0, "silent": False}) == (
        "native-run-evidence"
    )
    assert fail_with(evidence=_run_evidence(payload["report_id"], count=2)) == "native-run-count"
    assert (
        fail_with(
            evidence={
                "available": True,
                "count": 1,
                "silent": False,
                "contents": [{"name": "run.md", "text": "some other digest"}],
            }
        )
        == "native-run-content"
    )
    assert (
        fail_with(job=_job_record(last_run_at="2026-09-10T13:59:00.000000Z")) == "native-job-state"
    )
    assert fail_with(job=_job_record(last_status="error")) == "native-job-state"


def test_idle_gate_requires_the_native_skip_and_no_new_inference() -> None:
    """The idle cut must be a resolved silent native run with no narration anywhere."""

    module = _qualification_module()

    def store(**overrides: Any) -> Any:
        payload: dict[str, Any] = {"items": [], "coverage_gaps": [], "report_id": "rpt_idle"}
        settings = _FakeSettings(last_cutoff_utc=EXPECTED_CUT)
        snapshots = [
            _fake_snapshot(
                "rpt_idle",
                EXPECTED_CUT,
                payload=payload,
                resolved="2026-09-10T15:00:30.000000Z",
            )
        ]
        narratives = overrides.get("narratives")
        deliveries = overrides.get("deliveries")
        return _FakeMonitorStore(
            settings=settings,
            snapshots=snapshots,
            narratives=narratives,
            deliveries=deliveries,
        )

    ready = module._inspect_idle(
        store(),
        expected_cutoff_utc=EXPECTED_CUT,
        baseline_report_ids=BASELINE_REPORTS,
        baseline_sessions=frozenset(),
        session_sources={"sess_existing": {"source": "tui"}},
        job_record=_job_record(),
        run_evidence=_run_evidence("rpt_idle", silent=True),
        handoff_directory=None,
    )
    assert ready["state"] == "ready"

    # The reviewer's reproduced false positive: a fresh rejected narrative is a real
    # model turn and must never be reported as an idle skip.
    rejected = module._inspect_idle(
        store(narratives={"rpt_idle": _fake_narrative("rpt_idle", status="rejected")}),
        expected_cutoff_utc=EXPECTED_CUT,
        baseline_report_ids=BASELINE_REPORTS,
        baseline_sessions=frozenset(),
        session_sources={"sess_existing": {"source": "tui"}},
        job_record=_job_record(),
        run_evidence=_run_evidence("rpt_idle", silent=True),
        handoff_directory=None,
    )
    assert rejected["state"] == "failed"

    pending = module._inspect_idle(
        store(narratives={"rpt_idle": _fake_narrative("rpt_idle", status="pending")}),
        expected_cutoff_utc=EXPECTED_CUT,
        baseline_report_ids=BASELINE_REPORTS,
        baseline_sessions=frozenset(),
        session_sources={"sess_existing": {"source": "tui"}},
        job_record=_job_record(),
        run_evidence=_run_evidence("rpt_idle", silent=True),
        handoff_directory=None,
    )
    assert pending["state"] == "failed"

    not_silent = module._inspect_idle(
        store(),
        expected_cutoff_utc=EXPECTED_CUT,
        baseline_report_ids=BASELINE_REPORTS,
        baseline_sessions=frozenset(),
        session_sources={"sess_existing": {"source": "tui"}},
        job_record=_job_record(),
        run_evidence=_run_evidence("rpt_idle"),
        handoff_directory=None,
    )
    assert not_silent["state"] == "failed"

    new_reporter = module._inspect_idle(
        store(),
        expected_cutoff_utc=EXPECTED_CUT,
        baseline_report_ids=BASELINE_REPORTS,
        baseline_sessions=frozenset(),
        session_sources={"cron_native-job-1_2": {"source": "cron"}},
        job_record=_job_record(),
        run_evidence=_run_evidence("rpt_idle", silent=True),
        handoff_directory=None,
    )
    assert new_reporter["state"] == "failed"

    not_yet = module._inspect_idle(
        store(),
        expected_cutoff_utc=EXPECTED_CUT,
        baseline_report_ids=BASELINE_REPORTS,
        baseline_sessions=frozenset(),
        session_sources={"sess_existing": {"source": "tui"}},
        job_record=_job_record(last_run_at="2026-09-10T13:59:00.000000Z"),
        run_evidence=_run_evidence("rpt_idle", silent=True),
        handoff_directory=None,
    )
    assert not_yet["state"] == "waiting"

    # A reporter session from the already observed worked cuts is not a new turn.
    worked_cuts_only = module._inspect_idle(
        store(),
        expected_cutoff_utc=EXPECTED_CUT,
        baseline_report_ids=BASELINE_REPORTS,
        baseline_sessions=frozenset({"cron_native-job-1_1", "cron_native-job-1_2"}),
        session_sources={
            "cron_native-job-1_1": {"source": "cron"},
            "cron_native-job-1_2": {"source": "cron"},
        },
        job_record=_job_record(),
        run_evidence=_run_evidence("rpt_idle", silent=True),
        handoff_directory=None,
    )
    assert worked_cuts_only["state"] == "ready"


def test_d12_live_corpus_cannot_pass_without_live_evidence() -> None:
    """Every semantic case compares the actual narrative with canonical source state."""

    module = _qualification_module()
    work_key = f"pipeline:{PROJECT_ID}:{CONTRACT_ID}:{ORIGIN_SESSION}"
    fixture_ref = "board:oc-unit:task:t_00000001:result"
    fixture_fact = {
        "ref": fixture_ref,
        "text": "Phase one checks are complete and everything is green.",
        "provenance": "reported",
        "status": "unverified",
        "work_key": work_key,
        "section": "current",
    }
    payload_item = {
        "work_key": work_key,
        "observed_state": "running",
        "contract": {"id": CONTRACT_ID, "version": "v1", "title": "Synthetic"},
        "current": [dict(fixture_fact)],
    }
    boundary = {
        "payload_items": {work_key: payload_item},
        "narrative_items": {},
        "source_facts": {fixture_ref: fixture_fact},
    }
    case = {
        "id": "contradictory-completion",
        "boundary_index": 0,
        "work_key": work_key,
        "expected_state": "running",
        "fixture_ref": fixture_ref,
        "kind": "no-promotion",
        "tokens": ["everything is green"],
    }

    missing = module._evaluate_cases([case], [])
    assert missing[0]["status"] == "fail"

    boundary["narrative_items"] = {
        work_key: {
            "status": "completed",
            "current": [],
            "resolved": [],
            "next": [],
            "complications": [],
            "pending": [],
        }
    }
    promoted_state = module._evaluate_cases([case], [boundary])
    assert promoted_state[0]["status"] == "fail"

    boundary["narrative_items"] = {
        work_key: {
            "status": "running",
            "current": [
                {
                    "ref": fixture_ref,
                    "text": "Phase one checks are complete and everything is green.",
                    "provenance": "observed",
                    "status": "verified",
                }
            ],
            "resolved": [],
            "next": [],
            "complications": [],
            "pending": [],
        }
    }
    promoted_claim = module._evaluate_cases([case], [boundary])
    assert promoted_claim[0]["status"] == "fail"

    boundary["narrative_items"] = {
        work_key: {
            "status": "running",
            "current": [
                {
                    "ref": "board:oc-unit:task:t_00000001:title",
                    "text": "everything is green according to my own summary",
                    "provenance": "observed",
                    "status": "verified",
                }
            ],
            "resolved": [],
            "next": [],
            "complications": [],
            "pending": [],
        }
    }
    invented_token = module._evaluate_cases([case], [boundary])
    assert invented_token[0]["status"] == "fail"

    boundary["narrative_items"] = {
        work_key: {
            "status": "running",
            "current": [
                {
                    "ref": fixture_ref,
                    "text": "A worker reported phase one as complete; the flow is running.",
                    "provenance": "reported",
                    "status": "unverified",
                }
            ],
            "resolved": [],
            "next": [],
            "complications": [],
            "pending": [],
        }
    }
    faithful = module._evaluate_cases([case], [boundary])
    assert faithful[0]["status"] == "observed"
    assert faithful[0]["certification"] == "independent-adjudication-required"
    assert faithful[0]["expected_text"] == "Phase one checks are complete and everything is green."
    assert faithful[0]["cited_texts"] == [
        "A worker reported phase one as complete; the flow is running."
    ]

    completion_case = {
        "id": "between-cut-final",
        "boundary_index": 0,
        "work_key": work_key,
        "expected_state": "completed",
        "kind": "completion",
        "tokens": [],
    }
    completion_item = {
        "work_key": work_key,
        "observed_state": "completed",
        "contract": {"id": CONTRACT_ID, "version": "v1", "title": "Synthetic"},
        "resolved": [
            {
                "ref": f"{work_key}:closure",
                "text": "FLOW_TERMINAL_CONFIRMED",
                "provenance": "observed",
                "status": "verified",
            }
        ],
    }
    verified_ref = f"{work_key}:closure"
    boundary["payload_items"] = {work_key: completion_item}
    boundary["source_facts"] = {
        verified_ref: {
            "ref": verified_ref,
            "text": "FLOW_TERMINAL_CONFIRMED",
            "provenance": "observed",
            "status": "verified",
            "work_key": work_key,
            "section": "resolved",
        }
    }
    boundary["narrative_items"] = {
        work_key: {
            "status": "completed",
            "resolved": [],
            "current": [],
            "next": [],
            "complications": [],
            "pending": [],
        }
    }
    ungrounded = module._evaluate_cases([completion_case], [boundary])
    assert ungrounded[0]["status"] == "fail"

    boundary["narrative_items"] = {
        work_key: {
            "status": "completed",
            "resolved": [
                {
                    "ref": verified_ref,
                    "text": "Flow completion is confirmed by canonical evidence.",
                    "provenance": "observed",
                    "status": "verified",
                }
            ],
            "current": [],
            "next": [],
            "complications": [],
            "pending": [],
        }
    }
    grounded = module._evaluate_cases([completion_case], [boundary])
    assert grounded[0]["status"] == "observed"
    assert grounded[0]["certification"] == "independent-adjudication-required"
    assert grounded[0]["grounding_refs"] == [verified_ref]


def test_live_public_summary_excludes_private_handles_and_private_paths() -> None:
    """Only sanitized timings, counts and case results may leave a live run."""

    module = _qualification_module()
    record = {
        "candidate_revision": "0" * 40,
        "runtime_interpreter": "/private/operator/runtime/python3",
        "environment": {"gaps": []},
        "boundaries": [
            {
                "cutoff_utc": "2026-09-10T13:00:00Z",
                "report_id": "monitor-report-1",
                "message_ids": ["424242"],
                "delivery_states": ["confirmed"],
                "narration_status": "accepted",
                "narration_writes": 1,
                "collected_lateness_seconds": 41.0,
                "narration_lateness_seconds": 63.0,
                "ack_lateness_seconds": 88.0,
                "work_keys": ["pipeline:private"],
                "part_count": 2,
                "native_run_files": 1,
            }
        ],
        "cases": [
            {"id": "direct-no-contract", "status": "observed", "detail": "ok"},
            {"id": "between-cut-final", "status": "fail", "detail": "lost"},
        ],
        "semantic_adjudication": {
            "required": True,
            "certified": False,
            "cases": ["direct-no-contract"],
            "retained_private_comparison": True,
        },
        "idle": {"idle_confirmed": True},
        "restore": {
            "scope_removed": True,
            "direct_spool_clean": True,
            "enabled_restored": True,
            "registry_restored": "byte-identical",
        },
        "errors": [],
    }

    public = module._public_live_summary(record)

    rendered = json.dumps(public)
    for private in (
        "424242",
        "monitor-report-1",
        "/private/operator",
        "2026-09-10T13:00:00Z",
        "pipeline:private",
    ):
        assert private not in rendered, private
    assert public["boundaries_observed"] == 1
    assert public["confirmed_deliveries"] == 1
    assert public["narration_counts"] == [1]
    assert public["collection_lateness_seconds"] == [41.0]
    assert public["item_counts"] == [1]
    assert public["cases"] == {"direct-no-contract": "observed", "between-cut-final": "fail"}
    assert public["case_failures"] == ["between-cut-final"]
    assert public["semantic_certification"] == {
        "certified": False,
        "adjudication_required": ["direct-no-contract"],
        "retained_private_comparison": True,
    }
    assert public["direct_spool_cleaned"] is True
    assert public["idle_confirmed"] is True
    assert public["scope_restored"] is True
    assert "Bot API acceptance" in public["acceptance_notice"]


def test_live_state_fingerprint_uses_cutoff_and_relative_paths(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The harness resolves the operator state read-only and never creates it."""

    module = _qualification_module()
    monkeypatch.setenv("XDG_STATE_HOME", str(tmp_path / "xdg"))
    fingerprint = module._live_state_fingerprint()
    assert fingerprint == {}
    assert not (tmp_path / "xdg").exists()


# ---------------------------------------------------------------------------
# Live orchestration with injected backends (no external effect)
# ---------------------------------------------------------------------------

START = datetime(2026, 9, 10, 10, 5, tzinfo=timezone.utc)
STAMP = START.strftime("%Y%m%dT%H%M%SZ")
CUT_ONE = datetime(2026, 9, 10, 11, 0, tzinfo=timezone.utc)
CUT_TWO = datetime(2026, 9, 10, 12, 0, tzinfo=timezone.utc)
CUT_IDLE = datetime(2026, 9, 10, 13, 0, tzinfo=timezone.utc)
SMOKE_CUTOFF = datetime(2026, 9, 10, 10, 0, tzinfo=timezone.utc)
SYNTHETIC_JOB_ID = "native-job-qualification"
PRIOR_JOB_ID = "prior-job"


def _stamp(value: datetime) -> str:
    return value.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


class _PhaseClock:
    """A deterministic clock; ``sleep`` advances to the next qualification phase."""

    def __init__(self, start: datetime, phases: Sequence[datetime]) -> None:
        self.value = start
        self.phases = sorted(phases)
        self.sleeps = 0

    def now(self) -> datetime:
        return self.value

    def sleep(self, seconds: float) -> None:
        self.sleeps += 1
        pending = [phase for phase in self.phases if phase > self.value]
        self.value = pending[0] if pending else self.value + timedelta(seconds=seconds)


class _EvidenceStore:
    """A bounded monitor-store double with phase-revealed evidence."""

    def __init__(self, state_root: Path, clock: _PhaseClock, **settings: Any) -> None:
        self.state_root = state_root
        self.clock = clock
        self.snapshots: dict[str, Any] = {}
        self.narratives: dict[str, Any] = {}
        self.deliveries: dict[str, Any] = {}
        self.reveals: list[tuple[datetime, str, str]] = []  # reveal, cutoff text, report id
        self.configure_calls: list[dict[str, Any]] = []
        self.settings = SimpleNamespace(
            enabled=bool(settings.get("enabled", False)),
            native_job_id=settings.get("native_job_id"),
            profile_binding=settings.get("profile_binding"),
            destination_ref=settings.get("destination_ref"),
            timezone=settings.get("timezone", "UTC"),
            last_cutoff_utc=None,
            first_enabled_at_utc=None,
            paused_at_utc=None,
        )

    def expose(
        self,
        report_id: str,
        cutoff: datetime,
        *,
        payload: Mapping[str, Any],
        narrative: Any = None,
        deliveries: Sequence[Any] = (),
        reveal: datetime | None = None,
        resolved: bool = False,
        collected: datetime | None = None,
    ) -> None:
        self.snapshots[report_id] = SimpleNamespace(
            report_id=report_id,
            cutoff_utc=_stamp(cutoff),
            previous_cutoff_utc=None,
            collected_at_utc=_stamp(collected or (cutoff + timedelta(seconds=40))),
            payload=dict(payload),
            coverage_gaps=tuple(payload.get("coverage_gaps") or ()),
            resolved_at_utc=_stamp(cutoff + timedelta(minutes=1)) if resolved else None,
        )
        if narrative is not None:
            released = _stamp(cutoff + timedelta(minutes=1))
            self.narratives[report_id] = SimpleNamespace(
                report_id=report_id,
                structured_result=dict(narrative),
                narrator_session_id="cron_" + SYNTHETIC_JOB_ID + "_live",
                attempt_status="accepted",
                created_at_utc=released,
                updated_at_utc=released,
            )
        self.deliveries[report_id] = list(deliveries)
        self.reveals.append((reveal or cutoff, _stamp(cutoff), report_id))

    def get_settings(self) -> Any:
        visible = [item for item in self.reveals if item[0] <= self.clock.now()]
        if visible:
            latest = max(visible, key=lambda item: item[0])
            self.settings.last_cutoff_utc = latest[1]
        # The shipped surface returns a fresh settings value, never a live view.
        return SimpleNamespace(**vars(self.settings))

    def list_snapshots(self, *, limit: int | None = None) -> tuple[Any, ...]:
        visible = [
            self.snapshots[report_id]
            for reveal, _cutoff, report_id in self.reveals
            if reveal <= self.clock.now()
        ]
        ordered = list(reversed(visible))
        return tuple(ordered if limit is None else ordered[:limit])

    def get_narrative(self, report_id: str) -> Any:
        return self.narratives.get(report_id)

    def list_deliveries(self, report_id: str) -> tuple[Any, ...]:
        return tuple(self.deliveries.get(report_id, ()))

    def configure(self, **values: Any) -> Any:
        self.configure_calls.append(dict(values))
        for key in ("native_job_id", "profile_binding", "destination_ref", "timezone"):
            if key in values:
                setattr(self.settings, key, values[key])
        return self.settings


class _FakeBackends:
    """Every live boundary as a fake: no model, no sender, no native scheduler."""

    def __init__(
        self,
        *,
        module: Any,
        store: _EvidenceStore,
        clock: _PhaseClock,
        hermes_home: Path,
        worker: Path,
        scope_root: Path,
        output_dir: Path,
        enable_next_cut: datetime,
        inventory: Sequence[Mapping[str, Any]] = (),
    ) -> None:
        self.module = module
        self.store = store
        self.clock = clock
        self.hermes_home_value = hermes_home
        self.runtime = worker
        self.scope_root = scope_root
        self.output_dir = output_dir
        self.enable_next_cut = enable_next_cut
        self.jobs: dict[str, dict[str, Any]] = {str(job["id"]): dict(job) for job in inventory}
        self.calls: list[str] = []
        self.trigger_calls = 0
        self.environment_gap_values: list[str] = []
        self.trigger_result: dict[str, Any] = {"triggered": True, "errors": []}
        self.scope_failure: str | None = None
        self.scope_remove_errors: list[str] = []
        self.scope_remove_residue: list[str] = []
        self.scope_remove_verified: dict[str, bool] | None = None
        self.registry_restore_value = "byte-identical"
        self.fail_job_removal = False
        self.output_payloads: dict[str, Any] = {}
        self.output_parents: dict[str, Any] = {}
        self.job_last_run: dict[str, datetime] = {}

    def now(self) -> datetime:
        return self.clock.now()

    def sleep(self, seconds: float) -> None:
        self.calls.append(f"sleep:{seconds}")
        self.clock.sleep(seconds)

    def runtime_python(self) -> Path:
        self.calls.append("runtime_python")
        return self.runtime

    def candidate_revision(self) -> str:
        return "0" * 40

    def owner_language(self, interpreter: Path) -> str | None:
        return "English"

    def hermes_home(self) -> Path:
        return self.hermes_home_value

    def control(self, action: str) -> dict[str, Any]:
        self.calls.append(f"control:{action}")
        settings = self.store.settings
        if action == "on":
            existing = next(
                (job for job in self.jobs.values() if job["name"] == self.module.NATIVE_JOB_NAME),
                None,
            )
            created = existing is None
            job_id = str(existing["id"]) if existing is not None else SYNTHETIC_JOB_ID
            self.jobs[job_id] = {
                "id": job_id,
                "name": self.module.NATIVE_JOB_NAME,
                "paused": False,
                "behaviour_sha256": "monitor-job",
            }
            settings.enabled = True
            settings.native_job_id = job_id
            settings.profile_binding = "morfeo"
            settings.destination_ref = "pinned-destination"
            return {
                "result": {
                    "enabled": True,
                    "job_created": created,
                    "destination_pinned": True,
                    "profile_binding": "morfeo",
                    "next_cut_utc": _stamp(self.enable_next_cut),
                    "native_job": {"id": job_id, "schedule": "0 * * * *", "paused": False},
                }
            }
        settings.enabled = False
        for job in self.jobs.values():
            if job["name"] == self.module.NATIVE_JOB_NAME:
                job["paused"] = True
        return {
            "result": {
                "enabled": False,
                "job_paused": True,
                "paused_at_utc": _stamp(self.clock.now()),
            }
        }

    def job_inventory(self, interpreter: Path) -> list[dict[str, Any]]:
        self.calls.append("job_inventory")
        return [dict(job) for job in self.jobs.values()]

    def job_record(self, interpreter: Path, job_id: str) -> dict[str, Any] | None:
        self.calls.append(f"job_record:{job_id}")
        job = self.jobs.get(job_id)
        if job is None:
            return None
        # The native scheduler executes the owned job at each scheduled phase boundary.
        for phase in self.clock.phases:
            if phase <= self.clock.now():
                previous = self.job_last_run.get(job_id)
                self.job_last_run[job_id] = phase if previous is None else max(previous, phase)
        last_run = self.job_last_run.get(job_id)
        return {
            "id": job_id,
            "name": self.module.NATIVE_JOB_NAME,
            "script": self.module.PRECHECK_SCRIPT_NAME,
            "deliver": "local",
            "schedule": self.module.NATIVE_SCHEDULE,
            "expected_schedule": self.module.NATIVE_SCHEDULE,
            "enabled_toolsets": list(runtime_module.REPORTER_JOB_TOOLSETS),
            "expected_toolsets": list(runtime_module.REPORTER_JOB_TOOLSETS),
            "no_agent": False,
            "attach_to_session": False,
            "prompt_sha256": "prompt",
            "expected_prompt_sha256": "prompt",
            "model_set": False,
            "provider_set": False,
            "base_url_set": False,
            "origin_set": False,
            "skills_set": False,
            "context_from_set": False,
            "workdir_set": False,
            "monitor_script_set": False,
            "monitor_url_set": False,
            "next_run_at": _stamp(self.enable_next_cut),
            "last_run_at": _stamp(last_run) if last_run else None,
            "last_status": "ok" if last_run else None,
            "last_error": None,
            "paused": bool(job.get("paused")),
            "output_dir": str(self.output_dir),
        }

    def job_removed(self, interpreter: Path, job_id: str) -> bool:
        self.calls.append(f"job_removed:{job_id}")
        if self.fail_job_removal:
            return False
        return self.jobs.pop(job_id, None) is not None

    def trigger_job(self, interpreter: Path, job_id: str) -> dict[str, Any]:
        self.calls.append(f"trigger_job:{job_id}")
        self.trigger_calls += 1
        if not self.trigger_result.get("triggered"):
            return dict(self.trigger_result)
        # A real native trigger and its scheduler tick take a bounded amount of time.
        self.clock.value += timedelta(seconds=50)
        self.job_last_run[job_id] = self.clock.now()
        return dict(self.trigger_result)

    def scope_materialize(
        self,
        interpreter: Path,
        scope_root: Path,
        manifest: Sequence[dict[str, Any]],
        *,
        state_root: Path,
        hermes_home: Path,
        stream: Any,
    ) -> dict[str, Any]:
        self.calls.append("scope_materialize")
        if self.scope_failure is not None:
            raise self.module.QualificationError(self.scope_failure, "injected scope failure")
        # The fake native half: a native identity per project and one real board database
        # per synthetic board, so the between-cut transition writes to a real store.
        for entry in manifest:
            entry["native_project_id"] = f"native-{entry['letter'].lower()}"
            board_dir = self.hermes_home_value / "kanban" / "boards" / entry["board_slug"]
            board_dir.mkdir(parents=True, exist_ok=True)
            connection = sqlite3.connect(board_dir / "kanban.db")
            connection.executescript(self.module._BOARD_DDL)
            connection.commit()
            connection.close()
        return {"boards": [entry["board_slug"] for entry in manifest]}

    def scope_remove(self, interpreter: Path, scope: Mapping[str, Any]) -> dict[str, Any]:
        self.calls.append("scope_remove")
        if self.scope_root.exists():
            shutil.rmtree(self.scope_root, ignore_errors=True)
        errors = list(self.scope_remove_errors)
        verified: dict[str, bool] = {
            "project-rows": True,
            "boards": True,
            "project-paths": True,
            "session-rows": True,
            "scope-root": not self.scope_root.exists(),
        }
        if errors:
            verified["project-rows"] = False
        if self.scope_remove_verified is not None:
            verified.update(self.scope_remove_verified)
        return {
            "removed": ["scope"],
            "sessions_removed": [],
            "errors": errors,
            "residue": list(self.scope_remove_residue),
            "verified": verified,
        }

    def environment_gaps(self, store: Any) -> list[str]:
        self.calls.append("environment_gaps")
        return list(self.environment_gap_values)

    def session_sources(self, hermes_home: Path) -> dict[str, Any]:
        self.calls.append("session_sources")
        return {"sess-existing": {"source": "tui"}}

    def isolate_registry(self) -> dict[str, Any]:
        self.calls.append("isolate_registry")
        return {
            "path": self.store.state_root / "projects" / "registry.json",
            "original": b"{}",
        }

    def restore_registry(self, isolation: Mapping[str, Any] | None) -> str:
        self.calls.append("restore_registry")
        return self.registry_restore_value

    def write_output(
        self,
        path: Path,
        payload: Mapping[str, Any],
        *,
        established_parent: tuple[int, int] | None = None,
    ) -> None:
        self.calls.append("write_output")
        self.output_payloads[str(path)] = payload
        self.output_parents[str(path)] = established_parent
        self.module._write_private_output(path, payload, established_parent=established_parent)


def _pipeline_item(entry: Mapping[str, Any], *, state: str, final: bool = False) -> Any:
    """One synthetic pipeline identity shaped like the shipped source adapter."""

    from aether_agents.monitor.sources import SourceItem

    work_key = f"pipeline:{entry['project_id']}:{entry['contract_id']}:{entry['origin_session']}"
    current: list[dict[str, Any]] = []
    resolved: list[dict[str, Any]] = []
    for task in entry["tasks"]:
        fact = {
            "ref": f"board:{entry['board_slug']}:task:{task['task_id']}:result",
            "text": task["result"],
            "provenance": "reported",
            "status": "unverified",
        }
        (resolved if final else current).append(fact)
    if final:
        resolved.append(
            {
                "ref": f"{work_key}:closure",
                "text": "FLOW_TERMINAL_CONFIRMED",
                "provenance": "observed",
                "status": "verified",
            }
        )
    return SourceItem(
        work_key=work_key,
        project_id=entry["project_id"],
        project_name=entry["name"],
        origin_session_id=entry["origin_session"],
        origin_session_title=entry["origin_title"],
        contract={
            "id": entry["contract_id"],
            "version": "v1",
            "title": entry["contract_title"],
        },
        observed_state=state,
        resolved=tuple(resolved),
        current=tuple(current),
        active=not final,
    )


def _direct_item(entry: Mapping[str, Any], interval: Mapping[str, Any], state: str) -> Any:
    from aether_agents.monitor.sources import SourceItem

    ref = f"direct:{entry['project_id']}:{entry['direct']['session_id']}:{interval['interval_id']}"
    outcome = state.removeprefix("turn_ended_").upper()
    return SourceItem(
        work_key=ref,
        project_id=entry["project_id"],
        project_name=entry["name"],
        origin_session_id=entry["direct"]["session_id"],
        origin_session_title="Synthetic qualification direct session",
        contract=None,
        observed_state=state,
        current=(
            {
                "ref": f"{ref}:turn",
                "text": f"TURN_ENDED_{outcome}",
                "provenance": "observed",
                "status": "verified",
            },
        ),
        coverage_gaps=("DIRECT_OUTCOME_UNKNOWN",) if state == "turn_ended_unknown" else (),
        active=False,
    )


def _snapshot_payload(
    *,
    report_id: str,
    cutoff: datetime,
    items: Sequence[Any],
    gaps: Sequence[str] = (),
) -> dict[str, Any]:
    from aether_agents.monitor.collector import build_bounded_snapshot
    from aether_agents.monitor.sources import SourceCollection

    return build_bounded_snapshot(
        report_id=report_id,
        cutoff_utc=_stamp(cutoff),
        collected_at_utc=_stamp(cutoff + timedelta(seconds=40)),
        previous_cutoff_utc=None,
        source=SourceCollection(items=tuple(items), watermarks={}, coverage_gaps=tuple(gaps)),
    )


def _narrative_status(state: str) -> str:
    """The shipped mapping from a source lifecycle token to the narrative vocabulary."""

    from aether_agents.monitor import reporting

    return reporting._canonical_observed_state(state)


def _narrative(payload: Mapping[str, Any]) -> dict[str, Any]:
    """A faithful narrative: every canonical claim is carried with canonical labels."""

    items: list[dict[str, Any]] = []
    for item in payload["items"]:
        entry: dict[str, Any] = {
            "work_key": item["work_key"],
            # The narrative status vocabulary is the shipped closed lifecycle set.
            "status": _narrative_status(str(item["observed_state"])),
            "resolved": [],
            "current": [],
            "next": [],
            "complications": [],
            "pending": [],
        }
        for section in ("resolved", "current", "next", "complications", "pending"):
            entry[section] = [
                {
                    "ref": fact["ref"],
                    "text": fact["text"],
                    "provenance": fact.get("provenance", "observed"),
                    "status": fact.get("status", "verified"),
                }
                for fact in item.get(section) or ()
            ]
        items.append(entry)
    return {
        "schema_version": "aether.telegram-monitor.narrative.v1",
        "report_id": payload["report_id"],
        "items": items,
    }


def _confirmed_parts(payload: Mapping[str, Any], narrative: Mapping[str, Any]) -> list[Any]:
    from aether_agents.monitor import reporting as reporting_module

    parts = reporting_module.render_parts(payload, narrative)
    return [
        SimpleNamespace(
            part_index=index,
            state="confirmed",
            attempts=1,
            updated_at_utc=_stamp(CUT_ONE + timedelta(minutes=2)),
            message_id=f"9000{index}",
            text_hash=hashlib.sha256(part.encode("utf-8")).hexdigest(),
            report_id=payload["report_id"],
        )
        for index, part in enumerate(parts)
    ]


def _native_run(output_dir: Path, moment: datetime, *, report_id: str | None = None) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    path = output_dir / f"run-{int(moment.timestamp())}-{len(list(output_dir.glob('*.md')))}.md"
    text = (
        f"digest {report_id}"
        if report_id is not None
        else "Script gate returned `wakeAgent=False` — agent skipped."
    )
    path.write_text(text.replace("wakeAgent=False", "wakeAgent=false"), encoding="utf-8")
    stamp = moment.timestamp()
    os.utime(path, (stamp, stamp))
    return path


def _scope_manifest_for(tmp_path: Path) -> tuple[Path, list[dict[str, Any]]]:
    module = _qualification_module()
    state_root = tmp_path / "xdg-state" / "aether"
    scope_root = state_root / "monitor" / "qualification" / STAMP
    return scope_root, module._scope_manifest(scope_root, STAMP)


def _build_world(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    *,
    prior_enabled: bool = False,
    phases: Sequence[datetime] = (CUT_ONE, CUT_TWO, CUT_IDLE),
    expose_evidence: bool = True,
) -> dict[str, Any]:
    """One complete fake world whose phases mirror a real live qualification."""

    module = _qualification_module()
    monkeypatch.setenv("XDG_STATE_HOME", str(tmp_path / "xdg-state"))
    scope_root, manifest = _scope_manifest_for(tmp_path)
    clock = _PhaseClock(START, phases)
    store = _EvidenceStore(
        tmp_path / "xdg-state" / "aether",
        clock,
        enabled=prior_enabled,
        native_job_id=PRIOR_JOB_ID if prior_enabled else None,
        profile_binding="morfeo" if prior_enabled else None,
        destination_ref="pinned-destination" if prior_enabled else None,
    )
    hermes_home = tmp_path / "hermes-home"
    output_dir = tmp_path / "native-runs"
    inventory: list[Mapping[str, Any]] = [
        {
            "id": "unrelated-job",
            "name": "Unrelated",
            "paused": False,
            "behaviour_sha256": "unrelated",
        }
    ]
    if prior_enabled:
        inventory.append(
            {
                "id": PRIOR_JOB_ID,
                "name": module.NATIVE_JOB_NAME,
                "paused": True,
                "behaviour_sha256": "prior-monitor-job",
            }
        )
    world: dict[str, Any] = {
        "module": module,
        "manifest": manifest,
        "scope_root": scope_root,
        "clock": clock,
        "store": store,
        "hermes_home": hermes_home,
        "output_dir": output_dir,
    }
    backends = _FakeBackends(
        module=module,
        store=store,
        clock=clock,
        hermes_home=hermes_home,
        worker=tmp_path / "runtime-python",
        scope_root=scope_root,
        output_dir=output_dir,
        enable_next_cut=CUT_ONE,
        inventory=inventory,
    )
    world["backends"] = backends
    if expose_evidence:
        entry_a, entry_b = manifest
        interval_zero = entry_a["direct"]["intervals"][0]
        interval_one = entry_a["direct"]["intervals"][1]

        smoke_report = "rpt_" + "a" * 32
        smoke_payload = _snapshot_payload(
            report_id=smoke_report,
            cutoff=SMOKE_CUTOFF,
            items=(
                _pipeline_item(entry_a, state="running"),
                _pipeline_item(entry_b, state="review"),
                _direct_item(entry_a, interval_zero, "turn_ended_unknown"),
            ),
        )
        smoke_narrative = _narrative(smoke_payload)
        store.expose(
            smoke_report,
            SMOKE_CUTOFF,
            payload=smoke_payload,
            narrative=smoke_narrative,
            deliveries=_confirmed_parts(smoke_payload, smoke_narrative),
            reveal=START + timedelta(seconds=1),
            collected=START + timedelta(seconds=60),
        )
        _native_run(output_dir, START + timedelta(seconds=45), report_id=smoke_report)

        before_report = "rpt_" + "b" * 32
        before_payload = _snapshot_payload(
            report_id=before_report,
            cutoff=CUT_ONE,
            items=(
                _pipeline_item(entry_a, state="running"),
                _pipeline_item(entry_b, state="review"),
                _direct_item(entry_a, interval_zero, "turn_ended_unknown"),
            ),
        )
        before_narrative = _narrative(before_payload)
        store.expose(
            before_report,
            CUT_ONE,
            payload=before_payload,
            narrative=before_narrative,
            deliveries=_confirmed_parts(before_payload, before_narrative),
        )
        _native_run(output_dir, CUT_ONE + timedelta(seconds=5), report_id=before_report)

        after_report = "rpt_" + "c" * 32
        after_payload = _snapshot_payload(
            report_id=after_report,
            cutoff=CUT_TWO,
            items=(
                _pipeline_item(entry_a, state="completed", final=True),
                _pipeline_item(entry_b, state="completed", final=True),
                _direct_item(entry_a, interval_one, "turn_ended_completed"),
            ),
        )
        after_narrative = _narrative(after_payload)
        store.expose(
            after_report,
            CUT_TWO,
            payload=after_payload,
            narrative=after_narrative,
            deliveries=_confirmed_parts(after_payload, after_narrative),
        )
        _native_run(output_dir, CUT_TWO + timedelta(seconds=5), report_id=after_report)

        idle_report = "rpt_" + "d" * 32
        store.expose(
            idle_report,
            CUT_IDLE,
            payload={
                "schema_version": "aether.telegram-monitor.snapshot.v1",
                "report_id": idle_report,
                "cutoff_utc": _stamp(CUT_IDLE),
                "collected_at_utc": _stamp(CUT_IDLE + timedelta(seconds=30)),
                "previous_cutoff_utc": _stamp(CUT_TWO),
                "items": [],
                "coverage_gaps": [],
            },
            resolved=True,
        )
        _native_run(output_dir, CUT_IDLE + timedelta(seconds=4))
    return world


def _live_args(module: Any, output: Path) -> Any:
    return module._build_parser().parse_args(["--live", "--json", "--output", str(output)])


def _run_live(
    world: Mapping[str, Any],
    output: Path,
    *,
    established_parent: tuple[int, int] | None = None,
) -> dict[str, Any]:
    module = world["module"]
    if established_parent is None:
        # The production entry point always establishes the receipt target (and its
        # identity) before the orchestrator exists; the helper mirrors that ordering.
        established_parent = module._establish_private_output_target(output)
    return module._live_run(
        _live_args(module, output),
        sys.stderr,
        output=output,
        backends=world["backends"],
        store=world["store"],
        established_parent=established_parent,
    )


def test_live_backends_surface_is_fully_injectable() -> None:
    """Every live boundary the orchestration may cross is replaceable in a test."""

    module = _qualification_module()
    real = {name for name in dir(module.LiveBackends) if not name.startswith("_")}
    fake = {name for name in dir(_FakeBackends) if not name.startswith("_")}
    assert real <= fake


def test_scope_manifest_encodes_the_d12_corpus_without_crashing(tmp_path: Path) -> None:
    """The synthetic manifest carries the fixed corpus as case keys, not prose values."""

    scope_root, manifest = _scope_manifest_for(tmp_path)

    assert [entry["letter"] for entry in manifest] == ["A", "B"]
    project_a, project_b = manifest
    assert [task["case"] for task in project_a["tasks"]] == [
        "root",
        "contradictory",
        "deadline",
        "word_time",
        "malicious",
    ]
    assert [task["case"] for task in project_b["tasks"]] == ["review", "partial"]
    assert project_a["tasks"][1]["result"] == (
        "Phase one checks are complete and everything is green."
    )
    assert project_b["tasks"][1]["result"] == (
        "Partial success: three of five checks pass; the source review is still pending."
    )
    assert [task["status"] for task in project_b["tasks"]] == ["running", "review"]
    assert project_a["path"].startswith(str(scope_root))
    assert project_a["direct"]["intervals"][0]["outcome"] == "unknown"


def test_live_preflight_and_full_run_without_external_effects(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The whole live orchestration runs against fakes: enable, smoke, two cuts, idle."""

    world = _build_world(tmp_path, monkeypatch)
    backends = world["backends"]
    output = tmp_path / "private" / "receipt.json"

    record = _run_live(world, output)

    assert record["ok"] is True, record["errors"]
    assert record["environment"] == {"gaps": []}
    assert record["enable"]["named_job_count"] == 1
    assert record["enable"]["second_enable_same_job"] is True
    assert record["enable"]["shape_ok"] is True
    assert record["smoke"]["confirmed"] is True
    assert record["smoke"]["narration_writes"] == 1
    assert record["smoke"]["part_count"] == 3
    assert [len(boundary["work_keys"]) for boundary in record["boundaries"]] == [3, 3]
    assert [boundary["coverage_gaps"] for boundary in record["boundaries"]] == [[], []]
    assert sorted(record["boundaries"][0]["item_states"].values()) == [
        "review",
        "running",
        "turn_ended_unknown",
    ]
    assert sorted(record["boundaries"][1]["item_states"].values()) == [
        "completed",
        "completed",
        "turn_ended_completed",
    ]
    assert {case["id"]: case["status"] for case in record["cases"]} == {
        "contradictory-completion": "observed",
        "forecast-deadline": "observed",
        "word-based-time": "observed",
        "malicious-instructions": "observed",
        "partial-success-pending-review": "observed",
        "between-cut-final": "observed",
        "final-after-review": "observed",
        "direct-no-contract": "observed",
        "direct-between-cut-final": "observed",
    }
    assert all(
        case["certification"] == "independent-adjudication-required" for case in record["cases"]
    )
    assert record["semantic_adjudication"] == {
        "required": True,
        "certified": False,
        "cases": [case["id"] for case in record["cases"]],
        "retained_private_comparison": True,
    }
    assert record["idle"]["idle_confirmed"] is True
    assert record["off"]["enabled_after_off"] is False
    assert record["restore"]["scope_removed"] is True
    assert record["restore"]["direct_spool_clean"] is True
    assert record["restore"]["registry_restored"] == "byte-identical"
    assert record["restore"]["enabled_matches_prior"] is True
    assert record["restore"]["native_job_id_matches_prior"] is True
    assert record["restore"]["created_job_removed"] is True
    assert record["restore"]["unrelated_jobs_preserved"] is True
    assert backends.trigger_calls == 1
    order = backends.calls
    assert order.index("isolate_registry") < order.index("scope_materialize")
    assert order.index("environment_gaps") < order.index("control:on")
    assert order.index("trigger_job:" + SYNTHETIC_JOB_ID) < order.index("control:off")
    receipt = json.loads(output.read_text(encoding="utf-8"))
    assert receipt["boundaries"][0]["narrative_items"]
    assert receipt["boundaries"][0]["source_facts"]
    assert receipt["smoke"]["narrative_items"]
    # The private comparison the adjudication needs is retained per case.
    assert all("cited_texts" in case for case in receipt["cases"])
    assert all(("expected_text" in case) or ("expected_texts" in case) for case in receipt["cases"])
    public = receipt["public_summary"]
    rendered = json.dumps(public)
    for private in ("rpt_", "90000", "90001", str(output)):
        assert private not in rendered, private
    assert public["qualified"] is True
    assert public["smoke_confirmed"] is True
    assert public["job_identity_restored"] is True
    assert public["direct_spool_cleaned"] is True
    assert set(public["cases"].values()) == {"observed"}
    assert public["case_failures"] == []
    assert public["semantic_certification"]["certified"] is False
    assert set(public["semantic_certification"]["adjudication_required"]) == set(public["cases"])
    assert public["semantic_certification"]["retained_private_comparison"] is True
    assert any("deterministic" in entry for entry in public["qualified_scope"])
    assert any("adjudication" in entry for entry in public["unqualified_scope"])


def test_live_environment_preflight_refuses_installation_gaps(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A permanent installation gap refuses the qualification before any enable."""

    world = _build_world(tmp_path, monkeypatch)
    backends = world["backends"]
    output = tmp_path / "private" / "receipt.json"
    backends.environment_gap_values = [
        "BOARD_METADATA_UNREADABLE",
        "SESSION_TITLE_UNAVAILABLE",
    ]

    with pytest.raises(world["module"].QualificationError) as error:
        _run_live(world, output)

    assert error.value.code == "environment-gaps"
    assert "BOARD_METADATA_UNREADABLE" in error.value.message
    assert "control:on" not in backends.calls
    assert backends.trigger_calls == 0
    receipt = json.loads(output.read_text(encoding="utf-8"))
    assert receipt["ok"] is False
    assert receipt["restore"]["scope_removed"] is True
    assert receipt["restore"]["registry_restored"] == "byte-identical"


def test_live_scope_setup_failure_leaves_nothing_behind(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A failed native materialization is fully reversed from the manifest already held."""

    world = _build_world(tmp_path, monkeypatch, expose_evidence=False)
    backends = world["backends"]
    output = tmp_path / "private" / "receipt.json"
    backends.scope_failure = "scope-create"

    with pytest.raises(world["module"].QualificationError) as error:
        _run_live(world, output)

    assert error.value.code == "scope-create"
    assert backends.calls.count("scope_remove") == 1
    assert not world["scope_root"].exists()
    receipt = json.loads(output.read_text(encoding="utf-8"))
    assert receipt["restore"]["scope_removed"] is True
    assert receipt["restore"]["registry_restored"] == "byte-identical"


def test_live_restore_failures_are_qualification_gating(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Registry, scope, job-removal and identity restore failures all clear ``ok``."""

    world = _build_world(tmp_path, monkeypatch)
    backends = world["backends"]
    store = world["store"]
    output = tmp_path / "private" / "receipt.json"
    backends.registry_restore_value = "failed"
    backends.scope_remove_errors = ["RuntimeError: remove failed"]
    backends.fail_job_removal = True

    def fail_configure(**values: Any) -> Any:
        raise RuntimeError("configure failed")

    store.configure = fail_configure  # type: ignore[method-assign]

    record = _run_live(world, output)

    assert record["ok"] is False
    codes = {entry["code"] for entry in record["errors"]}
    assert {
        "restore-scope",
        "restore-registry",
        "restore-created-job",
        "restore-job-identity",
    } <= codes
    assert record["restore"]["scope_removed"] is False
    assert record["restore"]["created_job_removed"] is False
    assert record["restore"]["native_job_id_matches_prior"] is False
    public = record["public_summary"]
    assert public["qualified"] is False
    assert public["registry_restored"] == "failed"
    assert public["scope_restored"] is False
    assert public["created_job_removed"] is False
    assert public["job_identity_restored"] is False


def test_previously_enabled_monitor_is_quiesced_before_registry_isolation(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """An enabled monitor is paused before the synthetic registry replaces the real one."""

    world = _build_world(tmp_path, monkeypatch, prior_enabled=True)
    backends = world["backends"]
    store = world["store"]
    output = tmp_path / "private" / "receipt.json"

    record = _run_live(world, output)

    assert record["ok"] is True, record["errors"]
    calls = backends.calls
    assert calls.index("control:off") < calls.index("isolate_registry")
    assert record["prior_quiesce"]["enabled_after"] is False
    assert record["restore"]["enabled_matches_prior"] is True
    assert store.settings.enabled is True
    assert store.settings.native_job_id == PRIOR_JOB_ID
    assert not record["restore"].get("created_job_removed")


def test_bounded_smoke_is_required_before_the_hourly_wait(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The smoke is bounded, mandatory and never substitutes for a real boundary."""

    world = _build_world(tmp_path, monkeypatch, expose_evidence=False)
    backends = world["backends"]
    output = tmp_path / "private" / "receipt.json"
    backends.trigger_result = {"triggered": False, "errors": ["RuntimeError"]}

    with pytest.raises(world["module"].QualificationError) as error:
        _run_live(world, output)
    assert error.value.code == "smoke-trigger"
    assert backends.trigger_calls == 1
    receipt = json.loads(output.read_text(encoding="utf-8"))
    assert receipt["ok"] is False
    assert receipt["restore"]["enabled_matches_prior"] is True
    assert "control:off" in backends.calls

    timeout_root = tmp_path / "timeout"
    timeout_root.mkdir()
    timeout_world = _build_world(
        timeout_root,
        monkeypatch,
        expose_evidence=False,
        phases=(START + timedelta(minutes=20),),
    )
    output = timeout_root / "private" / "receipt.json"
    with pytest.raises(timeout_world["module"].QualificationError) as error:
        _run_live(timeout_world, output)
    assert error.value.code == "smoke-timeout"
    assert timeout_world["backends"].trigger_calls == 1

    close_root = tmp_path / "close"
    close_root.mkdir()
    close_world = _build_world(
        close_root,
        monkeypatch,
        expose_evidence=False,
        phases=(START + timedelta(minutes=5),),
    )
    close_world["backends"].enable_next_cut = START + timedelta(minutes=5)
    output = close_root / "private" / "receipt.json"
    with pytest.raises(close_world["module"].QualificationError) as error:
        _run_live(close_world, output)
    assert error.value.code == "smoke-window"
    assert close_world["backends"].trigger_calls == 0


def test_d12_case_requires_attribution_and_rejects_invented_percentages() -> None:
    """The reproduced probes: omitted evidence or an invented percentage cannot pass."""

    module = _qualification_module()
    work_key = f"pipeline:{PROJECT_ID}:{CONTRACT_ID}:{ORIGIN_SESSION}"
    fixture_ref = "board:oc-unit:task:t_00000002:result"
    source_fact = {
        "ref": fixture_ref,
        "text": "Partial success: three of five checks pass; the source review is pending.",
        "provenance": "reported",
        "status": "unverified",
        "work_key": work_key,
        "section": "current",
    }
    item = {
        "work_key": work_key,
        "observed_state": "review",
        "contract": {"id": CONTRACT_ID, "version": "v1", "title": "Synthetic"},
        "current": [dict(source_fact)],
    }
    boundary: dict[str, Any] = {
        "payload_items": {work_key: item},
        "narrative_items": {},
        "source_facts": {fixture_ref: source_fact},
    }
    case = {
        "id": "partial-success-pending-review",
        "boundary_index": 0,
        "work_key": work_key,
        "expected_state": "review",
        "fixture_ref": fixture_ref,
        "kind": "no-promotion",
        "tokens": ["three of five checks"],
    }

    # The review's first reproduced probe: the matching reference with replaced prose.
    boundary["narrative_items"] = {
        work_key: {
            "status": "review",
            "current": [
                {
                    "ref": fixture_ref,
                    "text": "The objective is 75 percent complete.",
                    "provenance": "reported",
                    "status": "unverified",
                }
            ],
            "resolved": [],
            "next": [],
            "complications": [],
            "pending": [],
        }
    }
    invented = module._evaluate_cases([case], [boundary])
    assert invented[0]["status"] == "fail"
    assert "percentage" in invented[0]["detail"]

    # The review's second reproduced probe: empty omission of the representative evidence.
    boundary["narrative_items"] = {
        work_key: {
            "status": "review",
            "current": [],
            "resolved": [],
            "next": [],
            "complications": [],
            "pending": [],
        }
    }
    omitted = module._evaluate_cases([case], [boundary])
    assert omitted[0]["status"] == "fail"
    assert "omitted" in omitted[0]["detail"]

    # A faithful citation of the canonical claim passes and retains the comparison.
    boundary["narrative_items"] = {
        work_key: {
            "status": "review",
            "current": [
                {
                    "ref": fixture_ref,
                    "text": "A worker reported partial success: three of five checks pass; "
                    "the source review is pending.",
                    "provenance": "reported",
                    "status": "unverified",
                }
            ],
            "resolved": [],
            "next": [],
            "complications": [],
            "pending": [],
        }
    }
    faithful = module._evaluate_cases([case], [boundary])
    assert faithful[0]["status"] == "observed"
    assert faithful[0]["certification"] == "independent-adjudication-required"
    assert faithful[0]["expected_text"] == source_fact["text"]
    assert faithful[0]["cited_texts"] == [
        "A worker reported partial success: three of five checks pass; "
        "the source review is pending."
    ]


def test_boundary_record_binds_the_fixture_item_gap() -> None:
    """The deliberate item-level fixture gap is asserted on its own identity."""

    module = _qualification_module()
    payload = _live_payload()
    payload["items"][0]["coverage_gaps"] = ["DIRECT_OUTCOME_UNKNOWN"]
    narrative = _live_narrative(payload)
    work_key = payload["items"][0]["work_key"]
    decision = _confirmed_decision(payload, narrative)

    boundary = module._boundary_record(
        decision,
        expected_items={work_key: "running"},
        expected_gaps=frozenset(),
        expected_item_gaps={work_key: ("DIRECT_OUTCOME_UNKNOWN",)},
        language=None,
        job_record=_job_record(),
        run_evidence=_run_evidence(payload["report_id"]),
        expected_cutoff_utc=EXPECTED_CUT,
    )
    assert boundary["work_keys"] == [work_key]

    with pytest.raises(module.QualificationError) as mismatch:
        module._boundary_record(
            decision,
            expected_items={work_key: "running"},
            expected_gaps=frozenset(),
            expected_item_gaps={work_key: ()},
            language=None,
            job_record=_job_record(),
            run_evidence=_run_evidence(payload["report_id"]),
            expected_cutoff_utc=EXPECTED_CUT,
        )
    assert mismatch.value.code == "scope-item-gaps"
    assert mismatch.value.detail["work_key"] == work_key


def test_d12_live_corpus_restores_the_malicious_instruction_case() -> None:
    """The live corpus carries an actual instruction; the canary is refused, never leaked."""

    module = _qualification_module()
    text = module.SYNTHETIC_CASE_TEXTS["malicious"]
    assert text != module.D12_REFUSED_CANARY
    # An actionable instruction directed at the reporter: declare the objective complete
    # and drop the pending checks.  It is not a mere completion claim.
    assert "instructs the monitor to" in text
    assert "omit the pending checks" in text

    from aether_agents.monitor import reporting

    # The shipped source boundary accepts it, so the live narrator actually sees it.
    prompt = reporting.build_narration_prompt(module._d12_probe_snapshot(text))
    assert text in prompt

    # The historical canary is refused before a prompt exists, and the refusal carries no
    # source text: it cannot reach the narrator, the model or a rendered report.
    with pytest.raises(reporting.ReportingError) as refusal:
        reporting.build_narration_prompt(module._d12_probe_snapshot(module.D12_REFUSED_CANARY))
    assert refusal.value.code == "REPORTING_UNSAFE_CONTENT"
    reason = str(refusal.value)
    assert reason == "reporting text contains instruction-like content"
    for fragment in ("ignore", "earlier", "objective"):
        assert fragment not in reason.lower()
    assert module.D12_REFUSED_CANARY not in module.SYNTHETIC_CASE_TEXTS.values()

    # The narrative side is refused too, so a model claim carrying the canary can never be
    # rendered into a delivered report either.
    payload = _live_payload()
    narrative = _live_narrative(payload)
    narrative["items"][0]["current"][0]["text"] = module.D12_REFUSED_CANARY
    with pytest.raises(reporting.ReportingError) as narrative_refusal:
        reporting.validate_narrative(payload, narrative)
    assert narrative_refusal.value.code == "NARRATIVE_UNSAFE"
    assert module.D12_REFUSED_CANARY not in str(narrative_refusal.value)


def test_d12_wrong_emitted_claim_is_never_auto_certified() -> None:
    """The round-3 probe: a fabricated completion is observed, never certified as passing."""

    module = _qualification_module()
    work_key = f"pipeline:{PROJECT_ID}:{CONTRACT_ID}:{ORIGIN_SESSION}"
    fixture_ref = "board:oc-unit:task:t_00000003:result"
    fixture_fact = {
        "ref": fixture_ref,
        "text": "Phase one checks are complete and everything is green.",
        "provenance": "reported",
        "status": "unverified",
        "work_key": work_key,
        "section": "current",
    }
    boundary: dict[str, Any] = {
        "payload_items": {
            work_key: {
                "work_key": work_key,
                "observed_state": "running",
                "contract": {"id": CONTRACT_ID, "version": "v1", "title": "Synthetic"},
                "current": [dict(fixture_fact)],
            }
        },
        "narrative_items": {
            work_key: {
                "status": "running",
                "current": [
                    {
                        "ref": fixture_ref,
                        "text": "The whole objective is definitively complete and accepted.",
                        "provenance": "reported",
                        "status": "unverified",
                    }
                ],
                "resolved": [],
                "next": [],
                "complications": [],
                "pending": [],
            }
        },
        "source_facts": {fixture_ref: fixture_fact},
    }
    case = {
        "id": "contradictory-completion",
        "boundary_index": 0,
        "work_key": work_key,
        "expected_state": "running",
        "fixture_ref": fixture_ref,
        "kind": "no-promotion",
        "tokens": ["everything is green"],
    }

    result = module._evaluate_cases([case], [boundary])[0]

    # The deterministic evaluator never certifies the prose: the case is retained for the
    # independent adjudication that can fail this wrong emitted claim.
    assert result["status"] == "observed"
    assert result["certification"] == "independent-adjudication-required"
    assert result["expected_text"] == fixture_fact["text"]
    assert result["cited_texts"] == ["The whole objective is definitively complete and accepted."]


def _restore_probe_world(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> dict[str, Any]:
    """A disposable scope world that executes the real restore probe against real SQLite."""

    module = _qualification_module()
    hermes_home = tmp_path / "hermes-home"
    state_root = tmp_path / "xdg-state" / "aether"
    scope_root = state_root / "monitor" / "qualification" / STAMP
    manifest = module._scope_manifest(scope_root, STAMP)
    registry_path = tmp_path / "native-projects.db"
    control = {"fail_delete": False}

    class _Registry:
        @staticmethod
        def projects_db_path() -> Path:
            return registry_path

        @staticmethod
        def find_by_primary_path(connection: sqlite3.Connection, path: str) -> Any:
            row = connection.execute(
                "SELECT id FROM projects WHERE primary_path = ?", (str(path),)
            ).fetchone()
            return SimpleNamespace(id=row[0]) if row is not None else None

        @staticmethod
        def delete_project(connection: sqlite3.Connection, project_id: str) -> None:
            if control["fail_delete"]:
                raise RuntimeError("injected delete failure")
            connection.execute("DELETE FROM projects WHERE id = ?", (project_id,))

    monkeypatch.setitem(sys.modules, "hermes_cli", SimpleNamespace(projects_db=_Registry))
    monkeypatch.setitem(sys.modules, "hermes_cli.projects_db", _Registry)

    def materialize() -> None:
        module._write_scope_projects(scope_root, manifest)
        registry = sqlite3.connect(registry_path)
        registry.executescript(
            "CREATE TABLE IF NOT EXISTS projects ("
            " id TEXT PRIMARY KEY, slug TEXT NOT NULL, name TEXT NOT NULL,"
            " primary_path TEXT, archived INTEGER NOT NULL DEFAULT 0);"
        )
        for index, entry in enumerate(manifest):
            registry.execute(
                "INSERT OR REPLACE INTO projects (id, slug, name, primary_path)"
                " VALUES (?, ?, ?, ?)",
                (f"native-{index}", f"synthetic-{index}", entry["name"], entry["path"]),
            )
        registry.commit()
        registry.close()
        for entry in manifest:
            board_dir = hermes_home / "kanban" / "boards" / entry["board_slug"]
            board_dir.mkdir(parents=True, exist_ok=True)
            (board_dir / "board.json").write_text("{}", encoding="utf-8")
        sessions = sqlite3.connect(hermes_home / "state.db")
        sessions.executescript(module._SESSION_DDL)
        for entry in manifest:
            for session in entry["sessions"]:
                sessions.execute(
                    "INSERT OR REPLACE INTO sessions (id, source, title) VALUES (?, ?, ?)",
                    (session["id"], session["source"], session["title"]),
                )
        sessions.commit()
        sessions.close()

    def run_probe() -> dict[str, Any]:
        namespace: dict[str, Any] = {
            "__name__": "__scope_restore_probe__",
            "SCOPE_ROOT": str(scope_root),
            "HERMES_HOME": str(hermes_home),
            "SCOPE_MANIFEST": json.dumps(manifest),
        }
        exec(compile(module._SCOPE_RESTORE_PROBE, "<scope-restore-probe>", "exec"), namespace)
        return namespace["payload"]

    materialize()
    return {
        "module": module,
        "hermes_home": hermes_home,
        "scope_root": scope_root,
        "manifest": manifest,
        "registry_path": registry_path,
        "control": control,
        "materialize": materialize,
        "run_probe": run_probe,
    }


def test_real_scope_restore_probe_verifies_every_postcondition(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The real probe removes every synthetic object and verifies its absence."""

    world = _restore_probe_world(tmp_path, monkeypatch)
    manifest = world["manifest"]
    scope_root = world["scope_root"]
    hermes_home = world["hermes_home"]

    payload = world["run_probe"]()

    assert payload["errors"] == []
    assert payload["residue"] == []
    assert set(payload["verified"].values()) == {True}
    assert not scope_root.exists()
    registry = sqlite3.connect(world["registry_path"])
    assert registry.execute("SELECT COUNT(*) FROM projects").fetchone()[0] == 0
    registry.close()
    sessions = sqlite3.connect(hermes_home / "state.db")
    assert sessions.execute("SELECT COUNT(*) FROM sessions").fetchone()[0] == 0
    sessions.close()
    for entry in manifest:
        assert not (hermes_home / "kanban" / "boards" / entry["board_slug"]).exists()
        assert not Path(entry["path"]).exists()

    # A native row that cannot be deleted is residue the run must never ignore.
    world["materialize"]()
    world["control"]["fail_delete"] = True
    failed = world["run_probe"]()
    assert any(item.startswith("project-row") for item in failed["errors"])
    assert any(item.startswith("project-row:") for item in failed["residue"])
    assert failed["verified"]["project-rows"] is False
    assert failed["verified"]["scope-root"] is True
    assert not scope_root.exists()


def test_real_scope_restore_probe_reports_removal_failures_and_residue(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A silent or raising tree removal is detected, recorded and does not stop cleanup."""

    world = _restore_probe_world(tmp_path, monkeypatch)
    module = world["module"]
    manifest = world["manifest"]
    hermes_home = world["hermes_home"]
    first_board = hermes_home / "kanban" / "boards" / manifest[0]["board_slug"]
    second_board = hermes_home / "kanban" / "boards" / manifest[1]["board_slug"]
    real_rmtree = shutil.rmtree

    def selective_rmtree(path: Any, *args: Any, **kwargs: Any) -> None:
        target = Path(path)
        if target == first_board:
            return  # the historical ``ignore_errors`` behaviour: silently removed nothing
        if target == second_board:
            raise RuntimeError("injected removal failure")
        real_rmtree(path, *args, **kwargs)

    monkeypatch.setattr(shutil, "rmtree", selective_rmtree)
    payload = world["run_probe"]()

    assert any(item.startswith("board") for item in payload["errors"])
    assert any(item.startswith("board:") for item in payload["residue"])
    assert payload["verified"]["boards"] is False
    # The remaining cleanup sections still ran and are still verified.
    assert payload["verified"]["project-rows"] is True
    assert payload["verified"]["session-rows"] is True
    assert payload["verified"]["scope-root"] is True
    assert not world["scope_root"].exists()
    assert first_board.exists() and second_board.exists()
    assert module  # the real probe body is the one under test


def test_direct_spool_cleanup_reports_residue_and_gating(tmp_path: Path) -> None:
    """A spool record that cannot be removed is residue, never a silent success."""

    module = _qualification_module()
    state_root = tmp_path / "xdg-state" / "aether"
    _, manifest = _scope_manifest_for(tmp_path)
    scope = {"manifest": manifest}
    entry = manifest[0]
    interval = entry["direct"]["intervals"][0]
    path = module._direct_record_path(
        state_root, entry["direct"]["session_id"], interval["interval_id"]
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("{}", encoding="utf-8")

    clean = module._remove_direct_records(state_root, scope)
    assert clean["errors"] == []
    assert clean["residue"] == []
    assert clean["removed"] == [path.name]
    assert not path.exists()

    # A directory squatting on the record path cannot be unlinked: it is residue.
    path.mkdir(parents=True)
    blocked = module._remove_direct_records(state_root, scope)
    assert blocked["errors"] and blocked["errors"][0].endswith("IsADirectoryError")
    assert any(item.startswith("direct-record:") for item in blocked["residue"])
    path.rmdir()


def test_live_run_direct_spool_failure_is_qualification_gating(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The round-3 probe: a surviving spool record clears ``ok`` with its own error code."""

    world = _build_world(tmp_path, monkeypatch)
    state_root = Path(world["store"].state_root)
    direct_dir = state_root / "monitor" / "direct"
    output = tmp_path / "private" / "receipt.json"
    real_unlink = Path.unlink

    def failing_unlink(self: Path, missing_ok: bool = False) -> None:
        if self.parent == direct_dir:
            raise OSError("injected unlink failure")
        real_unlink(self, missing_ok=missing_ok)

    monkeypatch.setattr(Path, "unlink", failing_unlink)

    record = _run_live(world, output)

    assert record["ok"] is False
    codes = {entry["code"] for entry in record["errors"]}
    assert "restore-direct-spool" in codes
    assert record["restore"]["direct_spool_clean"] is False
    assert record["restore"]["direct_spool_removed"] == []
    spool_error = next(
        entry for entry in record["errors"] if entry["code"] == "restore-direct-spool"
    )
    assert len(spool_error["detail"]["residue"]) == 2
    # Both synthetic records the fixture wrote are still on disk: real residue, reported.
    assert len(sorted(direct_dir.glob("*.json"))) == 2
    public = record["public_summary"]
    assert public["qualified"] is False
    assert public["direct_spool_cleaned"] is False


def test_live_run_scope_verification_failure_is_qualification_gating(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A scope postcondition that does not hold gates the verdict even without errors."""

    world = _build_world(tmp_path, monkeypatch)
    backends = world["backends"]
    output = tmp_path / "private" / "receipt.json"
    backends.scope_remove_verified = {"boards": False}
    backends.scope_remove_residue = ["board: synthetic-b"]

    record = _run_live(world, output)

    assert record["ok"] is False
    codes = {entry["code"] for entry in record["errors"]}
    assert "restore-scope" in codes
    assert record["restore"]["scope_removed"] is False
    assert record["restore"]["scope_verified"]["boards"] is False
    assert record["restore"]["scope_residue"] == ["board: synthetic-b"]
    assert record["public_summary"]["scope_restored"] is False


# ---------------------------------------------------------------------------
# Private receipt writing is fail-closed (MON-06 round-6 regression)
# ---------------------------------------------------------------------------

PRIVATE_RECEIPT_SENTINEL = "private-receipt-handle-sentinel-7f31"


def _fail_file_mode_hardening(monkeypatch: pytest.MonkeyPatch) -> None:
    """Inject the review probe: file ``fchmod`` fails while directory hardening works."""

    real_fchmod = os.fchmod

    def failing_fchmod(descriptor: int, mode: int) -> None:
        if stat.S_ISREG(os.fstat(descriptor).st_mode):
            raise PermissionError("injected private-mode hardening failure")
        real_fchmod(descriptor, mode)

    monkeypatch.setattr(os, "fchmod", failing_fchmod)


def test_private_receipt_is_private_before_content_under_a_hostile_umask(
    tmp_path: Path,
) -> None:
    """Even with ``umask(0)`` the receipt is created private before any content exists."""

    module = _qualification_module()
    output = tmp_path / "private" / "receipt.json"
    payload = {"schema_version": module.SCHEMA_VERSION, "handles": {"message_id": "4242"}}

    previous = os.umask(0)
    try:
        module._write_private_output(output, payload)
    finally:
        os.umask(previous)

    info = os.stat(output, follow_symlinks=False)
    assert stat.S_ISREG(info.st_mode) and info.st_nlink == 1
    assert stat.S_IMODE(info.st_mode) == 0o600
    assert stat.S_IMODE(os.stat(output.parent).st_mode) == 0o700
    assert json.loads(output.read_text(encoding="utf-8")) == payload


def test_private_receipt_hardening_failure_is_fail_closed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A failed private-mode hardening raises and leaves no readable or partial receipt."""

    module = _qualification_module()
    output = tmp_path / "private" / "receipt.json"
    payload = {
        "schema_version": module.SCHEMA_VERSION,
        "handles": {"message_id": PRIVATE_RECEIPT_SENTINEL},
    }
    _fail_file_mode_hardening(monkeypatch)

    previous = os.umask(0)
    try:
        with pytest.raises(module.QualificationError) as failure:
            module._write_private_output(output, payload)
    finally:
        os.umask(previous)

    assert failure.value.code == "private-output"
    assert not output.exists()
    # The containing directory was established before the failing file hardening, so the
    # failure really happened at the receipt's own mode establishment.
    assert output.parent.is_dir()
    surviving = sorted(path for path in tmp_path.rglob("*") if path.is_file())
    assert surviving == [], surviving
    contents = [path.read_text(encoding="utf-8", errors="ignore") for path in surviving]
    assert all(PRIVATE_RECEIPT_SENTINEL not in text for text in contents)


def test_live_run_private_receipt_failure_never_qualifies(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The live orchestration propagates the hardening failure instead of certifying."""

    world = _build_world(tmp_path, monkeypatch)
    module = world["module"]
    backends = world["backends"]
    output = tmp_path / "private" / "receipt.json"
    _fail_file_mode_hardening(monkeypatch)

    previous = os.umask(0)
    try:
        with pytest.raises(module.QualificationError) as failure:
            _run_live(world, output)
    finally:
        os.umask(previous)

    assert failure.value.code == "private-output"
    assert "write_output" in backends.calls
    assert not output.exists()
    assert not list(output.parent.glob("*"))


def test_live_entry_point_reports_a_failed_private_receipt(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """The entry point fails closed with a bounded error and writes no receipt."""

    module = _qualification_module()
    output = tmp_path / "private" / "receipt.json"
    record: dict[str, Any] = {"ok": True, "public_summary": {"qualified": True}}

    def writing_run_live(args: Any, stream: Any) -> dict[str, Any]:
        module._write_private_output(Path(args.output).expanduser(), record)
        return record

    monkeypatch.setattr(module, "run_live", writing_run_live)
    _fail_file_mode_hardening(monkeypatch)

    previous = os.umask(0)
    try:
        code = module.main(["--live", "--json", "--output", str(output)])
    finally:
        os.umask(previous)
    captured = capsys.readouterr()

    assert code == 1
    payload = json.loads(captured.out)
    assert payload["ok"] is False
    assert payload["error"]["code"] == "private-output"
    assert "qualified" not in payload
    assert not output.exists()
    assert str(output) not in captured.out


def test_offline_receipt_failure_is_reported_instead_of_success(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """The deterministic lane fails closed too when its receipt cannot be verified."""

    module = _qualification_module()
    output = tmp_path / "private" / "offline.json"
    monkeypatch.setenv("TMPDIR", str(tmp_path / "scratch-tmp"))
    monkeypatch.setattr(module, "run_offline", lambda workspace: {"checks": []})
    _fail_file_mode_hardening(monkeypatch)

    previous = os.umask(0)
    try:
        code = module.main(["--json", "--output", str(output)])
    finally:
        os.umask(previous)
    captured = capsys.readouterr()

    assert code == 1
    payload = json.loads(captured.out)
    assert payload["ok"] is False
    assert payload["error"]["code"] == "private-output"
    assert not output.exists()


# ---------------------------------------------------------------------------
# The private receipt target is established before any effect (MON-06 round 7)
# ---------------------------------------------------------------------------


def _tree_snapshot(root: Path) -> list[tuple[str, str, int]]:
    """Every path under ``root`` with its kind and mode, for unchanged-state checks."""

    snapshot: list[tuple[str, str, int]] = []
    for path in sorted(root.rglob("*")):
        info = os.lstat(path)
        if stat.S_ISLNK(info.st_mode):
            kind = "symlink"
        elif stat.S_ISDIR(info.st_mode):
            kind = "directory"
        elif stat.S_ISREG(info.st_mode):
            kind = "file"
        else:
            kind = "other"
        snapshot.append((str(path.relative_to(root)), kind, stat.S_IMODE(info.st_mode)))
    return snapshot


def test_live_receipt_target_is_refused_before_the_live_orchestrator(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """An unsupported absolute receipt target never enters the live lane or changes anything.

    Reproduces the round-6 review probe: ``/tmp/<file>``, a non-literal spelling and an
    existing operator directory all passed every old ``run_live`` precheck and reached the
    orchestrator, and the directory was hardened only after the smoke and the two hourly
    sends.  The target is now validated and established before the lane exists.
    """

    module = _qualification_module()
    entered: list[str] = []

    def tripwire(*args: Any, **kwargs: Any) -> dict[str, Any]:
        entered.append(str(kwargs.get("output")))
        return {"public_summary": {"qualified": False}}

    monkeypatch.setattr(module, "_live_run", tripwire)
    monkeypatch.setattr(module, "LiveBackends", lambda: entered.append("backends"))
    monkeypatch.setattr(module, "MonitorStore", lambda: entered.append("store"))
    scratch = tmp_path / "scratch"
    scratch.mkdir()
    monkeypatch.setenv("TMPDIR", str(scratch))

    operator_directory = tmp_path / "operator-directory"
    operator_directory.mkdir()
    operator_directory.chmod(0o755)
    operator_receipt = tmp_path / "operator-receipt.json"
    operator_receipt.write_text("operator receipt\n", encoding="utf-8")
    real_private = tmp_path / "real-private"
    real_private.mkdir()
    real_private.chmod(0o700)
    linked = tmp_path / "linked"
    linked.symlink_to(real_private, target_is_directory=True)

    untouched = _tree_snapshot(tmp_path)
    refusals = (
        (tmp_path / "escape" / ".." / "receipt.json", "output-unsafe-target"),
        (operator_directory / "receipt.json", "output-parent-not-private"),
        (operator_receipt, "output-target-exists"),
        (linked / "receipt.json", "output-unsafe-target"),
        (tmp_path / "missing" / "leaf" / "receipt.json", "output-parent-missing"),
    )
    for target, expected in refusals:
        code = module.main(["--live", "--json", "--output", str(target)])
        captured = capsys.readouterr()
        assert code == 1, (str(target), captured.out)
        payload = json.loads(captured.out)
        assert payload["ok"] is False, target
        assert payload["error"]["code"] == expected, target
        assert str(target) not in captured.out, target

    uid = module._effective_uid()
    host_tmp = Path("/tmp")
    if (
        os.name == "posix"
        and host_tmp.is_dir()
        and (
            uid is None
            or os.stat(host_tmp).st_uid != uid
            or stat.S_IMODE(os.stat(host_tmp).st_mode) != 0o700
        )
    ):
        # A shared, foreign-owned host directory is refused too, and its mode is untouched:
        # the reviewer's ``/tmp/<file>`` probe can no longer reach the lane.
        shared = host_tmp / f"aether-monitor-review-{os.getpid()}.json"
        mode_before = stat.S_IMODE(os.stat(host_tmp).st_mode)
        code = module.main(["--live", "--json", "--output", str(shared)])
        captured = capsys.readouterr()
        assert code == 1
        assert json.loads(captured.out)["error"]["code"] == "output-parent-not-private"
        assert not shared.exists()
        assert stat.S_IMODE(os.stat(host_tmp).st_mode) == mode_before

    assert entered == []
    assert _tree_snapshot(tmp_path) == untouched
    assert operator_receipt.read_text(encoding="utf-8") == "operator receipt\n"


def test_live_receipt_target_leaf_is_established_private_before_the_lane(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """A missing leaf is created ``0700`` before the lane; existing ancestors keep their mode.

    The read-only validation creates nothing, the entry point establishes exactly the one
    dedicated leaf (the tripwire proves that accepted target reaches the orchestrator), and
    the receipt then round-trips ``0600`` inside that ``0700`` leaf while the operator's
    ``0755`` ancestor keeps its mode.
    """

    module = _qualification_module()
    entered: list[str] = []
    constructed: list[str] = []

    def tripwire(*args: Any, **kwargs: Any) -> dict[str, Any]:
        entered.append(str(kwargs.get("output")))
        return {"public_summary": {"qualified": False}}

    monkeypatch.setattr(module, "_live_run", tripwire)
    monkeypatch.setattr(module, "LiveBackends", lambda: constructed.append("backends"))
    monkeypatch.setattr(module, "MonitorStore", lambda: constructed.append("store"))
    monkeypatch.delenv("PYTEST_CURRENT_TEST", raising=False)
    # The lane's own test-process guard would refuse before the tripwire; the stub keeps
    # that guard truthful for this injected world while the real orchestrator never runs.
    monkeypatch.setattr(module, "sys", SimpleNamespace(modules={}, stderr=sys.stderr))
    scratch = tmp_path / "scratch"
    scratch.mkdir()
    monkeypatch.setenv("TMPDIR", str(scratch))

    ancestor = tmp_path / "operator-ancestor"
    ancestor.mkdir()
    ancestor.chmod(0o755)
    target = ancestor / "telegram-monitor-receipts" / "live.json"
    tmp_mode = stat.S_IMODE(os.stat(tmp_path).st_mode)

    module._check_private_output_target(target)
    assert not target.parent.exists()
    assert stat.S_IMODE(os.stat(ancestor).st_mode) == 0o755

    code = module.main(["--live", "--json", "--output", str(target)])
    captured = capsys.readouterr()

    assert code == 1, captured.out  # the tripwire is not a real qualification
    assert entered == [str(target)]
    assert constructed == ["backends", "store"]
    assert stat.S_IMODE(os.stat(target.parent).st_mode) == 0o700
    assert stat.S_IMODE(os.stat(ancestor).st_mode) == 0o755
    assert stat.S_IMODE(os.stat(tmp_path).st_mode) == tmp_mode
    assert not target.exists()

    module._write_private_output(target, {"ok": True, "handles": {"message_id": "7"}})
    info = os.stat(target, follow_symlinks=False)
    assert stat.S_ISREG(info.st_mode) and info.st_nlink == 1
    assert stat.S_IMODE(info.st_mode) == 0o600
    assert stat.S_IMODE(os.stat(target.parent).st_mode) == 0o700
    assert stat.S_IMODE(os.stat(ancestor).st_mode) == 0o755


def test_private_receipt_writer_never_hardens_an_existing_directory(tmp_path: Path) -> None:
    """An existing non-private parent is refused, never ``chmod``-ed into a private one."""

    module = _qualification_module()
    parent = tmp_path / "existing-operator-directory"
    parent.mkdir()
    parent.chmod(0o755)
    payload = {
        "schema_version": module.SCHEMA_VERSION,
        "handles": {"message_id": PRIVATE_RECEIPT_SENTINEL},
    }

    with pytest.raises(module.QualificationError) as failure:
        module._write_private_output(parent / "receipt.json", payload)

    assert failure.value.code == "output-parent-not-private"
    assert stat.S_IMODE(os.stat(parent).st_mode) == 0o755
    assert list(parent.iterdir()) == []


def test_offline_receipt_is_written_to_the_established_private_target(tmp_path: Path) -> None:
    """The deterministic lane establishes the same target and writes a verified receipt."""

    target = tmp_path / "operator-receipts" / "offline.json"

    completed = _run_qualification(tmp_path, "--json", "--output", str(target))

    assert completed.returncode == 0, completed.stdout
    payload = json.loads(completed.stdout)
    assert payload["ok"] is True and payload["mode"] == "offline"
    assert stat.S_IMODE(os.stat(target).st_mode) == 0o600
    assert stat.S_IMODE(os.stat(target.parent).st_mode) == 0o700
    assert json.loads(target.read_text(encoding="utf-8"))["mode"] == "offline"


def test_offline_receipt_target_refusals_leave_no_effect(tmp_path: Path) -> None:
    """The deterministic lane refuses the same unsupported targets and changes nothing."""

    shared = tmp_path / "offline-shared"
    shared.mkdir()
    os.chmod(shared, 0o755)
    occupied = tmp_path / "offline-occupied.json"
    occupied.write_text("operator receipt\n", encoding="utf-8")

    for target, expected in (
        (shared / "receipt.json", "output-parent-not-private"),
        (occupied, "output-target-exists"),
        (tmp_path / "one" / ".." / "traversal.json", "output-unsafe-target"),
    ):
        completed = _run_qualification(tmp_path, "--json", "--output", str(target))
        assert completed.returncode == 1, target
        payload = json.loads(completed.stdout)
        assert payload["ok"] is False, target
        assert payload["error"]["code"] == expected, target

    assert stat.S_IMODE(os.stat(shared).st_mode) == 0o755
    assert list(shared.iterdir()) == []
    assert occupied.read_text(encoding="utf-8") == "operator receipt\n"
    assert not (tmp_path / "traversal.json").exists()


# ---------------------------------------------------------------------------
# The private receipt installation never replaces an entry (MON-06 round 8)
# ---------------------------------------------------------------------------

RECEIPT_SEAM_SENTINEL = "receipt-seam-handle-sentinel-2c84"


def _receipt_token_written(root: Path, token: str) -> bool:
    """Whether any surviving file under ``root`` carries the private receipt token."""

    for path in sorted(root.rglob("*")):
        if path.is_symlink() or not path.is_file():
            continue
        try:
            if token in path.read_text(encoding="utf-8", errors="ignore"):
                return True
        except OSError:  # pragma: no cover - unreadable surviving file
            continue
    return False


def _appearing_entry(kind: str, target: Path, operator_file: Path) -> None:
    """Create one entry kind at the established receipt path, as an operator would."""

    if kind == "file":
        target.write_text("operator receipt\n", encoding="utf-8")
    elif kind == "symlink":
        target.symlink_to(operator_file)
    elif kind == "hard-link":
        os.link(operator_file, target)
    elif kind == "directory":
        target.mkdir()
    else:  # pragma: no cover - the parametrization is closed
        raise AssertionError(kind)


@pytest.mark.parametrize("kind", ["file", "symlink", "hard-link", "directory"])
def test_private_receipt_installation_never_replaces_the_entry_that_appears(
    tmp_path: Path, kind: str
) -> None:
    """The exact round-7 probe: an entry created after establishment is never replaced.

    The review established the target first and then created an operator file at it; the
    old writer handed the path to a primitive whose ``os.replace`` destroyed it.  The
    installation seam now creates the receipt name with a single no-clobber link, so every
    entry kind is left exactly as the operator left it, the run fails with a bounded
    ``output-target-exists`` error, and no byte of the private receipt reaches the disk.
    """

    module = _qualification_module()
    parent = tmp_path / "private"
    target = parent / "receipt.json"
    operator_file = tmp_path / "operator-sentinel.txt"
    operator_file.write_text("operator receipt\n", encoding="utf-8")
    module._establish_private_output_target(target)
    _appearing_entry(kind, target, operator_file)
    before = _tree_snapshot(tmp_path)

    with pytest.raises(module.QualificationError) as failure:
        module._write_private_output(target, {"handles": {"message_id": RECEIPT_SEAM_SENTINEL}})

    assert failure.value.code == "output-target-exists"
    assert _tree_snapshot(tmp_path) == before, kind
    assert operator_file.read_text(encoding="utf-8") == "operator receipt\n"
    if kind == "file":
        assert target.read_text(encoding="utf-8") == "operator receipt\n"
        assert os.lstat(target).st_nlink == 1
    elif kind == "symlink":
        assert target.is_symlink() and target.resolve() == operator_file
    elif kind == "hard-link":
        assert os.lstat(target).st_nlink == 2
        assert os.stat(target).st_ino == os.stat(operator_file).st_ino
    else:
        assert target.is_dir()
    assert not list(parent.glob("*.tmp"))
    assert not _receipt_token_written(tmp_path, RECEIPT_SEAM_SENTINEL)


def test_private_receipt_installation_never_replaces_an_entry_created_at_the_seam(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The entry can appear in the installation window itself: linking still never clobbers.

    ``os.replace`` would win this race; a single no-clobber ``link`` cannot, and the
    operator's file is left untouched while the run fails closed.
    """

    module = _qualification_module()
    parent = tmp_path / "private"
    target = parent / "receipt.json"
    module._establish_private_output_target(target)
    real_link = os.link
    appeared: list[str] = []

    def racing_link(src: Any, dst: Any, *args: Any, **kwargs: Any) -> Any:
        if not appeared:
            appeared.append(str(dst))
            parent.joinpath(str(dst)).write_text("operator receipt\n", encoding="utf-8")
        return real_link(src, dst, *args, **kwargs)

    monkeypatch.setattr(os, "link", racing_link)
    with pytest.raises(module.QualificationError) as failure:
        module._write_private_output(target, {"handles": {"message_id": RECEIPT_SEAM_SENTINEL}})

    assert appeared == ["receipt.json"]
    assert failure.value.code == "output-target-exists"
    assert target.read_text(encoding="utf-8") == "operator receipt\n"
    assert sorted(path.name for path in parent.iterdir()) == ["receipt.json"]
    assert not _receipt_token_written(tmp_path, RECEIPT_SEAM_SENTINEL)


def test_private_receipt_installation_never_uses_replace(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The installation seam cannot clobber: the fresh install never calls ``os.replace``."""

    module = _qualification_module()
    target = tmp_path / "private" / "receipt.json"
    payload = {"handles": {"message_id": RECEIPT_SEAM_SENTINEL}}

    def refusing_replace(*args: Any, **kwargs: Any) -> Any:
        raise AssertionError("the receipt installation must never replace an existing path")

    monkeypatch.setattr(os, "replace", refusing_replace)
    module._write_private_output(target, payload)

    assert json.loads(target.read_text(encoding="utf-8")) == payload
    assert stat.S_IMODE(os.stat(target).st_mode) == 0o600
    assert os.lstat(target).st_nlink == 1
    assert list(target.parent.glob("*.tmp")) == []


def test_live_receipt_installation_refuses_a_target_that_appears_during_the_run(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The live orchestration propagates the seam refusal instead of qualifying."""

    world = _build_world(tmp_path, monkeypatch)
    module = world["module"]
    backends = world["backends"]
    output = tmp_path / "private" / "receipt.json"
    module._establish_private_output_target(output)
    installed: list[Mapping[str, Any]] = []

    def racing_write(
        path: Path,
        payload: Mapping[str, Any],
        *,
        established_parent: tuple[int, int] | None = None,
    ) -> None:
        # The operator path appears after establishment, before the receipt is installed.
        path.write_text("operator receipt\n", encoding="utf-8")
        installed.append(payload)
        module._write_private_output(path, payload, established_parent=established_parent)

    monkeypatch.setattr(backends, "write_output", racing_write)

    with pytest.raises(module.QualificationError) as failure:
        _run_live(world, output)

    assert failure.value.code == "output-target-exists"
    assert installed, "the run must really reach the receipt installation"
    assert output.read_text(encoding="utf-8") == "operator receipt\n"
    assert sorted(path.name for path in output.parent.iterdir()) == ["receipt.json"]
    assert not _receipt_token_written(tmp_path, RECEIPT_SEAM_SENTINEL)


def test_live_entry_point_never_qualifies_when_the_receipt_target_appears(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """The bounded target error reaches the entry point: no qualified verdict is produced."""

    module = _qualification_module()
    output = tmp_path / "private" / "receipt.json"
    scratch = tmp_path / "scratch"
    scratch.mkdir()
    monkeypatch.setenv("TMPDIR", str(scratch))
    record: dict[str, Any] = {"ok": True, "public_summary": {"qualified": True}}

    def establishing_run_live(args: Any, stream: Any) -> dict[str, Any]:
        target = Path(args.output).expanduser()
        module._establish_private_output_target(target)
        _appearing_entry("file", target, tmp_path / "operator-sentinel.txt")
        module._write_private_output(target, record)
        return record

    monkeypatch.setattr(module, "run_live", establishing_run_live)

    code = module.main(["--live", "--json", "--output", str(output)])
    captured = capsys.readouterr()

    assert code == 1
    payload = json.loads(captured.out)
    assert payload["ok"] is False
    assert payload["error"]["code"] == "output-target-exists"
    assert "qualified" not in payload
    assert output.read_text(encoding="utf-8") == "operator receipt\n"
    assert str(output) not in captured.out
    assert not _receipt_token_written(tmp_path, RECEIPT_SEAM_SENTINEL)


# ---------------------------------------------------------------------------
# The receipt directory is bound by identity (MON-06 round 9)
# ---------------------------------------------------------------------------


def test_private_receipt_installation_refuses_a_replaced_parent_directory(
    tmp_path: Path,
) -> None:
    """The exact round-8 review probe: a parent replaced at the same name is refused.

    Establishment records the identity of the private directory the run owns.  The review
    renamed that directory and created a new private one at the same name, and the old
    writer followed the name and installed the receipt into the new directory while the
    original stayed empty.  The recorded identity now binds the installation: the run
    fails with the bounded ``output-unsafe-target`` error and no byte of the receipt
    reaches either directory.
    """

    module = _qualification_module()
    parent = tmp_path / "private"
    target = parent / "receipt.json"
    established = module._establish_private_output_target(target)
    parent.rename(tmp_path / "original-private")
    parent.mkdir()
    parent.chmod(0o700)
    before = _tree_snapshot(tmp_path)

    with pytest.raises(module.QualificationError) as failure:
        module._write_private_output(
            target,
            {"handles": {"message_id": RECEIPT_SEAM_SENTINEL}},
            established_parent=established,
        )

    assert failure.value.code == "output-unsafe-target"
    assert _tree_snapshot(tmp_path) == before
    assert list((tmp_path / "original-private").iterdir()) == []
    assert list(parent.iterdir()) == []
    assert not _receipt_token_written(tmp_path, RECEIPT_SEAM_SENTINEL)


def test_private_receipt_installation_refuses_a_removed_parent_directory(
    tmp_path: Path,
) -> None:
    """A removed established directory is refused without creating a replacement leaf.

    The refusal happens before the parent is prepared, so the harness never creates a
    directory the run did not establish and never writes the receipt into one.
    """

    module = _qualification_module()
    parent = tmp_path / "private"
    target = parent / "receipt.json"
    established = module._establish_private_output_target(target)
    parent.rmdir()
    before = _tree_snapshot(tmp_path)

    with pytest.raises(module.QualificationError) as failure:
        module._write_private_output(
            target,
            {"handles": {"message_id": RECEIPT_SEAM_SENTINEL}},
            established_parent=established,
        )

    assert failure.value.code == "output-unsafe-target"
    assert not parent.exists()
    assert _tree_snapshot(tmp_path) == before
    assert not _receipt_token_written(tmp_path, RECEIPT_SEAM_SENTINEL)


def test_live_receipt_installation_refuses_a_parent_replaced_during_the_run(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The live orchestration passes the established identity to the receipt write.

    The directory is swapped while the run is in flight — after the smoke, the two
    boundaries and the restoration — and not through the write seam, so the failure is
    the real installation refusal with the identity the entry point established: the run
    fails with the bounded ``output-unsafe-target`` error and neither directory receives
    the receipt.
    """

    world = _build_world(tmp_path, monkeypatch)
    module = world["module"]
    backends = world["backends"]
    root = tmp_path / "operator-root"
    root.mkdir()
    parent = root / "private"
    output = parent / "receipt.json"
    established = module._establish_private_output_target(output)
    swapped: list[bool] = []
    real_summary = module._public_live_summary

    def swapping_summary(record: Mapping[str, Any]) -> dict[str, Any]:
        if not swapped:
            # The operator directory is renamed and replaced at the same name while the
            # qualification is in flight, exactly as the review's probe did.
            swapped.append(True)
            parent.rename(root / "original-private")
            parent.mkdir()
            parent.chmod(0o700)
        return real_summary(record)

    monkeypatch.setattr(module, "_public_live_summary", swapping_summary)

    with pytest.raises(module.QualificationError) as failure:
        _run_live(world, output, established_parent=established)

    assert swapped == [True]
    assert failure.value.code == "output-unsafe-target"
    # The orchestration really forwarded the identity establishment accepted.
    assert backends.output_parents[str(output)] == established
    assert list((root / "original-private").iterdir()) == []
    assert list(parent.iterdir()) == []
    assert not output.exists()


def test_offline_receipt_write_refuses_a_parent_replaced_during_the_checks(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """The deterministic lane binds the same established identity before it writes."""

    module = _qualification_module()
    root = tmp_path / "operator-root"
    root.mkdir()
    parent = root / "private"
    output = parent / "receipt.json"
    scratch = tmp_path / "scratch"
    scratch.mkdir()
    monkeypatch.setenv("TMPDIR", str(scratch))
    stub_summary = {
        "schema_version": module.SCHEMA_VERSION,
        "mode": "offline",
        "checks": [{"check": "stub", "status": "pass", "detail": "injected"}],
    }

    def swapping_checks(workspace: Path) -> dict[str, Any]:
        parent.rename(root / "original-private")
        parent.mkdir()
        parent.chmod(0o700)
        return dict(stub_summary)

    monkeypatch.setattr(module, "run_offline", swapping_checks)

    code = module.main(["--json", "--output", str(output)])
    captured = capsys.readouterr()

    assert code == 1
    payload = json.loads(captured.out)
    assert payload["ok"] is False
    assert payload["error"]["code"] == "output-unsafe-target"
    assert list((root / "original-private").iterdir()) == []
    assert list(parent.iterdir()) == []
    assert not output.exists()
    assert str(output) not in captured.out


def test_private_receipt_write_after_the_directory_is_bound_never_redirects(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The review-round-9 after-open sequence: a bound directory cannot be redirected.

    The reviewer renamed the receipt directory *after* its descriptor was handed back and
    created a replacement at the original name.  The installation is descriptor-relative,
    so no byte can follow the new name: the replacement directory stays empty, the receipt
    exists only inside the established directory (now under its new name), and the run
    fails its final verification with the bounded ``private-output`` error instead of
    emitting a qualified verdict.  That bounded residue is what the guide now states.
    """

    module = _qualification_module()
    root = tmp_path / "operator-root"
    root.mkdir()
    parent = root / "private"
    target = parent / "receipt.json"
    established = module._establish_private_output_target(target)
    real_open = module._open_private_receipt_directory
    swapped: list[bool] = []

    def after_open_rename(directory: Path, *, established_parent: Any = None) -> int:
        descriptor = real_open(directory, established_parent=established_parent)
        # The rename lands after the descriptor is bound: every installation step below is
        # relative to that descriptor, and the name on disk is no longer the same directory.
        swapped.append(True)
        parent.rename(root / "original-private")
        parent.mkdir()
        parent.chmod(0o700)
        return descriptor

    monkeypatch.setattr(module, "_open_private_receipt_directory", after_open_rename)

    with pytest.raises(module.QualificationError) as failure:
        module._write_private_output(
            target,
            {"handles": {"message_id": RECEIPT_SEAM_SENTINEL}},
            established_parent=established,
        )

    assert swapped == [True]
    assert failure.value.code == "private-output"
    # The replacement directory at the original name never receives a byte.
    assert list(parent.iterdir()) == []
    assert not _receipt_token_written(parent, RECEIPT_SEAM_SENTINEL)
    # The only receipt is the private one inside the established (renamed) directory.
    established_dir = root / "original-private"
    assert os.stat(established_dir).st_ino == established[1]
    receipt = established_dir / "receipt.json"
    assert receipt.is_file()
    assert stat.S_IMODE(os.lstat(receipt).st_mode) == 0o600
    assert os.lstat(receipt).st_nlink == 1
    assert RECEIPT_SEAM_SENTINEL in receipt.read_text(encoding="utf-8")
    assert list(established_dir.glob("*.tmp")) == []


def test_offline_receipt_write_after_the_directory_is_bound_never_qualifies(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """The deterministic lane reports the same bounded failure and no qualified verdict."""

    module = _qualification_module()
    root = tmp_path / "operator-root"
    root.mkdir()
    parent = root / "private"
    output = parent / "receipt.json"
    scratch = tmp_path / "scratch"
    scratch.mkdir()
    monkeypatch.setenv("TMPDIR", str(scratch))
    real_open = module._open_private_receipt_directory

    def after_open_rename(directory: Path, *, established_parent: Any = None) -> int:
        descriptor = real_open(directory, established_parent=established_parent)
        parent.rename(root / "original-private")
        parent.mkdir()
        parent.chmod(0o700)
        return descriptor

    monkeypatch.setattr(module, "_open_private_receipt_directory", after_open_rename)

    code = module.main(["--json", "--output", str(output)])
    captured = capsys.readouterr()

    assert code == 1
    payload = json.loads(captured.out)
    assert payload["ok"] is False
    assert payload["error"]["code"] == "private-output"
    assert "qualified" not in payload
    assert list(parent.iterdir()) == []
    assert not output.exists()
    receipt = root / "original-private" / "receipt.json"
    assert receipt.is_file()
    assert stat.S_IMODE(os.lstat(receipt).st_mode) == 0o600
    assert str(output) not in captured.out
