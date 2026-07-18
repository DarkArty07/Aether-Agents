# v0.19.0 Autonomous Coordination — Design

**Status:** IDEA / requirements discovery. No implementation is authorized.

**Date:** 2026-07-18

## 1. Purpose

Aether Agents v0.19.0 explores a major architectural evolution: move from a model where Hermes invokes Daimons as isolated tools and manually transports every handoff, toward a contract-bounded autonomous team whose members can communicate and coordinate directly.

The goal is not maximum autonomy. The goal is to remove routine coordination from Hermes while preserving the qualities that define Aether: design with the user, explicit authority, specialized identities, evidence-based quality gates, continuity, observability, and safe escalation.

## 2. Problem statement

Aether currently centralizes both strategic reasoning and routine execution routing in Hermes. Hermes understands the user, designs the solution, decomposes work, invokes each Daimon, receives every result, and forwards relevant context to the next Daimon. This produces strong control and visibility, but it also makes the most capable and expensive model the message bus for all agent interaction.

Communication-only changes would not solve that bottleneck. Fully self-organizing agents would remove the bottleneck but also risk losing Aether's design-led identity, role boundaries, traceability, and user control.

v0.19.0 must separate two responsibilities:

1. **Strategic authority:** understanding intent, designing contracts, making architectural decisions, and governing escalation.
2. **Bounded execution coordination:** creating subtasks, selecting specialists, exchanging evidence, reviewing work, and correcting failures within an approved contract.

## 3. Approved architectural principles

### 3.1 Feasibility before implementation

This initiative remains limited to requirements, research, design, and viability analysis until an explicit GO decision.

Before that gate, the project will not:

- fork or vendor Cotal;
- install candidate coordination infrastructure;
- modify Olympus, Hermes profiles, Daimon profiles, or runtime configuration;
- create connectors or protocol implementations;
- run a migration or integration spike.

A future spike may be designed during this phase, but it must not be executed without separate approval.

### 3.2 Contract-bounded autonomy

Hermes and the user define and approve an execution contract. At minimum, the contract contains:

- objective and expected outcome;
- scope and explicit exclusions;
- relevant context and evidence requirements;
- role authorities and prohibited actions;
- acceptance criteria and QA gates;
- resource, time, and retry limits;
- escalation conditions;
- completion authority.

Once approved, Daimons may autonomously:

- create subtasks inside the contract;
- select and contact relevant specialists;
- exchange context, evidence, questions, and results;
- request research, consultation, implementation, or review;
- run implementation-review-correction loops;
- report progress events without pausing execution.

They must escalate:

- architectural or product decisions not settled by the contract;
- scope changes;
- irreversible or externally consequential actions not authorized by the contract;
- missing access, dependencies, credentials, or infrastructure;
- conflicts that cannot be resolved from evidence and role authority;
- repeated failure at the contract's retry limit;
- any condition that would violate the contract.

### 3.3 Hermes remains the design authority

Hermes remains the only agent the user must interact with directly. Hermes uses the strongest model because its primary responsibility is not message transport; it is understanding the user's intent and turning that intent into a coherent, safe, testable contract.

Hermes retains responsibility for:

- requirements discovery and design conversation;
- architectural options and trade-offs;
- contract definition and approval;
- phase and scope governance;
- user-visible synthesis;
- escalation handling;
- observability and intervention;
- final recommendation at major decision gates.

Hermes must not remain the routine relay for every Daimon-to-Daimon interaction. If every handoff still requires Hermes, v0.19.0 has failed its central goal.

### 3.4 Lateral team with an accountable owner

Each approved contract has one accountable owner. The owner is responsible for integrating evidence and proposing completion, but is not the only participant allowed to coordinate.

Any participating Daimon may contact another relevant role inside the contract. This is a lateral team constrained by role authority, not a free-for-all.

Required invariants:

- one contract has one accountable owner at a time;
- all participants may communicate laterally when relevant;
- role boundaries remain binding;
- consultants do not silently become implementers;
- reviewers may block completion within their review authority but may not redefine the product;
- only the accountable owner may propose that the contract is complete;
- Hermes handles unresolved escalations and changes to the contract;
- every delegation, result, review, retry, and escalation remains observable.

This rejects both a single local leader as the exclusive communication hub and a rigid fixed workflow.

## 4. New Daimon requirement

v0.19.0 is expected to introduce a new permanent Daimon dedicated to autonomous execution coordination. Its final name, eponym, personality, authority, invocation model, tools, and lifecycle are intentionally undecided.

### Why a new role is likely necessary

Moving routine coordination out of Hermes without assigning it explicitly would create ambiguous ownership. Existing Daimons have focused domain identities:

- Hefesto implements;
- Etalides researches;
- Athena reviews security and quality risk;
- Ictinus advises on backend architecture;
- Daedalus advises and prototypes design;
- Ariadna curates continuity.

Making one of these roles the permanent coordinator would blur its domain authority. A dedicated role can preserve Hermes as design authority while operating the approved contract and maintaining execution-level coordination.

### Candidate responsibilities to decide

The role may be responsible for some or all of the following, subject to user approval:

- receive an approved contract from Hermes;
- establish the initial task owner and participant roster;
- maintain the task graph and correlation between subtasks;
- enforce scope, budget, retry, and concurrency limits;
- observe presence and identify stalls;
- route events without becoming the only communication path;
- ensure required QA gates occur;
- consolidate execution state for Hermes without replacing domain evidence;
- trigger escalation when contract conditions are met;
- prevent a task from declaring completion without the required evidence.

The new agent must not independently redesign the user's objective or silently expand scope.

## 5. Target topology — provisional

```text
User
  │
  ▼
Hermes — requirements, design, contract, decisions, escalation
  │ approved contract
  ▼
[New coordination Daimon — exact authority TBD]
  │
  ├──────── accountable task owner
  │               │
  │       ┌───────┼────────┐
  │       ▼       ▼        ▼
  │   Hefesto  Etalides  Ictinus
  │       ▲       │        │
  │       └───────┼────────┘
  │               ▼
  └──────────── Athena / QA gate

All authorized participants may communicate laterally.
Hermes receives events and escalations, not every routine handoff.
```

The diagram does not yet decide whether the new Daimon owns contracts, merely supervises them, or acts as a coordination service while task ownership stays with a domain Daimon.

## 6. Properties v0.19.0 must preserve

The feasibility study must treat these as candidate non-negotiable requirements and validate them with the user:

- Hermes remains the user-facing design authority.
- Explicit contracts precede autonomous execution.
- Every task and subtask has attributable ownership.
- Daimon specializations and write boundaries remain meaningful.
- Architectural and product decisions remain human-governed.
- QA failures cannot be averaged or narrated away.
- Missing evidence remains insufficient, not success.
- `.aether` continuity remains durable and truthful.
- Agent communication and lifecycle are observable and auditable.
- Retries, duplicate delivery, and side effects are bounded and idempotent.
- The system can stop, escalate, and recover without losing project state.
- Migration must be staged and reversible.

## 7. Research and feasibility questions

The design is not complete until research answers:

1. Can Cotal support persistent Aether/Hermes profiles without temporary homes or session loss?
2. Can a coordination protocol carry Aether contracts, evidence, reviews, and escalation semantics without forking its wire core?
3. Which component owns agent lifecycle: Olympus, Cotal Manager, Hermes gateway, or a redesigned boundary?
4. How are identity, project root, contract ID, task ID, session ID, and message ID correlated?
5. How are at-least-once messages deduplicated before external side effects?
6. Which messages may become agent context, and how are untrusted messages prevented from becoming privileged instructions?
7. How are role permissions and reviewer vetoes enforced rather than merely prompted?
8. What execution state belongs in a message broker, Olympus storage, and `.aether`?
9. What does Hermes need to observe, and what can remain summarized until escalation?
10. Can the design tolerate loss or replacement of Cotal without losing Aether project continuity?
11. What maintenance burden would an upstream-compatible extension, focused fork, or deep fork impose?
12. Which comparable protocols or frameworks offer a better fit?

## 8. Planned design artifacts

The v0.19.0 exploration will produce:

1. `DESIGN.md` v1 — this living requirements and design document.
2. `BASELINE.md` — verified current Aether architecture and irreplaceable properties.
3. `RESEARCH.md` — candidate and protocol evidence, beginning with Cotal.
4. `FEASIBILITY.md` — fit-gap, security, operations, cost, maturity, and maintenance analysis.
5. `DESIGN.md` v2 — two or three complete target architectures.
6. `MIGRATION_PLAN.md` — reversible stages and proposed spikes, without execution.
7. Final `GO`, `NO-GO`, or `CONTINUE RESEARCH` recommendation for explicit approval.

## 9. Current decision gate

The next user decision is the exact authority of the new coordination Daimon. Role definition must precede naming and personality so that its identity reflects a real responsibility rather than forcing the architecture to fit a name.
