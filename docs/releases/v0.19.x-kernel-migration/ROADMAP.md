# v0.19.x Incremental Kernel Migration — Roadmap

**Status:** v0.19.1 AND v0.19.2 IMPLEMENTED; v0.19.3 GATE A APPROVED AND IMPLEMENTATION AUTHORIZED; LIVE GATE BLOCKED

**Canonical design:** `DESIGN.md`

**v0.19.1 implementation plan:** `V0.19.1_IMPLEMENTATION_PLAN.md`

**v0.19.3 implementation plan:** `V0.19.3_IMPLEMENTATION_PLAN.md`

**Frozen predecessor:** `../v0.19.0-autonomous-coordination/RELEASE_CLOSEOUT.md`

## 1. Governing rule

Each patch carries one operational hypothesis. Every patch remains default-off, has independent implementation and live-execution gates, preserves one authority per run, and freezes before the next patch begins.

```text
v0.19.0  frozen unvalidated baseline
   |
   v
v0.19.1  live single-task kernel composition
   |
   v
v0.19.2  trusted runtime-bound evidence
   |
   v
v0.19.3  executable closure and cleanup
   |
   v
v0.19.4  fixed two-agent handoff, zero Hermes relay
   |
   v
v0.19.5  bounded active Harmonia selection
   |
   v
v0.19.6  fault-injected pilot and architecture verdict
```

A failure does not automatically authorize a correction patch or the next milestone. The train stops at the failing version until the user chooses repair, redesign or abandonment.

## 2. Patch matrix

| Version | State | Hypothesis | Required evidence | Explicit exclusions |
|---|---|---|---|---|
| v0.19.1 | IMPLEMENTED — deterministic and bounded live evidence recorded | One opted-in task reaches ACPManager through server-owned kernel composition. | Actual composition seam, durable admission/staging/session binding, honest uncertainty, unchanged legacy default. | Completion, review, closure, handoff, Harmonia planning. |
| v0.19.2 | IMPLEMENTED — Gate B closed at `b759609` | A verifier-bound receipt proves the exact task result independently of agent prose. | Exact identity tuple, artifact generation/digest, stale/forged evidence rejection, deterministic replay and atomic dependent release. | Closure, next-task selection, handoff. |
| v0.19.3 | IMPLEMENTED — Gate B closed at `7e432f5`; Gate C live blocked | Trusted work closes only after ACPManager-owned cleanup is verified. | Closure snapshot, durable close intent, cleanup receipt, `CLOSE_FAILED`/`RECONCILIATION_REQUIRED`, no managed survivor under `CLOSED`. | Handoff, Harmonia, broad pilot. |
| v0.19.4 | GATE A PROPOSED — submission seam decision required | Task B starts from Task A's durable result without Hermes relay. | Two-task trace, contract-bound workers, immutable digest-bound snapshot, cleanup-before-handoff and zero routine Hermes calls between tasks. | Dynamic task selection, repair loops, arbitrary DAG. |
| v0.19.5 | BLOCKED by v0.19.4 | Harmonia selects a bounded next task without becoming runtime/lifecycle authority. | Projection revision CAS, eligibility enforcement, kernel commit and no Harmonia ACP call. | Open-ended planning, contract amendment, global activation. |
| v0.19.6 | BLOCKED by v0.19.5 | The complete bounded path survives representative failures without hub-and-spoke fallback. | Disposable live run, fault matrix and formal viability verdict. | Production rollout, second fixture, global replacement claim. |

## 3. Per-patch gates

Every increment uses four independent gates:

### Gate A — Design

- one hypothesis;
- one authority delta;
- named non-goals;
- deterministic gate;
- live gate;
- rollback and stop conditions;
- explicit user approval.

### Gate B — Implementation

- exact RED tests precede source changes;
- focused, subsystem and full-suite regression;
- lint, compile, diff and scope checks;
- credential scan;
- no configuration or runtime activation;
- atomic commit(s) restricted to the patch.

### Gate C — Live execution

Requires separate user authorization after Gate B. Freeze:

- exact project/root;
- immutable contract and task set;
- runtime/config eligibility;
- task, retry, time and effect budgets;
- allowed Daimons;
- expected ledger path;
- failure matrix;
- cleanup deadline;
- rollback trigger.

### Gate D — Closeout

Record one outcome:

- `VALIDATED` — the patch hypothesis is supported by named evidence;
- `BLOCKED` — implementation exists but the operational gate failed or could not complete;
- `NOT_VIABLE` — a permanent invariant was violated;
- `ABANDONED` — user stops the line without a viability claim.

No next patch starts before Gate D.

## 4. Global stop conditions

The experiment train stops immediately on:

- two authorities for one run;
- any `PilotStore` write from kernel mode;
- silent fallback after kernel admission;
- accepted external effect retried as if pre-acceptance;
- stale evidence accepted;
- `CLOSED` with unverified lifecycle cleanup;
- Harmonia making direct ACP calls;
- Hermes resuming routine relay inside a no-relay gate;
- cross-project ledger/session contamination;
- unbounded retries, cleanup or agent creation;
- activation caused by configuration alone.

## 5. Final success criterion

v0.19.6 may issue `VIABLE` only if one approved bounded workflow demonstrates:

```text
Hermes contract submissions:                 1
Hermes routine relay after admission:        0
Hermes next-agent selections after admission: 0
Hermes correction/retry dispatches:          0
Kernel-owned routine transitions:            all
ACPManager-owned lifecycle operations:       all
Trusted evidence and closure receipts:       complete
Silent fallback or dual authority:           none
Mandatory fault cases:                       passed/fail-closed
```

`VIABLE` applies only to the bounded topology tested. General replacement, second fixture and production activation require later design and authorization.

## 6. Current gate

v0.19.3 deterministic Gate B is frozen at `7e432f5`; its live Gate C remains blocked. The current work is the v0.19.4 Gate A proposal in `V0.19.4_GATE_A_PROPOSAL.md`.

The proposed model uses one immutable contract with fixed A/B worker bindings, a verifier-owned digest-addressed snapshot and a hard `A CLOSED` prerequisite before B admission. One architectural decision remains: whether the existing public `harmonia start` seam may accept the complete fixed two-task contract without selecting or relaying between tasks. Harmonia remains default-off. Live ACP, configuration changes, gateway restart, implementation before Gate A approval, merge, tag, deployment and publication remain unauthorized.
