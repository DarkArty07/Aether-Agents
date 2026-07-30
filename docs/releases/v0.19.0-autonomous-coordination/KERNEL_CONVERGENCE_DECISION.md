# v0.19.0 Kernel-Backed Convergence Decision

**Status:** HISTORICAL CONVERGENCE DECISION — SUPERSEDED FOR v0.19.0 STATUS BY `RELEASE_CLOSEOUT.md`

**Implementation outcome:** v0.19.0 implemented deterministic convergence through R11, then froze as experimental/default-off/not operationally validated. R12–R14, another pilot, live coordination, gateway/config mutation, merge, tag, deployment and publication are outside this version.

> **Post-closeout maintenance note (2026-07-29):** this decision records the historical convergence rationale. Current source retains the kernel foundations and removes the non-authoritative R2–R8 executable laboratories; use [`../../architecture/EXPERIMENTAL_COORDINATION.md`](../../architecture/EXPERIMENTAL_COORDINATION.md) for the current code boundary.

## Decision

Aether will preserve the R2–R7 deterministic coordination kernel and make it the mandatory operational path for new kernel-backed pilots. R8's `PilotStore` runtime remains historical and reproducible but must not be hardened into a second kernel.

The target is:

```text
PilotManifest                  fixture definition
      |
Snake compiler                 deterministic translation
      |
R2–R7 kernel                   semantic operational authority
      |
Olympus / ACPManager           process and ACP session authority
      |
Evidence, review, closure      proof and semantic completion
```

A temporary compatibility facade may expose legacy read APIs over kernel projections. It must not dual-write or retain independent mutable state.

## Evidence behind the decision

R2–R7 already implement immutable contracts, an authenticated SQLite ledger, projections, leases/fencing, admission, Harmonia planning, ledger-backed transport, effects, independent review, closure validation, and default-off shadow integration. A fresh focused audit passed 218 kernel tests.

The same audit found no operational construction of `LedgerNativeTransport`, no operational call site of `validate_closure()`, and no composition root that makes `SQLiteLedger` the effective authority for a run. R8 instead executes:

```text
PilotManifest
  -> PilotCoordinator / PilotStore
  -> dispatch_pilot_task()
  -> OlympusRuntimeAdapter
  -> ACPManager
```

R8 therefore validated the weaker parallel runtime, not the complete R2–R7 path.

## Non-negotiable invariants

1. One run selects exactly one runtime at creation: `legacy` or `kernel-backed`.
2. Kernel-backed runs never write operational state to `PilotStore`.
3. Every semantic transition is derived from durable trusted state and appended through the ledger.
4. `ProjectionReducer` materializes workflow state; caller-provided DTOs are not authority.
5. Delivery, execution, semantic outcome, and operational closure are separate lifecycles.
6. A task result cannot mutate state without the current run/task/attempt/lease/fence binding.
7. Ambiguous post-dispatch outcomes become `UNKNOWN`, block retry, and require reconciliation.
8. Budget tracks authorized, reserved, committed, spent, and released amounts durably.
9. Correction admission reserves verification, re-review, recovery, and cleanup obligations.
10. Evidence preserves provenance classes: `agent_claim`, `runtime_receipt`, `verifier_receipt`, `review_finding`, `operator_attestation`, and `snapshot_evidence`.
11. Agent prose never becomes a command receipt, passing gate, or completion assertion.
12. Artifact generation is ledger-derived. A later write invalidates prior verification, review, and closure snapshots.
13. Reviewer independence derives from kernel assignment, Olympus session identity, read-only capabilities, and snapshot binding.
14. `validate_closure()` remains pure but receives only a snapshot built from authoritative state.
15. Semantic outcome and operational lifecycle are distinct:

```text
semantic_outcome: ACCEPTED | REJECTED | BLOCKED
operational_lifecycle: OPEN | CLOSING | CLOSED | CLOSE_FAILED
```

16. Cleanup is persisted, executed through Olympus/runtime owners, verified, and receipted before `CLOSED`.
17. Olympus remains the sole owner of ACP processes, connections, sessions, cancel, close, and teardown.
18. Harmonia remains a pure planner and stays shadow-only during the first kernel-backed Snake run.
19. `.aether` remains project continuity, never workflow authority.
20. Existing hash chain, HMAC, trusted-anchor, fencing, and default-off guarantees are preserved.

## Initial threat model

The implementation plan targets a local single-user machine with cooperative processes. It does not claim protection against hostile local plugins/processes, remote execution, or multi-host coordination. Existing integrity controls remain mandatory; stronger capability/token custody is deferred rather than removed.

## Accepted scope

- fixed Snake graph;
- one host and local SQLite;
- concurrency 1;
- kernel-controlled verifier for tests/builds;
- E0/E1 only;
- Harmonia shadow;
- default-off;
- no migration of the historical R8 database;
- no live activation in this planning authorization.

## Rejected alternatives

- **Harden PilotStore into the kernel:** duplicates R2–R7 authority.
- **Permanent common interface over two equal runtimes:** preserves dual authority.
- **A third generic workflow framework:** unnecessary for the fixed pilot.
- **Mid-run migration:** breaks authority and recovery identity.
- **Agent-reported command results as trusted evidence:** confuses claim with observation.

## Approval gates

This decision authorizes documentation and planning only. Separate written approval is required for:

1. production/test source implementation;
2. running RED tests that require code additions;
3. active Snake execution;
4. gateway/runtime activation or restart;
5. merge, tag, deployment, publication, or release.
