"""Aether acceptance tests for same-card implementation/review phases.

These tests pin the Hermes lifecycle behavior Aether relies on for issue #190.
They isolate inherited dispatcher routing as well as HERMES_HOME.
"""

from __future__ import annotations

import inspect
import os
from pathlib import Path

import pytest
from hermes_cli import goals
from hermes_cli import kanban_db as kb


@pytest.fixture
def isolated_board(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    # Explicit dispatcher pins outrank HERMES_HOME. Also remove task/run
    # identity so native helpers cannot attribute fixture work to a real run.
    for name in tuple(os.environ):
        if name.startswith("HERMES_KANBAN_"):
            monkeypatch.delenv(name)
    home = tmp_path / "hermes-home"
    home.mkdir()
    monkeypatch.setenv("HERMES_HOME", str(home))
    kb.init_db()
    with kb.connect_closing() as conn:
        yield conn


@pytest.mark.parametrize("selector", ["db", "board", "home", "workspaces", "all"])
def test_isolated_board_preserves_dispatcher_namespace(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, selector: str
) -> None:
    def fixture_environment() -> dict[str, str]:
        # Hermes may lazily set HERMES_QUIET while importing its CLI.
        # Compare the fixture-owned namespace and an unrelated control,
        # not the side effects of every native module loaded by the cycle.
        return {
            name: value
            for name, value in os.environ.items()
            if name.startswith("HERMES_KANBAN_") or name in {"HERMES_HOME", "AETHER_TEST_SENTINEL"}
        }

    monkeypatch.delenv("HERMES_QUIET", raising=False)
    # Never use a real inherited board even when exercising the broken fixture.
    for name in tuple(os.environ):
        if name.startswith("HERMES_KANBAN_"):
            monkeypatch.delenv(name)
    outer = tmp_path / "dispatcher"
    outer.mkdir()
    monkeypatch.setenv("HERMES_HOME", str(outer))
    outer_db = outer / "kanban.db"
    kb.init_db(db_path=outer_db)
    with kb.connect_closing(db_path=outer_db) as conn:
        kb.create_task(conn, title="dispatcher sentinel", assignee=None)
    before = {
        path.relative_to(outer): path.read_bytes() for path in outer.rglob("*") if path.is_file()
    }

    selectors = {
        "db": ("HERMES_KANBAN_DB", str(outer_db)),
        "board": ("HERMES_KANBAN_BOARD", "dispatcher-board"),
        "home": ("HERMES_KANBAN_HOME", str(outer)),
        "workspaces": ("HERMES_KANBAN_WORKSPACES_ROOT", str(outer / "workspaces")),
    }
    for key in selectors if selector == "all" else (selector,):
        name, value = selectors[key]
        monkeypatch.setenv(name, value)
    # Role/run markers must not make fixture operations impersonate the worker.
    for name, value in {
        "HERMES_KANBAN_TASK": "t_outer",
        "HERMES_KANBAN_RUN_ID": "91",
        "HERMES_KANBAN_AFFINITY_FLOW_ID": "outer-flow",
        "HERMES_KANBAN_FUTURE_FIELD": "outer-future",
    }.items():
        monkeypatch.setenv(name, value)
    monkeypatch.setenv("AETHER_TEST_SENTINEL", "preserve unrelated configuration")
    inherited = fixture_environment()

    inner = tmp_path / "fixture"
    inner.mkdir()
    with pytest.MonkeyPatch.context() as fixture_patch:
        fixture = inspect.unwrap(isolated_board)(inner, fixture_patch)
        try:
            conn = next(fixture)
            actual = Path(conn.execute("PRAGMA database_list").fetchone()[2]).resolve()
            expected_home = inner / "hermes-home"
            assert actual == (expected_home / "kanban.db").resolve()
            assert kb.workspaces_root() == expected_home / "kanban" / "workspaces"
            assert not any(name.startswith("HERMES_KANBAN_") for name in os.environ)
            assert os.environ["AETHER_TEST_SENTINEL"] == inherited["AETHER_TEST_SENTINEL"]
            test_same_card_cycle_preserves_contract_candidate_budget_and_history(conn)
            assert conn.execute("SELECT COUNT(*) FROM tasks").fetchone()[0] == 1
        finally:
            fixture.close()

    assert fixture_environment() == inherited
    after = {
        path.relative_to(outer): path.read_bytes() for path in outer.rglob("*") if path.is_file()
    }
    assert after == before


def _stable_contract(task) -> dict:
    """Fields that phase transitions must never rewrite."""
    return {
        "id": task.id,
        "title": task.title,
        "body": task.body,
        "created_by": task.created_by,
        "workspace_kind": task.workspace_kind,
        "workspace_path": task.workspace_path,
        "branch_name": task.branch_name,
        "priority": task.priority,
        "max_runtime_seconds": task.max_runtime_seconds,
        "max_retries": task.max_retries,
        "goal_mode": task.goal_mode,
        "goal_max_turns": task.goal_max_turns,
    }


def test_initial_review_requires_an_independent_reviewer(isolated_board) -> None:
    """A same-card implementer cannot leave its review run self-claimable."""
    conn = isolated_board
    task_id = kb.create_task(
        conn,
        title="Require independent review",
        body="The implementing profile must not approve its own candidate.",
        assignee="implementer",
        created_by="supervisor",
    )
    implementation = kb.claim_task(conn, task_id, claimer="implementer:1")
    assert implementation is not None

    ok, reason = kb.request_review(
        conn,
        task_id,
        summary="Implementation and focused tests are ready.",
        expected_run_id=implementation.current_run_id,
        with_reason=True,
    )

    assert ok is False
    assert reason is not None
    assert "reviewer" in reason
    task = kb.get_task(conn, task_id)
    assert task is not None
    assert task.status == "running"
    assert task.assignee == "implementer"
    assert task.current_run_id == implementation.current_run_id
    assert task.claim_lock is not None


def test_same_card_cycle_preserves_contract_candidate_budget_and_history(
    isolated_board,
) -> None:
    conn = isolated_board
    task_id = kb.create_task(
        conn,
        title="Implement guarded export",
        body="Export only validated rows and prove the fallback branch.",
        assignee="implementer",
        created_by="supervisor",
        workspace_kind="worktree",
        workspace_path="/tmp/aether-same-card-candidate",
        branch_name="aether/t_same_card",
        priority=7,
        max_runtime_seconds=900,
        max_retries=2,
        goal_mode=True,
        goal_max_turns=9,
    )
    original = kb.get_task(conn, task_id)
    assert original is not None
    stable = _stable_contract(original)

    implementation_1 = kb.claim_task(conn, task_id, claimer="implementer:1")
    assert implementation_1 is not None
    assert kb.request_review(
        conn,
        task_id,
        reviewer="supervisor",
        summary="Implementation and focused tests are ready.",
        metadata={"candidate": "abc123"},
        expected_run_id=implementation_1.current_run_id,
    )
    awaiting_review = kb.get_task(conn, task_id)
    assert awaiting_review is not None
    assert awaiting_review.status == "review"
    assert awaiting_review.assignee == "supervisor"
    assert _stable_contract(awaiting_review) == stable

    review_1 = kb.claim_review_task(conn, task_id, claimer="supervisor:1")
    assert review_1 is not None
    assert kb.request_changes(
        conn,
        task_id,
        reason="Add a regression for the fallback branch.",
        expected_run_id=review_1.current_run_id,
    ) == (True, "implementer")
    awaiting_rework = kb.get_task(conn, task_id)
    assert awaiting_rework is not None
    assert awaiting_rework.status == "ready"
    assert awaiting_rework.assignee == "implementer"
    assert _stable_contract(awaiting_rework) == stable
    assert kb.goal_run_status(conn, task_id, review_1.current_run_id) == "changes_requested"

    implementation_2 = kb.claim_task(conn, task_id, claimer="implementer:2")
    assert implementation_2 is not None
    assert kb.request_review(
        conn,
        task_id,
        summary="Fallback regression added and suite passes.",
        metadata={"candidate": "def456"},
        expected_run_id=implementation_2.current_run_id,
    )
    awaiting_rereview = kb.get_task(conn, task_id)
    assert awaiting_rereview is not None
    assert awaiting_rereview.status == "review"
    assert awaiting_rereview.assignee == "supervisor"
    assert _stable_contract(awaiting_rereview) == stable

    review_2 = kb.claim_review_task(conn, task_id, claimer="supervisor:2")
    assert review_2 is not None
    assert kb.complete_task(
        conn,
        task_id,
        summary="Approved after independent verification.",
        result="accepted",
        expected_run_id=review_2.current_run_id,
    )

    completed = kb.get_task(conn, task_id)
    assert completed is not None
    assert completed.status == "done"
    assert completed.block_recurrences == 0
    assert _stable_contract(completed) == stable

    runs = kb.list_runs(conn, task_id)
    assert [run.profile for run in runs] == [
        "implementer",
        "supervisor",
        "implementer",
        "supervisor",
    ]
    assert [run.outcome for run in runs] == [
        "review_requested",
        "changes_requested",
        "review_requested",
        "completed",
    ]
    events = kb.list_events(conn, task_id)
    event_kinds = [event.kind for event in events]
    assert event_kinds.count("review_requested") == 2
    assert event_kinds.count("changes_requested") == 1
    assert event_kinds.count("completed") == 1
    assert "blocked" not in event_kinds
    assert "block_loop_detected" not in event_kinds


@pytest.mark.parametrize(
    ("phase_status", "expected_outcome"),
    [
        ("review", "review_requested_by_worker"),
        ("changes_requested", "changes_requested_by_reviewer"),
        ("done", "completed_by_worker"),
    ],
)
def test_goal_loop_accepts_phase_terminal_handoff_before_static_judge(
    monkeypatch: pytest.MonkeyPatch,
    phase_status: str,
    expected_outcome: str,
) -> None:
    monkeypatch.setattr(
        goals,
        "judge_goal",
        lambda *args, **kwargs: pytest.fail(
            "a terminal lifecycle handoff must not be re-judged by the prior phase"
        ),
    )

    result = goals.run_kanban_goal_loop(
        task_id="t_phase",
        goal_text="static card goal",
        run_turn=lambda prompt: pytest.fail("must not spend another phase turn"),
        task_status_fn=lambda: phase_status,
        block_fn=lambda reason: pytest.fail("must not block a valid handoff"),
        first_response="Durable phase handoff recorded.",
    )

    assert result["outcome"] == expected_outcome
    assert result["turns_used"] == 1
