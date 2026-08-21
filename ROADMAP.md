# Aether Agents — Design Roadmap

**Status:** R0–R13, amended PD-44, and PD-45 accepted; proportional Morfeo delivery is mechanically verified and #196 is closed by owner acceptance
**Updated:** 2026-08-20
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
| **R4** | Hermes Framework boundary | Classify Hermes's three coordination primitives and its native capabilities against accepted Aether requirements; record the runtime/method boundary. Does not select a primitive or activate anything. | R0, R1, R2, R3 | **done** | [`spec.md`](specs/r4-hermes-boundary/spec.md) |
| **R5** | Topology, identity, and isolation | The durable board is Aether's coordination primitive; three profiles, one per role; per-card worktrees; blocked cards as the escalation channel. Does not decide A2A's scope. | R1, R2, R4 | **done** | [`spec.md`](specs/r5-topology-and-isolation/spec.md) |
| **R6** | Protocol and communication | The board is the only inter-role transport. A2A is a platform adapter, available and unused, with two stated reopening conditions; MCP is an outward surface only. Owns the owner's notification channel. | R2, R3, R4, R5 | **done** | [`spec.md`](specs/r6-protocol-and-communication/spec.md) |
| **R7** | Supervision, parallelism, and convergence | Decomposition belongs to the supervisor against a competing runtime default; two-tier escalation; convergence configured, not designed; concurrency and budget starting values. | R2, R3, R5, R6 | **done** | [`spec.md`](specs/r7-supervision-and-convergence/spec.md) |
| **R8** | Workspaces, Git, and integration | Worktree per unit, the contract's writer rule, dependency-ordered integration, one commit per unit so every unit is individually revertible, bounded publication authority. | R2, R5, R7 | **done** | [`spec.md`](specs/r8-workspaces-and-integration/spec.md) |
| **R9** | State, artifacts, memory, and recovery | Three stores with one owner each, deliverable declaration, owner-preference memory bounded, the card as the unit of durability, retention that separates record from telemetry. | R2, R5, R6, R7, R8 | **done** | [`spec.md`](specs/r9-state-and-recovery/spec.md) |
| **R10** | Security, trust, and authority enforcement | Single-host trusted-local-user threat model, asymmetric containment, a fail-closed pre-tool-call hook as the enforcement point, and a definitive list of protected effects. | R1, R5, R6, R7, R8, R9 | **done** | [`spec.md`](specs/r10-security-and-authority/spec.md) |
| **R11** | Evidence, observability, and evaluation | The running product as deliverable, per-unit evidence answering four questions, ranked finding classes, and the verified-or-assumed discipline for claims about the runtime. | R2, R3, R7, R8, R9, R10 | **done** | [`spec.md`](specs/r11-evidence-and-observability/spec.md) |
| **R12** | Models, routing, and economics | Capability allocated per profile with a per-unit override, auxiliary slots dispositioned, provider-agnostic. Model names are bound at build time, not here. | R1, R7, R10, R11 | **done** | [`spec.md`](specs/r12-models-and-economics/spec.md) |
| **R13** | Design synthesis and release | Reconciles R0–R12, specifies what each prompt must guarantee, lists the complete configuration inventory and the ten unobserved claims. Authorizes no build and no run. | R0–R12 | **done** | [`spec.md`](specs/r13-synthesis-and-release/spec.md) |

## 6. EC1 — Walking-skeleton evidence checkpoint

After R2 and R5 are accepted—and before R6, R7, or R9 closes empirical claims—Aether should seek a **separate explicit build authorization** for one minimal evidence run:

```text
Morfeo → supervision → one implementer → evidence → independent review
```

The task must be trivial, bounded, reversible, and unrelated to product delivery. Its purpose is to measure contract handoff, cancellation, evidence quality, authority preservation, and recovery assumptions before later stages rely on them.

Since R5 selected the durable board, EC1 is a board run across three profiles rather than an in-process delegation.

Two verification passes on 2026-08-17 settled every mechanically testable board/runtime claim without a
profile, agent, or model. Christopher then explicitly authorized Phase 5 on 2026-08-18. The live EC1 run
completed one sacrificial Morfeo → Supervisor → Implementer → review → integration path and one impossible
goal-mode negative control. It observed both convergence outcomes, real TUI wake delivery to Morfeo, and
acceptance-quality worker evidence. It also exposed lifecycle contradictions around initial blocking,
triage redispatch, worker-created limits, and same-card goal predicates. The complete trace is
[`R13 research §14`](specs/r13-synthesis-and-release/research.md).

After EC1, [`R13 Phase 6`](specs/r13-synthesis-and-release/plan.md) qualifies that evidence, revisits
provisional decisions, correlates cost, records debt, and returns `READY` or `HOLD`. Phase 6 is an
evidence-closure phase inside R13, not a new roadmap design area and not cutover authority.

EC1 was not automatically authorized by this roadmap; it ran only after Christopher's separate explicit
authorization. It remained a sacrificial evidence checkpoint, not product implementation or a
code-enforced stage transition.

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

**The design phase is complete and accepted.** R0 through R13 are accepted, all on 2026-08-17 — R0–R3 at the R0 review, R4 through R13 at the R4–R13 Decision Review. R4 and R5 additionally carry corrections made after their first drafts were contradicted by direct execution of the runtime. R13 was amended on 2026-08-18 by explicit owner instruction to formalize Phase 6.

Build Phases 0–4 and the separately authorized EC1 Phase 5 run are complete. Morfeo, Supervisor, and
Implementer returned to a stopped-profile state after producing permanent board evidence: two `done`
cards and one deliberately `blocked` negative control. The canonical sacrificial fixture passes
`python3 verify.py`. No product code, publication, deployment, credential change, or Hermes-to-Morfeo
cutover occurred.

This repository's own governance is materialized at `.specify/memory/constitution.md`, copying the accepted R0 §4 principles as `specs/r0-design-governance/spec.md` directs. It is untracked and R0 remains its canonical source. The constitution of a project Aether *builds* is a different artifact that lives inside that project, and is written when work on it starts (R3-D04).

**The next protected gate is Phase 6 evidence re-qualification, not another Phase 5 run or cutover.**
The earlier Phase 6 `HOLD` packet was truthful before EC1 and remains historical; it has not yet consumed
the new evidence or classified the runtime findings. Until that analytical phase is re-executed, no claim
is formally promoted and no `READY` recommendation is current.

PD-44's proportional-Morfeo contract and its 2026-08-20 capability amendment are accepted and canonical;
PD-45 adds `skills` and `vision` to all three roles without widening authority. The stopped live profiles now
contain the mechanically verified delivery: Morfeo has CLI/Telegram parity with `code_execution`, `cronjob`,
and `delegation`, while Supervisor and Implementer retain `code_execution` and gain `skills`/`vision` but not
cron or delegation. Browser execution and computer use remain excluded from Morfeo. #196 is closed by
explicit owner acceptance of the active direct-execution experience as sufficient functional validation.

The separately authorized #198 runtime repair remains local and mechanically verified; its upstream defect is
recorded at `NousResearch/hermes-agent#89677`. The gateway reload completed, but first-spawn branch propagation
still requires its own live acceptance before #198 closes. #199 is closed after 27/27 focused regressions and
a live read-only branch-inspection proof. #200 is closed by merged PR #201: `policy/hooks/` is the sanitized
canonical source and `scripts/sync_policy_hooks.py` provides atomic install, parity check, and drift-safe
restore. Phase 6 evidence re-qualification, the other open issues, release, deployment, and product cutover
remain separate work.

A deliverable previously scheduled into R3 no longer exists there. R3 was to extract Christopher's standing code-quality standards into constitution principles, on the assumption that a single constitution governed all Aether work. R3-D04 corrected that: Spec Kit's constitution lives **inside the project being built**, so there is no Aether-wide constitution to author. Per-project standards are established when work on a project starts, and the owner's cross-project preferences belong to Morfeo's learned memory, whose realization is R4 and whose storage is R9.

The extraction itself remains worthwhile. It is now an input to Morfeo's memory rather than a design artifact, and is not a gate on any design stage.
