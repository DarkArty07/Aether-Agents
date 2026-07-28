# v0.19.0 Kernel-Backed Convergence Roadmap

**Status:** FROZEN AT R11 — HISTORICAL CONVERGENCE PLAN; R12–R15 DEFERRED TO LATER VERSIONED EXPERIMENTS

**Closeout authority:** `RELEASE_CLOSEOUT.md`. R11 is the final v0.19.0 implementation milestone. Sections R12–R15 below are preserved as design input and are not pending scope for v0.19.0.

**Predecessor:** `ROADMAP.md` R0–R8. That history remains normative evidence and is not rewritten. R8 ended `BLOCKED` after the bounded Snake pilot exercised the legacy pilot runtime and failed its final independent product review.

**Historical objective:** prove whether the architecture could become functionally viable through one kernel-backed pilot. v0.19.0 stopped before that proof, so no `VIABLE` verdict was issued.

## Release boundary

v0.19.0 closeout contains:

- R7 shadow stable and default-off;
- frozen legacy R8 blocked evidence;
- deterministic kernel convergence through R11;
- no trusted-evidence runtime, executable closure or kernel-backed pilot;
- no autonomous general rollout;
- local single-user/cooperative-process threat model;
- no E2–E4 live effects;
- no merge, tag, deployment, publication or runtime activation authorized by this closeout.

## Path

```text
R8L  Legacy R8 evidence frozen (BLOCKED)
  |
  v
R9   Convergence contracts and RED composition matrix (COMPLETE)
  |
  v
R10  Durable workflow projection and budget authority (COMPLETE)
  |
  v
R11  Ledger-native dispatch, lease/fence, and reconciliation (COMPLETE)
  |
  v
FREEZE v0.19.0 experimental baseline; no operational viability verdict
  |
  v
LATER VERSIONED EXPERIMENTS (separate authorization)
  - trusted evidence and review binding
  - executable closure and cleanup
  - default-off live composition
  - clean kernel-backed pilot and fault matrix
```

## R8L — Freeze legacy evidence

**Status:** COMPLETE / READ-ONLY

- preserve historical PilotStore DB, R8 handoff, contract, incidents, and test fixtures;
- preserve final `blocked` outcome and consumed attempt budget;
- never migrate the historical run mid-flight;
- no fourth review, correction, or closure dispatch;
- classify legacy APIs explicitly.

**Exit:** legacy artifacts remain reproducible and new kernel work cannot mutate them.

## R9 — Contracts and RED composition matrix

**Status:** COMPLETE

Deliverables:

1. convergence decision and ownership matrix;
2. typed semantic responsibilities for run/task/attempt/session/dispatch/effect/evidence/gate/budget/closure;
3. legal transition tables;
4. authority producer→artifact→consumer matrix;
5. exact RED tests for every current bypass;
6. compiler contract from `PilotManifest` to the kernel;
7. feature flag/default-off and runtime-mode contract;
8. no-write scan for PilotStore in kernel-backed mode.

**Exit:** every implementation milestone has a behavioral RED and an exact authority boundary.

## R10 — Workflow projection and budget authority

**Status:** COMPLETE — deterministic verification and recorded security findings reconciled

Implement with a fake executor only:

- run identity and mode;
- fixed plan revision;
- task dependencies and readiness;
- attempt history and supersession;
- durable session-binding intent;
- artifact generation;
- budget authorized/reserved/committed/spent/released;
- correction/retry/recovery re-admission;
- deterministic rebuild and divergence checks.

**Exit:** delete/rebuild projections without losing semantic run state; no caller input can directly advance task, budget, gate, or closure state.

## R11 — Dispatch, fencing, and uncertain effects

**Status:** COMPLETE — commit `0912f1d`; focused suite (45), coordination regression (650), full suite (841), Ruff, compile, diff, staged-scope and credential scan are GREEN.

- persist dispatch intent before ACP calls;
- claim through `LedgerNativeTransport`;
- derive immutable dispatch envelope from authoritative projection;
- bind run/task/attempt/contract/plan/lease/fence/snapshot;
- call only public ACPManager lifecycle operations;
- persist logical and ACP session identity;
- separate delivery ACK from execution status;
- timeout after accepted dispatch becomes `UNKNOWN`;
- reconcile before retry;
- persist cancellation intent for expired/superseded attempts;
- harden `complete_outbox()` binding.

**Exit:** fault injection at every persist/effect boundary cannot duplicate semantic execution or accept stale results.

## Deferred design inventory — not v0.19.0 scope

The following R12–R15 sections are preserved to carry design intent into later versioned experiments. They are not pending milestones for v0.19.0 and their numbering may be remapped when a later increment is authorized.

## R12 — Trusted evidence and generic review binding

- explicit evidence provenance classes;
- kernel-controlled verifier for approved commands;
- argv/cwd/time/exit/output hashes and pre/post snapshots;
- ledger-derived artifact generations;
- automatic staleness after later writes;
- structured results only; prose remains summary;
- reviewer assignment derived from kernel/Olympus identity;
- enforced read-only capability and independent attempt/session;
- persisted review findings and gate evaluations.

The review mechanism remains role/capability-based and must not hard-code Athena. While Athena is suspended, milestone acceptance uses controlled verifier receipts, adversarial deterministic tests, direct Hermes inspection, and user authority where reserved. This milestone may test reviewer identity and independence with fakes; it does not authorize dispatching Athena.

**Exit:** an agent-created receipt, JSON-in-prose, or stale review cannot satisfy a gate.

## R13 — Closure and cleanup

- authoritative `ClosureSnapshotBuilder`;
- pure `validate_closure()` retained;
- persisted semantic verdict;
- separate operational lifecycle;
- persisted cleanup plan;
- cleanup executor calling lifecycle owners;
- receipts for session cancellation/close, lease release, managed children, and listener checks;
- `CLOSE_FAILED` when postconditions fail;
- no final `CLOSED` before cleanup verification.

**Exit:** completion cannot bypass closure authority and closure cannot claim cleanup it did not execute.

## R14 — Kernel-backed Snake

Entry requires R9–R13 GREEN and separate execution authorization.

Conditions:

- clean root and new DB;
- fixed Snake manifest;
- concurrency 1;
- E0/E1 only;
- Harmonia shadow;
- no PilotStore operational writes;
- no incident-specific fallback;
- no manual DB mutation;
- no coordinator changes during the run;
- no Athena task or Athena-dependent acceptance gate;
- no publication or live global activation.

Fault matrix includes:

- crash before/after intent;
- crash after session open;
- response lost after possible effect;
- stale lease/fence result;
- duplicate delivery/event/result;
- invalid structured response;
- false agent success claim;
- insufficient budget for correction plus re-review;
- stale evidence after write;
- SQLite busy/contention;
- cleanup failure and surviving listener.

**Exit:** either evidence-backed semantic acceptance plus verified `CLOSED`, or an honest fail-closed terminal outcome. A blocked result remains valid evidence. Hermes then issues a functional verdict for the v0.19.0 architecture: `VIABLE`, `VIABLE WITH BLOCKERS`, or `NOT VIABLE`, grounded in the durable run and fault-injection evidence.

## R15 — Second fixture

**Status:** DEFERRED / SEPARATE APPROVAL

Select a different language/framework, task type, repository structure, and evidence class. Keep topology bounded initially. Its purpose is to detect Snake-specific overfitting, not to broaden autonomy automatically.

## Stop conditions

Stop before advancing when:

- dual-write appears;
- PilotStore becomes mutable authority for a kernel run;
- a semantic transition depends on agent prose;
- a retry is proposed while effect state is uncertain;
- budget obligations cannot be reserved;
- a stale fence can mutate state;
- closure facts are caller-supplied;
- cleanup cannot be verified;
- a required architectural decision changes approved scope;
- a deterministic blocker remains reproducible after the bounded correction budget;
- proving the milestone would require Athena while the global suspension remains active.

## Current verification policy

Athena is suspended globally until explicit user reactivation. For R11–R14:

1. write exact RED tests before implementation;
2. require focused, subsystem, full-suite, lint, compile, diff, scope, and secret checks;
3. use fault injection at every persist/effect boundary;
4. inspect producer→artifact→consumer authority directly;
5. reproduce every blocker before correction and every claimed fix afterward;
6. keep implementation, pilot execution, activation, and publication as separate authorization gates;
7. let Hermes accept or reject each milestone from observable evidence, with the user retaining architectural and run authorization.

This policy removes Athena as a universal gate; it does not convert missing evidence, unresolved security defects, or a failed pilot into PASS.

## Authorization matrix

| Action | Current status |
|---|---|
| Documentation and planning | AUTHORIZED |
| R9/R10 source and tests | COMPLETE |
| R11a RED dispatch/outbox/fencing tests | COMPLETE and committed in `869efee` |
| R11b source/test implementation | COMPLETE and committed in `0912f1d` |
| R12–R15 source/test implementation | DEFERRED outside v0.19.0; requires later versioned authorization |
| Fake-runtime deterministic tests | R11 focused 45, coordination 650 and full 841 GREEN at closeout |
| Real ACP kernel integration tests | NOT EXECUTED in v0.19.0 |
| Clean kernel-backed pilot | NOT EXECUTED in v0.19.0 |
| Athena review or dispatch | SUSPENDED until explicit user reactivation |
| Gateway restart/config mutation | NOT AUTHORIZED |
| Merge/tag/release/publication | NOT AUTHORIZED by this closeout |
