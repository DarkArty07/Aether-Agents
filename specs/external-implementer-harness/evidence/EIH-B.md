# EIH-B Evidence — Gateway Override and Launcher Routing

**Unit**: EIH-B
**Objective Contract**: `oc_f1ea2c4a2e0662da@v1`
**Owning Issue**: [#563](https://github.com/DarkArty07/Aether-Agents/issues/563)
**Base Commit**: `2221302f1c93fb4ffd166df9b5482aa2fecaef7a` (on top of EIH-A `fd1e7128e3b00769cb65061e8066ddf290305370`)
**Task ID**: `t_d3197963`
**Profile**: `implementer`

---

## 1. Outcome Summary

Implemented the console script `aether-kanban-worker` and gateway `HERMES_BIN` plugin override per EIH-01, EIH-03, AC1, AC3, plan §3.4/§3.5, and Supervisor decomposition correction `t_f6160bfc` (shared decisions 14 and 14a):
1. `pyproject.toml` declares the console script `aether-kanban-worker = "aether_agents.kanban_worker_launcher:main"`.
2. In `aether_agents.objective_contracts.hermes_plugin.register`, after the existing Morfeo profile check, sets `os.environ["HERMES_BIN"]` to the absolute path of `aether-kanban-worker` resolved from the running release's own scripts directory without passing through the `runtime/current` selector. Set only when the path is a regular executable file; otherwise leaves the environment unchanged. Repeated registration is idempotent.
3. The launcher evaluates attempt eligibility against all seven plan section 3.5 conditions:
   - Required environment variables (`HERMES_KANBAN_TASK`, `HERMES_KANBAN_RUN_ID`, `HERMES_KANBAN_CLAIM_LOCK`, `HERMES_KANBAN_DB`, `HERMES_KANBAN_BOARD`, `HERMES_KANBAN_WORKSPACE`, `HERMES_PROFILE`) are present and the workspace directory exists.
   - `HERMES_PROFILE` is `implementer`.
   - `board.json` in the same canonical board directory as `HERMES_KANBAN_DB` (rejecting symlinks, non-directories, and path redirection outside canonical board root) carries an Aether contract identity and `aether_implementer_harness == "claude-code"`.
   - `HERMES_KANBAN_GOAL_MODE` is not `1`.
   - The attempt is a work claim: latest `claimed` event has no `source_status: "review"`, `HERMES_KANBAN_REVIEW_AFFINITY` is unset, and `argv` has no `--resume`.
   - `argv` pins no Hermes model or effort (`-m`, `--model`, `--provider`, `--reasoning`). Profile-derived `--toolsets` and `--skills` pins do not affect eligibility.
   - A `claude` executable resolves on `PATH`.
4. When all conditions hold, the launcher routes the attempt to the fixed adapter seam `aether_agents.claude_code_adapter.run_attempt(argv, env)` per shared decision 14a, passing the full dispatcher argument vector (including `argv[0]`) and unchanged environment, returning its integer exit code (0, 76, 143).
5. The adapter is imported strictly inside the eligible branch; the pass-through path never imports `aether_agents.claude_code_adapter`.
6. Otherwise — and on any exception while deciding (missing or corrupt board file, unreadable database, malformed event payload) — the launcher replaces itself via `execv` with the Hermes entry point the dispatcher would have resolved without the override (`hermes` on inherited `PATH`, else `sys.executable -m hermes_cli.main`), preserving the unchanged argv tail and environment, and never re-reading `HERMES_BIN`.

---

## 2. Modification Boundary Verification

- **Modified Files**:
  - `pyproject.toml`:
    - Added `aether-kanban-worker = "aether_agents.kanban_worker_launcher:main"` under `[project.scripts]`.
  - `src/aether_agents/objective_contracts/hermes_plugin.py`:
    - Applied after EIH-A commit `fd1e7128e3b00769cb65061e8066ddf290305370`.
    - Added `_passes_through_runtime_current`, `_resolve_running_release_launcher`, and `_configure_hermes_bin_override`.
    - Invoked `_configure_hermes_bin_override()` in `register` immediately after Morfeo profile check.
  - `src/aether_agents/kanban_worker_launcher.py`:
    - New module implementing the console script entry point `main`, `is_eligible_for_claude_code`, and `pass_through_to_hermes`.
  - `tests/test_kanban_worker_launcher.py`:
    - 42 new focused unit tests covering plugin override, routing eligibility conditions 1–7 independently, decision exceptions, exact pass-through execution, adapter exit code propagation, and absence of adapter imports on pass-through.
  - `specs/external-implementer-harness/evidence/EIH-B.md`:
    - This evidence receipt.

- **Preserved Boundaries**:
  - `src/aether_agents/objective_contracts/store.py` (untouched; owned by EIH-A).
  - Selection parameter, schema, projection, and reuse validation in `hermes_plugin.py` (untouched; owned by EIH-A).
  - Claude adapter implementation, worker MCP server, and PD-71 hook (untouched; owned by EIH-C).
  - Guidance, documentation, and SOUL files (untouched; owned by EIH-D).
  - `policy/` and `src/aether_agents/resources/` (untouched).
  - Canonical Objective Contract and specs design artifacts (untouched).
  - No real Claude Code calls made; no live boards, live Hermes homes, or runtime selector accessed.
  - No secrets, credentials, or operator home paths added.

---

## 3. Verification and Evidence Matrix

| Check | Command | Observed Result | Evidence Location |
| --- | --- | --- | --- |
| Focused launcher routing suite | `uv run --frozen pytest tests/test_kanban_worker_launcher.py -q` | 42 passed in 8.75s | `tests/test_kanban_worker_launcher.py` |
| Focused launcher with exact checkout | `uv run --frozen python scripts/run_tests.py tests/test_kanban_worker_launcher.py` | 42 passed in 7.66s | `tests/test_kanban_worker_launcher.py` |
| EIH-A selection suite regression | `uv run --frozen python scripts/run_tests.py tests/test_implementer_harness_selection.py` | 15 passed in 15.61s | `tests/test_implementer_harness_selection.py` |
| Full contract test suite regression | `uv run --frozen python scripts/run_tests.py tests/test_objective_contracts.py` | 45 passed in 79.25s | `tests/test_objective_contracts.py` |
| Console script execution test | `uv run --frozen aether-kanban-worker --help` | Successfully replaces itself via execv with hermes help output (exit code 0) | Subprocess execution |
| Linter check | `uv run --frozen ruff check src/aether_agents/kanban_worker_launcher.py src/aether_agents/objective_contracts/hermes_plugin.py tests/test_kanban_worker_launcher.py` | All checks passed! | Source tree |
| Formatter check | `uv run --frozen ruff format --check src/aether_agents/kanban_worker_launcher.py src/aether_agents/objective_contracts/hermes_plugin.py tests/test_kanban_worker_launcher.py` | 3 files already formatted | Source tree |
| Type check | `uv run --frozen mypy src/aether_agents/kanban_worker_launcher.py src/aether_agents/objective_contracts/hermes_plugin.py` | Success: no issues found in 2 source files | Source tree |
| Whitespace & git check | `git diff --check` | Clean (exit code 0) | Git diff |

### Quickstart §1 Bullet Mapping

1. **Plugin override**:
   - `HERMES_BIN` set only for a valid release launcher resolved outside `runtime/current`: verified in `test_plugin_override_sets_hermes_bin_for_valid_release_launcher`.
   - Repeated registration is idempotent: verified in `test_plugin_override_idempotent`.
   - Missing launcher leaves `HERMES_BIN` unchanged: verified in `test_plugin_override_leaves_env_unchanged_when_launcher_missing`.
   - Non-executable launcher leaves `HERMES_BIN` unchanged: verified in `test_plugin_override_leaves_env_unchanged_when_launcher_not_executable`.
   - Directory named launcher leaves `HERMES_BIN` unchanged: verified in `test_plugin_override_leaves_env_unchanged_when_launcher_is_directory`.
   - Path passing through `runtime/current` refused: verified in `test_plugin_override_rejects_path_passing_through_runtime_current`.
   - Symlinks outside `runtime/current` resolve to target release path: verified in `test_plugin_override_resolves_symlinks_outside_runtime_current`.
   - Non-Morfeo profiles do not trigger override: verified in `test_plugin_override_not_triggered_for_non_morfeo_profile`.

2. **Launcher routing**:
   - Fully eligible attempt reaches the adapter seam `aether_agents.claude_code_adapter.run_attempt(argv, env)`: verified in `test_baseline_eligible_attempt_reaches_adapter_seam`.
   - Adapter return codes (0, 76, 143) returned directly: verified in `test_eligible_returns_adapter_exit_codes`.
   - Ineligible attempts never import `claude_code_adapter`: verified in `test_passthrough_never_imports_claude_code_adapter`.
   - Ineligible attempt replaces process via execv with unchanged argv tail and environment: verified in `test_passthrough_preserves_argv_tail_and_env`.
   - Condition 1 (each required env var missing independently, non-existent workspace) forces pass-through: verified in `test_condition_1_*`.
   - Condition 2 (profile not `implementer`) forces pass-through: verified in `test_condition_2_profile_not_implementer_forces_passthrough`.
   - Condition 3 (missing board.json, corrupt JSON, symlink board.json, symlink board directory, symlink database, directory redirection outside canonical boards root, missing contract identity, harness not `claude-code`, archived board) forces pass-through: verified in `test_condition_3_*`.
   - Condition 4 (`HERMES_KANBAN_GOAL_MODE == 1`) forces pass-through: verified in `test_condition_4_goal_mode_is_1_forces_passthrough`.
   - Condition 5 (claimed event `source_status: "review"`, review affinity set, argv contains `--resume`) forces pass-through: verified in `test_condition_5_*`.
   - Condition 6 (argv pins `-m`, `--model`, `--provider`, `--reasoning`) forces pass-through: verified in `test_condition_6_*`.
   - Condition 7 (`claude` not on `PATH`) forces pass-through: verified in `test_condition_7_claude_not_on_path_forces_passthrough`.
   - Decision exceptions (corrupt/unreadable SQLite DB, missing events table) force pass-through: verified in `test_decision_exception_*`.
   - Pass-through never re-reads `HERMES_BIN`: verified in `test_passthrough_never_rereads_hermes_bin`.
   - Fallback to `sys.executable -m hermes_cli.main` when `hermes` is not on `PATH`: verified in `test_passthrough_module_fallback_when_hermes_not_on_path`.

---

## 4. Unit Compatibility Conclusion

- **Compatibility impact**: `minor` (additive, opt-in).
  - Pre-change Hermes workers continue to receive identical invocation and environment via the pass-through path.
  - The `HERMES_BIN` override is scoped strictly to the Morfeo gateway process and only activates when the release's own launcher executable exists.
  - Any uncertainty, missing contract identity, unselected harness, review attempt, model override, or exception falls back seamlessly to the exact pre-change Hermes execution.
