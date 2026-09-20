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

This record now covers two rounds: candidate `cba887bc` plus the rework commit that closes the
same-card review return on that candidate. Round-1 review verified the helper, the update-entry
clock, shared cancellation, post-call fences and the GX-06/D37 oracles, and returned three
defects: (1) the pre-publication deadline fences raised `TIMEOUT`/`failed` instead of the
established pending/partial receipt, (2) any Graphify `TIMEOUT` carrying the component message
was relabeled as operation-deadline exhaustion, and (3) the fingerprint preparation swallowed a
budget `TIMEOUT` and the update then rebuilt and published. All three are fixed in this commit;
the round-1 oracles that encoded (2) were rewritten as described below.

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

### Rework round (file references are this commit)

- `graphify.py:91-93` adds `_operation_budget_exhausted()`, which is true only once the
  operation's own remaining time is down to the finalization reserve.
- `graphify.py:106-112` attributes `operation_deadline_timeout` from that clock fact instead of
  the component's `TIMEOUT` message. A component timeout with time left on the operation budget
  now stays a typed `TIMEOUT`; the message text is no longer proof of budget exhaustion.
- `snapshots.py:1613-1626` replaces the two pre-publication `raise KnowledgeError("TIMEOUT", ...)`
  fences with `_deadline_result(existing_manifest, semantic_meta)`. Expiry before the manifest
  record or before the pointer record now produces the established pending/unchanged receipt,
  the `terminal_outcome=deadline` operation record, the released lock and no pointer, instead of
  a `failed`/`TIMEOUT` operation.
- `semantic.py:1199-1205` re-raises `OPERATION_CANCELLED` and `TIMEOUT` from the fingerprint
  preparation instead of reporting "no fingerprint"; other preparation failures still degrade to
  `None` as before.
- `snapshots.py:1236-1253` handles that raised fingerprint error in `update()`: a budget-attributed
  timeout returns the deadline receipt, a cancellation and an independent typed timeout propagate.
  A fenced or failed fingerprint can therefore no longer be reinterpreted as "needs rebuild" and
  published.
- Deliberate behavior change on that fingerprint path: the previous swallow-and-rebuild behavior
  predates this unit (base `00715d23`), but decision 10/AC-6 make the fingerprint preparation a
  budget-consuming Graphify call, so continuing to publish from its rejected result is the defect
  under repair rather than a preserved behavior.

## Acceptance coverage

| Obligation | Verification | Observed result |
| --- | --- | --- |
| Deadline begins at native update entry and is shared across Graphify calls | `tests/test_knowledge_regressions.py::test_operation_wide_deadline_starts_at_update_entry_and_bounds_graphify_invocations` | Passed; probe, structural update, semantic prepare/validate/compose receive positive decreasing timeouts and one event. |
| Semantic prepare/validate/compose propagation | `tests/test_knowledge_semantic_manager.py::test_prepare_validate_compose_receive_positive_timeout_and_shared_cancel` | Passed; every call receives the shared event and timeout within the reserved remaining budget. |
| Post-call deadline fence / no pointer | `test_post_call_fence_rejects_result_returned_after_deadline` | Passed; returns pending deadline receipt, records `terminal_outcome=deadline`, and publishes no pointer. |
| Post-call cancellation fence / no pointer | `test_post_call_fence_rejects_result_returned_after_host_cancel` | Passed; returns `OPERATION_CANCELLED`, leaves no pointer, and releases the lock. |
| Process-group cleanup | `test_host_cancel_terminates_process_group_releases_lock_and_leaves_no_pointer` plus existing Graphify process regression | Passed; parent and child process IDs exit, lock is reacquirable, and no pointer is published. |
| Natural semantic deadline and validated-cache retention | `test_deadline_zero_returns_honest_pending_receipt`, `test_operation_budget_compose_timeout_attributes_deadline_and_retains_cache`, and GX-06 regression | Passed; no compose after budget, cache remains, pending/deadline attribution is explicit. |
| Independent compose defect classification | Existing `test_compose_failure_is_category_apply_and_bounds_state` and `test_compose_timeout_while_budget_remains_is_a_bounded_apply_failure` | Passed; independent failures remain bounded `apply`/typed failures rather than deadline receipts. |
| Publication fence: expiry before the manifest or pointer record (AC-7) | `test_publication_fence_deadline_returns_deadline_receipt[manifest-build]`, `[manifest-record]` | Passed; pending deadline receipt with `terminal_outcome=deadline`, no pointer for the revised revision, the previously published revision untouched, lock reacquirable. RED before the fix: both nodes raised `TIMEOUT` at `snapshots.py:1607`/`1618` of candidate `cba887bc`. |
| Publication fence: retain the prior complete snapshot (AC-7) | `test_publication_fence_deadline_retains_the_previous_snapshot` | Passed; `unchanged` receipt carrying the retained `snapshot_id`, unchanged pointer bytes, `terminal_outcome=deadline`, lock reacquirable. RED before the fix (raised `TIMEOUT`). |
| Budget-only timeout attribution (AC-7) | `test_compose_timeout_while_budget_remains_is_a_bounded_apply_failure`, `test_operation_budget_compose_timeout_attributes_deadline_and_retains_cache` | Passed; a stock component `TIMEOUT` with minutes left on the operation clock is `apply`/typed and not deadline; the same error after the operation clock ran out is deadline-attributed. The first node is RED on `cba887bc` (message-based attribution). |
| Fingerprint preparation fence (AC-6/AC-7) | `test_fingerprint_prepare_timeout_never_rebuilds_or_publishes`, `test_fingerprint_prepare_budget_timeout_returns_deadline_receipt` | Passed; a component timeout raises typed `TIMEOUT` with zero structural rebuilds and unchanged pointer; a budget-attributed timeout returns the `unchanged` deadline receipt. RED before the fix: the first node did not raise (swallowed, then rebuilt and published). |
| Existing cancellation and snapshot invariants | `tests/test_knowledge_regressions.py` | Passed: 59 passed, 1 conditional live-auxiliary skip (round 1 measured 54 passed before the five new nodes). |

## Verification log

Commands executed on the candidate worktree (round 1):

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

Round-2 (rework) focused verification, fail-first then green:

```text
# RED on candidate cba887bc, before the source repair:
uv run python scripts/run_tests.py -- \
  tests/test_knowledge_semantic_manager.py::test_compose_timeout_while_budget_remains_is_a_bounded_apply_failure \
  tests/test_knowledge_semantic_manager.py::test_operation_budget_compose_timeout_attributes_deadline_and_retains_cache \
  "tests/test_knowledge_regressions.py::test_publication_fence_deadline_returns_deadline_receipt" \
  tests/test_knowledge_regressions.py::test_fingerprint_prepare_timeout_never_rebuilds_or_publishes \
  tests/test_knowledge_regressions.py::test_fingerprint_prepare_budget_timeout_returns_deadline_receipt -q --tb=line
4 failed, 2 passed
#   compose-attribution node: assert True is False (deadline_exhausted was True)
#   publication fence [manifest-build]: KnowledgeError TIMEOUT at src/.../snapshots.py:1607
#   publication fence [manifest-record]: KnowledgeError TIMEOUT at src/.../snapshots.py:1618
#   fingerprint component timeout: DID NOT RAISE (swallowed, rebuilt, published)

# GREEN after the source repair (same nodes, plus the retention node):
26 passed
#   including tests/test_knowledge_semantic_manager.py (21) and the five new regression nodes

uv run python scripts/run_tests.py -- tests/test_knowledge_regressions.py -q -rs
59 passed, 1 skipped in 98.83s
#   same single conditional skip: live auxiliary connection not provisioned

uv run python scripts/run_tests.py -- \
  tests/test_knowledge_regressions.py::test_gx06_deadline_seconds_zero_pending_honest_coverage \
  tests/test_knowledge_regressions.py::test_d37_failure_preservation_timeout_exhaustion_malformed \
  tests/test_knowledge_regressions.py::test_cancel_at_each_lifecycle_boundary_never_publishes_a_candidate \
  tests/test_knowledge_regressions.py::test_component_timeout_and_cancel_kill_the_whole_process_group \
  tests/test_knowledge_regressions.py::test_host_interrupt_during_composition_publishes_nothing -q
9 passed

uv run --frozen ruff check src/aether_agents tests scripts
All checks passed!

uv run --frozen ruff format --check src/aether_agents tests scripts
171 files already formatted

uv run --frozen mypy src/aether_agents
Success: no issues found in 67 source files

uv run --frozen python scripts/check_documentation.py
documentation validation passed

uv build
Successfully built dist/aether_agents-1.0.0rc3.tar.gz
Successfully built dist/aether_agents-1.0.0rc3-py3-none-any.whl

git diff --check
clean
```

The native component lane used the configured pinned Graphify 0.9.54 interpreter
(`~/.local/state/aether/knowledge/component.json`, read-only; no pytest installed into the managed
component). Both the round-1 and round-2 regression runs are deterministic stand-in oracles plus
the pre-existing native process oracles; no live model or auxiliary call was made.

The complete exact-Hermes suite was also run after the final knowledge changes:

```text
AETHER_GRAPHIFY_PYTHON=<configured pinned Graphify 0.9.54 interpreter> \
  uv run python scripts/run_tests.py -- -q --tb=line -rs
2 failed, 1863 passed, 10 skipped, 587 subtests passed in 395.41s
```

The two failures are outside this unit and reproduce as existing cross-unit gates (identified by
running the two modules directly):

1. `tests/test_aether_tui_launcher.py::MorfeoTuiLauncherTests::test_versioned_launcher_contains_no_machine_specific_home`
   observes the checkout's launcher mode as `775` (`509`) rather than the expected `755` (`493`);
   this unit did not modify `scripts/aether_tui.py` or launcher permissions.
2. `tests/test_public_artifacts.py::test_canonical_base_manifest_matches_tracked_non_specs_files`
   reports the pre-existing policy manifest drift for the objective-contract paths and website
   test inventory; policy registration is explicitly owned by LG-DOCS and was not changed here.

The ten exact-suite skips were reported by pytest and remain conditional/pre-existing: the
isolated native worker lane, live auxiliary connection, disposable component installation,
exact-Hermes session-affinity lane, 100k qualification lane, and unavailable product runtime
lanes. No skip was added by LG-KNOW.

The repository coverage-floor command was also run with the exact checkout identity and pinned
component environment (the exact-Hermes checkout on `PYTHONPATH`, as `scripts/run_tests.py`
supplies it, because the packaged environment alone cannot import `hermes_cli` for
`tests/test_same_card_phase_predicates.py`):

```text
uv run --frozen python -m coverage run -m pytest -q \
  --ignore=tests/test_observation_performance.py
2 failed, 1859 passed, 10 skipped, 587 subtests passed in 433.38s
uv run --frozen python -m coverage report --format=total
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
- Round-2 residual risk: the deadline attribution now depends on the operation clock rather than
  the component's `TIMEOUT` text. If a future Graphify version raises a different error code for a
  budget-caused stop, or if the component silently truncates a call instead of timing out, the
  attribution would need re-review against `graphify.py:91-112`. A component-level timeout that
  leaves the operation budget intact is intentionally a typed failure, not a deadline receipt.
- Full integrated acceptance remains blocked by the two unrelated launcher/policy gates above;
  LG-DOCS/LG-LIFE must resolve their owned gates before aggregate qualification.
- The local implementation is ready for same-card Supervisor review. No remote or live effect
  was performed.
