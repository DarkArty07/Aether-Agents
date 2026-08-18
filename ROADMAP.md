# Aether Agents — Design Roadmap

**Status:** R0–R3 accepted; R4–R13 written and awaiting review
**Updated:** 2026-08-17
**Product authority:** Christopher

## 1. Purpose

This file is Aether's shallow **spec of specs**. It owns only stable design-area identifiers, intent, scope boundaries, dependencies, documentary status, and links to active specifications.

Detailed requirements, research, decisions, and acceptance criteria belong in the specification directory of the stage that owns them. This roadmap must not duplicate the accepted and open product decisions in `DESIGN.md`.

## 2. Agentic interpretation

This roadmap guides agent reasoning; it is not an executable workflow definition. R0–R13 name durable design areas and useful dependencies. The active agent may infer, define, split, combine, or revisit the practical cognitive frame needed for current intent without code instantiating a stage.

`Stage`, `status`, `gate`, `close`, `reopen`, and `return` are semantic signals interpreted by agents and Christopher. They do not require a workflow engine, parser, scheduler, database, or executable transition validator. Tests and scripts may validate artifacts or effects but never control the existence or intellectual progression of a design stage.

## 3. Sources of truth

- `README.md` is the entry point: what Aether is, how work flows, and what a builder must do.
- `DESIGN.md` owns the current conceptual product design, accepted foundations, open decisions, and review triggers.
- `specs/r0-design-governance/spec.md` owns the accepted R0 governance model.
- Each later `specs/<stage>/spec.md` owns its stage.
- This roadmap owns only decomposition, dependency guidance, documentary progress, and links.

**Recorded deviation.** R0 through R5 separate requirements from evidence into `spec.md` and `research.md`. R6 through R13 were designed in a single verification session whose evidence is shared across all of them, so each carries an `Evidence` section inline stating what was verified, what was assumed, and what was not inspected. The obligation is unchanged — every claim still names its source and its status — and splitting one session's evidence into eight files would have produced ceremony rather than traceability.

If this roadmap conflicts with an owning specification, correct the owning artifact first and then reconcile this index.

## 4. Documentary status model

```text
planned → in-progress → done
              ↑          │
              └──────────┘ materially affected change
```

- **planned:** bounded design area, not currently active.
- **in-progress:** active, under review, blocked, or revising materially affected content.
- **done:** accepted requirements and decisions have passed their quality checks and are part of a durable Git baseline.

These labels are documentation, not runtime states. Decisions do not have a separate status lifecycle.

## 5. Roadmap

| ID | Design area | Intent and scope boundary | Depends on | Status | Owning spec |
| --- | --- | --- | --- | --- | --- |
| **R0** | Design governance and baseline | Define current-truth ownership, agentic stage semantics, autonomous review, change impact, evidence, and authority scopes. Does not implement Spec Kit or runtime mechanisms. | Conceptual design | **done** | [`spec.md`](specs/r0-design-governance/spec.md) |
| **R1** | Product authority and operating experience | Define owner–Morfeo interaction, extraction, interruption, effects, delivery, and review. Does not define contract content or technology. | R0 | **done** | [`spec.md`](specs/r1-authority-and-interaction/spec.md) |
| **R2** | Multi-agent contract and handoff | Identify the contract as the Spec Kit artifact set, add Aether's execution envelope, make completeness measurable, and define defect return. Does not select transport or runtime topology. | R0, R1 | **done** | [`spec.md`](specs/r2-contract-and-handoff/spec.md) |
| **R3** | Spec Kit as a multi-agent method | Assign every Spec Kit phase to exactly one role, locate the handoff boundary, and separate owner preferences from project constitutions. Does not install or fork Spec Kit. | R1, R2 | **done** | [`spec.md`](specs/r3-speckit-multiagent-method/spec.md) |
| **R4** | Hermes Framework boundary | Classify Hermes's three coordination primitives and its native capabilities against accepted Aether requirements; record the runtime/method boundary. Does not select a primitive or activate anything. | R0, R1, R2, R3 | **in-progress** | [`spec.md`](specs/r4-hermes-boundary/spec.md) |
| **R5** | Topology, identity, and isolation | The durable board is Aether's coordination primitive; four profiles, one per role; per-card worktrees; blocked cards as the escalation channel. Does not decide A2A's scope. | R1, R2, R4 | **in-progress** | [`spec.md`](specs/r5-topology-and-isolation/spec.md) |
| **R6** | Protocol and communication | The board is the only inter-role transport. A2A is a platform adapter, available and unused, with two stated reopening conditions; MCP is an outward surface only. Owns the owner's notification channel. | R2, R3, R4, R5 | **in-progress** | [`spec.md`](specs/r6-protocol-and-communication/spec.md) |
| **R7** | Supervision, parallelism, and convergence | Decomposition belongs to the supervisor against a competing runtime default; two-tier escalation; convergence configured, not designed; concurrency and budget starting values. | R2, R3, R5, R6 | **in-progress** | [`spec.md`](specs/r7-supervision-and-convergence/spec.md) |
| **R8** | Workspaces, Git, and integration | Worktree per unit, the contract's writer rule, dependency-ordered integration, one commit per unit so every unit is individually revertible, bounded publication authority. | R2, R5, R7 | **in-progress** | [`spec.md`](specs/r8-workspaces-and-integration/spec.md) |
| **R9** | State, artifacts, memory, and recovery | Three stores with one owner each, deliverable declaration, owner-preference memory bounded, the card as the unit of durability, retention that separates record from telemetry. | R2, R5, R6, R7, R8 | **in-progress** | [`spec.md`](specs/r9-state-and-recovery/spec.md) |
| **R10** | Security, trust, and authority enforcement | Single-host trusted-local-user threat model, asymmetric containment, a fail-closed pre-tool-call hook as the enforcement point, and a definitive list of protected effects. | R1, R5, R6, R7, R8, R9 | **in-progress** | [`spec.md`](specs/r10-security-and-authority/spec.md) |
| **R11** | Evidence, observability, and evaluation | The running product as deliverable, per-unit evidence answering four questions, ranked finding classes, and the verified-or-assumed discipline for claims about the runtime. | R2, R3, R7, R8, R9, R10 | **in-progress** | [`spec.md`](specs/r11-evidence-and-observability/spec.md) |
| **R12** | Models, routing, and economics | Capability allocated per profile with a per-unit override, auxiliary slots dispositioned, provider-agnostic. Model names are bound at build time, not here. | R1, R7, R10, R11 | **in-progress** | [`spec.md`](specs/r12-models-and-economics/spec.md) |
| **R13** | Design synthesis and release | Reconciles R0–R12, specifies what each prompt must guarantee, lists the complete configuration inventory and the ten unobserved claims. Authorizes no build and no run. | R0–R12 | **in-progress** | [`spec.md`](specs/r13-synthesis-and-release/spec.md) |

## 6. EC1 — Walking-skeleton evidence checkpoint

After R2 and R5 are accepted—and before R6, R7, or R9 closes empirical claims—Aether should seek a **separate explicit build authorization** for one minimal evidence run:

```text
Morfeo → supervision → one implementer → evidence → independent review
```

The task must be trivial, bounded, reversible, and unrelated to product delivery. Its purpose is to measure contract handoff, cancellation, evidence quality, authority preservation, and recovery assumptions before later stages rely on them.

Since R5 selected the durable board, EC1 is a board run across three profiles rather than an in-process delegation.

**EC1 has shrunk to three items.** Two verification passes on 2026-08-17 exercised the runtime directly on an isolated database, using its injectable spawn seam and its directly callable board kernel — no profile, no agent, no model. Between them they settled dependency gating, parallel release, verbatim handoff, durable blocking, two-tier escalation, attempt history, the unblock-loop limit, worker dispatch, per-card worktrees, live concurrency capping, crash reclaim, the review lane, enforcement blocking, and the decomposition disable.

Three claims still require a paid run: convergence judging, wake delivery, and whether a real worker's evidence supports acceptance. [`R13 §5`](specs/r13-synthesis-and-release/spec.md) is the authoritative checklist and [`R13 research`](specs/r13-synthesis-and-release/research.md) holds the findings, including four corrections that changed accepted requirements.

EC1 is not automatically authorized by this roadmap, is not a product implementation, and is not a code-enforced stage transition. If Christopher does not authorize it, affected later stages must label runtime behavior as an assumption rather than measured fact.

## 7. Change and regression

When current intent or evidence changes:

1. Update the artifact that owns the affected decision.
2. Record the reason, evidence, alternatives, and change impact in that stage's research artifact.
3. Inspect direct and transitive roadmap dependencies.
4. Return only materially affected `done` stages to `in-progress` with a short reason.
5. Reconcile derived plans, contracts, prompts, tasks, code, or runtime evidence.
6. Present Christopher only the changed material decisions and consequences.

Git preserves superseded text. No B0/B1 registry or per-decision state machine is required.

## 8. Current boundary

**The design phase is written through R13.** R0 through R3 are accepted. R4 through R13 are written and await Christopher's review; R4 and R5 additionally carry corrections made after their first drafts were contradicted by direct execution of the runtime.

No profile, worker, scheduler, protocol, persistence service, model route, product code, or runtime activation is authorized. The system prompts and any project constitution are build artifacts and are deliberately not written; [`R13 §3`](specs/r13-synthesis-and-release/spec.md) specifies what each prompt must guarantee without writing one.

The next action is **review, not design**. After review, the sequence is the build order in [`README.md`](README.md), and then the evidence checkpoint of §6 — which is the only thing that can promote this repository's ten remaining assumptions to measured fact.

A deliverable previously scheduled into R3 no longer exists there. R3 was to extract Christopher's standing code-quality standards into constitution principles, on the assumption that a single constitution governed all Aether work. R3-D04 corrected that: Spec Kit's constitution lives **inside the project being built**, so there is no Aether-wide constitution to author. Per-project standards are established when work on a project starts, and the owner's cross-project preferences belong to Morfeo's learned memory, whose realization is R4 and whose storage is R9.

The extraction itself remains worthwhile. It is now an input to Morfeo's memory rather than a design artifact, and is not a gate on any design stage.
