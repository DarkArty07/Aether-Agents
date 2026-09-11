# MON-D14R Implementation Evidence — production module chain gating before laboratory creation and stale mapping refusal

**Unit:** D14R preflight module-chain gating and stale editable-mapping refusal
**Task:** `t_a28871a5`
**Objective Contract:** `oc_f8c9fc9320587cf3@v3` (`.aether/objective-contracts/oc_f8c9fc9320587cf3/v3.md`, SHA-256 `f21facaf58af20a2d0595cdaa927a99ca6336e5b14b5d073ec3501bbfbf7f47c`)
**Source:** Morfeo resolution on card `t_b8077e66` (2026-09-10 21:45, after operational recovery of issue #399)
**Base commit:** `cf8cf3dee85bdf9b8e6c7802629ebcb4456afc38`
**Phase:** implementer unit; **no live effect performed** — no `--live` run, no model call, no Telegram send, no scheduler start, no profiler/registry mutation, no profile/config/credential/provider change, no Hermes patch, no modification of the recovered runtime, no cleanup of the retained lab root or the failed receipt.

## Scope and changed paths

- `scripts/qualify_telegram_monitor.py` — updated `_LAB_NATIVE_PROBE` to execute the fixture's own import order and resolve the production module chain (`hermes_state` → `SessionDB` / writer surface and artifact) before `cron.*` or `gateway.*` imports in both preflight (`lab_root=None`) and laboratory (`lab_root` provided).
- `tests/test_telegram_monitor_cli_plugin.py` — added 5 focused D14R test functions covering controlled stale-mapping reproduction and preflight refusal before lab creation, in-laboratory gate unmasking, preflight SessionDB writer surface validation, probe import order verification, and preserved v3 failed attempt receipt integrity.
- `docs/guides/telegram-monitor.md` — updated the read-only preflight and in-laboratory gate descriptions with D14R module chain resolution and fixture import order details.
- `CHANGELOG.md` — added entry under `[Unreleased]` for the D14R qualification preflight correction.
- `specs/telegram-monitor/evidence/MON-D14R.md` — this portable evidence file.

Preserved unchanged: production `src/`, all design specifications in `specs/telegram-monitor/{spec,plan,quickstart,qualification-isolation,research,tasks}.md`, Objective Contracts `v1.md`, `v2.md`, `v3.md`, prior evidence records (`MON-06.md`, `MON-D14.md`), root `AGENTS.md`, and `.github/workflows/policy.yml` (manifest list exact at 376 files).

## Reproduction of defect and corrected behavior

### Defect observed in the authorized live attempt on `cf8cf3d`

In the single authorized live attempt on `cf8cf3dee85bdf9b8e6c7802629ebcb4456afc38`, the harness failed at `lab-fixture` with `["fixture-imports: ModuleNotFoundError"]` (retained failed receipt `telegram-monitor-live-v3.json` SHA-256 `c23096fe793fd2263a2f59525b23799729b64eb3f61b9803932ae9b9496b79e8`, console log `live-run-v3-console.log` SHA-256 `a6046560aedbdc6d47d209010baa2e9c63ee1ae66c8a841f274a88347e81189d`).

**Root Cause:**
1. In the provisioned runtime, the editable-install mapping was stale for the newly added `hermes_state_compaction` module. In any fresh Python process that imported `hermes_state` early, `import hermes_state` failed with `ModuleNotFoundError`; it succeeded only when an earlier import (such as `cron.jobs` or `cron.scheduler_provider`) had already bootstrapped the Hermes source tree onto `sys.path`.
2. In the pre-correction harness (`cf8cf3d`), the read-only preflight (`_lab_preflight`, with `lab_root=None`) did not import or resolve `hermes_state` or the writer surface at all (they were guarded under `if LAB_ROOT_JSON:`). Thus, the preflight passed (`problems = []`), and the private laboratory root was created on disk.
3. The in-laboratory gate (`_lab_context_preflight`, with `lab_root` set) imported `from cron.scheduler_provider import InProcessCronScheduler` at line 2890 *before* resolving writers at line 2981. This early `cron` import bootstrapped `sys.path`, masking the stale mapping and allowing the in-lab writer probe to pass.
4. Next, `_lab_fixture` ran `_LAB_FIXTURE_PROBE` in a fresh child process. That probe began directly with `from hermes_state import SessionDB` without prior `cron` bootstrap, failing immediately with `["fixture-imports: ModuleNotFoundError"]`.
5. Gate success therefore failed to imply fixture importability, and the refusal occurred after the private root had already been created.

### Controlled reproduction on minimal native tree

To reproduce this deterministically without altering the recovered operator runtime, a controlled minimal native tree was synthesized where `hermes_state.py` requires `cron.scheduler_provider` to be imported first:
- `hermes_state.py`: raises `ModuleNotFoundError("No module named 'hermes_state_compaction'")` unless `_HERMES_BOOTSTRAPPED` is present in `sys.modules`.
- `cron/scheduler_provider.py`: sets `sys.modules["_HERMES_BOOTSTRAPPED"] = True` on import.

**Pre-correction candidate (`cf8cf3d`) observed outcome:**
```json
{
  "reached_fixture": false,
  "reached_transition": false,
  "phase1_problems": [],
  "root_after_phase1": false,
  "created": true,
  "gate_problems": [],
  "gate_writers": ["hermes_cli.kanban_db.complete_task", ...],
  "gate_artifacts": [...],
  "destination_matches": true,
  "driver_error": "QualificationError: the synthetic laboratory scope could not be materialized through the shipped writers; the laboratory root is retained for reconciliation"
}
```
*Result:* Read-only preflight passed (`phase1_problems: []`), laboratory was created (`created: true`), in-laboratory gate passed (`gate_problems: []`, masked by `cron`), and execution failed at `lab-fixture` with the lab root already created on disk.

**Corrected candidate (D14R) observed outcome:**
```json
{
  "reached_fixture": false,
  "reached_transition": false,
  "phase1_problems": [
    "provisioned-fixture-imports: ModuleNotFoundError",
    "provisioned-writer-interface-missing:hermes_state.SessionDB.create_session",
    "provisioned-writer-interface-missing:hermes_state.SessionDB.set_session_title",
    "provisioned-writer-artifact-missing:hermes_state"
  ],
  "root_after_phase1": false
}
```
*Result:* Harness refuses immediately at the read-only preflight with bounded problem codes. The laboratory creation is never invoked (`created: false`), no laboratory directory is created on disk, no credential is acquired, refreshed, injected into the reference probe, copied into the lab root or the receipt, no credential is used, and no model or send effect is made. Note that the pre-existing D14 access collection (`_lab_access` → `telegram_monitor_lab.collect_access`) still performs its local read of the provisioned profile environment file before the chain check; that local read is pre-existing, unchanged, and within D14 access resolution scope.

## D14R Implementation Details

1. **Exact production module chain gating in read-only preflight:**
   - In `_LAB_NATIVE_PROBE`, before any `cron.*` or `gateway.*` module is imported, the harness exercises the exact module chain used by the fixture and production:
     ```python
     try:
         from aether_agents.monitor import runtime as monitor_runtime
         from aether_agents.monitor.store import MonitorStore
         from aether_agents.observation.context import ProjectRegistry
         from hermes_cli import kanban_db, projects_db
         from hermes_state import SessionDB
     except Exception as error:
         payload["problems"].append(f"fixture-imports: {type(error).__name__}")
     ```
   - In both preflight and laboratory variants, the probe also resolves the writer surface backed by `hermes_state` (`SessionDB.create_session` with parameter validation, `SessionDB.set_session_title`) and verifies the readable module artifact digest for `hermes_state`.
   - If any import or writer interface check fails, bounded problem codes are appended to `payload["problems"]` (`fixture-imports: <Error>`, `writer-interface-missing:<name>`, `writer-parameter-missing:<name>:<param>`, `writer-artifact-missing:<module>`).
   - In `_lab_preflight`, these propagate under the `provisioned-` prefix and raise `QualificationError("lab-preflight", ...)` before `_lab_create` is reached.

2. **In-laboratory gate unmasking:**
   - The in-laboratory probe body executes the fixture's import order *first*, before `cron.scheduler_provider` or `gateway.config` can bootstrap `sys.path`.
   - Gate success therefore strictly implies fixture importability.

3. **Preservation of reviewed D14 semantics:**
   - `HERMES_HOME` normalization continues to accept multi-profile root and exact `profiles/morfeo` forms, rejecting invalid/ambiguous/linked/relative candidates.
   - The reference probe continues to invoke `load_hermes_dotenv()` before `load_gateway_config()`.
   - Negative control against injected lab access remains intact.
   - All machine paths and secret values remain completely excluded from public artifacts.

## Acceptance Criteria Mapping

| Requirement / AC | Check | Observed Result | Evidence Location |
| --- | --- | --- | --- |
| D14R Stale mapping preflight refusal | `test_d14r_stale_mapping_reproduction_refuses_at_preflight_before_lab_created` | PASS: Stale mapping refuses at read-only preflight with bounded codes (`provisioned-fixture-imports`, `provisioned-writer-interface-missing`); `created=false`, no lab root on disk | `tests/test_telegram_monitor_cli_plugin.py:6204` (`test_d14r_stale_mapping_reproduction_refuses_at_preflight_before_lab_created`) |
| D14R In-lab gate unmasked by cron | `test_d14r_in_lab_gate_exercises_fixture_import_order_unmasked_by_cron` | PASS: In-lab probe reports `fixture-imports: ModuleNotFoundError` and writer missing even with `cron` present in tree | `tests/test_telegram_monitor_cli_plugin.py:6225` (`test_d14r_in_lab_gate_exercises_fixture_import_order_unmasked_by_cron`) |
| D14R Preflight SessionDB writer check | `test_d14r_preflight_refuses_missing_hermes_state_writer_surface` | PASS: Dropping `create_session` causes bounded refusal `provisioned-writer-interface-missing:hermes_state.SessionDB.create_session` before lab creation | `tests/test_telegram_monitor_cli_plugin.py:6244` (`test_d14r_preflight_refuses_missing_hermes_state_writer_surface`) |
| D14R Native probe import order | `test_d14r_native_probe_body_executes_fixture_imports_before_cron_and_gateway` | PASS: `from hermes_state import SessionDB` strictly precedes `InProcessCronScheduler` and `load_gateway_config` in probe body; asserts identical import chain order to `_LAB_FIXTURE_PROBE` | `tests/test_telegram_monitor_cli_plugin.py:6262` (`test_d14r_native_probe_body_executes_fixture_imports_before_cron_and_gateway`) |
| D14R Preserved v3 failure receipt | `test_d14r_preserved_v3_failed_receipt_and_console_log_unchanged` | PASS: Preserved v3 receipt SHA-256 `c23096fe...` and console log `a6046560...` unchanged | `tests/test_telegram_monitor_cli_plugin.py:6299` (`test_d14r_preserved_v3_failed_receipt_and_console_log_unchanged`) |
| D14 Preserved prior refusal receipt | `test_d14_preserved_prior_refusal_receipt_and_log_unchanged` | PASS: Preserved v2 receipt SHA-256 `eb2f3ad3...` and log `5a9ca1fe...` unchanged | `tests/test_telegram_monitor_cli_plugin.py:6154` (`test_d14_preserved_prior_refusal_receipt_and_log_unchanged`) |
| D14 Destination digest parity | `test_d14_target_digest_equality_and_no_access_values` | PASS: Reference probe and laboratory probe destination digests match (`4e7c5b38...`), no secrets leaked | `tests/test_telegram_monitor_cli_plugin.py:6055` (`test_d14_target_digest_equality_and_no_access_values`) |
| D14 Runtime reference probe | `test_d14_runtime_reference_destination_probe_matches_gateway_context` | PASS: Reference probe on recovered runtime resolves `36007c9a8b0f8394...` | `tests/test_telegram_monitor_cli_plugin.py:6100` (`test_d14_runtime_reference_destination_probe_matches_gateway_context`) |
| Healthy runtime preflight rehearsal | `_lab_preflight` on recovered runtime | PASS: `problems=[]`, profile digest `de71053213ebdde16a6a1e36c89f3407c2f0a08cdfbe080ff84035fcd0fdab2a`, destination digest `36007c9a8b0f839416989e6aa06b2d8225c11142837fc5539cf8a33b59935f5f` | Rehearsal command |
| Deterministic offline lane | `uv run --frozen python scripts/qualify_telegram_monitor.py --json` | PASS: 11/11 checks pass, 0 model calls, 0 Telegram sends, `ok=true` | `scripts/qualify_telegram_monitor.py:884` |

### Per-Test Fail-Before / Pass-After Mapping (Candidate vs Base `cf8cf3d`)

| Test Function | Pre-correction (`cf8cf3d`) Result | Corrected Candidate (D14R) Result | Observed Semantics |
| --- | --- | --- | --- |
| `test_d14r_stale_mapping_reproduction_refuses_at_preflight_before_lab_created` | FAIL (exit code 3) | PASS (exit code 2) | Pre-correction: preflight passed (`phase1_problems: []`), laboratory created on disk (`created: true`), in-lab gate passed (`gate_problems: []`, masked by `cron`), fixture child failed with `QualificationError: the synthetic laboratory scope could not be materialized through the shipped writers`. Corrected: refuses fail-closed at read-only preflight (`phase1_problems: ["provisioned-fixture-imports: ModuleNotFoundError", "provisioned-writer-interface-missing...", "provisioned-writer-artifact-missing..."]`), `created: false`, zero laboratory root created on disk. |
| `test_d14r_in_lab_gate_exercises_fixture_import_order_unmasked_by_cron` | FAIL | PASS | Pre-correction: in-lab gate probe reported `problems: []` because earlier `from cron.scheduler_provider import InProcessCronScheduler` bootstrapped `sys.path`, masking the stale mapping. Corrected: in-lab gate executes fixture chain first, detecting `fixture-imports: ModuleNotFoundError` and missing writer interfaces unmasked by cron. |
| `test_d14r_preflight_refuses_missing_hermes_state_writer_surface` | FAIL | PASS | Pre-correction: `phase1_problems == []` because preflight did not validate `hermes_state` writer surface when `lab_root=None`. Corrected: `phase1_problems` includes `provisioned-writer-interface-missing:hermes_state.SessionDB.create_session` before lab creation. |
| `test_d14r_native_probe_body_executes_fixture_imports_before_cron_and_gateway` | FAIL | PASS | Pre-correction: `from hermes_state import SessionDB` missing from probe body before cron/gateway imports. Corrected: probe body executes fixture import chain in identical order to `_LAB_FIXTURE_PROBE` before `cron` or `gateway` imports. |
| `test_d14r_preserved_v3_failed_receipt_and_console_log_unchanged` | PASS | PASS | Preservation-only check: preserved v3 receipt digest `c23096fe...` and console log digest `a6046560...` remain byte-identical on both base and candidate. |

## Verification Results

1. **Deterministic lane:**
   ```bash
   uv run --frozen python scripts/qualify_telegram_monitor.py --json
   ```
   Result: `ok: true`, 11/11 checks passed, `external_effects: {"model_calls": 0, "telegram_sends": 0}`.

2. **Focused monitor test suite:**
   ```bash
   uv run --frozen python scripts/run_tests.py -- -q tests/test_telegram_monitor_*.py
   ```
   Result: **309 passed in 20.40s** (exit code 0).

3. **Full test suite:**
   ```bash
   uv run --frozen python scripts/run_tests.py
   ```
   Result: **1495 passed, 64 skipped, 2 failed** (exit code 1).
   Baseline comparison against `cf8cf3dee85bdf9b8e6c7802629ebcb4456afc38`:
   - Both 2 failures reproduce identically on base `cf8cf3d`:
     1. `tests/test_tracked_public_surface.py::test_tracked_public_surface_contains_no_operator_paths`: pre-existing historical contract violation in `.aether/objective-contracts/oc_0084270d940c98d9/v1.md` (documented and accepted).
     2. `tests/test_same_card_phase_predicates.py::test_initial_review_requires_an_independent_reviewer`: pre-existing lifecycle predicate test failure on base.
   - Baseline parity confirmed; 0 regressions introduced.

4. **Documentation validation:**
   ```bash
   uv run --frozen python scripts/check_documentation.py
   ```
   Result: `documentation validation passed` (exit code 0).

5. **Static quality gates:**
   ```bash
   uv run --frozen python -m compileall -q src tests scripts/check_documentation.py scripts/qualify_knowledge_expansion.py scripts/qualify_observation.py scripts/qualify_telegram_monitor.py scripts/telegram_monitor_lab.py scripts/check_hermes_baseline_drift.py scripts/check_public_artifacts.py scripts/run_tests.py scripts/validate_hermes_patch_reconciliation.py tests/test_documentation.py
   uv run --frozen mypy src/aether_agents
   uv run --frozen ruff check src tests scripts/check_documentation.py scripts/qualify_knowledge_expansion.py scripts/qualify_observation.py scripts/qualify_telegram_monitor.py scripts/telegram_monitor_lab.py scripts/check_hermes_baseline_drift.py scripts/check_public_artifacts.py scripts/run_tests.py scripts/validate_hermes_patch_reconciliation.py
   uv run --frozen ruff format --check src tests scripts/check_documentation.py scripts/qualify_knowledge_expansion.py scripts/qualify_observation.py scripts/qualify_telegram_monitor.py scripts/telegram_monitor_lab.py scripts/check_hermes_baseline_drift.py scripts/check_public_artifacts.py scripts/run_tests.py scripts/validate_hermes_patch_reconciliation.py
   uv build --out-dir /tmp/aether-dist
   git diff --check cf8cf3d...HEAD
   ```
   Result: all static gates passed cleanly with 0 errors or warnings.

6. **Policy manifest check:**
   Policy file list in `.github/workflows/policy.yml` matches `git ls-files` (excluding `specs/`) exactly: 376/376 files, 0 missing, 0 extra.

7. **Public artifact path scan:**
   ```bash
   uv run --frozen python scripts/check_public_artifacts.py --root . --artifact /tmp/aether-dist/*.whl --artifact /tmp/aether-dist/*.tar.gz
   ```
   Result: 0 violations added in tracked surface or built artifacts; baseline parity preserved (only pre-existing `.aether/objective-contracts/oc_0084270d940c98d9/v1.md` flagged).

8. **Confidence check against recovered runtime:**
   Read-only preflight rehearsal against installation interpreter (`<installation-home>/.venv-hermes/bin/python`) and Morfeo profile confirms:
   - `problems`: `[]`
   - `profile_digest`: `de71053213ebdde16a6a1e36c89f3407c2f0a08cdfbe080ff84035fcd0fdab2a`
   - `destination_digest`: `36007c9a8b0f839416989e6aa06b2d8225c11142837fc5539cf8a33b59935f5f`
   Confirming that the healthy runtime path does not regress.

## Residual Risk

- **Live attempt budget:** The single v3 live attempt was consumed by the pre-correction failure (`c23096fe...`). Exactly one additional live attempt requires an explicit owner decision before execution.
- **Terminal integration ownership:** All live runs (`--live --wait-hourly-boundaries 2`), model calls, Telegram sends, and production activation remain exclusively owned by Supervisor in terminal integration task `t_b8077e66`.
