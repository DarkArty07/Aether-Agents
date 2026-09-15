# LC-FIX-COVLANE Evidence — CI coverage lane repaired at its real root cause (#428)

**Unit:** LC-FIX-COVLANE (task `t_51e95a1d`, Implementer; same-card review pending)
**Objective Contract:** `oc_3397f9f05d780f8e@v1`
**Canonical breakdown:** `specs/001-aether-v1-productization/tasks.md` (read-only for this unit)
**Branch:** `aether-agents-2/t_51e95a1d-lc-fix-covlane-make-the-ci-coverage-lane`
**Pre-change tip:** `e2738bd`
**Delivered change:** `tests/test_hermes_editable.py`, `tests/test_same_card_phase_predicates.py`,
and this record (`specs/001-aether-v1-productization/evidence/LC-FIX-COVLANE.md`)
(no workflow change — see §8)
**Status of this record:** unit-local implementation evidence. It is not an aggregate release
conclusion, not a publication claim, and not independent review.

---

## 1. Primary-source reproduction

The red step was read from the run itself, not from a summary.

| Fact | Value |
| --- | --- |
| Run / head | `34959238413` / `be9f4ac` |
| Step | `observation-qualification` → `Enforce integrated coverage floor` |
| Jobs | 3.11 `104348599829`, 3.12 `104348599838`, 3.13 `104348600266` |
| 3.11 / 3.13 summary | `12 failed, 1785 passed, 23 skipped, 587 subtests` |
| 3.12 summary | `13 failed, 1784 passed, 23 skipped, 587 subtests` |
| Effect | pytest's non-zero exit aborts the `set -euo pipefail` step before the Graphify append and before `coverage report`, so the lane produced **no floor measurement at all** |

Attribution was re-measured independently from the primary source: `origin/main` run
`34825309185` fails the same step in all three jobs (`103915960791`, `103915960745`,
`103915960914`) with exactly the twelve pre-existing failures (classes A and B); the
class C node does not appear in any of them.

## 2. Class A — the offline editable oracle could not resolve its build requirement

### 2.1 Measured failure at the pre-change tip

The disposable fixture fork declared an **external** build requirement
(`[build-system] requires = ["setuptools>=61.0"]`). Under `--offline` that requirement can
only be satisfied from a populated uv cache, so a clean runner fails and a developer
machine passes. Driven into failure locally with a disposable cold cache:

```
$ UV_CACHE_DIR=<fresh-empty-dir> uv run --frozen pytest tests/test_hermes_editable.py -q
11 failed, 4 passed
```

The message matches the CI class exactly (`/tmp/pytest-of-<user>/...` shortened here):

```
AssertionError: Initial editable install failed: Using Python 3.13.15 environment at: <venv>
├─▶ Failed to resolve requirements from `build-system.requires`
├─▶ No solution found when resolving: `setuptools>=61.0`
╰─▶ Because setuptools was not found in the cache and you require setuptools>=61.0, ...
hint: Packages were unavailable because the network was disabled.
```

### 2.2 Root cause

The oracle measured **cache warmth**, not offline behaviour. The fixture's own build
requirement had to be downloaded or already cached, so the "offline" editable build was only
ever offline-capable on a machine whose cache happened to contain `setuptools` — a developer
machine — while a clean runner could not build the fixture at all. The product's
reconciliation code was not at fault; the fixture's declared external build requirement was.

### 2.3 Repair

The disposable fork is now self-contained: it **vendors its own PEP 517/660 backend**
(`_DISPOSABLE_BACKEND_SOURCE` in `tests/test_hermes_editable.py`, reached through
`backend-path`, with `build-system.requires = []`), so both the offline editable build and
`uv build --wheel --offline` need nothing from an index or a cache. No network access was
added to the offline path and no assertion was weakened, skipped or deleted.

The fixture's *observable* install surface is preserved, so every existing assertion still
measures the same behaviour:

| Observable | Produced by the fixture backend |
| --- | --- |
| `__editable__.hermes_agent-0.20.4.pth` | PEP 660 mapping file |
| `__editable___hermes_agent_0_20_4_finder.py` | real meta path finder resolving **only** the declared `py-modules` inventory to source files |
| `hermes_agent-0.20.4.dist-info` (`METADATA`, `WHEEL`, `RECORD`) | wheel metadata (uv adds `direct_url.json` with `dir_info.editable: true`) |
| `hermes_agent.egg-info` | the legacy build artifact the reconciler removes as debris (keeps `remove_editable_build_debris` exercised) |
| `[tool.setuptools] py-modules` | unchanged single inventory source for the fixture **and** the product's `check_fork_packaging_inventory` |

Two fixture properties are load-bearing and pinned by the rollback nodes:
the finder is built from the inventory declared **at build time** (so a module added to
source but not yet reconciled stays unmapped, preserving the RED/GREEN semantics), and the
editable wheel ships **no module copies** (otherwise a rolled-back reconciliation would keep
resolving the withdrawn module from site-packages instead of reporting it unmapped).

### 2.4 Green after the repair

| Condition | Result |
| --- | --- |
| `UV_CACHE_DIR=<cold>` run 1/2/3 | `15 passed` / `15 passed` / `15 passed` |
| ambient (warm) uv cache | `15 passed` |
| pre-change, same cold condition | `11 failed, 4 passed` |

## 3. Class B — the exact-checkout resolver pointed at an absent cache directory

### 3.1 Measured failure at the pre-change tip

The lane provisions exactly one verified checkout (`${RUNNER_TEMP}/hermes-exact`) and exposes
it on `PYTHONPATH` — it populates no cache entry and sets no checkout identity for the
coverage step. `_resolve_baseline_checkout()` consulted only
`AETHER_EXACT_HERMES_CHECKOUT` and the canonical cache entry, so it failed before anything
could be verified. Reproduced locally by removing both ambient sources:

```
$ env -u AETHER_EXACT_HERMES_CHECKOUT XDG_CACHE_HOME=<fresh-empty-dir> \
    PYTHONPATH=<exact-checkout> uv run --frozen pytest \
    tests/test_same_card_phase_predicates.py::test_initial_review_requires_an_independent_reviewer -q
E   FileNotFoundError: [Errno 2] No such file or directory: '<fresh-empty-dir>/aether-agents'
1 failed
```

### 3.2 Root cause and repair

The resolver diverged from the convention the rest of the suite already uses for the
lane-provided checkout (`importlib.util.find_spec("hermes_cli")` → repository root, as in
`tests/test_observation_lifecycle.py` and `tests/test_observation_qualification.py`), while
this node can only import `hermes_cli` from that same checkout.

Repair keeps the explicit override first and the canonical cache entry as the local default,
then falls back to the checkout the suite is actually running against, and keeps the cache
path as the terminal fallback so an unresolvable environment still fails loudly:

```
explicit AETHER_EXACT_HERMES_CHECKOUT → existing cache entry → loaded hermes_cli checkout → cache path
```

`verify_clean_checkout` still authenticates tag object, commit and cleanliness on every
candidate, so the node cannot pass against a wrong checkout.

### 3.3 Green, and the negative control

| Check | Result |
| --- | --- |
| CI-shaped environment (no cache entry, no identity, checkout only on `PYTHONPATH`) | `tests/test_same_card_phase_predicates.py` → `11 passed` (previously `1 failed`) |
| Negative control: `AETHER_EXACT_HERMES_CHECKOUT` pointed at a repository at the wrong commit | `1 failed` with `IntegrityError: Hermes checkout commit mismatch: expected e624e9fd…, got e2738bd…` — loud failure, never a skip |

## 4. Lane end-to-end (the floor is measured again)

The step's own sequence was run locally with the lane's environment:
`PYTHONPATH=<exact-checkout>`, `COVERAGE_FILE`, `AETHER_GRAPHIFY_PYTHON` (isolated
hash-locked component), `AETHER_TEST_COMPONENT_INSTALL=1`, a fresh `XDG_CACHE_HOME` and
`AETHER_EXACT_HERMES_CHECKOUT` unset — i.e. the CI checkout/cache shape.

**As delivered on this branch** the sequence reproduces the CI behaviour exactly: the step
aborts at pytest's non-zero exit and never reaches `coverage report`. The two failures are
**not** attributable to this unit — both are the single cross-unit operator-path finding
described in §9 (§4 of the lane log: `2 failed, 1803 passed, 15 skipped`).

**With that single cross-unit line repaired** (measured in a throwaway checkout of the same
tree, applied only there, never in this unit's diff):

| Step | Result |
| --- | --- |
| `coverage run -m pytest -q --ignore=tests/test_observation_performance.py` | `1802 passed, 18 skipped, 587 subtests passed` — **0 failed** |
| `$AETHER_GRAPHIFY_PYTHON -m coverage run --append -m pytest -q tests/test_graphify_worker_native.py` | `36 passed` |
| `coverage report --format=total` | **78** (`precision=0`; exact `78.09`) against the committed floor `fail_under = 78`; step exit `0` |

The margin is +0.09 points: the floor is met, not raised or lowered, and `pyproject.toml`
was not touched.

## 5. Observation manifest preserved

Neither delivered file is in the observation `CORE_TESTS` set, and no observation module was
touched. Re-measured directly anyway (`scripts/qualify_observation.py::_collection_manifest`
over `CORE_TESTS`): `466` nodes and digest
`b9879d323fa5c36bedee667008324f159885f054782f3bba1fa310797b260ee4` — unchanged, and the
pinned node `tests/test_observation_qualification.py::test_locked_core_manifest_matches_the_actual_collected_nodes` passes.

## 6. Class C — classified, escalated, not absorbed

**Not this unit's root cause and not reproducible locally; no fix attempted.**

Measured CI facts: the node fails only in the 3.12 job of run `34959238413`
(`test_observation_journal_storage.py::test_checkpoint_sink_derives_review_authority_from_durable_native_assignment`);
it fails at `tests/test_observation_journal_storage.py:1206` (`assert result.accepted` for the
legitimate second `review_approved`), i.e. **after** the forged attempt was already rejected
correctly with `CHECKPOINT_REFERENCE_UNKNOWN`; the same node passes in the 3.11 and 3.13 jobs
of that run and in all three jobs of the `origin/main` run. The 3.12 job was markedly slower
than its siblings in that run (suite times 396.84 s / 616.20 s / 432.66 s for 3.11 / 3.12 / 3.13),
and slower still than the same job on `origin/main` (541.41 s).

Mechanism (read from the source): a `review.approved` checkpoint must derive its principal
chain from durable evidence — the classification event, the exact descendant
`review.requested` event, and the collector's **live** durable snapshot of the active segment
(`src/aether_agents/observation/checkpoint.py:600-708`, `src/aether_agents/observation/capture/journal.py:756`).
Every unavailability path fails closed: a bounded snapshot-lock timeout, a missing flush
boundary, an inode/directory-route mismatch or an incomplete line all return `None`, which the
sink reports as `CHECKPOINT_AUTHORITY_UNVERIFIED`. The node therefore asserts deterministic
success on a path whose inputs are availability- and timing-sensitive.

Local evidence (all in the CI checkout/cache shape):

| Local run | Class C node |
| --- | --- |
| Isolated, CPython 3.12.13, 5 repetitions | `1 passed` × 5 |
| Whole suite, CPython 3.12.13 (`1802 passed, 18 skipped, 0 failed` in 418.54 s) | absent from the failure list |
| Whole suite, 3.13, as delivered on this branch (§4) | absent from the two-failure list |
| Whole suite, 3.13, with the cross-unit line repaired (§4) | absent from the failure list |

Classes A and B cannot explain it — the delivered diff touches no observation, journal or
checkpoint code, and the failing path is independent of the editable fixture.

Disposition: escalated for the owning lane with this evidence. A guessed repair (relaxing the
fail-closed path, or the assertion) is exactly what this unit was instructed not to do.

## 7. Static and preservation gates

| Gate | Result |
| --- | --- |
| `ruff check tests/test_hermes_editable.py tests/test_same_card_phase_predicates.py` | `All checks passed!` |
| `ruff format --check` on both files | `2 files already formatted` |
| `git diff --check` | clean |
| `uv run --frozen mypy src/aether_agents` | `Success: no issues found in 67 source files` |
| `uv run --frozen python scripts/check_documentation.py` | `documentation validation passed` |
| `uv build` | wheel and sdist built (`aether_agents-1.0.0rc1`) |
| `scripts/check_public_artifacts.py --root . --artifact <whl> --artifact <sdist>` | exits `1` on the pre-existing cross-unit finding in §9; no finding for any file this unit touched |
| Fresh environment at the delivered commit | `importlib.metadata.version("aether-agents")` → `1.0.0rc1` |

## 8. Audited but not changed

- **`.github/workflows/policy.yml` coverage-lane environment** — writable for this unit, and
  deliberately left untouched. Exporting `AETHER_EXACT_HERMES_CHECKOUT` in that step would
  also change the behaviour of unrelated nodes: measured on the `hermes_exact` selection, it
  flips 6 nodes from skip to run (`12 passed, 8 skipped` → `18 passed, 2 skipped`). They all
  passed locally, but that expands the coverage lane's node set beyond this unit's mandate and
  adds unverifiable-on-CI surface, so the narrower resolver repair was chosen and this
  alternative is recorded here for the owning lane.
- **`src/aether_agents/**`** — untouched. No product defect was proven: the reconciliation
  code refuses non-editable targets, rolls back and preserves source bytes exactly as its
  oracles require; only the test fixture's buildability was at fault.
- **`tests/test_release_bundle.py`, `tests/test_public_artifacts.py`** — untouched; their two
  node failures are entirely caused by the cross-unit finding in §9.
- **`tests/test_telegram_monitor_cli_plugin.py::_exact_checkout`** — the same latent
  cache-path-only resolution as class B, but it skips instead of failing, so it is not part of
  this failure and stays outside this unit's writable boundary.

## 9. Cross-unit finding (flagged, not repaired here)

`specs/001-aether-v1-productization/evidence/LC-INT.md` contains an absolute runner-home path
(the runner's `${HOME}/.cache/aether-agents` checkout location, written with the literal
runner home directory), introduced by commit `e2738bd` — i.e. **after** the CI
head `be9f4ac`, which is why the lanes that ran on that head never saw it. Measured effect on
this branch:

- `scripts/check_public_artifacts.py` exits `1` with exactly one finding:
  `specs/001-aether-v1-productization/evidence/LC-INT.md: absolute-user-home`
  (1 of 658 tracked files; no other finding).
- That single finding fails `tests/test_public_artifacts.py::test_tracked_public_surface_contains_no_operator_paths`
  and `tests/test_release_bundle.py::test_scan_bundle_reviews_upstream_fork_bytes_without_vetoing`
  (`BundleError: private-path-scan`), which is what stops the coverage step from reaching
  `coverage report` in §4, and it would also stop the `policy` job's
  `Reject operator-specific paths in public artifacts` step.

The record belongs to the LC-INT lane (breakdown rule 10: one record per unit; and
`specs/001-aether-v1-productization/evidence/**` other than this unit's own record is
preserved), so it was reported to that card with the exact location and the minimal wording
change instead of being edited here. Fixing that one line makes the lane sequence green
end-to-end, as measured in §4.

## 10. Not claimed by this record

- No publication, push, tag, release or aggregate `release_impact` / `release_action` /
  `release_channel` conclusion (Supervisor-owned).
- No claim that the CI lane is green on a runner: the CI-shaped conditions (cold uv cache;
  absent cache entry and unset identity) were reproduced locally, and the end-to-end sequence
  was measured locally, but no push or workflow run is part of this record.
- No acceptance of class C: it is classified and escalated, not fixed and not absorbed.
