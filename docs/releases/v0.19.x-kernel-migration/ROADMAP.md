# v0.19.x Incremental Kernel Migration — Roadmap

**Status:** CLOSED AT v0.19.5 — `VIABLE — BOUNDED`

**Canonical design:** `DESIGN.md`

**v0.19.1 implementation plan:** `V0.19.1_IMPLEMENTATION_PLAN.md`

**v0.19.3 implementation plan:** `V0.19.3_IMPLEMENTATION_PLAN.md`

**Frozen predecessor:** `../v0.19.0-autonomous-coordination/RELEASE_CLOSEOUT.md`

**Final evidence:** `V0.19.5_GATE_C_EVIDENCE.md`

**Roadmap closeout:** `ROADMAP_CLOSEOUT.md`

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
v0.19.6  separate patch cancelled at closeout; verdict absorbed by v0.19.5 evidence
```

A failure does not automatically authorize a correction patch or the next milestone. The train stops at the failing version until the user chooses repair, redesign or abandonment.

## 2. Patch matrix

| Version | State | Hypothesis | Required evidence | Explicit exclusions |
|---|---|---|---|---|
| v0.19.1 | IMPLEMENTED — deterministic and bounded live evidence recorded | One opted-in task reaches ACPManager through server-owned kernel composition. | Actual composition seam, durable admission/staging/session binding, honest uncertainty, unchanged legacy default. | Completion, review, closure, handoff, Harmonia planning. |
| v0.19.2 | IMPLEMENTED — Gate B closed at `b759609` | A verifier-bound receipt proves the exact task result independently of agent prose. | Exact identity tuple, artifact generation/digest, stale/forged evidence rejection, deterministic replay and atomic dependent release. | Closure, next-task selection, handoff. |
| v0.19.3 | IMPLEMENTED — lifecycle/cleanup hypothesis exercised by later live gates | Trusted work closes only after ACPManager-owned cleanup is verified. | Closure snapshot, durable close intent, cleanup receipt, `CLOSE_FAILED`/`RECONCILIATION_REQUIRED`, no managed survivor under `CLOSED`. | Handoff, Harmonia, broad pilot. |
| v0.19.4 | VALIDATED — Gate C PASS | Task B starts from Task A's durable result without Hermes relay. | Two-task trace, contract-bound workers, immutable digest-bound snapshot, cleanup-before-handoff and zero routine Hermes calls between tasks. | Dynamic task selection, repair loops, arbitrary DAG. |
| v0.19.5 | VALIDATED — Gate C PASS; `VIABLE — BOUNDED` | Harmonia selects a bounded next task without becoming runtime/lifecycle authority. | Projection revision CAS, eligibility enforcement, kernel commit, real semantic successor consumption and no Harmonia ACP call. | Open-ended planning, contract amendment, global activation. |
| v0.19.6 | CLOSED — no separate patch; absorbed by final v0.19.5 evidence | The bounded architecture receives a formal viability disposition without extending the topology. | Deterministic fault matrix, fail-closed live corrections, final disposable real run and formal verdict in `ROADMAP_CLOSEOUT.md`. | Production rollout, second fixture, global replacement claim. |

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

The roadmap may issue `VIABLE` only if one approved bounded workflow demonstrates:

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

## 6. Final gate disposition

The v0.19.5 real disposable Gate C passed at candidate head `e8b287b`. Its exact trace, semantic artifacts, event-chain checks, corrections and boundaries are versioned in `V0.19.5_GATE_C_EVIDENCE.md`.

On 2026-07-27 Chris explicitly closed this roadmap after receiving the bounded replacement verdict. The final disposition is `VIABLE — BOUNDED`. A separate v0.19.6 implementation is cancelled rather than left pending; its intended formal decision is captured in `ROADMAP_CLOSEOUT.md` using the accumulated deterministic fault matrix, fail-closed live corrections and final real Gate C.

Harmonia remains default-off. PR readiness, merge, tag, release, deployment, publication and production activation remain unauthorized by this roadmap closeout.
