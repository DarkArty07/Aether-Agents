# R4 Specification: The Hermes Framework Boundary

**Roadmap ID**: R4  
**Stage status**: done  
**Accepted**: 2026-08-17 — Christopher accepted the R4–R13 Decision Review  
**Decision authority**: Christopher  
**Autonomous design delegate for this stage**: Hermes  
**Future role owner**: Morfeo  
**Depends on**: R0, R1, R2, R3, `DESIGN.md`  
**May affect**: R5, R6, R7, R8, R9, R10, R11, R12  
**Parent roadmap**: `../../ROADMAP.md`  
**Research**: `research.md`  
**Hermes evidence**: version **0.20.1**, revision `411903b6fa258f81afcc3869eb615f6218e1776a`, source `home/.venv-hermes/src/hermes-agent` — the tree the Aether profile actually loads.

> **This specification was rewritten on 2026-08-17.** Its first version was researched against a different checkout, version 0.19.1, which is not what Aether runs. Three of its findings were false. The record of the error and its retractions are in `research.md` §6b and §11.

## 1. Purpose

R4 determines what it concretely means that Hermes is Aether's foundation, and where Aether's own layer begins.

The governing finding, now correctly established: **Hermes ships three distinct coordination primitives, not one**, and one of them — the durable multi-profile board — is described upstream in terms that match Aether's intended architecture almost exactly. R4's job is to classify all three and to correct the earlier assumption that Aether's coordination layer had to be designed.

R4 does not choose which primitive Aether uses (R5), decide A2A's scope (R6), design supervision (R7), decide branch mechanics (R8), choose persistence (R9), or design enforcement (R10). R4 activates nothing and changes no configuration.

## 2. Three Coordination Primitives

| | In-process delegation | Durable board | A2A |
|---|---|---|---|
| Shape | Function call, fork and join | Durable queue with state machine | Protocol over HTTP |
| Worker identity | Anonymous subagent | **Named profile with persistent memory, a full OS process** | Independent agent, possibly another framework |
| Parent behaviour | Blocks until the child returns | Fire and forget after creation | Request or streamed task |
| Resumability | **None — failed is failed** | **Block, unblock, re-run; crash and reclaim** | Task lifecycle with polling and push |
| Human in the loop | Not supported | **Comment or unblock at any point** | Caller-mediated |
| Agents per unit of work | One call, one subagent | **Many over the unit's life — retry, review, follow-up** | One peer per call |
| Audit trail | Lost on context compression | **Durable rows, permanently** | Signed audit log per exchange |
| Coordination shape | Hierarchical, caller to callee | **Peer — any profile reads and writes any task** | Peer across process or machine |
| Per-unit model choice | No — the model pin is global | **Yes, per task** | Per peer |

- **FR-401**: Aether MUST classify a Hermes capability before adopting it, and MUST NOT adopt one merely because it exists.
- **FR-402**: Aether MUST NOT build a coordination mechanism that duplicates one of these three.
- **FR-403**: Aether MUST NOT fork or modify Hermes core. Adaptation belongs in configuration, profiles, skills, plugins, and prompts.
- **FR-404**: Every capability claim MUST record the Hermes version, because these claims are version-specific and one minor release already invalidated three of them.

### Upstream's own selection guidance

Hermes states when each primitive is appropriate. Aether MUST decide against this guidance rather than against availability:

- In-process delegation when the parent needs a short reasoning answer before continuing, with no human involved and the result returning into the parent's context.
- The durable board when work **crosses agent boundaries, must survive restarts, might need human input, might be picked up by a different role, or must be discoverable after the fact**.
- A2A when crossing process, machine, or framework boundaries.

- **FR-405**: Where Aether's requirements match upstream's stated criteria for a primitive, the burden of justification falls on choosing a different one.

## 3. The Finding That Reshapes Later Stages

Upstream describes the durable board's purpose as *coordinating multiple named profiles without fragile in-process subagent swarms*, and lists among the workloads it covers and delegation cannot: **decompose, implement in parallel worktrees, review, iterate, open a pull request.**

That is Aether's architecture, stated by the framework. Every criterion upstream gives for choosing the board is an accepted Aether requirement:

| Upstream criterion | Aether requirement |
|---|---|
| Work crosses agent boundaries | Three roles with separated authority (PD-02) |
| Must survive restarts | PD-26, which R4's earlier version recorded as an unavoidable limit |
| Might need human input | Christopher's review and acceptance (R1) |
| Might be picked up by a different role | Contract-defect escalation to Morfeo (PD-18) |
| Must be discoverable after the fact | Evidence and traceability (R2, R11) |
| Parallel worktrees | The shared-working-directory constraint R4's earlier version treated as fixed |

- **FR-406**: `DESIGN.md` §9's statement that the board subsystem is not selected was made without evidence and MUST be treated as an open decision, not a standing one.
- **FR-407**: The choice among the three primitives belongs to R5 and MUST be made on these criteria.
- **FR-408**: If Aether selects the board, PD-26 and the parallel-workspace constraint MUST be revisited, because both were recorded as framework limits that the board does not have.

## 4. Capabilities Aether Inherits

Verified against 0.20.1; see `research.md` §12.

> **Which primitive provides which.** R5 selected the durable board, so the board's equivalents are the ones Aether actually relies on. Rows below that describe in-process delegation — steering a running child, the progress-based stall monitor, per-child iteration limits — remain accurate but apply only inside a single worker's run, not across role boundaries. The board's counterparts are heartbeats with dispatcher reclaim, bounded retries, and per-card goal mode. Neither list is a menu to mix: crossing a role boundary always uses the board (PD-29).

| Aether requirement | Native capability | Class |
|---|---|---|
| Handoff completeness — the receiver must need nobody (R2 §2) | Children start with a completely fresh conversation; the parent must pass everything explicitly | Reusable, framework-enforced |
| No phase blocks on the owner (R3-FR-320) | Children cannot interact with the user | Reusable, structurally enforced |
| Authority neither inherited nor widened (R2-FR-206) | Children inherit the parent's toolsets; widening is rejected, narrowing is permitted per launch | Reusable, structurally enforced |
| No re-concentration of roles (PD-13) | Leaf children cannot delegate, write shared memory, message platforms, or schedule work | Reusable, structurally enforced |
| Attempt budget (R2-FR-207) | Per-child iteration limit; per-card goal mode on the board | Reusable |
| Bound on runaway execution (R1-D06) | Progress-based stall monitor with grace window and terminal stalled outcome | Reusable |
| Mid-flight correction without losing work | **Steering: list, steer, and stop a running child, with honest delivery semantics** | Reusable — was wrongly recorded as absent |
| Convergence until an objective is met | **Judge-driven continuation, available per session and per board card** | Reusable — Aether need not design a convergence engine |
| Role-tiered economics (`DESIGN.md` §7) | Global delegation model pin; **per-task model override on the board** | Reusable |
| Evidence of what a worker did | Append-only per-task transcripts and manifest; durable board rows | Reusable |
| Owner visibility (R1 §F) | Live subagent tree with per-branch cost, token and touched-file rollups; board dashboard | Reusable |
| Cancellation (R1 §D) | Cooperative, honored at the next safe boundary, ownership-scoped | Reusable |
| Owner preference memory (R3-D04) | Native curated memory and cross-session user modelling; per-profile peers over a shared user workspace | Reusable, pending direct inspection |
| Per-role isolation of credentials, memory, skills, prompt | **A profile per agent — upstream instructs this explicitly** | Reusable |

- **FR-409**: Where Hermes enforces an invariant structurally that Aether specified as an instruction, the structural enforcement is primary and the instruction is reinforcement.
- **FR-410**: Aether MUST NOT design a convergence engine, a steering channel, or an audit trail. All three exist.

### Capabilities found later, in a verification pass

Four native capabilities were missed by this classification and found by executing the runtime rather than reading it. Three of them do work Aether had assigned to a role, which makes them the most consequential omissions in this stage.

| Capability | Class | Consequence |
|---|---|---|
| **Automatic triage decomposition** — an auxiliary model fans out any card in the triage column, routing children by profile description | **Incompatible; must be disabled** | It performs the supervisor's phase without reading the contract (R7-FR-706) |
| **Automatic triage specification** — an auxiliary model rewrites a triage card's body | **Incompatible; must be disabled** | It edits a card that traces to a contract Aether owns (R7-FR-707) |
| **First-class same-card review** with a bundled review procedure and automatic reviewer dispatch | **Reusable, with a caveat** | Review is a transition rather than a block; the bundled procedure is not Aether's reviewer of record (R7-FR-735) |
| **Injected worker guidance** — a lifecycle and orchestration block placed in every board worker's system prompt | **Reusable, framework-provided** | Several R5 requirements restate it; Aether's prompts must build on it, never duplicate it (R13-FR-1328) |

- **FR-410a**: A native behaviour that performs a phase Aether assigned to a role MUST be classified as incompatible and disabled, not tolerated. Availability is not adoption, and a default is not a decision (FR-418).
- **FR-410b**: Classification MUST include behaviours that are **on by default**. This stage classified capabilities Aether might switch on and missed three that were already running.

## 5. Profiles Are the Isolation Boundary

Upstream is explicit that **every agent gets its own profile**, and states the failure mode plainly: two agent processes sharing one Hermes home both write memory automatically and each loads the other's writes into its system prompt, compounding state until it is no longer anything that was configured.

- **FR-411**: Aether MUST NOT point two independent agent processes at one profile.
- **FR-412**: A profile is the unit of isolation for configuration, credentials, personality, memory, sessions, skills, and scheduled work.
- **FR-413**: Agents that need shared memory MUST use an external memory provider rather than a shared home.
- **FR-414**: R4's earlier claim that profiles cannot exchange work is **withdrawn**. The durable board coordinates profiles on one machine, and A2A coordinates them across process or machine boundaries.
- **FR-414a**: **Refinement.** A2A is implemented as a **platform adapter**, registered alongside the messaging platforms rather than as a peer of the board. Inbound tasks are routed into the receiving agent's live session, exactly as a message from any other platform would be. It is therefore not a drop-in substitute for the board's per-unit fresh context, and R6 decides its scope on that basis rather than on protocol capability alone.

## 6. Remaining Gaps

Only one of the three gaps recorded earlier survives, and **R5 removed it from Aether's path** by selecting the board. It is retained because it still constrains delegation used inside a worker's own run.

- **FR-415**: **In-process delegation is not durable.** A running child does not survive a runtime restart, reconnection afterwards is unavailable, and the attempt is recorded as unknown because side effects cannot be proven. This is a property of delegation specifically, **not of Hermes**, and the board does not share it.
- **FR-416**: An interrupted run whose side effects cannot be established MUST be reported as indeterminate, never as success or failure.
- **FR-417**: In-process delegation provides no child-initiated upward channel. A child returns, or the parent steers it. Escalation design (R7) MUST work within that, unless R5 selects a primitive where blocking a unit of work for another role to pick up is native.

## 7. Availability Is Not Adoption

- **FR-418**: Messaging platforms, desktop surfaces, and scheduling remain unselected. Their presence in a live profile is not adoption.
- **FR-419**: Every capability relevant to an Aether requirement MUST be classified as reusable, adaptable, insufficient, incompatible, or unselected, with a reason.
- **FR-420**: A capability classified as unselected MUST record why, so a later stage does not silently reverse it — and MUST NOT be classified as unselected on the basis of unverified evidence, which is what happened to the board.

## 8. Boundary Policy

- **FR-421**: Hermes owns the runtime: conversation, tools, delegation, the board, A2A, terminal backends, memory, its own persistence, and observability of its own execution.
- **FR-422**: Aether owns the method: roles, phase assignment, the contract, quality standards, extraction behaviour, and the instructions that make each role behave as specified.
- **FR-423**: Where the two meet, Aether expresses itself through profiles, configuration, skills, and prompts.
- **FR-424**: An upgrade MUST be reviewed against this classification before an accepted Aether decision is treated as still valid. A single minor release invalidated three findings; this is not a hypothetical risk.

## 9. Requirements Inherited by Later Stages

| Requirement | Owner |
|---|---|
| Choose among the three coordination primitives on upstream's stated criteria | R5 |
| One profile per agent; never two processes on one home | R5 |
| Reconsider PD-26 and the parallel-workspace constraint if the board is selected | R5, R8, R9 |
| A2A is available and targets cross-process boundaries; decide its scope from R5's topology | R6 |
| Do not design a convergence engine — judge-driven continuation exists | R7 |
| Steering exists; redirecting a worker need not mean killing it | R7 |
| Parallel worktrees are native to the board, not to delegation | R8 |
| Durable rows are a permanent audit trail; delegation transcripts are not | R9, R11 |
| Per-task model override exists on the board but not in delegation | R12 |

## 10. Success Criteria

- **SC-401**: Every capability claim names an inspected file, the recorded revision, and the version.
- **SC-402**: Every claim is verified against the tree the runtime actually loads.
- **SC-403**: No Aether mechanism duplicates a native capability that satisfies its requirement.
- **SC-404**: Each of the three primitives is classified, with upstream's own selection criteria recorded.
- **SC-405**: No capability is recorded as unselected on unverified evidence.
- **SC-406**: A future upgrade can be assessed against this classification without re-deriving it.

## 11. Done When

- [x] The baseline is corrected to the source the runtime loads.
- [x] The three false findings are retracted with the record of how they occurred.
- [x] All three coordination primitives are classified, with upstream's selection guidance.
- [x] The match between the durable board and Aether's architecture is recorded.
- [x] Profiles are established as the isolation boundary.
- [x] The one surviving gap is stated as a property of delegation rather than of Hermes.
- [x] Requirements inherited by later stages are recorded.
- [x] Hooks inspected directly, including the consent allowlist that can render an enforcement point inert (PD-43).
- [ ] Still not inspected directly: memory internals, terminal backends, and the A2A adapter's implementation. Each is read by the stage that owns it.
- [x] Christopher has reviewed the corrected classification (R4–R13 Decision Review, 2026-08-17).
