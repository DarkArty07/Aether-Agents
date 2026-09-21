"""Tests for passive observer startup, asynchronous retained bindings, and snapshot indexing.

Satisfies:
(a) Registration and hot hooks complete while historical reader is deliberately held on a barrier;
(b) An unchanged retained snapshot is validated once per snapshot, demonstrated by instrumentation;
(c) Appended, replaced, truncated, conflicting and quarantined segments preserve canonical
    binding/privacy invariants and full-versus-incremental semantic equivalence.
"""

from __future__ import annotations

import secrets
import threading
from copy import deepcopy
from pathlib import Path
from time import perf_counter
from types import SimpleNamespace
from typing import Any

import pytest
from observation_helpers import (
    EPOCH,
    PROJECT_ID,
    TRACE_ID,
    EventFactory,
    project_marker,
)

from aether_agents.observation.capture import hermes_plugin
from aether_agents.observation.capture.collector import Collector
from aether_agents.observation.capture.journal import JournalWriter, list_segments

try:
    from aether_agents.observation.capture.retained_index import (
        RetainedIndex,
        _resolve_retained_binding,
        get_retained_index,
    )
except ModuleNotFoundError:  # Base-revision RED harness: RC6 has no retained index yet.
    RetainedIndex = None  # type: ignore[assignment,misc]
    _resolve_retained_binding = None  # type: ignore[assignment]
    get_retained_index = None  # type: ignore[assignment]
from aether_agents.observation.context import ProjectRegistry
from aether_agents.observation.contracts import (
    canonical_json_bytes,
)
from aether_agents.observation.identity import correlation_token
from aether_agents.paths import ObservationPaths


class FakePluginContext:
    def __init__(self, profile_name: str = "morfeo") -> None:
        self.profile_name = profile_name
        self.hooks: dict[str, list[Any]] = {}
        self.unload_callbacks: list[Any] = []

    def register_hook(self, name: str, callback: Any) -> None:
        self.hooks.setdefault(name, []).append(callback)

    def register_tool(self, **_kwargs: Any) -> None:
        pass

    def on_unload(self, callback: Any) -> None:
        self.unload_callbacks.append(callback)


def _setup_project(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> tuple[Path, ObservationPaths]:
    state = tmp_path / "state"
    project = tmp_path / "project"
    marker = project / ".aether" / "project.toml"
    marker.parent.mkdir(parents=True, exist_ok=True)
    marker.write_text(project_marker(PROJECT_ID), encoding="utf-8")
    monkeypatch.setenv("XDG_STATE_HOME", str(state))
    monkeypatch.setenv("AETHER_PROJECT_ID", PROJECT_ID)
    monkeypatch.setenv("HERMES_HOME", str(tmp_path / "hermes" / "profiles" / "morfeo"))
    registry = ProjectRegistry()
    registry.register(PROJECT_ID, project, "test-passive")
    paths = ObservationPaths.for_project(PROJECT_ID, root=state)
    paths.ensure()
    return project, paths


def _write_sample_journal(paths: ObservationPaths, count: int = 5) -> list[dict[str, Any]]:
    factory = EventFactory()
    events: list[dict[str, Any]] = [factory.opened()]
    events.append(
        factory.unit(
            "work_unit.bound",
            "reported",
            1.0,
            task_ref="t_11111111",
            relation="root",
        )
    )
    for i in range(count):
        events.append(
            factory.unit(
                "work_unit.bound",
                "reported",
                2.0 + i,
                task_ref=f"t_{i + 2:08x}",
                relation="child",
            )
        )
    writer = JournalWriter(paths=paths, producer_epoch=EPOCH)
    writer.open()
    for ev in events:
        writer.append(ev)
    writer.close()
    return events


def test_registration_and_hot_hooks_complete_while_historical_reader_held_on_barrier(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """(a) Registration and hot hooks complete while historical reader is held on barrier.

    The candidate uses the RetainedIndex worker.  On the base revision, the same
    harness patches the module-level ``hermes_plugin.list_segments`` seam reached by
    synchronous ``_restore_all_retained_bindings``; that side must fail by blocking
    registration until the barrier is released.
    """
    _, paths = _setup_project(tmp_path, monkeypatch)
    _write_sample_journal(paths, count=20)

    barrier_entered = threading.Event()
    barrier_release = threading.Event()

    ctx = FakePluginContext()
    if RetainedIndex is None:
        original_list_segments = hermes_plugin.list_segments

        def blocking_list_segments(value: ObservationPaths) -> Any:
            barrier_entered.set()
            barrier_release.wait(timeout=5.0)
            return original_list_segments(value)

        monkeypatch.setattr(hermes_plugin, "list_segments", blocking_list_segments)
        registration_finished = threading.Event()
        registration_error: list[BaseException] = []

        def register_base() -> None:
            try:
                hermes_plugin.register(ctx)
            except BaseException as exc:  # pragma: no cover - diagnostic for base RED runs
                registration_error.append(exc)
            finally:
                registration_finished.set()

        registration_thread = threading.Thread(target=register_base)
        registration_thread.start()
        assert barrier_entered.wait(timeout=2.0), "Base startup should hit the history barrier"
        assert not registration_finished.is_set(), (
            "Base registration unexpectedly bypassed synchronous retained-history recovery"
        )
        barrier_release.set()
        registration_thread.join(timeout=2.0)
        assert not registration_error
        assert registration_finished.is_set()
        pytest.fail(
            "Base revision synchronously waits for retained history during registration; "
            "the candidate branch must take the worker path"
        )

    original_refresh = RetainedIndex.refresh

    def blocking_refresh(
        self: RetainedIndex, p: ObservationPaths, *args: Any, **kwargs: Any
    ) -> None:
        barrier_entered.set()
        barrier_release.wait(timeout=5.0)
        original_refresh(self, p, *args, **kwargs)

    monkeypatch.setattr(RetainedIndex, "refresh", blocking_refresh)

    start_reg = perf_counter()
    hermes_plugin.register(ctx)
    elapsed_reg = perf_counter() - start_reg
    assert elapsed_reg < 5.0, (
        f"Registration took {elapsed_reg:.4f}s; must not wait for history (5s barrier)"
    )

    # Background worker triggers blocking_refresh
    assert barrier_entered.wait(timeout=2.0), "Historical reader should have hit the barrier"

    # While historical reader is deliberately held on barrier, fire all hot hooks
    token = correlation_token(TRACE_ID, "hot-hook-unit")

    start_hooks = perf_counter()
    # 1. on_session_start
    if "on_session_start" in ctx.hooks:
        ctx.hooks["on_session_start"][0](session_id="hot-sess-1")

    # 2. pre_tool_call
    if "pre_tool_call" in ctx.hooks:
        ctx.hooks["pre_tool_call"][0](
            tool_name="kanban_create",
            tool_call_id="call-hot-1",
            session_id="hot-sess-1",
            args={"idempotency_key": token},
        )

    # 3. post_tool_call (with kanban_create)
    if "post_tool_call" in ctx.hooks:
        ctx.hooks["post_tool_call"][0](
            tool_name="kanban_create",
            tool_call_id="call-hot-1",
            session_id="hot-sess-1",
            status="completed",
            args={"idempotency_key": token},
            result={"ok": True, "task_id": "t_hot_task", "project_id": PROJECT_ID},
        )

    # 4. pre_api_request / post_api_request
    if "pre_api_request" in ctx.hooks:
        ctx.hooks["pre_api_request"][0](
            api_request_id="hot-req-1",
            session_id="hot-sess-1",
            turn_id="turn-1",
            task_id="t_hot_task",
            model="model-test",
            provider="provider-test",
        )
    if "post_api_request" in ctx.hooks:
        ctx.hooks["post_api_request"][0](
            api_request_id="hot-req-1",
            session_id="hot-sess-1",
            turn_id="turn-1",
            task_id="t_hot_task",
            status="completed",
            usage={"input_tokens": 10, "output_tokens": 20, "total_tokens": 30},
        )

    # 5. kanban_task_claimed
    if "kanban_task_claimed" in ctx.hooks:
        ctx.hooks["kanban_task_claimed"][0](
            task_id="t_hot_task",
            session_id="hot-sess-1",
        )

    elapsed_hooks = perf_counter() - start_hooks
    assert elapsed_hooks < 0.050, f"Hot hooks took {elapsed_hooks:.4f}s; must not wait for history"

    # Release historical reader barrier
    barrier_release.set()

    for cb in reversed(ctx.unload_callbacks):
        cb()


@pytest.mark.skipif(
    RetainedIndex is None, reason="retained index is absent on the base RED revision"
)
def test_unchanged_retained_snapshot_validated_once_via_instrumentation(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """(b) An unchanged retained snapshot is validated once per snapshot (instrumented)."""
    _, paths = _setup_project(tmp_path, monkeypatch)
    _write_sample_journal(paths, count=5)

    index = get_retained_index(paths)
    assert index.validation_count == 0

    index.refresh(paths)
    assert index.validation_count == 1, "First refresh must validate the snapshot"
    assert index.trace_exists(TRACE_ID)
    assert index.get_binding("t_11111111") == (TRACE_ID, "root")

    # Repeat refreshes on unchanged snapshot: validation_count must not increase
    for _ in range(10):
        index.refresh(paths)
        assert index.validation_count == 1, "Unchanged snapshot must not re-validate"

    # Helper queries also do not re-validate unchanged snapshot
    assert hermes_plugin._retained_trace_exists(paths, TRACE_ID)
    assert hermes_plugin._retained_binding(paths, "t_11111111") == (TRACE_ID, "root")
    assert len(index.get_bindings()) >= 2
    assert index.validation_count == 1, "Lookups must use cached index without re-validating"

    # Now append an event: snapshot changes, so next refresh increments counter exactly once
    factory = EventFactory()
    new_event = factory.unit(
        "work_unit.bound",
        "reported",
        100.0,
        task_ref="t_99999999",
        relation="child",
    )
    writer = JournalWriter(paths=paths, producer_epoch=f"prd_{secrets.token_hex(16)}")
    writer.open()
    writer.append(new_event)
    writer.close()

    index.refresh(paths)
    assert index.validation_count == 2, "Modified snapshot must trigger exactly one re-validation"
    assert index.get_binding("t_99999999") is not None

    for _ in range(5):
        index.refresh(paths)
        assert index.validation_count == 2, "Unchanged modified snapshot must stay at 2"


@pytest.mark.skipif(
    RetainedIndex is None, reason="retained index is absent on the base RED revision"
)
def test_retained_index_full_versus_incremental_semantic_equivalence(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """(c) Appended segments preserve full-versus-incremental semantic equivalence."""
    _, paths = _setup_project(tmp_path, monkeypatch)
    _write_sample_journal(paths, count=3)

    # Build incremental index
    incremental = RetainedIndex(paths.project_id)
    incremental.refresh(paths)
    assert incremental.validation_count == 1

    # Append more events in a second segment
    factory = EventFactory()
    writer = JournalWriter(paths=paths, producer_epoch=f"prd_{secrets.token_hex(16)}")
    writer.open()
    for i in range(4):
        ev = factory.unit(
            "work_unit.bound",
            "reported",
            50.0 + i,
            task_ref=f"t_second_{i}",
            relation="child",
        )
        writer.append(ev)
    writer.close()

    # Refresh incremental index
    incremental.refresh(paths)
    assert incremental.validation_count == 2

    # Build fresh index from scratch on the complete directory
    fresh = RetainedIndex(paths.project_id)
    fresh.refresh(paths)
    assert fresh.validation_count == 1

    # Verify semantic equivalence
    assert incremental.traces == fresh.traces
    assert incremental.resolved_bindings == fresh.resolved_bindings
    assert sorted(incremental.candidate_rows.keys()) == sorted(fresh.candidate_rows.keys())
    for k in fresh.candidate_rows:
        assert incremental.candidate_rows[k] == fresh.candidate_rows[k]


@pytest.mark.skipif(
    RetainedIndex is None, reason="retained index is absent on the base RED revision"
)
def test_retained_index_handles_truncated_replaced_conflicting_and_quarantined(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """(c) Truncated, replaced, conflicting, and quarantined segments are correctly handled."""
    _, paths = _setup_project(tmp_path, monkeypatch)
    _write_sample_journal(paths, count=3)

    index = RetainedIndex(paths.project_id)
    index.refresh(paths)
    assert index.validation_count == 1
    assert "t_00000002" in index.resolved_bindings

    # 1. Truncation test: truncate segment bytes
    segments = list_segments(paths)
    target_seg = segments[0]
    raw = target_seg.path.read_bytes()
    # Truncate halfway
    target_seg.path.write_bytes(raw[: len(raw) // 2])
    index.refresh(paths)
    assert index.validation_count == 2, "Truncation must trigger re-validation"

    # 2. Replacement test: write an active segment, index it, then replace it with new inode/content
    epoch2 = f"prd_{secrets.token_hex(16)}"
    active_seg = paths.active / f"{epoch2}.0000000000000000.active.jsonl"
    factory2 = EventFactory(epoch=epoch2)
    ev1 = factory2.unit(
        "work_unit.bound", "reported", 10.0, task_ref="t_12345678", relation="child"
    )
    active_seg.write_bytes(canonical_json_bytes(ev1) + b"\n")
    index.refresh(paths)
    assert "t_12345678" in index.resolved_bindings
    c_before = index.validation_count

    ev2 = EventFactory(epoch=epoch2).unit(
        "work_unit.bound", "reported", 11.0, task_ref="t_aaaaaaaa", relation="child"
    )
    tmp_replacement = active_seg.with_suffix(".tmp")
    tmp_replacement.write_bytes(canonical_json_bytes(ev2) + b"\n")
    tmp_replacement.replace(active_seg)

    index.refresh(paths)
    assert index.validation_count == c_before + 1, "Replacement must trigger re-validation"
    assert "t_aaaaaaaa" in index.resolved_bindings
    assert "t_12345678" not in index.resolved_bindings

    # 3. Quarantine test: place a segment in quarantine dir; it must be completely ignored
    quarantine_file = (
        paths.quarantine / f"{EPOCH}.0000000000000001.0000000000000002.quarantine.jsonl"
    )
    hostile_event = deepcopy(ev2)
    hostile_event["work_unit"]["task_ref"] = "t_bbbbbbbb"
    quarantine_file.write_bytes(canonical_json_bytes(hostile_event) + b"\n")

    index.refresh(paths)
    assert "t_bbbbbbbb" not in index.resolved_bindings

    # 4. Conflicting binding test: candidate rows with contradictory unbind / bind across epochs
    cands: list[tuple[str, int, str, str, str, str]] = [
        ("epoch1", 1, "evt1", "work_unit.bound", "root", TRACE_ID),
        ("epoch2", 1, "evt2", "work_unit.unbound", "root", TRACE_ID),
    ]
    resolved = _resolve_retained_binding(cands)
    assert resolved is None, "Conflicting bind/unbind across independent epochs must not resolve"

    # Production hook boundary: a cold index must not emit a new claim over a
    # pre-existing retained claim. The pending intent is rejected when refresh sees A.
    _, cold_paths = _setup_project(tmp_path / "cold-binding", monkeypatch)
    _write_sample_journal(cold_paths, count=0)
    cold_index = get_retained_index(cold_paths)
    cold_collector = Collector(paths=cold_paths, runtime_fingerprint="3" * 64)
    cold_collector.start(None)
    cold_trace = "ctr_22222222222222222222222222222222"
    cold_event = EventFactory(
        project_id=PROJECT_ID,
        trace_id=cold_trace,
        epoch=cold_collector.producer_epoch,
    ).unit("work_unit.bound", "reported", 7.0, task_ref="t_11111111", relation="child")
    cold_observer = object.__new__(hermes_plugin._Observer)
    assert not cold_observer._emit_binding_durable(
        cold_collector,
        trace_id=cold_trace,
        task_ref="t_11111111",
        relation="child",
        event=cold_event,
    )
    cold_collector.stop()
    cold_index.refresh(cold_paths)
    assert cold_index.get_binding("t_11111111") == (TRACE_ID, "root")
    assert cold_index.binding_state("t_11111111") == "verified"
    assert cold_index.pending_binding("t_11111111") is None
    assert all(row[-1] != cold_trace for row in cold_index.candidate_rows["t_11111111"]), (
        "Unchecked conflicting hook claim must not enter retained history"
    )

    # A pending local claim survives an unrelated segment refresh, then is emitted
    # only after a complete snapshot proves that its task is absent.
    _, pending_paths = _setup_project(tmp_path / "pending-binding", monkeypatch)
    pending_index = get_retained_index(pending_paths)
    pending_collector = Collector(paths=pending_paths, runtime_fingerprint="3" * 64)
    pending_collector.start(None)
    pending_trace = "ctr_33333333333333333333333333333333"
    pending_event = EventFactory(
        project_id=PROJECT_ID,
        trace_id=pending_trace,
        epoch=pending_collector.producer_epoch,
    ).unit("work_unit.bound", "reported", 8.0, task_ref="t_abcdef01", relation="implementation")
    pending_observer = object.__new__(hermes_plugin._Observer)
    pending_observer._reconciler = hermes_plugin._NativeReconciliationWorker(pending_observer)
    assert not pending_observer._emit_binding_durable(
        pending_collector,
        trace_id=pending_trace,
        task_ref="t_abcdef01",
        relation="implementation",
        event=pending_event,
    )
    assert pending_index.binding_state("t_abcdef01") == "pending"

    unrelated = EventFactory(
        project_id=PROJECT_ID,
        trace_id=TRACE_ID,
        epoch=f"prd_{secrets.token_hex(16)}",
    ).unit("work_unit.bound", "reported", 9.0, task_ref="t_deadbeef", relation="child")
    unrelated_writer = JournalWriter(
        paths=pending_paths, producer_epoch=f"prd_{secrets.token_hex(16)}"
    )
    unrelated_writer.open()
    unrelated_writer.append(unrelated)
    unrelated_writer.close()
    pending_index.refresh(pending_paths)
    assert pending_index.pending_binding("t_abcdef01") == (pending_trace, "implementation")
    pending_observer._flush_pending_binding_events(pending_collector)
    pending_collector.stop()
    pending_index.refresh(pending_paths)
    assert pending_index.get_binding("t_abcdef01") == (pending_trace, "implementation")
    assert pending_index.pending_binding("t_abcdef01") is None


@pytest.mark.skipif(
    RetainedIndex is None, reason="retained index is absent on the base RED revision"
)
def test_retained_index_reports_unavailable_snapshot_without_false_empty_state(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Enumeration failure remains observable and fail-closed."""
    from aether_agents.observation.capture import retained_index as retained_index_module

    _, paths = _setup_project(tmp_path, monkeypatch)
    index = RetainedIndex(paths.project_id)
    health_codes: list[str] = []

    def unavailable(_paths: ObservationPaths) -> list[Any]:
        raise OSError("synthetic retained-store failure")

    monkeypatch.setattr(retained_index_module, "list_segments", unavailable)
    index.refresh(
        paths, collector=SimpleNamespace(health=SimpleNamespace(increment=health_codes.append))
    )

    assert index.snapshot_state == "unavailable"
    assert "RETAINED_INDEX_UNAVAILABLE" in health_codes
    assert not index.trace_exists(TRACE_ID)
    assert index.get_binding("t_11111111") is None
    assert index.get_bindings() == {}
