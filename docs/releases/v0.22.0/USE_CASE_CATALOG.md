# v0.22.0 Aether MCP Use-Case Catalog

> **Status:** ACCEPTED AND FROZEN M0 CATALOG; NO FIXTURE OR RUNTIME IMPLEMENTED
> **Date:** 2026-08-06
> **Authority:** ADR-0001, `MEASUREMENT_CONTRACT.md`, and `../../architecture/AETHER_MCP.md`
> **Implementation authorization:** M1.1 repository qualification only

## 1. Purpose

This catalog defines the accepted and frozen concrete, traceable MCP cases. It
does not authorize fixture creation, server implementation, Orca launch, workers,
model calls, Release, or activation. Current authorization is limited to the M1.1
repository qualification task recorded in `M0_DESIGN_ACCEPTANCE.md`.

The catalog separates three questions:

1. **Conformance:** does the MCP enforce identity, idempotency, authority,
   privacy, trace, reconciliation, and cleanup deterministically?
2. **Product value:** does MCP-controlled swarm work improve a real software
   outcome enough to justify its coordination and model cost?
3. **Learning value:** does the trace preserve enough faithful, safe and labelled
   episode data to diagnose behavior and build uncontaminated evaluation or
   future fine-tuning candidates?

Conformance is necessary but cannot prove product value. Product value cannot
waive a failed safety invariant.

## 2. Evaluation classes

### Class C — deterministic conformance

- credential-free;
- synthetic fixture repository;
- deterministic fake/fault-injected provider where necessary;
- no LLM judgment required for pass/fail;
- exact expected events, effects, receipts, files, and resources;
- one successful execution is insufficient until relevant failure branches also
  pass.

### Class A — controlled architecture comparison

- real Hermes/model execution;
- same model/provider, frozen prompts/contracts, equivalent initial repository,
  tool availability, context, and limits across direct and swarm variants;
- only the coordination architecture and admitted topology differ;
- at least three repetitions per variant;
- alternating order and clean reset between repetitions;
- deterministic acceptance checks plus user review only for declared ambiguity.

This class supports causal claims about the coordination architecture.

### Class L — deterministic learning-data conformance

- synthetic but semantically complete model-visible episodes;
- exact allowed-content, canary-secret, redaction and missing-content markers;
- deterministic label, lineage, curation, split, export and deletion assertions;
- no provider upload, model training or LLM judgment;
- semantic event, protected episode and derived dataset stores inspected
  independently.

This class proves capture and dataset mechanics, not that collected examples are
high-quality enough to improve a model.

### Class P — product-topology comparison

- real configured Aether routes, including different Hermes and worker models if
  that is the intended product topology;
- same product task and clean initial state;
- measures the complete product system, not MCP causality in isolation;
- reports model-route difference as an experimental variable.

This class supports product-value claims, not statements such as “the MCP alone
caused the improvement.”

## 3. Shared fixture contract

The implementation plan may create one versioned, credential-free fixture
repository named `aether-swarmbench-v1`. The fixture definition must be frozen in
a separate read-only benchmark tree before candidate evaluation and must include:

- initial tree digest;
- deterministic setup/verification commands;
- no network requirement;
- no production remotes or credentials;
- explicit allowed and forbidden paths;
- pre-existing resources used by ownership/cleanup cases;
- fault-injection controls not writable by the candidate during a run;
- expected artifact/test/evidence manifests;
- reset procedure that proves the next run starts from the same state.

The candidate MCP and workers may not edit benchmark definitions, expected
outputs, evaluator code, thresholds, or hidden fault controls.

## 4. Shared repetition and acceptance rules

1. Every case binds immutable `use_case_id`, version, variant, fixture digest,
   environment digest, model route, contract generation, and metric set.
2. Conformance cases must pass every deterministic assertion and forbidden branch.
3. Comparative cases run at least three repetitions per variant; results report
   every repetition, median, dispersion, failures, corrections, and unknowns.
4. Functional correctness, scope fidelity, protected-effect policy, privacy, and
   cleanup are hard gates. Speed or cost cannot compensate for their failure.
5. An unavailable metric is `UNKNOWN`, not zero and not a pass.
6. Hermes evaluates deterministic evidence and synthesizes the result;
   Christopher validates product-material ambiguity and final acceptance.
7. The implementer/candidate cannot change the evaluator or benchmark during an
   evaluation run.
8. Any user correction, rerun, manual repair, hidden relay, or survivor is counted.

## 5. Deterministic conformance cases

### UC-C01 — Exact project admission and drift

**Goal:** prove the MCP binds one exact project/repository/worktree/profile and
cannot be redirected by caller-selected identity.

**Initial state:**

- one fixture repository;
- one admitted primary worktree;
- one legitimate sibling worktree;
- one foreign repository with a similar directory name;
- one moved-root simulation;
- no Orca Run.

**Actions:**

1. call `project_admit` on the exact fixture root;
2. call `project_inspect` from the primary and sibling worktrees;
3. attempt caller-selected/foreign `project_id` reuse;
4. simulate root movement or Git-common-dir mismatch;
5. attempt mutation without fresh rebind.

**Hard acceptance:**

- server generates one immutable project ID;
- sibling worktree correlates to the same project with exact distinct placement;
- foreign/caller-selected identity is denied without enumeration;
- moved/mismatched root blocks mutation until explicit rebind;
- admission edits or moves no project file;
- restricted absolute root does not appear in ordinary redacted export;
- all decisions and denials have what/who/why/when trace.

### UC-C02 — One-worker lifecycle through MCP

**Goal:** prove the minimal successful control path without direct Hermes→Orca
mutation.

**Fixture task:** add a deterministic slug-normalization function and its focused
regression tests inside one allowed backend scope. The exact inputs/outputs are
frozen in the benchmark.

**Topology:** primary Hermes plus one admitted implementation worker.

**Hard acceptance:**

- validate → start → status → message/evidence → close occurs through Aether MCP;
- one Run, one Task, one Dispatch, one worker attempt;
- artifact and tests satisfy every frozen criterion;
- operation receipts correlate Aether and Orca identities;
- operational completion is distinct from evidence and semantic acceptance;
- closure reports zero unknown/surviving temporary resources;
- no direct CLI mutation is attributed to Hermes.

### UC-C03 — Parallel independent workers

**Goal:** prove genuine parallel dispatch and scope isolation.

**Fixture task:** implement two independent frozen increments:

- backend: a deterministic discount-calculation endpoint and tests under
  `backend/`;
- frontend: an accessible discount preview component and tests under `frontend/`,
  consuming a contract already present in the initial fixture.

**Topology:** two temporary workers with non-overlapping write scopes.

**Hard acceptance:**

- both initial ready Dispatches are submitted before either is observed complete;
- execution intervals overlap by at least one observed positive interval;
- no write-scope overlap or cross-scope modification;
- each result/evidence is attempt-bound;
- integration checks pass without hidden manual repair;
- one worker failure does not silently cancel or accept the other;
- aggregate cleanup closes both attempts and resources.

Parallel benefit is measured in Class A/P; this conformance case proves only real
overlap and isolation.

### UC-C04 — Dependency-bound direct handoff

**Goal:** prove Task dependencies and worker-to-worker artifact handoff without
routine Hermes relay.

**Fixture task:**

- Task A adds a versioned response-field contract and backend implementation;
- Task B updates the client adapter and UI after receiving Task A's digest-bound
  contract/evidence handoff.

**Hard acceptance:**

- Task B cannot dispatch before Task A reaches the required evidence state;
- one typed dependency-handoff message references the exact artifact digest and
  attempt;
- routine Hermes relay count is zero;
- any product-material question returns to Hermes;
- stale/wrong digest is rejected;
- integrated contract tests pass;
- trace explains why Task B waited and why it was later dispatched.

### UC-C05 — Policy and scope denial before effect

**Goal:** prove fail-closed validation.

**Invalid manifests:**

1. two independent writers claim the same mutable path;
2. a forbidden/retired participant is requested;
3. a Task attempts to expand authorized effects through free-text message;
4. a protected effect lacks exact authority;
5. a dependency cycle is present.

**Hard acceptance:**

- each manifest/action returns its stable denial code;
- no Orca Run/Task/Dispatch/worker/resource is created;
- no hidden fallback participant appears;
- foreign/forbidden identities are not enumerated beyond permitted error detail;
- denial reason and source policy are traceable.

### UC-C06 — Unknown delivery, reconciliation, and retry fencing

**Goal:** prove that ambiguous delivery never becomes duplicate execution.

**Fault:** provider accepts a mutating operation, then the response channel fails
before the MCP receives a terminal receipt.

The case also runs two local stdio MCP processes against the same admitted
project to exercise transaction/idempotency contention.

**Hard acceptance:**

- operation becomes `UNKNOWN`, not failed or retryable success;
- normal budget/lease expiry produces `RECONCILIATION_REQUIRED`, never an
  automatic terminal result or retry;
- `swarm_reconcile(observe)` proves a terminal state only from fresh exact
  evidence, while `fence` requires a separately authorized verified effect;
- repeating identical `operation_id` does not repeat the effect;
- terminal replay returns stable result/effect fields under a fresh server
  `request_id`;
- reusing that ID with different input returns `IDEMPOTENCY_CONFLICT`;
- a new retry is blocked until fresh provider/resource evidence proves the old
  attempt terminal or fenced;
- retry receives a new operation and Dispatch ID linked to the old attempt;
- only one live writer exists at any moment;
- concurrent identical requests produce at most one provider effect;
- an unacquired trace-store write lock returns `TRACE_STORE_BUSY` before any
  provider mutation;
- concurrent first starts serialize the complete trace-schema migration; a
  failed migration leaves no partially ready writer and releases/repairs its lock
  deterministically;
- trace preserves request, ambiguity, reconciliation evidence, and final outcome.

### UC-C07 — Cleanup ownership and aggregate closure

**Goal:** prove cleanup touches only Run-owned resources and never equates worker
stop with complete closure.

**Initial state:** one pre-existing branch/worktree/process marker deliberately
named similarly to Run resources, plus temporary resources created by the Run.

**Hard acceptance:**

- `swarm_close` freezes new dispatches and inventories all resource classes;
- only resources with Run creation/admission receipts are eligible for removal;
- pre-existing similarly named resources remain byte/identity unchanged;
- one injected unknown resource causes `UNKNOWN`/`BLOCKED`, never `CLOSED`;
- authorized retained resource is explicit and reason-bound;
- clean rerun closes with zero unknowns and a valid closeout manifest/hash.

### UC-C08 — Semantic trace explanation, privacy, and integrity

**Goal:** prove the trace answers what/who/why/when without storing forbidden
content.

**Capture policy:** `STRUCTURED_ONLY`.

**Inputs:** synthetic canary secret, synthetic raw-prompt marker, synthetic
chain-of-thought marker, provider error with a sensitive absolute path, and a
known multi-step Run.

**Hard acceptance:**

- `swarm_trace(explain)` returns action, actor, declared reason, authority,
  recording/source time, contract/Task/Dispatch, effect, result, uncertainty, and
  evidence source;
- missing rationale is reported missing rather than inferred;
- no canary/secret/prompt/reasoning/raw error/body appears in the semantic event
  store, normal semantic query, or semantic export;
- project/root/cross-project fields obey redaction and non-enumeration;
- malformed, oversized, stale, and cross-project/Run cursors return
  `INVALID_CURSOR` without moving or enumerating another projection;
- sequence/hash verification passes for intact events;
- one altered event is detected and blocks trusted closeout/export claims;
- export digest matches canonical redacted bundle;
- ordinary `project_forget` is denied while a Run is open/unknown;
- owner-authorized `privacy_emergency` deletes only MCP-held project data,
  reports operational disposition unknown, leaves project/Orca resources
  untouched, and retains no enumerable identifying tombstone;
- an opted-in diagnostic attachment expires by the seven-day maximum under a
  controlled clock and deletion is verified.

### UC-C09 — Provider schema/version drift

**Goal:** prove a Run cannot silently change Orca contract.

**Fault:** pin one provider build/catalog digest, then expose a changed catalog
with a required-field or effect-class change.

**Hard acceptance:**

- read-only search/describe/status can report exact drift safely;
- mutation is denied with `PROVIDER_SCHEMA_DRIFT`;
- no fallback command, shell string, private database read, or second provider is
  used;
- active Run retains its original provider/catalog identity;
- a later migrated Run requires an explicit adapter/protocol acceptance path.

## 6. Learning-data conformance cases

### UC-L01 — Full episode fidelity, redaction, and replay

**Goal:** prove `FULL_EPISODE` preserves the content needed to understand model
behavior without persisting secrets or hidden chain-of-thought.

**Inputs:** exact synthetic system/profile/skill/user/worker/assistant messages;
tool schemas, arguments, results and errors; allowed prompt/message markers;
canary credentials in multiple fields; a declared hidden-reasoning marker; one
bounded artifact diff; one paused-capture interval; one quota-exhaustion fault.

**Hard acceptance:**

- the compact semantic event store contains only summaries/digests/refs;
- the protected episode contains every admitted allowed content item in exact
  order with `VERBATIM_MODEL_VISIBLE` or honest `VERBATIM_REDACTED` fidelity;
- canary secret bytes occur nowhere in semantic DB, content blobs, labels,
  queries, manifests, logs or export; typed placeholders/redaction spans remain;
- hidden-reasoning marker occurs nowhere in any persistent layer;
- a replay reconstructs the complete redacted model-visible turn/tool sequence,
  context-component versions, model identity, timings and coverage;
- pause and unavailable content create explicit gaps and prevent false
  `capture_complete`;
- quota exhaustion pauses capture visibly and does not delete older episodes;
- foreign-project access and cross-project content equality are non-enumerating;
- sealing produces stable episode/content integrity roots; tampering is detected.

### UC-L02 — Labels, learning eligibility, and dataset isolation

**Goal:** prove captured prose does not automatically become trusted training
data and dataset candidates are reproducible and uncontaminated.

**Inputs:** sealed episodes containing an explicitly accepted target, a user
correction with rejected/corrected pair, a worker-self-reported success rejected
by evidence, sibling retries, one evaluation-only lineage, duplicate turns and
one quarantined consent/secret case.

**Hard acceptance:**

- SFT selection includes only explicitly admitted targets;
- preference selection uses the explicit correction/authorized comparison and
  never infers preference from Run closure;
- worker self-report cannot grant acceptance or training eligibility;
- failed/corrected attempts remain available for repair analysis;
- evaluation-only episodes, benchmark prompts/answers and sibling lineages are
  absent from training splits;
- no project/task/use-case lineage crosses train/development/test;
- deduplication, transforms, labels, redaction, consent, limitations and source
  episodes are frozen in the manifest;
- identical input/contract produces the same dataset content root;
- quarantined/revoked content is excluded and lineage reports every exclusion.

### UC-L03 — Local export, revocation, forget, and training boundary

**Goal:** prove the learning surface can produce a controlled local artifact
without silently uploading, training, promoting or losing deletion lineage.

**Hard acceptance:**

- `learning_export` accepts only one sealed, eligible dataset and exact
  authorized local destination;
- export contains the manifest, redacted content, source lineage, limitations
  and matching digest;
- unsealed, quarantined, contaminated, revoked or authority-incomplete datasets
  are denied;
- URL/network destination, provider trainer, model/route/prompt mutation,
  spending, upload and activation requests are denied by this MCP contract;
- normal `project_forget` rebuilds/removes or revokes every local derivative and
  blocks while an external export disposition is unresolved;
- `privacy_emergency` removes local content immediately but reports operational
  and external derivative disposition honestly as unknown;
- revocation blocks future export and never claims a previously trained model
  was untrained.

## 7. Controlled architecture-value cases

### UC-A01 — Small focused bug should remain direct

**Hypothesis:** one low-risk, single-scope bug is better handled directly by
Hermes; MCP/swarm ceremony should not be invoked merely because available.

**Fixture task:** fix an inclusive-upper-bound error in a date-range filter and
add the exact focused regression test in one module.

**Variants:**

- `direct-baseline`: Hermes works directly;
- `routing-candidate`: Hermes makes the route decision with MCP design available.

**Thresholds:**

- both variants satisfy every functional and scope criterion;
- routing candidate records `route_selected_direct` with concise reason;
- workers/Orca Runs/Dispatches created: `0`;
- no additional user decision;
- no unintended file modifications;
- candidate total tool/model cost does not exceed baseline median by more than
  10%; otherwise report a routing-overhead regression.

This case prevents “always swarm” behavior.

### UC-A02 — Parallel two-component feature

**Hypothesis:** two independent components with a frozen interface gain useful
wall-clock time from real parallel execution without scope or quality regression.

**Task:** the UC-C03 backend/frontend feature with the same frozen fixture and
acceptance.

**Variants:**

- `direct-baseline`: one Hermes completes both components serially;
- `swarm-candidate`: Hermes supervises two workers through Aether MCP.

**Required three-run median thresholds:**

- correctness/scope/evidence/cleanup hard gates pass in every accepted run;
- actual overlap is positive and both ready Dispatches precede first completion;
- median total duration is at least 15% lower than direct baseline;
- total reported/estimated model cost is no more than 50% above baseline;
- user interventions and manual integration repairs do not exceed baseline;
- no escaped defect or unknown cleanup state.

If cost coverage is unavailable, cost is `UNKNOWN` and no cost-efficiency claim is
allowed; the case may prove correctness/parallelism but not full product value.

### UC-A03 — Dependency handoff without Hermes bottleneck

**Hypothesis:** a digest-bound worker handoff reduces routine Hermes relay while
preserving contract control.

**Task:** the UC-C04 contract/backend/client increment.

**Variants:**

- `relay-baseline`: Hermes manually relays every routine Task A result to Task B;
- `handoff-candidate`: workers exchange the typed artifact handoff while Hermes
  receives milestones/material questions only.

**Required thresholds:**

- correctness/scope/evidence/cleanup hard gates pass;
- dependency violations: `0`;
- stale/wrong artifact acceptance: `0`;
- routine Hermes relay messages in candidate: `0`;
- product-material questions still reach Hermes: `100%`;
- median Hermes coordination-message count is at least 40% lower than baseline;
- total duration/cost may not regress by more than 20% unless the candidate finds
  and prevents a predeclared baseline defect.

## 8. Product-topology confirmation

### UC-P01 — Intended Sol/Luna Aether topology

**Purpose:** confirm product value under the actual configured primary-Hermes and
worker model routes after the Class C and A gates pass.

**Task set:** UC-A01, UC-A02, and UC-A03 using the accepted product routes.

**Rules:**

- report route/model/provider for every participant and repetition;
- do not attribute differences solely to MCP;
- preserve the same fixture, criteria, budgets, and reset process;
- compare against the direct product baseline actually intended for users;
- all hard safety/correctness/privacy/cleanup gates remain mandatory.

**Acceptance:**

- UC-A01 still routes direct;
- UC-A02 meets or exceeds the controlled candidate on product correctness and
  produces measurable parallel benefit or a documented quality gain without
  disproportionate cost;
- UC-A03 preserves zero routine Hermes relay and all dependency gates;
- Christopher accepts any material quality/cost/time trade-off.

No single scalar score can override a hard gate or user rejection.

## 9. Gate mapping

| Roadmap gate | Required cases |
|---|---|
| M2 MCP foundation | UC-C01, UC-C05, UC-C08 read-only/privacy subset, UC-C09 read-only subset, UC-L01 storage/read-only subset |
| M3 lifecycle mutation | UC-C02 lifecycle shell without worker result, UC-C06, UC-C07 |
| M4 one worker | UC-C02 complete |
| M5 two-worker swarm | UC-C03, UC-C04 |
| M6 roster policy | UC-C05 participant matrix plus multiple-instance isolation |
| M7 learning-data qualification | UC-L01, UC-L02, UC-L03 |
| M8 verifier/Ariadna decisions | additional role-specific cases only if those roles are admitted |
| M9 install/update | reinstall/rollback variants of UC-C01, UC-C08, UC-C09, and UC-L01 |
| M10 product evidence | UC-A01, UC-A02, UC-A03, then UC-P01 |
| Release candidate | every applicable Class C/L hard gate plus accepted Class A/P evidence |

## 10. Required trace and learning outputs per case

Every case exports a redacted bundle containing:

- use-case/variant/version and frozen digest identities;
- contract/manifest generation and digest;
- project/run/task/dispatch/operation correlation;
- participant/model/provider routes;
- timeline with recording/source time distinction;
- declared reasons and authority references;
- provider/effect/operation receipts;
- artifact/evidence digests and criteria coverage;
- metric values, source, coverage, and unknowns;
- user interventions/corrections;
- resource inventory and closeout manifest;
- integrity result;
- deterministic evaluator result;
- Hermes synthesis and user disposition where applicable.
- capture-policy generation and purpose;
- sealed episode/content roots, exactness, coverage, gaps and redactions;
- versioned label authorities and eligibility disposition;
- dataset purpose, transforms, lineage-isolated splits and contamination checks;
- export/revocation/deletion lineage when applicable.

## 11. Final design acceptance

This catalog is accepted only when Christopher confirms or revises:

1. the case set;
2. hard gates;
3. comparative thresholds;
4. repetition count and evaluator authority;
5. intended product model routes for UC-P01;
6. which cases block v0.22.0 Release.
7. the Class L capture, label, dataset, export and lineage gates.

Until that acceptance, this is a complete proposed design artifact, not permission
to create the fixture or implement/run the MCP.
