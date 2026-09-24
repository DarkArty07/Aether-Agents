# OC79-OBS — Resolve observer tool categories without the plugin-lock import cycle

**Unit**: OC79-OBS (`t_977b6239`), Implementer.
**Authority**: Objective Contract `oc_79b55027e7c3688d@v1` (SHA-256
`0b685dbfd7deb68e1b526a76b71d057d021f9bbf3984fff8c398ccd62ba9cca6`), base
`004c5f076da9e7be4fd64e4bc2adc60e21d4a2f6`, and Supervisor breakdown
`specs/001-aether-v1-productization/tasks-oc79.md` (commit `f71a3677`).
**Scope**: AC4 (observer half); OBS-D-032, OBS-FR-087; in-scope observer sentence.
**Compatibility conclusion**: unit-level `patch`; no aggregate release or publication conclusion.
**Locked core tests**: unchanged (`EXPECTED_CORE_TESTS = 472`, node-manifest SHA-256
`c1b1215945754612bb768e513fbeefb4974ce6bba7b44fec39ab9a43ccc0ae0a`). The regressions
are in `tests/test_observation_passive_startup.py`, outside the seven locked files.

## 1. Runtime identity and test environment

- **Locked runtime release**: Hermes Agent baseline `v2026.8.18`.
- **Annotated tag object**: `9f13bbbf8423427e159c78066356ca0e27ca6b74`.
- **Exact commit**: `e624e9fde561e1add9388384012b295fde669ade`; checkout was clean.
- **Execution harness**: `scripts/run_tests.py` verifies the exact checkout and places it
  first on `PYTHONPATH`. The same runtime identity was resolved after the final tests.
- **Per-node isolation**: the regression nodes capture the ambient `HERMES_HOME` witness,
  then `_setup_project()` redirects `HOME`, XDG data/config/state/cache, `TMPDIR`,
  `HERMES_HOME`, `AETHER_PROJECT_ID`, and every inherited `HERMES_KANBAN_*` variable
  before importing Hermes CLI modules or looking up the plugin manager. The witness-only
  node uses the same isolation before its controlled filesystem experiments.
- **Ambient witness behavior and scope**:
  - It inventories candidate files and distinguishes path coverage changes (added/removed)
    from content changes. Ordinary candidate files use size, mtime and SHA-256.
  - A changed cache path is sampled every 0.1 s for a 2.0 s confirmation window. Repeated
    changes are treated as concurrent churn for that comparison only; no process-global
    exclusion is retained. A quiet single change remains a failure. The committed witness
    regression exercises recurring writers at 0.2, 0.3, 0.5, 0.75 and 1.5 s, then verifies
    that a quiet update to the same path is still detected.
  - `state.db` is never read or content-hashed. Its witness records main-file size/mtime
    and WAL presence; creation/removal of the main DB is visible. If a WAL is present at
    either endpoint, database metadata deltas are not attributed to the test. Therefore
    WAL-backed database contents and WAL-only commits are explicitly outside this witness's
    coverage; the test does not claim that the witness proves zero DB writes in that mode.
    When `HERMES_HOME` is unset, `_witness_target()` returns `None` and the ambient witness
    is empty, so fixture isolation—not ambient monitoring—is the protection in that lane.
- **MCP fixture boundary**:
  - In this test environment `import mcp` raises `ModuleNotFoundError`,
    `_ensure_mcp_sdk()` returns `False`, and `discover_mcp_tools()` returns `[]`.
  - The bounded fixture registers synthetic `mcp__demo_server__echo` directly in
    `tools.registry.registry`; it exercises no server process or live connection.
  - The test checks startup below its 5.0 s in-test bound and exactly one early
    `tool.started` plus one `tool.completed` journal event, without changing the production
    timeout. Real installed-server transport qualification belongs to OC79-QUAL.

## 2. Implemented behavior

1. `_resolve_category_normalizer()` in
   `src/aether_agents/observation/capture/hermes_plugin.py` resolves categories through the
   selected runtime's lightweight registered-tool accessor
   (`tools.registry.registry.get_toolset_for_tool` / equivalent registry-owned lookup),
   feeding `hermes_cli.observability.shared_metrics_contract.tool_category`. Registration
   does not import discovery-bearing `model_tools`.
2. A controlled two-thread import/plugin lock cycle is demonstrated with the pre-fix call
   pattern; the candidate observer registration completes while the other thread is
   importing `model_tools` with the plugin discovery lock held.
3. Native and late-registered categories match the registry plus shared taxonomy. Native
   registration is explicitly established with `discover_builtin_tools()`. Unregistered
   tools map to `other`; missing native capability remains the visible
   `NATIVE_TOOL_CATEGORY_UNAVAILABLE` coverage gap and does not stop an agent.
4. MCP-enabled fixture startup stays within the bounded test and an early synthetic MCP
   tool turn is written once. No production timeout, observer write path or network path
   was added.

## 3. Requirement → check → observed result → evidence

| Requirement / oracle | Check actually run | Observed result | Evidence / attribution |
|---|---|---|---|
| AC4, controlled pre-fix lock-cycle pattern | `uv run --frozen python scripts/run_tests.py -- tests/test_observation_passive_startup.py -k test_pre_fix_category_normalizer_demonstrates_import_lock_cycle -q` | **PASS**, 1 passed, 18 deselected in 2.19 s. Thread 2 cannot finish the pre-fix `model_tools` lookup until the test releases the discovery lock; both threads then join. | `tests/test_observation_passive_startup.py`; direct candidate test of the pre-fix pattern. |
| AC4, candidate avoids the import/plugin cycle | `uv run --frozen python scripts/run_tests.py -- tests/test_observation_passive_startup.py -k test_candidate_observer_registration_avoids_model_tools_import_and_lock_cycle -q` | **PASS**, 1 passed, 18 deselected in 2.67 s. The isolated candidate completes registration; the frozen-base RED is recorded in §4.1. | Same test file; candidate and frozen-base evidence. |
| OBS-D-032 taxonomy parity and visible gap | `uv run --frozen python scripts/run_tests.py -- tests/test_observation_passive_startup.py -k test_native_and_late_registered_tool_categories_match_registry_and_taxonomy -q` | **PASS**, 1 passed, 18 deselected in 2.09 s. Native `kanban_create` → `planning`; late MCP/web tools → `mcp`/`web`; unknown → `other`; degraded native resolution records `NATIVE_TOOL_CATEGORY_UNAVAILABLE`. | Same test file; deterministic in-node native discovery. |
| AC4 / OBS-FR-087 bounded MCP startup and one early turn | `uv run --frozen python scripts/run_tests.py -- tests/test_observation_passive_startup.py -k test_isolated_mcp_enabled_startup_and_single_early_turn_bounded -q` | **PASS**, 1 passed, 18 deselected in 1.67 s. The node's internal startup measurement was below its 5.0 s bound; exactly one start and one completion event were present. | Same test file; synthetic MCP registry entry, no server connection. |
| Ambient witness stability and bounded SQLite handling | `uv run --frozen python scripts/run_tests.py -- tests/test_observation_passive_startup.py -k test_live_witness_churn_is_per_comparison_and_state_db_is_wal_bounded -q` | **PASS**, 5 passed, 14 deselected in 37.71 s. Recurring cache churn at 0.2/0.3/0.5/0.75/1.5 s is tolerated per comparison; quiet cache deltas still fail, including after churn stops. A sparse 698 MiB test DB is not hashed; WAL-backed metadata/checkpoint changes are scoped out, while a no-WAL metadata delta is detected. | Same test file; all synthetic profile data lives under `tmp_path`. |
| Focused project lane | `uv run --frozen python scripts/run_tests.py -- tests/test_project_init.py tests/test_aether_tui_launcher.py tests/test_observation_cli_plugin.py tests/test_observation_passive_startup.py tests/test_observation_usage_guidance.py -q` | **PASS**, 170 passed, 13 subtests passed in 91.57 s. | Canonical exact-Hermes runner. |
| Qualification lock oracle | `uv run --frozen python scripts/run_tests.py -- tests/test_observation_qualification.py -q` | **PASS**, 60 passed, 1 skipped in 13.27 s. `EXPECTED_CORE_TESTS = 472` and digest `c1b1215945754612bb768e513fbeefb4974ce6bba7b44fec39ab9a43ccc0ae0a` remain unchanged. | `tests/test_observation_qualification.py`; the new nodes are outside the locked set. |
| Static quality | `uv run --frozen ruff check src/aether_agents tests scripts && uv run --frozen ruff format --check src/aether_agents tests scripts && uv run --frozen mypy src/aether_agents` | **PASS**: Ruff clean; 181 files formatted; mypy clean for 69 source files. | Direct. |
| Public artifact path scan | `uv run --frozen python scripts/check_public_artifacts.py` | **PASS**, tracked surface and 0 artifacts. | Direct. |
| Documentation validation | `uv run --frozen python scripts/check_documentation.py` | **PASS**. | Direct. |
| Patch hygiene | `git diff --check` on the complete working-tree delta | **PASS** (no whitespace errors or conflict residue). The committed base-to-tip check is also reported in the review handoff. | Direct. |

## 4. RED and GREEN execution log

### 4.1 RED against frozen pre-fix source (base `004c5f07`)

The scratch archive used frozen base `004c5f076da9e7be4fd64e4bc2adc60e21d4a2f6` plus the
candidate regression test file; its home/XDG/Hermes/temp and Kanban routing environment was
isolated. Command:

```text
uv run --frozen python scripts/run_tests.py -- tests/test_observation_passive_startup.py -k "test_candidate_observer_registration_avoids_model_tools_import_and_lock_cycle" -q
```

Observed expected RED (pytest exit 1):

```text
F                                                                        [100%]
>       assert completed, "Candidate registration deadlocked on the import/plugin lock cycle"
E       AssertionError: Candidate registration deadlocked on the import/plugin lock cycle

tests/test_observation_passive_startup.py:1394: AssertionError
1 failed, 18 deselected in 5.70s
```

The test releases the held plugin discovery lock before joining both threads; the failure
therefore records the required blocked candidate registration, not a permanently leaked
thread or a test-process hang.

### 4.2 GREEN on the candidate

The candidate registration, pre-fix-pattern, taxonomy and MCP startup nodes each passed
standalone (the exact commands and results are in §3). The full focused lane also passed
with all five witness-cadence cases. No production/deferred-prompt timeout was increased.

## 5. Manifest and qualification lock delta

- `EXPECTED_CORE_TESTS = 472`: unchanged.
- `EXPECTED_CORE_NODE_MANIFEST_SHA256 = c1b1215945754612bb768e513fbeefb4974ce6bba7b44fec39ab9a43ccc0ae0a`: unchanged.
- `tests/test_observation_passive_startup.py` is not among the seven locked files; no lock
  re-derivation was due. No file under `tests/test_observation_cli_plugin.py`,
  `tests/test_observation_qualification.py`, or `scripts/qualify_observation.py` was changed.
- Unit changes are confined to the observer category adapter, passive-startup regressions,
  and this evidence file. `src/aether_agents/commands/init.py`,
  `src/aether_agents/launcher.py`, `docs/**`, `.github/workflows/policy.yml`, and `.aether/**`
  were not changed.

## 6. Remaining witness coverage limits

The cache stability rule discounts only repeated observed churn during the 2.0 s probe. A
one-time concurrent cache write is indistinguishable from a test write and remains a
reported delta; writers slower than the probe are not proven harmless. Under an active WAL,
`state.db` content and WAL-only commits are not witnessed, by explicit code and record
scope. CI runs with `HERMES_HOME` unset have no ambient witness. These limits do not alter
the isolated fixture checks or the red/green production regression, but they prevent
claiming that the helper alone proves zero changes to every ambient profile/database path.
