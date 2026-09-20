# LG-LIFE — Release-owned TUI and branded projections

**Authority.** Objective Contract `oc_ff82ba151cdf3861@v2` (SHA-256
`e5c4fea02a5b1cee977c93a602d5af622b59e7325c9efb3be7d7b1e7bfc49bd0`), in-scope
items 2 and 3; AC-3, AC-4, and AC-5; breakdown unit LG-LIFE from
`specs/001-aether-v1-productization/tasks-rc4.md`.

**Base.** Commit `00715d237d795e365c5e462b6b80d5a1bd8d8188`. Clean worktree.

**New tracked non-`specs/` paths for LG-DOCS:**
- `tests/test_tui_projections.py`

**Unit compatibility.** `patch` (backwards-compatible internal lifecycle and projection repair).

## What changed

| Path | Change |
| --- | --- |
| `src/aether_agents/lifecycle.py` | Built/staged release-owned TUI (`dist/entry.js`) outside `hermes-source`, hash-bound in release record (`tui_sha256`) and manifest without copy fallbacks; branded terminal-based Desktop entry (`Name=Aether`, `Exec=.../aether --project <root>`, `Continue Aether` action); WSL Windows Terminal adapters (`Aether.cmd` and `Continue-Aether.cmd`) with runtime detection via `detect_wsl_shortcuts_dir` for operator roots; cleanup of legacy `hermes.desktop` upon projection/deactivation with rollback snapshot preservation; exact project binding resolution in `_resolve_default_project` and fail-closed `projection_spec` without guessing or store parent fallback; `export HERMES_TUI_DIR="$AETHER_RUNTIME_ROOT/tui"` in launcher without ambient fallback; `HERMES_TUI_DIR` selector line enforcement in `_service_unit_selects_release` to catch service drift; doctor fail-closed checks on altered, unbound, or missing TUI bytes; projection failure state-restoration rollback; `build_tui_in_disposable_workspace` and `detect_wsl_distribution` helpers |
| `scripts/release_bundle.py` | Removed checkout `scripts/aether_tui.py` copy; staged release-owned TUI under `roots / "tui"` outside `hermes-source` via fail-closed disposable build with no copy fallback; added `HERMES_TUI_DIR` to runtime environments; qualified packaged `aether --project <root> --json` with `required=True` rather than importing checkout scripts |
| `tests/test_lifecycle_projections.py` | Updated `_operator_destination_witnesses` to watch `aether.desktop`, legacy `hermes.desktop`, and operator WSL shortcuts; updated mock `hermes_refreshed` units to include `HERMES_TUI_DIR`; updated mock `_record` helper to stage `tui_sha256` and `tui/dist/entry.js` |
| `tests/test_tui_projections.py` | Focused regression test suite (10 deterministic nodes): disposable TUI build/staging from exact commit `aed6591a69f453a1867b73628603e7b53ba40ffc` without skips or hardcoded paths; branded desktop actions and WSL adapters; selector coherence across lifecycle transitions; doctor fail-closed checks on altered/missing/unbound TUI bytes; projection failure opaque-state recovery; locked-source inventory/hash immutability after PTY launch; operator WSL projection generation and legacy `hermes.desktop` removal/rollback; service unit drift detection on missing/tampered `HERMES_TUI_DIR`; exact project binding fail-closed negative control |

## Measured TUI Build & Verification Receipt

- **Maintained fork commit:** `aed6591a69f453a1867b73628603e7b53ba40ffc` (`DarkArty07/aether-hermes` `aether-main`)
- **Workspace isolation:** TUI built in a clean disposable temporary directory via `git archive` export; locked `hermes-source` is never touched by npm/build.
- **Node version:** `v22.23.2`
- **npm version:** `10.9.8`
- **Output TUI asset:** `dist/entry.js`
- **Output digest (SHA-256):** `f56f6225d9124376eedec1834d372c76a33292aedc41021cc13d6c3b32a05643`
- **Deterministic verification:** repeated independent clean builds in separate disposable roots yielded identical SHA-256.

## Verification Matrix

| Obligation | Check / Command | Result | Evidence Location |
| --- | --- | --- | --- |
| Disposable TUI build & provenance | `pytest tests/test_tui_projections.py::test_tui_disposable_build_and_staging` | PASS | `tests/test_tui_projections.py:146` |
| Branded desktop actions & WSL adapters | `pytest tests/test_tui_projections.py::test_projection_spec_branded_actions_and_tui_env` | PASS | `tests/test_tui_projections.py:175` |
| Lifecycle selector agreement & deactivation | `pytest tests/test_tui_projections.py::test_projection_cycle_and_selector_agreement` | PASS | `tests/test_tui_projections.py:222` |
| Doctor fail-closed on altered/missing TUI | `pytest tests/test_tui_projections.py::test_doctor_fail_closed_on_altered_or_missing_tui_bytes` | PASS | `tests/test_tui_projections.py:261` |
| Projection failure rollback | `pytest tests/test_tui_projections.py::test_projection_failure_restores_prior_opaque_state` | PASS | `tests/test_tui_projections.py:287` |
| Locked-source hash/inventory immutability | `pytest tests/test_tui_projections.py::test_locked_source_inventory_and_hashes_identical_after_tui_launch` | PASS | `tests/test_tui_projections.py:321` |
| Operator WSL projections & legacy desktop removal | `pytest tests/test_tui_projections.py::test_operator_wsl_projections_and_legacy_desktop_removal` | PASS | `tests/test_tui_projections.py:396` |
| Service unit drift on missing/tampered HERMES_TUI_DIR | `pytest tests/test_tui_projections.py::test_service_unit_drift_on_missing_or_tampered_hermes_tui_dir` | PASS | `tests/test_tui_projections.py:464` |
| Doctor fail-closed on unbound/missing TUI | `pytest tests/test_tui_projections.py::test_doctor_fails_closed_when_tui_is_none_or_missing` | PASS | `tests/test_tui_projections.py:497` |
| Exact project binding fails closed | `pytest tests/test_tui_projections.py::test_exact_project_binding_fails_closed_without_exact_marker_or_registry` | PASS | `tests/test_tui_projections.py:510` |
| Full lifecycle projection suite | `uv run --frozen pytest tests/test_lifecycle_projections.py` | 21 passed | 21/21 passed in 7.21s |
| Full release bundle qualification suite | `uv run --frozen pytest tests/test_release_bundle.py` | 35 passed | 35/35 passed in 4.33s |
| Combined test suite | `uv run --frozen pytest -q tests/test_tui_projections.py tests/test_lifecycle_projections.py tests/test_release_bundle.py` | 66 passed | 66/66 passed in 23.51s |
| Public artifact path scan | `uv run --frozen python scripts/check_public_artifacts.py --root .` | PASS | 0 findings, exit code 0 |
| Documentation check | `uv run --frozen python scripts/check_documentation.py` | PASS | Validation passed, exit code 0 |
| Wheel & sdist build | `uv build` | PASS | Built sdist and wheel cleanly |
| Ruff lint check | `uv run --frozen ruff check src/aether_agents tests scripts` | PASS | All checks passed |
| Ruff format check | `uv run --frozen ruff format --check src/aether_agents tests scripts` | PASS | 172 files formatted |
| Type check | `uv run --frozen mypy src/aether_agents` | PASS | 0 issues across 67 files |

## Non-claims

This unit does not author the packaged CLI module (owned by LG-CLI), update VERSION or documentation identity (owned by LG-DOCS), activate the live host installation or mutate issues (owned by LG-CLOSE), or create/push tags or pull requests.
