# TUI-PRESERVE — Launcher, Desktop, and WSL Release-TUI Preservation Evidence (rc5)

**Unit**: TUI-PRESERVE (`t_e6868454`), role Implementer, worktree branch
`aether-agents-2/t_e6868454-tui-preserve-launcher-desktop-wsl-releas`.
**Authority**: Objective Contract `oc_a7a3cff05e82c148@v1`
(SHA-256 `ad216e2a71737fb0f324f8f3c3b2391473e0c8e7aa41077dfe1ce70ba241a588`), base commit
`e1c5f9a49d0513b1903c52368b29c4dd39033fdc`, Supervisor breakdown with shared decisions 1–10
(`specs/001-aether-v1-productization/tasks-rc5.md` at `4c4862e3`). Never edited the contract.
**Delivered scope**: contract in-scope 3; acceptance obligations AC-5 (launcher/Desktop/WSL half),
AC-1 (launcher half); breakdown unit TUI-PRESERVE.
**Unit compatibility**: `patch`.

---

## 1. Summary of preservation proof and test coverage

Preservation proof that Aether's launch surfaces keep delivering the release-owned TUI while
the gateway service no longer depends on that variable (option B for #487):

1. **Packaged launcher and installed-wheel console script export `HERMES_TUI_DIR`**:
   - `src/aether_agents/launcher.py` exports `HERMES_TUI_DIR = <runtime/current>/tui` to the
     Hermes process it launches via `os.execve(executable, command, environment)`.
   - Proved with a real packaged-launcher subprocess invocation (`python -m aether_agents.launcher`)
     and a real stub Hermes executable that captures its execution environment and arguments:
     - Fresh launch: exports `HERMES_TUI_DIR`, `HERMES_HOME`, `AETHER_PROJECT_ID`, `PWD`; drops
       ambient/dirty variables (`PYTHON*`, `HERMES_PROFILE`, `HERMES_TUI_PORT`, `HERMES_SESSION_ID`,
       `HERMES_KANBAN_*`, `HERMES_TASK*`, `HERMES_CRON_*`); preserves credentials.
     - Continuation launch (`--resume latest`): passes `--resume latest` in argv and exports
       `HERMES_TUI_DIR`.
   - Proved through an installed-wheel console-script lane (`uv build --wheel`, installed into a
     disposable virtual environment, invoking `<venv>/bin/aether` directly) rather than importing
     internals only.
   - Tested in `tests/test_aether_tui_launcher.py`:
     - `test_real_packaged_launcher_executes_stub_hermes_fresh_and_resume_latest`
     - `test_installed_wheel_console_script_lane_fresh_and_resume_latest`

2. **Non-mutating `aether --project <exact root> --json`**:
   - Executes the console script and packaged CLI with `--project <root> --json`.
   - Takes a comprehensive filesystem snapshot (recursive walk with file type, size, and SHA-256
     hash) across the project root, runtime root, and state root before and after invocation.
   - Proves `before_snapshot == after_snapshot` (zero filesystem mutation).
   - Validates JSON output: `result="ready"`, `project_id`, `repo_root`, `cwd`, `hermes_home`,
     `tui_dir` pointing to `<runtime/current>/tui`, `hermes_executable` pointing to
     `<runtime/current>/venv/bin/hermes`, and canonical command.
   - Tested in `tests/test_aether_tui_launcher.py`:
     - `test_aether_project_json_non_mutating_and_reports_release_identity`

3. **No npm/build artefacts and unchanged locked `hermes-source` inventory**:
   - Prepared disposable release containing representative locked `hermes-source` (`package.json`,
     `tsconfig.json`, `pyproject.toml`, `README.md`, `src/index.ts`).
   - Asserts a pre/post inventory (`rel_path -> (file_type, sha256)`) over the release's
     `hermes-source` before and after both fresh and continuation (`--resume latest`) launches.
   - Proves `pre_inventory == post_inventory` (exact bit-for-bit preservation).
   - Asserts complete absence of build/npm artefacts (`node_modules`, `package-lock.json`,
     `*.tsbuildinfo`, `.npm`, `.turbo`, `npm-debug.log*`) across `hermes-source`, release directory,
     and project root.
   - Tested in `tests/test_aether_tui_launcher.py`:
     - `test_launch_creates_no_build_artefacts_and_leaves_locked_hermes_source_unchanged`

4. **Desktop and WSL projection bytes point to stable `aether` entry point with `--resume latest`**:
   - Consumed `LifecycleManager.projection_spec(...)` read-only as an interface.
   - Linux Desktop entry (`spec.desktop_bytes`):
     - Main entry: `Exec=<runtime_current>/venv/bin/aether --project <resolved_project>`
     - Action: `Actions=Continue;`, `[Desktop Action Continue]`, `Name=Continue Aether`
     - Continuation entry: `Exec=<runtime_current>/venv/bin/aether --project <resolved_project> --resume latest`
   - WSL Windows Terminal shortcuts (`spec.wsl_shortcuts`):
     - `Aether.cmd`: `wt.exe wsl.exe [distro]-- "<runtime_current>/venv/bin/aether" --project "<resolved_project>"`
     - `Continue-Aether.cmd`: `wt.exe wsl.exe [distro]-- "<runtime_current>/venv/bin/aether" --project "<resolved_project>" --resume latest`
   - Tested both with explicit `project_root` and with default registry resolution.
   - Tested in `tests/test_aether_tui_launcher.py`:
     - `test_desktop_and_wsl_projections_point_to_stable_aether_entry_point`

5. **Gateway boundary preservation**:
   - Conformed strictly to the boundary: did not assert on unit-file bytes or gateway doctor
     semantics, preserving ownership for GW-SERVICE (`lifecycle.py`).

---

## 2. Verification table

| Clause | Assigned obligation | Exact command executed | Observed result | Evidence status |
|---|---|---|---|---|
| Clause 1 (Packaged launcher) | `HERMES_TUI_DIR` exported to stub Hermes executable for fresh and `--resume latest` | `uv run --frozen python scripts/run_tests.py -- tests/test_aether_tui_launcher.py::TuiPreservationTests::test_real_packaged_launcher_executes_stub_hermes_fresh_and_resume_latest` | PASS: stub reports exact release `HERMES_TUI_DIR`, `HERMES_HOME`, project id, clean env, and `--resume latest` arg | Direct |
| Clause 1 (Installed wheel) | Console script `aether` from installed wheel exports `HERMES_TUI_DIR` to stub Hermes | `uv run --frozen python scripts/run_tests.py -- tests/test_aether_tui_launcher.py::TuiPreservationTests::test_installed_wheel_console_script_lane_fresh_and_resume_latest` | PASS: wheel built via `uv build`, installed in disposable venv; console script launches stub with exact `HERMES_TUI_DIR` | Direct |
| Clause 2 (JSON identity) | `aether --project <root> --json` is non-mutating and reports projection identity | `uv run --frozen python scripts/run_tests.py -- tests/test_aether_tui_launcher.py::TuiPreservationTests::test_aether_project_json_non_mutating_and_reports_release_identity` | PASS: recursive file tree SHA-256 before == after; JSON output matches release identity | Direct |
| Clause 3 (Source preservation) | Launch creates no npm/build artefacts and leaves locked `hermes-source` unchanged | `uv run --frozen python scripts/run_tests.py -- tests/test_aether_tui_launcher.py::TuiPreservationTests::test_launch_creates_no_build_artefacts_and_leaves_locked_hermes_source_unchanged` | PASS: pre/post file type and SHA-256 inventories identical; no node_modules or build files | Direct |
| Clause 4 (Desktop/WSL actions) | Desktop and WSL actions target stable `aether` entry point with `--resume latest` | `uv run --frozen python scripts/run_tests.py -- tests/test_aether_tui_launcher.py::TuiPreservationTests::test_desktop_and_wsl_projections_point_to_stable_aether_entry_point` | PASS: Desktop and WSL shortcut bytes contain stable entry point, resolved project root, and `--resume latest` | Direct |
| Clause 5 (Gateway boundary) | Gateway service independence owned by GW-SERVICE; do not duplicate oracle | Code inspection of `test_aether_tui_launcher.py` | PASS: no assertions on `service_bytes` or systemd unit files in launcher test module | Direct |
| Full suite | Integrated launcher and preservation test suite | `uv run --frozen python scripts/run_tests.py -- tests/test_aether_tui_launcher.py -q` | PASS: 28 passed, 9 subtests passed in 4.75s | Direct |
| Lint & Format | Code style and formatting | `uv run --frozen ruff check src/aether_agents tests scripts && uv run --frozen ruff format --check src/aether_agents tests scripts` | PASS: All checks passed, 174 files formatted | Direct |
| Type check | Static typing | `uv run --frozen mypy src/aether_agents` | PASS: Success: no issues found in 68 source files | Direct |
| Docs check | Documentation validation | `uv run --frozen python scripts/check_documentation.py` | PASS: documentation validation passed | Direct |
| Wheel build | Packaging sanity | `uv build` | PASS: Successfully built wheel and sdist | Direct |
| Git cleanliness | No whitespace/check errors | `git diff --check` | PASS: clean output | Direct |

---

## 3. Tracked file manifest changes

Modified tracked paths:
- `src/aether_agents/launcher.py` (added canonical `if __name__ == "__main__": sys.exit(main())` entry block)
- `tests/test_aether_tui_launcher.py` (added `TuiPreservationTests` covering clauses 1–4)

New documentation/evidence path:
- `specs/001-aether-v1-productization/evidence/TUI-PRESERVE.md` (this file; under `specs/`, does not affect policy manifest)

Preserved boundaries:
- `src/aether_agents/lifecycle.py` (untouched; owned by GW-SERVICE)
- `tests/test_tui_projections.py` (untouched; owned by GW-SERVICE)
- `tests/test_lifecycle_projections.py` (untouched; owned by GW-SERVICE)
- `VERSION`, `CHANGELOG.md`, `README.md`, `docs/**`, `AGENTS.md`, `.github/workflows/policy.yml` (untouched; owned by DOCS)
- Canonical Objective Contract `.aether/objective-contracts/oc_a7a3cff05e82c148/v1.md` (consumed read-only, untouched)
- Primary checkout `/home/darkarty/Desktop/agentes/aether` (untouched)
- Every live XDG destination (`~/.config/systemd/user/`, etc., untouched)

---

## 4. Residual risk

- No known launcher residual risk. The launcher, installed console script, Desktop entry, and
  WSL actions continue to export and resolve the release-owned TUI and project bindings cleanly.
- Historical known baseline issue in `tests/test_public_artifacts.py` (manifest mismatch due to
  `policy.yml` missing the contract path at base) is owned and will be resolved by the DOCS unit.
