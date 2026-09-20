# LG-KNOW — Operation-wide Graphify deadline

**Unit:** LG-KNOW
**Objective Contract:** `oc_ff82ba151cdf3861@v2`
**Canonical breakdown:** `specs/001-aether-v1-productization/tasks-rc4.md`
**Base:** `00715d237d795e365c5e462b6b80d5a1bd8d8188`
**Compatibility impact:** `patch`
**Status:** unit-local implementation evidence; not independent review, integration, activation, or release evidence.

## Scope and preservation

Implemented the operation-wide Project Knowledge/Graphify deadline in the assigned knowledge
surfaces only. The change does not edit the Objective Contract, launcher/lifecycle files,
`graph_worker.py`, `policy.yml`, VERSION, documentation identity, credentials, provider/router
configuration, or live auxiliary state. No live model call, publication, push, PR, tag, issue
mutation, or activation was performed. No new tracked non-`specs/` path was created; LG-DOCS
therefore has no new unit path to register beyond the already tracked knowledge test files.

## Implementation

- `src/aether_agents/knowledge/graphify.py`
  - Added one bounded Graphify invocation helper that computes a positive timeout from the
    shared monotonic deadline, subtracts the finalization reserve, passes the same shared
    cancellation event, and fences the returned result against cancellation/deadline.
  - Preserved isolated worker process-group cleanup (`os.killpg` on POSIX) for timeout,
    cancellation, and host interruption.
  - Preserved the backend's configured component timeout as an additional upper bound.
  - Distinguishes a budget-caused Graphify `TIMEOUT` from an independent typed timeout so
    independent failures are not relabeled as deadline outcomes.

- `src/aether_agents/knowledge/semantic.py`
  - `run_semantic_extraction` accepts the caller-owned operation deadline and does not create
    a second operation-wide clock when invoked from `KnowledgeStore.update()`.
  - Semantic prepare paging, validate, and compose all use the bounded invocation helper with
    the same event and remaining timeout.
  - Pre/post-call fences stop late results. Budget-caused prepare/validate/compose timeouts
    produce pending/deferred deadline attribution and retain validated cache; independent
    compose defects remain `apply` failures.
  - Receipts identify operation-wide deadline exhaustion additively in the pipeline block.

- `src/aether_agents/knowledge/snapshots.py`
  - Starts the monotonic deadline at native `KnowledgeStore.update()` entry, with the existing
    300-second cap and lower explicit operation configuration/argument support.
  - Routes probe, structural update, fingerprint preparation, legacy validation, and semantic
    prepare/validate/compose through the shared deadline/event path.
  - Adds terminal pre-publication fences. A budget-caused timeout returns a valid pending/
    unchanged receipt with deadline attribution, leaves the prior valid snapshot intact when
    present, releases the lock, records terminal deadline state, and does not publish a pointer.
  - Host cancellation remains `OPERATION_CANCELLED`; independent timeout defects still raise
    through the existing lifecycle rather than being converted to deadline receipts.

## Acceptance coverage

| Obligation | Verification | Observed result |
| --- | --- | --- |
| Deadline begins at native update entry and is shared across Graphify calls | `tests/test_knowledge_regressions.py::test_operation_wide_deadline_starts_at_update_entry_and_bounds_graphify_invocations` | Passed; probe, structural update, semantic prepare/validate/compose receive positive decreasing timeouts and one event. |
| Semantic prepare/validate/compose propagation | `tests/test_knowledge_semantic_manager.py::test_prepare_validate_compose_receive_positive_timeout_and_shared_cancel` | Passed; every call receives the shared event and timeout within the reserved remaining budget. |
| Post-call deadline fence / no pointer | `test_post_call_fence_rejects_result_returned_after_deadline` | Passed; returns pending deadline receipt, records `terminal_outcome=deadline`, and publishes no pointer. |
| Post-call cancellation fence / no pointer | `test_post_call_fence_rejects_result_returned_after_host_cancel` | Passed; returns `OPERATION_CANCELLED`, leaves no pointer, and releases the lock. |
| Process-group cleanup | `test_host_cancel_terminates_process_group_releases_lock_and_leaves_no_pointer` plus existing Graphify process regression | Passed; parent and child process IDs exit, lock is reacquirable, and no pointer is published. |
| Natural semantic deadline and validated-cache retention | `test_deadline_zero_returns_honest_pending_receipt`, `test_compose_timeout_attributes_deadline_and_retains_cache`, and GX-06 regression | Passed; no compose after budget, cache remains, pending/deadline attribution is explicit. |
| Independent compose defect classification | Existing `test_compose_failure_is_category_apply_and_bounds_state` and synthetic structural timeout regression | Passed; independent failures remain bounded `apply`/typed failures rather than deadline receipts. |
| Existing cancellation and snapshot invariants | `tests/test_knowledge_regressions.py` | Passed: 54 passed, 1 conditional live-auxiliary skip. |

## Verification log

Commands executed on the candidate worktree:

```text
uv run python scripts/run_tests.py -- tests/test_knowledge_semantic_manager.py -q
20 passed in 2.36s

AETHER_GRAPHIFY_PYTHON=<configured pinned Graphify 0.9.54 interpreter> \
  uv run python scripts/run_tests.py -- tests/test_knowledge_regressions.py -q
54 passed, 1 skipped in 98.88s

uv run --frozen ruff check src/aether_agents tests scripts
All checks passed!

uv run --frozen ruff format --check src/aether_agents tests scripts
171 files already formatted

uv run --frozen mypy src/aether_agents
Success: no issues found in 67 source files

uv run --frozen python scripts/check_documentation.py
documentation validation passed

uv build
Successfully built the source distribution and wheel for the current package identity.

git diff --check
passed
```

The complete exact-Hermes suite was also run after the final knowledge changes:

```text
AETHER_GRAPHIFY_PYTHON=<configured pinned Graphify 0.9.54 interpreter> \
  uv run python scripts/run_tests.py -- -q --tb=short -rs
1857 passed, 10 skipped, 587 subtests passed, 2 failed
```

The two failures are outside this unit and reproduce as existing cross-unit gates:

1. `tests/test_aether_tui_launcher.py::MorfeoTuiLauncherTests::test_versioned_launcher_contains_no_machine_specific_home`
   observes the checkout's existing launcher mode as `775` rather than the expected `755`;
   this unit did not modify `scripts/aether_tui.py` or launcher permissions.
2. `tests/test_public_artifacts.py::test_canonical_base_manifest_matches_tracked_non_specs_files`
   reports the pre-existing policy manifest drift for the objective-contract paths and website
   test inventory; policy registration is explicitly owned by LG-DOCS and was not changed here.

The ten exact-suite skips were reported by pytest and remain conditional/pre-existing: the
isolated native worker lane, live auxiliary connection, disposable component installation,
exact-Hermes session-affinity lane, 100k qualification lane, and unavailable product runtime
lanes. No skip was added by LG-KNOW.

The repository coverage-floor command was also run with the exact checkout identity and pinned
component environment:

```text
coverage run -m pytest -q --ignore=tests/test_observation_performance.py
1853 passed, 10 skipped, 587 subtests passed, 2 failed
coverage report --format=total
75
Coverage failure: total of 75 is less than fail-under=78
```

The same two unrelated launcher-permission and policy-manifest failures account for the
non-zero test status; no coverage floor claim is made. The exact native process regression in
`tests/test_knowledge_regressions.py` was run with the configured pinned component and passed.

## Remaining risk and handoff

- Unit-level behavior is covered by deterministic fake-clock, slow-backend, timeout, cancel,
  cache, lock, process-group, and pointer-fence tests. No live semantic qualification was
  attempted, as required by the unit boundary.
- Full integrated acceptance remains blocked by the two unrelated launcher/policy gates above;
  LG-DOCS/LG-LIFE must resolve their owned gates before aggregate qualification.
- The local implementation is ready for same-card Supervisor review. No remote or live effect
  was performed.
