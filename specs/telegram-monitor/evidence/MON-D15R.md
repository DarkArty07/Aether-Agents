# MON-D15R Implementation Evidence — gap-free laboratory sources for isolated qualification

**Unit:** D15R — make the laboratory genuinely gap-free for the product's own read-only sources
**Task:** `t_125d63bf`
**Objective Contract:** `oc_f8c9fc9320587cf3@v3` (`.aether/objective-contracts/oc_f8c9fc9320587cf3/v3.md`, SHA-256 `f21facaf58af20a2d0595cdaa927a99ca6336e5b14b5d073ec3501bbfbf7f47c`)
**Source:** Owner D15 authorization on card `t_b8077e66` (canonical record `specs/telegram-monitor/qualification-isolation.md` §D15, commit `08d8233065d181a0f43b215ea2d71b2865818f0f`)
**Base commit:** `f603f8f1ace4dbb112afb05e032da620642e7050`
**Candidate commit:** `2ea97e17926ce46700c02fb3411fc414589d3d37`
**Phase:** implementer unit; **no live effect performed** — no `--live` run, no model call, no Telegram send, no scheduler start, no enable of any lab job, no profiler/registry mutation, no profile/config/credential/provider change, no runtime modification, no cleanup of retained labs/receipts, no push/PR/issue mutation.

## Scope and changed paths

- `src/aether_agents/monitor/sources.py`:
  1. `_resolve_board_paths`: only include implicit default board entry when its store exists (`kanban.db` or `boards/default/board.json` or `boards/default/kanban.db`), and exclude `default` from the `boards_root` iteration to avoid creating duplicate invalid paths.
  2. `_PHONE_RE`: aligned regex with the canonical pattern from `src/aether_agents/monitor/reporting.py`, preventing ISO dates (such as `2099-12-31` in task results) from being falsely flagged as phone numbers and raising `TASK_RESULT_UNSAFE`.
- `scripts/qualify_telegram_monitor.py`:
  1. `_environment_gaps`: accepted `hermes_home` keyword argument, evaluating the laboratory's own Hermes root (`lab["hermes_home"]`) instead of falling back to the operator's profile home.
  2. `QualificationBackends.environment_gaps`: accepted `hermes_home` and `lab` keyword arguments, forwarding `hermes_home` to `_environment_gaps`.
  3. `_qualify` at step 2a: invoked `backends.environment_gaps(store, hermes_home=Path(str(lab["hermes_home"])), lab=lab)` to probe the laboratory's own read-only sources before any enable effect.
  4. `_LAB_FIXTURE_PROBE`: seeded the two synthetic boards through the shipped execution-board writer (`_provision_execution_board` with fallback to `_create_metadata_exclusive` + `kanban_db.init_db`/`create_board`), populating complete Objective Contract metadata (`aether_project_id`, `aether_contract_id`, `aether_contract_version`, canonical `project_id`, `default_workdir`, `archived: false`).
- `tests/test_telegram_monitor_sources.py`:
  Added focused unit tests verifying:
  1. Root without default store emits no `BOARD_METADATA_UNREADABLE`.
  2. Root with unreadable default store (`kanban.db` exists, no `board.json`) preserves `BOARD_METADATA_UNREADABLE`.
  3. Root with unbound default store (`kanban.db` and empty `board.json`) preserves `BOARD_PROJECT_UNBOUND`.
  4. ISO dates in task results do not produce `TASK_RESULT_UNSAFE`.
- `tests/test_telegram_monitor_cli_plugin.py`:
  1. Updated `FakeQualificationBackends.environment_gaps` to accept `*args, **kwargs`.
  2. Updated `_CHAIN_STUB_MODULES` with `board_dir`, `init_db`, `read_board_metadata`, `connect_closing`, `list_projects` stubs.
  3. Added `test_d15r_coverage_probe_context_binds_to_lab_hermes_home` verifying coverage probe binds to lab hermes root.
  4. Added `test_d15r_reproduction_and_corrected_gap_free_laboratory` verifying pre-correction mixed context refusal vs corrected gap-free lab (`[]`).
  5. Added `test_d15r_negative_control_broken_lab_refuses` verifying broken lab metadata and missing contract artifact refuse with `BOARD_PROJECT_UNBOUND` and `FINAL_CONTRACT_UNREADABLE`.
  6. Added `test_d15r_fixture_and_environment_gaps_chain_end_to_end` exercising the real runtime chain (`_lab_create` → `_scope_manifest` → `_write_scope_projects` → `_lab_fixture` → `_environment_gaps`) yielding zero gaps.
- `CHANGELOG.md`: added entry under `[Unreleased]`.
- `specs/telegram-monitor/evidence/MON-D15R.md`: this evidence record.

Preserved unchanged: all design specifications in `specs/telegram-monitor/{spec,plan,quickstart,qualification-isolation,research,tasks}.md`, Objective Contracts `v1.md`, `v2.md`, `v3.md`, prior evidence records (`MON-06.md`, `MON-D14.md`, `MON-D14R.md`), the harness public CLI (`--json`, `--live`, `--wait-hourly-boundaries`, `--output`), the private evidence directory `/home/darkarty/.local/qualification/telegram-monitor-evidence/`, retained laboratory roots under `/home/darkarty/.local/state/aether/monitor/lab/`, and `.github/workflows/policy.yml` (manifest list exact at 376 files).

## Defect statement and reproduction

### The defect observed on `f603f8f`

The authorized live attempt on `f603f8f` reached the pre-enable coverage gate (step 2a, line 4584) and refused with:
```json
{
  "code": "environment-gaps",
  "message": "the laboratory sources report coverage gaps that prevent the genuine no-work skip: BOARD_METADATA_UNREADABLE, NATIVE_PROJECT_MISSING, SESSION_TITLE_UNAVAILABLE",
  "detail": {
    "gaps": ["BOARD_METADATA_UNREADABLE", "NATIVE_PROJECT_MISSING", "SESSION_TITLE_UNAVAILABLE"]
  }
}
```
This refusal occurred after lab creation and fixture seeding, but strictly before any enable/scheduler/model/send effect (`enable`, `scheduler`, `smoke`, `boundaries` were all empty, and production state was byte-identical).

### Root cause diagnosis against retained lab `20260911T052506Z-2be4d0c9a98a`

1. **Wrong context (harness):** `_environment_gaps(store)` in `scripts/qualify_telegram_monitor.py:2739` constructed `ReadOnlySources(state_root=store.state_root, hermes_home=monitor_runtime.hermes_home())` in the parent process. Because the parent process was not running with the lab's environment, `hermes_home` resolved to the operator's production profile home while `state_root` was the lab's `xdg-state/aether`. This mixed context caused `NATIVE_PROJECT_MISSING` (lab projects not registered in production native state) and `SESSION_TITLE_UNAVAILABLE` (production sessions unmapped to lab projects).
2. **Phantom default board (product):** Even when evaluating with the lab's own Hermes root (`lab_hermes`), `_resolve_board_paths` unconditionally prepended `("default", root / "kanban.db")`. `_read_board_bindings` then looked for `<root>/kanban/boards/default/board.json`. In a fresh root without a default board store (such as the lab), this missing file produced a false `BOARD_METADATA_UNREADABLE`. Furthermore, because a default board slug (`default`) can never match the execution-board grammar (`oc-<portable>-<contract>-v<n>`), no laboratory could ever be gap-free while this phantom entry was emitted.
3. **Unbound synthetic boards (fixture):** The lab's synthetic boards carry slugs in the exact execution-board convention (`oc-<portable-project>-<contract>-v1`) and the fixture writes final contract artifacts (`.aether/objective-contracts/<contract>/v1.md`), but the boards were created with plain `kanban_db.create_board(...)`. Consequently, `board.json` lacked `aether_project_id`, `aether_contract_id`, and `aether_contract_version`, yielding `BOARD_PROJECT_UNBOUND`.
4. **Over-broad phone regex rejecting dates (product):** In `src/aether_agents/monitor/sources.py:58`, `_PHONE_RE = re.compile(r"(?<!\d)(?:\+?\d[\d .()_-]{8,}\d)(?!\d)")` was overly broad and matched ISO date formats `YYYY-MM-DD` (e.g. `2099-12-31` in task A3's result `"Phase two rollout will finish by 2099-12-31 according to the latest draft."`), causing `_safe_text` to return `None` and raising `TASK_RESULT_UNSAFE`. Aligning `_PHONE_RE` with `reporting.py:121` (`r"(?<!\d)(?:\+\d{1,3}[ .-]?)?(?:\(\d{2,4}\)[ .-]?|\d{3}[ .-])\d{3}[ .-]\d{4}(?!\d)"`) resolves this without weakening real phone number detection.

### Reproduction results

Running read-only diagnosis against retained lab `20260911T052506Z-2be4d0c9a98a`:
- **Pre-correction (mixed context):** `ReadOnlySources(state_root=lab_state, hermes_home=prod_hermes).collect(...)` → `('BOARD_METADATA_UNREADABLE', 'NATIVE_PROJECT_MISSING', 'SESSION_TITLE_UNAVAILABLE')` (reproducing exact live refusal).
- **Pre-correction (lab hermes, unpatched sources & fixture):** `ReadOnlySources(state_root=lab_state, hermes_home=lab_hermes).collect(...)` → `('BOARD_METADATA_UNREADABLE', 'BOARD_PROJECT_UNBOUND')`.
- **Corrected candidate:** Fresh laboratory seeded with `_provision_execution_board` and evaluated with lab `hermes_home` and patched `sources.py` → `[]` (**zero collection-level coverage gaps**).

## Acceptance Criteria Mapping

| Requirement / AC | Check | Observed Result | Evidence Location |
| --- | --- | --- | --- |
| 1. Probe bound to lab context | `test_d15r_coverage_probe_context_binds_to_lab_hermes_home` | PASS: `backends.environment_gaps` forwards `hermes_home=Path(str(lab["hermes_home"]))`, resolving isolated lab context | `tests/test_telegram_monitor_cli_plugin.py` |
| 2. Fixture boards bind like real ones | `test_d15r_fixture_and_environment_gaps_chain_end_to_end` | PASS: Seeding boards through shipped execution-board writer populates all Objective Contract bindings; `environment_gaps` reports `[]` | `tests/test_telegram_monitor_cli_plugin.py` |
| 3. No phantom default gap | `test_root_without_default_board_store_produces_no_phantom_metadata_gap` | PASS: Root without default store omits `default` slug and produces no `BOARD_METADATA_UNREADABLE` gap | `tests/test_telegram_monitor_sources.py` |
| 3b. Default store gap preservation | `test_root_with_unreadable_or_unbound_default_store_preserves_gap` | PASS: Root with unreadable default store preserves `BOARD_METADATA_UNREADABLE`; unbound store preserves `BOARD_PROJECT_UNBOUND` | `tests/test_telegram_monitor_sources.py` |
| 3c. Date preservation in task results | `test_iso_dates_in_task_result_do_not_produce_task_result_unsafe` | PASS: `2099-12-31` does not match `_PHONE_RE`; `_safe_text` passes and produces no `TASK_RESULT_UNSAFE` | `tests/test_telegram_monitor_sources.py` |
| 4. Controlled reproduction & gap-free lab | `test_d15r_reproduction_and_corrected_gap_free_laboratory` | PASS: Pre-correction mixed context reports false gaps; corrected lab reports `[]` (zero gaps) | `tests/test_telegram_monitor_cli_plugin.py` |
| 5. Negative control | `test_d15r_negative_control_broken_lab_refuses` | PASS: Broken board metadata reports `BOARD_PROJECT_UNBOUND`; deleted contract reports `FINAL_CONTRACT_UNREADABLE` | `tests/test_telegram_monitor_cli_plugin.py` |
| 6. Deterministic offline lane | `uv run --frozen python scripts/qualify_telegram_monitor.py --json` | PASS: 11/11 checks pass, `external_effects: {"model_calls": 0, "telegram_sends": 0}`, `ok=true` | `scripts/qualify_telegram_monitor.py` |
| 7. Focused monitor suite | `uv run --frozen python scripts/run_tests.py -- -q tests/test_telegram_monitor_*.py` | PASS: 316/316 tests pass in 22.20s | `tests/` |

### Per-Test Fail-Before / Pass-After Mapping (Candidate vs Base `f603f8f`)

| Test Function | Base `f603f8f` Result | Corrected Candidate Result | Observed Semantics |
| --- | --- | --- | --- |
| `test_root_without_default_board_store_produces_no_phantom_metadata_gap` | FAIL (`assert "default" not in paths` failed; `assert "BOARD_METADATA_UNREADABLE" not in gaps` failed) | PASS | Base unconditionally prepended `("default", root / "kanban.db")` and emitted `BOARD_METADATA_UNREADABLE` on roots lacking default store. Corrected candidate includes default only when its store exists on disk. |
| `test_iso_dates_in_task_result_do_not_produce_task_result_unsafe` | FAIL (`assert _safe_text(...) is not None` failed) | PASS | Base `_PHONE_RE` was overly broad and matched `2099-12-31`, causing `_safe_text` to return `None`. Corrected candidate aligns `_PHONE_RE` with `reporting.py` and treats ISO dates as valid prose. |
| `test_d15r_reproduction_and_corrected_gap_free_laboratory` | FAIL | PASS | Base evaluated parent's profile home instead of lab's `hermes_home`, and boards lacked execution-board contract metadata. Corrected candidate evaluates lab context with bound boards and reports `[]` (zero gaps). |
| `test_d15r_fixture_and_environment_gaps_chain_end_to_end` | FAIL | PASS | Full end-to-end chain on base refused with `environment-gaps`. Corrected candidate reaches pre-enable coverage probe and reports zero gaps. |

## Exact Verification Commands and Output

1. **Deterministic offline lane:**
   ```bash
   uv run --frozen python scripts/qualify_telegram_monitor.py --json
   ```
   Result: `ok: true`, 11/11 checks passed, `external_effects: {"model_calls": 0, "telegram_sends": 0}`.

2. **Focused monitor test suite:**
   ```bash
   uv run --frozen python scripts/run_tests.py -- -q tests/test_telegram_monitor_*.py
   ```
   Result: **316 passed in 22.20s** (exit code 0).

3. **Full test suite:**
   ```bash
   uv run --frozen python scripts/run_tests.py
   ```
   Result: **1502 passed, 64 skipped, 2 failed** (exit code 1).
   Baseline comparison against `f603f8f`:
   - Both 2 failures reproduce identically on base `f603f8f`:
     1. `tests/test_public_artifacts.py::test_tracked_public_surface_contains_no_operator_paths`: pre-existing historical contract violation in `.aether/objective-contracts/oc_0084270d940c98d9/v1.md` (documented and accepted).
     2. `tests/test_same_card_phase_predicates.py::test_initial_review_requires_an_independent_reviewer`: pre-existing lifecycle predicate test failure on base.
   - Baseline parity confirmed; 0 regressions introduced.

4. **Documentation validation:**
   ```bash
   uv run --frozen python scripts/check_documentation.py
   ```
   Result: `documentation validation passed` (exit code 0).

5. **Type checking:**
   ```bash
   uv run --frozen mypy src/aether_agents
   ```
   Result: `Success: no issues found in 65 source files` (exit code 0).

6. **Linter and format validation:**
   ```bash
   uv run --frozen ruff check src tests scripts/check_documentation.py scripts/qualify_knowledge_expansion.py scripts/qualify_observation.py scripts/qualify_telegram_monitor.py scripts/telegram_monitor_lab.py scripts/check_hermes_baseline_drift.py scripts/check_public_artifacts.py scripts/run_tests.py scripts/validate_hermes_patch_reconciliation.py
   uv run --frozen ruff format --check src tests scripts/check_documentation.py scripts/qualify_knowledge_expansion.py scripts/qualify_observation.py scripts/qualify_telegram_monitor.py scripts/telegram_monitor_lab.py scripts/check_hermes_baseline_drift.py scripts/check_public_artifacts.py scripts/run_tests.py scripts/validate_hermes_patch_reconciliation.py
   ```
   Result: `All checks passed!` and `150 files already formatted` (exit code 0).

7. **Bytecode compilation:**
   ```bash
   uv run --frozen python -m compileall -q src tests scripts/check_documentation.py scripts/qualify_knowledge_expansion.py scripts/qualify_observation.py scripts/qualify_telegram_monitor.py scripts/telegram_monitor_lab.py scripts/check_hermes_baseline_drift.py scripts/check_public_artifacts.py scripts/run_tests.py scripts/validate_hermes_patch_reconciliation.py tests/test_documentation.py
   ```
   Result: exit code 0.

8. **Package build and public artifact scan:**
   ```bash
   uv build
   uv run --frozen python scripts/check_public_artifacts.py --root . --artifact dist/*.whl --artifact dist/*.tar.gz
   rm -rf dist
   ```
   Result: 0 violations added in tracked surface or built artifacts; baseline parity preserved (only pre-existing `.aether/objective-contracts/oc_0084270d940c98d9/v1.md` flagged).

9. **Whitespace and conflict marker check:**
   ```bash
   git diff --check f603f8f1ace4dbb112afb05e032da620642e7050...HEAD
   ```
   Result: clean (exit code 0).

10. **Policy manifest exact parity:**
    ```bash
    bash -c '
    expected=$(mktemp)
    actual=$(mktemp)
    trap "rm -f $expected $actual" EXIT
    sed -n "35,410p" .github/workflows/policy.yml > "$expected"
    sed -i "s/^          //" "$expected"
    sort -o "$expected" "$expected"
    git ls-files | grep -v "^specs/" | sort > "$actual"
    diff -u "$expected" "$actual"
    echo "Diff status: $?"
    '
    ```
    Result: `Diff status: 0` (376 files, 0 missing, 0 extra).

## Residual Risk

- **Live attempt budget:** The v4 pre-effect refusal occurred strictly before enablement and consumed no external-effect budget (0 model calls, 0 Telegram sends). Exactly one authorized live attempt remains owned by Supervisor in terminal integration task `t_b8077e66`.
- **Terminal integration ownership:** The next authorized live attempt runs on this corrected candidate and stops with no rerun if it fails after lab job/scheduler/model/Telegram effects begin. All live runs (`--live --wait-hourly-boundaries 2`), model calls, Telegram delivery, and production activation remain exclusively owned by Supervisor.
