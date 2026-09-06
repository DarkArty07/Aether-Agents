---
name: objective-contract-design
description: Use when Morfeo designs a pipeline contract.
version: 0.1.0
author: Morfeo (Aether role), Hermes Agent
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [contracts, design, requirements, verification]
    related_skills: []
---

# Objective Contract Design

Turn approved intent into discoverable requirements, material technical design and
observable acceptance before a pipeline handoff. This is Morfeo's procedure, not a
new source of requirements or a competing artifact format. It cannot grant authority.
The owner and canonical artifacts govern; Supervisor owns independent receipt review
and decomposition, and Implementer retains reversible unit-local judgement.

## When to Use

- Use when Morfeo designs, checks or supersedes a pipeline Objective Contract.
- Use for resolving a contract defect returned by Supervisor at its owning artifact.
- Do not require a contract or this full procedure for bounded direct work.
- Do not use to decompose tasks, implement a product, or certify your own independent review.
- Other roles may inspect these criteria as evidence; this procedure does not assign
  Morfeo's design or contract-authoring phase to them.

## Prerequisites

Read the owner instruction, constitution, relevant design/specifications and root
`AGENTS.md`. Discover relevant Project Canonical Skills through their named
project-relative `.aether/skills/<name>/SKILL.md` paths and Aether Canonical Skills
through native discovery. Preserve brownfield guidance and confirm the actual Project.
Resolve testing standard, authority and convergence bounds explicitly from the owner
or their delegated project policy; a skill does not supply universal defaults.

## Procedure

1. **Inspect before prescribing.** With `read_file`, `search_files` and `terminal`,
   locate the actual implementation, public interfaces, tests, dependencies and
   repository state. Record stable project-relative paths/symbols and the inspected
   revision. Separate observed behavior, intended behavior and unqualified assumptions.
   Finish when the proposed change can be located in the real project.
   Keep each further inspection tied to an unanswered material question and the
   decision it can change. Reuse already verified references at the same revision;
   do not repeatedly rediscover them or investigate every future unit's local details.
2. **Extract intent.** Write the problem, user-visible outcome, representative user
   stories, exclusions and preservation boundary in their existing canonical homes.
   Identify each material question; resolve it with the owner when no delegated answer
   exists. Persist each accepted clarification immediately, not only in conversation.
   Finish when the next role need not reconstruct intent from a chat.
3. **Make requirements observable.** Give obligations stable references and describe
   relevant normal, error and boundary scenarios. Distinguish product acceptance from
   method, authority and operational closeout. Replace vague adjectives with the
   project's agreed observable criterion, not an invented numeric target.
4. **Resolve material feasibility.** Inspect or perform an authorized bounded probe
   for a central uncertainty such as whether a required framework interface exists.
   Record what the probe proves and what it does not. If feasibility remains unknown,
   do not label the build ready: resolve an explicitly bounded research objective with
   its own acceptance or return the missing decision. Never disguise research as a
   trivial Implementer detail or acquire access to make a design appear feasible.
5. **Design only the applicable material boundaries.** Use the technical `plan.md`
   and existing canonical owners to specify component responsibilities and data/control
   flow. Specify shared input/output/error interfaces, data lifecycle, states,
   invariants, concurrency and recovery where the objective needs them. Name selected
   decisions, evidence-backed assumptions, rejected alternatives and change impact.
   Use diagrams, schema fragments, examples or pseudocode when they remove ambiguity;
   omit empty templates. Finish when workers cannot invent incompatible shared answers.
6. **Preserve local judgement.** Explicitly distinguish owner-reserved decisions,
   Morfeo's material design, Supervisor's contract-supported shared execution decisions
   and Implementer's equivalent reversible local choices. An internal function name
   need not be prescribed; a shared response shape may need to be. References to code
   lines are inspection evidence, not a permanently fixed patch instruction.
7. **Design verification.** Map each acceptance obligation to a scenario, expected
   observable result and intended evidence in the owning artifacts. Provide the
   canonical runnable end-to-end validation, including prerequisites, commands or
   tool actions, and expected pass/fail observations. Mark unavailable capabilities honestly.
   Distinguish proposed checks from executed results and unit checks from integrated
   acceptance; do not impose test-first or live calls unless the resolved standard does.
8. **Check contradictions before finalizing.** Compare scope, deliverables, acceptance,
   authority, dependencies, preservation and expected test effects. A real-flow test
   cannot also require its own board/session records never to change. Preservation
   normally names unrelated state and declared product invariants, not all bytes on
   the machine. Verify every referenced owning artifact exists at the intended base.
   Record the reason for genuinely non-applicable design dimensions without filler.
   Perform a cold-read self-check: given only the referenced artifacts, list the
   decisions the receiver would still have to invent and remove each material gap.
   This is an author self-check, not an independent reviewer verdict.
9. **Materialize one handoff.** Use the authorized `objective_contract` capability with
   explicitly verified portable Project identity and incremental sections. Reference
   owning artifacts rather than copying a competing spec/plan. Validate, finalize and
   checkpoint exact bytes through the normal Git workflow. Carry only the prescribed
   short envelope to Supervisor; keep returned opaque routing values in root-card
   side data exactly as the capability requires. Never invent or repair routing identity.
10. **State what is and is not complete.** Report design self-check evidence and any
    remaining material risk. Structural validation/finalization is not semantic
    approval. Supervisor independently checks receipt quality and derives `tasks.md`;
    do not claim cross-artifact task coverage before that breakdown exists. If review
    returns a contract defect, repair the owning artifact and supersede final bytes
    when required; never patch an immutable contract in place.

## Writing rules and compact evidence

Separate four kinds of statement in the owning artifact: **decided** (authority and
rationale), **assumed** (evidence and what would invalidate it), **locally delegated**
(choice and boundaries), and **illustrative** (example, not a new obligation). A
material unverified assumption cannot become a build-ready decision by changing its
label. Use MUST only for an existing or accepted requirement, not a stylistic preference.
Write an action, its observable output and its completion condition rather than a list
of adjectives. Avoid repeating the same rule in the Objective Contract, plan and skill.

For a material design decision, a compact entry in the existing plan can say:

| Decision | Approved choice and reason | Evidence/assumption | Verification reference | Local freedom |
|---|---|---|---|---|
| Existing decision reference | Chosen behavior and rejected material alternative | Inspected source or authorized probe; validity boundary | Existing acceptance/scenario reference | Equivalent private implementation choices |

This is an optional prose aid, not another registry or schema. Use existing identifiers
and references; do not create a separate file or new identifier system just for this table.
If design is incomplete, return the specific question, why it changes the outcome,
known alternatives and evidence, and which owner can decide. Do not ask the owner to
repeat context that the repository or prior accepted artifact can answer.

## Worked contrast (illustrative, not executed evidence)

Weak: "Add robust cache recovery; test adequately."

Better, only if approved: "The existing cache is optional. On a corrupt cache record,
fall back to the canonical source without altering it; return the same public result
as a cold read. The shared adapter returns the existing result type and records the
existing cache-miss code. Acceptance compares cold and corrupt-cache reads and checks
source preservation. The local eviction data structure remains an Implementer choice."

The improvement is a decided behavior, interface and oracle, not extra prose or a
prescribed implementation. An objective with durable concurrent writers would need
additional applicable state/atomicity decisions; this example does not supply them.

## Pitfalls

- Treating eleven nonempty sections, a digest or `finalize` as proof of good design.
- Saying "Supervisor will design the API" when the API is material missing intent.
- Prescribing every line of code, inventing architecture for a small change, or copying
  the same authority into several competing documents.
- Making downstream workers locate artifacts that exist only in a chat or dirty base.
- Treating an expected objective-owned test mutation as damage to unrelated user state.
- Claiming every revision is a design failure: new owner intent and corrected repository
  baselines are different from an initially contradictory acceptance criterion.

## Verification

Review one sufficient small case, one materially incomplete case, one contradictory
case and one complex interface/state case. Record exact references and what each case
accepts, rejects or leaves locally discretionary. The small case must not acquire
unnecessary architecture. A real receiver must identify absent material decisions
rather than invent them. Evidence of this exercise is separate from document-format
checks and from later product execution; do not self-label it independent review.
