# RC6-OBS — Passive observer startup, retained-history index, and native query parity

**Unit**: RC6-OBS (`t_f6d83945`), Implementer. The bounded continuation **RC6-OBS-2**
(`t_6020b35d`) corrects the post-review discrepancy the design steward opened on the
accepted tip and is recorded in place below.
**Authority**: Objective Contract `oc_b5926701207812e8@v1` (digest
`e7164c83862b747c7868706799c08ea63151ca388aa2dc2b1b89a40be33b01fc`), base
`d2874c2f3fc839a82fbaa96ece6edebab3856298`, and
`specs/001-aether-v1-productization/plan-rc6.md` §O1/§O2.
**Scope**: O1, O2, D1; acceptance AC-4 and AC-5. The contract was not edited.
**Compatibility conclusion**: unit-level `patch`; no aggregate release or publication conclusion.
**Accepted tip carried forward**: `00be3b17630e108c53994e15afb380f31dffada3`. The
correction changes no accepted criterion; it removes two claims that were not true of
that tip (`INCOMPLETE_IMPLEMENTATIONS`-class overstatement), recorded in §4.1.

## 1. Implemented behavior

1. Registration and synchronous native hooks remain passive. Retained journal validation,
   native reads, and maintenance-lock work run through the plugin-owned reconciliation
   worker rather than `_Observer` construction, collector creation, or hot callbacks.
2. `RetainedIndex` validates one retained snapshot and reuses unchanged segment state.
   Its snapshot state is `validated`, `incomplete`, or `unavailable`; invalid, replaced,
   truncated, quarantined, and unverified archive inputs cannot become verified bindings.
   Segment enumeration failures increment `RETAINED_INDEX_UNAVAILABLE` and do not look like
   an empty successful snapshot.
3. Native binding claims are never published by a synchronous hook. A hook restores an
   already-verified row (no journal evidence, unchanged) and keeps every other state -
   including a validated `absent` verdict - as a pending intent for the worker. The
   reconciliation worker validates at its own cadence and publishes pending intents
   inside the `native-binding` project lock, so cooperating emitters serialize. The hook
   is therefore free of retained-history replay, archive verification and decompression,
   and maintenance-lock waits, and it cannot publish a claim that contradicts evidence
   that moved after the snapshot it read.
4. `RetainedIndex.snapshot_covers_disk` is a stat-only comparison of the live segment set
   against the validated snapshot signature. *Correction*: the accepted tip's version was
   stat-only for live segments but called `verify_archive` for every archived segment,
   which hashes the compressed bytes, decompresses the gzip and re-validates every
   archived event. It is now genuinely stat-only: `_current_segment_stats(..., verify_archives=False)`
   reads no manifest and no archived content, and only the asynchronous validation path
   re-verifies archives. The verdict is consulted by the worker's validated emission
   (§1.3), never by a hook. If any segment owned by another producer appeared, grew, was
   replaced, was truncated, or disappeared after validation, the absence verdict is no
   longer proof, a content-free `BINDING_STALE_SNAPSHOT` counter is incremented, and the
   intent stays pending for the next validated cycle. The process's own producer epoch is
   exempt, because its own appends and rotations are tracked here as pending intents and
   cannot contradict its own validated evidence.
5. The previously implemented native/CLI query parity and fixed transient codes remain
   intact: native `AETHER-OBSERVE-BUSY` / `AETHER-OBSERVE-CATCHUP-INCOMPLETE` and CLI
   `STATE_BUSY` / `CATCHUP_INCOMPLETE`, with genuine unreadable state still fail-closed.

## 2. Requirement → check → observed result → evidence

| Requirement / oracle | Check actually run | Observed result | Evidence path / attribution |
|---|---|---|---|
| AC-4(a): registration and hot hooks do not wait for a paused retained reader | `uv run --frozen python scripts/run_tests.py -- -q tests/test_observation_passive_startup.py` | **PASS**. Candidate registration and hot-hook path complete while the worker-side reader is held; the base-compatible harness fails intentionally when the base synchronous path reaches the patched `hermes_plugin.list_segments` barrier. | `tests/test_observation_passive_startup.py`; direct candidate run. The d2874c2f base RED receipt (**1 failed**, expected synchronous-history assertion) is the accepted unit's measurement, reused here and not re-run by RC6-OBS-2; the RC6-OBS-2 base runs are in §4.2. |
| AC-4(b): one validated index per unchanged snapshot | Same passive-startup command; instrumentation asserts `validation_count` remains one across repeated lookups and increments once after an append | **PASS**. Counters demonstrate reuse rather than prose-only attribution. | `tests/test_observation_passive_startup.py::test_unchanged_retained_snapshot_validated_once_via_instrumentation`; direct. |
| AC-4(c): append, replacement, truncation, conflict, quarantine, and full/incremental equivalence | Same passive-startup command | **PASS**. Ten tests pass, including production-boundary regressions for a cold conflicting claim, a moved-snapshot conflicting claim, a pending claim during an unrelated segment refresh, own-epoch appends, retained-store enumeration failure, the archived-history hook path, cooperating-writer serialization, and worker-mode publication. | `tests/test_observation_passive_startup.py`; direct. |
| AC-4(c) archive-path oracle (RC6-OBS-2): the synchronous hook binding path must not read or re-validate archived history | `... -q tests/test_observation_passive_startup.py::test_hook_binding_path_reads_no_archived_history_and_stays_bounded` on a corpus built with the production compaction path (3 archives x 400 events) with `verify_archive` / `_read_gzip_segment` instrumented | **PASS**. Hook path: **0** `verify_archive` calls, **0** decompressions, mean 0.437 ms / p95 0.485 ms / max 0.661 ms over 20 samples; the hook publishes nothing, keeps the intent `pending`, and the worker then publishes it with the same zero archive reads. | `tests/test_observation_passive_startup.py`; direct. RED at `00be3b17` on the same file: `hook read archived history: {'verify_archive': 3, 'read_gzip_segment': 3} in 1.183s over 3 archived segments`. |
| AC-4(c) cooperating-writer serialization oracle (RC6-OBS-2): with a pre-existing durable claim for task `T`, a cooperating emitter for the same task must leave exactly one durable claim, preserve the attribution and create no unresolvable conflict | `... -q tests/test_observation_passive_startup.py::test_cooperating_emitters_serialize_absence_based_durable_emission` (interleaves a cooperating emitter, base `d2874c2f`'s read+emit order under `project_lock(paths, "native-binding")` over the production retained read and the production emit, into the worker's verdict→append window) | **PASS**. The cooperating emitter cannot enter the critical section (`serialized_out`); exactly one durable claim results; a second cooperating emitter for the same task is `refused`; the retained resolution keeps the winning attribution and stays `verified`. | `tests/test_observation_passive_startup.py`; direct. RED at `00be3b17`: cooperating emitter `emitted`, two retained claims for one task (`ctr_8888…`, `ctr_7777…`) and resolution collapsed to `None`. |
| AC-4(c) worker publication (RC6-OBS-2): the worker publishes validated absence claims exactly once, under the lock | `... -q tests/test_observation_passive_startup.py::test_worker_emission_publishes_validated_absence_claims_once_under_the_lock` | **PASS**. Hook path publishes nothing and takes no lock; the worker-mode call publishes under `native-binding` and the flush appends nothing a second time. | `tests/test_observation_passive_startup.py`; direct. RED at `00be3b17` (the hook publishes). |
| AC-4(c) moved-snapshot preservation (Supervisor run-20 blocking item): a durable claim must not rest on an absence verdict that no longer covers the live retained snapshot | `uv run --frozen python scripts/run_tests.py -- -q tests/test_observation_passive_startup.py -p no:randomly` on the candidate, on a disposable `03c0e635` worktree, and on a disposable `d2874c2f` worktree (preservation reference) with the same production entry point | **PASS**. Candidate: neither the hook nor the worker publishes; no durable claim is appended, the pre-existing durable attribution is preserved and the contradictory intent is dropped by validation. `03c0e635`: the hook accepted and appended a second claim, resolution collapsed to `None`. Base: refuses and preserves. | `tests/test_observation_passive_startup.py::test_moved_snapshot_stops_an_absent_verdict_from_publishing_a_claim`; three-way table in §4. |
| AC-4(d): unchanged callback/reduction budgets | `uv run --frozen python scripts/run_tests.py -- -q tests/test_observation_performance.py` (included in focused run) | **PASS** in the focused suite; existing p95 ≤ 5 ms, p99 ≤ 20 ms callback and reduction gates remain unchanged and were not edited. | `tests/test_observation_performance.py`; direct. The previously independently measured candidate corpus recorded hook p95 0.8 µs / p99 2.8 µs. |
| AC-5(e): native/CLI busy and incomplete parity with later recovery | `uv run --frozen python scripts/run_tests.py -- -q tests/test_observation_query_parity.py tests/test_observation_cli_plugin.py tests/test_observation_brief_tool.py` (included in focused run) | **PASS**. Fixed native and CLI transient codes are returned under controlled contention; settled state succeeds with equivalent summaries. Four native-payload tests now drive the worker's validated emission explicitly because the hook no longer publishes; they pass on the accepted tip as well. | `tests/test_observation_query_parity.py`; direct. |
| AC-5(f): genuine corruption/privacy failures remain errors without leaks | Same parity/CLI/brief command | **PASS**. Fixed unreadable errors remain errors; no raw exception, path, payload, or lock-owner detail is exposed. | `tests/test_observation_query_parity.py`; direct. |
| Focused observation lane | `uv run --frozen python scripts/run_tests.py -- -q tests/test_observation_performance.py tests/test_observation_brief_tool.py tests/test_observation_batch_replay_regression.py tests/test_observation_journal_storage.py tests/test_observation_ingest_scale.py tests/test_observation_cli_plugin.py tests/test_observation_passive_startup.py tests/test_observation_query_parity.py` | **259 passed** (accepted tip: 256; the three RC6-OBS-2 regressions are the delta). | Canonical exact-Hermes runner; direct. |
| Full observation regression lane | `uv run --frozen python scripts/run_tests.py -- -q tests/test_observation_*.py` | **684 passed, 1 skipped** (accepted tip: 681 passed, 1 skipped). Includes `tests/test_observation_qualification.py` at **60 passed, 1 skipped**. | Canonical exact-Hermes runner; direct. The skip is an existing qualification/environment boundary, not a suppressed failure. |
| Qualification lock and exact source harness | `uv run --frozen python scripts/qualify_observation.py test --checkout <isolated exact Hermes checkout> --json` | exit 0; `collected=472`, `passed=472`; node manifest SHA-256 `c1b1215945754612bb768e513fbeefb4974ce6bba7b44fec39ab9a43ccc0ae0a` (equals the locked constant and the mirror); plugin callback count **22**; raw payload absent. The locked constants and `tests/fixtures/observation/complete-summary.json` were not touched. | `scripts/qualify_observation.py`; direct. Exact Hermes source identity was the locked `v2026.8.18` / commit `e624e9fde561e1add9388384012b295fde669ade`, tag object `9f13bbbf8423427e159c78066356ca0e27ca6b74`, clean checkout; private checkout receipts are not copied here. |
| Static quality | `uv run --frozen ruff check src/aether_agents tests scripts && uv run --frozen ruff format --check src/aether_agents tests scripts && uv run --frozen mypy src/aether_agents` | **PASS**: Ruff clean, format clean for 178 files, mypy clean for 69 source files. | Direct. |
| Public-artifact path privacy | `uv run --frozen python scripts/check_public_artifacts.py` | **PASS** (tracked surface + 0 artifacts). | `scripts/check_public_artifacts.py`; direct. |
| Patch hygiene | `git diff --check` on the unit branch | **PASS** (no whitespace/conflict residue). | Direct. |

The companion public-artifact manifest comparison (`tests/test_public_artifacts.py::test_canonical_base_manifest_matches_tracked_non_specs_files`)
still fails at the supplied base and is owned by the documentation/integration units; this
unit did not edit `.github/workflows/policy.yml` and added no tracked non-`specs/` file
(§6). The same file's operator-path suite passes (`32 passed, 567 subtests passed` for
`tests/test_public_artifacts.py` + `tests/test_policy_hooks.py`).

## 3. Measured retained corpus, index cost, and the replaced decision window

The objective-scale reproduction used the isolated retained corpus shape previously measured
by Supervisor review: **244 journal files, 76 summaries, 7 registered projects, and 22 native
callbacks**. The accepted candidate measurement recorded passive registration **0.0222 s**,
initial background index build **0.0863 s** for a 35-segment project corpus, and unchanged
snapshot check **1.47 ms** mean under independent review; the prior behavior needed **7m36s**
to reach agent-ready because retained history was re-validated repeatedly.

The correction adds the moved-snapshot coverage pass to the binding-emission path only. An
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

### 3.1 Archived-history cost (RC6-OBS-2 correction)

The 244-segment corpus above contains no archived segments, so it could not see the
defect the steward found. A second isolated corpus puts the whole retained history in
**verified archives** (3 archived segments × 400 events = 1,200 archived events), each
produced by the production compaction path (`compact_segment`) from a closed segment of
its own producer epoch and verified with `verify_archive`. The same disposable-store
harness was run against the accepted tip and against this correction (20 samples each):

| Measurement (isolated 3-archive corpus, 1,200 archived events) | Accepted tip `00be3b17` | This correction |
|---|---|---|
| Hook binding claim, mean / p95 / max | 1,218.1 / 1,291.4 / 1,303.5 ms | **0.437 / 0.485 / 0.661 ms** |
| `verify_archive` calls per hook claim | 3 (+ 3 gzip decompressions) | **0** |
| Coverage verdict (stat-only), mean / p95 / max | 1,194.4 / 1,244.5 / 1,246.1 ms | **0.649 / 0.742 / 0.986 ms** |
| Worker flush with no pending intents | 1,210.3 ms (the verdict ran unconditionally) | **< 0.1 ms** (returns before any coverage work) |
| Worker flush publishing 21 pending intents | n/a (the hook had published them already) | **23.5 ms total** |
| Background index validation of the archived corpus | 2.42 s | 2.44 s (unchanged background work) |
| Archived-content reads on the hook path (in-test instrumentation) | 3 + 3 per claim | **0** |

Run-to-run variance on the corrected revision: a first pass of the same harness measured
hook mean 0.579 ms / coverage mean 0.792 ms / flush 31.4 ms, i.e. the quoted figures are
the same order and not a favourable single sample. The ~2,800× narrowing on the hook path
is the point; no universal latency SLO is claimed from these retained-corpus numbers, and
none is claimed for a rendered shell or a whole TUI start.

### 3.2 Preservation boundary of the absence rule (corrected)

- **Serialized cooperating writers.** The emission critical section is the coverage
  verdict *and* the append under `project_lock(paths, "native-binding")` - the same lock
  the pre-fix production emitter held across its retained read and its append. A
  cooperating emitter that read the same absence therefore cannot also append: whichever
  process takes the lock first publishes, and the other re-checks and refuses. The
  withdrawn premise was that this was impossible "because hooks may not lock"; O1 forbids
  *blocking hooks*, not the existing background worker, and hooks do not publish at all
  now. Serialization receipt: §2 (serialization oracle).
- **Non-cooperating writers.** A writer that appends a contradictory claim without taking
  that lock is still caught by the stat-only coverage verdict, which detects the changed
  segment signature and refuses. A claim that lands inside the remaining unsynchronized
  window (a non-cooperating writer in the sub-millisecond gap between the verdict and the
  append) is not prevented; the canonical outcome is then an honest unresolved conflict
  (`binding_state == "conflict"`, no winner chosen by recency, no history erased) and the
  local coverage is reported unresolved rather than attributed. This residual is stated in
  §7 and is not claimed as eliminated.
- **Hooks never publish.** An absence-based hook intent becomes durable at the worker's
  next cycle. Every hook in `_RECONCILIATION_HOOKS` requests that cycle immediately
  (debounce 0.05 s); the worker's own 30 s interval only bounds the case where nothing
  requests a cycle. The cost of that cycle's validation is background work, off the agent
  path.
- **Already-verified bindings.** Restoring a verified row into the in-memory binder is
  unchanged and proceeds from the validated snapshot (O1: verified native/canonical
  bindings proceed independently of slow historical catch-up). It writes no journal
  evidence, and if a later foreign claim changes that task's resolution the next validation
  reports the conflict honestly and stops attributing further events to it.

## 4. RED discipline and semantic-risk correction

The original passive-startup test could not collect at base because the retained-index module did
not exist there. The test harness conditionally imports that RC6-only module and, on the base
revision, patches the history seam present in both revisions: `hermes_plugin.list_segments`. The
base run reached that seam during registration and was held by the barrier; the test failed with
the expected synchronous-history assertion. The candidate run passes the same module (10 tests).
This is an executable RED/PASS pair, not a claim inferred only from the prior live observation.

The review reproduced two binding-window failures: a new hook claim could be emitted while
retained history still contained a contradictory binding, and a local in-memory claim could
disappear when another segment triggered re-aggregation. The earlier correction kept such claims
pending, never returned them as verified, preserved them across unrelated refreshes, and either
corroborated the exact retained row or left coverage unresolved. The run-20 review then showed
that the *cold* case was fixed but the *stale* case was not: a snapshot validated as `absent` for
a task kept licensing a durable claim after a foreign producer had attributed that task.

### 4.1 What the steward's discrepancy corrected

1. **"stat-only" was false for archives.** `snapshot_covers_disk` reached
   `_current_segment_stats`, which called `verify_archive` for every archived segment:
   manifest read, compressed-byte hash, gzip decompression, and schema/sequence/privacy
   validation of every archived event (`src/aether_agents/observation/retention.py`). On
   the archived corpus above that is 3 calls and ~1.2 s per hook claim, on every claim,
   with no caching. The live store holds 0 archived files today, so the impact was
   prospective - but it is the exact O1 defect class this unit exists to remove, and it
   would have started costing seconds per `kanban_create` the moment retention compacted
   a segment. The previous tests missed it because their corpora contained no archived
   segments and the barrier harness patched `refresh`, not the archive verification inside
   the coverage check.
2. **The unsynchronized check→append residual rested on a withdrawn premise.** The accepted
   text claimed the unprotected interval was inherent "because hooks may not lock". O1
   forbids blocking hooks, not validated and serialized emission in the existing worker.
   The pre-fix production emitter held `project_lock(paths, "native-binding")` across
   read+emit; that serialization is restored on the emission path that remains.

### 4.2 RED receipts for the new regressions

Disposable detached worktree at `00be3b17` with this unit's test files copied in and the
same canonical runner:

- `tests/test_observation_passive_startup.py` → **4 failed, 6 passed**:
  `test_hook_binding_path_reads_no_archived_history_and_stays_bounded` (RED detail:
  `hook read archived history: {'verify_archive': 3, 'read_gzip_segment': 3} in 1.183s
  over 3 archived segments`), `test_cooperating_emitters_serialize_absence_based_durable_emission`
  (RED detail: cooperating emitter `emitted`; two retained claims for one task), the
  worker-publication regression (RED detail: the hook published and returned `True`), and
  the updated own-producer regression, which encodes the corrected hook contract and fails
  where the accepted tip publishes from the hook.
- `tests/test_observation_cli_plugin.py` → **65 passed** at base as well: the four tests
  updated to drive the worker's validated emission explicitly are preservation tests, green
  on both revisions.
- Candidate: the same two modules and the full lane pass (§2).
- The measurement harness is revision-agnostic: the same script, corpus shape, and
  entry points were run against both revisions (§3.1).

## 5. Direct versus reused attribution

**Direct in the RC6-OBS-2 correction**:

- `src/aether_agents/observation/capture/retained_index.py`: `_current_segment_stats`
  gains the `verify_archives` mode (stat-only enumeration for coverage, manifest
  re-verification only on the asynchronous validation path); `snapshot_covers_disk` uses it
  and its docstring now states exactly what it does.
- `src/aether_agents/observation/capture/hermes_plugin.py`: `_emit_binding_durable` splits
  the hook path (restore verified, else keep pending) from the worker path
  (`from_worker=True`, the two reconciliation call sites) and the new
  `_publish_absent_binding` holds `project_lock(paths, "native-binding")` across the
  stat-only verdict and the append; `_flush_pending_binding_events` takes the same lock
  over its verdict and appends, increments `BINDING_STALE_SNAPSHOT` when the verdict no
  longer covers the live evidence, and returns before any coverage work when nothing is
  pending.
- `tests/test_observation_passive_startup.py`: the archived-corpus builder and
  content-read instrumentation, the archive-path regression, the cooperating-writer
  interleave regression, the worker-publication regression, and the updated own-producer
  regression.
- `tests/test_observation_cli_plugin.py`: the shared `_publish_pending_bindings` driver and
  its four call sites, which now exercise the worker's validated emission explicitly.
- `specs/001-aether-v1-productization/evidence/RC6-OBS.md`: this correction, the
  archived-corpus measurements, and the corrected residual text.

**Direct in the original RC6-OBS unit** (reused unchanged): the retained index, the worker
lifecycle, native/CLI typed error mapping, the segment parser, privacy/quarantine rules, the
callback and reduction gates. **Reused and independently rechecked by RC6-OBS-2**: the
locked qualification constants and the 22-callback exact-Hermes harness (re-run, unchanged);
no observation core test was added, removed, or renamed, and
`tests/fixtures/observation/complete-summary.json` was not regenerated.

## 6. Tracked manifest lines for integration

**No new tracked non-`specs/` paths were added or renamed by RC6-OBS-2** - it edits only
files RC6-OBS already landed, so the manifest lines for integration are unchanged:

```text
src/aether_agents/observation/capture/retained_index.py
tests/test_observation_passive_startup.py
tests/test_observation_query_parity.py
```

Paths modified by RC6-OBS-2, all inside the assigned writable surface:

```text
src/aether_agents/observation/capture/hermes_plugin.py
src/aether_agents/observation/capture/retained_index.py
tests/test_observation_cli_plugin.py
tests/test_observation_passive_startup.py
```

Preserved owner boundaries include `src/aether_agents/lifecycle.py`, `src/aether_agents/cli.py`,
`src/aether_agents/launcher.py`, `scripts/aether_tui.py`, `docs/**`, `VERSION`,
`.github/workflows/policy.yml`, the normative specs, and
`tests/fixtures/observation/complete-summary.json`.

## 7. Residual risk and environment limits

- **Serialized cooperators, honest non-cooperating window (bounded, measured).** Absence
  -based publication now happens only in the worker, under the `native-binding` project
  lock, so two cooperating emitters cannot both publish a contradictory claim for one
  task. A writer that ignores that lock can still land a claim inside the remaining
  sub-millisecond window between the stat-only verdict and the append; the canonical
  outcome is then an honest unresolved conflict, never a stale-verdict claim. The window
  is not claimed as eliminated, and it no longer sits on the synchronous hook path at all.
- **Hook intents are durable at worker cadence.** A binding intent recorded by a hook is
  published on the worker's next cycle, which the hook requests immediately (debounce
  0.05 s); if the process stops before that cycle, the intent is simply never published -
  honest incomplete coverage, never a false attribution. This replaces instant hook
  publication, which is what the objective's "hooks stay free of history work" requires.
- **Rule scope (explicit).** The coverage requirement applies where a claim can become
  *durable*: the worker's direct publication and its pending flush. Restoring an already
  verified row into the in-memory binder is unchanged and continues to proceed from a
  validated snapshot, writes no journal evidence, and is re-judged by the next validation.
- **Own-epoch exemption.** The rule exempts segments of the emitting collector's own producer
  epoch, so a healthy single-producer session is not stalled by its own appends. A collector
  restart leaves the previous epoch's segments treated as foreign, which only makes the
  emission wait for re-validation; it is conservative, never a false attribution.
- **Archive-manifest drift is not a content-drift signal.** The stat-only verdict compares
  archive bytes, not manifests: an archive whose manifest became unreadable while its bytes
  stayed identical still carries exactly the events the validated snapshot read, so its
  contribution to the absence verdict is unchanged. Validation itself still refuses an
  archive it cannot verify and reports `incomplete`.
- If retained segment enumeration or archive verification is unavailable, the index reports
  `unavailable`/`incomplete`, increments a content-free health counter, and returns no
  verified binding. A later worker cycle must reattempt validation; this is not reported as
  a successful empty state.
- The focused and full observation lanes use the canonical exact-Hermes runner because plain
  pytest without the locked Hermes checkout cannot import the native `hermes_cli` boundary.
  The exact checkout, HOME/XDG state, and temporary qualification destinations were isolated;
  no live profile, board, gateway, TUI, credentials, provider configuration, or external
  service was read for mutation or changed by this unit. The archived-corpus harness ran in a
  throwaway isolated store with every `HERMES_KANBAN_*` variable removed.
- The pre-existing `.github/workflows/policy.yml` manifest mismatch in
  `tests/test_public_artifacts.py` is unchanged by this unit and remains with RC6-DOCS/RC6-INT.
- This handoff does not claim live candidate-TUI readiness, integrated lifecycle/launcher
  compatibility, release qualification beyond the observation lane, publication, activation,
  or aggregate objective acceptance. Supervisor owns those conclusions and the next review.
