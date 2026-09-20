# LG-LIFE — Release-owned TUI and branded projections

**Authority.** Objective Contract `oc_ff82ba151cdf3861@v2` (SHA-256
`e5c4fea02a5b1cee977c93a602d5af622b59e7325c9efb3be7d7b1e7bfc49bd0`), in-scope
items 2 and 3; AC-3, AC-4, and AC-5; issues #480/#481; breakdown unit LG-LIFE from
`specs/001-aether-v1-productization/tasks-rc4.md`.

**Base.** Commit `00715d237d795e365c5e462b6b80d5a1bd8d8188`. Worktree clean at start.

**New tracked non-`specs/` paths for LG-DOCS:** `tests/test_tui_projections.py`.

**Unit compatibility.** `patch` (internal lifecycle, projection and bundle-tooling
repair; no product interface removed).

## Round-5 change: the archive binding is independent of the ambient Git environment

Round-4 review item: the archive callers passed

`env={**_isolated_subprocess_environment(), **_git_environment(checkout)}`

`_isolated_subprocess_environment()` copies the process environment and keeps `GIT_*`,
while `_git_environment()` merely *omits* the override names from its own dict. A dict
merge cannot delete a key the second mapping never carried, so an inherited `GIT_DIR`
survived and beat both `-C <path>` and `--git-dir=<path>`. Every Git inspection and
archive step therefore still had one ambient route back to whatever repository `GIT_DIR`
named — on this host, this Aether checkout and its unreachable Hermes object.

| Path | Change |
| --- | --- |
| `src/aether_agents/lifecycle.py` | `_git_environment()` is now the single composer: it starts from `_isolated_subprocess_environment()` and deletes the seven override names from that mapping, adding only the deliberate `GIT_CEILING_DIRECTORIES=<parent>` when the supplied path has no own `.git`. `_git()`, `_materialize_git_archive()` and `build_tui_in_disposable_workspace()` pass that one mapping instead of merging two, so no Git subprocess in the module can inherit an ambient binding |
| `scripts/release_bundle.py` | `_GIT_ENVIRONMENT_OVERRIDES`, `_own_git_directory()`, `_git_command()` (appends `--git-dir=<repo>/.git`) and `_git_environment()`; `_isolated_environment()` deletes the same names so no child process (`uv`, cloned-repo tooling, the product CLI) inherits them either. `_git()`, `_git_raw()`, `_git_archive_bytes()` and `_read_project_metadata()` are all bound to the supplied repository. Git *config* variables are deliberately untouched: stripping `GIT_CONFIG_*` would break `safe.directory` handling on CI runners without fixing the repository binding |
| `tests/test_tui_projections.py` | Fixture Git helper strips `GIT_*`; three new nodes: composed environment under a hostile ambient set, refusal of an ambient `GIT_DIR`/`GIT_OBJECT_DIRECTORY` for a supplied non-repository, and a supplied checkout that still archives only its own commit while the ambient binding is set |
| `tests/test_release_bundle.py` | Fixture Git helper strips `GIT_*`; one new node: under ambient `GIT_DIR` (and separately `GIT_OBJECT_DIRECTORY`) the pin cannot be archived out of a fork, the fork's own `HEAD` and declared metadata still resolve, and the fork's own archive carries no `ui-tui` members |
| `tests/test_lifecycle_projections.py` | Fixture Git helper strips `GIT_*` so the lane is immune to an ambient binding |

## Fail-first evidence (measured before the fix)

Standalone probe against the pre-fix revision (fixture Git commands env-cleaned, so the
probe itself never inherits the trap it sets):

| Probe | Observed before the fix |
| --- | --- |
| `{**_isolated_subprocess_environment(), **_git_environment(<non-repository>)}` with ambient `GIT_DIR` | `GIT_DIR` still present in the merged mapping, value = this worktree's `.git` |
| `_materialize_git_archive(<supplied non-repository>, aed6591a…, <dest>)` | **succeeded**; `dest` materialized 10,366 entries of this Aether checkout (`.coderabbit.yaml`, `.dockerignore`, …) — the locked-source digest input |
| `release_bundle._git_archive_bytes(<tiny fork with only ONLY-FORK.txt>, aed6591a…, "hermes-agent")` | **succeeded** with 10,367 members, `hermes-agent/ui-tui` present, `ONLY-FORK.txt` absent |
| `git rev-parse HEAD` inside that fork via `release_bundle._git` | returned this checkout's revision — the fork's own history was unreachable |

Node-level fail-first: with only the production changes stashed,
`pytest -q tests/test_tui_projections.py -k "ambient or binds_a_supplied"
tests/test_release_bundle.py -k ambient` → **3 failed, 1 passed, 54 deselected in
6.82 s**. The composed-environment assertion alone passes pre-fix (the old
`_git_environment()` already filtered `os.environ`); the defect lived in the merge at the
call sites, which the two lifecycle integration nodes and the bundle node do catch.

## Post-fix probes (hostile ambient set, same fixtures)

| Probe | Observed |
| --- | --- |
| All seven override names exported (`GIT_DIR`, `GIT_WORK_TREE`, `GIT_COMMON_DIR`, `GIT_OBJECT_DIRECTORY`, `GIT_ALTERNATE_OBJECT_DIRECTORIES`, `GIT_INDEX_FILE`, `GIT_CEILING_DIRECTORIES`, all pointed at this checkout) | zero names survive in `lifecycle._git_environment()` and `release_bundle._git_environment()`; the non-repository path carries only `GIT_CEILING_DIRECTORIES=<resolved parent>` |
| `lifecycle._git(<supplied checkout>, "rev-parse", "HEAD" / "--show-toplevel")` | the supplied checkout's own commit and `--show-toplevel` = the supplied directory |
| `release_bundle._git(["rev-parse", "HEAD"], <fork>)`, `_read_project_metadata(<fork>, <fork HEAD>)` | the fork's own `HEAD`; `{'name': 'hermes-agent', 'version': '0.20.4', 'requires_python': '>=3.11,<3.14'}` |
| `lifecycle._materialize_git_archive(<non-repository>, aed6591a…, <dest>)` | refused: `Hermes source archive failed (git exit 128)`; `dest` not created |
| `release_bundle._git_archive_bytes(<fork without the pin>, aed6591a…)` | refused: `archive-failed: archiving aed6591a… failed`; no `ui-tui` member can be emitted |
| `_git_archive_bytes(<fork>, <fork HEAD>)` | only `hermes-agent`, `hermes-agent/ONLY-FORK.txt`, `hermes-agent/pyproject.toml` |

Earlier rounds of this unit (branded `Aether` / `Continue Aether` projections, WSL
adapters, legacy `hermes.desktop` retirement, exact project binding, service
`HERMES_TUI_DIR` drift, doctor `TUI_ASSET_*` codes, materialized-tree staging) are
unchanged by this round.

## Verification matrix

| Obligation | Command / check | Result | Evidence location |
| --- | --- | --- | --- |
| Focused LG-LIFE lane | `uv run --frozen python -m pytest -q tests/test_tui_projections.py tests/test_lifecycle_projections.py tests/test_release_bundle.py` | **79 passed in 15.4 s** (79 collected) | this record |
| The same lane with `GIT_DIR` / `GIT_OBJECT_DIRECTORY` / `GIT_ALTERNATE_OBJECT_DIRECTORIES` exported for the whole process, pointed at this checkout | as above | **79 passed in 14.7 s**; repository state unchanged (same `HEAD`, no local `user.*`, no index or worktree drift) | this record |
| Observation / qualification / baseline / patch lanes | `uv run --frozen python scripts/run_tests.py -- -q tests/test_observation_lifecycle.py tests/test_hermes_baseline.py tests/test_same_card_phase_predicates.py tests/test_observation_qualification.py tests/test_hermes_patch_reconciliation.py` | **200 passed, 1 skipped in 163.3 s** | this record |
| Full repository runner | `AETHER_MAINTAINED_FORK_CHECKOUT=<provisioned fork checkout> uv run --frozen python scripts/run_tests.py -- -q` | **2 failed, 1813 passed, 70 skipped, 587 subtests passed in 353.0 s** | this record; residuals below |
| Integrated coverage floor (decision 12) | `PYTHONPATH=<exact baseline checkout> AETHER_GRAPHIFY_PYTHON=<isolated component python> AETHER_TEST_COMPONENT_INSTALL=1 uv run --frozen coverage run -m pytest -q --ignore=tests/test_observation_performance.py`; `<component python> -m coverage run --append -m pytest -q tests/test_graphify_worker_native.py`; `uv run --frozen coverage report --format=total` | main lane **2 failed, 1870 passed, 9 skipped, 587 subtests passed in 436.4 s** (same two residuals); component lane **36 passed**; total **78**, exit 0 against the `fail_under = 78` floor | this record |
| Public artifact path scan | `uv run --frozen python scripts/check_public_artifacts.py --root .` | exit 0, 0 findings | this record |
| Documentation check | `uv run --frozen python scripts/check_documentation.py` | exit 0 | this record |
| Wheel & sdist build | `uv build` | sdist + wheel built | this record |
| Ruff lint / format | `uv run --frozen ruff check src/aether_agents tests scripts`; `ruff format --check …` | pass; 172 files formatted | this record |
| Type check | `uv run --frozen mypy src/aether_agents` | 0 issues, 67 files | this record |
| Whitespace / conflict markers | `git diff --check 00715d23..HEAD` | exit 0 | this record |
| New skips introduced | `pytest --collect-only` count + no `pytest.skip` in the new nodes | none | `tests/test_tui_projections.py`, `tests/test_release_bundle.py` |
| Fresh `--no-local` clone of the unit branch (deterministic CI checkout shape) | `git clone --no-local --branch <unit branch>`; `git cat-file -t aed6591a…`; `build_tui_in_disposable_workspace(<clone>, aed6591a…, …)`; `uv run --frozen python -m pytest -q tests/test_tui_projections.py tests/test_lifecycle_projections.py tests/test_release_bundle.py` inside the clone | pin **absent** (`cat-file` exit 128); build **refused**: `failed to extract git archive of commit aed6591a…`; a nested non-repository refuses with `git exit 128`; the focused lane on that clone is **79 passed in 14.9 s** — the lane does not depend on this host's object database | this record |

## Live evidence (provisioned maintained fork, disposable workspace)

| Check | Measurement |
| --- | --- |
| Exact-commit archive build from the fork checkout | commit `aed6591a69f453a1867b73628603e7b53ba40ffc`; `source=git-archive`; Node `v22.23.2`; npm `10.9.8`; `dist/entry.js` SHA-256 `f56f6225d9124376eedec1834d372c76a33292aedc41021cc13d6c3b32a05643` in 8.4 s |
| Build from the materialized exact-commit tree (no `.git`) | same digest `f56f6225…`; `source=materialized-tree`; 7.7 s; digest equality with the archive build |
| Real PTY launch of the release-owned asset | `node <release-tui>/dist/entry.js` with `HERMES_TUI_DIR` set and `npm` replaced by a failing sentinel: TUI rendered (ink alternate screen) and was terminated after the 20 s probe window (`exit_code 143`); `npm_invoked=false`; locked-source inventory **9,377 entries identical before/after**; no `node_modules`, no `ui-tui/dist` in the locked source |

The binding repair changed no staged byte: both source shapes still produce the digest
recorded in the earlier rounds of this unit.

## Full-runner residuals (both outside this unit)

The same two nodes fail in the coverage lane.

| Failing node | Observed | Why it is not this unit |
| --- | --- | --- |
| `tests/test_aether_tui_launcher.py::MorfeoTuiLauncherTests::test_versioned_launcher_contains_no_machine_specific_home` | `AssertionError: 509 != 493` — the checkout's `scripts/aether_tui.py` is `0o775` on disk while the index records `100755`; `git status` reports no change for the path | `scripts/aether_tui.py` is out of this unit's writable surface and unmodified in this diff; the residue predates this round |
| `tests/test_public_artifacts.py::test_canonical_base_manifest_matches_tracked_non_specs_files` | the `policy.yml` manifest has 422 entries, tracked non-`specs/` files are 425: missing `.aether/objective-contracts/oc_ff82ba151cdf3861/v1.md`, `…/v2.md`, `tests/test_tui_projections.py` | decision 11 makes `policy.yml` registration LG-DOCS work; this unit records `tests/test_tui_projections.py` in the handoff instead of editing the workflow |

## Probe hygiene (reported because it changed shared state, and now prevented)

Reproducing the defect the way the review did — exporting `GIT_DIR` process-wide — made
the *probe's own* fixture Git commands write into this checkout: a throwaway
`ONLY-FORK.txt` commit appeared on the unit branch, the worktree index was replaced by
that commit's tree, and repo-local `user.name` / `user.email` were overwritten. It was
repaired immediately and verified: `git reset --hard` to the candidate revision, the two
repo-local `user.*` entries removed (leaving the operator's global identity as the only
one), `git status` clean, `git log` at the candidate, no ref/tag/stash/worktree change,
and only an unreachable garbage object left in the object database. The fixtures now
cannot repeat this: every Git command in the test helpers and in both probes runs with
`GIT_*` removed from its environment, and the new nodes set the ambient trap with
`monkeypatch` after their fixtures are committed.

## Non-claims

This unit does not author the packaged CLI module (LG-CLI), update `VERSION` or
documentation identity (LG-DOCS), register the new test path in `policy.yml` (LG-DOCS),
or activate the live host installation, mutate issues, tag or publish (LG-CLOSE /
Supervisor). The `specs/` record is unit evidence, not an aggregate release conclusion;
`release_impact` / `release_action` / `release_channel` belong to LG-CLOSE.
