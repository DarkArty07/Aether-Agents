# LG-LIFE — Release-owned TUI and branded projections

**Authority.** Objective Contract `oc_ff82ba151cdf3861@v2` (SHA-256
`e5c4fea02a5b1cee977c93a602d5af622b59e7325c9efb3be7d7b1e7bfc49bd0`), in-scope
items 2 and 3; AC-3, AC-4, and AC-5; issues #480/#481; breakdown unit LG-LIFE from
`specs/001-aether-v1-productization/tasks-rc4.md`.

**Base.** Commit `00715d237d795e365c5e462b6b80d5a1bd8d8188`. Worktree clean at start.

**New tracked non-`specs/` paths for LG-DOCS:** `tests/test_tui_projections.py`.

**Unit compatibility.** `patch` (internal lifecycle, projection and bundle-tooling
repair; no product interface removed).

## Round-4 change: the supplied tree is the only source of the TUI bytes

Round-3 review item: `build_tui_in_disposable_workspace` still ran
`git -C <supplied> archive <commit>`, so Git resolved an *enclosing* repository whenever
the supplied path had no `.git` of its own. `clean_install` hands the builder the archive
extraction, which never has one, so bundle qualification either failed on a clean runner
or — on a developer host whose object database happens to carry an unreachable Hermes
object — archived bytes that no clean clone of the supplied tree contains.

| Path | Change |
| --- | --- |
| `src/aether_agents/lifecycle.py` | `_own_git_directory()`, `_git_prefix()` and `_git_environment()` bind every supplied-checkout Git call to `<checkout>/.git` (`--git-dir=<path>`), strip ambient `GIT_DIR` / `GIT_WORK_TREE` / `GIT_COMMON_DIR` / `GIT_OBJECT_DIRECTORY` / `GIT_ALTERNATE_OBJECT_DIRECTORIES` / `GIT_INDEX_FILE` / `GIT_CEILING_DIRECTORIES`, and fence discovery at the supplied path when it has no own `.git`. `build_tui_in_disposable_workspace` archives only the supplied checkout's own repository; an already-materialized exact-commit tree (the bundle extraction) is copied into the disposable workspace and built there; a supplied tree that cannot carry `ui-tui` fails closed with a specific `IntegrityError`. Receipt and `provenance.json` gain `source` (`git-archive` / `materialized-tree`). `_git()` and `_materialize_git_archive()` (locked-source digest input to `_tree_sha256`) use the same binding |
| `scripts/release_bundle.py` | `materialize_fork_closure()` extracts the bundle archive into its single closure root; `stage_fork_tui()` stages the release-owned TUI from that closure (never a checkout, never an enclosing repository); `clean_install()` uses both and records the staged asset as `tui_asset` (`sha256`, `entry_path`, `source`, `node_version`, `npm_version`) in the clean-install report |
| `tests/test_tui_projections.py` | Six new deterministic nodes: materialized-tree staging, refusal to archive an enclosing repository, own-`.git` archive of the requested commit, refusal of a tree without `ui-tui`, `_git` supplied-directory binding, `_materialize_git_archive` supplied-directory binding. No skip, no operator path |
| `tests/test_release_bundle.py` | Two new nodes: closure extraction refuses a multi-root archive; the bundle TUI stage builds the extracted closure (with an enclosing repository present) and leaves the closure read only |

Earlier rounds of this unit (branded `Aether` / `Continue Aether` projections, WSL
adapters, legacy `hermes.desktop` retirement, exact project binding, service
`HERMES_TUI_DIR` drift, doctor `TUI_ASSET_*` codes) are unchanged by this round.

## Fail-first evidence (measured before the fix, same nodes)

`pytest -q tests/test_tui_projections.py -k "materialized_tree_without_repository or
never_archives_an_enclosing_repository or requested_commit_from_its_own_git_entry or
refuses_tree_without_ui_tui or binds_to_the_supplied_directory or
source_materialization_never_archives"` → **6 failed, 11 deselected in 3.03 s**

| Node | Observed before the fix |
| --- | --- |
| `test_tui_build_stages_materialized_tree_without_repository` | `IntegrityError: failed to extract git archive of commit aed6591a…` (the `clean_install` shape refused) |
| `test_tui_build_never_archives_an_enclosing_repository` | enclosing repository archived, then `npm install … ENOENT … /tmp/…/package.json` |
| `test_tui_build_archives_the_requested_commit_from_its_own_git_entry` | build ran; receipt had no `source` |
| `test_tui_build_refuses_tree_without_ui_tui` | npm failure instead of a specific refusal |
| `test_checkout_git_inspection_binds_to_the_supplied_directory` | `_git` returned `true` for a directory inside an enclosing repository |
| `test_source_materialization_never_archives_an_enclosing_repository` | `_materialize_git_archive` archived the enclosing repository |

## Verification matrix

| Obligation | Command / check | Result | Evidence location |
| --- | --- | --- | --- |
| Supplied-checkout binding (round-3 item) | `uv run --frozen pytest -q tests/test_tui_projections.py` | **17 passed** | `tests/test_tui_projections.py:258, 282, 306, 328, 340, 351` |
| Bundle TUI stage from the extracted closure | `uv run --frozen pytest -q tests/test_release_bundle.py` | **37 passed** | `tests/test_release_bundle.py:522, 537` |
| Focused LG-LIFE lane | `uv run --frozen pytest -q tests/test_tui_projections.py tests/test_lifecycle_projections.py tests/test_release_bundle.py` | **75 passed in 15.9 s** (75 collected) | this record |
| Observation / qualification / baseline / patch lanes | `uv run --frozen python scripts/run_tests.py -- -q tests/test_observation_lifecycle.py tests/test_hermes_baseline.py tests/test_same_card_phase_predicates.py tests/test_observation_qualification.py tests/test_hermes_patch_reconciliation.py` | **200 passed, 1 skipped in 166.8 s** | this record |
| Full repository runner | `AETHER_EXACT_HERMES_CHECKOUT=<exact baseline checkout> AETHER_MAINTAINED_FORK_CHECKOUT=<provisioned fork checkout> uv run --frozen python scripts/run_tests.py -- -q` | **2 failed, 1809 passed, 70 skipped, 587 subtests passed in 396.7 s** | this record; residuals below |
| Integrated coverage floor (decision 12) | `PYTHONPATH=<exact baseline checkout> AETHER_GRAPHIFY_PYTHON=<isolated component python> AETHER_TEST_COMPONENT_INSTALL=1 uv run --frozen coverage run -m pytest -q --ignore=tests/test_observation_performance.py`; `<component python> -m coverage run --append -m pytest -q tests/test_graphify_worker_native.py`; `uv run --frozen coverage report --format=total` | main lane **2 failed, 1866 passed, 9 skipped, 587 subtests passed in 513.6 s** (same two residuals); component lane **36 passed**; total **78**, exit 0 against the `fail_under = 78` floor | this record |
| Public artifact path scan | `uv run --frozen python scripts/check_public_artifacts.py --root .` | exit 0, 0 findings | this record |
| Documentation check | `uv run --frozen python scripts/check_documentation.py` | exit 0 | this record |
| Wheel & sdist build | `uv build` | sdist + wheel built | this record |
| Ruff lint / format | `uv run --frozen ruff check src/aether_agents tests scripts`; `ruff format --check …` | pass; 172 files formatted | this record |
| Type check | `uv run --frozen mypy src/aether_agents` | 0 issues, 67 files | this record |
| New skips introduced | `pytest --collect-only` counts + `grep -n "pytest.skip" tests/test_tui_projections.py` | none | this record |

## Full-runner residuals (both outside this unit)

The same two nodes fail in the coverage lane. Without `AETHER_GRAPHIFY_PYTHON` /
`AETHER_TEST_COMPONENT_INSTALL` exported for the main lane the knowledge and Graphify
integration nodes skip (70 skips) and the measured total is 76; the isolated component
lane alone does not recover that delta, so the canonical environment above is the one
the floor refers to.

| Failing node | Observed | Why it is not this unit |
| --- | --- | --- |
| `tests/test_aether_tui_launcher.py::MorfeoTuiLauncherTests::test_versioned_launcher_contains_no_machine_specific_home` | `AssertionError: 509 != 493` — the checkout's `scripts/aether_tui.py` is `0o775` on disk while the index records `100755`; `git status` reports no change for the path | `scripts/aether_tui.py` is out of this unit's writable surface and unmodified in this diff; the residue predates this round (same failure reported in the round-3 handoff) |
| `tests/test_public_artifacts.py::test_canonical_base_manifest_matches_tracked_non_specs_files` | the `policy.yml` manifest has 422 entries, tracked non-`specs/` files are 425: missing `.aether/objective-contracts/oc_ff82ba151cdf3861/v1.md`, `…/v2.md`, `tests/test_tui_projections.py` | decision 11 makes `policy.yml` registration LG-DOCS work; this unit records `tests/test_tui_projections.py` in the handoff instead of editing the workflow |

## Live evidence (provisioned maintained fork, disposable workspace)

| Check | Measurement |
| --- | --- |
| Exact-commit archive build from the fork checkout | commit `aed6591a69f453a1867b73628603e7b53ba40ffc`; `source=git-archive`; Node `v22.23.2`; npm `10.9.8`; `dist/entry.js` SHA-256 `f56f6225d9124376eedec1834d372c76a33292aedc41021cc13d6c3b32a05643` in 8.6 s |
| Build from the materialized exact-commit tree (no `.git`) | same digest `f56f6225…`; `source=materialized-tree`; 8.1 s; digest equality with the archive build |
| Real PTY launch of the release-owned asset | `node <release-tui>/dist/entry.js` with `HERMES_TUI_DIR` set and `npm` replaced by a failing sentinel: TUI rendered (ink alternate screen) and was terminated after the 20 s probe window (`exit_code 143`); `npm_invoked=false`; locked-source inventory **9,377 entries identical before/after**; no `node_modules`, no `ui-tui/dist` in the locked source |
| Fresh `--no-local` clone of the unit branch (CI checkout shape) | Hermes pin object absent (`cat-file` exit 128); build **refused**: `failed to extract git archive of commit aed6591a…`; the clone's own worktree is still refused for `ui-tui` rather than archived from anywhere else |
| Non-repository tree inside this Aether worktree (leaked object DB) | build **refused** on the supplied tree: `maintained fork source does not contain ui-tui/package.json` (no enclosing object database consulted) |

Repeated clean builds from both source shapes produced the same digest as the earlier
rounds of this unit, so the binding repair changed no staged byte.

## Non-claims

This unit does not author the packaged CLI module (LG-CLI), update `VERSION` or
documentation identity (LG-DOCS), register the new test path in `policy.yml` (LG-DOCS),
or activate the live host installation, mutate issues, tag or publish (LG-CLOSE /
Supervisor). The `specs/` record is unit evidence, not an aggregate release conclusion;
`release_impact` / `release_action` / `release_channel` belong to LG-CLOSE.
