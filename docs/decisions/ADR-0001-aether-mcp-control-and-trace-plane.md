# ADR-0001: Aether MCP control and trace plane

- **Status:** APPROVED; ADAPTIVE PROVIDER AMENDMENT ACTIVE
- **Date:** 2026-08-06
- **Owner:** Christopher (DarkArty07)
- **Partially supersedes:** PDR-0012 section 6's demand-driven-adapter condition and the v0.22.0 CLI-first/no-Aether-MCP roadmap assumption
- **Preserves:** PDR-0012's Hermes–Orca ownership boundary, retirement of Olympus and the disconnected native core, no hidden fallback, no duplicated Orca operational state, and separate activation/release gates
- **Refined by:** Detailed contracts under `../architecture/AETHER_MCP.md`, `../reference/`, and `../releases/v0.22.0/M1_4_R1_ADAPTER_DECISION.md`
- **Implementation boundary:** bounded R0-R6 redesign/qualification closed with the provider product gate blocked; no MCP registration, model-backed worker, Release, or activation

## Context

The first v0.22.0 design proposed that Hermes control Orca directly through its
version-matched CLI and JSON output. The product owner rejected CLI-first as the
Aether product boundary.

Direct CLI control can operate Orca, but it does not by itself give Aether one
stable interface that explains:

- what happened;
- who initiated it;
- why it was chosen;
- when it occurred;
- which contract, use case, Task, and Dispatch it served;
- which authority permitted it;
- what effect and result were observed;
- which artifacts and evidence support the conclusion.

The product owner requires an Aether-owned MCP that condenses the Orca
orchestration surface for Hermes and preserves data suitable for system
evaluation, learning, refinement and future fine-tuning. Auditability is useful
but secondary. The concrete catalog is accepted and frozen in
`../releases/v0.22.0/USE_CASE_CATALOG.md`; implementation remains package-by-
package gated.

## Decision

### 1. Aether is MCP-first for swarm control

The target control topology is:

```text
User
  -> Hermes product contract and semantic decisions
  -> Aether MCP typed control and trace plane
  -> Orca version-matched public structured interface
  -> Orca Run / Task / Dispatch / worker / message / terminal / worktree mechanics
```

Hermes uses the Aether MCP as its exclusive normal swarm-control interface.
Hermes does not construct free-form Orca shell commands and does not depend on a
static tool for every Orca command.

The public Orca CLI or a later official structured Orca API remains an internal
provider seam below the MCP. This is not CLI-first product architecture: the
Aether MCP contract is stable for Hermes while the admitted Orca provider driver
is replaceable and version-pinned.

### 2. One MCP server exposes a bounded operational surface

The Aether MCP exposes:

1. **Project identity operations** to admit and freshly inspect one exact
   project/repository/worktree/profile binding before swarm work.
2. **Product operations** for normal Hermes supervision: validate, start,
   dispatch, inspect, communicate, reconcile, retry, cancel, close, and use typed
   trace actions to query or append bounded decisions/evidence.
3. **Dynamic Orca operations** for admitted coverage and diagnosis: search the
   pinned catalog, describe an operation, and call one described operation.

The operational contract contains exactly 15 designed tools. Independent batching
and eventual observation are internal adapter capabilities, not separate Hermes
tools. `project_forget` belongs to a future owner/admin boundary. Learning capture,
label, dataset, and export operations belong to a separate default-off learning
boundary and later M7 gate.

The dynamic surface avoids injecting one static MCP tool per Orca command. It
accepts command identifiers and structured arguments, never free-form shell
strings, and cannot bypass the higher-level authority/effect policy.

### 3. Orca remains the only operational source of truth

Orca exclusively owns mutable operational state for:

- Runs, Tasks, dependencies, and Dispatch attempts;
- workers, terminals, worktrees, and process lifecycle;
- operational messages, questions, replies, recovery, and cleanup state.

The Aether MCP may cache a bounded projection for query performance, but a cache
is never authoritative and must identify its source and freshness. The MCP must
query or reconcile with Orca before making a current-state claim.

### 4. Aether owns semantic trace and protected learning episodes

The MCP owns an append-only product trace containing only facts that Orca does
not own as product meaning:

- contract and use-case references;
- participant/admission and scope decisions;
- concise declared rationale;
- authorization references;
- Aether-to-Orca identity correlation;
- requested operation and structured receipt;
- result classification, including unknown;
- artifact/evidence references and verification outcomes;
- semantic acceptance/rejection and cleanup reconciliation;
- measurement facts and coverage.

The compact semantic trace is not enough for learning. Under an admitted
`FULL_EPISODE` policy, Aether also stores separately protected, replayable,
secret-redacted content: model-visible context/messages, tool schemas/calls/
results, worker handoffs, responses, artifact changes, corrections and outcome
labels. Content bodies are referenced by project-scoped digest from the event
trace rather than duplicated into it.

Neither layer is a second Run/Task/message scheduler. It cannot dispatch work
without invoking Orca and cannot convert its own projection into operational
truth.

### 5. Every consequential mutation is explainable

Every state-changing MCP call requires:

- a caller-supplied idempotency/operation identifier;
- a server-admitted project identifier, except the initial project admission
  that generates it;
- a structured reason code;
- a concise human-readable reason summary;
- the governing authority or contract reference;
- the expected effect class;
- the affected project/run/task/dispatch identity where applicable.

The server supplies the authoritative event identifier, UTC timestamp, sequence,
and integrity fields. It records request and receipt separately so a timeout or
ambiguous delivery remains `UNKNOWN` until reconciled.

The semantic event projection stores declared rationale rather than content
bodies. The protected episode store may preserve full secret-redacted content
that was visible to participants. It never requests or stores hidden
chain-of-thought, credentials, secret environment values or unbounded provider/
terminal debug payloads.

### 6. Hermes has the full control surface; workers do not

Only the primary admitted Hermes coordinator receives the complete Aether MCP
control surface. A worker cannot obtain full Orca control merely because Hermes
has it.

Workers use the substrate's bounded injected/reporting capabilities or a future
separately designed worker-only surface. A worker must not choose another
project, create Tasks, start workers, inspect foreign work, alter participant
policy, authorize protected effects, or close another Dispatch.

### 7. The MCP is deterministic infrastructure

The MCP does not perform semantic planning or hidden model arbitration. Hermes
creates the product contract and Task DAG. The MCP validates, compiles, invokes,
correlates, records, queries, and reconciles.

MCP server-initiated LLM sampling is disabled for this server. No hidden LLM
coordinator loop or fallback runtime is permitted.

### 8. Runs pin their Orca provider contract

Every admitted Run records the exact Orca executable/artifact identity, version,
digest, public operation catalog/schema, and provider-driver version. A material
schema mismatch blocks mutation rather than silently changing behavior during a
Run.

The MCP uses version-matched public contracts only. Private Orca databases,
undocumented IPC, UI automation, and terminal-output scraping are not accepted
control seams.

### 8.1 Provider delivery, guarantee, and qualification are separate

The adaptive boundary classifies every required capability by three independent
fields:

- delivery: `NATIVE`, `COMPOSED`, `AETHER_OWNED`, `DEFERRED`, or `UNSUPPORTED`;
- guarantee: `FULL` or `DEGRADED`;
- qualification: `PROVEN`, `UNQUALIFIED`, or `UNKNOWN`.

A public Orca command is native delivery even when its result/effect/timeout/
recovery schema must be version-pinned by Aether. A composed operation is never
provider-native. A degraded design is not proven merely because its limitation is
documented.

Orca 1.4.167's missing event, inventory, cleanup, Run cancel/close, and Task
cancel aggregates are adapted only as declared in
`../releases/v0.22.0/M1_4_R1_ADAPTER_DECISION.md`. Every composition remains
unavailable until its exact fixture passes. Debt and removal conditions are
canonical in `../releases/v0.22.0/ORCA_ADAPTER_DEBT.md`.

### 9. Use cases are bound to traceable measurement contracts

The concrete v0.22.0 cases are accepted and frozen in
`../releases/v0.22.0/USE_CASE_CATALOG.md`. The MCP contract includes optional
`use_case_id`, variant, baseline, hypothesis, and measurement references from its
first version.

When a Run is an evaluation Run, those fields are mandatory and immutable.
Unknown cost, token, timing, evidence, or attribution values remain unknown;
they are never converted to zero or inferred from another entity.

### 10. Initial deployment is local and non-networked

The initial target is a local stdio MCP server launched by the exact Hermes
profile. It opens no HTTP/LAN listener, receives only an allowlisted environment,
and stores no provider credentials. Runtime activation and profile registration
remain later gates.

## Rationale

The MCP is justified by an observed product requirement rather than integration
aesthetics: Aether must make swarm behavior understandable and measurable while
shielding Hermes from a large changing Orca command surface.

A stable product API plus semantic events and replayable learning episodes lets
Aether preserve its identity, evidence and improvement model without rebuilding
the commodity runtime Orca already provides. A compact dynamic low-level surface
retains full diagnostic coverage without multiplying tools or accepting
arbitrary shell execution.

## Alternatives considered

### Direct CLI-first control

Rejected by the product owner. It exposes the substrate contract directly to
Hermes and lacks one Aether-owned semantic trace and measurement boundary.

### One static MCP tool for every Orca command

Rejected. It creates a large, high-churn tool surface, increases prompt cost, and
duplicates Orca's versioned catalog.

### One unrestricted `execute` mega-tool

Rejected. A free-form command or shell-string tool weakens schemas, permissions,
effect classification, compatibility checks, and auditability.

### Stateless MCP facade

Rejected. It can simplify invocation but cannot preserve durable why/when
traceability after operational cleanup or support controlled use-case
measurement.

### A second Aether orchestration runtime

Rejected. Recreating Run/Task/message/recovery state would rebuild Olympus under
a new boundary and create conflicting authority with Orca.

## Consequences

### Positive

- Hermes receives one stable Aether-native swarm interface.
- Every consequential action can be reconstructed by contract, reason, time,
  actor, effect, result, and evidence.
- Full authorized episodes can support qualitative evaluation, correction
  mining, prompt/policy/skill improvement, routing and future fine-tuning.
- Orca remains replaceable beneath a versioned provider adapter.
- Traceable use-case evaluation becomes a first-class capability.
- Tool count remains bounded while complete Orca coverage stays available.
- Product meaning, operational mechanics, evidence, and acceptance remain
  distinct.

### Negative

- Aether intentionally regains a bounded executable component after retiring its
  disconnected native runtime.
- The project must maintain MCP schemas, provider compatibility, trace
  migrations, privacy, idempotency, and recovery behavior.
- Trace and Orca can diverge unless reconciliation and source attribution are
  enforced.
- Persistent rich episode data creates material retention, encryption,
  consent, intellectual-property, lineage, deletion and disclosure obligations.

## Validation or review gate

The design gate requires:

1. one explicit authority owner for every datum;
2. exact MCP tool and envelope schemas;
3. no free-form shell execution;
4. operation idempotency and ambiguous-delivery reconciliation;
5. version-pinned Orca catalog handling;
6. append-only semantic trace plus encrypted, project-isolated rich episodes,
   privacy exclusions and integrity checks;
7. deterministic project/workspace/run/task/dispatch correlation;
8. separate semantic, operational, evidence, and acceptance states;
9. a final traceable use-case catalog with frozen metrics and thresholds;
10. episode completeness, redaction, label authority, lineage, contamination,
    revocation and export boundaries;
11. executable negative tests planned for forged identity, stale Dispatch,
    foreign project, forbidden participant, schema drift, duplicate operation,
    partial batch, crash recovery, secret disclosure, and incomplete cleanup.

## Implementation authorization

The product owner accepted the detailed MCP-first design, contracts, measurement
model, use-case catalog and roadmap on 2026-08-06. The exact acceptance and
stepwise external-agent workflow are recorded in
`../releases/v0.22.0/M0_DESIGN_ACCEPTANCE.md`.

The owner selected the adaptive provider path on 2026-08-08 and authorized the
ordered R0-R6 task in
`../external-agent/TASK-ORCA-ADAPTER-REDESIGN.md`. The task closes with the
default-off contract and restricted adapter/journal/reconciler foundation
implemented, the two-worker slice blocked/not executed, and zero tools activated.
Any coordinator-admission qualification now requires a separate owner decision.

## References

- Hermes–Orca ownership boundary: `PDR-0012-hermes-orca-swarm-boundary.md`
- Swarm roster: `PDR-0013-swarm-roster-and-personality-model.md`
- MCP architecture: `../architecture/AETHER_MCP.md`
- Swarm operating model: `../architecture/ORCHESTRATION.md`
- MCP tool contract: `../reference/AETHER_MCP_CONTRACT.md`
- Trace schema: `../reference/AETHER_TRACE_SCHEMA.md`
- Learning episode/dataset schema: `../reference/AETHER_LEARNING_EPISODE_SCHEMA.md`
- Measurement contract: `../releases/v0.22.0/MEASUREMENT_CONTRACT.md`
- Use-case catalog: `../releases/v0.22.0/USE_CASE_CATALOG.md`
- v0.22.0 roadmap: `../releases/v0.22.0/ROADMAP.md`
- M0 acceptance: `../releases/v0.22.0/M0_DESIGN_ACCEPTANCE.md`
- Adaptive provider decision: `../releases/v0.22.0/M1_4_R1_ADAPTER_DECISION.md`
- Adapter debt ledger: `../releases/v0.22.0/ORCA_ADAPTER_DEBT.md`
