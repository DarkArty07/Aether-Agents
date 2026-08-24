"""Aether acceptance tests for same-card implementation/review phases.

These tests pin the Hermes lifecycle behavior Aether relies on for issue #190.
They use an isolated HERMES_HOME and never touch the real board.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from hermes_cli import goals
from hermes_cli import kanban_db as kb


@pytest.fixture
def isolated_board(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    home = tmp_path / "hermes-home"
    home.mkdir()
    monkeypatch.setenv("HERMES_HOME", str(home))
    kb.init_db()
    with kb.connect_closing() as conn:
        yield conn


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
