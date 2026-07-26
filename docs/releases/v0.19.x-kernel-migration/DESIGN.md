# v0.19.x Incremental Kernel Migration — Design

**Status:** APPROVED DESIGN — IMPLEMENTATION AND LIVE EXECUTION NOT AUTHORIZED

**Design scope:** versioned experimental increments after the frozen v0.19.0 baseline. This document does not authorize implementation, live ACP execution, configuration changes, gateway restart, merge, tag, deployment or publication.

**Baseline authority:** `../v0.19.0-autonomous-coordination/RELEASE_CLOSEOUT.md`

## 1. Product hypothesis

Aether can replace Hermes' routine hub-and-spoke coordination with a durable kernel without removing Hermes as the user-facing strategic authority or Olympus as the ACP lifecycle owner.

The hypothesis is not considered true until a bounded real workflow completes with:

- one approved contract submitted by Hermes;
- kernel-owned admission, dispatch, handoff, evidence, recovery and closure;
- Olympus-owned process/session lifecycle;
- zero routine Hermes result relay, next-agent selection, correction dispatch or retry;
- a durable fault-injection record;
- a final verdict of `VIABLE`, `VIABLE WITH BLOCKERS` or `NOT VIABLE`.

## 2. Relationship to v0.19.0

v0.19.0 remains frozen and unchanged as:

> Experimental, default-off and not operationally validated.

The v0.19.x train does not retroactively claim that v0.19.0 replaced hub-and-spoke. Each increment is a new bounded experiment built from that baseline.

R8 `PilotStore` is historical blocked evidence. It is never a writable authority, fallback, projection or migration source for the kernel path.

## 3. Authority model

| Authority | Owns | Must not own |
|---|---|---|
| User | Product direction, architecture approval, external effects, activation and final waivers | Routine execution coordination |
| Hermes | User intent, contract preparation, architecture, authorization, escalations and final synthesis | Routine handoffs, next-agent selection after admission, result relay or hidden retry |
| Kernel | Admitted-run state, dispatch, task transitions, handoffs, evidence authority, recovery classification and closure | ACP process/session implementation or product decisions |
| Harmonia | Bounded plan proposals and next-task selection inside an approved contract when its patch is reached | Direct ACP calls, contract amendments, lifecycle, evidence acceptance or closure |
| Olympus/ACPManager | Processes, ACP sessions, cancel/close and lifecycle observations | Semantic task success, workflow admission or contract authority |
| Daimons | Role-bounded deliverables and evidence claims | Amending contracts, self-authorizing effects or self-passing independent gates |

## 4. Permanent invariants

1. Every run selects exactly one immutable runtime authority: `legacy` or `kernel`.
2. Kernel mode is persisted before the first external effect.
3. Legacy fallback is allowed only before kernel admission.
4. After admission, `UNKNOWN`, reconciliation and failures remain kernel-owned.
5. No ACP effect occurs before durable admission and dispatch staging.
6. `PilotStore` receives no writes from a kernel run.
7. The kernel writes one project-scoped ledger; there is no dual-write.
8. ACPManager remains the sole process/session lifecycle owner.
9. Technical ACP completion is not semantic completion.
10. Agent prose is not verifier evidence.
11. `CLOSED` requires trusted evidence and verified cleanup.
12. Harmonia may propose or select; only the kernel commits state and dispatch.
13. Stale workers cannot ACK, reconcile, complete, cancel or close after fence loss.
14. Disabling admission does not reinterpret or migrate existing kernel runs.
15. Every increment remains default-off and reversible by preventing new admissions.
16. No increment advances solely because unit tests are green.

## 5. Current and target paths

### Current operational path

```text
Hermes
  -> talk_to
  -> Olympus server
  -> ACPManager
  -> Daimon
  -> Hermes reads result and chooses the next action
```

### Target bounded path

```text
Hermes + user approve contract
  -> Hermes submits one kernel run request
  -> server-owned coordination composition
  -> project-scoped ledger
  -> KernelRunService
  -> KernelDispatcher
  -> OlympusRuntimeAdapter
  -> ACPManager lifecycle
  -> trusted evidence
  -> verified closure
  -> kernel selects/admits next bounded task
  -> Hermes receives escalation or final projection only
```

## 6. Experimental patch convention

The user selected a v0.19.x micro-patch train to make the migration observable and stoppable. This is an explicit experimental pre-1.0 versioning exception: increments may add default-off experimental capability, but they must not claim production readiness.

Each patch has exactly one operational hypothesis and the following lifecycle:

```text
PROPOSED
  -> DESIGN APPROVED
  -> IMPLEMENTATION AUTHORIZED
  -> DETERMINISTIC GREEN
  -> LIVE EXECUTION AUTHORIZED
  -> VALIDATED | BLOCKED | NOT VIABLE
  -> FROZEN
```

Approval of this design does not skip any later implementation or live-execution gate.

## 7. Approved six-patch sequence

The sequence deliberately separates trusted evidence from executable closure. Combining them would hide which authority failed.

| Patch | Single operational hypothesis | Exit evidence |
|---|---|---|
| v0.19.1 | One explicitly authorized task can traverse the real server-owned kernel composition into ACPManager. | Durable admission/dispatch/session binding through the actual composition seam; no semantic completion claim. |
| v0.19.2 | The single task can produce trusted, runtime-bound evidence that agent prose or stale state cannot forge. | Verifier receipt bound to exact run/task/attempt/contract/session/artifact generation. |
| v0.19.3 | A task with trusted evidence can close only after ACPManager-owned cleanup is verified. | Closure receipt or explicit `CLOSE_FAILED`; no surviving managed resource under `CLOSED`. |
| v0.19.4 | A fixed second task can start from Task A's ledger-bound result without Hermes relay. | Two-agent trace with zero routine Hermes calls between A and B. |
| v0.19.5 | Harmonia can select the next eligible task inside an approved contract without becoming a second runtime authority. | Revision-bound plan accepted by kernel; no direct Harmonia ACP call. |
| v0.19.6 | The bounded architecture survives representative failures without restoring Hermes hub-and-spoke. | Fault matrix plus `VIABLE`, `VIABLE WITH BLOCKERS` or `NOT VIABLE`. |

No patch begins until the preceding patch is frozen with evidence. A blocked patch stops the train until the user chooses repair, redesign or abandonment.

## 8. v0.19.1 detailed design — single-task composition

### Hypothesis

A single explicitly authorized task can be admitted, durably staged and accepted by ACP through:

```text
server composition
  -> KernelRunService
  -> KernelDispatcher
  -> OlympusRuntimeAdapter
  -> ACPManager
```

while ACPManager remains the sole process/session lifecycle owner.

### Honest capability boundary

v0.19.1 may report:

- admitted;
- dispatch pending;
- accepted;
- rejected before effect;
- retryable pre-acceptance failure;
- `UNKNOWN` / reconciliation required;
- technical observation.

It must not report:

- semantic completion;
- trusted artifact acceptance;
- independent review pass;
- verified closure;
- hub-and-spoke replacement.

`KernelRunService.complete_task()` is currently unimplemented, so v0.19.1 must not disguise ACP terminal status as task completion.

### Proposed composition seam

A server-owned factory should construct a project runtime only after explicit eligibility checks:

```text
build_coordination_runtime(
    trusted project root,
    derived project identity,
    existing ACPManager,
    parsed coordination config,
    explicit activation record,
)
```

The resulting bundle contains:

```text
project coordination store
SQLiteLedger
KernelWriter
KernelRunService
KernelDispatcher
OlympusRuntimeAdapter
```

Composition itself performs no ACP effect. Request admission is a separate operation.

### Proposed storage boundary

Use a project-scoped coordination database derived from trusted project identity, conceptually:

```text
<AETHER_HOME>/.olympus/projects/<validated-project-id>/coordination.db
```

Requirements:

- absolute trusted project root;
- project ID derived by the server, not selected as a path by the caller;
- ledger scope matches project identity and root;
- no use of the global Olympus session DB as coordination authority;
- no `PilotStore` projection or dual-write;
- inspect/read operations must not create or migrate state.

The exact resolver and filesystem location remain a later technical design decision; the per-project authority boundary is mandatory.

### Proposed request seam

The smallest backward-compatible experiment is an explicit discriminator on the existing delegation surface, conceptually:

```text
talk_to(action="delegate", coordination="kernel-single-task")
```

Effective admission requires all conditions:

```text
explicit request opt-in
AND server config permits kernel-single-task
AND project is allowlisted
AND max_active_runs permits admission
AND immutable contract authorizes the task
```

The request field alone is never authorization. Ordinary `talk_to` remains unchanged when the discriminator is absent.

A separate future `kernel_run` MCP tool may provide stronger steady-state separation, but it is not required for the smallest v0.19.1 experiment. A server-global selector is rejected because it could silently reroute all projects.

### Proposed default-off config shape

```yaml
coordination:
  enabled: false
  mode: legacy
  allowed_modes:
    - legacy
  project_allowlist: []
  max_active_runs: 0
```

Code presence, composition eligibility, request intent and live execution authorization are separate states. Configuration does not start a run.

### v0.19.1 non-goals

- no semantic completion;
- no trusted evidence acceptance;
- no closure claim;
- no handoff;
- no active Harmonia;
- no arbitrary graph;
- no production migration;
- no default-mode change;
- no gateway activation as part of implementation;
- no legacy fallback after admission.

### v0.19.1 deterministic gate

Before any live execution authorization, controlled tests must show:

1. absent/disabled kernel mode produces zero kernel and ACP effects;
2. legacy `talk_to` response and behavior remain unchanged;
3. explicit eligible opt-in creates one project runtime;
4. one run persists one immutable authority mode;
5. one task produces one durable staged dispatch;
6. accepted ACP identity is durably bound;
7. pre-acceptance failure is retryable without duplicate accepted effect;
8. response loss after acceptance becomes `UNKNOWN`;
9. stale worker fencing rejects terminal mutation;
10. project mismatch and arbitrary ledger paths fail closed;
11. server shutdown closes coordination resources within a bound;
12. no kernel path writes `PilotStore`.

### v0.19.1 live gate

A separate authorization may permit one disposable, single-task, no-side-effect ACP run. Pass means only:

- the real server composition selected kernel mode;
- the task reached ACPManager through the kernel path;
- durable identity and technical status agree;
- Hermes did not bypass the selected authority;
- cleanup/reconciliation state is reported honestly.

It does not mean semantic success or architecture viability.

### v0.19.1 rollback

- stop new kernel admissions;
- leave ordinary legacy calls unchanged;
- preserve admitted kernel runs for inspection/reconciliation;
- never retry an admitted run through legacy;
- preserve the project ledger as evidence;
- do not delete or rewrite ACP session history.

### v0.19.1 stop conditions

Any of these blocks the patch:

- dual-write or dual authority;
- legacy call after kernel admission;
- missing project binding;
- accepted effect classified as retryable;
- ACP session identity mismatch;
- unbounded or invisible teardown;
- config alone initiates work;
- ordinary `talk_to` changes when kernel mode is absent.

## 9. Later patch boundaries

### v0.19.2 — trusted evidence

Bound evidence to installation, project, run, task, attempt, contract generation, revocation epoch, plan, snapshot, logical session and ACP session. Reject stale, forged, conflicting or unrelated evidence. No closure.

### v0.19.3 — executable closure

Require trusted evidence before completion. Use ACPManager public lifecycle methods, durable cleanup receipts and `CLOSE_FAILED`. No multi-agent handoff.

### v0.19.4 — fixed handoff

Use exactly two pre-approved tasks. Task B becomes eligible only after Task A's trusted closure. Handoff is bounded and digest-bound. Hermes performs zero routine relay between tasks. No dynamic Harmonia selection.

### v0.19.5 — bounded Harmonia

Harmonia selects only from a bounded contract candidate set and a revision-bound projection. Kernel validates and commits. Harmonia makes no direct ACP call and cannot amend the contract.

### v0.19.6 — fault pilot and verdict

Run a disposable bounded workflow through failure cases including spawn/send failure, accepted-response loss, stale fence, contention, stale evidence, cancellation, restart and cleanup timeout. Any duplicate authority, silent fallback, stale evidence acceptance or incorrect retry of uncertainty yields `NOT_VIABLE`.

## 10. Review and evidence policy

Athena remains suspended. Validation uses:

- exact RED/GREEN tests;
- direct Hermes source and call-site verification;
- controlled runtime evidence;
- proportional independent consultation when architecture risk requires it;
- explicit user authorization before live ACP or external effects.

A test report, agent statement or specialist opinion never substitutes for observable runtime evidence.

## 11. Current decision gate — v0.19.1 API seam

The six-patch sequence is approved. The next decision is how an explicitly authorized v0.19.1 request selects the kernel without changing ordinary `talk_to` behavior.

### Option A — discriminator inside `talk_to` (recommended for v0.19.1)

```text
talk_to(action="delegate", coordination="kernel-single-task")
```

- smallest backward-compatible change;
- reuses the established Hermes-to-Olympus surface;
- ordinary calls remain legacy when the field is absent;
- Olympus must enforce config, project allowlist, contract and immutable run authority;
- eventual steady-state separation may still require a dedicated tool.

### Option B — separate `kernel_run` MCP tool

- strongest structural separation between legacy sessions and kernel runs;
- clearer response and lifecycle contract;
- expands the public MCP surface before the first operational hypothesis is proven;
- requires more Hermes integration and compatibility work in v0.19.1.

A server-global runtime switch is rejected because it could reroute unrelated projects and existing behavior.

**Recommendation:** approve Option A for v0.19.1 only. Reassess a dedicated `kernel_run` tool after v0.19.4 proves a no-relay handoff. Choosing either option authorizes detailed planning only; code and live execution remain separate gates.
