"""Deterministic before/after comparison for a bounded improvement attempt.

The v0.20.0 external logic audit found that the increment could record what a
session did but could not express whether anything got *better*: no task, no
acceptance criterion, no baseline measurement, no candidate measurement, no
comparison, no rollback. Counting tool calls is activity, not improvement.

This module supplies the smallest machinery that makes a causal claim possible,
and refuses to make one when the preconditions are absent:

* a **task record** written *before* the change, carrying the owner's statement
  and acceptance criterion, the baseline commit and its dirty digest, and the
  digest of the evaluation set;
* an **evaluation digest** over a frozen set of files, so a comparison whose
  yardstick moved is rejected rather than reported;
* **two evaluation runs** — baseline and candidate — measured with that same
  yardstick;
* a **deterministic verdict** derived from those facts alone.

Two properties are deliberate. The verdict never promotes: `IMPROVED` means the
evidence supports the claim, not that the change is accepted, and promotion
stays a separate owner decision. And the module never decides *what* to measure;
the task statement, the acceptance criterion and the evaluation set are data the
product owner supplies, because which task distribution matters is a product
question this code has no standing to answer.
"""

from __future__ import annotations

import hashlib
import sqlite3
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from olympus_v3.self_improvement.ledger import SelfImprovementLedger

# Verdicts that refuse to compare, because a precondition failed.
INVALID_EVALUATION_CHANGED = "INVALID_EVALUATION_CHANGED"
INVALID_DIRTY_BASELINE = "INVALID_DIRTY_BASELINE"
INCOMPLETE = "INCOMPLETE"
# Verdicts that report a comparison.
REGRESSED = "REGRESSED"
NO_CHANGE = "NO_CHANGE"
IMPROVED = "IMPROVED"


class CausalityError(ValueError):
    """A task or evaluation run violates the comparison contract."""


@dataclass(frozen=True)
class ImprovementTask:
    task_id: str
    statement: str
    acceptance_criterion: str
    baseline_commit: str
    baseline_dirty_digest: str
    evaluation_digest: str


@dataclass(frozen=True)
class EvaluationRun:
    task_id: str
    phase: str
    commit_id: str
    evaluation_digest: str
    passed: int
    failed: int
    metric: float | None = None
    duration_ms: int | None = None


@dataclass(frozen=True)
class Comparison:
    """The full basis for a verdict, so a third party can re-derive it."""

    task_id: str
    verdict: str
    reason: str
    baseline: EvaluationRun | None
    candidate: EvaluationRun | None

    @property
    def supports_a_causal_claim(self) -> bool:
        return self.verdict in {REGRESSED, NO_CHANGE, IMPROVED}


def evaluation_digest(paths: Iterable[Path]) -> str:
    """Digest a frozen evaluation set by relative path and content.

    The digest is the mechanism that stops the candidate from grading itself
    against a yardstick it moved. Directories are walked deterministically, and
    a missing entry fails loudly rather than silently changing the digest.
    """

    entries: list[tuple[str, str]] = []
    roots = [Path(p).expanduser().resolve() for p in paths]
    if not roots:
        raise CausalityError("an evaluation set cannot be empty")
    for root in roots:
        if root.is_file():
            files = [root]
            base = root.parent
        elif root.is_dir():
            files = sorted(item for item in root.rglob("*") if item.is_file())
            base = root
        else:
            raise CausalityError(f"evaluation set entry does not exist: {root}")
        for item in files:
            digest = hashlib.sha256(item.read_bytes()).hexdigest()
            entries.append((str(item.relative_to(base)), digest))
    canonical = "\n".join(f"{name}:{digest}" for name, digest in sorted(entries))
    return "sha256:" + hashlib.sha256(canonical.encode()).hexdigest()


def _connect(ledger: SelfImprovementLedger) -> sqlite3.Connection:
    ledger.ensure_schema()
    connection = sqlite3.connect(str(ledger.path), timeout=5.0)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    connection.execute("PRAGMA busy_timeout = 5000")
    return connection


def record_task(ledger: SelfImprovementLedger, task: ImprovementTask) -> None:
    """Write the task once.

    A task is immutable. Its acceptance criterion has to predate the change it
    judges, so redefining the criterion once the result is known is refused.
    """

    if not task.statement.strip() or not task.acceptance_criterion.strip():
        raise CausalityError("a task needs a statement and an acceptance criterion")
    with _connect(ledger) as connection:
        existing = connection.execute(
            "SELECT statement, acceptance_criterion, evaluation_digest FROM improvement_tasks WHERE task_id = ?",
            (task.task_id,),
        ).fetchone()
        if existing is not None:
            if (
                str(existing["statement"]) != task.statement
                or str(existing["acceptance_criterion"]) != task.acceptance_criterion
                or str(existing["evaluation_digest"]) != task.evaluation_digest
            ):
                raise CausalityError(
                    f"task {task.task_id!r} already exists with a different statement, criterion or "
                    "evaluation set; a criterion cannot be redefined after the result is known"
                )
            return
        connection.execute(
            """
            INSERT INTO improvement_tasks (
                task_id, statement, acceptance_criterion, baseline_commit,
                baseline_dirty_digest, evaluation_digest, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                task.task_id,
                task.statement,
                task.acceptance_criterion,
                task.baseline_commit,
                task.baseline_dirty_digest,
                task.evaluation_digest,
                time.time(),
            ),
        )


def record_evaluation_run(ledger: SelfImprovementLedger, run: EvaluationRun) -> None:
    """Write one measurement.

    A phase is measured once and cannot be replaced. Re-measuring until the
    answer is favourable is the failure this prevents.
    """

    if run.phase not in {"baseline", "candidate"}:
        raise CausalityError("phase must be baseline or candidate")
    with _connect(ledger) as connection:
        cursor = connection.execute(
            """
            INSERT OR IGNORE INTO evaluation_runs (
                task_id, phase, commit_id, evaluation_digest,
                passed, failed, metric, duration_ms, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                run.task_id,
                run.phase,
                run.commit_id,
                run.evaluation_digest,
                int(run.passed),
                int(run.failed),
                float(run.metric) if run.metric is not None else None,
                int(run.duration_ms) if run.duration_ms is not None else None,
                time.time(),
            ),
        )
        if cursor.rowcount != 1:
            raise CausalityError(
                f"{run.phase} for task {run.task_id!r} is already measured; a phase is measured once"
            )


def _row_to_run(row: sqlite3.Row) -> EvaluationRun:
    return EvaluationRun(
        task_id=str(row["task_id"]),
        phase=str(row["phase"]),
        commit_id=str(row["commit_id"]),
        evaluation_digest=str(row["evaluation_digest"]),
        passed=int(row["passed"]),
        failed=int(row["failed"]),
        metric=row["metric"],
        duration_ms=row["duration_ms"],
    )


def load_task(ledger: SelfImprovementLedger, task_id: str) -> ImprovementTask:
    with _connect(ledger) as connection:
        row = connection.execute("SELECT * FROM improvement_tasks WHERE task_id = ?", (task_id,)).fetchone()
    if row is None:
        raise CausalityError(f"unknown task {task_id!r}")
    return ImprovementTask(
        task_id=str(row["task_id"]),
        statement=str(row["statement"]),
        acceptance_criterion=str(row["acceptance_criterion"]),
        baseline_commit=str(row["baseline_commit"]),
        baseline_dirty_digest=str(row["baseline_dirty_digest"]),
        evaluation_digest=str(row["evaluation_digest"]),
    )


def compare(ledger: SelfImprovementLedger, task_id: str, *, higher_metric_is_better: bool = True) -> Comparison:
    """Derive a verdict from recorded facts alone.

    Preconditions are checked before any comparison, and a failed precondition
    yields a refusal rather than a result. In particular both runs must carry the
    evaluation digest fixed when the task was written: a candidate that moved the
    yardstick produces `INVALID_EVALUATION_CHANGED`, never `IMPROVED`.
    """

    with _connect(ledger) as connection:
        task_row = connection.execute(
            "SELECT evaluation_digest, baseline_dirty_digest FROM improvement_tasks WHERE task_id = ?",
            (task_id,),
        ).fetchone()
        if task_row is None:
            raise CausalityError(f"unknown task {task_id!r}")
        runs = {
            str(row["phase"]): _row_to_run(row)
            for row in connection.execute(
                "SELECT * FROM evaluation_runs WHERE task_id = ?", (task_id,)
            ).fetchall()
        }

    baseline = runs.get("baseline")
    candidate = runs.get("candidate")
    expected = str(task_row["evaluation_digest"])

    def result(verdict: str, reason: str) -> Comparison:
        return Comparison(task_id=task_id, verdict=verdict, reason=reason, baseline=baseline, candidate=candidate)

    if baseline is None or candidate is None:
        missing = "baseline" if baseline is None else "candidate"
        return result(INCOMPLETE, f"the {missing} measurement is missing")

    for run in (baseline, candidate):
        if run.evaluation_digest != expected:
            return result(
                INVALID_EVALUATION_CHANGED,
                f"the {run.phase} run used evaluation set {run.evaluation_digest} "
                f"but the task fixed {expected}",
            )

    dirty = str(task_row["baseline_dirty_digest"])
    if dirty != "clean":
        return result(
            INVALID_DIRTY_BASELINE,
            f"the baseline worktree was not clean ({dirty}), so the change cannot be attributed",
        )

    if candidate.failed > baseline.failed:
        return result(REGRESSED, f"failures rose from {baseline.failed} to {candidate.failed}")
    if candidate.failed < baseline.failed:
        return result(IMPROVED, f"failures fell from {baseline.failed} to {candidate.failed}")

    if baseline.metric is not None and candidate.metric is not None:
        if candidate.metric == baseline.metric:
            return result(NO_CHANGE, f"failures and metric are unchanged at {baseline.metric}")
        better = candidate.metric > baseline.metric if higher_metric_is_better else candidate.metric < baseline.metric
        direction = "rose" if candidate.metric > baseline.metric else "fell"
        return result(
            IMPROVED if better else REGRESSED,
            f"failures are unchanged and the metric {direction} from {baseline.metric} to {candidate.metric}",
        )

    return result(NO_CHANGE, f"failures are unchanged at {baseline.failed} and no metric was recorded")


def render_comparison(comparison: Comparison, task: ImprovementTask) -> str:
    """Render the comparison so a third party can audit the claim.

    States explicitly that the verdict is not an acceptance: promotion is a
    separate owner decision and this projection has no authority to grant it.
    """

    lines = [
        f"# Improvement comparison — {comparison.task_id}",
        "",
        f"- Verdict: `{comparison.verdict}`",
        f"- Reason: {comparison.reason}",
        f"- Supports a causal claim: {comparison.supports_a_causal_claim}",
        "",
        "## Task, fixed before the change",
        "",
        f"- Statement: {task.statement}",
        f"- Acceptance criterion: {task.acceptance_criterion}",
        f"- Baseline commit: `{task.baseline_commit}`",
        f"- Baseline worktree: `{task.baseline_dirty_digest}`",
        f"- Evaluation set: `{task.evaluation_digest}`",
        "",
        "## Measurements",
        "",
    ]
    for label, run in (("Baseline", comparison.baseline), ("Candidate", comparison.candidate)):
        if run is None:
            lines.append(f"- {label}: not measured")
            continue
        metric = "none" if run.metric is None else f"{run.metric}"
        lines.append(
            f"- {label}: commit `{run.commit_id}` · passed {run.passed} · failed {run.failed} · metric {metric}"
        )
    lines += [
        "",
        "## Authority boundary",
        "",
        "This comparison does not accept, promote, merge, tag or release the candidate.",
        "A verdict of IMPROVED means the recorded evidence supports the claim, not that the",
        "change was adopted. Promotion remains a separate product-owner decision.",
        "",
    ]
    return "\n".join(lines)
