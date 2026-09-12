# MON-LC1 Implementation Evidence — the approved Aether plugin entry-point set admits the accepted monitor plugin

**Unit:** MON-LC1
**Task:** `t_c898b67f`
**Objective Contract:** `oc_f8c9fc9320587cf3@v2` (SHA-256 `1e5aaef54d3ca312af3888bb5fdef97bb374fc4daadb26ba610bf7cf0866624d`)
**Supervisor breakdown:** `specs/telegram-monitor/tasks.md` at decomposition commit `86015907b20e0a42e33c6644695761889e823e10` (AC-8 row, shared decision 7)
**Base commit:** `21d44b5d87deaed2f3e5eccfea15dcd2a740ca6b` (tree `f9a1a9dfb77b49480903153311a3aad1c403aa36`)
**Implementation tree SHA (before this evidence file):** `e35673ce3eb9e4a4aff8a61251b6ad6cc9d59150` (`git write-tree` with `src/aether_agents/lifecycle.py` and `docs/product-boundary.md` staged, this evidence file excluded)
**Status:** self-verified; ready for same-card Supervisor review. No push, PR, merge, model call, Telegram call, activation, credential or configuration change was made.

## Scope and changed paths

- `src/aether_agents/lifecycle.py` — the only production change: one descriptor constant and one
  membership line.
- `docs/product-boundary.md` — the plugin-discovery/tool-registration row that still enumerated the
  three pre-existing entry points.
- `specs/telegram-monitor/evidence/MON-LC1.md` — this portable evidence file.

Nothing else differs from the base. In particular `pyproject.toml`,
`src/aether_agents/resources/profiles/*`, `tests/test_observation_packaging.py`,
`tests/test_public_artifacts.py`, `tests/test_observation_lifecycle.py`, `tests/test_telegram_monitor_runtime.py`,
`docs/capabilities.toml`, `docs/reference/*`, all monitor production code,
`scripts/qualify_telegram_monitor.py`, the `specs/telegram-monitor/` design artifacts, root `AGENTS.md`,
both Objective Contracts, lockfiles and `.github/workflows/policy.yml` are unchanged.

## Base establishment

The declared base is not an ancestor of the dispatch branch tip, and the dispatch branch had no local
commits, so the card's permitted reset was used on this branch only:

```text
git log --oneline -1 <dispatch branch>      -> 10e5140 docs(monitor): finalize v2 isolated qualification and production activation
git merge-base --is-ancestor 21d44b5 HEAD   -> not contained
git reset --hard 21d44b5d87deaed2f3e5eccfea15dcd2a740ca6b   (clean worktree, no local commits, no force-push)
git rev-parse HEAD        -> 21d44b5d87deaed2f3e5eccfea15dcd2a740ca6b
git rev-parse HEAD^{tree} -> f9a1a9dfb77b49480903153311a3aad1c403aa36   (matches the card's recorded tree)
```

No other branch, worktree or the v2 root branch (`10e51404ce83ea9fd26d73ad7f4c01c094a30baa`) was modified or merged.
`2d49418b2ac9a3f64764b84e1b071df48b85070f` (MON-05) is an ancestor of the base, so the accepted monitor
packaging is present.

## Reproduction on the unmodified base

Exact-Hermes lane over the affected files on the untouched base (`21d44b5`):

```text
uv run --frozen python scripts/run_tests.py -- -q --tb=no tests/test_observation_lifecycle.py tests/test_observation_packaging.py tests/test_public_artifacts.py
```

Result: **7 failed, 97 passed in 65.12s** (exit 1) — the six entry-point allow-list failures plus the
unchanged pre-existing #364 public-artifact finding:

```text
tests/test_observation_lifecycle.py::test_wheel_fingerprint_binds_runtime_metadata_schemas_and_entry_points
tests/test_observation_lifecycle.py::test_wheel_inspection_binds_the_targets_own_projection_schema
tests/test_observation_lifecycle.py::test_release_lock_identity_is_explicit_and_semantically_matches_the_wheel
tests/test_observation_lifecycle.py::test_prepare_release_installs_one_wheel_in_manager_and_exact_runtime
tests/test_observation_lifecycle.py::test_exact_public_lifecycle_uses_real_plugin_profiles_query_and_recovery
tests/test_observation_lifecycle.py::test_disposable_public_install_capture_query_update_rollback_uninstall_purge
tests/test_public_artifacts.py::test_tracked_public_surface_contains_no_operator_paths   (issue #364, separate, untouched)
```

Focused traceback run of the three wheel-level cases on the same base records the raised error:

```text
uv run --frozen python scripts/run_tests.py -- -q --tb=short \
  tests/test_observation_lifecycle.py::test_wheel_fingerprint_binds_runtime_metadata_schemas_and_entry_points \
  tests/test_observation_lifecycle.py::test_wheel_inspection_binds_the_targets_own_projection_schema \
  tests/test_observation_lifecycle.py::test_release_lock_identity_is_explicit_and_semantically_matches_the_wheel

src/aether_agents/lifecycle.py:4012: in _inspect_wheel
    raise IntegrityError("candidate Aether plugin entry-point set mismatch")
E   aether_agents.lifecycle.IntegrityError: candidate Aether plugin entry-point set mismatch
3 failed in 2.13s
```

Root cause: the base `AETHER_PLUGIN_ENTRY_POINTS` (`src/aether_agents/lifecycle.py:105`) enumerated three
plugin entry points while the repository already ships four (`pyproject.toml:33`), so the candidate-wheel
verifier (`_inspect_wheel`), the installed-environment probe (`_verify_installed_environment`) and the
installed identity comparison (`_installed_aether_identity`) rejected the accepted distribution.

## Baseline comparison (MON-05 tip `2d49418`)

The same three-file lane was executed on an unmodified, clean disposable git worktree of `2d49418`
(outside the repository, no branch created, removed afterwards): **7 failed, 97 passed in 337.05s** with
the identical six entry-point failures plus the same #364 finding. The defect class therefore predates the
unit base and is not introduced by the monitor chain tip.

## Change

```diff
--- a/src/aether_agents/lifecycle.py
+++ b/src/aether_agents/lifecycle.py
@@
 KNOWLEDGE_ENTRY_POINT: dict[str, str] = {
     "plugin_name": "aether-project-knowledge",
     "group": "hermes_agent.plugins",
     "target": "aether_agents.knowledge.hermes_plugin",
 }

+MONITOR_ENTRY_POINT: dict[str, str] = {
+    "plugin_name": "aether-telegram-monitor",
+    "group": "hermes_agent.plugins",
+    "target": "aether_agents.monitor.hermes_plugin",
+}
+
 AETHER_PLUGIN_ENTRY_POINTS: dict[str, str] = {
     OBSERVER_ENTRY_POINT["plugin_name"]: OBSERVER_ENTRY_POINT["target"],
     OBJECTIVE_CONTRACT_ENTRY_POINT["plugin_name"]: OBJECTIVE_CONTRACT_ENTRY_POINT["target"],
     KNOWLEDGE_ENTRY_POINT["plugin_name"]: KNOWLEDGE_ENTRY_POINT["target"],
+    MONITOR_ENTRY_POINT["plugin_name"]: MONITOR_ENTRY_POINT["target"],
 }
```

The monitor descriptor follows the existing `OBSERVER_ENTRY_POINT`/`OBJECTIVE_CONTRACT_ENTRY_POINT`/
`KNOWLEDGE_ENTRY_POINT` pattern; no string literal is duplicated and the single mapping remains the sole
source for all three verifiers. Set equality is preserved everywhere it existed before, so an unapproved
extra plugin is still rejected. `docs/product-boundary.md` now names the shipped fourth entry point
(`Morfeo-only aether-telegram-monitor`), matching `pyproject.toml`, `docs/capabilities.toml` and
`docs/reference/plugins-and-tools.md`.

## Verification

| # | Assigned acceptance obligation | Check actually run | Observed result |
| --- | --- | --- | --- |
| 1 | Reproduction on the unmodified base recorded (command, failing names, raised error) | `scripts/run_tests.py` three-file lane and a focused `--tb=short` run on base `21d44b5`; comparison lane on a disposable `2d49418` worktree | 7 failed / 97 passed with the six named entry-point failures and `IntegrityError: candidate Aether plugin entry-point set mismatch` (`lifecycle.py:4012`); identical class at `2d49418` |
| 2 | Entry-point class failure set empty; approved-set tests and negative controls pass | Same three-file lane after the change; focused subset: wheel fingerprint binding, `test_wheel_rejects_unapproved_third_plugin_entry_point`, `test_wheel_runtime_metadata_tampering_is_rejected` (4 cases), `test_installed_environment_probe_loads_every_approved_aether_plugin`, `test_wheel_observer_dependency_lock_rejects_unhashed_or_unexpected_closure` | Lane: **1 failed, 103 passed** — only the unrelated #364 finding; no `candidate`/`installed` entry-point set mismatch anywhere. Focused subset: **8 passed in 3.58s**. The negative control still rejects an unapproved extra plugin |
| 3 | `uv run --frozen pytest -q tests/test_observation_lifecycle.py tests/test_observation_packaging.py` passes; three-file lane shows only #364 | Plain pytest invocation on candidate and on the unmodified base | Candidate **1 failed, 98 passed**; base **6 failed, 93 passed**. The single remaining failure is `test_exact_public_lifecycle_uses_real_plugin_profiles_query_and_recovery` raising `ModuleNotFoundError: No module named 'hermes_cli'` — the documented plain-lane environment limitation (the plain invocation does not put the exact Hermes checkout on `PYTHONPATH`); it fails identically on the unmodified base and passes in the routed exact-Hermes lane (part of the 103 passed above) |
| 4 | `uv build` succeeds and the built wheel's entry-point set equals the approved set the code asserts | `uv build --out-dir <disposable dir outside the repository>`; programmatic comparison of the wheel's `entry_points.txt` with `AETHER_PLUGIN_ENTRY_POINTS`; `LifecycleManager._inspect_wheel(wheel)` | Built `aether_agents-0.24.0-py3-none-any.whl`; wheel `[hermes_agent.plugins]` = `AETHER_PLUGIN_ENTRY_POINTS` = 4 entries (`aether-contract-observer`, `aether-objective-contracts`, `aether-project-knowledge`, `aether-telegram-monitor`); comparison `True`; the candidate-wheel verifier accepted the artifact and returned fingerprint `124c2d8baeae58e7915600c4966d1d12b456127d5f1332dc2fbd2d33e2e7f648` |
| 5 | `check_documentation.py` passes and `docs/product-boundary.md` agrees with the shipped plugin set | `uv run --frozen python scripts/check_documentation.py` | `documentation validation passed` (exit 0); the boundary row now names the same four entry points as `pyproject.toml`, `docs/capabilities.toml` and `docs/reference/plugins-and-tools.md` |
| 6 | ruff check, ruff format --check, mypy, compileall, `git diff --check` clean; only authorized paths differ | `uv run --frozen ruff check <CI path set>`; `uv run --frozen ruff format --check <CI path set>`; `uv run --frozen mypy src/aether_agents`; `uv run --frozen python -m compileall -q src tests …`; `git diff --check 21d44b5d87deaed2f3e5eccfea15dcd2a740ca6b...HEAD`; `git status --porcelain` | mypy: `Success: no issues found in 65 source files`. compileall: exit 0. `git diff --check 21d44b5d87deaed2f3e5eccfea15dcd2a740ca6b...HEAD`: exit 0 (committed-range form, re-checked after the review-round-1 correction of the trailing space this file carried at line 101). ruff (locked `0.16.4`): 7 findings / 4 unformatted files — **byte-identical to the pristine base `21d44b5`** (normalized concise diff empty); none is in a path this unit touched, and all are outside the writable surface (see "Residual risk"). Only `docs/product-boundary.md`, `src/aether_agents/lifecycle.py` and this evidence file differ from the base |
| 7 | Evidence file records mapping, commits, commands/results, before/after failures and the compatibility conclusion | This file | Recorded |

### Deliberate non-effects

- No `pyproject.toml`, profile-resource, capability-registry, reference-doc, monitor-code, harness, lockfile,
  contract or check was edited; the monitor was not removed, made optional, excluded from a verifier, or
  exempted from any comparison.
- No verifier oracle, comparison operand or negative control was relaxed: `_inspect_wheel` still requires
  exact set equality, `_verify_installed_environment` still compares the probe's entry set, and
  `_installed_aether_identity` still compares sorted entry points plus console scripts.
- No live model call, Telegram send, profile/job/plugin/service activation, credential or configuration
  operation, registry change, package publication, push, PR, merge or issue mutation.
- `tests/test_telegram_monitor_runtime.py` (MON-05-R1) and the MON-06R harness/docs/evidence were not touched.

### Requirement mapping

| Source | Requirement | Evidence |
| --- | --- | --- |
| `specs/telegram-monitor/spec.md:84` (AC-8) | Packaged entry points/resources, plugin allowlist, CLI/tool contracts, capability registry and user guide agree; quality gates pass without weakening them | Obligations 2, 4, 5, 6: allow-list code now agrees with `pyproject.toml`, capabilities registry and reference docs; no check weakened |
| `specs/telegram-monitor/tasks.md` AC-8 row (decomposition `8601590`) | "the approved Aether plugin entry-point set admits the accepted monitor plugin; the six lifecycle allow-list failures disappear without weakening any integrity check" | Obligation 2: six failures → 0 on this class (`1 failed, 103 passed`, only #364 remains); negative controls pass |
| `specs/telegram-monitor/tasks.md` shared decision 7 (decomposition `8601590`) | `aether-telegram-monitor = aether_agents.monitor.hermes_plugin` belongs to the approved set because accepted MON-05 packaging already ships it; the correction is mechanical and must not weaken any verifier | Exact change applied through a descriptor constant; the shipped packaging already carried the entry point before this unit |
| `specs/telegram-monitor/evidence/MON-05.md` (cross-unit collision) | Required repair: add the monitor entry point to `AETHER_PLUGIN_ENTRY_POINTS` with a `MONITOR_ENTRY_POINT` constant beside the existing three, and update matching release-fingerprint expectations | Constant added as specified. No test expectation needed changing: the failing expectations were the six behaviour tests, and the approved-set expectation in `tests/test_observation_lifecycle.py:1319` iterates `AETHER_PLUGIN_ENTRY_POINTS` dynamically; the explicit four-entry sets live in the preserved `tests/test_observation_packaging.py:85` and `tests/test_public_artifacts.py:112` |

### `unit_compatibility` conclusion

**`none`** — confirmed from the observed evidence, not assumed:

- The shipped packaging is unchanged; the wheel's public plugin entry-point set for the same
  `pyproject.toml` is byte-identical before and after this unit (four entries in both cases). What changed is
  that the lifecycle assertion now agrees with it instead of rejecting it.
- The public CLI (`aether = aether_agents.cli:main`), the tool surfaces, the packaged schemas, the observation
  version constants (`OBSERVATION_COMPATIBILITY`), the release-lock schema and both profile bundles are
  untouched.
- The only observable internal effect is the value of the derived `installed_file_fingerprint` for a given
  wheel (it now binds four entry points instead of three). That value is computed at inspection time on both
  the wheel side and the installed side and is not a public interface; before this unit no candidate carrying
  the accepted packaging could pass validation at all.
- The integrity boundary is unchanged and remains closed: any unapproved additional entry point still fails
  set equality (`test_wheel_rejects_unapproved_third_plugin_entry_point` and the tampering cases pass).

### Residual risk

1. **Pre-existing ruff dirt at the base (unrelated to this unit).** After the change,
   `ruff check` reports 7 findings and `ruff format --check` 4 unformatted files with the locked `0.16.4`
   binary; the pristine base `21d44b5` reports the exact same set, and none of the paths is one this unit
   touched. Correcting them means editing `src/aether_agents/knowledge/semantic.py`,
   `tests/test_knowledge_regressions.py` and `tests/test_objective_contracts.py`, which are outside this
   unit's writable surface — reported, not edited; it is the same class as the preserved #364 finding.
2. **Literal plain-pytest invocation.** Acceptance item 3's literal command cannot pass
   `test_exact_public_lifecycle_uses_real_plugin_profiles_query_and_recovery`, because that test needs the
   exact Hermes checkout on `PYTHONPATH`; the project's documented runner supplies it and the test passes
   there. This limitation exists identically on the base and is not introduced here.
3. **The reported #364 public-artifact finding remains open and untouched**: the three-file lane still
   reports `test_tracked_public_surface_contains_no_operator_paths` for
   `.aether/objective-contracts/oc_0084270d940c98d9/v1.md`.

Supervisor owns aggregate release conclusions and integration; this file reports unit-level evidence only.
