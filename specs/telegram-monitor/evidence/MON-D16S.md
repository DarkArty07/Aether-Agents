# MON-D16S Implementation Evidence — internally consistent and cooperatively stoppable laboratory

**Unit:** D16S — correct the accelerated laboratory fixture/oracle state mismatch and failure-path shutdown ordering
**Task:** `t_491d068c`
**Objective Contract:** `oc_f8c9fc9320587cf3@v4`
**Base commit:** `5cdb308d155d7476a43f7adc4e96bf5c24b54485` (integrated D16+D16R tip)
**Candidate implementation commit:** `4e156e1` (`4e156e14e63d540128ebafb12409e3912e19f754`)
**Phase:** Implementer unit; **no live effect performed**. No `--live` run, model call, Telegram send, real laboratory/production job enablement, profile/config/credential/provider mutation, retained-laboratory cleanup, push, PR or issue mutation was performed. The scratch chain probe and the focused tests created and disabled only their own temporary laboratory roots under the system temporary directory.

## Source finding and measured defects

The MON-V4-INT finding attached to terminal card `t_84c2812b` measured two harness-internal failures on candidate `5cdb308` after external effects had begun. This unit re-read that finding and the private receipt `telegram-monitor-live-v5.json` (sha256 `6f0c8eabf70b7f321ed2ec2312c5f0687659bd030d37b6ebe3db42a344d2c7a6` — re-hashed read-only and identical to the finding's digest). The receipt's own errors are exactly:

- `scope-state` — "a synthetic work identity was not in the expected canonical state at the cut";
- `lab-scheduler-stop` — "the bounded native scheduler instance did not stop inside the bounded wait; the objective evidence is retained and the laboratory must be reconciled" (`retention.scheduler_stopped: false`).

The retained laboratory `20260911T125411Z-1181c8ac8baf` was inspected read-only: its monitor job `fa6bf983ab9a` is `enabled: false`, native `state: paused`, and it remains retained and inert; nothing was modified, deleted or cleaned.

1. **Fixture state could not satisfy its own smoke/boundary oracle.** The fixture passed `initial_status="running"` to native `hermes_cli.kanban_db.create_task`, but the shipped writer derives the row status itself (`blocked` → `blocked`, triage → `triage`, otherwise `ready`/`todo`). The measured collector output was therefore A pipeline `queued` while the oracle required `running`.
2. **Failure cleanup stopped the scheduler while its enabled job remained due every minute.** The stop bound was a scheduler-only 120 s per phase while a single in-flight run can include model narration plus delivery, so the process outlived the harness's wait and the receipt reported `lab-scheduler-stop`.

## Bounded implementation

### Fixture and shared scope oracle

- `scripts/telegram_monitor_lab.py:678-712` requires the shipped `claim_task` writer (`:704`) and the task-writer keywords the fixture uses, now including `session_affinity` and the native `project_id`; the pre-write gate therefore refuses a runtime that cannot express the corrected fixture.
- `scripts/qualify_telegram_monitor.py:1671-1675` declares project A's root as genuinely started (`running`) and project B's root as truthful `ready` beside its pending review case; `:1750` includes open `ready` roots in the between-cut transition. No SQL status row is fabricated.
- `scripts/qualify_telegram_monitor.py:3744-3745` passes the native project identity and the terminal-flow affinity to the shipped task writer; `:3773-3776` calls the shipped `claim_task` for the task declared `running`, which creates the real in-progress state. The fixture never writes task SQL.
- `scripts/qualify_telegram_monitor.py:2312-2402` adds `_scope_expectation_parts` and the deterministic evaluator `_evaluate_scope_expectations` (exact work identities, canonical states, collection gaps and item-level gaps). `:2622-2666` centralizes the four plans (`smoke`, `boundary-1`, `boundary-2`, `idle`); the live smoke/boundary path consumes the same builders at `:5264-5265`, `:5299` and `:5324`.

### Cooperative failure shutdown

- `scripts/qualify_telegram_monitor.py:197-207` derives the scheduler stop bound from the deadlines the lane already tolerates: `max(COLLECTION_DEADLINE_SECONDS, SMOKE_DEADLINE_SECONDS, BOUNDARY_SLOP)` = 900 s per cooperative/SIGTERM phase, instead of the unrelated fixed 120 s.
- Success path keeps its order: manual off (`:5483-5494`) → cooperative scheduler stop → retention verification.
- Failure path (`finally`, `:5512+`): `disable_lab_before_scheduler_stop` (`:5514-5568`) first calls the shipped control service with `ACTION_OFF`, requires a disabled result and requires the owned job observed `paused`; the guard at `:5570-5571` runs it whenever a scheduler or job identity exists and no verified off is recorded; only then does `_lab_scheduler_stop` run. The stop helper (`:4739-4771`) verifies exit through `_pid_alive` (`:4774`) on the recorded pid and still raises `lab-scheduler-stop` — recorded, not swallowed — if the process cannot be proven gone.

### Test-runner environment hygiene (found during this unit's own verification)

`scripts/run_tests.py` puts the exact Hermes baseline checkout first on the test process's `PYTHONPATH`. A laboratory child inherits `PYTHONPATH` by design (`scripts/telegram_monitor_lab.py`: `existing_pythonpath`, pre-existing behavior since `59a0c8f`; `_runtime_execute` forwards the caller's context). With the corrected fixture now requiring this fork's patched writer surface, a child that resolves the unpatched baseline checkout is *correctly* refused by the gate (`writer-parameter-missing:hermes_cli.kanban_db.create_task:session_affinity`). The live lane never runs with that shadow, so the tests must drive the runtime's own resolution:

- `tests/test_telegram_monitor_cli_plugin.py:7371-7377` (D15R fixture chain test) no longer forwards the runner's `PYTHONPATH` into the laboratory child context.
- `tests/test_telegram_monitor_cli_plugin.py:7523-7542` (`_make_d16r_test_profile`, shared by the D16S and D16R runtime tests) drops the runner's `PYTHONPATH` from the simulated provisioned context.

Without these two corrections the corrected fixture made two pre-existing tests fail **only under `scripts/run_tests.py`** (they pass in the focused lane); with them, base and candidate agree (see fail-before/pass-after below). No harness semantics changed.

## Acceptance coverage

| Obligation | Check and observed result | Evidence location |
| --- | --- | --- |
| Native fixture reaches the canonical smoke state | **PASS**: real scratch fixture through the provisioned runtime produced A `running`, B `review`, direct `turn_ended_unknown`; seeded counts 2 projects, 2 boards, 5 sessions, 8 tasks, 2 direct intervals. | `tests/test_telegram_monitor_cli_plugin.py:6301-6404`; scratch chain probe below |
| Corrected transition reaches the second plan | **PASS**: after the shipped transition the real collector produced A `completed`, B `completed`, direct `turn_ended_completed`, no collection gaps. | same test and chain probe |
| Idle plan is genuine and empty | **PASS**: after marker advancement the real collector produced zero items and zero gaps; `SourceCollection.idle` was true. | `tests/test_telegram_monitor_cli_plugin.py:6401` |
| Deterministic evaluator refuses a mismatch | **PASS**: a deliberate A expectation of `queued` raised `QualificationError` `scope-state` with observed `running`. | `tests/test_telegram_monitor_cli_plugin.py:6363-6369` |
| Same expectations cover every live plan | **PASS**: the focused test evaluates `smoke`, `boundary-1`, `boundary-2`, `idle` through `_scope_expectation_plans`; the live lane uses the same helper. | `:6301-6404`; script refs above |
| Failure cleanup ordering | **PASS**: the fake live failure records exactly one `lab_control:off` before `lab_scheduler_stop`, `enabled_after_off=false`, `job_paused=true`, `scheduler.stopped=true`. | `tests/test_telegram_monitor_cli_plugin.py:3422-3445` |
| Native writer gate | **PASS**: the generated native-probe and real-chain tests pass with the added claim interface/keywords; a missing writer is refused before seeding. | `scripts/telegram_monitor_lab.py:678-712`; focused lane |
| Runner-condition robustness | **PASS**: agent-runtime and D15R/D16R tests that drive real laboratory children pass under the exact `scripts/run_tests.py` environment, matching base. | see fail-before/pass-after |

## First-hand scratch chain probe

Drive: `_lab_plan → lab_preflight → lab_create → lab_context_preflight → _scope_manifest → _write_scope_projects → lab_fixture → environment_gaps → lab_control(ACTION_ON)` plus the shared four-plan expectation evaluation, on a temporary root outside every Git worktree and outside the operator evidence directory (system temporary directory), with synthetic test-owned configuration/access, no model, no Telegram transport and no scheduler. The probe disabled its scratch job through the shipped control service in `finally` and removed only its own temporary root.

Observed result (`/tmp/d16s_chain_probe.py`, re-run on this candidate):

- `lab_preflight: []` · `lab_create: true` · `lab_context_preflight: []`
- `lab_fixture: {projects: 2, boards: 2, sessions: 5, tasks: 8, direct: 2}` · `environment_gaps: []`
- `lab_control(ACTION_ON): ok=true, job_created=true, production_schedule="0 * * * *"`
- `expectation_plans_passed: ["smoke", "boundary-1", "boundary-2", "idle"]`
- before states `["review", "running", "turn_ended_unknown"]`; after states `["completed", "completed", "turn_ended_completed"]`
- idle: `0` items, `[]` gaps; transition completed: `3`; probe result: `ok=true`

This is a pre-effect scratch probe only; it is not live qualification or production acceptance.

## Fail-before / pass-after

Baseline observations were taken against a detached scratch checkout of exactly `5cdb308` (`/tmp/d16s-base`); the baseline checkout was not edited.

| Behavior-bearing check | Base observation | Candidate observation |
| --- | --- | --- |
| Real fixture state/oracle | **FAIL**: native fixture/collector reported `scope-state: expected running, observed queued`; seeded counts unchanged 2/2/5/8/2. | **PASS**: `test_d16s_real_fixture_expectations_cover_smoke_boundaries_and_idle`; A `running`, B `review`, direct unknown. |
| New deterministic evaluator | **FAIL**: base module has no `_evaluate_scope_expectations`; `AttributeError: module 'qualify_telegram_monitor' has no attribute '_evaluate_scope_expectations'`. | **PASS**: evaluator checks all four plans and rejects a deliberate `queued` mismatch with `scope-state`. |
| Failure-path shutdown order | **FAIL**: base fake orchestration stopped after `scheduler-evidence` with calls `[..., lab_scheduler_start, lab_scheduler_stop, lab_release, write_output]` and no `lab_control:off`; `off_before_scheduler_stop=false`. | **PASS**: `test_failure_path_disables_lab_before_stopping_scheduler`; off precedes stop and the scheduler stop is recorded. |
| Existing fake-world orchestration | **PASS**: the existing success-path world stays green (manual off before stop, retention order). | **PASS**: existing tests plus the new failure-order and real-fixture tests. |
| D15R fixture chain under `scripts/run_tests.py` | **PASS** (baseline). | **PASS after the hygiene correction**; before it, the corrected fixture raised `lab-fixture` with `fixture-tasks: TypeError` ("create_task() got an unexpected keyword argument 'session_affinity'") because the runner's baseline checkout shadowed the runtime inside the lab child. |
| D16R/D16S runtime tests under `scripts/run_tests.py` with `AETHER_HERMES_PYTHON` set | **PASS** on base (the added writer requirement did not exist). | **PASS after the hygiene correction**; before it, the gate truthfully refused the shadowed runtime (`writer-parameter-missing:…:session_affinity`). |

Base behaviors were reproduced first-hand in this attempt with external temporary probe scripts against the detached checkout; only scratch roots and synthetic credentials were used.

## Verification commands and observed results

- `git log --oneline -4` + `git status --short`: **PASS** at start; tip `5cdb308`, clean tree.
- Focused monitor lane (`AETHER_HERMES_PYTHON=<provisioned candidate runtime> PYTHONPATH=. uv run --frozen pytest tests/test_telegram_monitor_cli_plugin.py tests/test_telegram_monitor_sources.py tests/test_telegram_monitor_delivery.py tests/test_telegram_monitor_reporting.py tests/test_telegram_monitor_runtime.py tests/test_telegram_monitor_state.py -q`): **PASS**, `331 passed` (final content).
- Deterministic lane (`TMPDIR=/tmp uv run --frozen python scripts/qualify_telegram_monitor.py --json`): **PASS**, `ok: true`, unchanged 12-check set, `external_effects: {"model_calls": 0, "telegram_sends": 0}`.
- Chain probe (`uv run --frozen python /tmp/d16s_chain_probe.py`, scratch root under `/tmp`): **PASS**, four plans green, no model/send/scheduler.
- `python3 scripts/check_documentation.py`: **PASS**, `documentation validation passed`.
- `uv run --frozen mypy src/aether_agents`: **PASS**, no issues in 65 files.
- Policy-job Ruff paths (check + format): **PASS**, `All checks passed!` and `150 files already formatted`.
- Policy-job compileall path list: **PASS**, no errors.
- `uv build --out-dir /tmp/d16s-dist`: **PASS**, wheel + sdist `aether_agents-0.24.0`.
- `scripts/check_public_artifacts.py --root . --artifact <wheel> --artifact <sdist>`: **only the two documented pre-existing rows** — `.aether/objective-contracts/oc_0084270d940c98d9/v1.md: absolute-user-home` and `: operator-desktop-layout`; no D16S path reported.
- `python3 scripts/run_tests.py` (controlled: `AETHER_HERMES_PYTHON` unset): **candidate** `9 failed, 1514 passed, 68 skipped, 18 errors`; **base** (detached `5cdb308`, same command) `9 failed, 1510 passed, 70 skipped, 18 errors`. The failed sets are **identical**: the three Graphify failures + 18 Graphify errors ("The configured Graphify version is not qualified." — the CI installs a hash-locked disposable component absent here), `test_public_artifacts` (the two documented rows), `test_same_card_phase_predicates`, and four monitor tests (`test_exact_packaged_precheck_child_hands_the_lease_to_the_reporter`, `test_offline_qualification_makes_no_model_or_sender_call`, `test_offline_receipt_is_written_to_the_established_private_target`, `test_offline_workspace_collision_is_skipped_for_a_fresh_run_owned_name`) whose child-runner environment matches CI only. The pass/skip delta (4 more passes, 2 fewer skips on the candidate) is explained by this unit's two added tests (one pass, one skip without `AETHER_HERMES_PYTHON`) and by the detached base checkout sitting outside the repository tree, where three runtime-fallback tests cannot resolve `home/.venv-hermes` and therefore skip. No failure is attributable to D16S.
- Environment note: during the comparison the system temporary filesystem filled to 100% (`/tmp`, 16 GB) and one intermediate base re-run aborted with mass `ENOSPC` failures. Pytest's own temporary root (8 GB) was removed (it is pytest scratch, not evidence) and the controls above were re-run cleanly; the retained laboratory, the private evidence directory and every prior receipt were untouched.
- `git diff --check 5cdb308...HEAD`: **PASS**, exit 0 (no whitespace errors), run after the bounded commit `4e156e1`.
- Policy manifest emulation (index manifest + spec-manifest checks from `.github/workflows/policy.yml`, run with this evidence file staged): **PASS**, exit 0; non-`specs/` manifest `expected=377 actual=377`, `missing=[]`, `extra=[]`; the tracked spec manifest is non-empty and every entry passed the mode/stage/extension/secret-like checks; the `VERSION` shape, forbidden `schemas/`/`home/<private-dirs>/` paths and legacy-name checks also passed.
- Retained laboratory re-check (read-only): job `fa6bf983ab9a` still `enabled: false`, `state: paused`; production scope not touched by this unit.

## Preservation, compatibility and residual risk

Preserved unchanged: the public harness CLI and fixed `--wait-hourly-boundaries 2`, production schedule `0 * * * *`, D14/D14R/D15R/D16/D16R semantics, the laboratory profile-home convention and lab-scoped plugin loading, every other accepted monitor module (no `src/aether_agents/monitor` change), the private evidence directory and receipts, the operator registry/boards/sessions/jobs/state, the retained laboratory roots including `20260911T125411Z-1181c8ac8baf`, blocked v2 cards, v3 board/evidence and issue #367. No new CLI option; the fixed boundary count stays 2; no clock change, fake scheduler or manual tick.

**Unit compatibility conclusion:** the change is confined to the qualification fixture/oracle, its failure-path shutdown ordering and the tests that drive them. Production monitor behavior and the production cron expression are unchanged; the focused monitor lane and the controlled repository comparison show no D16S-attributable failure. This is unit-level compatibility evidence, not an aggregate release or publication decision.

**Residual risk:** the corrected laboratory has still never crossed its first real model/Telegram cut. The next live action is one separately authorized accelerated attempt on this reviewed candidate; if external effects begin and it fails, the laboratory job is disabled through the shipped control service first, the native scheduler is then stopped cooperatively with retained evidence and a proven-pid exit, and no automatic rerun is authorized. Independent Supervisor review must re-drive the scratch chain and the deterministic evaluator on the committed candidate.
