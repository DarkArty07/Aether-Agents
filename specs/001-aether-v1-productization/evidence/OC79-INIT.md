# OC79-INIT — Unborn-Root Init, Exact Native Project Create/Reuse, and Pure Dry-Run Evidence

**Unit**: OC79-INIT (`t_2c5aff9a`), role Implementer, worktree branch
`aether-agents-2/t_2c5aff9a-oc79-init-unborn-root-init-exact-native`.
**Authority**: Objective Contract `oc_79b55027e7c3688d@v1`
(SHA-256 `0b685dbfd7deb68e1b526a76b71d057d021f9bbf3984fff8c398ccd62ba9cca6`), base commit
`004c5f076da9e7be4fd64e4bc2adc60e21d4a2f6` ("docs: finalize project intake and TUI startup objective"),
Supervisor breakdown `specs/001-aether-v1-productization/tasks-oc79.md` (commit `f71a3677`),
material design `specs/001-aether-v1-productization/plan.md` §4.6 / §10.1–10.2, and
`specs/001-aether-v1-productization/contracts/cli.md` section 2 (`aether init`).
Never edited the canonical contract.
**Delivered scope**: AC1, AC2; A1-FR-046/047/048/049/052; `plan.md` §10.1–10.2; `contracts/cli.md` section 2.
**Unit compatibility conclusion**: `patch`.
**Runtime provenance**: Hermes Agent `v0.20.1` (`2026.8.13`), install directory `<data-root>/releases/1.0.0rc8-1771b4f70a31bf70/hermes-source`, manager `aether 1.0.0rc8`.

---

## 1. Summary of behavior and delivered features

1. **Refusal of plain directories and subdirectories safely**:
   - `aether init` verifies that the target path is an existing directory and the exact root of a Git repository.
   - Non-Git directories are refused with stable code `AETHER-INIT-NOT-A-GIT-REPOSITORY`, failure kind `missing_prerequisite`, actionable `git init` guidance in the error message, and zero mutation to filesystem, native state, or project registry.
   - Subdirectories inside a Git repository that are not the repository root are refused with stable code `AETHER-INIT-NOT-REPOSITORY-ROOT`, failure kind `invalid_input`.

2. **Acceptance of the unborn exact Git root**:
   - A clean empty folder where the owner has run `git init` (with no initial commit, i.e. `git rev-parse --verify HEAD^{commit}` fails) is accepted as a valid target.
   - `aether init` never executes `git init`, creates no commit (empty or scaffold), creates no remote, and performs no publication.
   - Initializing an unborn root yields exactly one portable `.aether/project.toml` marker, exactly one native Hermes Project row bound by exact primary path, and local registry binding. `HEAD^{commit}` verification continues to fail after `init`.

3. **Pure preview under `--dry-run`**:
   - `aether init --dry-run --json` executes the complete preflight check (including target path validation, ignore policy check, worktrees check, marker checks, native projects lookup, and runtime availability check).
   - Reports prospective actions (`"action": "create"|"none"`, `"hermes_project_action": "create"|"reuse"`, prospective project ID/slug) with result `"planned"` and `changed: false`.
   - Leaves the repository byte-for-byte identical: `.gitignore` is untouched, `.aether/` is not created, `projects.db` is unmutated, and the Aether project registry is not created or modified.

4. **Creation of exactly one native Project when none exists**:
   - Within the resolved managed Morfeo profile home, when zero active and zero archived exact-path matches exist, `init` creates exactly one native Project using the runtime CLI: `hermes project create <NAME> --primary <PATH>`.
   - The runtime executable and Morfeo profile home are resolved according to the pinned precedence:
     - Profile home: `AETHER_HERMES_ROOT/profiles/morfeo`, else `state_root()/hermes/profiles/morfeo`, else `<repo>/home/profiles/morfeo`, else `state_root()/hermes/profiles/morfeo`.
     - Runtime executable: `AETHER_RUNTIME_ROOT/venv/bin/hermes`, else `data_root()/runtime/current/venv/bin/hermes`, else `<repo>/home/.venv-hermes/bin/hermes`, else `data_root()/runtime/current/venv/bin/hermes`.
   - After CLI creation, `init` performs readback verification through the read-only SQLite lookup on `profile_home/projects.db` asserting exactly one non-archived match with exact primary path and matching returned ID before writing the portable marker or local registry mapping.

5. **Exact native Project reuse and idempotency**:
   - When exactly one non-archived Project matches the repository root's exact primary path, `init` reuses it (`hermes_project_action: "reuse"`).
   - Re-running `init` on an already-initialized project is identity-preserving, does not duplicate native Projects, and returns `result: "no_change"` when no ignore policy fix is required.

6. **Actionable, fail-closed diagnostic codes** (23 refusal codes and 1 success warning emitted by `init`):
   - `AETHER-INIT-PATH-INVALID`: target path does not exist or is not a directory.
   - `AETHER-INIT-NOT-A-GIT-REPOSITORY`: plain directory without Git; includes actionable guidance to run `git init`.
   - `AETHER-INIT-NOT-REPOSITORY-ROOT`: path is inside a Git repository but not its top-level root.
   - `AETHER-INIT-CROSS-PROFILE-PATH`: path is located inside a Hermes profile directory.
   - `AETHER-INIT-FORGE-UNRESOLVED`: explicit `--forge github` without GitHub `origin` remote.
   - `AETHER-INIT-ENV-INVALID`: empty or relative `AETHER_HERMES_ROOT` or `AETHER_RUNTIME_ROOT` environment override.
   - `AETHER-INIT-MARKER-UNSAFE`: existing `.aether/project.toml` is a symlink or non-regular file.
   - `AETHER-INIT-MARKER-UNREADABLE`: existing marker has invalid TOML syntax or cannot be read.
   - `AETHER-INIT-MARKER-INVALID`: existing marker does not conform to `project.schema.json`.
   - `AETHER-INIT-IDENTITY-CONFLICT`: project UUID already registered at a different live directory.
   - `AETHER-INIT-HERMES-PROJECTS-UNAVAILABLE`: Hermes `projects.db` exists but cannot be opened read-only (e.g. permission denied).
   - `AETHER-INIT-HERMES-PROJECTS-UNREADABLE`: Hermes `projects.db` lacks required `projects` table or file is not a valid SQLite database.
   - `AETHER-INIT-HERMES-PROJECT-ARCHIVED`: an archived Project in `projects.db` matches the exact primary path.
   - `AETHER-INIT-HERMES-PROJECT-PATH-MISMATCH`: explicit `--hermes-project ID` does not have target path as exact primary path.
   - `AETHER-INIT-HERMES-PROJECT-AMBIGUOUS`: multiple non-archived Projects match the exact primary path.
   - `AETHER-INIT-HERMES-RUNTIME-UNAVAILABLE`: runtime executable missing, not executable, or failing self-check when native creation is required.
   - `AETHER-INIT-HERMES-PROJECT-CREATE-FAILED`: `hermes project create` CLI invocation returned non-zero exit code.
   - `AETHER-INIT-HERMES-PROJECT-VERIFY-FAILED`: readback verification after CLI creation found no matching row or ID mismatch.
   - `AETHER-INIT-IGNORE-POLICY-UNSAFE`: `.gitignore` is a symlink or non-regular file.
   - `AETHER-INIT-IGNORE-POLICY-UNWRITABLE`: `.gitignore` cannot be written or updated due to filesystem error.
   - `AETHER-INIT-IGNORE-POLICY-CONFLICT`: pre-existing ignore rules conflict and cannot be corrected by appending.
   - `AETHER-INIT-WORKTREES-CONFLICT`: `.worktrees` is tracked or staged in Git.
   - `AETHER-INIT-PROJECT-RELOCATED` (warning): registered project path was moved to this location; emits warning notice on success (`result: "changed"`).
   - `AETHER-INIT-REGISTRY-WRITE-FAILED`: local Aether project registry write or update failed.

7. **Brownfield preservation**:
   - Existing governance (`AGENTS.md`), uncommitted changes, branches, remotes, and files are inspected and preserved intact.
   - `.gitignore` is only appended and verified using `git check-ignore`; restored byte-for-byte on refusal.

8. **Interruption and retry safety**:
   - A simulated failure after native Project creation (where the native row exists in `projects.db` but the marker is not yet written) retries safely on the next invocation: reuses the existing native Project without creating a duplicate and completes marker and registry creation.

---

## 2. Verification evidence

### 2.0 Runtime verification environment

- Runtime executable: `<data-root>/runtime/current/venv/bin/hermes`
- Runtime release / version: Hermes Agent `v0.20.1` (`2026.8.13`), install directory `<data-root>/releases/1.0.0rc8-1771b4f70a31bf70/hermes-source`
- Manager version: `aether 1.0.0rc8`

### 2.1 Focused test lane

Command:
```bash
uv run --frozen python scripts/run_tests.py -- tests/test_project_init.py tests/test_aether_tui_launcher.py tests/test_observation_cli_plugin.py tests/test_observation_passive_startup.py tests/test_observation_usage_guidance.py -q
```
Observed result:
- Exit code: `0`
- Counts: `175 passed, 13 subtests passed in 48.53s`
- (Baseline was 161 passed; +14 net new test cases added in `tests/test_project_init.py`).

### 2.2 Static checks and typing

1. Ruff check:
   ```bash
   uv run --frozen ruff check src/aether_agents tests scripts
   ```
   Observed: `All checks passed!` (exit code `0`).

2. Ruff format check:
   ```bash
   uv run --frozen ruff format --check src/aether_agents tests scripts
   ```
   Observed: `181 files already formatted` (exit code `0`).

3. Mypy type check:
   ```bash
   uv run --frozen mypy src/aether_agents
   ```
   Observed: `Success: no issues found in 69 source files` (exit code `0`).

### 2.3 Environment and Kanban isolation witness

The autouse fixture `isolate_environment` in `tests/test_project_init.py` enforces explicit isolation per test execution:
- User home and XDG roots: `HOME`, `XDG_DATA_HOME`, `XDG_STATE_HOME`, and `XDG_CONFIG_HOME` are redirected to private directories under `tmp_path`.
- Scratch directory: `TMPDIR` is explicitly redirected to `<tmp_path>/tmp`.
- Ambient Hermes and Aether deployment roots: `HERMES_HOME`, `AETHER_HERMES_ROOT`, and `AETHER_RUNTIME_ROOT` are cleared; `AETHER_RUNTIME_ROOT` points to a fake test runtime root under `tmp_path`.
- Kanban routing and board selectors: all inherited `HERMES_KANBAN_*` selectors (`HERMES_KANBAN_DB`, `HERMES_KANBAN_BOARD`, `HERMES_KANBAN_TASK`, `HERMES_KANBAN_RUN_ID`, `HERMES_KANBAN_WORKSPACE`, `HERMES_KANBAN_WORKSPACES_ROOT`, `HERMES_KANBAN_CLAIM_LOCK`, `HERMES_KANBAN_BRANCH`) are redirected to temporary destinations under `<tmp_path>/kanban`, and any other ambient `HERMES_KANBAN_*` variables are deleted.
- Stand-in board snapshot witness: a disposable stand-in board `<tmp_path>/kanban/kanban.db` is seeded before each test; a full table/byte digest snapshot is captured prior to test execution and verified identical at teardown, ensuring no test write escapes to or pollutes a live board.
- Effective roots boundary witness: `tmp_path` is asserted to enclose all resolved effective roots (`state_root()`, `data_root()`, `_resolve_profile_home(tmp_path)`, `HERMES_KANBAN_DB`, `HERMES_KANBAN_WORKSPACES_ROOT`, `TMPDIR`) both before test execution and at teardown.
- Pre-existing live profile notice: 26 native rows with dead scratch paths created during early test runs sit in the operator's live Morfeo profile (`<state-root>/hermes/profiles/morfeo/projects.db`); preserved without unauthorized live mutation for terminal card (`t_6f2fc069`) / owner disposition.

---

## 3. Requirement to test oracle mapping

| Contract obligation | Requirement description | Test oracle in `tests/test_project_init.py` | Observed outcome |
| --- | --- | --- | --- |
| AC1 / A1-FR-046 | Plain directory refused with actionable `git init` guidance; zero mutation | `test_refuse_plain_directory_actionable_guidance` | Code `AETHER-INIT-NOT-A-GIT-REPOSITORY`, `"git init"` in message, 0 directory files created |
| AC1 / A1-FR-047 | Unborn exact Git root accepted; no commit, remote, publication | `test_unborn_git_root_init` | `HEAD^{commit}` fails before & after; 0 remotes; marker valid; native Project bound |
| AC1 / A1-FR-049 | Pure dry-run preview; prospective creation/reuse reported without writes | `test_dry_run_purity_byte_level` | Result `planned`; `action: create`; `.gitignore` byte-for-byte identical; 0 files written |
| AC1 / A1-FR-049 | Create exactly one native Project when none exists via runtime CLI | `test_missing_hermes_project_creates_exactly_one_native_project_when_none_exists` | Invokes CLI; readback verifies row; 1 row in `projects.db`; registry updated |
| AC1 / A1-FR-049 | Absent `projects.db` counts as 0 matches, created successfully | `test_init_creates_native_project_when_projects_db_absent` | Zero matches; create succeeds; `projects.db` created; marker and registry written |
| AC1 / A1-FR-049 | Repeat `init` is idempotent and identity-preserving | `test_init_is_idempotent` | Result `no_change`; `changed: false`; same project ID; 0 duplicates |
| AC2 / A1-FR-049 | Exact non-archived Project reused; exact path wins over name | `test_exact_path_match_wins_over_identical_project_names` | Reuses matching exact primary path `p_exact` |
| AC2 / A1-FR-049 | Ambiguous exact matches refuse with list of IDs | `test_ambiguous_exact_matches_refuse_until_disambiguated` | Code `AETHER-INIT-HERMES-PROJECT-AMBIGUOUS`; disambiguation with `--hermes-project` succeeds |
| AC2 / A1-FR-049 | Explicit `--hermes-project` with path mismatch is refused | `test_explicit_hermes_project_with_mismatched_path_is_refused` | Code `AETHER-INIT-HERMES-PROJECT-PATH-MISMATCH` |
| AC2 / A1-FR-049 | Matching archived Project refused as visible identity conflict | `test_refuse_archived_exact_path_match` | Code `AETHER-INIT-HERMES-PROJECT-ARCHIVED`; no replacement created |
| AC2 / A1-FR-046 | Subdirectory of a Git repository refused | `test_non_repository_and_subdirectory_are_refused` | Code `AETHER-INIT-NOT-REPOSITORY-ROOT` |
| AC2 / A1-FR-046 | Path inside a Hermes profile directory refused | `test_refuse_cross_profile_path` | Code `AETHER-INIT-CROSS-PROFILE-PATH` |
| AC2 / A1-FR-049 | Target runtime unavailable refuses before mutation | `test_missing_hermes_project_refuses_when_runtime_unavailable` | Code `AETHER-INIT-HERMES-RUNTIME-UNAVAILABLE`; 0 mutations |
| AC2 / A1-FR-049 | Corrupt `projects.db` refuses without modifying state | `test_refuse_when_projects_db_unreadable_or_corrupt` | Code `AETHER-INIT-HERMES-PROJECTS-UNREADABLE`; 0 mutations |
| AC2 / A1-FR-049 | Schema-invalid `projects.db` refuses | `test_refuse_when_projects_db_schema_invalid` | Code `AETHER-INIT-HERMES-PROJECTS-UNREADABLE`; 0 mutations |
| AC2 / A1-FR-049 | Symlinked / dangling `.gitignore` refused before modification | `test_refuse_symlinked_gitignore`, `test_refuse_dangling_symlinked_gitignore` | Code `AETHER-INIT-IGNORE-POLICY-UNSAFE`; symlink untouched, target uncreated |
| AC2 / A1-FR-049 | Symlinked / dangling marker refused before modification | `test_refuse_symlinked_or_dangling_marker` | Code `AETHER-INIT-MARKER-UNSAFE`; symlink untouched, target uncreated |
| AC2 / A1-FR-049 | Conflicting live identity refused | `test_conflicting_live_identity_is_refused` | Code `AETHER-INIT-IDENTITY-CONFLICT` |
| AC2 / A1-FR-049 | Moved repository repoints stale registry binding | `test_moved_repository_repoints_the_stale_binding` | Warning `AETHER-INIT-PROJECT-RELOCATED`, `result: "changed"`, registry updated |
| AC2 / A1-FR-048 | Brownfield governance, dirty state, remotes, branches preserved | `test_brownfield_preservation_with_dirty_state` | `AGENTS.md`, `dirty.txt`, `README.md`, remotes intact |
| AC2 / A1-FR-049 | Interruption after native creation retries safely | `test_retry_after_interruption_following_native_creation` | Reuses created project; count remains 1; completes marker and registry |

---

## 4. Manifest and policy status

- No new non-`specs/` files were added or removed in this unit.
- Writable surface touched:
  - `src/aether_agents/commands/init.py` (existing tracked file)
  - `tests/test_project_init.py` (existing tracked file)
  - `specs/001-aether-v1-productization/evidence/OC79-INIT.md` (new file under `specs/`, excluded from policy manifest)
- Exact literal additions required for `.github/workflows/policy.yml`: **none** (0 lines).
