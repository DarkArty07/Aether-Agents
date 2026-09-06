"""Read-only source qualification for #280; all state lives in pytest tmp_path."""

import sqlite3
from pathlib import Path

import pytest


@pytest.fixture
def flow(tmp_path, monkeypatch):
    # The caller also launches with an isolated home before importing Hermes.
    for key in list(__import__("os").environ):
        if key.startswith("HERMES_KANBAN_"):
            monkeypatch.delenv(key, raising=False)
    monkeypatch.setenv("HERMES_HOME", str(tmp_path / "home"))
    monkeypatch.setenv("HERMES_KANBAN_HOME", str(tmp_path / "boards"))
    from hermes_cli import kanban_db as kb
    from hermes_cli import lifecycle, projects_db

    # Observers are unrelated to the routing under test; don't notify real plugins.
    monkeypatch.setattr(lifecycle, "invoke_hook", lambda *args, **kwargs: None)
    original_connect = sqlite3.connect

    def isolated_connect(database, *args, **kwargs):
        if str(database) != ":memory:":
            assert Path(str(database)).resolve().is_relative_to(tmp_path.resolve()), database
        return original_connect(database, *args, **kwargs)

    monkeypatch.setattr(sqlite3, "connect", isolated_connect)
    with projects_db.connect_closing() as pc:
        project = projects_db.create_project(pc, name="Disposable flow", primary_path=str(tmp_path))
    conn = kb.connect(db_path=tmp_path / "flow.db")

    def task(title, who, parents=(), affinity=None, session="supervisor-session"):
        return kb.create_task(
            conn,
            title=title,
            assignee=who,
            project_id=project,
            parents=parents,
            session_id=session,
            workspace_kind="dir",
            workspace_path=str(tmp_path),
            session_affinity=affinity,
        )

    root = task(
        "root", "supervisor", affinity={"flow_id": "disposable-flow"}, session="exact-origin"
    )
    kb.add_notify_sub(conn, task_id=root, platform="tui", chat_id="exact-origin")
    yield kb, conn, task, root
    conn.close()


def topology(flow):
    kb, conn, task, root = flow
    assert kb.claim_task(conn, root)
    assert kb.complete_task(conn, root)
    unit = task("unit", "implementer", parents=(root,))
    controller = task(
        "controller",
        "supervisor",
        parents=(root, unit),
        affinity={"flow_id": "disposable-flow", "terminal": True},
    )
    assert kb.claim_task(conn, unit)
    return kb, conn, unit, controller


def origin_events(kb, conn, controller):
    _, events = kb.unseen_events_for_sub(
        conn,
        task_id=controller,
        platform="tui",
        chat_id="exact-origin",
        kinds=("origin_signal", "flow_terminal"),
    )
    return events


def test_repairable_child_stays_internal_and_resumes(flow):
    kb, conn, unit, controller = topology(flow)
    assert kb.block_task(conn, unit, kind="capability", reason="repairable local error")
    assert kb.get_task(conn, controller).status == "ready"
    assert origin_events(kb, conn, controller) == []
    assert kb.claim_task(conn, controller)
    assert kb.block_task(conn, controller, kind="dependency", reason="resolved; retry unit")
    assert kb.get_task(conn, unit).status == "ready"
    assert origin_events(kb, conn, controller) == []


def test_controller_needs_input_without_explicit_signal_reaches_origin(flow):
    kb, conn, unit, controller = topology(flow)
    assert kb.block_task(conn, unit, kind="needs_input", reason="missing owner decision")
    assert origin_events(kb, conn, controller) == []
    assert kb.claim_task(conn, controller)
    assert kb.block_task(conn, controller, kind="needs_input", reason="owner decision required")
    events = origin_events(kb, conn, controller)
    assert len(events) == 1, "Both tasks are blocked, but no event can reach origin"
    assert events[0].payload["origin_signal"] == "input"


def test_exhausted_non_affinity_child_routes_to_controller(flow):
    kb, conn, unit, controller = topology(flow)
    assert kb._record_task_failure(
        conn,
        unit,
        "spawn failed",
        outcome="spawn_failed",
        failure_limit=1,
        release_claim=True,
        end_run=True,
    )
    # These are the two actual calls used by the current dispatcher failure path.
    kb._route_affinity_terminal(conn, unit, reason="spawn failed", outcome="failed")
    assert kb.get_task(conn, controller).status == "ready", "Controller remains parent-gated"
    assert kb._pending_flow_attentions(conn, controller), "Failure never enters recovery routing"
    assert origin_events(kb, conn, controller) == []


def test_root_block_before_controller_has_origin_signal(flow):
    kb, conn, _, root = flow
    assert kb.claim_task(conn, root)
    assert kb.block_task(conn, root, kind="needs_input", reason="root cannot decompose")
    assert len(origin_events(kb, conn, root)) == 1, "Bootstrap root blocks silently"


def test_pending_attention_cannot_be_kept_silent_by_heartbeats(flow, monkeypatch):
    import os
    import time

    kb, conn, unit, controller = topology(flow)
    assert kb.block_task(conn, unit, kind="needs_input", reason="decision unresolved")
    assert kb.claim_task(conn, controller)
    kb._set_worker_pid(conn, controller, os.getpid())
    future = time.time() + 301
    monkeypatch.setattr(kb.time, "time", lambda: future)
    # The process is alive and refreshes its lease, but has not resolved the attention.
    assert kb.heartbeat_claim(conn, controller)
    assert kb.heartbeat_worker(conn, controller)

    def forbidden_spawn(*args, **kwargs):
        raise AssertionError("Qualification must not spawn any worker")

    result = kb.dispatch_once(conn, spawn_fn=forbidden_spawn, max_spawn=0)
    assert not result.spawned
    assert kb.get_task(conn, controller).status == "running"
    assert origin_events(kb, conn, controller), (
        "Heartbeat-only controller has no bounded escalation"
    )
