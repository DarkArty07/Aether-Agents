# Aether Agents v0.22.0 MCP-First Swarm Roadmap

> **Status:** M0 FAST PATH ACCEPTED; M2.1a AUTHORIZED; M1.1b DEFERRED; NOT ACTIVATED
> **Date:** 2026-08-07
> **Owner:** Christopher (DarkArty07)
> **Current released baseline:** `v0.20.0`
> **Candidate workspace:** `feature/v0.22.0-orca-transition`
> **Governing decisions:** PDR-0012, PDR-0013, and ADR-0001
> **Implementation authorization:** M2.1a default-off zero-tool MCP bootstrap only; provider and runtime remain gated

## 1. Objective

Deliver a coherent Aether Agents v0.22.0 candidate in which Hermes can supervise
an Orca-backed swarm exclusively through one Aether-owned MCP control and trace
plane, with:

- a small stable Daimon roster;
- multiple Task-bound workers per admitted archetype when justified;
- actual parallel Tasks and bounded peer communication;
- exact project/profile/worktree isolation;
- durable what/who/why/when/effect/result/evidence traceability;
- full secret-redacted learning episodes and versioned dataset lineage for
  system refinement and future fine-tuning;
- measurable use cases frozen before implementation;
- rollback and zero-survivor cleanup;
- no restoration of Olympus, Harmonia, ACPManager, `talk_to`, or a duplicate
  orchestration runtime.

## 2. Current truth

- The historical Aether native coordination core is retired from the candidate.
- The current candidate has no accepted multi-agent execution runtime.
- Orca is not running for this design work.
- The Aether MCP package, tools, semantic/learning stores, config, and runtime do
  not exist.
- Hermes currently performs bounded work directly.
- PDR-0012 defines the Hermes–Orca ownership boundary.
- PDR-0013 defines the target roster and personality model.
- ADR-0001 approves MCP-first control and partially supersedes the prior
  CLI-first/no-Aether-MCP assumption.
- The concrete measurable use cases, thresholds and detailed MCP-first design
  were accepted and frozen by the product owner on 2026-08-06.

No target statement in this roadmap is a current-runtime claim.

## 3. Target topology

```text
User
  -> Hermes product contract, routing, supervision, synthesis
  -> Aether MCP v1alpha1
       -> typed product operations
       -> policy and contract validation
       -> version-pinned Orca provider adapter
       -> append-only semantic trace and operation receipts
       -> protected replayable learning episodes
       -> labels, dataset lineage, local curation/export boundary
       -> query, explanation, evidence, learning, and measurement projections
  -> Orca public structured interface
       -> Runs / Tasks / Dispatches / workers
       -> messages / questions / replies
       -> terminals / worktrees / recovery / cleanup
  -> artifacts, Git, tests, builds, rendered evidence
```

This topology is **MCP-first** for Hermes. The public Orca CLI may be used by the
provider adapter or isolated engineering qualification, but it is not the normal
Hermes product interface.

## 4. Authority boundaries

| Concern | Owner |
|---|---|
| Product meaning, material trade-offs, final acceptance | User |
| Requirements, contract, Task DAG, routing, integration, completion proposal | Hermes |
| MCP schemas, admission validation, idempotency, correlation, semantic trace, protected learning episodes/datasets | Aether MCP |
| Run/Task/Dispatch/worker/message/terminal/worktree/recovery/cleanup state | Orca |
| Specialist judgment inside one Task | Admitted worker archetype |
| Artifact bytes and repository lineage | Git/filesystem |
| Test/build/E2E outcome | Executed evidence |
| Technical acceptance | Hermes or admitted Independent Verifier |
| Release and activation | Separate explicit gates |

The Aether MCP may project Orca state but may not own a competing operational
truth. Orca activity or worker prose does not confer product authority.

## 5. Approved design direction

### 5.1 Aether MCP

The target MCP is one local stdio server for the primary Hermes coordinator. It
provides:

- high-level swarm operations;
- dynamic search/describe/call/batch/events access to the pinned Orca catalog;
- structured reasons and authority references for mutations;
- operation idempotency and ambiguous-delivery reconciliation;
- product-to-runtime identity correlation;
- append-only privacy-safe trace;
- protected secret-redacted model-visible episodes, labels and dataset lineage;
- evidence, closure, explanation, learning and measurement projections;
- local dataset export without upload, training or promotion.

The detailed design is canonical in:

- `../../architecture/AETHER_MCP.md`;
- `../../reference/AETHER_MCP_CONTRACT.md`;
- `../../reference/AETHER_TRACE_SCHEMA.md`;
- `../../reference/AETHER_LEARNING_EPISODE_SCHEMA.md`;
- `MEASUREMENT_CONTRACT.md`.

### 5.2 Stable archetypes, temporary workers

Target roster:

- **Hefesto:** sustained implementation and broad refactors;
- **Daedalus:** UX, interaction, product flow, and prototypes;
- **Ictinus:** backend architecture, data, and scalability consultation;
- **Ariadna:** conditional continuity specialist, disabled until evidence proves
  value beyond Hermes-native continuity;
- **Independent Verifier:** proposed acceptance role, not implemented or
  admitted until designed and benchmarked.

Athena and Etalides have target retirement/forbidden disposition. No new design
or workflow may depend on Etalides.

Multiple workers may be launched from one archetype when Tasks are independent
and have distinct write scopes. The archetype is stable; the worker instance is
Task-bound and temporary.

### 5.3 Direct work remains valid

Hermes works directly when one accountable owner is the shortest reliable path.
The swarm is used only when distinct specialist contribution or real independent
parallelism is expected to improve quality or time more than coordination cost.

## 6. Non-negotiable invariants

1. **MCP-first:** Hermes does not construct free-form Orca commands for normal
   swarm work.
2. **No arbitrary shell:** Aether MCP accepts typed identifiers and structured
   arguments only.
3. **One operational owner:** Orca owns mutable runtime state.
4. **Two-layer learning trace:** Aether owns a compact semantic event index plus
   authorized protected model-visible episodes, labels and dataset lineage—not a
   second scheduler or Orca state copy.
5. **No hidden coordinator:** MCP sampling and hidden LLM loops are disabled.
6. **Version pinning:** every Run pins Orca build, digest, catalog/schema, and
   adapter version.
7. **Idempotency:** every mutation has one operation ID; duplicate/different
   reuse is rejected.
8. **Unknown remains unknown:** a timeout after possible delivery is reconciled
   before retry.
9. **Project identity:** Run + exact project root/worktree + Aether home + profile
   identity must correlate before attribution.
10. **One writer per scope:** parallel writers require separate worktrees/scopes
    or explicit serialization.
11. **Participant policy:** required/allowed/disabled/forbidden applies to
    selection, retry, fallback, recovery, and peer proposals.
12. **Workers do not recurse:** workers cannot create Tasks, launch workers,
    change participant policy, or gain the coordinator MCP surface.
13. **Learning privacy:** admitted full episodes may preserve secret-redacted
    model-visible prompts/messages/tool trajectories; credentials, hidden
    chain-of-thought, unadmitted cross-project data and unbounded debug payloads
    are never persisted.
14. **Evidence is not acceptance:** tests and technical completion do not equal
    user acceptance.
15. **No legacy fallback:** Olympus, Harmonia, ACPManager, `talk_to`, and the
    retired native kernel cannot reappear by compatibility or failure recovery.
16. **Separate horizons:** design, implementation, integration, Release, and
    activation require distinct gates.

## 7. Scope

### Included in the v0.22.0 target

- Aether MCP `v1alpha1` design and bounded implementation;
- local stdio coordinator surface;
- Orca provider catalog/adapter through public structured contracts;
- semantic trace store and query/explain projections;
- protected rich-episode/content storage, labels, curation, dataset lineage and
  local-only export;
- manifest validation, participant policy, operation receipts, reconciliation;
- one-worker and two-worker executed workflows through the MCP;
- bounded worker communication and dependency handoff;
- retry, cancellation, restart, rollback, and cleanup evidence;
- target roster qualification;
- final traceable use-case catalog and controlled evaluation;
- product/config/install/upgrade/diagnostic/rollback integration;
- exact candidate acceptance, integration, GitHub Release, and later activation
  only after their own gates.

### Excluded

- direct CLI-first Hermes operation;
- arbitrary shell execution through MCP;
- a second Aether Run/Task/message/recovery database;
- restoration of retired coordination code;
- import of historical `.aether` runtime databases;
- hidden fallback to legacy paths;
- dynamic role/personality generation;
- recursive worker delegation;
- universal specialist participation;
- Athena or Etalides in the target runtime;
- unproven Ariadna or Independent Verifier as mandatory release dependencies;
- credentials, hidden chain-of-thought, unadmitted private/cross-project data or
  unbounded provider/terminal logs in any learning layer;
- automatic dataset eligibility, external upload, training, fine-tuning,
  prompt/model/route mutation or candidate promotion;
- distributed/remote MCP service in the first accepted implementation;
- activation, deployment, credentials, spending, migration, or publication before
  their explicit gates.

## 8. Design closure sequence

M0 closed on 2026-08-06 when the product owner accepted the detailed design and
frozen use-case catalog. M1.1a identity/catalog evidence is accepted as a bounded
fast-track prerequisite and the current horizon is read-only M1.2 seam mapping.
M1.1b remains a mandatory blocker before M1.3 lifecycle work.

### M0 — Final design and traceable use cases

**Outcome:** one accepted MCP-first architecture, exact control/semantic-trace/
learning-episode contract, and frozen use-case/evaluation package.

**Status:** accepted on 2026-08-06. Evidence: `M0_DESIGN_ACCEPTANCE.md`.

**Deliverables:**

- ADR-0001 approved direction;
- `../../architecture/AETHER_MCP.md`;
- `../../reference/AETHER_MCP_CONTRACT.md`;
- `../../reference/AETHER_TRACE_SCHEMA.md`;
- `../../reference/AETHER_LEARNING_EPISODE_SCHEMA.md`;
- `MEASUREMENT_CONTRACT.md`;
- `USE_CASE_CATALOG.md`;
- reconciled PDR, product, authority, orchestration, guide, roadmap, and status
  references;
- final use-case catalog with specified tasks/fixtures/variants and hard gates;
- baseline and model-equivalence policy;
- metrics, thresholds, evaluator, rich episode, labels, dataset lineage,
  privacy, evidence, and cleanup contracts;
- explicit separation between design acceptance and later implementation plan.

**Acceptance:**

- product owner accepted the detailed design on 2026-08-06;
- every datum has one authority owner;
- tool schemas contain no arbitrary command or duplicate runtime state;
- what/who/why/when/effect/result/evidence can be reconstructed;
- admitted full episodes can replay the secret-redacted model-visible context,
  messages, tools, corrections and outcomes needed for learning;
- retention/privacy and unknown-state behavior are explicit;
- use cases are measurable and frozen before code;
- no runtime, worker, config, or source mutation occurred during design.

**Stop condition:** approved design and cases. Implementation remains a later
horizon.

## 9. Implementation and qualification milestones

Each milestone requires the previous milestone's accepted evidence and a
separate implementation/operation authorization applicable to that step.

### M1 — Orca provider qualification

**Outcome:** exact public Orca provider contract qualified without workers.

Tasks:

1. resolve exact executable/build/version/digest with no fallback;
2. load version-matched public orchestration catalog/guides;
3. freeze structured schemas/effect classes needed by Aether MCP;
4. exercise cold start, status, restart, stop, rollback, and cleanup in an
   isolated Orca home/state root;
5. prove no production/global Orca state is touched;
6. capture structured evidence and zero survivors.

Direct CLI may be used only inside this isolated provider-qualification harness,
not as the Hermes product interface.

**Acceptance:** exact build/catalog known; public structured contracts sufficient
or specific missing seams documented; lifecycle rollback and zero survivors
proven.

### M2 — Aether MCP foundation

**Outcome:** local read/control foundation with no worker dispatch.

Deliverables:

- bounded MCP package and stdio entry point;
- coordinator principal/project binding;
- protocol envelopes and stable errors;
- manifest validation;
- provider catalog search/describe and read-only call/events;
- operation journal/idempotency;
- append-only semantic trace plus encrypted project-isolated episode/content
  store, migration, integrity, privacy, capture-policy and read/export
  foundations;
- source-labelled status/explanation projections;
- no ambient secrets or network listener.

**Acceptance:** contract RED/GREEN tests, two-project isolation, restart,
migration, privacy/secret-redaction scan, synthetic episode replay, invalid
identity/effect/schema/capture-policy rejection, and read-only provider parity
pass.

### M3 — Lifecycle through Aether MCP

**Outcome:** Run lifecycle controlled only through the MCP, still without a real
worker.

Exercise:

- validate/start/status/cancel/close;
- partial-start handling;
- duplicate operation replay and conflict;
- ambiguous delivery reconciliation;
- provider schema drift;
- MCP/provider crash and restart;
- rollback and aggregate cleanup.

**Acceptance:** every effect has one receipt; no duplicate Run/Task; unknowns
remain explicit; closure proves zero survivors.

### M4 — One synthetic worker

**Outcome:** one deterministic bounded worker completes one Task through MCP.

Exercise:

- exact profile/home/project/worktree binding;
- dispatch acceptance separated from worker completion;
- progress, question/reply, artifact, and evidence references;
- Hermes review and semantic completion proposal;
- cancellation and failed-attempt negative paths;
- cleanup and trace explanation;
- `FULL_EPISODE` capture of model-visible context, worker response, tool
  trajectory, correction/evidence and closeout labels.

**Acceptance:** deterministic artifact and expected evidence; exact correlation;
no authority escalation; semantic trace explains selection/lifecycle; sealed
episode is replayable with honest gaps/redactions; zero survivors.

### M5 — Two-worker real swarm

**Outcome:** actual independent parallelism and bounded handoff.

Exercise:

- two Tasks with separate scopes/worktrees;
- both Dispatches submitted before observation;
- measured overlap;
- peer question/reply or dependency handoff;
- one controlled failed attempt and new retry lineage;
- stale/late old-attempt rejection;
- integration and broader verification;
- aggregate close and cleanup.

**Acceptance:** real overlap, no conflicting writers, bounded communication, old
attempt fenced, integrated result passes, trace complete, zero survivors.

### M6 — Stable roster qualification

**Outcome:** Hefesto, Daedalus, and Ictinus operate as stable archetypes with
Task-bound instances and enforced participant policy.

Tasks:

- bind exact profile homes/models/toolsets;
- prove multiple instances from one archetype remain isolated;
- test required/allowed/disabled/forbidden policy;
- prove Athena/Etalides unavailable without fallback;
- prove unavailable participant handling is honest;
- reconcile tracked profile inventory only under explicit implementation scope.

**Acceptance:** each retained archetype demonstrates its distinct contribution;
policy is deterministic; no retired role can be selected directly or indirectly.

### M7 — Learning episode and dataset qualification

**Outcome:** rich trace data is replayable, privacy-safe and usable to construct
reproducible local evaluation/training candidates without automatic eligibility,
upload or training.

Exercise:

- exact secret-redacted model-visible context/message/tool/artifact capture;
- explicit gaps, quota failure, quarantine and immutable episode sealing;
- user correction, preference, failure, quality and eligibility label authority;
- SFT, preference, tool-policy, repair, routing and evaluation dataset manifests;
- project/task/use-case-lineage train/development/test isolation;
- benchmark contamination, duplicate, consent/license and revocation handling;
- local export, project forget and external-derivative unknown boundaries;
- rejection of upload, training, model/route/prompt mutation and promotion.

**Acceptance:** UC-L01, UC-L02 and UC-L03 pass; no secret or hidden
chain-of-thought persists; dataset builds are reproducible; revoked/evaluation
data cannot leak into training/export; no network/trainer effect exists.

### M8 — Independent Verifier and Ariadna decision

**Outcome:** evidence-based admit/retire decisions for the proposed verifier and
conditional continuity specialist.

- The Independent Verifier must have a distinct acceptance contract, read-only
  default scope, deterministic task ID/attempt budget, and benchmark value.
- Ariadna remains disabled until it demonstrates continuity value beyond Hermes
  native memory, skills, session history, and versioned project docs.

**Acceptance:** each role is admitted only if measurable benefit exceeds cost and
complexity. Failure to prove value results in explicit exclusion, not a hidden
release blocker unless the final M0 case catalog made that gate mandatory.

### M9 — Product, install, upgrade, diagnostics, rollback

**Outcome:** Aether MCP/Orca integration is an intentional user-facing product
capability, still default-off unless activation is separately accepted.

Deliverables:

- profile/config templates;
- local stdio launch policy and environment allowlist;
- install/upgrade/status/doctor/rollback behavior;
- data/trace migration and retention handling;
- exact compatibility matrix;
- operator and user documentation;
- clean-room first-use artifact;
- uninstall/rollback preserving user data and historical evidence.

**Acceptance:** clean-room installation and rollback work; exact version/build is
reported; no stale process/state/config; privacy and project isolation pass.

### M10 — Controlled use-case evaluation

**Outcome:** execute the M0-frozen case catalog against direct/general-agent
baselines and the MCP/swarm candidate.

Evidence includes:

- exact prompts and initial-state digests;
- candidate/model/provider/tool identities;
- full accepted semantic trace, sealed learning episode/content root, labels and
  dataset-lineage disposition;
- product, quality, time, coordination, cost, reliability, and cleanup metrics;
- failed attempts, corrections, unknowns, and user interventions;
- evaluator verdict and product-owner disposition.

**Acceptance:** every mandatory threshold passes. Missing evidence is not a pass.
The MCP/swarm must be non-inferior or superior according to the pre-frozen rule;
internal runtime correctness alone is insufficient.

### M11 — Exact candidate acceptance and Release

**Outcome:** one exact tree accepted and published as v0.22.0.

Required gates:

- clean candidate worktree;
- full repository suite and documentation checks;
- clean-environment install/upgrade/rollback;
- security/privacy/trace-integrity review proportional to consequence;
- no stale version claims or forbidden runtime path;
- exact SHA accepted;
- atomic English commits;
- integration through the approved Git/GitHub flow;
- tag and GitHub Release with rationale, alternatives, impact, evidence,
  compatibility, and rollback.

Release publishes source/product artifacts. It does not automatically activate a
local persistent swarm.

### M12 — Persistent activation

**Outcome:** explicit local operational enablement only after Release.

Requires separate authority for:

- MCP profile registration;
- persistent semantic/learning trace collection, encryption, retention, quota,
  curation and deletion policy;
- Orca startup or service behavior;
- live participant policy;
- monitoring and operator rollback.

**Acceptance:** live E2E, health/status, restart, privacy, project isolation,
cleanup, rollback, and user-facing behavior all pass. Activation is never implied
by implementation, merge, tag, or Release.

## 10. Detailed execution roadmap

> **Planning boundary:** This section is not evidence of existing files or
> behavior. `M0_DESIGN_ACCEPTANCE.md` authorizes M1.1 only. Every later package
> remains a future instruction until the preceding package is independently
> accepted and its exact scope is authorized.

### 10.1 Delivery model

v0.22.0 is one product candidate, not a sequence of public patch releases. The
milestones below are internal, independently verifiable work packages on the
`feature/v0.22.0-orca-transition` candidate. Do not create intermediate public
SemVer tags merely to mark progress.

The release critical path is:

```text
M0 owner acceptance
  -> M1 exact Orca qualification
  -> M2 MCP/storage foundation
  -> M3 lifecycle authority
  -> M4 one-worker vertical slice
  -> M5 real two-worker swarm
  -> M6 stable roster
  -> M7 learning-data qualification
  -> M8 verifier/Ariadna disposition
  -> M9 productization
  -> M10 controlled evaluation
  -> M11 exact Release
```

M12 activation is outside release completion. Fine-tuning, provider upload,
training spend and model promotion are outside both M11 and M12.

Each implementation work package must follow:

```text
reconstruct exact baseline and dirty paths
-> freeze task manifest and forbidden effects
-> write behavioral RED
-> prove the RED fails for the intended missing behavior
-> implement the minimum GREEN
-> run focused + affected regression gates
-> inspect source/test bodies and changed-path scope
-> record exact evidence and unknowns
-> form one atomic English commit
-> validate the committed artifact before dependent work
```

A milestone cannot close from implementer prose, file existence, or a green happy
path. Its acceptance matrix must map every invariant to positive, negative, fault,
restart and concurrency evidence as applicable.

### 10.2 Planned repository and state layout

The paths below are the planned v0.22.0 ownership map. They do not exist at the
M0 boundary. M1 may amend the provider-specific subset only if executable evidence
proves the public Orca contract differs; a material amendment returns to M0 owner
review.

#### Repository source

```text
src/aether_mcp/
  __init__.py                 package/protocol version only
  __main__.py                 local stdio entry point
  server.py                   MCP composition and tool registration
  protocol/
    models.py                 canonical request/response models
    errors.py                 stable error registry
    canonical.py              canonicalization and idempotency digest
    schema_export.py          deterministic JSON Schema snapshots
  security/
    principal.py              trusted coordinator principal derivation
    effects.py                effect classification and authorization
    cursors.py                scoped integrity-protected cursors
    redaction.py              secret/PII redaction before persistence
    crypto.py                 project-scoped authenticated encryption
  domain/
    identity.py               project/home/profile/worktree identity
    manifests.py              immutable swarm contract generations
    participants.py           roster and participation policy
    correlation.py            Aether-to-Orca identity bindings
  store/
    database.py               SQLite connection/transaction boundary
    migrations.py             monotonic schema migration and refusal
    journal.py                operation/idempotency/reconciliation authority
    events.py                 compact append-only semantic events
    content.py                encrypted project-scoped content blobs
    episodes.py               learning-episode manifests and sealing
    datasets.py               labels, lineage, exports and revocations
  providers/orca/
    discovery.py              exact build/catalog qualification
    adapter.py                structured public Orca operations only
    mapping.py                Orca results -> stable Aether outcomes/errors
  services/
    admission.py              project admission/inspection
    swarm.py                  high-level swarm operations
    learning.py               capture/label/dataset/export operations
    retention.py              quota, forget and revocation behavior
    projections.py            status/trace/explanation/read models
```

`src/aether_mcp` is a new bounded integration product. It must not import, copy,
rename or recreate `src/aether_agents`, `olympus_v3`, ACPManager, Harmonia,
`talk_to`, lifecycle databases or the retired policy kernel.

#### Contract snapshots

```text
schemas/aether-mcp/v1alpha1/
  protocol.schema.json
  manifest.schema.json
  event.schema.json
  learning-episode.schema.json
  dataset-manifest.schema.json
  tools.schema.json
```

Python models are the implementation source; committed schema snapshots are
generated deterministically and checked for drift. There is one schema version
per protocol object, and provider/catalog versions remain independent.

#### Tests and fixtures

```text
tests/aether_mcp/
  unit/
  contract/
  storage/
  provider/
  integration/
  e2e/
tests/fixtures/aether_mcp/
  provider_catalogs/
  projects/
  episodes/
  use_cases/
```

All future tests remain discoverable under the existing root `pytest` policy.
No milestone may add a one-off test framework when pytest and the standard
library suffice.

#### Qualification and release tooling

```text
scripts/aether_mcp/
  qualify_orca.py
  check_contract.py
  run_use_cases.py
  inspect_evidence.py
  verify_clean_install.py
docs/releases/v0.22.0/evidence/
  M1_PROVIDER_QUALIFICATION.md
  M1_PROVIDER_QUALIFICATION.json
  M2_MCP_FOUNDATION.md
  M3_LIFECYCLE.md
  M4_ONE_WORKER.md
  M5_TWO_WORKER.md
  M6_ROSTER.md
  M7_LEARNING_DATA.md
  M8_ROLE_DECISIONS.md
  M9_PRODUCTIZATION.md
  M10_EVALUATION_REPORT.md
  M11_RELEASE_ACCEPTANCE.md
```

Human-readable evidence explains consequence and unknowns; machine-readable
evidence carries exact identities, commands, digests and outcomes. Neither file
may claim PASS until independent milestone acceptance has checked the exact
candidate.

#### Planned local state

```text
$AETHER_HOME/state/aether-mcp/v1/index.sqlite3
$AETHER_HOME/state/aether-mcp/v1/projects/<project_id>/content/<digest>.aeb
$AETHER_HOME/state/aether-mcp/v1/projects/<project_id>/exports/<dataset_id>/
```

The SQLite index stores semantic events, operation receipts and metadata—not
Orca's Run/Task/Dispatch state. Rich bodies live only in authenticated encrypted
blobs. Encryption keys never live in Git, schemas, SQLite, episode bodies or
exports. `FULL_EPISODE` fails closed until an accepted key provider is configured;
the deterministic test harness uses ephemeral keys only.

### 10.3 Dependency and authority gates

| Gate | Required decision/evidence | What it authorizes | What remains blocked |
|---|---|---|---|
| D0 | Owner accepts M0 design, cases and this roadmap | Begin repository-only M1 | Runtime activation, credentials, spend, Release |
| D1 | M1 proves exact structured Orca seams | Implement pinned adapter in M2 | Private DB/API use, prose parsing, UI automation |
| D2 | Security review accepts encryption/redaction/key-provider contract | Implement protected episode storage | Persistent key creation or live full capture |
| D3 | Owner approves exact provider/account/model/budget for a bounded real run | Execute named M5/M6/M10 model-backed cases | General activation or recurring spend |
| D4 | M8 evidence supports Verifier and/or Ariadna | Admit only the accepted role/contract | Hidden replacement reviewer or mandatory unproven role |
| D5 | Product owner accepts exact M10 candidate evidence | Enter M11 source Release gate | Persistent activation |
| D6 | Separate post-Release operation authority | Execute M12 on the named installation | Fine-tuning, external upload, model promotion |

`D0` was granted by the product owner on 2026-08-06 and is recorded in
`M0_DESIGN_ACCEPTANCE.md`. The owner fast-tracked only the provider-independent
M2.1a package/stdio bootstrap under D0. It may expose zero tools and perform no
provider, storage or registration effect. M1.1b is deferred, D1–D6 remain
ungranted, and no lower gate implies a later gate. An Orca adapter, provider
call, MCP tool or M2.2+ package still requires its named gate.

### 10.4 Tool-to-milestone coverage

| Milestone | Tools first made GREEN |
|---|---|
| M2 | `project_admit`, `project_inspect`, `swarm_validate`, `swarm_trace`, `orca_search`, `orca_describe`, read-only `orca_call`, `orca_events` |
| M3 | `swarm_start` without dispatch, `swarm_status`, `swarm_reconcile`, `swarm_cancel`, `swarm_record_decision`, `swarm_record_evidence`, `swarm_close` |
| M4 | `swarm_dispatch`, `swarm_message`, `swarm_retry`, mutating allowlisted `orca_call`/`orca_batch` |
| M7 | `learning_capture`, `learning_label`, `learning_dataset`, `learning_export`, `project_forget` |

Every earlier tool remains in regression scope when a later milestone adds
behavior. No milestone may register a placeholder tool that returns fabricated
success.

### 10.5 M0 work packages — freeze the product contract

#### M0.1 — Architecture and authority reconciliation

**Artifacts:** ADR-0001, `../../architecture/AETHER_MCP.md`,
`../../architecture/ORCHESTRATION.md`, PDR-0009/PDR-0012/PDR-0013 and
`../../knowledge/AUTHORITY.md`.

**Gate:** one owner for product meaning, runtime state, semantic events, rich
content, labels, datasets, technical acceptance and final acceptance. Any overlap
between Aether and Orca runtime authority blocks M1.

#### M0.2 — Contract, learning schema and frozen cases

**Artifacts:** `../../reference/AETHER_MCP_CONTRACT.md`,
`../../reference/AETHER_TRACE_SCHEMA.md`,
`../../reference/AETHER_LEARNING_EPISODE_SCHEMA.md`,
`MEASUREMENT_CONTRACT.md` and `USE_CASE_CATALOG.md`.

**Gate:** 24 tools, 16 cases, explicit source/authority for every measurement,
replay exactness classes, redaction/quarantine rules, lineage-isolated splits and
no automatic training eligibility.

#### M0.3 — Owner acceptance

**Action:** present the exact included/excluded scope, D0–D6 gates, runtime layout,
M1–M11 critical path and M12 separation.

**Pass:** owner explicitly accepts or corrects the roadmap. Record corrections in
the authoritative documents before changing M0 status.

**Stop:** no source, test, package, config, runtime, credential, commit, provider
call or external effect begins under M0 documentation authority.

**Recorded result:** accepted on 2026-08-06. The M0 design-and-acceptance work
closed without new source, runtime, worker, configuration, credential or provider
effects. Earlier retirement diagnostics remain historical candidate evidence. See
`M0_DESIGN_ACCEPTANCE.md`.

### 10.6 M1 work packages — qualify Orca before writing the adapter

#### M1.1 — Freeze source and executable identity

**Planned files:** create `scripts/aether_mcp/qualify_orca.py`,
`tests/aether_mcp/provider/test_qualification.py` and M1 evidence files.

**RED:** reject an absent executable, wrong digest, version/catalog mismatch,
unstructured response or ambient/global state path.

**GREEN:** resolve one exact Orca executable/artifact, build/version, digest,
catalog/schema version, isolated home and state root. The probe emits JSON without
secrets and performs no worker/model call.

**Verify:** run the qualification test and probe twice; require byte-equivalent
identity fields and no new files outside the isolated root/evidence allowlist.

**Fast-track disposition (2026-08-07):** M1.1a exact installed identity and
catalog are accepted in `M1_1A_IDENTITY_CATALOG_ACCEPTANCE.md` as the read-only
basis for M1.2. Reusable adversarial isolation remains M1.1b accepted debt and
must close before M1.3. This split does not label the rejected generic qualifier
accepted and authorizes no lifecycle operation.

#### M1.2 — Freeze the structured provider seam matrix

Map every low-level operation needed by the 24 MCP tools to an official structured
Orca operation, its arguments, result schema, effect class, timeout and recovery
semantics. Classify each as `SUPPORTED`, `PARTIAL`, `MISSING` or `UNKNOWN`.

**Pass:** every M2–M5 operation has a public structured seam. Diagnostic prose may
be retained as bounded evidence but cannot become control input.

**Fail/return to M0:** a required operation exists only through private storage,
GUI automation, free-form shell or unstable prose parsing.

#### M1.3 — Exercise isolated lifecycle and rollback

Run cold start, status, restart, stop, rollback and cleanup only inside an
M1-owned temporary root. Capture process/resource inventories before and after.

**Faults:** startup timeout, malformed catalog, killed qualification process,
partial state creation and repeated cleanup.

**Pass:** no global/installed Orca state changes, cleanup is idempotent and zero
M1-owned survivors remain.

#### M1.4 — Close the provider decision

M1 evidence records the exact supported catalog and every gap. If the seam is
sufficient, freeze the adapter contract and dependency versions. If not, stop;
do not design a hidden fallback.

**Proposed atomic commits:**

1. `test: add deterministic Orca qualification contract`
2. `docs: record qualified Orca provider boundary`

### 10.7 M2 work packages — build the default-off MCP foundation

#### M2.1 — Bootstrap only the bounded `aether_mcp` package

**Planned modifications:** `pyproject.toml`, `Makefile` and the new package/test
roots from section 10.2.

Freeze Python 3.11+, the exact official MCP SDK compatible with Hermes and the
pinned cryptography dependency selected at D2. Prefer standard-library `sqlite3`;
do not restore `aiosqlite`, the historical `aether-agents` distribution or old
entry points.

**RED:** import/stdio smoke expects only the new namespace and proves every legacy
namespace/entry point remains absent.

**GREEN:** `python -m aether_mcp` starts one local stdio MCP process, exposes
protocol metadata and cleanly exits on EOF without network listeners or provider
effects.

#### M2.2 — Implement canonical protocol and stable errors

Implement result/error envelopes, operation identity, effect classes, canonical
request encoding, schema export and bounded input sizes.

**Negative matrix:** unknown fields where forbidden, oversized body/cursor,
malformed UUID, wrong protocol version, caller-asserted principal, arbitrary
command string, idempotency mismatch and secret-bearing error text.

**Pass:** generated snapshots match `schemas/aether-mcp/v1alpha1/`; all 24 tool
schemas are present but only M2 tools are registered as callable.

#### M2.3 — Implement trusted principal and project admission

Derive coordinator identity from launch/session context. Resolve canonical project
root, Git common root/worktree, Aether/Hermes home and profile. Generate immutable
project IDs server-side.

**Tests:** symlink escape, moved root, nested repo, nonexistent root, worktree of
same repo, foreign profile, cross-project ID guessing, restart and concurrent
admission.

**Pass:** `project_admit` and `project_inspect` cannot enumerate or mutate another
project and cannot initialize/clean an admitted project.

#### M2.4 — Implement migrations, journal and semantic event authority

Create monotonic SQLite migrations, uniqueness constraints, append transactions,
operation replay/conflict and integrity roots. Every mutation request must commit
before a provider effect can begin.

**Fault matrix:** busy lock, crash before request commit, crash after request but
before provider call, crash after possible effect, migration interruption,
unsupported future schema and two MCP processes sharing one Aether home.

**Pass:** no provider call occurs when durable append fails; possible effects
become `RECONCILIATION_REQUIRED`; replay cannot duplicate a mutation.

#### M2.5 — Implement protected content foundation

Redact before persistence, derive project-scoped content identities, encrypt each
blob with authenticated associated data, write atomically and verify before index
commit. The exact cryptographic construction and key-provider interface receive a
security review before GREEN.

**Tests:** secret canaries in every content field, wrong project/key/AAD, nonce
uniqueness, truncated/tampered blob, short write, orphan cleanup, quota exhaustion,
capture disabled, key unavailable and cross-project duplicate plaintext.

**Pass:** structured capture remains usable without a key; `FULL_EPISODE` fails
closed without one; no plaintext secret or cross-project digest correlation exists
on disk.

#### M2.6 — Implement read-only Orca catalog and projections

Implement pinned `orca_search`, `orca_describe`, read-only `orca_call`,
`orca_events`, `swarm_validate`, and safe `swarm_trace`/status projections.

**Pass:** output is source-labelled and freshness-aware; unsupported or drifted
provider schemas fail closed; Aether stores correlations, not copied runtime
state.

#### M2.7 — Foundation closure

Run focused contract/storage/provider tests, all existing retirement/setup tests,
Ruff, compileall, schema drift, local-link, secret and forbidden-import scans.
Update retirement tests intentionally: allow only `src/aether_mcp`; continue to
reject `src/aether_agents`, `olympus_v3`, old plugins/entry points and legacy
dependencies.

**Proposed atomic commits:**

1. `feat: add bounded Aether MCP protocol package`
2. `feat: add project-isolated operation and trace store`
3. `feat: add protected learning content foundation`
4. `feat: add read-only Orca provider catalog`
5. `test: preserve retired runtime boundaries for Aether MCP`

### 10.8 M3 work packages — own lifecycle semantics without workers

#### M3.1 — Validate and start without dispatch

Implement immutable manifest generations and `swarm_start` with dispatch disabled.
Persist request and possible-effect state before invoking Orca; correlate returned
Run/Task IDs exactly.

**Tests:** invalid DAG/cycle, stale project inspection, forbidden participant,
effect mismatch, duplicate exact start, conflicting replay, partial Run/Task
creation and provider timeout.

#### M3.2 — Status, decision and evidence append

Implement `swarm_status`, `swarm_record_decision` and
`swarm_record_evidence` as source-labelled projections/semantic facts. Reject
caller-asserted acceptance and evidence outside the admitted contract.

#### M3.3 — Reconcile uncertain effects before retry

Implement observe/fence modes, normal provider budget, `reconcile_after_utc` and
`lease_deadline_utc`. A deadline creates an obligation; it never invents failure.

**Crash matrix:** response loss, process death after provider acceptance, durable
request with no receipt, stale fence token and two reconcilers.

**Pass:** a possibly accepted effect is called at most once until exact evidence
or an authorized fence makes a new attempt safe.

#### M3.4 — Cancel and close

Implement cancellation request/acknowledgement separately from aggregate cleanup.
`swarm_close` requires terminal semantic disposition, resource inventory and
provider cleanup evidence.

**Tests:** cancel-running, cancel-terminal, partial acknowledgement, close with
live resource, repeated close, provider restart and cleanup failure.

#### M3.5 — Lifecycle closure

Execute UC-C01, C02, C04, C06, C08 and C09 variants that do not require a worker.
Evidence must prove one receipt per effect, explicit unknowns and zero survivors.

**Proposed atomic commits:**

1. `feat: add manifest-bound Orca lifecycle control`
2. `feat: reconcile uncertain Orca effects before retry`
3. `feat: add evidence-bound swarm closure`

### 10.9 M4 work packages — one deterministic worker vertical slice

#### M4.1 — Build a deterministic fixture worker

Create a bounded worker fixture under `tests/fixtures/aether_mcp/` that can emit
progress, request one answer, write one allowlisted artifact, return evidence,
fail before/after acceptance and obey cancellation. It uses no external model,
credential or spend.

#### M4.2 — Dispatch, observe and message

Implement `swarm_dispatch` and `swarm_message` against the M1-qualified public
surface. Dispatch acceptance, worker progress, technical completion and semantic
acceptance remain distinct events.

**Tests:** wrong sender/recipient/task, unauthorized scope, message size/type,
question/reply correlation, worker completion without evidence and late message
after fencing.

#### M4.3 — New-attempt retry lineage

Implement `swarm_retry` only after terminal/fenced evidence. Every retry creates a
new Dispatch/attempt/epoch; stale attempts lose write/message authority.

#### M4.4 — Seal the first complete learning episode

Capture the exact redacted context/messages/tool exchanges/artifact/test/result
that the deterministic worker saw or produced. Record explicit gaps and labels;
seal only after semantic close.

#### M4.5 — Vertical-slice closure

Run success, question/reply, deterministic failure, cancellation, retry and
restart variants. Validate the artifact independently and prove no worker,
terminal, worktree or lease survives.

**Proposed atomic commits:**

1. `test: add deterministic Orca worker fixture`
2. `feat: add bounded dispatch messaging and retry`
3. `feat: seal replayable one-worker learning episodes`

### 10.10 M5 work packages — real parallel swarm

#### M5.1 — Prove deterministic two-worker overlap first

Use two independent fixture Tasks/worktrees with a barrier fixture so overlap is
observed deterministically rather than inferred from total duration. Submit both
Dispatches before polling either.

**Tests:** conflicting scope rejection, one worker failure while the other
continues, handoff before predecessor evidence, stale writer and aggregate cancel.

#### M5.2 — Implement peer communication and dependency handoff

Permit only admitted message kinds/recipients. A handoff references an immutable
artifact/evidence digest; prose alone cannot unlock a dependent Task.

#### M5.3 — Integrate and verify artifacts

Hermes reviews both outputs, integrates in the coordinator-owned scope and runs
affected regression evidence. Worker completion cannot self-merge or self-accept.

#### M5.4 — Execute one bounded model-backed swarm

This subpackage is blocked until D3 names the provider, accounts, models, budget,
task and stop limit. Use isolated worktrees/state, never persistent activation.
Compare actual dispatch overlap, quality, retries, messages, cost and cleanup with
the deterministic fixture baseline.

**Pass:** UC-C03 and C05 pass with real overlap and zero survivors. If the
authorized real provider run is unavailable, record `UNKNOWN`; do not substitute
fixture evidence for model-backed behavior.

**Proposed atomic commits:**

1. `test: prove deterministic two-worker overlap and fencing`
2. `feat: add artifact-bound worker handoffs`
3. `docs: record bounded model-backed swarm evidence`

### 10.11 M6 work packages — enforce the stable roster

#### M6.1 — Freeze retained profile contracts

Inspect and bind exact homes/config/templates for Hefesto, Daedalus and Ictinus.
Ariadna remains disabled; Independent Verifier remains absent. Record model/toolset
identity without secrets.

#### M6.2 — Retire target-forbidden profiles from active generation

Modify the profile inventory/setup/doctor/tests so Athena and Etalides are not
generated, registered, selected, recovered or used as fallback. Preserve their
historical documentation; remove active physical templates only in this
authorized implementation milestone.

Planned affected paths include `home/profiles/*`, `home/config.yaml.template`,
`scripts/setup.sh`, `scripts/update.sh`, `Makefile`, profile/reference docs and
setup/retirement tests.

#### M6.3 — Prove multiple instances per archetype

Launch two Task-bound instances of one retained archetype in independent scopes.
Require unique Run/Task/Dispatch/worker/worktree identities and shared immutable
profile digest.

#### M6.4 — Prove distinct product contribution

Execute the frozen Hefesto, Daedalus and Ictinus cases. A profile passes only when
its output demonstrates the contracted domain contribution, not merely successful
startup.

**Pass:** UC-C07 and the role-specific catalog cases pass; direct/indirect/fallback
attempts to select retired roles deterministically fail.

**Proposed atomic commits:**

1. `refactor: enforce the retained Aether swarm roster`
2. `test: prove profile policy and worker-instance isolation`
3. `docs: record retained archetype qualification`

### 10.12 M7 work packages — turn episodes into trustworthy datasets

#### M7.1 — Capture fidelity and explicit gaps

Capture ordered model-visible system/developer/user/assistant/worker messages,
tool schemas/calls/results, material Orca messages, artifacts and provider usage.
Assign exactness class to every body; never label a sanitized or missing body as
verbatim.

#### M7.2 — Redaction, encryption and quarantine equivalence class

Run synthetic secret/PII canaries through every source: prompt component, tool
argument/result, terminal slice, message, artifact diff, exception, provider body
and export. A detection/redaction failure quarantines the episode and blocks
dataset/export eligibility.

#### M7.3 — Sealing, replay, quota and crash recovery

Seal immutable manifests only when all referenced blobs exist and verify. Replay
must reconstruct order and gaps without invoking a provider. Quota exhaustion
pauses capture visibly; it never deletes old data or downgrades silently.

#### M7.4 — Label authority

Implement append-only labels with source/authority: user acceptance/correction,
Hermes technical verdict, deterministic evaluator evidence, independent review and
worker self-report. Worker self-report remains non-accepting.

#### M7.5 — Dataset construction

Build deterministic SFT, preference, tool-policy, repair, routing and evaluation
manifests. Split by project/task/use-case lineage, not individual turns. Deduplicate
within authorized project boundaries without revealing cross-project equality.

#### M7.6 — Contamination and evaluator isolation

Reject benchmark answers, evaluator prompts, sibling retries and held-out lineages
from training splits. Dataset builders cannot modify their own evaluator, frozen
thresholds or source labels.

#### M7.7 — Export, revoke and forget

Export only sealed eligible datasets to an exact approved local destination.
Record export digest/receipt. Revocation blocks future use; `project_forget`
traverses events, blobs, labels, datasets and exports and reports external
derivatives honestly.

#### M7.8 — Learning-data closure

Run UC-L01, L02 and L03 plus storage migration, tamper, concurrent capture and
secret scans. Rebuild each dataset twice and require identical manifests/digests.
Prove there is no network client or trainer effect in the package.

**Proposed atomic commits:**

1. `feat: capture sealed replayable learning episodes`
2. `feat: add authority-bound episode labels`
3. `feat: build lineage-isolated learning datasets`
4. `feat: add local export revocation and project forget`
5. `test: reject contaminated or privacy-unsafe learning data`

### 10.13 M8 work packages — decide optional roles from evidence

#### M8.1 — Freeze evaluator tasks and baselines

Use the same tasks, models, initial conditions and acceptance rules for direct
Hermes, Hermes deterministic evaluation, proposed Independent Verifier and
proposed Ariadna continuity work. Keep their own outputs out of their evaluation
context.

#### M8.2 — Independent Verifier decision

Measure defect discovery, false positives, missed blockers, time, calls, cost and
rework. If accepted, first add a read-only profile/contract and no write/release
authority. If rejected, record explicit exclusion and create no runtime profile.

#### M8.3 — Ariadna decision

Compare against Hermes-native memory, skills, session history and versioned docs.
Admission requires distinct continuity value and bounded cost without global-user
profile authority. Otherwise keep disabled and do not restore curation facades.

**Pass:** M8 evidence names `ADMIT`, `REJECT` or `INSUFFICIENT` for each role.
`INSUFFICIENT` cannot become a hidden release dependency unless M0 explicitly
required it.

### 10.14 M9 work packages — productize without activating

#### M9.1 — Package and configuration contract

Finalize `aether-mcp` package metadata/version, stdio command, root coordinator
MCP registration template and environment allowlist. Worker profiles must not
receive the coordinator surface. Default capture is structured-only and swarm
activation remains off.

#### M9.2 — Setup, update and doctor

Extend `scripts/setup.sh`, `scripts/update.sh`, `Makefile` and tests for idempotent
installation, exact executable/version resolution, schema compatibility, key-
provider readiness, Orca readiness and disabled-by-default status. Never print
secrets or create persistent encryption credentials without D6.

#### M9.3 — Migration and upgrade

Test clean install, previous v0.20 install, early v0.22 schema upgrade, interrupted
migration, unsupported future schema and repeated upgrade. Historical `.aether`
databases remain untouched; only the new `state/aether-mcp/v1` store participates.

#### M9.4 — Rollback and uninstall

Rollback code/config while preserving the new store and exports by default.
Destructive data removal requires a separate exact action. Restore previous
wrappers/config atomically and prove no stale process or registration remains.

#### M9.5 — Documentation and clean-room first use

Update README, website, installation, configuration, command, environment,
project-layout, privacy, troubleshooting and rollback docs. In a disposable clean
home, install twice, run doctor, inspect tools/status and uninstall without ever
starting a worker.

**Proposed atomic commits:**

1. `feat: package the default-off Aether MCP product`
2. `feat: add Aether MCP setup update and diagnostics`
3. `feat: add non-destructive upgrade and rollback`
4. `docs: document the v0.22.0 MCP and learning boundary`

### 10.15 M10 work packages — execute the frozen evaluation

#### M10.1 — Freeze exact candidates and equivalent baselines

Record candidate tree, package/protocol/provider/catalog/profile/model/tool/fixture
digests and environment. Direct and swarm variants use equivalent initial state
and models unless the frozen case explicitly studies routing.

#### M10.2 — Run deterministic conformance first

Execute all deterministic C/L cases, contract/storage/fault/restart/concurrency
matrices and full repository gates before any authorized model-backed run. Stop
on privacy, identity, duplicate-effect or cleanup blockers.

#### M10.3 — Run authorized model-backed product cases

Under D3, execute cases in the frozen order with bounded attempts and costs.
Persist exact episodes, labels, corrections and unknowns. Never rerun selectively
to hide a failure; corrections create new attempts and lineage.

#### M10.4 — Independent evaluation and product disposition

The evaluator consumes frozen artifacts but cannot change tasks, thresholds,
datasets or candidate. Report direct-versus-swarm quality, latency, cost,
coordination overhead, reliability, cleanup and learning-data fitness. User
corrections remain product authority.

#### M10.5 — Correction budget

Permit at most two bounded correction rounds per failed equivalence class before
returning to the owning milestone. After each correction, rerun the full affected
case family and final aggregate suite. Never lower a frozen threshold to obtain a
pass.

**Pass:** all mandatory thresholds in `MEASUREMENT_CONTRACT.md` and
`USE_CASE_CATALOG.md` pass on the exact candidate; unavailable evidence is
`UNKNOWN`, not zero or PASS.

### 10.16 M11 work packages — accept and publish one exact tree

#### M11.1 — Reconcile scope and atomic history

Audit every changed/untracked path against this roadmap, split mixed changes into
logical English commits, scan for secrets and remove generated residue. Version,
schema, package, README, status, changelog and release evidence must agree.

#### M11.2 — Validate the committed candidate in isolation

Create a fresh detached worktree at the exact candidate commit and a candidate-
local environment. Verify interpreter/import provenance, install dependencies,
run focused and full tests, Ruff, compileall, schemas, docs/links, setup/update/
doctor, clean install/upgrade/rollback, use cases, forbidden-runtime scans and
secret review. The checkout must remain clean after verification.

#### M11.3 — Product-owner exact-candidate acceptance

Present the exact SHA/tree, included/excluded scope, evidence, limitations,
unknowns, alternatives, compatibility and rollback. D5 requires explicit product
acceptance; internal tests cannot grant it.

#### M11.4 — Integrate and publish under standing source authority

If repository policy and standing authority still apply and every required gate
is green, push the feature branch, open/update a PR to `main`, preserve audited
history, wait for required checks, merge, verify tree identity, create the
annotated `v0.22.0` tag on integrated `main`, and verify the GitHub Release.

This future source sequence does not follow from the current documentation request
and never authorizes install, restart, activation, credentials or spend.

#### M11.5 — Reconcile release state

Verify `origin/main`, peeled tag and GitHub Release converge; reconcile issues and
milestone; delete only the proved merged branch/worktree; preserve historical and
learning stores. Set M12 to separately gated, not pending implementation.

### 10.17 M12 post-Release activation plan

M12 is documented here only to prevent source Release from being mistaken for a
live cutover. Every package below remains blocked until D6.

#### M12.1 — Freeze the named installation and rollback baseline

Inventory the exact installation, profiles, services, wrappers, process/listener
state, MCP registrations, Orca identity, data roots and rollback sources. Preserve
secret-safe before-state evidence and prove the v0.22.0 package/tree identity.

**Stop:** identity drift, missing rollback source, unrelated dirty runtime state or
an installation different from the one named by D6.

#### M12.2 — Configure key custody and default-off registration

Configure the accepted key provider and capture/retention/quota policy without
printing or copying secrets into Git. Register the local MCP and exact Orca build,
then enable only the accepted participant policy. Registration precedes worker
activation and must be independently reversible.

**Pass:** doctor/status report exact versions, key-provider readiness and no
worker/Run; non-coordinator profiles cannot see the full MCP surface.

#### M12.3 — Execute one bounded live E2E

Activate only for the named case and budget. Exercise start, dispatch, interaction,
evidence, episode capture, semantic acceptance, close, restart/replay, privacy,
project isolation and zero-survivor cleanup. Record live evidence separately from
v0.22.0 source acceptance.

**Pass:** the bounded case and post-restart inspection pass with no secret leak,
foreign-project access, stale worker, terminal, worktree, listener or lease.

#### M12.4 — Accept activation or restore the baseline

On any failed gate, execute the frozen rollback and verify the exact pre-activation
registration/process/config state while preserving diagnostic evidence. On GREEN,
the owner separately accepts the live configuration and ongoing policy; one E2E
does not authorize broader participants, projects, quotas or spend.

No recurring capture, provider spend, dataset upload or fine-tuning is implied.

### 10.18 Cross-milestone regression matrix

| Invariant | First RED | Must rerun through |
|---|---|---|
| No legacy runtime/fallback | M2 | M11 |
| Protocol/schema compatibility | M2 | M11 |
| Project/principal isolation | M2 | M12 |
| Durable-before-effect idempotency | M2 | M11 |
| Unknown-effect reconciliation | M3 | M12 |
| Writer/attempt fencing | M4 | M12 |
| Parallel overlap and handoff | M5 | M10 |
| Participant policy/retired roles | M6 | M12 |
| Secret redaction/encryption | M2 | M12 |
| Episode replay/gap honesty | M4 | M10 |
| Dataset lineage/contamination | M7 | M10 |
| Revocation/forget/export honesty | M7 | M12 |
| Install/upgrade/rollback | M9 | M12 |
| Product thresholds | M10 | M11 |
| Zero-survivor cleanup | M1 | M12 |

### 10.19 Completion definition

v0.22.0 is complete only at M11 when one integrated and published exact tree has:

- every required implementation artifact;
- 24 real MCP tools with no placeholders or arbitrary shell;
- qualified one-worker, parallel-swarm and retained-roster behavior;
- protected replayable episodes and reproducible local datasets;
- all mandatory 16-case thresholds and aggregate gates;
- clean install/upgrade/rollback;
- no legacy runtime/fallback;
- exact product-owner acceptance and source Release evidence.

M12 activation and any fine-tuning remain separate outcomes. A successful M7
dataset export is not evidence that Aether improved; only a separately designed,
baseline-controlled evaluation can make that claim.

## 11. Evidence contract

Every executed milestone records:

- exact project root and isolated state roots;
- exact Git SHA/tree state;
- Aether MCP protocol/package identity;
- Orca executable/build/digest/catalog identity;
- Hermes/worker profile home, model route, and allowed toolset;
- command/tool input in normalized secret-free semantic form plus the exact
  admitted redacted model-visible episode reference;
- structured result and timestamps;
- Aether/Orca identity bindings;
- artifact/evidence digests;
- failures, retries, corrections, unknowns, and waivers;
- resource inventory before/after;
- rollback and zero-survivor proof;
- criteria-to-evidence map and acceptance authority.

Historical evidence is immutable. A correction adds a new record and explicit
supersession.

## 12. Failure and stop policy

Stop the current milestone and preserve evidence when:

- exact provider build/schema cannot be established;
- a required operation lacks a public structured seam;
- Aether and Orca both appear authoritative for the same operational fact;
- identity, scope, participant, or effect policy cannot be enforced;
- an operation result remains ambiguous after bounded reconciliation;
- a stale writer cannot be fenced;
- any learning layer exposes credentials, hidden chain-of-thought, unadmitted
  cross-project content or other forbidden data;
- capture claims completeness with gaps, dataset lineage/contamination is
  unresolved, or an export/training effect exceeds authority;
- migration/integrity/retention behavior is unsafe;
- rollback cannot restore the prior state;
- cleanup cannot prove resource disposition;
- a mandatory use-case threshold fails;
- the same approach fails three times.

A failed gate does not authorize a hidden fallback, private Orca database access,
UI automation, broad kernel, or acceptance rewrite. Return to the smallest
applicable design/implementation boundary.

## 13. Current gate and stop condition

### NOW

Execute **M2.1a — default-off MCP bootstrap** as one external-agent task. Add only
the `aether_mcp` package metadata, static identity, a real zero-tool stdio MCP
process, focused tests and the bounded smoke target. It must not invoke Orca,
open a socket, persist state, register with Hermes or implement any MCP tool.

### STOP CONDITION

Stop after one exact M2.1a implementation/evidence commit and report. Hermes then
reproduces package metadata, real initialize/list-tools handshake, EOF behavior,
focused/full tests and zero socket/process/file effects. M1.1b, D1, provider
adapter, M1.3 and M2.2+ remain blocked regardless of the implementer result.

### LATER GATES

Accept M2.1a -> separately authorize M2.2 or return to M1.1b/provider
qualification as required. Before any Orca operation: close M1.1b -> separately
authorized isolated contract fixtures/lifecycle -> M1.4 provider decision ->
provider adapter -> M3 lifecycle -> M4 one worker -> M5 real two-worker swarm -> M6 roster -> M7
learning-data qualification -> M8 verifier/Ariadna decisions -> M9
productization -> M10 controlled evaluation -> M11 Release -> M12 activation.
