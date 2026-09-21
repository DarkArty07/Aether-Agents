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
3. Native binding claims no longer treat an unknown or moved index as proof of absence.
   A hook claim is kept as a bounded pending intent until a complete snapshot corroborates
   it or proves the task absent. Contradictory retained rows remain unresolved. Pending
   intents survive unrelated snapshot refreshes and are flushed only through the worker
   after validation; the hook never waits for that work.
4. A durable claim is published only while the validated snapshot still covers the live
   retained evidence. `RetainedIndex.snapshot_covers_disk` is a stat-only comparison of the
   live segment set against the validated snapshot signature; hooks call it without reading
   journal content and without taking the maintenance lock. If any segment owned by another
   producer appeared, grew, was replaced, was truncated, or disappeared after validation,
   the absence verdict is no longer proof, a content-free `BINDING_STALE_SNAPSHOT` counter is
   incremented, and the intent stays pending for the worker's validated emission path. The
   process's own producer epoch is exempt, because its own appends and rotations are tracked
   here as pending intents and cannot contradict its own validated evidence.
5. The previously implemented native/CLI query parity and fixed transient codes remain
   intact: native `AETHER-OBSERVE-BUSY` / `AETHER-OBSERVE-CATCHUP-INCOMPLETE` and CLI
   `STATE_BUSY` / `CATCHUP_INCOMPLETE`, with genuine unreadable state still fail-closed.

## 2. Requirement → check → observed result → evidence

| Requirement / oracle | Check actually run | Observed result | Evidence path / attribution |
|---|---|---|---|
| AC-4(a): registration and hot hooks do not wait for a paused retained reader | `uv run --frozen python scripts/run_tests.py -- -q tests/test_observation_passive_startup.py` | **7 passed**. Candidate registration and hot-hook path complete while the worker-side reader is held; the base-compatible harness fails intentionally when the base synchronous path reaches the patched `hermes_plugin.list_segments` barrier. | `tests/test_observation_passive_startup.py`; direct candidate run. Base RED run on a disposable `d2874c2f` worktree: **1 failed** with the expected synchronous-history-wait assertion. |
| AC-4(b): one validated index per unchanged snapshot | Same passive-startup command; instrumentation asserts `validation_count` remains one across repeated lookups and increments once after an append | **PASS**. Counters demonstrate reuse rather than prose-only attribution. | `tests/test_observation_passive_startup.py::test_unchanged_retained_snapshot_validated_once_via_instrumentation`; direct. |
| AC-4(c): append, replacement, truncation, conflict, quarantine, and full/incremental equivalence | Same passive-startup command | **PASS**. Seven tests pass, including production-boundary regressions for a cold conflicting claim, a moved-snapshot conflicting claim, a pending claim during an unrelated segment refresh, own-epoch appends, and retained-store enumeration failure. | `tests/test_observation_passive_startup.py`; direct. |
| AC-4(c) moved-snapshot preservation (Supervisor run-20 blocking item): a durable claim must not rest on an absence verdict that no longer covers the live retained snapshot | `uv run --frozen python scripts/run_tests.py -- -q tests/test_observation_passive_startup.py -p no:randomly` on the candidate, on a disposable `03c0e635` worktree, and on a disposable `d2874c2f` worktree (preservation reference) with the same production entry point | **PASS**. Candidate: hook refuses, no durable claim is appended, the pre-existing durable attribution is preserved and the contradictory intent is dropped by validation. `03c0e635`: same scenario, hook accepted and appended a second claim, resolution collapsed to `None`. Base: refuses and preserves. | `tests/test_observation_passive_startup.py::test_moved_snapshot_stops_an_absent_verdict_from_publishing_a_claim`; three-way table in §4. |
| AC-4(d): unchanged callback/reduction budgets | `uv run --frozen python scripts/run_tests.py -- -q tests/test_observation_performance.py` (included in focused run) | **PASS** in the focused suite; existing p95 ≤ 5 ms, p99 ≤ 20 ms callback and reduction gates remain unchanged and were not edited. | `tests/test_observation_performance.py`; direct. The previously independently measured candidate corpus recorded hook p95 0.8 µs / p99 2.8 µs. |
| AC-5(e): native/CLI busy and incomplete parity with later recovery | `uv run --frozen python scripts/run_tests.py -- -q tests/test_observation_query_parity.py tests/test_observation_cli_plugin.py tests/test_observation_brief_tool.py` (included in focused run) | **PASS**. Fixed native and CLI transient codes are returned under controlled contention; settled state succeeds with equivalent summaries. | `tests/test_observation_query_parity.py`; direct. |
| AC-5(f): genuine corruption/privacy failures remain errors without leaks | Same parity/CLI/brief command | **PASS**. Fixed unreadable errors remain errors; no raw exception, path, payload, or lock-owner detail is exposed. | `tests/test_observation_query_parity.py`; direct. |
| Focused observation lane | `uv run --frozen python scripts/run_tests.py -- -q tests/test_observation_performance.py tests/test_observation_brief_tool.py tests/test_observation_batch_replay_regression.py tests/test_observation_journal_storage.py tests/test_observation_ingest_scale.py tests/test_observation_cli_plugin.py tests/test_observation_passive_startup.py tests/test_observation_query_parity.py` | **256 passed**. | Canonical exact-Hermes runner; direct. |
| Full observation regression lane | `uv run --frozen python scripts/run_tests.py -- -q tests/test_observation_*.py` | **681 passed, 1 skipped**. Includes `tests/test_observation_qualification.py` at **60 passed, 1 skipped**. | Canonical exact-Hermes runner; direct. The skip is an existing qualification/environment boundary, not a suppressed failure. |
| Qualification lock and exact source harness | `uv run --frozen python scripts/qualify_observation.py test --checkout <isolated exact Hermes checkout> --json` | **472 passed**, `collected=472`; node manifest SHA-256 `c1b1215945754612bb768e513fbeefb4974ce6bba7b44fec39ab9a43ccc0ae0a` (equals the locked constant and the mirror); plugin callback count **22**; raw payload absent. | `scripts/qualify_observation.py`; direct. Exact Hermes source identity was the locked `v2026.8.18` / commit `e624e9fde561e1add9388384012b295fde669ade`, tag object `9f13bbbf8423427e159c78066356ca0e27ca6b74`, clean checkout; private checkout receipts are not copied here. |
| Static quality | `uv run --frozen ruff check src/aether_agents tests scripts && uv run --frozen ruff format --check src/aether_agents tests scripts && uv run --frozen mypy src/aether_agents` | **PASS**: Ruff clean, format clean for 178 files, mypy clean for 69 source files. | Direct. |
| Public-artifact path privacy | `uv run --frozen python scripts/check_public_artifacts.py` | **PASS** (tracked surface + 0 artifacts). | `scripts/check_public_artifacts.py`; direct. |

The companion public-artifact manifest comparison (`tests/test_public_artifacts.py::test_canonical_base_manifest_matches_tracked_non_specs_files`)
still fails at the supplied base and is owned by the documentation/integration units; this
unit did not edit `.github/workflows/policy.yml`. The same file's operator-path suite passes
(`32 passed, 567 subtests passed` for `tests/test_public_artifacts.py` + `tests/test_policy_hooks.py`).

## 3. Measured retained corpus, index cost, and the replaced decision window

The objective-scale reproduction used the isolated retained corpus shape previously measured
by Supervisor review: **244 journal files, 76 summaries, 7 registered projects, and 22 native
callbacks**. The accepted candidate measurement recorded passive registration **0.0222 s**,
initial background index build **0.0863 s** for a 35-segment project corpus, and unchanged
snapshot check **1.47 ms** mean under independent review; the prior behavior needed **7m36s**
to reach agent-ready because retained history was re-validated repeatedly.

This correction adds the moved-snapshot coverage pass to the binding-emission path only. An
isolated disposable store was rebuilt at the same scale (244 segments × 6 events = 1,464
events) and measured with the same production entry points:

| Measurement (isolated 244-segment corpus) | Candidate | Base `d2874c2f` |
|---|---|---|
| Initial full retained validation | 2.26 s | n/a (no index) |
| Coverage pass, unchanged snapshot | mean 5.12 ms / p95 7.31 ms / max 10.17 ms (200 samples) | n/a |
| Coverage pass, moved snapshot | mean 5.39 ms / p95 7.70 ms / max 15.38 ms (200 samples) | n/a |
| Durable append after the pass | mean 1.82 ms / max 8.50 ms (50 samples) | n/a |
| Full hook binding emission (projected event + pass + append) | mean 12.26 ms / p95 15.14 ms / max 17.25 ms; **50/50 durable** (own-epoch rule holds in bulk) | n/a |
| Locked full retained re-read that the pass replaces, on the same corpus | n/a | mean 2,176.67 ms / p95 3,879.87 ms / max 4,846.33 ms (50 samples) |

These are retained-corpus and registration measurements for the observed objective scale, not
a universal total-TUI SLO and not a rendered-shell readiness claim. No live installation, owner
process, or live observation store was touched; both revisions were exercised in disposable
worktrees with isolated HOME/XDG state.

### Preservation boundary of the moved-snapshot rule

- A foreign claim that has landed before the coverage pass reads its segment is detected: the
  intent stays pending, no durable claim is published, and the earlier attribution is preserved
  (regression plus three-way probe in §4).
- The coverage pass and the append are **not** atomic and are **not** serialized against foreign
  writers: O1 forbids hooks from holding the maintenance lock or waiting for history recovery,
  and no new coordinator, polling loop, or blocking wait was added. On the isolated corpus that
  unsynchronized interval measures a 5.12 ms mean pass followed by a 1.82 ms mean append. A
  foreign claim completing inside that window is not prevented; the canonical outcome is then an
  honest unresolved conflict (`binding_state == "conflict"`, no winner chosen by recency, no
  history erased) and the local coverage is reported unresolved rather than attributed. The base
  revision's equivalent decision window was its locked re-read followed by the append, measured
  at 2,176.67 ms mean on the same corpus, and it was equally unsynchronized against writers that
  do not take that lock.
- No preservation claim is made across that interval, and this is stated as a bounded residual in
  §7 rather than as eliminated risk.
- The window is narrowed, not enlarged: it is 2,177 ms → ~7 ms on the observed corpus scale, and
  the class it removes (publishing from a verdict that had already moved) is the class the review
  reproduced.

## 4. RED discipline and semantic-risk correction

The original passive-startup test could not collect at base because the retained-index module did
not exist there. The test harness conditionally imports that RC6-only module and, on the base
revision, patches the history seam present in both revisions: `hermes_plugin.list_segments`. The
base run reached that seam during registration and was held by the barrier; the test failed with
the expected synchronous-history assertion. The candidate run passes the same module (7 tests).
This is an executable RED/PASS pair, not a claim inferred only from the prior live observation.

The review reproduced two binding-window failures: a new hook claim could be emitted while
retained history still contained a contradictory binding, and a local in-memory claim could
disappear when another segment triggered re-aggregation. The earlier correction kept such claims
pending, never returned them as verified, preserved them across unrelated refreshes, and either
corroborated the exact retained row or left coverage unresolved. The run-20 review then showed
that the *cold* case was fixed but the *stale* case was not: a snapshot validated as `absent` for
a task kept licensing a durable claim after a foreign producer had attributed that task.

Three-way production-path measurement for the defect ordering (snapshot validated as `absent` for
`T` → another producer appends its durable claim `T → A` → this process's hook claims `T → B`):

| Revision | Hook verdict | Retained claims for `T` | Resolved binding for `T` |
|---|---|---|---|
| base `d2874c2f` (preservation reference) | refused (`False`) | 1 (`A`) | `(A, "root")` — preserved |
| `03c0e635` (prior candidate) | accepted (`True`), appended | 2 (`A`, `B`) | `None` — the conflict destroyed the durable attribution |
| current candidate | refused (`False`), intent left pending | 1 (`A`) | `(A, "root")` — preserved; the contradictory intent is dropped by validation |

Base has no asynchronous snapshot verdict, so it always re-read live retained evidence under the
maintenance lock; its entry-point behaviour was measured directly in a disposable base worktree
through the same production function. The same production probe in the opposite ordering (foreign
claim appended first, then the hook claim) returns `False`, one retained claim, and resolution
`(A, "root")` on base, on `03c0e635`, and on this candidate, so the correction adds no regression in
the ordering base already handled.

Regression receipts:

- Candidate, canonical lane, `tests/test_observation_passive_startup.py` → **7 passed**.
- Same module copied into a disposable `03c0e635` worktree → the stale-absence regression
  **fails on the behavioural assertion** (`assert not True = _emit_binding_durable(...)`), i.e. the
  hook publishes the claim; the companion mechanism test fails there with `AttributeError` because
  `snapshot_covers_disk` does not exist in that revision, so it is not the RED carrier.
- Same module in a disposable `92f0ae8b` worktree → fails earlier with `AttributeError: 'RetainedIndex'
  object has no attribute 'binding_state'`; that revision predates state classification, so this
  regression is honestly not executable there. RED for the class rests on `03c0e635`.

## 5. Direct versus reused attribution

**Direct in this correction**:

- `src/aether_agents/observation/capture/retained_index.py`: `_current_segment_stats` is now the
  single stat-only enumeration shared by validation and coverage; the private snapshot signature
  carries the owning producer epoch; `snapshot_covers_disk` implements the epoch-aware coverage
  verdict used before any absence-based durable claim.
- `src/aether_agents/observation/capture/hermes_plugin.py`: the hook binding path and the worker's
  pending-flush path both refuse to publish from a verdict that no longer covers the live retained
  evidence, increment `BINDING_STALE_SNAPSHOT`, and keep the intent pending instead.
- `tests/test_observation_passive_startup.py`: the moved-snapshot regression, the own-epoch
  non-regression, and the retained-claim reader used by both.
- `specs/001-aether-v1-productization/evidence/RC6-OBS.md`: this boundary statement, the
  three-way RED/GREEN receipt, and the re-measured corpus table.

**Reused and independently rechecked**: the previously reviewed native/CLI typed error mapping,
passive worker lifecycle, index segment parser, privacy/quarantine rules, callback and reduction
gates, qualification constants, and the 22-callback exact-Hermes harness. No observation core test
was added, removed, or renamed; the locked 472-node manifest and its mirror remain unchanged, and
`tests/fixtures/observation/complete-summary.json` was not regenerated.

## 6. Tracked manifest lines for integration

No new tracked non-`specs/` paths were added by this correction (the two regressions extend an
already-landed module). The unit's existing new paths relative to base, which must remain literal
in the integration manifest, are:

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
src/aether_agents/observation/capture/retained_index.py
src/aether_agents/observation/query.py
tests/test_observation_cli_plugin.py
tests/test_observation_passive_startup.py
```

Preserved owner boundaries include `src/aether_agents/lifecycle.py`, `src/aether_agents/cli.py`,
`src/aether_agents/launcher.py`, `scripts/aether_tui.py`, `docs/**`, `VERSION`,
`.github/workflows/policy.yml`, the normative specs, and
`tests/fixtures/observation/complete-summary.json`.

## 7. Residual risk and environment limits

- **Unsynchronized coverage interval (bounded, measured).** The coverage pass and the durable
  append are not serialized against foreign writers, because O1 forbids hooks from holding the
  maintenance lock and this unit added no coordinator or blocking wait. A foreign claim completing
  inside the measured 5.12 ms mean pass + 1.82 ms mean append window is not prevented and would
  produce an honest unresolved conflict instead of a stale-verdict claim. The window is ~300×
  narrower than the base decision window it replaces (2,176.67 ms mean) and is not claimed as
  eliminated.
- **Rule scope (explicit).** The coverage requirement applies where a claim can become
  *durable*: the hook binding path and the worker's pending flush. Restoring an already
  verified row into the in-memory binder is unchanged and continues to proceed from a
  validated snapshot (O1: verified native/canonical bindings proceed independently of slow
  historical catch-up). It writes no journal evidence, and if a later foreign claim changes
  that task's resolution the next validation reports the conflict honestly and stops
  attributing further events to it.
- **Own-epoch exemption.** The rule exempts segments of the emitting collector's own producer
  epoch, so a hook that emits a durable claim while the validated snapshot is unchanged still
  publishes immediately. A collector restart leaves the previous epoch's segments treated as
  foreign, which only makes the hook keep an intent pending until the worker re-validates; it is
  conservative, never a false attribution.
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
- The pre-existing `.github/workflows/policy.yml` manifest mismatch in
  `tests/test_public_artifacts.py` is unchanged by this unit and remains with RC6-DOCS/RC6-INT.
- This handoff does not claim live candidate-TUI readiness, integrated lifecycle/launcher
  compatibility, release qualification beyond the observation lane, publication, activation,
  or aggregate objective acceptance. Supervisor owns those conclusions and the next review.
