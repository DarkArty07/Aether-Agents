# Multi-Agent Operating Model

> **Status:** APPROVED TARGET — current runtime parity not yet verified
> **Owner:** Christopher (DarkArty07)
> **Governing decisions:** `../decisions/PDR-0005-multi-agent-participation-and-coordination.md`, `../decisions/PDR-0008-canonical-definition-and-project-completion.md`
> **Implementation authorization:** None

## Purpose

This document defines the approved conceptual model for specialist participation, lateral coordination, disagreement resolution, and the relationship between the product doctrine and the v0.19.x kernel migration.

It describes the target operating model. It must not be read as proof that the current live runtime already behaves this way.

## Core doctrine

> Centralize product vision; decentralize routine coordination.

The user remains product owner. Hermes preserves intent and synthesizes consequential decisions. Harmonia and the kernel coordinate bounded execution. Daimons provide specialist judgment. Olympus owns ACP lifecycle.

The multi-agent system is successful only when specialist value exceeds coordination cost and the final software project is better than a strong general-agent baseline.

## Specialist participation policy

Every Daimon has one effective participation state in the applicable scope:

| State | Meaning | Selection behavior |
|---|---|---|
| `required` | The approved contract requires the role for a named task or gate. | Aether must involve it or escalate inability to satisfy the contract. |
| `allowed` | Aether may select the role when expected value exceeds coordination cost. | Selection remains discretionary and evidence-based. |
| `disabled` | The user does not want the role used unless explicitly re-enabled. | Automatic routing and fallback must skip it. |
| `forbidden` | The role must not participate in the applicable scope. | No direct, indirect, fallback, renamed, or peer-proposed invocation is valid. |

### Policy precedence

1. Current explicit user instruction.
2. Project-specific user policy.
3. Run or contract participant policy.
4. Durable approved preferences.
5. Product defaults.
6. Agent recommendation.

A lower layer cannot re-enable a Daimon disabled by a higher layer.

### Athena precedent

Athena is currently suspended until explicit user reactivation. This is not merely a one-off operational exception; it demonstrates the product requirement that user/project policy must be able to disable any specialist.

Skipping a Daimon does not automatically waive its quality concern. Aether must choose an honest alternative or escalate the residual consequence.

## Participation decision

Before involving a Daimon, Aether should answer:

1. What distinct specialist contribution is needed?
2. Which known general-agent weakness or project risk does it address?
3. What artifact, decision, review, or evidence will it produce?
4. Is its scope and authority bounded?
5. Is it allowed by user/project policy?
6. Is the expected quality gain greater than model, latency, context, and coordination cost?
7. Can the task be handled as well by the current owner, a smaller model, deterministic tooling, or no additional agent?

If the last answer is yes and specialist independence is not required, the Daimon should not be activated.

## Target coordination topology

```text
User / Product Owner
        |
        v
Hermes — intent, contract, product synthesis, material escalation
        |
        v
Coordination contract + durable semantic ledger
        |
        +-----------------------------+
        |                             |
        v                             v
Harmonia / kernel                Olympus / ACPManager
workflow state, admission,       processes, sessions,
dependencies, budgets,           heartbeat, cancellation,
evidence, recovery               technical closure
        |
        v
Authorized Daimons collaborate laterally
under role, task, evidence and participant boundaries
```

Hermes receives meaningful milestones, risks, escalations, and final projections. It does not need every peer message in its context.

Harmonia observes and coordinates but is not required to relay every message. The kernel validates and commits authoritative workflow transitions. Olympus executes and owns technical ACP lifecycle.

## Lateral collaboration contract

An authorized Daimon may directly:

- request information from another allowed role;
- transfer a bounded dependency result;
- share an artifact or evidence reference;
- request a specific review;
- report a blocker or finding;
- propose a derived subtask;
- continue a pre-approved task chain.

Every lateral action must preserve:

- contract and generation identity;
- sender and recipient role identity;
- project and task scope;
- user participation policy;
- authority class and prohibited actions;
- provenance and taint boundaries;
- evidence references;
- budget and attempt limits;
- durable traceability.

Free text may inform reasoning but cannot grant authority, expand scope, re-enable a Daimon, approve risk, or amend the contract.

## Accountable owner

Each deliverable or task chain has one accountable owner responsible for integrating the result and proposing completion.

The accountable owner is not necessarily Hermes and is not the only participant allowed to coordinate. Ownership provides accountability, not unlimited authority.

Owners cannot self-approve an independent gate.

## Technical closure versus product completion

A Daimon, task owner, Harmonia, the kernel, or Olympus may establish technical terminality, evidence completion, or semantic workflow closure inside the active contract.

None of those states independently establish that the user obtained the intended product.

Hermes compares the integrated result and evidence against the preserved requirements and may propose product completion. The user remains final acceptance authority, except where the approved contract defines objective acceptance that does not require another confirmation.

A workflow must not rewrite its requirements or acceptance criteria to justify what it happened to produce.

## Harmonia boundary

Harmonia may:

- reconstruct current workflow state;
- admit contract-derived subtasks deterministically;
- select eligible roles from an approved candidate set;
- track dependencies, attempts, budgets, stalls, and gates;
- request evidence or clarification;
- coordinate bounded retries and recovery;
- publish high-value escalation and completion projections.

Harmonia may not:

- change product vision or scope;
- amend the contract;
- override user participation policy;
- invoke forbidden or disabled Daimons;
- become a domain implementer or reviewer;
- own ACP processes or sessions;
- call ACP directly when Olympus owns that operation;
- approve her own coordination result;
- resolve domain disputes through preference or majority vote.

## Disagreement resolution

### Resolution hierarchy

1. Current explicit user instruction.
2. Approved product vision and decisions.
3. Active contract, scope, exclusions, and acceptance criteria.
4. Actual artifacts and reproducible evidence.
5. Approved quality hierarchy and proportionality.
6. Specialist authority in the relevant domain.
7. Hermes cross-domain synthesis.
8. Product-owner decision for material product changes, risk acceptance, or irresolvable ambiguity.

### Rules

- Repetition does not increase authority.
- Model size does not increase authority.
- Majority vote does not determine truth or product direction.
- Independent domain gates remain separate.
- A blocking finding must be specific, evidenced, within scope, and resolvable.
- Contradictory factual claims seek new reproducible evidence or another authorized assessment.
- Risk-priority disagreements escalate when they require a product compromise.
- A valid waiver names risk, evidence, impact, rationale, accepting authority, and scope.

## Relationship to v0.19.0

### What v0.19.0 designed correctly

The frozen v0.19.0 architecture identifies the same target:

- Hermes should leave routine message transport after contract approval.
- Daimons should communicate through typed, contract-bound lateral messages.
- Harmonia should coordinate task state, budgets, gates, and escalation without becoming product or lifecycle authority.
- A durable ledger should preserve semantic state and evidence.
- Olympus should retain ACP lifecycle ownership.
- Reviewer disagreements should remain visible and be resolved through evidence, role authority, bounded correction, waiver, and escalation.

### What v0.19.0 did not prove

The release closeout states that v0.19.0 did not replace the live Hermes hub-and-spoke path. It remained default-off and lacked a production composition root, kernel-backed live ACP proof, complete trusted evidence, executable closure, and production migration/rollback.

The active operational path remained Hermes relaying through `talk_to` and ACPManager.

## Relationship to v0.19.x

The approved incremental migration tests one authority hypothesis at a time:

| Patch | Hypothesis |
|---|---|
| v0.19.1 | One task can traverse the real server-to-kernel-to-Olympus boundary under one semantic authority. |
| v0.19.2 | Results can be bound to trusted evidence. |
| v0.19.3 | Semantic closure and cleanup can be proven. |
| v0.19.4 | A fixed Task A → Task B handoff can occur with zero routine Hermes relay. |
| v0.19.5 | Harmonia can select a bounded next task while the kernel validates and commits. **Validated by real Gate C.** |
| v0.19.6 | Closed without a separate patch; its verdict was absorbed by the v0.19.5 deterministic fault matrix, fail-closed corrections, and final real Gate C. |

The roadmap closed at v0.19.5 with a `VIABLE — BOUNDED` verdict. This validates the demonstrated default-off topology, not production activation, arbitrary DAGs, open-ended planning, or global replacement. The product doctrine is satisfied more broadly only when these mechanics also respect user-controlled Daimon participation and improve project quality and coordination cost.

## No-relay proof

A valid no-relay workflow should demonstrate:

```text
Hermes contract submissions:                  1
Hermes routine result relays after admission: 0
Hermes next-agent selections after admission: 0
Hermes correction or retry dispatches:        0
```

Hermes may still receive an escalation or final synthesis projection. That does not violate the no-relay goal because strategic authority and routine relay are different responsibilities.

## Failure conditions

The target model fails when:

- a disabled Daimon is invoked directly or indirectly;
- a peer expands scope through a message;
- Harmonia becomes a second product, semantic, or ACP lifecycle authority;
- Hermes continues relaying every routine result;
- the kernel and another store both claim authoritative workflow state;
- uncertainty is retried blindly rather than reconciled;
- reviewer disagreement is resolved by repetition or majority;
- user attention increases without compensating product value;
- project quality does not improve over simpler general-agent execution.

## Current versus target

This document is normative product and target-system knowledge.

Current runtime behavior, implementation status, and blockers must be established from source, tests, current-system documentation, and release evidence. The v0.19.5 evidence proves bounded viability only; this model and that evidence do not authorize activation or prove global runtime parity.
