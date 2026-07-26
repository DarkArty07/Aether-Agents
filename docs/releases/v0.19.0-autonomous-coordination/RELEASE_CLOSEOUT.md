# v0.19.0 Autonomous Coordination — Release Closeout

**Status:** FROZEN EXPERIMENTAL BASELINE — DEFAULT-OFF — NOT OPERATIONALLY VALIDATED

**Closeout baseline:** `e26d890` (`docs(coordination): record R11 closeout`)

**Decision:** v0.19.0 stops at R11. R12–R14 are not part of this version and no live activation, merge, tag, deployment, publication, or release-readiness claim is authorized by this document.

## 1. Honest release verdict

v0.19.0 contains a substantial experimental coordination subsystem, but it is not a demonstrated replacement for Hermes' live hub-and-spoke orchestration.

The version demonstrates deterministic building blocks, a default-off shadow observer, durable authority primitives, and a kernel dispatch candidate through R11. It does not demonstrate a production composition root, a kernel-backed live ACP run, trusted evidence and independent review binding, verified operational closure, production migration/rollback, or replacement of the live `talk_to -> ACPManager` path.

The only accurate label is:

> **Experimental, default-off, and not operationally validated.**

## 2. Evidence matrix

| Area | Closeout classification | What is actually established |
|---|---|---|
| R2–R6 primitives | Demonstrated in deterministic tests | Contracts, ledger, projections, admission, capabilities, transport concepts, effects, review types and closure validation exist as isolated/default-off components. |
| R7 shadow | Demonstrated, observational only | Real Olympus session evidence was correlated; shadow remained default-off, performed no coordination effect and never asserted semantic completion. |
| R8 Snake pilot | Legacy / blocked | It produced a real artifact and fail-closed recovery evidence, but executed through `PilotStore` and `dispatch_pilot_task()`, bypassing the selected kernel. Final review rejected the artifact and closure was not dispatched. |
| R9–R10 convergence | Demonstrated in deterministic tests | Kernel workflow, budget and authority composition were added. This does not prove use by the live server. |
| R11 dispatch | Demonstrated in deterministic tests | Durable intent, worker fencing, uncertain-effect recovery, legacy-outbox migration and the Olympus adapter seam are implemented. Focused 45, coordination 650 and full 841 tests passed at closeout. |
| Live kernel composition | Not demonstrated | No production server composition root creates and operates `KernelRunService` plus `KernelDispatcher` as the authority for `talk_to`. |
| R12 trusted evidence/review | Not implemented in v0.19.0 | Agent claims, verifier receipts, artifact generations and runtime-bound independent review are not composed into the kernel runtime. |
| R13 closure/cleanup | Not implemented in v0.19.0 | Authoritative closure snapshots, executable cleanup receipts, listener/child verification and `CLOSE_FAILED` are not composed into the kernel runtime. |
| R14 kernel-backed pilot | Not executed | No clean kernel-backed Snake run or complete fault matrix was performed. |
| Production migration/rollback | Not demonstrated | Migration behavior is tested in disposable SQLite fixtures; no live installation migration, activation or rollback was executed. |
| Hub-and-spoke replacement | Not demonstrated | Hermes remains the routine relay on the operational path. |

## 3. Integration truth

The live path remains:

```text
Hermes
  -> MCP talk_to
  -> Olympus v3 server
  -> ACPManager
  -> Daimon ACP session/process
```

The candidate kernel path exists as code:

```text
KernelRunService
  -> SQLiteLedger / durable projections
  -> KernelDispatcher
  -> OlympusRuntimeAdapter.dispatch_kernel()
  -> ACPManager public lifecycle methods
```

But the live server does not construct or select that path. `KernelRunService` and `KernelDispatcher` are definitions/exports used by tests and candidate composition, not the operational authority of the gateway.

Therefore v0.19.0 does **not** replace Hermes' hub-and-spoke coordination.

## 4. Allowed claims

The project may state that:

- v0.19.0 contains an experimental Aether-native coordination kernel;
- the subsystem is default-off;
- R7 shadow was exercised against real Olympus evidence without operational authority;
- R8 is preserved as legacy blocked evidence and did not validate the selected kernel;
- R9–R11 have deterministic implementation evidence;
- R11 is committed in `0912f1d` and documented in `e26d890`;
- the live `talk_to` path remains the existing Hermes/Olympus path;
- operational integration and architecture replacement remain unproven.

## 5. Forbidden claims

The project must not state that:

- v0.19.0 replaces Hermes hub-and-spoke;
- the kernel is the current production runtime;
- R8 validated the selected architecture end to end;
- the Snake pilot was accepted or closed;
- live kernel-backed ACP integration was demonstrated;
- production migration or rollback was executed;
- universal exactly-once behavior was proven;
- operational `CLOSED` and cleanup were proven;
- v0.19.0 is production-ready or release-ready;
- suspended review work is equivalent to an independent PASS.

## 6. Frozen scope

v0.19.0 is frozen at R11. The following are explicitly outside this version:

- trusted evidence runtime and artifact-generation invalidation;
- runtime-bound independent review;
- authoritative closure snapshot and executable cleanup;
- live composition root or runtime selector;
- active Harmonia coordination;
- kernel-backed Snake execution;
- replacement of routine Hermes relay;
- gateway/config/auth migration;
- production deployment, merge, tag or publication.

Existing R12–R15 sections are retained as historical design input, not as unfinished requirements that keep v0.19.0 open.

## 7. Approved later experimental increments

The user approved a six-patch experimental train for work after v0.19.0. Its canonical design is `../v0.19.x-kernel-migration/DESIGN.md`; approval does not authorize code or live execution.

| Version | Bounded experiment | Required stop gate |
|---|---|---|
| v0.19.1 | Explicit default-off kernel composition for one task | Real server composition reaches ACPManager with one immutable authority; no completion claim. |
| v0.19.2 | Trusted verifier receipts and runtime-bound evidence | Agent prose, stale generation or unrelated ACP state cannot pass. |
| v0.19.3 | Executable closure and manager-owned cleanup | No `CLOSED` while a session or managed resource remains unverifiably open. |
| v0.19.4 | Fixed two-agent ledger handoff | Hermes performs zero routine relay or next-agent dispatch between Tasks A and B. |
| v0.19.5 | Bounded active Harmonia selection | Harmonia selects inside an approved contract; kernel commits; Harmonia makes no ACP call. |
| v0.19.6 | Fault-injected bounded pilot | Result is `VIABLE`, `VIABLE WITH BLOCKERS`, or `NOT VIABLE`. |

Every increment starts default-off, receives separate implementation and live-execution authorization, freezes before the next increment, and stops the train if an authority invariant fails.

## 8. Repository and packaging warning

At closeout audit time, the feature branch was 59 commits ahead of `main` and the working tree also contained unrelated tracked modifications and many untracked runtime/config/skill/R8 artifacts. Those paths are not evidence of a clean release candidate and must not be swept into a merge or package.

In particular, closeout must not absorb `.olympus/`, databases/WAL files, logs, backups, credentials, unrelated `home/**` or skill changes, uncommitted R8 changes, or an unreviewed lockfile.

A clean merge/tag/package decision requires a separate scoped reconciliation from committed history. This document does not perform or authorize it.

## 9. Remaining known risks

- ACP asynchronous teardown defects remain unresolved.
- Production key custody and hostile-local-process protection are outside the proven threat model.
- R8 remains terminally blocked as historical evidence.
- No clean production-like kernel integration run exists.
- No active runtime rollback has been exercised.
- The current branch/working tree is not itself a clean release artifact.

## 10. Closeout meaning

Closing v0.19.0 means stopping scope growth and preserving an honest experimental baseline. It does not mean activation, acceptance of the architecture, merge, tag, deployment or publication.

The architecture succeeds only when a later bounded experiment proves that the kernel—not Hermes relay prose—coordinates routine work from an approved contract through verified closure. Until then, replacement remains an explicit hypothesis, not a released capability.
