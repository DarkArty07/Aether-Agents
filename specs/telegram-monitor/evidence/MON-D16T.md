# MON-D16T Implementation Evidence — truthful laboratory stop detection and paced accelerated start

**Unit:** D16T — make the accelerated laboratory's stop detection truthful and keep a mistimed start from consuming a live attempt
**Task:** `t_8de4ade1`
**Objective Contract:** `oc_f8c9fc9320587cf3@v4`
**Base commit:** `c760aefad0599c959702684c283c751e5f6f1d43` (integrated reviewed tip: D16 `98fce3e` + D16R `5cdb308` + D16S `c760aef`)
**Candidate implementation commit:** `0f8a741762af7a9ad8613f8f143ca4170a7f1fc3` (`0f8a741`)
**Phase:** Implementer unit; **no live effect performed**. No `--live` run, model call, Telegram send, real laboratory/production job enablement, scheduler started outside a test, profile/config/credential/provider mutation, retained-laboratory cleanup, push, PR or issue mutation was performed.

## Source findings and measured defects

Two defects were measured on the terminal phase's live attempts and findings:

1. **Defect A: Stop verifier treats an exited child as a running child (blocks clean live acceptance)**
   - *Measurement and attribution:* In attempt v6 (and previously v5), `_lab_scheduler_stop` polled `_pid_alive(pid)`, which only executed `os.kill(pid, 0)`. When the child exited cooperatively on `scheduler-stop` (watched by `_LAB_SCHEDULER_BODY` every 0.5 s), the child process entered zombie state (`Z` in `/proc/<pid>/stat`). Because the `Popen` handle was discarded upon return from `_lab_scheduler_start`, nothing in the harness reaped the child. `os.kill(pid, 0)` returned success on the zombie process, so the harness concluded the runner was still alive, burned the full stop wait (`LAB_SCHEDULER_STOP_SECONDS`), sent SIGTERM (which a zombie ignores), waited another bound, and raised `lab-scheduler-stop`.
   - *Corrected attribution of v5 stop error:* In v5, the receipt ended with `lab-scheduler-stop` after an abort, which was initially read as "the runner outlived the bound while enabled and due every minute". That reading is superseded by the zombie-detection evidence: attempt v6 wrote the stop file 1.5 s after child readiness, the child exited cleanly before the minute boundary (verified by `last_run_at: None`, no snapshot, no deliveries), yet remained a zombie in the process table. Because `record["ok"] = bool(record.get("ok")) and not record["errors"]`, this defect alone made even a successful acceptance run record `ok: false`.

2. **Defect B: Mistimed start consumes a live attempt with zero effects**
   - *Measurement and attribution:* Attempt v6 started at 2026-09-11T15:56:46Z (14 s before the next minute boundary). Enable completed at 15:56:52.4Z; the native scheduler attested at 15:56:55.7Z. `_smoke_phase` evaluated `lead = (cut_one - now).total_seconds()`, where `cut_one` was `15:57:00` and `now` was `15:56:55.7`, leaving ~4.3 s of lead. Because `lead < SMOKE_MIN_LEAD_SECONDS` (5.0 s), the guard refused with `smoke-window` before any model call, Telegram send, or production effect occurred.

## Bounded implementation

Diff is strictly confined to `scripts/qualify_telegram_monitor.py` and `tests/test_telegram_monitor_cli_plugin.py`.

### Truthful stop detection and process reaping (Defect A)

- `scripts/qualify_telegram_monitor.py:4766`: `_lab_scheduler_start` retains the `subprocess.Popen` handle under `"process": process` in the returned scheduler mapping.
- `scripts/qualify_telegram_monitor.py:5380-5382`: `_live_run` excludes the non-serializable `"process"` object from `record["scheduler"]` (`{key: value for key, value in scheduler.items() if key != "process"}`), preserving JSON serialization of the receipt.
- `scripts/qualify_telegram_monitor.py:4789-4813`: `_lab_scheduler_stop` implements `_check_stopped()`. If `process.poll()` is available, it polls the process, reaping the child and obtaining its true exit code. If `pid` is a child of the harness, `os.waitpid(pid, os.WNOHANG)` reaps the zombie and extracts the exit status.
- `scripts/qualify_telegram_monitor.py:4863-4882`: `_pid_alive(pid)` checks `os.kill(pid, 0)` and reads `/proc/{pid}/stat`; if the process state is `"Z"` (zombie) or `"X"` (dead), it returns `False`.
- `scripts/qualify_telegram_monitor.py:4816-4859`: Cooperative stop-file signaling remains first (preserving D16S off-before-stop ordering); on cooperative exit, `stopped: True`, `cooperative: True`, `exit_code: 0`, and `exit_status: 0` are returned immediately without burning the bound. If the process ignores both the stop file and SIGTERM, `_lab_scheduler_stop` raises `QualificationError("lab-scheduler-stop")` fail-closed. Open pipes (`stdout`, `stderr`) are closed.
- `scripts/qualify_telegram_monitor.py:5681-5705`: `_live_run` records `stopped`, `cooperative`, `exit_code`, and `exit_status` into `record["scheduler"]`.

### Paced start avoiding mistimed attempt consumption (Defect B)

- `scripts/qualify_telegram_monitor.py:197-204`: Constants `SMOKE_START_MIN_LEAD_SECONDS = 25.0` and `SMOKE_ACCELERATE_MIN_LEAD_SECONDS = 15.0` define the lead thresholds.
- `scripts/qualify_telegram_monitor.py:2101-2127`: `_wait_for_minute_lead(backends, min_lead_seconds)` computes remaining seconds in the current minute (`60.0 - (now.second + now.microsecond / 1_000_000)`). If remaining lead is below the threshold, it sleeps (using `backends.sleep`) until just after the next minute boundary.
- `scripts/qualify_telegram_monitor.py:5233-5240`: `_live_run` invokes `_wait_for_minute_lead(backends, SMOKE_START_MIN_LEAD_SECONDS, ...)` before enabling the lab monitor.
- `scripts/qualify_telegram_monitor.py:5296-5303`: `_live_run` invokes `_wait_for_minute_lead(backends, SMOKE_ACCELERATE_MIN_LEAD_SECONDS, ...)` before accelerating the schedule via `cron.jobs.update_job`.
- `scripts/qualify_telegram_monitor.py:2130-2138`: The existing fail-closed check in `_smoke_phase` (`lead < SMOKE_MIN_LEAD_SECONDS`) remains untouched as the backstop; the pacing makes it unreachable merely from an unlucky operator start second.

## Acceptance coverage

| Obligation | Check and observed result | Evidence location |
| --- | --- | --- |
| Cooperative child exit detected without consuming bound | **PASS**: Real child process exiting on stop file detected in <0.05 s, reaped, exit code recorded (`stopped: true, cooperative: true, exit_code: 0, exit_status: 0`). | `tests/test_telegram_monitor_cli_plugin.py:7626-7662` |
| True exit status recorded in receipt | **PASS**: `receipt["scheduler"]["exit_code"] == 0` and `receipt["scheduler"]["cooperative"] == true` recorded. | `tests/test_telegram_monitor_cli_plugin.py:7655-7656`, `scripts/qualify_telegram_monitor.py:5697-5700` |
| Unresponsive child fails closed | **PASS**: Child ignoring stop file and SIGTERM times out after bound and raises `lab-scheduler-stop`. | `tests/test_telegram_monitor_cli_plugin.py:7665-7697` |
| Mistimed start reaches valid smoke window | **PASS**: Start at second 46 (attempt v6 condition) sleeps 14.1 s to next minute boundary before enable, reaches smoke with runway, triggers smoke (`trigger_calls: 1`), and avoids `smoke-window`. | `tests/test_telegram_monitor_cli_plugin.py:7700-7726` |
| Smoke-window backstop retained | **PASS**: Direct call to `_smoke_phase` with lead < 5 s raises `smoke-window`. | `tests/test_telegram_monitor_cli_plugin.py:3992-4008` |
| Offline deterministic lane | **PASS**: `ok: true`, 12/12 checks, `external_effects: {model_calls: 0, telegram_sends: 0}`. | `TMPDIR=/tmp uv run --frozen python scripts/qualify_telegram_monitor.py --json` |
| Focused monitor lane | **PASS**: 329 passed, 5 skipped (without `AETHER_HERMES_PYTHON`). | `PYTHONPATH=. uv run --frozen pytest tests/test_telegram_monitor_*.py` |

## Fail-before / pass-after

Reproduced first-hand against a detached scratch checkout of base `c760aef` (`/tmp/scratch_base_c760aef`):

| Behavior-bearing check | Base `c760aef` observation | Candidate `0f8a741` observation |
| --- | --- | --- |
| Cooperative exit stop detection (`test_d16t_lab_scheduler_stop_detects_cooperative_exit_and_records_status`) | **FAIL**: `QualificationError: the bounded native scheduler instance did not stop inside the bounded wait; the objective evidence is retained and the laboratory must be reconciled` (`code: lab-scheduler-stop`). Process was a zombie (`state: Z`), `_pid_alive` returned `True`, bound was consumed. | **PASS**: `stopped: True`, `cooperative: True`, `exit_code: 0`, `exit_status: 0`. Process reaped cleanly in <0.05 s. |
| Unresponsive child fail-closed (`test_d16t_lab_scheduler_stop_fails_closed_when_child_ignores_stop_and_sigterm`) | **PASS**: Child ignoring both stop file and SIGTERM fails closed with `QualificationError("lab-scheduler-stop")`. | **PASS**: Preserved fail-closed behavior; raises `QualificationError("lab-scheduler-stop")`. |
| Mistimed start pacing (`test_d16t_harness_start_in_last_seconds_reaches_valid_smoke_window`) | **FAIL**: `assert False where False = any("sleep:14.1" in call for call in backends.calls)`. Base did not wait before enable, reaching smoke with inadequate lead. | **PASS**: `sleep:14.1` called before enable, `world["backends"].trigger_calls == 1`, `error.value.code != "smoke-window"`. |

## Verification commands and observed results

- `git log --oneline -4` + `git status`: **PASS** at start; tip `c760aef`, clean tree.
- Deterministic lane (`TMPDIR=/tmp uv run --frozen python scripts/qualify_telegram_monitor.py --json`): **PASS**, `ok: true`, unchanged 12 checks, `external_effects: {"model_calls": 0, "telegram_sends": 0}`.
- Focused monitor lane (`PYTHONPATH=. uv run --frozen pytest tests/test_telegram_monitor_*.py`): **PASS**, `329 passed, 5 skipped in 23.02s`.
- Full runner (`uv run --frozen python scripts/run_tests.py`): **PASS**, `2 failed, 1515 passed, 69 skipped in 274.18s`. The failed set is **identical** to base:
  1. `tests/test_public_artifacts.py::test_tracked_public_surface_contains_no_operator_paths` (documented pre-existing `oc_0084270d940c98d9/v1.md` rows).
  2. `tests/test_same_card_phase_predicates.py::test_initial_review_requires_an_independent_reviewer` (documented pre-existing).
  Candidate pass count increased by +3 (1512 → 1515), exactly matching the 3 added D16T tests.
- `uv run --frozen mypy src/aether_agents`: **PASS**, no issues in 65 source files.
- `uv run --frozen python scripts/check_documentation.py`: **PASS**, documentation validation passed.
- `uv run --frozen ruff check scripts/qualify_telegram_monitor.py tests/test_telegram_monitor_cli_plugin.py`: **PASS**, clean.
- `uv run --frozen ruff format --check scripts/qualify_telegram_monitor.py tests/test_telegram_monitor_cli_plugin.py`: **PASS**, 2 files already formatted.
- `python3 -m compileall src scripts tests`: **PASS**, all compiled clean.
- `uv build`: **PASS**, successfully built `dist/aether_agents-0.24.0.tar.gz` and `dist/aether_agents-0.24.0-py3-none-any.whl`.
- `git diff --check c760aef...HEAD`: **PASS**, exit 0, no whitespace or formatting errors.
- `python3 scripts/check_public_artifacts.py`: **PASS**, only the two documented pre-existing `oc_0084270d940c98d9/v1.md` rows.
- Policy manifest emulation (verbatim step from `.github/workflows/policy.yml`): **PASS**, exit 0 (`Diff exit: 0`), 377 paths exact match.

## Preservation, compatibility and residual risk

- **Preserved unchanged:** Every design document, Objective Contract `oc_f8c9fc9320587cf3@v4`, all prior evidence records, harness public CLI (`--json`, `--live`, `--wait-hourly-boundaries 2`, `--output`), production schedule `0 * * * *`, `src/aether_agents/**` (zero product code changes), D14/D14R/D15R/D16/D16R/D16S semantics, retained laboratories (`20260911T125411Z-1181c8ac8baf`, `20260911T155646Z-8cd41cdb6427`), private evidence directory, and operator registry/boards/sessions/jobs/state.
- **Unit compatibility conclusion:** The change is confined to qualification harness stop detection, process reaping, start pacing, and associated test coverage. Production behavior is unaffected.
- **Residual risk:** The laboratory has still never crossed a real model or Telegram cut. The next live attempt remains the single authorized attempt on terminal card `t_84c2812b`; any failure after external effects begin stops the experiment with durable evidence and no automatic rerun.
