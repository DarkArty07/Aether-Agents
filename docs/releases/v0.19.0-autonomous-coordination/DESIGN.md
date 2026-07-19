# v0.19.0 Autonomous Coordination — Design v2

**Status:** **APPROVED — DEFAULT-OFF IMPLEMENTATION AUTHORIZED.** On 2026-07-18 the user authorized autonomous execution of Phase 0 through the code-complete R7 shadow-mode gate under `IMPLEMENTATION_PLAN.md`. Live gateway restart, runtime activation, credential repair, real pilot effects, merge, tag, and release remain separately blocked while the user is away.

**Date:** 2026-07-18

## 0. Decision summary v2

**Selected architecture:** Option A — an **Aether-native coordination control plane over Olympus/ACP**. The Aether Contract Registry and append-only Coordination Ledger are the semantic authority; deterministic admission, capability, effect-reconciliation, and closure components enforce typed rules. Olympus/ACP remains the sole owner of process, ACP connection, session, heartbeat, technical cancellation, and technical closure. Native ledger-backed dispatch is the initial transport behind a `TransportAdapter` seam.

**Ranking and exclusions:** Direct NATS JetStream is **Option C**, a future transport-only scale-out candidate requiring separate evidence and approval. Cotal transport-only is **Option B**, ranked last, not selected, not adopted or forked, and excluded from the initial runtime. Neither Cotal nor any transport owns contracts, lifecycle, completion, or semantic authority.

**Authority and status:** Hermes remains the user-facing design, contract, amendment, escalation, and ordinary completion authority. Harmonia has one durable logical identity per project and an on-demand, leased runtime for coordination stewardship; she is not a process/session lifecycle owner. Phase 0 and staged default-off implementation are authorized; deployment, candidate infrastructure, live activation, credential mutation, and real effects are not.

**Closure:** completion is two-stage: the accountable owner proposes an evidenced terminal result; Harmonia performs deterministic mechanical validation. The completion authority is `automatic` only for explicitly configured low-risk routine work, `hermes` by default, or `user` for reserved decisions. The only final semantic states are `completed`, `partially_completed`, `failed`, and `cancelled`.

### 0.1 Why Aether does not embed Cotal Core directly

The phrase **“Cotal-Core-inspired”** is an architectural boundary, not a rejection of Cotal's ideas. Aether adopts the transport-agnostic concepts that make Cotal valuable—owner/actor principals, participant cards, typed envelopes, multicast/unicast/anycast, presence, channels, live/durable delivery classes, and separate active/read/publish permissions—but implements them inside Aether's Python/Olympus control plane.

A literal dependency on `@cotal-ai/core` is not selected for the initial v0.19 runtime because:

1. Cotal's reference core is TypeScript and its only defined transport binding is currently NATS/JetStream, which would add a Node sidecar, broker operations, a Python↔TypeScript bridge, and a second failure/recovery surface before local Aether coordination proves that scale is needed.
2. Cotal Core provides wire identity, routing, delivery, presence, and transport grants; it does not provide Aether's execution-contract authority, immutable task generations, independent QA gates, E0–E4 effect reconciliation, semantic completion, or `.aether` continuity. Those Aether-owned layers are required regardless of transport choice.
3. Cotal's current Hermes connector is incompatible with Aether's baseline: it targets the Hermes 0.16 line, launches a child gateway in a temporary `HERMES_HOME`, disables approvals, and does not resume sessions. Aether requires persistent profiles, the existing Telegram gateway, and Olympus as the sole process/session lifecycle owner.
4. Embedding the connector or Manager would create competing lifecycle ownership. v0.19 instead keeps a `TransportAdapter` seam so a future Cotal/NATS binding can be evaluated without transferring semantic or lifecycle authority.

This choice does not preclude interoperability. A later adapter may implement the Cotal Wire Specification after native behavior is measured and a separate compatibility/operations gate approves NATS. The adapter must preserve Olympus lifecycle ownership and treat transport delivery as evidence, never semantic completion.

### 0.2 Observable difference from Aether v0.18.2

Today Hermes is both strategic authority and routine relay: it decomposes work, calls one Daimon, receives the result, forwards context to the next Daimon, drives every review/correction loop, and synthesizes completion. Daimons are specialized tools with no contract-authorized lateral coordination.

In v0.19.0:

- Hermes and the user approve an immutable execution contract, then Hermes leaves routine message transport;
- Harmonia deterministically admits in-scope subtasks, tracks budgets/gates/stalls, and escalates ambiguity without becoming a process manager or product authority;
- Daimons exchange typed, contract-bound envelopes laterally through multicast, unicast, or role-anycast routes;
- the Coordination Ledger records semantic intent, authority, tasks, reviews, effects, evidence, and closure, while Olympus continues to record and own technical sessions/processes;
- Aether-issued PoP capabilities bind every privileged operation to project, contract generation, task, role, audience, target, effect, expiry, revocation epoch, and fencing epoch;
- completion becomes two-stage and evidenced rather than equated with an ACP session returning `completed`.

The expected user-facing result is fewer Hermes relay turns, less flagship-model message-bus cost, autonomous specialist coordination inside approved boundaries, and preserved escalation/control when a real decision is required.

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

The approved coordination architecture is now authorized for Phase 0 and staged default-off implementation through R7. Execution remains bounded by the gateway-survival, budget, TDD, review, and stop gates in `IMPLEMENTATION_PLAN.md`; live activation and externally consequential effects remain separately prohibited.

Before that gate, the project will not:

- fork or vendor Cotal;
- install candidate coordination infrastructure;
- modify Olympus, Daimon profiles, or autonomous-coordination runtime configuration; the sole approved profile exception is the versioned Hermes `home/SOUL.md` operational-contract optimization described in §3.3;
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

The v0.19.0 release baseline includes the approved Hermes operational-contract optimization. It preserves Hermes as design and escalation authority while making routine execution policy deterministic:

- explicit instruction precedence protects current user intent and authorization boundaries;
- FAST, STANDARD, and FULL paths prevent small work from being forced through the full pipeline;
- session identity is scoped by `session_id + PROJECT_ROOT + AETHER_HOME`, including concurrent instances of one Daimon profile;
- logical session closure is distinguished from persistent ACP profile processes;
- validation is proportional to risk rather than routing every change through Athena;
- each stable review task permits at most three total Athena executions, including the initial audit, before mandatory escalation;
- conversation turn count alone never forces delegation while scope remains precise and progress verifiable.

These prompt-level rules are part of v0.19.0 governance and release scope. They do not grant Daimons lateral communication, contract admission, capability enforcement, ledger authority, or any other runtime coordination feature before its separately authorized implementation gate.

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

Subtask creation follows this explicit state model: `proposed → admitted → ready → dispatched → running → review → closure_proposed → accepted → completed | partially_completed | failed | cancelled`. `retained`, `blocked`, `failed`, `cancelled`, and the bounded correction loop are explicit interruption paths; no other final semantic state is valid. A `partially_completed` state must identify the accepted partial outcome, unmet acceptance criteria, remaining risk, and completion authority decision.

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

The contract sets the retry limit, with three cycles as the default maximum. Harmonia tracks attempts, evidence changes, finding stability, budget, and unaffected parallel work, but does not decide the domain dispute. Required reviewer independence means distinct owner, runtime instance, workload credential/capability, and review role; no same control identity may self-review. Shared-model or systemic risk remains visible, and independence is not claimed to remove it.

After the retry limit:

- factual disputes seek independent reproducible evidence or another authorized specialist assessment;
- architecture, product, or priority disputes escalate to Hermes and the user when required;
- risk acceptance follows the contract's explicit waiver authority.

A required gate ends only as `passed`, `failed`, or `waived`. A valid waiver records the risk, evidence, impact, rationale, accepting authority, owner, and any review condition or expiry. An E4 approval or waiver is a typed, strongly authenticated, immutable, nonce/expiry/replay-protected record bound to the exact effect or finding, artifact, target, contract generation, and hash; free text never represents approval. A task may complete only when every required gate is passed or validly waived.

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

### 3.11 Approved effect safety — Classified, receipted, and idempotent

Every observable operation is classified before execution:

- `E0` — read-only;
- `E1` — local, isolated, and reversible;
- `E2` — local shared or destructive;
- `E3` — external but reversible;
- `E4` — external, sensitive, or irreversible.

Contracts may preauthorize bounded E0 and E1 operations. E2 requires explicit capability, resource exclusion, preconditions, and recovery planning. E3 requires explicit contract authority, a verifiable remote receipt, and destination idempotency where available. E4 requires approval from the designated authority—normally the user—at execution time; free-text claims of approval are invalid.

Each effect records a stable effect ID and idempotency key derived from contract, task, operation intent, and version; class, target, authorization, preconditions, expected receipt, and state. E2 requires a proof-of-possession capability, preconditions, and resource exclusion/lease. E3 requires exact explicit contract authority, target binding, remote receipt, and destination idempotency where available. E4 requires the exact typed approval described in §3.7 at execution time. The effect lifecycle distinguishes `planned`, `authorized`, `executing`, `succeeded`, `failed`, `unknown`, `reconciled_succeeded`, `reconciled_failed`, and `manual_resolution`.

Retry rules:

- E0 may repeat when the read itself is not a consequential external action;
- E1 may repeat under preserved preconditions and the same idempotency identity;
- E2 and E3 require target reconciliation before retry;
- E4 never retries automatically after an unknown outcome;
- `unknown` is never treated as failure;
- retrying reuses the original idempotency key rather than creating a new logical operation.

Successful effects produce verifiable receipts such as artifact hash and path, commit, migration ID, remote object ID or URL, API result, deployed version, timestamp, actor, and before/after preconditions. Ledger summaries reference the actual target or artifact rather than replacing it.

After runtime loss, Harmonia consults Olympus, the coordination ledger, and the target system before choosing resume, retry, compensate, or escalate. Compensation is a separate authorized effect with its own risks and evidence; it is not assumed to be a perfect rollback.

The system does not promise universal exactly-once execution. It aims for effectively-once observable effects where the destination supports idempotency and otherwise stops for reconciliation before repetition.

### 3.12 Approved capability authority — Least-privilege intersection

Effective authority is the intersection of permanent role ceilings, project policy, contract grants, task-scoped capabilities, and runtime enforcement. A denial at any layer denies the action; authority is default-deny rather than inferred from message text.

Permanent role ceilings preserve Daimon identity and cannot be elevated by a contract. Consultants do not become implementers, implementers do not self-approve independent gates, Harmonia does not perform specialist work, and continuity curation does not acquire decision authority.

Project policy limits protected branches, sensitive paths, secret material, available tools and environments, network access, globally prohibited actions, mandatory approvals, and shared resources.

Contracts grant only the subset of role and project authority required for the approved outcome. Each admitted task then receives a short-lived, non-transferable signed proof-of-possession capability bound to installation/project, agent role/profile, Olympus session ID, runtime instance, issuer/audience, contract version, task, exact target, permissions, resources, effect classes, lease/fencing epoch, expiry, and revocation epoch. E2–E4 never rely on bearer-only authority; E2–E4 require online revocation checking at the tool/effect boundary.

Capabilities:

- use minimum necessary scope;
- cannot exceed the issuer's policy authority or the recipient's role ceiling;
- cannot be transferred or silently delegated;
- cannot mint a stronger capability;
- expire and are revocable;
- remain auditable without exposing embedded secrets.

Runtime enforcement should constrain actual tools, paths, worktrees or sandboxes, commands, network destinations, credentials, effect classes, leases, and expiration where technically feasible. Any rule enforced only through model instructions must be labeled as a soft control and residual risk, never presented as a hard security boundary.

A capability is revoked when its task ends or is cancelled, ownership changes, the contract pauses or changes version, its lease or TTL expires, runtime identity is lost, a violation occurs, Harmonia loses coordination authority, or Hermes issues an authorized stop. Revocation prevents new effects; active operations reach a safe boundary or enter reconciliation, and evidence is preserved.

Credentials are referenced opaquely and delivered through the minimum authorized runtime boundary. They are not placed in message payloads or coordination events. Agent and runtime identities support independent credential rotation and revocation.


### 3.13 v2 security enforcement requirements

The following hard requirements consolidate and make explicit the approved security additions. They are enforced by cryptography, state-transition logic, storage transaction/CAS semantics, or tool/effect-boundary checks. Prompt text, model judgment, and advisory policy are soft controls and residual risk; they cannot authorize effects.

1. **Workload identity:** Aether controls a short-lived proof-of-possession credential bound to installation/project, agent role/profile, Olympus session ID, runtime instance, issuer/audience, expiry, and revocation epoch.
2. **Ledger integrity:** authenticated writers; append-only immutable events; server sequence/time; serializable/CAS transitions; a per-project hash chain and signed checkpoints; rebuildable projections; protected backup/restore and integrity verification.
3. **Fencing:** Harmonia’s renewable lease carries a monotonically increasing fencing epoch. Every privileged ledger mutation and E2–E4 authorization rejects a stale epoch.
4. **Amendment and revocation:** an amendment is atomic: increment generation, append the immutable new version, revoke affected capabilities, fence stale messages, place affected in-flight E2–E4 work into reconciliation, then publish the transition. A task, message, or capability with a mismatched generation cannot create a semantic transition.
5. **Context boundary:** a bounded renderer separates authority metadata from tainted untrusted payload; provenance survives relays; peer/external text never becomes system authority; and runtime tools independently enforce effects.
6. **PoP capability boundary:** capabilities are signed/proof-of-possession, audience/task/target/effect scoped, short-lived, and checked at the tool/effect boundary. E2–E4 require online revocation checking.
7. **E4 and waiver approval:** E4 approval and risk waiver are exact typed, authenticated, immutable, nonce/expiry/replay-protected bindings to the relevant effect or finding, artifact, target, contract generation, and hash. Free text is invalid.
8. **Reviewer independence:** an independent required review has a distinct owner, runtime instance, workload credential/capability, and review role. No same control identity self-reviews.
9. **Adversarial quotas:** rate, size, fan-out, proposal, retry, review-challenge, artifact, lease, model, and tool-cost quotas apply, while required QA and recovery capacity remains reserved.
10. **Recovery ordering:** after restart, lease loss, or partial outage: verify ledger authority/integrity; process inbox/outbox; query Olympus runtime facts; reconcile targets/artifacts; only then perform an authorized semantic transition. No new authority or E2–E4 authorization is issued during integrity uncertainty.

The following are non-waivable for autonomous continuation and fail closed to escalation: identity failure; ledger-integrity failure; unknown E4 outcome; missing critical evidence; secret-access violation; and missing independent review.

## 4. New Daimon — Harmonia

v0.19.0 defines **Harmonia — Coordination Steward**, dedicated to contract state and autonomous execution governance. Her name, role, operating personality, durable project identity, on-demand reasoning runtime, and non-ownership of Olympus process/session lifecycle are approved. Her concrete invocation mechanism, tools, persistence implementation boundary, and adapter insertion points remain proposed until an explicitly authorized Phase 0 verifies them.

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

Harmonia has one durable logical identity per project, but her model runtime is active only while autonomous work requires coordination. The Aether Contract Registry and Coordination Ledger, not model conversation history, are the semantic source of truth. Olympus/ACP remains the sole process/session lifecycle owner; Harmonia never spawns, closes, or owns ACP processes or sessions.

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


### 4.1 v2 completion and closure authority

Completion is explicitly two-stage:

1. **Owner proposal:** the accountable owner proposes a terminal result and submits required evidence, artifact references/hashes, gate outcomes, and unresolved effects.
2. **Harmonia validation:** deterministic mechanical validation checks the task graph and gates, evidence references, contract generation, capability/effect reconciliation, leases/fencing, and required continuity publication. It does not replace an independent reviewer’s domain judgment.

| Completion authority | When it may accept closure | Required path |
|---|---|---|
| `automatic` | Explicitly configured low-risk routine work only | Owner proposal + Harmonia validation; no prohibited condition |
| `hermes` (**default**) | Ordinary work after mechanical validity | Harmonia validates; Hermes accepts, rejects, or escalates |
| `user` | Architecture/product decisions, releases, E4, material waiver, scope change, contractual/external delivery | Harmonia validates; Hermes presents evidence; user accepts or rejects |

`automatic` is prohibited for architecture/product decisions, releases, E4, material waivers, scope changes, and contractual/external delivery. Before terminal publication, cleanup occurs in this exact order: **revoke capabilities; reconcile effects and Olympus sessions; release leases; publish required durable continuity; then allow Harmonia to idle-shut down.** An ACP session completing is runtime evidence, not semantic task completion.

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


### v2 selected control-plane topology

```text
User <-> Hermes (design, contract, amendment, escalation)
                 |
                 v
Aether Contract Registry + immutable Coordination Ledger
                 |              ^
        Harmonia (leased, fencing-epoch coordinator)
                 |
  Admission Engine / Capability Issuer / Effect Reconciler
                 |
       Olympus Runtime Adapter -> Olympus/ACP -> Daimon runtimes
                 |
     TransportAdapter (native ledger-backed dispatch in v0.19)
```

The Contract Registry and Coordination Ledger are Aether-owned and append-only/rebuildable. Deterministic control-plane components enforce admission, capability issuance/validation, effect reconciliation, and closure; they do not infer authority from prose. Transport supplies delivery/retry mechanics only. This topology preserves lateral direct communication and never makes Harmonia the mandatory relay.

## 6. Properties v0.19.0 must preserve

The feasibility study and all future phases must preserve these approved non-negotiable requirements:

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

The selected architecture is approved, but these implementation facts remain unknown and must be evidenced during the now-authorized Phase 0 before production-code stages advance:

1. Which exact Olympus and ACP extension seams can propagate project, contract, task, runtime, and message correlation without creating a second lifecycle owner?
2. Which installed runtime attributes can be bound into Aether proof-of-possession workload identity, and where are issuance, rotation, revocation, and key custody enforced?
3. Can the selected physical coordination store provide the required serializable/CAS transitions, fencing, append-only integrity, transactional inbox/outbox, verified backup/restore, and projection rebuild?
4. Which tool and effect interception point can enforce task capabilities, target restrictions, revocation, and fencing independently of model behavior?
5. How are at-least-once messages durably deduplicated and ordered before semantic transitions or external side effects?
6. Which messages may become bounded agent context, and how are provenance and taint preserved while untrusted text is prevented from becoming authority?
7. Which measurable identity and control-domain properties establish reviewer independence beyond distinct role names?
8. How does recovery reconcile ledger, inbox/outbox, Olympus runtime facts, artifacts, and target receipts at every crash boundary?
9. Which milestone, gate, budget, blocker, escalation, and completion signals must reach Hermes, and which routine events remain drill-down only?
10. What measured throughput, latency, fan-out, multi-host, or recovery requirement would justify replacing native dispatch with direct JetStream?
11. If Cotal is ever reconsidered, can a transport-only adapter preserve persistent profiles, approvals, resume, Olympus ownership, and Aether semantic authority without using the current connector lifecycle?
12. Which cryptographic, storage, and transport dependencies satisfy the approved requirements with acceptable maintenance, licensing, and operational cost?

## 8. Design artifacts and status

The pre-code exploration has produced the complete versioned package:

1. `DESIGN.md` v2 — preserved normative requirements, selected architecture, closure model, and security boundaries.
2. `BASELINE.md` — verified current Aether architecture and irreplaceable properties.
3. `RESEARCH.md` — Cotal and alternative evidence with verified/inferred/unknown labels.
4. `FEASIBILITY.md` — fit-gap, threat, operations, cost, maturity, and maintenance analysis with the final recommendation.
5. `MIGRATION_PLAN.md` — reversible stages and authorized isolated evidence-only proofs.
6. `IMPLEMENTATION_PLAN.md` — exact authorized TDD sequence and gates through default-off R7.
7. `ROADMAP.md` — canonical release milestones, entry/exit gates, rollback boundaries, release criteria, and current blockers.

The decision is **GO for the authorized staged Aether-native implementation** and **NO-GO for direct Cotal integration or fork in the initial v0.19 runtime**.

## 9. Current execution gate

The user's 2026-07-18 approval authorizes the exact Phase 0→R7 default-off sequence in [MIGRATION_PLAN.md](MIGRATION_PLAN.md) and [IMPLEMENTATION_PLAN.md](IMPLEMENTATION_PLAN.md). Each phase still depends on its evidence gate; authorization does not convert an unproven seam into a GO.

**APPROVED:** Option A architecture; Hermes/Harmonia/Olympus authority boundaries; two-stage closure; final-state and cleanup rules; security requirements; staged recommendation.

**PROVISIONAL UNTIL PHASE 0:** concrete schemas, storage location, cryptographic library/protocol, adapter interfaces, and implementation paths.

**UNKNOWN/BLOCKED until Phase 0 evidence:** installed ACP/Hermes extension compatibility for identity propagation and tool-bound enforcement; SQLite/store feasibility for required transaction/integrity semantics; exact Olympus hook/adapter insertion points; approved key-management boundary; measurable provider/runtime identity attributes.

**Authorized now:** isolated Phase 0 proofs, default-off source/tests/docs, Daimon work, local verification, and atomic commits. **Still blocked:** Cotal/NATS/JetStream installation, live gateway/runtime changes, credential repair, real E0–E4 effects, production migration, merge, tag, and release publication.
