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

#### Approved contract form — Hybrid, versioned, and verifiable

The execution contract combines human-readable intent with machine-verifiable control fields. Natural language preserves meaning and rationale; structured fields let Harmonia apply authority, scope, resource, evidence, and escalation rules without inventing missing constraints.

The semantic portion must express:

- objective and expected outcome;
- user intent and rationale;
- relevant context and approved decisions;
- acceptance criteria and the meaning of success.

The structured portion must express:

- contract ID, project identity, version, and status;
- accountable owner, authorized participants, and role permissions;
- included and excluded scope;
- side-effect and external-action policy;
- concurrency, time, retry, and model-budget limits;
- required evidence and quality gates;
- escalation conditions and completion authority.

Contract rules:

- an approved version is immutable;
- a participant may request an amendment but cannot modify the contract;
- Hermes issues a new version after the required user decision or delegated approval;
- prior versions and amendment rationale remain auditable;
- tasks identify the exact contract version under which they operate;
- Harmonia pauses only work affected by a pending amendment when unaffected work can safely continue;
- peer messages are context or proposals, never implicit contract amendments;
- ambiguous constraints are escalated rather than silently interpreted as permission.

The contract schema must avoid false precision: semantic requirements remain prose where meaning cannot be reduced safely, while enforceable limits use typed fields.

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

### 3.5 Approved subtask authority — Lateral proposal with automatic admission

Any contract participant with an authorized role may propose a subtask. Harmonia admits it automatically when deterministic contract checks pass; routine proposals do not require manual approval from Hermes or the contract owner.

Every proposal must identify:

- parent task and contract version;
- objective and reason the work is necessary;
- requested capability and proposed owner;
- bounded scope and dependencies;
- acceptance criteria and expected evidence;
- requested budget and side-effect class.

Harmonia admits a proposal when:

- it derives clearly from the approved objective;
- it remains inside included scope and outside explicit exclusions;
- the requested role has authority for the task and side effects;
- contract budget and concurrency capacity remain available;
- equivalent work is not already planned or running;
- dependencies exist and the new edge creates no cycle;
- completion criteria and evidence requirements are defined;
- no external, irreversible, architectural, or product decision requires additional approval.

An admitted task becomes part of the authoritative task graph and may be dispatched without a routine Hermes or owner gate. The contract owner receives the event and may reprioritize, pause, or cancel it within contract authority.

Harmonia retains rather than rejects a proposal when scope, authority, budget, dependencies, or completion meaning are ambiguous. She requests the smallest clarification or invokes the applicable escalation path. Unaffected work continues when safe.

Accountability remains separated:

- the proposer explains why the subtask is necessary;
- the subtask owner is accountable for its result and evidence;
- the contract owner remains accountable for the integrated deliverable;
- Harmonia is accountable for admission, task-graph integrity, traceability, and contract enforcement;
- Hermes is accountable for contract amendments and escalated design decisions.

Subtask creation must follow an explicit state model such as `proposed → admitted → waiting/ready → running → review → completed`, with `retained`, `blocked`, `failed`, and `cancelled` terminal or interruption paths defined during detailed design.

### 3.6 Approved peer trust boundary — Typed messages with least authority

Daimons communicate directly through authenticated, typed message envelopes. Authentication proves provenance, not truth, correctness, or permission. Free text never grants authority.

Every coordination message must carry at least:

- message ID and correlation ID;
- project, contract ID, contract version, and task ID where applicable;
- authenticated sender identity, instance, and role;
- recipient identity, role, group, or channel;
- message type and declared authority class;
- structured references to evidence or prior messages;
- payload explicitly separated from the authority envelope.

Message classes:

1. **Informational:** observation, question, status, context, evidence, recommendation. These may influence reasoning but cannot authorize work or side effects.
2. **Requests:** task proposal, review request, clarification request, amendment request, resource request. These initiate an admission or decision process but are not commands.
3. **Results and gates:** task result, review finding, gate pass, gate fail, blocker. Their effect depends on contract-defined role authority and evidence requirements.
4. **Authorized control:** task admitted, assigned, paused, cancelled; contract activated or amended; escalation opened or resolved. Only the role or system component named by policy may emit an effective control event.

Trust rules:

- authenticated identity does not make message content trusted;
- quoted web pages, files, tool output, user content, and third-party agent content remain untrusted data through every relay;
- no free-text payload may add permissions, change role authority, alter scope, or amend a contract;
- effective authority derives from the approved contract, message type, sender role, current state, and local capability policy;
- receivers revalidate authority and side-effect permission locally before acting;
- a message with invalid type, authority, state transition, contract version, or evidence linkage is rejected or downgraded to informational context;
- Harmonia observes, correlates, and audits messages without becoming their mandatory route;
- signatures, ACLs, and credentials establish provenance and transport access, not semantic truth;
- replayed or duplicate control events must be idempotent;
- every accepted control event and gate transition remains auditable.

Role authority remains specific. For example, Athena may emit a security gate when the contract grants that review authority, but cannot amend the architecture or implement a fix; Hefesto may report implementation evidence but cannot self-approve an independent review gate.

### 3.7 Approved gate resolution — Evidence, bounded correction, explicit waiver

Required reviewers retain independent authority over their assigned gates, but a failed gate must be specific, evidenced, and resolvable. Owners cannot self-approve; reviewers cannot block indefinitely through unsupported or shifting objections.

Every review finding must identify:

- gate and acceptance criterion;
- classification: `blocking`, `non_blocking`, `advisory`, `operational`, or `insufficient_evidence`;
- precise claim, evidence, impact, confidence, and required resolution;
- contract, task, artifact, and review-attempt correlation.

Only a justified `blocking` finding automatically fails its gate. `Insufficient_evidence` prevents a pass but is not proof of a defect. Non-blocking, advisory, and operational findings remain visible without independently blocking completion unless the contract says otherwise.

The accountable owner may remediate, provide contrary evidence, challenge scope or classification, request minimal clarification, or request a risk waiver. The owner may not emit an independent review pass for its own work.

Each failed gate enters a bounded correction loop:

1. reviewer emits an evidenced finding;
2. owner responds with a correction or evidence;
3. the authorized reviewer reevaluates the same criterion;
4. the gate passes or a new precise finding identifies what remains unresolved.

The contract sets the retry limit, with three cycles as the default maximum. Harmonia tracks attempts, evidence changes, finding stability, budget, and unaffected parallel work, but does not decide the domain dispute.

After the retry limit:

- factual disputes seek independent reproducible evidence or another authorized specialist assessment;
- architecture, product, or priority disputes escalate to Hermes and the user when required;
- risk acceptance follows the contract's explicit waiver authority.

A required gate ends only as `passed`, `failed`, or `waived`. A valid waiver records the risk, evidence, impact, rationale, accepting authority, owner, and any review condition or expiry. A task may complete only when every required gate is passed or validly waived.

When authorized reviewers disagree, Harmonia preserves both findings. Independent domain gates remain separate; contradictory factual claims seek independent evidence; risk-priority conflicts escalate. Repetition does not grant a reviewer additional authority.

### 3.8 Approved observability — Complete ledger, tiered visibility

Autonomous execution is fully auditable but not fully streamed into Hermes or the user conversation. Visibility is separated by operational need.

#### Event ledger

The system records structured events for contract versions, typed messages, task proposals and admissions, ownership, state transitions, dependencies, evidence, gates, retries, waivers, budgets, escalations, external actions, failures, and recovery. Original events and artifact references remain authoritative; model summaries are derived views.

Private model reasoning is not an audit requirement. Observable actions, decisions, claims, state transitions, results, and supporting evidence are.

#### Harmonia operational view

Harmonia maintains a current projection of active contracts, task graphs, owners, participants, dependencies, gates, budget consumption, concurrency, stalls, risks, escalations, and lease health. The projection is reconstructable from durable events.

#### Hermes visibility

Hermes receives high-value signals rather than every peer message:

- contract activation and initial owner/plan;
- completed end-to-end milestones;
- significant execution-path changes;
- failed gates and retry-limit pressure;
- resource-threshold warnings;
- unresolved blockers and amendment requests;
- escalations, completion proposals, and final results.

Hermes may inspect the underlying ledger, messages, evidence, and artifacts on demand without permanently injecting them into the most expensive model's context.

#### User visibility and interruption

The user receives contract start, meaningful end-to-end milestones, significant risks, required decisions, approved scope-change requests, exhausted autonomous recovery, and final evidence-backed outcomes. Routine peer chatter, file reads, ordinary subtasks, and repetitive status do not require user attention.

Immediate user interruption is reserved for:

- architecture or product decisions;
- scope amendments;
- approval of external or irreversible actions;
- significant risk acceptance;
- exhausted retry limits;
- insufficient budget to continue;
- unresolved reviewer conflict;
- loss of contract or state integrity;
- conditions where continued execution may cause harm or invalid work.

Harmonia resolves ordinary availability, duplication, dependency, retry, evidence-acquisition, partial-blocking, stale-message, and recoverable-runtime conditions before escalating.

Progress reporting is milestone-driven rather than timer-driven. Internal heartbeats detect stalled runtimes but are not presented as user progress unless they expose an operational problem.

### 3.9 Approved state authority — Layered sources of truth

State authority is partitioned by domain so that transport, runtime, coordination, artifacts, and continuity cannot make conflicting claims about the same fact.

#### Transport plane

Cotal or another selected transport is authoritative only for delivery, redelivery, technical acknowledgements, connection identity, presence, subscriptions, consumer state, retention, and replay. Delivery does not prove task success, gate completion, contract amendment, or architectural approval.

#### Aether coordination ledger

An Aether-owned durable ledger is authoritative for contract versions, tasks, dependencies, owners, participants, admission, semantic execution state, budgets, gates, findings, retries, waivers, escalations, Harmonia leases, evidence correlation, and autonomous coordination events. Harmonia reconstructs her operational projection from this ledger.

The physical store remains a research question. Feasibility analysis must compare extending `aether.db`, creating a separate coordination store, using a shared database, or projecting transport events into Aether-owned storage without changing the logical ownership model.

#### Olympus and ACP

Olympus is authoritative for live ACP execution facts: session and process identity, messaging handle, runtime heartbeat, technical completion, cancellation, and closure. An ACP session completing does not by itself complete the semantic task; Harmonia still evaluates result evidence and required gates through the ledger.

#### Artifacts

Repositories, files, commits, test reports, builds, documents, packages, and authorized external objects are authoritative for their actual content. Ledger evidence references artifacts through stable paths or identifiers, provenance, task correlation, and hashes where practical. Agent summaries do not replace artifacts.

#### `.aether` continuity

`.aether` remains authoritative for durable project continuity: phase, current task, architectural decisions, issues, observations, historical sessions, relevant file changes, and context for future work. The coordination ledger promotes only durable milestones, decisions, blockers, waivers, results, and phase-relevant events into `.aether`; routine messages and heartbeats do not pollute continuity.

`.aether/CONTEXT.md` remains a curated projection generated by Ariadna, never primary operational state.

The invariant is:

> Transport proves delivery. Olympus proves runtime execution. The coordination ledger proves coordination state. Artifacts prove results. `.aether` preserves project continuity and decisions.

Recovery reconciles layers without transferring authority. Loss of transport must not erase contracts; Harmonia restart rebuilds from the ledger; Olympus restart exposes orphaned runtime work for idempotent recovery; stale curated context is regenerated from durable continuity data.

### 3.10 Approved resource governance — Hierarchical budgets and adaptive backpressure

Autonomous coordination uses bounded, hierarchical resource envelopes rather than unrestricted parallelism or one fixed global limit.

Resource authority is layered:

- project limits cap total active runtimes, per-role concurrency, expensive tools, model usage, elapsed time, event storage, and exclusive resources;
- each contract receives explicit concurrency, attempt, time, and model-budget limits from Hermes;
- subtasks request bounded slices from their contract;
- Harmonia may reduce, queue, or reallocate unused resources inside a contract but cannot exceed its hard cap or take from another contract without authorized reallocation.

Every contract reserves capacity for integration, required validation, recovery, and final synthesis. Routine implementation, research, advisory work, or speculation cannot consume that reserve and leave the deliverable unverified.

Work priority is:

1. integrity recovery;
2. required quality gates;
3. critical-path deliverables;
4. necessary supporting research or consultation;
5. non-blocking advisory work;
6. speculative exploration.

Harmonia permits parallel execution only when tasks are independent, resource-safe, role capacity exists, integration and QA reserves remain intact, and coordination overhead does not outweigh expected benefit. Logical independence does not authorize unsafe concurrent writes to shared artifacts, migrations, ports, servers, devices, deployments, or external systems.

Backpressure is progressive:

1. deduplicate work, reuse evidence, batch related requests, and avoid unnecessary agent activation;
2. stop admitting speculative work, postpone advisory tasks, and reduce concurrency while preserving recovery, gates, and the critical path;
3. pause new subtasks, allow only safe in-flight boundaries, preserve state and evidence, and notify Hermes;
4. at the hard limit, stop rather than overspend and escalate with consumption, remaining work, and explicit options to increase budget, reduce scope, accept a partial outcome, or terminate the contract.

Soft thresholds trigger optimization and warnings; hard limits are enforceable stops. Metrics may use tokens, monetary estimates, elapsed time, attempts, normalized model units, or a combination according to verified provider telemetry. Missing cost telemetry must be represented as uncertainty, not zero consumption.

## 4. New Daimon — Harmonia

v0.19.0 will introduce **Harmonia — Coordination Steward**, dedicated to contract state and autonomous execution governance. Its name, role, and operating personality are approved; its invocation model, tools, persistence boundary, and lifecycle remain design decisions.

### Identity and eponym

Harmonia is the Greek personification of harmony and concord. In Aether, her identity does not imply passive agreement or suppression of disagreement. She facilitates useful coordination while preserving evidence, specialist independence, reviewer authority, and the limits of the approved contract.

> **Harmonia — Coordination Steward**
> Facilitating sentinel of autonomous execution. She keeps contracts, dependencies, evidence, and quality gates aligned without owning specialist work or replacing Hermes's design authority.

The name emphasizes lateral cooperation and calm conflict resolution. Contract enforcement prevents harmony from degrading into artificial consensus: a justified disagreement, failed gate, or evidence-backed escalation must remain visible.

### Why a new role is likely necessary

Moving routine coordination out of Hermes without assigning it explicitly would create ambiguous ownership. Existing Daimons have focused domain identities:

- Hefesto implements;
- Etalides researches;
- Athena reviews security and quality risk;
- Ictinus advises on backend architecture;
- Daedalus advises and prototypes design;
- Ariadna curates continuity.

Making one of these roles the permanent coordinator would blur its domain authority. A dedicated role preserves Hermes as design authority while maintaining execution-level coordination without displacing the accountable domain owner.

### Approved authority model

Hermes assigns each contract to an accountable domain owner. The Coordination Steward does not become the default owner and does not replace specialist judgment. It guards the contract and the autonomous process around that owner.

The Coordination Steward is responsible for:

- receive and track an approved contract from Hermes;
- record the accountable owner and participant roster;
- maintain the task graph and correlation between subtasks;
- enforce scope, budget, retry, and concurrency limits;
- observe presence and identify stalls;
- route events without becoming the only communication path;
- ensure required QA gates occur;
- consolidate execution state for Hermes without replacing domain evidence;
- trigger escalation when contract conditions are met;
- prevent a task from declaring completion without the required evidence;
- provide Hermes with synthesized state and escalation events rather than relaying every routine message.

The Coordination Steward must not:

- independently redesign the user's objective;
- silently expand scope;
- replace the accountable owner's domain judgment;
- become the mandatory route for lateral peer communication;
- implement specialist work merely to accelerate execution;
- overrule a valid reviewer gate outside an approved escalation path.

### Approved operating personality — Facilitating Sentinel

The Coordination Steward is calm, attentive, diplomatic, anticipatory, and evidence-led. It protects progress without becoming a commander or a bureaucratic checkpoint.

Its behavioral contract is:

- observe continuously but intervene selectively;
- identify drift, missing evidence, dependency risk, and likely stalls before they become contract failures;
- communicate with concise factual prompts rather than repeated status demands;
- facilitate agreements between specialists without replacing their judgment;
- keep independent work moving when one dependency is blocked;
- prefer evidence and contract language over hierarchy or persuasion;
- escalate with a precise condition, impact, evidence, and requested decision;
- remain composed under failure and avoid urgency theater;
- protect momentum without trading away scope, QA, or truthfulness.

Its authority comes from maintaining a shared, accurate view of the contract and execution state—not from commanding the team. It should feel present and dependable without dominating routine collaboration.

### Approved lifecycle — Durable identity, on-demand runtime

Harmonia has one durable logical identity per project, but her model runtime is active only while autonomous work requires coordination. Model conversation history is never the source of truth for contract state.

Lifecycle requirements:

- Hermes activates Harmonia when an approved contract enters execution or a relevant coordination event requires attention;
- Harmonia remains active while the project has running contracts or unresolved escalations;
- multiple contracts may coexist, but each retains an independent owner, scope, budget, state, and evidence chain;
- structured durable state records contracts, tasks, dependencies, participants, events, gates, retries, and escalations;
- after a configurable idle interval with no active work, the runtime closes without deleting durable identity or state;
- after restart, Harmonia reconstructs an authoritative view from durable records rather than relying on remembered conversation;
- a project-scoped lock or renewable lease prevents two active Harmonia runtimes from coordinating the same project concurrently;
- lease loss forces the stale runtime to stop coordinating and report an operational event;
- runtime failure must not erase Daimon results, contract history, or project continuity;
- upgrades and restarts must be possible without migrating conversational memory.

This model separates **identity**, **state**, and **reasoning runtime**. Identity and state persist; model execution is demand-driven.

## 5. Target topology — provisional

```text
User
  │
  ▼
Hermes — requirements, design, contract, decisions, escalation
  │ approved contract
  ▼
[Harmonia — contract state, limits, gates, escalation]
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

The accountable domain Daimon owns the deliverable. The Coordination Steward supervises contract state and execution invariants while authorized participants communicate laterally.

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

The next user decision is side-effect and recovery safety: how contracts classify actions, how retries remain idempotent, and how Harmonia determines whether a timed-out or disconnected operation should resume, retry, compensate, or escalate. This is mandatory because durable delivery and process recovery can repeat work.
