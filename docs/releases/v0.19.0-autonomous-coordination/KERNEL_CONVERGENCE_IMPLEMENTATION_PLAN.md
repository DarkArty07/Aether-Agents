# Kernel-Backed Snake Convergence Implementation Plan

> **For Hermes:** execute only after Christopher explicitly authorizes implementation. Follow TDD, milestone-implementation-governance, scoped staging, deterministic adversarial verification, and direct Hermes acceptance. Do not dispatch Athena until the user explicitly reactivates it.

**Goal:** compose the existing R2–R7 primitives into one authoritative, reconstructable, default-off runtime for a fixed Snake workflow without PilotStore writes.

**Architecture:** a small `KernelRunService` is the only command boundary for semantic workflow changes. It validates commands against durable projections, appends typed facts through `SQLiteLedger`, and exposes read projections. A dispatcher consumes authoritative outbox records and calls public ACPManager methods through the existing Olympus adapter. Evidence, review, and closure are derived from durable state; Olympus retains lifecycle ownership.

**Tech stack:** Python 3.11+, dataclasses/enums, SQLite, asyncio, existing Olympus ACP APIs, pytest, Ruff. No new runtime dependency.

**Current authorization/status:** R9–R11 are complete; R11 is committed in `0912f1d` after migration, uncertain-effect recovery and concurrent-worker fencing closure. R12–R13 remain blocked pending separate authorization. Do not run live ACP, execute the Snake pilot, activate, merge, tag or publish from this checkpoint.

---

## 1. Composition map

| Stage | Existing component | Proposed call site | Reads authority | Writes fact/projection | Primary failure |
|---|---|---|---|---|---|
| Compile fixture | `pilot_compiler.py` | `snake_compiler.py::compile_kernel_snake()` | immutable manifest | contract/plan drafts | nondeterministic or incomplete mapping |
| Create run | `ExecutionContract`, `SQLiteLedger` | `kernel_runtime.py::KernelRunService.create_run()` | contract head, runtime mode | run/plan/budget initialized | duplicate/mismatched run |
| Evaluate readiness | `ProjectionReducer`, admission | `KernelRunService.ready_tasks()` | workflow + budget projection | none | stale/caller projection |
| Admit attempt | `AdmissionEngine` plus durable budget | `KernelRunService.admit_attempt()` | task/deps/budget/contract | budget reserved, attempt created | future obligations unfunded |
| Acquire ownership | ledger lease methods | `KernelRunService.acquire_attempt()` | active attempt and lease | lease/fence binding | stale owner/epoch |
| Stage dispatch | `LedgerNativeTransport.stage()` | `kernel_dispatcher.py::stage_ready()` | attempt/lease/plan/snapshot | dispatch intent/outbox | intent not bound to attempt |
| Deliver | `LedgerNativeTransport.claim()` + adapter | `KernelDispatcher.dispatch_once()` | claimed outbox/envelope | delivery accepted/failed | duplicate or uncertain delivery |
| Open ACP | `OlympusRuntimeAdapter`, `ACPManager` | adapter method consuming authoritative envelope | immutable dispatch envelope | session binding observation | identity mismatch/partial open |
| Observe execution | `ACPManager.poll()` | `KernelDispatcher.observe_once()` | session binding/current fence | runtime observation/result/UNKNOWN | response loss/stale result |
| Reconcile | effects state machine | `kernel_dispatcher.py::reconcile_unknown()` | snapshots/session/Git/process facts | reconciled result or manual block | unsafe retry |
| Verify | new controlled verifier | `evidence_runtime.py::KernelVerifier.run()` | approved command/scope/current generation | verifier receipt/snapshot | agent claim treated as receipt |
| Review | `ReviewGate` | `review_runtime.py::evaluate_assigned_gate()` | assignment/session/capability/snapshot | finding/gate result | caller-declared independence |
| Build closure | `validate_closure()` | `closure_runtime.py::ClosureSnapshotBuilder.build()` | all current projections | closure requested/snapshot hash | incomplete/stale facts |
| Close | cleanup plan + ACP lifecycle | `ClosureOrchestrator.close()` | persisted verdict/cleanup state | cleanup receipts/lifecycle | false CLOSED after failed cleanup |

## 2. Minimum durable model

### Reuse unchanged or with narrow extension

- `ExecutionContract`, `ContractLimits`, `TaskState`, `EvidenceGate` from `contracts.py`.
- `Principal`, `Scope`, signed event drafts and writer context from `protocol.py`/`ledger.py`.
- `EffectSpec`, `EffectLifecycle`, `can_retry()` and transition rules from `effects.py`.
- `ReviewGate`, `ReviewFinding`, `GateEvaluation` and waiver types from `review.py`.
- `ClosureProposal`, `CompletionAuthority`, `CompletionState`, `validate_closure()` from `closure.py`.
- `PilotManifest` and `PilotTask` as the fixture DSL only.

### Add semantic records because no sufficient type exists

- `RunRecord`: run ID, mode, contract generation, plan revision, semantic outcome, operational lifecycle.
- `TaskRecord`: task identity, dependencies, owner role, state, artifact generation.
- `AttemptRecord`: attempt number, superseded attempt, state, lease resource/epoch, budget reservation.
- `TaskSessionBinding`: run/task/attempt, logical session, ACP session, project root, lease fence.
- `DispatchRecord`: message/idempotency identity and delivery/execution lifecycle.
- `BudgetAccount` and `BudgetReservation`: authorized/reserved/committed/spent/released by category.
- `EvidenceRecord`: provenance, producer, run/task/attempt/session, generation, payload hash and trust class.
- `GateRecord`: assigned reviewer/session/capability, generation, attempts and result.
- `ClosureRecord`: semantic verdict, operational lifecycle, snapshot hash and cleanup receipts.

These are domain records, not a third workflow framework. Their only mutation path is typed ledger events through `KernelRunService`.

## 3. Proposed source boundaries

| Path | Responsibility |
|---|---|
| `src/olympus_v3/coordination/workflow.py` | durable domain records, legal transitions, projection helpers |
| `src/olympus_v3/coordination/kernel_runtime.py` | composition root and command boundary |
| `src/olympus_v3/coordination/budget.py` | durable account/reservation invariants |
| `src/olympus_v3/coordination/kernel_dispatcher.py` | outbox→Olympus bridge, observation and reconciliation |
| `src/olympus_v3/coordination/evidence_runtime.py` | evidence provenance and controlled verifier |
| `src/olympus_v3/coordination/review_runtime.py` | authoritative reviewer assignment/binding |
| `src/olympus_v3/coordination/closure_runtime.py` | snapshot builder, persisted verdict, cleanup executor |
| `src/olympus_v3/coordination/snake_compiler.py` | deterministic fixture→kernel translation |
| `src/olympus_v3/coordination/projections.py` | recognize/project the new durable semantic events |
| `src/olympus_v3/coordination/ledger.py` | only narrow transactional/binding additions, including outbox completion verification |
| `src/olympus_v3/coordination/olympus_adapter.py` | consume authoritative dispatch envelope; preserve pilot method for legacy only |
| `src/olympus_v3/coordination/__init__.py` | public exports after focused export tests pass |

Do not modify `ACPManager` unless an isolated ACP lifecycle RED proves a defect there. Do not add kernel knowledge to ACPManager.

## 4. Exact RED test plan

### Task 1 — Workflow state and rebuild

**Create:** `tests/coordination/test_kernel_workflow.py`

RED tests:

1. `test_run_projection_rebuild_restores_tasks_attempts_sessions_gates_budget_and_closure`
   - invariant: semantic run state is reconstructable;
   - fails today: no workflow projection/types.
2. `test_only_kernel_service_can_advance_semantic_task_state`
   - invariant: caller DTO cannot mutate authority;
   - fails today: no command boundary.
3. `test_kernel_run_selects_one_runtime_mode_and_cannot_switch_mid_run`
   - invariant: no mixed legacy/kernel execution.
4. `test_kernel_backed_run_never_writes_pilot_store`
   - invariant: no dual-write.
5. `test_later_artifact_write_increments_generation_and_stales_prior_gates`
   - invariant: evidence invalidation is automatic.

Focused command:

```text
uv run pytest -q tests/coordination/test_kernel_workflow.py
```

### Task 2 — Durable budget

**Create:** `tests/coordination/test_kernel_budget.py`

RED tests:

1. `test_budget_conservation_authorized_equals_available_reserved_committed_and_spent`
2. `test_correction_without_verification_rereview_recovery_and_cleanup_reserve_is_rejected`
3. `test_retry_and_replan_require_fresh_admission`
4. `test_release_returns_unused_reservation_without_erasing_spend`
5. `test_only_contract_amendment_authority_can_raise_authorized_budget`
6. `test_concurrent_reservations_cannot_overdraw_account`
7. `test_budget_projection_rebuild_is_equivalent`

### Task 3 — Outbox binding and dispatch

**Create:** `tests/coordination/test_kernel_dispatcher.py`

RED tests:

1. `test_complete_outbox_rejects_missing_or_unbound_completion_event`
2. `test_dispatch_intent_is_durable_before_olympus_call`
3. `test_delivery_ack_does_not_complete_task`
4. `test_dispatch_envelope_binds_run_task_attempt_contract_plan_lease_and_snapshot`
5. `test_duplicate_dispatch_replays_one_session_binding`
6. `test_response_loss_after_accepted_dispatch_becomes_unknown`
7. `test_unknown_result_blocks_retry_until_reconciled`
8. `test_failed_delivery_before_session_acceptance_is_retryable`
9. `test_process_restart_recovers_claimed_dispatch_without_duplicate_semantic_effect`

Use a fake ACPManager first. No real Daimon in this milestone.

### Task 4 — Lease/fence and ACP binding

**Create:** `tests/coordination/test_kernel_fencing.py`

RED tests:

1. `test_task_session_binding_persists_logical_and_acp_identity_with_fence`
2. `test_expired_lease_marks_attempt_orphaned_and_persists_cancel_intent`
3. `test_stale_fence_result_cannot_mutate_task_or_budget`
4. `test_superseded_attempt_rejects_late_terminal_result`
5. `test_cancel_observation_does_not_clear_unknown_effect_without_reconciliation`
6. `test_current_fence_result_is_idempotent`
7. `test_historical_olympus_status_cannot_override_new_attempt`

### Task 5 — Evidence and controlled verifier

**Create:** `tests/coordination/test_kernel_evidence.py`

RED tests:

1. `test_agent_claim_cannot_satisfy_verification_gate`
2. `test_json_embedded_in_prose_remains_unstructured_result`
3. `test_verifier_receipt_binds_argv_cwd_exit_output_hashes_attempt_session_and_generation`
4. `test_verifier_rejects_command_outside_contract_scope`
5. `test_later_write_stales_verifier_receipt`
6. `test_duplicate_receipt_identity_is_idempotent_and_mismatch_fails`
7. `test_operator_attestation_requires_explicit_authority_reason_scope_and_snapshot`
8. `test_verifier_timeout_is_observed_failure_not_agent_claim`

The verifier executes only allowlisted local commands in a supplied fixture root. It receives no shell string and no secrets.

### Task 6 — Generic review authority without Athena dispatch

**Create:** `tests/coordination/test_kernel_review.py`

RED tests:

1. `test_reviewer_identity_is_derived_from_kernel_assignment_and_olympus_binding`
2. `test_owner_or_writer_session_cannot_satisfy_independent_gate`
3. `test_review_assignment_has_read_only_capability`
4. `test_stale_generation_review_cannot_pass_current_gate`
5. `test_review_finding_and_gate_result_are_persisted_and_rebuildable`
6. `test_caller_constructed_gate_evaluation_without_assignment_is_rejected`
7. `test_review_attempt_budget_is_reserved_before_dispatch`

These tests validate generic reviewer assignment, capability, independence, persistence, and rebuild using controlled identities/fakes. They must not assume that Athena is the reviewer and do not authorize an Athena session. While Athena remains suspended, executable milestone acceptance belongs to Hermes using deterministic evidence.

### Task 7 — Closure and cleanup

**Create:** `tests/coordination/test_kernel_closure.py`

RED tests:

1. `test_closure_snapshot_builder_uses_authoritative_projection_only`
2. `test_caller_supplied_integrity_or_critical_evidence_flags_are_ignored`
3. `test_semantic_acceptance_enters_closing_not_closed`
4. `test_closed_requires_session_lease_child_and_listener_cleanup_receipts`
5. `test_cleanup_failure_preserves_semantic_outcome_and_sets_close_failed`
6. `test_close_retry_is_idempotent_and_does_not_duplicate_lifecycle_effects`
7. `test_stale_closure_snapshot_is_invalidated_by_later_write`
8. `test_no_public_path_can_set_closed_directly`

### Task 8 — Snake compiler and compatibility

**Create:**

- `tests/coordination/test_snake_kernel_compiler.py`
- `tests/coordination/test_pilot_kernel_compatibility.py`

RED tests:

1. `test_snake_manifest_compiles_deterministically_to_contract_plan_and_budget`
2. `test_compiled_graph_preserves_dependencies_roles_gates_and_effect_limits`
3. `test_legacy_run_remains_read_only_and_reproducible`
4. `test_kernel_compatibility_view_reads_projection_without_pilot_tables`
5. `test_dispatch_pilot_task_is_unreachable_from_kernel_mode`
6. `test_harmonia_shadow_cannot_mutate_fixed_plan`

### Task 9 — Fault injection E2E with fake runtime

**Create:** `tests/coordination/test_kernel_fault_injection.py`

Parameterized boundaries:

- before/after event append;
- before/after outbox claim;
- after session open before binding persistence;
- after possible effect before result;
- before/after evidence persistence;
- after verdict before cleanup;
- during each cleanup step.

Assert rebuild equivalence, no duplicate semantic transition, no unsafe retry, and honest `UNKNOWN`/`CLOSE_FAILED` outcomes.

### Task 10 — Real ACP integration gate

**Modify only after fake-runtime milestones pass:**

- `tests/coordination/test_olympus_adapter.py`
- `tests/test_acp_manager_lifecycle.py` only for isolated ACP defects
- create `tests/coordination/test_kernel_olympus_integration.py`

Required tests:

1. `test_authoritative_dispatch_opens_exact_expected_logical_session`
2. `test_olympus_ack_persists_delivery_without_semantic_completion`
3. `test_expired_attempt_requests_cancel_through_public_manager_api`
4. `test_close_session_failure_yields_cleanup_failure`
5. `test_no_private_acp_manager_registry_is_accessed`

No live gateway and no persistent profile process is required; use controlled fakes first, then one disposable actual-API smoke behind a separate gate.

## 5. Implementation milestones and logical commits

1. `docs: define kernel-backed convergence authority`
   - decision, roadmap, ACP audit, plan, canonical links.
2. `test: specify kernel workflow and budget invariants`
   - RED tests only; expected intentional failure recorded.
3. `feat: add durable kernel workflow projection`
   - workflow records, command service, rebuild.
4. `feat: add durable coordination budget authority`
   - reservations, re-admission, concurrency.
5. `test: specify ledger-native dispatch and fencing`
   - RED dispatch/fence tests.
6. `fix: bind outbox completion to authoritative events`
   - transactional event/run/task/attempt validation.
7. `feat: connect ledger-native dispatch to Olympus`
   - fake first; public ACP operations only.
8. `feat: add fenced execution reconciliation`
   - UNKNOWN, cancellation intent, stale-result rejection.
9. `test: specify trusted evidence and review binding`
10. `feat: add controlled verifier and evidence provenance`
11. `feat: bind independent review to runtime identity`
12. `test: specify executable semantic closure`
13. `feat: add authoritative closure and cleanup runtime`
14. `feat: compile Snake fixture into kernel contracts`
15. `test: add kernel fault-injection matrix`
16. `docs: record kernel convergence evidence and pilot gate`

Each commit stages only declared files. No blanket staging; the branch is already dirty with unrelated and historical R8 paths.

## 6. Verification gates per milestone

Run in order:

1. focused RED/GREEN test file;
2. affected coordination subsystem tests;
3. `uv run pytest -q tests/coordination`;
4. `uv run pytest -q`;
5. Ruff on changed Python files;
6. `python -m compileall` on changed package;
7. `git diff --check`;
8. source scan for forbidden PilotStore writes/private ACPManager access;
9. staged-path and secret scan before any commit.

Security-sensitive milestones for receipts, review, authority, and closure require a producer→artifact→consumer adversarial matrix, deterministic negative tests, direct source inspection, and reproduction of every claimed fix. Athena is not part of the current gate and must not be dispatched until explicit user reactivation.

## 7. Pilot gate after implementation

Implementation approval does not authorize the pilot. A later clean Snake run requires:

- all deterministic and fault-injection tests GREEN;
- code committed in atomic milestones;
- new disposable control DB/root;
- explicit run contract and budget;
- no live global coordination activation;
- no writes to historical PilotStore;
- no manual repair/fallback;
- process/listener preflight and cleanup verification;
- direct Hermes acceptance of the deterministic and fault-injection evidence;
- no Athena dependency while the global suspension remains active;
- explicit Christopher authorization.

## 8. Stop point

This plan is complete when documentation, paths, RED names, invariants, commands, and commit boundaries are verified. Stop before creating/modifying any Python source or test file. Implementation begins only after Christopher reviews the summary and explicitly authorizes the code phase.
