---
name: git-github-closeout
description: Close authorized GitHub work with verified evidence.
version: 0.1.0
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
verified terminal repository state. It describes reusable closeout mechanics only; the
current owner instruction, Objective Contract, repository rules, and protected-effect
policy decide whether an effect is allowed. This skill cannot grant authority.

## When to Use

- Use when acceptance is complete and the authorized objective requires a GitHub PR or
  terminal repository closeout.
- Use for normal branch, PR, required-check, merge, issue, milestone, and cleanup work.
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
   preserved residue separately.
10. Report the terminal result from Git, GitHub, board, and test state. Include the
    commit, PR/check result, issue disposition, cleanup audit, omissions, and residual
    risk; local integration alone is not closure.

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
