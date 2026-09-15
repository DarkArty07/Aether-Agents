# LC-INT Integration Evidence — Aether 1.0.0-rc.1

**Unit:** LC-INT (task `t_7326adb7`, Supervisor-owned integration lane)
**Objective Contract:** `oc_3397f9f05d780f8e@v1` (SHA-256 `4d4c7650bf8ea93fc7cffe3d87f7f974e172d66cefcf6a74a2d83051568a4879`)
**Integration base:** `410c172ae69ffa87f6e32960ae4aef3b8d6598f0`
**Integration branch:** `aether-agents-2/lc-int-integration`
**Consumed breakdown:** `specs/001-aether-v1-productization/tasks.md` at `61124bc1dea787fbc5408fcc7f7b4f654f342e78`
**Status of this record:** pre-publication facts are complete; the publication section (§6) is
completed after the tag and prerelease exist, because a commit cannot contain the identity of
the tag that points at it. See §6 for the recording rule.

---

## 1. Reviewed units consumed (each independently reviewed on its own card)

| Unit | Card | Reviewed tip | Deliverable |
| --- | --- | --- | --- |
| Decomposition root | `t_a3b2d549` | `4cb32353a9` | Supervisor breakdown at `61124bc1` |
| LC-DOCS | `t_c0ff1794` | `35fa6e67c7` | design/docs/registry reconciliation |
| LC-BLOCK | `t_8a02a727` | `d87140b5ce` | blockers #437/#438 closeout artifacts |
| LC-FORK | `t_926a1913` | `5037653f06` | maintained-fork candidate |
| LC-RUNTIME | `t_359beef2` | `a2fa63660f` | schema-v4 lock, `maintained_fork`, `aether update --local`, rollback |
| LC-RELTOOL | `t_69a9eae4` | `2bd4dc0f49` | bundle builder, lock validation, publication verification |
| LC-PORT420 | `t_56d86e11` | `6a3a9dab05` (Aether side) | HLP-420 fork delivery evidence |
| LC-FIX-INIT | `t_0ba61e88` | `35fb9bd9f5` | `aether init` marker records the release display identity |
| LC-FIX-GOLDEN | `t_577d3184` | `9b46e68897` | observation golden regenerated at the RC identity |

No unit was consumed unreviewed. `LC-FIX-INIT` and `LC-FIX-GOLDEN` were raised by the
merged-tree gate and returned as implementation work with their own review verdicts.

## 2. Merge commits and ancestry

Nine merges, each preserving the unit's own commits (no squash, amend, rebase or history
rewrite). First-parent order from the base:

```
23b2d80  Merge root decomposition
a28fed0  Merge LC-DOCS
e90c201  Merge LC-BLOCK
7fba0b2  Merge LC-FORK
feea171  Merge LC-RUNTIME
b8f00be  Merge LC-RELTOOL
0920d40  Merge LC-PORT420
ddd830a  Merge LC-FIX-INIT
f651625  Merge LC-FIX-GOLDEN
```

Every reviewed tip above is verified as an ancestor of the integration tip. `origin/main`
(`0a8b25b354b95c7a4c026c42080bb627a7b6876a`) is already an ancestor, so no `origin/main`
merge was required.

## 3. Maintained-fork integration (companion repository)

- Fork `DarkArty07/aether-hermes`, branch `aether-main`, accepted merged commit
  `9031bae0e8b0ab40c4fd7ba50c644972ff512611`.
- PRs [#12](https://github.com/DarkArty07/aether-hermes/pull/12) (HLP-425 review-flow
  continuity) and [#13](https://github.com/DarkArty07/aether-hermes/pull/13) (HLP-420
  Responses terminal fidelity) merged green; no history rewrite, no force push.
- The fork is **tagless by design**; the release lock binds repository, branch, commit,
  materialized source-tree digest, artifacts and provenance instead of a tag.
- Canonical materialized source-tree digest (`lifecycle._tree_sha256` over the
  materialized source, EOL-normalized, DFS order):
  `495e5f4b8d9ecc293b5ea956ef693d8bc0cd78b3f6ac03475a6cfefb4b40ef31`.
- Hermes distribution identity preserved (`hermes-agent 0.20.1`); `uv.lock` untouched.

## 4. Bounded integration repairs (all committed on the integration branch)

| Commit | Repair | Basis |
| --- | --- | --- |
| `ac1a5ba` | policy manifest lines for both branches' new non-`specs/` files, plus `scripts/release_bundle.py` in the CI lint scope | exact recorded lines; manifest then exactly matches tracked files (406 = 406) |
| `11b2f45` | remove a machine-specific checkout path from LC-PORT420 evidence | reference/path correction |
| `e0c1b78` | pin `FORK_COMMIT` to the accepted merged fork revision | shared decision 4 |
| `85549ae` | lock fixture validated against the shipped v4 schema | integration-bound: LC-RELTOOL's fixture assumed schema v3 while LC-RUNTIME delivered v4; only the merge has both |
| `49b28a1` | restore the product module cache after the release-tool module's `sys.modules` purge | integration-bound: the single-process canonical runner plus a tool fixture that purges product modules |
| `5a4fb00` | format the module-cache fixture | my own earlier commit's over-long line; CI-scope `ruff format --check` |
| `2cb7485` | regenerate reconciliation evidence at the merged fork tip | accepted generator, `--check` mode current |
| `060c56d` | correct the `DESIGN.md` link to the observation spec | reference/path correction (LC-DOCS introduced an `../` prefix from the repository root) |

`060c56d` attribution, stated precisely: the broken link was **not** reported by the failing
GitHub run `34958008452`. That run's `policy` job stopped at its first failing step, so the
`Validate accepted R0 design baseline` step was **skipped** there. The finding came from
running that step's extracted script locally as part of this lane's pre-flight, and the
objective's own commit `dd91444` (LC-DOCS) is its origin — `origin/main` referenced the
donor directory without the `spec.md` suffix. After the correction the step's own checker
reports 0 broken relative links across all 321 tracked markdown files.

### 4.1 Withdrawn candidate (not accepted by this lane)

`5cf90b5` proposed extending the `policy` job's `VERSION` assertion to accept the
contract-decided RC identity. The design steward correctly classified it as a release-policy
guard **behavior** change rather than one of this lane's enumerated direct repairs, and
contract stop condition 60 requires a cleanly diagnosed objective-caused CI failure to be
repaired through normal bounded rework. It was therefore **withdrawn** by revert `04e5192`
and preserved in history as candidate/evidence only. The correction is owned by focused unit
**LC-FIX-GUARD** (card `t_22bc9005`) together with its positive/negative identity controls,
and tracked as issue [#443](https://github.com/DarkArty07/Aether-Agents/issues/443).

Consequence, recorded deliberately: with the candidate withdrawn the required `policy` job is
red at `04e5192`. That is the honest state while the guard correction has no independent
implementation/review lane, and it is why this lane does not merge or tag until LC-FIX-GUARD
is reviewed.

## 5. Gates measured at the merged tree

Measured at `060c56d` (all seven units plus both repaired units, and the two gate repairs
above) on a quiet machine, unless stated otherwise:

| Gate | Result |
| --- | --- |
| Full canonical suite (`scripts/run_tests.py`) | **1753 passed, 70 skipped, 0 failed** (571.66 s, exit 0) |
| Reconciliation `--check` at the merged fork revision | **current** — 27 present, 0 partial, 0 absent, 2 unverified (`HLP-246`, `HLP-247`), `refusing: []` |
| `scripts/check_documentation.py` | passed |
| `scripts/check_public_artifacts.py` | passed |
| `policy` job steps 1–5, run locally from the workflow's own `run:` blocks | exit 0 each (with the guard correction in place; see §4.1 for the current red state) |
| CI coverage lane, **in CI** (PR #442, run `34959238413`, head `be9f4ac`) | **RED in all three jobs** at step `Enforce integrated coverage floor` — see §5.2. 3.11/3.13: 12 failed, 1785 passed, 23 skipped, 587 subtests; 3.12: 13 failed, 1784 passed, 23 skipped. Pytest exits non-zero under `set -euo pipefail`, so the step aborts **before** the Graphify append and `coverage report`; the floor total was not produced in CI |
| CI coverage lane, same commands re-run locally | 1810 passed, 9 skipped, **1 failed**; `coverage report --format=total` = **78** against the committed floor `fail_under = 78` (`pyproject.toml:89`, `precision = 0`) — **diagnostic only, not representative of CI**: the operator machine resolves the offline build requirement from a warm `uv` cache, so the eleven editable-tooling nodes that fail in CI pass here |
| Graphify native lane in the isolated component (local) | 36 passed |
| Contract's named `pytest --cov=aether_agents --cov-report=term-missing` | **not usable as written in this environment** — see §5.1 |

### 5.1 The two coverage commands, and why only one is authoritative here

The coverage floor is satisfied: the CI-form lane measured a total of **78** with the
committed floor at `fail_under = 78`. The contract's other named coverage command,
`uv run --frozen pytest -q --cov=aether_agents --cov-report=term-missing`, cannot be run
bare in this environment, for two measured reasons:

1. Without the repository runner's exact-Hermes `PYTHONPATH`, collection fails outright:
   `ModuleNotFoundError: No module named 'hermes_cli'` (1 error, 1 skipped, 6.4 s). This is
   exactly what `CONTRIBUTING.md` warns about when it says to use the repository runner for
   exact-Hermes integration coverage.
2. With that `PYTHONPATH` supplied, the run completes 1747 passed / 11 failed and then raises
   a coverage `INTERNALERROR`: `DataError: Can't combine statement coverage data with branch
   data`. Mechanism, measured: the development environment ships an auto-start hook
   (`.venv/.../a1_coverage.pth`) that starts coverage in subprocesses when
   `COVERAGE_PROCESS_START`/`COVERAGE_PROCESS_CONFIG` is set, which pytest-cov's `--cov` does
   set; a child whose working directory is outside the repository (test `tmp_path` roots,
   which the suite uses heavily) does not find `pyproject.toml`, so it resolves
   `branch = False` and writes statement-only parallel data
   (`branch` is `True` from the repository root, `False` from `/tmp` — verified directly).
   pytest-cov's `finish()` then combines statement-only with branch-enabled data and fails.

This is a pre-existing repository/tooling interaction, not an objective-caused defect: it
requires neither this branch's changes nor the RC identity, and CI deliberately uses the
`coverage run` form instead. It is recorded here rather than absorbed. Its consequence for this
lane's evidence is that the contract's `--cov` command produced no usable floor measurement, and
the CI-form command produced a floor measurement only on the operator machine — so neither is
offered as the coverage gate's result, and the gate's real state is §5.2.

### 5.2 Integrated CI state on PR #442 (authoritative for the gate position)

Run `34959238413` (head `be9f4ac`, the current PR tip) is **red in all six non-`pull-request-target`
jobs**: the three `policy` jobs because the withdrawn `VERSION` guard candidate is not in the
tree (§4.1), and the three `observation-qualification` jobs because of the coverage lane below.

Failure classes inside the coverage step, verified from the run's own log:

| Class | Nodes | Evidence |
| --- | --- | --- |
| Offline editable tooling cannot resolve its build requirement | 11 nodes in `tests/test_hermes_editable.py` (`test_red_green_editable_reconciliation`, `test_offline_mode_reconciliation`, `test_reconcile_raise_on_failure_false`, …) | `AssertionError: Initial editable install failed: … venv1` and `uv build --wheel failed: Building wheel...` |
| Exact-checkout resolver points at an absent cache directory | `tests/test_same_card_phase_predicates.py::test_initial_review_requires_an_independent_reviewer` | `FileNotFoundError` for the runner's absent cache directory (`…/.cache/aether-agents`) |
| Checkpoint authority unverified — **3.12 only** | `tests/test_observation_journal_storage.py::test_checkpoint_sink_derives_review_authority_from_durable_native_assignment` | `CheckpointResult(accepted=False, reason_code='CHECKPOINT_AUTHORITY_UNVERIFIED')` |

**Attribution, measured rather than assumed.** The first two classes are **pre-existing and not
objective-caused**: `origin/main` run `34825309185` fails the same coverage step with the same
eleven editable nodes and the same predicate node, and neither file (`tests/test_hermes_editable.py`,
`tests/test_same_card_phase_predicates.py`) appears in this objective's diff. They are tracked by
issue [#428](https://github.com/DarkArty07/Aether-Agents/issues/428). The third is **new relative to
`main`** (main's 3.12 job has exactly the twelve), its file is likewise untouched by this objective,
and the node **passes locally** in this tree — so it is an environment/order-sensitive symptom that
needs its own classification and is not assumed to be this objective's defect.

**Gate position, stated without softening.** The required checks are `policy (3.11/3.12/3.13)` and
`pull-request-target`; the observed-but-red `observation-qualification` matrix is *not* a required
check and is red on `origin/main` as well. It is nevertheless inside this contract's gates —
AC-10 names the coverage floor and stop condition 60 treats unresolved test failures as a stop —
so this lane does **not** merge, tag or describe the integrated gates as green while it is red.
Local measurements (§5) are recorded as diagnostics, not as substitutes: the `coverage = 78` total
was produced on the operator machine, in an environment whose warm `uv` cache masks the eleven CI
failures, and CI never reaches `coverage report` at all. Neither number is offered as the gate's
result. The directed next step is canonical rework of #428 (and separate classification of the
3.12-only symptom) with an independent review lane, which is why publication is deferred.

## 6. Publication (completed after the tag exists)

To be recorded here once created: PR number, run IDs, required-check results, the merged
`main` commit, the annotated tag object id and its dereferenced commit, the release flags,
every attached artifact with its local and downloaded SHA-256, and the fresh
artifact-installed CLI handshake. The qualified release identity is package `1.0.0rc1`,
tag/prerelease `v1.0.0-rc.1`, `prerelease = true`, not draft; no PyPI publication and no
stable `1.0.0` claim.

### Publication path notes

- `.github/workflows/release.yml` performs the build and the create/reconcile from the
  tagged commit; `FORK_COMMIT` is pinned to the accepted fork revision (§3).
- The workflow's create path attaches the tool's verified eight-member set, checksum file
  included; the reconcile path re-verifies published names and digests or fails closed
  (`gh release edit` accepts no file arguments, so it can never attach bytes).
- `gh release upload` and `--clobber` are not used anywhere.
