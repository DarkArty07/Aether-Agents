"""Batch performance must preserve replay ordering and event atomicity."""

import sqlite3
from itertools import permutations

import pytest
from observation_helpers import PROJECT_ID, TRACE_ID, EventFactory

from aether_agents.observation import query
from aether_agents.observation.capture.journal import JournalWriter
from aether_agents.observation.contracts import READ_MODEL_SCHEMA, validate_event
from aether_agents.observation.reduce import ingest as ingest_module
from aether_agents.observation.reduce.ingest import ingest_pending
from aether_agents.observation.storage import ReadModel
from aether_agents.paths import ObservationPaths


def test_same_batch_successful_replay_does_not_restore_failure_diagnostic(
    tmp_path, monkeypatch
) -> None:
    paths = ObservationPaths.for_project(PROJECT_ID, root=tmp_path)
    event = EventFactory().opened(0)

    with ReadModel.open(paths) as model:
        derive = model._derive
        attempts = 0

        def fail_once(candidate):
            nonlocal attempts
            attempts += 1
            if attempts == 1:
                raise RuntimeError("transient projection failure")
            derive(candidate)

        monkeypatch.setattr(model, "_derive", fail_once)
        assert model.upsert_events([event, event]) == 1
        assert attempts == 2
        assert (
            model._conn.execute(
                "SELECT COUNT(*) FROM event_derivation WHERE event_id=?", (event["event_id"],)
            ).fetchone()[0]
            == 1
        )
        assert (
            model._conn.execute(
                "SELECT COUNT(*) FROM derived_diagnostic "
                "WHERE event_ref=? AND reason_code='EVENT_DERIVATION_FAILED'",
                (event["event_id"],),
            ).fetchone()[0]
            == 0
        )


@pytest.mark.parametrize("method", ["_derive", "_clear_event_failure"])
def test_interruption_inside_projection_never_commits_partial_event(
    tmp_path, monkeypatch, method
) -> None:
    paths = ObservationPaths.for_project(PROJECT_ID, root=tmp_path)
    factory = EventFactory()
    first = factory.opened(0)
    second = factory.contract(
        "contract.persisted", "completed", 1, revision=1, after_sha256="a" * 64
    )
    writer = JournalWriter(paths=paths, producer_epoch=first["producer_epoch"])
    writer.open()
    for event in (first, second):
        assert writer.append(event).accepted
    writer.close()
    derive = getattr(ReadModel, method)

    def interrupt_second(self, event):
        if event["event_id"] == second["event_id"]:
            raise KeyboardInterrupt("interrupted before derivation completed")
        return derive(self, event)

    monkeypatch.setattr(ReadModel, method, interrupt_second)
    with pytest.raises(KeyboardInterrupt):
        ingest_pending(paths)

    # Inspect without ReadModel.open(), whose recovery must not hide an atomicity
    # violation already made durable by the interrupted transaction.
    with sqlite3.connect(paths.projection_db(READ_MODEL_SCHEMA)) as connection:
        assert connection.execute("SELECT event_id FROM observation_event").fetchall() == [
            (first["event_id"],)
        ]
        assert (
            connection.execute(
                "SELECT COUNT(*) FROM observation_event e "
                "LEFT JOIN event_derivation d ON e.event_id=d.event_id "
                "WHERE d.event_id IS NULL"
            ).fetchone()[0]
            == 0
        )

    monkeypatch.setattr(ReadModel, method, derive)
    ingest_pending(paths)
    with ReadModel.open(paths) as model:
        assert model._conn.execute("SELECT COUNT(*) FROM event_derivation").fetchone()[0] == 2


def test_bulk_failure_diagnostic_survives_a_later_batch_interruption(tmp_path, monkeypatch):
    paths = ObservationPaths.for_project(PROJECT_ID, root=tmp_path)
    factory = EventFactory()
    events = [factory.opened(0)] + [
        factory.unit("work_unit.status", "started", index, task_ref="root", task_status="running")
        for index in (1, 2)
    ]
    with ReadModel.open(paths) as model:
        derive = model._derive

        def fail_then_interrupt(event):
            if event["event_id"] == events[1]["event_id"]:
                raise RuntimeError("synthetic derivation failure")
            if event["event_id"] == events[2]["event_id"]:
                raise KeyboardInterrupt("later event interrupted")
            return derive(event)

        monkeypatch.setattr(model, "_derive", fail_then_interrupt)
        with pytest.raises(KeyboardInterrupt):
            model.upsert_events(events)

    with sqlite3.connect(paths.projection_db(READ_MODEL_SCHEMA)) as connection:
        assert connection.execute("SELECT event_id FROM observation_event").fetchall() == [
            (events[0]["event_id"],)
        ]
        assert connection.execute(
            "SELECT event_ref, reason_code FROM derived_diagnostic"
        ).fetchall() == [(events[1]["event_id"], "EVENT_DERIVATION_FAILED")]


def test_duplicate_status_arrival_order_preserves_causal_latest_state(tmp_path) -> None:
    factory = EventFactory()
    events = [
        factory.unit("work_unit.status", "started", 0, task_ref="root", task_status="running"),
        factory.unit("work_unit.status", "started", 0, task_ref="root", task_status="running"),
        factory.unit("work_unit.status", "completed", 2, task_ref="root", task_status="done"),
    ]
    for index, ordering in enumerate(permutations(events)):
        paths = ObservationPaths.for_project(PROJECT_ID, root=tmp_path / str(index))
        with ReadModel.open(paths) as model:
            assert model.upsert_events(ordering) == 3
            row = model._conn.execute(
                "SELECT task_status, last_event_id FROM bound_work_unit"
            ).fetchone()
            assert row == ("done", events[-1]["event_id"])


@pytest.mark.parametrize("source_kind", ["hermes_hook", "native_reconciliation"])
def test_advancing_status_timestamps_match_full_replay_without_rescanning(
    tmp_path, monkeypatch, source_kind
) -> None:
    factory = EventFactory()
    events = [factory.opened(0)]
    for index in range(1, 41):
        event = factory.unit(
            "work_unit.status", "started", index, task_ref="t_aaaaaaaa", task_status="running"
        )
        event["source_kind"] = source_kind
        if source_kind == "native_reconciliation":
            event["source_hook"] = "kanban_read"
        validate_event(event)
        events.append(event)

    expected_paths = ObservationPaths.for_project(PROJECT_ID, root=tmp_path / "full")
    with ReadModel.open(expected_paths) as model:
        monkeypatch.setattr(model, "_derive_bound_work_unit_status", model._derive_bound_work_unit)
        assert model.upsert_events(events) == len(events)
        expected = model._conn.execute("SELECT * FROM bound_work_unit").fetchall()

    candidate_paths = ObservationPaths.for_project(PROJECT_ID, root=tmp_path / "incremental")
    with ReadModel.open(candidate_paths) as model:
        full_replay = model._derive_bound_work_unit
        replay_count = 0

        def counted_replay(event):
            nonlocal replay_count
            replay_count += 1
            return full_replay(event)

        monkeypatch.setattr(model, "_derive_bound_work_unit", counted_replay)
        assert model.upsert_events(events) == len(events)
        assert model._conn.execute("SELECT * FROM bound_work_unit").fetchall() == expected
        assert replay_count == 1
        assert model._conn.execute("SELECT COUNT(*) FROM event_derivation").fetchone()[0] == 41


@pytest.mark.parametrize("lock_busy", [False, True])
def test_partial_query_never_reduces_or_claims_complete_coverage(tmp_path, monkeypatch, lock_busy):
    paths = ObservationPaths.for_project(PROJECT_ID, root=tmp_path)
    paths.ensure()

    def partial(*_args, **_kwargs):
        return ingest_module.IngestReport(incomplete=True, lock_timed_out=lock_busy)

    def unexpected_reduce(*_args, **_kwargs):
        pytest.fail("partial catch-up must not reduce an apparently complete summary")

    monkeypatch.setattr(ingest_module, "ingest_pending", partial)
    monkeypatch.setattr(ingest_module, "reduce_trace", unexpected_reduce)
    with pytest.raises(
        query.StateUnreadableError, match="maintenance lock busy|catch-up incomplete"
    ):
        query.load_summary(paths, TRACE_ID)
    with pytest.raises(
        query.StateUnreadableError, match="maintenance lock busy|catch-up incomplete"
    ):
        query.resolve_trace(paths, TRACE_ID)


def test_finished_catchup_does_not_keep_a_permanent_backlog_gap(tmp_path) -> None:
    paths = ObservationPaths.for_project(PROJECT_ID, root=tmp_path)
    factory = EventFactory()
    first = factory.opened(0)
    second = factory.contract(
        "contract.persisted", "completed", 1, revision=1, after_sha256="a" * 64
    )
    writer = JournalWriter(paths=paths, producer_epoch=first["producer_epoch"])
    writer.open()
    for event in (first, second):
        assert writer.append(event).accepted
    writer.close()

    partial = ingest_pending(paths, max_events=1)
    assert partial.incomplete is True
    complete = ingest_pending(paths)
    assert complete.incomplete is False
    with ReadModel.open(paths) as model:
        assert (
            model._conn.execute(
                "SELECT COUNT(*) FROM derived_diagnostic "
                "WHERE reason_code='INGEST_CATCHUP_INCOMPLETE'"
            ).fetchone()[0]
            == 0
        )


def test_incremental_checkpoints_do_not_rehash_the_entire_prefix_per_batch(tmp_path, monkeypatch):
    from test_observation_ingest_scale import _status_stream, _write_closed

    paths = _write_closed(tmp_path, _status_stream(500))
    segment_bytes = sum(path.stat().st_size for path in paths.closed.iterdir())
    original = ingest_module.sha256_hex
    hashed_bytes = 0

    def tracked_hash(payload):
        nonlocal hashed_bytes
        hashed_bytes += len(payload)
        return original(payload)

    monkeypatch.setattr(ingest_module, "sha256_hex", tracked_hash)
    assert ingest_pending(paths).events_inserted == 500
    assert hashed_bytes <= 3 * segment_bytes
