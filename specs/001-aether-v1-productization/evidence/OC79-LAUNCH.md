# OC79-LAUNCH — Open Verified Unborn-Root Intake and Remove Sole-Project Fallback

**Unit**: OC79-LAUNCH (`t_2e35f5cf`), role Implementer, worktree branch
`aether-agents-2/t_2e35f5cf-oc79-launch-open-verified-unborn-root-in`.
**Authority**: Objective Contract `oc_79b55027e7c3688d@v1`
(SHA-256 `0b685dbfd7deb68e1b526a76b71d057d021f9bbf3984fff8c398ccd62ba9cca6`), base commit
`004c5f076da9e7be4fd64e4bc2adc60e21d4a2f6`, Supervisor breakdown
`specs/001-aether-v1-productization/tasks-oc79.md` (committed at `f71a3677` on the root branch).
**Delivered scope**: AC3; A1-FR-043, A1-FR-043a, A1-FR-100, A1-SC-018/019; `contracts/cli.md` launch section.
**Unit compatibility conclusion**: `patch`.

---

## 1. Summary of Changes

1. **Open without `AGENTS.md` (A1-FR-043a, A1-FR-100, A1-SC-019)**:
   - Removed the five obsolete `(repo / "AGENTS.md").is_file()` checks in `src/aether_agents/launcher.py`:
     - Line ~290: inside `_resolve_project` route (1) (explicit `--project PATH` or `AETHER_PROJECT_ROOT`).
     - Line ~337: inside `_resolve_project` route (2) (explicit verified `AETHER_PROJECT_ID`).
     - Line ~358: inside `_resolve_project` route (3) (current repository marker or nearest initialized parent).
     - Line ~377: inside `_resolve_project` route (5) (the former sole-project fallback).
     - Line ~659: inside `inspect_activation` (the activation validation gate).
   - A verified initialized repository whose `.aether/project.toml` agrees with the local project registry opens Morfeo without requiring a root `AGENTS.md` or a Git commit.
   - All other identity, source, profile, config, SOUL, runtime executable, TUI directory, toolset, and terminal cwd checks remain strictly fail-closed. Missing `AGENTS.md` is permitted only as an onboarding condition on the verified route.

2. **Removal of Sole-Project Fallback (A1-FR-043)**:
   - Removed `_resolve_project` route (5) fallback that previously resolved a sole registered project when invoked from an unrelated uninitialized cwd.
   - When cwd has no initialized project and no explicit project selection is provided, the launcher now refuses with actionable `git init` / `aether init` guidance:
     `"current directory is not an initialized Aether project; run 'git init' and 'aether init' to initialize"`
     even when exactly one project is registered in the project registry.
   - Multiple registered projects without an explicit selection continue to refuse with `ambiguous project identity`.
   - Empty registry without an explicit selection continues to refuse with `"no Aether project found and project registry is empty"`.

3. **Exact Selection Preserved**:
   - Explicit `--project PATH` (relative values normalize against invocation cwd, empty refused).
   - `AETHER_PROJECT_ROOT` (absolute only, empty/relative refused).
   - `AETHER_PROJECT_ID` (canonical UUID agreeing with marker and registry).
   - Current directory or nearest initialized parent (verifying `.aether/project.toml` and exact-path registry agreement).
   - No display-name, session-recency, board-default, or approximate-path inference.

4. **Conversation Readiness is not a Model Reply**:
   - The launcher deliverable validates and establishes agent readiness, component path resolution, transport environment scrub, and launch plan formation.
   - Real provider replies and live conversation transcripts are explicitly excluded from this objective's deliverable and remain Morfeo runtime interactions.

---

## 2. Requirement and Acceptance Coverage

| Obligation | Requirement | Verification Check | Result |
| --- | --- | --- | --- |
| AC3 | Open without `AGENTS.md` and without commit | `test_launch_verified_unborn_root_without_agents_md_and_without_commit` | PASS |
| AC3 | No sole-project fallback | `test_project_resolution_sole_registered_project` | PASS |
| A1-FR-043 | Exact selection, no sole fallback | `test_project_resolution_sole_registered_project`, `test_observation_usage_guidance.py` | PASS |
| A1-FR-043a | Verified route proof, missing `AGENTS.md` onboarding-only | `test_component_path_resolutions`, `test_launch_verified_unborn_root_without_agents_md_and_without_commit` | PASS |
| A1-FR-100 | First conversation opens before `AGENTS.md` exists | `test_launch_verified_unborn_root_without_agents_md_and_without_commit` | PASS |
| A1-SC-019 | Unborn empty root flow without first commit or `AGENTS.md` | `test_launch_verified_unborn_root_without_agents_md_and_without_commit` | PASS |

---

## 3. Decisive RED / GREEN Evidence

### Red: Sole-Project Node against Pre-fix Source

Executing the rewritten test against the pre-fix implementation where route (5) silently fell back to the sole registered project:

```text
$ uv run --frozen python scripts/run_tests.py -- tests/test_aether_tui_launcher.py -k test_project_resolution_sole_registered_project
============================= test session starts ==============================
platform linux -- Python 3.13.15, pytest-9.1.1, pluggy-1.6.0
rootdir: /home/darkarty/Desktop/agentes/aether/.worktrees/t_2e35f5cf
configfile: pyproject.toml
plugins: anyio-4.14.2, cov-6.3.0
collected 44 items / 43 deselected / 1 selected

tests/test_aether_tui_launcher.py F                                      [100%]

=================================== FAILURES ===================================
____ MorfeoTuiLauncherTests.test_project_resolution_sole_registered_project ____

self = <test_aether_tui_launcher.MorfeoTuiLauncherTests testMethod=test_project_resolution_sole_registered_project>

    def test_project_resolution_sole_registered_project(self) -> None:
        from aether_agents.launcher import ActivationError, inspect_activation

        non_repo_dir = Path(self.tempdir.name) / "empty_dir"
        non_repo_dir.mkdir(parents=True)

        # An unrelated uninitialized cwd must refuse with actionable guidance even
        # when a sole project is registered (A1-FR-043 removes the sole-project fallback).
        with patch.object(Path, "cwd", return_value=non_repo_dir):
>           with self.assertRaises(ActivationError) as ctx:
                 ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
E           AssertionError: ActivationError not raised

tests/test_aether_tui_launcher.py:731: AssertionError
=========================== short test summary info ============================
FAILED tests/test_aether_tui_launcher.py::MorfeoTuiLauncherTests::test_project_resolution_sole_registered_project
======================= 1 failed, 43 deselected in 0.47s =======================
```

### Green: Sole-Project Node on Candidate

```text
$ uv run --frozen python scripts/run_tests.py -- tests/test_aether_tui_launcher.py -k test_project_resolution_sole_registered_project
============================= test session starts ==============================
platform linux -- Python 3.13.15, pytest-9.1.1, pluggy-1.6.0
rootdir: /home/darkarty/Desktop/agentes/aether/.worktrees/t_2e35f5cf
configfile: pyproject.toml
plugins: anyio-4.14.2, cov-6.3.0
collected 45 items / 44 deselected / 1 selected

tests/test_aether_tui_launcher.py .                                      [100%]

======================= 1 passed, 44 deselected in 0.48s =======================
```

### Green: Positive Case for Verified Unborn Root without `AGENTS.md` and without Commit

```text
$ uv run --frozen python scripts/run_tests.py -- tests/test_aether_tui_launcher.py -k test_launch_verified_unborn_root_without_agents_md_and_without_commit
============================= test session starts ==============================
platform linux -- Python 3.13.15, pytest-9.1.1, pluggy-1.6.0
rootdir: /home/darkarty/Desktop/agentes/aether/.worktrees/t_2e35f5cf
configfile: pyproject.toml
plugins: anyio-4.14.2, cov-6.3.0
collected 45 items / 44 deselected / 1 selected

tests/test_aether_tui_launcher.py .                                      [100%]

======================= 1 passed, 44 deselected in 0.48s =======================
```

---

## 4. Cross-File Oracle Verification

The cross-file oracle `tests/test_observation_usage_guidance.py` was executed directly against the candidate:

```text
$ uv run --frozen python scripts/run_tests.py -- tests/test_observation_usage_guidance.py -q
.........                                                                [100%]
9 passed in 0.17s
```

**Result**: PASS unchanged (exit code 0, 9 passed).
The resolver changes do not invalidate the precedence assertions in `test_documented_project_selection_precedence_matches_the_implemented_resolver` (which uses a two-project registry where multiple registered projects raise `ambiguous project identity`), and `docs/**` was not modified in this unit.

---

## 5. Verification Commands and Results

1. **Focused Lane**:
   ```text
   $ uv run --frozen python scripts/run_tests.py -- tests/test_project_init.py tests/test_aether_tui_launcher.py tests/test_observation_cli_plugin.py tests/test_observation_passive_startup.py tests/test_observation_usage_guidance.py -q
   ............................................................. [ 37%]
   ...................................................................... [ 80%]
   ...............................                                          [100%]
   162 passed, 13 subtests passed in 42.82s
   Exit code: 0
   ```

2. **Ruff Check**:
   ```text
   $ uv run --frozen ruff check src/aether_agents tests scripts
   All checks passed!
   Exit code: 0
   ```

3. **Ruff Format**:
   ```text
   $ uv run --frozen ruff format --check src/aether_agents tests scripts
   181 files already formatted
   Exit code: 0
   ```

4. **Mypy**:
   ```text
   $ uv run --frozen mypy src/aether_agents
   Success: no issues found in 69 source files
   Exit code: 0
   ```

5. **Git Diff Check**:
   ```text
   $ git diff --check
   Exit code: 0
   ```

---

## 6. Manifest Impact

No tracked non-`specs/` files were added, renamed, or deleted by this unit. The existing tracked files `src/aether_agents/launcher.py` and `tests/test_aether_tui_launcher.py` were modified in place. The public evidence file `specs/001-aether-v1-productization/evidence/OC79-LAUNCH.md` is under `specs/` and excluded from the `.github/workflows/policy.yml` manifest by design.

---

## 7. Remaining Risk and Downstream Handoff

- **Remaining Risk**: None within this unit. The implementation strictly adheres to the hard constraints: `_resolve_component_paths` precedence is preserved, inherited-transport scrub is unmodified, sorted JSON keys contract is maintained, and all operations remain local without live effects.
- **Downstream Handoff**: `OC79-DOCS` (`t_9993248c`) can update documentation regarding the removal of the sole-project fallback and `AGENTS.md` optionality during greenfield intake.
