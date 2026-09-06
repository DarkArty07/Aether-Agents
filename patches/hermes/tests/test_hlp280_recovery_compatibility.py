"""Recovery compatibility checks; uses the same isolated real-DB fixture."""

import importlib.util
import sqlite3
import threading
from pathlib import Path

import pytest

_spec = importlib.util.spec_from_file_location(
    "source_probe", Path(__file__).with_name("test_hlp280_live_routing_probe.py")
)
assert _spec is not None and _spec.loader is not None
_probe = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_probe)
flow = _probe.flow
topology = _probe.topology
origin_events = _probe.origin_events


def test_non_flow_block_is_not_escalated(flow):
    kb, conn, task, _ = flow
    legacy = task("legacy", "implementer")
    assert kb.claim_task(conn, legacy)
    assert kb.block_task(conn, legacy, kind="needs_input", reason="legacy")
    assert not any(e.kind == "origin_signal" for e in kb.list_events(conn, legacy))


def test_stale_run_cannot_block_or_signal(flow):
    kb, conn, _, root = flow
    assert kb.claim_task(conn, root)
    before = list(conn.iterdump())
    assert not kb.block_task(conn, root, kind="needs_input", reason="stale", expected_run_id=999999)
    assert list(conn.iterdump()) == before


def test_new_run_can_signal_again(flow):
    kb, conn, _, root = flow
    for iteration in range(2):
        assert kb.claim_task(conn, root)
        assert kb.block_task(conn, root, kind="needs_input", reason="missing choice")
        if iteration == 0:
            assert kb.unblock_task(conn, root)
    # The second recurrence intentionally lands in triage, with a fresh signal.
    assert len(origin_events(kb, conn, root)) == 2


@pytest.mark.parametrize("status", ["scheduled", "blocked", "triage"])
def test_unavailable_controller_never_swallows_blocker(flow, status):
    kb, conn, unit, controller = topology(flow)
    with kb.write_txn(conn):
        conn.execute("UPDATE tasks SET status=? WHERE id=?", (status, controller))
    assert kb.block_task(conn, unit, kind="needs_input", reason="owner choice")
    if status == "scheduled":
        assert kb.get_task(conn, controller).status == "ready"
        assert kb.claim_task(conn, controller)
    else:
        assert len(origin_events(kb, conn, unit)) == 1
        assert kb.get_task(conn, controller).status == status


@pytest.mark.parametrize("automatic", [False, True])
def test_failure_during_attention_requeue_rolls_back_whole_transition(flow, automatic):
    kb, conn, unit, controller = topology(flow)
    conn.execute(
        "CREATE TEMP TRIGGER reject_promotion BEFORE UPDATE OF status ON tasks "
        "WHEN NEW.status='ready' BEGIN SELECT RAISE(ABORT,'injected promotion failure'); END"
    )
    before = list(conn.iterdump())
    with pytest.raises(sqlite3.IntegrityError, match="injected promotion failure"):
        if automatic:
            kb._record_task_failure(
                conn,
                unit,
                "spawn failed",
                outcome="spawn_failed",
                failure_limit=1,
                release_claim=True,
                end_run=True,
            )
        else:
            kb.block_task(conn, unit, kind="capability", reason="failed locally")
    assert list(conn.iterdump()) == before
    assert kb.get_task(conn, unit).status == "running"
    assert kb._pending_flow_attentions(conn, controller) == []


def test_two_dispatchers_do_not_duplicate_terminal_event(flow):
    kb, conn, _, root = flow
    dbfile = conn.execute("PRAGMA database_list").fetchone()[2]
    barrier = threading.Barrier(2)
    errors = []

    def worker():
        c = kb.connect(db_path=Path(dbfile))
        try:
            barrier.wait(timeout=5)
            kb._route_affinity_terminal(c, root, reason="same failure")
        except Exception as exc:
            errors.append(repr(exc))
        finally:
            c.close()

    workers = [threading.Thread(target=worker) for _ in range(2)]
    for thread in workers:
        thread.start()
    for thread in workers:
        thread.join(timeout=10)
    assert not any(t.is_alive() for t in workers)
    assert errors == []
    assert len([e for e in kb.list_events(conn, root) if e.kind == "flow_terminal"]) == 1
    assert kb.list_events(conn, root)[-1].kind == "flow_terminal"


def test_expiry_dedupes_without_killing_controller(flow, monkeypatch):
    import time

    kb, conn, unit, controller = topology(flow)
    assert kb.block_task(conn, unit, kind="capability", reason="cannot recover yet")
    assert kb.claim_task(conn, controller)
    now = int(time.time())
    monkeypatch.setattr(kb.time, "time", lambda: now + 299)
    kb._escalate_expired_flow_attentions(conn)
    assert origin_events(kb, conn, controller) == []
    monkeypatch.setattr(kb.time, "time", lambda: now + 300)
    for _ in range(3):
        kb._escalate_expired_flow_attentions(conn)
    assert len(origin_events(kb, conn, controller)) == 1
    assert kb.get_task(conn, controller).status == "running"
    assert kb.block_task(conn, controller, kind="dependency", reason="recovered")
    assert kb.get_task(conn, unit).status == "ready"
    kb._escalate_expired_flow_attentions(conn)
    assert len(origin_events(kb, conn, controller)) == 1
