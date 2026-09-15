# LC-RUNTIME — maintained-fork lock, local update route and state-preserving lifecycle

**Unit**: LC-RUNTIME (`t_359beef2`), role Implementer, worktree branch
`aether-agents-2/t_359beef2-lc-runtime-maintained-fork-lock-local-up`.
**Authority**: Objective Contract `oc_3397f9f05d780f8e@v1`
(SHA-256 `4d4c7650bf8ea93fc7cffe3d87f7f974e172d66cefcf6a74a2d83051568a4879`), base commit
`410c172ae69ffa87f6e32960ae4aef3b8d6598f0`, Supervisor breakdown with shared decisions 1–17
(`specs/001-aether-v1-productization/tasks.md` at `61124bc1`, amended at `5ede8524` and `337a071`).
Never edited the contract.
**Delivered scope**: contract in-scope 3–6, 9 and 10 (disposable lane); deliverables D2–D5;
acceptance obligations AC-01…AC-08 (implementation half).
**Working fork candidate**: `DarkArty07/aether-hermes:aether-main` at
`54eeb56dabefc98821d696656ed58c55dd777346` (clean checkout). This is the *working* candidate used
at development time, **not** the final accepted fork commit: `LC-PORT420` lands HLP-420 and
`LC-INT` re-derives `hermes.commit`, `source_tree_sha256` and the artifact digests at the merged
fork tip. No RED/GREEN result in this record was produced at a final accepted fork revision, and
no fork tag exists at the candidate revision, so the lock binds the fork by repository + branch +
exact `commit` + `source_tree_sha256` + artifact closure and leaves `hermes.tag` optional.

## 1. Starting point

Run 14 began from the run-7 worktree state: the run-7 implementation was **uncommitted** (HEAD at
base `410c172`, 13 modified files plus one untracked focused test module) and the previous run was
reclaimed while a live-state escape was in progress. Both facts shaped the order of work below.

Adopted run-7 work (verified, completed or repaired here): `schema_version` 4 maintained-fork
release lock and validation, the `aether update --local` route and its refusals, the XDG
active-record/staging/releases/`runtime/current`/launcher/Desktop/systemd projections, transition
recovery, doctor mismatch codes, the maintained-fork reconciliation generator and evidence, the
`hermes_exact` maintained-fork lane, and the owner's launcher separation integration.

## 2. Owner launcher separation (contract in-scope 3, card outcome 6)

The owner's two uncommitted launcher changes were integrated into this unit's worktree and the
owner's primary checkout was only read:

- `scripts/aether_tui.py` is **byte-identical** to the primary checkout: `diff` against that file
  reports no difference (`LAUNCHER BYTE-IDENTICAL`), and the primary checkout was never written by
  this unit.
- `tests/test_aether_tui_launcher.py` is **equivalent, not byte-identical**: the integrated file
  gained the separated-runtime lane (`test_check_supports_separated_runtime_and_state_roots`,
  `test_separated_runtime_paths_must_be_absolute`) that exercises
  `AETHER_PROJECT_ROOT`/`AETHER_HERMES_ROOT`/`AETHER_RUNTIME_ROOT`, and it differs from the owner's
  dirty file by exactly one wrapped expression at line 174 (the
  `project / "specs" / … / "project.schema.json"` tuple, five lines there, one line here) —
  semantically identical, and `ruff format --check` is clean at `line-length = 100` in both forms.

## 3. Blocking defect found at run start and repaired: #439 isolation

Run 7's candidate made `SystemdUserController` the default service seam and resolved the launcher,
Desktop-entry and unit destinations from the ambient environment, so a *disposable* store could
write the operator's real `~/.config/systemd/user` unit and signal the live user manager (issue
#439; the live unit entered a restart loop and was restored by Morfeo before this run started).

Repair, all inside this unit's writable surface:

- `ProjectionRoots` (launcher/Desktop/service directories) is now an explicit, injectable value
  (`src/aether_agents/lifecycle.py`): `ProjectionRoots.operator()` for the ambient installation,
  `ProjectionRoots.disposable(root)` for confined lanes.
- `LifecycleManager` resolves projection destinations through `projection_roots()`: an injected
  value wins; the ambient installation keeps the operator destinations; **every other store
  derives confined destinations beside its own root** (`<data-root-parent>/aether-projections/...`
  or the state-root parent when only the state root was redirected). A disposable manager can no
  longer resolve an operator destination at all.
- The default service controller is `SystemdUserController` **only** for the ambient installation
  with no injected roots. Every other manager gets `DisabledServiceController` and reports
  `service_restart: "disabled_non_installed_environment"` instead of silently restarting.
- `aether doctor --json` now reports `service_controller.available/reason` and records the exact
  projection error text under `projection_error` when projections cannot be read.
- The focused module gained the negative control
  `test_disposable_lane_cannot_reach_the_operator_unit_or_systemctl` (runs with the **ambient**
  environment, witnesses hash+mtime of the real launcher, Desktop entry and unit, patches
  `SystemdUserController.restart` to fail the test if it is ever reached, and proves the derived
  destinations live under the disposable root) and
  `test_installed_environment_is_the_only_operator_projection_owner` (production path preserved).

Independent observation beyond the test: `/tmp/lc_runtime_witness.sh` recorded hash+mtime of the
operator's `~/.local/bin/aether`, `~/.local/share/applications/hermes.desktop` and
`~/.config/systemd/user/hermes-gateway-morfeo.service` before and after every test invocation in
this run — including the complete 1704-test suite — and every comparison reported
`WITNESS UNCHANGED`. No `systemctl` invocation was made by this unit.

## 4. What changed

| File | Change |
| --- | --- |
| `src/aether_agents/lifecycle.py` | maintained-fork `HermesSource`/lock validation with per-mode retired-mode refusal (`_retired_mode_message`, each mode's own reason), `LocalCandidate` verification, `update_local`, projection seams (`ProjectionRoots`, confined derivation, disabled controller for non-installed stores), doctor/`service_plan` detail, duplicate `verify_clean_checkout` definition removed |
| `src/aether_agents/cli.py` | pinned `--local --aether-checkout --aether-commit --fork-checkout --fork-commit` surface, mutual exclusions, `_run_local_transition` preview/activation envelopes and refusals |
| `src/aether_agents/paths.py` | explicit `user_bin_dir`/`applications_dir`/`systemd_user_dir` resolvers |
| `src/aether_agents/resources/schemas/**` | packaged copy is Hatch-force-included from the contract copy, so the two stay byte-identical by construction (`pyproject.toml:55`) |
| `specs/001-aether-v1-productization/contracts/release-lock.schema.json` | `schema_version` const 4; `hermes.source_mode` const `maintained_fork`, `repository`/`branch` consts, `commit`, `source_tree_sha256`, optional `tag`, `python_requires`, closed `artifacts` closure; retired modes and transitional-only keys rejected, with the `source_mode` description naming each retired mode's own reason (review round, below) |
| `specs/001-aether-v1-productization/contracts/hermes-patch-reconciliation.schema.json` | maintained-fork selected-source reconciliation shape |
| `scripts/validate_hermes_patch_reconciliation.py` | maintained-fork generation/check mode (`--check` never writes), fail-closed partial/absent entries, one trailing newline in the generated preflight (fixed `git diff --check` whitespace error) |
| `HERMES_LOCAL_PATCHES.md` + `specs/.../evidence/hermes-patch-*` | ledger/aggregate/preflight reconciled to the maintained fork at `54eeb56` |
| `scripts/aether_tui.py` | owner launcher separation, byte-identical to the primary checkout |
| `tests/test_lifecycle_projections.py` (new) | preview/refusals, projection coherence, doctor mismatch, recovery reprojection, interruption at the service projection, update/rollback/forward-activation with hash-level state preservation, #439 isolation controls |
| `tests/test_observation_lifecycle.py` | maintained-fork lock fixtures and refusals, profile homes under the state root, RC-source `hermes_exact` lane, two assertion repairs (below), and the release-lock fixture version derived from the built wheel instead of a stale `0.24.0` literal (cross-unit repair requested by `LC-RELTOOL`/Supervisor); the retired-mode refusal block now asserts each mode's own reason instead of any borrowed one (§10) |
| `tests/test_a1_contracts.py` | schema v4 agreement with the owning r13 plan line, retired-mode/const-key refusals |
| `tests/test_hermes_patch_reconciliation.py`, `tests/test_aether_tui_launcher.py` | maintained-fork reconciliation and launcher-separation coverage |

Two defects in adopted tests were repaired rather than accommodated: the stale profile-home
assertion (`test_activation_materializes_three_explicit_profile_homes_under_store` now asserts the
state-root layout) and `test_release_lock_identity_is_explicit_and_semantically_matches_the_wheel`
(its forged-lock step left `version` at the previously forged value, so `load_release_lock` raised
before the intended observer-digest assertion; the test now restores both fields).

## 5. Requirement coverage (AC-01…AC-08, implementation half)

| Obligation | Evidence command | Observed result |
| --- | --- | --- |
| AC-01 source authority (fork identity, retired constant refused) | `uv run --frozen python scripts/run_tests.py -- -q -p no:cacheprovider tests/test_a1_contracts.py tests/test_observation_lifecycle.py -k "lock or fork or identity or materializes"`; `tests/test_hermes_baseline.py` | schema v4 accepts only `maintained_fork` + exact repository/branch/commit/tree/artifacts; `upstream` and `transitional_fork` each refuse with the reason that mode actually had (`transitional_fork`: fixed public baseline plus residual `patches/hermes/*.patch` replay; `upstream`: the RC's source identity is the maintained fork, and a deliberate upstream selection would need its own reviewed decision and schema representation) followed by the actionable regenerate guidance (`_retired_mode_message`); `tests/test_release_lock_uses_the_maintained_fork_identity_not_the_public_baseline` passes. `hermes.tag` is **not required** for `maintained_fork` (no tag exists at the fork candidate; the supervisor's measured decision) and a declared tag is still verified to dereference to the locked commit. PR/merge evidence for the fork and Aether repositories is `LC-FORK`/`LC-INT` work, not claimed here. |
| AC-02 patch completeness | `uv run --frozen python scripts/validate_hermes_patch_reconciliation.py --check --fork-checkout <clean fork checkout> --json` | `status: current`, `records: 29`, `present: 26`, `partial: 1`, `absent: 0`, `unverified: 2`; the single refusing entry is HLP-420 (`tests/agent/test_auxiliary_client_responses_terminal_420.py` absent at `54eeb56`) — owned by `LC-PORT420`, re-pinned by `LC-INT`. The local route refuses preparation on stale/refusing coverage (focused refusal tests). No `.patch` replay path exists in `src/` or `scripts/` (grep: only the retirement message and tests that assert refusal). |
| AC-03 layout/preservation | `tests/test_lifecycle_projections.py::test_local_update_preserves_mutable_state_bytes_and_rolls_back_exactly`; `tests/test_observation_lifecycle.py::test_update_rollback_reupdate_preserves_unknown_observation_bytes` | release code stays under the data root, operational homes and mutable state under the state root; observation bytes, a profile-home `sessions.sqlite3`, an owner memory file and monitor state keep identical SHA-256 across install → update → rollback → forward activation; the generic `~/.local/bin/hermes` was never touched. |
| AC-04 local preview | `tests/test_lifecycle_projections.py` (preview + every refusal); `test_cli_local_route_requires_the_complete_pinned_surface` | preview is read-only (`before == after` file list, no staging/releases/active pointer), reports exact Aether/fork revisions, target version/tag, HLP coverage, artifacts/hash, service interruption, preserved state and blockers; refuses dirty trees, commit mismatch, foreign origin, `VERSION`≠tag, wrong branch, incompatible Python, stale/refusing coverage, missing or conflicting pinned inputs and incomplete option surfaces without staging or activation. |
| AC-05 immutable candidate | `tests/test_observation_lifecycle.py::test_exact_public_lifecycle_uses_real_plugin_profiles_query_and_recovery` with `AETHER_MAINTAINED_FORK_CHECKOUT=<clean fork checkout at 54eeb56>` | 1 passed in 89.55s against the real maintained fork: wheel install into versioned manager/runtime environments, all three profile homes materialized, observer plugin loads/unloads with 22 callbacks and zero remaining, query reads the trace, update → rollback → forward activation preserve unknown-newer bytes, doctor reports not-ready on a deliberately broken runtime and rollback recovers, uninstall preserves observation state. Without a provisioned fork checkout the same lane proves the retired public baseline is refused (`not the selected repository`) and publishes nothing. |
| AC-06 atomic activation | `tests/test_lifecycle_projections.py::test_projection_follows_the_selector_and_reports_coherence`, `::test_interrupted_service_projection_restores_and_recovers_the_release`, `::test_recovery_reprojects_a_partial_transition` | after one transition the active record, `runtime/current`, launcher, Desktop entry and unit bytes agree; an injected interruption at the service projection leaves the previous release active with coherent projections, the transition journal failed, no service signalled, and a reopened manager reconciles the same durable state without a second transition. Unrelated services are never addressed (single-unit controller). |
| AC-07 doctor | `tests/test_lifecycle_projections.py::test_doctor_reports_fail_closed_projection_mismatches`; `tests/test_observation_lifecycle.py -k doctor` | `projection_status` reports `launcher_projection_mismatch`, `desktop_projection_missing`, `runtime_pointer_mismatch`; doctor maps them to `RUNTIME_POINTER_MISMATCH`/`LAUNCHER_PROJECTION_MISMATCH`/`DESKTOP_PROJECTION_MISMATCH`/`SERVICE_PROJECTION_MISMATCH` and now also reports the service-controller availability/reason. |
| AC-08 rollback | `tests/test_lifecycle_projections.py::test_local_update_preserves_mutable_state_bytes_and_rolls_back_exactly`; `tests/test_observation_lifecycle.py::test_rollback_uses_the_durable_predecessor_of_the_latest_activation` | rollback moves code/runtime/service back to the durable predecessor (selector and three service restarts observed through the injected controller) while every mutable-state SHA-256 stays identical; forward activation of the same target preserves them again. The real activation/rollback/forward-activation lane on published bytes is `LC-CLOSE`. |

## 6. Verification log (raw)

All commands run from the unit worktree; Hermes-facing lanes use the repository runner
(`scripts/run_tests.py`, exact checkout on `PYTHONPATH`).

- Focused module: `uv run --frozen python scripts/run_tests.py -- -q -p no:cacheprovider tests/test_lifecycle_projections.py` → **17 passed**.
- Focused sweep (lock/reconciliation/packaging/launcher/public-artifacts):
  `... -- -q -p no:cacheprovider tests/test_lifecycle_projections.py tests/test_a1_contracts.py tests/test_hermes_patch_reconciliation.py tests/test_hermes_baseline.py tests/test_hermes_editable.py tests/test_observation_packaging.py tests/test_aether_tui_launcher.py tests/test_public_artifacts.py`
  → **125 passed, 2 failed** — `test_release_lock_schema_and_plan_agree_on_version_four` (r13 plan line, `LC-DOCS`) and the policy manifest list (`LC-BLOCK` + a website entry), both integration-bound below.
- Full suite (canonical, uninstrumented): `uv run --frozen python scripts/run_tests.py -- -q --tb=no -rf -p no:cacheprovider`
  → **3 failed, 1709 passed, 70 skipped, 587 subtests passed in 263.20s**, and the three failures are
  exactly the integration-bound set: `test_release_lock_schema_and_plan_agree_on_version_four`
  (r13 plan line, `LC-DOCS`), `test_canonical_base_manifest_matches_tracked_non_specs_files`
  (policy manifest, `LC-BLOCK` + a website entry), and
  `test_telegram_monitor_cli_plugin.py::test_d15r_fixture_and_environment_gaps_chain_end_to_end`
  (#437, `LC-BLOCK`).
- Full suite with coverage instrumentation:
  `uv run --frozen python scripts/run_tests.py -- -q --cov=aether_agents --cov-report=term-missing --cov-fail-under=78 -p no:cacheprovider`
  → see §6.1. Under instrumentation the suite is slower and timing-sensitive Telegram-Monitor nodes
  can fail that pass uninstrumented and in isolation (measured: `test_d16t_lab_scheduler_stop_detects_cooperative_exit_and_records_status`
  3/3 passes in isolation, 0.16–0.21s each); those are the #438 class owned by `LC-BLOCK`.
- End-state full suite at the frozen commits (`a9c6137`, `15ee753`, `26771c5`):
  `uv run --frozen python scripts/run_tests.py -- -q --tb=no -rf -p no:cacheprovider` →
  **3 failed, 1709 passed, 70 skipped, 587 subtests passed in 386.86s**, the same three
  integration-bound failures and no others, with the operator-destination witnesses unchanged before
  and after the run.
- Earlier run at the same revision (before the fixture-version fix, for the record):
  **1704 passed, 6 failed, 70 skipped, 587 subtests passed in 451.79s**, with the extra failures being
  the RC-source lane before its repair and the version-coupled fixture repaired above.
- Coverage: `uv run --frozen python scripts/run_tests.py -- -q --cov=aether_agents --cov-report=term-missing -p no:cacheprovider` → see §6.1. The bare `uv run --frozen python -m pytest -q --cov=...` form cannot collect in a plain shell (`tests/test_same_card_phase_predicates.py` imports `hermes_cli`, which only the exact checkout provides) — the documented plain-lane limitation, unchanged by this unit.
- Static gates: `uv run --frozen ruff check src/aether_agents tests scripts` → **All checks passed**;
  `uv run --frozen ruff format --check src/aether_agents tests scripts` → **165 files already formatted**;
  `uv run --frozen mypy src/aether_agents` → **Success: no issues found in 67 source files**
  (note: `src/aether_agents/lifecycle.py` and `paths.py` are excluded by the pre-existing
  `[tool.mypy] exclude` for legacy inference defects; this unit did not change that configuration).
- Documentation gate: `uv run --frozen python scripts/check_documentation.py` → **fails with exactly
  five errors, all attributable to `LC-DOCS`'s pending registry rows** (integration-bound, see §7):
  `uncovered derived surface: cli.option.aether.update.--local`, `--aether-checkout`, `--aether-commit`,
  `--fork-checkout`, `--fork-commit`. No other documentation error is present. Re-confirmed unchanged at
  the review-round commit `59fa15c` (same five lines, no sixth error).
- Reconciliation: `uv run --frozen python scripts/validate_hermes_patch_reconciliation.py --check --fork-checkout <clean fork checkout> --json` → `reconciliation validation passed: reconciliation evidence is current`; `tests/test_hermes_patch_reconciliation.py` → **23 passed**.
- Whitespace: `git diff --check` → clean (one generated blank-line-at-EOF error in the run-7 preflight was fixed in the generator **and** the committed file so regeneration stays byte-identical).
- Skips: no test skip was added, removed or weakened by this unit. The RC-source lane's conditional
  asserts the fail-closed refusal of the retired public baseline when no fork checkout is provisioned;
  it is an assertion, never a skip. `pytest` skipped 70 nodes in the full run, all pre-existing
  platform/environment-conditioned skips in modules this unit did not touch.
- Build: `uv build` → `Successfully built dist/aether_agents-0.24.0.tar.gz` and
  `dist/aether_agents-0.24.0-py3-none-any.whl` (0.24.0 is the current `VERSION`; the RC version is
  `LC-RELTOOL`'s surface). The packaged copy of the release-lock schema read out of the wheel
  (`aether_agents/resources/schemas/release-lock.schema.json`) is **byte-identical** to
  `specs/001-aether-v1-productization/contracts/release-lock.schema.json`
  (SHA-256 `2d7035780c34bd970b56d05d0150f06de409a83f76402638ea814d1d0b5afc76`), so the packaged/contract
  pair cannot drift (Hatch force-include from the single contract file).
- Real CLI observation (read-only): `aether update --local --aether-checkout <disposable candidate clone> --aether-commit <clone commit> --fork-checkout <fork> --fork-commit 54eeb56… --dry-run --json` → exit 4,
  `ACTIVE_MANAGER_AUTHORITY_REQUIRED` ("no active manager can authorize this mutation"). Stateful
  commands are dispatched through the authenticated active manager by the pre-existing
  `_STATEFUL_COMMANDS` gate (`src/aether_agents/cli.py`, unchanged by this unit), so the real local
  preview/activation lane runs through the installed manager after `LC-INT` installs the RC —
  `LC-CLOSE`'s lane. Live witness: unchanged; the live installation was only read.
- Review round (Supervisor run 30, changes requested on accuracy only, branch tip `fb22bd6`):
  `uv run --frozen python scripts/run_tests.py -- -q -p no:cacheprovider "tests/test_observation_lifecycle.py::test_release_lock_uses_the_maintained_fork_identity_not_the_public_baseline"`
  → **1 passed in 0.13s** with the extended per-mode refusal assertions;
  `… scripts/run_tests.py -- -q -p no:cacheprovider tests/test_a1_contracts.py` →
  **1 failed, 29 passed, 11 subtests passed in 1.34s**, the single failure being the
  integration-bound r13 plan line (§7.2); focused sweep
  `… tests/test_lifecycle_projections.py tests/test_a1_contracts.py tests/test_hermes_patch_reconciliation.py tests/test_hermes_baseline.py tests/test_hermes_editable.py tests/test_observation_packaging.py tests/test_aether_tui_launcher.py tests/test_public_artifacts.py`
  → **2 failed, 125 passed, 20 subtests passed in 40.78s**, the two failures exactly the
  integration-bound r13 plan line and the policy manifest, no new failure;
  `ruff check src/aether_agents/lifecycle.py tests/test_observation_lifecycle.py` →
  **All checks passed**; `ruff format --check` on the same two files → **2 files already formatted**.
  Both retirement texts were rendered and read directly (§10) instead of being assumed.
- End-state full suite at the review-round commit (`59fa15c`):
  `uv run --frozen python scripts/run_tests.py -- -q --tb=no -rf -p no:cacheprovider` →
  **3 failed, 1709 passed, 70 skipped, 587 subtests passed in 398.59s (0:06:38)**, the same three
  integration-bound failures and no others (`test_release_lock_schema_and_plan_agree_on_version_four`,
  `test_canonical_base_manifest_matches_tracked_non_specs_files`,
  `test_telegram_monitor_cli_plugin.py::test_d15r_fixture_and_environment_gaps_chain_end_to_end`).
  Operator-destination witness captured before (`00:00:41`) and after (`00:07:21`) the run:
  `~/.local/bin/aether` `ca2479e4…` mtime `1789443062`, `hermes.desktop` `2338dfa7…` mtime
  `1789443068`, `hermes-gateway-morfeo.service` `1b7421b1…` mtime `1789445613` — all **byte- and
  mtime-identical**, the same values the Supervisor captured independently in review run 30;
  `aether-gateway-morfeo.service` absent before and after, and no `systemctl` invocation was made
  (`WITNESS UNCHANGED`).

### 6.1 Coverage result

`uv run --frozen python scripts/run_tests.py -- -q --tb=no -rf --cov=aether_agents --cov-report=term-missing --cov-fail-under=78 -p no:cacheprovider`
→ test outcomes under instrumentation: **7 failed, 1705 passed, 70 skipped, 587 subtests passed in
621.39s (0:10:21)**, exit status 3; the **coverage report itself could not be produced**:

```text
INTERNALERROR>   File ".../pytest_cov/engine.py", line 336, in finish
INTERNALERROR>     self.cov.combine()
INTERNALERROR>   File ".../coverage/data.py", line 216, in combine_parallel_data
INTERNALERROR> coverage.exceptions.DataError: Can't combine statement coverage data with branch data
```

Measured facts and disposition:

- The same `combine()` failure occurred on the first coverage attempt in this session, before any unit
  edit beyond the isolation repair, and again on a clean `.coverage*` slate, so it is not introduced
  by the changes in this record.
- The suite mixes coverage data modes: `[tool.coverage.run]` configures `branch = true` while
  per-process `.coverage.<host>.<pid>.<random>` data files produced during the run carry statement
  data. Both `pyproject.toml` (coverage configuration) and `scripts/run_tests.py` are outside this
  unit's writable surface, so the fix is not made here.
- The two extra failures under instrumentation (beyond the three attributable ones) are the
  timing-sensitive Telegram-Monitor nodes that pass uninstrumented and in isolation (measured for
  `test_d16t_lab_scheduler_stop_detects_cooperative_exit_and_records_status`: 3/3 passes, 0.16–0.21s).
- Therefore **the 78 % coverage floor is not evaluated in this lane and this unit does not claim it**;
  `LC-INT` must produce the coverage verdict on the integrated revision (and may need to fix the mixed
  coverage modes). This is reported, not absorbed.

## 7. Integration-bound and cross-unit items

1. **`LC-DOCS` — capability registry**: the five pinned `cli.option.aether.update.*` rows and
   `docs/reference/cli.md` are that unit's surface; this branch deliberately reports exactly those
   five `uncovered derived surface` errors and claims no documentation-green in isolation.
2. **`LC-DOCS` — r13 plan line**: `tests/test_a1_contracts.py::test_release_lock_schema_and_plan_agree_on_version_four`
   fails on this branch only because `specs/r13-synthesis-and-release/plan.md` still says
   "release-lock schema is integer `3`". The schema constant (4) and the assertion were updated
   together and the assertion still proves the schema/plan agreement; the plan line is that unit's.
3. **`LC-BLOCK` — policy manifest**: `tests/test_public_artifacts.py::test_canonical_base_manifest_matches_tracked_non_specs_files`
   compares the whole `policy.yml` heredoc against every tracked non-`specs/` file. At the base the
   heredoc is already missing `.aether/objective-contracts/oc_3397f9f05d780f8e/v1.md` (added by the
   contract commit) and `website/tests/content.test.mjs`; this unit adds one further tracked file,
   so `LC-INT` must append this exact line to the heredoc (10-space indent, non-`specs/` manifest):
   `          tests/test_lifecycle_projections.py`
4. **`LC-BLOCK` — Monitor regressions**: `test_telegram_monitor_cli_plugin.py::test_d15r_fixture_and_environment_gaps_chain_end_to_end`
   fails in isolation (the #437 class: the shipped writer rejects the D15R fixture that does not
   name a distinct reviewer) and `::test_d16t_lab_scheduler_stop_detects_cooperative_exit_and_records_status`
   fails only in the full-suite order (**3/3 passes in isolation**, 0.16–0.21s each — the #438
   order/ambient dependence). Both are that unit's declared outcome; this unit did not touch the
   Monitor modules.
5. **`LC-PORT420` / `LC-INT` — fork pinning**: `54eeb56` is the working candidate. The reconciliation
   aggregate is current *at that revision* and will be regenerated at the merged fork tip; the lock
   generator/validator take the fork commit and tree digest as explicit inputs so re-pinning stays
   mechanical, and digests that do not match are refused (kept fail-closed, not softened).
6. **`LC-CLOSE` — first promotion through the new boundary**: measured read-only, the live
   installation currently exposes `runtime/current` (a prepared release directory) but **no
   authenticated active record** (`active.json` absent in both the data and state roots), so
   `aether update` correctly reports `ACTIVE_MANAGER_AUTHORITY_REQUIRED` instead of acting. The RC's
   first promotion therefore has to install/bootstrap the active record before the local route can
   be used as the sole promotion boundary; that sequencing belongs to the integration/closeout lane,
   not to this unit, and this unit performed no live mutation to create the record.
7. **`LC-RELTOOL` — version-coupled fixture, repaired here**: at `VERSION` `1.0.0rc1`,
   `test_prepare_release_installs_one_wheel_in_manager_and_exact_runtime` built the repository's real
   wheel but wrote its fixture lock with a hardcoded `0.24.0` package version, so the wheel-identity
   comparison refused it. The fixture now reads the built wheel's own metadata version and the shared
   lock helper derives display version and release tag from the PEP 440 package version. Verified:
   that node passes (11.40s) with the operator-destination witnesses unchanged. No other stale
   product-version literal exists in the touched surfaces (the remaining `0.24.0` occurrences are
   inert fixture data and a now version-agnostic comment).
8. **`LC-INT` — coverage gate not evaluated on this branch** (see §6.1): neither lane measured the
   78 % floor here. The `scripts/run_tests.py --cov` attempt (pytest-cov) cannot produce a report
   because its `combine()` refuses mixed statement/branch data, and CI's actual enforcement is a
   different invocation — `uv run --frozen coverage run -m pytest … --ignore=tests/test_observation_performance.py`
   followed by `uv run --frozen coverage report --format=total` (`.github/workflows/policy.yml:639-643`),
   where both invocations share the `branch = true` configuration. No green coverage claim is made in
   this unit in either lane; per Shared decision 16 the floor is `LC-INT`'s obligation on the merged
   tree, and a real failure there returns as an integration finding rather than being absorbed here.
   The Supervisor corrected this row's earlier attribution in review run 30 (the pytest-cov failure is
   not evidence about the CI lane).
9. **`LC-FORK` / `LC-INT` — canonical encoding of `hermes.source_tree_sha256`** (raised to the
   controller as request #10 and **resolved**; recorded as Shared decision 19 in
   `specs/001-aether-v1-productization/tasks.md` at `4cb3235`): the shipping validator is canonical —
   `lifecycle._tree_sha256` re-derives the value from the materialized commit (rows
   `(posix-relative-path, sha256(file bytes))` in `os.walk` DFS order with per-level sorted names,
   `__pycache__` excluded, symlinks/non-regular files refused, serialized as compact JSON and hashed),
   so `LC-INT` generates the re-pinned lock with it. Two independent causes explained the divergence
   with LC-FORK's published figures, and neither is a defect here: LC-FORK's numbers are **blob-based**
   snapshots (`sha256` of the Git blob bytes; the fork's nine `*.ps1` files are LF in the blob and CRLF
   when materialized, so a blob recipe can never equal a materialized one), and a **global path sort**
   is not the same order as the canonical DFS walk. Canonical values at the two revisions I measured
   locally: `54eeb56dabefc98821d696656ed58c55dd777346` → `4f0c6fabb658bcb49e14ebfd97ec60b5bdca249471d7706cb1532fcf56095295`
   (tree `8d50484dcc…`), `387705ea1dd76f43585fca220b11859173cc4a6b` → `fb3e5336a0106ad96ccac88345f23880a9f2597235f023aab246add4a2498337`
   (tree `ead7e6c3c4…`); each materializes to 9,375 regular files with no symlink. The lock schema
   description and the function docstring now state the recipe explicitly, and
   `tests/test_lifecycle_projections.py::test_tree_projection_encoding_is_the_documented_canonical_recipe`
   pins it (including that the sort variant differs). `aether_agents.hermes_editable.compute_source_tree_sha256`
   is a *different* projection for the editable path and is never the lock recipe.

## 8. Residual risk

- The interruption, recovery and preservation evidence uses disposable stores with synthetic
  releases and an injected recording controller. It proves the route's sequencing, atomicity and
  fail-closed identity behavior; it does not prove a real systemd restart (deliberately: that is
  the bounded live lane, and the unit is forbidden from restarting the operator's services).
- `hermes.tag` is optional for `maintained_fork` because no tag exists at the fork candidate; a
  declared tag is still verified to dereference to the locked commit. Re-pinning at `LC-INT` must keep
  `commit`/`source_tree_sha256`/artifact digests consistent — the validator refuses mismatches.
- HLP-420 is refusing at `54eeb56`: the RC cannot be prepared from that revision until `LC-PORT420`
  lands, which is the intended fail-closed behavior, not a defect in this unit.
- `specs/telegram-monitor/evidence/*` and `specs/007-.../evidence/SR-396.md` reference the
  `hermes_exact` lane by its historical name; the lane keeps that name and now qualifies the RC
  source instead of the retired public baseline. The historical records were not rewritten.

## 9. Compatibility (unit-level only)

Unit-level compatibility impact: **breaking for the retired source model, additive for the CLI
surface**. The release-lock document moves from `schema_version` 3 (`upstream`/`transitional_fork`)
to 4 (`maintained_fork` only); `aether update` gains five options and `--local` mode; the packaged
schema copy is force-included from the single contract file, so no packaged/contract drift is
possible. All other manager commands keep their pinned envelopes. This is not an aggregate release
conclusion: `LC-INT` owns the merged-tree gates, the fork re-pin and publication, and `LC-CLOSE`
owns the real activation lane and the terminal report.

## 10. Review round and its disposition

Supervisor review run 30 (claimed from the review lane at branch tip `fb22bd6`) returned **changes
requested** for one bounded accuracy item: the refusal texts attributed residual `.patch` replay to
`upstream`, which never replayed patches — only `transitional_fork` did (fixed public baseline plus
residual patch replay). The review confirmed the refusal *behaviour* as contract-backed (AC-01/D2)
and required only the claims to be corrected, so behaviour was not touched.

Applied in this round, entirely inside the declared writable surface:

| Text | Before | After |
| --- | --- | --- |
| `contracts/release-lock.schema.json` `source_mode` description | one shared claim that the retired `upstream` and `transitional_fork` modes "replayed residual `.patch` files onto a fixed public baseline" | each mode's own reason: `transitional_fork` = a fixed public baseline plus residual `.patch` replay; `upstream` = the released public artifact consumed as-is, not the RC's source identity, needing its own reviewed decision and schema representation |
| `src/aether_agents/lifecycle.py` comment above the constants | "The retired modes replayed … onto a fixed public baseline" | per-mode statement, closing with "each is refused with the reason that mode actually had, never a borrowed one" |
| `_RETIRED_MODE_MESSAGE` | one reason for both modes ("the fixed public baseline and its residual patch replay …") | `_RETIRED_MODE_REASONS` + `_retired_mode_message(mode)`: each mode carries the reason it actually had, followed by the unchanged actionable regenerate guidance. Both call sites (`HermesSource.from_record`, `_refuse_retired_source_mode`) use the helper |
| `tests/test_observation_lifecycle.py` refusal block | a single `match="retired"` on `transitional_fork` | both modes asserted: `transitional_fork` must state "residual patches/hermes/*.patch replay" and name `maintained_fork`; `upstream` must name the maintained-fork repository, contain "released public artifact", and contain neither "residual" nor a replay claim. RED/GREEN measured, not assumed: with the pre-fix module restored (`git checkout -- src/aether_agents/lifecycle.py`) the node fails (**1 failed in 0.18s**, at the `transitional_fork` phrase), and the pre-fix `upstream` text also fails its assertions ("released public artifact" absent, "residual" present) while the replay-claim assertion alone does not distinguish the two texts; after restoring the fixed module byte-exactly (SHA-256 `1bf090e48c5e6c29dff8a2a6b0026765f6901d0eb41d90dffd7874ff08423081`) the node passes (**1 passed in 0.11s**) |
| this record, §2 | both launcher changes described as "integrated byte-identically" | `scripts/aether_tui.py` is byte-identical; `tests/test_aether_tui_launcher.py` is equivalent-but-not-byte-identical (one wrapped expression at line 174) |
| this record, §5 AC-01 row and §7.8 | quoted `_RETIRED_MODE_MESSAGE` as one generic reason; attributed the unmeasured coverage floor to the pytest-cov lane | per-mode reasons recorded; coverage attribution corrected to the CI invocation (`policy.yml:639-643`) as an `LC-INT` obligation, the Supervisor's correction from the same review |

Refusal behaviour is unchanged: both retired modes still refuse before any staging or activation,
each naming the maintained fork, branch and exact-commit regeneration path. Nothing in this round
changed acceptance, the pinned identifiers, a shared interface or another unit's file.
