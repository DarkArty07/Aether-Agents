"""Regression and scale gates for observation ingest (#417).

``aether observe`` was timing out at the host 420s deadline because journal
ingestion committed once per event, advanced the segment cursor only after the
whole segment finished, and held the project lock for unbounded catch-up. These
tests use disposable directories only.
"""

from __future__ import annotations

import threading
import time
from copy import deepcopy
from pathlib import Path

import pytest
from observation_helpers import EPOCH, PROJECT_ID, EventFactory

from aether_agents.observation.capture.journal import JournalWriter
from aether_agents.observation.locking import project_lock
from aether_agents.observation.reduce.ingest import ingest_pending
from aether_agents.observation.storage import ReadModel
from aether_agents.paths import ObservationPaths


def _status_stream(count: int) -> list[dict]:
    factory = EventFactory(epoch=EPOCH)
    opened = factory.opened(0)
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
        events.append(event)
    return events


def _write_closed(tmp_path: Path, events: list[dict]):
    paths = ObservationPaths.for_project(PROJECT_ID, root=tmp_path)
    writer = JournalWriter(paths=paths, producer_epoch=EPOCH)
    writer.open()
    for event in events:
        assert writer.append(event).accepted
    closed = writer.close()
    assert closed is not None
    return paths


def test_ingest_checkpoints_cursor_when_segment_ingest_is_interrupted(
    tmp_path, monkeypatch
) -> None:
    """Progress must survive interruption; a killed observe must not restart from zero."""
    paths = _write_closed(tmp_path, _status_stream(40))
    segment_key = next(
        path.relative_to(paths.journal).as_posix() for path in paths.closed.iterdir()
    )

    seen = {"n": 0}
    original = ReadModel.project_event

    def interrupt_after_progress(self, event):
        seen["n"] += 1
        if seen["n"] > 12:
            raise KeyboardInterrupt("simulated observe deadline")
        return original(self, event)

    monkeypatch.setattr(ReadModel, "project_event", interrupt_after_progress)

    with pytest.raises(KeyboardInterrupt):
        ingest_pending(paths)

    with ReadModel.open(paths) as model:
        cursor = model.read_cursor(segment_key)
        assert cursor is not None
        assert cursor.last_seq >= 11
        assert cursor.byte_length > 0
        retained = model._conn.execute("SELECT COUNT(*) FROM observation_event").fetchone()[0]
        assert retained >= 12

    monkeypatch.setattr(ReadModel, "project_event", original)
    report = ingest_pending(paths)
    with ReadModel.open(paths) as model:
        total = model._conn.execute("SELECT COUNT(*) FROM observation_event").fetchone()[0]
    assert total == 40
    assert report.events_inserted == 40 - retained


def test_bulk_upsert_commits_far_fewer_transactions_than_events(tmp_path) -> None:
    paths = ObservationPaths.for_project(PROJECT_ID, root=tmp_path)
    events = _status_stream(128)
    with ReadModel.open(paths) as model:
        batches = {"n": 0}
        original = model._upsert_event_batch

        def wrapped(batch):
            batches["n"] += 1
            return original(batch)

        model._upsert_event_batch = wrapped  # type: ignore[method-assign]
        inserted = model.upsert_events(events)
        assert inserted == 128
        assert batches["n"] < 128
        assert batches["n"] <= (128 // 16) + 1


def test_query_ingest_budget_stops_with_incomplete_progress_and_resumes(tmp_path) -> None:
    paths = _write_closed(tmp_path, _status_stream(80))

    first = ingest_pending(paths, max_events=25)
    assert first.incomplete is True
    assert first.events_inserted == 25
    with ReadModel.open(paths) as model:
        assert model._conn.execute("SELECT COUNT(*) FROM observation_event").fetchone()[0] == 25

    second = ingest_pending(paths, max_events=25)
    assert second.events_inserted == 25
    assert second.incomplete is True

    final = ingest_pending(paths)
    assert final.events_inserted == 30
    assert final.incomplete is False
    with ReadModel.open(paths) as model:
        assert model._conn.execute("SELECT COUNT(*) FROM observation_event").fetchone()[0] == 80


def test_query_lock_wait_is_bounded_and_reports_incomplete(tmp_path) -> None:
    paths = ObservationPaths.for_project(PROJECT_ID, root=tmp_path)
    paths.ensure()
    hold = threading.Event()
    ready = threading.Event()

    def holder() -> None:
        with project_lock(paths, "storage-transition"):
            ready.set()
            hold.wait(timeout=5.0)

    thread = threading.Thread(target=holder, daemon=True)
    thread.start()
    assert ready.wait(timeout=2.0)

    started = time.perf_counter()
    report = ingest_pending(paths, lock_timeout_s=0.05)
    elapsed = time.perf_counter() - started
    hold.set()
    thread.join(timeout=2.0)

    assert report.incomplete is True
    assert report.lock_timed_out is True
    assert elapsed < 1.0


def test_realistic_ingest_batch_beats_per_event_commit_baseline(tmp_path) -> None:
    """Synthetic catch-up of 2k events must stay well under a query-style budget."""
    paths = _write_closed(tmp_path, _status_stream(2000))
    started = time.perf_counter()
    report = ingest_pending(paths)
    elapsed = time.perf_counter() - started
    assert report.events_inserted == 2000
    assert report.incomplete is False
    # Per-event commit baseline was ~6ms/event (~12s for 2k). Batched ingest must
    # remain inside a comfortable observe budget with headroom under the 420s host cap.
    assert elapsed < 8.0, f"ingest of 2000 events took {elapsed:.3f}s"
