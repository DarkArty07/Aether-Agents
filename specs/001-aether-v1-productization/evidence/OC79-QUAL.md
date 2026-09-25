# OC79-QUAL — Isolated Qualification Receipts and Preservation Evidence

**Unit**: OC79-QUAL, role Implementer.
**Authority**: Objective Contract `oc_79b55027e7c3688d@v1`
(SHA-256 `0b685dbfd7deb68e1b526a76b71d057d021f9bbf3984fff8c398ccd62ba9cca6`), base commit
`004c5f076da9e7be4fd64e4bc2adc60e21d4a2f6`, and Supervisor breakdown
`specs/001-aether-v1-productization/tasks-oc79.md` (commit `f71a3677`).
**Scope**: Qualification entry and receipts for AC1–AC5; tasks-oc79.md section 107.
**Compatibility conclusion**: `patch`.

---

## 1. Summary of Qualification Deliverables

1. **Qualification Entry (`scripts/qualify_oc79.py`)**:
   - Implemented isolated, reproducible qualification script exercising all AC1–AC4 behaviors in a disposable temporary environment.
   - Fully isolated: isolates `HOME`, `XDG_DATA_HOME`, `XDG_CONFIG_HOME`, `XDG_STATE_HOME`, `XDG_CACHE_HOME`, `TMPDIR`, and `HERMES_HOME`.
   - Cleans all `HERMES_KANBAN_*` and `AETHER_PROJECT_*` ambient environment variables.
   - Emits structured machine-readable JSON receipt under `--json` and human-readable summary by default.

2. **Policy Manifest Registration**:
   - Added `scripts/qualify_oc79.py` to `.github/workflows/policy.yml` in alphabetical order in the canonical base manifest.
   - Added `scripts/qualify_oc79.py` to `compileall`, `ruff check`, and `ruff format` verification steps in `.github/workflows/policy.yml`.
   - Verified with `tests/test_public_artifacts.py`.

---

## 2. Qualification Execution & Scenarios

### 2.1 Execution Command
```bash
uv run --frozen python scripts/qualify_oc79.py --json
```

### 2.2 Qualification Output
```json
{
  "checks_passed": 18,
  "checks_run": 18,
  "duration_s": 2.867,
  "scenarios": {
    "brownfield": {
      "brownfield_files_preserved": true,
      "custom_agents_md_preserved": true,
      "uncommitted_work_preserved": true
    },
    "observer_mcp": {
      "category_normalizer_resolved": true,
      "model_tools_unimported": true,
      "observer_registration_bounded": true
    },
    "refusals": {
      "plain_dir_refused_with_guidance": true,
      "subdirectory_refused": true,
      "uninitialized_launch_refused_with_guidance": true
    },
    "unborn_root_flow": {
      "check_json_ready": true,
      "dry_run_pure_preview": true,
      "init_actual_success": true,
      "poststate_head_unborn": true,
      "poststate_no_agents_md": true,
      "poststate_no_remotes": true,
      "prestate_head_unborn": true,
      "repeat_init_idempotent": true
    }
  },
  "status": "PASS"
}
```

### 2.3 Verification Matrix

| Scenario / Criterion | Tested Condition | Result |
|---|---|---|
| **AC1: Greenfield Unborn Root** | Empty Git root (`git init -b main`) without commits or remotes | **PASS** (`prestate_head_unborn`, `poststate_head_unborn`, `poststate_no_remotes`) |
| **AC1: Pure Preview** | `aether init --dry-run --json` leaves filesystem completely byte-identical | **PASS** (`dry_run_pure_preview`) |
| **AC1: Exact Project Create** | `aether init --json` establishes `.aether/project.toml` and binds native Hermes Project | **PASS** (`init_actual_success`, `poststate_no_agents_md`) |
| **AC1: Idempotency** | Repeat `aether init --json` returns `no_change` with identical project identifiers | **PASS** (`repeat_init_idempotent`) |
| **AC2: Refusal Boundaries** | Plain non-Git dir refused with `git init` actionable guidance; subdirectory refused; uninitialized launch refused without fallback | **PASS** (`plain_dir_refused_with_guidance`, `subdirectory_refused`, `uninitialized_launch_refused_with_guidance`) |
| **AC2: Brownfield Preservation** | Existing files, uncommitted edits, and custom `AGENTS.md` preserved intact | **PASS** (`brownfield_files_preserved`, `custom_agents_md_preserved`, `uncommitted_work_preserved`) |
| **AC3: Launch Alignment** | `aether --check --json` verifies exact project, Morfeo profile, and terminal cwd alignment | **PASS** (`check_json_ready`) |
| **AC4: Lightweight Observer Registration** | Observer plugin registers hooks without importing `model_tools` or incurring startup deadlock | **PASS** (`observer_registration_bounded`, `model_tools_unimported`, `category_normalizer_resolved`) |

---

## 3. Unit & Integration Test Verification

| Test Target | Command | Result |
|---|---|---|
| Project Init Suite | `uv run --frozen python scripts/run_tests.py -- tests/test_project_init.py -q` | **PASS**, 37 passed |
| Launcher Suite | `uv run --frozen python scripts/run_tests.py -- tests/test_aether_tui_launcher.py -q` | **PASS**, 81 passed |
| Observer Passive Startup | `uv run --frozen python scripts/run_tests.py -- tests/test_observation_passive_startup.py -q` | **PASS**, 28 passed |
| Observer CLI Plugin | `uv run --frozen python scripts/run_tests.py -- tests/test_observation_cli_plugin.py -q` | **PASS**, 31 passed |
| Launcher Guidance Oracle | `uv run --frozen python scripts/run_tests.py -- tests/test_observation_usage_guidance.py -q` | **PASS**, 9 passed |
| Public Artifacts / Manifest | `uv run --frozen python scripts/run_tests.py -- tests/test_public_artifacts.py -q` | **PASS**, 9 passed |
| Documentation Check | `uv run --frozen python scripts/check_documentation.py` | **PASS**, documentation validation passed |
| Packaging & Distribution | `uv build` | **PASS**, built wheel and sdist cleanly |
| Static Lint & Format | `uv run --frozen ruff check ... && uv run --frozen ruff format --check ...` | **PASS**, all checks passed |
| Type Check | `uv run --frozen mypy src/aether_agents` | **PASS**, 0 issues in 69 source files |
