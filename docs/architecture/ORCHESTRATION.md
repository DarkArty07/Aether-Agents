# Contract-Governed Lateral Multi-Agent Orchestration

> **Status:** PROPOSED — AWAITING PRODUCT OWNER APPROVAL
> **Owner:** Christopher (DarkArty07)
> **Design date:** 2026-07-29
> **Current implementation baseline:** [`v0.19.x kernel-migration closeout`](../releases/v0.19.x-kernel-migration/ROADMAP_CLOSEOUT.md)
> **Normative product model:** [`../knowledge/MULTI_AGENT_MODEL.md`](../knowledge/MULTI_AGENT_MODEL.md)
> **Governing decisions:** [`PDR-0004`](../decisions/PDR-0004-product-owner-authority-and-bounded-autonomy.md), [`PDR-0005`](../decisions/PDR-0005-multi-agent-participation-and-coordination.md), and [`PDR-0009`](../decisions/PDR-0009-semver-self-improvement-cycle.md)
> **Implementation authorization:** None. Approval of this design establishes the target architecture; it does not by itself authorize source changes, live Daimon sessions, runtime activation, credentials, migration, release, deployment, or publication.

## 1. Decision summary

Aether should replace routine Hermes hub-and-spoke delegation with **contract-governed lateral orchestration**:

- the user remains product owner;
- Hermes interprets intent, freezes one bounded execution contract, handles material amendments or escalations, and synthesizes the final product result;
- Harmonia coordinates admitted work but does not become a product authority, reasoning hub, message relay, worker, or ACP lifecycle owner;
- the deterministic kernel and its durable ledger are the only semantic workflow authority;
- Olympus and `ACPManager` remain the only process and ACP-session lifecycle authority;
- authorized Daimons exchange typed results, evidence, review requests, blockers, and dependency handoffs through kernel-bound artifacts and events without Hermes copying their messages;
- every deliverable has one accountable owner, every writer has a bounded write scope, and every external effect is denied unless explicitly authorized;
- technical closure remains distinct from Hermes' completion proposal and the user's final product acceptance.

This architecture is **not unconstrained peer-to-peer**. It deliberately centralizes product meaning and deterministic authority while decentralizing routine specialist execution and communication.

## 2. Product problem

The current legacy interaction model makes Hermes both strategic lead and transport layer:

```text
Hermes -> specialist A -> Hermes -> specialist B -> Hermes
```

That topology has four recurring costs:

1. the most capable and expensive model spends context and inference on routine relay;
2. every handoff waits for Hermes even when the next task is already approved;
3. specialist outputs lose provenance or nuance when summarized into another prompt;
4. recovery, retry, and completion authority become entangled with conversation state.

A pure autonomous swarm would remove the relay but create worse product failures: task proliferation, unclear authority, conflicting writers, user-policy violations, vision drift, and unsupported completion claims.

The required middle path is:

> **Centralized intent and deterministic authority; lateral, contract-bounded specialist execution.**

## 3. Approved requirements and traceability

| ID | Requirement | Governing source | Design response |
|---|---|---|---|
| R1 | The user owns product meaning, material scope, consequential effects, and final acceptance. | `PDR-0004`, `AUTHORITY.md` | Product authority remains outside the worker graph. |
| R2 | Hermes must not relay every routine specialist result, review, correction, or handoff. | `PDR-0005`, Objective 13 | One contract submission; zero routine Hermes relays after admission. |
| R3 | Product vision remains centralized while routine coordination becomes lateral. | `VISION.md`, `PRINCIPLES.md` | Product, coordination, and execution planes have separate owners. |
| R4 | Every Daimon has an effective `required`, `allowed`, `disabled`, or `forbidden` state. | `PDR-0005`, `MULTI_AGENT_MODEL.md` | The effective participant-policy snapshot is contract-bound and enforced on every route. |
| R5 | A Daimon participates only when its expected value exceeds coordination cost. | `PDR-0005`, Principle 13 | No universal full-team workflow; the minimum sufficient roster is admitted. |
| R6 | Lateral collaboration must preserve contract, role, scope, evidence, budget, provenance, and traceability. | `MULTI_AGENT_MODEL.md` | Typed messages and immutable artifact references cannot expand authority. |
| R7 | Every task or deliverable has one accountable owner. | `MULTI_AGENT_MODEL.md` | A task has one bound worker and one write owner; reviewers do not become co-writers. |
| R8 | Harmonia coordinates but cannot amend intent, override policy, implement, self-approve, or call ACP directly. | `PDR-0005` | Harmonia proposes actions; the kernel validates and commits; Olympus executes. |
| R9 | Olympus owns ACP process and session lifecycle. | `PDR-0004`, `PDR-0005` | All spawn, observe, cancel, and cleanup effects pass through `OlympusRuntimeAdapter -> ACPManager`. |
| R10 | Uncertain external effects must reconcile before retry or direct takeover. | Self-improvement cycle, kernel evidence | Durable outbox, fencing, `UNKNOWN`, reconciliation, and cleanup proof are mandatory. |
| R11 | Current user policy overrides project, run, defaults, history, and agent recommendations. | `MULTI_AGENT_MODEL.md` | Policy resolution records effective state and provenance before admission. |
| R12 | The default experience shows outcomes and meaningful milestones, not raw agent theater. | `EXPERIENCE.md`, Principles 21–23 | Hermes consumes compact projections; full events remain available for drill-down. |
| R13 | Aether's complexity is justified only by product-quality and coordination-cost improvement. | `VISION.md`, Principle 18 | Evaluation compares the same task with direct/general-agent baselines. |
| R14 | No fault may silently restore the legacy hub or create duplicate semantic authority. | `PDR-0005`, PDR-0009 | `talk_to` is not a normal fallback; takeover requires terminal reconciliation and zero survivors. |
| R15 | Technical terminality does not prove user-outcome completion. | `PDR-0008`, `MULTI_AGENT_MODEL.md` | Task, run, product-completion, and user-acceptance states remain separate. |

No requirement in this design is derived merely from available code. Product documents and approved decisions define the target; source and tests define what can be reused.

## 4. Current verified baseline

The maintained default-off path already contains a useful bounded kernel. The following capabilities are verified in current source and preserved release evidence:

- strict `harmonia` MCP actions: `start`, `status`, and `stop`;
- immutable `ExecutionContract` identity and generation;
- project-derived, SQLite-backed durable ledger;
- authenticated writer and integrity keys loaded outside YAML and MCP payloads;
- task, attempt, session, dispatch, evidence, cleanup, and closure events;
- one writer lease and fenced outbox delivery;
- exact project-root allowlisting;
- kernel-authorized ACP dispatch through public `ACPManager` methods;
- verifier-owned task-result receipts;
- immutable, digest-bound handoff snapshots;
- fixed two-task automatic handoff;
- bounded deterministic successor selection with kernel revalidation and CAS commit;
- restart recovery and monitor resumption;
- cleanup proof requiring zero logical and process survivors;
- a default-off runtime and no need to revive the retired R2–R8 protocol, transport, shadow, or pilot laboratories.

### 4.1 Components to retain

| Current component | Target responsibility | Disposition |
|---|---|---|
| `harmonia_contract.py` | Strict public request parsing | Retain and evolve with exact topology variants and task briefs. |
| `harmonia_service.py` | Admission and public projection | Retain; remove private cross-component access and split policy/compilation/projection responsibilities. |
| `harmonia_store.py` | Project-scoped store derivation and read-only inspection | Retain. |
| `harmonia_runtime.py` | Project runtime composition and monitor ownership | Retain; replace callback/private coupling with public kernel operations. |
| `contracts.py` | Immutable execution authority | Retain; add effective participant policy and per-task semantic contracts. |
| `ledger.py` | Authoritative append-only state and transactional batches | Retain; expose narrow public query/command boundaries before decomposition. |
| `workflow.py` | Deterministic state reduction | Retain; distinguish technical closure from semantic task outcome. |
| `kernel_runtime.py` | Kernel commands and projections | Retain as sole semantic write authority. |
| `kernel_dispatcher.py` | Outbox, fencing, dispatch, evidence, and cleanup commands | Retain; evolve the canonical worker envelope. |
| `evidence.py` | Artifact verification, receipts, and handoff snapshots | Retain; add typed result semantics without weakening verifier ownership. |
| `harmonia_selection.py`, `selection_commit.py` | Bounded selection proposal and CAS commit | Retain; selection remains contract-bound and deterministic first. |
| `budget.py`, `leases.py`, `effects.py`, `closure.py`, `review.py`, `projections.py` | Safety and semantic foundations | Retain where used; expose only bounded public operations. |
| `olympus_adapter.py` | ACP lifecycle side effects | Retain as the sole runtime adapter. |
| `principal.py` | Project-scoped principal identity | Retain and extend only when participant-policy enforcement requires it. |

### 4.2 Gaps that prevent the target experience

| Gap | Current evidence | Required correction |
|---|---|---|
| Public schema/parser mismatch | The MCP schema still requires selection fields for every `start`, while the parser supports single, fixed, and bounded forms. | Exact mutually exclusive schema variants; GitHub #133. |
| No per-task brief | Fixed tasks carry ID, worker, permissions, and prerequisites, but share one run-level objective. | Add a bounded task brief and task-specific acceptance contract. |
| Legacy profile assumptions | Ictinus and Hefesto state that Hermes directly prompts them and receives every result. | Make them kernel-dispatched, handoff-aware specialists. |
| Incomplete participant policy | Athena is hard-rejected, but the four-state policy is not uniformly resolved or enforced. | Add an effective policy snapshot and enforce it at compile, selection, dispatch, retry, recovery, and substitution. |
| Weak semantic result model | `AETHER_TASK_RESULT_V1` accepts a generic result mapping; technical terminal status drives closure. | Add a typed semantic outcome and structured deliverables/evidence. |
| Projection ambiguity | Public status focuses on the latest events and always reports `semantic_completion: false`. | Add run-level and per-task semantic projections with truthful unknown states. |
| Private authority crossings | Service/runtime call `ledger.conn`, dispatcher private methods, private writer state, and `_after_close`. | Replace them with narrow public kernel/ledger methods. |
| Misleading configuration names | `kernel-single-task` enables fixed and bounded graphs; `mode: legacy` is compatibility-only. | Migrate names through a separately tested compatibility contract. |
| No general typed lateral inbox | The current fixed handoff is dependency-driven only. | Add typed message events only after the fixed vertical path is healthy. |
| No product-value proof | Internal coordination tests do not show better software outcomes. | Compare quality, rework, latency, cost, and user coordination against a simpler baseline. |

## 5. Target architecture

```text
┌──────────────────────────────── PRODUCT PLANE ────────────────────────────────┐
│ User / Product Owner                                                        │
│   vision · priorities · material compromises · external effects · acceptance│
│                                │                                             │
│                                ▼                                             │
│ Hermes                                                                       │
│   intent · requirements · contract proposal · amendments · escalation ·      │
│   final product synthesis                                                    │
└────────────────────────────────┬──────────────────────────────────────────────┘
                                 │ one admitted contract / material amendment
                                 ▼
┌──────────────────────────── COORDINATION PLANE ───────────────────────────────┐
│ Harmonia                              Deterministic Kernel                    │
│ observe · propose · schedule   ───►   validate · commit · fence · release     │
│ no product or ACP authority           sole semantic workflow writer          │
│                                          │                                   │
│                                          ▼                                   │
│                              Durable Coordination Ledger                      │
│                   contracts · policy · tasks · messages · evidence · closure │
└────────────────────────────────┬──────────────────────────────────────────────┘
                                 │ kernel-authorized effects
                                 ▼
┌────────────────────────────── EXECUTION PLANE ────────────────────────────────┐
│ Olympus / ACPManager                                                        │
│ spawn · send · observe · cancel · cleanup · prove zero survivors             │
│              │                                  │                            │
│              ▼                                  ▼                            │
│          Ictinus ───── typed artifact/event ─────► Hefesto                   │
│       read-only design                         bounded writer                 │
│              │                                  │                            │
│              └──────── other admitted Daimons ──┘                            │
└────────────────────────────────┬──────────────────────────────────────────────┘
                                 │ result artifacts and runtime evidence
                                 ▼
┌────────────────────────────── EVIDENCE PLANE ─────────────────────────────────┐
│ Kernel verifier · immutable snapshots · receipts · test output · cleanup proof│
└────────────────────────────────┬──────────────────────────────────────────────┘
                                 │ milestones / blocker / final projection
                                 ▼
                              Hermes
```

### 5.1 Why this is not hub-and-spoke

A central component does not by itself create the rejected topology. The rejected topology requires a reasoning/message hub that receives, interprets, and retransmits every edge.

In this design:

- Hermes submits the contract once;
- Ictinus' accepted result becomes a verifier-owned immutable snapshot;
- the kernel releases Hefesto automatically from the declared dependency;
- Hefesto consumes the snapshot without Hermes reading, summarizing, or copying it;
- technical retries follow contract policy without Hermes selecting the worker again;
- Hermes receives only milestones, a material escalation, or the final projection.

The kernel acts as a transactional authority and broker, not a conversational manager. Harmonia acts as a bounded coordinator, not a second Hermes.

### 5.2 Why this is not unrestricted peer-to-peer

Daimons do not receive ledger signing keys, amend contracts, invent unbounded tasks, invoke arbitrary peers, or grant permissions through text. All lateral communication is:

- tied to one contract generation;
- addressed to an admitted task or role;
- limited to an allowed message kind;
- constrained to existing scope and budget;
- recorded durably;
- ineffective as an authority grant;
- validated before it can release work.

This preserves autonomy of execution without decentralizing product meaning.

## 6. Authority ownership

| Fact or action | Sole authority | Proposal/input sources | Forbidden duplicate authority |
|---|---|---|---|
| Product intent and material outcome | User, interpreted by Hermes | Specialists may recommend | Harmonia, kernel, Daimons |
| Active execution contract | Kernel ledger; Hermes is amendment principal | Hermes proposes | Worker text, UI state, Harmonia preference |
| Effective participant policy | User/project policy resolved into contract snapshot | Hermes and project defaults | Peer proposal or fallback |
| Task graph and bindings | Active contract generation | Hermes; later bounded task proposals | Runtime session or worker prompt |
| Eligibility | Kernel-derived projection | Harmonia may propose candidate ID | Worker self-selection |
| Selection commit | Kernel CAS event | Harmonia task-only proposal | Hermes relay or ACP adapter |
| Task specialist content | Bound Daimon | Handoff artifacts and project source | Harmonia |
| Artifact trust | Kernel verifier and receipt | Worker supplies result bytes | Worker completion prose |
| ACP process/session | Olympus / `ACPManager` | Kernel dispatch intent | Harmonia or worker |
| Technical closure | Kernel after evidence and cleanup | Olympus terminal observation | Agent's `done` text |
| Product completion proposal | Hermes | Kernel projection and project evidence | Kernel or Daimon |
| Final acceptance | User | Hermes recommendation | Any technical terminal state |

## 7. Participant-policy model

### 7.1 Effective states

| State | Meaning | Runtime behavior |
|---|---|---|
| `required` | A named task or gate requires this Daimon. | Admission fails or escalates if unavailable; no silent substitute. |
| `allowed` | Aether may use the Daimon when expected value exceeds cost. | Eligible only when included by the admitted contract. |
| `disabled` | The user does not want automatic use. | Excluded from selection, fallback, retry, recovery, peer proposals, and equivalent-role substitution. |
| `forbidden` | The Daimon must not participate in the applicable scope. | Any direct or indirect invocation is an authority violation and fails closed. |

### 7.2 Precedence

The resolver applies the approved order:

1. current explicit user instruction;
2. project-specific policy;
3. run or contract policy;
4. durable approved user preference;
5. product default;
6. agent recommendation.

A lower layer cannot re-enable a higher-layer `disabled` or `forbidden` state. The admitted contract stores the effective snapshot and provenance used at admission so restart behavior cannot drift with later configuration changes.

### 7.3 Enforcement points

The same policy decision must be enforced at:

1. public contract parsing;
2. contract compilation;
3. worker discovery resolution;
4. task binding;
5. eligibility projection;
6. Harmonia proposal validation;
7. kernel selection commit;
8. dispatch staging;
9. retry and recovery;
10. fallback or equivalent-role substitution;
11. peer-proposed consultation or review;
12. restart reconstruction.

Enforcement at only the prompt or only the first dispatch is insufficient.

### 7.4 Initial Aether project policy

The first pilot uses the smallest justified roster:

| Participant | Effective pilot state | Reason |
|---|---|---|
| Ictinus | `required` for architecture task | Produces a distinct read-only backend boundary recommendation. |
| Hefesto | `required` for implementation task | Owns the bounded code change and tests. |
| Daedalus | Not admitted | No UX contribution exists in the selected task. |
| Ariadna | Not a workflow worker | Remains limited to supported continuity curation. |
| Athena | `forbidden` | Current explicit owner policy excludes her until reactivation. |
| Etalides | `disabled` and no new dependency | The project is preparing to discontinue this role. |
| Hermes | Contract/amendment/completion authority, not worker | Preserves product intent and acceptance. |
| Harmonia | Coordinator, not worker | Cannot appear as a task participant. |

This table is project policy for the pilot, not a universal product default.

## 8. Contract model

### 8.1 Run contract

The existing `ExecutionContract` remains the authority envelope and evolves compatibly. A complete admitted run records:

- immutable `contract_id`, `project_id`, and `generation`;
- accountable owner, completion authority, and amendment authority;
- objective and expected product-independent technical outcome;
- global included and excluded scopes;
- effective participant-policy snapshot with provenance;
- exact task definitions and worker bindings;
- role permissions;
- evidence and independent gate requirements;
- side-effect policy;
- time, model, QA, recovery, attempt, graph, and concurrency limits;
- escalation conditions;
- source-tree snapshot digest;
- revocation epoch;
- supported selection policy, when any.

The caller proposes product-meaningful values. The server derives installation identity, project identity, contract identity, signing data, session identity, fences, message IDs, artifact paths, and verifier metadata.

### 8.2 Task contract

Every task must have a self-contained semantic brief. The target task definition is:

```text
TaskContract
  task_id
  worker_id or bounded candidate set
  role
  objective
  expected_outcome
  included_scopes       subset of run scope
  excluded_scopes
  permissions
  prerequisites
  required_inputs       artifact/message references
  result_schema
  acceptance_checks
  evidence_requirements
  write_scope           empty for consultants
  attempt_limit
  escalation_conditions
```

The current `HarmoniaTaskSpec` lacks `objective`, `expected_outcome`, and task-specific scope. Those fields are required before a real Ictinus-to-Hefesto task can be considered semantically self-contained.

### 8.3 Permission vocabulary

The contract uses a bounded semantic vocabulary rather than arbitrary strings:

- `read_project`;
- `return_evidence`;
- `write_scoped_files`;
- `run_focused_tests`;
- `run_full_tests`;
- `network_read`;
- `external_effect`.

Availability of a toolset does not grant these permissions. `external_effect` remains denied by default and additionally requires an allowed effect kind and product-owner authority where applicable.

### 8.4 Amendments

A material contract change creates generation `N+1` and increments the revocation epoch. It never mutates generation `N` in place.

An amendment must:

- be issued by the contract amendment authority;
- state rationale and affected tasks/identities;
- invalidate stale dispatch authority;
- preserve historical events;
- reconcile any possibly accepted effect before redispatch;
- re-resolve participant policy when the amendment changes participants;
- return to the user only when the amendment has a product-material consequence.

## 9. Worker envelope and semantic result

### 9.1 Dispatch envelope

The kernel sends canonical JSON, not an unconstrained relay prompt. The next envelope version contains:

- authority identity and generation;
- exact task brief;
- effective worker permissions;
- project root and scoped paths;
- limits and side-effect policy;
- acceptance checks;
- required input artifact references;
- expected result document;
- non-authority instructions.

The prompt digest is bound to durable dispatch authority before the external ACP effect.

### 9.2 Typed task result

`AETHER_TASK_RESULT_V2` separates technical session status from semantic task outcome:

```text
semantic_outcome:
  completed | blocked | clarification_required | failed
summary:
  concise bounded result
deliverables:
  typed artifact references or changed-scope claims
evidence:
  commands, checks, outputs, or verifier references
findings:
  bounded observations relevant to the task
deviations:
  named departures from the task contract
requests:
  typed consultation, review, correction, or clarification proposals
```

Exact identity, path, generation, message, and session fields remain kernel-owned. Free text may explain a result but cannot grant authority, add participants, expand scope, waive evidence, or amend the contract.

### 9.3 Consultant and writer delivery

- **Read-only consultant:** returns exactly one structured JSON result through ACP. The kernel materializes the result artifact using authenticated dispatch identity.
- **Writer:** modifies only the admitted write scope, executes required verification, then atomically writes the kernel-specified result document.
- **Verifier/reviewer:** returns a typed verdict and findings; it does not write implementation files or self-approve its own prior work.

## 10. Lateral communication model

### 10.1 Direct means semantic directness

A Daimon-to-Daimon handoff is direct when the producer addresses or releases a contract-bound successor and the successor consumes the original verified artifact without Hermes interpretation. The kernel may transport and validate the exchange without becoming a reasoning relay.

### 10.2 Allowed message kinds

The target message family is intentionally small:

| Kind | Purpose | Can release work? |
|---|---|---|
| `dependency_handoff` | Transfer a verified prerequisite result. | Yes, when declared in the contract. |
| `consultation_request` | Request bounded specialist analysis. | Only if participant, scope, and task family are pre-authorized. |
| `review_request` | Ask an independent role to assess a named artifact/gate. | Only for an admitted review task. |
| `correction_request` | Return evidenced findings to the accountable owner. | Only within attempt and correction budget. |
| `clarification_request` | Pause for missing authority or information. | No; it creates a blocker projection. |
| `blocker_report` | Report inability to proceed safely. | No. |
| `subtask_proposal` | Suggest a derived task. | Never directly; the kernel must validate or escalate. |

### 10.3 Message envelope

Every lateral message records:

- contract ID, generation, and revocation epoch;
- run ID and message ID;
- sender task/attempt and recipient task/role;
- message kind;
- scope digest;
- referenced artifact receipts;
- required response kind;
- remaining budget/attempt context;
- creation and consumption events.

Workers do not sign ledger events directly. They submit structured results through their authenticated ACP session; the kernel validates and records the resulting event.

### 10.4 First increment boundary

The first live increment supports only `dependency_handoff`, generated from a verified predecessor receipt. General consultation, review, correction, and subtask messages remain target design until the fixed path is operationally healthy.

No retired Cotal-inspired protocol or transport module is restored merely to provide these message names.

## 11. Workflow and state machines

### 11.1 Run lifecycle

```text
PROPOSED
  -> ADMITTED
  -> ACTIVE
  -> TECHNICAL_COMPLETION_PROPOSED
  -> TECHNICALLY_CLOSED

Alternative terminal/control states:
  BLOCKED
  FAILED
  CANCELLED
  RECONCILIATION_REQUIRED
```

`TECHNICALLY_CLOSED` means the contract graph, evidence, and cleanup obligations are satisfied. It does not mean the user accepted the product outcome.

### 11.2 Task lifecycle

```text
PROPOSED
  -> BLOCKED_ON_PREREQUISITES
  -> READY
  -> DISPATCH_STAGED
  -> RUNNING
  -> RESULT_SUBMITTED
  -> EVIDENCE_VERIFIED
  -> CLEANUP_PENDING
  -> CLOSED
```

Controlled branches:

```text
RUNNING -> CLARIFICATION_REQUIRED -> AMENDED/RESUMED or CANCELLED
RUNNING -> FAILED -> CORRECTION_READY or CLOSED_FAILED
ANY EFFECT BOUNDARY -> RECONCILIATION_REQUIRED
```

Task `CLOSED` must expose its semantic outcome (`completed`, `blocked`, `failed`, or `cancelled`) rather than treating cleanup completion as successful work.

### 11.3 Attempt lifecycle

One logical task may have multiple attempts, but only one live fenced attempt:

```text
ACTIVE -> COMPLETED
       -> ORPHANED
       -> SUPERSEDED
       -> FAILED
       -> CANCELLED
```

A retry requires:

- a classified failure;
- remaining attempt and recovery budget;
- no unknown accepted effect;
- cleanup or supersession of the prior attempt;
- the same worker binding unless the contract explicitly authorizes substitution;
- a new fence and message identity.

### 11.4 Graph closure

A run can close only when:

1. every required task is semantically terminal;
2. every required edge has a consumed, verifier-bound handoff;
3. every required gate passed or carries a valid typed waiver;
4. no active, unknown, or reconciliation-required effect remains;
5. every ACP session has verified cleanup;
6. no writer lease or process survivor remains;
7. no unhandled material blocker remains;
8. the final projection can be rebuilt from the ledger alone.

## 12. Scheduling, selection, and concurrency

### 12.1 Deterministic first

The initial scheduler supports only:

1. one task;
2. one fixed sequential two-task handoff;
3. the already-validated bounded choice between exactly two declared successors.

Harmonia may propose a task ID only from the kernel-derived eligible set. The kernel recomputes eligibility, validates participant policy and bindings, and commits one winner through CAS.

### 12.2 No planner authority

An LLM planner is not presumed. If introduced later:

```text
planner -> typed proposal
kernel  -> re-derive, validate, commit or reject
Olympus -> execute
```

The planner cannot become a task in its own graph, amend the contract, sign the ledger, own lifecycle, accept evidence, or approve product completion.

### 12.3 Parallelism

Parallel execution is admitted only when:

- tasks have no unmet dependency;
- write scopes are disjoint;
- shared resources have an explicit coordination rule;
- the contract concurrency budget permits it;
- one accountable owner exists for each deliverable;
- final integration has a named owner.

Read-only tasks may run in parallel when their context and budget permit it. Two agents never write the same scope concurrently.

### 12.4 Bounded graph expansion

Later graph expansion may admit a proposed task only when all of the following are deterministic:

- task family is pre-authorized;
- participant is effectively `required` or `allowed`;
- scope is a subset of the active contract;
- no forbidden effect or permission is introduced;
- node, depth, concurrency, attempt, and budget limits remain available;
- prerequisites reference existing tasks and cannot create a cycle;
- the accountable owner and acceptance gate are explicit.

Otherwise the proposal is rejected or escalated; it never mutates the graph by model assertion.

## 13. Failure, recovery, and takeover

| Failure point | Durable interpretation | Required response |
|---|---|---|
| Before admission | No coordinator authority exists. | Reject with zero store/run/session effects. |
| After admission, before dispatch | Kernel owns a durable run; no worker effect. | Stop semantically, close run, then permit direct work. |
| Dispatch not accepted | Retry only under the same fenced authority and budget. | No duplicate worker. |
| Acceptance may have occurred | External outcome is `UNKNOWN`. | Reconcile exact session/effect before retry. |
| Worker reports blocker | Semantic blocker, not infrastructure failure. | Route bounded clarification or escalate once. |
| Worker output invalid | Evidence failure. | Preserve artifact, clean session, classify worker/contract/framework defect. |
| Source task fails | Successor remains blocked. | No handoff and no implicit bypass. |
| Cleanup cannot be proved | `RECONCILIATION_REQUIRED`. | Do not claim closure or start overlapping writer. |
| Runtime restart | Ledger is authoritative. | Rebuild projections, resume monitors, stage only committed eligible work. |
| Framework defect inside Aether | Dogfood failure evidence. | Repair minimally, verify, and retry the same Harmonia contract. |
| Harmonia unavailable in another project | Framework route unavailable. | Complete that project directly; do not mutate Aether incidentally. |

Direct Hermes takeover follows:

```text
COORDINATOR_ACTIVE
  -> TAKEOVER_REQUESTED
  -> RECONCILING
  -> CLEANUP_VERIFIED
  -> HERMES_DIRECT
```

There is no hidden `talk_to` fallback. Internal `ACPManager` use by Olympus is retained because lifecycle substrate is not the legacy orchestration surface.

## 14. Evidence and acceptance

### 14.1 Evidence layers

1. **Worker result:** specialist-authored structured content.
2. **Artifact verification:** kernel-owned identity, schema, path, digest, size, and generation checks.
3. **Runtime evidence:** authenticated ACP session binding and terminal observation.
4. **Cleanup evidence:** persisted proof of zero session/process survivors.
5. **Project verification:** tests, build, lint, diff review, and user-visible behavior.
6. **Product synthesis:** Hermes compares the integrated result against the preserved intent.
7. **Final acceptance:** the user accepts, rejects, redirects, or accepts named deviations.

A worker's completion prose cannot substitute for any later layer.

### 14.2 Write-scope evidence

For writer tasks, the kernel contract captures a source snapshot digest and allowed path set. Acceptance compares the resulting changed-path set against that scope. A scope violation fails the task even when tests pass.

The first pilot may perform this comparison in deterministic post-run verification if Hermes Agent cannot yet sandbox subpaths. The enforcement level must be reported honestly; prompt-only scope control is not described as a sandbox.

### 14.3 Independent gates

The implementer cannot be the sole acceptance authority for critical work. The first maintenance pilot uses:

- Ictinus for the architecture artifact;
- Hefesto for implementation and self-verification;
- deterministic tests and Hermes diff review for acceptance.

Athena is not used or replaced by a renamed security reviewer.

## 15. Public MCP and internal boundaries

### 15.1 Public `harmonia` surface

The first approved increment retains three actions:

- `start` — submit one immutable contract;
- `status` — read one durable projection;
- `stop` — request cancellation/cleanup or reconciliation.

The schema must express mutually exclusive contract variants exactly:

1. single worker;
2. fixed two-task chain;
3. bounded three-task selection topology.

Selection fields are required only for variant 3. The parser and MCP schema must accept and reject the same request set.

### 15.2 Later control actions

A future material clarification flow may justify an authenticated `amend` action. It is not added until a live run demonstrates the need. General worker messaging does not belong on Hermes' public control surface.

### 15.3 Internal API boundaries

Before broadening topology, replace current private access with narrow operations such as:

- read contract/store counts through ledger queries;
- derive dispatch authority through dispatcher public methods;
- append service-owned control events through a kernel command boundary;
- register successor-release hooks through an explicit runtime interface;
- expose writer context only inside kernel-owned transaction services.

These changes preserve behavior and reduce dual-authority risk; they are not a new coordinator.

## 16. Projections and user experience

### 16.1 Default projection to Hermes

The normal projection includes:

- run objective and current stage;
- admitted participants and effective policy;
- current accountable task owner;
- completed milestones;
- material blocker or escalation;
- evidence summary;
- cleanup/reconciliation state;
- final technical outcome and known deviations.

It excludes raw prompts, hidden reasoning, credentials, lease tokens, and routine poll chatter.

### 16.2 Drill-down projection

On demand, Aether may expose:

- complete task graph and states;
- worker bindings and attempts;
- typed lateral messages;
- artifact and receipt digests;
- tests and evidence;
- budgets, latency, model usage, and estimated cost;
- retries and recovery decisions;
- complete append-only event history.

Any future UI remains a projection/command surface; it never owns a competing task or completion state.

## 17. Security and trust boundaries

The target preserves these controls:

- coordination keys remain environment-provided and never enter YAML, MCP payloads, logs, prompts, or artifacts;
- workers never receive ledger writer or integrity keys;
- project roots are canonical, existing, exact-allowlisted directories;
- artifact paths are kernel-derived and symlink/path-escape safe;
- result sizes and nesting are bounded;
- dispatch identity is tied to contract generation, revocation epoch, plan revision, snapshot digest, task, attempt, message, and session;
- outbox effects use intent-before-effect ordering and fencing;
- external effects are denied by default;
- free text cannot grant authority;
- disabled or forbidden roles cannot be reached through fallback, aliases, or peer proposals;
- status projections redact secrets and internal authority tokens;
- no cleanup claim is accepted without zero-survivor proof;
- unknown effects fail closed.

The design does not claim OS-level subpath sandboxing where only post-run scope verification exists.

## 18. Initial vertical pilot: Ictinus to Hefesto

### 18.1 Objective

Use the architecture to improve its own maintained kernel baseline, not to run a synthetic demo.

### 18.2 Real task

Replace one selected private `ledger.conn` read in `harmonia_service.py` with a narrow public ledger query while preserving behavior.

### 18.3 Task A — Ictinus

- **Role:** read-only backend architect.
- **Scope:** selected service query, ledger authority boundary, neighboring tests.
- **Permissions:** `read_project`, `return_evidence`.
- **Deliverable:** structured recommendation containing the narrow public API, invariants, affected caller, tests, trade-off, and explicit non-goals.
- **No writes:** Ictinus cannot modify source or documentation.
- **Semantic acceptance:** the artifact is sufficiently precise for implementation without Hermes rewriting it.

### 18.4 Automatic handoff

After Ictinus completes:

1. Olympus reports technical terminal state;
2. the kernel materializes and verifies Ictinus' structured result;
3. the verifier publishes an immutable snapshot and receipt;
4. cleanup is proven;
5. the fixed prerequisite edge becomes satisfied;
6. the kernel stages Hefesto exactly once;
7. Hefesto receives the original verified artifact reference.

Hermes does not read, summarize, copy, select, or redispatch between tasks.

### 18.5 Task B — Hefesto

- **Role:** accountable implementation owner.
- **Scope:** the selected ledger API, service consumer, and focused regression tests.
- **Permissions:** `read_project`, `write_scoped_files`, `run_focused_tests`, `return_evidence`.
- **Required input:** Ictinus' verifier-bound handoff snapshot.
- **Deliverable:** minimal implementation, focused tests, exact commands/results, deviations, and blocker state.
- **Non-goals:** broad ledger decomposition, configuration migration, topology expansion, provider/model changes, release, or activation.

### 18.6 Independent acceptance

Hermes verifies:

- changed paths stay within scope;
- the new public API owns the query correctly;
- no private access remains at the selected call site;
- tests meaningfully exercise behavior rather than implementation trivia;
- focused and affected coordination tests pass;
- the run closes with two evidence receipts and zero survivors;
- no `talk_to` or manual relay occurred.

### 18.7 Pilot success counters

```text
Hermes contract submissions:                  1
Hermes routine result relays after admission: 0
Hermes next-agent selections after admission: 0
Hermes retry dispatches after admission:      0
Ictinus verified artifacts:                  >=1
Kernel automatic prerequisite releases:     >=1
Hefesto bounded implementations:              1
Legacy fallback invocations:                  0
Scope violations:                             0
Unknown effects at close:                     0
Surviving sessions/processes:                 0
```

A single-worker Hefesto run may be used only as an isolated health smoke. It does not satisfy this pilot or prove the target architecture.

## 19. Incremental delivery boundary

### 19.1 Candidate v0.20.1

The proposed first candidate is a compatible correction and use-first validation:

1. resolve public schema/parser parity (#133);
2. add the minimum task-specific brief/result semantics needed for a real fixed handoff;
3. adapt Ictinus and Hefesto profiles to kernel dispatch and handoff consumption;
4. replace only the public/private boundaries required to execute the pilot safely;
5. execute the real Ictinus-to-Hefesto pilot;
6. repair any observed Aether framework defect and retry the same contract;
7. preserve default-off configuration and project isolation;
8. publish no release claim until the exact candidate tree passes deterministic and live gates.

The current maintenance audit remains authoritative about retained and retired code. If this design is approved, it supersedes only the audit's sequencing recommendation that all private-boundary cleanup must finish before any new coordination work. Maintenance instead proceeds vertically through real Harmonia use. It does not restore retired laboratories or waive their removal evidence.

### 19.2 Later increments

Later versions are evidence-driven, not pre-reserved. Candidate signals may include:

- uniform four-state participant-policy enforcement;
- typed consultation/review/correction messages;
- bounded task proposals;
- safe disjoint parallelism;
- richer graph closure;
- a planner proposal boundary;
- production migration or global activation.

Each requires a separate falsifiable hypothesis and cannot be inferred from the v0.20.1 pilot.

## 20. Evaluation

The architecture is valuable only if it improves software production, not merely coordination internals.

### 20.1 Operational metrics

- Hermes relay count;
- user coordination actions;
- task and run latency;
- model/token cost by role;
- duplicate dispatches;
- scope violations;
- retry/recovery count;
- unknown effects;
- cleanup survivors;
- context passed between specialists;
- percentage of projections reconstructed from the ledger.

### 20.2 Product-quality metrics

- scope fidelity;
- correctness and regressions;
- architecture quality;
- maintainability;
- verification sufficiency;
- documentation coherence;
- user corrections and rework;
- final user acceptance.

### 20.3 Baseline

For representative tasks, compare:

```text
A: direct strong general agent / Hermes execution
B: Aether contract-governed specialist workflow
```

Use equivalent starting trees, prompts, models where meaningful, and acceptance rubrics. Aether wins only when quality gain and reduced user coordination justify its extra runtime cost.

## 21. Rejected alternatives

### 21.1 Hermes hub-and-spoke

Rejected because Hermes remains an expensive message bus, every handoff is serialized through one context, and specialists cannot advance an approved chain autonomously.

### 21.2 Pure peer-to-peer swarm

Rejected because agents could create tasks, invoke roles, expand scope, and produce conflicting authority without a durable contract.

### 21.3 Harmonia as an LLM manager

Rejected because it would replace one reasoning hub with another and blur product, semantic, and lifecycle authority.

### 21.4 Shared mutable multi-writer workspace

Rejected because concurrent agents can overwrite or invalidate each other's work and make provenance unverifiable.

### 21.5 Restore retired protocol/transport laboratories

Rejected because they had no current server consumer and would create a second identity, message, capability, or workflow authority.

### 21.6 Arbitrary DAG and open-ended planning first

Rejected because the fixed handoff already exercises the target authority split with much smaller failure and debugging surfaces.

### 21.7 Fixed full-team lifecycle

Rejected because agent count is not a quality metric and mandatory specialists recreate autonomous bureaucracy.

### 21.8 Hidden legacy fallback

Rejected because it masks Harmonia defects and prevents causal evidence that the replacement path works.

## 22. Approval package

Approval of this design means the product owner accepts these architecture consequences:

1. Hermes remains product-intent and final-synthesis authority but leaves routine message transport after contract admission.
2. The kernel/ledger remains a central deterministic authority; the system is not a free peer-to-peer swarm.
3. Daimons collaborate laterally through typed, durable artifacts/events rather than unbounded direct chat.
4. User-controlled participant states are enforced on every selection, fallback, retry, and recovery path.
5. Harmonia coordinates but cannot become product authority, domain worker, mandatory relay, or ACP lifecycle owner.
6. Olympus remains the sole ACP lifecycle owner.
7. The first valid proof is a real `Ictinus -> Hefesto` maintenance handoff with zero routine Hermes relay and zero survivors.
8. v0.20.1 remains default-off and project-isolated; global activation, broader topology, dynamic hiring, and release remain separate gates.

Approval does **not** authorize implementation automatically. The next explicit gate would be authorization to implement the bounded v0.20.1 candidate from a clean, isolated branch/worktree.

## 23. Approval criteria

Promote this document from `PROPOSED` to `APPROVED TARGET` only when the product owner confirms that:

- centralized product intent plus lateral specialist execution is the intended operating model;
- a deterministic kernel is acceptable even though Hermes hub-and-spoke is not;
- durable typed artifacts/events are the preferred first collaboration mechanism;
- the proposed authority boundaries are correct;
- the first Ictinus-to-Hefesto pilot is representative enough to authorize implementation.

If any item is rejected, preserve this document as a proposal and record the requested product-level correction before implementation planning.

## 24. References

- [`../product/VISION.md`](../product/VISION.md)
- [`../product/PRINCIPLES.md`](../product/PRINCIPLES.md)
- [`../product/OBJECTIVES.md`](../product/OBJECTIVES.md)
- [`../product/SCOPE.md`](../product/SCOPE.md)
- [`../product/EXPERIENCE.md`](../product/EXPERIENCE.md)
- [`../knowledge/AUTHORITY.md`](../knowledge/AUTHORITY.md)
- [`../knowledge/MULTI_AGENT_MODEL.md`](../knowledge/MULTI_AGENT_MODEL.md)
- [`../knowledge/SELF_IMPROVEMENT_CYCLE.md`](../knowledge/SELF_IMPROVEMENT_CYCLE.md)
- [`../decisions/PDR-0004-product-owner-authority-and-bounded-autonomy.md`](../decisions/PDR-0004-product-owner-authority-and-bounded-autonomy.md)
- [`../decisions/PDR-0005-multi-agent-participation-and-coordination.md`](../decisions/PDR-0005-multi-agent-participation-and-coordination.md)
- [`../decisions/PDR-0008-canonical-definition-and-project-completion.md`](../decisions/PDR-0008-canonical-definition-and-project-completion.md)
- [`../decisions/PDR-0009-semver-self-improvement-cycle.md`](../decisions/PDR-0009-semver-self-improvement-cycle.md)
- [`../releases/v0.19.x-kernel-migration/ROADMAP_CLOSEOUT.md`](../releases/v0.19.x-kernel-migration/ROADMAP_CLOSEOUT.md)
