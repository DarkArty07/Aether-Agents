# OC79-LAUNCH — Open Verified Unborn-Root Intake and Remove Sole-Project Fallback

**Unit**: OC79-LAUNCH (`t_2e35f5cf`), role Implementer, worktree branch
`aether-agents-2/t_2e35f5cf-oc79-launch-open-verified-unborn-root-in`.
**Authority**: Objective Contract `oc_79b55027e7c3688d@v1`
(SHA-256 `0b685dbfd7deb68e1b526a76b71d057d021f9bbf3984fff8c398ccd62ba9cca6`), base commit
`004c5f076da9e7be4fd64e4bc2adc60e21d4a2f6`, Supervisor breakdown
`specs/001-aether-v1-productization/tasks-oc79.md` (committed at `f71a3677` on the root branch).
**Delivered commit**: `9a8a31c5c2f27195ed9c84eeae5d9e8e974a4c71` (evidence-artifact delta on top of `25a20942baa9686fa4edc498740b8d0263bb1112`, which carries the behaviour change).
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

3. **Exact Selection and Route (1) Registry Proof (A1-FR-043a)**:
   - Explicit `--project PATH` and `AETHER_PROJECT_ROOT` now strictly prove `registry.knows(project_id)`, exact-path equality `registry.project_path(project_id) == repo`, and `registry.verify_with_marker(project_id)` before returning. An unregistered marker or path conflict fails closed with actionable guidance (`"run 'aether init' first"`).
   - Relative `--project PATH` values normalize against invocation cwd; empty values are refused.
   - `AETHER_PROJECT_ROOT` requires a non-empty absolute path; empty/relative values are refused.
   - `AETHER_PROJECT_ID` requires a canonical UUID agreeing with marker and registry.
   - Current directory or nearest initialized parent verifies `.aether/project.toml` and exact-path registry agreement.
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
| A1-FR-043a | Verified route proof, missing `AGENTS.md` onboarding-only | `test_check_supports_separated_runtime_and_state_roots`, `test_project_resolution_explicit_route_refuses_unregistered_marker`, `test_launch_verified_unborn_root_without_agents_md_and_without_commit` | PASS |
| A1-FR-100 | First conversation opens before `AGENTS.md` exists | `test_launch_verified_unborn_root_without_agents_md_and_without_commit` | PASS |
| A1-SC-019 | Unborn empty root flow without first commit or `AGENTS.md` | `test_launch_verified_unborn_root_without_agents_md_and_without_commit` | PASS |

---

## 3. Decisive RED / GREEN Evidence

All three transcripts below were produced at the reviewed candidate commit
`25a20942baa9686fa4edc498740b8d0263bb1112` (review round 2). The RED pairings swap
`src/aether_agents/launcher.py` for the pre-fix base revision
`004c5f076da9e7be4fd64e4bc2adc60e21d4a2f6` (sha256 `2805eec2…`) while keeping the
delivered test file in place. Provenance asserted on each run:

```text
c619171b6c5c9442759ddff4f50704e48340b1ef96ec6037bf4a17d5adb81255  src/aether_agents/launcher.py   (candidate)
2805eec234259f1d112a0fbb383851ba32094df30b512c24d5e074a6b5ff7213  /tmp/oc79_prefix_launcher.py    (pre-fix, swapped in for RED)
2805eec234259f1d112a0fbb383851ba32094df30b512c24d5e074a6b5ff7213  src/aether_agents/launcher.py   (verified in place during RED)
c619171b6c5c9442759ddff4f50704e48340b1ef96ec6037bf4a17d5adb81255  src/aether_agents/launcher.py   (restored after RED)
RED_EXIT=1  RED_EXIT2=1            # pytest exit codes for both RED pairings
```

`rootdir:` lines are quoted as `<repo-root>` to keep this public evidence file free of
operator paths.

### 3.1 Red: Rewritten Sole-Project Node against Pre-fix Source

At the pre-fix source the rewritten node proves the removed fallback: the unrelated
uninitialized cwd does not raise, so `assertRaises(ActivationError)` fails.

```text
$ uv run --frozen python scripts/run_tests.py -- tests/test_aether_tui_launcher.py -k test_project_resolution_sole_registered_project
============================= test session starts ==============================
platform linux -- Python 3.13.15, pytest-9.1.1, pluggy-1.6.0
rootdir: <repo-root>
configfile: pyproject.toml
plugins: anyio-4.14.2, cov-6.3.0
collected 46 items / 45 deselected / 1 selected

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

tests/test_aether_tui_launcher.py:804: AssertionError
=========================== short test summary info ============================
FAILED tests/test_aether_tui_launcher.py::MorfeoTuiLauncherTests::test_project_resolution_sole_registered_project
======================= 1 failed, 45 deselected in 0.47s =======================
```

### 3.2 Green: Rewritten Sole-Project Node on Candidate

```text
$ uv run --frozen python scripts/run_tests.py -- tests/test_aether_tui_launcher.py -k test_project_resolution_sole_registered_project
============================= test session starts ==============================
platform linux -- Python 3.13.15, pytest-9.1.1, pluggy-1.6.0
rootdir: <repo-root>
configfile: pyproject.toml
plugins: anyio-4.14.2, cov-6.3.0
collected 46 items / 45 deselected / 1 selected

tests/test_aether_tui_launcher.py .                                      [100%]

======================= 1 passed, 45 deselected in 0.23s =======================
```

### 3.3 Green: Positive Case for Verified Unborn Root without `AGENTS.md` and without Commit

The node creates a real `git init` repository with no commit (verified via
`git rev-parse --verify HEAD` returning non-zero), writes only
`.aether/project.toml`, registers the project, and asserts `inspect_activation()`
returns a launch plan. On the pre-fix source it fails at
`src/aether_agents/launcher.py:359` with
`Aether repository marker does not exist: .../unborn_project/AGENTS.md`, which pins
A1-FR-100 (first conversation opens before `AGENTS.md` exists).

Red on pre-fix source:

```text
$ uv run --frozen python scripts/run_tests.py -- tests/test_aether_tui_launcher.py -k test_launch_verified_unborn_root_without_agents_md_and_without_commit
============================= test session starts ==============================
platform linux -- Python 3.13.15, pytest-9.1.1, pluggy-1.6.0
rootdir: <repo-root>
configfile: pyproject.toml
plugins: anyio-4.14.2, cov-6.3.0
collected 46 items / 45 deselected / 1 selected

tests/test_aether_tui_launcher.py F                                      [100%]

=================================== FAILURES ===================================
_ MorfeoTuiLauncherTests.test_launch_verified_unborn_root_without_agents_md_and_without_commit _

self = <test_aether_tui_launcher.MorfeoTuiLauncherTests testMethod=test_launch_verified_unborn_root_without_agents_md_and_without_commit>

    def test_launch_verified_unborn_root_without_agents_md_and_without_commit(self) -> None:
        import subprocess
    
        from aether_agents.launcher import inspect_activation
        from aether_agents.launcher import main as launcher_main
    
        unborn_pid = "33333333-3333-4333-8333-333333333333"
        unborn_repo = Path(self.tempdir.name) / "unborn_project"
        unborn_repo.mkdir(parents=True)
    
        # 1. git init without any commit -> unborn repository
        subprocess.run(["git", "init", "-q", "-b", "main", str(unborn_repo)], check=True)
        # Verify it has no commits (HEAD does not resolve)
        proc = subprocess.run(
            ["git", "-C", str(unborn_repo), "rev-parse", "--verify", "HEAD"],
            capture_output=True,
            text=True,
        )
        self.assertNotEqual(proc.returncode, 0)
    
        # 2. Write portable project marker (.aether/project.toml), NO AGENTS.md
        marker = unborn_repo / ".aether" / "project.toml"
        marker.parent.mkdir(parents=True)
        marker.write_text(
            "\n".join(
                (
                    "schema_version = 1",
                    f'project_id = "{unborn_pid}"',
                    'name = "unborn-intake"',
                    'initialized_by = "1.0.0"',
                    'forge = "local"',
                    'contract_root = "specs"',
                    'default_branch = "main"',
                    "",
                )
            ),
            encoding="utf-8",
        )
        self.assertFalse((unborn_repo / "AGENTS.md").exists())
    
        # 3. Register in local project registry
        self.registry.register(unborn_pid, unborn_repo, name="unborn-intake")
    
        # 4. Copy isolated Morfeo home runtime fixtures so component paths resolve
        shutil.copytree(self.root / "home", unborn_repo / "home")
    
        # 5. Bare aether launch in cwd resolves project, binds Morfeo profile, ready
        with patch.object(Path, "cwd", return_value=unborn_repo):
>           plan = inspect_activation()
                   ^^^^^^^^^^^^^^^^^^^^

tests/test_aether_tui_launcher.py:870: 
_ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ 
src/aether_agents/launcher.py:653: in inspect_activation
    repo, project_id = _resolve_project(project)
                       ^^^^^^^^^^^^^^^^^^^^^^^^^
_ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ 

project_arg = None

    def _resolve_project(project_arg: str | Path | None = None) -> tuple[Path, str]:
        """Resolve exact project binding according to LG-CLI decision 6."""
        hermes_root = _absolute_env_path("AETHER_HERMES_ROOT")
        registry = _registry(hermes_root)
    
        # (1) Explicit --project PATH or AETHER_PROJECT_ROOT
        if project_arg is not None or "AETHER_PROJECT_ROOT" in os.environ:
            if project_arg is not None:
                if _is_empty_path(project_arg):
                    raise ActivationError("project path must not be empty")
                repo = Path(project_arg).expanduser().resolve()
            else:
                raw_root = os.environ.get("AETHER_PROJECT_ROOT", "").strip()
                if not raw_root:
                    raise ActivationError("AETHER_PROJECT_ROOT must not be empty")
                repo_env = _absolute_env_path("AETHER_PROJECT_ROOT")
                if repo_env is None:
                    raise ActivationError("AETHER_PROJECT_ROOT must not be empty")
                repo = repo_env.resolve()
    
            if not (repo / "AGENTS.md").is_file():
                raise ActivationError(f"Aether repository marker does not exist: {repo / 'AGENTS.md'}")
            project_id = _portable_project_id(repo)
    
            if "AETHER_PROJECT_ID" in os.environ:
                env_pid_raw = os.environ.get("AETHER_PROJECT_ID", "").strip()
                if not env_pid_raw:
                    raise ActivationError("AETHER_PROJECT_ID must not be empty")
                env_pid = canonical_project_id(env_pid_raw)
                if env_pid is None:
                    raise ActivationError(
                        f"AETHER_PROJECT_ID {env_pid_raw} is not a valid canonical UUID"
                    )
                if env_pid != project_id:
                    raise ActivationError(
                        f"explicit AETHER_PROJECT_ID {env_pid_raw} conflicts with project marker {project_id}"
                    )
    
            if registry.knows(project_id):
                registered = registry.project_path(project_id)
                if registered is not None and registered.resolve() != repo:
                    raise ActivationError(
                        f"project ID {project_id} conflicts with registered path: {registered}"
                    )
    
            return repo, project_id
    
        # (2) Explicit verified AETHER_PROJECT_ID when registry and portable marker agree
        if "AETHER_PROJECT_ID" in os.environ:
            raw_pid = os.environ.get("AETHER_PROJECT_ID", "").strip()
            if not raw_pid:
                raise ActivationError("AETHER_PROJECT_ID must not be empty")
            env_pid = canonical_project_id(raw_pid)
            if env_pid is None:
                raise ActivationError(f"AETHER_PROJECT_ID {raw_pid} is not a valid canonical UUID")
            if not registry.knows(env_pid):
                raise ActivationError(
                    f"AETHER_PROJECT_ID {env_pid} is not registered in the project registry"
                )
            loc = registry.project_path(env_pid)
            if loc is None or not loc.is_dir():
                raise ActivationError(f"registered project path for {env_pid} does not exist: {loc}")
            if not registry.verify_with_marker(env_pid):
                raise ActivationError(
                    f"project registry and portable marker do not agree for {env_pid}"
                )
            repo = loc.resolve()
            if not (repo / "AGENTS.md").is_file():
                raise ActivationError(f"Aether repository marker does not exist: {repo / 'AGENTS.md'}")
            return repo, env_pid
    
        # (3) Current repository marker or sole registered project only when registry and marker agree
        cursor = Path.cwd().resolve()
        repo_candidate: Path | None = None
        for candidate in (cursor, *cursor.parents):
            if (candidate / ".aether" / "project.toml").is_file():
                repo_candidate = candidate
                break
    
        if repo_candidate is not None:
            marker_pid = _portable_project_id(repo_candidate)
            reg_path = registry.project_path(marker_pid)
            if (
                registry.knows(marker_pid)
                and reg_path is not None
                and reg_path.resolve() == repo_candidate.resolve()
                and registry.verify_with_marker(marker_pid)
            ):
                if not (repo_candidate / "AGENTS.md").is_file():
>                   raise ActivationError(
                        f"Aether repository marker does not exist: {repo_candidate / 'AGENTS.md'}"
                    )
E                   aether_agents.launcher.ActivationError: Aether repository marker does not exist: /tmp/aether-tui-launcher-l0jmc9gy/unborn_project/AGENTS.md

src/aether_agents/launcher.py:359: ActivationError
=========================== short test summary info ============================
FAILED tests/test_aether_tui_launcher.py::MorfeoTuiLauncherTests::test_launch_verified_unborn_root_without_agents_md_and_without_commit
======================= 1 failed, 45 deselected in 0.45s =======================
```

Green on candidate:

```text
$ uv run --frozen python scripts/run_tests.py -- tests/test_aether_tui_launcher.py -k test_launch_verified_unborn_root_without_agents_md_and_without_commit
============================= test session starts ==============================
platform linux -- Python 3.13.15, pytest-9.1.1, pluggy-1.6.0
rootdir: <repo-root>
configfile: pyproject.toml
plugins: anyio-4.14.2, cov-6.3.0
collected 46 items / 45 deselected / 1 selected

tests/test_aether_tui_launcher.py .                                      [100%]

======================= 1 passed, 45 deselected in 0.47s =======================
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
   ................................                                         [100%]
   163 passed, 13 subtests passed in 40.10s
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

5. **Git Diff Check (CI-range form)**:
   The `.github/workflows/policy.yml` job checks the committed range, so the
   range form is recorded here rather than the argument-less form, which is a
   no-op once the work is committed:
   ```text
   $ git diff --check 004c5f07...HEAD
   Exit code: 0
   ```

6. **Public Artifact Privacy Gate**:
   ```text
   $ uv run --frozen python scripts/check_public_artifacts.py --root .
   public artifact path scan passed: tracked surface + 0 artifact(s)
   Exit code: 0
   ```
   `tests/test_public_artifacts.py::test_tracked_public_surface_contains_no_operator_paths`
   passes (reported separately in round 2 verification).

---

## 6. Manifest Impact

No tracked non-`specs/` files were added, renamed, or deleted by this unit. The existing tracked files `src/aether_agents/launcher.py` and `tests/test_aether_tui_launcher.py` were modified in place. The public evidence file `specs/001-aether-v1-productization/evidence/OC79-LAUNCH.md` is under `specs/` and excluded from the `.github/workflows/policy.yml` manifest by design.

---

## 7. Remaining Risk and Downstream Handoff

- **Remaining Risk**: None within this unit. The implementation strictly adheres to the hard constraints: `_resolve_component_paths` precedence is preserved, inherited-transport scrub is unmodified, sorted JSON keys contract is maintained, and all operations remain local without live effects.
- **Downstream Handoff**: `OC79-DOCS` (`t_9993248c`) can update documentation regarding the removal of the sole-project fallback and `AGENTS.md` optionality during greenfield intake.
