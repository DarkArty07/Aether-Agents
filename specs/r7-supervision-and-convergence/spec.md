# R7 Specification: Supervision, Parallelism, and Convergence

**Roadmap ID**: R7
**Stage status**: in-progress — reopened for PD-73 autonomy and PD-74 E2E reliability qualification
**Accepted baseline**: 2026-08-17 — Christopher accepted the R4–R13 Decision Review
**Amended**: 2026-08-18 — scoped explicitly to work Morfeo dispatches under PD-44
**Amended**: 2026-08-21 — asymmetric starting capacity accepted: one Supervisor and three Implementers
**Reopened**: 2026-08-26 — local reversible judgement and integration repair are no longer forced through decision-card/guard ceremony
**Amended**: 2026-08-29 — one flow-bound Supervisor session/workspace accepted and live-qualified
**Decision authority**: Christopher
**Autonomous design delegate for this stage**: Hermes
**Future role owner**: Supervisor
**Depends on**: R2, R3, R5, R6, `DESIGN.md`
**May affect**: R8, R9, R10, R11, R12
**Parent roadmap**: `../../ROADMAP.md`
**Hermes evidence**: version 0.20.1, revision `411903b6fa258f81afcc3869eb615f6218e1776a`, source `home/.venv-hermes/src/hermes-agent`

## 1. Purpose

R7 specifies how a contract Morfeo dispatches to the pipeline becomes parallel work, what happens when a delegated unit cannot proceed, and how that work terminates. It does not govern a direct PD-44 action, because no delegated unit, Supervisor run, or cross-role convergence exists on that route.

The stage was scoped expecting to design decomposition, retries, and a convergence engine. All three exist in the runtime. What R7 actually owns is narrower and more consequential: **which of the runtime's behaviours Aether uses, which it must switch off, and what the supervisor decides that no mechanism can decide for it.**

R7 does not define branch or integration mechanics (R8), retention (R9), enforcement (R10), evidence format (R11), or model selection (R12).

## 2. Decomposition Belongs to the Supervisor

- **FR-700**: Every requirement in this stage applies when Morfeo has selected and dispatched the pipeline. A direct action MUST NOT be wrapped in a ceremonial contract, decomposition, review card, or integration unit merely to satisfy R7.

R3-D01 assigned `tasks` to the supervising role because a breakdown requires concrete file paths and knowledge of the real codebase. That assignment is now load-bearing in a way R3 could not have known, because the runtime ships a competing decomposer.

- **FR-701**: The supervisor MUST derive the breakdown from the contract, and MUST run cross-artifact analysis before creating any execution instance (R2-FR-214).
- **FR-701a**: The breakdown MUST be decomposed along **independently testable user stories**, which is what keeps one wrong unit cheap instead of fatal (R2 §8, R1 §4). A breakdown organised by layer or by file touches every story at once and destroys the bounded blast radius the contract relies on.
- **FR-702**: `tasks.md` is the breakdown of record; cards are execution instances of its units (PD-34). The supervisor MUST NOT create a card that traces to no unit.
- **FR-703**: The Supervisor does not own feature implementation. After fan-out it remains the decomposition/review/integration authority, but under PD-73 it MAY make a bounded integration repair (for example a conflict resolution, import, wiring, build/config glue, or reference correction) when that repair is strictly required to combine already-accepted units and introduces no new product behavior, acceptance criterion, shared-interface decision, or feature scope. Anything larger returns to an Implementer.
- **FR-704**: Every decision two sibling units would each have to make MUST be made once by the supervisor and written into **both** card bodies. Workers cannot see sibling cards, so an unstamped shared decision is a decision each worker invents differently.
- **FR-705**: Each card body MUST be written as explicit acceptance criteria, not as a description. This is a hard requirement rather than a style preference, because the convergence judge reads the body as its acceptance criteria (§7).

## 3. Two Runtime Defaults That Must Be Switched Off

Both are enabled by default and both silently take work away from the supervisor. Leaving either alone produces a system that reassigns work the contract never authorised.

### Automatic decomposition

The dispatcher runs an auxiliary language model over any card sitting in the triage column on every tick, reads the installed profile roster with their descriptions, and fans the card out into a task graph routed by profile description.

That is the supervisor's job, performed by a model that has not read the contract and routes on profile blurbs rather than on the breakdown.

- **FR-706**: Automatic triage decomposition MUST be disabled before any unattended run.
- **FR-707**: Automatic specification rewriting of triage cards MUST also be disabled, because it edits the body of a card that traces to a contract Aether owns.
- **FR-708**: No Aether card may be created in the triage column. Triage is the runtime's holding area for un-owned ideas; every Aether card has an owner by construction.

### The interaction that makes this urgent

The two defaults compose badly. The unblock-loop breaker routes a repeatedly-blocked card to triage, and automatic decomposition consumes whatever lands in triage. A unit that blocks twice for the same cause would therefore be handed to a generic model and split across profiles — the exact failure PD-13 names as the standing architectural risk.

- **FR-709**: The composition of loop-breaking and automatic decomposition MUST be treated as a defect surface, and the design MUST NOT rely on any card reaching triage benignly.

## 4. Parallelism

- **FR-710**: Parallelism MUST follow the breakdown's own independence markers and dependency ordering (R3-FR-303, PD-34). Aether MUST NOT add an independent concurrency policy on top of the breakdown.
- **FR-711**: Parallelism MUST be expressed as a concurrency limit against one implementer profile, never as additional roles or profiles (PD-30).
- **FR-712**: A board-wide concurrent-unit limit and explicit profile overrides MUST both be set. The accepted starting values are **four** board workers total, **one** Supervisor, and **three** Implementers. The runtime representation is `max_in_progress: 4`, uniform fallback `max_in_progress_per_profile: 3`, and overrides `supervisor: 1`, `implementer: 3` (PD-47).
- **FR-712a**: Ready and review dispatch MUST share the same effective profile limit and running count. Review must not bypass either the uniform fallback or an explicit override.
- **FR-712b**: A single Supervisor owns decomposition, review, convergence, and integration for one contract. Throughput is increased by releasing independent Implementer units; Aether MUST NOT duplicate Supervisors merely to consume more concurrency.
- **FR-713**: FR-712's numbers are calibration starting points, not derived constants. They MUST be revised from observed contract duration, idle time, worker occupancy, collision rate, integration cost, provider rate limiting, and host saturation; the revision MUST be recorded.
- **FR-714**: Units that would each edit the same file MUST NOT be dispatched concurrently. Independence in the breakdown means file-level independence, not merely logical separability.

### Flow-bound Supervisor continuity

- **FR-714a**: A pipeline root MUST carry the opaque `flow_id` returned by Objective Contract handoff preparation as `session_affinity={flow_id, terminal=false}`. The identifier is routing side data, not contract prose or product authority.
- **FR-714b**: All same-flow Supervisor phases MUST reuse one exact Hermes session and one canonical Supervisor workspace. Separate operating-system processes resume that session; they MUST NOT create a fresh task-keyed Supervisor worktree for review or integration.
- **FR-714c**: A same-flow same-profile child inherits the flow and shared workspace as `workspace_kind=dir`; a cross-profile child MUST NOT inherit Supervisor affinity. Every Implementer card receives a fresh session and its own project worktree.
- **FR-714d**: The runtime MUST fence the binding by board, Project, flow, profile, workspace, generation and lease. Resume MUST use the exact stored session with `--no-restore-cwd --in <canonical-workspace>` and reject missing, closed, corrupt, cross-profile, cross-Project, cross-flow, or stale-generation state.
- **FR-714e**: Exactly one terminal Supervisor card uses `terminal=true`. Ordinary decomposition, implementation, review and rework milestones remain silent to the origin; only explicit `input`, `revision`, or `flow_terminal` routing returns to Morfeo's owner-facing session.

## 5. Escalation — local judgement first, durable escalation when material

Christopher's original instruction remains authoritative at the material boundary:

> If an implementer blocks, the system resolves it through the supervisor, not me. If the system does not have enough information to be built, then it goes back up to Morfeo and he asks me what was never defined.

The 2026-08-26 simplification clarifies what **blocks** means. A normal implementation choice is not a block simply because the card did not spell it out.

### Tier 0 — Implementer decides locally

- **FR-715**: Implementer MUST decide a technical detail locally when the choice is reversible, testable inside its unit, does not change scope or acceptance criteria, does not alter an agreed shared interface, does not affect another independent unit, and does not grant new authority.
- **FR-716**: A Tier-0 choice MUST be visible in normal code/evidence when material to review, but it MUST NOT create a decision card merely to obtain permission for ordinary implementation judgement.
- **FR-717**: If several reasonable local implementations satisfy the same contract, choosing one is implementation work, not a contract defect.

### Tier 1 — material contract-supported decision

The existing decision-card mechanism remains useful when the choice affects shared execution or requires Supervisor judgement. It is no longer mandatory ceremony for every unanswered detail.

1. Implementer states the material question, candidate answers and consequences.
2. It creates a decision card addressed to Supervisor and links it as a parent of its own card.
3. The dependency gate returns the implementation unit to waiting.
4. Supervisor decides from the canonical contract and completes the decision card with a binding summary.
5. The implementation unit promotes and resumes with the decision.

- **FR-718**: Tier 1 SHOULD use the verified decision-card pattern rather than a human-visible block.
- **FR-719**: Implementer MUST NOT fan out product implementation or create sibling execution work on its own authority. This is a semantic/review rule under PD-73, not a pre-tool permission rule under R10.
- **FR-719a**: A decision card MUST carry the question, candidate answers and consequences; a card that only reports confusion is incomplete.

### Tier 2 — the contract is genuinely defective

- **FR-720**: When Supervisor determines that a material answer is not derivable from the contract and no safe local default preserves the same acceptance/interface contract, it MUST surface the missing product decision rather than invent one.
- **FR-721**: Tier 2 reaches Morfeo, who owns contract revision and asks Christopher only for the missing product/authority decision. Sibling units continue untouched.
- **FR-722**: The repaired decision is corrected in the artifact that owns it and propagated to affected work; unrelated units are not rematerialised.

### Separation rule

- **FR-723**: Local reversible technical judgement stays with Implementer; shared contract-supported judgement stays with Supervisor; genuinely missing product intent reaches Morfeo/Christopher. The system MUST NOT promote a lower tier merely because automation can represent the question as a card.

## 6. A Hard Limit That Cannot Be Configured Away

After a card is blocked, unblocked, and blocked again for the same cause, the runtime routes it to triage for a human decision. The threshold is a source-level constant, not a configuration key, and the counter deliberately survives each unblock, resetting only on successful completion.

- **FR-724**: Aether MUST treat the number of human-visible blocks per unit as effectively **one useful attempt**, and MUST design escalation so this budget is rarely spent. Tier 0 local judgement and Tier 1 durable decisions exist precisely to avoid spending it on ordinary technical uncertainty.
- **FR-725**: The limit MUST NOT be raised by patching the runtime. Modifying upstream core is prohibited (FR-403).
- **FR-726**: An answer to a blocked unit MUST resolve the underlying cause, not merely release the card. Releasing without resolving spends the last attempt.
- **FR-727**: Where a unit's difficulty is a dependency on other work rather than a missing decision, it MUST be expressed as a dependency wait, which returns the unit to waiting and auto-resumes without human involvement or recurrence accounting.

## 7. Convergence

The runtime provides a judge-driven continuation loop per card: after each turn an auxiliary judge checks the output against the card body as acceptance criteria, and continuation is fed back until the judge agrees, the worker terminates, or the turn budget is exhausted — which blocks the card for review rather than exiting silently.

- **FR-728**: Aether MUST NOT design a convergence engine. It configures the existing one (PD-25).
- **FR-729**: Goal-mode continuation MUST be applied to units whose completion is open-ended — "until the suite passes", "until every page is migrated" — and MUST NOT be applied to cheap one-shot units, where per-turn judging is not justified.
- **FR-730**: A unit in goal mode MUST carry a turn budget. The starting value is **twenty** turns, revised by evidence under FR-713.
- **FR-731**: The contract MUST carry the convergence budget at contract level (R2-FR-207); a per-unit budget is an instance of it and MUST NOT exceed it.
- **FR-732**: Budget exhaustion MUST be reported as *not converged*, a legitimate terminal outcome (R1-FR-121), and MUST NOT be reported as failure.
- **FR-733**: Because the judge reads the card body, FR-705 is a precondition for goal mode. A unit whose body is prose MUST NOT be run in goal mode.

## 8. Review

The runtime provides first-class same-card review: an implementer can hand its card to review with structured evidence, and the dispatcher claims it with a bundled review skill unless review dispatch is switched off. A reviewer approves, returns actionable rework, or escalates.

- **FR-734**: Review MUST be performed by a role that authored neither the requirements nor the code (R3-FR-318). The supervisor is that role.
- **FR-735**: Aether MUST NOT rely on the bundled review skill as its reviewer of record. It MAY be pinned to a review card as additional procedure, but the reviewing authority is the supervisor profile.
- **FR-736**: Returning rework MUST use the review return path rather than a block, so repeated review cycles do not consume the recurrence budget of §6.
- **FR-737**: Review MUST be same-card, so review history stays attached to the work it judges (R5-FR-526).
- **FR-737a**: **A reviewer verdict requires a claimed review run.** Verified by execution: returning rework is valid only while the unit is running under a run claimed from review, and it returns a diagnostic rather than failing loudly when it is not. A verdict issued against a unit merely sitting in review does nothing. Aether's review procedure MUST therefore run inside a dispatched review run, never as a direct write.
- **FR-737b**: Requesting review wakes a subscribed originator in the same way a block does. Review-time wakes MUST be scoped to Morfeo's own reasoning and MUST NOT reach the owner (R6-FR-619).

## 9. Attempts, Runtime, and Liveness

- **FR-738**: Every unit MUST carry an attempt limit. The starting value is **three** attempts before the unit auto-blocks with its last error.
- **FR-738a**: **A crash consumes an attempt.** Verified by execution: when the dispatcher detects a worker whose process is gone, it returns the unit to its source phase *and increments the consecutive-failure counter*. This is not the same as a stale-claim reclaim, which does not tick the counter. Environmental failure and defective work therefore draw on the same budget.
- **FR-738b**: The attempt limit MUST therefore be set above the number of environmental failures a single unattended session can plausibly produce. A limit of two means two machine sleeps, two network drops, or two provider outages exhaust a unit that never did anything wrong — and an exhausted unit auto-blocks, which then draws on the near-single human answer of FR-724. This is why FR-738's starting value is three rather than two.
- **FR-739**: Every implementation unit MUST carry a wall-clock limit. The starting value is **two hours** per attempt.
- **FR-740**: A unit expected to exceed one hour MUST emit liveness signals, or the dispatcher reclaims it as crashed and its current progress is lost.
- **FR-741**: A reclaim MUST be treated as benign — lost progress, not a failure (R5-FR-537).
- **FR-742**: Aether MUST NOT report an outcome the board does not record (R5-FR-538).
- **FR-742a**: Aether MUST NOT steer a running worker across a role boundary. Steering exists and stays available inside a single worker's own run (R4-FR-417), but crossing a role boundary always uses the board (PD-29). Redirecting already-dispatched work MUST therefore use the review return path (FR-736) or a Tier-1 decision card (FR-718), never an out-of-band interruption. A direct Morfeo action crosses no role boundary, so this rule does not require a card for it.

## 10. Collision Hotspots

- **FR-743**: A worker whose diff repeatedly collides in one file MUST flag it as a hotspot in a comment and repeat the flag in its completion evidence.
- **FR-744**: Two hotspot flags naming the same path MUST cause the supervisor to create a decomposition unit for that file before more work touching it is queued.
- **FR-745**: Hotspot flagging is inherited from the runtime's injected worker guidance. Aether's instructions MUST reinforce it, not restate it (PD-25).

## 11. Evidence

Executed directly against the recorded revision on an isolated board:

- Creating child units against an open parent leaves them waiting; completing the parent promotes them, and three independent siblings were released simultaneously.
- A completed unit's summary and structured metadata reach a dependent unit verbatim, alongside prior attempts and the full comment thread.
- Blocking one unit left its siblings untouched.
- **The decision-card pattern works as specified in §5**: creating a decision card and linking it as a parent returned the implementer's own card to waiting without a block; completing the decision card promoted the implementer's card and delivered the decision verbatim as parent handoff.
- The unblock-loop breaker fired on the **second** block of the same kind, routing the unit to triage with a recorded recurrence count.
- Diagnostics reported the triage decomposer as active on that unit, confirming the composition described in FR-709.
- The recurrence threshold is a module-level constant and appears nowhere in the configuration defaults.

A second pass verified what this list had deferred, using the dispatcher's injectable spawn function and direct calls into the board kernel — no profile, no agent, no model. Full record in [`../r13-synthesis-and-release/research.md`](../r13-synthesis-and-release/research.md):

- Worker spawn, workspace preparation, and run-row creation execute as specified.
- The concurrency limit is a **live cap**: with a limit of two and three eligible units, one tick spawned two and the next spawned none.
- Crash detection returns the unit to its source phase **and ticks the failure counter**, which forced FR-738 upward.
- The review lane claims a unit, spawns a reviewer, and routes rework back to the original implementer, with the recurrence counter untouched throughout.
- Disabling automatic decomposition is honoured and re-read each tick.

Still assumed: goal-mode judging, which needs a model in the loop.

## 12. Requirements Inherited by Later Stages

| Requirement | Owner |
|---|---|
| Concurrent units must not share a working tree; integration order follows the dependency graph | R8 |
| Preserved worktrees and durable rows accumulate and need retention | R9 |
| Protected external/irreversible effects remain edge-enforced; Implementer fan-out responsibility is verified by review/E2E rather than pre-tool card denial | R10, R11 |
| The two disabled defaults are configuration facts that must be verified before a run | R10, R13 |
| Completion evidence is the evidence base; not-converged is a reportable outcome | R11 |
| Goal-mode judging and the disabled auxiliary slots are model decisions | R12 |
| Starting values in FR-712, FR-730, FR-738, FR-739 are calibrated by the first authorized run | R13 |

## 13. Success Criteria

- **SC-701**: No unit is decomposed by anything other than the supervisor.
- **SC-702**: A reversible local technical detail is decided by Implementer without a decision card or human wake; a shared contract-supported question is resolved by Supervisor without waking a human.
- **SC-703**: A genuinely missing product/contract decision reaches Morfeo without any sibling unit stopping.
- **SC-704**: No unit reaches the triage column.
- **SC-705**: Two parallel units never edit the same file.
- **SC-706**: A non-converging unit terminates as not converged, with its budget recorded.
- **SC-707**: In the pipeline, no role reviews its own output. Direct PD-44 verification is not represented as independent pipeline review.
- **SC-708**: Every numeric limit in this specification is either observed or explicitly marked as an uncalibrated starting value.
- **SC-709**: No direct Morfeo action is materialized as a fake delegated unit, while every substantial objective selected for the pipeline remains governed by R7 in full.
- **SC-710**: Supervisor may repair integration glue without creating a new implementation unit only when the repair adds no new behavior; E2E evidence distinguishes that bounded repair from feature implementation.

## 14. Done When

- [x] Decomposition is assigned to the supervisor against a competing runtime default.
- [x] Both defaults that take work from the supervisor are identified and required to be disabled.
- [x] The interaction between loop-breaking and automatic decomposition is recorded as a defect surface.
- [x] Parallelism is expressed as concurrency limits with stated starting values.
- [x] Two-tier escalation is specified, and tier 1 is verified end to end in the runtime.
- [x] The unconfigurable recurrence limit is recorded as a hard design constraint.
- [x] Convergence is configured rather than designed, with its precondition stated.
- [x] Review is assigned without ceding reviewing authority to a bundled skill.
- [x] Attempt, runtime, and liveness bounds are set.
- [x] Christopher has reviewed the stage (R4–R13 Decision Review, 2026-08-17).
- [ ] Starting values are calibrated against a first authorized run.
