# RC6-OBS — Passive observer startup, retained-history index, and native query parity

**Unit**: RC6-OBS (`t_f6d83945`), Implementer
**Authority**: Objective Contract `oc_b5926701207812e8@v1` (digest
`e7164c83862b747c7868706799c08ea63151ca388aa2dc2b1b89a40be33b01fc`), base
`d2874c2f3fc839a82fbaa96ece6edebab3856298`, and
`specs/001-aether-v1-productization/plan-rc6.md` §O1/§O2.
**Scope**: O1, O2, D1; acceptance AC-4 and AC-5. The contract was not edited.
**Compatibility conclusion**: unit-level `patch`; no aggregate release or publication conclusion.

## 1. Implemented behavior

1. Registration and synchronous native hooks remain passive. Retained journal validation,
   native reads, and maintenance-lock work run through the plugin-owned reconciliation
   worker rather than `_Observer` construction, collector creation, or hot callbacks.
2. `RetainedIndex` validates one retained snapshot and reuses unchanged segment state.
   Its snapshot state is `validated`, `incomplete`, or `unavailable`; invalid, replaced,
   truncated, quarantined, and unverified archive inputs cannot become verified bindings.
   Segment enumeration failures increment `RETAINED_INDEX_UNAVAILABLE` and do not look like
   an empty successful snapshot.
3. Native binding claims no longer treat an unknown or stale index as proof of absence.
   A hook claim is kept as a bounded pending intent until a complete snapshot corroborates
   it or proves the task absent. Contradictory retained rows remain unresolved. Pending
   intents survive unrelated snapshot refreshes and are flushed only through the worker
   after validation; the hook never waits for that work.
4. The previously implemented native/CLI query parity and fixed transient codes remain
   intact: native `AETHER-OBSERVE-BUSY` / `AETHER-OBSERVE-CATCHUP-INCOMPLETE` and CLI
   `STATE_BUSY` / `CATCHUP_INCOMPLETE`, with genuine unreadable state still fail-closed.

## 2. Requirement → check → observed result → evidence

| Requirement / oracle | Check actually run | Observed result | Evidence path / attribution |
|---|---|---|---|
| AC-4(a): registration and hot hooks do not wait for a paused retained reader | `uv run --frozen python scripts/run_tests.py -- -q tests/test_observation_passive_startup.py` | **5 passed**. Candidate registration and hot-hook path complete while the worker-side reader is held; the base-compatible harness fails intentionally when the base synchronous path reaches the patched `hermes_plugin.list_segments` barrier. | `tests/test_observation_passive_startup.py`; direct candidate run. Base RED run on disposable `d2874c2f` worktree: **1 failed** with the expected synchronous-history-wait assertion. |
| AC-4(b): one validated index per unchanged snapshot | Same passive-startup command; instrumentation asserts `validation_count` remains one across repeated lookups and increments once after an append | **PASS**. Counters demonstrate reuse rather than prose-only attribution. | `tests/test_observation_passive_startup.py::test_unchanged_retained_snapshot_validated_once_via_instrumentation`; direct. |
| AC-4(c): append, replacement, truncation, conflict, quarantine, and full/incremental equivalence | Same passive-startup command | **PASS**. Five tests pass, including production-boundary regressions for a cold/stale conflicting claim, a pending claim during an unrelated segment refresh, and retained-store enumeration failure. | `tests/test_observation_passive_startup.py`; direct. |
| AC-4(d): unchanged callback/reduction budgets | `uv run --frozen python scripts/run_tests.py -- -q tests/test_observation_performance.py` (included in focused run) | **PASS** in the focused suite; existing p95 ≤ 5 ms, p99 ≤ 20 ms callback and reduction gates remain unchanged. | `tests/test_observation_performance.py`; direct. The previously independently measured candidate corpus recorded hook p95 0.8 µs / p99 2.8 µs. |
| AC-5(e): native/CLI busy and incomplete parity with later recovery | `uv run --frozen python scripts/run_tests.py -- -q tests/test_observation_query_parity.py tests/test_observation_cli_plugin.py tests/test_observation_brief_tool.py` (included in focused run) | **PASS**. Fixed native and CLI transient codes are returned under controlled contention; settled state succeeds with equivalent summaries. | `tests/test_observation_query_parity.py`; direct. |
| AC-5(f): genuine corruption/privacy failures remain errors without leaks | Same parity/CLI/brief command | **PASS**. Fixed unreadable errors remain errors; no raw exception, path, payload, or lock-owner detail is exposed. | `tests/test_observation_query_parity.py`; direct. |
| Focused observation lane | `uv run --frozen python scripts/run_tests.py -- -q tests/test_observation_performance.py tests/test_observation_brief_tool.py tests/test_observation_batch_replay_regression.py tests/test_observation_journal_storage.py tests/test_observation_ingest_scale.py tests/test_observation_cli_plugin.py tests/test_observation_passive_startup.py tests/test_observation_query_parity.py` | **254 passed**. | Canonical exact-Hermes runner; direct. |
| Full observation regression lane | `uv run --frozen python scripts/run_tests.py -- -q tests/test_observation_*.py` | **679 passed, 1 skipped**. | Canonical exact-Hermes runner; direct. The skip is an existing qualification/environment boundary, not a suppressed failure. |
| Qualification lock and exact source harness | `uv run --frozen python scripts/qualify_observation.py checkout --path <isolated exact Hermes checkout> --json` followed by `uv run --frozen python scripts/qualify_observation.py test --checkout <isolated exact Hermes checkout> --json` | **472 passed**, `collected=472`; node manifest SHA-256 `c1b1215945754612bb768e513fbeefb4974ce6bba7b44fec39ab9a43ccc0ae0a`; plugin callback count **22**; raw payload absent. | `scripts/qualify_observation.py`; direct. Exact Hermes source identity was the locked `v2026.8.18` / commit `e624e9fde561e1add9388384012b295fde669ade`; private checkout receipts are not copied here. |
| Qualification mirror | `uv run --frozen python scripts/run_tests.py -- -q tests/test_observation_qualification.py` | **60 passed, 1 skipped**. | Canonical exact-Hermes runner; direct. |
| Static quality | `uv run --frozen ruff check src/aether_agents tests scripts && uv run --frozen ruff format --check src/aether_agents tests scripts && uv run --frozen mypy src/aether_agents` | **PASS**: Ruff clean, format clean for 178 files, mypy clean for 69 source files. | Direct. |
| Public-artifact path privacy | `uv run --frozen python scripts/check_public_artifacts.py` | **PASS** after replacing operator-local checkout paths with generic lane references. | `scripts/check_public_artifacts.py`; direct. |

The companion public-artifact manifest comparison is still a pre-existing integrated
surface mismatch at the supplied base and is owned by the documentation/integration
units; this unit did not edit `.github/workflows/policy.yml`.

## 3. Measured retained corpus and startup attribution

The objective-scale reproduction used the isolated retained corpus previously measured by
Supervisor review: **244 journal files, 76 summaries, 7 registered projects, and 22 native
callbacks**. The accepted candidate measurement recorded:

- passive registration: **0.0222 s**;
- initial background index build for one 35-segment project corpus: **0.0863 s**;
- unchanged snapshot check: **0.00145 s** mean-scale observation, with independent review
  measuring 1.47 ms mean / 1.76 ms maximum over repeated checks;
- prior behavior on the accumulated corpus: **7m36s** before agent-ready due to repeated
  retained-history validation.

These are retained-corpus and registration measurements, not a universal total-TUI SLO and
not a rendered-shell readiness claim. The startup regression is direct in this unit. The
objective-scale timings above are reused, independently reviewed measurements from the
same executable candidate behavior; no live installation or owner process was touched by
this correction. The new pending-binding regressions add no synchronous history work.

## 4. RED discipline and semantic-risk correction

The original passive-startup test could not collect at base because the retained-index
module did not exist there. The test harness now conditionally imports that RC6-only module
and, on the base revision, patches the history seam present in both revisions:
`hermes_plugin.list_segments`. The base run reached that seam during registration and was
held by the barrier; the test failed with the expected synchronous-history assertion.
The candidate run passed the same module's four tests. This is an executable RED/PASS pair,
not a claim inferred only from the prior live observation.

The prior review reproduced two binding-window failures: a new hook claim could be emitted
while retained history still contained a contradictory binding, and a local in-memory
claim could disappear when another segment triggered re-aggregation. The correction keeps
such claims pending, never returns them as verified, preserves them across unrelated
refreshes, and either corroborates the exact retained row or leaves coverage unresolved.
The production-boundary tests exercise both paths and verify that contradictory retained
history is not overwritten and that an unrelated segment does not drop the pending intent.

## 5. Direct versus reused attribution

**Direct in this correction**:

- `src/aether_agents/observation/capture/retained_index.py`: snapshot-state/error health,
  verified-only getters, pending binding intents, conflict preservation, and complete-snapshot
  flush eligibility;
- `src/aether_agents/observation/capture/hermes_plugin.py`: hook binding now distinguishes
  verified, pending, conflicting, absent, and incomplete state; worker flushes pending
  intents after retained validation; obsolete full-history helper readers were removed;
- `tests/test_observation_passive_startup.py`: base-compatible RED harness and binding-window
  regressions;
- `tests/test_observation_cli_plugin.py`: existing hook fixtures now seed a validated empty
  snapshot explicitly where they assert immediate durable binding behavior;
- `specs/001-aether-v1-productization/evidence/RC6-OBS.md`: corrected portable evidence,
  verification lane, RED receipt, and residual-risk statement.

**Reused and independently rechecked**: the previously reviewed native/CLI typed error
mapping, passive worker lifecycle, index segment parser, privacy/quarantine rules, callback
and reduction gates, qualification constants, and the 22-callback exact-Hermes harness.
No observation core test was added, removed, or renamed; the locked 472-node manifest and
its mirror remain unchanged.

## 6. Tracked manifest lines for integration

No new tracked non-`specs/` paths were added by this review correction. The unit's existing
new paths relative to base, which must remain literal in the integration manifest, are:

```text
src/aether_agents/observation/capture/retained_index.py
tests/test_observation_passive_startup.py
tests/test_observation_query_parity.py
```

Modified paths remain within the assigned writable surface:

```text
src/aether_agents/commands/observe.py
src/aether_agents/observation/brief.py
src/aether_agents/observation/capture/collector.py
src/aether_agents/observation/capture/hermes_plugin.py
src/aether_agents/observation/query.py
tests/test_observation_cli_plugin.py
tests/test_observation_passive_startup.py
```

Preserved owner boundaries include `src/aether_agents/lifecycle.py`, `src/aether_agents/cli.py`,
`src/aether_agents/launcher.py`, `scripts/aether_tui.py`, `docs/**`, `VERSION`,
`.github/workflows/policy.yml`, the normative specs, and
`tests/fixtures/observation/complete-summary.json`.

## 7. Residual risk and environment limits

- A pending native binding can remain unresolved if the worker is stopped before its next
  complete snapshot. It is intentionally not presented as a verified binding; the bounded
  consequence is incomplete coverage, not a false task attribution. Unload still joins the
  plugin-owned worker within its existing two-second bound.
- If retained segment enumeration or archive verification is unavailable, the index reports
  `unavailable`/`incomplete`, increments a content-free health counter, and returns no
  verified binding. A later worker cycle must reattempt validation; this is not reported as
  a successful empty state.
- The focused and full observation lanes use the canonical exact-Hermes runner because plain
  pytest without the locked Hermes checkout cannot import the native `hermes_cli` boundary.
  The exact checkout, HOME/XDG state, and temporary qualification destinations were isolated;
  no live profile, board, gateway, TUI, credentials, provider configuration, or external
  service was read for mutation or changed by this unit.
- This handoff does not claim live candidate-TUI readiness, integrated lifecycle/launcher
  compatibility, release qualification beyond the observation lane, publication, activation,
  or aggregate objective acceptance. Supervisor owns those conclusions and the next review.
