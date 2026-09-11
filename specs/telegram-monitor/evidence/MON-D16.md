# MON-D16 Implementation Evidence — native accelerated laboratory schedule

**Unit:** D16 — native accelerated laboratory schedule with minute boundaries and hourly production
**Task:** `t_37daf6b2`
**Objective Contract:** `oc_f8c9fc9320587cf3@v4` (SHA-256 `765a2f48842835d91049f959defd6c3bd15cd43de9ef97da67a37d1a819bcfe0`)
**Base commit:** `81d8cad489702fac6580aee54e3ad3fc976d7d96` (v4 breakdown on integration base `828b736745fe1cd86ef51e5620ffc1094a952c32`)
**Candidate implementation commit:** `369b08adee5ea5f7598eba53382671fe37f730dc`
**Phase:** Implementer unit; **no live effect performed** — no `--live` run, model call, Telegram send, scheduler start, lab-job enable, profile/config/credential/provider mutation, runtime modification, retained-lab cleanup, push, PR or issue mutation.

## Scope and changed paths

- `scripts/qualify_telegram_monitor.py`
  - Added the fixed qualification-only `* * * * *` expression beside the unchanged production `0 * * * *` shape.
  - Added a private-context native probe that validates the owned job at the production shape and calls only `cron.jobs.update_job` to apply the accelerated expression. The probe records before/after schedules and the native recomputed `next_run_at`; it never rewrites a jobs store.
  - Added native cron interface preflight for `get_job`, `update_job`, `compute_next_run` and `get_due_jobs`.
  - Attested the bounded runner as `cron.scheduler_provider.InProcessCronScheduler` in `native-scheduled-tick` mode with a one-second check interval. Manual/forced/custom scheduler evidence is rejected.
  - Changed the two active and following idle cut spacing to real one-minute scheduled boundaries, reduced polling/slop and bounded run-evidence windows for the accelerated cadence, and filtered active native output to the observed report id.
  - Added truthful private-receipt and public-summary fields for production validation, accelerated expression, native update interface, accelerated timestamps and explicit non-production/non-elapsed-hour labels.
- `tests/test_telegram_monitor_cli_plugin.py`
  - Updated the injected live-shaped world to use minute-spaced cuts and native schedule attestations.
  - Added native-interface, sibling-job preservation, truthful-summary and forced-tick/custom-scheduler refusal coverage.
  - Updated native probe fixtures with the cron API surface used by the preflight.
- `specs/telegram-monitor/evidence/MON-D16.md`
  - This bounded evidence record.

Preserved unchanged: design and contract documents, prior evidence, the public harness option names and fixed count, production monitor implementation and schedule, D14/D14R/D15R behavior, private evidence/retained labs, runtime/profile/config/credentials, and unrelated state.

## Acceptance coverage

| Requirement | Check and observed result | Evidence location |
| --- | --- | --- |
| Lab-only native update | `test_d16_native_update_changes_only_the_private_lab_job` passed. A real temporary Hermes runtime store changed the owned job from `0 * * * *` to `* * * * *`, returned a recomputed `next_run_at`, and left an unrelated `0 * * * *` job unchanged. | `tests/test_telegram_monitor_cli_plugin.py`; `_lab_schedule_update` and `_LAB_SCHEDULE_UPDATE_PROBE` in `scripts/qualify_telegram_monitor.py` |
| Production shape and truthful lab labels | `test_live_preflight_and_full_run_without_external_effects` passed with production validation true, native interface `cron.jobs.update_job`, private-lab-only true, accelerated `* * * * *`, two timestamps one minute apart, and an idle timestamp one minute later. Public summary explicitly reports `production_hourly_evidence: false` and `elapsed_hour_evidence: false`. | `tests/test_telegram_monitor_cli_plugin.py`; public summary in `scripts/qualify_telegram_monitor.py` |
| No forbidden substitutes | `test_d16_schedule_evidence_rejects_manual_and_custom_substitutes`, `test_live_refuses_non_native_schedule_update_before_scheduler` and `test_live_refuses_custom_scheduler_evidence_before_smoke` passed. The live-shaped path refuses bad update/scheduler attestations before model/transport work; the static deterministic check rejects forced-fire content. | `tests/test_telegram_monitor_cli_plugin.py`; `_schedule_update_evidence_ok`, `_scheduled_evidence_ok`, `_check_lab_schedule_contract` |
| Existing monitor behavior | Focused monitor lane passed 320 tests. Existing runtime schedule/drift/DST/restart controls were retained and the full focused monitor suite remained green. | `tests/test_telegram_monitor_*.py` |
| Offline safety | `uv run --frozen python scripts/qualify_telegram_monitor.py --json` returned `ok: true`; all 12 deterministic checks passed, including `lab-schedule-contract`, with `external_effects: {"model_calls": 0, "telegram_sends": 0}`. | Command output; deterministic checks in `scripts/qualify_telegram_monitor.py` |

## Fail-before / pass-after

The modified focused test file was overlaid onto a clean scratch checkout of base `81d8cad` and run with the same provisioned runtime path. The base run produced **5 failures / 114 deselected**:

| Behavior-bearing test | Base observation | Candidate observation |
| --- | --- | --- |
| `test_live_preflight_and_full_run_without_external_effects` (receipt/labels and minute schedule) | **FAIL** at the fake scheduler attestation with `AttributeError: module 'qualify_telegram_monitor' has no attribute 'LAB_SCHEDULER_INTERVAL_SECONDS'` | **PASS** as part of the focused D16 run |
| `test_d16_schedule_evidence_rejects_manual_and_custom_substitutes` | **FAIL** with `AttributeError: module 'qualify_telegram_monitor' has no attribute '_schedule_update_evidence_ok'` | **PASS** |
| `test_d16_native_update_changes_only_the_private_lab_job` | **FAIL** with `AttributeError: module 'qualify_telegram_monitor' has no attribute '_lab_schedule_update'` | **PASS**; real temporary native store update and sibling preservation observed |
| `test_live_refuses_non_native_schedule_update_before_scheduler` | **FAIL** at the base fake scheduler with the missing `LAB_SCHEDULER_INTERVAL_SECONDS` attribute | **PASS**; refusal occurred before scheduler start and trigger |
| `test_live_refuses_custom_scheduler_evidence_before_smoke` | **FAIL** at the same missing interval attestation | **PASS**; refusal occurred before smoke |

The candidate command was:

```text
uv run --frozen python scripts/run_tests.py -- -q tests/test_telegram_monitor_cli_plugin.py -k 'd16 or non_native_schedule or custom_scheduler or live_preflight_and_full_run'
```

Observed candidate result: **5 passed, 114 deselected**.

## Verification commands and observed results

- Base ancestry and clean starting state: passed. `7d433b3` and `2aec2b7` were ancestors; log showed `81d8cad`, merge `828b736`, `2aec2b7`, `7d433b3`; initial status was clean.
- `uv run --frozen python scripts/qualify_telegram_monitor.py --json`: **PASS**, `ok: true`, 12/12 checks pass, zero model calls and zero Telegram sends; candidate revision `369b08a`.
- `uv run --frozen python scripts/run_tests.py -- -q tests/test_telegram_monitor_*.py`: **PASS**, 320 passed.
- `uv run --frozen python scripts/check_documentation.py`: **PASS**, `documentation validation passed`.
- `uv run --frozen mypy src/aether_agents`: **PASS**, no issues in 65 source files.
- Ruff check over the policy paths: **PASS**, `All checks passed!`.
- Ruff format check over the policy paths: **PASS**, `150 files already formatted`.
- Compileall over source, tests and policy scripts: **PASS**.
- `uv build`: **PASS**, wheel and source distribution built for `aether_agents-0.24.0`.
- `uv run --frozen python scripts/check_public_artifacts.py --root . --artifact dist/*.whl --artifact dist/*.tar.gz`: **FAIL with the two known pre-existing findings only**: `.aether/objective-contracts/oc_0084270d940c98d9/v1.md` `absolute-user-home` and `operator-desktop-layout`. No D16 path was reported; `dist/` was removed after the scan.
- `git diff --check`: **PASS**.
- Policy manifest emulation over the current heredoc file list and `git ls-files`: **PASS**, `377 = 377`, missing `[]`, extra `[]`.
- Full `uv run --frozen python scripts/run_tests.py`: attempted, but the concurrent shared host exhausted `/tmp` during unrelated fixture work and pytest terminated with `OSError: [Errno 28] No space left on device` after `129 failed, 1035 passed, 43 skipped, 6 errors`. This is an environment-capacity result, not treated as a green full-suite result; the focused monitor lane and all unit-specific checks passed. Supervisor should re-run the full suite on a capacity-stable integration environment.

No `--live` command was run by this unit, as required. The single accelerated live qualification and all external effects belong to terminal card `t_84c2812b`.

## Compatibility and residual risk

**Unit compatibility conclusion:** additive qualification-harness behavior only. The production monitor runtime and its fixed `0 * * * *` schedule are unchanged; deterministic existing monitor controls pass. This is unit-level compatibility evidence, not an aggregate release decision.

**Residual risk:** the accelerated lab's minute expression and timestamps are tested in the unit's injected orchestration plus the real temporary native cron-store update; the provisioned model/Telegram path and actual native scheduler/model/transport effects remain unobserved until the one authorized terminal live run. The product monitor still computes its natural hourly report cutoff; terminal live evidence must verify that the selected real minute boundaries yield the intended two active reports without pretending they represent elapsed hours. A live failure after lab job/scheduler/model/Telegram effects begin must stop the experiment with retained private evidence and no automatic rerun.
