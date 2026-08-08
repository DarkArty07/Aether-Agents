# M1 Orca Provider Seam Qualification Matrix

> **Status:** ACCEPTED — PROVIDER SEAM INSUFFICIENT
> **Date:** 2026-08-07
> **Target Candidate:** Orca v1.4.167
> **Implementation Owner:** Repository-local external coding agent
> **Acceptance Owner:** Hermes

## 1. Executive Summary and Source Identity

This document evaluates the Orca CLI public structured seam against the frozen 24-tool Aether MCP contract and low-level M2–M5 provider requirements.

### 1.1 Collection Method & Identity Facts
Catalog data was collected via exactly two isolated executions of:
```text
/home/darkarty/.local/bin/orca agent-context --json
```
Each probe ran inside an isolated root with `HOME`, `TMPDIR`, `XDG_*` roots pointing strictly below `/tmp/aether-m1-2-*` with an explicit environment allowlist. Outputs were verified to be byte-identical with empty stderr.

```text
Launcher Path:        /home/darkarty/.local/bin/orca
Launcher Size:        1015 bytes
Launcher SHA-256:     89efbb54323f6eb2372aa59f32d0e0d330486ae6764b7dd5896705c638a90208
AppImage Path:        /home/darkarty/.local/opt/orca/orca-linux.AppImage
AppImage Size:        203385690 bytes
AppImage SHA-256:     813b11e99f7caa4bf8e4fc47200dd6c465f34a04d61e855adbd8822190592e33
Product Version:      1.4.167
Catalog Schema:       1
Declared Commands:    220
Actual Commands:      220
Catalog Bytes:        153496
Catalog SHA-256:      068e1d66737f19835536e4a1573a2f931bffe9821af9c1bdff855f902898944b
```

### 1.2 Classification Summary

- **Total Required M2–M5 Capabilities:** 55
- **SUPPORTED:** 0
- **PARTIAL:** 49
- **MISSING:** 6
- **UNKNOWN:** 0
- **Provisional Gate:** `INSUFFICIENT`

## 2. Aether MCP Tool Inventory & Ownership

The 24 frozen Aether MCP tools are partitioned between Aether-local responsibilities and Orca provider operations:

| Tool Name | Milestone | Ownership | Effect Class | Evaluated M1.2 | Provider Seam Required |
|---|---|---|---|---|---|
| `project_admit` | M2 | Aether-local | LOCAL_APPEND_ONLY | True | No (Aether-local) |
| `project_inspect` | M2 | Aether-local | READ_ONLY | True | No (Aether-local) |
| `swarm_validate` | M2 | Aether-local | READ_ONLY | True | No (Aether-local) |
| `swarm_start` | M3 | hybrid | LOCAL_REVERSIBLE | True | Yes |
| `swarm_status` | M3 | hybrid | READ_ONLY | True | Yes |
| `swarm_dispatch` | M4 | hybrid | LOCAL_REVERSIBLE | True | Yes |
| `swarm_message` | M4 | hybrid | LOCAL_APPEND_ONLY | True | Yes |
| `swarm_reconcile` | M3 | hybrid | LOCAL_APPEND_ONLY | True | Yes |
| `swarm_retry` | M4 | hybrid | LOCAL_REVERSIBLE | True | Yes |
| `swarm_cancel` | M3 | hybrid | LOCAL_REVERSIBLE | True | Yes |
| `swarm_record_decision` | M3 | Aether-local | LOCAL_APPEND_ONLY | True | No (Aether-local) |
| `swarm_record_evidence` | M3 | Aether-local | LOCAL_APPEND_ONLY | True | No (Aether-local) |
| `swarm_close` | M3 | hybrid | LOCAL_DESTRUCTIVE | True | Yes |
| `swarm_trace` | M2 | Aether-local | READ_ONLY | True | No (Aether-local) |
| `orca_search` | M2 | Orca-provider | READ_ONLY | True | Yes |
| `orca_describe` | M2 | Orca-provider | READ_ONLY | True | Yes |
| `orca_call` | M2 | Orca-provider | READ_ONLY | True | Yes |
| `orca_batch` | M4 | hybrid | LOCAL_REVERSIBLE | True | No distinct seam (Aether-owned batch envelope) |
| `orca_events` | M2 | Orca-provider | READ_ONLY | True | Yes |
| `learning_capture` | M7 | Aether-local | LOCAL_APPEND_ONLY | False | No (Aether-local) |
| `learning_label` | M7 | Aether-local | LOCAL_APPEND_ONLY | False | No (Aether-local) |
| `learning_dataset` | M7 | Aether-local | LOCAL_REVERSIBLE | False | No (Aether-local) |
| `learning_export` | M7 | Aether-local | LOCAL_REVERSIBLE | False | No (Aether-local) |
| `project_forget` | M7 | Aether-local | LOCAL_DESTRUCTIVE | False | No (Aether-local) |

## 3. Capability Matrix by Domain

Every required low-level M2–M5 capability domain is summarized below:

| Capability ID | Domain | Provider Command | Classification | Required By Tools |
|---|---|---|---|---|
| `agent_context_read` | identity_drift | `agent-context` | **PARTIAL** | `orca_describe`, `orca_search` |
| `cat_describe` | catalog_discovery | `agent-context` | **PARTIAL** | `orca_describe` |
| `cat_search` | catalog_discovery | `agent-context` | **PARTIAL** | `orca_search` |
| `coordinator_start` | recovery_reconciliation | `orchestration coordinator-start` | **PARTIAL** | `swarm_reconcile`, `swarm_start` |
| `coordinator_stop` | recovery_reconciliation | `orchestration coordinator-stop` | **PARTIAL** | `swarm_close` |
| `dispatch_abandon` | dispatch_fencing | `orchestration worker-abandon` | **PARTIAL** | `swarm_reconcile`, `swarm_retry` |
| `dispatch_show` | dispatch_fencing | `orchestration dispatch-show` | **PARTIAL** | `swarm_status` |
| `dispatch_submit` | dispatch_fencing | `orchestration dispatch` | **PARTIAL** | `swarm_dispatch`, `swarm_retry` |
| `events_read` | event_observation | *None* | **MISSING** | `orca_events` |
| `gate_create` | messaging_questions | `orchestration gate-create` | **PARTIAL** | `swarm_message` |
| `gate_list` | messaging_questions | `orchestration gate-list` | **PARTIAL** | `swarm_status` |
| `gate_resolve` | messaging_questions | `orchestration gate-resolve` | **PARTIAL** | `swarm_message` |
| `message_check` | messaging_questions | `orchestration check` | **PARTIAL** | `orca_events`, `swarm_status` |
| `message_inbox` | messaging_questions | `orchestration inbox` | **PARTIAL** | `swarm_message`, `swarm_status` |
| `message_send` | messaging_questions | `orchestration send` | **PARTIAL** | `swarm_message` |
| `orchestration_reset` | recovery_reconciliation | `orchestration reset` | **PARTIAL** | `swarm_reconcile` |
| `question_ask` | messaging_questions | `orchestration ask` | **PARTIAL** | `swarm_message` |
| `question_reply` | messaging_questions | `orchestration reply` | **PARTIAL** | `swarm_message` |
| `resource_cleanup` | resource_cleanup | *None* | **MISSING** | `swarm_close` |
| `resource_inventory` | resource_cleanup | *None* | **MISSING** | `swarm_close`, `swarm_status` |
| `run_cancel` | run_lifecycle | *None* | **MISSING** | `swarm_cancel` |
| `run_close` | run_lifecycle | *None* | **MISSING** | `swarm_close` |
| `run_create` | run_lifecycle | `orchestration run-create` | **PARTIAL** | `swarm_start` |
| `run_current` | run_lifecycle | `orchestration run-current` | **PARTIAL** | `swarm_status` |
| `run_list` | run_lifecycle | `orchestration run-list` | **PARTIAL** | `swarm_status` |
| `run_show` | run_lifecycle | `orchestration run-show` | **PARTIAL** | `swarm_status` |
| `run_use` | run_lifecycle | `orchestration run-use` | **PARTIAL** | `swarm_start` |
| `runtime_status_read` | identity_drift | `status` | **PARTIAL** | `swarm_status` |
| `task_cancel` | task_lineage | *None* | **MISSING** | `swarm_cancel` |
| `task_create` | task_lineage | `orchestration task-create` | **PARTIAL** | `swarm_start` |
| `task_list` | task_lineage | `orchestration task-list` | **PARTIAL** | `swarm_status` |
| `task_retry_lineage` | task_lineage | `orchestration worker-start` | **PARTIAL** | `swarm_retry` |
| `task_update` | task_lineage | `orchestration task-update` | **PARTIAL** | `swarm_reconcile`, `swarm_status` |
| `terminal_close` | terminal_operations | `terminal close` | **PARTIAL** | `orca_call`, `swarm_close` |
| `terminal_create` | terminal_operations | `terminal create` | **PARTIAL** | `orca_call`, `swarm_dispatch` |
| `terminal_list` | terminal_operations | `terminal list` | **PARTIAL** | `orca_call`, `swarm_status` |
| `terminal_read` | terminal_operations | `terminal read` | **PARTIAL** | `orca_call`, `swarm_status` |
| `terminal_send` | terminal_operations | `terminal send` | **PARTIAL** | `orca_call` |
| `terminal_show` | terminal_operations | `terminal show` | **PARTIAL** | `orca_call`, `swarm_status` |
| `terminal_stop` | terminal_operations | `terminal stop` | **PARTIAL** | `orca_call`, `swarm_cancel`, `swarm_close` |
| `terminal_wait` | terminal_operations | `terminal wait` | **PARTIAL** | `orca_call`, `swarm_status` |
| `worker_abandon` | worker_lifecycle | `orchestration worker-abandon` | **PARTIAL** | `swarm_reconcile` |
| `worker_env_add` | worker_lifecycle | `environment add` | **PARTIAL** | `swarm_dispatch` |
| `worker_env_show` | worker_lifecycle | `environment show` | **PARTIAL** | `swarm_status` |
| `worker_read` | worker_lifecycle | `orchestration worker-read` | **PARTIAL** | `swarm_status` |
| `worker_show` | worker_lifecycle | `orchestration worker-show` | **PARTIAL** | `swarm_status` |
| `worker_start` | worker_lifecycle | `orchestration worker-start` | **PARTIAL** | `swarm_dispatch`, `swarm_retry` |
| `worker_stop` | worker_lifecycle | `orchestration worker-stop` | **PARTIAL** | `swarm_cancel`, `swarm_close` |
| `worktree_create` | worktree_management | `worktree create` | **PARTIAL** | `swarm_dispatch` |
| `worktree_current` | worktree_management | `worktree current` | **PARTIAL** | `swarm_status` |
| `worktree_list` | worktree_management | `worktree list` | **PARTIAL** | `swarm_status` |
| `worktree_ps` | worktree_management | `worktree ps` | **PARTIAL** | `swarm_close`, `swarm_status` |
| `worktree_remove` | worktree_management | `worktree rm` | **PARTIAL** | `swarm_close` |
| `worktree_set` | worktree_management | `worktree set` | **PARTIAL** | `swarm_dispatch` |
| `worktree_show` | worktree_management | `worktree show` | **PARTIAL** | `swarm_status` |

## 4. Gaps and Seam Deficiencies

### 4.1 MISSING Capabilities (No Public Orca Seam)
The following 6 capabilities have no public structured command in the Orca catalog:

- **`events_read`** (Domain: `event_observation`): Read stream of Orca provider events.
  - *Gap:* No public structured Orca command satisfies this required capability.
  - *Required by tools:* ['orca_events']
- **`resource_cleanup`** (Domain: `resource_cleanup`): Idempotent aggregate cleanup of Run resources.
  - *Gap:* No public structured Orca command satisfies this required capability.
  - *Required by tools:* ['swarm_close']
- **`resource_inventory`** (Domain: `resource_cleanup`): Aggregate inventory of all allocated Orca resources.
  - *Gap:* No public structured Orca command satisfies this required capability.
  - *Required by tools:* ['swarm_close', 'swarm_status']
- **`run_cancel`** (Domain: `run_lifecycle`): Cancel an active Orca Run and stop all underlying tasks.
  - *Gap:* No public structured Orca command satisfies this required capability.
  - *Required by tools:* ['swarm_cancel']
- **`run_close`** (Domain: `run_lifecycle`): Close Orca Run and seal operational state.
  - *Gap:* No public structured Orca command satisfies this required capability.
  - *Required by tools:* ['swarm_close']
- **`task_cancel`** (Domain: `task_lineage`): Cancel specific Task in Orca Run.
  - *Gap:* No public structured Orca command satisfies this required capability.
  - *Required by tools:* ['swarm_cancel']

### 4.2 PARTIAL Capabilities (Command Exists, Unstructured Semantics)
The following 49 capabilities correspond to public commands in Orca, but lack machine-readable output schema declarations, structured timeout contracts, or structured recovery contracts in the catalog metadata:

- **`agent_context_read`** (Command: `agent-context`): Result schema, timeout semantics, and recovery semantics are not publicly structured in catalog metadata.
- **`cat_describe`** (Command: `agent-context`): Result schema, timeout semantics, and recovery semantics are not publicly structured in catalog metadata.
- **`cat_search`** (Command: `agent-context`): Result schema, timeout semantics, and recovery semantics are not publicly structured in catalog metadata.
- **`coordinator_start`** (Command: `orchestration coordinator-start`): Result schema, timeout semantics, and recovery semantics are not publicly structured in catalog metadata.
- **`coordinator_stop`** (Command: `orchestration coordinator-stop`): Result schema, timeout semantics, and recovery semantics are not publicly structured in catalog metadata.
- **`dispatch_abandon`** (Command: `orchestration worker-abandon`): Result schema, timeout semantics, and recovery semantics are not publicly structured in catalog metadata.
- **`dispatch_show`** (Command: `orchestration dispatch-show`): Result schema, timeout semantics, and recovery semantics are not publicly structured in catalog metadata.
- **`dispatch_submit`** (Command: `orchestration dispatch`): Result schema, timeout semantics, and recovery semantics are not publicly structured in catalog metadata.
- **`gate_create`** (Command: `orchestration gate-create`): Result schema, timeout semantics, and recovery semantics are not publicly structured in catalog metadata.
- **`gate_list`** (Command: `orchestration gate-list`): Result schema, timeout semantics, and recovery semantics are not publicly structured in catalog metadata.
- **`gate_resolve`** (Command: `orchestration gate-resolve`): Result schema, timeout semantics, and recovery semantics are not publicly structured in catalog metadata.
- **`message_check`** (Command: `orchestration check`): Result schema, timeout semantics, and recovery semantics are not publicly structured in catalog metadata.
- **`message_inbox`** (Command: `orchestration inbox`): Result schema, timeout semantics, and recovery semantics are not publicly structured in catalog metadata.
- **`message_send`** (Command: `orchestration send`): Result schema, timeout semantics, and recovery semantics are not publicly structured in catalog metadata.
- **`orchestration_reset`** (Command: `orchestration reset`): Result schema, timeout semantics, and recovery semantics are not publicly structured in catalog metadata.
- **`question_ask`** (Command: `orchestration ask`): Result schema, timeout semantics, and recovery semantics are not publicly structured in catalog metadata.
- **`question_reply`** (Command: `orchestration reply`): Result schema, timeout semantics, and recovery semantics are not publicly structured in catalog metadata.
- **`run_create`** (Command: `orchestration run-create`): Result schema, timeout semantics, and recovery semantics are not publicly structured in catalog metadata.
- **`run_current`** (Command: `orchestration run-current`): Result schema, timeout semantics, and recovery semantics are not publicly structured in catalog metadata.
- **`run_list`** (Command: `orchestration run-list`): Result schema, timeout semantics, and recovery semantics are not publicly structured in catalog metadata.
- **`run_show`** (Command: `orchestration run-show`): Result schema, timeout semantics, and recovery semantics are not publicly structured in catalog metadata.
- **`run_use`** (Command: `orchestration run-use`): Result schema, timeout semantics, and recovery semantics are not publicly structured in catalog metadata.
- **`runtime_status_read`** (Command: `status`): Result schema, timeout semantics, and recovery semantics are not publicly structured in catalog metadata.
- **`task_create`** (Command: `orchestration task-create`): Result schema, timeout semantics, and recovery semantics are not publicly structured in catalog metadata.
- **`task_list`** (Command: `orchestration task-list`): Result schema, timeout semantics, and recovery semantics are not publicly structured in catalog metadata.
- **`task_retry_lineage`** (Command: `orchestration worker-start`): Result schema, timeout semantics, and recovery semantics are not publicly structured in catalog metadata.
- **`task_update`** (Command: `orchestration task-update`): Result schema, timeout semantics, and recovery semantics are not publicly structured in catalog metadata.
- **`terminal_close`** (Command: `terminal close`): Result schema, timeout semantics, and recovery semantics are not publicly structured in catalog metadata.
- **`terminal_create`** (Command: `terminal create`): Result schema, timeout semantics, and recovery semantics are not publicly structured in catalog metadata.
- **`terminal_list`** (Command: `terminal list`): Result schema, timeout semantics, and recovery semantics are not publicly structured in catalog metadata.
- **`terminal_read`** (Command: `terminal read`): Result schema, timeout semantics, and recovery semantics are not publicly structured in catalog metadata.
- **`terminal_send`** (Command: `terminal send`): Result schema, timeout semantics, and recovery semantics are not publicly structured in catalog metadata.
- **`terminal_show`** (Command: `terminal show`): Result schema, timeout semantics, and recovery semantics are not publicly structured in catalog metadata.
- **`terminal_stop`** (Command: `terminal stop`): Result schema, timeout semantics, and recovery semantics are not publicly structured in catalog metadata.
- **`terminal_wait`** (Command: `terminal wait`): Result schema, timeout semantics, and recovery semantics are not publicly structured in catalog metadata.
- **`worker_abandon`** (Command: `orchestration worker-abandon`): Result schema, timeout semantics, and recovery semantics are not publicly structured in catalog metadata.
- **`worker_env_add`** (Command: `environment add`): Result schema, timeout semantics, and recovery semantics are not publicly structured in catalog metadata.
- **`worker_env_show`** (Command: `environment show`): Result schema, timeout semantics, and recovery semantics are not publicly structured in catalog metadata.
- **`worker_read`** (Command: `orchestration worker-read`): Result schema, timeout semantics, and recovery semantics are not publicly structured in catalog metadata.
- **`worker_show`** (Command: `orchestration worker-show`): Result schema, timeout semantics, and recovery semantics are not publicly structured in catalog metadata.
- **`worker_start`** (Command: `orchestration worker-start`): Result schema, timeout semantics, and recovery semantics are not publicly structured in catalog metadata.
- **`worker_stop`** (Command: `orchestration worker-stop`): Result schema, timeout semantics, and recovery semantics are not publicly structured in catalog metadata.
- **`worktree_create`** (Command: `worktree create`): Result schema, timeout semantics, and recovery semantics are not publicly structured in catalog metadata.
- **`worktree_current`** (Command: `worktree current`): Result schema, timeout semantics, and recovery semantics are not publicly structured in catalog metadata.
- **`worktree_list`** (Command: `worktree list`): Result schema, timeout semantics, and recovery semantics are not publicly structured in catalog metadata.
- **`worktree_ps`** (Command: `worktree ps`): Result schema, timeout semantics, and recovery semantics are not publicly structured in catalog metadata.
- **`worktree_remove`** (Command: `worktree rm`): Result schema, timeout semantics, and recovery semantics are not publicly structured in catalog metadata.
- **`worktree_set`** (Command: `worktree set`): Result schema, timeout semantics, and recovery semantics are not publicly structured in catalog metadata.
- **`worktree_show`** (Command: `worktree show`): Result schema, timeout semantics, and recovery semantics are not publicly structured in catalog metadata.

## 5. Architectural Assessment & Recommendations

### 5.1 Seam Qualification Verdict
Does every required M2–M5 operation have a public structured seam in Orca?

**NO.** Out of 55 required capabilities across 12 domains:
- 0 capabilities satisfy the strict `SUPPORTED` standard (because output schemas, timeout contracts, and recovery semantics are absent from catalog JSON metadata).
- 49 capabilities are `PARTIAL` (public command exists, but output schema / timeout / recovery contracts are not machine-readable in the catalog).
- 6 capabilities are `MISSING` (no public Orca command exists for Run cancellation, Run closure, Task cancellation, event stream observation, aggregate resource inventory, or aggregate resource cleanup).

### 5.2 Status of M1.1b and M1.3
- **M1.1b Status:** Remains OPEN as accepted debt. The reusable adversarial isolation qualifier is not fully closed.
- **M1.3 Status:** Remains BLOCKED. No Orca runtime execution, worker launch, or state creation was performed or authorized during M1.2.

### 5.3 Implementer Recommendation
**Recommendation:** `RETURN_TO_M0_DESIGN`

Because essential control operations (Run cancel/close, Task cancel, resource cleanup) have no public structured command, and output/timeout/recovery contracts are not publicly structured in catalog metadata, the provider seam is insufficient. Aether cannot build a robust, deterministic provider adapter without returning to M0 design to address missing seams or revise expectations.
