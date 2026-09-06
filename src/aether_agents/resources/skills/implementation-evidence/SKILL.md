---
name: implementation-evidence
description: Use when Implementer executes a contract-derived unit.
version: 0.1.0
author: Morfeo (Aether role), Hermes Agent
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [implementation, testing, evidence, handoff]
    related_skills: []
---

# Implementation and Unit Evidence

Turn one Supervisor-derived unit into verified behavior and a truthful handoff.
This procedure cannot grant authority, redefine acceptance, create a second task tree
or replace the native review lifecycle. Material design belongs to Morfeo; decomposition,
shared contract-supported execution decisions and independent review belong to Supervisor.

## When to Use

- Use when Implementer starts, resumes, self-checks or hands off a scoped unit.
- Use for correcting implementation failures returned through the native review path.
- Do not use to author an Objective Contract, split the wider product, publish or integrate.
- Other roles may inspect this evidence procedure without assuming Implementer's
  execution phase or treating its self-review as independent approval.

## Prerequisites

Read the assigned card with `kanban_show`, applicable parent handoffs and actual source
in the assigned workspace. Follow root `AGENTS.md`; discover relevant Project Canonical
Skills through project-relative reads and Aether Canonical Skills through native discovery.
Use the testing standard and authority already resolved for this project/unit. The
Supervisor-owned delivery defines scope; reading more context does not enlarge it.

## Procedure

1. **Establish the actual starting point.** Verify workspace, branch/base, repository
   state and prerequisites through `terminal`, `read_file` and `search_files`. Compare
   parent handoff references with real artifacts rather than trusting a stale summary.
   Preserve unrelated dirty work. Identify assigned requirements, accepted interfaces,
   modifiable surface, test oracles and expected delivery. Do not spend a full product
   investigation rediscovering decisions already supplied by the canonical design.
   Once scope, inputs, interfaces and oracles are verified, begin the bounded change.
   Reopen investigation only for a concrete inconsistency, failure or unknown affecting
   the unit; do not wait for a second permission to exercise delegated local judgement.
2. **Classify uncertainty at the right owner.** Decide reversible local implementation
   choices that preserve acceptance, shared interfaces, other units and authority.
   Bring a material shared question, candidate answers and consequences to Supervisor
   through the existing durable path. A genuinely absent product/design decision goes
   back through Supervisor to Morfeo. A missing prerequisite is a dependency, not a
   request for owner permission. An oversized or colliding unit needs Supervisor's
   re-decomposition, not hidden sibling agents or a new Objective Contract.
3. **Make a short local execution approach.** Identify the smallest behavior changes
   and tests needed for this unit, using the existing code and conventions. This is
   working reasoning, not another authoritative `plan.md` or `tasks.md`. Do not require
   approval for equivalent local algorithms, private names, or test organization.
   Investigate the smallest unknown that blocks the unit; do not design an unrelated
   framework or absorb incidental defects that do not block acceptance.
4. **Implement with the resolved test discipline.** Follow test-first only when the
   project's standard requires it. Reproduce a defect when that is the acceptance
   basis. Exercise normal and required negative/boundary cases. Keep changes within
   the unit, preserve shared interfaces, and avoid mass staging or unrelated cleanup.
   A mock is useful for its stated boundary; it does not prove a required real integration.
5. **Verify behavior, not just buildability.** Run the assigned checks using the actual
   project environment. Record command/action, candidate revision, exit/result and
   evidence location. Distinguish compile/lint, unit checks, integrated behavior and
   live qualification. A test not run is not PASS; a plausible sample is not a real
   result. If a command cannot run, report the actual failure and a valid in-scope
   alternative when available, never fabricated output or a weakened oracle.
6. **Self-review against the delivery.** Inspect `git diff`, required preservation and
   requirement-to-evidence coverage. Account for every assigned acceptance item,
   including errors and absence of forbidden effects. State material local choices
   and why they preserve the contract. Flag missing, partial, contradictory or
   unrequested behavior rather than announcing completion from confidence.
7. **Prepare a bounded evidence handoff.** Commit only intended paths when authorized.
   Report changed files, commit/artifact references, exact verification results,
   assigned requirement coverage, environment limits and remaining risks. Use stable
   project-relative evidence references in portable artifacts; never include secrets,
   raw private state or provider credentials. Report unit-level compatibility evidence
   only; Supervisor owns aggregate release conclusions and pipeline publication.
8. **Use the existing terminal/review lane.** Re-read the actual graph and native task
   protocol. Normal Aether unit review is same-card: request it instead of self-approving;
   only the claimed Supervisor review run issues its verdict. A terminal integration
   child alone does not replace unit review. If the trusted runtime graph explicitly
   pre-creates a distinct review lane, complete the finished phase to release it as
   that protocol requires; do not strand it or duplicate it with same-card review.
   Never block merely for review or call a finished unit a fully closed product. Use
   native lifecycle tools, not shell board edits or another queue. Preserve real blockers.

## Evidence shape (illustrative, not a tool-schema change)

For each assigned acceptance obligation, report its source reference, the check you
actually ran, observed result and durable evidence location. A compact table is enough.

Example distinction:
- "Tests passed" is insufficient when acceptance also requires preserving input data.
- "AC-2: corrupt input returns the specified error; AC-3: before/after input comparison
  is unchanged" would be useful only when those checks actually ran and their evidence
  is attached. Writing this example into a report does not satisfy either obligation.
- A passing unit test of an adapter does not establish a live external service result.

The Supervisor owns the unit-delivery template. Consume it; do not redefine its shared
interfaces or create a competing acceptance schema to make implementation easier.

## Pitfalls

- Treating the card as a vague suggestion or treating inspected files as new scope.
- Escalating every local choice, or silently deciding a material shared API change.
- Fanning out product work to subagents or sibling cards instead of returning a bad split.
- Modifying a canonical Objective Contract to make the implemented result acceptable.
- Reporting test counts or success prose without mapping the actual required behavior.
- Using heartbeats as proof of progress, or discarding useful work because a run is long.
- Publishing, integrating, or claiming an aggregate release decision from a unit role.

## Verification

Use a unit whose acceptance contains a normal outcome, a negative case and a preservation
obligation. Verify that incomplete evidence cannot be reported as complete, that a
reversible local choice proceeds without a decision-card ceremony, and that a material
interface question reaches Supervisor. Inspect actual changed state and test results.
A later independent reviewer must be able to reproduce or inspect the claim without
recovering the Implementer's conversation. Static wording checks alone do not prove
this behavior, and self-review must never be labelled independent review.
