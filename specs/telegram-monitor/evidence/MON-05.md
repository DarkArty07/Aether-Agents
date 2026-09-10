# MON-05 Implementation Evidence — native runtime, controls and packaging

**Unit:** MON-05
**Task:** `t_8608f340`
**Objective Contract:** `oc_f8c9fc9320587cf3@v1` (SHA-256 `0de5f55efe6844174efd8abf9f72f492c6d36981af42bb730fb34ce8774c9d24`)
**Base commit:** `fbf0b1d922b8e72943f3a6e99620520dc8d9f9d9` (reviewed MON-01..MON-04 replay; see "Base reconstruction")
**Candidate implementation tree SHA (before this evidence file):** `447bc4793391573e04f49a9f964a5b7cb8b5d4b0`
**Status:** self-verified; ready for same-card Supervisor review.

## Scope and changed paths

Only the assigned MON-05 paths are changed:

- `src/aether_agents/monitor/service.py` (new)
- `src/aether_agents/monitor/runtime.py` (new)
- `src/aether_agents/monitor/hermes_plugin.py` (new)
- `src/aether_agents/monitor/commands.py` (new)
- `src/aether_agents/resources/monitor/precheck.py` (new)
- `src/aether_agents/cli.py` (monitor command family only)
- `pyproject.toml` (one entry point)
- `src/aether_agents/resources/profiles/morfeo/config.yaml` (monitor opt-in only)
- `tests/test_telegram_monitor_runtime.py` (new)
- `tests/test_telegram_monitor_cli_plugin.py` (new)
- `tests/test_observation_packaging.py` (fourth entry point, packaged resources, monitor help)
- `tests/test_public_artifacts.py` (fourth entry point)
- `specs/telegram-monitor/evidence/MON-05.md` (this file)

**New non-`specs/` path inventory for MON-06 (complete):**

```text
src/aether_agents/monitor/service.py
src/aether_agents/monitor/runtime.py
src/aether_agents/monitor/hermes_plugin.py
src/aether_agents/monitor/commands.py
src/aether_agents/resources/monitor/precheck.py
tests/test_telegram_monitor_runtime.py
tests/test_telegram_monitor_cli_plugin.py
```

No Supervisor/Implementer profile config, SOUL/home/runtime file, accepted MON-01..MON-04
file, `docs/`, `.github/workflows/policy.yml`, native Hermes file, lockfile, source database
or Objective Contract was modified. No dependency or lockfile change was made.

## Base reconstruction

The parent handoffs reference reviewed candidates on other branches with different SHAs
(MON-02 `55334be6fb0d187fef341689775e929a8a286b56`, MON-04 `d908c033d139e9dfeddfedf4461f85b40faedadc`).
This branch carries a replay of the accepted MON-01..MON-04 work. Blob-level equality was
verified before implementing, e.g.:

```text
src/aether_agents/monitor/collector.py  MON-02 4f1780f0304643b695bc53dca17911f9e20792dd  HEAD 4f1780f0304643b695bc53dca17911f9e20792dd
src/aether_agents/monitor/sources.py    MON-02 59a516cf5e40e604509597ee2cb87507938d7f0c  HEAD 59a516cf5e40e604509597ee2cb87507938d7f0c
src/aether_agents/monitor/delivery.py   MON-04 bd627828d7db2df1821a0b371bba2c99f6ba5170  HEAD bd627828d7db2df1821a0b371bba2c99f6ba5170
tests/test_telegram_monitor_sources.py  MON-02 2aefcf1fef2166af6b21b311c4a1fa4fa2226276  HEAD 2aefcf1fef2166af6b21b311c4a1fa4fa2226276
tests/test_telegram_monitor_delivery.py MON-04 bfbcb71fce8e30bd0264b447812a88fdf3f46f64  HEAD bfbcb71fce8e30bd0264b447812a88fdf3f46f64
```

## Native interface inspection (fail-preflight basis)

The release-locked fixture and the actually imported maintained runtime were both inspected
before relying on cron/plugin/hook/toolset/sender behavior:

| Interface | Observed release-locked fact (`v2026.8.18` @ `e624e9f`) | Observed imported maintained runtime |
| --- | --- | --- |
| Wake gate | `cron/scheduler.py:3742 _parse_wake_gate`: last non-empty stdout line, `{"wakeAgent": false}` skips the agent | same helper present |
| Agent-backed job with script | `cron/scheduler.py:4874-4896`: pre-check runs first and `wakeAgent=false` returns before `_build_job_prompt`/`AIAgent` | same branch |
| Cron session identity | `cron/scheduler.py:4928`: `cron_<job_id>_<timestamp>`, `platform="cron"` (`:5582`) | same construction |
| Plugin hooks | `hermes_cli/plugins.py:156 VALID_HOOKS` contains `post_tool_call`, `post_llm_call`, `on_session_end` | same membership |
| Hook payloads | `post_tool_call` carries `tool_name/session_id/turn_id` (`model_tools.py:1136`); `post_llm_call` fires on successful non-interrupted turns with `assistant_response/platform/turn_id` (`agent/turn_finalizer.py:615`); `on_session_end` carries `completed/failed/interrupted/platform/turn_id` (`:813`) | same payload shapes |
| Job creation | `cron/jobs.py:1780 create_job(prompt, schedule, ..., script, enabled_toolsets, no_agent, attach_to_session, monitor_script, monitor_url)` | same signature |
| Script location | `_run_job_script` resolves relative paths under `<HERMES_HOME>/scripts` and runs `.py` with the runtime interpreter | same resolution |
| Plugin toolsets | `toolsets.validate_toolset` accepts plugin-registered toolset names from `tools.registry` | same |
| Telegram home target | `gateway.config.load_gateway_config().get_home_channel(Platform.TELEGRAM)` (also used by MON-04) | same |

No material mismatch was found, so implementation proceeded against the release-locked
fixture. The imported maintained runtime is a private local checkout and was inspected
read-only; no Hermes file was modified and no Hermes patch is proposed.

## Implemented behavior

- **One owned job.** `HermesRuntime.ensure_job` installs the packaged
  `resources/monitor/precheck.py` verbatim under `<HERMES_HOME>/scripts/aether_monitor_precheck.py`
  and creates or adopts exactly one job with `schedule=0 * * * *`, `no_agent=False`,
  `script=aether_monitor_precheck.py`, `deliver=local`, `attach_to_session=False`,
  `enabled_toolsets=["aether_monitor_reporting"]`, no `monitor_script`/`monitor_url`, no
  `origin`/`model`/`provider`. The persisted job id is the runtime authority: a second `on`
  reuses it, and a job whose name is claimed by a different id (or two candidates) fails
  closed as `JOB_CONFLICT`. A persisted id whose job drifted is repaired through
  `update_job` to the same fixed shape (including clearing monitor suppression fields);
  unrelated jobs are never listed as owned, updated, paused or resumed.
- **Manual off is durable and ordered.** `MonitorService._off` commits `enabled=false`
  before pausing the exact persisted job; a racing pre-check re-reads the switch and stops
  without inference, and a racing send re-checks `enabled` before every attempt (MON-04
  adapter). Restart/agent activity cannot re-enable the monitor: `on` is the only writer.
- **Destination pin.** `on` resolves only the existing configured Telegram home chat/thread
  through the native gateway configuration and persists an opaque
  `telegram-home-<sha256>` reference. Missing, invalid or changed target fails closed
  (`DESTINATION_MISSING`/`DESTINATION_INVALID`/`DESTINATION_CHANGED`) without credential
  acquisition, job creation, or any fallback recipient; a different profile fails as
  `RUNTIME_MISMATCH`. No destination value is persisted in `settings` or printed.
- **Deterministic pre-check and wake gate.** `run_precheck` validates enabled state, the
  owned job binding, and the native hook/scheduling interface readiness
  (`_module_problems`), then recovers state, then either recovers an unfinished report or
  collects one hourly cut. Genuine idle emits `{"wakeAgent": false}` before inference and
  resolves the idle report; ongoing work, an unreported final outcome, a source failure,
  a runtime mismatch or a pre-check crash emit `{"wakeAgent": true}` and never look idle.
  A late tick resolves to the local wall-clock hour it belongs to; a repeat tick inside the
  same hour is suppressed only when the cut is already collected or a live narration owns
  it.
- **Bounded recovery.** A report that was collected but never narrated (process death or
  callback failure) is re-surfaced by the next pre-check with its own bounded context and
  the narration lease, so a pending report cannot be silently lost behind a newer cut.
  Reports whose parts never confirmed are retried through the transport only (never a model
  call), and a failed/rejected narration is re-sent as the single fixed labeled service
  notice per report cut.
- **Reporter recognition.** A reporter is exactly a native cron session whose id starts with
  `cron_<persisted job id>_`, on platform `cron`, for the bound profile, with the pending
  narration lease present and the report unresolved. `post_llm_call` validates the narrative
  against the canonical snapshot and persists `accepted`/`rejected`; `on_session_end`
  renders and delivers only for that exact session, releases the narration state, and
  sends only the labeled service notice when narration failed. Any other hook path only
  records source evidence and never sends.
- **Direct Morfeo work.** `post_tool_call` enrolls a project-bound turn only when the exact
  native session exists and its recorded workdir matches a marker-verified registered
  project (portable id + native project id); `post_llm_call` attaches a bounded reported
  summary; `on_session_end` marks the interval `completed`/`failed`/`interrupted`/`unknown`.
  A continuation opens a new interval, reporter/cron sessions and monitor-control calls are
  excluded, and the bounded spool is pruned by age and count.
- **CLI and tool parity.** `aether monitor status|on|off|history` with `--json` on every
  action and `history --limit N`; the native `aether_monitor` tool exposes the same four
  actions and limit in ordinary Morfeo sessions and refuses control from monitor runs.
  Both go through one `MonitorService`, so schema `aether.telegram-monitor.v1`, `ok`,
  `action`, `result`/`error` cannot drift. Malformed actions, extra arguments and invalid
  limits fail closed (`INVALID_ARGUMENT`/`INVALID_LIMIT`, argparse exit 2).
- **Hermes-free manager boundary.** The parser/help path imports no Hermes module; when the
  manager interpreter lacks Hermes, control actions run through a validated
  product-runtime subprocess (`AETHER_HERMES_PYTHON`, else a `hermes`-sibling interpreter,
  else the manager interpreter; each candidate must import `cron.jobs`,
  `hermes_cli.plugins` and the monitor runtime). Only a fully validated envelope for the
  requested action is accepted; anything else (non-JSON, wrong schema, wrong action,
  crash) fails closed. `status`/`history` still read durable state without Hermes;
  `on`/`off` report `RUNTIME_UNAVAILABLE` and change nothing.
- **Restricted reporter toolset.** The plugin registers exactly two tools:
  `aether_monitor` in `aether_monitor` and `aether_monitor_report_snapshot` in the dedicated
  `aether_monitor_reporting` toolset. Registration is Morfeo-only and opt-in. Against the
  release-locked registry the reporter toolset resolves to exactly one tool and the control
  toolset to exactly one tool, so the hourly job's `enabled_toolsets` cannot default-expand
  to terminal/file/messaging/board/delegation/cron/control tools. The MORFEO profile is the
  only profile config that enables the plugin (`language: Spanish`); Supervisor and
  Implementer configs are untouched.
- **Packaging.** One new entry point `aether-telegram-monitor = aether_agents.monitor.hermes_plugin`
  (four total), the packaged pre-check and narration context ship in the wheel byte-equal to
  source, and the monitor help path still works with a deliberately broken Hermes import.

## Requirement-to-evidence mapping

| Obligation (TM/D/AC/plan) | Check executed | Observed result |
| --- | --- | --- |
| TM-005/D1/D2: one native hourly job, `0 * * * *`, ordinary agent job, packaged pre-check, `deliver=local`, no monitor suppression | `test_exact_hermes_interfaces_hooks_toolset_and_owned_cron_job` (`hermes_exact`, real `cron.jobs.create_job` kwargs captured) | Session id `cron_<job-id>_<timestamp>` and `platform="cron"` confirmed in the release-locked scheduler; job created with `schedule="0 * * * *"`, `script="aether_monitor_precheck.py"`, `deliver="local"`, `no_agent=False`, `attach_to_session=False`, `enabled_toolsets=["aether_monitor_reporting"]`, no monitor/origin/model fields; script installed byte-equal to the packaged resource. |
| AC-1: idempotent `on`, no duplicate job | `test_on_is_idempotent_and_reuses_the_single_owned_job`; `test_exact_hermes_interfaces_...` (second `ensure_job` must not call `create_job`) | First `on` created, second reused: exactly one `create_job` call, stable job id, one native job. |
| AC-1/D5: `off` persists before pausing; unrelated jobs untouched | `test_off_persists_disabled_before_pausing_the_exact_job`; `test_exact_hermes_interfaces_...` | Recorded event order `enabled:False` before `pause:<job-id>`; only the owned id paused/resumed; an unrelated job's JSON bytes were identical before and after the on/off cycle. |
| AC-1: repeated `on` after restart/activity stays off | `test_off_persists_disabled_before_pausing_the_exact_job` (status after restart) | Status reported `enabled: false`; only `on` writes enablement. |
| AC-1: missing/changed/ambiguous destination fails without credential request | `test_on_fails_closed_on_missing_or_changed_destination`; `test_on_rejects_a_different_profile_or_changed_pin` | `DESTINATION_MISSING`, `DESTINATION_CHANGED`, `RUNTIME_MISMATCH`; no job call, no pin persisted, enablement unchanged. |
| AC-2/D2: hourly wall-clock cuts, late ticks visible, DST, repeat suppression | `test_precheck_uses_the_local_wall_clock_hour_and_suppresses_a_repeat_tick`; `test_next_hour_boundary_is_always_a_future_wall_clock_hour`; `test_hour_boundary_follows_the_wall_clock_across_a_dst_fold`; `test_precheck_collection_and_gate_stay_well_inside_the_start_bound` | Late 12:59:30 tick produced the 12:00 local cutoff record and `wakeAgent:true`; a repeat tick with a live narration collected nothing; a resolved same-hour tick reported `already-collected`; across the `Europe/Madrid` fold both instants resolved to the same local wall-clock hour with differing explicit offsets and monotonic UTC cutoffs; deterministic pre-check work stayed far below the 120 s start bound. |
| AC-2/D4/D8: idle is silent, source failure wakes, no unreported loss | `test_precheck_idle_resolves_the_report_and_skips_inference`; `test_precheck_source_failure_wakes_instead_of_looking_idle`; `test_precheck_runtime_mismatch_is_observable_and_never_idle`; `test_precheck_resumes_an_unfinished_report_instead_of_collecting_again`; `test_precheck_waits_while_a_live_narration_owns_the_report` | Idle emitted `{"reason":"idle","wakeAgent":false}` before any inference and resolved the report; collection error, pre-check error and runtime mismatch emitted `wakeAgent:true`; an un-narrated prior report was re-surfaced with its bounded context and lease instead of a second cut; a live narration produced no duplicate narration and no second collection. |
| AC-2/AC-6: bounded transport retry without extra narration | `test_precheck_retries_unconfirmed_parts_without_rerunning_the_narrator` | A failed part was re-rendered from the accepted structure and confirmed on the next tick; narrative stayed `accepted`; no collector ran. |
| AC-4: unreported final retained; root completion not closure | covered by accepted MON-02 source tests; MON-05 wakes for unreported finals | `_markers_for_snapshot` advances a work key only after all covering parts confirm; the recovery path keeps a report pending until then. |
| AC-6/D8/D10: narration failure yields only the labeled notice, once per cut | `test_precheck_sends_one_labeled_service_notice_for_failed_narration`; `test_session_end_sends_only_a_notice_for_rejected_narration`; `test_post_llm_call_rejects_malformed_or_fabricated_narratives` | A `failed` narration produced exactly one `[SERVICE NOTICE]`/`[NO PROGRESS COVERAGE]` notice, no coverage marker; a second tick added nothing; a rejected narrative was persisted as `rejected` and never became an official report. |
| AC-6: exact reporter match, recursion exclusion | `test_reporter_context_requires_the_exact_owned_cron_binding`; `test_post_llm_call_persists_only_a_validated_narrator_result`; `test_session_end_delivers_only_for_the_owned_reporter_and_advances_on_confirm` | Wrong job id, wrong platform, wrong profile, disabled monitor and foreign session all failed to match; only the exact `cron_<job_id>_…` session with the pending lease persisted/validated the narrative and delivered; a repeat session-end sent nothing. |
| AC-6: manual off blocks narration/send and retry | `test_manual_off_blocks_narration_delivery_and_retry` | The racing session-end performed no send and left the report pending/durable; re-enabling let the next pre-check deliver the preserved report exactly once without another narration. |
| AC-4/D3: direct project-bound work, no invented contract | `test_direct_enrollment_requires_an_exact_project_bound_session`; `test_direct_turn_end_marks_flags_and_continuation_opens_a_new_interval`; `test_direct_turn_end_requires_an_enrolled_interval` | Only the exact session whose workdir matched the marker-verified registered project enrolled; `cron_` sessions, monitor-control calls and unbound sessions enrolled nothing; a turn recorded `completed` with a bounded summary and the continuation opened a new `unknown` interval. |
| D7/D12 privacy: no raw transcripts/paths/identifiers | `test_direct_records_reject_unsafe_reported_summaries`; `test_control_tool_matches_the_cli_envelope_and_rejects_bad_arguments` | URL/path/`@`-bearing reported summaries were dropped; a 4000-character summary was truncated to the 600-character bound; the durable record held no raw content. |
| AC-1/D5: CLI/tool parity and malformed inputs | `test_control_tool_matches_the_cli_envelope_and_rejects_bad_arguments`; `test_cli_actions_read_the_durable_state_without_hermes`; `test_cli_malformed_inputs_fail_closed` | Tool and CLI produced the same schema/action/result keys for the same durable state; extra/unknown/invalid arguments returned `INVALID_ARGUMENT`/`INVALID_LIMIT` or argparse exit 2; `on` without a runtime failed closed without changing state. |
| AC-8/plan §7: Hermes-free manager, validated subprocess boundary | `test_cli_parser_and_help_are_hermes_free_and_expose_the_fixed_surface`; `test_runtime_subprocess_boundary_validates_and_fails_closed`; packaging `monitor --help` with a broken Hermes import | `aether monitor --help` worked with no Hermes in `sys.modules`; the runtime probe rejected a candidate that cannot import the interfaces; non-JSON/wrong-schema/wrong-action/crash outputs were rejected; action and `--limit` were forwarded exactly; `HERMES_KANBAN_*`/`PYTHONPATH` are stripped for the child. |
| AC-8/plan §7: restricted reporter toolset, Morfeo-only opt-in | `test_reporter_tool_is_restricted_to_the_dedicated_toolset_and_exact_run`; `test_tool_registration_is_morfeo_only_and_opt_in`; `test_morfeo_portable_opt_in_is_the_only_profile_that_enables_the_monitor`; `test_exact_hermes_interfaces_...` (real registry) | Exactly two tools registered; reporter toolset resolved to exactly `{aether_monitor_report_snapshot}` and control toolset to exactly `{aether_monitor}` in the release-locked registry; authoring/registration for Supervisor/Implementer and disabled settings produced no tools. |
| AC-8: packaged entry point and resources | `test_only_one_plugin_entry_point_is_declared_for_the_monitor`; `test_wheel_exposes_the_fourth_entry_point_and_monitor_resources`; `test_wheel_has_exact_official_plugin_entrypoints_and_role_profile_opt_ins`; `test_same_wheel_installs_in_isolated_manager_and_runtime_without_path_shadowing` | Wheel declares exactly four plugin entry points; monitor resources and profile opt-in ship byte-equal; manager and runtime installs agree. |
| Plan §6: capability preflight against the imported runtime | `test_exact_hermes_interfaces_hooks_toolset_and_owned_cron_job`; `_module_problems` source check | `_module_problems()` returned `[]` against the verified release-locked checkout, and the wake-gate/hook/toolset facts above were read from the actual sources. |

## Verification record

All commands were run in the assigned worktree with the locked `uv` environment.

- Quickstart focused files (`quickstart.md` §2):
  - `uv run --frozen pytest -q tests/test_telegram_monitor_state.py` → **20 passed in 0.17s**
  - `uv run --frozen pytest -q tests/test_telegram_monitor_sources.py` → **39 passed in 0.34s**
  - `uv run --frozen pytest -q tests/test_telegram_monitor_runtime.py` → **29 passed in 0.42s**
  - `uv run --frozen pytest -q tests/test_telegram_monitor_delivery.py` → **22 passed in 0.34s**
  - `uv run --frozen pytest -q tests/test_telegram_monitor_cli_plugin.py` → **11 passed in 1.86s**
- MON-05 runtime/CLI plus the complete accepted monitor surface through the exact-Hermes
  bootstrap lane:
  `uv run --frozen python scripts/run_tests.py -- -q tests/test_telegram_monitor_runtime.py tests/test_telegram_monitor_cli_plugin.py tests/test_telegram_monitor_state.py tests/test_telegram_monitor_sources.py tests/test_telegram_monitor_reporting.py tests/test_telegram_monitor_delivery.py`
  → **182 passed in 4.58s** (the release-locked checkout is verified before pytest starts;
  both `hermes_exact` tests executed rather than skipped).
- Regression surfaces in the same lane:
  `... tests/test_observation_cli_plugin.py tests/test_observation_packaging.py tests/test_public_artifacts.py tests/test_knowledge_plugin_cli.py tests/test_objective_contracts.py`
  → **2 failed, 105 passed, 1 skipped**; the two failures are baseline, not candidate-caused
  (see "Pre-existing baseline failures").
- Full repository suite through the exact-Hermes bootstrap lane:
  `uv run --frozen python scripts/run_tests.py -- -q`
  → **7 failed, 1260 passed, 60 skipped, 373 subtests passed in 113.16s**. One failure is
  the pre-existing issue #364 (below). The other six are candidate-caused and are a
  cross-unit collision that MON-05 cannot repair inside its writable boundary — see the
  next section.
- Packaging: `uv build` through `test_wheel_exposes_the_fourth_entry_point_and_monitor_resources`
  and `test_same_wheel_installs_in_isolated_manager_and_runtime_without_path_shadowing`
  → passed (four entry points, shipped resources, manager/runtime fingerprint equality,
  monitor help with a broken Hermes import).
- Static gates:
  - `uv run --frozen ruff check src/aether_agents/monitor tests/test_telegram_monitor_runtime.py tests/test_telegram_monitor_cli_plugin.py src/aether_agents/cli.py src/aether_agents/resources/monitor/precheck.py` → **All checks passed**
  - `uv run --frozen ruff format --check src/aether_agents/monitor tests/test_telegram_monitor_runtime.py tests/test_telegram_monitor_cli_plugin.py src/aether_agents/cli.py src/aether_agents/resources/monitor/precheck.py tests/test_observation_packaging.py tests/test_public_artifacts.py` → **17 files already formatted**
  - `uv run --frozen ruff check tests/` → **6 errors, all pre-existing** (same 6 on the
    base commit; `tests/test_knowledge_regressions.py`, `tests/test_objective_contracts.py`)
  - `uv run --frozen mypy src/aether_agents/monitor` → **Success: no issues found in 11 source files**
  - `uv run --frozen python -m compileall -q src tests` → passed
  - `uv run --frozen python scripts/check_hermes_baseline_drift.py --json` → exit 0
    (baseline `v2026.8.18` / `e624e9f…`)
  - `git diff --check` → passed
- Deliberate non-effects: no live model call, no Telegram send, no profile/job activation, no
  source database write, no credential operation, no dependency or lockfile change, no push,
  PR, merge or issue mutation. All native checks ran against disposable homes, disposable
  cron stores and fake senders.

## Cross-unit collision: the lifecycle entry-point allow-list (return to Supervisor)

The card requires exactly one new plugin entry point
(`aether-telegram-monitor = aether_agents.monitor.hermes_plugin`). The accepted product
lifecycle validates a candidate wheel against a closed allow-list:

- `src/aether_agents/lifecycle.py:105 AETHER_PLUGIN_ENTRY_POINTS` enumerates the three
  previously approved plugins and is compared with the built wheel at `:4011`
  (`IntegrityError: candidate Aether plugin entry-point set mismatch`).

Consequently six accepted-lifecycle tests now fail in the full suite:

```text
tests/test_observation_lifecycle.py::test_wheel_fingerprint_binds_runtime_metadata_schemas_and_entry_points
tests/test_observation_lifecycle.py::test_wheel_inspection_binds_the_targets_own_projection_schema
tests/test_observation_lifecycle.py::test_release_lock_identity_is_explicit_and_semantically_matches_the_wheel
tests/test_observation_lifecycle.py::test_prepare_release_installs_one_wheel_in_manager_and_exact_runtime
tests/test_observation_lifecycle.py::test_exact_public_lifecycle_uses_real_plugin_profiles_query_and_recovery
tests/test_observation_lifecycle.py::test_disposable_public_install_capture_query_update_rollback_uninstall_purge
```

Both `src/aether_agents/lifecycle.py` and `tests/test_observation_lifecycle.py` are outside
this unit's writable boundary, so MON-05 did not edit them and did not weaken any check.
Required repair (Supervisor/MON-INT, bounded and mechanical): add the monitor entry point to
`AETHER_PLUGIN_ENTRY_POINTS` (with a `MONITOR_ENTRY_POINT` constant beside the existing three)
and update the matching release-fingerprint expectations in `tests/test_observation_lifecycle.py`.
Until that lands, installed-wheel/release-candidate validation rejects the fourth entry point;
the monitor's own behavior is unaffected, and its packaging evidence above was obtained from
the wheel built by `test_wheel_exposes_the_fourth_entry_point_and_monitor_resources`.

## Pre-existing baseline failures

- `tests/test_public_artifacts.py::test_tracked_public_surface_contains_no_operator_paths`
  fails identically on the base commit: `.aether/objective-contracts/oc_0084270d940c98d9/v1.md`
  reports `absolute-user-home` and `operator-desktop-layout` (issue #364, owned by the
  contract/D12 work, not this unit). MON-05 adds no scanner finding.
- The plain `pytest` lane cannot collect Hermes-dependent observation tests
  (`ModuleNotFoundError` for `hermes_cli` and other Hermes-only modules) — the documented environment
  limitation the accepted MON-01..MON-04 evidence already records. They pass in the
  exact-Hermes bootstrap lane.
- `scripts/check_documentation.py` now reports the monitor CLI options and plugin as
  uncovered derived surface. That is MON-06's assigned documentation and generated
  capability registry work (`docs/reference/cli.md`, `docs/reference/plugins-and-tools.md`,
  `docs/capabilities.toml`); MON-05 must not edit those files. No existing documentation
  check was weakened.

## Compatibility and residual risk

**Unit compatibility impact: `none`.** The monitor is additive: four new monitor modules, one
resource, one plugin entry point listed only in the Morfeo profile, one new CLI command
family and additive test updates. No existing import, tool, command, profile, policy file or
Hermes behavior changed; the manager package remains importable without Hermes.

Residual risks, stated honestly:

- The runtime subprocess boundary resolves the product interpreter from
  `AETHER_HERMES_PYTHON`, then a `hermes`-sibling interpreter, then the manager interpreter,
  and requires a successful interface probe. On an installation whose Hermes lives behind an
  unusual launcher, the operator must set `AETHER_HERMES_PYTHON` (private operational
  context); the failure mode is a bounded `RUNTIME_UNAVAILABLE`, not a guess.
- `_module_problems()` is a capability preflight, not a guarantee: it proves the imported
  runtime exposes the interfaces, not that the plugin will be enabled there. Activation
  therefore remains MON-INT's verified step, and a drifted runtime makes the pre-check wake
  with an explicit diagnostic instead of pretending to be idle.
- The narration lease protects one in-flight narration per cut and is released by the
  reporter's own path; a crashed narration's lease is recovered by the store's dead-owner
  recovery on the next lease operation, so a crashed tick is re-narrated rather than lost.
  This was verified with a live-lease probe and a resumption probe, but only deterministic
  fakes stood in for the real model turn.
- The pre-check's runtime-mismatch path wakes the agent with a diagnostic instead of a
  snapshot; the reporter cannot match it, so no report is sent and the failure is visible in
  the cron output. Live qualification of that path belongs to MON-INT.
- AC-5 narrative fidelity, AC-7 live Telegram acceptance and AC-9 activation remain MON-06
  and MON-INT work; this unit provides deterministic evidence only.
