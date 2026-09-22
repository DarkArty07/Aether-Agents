"""Tests for passive observer startup, asynchronous retained bindings, and snapshot indexing.

Satisfies:
(a) Registration and hot hooks complete while historical reader is deliberately held on a barrier;
(b) An unchanged retained snapshot is validated once per snapshot, demonstrated by instrumentation;
(c) Appended, replaced, truncated, conflicting and quarantined segments preserve canonical
    binding/privacy invariants and full-versus-incremental semantic equivalence.
"""

from __future__ import annotations

import json
import secrets
import threading
from contextlib import contextmanager
from copy import deepcopy
from pathlib import Path
from time import perf_counter, thread_time
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
from aether_agents.observation.capture.journal import (
    JournalWriter,
    list_segments,
    parse_segment_name,
    read_segment,
)

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
from aether_agents.observation.locking import ProjectLockTimeout, project_lock
from aether_agents.observation.retention import compact_segment, verify_archive
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


def _retained_unit_claims(paths: ObservationPaths, task_ref: str) -> list[tuple[str, str]]:
    """Return every retained ``work_unit`` claim for one task ref, in segment order."""
    claims: list[tuple[str, str]] = []
    for segment in list_segments(paths):
        if segment.state == "quarantine":
            continue
        for line in read_segment(segment.path).lines:
            event = json.loads(line.decode("utf-8"))
            unit = event.get("work_unit")
            if isinstance(unit, dict) and unit.get("task_ref") == task_ref:
                claims.append((str(event.get("trace_id")), str(event.get("event_type"))))
    return claims


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
    historical_reader_resumed = threading.Event()

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
        historical_reader_resumed.set()
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

    # The barrier proves the causal requirement. A wall clock also counts times
    # when CI deschedules this thread, which is not time spent inside hot hooks.
    start_hooks = thread_time()
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

    elapsed_hooks = thread_time() - start_hooks
    assert not historical_reader_resumed.is_set(), "Hot hooks waited for the historical reader"
    assert elapsed_hooks < 0.050, f"Hot hooks used {elapsed_hooks:.4f}s of CPU"

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


@pytest.mark.skipif(
    RetainedIndex is None, reason="retained index is absent on the base RED revision"
)
def test_moved_snapshot_stops_an_absent_verdict_from_publishing_a_claim(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A stale absence verdict must not publish a claim the live evidence contradicts.

    Production hook path: the retained snapshot validates task ``T`` as absent, another
    producer then appends its own durable claim for ``T``, and this process's hook claims
    a different trace for the same task.  Publishing that claim would leave both claims
    unresolvable and destroy the pre-existing durable attribution, so the hook keeps its
    intent pending for the worker's validated emission path instead.  Candidate
    ``03c0e635`` appended the claim here (returning ``True``); base ``d2874c2f`` refused
    it and preserved the durable attribution, which is the preservation reference for
    this regression.
    """
    _, paths = _setup_project(tmp_path / "stale-binding", monkeypatch)
    task_ref = "t_5a17e001"
    retained_trace = "ctr_44444444444444444444444444444444"
    claimed_trace = "ctr_55555555555555555555555555555555"
    index = get_retained_index(paths)
    collector = Collector(paths=paths, runtime_fingerprint="3" * 64)
    collector.start(None)

    # 1. The validated snapshot reports the task absent.
    index.refresh(paths)
    assert index.binding_state(task_ref) == "absent"

    # 2. Another producer appends its durable claim after that validation.
    foreign_epoch = f"prd_{secrets.token_hex(16)}"
    foreign_event = EventFactory(
        project_id=PROJECT_ID, trace_id=retained_trace, epoch=foreign_epoch
    ).unit("work_unit.bound", "reported", 21.0, task_ref=task_ref, relation="root")
    foreign_writer = JournalWriter(paths=paths, producer_epoch=foreign_epoch)
    foreign_writer.open()
    assert foreign_writer.append(foreign_event).accepted
    foreign_writer.close()

    assert index.binding_state(task_ref) == "absent", "the in-memory verdict is unchanged"

    # 3. The hook claim must not become durable on that moved verdict.
    claimed_event = EventFactory(
        project_id=PROJECT_ID, trace_id=claimed_trace, epoch=collector.producer_epoch
    ).unit("work_unit.bound", "reported", 22.0, task_ref=task_ref, relation="root")
    observer = object.__new__(hermes_plugin._Observer)
    observer._reconciler = hermes_plugin._NativeReconciliationWorker(observer)
    assert not observer._emit_binding_durable(
        collector,
        trace_id=claimed_trace,
        task_ref=task_ref,
        relation="root",
        event=claimed_event,
    )
    assert _retained_unit_claims(paths, task_ref) == [(retained_trace, "work_unit.bound")]
    assert not index.snapshot_covers_disk(paths, own_epoch=collector.producer_epoch), (
        "the absence verdict no longer covers the live retained evidence"
    )

    # 4. The worker's validated emission path refuses the same moved verdict.
    observer._flush_pending_binding_events(collector)
    assert _retained_unit_claims(paths, task_ref) == [(retained_trace, "work_unit.bound")]
    collector.stop()

    # 5. Validating the live evidence preserves the durable attribution and drops the
    #    contradictory intent instead of letting it destroy the earlier claim.
    index.refresh(paths)
    assert index.get_binding(task_ref) == (retained_trace, "root")
    assert index.binding_state(task_ref) == "verified"
    assert index.pending_binding(task_ref) is None
    assert all(row[-1] != claimed_trace for row in index.candidate_rows[task_ref])


@pytest.mark.skipif(
    RetainedIndex is None, reason="retained index is absent on the base RED revision"
)
def test_own_producer_appends_keep_a_validated_verdict_usable(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """This process's own appends must not stall its own durable binding.

    Guards the boundary of the moved-snapshot rule: a healthy single-producer session
    still publishes its claim immediately, while the same snapshot viewed from another
    producer epoch, or after a foreign segment appears, correctly stops covering the
    live retained evidence.
    """
    _, paths = _setup_project(tmp_path / "own-epoch-binding", monkeypatch)
    task_ref = "t_5a17e002"
    own_trace = "ctr_66666666666666666666666666666666"
    index = get_retained_index(paths)
    collector = Collector(paths=paths, runtime_fingerprint="3" * 64)
    collector.start(None)
    index.refresh(paths)
    assert index.binding_state(task_ref) == "absent"
    assert index.snapshot_covers_disk(paths, own_epoch=collector.producer_epoch)

    # The session's own events land in its own segment after that validation.
    own_event = EventFactory(
        project_id=PROJECT_ID, trace_id=own_trace, epoch=collector.producer_epoch
    ).unit("work_unit.bound", "reported", 31.0, task_ref="t_5a17e003", relation="implementation")
    assert collector.emit(own_event).accepted

    assert index.snapshot_covers_disk(paths, own_epoch=collector.producer_epoch)
    assert not index.snapshot_covers_disk(paths, own_epoch=f"prd_{secrets.token_hex(16)}")

    binding_event = EventFactory(
        project_id=PROJECT_ID, trace_id=own_trace, epoch=collector.producer_epoch
    ).unit("work_unit.bound", "reported", 32.0, task_ref=task_ref, relation="root")
    observer = object.__new__(hermes_plugin._Observer)
    observer._reconciler = hermes_plugin._NativeReconciliationWorker(observer)
    assert not observer._emit_binding_durable(
        collector,
        trace_id=own_trace,
        task_ref=task_ref,
        relation="root",
        event=binding_event,
    )
    assert _retained_unit_claims(paths, task_ref) == [], (
        "the synchronous hook path never publishes a durable claim"
    )
    assert index.binding_state(task_ref) == "pending"

    # The worker publishes it from its own validated snapshot, serialized against
    # cooperating emitters.
    observer._flush_pending_binding_events(collector)
    assert _retained_unit_claims(paths, task_ref) == [(own_trace, "work_unit.bound")]

    # A foreign segment appearing after validation stops covering, so the next claim
    # for the same snapshot is kept pending instead of being published.
    foreign_writer = JournalWriter(paths=paths, producer_epoch=f"prd_{secrets.token_hex(16)}")
    foreign_writer.open()
    assert foreign_writer.append(
        EventFactory(
            project_id=PROJECT_ID,
            trace_id=own_trace,
            epoch=foreign_writer.producer_epoch,
        ).unit(
            "work_unit.bound", "reported", 33.0, task_ref="t_5a17e004", relation="implementation"
        )
    ).accepted
    foreign_writer.close()
    assert not index.snapshot_covers_disk(paths, own_epoch=collector.producer_epoch)
    collector.stop()

    index.refresh(paths)
    assert index.get_binding(task_ref) == (own_trace, "root")
    assert index.get_binding("t_5a17e003") == (own_trace, "implementation")


#: A hook-path bound well under the measured base cost of the archived corpus built
#: below (3 archived segments x 400 events cost ~1.2 s of hashing, decompression and
#: re-validation), and still generous for a loaded machine.
_ARCHIVE_HOOK_BOUND_S = 0.25


def _build_archived_corpus(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    *,
    archives: int = 3,
    events_per_archive: int = 400,
) -> ObservationPaths:
    """Build a retained corpus whose whole history lives in verified archives.

    Every archive is produced by the production compaction path from a closed segment
    with its own producer epoch, so the cost this regression measures is real
    ``verify_archive`` work: compressed-byte hashing, gzip decompression, and schema,
    sequence and privacy validation of every archived event.
    """
    _, paths = _setup_project(tmp_path / "archived-hook", monkeypatch)
    for archive_index in range(archives):
        epoch = f"prd_{secrets.token_hex(16)}"
        factory = EventFactory(epoch=epoch)
        writer = JournalWriter(paths=paths, producer_epoch=epoch)
        writer.open()
        for event_index in range(events_per_archive):
            event = factory.unit(
                "work_unit.bound",
                "reported",
                100.0 + event_index,
                task_ref=f"t_{archive_index:02x}{event_index:06x}",
                relation="child",
            )
            assert writer.append(event).accepted
        closed = writer.close()
        assert closed is not None
        segment = parse_segment_name(closed)
        assert segment is not None and segment.state == "closed"
        result = compact_segment(paths, segment)
        assert verify_archive(result.manifest_path).ok
    return paths


def _count_archive_content_reads(monkeypatch: pytest.MonkeyPatch, counts: dict[str, int]) -> None:
    """Instrument the two content-reading seams of archived-history verification."""
    from aether_agents.observation import retention as retention_module

    original_verify = retention_module.verify_archive
    original_read = retention_module._read_gzip_segment

    def counting_verify(manifest_path: Path) -> Any:
        counts["verify_archive"] += 1
        return original_verify(manifest_path)

    def counting_read(compressed: bytes) -> Any:
        counts["read_gzip_segment"] += 1
        return original_read(compressed)

    monkeypatch.setattr(retention_module, "verify_archive", counting_verify)
    monkeypatch.setattr(retention_module, "_read_gzip_segment", counting_read)


@pytest.mark.skipif(
    RetainedIndex is None, reason="retained index is absent on the base RED revision"
)
def test_hook_binding_path_reads_no_archived_history_and_stays_bounded(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A synchronous hook publishes nothing and reads no archived history.

    The retained corpus is entirely archived, so the accepted tip's stat-only coverage
    check had to hash, decompress and re-validate every archive before a hook could
    publish: this harness measures ~1.2 s and three ``verify_archive`` calls per claim on
    ``00be3b17``.  A hook keeps the intent pending instead, and the reconciliation worker
    publishes it afterwards from its own validated snapshot.
    """
    paths = _build_archived_corpus(tmp_path, monkeypatch)
    collector = Collector(paths=paths, runtime_fingerprint="3" * 64)
    collector.start(None)
    index = get_retained_index(paths)
    index.refresh(paths)
    assert index.snapshot_state == "validated"
    archived = [segment for segment in list_segments(paths) if segment.state == "archive"]
    assert len(archived) == 3

    counts = {"verify_archive": 0, "read_gzip_segment": 0}
    _count_archive_content_reads(monkeypatch, counts)

    task_ref = "t_a2c00001"
    claim_trace = "ctr_9a9a9a9a9a9a9a9a9a9a9a9a9a9a9a9a"
    claim_event = EventFactory(
        project_id=PROJECT_ID, trace_id=claim_trace, epoch=collector.producer_epoch
    ).unit("work_unit.bound", "reported", 900.0, task_ref=task_ref, relation="root")
    observer = object.__new__(hermes_plugin._Observer)
    observer._reconciler = hermes_plugin._NativeReconciliationWorker(observer)

    start = perf_counter()
    published = observer._emit_binding_durable(
        collector,
        trace_id=claim_trace,
        task_ref=task_ref,
        relation="root",
        event=claim_event,
    )
    elapsed = perf_counter() - start

    assert counts == {"verify_archive": 0, "read_gzip_segment": 0}, (
        f"hook read archived history: {counts} in {elapsed:.3f}s over"
        f" {len(archived)} archived segments"
    )
    assert elapsed < _ARCHIVE_HOOK_BOUND_S, (
        f"hook binding path took {elapsed:.3f}s on a {len(archived)}x400 archived corpus"
    )
    assert published is False, "a hook must not publish a durable claim"
    assert _retained_unit_claims(paths, task_ref) == []
    assert index.binding_state(task_ref) == "pending"

    # The worker's own coverage pass and emission stay stat-only as well.
    observer._flush_pending_binding_events(collector)
    assert _retained_unit_claims(paths, task_ref) == [(claim_trace, "work_unit.bound")]
    assert counts == {"verify_archive": 0, "read_gzip_segment": 0}
    collector.stop()


def _cooperating_durable_emit(
    paths: ObservationPaths,
    task_ref: str,
    trace_id: str,
    *,
    timeout_s: float | None,
) -> str:
    """One cooperating durable claim in base ``d2874c2f``'s read+emit order.

    The base emitter held ``project_lock(paths, "native-binding")`` across its retained
    read *and* its append, so a second cooperating emitter serializes behind it and
    refuses instead of appending a contradictory claim.  The lock, the retained read and
    the emit are production code; only this composition is test-local, because the
    accepted tip moved absence-based emission into the reconciliation worker.
    """
    try:
        with project_lock(paths, "native-binding", timeout_s=timeout_s):
            if hermes_plugin._retained_binding(paths, task_ref) is not None:
                return "refused"
            emitter = Collector(paths=paths, runtime_fingerprint="3" * 64)
            emitter.start(None)
            try:
                event = EventFactory(
                    project_id=PROJECT_ID,
                    trace_id=trace_id,
                    epoch=emitter.producer_epoch,
                ).unit("work_unit.bound", "reported", 61.0, task_ref=task_ref, relation="root")
                accepted = emitter.emit(event).accepted
            finally:
                emitter.stop()
            return "emitted" if accepted else "emit_failed"
    except ProjectLockTimeout:
        return "serialized_out"


@pytest.mark.skipif(
    RetainedIndex is None, reason="retained index is absent on the base RED revision"
)
def test_cooperating_emitters_serialize_absence_based_durable_emission(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A cooperating emitter cannot interleave with the worker's verdict->append window.

    The hook keeps an absence-based intent pending; a cooperating emitter then runs
    *inside* the window between the worker's coverage verdict and its append.  On the
    accepted tip ``00be3b17`` that window is unprotected, so the cooperating claim lands
    and the worker appends a second, contradictory claim: two retained claims for one task
    and no resolution.  Here the window is serialized by the project lock the pre-fix
    production emitter used, so the cooperating emitter cannot append, exactly one durable
    claim results, and a later cooperating emitter for the same task is refused instead of
    creating a conflict.
    """
    _, paths = _setup_project(tmp_path / "cooperating-binding", monkeypatch)
    task_ref = "t_c0000001"
    hook_trace = "ctr_77777777777777777777777777777777"
    first_rival_trace = "ctr_88888888888888888888888888888888"
    second_rival_trace = "ctr_99999999999999999999999999999999"
    collector = Collector(paths=paths, runtime_fingerprint="3" * 64)
    collector.start(None)
    index = get_retained_index(paths)
    observer = object.__new__(hermes_plugin._Observer)
    observer._reconciler = hermes_plugin._NativeReconciliationWorker(observer)

    # 1. The production hook path keeps the absence-based intent pending.
    hook_event = EventFactory(
        project_id=PROJECT_ID, trace_id=hook_trace, epoch=collector.producer_epoch
    ).unit("work_unit.bound", "reported", 51.0, task_ref=task_ref, relation="root")
    assert not observer._emit_binding_durable(
        collector,
        trace_id=hook_trace,
        task_ref=task_ref,
        relation="root",
        event=hook_event,
    )
    assert index.binding_state(task_ref) == "pending"
    assert _retained_unit_claims(paths, task_ref) == []

    # 2. The worker validated the task as absent before its emission cycle.
    index.refresh(paths)
    assert index.binding_state(task_ref) == "pending"

    # 3. Interleave a cooperating emitter into the verdict -> append window.
    verdict_taken = threading.Event()
    interleave_done = threading.Event()
    original_covers = RetainedIndex.snapshot_covers_disk

    def paused_covers(
        self: RetainedIndex, value: ObservationPaths, *args: Any, **kwargs: Any
    ) -> bool:
        verdict = original_covers(self, value, *args, **kwargs)
        verdict_taken.set()
        assert interleave_done.wait(timeout=5.0), "cooperating emitter never completed"
        return verdict

    monkeypatch.setattr(RetainedIndex, "snapshot_covers_disk", paused_covers)
    outcomes: list[str] = []

    def cooperating_emitter() -> None:
        assert verdict_taken.wait(timeout=5.0)
        try:
            outcomes.append(
                _cooperating_durable_emit(paths, task_ref, first_rival_trace, timeout_s=0.3)
            )
        finally:
            interleave_done.set()

    thread = threading.Thread(target=cooperating_emitter, name="cooperating-emitter")
    thread.start()
    observer._flush_pending_binding_events(collector)
    thread.join(timeout=5.0)
    assert not thread.is_alive()

    claims = _retained_unit_claims(paths, task_ref)
    assert claims == [(hook_trace, "work_unit.bound")], (
        "exactly one durable claim must result"
        f" (cooperating emitter: {outcomes}, retained claims: {claims})"
    )
    assert outcomes and outcomes[0] in {"serialized_out", "refused"}, (
        f"the cooperating emitter appended inside the window: {outcomes}"
    )

    # 4. A cooperating emitter for the same task preserves the existing attribution.
    assert (
        _cooperating_durable_emit(paths, task_ref, second_rival_trace, timeout_s=None) == "refused"
    )
    assert _retained_unit_claims(paths, task_ref) == [(hook_trace, "work_unit.bound")]

    # 5. The retained resolution keeps the winning attribution and stays resolvable.
    index.refresh(paths)
    assert index.get_binding(task_ref) == (hook_trace, "root")
    assert index.binding_state(task_ref) == "verified"
    collector.stop()


def _recording_project_lock(original: Any, recorded: list[str]) -> Any:
    """Wrap ``project_lock`` so the test can see which locks the code under test takes."""

    @contextmanager
    def wrapper(value: ObservationPaths, name: str, **kwargs: Any) -> Any:
        recorded.append(name)
        with original(value, name, **kwargs):
            yield

    return wrapper


@pytest.mark.skipif(
    RetainedIndex is None, reason="retained index is absent on the base RED revision"
)
def test_worker_emission_publishes_validated_absence_claims_once_under_the_lock(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The worker publishes from its validated snapshot, under the project lock.

    The same production entry point a synchronous hook uses keeps its intent pending and
    takes no maintenance lock there; the reconciliation worker -- which validated the
    snapshot at its own cadence -- publishes immediately inside the ``native-binding``
    project lock and marks the intent emitted, so its later flush appends nothing twice.
    """
    _, paths = _setup_project(tmp_path / "worker-binding", monkeypatch)
    hook_task = "t_w0rker02"
    worker_task = "t_w0rker01"
    hook_trace = "ctr_d0d0d0d0d0d0d0d0d0d0d0d0d0d0d0d0"
    worker_trace = "ctr_d1d1d1d1d1d1d1d1d1d1d1d1d1d1d1d1"
    collector = Collector(paths=paths, runtime_fingerprint="3" * 64)
    collector.start(None)
    index = get_retained_index(paths)
    index.refresh(paths)
    assert index.binding_state(hook_task) == "absent"
    assert index.binding_state(worker_task) == "absent"
    observer = object.__new__(hermes_plugin._Observer)
    observer._reconciler = hermes_plugin._NativeReconciliationWorker(observer)

    def claim_event(trace_id: str, task_ref: str, seconds: float) -> dict[str, Any]:
        return EventFactory(
            project_id=PROJECT_ID, trace_id=trace_id, epoch=collector.producer_epoch
        ).unit("work_unit.bound", "reported", seconds, task_ref=task_ref, relation="root")

    recorded: list[str] = []
    monkeypatch.setattr(
        hermes_plugin,
        "project_lock",
        _recording_project_lock(project_lock, recorded),
        raising=False,
    )

    # The synchronous hook path publishes nothing and waits for no maintenance lock.
    assert not observer._emit_binding_durable(
        collector,
        trace_id=hook_trace,
        task_ref=hook_task,
        relation="root",
        event=claim_event(hook_trace, hook_task, 71.0),
    )
    assert _retained_unit_claims(paths, hook_task) == []
    assert recorded == []

    # The worker publishes the same validated absence immediately, serialized.
    assert observer._emit_binding_durable(
        collector,
        trace_id=worker_trace,
        task_ref=worker_task,
        relation="root",
        event=claim_event(worker_trace, worker_task, 72.0),
        from_worker=True,
    )
    assert _retained_unit_claims(paths, worker_task) == [(worker_trace, "work_unit.bound")]
    assert recorded == ["native-binding"]

    # The flush publishes the hook's intent, and appends nothing a second time.
    observer._flush_pending_binding_events(collector)
    assert _retained_unit_claims(paths, hook_task) == [(hook_trace, "work_unit.bound")]
    assert _retained_unit_claims(paths, worker_task) == [(worker_trace, "work_unit.bound")]
    assert recorded == ["native-binding", "native-binding"]
    collector.stop()
