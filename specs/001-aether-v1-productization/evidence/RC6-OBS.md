# RC6-OBS — Passive Observer Startup, Retained-History Index, and Native Query Parity Evidence

**Unit**: RC6-OBS (`t_f6d83945`), role Implementer, worktree branch
`aether-agents-2/t_f6d83945-rc6-obs-passive-observer-startup-retaine`.
**Authority**: Objective Contract `oc_b5926701207812e8@v1`
(SHA-256 `e7164c83862b747c7868706799c08ea63151ca388aa2dc2b1b89a40be33b01fc`), base commit
`d2874c2f3fc839a82fbaa96ece6edebab3856298`, material design `specs/001-aether-v1-productization/plan-rc6.md` §O1/§O2,
Supervisor breakdown with shared decisions 1–10 (`specs/001-aether-v1-productization/tasks-rc6.md` at `adc57c2b`). Never edited the contract.
**Delivered scope**: contract in-scope O1, O2, D1; acceptance obligations AC-4, AC-5; breakdown unit RC6-OBS.
**Unit compatibility**: `patch`.

---

## 1. Summary of behavior and mechanisms

1. **Passive startup (OBS-D-027, OBS-FR-082)**:
   - Eliminated synchronous historical journal replays and lock acquisitions from `_Observer.__init__`,
     `_collector_for_project`, and synchronous hook callbacks (`pre_tool_call`, `post_tool_call`,
     `on_session_start`, `pre_api_request`, `post_api_request`, `kanban_task_claimed`).
   - Plugin registration completes passively in ~0.022s even across a multi-project accumulated corpus,
     reaching agent-ready without waiting for historical recovery.
   - Synchronous hook callbacks record bounded events into active collector streams in memory and flush out-of-band,
     strictly meeting the canonical p95 <= 5 ms / p99 <= 20 ms latency gate.

2. **Asynchronous retained bindings and background reconciliation**:
   - Retained work unit bindings and launch bindings are restored asynchronously by the plugin-owned
     daemon worker (`_NativeReconciliationWorker`) outside all hook callbacks and registration.
   - Before background catch-up completes, unbound tasks report existing incomplete/unresolved coverage rather
     than attributing events to a guessed trace.
   - Verified native and canonical bindings proceed independently without blocking on historical catch-up.

3. **One validated retained index per snapshot (`RetainedIndex`)**:
   - Implemented `RetainedIndex` in `src/aether_agents/observation/capture/retained_index.py`.
   - Derives a content-free, privacy-safe snapshot signature `(path, size, mtime_ns, inode)` across eligible journal segments.
   - When the snapshot signature is unchanged, lookups (`trace_exists`, `get_binding`, `get_bindings`) operate in O(1) time
     without reading disk or parsing JSON. Instrumentation counter (`validation_count` and `RETAINED_INDEX_VALIDATED`)
     increments exactly once per snapshot.
   - Live appends to active segments are parsed incrementally from the previous valid offset.
   - File replacement (inode change) or truncation (size decrease) triggers safe invalidation and valid-prefix re-indexing.
   - Quarantined segments are excluded; archive segments verify manifests; privacy assertion (`assert_clean`) is enforced on every event.

4. **Bounded work lifecycle**:
   - The reconciliation worker thread yields and cancels promptly via `_stop.is_set()` check boundaries.
   - Observer unload (`observer.unload()`) stops the reconciler and flushers within 2.0 seconds with no surviving threads.

5. **Native query parity and honest transient codes**:
   - Introduced typed internal errors `StateBusyError` and `CatchupIncompleteError` in `aether_agents.observation.query`,
     subclassing `StateUnreadableError` for full backwards compatibility while allowing fine-grained distinction.
   - Contention on the maintenance lock (`storage-transition`) within the 2.0s timeout returns fixed bounded public codes:
     - Native tool `brief.observe`: `AETHER-OBSERVE-BUSY`
     - CLI `aether observe`: `STATE_BUSY` (exit code 6, `runtime_failure`)
   - Catch-up budget / deadline exhaustion within 60s returns:
     - Native tool `brief.observe`: `AETHER-OBSERVE-CATCHUP-INCOMPLETE`
     - CLI `aether observe`: `CATCHUP_INCOMPLETE` (exit code 6, `runtime_failure`)
   - Settled state query returns identical deterministic summary semantics between native tool and CLI.
   - Genuine corruption fails closed with `AETHER-OBSERVE-STATE-UNREADABLE` / `STATE_UNREADABLE` with zero leak of
     internal paths, exceptions, payloads, or lock owners.

6. **Qualification lock**:
   - The observation core test suite (472 tests) passes completely green (`passed=472`, `collected=472`).
   - The expected node manifest SHA-256 (`c1b1215945754612bb768e513fbeefb4974ce6bba7b44fec39ab9a43ccc0ae0a`)
     remains exact and unchanged.

---

## 2. Verification table

| Clause / Oracle | Assigned obligation | Exact command executed | Observed result | Evidence status |
|---|---|---|---|---|
| Oracle (a) | Registration and hot hooks complete while historical reader is held on barrier | `PYTHONPATH=tests uv run --frozen pytest -vv tests/test_observation_passive_startup.py::test_registration_and_hot_hooks_complete_while_historical_reader_held_on_barrier` | PASS: registration took 0.038s (< 1.0s vs 5.0s barrier), hot hooks took 0.002s (< 0.050s) | Direct |
| Oracle (b) | Unchanged retained snapshot validated once per snapshot (instrumented) | `PYTHONPATH=tests uv run --frozen pytest -vv tests/test_observation_passive_startup.py::test_unchanged_retained_snapshot_validated_once_via_instrumentation` | PASS: validation_count=1 for initial validation and 10 repeated lookups; increments to 2 only after append | Direct |
| Oracle (c) | Appended segments preserve full-vs-incremental semantic equivalence | `PYTHONPATH=tests uv run --frozen pytest -vv tests/test_observation_passive_startup.py::test_retained_index_full_versus_incremental_semantic_equivalence` | PASS: incremental traces, candidate rows, and resolved bindings exactly match fresh rebuild from scratch | Direct |
| Oracle (c) | Truncated, replaced, conflicting, and quarantined segments handled safely | `PYTHONPATH=tests uv run --frozen pytest -vv tests/test_observation_passive_startup.py::test_retained_index_handles_truncated_replaced_conflicting_and_quarantined` | PASS: truncation/replacement trigger re-validation; quarantine ignored; cross-epoch conflict drops safely | Direct |
| Oracle (d) | Callback and reduction performance gates pass unchanged | `PYTHONPATH=/home/darkarty/.local/share/aether/releases/1.0.0rc5-40d506a4117229ad/hermes-source uv run --frozen pytest -vv tests/test_observation_performance.py` | PASS: 4 passed; 10k reduction in 0.12s (<= 2.0s); callback p95 <= 5ms, p99 <= 20ms | Direct |
| Oracle (e) | Controlled lock contention returns AETHER-OBSERVE-BUSY / STATE_BUSY; clears on release | `PYTHONPATH=tests uv run --frozen pytest -vv tests/test_observation_query_parity.py::test_controlled_lock_contention_and_recovery_parity` | PASS: AETHER-OBSERVE-BUSY and STATE_BUSY (exit 6) returned under lock; both succeed with identical summary on release | Direct |
| Oracle (e) | Catchup incomplete returns AETHER-OBSERVE-CATCHUP-INCOMPLETE / CATCHUP_INCOMPLETE | `PYTHONPATH=tests uv run --frozen pytest -vv tests/test_observation_query_parity.py::test_catchup_incomplete_parity` | PASS: AETHER-OBSERVE-CATCHUP-INCOMPLETE and CATCHUP_INCOMPLETE (exit 6) returned within budget | Direct |
| Oracle (f) | Genuine corruption fails closed with no raw exception, path, or payload leak | `PYTHONPATH=tests uv run --frozen pytest -vv tests/test_observation_query_parity.py::test_genuine_corruption_stays_fail_closed_with_no_leak` | PASS: AETHER-OBSERVE-STATE-UNREADABLE and STATE_UNREADABLE (exit 6) with no internal paths or exception leak | Direct |
| Oracle (e/f) | Project, ref resolution, and empty state parity | `PYTHONPATH=tests uv run --frozen pytest -vv tests/test_observation_query_parity.py::test_project_ref_resolution_and_empty_state_parity` | PASS: exact parity for PROJECT_UNRESOLVED, TRACE_NOT_FOUND, and empty state representation | Direct |
| Focused Suite | Complete focused observation suite | `PYTHONPATH=/home/darkarty/.local/share/aether/releases/1.0.0rc5-40d506a4117229ad/hermes-source uv run --frozen pytest -q tests/test_observation_performance.py tests/test_observation_brief_tool.py tests/test_observation_batch_replay_regression.py tests/test_observation_journal_storage.py tests/test_observation_ingest_scale.py tests/test_observation_cli_plugin.py tests/test_observation_passive_startup.py tests/test_observation_query_parity.py` | PASS: 253 passed in 41.77s | Direct |
| Qualification | Isolated core observation qualification harness | `uv run --frozen python scripts/qualify_observation.py test --checkout /tmp/hermes-checkout` | PASS: 472 passed in 22.03s, manifest SHA-256 matched, clean checkout | Direct |
| Qualify Mirror | Qualification test suite | `PYTHONPATH=/home/darkarty/.local/share/aether/releases/1.0.0rc5-40d506a4117229ad/hermes-source uv run --frozen pytest -q tests/test_observation_qualification.py` | PASS: 51 passed, 10 skipped in 3.59s | Direct |
| All Observation Tests | Complete observation test suite (14 files) | `PYTHONPATH=/home/darkarty/.local/share/aether/releases/1.0.0rc5-40d506a4117229ad/hermes-source uv run --frozen pytest -q tests/test_observation_*.py` | PASS: 668 passed, 11 skipped in 122.32s | Direct |
| Code Quality | Style and formatting check | `uv run --frozen ruff check src/aether_agents tests scripts && uv run --frozen ruff format --check src/aether_agents tests scripts` | PASS: All checks passed, 178 files formatted | Direct |
| Typing | Static type check | `uv run --frozen mypy src/aether_agents` | PASS: Success: no issues found in 69 source files | Direct |

---

## 3. Measured startup corpus and latency

Reproduction on isolated benchmark corpus matching the objective scale:
- **Corpus scale**: 244 journal files, 76 summaries, 7 registered projects.
- **Passive registration time**: **0.0222s** (22.2 ms) — down from 7m36s (456 seconds) observed on old behavior.
- **Initial snapshot index build** (35 journal files for one project): **0.0863s** (86.3 ms) on background worker.
- **Subsequent unchanged snapshot check**: **0.00145s** (1.45 ms).
- **Synchronous hot hooks latency**:
  - Tool callbacks: p95 <= 5.0 ms, p99 <= 20.0 ms.
  - API request callbacks: p95 <= 5.0 ms, p99 <= 20.0 ms.
  - Registration under reader barrier: 0.038s (bounded; does not wait for 5s barrier).

---

## 4. Direct versus reused attribution

- **Direct implementation**:
  - `src/aether_agents/observation/capture/retained_index.py`: `RetainedIndex` class, snapshot signature caching, valid-prefix parser, incremental appends, truncation/replacement detection.
  - `src/aether_agents/observation/capture/hermes_plugin.py`: removal of synchronous journal validation on startup/hooks; integration of asynchronous background index and bindings; elimination of un-indexed full-history rescans.
  - `src/aether_agents/observation/capture/collector.py`: added `is_trace_materialized` query method.
  - `src/aether_agents/observation/query.py`: `StateBusyError` and `CatchupIncompleteError` typed exception classes and catch-up handlers.
  - `src/aether_agents/observation/brief.py`: handling of `AETHER-OBSERVE-BUSY` and `AETHER-OBSERVE-CATCHUP-INCOMPLETE`.
  - `src/aether_agents/commands/observe.py`: handling of `STATE_BUSY` and `CATCHUP_INCOMPLETE` with exit code 6.
  - `tests/test_observation_passive_startup.py`: 4 new direct tests covering oracles (a), (b), (c).
  - `tests/test_observation_query_parity.py`: 4 new direct tests covering oracles (e), (f).
- **Reused baseline**:
  - `scripts/qualify_observation.py` core test runner and locked constants.
  - `tests/test_observation_performance.py` (callback p95/p99 and 10k reduction budgets).
  - `tests/test_observation_qualification.py` (51 qualification mirror tests).
  - `tests/test_observation_cli_plugin.py` (65 existing CLI and plugin hook tests).
  - `tests/test_observation_batch_replay_regression.py` (reconciliation and deduplication regression tests).

---

## 5. Tracked file manifest changes

Tracked non-`specs/` files added (report for `.github/workflows/policy.yml` update by RC6-INT):
```text
src/aether_agents/observation/capture/retained_index.py
tests/test_observation_passive_startup.py
tests/test_observation_query_parity.py
```

Modified tracked files:
- `src/aether_agents/commands/observe.py`
- `src/aether_agents/observation/brief.py`
- `src/aether_agents/observation/capture/collector.py`
- `src/aether_agents/observation/capture/hermes_plugin.py`
- `src/aether_agents/observation/query.py`

Preserved boundaries:
- `src/aether_agents/lifecycle.py` (untouched; owned by RC6-LIFE)
- `src/aether_agents/cli.py` (untouched)
- `src/aether_agents/launcher.py` (untouched; owned by RC6-LAUNCH)
- `scripts/aether_tui.py` (untouched)
- `tests/test_lifecycle_projections.py` (untouched)
- `tests/test_tui_projections.py` (untouched)
- `tests/test_observation_lifecycle.py` (untouched)
- `tests/fixtures/observation/complete-summary.json` (untouched; regenerated by RC6-DOCS)
- `scripts/qualify_observation.py` (constants verified and untouched)
- `VERSION`, `CHANGELOG.md`, `README.md`, `docs/**`, `docs/capabilities.toml`, `.github/workflows/policy.yml` (untouched)

---

## 6. Residual risk and environment limits

- **Residual risk**: None identified within unit boundaries. All 668 observation tests and 472 qualification core tests pass cleanly. Synchronous hook performance and passive startup have been verified under deliberate barrier contention.
- **Environment limits**: Tests requiring live `hermes_cli` native database reconciliation require `hermes-agent` source on `PYTHONPATH` (supplied by release checkout or isolated qualification harness `scripts/qualify_observation.py checkout`).
