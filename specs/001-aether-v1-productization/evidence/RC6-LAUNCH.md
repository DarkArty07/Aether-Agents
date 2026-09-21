# RC6-LAUNCH — Inherited Transport Selector Scrubbing and Packaged Launch Evidence (rc6)

**Unit**: RC6-LAUNCH (`t_fb74d205`) and continuation RC6-LAUNCH-2 (`t_b0975e1c`), role Implementer, worktree branch
`aether-agents-2/t_b0975e1c-rc6-launch-2-scrub-inherited-terminal_cw`.
**Authority**: Objective Contract `oc_b5926701207812e8@v1`
(SHA-256 `e7164c83862b747c7868706799c08ea63151ca388aa2dc2b1b89a40be33b01fc`), base commit
`c79f5b147ae0c4f52c606978ff0bf3e82c5096fb` (accepted RC6-LAUNCH tip on base `d2874c2f3fc839a82fbaa96ece6edebab3856298`), material design
`specs/001-aether-v1-productization/plan-rc6.md` §U1, and Supervisor breakdown with shared decisions 1–10
(`specs/001-aether-v1-productization/tasks-rc6.md` at `adc57c2b`). Never edited the contract.
**Delivered scope**: contract U1 (code half), D1; acceptance obligation AC-6 (code half); breakdown units RC6-LAUNCH and RC6-LAUNCH-2.
**Unit compatibility conclusion**: `patch`.

---

## 1. Summary of behavior and verification

1. **Scrubbing inherited transport selectors and stale paths**:
   - `src/aether_agents/launcher.py` scrubs transport selectors and stale active-session transport paths
     from `os.environ` before executing the Hermes TUI child process via `os.execve(executable, command, environment)`:
     - Transport selectors: `HERMES_PYTHON`, `HERMES_PYTHON_SRC_ROOT`, `HERMES_BIN`, `HERMES_CWD`, `TERMINAL_CWD`, `MESSAGING_CWD`, `_HERMES_GATEWAY`.
     - Stale socket/RPC/gateway paths: `HERMES_RPC_SOCKET`, `HERMES_RPC_DIR`, `HERMES_RPC_TOKEN`,
       `HERMES_TUI_GATEWAY_URL`, `HERMES_TUI_SIDECAR_URL`, `HERMES_GATEWAY_SESSION`, `HERMES_GATEWAY_*`.
     - Stale active-session transport files and ids: `HERMES_TUI_ACTIVE_SESSION_FILE`, `HERMES_SESSION_ID`,
       `HERMES_SESSION_KEY`, `HERMES_SESSION_*`, `HERMES_UI_SESSION_ID`.
     - Stale process/desktop state: `HERMES_DESKTOP_READY_FILE`, `HERMES_DESKTOP_CHILD_PID`, `HERMES_DESKTOP_*`,
       `HERMES_COMPUTE_HOST_*`, `HERMES_PARENT_*`, `HERMES_ACTION_ID`.
     - Python and virtual environment leak prevention: `PYTHON*`, `VIRTUAL_ENV`.
     - Task/board routing: `HERMES_KANBAN_*`, `HERMES_TASK*`, `HERMES_CRON_*`, `HERMES_PROFILE`.
   - Preserves unrelated provider credentials (e.g. `CUSTOM_CREDENTIAL_KEY`, `OPENAI_API_KEY`, `ANTHROPIC_API_KEY`)
     and model configuration (e.g. `HERMES_MODEL`, `HERMES_INFERENCE_MODEL`).

2. **Binding target release identities after scrubbing**:
   - `HERMES_PYTHON`: resolves to the active release's absolute lexical Python interpreter path
     (`<target_venv>/bin/python` or `python3`), preserving the venv symlink without leaf dereference to
     the base interpreter. Proved via a bounded isolated subprocess probe (`python -I -c ...` executed with
     isolated cwd) asserting `sys.prefix` and `purelib` resolve within and corroborate the same target release venv.
     Accepted venvs derive strictly from the selected target (`hermes` executable's venv and explicitly supplied
     runtime root), preventing silent fallback to ambient or foreign releases. Candidates outside the target venv
     or with failing/split probe results raise `ActivationError` and are never bound silently. Current process
     `sys.executable` fallback is accepted only if it also proves to be inside that same target release venv.
   - `HERMES_PYTHON_SRC_ROOT`: resolves to the active release's `hermes-source` directory if present
     (`<target_release>/hermes-source`). Never inherits parent's `HERMES_PYTHON_SRC_ROOT`.
   - `HERMES_TUI_DIR`: binds the active release's TUI directory (`<target_release>/tui`).
   - `HERMES_HOME`: binds the active release's Morfeo profile (`<state_root>/hermes/profiles/morfeo`).
   - `AETHER_PROJECT_ID`: binds the exact verified project UUID.
   - `PWD`: binds the exact verified repository root.
   - Child execution: `[<hermes_executable>, "--tui", "--in", "<repo_root>", ...]` executed with the scrubbed environment.

3. **Clean and contaminated shell environments**:
   - Fresh launch and continuation launch (`--resume latest`) both succeed in a clean shell environment (no ambient
     transport variables) and in a heavily contaminated shell environment (with old backend python, old source root,
     stale gateway URLs, and stale sockets).
   - In both environments, the launched child receives the exact active release identities and zero stale transport residue.
   - The bound `HERMES_PYTHON` is lexically equal to the release venv interpreter path and distinct from the
     dereferenced base interpreter, with `sys.prefix` and `purelib` verified inside the release venv.

4. **Bare `aether` launch inside project directory**:
   - Tested bare invocation `aether` from cwd matching an initialized registered project without `--project`.
   - Resolves exact project from disk marker and registry agreement, scrubs contaminated environment, and binds
     target identities identically.

5. **Non-mutating plan and locked-source preservation**:
   - `aether --project <root> --json` remains strictly non-mutating and outputs the canonical plan keys.
   - Reserved arguments (`--safe-mode`, `--profile`, etc.) continue to fail closed with code 2.
   - Pre/post file-type and SHA-256 inventories of locked `hermes-source` match bit-for-bit across launches, with zero
     npm/build artefacts generated.

6. **Scrubbing inherited modern cwd selectors and verifying project alignment (RC6-LAUNCH-2)**:
   - `src/aether_agents/launcher.py` scrubs `TERMINAL_CWD` and `MESSAGING_CWD` in `keys_to_drop`, closing the asymmetry
     where `HERMES_CWD` was dropped while the modern runtime selectors were inherited by the target Hermes process.
   - Ambient parent `TERMINAL_CWD` and `MESSAGING_CWD` are removed before `os.execve`, ensuring the fresh TUI/session
     reports the resolved project root as its cwd and does not steer into a foreign directory.
   - Preserves operator configuration bytes and the native runtime config bridge (`apply_terminal_config_to_env`).
   - Profile configuration is verified against the selected project: if `terminal.cwd` in `config.yaml` is set and
     resolves to the project root, launch proceeds; if `terminal.cwd` contradicts the resolved project, `inspect_activation`
     visibly refuses with `ActivationError` (exit code 2), preventing silent misdirection of the session.

---

## 2. Contaminated environment construction and defect reproduction

The test suite constructs the contaminated parent environment via `_make_contaminated_env()` in
`tests/test_aether_tui_launcher.py`:

```python
env["HERMES_PYTHON"] = "/opt/stale-backend/venv/bin/python"
env["HERMES_PYTHON_SRC_ROOT"] = "/opt/stale-backend/hermes-source"
env["HERMES_TUI_GATEWAY_URL"] = "ws://127.0.0.1:9999"
env["HERMES_TUI_SIDECAR_URL"] = "ws://127.0.0.1:9998"
env["HERMES_TUI_ACTIVE_SESSION_FILE"] = "/tmp/stale-session.json"
env["HERMES_RPC_SOCKET"] = "/tmp/stale-rpc.sock"
env["HERMES_RPC_DIR"] = "/tmp/stale-rpc"
env["HERMES_RPC_TOKEN"] = "stale-rpc-token"
env["HERMES_SESSION_ID"] = "stale-session-123"
env["HERMES_SESSION_KEY"] = "stale-session-key"
env["HERMES_UI_SESSION_ID"] = "stale-ui-session-id"
env["HERMES_CWD"] = "/tmp/stale-cwd"
env["TERMINAL_CWD"] = "/tmp/stale-terminal-cwd"
env["MESSAGING_CWD"] = "/tmp/stale-messaging-cwd"
env["HERMES_BIN"] = "/tmp/stale-bin/hermes"
env["VIRTUAL_ENV"] = "/opt/stale-backend/venv"
env["_HERMES_GATEWAY"] = "1"
env["HERMES_GATEWAY_SESSION"] = "stale-gw-session"
env["HERMES_DESKTOP_READY_FILE"] = "/tmp/stale-desktop.ready"
env["HERMES_PROFILE"] = "dirty-profile"
env["PYTHONBREAKPOINT"] = "custom-breakpoint"
env["PYTHONWARNINGS"] = "error"
env["HERMES_TUI_DIR"] = "/tmp/stale-ambient-tui"
env["HERMES_TUI_PORT"] = "9999"
env["HERMES_KANBAN_TASK"] = "t_stale456"
env["HERMES_KANBAN_DB"] = "/tmp/stale-kanban.db"
env["HERMES_TASK_ID"] = "stale-task"
env["HERMES_CRON_JOB"] = "stale-cron"
env["CUSTOM_CREDENTIAL_KEY"] = "retained-secret"
```

### Confirmed defect (RC6-LAUNCH-2)

Supervisor review of RC6-QUAL (run 46) reproduced end-to-end that the initial RC6-LAUNCH scrub
dropped `HERMES_CWD` but missed the modern cwd selectors `TERMINAL_CWD` and `MESSAGING_CWD`.
The maintained fork sets both spellings on the same line (`hermes_cli/main.py:2556-2557`), while the shipped
product and runtime gateway read `TERMINAL_CWD` as the workspace cwd (`hermes_cli/config.py:3377`,
`config_defaults.py:4617`, `tui_gateway/server.py:1610/2530`). Consequently, the initial scrub blocked the
legacy spelling but let the modern one through into `/proc/<pid>/environ`, steering the fresh TUI's
session cwd to the ambient foreign directory rather than the resolved project root.

### Implementer RED reproduction re-run

On base commit `c79f5b147ae0c4f52c606978ff0bf3e82c5096fb`, executed the dedicated launch exec path regression:
- Command: `uv run --frozen python scripts/run_tests.py -- -k "test_regression_contaminated_parent_cannot_override_project_cwd_with_terminal_or_messaging_cwd"`
- Observed result:
  ```
  FAILED tests/test_aether_tui_launcher.py::TuiPreservationTests::test_regression_contaminated_parent_cannot_override_project_cwd_with_terminal_or_messaging_cwd
  AssertionError: 'TERMINAL_CWD' unexpectedly found in {'... TERMINAL_CWD': '/tmp/stale-terminal-foreign-cwd', ...}
  ```
- Result: RED confirmed. The hostile ambient `TERMINAL_CWD` and `MESSAGING_CWD` leaked into the target environment.

### Post-fix verification

With `TERMINAL_CWD` and `MESSAGING_CWD` added to `keys_to_drop` and `_configured_terminal_cwd` project alignment validation:
- Fresh and `--resume latest` launches strip `TERMINAL_CWD`, `MESSAGING_CWD`, and `HERMES_CWD`.
- Child executable process cwd and `PWD` match the resolved project root `str(self.project_dir.resolve())`.
- Legitimate `terminal.cwd` in `config.yaml` matching the project root is accepted and preserved for the runtime config bridge.
- Contradictory `terminal.cwd` in `config.yaml` is visibly refused with `ActivationError` (code 2), preventing silent misrouting.

---

## 3. Requirement to verification mapping

| Requirement / Clause | Verification check | Observed result | Evidence status |
|---|---|---|---|
| AC-6: Scrub inherited transport selectors | `tests/test_aether_tui_launcher.py::TuiPreservationTests::test_regression_contaminated_parent_cannot_select_old_backend` | PASS: child does not inherit stale `HERMES_PYTHON`, `HERMES_PYTHON_SRC_ROOT`, `HERMES_RPC_SOCKET`, `HERMES_TUI_GATEWAY_URL`, or `VIRTUAL_ENV` | Direct |
| AC-6: Scrub inherited modern cwd selectors (TERMINAL_CWD, MESSAGING_CWD) | `tests/test_aether_tui_launcher.py::TuiPreservationTests::test_regression_contaminated_parent_cannot_override_project_cwd_with_terminal_or_messaging_cwd` | PASS: child does not inherit contaminated `TERMINAL_CWD` or `MESSAGING_CWD`, child cwd and PWD match resolved project root in fresh and resume launches, legitimate project-matching config is accepted and preserved, and contradictory `terminal.cwd` is visibly refused with `ActivationError` | Direct |
| AC-6: Bind target interpreter and source root after scrubbing | `tests/test_aether_tui_launcher.py::TuiPreservationTests::test_launch_scrubs_inherited_transport_and_binds_target_in_clean_and_contaminated_envs` | PASS: child receives exact target `HERMES_PYTHON`, `HERMES_PYTHON_SRC_ROOT`, `HERMES_TUI_DIR`, `HERMES_HOME`, `AETHER_PROJECT_ID`, `PWD` in both clean and contaminated envs; `_assert_bound_target_python` confirms lexical path and subprocess probe `sys.prefix`/`purelib` match release venv | Direct |
| AC-6: Symlink venv interpreter preserved without leaf dereference | `tests/test_aether_tui_launcher.py::TuiPreservationTests::_assert_bound_target_python` in all launch tests | PASS: `HERMES_PYTHON` equals lexical `<target_venv>/bin/python` symlink and differs from dereferenced base interpreter; subprocess probe confirms `sys.prefix` equals target venv | Direct |
| AC-6: Secondary case regular-file executable stub | `tests/test_aether_tui_launcher.py::TuiPreservationTests::test_target_python_supports_regular_file_executable_stub_secondary_case` | PASS: regular file executable inside target venv passing probe is accepted and returns lexical path | Direct |
| AC-6: Foreign or failing interpreter fails closed | `tests/test_aether_tui_launcher.py::TuiPreservationTests::test_target_python_rejects_foreign_or_failing_interpreter` | PASS: foreign `sys.prefix`, non-executable binary, or failing probe raises `ActivationError` and never binds silently | Direct |
| AC-6: Probe isolated from project-local imports | `tests/test_aether_tui_launcher.py::TuiPreservationTests::test_target_python_probe_isolated_from_project_local_imports` | PASS: probe runs with `python -I` and isolated cwd; project-local `sysconfig.py`/`sitecustomize.py` cannot spoof verdict | Direct |
| AC-6: Rejection of cross-release fallback via ambient root | `tests/test_aether_tui_launcher.py::TuiPreservationTests::test_target_python_rejects_cross_release_fallback_via_ambient_root` (ambient release venv under `XDG_DATA_HOME`, selected target venv holds `bin/hermes` and no interpreter, positive control asserts the ambient interpreter verifies inside its own venv, and `sys.executable` is patched to that ambient interpreter so the resolver's `sys.executable` fallback branch is exercised as the running release) | PASS: accepted venvs derive from the selected target alone, so the ambient release interpreter is never bound and resolution fails closed with `ActivationError`. RED before the correction (`e148f79c`): the same node copied into a disposable worktree fails with `AssertionError: ActivationError not raised`, and an equivalent in-process harness over the same fixture reports `RESULT: BOUND: <ambient release>/venv/bin/python` on `e148f79c` versus `RESULT: FAIL-CLOSED (ActivationError)` on this candidate | Direct |
| AC-6: Rejection of split corroboration across independent roots | `tests/test_aether_tui_launcher.py::TuiPreservationTests::test_target_python_rejects_split_corroboration_across_independent_roots` | PASS: probe and resolver require `sys.prefix` and `purelib` to corroborate the same target venv; split roots rejected | Direct |
| AC-6: Fresh and `--resume latest` in both environments | `tests/test_aether_tui_launcher.py::TuiPreservationTests::test_launch_scrubs_inherited_transport_and_binds_target_in_clean_and_contaminated_envs` | PASS: fresh launch and resume launch succeed in clean and contaminated envs with exact argv and target env | Direct |
| AC-6: Installed wheel console script lane | `tests/test_aether_tui_launcher.py::TuiPreservationTests::test_installed_wheel_console_script_lane_fresh_and_resume_latest` | PASS: installed console script scrubs contaminated env and exports target `HERMES_PYTHON`, `HERMES_PYTHON_SRC_ROOT`, `HERMES_TUI_DIR` | Direct |
| AC-6: Bare `aether` inside project directory | `tests/test_aether_tui_launcher.py::TuiPreservationTests::test_bare_aether_launch_in_project_cwd_clean_and_contaminated` | PASS: resolves project from cwd marker + registry, scrubs contaminated vars, binds target identities | Direct |
| AC-6: Non-mutating `--json` plan and reserved args | `tests/test_aether_tui_launcher.py::TuiPreservationTests::test_aether_project_json_non_mutating_and_reports_release_identity`, `test_json_mode_non_mutating_plan_keys` | PASS: zero filesystem mutation pre/post; plan keys match canonical contract; reserved args fail closed | Direct |
| AC-6: Source and TUI bit-for-bit preservation | `tests/test_aether_tui_launcher.py::TuiPreservationTests::test_launch_creates_no_build_artefacts_and_leaves_locked_hermes_source_unchanged` | PASS: pre/post SHA-256 inventories of locked source match bit-for-bit; no npm/build artifacts created | Direct |
| AC-6: Projections point to stable entry point | `tests/test_aether_tui_launcher.py::TuiPreservationTests::test_desktop_and_wsl_projections_point_to_stable_aether_entry_point` | PASS: Desktop and WSL entry points target `<runtime_current>/venv/bin/aether` and support `--resume latest` | Direct |
| Preservation: Other projection suites | `uv run --frozen pytest -q tests/test_tui_projections.py tests/test_lifecycle_projections.py` | PASS: 41 passed | Direct |
| Code quality: Ruff lint | `uv run --frozen ruff check src/aether_agents tests scripts` | PASS: All checks passed | Direct |
| Code quality: Ruff format | `uv run --frozen ruff format --check src/aether_agents tests scripts` | PASS: 175 files already formatted | Direct |
| Code quality: Mypy static typing | `uv run --frozen mypy src/aether_agents` | PASS: Success: no issues found in 68 source files | Direct |
| Hygiene: Public artifacts scan | `uv run --frozen python scripts/check_public_artifacts.py` | PASS: public artifact path scan passed | Direct |
| Hygiene: Documentation validation | `uv run --frozen python scripts/check_documentation.py` | PASS: documentation validation passed | Direct |

---

## 4. Attribution: Direct versus Reused Evidence

- **Direct evidence**:
  - `src/aether_agents/launcher.py`: implemented `_resolve_target_python`, `_probe_venv_interpreter`, and
    `_resolve_target_source_root`; expanded `keys_to_drop` to scrub all transport selectors, stale RPC/gateway/socket
    paths, active session files, and virtualenv variables; bound `HERMES_PYTHON` and `HERMES_PYTHON_SRC_ROOT` to
    target release identities. `_resolve_target_python` preserves lexical symlinks, confines accepted venvs strictly to
    the selected target (no ambient fallback), verifies `sys.prefix` and `purelib` corroborate the same venv via an
    isolated probe (`python -I` and isolated cwd), and fails closed with `ActivationError` if no candidate qualifies.
  - `tests/test_aether_tui_launcher.py`: modeled the real symlinked venv layout in test fixtures with `pyvenv.cfg`,
    implemented `_assert_bound_target_python` verifying both lexical path equality and subprocess probe results,
    added `test_target_python_supports_regular_file_executable_stub_secondary_case`,
    `test_target_python_rejects_foreign_or_failing_interpreter`,
    `test_target_python_probe_isolated_from_project_local_imports`,
    `test_target_python_rejects_cross_release_fallback_via_ambient_root` (positive control proving the
    ambient interpreter verifies inside its own venv, with `sys.executable` patched to it so the
    resolver's fallback branch is genuinely exercised),
    `test_target_python_rejects_split_corroboration_across_independent_roots`,
    and `test_regression_contaminated_parent_cannot_override_project_cwd_with_terminal_or_messaging_cwd`, and updated all launch tests to assert target venv confinement and modern cwd selector scrubbing.
  - Focused test suite execution: `tests/test_aether_tui_launcher.py` (37 passed, 13 subtests passed).
- **Reused evidence**:
  - Unchanged projection spec generator tests (`tests/test_tui_projections.py`, `tests/test_lifecycle_projections.py`),
    reused from rc5 at unchanged code identity.
  - Locked source tree inventory and no-build/npm assertions from `TuiPreservationTests`, reused at unchanged structure.

---

## 5. Tracked file manifest lines

No tracked non-`specs/` files were added, renamed, or removed in this unit:
- `src/aether_agents/launcher.py` (modified existing file)
- `tests/test_aether_tui_launcher.py` (modified existing file)
- `specs/001-aether-v1-productization/evidence/RC6-LAUNCH.md` (this file; located under `specs/`, excluded from policy manifest)

Manifest lines to add to `.github/workflows/policy.yml`: **none**.

---

## 6. Residual risk and environment limits

- **Residual risk**: Target interpreter resolution relies on the release venv containing an executable Python binary
  or symlink and a valid `pyvenv.cfg` so Python initializes `sys.prefix` and `purelib` matching the release venv.
  If an installed release venv is damaged (e.g. missing interpreter or unresolvable purelib), the launcher fails closed
  with `ActivationError` (exit code 2) rather than silently executing with a foreign or ambient interpreter.
  Live canary qualification in RC6-QUAL and RC6-CLOSE exercises the end-to-end launch on real release trees.
- **Residue observation**: In disposable launcher qualification lanes, launching the full TUI front-end can spawn a
  background `tui_gateway` server process that remains active after the interactive TUI process terminates.
  Test suites use subprocess isolation with short-lived stubs to avoid process leaks; manual and qualification test lanes
  should actively monitor and clean lingering background gateway processes.
- **Environment limits**:
  - Full mixed-version qualification (`scripts/qualify_mixed_version_lifecycle.py`) and live canary activation
    belong to downstream units RC6-QUAL and RC6-CLOSE.
  - Base `policy.yml` manifest reconciliation belongs to RC6-DOCS / RC6-INT.
