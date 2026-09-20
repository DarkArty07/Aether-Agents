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
For releases starting with `1.0.0rc5` and newer, Aether yields ownership of the
systemd user unit `hermes-gateway-morfeo.service` to the Hermes Agent CLI:
1. `ProjectionSpec`: When `record.version` satisfies `_is_hermes_owned_gateway_version`
   (`>= 1.0.0rc5`), `ProjectionSpec.service_bytes` is set to `b""`.
2. `ProjectionSpec.digests()`: Only digests `service_bytes` when non-empty. For rc5+,
   `digests()` returns `launcher`, `desktop`, and `wsl_*` digests only, completely omitting
   `"service"`.
3. `project_release`: Does not include `spec.service_path` in `targets` to write for rc5+.
   Aether writes only `launcher`, `desktop`, and `wsl_shortcuts` projections.
4. `projection_status`: Bypasses byte comparison for `spec.service_path` on rc5+ releases,
   routing directly to semantic validation.
5. No systemd drop-in (`hermes-gateway-morfeo.service.d`) and no Aether wrapper unit is
   introduced.
6. Aether-owned projections (launcher exporting `HERMES_TUI_DIR`, desktop entry with
   Aether and Continue Aether actions, WSL terminal shortcuts) remain identical and
   independently preserved.

### Verification
- `test_ac1_ownership_projection_spec_and_digests_rc5` proves:
  - `spec.service_bytes == b""` for `1.0.0rc5`.
  - `"service"` is absent from `spec.digests()`.
  - `launcher_bytes` preserves `export HERMES_TUI_DIR=`.
  - `desktop_bytes` preserves `--project` and `Continue` action.
  - rc4 and rc3 records retain their historical `service_bytes` and `"service"` digests.

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
  - Generated unit survives repeated Hermes `gateway start` / `restart` without any Aether rewrite loop.

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
9. **Service availability probe**: `ServiceController.status(unit_name)` is queried. When the
   controller is available, an inactive or failed service reports `SERVICE_UNAVAILABLE`.

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
   stopping and disabling the service via Hermes CLI and unlinking the unit file.
4. **Transition Cycle**: Supports rc4→rc5 update, explicit rc3 rollback, and forward rc5
   reactivation with coherent active records at each step.

### Verification
- `test_ac4_transition_refresh_failure_restores_opaque_state_and_zero_pending`:
  - Proves materialization failure leaves active record at prior release, prior unit bytes restored,
    and 0 pending transitions in the journal.
- `test_ac4_transition_restart_failure_restores_opaque_state`:
  - Proves service restart failure restores prior unit bytes and selector.
- `test_ac4_uninstall_invokes_hermes_gateway_uninstall`:
  - Proves uninstall calls Hermes `gateway uninstall` noninteractively.
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

## 6. Isolation Guarantees

- `test_isolation_guarantee_no_operator_state_touched` verifies:
  - Live operator file `~/.config/systemd/user/hermes-gateway-morfeo.service` is read before and after test execution; bytes are identical.
  - All test projections, stores, and units remain strictly confined under `tmp_path`.

---

## 7. Test Execution Summary

Executed in private worktree `.venv` with Python 3.13.15:

```bash
uv run --frozen python scripts/run_tests.py -- tests/test_lifecycle_projections.py tests/test_tui_projections.py tests/test_hermes_gateway_service.py -q
```
**Result:** 52 passed in 11.95s.

```bash
uv run --frozen pytest -q tests/test_lifecycle_projections.py tests/test_tui_projections.py tests/test_projection_transition_runner.py tests/test_lifecycle_adoption.py tests/test_hermes_gateway_service.py
```
**Result:** 80 passed in 17.25s.

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
- Primary checkout and live operator files under `~/.config` and `~/.local`.
