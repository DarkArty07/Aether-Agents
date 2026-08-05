# Experimental Coordination Maintenance Audit

> **Status:** HISTORICAL MAINTENANCE BASELINE; superseded in the v0.22.0 candidate
> **Date:** 2026-07-29
> **Baseline:** `origin/main` at `9c73144`
> **Scope:** v0.19.0 and v0.19.x coordination source, tests, scripts, configuration, and historical evidence
> **Current transition evidence:** `../releases/v0.22.0/OLYMPUS_RETIREMENT_INVENTORY.md`

## 1. Purpose

This audit records the coordination-maintenance baseline that preceded v0.22.0.
Its retained-code table is historical: the v0.22.0 R2 cut removed the Harmonia
public/runtime wrapper and bounded demo. R3a then moved Aether-owned identity,
contracts, budgets, evidence, effects, review and closure to a temporary native
package; R3b removed the generic Olympus kernel and its package facade. PDR-0012
subsequently retired that disconnected native package as well. None of these
historical classifications defines a current executable surface.

The maintenance goal is not to advance multi-agent coordination. It is to establish a smaller, truthful, testable baseline before new coordination work begins.

No runtime activation, key provisioning, gateway restart, database migration, deployment, tag, or release is part of this candidate.

## 2. Method

The classification used the following evidence:

1. traced imports from `olympus_v3.server` into the coordination package;
2. traced the `harmonia` MCP handler through `HarmoniaService`, `ProjectRuntimeRegistry`, `KernelRunService`, `KernelDispatcher`, and `OlympusRuntimeAdapter`;
3. searched every source and test consumer of the experimental modules and symbols;
4. compared the current tree with `v0.18.2`, `v0.20.0`, and `origin/main`;
5. ran the experiment-specific tests before retirement to distinguish dead code from broken code;
6. added executable removal contracts before deleting source;
7. reran the maintained coordination suite after each cut.

The retired experiments were internally tested. They were removed because they were not part of the authoritative runtime, not because their tests happened to fail.

## 3. Code retained by this historical baseline

| Area | Retained modules | Why it remains useful |
|---|---|---|
| Public Harmonia boundary | `harmonia_contract.py`, `harmonia_service.py`, `harmonia_store.py` | Parses the public `start/status/stop` contract, admits bounded runs, derives project-local storage, and projects public status. |
| Runtime composition | `harmonia_runtime.py` | Builds one project-scoped ledger/runtime/dispatcher/adapter composition and owns monitor cleanup. |
| Durable authority | `contracts.py`, `ledger.py`, `workflow.py`, `kernel_runtime.py`, `kernel_dispatcher.py` | Implements immutable execution authority, append-only state, task/attempt transitions, outbox delivery, fencing, reconciliation, and closure flow. |
| Bounded selection | `harmonia_selection.py`, `selection_commit.py` | Implements deterministic candidate projection, kernel revalidation, and CAS selection commit. |
| Evidence and safety | `evidence.py`, `budget.py`, `leases.py`, `projections.py`, `effects.py`, `review.py`, `closure.py` | Preserves trusted artifact handling, budgets, leases, deterministic projections, effect lifecycle, review types, and semantic closure validation used by the kernel. |
| Project identity | `principal.py` | Retains only the project-scoped `Principal` and shared `ValidationError` actually consumed by the kernel. |
| Lifecycle adapter | `olympus_adapter.py` | Retains only kernel-authorized dispatch, observation, cancellation, evidence, and persisted cleanup through public ACPManager methods. |
| Controlled E2E harness | `scripts/run_harmonia_bounded_demo.py` | Exercises the maintained bounded kernel composition in disposable fake mode and requires separate explicit confirmation for real ACP dispatch. |
| Package facade | `coordination/__init__.py` | Re-exports only maintained kernel foundations rather than every historical experiment. |

The v0.22.0 candidate subsequently removed the public Harmonia boundary,
runtime composition, bounded selection and demo rows above. R3a also moved the
evidence/safety and project-identity product logic out of Olympus without
legacy copies. R3b removed the durable kernel and lifecycle adapter after
proving zero active source or script consumers. Historical retention never
established production readiness.

## 4. Code retired

### 4.1 R8 parallel pilot runtime

Removed:

- `pilot.py`
- `pilot_compiler.py`
- `pilot_evidence.py`
- `pilot_model.py`
- `pilot_store.py`
- `scripts/run_r8_snake_pilot.py`
- `dispatch_pilot_task()` and `observe_pilot_task()`

Reason: R8 maintained a second mutable workflow authority through `PilotStore` and bypassed the selected kernel. The v0.19.0 closeout already classified it as legacy/blocked.

### 4.2 R7 shadow runtime

Removed:

- `shadow.py`
- `shadow_store.py`
- `scripts/run_r7_shadow_benchmark.py`
- the executable `mode: shadow` configuration path

Reason: R7 was observational evidence, not an active coordinator. The server never consumed `CoordinationConfig.mode`, and the tracked template still advertised an inert historical mode. `mode: shadow` now fails closed.

### 4.3 Pre-kernel logical coordinator

Removed:

- `admission.py`
- `harmonia.py`
- `presence.py`
- `OlympusRuntimeAdapter.dispatch()` and `OlympusRuntimeAdapter.observe()`
- `RuntimeReceipt`, `RuntimeObservation`, and `RuntimeStatus`

Reason: this path planned and dispatched `HarmoniaPlan` values outside the durable kernel composition. It had no current entrypoint after the kernel-backed Harmonia service became authoritative.

### 4.4 Cotal-inspired protocol and transport laboratory

Removed:

- `capabilities.py`
- `channels.py`
- `context.py`
- `identity.py`
- `protocol.py`
- `schema.py`
- `transport.py`
- `native_transport.py`

Reason: these modules formed an isolated identity, capability, envelope, channel, and transport model. No current server path constructed or consumed it. Keeping it in source and re-exporting it implied security and runtime guarantees that the active system did not provide.

The project-scoped `Principal` validation needed by contracts and dispatch was extracted without changing its accepted values or wire round-trip.

### 4.5 Phase 0 feasibility harnesses

Removed the five Python files under `tests/phase0/`.

Reason: they implemented independent tests-only versions of an authorization boundary, SQLite ledger, and effect hook boundary. They imported no Aether production coordination code and had already served their R1 feasibility purpose. The production kernel now has its own direct regression coverage.

### 4.6 Lease-heartbeat spike executable

Removed `spikes/001-harmonia-lease-heartbeat/main.py`.

Reason: the spike explicitly declared itself throwaway and required retirement once production regression coverage existed. Its `README.md`, `DECISION.md`, and `result.json` remain as historical evidence, while maintained lifecycle tests now cover the selected invariants directly.

## 5. Historical evidence policy

The retirement removes executable source from the current candidate, not history.

- v0.19.0 and v0.19.x reports, matrices, contracts, and closeouts remain under `docs/releases/`.
- Historical path references in those documents describe the tree at that milestone.
- The last released source tree containing the retired laboratories is available at tag `v0.20.0`; exact intermediate implementations remain in Git history.
- Historical stores are not migrated, opened, or mutated by this maintenance candidate.

Future code must not copy a retired prototype merely because a historical report records a passing test. A new capability must be justified against the current kernel authority model.

## 6. Measured reduction

| Measure | `origin/main` baseline | Maintained candidate | Change |
|---|---:|---:|---:|
| Coordination source files | 38 | 21 | -17 |
| Coordination source lines | 16,449 | 10,824 | -5,625 |
| Coordination test files | 57 | 35 | -22 |
| Coordination test lines | 15,200 | 10,373 | -4,827 |
| Package public exports | 176 | 83 | -93 |
| Coordination modules loaded by server import | 38 | 21 | -17 |
| Historical executable scripts | 2 | 0 | -2 |
| Standalone Phase 0 proof files | 5 | 0 | -5 |
| Standalone Phase 0 proof lines | 946 | 0 | -946 |
| Throwaway spike executables | 1 | 0 | -1 |
| Throwaway spike lines | 240 | 0 | -240 |

Pre-retirement evidence:

- 186 R8-focused tests passed before the R8 runtime was removed.
- 319 mixed pre-kernel/R7 and retained-boundary tests passed before the second cut, covering the whole affected equivalence class rather than only files selected for retirement.
- 43 Phase 0 feasibility tests passed before the tests-only harnesses were removed.

Post-retirement evidence:

- removal/config/principal contract: 19 passed;
- maintained coordination suite: 582 passed;
- canonical repository suite with the candidate `src/` explicitly isolated on `PYTHONPATH`: 823 passed;
- Ruff over `src/`: passed;
- `compileall`: passed;
- residual deleted-module import search: zero matches;
- `git diff --check`: passed;
- sdist and wheel build: passed;
- isolated wheel import: passed with 83 maintained coordination exports.

## 7. Historical maintenance debt

This section describes debt at the historical maintenance baseline. Current
disposition and measurements are maintained in the v0.22.0 inventory.

### 7.1 Private cross-component access

Current code crosses internal boundaries through:

- `context.ledger.conn`;
- `context.dispatcher._envelope()`;
- `context.dispatcher._append()`;
- `context.dispatcher._writer`;
- `dispatcher._after_close`.

These accesses make authority ownership hard to reason about. The next maintenance slice should add narrow public kernel/ledger operations and remove these private couplings before adding coordination behavior.

### 7.2 Oversized modules

The largest retained modules remain:

- `ledger.py`: 2,253 lines;
- `kernel_dispatcher.py`: 1,515 lines;
- `kernel_runtime.py`: 815 lines;
- `workflow.py`: 770 lines;
- `harmonia_runtime.py`: 543 lines;
- `harmonia_service.py`: 514 lines.

They should be decomposed by authority boundary, not by arbitrary file size. Behavior must remain unchanged while refactoring.

### 7.3 Configuration compatibility field

`CoordinationConfig.mode` now accepts only `legacy`. It is retained temporarily for compatibility, but the current Harmonia service uses `allowed_modes`, not `mode`. Removing the field requires an explicit configuration migration contract and is not bundled into this retirement.

### 7.4 Public API breadth

The package facade is reduced but still exports 83 foundation symbols. A later maintenance pass should identify which names are genuine external contracts and move internal implementation imports to direct modules.

### 7.5 Operational evidence

Harmonia remains default-off. This maintenance does not prove:

- active runtime readiness;
- arbitrary task graphs;
- participant-policy enforcement across all paths;
- recovery after committed successor selection;
- multi-project load behavior;
- an LLM planner;
- product improvement over a strong general agent.

## 8. Maintenance sequence before new coordination work

1. Replace private dispatcher/ledger access with narrow public authority methods.
2. Add deterministic characterization tests around those boundaries.
3. Decompose the ledger, dispatcher, runtime composition, and service without behavior changes.
4. Define and execute a configuration migration for the dead `mode` field.
5. Run the complete repository suite and independent candidate review.
6. Only then freeze the next bounded coordination hypothesis.

The next coordination increment must start from this maintained kernel baseline, not from the retired R2–R8 laboratory APIs.
