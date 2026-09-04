# R5 Specification: Topology, Identity, and Isolation

**Roadmap ID**: R5  
**Stage status**: done — reconciled 2026-08-26 for PD-71/PD-73; role topology unchanged
**Accepted baseline**: 2026-08-17 — Christopher accepted the R4–R13 Decision Review
**Amended**: 2026-08-18 — PD-44 proportional direct execution accepted by Christopher
**Amended**: 2026-08-20 — PD-44 capability surface expanded and PD-45 accepted by Christopher
**Amended**: 2026-08-26 — role responsibility remains semantic while the pre-tool micro-permission boundary is retired
**Amended**: 2026-09-04 — autonomous stewardship, project guidance, and procedural skill precedence reconciled
**Decision authority**: Christopher  
**Autonomous design delegate for this stage**: Hermes  
**Future role owner**: Morfeo  
**Depends on**: R1, R2, R3, R4, `DESIGN.md`  
**May affect**: R6, R7, R8, R9, R10, R11, R12  
**Parent roadmap**: `../../ROADMAP.md`  
**Research**: `research.md`  
**Hermes evidence**: version 0.20.1, revision `411903b6fa258f81afcc3869eb615f6218e1776a`, source `home/.venv-hermes/src/hermes-agent`

> A previous R5 was designed on the false premise that Hermes profiles cannot exchange work, and was deleted rather than patched. Christopher selected the durable board and separate profiles. This specification is built on that selection.

## 1. Purpose

R5 makes Aether's roles real: which processes exist, which profile each runs under, what is isolated, how work moves between them, and what happens when a part fails.

Christopher's constraint governs: **each role is a real agentic process with its own reasoning loop.** The durable multi-profile board satisfies it in the strongest available form — every worker is a full operating-system process with its own profile, its own persistent memory, and its own model.

R5 does not decide A2A's scope (R6), design supervision policy or set concurrency numbers (R7), decide branch naming and integration mechanics (R8), choose retention (R9), or design enforcement (R10).

## 2. Selected Coordination Primitive

Aether uses the **durable multi-profile board**, chosen against upstream's own stated criteria. Every criterion it gives for preferring the board over in-process delegation is an accepted Aether requirement:

| Upstream criterion | Aether requirement |
|---|---|
| Work crosses agent boundaries | Three roles with separated authority (PD-02) |
| Must survive restarts | Hours of unattended execution (R1) |
| Might need human input | Christopher's review and acceptance (R1) |
| Might be picked up by a different role | Contract-defect escalation (PD-18) |
| Must be discoverable after the fact | Evidence and traceability (R2, R11) |

- **FR-501**: Aether MUST use the durable board as its coordination primitive.
- **FR-502**: In-process delegation MAY be used *inside* a single worker's run when that worker needs a bounded reasoning answer before continuing. It MUST NOT be used to cross a role boundary.
- **FR-503**: Aether MUST NOT build queueing, state, retry, reclaim, or audit machinery. All of it exists.

## 3. Profiles

One profile per agent (PD-27). Each is a separate Hermes home with its own configuration, credentials, personality, memory, sessions, and model.

**Three roles, three profiles.** PD-02 fixes the role count, and R5 does not change it.

| Profile | Role | Model tier | Owns |
|---|---|---|---|
| `morfeo` | Owner interlocutor, contract architect, and direct operational steward | Frontier | `constitution`, `specify`, `clarify`, `plan`, bounded direct operations |
| `supervisor` | Decomposition, executability analysis, review, convergence, integration | Capable | `tasks`, `analyze`, `checklist`, `converge` |
| `implementer` | Writes the code | Inexpensive | `implement` |

By PD-45, `skills` and `vision` are base toolsets for all three profiles. They add access to skill-document management and visual inspection without changing any role's decision authority or owned work.

- **FR-504**: Aether MUST have exactly three agent roles, each under its own profile. Two agent processes MUST NOT share a Hermes home.
- **FR-505**: A single `implementer` profile MUST serve many concurrent cards. Concurrency is a dispatcher limit, not a profile count, so parallelism MUST NOT be expressed by adding roles or profiles.
- **FR-506**: `morfeo` MUST expose board, file, and terminal toolsets, together with the existing memory and research surfaces composed for its platform. File access is general within the project it is managing; terminal enables direct operational stewardship. Only browser execution and computer use remain excluded from Morfeo's operational surface.

### Responsibility is semantic; selected runtime gates remain structural

Morfeo's route boundary is agentic rather than structurally enforced: its operational capability is broader than the direct work it should choose. Implementer also has ordinary board/file/terminal capability within its dispatched context; that capability is not product authority. Board enumeration and unblocking remain structurally gated to orchestrators by Hermes.

- **FR-506a**: An `implementer` MUST NOT fan out sibling product implementation or widen its own unit scope on its own authority. A material shared question may use the Tier-1 decision-card pattern in R7. This is a semantic/review obligation under PD-73, not a pre-tool card-creation denial.
- **FR-506b**: Aether MUST NOT describe Morfeo's direct-versus-pipeline judgement or any role's ordinary local technical responsibility as structural or hook-enforced. It is agentic responsibility, evidenced by the resulting artifacts and E2E behavior.
- **FR-506c**: R10 protects only PD-71 edge effects. Card creation/linking, ordinary local Git/file use, artifact inspection and reversible implementation choices are not protected effects solely because a role could misuse them.
- **FR-506d**: Two useful restrictions **are** native/structural for dispatched workers and MAY be relied on operationally: a worker cannot enumerate the board, and a worker cannot unblock a card — including its own. They are not a security boundary between principals.
- **FR-506e**: Portable `config.yaml`, `SOUL.md`, and the reconciled minimal R10 policy MUST be versioned and activated coherently. The public profile bundle therefore carries both behavior and configuration bytes for every role.
- **FR-506f**: No classifier, score, threshold, special board lane, or hook may decide whether Morfeo acts directly. The complete owner objective is the unit of judgement; fragmentation into small mutations MUST NOT change the route.
- **FR-506g**: Under amended PD-44, Morfeo MAY use `code_execution`, `cronjob`, and `delegation` (`delegate_task`) on both CLI and Telegram. `code_execution` supports bounded direct work with many repetitive mechanical steps. Cron may schedule Morfeo's own follow-up or a future pipeline start, selected case by case through the same whole-objective reasoning as the direct/pipeline route, and MUST NOT establish permanent autonomy beyond an owner-requested objective. Delegated subagents may assist only Morfeo's own bounded direct work and MUST NOT receive product implementation belonging to Supervisor/Implementer. As with FR-506b's route choice, that delegation boundary is agentic self-control, not structural or hook-enforced.
- **FR-507**: Model tiering MUST be expressed per profile, with a per-card override reserved for quality-sensitive units.
- **FR-508**: Every card's assignee MUST name a profile that exists. Assignment MUST be grounded in actual profiles before a card is created.
- **FR-508a**: **Corrected by execution.** An unknown assignee does not fail loudly and does not fail silently everywhere: the dispatcher reports it in its own output as a skipped non-spawnable lane and treats it as legitimate, because an assignee that is not a local profile is a supported external-worker shape. **Nothing is written to the card** — its event history shows only creation and promotion. A typo'd assignee therefore leaves a unit waiting forever and is invisible at the place anyone would look. Detection MUST come from the board's health snapshot, which reports a unit whose assignee never produces a claim (R11-FR-1122).
- **FR-509**: A new role MUST NOT be introduced to solve an execution problem. Fresh context, a pinned skill, or a per-card model override MUST be tried first, and adding a role requires Christopher's decision against PD-02.
- **FR-509a**: Aether MUST retain exactly three roles. In pipeline work, Supervisor owns review, integration, aggregate `release_impact`/`release_action`/`release_channel` classification, normal GitHub PR/check/merge closeout, applicable issue/milestone reconciliation, and terminal evidence; Implementer owns bounded local unit work and commits but never publication. In bounded direct work, Morfeo owns authorized routine closeout.
- **FR-509b**: Role procedures MUST remain subordinate to authority. Agents discover only task-relevant Aether or project canonical skills through root `AGENTS.md`, direct project-relative reads, card pinning, or an existing native mechanism; no hard-coded skill list, loader, or new role is introduced by R5.
- **FR-509c**: Every project MUST have accurate root `AGENTS.md` guidance. Morfeo establishes missing guidance after repository inspection and constitution confirmation, the role whose authorized change invalidates guidance updates it, and Supervisor verifies coherence before pipeline closure. Brownfield guidance is preserved and reconciled.

### Concurrent processes

At any moment Aether runs one `morfeo` and, when Morfeo dispatches substantial work, one `supervisor` and up to N `implementer` workers, where N is the configured concurrency limit. The role count remains three; a direct action creates no new role or worker.

## 4. Boards Are the Project Boundary

- **FR-510**: Aether MUST use one board per project. A worker is pinned to its board at spawn and cannot see another.
- **FR-511**: The board is the hard isolation boundary between projects. Namespacing within a board is a soft filter and MUST NOT be relied on for isolation.
- **FR-512**: The board is single-host by design, under a trusted-local-user threat model. Aether MUST NOT treat it as a security boundary between principals, and R10 MUST record this.

## 5. Workspaces — Parallel Isolation, Solved

The constraint that defeated the previous design does not exist here. The board provides three workspace kinds, and one is a git worktree per card.

| Aether work | Workspace kind | Behaviour |
|---|---|---|
| Implementing a unit | `worktree` — a git worktree per card | Preserved through review, integration, and publication; cleaned after durable terminal evidence |
| Work on an existing project in place | `dir:<absolute path>` | Preserved; must be absolute |
| Research, analysis, decomposition | `scratch` | Deleted on completion; declared artifacts copied to durable storage first |

- **FR-513**: Implementation cards MUST use a per-card git worktree. This is the isolation the earlier design could not obtain.
- **FR-514**: Parallel implementers therefore MUST NOT share a working tree, and parallelism is no longer bounded by file disjointness within one checkout.
- **FR-515**: A `dir:` workspace MUST be an absolute path. Relative paths are rejected at dispatch as a confused-deputy vector.
- **FR-516**: A card whose workspace is ephemeral MUST declare its deliverables explicitly, or they are lost on completion.

## 6. How Work Moves

```text
Christopher ──conversation──► morfeo
                    │
                    ├── bounded operational objective ──► Morfeo acts directly
                    │                                      and verifies the result
                    │
                    └── substantial objective ──► one contract card
                                                   ▼
                                             [ supervisor ]
                                                   │  derives breakdown and analyzes
                                       ┌───────────┼───────────┐
                                       ▼           ▼           ▼
                               [ implementer ] [ implementer ] [ implementer ]
                                       └───────────┼───────────┘
                                                   ▼
                                           [ integration card ]
```

### The seam between the breakdown and the board

Spec Kit produces `tasks.md`; the board executes cards. Nothing until now said how they relate, and leaving it implicit would produce two competing records of what work exists.

- **FR-516a**: `tasks.md` is the **breakdown of record** and belongs to the contract. Cards are **execution instances** of the units it names. There is one plan and one execution surface, never two plans.
- **FR-516b**: Every pipeline implementation card MUST trace to a unit in `tasks.md`, and every unit intended for pipeline execution MUST be materialized as a card. A direct PD-44 action is not a pipeline unit and MUST NOT be represented by a false implementation card merely to satisfy this rule.
- **FR-516c**: When convergence appends remaining work to `tasks.md`, each appended unit MUST be materialized as a new card rather than reopening a completed one.
- **FR-516d**: The breakdown's parallel markers MUST determine card independence, and its dependency ordering MUST determine parent links.
- **FR-516e**: A card MUST NOT be edited to change what the contract asks for. Intent changes at the artifact that owns it, and the board is re-materialized from the corrected breakdown.

- **FR-517**: When Morfeo selects the pipeline, it MUST hand the contract over as exactly one card assigned to `supervisor`. Morfeo MUST NOT create implementation cards, because decomposition belongs to the supervising role (R3-D01). Direct PD-44 work requires no handoff card because no role boundary is crossed.
- **FR-518**: The supervising role MUST create child cards, link them to their integration card, and then step back. It MUST NOT perform the implementation itself.
- **FR-519**: Every child card body MUST carry every decision it depends on. Workers cannot see sibling cards, so a decision left implicit is a decision each worker will invent differently. This is R2's handoff completeness principle at the card level.
- **FR-520**: Any decision two parallel cards would each have to make MUST be made once by the supervising role and stamped into both bodies.
- **FR-521**: Completion MUST carry structured evidence answering what changed, how it was verified, what would unblock a retry, and what risk is deliberately left open.
- **FR-522**: A parent link MUST be used as the context handoff channel. A child receives each completed parent's summary and evidence verbatim.

## 7. Escalation and Human Input — PD-18 Resolved

The board provides the upward channel the previous design could not find.

> **Superseded in part by R7 §5.** This section was written treating "block with a reason" as the single escalation mechanism. Execution against the runtime showed two things that split it in two. First, blocking is a **scarce** resource: after one block, one release, and a second block for the same cause, the unit is routed out of the work pool by a source-level constant that configuration cannot raise. Second, a question the contract can answer does not need a human at all — a decision card linked as a parent of the asking unit returns it to waiting and resumes it automatically, using only worker-available tools. R7 owns the two-tier model; the requirements below now describe **tier 2 only**, the case where the contract itself is defective.

- **FR-523**: A **contract defect** MUST be raised by blocking the card with a reason and a type. The card waits durably; it is not a lost run.
- **FR-523a**: A question the contract *can* answer MUST NOT be raised by blocking. It is a tier-1 escalation and MUST use the decision-card pattern (R7-FR-715), which consumes no part of the block budget.
- **FR-523b**: A block MUST carry its type. A unit waiting on other work is a dependency wait, which returns it to waiting and auto-resumes without any human; only a missing input or a missing capability surfaces to a person.
- **FR-524**: Morfeo or Christopher MUST be able to comment on a blocked card and unblock it. Comments are the inter-agent protocol, and a re-spawned worker reads the full thread as context.
- **FR-525**: Escalation MUST NOT discard completed sibling work. Blocking is scoped to one card.
- **FR-526**: Review MUST use same-card review with a named reviewer profile rather than a new card, so that review history stays attached to the work it judges.
- **FR-526a**: Same-card review is a **first-class transition, not a block**, so repeated review cycles do not consume the block budget of FR-527b. Returning rework MUST use the review return path (R7-FR-736).
- **FR-526b**: The runtime dispatches review by claiming the unit with a bundled review procedure unless that behaviour is disabled. Aether MAY keep it as additional procedure but MUST NOT treat it as its reviewer of record; the reviewing authority is the supervisor profile (R7-FR-735).
- **FR-527**: An external failure — a tool or framework not doing what it should — MUST also block with a reason rather than fail silently, so it reaches Christopher durably.
- **FR-527a**: Christopher is **not** the first responder to a stuck unit. His instruction, recorded 2026-08-17: the system resolves it through the supervisor; only work that cannot be built because something was never defined returns to Morfeo and then to him (R6-FR-618, R7-FR-723).
- **FR-527b**: Aether MUST treat the human-visible block budget as effectively **one useful attempt per unit**, and MUST NOT design any routine flow that spends it. The threshold is a source constant, not configuration, and raising it would require modifying upstream core, which FR-403 forbids.
- **FR-527c**: A unit that exhausts the budget is routed to the triage column, where the runtime's automatic decomposer would consume it and split it across profiles. That composition is a defect surface, and it is why R7-FR-706 requires automatic decomposition to be disabled before any unattended run.

## 8. Convergence

- **FR-528**: A unit whose completion is open-ended MUST run in goal mode, where a judge checks the worker's output against the card body as acceptance criteria and continuation is fed back until it agrees.
- **FR-529**: A card body used as acceptance criteria MUST be written as explicit acceptance criteria. The judge is only as good as that text.
- **FR-530**: Exhausting the turn budget MUST block the card for human review rather than exit silently. This is R1-FR-121's legitimate non-convergence, natively.
- **FR-531**: Goal mode MUST NOT be applied to cheap one-shot units, where per-turn judging cost is not justified and existing retry handling suffices.

## 9. Identity and Correlation

- **FR-532**: Every delegated unit of work MUST be identified by its card, and every delegated attempt MUST be recorded as its own row. A direct Morfeo action remains attributable to Morfeo's current session and repository diff or command evidence rather than inventing a board unit.
- **FR-533**: Pipeline role attribution MUST come from the card's assignee profile; direct action attribution comes from Morfeo's profile and session.
- **FR-534**: Aether MUST use the board's durable rows, events, comments, and attempt records as its record. It MUST NOT build a parallel one.
- **FR-535**: A pipeline repository change MUST be attributable to a card, profile, and attempt. A direct PD-44 change MUST be attributable to Morfeo's profile and session, with the actual diff or command result available for inspection.

## 10. Failure and Recovery — PD-26 Resolved

Restart durability was recorded as an unavoidable limit. It was a limit of in-process delegation, not of Hermes.

| Failure | Native handling |
|---|---|
| Worker crashes | The dispatcher reclaims the task; it returns to ready for re-dispatch without a failure tick |
| Worker hangs | Reclaimed after the stale timeout when heartbeats stop |
| Worker exits without completing or blocking | Treated as a protocol violation, nudged, then bounded retry, then auto-block |
| Repeated spawn failure | Auto-blocked with the last error as the reason after the failure limit |
| Quota or auth error, recent success, or an open pull request | Respawn is refused, preventing worker storms |
| Gateway restarts | The dispatcher restarts with it and reclaims what was in flight |

- **FR-536**: Long-running work MUST heartbeat, or it will be reclaimed as crashed and lose its current progress.
- **FR-537**: A reclaim MUST be treated as benign — lost progress, not a failure.
- **FR-538**: Aether MUST NOT report an outcome the board does not record. Success and failure both come from a terminal board state.
- **FR-539**: PD-26 is superseded: unattended work **does** survive a restart, because the unit of durability is the card rather than the process.

## 11. Collision Handling

- **FR-540**: When two workers' branches conflict, neither MUST self-adjudicate. A colliding worker lacks its peer's context and will either overwrite the other side or abandon its own.
- **FR-541**: A reconciliation card MUST be created and assigned to `implementer`, with both conflicted cards as parents so both diffs and both intents reach it. Neutrality comes from the **fresh context** every dispatched worker starts with, not from a fourth role: the worker that resolves the conflict produced neither side and knows nothing of either run beyond what the parent links carry.
- **FR-541a**: A reconciliation card MUST pin the conflict-resolution skill to that card rather than to a profile, so no role exists solely to reconcile.
- **FR-541b**: A reconciliation card MAY carry a per-card model override, since adjudicating two intents is harder than executing one. This is the mechanism for giving reconciliation more capability without giving it a role.
- **FR-542**: A worker that notices repeated collisions in one file MUST flag it as a hotspot in a comment and in its completion evidence.
- **FR-543**: Two hotspot flags naming the same path MUST trigger a decomposition card for that file before more work touching it is queued. Splitting a magnet file is cheaper than reconciling every future collision.

## 12. Requirements Inherited by Later Stages

| Requirement | Owner |
|---|---|
| Within one host the board suffices; A2A applies only if Aether ever spans hosts | R6 |
| Set board-wide and per-profile concurrency limits | R7 |
| Decide when a unit runs in goal mode and what turn budget it carries | R7 |
| Worktree naming, branch strategy, and integration order | R8 |
| Retention of durable rows, attachments, and preserved worktrees | R9 |
| Workers can create/link cards; semantic fan-out responsibility is verified by review/E2E while only PD-71 edge effects are hook-enforced | R7, R10, R11 |
| Portable role configuration and `SOUL.md` behavior bytes are activated coherently with the reconciled minimal policy | A1, R10, R13 |
| The board is single-host under a trusted-local-user model | R10 |
| Structured completion evidence is the evidence base | R11 |
| Per-profile models plus per-card override | R12 |

## 13. Success Criteria

- **SC-500**: Aether has exactly three agent roles. No execution problem was solved by adding one.
- **SC-501**: Each role runs as its own operating-system process under its own profile.
- **SC-502**: Two parallel implementers never share a working tree.
- **SC-503**: A worker crash or gateway restart loses at most one attempt's progress, never the unit of work.
- **SC-504**: A contract defect reaches Morfeo durably without discarding sibling work.
- **SC-505**: Every pipeline repository change is attributable to a card, profile, and attempt; every direct change is attributable to Morfeo's profile, session, and actual diff or command evidence.
- **SC-506**: Non-convergence blocks for review rather than exiting silently.
- **SC-507**: Aether adds no queue, state machine, retry, reclaim, or audit mechanism of its own.
- **SC-508**: Morfeo has file and terminal capability for bounded direct operations, no unrelated toolset is enabled, and substantial work still crosses the role boundary through one Supervisor card.
- **SC-509**: Pipeline closeout remains owned by Supervisor while bounded direct closeout remains owned by Morfeo, with Implementer limited to local unit work and commits.
- **SC-510**: All roles use task-relevant procedural skills without turning skills into authority or adding a role, loader, or coordination mechanism, and every project has accurate root `AGENTS.md` guidance before pipeline closure.

## 14. Owner correction resolved: Morfeo is also the owner's operational steward

During analysis of DOC-09/P5-F13, the owner corrected the responsibility model: Morfeo is not only Aether's contract architect; Morfeo is also the owner's operational assistant and must perform direct project stewardship, including terminal- and GitHub-mediated work, when the complete objective does not justify the full multi-role pipeline.

The blanket removal of terminal and general project writing was a design error, not a safety principle. Permanent role reconcentration remains prohibited, while bounded proportional execution is legitimate. Route selection belongs to Morfeo's reasoning over the complete owner objective, with anti-fragmentation and direct-to-pipeline route change required by R1-FR-133a through FR-133d.

The owner has now resolved the previously open boundary: no classifier, threshold, fast lane, fourth role, or route-selection gate is added; feature-scale product work remains in the pipeline; PD-71 narrows protected effects to the irreversible/external edge; Git provides ordinary rollback where applicable. PD-74 now requires functional E2E validation of Morfeo's route judgement through the disposable real-path harness rather than deferring that validation to owner intuition. Until the model-backed reliability gate is explicitly authorized and passes, route quality remains implemented but not fully qualified.

## 15. Done When

- [x] The coordination primitive is selected against upstream's criteria.
- [x] The profile per role is defined with its model tier and owned phases.
- [x] Boards are established as the project boundary.
- [x] Per-card worktrees resolve the parallel-isolation constraint.
- [x] The path work takes between roles is defined.
- [x] Escalation and human input resolve PD-18.
- [x] Convergence and non-convergence are defined.
- [x] Failure handling supersedes PD-26.
- [x] Collision handling follows upstream's neutral-reconciler pattern.
- [x] Load-bearing claims verified in source, not only documentation: native board/tool gating, the real pre-tool interception surface, and the currency of the Spec Kit checkout.
- [x] Structural runtime gates are distinguished from semantic role responsibility rather than overclaimed as role isolation.
- [x] The R13 build contradiction between Morfeo's stewardship and its absent file capability is corrected; portable `config.yaml` + `SOUL.md` activation now carries the reconciled behavior contract while R10 protects only PD-71 edge effects.
- [x] PD-44 replaces the obsolete no-execution boundary with proportional direct stewardship while preserving three roles, pipeline separation for substantial product work, and the anti-fragmentation rule.
- [x] Corrected against execution, not only reading: escalation is now proportional Tier 0/1/2, the block budget remains effectively one human-visible attempt, the unknown-assignee behaviour is stated accurately, and the review lane remains a first-class transition with a bundled procedure.
- [x] Pipeline and direct-route stewardship ownership, project guidance duties, and task-relevant procedural-skill discovery are reconciled without changing the three-role topology.
- [x] Dispatcher internals inspected and executed: claim, workspace preparation, spawn, live concurrency capping, crash detection, stale reclaim, and the review claim path.
- [ ] Still not inspected: memory-provider internals and terminal backends. Each is read by the stage that relies on it — R9 and R8 respectively.
- [x] Christopher reviewed the baseline (R4–R13 Decision Review, 2026-08-17), accepted PD-44 on 2026-08-18, and accepted the capability amendment plus PD-45 on 2026-08-20.
