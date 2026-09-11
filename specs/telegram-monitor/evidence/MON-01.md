# MON-01 Implementation Evidence — Telegram monitor state foundation

**Unit:** MON-01
**Task:** `t_f5ee60bc`
**Objective Contract:** `oc_f8c9fc9320587cf3@v1`
**Base commit:** `da7bcef5854763bf5b70a5540f707722c158dfbb`
**Candidate implementation tree SHA (before evidence file):** `87c089c00daec95301c7bfbd83c8a81f5ba1bfd5`
**Status:** Implemented and self-verified; ready for same-card Supervisor review.

## Scope and changed paths

Only the assigned MON-01 paths are changed:

- `src/aether_agents/monitor/__init__.py`
- `src/aether_agents/monitor/models.py`
- `src/aether_agents/monitor/store.py`
- `tests/test_telegram_monitor_state.py`
- `specs/telegram-monitor/evidence/MON-01.md`

The new non-`specs/` path inventory for MON-06 is the three monitor source files and
`tests/test_telegram_monitor_state.py`. No existing source adapter, reporting, delivery,
runtime, CLI, plugin entry point, profile resource, policy manifest, Objective Contract,
source database, Hermes checkout, or live profile was modified.

## Implemented behavior

- Private monitor SQLite state at `<Aether state_root>/monitor/monitor.sqlite3`, using
  the existing owner-only directory/file primitives and descriptor-based POSIX opening.
  Symlink, traversal, non-regular-file, and hard-link database attacks are rejected;
  database and SQLite sidecars are hardened to 0600.
- Frozen data records for settings, work enrollment, immutable snapshots, narratives,
  per-part outbox deliveries, and transactional leases. JSON is canonicalized and bounded;
  snapshot payload digests and delivery text hashes are persisted.
- Stable work identity, unique report/cutoff and report/part keys, and SQLite triggers
  prevent direct mutation of immutable identity/content columns.
- Short `BEGIN IMMEDIATE` transactions claim collection/delivery leases and commit before
  a caller performs model/network work. Delivery claims fence duplicate senders; the
  persisted enabled flag is checked after a claim and before dispatch.
- Leases persist owner PID and recover expired or dead-owner `sending` records as
  `uncertain`; ambiguous delivery is not automatically replayed. Receipts require the
  original lease token and a positive message ID for `confirmed`.
- Manual off is persisted by `set_enabled(False)` before a caller pauses native scheduling;
  off survives a new `MonitorStore` instance and suppresses a claimed delivery in the
  off race.
- Explicit snapshot resolution supports idle/no-part intervals. Retention uses the
  resolution timestamp, retains pending/failed/uncertain deliveries and active or
  unreported work, and purges only resolved history after the configured 30-day window.
- The store never receives or opens a source SessionDB, Kanban DB, observation DB, or
  source path.

## Requirement-to-evidence mapping

| Obligation | Check executed | Observed result |
| --- | --- | --- |
| Private path and privacy controls | `test_store_uses_private_contained_path_and_hardens_existing_database`; `test_store_rejects_traversal_symlink_and_hard_linked_database` | Owner-only modes and safe path rejection passed. |
| Settings, enrollment, watermarks, restart persistence | `test_settings_off_is_durable_and_configuration_is_private`; `test_work_item_identity_is_immutable_but_observed_state_and_watermark_change`; `test_narrative_outbox_and_watermark_survive_restart` | State and cursors survived restart; off remained false. |
| Immutable and unique record identity | `test_snapshot_ids_and_cutoffs_are_unique_and_payload_is_immutable`; direct SQLite trigger checks for snapshots, work items, and deliveries | Duplicate report/cutoff and identity/content mutations were rejected. |
| Collection/send duplicate fencing | `test_collection_lease_fences_duplicate_workers`; `test_stale_collection_lease_cannot_commit_and_current_owner_can`; `test_delivery_lease_fences_concurrent_senders_and_allows_writes_during_slow_call` | Exactly one concurrent collection/delivery claimant succeeded; expired/replaced collector lease was rejected with LeaseLostError while current owner committed successfully; disabled store rejected commit under manual-off. |
| Timestamp precision and fractional ordering | `test_utc_timestamp_normalization_and_fractional_ordering_boundaries` | Normalized ISO-8601 UTC text (microsecond precision) and parsed instants correctly advanced cutoff from whole to fractional seconds, rejected backwards movements, validated previous cutoff preceding snapshot cutoff, and preserved fractional TTL (0.5s) eligibility and expiry. |
| No transaction held across external work | `test_delivery_lease_fences_concurrent_senders_and_allows_writes_during_slow_call` | A settings write completed while a fake slow external call was blocked after the lease transaction. |
| Manual-off race | `test_manual_off_is_rechecked_after_lease_before_dispatch` | Dispatch became ineligible and the claimed part was suppressed after persisted off. |
| Crash/restart uncertainty and dead-owner recovery | `test_restart_recovers_expired_sending_as_uncertain_and_does_not_retry_blindly`; `test_restart_recovers_sending_from_dead_owner_before_lease_expiry`; `test_expired_lease_cannot_commit_a_late_receipt` | Sending became `uncertain`; late receipt was fenced; dead-owner state recovered without waiting for TTL. |
| Resolution and bounded retention | `test_snapshot_resolution_is_explicit_and_rejects_unresolved_parts`; `test_stale_resolved_history_is_purged_but_pending_uncertain_and_work_survive`; `test_old_completed_work_is_bounded_but_active_or_unreported_work_is_retained`; `test_failed_delivery_remains_unresolved_for_later_retry_and_retention` | Only resolved records aged beyond 30 days were purgeable; active, pending, failed, uncertain, and unreported attribution remained. |
| Source preservation | `test_source_database_is_not_opened_or_modified` | Source bytes, inode, size, mtime, schema, and row remained unchanged. |

## Verification record

All commands were run in the assigned worktree with the locked `uv` environment.

- RED before implementation: `uv run --frozen pytest -q tests/test_telegram_monitor_state.py`
  failed during collection because the new `aether_agents.monitor` package did not yet
  exist (`ModuleNotFoundError`).
- GREEN focused suite: `uv run --frozen pytest -q tests/test_telegram_monitor_state.py`
  → **20 passed in 0.17s** (includes regression tests for transactional collection lease fencing, stale collector commit rejection, current owner commit, manual-off preservation, and fractional timestamp/TTL boundary conditions).
- Owned lint: `uv run --frozen ruff check src/aether_agents/monitor tests/test_telegram_monitor_state.py`
  → **All checks passed**.
- Owned format: `uv run --frozen ruff format --check src/aether_agents/monitor tests/test_telegram_monitor_state.py`
  → **4 files already formatted**.
- Owned type check: `uv run --frozen mypy src/aether_agents/monitor`
  → **Success: no issues found in 3 source files**. The command emitted only the existing
  pyproject override note for optional modules.
- Owned bytecode check: `uv run --frozen python -m compileall -q src/aether_agents/monitor tests/test_telegram_monitor_state.py`
  → **passed**.
- Whitespace check: `git diff --check` and staged `git diff --cached --check` → **passed**.
- Full repository compile: `uv run --frozen python -m compileall -q src tests` → **passed**.

The full repository pytest command was attempted as required:
`uv run --frozen pytest -q` stopped during collection before candidate tests because
`tests/test_same_card_phase_predicates.py` imports unavailable `hermes_cli`
(`ModuleNotFoundError`). Full-repository `ruff check src tests` and
`ruff format --check src tests` also report pre-existing diagnostics/format drift in
unowned files (`src/aether_agents/knowledge/semantic.py`,
`src/aether_agents/objective_contracts/hermes_plugin.py`,
`tests/test_knowledge_regressions.py`, and `tests/test_objective_contracts.py`). These
files were not changed by MON-01 and were not fixed within this bounded unit.

No live model, Telegram transport, profile/job activation, source mutation, credential
operation, dependency change, publication, push, PR, merge, or issue mutation was run.

## Compatibility and residual risk

**Unit compatibility impact: `none`.** This is a new monitor-owned package and focused
state test surface; existing imports and runtime behavior are unchanged. Downstream MON-02,
MON-04, and MON-05 must review and consume these private interfaces before integration.

Remaining risk is limited to integrated callers selecting the correct source identities,
native transport, and runtime lifecycle; those are explicitly owned by later units and
were not simulated here. Independent Supervisor review and integrated qualification remain
outstanding.
