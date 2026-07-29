"""Contract for the before/after comparison introduced by Phase 2.

The audit's finding was not that the comparison was wrong but that it did not
exist: v0.20.0 could count activity and could not say whether anything improved.
These tests pin the refusals as hard as the results, because a machine that
reports IMPROVED when its yardstick moved is worse than one that reports
nothing.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from olympus_v3.self_improvement.causality import (
    IMPROVED,
    INCOMPLETE,
    INVALID_DIRTY_BASELINE,
    INVALID_EVALUATION_CHANGED,
    NO_CHANGE,
    REGRESSED,
    CausalityError,
    EvaluationRun,
    ImprovementTask,
    compare,
    evaluation_digest,
    load_task,
    record_evaluation_run,
    record_task,
    render_comparison,
)
from olympus_v3.self_improvement.ledger import SelfImprovementLedger

BASELINE_COMMIT = "a" * 40
CANDIDATE_COMMIT = "b" * 40


@pytest.fixture()
def ledger(tmp_path: Path) -> SelfImprovementLedger:
    return SelfImprovementLedger(tmp_path / ".aether" / "self_improvement.db")


@pytest.fixture()
def evaluation_set(tmp_path: Path) -> Path:
    root = tmp_path / "evaluation"
    (root / "cases").mkdir(parents=True)
    (root / "cases" / "case_one.txt").write_text("first expected outcome\n", encoding="utf-8")
    (root / "cases" / "case_two.txt").write_text("second expected outcome\n", encoding="utf-8")
    return root


def _task(digest: str, *, dirty: str = "clean") -> ImprovementTask:
    return ImprovementTask(
        task_id="task-1",
        statement="Reduce dispatch failures on the bounded coordination path.",
        acceptance_criterion="No regression on the frozen set and at least one fewer failure.",
        baseline_commit=BASELINE_COMMIT,
        baseline_dirty_digest=dirty,
        evaluation_digest=digest,
    )


def _run(phase: str, digest: str, *, passed: int, failed: int, metric: float | None = None) -> EvaluationRun:
    return EvaluationRun(
        task_id="task-1",
        phase=phase,
        commit_id=BASELINE_COMMIT if phase == "baseline" else CANDIDATE_COMMIT,
        evaluation_digest=digest,
        passed=passed,
        failed=failed,
        metric=metric,
    )


# --------------------------------------------------------------------------
# The frozen evaluation set
# --------------------------------------------------------------------------


def test_digest_is_stable_and_content_addressed(evaluation_set: Path) -> None:
    first = evaluation_digest([evaluation_set])

    assert first == evaluation_digest([evaluation_set])

    (evaluation_set / "cases" / "case_two.txt").write_text("moved goalpost\n", encoding="utf-8")

    assert evaluation_digest([evaluation_set]) != first


def test_digest_notices_an_added_or_removed_case(evaluation_set: Path) -> None:
    before = evaluation_digest([evaluation_set])
    (evaluation_set / "cases" / "case_three.txt").write_text("third\n", encoding="utf-8")
    added = evaluation_digest([evaluation_set])
    (evaluation_set / "cases" / "case_three.txt").unlink()

    assert added != before
    assert evaluation_digest([evaluation_set]) == before


def test_missing_or_empty_evaluation_set_fails_loudly(tmp_path: Path) -> None:
    with pytest.raises(CausalityError, match="cannot be empty"):
        evaluation_digest([])
    with pytest.raises(CausalityError, match="does not exist"):
        evaluation_digest([tmp_path / "absent"])


# --------------------------------------------------------------------------
# The task is fixed before the change
# --------------------------------------------------------------------------


def test_a_task_needs_a_statement_and_a_criterion(ledger: SelfImprovementLedger, evaluation_set: Path) -> None:
    digest = evaluation_digest([evaluation_set])
    task = ImprovementTask("task-1", "  ", "criterion", BASELINE_COMMIT, "clean", digest)

    with pytest.raises(CausalityError, match="statement and an acceptance criterion"):
        record_task(ledger, task)


def test_a_criterion_cannot_be_redefined_after_the_fact(
    ledger: SelfImprovementLedger, evaluation_set: Path
) -> None:
    """Rewriting success once the result is known is the failure mode the whole
    cycle exists to prevent."""

    digest = evaluation_digest([evaluation_set])
    record_task(ledger, _task(digest))
    relaxed = ImprovementTask(
        task_id="task-1",
        statement="Reduce dispatch failures on the bounded coordination path.",
        acceptance_criterion="Any outcome is fine, actually.",
        baseline_commit=BASELINE_COMMIT,
        baseline_dirty_digest="clean",
        evaluation_digest=digest,
    )

    with pytest.raises(CausalityError, match="cannot be redefined"):
        record_task(ledger, relaxed)


def test_recording_the_same_task_twice_is_idempotent(
    ledger: SelfImprovementLedger, evaluation_set: Path
) -> None:
    digest = evaluation_digest([evaluation_set])
    record_task(ledger, _task(digest))
    record_task(ledger, _task(digest))

    assert load_task(ledger, "task-1").acceptance_criterion.startswith("No regression")


def test_a_phase_is_measured_once(ledger: SelfImprovementLedger, evaluation_set: Path) -> None:
    """Re-measuring until the answer is favourable is refused."""

    digest = evaluation_digest([evaluation_set])
    record_task(ledger, _task(digest))
    record_evaluation_run(ledger, _run("baseline", digest, passed=10, failed=2))

    with pytest.raises(CausalityError, match="already measured"):
        record_evaluation_run(ledger, _run("baseline", digest, passed=12, failed=0))


# --------------------------------------------------------------------------
# Refusals — these matter more than the results
# --------------------------------------------------------------------------


def test_a_moved_yardstick_invalidates_the_comparison(
    ledger: SelfImprovementLedger, evaluation_set: Path
) -> None:
    """The anti-F-05 rule: if the evaluation set changed between baseline and
    candidate, the verdict is INVALID, never IMPROVED."""

    fixed = evaluation_digest([evaluation_set])
    record_task(ledger, _task(fixed))
    record_evaluation_run(ledger, _run("baseline", fixed, passed=10, failed=5))

    (evaluation_set / "cases" / "case_two.txt").write_text("easier case\n", encoding="utf-8")
    moved = evaluation_digest([evaluation_set])
    record_evaluation_run(ledger, _run("candidate", moved, passed=15, failed=0))

    comparison = compare(ledger, "task-1")

    assert comparison.verdict == INVALID_EVALUATION_CHANGED
    assert comparison.supports_a_causal_claim is False


def test_a_dirty_baseline_invalidates_attribution(
    ledger: SelfImprovementLedger, evaluation_set: Path
) -> None:
    digest = evaluation_digest([evaluation_set])
    record_task(ledger, _task(digest, dirty="dirty:7:sha256:" + "0" * 64))
    record_evaluation_run(ledger, _run("baseline", digest, passed=10, failed=5))
    record_evaluation_run(ledger, _run("candidate", digest, passed=15, failed=0))

    comparison = compare(ledger, "task-1")

    assert comparison.verdict == INVALID_DIRTY_BASELINE
    assert comparison.supports_a_causal_claim is False


def test_one_measurement_is_not_a_comparison(ledger: SelfImprovementLedger, evaluation_set: Path) -> None:
    digest = evaluation_digest([evaluation_set])
    record_task(ledger, _task(digest))
    record_evaluation_run(ledger, _run("baseline", digest, passed=10, failed=5))

    comparison = compare(ledger, "task-1")

    assert comparison.verdict == INCOMPLETE
    assert comparison.supports_a_causal_claim is False


def test_an_unknown_task_cannot_be_compared(ledger: SelfImprovementLedger) -> None:
    with pytest.raises(CausalityError, match="unknown task"):
        compare(ledger, "never-recorded")


# --------------------------------------------------------------------------
# Results
# --------------------------------------------------------------------------


def test_fewer_failures_is_an_improvement(ledger: SelfImprovementLedger, evaluation_set: Path) -> None:
    digest = evaluation_digest([evaluation_set])
    record_task(ledger, _task(digest))
    record_evaluation_run(ledger, _run("baseline", digest, passed=10, failed=5))
    record_evaluation_run(ledger, _run("candidate", digest, passed=14, failed=1))

    comparison = compare(ledger, "task-1")

    assert comparison.verdict == IMPROVED
    assert comparison.supports_a_causal_claim is True


def test_more_failures_is_a_regression(ledger: SelfImprovementLedger, evaluation_set: Path) -> None:
    digest = evaluation_digest([evaluation_set])
    record_task(ledger, _task(digest))
    record_evaluation_run(ledger, _run("baseline", digest, passed=14, failed=1))
    record_evaluation_run(ledger, _run("candidate", digest, passed=10, failed=5))

    assert compare(ledger, "task-1").verdict == REGRESSED


def test_identical_measurements_are_not_an_improvement(
    ledger: SelfImprovementLedger, evaluation_set: Path
) -> None:
    digest = evaluation_digest([evaluation_set])
    record_task(ledger, _task(digest))
    record_evaluation_run(ledger, _run("baseline", digest, passed=12, failed=3))
    record_evaluation_run(ledger, _run("candidate", digest, passed=12, failed=3))

    assert compare(ledger, "task-1").verdict == NO_CHANGE


def test_a_metric_breaks_the_tie_in_the_declared_direction(
    ledger: SelfImprovementLedger, evaluation_set: Path
) -> None:
    digest = evaluation_digest([evaluation_set])
    record_task(ledger, _task(digest))
    record_evaluation_run(ledger, _run("baseline", digest, passed=12, failed=3, metric=180.0))
    record_evaluation_run(ledger, _run("candidate", digest, passed=12, failed=3, metric=120.0))

    assert compare(ledger, "task-1", higher_metric_is_better=False).verdict == IMPROVED
    assert compare(ledger, "task-1", higher_metric_is_better=True).verdict == REGRESSED


# --------------------------------------------------------------------------
# The projection never promotes
# --------------------------------------------------------------------------


def test_the_rendered_comparison_refuses_to_accept_the_candidate(
    ledger: SelfImprovementLedger, evaluation_set: Path
) -> None:
    digest = evaluation_digest([evaluation_set])
    record_task(ledger, _task(digest))
    record_evaluation_run(ledger, _run("baseline", digest, passed=10, failed=5))
    record_evaluation_run(ledger, _run("candidate", digest, passed=14, failed=1))

    rendered = render_comparison(compare(ledger, "task-1"), load_task(ledger, "task-1"))

    assert "Verdict: `IMPROVED`" in rendered
    assert "does not accept, promote, merge, tag or release the candidate" in rendered
    assert "Promotion remains a separate product-owner decision." in rendered
    assert "No regression on the frozen set" in rendered
