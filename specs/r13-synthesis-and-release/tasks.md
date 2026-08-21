# PD-44 Proportional Direct Execution — Supervisor Task Breakdown

**Status:** completed historical execution contract. The accepted delivery and later owner validation are recorded in `research.md` §16. This file preserves the pre-delivery task terms and is not an active instruction; its #196-open requirements were superseded by Christopher's later validation and explicit closure authority.

**Derived by:** Supervisor, 2026-08-18

**Source contract:** `DESIGN.md` PD-44; `.specify/memory/constitution.md` 1.0.1; R1 FR-133 through FR-133e; R2 FR-204a, FR-206, FR-208, FR-214 through FR-224; R3 FR-301 through FR-305; R5 FR-506 through FR-506f and FR-517 through FR-522; R7 FR-700 through FR-705, FR-714 through FR-720, FR-729 through FR-739, and FR-743; R8 FR-801, FR-804b, FR-805, FR-809 through FR-812, FR-813 through FR-819b, and FR-823a; R9 FR-901, FR-902, and FR-915; R10 FR-1005 through FR-1013a; R11 FR-1101 through FR-1108; R12 FR-1201 through FR-1202a; R13 FR-1306 through FR-1310h and FR-1341a through FR-1341j; and the PD-44 amendment in `plan.md` lines 480–575.

## Owner-authorized one-time interactive delivery exception

**Decision (2026-08-20):** Christopher rejected a full local implementation of Hermes #88057 as disproportionate for this PD-44 delivery and instead authorized exactly one audited interactive transfer. The protected-path candidate `t_34e1fed9` proved the relevant failure closed: its Morfeo instruction-file write was denied after the TUI approval prompt timed out, and no target byte changed. That card, its baseline, and dependent `t_e4ba11f1` are audit evidence only; neither may be released, recovered, edited, or integrated.

This decision changes only the final transfer mechanism. It does not change the accepted five-file scope, content requirements, authority limits, secret exclusion, mechanical-only validation standard, or #196-open state. It authorizes no Hermes core change, hook/config bypass, credential/session/database mutation, profile/gateway restart, history effect, publication, or functional test. The final interactive action is not a substitute for the later owner validation of route judgment and live-hook efficacy.

### Why the normal integration card is non-executable

The normal `PD44-02` path would write protected Morfeo instruction/policy files from a non-interactive Supervisor worker. Hermes #88057 prevents the TUI approval request from reaching that worker's owner interaction. Retrying, bypassing the gate, weakening the hook, or implementing a broad local approval relay would contradict the failure evidence and the owner's proportionality decision. The live Morfeo policy permits a multi-file `patch` only from the integration worktree, and its interactive approval boundary is the intended one-operation gate.

### Narrow replacement graph and shared decisions

```text
PD44-I01 — unprotected five-target proposal bundle (Implementer; initially blocked)
    → same-card independent Supervisor review
    → one direct interactive Morfeo `patch` call after explicit owner approval (no card)
    → Christopher's deferred manual direct-versus-pipeline and live-hook validation
```

1. **No new role or workflow.** The proposal author is the normal Implementer in one fresh branch-bound worktree; the independent reviewer is Supervisor on the same card. The final transfer is a bounded direct Morfeo action and therefore creates no ceremonial integration card (PD-29). It is not a new lane, classifier, router, state store, role, or general exception.
2. **One indivisible logical proposal.** The approved result remains exactly these five live targets: `home/profiles/morfeo/SOUL.md`, `home/profiles/morfeo/config.yaml`, `home/profiles/morfeo/hooks/aether_pre_tool_policy.py`, `README.md`, and `ROADMAP.md`. They are authored and reviewed together; no parallel sibling may decide a subset.
3. **Unprotected bundle only.** Supervisor seeds no live target path in the candidate worktree. It copies only the current secret-free target bytes into `.pd44-interactive-proposal/baseline/current/` and `.pd44-interactive-proposal/candidate/current/`, preserving the same relative paths below each root. The baseline tree is read-only. No `.env`, credential, token, session, memory, database, keyring, or other private runtime state may enter the worktree.
4. **Exact review and transfer evidence.** The bundle has a baseline manifest, candidate manifest, live-preimage manifest (baseline hashes against the five real relative target paths), live-postimage manifest (candidate hashes against those same five paths), `apply.patch`, and an `apply.patch.sha256` record. `apply.patch` must be one V4A patch with exactly five `Update File` operations for the live target paths and no Add, Delete, Move, or extra target. A disposable isolated mirror must prove the current Hermes V4A parser accepts the patch and transforms every baseline byte into the exact candidate byte before approval.
5. **One interactive operation, no workaround.** After independent review, an already interactive Morfeo session—not an Implementer, Supervisor, controller, or spawned board worker—must first verify the live-preimage manifest and approved-patch hash. Only if both still match may it submit the entire `apply.patch` in one `patch(mode="patch")` call while on the integration worktree. The runtime approval prompt requires explicit owner acceptance. A denial, timeout, missing approval, malformed patch, changed preimage, or post-write mismatch stops the action; it must not be retried, split, copied through the terminal, bypassed, or repaired by a worker.
6. **Bounded final verification.** The direct session may report actual pre/post hash evidence and run only the already accepted mechanical checks after a successful patch. It must not start/restart a profile or gateway, execute a behavior/policy test, benchmark, route-classification suite, or any protected/external effect. It preserves the proposal worktree and all manifests for Christopher. #196 remains open.

## Cross-artifact executability analysis

| Contract concern | Observed, settled conclusion | Execution consequence |
| --- | --- | --- |
| Route and role boundary | This is substantial local configuration/product work, so it remains on the Morfeo → Supervisor → Implementer pipeline route. Direct stewardship is not being exercised by this card. | Morfeo created one Supervisor card only; Supervisor creates the implementation and integration units. |
| Atomicity and collision | Doctrine, effective capability, policy, README, and ROADMAP all describe one responsibility model. They share files and must not be independently dispatched. | One Implementer candidate, no parallel sibling implementation, then one dependent integration unit. |
| Ignored live state | Morfeo's three profile files are ignored; a clean worktree does not contain them. A directory Implementer workspace would lack its enforced branch binding. | Use the explicit FR-804b/FR-1341i staged-candidate mechanism, not a shared Implementer directory. |
| Runtime workspace support | The loaded Hermes 0.20.1 source resolves a worktree anchored at the repository root to `.worktrees/<task-id>` and the fallback branch `wt/<task-id>` (`hermes_cli/kanban_db.py:7748–7807`). The dispatcher exports that binding only for worktree cards (`:10418–10421`). | The candidate card is initially blocked, branch-bound, and seeded before the root card completes and releases it. |
| Effective capability baseline | `HERMES_HOME=home/profiles/morfeo hermes config get platform_toolsets` currently resolves CLI to `kanban`, `file`, `memory`, `session_search`, `web`, and `terminal`; Telegram intentionally has the same existing composition without terminal. | Copy and verify the current config; do not make a redundant configuration mutation unless the candidate resolver finds a real defect. Never widen Telegram or add unrelated toolsets. |
| Policy baseline | The current Morfeo hook still contains obsolete Morfeo execution denial while its generic file-target logic has already been partially broadened. Supervisor and Implementer branches are active in the same policy source. | Candidate removal is narrowly Morfeo-specific; it must retain transversal secret/credential controls and every Supervisor/Implementer restriction. |
| Existing brownfield state | `main` is at `76a187e06262f299a48ac10068717050f38ba494` with required uncommitted documentation/runtime work, and the five targets are present. | No reset, clean, stash, checkout-over, rebase, commit, push, or overwrite of a changed live target. |
| Validation standard | Christopher selected mechanical validity only. Functional route and live-hook behavior are explicitly deferred. | Parse YAML, compile the hook, inspect effective toolsets and complete candidate/live diffs, run `git diff --check`, and do not start Morfeo or invoke a behavior/policy test. |

The prior directory-workspace blocker is resolved in principle by the controlled staging and byte-only integration mechanism below. A later source inspection exposed a separate runtime delivery contradiction before the candidate was released; its repaired execution boundary is recorded under **Resolved runtime prerequisite and fresh execution boundary**. If a target is discovered to contain secret/private runtime material, this is again non-executable: do not stage it and block the affected unit rather than inventing an exception.

## Scope, authority, and shared decisions

Christopher authorized reversible local PD-44 edits and the mechanical checks below. The authorization excludes commit, push, pull request, merge, issue closure, tag, release, deployment, restart, credential/session/database mutation, Git-history rewrite, cleanup of existing work, and every other protected external effect. Issue #196 remains open.

The following decisions are settled once and are stamped into both executable card bodies:

1. **One indivisible candidate.** The five target files are one coherent transition. There is no parallel implementation and no goal-mode loop; ordinary same-card review supplies the independent review that this pipeline unit needs.
2. **Candidate paths.** The only candidate targets are `home/profiles/morfeo/SOUL.md`, `home/profiles/morfeo/config.yaml`, `home/profiles/morfeo/hooks/aether_pre_tool_policy.py`, `README.md`, and `ROADMAP.md`. No accepted `DESIGN.md`, R1–R13 artifact, Supervisor/Implementer profile, credential, session, memory, database, source runtime, branch history, or remote state is in scope.
3. **Staging evidence is not a second store.** Supervisor seeds immutable snapshots under `.pd44-baseline/current/` inside the candidate worktree and a SHA-256 manifest at `.pd44-baseline/manifest.sha256`. The directory is local workspace evidence required by FR-804b, not a contract or execution record; it is read-only, ignored from candidate status, and must remain unchanged. Candidate-specific change review compares each target to this baseline, not to the dirty shared `main` worktree.
4. **Branch and manifest gate.** The candidate worktree is anchored at the repository root and resolves to `.worktrees/<candidate-id>` on the runtime-derived `wt/<candidate-id>` branch. Before release, Supervisor verifies the branch, target manifest, baseline hashes, and that no secret/private runtime file has been copied. A candidate worker that cannot verify this gate must block rather than edit.
5. **No redundant config churn.** The observed effective CLI toolset already contains the required `kanban + file + terminal` plus `memory + session_search + web`; Telegram does not get terminal. The candidate must preserve this composition and leave `config.yaml` byte-identical unless its own resolver shows a real discrepancy.
6. **No route mechanism.** Direct-versus-pipeline selection remains Morfeo's contextual reasoning over the complete owner objective. Neither unit may introduce a classifier, score, threshold, benchmark, fast lane, new card type, new role, database, model router, hook gate, or external route mechanism.
7. **No activation.** Morfeo remains stopped throughout preparation, candidate work, review, and integration. No live profile start, prompt benchmark, route-classification suite, functional hook invocation, or behavior test is authorized.
8. **Byte-only integration.** The integration unit may copy only independently approved candidate bytes after proving all five live targets still equal their immutable baseline snapshots. If any live target has changed since staging, it records a hotspot and blocks; it does not overwrite, merge, redesign, or repair the content.
9. **Preservation and reporting.** The candidate worktree, its branch, and `.pd44-baseline` remain preserved through Christopher's manual validation. Every unit reports actual checks, exact changed target paths, preserved-baseline status, stopped-profile status, residual functional risk, and that issue #196 remains open. Durable evidence contains no secrets or raw private-runtime contents.

## Execution graph

```text
PD44-01 — isolated atomic candidate (Implementer; initially blocked)
    → same-card independent Supervisor review
    → PD44-02 — byte-only stopped-profile integration (Supervisor; shared dir)
    → Christopher's manual direct-versus-pipeline and live-hook validation
```

`PD44-01` and `PD44-02` are intentionally serial. The integration card has `PD44-01` as its parent, so it cannot run until the candidate's same-card review has approved and completed it. There are no parallel siblings.

## Supervisor preparation before release

Before the root Supervisor card completes, it must:

1. Create `PD44-01` as an initially blocked `implementer` worktree card with `max_retries: 3` and `max_runtime_seconds: 7200`, anchored at this repository root.
2. Materialize its runtime-derived `.worktrees/<candidate-id>` worktree and `wt/<candidate-id>` branch without committing, resetting, or changing `main`.
3. Check all five source targets for high-confidence secret material. Copy only those five non-secret files into matching candidate paths. Do not copy `.env`, auth/credential files, tokens, sessions, memories, databases, keyrings, or any other profile state.
4. Copy the same five source bytes into `.pd44-baseline/current/`, write the SHA-256 manifest there, mark the snapshot tree read-only, and exclude it from candidate status. Verify both source-to-candidate and snapshot-manifest hashes before release.
5. Verify `git -C <candidate-worktree> branch --show-current` equals the card branch and that the worktree has no candidate delta before editing.
6. Create `PD44-02` as a dependent `supervisor` directory card with `PD44-01` as its parent, `max_retries: 3`, and `max_runtime_seconds: 7200`.
7. Only after all preflight evidence is true, complete this decomposition card. Its dependency transition releases the prepared candidate; it must not be released before preparation finishes.

## Resolved runtime prerequisite and fresh execution boundary

The legacy candidate `t_b02bdbad`, its branch, and immutable baseline remain preserved as pre-fix audit evidence. They must not be released, recovered, edited, or used for integration: the old graph exhausted its block-loop path before the repair and is not the clean execution instance of this breakdown.

The controlled runtime repair now updates the in-memory claimed worktree task with its resolved fallback branch before the ready or review spawn path exports `HERMES_KANBAN_BRANCH`. The current gateway was externally reloaded after that repair, and its editable interpreter resolves the repaired source. This establishes that a fresh candidate may be prepared; it does not substitute source inspection or a process restart for the candidate's own first-spawn entry gate.

The fresh candidate must still verify, before any content mutation, that its supplied `HERMES_KANBAN_BRANCH` is nonempty and equals its actual `wt/<card-id>` branch. A missing or mismatched binding is a genuine runtime-capability failure: the worker blocks without modifying a target, copying more state, weakening policy, writing the board database, changing roles, or spending work on a workaround. If the gate passes, the existing two-unit graph and all five-file atomicity, baseline, review, stopped-profile, and byte-only-integration requirements apply unchanged.

## PD44-01 — Build the isolated Morfeo direct-stewardship candidate

**Assignee:** `implementer`

**Workspace:** runtime-derived worktree `.worktrees/<candidate-id>` on its card-bound branch. It contains the five staged target files and read-only `.pd44-baseline` evidence prepared by Supervisor.

**Card settings:** `max_retries: 3`; `max_runtime_seconds: 7200`; no goal mode.

**Required inputs:** this card's explicit body, the accepted PD-44 contract, the staged five-file baseline, and the parent handoff. The card body, not a sibling or `tasks.md`, is the Implementer's complete execution scope.

**Acceptance criteria:**

1. Before changing content, verify the assigned workspace, runtime branch binding, baseline manifest, and five-file target manifest. If the branch, target set, baseline hashes, or secret-free precondition is absent, block rather than edit or stage any additional file.
2. Rewrite the entire staged Morfeo SOUL as one coherent doctrine, not an addendum. It identifies Morfeo as owner interlocutor, designer, contract architect, memory/adaptation steward, and direct operational assistant — neither a designer who exceptionally touches files nor Aether's general Implementer.
3. State conceptual direct-route signals: the complete objective is understood and bounded; consequences are inspectable; correction/reversal is practical; significant decomposition or parallel context is unnecessary; independent review adds no proportionate value; and the objective is not a substantial feature.
4. State conceptual pipeline signals: feature work, architecture, multiple responsibilities, meaningful decomposition, independent parallel work, complex integration, valuable independent review, material construction uncertainty, or real scope growth. Preserve complete-objective anti-fragmentation; permit direct inspection for scope discovery; require stopping expansion, completing the canonical contract, and handing exactly one card to Supervisor when scope grows; include the exact principle: “use the process that fits the problem, not the maximum process available.”
5. Retain current-instruction precedence, scope fidelity, credential limits, product-decision ownership, protected-effect boundaries, incidental-work disclosure, and capability-versus-authority limits. Address the owner generically and do not embed a person, stack, project type, machine path, secret, or runtime selection.
6. Resolve candidate configuration with `HERMES_HOME` pointing to the staged Morfeo profile. The effective CLI toolsets must be exactly the existing `kanban`, `file`, `memory`, `session_search`, `web`, and `terminal`; Telegram remains without `terminal`. Do not enable browser execution, computer use, sandboxed code execution, cron, delegation, or any unrelated toolset. Leave the staged config byte-identical unless this resolver identifies a real deficiency, and report why any config byte changed.
7. Reconcile only obsolete Morfeo policy: remove Morfeo-specific general execution/terminal denial, contract-only Morfeo file-mutation/path containment, and equivalent text that says Morfeo has no execution or implementation authority. Retain every transversal secret/credential protection plus all Supervisor/Implementer policy paths. Do not add direct/pipeline classification, task size, or risk policy logic.
8. Update README so its flow visibly expresses `owner → Morfeo → direct action OR Supervisor → Implementers`, explains both routes briefly, and retains the normal pipeline's independent review/integration meaning. Update ROADMAP's current boundary so it no longer claims or implies Morfeo lacks terminal/general project-file capability; keep all affected documentary stages `done`, preserve R12 as `done`, and carry Christopher's deferred PD-44 functional validation and issue #196-open state forward.
9. Touch only the five candidate targets relative to `.pd44-baseline`. Do not alter the baseline snapshots, contract artifacts, other profile files, repository history, or remote state. Do not commit, push, publish, start a profile, or perform an external/protected effect.
10. Run and report only actual mechanical evidence: baseline manifest validation; PyYAML parse of the staged config; Python compilation of the staged hook; runtime effective-platform-toolset inspection; `git diff --check`; and a complete baseline-to-candidate diff review that proves the target whitelist, retained protections, no unrelated toolset, no obsolete doctrine, and no route mechanism. Do not run a live Morfeo behavior, hook/policy, benchmark, or route-classification test.
11. Confirm from `hermes profile list` that Morfeo remained stopped. Request same-card Supervisor review and hand over the exact changed paths, check outcomes, candidate/baseline hash evidence, config-resolution evidence, stopped/no-live-test confirmation, baseline-preservation result, residual functional risk, and issue #196-open confirmation.

## Same-card review of PD44-01

The reviewing Supervisor must cold-read the candidate's complete baseline-to-candidate diff before relying on the Implementer's handoff. It must not edit the candidate. It must independently rerun the allowed mechanical checks, inspect the staged effective CLI and Telegram toolsets, verify the candidate branch/manifest and Morfeo's stopped status, and verify that no candidate bytes outside the five targets changed. It approves only when all acceptance criteria are met; otherwise it returns concrete, correctable defects through `kanban_request_changes`. A genuine contract contradiction or unavailable prerequisite blocks/escalates rather than being worked around.

## PD44-02 — Apply the approved candidate to the stopped live profile

**Assignee:** `supervisor`

**Dependencies:** independently approved, completed `PD44-01`.

**Workspace:** shared repository directory on the current integration branch, used only for the authorized byte-for-byte/reviewed-diff application.

**Card settings:** `max_retries: 3`; `max_runtime_seconds: 7200`; no goal mode.

**Acceptance criteria:**

1. Read the completed parent review evidence and locate the preserved candidate worktree and immutable baseline. Confirm that the parent was completed by independent Supervisor review, not merely by Implementer self-report.
2. Confirm Morfeo is stopped and remains stopped. Do not start, restart, or behavior-test it.
3. Revalidate the candidate baseline manifest and high-confidence secret/private-runtime exclusion. Before copying, compare every live target byte-for-byte with the corresponding `.pd44-baseline/current/` snapshot. If any live target differs, add a hotspot comment naming the target and block without overwriting it.
4. Apply only the approved candidate bytes for the five targets. Do not add, repair, reinterpret, merge, or redesign content. Do not modify any other live profile state, contract artifact, Supervisor/Implementer profile, credential/session/memory/database, branch history, or remote state.
5. Verify every applied live target is byte-for-byte equal to the approved candidate. Preserve the candidate worktree, branch, and baseline evidence through Christopher's manual validation.
6. Run and report only actual mechanical evidence on the live result: PyYAML parse of the live config; Python compilation of the live hook; effective Morfeo CLI/Telegram toolset resolution; `git diff --check`; and a complete current diff review confirming only candidate-approved PD-44 target changes, no unrelated toolsets, and no route mechanism. Do not run any live Morfeo behavior, prompt benchmark, route-classification suite, or functional hook test.
7. Preserve every pre-existing local modification. Do not reset, clean, stash, checkout-over, commit, push, publish, close issue #196, or perform a protected external effect.
8. Complete with a durable non-secret handoff naming the exact target files applied; source/candidate/live byte-match evidence; all mechanical check results; stopped/no-live-test confirmation; no-unrelated-toolset/no-route-mechanism confirmation; preserved-local-work and preserved-worktree confirmation; residual risk that direct-versus-pipeline behavior and live-hook efficacy remain unverified pending Christopher's manual test; and issue #196-open confirmation.

## Validation path and residual risk

The deliberately selected validation path is mechanical only. It can establish syntax, YAML parseability, toolset resolution, candidate/live byte identity, and diff hygiene. It cannot establish that Morfeo makes correct proportional route choices or that the live hook fires/effectively permits and denies the intended calls. Christopher owns that later manual direct-versus-pipeline and live-hook validation; the candidate worktree and immutable baseline remain preserved as its evidence.
