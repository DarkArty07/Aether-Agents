# MON-D16R Implementation Evidence — run the laboratory as the provisioned Morfeo profile and load the candidate monitor plugin

**Unit:** D16R — run the D13 isolated laboratory under the provisioned Morfeo profile convention and load the candidate monitor plugin
**Task:** `t_d32cf630`
**Objective Contract:** `oc_f8c9fc9320587cf3@v4` (SHA-256 `765a2f48842835d91049f959defd6c3bd15cd43de9ef97da67a37d1a819bcfe0`)
**Base commit:** `98fce3e605f701d3bf20e51d7df921bf6b01faad` (D16 approval; code candidate `e629de52a658249a460b57e7f7813a1ef0dc4cb5`)
**Candidate implementation commit:** `9cbd934` (`9cbd93401e20a3898256bada011a4ed389e3c2aa`, includes `e4435a6`)
**Phase:** Implementer unit; **no live effect performed** — no `--live` run, model call, Telegram send, scheduler start, enable of a real laboratory or production job, profile/credential/provider mutation, provisioned runtime/venv modification, retained-lab cleanup, push, PR or issue mutation.

## Scope and changed paths

- `scripts/telegram_monitor_lab.py`:
  - Aligned laboratory child profile-home convention with production: `HERMES_HOME` is set to `<lab root>/hermes/profiles/morfeo` (`plan.profile_home`).
  - Added `plugins_meta` directory to `LabPlan` (`<lab root>/plugins_meta`) and hardened in `create_root`.
  - Added `write_plugin_metadata` writing a pinned candidate distribution artifact `aether_agents_candidate_monitor-0.24.0.dist-info` declaring `[hermes_agent.plugins]` entry point `aether-telegram-monitor = aether_agents.monitor.hermes_plugin`.
  - Added `plugins` to `_CONFIG_SECTIONS` and updated `minimal_config` to preserve provisioned plugin decisions and ensure `aether-telegram-monitor` is enabled in `plugins.enabled` and `plugins.entries.aether-telegram-monitor.settings.enabled = True`.
  - Added `plan.plugins_meta` to `child_environment`'s `PYTHONPATH`, and verified in `context_problems` that `plugins_meta` resides strictly within the laboratory root and is present in `PYTHONPATH`.
- `scripts/qualify_telegram_monitor.py`:
  - Updated `_LAB_SCHEDULE_UPDATE_PROBE` and `_lab_schedule_update` home assertions to verify `resolved_home == resolved_root / "hermes" / "profiles" / "morfeo"`.
  - Added monitor plugin discovery/load probe in `_LAB_NATIVE_PROBE` for laboratory children (`LAB_ROOT_JSON`).
  - Updated in-laboratory gate `_lab_context_preflight` to fail closed before synthetic scope seeding or enable if the candidate plugin is missing, not enabled, missing tools (`aether_monitor`, `aether_monitor_report_snapshot`), missing hooks (`on_session_end`, `post_llm_call`, `post_tool_call`), or encounters an import error.
- `src/aether_agents/monitor/sources.py`:
  - Resolved kanban root in `_resolve_board_paths` to check `root.parent.parent` when `root.parent.name == "profiles"`, matching Hermes native `kanban_db.boards_root()` behavior.
  - Resolved session DB paths in `_resolve_session_paths` to check sibling profiles and root when `root.parent.name == "profiles"`.
  - **Non-lab scope disclosure and rationale:** This correction is **not lab-only**; it changes the resolver's behavior whenever `HERMES_HOME` is configured as a profile home directory (`<installation>/profiles/morfeo`), which is precisely the shape used by the provisioned production runtime. In Hermes Agent, kanban boards are stored in `<root>/kanban/boards`, shared across profiles by design (`kanban_db.boards_root()`). Prior to this fix, `_resolve_board_paths` looked for kanban boards strictly under `HERMES_HOME / "kanban" / "boards"`, resolving 0 boards when `HERMES_HOME` pointed to a profile home. That caused `ReadOnlySources.collect()` to return 0 items and report `idle: True`, which would silently render every accelerated cut idle and permanently prevent the production monitor from detecting registered work. Checking `root.parent.parent` when `root.parent.name == "profiles"` (and checking sibling profiles / root for session databases in `_resolve_session_paths`) was therefore strictly required for the monitor to discover boards and sessions in the provisioned production runtime as well as in the laboratory. (Note: while kanban board resolution is pinned by `test_profile_shaped_hermes_home_resolves_kanban_boards_and_is_not_idle`, the `_resolve_session_paths` profile-aware hunk for sibling-profile and parent-root `state.db` resolution remains an explicitly known unpinned hunk because reverting it alone leaves sources and the harness chain green, as the laboratory and Morfeo profile resolve their own `state.db` via the primary candidate path).
- `tests/test_telegram_monitor_sources.py`:
  - Added behavior-bearing regression test `test_profile_shaped_hermes_home_resolves_kanban_boards_and_is_not_idle` pinning that a profile-shaped `HERMES_HOME` (`<root>/profiles/morfeo`) resolves boards under `<root>/kanban/boards` and yields a non-idle collection (`idle: False`, `len(items) > 0`), along with a plain-root control preserving standard resolution. Reverting the `kanban_root` hunk alone in `sources.py` causes this test to fail, proving the pin.
- `tests/test_telegram_monitor_cli_plugin.py`:
  - Aligned `test_d16_native_update_changes_only_the_private_lab_job`, `_PROBE_STUB_MODULES`, `_CHAIN_STUB_MODULES`, and `_CHAIN_DRIVER` with the profile-home convention and added `hermes_cli/plugins.py` stubs.
  - Added 5 behavior-bearing tests:
    - `test_d16r_lab_context_resolves_morfeo_profile_and_reads_configuration`
    - `test_d16r_child_containment_verifies_roots_inside_lab_and_refuses_escapes`
    - `test_d16r_candidate_plugin_discovered_and_registered_in_lab_child`
    - `test_d16r_gate_refuses_lab_when_plugin_cannot_be_loaded`
    - `test_d16r_enable_reaches_native_job_creation_in_lab_context`
- `specs/telegram-monitor/evidence/MON-D16R.md`:
  - This evidence document.

Preserved unchanged: design documents, immutable contract artifacts, prior evidence records, harness public CLI (`--json`, `--live`, `--wait-hourly-boundaries 2`, `--output`), D14/D14R provisioned-preflight semantics, D15R source evaluation and fixture binding, fail-closed receipt controls, D16 accelerated-schedule semantics, production schedule `0 * * * *`, and operator state.

## Defect statements and first-hand measurements

### Defect 1 — the laboratory Hermes-home convention did not match production
- **Finding:** `telegram_monitor_lab.child_environment` set `HERMES_HOME=<lab root>/hermes`, while the lab's decision configuration was written to `<lab root>/hermes/profiles/morfeo/config.yaml`. Hermes resolves `get_config_path() = get_hermes_home()/config.yaml`, so the configuration was never read, and `hermes_cli.profiles.get_active_profile_name()` inferred `"default"`. At enable time, `aether_agents.monitor.service._on()` verified `profile_text != MORFEO_PROFILE` ("morfeo") and refused with `RUNTIME_MISMATCH` ("the monitor can only be enabled from the provisioned Morfeo runtime; no job or destination was changed").
- **Measured baseline contrast:**
  - `HERMES_HOME=<root>`: `get_active_profile_name() == 'default'`, `load_config() == {'model': '', 'providers': {}, ...}`, `aether monitor on` refused with `RUNTIME_MISMATCH`.
  - `HERMES_HOME=<root>/profiles/morfeo`: `get_active_profile_name() == 'morfeo'`, `load_config() == {'model': {'default': 'candidate'}, ...}`, `aether monitor on` succeeded with `ok: True`.

### Defect 2 — the candidate monitor plugin could not register in lab children
- **Finding:** Reporter narrative capture and delivery depend on plugin hooks (`post_tool_call`, `post_llm_call`, `on_session_end`) and reporting tools (`aether_monitor`, `aether_monitor_report_snapshot`). Two gaps prevented registration:
  1. The installed interpreter's dist-info entry points only listed `aether-contract-observer`, `aether-objective-contracts`, `aether-project-knowledge`; `aether-telegram-monitor` was absent.
  2. `telegram_monitor_lab.minimal_config` projected `_CONFIG_SECTIONS` without `plugins`, dropping plugin enable decisions.
- **Measured baseline contrast:**
  - Base child probe: `importlib.metadata.entry_points(group="hermes_agent.plugins")` returned only the 3 observer/contracts/knowledge plugins; `PluginManager.discover_and_load(force=True)` loaded `aether-telegram-monitor: None` (`plugin_loaded: False`, `tools: []`, `hooks: []`).
  - Candidate child probe: `aether-telegram-monitor` was discovered via private lab distribution metadata on `PYTHONPATH`, loaded with `enabled: True`, tools `['aether_monitor', 'aether_monitor_report_snapshot']`, and hooks `['on_session_end', 'post_llm_call', 'post_tool_call']`.

### Defect 3 — source resolver did not resolve kanban boards or sessions when HERMES_HOME was a profile home
- **Finding:** In provisioned production and the laboratory, `HERMES_HOME` is `<root>/profiles/morfeo`. Hermes Agent shares kanban boards across profiles under `<root>/kanban/boards`. Prior to the fix, `_resolve_board_paths` resolved boards under `HERMES_HOME / "kanban" / "boards"` (`<root>/profiles/morfeo/kanban/boards`), which does not exist. This resulted in resolving 0 boards. In a fixture-seeded environment, `ReadOnlySources(state_root=..., hermes_home=<root>/profiles/morfeo).collect(...)` returned 0 items and `idle: True`. Reverting the `kanban_root` hunk alone caused the synthetic boards to resolve to nothing, which would make every accelerated cut idle and make production permanently report no work.
- **Measured baseline contrast:**
  - With fix: `_resolve_board_paths(board_paths=None, hermes_home=profile_home)` resolves `BOARD_SLUG` from `<root>/kanban/boards`; `ReadOnlySources.collect()` yields `collection.items` with tasks (`len > 0`) and `idle: False`.
  - Reverting `kanban_root` hunk alone: `_resolve_board_paths` returns `()`; `collection.items` is empty (`()`) and `collection.idle` is `True`. Plain-root control `<root>` preserves resolution in both cases.

## Pre-effect chain probe reproduction

Drove the pre-effect chain (`_lab_plan → lab_preflight → lab_create → lab_context_preflight → _scope_manifest → _write_scope_projects → lab_fixture → environment_gaps → lab_control(ACTION_ON)`):

1. **Uncorrected convention reproduction (Half 1):**
   - Laboratory created with `HERMES_HOME=<lab root>/hermes`.
   - `_lab_control(interpreter, record, ACTION_ON)` raised `QualificationError: the monitor can only be enabled from the provisioned Morfeo runtime; no job or destination was changed` (code: `RUNTIME_MISMATCH`).
2. **Corrected convention execution (Half 2):**
   - Scratch laboratory created at `/tmp/d16r_chain_probe/monitor/lab/20260911T130000Z-000000000002` (outside every Git worktree).
   - `preflight problems`: `[]`.
   - `lab_create`: created with `record["hermes_home"] = ".../hermes/profiles/morfeo"`.
   - `lab_context_preflight`: `problems: []`, `monitor_plugin: {'present': True, 'enabled': True, 'tools': ['aether_monitor', 'aether_monitor_report_snapshot'], 'hooks': ['on_session_end', 'post_llm_call', 'post_tool_call']}`.
   - `_scope_manifest` and `_write_scope_projects`: 2 projects materialized.
   - `lab_fixture`: seeded 2 projects, 2 boards, 8 tasks.
   - `environment_gaps`: `[]`.
   - `lab_control(ACTION_ON)`: `ok: True`, `native_job: {'id': '72b153acfc99', 'name': 'Aether Telegram Monitor', 'schedule': '0 * * * *', 'state': 'active'}`.
   - `_lab_schedule_update`: updated from `0 * * * *` to `* * * * *` via `cron.jobs.update_job`.

## Fail-before / pass-after

Evaluated on a detached scratch worktree of base `98fce3e605f701d3bf20e51d7df921bf6b01faad` overlaid with the test suite:

| Test | Base / unpinned observation (`98fce3e` / reverted hunk) | Candidate observation |
| --- | --- | --- |
| `test_d16r_lab_context_resolves_morfeo_profile_and_reads_configuration` | **FAIL**: `AssertionError: assert PosixPath('.../hermes') == PosixPath('.../hermes/profiles/morfeo')` | **PASS**: resolves `morfeo` profile and reads decision config |
| `test_d16r_child_containment_verifies_roots_inside_lab_and_refuses_escapes` | **FAIL**: `AssertionError: assert 'plugins-meta-not-in-pythonpath' in []` | **PASS**: verifies mutable roots inside lab and catches escaping roots |
| `test_d16r_candidate_plugin_discovered_and_registered_in_lab_child` | **FAIL**: `AssertionError: assert 'aether-telegram-monitor' in ['aether-contract-observer', ...]` | **PASS**: discovers entry point, loads plugin, registers 2 tools and 3 hooks |
| `test_d16r_gate_refuses_lab_when_plugin_cannot_be_loaded` | **FAIL**: `AttributeError: 'LabPlan' object has no attribute 'plugins_meta'` | **PASS**: in-lab gate refuses fail-closed before scope seeding with `monitor-plugin-missing` / `monitor-plugin-not-enabled` |
| `test_d16r_enable_reaches_native_job_creation_in_lab_context` | **FAIL**: `KeyError: 'monitor_plugin'` | **PASS**: harness pre-effect chain reaches `ACTION_ON` without `RUNTIME_MISMATCH` and creates production-shaped job |
| `test_profile_shaped_hermes_home_resolves_kanban_boards_and_is_not_idle` | **FAIL**: `AssertionError: assert False where False = any(...)` (0 boards resolved under `<root>/profiles/morfeo/kanban/boards`, empty items, `idle: True`) | **PASS**: resolves boards under `<root>/kanban/boards`, collection is non-idle (`len > 0`, `idle: False`), and plain-root control passes |

Result on base / reverted: **6 failed** (5 in `cli_plugin` on base `98fce3e`; 1 in `sources` on base or when reverting the `kanban_root` hunk alone).
Result on candidate: **6 passed** (126 passed in `cli_plugin`, 43 passed in `sources`; 329 passed total in focused monitor lane).

## Verification commands and observed results

- `git log --oneline -4`: tip is `98fce3e` (clean starting base).
- `PYTHONPATH=. uv run --frozen pytest tests/test_telegram_monitor_cli_plugin.py`: **PASS** (122 passed, 4 skipped without `AETHER_HERMES_PYTHON`; with `AETHER_HERMES_PYTHON=$AETHER_HERMES_PYTHON`: 126 passed in 23.18s).
- `PYTHONPATH=. uv run --frozen pytest tests/test_telegram_monitor_sources.py`: **PASS** (43 passed in 0.38s).
- `AETHER_HERMES_PYTHON=$AETHER_HERMES_PYTHON PYTHONPATH=. uv run --frozen pytest tests/test_telegram_monitor_*.py`: **PASS** (329 passed in 26.96s with provisioned runtime interpreter; without `AETHER_HERMES_PYTHON`: 325 passed, 4 skipped).
- `TMPDIR=/tmp uv run --frozen python scripts/qualify_telegram_monitor.py --json`: **PASS** (`ok: true`, 12/12 checks, `external_effects: {model_calls: 0, telegram_sends: 0}`).
- `uv run --frozen python scripts/run_tests.py -- tests/test_telegram_monitor_*.py`: **PASS** (325 passed, 4 skipped without `AETHER_HERMES_PYTHON`; with `AETHER_HERMES_PYTHON=$AETHER_HERMES_PYTHON`: 329 passed in 21.07s).
- `uv run --frozen python scripts/check_documentation.py`: **PASS** (`documentation validation passed`).
- `uv run --frozen mypy src/aether_agents`: **PASS** (`Success: no issues found in 65 source files`).
- `uv run --frozen ruff check ...`: **PASS** (`All checks passed!`).
- `uv run --frozen ruff format --check ...`: **PASS** (`150 files already formatted`).
- `uv run --frozen python -m compileall src tests scripts`: **PASS** (0 errors).
- `uv build`: **PASS** (`aether_agents-0.24.0.tar.gz` and `aether_agents-0.24.0-py3-none-any.whl`).
- `git diff --check`: **PASS** (clean diff).
- `scripts/check_public_artifacts.py`: **FAIL with the two known pre-existing findings only** (`.aether/objective-contracts/oc_0084270d940c98d9/v1.md: absolute-user-home` and `operator-desktop-layout`, issue #364); output is identical to base `98fce3e` (no candidate path reported; dist was removed after scan).
- `.github/workflows/policy.yml` manifest emulation: **PASS** (`diff -u "$expected" "$actual"` exit code 0).

## Compatibility and residual risk

**Unit compatibility conclusion:**
The corrections are strictly additive and scoped to the isolated laboratory child context and the monitor source resolver when a profile directory convention is present. The production monitor's fixed `0 * * * *` schedule, default precheck hourly cutoff, and service behavior remain unchanged. This is unit-level compatibility evidence, not an aggregate release decision.

**Residual risk:**
After this correction the laboratory still has never crossed its first cut; the live qualification remains the terminal card's single attempt, and a failure after the lab job/scheduler/model/Telegram effects begin stops the experiment with evidence and no automatic rerun. Terminal card `t_84c2812b` will consume this verified candidate to execute the single authorized live qualification.
