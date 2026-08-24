"""Executable performance and resilience gates for Contract Observation.

The committed baseline records the complete 10k/100k scaling run and the exact
release-machine description.  These tests keep the pass/fail budgets executable
without making every ordinary suite allocate the 100k-event evidence fixture.
"""

from __future__ import annotations

import json
import math
from copy import deepcopy
from pathlib import Path
from time import perf_counter, perf_counter_ns
from typing import Any

from observation_helpers import PROJECT_ID, TRACE_ID, EventFactory

from aether_agents.observation.capture import hermes_plugin
from aether_agents.observation.context import ProjectRegistry
from aether_agents.observation.identity import correlation_token
from aether_agents.observation.reduce.reducer import ReductionInput, reduce_events

BASELINE = Path(__file__).parent / "fixtures" / "observation" / "performance-baseline.json"


class _PluginContext:
    """The public PluginContext surface used by Hermes's in-process callbacks."""

    profile_name = "morfeo"

    def __init__(self) -> None:
        self.hooks: dict[str, list[Any]] = {}
        self.unload_callbacks: list[Any] = []

    def register_hook(self, name: str, callback: Any) -> None:
        self.hooks.setdefault(name, []).append(callback)

    def on_unload(self, callback: Any) -> None:
        self.unload_callbacks.append(callback)


def _stress_events(count: int) -> list[dict[str, Any]]:
    """A retained, schema-shaped state stream with no artificial process-step growth."""
    factory = EventFactory()
    opened = factory.opened()
    state = factory.unit(
        "work_unit.status",
        "started",
        1,
        task_ref="root",
        relation="root",
        task_status="running",
    )
    events = [opened]
    for sequence in range(1, count):
        event = deepcopy(state)
        event["event_id"] = f"evt_{sequence + 1:032x}"
        event["producer_seq"] = sequence
        event["monotonic_ns"] = sequence + 1
        observed_at = factory.at(sequence / 1000).strftime("%Y-%m-%dT%H:%M:%S.%fZ")
        event["occurred_at"] = observed_at
        event["recorded_at"] = observed_at
        events.append(event)
    return events


def _percentile(samples: list[float], fraction: float) -> float:
    ordered = sorted(samples)
    return ordered[math.ceil(fraction * len(ordered)) - 1]


def test_ten_thousand_event_reduction_stays_inside_two_second_budget() -> None:
    events = _stress_events(10_000)
    started = perf_counter()
    summary = reduce_events(
        ReductionInput(
            trace_id=TRACE_ID,
            project_id=PROJECT_ID,
            events=events,
            producer_count=1,
        )
    )
    elapsed = perf_counter() - started
    assert summary["source_event_count"] == 10_000
    assert elapsed <= 2.0, f"10k reduction took {elapsed:.6f}s"


def test_native_plugin_callback_latency_includes_projection_validation_and_append(
    monkeypatch, tmp_path
) -> None:
    state = tmp_path / "state"
    project = tmp_path / "project"
    marker = project / ".aether" / "project.toml"
    marker.parent.mkdir(parents=True)
    marker.write_text(f'project_id = "{PROJECT_ID}"\n', encoding="utf-8")
    monkeypatch.setenv("XDG_STATE_HOME", str(state))
    monkeypatch.setenv("AETHER_PROJECT_ID", PROJECT_ID)
    monkeypatch.setenv("HERMES_HOME", str(tmp_path / "hermes" / "profiles" / "morfeo"))
    assert ProjectRegistry().register(PROJECT_ID, project, "performance-fixture")

    # Native-store reads belong to the separate reconciliation worker. Holding that
    # worker idle isolates exactly the synchronous callback budget under test.
    monkeypatch.setattr(hermes_plugin._NativeReconciliationWorker, "start", lambda self: None)
    context = _PluginContext()
    hermes_plugin.register(context)
    token = correlation_token(TRACE_ID, "root")
    context.hooks["pre_tool_call"][0](
        tool_name="kanban_create",
        tool_call_id="create",
        session_id="performance-session",
        args={"idempotency_key": token},
    )
    context.hooks["post_tool_call"][0](
        tool_name="kanban_create",
        tool_call_id="create",
        session_id="performance-session",
        status="success",
        args={"idempotency_key": token},
        result={"ok": True, "task_id": "t_aaaaaaaa", "project_id": PROJECT_ID},
    )

    samples: list[float] = []
    for index in range(500):
        payload = {
            "tool_name": "terminal",
            "tool_call_id": f"call-{index}",
            "session_id": "performance-session",
            "task_id": "t_aaaaaaaa",
        }
        started = perf_counter_ns()
        context.hooks["pre_tool_call"][0](**payload)
        samples.append((perf_counter_ns() - started) / 1_000_000)
        started = perf_counter_ns()
        context.hooks["post_tool_call"][0](**payload, status="success", duration_ms=1)
        samples.append((perf_counter_ns() - started) / 1_000_000)

    measured = samples[40:]  # exclude cache/filesystem warm-up, never slow outliers
    api_samples: list[float] = []
    for index in range(100):
        payload = {
            "api_request_id": f"request-{index}",
            "session_id": "performance-session",
            "turn_id": f"turn-{index}",
            "task_id": "t_aaaaaaaa",
            "model": "model-1",
            "provider": "provider-1",
            "system_prompt": "synthetic benchmark prompt",
            "message_count": 2,
            "tool_count": 3,
        }
        started = perf_counter_ns()
        context.hooks["pre_api_request"][0](**payload)
        api_samples.append((perf_counter_ns() - started) / 1_000_000)
        started = perf_counter_ns()
        context.hooks["post_api_request"][0](
            **payload,
            status="completed",
            usage={"input_tokens": 2, "output_tokens": 3, "total_tokens": 5},
        )
        api_samples.append((perf_counter_ns() - started) / 1_000_000)
    try:
        assert _percentile(measured, 0.95) <= 5.0
        assert _percentile(measured, 0.99) <= 20.0
        assert _percentile(api_samples[20:], 0.95) <= 5.0
        assert _percentile(api_samples[20:], 0.99) <= 20.0
    finally:
        for callback in reversed(context.unload_callbacks):
            callback()


def test_recorded_clean_checkout_scaling_evidence_is_complete() -> None:
    evidence = json.loads(BASELINE.read_text(encoding="utf-8"))
    assert evidence["schema_version"] == 1
    assert evidence["contract"]["hermes"] == {
        "repository": "https://github.com/NousResearch/hermes-agent.git",
        "distribution": "hermes-agent",
        "version": "0.20.4",
        "commit": "e624e9fde561e1add9388384012b295fde669ade",
        "tag": "v2026.8.18",
        "tag_object": "9f13bbbf8423427e159c78066356ca0e27ca6b74",
    }
    callback = evidence["callback"]
    assert callback["sample_count"] == 2_000
    assert callback["plugin_callback_count"] == 22
    assert callback["unload_hook_count"] == 0
    assert callback["raw_prompt_absent"] is True
    assert callback["raw_response_absent"] is True
    assert callback["surfaces"]["tool"]["sample_count"] == 1_000
    assert callback["surfaces"]["api"]["sample_count"] == 1_000
    assert callback["p95_ms"] <= 5.0
    assert callback["p99_ms"] <= 20.0
    assert evidence["reduction"]["mode"] == "full_reduction"
    assert evidence["reduction"]["ten_thousand"]["seconds"] <= 2.0
    assert evidence["reduction"]["one_hundred_thousand"]["event_count"] == 100_000
    flush = evidence["flush"]
    assert flush["sample_count"] == flush["successful_flushes"] == 20
    assert flush["execution_path"] == "supervised_out_of_band"
    assert flush["synchronous_callback_fsync"] is False
    incremental = evidence["incremental_pipeline"]
    assert incremental["mode"] == "incremental_journal_sqlite_projection"
    assert incremental["normative_counts_complete"] is True
    assert incremental["event_counts"] == [10_000, 100_000]
    for label, count in (("ten_thousand", 10_000), ("one_hundred_thousand", 100_000)):
        assert incremental[label]["event_count"] == count
        assert incremental[label]["source_event_count"] == count
