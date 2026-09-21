# RC6-LAUNCH — Inherited Transport Selector Scrubbing and Packaged Launch Evidence (rc6)

**Unit**: RC6-LAUNCH (`t_fb74d205`) and continuation RC6-LAUNCH-2 (`t_b0975e1c`), role Implementer, worktree branch
`aether-agents-2/t_b0975e1c-rc6-launch-2-scrub-inherited-terminal_cw`.
**Continuation**: RC6-LAUNCH-3 (`t_92029d03`), role Implementer, worktree branch
`aether-agents-2/t_92029d03-rc6-launch-3-interpret-terminal.cwd-with`, base = accepted RC6-LAUNCH-2 tip
`4668a6ac5f5d1e19b20194c71a997d3bca5f5e1a`. Sections 1–6 are the LAUNCH / LAUNCH-2 receipt; section 7 is the
RC6-LAUNCH-3 continuation receipt.
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

---

## 7. RC6-LAUNCH-3 — `terminal.cwd` interpreted with the config grammar (`t_92029d03`)

**Base**: accepted RC6-LAUNCH-2 tip `4668a6ac5f5d1e19b20194c71a997d3bca5f5e1a` (detached worktree re-checked out at
that revision; the dispatcher-created branch had started from the main tip and was reset to the named accepted tip).
**Surface used**: `src/aether_agents/launcher.py`, `tests/test_aether_tui_launcher.py`, this file. The public CLI,
report keys, scrub list, `lifecycle.py`, docs and other units' tests were not touched.

### 7.1 Defect: a line scanner cannot establish "verified absence"

The U1 alignment gate in `inspect_activation` refuses only when a configured `terminal.cwd` is *seen* to contradict
the selected project. `_configured_terminal_cwd` recognised one textual shape (`terminal:` followed by an indented
`cwd:` line) and stripped everything after `#`, so for any other valid form its `None` meant "not seen" rather than
"no contradictory cwd" — the gate's non-refusal did not mean what the gate exists to certify.

Reproductions before this change, labelled by author:

| Author | Probe | Observed |
|---|---|---|
| design steward | synthetic config files read by the helper, `yaml.safe_load` as the reference interpretation | `terminal: {cwd: /tmp/foreign}` → helper `None`, YAML `/tmp/foreign`; `cwd: "/tmp/project#one"` → helper `/tmp/project`, YAML `/tmp/project#one`; block-style control agreed |
| Supervisor | the same table at helper level, plus an end-to-end probe on a disposable qualification lane (real PTY, RC6-LAUNCH-2 code) | the launcher did not refuse the flow-style probe, while the block-style control refused with exit 2 (`contradicts selected project`); `TERMINAL_CWD=/tmp/flow-foreign-dir` reached both the node TUI and its `tui_gateway` child — the consumer's own config bridge honoured exactly the contradiction the gate silently passed |
| this unit (RC6-LAUNCH-3) | helper table re-measured against both readers (§7.3) and an end-to-end RED receipt (§7.4) | both divergences reproduced; the base reader additionally returned the *string* `null` for `cwd: null` (a false refusal the consumer never asked for) |

### 7.2 Mechanism change

`_configured_terminal_cwd` now parses the profile config with the config grammar's own interpreter and reads
`terminal.cwd` from the parsed mapping. The line scanner and its `without PyYAML` docstring are deleted; no new
special case was added. The import is lazy, inside the helper, so module import stays as light as before for
`aether --version` and manager-side imports.

The consumer's interpretation, read read-only from the materialized `hermes-source/` of the locally installed
release (accepted maintained-fork source, not a second authority):

- `utils.py:767-771` — `_get_fast_yaml_loader()` returns `yaml.CSafeLoader`, falling back to `yaml.SafeLoader`.
- `utils.py:774-782` — `fast_safe_load(stream)` is `yaml.load(stream, Loader=…)`, documented as "behaviour is
  identical everywhere — only the speed differs".
- `hermes_cli/config.py:330` `import yaml`; `:3123` `read_raw_config()`; `:3186-3194` documented semantics
  (missing file → `{}`; unparseable YAML or other I/O errors → raises; non-dict root → `{}`).
- `hermes_cli/config.py:3434` `apply_terminal_config_to_env`; `:3486-3487` skips `cwd` values in
  `{".", "auto", "cwd"}`; `:3491` `os.path.expanduser`; `:3492-3493` writes the bridge variable;
  `:2198` reads `terminal_cfg.get("cwd", ".")`.

Semantics preserved, unchanged in `inspect_activation`: a configured value that resolves (after `~` expansion) to
the selected project is accepted and its config bytes are left untouched; a value that resolves elsewhere is
refused visibly with the existing `ActivationError` (exit 2, same message); absent key, `null`, `.`, `./`, `auto`,
`cwd` and empty stay unconstrained; the LAUNCH-2 `TERMINAL_CWD`/`MESSAGING_CWD` scrub is untouched.

### 7.3 Reader re-measurement (helper level, this unit)

Same probe script executed against the base tree (`4668a6ac`) and the candidate tree; reference column is
`yaml.safe_load` of the same document. `/tmp/…` fixture values only.

| config document | base reader | candidate reader | YAML reference |
|---|---|---|---|
| `terminal: {cwd: /tmp/foreign}` | `None` (not seen) | `/tmp/foreign` | `/tmp/foreign` |
| `terminal:` + `cwd: "/tmp/project#one"` | `/tmp/project` (truncated) | `/tmp/project#one` | `/tmp/project#one` |
| block style `cwd: /tmp/selected` (control) | `/tmp/selected` | `/tmp/selected` | `/tmp/selected` |
| `cwd: null` | `"null"` (string → would refuse) | `None` | `None` |
| `cwd: .` | `None` | `None` | `.` (runtime sentinel) |
| key absent | `None` | `None` | `None` |
| unparseable document containing a `cwd:` line | `/tmp/broken` (read from a broken document) | `None` (abstains, §7.5) | `YAMLError: ParserError` |

Loader equivalence: for the flow-style, quoted-`#` and unparseable documents, `yaml.safe_load` and the consumer's
call shape `yaml.load(stream, Loader=CSafeLoader)` return identical results (including `YAMLError: ParserError` on
the unparseable document), so the gate now reads the document the same way the runtime does.

Read-only witness: the live Morfeo profile's `terminal.cwd` still falls in the runtime's no-explicit-cwd sentinel
set, so the gate abstains for it exactly as before. No launch was performed against the live profile/installation.

### 7.4 RED receipt and post-fix verification

- **RED** — disposable detached worktree at `4668a6ac5f5d1e19b20194c71a997d3bca5f5e1a`, only the two new test nodes
  copied in from the candidate; every `HERMES_KANBAN_*` variable unset and a throwaway `TMPDIR`.
  Command: `uv run --frozen python scripts/run_tests.py -- -q
  "tests/test_aether_tui_launcher.py::TuiPreservationTests::test_regression_flow_style_terminal_cwd_is_interpreted_by_the_config_grammar"
  "tests/test_aether_tui_launcher.py::TuiPreservationTests::test_regression_quoted_terminal_cwd_with_hash_is_compared_faithfully"`.
  Observed: `2 failed in 1.09s` — `AssertionError: 0 != 2 :` for the flow-style node (the launcher launched instead
  of refusing) and `AssertionError: 0 != 2 :` for the quoted-`#` node (the contradictory value was truncated to the
  selected project and accepted). RED confirmed for both required regressions.
- **GREEN** — same command on the candidate: both nodes pass. Full focused suite on the candidate:
  `40 passed, 13 subtests passed` (37 passed + 13 subtests at the base tip). The installed-wheel lane passes too.
- Static gates on the candidate: `ruff check` clean, `ruff format --check` 175 files formatted, `mypy` clean
  (68 files), `python scripts/check_public_artifacts.py` passed. `python scripts/check_documentation.py` — carried
  as a lineage artifact on unit branches — also ran here and passed (exit 0), so nothing was left unrun.
- No real launch was exercised by this unit: the fixture suite launches the stub runtime, and the base-tree probe
  used the same fixture. No `tui_gateway` residue was produced and no live store, release tree or owner profile was
  written.

### 7.5 Boundary: an unreadable or unparseable config

Chosen posture: an unparseable profile config is **not** a launcher refusal class. The helper reports "no explicit
cwd" for it and the launch proceeds unchanged, so the runtime's own load semantics decide (per
`hermes_cli/config.py:3186-3194`: unparseable YAML raises there, and callers that prefer fail-open, last-known-good
or warn behaviour already carry that handling). Reasons: (a) a document the product's own grammar rejects cannot
describe a session either — the runtime raises for those same bytes, so the gate's abstention cannot leave a
contradictory cwd running; (b) inventing a launcher-level refusal would add a failure class the canonical design
never specified and would pre-empt the runtime's own diagnostics for the operator. Verified by the third regression
node (exempt forms accepted, unparseable config accepted by the launcher) and by the loader-equivalence probe.

An *unreadable* config is unchanged and fail-closed: the required-toolsets scan reads the same file first and
`main()` already maps `OSError`/`UnicodeError` to exit 2, which is the pre-existing behavior this unit did not
alter.

### 7.6 Boundary and residual risk carried by this change

- **Launcher-environment dependency on PyYAML.** The gate now needs a YAML interpreter in the launcher's own
  environment. The supported launch entry point is the projected `aether` console script inside the release
  runtime venv (`lifecycle.py:6590` `exec "$AETHER_RUNTIME_ROOT/venv/bin/aether"`, also the Desktop/WSL
  projections), and that environment carries PyYAML through the Hermes dependency closure — the installed rc5
  release's `runtime/lib/python3.13/site-packages` contains `yaml`, and `artifacts/hermes-requirements.txt` pins
  `pyyaml==6.0.3`. Measured counter-case: a wheel-only venv (`uv venv` + `uv pip install <wheel>`) cannot import it
  (`ModuleNotFoundError: No module named 'yaml'`), because the wheel declares `jsonschema` as its only runtime
  dependency and PyYAML is a *development*-group dependency of this repository. With the mechanism applied and the
  wheel-lane fixture untouched, three installed-wheel lanes failed with exactly that import error — recorded, not
  hidden. The fixture in the focused suite therefore installs `PyYAML>=6.0` beside the wheel and models the real
  launch closure member (comment in the fixture cites it). Declaring PyYAML in the *wheel's* runtime dependency
  metadata, and the matching release-lock / observer-requirements digest flow, is a packaging change outside this
  unit's surface: raised for the Supervisor instead of absorbed here. The failure mode is loud (import error), never
  a silent gate abstention.
- **`_top_level_toolsets` remains a line scanner** for the required-toolsets *presence* check. Deliberate
  non-change, out of this unit's scope: that check fails closed (a form it cannot read reports the toolset as
  missing and refuses), so it cannot produce the silent-pass defect corrected here. Flagged for the Supervisor.
- **Comparison semantics unchanged**: the change is *which value* is compared (`Path(...).resolve()` after `~`
  expansion), not how it is compared; quoting inside a YAML document is resolved by the grammar before comparison.
- **Isolation limit of the gate run**: the focused suite's own fixtures provide the throwaway HOME/XDG data+state/
  registry and build the environment of every subprocess they launch, so the gate was run with every
  `HERMES_KANBAN_*` routing variable unset and a throwaway `TMPDIR`, but with the developer `HOME`/uv cache still
  in place for the tooling itself.

### 7.7 Requirement → verification mapping (this unit)

| Obligation | Verification check | Observed result | Evidence status |
|---|---|---|---|
| Flow-style contradictory `terminal.cwd` is refused with the existing error | `…::test_regression_flow_style_terminal_cwd_is_interpreted_by_the_config_grammar` (RED at `4668a6ac`) | PASS: exit 2, `contradicts selected project`, configured value echoed; no launch | Direct |
| Flow-style cwd naming the selected project is accepted and preserved | same node, second case | PASS: exit 0, child `cwd`/`PWD` = resolved project, config bytes unchanged, no ambient selector in the child | Direct |
| Quoted value containing `#` is compared faithfully | `…::test_regression_quoted_terminal_cwd_with_hash_is_compared_faithfully` (RED at `4668a6ac`) | PASS: `<project>#one` refused as contradictory; a project whose own path contains `#` is accepted when named exactly | Direct |
| Exempt forms and unparseable config never turn into a launcher refusal | `…::test_regression_unconstrained_cwd_values_and_unparseable_config_never_refuse` | PASS: `null`, `.`, `auto`, `""`, absent key accepted; unparseable document leaves the launch to the runtime | Direct |
| Accepted semantics from RC6-LAUNCH-2 preserved | existing launch suites (block-style match/contradiction, contaminated parent scrub, fresh/resume, non-mutating `--json`) | PASS: 40 passed, 13 subtests passed | Direct |
| Gate/static checks | focused suite, `ruff check`, `ruff format --check`, `mypy src/aether_agents`, `check_public_artifacts.py` | PASS: 40 passed / 13 subtests; ruff clean; 175 files formatted; mypy clean (68 files); artifact scan passed | Direct |
| No live or remote effect | live witnesses read after the runs | No push/PR/merge/tag/release/activation/service restart/issue mutation. Witnesses: the live Morfeo profile `config.yaml` unchanged (only read), the live project registry unchanged, and no file in the active release tree newer than this run's start; the only state written during the window belongs to the running worker sessions and the live runtime itself. No `tui_gateway` process was started or killed by this unit | Direct |

### 7.8 Manifest lines

No tracked non-`specs/` file was added, renamed or removed: `src/aether_agents/launcher.py` and
`tests/test_aether_tui_launcher.py` are modified existing files and this evidence file is under `specs/`.
Manifest lines to add to `.github/workflows/policy.yml`: **none**.

## 8. RC6-LAUNCH-4 — `terminal.cwd` read through the selected runtime's YAML grammar (`t_42bbf99a`)

This unit continues RC6-LAUNCH / -2 / -3 on base **`d45daabe844f8a4e2a65484719321d1c49c2c93b`** (the accepted
RC6-LAUNCH-3 tip; the dispatcher-created worktree started from the repository's main tip and was reset to that
base before any edit). It changes the *mechanism* by which `terminal.cwd` is interpreted; it does not change
what the alignment check means. Mechanism commit: **`c77e9d75b8f7b6b0a67d8aa1975f4f1674e54e89`**; the commit
carrying this section adds only this section.

### 8.1 Steward disposition and its verified grounds

The plan paragraph that resolves the packaging question is U1, *"Delegated packaging disposition for the
configured-cwd check"*, in `specs/001-aether-v1-productization/plan-rc6.md` at commit
`e773e80929d15e05ed288f694e68b1546d4ecce3`. Its direction: keep the manager/wheel dependency closure,
interpret `terminal.cwd` with the **selected Hermes runtime's** real YAML grammar through a bounded,
isolated, fixed-operation read-only subprocess, reuse the selected lexical-venv provenance check, transport
only the cwd interpretation/status, and turn an unavailable interpreter into a bounded refusal rather than
verified absence.

Grounds re-verified in this unit (each one read, not recalled):

| Ground | Measurement | Where |
|---|---|---|
| The wheel declares one runtime dependency | `Requires-Dist: jsonschema==4.26.0` (only) in the built candidate wheel's `*.dist-info/METADATA`; `dependencies = ["jsonschema==4.26.0"]` in `pyproject.toml` | `pyproject.toml`; wheel metadata measured from this revision |
| The frozen reader requires *exact* dependency equality | `_OBSERVER_RUNTIME_DEPENDENCIES = {"jsonschema": "4.26.0"}`; the reader builds `expected_requirements = {f"{name}=={version}" …}` and raises `IntegrityError("candidate runtime dependencies mismatch")` when the sets differ | `src/aether_agents/lifecycle.py:904`, `:5779-5786` |
| The target runtime carries the pinned YAML provider | `<release>/artifacts/hermes-requirements.txt:562` is `pyyaml==6.0.3` in the inspected release tree; `uv.lock` resolves `pyyaml` to `6.0.3` | release artifact (inspected release tree), `uv.lock` |
| The launcher's own environment has no YAML interpreter | fixture self-check: the manager closure venv (wheel plus declared dependencies alone) exits non-zero with `No module named 'yaml'` for `python -I -c "import yaml"` | `tests/test_aether_tui_launcher.py` (`TuiPreservationTests.setUpClass`) |

Consequence: importing YAML inside the launcher would make the module depend on an undeclared package, and
declaring PyYAML in the wheel would break the exact `Requires-Dist` equality the frozen rc5 manager reader
enforces — invalidating the required rc5 → rc6 first hop. The mechanism therefore moves the grammar to the
selected runtime instead of moving a package into the manager closure.

### 8.2 Mechanism change

`src/aether_agents/launcher.py`:

- `import yaml` is **gone** from the module. The launcher runs correctly with the wheel's declared
  dependencies plus the standard library.
- `_configured_terminal_cwd(target_python, config)` now delegates the interpretation to the target runtime
  interpreter and keeps only launcher-side policy: the "no explicit cwd" sentinels
  (`null`, `.`, `./`, `auto`, `cwd`, empty, absent key) and the unparseable-document abstention.
- `inspect_activation` resolves that interpreter through the **existing** helper —
  `_resolve_target_python(hermes, AETHER_RUNTIME_ROOT)` — with its lexical-venv provenance discipline
  (isolated `sys.prefix`/`purelib` corroboration inside the target venv). No second provenance scheme was
  introduced.
- The exact-project comparison and its refusal are untouched:
  `Morfeo terminal.cwd (<value>) contradicts selected project (<repo>)`, `ActivationError` → exit 2.
- `--json`/`--check` remain non-mutating and keep exactly the same plan keys; the gate now also runs in those
  modes, so the check is a faithful predictor of the launch instead of a weaker sibling of it.

### 8.3 What the probe does and does not do

One fixed child, started as `<target python> -I -B -c <fixed script> <config path>`:

- **Isolated**: `-I` (no environment-derived path, no user site, no implicit cwd/script directory on
  `sys.path`) and `-B` (no bytecode writes). Environment passed to the child is the minimal
  `PATH`/`SYSTEMROOT`/`TMPDIR`/`TEMP`/`TMP` subset; `stdin` is `DEVNULL`; cwd is the interpreter's own
  directory, else the temporary directory; timeout 10 s; both streams captured.
- **Read-only**: the child opens one path for reading and prints one small JSON object. It performs no config
  migration, no plugin discovery, no service or model request, and no write.
- **Minimal verdict**: `{"status": "absent"}`, `{"status": "value", "cwd": "<string>"}`,
  `{"status": "malformed"}`, or `{"status": "unavailable"}` (the target runtime cannot import a YAML
  interpreter). Nothing else is transported — not the profile, not an environment value, not a secret, not a
  parser exception text or traceback.
- **Strictly parsed** on the launcher side: the last non-empty stdout line must be a JSON object with a
  recognised status; a `value` status must carry a string cwd. Anything else — non-zero exit, timeout, no
  output, unreadable or unrecognised status, missing value — is a refusal, never a guess.

### 8.4 Refusal semantics (stricter than RC6-LAUNCH-3, deliberately)

If the target runtime cannot be resolved/verified, cannot import a YAML interpreter, fails the probe, or
returns anything unusable, the gate refuses visibly: `ActivationError` → exit 2 with the stable message

```
aether: Morfeo terminal.cwd cannot be verified: the selected Hermes runtime provides no YAML interpreter (<bounded reason>)
```

No traceback, no `ModuleNotFoundError` text, and no silently "ready" plan. An unresolved interpreter must not
read as "no contradictory cwd": the abstention path stays reserved for the cases where the document *was*
interpreted (no explicit binding) or is the runtime's own error to surface (unparseable document).

### 8.5 Two closures in the test model

`tests/test_aether_tui_launcher.py`:

- The fixture's ad-hoc `PyYAML>=6.0` install beside the wheel is **removed**. The wheel lane is now the
  **manager closure**: the wheel plus its declared dependencies alone, asserted by the fixture itself
  (`import yaml` must fail there).
- The **target-runtime closure** is a real venv carrying the pinned provider (`pyyaml==6.0.3`), built once per
  test module and materialized per test by copy, so the provenance probe stays decisive and per-test mutation
  (a `chmod`, a removed interpreter) cannot leak between tests. The release venv of the preservation fixture is
  that closure; the module-level launcher fixture binds it as `home/.venv-hermes`; the separate
  runtime/state-root fixture in `MorfeoTuiLauncherTests` now also carries a runtime closure, because a real
  runtime store has one.
- New regressions: manager-closure delegation (contradiction refused / matching binding accepted /
  unparseable document still abstains), bounded refusal for a target runtime without a YAML interpreter and for
  an unverifiable interpreter, probe hygiene and isolation (bounded child, no secret or parser text, minimal
  environment, `-I`/`-B`, safe cwd), and isolation from a shadow `yaml` package on `PYTHONPATH`/cwd.

### 8.6 RED receipt

Command (identical in both trees; the wrapper only unsets `HERMES_KANBAN_*` and the ambient deployment roots
and supplies a throwaway `TMPDIR`):

```
uv run --frozen python scripts/run_tests.py -- -q tests/test_aether_tui_launcher.py
```

Base revision `d45daabe844f8a4e2a65484719321d1c49c2c93b` in a disposable detached worktree carrying **this
unit's** test module: **7 failed, 37 passed, 13 subtests passed**. Failures and their causes:

| Node | Observed at base | Cause |
|---|---|---|
| `…::TuiPreservationTests::test_installed_wheel_console_script_lane_fresh_and_resume_latest` | exit 1 with a traceback | `ModuleNotFoundError: No module named 'yaml'` — the manager closure cannot satisfy the in-process import |
| `…::TuiPreservationTests::test_aether_project_json_non_mutating_and_reports_release_identity` | exit 1 with a traceback | same |
| `…::TuiPreservationTests::test_launch_creates_no_build_artefacts_and_leaves_locked_hermes_source_unchanged` | exit 1 with a traceback | same |
| `…::TuiPreservationTests::test_rc6_launch4_manager_closure_interprets_terminal_cwd_via_target_runtime` | exit 1 with a traceback (expected 2) | same |
| `…::TuiPreservationTests::test_rc6_launch4_absent_yaml_interpreter_refuses_visibly` | exit 0 and a `"result": "ready"` plan on stdout (expected 2) | base reports a *verified absence* it never verified |
| `…::TuiPreservationTests::test_rc6_launch4_probe_child_is_bounded_and_carries_no_secret_or_parser_text` | `TypeError: _configured_terminal_cwd() takes 1 positional argument but 2 were given` | no bounded delegation child exists at base |
| `…::TuiPreservationTests::test_rc6_launch4_probe_is_isolated_from_a_shadow_yaml_package` | exit 2 with `aether: Morfeo terminal.cwd (<shadow-declared-foreign>) contradicts selected project (<project>)` | a project-local `yaml.py` on `PYTHONPATH` answers the gate at base |

The first four are the packaging defect applied to lanes that were green only while the fixture installed
PyYAML beside the wheel; the remaining three are the new semantic obligations.

### 8.7 Post-change verification (candidate)

At revision `c77e9d75b8f7b6b0a67d8aa1975f4f1674e54e89`:

| Check | Result |
|---|---|
| `uv run --frozen python scripts/run_tests.py -- -q tests/test_aether_tui_launcher.py` | PASS: **44 passed, 13 subtests passed** (40 + 4 new nodes, every previously green node still green) |
| `uv run --frozen ruff check src/aether_agents/launcher.py tests/test_aether_tui_launcher.py` | PASS: all checks passed |
| `uv run --frozen ruff format --check` (same files) | PASS: 2 files already formatted |
| `uv run --frozen mypy src/aether_agents` | PASS: no issues in 68 source files |
| `uv run --frozen python scripts/check_public_artifacts.py` | PASS: tracked surface + 0 artifacts |
| collateral: `tests/test_project_marker_validation.py` (the only other suite loading the launcher shim) | PASS: 15 passed |
| repository-wide `ruff check` / `ruff format --check` | identical at base and candidate: 4 pre-existing findings and 8 unformatted files, all in `lab/` and `specs/**/fixtures` or `specs/**/evidence` lineage artifacts outside this unit's surface |

Helper-level re-measurement of the delegated reader (scratch probe, forms and results recorded here):
absent key, `null`, `.`, `auto`, empty string, non-mapping `terminal` → no explicit cwd; block-style, flow-style
and quoted-`#` values, values with trailing comments, and a non-string scalar → returned exactly as the grammar
yields them; duplicate-key/scanner-invalid documents → abstention. With an interpreter that has no YAML
provider, every one of those forms refuses with the stable message.

### 8.8 Requirement → verification mapping (this unit)

| Obligation | Verification check | Observed result | Evidence status |
|---|---|---|---|
| No in-process YAML import; launcher works with the wheel's declared dependencies alone | `…::test_rc6_launch4_manager_closure_…` (RED at `d45daabe`), fixture self-check in `setUpClass` | PASS: manager closure has no YAML interpreter, gate still refuses a contradictory binding and still launches a matching one | Direct |
| `terminal.cwd` interpreted by the selected target runtime through a bounded, isolated, read-only subprocess | `…::test_rc6_launch4_manager_closure_…`, `…::test_rc6_launch4_probe_child_is_bounded_…` | PASS: `-I -B`, minimal env, safe cwd, `DEVNULL` stdin, bounded timeout, fixed script, no writes | Direct |
| Child carries only the interpretation/status | same hygiene node (raw child stdout/stderr inspected) | PASS: `{"status": …}` only; sentinel secret and parser text absent from child and launcher streams | Direct |
| Unavailable interpreter or missing parser ⇒ bounded refusal naming the capability | `…::test_rc6_launch4_absent_yaml_interpreter_refuses_visibly` (both check and launch modes, plus the unverifiable-interpreter case) | PASS: exit 2, stable message, no traceback, no launch | Direct |
| Preservation: exact-project comparison, flow-style and quoted-`#` fixes, sentinel forms, malformed disposition, selector scrub, fresh/resume, `--json` plan keys | the inherited RC6-LAUNCH/-2/-3 nodes and the launch suites | PASS: 44 passed, 13 subtests; plan keys unchanged | Direct |
| Two real closures modelled, ad-hoc PyYAML beside the wheel removed | `TuiPreservationTests.setUpClass` + the two fixture lanes | PASS: manager closure asserts no YAML; target runtime closure provides `pyyaml==6.0.3` | Direct |
| No live or remote effect | witnesses read after the runs | No push/PR/merge/tag/release/activation/service restart/issue mutation. The live profile `config.yaml`, the project registry and the active release pointer are unchanged; nothing in the active release tree was written during this unit's window (the only newer file there is the release manager venv's cached launcher bytecode, written before this card was claimed); the two running `tui_gateway` processes pre-date this unit's window and were neither started nor terminated by it; every fixture lane launches a stub Hermes, never a real TUI | Direct |

### 8.9 Boundary and residual risk carried by this change

- **The gate now needs a verifiable target runtime in every mode.** `--check` and `--json` refuse (exit 2)
  when the selected runtime's interpreter cannot be verified or provides no YAML interpreter, where they
  previously produced a plan. That is the intended strictness of this unit, and it is a *supported-route*
  statement the integration unit must carry: the projected `aether` entry point runs from the release runtime
  venv, which carries the pinned provider; a manager-only environment can no longer render a plan, and it
  fails loudly instead of silently.
- **Deliberate abstention kept**: an unreadable or unparseable profile document is still *not* a launcher
  refusal class — the runtime surfaces its own error for those bytes. Unreadable files are unreachable in
  practice because the required-toolsets read of the same file precedes the gate and refuses first.
- **Target interpreter resolved twice on a launch path**: once inside `inspect_activation` for the gate and
  once in `main` to bind `HERMES_PYTHON`. Both are the same deterministic, read-only resolution; the
  duplication was accepted to leave the `--json` plan surface byte-identical.
- **`_top_level_toolsets` remains a line scanner** (pre-existing, unchanged): it fails closed, so it cannot
  produce a silent pass. Flagged for the Supervisor, not changed here.
- **No packaging change**: PyYAML is still not declared in the wheel's runtime metadata, and no release-lock,
  closure or dependency change is part of this unit — that was the point of the disposition.

### 8.10 Manifest lines

No tracked non-`specs/` file was added, renamed or removed: `src/aether_agents/launcher.py` and
`tests/test_aether_tui_launcher.py` are modified existing files and this evidence file is under `specs/`.
Manifest lines to add to `.github/workflows/policy.yml`: **none**.
