# Orca Adapter Redesign and Bounded Orchestration Qualification

> **Status:** AUTHORIZED / FROZEN / IN PROGRESS
> **Owner authorization:** Christopher (DarkArty07), 2026-08-08
> **Execution owner:** Hermes
> **Candidate:** Aether Agents `v0.22.0.dev0`
> **Branch:** `feature/v0.22.0-orca-transition`
> **Base commit:** `b807c6282334aaee2be8e19b41f6fc77eb6ac704`
> **Base tree:** `c8c1ff86f31631c0818ec159bd970d7cca86bb61`
> **Worktree:** `/home/darkarty/Desktop/agentes/aether/.aether/worktrees/feature-v0.22.0-orca-redesign`
> **Draft PR:** `#163`; remains Draft

## 1. Goal

Redesign the Aether/Hermes-to-Orca boundary around the public capabilities Orca
actually exposes, implement the minimum coherent default-off adapter and
reconciliation foundation, and prove or reject an isolated two-worker synthetic
orchestration slice without pretending that composed behavior is provider-native.

The redesign must preserve the Aether product contract while avoiding a duplicate
Orca scheduler, private-state access, free-form shell control, GUI automation, or
hidden fallback.

## 2. Current acceptance condition

This task is complete only when all of the following are true:

1. the product/authority documents define one coherent revised boundary;
2. the operational Hermes MCP catalog contains exactly 15 designed tools and
   remains default-off with exactly zero registered/callable tools;
3. every required provider capability has a delivery class and a separate
   assurance state;
4. the exact Orca lifecycle harness no longer mixes AppImage preparation output
   with the structured runtime protocol;
5. the real isolated lifecycle is executed twice and its result is recorded
   honestly as `PASS`, `BLOCKED`, or `REJECTED`;
6. the adapter/reconciler foundation has deterministic RED/GREEN tests for
   version pinning, typed argv construction, receipts, partial effects,
   `UNKNOWN`, idempotency, and reconciliation;
7. an isolated two-worker synthetic slice is actually executed when its
   prerequisites pass, or the exact blocker and completed lower-level evidence
   are preserved;
8. focused and affected regression gates pass for the exact final tree;
9. no MCP registration, global Orca mutation, model-backed worker call,
   credential use, deployment, merge, tag, Release, or activation occurs;
10. cleanup proves zero task-owned process, listener, mount, worktree, and
    temporary-root survivors.

A blocked provider result does not invalidate successfully completed design,
protocol, or deterministic adapter work. It does block any dependent real slice
and must never be relabeled as success.

## 3. Non-goals and protected effects

This task does **not** authorize:

- MCP registration or activation in Hermes;
- a persistent Orca service or modification of installed/global Orca state;
- private Orca database/storage access;
- UI/browser automation for provider control;
- parsing unrestricted prose as control input;
- arbitrary shell, command interpolation, or caller-supplied argv;
- restoration of Olympus, Harmonia, ACPManager, `talk_to`, or a renamed fallback;
- a second Aether operational Run/Task/Dispatch scheduler;
- real model-backed Daimon execution, provider/account selection, credentials, or
  spending;
- push, merge, rebase, amend, tag, GitHub Release, deployment, or activation;
- changes to the dirty primary checkout.

Local atomic English commits are allowed. Integration remains a later gate.

## 4. Revised ownership boundary

### Hermes owns

- user-intent interpretation;
- product contract, non-goals, acceptance, and stop condition;
- Task DAG, participant selection, routing, and synthesis;
- direct-versus-swarm decision;
- technical verification and completion proposal.

### Aether MCP owns

- coordinator/project/profile/worktree admission and correlation;
- contract generations and deterministic validation;
- participant/effect/scope policy;
- version-pinned provider schemas and capability declarations;
- operation identity, durable request/receipt journal, and idempotency;
- composition plans over public typed Orca operations;
- reconciliation obligations and conservative `UNKNOWN` handling;
- bounded semantic decisions, evidence references, trace, and closeout.

Aether records product-semantic closeout and correlations. It does not mirror or
independently schedule mutable Orca Run/Task/Dispatch state.

### Orca owns

- mutable Run, Task, Dispatch, worker, terminal, worktree, and operational-message
  state;
- actual process/resource effects;
- public runtime recovery and cleanup mechanics it exposes.

### Git/filesystem and executed checks own

- artifact bytes and repository lineage;
- test, build, and rendered-result evidence.

## 5. Capability classification model

One overloaded label is insufficient. Each capability therefore has three axes.

### Delivery class

- `NATIVE`: one public version-pinned Orca operation performs the capability;
- `COMPOSED`: an Aether-owned plan uses only public typed Orca operations;
- `AETHER_OWNED`: product policy, correlation, journal, evidence, or semantic
  closeout that does not claim provider operational ownership;
- `DEFERRED`: intentionally unavailable in the current operational surface;
- `UNSUPPORTED`: no safe admitted implementation exists.

### Guarantee

- `FULL`: the intended contract has no known semantic reduction;
- `DEGRADED`: atomicity, immediacy, completeness, or provider-native semantics
  are explicitly lower.

### Qualification

- `PROVEN`: deterministic contract and executed evidence cover the declared
  guarantee;
- `UNQUALIFIED`: a candidate path exists but has not passed its fixture;
- `UNKNOWN`: available evidence cannot classify the actual effect.

`NATIVE` never means its schema, timeout, or recovery metadata came from Orca's
catalog, and `DEGRADED` never means implemented or proven. Delivery, guarantee,
qualification, and schema authority are recorded separately.

## 6. Revised operational MCP catalog

The default-off Hermes operational contract contains these 15 tools:

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

`swarm_trace` gains typed actions for query, decision append, and evidence append.
The server validates each action's effect and requires an operation identity for
append actions.

### Internal capabilities, not separate public tools

- provider observation/polling used by status, trace, and reconciliation;
- bounded independent-call batching used only as an implementation optimization;
- correlation-backed resource inventory;
- compensation/cleanup plans;
- Run/Task cancel and product closeout compositions;
- decision/evidence append services behind `swarm_trace`.

### Protected or deferred surfaces

- `project_forget`: owner/admin-only future surface, not the operational Hermes
  MCP;
- `learning_capture`, `learning_label`, `learning_dataset`, `learning_export`:
  deferred to a separate default-off learning boundary and later gate.

Removing a public schema does not delete the product capability or historical
M2.2 evidence. M2.2 remains accepted for its exact historical tree; this task
creates a successor alpha contract.

## 7. Six missing Orca aggregates

| Capability | Delivery | Guarantee | Qualification | Honest limitation |
|---|---|---|---|---|
| `events_read` | `AETHER_OWNED` polling/journal projection | `DEGRADED` | `UNQUALIFIED` | eventual observation; no native event stream claim |
| `resource_inventory` | `COMPOSED` from correlation receipts plus public list/show/status | `DEGRADED` | `UNQUALIFIED` | covers admitted/created resources; external drift may remain unknown |
| `resource_cleanup` | `COMPOSED` compensation plan | `DEGRADED` | `UNQUALIFIED` | non-atomic; partial cleanup remains explicit |
| `run_cancel` | `COMPOSED` dispatch/worker/terminal stop plus reconciliation | `DEGRADED` | `UNQUALIFIED` | cancellation request is not aggregate atomic cancellation |
| `run_close` | `AETHER_OWNED` semantic closeout after verified cleanup | `DEGRADED` | `UNQUALIFIED` | does not claim an Orca-native Run-close transition |
| `task_cancel` | `COMPOSED` worker/dispatch/terminal stop plus reconciliation | `DEGRADED` | `UNQUALIFIED` | `task-update failed` is never relabeled as cancellation |

No `UNQUALIFIED` composition becomes callable or satisfies D1 until its exact
fixture passes.

## 8. Revised D1 rule

D1 no longer requires every Aether capability to be provider-native. D1 may become
ready only when:

1. exact Orca build, artifact, catalog, schema bundle, and adapter identities are
   pinned;
2. every capability required by an enabled tool is `NATIVE`, `COMPOSED`, or
   `AETHER_OWNED` and has `PROVEN` or explicitly accepted `DEGRADED` assurance;
3. no enabled tool depends on `DEFERRED`, `UNSUPPORTED`, or `UNQUALIFIED` behavior;
4. every composition proves preconditions, step identities, effects, timeout,
   `UNKNOWN`, observation, reconciliation, cleanup, partial results, rollback
   limits, and idempotent replay;
5. exact lifecycle, restart/recovery, and zero-survivor cleanup pass in isolation;
6. provider drift fails closed;
7. the product owner explicitly accepts the remaining debt and degraded
   guarantees.

D1 remains ungranted while this task executes. Implementation authorization is not
runtime acceptance.

## 9. Milestones and live checklist

### R0 — Isolation and frozen plan

- [x] Confirm feature base commit/tree and Draft PR state.
- [x] Confirm dirty primary checkout is outside scope.
- [x] Create exclusive redesign worktree.
- [x] Freeze this task contract, protected effects, milestones, and stop boundary.
- [x] Validate documentation references/YAML and commit R0 atomically.

**Acceptance:** exact isolated worktree, versioned plan, truthful authorization
state, no product/provider/runtime effect.

### R1 — Ownership, catalog, and debt redesign

- [x] Amend canonical architecture, MCP contract, orchestration, roadmap, and
      provider-decision documents.
- [x] Replace the 24-tool operational claim with the 15-tool catalog.
- [x] Record the three-axis capability model and six aggregate adaptations.
- [x] Add a debt ledger with consequence, severity, mitigation, acceptance,
      removal condition, and affected Orca version.
- [x] Cross-check every canonical reference and structured status projection.

**Acceptance:** one coherent owner per fact/effect; no document claims current
runtime support; D1 rule is measurable and fail-closed.

### R2 — Successor alpha protocol contract

- [x] Publish the successor as `aether.mcp/v1alpha2` without rewriting the
      historical `v1alpha1` snapshot.
- [x] Write RED tests for the exact 15-tool set and rejected removed names.
- [x] Write RED tests for typed `swarm_trace` query/decision/evidence actions.
- [x] Implement the minimum schema/validator changes.
- [x] Regenerate deterministic schema snapshot.
- [x] Prove zero callable/registered tools and no side effects.

**Acceptance:** focused protocol tests, schema drift, stdio smoke, Ruff, and
compileall pass; all removed names fail validation; registration remains zero.

### R3 — Exact Orca lifecycle adaptation

- [x] Write RED tests proving preparation output cannot enter runtime framing.
- [x] Verify exact AppImage identity, extract into the owned root as a distinct
      bounded preparation step, and execute the staged `AppRun` afterward.
- [x] Reserve runtime stdout for one structured protocol stream.
- [x] Re-run focused harness tests.
- [ ] Execute the exact real lifecycle twice in fresh namespaces.
- [x] Record `BLOCKED` evidence and zero survivors without relaxing fail-closed
      behavior.

The two accepted real repetitions remain unchecked because coordinator bootstrap
blocked the lifecycle after cold readiness. R3 is closed `BLOCKED`, not silently
treated as complete/PASS.

**Acceptance target:** the historical extraction/framing defect is fixed by
construction and execution; full real lifecycle requires two reproducible probes.
R3 met the first clause and cleanup, but closed `BLOCKED` before the second.

### R4 — Adapter and reconciler foundation

- [x] Write RED tests for pinned command descriptions and structured argv.
- [x] Implement version/capability binding without free-form shell.
- [x] Write RED tests for durable operation receipts, idempotent replay/conflict,
      possible delivery, and reconciliation.
- [x] Implement the minimum journal/correlation/reconciler services.
- [x] Leave inventory/cleanup/cancel/close and every provider mutation unavailable;
      R3 proved no trusted coordinator binding.
- [x] Prove provider schema/build drift, stale/foreign binding, malformed receipts,
      symlink escape and operation conflicts fail closed.

**Acceptance:** deterministic adapter tests cover positive, negative, timeout,
partial, restart, and reconciliation paths; no tool registration or ambient
provider effect.

### R5 — Isolated two-worker synthetic slice

- [ ] Freeze one deterministic two-Task fixture with separate worktrees/scopes.
- [ ] Start both synthetic workers before observing either result.
- [ ] Prove measured overlap and one bounded message/handoff.
- [ ] Exercise one controlled failure and retry with new lineage.
- [ ] Exercise cancellation or exact honest inability.
- [ ] Integrate deterministic artifacts and run checks.
- [ ] Close/reconcile and prove zero survivors.
- [x] Close the milestone `BLOCKED / NOT EXECUTED` because the trusted coordinator
      prerequisite failed before any runtime resource could be admitted.

All runtime fixture items remain unchecked because R3 did not qualify the trusted
coordinator binding and R4 deliberately contains no provider executor.

**Acceptance:** actual isolated provider-backed orchestration mechanics pass with
no model/provider-account call. If R3/R4 prerequisites fail, R5 closes `BLOCKED`
with the exact missing evidence rather than using another execution path.

### R6 — Final acceptance audit and handoff

- [ ] Inspect every changed file and requirement-to-evidence mapping.
- [ ] Run focused, affected, full, schema, packaging, smoke, secret, and forbidden-
      path checks proportional to the final changes.
- [ ] Verify exact committed tree in a detached clean environment.
- [ ] Reconcile ROADMAP, STATUS, AGENTS, acceptance evidence, and this checklist.
- [ ] Verify no task-owned resources survive.
- [ ] Produce a reproducible handoff and stop before integration/activation.

**Acceptance:** clean exact candidate, honest unknowns/blockers, no unrelated
changes, and no protected effect.

## 10. Execution and reporting discipline

- Exactly one milestone is `IN_PROGRESS` at a time.
- Hermes reports each milestone result to the product owner before advancing.
- Every implementation milestone follows RED -> prove intended failure -> minimum
  GREEN -> focused regression -> affected regression -> source/diff inspection ->
  atomic English commit -> committed-tree verification.
- The same failed technical approach is attempted at most three times.
- Historical acceptance records remain historical; successor decisions are added
  rather than rewriting past evidence as though it never occurred.
- Missing evidence is `UNKNOWN` or `BLOCKED`, never zero or PASS.

## 11. Current progress

| Milestone | State | Evidence |
|---|---|---|
| R0 | `COMPLETED` | isolated worktree at base `b807c62`; frozen task; YAML/reference validation PASS |
| R1 | `COMPLETED` | 15-tool contract, three-axis 55-capability matrix, six aggregate adaptations, debt ledger, revised D1 |
| R2 | `COMPLETED` | `v1alpha2`; 15 schemas; 105 passed/1 deselected; Ruff/compileall/snapshot/zero-tool smoke PASS |
| R3 | `CLOSED_BLOCKED` | framing/cold status PASS; coordinator bootstrap unqualified; 23 passed/1 deselected; zero survivors; D1 false |
| R4 | `COMPLETED_RESTRICTED` | exact binding, immutable argv, atomic journal, idempotency, UNKNOWN/reconciliation; 16 passed; mutations unavailable; 0 tools |
| R5 | `CLOSED_BLOCKED_NOT_EXECUTED` | coordinator binding unqualified; 0 tools/executors/workers/models/resources; lower-level evidence preserved |
| R6 | `PENDING` | — |

## 12. Final stop boundary

Stop after R6. Report what was proved, what remains degraded or unknown, and the
single next material gate. Do not push, merge, tag, publish, register, activate,
use model credentials, spend, or start persistent services under this task.
