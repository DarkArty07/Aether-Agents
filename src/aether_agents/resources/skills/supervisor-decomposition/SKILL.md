---
name: supervisor-decomposition
description: Use when Supervisor decomposes or reviews units.
version: 0.1.1
author: Morfeo (Aether role), Hermes Agent
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [supervision, decomposition, parallelism, review]
    related_skills: []
---

# Supervisor Decomposition and Coordination

Translate one finalized design into traceable independently testable units, then
coordinate and independently review their evidence. This procedure cannot grant
authority, invent product design or replace the native board lifecycle. Morfeo owns
material intent/design; Supervisor owns execution decomposition; Implementer owns
bounded implementation. More workers are not a quality or performance guarantee.

## When to Use

- Use when Supervisor receives a finalized Objective Contract for decomposition.
- Use for reviewing a breakdown, diagnosing avoidable serialization, or returning rework.
- Do not use to dispatch direct Morfeo work or let Implementer fan out product work.
- Morfeo and Implementer may read delivery criteria as evidence; this skill does not
  assign them Supervisor's decomposition, independent review or integration phase.

## Prerequisites

Verify the envelope, Project, exact contract bytes, base and referenced canonical
artifacts. Read root `AGENTS.md` and discover relevant canonical procedures using the
project-relative convention and native discovery. Inspect the actual repository,
existing `tasks.md`, relevant board state and provisioned profiles/capacity. Treat
current limits and authority as constraints, not settings to tune during decomposition.

## Procedure

1. **Check receipt, not just the digest.** Locate requirements, material design,
   interfaces, acceptance, authority and runnable validation. Identify contradictions
   or genuinely missing product decisions before inventing a breakdown around them.
   Return a contract defect to Morfeo. Do not require irrelevant diagrams or escalate
   equivalent reversible local choices that already preserve the contract.
   Stop receipt investigation when the design and dependency decisions needed to write
   executable units are known. Before another broad read, name the unanswered question
   and which scope, dependency or acceptance choice it affects. Do not perform each
   Implementer's local investigation yourself or reread unchanged evidence for reassurance.
2. **Derive independently testable outcomes.** Create or update only Supervisor-owned
   `tasks.md`, mapping each buildable requirement to execution and verification units
   and each unit back to its source. Account separately for non-build obligations such
   as preservation and authority. Do not partition by arbitrary file count, by technical
   layer alone, or into tiny busywork to fill slots. Review this draft with the owning
   spec/plan before creating execution instances.
3. **Explain dependencies and shared decisions.** For every edge, name the prerequisite
   artifact, verified state or shared-file ownership that necessitates it. Resolve
   contract-supported shared execution choices once and stamp them into affected unit
   bodies. A missing material API/design decision returns to Morfeo, not a worker vote.
   Identify shared writable files; concurrent edits to the same file are not independent
   under the current Aether policy. Split behavior at an already agreed boundary or
   serialize the conflict; do not redesign a module just to make the graph look parallel.
4. **Find useful parallelism.** Mark units independent only when prerequisites,
   interfaces and file ownership permit separate implementation and tests. Explain a
   materially concentrated unit's non-splittable dependency or collision, not merely
   "same feature". Check for false edges between unrelated outcomes. Never require a
   fixed worker count or raise runtime limits. Finish when both necessary serialization
   and available independence are explicit in the existing breakdown.
5. **Write executable unit deliveries.** Use the compact delivery below, with concrete
   values or a precise canonical reference for each relevant item. Include the shared
   decisions a worker cannot see in sibling context. Do not paste the complete Objective
   Contract or opaque routing values. Acceptance must describe observable completion,
   not "work on the feature". Pin only relevant installed skills, not every procedure.
6. **Validate the graph and dispatch.** Check complete source coverage, real assignees,
   dependencies, isolated workspaces, scopes, acceptance and terminal review ownership.
   Use the existing `kanban_create`/`kanban_link` mechanisms and runtime lifecycle;
   never introduce a second queue, automatic decomposer or in-process product swarm.
   Materialize independent calls together where supported. Complete the decomposition
   root once its verified handoff is done so its parent-gated children can run; do not
   hold it open to supervise their implementation. Preserve the exact flow-affinity
   rules and create no root goal loop that waits for the implementation it parent-gates.
7. **Coordinate without busywork.** Let ready independent units run within existing
   capacity. A genuine prerequisite may wait; an unrelated review, documentation task
   or optional investigation must not become an invented barrier. Use board state and
   run evidence, not current assignee totals or heartbeats alone, to distinguish queue
   wait, useful work, external failure and rework. Route problems using the existing
   review/dependency/contract-defect paths. Do not interrupt healthy active workers.
8. **Revisit a bad split proportionately.** Investigate repeated hotspots or a unit
   that now demonstrably spans independently deliverable outcomes. Reconcile future
   work in `tasks.md` and the board under the existing lifecycle; do not duplicate active
   scopes, silently rewrite final contracts, widen the objective or create new roles.
   Respect contract attempt/convergence bounds; do not invent stricter acceptance gates.
9. **Review the implementation, not the narration.** Read the actual diff and run
   evidence against the unit's requirements, interfaces, preservation and oracles.
   Re-run proportionate checks when required. A missing obligation is rework even if
   the summary says PASS. A unit-level success is not integrated product success.
   Apply Review convergence below before returning repeated piecemeal corrections.
   For graphs you create, review units through the native same-card lane; issue a
   verdict only from the claimed review run. Honor a distinct pre-created review lane
   when the trusted runtime graph explicitly supplies it. The terminal integration
   card consumes reviewed units; it does not replace unit review. Integrate and close
   out under existing procedures, preserving accepted commits and release conclusions.

## Review convergence

Supervisor owns convergence, not only a sequence of individually valid defect reports.
Use the existing review comments, evidence and breakdown; do not add a form, registry,
classifier, judge, automatic approval threshold or new lifecycle.

1. **Tie findings to current obligations.** For each material defect, identify the
   requirement or preservation boundary, its reproduction and the affected mechanism.
   Separate required corrections from optional improvements. Optional work does not
   block acceptance; record it without adding it to the unit's scope.
2. **Review the mechanism together.** Cover its relevant normal path, failures,
   preservation and recovery as one bounded review, not one predictable operation per
   return. For a receipt writer, for example, consider creation, write, refusal and
   cleanup together. This does not require reviewing the entire repository each time.
3. **Recognize non-convergence.** Before another piecemeal return, assess the common
   cause when the same failure class recurs, one fix exposes an equivalent case, or
   repair machinery grows without closing the obligation. Compare the exact candidates
   and evidence; a round count or long runtime alone is not the diagnosis.
4. **Return one coherent correction or a material design question.** An isolated bug,
   or a common-cause repair that stays within the agreed design and unit boundary,
   remains Implementer rework. If the evidence challenges an existing material design,
   shared interface, scope, guarantee or authority decision, return it to Morfeo even
   when the contract is complete. State the failing premise, evidence, preserved
   requirements and the decision needed; do not silently redesign it or weaken it.
   Suspend the failing patch-by-patch strategy, not healthy independent work. Preserve
   the candidate and unfinished work through the native lifecycle.
5. **Consolidate the handoff.** Give the known findings together, the common mechanism
   when supported, and observable verification. Avoid both an open-ended instruction
   to keep hardening and a second oversized specification inside the card.
6. **Re-review proportionately.** Check the changed risk surface, prior mandatory
   controls and affected regressions. Do not reopen settled unrelated areas without
   evidence or invent universal guarantees outside the agreed boundary. A genuinely
   new defect or introduced regression still requires its own reproduction and may
   prevent acceptance. Never approve merely because a round budget was reached, hide
   a failure, or remove a preservation obligation to finish sooner.

### Review contrasts (illustrative, not behavioral evidence)

| Case | Appropriate response |
| --- | --- |
| Isolated implementation defect within a settled interface | Return the bounded correction and its verification to Implementer. |
| Repeated failures expose an unsuitable shared-state isolation design | Consolidate the common cause and return the material design question to Morfeo. |
| Unrelated optional refactor suggested during review | Record it separately; do not block the existing acceptance. |
| A later patch introduces a new real preservation regression | Reproduce and return it; consolidation is not immunity from further review. |

Document/loading tests can check that this procedure exists and remains consistent.
They cannot prove that a model follows it. Observe actual authorized work through the
existing adoption tracker; do not restart a retired synthetic campaign or fabricate a
speedup or behavioral qualification result.

## Compact unit delivery (template, not another schema)

- Source: contract reference, owning `tasks.md` unit and assigned requirement IDs.
- Outcome: independently testable result and explicit exclusions.
- Inputs: inspected base, exact prerequisite deliverables and their acceptance state.
- Boundaries: writable surface, preserved areas and shared interface decisions.
- Judgement: local choices left to Implementer and material questions to return.
- Verification: agreed commands/actions, acceptance oracles and required evidence.
- Dependencies: actual parent edges and reason; declared independence or collision.
- Completion: expected commit/artifact handoff, remaining-risk reporting and explicit
  unit review lane, distinct from terminal integration. Runtime/session/board binding
  remains native side data, not prose identity.

Use an existing plan reference for long stable context. Do not make a unit consume
stale parent prose as proof of the current repository. Supervisor retains ownership
of this template and of the breakdown; Implementer consumes it without duplicating
contract authority.

## Concrete split example (illustrative, not an execution report)

Assume an approved fixture objective already defines two results: a formatter changes
`formatter.py` and has verifier `verify_formatter.py`; a read-only exporter changes
`exporter.py` and has verifier `verify_exporter.py`. The response shapes and input
preservation requirement are already decided; neither unit changes shared files.

| Unit | Assigned outcome | Writable surface | Verification | Actual dependency |
|---|---|---|---|---|
| Formatter | Exact approved formatting behavior | `formatter.py`, its unit tests | Formatting examples and boundary cases | Verified decomposition root |
| Exporter | Exact approved read-only export | `exporter.py`, its unit tests | Export shape and unchanged inputs | Verified decomposition root |
| Terminal integration | Combined result and closeout | Integration-owned artifacts only | Both accepted outputs plus integrated acceptance | Root and both independently reviewed units |

The two implementation units can be dispatched together. Same-card unit review remains
separate from terminal integration. Do not create a Formatter-to-Exporter edge just
because Formatter is listed first. If inspection instead proves both must edit
`adapter.py`, record that concrete collision and serialize them; this example does not
authorize an architectural refactor or waive a contract gate to recover parallelism.
Actual overlap still needs run evidence; this table demonstrates only graph reasoning.

## Worked contrasts (illustrative)

- Independent report formatting and an unrelated read-only export can run together
  only if their stories, agreed interfaces, writable files and tests are independent.
- Two operations editing the same dispatcher file are not parallel units under current
  policy even if they implement different logical branches. Record that collision.
- A shared interface must exist before consumers implement against it. An unrelated
  documentation unit is not a prerequisite for those consumers merely because it was
  listed earlier. Never waive an actual contract-required gate to manufacture overlap.

## Pitfalls

- Creating cards without a canonical breakdown or replacing design with long card prose.
- Delaying all fan-out while personally implementing or overplanning unrelated details.
- Equating one large unit with a defect without inspecting its true coupling.
- Adding workers, tools, profiles or limits instead of fixing a faulty dependency graph.
- Treating every new instance of the same failure class as an unrelated review finding,
  or using a fixed round count to approve unresolved defects.
- Counting currently Supervisor-assigned reviewed cards as Supervisor implementation.
- Closing a root before its decomposition exists, or leaving it running until its own
  parent-gated implementation finishes. Follow the native lifecycle, not a new one.

## Verification

Trace requirement to unit to actual evidence. Inspect a graph with real independence
and one with a necessary interface/shared-file dependency: the first must permit
concurrent execution; the second must preserve its valid ordering. When live execution
is authorized, prove overlap from claimed/spawned/completed run intervals on an isolated
board, not dependency diagrams alone. Record unavailable capacity and external latency
separately. Check an incomplete worker delivery is returned for rework and that ordinary
local choices stay local. Do not infer a speedup percentage from these controls.
