# HLP-280 affinity-flow liveness — Supervisor task breakdown

**Status:** executable breakdown for Objective Contract `oc_63345d36f393baf9@v3`
**Derived by:** Supervisor, 2026-09-01
**Owning plan:** [`plan.md`](plan.md), especially the persistent lane, recovery, and reliability requirements
**Objective Contract:** [`.aether/objective-contracts/oc_63345d36f393baf9/v3.md`](../../.aether/objective-contracts/oc_63345d36f393baf9/v3.md)
**Execution base:** `90251eee186c735f36adda4446203afde759798f`

This file is the execution breakdown of record. It does not amend the finalized Objective Contract. The contract remains read-only throughout execution.

## 1. Executability and cross-artifact result

Preflight at the execution base established:

- `.aether/project.toml`, the Objective Contract, the native Hermes Project, and the execution-board metadata all bind portable project `12027989-a08f-41cd-a82c-54ff1bfb6b03` to this repository.
- The contract bytes have SHA-256 `9baf9035956ba1f4c7b8735137447728baee569c6b221c79e2d73cfc892abbfa` and Git `HEAD` is the required execution base.
- The loaded editable Hermes distribution still resolves from project-relative `home/.venv-hermes/src/hermes-agent`, reports `hermes-agent` `0.20.1`, and has committed `HEAD` `0b288979e2322c02ab42c05f1e183bb31cfa5aa9`. Its dirty state is expected, shared, and must be preserved hunk-by-hunk.
- The superseded v1 candidate commit `655b0cb0349e26cfaaf196849680ed83bed56067` is reachable and contains the unactivated explicit-recovery antecedent. It is evidence and a starting reference only; it is not an activatable candidate.
- R7 requires one Supervisor per contract, fresh Implementer sessions/worktrees, independent review, three attempts, and a two-hour attempt limit. Its normal same-card review shape cannot be combined with this execution's pre-created dependent review/release lanes; the injected board lifecycle requires exactly one dedicated review mechanism rather than both. R8/R9 require dependency-ordered integration, preservation of shared dirty state, and board/Git evidence rather than a second execution store.
- The A1 and 004 stabilization freeze permits this indispensable E2E-liveness repair but no unrelated feature, framework upgrade, gateway/TUI behavior change, or broad cleanup.

The objective is executable as six serial cards: two Implementer publication units, two independent Supervisor review units, one Supervisor activation unit, and one terminal Supervisor verification unit. Dedicated review cards are used because the review/activation lanes are pre-created dependents; mixing same-card review with a dependent review/release lane would duplicate the board lifecycle. Behavior and evidence publication are separated by a live activation gate, so the contract's exactly-two-PR order is enforceable rather than aspirational.

## 2. Shared decisions stamped into every affected unit

1. **Exactly two Aether pull requests.** PR1 contains behavior, tests, the independent HLP-280 patch, this breakdown, policy allowlisting, and truthful pre-activation documentation with activation fields `RELOAD_PENDING`. PR2 is created only after successful activation and contains factual evidence/ledger/docs changes only. No third PR is permitted.
2. **No active-tree development.** Resolve the active Hermes checkout from the repository's common Git root and read it as evidence. Copy only the necessary non-secret source/test bytes into an isolated candidate. Development, RED/GREEN, patch generation, and reconstruction never modify the shared active checkout.
3. **Exact active-byte provenance.** Candidate and patch start from the exact active bytes, not clean upstream, v1's branch, or a guessed reconstruction. Record preimage hashes and the active committed revision; fail on drift or ambiguous ownership.
4. **Fixed runtime surface.** Reuse `kanban_unblock`, existing affinity/attention events, existing failure accounting, and existing notification routing. Add no tool, CLI verb, table, status, service, notifier, plugin, cron, watcher, gateway behavior, or TUI behavior.
5. **Fixed liveness semantics.** A valid pending `flow_attention` may bypass parent gating only for the unique terminal controller in the same Project/flow/session relationship. Explicit unblock lands that controller in `ready`; rediscovery may requeue `todo` idempotently but never deliberately `blocked`. A silent non-`dependency` terminal-affinity block without `input|revision|recovery` is rejected before mutation.
6. **Fixed automatic-failure semantics.** When the existing circuit breaker terminally fails a non-affinity child in a valid affinity flow, route one deduplicated controller-first `flow_attention`. Terminal-affinity failures retain `flow_terminal`. Below-threshold retries, ordinary parent gating, unrelated tasks, ambiguous graphs, malformed affinity, and cross-Project/flow/session cases retain current behavior. Centralize this at the existing automatic-failure terminal boundary so protocol-violation, spawn, crash, timeout, and equivalent `gave_up` paths cannot drift apart.
7. **Owner-silent repair.** Internal attention, review, activation, and evidence milestones do not notify the owner. Only the already accepted explicit origin signals and `flow_terminal` cross the origin boundary, once.
8. **Production size and file limit.** Final production delta is at most 130 changed lines across `hermes_cli/kanban_db.py` plus only the minimal explanatory/schema text required in `tools/kanban_tools.py`. Tests and Aether evidence are outside that production count. No gateway/TUI production file changes.
9. **Patch identity.** Publish one independent `patches/hermes/HLP-280-affinity-controller-requeue.patch` with computed SHA-256. Prove forward apply, reverse apply, byte-for-byte candidate reconstruction, target preservation, and absence of foreign HLP hunks.
10. **Shared dirty-tree safety.** Never restore or overwrite a complete active Hermes file. Activation uses exact reviewed hunks only after pre-hash and backup readback. Any target drift, duplicate writer, ambiguous ownership, or failed reconstruction stops before mutation.
11. **Testing floor.** Use isolated homes, DBs, workspaces, task-owned temporary roots, and remove `HERMES_DELEGATED_CHILD_CONTEXT`. Preserve v1 RED/GREEN evidence only after independent applicability checks. Run focused affinity/tools/failure tests, affected Kanban/tool/TUI/gateway/guard suites, Hermes's canonical per-file runner, Ruff/format, compile/type checks, `git diff --check`, and the Aether reconciliation/documentation/public-artifact/full test gates named by the contract. Only an exactly reproduced baseline-equivalent cron environment skip outside acceptance may remain.
12. **Stop/rollback.** Stop on any Objective Contract stop condition. A live reload or canary failure restores the exact backup, reloads once, and runs the last-known-good canary. At most two v3-focused behavior repair variants are allowed; behavioral repair after PR1 merge requires returning to implementation rather than slipping code into PR2.

## 3. Dependency graph

```text
HLP280-01 — isolated behavior, tests, patch, ledger, and PR1 (Implementer)
    → HLP280-01R — independent review, checks, and PR1 merge (Supervisor)
        → HLP280-02 — exact backup, activation, reload, and no-watcher canaries (Supervisor)
            → HLP280-03 — factual evidence-only PR2 (Implementer)
                → HLP280-03R — independent review, checks, and PR2 merge (Supervisor)
                    → HLP280-04 — integrated verification, #280 closeout, cleanup report (terminal Supervisor)
```

The Supervisor activation and final units reuse the root flow/session/workspace. Each Implementer receives a fresh session and its own worktree. The graph is deliberately serial because PR2 facts do not exist before activation and the active Hermes targets are a shared hotspot.

## 4. HLP280-01 — Build, qualify, and open PR1

**Assignee:** `implementer`

**Dependencies:** this decomposition root

**Workspace:** fresh project-linked worktree and branch

**Card settings:** `max_retries=3`; `max_runtime_seconds=7200`; goal mode disabled

**Outputs:** complete PR1 candidate and opened PR1 awaiting independent review; no runtime mutation

### Acceptance criteria

1. Verify the parent preflight and Objective Contract identity/digest/base. Consume the finalized contract read-only; do not edit, stage, replace, or recreate it.
2. Bring this Supervisor-authored breakdown commit into the unit branch unchanged so PR1 contains the breakdown of record.
3. Resolve and inspect the exact active Hermes source/version/revision/status and v1 antecedent. Create an isolated candidate from exact active target bytes; record target pre-hashes and never modify the active checkout.
4. Demonstrate RED for both zero-frontier defects: explicit recovery leaves the pending-attention controller unclaimable, and an automatic terminal failure of a non-affinity child leaves no controller attention. Preserve the silent-block rejection RED where absent.
5. Implement the fixed semantics in §2 without widening lifecycle behavior. Cover external unblock, `todo` rediscovery, deliberate `blocked`, unique claim/event count, malformed/ambiguous/cross-Project/flow/session isolation, terminal-affinity `flow_terminal`, below-threshold retries, protocol-violation `gave_up`, and representative spawn/crash/timeout trips.
6. Keep the final production diff within the 130-line cap and target limit. Report added/removed/changed line counts separately for production and tests.
7. Generate the independent HLP-280 patch from the exact candidate. Prove apply, reverse, reconstruction, non-target preservation, computed digest readback, and no foreign HLP hunks.
8. Reconcile `HERMES_LOCAL_PATCHES.md`, the HLP-211 reconciliation entry/aggregate/preflight, HLP-247 summary visibility, status headings, hotspot text, CHANGELOG, limitations, issue/policy references, and CI policy allowlist. Every pre-activation fact must be truthful; activation/backup/PID/canary fields remain `RELOAD_PENDING` or explicitly pending.
9. Run the complete Hermes and Aether gates required by §2 and the Objective Contract. Record exact commands/results and any baseline comparison for the sole permitted skip.
10. Commit coherent, revertible changes; push the unit branch and open PR1 against the current default branch using existing authorization. The PR body must state the production count, patch digest, test evidence, no active mutation, and `RELOAD_PENDING` state.
11. Complete the unit with the PR URL, commit, changed paths, exact candidate/preimage hashes, patch identity/reconstruction evidence, production count, and check state. A pre-created independent review card consumes this handoff. Do not request same-card review, merge, activate, close #280, or create PR2.

## 5. HLP280-01R — Independently review and merge PR1

**Assignee:** `supervisor`

**Dependencies:** decomposition root and completed HLP280-01

**Workspace:** same flow-bound Supervisor workspace

**Card settings:** `max_retries=3`; `max_runtime_seconds=7200`; goal mode disabled

**Outputs:** independently reviewed and merged PR1; no runtime mutation

### Acceptance criteria

1. Inspect HLP280-01's actual branch, PR, diff, commits, and check state. Cold-read the patch/diff before relying on the handoff narrative.
2. Independently rerun focused behavior, production-line counting, patch apply/reverse/reconstruction, Aether reconciliation/documentation/public-artifact validation, and the contract's required negative controls.
3. Verify the active Hermes checkout is unchanged, PR1 is the first and only objective PR, every activation fact remains honestly pending, and the Objective Contract is unchanged.
4. If a correctable implementation defect exists, create an Implementer rework child or return equivalent dependency-linked rework; do not edit behavior as reviewer and do not consume a human-visible block. The review card does not complete until the corrected candidate is independently reverified.
5. Wait for required checks, approve, and merge PR1 without bypass, force, or activation. Complete with PR URL, reviewed commit, merge commit, checks, rerun evidence, patch digest, production count, and confirmation that the active runtime was not mutated.

## 6. HLP280-02 — Activate the reviewed bytes and prove both live paths

**Assignee:** `supervisor`

**Dependencies:** completed HLP280-01R

**Workspace:** same flow-bound Supervisor workspace

**Card settings:** `max_retries=3`; `max_runtime_seconds=7200`; goal mode disabled

**Outputs:** activated or exactly rolled-back runtime; factual activation handoff for PR2

### Acceptance criteria

1. Inspect HLP280-01's completed review evidence and independently verify PR1 is merged, checks are green, and merged patch/behavior bytes equal the approved candidate. Refuse activation if PR1 is not merged or activation facts were fabricated in advance.
2. Resolve the active editable source and running gateway from current state. Verify target ownership, active committed revision, exact pre-hashes, dirty-tree target diff, and absence of another writer. Stop on drift or ambiguity.
3. Create the exact task-owned backup/manifest before mutation, read it back, and verify hashes for every target plus the relevant dirty-state manifest. Do not copy secrets or unrelated private state into versioned/public evidence.
4. Apply only the reviewed HLP-280 hunks to the active targets. Never overwrite a complete dirty file. Verify active post-hashes and byte equality with the reviewed candidate while preserving every non-target byte.
5. Run pre-reload focused tests from the active result, reload the Aether-owned Hermes gateway exactly once, and prove healthy process identity/state/readback with no duplicate/concurrent writer.
6. Run deterministic probes and both owner-required no-watcher live paths: explicit external recovery of a pending-attention controller, and automatic non-affinity child terminal failure reaching the unique controller. Prove single attention/requeue/claim, same Supervisor session/workspace/flow fencing, no repairable owner wake, preserved terminal `flow_terminal`, and successful completion/return.
7. On any reload or canary failure, restore exact backup hunks, reload once, run the last-known-good canary, and stop. Do not attempt a third behavior variant and do not author behavioral changes here.
8. Record non-secret factual evidence in the completion handoff: backup locator and manifest hash, pre/post target hashes, patch digest/merge commit, old/new PID and service state, commands/results, canary event/run/session facts, owner-delivery result, rollback command/result, active status, and residual risk. Do not edit repository behavior/docs, open PR2, or close #280.

## 7. HLP280-03 — Publish factual evidence-only PR2

**Assignee:** `implementer`

**Dependencies:** successful HLP280-02 activation/canary

**Workspace:** fresh project-linked worktree and branch from the merged default branch

**Card settings:** `max_retries=3`; `max_runtime_seconds=7200`; goal mode disabled

**Outputs:** complete evidence-only candidate and opened PR2 awaiting independent review

### Acceptance criteria

1. Verify PR1 is merged and read HLP280-02's factual activation handoff. If activation rolled back, failed, is incomplete, or lacks exact evidence, block without creating PR2.
2. Start from the default branch containing PR1. Modify only ledger/evidence/documentation paths needed to replace pending fields with the observed backup, hash, PID/state, canary, rollback, activation, and issue facts. Do not change Hermes behavior, tests that define behavior, patch bytes, policy allowlist, runtime code, hooks, gateway/TUI code, or the Objective Contract.
3. Preserve privacy: no absolute private machine path, raw owner/session content, secret, credential, provider/model binding, full private board/database, or unbounded log enters Git. Use project-relative/bounded evidence and safe identifiers only where the contract requires them.
4. Prove mechanically that PR2 is evidence-only by comparing its changed paths and patch artifact/runtime hashes with merged PR1. The HLP-280 patch digest and production bytes must be identical.
5. Update truthful final HLP-280 status, complete the reconciliation entry/aggregate/preflight and CHANGELOG/limitations/issue evidence, and distinguish v1/v2/v3. Do not claim #280 closed before merge.
6. Run all documentation, reconciliation, policy/public-artifact, focused, full `scripts/run_tests.py`, Ruff/format/mypy/build, and `git diff --check` gates applicable to the evidence-only change. Record exact results.
7. Commit the evidence-only unit, push it, and open exactly PR2 against the default branch. The PR body must state that behavior/patch bytes are unchanged and cite the bounded activation/canary evidence.
8. Complete with PR URL, commit, changed paths, behavior/patch hash comparison, evidence provenance, and check state. A pre-created independent review card consumes this handoff. Do not request same-card review, merge, or close #280.

## 8. HLP280-03R — Independently review and merge PR2

**Assignee:** `supervisor`

**Dependencies:** completed HLP280-03

**Workspace:** same flow-bound Supervisor workspace

**Card settings:** `max_retries=3`; `max_runtime_seconds=7200`; goal mode disabled

**Outputs:** independently reviewed and merged evidence-only PR2

### Acceptance criteria

1. Verify the actual activation facts against HLP280-02 and current bounded live readback before relying on the Implementer summary.
2. Independently prove PR2 changes no behavior, behavior tests, policy allowlist, or HLP-280 patch bytes; recompute the patch and active-byte hashes and compare with merged PR1.
3. Rerun reconciliation, documentation, policy/public-artifact, focused, full, Ruff/format/mypy/build, and diff checks required by the contract; wait for required GitHub checks.
4. If correctable evidence defects exist, create an Implementer rework child or return equivalent dependency-linked rework; do not edit the candidate as reviewer and do not consume a human-visible block. Reverify the corrected candidate independently.
5. Approve and merge PR2 without bypass or force. Complete with PR URL, reviewed commit, merge commit, checks, evidence-only proof, activation-readback comparison, and confirmation that #280 remains open for terminal verification.

## 9. HLP280-04 — Terminal integrated verification and closeout

**Assignee:** `supervisor`

**Dependencies:** decomposition root, HLP280-01, HLP280-01R, HLP280-02, HLP280-03, and HLP280-03R

**Workspace:** same flow-bound Supervisor workspace

**Card settings:** `max_retries=3`; `max_runtime_seconds=7200`; goal mode disabled; terminal affinity enabled

**Outputs:** integrated verification, issue closure, cleanup report, and one terminal flow handoff

### Acceptance criteria

1. Inspect every parent card and both merged PRs. Verify exactly two objective PRs exist, PR1 precedes runtime mutation, PR2 follows successful activation, both had independent Supervisor review/checks, and PR2 is evidence-only.
2. Update the flow workspace to the merged default branch without discarding unrelated work. Verify merged files, active runtime bytes, patch digest, ledger/reconciliation outputs, and current healthy service state agree.
3. Run the integrated Aether verification set plus the deterministic HLP-280 probes and bounded no-watcher readback needed to prove the installed result remains green. Do not spend/model-run beyond the already authorized local canaries and do not perform unrelated release/cutover work.
4. Close Aether issue #280 only after all acceptance criteria pass and PR2 is merged. Add a concise closeout that cites the two merged PRs and bounded evidence; do not expose private runtime content.
5. Produce the cleanup report distinguishing v1, v2, and v3 artifacts; preserved/removed objective worktrees; backup retention; branch status; temporary DB/process cleanup; and pre-existing dirty Hermes state. Preserve rollback inputs through the stated retention need.
6. If integrated verification finds a behavioral defect, create/return Implementer work rather than editing behavior in this terminal unit. Only mechanically implied path/reference/wiring repair is permitted, and any such repair must not create a third PR under this contract.
7. Complete once with `flow_terminal`, summarizing exact merged commits/PRs, activation state, checks, canaries, issue state, cleanup, rollback readiness, and residual risk. No internal milestone should notify the owner before this terminal handoff.
