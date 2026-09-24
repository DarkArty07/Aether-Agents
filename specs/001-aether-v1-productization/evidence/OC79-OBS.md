# OC79-OBS — Resolve observer tool categories without the plugin-lock import cycle

**Unit**: OC79-OBS (`t_977b6239`), Implementer.
**Authority**: Objective Contract `oc_79b55027e7c3688d@v1` (SHA-256
`0b685dbfd7deb68e1b526a76b71d057d021f9bbf3984fff8c398ccd62ba9cca6`), base
`004c5f076da9e7be4fd64e4bc2adc60e21d4a2f6`, and Supervisor breakdown
`specs/001-aether-v1-productization/tasks-oc79.md` (commit `f71a3677`).
**Scope**: AC4 (observer half); OBS-D-032, OBS-FR-087; in-scope observer sentence.
**Compatibility conclusion**: unit-level `patch`; no aggregate release or publication conclusion.
**Locked core tests**: Unchanged (`EXPECTED_CORE_TESTS = 472`, node-manifest digest
`c1b1215945754612bb768e513fbeefb4974ce6bba7b44fec39ab9a43ccc0ae0a`). Tests placed in
`tests/test_observation_passive_startup.py` outside the 7 locked files.

## 1. Runtime identity and test environment

- **Locked runtime release**: Hermes Agent baseline `v2026.8.18`.
- **Annotated tag object**: `9f13bbbf8423427e159c78066356ca0e27ca6b74`.
- **Exact commit**: `e624e9fde561e1add9388384012b295fde669ade` (clean checkout).
- **Execution harness**: `scripts/run_tests.py` verifies checkout provenance and injects the release at head of `PYTHONPATH`.
- **Isolation and witnesses**:
  - `HOME`, `XDG_DATA_HOME`, `XDG_CONFIG_HOME`, `XDG_STATE_HOME`, `XDG_CACHE_HOME`, `TMPDIR`, and `HERMES_HOME` are isolated to fresh subdirectories under `tmp_path` before any Hermes imports or plugin manager lookups.
  - All `HERMES_KANBAN_*` routing environment variables are cleared.
  - Zero unintended writes to ambient profiles or discovery caches is established by full before/after file inventory of the ambient home (0 files created under empty ambient; `CHANGED_FILES: NONE` under live-shaped ambient). In addition, each new test node executes an in-test before/after content and size witness on ambient `HERMES_HOME` (covering `SOUL.md`, `config.yaml`, `state.db`, `cache/`, and profile root files, with stability-gating for candidate churned targets to prevent false-RED under concurrent external writers).
- **MCP fixture boundary**:
  - In this local test environment `import mcp` raises `ModuleNotFoundError` (`tools.mcp_tool._ensure_mcp_sdk()` returns `False`, `discover_mcp_tools()` returns `[]`).
  - The bounded fixture registers a synthetic `mcp__demo_server__echo` entry directly in `tools.registry.registry`, exercising no external server process or live connection.
  - Validates bounded startup completion (< 5.0s bound; standalone node measured 1.49-1.51s call / 1.59-1.61s wall) and exactly-once turn processing into the journal without extending the production timeout. Live installed qualification with real MCP transport is owned by OC79-QUAL.

## 2. Implemented behavior

1. `_resolve_category_normalizer()` in `src/aether_agents/observation/capture/hermes_plugin.py`
   resolves tool categories using the runtime's lightweight registered-tool accessor
   (`tools.registry.registry.get_toolset_for_tool` / `tools_registry.get_toolset_for_tool`)
   feeding the existing shared-metrics taxonomy (`hermes_cli.observability.shared_metrics_contract.tool_category`).
   It does not import the discovery-bearing `model_tools` during observer registration.
2. A controlled two-thread race condition between `import model_tools` (which calls
   `discover_plugins()` -> `with manager._discovery_lock:`) and observer registration
   (which runs with `manager._discovery_lock` held) was established as an isolated
   **red-capable** regression against the frozen pre-fix source, and proven **green**
   on the candidate.
3. Native registered tools (e.g. `kanban_create` -> `planning`) and late-registered tools
   (e.g. `mcp:context_server` -> `mcp`, `web` -> `web`) match the selected registry plus
   shared taxonomy. Native discovery is established deterministically in-node via
   `discover_builtin_tools()`. Missing native capability stays the visible
   `NATIVE_TOOL_CATEGORY_UNAVAILABLE` coverage gap without stopping or failing an agent.
4. Isolated MCP-enabled startup completes within a bounded fixture without extending the
   production timeout (< 5.0s bound; standalone node measured 1.49-1.51s call / 1.59-1.61s
   wall), and an early first turn with an MCP tool is processed exactly once into the event
   journal.

## 3. Requirement → check → observed result → evidence

| Requirement / oracle | Check actually run | Observed result | Evidence path / attribution |
|---|---|---|---|
| AC4 (race reproduction, pre-fix): pre-fix normalizer reaches import/plugin lock cycle | `uv run --frozen python scripts/run_tests.py -- tests/test_observation_passive_startup.py -k "test_pre_fix_category_normalizer_demonstrates_import_lock_cycle"` | **PASS** standalone (3 runs: 1 passed, 13 deselected in 2.09s / 2.28s / 2.39s wall, node `call` duration 1.97s / 2.12s / 2.12s). Pre-fix pattern demonstrably deadlocks: Thread 2 blocks on `model_tools` import lock while Thread 1 blocks on `manager._discovery_lock`. Full environment isolation verified; zero ambient modification established by before/after inventory and stability-gated witness. | `tests/test_observation_passive_startup.py`; direct. |
| AC4 (race reproduction, candidate): candidate registration avoids lock cycle | `uv run --frozen python scripts/run_tests.py -- tests/test_observation_passive_startup.py -k "test_candidate_observer_registration_avoids_model_tools_import_and_lock_cycle"` | **PASS** standalone on candidate (3 runs: 1 passed, 13 deselected in 2.34s / 2.45s / 2.70s wall, whole-process wall 3.3-3.7s measured with `/usr/bin/time`); **FAIL (RED)** against pre-fix base `004c5f07` with `AssertionError: Candidate registration deadlocked on the import/plugin lock cycle`. The in-test `t2_done.wait(timeout=5.0)` returns immediately on the candidate (in-test wait measured ≈0.4–0.9s standalone on the reviewed host; registration, not harness startup, is its dominant cost). Full environment isolation verified; zero ambient modification established by before/after inventory and stability-gated witness. | `tests/test_observation_passive_startup.py`; direct RED/GREEN evidence. |
| OBS-D-032: native and late-registered tool categories match registry and taxonomy | `uv run --frozen python scripts/run_tests.py -- tests/test_observation_passive_startup.py -k "test_native_and_late_registered_tool_categories_match_registry_and_taxonomy"` | **PASS** standalone (2 runs: 1 passed, 13 deselected in 2.06s / 2.02s wall, node `call` duration 1.93s / 1.91s; order-independent, native discovery deterministic via `discover_builtin_tools()`). Built-in tools resolve to taxonomy categories (`planning`); late-registered tools resolve dynamically (`mcp`, `web`); unregistered resolves to `other`; degraded native resolver records visible `NATIVE_TOOL_CATEGORY_UNAVAILABLE` coverage gap. | `tests/test_observation_passive_startup.py`; direct. |
| AC4 / OBS-FR-087: isolated MCP-enabled startup and single early turn | `uv run --frozen python scripts/run_tests.py -- tests/test_observation_passive_startup.py -k "test_isolated_mcp_enabled_startup_and_single_early_turn_bounded"` | **PASS** standalone (2 runs: 1 passed, 13 deselected in 1.61s / 1.59s wall); (< 5.0s bound, production timeout not extended); early turn with synthetic MCP tool processed exactly once (`tool.started` and `tool.completed` with category `mcp`). Full environment isolation verified; zero ambient modification established by before/after inventory and stability-gated witness. | `tests/test_observation_passive_startup.py`; direct. |
| Baseline focused lane | `uv run --frozen python scripts/run_tests.py -- tests/test_project_init.py tests/test_aether_tui_launcher.py tests/test_observation_cli_plugin.py tests/test_observation_passive_startup.py tests/test_observation_usage_guidance.py -q` | **165 passed, 13 subtests passed** in 47.53s (baseline was 161 passed; delta is exactly the 4 new regression tests). | Canonical exact-Hermes runner; direct. |
| Qualification lock and core manifest oracle | `uv run --frozen python scripts/run_tests.py -- tests/test_observation_qualification.py -q` | **60 passed, 1 skipped** in 13.15s. `EXPECTED_CORE_TESTS = 472` and manifest digest `c1b1215945754612bb768e513fbeefb4974ce6bba7b44fec39ab9a43ccc0ae0a` preserved unmodified. | `tests/test_observation_qualification.py`; direct. |
| Static quality | `uv run --frozen ruff check src/aether_agents tests scripts && uv run --frozen ruff format --check src/aether_agents tests scripts && uv run --frozen mypy src/aether_agents` | **PASS**. Ruff clean, 181 files formatted, mypy clean for 69 source files. | Direct. |
| Public-artifact path privacy | `uv run --frozen python scripts/check_public_artifacts.py` | **PASS** (tracked surface + 0 artifacts). | `scripts/check_public_artifacts.py`; direct. |
| Patch hygiene | `git diff --check 004c5f07...HEAD` on the unit branch | **PASS** (no trailing whitespace or conflict residue). | Direct. |

## 4. RED and GREEN execution log

### 4.1 RED run against frozen pre-fix source (base `004c5f07`)

Command in scratch archive of base `004c5f07` with delivered tests:
```
uv run --frozen python scripts/run_tests.py -- tests/test_observation_passive_startup.py -k "test_candidate_observer_registration_avoids_model_tools_import_and_lock_cycle"
```
Observed output:
```
============================= test session starts ==============================
platform linux -- Python 3.13.15, pytest-9.1.1, pluggy-1.6.0
rootdir: /tmp/oc79_red_base
configfile: pyproject.toml
plugins: cov-6.3.0, anyio-4.14.2
collected 14 items / 13 deselected / 1 selected

tests/test_observation_passive_startup.py F                              [100%]

=================================== FAILURES ===================================
_ test_candidate_observer_registration_avoids_model_tools_import_and_lock_cycle _
...
>       assert completed, "Candidate registration deadlocked on the import/plugin lock cycle"
E       AssertionError: Candidate registration deadlocked on the import/plugin lock cycle
E       assert False

tests/test_observation_passive_startup.py:1205: AssertionError
=========================== short test summary info ============================
FAILED tests/test_observation_passive_startup.py::test_candidate_observer_registration_avoids_model_tools_import_and_lock_cycle
======================= 1 failed, 13 deselected in 6.32s =======================
```

### 4.2 GREEN run on candidate implementation

Command:
```
uv run --frozen python scripts/run_tests.py -- tests/test_observation_passive_startup.py -k "test_pre_fix_category_normalizer_demonstrates_import_lock_cycle or test_candidate_observer_registration_avoids_model_tools_import_and_lock_cycle or test_native_and_late_registered_tool_categories_match_registry_and_taxonomy or test_isolated_mcp_enabled_startup_and_single_early_turn_bounded"
```
Observed output:
```
============================= test session starts ==============================
platform linux -- Python 3.13.15, pytest-9.1.1, pluggy-1.6.0
rootdir: <worktree-root>
configfile: pyproject.toml
plugins: anyio-4.14.2, cov-6.3.0
collected 14 items / 10 deselected / 4 selected

tests/test_observation_passive_startup.py ....                           [100%]

======================= 4 passed, 10 deselected in 7.48s =======================
```

The earlier 1.98s figure for this 4-node combo was a re-run measurement; the current
reproducible value on this revision is 7.48s.

## 5. Manifest and qualification lock delta

- `EXPECTED_CORE_TESTS = 472`: unchanged.
- `EXPECTED_CORE_NODE_MANIFEST_SHA256 = c1b1215945754612bb768e513fbeefb4974ce6bba7b44fec39ab9a43ccc0ae0a`: unchanged.
- Files modified: `src/aether_agents/observation/capture/hermes_plugin.py`, `tests/test_observation_passive_startup.py`.
- No locked core files (`tests/test_observation_cli_plugin.py`, etc.) were altered; `scripts/qualify_observation.py` and `tests/test_observation_qualification.py` remain untouched.
- No files under `src/aether_agents/commands/init.py`, `src/aether_agents/launcher.py`, `docs/**`, `.github/workflows/policy.yml` or `.aether/**` were touched.
