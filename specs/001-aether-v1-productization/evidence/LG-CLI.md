# LG-CLI — Packaged launcher and exact project binding

**Unit**: LG-CLI (`t_7fab49b1`), role Implementer, worktree branch
`aether-agents-2/t_7fab49b1-lg-cli-packaged-launcher-and-exact-proje`.
**Authority**: Objective Contract `oc_ff82ba151cdf3861@v2`
(SHA-256 `e5c4fea02a5b1cee977c93a602d5af622b59e7325c9efb3be7d7b1e7bfc49bd0`), base commit
`00715d237d795e365c5e462b6b80d5a1bd8d8188`, Supervisor breakdown with shared decisions 1–7 and 12–15
(`specs/001-aether-v1-productization/tasks-rc4.md` at `155c67ea`). Never edited the contract.
**Delivered scope**: contract in-scope 1; acceptance obligations AC-1, AC-2; issue #480 launcher/CLI half;
breakdown unit LG-CLI.
**Unit compatibility**: `patch`.

## 1. Summary of changes

1. **Packaged launcher (`src/aether_agents/launcher.py`)**:
   - New Hermes-import-free module implementing public API `inspect_activation(extra_args=()) -> dict` and `main(argv=None) -> int`.
   - Exact project resolution following decision 6:
     1. Explicit `--project PATH` (or `AETHER_PROJECT_ROOT`), requiring valid `.aether/project.toml` and `AGENTS.md`, verifying agreement with registry if known, and rejecting conflict with explicit `AETHER_PROJECT_ID`.
     2. Explicit verified `AETHER_PROJECT_ID` when registry and portable marker both confirm it.
     3. Current repository marker or sole registered project only when registry and marker agree; otherwise fails visibly and nonzero.
   - Comprehensive environment scrub following decision 7:
     - Drops conflicting `PYTHON*` (`PYTHONPATH`, `PYTHONHOME`, `PYTHONSTARTUP`, etc.).
     - Drops `HERMES_PROFILE`.
     - Drops ambient `HERMES_TUI*` (`HERMES_TUI_DIR`, `HERMES_TUI_PORT`, etc.).
     - Drops inherited session, task, cron and Kanban launch residue (`HERMES_SESSION_ID`, `HERMES_KANBAN_*`, `HERMES_TASK*`, `HERMES_CRON_*`).
     - Preserves ordinary credentials (`OPENAI_API_KEY`, etc.) and configuration.
     - Sets exact `HERMES_HOME`, `AETHER_PROJECT_ID`, `PWD`, and release-owned `HERMES_TUI_DIR`.
   - Reserved binding flags policy: rejects `--in`, `--profile`, `--tui`, `--cli`, `--toolsets`, `-t`, `-p`, `--safe-mode`, `--ignore-user-config`, `--ignore-rules`. Permitted passthrough flags like `--resume latest` are preserved.
   - Non-mutating JSON launch plan (`--json` or `--check`): returns `result="ready"` with exact 9 sorted keys: `command`, `cwd`, `hermes_executable`, `hermes_home`, `project_id`, `repo_root`, `required_toolsets`, `result`, `tui_dir`.

2. **CLI dispatch (`src/aether_agents/cli.py`)**:
   - Bare `aether [--project PATH] [--json]` dispatches directly to packaged `aether_agents.launcher.main`, without `exec` of checkout `scripts/aether_tui.py`.
   - Top-level `--json` is no longer flagged unsupported; it passes to `launcher.main` and produces the launch plan.
   - Normalizes top-level `--resume <value>` tokens prior to subparser consumption so argparse subparsers do not treat the value token as an invalid subcommand choice, while preserving the raw two-token argv for `_run_launch`.
   - Tolerates unrecognized flags when `args.command is None` so launcher options (e.g. `--resume latest`) pass through to `launcher.main`.
   - Empty `--project` argument or empty `AETHER_PROJECT_ROOT` environment variable fails visibly with exit code 2 and descriptive stderr message, never guesses cwd, and never raises `AssertionError`.

3. **Checkout compatibility shim (`scripts/aether_tui.py`)**:
   - Thin shim delegating to `aether_agents.launcher.main`.
   - Re-exports `REQUIRED_TOOLSETS`, `_RESERVED_ARGS`, `ActivationError`, `_portable_project_id`, `inspect_activation`, `main`.
   - Defaults `AETHER_PROJECT_ROOT` to checkout root when invoked directly without `--project`.

4. **Launcher and marker validation test suite (`tests/test_aether_tui_launcher.py`)**:
   - Covers path/UUID/registry/marker agreement and conflict:
     - Explicit `--project PATH` with valid marker.
     - Conflict between marker and explicit `AETHER_PROJECT_ID`.
     - Conflict between marker and registry path.
     - Verified `AETHER_PROJECT_ID` resolution and unregistered/corrupt rejections.
     - Current repository marker agreement and un-registered disagreement.
     - Sole registered project resolution from non-repo directories and multi-project ambiguity rejection.
     - Missing project / empty registry rejection.
   - Covers `--json` non-mutation and exact plan keys.
   - Covers reserved argument refusal.
   - Covers env scrub of Kanban, session, task, cron, TUI residue, preserving credentials.
   - Covers `--resume latest` passthrough via both `launcher.main` and installed CLI `aether_agents.cli.main` (both `--resume latest` and bare `--resume`).
   - Covers empty identity refusal (`--project ""`, `Path("")`, `AETHER_PROJECT_ROOT=""`, etc.) via `inspect_activation` and `cli_main`, asserting exit 2, visible error, absence of `AssertionError`, and no cwd guess.
   - Covers clean installed-wheel launch path without checkout `scripts/`.
   - Verifies absence of machine-specific home paths.

## 2. Tracked file manifest changes

New tracked non-`specs/` path for LG-DOCS:
- `src/aether_agents/launcher.py`

Modified tracked paths:
- `scripts/aether_tui.py`
- `src/aether_agents/cli.py`
- `tests/test_aether_tui_launcher.py`

Preserved boundaries:
- `src/aether_agents/lifecycle.py` (untouched)
- `src/aether_agents/knowledge/*` (untouched)
- `VERSION` (untouched)
- `docs/**` (untouched)
- `.github/workflows/policy.yml` (untouched; LG-DOCS registers new tracked path)
- `.aether/objective-contracts/oc_ff82ba151cdf3861/v2.md` (never created, edited, staged, or copied)
- Owner primary checkout (untouched)

## 3. Verification evidence

| Check | Command | Observed result |
|---|---|---|
| Linter | `uv run --frozen ruff check src/aether_agents tests scripts` | All checks passed! (exit 0) |
| Formatter | `uv run --frozen ruff format --check src/aether_agents tests scripts` | 172 files already formatted (exit 0) |
| Type check | `uv run --frozen mypy src/aether_agents` | Success: no issues found in 68 source files (exit 0) |
| Unit tests | `uv run --frozen python scripts/run_tests.py -- tests/test_aether_tui_launcher.py tests/test_project_marker_validation.py` | 38 passed in 3.28s (exit 0) |
| Lifecycle/CLI tests | `uv run --frozen python scripts/run_tests.py -- tests/test_observation_lifecycle.py tests/test_observation_cli_plugin.py tests/test_telegram_monitor_cli_plugin.py tests/test_knowledge_plugin_cli.py` | 292 passed, 6 skipped in 139.13s (exit 0) |
| Branch coverage | `uv run --frozen coverage run -m pytest -q tests/test_aether_tui_launcher.py tests/test_project_marker_validation.py && uv run --frozen coverage report --include="src/aether_agents/launcher.py"` | 82% branch coverage on `src/aether_agents/launcher.py` (above 78% floor) |
| Wheel build | `uv build` | Successfully built `dist/aether_agents-1.0.0rc3-py3-none-any.whl` (exit 0) |
| Documentation check | `uv run --frozen python scripts/check_documentation.py` | Documentation validation passed (exit 0) |
| Installed console script verification | Installed wheel execution of `aether --project <root> --json --resume latest`, `aether --project <root> --json --resume`, `aether --project "" --json`, `AETHER_PROJECT_ROOT="" aether --json` | PASS: `--resume latest` and `--resume` return ready plan with `--resume latest` in command (exit 0); empty `--project` and `AETHER_PROJECT_ROOT=""` fail visibly with descriptive error (exit 2), no `AssertionError`, no cwd guess. |
| Clean launch path | Verification script executing `aether --project <path> --json` with no checkout `scripts/` tree present | PASS: clean launch plan generated without checkout `scripts/` dependency |
