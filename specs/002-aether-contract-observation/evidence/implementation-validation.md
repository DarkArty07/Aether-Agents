# Contract Observation implementation validation

**Evidence cut**: 2026-08-24

**Product version in the working tree**: `0.24.0`

**Branch**: `feat/002-contract-observation`

**Base HEAD**: `47e26c5884d906aeb9790937910ec4a7bb67c3ed`

**Verdict**: **partial / under validation**

This is an evidence ledger, not a release certificate. It records only commands and
results observed during implementation or reproduced against the current working tree.
The implementation is not committed at the base HEAD above, the final Python/build/CI
matrix has not run, and the owner-approved real provider trace in issue #195 has not run.
Consequently this document does not call the layer complete, release-ready, or
production-ready.

## 1. Qualification contract

The block below is the stable machine-readable **acceptance contract** consumed by
`scripts/qualify_observation.py`. It is not a substitute for a final execution record.
In particular, the event counts state what the real 10k/100k runs must retain; final
timings and rates remain pending later in this report.

<!-- BEGIN AETHER_OBSERVATION_QUALIFICATION_RESULTS_V1 -->
```json
{
  "schema_version": 1,
  "claims": {
    "tests": {
      "minimum": 119,
      "plugin_callback_count": 22,
      "unload_hook_count": 0,
      "hermes_checkout": {
        "tag": "v2026.8.18",
        "tag_object": "9f13bbbf8423427e159c78066356ca0e27ca6b74",
        "commit": "e624e9fde561e1add9388384012b295fde669ade",
        "clean": true
      }
    },
    "benchmark": {
      "schema_version": 1,
      "reduction": {
        "ten_thousand": {
          "event_count": 10000,
          "source_event_count": 10000
        },
        "one_hundred_thousand": {
          "event_count": 100000,
          "source_event_count": 100000
        }
      },
      "callback": {
        "plugin_callback_count": 22,
        "unload_hook_count": 0,
        "raw_prompt_absent": true,
        "raw_response_absent": true
      },
      "flush": {
        "synchronous_callback_fsync": false
      },
      "incremental_pipeline": {
        "mode": "incremental_journal_sqlite_projection",
        "normative_counts_complete": true,
        "event_counts": [10000, 100000],
        "ten_thousand": {
          "event_count": 10000,
          "source_event_count": 10000
        },
        "one_hundred_thousand": {
          "event_count": 100000,
          "source_event_count": 100000
        }
      }
    }
  }
}
```
<!-- END AETHER_OBSERVATION_QUALIFICATION_RESULTS_V1 -->

## 2. Exact Hermes evidence boundary

The qualifying public baseline is Hermes Agent `0.20.4`, annotated tag
`v2026.8.18`, tag object
`9f13bbbf8423427e159c78066356ca0e27ca6b74`, dereferenced commit
`e624e9fde561e1add9388384012b295fde669ade`.

Two disposable checkouts with those coordinates have been inspected:

- `/tmp/aether-qualification-hermes-v2026.8.18` is the checkout used by the
  reproducible qualification route. A read-only inspection on this evidence cut
  returned the exact commit/tag object above and empty `git status --porcelain=v1`.
- `/tmp/aether-hermes-v2026.8.18` is the checkout used by the focused exact-lifecycle
  audit. It returned the same commit/tag object and empty porcelain status.

The dirty checkout under
`/home/darkarty/Desktop/agentes/aether/home/.venv-hermes/src/hermes-agent` is not an
evidence input and is never treated as qualifying.

The upstream tag does not produce an ordinary Hermes wheel/sdist through its own build
configuration. `LifecycleManager.prepare_release()` therefore first authenticates the
public tag/commit, materializes only that commit's tracked bytes with `git archive` into
the candidate's release-local `<release>/hermes-source`, records a deterministic tree
digest, exports the locked Hermes dependency plan outside that authenticated tree, and
installs Hermes with PEP 660 metadata pointing to the release-local archive. It does
**not** copy ignored/untracked checkout bytes or point at the temporary evidence
checkout. The one closed `hermes_agent.egg-info` build-debris directory created by the
editable build is removed after installation and the tracked-tree digest is proved
again. This release-local PEP 660 exception concerns Hermes only: the same staged,
immutable `aether-agents` wheel is installed normally into manager and runtime.

This nuance must remain visible in release review. It must not be rewritten as either
“Hermes wheel built successfully” or “runtime uses the mutable qualification checkout.”

## 3. Issue-to-implementation map

The statuses below describe evidence present in this working tree; they do not close
the corresponding GitHub issues.

| Issue | Implemented boundary and regression evidence | Current disposition |
|---|---|---|
| #213 | `observation/checkpoint.py`, `observation/reduce/reducer.py`, `observation/storage.py`, the structured event schema, and authority/review/query regressions prevent a caller-selected role or a mere raw event from proving completion or terminality. Exact root/acceptance/ten-invariant closure and post-verification semantic-delta invalidation remain enforced. Parentage, binding, run-terminal, event-ID, and producer-sequence conflicts that affect the work graph now invalidate graph settlement instead of surviving as documentary gaps beside `completed`. | Completion authority, read-side terminal authority, graph-conflict closure, and the product-shaped durable-review path are GREEN in focused tests. Final full-suite and independent final-diff review are pending; do not mark closed from focused evidence alone. |
| #214 | Native `relation`/`required` remain `unknown`/null unless an exact product-owned classification exists. Retained JSONL cannot bootstrap a binding without canonical schema/privacy/segment verification. Event-ID/native-identity/producer-sequence conflicts become reproducible bounded gaps and neutralize only the graph facts they contradict; unrelated tool/model conflicts do not become a global completion gate. Producer clocks and timestamps do not invent causal edges, retry, waves, or freshness. Durable task-parent edges enter the process DAG only when they select one unique parent attempt. | Focused causal, retained-bootstrap, ambiguity, permutation, and sabotage probes are GREEN; final full-suite replay is pending. |
| #215 | Unpaired terminals, missing turn/API IDs, heartbeat recency, absent dispatch limits, hook coverage, and every native run outcome remain separate coverage facts. A terminal without a start no longer yields complete coverage, and a recovered historical crash cannot manufacture current `stale` liveness. | Focused regressions and heartbeat controls are GREEN; final qualification output is pending. |
| #216 | `capture/journal.py` retains critical flush debt after failed `fsync`, wakes on critical events, bounds stop, and preserves source through incomplete archive/manifest/file/directory durability. Compaction and recovery use verified, idempotent transitions. | Recorded focused RED/GREEN and an expanded storage run exist; final Python matrix is pending. |
| #217 | `observation/storage.py` makes raw event plus derivations atomic, commits derivation diagnostics separately, isolates bulk failures, fences readers/writers, durably replaces projection pointers, and preserves unknown-newer source bytes across update/rollback/re-update. | Recorded storage GREEN plus an explicit SQLite TOCTOU kill test exist; final matrix is pending. |
| #218 | `observation/privacy.py`, schema reference grammars, and every native projector reject raw command/output/error/prompt/response and host-path shapes before queue, journal, SQLite, summary, retry, or diagnostic persistence. Tests use full malicious native callback/reconciliation payloads. | Structural tests exist; final three-version suite and exact qualification privacy scan are pending. |
| #219 | `paths.py`, atomic writers, product-state readers, journal/storage primitives, retained/recovery readers, projection fences, and lifecycle authority roots require absolute XDG roots, closed generated components, directory-relative no-follow opens, single-link private files, and `0600` DB/WAL/SHM. Registry/key/summary/projection/active-release/transition/ownership bytes cannot enter authority through an external symlink, hard link, or name swap; compaction/recovery likewise never accept an external alias as observation evidence. | Relative/tilde XDG, predictable-temp, reader alias, segment/source link, rename race, sidecar, SQLite TOCTOU, authority-swap, and purge-ownership tests are present; focused probes and sabotage are GREEN. |
| #220 | `scripts/qualify_observation.py`, `tests/test_observation_qualification.py`, and CI policy recreate/verify the exact public tag, require at least 119 observation tests, exercise real `PluginContext`, require 22 registered callbacks, capture tool/API events without raw prompt/response, and require zero hooks after unload. | Exact checkout identity is verified and focused real-plugin/lifecycle evidence exists. The final runner result and CI job are `PENDING_FINAL_EXACT_HERMES_QUALIFICATION` and `PENDING_FINAL_CI_STATUS`. |
| #221 | `lifecycle.py`, `cli.py`, schema-3 `ReleaseRecord`, dual manager/runtime installs of one Aether wheel, marker-aware hash-locked dependency closure, three explicit profile homes, doctor, atomic transition/CAS/recovery, update/rollback/re-update, preserve/purge uninstall, and exact public lifecycle tests cover the observation-related A1 slice. | Changes still requested: active-manager dispatch/identity enforcement and doctor integrity classification are under implementation. The canonical A1 release-lock schema is version 3, but final release-lock instance/provenance, full lifecycle matrix, committed diff, PR/CI, and #195 also remain pending. |
| #222 | `commands/observe.py` and the A1/002 CLI contracts expose one discriminated JSON union: empty is exactly `{"state":"empty","summary":null}` and a resolved trace is `{"state":"summary","summary":{...}}`. Human output is projected from the same representation; an explicit unknown `REF` returns `TRACE_NOT_FOUND` instead of being mistaken for global emptiness. `--watch --json` is rejected with one stable envelope rather than silently becoming NDJSON. | RED/GREEN and sabotage are recorded below. Focused current replay is GREEN; final matrix and PR/CI remain pending. |

### A1 schema-3, wheel, home, and state facts

- The canonical contract at
  `specs/001-aether-v1-productization/contracts/release-lock.schema.json` has
  `schema_version: 3` and binds the observer entry-point tuple plus event, summary,
  segment-manifest, and projection write/read compatibility.
- The local active `ReleaseRecord` also uses schema 3 and validates that every write
  version belongs to its read set. It records the same-wheel digest/pre-build identity,
  installed-file fingerprint, observer tuple, packaged schema digests, Hermes source
  identity, and profile-bundle digest.
- The release transition installs one staged Aether wheel into both manager and runtime,
  then compares installed identities. No per-profile observer wheel or editable Aether
  source copy is created.
- Product-owned profile homes are explicit and persistent under
  `XDG_DATA_HOME/aether/profiles/{morfeo,supervisor,implementer}`. Mutable transition and
  observation state is under `XDG_STATE_HOME/aether`. Tests use disposable homes only.
- A final canonical release-lock **instance** with external artifact URLs/digests and
  provenance is not present in this evidence cut. The local schema-3 transition record
  must not be presented as that publication artifact.

## 4. TDD regression ledger

All commands below unset delegated-child context and use disposable pytest roots. RED
results describe the deliberately failing implementation cut before the minimal fix;
GREEN results describe the subsequent run. Where a literal historical selection was
not retained, this report says so instead of reconstructing a command.

### 4.1 Caller-selected checkpoint authority

Exact RED and same-node GREEN command:

```bash
env -u HERMES_DELEGATED_CHILD_CONTEXT \
  UV_PROJECT_ENVIRONMENT=/tmp/aether-py311 \
  uv run --python 3.11 --frozen pytest -q \
  tests/test_observation_contracts.py::test_checkpoint_constructor_rejects_caller_selected_authority
```

- RED: `1 failed`; `pytest.raises(TypeError)` reported **DID NOT RAISE** because the
  constructor still accepted caller-selected `profile`, `role`, `actor_id`, and
  `authority_context`.
- GREEN: `1 passed`. A current replay on 2026-08-24 also returned `1 passed`.
- An expanded authority/checkpoint selection recorded `7 passed`; its literal selection
  was not retained, so that aggregate is not used as an exact-command release claim.

### 4.2 Ten semantic/coverage probes

The parameterized native-terminal node contributes two cases, so this command selects
ten tests exactly:

```bash
env -u HERMES_DELEGATED_CHILD_CONTEXT \
  UV_PROJECT_ENVIRONMENT=/tmp/aether-py311 \
  uv run --python 3.11 --frozen pytest -q \
  tests/test_observation_reducer.py::test_conflicting_repeated_event_id_is_a_reproducible_gap \
  tests/test_observation_reducer.py::test_duplicate_producer_sequence_is_not_turned_into_a_causal_edge \
  tests/test_observation_reducer.py::test_product_owned_exact_classification_survives_native_unknown_in_any_order \
  tests/test_observation_reducer.py::test_opaque_producer_epoch_cannot_decide_verification_freshness \
  tests/test_observation_cli_plugin.py::test_retained_binding_refuses_cross_producer_wall_clock_order \
  tests/test_observation_reducer.py::test_anomalous_terminal_without_retry_edge_does_not_create_redispatch_round \
  tests/test_observation_reducer.py::test_dispatch_without_declared_limits_degrades_coverage \
  tests/test_observation_cli_plugin.py::test_native_terminal_never_turns_explicit_non_success_into_done \
  tests/test_observation_reducer.py::test_protocol_violation_outcome_is_not_folded_away_as_generic_success
```

- RED: `10 failed`. The defects included silent event/sequence conflict handling,
  native unknown overwriting exact product classification, producer epoch deciding
  freshness, a cross-producer binding retained by wall-clock order, synthetic
  redispatch/rework, null limits treated as known, and failed/protocol outcomes folded.
- GREEN: `10 passed`. A current replay on 2026-08-24 returned `10 passed in 0.45s`.

### 4.3 Journal, storage, compaction, and SQLite TOCTOU

The focused storage cut recorded:

```text
RED:   5 failed, 146 deselected
GREEN: 9 passed, 142 deselected
```

The expanded storage file subsequently recorded:

```text
150 passed, 1 deselected
```

The historical `-k` expression/node list for the 5-to-9 aggregate was not retained in
the repository task log. The counts are kept as an implementation audit trail, but are
not promoted to an exact-command final gate. The exercised regressions are named in
`tests/test_observation_journal_storage.py`, including rotated `fsync` debt, atomic
event/derivation rollback and replay, valid-invalid-valid bulk ingest, durable projection
pointer replacement, stale compaction references, archive/source durability, and
cross-process transition fencing.

The SQLite name-swap test has an exact command:

```bash
env -u HERMES_DELEGATED_CHILD_CONTEXT \
  UV_PROJECT_ENVIRONMENT=/tmp/aether-py311 \
  uv run --python 3.11 --frozen pytest -q \
  tests/test_observation_journal_storage.py::test_read_model_rejects_db_symlink_swap_before_external_bytes_change
```

- Sabotage RED: the secure file-descriptor path was temporarily replaced by
  `sqlite3.connect(path)`; `1 failed` because `external.read_bytes() != before`.
- Restored GREEN: `1 passed`. A current replay returned `1 passed in 0.13s`.

### 4.4 Durable review assignment

The first durable-assignment slice used this exact command:

```bash
env -u HERMES_DELEGATED_CHILD_CONTEXT \
  UV_PROJECT_ENVIRONMENT=/tmp/aether-py311 \
  uv run --python 3.11 --frozen pytest -q \
  tests/test_observation_journal_storage.py::test_checkpoint_sink_derives_review_authority_from_durable_native_assignment
```

- Initial RED: `1 failed in 0.33s`; the checkpoint returned
  `CHECKPOINT_AUTHORITY_UNVERIFIED` because it did not consume durable assignment
  evidence.
- Initial GREEN: `1 passed in 0.36s` after resolving the reviewer from durable native
  assignment plus active product authority.
- Sabotage: temporarily restoring the pre-fix `checkpoint_principal` path returned
  `1 failed in 0.33s` with `CHECKPOINT_AUTHORITY_UNVERIFIED`; restoring the change
  returned GREEN.

An independent audit then found that the fixture itself supplied native
`relation="review"`, while the real Hermes adapter supplies `relation="unknown"` and
`required=null`. The fixture was hardened to record native identity/assignment first and
an exact product-owned `work_unit_classified` checkpoint second. That hardened cut first
returned this additional RED:

```text
1 failed in 0.34s
forged caller result: CHECKPOINT_AUTHORITY_UNVERIFIED
expected rejection class: CHECKPOINT_REFERENCE_UNKNOWN
```

The rejection class was corrected without accepting the forged caller. Two further
adversarials then exposed that a known native `relation="root"` or `required=false`
could be contradicted by a product classification as review/required. Their TDD record
is:

```text
RED:      2 failed in 0.49s; both contradictions were accepted
SABOTAGE: 2 failed in 0.37s after temporarily removing the native/product comparison
GREEN:    8 passed (positive path plus seven adversarials)
EXPANDED: 159 passed in 2.65s (contracts plus journal/storage)
```

The exact expanded focused command (the second node contributes seven parameter cases)
is:

```bash
env -u HERMES_DELEGATED_CHILD_CONTEXT \
  UV_PROJECT_ENVIRONMENT=/tmp/aether-py311 \
  uv run --python 3.11 --frozen pytest -q \
  tests/test_observation_journal_storage.py::test_checkpoint_sink_derives_review_authority_from_durable_native_assignment \
  tests/test_observation_journal_storage.py::test_checkpoint_sink_rejects_conflicting_durable_review_evidence
```

The fix permits product-owned classification to refine only native
`relation="unknown"` and `required=null`; any known native value must agree. A current
replay of the exact focal command above returned `1 passed in 0.27s`; the expanded
command returned `8 passed in 0.50s`. This resolves the known production-shape RED, but
focused GREEN still does not close #213 or #221 before the final suite and independent
final-diff review.

### 4.5 XDG split and content-free doctor

Historical RED command:

```bash
env -u HERMES_DELEGATED_CHILD_CONTEXT \
  UV_PROJECT_ENVIRONMENT=/tmp/aether-py311 \
  uv run --python 3.11 --frozen pytest -q \
  tests/test_observation_lifecycle.py::test_cli_lifecycle_separates_immutable_data_from_mutable_state \
  tests/test_observation_lifecycle.py::test_doctor_reports_only_content_free_observer_state_and_permission_health \
  tests/test_observation_lifecycle.py::test_doctor_inspects_projection_integrity_and_summary_coverage_without_content
```

- RED: `3 failed`: CLI rooted immutable releases in state instead of data,
  `ReleaseStore` did not accept a separate `state_root`, and doctor omitted projection
  integrity/summary coverage keys.
- After the fixes, an expanded selection recorded `5 passed in 0.79s`; that exact
  five-node literal was not retained.

Current reproducible GREEN command, including the executing-manager negative control:

```bash
env -u HERMES_DELEGATED_CHILD_CONTEXT \
  UV_PROJECT_ENVIRONMENT=/tmp/aether-py311 \
  uv run --python 3.11 --frozen pytest -q \
  tests/test_observation_lifecycle.py::test_cli_lifecycle_separates_immutable_data_from_mutable_state \
  tests/test_observation_lifecycle.py::test_doctor_reports_only_content_free_observer_state_and_permission_health \
  tests/test_observation_lifecycle.py::test_doctor_inspects_projection_integrity_and_summary_coverage_without_content \
  tests/test_observation_lifecycle.py::test_doctor_detects_manager_runtime_wheel_divergence_without_importing_hermes
```

Result on 2026-08-24: `4 passed in 0.87s`.

The manager negative-control node also has its own TDD/sabotage record:

- RED: `1 failed in 0.27s`; `/bin/false` did not produce
  `EXECUTING_MANAGER_INVALID`.
- GREEN: `1 passed in 0.42s` after doctor validated the executing manager independently
  of the managed Hermes runtime.
- Sabotage with the pre-fix path: `1 failed in 0.43s`.
- Restored: `1 passed in 0.42s`.

### 4.6 Discriminated empty/summary CLI state (#222)

The initial empty-state regression used the exact empty node:

```bash
env -u HERMES_DELEGATED_CHILD_CONTEXT \
  UV_PROJECT_ENVIRONMENT=/tmp/aether-py311 \
  uv run --python 3.11 --frozen pytest -q \
  tests/test_observation_cli_plugin.py::test_observe_empty_human_and_json_share_one_discriminated_representation
```

- RED: the JSON envelope returned `data={}` instead of the explicit empty variant.
- GREEN: the empty variant is exactly `{"state":"empty","summary":null}` and human
  output is rendered from that same state.
- Sabotage: temporarily restoring `data={}` made the regression fail; restoring the
  discriminated representation returned GREEN.

A second RED showed that an explicit nonexistent `REF` returned success/empty state.
After the minimal fix it returns the bounded `TRACE_NOT_FOUND` error. The current exact
seven-node replay covering summary, empty, single-open, ambiguous-open, all-closed,
missing-ref, and unresolved-project behavior returned `7 passed in 0.59s` on
2026-08-24.

### 4.7 Callback/journal non-intrusion under blocked durability

Independent reauditing found four paths that could inherit durability latency: an
authority snapshot waiting for the flusher lock, `pread` retaining that lock, an
ordinary append waiting behind `fsync`, and threshold rotation calling `fsync` directly
from `append`. A fifth regression showed that a rejected append then repeated the
bounded wait while trying to append its diagnostic.

The RED/sabotage observations were real: each of the first four exceeded the `0.5 s`
test boundary while its synthetic kernel operation remained blocked; the duplicate
diagnostic path took `0.203 s` against an isolated `0.16 s` limit. The minimal fix uses
bounded lock acquisition, copies a proven durable descriptor/inode state before reading
outside the lock, requests rotation from the callback, performs rotation in the
supervised flusher, and writes the content-free busy diagnostic nonblocking.

Current exact GREEN command:

```bash
env -u HERMES_DELEGATED_CHILD_CONTEXT \
  PYTHONDONTWRITEBYTECODE=1 \
  PYTHONPATH=/tmp/aether-hermes-v2026.8.18 \
  AETHER_EXACT_HERMES_CHECKOUT=/tmp/aether-hermes-v2026.8.18 \
  UV_PROJECT_ENVIRONMENT=/tmp/aether-py311 \
  uv run --python 3.11 --frozen pytest -q \
  tests/test_observation_journal_storage.py::test_threshold_rotation_never_runs_fsync_in_append \
  tests/test_observation_journal_storage.py::test_append_fails_open_while_flusher_holds_writer_lock \
  tests/test_observation_journal_storage.py::test_collector_busy_diagnostic_does_not_wait_for_writer_lock_twice \
  tests/test_observation_journal_storage.py::test_durable_snapshot_does_not_hold_writer_lock_during_pread \
  tests/test_observation_journal_storage.py::test_checkpoint_sink_fails_open_while_active_fsync_holds_writer_lock \
  tests/test_observation_journal_storage.py::test_deferred_rotation_keeps_critical_debt_when_rename_directory_fsync_fails
```

Result on 2026-08-24: `6 passed in 0.34s`. The subsequent independent core freeze
returned `288 passed in 4.49s`; see section 4.11 for its exact command and permutation
stress evidence.

### 4.8 Qualification runner claims are executed, not hard-coded

Regression tests first exposed twelve independent claim-validation defects, including
accepting a skipped PluginContext harness, reporting hard-coded hook/unload values
without requiring one executed harness pass, dropping subprocess evidence, using the
repository virtualenv instead of the executing interpreter for packaging, omitting API
callback latency, and not enforcing performance budgets. Two further RED tests showed
that the incremental runner could omit the normative 100,000-event point.

The focused implementation cycles recorded `12` RED then `12/12` GREEN, followed by
`2` RED then `6/6` GREEN for the exact incremental gate. A sabotage of the harness
acceptance path made all four skipped/omitted/multiple-outcome adversarials fail; the
restored implementation returned `4 passed`. The literal combined historical RED
selection was not retained, so those counts are an implementation ledger rather than a
final exact-command claim.

Current reproducible non-deep qualification command:

```bash
env -u HERMES_DELEGATED_CHILD_CONTEXT \
  PYTHONDONTWRITEBYTECODE=1 \
  PYTHONPATH=/tmp/aether-hermes-v2026.8.18 \
  AETHER_EXACT_HERMES_CHECKOUT=/tmp/aether-hermes-v2026.8.18 \
  UV_PROJECT_ENVIRONMENT=/tmp/aether-py311 \
  uv run --python 3.11 --frozen pytest -q \
  tests/test_observation_qualification.py \
  tests/test_observation_performance.py \
  tests/test_observation_packaging.py \
  -k 'not benchmark_cli_executes_100k'
```

Result on 2026-08-24: `27 passed, 1 deselected in 7.09s`. The deselected node is the
explicit deep 100k CLI runner and remains part of the final performance execution, not
waived evidence.

### 4.9 Identical pinned observer dependency in both environments

Exact regression node:

```bash
env -u HERMES_DELEGATED_CHILD_CONTEXT \
  UV_PROJECT_ENVIRONMENT=/tmp/aether-py311 \
  uv run --python 3.11 --frozen pytest -q \
  tests/test_observation_lifecycle.py::test_observer_dependencies_are_pinned_identically_for_manager_and_runtime
```

- RED: `1 failed in 0.31s`; `LifecycleManager` had no
  `_install_observer_dependencies`, so the manager could resolve a different
  `jsonschema` version from the runtime.
- GREEN: both environments install and verify `jsonschema==4.26.0` before the same
  Aether wheel is installed with `--no-deps`.
- Sabotage: replacing the helper with a no-op made the call assertion fail; restoration
  returned `1 passed`.

A current replay of this node plus the real dual-environment wheel preparation returned
`2 passed in 4.97s`.

### 4.10 Linear producer-sequence conflict detection

Profiling the real 10k retained-work-unit fixture found that `_sequence_gaps()` called
`list.count()` once per sequence. The TDD regression instruments integer equality
comparisons rather than relying only on a wall-clock threshold.

```bash
env -u HERMES_DELEGATED_CHILD_CONTEXT \
  UV_PROJECT_ENVIRONMENT=/tmp/aether-py311 \
  uv run --python 3.11 --frozen pytest -q \
  tests/test_observation_reducer.py::test_sequence_gap_detection_does_not_rescan_all_sequences_for_each_value
```

- RED: `128` sequences caused `16,256` equality comparisons against a linear upper
  bound of `512`.
- GREEN: one `Counter(sequences)` pass produced zero equality comparisons for distinct
  hashes while preserving sorted duplicate diagnostics.
- Sabotage: restoring `list.count()` reproduced `16,256` comparisons and failed the
  regression; restoring `Counter` returned GREEN.
- Equivalence: a fixture containing duplicate sequences and gaps produced identical
  canonical summary bytes and `summary_id`, including both
  `PRODUCER_SEQUENCE_CONFLICT` and `PRODUCER_SEQUENCE_GAP`.

Five post-fix 10k samples were `0.520–0.541 s`, all below the `2 s` contract budget.
A current replay of the complexity node plus the executable 10k budget node returned
`2 passed in 0.91s`.

### 4.11 Native-identity dedupe preserves explicit product evidence

The first reducer regression demonstrated that selecting one representative for two
otherwise equivalent native envelopes could discard the envelope named by an explicit
product-classification parent. A second slice exposed the corresponding persistence
defect: the unique SQLite native-identity index retained only two of three raw
envelopes, and duplicate derivation changed the aggregate action count instead of
retaining proof without applying a second semantic effect.

Exact focal command after the fixes:

```bash
env -u HERMES_DELEGATED_CHILD_CONTEXT \
  PYTHONDONTWRITEBYTECODE=1 \
  PYTHONPATH=/tmp/aether-hermes-v2026.8.18 \
  AETHER_EXACT_HERMES_CHECKOUT=/tmp/aether-hermes-v2026.8.18 \
  UV_PROJECT_ENVIRONMENT=/tmp/aether-py311 \
  uv run --python 3.11 --frozen pytest -q \
  tests/test_observation_reducer.py::test_native_dedupe_preserves_explicit_classification_parent_in_every_permutation \
  tests/test_observation_reducer.py::test_native_dedupe_preserves_every_explicit_parent_target \
  tests/test_observation_journal_storage.py::test_native_identity_index_migrates_and_rebuilds_as_non_unique \
  tests/test_observation_journal_storage.py::test_ingest_preserves_explicit_native_parent_target_in_every_permutation \
  tests/test_observation_journal_storage.py::test_read_model_preserves_two_explicit_duplicate_parent_targets
```

- RED: reducer dedupe discarded the explicitly referenced target; the read model
  inserted two rather than three raw envelopes, and a semantic duplicate inflated the
  action aggregate from two to three.
- GREEN: every raw envelope and `event_derivation` proof is retained, explicit parent
  targets survive all permutations, and only one canonical semantic effect is applied
  for an unreferenced duplicate.
- Sabotage: restoring representative-only dedupe and the unique native-identity index
  reproduced the target loss and incorrect raw/aggregate counts; restoring the fixes
  returned GREEN.

The final read-only core audit ran the complete contracts, journal/storage, and reducer
files with the same environment:

```bash
env -u HERMES_DELEGATED_CHILD_CONTEXT \
  PYTHONDONTWRITEBYTECODE=1 \
  PYTHONPATH=/tmp/aether-hermes-v2026.8.18 \
  AETHER_EXACT_HERMES_CHECKOUT=/tmp/aether-hermes-v2026.8.18 \
  UV_PROJECT_ENVIRONMENT=/tmp/aether-py311 \
  uv run --python 3.11 --frozen pytest -q \
  tests/test_observation_contracts.py \
  tests/test_observation_journal_storage.py \
  tests/test_observation_reducer.py
```

Result: `288 passed in 4.49s`. Independent permutation probes produced one stable
outcome for all `6/6` one-target orders and all `24/24` two-target orders; the
unique-to-non-unique migration and rebuild retained a non-unique index, raw proof, and
one semantic effect. Concurrent append/snapshot and flush/snapshot stress each completed
`80/80` iterations with zero unavailable results, failures, or deadlocks.

### 4.12 Reproducible build backend and executable same-wheel proof

The original package test installed the runtime wheel with `--no-deps` and inspected
distribution metadata only. It therefore passed even though the isolated runtime could
not import the observer because `jsonschema>=4.23` was absent. A separate regression
showed that the PEP 517 backend was declared as the open range `hatchling>=1.27` and was
not present in the development lock.

Exact focal commands:

```bash
env -u HERMES_DELEGATED_CHILD_CONTEXT \
  UV_PROJECT_ENVIRONMENT=/tmp/aether-py311 \
  uv run --python 3.11 --frozen pytest -q \
  tests/test_observation_packaging.py::test_same_wheel_installs_in_isolated_manager_and_runtime_without_path_shadowing

env -u HERMES_DELEGATED_CHILD_CONTEXT \
  UV_PROJECT_ENVIRONMENT=/tmp/aether-py311 \
  uv run --python 3.11 --frozen pytest -q \
  tests/test_observation_packaging.py::test_build_backend_is_exact_dev_only_and_locked
```

- Same-wheel RED: `1 failed`; `uv pip check` reported that `aether-agents` required
  `jsonschema>=4.23` but it was not installed in the runtime.
- Same-wheel GREEN: `1 passed in 2.05s`. Both disposable environments install the same
  wheel with dependencies, pass `uv pip check`, import the observer from their own
  `site-packages`, load the single real Hermes entry point, and expose callable
  `register` without source-tree shadowing.
- Same-wheel sabotage: restoring runtime `--no-deps` reproduced the failure; restoring
  the dependency-complete install returned GREEN.
- Backend RED: the test observed `hatchling>=1.27` rather than an exact locked backend.
  The build requirement and dev lock now select `hatchling==1.27.0`; sabotage restoring
  the range failed the regression and restoration returned GREEN.
- Expanded packaging result: `5 passed in 2.14s`; `uv lock --check`, compileall, Ruff
  lint/format, and `git diff --check` were GREEN at that implementation cut.

### 4.13 Benchmark artifact and committed baseline use one sample contract

The historical performance fixture recorded 960 API callbacks, 4,900 tool callbacks,
and 100 flush samples from an older harness, while the current qualification runner
executes 1,000 API callbacks, 1,000 tool callbacks, and 20 supervised flush samples.
The regression now requires the committed fixture to be the raw output shape emitted by
the current exact-Hermes benchmark, including its contract identity, separate tool/API
surfaces, real callback/unload/privacy values, and 10k/100k incremental pipeline.

Exact RED command:

```bash
env -u HERMES_DELEGATED_CHILD_CONTEXT \
  PYTHONDONTWRITEBYTECODE=1 \
  PYTHONPATH=/tmp/aether-hermes-v2026.8.18 \
  AETHER_EXACT_HERMES_CHECKOUT=/tmp/aether-hermes-v2026.8.18 \
  UV_PROJECT_ENVIRONMENT=/tmp/aether-py311 \
  uv run --python 3.11 --frozen pytest -q \
  tests/test_observation_performance.py::test_recorded_clean_checkout_scaling_evidence_is_complete
```

RED on 2026-08-24: `1 failed in 0.07s`, at `evidence["contract"]`, with
`KeyError: 'contract'`. This is the expected stale-baseline defect. GREEN is deliberately
deferred until the single final Python 3.11 deep benchmark has actually completed; its
temporary raw artifact will be inspected before the fixture bytes are updated. No
timing or GREEN result is claimed here yet.

### 4.14 Critical durability debt is retryable, confined, and idempotent

The first #216 fix retained old critical segment paths after a failed rotation/file or
directory `fsync`, but no code ever retried or removed that debt. A later healthy flush
therefore remained permanently false and the flusher could never acknowledge recovered
storage.

The three-test TDD selection initially returned `3 failed in 0.51s`: critical debt was
sticky after recovery, a partial active-to-closed rename had no retry path, and no second
file `fsync` occurred. The minimal implementation binds each obligation to the original
device/inode/size, accepts only closed-grammar active/closed candidates, reopens relative
to a directory descriptor with `O_NOFOLLOW`, rechecks identity before and after file
`fsync`, fsyncs both rename directories, and removes only the exact proven obligation.
Repeated failure or path replacement retains the debt. A damaged active tail is fsynced
but is never promoted, truncated, or deleted, so unclean-tail coverage remains visible.

- GREEN: four debt/tail regressions passed; the original three-test selection returned
  `3 passed in 0.40s`.
- Sabotage: temporarily disabling `_retry_critical_debt_locked()` returned `2 failed`
  with exit `1`; restoration returned GREEN.
- Expanded current cut: `86 passed in 3.34s` for the journal-focused selection and
  `292 passed in 4.74s` for contracts + journal/storage + reducer.
- Static cut: compileall, Ruff lint/format, and `git diff --check` were GREEN.

### 4.15 Causal round membership cannot come from presentation order

The previous round builder partitioned one total topological presentation by trigger
index and linked every adjacent partition through `previous_round_id`. Consequently an
independent direction-change event could move an unrelated run into a different round,
and two independent explicit roots could collapse into one round solely because their
timestamps happened to be adjacent.

The focused RED/GREEN selection was:

```bash
env -u HERMES_DELEGATED_CHILD_CONTEXT \
  UV_PROJECT_ENVIRONMENT=/tmp/aether-py311 \
  uv run --python 3.11 --frozen pytest -q \
  tests/test_observation_reducer.py \
  -k 'independent_direction_trigger or two_explicit_task_roots or explicit_trigger_edge_assigns'
```

- RED: `2 failed, 1 passed`. One independent run received the preceding direction
  round as `previous_round_id`, while two roots with no edge appeared in one round.
- GREEN: `3 passed`. Round seeds now use typed explicit triggers; membership comes only
  from durable task-parent edges, exact native `(task_ref, run_id)` spans, or explicit
  event parents; `previous_round_id` exists only for a proven predecessor.
- Sabotage: substituting the former index/boundary/adjacent-previous algorithm in memory
  returned exit `1` with the same `2 failed, 1 passed`; the working tree was restored
  before the GREEN run.
- Expanded current cut: `109 passed in 1.45s` for the reducer file. The implementing
  agent's contracts + journal/storage + reducer replay recorded `296 passed in 4.57s`.

The canonical summary golden was regenerated only after inspecting the semantic delta
and validating the complete summary. Its initial round still contains the same explicit
implementation and review spans and the same waves. Ten invariant checks, terminal
verification, and closure now have `round_id = null` because they have no parent-event,
task, or native-span edge into that round. Keeping them there by timestamp would violate
OBS-FR-052. No other semantic summary field changed apart from the content-addressed
`summary_id` implied by this correction.

### 4.16 A1 lifecycle release boundaries use retained locks and tracked Hermes bytes

The #221 audit found four independent release-boundary defects: a clean Git status did
not exclude ignored worktree bytes, the schema-3 lock was only partially validated and
was not retained, manager observer dependencies were resolved online without hashes,
and rollback used a historical record rather than the predecessor of the latest durable
activation. Tests were written before each implementation correction.

- Full-lock/schema RED:
  `pytest -q tests/test_a1_contracts.py::ReleaseLockSourceModeTests::test_source_tree_digest_is_required_and_artifact_paths_are_closed tests/test_observation_lifecycle.py::test_release_lock_loader_validates_the_complete_schema`
  returned `6 failed`: the source-tree digest was optional and malformed profile,
  artifact URL/path, and extra-field shapes could bypass the partial loader. Draft
  2020-12 validation plus exact A1/Hermes semantic checks returned GREEN. A later
  combined selection returned `17 passed, 3 subtests passed in 8.74s`.
- Observer-dependency RED returned three failures: the schema accepted a missing lock
  digest, lifecycle used an unbound online install, and the wheel contained no
  hash-bound closure. The candidate wheel now packages the exact tracked `uv.lock`
  runtime export; manager uses `uv pip sync --require-hashes --strict`, runtime applies
  the same closure after its independent Hermes lock, and manifest/doctor verify the
  retained bytes and digest. The packaging parity selection returned `2 passed in
  1.57s`; the complete packaging file returned `6 passed in 2.16s`.
- Tracked-source sabotage temporarily restored worktree copying. The regression failed
  with ignored `.env` and `hermes_agent.egg-info/PKG-INFO` as the two extra files.
  Restoring `git archive` extraction returned GREEN. Qualification separately
  materialized the exact checkout and proved its observed file set equals `git
  ls-tree`, excluding ignored egg-info and bytecode (`1 passed in 1.87s`).
- Dependency-lock sabotage bypassed wheel lock validation; the adversarial unhashed
  closure test failed with `DID NOT RAISE IntegrityError`. Restoring validation returned
  GREEN. Full-schema bypass sabotage similarly produced five `DID NOT RAISE` failures
  before restoration.
- Rollback sabotage restored the historical-predecessor behavior. The A→B→C→reactivate
  B regression failed because B pointed to A instead of C. Restoring the durable
  activation edge returned GREEN. Initial-install recovery also removes only Aether
  profile bytes when the recovered active pointer is `None`.

The public lifecycle lane used only
`/tmp/aether-qualification-hermes-v2026.8.18`, annotated tag `v2026.8.18`, tag object
`9f13bbbf8423427e159c78066356ca0e27ca6b74`, and commit
`e624e9fde561e1add9388384012b295fde669ade`. Its first real run correctly failed because
PEP 660 created `hermes_agent.egg-info` inside the authenticated tree. Lifecycle now
removes only that closed, regular setuptools build-debris directory after installation;
the venv's installed dist-info remains authoritative and the tracked tree digest is
rechecked. The restored exact test returned `1 passed in 42.66s`. The full lifecycle
file excluding only that exact-public node returned `53 passed, 1 deselected in
23.85s`. The real PluginContext harness independently returned `1 passed in 1.68s` and
measured 22 callbacks, tool/API capture, absent raw payloads, and zero hooks after
unload. These are intermediate implementation results; the final matrix below remains
pending after all concurrent changes settle.

### 4.17 Raw terminal evidence cannot preempt authority-checked reduction

The read-side projection formerly copied every raw `trace.cancelled`,
`trace.abandoned`, or `trace.failed` envelope directly into
`observation_trace.termination`. That let actor/profile/role strings supplied by an
implementer, or a Morfeo-shaped event with no coherent active-release authority,
remove the only trace from a no-REF query before the reducer could expose the authority
gap. The regression writes each outcome through the real journal, ingests it into
SQLite, resolves it through `query.resolve_trace(None)`, and then reduces it.

```bash
env -u HERMES_DELEGATED_CHILD_CONTEXT PYTHONDONTWRITEBYTECODE=1 \
  UV_PROJECT_ENVIRONMENT=/tmp/aether-py311 \
  uv run --python 3.11 --frozen pytest -q \
  tests/test_observation_journal_storage.py::test_raw_terminal_event_cannot_hide_trace_before_authoritative_reduction
```

- RED: `6 failed in 0.84s`; every case raised `NoOpenTraceError` from
  `resolve_trace(None)` because `_touch_trace()` had already asserted terminality.
- GREEN: `6 passed in 0.75s`. Raw trace indexing now remains `open`; only
  `record_summary()` mirrors the reducer's authority-checked termination. An
  unauthorized implementer and unavailable authority both reduce to `open` with
  `TERMINAL_AUTHORITY_UNVERIFIED`; unavailable authority also retains
  `AUTHORITY_CONTEXT_UNAVAILABLE`.
- Sabotage: temporarily restoring the three-event raw terminal map reproduced
  `6 failed in 0.83s` with the same `NoOpenTraceError` boundary. After restoring the
  implementation, the six-case node plus the no-REF CLI authority-unavailable
  regression returned `7 passed in 0.85s`.

### 4.18 Journal readers reject external links across ingest, compaction, and recovery

The prior discovery/read path used `Path.is_file()`, `Path.open()`, and `Path.read_bytes()`.
A valid external JSONL linked under a valid `journal/closed` name was therefore treated
as owned evidence. The regression creates the complete external native segment first,
then inserts either a symlink or hardlink into a different project's closed directory.

```bash
env -u HERMES_DELEGATED_CHILD_CONTEXT PYTHONDONTWRITEBYTECODE=1 \
  UV_PROJECT_ENVIRONMENT=/tmp/aether-py311 \
  uv run --python 3.11 --frozen pytest -q \
  tests/test_observation_journal_storage.py::test_ingest_rejects_linked_segment_outside_project_without_reading_it \
  tests/test_observation_journal_storage.py::test_compaction_rejects_linked_source_outside_project_without_touching_it
```

- RED: ingestion returned `events_inserted=2` for both link kinds (`2 failed in
  0.50s`), and compaction accepted and removed both local aliases (`2 failed in
  0.51s`).
- GREEN: the combined four cases returned `4 passed in 0.55s` (a restored replay
  returned `4 passed in 0.46s`). Directory enumeration and file reads now use
  directory descriptors, `O_NOFOLLOW`, nonblocking opens, regular-file checks,
  single-link ownership, and opened/named inode agreement. Gzip decompression wraps
  that same descriptor. Unsafe segments remain visible as corrupt without reaching
  SQLite.
- Recovery RED: a verified archive plus an external linked source raised
  `UnsafeObservationPath` instead of failing open (`2 failed in 0.65s`). Recovery now
  retains that local alias for manual review, reports zero completed deletions, and
  leaves external bytes unchanged (`2 passed in 0.66s`; restored replay `2 passed in
  0.45s`).
- Sabotage: temporarily restoring the former path-following reader produced `4 failed
  in 0.64s` for ingest/compaction and `2 failed in 0.54s` for recovery. Restoring the
  confined reader returned both selections to GREEN.

### 4.19 Retained bytes cannot bootstrap causal authority by existence

`_retained_binding_rows()` and `_retained_trace_exists()` formerly parsed enough JSON
fields to restore a task/trace without event-schema or privacy validation. A canonical
JSON line with a valid project/trace/epoch/sequence and native-looking source, but an
invalid event ID and no required event envelope, returned a root binding.

```bash
env -u HERMES_DELEGATED_CHILD_CONTEXT PYTHONDONTWRITEBYTECODE=1 \
  UV_PROJECT_ENVIRONMENT=/tmp/aether-py311 \
  uv run --python 3.11 --frozen pytest -q \
  tests/test_observation_cli_plugin.py::test_invalid_retained_line_cannot_bootstrap_trace_or_task_authority
```

- RED: `1 failed in 0.15s`; `_retained_binding()` returned the forged
  `(trace_id, "root")` tuple.
- GREEN: the exact node returned `1 passed in 0.28s`; together with the independent
  producer contradiction control it returned `2 passed in 0.30s`. Recovery now shares
  the confined segment reader, requires canonical JSON, schema validity, the structural
  privacy guard, exact project/producer/sequence agreement, native binding provenance,
  and a verified manifest for archives. Quarantine never restores authority.
- Sabotage: disabling schema plus structural privacy validation reproduced the forged
  binding (`1 failed in 0.16s`); restoring both gates returned `1 passed in 0.28s`.

### 4.20 Historical anomalies never become current liveness evidence

A first run that crashed and a second explicit attempt that completed left
`latest_run_outcome=completed` and `anomalies=clear`, but the total historical crash
counter still forced `liveness=stale`. That contradicted the summary's own current state
and inferred heartbeat recency from an unrelated dimension.

```bash
env -u HERMES_DELEGATED_CHILD_CONTEXT PYTHONDONTWRITEBYTECODE=1 \
  UV_PROJECT_ENVIRONMENT=/tmp/aether-py311 \
  uv run --python 3.11 --frozen pytest -q \
  tests/test_observation_reducer.py::test_recovered_run_anomaly_never_becomes_current_liveness_evidence
```

- RED: `1 failed in 0.47s`, `stale != unknown`.
- GREEN: the new node, every anomalous run outcome, and fresh/stale/unknown native
  heartbeat controls returned `9 passed in 0.50s`; the restored exact node returned
  `1 passed in 0.44s`. Historical outcomes remain in run totals while only current
  unresolved death or native heartbeat recency affects liveness.
- Sabotage: restoring the historical-total branch returned `1 failed in 0.46s` with
  the same contradiction; restoration returned GREEN.

### 4.21 Durable task-parent edges enter the process DAG only when unique

The reviewed fixture contains a durable `review.parent_task_refs=["impl"]` claim and
exactly one implementation attempt, but the process builder previously considered only
`parent_event_id`. The review therefore had no predecessor and the critical path omitted
its two seconds. Conversely, selecting one of multiple implementation attempts would
invent causality.

- RED command: the exact
  `test_unique_durable_parent_task_links_implementation_to_review_critical_path` node
  returned `1 failed in 0.49s`, with `[] != ["stp-0002"]`.
- GREEN: the unique durable edge produces `impl -> review`, critical duration `6000ms`,
  and `review_wait_ms=2000` (`1 passed in 0.44s`). A second regression proves two parent
  attempts select no predecessor. The complete reducer file returned `113 passed in
  1.68s`.
- Sabotage: omitting durable parents reproduced the original failure (`1 failed in
  0.48s`). Weakening cardinality to choose the first non-empty candidate made the
  ambiguous-attempt regression fail with an invented `stp-0001` predecessor (`1 failed
  in 0.36s`). Both changes were restored.
- The golden was changed only after inspecting five semantic deltas: critical duration
  `4000 -> 6000`, review wait `0 -> 2000`, critical step IDs add `stp-0003`, the review
  adds predecessor `stp-0002`, and the content-addressed summary ID changes to
  `sum_6ab3057941648d7acc9f6dd578d4d333185ac56e7ce9fd71ab0ffa371053112c`.

### 4.22 Native identity privacy is structural and precedes every Aether sink

Hermes SessionDB and provider identifiers are externally supplied opaque values; a
length-only `safe_ref()` cannot prove either provenance or absence of command/prompt/path
content. The new contract keeps exact native grammars only where Hermes owns a closed
one (Kanban `t_<8 hex>`, positive run ID, bounded profile). Session, turn, API request,
tool call, and approval identifiers are projected through a project-keyed HMAC and carry
the fingerprint-key epoch in `sid|trn|api|call|apr_fpk_<epoch>_<digest>` form.

- RED native-store case: the complete malicious Kanban/SessionDB payload in
  `test_native_reconciliation_rejects_content_shaped_identities_before_aether_persistence`
  failed because `PRIVATE_RUN_ERROR` reached the journal even though the old schema and
  guard accepted it.
- RED callback case: full public hook payloads retained raw supplied identifiers inside
  `_pending_spans` before any journal write. Projection now occurs before pending maps,
  retry correlation, queue, journal, SQLite, summary, or diagnostic emission. Native
  session references from reconciliation also require exact SessionDB corroboration
  before HMAC projection.
- The schema conditionals, projector, and `assert_clean()` recognize the same keyed
  pseudonym grammar across ordinary tool/model events, retries, subagents, approvals,
  and configuration/tool-surface blocks. Rejected diagnostics contain neither hostile
  bytes nor their directly correlatable SHA-256 digests. Product-owned logical refs such
  as `root` are not incorrectly treated as Hermes-native identifiers.
- GREEN: the adversarial reconciliation selection returned `2 passed in 1.19s`; the
  stabilized contracts + journal/storage + reducer + CLI selection returned `348 passed
  in 8.79s`, independently replayed by the lead as `348 passed in 8.73s` against Hermes
  commit `e624e9fde561e1add9388384012b295fde669ade`.
- Sabotage: restoring raw `return candidate`/`safe_ref` behavior made the callback
  pending-map assertion fail (`1 failed in 0.64s`); restoring keyed projection returned
  `1 passed in 0.60s`.

### 4.23 A missing pre-hook remains visible without breaking post-hook capture

The privacy refactor added `collector` to `_tool_metadata()` but three post-only
`kanban_create` branches still called the old signature. A successful or failed
`post_tool_call` with no preceding callback therefore raised `TypeError`, incremented
`callback_errors`, and lost its terminal evidence. After fixing the signature, the old
fallback would also have invented a `tool.started` event that Hermes never supplied.

- RED: the success/failure post-only regressions returned `2 failed in 0.74s`, both with
  missing `name` in `_tool_metadata()` and `callback_errors=1`.
- GREEN: all three calls now pass the collector, and a deferred start is emitted only
  when a real pending pre-hook exists. Both cases returned `2 passed in 0.58s`; success
  retains an unpaired terminal, reducer coverage gap, and strict-token durable binding,
  while failure retains terminal/gap without inventing a binding.
- Sabotage: reverting one call reproduced the success-path `TypeError` (`1 failed in
  0.62s`); restoration returned `2 passed in 0.57s`. The complete exact-Hermes CLI file
  then returned `37 passed in 3.76s`.

### 4.24 Atomic private writes never follow predictable temporary links

The fingerprint-key pointer, project registry, and content-free health counters each
created a predictable temporary name with `Path.write_text()` and hardened it only
afterwards. A pre-existing symlink at that name was therefore followed before the
confinement check. The keyring and registry overwrote external bytes; the health path
also propagated `UnsafeObservationPath` despite its documented never-raises boundary.

The same four-node command is used for the restored implementation; the RED cut
selected its three call-site nodes and omitted only the durability control:

```bash
env -u HERMES_DELEGATED_CHILD_CONTEXT PYTHONDONTWRITEBYTECODE=1 \
  PYTHONPATH=/tmp/aether-hermes-v2026.8.18 \
  AETHER_EXACT_HERMES_CHECKOUT=/tmp/aether-hermes-v2026.8.18 \
  UV_PROJECT_ENVIRONMENT=/tmp/aether-py311 \
  uv run --python 3.11 --frozen pytest -q \
  tests/test_observation_contracts.py::test_project_registry_temp_symlink_never_overwrites_external_file \
  tests/test_observation_contracts.py::test_health_counter_temp_symlink_is_fail_open_and_never_overwrites_external_file \
  tests/test_observation_contracts.py::test_fingerprint_pointer_temp_symlink_never_overwrites_external_file \
  tests/test_observation_contracts.py::test_atomic_private_write_fsyncs_file_and_directory_before_return
```

- RED: the three full call-site probes returned `3 failed in 0.25s`, after observing
  changed external bytes for key pointer and registry and an escaped exception for
  health accounting.
- GREEN: `atomic_private_write()` now creates through a verified directory descriptor
  with `O_EXCL|O_NOFOLLOW` and mode `0600`, writes every byte, performs file `fsync`,
  verifies the named/open inode and single-link state, replaces relative to the same
  directory descriptor, verifies the installed inode, performs directory `fsync`, and
  cleans up only the exact temporary inode it created. Registry and keyring use that
  primitive; health treats both I/O and confinement rejection as fail-open. The three
  adversarial nodes plus the file-before-directory durability node returned `4 passed
  in 0.32s`; the lead independently replayed them against exact Hermes in `0.19s`, and
  the independent reviewer replayed them in `0.20s`.
- Sabotage: replacing the shared primitive with the former `Path.write_text()` behavior
  returned `3 failed in 0.25s` with external-byte modification. Restoring it returned
  GREEN. The implementation agent's contracts-plus-journal replay returned `204 passed
  in 4.14s`; that focused aggregate does not replace the final matrix below.

Read-side alias confinement is being validated separately and is not claimed by this
write-side slice.

### 4.25 Work-graph conflicts invalidate only the authority they contradict

The reducer previously emitted coverage gaps for conflicting parentage, root bindings,
native run terminals, event IDs, and producer sequences but could still select one
graph description and return `completed`. That made the gap documentary rather than a
completion invariant. The regression permutes each conflict and also retains a
non-graph tool conflict control:

```bash
env -u HERMES_DELEGATED_CHILD_CONTEXT PYTHONDONTWRITEBYTECODE=1 \
  PYTHONPATH=/tmp/aether-hermes-v2026.8.18 \
  AETHER_EXACT_HERMES_CHECKOUT=/tmp/aether-hermes-v2026.8.18 \
  UV_PROJECT_ENVIRONMENT=/tmp/aether-py311 \
  uv run --python 3.11 --frozen pytest -q \
  tests/test_observation_reducer.py::test_conflicting_native_parentage_neutralizes_graph_authority_in_any_order \
  tests/test_observation_reducer.py::test_conflicting_root_bindings_neutralize_root_authority_in_any_order \
  tests/test_observation_reducer.py::test_conflicting_native_run_terminals_invalidate_graph_in_any_order \
  tests/test_observation_reducer.py::test_conflicting_run_event_id_retains_bounded_graph_ambiguity_in_any_order \
  tests/test_observation_reducer.py::test_producer_sequence_conflict_neutralizes_only_involved_work_status \
  tests/test_observation_reducer.py::test_non_graph_event_id_conflict_does_not_gate_settled_work_graph
```

- RED parent/binding/native-terminal: `3 failed in 0.53s`, all because the summary
  remained `completed`. GREEN was `3 passed in 0.41s`; temporarily restoring the
  first-fact behavior reproduced `3 failed in 0.52s`, and restoration returned
  `3 passed in 0.41s`.
- RED event-ID/producer-sequence: `2 failed in 0.47s`, again because graph completion
  survived an unresolved graph fact. The reconciler now retains bounded semantic
  conflict metadata when it must collapse a repeated event ID, and producer-sequence
  conflict metadata names only the involved graph-affecting work facts. GREEN was
  `2 passed in 0.40s`.
- The six-node adversarial/control command returned `6 passed in 0.53s`. Disabling the
  bounded conflict propagation made the two graph nodes fail while the tool-only
  control remained GREEN (`2 failed, 1 passed in 0.51s`); restoration returned the
  three-node selection to `3 passed in 0.44s`. The complete reducer file then returned
  `119 passed in 1.92s`; the lead independently replayed all six nodes in `0.48s`.

Conflicting parentage/root semantics are neutralized to unknown with no causal edge;
conflicting terminal state becomes unknown while both observed outcome totals remain.
This is deliberately not a global `coverage.complete` completion gate: an unrelated
tool/model conflict stays visible but does not alter an otherwise settled work graph.

### 4.26 Product-owned state readers reject external aliases before authority use

Several product-state readers still used `Path.read_text()`/`read_bytes()` after a
separate existence or symlink check. Complete, valid-looking external bytes could then
govern the project registry, key epoch, prior-summary comparison, projection high-water
fence, active-release authority, release/transition recovery, or the ownership proof
used before purge. Hard links bypassed symlink-only checks, and name swaps between check
and read reproduced the same problem.

```bash
env -u HERMES_DELEGATED_CHILD_CONTEXT PYTHONDONTWRITEBYTECODE=1 \
  PYTHONPATH=/tmp/aether-hermes-v2026.8.18 \
  AETHER_EXACT_HERMES_CHECKOUT=/tmp/aether-hermes-v2026.8.18 \
  UV_PROJECT_ENVIRONMENT=/tmp/aether-py311 \
  uv run --python 3.11 --frozen pytest -q \
  tests/test_observation_contracts.py::test_registry_and_health_reads_reject_external_state_aliases \
  tests/test_observation_contracts.py::test_fingerprint_pointer_read_rejects_external_alias_and_starts_lost_epoch \
  tests/test_observation_contracts.py::test_fingerprint_key_read_rejects_external_alias_and_rotates_lost_epoch \
  tests/test_observation_contracts.py::test_previous_summary_read_rejects_external_alias \
  tests/test_observation_journal_storage.py::test_projection_pointer_swap_after_hardening_cannot_govern_version_fence \
  tests/test_observation_lifecycle.py::test_active_pointer_swap_after_symlink_check_cannot_grant_release_authority \
  tests/test_observation_lifecycle.py::test_release_record_swap_after_release_path_check_is_rejected \
  tests/test_observation_lifecycle.py::test_transition_swap_after_symlink_check_cannot_govern_recovery \
  tests/test_observation_lifecycle.py::test_purge_refuses_ownership_marker_swapped_after_symlink_check
```

- RED: the four parameterized observation nodes plus projection returned `9 failed in
  1.01s`; the four lifecycle authority/recovery/purge swaps returned `4 failed in
  0.40s`.
- GREEN: `read_private_bytes()` opens through a verified directory descriptor with
  `O_NOFOLLOW|O_NONBLOCK`, requires a singly linked regular file, and revalidates
  opened/named device+inode and link count before and after the complete read. Callers
  fail closed, fail open, or rotate a lost key according to their existing API rather
  than accepting aliased bytes. The combined selection returned `13 passed in 0.88s`,
  independently replayed by the lead with the exact public Hermes source in the same
  `0.88s`.
- Sabotage: replacing the primitive with `path.read_bytes()` produced `11 failed,
  2 passed in 1.23s`; the two surviving symlink cases were already stopped by an
  earlier closed-path check, while every hard-link and name-swap probe killed the
  mutant. The sabotage was removed.
- Expanded validation returned `213 passed in 4.15s` for contracts+journal/storage and
  `76 passed, 3 subtests passed in 62.58s` for A1 contracts+lifecycle. That expanded
  replay found one missing explicit directory `fsync` after projection-pointer publish
  (`1 failed, 212 passed`); restoring the barrier made the fsync/swap focal selection
  `3 passed` and produced the final aggregates above.

### 4.27 JSON watch cannot silently change the one-envelope CLI contract

`aether observe --watch --json` formerly emitted one complete JSON object for every
change. That output was valid line by line but contradicted the stable A1 rule that
`--json` emits exactly one object; neither CLI contract declared NDJSON.

```bash
env -u HERMES_DELEGATED_CHILD_CONTEXT PYTHONDONTWRITEBYTECODE=1 \
  PYTHONPATH=/tmp/aether-hermes-v2026.8.18 \
  AETHER_EXACT_HERMES_CHECKOUT=/tmp/aether-hermes-v2026.8.18 \
  UV_PROJECT_ENVIRONMENT=/tmp/aether-py311 \
  uv run --python 3.11 --frozen pytest -q \
  tests/test_observation_cli_plugin.py::test_observe_rejects_watch_json_in_one_stable_json_envelope
```

- RED: `1 failed in 0.62s`; two watched summaries produced exit `0` instead of the
  single invalid-input envelope.
- GREEN: the mutually exclusive combination now returns exit `2` and exactly one
  `WATCH_JSON_UNSUPPORTED` envelope (`1 passed in 0.48s`). The human watch surface is
  unchanged; ordinary JSON still uses exactly the `empty|summary` discriminated union.
- Sabotage: temporarily removing the early guard reproduced `1 failed in 0.62s` with
  exit `0`; restoration returned `1 passed in 0.49s`. Both the A1 CLI contract and the
  002 public-interface section now state the incompatibility explicitly.

### 4.28 Observer dependency validation evaluates lock markers per target Python

The packaged hash-bound lock correctly marks `typing-extensions==4.16.0` for Python
versions below 3.13. A real temporary Python 3.13 sync therefore installed five
effective distributions and omitted it, while lifecycle validation iterated an
unconditional six-distribution map. The release would fail only on the supported 3.13
lane despite having applied its lock correctly.

```bash
env -u HERMES_DELEGATED_CHILD_CONTEXT PYTHONDONTWRITEBYTECODE=1 \
  UV_PROJECT_ENVIRONMENT=/tmp/aether-py311 \
  uv run --python 3.11 --frozen pytest -q \
  tests/test_observation_lifecycle.py::test_observer_dependency_markers_define_the_effective_python_closure
```

- RED: `1 failed in 0.36s` because no marker-aware effective-closure function existed.
- GREEN: prepare and validate now query the target environment's major/minor version
  and require only the hash-locked entries whose closed marker applies. The pure 3.12
  versus 3.13 regression returned `1 passed in 0.29s`; a restored replay returned
  `1 passed in 0.25s`.
- Sabotage: forcing the 3.13 closure back to all six distributions returned `1 failed
  in 0.31s`; restoration returned GREEN. A direct target-interpreter probe subsequently
  reported Python `3.13.15` and an effective closure of five distributions with
  `typing-extensions` absent.

### 4.29 Public manager authority and lifecycle dispatch are release-bound (#221)

The public `uv` wrapper formerly had no product-owned proof that a stateful command was
being executed by the active manager release. The completed slice authenticates the
active record, no-follow wheel bytes and digest, packaged/installed identity,
compatibility tuple, and manager marker before dispatching the mutation to the exact
active release interpreter. Python/uv/pip environment overrides are scrubbed at that
boundary, and the release-local CLI refuses stale-manager or recursive dispatch.

The regression set covers a different wheel with the same version, profile validation
TOCTOU, absence as a doctor integrity error, and the disposable public lifecycle:

```bash
env -u HERMES_DELEGATED_CHILD_CONTEXT PYTHONDONTWRITEBYTECODE=1 \
  UV_PROJECT_ENVIRONMENT=/tmp/aether-py311 \
  uv run --python 3.11 --frozen pytest -q \
  tests/test_observation_lifecycle.py::test_non_active_manager_cannot_mutate_with_a_different_wheel_or_same_version \
  tests/test_observation_lifecycle.py::test_profile_activation_validation_rejects_check_then_symlink_swap \
  tests/test_observation_lifecycle.py::test_cli_doctor_absence_is_integrity_error_not_protected_gate \
  tests/test_observation_lifecycle.py::test_disposable_public_install_capture_query_update_rollback_uninstall_purge
```

- Authority/doctor RED was `2 failed in 5.05s`; the disposable public path returned
  `1 passed in 15.43s` after the active-manager boundary was implemented, and the
  adversarial manager/doctor selection returned `3 passed in 0.27s`.
- Restoring the former unbound dispatch made the manager-authority sabotage fail
  (`1 failed in 0.35s`); restoration returned `2 passed in 0.15s`.
- Profile activation had its own `1 failed in 0.34s` RED, `1 passed in 0.14s` GREEN,
  and `1 failed in 0.19s` sabotage when the separate check/read race was restored.
- The lead independently replayed the four-node command above: `4 passed in 15.40s`.
  The non-exact lifecycle file returned `61 passed, 1 deselected in 26.91s`, the exact
  lifecycle node returned `1 passed in 38.55s`, CLI returned `38 passed in 3.72s`, and
  packaging returned `6 passed in 2.14s` at that implementation cut.

This is focused evidence. The same-wheel final lifecycle matrix and exact public
lifecycle rerun after all source changes remain in section 6.

### 4.30 State-root ancestor replacement is rejected at the retained descriptor (#219)

The earlier link hardening protected the final filename but still opened some parent
paths through ambient resolution. A verified project leaf could therefore be reached
through a replaced state-root ancestor. The shared private reader/writer, journal
listing/reads, and SQLite connection now walk components with directory descriptors and
`O_NOFOLLOW`, retain the verified parent descriptor through the operation, and revalidate
the named parent before accepting the boundary.

```bash
env -u HERMES_DELEGATED_CHILD_CONTEXT PYTHONDONTWRITEBYTECODE=1 \
  UV_PROJECT_ENVIRONMENT=/tmp/aether-py311 \
  uv run --python 3.11 --frozen pytest -q \
  tests/test_observation_contracts.py::test_registry_read_rejects_symlinked_state_ancestor \
  tests/test_observation_contracts.py::test_registry_write_rejects_state_ancestor_swapped_after_directory_check \
  tests/test_observation_journal_storage.py::test_journal_listing_and_read_reject_symlinked_state_ancestor \
  tests/test_observation_journal_storage.py::test_read_model_rejects_projection_ancestor_swap_before_external_bytes_change
```

- Private read RED was `1 failed in 0.28s`; the alias selection became `3 passed in
  0.21s`, while restoring the direct reader produced `1 failed in 0.24s`.
- Private write RED was `1 failed in 0.22s`; the focal selection became `4 passed in
  0.22s`, and the old parent open reproduced `1 failed in 0.23s`.
- Journal listing/read RED was `1 failed in 0.45s`; the linked ingest/compaction
  selection returned `5 passed in 0.53s` (restored replay `0.47s`). Separate listing
  and read sabotages returned `1 failed in 0.45s` and `1 failed in 0.49s`.
- SQLite RED was `1 failed in 0.38s` and observed changed external DB bytes. The
  new/existing/sidecar/link selection returned `5 passed in 0.35s` (restored replay
  `0.36s`); disabling parent revalidation reproduced `1 failed in 0.37s` and external
  byte drift.
- The complete contracts file returned `121 passed in 0.80s` after the subsequent
  native-provenance slice. Contracts plus journal/storage returned `232 passed in
  4.57s` after the storage transaction work in section 4.33.

No live XDG state, profile, service, or user installation was used by these tests.

### 4.31 Conflicting authority and heartbeat facts stay non-positive (#213/#214/#215)

Six related reducer holes were closed as bounded semantic slices:

1. conflicting parent claims no longer merge independent roots into one round;
2. non-success trace terminals require the event-type-specific status;
3. evidence added to an already-passed acceptance criterion is a semantic delta and
   invalidates an earlier verification;
4. a native status identity excludes its disposition, so incompatible terminal
   outcomes at the same native coordinates conflict rather than evade reconciliation;
5. an event-ID conflict touching an authority-bearing fact cannot select an authorized
   representative and retain positive authority;
6. the first native running heartbeat updates liveness but not verified progress or an
   invented execution-start timestamp. Rejected review/completion attempts remain
   visible process steps with `outcome=unverified`, null semantic delta, and partial
   coverage rather than exact approvals/verifications.

The final four-finding command was:

```bash
env -u HERMES_DELEGATED_CHILD_CONTEXT PYTHONDONTWRITEBYTECODE=1 \
  UV_PROJECT_ENVIRONMENT=/tmp/aether-py311 \
  uv run --python 3.11 --frozen pytest -q tests/test_observation_reducer.py \
  -k 'first_native_heartbeat_snapshot or unassigned_review_attempt or same_native_status_coordinates or completion_event_id_conflict'
```

- RED was `4 failed, 124 deselected in 0.68s`: progress was `verified`, the review step
  was exact `approved`, no native-terminal gap existed, and the conflicting completion
  remained `completed`.
- GREEN was `4 passed, 124 deselected in 0.50s`.
- The combined sabotage restored all four defective decisions and returned `4 failed,
  124 deselected in 0.74s`; restoration returned GREEN.
- A separate process-projection RED showed an implementer verification as exact
  `verified` (`1 failed in 0.53s`). GREEN for forged completion, event-ID conflict, and
  unassigned review was `3 passed in 0.54s`; disabling the verified-event projection
  returned `1 failed in 0.55s`.
- A later conflicting assignee formerly revoked the work-graph approval but left the
  process step exact. That RED was `1 failed in 0.48s`; final-state authority
  reconciliation plus valid-golden/unassigned controls returned `3 passed in 0.62s`.
  Disabling final reconciliation reproduced `1 failed in 0.51s`.
- The conflicting-round RED was one merged round (`1 failed in 0.40s`); the relevant
  four-node GREEN was `4 passed in 0.52s`, and restoring raw parent claims reproduced
  `1 failed in 0.40s`.
- Terminal schema/reducer RED was `6 failed in 0.86s`; the valid and adversarial cases
  returned `9 passed in 0.62s`. Reducer and schema sabotages independently returned
  `3 failed in 0.61s` and `3 failed in 0.41s`.
- Acceptance evidence freshness RED was `1 failed in 0.55s`; the combined acceptance /
  terminal selection returned `8 passed in 0.67s`, and restoring state-only comparison
  reproduced `1 failed in 0.54s`.
- After restoration, the complete reducer file returned `128 passed in 2.05s`; Ruff
  lint/format was GREEN.

The benchmark fixture initially copied one identical native status timestamp many
times. Correct reconciliation reduced that synthetic stream to two facts, revealing an
invalid scale workload rather than a reducer defect. Both stress generators now assign
a distinct native observation timestamp per event:

- RED: qualification 1k and performance 10k returned `2 failed in 1.48s`, each observing
  `source_event_count=2`.
- GREEN: both retained their requested event counts and returned `2 passed in 1.16s`.
- Restoring the duplicated native coordinate reproduced the same `2 failed in 1.48s`;
  the distinct-fact generator was restored and returned GREEN.

The committed performance artifact remains intentionally untouched until the complete
10k/100k exact-checkout benchmark is executed in the final matrix.

### 4.32 Native reconciliation without verifiable provenance fails before persistence (#218)

The native privacy grammar was previously activated only when both `source_kind` and a
recognized `source_hook` were present. A full `native_reconciliation` event could set
`source_hook=null` and pass UUID-like raw session/turn/request identities through the
generic opaque-reference validator. The schema and runtime guard now fail closed unless
native reconciliation names one recognized public source hook; the existing native
pseudonym grammar then applies unchanged.

```bash
env -u HERMES_DELEGATED_CHILD_CONTEXT PYTHONDONTWRITEBYTECODE=1 \
  PYTHONPATH=src:tests UV_PROJECT_ENVIRONMENT=/tmp/aether-py311 \
  uv run --python 3.11 --frozen pytest -q tests/test_observation_contracts.py \
  -k 'native_reconciliation_without_verifiable_source'
```

- RED: `2 failed, 119 deselected`; both schema and `assert_clean()` accepted the full
  hostile event.
- GREEN: `2 passed, 119 deselected`; rejection uses the content-free reason
  `INVALID_NATIVE_SOURCE_PROVENANCE`.
- Removing both barriers reproduced the same two failures; restoration returned
  `2 passed` and the complete contracts file returned `121 passed in 0.80s`.
- Against clean exact Hermes `e624e9fde561e1add9388384012b295fde669ade`, the malicious
  reconciliation plus out-of-band reconciliation selection returned `2 passed, 143
  deselected`. A real journal append reported `accepted=False`, the reason above, and
  `persisted_files=[]`.

An initial plugin invocation without the exact checkout on `PYTHONPATH` failed honestly
with `ModuleNotFoundError: hermes_cli`; it was not counted as evidence. The corrected
exact-checkout invocation is the result recorded above.

### 4.33 Projection rebuild and replay have a real transactional boundary (#217)

Rebuild formerly deleted the live DB/WAL/SHM before candidate creation, admitted a
concurrent reader into an empty database, and left a durable pointer naming a missing
file when candidate connect failed. A successful replay also left its transient
`EVENT_DERIVATION_FAILED` diagnostic permanently active.

`ReadModel` now builds a private randomized candidate, applies DDL and
`integrity_check`, file-fsyncs it, upgrades a shared reader lease, checkpoints the old
WAL, atomically renames the candidate, directory-fsyncs, and only then reopens the
winner. Connect/DDL/rename failures retain the old projection and pointer. Owned stale
temps are cleaned idempotently; unknown names remain. Ordinary `open()` cannot publish a
pointer. `publish_projection(expected_active=...)` and compensating
`unpublish_projection(expected_active=...)` are lock/CAS operations, and a successful
single-event replay clears only the matching transient derivation diagnostic.

- Replay plus candidate connect/DDL RED: `3 failed in 0.61s`.
- Pointer/CAS/fsync/reader-coordination RED: `3 failed in 0.54s`.
- Atomic-rename retry RED: `1 failed in 0.61s`; stale-temp recovery RED: `1 failed in
  0.42s`; publish compensation RED: `2 failed in 0.53s`.
- Restoring the three primary defects returned `3 failed in 0.40s`; the rename sabotage
  independently returned `1 failed in 0.35s`.
- Restored focal GREEN was `7 passed in 0.53s`. The lead independently replayed the
  replay/pointer/rebuild/update-rollback selection as `6 passed, 105 deselected in
  0.55s`.
- The complete journal/storage file returned `111 passed in 4.15s`; contracts plus
  journal/storage returned `232 passed in 4.57s`; Ruff lint/format was GREEN.

The API itself is not represented as lifecycle integration evidence. At this point an
`rg` audit found no production call site outside tests; update/rollback/re-update
selection is therefore being validated separately before the final lifecycle matrix.

## 5. Schema source and package parity

There is one editable normative schema source:

```text
specs/002-aether-contract-observation/contracts/observation-event.schema.json
specs/002-aether-contract-observation/contracts/observation-summary.schema.json
specs/002-aether-contract-observation/contracts/observation-segment-manifest.schema.json
```

There is no second editable root `contracts/` tree and no checked-in package-resource
copy. Hatch `force-include` maps those exact files into
`aether_agents/resources/schemas/` in the wheel; the sdist includes the normative source
directory. `tests/test_observation_packaging.py::test_wheel_and_sdist_schemas_are_exact_normative_bytes`
compares source, wheel, and sdist bytes directly. A read-only snapshot build observed
byte equality, but the working tree continued to change afterwards, so final artifact
and schema digests are deliberately not reused here.

The distinct A1 `release-lock.schema.json` is likewise force-included from its canonical
001 contract path and byte-compared across source, wheel, and sdist; it does not become
a fourth observation schema or an editable 002 copy.

```text
PENDING_FINAL_EVENT_SCHEMA_SHA256
PENDING_FINAL_SUMMARY_SCHEMA_SHA256
PENDING_FINAL_SEGMENT_MANIFEST_SCHEMA_SHA256
PENDING_FINAL_SCHEMA_SOURCE_WHEEL_SDIST_PARITY
```

## 6. Final validation matrix

Focused results above are implementation evidence, not the required final matrix.

| Gate | Final evidence |
|---|---|
| Python 3.11 full frozen suite | `PENDING_FINAL_PY311_TEST_RESULT` |
| Python 3.12 full frozen suite | `PENDING_FINAL_PY312_TEST_RESULT` |
| Python 3.13 full frozen suite | `PENDING_FINAL_PY313_TEST_RESULT` |
| Exact Hermes core test count (minimum 119) | `PENDING_FINAL_EXACT_HERMES_TEST_COUNT` |
| Real `PluginContext` callback count/unload | `PENDING_FINAL_EXACT_PLUGIN_22_AND_UNLOAD_0` |
| `git diff --check` for the final repository diff | `PENDING_FINAL_GIT_DIFF_CHECK` |
| `python -m compileall -q src tests` | `PENDING_FINAL_COMPILEALL` |
| `ruff check` configured scope | `PENDING_FINAL_RUFF_CHECK` |
| `ruff format --check` configured scope | `PENDING_FINAL_RUFF_FORMAT_CHECK` |
| Wheel build/hash | `PENDING_FINAL_WHEEL_SHA256` |
| Sdist build/hash | `PENDING_FINAL_SDIST_SHA256` |
| 10,000-event real reduction | `PENDING_FINAL_PERFORMANCE_10K` |
| 100,000-event real reduction | `PENDING_FINAL_PERFORMANCE_100K` |
| Real callback p95/p99 | `PENDING_FINAL_CALLBACK_P95_P99` |
| Same-wheel install/doctor/update/rollback/re-update/uninstall matrix | `PENDING_FINAL_PACKAGE_LIFECYCLE_MATRIX` |
| Exact public lifecycle after final code changes | `PENDING_FINAL_EXACT_PUBLIC_LIFECYCLE` |

A focused independent lifecycle audit did exercise a real built wheel against the exact
public checkout, real `PluginContext`, 22 callbacks, zero hooks after unload, content-free
doctor, read-model/summary inspection, manager/runtime divergence, and `/bin/false`.
Its focused selection recorded `4 passed in 34.24s`. Because later source/test changes
occurred, that run is intermediate evidence and does not replace any
`PENDING_FINAL_*` row.

## 7. Git and GitHub state

```text
branch: feat/002-contract-observation
base HEAD: 47e26c5884d906aeb9790937910ec4a7bb67c3ed
implementation commits: PENDING_FINAL_COMMIT_LIST
PR: PENDING_FINAL_PR_URL
CI: PENDING_FINAL_CI_STATUS
independent final diff review: PENDING_FINAL_INDEPENDENT_REVIEW
```

The working tree contains preserved pre-existing changes and the observation
implementation is not represented by the base HEAD. No force-push, destructive rebase,
live profile/service mutation, publication, or protected provider effect is claimed by
this report.

## 8. Risks, exclusions, and the external gate

- The product-shaped durable-review regression in section 4.4 is now GREEN after two
  successive adversarial refinements. Its final full-matrix and independent final-diff
  review remain pending.
- The final three-Python matrix, static gates, artifact hashes, performance runs,
  lifecycle matrix, commits, PR, and real CI status are explicitly pending above.
- The local schema-3 release record does not replace the final canonical A1 release-lock
  instance and external artifact provenance.
- The PEP 660 Hermes installation is confined to a copied, digest-bound release-local
  source tree. Review must preserve that exact fact and decide it against the A1 source
  contract; it must not silently describe it as an ordinary upstream wheel.
- No dashboard/API, separate read-only agent tool, automatic pruning, productivity
  score, or Hermes core patch was added to the 1.0 observation surface.
- Liveness, activity, verified progress, waiting, anomalies, and termination remain
  separate; heartbeat does not prove progress; unknown/unavailable does not become a
  positive claim.

Issue #195 remains an owner-approved external gate. The controlled real three-role flow
using the exact public candidate and a public Hermes-supported provider has **not** been
executed. Local exact-checkout, synthetic callback, SQLite, package, and lifecycle tests
are not that trace. Until #195 is executed and its evidence independently reviewed,
Aether must not be described as complete, release-ready, production-ready, or ready for
stable publication.
