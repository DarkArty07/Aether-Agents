# MON-02 Implementation Evidence — read-only sources and hourly collector

**Unit:** MON-02
**Task:** `t_e4840003`
**Objective Contract:** `oc_f8c9fc9320587cf3@v1`
**Decomposition:** `8399978d47757d7d10aaa756a779b4eb812938ee`
**Accepted prerequisite:** MON-01 reviewed commit `cfbab930727c2e68fb6a0391088e77918b712edd`
**Candidate implementation tree:** the final local MON-02 commit is recorded in the
Supervisor handoff metadata; this evidence is portable and contains no machine-local
runtime state.

## Scope and changed paths

Only the MON-02-owned paths are changed:

- `src/aether_agents/monitor/sources.py`
- `src/aether_agents/monitor/collector.py`
- `tests/test_telegram_monitor_sources.py`
- `specs/telegram-monitor/evidence/MON-02.md`

MON-01 state/models/store files remain unchanged after the accepted prerequisite. No
reporting, delivery, runtime, CLI, plugin, packaging, policy, profile, SOUL, Objective
Contract, native Hermes, source database, or live installation files were modified.
The new non-`specs/` path inventory for MON-06 is the two source modules and the focused
source test module.

## Implemented behavior

- Enumerates only registry entries whose portable marker, registered path, and exact
  non-archived native Hermes Project primary path agree. Colliding display names do not
  establish identity; portable project UUID and native Project ID remain separate.
- Reads canonical execution-board metadata and requires the canonical board slug,
  portable Aether project, exact native Hermes Project ID, exact project-root
  `default_workdir`, Objective Contract ID/version, and a readable finalized contract
  with exact `created_in_session`/`finalized_in_session` provenance. Missing or conflicting
  native ID/path metadata fails closed with a coverage gap. Every supplied contract ID or
  version alias must corroborate the others, and a present `board.json` slug must match
  the enumerated canonical slug. Supports the native metadata keys `aether_project_id`,
  `aether_contract_id`, and `aether_contract_version`.
- Opens existing projects, board, and SessionDB SQLite files through `mode=ro` URIs,
  asserts `PRAGMA query_only=ON`, validates a singly-linked non-aliased source file, and
  selects explicit bounded columns. No native mutator, migration, materialization, or
  source write is called.
- Normalizes pipeline task/run/event state into project/contract/origin work items,
  including queued, review, triage, blocked, running, stale/failure diagnostics and
  bounded reported result/run summaries. The task's creator session is validated as
  project-bound evidence but does not replace the finalized contract's exact authored
  origin session; the exact finalized session is separately required, non-reporter and
  project-bound. Optional worker-session/affinity evidence is validated separately.
  Conflicted exact native session IDs are removed from the catalog, so dependent origin,
  finalizer, creator, worker and direct records fail closed rather than using an arbitrary
  SessionDB row. Reporter sessions are excluded. A root task completing without the exact
  terminal-affinity flow remains `waiting` with a visible `TERMINAL_CLOSURE_UNRESOLVED`
  gap rather than being treated as closed.
- Reconciles task runs/events after persisted per-board run/event cursors and uses the
  prior cutoff as a bounded timestamp fallback. First enable suppresses completed
  history that predates enrollment while retaining already-open work; persisted
  snapshot watermarks and work-item markers survive collector restart. A terminal
  identity first observed between cuts remains reportable until its final delivery
  marker is present, then the returned source cut becomes genuinely idle.
- Normalizes direct project-bound turn intervals as `turn_ended_*` with explicit
  no-contract identity and `PROJECT_ACCEPTANCE_NOT_OBSERVED`; both native project ID and
  exact project root are required, and the chosen SessionDB session paths must bind to
  that project. Continuation intervals remain distinct. Exact reporter-source sessions
  are excluded.
- Applies selected-source privacy bounds before facts cross the adapter: prose is bounded,
  path/URI/email/phone/credential/transcript-shaped values are rejected, and unsafe
  source fields produce coverage diagnostics rather than being silently passed through.
- Reads optional explicitly bound observation summaries as status/diagnostic codes only;
  raw observation content is not copied.
- Builds deterministic `aether.telegram-monitor.snapshot.v1` payloads with exact report,
  cutoff, collection, previous-cutoff, project/origin/optional-contract identities,
  observed states, evidence refs, bounded evidence facts and coverage gaps. Compaction
  removes prose before identity and retains every active work identity; an impossible
  identity bound fails closed with `SnapshotBoundsError`.
- Reconciles through the accepted MON-01 store: durable source watermarks, work items,
  collection lease, immutable snapshot and monotonic cutoff. Collector has no model,
  Telegram, scheduler, or network path.

## Requirement-to-evidence mapping

| Obligation | Check executed | Observed result |
| --- | --- | --- |
| Exact registered/marker/native Project identity and colliding names | `test_project_and_board_identity_is_exact_and_root_done_is_not_closure`; `test_two_bound_projects_with_colliding_names_are_kept_separate`; `test_same_project_multiple_contracts_and_origins_stay_distinct` | Exact UUID/path/native IDs attributed two concurrent projects and two contracts in one project independently; same display name did not merge them. |
| Final contract, authored/finalized sessions, and exact origin/contract/version correlation | `test_contract_origin_and_finalizer_are_distinct_verified_sessions`; `test_finalized_contract_session_must_be_present_nonreporter_and_project_bound`; `test_contract_origin_creator_and_worker_sessions_are_separately_bound`; `test_conflicted_session_ids_are_not_used_for_pipeline_or_direct_resolution`; `test_conflicted_creator_or_worker_session_is_not_used` | The finalized contract's authored origin remains the report header while a distinct finalized session is required to exist, be non-reporter and project-bound; Supervisor creator and worker sessions remain separate evidence; conflicting IDs fail closed for each dependent resolution. |
| Canonical board native project/path binding | `test_board_requires_canonical_native_project_id_and_root_path` | Missing/conflicting native Hermes Project ID or `default_workdir` fails closed with a visible gap and never reports the item. |
| Consistent board contract aliases and canonical slug | `test_board_contract_aliases_and_metadata_slug_must_agree` | Conflicting contract ID/version aliases and a metadata slug that disagrees with the enumerated board slug produce coverage gaps and no source item. |
| Review/root-vs-terminal lifecycle | `test_project_and_board_identity_is_exact_and_root_done_is_not_closure`; `test_root_done_without_terminal_affinity_is_not_closed`; `test_task_lifecycle_states_and_stale_failure_diagnostics` | Review, queued, triage, blocked, stale/running, failure and authoritative terminal states remain visible; root-only completion remains `waiting` with `TERMINAL_CLOSURE_UNRESOLVED`. |
| Direct no-contract, exact binding, continuation and reporter exclusion | `test_direct_turn_ended_without_contract_and_reporter_are_normalized`; `test_direct_work_requires_exact_native_project_and_session_binding`; `test_direct_continuation_intervals_remain_distinct_and_no_contract`; `test_direct_previous_cutoff_filters_old_intervals_but_keeps_continuations` | Direct intervals are distinct `turn_ended_*` identities with no contract, project acceptance remains unobserved, missing/conflicting native binding wakes with a gap, old completed intervals are cut, continuations remain, and cron reporter input is excluded. |
| Strict SQLite read-only opening and source preservation | `test_read_only_open_fails_closed_and_does_not_change_source`; `test_collector_persists_snapshot_and_preserves_all_native_sources` | Query-only mutation fails; source bytes, inode, size and mtime remained unchanged for projects, SessionDB and board databases. Symlink open fails closed. |
| Malformed/unsafe source is visible, not idle | `test_malformed_native_project_and_marker_is_a_coverage_gap_not_idle`; `test_sensitive_result_is_dropped_and_wakes_with_coverage_gap` | Invalid marker and source canary yield coverage gaps, no unsafe text enters the normalized item, and `SourceCollection.idle` is false. |
| Snapshot shape, deterministic bounded compaction and identity retention | `test_snapshot_compaction_is_deterministic_and_retains_each_identity`; collector assertion in `test_collector_persists_snapshot_and_preserves_all_native_sources` | Reversed input order produced the same bounded payload; all 100 work identities remained; payload stayed within 24,000 encoded characters/bytes under the tested bound. Impossible identity size raises `SnapshotBoundsError`. |
| First-enable suppression, between-cut final retention, durable watermarks and genuine idle | `test_first_enable_suppresses_completed_history`; `test_between_cut_final_is_reported_once_then_persisted_watermark_is_idle` | Completed history before first enable is omitted; a newly completed flow is reported once across a collector restart using persisted run/event cursors, old run facts are not replayed, and a confirmed final produces an empty idle cut. |
| Accepted MON-01 store integration and monotonic watermark | `test_collector_persists_snapshot_and_preserves_all_native_sources`; `tests/test_telegram_monitor_state.py` | 52 combined MON-01/MON-02 tests passed; collector persisted the canonical snapshot and advanced the accepted store cutoff without touching sources. |

## Verification record

Commands were run in the assigned worktree with the locked `uv` environment:

- `env -i PATH="$PATH" HOME="$HOME" UV_CACHE_DIR="$HOME/.cache/uv" uv run --frozen pytest -q tests/test_telegram_monitor_sources.py` → **39 passed**; this clean-environment form removes all inherited variables, including every `HERMES_KANBAN_*` variable.
- `env -i PATH="$PATH" HOME="$HOME" UV_CACHE_DIR="$HOME/.cache/uv" uv run --frozen pytest -q tests/test_telegram_monitor_sources.py tests/test_telegram_monitor_state.py` → **59 passed**.
- `uv run --frozen ruff check src/aether_agents/monitor tests/test_telegram_monitor_sources.py` → **All checks passed**.
- `uv run --frozen ruff format --check src/aether_agents/monitor tests/test_telegram_monitor_sources.py` → **6 files already formatted**.
- `uv run --frozen mypy src/aether_agents/monitor` → **Success: no issues found in 5 source files**. The command emitted only the existing unused optional-module override note.
- `uv run --frozen python -m compileall -q src/aether_agents/monitor tests/test_telegram_monitor_sources.py` → **passed**.
- `git diff --check` and staged `git diff --cached --check` → **passed**.

The full-repository command
`env -i PATH="$PATH" HOME="$HOME" UV_CACHE_DIR="$HOME/.cache/uv" uv run --frozen pytest -q`
was also attempted; collection stopped before MON-02 execution because the pre-existing
`tests/test_same_card_phase_predicates.py` import requires unavailable `hermes_cli`
(`ModuleNotFoundError`). The focused MON-01/MON-02 controls above completed successfully.

No live model, Telegram transport, profile/job activation, source mutation, credential
operation, dependency/lockfile change, publication, push, PR, merge, or issue mutation
was run. Full-repository integration and live qualification remain Supervisor-owned.

## Compatibility and residual risk

**Unit compatibility impact: `none` for existing Aether behavior; additive monitor source
and collector modules only.** The unit consumes the accepted MON-01 private store/model
interfaces and does not alter them. Downstream MON-04/MON-05 must independently review
source identity, collector scheduling, delivery/reporting integration, and native runtime
lifecycle.

Residual risk is limited to native runtime schema variation outside the exercised
fixtures, exact observation projection selection during integration, and integrated
source-to-report lifecycle. Unsafe or ambiguous source variation fails closed as a
coverage gap rather than being treated as idle or guessed identity.
