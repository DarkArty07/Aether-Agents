---
name: git-github-closeout
description: Close GitHub work and manage owned temporary storage.
version: 0.1.2
author: Christopher, Hermes Agent
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [git, github, closeout, pull-request, verification]
    related_skills: []
---

# Git/GitHub Closeout Skill

Use this procedure for an owner-authorized GitHub-backed objective that must reach a
verified terminal repository state, or its local hygiene subprocedure during authorized
work. It describes reusable closeout and storage-hygiene mechanics only; the
current owner instruction, Objective Contract, repository rules, and protected-effect
policy decide whether an effect is allowed. This skill cannot grant authority.

## When to Use

- Use when acceptance is complete and the authorized objective requires a GitHub PR or
  terminal repository closeout.
- Use for normal branch, PR, required-check, merge, issue, milestone, and cleanup work.
- All three roles may use the Workspace and temporary-storage hygiene section during
  authorized work, before terminal closeout. That local subprocedure neither requires
  GitHub publication nor grants Implementer any publication or integration authority.
- Do not use for choosing SemVer impact, release action, or release channel; use the
  SemVer/release procedure for that decision.
- Do not use for credentials, repository settings, force operations, bypassing checks,
  deployment, package publication, or unrelated maintenance.

## Prerequisites

- A finalized Objective Contract or current owner instruction names the repository,
  scope, acceptance evidence, and permitted GitHub effects.
- Repository guidance and applicable project canonical skills have been read.
- GitHub authentication is already provisioned; never acquire, widen, or expose it.
- A clean-enough working tree and the required local verification commands are known.

For local temporary-storage hygiene alone, apply ownership, preservation and workspace
checks; do not require GitHub authentication or a completed objective merely to retire
an unneeded disposable intermediate.

## How to Run

Run inspection and verification through the `terminal` tool from the assigned checkout.
Use the repository's documented `gh` workflow only after the contract authorizes the
corresponding external step. Keep all evidence redacted and project-relative.

## Quick Reference

- `terminal(command="git status --short --branch")`
- `terminal(command="git diff --check")`
- `terminal(command="git log -1 --oneline")`
- `terminal(command="gh pr checks --watch")`
- `terminal(command="gh pr view --json number,state,mergeCommit,statusCheckRollup")`

## Procedure

1. Re-read acceptance, scope, authority, and stop conditions. Record every closeout step
   that applies and an explicit non-applicability reason for every omitted step.
2. Inspect `git status`, the diff, the intended base branch, and repository guidance.
   Confirm every changed path belongs to the objective and that no secret or local state
   is staged.
3. Run focused tests, affected tests, `git diff --check`, and the project's required
   quality gates. Fix only objective-caused failures within the bounded rework allowance.
4. For direct/single-unit work, review the final diff and stage only the intended files.
   Create one conventional commit whose message describes the verified change; record
   its SHA and tree state. For pipeline integration, preserve every accepted
   implementation unit as its own commit or merge commit and record each unit's SHA and
   tree state. Never squash, amend, rebase, or perform a history rewrite in pipeline
   integration.
5. When the contract authorizes publication, push the normal branch and open one PR
   against the protected default branch. Link the acceptance and verification evidence.
   Never force-push, rewrite history, or bypass review or protection.
6. Wait for all required checks and review gates. Diagnose a failure from its actual log,
   make the smallest in-scope correction, and rerun the affected evidence. An unrelated
   platform failure is recorded, not hidden by weakening a gate.
7. Merge only through the repository's normal green path. Verify the PR is merged, its
   merge commit is the expected one, and required checks remain green.
8. Reconcile an applicable linked issue and milestone without creating ceremonial or
   duplicate records. If none applies, record the specific reason in the evidence.
9. Only after durable PR, merge, board, and final-verification evidence exists, audit all
   objective-owned merged child/root branches and worktrees, locally and remotely where
   authorized. Remove all objective-owned merged child/root branches and worktrees
   identified by the audit. Preserve active, unmerged, blocked, review-active, concurrent,
   unknown, unrelated, and pre-existing branches, worktrees, stashes, and processes; report
   preserved residue separately. Use the checks below, including shared `dir` children.
   Apply only the evidence gates relevant to the actual route: no board or PR is invented
   for direct local work that did not require one.
10. Report the terminal result from Git, GitHub, board, and test state. Include the
    commit, PR/check result, issue disposition, cleanup audit, omissions, and residual
    risk; local integration alone is not closure.

## Workspace and temporary-storage hygiene

This is an instruction-level responsibility using existing tools, not a runtime collector.
Each role owns the disposable resources it creates; Morfeo owns direct-route worktree
retirement and Supervisor owns terminal pipeline retirement. Keep only the necessary
path/consumer notes in existing working context or handoff; do not add a registry or card.

For discretionary project scratch work, use project-relative
`.aether/tmp/<work-scope>/` with distinct ownership when concurrent work needs isolation.
Do not scatter exploratory reports or disposable scripts through the repository root.
Product deliverables belong in the project's structure outside `.aether`; exploratory
notes and plans retain their own conventions, not the temporary directory's lifetime.
Tool-managed worktrees, caches, runtime state and required external research locations
retain their existing rules. Do not relocate them or migrate historical residue merely
to impose this convention. `.aether` is neither wholly disposable nor wholly public.

1. **Check the destination before growth.** Before a large clone, extraction, build,
   test batch or repeated attempt, inspect available capacity on the filesystem actually
   receiving the data, including the configured temporary root. `/tmp` may be a bounded
   memory-backed filesystem independent of the repository disk. Prefer existing usable
   checkouts/caches over redundant copies where that preserves isolation. If space is
   inadequate, reclaim only your eligible residue or choose an already permitted
   destination with enough capacity; do not expand a mount, move a shared temp root or
   purge global caches as an implicit repair.
2. **Bound the lifetime at creation.** Use a unique owned temporary directory and the
   host's normal scoped cleanup facility (for example a temporary-directory context or
   a finally/exit cleanup for that exact directory). Keep deliverables out of disposable
   storage or transfer them to their durable destination before cleanup. Avoid repeated
   full clones or environments when the same isolated copy is still usable.
3. **Retire intermediates promptly.** After the creating operation or its last consumer
   finishes, preserve the needed result, evidence and failure diagnosis, then remove
   unneeded owned copies, extracted archives and build/test environments. Do not wait for
   the whole project or release to finish. A failure justifies retaining the material
   needed to diagnose/reproduce it, not every cache by default. Keep review inputs and
   unique uncommitted data; list any necessary leftover and who/what still needs it.
4. **Audit a worktree before retirement.** Bind its exact repository, path, branch and
   relevant board references. Inspect Git status including untracked files, retained
   commits/artifacts, nested repositories/worktrees and actual process use (including
   CWDs and open files). Check every consumer sharing the path, especially nonterminal
   `dir` children and active reviewers. Preserve source branches until their own gate is
   satisfied: removing a worktree directory is not permission to delete history. An idle
   shell is not a worker, but do not delete its CWD or terminate it implicitly. A stale
   running/blocked card is not proof of liveness; neither does a merged PR authorize
   marking that card done or abandoning its remaining obligation.
5. **Remove and verify only the audited set.** Recheck concurrent consumers immediately
   before removal, leave the target CWD, and use ordinary `git worktree remove` for
   worktrees (including any nested worktree's own Git registration), not recursive raw
   deletion. If Git refuses, inspect the reason instead of adding force. Delete only the
   exact owned disposable directories already shown to contain no needed data or active
   consumers. Confirm removal and reclaimed capacity; report retained paths with their
   reason and condition for removing them, not a blanket "cleanup done".
6. **Resume without accumulating.** After interruption or on resumption, recheck the
   owned leftovers named in existing continuity against current sources. Reclaim those
   now eligible before creating replacements. Unknown or historical nonterminal work
   requires reconciliation with its owning objective, not deletion by age or inference.

Never sweep an entire shared temporary root, infer ownership from a filename prefix or
age alone, or remove other sessions' data. Required logs, board rows, durable evidence,
credentials, active releases and rollback backups are not disposable intermediates.
Historical-residue cleanup is separately scoped; these instructions do not abandon old
contracts or introduce a new human approval gate for clearly owned disposable files.

## Pitfalls

- A green local test run does not prove a merged PR or terminal repository state.
- A PR being open, a branch being merged locally, or a zero failure count is not proof of
  completion.
- Never use `--force`, `--no-verify`, an administrative merge, or a check bypass.
- Do not delete a branch or worktree before durable merge evidence exists.
- Do not turn a missing release decision into a closeout decision; keep impact, action,
  and channel separate.

## Verification

- Confirm the final commit and tree with `terminal(command="git status --short --branch && git log -1 --oneline")`.
- Confirm checks and merge state with the repository's read-only PR inspection command.
- Confirm applicable issue/milestone reconciliation or its explicit non-applicability
  reason.
- Confirm every accepted pipeline unit remains individually inspectable as its own commit
  or merge commit and that integration history was not squashed, amended, rebased, or
  otherwise rewritten.
- Confirm all objective-owned merged child/root branches and worktrees are absent after
  the evidence gate while active, unmerged, blocked, review-active, concurrent, unknown,
  unrelated, and pre-existing residue remains.
- Preserve the exact commands, observed outputs, and remaining risk in the handoff.
- For an actual cleanup, distinguish verified removals from necessary retained residue.
  Editing this procedure requires documentary/resource coherence, not a new live cleanup
  campaign or proof of model obedience; behavioral feedback comes from ordinary use.
