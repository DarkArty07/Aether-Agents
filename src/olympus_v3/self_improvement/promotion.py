"""Disposable candidates and a promotion gate the evidence cannot open by itself.

Phase 2 made a comparison possible. It did not make one *safe*: a candidate was
still built in the same working tree that served as its own baseline, so there
was no cheap way back to the starting point, and nothing separated "the evidence
supports this" from "this is adopted".

Two mechanisms close that:

* :func:`disposable_candidate` builds the candidate in a throwaway git worktree
  and discards it unconditionally. Rollback stops being a procedure that can be
  forgotten and becomes the structure of the operation — nothing is written into
  the baseline tree, so there is nothing to undo.
* :func:`promote` records adoption, and refuses unless the comparison already
  supports a causal claim *and* a named human supplied an approval. Evaluation
  never promotes; promotion never re-evaluates.

An honest limit: the approval is procedural, not cryptographic. Nothing here can
stop an automated caller from passing a string. What it does guarantee is that
promotion cannot happen on a verdict that is INCOMPLETE, INVALID or REGRESSED,
that the approver is named in the durable record, and that adoption is a
separate act from measurement rather than a side effect of it.
"""

from __future__ import annotations

import shutil
import sqlite3
import subprocess
import tempfile
import time
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Iterator

from olympus_v3.self_improvement.causality import IMPROVED, Comparison
from olympus_v3.self_improvement.ledger import SelfImprovementLedger


class PromotionRefused(RuntimeError):
    """Adoption was requested without the evidence or the approval to support it."""


class CandidateWorktreeError(RuntimeError):
    """A disposable candidate could not be created or discarded."""


@dataclass(frozen=True)
class Promotion:
    task_id: str
    verdict: str
    approved_by: str
    approval_note: str
    promoted_commit: str


def _git(*args: str, cwd: Path) -> str:
    completed = subprocess.run(
        ["git", *args], cwd=str(cwd), capture_output=True, text=True, timeout=120, check=False
    )
    if completed.returncode != 0:
        raise CandidateWorktreeError(f"git {' '.join(args)} failed: {completed.stderr.strip()}")
    return completed.stdout.strip()


@contextmanager
def disposable_candidate(repository: Path, base_commit: str) -> Iterator[Path]:
    """Yield a throwaway worktree at ``base_commit`` and discard it afterwards.

    The candidate is built here, never in the baseline tree. Discarding happens
    whether the body succeeds, fails or raises, so a candidate that made things
    worse leaves nothing behind to revert.
    """

    repository = Path(repository).expanduser().resolve()
    parent = Path(tempfile.mkdtemp(prefix="aether-candidate-"))
    worktree = parent / "candidate"
    try:
        _git("worktree", "add", "--detach", "--quiet", str(worktree), base_commit, cwd=repository)
    except CandidateWorktreeError:
        shutil.rmtree(parent, ignore_errors=True)
        raise
    try:
        yield worktree
    finally:
        try:
            _git("worktree", "remove", "--force", str(worktree), cwd=repository)
        except CandidateWorktreeError:
            # Never let cleanup mask the caller's own failure; the temp tree is
            # removed below either way and `git worktree prune` reconciles the
            # administrative record.
            _git("worktree", "prune", cwd=repository)
        shutil.rmtree(parent, ignore_errors=True)


def _connect(ledger: SelfImprovementLedger) -> sqlite3.Connection:
    ledger.ensure_schema()
    connection = sqlite3.connect(str(ledger.path), timeout=5.0)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    connection.execute("PRAGMA busy_timeout = 5000")
    return connection


def promote(
    ledger: SelfImprovementLedger,
    comparison: Comparison,
    *,
    approved_by: str,
    approval_note: str,
    promoted_commit: str,
) -> Promotion:
    """Record adoption of a candidate, or refuse and say why.

    Refuses when the comparison does not support a causal claim, when the
    verdict is anything other than IMPROVED, when no named approver or reason is
    given, or when the task was already promoted. A second promotion of the same
    task is refused rather than overwritten, so the durable record cannot be
    quietly restated.
    """

    if not comparison.supports_a_causal_claim:
        raise PromotionRefused(
            f"verdict {comparison.verdict} does not support a causal claim: {comparison.reason}"
        )
    if comparison.verdict != IMPROVED:
        raise PromotionRefused(f"only an IMPROVED candidate may be promoted, not {comparison.verdict}")
    if not approved_by.strip() or not approval_note.strip():
        raise PromotionRefused("promotion needs a named approver and a stated reason")
    if not promoted_commit.strip():
        raise PromotionRefused("promotion needs the commit being adopted")

    with _connect(ledger) as connection:
        cursor = connection.execute(
            """
            INSERT OR IGNORE INTO promotions (
                task_id, verdict, approved_by, approval_note, promoted_commit, created_at
            ) VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                comparison.task_id,
                comparison.verdict,
                approved_by.strip(),
                approval_note.strip(),
                promoted_commit.strip(),
                time.time(),
            ),
        )
        if cursor.rowcount != 1:
            raise PromotionRefused(f"task {comparison.task_id!r} is already promoted")

    return Promotion(
        task_id=comparison.task_id,
        verdict=comparison.verdict,
        approved_by=approved_by.strip(),
        approval_note=approval_note.strip(),
        promoted_commit=promoted_commit.strip(),
    )


def promotion_for(ledger: SelfImprovementLedger, task_id: str) -> Promotion | None:
    with _connect(ledger) as connection:
        row = connection.execute("SELECT * FROM promotions WHERE task_id = ?", (task_id,)).fetchone()
    if row is None:
        return None
    return Promotion(
        task_id=str(row["task_id"]),
        verdict=str(row["verdict"]),
        approved_by=str(row["approved_by"]),
        approval_note=str(row["approval_note"]),
        promoted_commit=str(row["promoted_commit"]),
    )
