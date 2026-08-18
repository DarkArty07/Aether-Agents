# R5 Research: The Board as Aether's Topology

**Purpose**: Evidence for selecting the durable board, the profile layout, and the resolution of PD-18 and PD-26.  
**Upstream repository**: `https://github.com/NousResearch/hermes-agent.git`  
**Source inspected**: `home/.venv-hermes/src/hermes-agent` — the tree the Aether profile loads  
**Version**: 0.20.1, revision `411903b6fa258f81afcc3869eb615f6218e1776a`  
**Primary source**: `website/docs/user-guide/features/kanban.md`

## 1. Governing Decisions

Christopher selected the durable board and separate profiles. R4's corrected research established that upstream describes the board's purpose as Aether's architecture and that a profile per agent is upstream's explicit instruction. This stage builds on both.

The previous R5 was deleted, not revised. Its central argument — that profiles cannot exchange work — was false, and every downstream conclusion inherited the error.

## 2. Why the Board, in Upstream's Own Words

The board *"lets multiple named agents collaborate on work without fragile in-process subagent swarms. Every task is a row … every handoff is a row anyone can read and write; every worker is a full OS process with its own identity."*

That last clause is the strongest available satisfaction of Christopher's constraint that each role be a real agentic process. In-process delegation gives anonymous subagents; the board gives named processes with their own profiles, memory, and models.

Upstream's selection rule, reproduced because R5 is decided by it:

> "Use Kanban when work crosses agent boundaries, needs to survive restarts, might need human input, might be picked up by a different role, or needs to be discoverable after the fact."

All five hold for Aether. And among the workloads listed as covered by the board and not by delegation: *"Engineering pipelines — decompose → implement in parallel worktrees → review → iterate → PR."*

## 3. Concept Mapping

Aether's design maps onto the board with almost nothing left over.

| Aether concept | Board mechanism |
|---|---|
| Morfeo | Orchestrator profile — *"a well-behaved orchestrator does not do the work itself. It decomposes the user's goal into tasks, links them, assigns each to one of the profiles you've set up, and steps back."* |
| Supervising role | A worker on its own card that creates and links child cards |
| Implementer | Worker profile on an inexpensive model, one per card, many concurrent |
| Contract | Card title and body, plus parent handoffs and the comment thread |
| Unit of work | A card |
| Bounded blast radius | One card, one worktree, one attempt row |
| Convergence | Goal-mode card with a judge against the body as acceptance criteria |
| Escalation | `block(reason)` → comment → unblock; any profile or human may act |
| Review | Same-card review with a named reviewer profile |
| Evidence | Structured completion metadata plus durable rows, events, and attempt records |
| Parallel isolation | A git worktree per card |
| Crash recovery | Dispatcher reclaim of crashed and stale workers |
| Model tiering | Per-profile model, plus per-card override |
| Christopher's visibility | Dashboard, comments, board state |

## 4. Decisions

## R5-D01 — Aether's coordination primitive is the durable board

- **Need**: R4 established three primitives and handed the selection here.
- **Decision**: The board. In-process delegation remains available *within* a single worker's run for a bounded reasoning answer, but never to cross a role boundary.
- **Rationale**: All five of upstream's criteria for preferring the board are accepted Aether requirements, and two of them — surviving restarts and being picked up by a different role — are requirements the delegation path cannot satisfy at all. The board also removes the two constraints the deleted R5 treated as fixed.
- **Evidence**: `kanban.md:11, 32-53, 55-70`.
- **Alternatives considered**: In-process delegation was rejected because failed is failed, there is no human-in-the-loop, the audit trail is lost on context compression, and coordination is strictly hierarchical. A hybrid running both was rejected as two execution models to reason about.
- **Change impact**: Supersedes PD-26 and resolves PD-18. R6 loses most of its scope, since every Aether boundary is now within one host.

## R5-D02 — Three profiles, one per role, and no fourth role

- **Need**: Christopher wants separate profiles, and upstream instructs one per agent.
- **Decision**: Exactly three — `morfeo` on a frontier model with board, memory and research tools but no implementation tools; `supervisor` on a capable model; one `implementer` on an inexpensive model serving many concurrent cards.
- **Rationale**: Upstream's cost guidance is explicit that decomposition needs frontier judgment while executing a well-specified card usually does not, and that workers carry the vast majority of tokens. Restricting Morfeo's toolsets is upstream's own recommendation for orchestrators — *"pair it with a profile whose toolsets are restricted to board operations so the orchestrator literally cannot execute implementation tasks even if it tries"* — which turns PD-13 from an instruction into a structural property. One implementer profile rather than several follows the fleet pattern; concurrency is configured, not enumerated.
- **Evidence**: `kanban.md:482-500, 531-558, 790-800`; `profiles.md:13-16`.
- **Alternatives considered**: One profile per parallel worker was rejected as pointless multiplication.
- **Change impact**: R12 sets the model per profile. R10 must verify that toolset restriction actually prevents card creation by workers.

### Correction — a fourth role was proposed and withdrawn

The first draft of this stage added a `reconciler` profile as a fourth role, because upstream's collision guidance says a reconciliation card should go to *"a third, neutral profile"*. Christopher caught it: **PD-02 fixes the role count at three**, and adding one is a product decision that cannot be smuggled in as an implementation detail.

The withdrawal costs nothing, because neutrality does not require a role. Upstream's stated reason for neutrality is that *"the colliding agent lacks its peer's context and reliably overwrites the other side or abandons its own"* — the defect is the colliding worker's own biased context, not its role. Every dispatched worker starts with a completely fresh conversation, so a reconciliation card assigned to `implementer` reaches a worker that produced neither side and knows nothing of either run beyond what the parent links carry. That is the neutrality the guidance is protecting.

Two native mechanisms cover what a dedicated profile would have added:

- **Skills can be pinned to a specific card**, so the conflict-resolution procedure travels with the reconciliation card instead of requiring a profile that holds it permanently.
- **A per-card model override** can give reconciliation more capability than routine implementation, which is the honest argument for a fourth role — adjudicating two intents is harder than executing one — without creating one.

Recorded as a general rule in FR-509: an execution problem must be solved with fresh context, a pinned skill, or a model override before anyone proposes a role. Adding a role requires Christopher's decision against PD-02.

## R5-D03 — Per-card worktrees, which dissolves the parallelism constraint

- **Need**: The deleted R5 recorded that children share the parent's working directory and that parallelism was therefore bounded by file disjointness within one checkout.
- **Decision**: Implementation cards use a git worktree per card, preserved on completion. Work on an existing project in place uses an absolute directory. Research and decomposition use ephemeral workspaces with explicitly declared deliverables.
- **Rationale**: The shared-working-directory limit was a property of the in-process launch API, not of Hermes. The board offers a worktree workspace kind specifically for coding tasks, which is exactly the isolation the previous design could not obtain.
- **Evidence**: `kanban.md:55-70` on the three workspace kinds.
- **Alternatives considered**: A shared checkout with disjoint file assignment is no longer necessary. An ephemeral workspace for implementation was rejected because it is deleted on completion.
- **Change impact**: R7's concurrency ceiling rises substantially. R8 owns worktree naming, branch strategy, and integration order. R9 owns retention of preserved worktrees.

## R5-D04 — Escalation is a blocked card, not a lost run

- **Need**: PD-18 required Morfeo to receive contract defects. R4 found no upward channel in delegation and handed the mechanism to R7.
- **Decision**: A contract defect blocks the card with a reason. The card waits durably. Morfeo or Christopher comments and unblocks; a re-spawned worker reads the full comment thread as context. Sibling work is untouched.
- **Rationale**: This is upstream's human-in-the-loop pattern — *worker blocks → user comments → unblock* — and it satisfies every property the escalation needed: durable rather than a lost partial run, actionable by a different role, and scoped to one card. Comments are described as the inter-agent protocol, which makes them the channel rather than a workaround.
- **Evidence**: `kanban.md:55-70` on comments and blocked status; `kanban.md:902-916` pattern P5.
- **Alternatives considered**: Terminal return with re-delegation, which R4 had sketched, is no longer necessary and would discard the attempt. A separate escalation card was rejected because blocking keeps the history attached to the work.
- **Change impact**: PD-18 is resolved rather than pending. R7 designs when to block, not how to escalate.

## R5-D05 — Non-convergence blocks rather than exits

- **Need**: R1-FR-121 requires non-convergence to be a legitimate terminal outcome.
- **Decision**: Open-ended units run in goal mode with the card body as explicit acceptance criteria. Exhausting the turn budget blocks the card for human review.
- **Rationale**: Upstream implements precisely this, including the failure behaviour Aether specified — the budget running out *"blocks the card for human review rather than exiting silently."* The caveat is upstream's own: the judge is only as good as the goal text, which raises the stakes on writing card bodies as acceptance criteria rather than descriptions.
- **Evidence**: `kanban.md:513-529`.
- **Alternatives considered**: Applying goal mode universally was rejected on upstream's advice that per-turn judging is not worth it for cheap one-shot work.
- **Change impact**: R7 decides which units are goal-mode and what budget they carry. R2's acceptance criteria become load-bearing for the judge, not only for humans.

## R5-D06 — Collisions go to a neutral third profile

- **Need**: Parallel worktrees mean branches that must merge.
- **Decision**: Neither colliding worker adjudicates. A reconciliation card goes to `implementer` with both conflicted cards as parents, so both diffs and both intents arrive in the fresh context of a worker that produced neither side. The conflict-resolution skill is pinned to that card, and the card may carry a stronger per-card model. Repeated collisions in one file are flagged as hotspots, and two flags on the same path trigger a decomposition card for that file before more work touching it is queued.
- **Rationale**: Upstream states the failure mode directly: *"the colliding agent lacks its peer's context and reliably overwrites the other side or abandons its own."* The parent-link mechanism is what carries both intents, so the pattern depends on links rather than on a new primitive. Hotspot flagging is the upstream fix that prevents reconciliation from becoming a standing lane.
- **Evidence**: `kanban.md:954-988`, including the bundled reconciler skill.
- **Alternatives considered**: Letting the supervising role reconcile was rejected as re-concentration and because it would hold both roles' authority over one conflict.
- **Change impact**: R8 owns merge order. R7 owns creating reconciliation cards.

## 5. Superseded and Resolved

| Prior decision | Outcome |
|---|---|
| **PD-18** — Morfeo reachable for contract defects; mechanism pending | **Resolved.** A blocked card is the channel; any profile or human may act on it. |
| **PD-26** — unattended execution cannot survive a restart | **Superseded.** The unit of durability is the card, not the process. A crash costs one attempt. |
| R4's Gap 1 — no upward channel | Resolved for the board. Remains true of in-process delegation, which Aether no longer uses across roles. |
| R4's Gap 2 — no durability | Resolved. Dispatcher reclaim, heartbeats, bounded retries, and respawn guards. |
| Deleted R5's shared-working-directory constraint | Void. Worktrees are per card. |

## 6. Load-Bearing Details Worth Preserving

Details that will be easy to lose and expensive to rediscover:

- **An unknown assignee fails silently at dispatch.** Card creation must be grounded in profiles that actually exist.
- **Workers cannot see sibling cards.** Any decision two parallel cards depend on must be stamped into both bodies by the role that decomposes. Upstream's example is two halves of an import/export pair inventing incompatible formats.
- **A worker that exits without completing or blocking is a protocol violation**, nudged up to twice, then bounded-retried, then auto-blocked.
- **Ephemeral workspaces are deleted on completion.** Deliverables must be declared explicitly, and a missing declared artifact keeps the task in flight so the path can be corrected.
- **Heartbeats are required past an hour**, or the dispatcher reclaims the task as crashed.
- **The respawn guard** refuses re-spawn after a quota or auth error, after a recent success, or when a comment links an open pull request.
- **Absolute paths only** for directory workspaces; relative paths are rejected as a confused-deputy vector.
- **The board is single-host by design**, under a trusted-local-user threat model.

## 7. What Remains for R6

Every Aether role boundary is now a card on one board on one host. A2A exists, is complete, and targets cross-process, cross-machine and cross-framework boundaries — none of which Aether currently has.

R6's likely outcome is that A2A is available and unused, with the condition that would change it recorded: Aether spanning more than one machine, or exposing a role to a non-Hermes agent.

## 8. Source Verification of Load-Bearing Claims

Documentation claims that accepted decisions depend on were checked against the code, not only the docs.

### Card creation is NOT gated to orchestrators — containment is asymmetric

`toolsets.py:80-90` defines the board toolset as one flat set, enabled when the worker environment marks a dispatched task **or** when a profile explicitly opts in. `tools/kanban_tools.py` then gates each tool individually, and the split is narrower than assumed:

| Tool | Gate | Available to a worker? |
|---|---|---|
| `kanban_list` | orchestrator mode | **No** |
| `kanban_unblock` | orchestrator mode | **No** |
| `kanban_create` | board mode | **Yes** |
| `kanban_link` | board mode | **Yes** |
| show, complete, block, request_review, request_changes, heartbeat, comment, attach | board mode | Yes |

The orchestrator gate's own docstring explains the intent: *"Dispatcher-spawned workers should close their own task via the lifecycle tools, not enumerate or unblock board state."* Enumeration and unblocking are contained. **Creation and linking are not.**

**Consequence.** R5's first draft claimed role containment was structural. It is structural in one direction only: withholding implementation tools from the designer works, but an implementer cannot be structurally prevented from fanning out work. Recorded as PD-35 and FR-506a to FR-506d. The overclaim mattered because PD-13 — re-concentration as the standing risk — was the failure that killed the previous architecture, and an instruction is a weaker guard than a guarantee.

**What is genuinely structural for workers**, and therefore may be relied on: a worker cannot enumerate the board, and cannot unblock any card including its own. So an implementer cannot discover sibling work and cannot release itself from a block.

### The enforcement point for protected effects exists

`website/docs/user-guide/features/hooks.md:9-19` documents four hook systems. The load-bearing sentence: *"Hooks are not all passive: directive/control hooks can change flow, transforms can replace content, and a shell `pre_tool_call` hook can block or fail closed."*

**Consequence.** R1-FR-134 asserted that a small number of behaviours need automated support because instructions cannot guarantee them, without naming a mechanism. The mechanism is a blocking, fail-closed tool-call hook, registered per profile. This is R10's enforcement point and it is verified rather than assumed. It is also what makes FR-506c actionable.

### Spec Kit's checkout is current and singular

Checked because the same class of error already produced a false finding about Hermes. There is exactly one Spec Kit tree on this machine, its HEAD equals `origin/main` with zero commits behind, and Spec Kit is **not** installed as a package anywhere — so unlike Hermes there is no second, authoritative tree to confuse it with. The revision cited across R0 through R3 is the current upstream revision.

## 9. Risks

| Risk | Mitigation | Owner |
|---|---|---|
| A card body written as description rather than acceptance criteria weakens the judge | Acceptance criteria are already required by R2; goal mode makes them load-bearing | R7 |
| Workers can create cards, which could re-concentrate roles | Toolset restriction plus instruction; verify the restriction actually holds | R10 |
| Preserved worktrees accumulate | Retention policy | R9 |
| A hotspot file becomes a standing reconciliation lane | Two flags trigger decomposition before more work is queued | R7 |
| Board is not a security boundary between principals | Recorded as the trusted-local-user model | R10 |
| Dispatcher internals not yet inspected | Read by R7 before concurrency policy is set | R7 |
