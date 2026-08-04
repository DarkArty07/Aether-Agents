"""Contract for disposable candidates and the promotion gate (Phase 3).

The audit found that a candidate was built in the tree that was simultaneously
its own baseline and its own evaluator, with no rollback, and that nothing
separated evidence from adoption. These tests pin both halves: a candidate
leaves no trace in the baseline, and promotion refuses every verdict that is not
a supported improvement approved by a named person.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from aether_agents.self_improvement.causality import (
    INCOMPLETE,
    INVALID_EVALUATION_CHANGED,
    NO_CHANGE,
    REGRESSED,
    Comparison,
    EvaluationRun,
    ImprovementTask,
    compare,
    record_evaluation_run,
    record_task,
)
from aether_agents.self_improvement.ledger import SelfImprovementLedger
from aether_agents.self_improvement.promotion import (
    CandidateWorktreeError,
    PromotionRefused,
    disposable_candidate,
    promote,
    promotion_for,
)

DIGEST = "sha256:" + "c" * 64
BASELINE_COMMIT = "a" * 40
CANDIDATE_COMMIT = "b" * 40


@pytest.fixture()
def ledger(tmp_path: Path) -> SelfImprovementLedger:
    return SelfImprovementLedger(tmp_path / ".aether" / "self_improvement.db")


def _git(*args: str, cwd: Path) -> str:
    return subprocess.run(
        ["git", *args], cwd=str(cwd), capture_output=True, text=True, check=True
    ).stdout.strip()


@pytest.fixture()
def repository(tmp_path: Path) -> Path:
    root = tmp_path / "repo"
    root.mkdir()
    _git("init", "-q", "-b", "main", cwd=root)
    _git("config", "user.email", "owner@example.invalid", cwd=root)
    _git("config", "user.name", "owner", cwd=root)
    (root / "tracked.txt").write_text("baseline\n", encoding="utf-8")
    _git("add", "tracked.txt", cwd=root)
    _git("commit", "-qm", "baseline", cwd=root)
    return root


def _improved(ledger: SelfImprovementLedger) -> Comparison:
    record_task(
        ledger,
        ImprovementTask("task-1", "statement", "criterion", BASELINE_COMMIT, "clean", DIGEST),
    )
    record_evaluation_run(
        ledger, EvaluationRun("task-1", "baseline", BASELINE_COMMIT, DIGEST, passed=10, failed=5)
    )
    record_evaluation_run(
        ledger, EvaluationRun("task-1", "candidate", CANDIDATE_COMMIT, DIGEST, passed=14, failed=1)
    )
    return compare(ledger, "task-1")


# --------------------------------------------------------------------------
# Rollback is structural, not a procedure that can be forgotten
# --------------------------------------------------------------------------


def test_a_candidate_leaves_no_trace_in_the_baseline(repository: Path) -> None:
    head_before = _git("rev-parse", "HEAD", cwd=repository)

    with disposable_candidate(repository, "HEAD") as candidate:
        (candidate / "tracked.txt").write_text("candidate rewrote this\n", encoding="utf-8")
        (candidate / "invented.txt").write_text("and added this\n", encoding="utf-8")
        assert (candidate / "tracked.txt").read_text(encoding="utf-8") == "candidate rewrote this\n"
        candidate_path = candidate

    assert not candidate_path.exists()
    assert (repository / "tracked.txt").read_text(encoding="utf-8") == "baseline\n"
    assert not (repository / "invented.txt").exists()
    assert _git("rev-parse", "HEAD", cwd=repository) == head_before
    assert _git("status", "--porcelain", cwd=repository) == ""


def test_a_failing_candidate_is_discarded_just_the_same(repository: Path) -> None:
    """The candidate that made things worse is exactly the one that must not
    survive, so discarding cannot depend on a clean exit."""

    with pytest.raises(RuntimeError, match="candidate blew up"):
        with disposable_candidate(repository, "HEAD") as candidate:
            (candidate / "tracked.txt").write_text("half-finished damage\n", encoding="utf-8")
            raise RuntimeError("candidate blew up")

    assert (repository / "tracked.txt").read_text(encoding="utf-8") == "baseline\n"
    assert _git("status", "--porcelain", cwd=repository) == ""
    # The repository itself is the only worktree left registered.
    assert len(_git("worktree", "list", cwd=repository).splitlines()) == 1


def test_an_unknown_base_commit_fails_loudly(repository: Path) -> None:
    with pytest.raises(CandidateWorktreeError):
        with disposable_candidate(repository, "d" * 40):
            pytest.fail("a candidate must not be yielded for an unknown base")


# --------------------------------------------------------------------------
# Evaluation never promotes
# --------------------------------------------------------------------------


def test_an_improved_candidate_can_be_adopted_by_a_named_person(ledger: SelfImprovementLedger) -> None:
    promotion = promote(
        ledger,
        _improved(ledger),
        approved_by="Christopher (product owner)",
        approval_note="Fewer failures on the frozen set and no regression.",
        promoted_commit=CANDIDATE_COMMIT,
    )

    assert promotion.approved_by == "Christopher (product owner)"
    assert promotion_for(ledger, "task-1") == promotion


@pytest.mark.parametrize("verdict", [INCOMPLETE, INVALID_EVALUATION_CHANGED, REGRESSED, NO_CHANGE])
def test_promotion_refuses_every_unsupported_verdict(ledger: SelfImprovementLedger, verdict: str) -> None:
    comparison = Comparison(task_id="task-1", verdict=verdict, reason="fixture", baseline=None, candidate=None)

    with pytest.raises(PromotionRefused):
        promote(
            ledger,
            comparison,
            approved_by="Christopher",
            approval_note="looks fine to me",
            promoted_commit=CANDIDATE_COMMIT,
        )

    assert promotion_for(ledger, "task-1") is None


def test_promotion_refuses_an_unnamed_approver(ledger: SelfImprovementLedger) -> None:
    comparison = _improved(ledger)

    with pytest.raises(PromotionRefused, match="named approver and a stated reason"):
        promote(ledger, comparison, approved_by="   ", approval_note="ok", promoted_commit=CANDIDATE_COMMIT)
    with pytest.raises(PromotionRefused, match="named approver and a stated reason"):
        promote(ledger, comparison, approved_by="Christopher", approval_note="", promoted_commit=CANDIDATE_COMMIT)

    assert promotion_for(ledger, "task-1") is None


def test_a_promotion_cannot_be_quietly_restated(ledger: SelfImprovementLedger) -> None:
    comparison = _improved(ledger)
    promote(
        ledger,
        comparison,
        approved_by="Christopher",
        approval_note="original reason",
        promoted_commit=CANDIDATE_COMMIT,
    )

    with pytest.raises(PromotionRefused, match="already promoted"):
        promote(
            ledger,
            comparison,
            approved_by="somebody else",
            approval_note="revised reason",
            promoted_commit="e" * 40,
        )

    assert promotion_for(ledger, "task-1").approval_note == "original reason"
