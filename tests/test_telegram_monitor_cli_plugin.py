"""``aether monitor`` CLI, native control tool and plugin packaging (MON-05).

The deterministic half uses a Hermes-free manager interpreter and a disposable monitor
state root.  The ``hermes_exact`` half runs against the release-locked public Hermes
checkout to prove the real cron/plugin/toolset interfaces the monitor registers.
"""

from __future__ import annotations

import configparser
import contextlib
import hashlib
import importlib.util
import io
import json
import os
import re
import shutil
import signal
import stat
import subprocess
import sys
import textwrap
import time
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


def _lab_module() -> Any:
    """Load ``scripts/telegram_monitor_lab.py`` the way the harness imports it."""

    spec = importlib.util.spec_from_file_location(
        "telegram_monitor_lab", ROOT / "scripts" / "telegram_monitor_lab.py"
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules["telegram_monitor_lab"] = module
    spec.loader.exec_module(module)
    return module


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
    created: str = "2026-09-10T14:00:40.000000Z",
    updated: str = "2026-09-10T14:00:40.000000Z",
    text_hash: str = "0" * 64,
) -> Any:
    return SimpleNamespace(
        part_index=index,
        state=state,
        attempts=1,
        created_at_utc=created,
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

    # The legitimate shipped-path pending->accepted two-phase write before render is accepted
    legit_decision = _confirmed_decision(payload, narrative)
    legit_decision["narrative"] = _fake_narrative(
        payload["report_id"],
        result=narrative,
        created="2026-09-10T14:00:20.000000Z",
        updated="2026-09-10T14:00:35.000000Z",
    )
    legit_boundary = module._boundary_record(
        legit_decision,
        expected_items=dict(expected_items),
        expected_gaps=frozenset(),
        language=None,
        job_record=_job_record(),
        run_evidence=_run_evidence(payload["report_id"]),
        expected_cutoff_utc=EXPECTED_CUT,
    )
    assert legit_boundary["narration_writes"] == 1
    assert legit_boundary["narration_status"] == "accepted"

    # A second narration write after render enqueue is refused
    assert (
        fail_with(
            narrative=_fake_narrative(
                payload["report_id"],
                result=narrative,
                created="2026-09-10T14:00:20.000000Z",
                updated="2026-09-10T14:00:50.000000Z",
            )
        )
        == "multiple-narrations"
    )
    # An inverted narrative timestamp is refused
    assert (
        fail_with(
            narrative=_fake_narrative(
                payload["report_id"],
                result=narrative,
                created="2026-09-10T14:00:35.000000Z",
                updated="2026-09-10T14:00:20.000000Z",
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


def test_narration_oracle_guards_shipped_two_phase_write(tmp_path: Path) -> None:
    """The narration oracle accepts the shipped two-phase write and refuses a second narration."""

    module = _qualification_module()
    from aether_agents.monitor import reporting as reporting_module
    from aether_agents.monitor.store import MonitorStore

    store = MonitorStore(tmp_path)
    store.set_enabled(True)
    cutoff = EXPECTED_CUT
    lease = store.acquire_collection_lease(cutoff, owner_id="collector-1", ttl_seconds=300)
    assert lease is not None

    payload = _live_payload()
    report_id = payload["report_id"]

    snapshot = store.create_snapshot(
        cutoff_utc=payload["cutoff_utc"],
        previous_cutoff_utc=payload["previous_cutoff_utc"],
        collected_at_utc=payload["collected_at_utc"],
        watermarks={},
        payload=payload,
        coverage_gaps=(),
        report_id=report_id,
        lease=lease,
    )

    # Phase 1: handoff state written as pending
    store.put_narrative(
        report_id, structured_result=None, narrator_session_id=None, attempt_status="pending"
    )

    # Phase 2: validated narrative written as accepted
    structured = _live_narrative(payload)
    store.put_narrative(
        report_id,
        structured_result=structured,
        narrator_session_id="cron_native-job-1_test",
        attempt_status="accepted",
    )

    narrative = store.get_narrative(report_id)
    assert narrative is not None
    assert narrative.attempt_status == "accepted"
    assert narrative.structured_result is not None

    # Shipped render and delivery lifecycle
    parts = reporting_module.render_parts(snapshot.payload, narrative.structured_result)
    deliveries = store.enqueue_deliveries(report_id, parts)
    for delivery_part in deliveries:
        claim = store.claim_delivery(
            report_id, delivery_part.part_index, owner_id="delivery-1", ttl_seconds=60
        )
        assert claim is not None
        store.complete_delivery(
            claim, outcome="confirmed", message_id=f"msg_{delivery_part.part_index}"
        )

    confirmed_deliveries = store.list_deliveries(report_id)
    work_key = payload["items"][0]["work_key"]

    decision = {
        "state": "ready",
        "snapshot": snapshot,
        "narrative": narrative,
        "deliveries": confirmed_deliveries,
    }

    # The legitimate two-phase write must satisfy the smoke oracle (cutoff_mode="not-after")
    smoke_record = module._boundary_record(
        decision,
        expected_items={work_key: "running"},
        expected_gaps=frozenset(),
        language=None,
        job_record=_job_record(),
        run_evidence=_run_evidence(report_id),
        expected_cutoff_utc=cutoff,
        cutoff_mode="not-after",
    )
    assert smoke_record["narration_writes"] == 1
    assert smoke_record["narration_status"] == "accepted"
    assert smoke_record["delivery_states"] == ["confirmed"]

    # The legitimate two-phase write must also satisfy the boundary oracle (cutoff_mode="exact")
    boundary_record = module._boundary_record(
        decision,
        expected_items={work_key: "running"},
        expected_gaps=frozenset(),
        language=None,
        job_record=_job_record(),
        run_evidence=_run_evidence(report_id),
        expected_cutoff_utc=cutoff,
        cutoff_mode="exact",
    )
    assert boundary_record["narration_writes"] == 1
    assert boundary_record["narration_status"] == "accepted"

    # Drive a genuine second narration write through the store API (after render)
    store.put_narrative(
        report_id,
        structured_result=structured,
        narrator_session_id="cron_native-job-1_second_run",
        attempt_status="accepted",
    )
    second_narrative = store.get_narrative(report_id)
    second_decision = {
        "state": "ready",
        "snapshot": snapshot,
        "narrative": second_narrative,
        "deliveries": confirmed_deliveries,
    }

    # The second narration write must be refused by the oracle with multiple-narrations
    with pytest.raises(module.QualificationError) as exc_info:
        module._boundary_record(
            second_decision,
            expected_items={work_key: "running"},
            expected_gaps=frozenset(),
            language=None,
            job_record=_job_record(),
            run_evidence=_run_evidence(report_id),
            expected_cutoff_utc=cutoff,
            cutoff_mode="not-after",
        )
    assert exc_info.value.code == "multiple-narrations"

    with pytest.raises(module.QualificationError) as exc_info_exact:
        module._boundary_record(
            second_decision,
            expected_items={work_key: "running"},
            expected_gaps=frozenset(),
            language=None,
            job_record=_job_record(),
            run_evidence=_run_evidence(report_id),
            expected_cutoff_utc=cutoff,
            cutoff_mode="exact",
        )
    assert exc_info_exact.value.code == "multiple-narrations"


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
        "lab": {
            "root_digest": "a" * 64,
            "config_digest": "b" * 64,
            "stamp": "20260910T130000Z",
            "profile": "morfeo",
        },
        "retention": {
            "scheduler_stopped": True,
            "registry_touched": False,
            "laboratory": {"retained": True, "root_digest": "a" * 64},
        },
        "preflight": {
            "destination_digest": "c" * 64,
            "interfaces": {"scheduler": {}},
            "writers": {
                "required_interfaces": ["hermes_state.SessionDB.create_session"],
                "present_interfaces": ["hermes_state.SessionDB.create_session"],
                "artifact_modules": ["hermes_state"],
                "artifact_digests": {"hermes_state": "d" * 64},
                "installed_distributions": {"hermes-agent": "0.20.1"},
                "entry_points": ["aether-telegram-monitor=aether_agents.monitor.hermes_plugin"],
                "effective_roots_resolved": ["hermes_home", "kanban_db"],
            },
            "artifacts": {
                "hermes_state": {"file": "/private/modules/hermes_state.py", "sha256": "d" * 64}
            },
            "effective": {"kanban_db": "/private/lab/hermes/kanban.db"},
        },
        "errors": [],
    }

    public = module._public_live_summary(record)

    rendered = json.dumps(public)
    for private in (
        "424242",
        "monitor-report-1",
        "/private/operator",
        "/private/modules",
        "/private/lab",
        "2026-09-10T13:00:00Z",
        "pipeline:private",
    ):
        assert private not in rendered, private
    # The exact-candidate loading evidence reaches the public summary as names, versions and
    # digests only; the resolved module file and laboratory roots stay in the private receipt.
    assert public["preflight_writers"]["artifact_digests"] == {"hermes_state": "d" * 64}
    assert public["preflight_writers"]["installed_distributions"] == {"hermes-agent": "0.20.1"}
    assert public["preflight_writers"]["entry_points"] == [
        "aether-telegram-monitor=aether_agents.monitor.hermes_plugin"
    ]
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
    assert public["laboratory_retained"] is True
    assert public["scheduler_stopped"] is True
    assert public["operator_registry_touched"] is False
    assert public["idle_confirmed"] is True
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
CUT_TWO = datetime(2026, 9, 10, 11, 1, tzinfo=timezone.utc)
CUT_IDLE = datetime(2026, 9, 10, 11, 2, tzinfo=timezone.utc)
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


def _writer_task_id(entry: Mapping[str, Any], task: Mapping[str, Any]) -> str:
    """The task identity the fake shipped kanban writer assigns to one manifest task.

    It is deliberately *not* derived from the manifest: the writer owns identity, and the
    lane must follow whatever the writer returns.
    """

    raw = f"writer:{entry['board_slug']}:{task['key']}"
    return "t_" + hashlib.sha256(raw.encode("utf-8")).hexdigest()[:8]


class _FakeBackends:
    """Every live boundary as a fake: no model, no sender, no native scheduler.

    The fake implements the whole :class:`LiveBackends` surface, including the isolated
    laboratory seams, so the orchestration below it is exercised end to end without any
    external effect.  It never creates, renames, unlinks or replaces an operator registry
    entry — there is no such code path left in the harness — and its laboratory record is
    an in-memory mapping under the test's own temporary directory.
    """

    def __init__(
        self,
        *,
        module: Any,
        lab_module: Any,
        store: _EvidenceStore,
        clock: _PhaseClock,
        hermes_home: Path,
        worker: Path,
        scope_root: Path,
        output_dir: Path,
        enable_next_cut: datetime,
        inventory: Sequence[Mapping[str, Any]] = (),
        state_root_value: Path | None = None,
    ) -> None:
        self.module = module
        self.lab_module = lab_module
        self.store = store
        self.clock = clock
        self.hermes_home_value = hermes_home
        self.runtime = worker
        self.scope_root = scope_root
        self.output_dir = output_dir
        self.enable_next_cut = enable_next_cut
        self.state_root_value = state_root_value or scope_root.parents[1]
        self.jobs: dict[str, dict[str, Any]] = {str(job["id"]): dict(job) for job in inventory}
        self.calls: list[str] = []
        self.trigger_calls = 0
        self.environment_gap_values: list[str] = []
        self.environment_gaps_calls: list[dict[str, Any]] = []
        self.trigger_result: dict[str, Any] = {"triggered": True, "errors": []}
        self.output_payloads: dict[str, Any] = {}
        self.output_parents: dict[str, Any] = {}
        self.job_last_run: dict[str, datetime] = {}
        # Injectable fail-closed seams: each one reproduces a bounded refusal of the
        # isolated laboratory so a test can prove it can never emit a qualified verdict.
        self.preflight_problems: list[str] = []
        self.context_preflight_problems: list[str] = []
        self.create_failure: str | None = None
        self.fixture_failure: str | None = None
        self.transition_failure: str | None = None
        self.enable_failure: str | None = None
        self.off_failure: bool = False
        self.scheduler_start_failure: str | None = None
        self.scheduler_stop_failure: bool = False
        self.retention_problems: list[str] = []
        self.scheduler_running = False
        self.lab_plan_value: Any = None
        self.schedule_update_result: dict[str, Any] | None = None
        self.schedule_update_failure: str | None = None
        self.scheduler_result: dict[str, Any] | None = None
        # Identity seams: the fake owns task identity (like the shipped writer), and the
        # lane may only use what the writer returned.  ``fixture_binds_identities=False``
        # reproduces a lane that keeps an identity of its own instead.
        self.fixture_binds_identities: bool = True
        self.identity_shift: bool = False
        self.writer_identities: dict[str, str] = {}
        self.transitioned_identities: list[str] = []

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

    def _job_snapshot(self, job_id: str) -> dict[str, Any] | None:
        job = self.jobs.get(job_id)
        if job is None:
            return None
        # The native scheduler executes the owned job at each scheduled phase boundary.
        for phase in self.clock.phases:
            if phase <= self.clock.now():
                previous = self.job_last_run.get(job_id)
                self.job_last_run[job_id] = phase if previous is None else max(previous, phase)
        last_run = self.job_last_run.get(job_id)
        schedule = str(job.get("schedule") or self.module.NATIVE_SCHEDULE)
        next_cut = self.enable_next_cut
        if next_cut <= self.clock.now():
            future_phases = [phase for phase in self.clock.phases if phase > self.clock.now()]
            if future_phases:
                next_cut = future_phases[0]
            else:
                next_cut = (self.clock.now() + timedelta(minutes=1)).replace(
                    second=0, microsecond=0
                )
        return {
            "id": job_id,
            "name": self.module.NATIVE_JOB_NAME,
            "script": self.module.PRECHECK_SCRIPT_NAME,
            "deliver": "local",
            "schedule": schedule,
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
            "next_run_at": _stamp(next_cut),
            "last_run_at": _stamp(last_run) if last_run else None,
            "last_status": "ok" if last_run else None,
            "last_error": None,
            "paused": bool(job.get("paused")),
            "output_dir": str(self.output_dir),
        }

    def lab_preflight(self, plan: Any, *, interpreter: Path) -> dict[str, Any]:
        self.calls.append("lab_preflight")
        # The read-only phase: layout, decision-only configuration, borrowed access and the
        # provisioned route.  It resolves no writer surface and creates nothing.
        return {
            "problems": list(self.preflight_problems),
            "config_digest": "0" * 64,
            "config_text": "model:\n  default: candidate\n",
            "access": {"names": ["TELEGRAM_BOT_TOKEN", "TELEGRAM_HOME_CHANNEL"], "present": {}},
            "interfaces": {
                "scheduler": {"class": "cron.scheduler_provider.InProcessCronScheduler"},
                "jobs": {
                    "get_job": True,
                    "update_job": True,
                    "compute_next_run": True,
                    "get_due_jobs": True,
                },
            },
            "destination_digest": "d" * 64,
            "destination_thread_present": False,
            "_access": {"TELEGRAM_BOT_TOKEN": "borrowed"},
            "_environment": {"HOME": str(plan.home), "HERMES_HOME": str(plan.hermes_home)},
        }

    def lab_context_preflight(
        self, plan: Any, preflight: Mapping[str, Any], *, interpreter: Path
    ) -> dict[str, Any]:
        self.calls.append("lab_context_preflight")
        # The in-laboratory gate: resolved inside the created root, before any effect.
        return {
            "problems": list(self.context_preflight_problems),
            "interfaces": {
                "scheduler": {"class": "cron.scheduler_provider.InProcessCronScheduler"},
                "jobs": {
                    "get_job": True,
                    "update_job": True,
                    "compute_next_run": True,
                    "get_due_jobs": True,
                },
            },
            # The same projection the shipped gate produces: names, digests, entry points
            # and versions, never a module file or laboratory path.
            "writers": self.module.telegram_monitor_lab.writer_summary(
                self.module._writer_probe_sample(plan)
            ),
            "artifacts": {"hermes_state": {"file": "/lab/hermes_state.py", "sha256": "0" * 64}},
            "effective": {"kanban_db": str(plan.hermes_home / "kanban.db")},
            "destination_digest": "d" * 64,
            "destination_thread_present": False,
        }

    def lab_create(self, plan: Any, preflight: Mapping[str, Any]) -> dict[str, Any]:
        self.calls.append("lab_create")
        if self.create_failure is not None:
            raise self.module.QualificationError(self.create_failure, "injected create failure")
        self.lab_plan_value = plan
        return {
            "schema_version": "aether.telegram-monitor.qualification-lab.v1",
            "stamp": plan.stamp,
            "profile": "morfeo",
            "root": str(plan.root),
            "state_root": str(plan.lab_state_root),
            "hermes_home": str(plan.hermes_home),
            "scope_root": str(plan.root / "scope"),
            "config_digest": preflight["config_digest"],
            "created_at_utc": _stamp(self.clock.now()),
            "environment": dict(preflight["_environment"]),
            "retained": True,
        }

    def lab_store(self, lab: Mapping[str, Any]) -> Any:
        self.calls.append("lab_store")
        return self.store

    def lab_fixture(
        self, interpreter: Path, lab: Mapping[str, Any], manifest: Sequence[dict[str, Any]]
    ) -> dict[str, Any]:
        self.calls.append("lab_fixture")
        if self.fixture_failure is not None:
            raise self.module.QualificationError(self.fixture_failure, "injected fixture failure")
        boards: list[str] = []
        sessions: list[str] = []
        seeded: list[dict[str, Any]] = []
        for entry in manifest:
            entry["native_project_id"] = f"native-{entry['letter'].lower()}"
            board_dir = Path(lab["hermes_home"]) / "kanban" / "boards" / entry["board_slug"]
            board_dir.mkdir(parents=True, exist_ok=True)
            boards.append(entry["board_slug"])
            sessions.extend(session["id"] for session in entry["sessions"])
            for task in entry["tasks"]:
                # The fake stands in for the shipped kanban writer: it assigns the task
                # identity itself and never echoes a manifest-declared id, so the lane can
                # only use the identities the writer actually returned.
                seeded.append(
                    {
                        "key": task["key"],
                        "task_id": _writer_task_id(entry, task),
                        "status": task["status"],
                    }
                )
        if self.fixture_binds_identities:
            # ``identity_shift`` reproduces a lane whose manifest keeps an identity of its
            # own instead of the one the writer returned; the writer's own record stays
            # truthful, so the lane cannot pass by agreeing with itself.
            bound = [
                ({**item, "task_id": f"{item['task_id']}-shifted"} if self.identity_shift else item)
                for item in seeded
            ]
            self.module._bind_writer_identities(manifest, bound)
        self.writer_identities = {str(item["key"]): str(item["task_id"]) for item in seeded}
        return {
            "projects": [
                {
                    "project_id": entry["project_id"],
                    "native_project_id": entry["native_project_id"],
                }
                for entry in manifest
            ],
            "boards": boards,
            "sessions": sessions,
            "tasks": seeded,
            "direct": [
                interval
                for entry in manifest
                for interval in entry.get("direct", {}).get("intervals", ())
            ],
        }

    def lab_transition(
        self, interpreter: Path, lab: Mapping[str, Any], manifest: Sequence[dict[str, Any]]
    ) -> dict[str, Any]:
        self.calls.append("lab_transition")
        if self.transition_failure is not None:
            raise self.module.QualificationError(
                self.transition_failure, "injected transition failure"
            )
        completed: list[str] = []
        for entry in manifest:
            identities = {str(task["key"]): str(task["task_id"]) for task in entry["tasks"]}
            for task in entry["transition"]:
                task_id = identities.get(str(task["key"]), "")
                if not task_id:
                    # Faithful to the shipped probe: the transition completes exactly the
                    # identity the writer returned, and refuses anything else.
                    raise self.module.QualificationError(
                        "lab-transition", "the transition key carries no writer identity"
                    )
                completed.append(task_id)
        self.transitioned_identities = list(completed)
        return {"completed": completed}

    def lab_scheduler_start(self, interpreter: Path, lab: Mapping[str, Any]) -> dict[str, Any]:
        self.calls.append("lab_scheduler_start")
        if self.scheduler_start_failure is not None:
            raise self.module.QualificationError(
                self.scheduler_start_failure, "injected scheduler start failure"
            )
        self.scheduler_running = True
        result = {
            "pid": 4242,
            "scheduler": "builtin",
            "scheduler_class": "cron.scheduler_provider.InProcessCronScheduler",
            "execution_mode": "native-scheduled-tick",
            "interval_seconds": self.module.LAB_SCHEDULER_INTERVAL_SECONDS,
            "stop_file": str(Path(lab["root"]) / "control" / "scheduler-stop"),
            "ready": True,
        }
        if self.scheduler_result is not None:
            result.update(self.scheduler_result)
        return result

    def lab_scheduler_stop(
        self, lab: Mapping[str, Any], scheduler: Mapping[str, Any]
    ) -> dict[str, Any]:
        self.calls.append("lab_scheduler_stop")
        if self.scheduler_stop_failure:
            # Faithful to the shipped helper: a runner that does not stop is never success.
            raise self.module.QualificationError(
                "lab-scheduler-stop", "the bounded native scheduler instance did not stop"
            )
        self.scheduler_running = False
        return {"stopped": True, "cooperative": True}

    def lab_release(self, plan: Any) -> dict[str, Any]:
        self.calls.append("lab_release")
        return {
            "retained": True,
            "root_digest": "r" * 64,
            "removed": False,
            "problems": list(self.retention_problems),
        }

    def state_root(self) -> Path:
        self.calls.append("state_root")
        return self.state_root_value

    def profile_home(self) -> Path:
        return self.state_root_value / "profiles" / "morfeo"

    def environ(self) -> Mapping[str, str]:
        return dict(os.environ)

    def lab_plan(self, state_root_value: Path, stamp: str) -> Any:
        self.calls.append("lab_plan")
        return self.lab_module.build_plan(
            self.state_root_value / "lab-host", stamp, token="0123456789ab"
        )

    def job_inventory(
        self, interpreter: Path, environment: Mapping[str, str] | None = None
    ) -> list[dict[str, Any]]:
        self.calls.append("job_inventory")
        return [dict(job) for job in self.jobs.values()]

    def job_record(
        self,
        interpreter: Path,
        job_id: str,
        environment: Mapping[str, str] | None = None,
    ) -> dict[str, Any] | None:
        self.calls.append(f"job_record:{job_id}")
        return self._job_snapshot(job_id)

    def trigger_job(
        self,
        interpreter: Path,
        job_id: str,
        environment: Mapping[str, str] | None = None,
    ) -> dict[str, Any]:
        self.calls.append(f"trigger_job:{job_id}")
        self.trigger_calls += 1
        if not self.trigger_result.get("triggered"):
            return dict(self.trigger_result)
        # A real native trigger and its scheduler tick take a bounded amount of time.
        self.clock.value += timedelta(seconds=50)
        self.job_last_run[job_id] = self.clock.now()
        return dict(self.trigger_result)

    def lab_control(self, lab: Mapping[str, Any], action: str) -> dict[str, Any]:
        self.calls.append(f"lab_control:{action}")
        settings = self.store.settings
        if action == "on":
            if self.enable_failure is not None:
                raise self.module.QualificationError(self.enable_failure, "injected enable failure")
            existing = next(
                (job for job in self.jobs.values() if job["name"] == self.module.NATIVE_JOB_NAME),
                None,
            )
            created = existing is None
            job_id = str(existing["id"]) if existing is not None else SYNTHETIC_JOB_ID
            self.jobs[job_id] = {
                "id": job_id,
                "name": self.module.NATIVE_JOB_NAME,
                "schedule": self.module.NATIVE_SCHEDULE,
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
        if self.off_failure:
            raise self.module.QualificationError("manual-off", "injected off failure")
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

    def lab_schedule_update(
        self, interpreter: Path, lab: Mapping[str, Any], job_id: str
    ) -> dict[str, Any]:
        self.calls.append(f"lab_schedule_update:{job_id}")
        if self.schedule_update_failure is not None:
            raise self.module.QualificationError(
                self.schedule_update_failure, "injected schedule update failure"
            )
        job = self.jobs.get(job_id)
        before_schedule = str(job.get("schedule") or self.module.NATIVE_SCHEDULE) if job else None
        if job is None:
            raise self.module.QualificationError(
                "lab-schedule-update", "injected missing schedule-update job"
            )
        job["schedule"] = self.module.ACCELERATED_LAB_SCHEDULE
        result = {
            "updated": True,
            "native_interface": "cron.jobs.update_job",
            "execution_mode": "native-lab-schedule-update",
            "private_lab_only": True,
            "production_schedule": before_schedule,
            "accelerated_schedule": self.module.ACCELERATED_LAB_SCHEDULE,
            "before": {
                "id": job_id,
                "name": self.module.NATIVE_JOB_NAME,
                "script": self.module.PRECHECK_SCRIPT_NAME,
                "deliver": "local",
                "schedule": before_schedule,
                "next_run_at": _stamp(self.enable_next_cut),
                "paused": False,
            },
            "after": {
                "id": job_id,
                "name": self.module.NATIVE_JOB_NAME,
                "script": self.module.PRECHECK_SCRIPT_NAME,
                "deliver": "local",
                "schedule": self.module.ACCELERATED_LAB_SCHEDULE,
                "next_run_at": _stamp(self.enable_next_cut),
                "paused": False,
            },
            "store_root": str(lab["hermes_home"]),
        }
        if self.schedule_update_result is not None:
            result.update(self.schedule_update_result)
        return result

    def owner_language(
        self, interpreter: Path, environment: Mapping[str, str] | None = None
    ) -> str | None:
        return "English"

    def environment_gaps(self, store: Any, *args: Any, **kwargs: Any) -> list[str]:
        self.calls.append("environment_gaps")
        self.environment_gaps_calls.append({"store": store, "args": args, "kwargs": kwargs})
        return list(self.environment_gap_values)

    def session_sources(
        self, hermes_home: Path, environment: Mapping[str, str] | None = None
    ) -> dict[str, Any]:
        self.calls.append("session_sources")
        return {"sess-existing": {"source": "tui"}}

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
    """One synthetic pipeline identity shaped like the shipped source adapter.

    The source references use the identity the fake shipped writer assigns, computed the
    same way the fake computes it.  The manifest itself carries no task identity until the
    fixture binds what the writer returned, so a lane that invents one cannot match these
    references.
    """

    from aether_agents.monitor.sources import SourceItem

    work_key = f"pipeline:{entry['project_id']}:{entry['contract_id']}:{entry['origin_session']}"
    current: list[dict[str, Any]] = []
    resolved: list[dict[str, Any]] = []
    for task in entry["tasks"]:
        fact = {
            "ref": f"board:{entry['board_slug']}:task:{_writer_task_id(entry, task)}:result",
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
    backends_lab_module = _lab_module()
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
        "lab_module": backends_lab_module,
        "manifest": manifest,
        "scope_root": scope_root,
        "clock": clock,
        "store": store,
        "hermes_home": hermes_home,
        "output_dir": output_dir,
    }
    backends = _FakeBackends(
        module=module,
        lab_module=backends_lab_module,
        state_root_value=tmp_path / "xdg-state" / "aether",
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
    # Corpus claims travel through the shipped completion writer, so only the case-bearing
    # tasks carry a case key and the open work carries none.
    assert [task["case"] for task in project_a["tasks"]] == [
        None,
        "contradictory",
        "deadline",
        "word_time",
        "malicious",
    ]
    assert [task["case"] for task in project_b["tasks"]] == [None, "partial", None]
    assert project_a["tasks"][1]["result"] == (
        "Phase one checks are complete and everything is green."
    )
    assert project_b["tasks"][1]["result"] == (
        "Partial success: three of five checks pass; the source review is still pending."
    )
    # A completed corpus task and one genuinely open descendant keep project A's contract
    # observable; project B carries a ready root and the pending review alongside its partial success.
    assert [task["status"] for task in project_a["tasks"]] == [
        "running",
        "done",
        "done",
        "done",
        "done",
    ]
    assert [task["status"] for task in project_b["tasks"]] == ["ready", "done", "review"]
    # The between-cut transition names the open work by manifest key: the task identity
    # itself is owned by the shipped kanban writer and is bound only after seeding.
    assert [task["key"] for task in project_a["transition"]] == ["A1"]
    assert [task["key"] for task in project_b["transition"]] == ["B1", "B3"]
    assert all("task_id" not in task for task in project_a["tasks"])
    assert project_a["links"] == [(0, 1), (0, 2), (0, 3), (0, 4)]
    assert project_b["links"] == [(0, 1), (0, 2)]
    assert [task["key"] for task in project_a["tasks"]] == ["A1", "A2", "A3", "A4", "A5"]
    assert project_a["path"].startswith(str(scope_root))
    assert project_a["direct"]["intervals"][0]["outcome"] == "unknown"


def test_scope_manifest_claims_and_sessions_only_carry_supported_writer_inputs(
    tmp_path: Path,
) -> None:
    """Sessions declare only what a shipped writer accepts; nothing is a guessed column."""

    _, manifest = _scope_manifest_for(tmp_path)

    for entry in manifest:
        for session in entry["sessions"]:
            assert set(session) == {
                "id",
                "source",
                "title",
                "cwd",
                "git_repo_root",
                "role",
            }, session
            # The store owns the row timestamps, and the title travels through the shipped
            # title writer; neither is a fixture-supplied keyword.
            assert session["title"].strip()
            assert session["cwd"] == session["git_repo_root"] == entry["path"]


def _seeded_fixture_payload(manifest: Sequence[dict[str, Any]]) -> list[dict[str, Any]]:
    """A child-probe payload shaped exactly like the real shipped-writer fixture output."""

    return [
        {
            "key": task["key"],
            "task_id": _writer_task_id(entry, task),
            "status": task["status"],
        }
        for entry in manifest
        for task in entry["tasks"]
    ]


def test_laboratory_fixture_binds_the_writer_returned_task_identities(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The real helper binds the ids the shipped writer returned, and refuses anything else.

    The child probe is replaced with a payload the shipped writers would produce, so this
    exercises the harness's own binding path: links, the between-cut transition and every
    D12 case reference must follow the returned identities, and an unbound key or a
    duplicated identity must refuse the fixture instead of inventing a value.
    """

    module = _qualification_module()
    _, manifest = _scope_manifest_for(tmp_path)
    payload = _seeded_fixture_payload(manifest)
    monkeypatch.setattr(
        module,
        "_runtime_execute",
        lambda *args, **kwargs: {
            "projects": [
                {
                    "project_id": entry["project_id"],
                    "native_project_id": f"native-{entry['letter']}",
                }
                for entry in manifest
            ],
            "boards": [entry["board_slug"] for entry in manifest],
            "sessions": [session["id"] for entry in manifest for session in entry["sessions"]],
            "tasks": payload,
            "direct": [],
            "errors": [],
        },
    )

    seeded = module._lab_fixture(
        Path("/usr/bin/false"),
        {
            "environment": {},
            "hermes_home": str(tmp_path / "hermes"),
            "state_root": str(tmp_path / "state"),
            "root": str(tmp_path),
        },
        manifest,
    )

    assert [item["key"] for item in seeded["tasks"]] == [item["key"] for item in payload]
    for entry in manifest:
        for task in entry["tasks"]:
            assert task["task_id"] == _writer_task_id(entry, task)
    # Every reference derived after seeding names the writer's identity, never a manifest
    # guess: the case references are built from the bound ids.
    cases = module._case_definitions(manifest)
    assert all(
        task_id in json.dumps(cases)
        for task_id in {
            task["task_id"] for entry in manifest for task in entry["tasks"] if task["case"]
        }
    )
    rendered = json.dumps(cases)
    assert "board:" + manifest[0]["board_slug"] + ":task:" in rendered

    # A payload that does not cover every manifest key refuses the whole binding.
    for broken in (
        payload[:-1],
        [*payload[:-1], {**payload[-1], "key": payload[0]["key"]}],
        [*payload[:-1], {**payload[-1], "task_id": payload[0]["task_id"]}],
        [*payload[:-1], {**payload[-1], "task_id": ""}],
    ):
        _, fresh = _scope_manifest_for(tmp_path)
        monkeypatch.setattr(
            module,
            "_runtime_execute",
            lambda *args, **kwargs: {
                "projects": [
                    {
                        "project_id": entry["project_id"],
                        "native_project_id": f"native-{entry['letter']}",
                    }
                    for entry in fresh
                ],
                "boards": [entry["board_slug"] for entry in fresh],
                "sessions": [],
                "tasks": broken,
                "direct": [],
                "errors": [],
            },
        )
        with pytest.raises(module.QualificationError) as error:
            module._lab_fixture(
                Path("/usr/bin/false"),
                {
                    "environment": {},
                    "hermes_home": str(tmp_path / "hermes"),
                    "state_root": str(tmp_path / "state"),
                    "root": str(tmp_path),
                },
                fresh,
            )
        assert error.value.code == "lab-fixture"
        # Nothing is half-bound: the refused fixture leaves no identity behind at all.
        assert all("task_id" not in task for entry in fresh for task in entry["tasks"])


def test_laboratory_fixture_refuses_a_child_that_reports_writer_errors(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A child probe that reports a bounded writer error refuses the fixture, never a pass."""

    module = _qualification_module()
    _, manifest = _scope_manifest_for(tmp_path)
    monkeypatch.setattr(
        module,
        "_runtime_execute",
        lambda *args, **kwargs: {"errors": ["fixture-sessions: TypeError"], "tasks": []},
    )

    with pytest.raises(module.QualificationError) as error:
        module._lab_fixture(
            Path("/usr/bin/false"),
            {
                "environment": {},
                "hermes_home": str(tmp_path / "hermes"),
                "state_root": str(tmp_path / "state"),
                "root": str(tmp_path),
            },
            manifest,
        )

    assert error.value.code == "lab-fixture"
    assert "fixture-sessions: TypeError" in json.dumps(error.value.detail)


def test_live_preflight_and_full_run_without_external_effects(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The whole live orchestration runs against fakes: enable, smoke, two cuts, idle."""

    world = _build_world(tmp_path, monkeypatch)
    module = world["module"]
    backends = world["backends"]
    output = tmp_path / "private" / "receipt.json"

    record = _run_live(world, output)

    assert record["ok"] is True, record["errors"]
    assert record["environment"] == {"gaps": []}
    assert len(backends.environment_gaps_calls) == 1
    gap_call = backends.environment_gaps_calls[0]
    expected_hermes_home = Path(backends.lab_plan_value.hermes_home)
    assert gap_call["kwargs"].get("hermes_home") == expected_hermes_home
    assert gap_call["kwargs"].get("lab") is not None
    assert Path(gap_call["kwargs"]["lab"]["hermes_home"]) == expected_hermes_home
    assert record["enable"]["named_job_count"] == 1
    assert record["enable"]["second_enable_same_job"] is True
    assert record["enable"]["shape_ok"] is True
    assert record["enable"]["production_schedule"] == "0 * * * *"
    assert record["enable"]["production_shape_validated"] is True
    assert record["schedule_update"]["native_interface"] == "cron.jobs.update_job"
    assert record["schedule_update"]["private_lab_only"] is True
    assert record["schedule_update"]["before"]["schedule"] == "0 * * * *"
    assert record["schedule_update"]["after"]["schedule"] == "* * * * *"
    assert record["schedule_update"]["validated_job"]["schedule"] == "* * * * *"
    assert record["schedule_update"]["validated_job"]["next_run_at"] is not None
    assert record["schedule_update"]["runtime_schedule_environment"] == {
        "name": "AETHER_MONITOR_QUALIFICATION_SCHEDULE",
        "value": "* * * * *",
        "scope": "private-lab-scheduler-child",
    }
    assert backends.jobs[SYNTHETIC_JOB_ID]["schedule"] == "* * * * *"
    assert record["smoke"]["confirmed"] is True
    assert record["smoke"]["narration_writes"] == 1
    assert record["smoke"]["part_count"] == 3
    assert [len(boundary["work_keys"]) for boundary in record["boundaries"]] == [3, 3]
    assert [boundary["coverage_gaps"] for boundary in record["boundaries"]] == [[], []]
    first_cut = module._parse_utc(record["boundaries"][0]["expected_cutoff_utc"])
    second_cut = module._parse_utc(record["boundaries"][1]["expected_cutoff_utc"])
    idle_cut = module._parse_utc(record["idle"]["cutoff_utc"])
    assert first_cut is not None and second_cut is not None and idle_cut is not None
    assert second_cut - first_cut == timedelta(minutes=1)
    assert idle_cut - second_cut == timedelta(minutes=1)
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
    # The laboratory is isolated and retained rather than restored: no operator state was
    # displaced, the lab root stays as declared evidence and its scheduler is stopped.
    assert record["retention"]["laboratory"]["retained"] is True
    assert record["retention"]["registry_touched"] is False
    assert record["retention"]["scheduler_stopped"] is True
    assert record["scheduler"]["stopped"] is True
    assert record["preflight"]["problems"] == []
    assert record["lab"]["retained"] is True
    assert record["scope"]["seeded"]["projects"] == 2
    # The lane uses exactly the task identities the shipped writer returned: the manifest
    # carries no identity of its own, the between-cut transition completes the returned
    # ids, and every boundary source reference is built from them.
    bound = {item["key"]: item["task_id"] for item in record["scope"]["task_identities"]}
    assert record["scope"]["identity_source"] == "shipped-kanban-writer"
    assert bound == backends.writer_identities
    assert sorted(backends.transitioned_identities) == sorted(
        bound[key] for key in ("A1", "B1", "B3")
    )
    reference_facts = set(record["boundaries"][0]["source_facts"])
    for entry in world["manifest"]:
        for task in entry["tasks"]:
            expected = f"board:{entry['board_slug']}:task:{bound[task['key']]}:result"
            assert expected in reference_facts, expected
    assert backends.trigger_calls == 1
    order = backends.calls
    assert order.index("lab_preflight") < order.index("lab_create")
    # The in-laboratory gate runs inside the created root and before anything is seeded or
    # spent; the writer surface and the loaded artifacts it resolves are part of the record.
    assert order.index("lab_create") < order.index("lab_context_preflight")
    assert order.index("lab_context_preflight") < order.index("lab_fixture")
    assert order.index("lab_context_preflight") < order.index("lab_control:on")
    assert order.index("lab_fixture") < order.index("lab_control:on")
    assert order.index("lab_control:on") < order.index("lab_schedule_update:" + SYNTHETIC_JOB_ID)
    assert order.index("lab_schedule_update:" + SYNTHETIC_JOB_ID) < order.index(
        "lab_scheduler_start"
    )
    assert order.index("lab_scheduler_start") < order.index("trigger_job:" + SYNTHETIC_JOB_ID)
    assert order.index("lab_transition") < order.index("lab_control:off")
    assert order.index("lab_control:off") < order.index("lab_scheduler_stop")
    assert order.index("lab_scheduler_stop") < order.index("lab_release")
    # The gate's projection is what the receipt and the public summary carry.
    assert record["preflight"]["writers"]["required_interfaces"] == sorted(
        name for name, _ in world["lab_module"].WRITER_REQUIREMENTS
    )
    assert set(record["preflight"]["artifacts"]) == {"hermes_state"}
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
    assert public["production_schedule"] == "0 * * * *"
    assert public["production_shape_validated"] is True
    assert public["accelerated_lab_schedule"] == "* * * * *"
    assert public["accelerated_schedule_update"] == {
        "updated": True,
        "native_interface": "cron.jobs.update_job",
        "private_lab_only": True,
        "from": "0 * * * *",
        "to": "* * * * *",
        "unrelated_jobs_unchanged": True,
    }
    assert public["temporal_oracle"] == "real-minute-boundaries-in-private-lab"
    assert public["production_hourly_evidence"] is False
    assert public["elapsed_hour_evidence"] is False
    assert public["accelerated_boundary_timestamps_utc"] == [
        record["boundaries"][0]["expected_cutoff_utc"],
        record["boundaries"][1]["expected_cutoff_utc"],
    ]
    assert public["accelerated_idle_timestamp_utc"] == record["idle"]["cutoff_utc"]
    assert public["native_scheduler_class"] == "cron.scheduler_provider.InProcessCronScheduler"
    assert public["scheduler_execution_mode"] == "native-scheduled-tick"
    assert public["scheduler_interval_seconds"] == 1
    assert public["smoke_confirmed"] is True
    assert public["laboratory_retained"] is True
    assert public["scheduler_stopped"] is True
    assert public["operator_registry_touched"] is False
    assert set(public["cases"].values()) == {"observed"}
    assert public["case_failures"] == []
    assert public["semantic_certification"]["certified"] is False
    assert set(public["semantic_certification"]["adjudication_required"]) == set(public["cases"])
    assert public["semantic_certification"]["retained_private_comparison"] is True
    assert any("deterministic" in entry for entry in public["qualified_scope"])
    assert any("adjudication" in entry for entry in public["unqualified_scope"])


def test_failure_path_disables_lab_before_stopping_scheduler(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A failed live phase pauses the lab job before the scheduler stop attempt."""
    world = _build_world(tmp_path, monkeypatch)
    backends = world["backends"]
    backends.scheduler_result = {"execution_mode": "forced-tick"}
    output = tmp_path / "private" / "receipt.json"

    with pytest.raises(world["module"].QualificationError) as error:
        _run_live(world, output)

    assert error.value.code == "scheduler-evidence"
    order = backends.calls
    assert order.index("lab_control:off") < order.index("lab_scheduler_stop")
    assert order.count("lab_control:off") == 1
    receipt = json.loads(output.read_text(encoding="utf-8"))
    assert receipt["off"]["failure_path"] is True
    assert receipt["off"]["enabled_after_off"] is False
    assert receipt["off"]["job_paused"] is True
    assert receipt["retention"]["scheduler_stopped"] is True
    assert receipt["scheduler"]["stopped"] is True


def test_d16_schedule_evidence_rejects_manual_and_custom_substitutes() -> None:
    """The qualification contract accepts only native update and scheduler attestations."""

    module = _qualification_module()
    update = {
        "updated": True,
        "native_interface": "cron.jobs.update_job",
        "execution_mode": "native-lab-schedule-update",
        "private_lab_only": True,
        "production_schedule": "0 * * * *",
        "accelerated_schedule": "* * * * *",
        "before": {"schedule": "0 * * * *"},
        "after": {"schedule": "* * * * *"},
    }
    scheduler = {
        "scheduler_class": "cron.scheduler_provider.InProcessCronScheduler",
        "execution_mode": "native-scheduled-tick",
        "interval_seconds": 1,
    }
    assert module._schedule_update_evidence_ok(update) is True
    assert module._scheduled_evidence_ok(update, scheduler) is True
    assert (
        module._schedule_update_evidence_ok({**update, "native_interface": "manual_tick"}) is False
    )
    assert module._schedule_update_evidence_ok({**update, "execution_mode": "forced-fire"}) is False
    assert (
        module._scheduled_evidence_ok(update, {**scheduler, "scheduler_class": "custom.Scheduler"})
        is False
    )
    assert (
        module._scheduled_evidence_ok(update, {**scheduler, "execution_mode": "manual-tick"})
        is False
    )
    assert module._check_lab_schedule_contract() == (
        "pass",
        "production remains 0 * * * *, the private lab alone updates through "
        "cron.jobs.update_job to * * * * *, and scheduled evidence excludes forced ticks",
    )


def test_d16_native_update_changes_only_the_private_lab_job(tmp_path: Path) -> None:
    """The real cron API updates one lab job and leaves a sibling job unchanged."""

    module = _qualification_module()
    runtime = Path(os.environ.get("AETHER_HERMES_PYTHON", "").strip())
    if not runtime.is_file():
        runtime = next(
            (
                parent / "home" / ".venv-hermes" / "bin" / "python"
                for parent in Path(__file__).resolve().parents
                if (parent / "home" / ".venv-hermes" / "bin" / "python").is_file()
            ),
            Path(""),
        )
    if not runtime.is_file():
        pytest.skip("product runtime interpreter not available")

    root = tmp_path / "laboratory"
    hermes_home = root / "hermes" / "profiles" / "morfeo"
    home = root / "home"
    tmp = root / "tmp"
    cwd = root / "work"
    for path in (hermes_home, home, tmp, cwd):
        path.mkdir(parents=True, exist_ok=True)
    environment = {
        "PATH": os.environ.get("PATH", ""),
        "HOME": str(home),
        "HERMES_HOME": str(hermes_home),
        "TMPDIR": str(tmp),
        "PYTHONDONTWRITEBYTECODE": "1",
        "PYTHONPATH": str(module.SOURCE_ROOT),
    }
    create_body = """
import json
from cron import jobs

owned = jobs.create_job(
    prompt="test monitor",
    schedule="0 * * * *",
    name="Aether Telegram Monitor",
    deliver="local",
    script="aether_monitor_precheck.py",
)
other = jobs.create_job(
    prompt="unrelated",
    schedule="0 * * * *",
    name="Unrelated qualification job",
    deliver="local",
    script="unrelated.py",
)
print(json.dumps({"owned": owned["id"], "other": other["id"]}))
"""
    created = module._runtime_execute(runtime, create_body, environment=environment, cwd=cwd)
    lab = {
        "root": str(root),
        "hermes_home": str(hermes_home),
        "cwd": str(cwd),
        "environment": environment,
    }

    result = module._lab_schedule_update(runtime, lab, str(created["owned"]))

    assert result["native_interface"] == "cron.jobs.update_job"
    assert result["private_lab_only"] is True
    assert result["before"]["schedule"] == "0 * * * *"
    assert result["after"]["schedule"] == "* * * * *"
    assert result["after"]["next_run_at"]
    inspect_body = """
import json
from cron import jobs

owned = jobs.get_job(OWNED_JSON)
other = jobs.get_job(OTHER_JSON)
def schedule(job):
    value = job.get("schedule") if isinstance(job, dict) else None
    return value.get("expr") if isinstance(value, dict) else value
print(json.dumps({"owned": schedule(owned), "other": schedule(other)}))
"""
    inspect_body = (
        f"OWNED_JSON = {str(created['owned'])!r}\n"
        f"OTHER_JSON = {str(created['other'])!r}\n" + inspect_body
    )
    inspected = module._runtime_execute(runtime, inspect_body, environment=environment, cwd=cwd)
    assert inspected == {"owned": "* * * * *", "other": "0 * * * *"}


def test_job_run_evidence_distinguishes_active_and_idle_runs_across_overlapping_minute_window(
    tmp_path: Path,
) -> None:
    """The idle run record is attributed by its silent gate across overlapping windows."""

    module = _qualification_module()
    output_dir = tmp_path / "native-runs"
    output_dir.mkdir(parents=True)

    base_time = datetime(2026, 9, 10, 11, 0, tzinfo=timezone.utc)
    cut_two = base_time + timedelta(minutes=1)  # 11:01:00
    cut_idle = base_time + timedelta(minutes=2)  # 11:02:00

    # Active cut 2 completes and writes output at 11:01:05 (non-silent).
    path_cut2 = output_dir / "run-cut2.md"
    path_cut2.write_text("digest rpt_cut2_active\nConfirmed delivery parts.", encoding="utf-8")
    t_cut2 = (cut_two + timedelta(seconds=5)).timestamp()
    os.utime(path_cut2, (t_cut2, t_cut2))

    # Idle cut completes and writes output at 11:02:04 (silent).
    path_idle = output_dir / "run-idle.md"
    path_idle.write_text(
        "# Cron Job: Aether Telegram Monitor\n\n"
        "Script gate returned `wakeAgent=false` — agent skipped.\n",
        encoding="utf-8",
    )
    t_idle = (cut_idle + timedelta(seconds=4)).timestamp()
    os.utime(path_idle, (t_idle, t_idle))

    # 1. Active cut 2 evidence: expected_report_id selects the active run.
    active_ev = module._job_run_evidence(
        output_dir,
        window_start=cut_two - timedelta(minutes=1),
        window_end=cut_two + timedelta(minutes=1),
        expected_report_id="rpt_cut2_active",
    )
    assert active_ev["count"] == 1
    assert active_ev["silent"] is False
    assert active_ev["contents"][0]["name"] == "run-cut2.md"

    # 2. Idle window [cut_idle - 1min, cut_idle + 1min] contains both cut2 and idle files.
    unfiltered = module._job_run_evidence(
        output_dir,
        window_start=cut_idle - timedelta(minutes=1),
        window_end=cut_idle + timedelta(minutes=1),
    )
    assert unfiltered["count"] == 2

    # 3. Idle cut with require_silent=True filters out the active cut and isolates the idle run.
    idle_ev = module._job_run_evidence(
        output_dir,
        window_start=cut_idle - timedelta(minutes=1),
        window_end=cut_idle + timedelta(minutes=1),
        require_silent=True,
    )
    assert idle_ev["count"] == 1
    assert idle_ev["silent"] is True
    assert idle_ev["contents"][0]["name"] == "run-idle.md"


def test_accelerated_lab_selects_boundary_after_overrunning_smoke(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """When the initial smoke overruns across a minute boundary, the harness selects

    the next boundary that will actually fire rather than aborting on the dropped cut.
    """

    skipped_cut = datetime(2026, 9, 10, 10, 6, tzinfo=timezone.utc)
    smoke_done = datetime(2026, 9, 10, 10, 6, 20, tzinfo=timezone.utc)
    cut_one = datetime(2026, 9, 10, 10, 7, tzinfo=timezone.utc)
    cut_two = datetime(2026, 9, 10, 10, 8, tzinfo=timezone.utc)
    cut_idle = datetime(2026, 9, 10, 10, 9, tzinfo=timezone.utc)
    phases = (skipped_cut, smoke_done, cut_one, cut_two, cut_idle)

    world = _build_world(tmp_path, monkeypatch, expose_evidence=False, phases=phases)
    store = world["store"]
    output_dir = world["output_dir"]
    manifest = world["manifest"]
    entry_a, entry_b = manifest
    interval_zero = entry_a["direct"]["intervals"][0]
    interval_one = entry_a["direct"]["intervals"][1]

    # At trigger time, the upcoming cut is skipped_cut (10:06:00), 60s in the future.
    world["backends"].enable_next_cut = skipped_cut

    # The smoke runs and overruns past skipped_cut (finishing at 10:06:20).
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
        reveal=smoke_done,
        collected=smoke_done - timedelta(seconds=5),
    )
    _native_run(output_dir, smoke_done - timedelta(seconds=5), report_id=smoke_report)

    # Active cuts are scheduled at cut_one and cut_two, and idle cut at cut_idle.
    before_report = "rpt_" + "b" * 32
    before_payload = _snapshot_payload(
        report_id=before_report,
        cutoff=cut_one,
        items=(
            _pipeline_item(entry_a, state="running"),
            _pipeline_item(entry_b, state="review"),
            _direct_item(entry_a, interval_zero, "turn_ended_unknown"),
        ),
    )
    before_narrative = _narrative(before_payload)
    store.expose(
        before_report,
        cut_one,
        payload=before_payload,
        narrative=before_narrative,
        deliveries=_confirmed_parts(before_payload, before_narrative),
    )
    _native_run(output_dir, cut_one + timedelta(seconds=5), report_id=before_report)

    after_report = "rpt_" + "c" * 32
    after_payload = _snapshot_payload(
        report_id=after_report,
        cutoff=cut_two,
        items=(
            _pipeline_item(entry_a, state="completed", final=True),
            _pipeline_item(entry_b, state="completed", final=True),
            _direct_item(entry_a, interval_one, "turn_ended_completed"),
        ),
    )
    after_narrative = _narrative(after_payload)
    store.expose(
        after_report,
        cut_two,
        payload=after_payload,
        narrative=after_narrative,
        deliveries=_confirmed_parts(after_payload, after_narrative),
    )
    _native_run(output_dir, cut_two + timedelta(seconds=5), report_id=after_report)

    idle_report = "rpt_" + "d" * 32
    store.expose(
        idle_report,
        cut_idle,
        payload={
            "schema_version": "aether.telegram-monitor.snapshot.v1",
            "report_id": idle_report,
            "cutoff_utc": _stamp(cut_idle),
            "collected_at_utc": _stamp(cut_idle + timedelta(seconds=30)),
            "previous_cutoff_utc": _stamp(cut_two),
            "items": [],
            "coverage_gaps": [],
        },
        resolved=True,
    )
    _native_run(output_dir, cut_idle + timedelta(seconds=4))

    output = tmp_path / "private" / "receipt.json"
    record = _run_live(world, output)
    assert record["ok"] is True
    assert record["smoke"]["confirmed"] is True
    boundaries = record["boundaries"]
    assert len(boundaries) == 2
    assert boundaries[0]["expected_cutoff_utc"] == _stamp(cut_one)
    assert boundaries[1]["expected_cutoff_utc"] == _stamp(cut_two)
    assert record["idle"]["cutoff_utc"] == _stamp(cut_idle)


def test_live_refuses_non_native_schedule_update_before_scheduler(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A manual/forced schedule substitute cannot reach the scheduler or model path."""

    world = _build_world(tmp_path, monkeypatch, expose_evidence=False)
    backends = world["backends"]
    backends.schedule_update_result = {
        "native_interface": "manual_tick",
        "execution_mode": "forced-fire",
    }
    output = tmp_path / "private" / "receipt.json"

    with pytest.raises(world["module"].QualificationError) as error:
        _run_live(world, output)

    assert error.value.code == "lab-schedule-update"
    assert "lab_schedule_update:" + SYNTHETIC_JOB_ID in backends.calls
    assert "lab_scheduler_start" not in backends.calls
    assert backends.trigger_calls == 0
    receipt = json.loads(output.read_text(encoding="utf-8"))
    assert receipt["ok"] is False
    assert receipt["schedule_update"]["native_interface"] == "manual_tick"


def test_live_refuses_custom_scheduler_evidence_before_smoke(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A custom/forced scheduler cannot be counted as a native scheduled laboratory cut."""

    world = _build_world(tmp_path, monkeypatch, expose_evidence=False)
    backends = world["backends"]
    backends.scheduler_result = {
        "scheduler_class": "qualification.CustomScheduler",
        "execution_mode": "forced-tick",
    }
    output = tmp_path / "private" / "receipt.json"

    with pytest.raises(world["module"].QualificationError) as error:
        _run_live(world, output)

    assert error.value.code == "scheduler-evidence"
    assert backends.trigger_calls == 0
    assert "lab_scheduler_start" in backends.calls
    assert "lab_scheduler_stop" in backends.calls
    receipt = json.loads(output.read_text(encoding="utf-8"))
    assert receipt["ok"] is False
    assert receipt["scheduler"]["scheduler_class"] == "qualification.CustomScheduler"


def test_live_refuses_to_continue_without_writer_task_identities(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A lane that never bound the writer identities cannot proceed to any live effect."""

    world = _build_world(tmp_path, monkeypatch)
    backends = world["backends"]
    output = tmp_path / "private" / "receipt.json"
    backends.fixture_binds_identities = False

    with pytest.raises(world["module"].QualificationError) as error:
        _run_live(world, output)

    assert error.value.code == "case-fixture"
    assert "lab_control:on" not in backends.calls
    assert backends.trigger_calls == 0
    receipt = json.loads(output.read_text(encoding="utf-8"))
    assert receipt["ok"] is False
    assert receipt["public_summary"]["qualified"] is False
    assert receipt["retention"]["registry_touched"] is False


def test_d12_cases_cannot_pass_with_a_manifest_identity_the_writer_did_not_return(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The D12 cases fail when the manifest identity is not the writer's own identity.

    This is the regression the rejected lane needed: the writer's returned identity is the
    only identity that can satisfy the case oracles, so a lane that keeps an identity of its
    own runs the whole route and still cannot produce a qualified verdict.
    """

    world = _build_world(tmp_path, monkeypatch)
    backends = world["backends"]
    output = tmp_path / "private" / "receipt.json"
    backends.identity_shift = True

    record = _run_live(world, output)

    bound = {item["key"]: item["task_id"] for item in record["scope"]["task_identities"]}
    assert bound != backends.writer_identities
    assert record["ok"] is False
    failed = [case["id"] for case in record["cases"] if case["status"] == "fail"]
    assert failed, record["cases"]
    assert all(
        case["detail"]
        in {
            "the narrative omitted the representative source evidence of the case",
            "the completion is not grounded in canonical observed evidence",
        }
        for case in record["cases"]
        if case["status"] == "fail"
    )
    assert record["public_summary"]["qualified"] is False
    assert record["public_summary"]["case_failures"] == failed
    assert "lab_control:on" in backends.calls


def test_live_preflight_refuses_the_read_only_phase_before_anything_is_created(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A read-only refusal never creates the laboratory or reaches the in-lab gate.

    The read-only phase owns the layout, the decision-only configuration, the borrowed
    access and the provisioned route; the writer surface and the loaded artifacts belong to
    the in-laboratory gate, which runs only inside the created root (D13 bootstrap 1 before
    2/5).  A refused read-only phase therefore stops the lane with a bounded code and no
    laboratory at all — asserted through the real helpers, with the injected backends only
    standing in for the external boundaries.
    """

    module = _qualification_module()
    lab_module = _lab_module()

    # The real helper with a real (refused) layout and no runtime: nothing is created and no
    # access is borrowed for it.
    inside = lab_module.build_plan(ROOT, "20260910T130000Z", token="abcdef012345")
    refused = module._lab_preflight(
        inside,
        interpreter=tmp_path / "no-such-runtime-interpreter",
        profile_home=tmp_path / "no-such-profile",
        environ={},
    )
    assert refused["problems"] == ["lab-root-inside-repository"]
    assert not inside.root.exists()
    assert "writers" not in refused and "artifacts" not in refused

    # And through the injected lane: the same refusal aborts before create and before the
    # in-laboratory gate, so the gate can never run on a laboratory that does not exist.
    world = _build_world(tmp_path, monkeypatch)
    backends = world["backends"]
    output = tmp_path / "private" / "receipt.json"
    backends.preflight_problems = ["lab-root-inside-repository"]

    with pytest.raises(world["module"].QualificationError) as error:
        _run_live(world, output)

    assert error.value.code == "lab-preflight"
    assert "lab_create" not in backends.calls
    assert "lab_context_preflight" not in backends.calls
    assert "lab_control:on" not in backends.calls and backends.trigger_calls == 0
    receipt = json.loads(output.read_text(encoding="utf-8"))
    assert receipt["ok"] is False
    assert receipt["retention"]["laboratory"] == {
        "created": False,
        "retained": False,
        "removed": False,
    }


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
    assert receipt["retention"]["laboratory"]["retained"] is True
    assert receipt["retention"]["registry_touched"] is False
    assert "lab_scheduler_start" not in backends.calls


def test_live_scope_setup_failure_retains_the_laboratory_evidence(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A failed shipped-writer fixture refuses, and the laboratory root stays for audit."""

    world = _build_world(tmp_path, monkeypatch, expose_evidence=False)
    backends = world["backends"]
    output = tmp_path / "private" / "receipt.json"
    backends.fixture_failure = "lab-fixture"

    with pytest.raises(world["module"].QualificationError) as error:
        _run_live(world, output)

    assert error.value.code == "lab-fixture"
    assert "lab_control:on" not in backends.calls
    receipt = json.loads(output.read_text(encoding="utf-8"))
    assert receipt["ok"] is False
    assert receipt["retention"]["laboratory"]["retained"] is True
    assert receipt["retention"]["registry_touched"] is False


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
    assert receipt["retention"]["scheduler_stopped"] is True
    assert "control:off" not in backends.calls

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

    # The fail-closed backstop: _smoke_phase refuses if the first cut has inadequate lead.
    with pytest.raises(world["module"].QualificationError) as error:
        world["module"]._smoke_phase(
            world["backends"],
            world["store"],
            world["backends"].runtime_python(),
            job_id="test-job",
            output_dir=None,
            language="English",
            baseline_report_ids=frozenset(),
            cut_one=world["backends"].now() + timedelta(seconds=2),
            expected_items={},
            expected_item_gaps={},
            stream=None,
        )
    assert error.value.code == "smoke-window"
    assert "lead_seconds" in error.value.detail


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
    assert constructed == ["backends"]
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


# ---------------------------------------------------------------------------
# Registry isolation and restore against a real disposable state root (round 11)
# ---------------------------------------------------------------------------

REGISTRY_PROJECT_A = "11111111-1111-4111-8111-111111111111"
REGISTRY_PROJECT_B = "22222222-2222-4222-8222-222222222222"
REGISTRY_PROJECT_C = "33333333-3333-4333-8333-333333333333"


# ---------------------------------------------------------------------------
# Live-shaped registry cycles and ownership fences (round 11, extended round 13)
# ---------------------------------------------------------------------------

SYNTHETIC_PROJECT_ONE = "44444444-4444-4444-8444-444444444444"
SYNTHETIC_PROJECT_TWO = "55555555-5555-4555-8555-555555555555"


def test_offline_workspace_is_unguessable_exclusive_private_and_removed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The deterministic lane's workspace is its own ``0700`` directory, removed on the way out."""

    module = _qualification_module()
    scratch = tmp_path / "scratch"
    scratch.mkdir()
    monkeypatch.setenv("TMPDIR", str(scratch))

    workspace = module._create_offline_workspace()

    info = os.lstat(workspace.path)
    assert stat.S_ISDIR(info.st_mode)
    assert stat.S_IMODE(info.st_mode) == 0o700
    assert info.st_uid == os.geteuid()
    assert (info.st_dev, info.st_ino) == workspace.identity
    token = workspace.path.name[len(module.OFFLINE_WORKSPACE_PREFIX) :]
    # Unguessable and run-owned: not the process id, and nothing a concurrent writer predicts.
    assert len(token) == 32 and all(character in "0123456789abcdef" for character in token)
    assert token != str(os.getpid())
    assert sorted(path.name for path in scratch.iterdir()) == [workspace.path.name]

    assert module._discard_offline_workspace(workspace) is True
    assert not workspace.path.exists()
    assert list(scratch.iterdir()) == []


def test_offline_workspace_collision_is_refused_and_never_removed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """An entry already present at a chosen name is refused, never adopted or deleted."""

    module = _qualification_module()
    scratch = tmp_path / "scratch"
    scratch.mkdir()
    monkeypatch.setenv("TMPDIR", str(scratch))
    monkeypatch.setenv("XDG_STATE_HOME", str(tmp_path / "xdg-state"))
    collision = scratch / f"{module.OFFLINE_WORKSPACE_PREFIX}an-unrelated-operator-directory"
    collision.mkdir()
    sentinel = collision / "unrelated-operator-sentinel.txt"
    sentinel.write_text("an unrelated operator directory that must survive\n", encoding="utf-8")
    monkeypatch.setattr(module, "_offline_workspace_name", lambda: collision.name)

    captured = io.StringIO()
    with contextlib.redirect_stdout(captured):
        code = module.main(["--json"])
    payload = json.loads(captured.getvalue())

    assert code == 1
    assert payload["ok"] is False
    assert payload["error"]["code"] == "workspace-unavailable"
    # The unrelated directory and its contents survive exactly as they were found.
    assert collision.is_dir()
    assert sentinel.read_text(encoding="utf-8") == (
        "an unrelated operator directory that must survive\n"
    )
    assert sorted(path.name for path in scratch.iterdir()) == [collision.name]


def test_offline_workspace_collision_is_skipped_for_a_fresh_run_owned_name(tmp_path: Path) -> None:
    """A colliding name is never reused: the lane runs elsewhere and leaves that directory alone.

    Runs as a real child process at the entry point, because the defect the round-14 review
    reproduced was a whole-run one: the lane adopted the predictable name, filled it, and
    deleted it — with the unrelated operator directory inside — while reporting success.
    """

    module = _qualification_module()
    scratch = tmp_path / "scratch"
    scratch.mkdir()
    collision = scratch / f"{module.OFFLINE_WORKSPACE_PREFIX}an-unrelated-operator-directory"
    collision.mkdir()
    sentinel = collision / "unrelated-operator-sentinel.txt"
    sentinel.write_text("an unrelated operator directory that must survive\n", encoding="utf-8")
    fresh = f"{module.OFFLINE_WORKSPACE_PREFIX}{'f' * 32}"
    script = textwrap.dedent(
        f"""
        import contextlib, importlib.util, io, json, os
        from pathlib import Path

        spec = importlib.util.spec_from_file_location(
            "qualify_telegram_monitor", {str(QUALIFICATION)!r}
        )
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        names = iter([{collision.name!r}, {fresh!r}])
        module._offline_workspace_name = lambda: next(names)
        captured = io.StringIO()
        with contextlib.redirect_stdout(captured):
            code = module.main(["--json"])
        payload = json.loads(captured.getvalue())
        print(json.dumps({{"code": code, "ok": payload.get("ok"),
                          "names": sorted(p.name for p in Path({str(scratch)!r}).iterdir())}}))
        """
    )
    completed = subprocess.run(
        [sys.executable, "-c", script],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
        env=_qualification_environment(tmp_path, poison_native=False) | {"TMPDIR": str(scratch)},
        timeout=300,
    )

    assert completed.returncode == 0, completed.stderr
    observed = json.loads(completed.stdout.strip().splitlines()[-1])
    assert observed["code"] == 0
    assert observed["ok"] is True
    # The colliding directory is never adopted, filled or deleted; the run used its own name and
    # removed exactly that one again (so only the unrelated directory is left).
    assert collision.is_dir()
    assert sentinel.read_text(encoding="utf-8") == (
        "an unrelated operator directory that must survive\n"
    )
    assert observed["names"] == [collision.name]


def test_offline_workspace_removal_is_bound_to_the_directory_this_run_created(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A path that no longer names this run's own directory is never deleted by name."""

    module = _qualification_module()
    scratch = tmp_path / "scratch"
    scratch.mkdir()
    monkeypatch.setenv("TMPDIR", str(scratch))
    workspace = module._create_offline_workspace()

    # The run's own directory is moved away and an unrelated one takes its place at the name.
    workspace.path.rename(scratch / "diverted-run-owned-workspace")
    replacement = scratch / workspace.path.name
    replacement.mkdir()
    sentinel = replacement / "unrelated-operator-sentinel.txt"
    sentinel.write_text("a replacement that must survive\n", encoding="utf-8")

    assert module._discard_offline_workspace(workspace) is False
    assert replacement.is_dir()
    assert sentinel.read_text(encoding="utf-8") == "a replacement that must survive\n"
    assert (scratch / "diverted-run-owned-workspace").is_dir()


def test_offline_workspace_residue_gates_the_verdict(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A workspace the lane cannot remove is reported as residue, never as a finished lane."""

    module = _qualification_module()
    scratch = tmp_path / "scratch"
    scratch.mkdir()
    monkeypatch.setenv("TMPDIR", str(scratch))
    monkeypatch.setenv("XDG_STATE_HOME", str(tmp_path / "xdg-state"))
    monkeypatch.setattr(module, "_remove_owned_directory_contents", lambda descriptor: False)

    captured = io.StringIO()
    with contextlib.redirect_stdout(captured):
        code = module.main(["--json"])
    payload = json.loads(captured.getvalue())

    assert code == 1
    assert payload["ok"] is False
    assert payload["error"]["code"] == "workspace-residue"
    retained = list(scratch.iterdir())
    assert retained and all(
        path.name.startswith(module.OFFLINE_WORKSPACE_PREFIX) for path in retained
    )


# ---------------------------------------------------------------------------
# D13 isolated native-runtime laboratory
# ---------------------------------------------------------------------------


def _intercept_operator_registry(monkeypatch: pytest.MonkeyPatch, watch: Path) -> list[str]:
    """Record every rename/replace/unlink whose source or destination names ``watch``.

    The detector is deliberately blunt: any filesystem operation the harness performs
    whose path mentions the operator registry directory is recorded, so a lane that
    touched it could not pass unnoticed.  ``test_..._detector_has_a_positive_control``
    proves the detector is not vacuous.
    """

    hits: list[str] = []
    real = {
        "rename": os.rename,
        "replace": os.replace,
        "unlink": os.unlink,
        "remove": os.remove,
        "rmdir": os.rmdir,
    }

    def note(operation: str, *candidates: Any) -> None:
        for candidate in candidates:
            if isinstance(candidate, (str, os.PathLike)):
                text = os.fspath(candidate)
                if str(watch) in text:
                    hits.append(f"{operation}:{text}")

    def wrapper(operation: str) -> Any:
        original = real[operation]

        def inner(*args: Any, **kwargs: Any) -> Any:
            note(operation, *args)
            return original(*args, **kwargs)

        return inner

    def rmtree(path: Any, *args: Any, **kwargs: Any) -> Any:
        note("rmtree", path)
        return shutil.rmtree(path, *args, **kwargs)

    for operation in ("rename", "replace", "unlink", "remove", "rmdir"):
        monkeypatch.setattr(os, operation, wrapper(operation))
    monkeypatch.setattr(shutil, "rmtree", rmtree)
    return hits


def test_operator_registry_detector_has_a_positive_control(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The containment detector actually fires: a deliberate rename is recorded."""

    registry_directory = tmp_path / "operator-state" / "projects"
    registry_directory.mkdir(parents=True)
    registry = registry_directory / "registry.json"
    registry.write_text('{"projects": {}}', encoding="utf-8")
    hits = _intercept_operator_registry(monkeypatch, registry_directory)

    os.rename(registry, registry.with_name("registry.json.held"))

    assert hits, "the operator-registry detector is vacuous"


def test_no_laboratory_code_path_touches_the_operator_project_registry(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The swap lane is gone, and a whole laboratory run never names the registry.

    The retired mechanism had one job: to hide this installation's registry behind a
    synthetic one.  It is removed rather than skipped, and the guarantees it carried —
    the operator's registered projects stay exactly as they were, nothing is hidden while
    unrelated work runs, and no entry is renamed, unlinked or replaced — are carried by
    containment instead: every mutable root of the laboratory lives inside its own private
    root, and the operator's registry is never addressed at all.
    """

    module = _qualification_module()
    source = Path(module.__file__).read_text(encoding="utf-8")
    for retired in (
        "_isolate_registry",
        "_restore_registry",
        "_rename_no_replace",
        "_RegistrySwapError",
        "REGISTRY_SWAP_CODES",
        "_StagingDirectory",
        "_scope_remove",
        "_remove_direct_records",
        "_move_registry_file_aside",
        "_install_registry_file",
        "scope_isolation_available",
        "owned_registry_entries",
        "registry_restore_value",
    ):
        assert not hasattr(module, retired), retired
    for retired_text in (
        "scope-isolation-unsupported",
        "registry.json.qualification-recovery.json",
        "registry.json.qualification-held",
        ".aether-qualification-staging-",
    ):
        assert retired_text not in source, retired_text
    assert "registry.json" not in Path(_lab_module().__file__).read_text(encoding="utf-8")

    registry_directory = tmp_path / "operator-state" / "projects"
    registry_directory.mkdir(parents=True)
    registry = registry_directory / "registry.json"
    registry.write_text('{"projects": {"operator": {"path": "/operator"}}}', encoding="utf-8")
    before = registry.read_bytes()
    inventory = sorted(path.name for path in registry_directory.iterdir())

    hits = _intercept_operator_registry(monkeypatch, registry_directory)
    world = _build_world(tmp_path, monkeypatch)
    record = _run_live(world, tmp_path / "private" / "receipt.json")

    assert record["ok"] is True, record["errors"]
    assert record["retention"]["registry_touched"] is False
    assert hits == [], hits
    assert registry.read_bytes() == before
    assert sorted(path.name for path in registry_directory.iterdir()) == inventory


def test_laboratory_root_is_created_exclusively_and_never_self_deleted(tmp_path: Path) -> None:
    """The private root is created once, is private, and is retained as objective evidence."""

    module = _qualification_module()
    lab_module = _lab_module()
    plan = lab_module.build_plan(tmp_path / "state", "20260910T130000Z", token="abcdef012345")
    assert lab_module.path_problems(plan, inside_repository=lambda path: False) == []

    recorded = module._lab_create(
        plan,
        {
            "config_text": "model:\n  default: candidate\n",
            "config_digest": "d" * 64,
            "_environment": {"HOME": str(plan.home)},
        },
    )

    assert plan.root.is_dir() and not plan.root.is_symlink()
    assert stat.S_IMODE(plan.root.stat().st_mode) == 0o700
    assert (plan.root / lab_module.LAB_RECORD_NAME).is_file()
    assert (plan.profile_home / lab_module.LAB_CONFIG_NAME).is_file()
    for path in (plan.root / lab_module.LAB_RECORD_NAME, plan.profile_home / "config.yaml"):
        assert stat.S_IMODE(path.stat().st_mode) == 0o600

    release = module._lab_release(plan)

    assert release["retained"] is True
    assert release["removed"] is False
    assert release["problems"] == []
    # The laboratory is not self-deleted: it is the declared objective evidence.
    assert plan.root.is_dir()
    assert recorded["retained"] is True

    # A second plan at the same name is never adopted.
    try:
        lab_module.create_root(plan)
    except lab_module.LabError as error:
        assert error.code == "lab-root-exists"
    else:  # pragma: no cover - only reached if the exclusive creation regressed
        raise AssertionError("an existing laboratory root was adopted")


def test_laboratory_layout_is_refused_inside_any_repository(tmp_path: Path) -> None:
    """A laboratory root inside this checkout, or on an existing name, is refused."""

    module = _qualification_module()
    lab_module = _lab_module()
    inside = lab_module.build_plan(module.ROOT, "20260910T130000Z", token="abcdef012345")
    problems = lab_module.path_problems(inside, inside_repository=module._inside_repository)
    assert "lab-root-inside-repository" in problems

    existing = lab_module.build_plan(tmp_path / "state", "20260910T130000Z", token="abcdef012345")
    existing.root.mkdir(parents=True)
    assert "lab-root-exists" in lab_module.path_problems(
        existing, inside_repository=lambda path: False
    )


def test_borrowed_access_is_never_persisted_into_the_laboratory(tmp_path: Path) -> None:
    """Only already provisioned access is borrowed, in memory, and nothing is written."""

    module = _qualification_module()
    lab_module = _lab_module()
    token = "123456:AAsynthetic-borrowed-token-value"
    env_file = tmp_path / "profile.env"
    env_file.write_text(
        f"TELEGRAM_BOT_TOKEN={token}\nTELEGRAM_HOME_CHANNEL=-1001234567890\n",
        encoding="utf-8",
    )

    access = lab_module.collect_access(
        names=(
            "TELEGRAM_BOT_TOKEN",
            "TELEGRAM_HOME_CHANNEL",
            "TELEGRAM_HOME_CHANNEL_THREAD_ID",
        ),
        environ={},
        env_files=(env_file,),
    )

    # The declared destination has no thread, so the optional name is simply not carried.
    assert sorted(access) == ["TELEGRAM_BOT_TOKEN", "TELEGRAM_HOME_CHANNEL"]
    fingerprint = lab_module.access_fingerprint(access)
    assert fingerprint["names"] == ["TELEGRAM_BOT_TOKEN", "TELEGRAM_HOME_CHANNEL"]
    assert fingerprint["present"] == {
        "TELEGRAM_BOT_TOKEN": True,
        "TELEGRAM_HOME_CHANNEL": True,
    }
    assert token not in json.dumps(fingerprint)

    plan = lab_module.build_plan(tmp_path / "state", "20260910T130000Z", token="abcdef012345")
    environment = lab_module.child_environment(
        plan,
        base={
            "HOME": "/production",
            "PYTHONPATH": "",
            "AETHER_MONITOR_QUALIFICATION_SCHEDULE": "* * * * *",
        },
        access=access,
        repository_src=module.SOURCE_ROOT,
    )
    assert environment["TELEGRAM_BOT_TOKEN"] == token  # process context only
    assert "AETHER_MONITOR_QUALIFICATION_SCHEDULE" not in environment
    module._lab_create(
        plan,
        {"config_text": "model:\n  default: candidate\n", "config_digest": "e" * 64},
    )

    written = [path for path in plan.root.rglob("*") if path.is_file()]
    assert written, "the laboratory record and configuration must exist"
    for path in written:
        assert token not in path.read_text(encoding="utf-8"), path
    assert token not in json.dumps(module._sanitize_lab({"root": str(plan.root)}))

    # An unavailable required name is a fail-closed preflight gap, not a silent gap.
    try:
        lab_module.collect_access(
            names=("TELEGRAM_BOT_TOKEN", "TELEGRAM_HOME_CHANNEL"),
            environ={},
            env_files=(),
        )
    except lab_module.LabError as error:
        assert error.code == "lab-access-missing"
    else:  # pragma: no cover - only reached if the fail-closed gap regressed
        raise AssertionError("a missing provisioned credential was not refused")


_PROBE_STUB_MODULES: dict[str, str] = {
    "hermes_constants.py": (
        "import os\n"
        "from pathlib import Path\n\n\n"
        "def get_hermes_home():\n"
        "    return Path(os.environ['HERMES_HOME'])\n"
    ),
    "hermes_state.py": (
        "class SessionDB:\n"
        "    def create_session(self, session_id, source, **kwargs):\n"
        "        return session_id\n\n"
        "    def _insert_session_row(\n"
        "        self, session_id, source, model=None, model_config=None, system_prompt=None,\n"
        "        user_id=None, session_key=None, chat_id=None, chat_type=None, thread_id=None,\n"
        "        parent_session_id=None, cwd=None, profile_name=None, git_repo_root=None,\n"
        "    ):\n"
        "        return None\n\n"
        "    def set_session_title(self, session_id, title):\n"
        "        return True\n"
    ),
    "hermes_cli/__init__.py": "",
    "hermes_cli/env_loader.py": "def load_hermes_dotenv(*args, **kwargs):\n    return []\n",
    "hermes_cli/kanban_db.py": (
        "import os\n"
        "from pathlib import Path\n\n\n"
        "def kanban_home():\n"
        "    env = os.environ.get('HERMES_HOME', '')\n"
        "    p = Path(env)\n"
        "    if p.parent.name == 'profiles':\n"
        "        return p.parent.parent\n"
        "    return p\n\n\n"
        "def kanban_db_path(board=None):\n"
        "    return kanban_home() / 'kanban.db'\n\n\n"
        "def boards_root():\n"
        "    return kanban_home() / 'kanban' / 'boards'\n\n\n"
        "def create_board(slug, *, name=None, default_workdir=None, project_id=None):\n"
        "    return {'slug': slug}\n\n\n"
        "def connect(db_path=None, *, board=None):\n"
        "    return None\n\n\n"
        "def create_task(conn, *, title, body=None, assignee=None, created_by=None, workspace_kind='scratch',\n"
        "                workspace_path=None, initial_status='running', session_id=None,\n"
        "                session_affinity=None, board=None, project_id=None):\n"
        "    return 't_stub'\n\n\n"
        "def claim_task(conn, task_id, *, ttl_seconds=None, claimer=None):\n"
        "    return object()\n\n\n"
        "def link_tasks(conn, parent_id, child_id):\n"
        "    return None\n\n\n"
        "def complete_task(conn, task_id, *, result=None, summary=None):\n"
        "    return True\n\n\n"
        "def request_review(conn, task_id, *, summary=None, with_reason=False):\n"
        "    return (True, None)\n"
    ),
    "hermes_cli/projects_db.py": (
        "import os\n"
        "from pathlib import Path\n\n\n"
        "def projects_db_path():\n"
        "    return Path(os.environ['HERMES_HOME']) / 'projects.db'\n\n\n"
        "def connect(db_path=None):\n"
        "    return None\n\n\n"
        "def create_project(conn, *, name, primary_path=None, board_slug=None):\n"
        "    return 'p_stub'\n"
    ),
    "cron/__init__.py": "",
    "cron/scheduler_provider.py": (
        "class InProcessCronScheduler:\n"
        "    @property\n"
        "    def name(self):\n"
        "        return 'builtin'\n\n"
        "    def start(self, stop_event, interval=60):\n"
        "        return None\n"
    ),
    "cron/jobs.py": (
        "def list_jobs():\n    return []\n\n"
        "def get_job(job_id):\n    return None\n\n"
        "def update_job(job_id, updates):\n    return None\n\n"
        "def compute_next_run(schedule, last_run_at=None):\n    return None\n\n"
        "def get_due_jobs():\n    return []\n"
    ),
    "gateway/__init__.py": "",
    "gateway/config.py": (
        "class Platform:\n"
        "    TELEGRAM = 'telegram'\n\n\n"
        "class _HomeChannel:\n"
        "    chat_id = 'stub-chat'\n"
        "    thread_id = None\n\n\n"
        "class _Config:\n"
        "    def get_home_channel(self, platform):\n"
        "        return _HomeChannel()\n\n\n"
        "def load_gateway_config():\n"
        "    return _Config()\n"
    ),
    "hermes_cli/plugins.py": (
        "class _StubPlugin:\n"
        "    enabled = True\n"
        "    tools_registered = ['aether_monitor', 'aether_monitor_report_snapshot']\n"
        "    hooks_registered = ['on_session_end', 'post_llm_call', 'post_tool_call']\n"
        "    error = None\n\n"
        "class PluginManager:\n"
        "    def __init__(self):\n"
        "        self._plugins = {'aether-telegram-monitor': _StubPlugin()}\n\n"
        "    def discover_and_load(self, force=False):\n"
        "        pass\n"
    ),
}


def _write_probe_native_tree(root: Path, *, drop: str | None = None) -> Path:
    """Materialize a minimal native tree the laboratory probe can resolve and digest."""

    for relative, text in _PROBE_STUB_MODULES.items():
        if drop is not None:
            # ``drop`` names a callable the stub tree must not expose, so the probe resolves
            # the rest of the surface and the gate reports exactly the missing one.
            text = text.replace(drop, "removed_by_test")
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
    return root


def _run_probe_body(
    tmp_path: Path,
    native_root: Path,
    *,
    lab_root: Path | None,
) -> tuple[dict[str, Any], Path]:
    """Run one generated probe-body variant in a real child process, offline.

    The body is the harness's own generated body — never a hand-written copy — so the
    variant the lane actually runs is the variant exercised here.
    """

    module = _qualification_module()
    if lab_root is not None:
        (lab_root / "hermes").mkdir(parents=True, exist_ok=True)
        (lab_root / "home").mkdir(parents=True, exist_ok=True)
        home = lab_root / "home"
        hermes_home = lab_root / "hermes"
    else:
        home = tmp_path / "provisioned-home"
        hermes_home = tmp_path / "provisioned-hermes"
        home.mkdir(parents=True, exist_ok=True)
        hermes_home.mkdir(parents=True, exist_ok=True)
    environment = {
        "PATH": os.environ.get("PATH", ""),
        "HOME": str(home),
        "HERMES_HOME": str(hermes_home),
        "PYTHONDONTWRITEBYTECODE": "1",
        "PYTHONPATH": os.pathsep.join((str(native_root), str(module.SOURCE_ROOT))),
    }
    completed = subprocess.run(
        [sys.executable, "-c", module._native_probe_body(lab_root=lab_root)],
        check=False,
        capture_output=True,
        text=True,
        cwd=str(native_root),
        env=environment,
        timeout=120,
    )
    assert completed.returncode == 0, completed.stderr[-800:]
    return json.loads(completed.stdout.strip().splitlines()[-1]), lab_root or hermes_home


def _run_native_probe(tmp_path: Path, native_root: Path) -> tuple[dict[str, Any], Path]:
    """Run the harness's own laboratory probe body in a real child process, offline."""

    return _run_probe_body(tmp_path, native_root, lab_root=tmp_path / "lab")


def test_native_probe_resolves_the_writer_surface_and_the_loaded_artifacts(
    tmp_path: Path,
) -> None:
    """The probe runs as a real child and records the loaded writer surface and artifacts.

    This is the regression for the rejected lane: the fixture used writer calls the
    provisioned revision does not accept, the preflight could not see the writer surface at
    all, and the probe payload was not even serializable because ``InProcessCronScheduler``
    exposes ``name`` as an instance property.  All three are checked here against a minimal
    native tree, with no native Hermes install and no external effect.
    """

    module = _qualification_module()
    lab_module = _lab_module()
    native_root = _write_probe_native_tree(tmp_path / "native")

    payload, lab_root = _run_native_probe(tmp_path, native_root)

    assert lab_module.writer_problems(payload, lab_root=lab_root) == []
    assert payload["interfaces"]["scheduler"]["name"] is None
    assert payload["interfaces"]["scheduler"]["name_is_instance_property"] is True
    assert str(module.SOURCE_ROOT) in str(
        payload["artifacts"]["aether_agents.monitor.runtime"]["file"]
    )
    # Every digest is the digest of the module file that was actually loaded: the native
    # stubs resolve from the stub tree, the product modules from this repository's source.
    assert set(payload["artifacts"]) == set(lab_module.WRITER_ARTIFACT_MODULES)
    for module_name, entry in payload["artifacts"].items():
        loaded = Path(entry["file"])
        assert hashlib.sha256(loaded.read_bytes()).hexdigest() == entry["sha256"], module_name
        if module_name.startswith(("hermes_", "cron.", "gateway.")):
            assert loaded.parent == native_root / Path(*module_name.split(".")).parent
    for name in (
        "hermes_home",
        "kanban_home",
        "kanban_db",
        "boards_root",
        "projects_db",
    ):
        assert str(lab_root) in str(payload["effective"][name]), name

    summary = lab_module.writer_summary(payload)
    assert sorted(summary["required_interfaces"]) == sorted(
        name for name, _ in lab_module.WRITER_REQUIREMENTS
    )
    assert sorted(summary["artifact_digests"]) == sorted(lab_module.WRITER_ARTIFACT_MODULES)
    # The public projection carries names and digests only, never a module path.
    rendered = json.dumps(summary)
    assert str(native_root) not in rendered
    assert str(lab_root) not in rendered


def test_native_probe_refuses_a_runtime_without_the_required_writer_surface(
    tmp_path: Path,
) -> None:
    """A revision missing a writer the fixture uses refuses with a bounded capability code."""

    lab_module = _lab_module()
    native_root = _write_probe_native_tree(tmp_path / "native", drop="request_review")

    payload, lab_root = _run_native_probe(tmp_path, native_root)

    problems = lab_module.writer_problems(payload, lab_root=lab_root)
    assert "writer-interface-missing:hermes_cli.kanban_db.request_review" in problems
    assert payload["writers"]["hermes_cli.kanban_db.request_review"]["present"] is False


def test_native_probe_refuses_a_writer_that_resolves_outside_the_laboratory(
    tmp_path: Path,
) -> None:
    """An inherited board selector that escapes the laboratory is refused, not trusted."""

    lab_module = _lab_module()
    native_root = _write_probe_native_tree(tmp_path / "native")

    payload, lab_root = _run_native_probe(tmp_path, native_root)

    escaped = json.loads(json.dumps(payload))
    escaped["effective"]["kanban_db"] = str(tmp_path / "operator" / "kanban.db")
    assert "writer-root-escape:kanban_db" in lab_module.writer_problems(escaped, lab_root=lab_root)


def test_both_generated_probe_variants_run_as_real_child_processes(tmp_path: Path) -> None:
    """Both generated probe bodies are valid, runnable Python.

    The rejected candidate generated the provisioned variant as ``LAB_ROOT_JSON = null``,
    so every real ``_lab_preflight`` died with ``NameError: name 'null' is not defined``
    before it could resolve anything.  Both variants the harness actually generates are
    executed here as real child processes and must exit 0 with a parsed payload.
    """

    module = _qualification_module()
    lab_module = _lab_module()
    native_root = _write_probe_native_tree(tmp_path / "native")

    provisioned_body = module._native_probe_body(lab_root=None)
    assert "LAB_ROOT_JSON = None" in provisioned_body
    assert "null" not in provisioned_body
    provisioned, _ = _run_probe_body(tmp_path, native_root, lab_root=None)
    assert provisioned["problems"] == []
    assert provisioned["destination_digest"]
    assert provisioned["interfaces"]["scheduler"]["name_is_instance_property"] is True
    # The provisioned variant resolves the route and the native interfaces only: the writer
    # surface exists only inside a laboratory child context.
    assert "writers" not in provisioned and "artifacts" not in provisioned

    lab_root = tmp_path / "lab-root"
    isolated_body = module._native_probe_body(lab_root=lab_root)
    assert f"LAB_ROOT_JSON = {json.dumps(str(lab_root))}" in isolated_body
    isolated, resolved_root = _run_probe_body(tmp_path, native_root, lab_root=lab_root)
    assert lab_module.writer_problems(isolated, lab_root=resolved_root) == []
    assert sorted(isolated["writers"]) == sorted(name for name, _ in lab_module.WRITER_REQUIREMENTS)
    assert sorted(isolated["artifacts"]) == sorted(lab_module.WRITER_ARTIFACT_MODULES)


def test_read_only_preflight_refuses_the_layout_without_creating_or_borrowing(
    tmp_path: Path,
) -> None:
    """A refused layout stops in the read-only phase: no root, no runtime, no access read.

    The interpreter below does not exist and no access value is supplied, so the refusal can
    only come from the layout check — and nothing may be created or borrowed for it.
    """

    module = _qualification_module()
    lab_module = _lab_module()
    inside = lab_module.build_plan(ROOT, "20260910T130000Z", token="abcdef012345")

    preflight = module._lab_preflight(
        inside,
        interpreter=tmp_path / "no-such-runtime-interpreter",
        profile_home=tmp_path / "no-such-profile",
        environ={},
    )

    assert preflight["problems"] == ["lab-root-inside-repository"]
    assert not inside.root.exists()
    assert preflight["access"] == {} and preflight["_access"] == {}
    assert preflight["config_text"] is None and preflight["_environment"] == {}

    # The in-laboratory gate is not reachable without the verified child context: it refuses
    # with its own bounded code instead of probing in this process's context.
    with pytest.raises(module.QualificationError) as error:
        module._lab_context_preflight(
            inside, {"_environment": {}, "destination_digest": "d" * 64}, interpreter=sys.executable
        )
    assert error.value.code == "lab-context-preflight"


#: A functional minimal native tree: it is not the shipping writer implementation, but it
#: answers the same calls the laboratory makes — a board/task store whose writer owns task
#: identity and refuses unknown ids, a project store, a session store and a gateway home
#: channel — so the harness's own chain can be executed end to end with no native install.
_CHAIN_STUB_MODULES: dict[str, str] = {
    "hermes_constants.py": (
        "import os\n"
        "from pathlib import Path\n\n\n"
        "def get_hermes_home():\n"
        "    return Path(os.environ['HERMES_HOME'])\n"
    ),
    "hermes_state.py": (
        "import json\n"
        "from pathlib import Path\n\n\n"
        "class SessionDB:\n"
        "    def __init__(self, db_path=None):\n"
        "        self.path = Path(db_path) if db_path else Path('sessions.json')\n\n"
        "    def _rows(self):\n"
        "        try:\n"
        "            return json.loads(self.path.read_text(encoding='utf-8'))\n"
        "        except FileNotFoundError:\n"
        "            return {}\n\n"
        "    def _write(self, rows):\n"
        "        self.path.parent.mkdir(parents=True, exist_ok=True)\n"
        "        self.path.write_text(json.dumps(rows, sort_keys=True), encoding='utf-8')\n\n"
        "    def create_session(self, session_id, source, **kwargs):\n"
        "        rows = self._rows()\n"
        "        rows[session_id] = {'source': source}\n"
        "        self._write(rows)\n"
        "        return session_id\n\n"
        "    def _insert_session_row(self, session_id, source, model=None, model_config=None,\n"
        "                            system_prompt=None, user_id=None, session_key=None,\n"
        "                            chat_id=None, chat_type=None, thread_id=None,\n"
        "                            parent_session_id=None, cwd=None, profile_name=None,\n"
        "                            git_repo_root=None, origin_json=None, display_name=None):\n"
        "        return None\n\n"
        "    def set_session_title(self, session_id, title):\n"
        "        rows = self._rows()\n"
        "        if session_id not in rows:\n"
        "            return False\n"
        "        rows[session_id]['title'] = title\n"
        "        self._write(rows)\n"
        "        return True\n"
    ),
    "hermes_cli/__init__.py": "",
    "hermes_cli/env_loader.py": (
        "import os\n"
        "from pathlib import Path\n\n\n"
        "def load_hermes_dotenv(*args, **kwargs):\n"
        "    env_path = Path(os.environ.get('HERMES_HOME', '')) / '.env'\n"
        "    if env_path.is_file():\n"
        "        for line in env_path.read_text(encoding='utf-8').splitlines():\n"
        "            if '=' in line and not line.startswith('#'):\n"
        "                k, v = line.split('=', 1)\n"
        "                os.environ[k.strip()] = v.strip()\n"
        "    return []\n"
    ),
    "hermes_cli/kanban_db.py": (
        "import os\n"
        "import sqlite3\n"
        "import uuid\n"
        "from pathlib import Path\n\n"
        "SCHEMA = (\n"
        "    'CREATE TABLE IF NOT EXISTS tasks (id TEXT PRIMARY KEY, title TEXT, status TEXT,'\n"
        "    ' result TEXT, summary TEXT, session_id TEXT);'\n"
        "    'CREATE TABLE IF NOT EXISTS links (parent_id TEXT, child_id TEXT);'\n"
        ")\n\n\n"
        "def kanban_home():\n"
        "    env = os.environ.get('HERMES_HOME', '')\n"
        "    p = Path(env)\n"
        "    if p.parent.name == 'profiles':\n"
        "        return p.parent.parent\n"
        "    return p\n\n\n"
        "def boards_root():\n"
        "    return kanban_home() / 'kanban' / 'boards'\n\n\n"
        "def kanban_db_path(board=None):\n"
        "    if board:\n"
        "        return boards_root() / board / 'kanban.db'\n"
        "    return kanban_home() / 'kanban.db'\n\n\n"
        "def board_dir(board=None):\n"
        "    return boards_root() / (board or 'default')\n\n\n"
        "def init_db(db_path=None, *, board=None):\n"
        "    return _connect(Path(db_path) if db_path else kanban_db_path(board))\n\n\n"
        "def read_board_metadata(board):\n"
        "    import json\n"
        "    path = board_dir(board) / 'board.json'\n"
        "    if path.is_file():\n"
        "        return json.loads(path.read_text())\n"
        "    return None\n\n\n"
        "def _connect(path):\n"
        "    path.parent.mkdir(parents=True, exist_ok=True)\n"
        "    connection = sqlite3.connect(path)\n"
        "    connection.executescript(SCHEMA)\n"
        "    return connection\n\n\n"
        "def create_board(slug, *, name=None, description=None, icon=None, color=None,\n"
        "                 default_workdir=None, project_id=None):\n"
        "    _connect(kanban_db_path(slug)).close()\n"
        "    return {'slug': slug, 'name': name, 'project_id': project_id}\n\n\n"
        "def connect(db_path=None, *, board=None):\n"
        "    return _connect(Path(db_path) if db_path else kanban_db_path(board))\n\n\n"
        "def create_task(conn, *, title, body=None, assignee=None, created_by=None,\n"
        "                workspace_kind='scratch', workspace_path=None, branch_name=None,\n"
        "                tenant=None, priority=0, parents=(), triage=False,\n"
        "                idempotency_key=None, max_runtime_seconds=None, skills=None,\n"
        "                max_retries=None, model_override=None, provider_override=None,\n"
        "                reasoning_effort=None, goal_mode=False, goal_max_turns=None,\n"
        "                initial_status='running', session_id=None, board=None,\n"
        "                project_id=None, project_source_task_id=None, session_affinity=None):\n"
        "    task_id = 't_' + uuid.uuid4().hex[:8]\n"
        "    conn.execute(\n"
        "        'INSERT INTO tasks (id, title, status, session_id) VALUES (?, ?, ?, ?)',\n"
        "        (task_id, title, initial_status, session_id),\n"
        "    )\n"
        "    conn.commit()\n"
        "    return task_id\n\n\n"
        "def claim_task(conn, task_id, *, ttl_seconds=None, claimer=None):\n"
        "    cursor = conn.execute(\n"
        "        \"UPDATE tasks SET status = 'running' WHERE id = ?\", (task_id,)\n"
        "    )\n"
        "    conn.commit()\n"
        "    return object() if cursor.rowcount == 1 else None\n\n\n"
        "def link_tasks(conn, parent_id, child_id):\n"
        "    conn.execute(\n"
        "        'INSERT INTO links (parent_id, child_id) VALUES (?, ?)', (parent_id, child_id)\n"
        "    )\n"
        "    conn.commit()\n\n\n"
        "def complete_task(conn, task_id, *, result=None, summary=None, metadata=None,\n"
        "                  created_cards=None, expected_run_id=None, fire_lifecycle_hook=True):\n"
        "    cursor = conn.execute(\n"
        "        \"UPDATE tasks SET status = 'done', result = ?, summary = ? WHERE id = ?\",\n"
        "        (result, summary, task_id),\n"
        "    )\n"
        "    conn.commit()\n"
        "    return cursor.rowcount == 1\n\n\n"
        "def request_review(conn, task_id, *, summary=None, metadata=None, reviewer=None,\n"
        "                   expected_run_id=None, force=False, with_reason=False):\n"
        "    cursor = conn.execute(\n"
        "        \"UPDATE tasks SET status = 'review', summary = ? WHERE id = ? AND status != 'done'\",\n"
        "        (summary, task_id),\n"
        "    )\n"
        "    conn.commit()\n"
        "    return (cursor.rowcount == 1, None)\n"
    ),
    "hermes_cli/projects_db.py": (
        "import os\n"
        "import sqlite3\n"
        "import uuid\n"
        "from pathlib import Path\n\n"
        "SCHEMA = (\n"
        "    'CREATE TABLE IF NOT EXISTS projects (id TEXT PRIMARY KEY, name TEXT, slug TEXT,'\n"
        "    ' primary_path TEXT);'\n"
        ")\n\n\n"
        "def projects_db_path():\n"
        "    return Path(os.environ['HERMES_HOME']) / 'projects.db'\n\n\n"
        "def connect(db_path=None):\n"
        "    path = Path(db_path) if db_path else projects_db_path()\n"
        "    path.parent.mkdir(parents=True, exist_ok=True)\n"
        "    connection = sqlite3.connect(path)\n"
        "    connection.executescript(SCHEMA)\n"
        "    return connection\n\n\n"
        "from contextlib import contextmanager\n\n\n"
        "@contextmanager\n"
        "def connect_closing(db_path=None):\n"
        "    conn = connect(db_path)\n"
        "    try:\n"
        "        yield conn\n"
        "    finally:\n"
        "        conn.close()\n\n\n"
        "def list_projects(conn, include_archived=False):\n"
        "    cursor = conn.execute('SELECT id, name, slug, primary_path FROM projects')\n"
        "    from collections import namedtuple\n"
        "    P = namedtuple('Project', ['id', 'name', 'slug', 'primary_path'])\n"
        "    return [P(*row) for row in cursor.fetchall()]\n\n\n"
        "def create_project(conn, *, name, slug=None, folders=None, primary_path=None,\n"
        "                   description=None, icon=None, color=None, board_slug=None,\n"
        "                   allow_duplicate_path=False):\n"
        "    project_id = 'p_' + uuid.uuid4().hex[:8]\n"
        "    conn.execute(\n"
        "        'INSERT INTO projects (id, name, slug, primary_path) VALUES (?, ?, ?, ?)',\n"
        "        (project_id, name, slug or project_id, primary_path),\n"
        "    )\n"
        "    conn.commit()\n"
        "    return project_id\n"
    ),
    "cron/__init__.py": "",
    "cron/scheduler_provider.py": (
        "class InProcessCronScheduler:\n"
        "    @property\n"
        "    def name(self):\n"
        "        return 'builtin'\n\n"
        "    def start(self, stop_event, interval=60):\n"
        "        return None\n"
    ),
    "cron/jobs.py": (
        "def list_jobs():\n    return []\n\n"
        "def get_job(job_id):\n    return None\n\n"
        "def update_job(job_id, updates):\n    return None\n\n"
        "def compute_next_run(schedule, last_run_at=None):\n    return None\n\n"
        "def get_due_jobs():\n    return []\n"
    ),
    "gateway/__init__.py": "",
    "gateway/config.py": (
        "import json\n"
        "import os\n"
        "from pathlib import Path\n\n\n"
        "class Platform:\n"
        "    TELEGRAM = 'telegram'\n\n\n"
        "class HomeChannel:\n"
        "    def __init__(self, chat_id, thread_id=None, name='Home'):\n"
        "        self.chat_id = chat_id\n"
        "        self.thread_id = thread_id\n"
        "        self.name = name\n\n\n"
        "class _Config:\n"
        "    def __init__(self, home):\n"
        "        self.home = home\n\n"
        "    def get_home_channel(self, platform):\n"
        "        return self.home\n\n\n"
        "def _provisioned_home():\n"
        "    home = os.environ.get('HERMES_HOME', '')\n"
        "    if not home:\n"
        "        return None\n"
        "    try:\n"
        "        return json.loads(\n"
        "            (Path(home) / 'gateway-home.json').read_text(encoding='utf-8')\n"
        "        )\n"
        "    except (FileNotFoundError, ValueError):\n"
        "        return None\n\n\n"
        "def load_gateway_config():\n"
        "    marker = _provisioned_home() or {}\n"
        "    chat_id = marker.get('chat_id') or os.environ.get('TELEGRAM_HOME_CHANNEL')\n"
        "    thread_id = marker.get('thread_id') or os.environ.get('TELEGRAM_HOME_CHANNEL_THREAD_ID')\n"
        "    if not chat_id:\n"
        "        return _Config(None)\n"
        "    return _Config(HomeChannel(chat_id=chat_id, thread_id=thread_id or None))\n"
    ),
    "hermes_cli/plugins.py": (
        "class _StubPlugin:\n"
        "    enabled = True\n"
        "    tools_registered = ['aether_monitor', 'aether_monitor_report_snapshot']\n"
        "    hooks_registered = ['on_session_end', 'post_llm_call', 'post_tool_call']\n"
        "    error = None\n\n"
        "class PluginManager:\n"
        "    def __init__(self):\n"
        "        self._plugins = {'aether-telegram-monitor': _StubPlugin()}\n\n"
        "    def discover_and_load(self, force=False):\n"
        "        pass\n"
    ),
}


#: The child driver: it runs the harness's own chain in the order the lane uses, stopping
#: exactly where the lane stops (a refused phase never reaches the next one) and reporting
#: the facts the test asserts.  Nothing is monkeypatched and nothing is faked.
_CHAIN_DRIVER = r"""
import importlib.util
import json
import sys
from pathlib import Path

ROOT = Path("@ROOT@")
facts = {"reached_fixture": False, "reached_transition": False}


def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


try:
    import hermes_cli.kanban_db as kanban

    lab = _load("telegram_monitor_lab", ROOT / "scripts" / "telegram_monitor_lab.py")
    q = _load("qualify_telegram_monitor", ROOT / "scripts" / "qualify_telegram_monitor.py")

    interpreter = Path(sys.executable)
    plan = lab.build_plan(Path("@HOST@"), "20260910T130000Z", token="abcdef012345")
    # Only the test-owned profile file provides the borrowed access: inherited transport
    # names are dropped so the run cannot read this installation's own credentials.
    environ = {
        name: value
        for name, value in __import__("os").environ.items()
        if not name.startswith(("TELEGRAM_", "AETHER_ROUTER_"))
    }
    preflight = q._lab_preflight(
        plan, interpreter=interpreter, profile_home=Path("@PROFILE@"), environ=environ
    )
    facts["phase1_problems"] = list(preflight["problems"])
    facts["root_after_phase1"] = plan.root.exists()
    manifest = None
    if not preflight["problems"]:
        record = q._lab_create(plan, preflight)
        facts["created"] = True
        gate = q._lab_context_preflight(plan, preflight, interpreter=interpreter)
        facts["gate_problems"] = list(gate["problems"])
        facts["gate_writers"] = sorted(gate["writers"]["present_interfaces"])
        facts["gate_artifacts"] = sorted(gate["artifacts"])
        facts["destination_matches"] = bool(
            gate["destination_digest"]
            and gate["destination_digest"] == preflight["destination_digest"]
        )
        if not gate["problems"]:
            manifest = q._scope_manifest(Path(record["scope_root"]), plan.stamp)
            q._write_scope_projects(Path(record["scope_root"]), manifest)
            seeded = q._lab_fixture(interpreter, record, manifest)
            facts["reached_fixture"] = True
            facts["seeded"] = {
                key: len(seeded[key]) for key in ("projects", "boards", "sessions", "tasks", "direct")
            }
            facts["bound"] = {
                task["key"]: task["task_id"] for entry in manifest for task in entry["tasks"]
            }
            facts["boards_by_key"] = {
                task["key"]: entry["board_slug"] for entry in manifest for task in entry["tasks"]
            }
            rows = {}
            hermes_root = Path(record["hermes_home"])
            if hermes_root.parent.name == "profiles":
                hermes_root = hermes_root.parent.parent
            boards_root = hermes_root / "kanban" / "boards"
            for entry in manifest:
                connection = kanban.connect(
                    db_path=boards_root / entry["board_slug"] / "kanban.db"
                )
                try:
                    rows[entry["board_slug"]] = sorted(
                        str(row[0]) for row in connection.execute("SELECT id FROM tasks")
                    )
                finally:
                    connection.close()
            facts["board_rows"] = rows
            transition = q._lab_transition(interpreter, record, manifest)
            facts["reached_transition"] = True
            facts["transition"] = transition
            facts["expected_transition"] = [
                facts["bound"][task["key"]] for entry in manifest for task in entry["transition"]
            ]
    print(json.dumps(facts))
except Exception as error:  # noqa: BLE001 - the driver reports its own failure
    facts["driver_error"] = f"{type(error).__name__}: {error}"
    print(json.dumps(facts))
    raise SystemExit(3)
"""


def _write_chain_native_tree(root: Path, *, drop: str | None = None) -> Path:
    """Materialize the functional minimal native tree the laboratory chain runs on."""

    for relative, text in _CHAIN_STUB_MODULES.items():
        if drop is not None:
            text = text.replace(drop, "removed_by_test")
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
    return root


def _chain_context(tmp_path: Path, native_root: Path) -> tuple[Path, dict[str, str]]:
    """A private provisioned context plus a test-owned profile with fake borrowed access."""

    home = tmp_path / "provisioned" / "home"
    hermes_home = tmp_path / "provisioned" / "hermes"
    home.mkdir(parents=True, exist_ok=True)
    hermes_home.mkdir(parents=True, exist_ok=True)
    # The provisioned context this lane compares its laboratory against.  The laboratory
    # child resolves the same destination from the borrowed environment instead.
    (hermes_home / "gateway-home.json").write_text(
        json.dumps({"chat_id": "-100000", "thread_id": None}), encoding="utf-8"
    )
    profile = hermes_home / "profiles" / "morfeo"
    profile.mkdir(parents=True, exist_ok=True)
    (profile / "config.yaml").write_text(
        "model:\n  default: candidate\n  provider: aether-router\n"
        "providers:\n  aether-router:\n    base_url: https://example.invalid\n"
        "    key_env: AETHER_ROUTER_API_KEY\n"
        "agent:\n  name: Morfeo\n",
        encoding="utf-8",
    )
    (profile / ".env").write_text(
        "TELEGRAM_BOT_TOKEN=test-borrowed-token\n"
        "TELEGRAM_HOME_CHANNEL=-100000\n"
        "AETHER_ROUTER_API_KEY=test-borrowed-key\n",
        encoding="utf-8",
    )
    environment = {
        "PATH": os.environ.get("PATH", ""),
        "HOME": str(home),
        "HERMES_HOME": str(hermes_home),
        "PYTHONDONTWRITEBYTECODE": "1",
        "PYTHONPATH": os.pathsep.join((str(native_root), str(ROOT / "src"))),
    }
    return profile, environment


def _run_chain_driver(
    tmp_path: Path, environment: Mapping[str, str], profile: Path
) -> dict[str, Any]:
    driver = tmp_path / "chain_driver.py"
    driver.write_text(
        _CHAIN_DRIVER.replace("@ROOT@", str(ROOT))
        .replace("@HOST@", str(tmp_path / "lab-host"))
        .replace("@PROFILE@", str(profile)),
        encoding="utf-8",
    )
    completed = subprocess.run(
        [sys.executable, str(driver)],
        cwd=str(tmp_path),
        check=False,
        capture_output=True,
        text=True,
        env=dict(environment),
        timeout=600,
    )
    assert completed.returncode == 0, completed.stderr[-2000:]
    return json.loads(completed.stdout.strip().splitlines()[-1])


def test_real_laboratory_chain_reaches_the_fixture_and_the_transition(tmp_path: Path) -> None:
    """The real preflight → create → in-lab gate → fixture → transition chain runs.

    This is the regression for the rejected candidate, which could not run its own chain at
    all: the generated provisioned probe body died with ``NameError: name 'null' is not
    defined``, and the isolated probe materialized the laboratory root before the exclusive
    creator, so bootstrap always refused with ``lab-root-exists``.  The harness's own
    functions run here in a real child process against a minimal native tree, with a private
    provisioned context and test-owned borrowed access — no monkeypatched probe and no fake
    backend.
    """

    lab_module = _lab_module()
    native_root = _write_chain_native_tree(tmp_path / "native")
    profile, environment = _chain_context(tmp_path, native_root)

    facts = _run_chain_driver(tmp_path, environment, profile)

    assert "driver_error" not in facts, facts
    # The read-only phase resolves the provisioned route and creates nothing.
    assert facts["phase1_problems"] == []
    assert facts["root_after_phase1"] is False
    # The private root is created exclusively and the gate runs inside it.
    assert facts["created"] is True
    assert facts["gate_problems"] == []
    assert len(facts["gate_writers"]) == len(lab_module.WRITER_REQUIREMENTS)
    assert facts["gate_artifacts"] == sorted(lab_module.WRITER_ARTIFACT_MODULES)
    assert facts["destination_matches"] is True
    # The chain really reaches the shipped-writer fixture and the between-cut transition.
    assert facts["reached_fixture"] is True and facts["reached_transition"] is True
    assert facts["seeded"] == {
        "projects": 2,
        "boards": 2,
        "sessions": 5,
        "tasks": 8,
        "direct": 2,
    }
    bound = facts["bound"]
    assert len(bound) == 8 and len(set(bound.values())) == 8
    assert all(identity.startswith("t_") for identity in bound.values())
    # Every bound identity is a row the writer itself created on its own board: the lane
    # cannot pass with an identity of its own.
    for key, task_id in bound.items():
        assert task_id in facts["board_rows"][facts["boards_by_key"][key]], key
    assert facts["transition"]["errors"] == []
    assert facts["transition"]["completed"] == facts["expected_transition"]
    assert facts["expected_transition"] == [bound["A1"], bound["B1"], bound["B3"]]


def test_d16s_real_fixture_expectations_cover_smoke_boundaries_and_idle(
    tmp_path: Path,
) -> None:
    """The real fixture and collector satisfy every live scope plan without live effects."""
    from aether_agents.monitor.collector import MonitorCollector
    from aether_agents.monitor.runtime import _markers_for_snapshot, load_direct_records
    from aether_agents.monitor.sources import ReadOnlySources
    from scripts import qualify_telegram_monitor as q
    from scripts import telegram_monitor_lab as lab

    runtime_py = Path(os.environ.get("AETHER_HERMES_PYTHON", "").strip())
    if not runtime_py.is_file():
        pytest.skip("product runtime interpreter not available")

    profile_home, env_prov = _make_d16r_test_profile(tmp_path)
    plan = lab.build_plan(tmp_path / "lab", "20260911T120000Z", token="abcdef012345")
    preflight = q._lab_preflight(
        plan, interpreter=runtime_py, profile_home=profile_home, environ=env_prov
    )
    assert preflight["problems"] == []
    record = q._lab_create(plan, preflight)
    gate = q._lab_context_preflight(plan, preflight, interpreter=runtime_py)
    assert gate["problems"] == []

    manifest = q._scope_manifest(Path(record["scope_root"]), plan.stamp)
    q._write_scope_projects(Path(record["scope_root"]), manifest)
    seeded = q._lab_fixture(runtime_py, record, manifest)
    assert {
        key: len(seeded[key]) for key in ("projects", "boards", "sessions", "tasks", "direct")
    } == {
        "projects": 2,
        "boards": 2,
        "sessions": 5,
        "tasks": 8,
        "direct": 2,
    }

    store = q.MonitorStore(Path(record["state_root"]))
    assert q._environment_gaps(store, hermes_home=Path(record["hermes_home"])) == []
    enabled = q._lab_control(runtime_py, record, q.ACTION_ON)
    assert enabled["ok"] is True

    try:
        sources = ReadOnlySources(
            state_root=store.state_root,
            hermes_home=Path(record["hermes_home"]),
        )
        collector = MonitorCollector(store, sources)
        first_cutoff = datetime.now(timezone.utc)
        first = collector.collect(
            cutoff_utc=first_cutoff,
            direct_records=load_direct_records(store),
        )
        plans = q._scope_expectation_plans(manifest)
        for label, expected_items, expected_item_gaps in plans[:2]:
            q._evaluate_scope_expectations(
                first.snapshot,
                expected_items=expected_items,
                expected_item_gaps=expected_item_gaps,
            )
            assert label in {"smoke", "boundary-1"}

        wrong = dict(plans[0][1])
        pipeline_a = next(key for key in wrong if key.startswith("pipeline:"))
        wrong[pipeline_a] = "queued"
        with pytest.raises(q.QualificationError) as mismatch:
            q._evaluate_scope_expectations(first.snapshot, expected_items=wrong)
        assert mismatch.value.code == "scope-state"
        assert mismatch.value.detail["observed"] == "running"

        for work_key, marker in _markers_for_snapshot(first.snapshot).items():
            store.mark_final_outcome_delivery(work_key, marker)

        time.sleep(1.1)
        transition = q._lab_transition(runtime_py, record, manifest)
        assert transition["errors"] == []
        second_cutoff = first_cutoff + timedelta(minutes=1)
        second = collector.collect(
            cutoff_utc=second_cutoff,
            direct_records=load_direct_records(store),
        )
        _, expected_after, expected_item_gaps_after = plans[2]
        q._evaluate_scope_expectations(
            second.snapshot,
            expected_items=expected_after,
            expected_item_gaps=expected_item_gaps_after,
        )
        for work_key, marker in _markers_for_snapshot(second.snapshot).items():
            store.mark_final_outcome_delivery(work_key, marker)

        idle = collector.collect(
            cutoff_utc=second_cutoff + timedelta(minutes=1),
            direct_records=load_direct_records(store),
        )
        _, expected_idle, expected_item_gaps_idle = plans[3]
        q._evaluate_scope_expectations(
            idle.snapshot,
            expected_items=expected_idle,
            expected_item_gaps=expected_item_gaps_idle,
        )
        assert idle.source.idle is True
    finally:
        # This is a scratch lab only; leave no enabled native job behind in the test root.
        q._lab_control(runtime_py, record, q.ACTION_OFF)


def test_real_laboratory_gate_refuses_an_unsupported_writer(
    tmp_path: Path,
) -> None:
    """The in-laboratory gate, not the read-only phase, owns the writer surface refusal.

    The native tree is the same functional tree with the review writer removed.  The
    read-only phase cannot see it (it never resolves the writer surface), so the run creates
    its private root — and the gate then refuses with a bounded capability code before the
    synthetic scope is seeded, the job is enabled or anything is spent.
    """

    native_root = _write_chain_native_tree(tmp_path / "native", drop="request_review")
    profile, environment = _chain_context(tmp_path, native_root)

    facts = _run_chain_driver(tmp_path, environment, profile)

    assert "driver_error" not in facts, facts
    assert facts["phase1_problems"] == []
    assert facts["created"] is True
    assert facts["gate_problems"] == [
        "writer-interface-missing:hermes_cli.kanban_db.request_review"
    ]
    assert facts["reached_fixture"] is False
    assert facts["reached_transition"] is False


def test_bounded_native_scheduler_instance_starts_and_stops_cooperatively(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """One supervised native scheduler child is started, then stopped and verified gone."""

    module = _qualification_module()
    lab = _fake_lab_record(tmp_path)
    script: list[str] = []
    # The bounded waits are exercised, not endured: shrink them for this unit test.
    monkeypatch.setattr(module, "LAB_SCHEDULER_STOP_SECONDS", 0.05)
    monkeypatch.setattr(module, "LAB_SCHEDULER_POLL_SECONDS", 0.01)

    class _Process:
        pid = 5150
        returncode = None

        def __init__(self) -> None:
            Path(lab["root"]).joinpath("control").mkdir(parents=True, exist_ok=True)

        def poll(self) -> int | None:
            return None

        def terminate(self) -> None:
            script.append("terminate")

    def fake_popen(command: Sequence[str], **kwargs: Any) -> Any:
        environment = kwargs["env"]
        assert environment["HERMES_HOME"] == lab["hermes_home"]
        assert environment["HOME"] == lab["environment"]["HOME"]
        script.append(Path(command[0]).name)
        body = command[-1]
        match = re.search(r'READY_JSON = ("(?:[^"\\\\]|\\\\.)*")', body)
        assert match is not None, "the scheduler body must carry its ready marker"
        Path(json.loads(match.group(1))).write_text(
            json.dumps(
                {
                    "pid": 5150,
                    "scheduler": "builtin",
                    "scheduler_class": "cron.scheduler_provider.InProcessCronScheduler",
                    "execution_mode": "native-scheduled-tick",
                    "interval_seconds": module.LAB_SCHEDULER_INTERVAL_SECONDS,
                }
            ),
            encoding="utf-8",
        )
        return _Process()

    monkeypatch.setattr(module.subprocess, "Popen", fake_popen)
    alive = {"value": True}
    monkeypatch.setattr(module, "_pid_alive", lambda pid: alive["value"])

    started = module._lab_scheduler_start(Path("/usr/bin/false"), lab)
    assert started["ready"] is True and started["scheduler"] == "builtin"

    # A runner that never exits is not success: the lane refuses instead of qualifying.
    with pytest.raises(module.QualificationError) as error:
        module._lab_scheduler_stop(lab, {**started, "pid": 5150})
    assert error.value.code == "lab-scheduler-stop"

    alive["value"] = False
    stopped = module._lab_scheduler_stop(lab, started)
    assert stopped["stopped"] is True and stopped["cooperative"] is True


def _fake_lab_record(tmp_path: Path) -> dict[str, Any]:
    root = tmp_path / "laboratory"
    (root / "control").mkdir(parents=True, exist_ok=True)
    return {
        "root": str(root),
        "state_root": str(root / "xdg-state" / "aether"),
        "hermes_home": str(root / "hermes"),
        "scope_root": str(root / "scope"),
        "environment": {"HOME": str(root / "home"), "HERMES_HOME": str(root / "hermes")},
        "retained": True,
    }


@pytest.mark.parametrize(
    ("stage", "code", "effects_allowed"),
    [
        ("preflight", "lab-preflight", False),
        ("context-preflight", "lab-context-preflight", False),
        ("create", "lab-create", False),
        ("fixture", "lab-fixture", False),
        ("enable", "enable-invalid", True),
        ("scheduler", "lab-scheduler", True),
        ("transition", "lab-transition", True),
        ("retention", "lab-retention", True),
        ("scheduler-stop", "lab-scheduler-stop", True),
        ("off", "manual-off", True),
    ],
)
def test_every_fail_closed_laboratory_stage_never_qualifies(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    stage: str,
    code: str,
    effects_allowed: bool,
) -> None:
    """Each fail-closed stage returns a bounded error and can never emit a qualified verdict."""

    world = _build_world(tmp_path, monkeypatch)
    backends = world["backends"]
    output = tmp_path / "private" / "receipt.json"
    if stage == "preflight":
        backends.preflight_problems = ["lab-root-inside-repository"]
    elif stage == "context-preflight":
        backends.context_preflight_problems = [
            "writer-interface-missing:hermes_cli.kanban_db.request_review"
        ]
    elif stage == "create":
        backends.create_failure = code
    elif stage == "fixture":
        backends.fixture_failure = code
    elif stage == "enable":
        backends.enable_failure = code
    elif stage == "scheduler":
        backends.scheduler_start_failure = code
    elif stage == "transition":
        backends.transition_failure = code
    elif stage == "retention":
        backends.retention_problems = ["not-private:lab.json"]
    elif stage == "scheduler-stop":
        backends.scheduler_stop_failure = True
    elif stage == "off":
        backends.off_failure = True

    with pytest.raises(world["module"].QualificationError) as error:
        _run_live(world, output)

    assert error.value.code == code
    receipt = json.loads(output.read_text(encoding="utf-8"))
    assert receipt["ok"] is False
    assert receipt["public_summary"]["qualified"] is False
    assert code in receipt["public_summary"]["errors"]
    assert receipt["retention"]["registry_touched"] is False
    if not effects_allowed:
        assert "lab_control:on" not in backends.calls
        assert backends.trigger_calls == 0
        assert "lab_scheduler_start" not in backends.calls
    # The bounded failure never leaves a live lab scheduler behind: a scheduler whose
    # start refused is stopped by definition, and every other stage drives the stop.
    if stage != "scheduler":
        assert ("lab_scheduler_start" in backends.calls) == (
            "lab_scheduler_stop" in backends.calls or backends.scheduler_stop_failure
        )


# --- D14 Provisioned profile normalization and reference destination tests ---


def test_d14_hermes_home_both_shapes_normalize_to_same_profile(tmp_path: Path) -> None:
    """Both HERMES_HOME conventions normalize to the same verified Morfeo profile."""
    q = _qualification_module()

    multi_root = tmp_path / "hermes_multi"
    exact_profile = multi_root / "profiles" / "morfeo"
    exact_profile.mkdir(parents=True)
    (exact_profile / "config.yaml").write_text("agent:\n  name: Morfeo\n", encoding="utf-8")

    norm_multi, class_multi, digest_multi = q._normalize_profile_home(multi_root)
    norm_exact, class_exact, digest_exact = q._normalize_profile_home(exact_profile)

    assert norm_multi == exact_profile.resolve()
    assert norm_exact == exact_profile.resolve()
    assert class_multi == "multi-profile-root"
    assert class_exact == "exact-profile"
    assert digest_multi == digest_exact
    assert len(digest_multi) == 64
    assert str(exact_profile) not in digest_multi


def test_d14_normalize_profile_refuses_missing_and_wrong_candidates(tmp_path: Path) -> None:
    """Missing and differently named candidates refuse before any effect."""
    q = _qualification_module()

    with pytest.raises(q.QualificationError) as missing_err:
        q._normalize_profile_home(tmp_path / "nonexistent")
    assert missing_err.value.code == "lab-profile"
    assert "does not exist" in missing_err.value.message

    wrong_named = tmp_path / "implementer"
    wrong_named.mkdir()
    (wrong_named / "config.yaml").write_text("agent:\n  name: implementer\n", encoding="utf-8")
    with pytest.raises(q.QualificationError) as wrong_err:
        q._normalize_profile_home(wrong_named)
    assert wrong_err.value.code == "lab-profile"
    assert "differently named candidate is refused" in wrong_err.value.message


def test_d14_normalize_profile_refuses_ambiguous_and_symlinked_candidates(tmp_path: Path) -> None:
    """Ambiguous and symlinked profile candidates refuse before any effect."""
    q = _qualification_module()

    ambig = tmp_path / "ambiguous_root" / "morfeo"
    ambig.mkdir(parents=True)
    (ambig / "config.yaml").write_text("agent:\n  name: Morfeo\n", encoding="utf-8")
    child = ambig / "profiles" / "morfeo"
    child.mkdir(parents=True)
    (child / "config.yaml").write_text("agent:\n  name: Morfeo\n", encoding="utf-8")

    with pytest.raises(q.QualificationError) as ambig_err:
        q._normalize_profile_home(ambig)
    assert ambig_err.value.code == "lab-profile"
    assert "ambiguous candidate is refused" in ambig_err.value.message

    real_prof = tmp_path / "real_dir" / "morfeo"
    real_prof.mkdir(parents=True)
    (real_prof / "config.yaml").write_text("agent:\n  name: Morfeo\n", encoding="utf-8")
    sym_prof = tmp_path / "sym_prof"
    sym_prof.symlink_to(real_prof)

    with pytest.raises(q.QualificationError) as sym_err:
        q._normalize_profile_home(sym_prof)
    assert sym_err.value.code == "lab-profile"
    assert "symbolic link" in sym_err.value.message


def test_d14_normalize_profile_refuses_missing_and_symlinked_config(tmp_path: Path) -> None:
    """Profiles missing configuration or using symlinked configuration are refused."""
    q = _qualification_module()

    no_cfg = tmp_path / "no_cfg" / "morfeo"
    no_cfg.mkdir(parents=True)
    with pytest.raises(q.QualificationError) as no_cfg_err:
        q._normalize_profile_home(no_cfg)
    assert no_cfg_err.value.code == "lab-profile"
    assert "config.yaml missing" in no_cfg_err.value.message

    sym_cfg_prof = tmp_path / "sym_cfg" / "morfeo"
    sym_cfg_prof.mkdir(parents=True)
    external_cfg = tmp_path / "external_config.yaml"
    external_cfg.write_text("agent:\n  name: Morfeo\n", encoding="utf-8")
    (sym_cfg_prof / "config.yaml").symlink_to(external_cfg)
    with pytest.raises(q.QualificationError) as sym_cfg_err:
        q._normalize_profile_home(sym_cfg_prof)
    assert sym_cfg_err.value.code == "lab-profile"
    assert "symbolic link" in sym_cfg_err.value.message


def test_d14_normalize_profile_refuses_relative_path_and_worker_identity_substitution(
    tmp_path: Path,
) -> None:
    """Relative paths, cwd fallback, and inherited worker identities cannot substitute."""
    q = _qualification_module()

    with pytest.raises(q.QualificationError) as rel_err:
        q._normalize_profile_home(Path("relative/morfeo"))
    assert rel_err.value.code == "lab-profile"
    assert "relative paths and cwd fallback are refused" in rel_err.value.message

    worker_prof = tmp_path / "profiles" / "implementer"
    worker_prof.mkdir(parents=True)
    (worker_prof / "config.yaml").write_text("agent:\n  name: implementer\n", encoding="utf-8")

    environ = {
        "HERMES_HOME": str(worker_prof),
        "HERMES_PROFILE": "morfeo",
        "HERMES_KANBAN_TASK": "t_dummy",
    }
    with pytest.raises(q.QualificationError) as subst_err:
        q._normalize_profile_home(environ=environ)
    assert subst_err.value.code == "lab-profile"
    assert "differently named candidate is refused" in subst_err.value.message


def test_d14_provisioned_reference_environment_strips_access(tmp_path: Path) -> None:
    """The provisioned reference environment is rooted at Morfeo and strips access names."""
    q = _qualification_module()

    prof = tmp_path / "profiles" / "morfeo"
    prof.mkdir(parents=True)
    (prof / "config.yaml").write_text("agent:\n  name: Morfeo\n", encoding="utf-8")

    environ = {
        "PATH": "/usr/bin:/bin",
        "HOME": "/home/user",
        "TELEGRAM_BOT_TOKEN": "secret-token",
        "TELEGRAM_HOME_CHANNEL": "secret-channel",
        "AETHER_ROUTER_API_KEY": "secret-key",
        "HERMES_TIMEZONE": "UTC",
    }
    ref_env = q._provisioned_reference_environment(prof, environ=environ)
    assert ref_env["HERMES_HOME"] == str(prof)
    assert ref_env["HERMES_TIMEZONE"] == "UTC"
    assert "TELEGRAM_BOT_TOKEN" not in ref_env
    assert "TELEGRAM_HOME_CHANNEL" not in ref_env
    assert "AETHER_ROUTER_API_KEY" not in ref_env
    assert not any(k.startswith(("TELEGRAM_", "AETHER_ROUTER_")) for k in ref_env)


def test_d14_negative_control_reference_probe_rejects_injected_lab_access(
    tmp_path: Path,
) -> None:
    """Supplying lab access to the reference probe is rejected (negative control)."""
    q = _qualification_module()

    prof = tmp_path / "profiles" / "morfeo"
    prof.mkdir(parents=True)
    (prof / "config.yaml").write_text("agent:\n  name: Morfeo\n", encoding="utf-8")

    with pytest.raises(q.QualificationError) as err1:
        q._lab_destination(
            Path(sys.executable),
            environment={"TELEGRAM_HOME_CHANNEL": "12345"},
            lab_root=None,
            profile_home=prof,
        )
    assert err1.value.code == "lab-reference-access-rejected"

    with pytest.raises(q.QualificationError) as err2:
        q._lab_destination(
            Path(sys.executable),
            environment={"TELEGRAM_BOT_TOKEN": "token123"},
            lab_root=None,
            profile_home=prof,
        )
    assert err2.value.code == "lab-reference-access-rejected"


def test_d14_native_probe_body_executes_load_hermes_dotenv_before_load_gateway_config() -> None:
    """_LAB_NATIVE_PROBE calls load_hermes_dotenv before load_gateway_config."""
    q = _qualification_module()
    body = q._LAB_NATIVE_PROBE

    dotenv_pos = body.find("load_hermes_dotenv()")
    gw_pos = body.find("load_gateway_config()")

    assert dotenv_pos != -1, "load_hermes_dotenv() call missing from probe body"
    assert gw_pos != -1, "load_gateway_config() call missing from probe body"
    assert dotenv_pos < gw_pos, "load_hermes_dotenv must execute before load_gateway_config"


def test_d14_target_digest_equality_and_no_access_values(tmp_path: Path) -> None:
    """Target digest matches between reference and lab probe, and no access values leak."""
    q = _qualification_module()
    lab_mod = _lab_module()

    chat_id = "-100000"
    token = "test-secret-token-12345"

    access = {"TELEGRAM_HOME_CHANNEL": chat_id, "TELEGRAM_BOT_TOKEN": token}
    fingerprint = lab_mod.access_fingerprint(access)
    assert chat_id not in str(fingerprint)
    assert token not in str(fingerprint)

    # Materialize minimal native tree and private provisioned context
    native_root = _write_chain_native_tree(tmp_path / "native")
    prof, env = _chain_context(tmp_path, native_root)
    env["PYTHONPATH"] = str(native_root) + ":" + os.environ.get("PYTHONPATH", "")

    # 1. Provisioned reference probe: resolves destination from profile .env via load_hermes_dotenv
    ref_env = {"PYTHONPATH": str(native_root) + ":" + os.environ.get("PYTHONPATH", "")}
    ref_res = q._lab_destination(Path(sys.executable), environment=ref_env, profile_home=prof)
    assert ref_res.get("problems") == []
    ref_digest = ref_res.get("destination_digest")
    assert ref_digest is not None
    assert len(ref_digest) == 64
    assert chat_id not in ref_digest

    # 2. Laboratory probe: resolves destination inside lab root from borrowed access
    lab_root = tmp_path / "lab_root"
    lab_root.mkdir()
    lab_env = {
        "PATH": os.environ.get("PATH", ""),
        "PYTHONPATH": env["PYTHONPATH"],
        "TELEGRAM_HOME_CHANNEL": chat_id,
        "HERMES_HOME": str(lab_root / "hermes"),
    }
    lab_res = q._lab_destination(Path(sys.executable), environment=lab_env, lab_root=lab_root)
    assert lab_res.get("problems") == []
    lab_digest = lab_res.get("destination_digest")
    assert lab_digest is not None

    # Reference destination digest and lab route destination digest are exactly equal
    assert ref_digest == lab_digest


def test_d14_runtime_reference_destination_probe_matches_gateway_context() -> None:
    """When the product runtime is available, reference probe resolves with matching digest."""
    q = _qualification_module()

    runtime_py: Path | None = None
    env_py = os.environ.get("AETHER_HERMES_PYTHON", "").strip()
    if env_py and Path(env_py).is_file():
        runtime_py = Path(env_py)
    else:
        try:
            runtime_py = q._runtime_python()
        except Exception:
            pass
    if runtime_py is None or not runtime_py.is_file():
        for parent in Path(__file__).resolve().parents:
            cand = parent / "home" / ".venv-hermes" / "bin" / "python"
            if cand.is_file():
                runtime_py = cand
                break
    if runtime_py is None or not runtime_py.is_file():
        pytest.skip("product runtime interpreter not available")

    prof: Path | None = None
    env_prof = os.environ.get("AETHER_MORFEO_PROFILE_HOME", "").strip()
    if env_prof:
        try:
            prof, _, _ = q._normalize_profile_home(Path(env_prof))
        except Exception:
            pass
    if prof is None:
        for parent in Path(__file__).resolve().parents:
            cand = parent / "home" / "profiles" / "morfeo"
            if cand.is_dir():
                try:
                    prof, _, _ = q._normalize_profile_home(cand)
                    break
                except Exception:
                    pass
    if prof is None:
        try:
            prof, _, _ = q._normalize_profile_home()
        except Exception:
            pass
    if prof is None or not prof.is_dir():
        pytest.skip("provisioned Morfeo profile not available")

    res = q._lab_destination(runtime_py, environment=None, profile_home=prof)
    assert res.get("problems") == []
    digest = res.get("destination_digest")
    assert digest is not None
    assert digest.startswith("36007c9a8b0f8394")
    assert res.get("destination_thread_present") is False


def test_d14_preserved_prior_refusal_receipt_and_log_unchanged() -> None:
    """The preserved v2 refusal receipt and log match their recorded SHA-256 digests."""
    env_dir = os.environ.get("AETHER_TELEGRAM_MONITOR_EVIDENCE_DIR", "").strip()
    evidence_dir = (
        Path(env_dir)
        if env_dir
        else Path.home() / ".local" / "qualification" / "telegram-monitor-evidence"
    )
    receipt = evidence_dir / "telegram-monitor-live.json"
    log = evidence_dir / "live-run.log"

    if not evidence_dir.is_dir() or not receipt.is_file() or not log.is_file():
        pytest.skip("preserved qualification refusal evidence not available on this machine")

    receipt_sha = hashlib.sha256(receipt.read_bytes()).hexdigest()
    log_sha = hashlib.sha256(log.read_bytes()).hexdigest()

    assert receipt_sha == "eb2f3ad3fda8ffb1e5439ad2d26694aec0d97f468bab5aa49dcd065afea94578"
    assert log_sha == "5a9ca1fe13d358a44d6907d5d23d99b1e599f70c0087f2eb6fc0d77ff774fdaa"


# --- D14R Production module chain resolution and stale mapping refusal tests ---


def _write_stale_mapping_native_tree(root: Path) -> Path:
    """Materialize a native tree where hermes_state cannot be imported early.

    Simulates the stale editable-install mapping: importing hermes_state directly fails with
    ModuleNotFoundError unless cron.scheduler_provider was imported first.
    """
    native_root = _write_chain_native_tree(root)
    hs = native_root / "hermes_state.py"
    original_hs = hs.read_text(encoding="utf-8")
    hs.write_text(
        "import sys\n"
        'if "_HERMES_BOOTSTRAPPED" not in sys.modules:\n'
        "    raise ModuleNotFoundError(\"No module named 'hermes_state_compaction'\")\n"
        + original_hs,
        encoding="utf-8",
    )

    cron_sp = native_root / "cron" / "scheduler_provider.py"
    original_sp = cron_sp.read_text(encoding="utf-8")
    cron_sp.write_text(
        "import sys\nsys.modules['_HERMES_BOOTSTRAPPED'] = True\n" + original_sp,
        encoding="utf-8",
    )
    return native_root


def test_d14r_stale_mapping_reproduction_refuses_at_preflight_before_lab_created(
    tmp_path: Path,
) -> None:
    """Stale mapping is refused at the read-only preflight before laboratory creation."""
    native_root = _write_stale_mapping_native_tree(tmp_path / "native")
    profile, environment = _chain_context(tmp_path, native_root)

    facts = _run_chain_driver(tmp_path, environment, profile)

    assert "driver_error" not in facts, facts
    # Refusal happens in read-only preflight:
    assert any("fixture-imports" in p for p in facts["phase1_problems"])
    assert any("writer-interface-missing" in p for p in facts["phase1_problems"])
    assert facts["root_after_phase1"] is False
    # Laboratory root was never created:
    assert facts.get("created", False) is False
    assert not (tmp_path / "lab-host").exists()
    assert facts["reached_fixture"] is False
    assert facts["reached_transition"] is False


def test_d14r_in_lab_gate_exercises_fixture_import_order_unmasked_by_cron(
    tmp_path: Path,
) -> None:
    """The in-laboratory gate exercises fixture import order and is not masked by cron."""
    q = _qualification_module()
    native_root = _write_stale_mapping_native_tree(tmp_path / "native")
    _, environment = _chain_context(tmp_path, native_root)

    lab_root = tmp_path / "lab-root"
    lab_root.mkdir()
    isolated = q._lab_destination(
        Path(sys.executable), environment=dict(environment), lab_root=lab_root
    )

    problems = isolated.get("problems", [])
    assert any("fixture-imports" in p for p in problems)
    assert any("writer-interface-missing:hermes_state.SessionDB" in p for p in problems)


def test_d14r_preflight_refuses_missing_hermes_state_writer_surface(
    tmp_path: Path,
) -> None:
    """Preflight refuses missing SessionDB writer methods before lab creation."""
    native_root = _write_chain_native_tree(tmp_path / "native", drop="create_session")
    profile, environment = _chain_context(tmp_path, native_root)

    facts = _run_chain_driver(tmp_path, environment, profile)

    assert "driver_error" not in facts, facts
    assert facts["phase1_problems"] == [
        "provisioned-writer-interface-missing:hermes_state.SessionDB.create_session"
    ]
    assert facts["root_after_phase1"] is False
    assert facts.get("created", False) is False
    assert not (tmp_path / "lab-host").exists()


def test_d14r_native_probe_body_executes_fixture_imports_before_cron_and_gateway() -> None:
    """_LAB_NATIVE_PROBE imports fixture chain before cron and gateway, matching _LAB_FIXTURE_PROBE."""
    q = _qualification_module()
    native_body = q._LAB_NATIVE_PROBE
    fixture_body = q._LAB_FIXTURE_PROBE

    chain = [
        "from aether_agents.monitor import runtime as monitor_runtime",
        "from aether_agents.monitor.store import MonitorStore",
        "from aether_agents.observation.context import ProjectRegistry",
        "from hermes_cli import kanban_db, projects_db",
        "from hermes_state import SessionDB",
    ]

    for stmt in chain:
        assert stmt in native_body, f"{stmt} missing from _LAB_NATIVE_PROBE"
        assert stmt in fixture_body, f"{stmt} missing from _LAB_FIXTURE_PROBE"

    # Assert identical import order across both probes
    for first, second in zip(chain[:-1], chain[1:], strict=True):
        assert native_body.find(first) < native_body.find(second), (
            f"{first} must precede {second} in _LAB_NATIVE_PROBE"
        )
        assert fixture_body.find(first) < fixture_body.find(second), (
            f"{first} must precede {second} in _LAB_FIXTURE_PROBE"
        )

    state_pos = native_body.find("from hermes_state import SessionDB")
    cron_pos = native_body.find("from cron.scheduler_provider import InProcessCronScheduler")
    gw_pos = native_body.find("load_gateway_config()")

    assert cron_pos != -1, "InProcessCronScheduler missing from probe body"
    assert gw_pos != -1, "load_gateway_config missing from probe body"
    assert state_pos < cron_pos, "fixture import chain must precede cron imports"
    assert state_pos < gw_pos, "fixture import chain must precede gateway config"


def test_d14r_preserved_v3_failed_receipt_and_console_log_unchanged() -> None:
    """The preserved v3 failure receipt and console log match recorded SHA-256 digests."""
    env_dir = os.environ.get("AETHER_TELEGRAM_MONITOR_EVIDENCE_DIR", "").strip()
    evidence_dir = (
        Path(env_dir)
        if env_dir
        else Path.home() / ".local" / "qualification" / "telegram-monitor-evidence"
    )
    receipt = evidence_dir / "telegram-monitor-live-v3.json"
    console_log = evidence_dir / "live-run-v3-console.log"

    if not evidence_dir.is_dir() or not receipt.is_file() or not console_log.is_file():
        pytest.skip("preserved v3 failed qualification evidence not available on this machine")

    receipt_sha = hashlib.sha256(receipt.read_bytes()).hexdigest()
    console_sha = hashlib.sha256(console_log.read_bytes()).hexdigest()

    assert receipt_sha == "c23096fe793fd2263a2f59525b23799729b64eb3f61b9803932ae9b9496b79e8"
    assert console_sha == "a6046560aedbdc6d47d209010baa2e9c63ee1ae66c8a841f274a88347e81189d"


def test_d15r_coverage_probe_context_binds_to_lab_hermes_home(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The coverage probe evaluates using the lab's Hermes root, never the parent profile."""
    from aether_agents.monitor import sources as monitor_sources

    q = _qualification_module()

    captured_sources: list[dict[str, Any]] = []

    class SpyReadOnlySources:
        def __init__(self, *args: Any, **kwargs: Any) -> None:
            captured_sources.append(kwargs)

        def collect(self, *args: Any, **kwargs: Any) -> Any:
            class DummyCollection:
                coverage_gaps: tuple[str, ...] = ()

            return DummyCollection()

    monkeypatch.setattr(monitor_sources, "ReadOnlySources", SpyReadOnlySources)

    lab_hermes = (tmp_path / "lab_hermes").resolve()
    lab_state = (tmp_path / "lab_state").resolve()
    fake_lab = {
        "hermes_home": str(lab_hermes),
        "state_root": str(lab_state),
    }
    store = q.MonitorStore(lab_state)

    # 1. Real LiveBackends.environment_gaps with explicit hermes_home
    backends = q.LiveBackends()
    gaps1 = backends.environment_gaps(store, hermes_home=lab_hermes)
    assert gaps1 == []
    assert len(captured_sources) == 1
    assert captured_sources[0]["hermes_home"] == lab_hermes
    assert captured_sources[0]["state_root"] == lab_state

    # 2. Real LiveBackends.environment_gaps with lab mapping (derives hermes_home)
    gaps2 = backends.environment_gaps(store, lab=fake_lab)
    assert gaps2 == []
    assert len(captured_sources) == 2
    assert captured_sources[1]["hermes_home"] == lab_hermes
    assert captured_sources[1]["state_root"] == lab_state

    # 3. Direct real _environment_gaps with hermes_home
    gaps3 = q._environment_gaps(store, hermes_home=lab_hermes)
    assert gaps3 == []
    assert len(captured_sources) == 3
    assert captured_sources[2]["hermes_home"] == lab_hermes
    assert captured_sources[2]["state_root"] == lab_state


def test_d15r_reproduction_and_corrected_gap_free_laboratory(tmp_path: Path) -> None:
    """Reproduction of pre-correction false refusal vs corrected gap-free lab."""
    import sqlite3

    from aether_agents.observation.context import ProjectRegistry

    q = _qualification_module()

    project_schema = (
        "CREATE TABLE projects (id TEXT PRIMARY KEY, slug TEXT NOT NULL, "
        "name TEXT NOT NULL, primary_path TEXT, archived INTEGER NOT NULL DEFAULT 0);"
    )
    board_schema = (
        "CREATE TABLE tasks (id TEXT PRIMARY KEY, title TEXT NOT NULL, status TEXT NOT NULL, "
        "project_id TEXT, session_id TEXT, created_at REAL, started_at REAL, completed_at REAL, "
        "workspace_path TEXT, current_run_id INTEGER, session_affinity TEXT, block_kind TEXT, "
        "last_heartbeat_at REAL, max_runtime_seconds INTEGER, result TEXT, "
        "consecutive_failures INTEGER NOT NULL DEFAULT 0);"
        "CREATE TABLE task_links (parent_id TEXT NOT NULL, child_id TEXT NOT NULL);"
        "CREATE TABLE task_runs (id INTEGER PRIMARY KEY, task_id TEXT, status TEXT, outcome TEXT, "
        "started_at REAL, ended_at REAL, last_heartbeat_at REAL, summary TEXT, error TEXT, profile TEXT);"
        "CREATE TABLE task_events (id INTEGER PRIMARY KEY, task_id TEXT, run_id INTEGER, kind TEXT, "
        "payload TEXT, created_at REAL);"
    )
    session_schema = (
        "CREATE TABLE sessions (id TEXT PRIMARY KEY, source TEXT NOT NULL, title TEXT, "
        "display_name TEXT, cwd TEXT, git_repo_root TEXT, started_at REAL, ended_at REAL, last_activity_at REAL);"
        "CREATE TABLE messages (id INTEGER PRIMARY KEY, session_id TEXT, role TEXT, content TEXT, timestamp REAL);"
    )

    lab_root = tmp_path / "lab"
    lab_hermes = lab_root / "hermes"
    lab_state = lab_root / "xdg-state" / "aether"
    scope_root = lab_root / "scope"
    lab_hermes.mkdir(parents=True)
    lab_state.mkdir(parents=True)
    scope_root.mkdir(parents=True)

    stamp = "20260911T053000Z"
    manifest = q._scope_manifest(scope_root, stamp)
    q._write_scope_projects(scope_root, manifest)

    with sqlite3.connect(lab_hermes / "projects.db") as pconn:
        pconn.executescript(project_schema)
        for entry in manifest:
            pconn.execute(
                "INSERT INTO projects VALUES (?, ?, ?, ?, 0)",
                (
                    f"p_native_{entry['letter'].lower()}",
                    entry["board_slug"],
                    entry["name"],
                    entry["path"],
                ),
            )

    with sqlite3.connect(lab_hermes / "state.db") as sconn:
        sconn.executescript(session_schema)
        for entry in manifest:
            for s in entry["sessions"]:
                sconn.execute(
                    "INSERT INTO sessions VALUES (?, ?, ?, ?, ?, ?, 1000.0, 1000.0, 1000.0)",
                    (s["id"], s["source"], s["title"], s["title"], s["cwd"], s["git_repo_root"]),
                )

    reg = ProjectRegistry(lab_state)
    for entry in manifest:
        reg.register(
            entry["project_id"],
            Path(entry["path"]),
            entry["name"],
            f"p_native_{entry['letter'].lower()}",
        )

    for entry in manifest:
        bdir = lab_hermes / "kanban" / "boards" / entry["board_slug"]
        bdir.mkdir(parents=True)
        (bdir / "board.json").write_text(
            json.dumps(
                {
                    "slug": entry["board_slug"],
                    "name": entry["name"],
                    "description": "Execution board",
                    "icon": "",
                    "color": "",
                    "default_workdir": entry["path"],
                    "project_id": f"p_native_{entry['letter'].lower()}",
                    "aether_project_id": entry["project_id"],
                    "aether_contract_id": entry["contract_id"],
                    "aether_contract_version": 1,
                    "created_at": 1789104311,
                    "archived": False,
                }
            ),
            encoding="utf-8",
        )
        with sqlite3.connect(bdir / "kanban.db") as bconn:
            bconn.executescript(board_schema)
            for idx, task in enumerate(entry["tasks"]):
                tid = f"t_{entry['letter'].lower()}{idx + 1:07d}"
                bconn.execute(
                    "INSERT INTO tasks (id, title, status, project_id, session_id, created_at, started_at, completed_at, workspace_path, result) "
                    "VALUES (?, ?, ?, ?, ?, 1000.0, 1000.0, 1000.0, ?, ?)",
                    (
                        tid,
                        task["title"],
                        task["status"],
                        f"p_native_{entry['letter'].lower()}",
                        entry["origin_session"],
                        entry["path"],
                        task.get("result"),
                    ),
                )

    store = q.MonitorStore(lab_state)

    # 1. Pre-correction reproduction: probe against empty/unrelated root yields coverage gaps
    empty_prod_hermes = tmp_path / "prod"
    empty_prod_hermes.mkdir()
    prod_gaps = q._environment_gaps(store, hermes_home=empty_prod_hermes)
    assert prod_gaps != []
    assert any(
        g in prod_gaps
        for g in (
            "NATIVE_PROJECTS_UNREADABLE",
            "SESSION_DB_UNREADABLE",
            "BOARD_METADATA_UNREADABLE",
        )
    )

    # 2. Corrected candidate: probe against lab_hermes yields ZERO coverage gaps
    lab_gaps = q._environment_gaps(store, hermes_home=lab_hermes)
    assert lab_gaps == []


def test_d15r_negative_control_broken_lab_refuses(tmp_path: Path) -> None:
    """A deliberately broken lab still refuses with matching coverage gap codes."""
    import sqlite3

    from aether_agents.observation.context import ProjectRegistry

    q = _qualification_module()

    project_schema = (
        "CREATE TABLE projects (id TEXT PRIMARY KEY, slug TEXT NOT NULL, "
        "name TEXT NOT NULL, primary_path TEXT, archived INTEGER NOT NULL DEFAULT 0);"
    )
    board_schema = (
        "CREATE TABLE tasks (id TEXT PRIMARY KEY, title TEXT NOT NULL, status TEXT NOT NULL, "
        "project_id TEXT, session_id TEXT, created_at REAL, started_at REAL, completed_at REAL, "
        "workspace_path TEXT, current_run_id INTEGER, session_affinity TEXT, block_kind TEXT, "
        "last_heartbeat_at REAL, max_runtime_seconds INTEGER, result TEXT, "
        "consecutive_failures INTEGER NOT NULL DEFAULT 0);"
        "CREATE TABLE task_links (parent_id TEXT NOT NULL, child_id TEXT NOT NULL);"
        "CREATE TABLE task_runs (id INTEGER PRIMARY KEY, task_id TEXT, status TEXT, outcome TEXT, "
        "started_at REAL, ended_at REAL, last_heartbeat_at REAL, summary TEXT, error TEXT, profile TEXT);"
        "CREATE TABLE task_events (id INTEGER PRIMARY KEY, task_id TEXT, run_id INTEGER, kind TEXT, "
        "payload TEXT, created_at REAL);"
    )
    session_schema = (
        "CREATE TABLE sessions (id TEXT PRIMARY KEY, source TEXT NOT NULL, title TEXT, "
        "display_name TEXT, cwd TEXT, git_repo_root TEXT, started_at REAL, ended_at REAL, last_activity_at REAL);"
        "CREATE TABLE messages (id INTEGER PRIMARY KEY, session_id TEXT, role TEXT, content TEXT, timestamp REAL);"
    )

    lab_root = tmp_path / "broken_lab"
    lab_hermes = lab_root / "hermes"
    lab_state = lab_root / "xdg-state" / "aether"
    scope_root = lab_root / "scope"
    lab_hermes.mkdir(parents=True)
    lab_state.mkdir(parents=True)
    scope_root.mkdir(parents=True)

    manifest = q._scope_manifest(scope_root, "20260911T053500Z")
    q._write_scope_projects(scope_root, manifest)

    with sqlite3.connect(lab_hermes / "projects.db") as pconn:
        pconn.executescript(project_schema)
        for entry in manifest:
            pconn.execute(
                "INSERT INTO projects VALUES (?, ?, ?, ?, 0)",
                (
                    f"p_native_{entry['letter'].lower()}",
                    entry["board_slug"],
                    entry["name"],
                    entry["path"],
                ),
            )

    with sqlite3.connect(lab_hermes / "state.db") as sconn:
        sconn.executescript(session_schema)
        for entry in manifest:
            for s in entry["sessions"]:
                sconn.execute(
                    "INSERT INTO sessions VALUES (?, ?, ?, ?, ?, ?, 1000.0, 1000.0, 1000.0)",
                    (s["id"], s["source"], s["title"], s["title"], s["cwd"], s["git_repo_root"]),
                )

    reg = ProjectRegistry(lab_state)
    for entry in manifest:
        reg.register(
            entry["project_id"],
            Path(entry["path"]),
            entry["name"],
            f"p_native_{entry['letter'].lower()}",
        )

    for entry in manifest:
        bdir = lab_hermes / "kanban" / "boards" / entry["board_slug"]
        bdir.mkdir(parents=True)
        (bdir / "board.json").write_text(
            json.dumps(
                {
                    "slug": entry["board_slug"],
                    "name": entry["name"],
                    "description": "Execution board",
                    "icon": "",
                    "color": "",
                    "default_workdir": entry["path"],
                    "project_id": f"p_native_{entry['letter'].lower()}",
                    "aether_project_id": entry["project_id"],
                    "aether_contract_id": entry["contract_id"],
                    "aether_contract_version": 1,
                    "created_at": 1789104311,
                    "archived": False,
                }
            ),
            encoding="utf-8",
        )
        with sqlite3.connect(bdir / "kanban.db") as bconn:
            bconn.executescript(board_schema)

    # 1. Deliberately break board A: remove portable project ID from metadata
    meta_a = lab_hermes / "kanban" / "boards" / manifest[0]["board_slug"] / "board.json"
    data = json.loads(meta_a.read_text(encoding="utf-8"))
    del data["aether_project_id"]
    meta_a.write_text(json.dumps(data), encoding="utf-8")

    store = q.MonitorStore(lab_state)
    gaps_unbound = q._environment_gaps(store, hermes_home=lab_hermes)
    assert "BOARD_PROJECT_UNBOUND" in gaps_unbound

    # 2. Deliberately break contract B: remove final contract artifact
    contract_b_artifact = (
        Path(manifest[1]["path"])
        / ".aether"
        / "objective-contracts"
        / manifest[1]["contract_id"]
        / "v1.md"
    )
    contract_b_artifact.unlink()

    gaps_missing_contract = q._environment_gaps(store, hermes_home=lab_hermes)
    assert "FINAL_CONTRACT_UNREADABLE" in gaps_missing_contract


def test_d15r_fixture_and_environment_gaps_chain_end_to_end(tmp_path: Path) -> None:
    """When product runtime is available, the full fixture + environment_gaps chain yields zero gaps."""
    from scripts import qualify_telegram_monitor as q
    from scripts import telegram_monitor_lab as lab

    runtime_py: Path | None = None
    env_py = os.environ.get("AETHER_HERMES_PYTHON", "").strip()
    if env_py and Path(env_py).is_file():
        runtime_py = Path(env_py)
    else:
        try:
            runtime_py = q._runtime_python()
        except Exception:
            pass
    if runtime_py is None or not runtime_py.is_file():
        for parent in Path(__file__).resolve().parents:
            cand = parent / "home" / ".venv-hermes" / "bin" / "python"
            if cand.is_file():
                runtime_py = cand
                break
    if runtime_py is None or not runtime_py.is_file():
        pytest.skip("product runtime interpreter not available")

    plan = lab.build_plan(tmp_path / "lab", "20260911T054500Z", token="abcdef012345")
    preflight = {
        "problems": [],
        "config_text": "",
        "config_digest": "0" * 64,
        "_environment": {
            "HERMES_HOME": str(plan.hermes_home),
            "HOME": str(plan.home),
            "TMPDIR": str(plan.tmp),
            # ``scripts/run_tests.py`` puts the exact Hermes baseline checkout first on the
            # test process's PYTHONPATH.  A laboratory child inherits PYTHONPATH by design,
            # so forwarding the runner's value would shadow the product runtime's own tree
            # with the baseline checkout (which lacks this fork's patched writers).  The
            # live lane never runs with that shadow: the child resolves only the worktree's
            # own sources plus its interpreter's environment.
            "PYTHONPATH": str(ROOT / "src"),
        },
    }
    lab_record = q._lab_create(plan, preflight)
    scope_root = Path(lab_record["scope_root"])
    manifest = q._scope_manifest(scope_root, plan.stamp)
    q._write_scope_projects(scope_root, manifest)

    seeded = q._lab_fixture(runtime_py, lab_record, manifest)
    assert len(seeded["boards"]) == 2
    assert len(seeded["tasks"]) == 8

    store = q.MonitorStore(Path(lab_record["state_root"]))
    gaps = q._environment_gaps(store, hermes_home=Path(lab_record["hermes_home"]))
    assert gaps == []


def test_d16r_lab_context_resolves_morfeo_profile_and_reads_configuration(tmp_path: Path) -> None:
    """Lab child resolves the morfeo profile and reads the laboratory configuration."""
    from scripts import qualify_telegram_monitor as q
    from scripts import telegram_monitor_lab as lab

    plan = lab.build_plan(tmp_path / "lab", "20260911T120000Z", token="abcdef012345")
    assert plan.hermes_home == plan.profile_home
    assert plan.hermes_home.name == "morfeo"
    assert plan.hermes_home.parent.name == "profiles"

    config_data = {
        "model": {"default": "candidate-model"},
        "timezone": "UTC",
        "plugins": {
            "enabled": ["aether-telegram-monitor"],
            "entries": {"aether-telegram-monitor": {"settings": {"enabled": True}}},
        },
    }
    lab.create_root(plan)
    lab.write_config(plan, lab.serialize_config(config_data))

    env = lab.child_environment(
        plan,
        base={"PATH": os.environ.get("PATH", "")},
        access={"TELEGRAM_BOT_TOKEN": "token-123", "TELEGRAM_HOME_CHANNEL": "-1000"},
        repository_src=ROOT / "src",
    )
    assert env["HERMES_HOME"] == str(plan.profile_home)

    runtime_py = Path(os.environ.get("AETHER_HERMES_PYTHON", "").strip())
    if not runtime_py.is_file():
        pytest.skip("product runtime interpreter not available")

    probe = """
import json
from hermes_cli import profiles
from hermes_cli.config import load_config

print(json.dumps({
    "active_profile": profiles.get_active_profile_name(),
    "model": load_config().get("model"),
    "plugins": load_config().get("plugins"),
}))
"""
    res = q._runtime_execute(runtime_py, probe, environment=env)
    assert res["active_profile"] == "morfeo"
    assert res["model"] == {"default": "candidate-model"}
    assert "aether-telegram-monitor" in res["plugins"]["enabled"]


def test_d16r_child_containment_verifies_roots_inside_lab_and_refuses_escapes(
    tmp_path: Path,
) -> None:
    """Context problems verify roots resolve inside lab and refuse escapes."""
    from scripts import telegram_monitor_lab as lab

    plan = lab.build_plan(tmp_path / "lab", "20260911T120000Z", token="abcdef012345")
    env = lab.child_environment(
        plan,
        base={"PATH": os.environ.get("PATH", "")},
        access={"TELEGRAM_BOT_TOKEN": "token-123", "TELEGRAM_HOME_CHANNEL": "-1000"},
        repository_src=ROOT / "src",
    )
    assert lab.context_problems(plan, env) == []

    # Escaping HERMES_HOME is refused
    bad_env = dict(env)
    bad_env["HERMES_HOME"] = str(tmp_path / "outside")
    problems = lab.context_problems(plan, bad_env)
    assert any("HERMES_HOME" in p for p in problems)

    # Missing plugins_meta in PYTHONPATH is refused
    no_meta_env = dict(env)
    no_meta_env["PYTHONPATH"] = str(ROOT / "src")
    problems_no_meta = lab.context_problems(plan, no_meta_env)
    assert "plugins-meta-not-in-pythonpath" in problems_no_meta


def test_d16r_candidate_plugin_discovered_and_registered_in_lab_child(tmp_path: Path) -> None:
    """Lab child discovers and registers candidate's monitor plugin with tools and hooks."""
    from scripts import qualify_telegram_monitor as q
    from scripts import telegram_monitor_lab as lab

    plan = lab.build_plan(tmp_path / "lab", "20260911T120000Z", token="abcdef012345")
    lab.create_root(plan)
    lab.write_config(
        plan,
        lab.serialize_config(
            lab.minimal_config({"model": {"default": "candidate"}, "timezone": "UTC"})
        ),
    )
    env = lab.child_environment(
        plan,
        base={"PATH": os.environ.get("PATH", "")},
        access={"TELEGRAM_BOT_TOKEN": "token-123", "TELEGRAM_HOME_CHANNEL": "-1000"},
        repository_src=ROOT / "src",
    )

    runtime_py = Path(os.environ.get("AETHER_HERMES_PYTHON", "").strip())
    if not runtime_py.is_file():
        pytest.skip("product runtime interpreter not available")

    probe = """
import json, importlib.metadata
from hermes_cli.plugins import PluginManager

eps = [ep.name for ep in importlib.metadata.entry_points(group="hermes_agent.plugins")]
mgr = PluginManager()
mgr.discover_and_load(force=True)
plugin = mgr._plugins.get("aether-telegram-monitor")

print(json.dumps({
    "eps": eps,
    "plugin_loaded": plugin is not None,
    "plugin_enabled": getattr(plugin, "enabled", False),
    "tools": getattr(plugin, "tools_registered", []),
    "hooks": getattr(plugin, "hooks_registered", []),
    "error": getattr(plugin, "error", None),
}))
"""
    res = q._runtime_execute(runtime_py, probe, environment=env)
    assert "aether-telegram-monitor" in res["eps"]
    assert res["plugin_loaded"] is True
    assert res["plugin_enabled"] is True
    assert sorted(res["tools"]) == ["aether_monitor", "aether_monitor_report_snapshot"]
    assert sorted(res["hooks"]) == ["on_session_end", "post_llm_call", "post_tool_call"]
    assert res["error"] is None


def _make_d16r_test_profile(tmp_path: Path) -> tuple[Path, dict[str, str]]:
    hermes = tmp_path / "prov" / "hermes"
    prof = hermes / "profiles" / "morfeo"
    prof.mkdir(parents=True, exist_ok=True)
    (hermes / "gateway-home.json").write_text(
        json.dumps({"chat_id": "-1000", "thread_id": None}), encoding="utf-8"
    )
    (prof / "config.yaml").write_text(
        "model:\n  default: candidate\nagent:\n  name: Morfeo\n", encoding="utf-8"
    )
    (prof / ".env").write_text(
        "TELEGRAM_BOT_TOKEN=tok-123\nTELEGRAM_HOME_CHANNEL=-1000\n", encoding="utf-8"
    )
    env = dict(os.environ)
    # ``scripts/run_tests.py`` puts the exact Hermes baseline checkout first on the test
    # process's PYTHONPATH.  A laboratory child inherits PYTHONPATH by design, so that
    # runner path would shadow the provisioned runtime's own tree (the baseline lacks this
    # fork's patched writers) and the gate would refuse it before any effect.  The live
    # lane runs without that shadow, so the simulated provisioned context omits it.
    env.pop("PYTHONPATH", None)
    env["HERMES_HOME"] = str(prof)
    return prof, env


def test_d16r_gate_refuses_lab_when_plugin_cannot_be_loaded(tmp_path: Path) -> None:
    """In-lab gate refuses fail-closed before any effect when plugin cannot load."""
    import shutil

    from scripts import qualify_telegram_monitor as q
    from scripts import telegram_monitor_lab as lab

    runtime_py = Path(os.environ.get("AETHER_HERMES_PYTHON", "").strip())
    if not runtime_py.is_file():
        pytest.skip("product runtime interpreter not available")

    profile_home, env_prov = _make_d16r_test_profile(tmp_path)

    plan = lab.build_plan(tmp_path / "lab", "20260911T120000Z", token="abcdef012345")
    preflight = q._lab_preflight(
        plan, interpreter=runtime_py, profile_home=profile_home, environ=env_prov
    )
    q._lab_create(plan, preflight)

    # 1. Negative case: plugin metadata missing
    shutil.rmtree(plan.plugins_meta)
    plan.plugins_meta.mkdir()
    gate1 = q._lab_context_preflight(plan, preflight, interpreter=runtime_py)
    assert "monitor-plugin-missing" in gate1["problems"]

    # 2. Negative case: plugin disabled in config
    lab.write_plugin_metadata(plan)
    cfg_path = plan.profile_home / lab.LAB_CONFIG_NAME
    cfg_path.write_text(
        lab.serialize_config({"plugins": {"enabled": [], "entries": {}}}),
        encoding="utf-8",
    )
    gate2 = q._lab_context_preflight(plan, preflight, interpreter=runtime_py)
    assert any("monitor-plugin" in p for p in gate2["problems"])


def test_d16r_enable_reaches_native_job_creation_in_lab_context(tmp_path: Path) -> None:
    """The pre-effect harness chain reaches ACTION_ON and creates the native job without RUNTIME_MISMATCH."""
    from scripts import qualify_telegram_monitor as q
    from scripts import telegram_monitor_lab as lab

    runtime_py = Path(os.environ.get("AETHER_HERMES_PYTHON", "").strip())
    if not runtime_py.is_file():
        pytest.skip("product runtime interpreter not available")

    profile_home, env_prov = _make_d16r_test_profile(tmp_path)

    plan = lab.build_plan(tmp_path / "lab", "20260911T120000Z", token="abcdef012345")
    preflight = q._lab_preflight(
        plan, interpreter=runtime_py, profile_home=profile_home, environ=env_prov
    )
    assert preflight["problems"] == []

    record = q._lab_create(plan, preflight)
    gate = q._lab_context_preflight(plan, preflight, interpreter=runtime_py)
    assert gate["problems"] == []
    assert gate["monitor_plugin"]["present"] is True
    assert gate["monitor_plugin"]["enabled"] is True

    scope_root = Path(record["scope_root"])
    manifest = q._scope_manifest(scope_root, plan.stamp)
    q._write_scope_projects(scope_root, manifest)
    seeded = q._lab_fixture(runtime_py, record, manifest)
    assert len(seeded["projects"]) == 2

    store = q.MonitorStore(Path(record["state_root"]))
    gaps = q._environment_gaps(store, hermes_home=Path(record["hermes_home"]))
    assert gaps == []

    ctrl = q._lab_control(runtime_py, record, q.ACTION_ON)
    assert ctrl.get("ok") is True
    assert ctrl["result"]["enabled"] is True
    assert ctrl["result"]["profile_binding"] == "morfeo"
    assert ctrl["result"]["native_job"]["schedule"] == "0 * * * *"


def test_d16t_lab_scheduler_stop_detects_cooperative_exit_and_records_status(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A child that exits cooperatively is reported stopped without consuming the bound and status is recorded."""
    module = _qualification_module()
    monkeypatch.setattr(module, "LAB_SCHEDULER_STOP_SECONDS", 0.2)
    monkeypatch.setattr(module, "LAB_SCHEDULER_POLL_SECONDS", 0.02)
    lab = _fake_lab_record(tmp_path)
    control = Path(lab["root"]) / "control"
    control.mkdir(parents=True, exist_ok=True)
    stop = control / "scheduler-stop"

    child_code = f"""
import time, sys
from pathlib import Path
stop = Path({str(stop)!r})
while not stop.exists():
    time.sleep(0.02)
sys.exit(0)
"""
    process = subprocess.Popen([sys.executable, "-c", child_code])
    scheduler = {
        "pid": process.pid,
        "process": process,
        "stop_file": str(stop),
        "ready": True,
    }
    try:
        stopped = module._lab_scheduler_stop(lab, scheduler)
        assert stopped["stopped"] is True
        assert stopped["cooperative"] is True
        assert stopped["exit_code"] == 0
        assert stopped["exit_status"] == 0
    finally:
        with contextlib.suppress(OSError):
            process.kill()
        process.wait()


def test_d16t_lab_scheduler_stop_fails_closed_when_child_ignores_stop_and_sigterm(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A child that ignores the stop file and SIGTERM still fails after the bound."""
    module = _qualification_module()
    monkeypatch.setattr(module, "LAB_SCHEDULER_STOP_SECONDS", 0.05)
    monkeypatch.setattr(module, "LAB_SCHEDULER_POLL_SECONDS", 0.01)
    lab = _fake_lab_record(tmp_path)
    control = Path(lab["root"]) / "control"
    control.mkdir(parents=True, exist_ok=True)
    stop = control / "scheduler-stop"

    child_code = """
import os, signal, sys, time
signal.signal(signal.SIGTERM, signal.SIG_IGN)
while True:
    time.sleep(0.05)
"""
    process = subprocess.Popen([sys.executable, "-c", child_code])
    scheduler = {
        "pid": process.pid,
        "process": process,
        "stop_file": str(stop),
        "ready": True,
    }
    try:
        with pytest.raises(module.QualificationError) as exc_info:
            module._lab_scheduler_stop(lab, scheduler)
        assert exc_info.value.code == "lab-scheduler-stop"
    finally:
        with contextlib.suppress(OSError):
            os.kill(process.pid, signal.SIGKILL)
        process.wait()


def test_d16t_harness_start_in_last_seconds_reaches_valid_smoke_window(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A harness start inside the last seconds of a minute waits for the boundary and reaches smoke."""
    start_time = START + timedelta(seconds=46)
    world = _build_world(
        tmp_path,
        monkeypatch,
        expose_evidence=False,
        phases=(
            START + timedelta(minutes=1),
            START + timedelta(minutes=2),
        ),
    )
    world["clock"].value = start_time
    world["backends"].enable_next_cut = START + timedelta(minutes=2)
    output = tmp_path / "private" / "receipt.json"
    with pytest.raises(world["module"].QualificationError) as error:
        _run_live(world, output)
    # The start lead wait prevented the mistimed start from failing with smoke-window;
    # it progressed past enable and scheduler start to trigger the smoke.
    assert error.value.code != "smoke-window"
    assert any("sleep:14.1" in call for call in world["backends"].calls)
    assert world["backends"].trigger_calls == 1
    assert "lab_control:on" in world["backends"].calls
    assert "lab_scheduler_start" in world["backends"].calls
    assert "lab_scheduler_stop" in world["backends"].calls
