# Hermes–Orca Swarm Operating Model

> **Status:** APPROVED MODEL; BOUNDED PROVIDER EXECUTION QUALIFIED; PRODUCTION NOT ACTIVATED
> **Date:** 2026-08-06
> **Authority:** PDR-0012, PDR-0013, PDR-0014, and ADR-0001
> **Current truth:** The exact Orca path is accepted through bounded M5.4 evidence, but Aether MCP remains zero-tool/unregistered; Hermes performs real work directly until the v0.23.0 production-entry gate passes.

## Product experience

The user designs and evaluates software through Hermes. The user does not need
to operate Aether MCP or Orca CLI, allocate terminals, create worktrees, route
Daimons, or reconcile worker output.

```text
User describes desired product outcome
  -> Hermes discovers material intent
  -> Hermes establishes a bounded contract
  -> Hermes chooses direct work or a swarm
  -> Hermes validates and supervises the swarm through Aether MCP
  -> Aether MCP invokes version-pinned public Orca operations
  -> workers produce artifacts and evidence
  -> Hermes reviews, integrates, verifies, and synthesizes
  -> user accepts, redirects, or rejects
```

Aether MCP is the target typed control and trace boundary behind Hermes. Orca
remains the operational control plane below that boundary, not a second product
conversation.

## Ownership boundary

| Concern | Owner |
|---|---|
| Product intent, visible behavior, material compromise, final acceptance | User |
| Requirements interpretation, task contract, routing, participant admission, synthesis | Hermes |
| Daimon identities, roles, profiles, participation policy, verification doctrine | Aether product artifacts |
| MCP schema, validation, idempotency, correlation, declared rationale, receipts, semantic trace, protected learning episodes/dataset lineage | Aether MCP |
| Run, Task, Dispatch, worker, terminal, worktree, message, retry, recovery state | Orca |
| Specialist judgment inside a bounded Task | Admitted worker/Daimon |
| Technical evidence and findings | Worker, tools, and future Independent Verifier |
| Integrated semantic acceptance proposal | Hermes |
| Release, activation, deployment, migration, credentials, spending | Separately authorized owner/gate |

No Orca status can redefine product meaning or final acceptance.

## Path selection

### Direct path

Hermes uses the direct path when one accountable owner can produce equivalent quality with less coordination.

```text
contract -> Hermes acts -> focused verification -> user-facing result
```

Typical cases:

- precise edits;
- focused diagnostics;
- bounded documentation;
- low-risk configuration correction;
- small bugs with a known affected area.

### Swarm path

Hermes uses the swarm only when distinct specialist judgment, independent review, sustained implementation, or safe parallelism is expected to improve the result more than its cost.

```text
contract
  -> participant selection
  -> Aether MCP manifest validation
  -> one Orca Run
  -> Task DAG
  -> Dispatch attempts and workers
  -> messages/questions/evidence
  -> review and integration
  -> cleanup
  -> user-facing result
```

A large repository, long conversation, or available profile does not by itself justify a swarm.

## Phase 1 — Product contract

Hermes translates the user's vision into a contract before dispatching work.

Minimum contract fields:

- concrete objective;
- observable user outcome;
- acceptance criteria;
- non-goals;
- material decisions already frozen;
- relevant constraints and user preferences;
- authorized effects and protected boundaries;
- verification expectations;
- stop condition;
- rollback or handoff expectation when relevant.

Hermes asks the user only when ambiguity changes product meaning, material compromise, consequence, or authority. Routine technical choices remain internal.

## Phase 2 — Team and Task graph

Hermes determines:

1. whether direct work is sufficient;
2. which distinct specialist contributions are needed;
3. effective participant policy for each archetype;
4. one deliverable and accountable owner per Task;
5. Task dependencies and readiness;
6. exact read/write scope;
7. worktree placement and conflict risk;
8. model/tool/data boundaries;
9. evidence and completion requirements;
10. retry and stop budgets.

Example:

```text
Task A — Experience flow
  owner: Daedalus
  dependencies: none
  output: accepted flow/states artifact

Task B — Data/API constraints
  owner: Ictinus
  dependencies: none
  output: architecture review

Task C — Backend implementation
  owner: Hefesto worker A
  dependencies: Task B
  write scope: backend/onboarding/**

Task D — Frontend implementation
  owner: Hefesto worker B
  dependencies: Task A, Task B
  write scope: frontend/onboarding/**

Task E — Integrated verification
  owner: future Independent Verifier
  dependencies: Task C, Task D
  output: verification review

Hermes — integration and semantic synthesis
```

Tasks A and B may start together. Tasks C and D wait for their dependencies. Several Tasks may use the same archetype without creating new personalities.

## Phase 3 — Aether MCP validation and Orca materialization

The target product sequence is conceptually:

```text
swarm_validate
  -> swarm_start
  -> swarm_status / swarm_dispatch for newly ready Tasks
  -> swarm_message for admitted communication
  -> swarm_reconcile for ambiguous or incomplete effects
  -> swarm_retry only after classified failure and fencing
  -> swarm_trace(action=record_evidence|record_decision)
  -> swarm_close
  -> swarm_trace(action=query) for timeline, explanation, metrics, and integrity
```

The MCP translates those stable Aether operations into the exact
version-matched public Orca Run/Task/Dispatch/worker/message/recovery/cleanup
operations. Bounded diagnostic coverage is available through `orca_search`,
`orca_describe`, and `orca_call`. Independent batching and eventual observation
are internal adapter capabilities rather than separate Hermes tools. The four
learning operations remain a later separate default-off boundary. No tool accepts
free-form shell strings.

The exact schemas are proposed in `../reference/AETHER_MCP_CONTRACT.md`. They are
not an active integration and this document does not authorize execution.

### Run

One Run represents one feature effort or bounded coordinated objective. It provides operational namespace, coordinator inbox, Tasks, Dispatches, and durable messages.

A Run does not own product intent or acceptance.

### Task

Each Task contains or references:

- Hermes contract/task identity;
- assigned archetype/profile;
- exact deliverable;
- dependencies;
- read/write scope;
- evidence and technical completion requirements;
- budget and retry limit;
- placement expectation.

### Dispatch

A Dispatch is one attempt at one Task. A retry creates a new Dispatch linked to the prior attempt. The prior attempt is fenced and cannot continue mutating current work.

`outcome_unknown` remains unknown. It must not be inferred as success from process exit, silence, or partial files.

### Worker

A worker is one profile-bound Hermes process executing one admitted Task. Workers cannot create Tasks, start children, admit participants, amend the contract, merge independently, or release.

## Phase 4 — Placement and write safety

A feature effort has one integration branch. That does not require every writer to use one checkout.

Hermes chooses placement:

- read-only consultants need no writable integration scope;
- disjoint writers may share a checkout only when file ownership is explicit and conflict risk is negligible;
- potentially overlapping writers require separate Orca child worktrees;
- every writer has one exact write scope;
- workers never force-push, rewrite shared history, or merge/release independently.

Orca owns worktree mechanics. Hermes owns conflict prevention and deterministic
integration; Aether MCP validates the declared placement/scope before invoking
Orca and records the resulting binding without becoming worktree authority.

## Phase 5 — Parallel execution and supervision

Hermes creates and starts all ready independent work before waiting.

```text
Daedalus running ----\
                      +--> dependent implementation
Ictinus running -----/

Hermes continues product/integration work in parallel
```

Supervision through `swarm_status`, `swarm_reconcile`, and `swarm_trace` is
pull-based in the initial target:

- worker start returns after Dispatch acceptance;
- Hermes remains usable in the primary conversation;
- status reads are non-blocking by default;
- bounded waiting occurs only when useful or explicitly requested;
- no hidden LLM coordinator loop is presumed;
- no spontaneous TUI notification is promised until a public delivery seam is proven.

## Phase 6 — Worker communication

Workers may communicate directly through Orca for routine collaboration inside
the contract. Hermes sends, observes, and traces coordinator-side communication
through Aether MCP rather than direct CLI commands.
### Allowed message kinds

- `progress`;
- `artifact_reference`;
- `dependency_handoff`;
- `technical_question`;
- `reply`;
- `review_request`;
- `finding`;
- `blocker`;
- `completion_reference`.

### Recommended envelope

```text
run_id
sender_task_id + sender_dispatch_id
recipient task/dispatch/group
message_kind
concise summary
artifact/evidence references
requires_decision: true|false
blocking_effect: none|description
receipt identity and source time
protected full secret-redacted message content ref when FULL_EPISODE is admitted
```

### Authority rule

Free text cannot grant authority. A worker message cannot:

- add scope;
- amend the product contract;
- enable a disabled, forbidden, retired, or unavailable participant;
- approve a protected effect;
- waive required evidence;
- authorize integration, release, or activation.

### Escalation

Routine technical questions may be answered by Hermes or another admitted specialist within authority. Product-material questions go to Hermes. Hermes asks the user only when the user owns the consequence.

## Phase 7 — Technical completion and evidence

A worker reports one explicit outcome:

- succeeded;
- failed;
- blocked;
- cancelled;
- outcome unknown.

A completion report should include:

- exact Task and Dispatch attempt;
- outcome and uncertainty;
- changed files or produced artifacts;
- evidence references;
- tests/checks executed and results;
- known limitations;
- unresolved findings or questions;
- integration notes.

`worker_done` settles operational reporting. It moves the work to review; it is not product acceptance.

Terminal transcript prose is diagnostic context, not sufficient evidence. Hermes verifies repository bytes, artifacts, executed checks, and rendered outcomes where relevant.

## Phase 8 — Review, correction, and retry

Hermes evaluates every result against the contract.

Possible dispositions:

- accept technical result for integration;
- request bounded correction on the same live attempt when safe;
- create a new retry Dispatch after a classified failure;
- reject as out of scope or insufficient;
- ask for independent domain review;
- preserve unknown outcome and stop.

A retry must record lineage with `retry-of`, use a new Dispatch identity, fence the old attempt, preserve attempt-specific evidence, and remain within budget.

Repeated failure is evidence. After three materially identical failed approaches, Hermes stops and escalates the actual blocker rather than looping.

## Phase 9 — Integration and independent verification

Hermes owns deterministic integration into the feature branch:

1. inspect each diff and artifact;
2. verify scope ownership;
3. verify per-Task evidence;
4. reconcile commits or changes consciously;
5. resolve conflicts according to product intent;
6. run integrated affected behavior;
7. request domain review or the future Independent Verifier when justified;
8. compare the integrated result against the original user outcome.

The future Verifier produces independent evidence and findings. It does not implement silent fixes or replace Hermes/user acceptance.

## Phase 10 — User-facing synthesis

The default user view contains product information, not raw orchestration mechanics:

```text
Objective
Current meaningful stage
Completed outcomes
Active blockers or risks
Decisions requiring the user
Verified evidence summary
Known limitations
Next meaningful result or acceptance request
```

Run IDs, Dispatches, terminals, messages, retries, trace events, operation
receipts, raw diagnostic references, and detailed resource state remain
available through progressive Aether MCP inspection, not forced into the main
conversation.

The user may:

- accept the outcome;
- request a correction;
- change a product decision;
- reject the result;
- accept a disclosed limitation.

## Phase 11 — Cleanup

Completion requires more than stopping a worker. Hermes calls `swarm_close` and
must obtain evidence that every resource created for the Run has a known
disposition:
- worker process;
- agent terminal;
- setup terminal/process;
- worktree;
- temporary branch;
- pending question/message;
- active Dispatch;
- temporary runtime state;
- retained artifacts and evidence.

Zero survivors must be demonstrated or each retained resource must have an explicit authorized reason. Stop, failure, and cancellation all enter cleanup.

For Orca 1.4.167 this is a composed, non-atomic cleanup plus an Aether-owned
semantic closeout. The returned projection must report the actual Orca Run status
separately and may not claim an Orca-native Run-close transition. Any partial or
unknown resource disposition returns `BLOCKED`, `CLEANUP_FAILED`, or `UNKNOWN`,
never `CLOSED`.

## Failure semantics

| Observation | Meaning |
|---|---|
| no new message | no new message; not failure |
| worker process exited | process terminality; outcome still requires classification |
| partial files exist | partial artifact; not success |
| `worker_done: succeeded` | worker-reported technical outcome; review pending |
| test passed | one evidence item; product acceptance still pending |
| retry started | new attempt; old attempt must be fenced |
| stop acknowledged | worker stop only; aggregate cleanup still pending |
| runtime state uncertain | preserve uncertainty; do not infer cleanup or success |

## Current gaps before activation

The following remain unproven:

1. implemented and accepted successor Aether MCP operational contract;
2. implemented local MCP principal/project isolation and trace integrity;
3. reproducible isolated Orca cold start, restart, stop, and zero survivors;
4. version-pinned structured Aether-MCP-to-Orca provider translation;
5. profile-bound Hermes worker launch with explicit `HERMES_HOME`;
6. two parallel workers with separate safe write scopes;
7. worker-to-worker messaging and question/reply under policy;
8. participant-policy enforcement for required/allowed/disabled/forbidden;
9. privacy-safe lifecycle observation;
10. cold resume for terminated Hermes conversations;
11. spontaneous delivery into the primary Hermes TUI/session (not required for
    the polling-based initial contract);
12. cost/token/model accounting sufficient for Aether product reporting;
13. independent Verifier profile, benchmark, and execution;
14. Ariadna's distinct utility and safe data contract;
15. aggregate cleanup evidence under partial-start and failure cases.
16. trusted coordinator-terminal admission; R3 proves cold headless readiness but
    not a public standalone sender bootstrap.

Therefore activation remains `NO-GO`.

## Blocked future synthetic qualification sequence

The bounded R0-R6 task closed before the mechanics below could be accepted because
trusted coordinator admission remains unqualified. A future R5-R1 may validate
them only under a separate owner-authorized gate, without model credentials or
spending. MCP remains unregistered/default-off.

### Pilot A — one synthetic worker

- disposable repository;
- no credentials or remotes;
- one Run, Task, Dispatch, and profile-bound Hermes worker;
- question/reply;
- explicit outcome and evidence;
- stop and complete cleanup;
- zero survivors.

### Pilot B — two workers

- two independent Tasks started before waiting;
- separate write scopes/worktrees;
- direct worker message and dependency handoff;
- one controlled failure and `retry-of` lineage;
- integrated verification;
- cleanup after success, failure, and cancellation;
- zero survivors.

Only after the MCP lifecycle and these pilots pass may Aether claim qualified
synthetic orchestration mechanics. A real model-backed Daimon claim still requires
the separate provider/account/model/budget gate and its own executed evidence.

## Non-goals

This design does not authorize or require:

- a broad Aether coordination runtime or second operational ledger beyond the
  bounded MCP facade, semantic event index and protected non-operational learning
  episode/dataset store approved by ADR-0001;
- restoration of Olympus, ACPManager, Harmonia, `talk_to`, or hidden fallback;
- direct CLI-first Hermes control or arbitrary shell execution through MCP;
- a networked/remote MCP service in the first accepted implementation;
- dynamic personality creation;
- universal multi-agent participation;
- direct user management of Orca;
- runtime activation, profile launch, deployment, credentials, migration,
  spending, push, merge, rebase, amend, tag, or Release.
