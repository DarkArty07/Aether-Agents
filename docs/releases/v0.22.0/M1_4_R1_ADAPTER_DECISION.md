# M1.4-R1 — Adaptive Orca provider and ownership decision

> **Status:** APPROVED SUCCESSOR DESIGN; IMPLEMENTATION/QUALIFICATION IN PROGRESS
> **Date:** 2026-08-08
> **Decision owner:** Christopher (DarkArty07)
> **Execution owner:** Hermes
> **D1 granted:** No
> **MCP registration/activation:** No
> **Canonical task:** `../../external-agent/TASK-ORCA-ADAPTER-REDESIGN.md`

## 1. Relationship to M1.4

`M1_4_PROVIDER_DECISION.md` remains the historical truth for the exact
`b807c62` boundary: the original 55-capability rule returned
`D1_BLOCKED_PROVIDER_SEAM_INSUFFICIENT`.

The product owner subsequently selected a bounded adaptive redesign. This
successor decision supersedes only:

- the assumption that every Aether capability must be a provider-native aggregate;
- the 24-tool operational catalog as the v1alpha1 target;
- the original D1 sufficiency rule;
- the stop boundary that required a provider-path owner decision.

It does not rewrite or invalidate the M1.2/M1.3 evidence, grant D1, register MCP,
or accept the Orca lifecycle.

## 2. Decision

Aether will adapt to Orca's public structured command surface rather than require
Orca to reproduce Aether's full product model.

- Hermes owns product intent, contracts, routing, supervision, synthesis, and
  completion proposals.
- Aether MCP owns typed admission/validation, policy, provider binding, operation
  identity, correlation, journal/receipts, composition plans, reconciliation,
  bounded semantic trace, and evidence/closeout references.
- Orca remains the sole owner of mutable Run, Task, Dispatch, worker, terminal,
  worktree, operational-message, recovery, and process/resource state.
- Git/filesystem and executed tools own artifact bytes and test/build evidence.
- The user owns product meaning, material compromises, protected effects, and
  final acceptance.

Aether may record a semantic closeout and compose public Orca operations. It may
not create an independent Orca-like scheduler, edit private Orca state, or label a
composition as provider-native.

## 3. Three-axis capability model

Every provider requirement is classified independently by:

### Delivery

- `NATIVE`: one public version-pinned Orca operation performs it;
- `COMPOSED`: an Aether plan invokes only public typed Orca operations;
- `AETHER_OWNED`: product policy, correlation, journal, trace, or semantic closeout;
- `DEFERRED`: intentionally unavailable in the current operational surface;
- `UNSUPPORTED`: no safe admitted implementation exists.

### Guarantee

- `FULL`: intended contract can be demonstrated without a known semantic reduction;
- `DEGRADED`: useful behavior exists, but atomicity, immediacy, completeness, or
  provider-native semantics are explicitly lower.

### Qualification

- `PROVEN`: exact deterministic and executed evidence satisfies the declared
  guarantee;
- `UNQUALIFIED`: a design/command path exists but has not passed its gate;
- `UNKNOWN`: current evidence cannot classify the actual effect.

Delivery is not proof. `NATIVE/FULL/UNQUALIFIED` remains unavailable for enabled
mutations until it becomes `PROVEN`.

The machine-readable successor is `M1_ORCA_ADAPTATION_MATRIX.json`; the historical
source remains `M1_ORCA_PROVIDER_SEAM_MATRIX.json`.

## 4. Revised Hermes operational catalog

The successor `aether.mcp/v1alpha2` operational contract contains exactly 15
designed tools; the 24-tool `v1alpha1` bundle remains immutable historical
evidence:

```text
project_admit
project_inspect
swarm_validate
swarm_start
swarm_status
swarm_dispatch
swarm_message
swarm_reconcile
swarm_retry
swarm_cancel
swarm_close
swarm_trace
orca_search
orca_describe
orca_call
```

All remain unregistered and uncallable during the R0-R6 task.

### Consolidated

`swarm_record_decision` and `swarm_record_evidence` become typed append actions of
`swarm_trace`. Query actions remain read-only. Append actions require an operation
identity, authority, and `LOCAL_APPEND_ONLY` effect.

### Internal

`orca_batch` becomes a bounded adapter optimization, not a Hermes tool. Every
member keeps its own identity/result and partial outcomes remain explicit.

`orca_events` becomes internal observation used by `swarm_status`,
`swarm_reconcile`, and `swarm_trace`. Because Orca 1.4.167 has no public event
stream, the first implementation is an eventual Aether projection and must not
claim provider ordering or completeness.

### Protected or deferred

`project_forget` moves to a future owner/admin-only boundary.

`learning_capture`, `learning_label`, `learning_dataset`, and `learning_export`
move to a separate default-off learning boundary and M7 gate. Learning remains an
Aether product objective; it is not required to prove the operational swarm.

## 5. Six missing aggregate capabilities

| Capability | Delivery | Guarantee | Qualification at this decision | Meaning |
|---|---|---|---|---|
| `events_read` | `AETHER_OWNED` | `DEGRADED` | `UNQUALIFIED` | polling + journal/receipt projection; no native event-stream claim |
| `resource_inventory` | `COMPOSED` | `DEGRADED` | `UNQUALIFIED` | correlation receipts plus public list/show/status; admitted resources only |
| `resource_cleanup` | `COMPOSED` | `DEGRADED` | `UNQUALIFIED` | idempotent compensation over admitted resources; non-atomic |
| `run_cancel` | `COMPOSED` | `DEGRADED` | `UNQUALIFIED` | stop/fence child resources and reconcile; non-atomic |
| `run_close` | `AETHER_OWNED` | `DEGRADED` | `UNQUALIFIED` | semantic closeout after verified cleanup; not an Orca Run-close transition |
| `task_cancel` | `COMPOSED` | `DEGRADED` | `UNQUALIFIED` | stop/fence task resources and reconcile; never aliases failed status to cancelled |

The other 49 M1.2 capabilities have public commands and therefore use delivery
`NATIVE`, intended guarantee `FULL`, and current qualification `UNQUALIFIED` until
version-pinned response/effect/timeout/recovery fixtures pass.

## 6. Composition requirements

A composition is admitted only when one version-pinned plan proves:

1. typed ordered public Orca operations;
2. exact preconditions and owned/correlated resource scope;
3. caller operation identity plus stable step identities;
4. effect class per step;
5. durable request before possible mutation;
6. timeout and possible-delivery classification;
7. observation and reconciliation;
8. partial-result semantics;
9. idempotent replay/conflict behavior;
10. cleanup and survivor inventory;
11. rollback/compensation limits;
12. provider/schema drift refusal.

No composition may use private database/storage, unrestricted prose, shell
interpolation, GUI automation, reset-as-cleanup, or broad process termination.

## 7. Revised D1 rule

D1 may be proposed to the product owner only when:

- exact Orca launcher/artifact/version/catalog/schema-bundle/adapter identities are
  pinned;
- every capability required by an enabled tool is `NATIVE`, `COMPOSED`, or
  `AETHER_OWNED`;
- every such capability is `PROVEN`, with any `DEGRADED` guarantee explicitly
  accepted;
- no enabled path depends on `DEFERRED`, `UNSUPPORTED`, `UNQUALIFIED`, or `UNKNOWN`;
- lifecycle cold start, restart/recovery, stop, reconciliation, and zero-survivor
  cleanup pass twice in fresh isolation;
- idempotency, partial effects, timeout, crash/restart, schema drift, and fencing
  tests pass;
- the exact debt ledger is accepted for the candidate.

This is stricter than “the command exists” and less artificial than “55/55 must
be provider-native.”

## 8. Current authorization and gates

The owner authorized the ordered R0-R6 sequence in the canonical task.

Authorized:

- successor design/contracts and deterministic schemas;
- exact isolated AppImage lifecycle correction and requalification;
- default-off adapter, journal, correlation, and reconciler foundation;
- one no-model two-worker synthetic provider-backed slice if prerequisites pass;
- local atomic English commits.

Still blocked:

- D1 grant before evidence;
- MCP registration/callability or persistent service activation;
- private/undocumented Orca interfaces;
- model-backed Daimons, credentials, account/provider selection, or spending;
- push, merge, rebase, amend, tag, Release, deployment, or activation.

## 9. Decision consequence

The redesigned architecture is potentially sufficient for agent orchestration:
Hermes and Aether retain product semantics and safety while Orca provides runtime
mechanics. That is a target hypothesis, not a current capability claim. R3-R5
must still produce real executed evidence.
