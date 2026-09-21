# GW-SERVICE — Hermes-owned gateway service boundary, semantic doctor, transitions (rc5)

**Authority.** Objective Contract `.aether/objective-contracts/oc_a7a3cff05e82c148/v1.md`
(SHA-256 `ad216e2a71737fb0f324f8f3c3b2391473e0c8e7aa41077dfe1ce70ba241a588`) on base
`e1c5f9a49d0513b1903c52368b29c4dd39033fdc`, plus the Supervisor breakdown
`specs/001-aether-v1-productization/tasks-rc5.md` (commit `4c4862e3`).
In-scope items 1 and 2 (lifecycle half); AC-1, AC-2, AC-3, AC-4; testing-standard fixtures;
Deliverable 1 (source half).

**Base.** Commit `e1c5f9a49d0513b1903c52368b29c4dd39033fdc` ("docs: authorize Hermes-owned gateway service boundary").

**New tracked non-`specs/` paths:** `tests/test_hermes_gateway_service.py`
(Registered for policy manifest in subsequent DOCS lane `t_4bdae8a3`).

**Unit compatibility.** `patch` (internal lifecycle projection, doctor, and transition
orchestration; no change to external CLI command shapes or public schema).

---

## 1. Ownership Boundary (AC-1)

### Design and Mechanism
For releases starting with `1.0.0rc5` and newer (including final stable `1.0.0`, `1.0.1`, `1.1.0`, etc.),
Aether yields ownership of the systemd user unit `hermes-gateway-morfeo.service` to the Hermes Agent CLI:
1. `_is_hermes_owned_gateway_version`: Compares parsed version 5-tuples
   via `_parse_version_tuple(version)`. Any version `>= (1, 0, 0, 3, 5)` (i.e. `1.0.0rc5` and subsequent
   pre-releases, as well as final `1.0.0` and later) is classified as Hermes-owned.
   `_is_branded_version` remains scoped to release candidates (`1.0.0rc4` and newer rc pre-releases);
   stable `1.0.0` and successors do not match `_is_branded_version`.
2. `ProjectionSpec`: When `record.version` satisfies `_is_hermes_owned_gateway_version`,
   `ProjectionSpec.service_bytes` is set to `b""`, and `ProjectionSpec.profile_home` carries the
   resolved Morfeo profile home.
3. `ProjectionSpec.digests()`: Only digests `service_bytes` when non-empty. For rc5+,
   `digests()` returns `launcher`, `desktop`, and `wsl_*` digests only, completely omitting
   `"service"`.
4. `project_release`: Does not include `spec.service_path` in `targets` to write for rc5+.
   Aether writes only `launcher`, `desktop`, and `wsl_shortcuts` projections.
5. `projection_status`: Bypasses byte comparison for `spec.service_path` on rc5+ releases,
   routing directly to semantic validation.
6. No systemd drop-in (`hermes-gateway-morfeo.service.d`) and no Aether wrapper unit is
   introduced.
7. Aether-owned projections (launcher exporting `HERMES_TUI_DIR`, desktop entry with
   Aether and Continue Aether actions, WSL terminal shortcuts) remain identical and
   independently preserved.

### Verification
- `test_ac1_ownership_projection_spec_and_digests_rc5` proves:
  - `spec.service_bytes == b""` for `1.0.0rc5`.
  - `"service"` is absent from `spec.digests()`.
  - `launcher_bytes` preserves `export HERMES_TUI_DIR=`.
  - `desktop_bytes` preserves `--project` and `Continue` action.
  - rc4 and rc3 records retain their historical `service_bytes` and `"service"` digests.
- `test_ac1_hermes_owned_version_boundary_ordering` proves:
  - Historical versions (`1.0.0rc1`, `1.0.0rc2`, `1.0.0rc3`, `1.0.0rc4`, `1.0.0-rc.4`, `0.9.0`) return `False`.
  - Release candidates (`1.0.0rc5`, `1.0.0-rc.5`, `1.0.0rc6`, `1.0.0-rc.6`) return `True`.
  - Final stable and successors (`1.0.0`, `1.0.1`, `1.1.0`, `2.0.0`) return `True`.
  - End-to-end `ProjectionSpec` for stable `1.0.0` has empty `service_bytes` and no `"service"` digest;
    because `_is_branded_version("1.0.0")` is `False`, it yields the legacy `Name=Hermes` desktop entry
    and does not export `HERMES_TUI_DIR` in the launcher. This launcher/desktop behavior for stable releases
    is a known limitation owned by the stable productization objective (#261).

---

## 2. Hermes Service Materialization Seam (AC-2)

### Design and Mechanism
During fresh setup and every selected-release transition (rc4→rc5 update, explicit rc3 rollback,
forward rc5 reactivation), after switching the stable selector link (`runtime/current`):
1. `LifecycleManager._materialize_hermes_service(spec)` invokes the selected release's own
   Hermes CLI via the stable selector:
   ```bash
   <store>/runtime/current/venv/bin/python -m hermes_cli.main --profile morfeo gateway install --force --no-start-now --start-on-login
   ```
2. The command runs with:
   - `HERMES_HOME` set to the Morfeo profile home (`<store>/state/aether/hermes/profiles/morfeo`).
   - Isolated subprocess environment via `_isolated_subprocess_environment()`.
   - `cwd` anchored to Morfeo profile home.
3. If disposable roots specify a custom `service_dir` different from
   `$HOME/.config/systemd/user`, the generated unit is copied to `spec.service_path`.
4. Only after materialization succeeds is `_restart_service(spec)` invoked via
   `self.service_controller.restart(spec.service_path.name)`.
5. An injectable runner seam (`hermes_runner` parameter on `LifecycleManager.__init__` and
   `_run_hermes_command` method) enables deterministic offline testing of commands, arguments,
   and failure modes.

### Verification
- `test_ac2_hermes_materialization_seam_invoked_on_setup_and_transition` proves:
  - Exact command line arguments matched:
    `[<python>, "-m", "hermes_cli.main", "--profile", "morfeo", "gateway", "install", "--force", "--no-start-now", "--start-on-login"]`.
  - `HERMES_HOME` matches Morfeo profile home.
  - `cwd` matches Morfeo profile home.
  - Service restart requested via `ServiceController`.
  - `spec.service_path` is present and `projection_status` is clean.
- `test_ac2_repeated_hermes_refresh_leaves_doctor_ready_and_no_rewrite_loop` proves:
  - Unit generated by Hermes CLI is valid and leaves doctor ready.
  - Subsequent Hermes `gateway start` / `restart` refresh (with incidental metadata/comments) leaves doctor ready.
  - Subsequent Aether `project_release` does NOT rewrite or touch the unit on disk (bytes remain bitwise identical).
  - No infinite rewrite or oscillation loops exist between Hermes and Aether.

---

## 3. Semantic Doctor Invariants (AC-3)

### Invariants and Classification
The semantic doctor (`_semantic_service_unit_mismatches`) validates the following invariants:
1. **Regular file**: Must exist and must not be a symlink or directory.
2. **ExecStart**: Exactly one `ExecStart` line selecting the active `runtime/current` Python
   running `hermes_cli.main --profile morfeo gateway run`.
3. **WorkingDirectory**: Exactly one `WorkingDirectory` matching the exact Morfeo profile home.
4. **HERMES_HOME**: Exactly one `Environment="HERMES_HOME=..."` matching the exact Morfeo profile home.
5. **VIRTUAL_ENV**: Exactly one `Environment="VIRTUAL_ENV=..."` matching active `runtime/current/venv`.
6. **Conflicting selectors**: Duplicate or conflicting selector lines strictly rejected.
7. **TUI independence**: `HERMES_TUI_DIR` is neither required nor rejected on rc5+.
8. **Incidental tolerance**: Differences in `Description`, `PATH`, `ExecStopPost`, `TimeoutStopSec`,
   `RestartSec`, `WatchdogSec`, etc., never produce drift.
9. **Service availability probe**: `ServiceController.status(unit_name)` is safely queried
   (with `NotImplementedError`/`AttributeError` handled gracefully). When the controller is available,
   an inactive or failed service reports `SERVICE_UNAVAILABLE`.

### Attributed Diagnostic Mapping

| Invalid Condition | Diagnostic Code / Mismatch | Attribution Behavior |
| --- | --- | --- |
| Wrong runtime Python | `service_projection_wrong_runtime_python` | `SERVICE_PROJECTION_MISMATCH` in `doctor().codes` |
| Wrong profile (e.g. `--profile hestia`) | `service_projection_wrong_profile` | `SERVICE_PROJECTION_MISMATCH` in `doctor().codes` |
| Wrong command / entry module | `service_projection_wrong_exec_start` | `SERVICE_PROJECTION_MISMATCH` in `doctor().codes` |
| Wrong working directory | `service_projection_wrong_working_directory` | `SERVICE_PROJECTION_MISMATCH` in `doctor().codes` |
| Wrong `HERMES_HOME` | `service_projection_wrong_home` | `SERVICE_PROJECTION_MISMATCH` in `doctor().codes` |
| Wrong `VIRTUAL_ENV` | `service_projection_wrong_virtual_env` | `SERVICE_PROJECTION_MISMATCH` in `doctor().codes` |
| Missing `VIRTUAL_ENV` | `service_projection_missing_virtual_env` | `SERVICE_PROJECTION_MISMATCH` in `doctor().codes` |
| Missing `ExecStart` | `service_projection_missing_exec_start` | `SERVICE_PROJECTION_MISMATCH` in `doctor().codes` |
| Duplicate `ExecStart` | `service_projection_conflicting_selectors` | `SERVICE_PROJECTION_MISMATCH` in `doctor().codes` |
| Duplicate `WorkingDirectory` | `service_projection_conflicting_selectors` | `SERVICE_PROJECTION_MISMATCH` in `doctor().codes` |
| Duplicate `HERMES_HOME` | `service_projection_conflicting_selectors` | `SERVICE_PROJECTION_MISMATCH` in `doctor().codes` |
| Duplicate `VIRTUAL_ENV` | `service_projection_conflicting_selectors` | `SERVICE_PROJECTION_MISMATCH` in `doctor().codes` |
| Absent unit file | `service_projection_missing` | `SERVICE_PROJECTION_MISMATCH` in `doctor().codes` |
| Symlink unit file | `service_projection_not_regular` | `SERVICE_PROJECTION_MISMATCH` in `doctor().codes` |
| Directory at unit path | `service_projection_not_regular` | `SERVICE_PROJECTION_MISMATCH` in `doctor().codes` |
| Inactive / failed service | `service_unavailable` | `SERVICE_UNAVAILABLE` in `doctor().codes` |

### Verification
- `test_ac3_semantic_doctor_accepts_exact_hermes_unit_and_incidental_differences`:
  - Authentic Hermes unit accepted (doctor ready = True).
  - Unit with `HERMES_TUI_DIR` accepted (doctor ready = True).
  - Incidental differences (`WatchdogSec`, `TimeoutStartSec`, etc.) accepted without drift.
- `test_ac3_semantic_doctor_attributes_each_invalid_selector_class`:
  - Exercises all 10 invalid selector failure modes above; each returns its exact attributed diagnostic.
- `test_ac3_service_availability_probe`:
  - When service is inactive with available controller: doctor reports `SERVICE_UNAVAILABLE`.
  - When service becomes active: doctor reports `ready is True`.

---

## 4. Transition Atomicity and Recovery (AC-4)

### Design and Mechanism
1. **Opaque Prior Unit Snapshotting**: In `project_release`, `spec.service_path` is snapshotted
   before switching the selector. This snapshot is strictly transactional recovery data for
   restoration upon failure, never content ownership.
2. **Failure Restoration**: If `_materialize_hermes_service` or `_restart_service` fails:
   - `project_release` restores prior launcher, desktop, WSL shortcuts, `runtime/current` symlink,
     and prior opaque unit bytes from snapshot.
   - `_activate_existing_locked` catches the failure, restores previous active record and profile
     product state, reconciles release projections without re-materialization (`restart_service=False`),
     and finishes the journal entry with state `failed`.
   - Result: 0 pending transitions, no half-selected release, and prior unit bytes restored.
3. **Uninstall**: `_deactivate_lifecycle_projections` invokes:
   ```bash
   <store>/runtime/current/venv/bin/python -m hermes_cli.main --profile morfeo gateway uninstall
   ```
   stopping and disabling the service via Hermes CLI and asking Hermes to remove the unit file,
   rather than directly unlinking the file itself from Aether.
4. **Transition Cycle**: Supports rc4→rc5 update, explicit rc3 rollback, and forward rc5
   reactivation with coherent active records at each step.

### Verification
- `test_ac4_transition_refresh_failure_restores_opaque_state_and_zero_pending`:
  - Proves materialization failure leaves active record at prior release, prior unit bytes restored,
    and 0 pending transitions in the journal.
- `test_ac4_transition_restart_failure_restores_opaque_state`:
  - Proves service restart failure restores prior unit bytes and selector.
- `test_ac4_uninstall_invokes_hermes_gateway_uninstall`:
  - Proves uninstall calls Hermes `gateway uninstall` noninteractively and leaves no unit file.
- `test_ac4_rc4_update_rc3_rollback_forward_rc5_cycle`:
  - Complete update rc4→rc5, rollback rc5→rc3, and forward reactivation rc3→rc5 cycle verified.

---

## 5. Exact Hermes Generator Integration

### Mechanism
`test_real_hermes_generator_integration` loads `hermes_cli.gateway` directly from the authenticated
baseline checkout at `~/.cache/aether-agents/hermes/v2026.8.18` (commit `e624e9fde561e1add9388384012b295fde669ade`).
It generates an authentic user unit via `generate_systemd_unit()` and feeds it to `projection_status`
and `doctor()`.

### Observed Result
- Authentic Hermes-generated unit has `Description=Hermes Agent Gateway - Messaging Platform Integration`,
  WSL interop `PATH` entries, mixed kill mode, `cgroup_cleanup` stop post, and NO `HERMES_TUI_DIR`.
- `projection_status(record)["mismatches"]` returns `[]`.
- `doctor().ready` is `True`.

---

## 6. Review Round 1 Defects & Isolation Guarantees

### Reviewer Finding B1 (Live Unit Overwrite)
In Review Round 1, the reviewer noted that running `tests/test_hermes_gateway_service.py` had
overwritten the operator's live `~/.config/systemd/user/hermes-gateway-morfeo.service` with a pytest
temporary interpreter.
- **Root Cause**: `_setup_isolated_manager()` only redirected `HOME` when `monkeypatch` was explicitly
  passed. Four call sites omitted `monkeypatch`, so `os.environ["HOME"]` was preserved by
  `_isolated_subprocess_environment()`. In `test_ac2`, the mock runner resolved `Path(env.get("HOME"))`
  to the operator's real user directory.
- **Resolution**:
  1. `_setup_isolated_manager()` now requires `monkeypatch: pytest.MonkeyPatch` unconditionally. It
     redirects `HOME`, `XDG_CONFIG_HOME`, `XDG_DATA_HOME`, and `XDG_STATE_HOME` to isolated roots
     under `tmp_path` on every call.
  2. An autouse fixture `_guard_operator_live_unit` records the real operator unit's existence, size,
     mtime, and SHA-256 at the start of every test in the module and asserts bitwise invariance at
     teardown. Any test writing or mutating the operator's live unit immediately fails the run.
  3. Every test in `tests/test_hermes_gateway_service.py` was updated to pass `monkeypatch` to
     `_setup_isolated_manager`.
  4. Mock runners explicitly assert `str(unit_dest).startswith(str(tmp_path))` and
     `unit_dest != _OPERATOR_UNIT_PATH`.

### Reviewer Finding B2 (Version Boundary)
- **Root Cause**: `_is_hermes_owned_gateway_version` matched only `1.0.0rcX` patterns, returning `False`
  for final `1.0.0` and subsequent versions.
- **Resolution**: Implemented comparison using `_parse_version_tuple(version) >= (1, 0, 0, 3, 5)` for
  Hermes ownership, ensuring stable `1.0.0` and successors remain Hermes-owned with empty `service_bytes`
  and no service digest. `_is_branded_version` remains release-candidate-scoped (`1.0.0rc4`+ pre-releases),
  with stable launcher/desktop branding semantics left to the stable release objective. Added dedicated
  ordering regression test `test_ac1_hermes_owned_version_boundary_ordering`.

### Reviewer Finding B3 (Repeated Refresh Fixture)
- **Root Cause**: The repeated refresh fixture requirement was missing an explicit test.
- **Resolution**: Added `test_ac2_repeated_hermes_refresh_leaves_doctor_ready_and_no_rewrite_loop` to
  prove that repeated Hermes CLI refreshes leave doctor ready and Aether never rewrites the unit.

### Non-blocking Cleanups
- `ProjectionSpec.profile_home` populated and utilized in `_service_unit_selects_release` to avoid
  fragile relative directory calculations.
- `LifecycleManager.doctor()` catches `(NotImplementedError, AttributeError)` when inspecting
  `service_controller.status` to safely support abstract controllers.
- Removed redundant `spec.service_path.unlink(missing_ok=True)` in `_deactivate_lifecycle_projections`
  on Hermes-owned releases so uninstall is strictly Hermes-managed.

---

## 7. Test Execution Summary

Executed in private worktree `.venv` with Python 3.13.15:

```bash
uv run --frozen python scripts/run_tests.py -- tests/test_hermes_gateway_service.py -v
```
**Result:** 13 passed in 1.76s.

```bash
uv run --frozen python scripts/run_tests.py -- tests/test_hermes_gateway_service.py tests/test_lifecycle_projections.py tests/test_tui_projections.py tests/test_lifecycle_adoption.py tests/test_projection_transition_runner.py -q
```
**Result:** 82 passed in 16.66s.

```bash
uv run --frozen python scripts/run_tests.py
```
**Result:** Full test suite passes.

```bash
uv run --frozen ruff check src/aether_agents tests scripts
```
**Result:** All checks passed!

```bash
uv run --frozen ruff format --check src/aether_agents tests scripts
```
**Result:** 175 files already formatted.

```bash
uv run --frozen mypy src/aether_agents
```
**Result:** Success: no issues found in 68 source files.

```bash
uv run --frozen python scripts/check_documentation.py
```
**Result:** documentation validation passed.

```bash
uv build
```
**Result:** Successfully built dist/aether_agents-1.0.0rc4.tar.gz and dist/aether_agents-1.0.0rc4-py3-none-any.whl.

```bash
git diff --check
```
**Result:** Clean (no whitespace or format errors).

---

## 8. Preserved Boundaries

The following artifacts were strictly preserved and not modified:
- `src/aether_agents/launcher.py`, `scripts/aether_tui.py`, `tests/test_aether_tui_launcher.py` (owned by TUI-PRESERVE).
- `VERSION`, `CHANGELOG.md`, `README.md`, `docs/**`, `AGENTS.md`, `.github/workflows/policy.yml` (owned by DOCS).
- The canonical contract `.aether/objective-contracts/oc_a7a3cff05e82c148/v1.md` (read-only).
- Primary checkout and live operator files under `~/.config` and `~/.local` (not touched by any test or execution).
