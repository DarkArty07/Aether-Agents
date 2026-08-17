# Aether Agents — Design Roadmap

**Status:** R0 accepted; R1–R13 planned
**Updated:** 2026-08-17
**Product authority:** Christopher

## 1. Purpose

This file is Aether's shallow **spec of specs**. It owns only stable design-area identifiers, intent, scope boundaries, dependencies, documentary status, and links to active specifications.

Detailed requirements, research, decisions, and acceptance criteria belong in the specification directory of the stage that owns them. This roadmap must not duplicate the accepted and open product decisions in `DESIGN.md`.

## 2. Agentic interpretation

This roadmap guides agent reasoning; it is not an executable workflow definition. R0–R13 name durable design areas and useful dependencies. The active agent may infer, define, split, combine, or revisit the practical cognitive frame needed for current intent without code instantiating a stage.

`Stage`, `status`, `gate`, `close`, `reopen`, and `return` are semantic signals interpreted by agents and Christopher. They do not require a workflow engine, parser, scheduler, database, or executable transition validator. Tests and scripts may validate artifacts or effects but never control the existence or intellectual progression of a design stage.

## 3. Sources of truth

- `DESIGN.md` owns the current conceptual product design, accepted foundations, open decisions, and review triggers.
- `specs/r0-design-governance/spec.md` owns the accepted R0 governance model.
- Each later `specs/<stage>/spec.md` will own its stage when that design area becomes active.
- This roadmap owns only decomposition, dependency guidance, documentary progress, and links.

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
| **R1** | Product authority and operating experience | Define Christopher–Morfeo interaction, decision materiality, escalation, and authority matrix. Does not define contract technology. | R0 | **planned** | Created when active |
| **R2** | Multi-agent contract and handoff | Define contract obligations, authority, acceptance, defect return, and lifecycle semantics. Does not select transport or runtime topology. | R0, R1 | **planned** | Created when active |
| **R3** | Spec Kit as a multi-agent method | Map accepted Spec Kit intellectual contracts across roles and artifacts. Does not install or fork Spec Kit. | R1, R2 | **planned** | Created when active |
| **R4** | Hermes Framework boundary | Classify native capabilities, bounded adaptations, missing capabilities, and incompatibilities. Does not activate extensions. | R0, R1, R2, R3 | **planned** | Created when active |
| **R5** | Topology, identity, and isolation | Define agents, instances, sessions, process/profile boundaries, isolation, and discovery requirements. Does not choose communication protocol. | R1, R2, R4 | **planned** | Created when active |
| **R6** | Protocol and communication | Decide A2A fit and scope plus Aether's communication envelope. Live-behavior claims require measured evidence, not documentation alone. | R2, R3, R4, R5; EC1 for empirical claims | **planned** | Created when active |
| **R7** | Supervision, parallelism, and convergence | Define decomposition, assignment, retries, independent verification, integration feedback, and convergence. Live-behavior claims require EC1 evidence. | R2, R3, R5, R6; EC1 | **planned** | Created when active |
| **R8** | Workspaces, Git, and integration | Define ownership, worktrees or alternatives, branch/commit boundaries, integration, publication authority, and rollback. | R2, R7 | **planned** | Created when active |
| **R9** | State, artifacts, memory, and recovery | Define persistence, resumability, provenance, retention, recovery, and source-of-truth boundaries. Runtime recovery claims require EC1 evidence. | R2, R5, R6, R7, R8; EC1 | **planned** | Created when active |
| **R10** | Security, trust, and authority enforcement | Build the threat model and distinguish prompt authority from executable safeguards and protected effects. | R1, R5, R6, R7, R9 | **planned** | Created when active |
| **R11** | Evidence, observability, and evaluation | Define trace evidence, independent verification, controlled EVAL, and acceptance reporting. | R2, R3, R7, R8, R9, R10 | **planned** | Created when active |
| **R12** | Models, routing, and economics | Select role- and gate-specific models through controlled evaluation; cost cannot substitute for demonstrated quality. | R1, R7, R10, R11 | **planned** | Created when active |
| **R13** | Design synthesis and release | Reconcile R0–R12 into a coherent architecture and explicit contract for entering implementation. Does not itself authorize build or activation. | R0–R12 | **planned** | Created when active |

## 6. EC1 — Walking-skeleton evidence checkpoint

After R2 and R5 are accepted—and before R6, R7, or R9 closes empirical claims—Aether should seek a **separate explicit build authorization** for one minimal evidence run:

```text
Morfeo → supervision → one implementer → evidence → independent review
```

The task must be trivial, bounded, reversible, and unrelated to product delivery. Its purpose is to measure contract handoff, cancellation, evidence quality, authority preservation, and recovery assumptions before later stages rely on them.

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

R0 is accepted and closed as a design stage. No profile, worker, scheduler, protocol, persistence service, model route, product code, or runtime activation is authorized by that acceptance.

The next recommended design area is **R1 — Product authority and operating experience**. It must not start automatically merely because R0 is done.
