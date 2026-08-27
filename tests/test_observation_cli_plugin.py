"""CLI and release-locked Hermes adapter integration for contract observation."""

from __future__ import annotations

import ast
import hashlib
import json
import logging
import os
import re
import secrets
import sqlite3
import subprocess
import tarfile
import zipfile
from argparse import Namespace
from copy import deepcopy
from io import StringIO
from pathlib import Path
from typing import Any

import pytest
from observation_helpers import PROJECT_ID, TRACE_ID, EventFactory, complete_trace

from aether_agents.cli import main
from aether_agents.commands.observe import run_observe
from aether_agents.observation import query, report
from aether_agents.observation.capture.journal import JournalWriter, list_segments, read_segment
from aether_agents.observation.context import ProjectRegistry
from aether_agents.observation.contracts import (
    canonical_json_bytes,
    validate_event,
    validate_summary,
)
from aether_agents.observation.identity import correlation_token
from aether_agents.observation.privacy import assert_clean, safe_error_class
from aether_agents.observation.reduce.reducer import ReductionInput, reduce_events
from aether_agents.paths import ObservationPaths


class FakePluginContext:
    """Small public-PluginContext-shaped facade; no private Hermes surface."""

    def __init__(self, profile_name: str = "morfeo") -> None:
        self.profile_name = profile_name
        self.hooks: dict[str, list[Any]] = {}
        self.unload_callbacks: list[Any] = []

    def register_hook(self, name: str, callback: Any) -> None:
        self.hooks.setdefault(name, []).append(callback)

    def on_unload(self, callback: Any) -> None:
        self.unload_callbacks.append(callback)


def _install_project(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> tuple[Path, ObservationPaths]:
    xdg = tmp_path / "xdg"
    project = tmp_path / "project"
    marker = project / ".aether" / "project.toml"
    marker.parent.mkdir(parents=True)
    marker.write_text(f'project_id = "{PROJECT_ID}"\n', encoding="utf-8")
    monkeypatch.setenv("XDG_STATE_HOME", str(xdg))
    registry = ProjectRegistry()
    assert registry.register(PROJECT_ID, project, "fixture")
    return project, ObservationPaths.for_project(PROJECT_ID)


def _write_fixture_journal(paths: ObservationPaths) -> None:
    fixture = complete_trace()
    _write_events(paths, fixture)


def _write_events(paths: ObservationPaths, fixture: EventFactory) -> None:
    writer = JournalWriter(paths=paths, producer_epoch=fixture.epoch)
    writer.open()
    try:
        for event in fixture.events:
            assert writer.append(event).accepted
    finally:
        writer.close()


def _journal_events(paths: ObservationPaths) -> list[dict[str, Any]]:
    events: list[dict[str, Any]] = []
    for segment in list_segments(paths):
        for line in read_segment(segment.path).lines:
            events.append(json.loads(line))
    return events


def test_observe_human_and_json_share_the_same_canonical_summary(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    project, paths = _install_project(monkeypatch, tmp_path)
    _write_fixture_journal(paths)

    human_out, human_err = StringIO(), StringIO()
    code = run_observe(
        Namespace(project=str(project), ref=TRACE_ID, since=None, watch=False, json=False),
        stdout=human_out,
        stderr=human_err,
    )
    assert code == 0 and not human_err.getvalue()

    json_out, json_err = StringIO(), StringIO()
    code = run_observe(
        Namespace(project=str(project), ref=TRACE_ID, since=None, watch=False, json=True),
        stdout=json_out,
        stderr=json_err,
    )
    envelope = json.loads(json_out.getvalue())
    assert code == 0 and not json_err.getvalue()
    assert envelope["result"] == "ready"
    assert set(envelope["data"]) == {"state", "summary"}
    assert envelope["data"]["state"] == "summary"
    validate_summary(envelope["data"]["summary"])
    assert envelope["data"]["summary"]["summary_id"] in human_out.getvalue()
    assert "CONCLUSION" in human_out.getvalue()
    assert "NEXT DECISION REQUIRED" in human_out.getvalue()


def test_objective_contract_finalize_materializes_trace_and_root_create_binds(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    from aether_agents.observation.capture import hermes_plugin

    _, paths = _install_project(monkeypatch, tmp_path)
    monkeypatch.setenv("AETHER_PROJECT_ID", PROJECT_ID)
    monkeypatch.setattr(hermes_plugin._NativeReconciliationWorker, "start", lambda self: None)
    context = FakePluginContext()
    hermes_plugin.register(context)
    contract_id = "oc_1234567890abcdef"
    trace_id = "ctr_abcdef0123456789abcdef0123456789"
    context.hooks["post_tool_call"][0](
        tool_name="objective_contract",
        tool_call_id="finalize",
        session_id="session-contract",
        status="success",
        args={"action": "finalize"},
        result={
            "project_id": PROJECT_ID,
            "contract_id": contract_id,
            "version": 1,
            "status": "final",
            "relative_path": ".aether/objective-contracts/oc_1234567890abcdef/v1.md",
            "sha256": "a" * 64,
            "observation_trace_id": trace_id,
        },
    )
    context.hooks["post_tool_call"][0](
        tool_name="kanban_create",
        tool_call_id="root-create",
        session_id="session-contract",
        status="success",
        args={"idempotency_key": correlation_token(trace_id, "root")},
        result={"ok": True, "task_id": "t_12345678", "project_id": PROJECT_ID},
    )
    context.unload_callbacks[-1]()
    events = _journal_events(paths)
    assert {event["event_type"] for event in events} >= {
        "trace.opened",
        "contract.persisted",
        "work_unit.bound",
    }
    assert {event["trace_id"] for event in events} == {trace_id}
    assert {event.get("contract_id") for event in events if event["event_type"] == "trace.opened"} == {
        contract_id
    }


def test_observe_empty_human_and_json_share_one_discriminated_representation(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    project, _paths = _install_project(monkeypatch, tmp_path)

    human_out, human_err = StringIO(), StringIO()
    code = run_observe(
        Namespace(project=str(project), ref=None, since=None, watch=False, json=False),
        stdout=human_out,
        stderr=human_err,
    )
    assert code == 0 and not human_err.getvalue()

    json_out, json_err = StringIO(), StringIO()
    code = run_observe(
        Namespace(project=str(project), ref=None, since=None, watch=False, json=True),
        stdout=json_out,
        stderr=json_err,
    )
    envelope = json.loads(json_out.getvalue())
    assert code == 0 and not json_err.getvalue()
    assert envelope["result"] == "ready"
    assert envelope["data"] == {"state": "empty", "summary": None}
    assert human_out.getvalue() == "No observed contract trace for this project yet.\n"


def test_observe_rejects_watch_json_in_one_stable_json_envelope(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    project, paths = _install_project(monkeypatch, tmp_path)
    _write_fixture_journal(paths)
    summaries = iter((complete_trace().summary(), complete_trace().summary()))
    monkeypatch.setattr(query, "watch", lambda *_args, **_kwargs: summaries)

    stdout, stderr = StringIO(), StringIO()
    code = run_observe(
        Namespace(project=str(project), ref=TRACE_ID, since=None, watch=True, json=True),
        stdout=stdout,
        stderr=stderr,
    )

    lines = stdout.getvalue().splitlines()
    assert code == 2
    assert stderr.getvalue() == ""
    assert len(lines) == 1
    envelope = json.loads(lines[0])
    assert envelope["result"] == "error"
    assert envelope["data"] == {}
    assert envelope["errors"] == [
        {
            "code": "WATCH_JSON_UNSUPPORTED",
            "message": "--watch cannot be combined with --json",
        }
    ]


def test_observe_without_ref_selects_the_only_open_trace(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    project, paths = _install_project(monkeypatch, tmp_path)
    fixture = EventFactory()
    fixture.opened()
    _write_events(paths, fixture)

    stdout, stderr = StringIO(), StringIO()
    code = run_observe(
        Namespace(project=str(project), ref=None, since=None, watch=False, json=True),
        stdout=stdout,
        stderr=stderr,
    )
    envelope = json.loads(stdout.getvalue())
    assert code == 0 and not stderr.getvalue()
    assert envelope["data"]["state"] == "summary"
    assert envelope["data"]["summary"]["trace_id"] == TRACE_ID


def test_observe_without_ref_rejects_multiple_open_traces(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    project, paths = _install_project(monkeypatch, tmp_path)
    first = EventFactory()
    first.opened()
    second = EventFactory(
        trace_id="ctr_22222222222222222222222222222222",
        epoch="prd_33333333333333333333333333333333",
    )
    second.opened()
    second.events[0]["event_id"] = "evt_22222222222222222222222222222222"
    _write_events(paths, first)
    _write_events(paths, second)

    stdout, stderr = StringIO(), StringIO()
    code = run_observe(
        Namespace(project=str(project), ref=None, since=None, watch=False, json=True),
        stdout=stdout,
        stderr=stderr,
    )
    envelope = json.loads(stdout.getvalue())
    assert code == 2 and not stderr.getvalue()
    assert envelope["result"] == "error"
    assert envelope["data"] == {}
    assert envelope["errors"][0]["code"] == "TRACE_AMBIGUOUS"
    assert envelope["errors"][0]["details"]["candidates"] == sorted((TRACE_ID, second.trace_id))


def test_observe_without_ref_surfaces_terminal_event_when_authority_is_unavailable(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    project, paths = _install_project(monkeypatch, tmp_path)
    fixture = EventFactory()
    fixture.opened()
    fixture.contract("trace.failed", "failed", 1)
    _write_events(paths, fixture)

    stdout, stderr = StringIO(), StringIO()
    code = run_observe(
        Namespace(project=str(project), ref=None, since=None, watch=False, json=True),
        stdout=stdout,
        stderr=stderr,
    )
    envelope = json.loads(stdout.getvalue())
    assert code == 0 and not stderr.getvalue()
    assert envelope["data"]["state"] == "summary"
    summary = envelope["data"]["summary"]
    assert summary["runtime_state"]["termination"] == "open"
    assert {
        "AUTHORITY_CONTEXT_UNAVAILABLE",
        "TERMINAL_AUTHORITY_UNVERIFIED",
    }.issubset({gap["reason_code"] for gap in summary["coverage"]["gaps"]})


def test_observe_rejects_a_ref_that_matches_no_trace(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    project, _paths = _install_project(monkeypatch, tmp_path)

    stdout, stderr = StringIO(), StringIO()
    code = run_observe(
        Namespace(
            project=str(project),
            ref="contract-does-not-exist",
            since=None,
            watch=False,
            json=True,
        ),
        stdout=stdout,
        stderr=stderr,
    )
    envelope = json.loads(stdout.getvalue())
    assert code == 2 and not stderr.getvalue()
    assert envelope["result"] == "error"
    assert envelope["errors"][0]["code"] == "TRACE_NOT_FOUND"


def test_observe_rejects_an_unresolved_project_without_guessing(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setenv("XDG_STATE_HOME", str(tmp_path / "xdg"))
    project = tmp_path / "not-an-aether-project"
    project.mkdir()

    stdout, stderr = StringIO(), StringIO()
    code = run_observe(
        Namespace(project=str(project), ref=None, since=None, watch=False, json=True),
        stdout=stdout,
        stderr=stderr,
    )
    envelope = json.loads(stdout.getvalue())
    assert code == 3 and not stderr.getvalue()
    assert envelope["result"] == "error"
    assert envelope["errors"][0]["code"] == "PROJECT_UNRESOLVED"


def test_cli_rejects_unknown_flags_for_every_implemented_command(
    capsys: pytest.CaptureFixture[str],
) -> None:
    assert main(["observe", "--bogus"]) == 2
    assert "unrecognized arguments: --bogus" in capsys.readouterr().err
    assert main(["doctor", "--future-a1-flag"]) == 2
    assert "unrecognized arguments: --future-a1-flag" in capsys.readouterr().err


def test_since_diff_ignores_tool_and_token_growth_but_reports_semantic_change() -> None:
    previous = complete_trace().summary()
    count_only = deepcopy(previous)
    count_only["tools"]["total_calls"] += 1
    count_only["tools"]["completed"] += 1
    count_only["model_context_economics"]["tokens"]["total_tokens"] = 999
    assert report.diff_summaries(count_only, previous)["change_classes"] == []

    changed = deepcopy(previous)
    changed["review_brief"]["verdict"] = "blocked"
    changed["review_brief"]["next_gate"]["kind"] = "owner_decision"
    diff = report.diff_summaries(changed, previous)
    assert set(diff["change_classes"]) >= {"verdict", "next_gate"}


def test_watch_backs_off_skips_full_reduction_and_suppresses_count_only_change(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    paths = ObservationPaths.for_project(PROJECT_ID, root=Path("/tmp/aether-watch-fixture"))
    baseline = complete_trace().summary()
    count_only = deepcopy(baseline)
    count_only["summary_id"] = "sum_" + "4" * 64
    count_only["tools"]["total_calls"] += 1
    semantic = deepcopy(count_only)
    semantic["summary_id"] = "sum_" + "5" * 64
    semantic["review_brief"]["verdict"] = "blocked"

    signatures = iter([("a",), ("a",), ("a",), ("b",), ("c",)])
    summaries = iter([baseline, count_only, semantic])
    reductions: list[str] = []
    sleeps: list[float] = []
    monkeypatch.setattr(query, "_fs_signature", lambda _paths: next(signatures))

    def load(_paths: ObservationPaths, trace_id: str) -> dict[str, Any]:
        reductions.append(trace_id)
        return next(summaries)

    monkeypatch.setattr(query, "load_summary", load)
    stream = query.watch(paths, TRACE_ID, sleep=sleeps.append)
    assert next(stream)["summary_id"] == baseline["summary_id"]
    assert next(stream)["review_brief"]["verdict"] == "blocked"
    assert reductions == [TRACE_ID, TRACE_ID, TRACE_ID]
    assert sleeps == [1.0, 2.0, 4.0, 1.0]


def test_release_locked_hook_taxonomy_registration_and_manager_isolation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from hermes_cli.plugins import VALID_HOOKS, PluginContext, PluginManager, PluginManifest

    from aether_agents.observation.capture import hermes_plugin

    assert set(hermes_plugin.OBSERVED_HOOKS) <= VALID_HOOKS
    ctx = FakePluginContext()
    hermes_plugin.register(ctx)
    first_counts = {name: len(callbacks) for name, callbacks in ctx.hooks.items()}
    hermes_plugin.register(ctx)
    assert first_counts == {name: 1 for name in hermes_plugin.OBSERVED_HOOKS}
    assert {name: len(callbacks) for name, callbacks in ctx.hooks.items()} == first_counts
    assert len(ctx.unload_callbacks) == 1

    # Exercise Hermes's real callback isolation boundary, not a local imitation.
    manager = PluginManager(scope_key="/tmp/aether-plugin-isolation")
    manifest = PluginManifest(
        name="aether-isolation-fixture",
        key="aether-isolation-fixture",
        source="entrypoint",
    )
    real_ctx = PluginContext(manifest, manager)
    monkeypatch.setattr(
        hermes_plugin._Observer,
        "dispatch",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(RuntimeError("synthetic")),
    )
    hermes_plugin.register(real_ctx)
    assert manager.invoke_hook("pre_tool_call", tool_name="x", tool_call_id="c") == []


def test_plugin_projects_native_payload_before_any_disk_write(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    from aether_agents.observation.capture import hermes_plugin

    _, paths = _install_project(monkeypatch, tmp_path)
    monkeypatch.setenv("AETHER_PROJECT_ID", PROJECT_ID)
    monkeypatch.setenv("HERMES_HOME", str(tmp_path / "hermes" / "profiles" / "morfeo"))
    monkeypatch.setattr(hermes_plugin._NativeReconciliationWorker, "start", lambda self: None)

    ctx = FakePluginContext()
    hermes_plugin.register(ctx)
    token = correlation_token(TRACE_ID, "root-unit")
    caplog.set_level(logging.DEBUG)
    runtime_nonce = secrets.token_hex(24)
    native_secret = (
        f"runtime-{runtime_nonce} raw prompt /etc/passwd owner-{runtime_nonce}@example.invalid"
    )
    unproven_error_type = f"runtime_secret_{secrets.token_hex(24)}"
    secret_values = [f"{native_secret} sink-{index}" for index in range(7)]
    ctx.hooks["pre_tool_call"][0](
        tool_name="kanban_create",
        tool_call_id="create-1",
        session_id="session-1",
        args={"idempotency_key": token, "body": secret_values[0]},
        user_task=secret_values[0],
        middleware_trace=secret_values[0],
    )
    ctx.hooks["post_tool_call"][0](
        tool_name="kanban_create",
        tool_call_id="create-1",
        session_id="session-1",
        status="success",
        args={"idempotency_key": token, "body": secret_values[0]},
        result={
            "ok": True,
            "task_id": "t_aaaaaaaa",
            "project_id": PROJECT_ID,
            "summary": secret_values[1],
        },
        error_message=secret_values[2],
    )
    ctx.hooks["pre_tool_call"][0](
        tool_name="terminal",
        tool_call_id="call-2",
        session_id="session-1",
        task_id="t_aaaaaaaa",
        args={"command": secret_values[0]},
    )
    ctx.hooks["post_tool_call"][0](
        tool_name="terminal",
        tool_call_id="call-2",
        session_id="session-1",
        task_id="t_aaaaaaaa",
        status="failed",
        result=secret_values[1],
        error_message=secret_values[2],
        error_type=unproven_error_type,
    )
    ctx.hooks["pre_api_request"][0](
        api_request_id="req-1",
        session_id="session-1",
        turn_id="turn-1",
        task_id="t_aaaaaaaa",
        model="model-1",
        provider="provider-1",
        system_prompt=secret_values[3],
        message_count=2,
        tool_count=3,
    )
    ctx.hooks["post_api_request"][0](
        api_request_id="req-1",
        session_id="session-1",
        turn_id="turn-1",
        task_id="t_aaaaaaaa",
        status="completed",
        response=secret_values[4],
        usage={"input_tokens": 2, "output_tokens": 3, "total_tokens": 5},
    )
    ctx.hooks["on_skill_lifecycle"][0](
        action="loaded",
        skill_name="safe-skill",
        session_id="session-1",
        task_id="t_aaaaaaaa",
    )
    ctx.hooks["subagent_start"][0](
        child_session_id="child-1",
        parent_session_id="session-1",
        task_id="t_aaaaaaaa",
        goal=secret_values[5],
    )
    ctx.hooks["subagent_stop"][0](
        child_session_id="child-1",
        parent_session_id="session-1",
        task_id="t_aaaaaaaa",
        status="completed",
        summary=secret_values[6],
    )
    for callback in reversed(ctx.unload_callbacks):
        callback()

    events = _journal_events(paths)
    assert {event["event_type"] for event in events} >= {
        "trace.opened",
        "work_unit.bound",
        "tool.started",
        "tool.failed",
        "model.request_started",
        "model.request_completed",
        "skill.loaded",
        "participant.joined",
        "participant.left",
    }
    assert {
        event["configuration"]["scope"]
        for event in events
        if event["event_type"] == "configuration.observed"
    } == {"trace", "participant"}
    assert any(
        event["configuration"]["observed_skill_set_fingerprint"] is not None
        and event["configuration"]["field_coverage"]["observed_skills"] == "exact"
        for event in events
        if event["event_type"] == "configuration.observed"
    )
    for event in events:
        validate_event(event)
        assert_clean(event)
    assert safe_error_class("ValueError") == "ValueError"
    assert safe_error_class("POLICY_DENIED") == "POLICY_DENIED"
    assert safe_error_class("policy.denied") == "policy.denied"
    failed_tool = next(event for event in events if event["event_type"] == "tool.failed")
    assert re.fullmatch(
        r"call_fpk_[a-f0-9]{32}_[a-f0-9]{64}",
        failed_tool["tool"]["call_id"],
    )
    assert failed_tool["tool"]["error_class"] is None
    assert any(
        re.fullmatch(
            r"api_fpk_[a-f0-9]{32}_[a-f0-9]{64}",
            event.get("model_request", {}).get("request_ref", ""),
        )
        and event.get("model_request", {}).get("provider") == "provider-1"
        for event in events
    )

    cli_streams: list[str] = []
    for json_mode in (False, True):
        stdout, stderr = StringIO(), StringIO()
        code = run_observe(
            Namespace(
                project=str(tmp_path / "project"),
                ref=TRACE_ID,
                since=None,
                watch=False,
                json=json_mode,
            ),
            stdout=stdout,
            stderr=stderr,
        )
        assert code == 0 and not stderr.getvalue()
        cli_streams.append(stdout.getvalue())

    distribution = tmp_path / "dist"
    subprocess.run(
        ["uv", "build", "--out-dir", str(distribution)],
        cwd=Path(__file__).parents[1],
        check=True,
        capture_output=True,
        text=True,
    )
    [wheel] = distribution.glob("*.whl")
    [sdist] = distribution.glob("*.tar.gz")
    with zipfile.ZipFile(wheel) as archive:
        wheel_bytes = b"".join(
            archive.read(name) for name in archive.namelist() if not name.endswith("/")
        )
    with tarfile.open(sdist, "r:gz") as archive:
        sdist_bytes = b"".join(
            member.read()
            for item in archive.getmembers()
            if item.isfile() and (member := archive.extractfile(item)) is not None
        )

    def retained_bytes(root: Path) -> bytes:
        return b"".join(
            candidate.read_bytes()
            for candidate in root.rglob("*")
            if candidate.is_file() and not candidate.is_symlink()
        )

    sinks = {
        "journal": retained_bytes(paths.journal),
        "sqlite": retained_bytes(paths.projections),
        "summary": retained_bytes(paths.summaries),
        "cli": "".join(cli_streams).encode(),
        "logs": "\n".join(record.getMessage() for record in caplog.records).encode(),
        "wheel": wheel_bytes,
        "sdist": sdist_bytes,
    }
    needles = [*(value.encode() for value in secret_values), unproven_error_type.encode()]
    for sink, retained in sinks.items():
        for needle in needles:
            assert needle not in retained, sink

    disk = b"".join(canonical_json_bytes(event) for event in events)
    for raw_identity in (b"call-2", b"req-1", b"session-1", b"turn-1", b"child-1"):
        assert raw_identity not in disk
    for forbidden_key in (
        b'"args":',
        b'"result":',
        b'"error_message":',
        b'"middleware_trace":',
        b'"user_task":',
        b'"prompt":',
        b'"response":',
        b'"goal":',
        b'"summary":',
        b'"tool_history":',
        b'"command":',
    ):
        assert forbidden_key not in disk


def test_post_only_kanban_create_success_keeps_terminal_gap_and_durable_binding(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """A missing pre hook cannot crash, invent a start, or lose a valid create result."""
    from aether_agents.observation.capture import hermes_plugin

    _, paths = _install_project(monkeypatch, tmp_path)
    monkeypatch.setenv("AETHER_PROJECT_ID", PROJECT_ID)
    monkeypatch.setattr(hermes_plugin._NativeReconciliationWorker, "start", lambda self: None)
    context = FakePluginContext()
    hermes_plugin.register(context)
    observer = context.unload_callbacks[-1].__self__
    task_ref = "t_cafebabe"
    error: Exception | None = None
    try:
        context.hooks["post_tool_call"][0](
            tool_name="kanban_create",
            tool_call_id="post-only-create-success",
            session_id="post-only-session",
            status="success",
            args={"idempotency_key": correlation_token(TRACE_ID, "post-only-root")},
            result={"ok": True, "task_id": task_ref, "project_id": PROJECT_ID},
        )
    except Exception as exc:  # pragma: no branch - assertion preserves callback health evidence
        error = exc
    assert error is None, (
        f"{type(error).__name__}: {error}; "
        f"callback_errors={observer._collector.stats.callback_errors}"
    )
    assert observer._collector.stats.callback_errors == 0
    for callback in reversed(context.unload_callbacks):
        callback()

    events = _journal_events(paths)
    terminal = next(event for event in events if event["event_type"] == "tool.completed")
    assert terminal["parent_event_id"] is None
    assert not any(event["event_type"] == "tool.started" for event in events)
    summary = reduce_events(
        ReductionInput(
            trace_id=TRACE_ID,
            project_id=PROJECT_ID,
            events=events,
            producer_count=1,
        )
    )
    assert "TOOL_TERMINAL_WITHOUT_START" in {
        gap["reason_code"] for gap in summary["coverage"]["gaps"]
    }
    assert hermes_plugin._retained_binding(paths, task_ref) == (TRACE_ID, "root")


def test_post_only_kanban_create_failure_keeps_terminal_gap_without_binding(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """A failed post-only create stays visible without authorizing its result task."""
    from aether_agents.observation.capture import hermes_plugin

    _, paths = _install_project(monkeypatch, tmp_path)
    monkeypatch.setenv("AETHER_PROJECT_ID", PROJECT_ID)
    monkeypatch.setattr(hermes_plugin._NativeReconciliationWorker, "start", lambda self: None)
    context = FakePluginContext()
    hermes_plugin.register(context)
    observer = context.unload_callbacks[-1].__self__
    assert observer._collector.ensure_trace_opened(
        TRACE_ID,
        source_kind="aether_checkpoint",
        source_hook="contract_persisted",
    )
    observer._activate_trace(observer._collector, TRACE_ID)
    task_ref = "t_baddecaf"
    error: Exception | None = None
    try:
        context.hooks["post_tool_call"][0](
            tool_name="kanban_create",
            tool_call_id="post-only-create-failure",
            session_id="post-only-session",
            status="failed",
            args={"idempotency_key": correlation_token(TRACE_ID, "failed-post-only-root")},
            result={"ok": False, "task_id": task_ref, "project_id": PROJECT_ID},
            error_type="TimeoutError",
        )
    except Exception as exc:  # pragma: no branch - assertion preserves callback health evidence
        error = exc
    assert error is None, (
        f"{type(error).__name__}: {error}; "
        f"callback_errors={observer._collector.stats.callback_errors}"
    )
    assert observer._collector.stats.callback_errors == 0
    for callback in reversed(context.unload_callbacks):
        callback()

    events = _journal_events(paths)
    terminal = next(event for event in events if event["event_type"] == "tool.failed")
    assert terminal["parent_event_id"] is None
    assert not any(event["event_type"] == "tool.started" for event in events)
    summary = reduce_events(
        ReductionInput(
            trace_id=TRACE_ID,
            project_id=PROJECT_ID,
            events=events,
            producer_count=1,
        )
    )
    assert "TOOL_TERMINAL_WITHOUT_START" in {
        gap["reason_code"] for gap in summary["coverage"]["gaps"]
    }
    assert hermes_plugin._retained_binding(paths, task_ref) is None


def test_native_callbacks_reject_unproven_identities_with_content_free_diagnostics(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Native callback identity columns are checked before event construction."""
    from aether_agents.observation.capture import hermes_plugin

    _, paths = _install_project(monkeypatch, tmp_path)
    monkeypatch.setenv("AETHER_PROJECT_ID", PROJECT_ID)
    monkeypatch.setattr(hermes_plugin._NativeReconciliationWorker, "start", lambda self: None)
    context = FakePluginContext()
    hermes_plugin.register(context)
    token = correlation_token(TRACE_ID, "root")
    context.hooks["pre_tool_call"][0](
        tool_name="kanban_create",
        tool_call_id="native-create",
        session_id="session-1",
        args={"idempotency_key": token},
    )
    context.hooks["post_tool_call"][0](
        tool_name="kanban_create",
        tool_call_id="native-create",
        session_id="session-1",
        status="success",
        args={"idempotency_key": token},
        result={"ok": True, "task_id": "t_deadbeef", "project_id": PROJECT_ID},
    )

    hostile_values = (
        b"PRIVATE_RUN_ERROR",
        b"PRIVATE_PARENT_ERROR",
        b"PROMPT LIKE RAW PROFILE",
        b"/etc/passwd",
        b"PRIVATE_SESSION_ERROR",
        b"PRIVATE_TURN_ERROR",
        b"PRIVATE_API_ERROR",
        b"PRIVATE_CALL_ERROR",
        b"raw command/output/error text",
        b"prompt-like raw response",
    )
    context.hooks["pre_tool_call"][0](
        tool_name="terminal",
        tool_call_id="PRIVATE_CALL_ERROR",
        session_id="PRIVATE_SESSION_ERROR",
        turn_id="PRIVATE_TURN_ERROR",
        api_request_id="PRIVATE_API_ERROR",
        task_id="t_deadbeef",
        args={"command": "raw command/output/error text"},
    )
    observer = context.unload_callbacks[-1].__self__
    pending_bytes = repr(observer._pending_spans).encode()
    assert all(value not in pending_bytes for value in hostile_values)
    context.hooks["post_tool_call"][0](
        tool_name="terminal",
        tool_call_id="PRIVATE_CALL_ERROR",
        session_id="PRIVATE_SESSION_ERROR",
        turn_id="PRIVATE_TURN_ERROR",
        api_request_id="PRIVATE_API_ERROR",
        task_id="t_deadbeef",
        status="failed",
        result="prompt-like raw response",
        error_message="raw command/output/error text",
        error_type="TimeoutError",
    )
    context.hooks["on_kanban_task_updated"][0](
        task_id="PRIVATE_RUN_ERROR",
        changed_fields=["status"],
        error="raw command/output/error text",
    )
    context.hooks["kanban_task_completed"][0](
        task_id="t_deadbeef",
        parent_task_ids=["PRIVATE_PARENT_ERROR"],
        run_id="PRIVATE_RUN_ERROR",
        session_id="/etc/passwd",
        profile="PROMPT LIKE RAW PROFILE",
        status="done",
        summary="prompt-like raw response",
        error="raw command/output/error text",
    )
    context.hooks["on_kanban_worker_exited"][0](
        task_id="t_deadbeef",
        parent_task_ids=["PRIVATE_PARENT_ERROR"],
        run_id="PRIVATE_RUN_ERROR",
        session_id="/etc/passwd",
        profile="PROMPT LIKE RAW PROFILE",
        outcome="failed",
        summary="prompt-like raw response",
        error="raw command/output/error text",
    )
    for callback in reversed(context.unload_callbacks):
        callback()

    events = _journal_events(paths)
    for event in events:
        validate_event(event)
        assert_clean(event)
    forbidden_bytes = hostile_values + tuple(
        hashlib.sha256(value).hexdigest().encode() for value in hostile_values
    )
    retained = b"".join(path.read_bytes() for path in paths.project.rglob("*") if path.is_file())
    assert all(value not in retained for value in forbidden_bytes)

    reasons = {
        event["coverage"]["reason_code"]
        for event in events
        if event["event_type"] == "coverage.gap"
    }
    assert {
        "NATIVE_KANBAN_TASK_ID_REJECTED",
        "NATIVE_KANBAN_PARENT_ID_REJECTED",
        "NATIVE_KANBAN_RUN_ID_REJECTED",
        "NATIVE_HERMES_SESSION_ID_REJECTED",
        "NATIVE_HERMES_PROFILE_ID_REJECTED",
    } <= reasons
    tool = next(
        event
        for event in events
        if event["event_type"] == "tool.started" and event["tool"]["name"] == "terminal"
    )
    pseudonym_pattern = re.compile(r"^(?:sid|trn|api|call)_fpk_[a-f0-9]{32}_[a-f0-9]{64}$")
    assert pseudonym_pattern.fullmatch(tool["session_id"])
    assert pseudonym_pattern.fullmatch(tool["turn_id"])
    assert pseudonym_pattern.fullmatch(tool["api_request_id"])
    assert pseudonym_pattern.fullmatch(tool["tool"]["call_id"])


def test_partial_hook_registration_becomes_trace_coverage_and_health(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    from aether_agents.observation.capture import hermes_plugin

    class PartialContext(FakePluginContext):
        def register_hook(self, name, callback):
            if name == "pre_api_request":
                raise RuntimeError("synthetic unavailable hook")
            super().register_hook(name, callback)

    _, paths = _install_project(monkeypatch, tmp_path)
    monkeypatch.setenv("AETHER_PROJECT_ID", PROJECT_ID)
    monkeypatch.setattr(hermes_plugin._NativeReconciliationWorker, "start", lambda self: None)
    ctx = PartialContext()
    hermes_plugin.register(ctx)
    token = correlation_token(TRACE_ID, "root-unit")
    ctx.hooks["pre_tool_call"][0](
        tool_name="kanban_create",
        tool_call_id="partial-create",
        session_id="session-1",
        args={"idempotency_key": token},
    )
    ctx.hooks["post_tool_call"][0](
        tool_name="kanban_create",
        tool_call_id="partial-create",
        session_id="session-1",
        status="success",
        args={"idempotency_key": token},
        result={"ok": True, "task_id": "t_bbbbbbbb", "project_id": PROJECT_ID},
    )
    for callback in reversed(ctx.unload_callbacks):
        callback()

    events = _journal_events(paths)
    assert "HOOK_REGISTRATION_PARTIAL" in {
        (event.get("coverage") or {}).get("reason_code") for event in events
    }
    assert "HOOK_MISSING_PRE_API_REQUEST" in {
        (event.get("coverage") or {}).get("reason_code") for event in events
    }
    summary = reduce_events(
        ReductionInput(
            trace_id=TRACE_ID,
            project_id=PROJECT_ID,
            events=events,
            producer_count=1,
        )
    )
    assert summary["capability_evidence"]["missing_hook_refs"] == ["pre_api_request"]
    health = json.loads(paths.health_counters.read_text(encoding="utf-8"))
    assert health["HOOK_REGISTRATION_FAILED"] == 1


@pytest.mark.parametrize(
    "native_outcome",
    [
        "completed",
        "blocked",
        "failed",
        "crashed",
        "timed_out",
        "spawn_failed",
        "gave_up",
        "reclaimed",
        "rate_limited",
        "stale",
        "review_requested",
        "changes_requested",
        "scheduled",
    ],
)
def test_worker_exit_hook_preserves_each_native_run_outcome(
    native_outcome: str,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    from aether_agents.observation.capture import hermes_plugin

    _, paths = _install_project(monkeypatch, tmp_path)
    monkeypatch.setenv("AETHER_PROJECT_ID", PROJECT_ID)
    monkeypatch.setattr(hermes_plugin._NativeReconciliationWorker, "start", lambda self: None)
    context = FakePluginContext()
    hermes_plugin.register(context)
    token = correlation_token(TRACE_ID, "root")
    context.hooks["pre_tool_call"][0](
        tool_name="kanban_create",
        tool_call_id="create",
        session_id="session-1",
        args={"idempotency_key": token},
    )
    context.hooks["post_tool_call"][0](
        tool_name="kanban_create",
        tool_call_id="create",
        session_id="session-1",
        status="success",
        args={"idempotency_key": token},
        result={"ok": True, "task_id": "t_cccccccc", "project_id": PROJECT_ID},
    )
    context.hooks["on_kanban_worker_exited"][0](
        task_id="t_cccccccc",
        run_id=1,
        profile="implementer",
        outcome=native_outcome,
    )
    for callback in reversed(context.unload_callbacks):
        callback()

    terminal = next(
        event for event in _journal_events(paths) if event["event_type"] == "run.finished"
    )
    assert terminal["work_unit"]["run_outcome"] == native_outcome


def _create_native_databases(root: Path) -> tuple[Path, Path]:
    board = root / "kanban.db"
    state_home = root / "hermes" / "profiles" / "morfeo"
    state_home.mkdir(parents=True)
    with sqlite3.connect(board) as connection:
        connection.executescript(
            """
            CREATE TABLE tasks (
                id TEXT PRIMARY KEY, assignee TEXT, status TEXT, created_at INTEGER,
                started_at INTEGER, completed_at INTEGER, project_id TEXT,
                idempotency_key TEXT, max_runtime_seconds INTEGER,
                last_heartbeat_at INTEGER, current_run_id INTEGER, session_id TEXT,
                block_kind TEXT
            );
            CREATE TABLE task_links (parent_id TEXT, child_id TEXT);
            CREATE TABLE task_runs (
                id INTEGER PRIMARY KEY, task_id TEXT, profile TEXT, status TEXT,
                max_runtime_seconds INTEGER, last_heartbeat_at INTEGER,
                started_at INTEGER, ended_at INTEGER, outcome TEXT,
                summary TEXT, metadata TEXT, error TEXT
            );
            CREATE TABLE task_events (
                id INTEGER PRIMARY KEY, task_id TEXT, run_id INTEGER,
                kind TEXT, payload TEXT, created_at INTEGER
            );
            """
        )
        connection.executemany(
            "INSERT INTO tasks VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            [
                (
                    "t_11111111",
                    "supervisor",
                    "done",
                    1_700_000_010,
                    1_700_000_011,
                    1_700_000_040,
                    PROJECT_ID,
                    correlation_token(TRACE_ID, "native-root"),
                    300,
                    1_700_000_039,
                    None,
                    "session-native",
                    None,
                ),
                (
                    "t_22222222",
                    "implementer",
                    "done",
                    1_700_000_012,
                    1_700_000_013,
                    1_700_000_038,
                    PROJECT_ID,
                    "ordinary-private-key",
                    300,
                    1_700_000_037,
                    2,
                    "session-child",
                    None,
                ),
                (
                    "t_33333333",
                    "other",
                    "done",
                    1_700_000_010,
                    None,
                    1_700_000_020,
                    "22222222-2222-4222-8222-222222222222",
                    correlation_token(TRACE_ID, "wrong-project"),
                    300,
                    None,
                    None,
                    None,
                    None,
                ),
            ],
        )
        connection.execute("INSERT INTO task_links VALUES ('t_11111111', 't_22222222')")
        connection.executemany(
            "INSERT INTO task_runs VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            [
                (
                    1,
                    "t_22222222",
                    "implementer",
                    "timed_out",
                    300,
                    1_700_000_020,
                    1_700_000_013,
                    1_700_000_021,
                    "timed_out",
                    "PRIVATE_RUN_SUMMARY",
                    "PRIVATE_RUN_METADATA",
                    "PRIVATE_RUN_ERROR",
                ),
                (
                    2,
                    "t_22222222",
                    "implementer",
                    "done",
                    300,
                    1_700_000_037,
                    1_700_000_022,
                    1_700_000_038,
                    "completed",
                    "PRIVATE_RUN_SUMMARY_2",
                    "PRIVATE_RUN_METADATA_2",
                    "PRIVATE_RUN_ERROR_2",
                ),
            ],
        )

    state = state_home / "state.db"
    with sqlite3.connect(state) as connection:
        connection.executescript(
            """
            CREATE TABLE sessions (
                id TEXT PRIMARY KEY, parent_session_id TEXT, profile_name TEXT,
                started_at REAL, ended_at REAL, message_count INTEGER,
                tool_call_count INTEGER, input_tokens INTEGER, output_tokens INTEGER,
                cache_read_tokens INTEGER, cache_write_tokens INTEGER,
                reasoning_tokens INTEGER, last_activity_at REAL,
                last_activity_provenance TEXT,
                system_prompt TEXT, origin_json TEXT, display_name TEXT, handoff_error TEXT
            );
            CREATE TABLE messages (
                id INTEGER PRIMARY KEY, session_id TEXT, role TEXT, timestamp REAL,
                active INTEGER, content TEXT, tool_calls TEXT, reasoning TEXT,
                api_content TEXT, display_metadata TEXT
            );
            """
        )
        connection.execute(
            "INSERT INTO sessions VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                "session-native",
                None,
                "morfeo",
                1_700_000_000.0,
                None,
                1,
                0,
                0,
                0,
                0,
                0,
                0,
                1_700_000_009.0,
                "native",
                "PRIVATE_SYSTEM_PROMPT",
                "PRIVATE_ORIGIN",
                "PRIVATE_DISPLAY",
                "PRIVATE_HANDOFF",
            ),
        )
        connection.execute(
            "INSERT INTO sessions VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                "session-child",
                "session-native",
                "implementer",
                1_700_000_012.0,
                1_700_000_038.0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                1_700_000_038.0,
                "native",
                "PRIVATE_CHILD_SYSTEM_PROMPT",
                "PRIVATE_CHILD_ORIGIN",
                "PRIVATE_CHILD_DISPLAY",
                "PRIVATE_CHILD_HANDOFF",
            ),
        )
        connection.execute(
            "INSERT INTO messages VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                7,
                "session-native",
                "user",
                1_700_000_009.0,
                1,
                "PRIVATE_MESSAGE_CONTENT",
                "PRIVATE_TOOL_JSON",
                "PRIVATE_REASONING",
                "PRIVATE_API_CONTENT",
                "PRIVATE_DISPLAY_METADATA",
            ),
        )
    state.chmod(0o600)
    return board, state_home


def _make_session_db_unsafe(state_home: Path, root: Path, link_kind: str) -> Path:
    """Replace one valid SessionDB path with an unsafe native-store topology."""
    state = state_home / "state.db"
    outside = root / "outside-sessiondb"
    outside.mkdir()
    if link_kind == "symlink":
        external = outside / "state.db"
        state.rename(external)
        state.symlink_to(external)
        return external
    if link_kind == "hardlink":
        external = outside / "state.db"
        external.hardlink_to(state)
        return external
    if link_kind == "fifo":
        state.unlink()
        os.mkfifo(state)
        return state
    if link_kind == "ancestor":
        external_home = outside / "morfeo"
        state_home.rename(external_home)
        state_home.symlink_to(external_home, target_is_directory=True)
        return external_home / "state.db"
    raise AssertionError(f"unhandled link kind: {link_kind}")


@pytest.mark.skipif(os.name != "posix", reason="POSIX no-follow and inode contract")
@pytest.mark.parametrize("link_kind", ["symlink", "hardlink", "fifo", "ancestor"])
def test_native_session_reconciliation_rejects_aliased_or_non_regular_database(
    link_kind: str,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Untrusted SessionDB topology cannot manufacture verified product context."""
    from aether_agents.observation.capture import hermes_plugin

    _, paths = _install_project(monkeypatch, tmp_path)
    board, state_home = _create_native_databases(tmp_path)
    external = _make_session_db_unsafe(state_home, tmp_path, link_kind)
    external_bytes = external.read_bytes() if external.is_file() else None
    monkeypatch.setenv("AETHER_PROJECT_ID", PROJECT_ID)
    monkeypatch.setenv("HERMES_KANBAN_DB", str(board))
    monkeypatch.setenv("HERMES_HOME", str(state_home))
    monkeypatch.setattr(hermes_plugin._NativeReconciliationWorker, "start", lambda self: None)
    monkeypatch.setattr(
        hermes_plugin,
        "_resolve_category_normalizer",
        lambda: (lambda _name: "unknown", None, False),
    )

    verified, available = hermes_plugin._verified_native_session_ids({"session-native"})
    assert verified == frozenset()
    assert available is False

    observer = hermes_plugin._Observer(FakePluginContext())
    assert observer._collector is not None
    observer._reconcile_native()
    health = observer._collector.health.read()
    observer.unload()

    events = _journal_events(paths)
    opened = next(event for event in events if event["event_type"] == "trace.opened")
    assert opened["contract"]["origin_message_id"] is None
    assert opened["contract"].get("session_lineage", []) == []
    assert all(
        event.get("work_unit") is None or event["work_unit"].get("session_id") is None
        for event in events
    )
    assert health.get("NATIVE_HERMES_SESSION_PROVENANCE_UNAVAILABLE") == 2
    summary = query.load_summary(paths, TRACE_ID)
    assert any(
        gap["reason_code"] == "NATIVE_HERMES_SESSION_PROVENANCE_UNAVAILABLE"
        for gap in summary["coverage"]["gaps"]
    )
    if external_bytes is not None:
        assert external.read_bytes() == external_bytes


@pytest.mark.skipif(os.name != "posix", reason="POSIX no-follow and inode contract")
def test_native_session_reconciliation_discards_rows_after_database_name_swap(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """A valid replacement inode cannot govern after the secure descriptor opens."""
    from aether_agents.observation.capture import hermes_plugin

    _, state_home = _create_native_databases(tmp_path)
    state = state_home / "state.db"
    replacement = tmp_path / "replacement-state.db"
    replacement.write_bytes(state.read_bytes())
    replacement.chmod(0o600)
    displaced = tmp_path / "displaced-state.db"
    monkeypatch.setenv("HERMES_HOME", str(state_home))
    real_connect = sqlite3.connect
    swapped = False

    def swap_then_connect(database: object, *args: object, **kwargs: object) -> sqlite3.Connection:
        nonlocal swapped
        if not swapped:
            state.rename(displaced)
            replacement.rename(state)
            swapped = True
        return real_connect(database, *args, **kwargs)

    monkeypatch.setattr(hermes_plugin.sqlite3, "connect", swap_then_connect)

    verified, available = hermes_plugin._verified_native_session_ids({"session-native"})

    assert swapped is True
    assert verified == frozenset()
    assert available is False


def test_out_of_band_native_reconciliation_is_allowlisted_causal_and_retry_preserving(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    from aether_agents.observation.capture import hermes_plugin

    _, paths = _install_project(monkeypatch, tmp_path)
    board, state_home = _create_native_databases(tmp_path)
    monkeypatch.setenv("AETHER_PROJECT_ID", PROJECT_ID)
    monkeypatch.setenv("HERMES_KANBAN_DB", str(board))
    monkeypatch.setenv("HERMES_HOME", str(state_home))
    monkeypatch.setattr(hermes_plugin._NativeReconciliationWorker, "start", lambda self: None)

    observer = hermes_plugin._Observer(FakePluginContext())
    observer._reconcile_native()
    observer.unload()
    events = _journal_events(paths)
    for event in events:
        validate_event(event)
        assert_clean(event)

    opened = next(event for event in events if event["event_type"] == "trace.opened")
    assert opened["contract"]["origin_message_id"] == 7
    bindings = {
        event["work_unit"]["task_ref"]: event["work_unit"]["relation"]
        for event in events
        if event["event_type"] == "work_unit.bound"
    }
    assert bindings == {"t_11111111": "root", "t_22222222": "unknown"}
    assert {
        event["work_unit"]["required"] for event in events if event.get("work_unit") is not None
    } == {None}
    run_outcomes = {
        event["work_unit"]["run_outcome"]
        for event in events
        if event["event_type"] == "run.finished"
    }
    assert run_outcomes == {"timed_out", "completed"}
    assert all(event["source_kind"] == "native_reconciliation" for event in events)

    disk = b"".join(canonical_json_bytes(event) for event in events)
    for forbidden in (
        b"ordinary-private-key",
        b"PRIVATE_RUN_SUMMARY",
        b"PRIVATE_RUN_METADATA",
        b"PRIVATE_RUN_ERROR",
        b"PRIVATE_SYSTEM_PROMPT",
        b"PRIVATE_ORIGIN",
        b"PRIVATE_MESSAGE_CONTENT",
        b"PRIVATE_TOOL_JSON",
        b"PRIVATE_REASONING",
        b"PRIVATE_API_CONTENT",
        b"PRIVATE_DISPLAY_METADATA",
    ):
        assert forbidden not in disk


def test_native_reconciliation_maps_exact_hermes_project_path_to_aether_uuid(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    from hermes_cli import projects_db

    from aether_agents.observation.capture import hermes_plugin

    project, paths = _install_project(monkeypatch, tmp_path)
    board, state_home = _create_native_databases(tmp_path)
    with projects_db.connect_closing(state_home / "projects.db") as connection:
        projects_db.create_project(
            connection,
            name="Stale",
            slug="stale",
            primary_path=str(tmp_path / "missing-project"),
        )
        runtime_project_id = projects_db.create_project(
            connection,
            name="Fixture",
            slug="fixture",
            primary_path=str(project),
        )
    with sqlite3.connect(board) as connection:
        connection.execute(
            "UPDATE tasks SET project_id=? WHERE id IN ('t_11111111','t_22222222')",
            (runtime_project_id,),
        )
    monkeypatch.setenv("AETHER_PROJECT_ID", PROJECT_ID)
    monkeypatch.setenv("HERMES_KANBAN_DB", str(board))
    monkeypatch.setenv("HERMES_HOME", str(state_home))
    monkeypatch.setattr(hermes_plugin._NativeReconciliationWorker, "start", lambda self: None)

    first = hermes_plugin._Observer(FakePluginContext())
    assert first._collector is not None
    assert first._collector.ensure_trace_opened(
        TRACE_ID,
        contract_id="oc_1234567890abcdef",
        source_kind="hermes_hook",
        source_hook="post_tool_call",
    )
    first.unload()

    observer = hermes_plugin._Observer(FakePluginContext())
    assert observer._collector is not None
    observer._reconcile_native()
    health = observer._collector.health.read()
    observer.unload()
    events = _journal_events(paths)
    bindings = {
        event["work_unit"]["task_ref"]
        for event in events
        if event["event_type"] == "work_unit.bound"
    }
    assert {"t_11111111", "t_22222222"} <= bindings
    assert all(event["project_id"] == PROJECT_ID for event in events)
    assert "EVENT_IDENTITY_COLLISION" not in health


def test_native_reconciliation_rejects_content_shaped_identities_before_aether_persistence(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """A complete hostile Kanban row never becomes an observation identifier.

    The values below occupy native identity columns, not a synthetic payload dict.
    They deliberately use shapes that the generic opaque-reference grammar accepts,
    while the locked Hermes producers cannot generate them.
    """
    from aether_agents.observation.capture import hermes_plugin

    _, paths = _install_project(monkeypatch, tmp_path)
    board, state_home = _create_native_databases(tmp_path)
    with sqlite3.connect(board) as connection:
        connection.execute(
            "INSERT INTO tasks VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                "PRIVATE_RUN_ERROR",
                "PROMPT_LIKE_RAW_ERROR",
                "done",
                1_700_000_050,
                1_700_000_051,
                1_700_000_052,
                PROJECT_ID,
                correlation_token(TRACE_ID, "malicious-native-row"),
                300,
                1_700_000_052,
                3,
                "/etc/passwd",
                None,
            ),
        )
        connection.execute(
            "INSERT INTO task_links VALUES (?, ?)",
            ("t_11111111", "PRIVATE_RUN_ERROR"),
        )
        connection.execute(
            "INSERT INTO task_runs VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                3,
                "PRIVATE_RUN_ERROR",
                "RAW_ERROR_PROFILE",
                "done",
                300,
                1_700_000_052,
                1_700_000_051,
                1_700_000_052,
                "completed",
                "raw command/output/error text",
                "prompt-like raw response",
                "/etc/passwd",
            ),
        )

    monkeypatch.setenv("AETHER_PROJECT_ID", PROJECT_ID)
    monkeypatch.setenv("HERMES_KANBAN_DB", str(board))
    monkeypatch.setenv("HERMES_HOME", str(state_home))
    monkeypatch.setattr(hermes_plugin._NativeReconciliationWorker, "start", lambda self: None)

    observer = hermes_plugin._Observer(FakePluginContext())
    assert observer._collector is not None
    assert observer._collector.ensure_trace_opened(
        TRACE_ID,
        source_kind="aether_checkpoint",
        source_hook="contract_persisted",
    )
    observer._reconcile_native()
    health = observer._collector.health.read()
    observer.unload()

    events = _journal_events(paths)
    for event in events:
        validate_event(event)
        assert_clean(event)
    journal_bytes = b"".join(canonical_json_bytes(event) for event in events)
    hostile_values = (
        b"PRIVATE_RUN_ERROR",
        b"PROMPT_LIKE_RAW_ERROR",
        b"RAW_ERROR_PROFILE",
        b"/etc/passwd",
        b"raw command/output/error text",
        b"prompt-like raw response",
    )
    hostile_digests = tuple(hashlib.sha256(value).hexdigest().encode() for value in hostile_values)
    forbidden_bytes = hostile_values + hostile_digests
    assert all(value not in journal_bytes for value in forbidden_bytes)

    summary = query.load_summary(paths, TRACE_ID)
    validate_summary(summary)
    assert_clean(summary)
    summary_bytes = canonical_json_bytes(summary)
    assert all(value not in summary_bytes for value in forbidden_bytes)
    aether_bytes = b"".join(
        path.read_bytes() for path in paths.project.rglob("*") if path.is_file()
    )
    assert all(value not in aether_bytes for value in forbidden_bytes)
    assert health.get("NATIVE_KANBAN_TASK_ID_REJECTED") == 1
    assert any(
        gap["reason_code"] == "NATIVE_KANBAN_TASK_ID_REJECTED"
        for gap in summary["coverage"]["gaps"]
    )


def test_native_protocol_violation_marker_is_preserved_without_event_payload(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    from aether_agents.observation.capture import hermes_plugin

    _, paths = _install_project(monkeypatch, tmp_path)
    board, state_home = _create_native_databases(tmp_path)
    with sqlite3.connect(board) as connection:
        connection.execute(
            "INSERT INTO task_events VALUES (?, ?, ?, ?, ?, ?)",
            (
                1,
                "t_22222222",
                1,
                "protocol_violation",
                "PRIVATE_PROTOCOL_EVENT_PAYLOAD",
                1_700_000_021,
            ),
        )
    monkeypatch.setenv("AETHER_PROJECT_ID", PROJECT_ID)
    monkeypatch.setenv("HERMES_KANBAN_DB", str(board))
    monkeypatch.setenv("HERMES_HOME", str(state_home))
    monkeypatch.setattr(hermes_plugin._NativeReconciliationWorker, "start", lambda self: None)

    observer = hermes_plugin._Observer(FakePluginContext())
    observer._reconcile_native()
    observer.unload()
    events = _journal_events(paths)
    violation = next(
        event for event in events if event["event_type"] == "run.finished" and event["run_id"] == 1
    )
    assert violation["work_unit"]["run_outcome"] == "protocol_violation"
    assert b"PRIVATE_PROTOCOL_EVENT_PAYLOAD" not in b"".join(
        canonical_json_bytes(event) for event in events
    )


@pytest.mark.parametrize("outcome", ["failed", "protocol_violation"])
def test_native_terminal_never_turns_explicit_non_success_into_done(outcome: str) -> None:
    from aether_agents.observation.capture import hermes_plugin

    status, run_status, run_outcome = hermes_plugin._Observer._native_run_terminal(
        {"status": "done", "outcome": outcome}
    )

    assert status == "failed"
    assert run_status == "done"
    assert run_outcome == outcome


def test_retained_binding_refuses_cross_producer_wall_clock_order(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    from aether_agents.observation.capture import hermes_plugin

    _, paths = _install_project(monkeypatch, tmp_path)
    fixture = EventFactory()
    unbound = fixture.unit(
        "work_unit.unbound",
        "reported",
        1,
        task_ref="root",
        relation="unknown",
        required=False,
        task_status="ready",
    )
    bound = fixture.unit(
        "work_unit.bound",
        "reported",
        100,
        task_ref="root",
        relation="root",
        required=True,
        task_status="running",
    )
    unbound["producer_epoch"], unbound["producer_seq"] = "prd_" + "1" * 32, 0
    bound["producer_epoch"], bound["producer_seq"] = "prd_" + "2" * 32, 0

    for event in (unbound, bound):
        writer = JournalWriter(paths=paths, producer_epoch=event["producer_epoch"])
        writer.open()
        try:
            assert writer.append(event).accepted
        finally:
            writer.close()

    assert hermes_plugin._retained_binding(paths, "root") is None
    assert "root" not in hermes_plugin._retained_bindings(paths)


def test_invalid_retained_line_cannot_bootstrap_trace_or_task_authority(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    from aether_agents.observation.capture import hermes_plugin
    from aether_agents.observation.reduce.ingest import ingest_pending

    _, paths = _install_project(monkeypatch, tmp_path)
    paths.ensure()
    task_ref = "t_1234abcd"
    epoch = "prd_" + "9" * 32
    invalid = {
        "event_id": "not-an-event-id",
        "event_type": "work_unit.bound",
        "project_id": PROJECT_ID,
        "trace_id": TRACE_ID,
        "producer_epoch": epoch,
        "producer_seq": 0,
        "source_kind": "native_reconciliation",
        "source_hook": "kanban_read",
        "work_unit": {
            "task_ref": task_ref,
            "relation": "root",
            "required": True,
        },
    }
    retained = paths.closed / f"{epoch}.0-0.jsonl"
    retained.write_bytes(canonical_json_bytes(invalid) + b"\n")

    assert hermes_plugin._retained_binding(paths, task_ref) is None
    assert task_ref not in hermes_plugin._retained_bindings(paths)
    assert not hermes_plugin._retained_trace_exists(paths, TRACE_ID)

    monkeypatch.setenv("AETHER_PROJECT_ID", PROJECT_ID)
    monkeypatch.setenv("AETHER_OBSERVATION_TRACE_ID", TRACE_ID)
    monkeypatch.setenv("HERMES_KANBAN_TASK", task_ref)
    monkeypatch.setattr(hermes_plugin._NativeReconciliationWorker, "start", lambda self: None)
    observer = hermes_plugin._Observer(FakePluginContext())
    try:
        assert observer._active_trace is None
        assert observer._collector is not None
        assert observer._collector.binder.trace_for(task_ref) is None
    finally:
        observer.unload()

    report = ingest_pending(paths)
    assert report.events_inserted == 0
    assert report.corrupt_segments == 1


def test_import_boundary_is_static_and_manager_modules_import_without_hermes() -> None:
    package = Path(__file__).parents[1] / "src" / "aether_agents"
    hermes_importers: list[str] = []
    forbidden_plugin_imports: list[str] = []
    forbidden_roots = {
        "aether_agents.commands",
        "aether_agents.transitions",
        "aether_agents.release",
        "aether_agents.service",
        "aether_agents.auth",
    }
    for path in package.rglob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            names: list[str] = []
            if isinstance(node, ast.Import):
                names = [alias.name for alias in node.names]
            elif isinstance(node, ast.ImportFrom) and node.module:
                names = [node.module]
            for name in names:
                if name == "hermes_cli" or name.startswith("hermes_cli.") or name == "hermes_state":
                    hermes_importers.append(path.relative_to(package).as_posix())
                if path.name == "hermes_plugin.py" and any(
                    name == root or name.startswith(root + ".") for root in forbidden_roots
                ):
                    forbidden_plugin_imports.append(name)
    assert set(hermes_importers) <= {"observation/capture/hermes_plugin.py"}
    assert forbidden_plugin_imports == []

    # These imports must remain independent of an installed/running Hermes runtime.
    import aether_agents.cli  # noqa: F401
    import aether_agents.commands.observe  # noqa: F401
    import aether_agents.observation.query  # noqa: F401
    import aether_agents.observation.report  # noqa: F401
