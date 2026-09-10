# MON-05 Implementation Evidence — native runtime, controls and packaging

**Unit:** MON-05
**Task:** `t_8608f340`
**Objective Contract:** `oc_f8c9fc9320587cf3@v1` (SHA-256 `0de5f55efe6844174efd8abf9f72f492c6d36981af42bb730fb34ce8774c9d24`)
**Base commit:** `fbf0b1d922b8e72943f3a6e99620520dc8d9f9d9` (reviewed MON-01..MON-04 replay; see "Base reconstruction")
**Implementation tree SHA (before this evidence file):** `d487a99e152983b59e7104592e72aa8b96a6c7ed` (`git write-tree` with the implementation and tests staged, this evidence file excluded)
**Status:** self-verified against review round 2 corrections; ready for same-card Supervisor
review.
**Review round:** 3 (round-2 changes requested at candidate `5deb29f428142dd68d4363383314557825e16dd7`).

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
  and creates or reconciles exactly one job with `schedule=0 * * * *`, `no_agent=False`,
  `script=aether_monitor_precheck.py`, `deliver=local`, `attach_to_session=False`,
  `enabled_toolsets=["aether_monitor_reporting", "no_mcp"]`, no
  `monitor_script`/`monitor_url`, no `origin`/`model`/`provider`/`skills`/`context_from`/
  `workdir`. The persisted job id is the runtime authority. A same-name job is *never*
  adopted without a persisted id, a persisted id whose record looks like a different job is
  never touched, a second job claiming the monitor name is `JOB_CONFLICT`, an unreadable
  inventory or an update that does not take fails as `JOB_OPERATION_FAILED`, and a drifted
  owned record is repaired through `update_job` to the full fixed shape (prompt, schedule,
  toolsets, model/provider/base_url/origin/skills/context/workdir included) and revalidated.
  `pause_job`/`resume_job` revalidate the ownership identity of the exact persisted record
  before any native mutation, so a replaced or foreign record is never paused or resumed.
- **Manual off is durable and ordered.** `MonitorService._off` commits `enabled=false`
  before pausing the exact persisted job; a racing pre-check re-reads the switch and stops
  without inference, and a racing send re-checks `enabled` before every attempt (MON-04
  adapter). Restart/agent activity cannot re-enable the monitor: `on` is the only writer.
  `on` resumes the owned native job *before* flipping the durable switch, so a failed enable
  can never claim "on" (or let a racing pre-check collect) while the job is unscheduled; the
  durable binding survives for a retry.
- **Exact Morfeo identity.** `on` requires the provisioned runtime to identify itself as
  the Morfeo profile (and to agree with any persisted binding) before any pin, job or state
  mutation; a missing or foreign identity fails as `RUNTIME_MISMATCH`. Every reporter path
  (`reporter_context`, snapshot tool, `post_llm_call`, `on_session_end`) and every direct
  enrollment path requires that exact profile, never accepting a missing identity.
- **Configured timezone.** The monitor resolves the native Hermes IANA zone
  (`hermes_time` → `HERMES_TIMEZONE` → server-local), pins it on `on`, and uses it for the
  hourly cutoff, `status` rendering and DST boundaries, so cuts land on the same clock the
  native cron actually fires on instead of the OS-local zone (e.g. `Asia/Kolkata` cuts at
  `:30` UTC).
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
  A late tick resolves to the configured wall-clock hour it belongs to; a repeat tick inside
  the same hour is suppressed only when the cut is already collected or a live narration owns
  it, and a contended cut lease makes the second tick emit `collection-in-progress` instead
  of starting a second narration.
- **Bounded recovery with a cross-process handoff.** A report that was collected but never
  narrated (process death or callback failure) is re-surfaced by the next pre-check with its
  own bounded context and a fresh pending narration lease plus its private handoff, so a
  pending report cannot be silently lost behind a newer cut. The pre-check runs in a native
  child process, so the handoff (mode-0600 JSON under `<state>/monitor/handoff/`) is what
  carries the exact pending report to the exact reporter session after the child exits; the
  lease row alone cannot survive the boundary because the store recovers dead owners by
  design. That live handoff is also the pre-inference fence: a later tick that finds it
  emits a non-wake `narration-in-progress` gate instead of waking a second narration for the
  same digest, and the reporter read path only exposes a snapshot after claiming the exact
  handoff for this report, cutoff, persisted job and session. Reports whose parts never
  confirmed are retried through the transport only (never a model call), and a
  failed/rejected narration is re-sent as the single fixed labeled service notice per report
  cut.
- **Reporter recognition.** A reporter is exactly a native cron session whose id starts with
  `cron_<persisted job id>_`, on platform `cron`, for the exact bound Morfeo profile (the
  callback identity and the durable persisted pin must both be Morfeo — a missing pin never
  matches), and whose unresolved report carries a fresh private handoff bound to that report,
  cutoff and persisted job; the snapshot read itself claims that exact handoff for the claiming
  session before any snapshot is exposed. Taking the narration lease over is
  token-fenced: a live foreign narration, a wrong-job/wrong-cutoff/foreign-holder handoff, or a
  *different* cron session of the same job, can never steal or refresh the claim, while the
  claiming session may refresh its own claim
  across `post_llm_call` → `on_session_end`. `post_llm_call` validates the narrative against
  the canonical snapshot and persists `accepted`/`rejected`; `on_session_end` renders and
  delivers only for that exact session, releases the narration lease and deletes the handoff,
  and sends only the labeled service notice when narration failed. Any other hook path only
  records source evidence and never sends.
- **Direct Morfeo work.** `post_tool_call` enrolls a project-bound turn only when the exact
  native session exists, its recorded `source` is a local interactive session (`tui`/`cli`),
  and its recorded workdir matches a marker-verified registered project (portable id + native
  project id); gateway platform traffic (`telegram`, …), sub-agent `tool` runs, cron sessions
  and unknown service sources never enroll. `post_llm_call` attaches a bounded reported
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
  toolset to exactly one tool; the owned job carries the supported `no_mcp` sentinel, which
  the release-locked scheduler strips at resolution time, so the per-job list cannot
  default-expand with every provisioned MCP server into terminal/file/messaging/board/
  delegation/cron/control tools. The MORFEO profile is the only profile config that enables
  the plugin (`language: Spanish`); Supervisor and Implementer configs are untouched.
- **Packaging.** One new entry point `aether-telegram-monitor = aether_agents.monitor.hermes_plugin`
  (four total), the packaged pre-check and narration context ship in the wheel byte-equal to
  source, and the monitor help path still works with a deliberately broken Hermes import.

## Review round 2 corrections (supersedes round-1 claims)

Round 1 requested changes against `383fe376e098a62d5068518cf7e0fff1ce1bc930`. Each item below
lists the defect, the correction in this candidate, and the regression that now covers it.

1. **Reporter lease across the real process boundary.** The packaged pre-check runs in a
   native child (`cron/scheduler.py:3482-3645` at `v2026.8.18`), so its lease owner is dead
   before the reporter session starts and `acquire_collection_lease` recovers it by design.
   The round-1 `_pending_lease_present` therefore rejected the exact reporter. Correction:
   the pre-check writes a private cross-process handoff
   (`<state>/monitor/handoff/<sha256(report_id)>.json`, mode 0600, schema
   `aether.telegram-monitor.handoff.v1`, bound to report/cutoff/job/holder/token/expiry)
   whenever it acquires a pending narration lease, and `_claim_pending_lease` transfers the
   claim to the exact reporter through it. Regressions:
   `test_precheck_child_handoff_reaches_the_exact_reporter` (real subprocess running the
   packaged entry point, child exits, parent store claims and delivers exactly once) and the
   exact-lane `test_exact_packaged_precheck_child_hands_the_lease_to_the_reporter` (the
   installed packaged script executed as a child, then through the real native
   `_run_job_script`, then a single delivery), plus
   `test_reporter_requires_the_exact_precheck_handoff` (no handoff, wrong-job handoff and
   expired handoff all refuse) and `test_reporter_claim_loses_to_a_live_foreign_narration`.
2. **Reporter-only tool surface.** The release-locked scheduler unions every enabled MCP
   server into a per-job list unless the supported `no_mcp` sentinel is present
   (`cron/scheduler.py:394-446`). The owned job now carries
   `enabled_toolsets=["aether_monitor_reporting", "no_mcp"]`, `_drift()` expects exactly that
   list, and the exact test proves with the real scheduler resolver that a provisioned MCP
   server is added without the sentinel and excluded with it.
3. **Profile checks failed open.** `on` now requires the exact Morfeo identity before any
   pin/job/state mutation (missing or foreign → `RUNTIME_MISMATCH`), and every reporter and
   direct path requires the exact profile. Regressions:
   `test_on_requires_the_exact_morfeo_identity_before_any_mutation`,
   `test_reporter_context_requires_the_exact_profile`,
   `test_direct_enrollment_rejects_gateway_service_and_foreign_profiles`.
4. **Job ownership and fixed shape.** `ensure_job` never adopts a same-name job without a
   persisted id, rejects a persisted id whose record is not the monitor job, rejects a
   second job claiming the monitor name, fails on an unreadable inventory, validates that
   `update_job` actually applied the full fixed shape (prompt, model, provider, base_url,
   origin, skills, context_from, workdir included), and `pause_job`/`resume_job` revalidate
   ownership before mutating. Regressions:
   `test_ensure_job_refuses_same_name_adoption_without_a_persisted_id`,
   `test_ensure_job_rejects_replaced_ids_and_inventory_failures`,
   `test_ensure_job_reconciles_the_full_fixed_shape`,
   `test_ensure_job_creation_carries_and_validates_the_fixed_shape`,
   `test_ensure_job_fails_when_the_native_update_does_not_apply`,
   `test_pause_and_resume_revalidate_ownership`, plus the exact-lane drift/pause/resume cycle
   through the real `cron.jobs` API.
5. **Failed `on` left the monitor enabled.** The order is now: validate identity/destination,
   ensure the owned job, persist the binding, resume the native job, and only then commit
   `enabled=true`. Regression: `test_failed_enable_never_flips_the_monitor_on` (resume
   failure → error, `enabled=false`, no `enabled:True` event, racing pre-check stays silent).
6. **Direct enrollment ignored the session source.** `_session_project_binding` now selects
   and validates the native session `source` against a closed local-interactive allow-list
   (`tui`, `cli`); gateway/sub-agent/service sources are excluded even when their cwd matches
   a registered project. Regression:
   `test_direct_enrollment_rejects_gateway_service_and_foreign_profiles` (telegram/tool
   sources with matching cwd enroll nothing; `tui` continues to enroll).
7. **Timezone.** `configured_timezone_name()` resolves `hermes_time` → `HERMES_TIMEZONE` →
   server-local; `on` pins the resolvable configured IANA zone; the pre-check cut, `status`
   rendering and DST boundaries all use it. Regressions:
   `test_configured_timezone_comes_from_native_configuration`,
   `test_precheck_cuts_hours_in_the_configured_native_zone` (`Asia/Kolkata` cut at `:30` UTC),
   `test_status_renders_the_next_cut_in_the_persisted_zone`,
   `test_status_keeps_a_resolvable_persisted_zone_over_a_local_label`,
   `test_on_pins_the_resolvable_configured_zone`,
   `test_hour_boundary_follows_the_configured_zone_across_a_dst_fold`.

A later self-review pass additionally fenced the lease takeover to the *exact* claiming
session (`test_reporter_claim_is_fenced_to_the_exact_session`): a second cron session of the
same job can neither claim nor deliver a live report, so the handoff cannot be used to
duplicate a narration. A repeat cut-contended tick now emits `collection-in-progress`
instead of starting a second narration.

Known environment limit: the optional `croniter` dependency is absent from this environment,
so a native `create_job` for `0 * * * *` cannot be executed here. Creation fidelity is
covered by `ensure_job`'s own post-create fixed-shape validation and the fake-native creation
assertion in the plain lane; the exact lane exercises the real native
`get_job`/`update_job`/`pause_job`/`resume_job` reconciliation cycle, the real scheduler
toolset resolution, and the real packaged-script execution.

## Review round 3 corrections (supersedes round-2 claims)

Round 2 requested changes against `5deb29f428142dd68d4363383314557825e16dd7`. Each item below
lists the reproduced defect, the correction in this candidate, and the regression that now
covers it.

1. **The handoff was not a real cross-process fence.** After the pre-check child exited,
   `_resume_pending_narration()` recovered its dead-process lease without consulting the
   still-live handoff and rewrote it, so two sequential real pre-check children against the
   same pending report each emitted `{"wakeAgent": true, "reason": "pending-report"}` — two
   narrations for one digest. `reporter_snapshot()` likewise only checked that *some* fresh
   handoff file existed: an independently written wrong-job handoff exposed the report, and a
   second same-job session could read after another session had claimed. Correction:
   `_fence_handoff()` resolves a live, exactly-bound handoff (report + cutoff + persisted job
   + known holder) and `_resume_pending_narration()` now consults it *before* any lease
   acquisition, emitting the non-wake `narration-in-progress` gate for a consumed tick;
   `_claim_pending_lease()` validates the handoff's holder and claimed session exactly (the
   pre-check's own transfer, or the exact claiming session only) before any takeover, and
   `reporter_snapshot()` performs that exact claim itself so the read is the fence.
   Regressions: `test_two_real_precheck_children_wake_exactly_one_narration` (two real child
   processes: the first wakes, the second emits `{"reason": "narration-in-progress"}` and
   leaves the handoff byte-identical, the expired fence then recovers, and exactly one
   reporter delivery follows) and `test_reporter_snapshot_requires_the_exact_live_handoff`
   (no handoff, foreign holder, foreign job, foreign cutoff, expired handoff and a second
   session are all refused; a released claim plus a fresh exact handoff reads again).
2. **The persisted profile binding was still optional.** `reporter_context()` accepted an
   enabled store with `profile_binding=None`, so a reporter path matched without the durable
   Morfeo pin. Correction: `settings.profile_binding == profile_name == MORFEO_PROFILE` is
   required on every reporter path. Regression:
   `test_reporter_context_requires_the_persisted_binding` (missing persisted binding refuses
   `reporter_context` and `post_llm_call`; re-pinning restores it).
3. **Raw native failures escaped the fixed JSON interface.** `on`, `status` and `off` raised
   raw `RuntimeError` out of `ensure_job`, `job_state` and `pause_job` with no
   `aether.telegram-monitor.v1` envelope. Correction: `MonitorService._native` /
   `_native_mapping` wrap every native identity, destination, get/create/update/pause/resume
   and status call into the sanitized `MonitorActionError` taxonomy, and both the CLI
   in-process boundary and the plugin control handler fail closed with the fixed envelope if
   the runtime raises. Regression: `test_native_failures_never_escape_the_control_envelope`
   (raw `RuntimeError` from identity/destination/ensure/resume/pause/state; all four public
   actions keep a valid envelope and make no unauthorized transition) plus
   `test_control_tool_returns_a_bounded_envelope_when_the_runtime_raises` and
   `test_cli_control_action_returns_the_envelope_when_the_runtime_raises`.
4. **Resume accepted a drifted record.** `_validated_job()` checked only name/script/deliver,
   so a paused persisted-id record with a hijacked prompt and `enabled_toolsets=["terminal"]`
   was resumed. Correction: `_validated_job(..., require_fixed_shape=True)` re-reads the
   record and revalidates the full behavior-bearing fixed shape (`_drift`) immediately before
   the native resume, failing as `JOB_CONFLICT` without any native mutation; `pause_job`
   deliberately keeps the fail-safe identity-only policy so a drifted record can still be
   stopped. Regressions: `test_resume_revalidates_the_fixed_shape_after_reconciliation` and
   the drift-after-reconciliation block inside the exact-lane
   `test_exact_hermes_interfaces_hooks_toolset_and_owned_cron_job` against the real
   release-locked `cron.jobs` store.
5. **`status` could label one clock while rendering another.** With the persisted pin
   `Asia/Kolkata` and the current configured zone `America/New_York`, `status` reported
   `timezone: Asia/Kolkata` while `next_cut_local`/`next_cut_utc` rendered `America/New_York`.
   Correction: `_status()` reports one effective clock (`timezone`), renders
   `next_cut_local`/`next_cut_utc` in that same zone, and exposes the persisted pin
   (`pinned_timezone`) and explicit `timezone_drift`; the process-local label is used only when
   no IANA zone resolves. Regression:
   `test_status_describes_one_clock_and_exposes_pinned_drift` (changed configured zone,
   unresolvable local label, and re-pinned agreement).

Also in this round: the `hermes_plugin.py` docstring now states the load-bearing `no_mcp`
sentinel explicitly, and two pre-existing wall-clock-dependent regressions
(`test_precheck_retries_unconfirmed_parts_without_rerunning_the_narrator` and the second tick
of `test_precheck_sends_one_labeled_service_notice_for_failed_narration`) now pass an explicit
tick clock. The first failed identically on the round-2 candidate after the host clock crossed
the seeded cut (07:00 America/Mexico_City); no assertion was weakened, and the recovery
sequence is now deterministic on any wall clock.

## Requirement-to-evidence mapping

| Obligation (TM/D/AC/plan) | Check executed | Observed result |
| --- | --- | --- |
| TM-005/D1/D2: one native hourly job, `0 * * * *`, ordinary agent job, packaged pre-check, `deliver=local`, no monitor suppression | `test_exact_hermes_interfaces_hooks_toolset_and_owned_cron_job` (`hermes_exact`, real `cron.jobs` reconciliation API); `test_ensure_job_creation_carries_and_validates_the_fixed_shape` | Session id `cron_<job-id>_<timestamp>` and `platform="cron"` confirmed in the release-locked scheduler; the created job carries `schedule="0 * * * *"`, `script="aether_monitor_precheck.py"`, `deliver="local"`, `no_agent=False`, `attach_to_session=False`, `enabled_toolsets=["aether_monitor_reporting","no_mcp"]`, the fixed prompt, and no monitor/origin/model fields; the exact lane repaired a hijacked record through the real `update_job` to that shape and the script installed byte-equal to the packaged resource. (Native `create_job` for a cron expression cannot execute here because the optional `croniter` dependency is absent; the exact lane exercises real create-shape validation via the repair cycle.) |
| AC-1: idempotent `on`, no duplicate job | `test_on_is_idempotent_and_reuses_the_single_owned_job`; `test_exact_hermes_interfaces_...` (second `ensure_job` must not mutate or duplicate) | First `on` created, second reused with no second native write: exactly one job, stable id, one duplicate-name check. |
| AC-1/D5: `off` persists before pausing; unrelated jobs untouched | `test_off_persists_disabled_before_pausing_the_exact_job`; `test_exact_hermes_interfaces_...` | Recorded event order `enabled:False` before `pause:<job-id>`; only the owned id paused/resumed; an unrelated job's JSON bytes were identical before and after the on/off cycle. |
| AC-1: repeated `on` after restart/activity stays off | `test_off_persists_disabled_before_pausing_the_exact_job` (status after restart) | Status reported `enabled: false`; only `on` writes enablement. |
| AC-1: missing/changed/ambiguous destination fails without credential request | `test_on_fails_closed_on_missing_or_changed_destination`; `test_on_rejects_a_different_profile_or_changed_pin` | `DESTINATION_MISSING`, `DESTINATION_CHANGED`, `RUNTIME_MISMATCH`; no job call, no pin persisted, enablement unchanged. |
| AC-2/D2: hourly wall-clock cuts in the configured zone, late ticks visible, DST, repeat suppression, one clock in `status` | `test_precheck_uses_the_local_wall_clock_hour_and_suppresses_a_repeat_tick`; `test_precheck_cuts_hours_in_the_configured_native_zone`; `test_next_hour_boundary_is_always_a_future_wall_clock_hour`; `test_hour_boundary_follows_the_configured_zone_across_a_dst_fold`; `test_status_renders_the_next_cut_in_the_persisted_zone`; `test_status_describes_one_clock_and_exposes_pinned_drift`; `test_precheck_collection_and_gate_stay_well_inside_the_start_bound` | Late 12:59:30 tick produced the 12:00 local cutoff record and `wakeAgent:true`; with `Asia/Kolkata` configured the cut landed at `:30` UTC (12:30Z for 12:45Z) rather than the UTC-grid 12:00Z; `status` rendered the next cut as `2026-09-10T19:00:00+05:30`; across the `Europe/Madrid` configured fold both instants resolved to the same wall-clock hour with differing explicit offsets and monotonic UTC cutoffs; with the pin `Asia/Kolkata` and the configured zone `America/New_York` the reported `timezone`, `next_cut_local` (`09:00:00-04:00`) and `next_cut_utc` described that one clock with `pinned_timezone`/`timezone_drift` exposing the stale pin, an unresolvable local label never became the reported clock, and re-pinning restored agreement; deterministic pre-check work stayed far below the 120 s start bound. |
| AC-2/D4/D8: idle is silent, source failure wakes, no unreported loss, cross-process handoff, one wake per pending digest | `test_precheck_idle_resolves_the_report_and_skips_inference`; `test_precheck_source_failure_wakes_instead_of_looking_idle`; `test_precheck_runtime_mismatch_is_observable_and_never_idle`; `test_precheck_resumes_an_unfinished_report_instead_of_collecting_again`; `test_precheck_waits_while_a_live_narration_owns_the_report`; `test_precheck_child_handoff_reaches_the_exact_reporter`; `test_two_real_precheck_children_wake_exactly_one_narration` | Idle emitted `{"reason":"idle","wakeAgent":false}` before any inference and resolved the report; collection error, pre-check error and runtime mismatch emitted `wakeAgent:true`; an un-narrated prior report was re-surfaced with its bounded context, a fresh lease and its handoff instead of a second cut; a live narration produced no duplicate narration and no second collection; a real pre-check child process exited before the parent reporter, whose store still claimed the `pending-report` handoff and delivered the report exactly once; two sequential real pre-check children produced exactly one wake (the second emitted `narration-in-progress` and left the handoff byte-identical), and after the fence expired the next child recovered the report and one exact reporter delivery followed. |
| AC-2/AC-6: bounded transport retry without extra narration | `test_precheck_retries_unconfirmed_parts_without_rerunning_the_narrator` | A failed part was re-rendered from the accepted structure and confirmed on the next tick; narrative stayed `accepted`; no collector ran. |
| AC-4: unreported final retained; root completion not closure | covered by accepted MON-02 source tests; MON-05 wakes for unreported finals | `_markers_for_snapshot` advances a work key only after all covering parts confirm; the recovery path keeps a report pending until then. |
| AC-6/D8/D10: narration failure yields only the labeled notice, once per cut | `test_precheck_sends_one_labeled_service_notice_for_failed_narration`; `test_session_end_sends_only_a_notice_for_rejected_narration`; `test_post_llm_call_rejects_malformed_or_fabricated_narratives` | A `failed` narration produced exactly one `[SERVICE NOTICE]`/`[NO PROGRESS COVERAGE]` notice, no coverage marker; a second tick added nothing; a rejected narrative was persisted as `rejected` and never became an official report. |
| AC-6: exact reporter match, handoff transfer, session fence, recursion exclusion | `test_reporter_context_requires_the_exact_owned_cron_binding`; `test_reporter_context_requires_the_exact_profile`; `test_reporter_context_requires_the_persisted_binding`; `test_reporter_requires_the_exact_precheck_handoff`; `test_reporter_snapshot_requires_the_exact_live_handoff`; `test_reporter_claim_is_fenced_to_the_exact_session`; `test_reporter_claim_loses_to_a_live_foreign_narration`; `test_post_llm_call_persists_only_a_validated_narrator_result`; `test_session_end_delivers_only_for_the_owned_reporter_and_advances_on_confirm`; `test_exact_packaged_precheck_child_hands_the_lease_to_the_reporter` | Wrong job id, wrong platform, missing/foreign profile, a missing persisted Morfeo binding, disabled monitor and foreign session all failed to match; a report without its pre-check handoff, with a wrong-job handoff or with an expired handoff was refused; the snapshot read itself claims the exact handoff, so a foreign holder, a foreign job, a foreign cutoff, an expired handoff and a second session of the same job are all refused and a released claim plus a fresh exact handoff reads again; a live foreign narration and a second cron session of the same job could neither claim nor deliver; only the exact `cron_<job_id>_…` session with the handoff persisted/validated the narrative and delivered, then released the lease and deleted the handoff, and a repeat session-end sent nothing. |
| AC-6: manual off blocks narration/send and retry | `test_manual_off_blocks_narration_delivery_and_retry` | The racing session-end performed no send and left the report pending/durable; re-enabling let the next pre-check deliver the preserved report exactly once without another narration. |
| AC-4/D3: direct project-bound work, exact source, no invented contract | `test_direct_enrollment_requires_an_exact_project_bound_session`; `test_direct_enrollment_rejects_gateway_service_and_foreign_profiles`; `test_direct_turn_end_marks_flags_and_continuation_opens_a_new_interval`; `test_direct_turn_end_requires_an_enrolled_interval` | Only the exact local-interactive session whose workdir matched the marker-verified registered project enrolled; a matching-cwd `telegram` gateway session and a `tool` sub-agent session enrolled nothing, as did a foreign profile; `cron_` sessions, monitor-control calls and unbound sessions enrolled nothing; a turn recorded `completed` with a bounded summary and the continuation opened a new `unknown` interval. |
| D7/D12 privacy: no raw transcripts/paths/identifiers | `test_direct_records_reject_unsafe_reported_summaries`; `test_control_tool_matches_the_cli_envelope_and_rejects_bad_arguments` | URL/path/`@`-bearing reported summaries were dropped; a 4000-character summary was truncated to the 600-character bound; the durable record held no raw content. |
| AC-1/D5: CLI/tool parity and malformed inputs | `test_control_tool_matches_the_cli_envelope_and_rejects_bad_arguments`; `test_cli_actions_read_the_durable_state_without_hermes`; `test_cli_malformed_inputs_fail_closed` | Tool and CLI produced the same schema/action/result keys for the same durable state; extra/unknown/invalid arguments returned `INVALID_ARGUMENT`/`INVALID_LIMIT` or argparse exit 2; `on` without a runtime failed closed without changing state. |
| AC-8/plan §7: Hermes-free manager, validated subprocess boundary | `test_cli_parser_and_help_are_hermes_free_and_expose_the_fixed_surface`; `test_runtime_subprocess_boundary_validates_and_fails_closed`; packaging `monitor --help` with a broken Hermes import | `aether monitor --help` worked with no Hermes in `sys.modules`; the runtime probe rejected a candidate that cannot import the interfaces; non-JSON/wrong-schema/wrong-action/crash outputs were rejected; action and `--limit` were forwarded exactly; `HERMES_KANBAN_*`/`PYTHONPATH` are stripped for the child. |
| AC-8/plan §7: restricted reporter toolset, Morfeo-only opt-in, no default expansion | `test_reporter_tool_is_restricted_to_the_dedicated_toolset_and_exact_run`; `test_tool_registration_is_morfeo_only_and_opt_in`; `test_morfeo_portable_opt_in_is_the_only_profile_that_enables_the_monitor`; `test_exact_hermes_interfaces_...` (real registry and real scheduler resolver) | Exactly two tools registered; reporter toolset resolved to exactly `{aether_monitor_report_snapshot}` and control toolset to exactly `{aether_monitor}` in the release-locked registry; the native scheduler resolver turned `["aether_monitor_reporting"]` into `["aether_monitor_reporting","provisioned-mcp"]` and resolved the fixed job list `["aether_monitor_reporting","no_mcp"]` to exactly `["aether_monitor_reporting"]`; authoring/registration for Supervisor/Implementer and disabled settings produced no tools. |
| AC-8: packaged entry point and resources | `test_only_one_plugin_entry_point_is_declared_for_the_monitor`; `test_wheel_exposes_the_fourth_entry_point_and_monitor_resources`; `test_wheel_has_exact_official_plugin_entrypoints_and_role_profile_opt_ins`; `test_same_wheel_installs_in_isolated_manager_and_runtime_without_path_shadowing` | Wheel declares exactly four plugin entry points; monitor resources and profile opt-in ship byte-equal; manager and runtime installs agree. |
| Plan §6: capability preflight against the imported runtime | `test_exact_hermes_interfaces_hooks_toolset_and_owned_cron_job`; `_module_problems` source check | `_module_problems()` returned `[]` against the verified release-locked checkout, and the wake-gate/hook/toolset facts above were read from the actual sources. |
| AC-1/plan §6: exact Morfeo identity before any mutation | `test_on_requires_the_exact_morfeo_identity_before_any_mutation`; `test_reporter_context_requires_the_exact_profile`; `test_reporter_context_requires_the_persisted_binding`; `test_direct_enrollment_rejects_gateway_service_and_foreign_profiles` | Missing/`implementer`/`supervisor` identities returned `RUNTIME_MISMATCH` with no enablement, job id, destination or profile binding persisted and no native call; `profile_name=None` matched no reporter context; an enabled store with `profile_binding=None` matched no reporter path and persisted no narrative; foreign-profile direct turns enrolled nothing. |
| AC-1/D5/plan §4: native failures keep the fixed JSON envelope | `test_native_failures_never_escape_the_control_envelope`; `test_control_tool_returns_a_bounded_envelope_when_the_runtime_raises`; `test_cli_control_action_returns_the_envelope_when_the_runtime_raises` | Raw `RuntimeError` from identity, destination, ensure, resume, pause and job-state left every action (`on`/`off`/`status`/`history`) a valid `aether.telegram-monitor.v1` envelope; failed enables never flipped `enabled` or `first_enabled_at_utc`, `status` degraded to a bounded `job_error`, `off` stayed durably off with a bounded warning, and the CLI/tool boundaries converted a raising in-process runtime into the same envelope. |
| AC-1: failed enable cannot flip the monitor on | `test_failed_enable_never_flips_the_monitor_on` | A native resume failure returned `JOB_OPERATION_FAILED`, left `enabled=false` and `first_enabled_at_utc` empty with no `enabled:True` event, persisted the owned binding for a retry, and the racing pre-check emitted `disabled` with no collection. |
| AC-1/D1: job ownership fail-closed (no name adoption, replaced ids, inventory/update failures, resume shape) | `test_ensure_job_refuses_same_name_adoption_without_a_persisted_id`; `test_ensure_job_rejects_replaced_ids_and_inventory_failures`; `test_ensure_job_reconciles_the_full_fixed_shape`; `test_ensure_job_fails_when_the_native_update_does_not_apply`; `test_pause_and_resume_revalidate_ownership`; `test_resume_revalidates_the_fixed_shape_after_reconciliation`; exact-lane pause of a foreign id and drift-after-reconciliation resume | A same-name foreign job without a persisted id, a replaced record at the persisted id, a duplicate monitor name and an unreadable inventory all failed with no create/update/mutation; a forced no-op update failed as `JOB_OPERATION_FAILED` without touching the record; the drifted record was repaired to the full fixed shape; behavior drift landing after reconciliation (prompt + `enabled_toolsets`) made resume fail `JOB_CONFLICT` against both the fake and the real release-locked store with the record left unmutated, while the fail-safe pause still stopped the identified record; a foreign id was never paused and its bytes were unchanged. |

## Verification record

All commands were run in the assigned worktree with the locked `uv` environment. Counts below
are from the final candidate (review round 3).

- Quickstart focused files (`quickstart.md` §2), plain lane
  (`uv run --frozen pytest -q -m "not hermes_exact" <file>`):
  - `tests/test_telegram_monitor_state.py` → **20 passed in 0.16s**
  - `tests/test_telegram_monitor_sources.py` → **39 passed in 0.32s**
  - `tests/test_telegram_monitor_reporting.py` → **61 passed in 1.90s**
  - `tests/test_telegram_monitor_delivery.py` → **21 passed, 1 deselected in 0.32s**
  - `tests/test_telegram_monitor_runtime.py` → **55 passed in 1.15s**
  - `tests/test_telegram_monitor_cli_plugin.py` → **11 passed, 3 deselected in 0.59s**
  - combined plain lane of all six files → **207 passed, 4 deselected in 4.41s**
- MON-05 runtime/CLI plus the complete accepted monitor surface through the exact-Hermes
  bootstrap lane:
  `uv run --frozen python scripts/run_tests.py -- -q tests/test_telegram_monitor_runtime.py tests/test_telegram_monitor_cli_plugin.py tests/test_telegram_monitor_state.py tests/test_telegram_monitor_sources.py tests/test_telegram_monitor_reporting.py tests/test_telegram_monitor_delivery.py`
  → **211 passed in 6.14s** (the release-locked checkout is verified before pytest starts;
  all four `hermes_exact` tests executed rather than skipped).
- Regression surfaces in the same lane:
  `... tests/test_observation_cli_plugin.py tests/test_observation_packaging.py tests/test_public_artifacts.py tests/test_knowledge_plugin_cli.py tests/test_objective_contracts.py`
  → **1 failed, 106 passed, 1 skipped in 11.20s**; the failure is the pre-existing
  public-artifact issue #364 (see "Pre-existing baseline failures").
- Full repository suite through the exact-Hermes bootstrap lane:
  `uv run --frozen python scripts/run_tests.py -- -q`
  → **7 failed, 1289 passed, 60 skipped, 373 subtests passed in 144.32s**. One failure is
  the pre-existing issue #364 (below). The other six are candidate-caused and are a
  cross-unit collision that MON-05 cannot repair inside its writable boundary — see the
  next section.
- Packaging: the wheel built inside the exact lane by
  `test_wheel_exposes_the_fourth_entry_point_and_monitor_resources` (four entry points,
  shipped resources) and `tests/test_observation_packaging.py` → **9 passed in 2.41s**
  (including `test_same_wheel_installs_in_isolated_manager_and_runtime_without_path_shadowing`
  and the monitor help check with a broken Hermes import).
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
- Round-3 regression check: with the new fence temporarily reverted, the unchanged
  `test_two_real_precheck_children_wake_exactly_one_narration` fails with the reviewer's
  reproduction (`{'wakeAgent': True, 'reason': 'pending-report'}` from the second child);
  it passes with the fence in place. The pre-existing wall-clock-dependent failure
  (`test_precheck_retries_unconfirmed_parts_without_rerunning_the_narrator`) was reproduced
  identically on the round-2 candidate before the deterministic tick clock was added.
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
- The narration lease protects one in-flight narration per cut and is transferred to the
  exact reporter session through the private handoff; after delivery the handoff is deleted
  and the lease released. A crashed narration's lease is recovered by the store's dead-owner
  recovery on the next lease operation, and the next pre-check re-surfaces the report with a
  fresh handoff, so a crashed tick is re-narrated rather than lost. The cross-process path is
  covered by two real-subprocess regressions (a plain-lane child and the installed packaged
  script through the native scheduler helper); only deterministic fakes stood in for the
  real model turn.
- The handoff carries identifiers and a lease token only, inside the monitor's private state
  root (directory mode 0700, file mode 0600, bounded at 8 KiB, `aether.telegram-monitor.handoff.v1`);
  it holds no message text, chat identity, credential or source content.
- `on` pins the resolvable configured IANA zone. The pre-check always follows the native
  configuration in force at fire time (that is the clock cron uses), and `status` reports
  that same effective clock for `timezone`, `next_cut_local` and `next_cut_utc` while
  exposing the persisted pin as `pinned_timezone` plus an explicit `timezone_drift` flag, so
  an operator who changes the native zone sees the drift instead of a mixed or stale clock
  (re-running `on` re-pins and clears the flag).
- The pre-check's runtime-mismatch path wakes the agent with a diagnostic instead of a
  snapshot; the reporter cannot match it, so no report is sent and the failure is visible in
  the cron output. Live qualification of that path belongs to MON-INT.
- AC-5 narrative fidelity, AC-7 live Telegram acceptance and AC-9 activation remain MON-06
  and MON-INT work; this unit provides deterministic evidence only.
