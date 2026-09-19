# RC3-IDENTITY — the rc.3 release identity and its coupled oracles

**Unit.** RC3-IDENTITY (Implementer) of the Aether `1.0.0-rc.3` objective.

**Authority.** Objective Contract `oc_a179da8d654aec8b@v1`, SHA-256
`0f045ab552c277a88c19c07b3e695b313c0f0a3a14f8bcd632700f8c1b68a7b6`, plus the
Supervisor-owned breakdown `specs/001-aether-v1-productization/tasks-rc3.md` (unit entry
RC3-IDENTITY). The contract's in-scope item 1, deliverable 1, AC-1, and the source-lane
half of the testing standard govern this unit.

**Base.** `ad85b729746a1eb756f96f138894d527122ab2fd` — the contract authorization commit on
top of clean pre-contract base `78984ebf9468892e9569ecbdead1977d6a2134ee` (`origin/main` at
contract finalization). The delivered change is one local commit on the unit branch; the branch
name embeds the execution-card identity and is therefore not published here. The owning card
handoff names the exact branch and commit.

**Effects.** Local and reversible only: file edits in `<aether-unit-worktree>`, one local
commit, one wheel built into `<scratch-root>`, and read-only test/scan runs. No push, PR,
merge, tag, release, asset write, package-index publication, workflow dispatch or
deployment, service restart or activation, issue mutation, or credentials use. The rc.1
and rc.2 releases were read and never written.

**Status of this record.** Unit-local implementation evidence. It is not an aggregate
release conclusion, not a publication or activation claim, and not independent review. Only
the terminal lane aggregates the three release conclusions; `RC3-INTEGRATE-TAG` and
`RC3-ACTIVATE-CLOSEOUT` own the integration, preflight, tag creation, activation, canary,
rollback, and closeout measurements listed in §7 as not taken here.

## 0. Reading conventions

- Every measurement states the command that produced it and the observed result.
- **Sanitization.** The unit worktree appears as `<aether-unit-worktree>`, scratch roots as
  `<scratch-root>`, the execution card/branch as "the unit branch". Commit ids, tag/release
  names, SHA-256 digests and public URLs are published verbatim: the measurement is
  meaningless without them.
- `git status --porcelain` and `git diff --numstat` below reflect the pre-commit state of the
  exact delivered set; this record is added by the same commit and therefore appears as one
  new tracked path in it.

## 1. What changed

```console
$ git status --porcelain
 M .github/workflows/release.yml
 M AGENTS.md
 M CHANGELOG.md
 M README.md
 M VERSION
 M tests/fixtures/observation/complete-summary.json
 M tests/test_public_artifacts.py
 M tests/test_release_bundle.py

$ git diff --numstat
3	3	.github/workflows/release.yml
1	1	AGENTS.md
26	0	CHANGELOG.md
1	1	README.md
1	1	VERSION
3	3	tests/fixtures/observation/complete-summary.json
19	5	tests/test_public_artifacts.py
2	2	tests/test_release_bundle.py
```

| Path | Change | sha256 (delivered) |
| --- | --- | --- |
| `VERSION` | `1.0.0rc2` → `1.0.0rc3` (the single product-version source) | `50dfda64de95d7ac712722f94676b094d22449beabe67cea7359e43d6dcb339b` |
| `README.md` | status paragraph (line 5) states local-only `1.0.0rc3` identity, non-claims, and predecessor dispositions | `a59ff58cbbce54fcee44b437008bc9fba8fd2540d7e5b1ae9d2705021948a96b` |
| `CHANGELOG.md` | new `1.0.0rc3` entry above rc.2 entry (26 insertions, 0 deletions: rc.2/rc.1 entries byte-unchanged) | `2d88308a817d32705644c006c71bcc8d33409e3814f294d46f10ba0f768b6d2e` |
| `AGENTS.md` | "currently authorized bounded objective" paragraph reconciled with `oc_a179da8d654aec8b@v1` and rc.3 identity | `d75e1d409f9e9f96dc31f925f585566209f3ee1204f16ca37d6a030dc4498ba1` |
| `.github/workflows/release.yml` | comment block above `FORK_COMMIT` reconciled with `oc_a179da8d654aec8b@v1`; pin unchanged at `aed6591a…` | `ea771196cb9ab2153a2281d2e8479689971829c47647a95c0297e3cb2fc91d69` |
| `tests/test_public_artifacts.py` | README status oracle updated with truthfulness guard; `ACCEPTED_PACKAGE_IDENTITIES` updated | `0692626edde2a2a80d554846f687422c3b902815ddfe51c317511fb7e8e823f3` |
| `tests/test_release_bundle.py` | `VERSION` release identity oracle updated to expect `1.0.0rc3` / `v1.0.0-rc.3` | `c33b5068e6cf77bb814f6d697389e75f09bb45992baa9c809a6dc91c94ef76f1` |
| `tests/fixtures/observation/complete-summary.json` | reviewed golden summary regenerated; exactly 3 version-derived lines moved | `6192dafb09480d574b37af880e59a7526fdb051b54826f55d5b244356c1823c6` |

Content notes:

- `VERSION` carries exactly one line `1.0.0rc3\n` with no trailing content.
- The changelog entry states the rc.3 identity (`1.0.0rc3` / `v1.0.0-rc.3`,
  `major`/`prepare`/`prerelease`), that rc.3 is local-only and not pushed/published in this
  objective, predecessor dispositions (rc.2 immutable and non-accepting, rc.1 published/rejected),
  incorporation of accepted #417 work on `main` (PR #471 / PR #472, #476, #477), the unchanged
  fork pin `aed6591a69f453a1867b73628603e7b53ba40ffc`, and the standing non-claims (not stable
  `1.0.0`, no package-index publication, WSL2 unverified, issue #261 open).
- The README paragraph names `1.0.0rc3`, annotated tag `v1.0.0-rc.3`, states the tag is a
  local-only candidate that is not pushed and not published in this objective (no nonexistent
  release link), keeps the three conclusions (`major`/`prepare`/`prerelease`), keeps the
  predecessor dispositions, the three non-claims, the open-#261 sentence, the feature-freeze
  sentence, cites no commit id, and carries no time-bound wording.
- `release.yml` refreshes only the authority comment above `FORK_COMMIT` to cite
  `oc_a179da8d654aec8b@v1`, retains the pin `aed6591a69f453a1867b73628603e7b53ba40ffc` unchanged,
  and keeps all validation logic intact.
- `tests/test_observation_reducer.py` required no code changes: the module's helper
  `_conflicting_envelopes` searches through 64 candidate envelopes (`implementer-1`..`64`), and
  under `1.0.0rc3` candidate `implementer-4` satisfies `canonical_digest(verification) < canonical_digest(candidate)`,
  preserving the precondition that the dangerous canonical representative is tested and passes.

## 2. Base receipt & verification

Measured at base `ad85b729746a1eb756f96f138894d527122ab2fd` before changes:

```console
$ uv sync --frozen
$ uv run --frozen pytest tests/test_public_artifacts.py tests/test_release_bundle.py -q
44 passed in 7.03s
```

The board base is clean and carries all required manifest and contract entries.

## 3. Reach proof — the corrected status reaches the built wheel's `METADATA`

```console
$ uv build --wheel --out-dir <scratch-root>/dist
Building wheel...
Successfully built <scratch-root>/dist/aether_agents-1.0.0rc3-py3-none-any.whl
# sha256 8987f650c027ad09a75ab41b11a6d766ad4fb3d6e6a72754f158f54b57cc3db9, 681 692 bytes
```

Wheel inspection proof:

| Measurement | Built wheel (`1.0.0rc3`) |
| --- | --- |
| `METADATA` `Version:` | `1.0.0rc3` |
| `METADATA` total bytes / status paragraph bytes | 7 782 / 990 bytes |
| `package version \`1.0.0rc3\`` | 1 / 1 |
| `annotated tag \`v1.0.0-rc.3\`` | 1 / 1 |
| `local-only candidate that is not pushed and not published` | 1 / 1 |
| `releases/tag/v1.0.0-rc.3` (forbidden published link) | **0 / 0** |
| `local rc.2 tag and activation history remain immutable` | 1 / 1 |
| `releases/tag/v1.0.0-rc.1` | 1 / 1 |
| `remains published and byte-immutable but rejected, and must not be activated` | 1 / 1 |
| `` `release_impact = major`, `release_action = prepare`, `release_channel = prerelease` `` | 1 / 1 |
| `**not** stable \`1.0.0\`` | 1 / 1 |
| `**not** a PyPI or other package-index publication` | 1 / 1 |
| `**not** a WSL2 qualification result` | 1 / 1 |
| `#261 therefore stays open with the stable, PyPI/OIDC and WSL2 gates outstanding` | 1 / 1 |
| `Feature expansion and nonessential Hermes changes remain frozen while the rolling reliability gate is qualified.` | 1 / 1 |
| **denial** `no release candidate has been published` | **0 / 0** |
| **denial** `beta stabilization build, not a release candidate` | **0 / 0** |
| **time-bound** `will be published` | 0 / 0 |
| **time-bound** `not yet` | 0 / 0 |
| **time-bound** `pending` | 1 / **0** (the single whole-document hit is the Telegram Monitor sentence at line 26) |
| **time-bound** `to be superseded` | 0 / 0 |

## 4. Coupled oracles — RED, repair, GREEN, control

All oracles below were measured, not assumed. Every mutation control mutated the file,
ran the test, verified the expected failure, and restored the file **byte-exactly** (restored
sha256 printed by the control equals the delivered sha256 in §1).

| # | Oracle | RED (observed) | Repair | GREEN | Mutation control |
| --- | --- | --- | --- | --- | --- |
| 1 | `test_release_bundle.py::test_version_file_carries_the_objective_release_identity` | `AssertionError: assert '1.0.0rc3' == '1.0.0rc2'` (line 127) | Expected identity updated to `1.0.0rc3` / `v1.0.0-rc.3` | `1 passed in 0.15s` | `VERSION` reverted to `1.0.0rc2` → `1 failed in 0.08s`; restored `50dfda64de95d7ac…` |
| 2 | `test_public_artifacts.py::test_readme_is_a_current_beta_portal_and_package_metadata_is_stable` | `AssertionError: assert 'releases/tag/v1.0.0-rc.2' in readme` (line 142) | Updated with rc.3 identity and truthfulness guard (`releases/tag/v1.0.0-rc.3` not in readme/status); kept negative controls, conclusions, non-claims, #261 | `9 passed in 1.94s` | Denial phrase inserted → `1 failed in 0.05s`; published rc.3 link inserted → `1 failed in 0.04s`; time-bound phrase inserted → `1 failed in 0.05s`; restored `a59ff58cbbce54fc…` |
| 3 | `test_observation_reducer.py::test_complete_pipeline_matches_the_reviewed_golden_summary_byte_for_byte` | `AssertionError: assert actual == expected` (differing in `provenance.compatibility_pairs[0].collector_version`, `reducer_version`, `summary_id`) | Golden summary fixture regenerated via documented procedure `json.dumps(actual, indent=2, sort_keys=True) + "\n"` | `128 passed in 2.34s` | Fixture `collector_version` reverted to `1.0.0rc2` → `1 failed in 0.46s`; restored `6192dafb09480d57…` |
| 4 | `test_observation_reducer.py::test_completion_event_id_conflict_neutralizes_authority_in_any_order` | `1 passed in 0.26s` (precondition verified: `implementer-4` candidate chosen with `v_digest < c_digest`) | No change required (`_conflicting_envelopes` searches `1..64` and cleanly satisfies the precondition under rc.3) | `128 passed in 2.34s` | Constrained search to `range(1, 2)` (where `implementer-1` digest is smaller than verification) → `1 failed in 0.49s` (`AssertionError: no conflicting envelope keeps the authorized bytes canonical`); restored `75c1547f79f5ddff…` |

## 5. Gates at the delivered tree

| Check | Command | Result |
| --- | --- | --- |
| Focused modules | `uv run --frozen pytest tests/test_public_artifacts.py tests/test_a1_contracts.py tests/test_release_bundle.py tests/test_documentation.py tests/test_contract_quality_documents.py -q -rs` | `103 passed, 1 skipped, 11 subtests passed in 8.94s` |
| Observation reducer module | `uv run --frozen pytest tests/test_observation_reducer.py -q` | `128 passed in 2.34s` |
| Documentation registry | `uv run --frozen python scripts/check_documentation.py` | `documentation validation passed`, exit 0 |
| Public-artifact path scan | `uv run --frozen python scripts/check_public_artifacts.py --root .` | `public artifact path scan passed: tracked surface + 0 artifact(s)`, exit 0 |
| Ruff lint (CI scope) | `uv run --frozen ruff check src tests scripts/check_documentation.py scripts/qualify_knowledge_expansion.py scripts/qualify_observation.py scripts/qualify_telegram_monitor.py scripts/telegram_monitor_lab.py scripts/check_hermes_baseline_drift.py scripts/check_public_artifacts.py scripts/release_bundle.py scripts/run_tests.py scripts/validate_hermes_patch_reconciliation.py` | `All checks passed!`, exit 0 |
| Ruff format (CI scope) | same path list, `ruff format --check` | `163 files already formatted`, exit 0 |
| Types | `uv run --frozen mypy src/aether_agents` | `Success: no issues found in 67 source files`, exit 0 |
| Whitespace | `git diff --check` | no output, exit 0 |
| Workflow parse | `yaml.safe_load` on `.github/workflows/release.yml` and `.github/workflows/policy.yml` | `release.yml`: parse=ok, jobs=['release']; `policy.yml`: parse=ok, jobs=['policy', 'observation-qualification', 'pull-request-target'] |
| Wheel build | `uv build --wheel --out-dir <scratch-root>/dist` | `aether_agents-1.0.0rc3-py3-none-any.whl`, sha256 `8987f650c027ad09a75ab41b11a6d766ad4fb3d6e6a72754f158f54b57cc3db9`, 681 692 bytes |

Deployment boundary: `.github/workflows/pages.yml` triggers on pushes to `main` touching
`website/**`, `docs/**` or itself. No delivered path matches, so this change cannot cause a
Pages build or deployment.

## 6. Environment-limited results (not unit defects)

- `SKIPPED [1] tests/test_contract_quality_documents.py:151`: "native loader requires the already
  provisioned Hermes interpreter". This skip is pre-existing and environmental (requires live
  Hermes runtime environment).
- No skip was added, and no assertion was weakened to obtain green.

## 7. Not verified here, with reasons

1. **Full canonical bootstrap, coverage gate, website suite and merged-revision numbers**
   belong to CI and `RC3-INTEGRATE-TAG`, which run on the PR head and merged revision.
2. **Tag creation, candidate freeze, and local update preview** belong to `RC3-INTEGRATE-TAG`.
   The Implementer role does not create tags or mutate release state.
3. **Activation, runtime canaries, rollback, and reactivation** belong to `RC3-ACTIVATE-CLOSEOUT`.
   No runtime activation was performed in this unit.
4. **Publication.** No tag push, GitHub release, or remote asset upload is performed in this
   unit or in this objective.
5. **Platforms.** WSL2, macOS and Windows remain unverified; nothing above is platform evidence.

## 8. Residuals — stale statements left unchanged, with reasons

Excluded surfaces (`docs/**`, `website/**`, `.github/workflows/pages.yml`, `ROADMAP.md`) may not
be edited by this unit: a push touching `docs/**`, `website/**` or `pages.yml` would trigger
a Pages deployment, which is outside this unit's scope.

| Path | Stale/superseded statement | Reason not changed |
| --- | --- | --- |
| `docs/capabilities.toml:136` | registry note mentions earlier rc milestone | `docs/**` is excluded from the unit's writable surface |
| `docs/reference/capabilities.md:694` | generated from `docs/capabilities.toml` | `docs/**` is excluded from the unit's writable surface |
| `docs/index.md:7–11` | mentions earlier rc milestone | `docs/**` is excluded from the unit's writable surface |
| `docs/product-boundary.md:36` | mentions earlier rc milestone | `docs/**` is excluded from the unit's writable surface |
| `docs/reference/limitations-and-troubleshooting.md:17` | scope table mentions earlier rc milestone | `docs/**` is excluded from the unit's writable surface |
| `ROADMAP.md:76–78, 111–112, 122, 171, 203` | roadmap describes earlier rc milestones | `ROADMAP.md` is excluded from the unit's writable surface |
| `DESIGN.md:351` (PD-57) | uses `v1.0.0-rc.1` / `1.0.0rc1` as grammar illustration | Illustrative tag-to-metadata mapping; conceptual design is Morfeo-owned |

## 9. Remaining `1.0.0rc2` hits sweep

A repository sweep `git grep -n '1\.0\.0rc2'` shows remaining references exist solely in:
1. `.aether/objective-contracts/oc_742f9f4797494bf9/v1.md`, `v2.md`, `v3.md`, `v4.md` (historical superseded contract files; immutable)
2. `.aether/objective-contracts/oc_a179da8d654aec8b/v1.md` (historical predecessor reference in canonical references)
3. `CHANGELOG.md:29` (the historical `1.0.0rc2` entry immediately below `1.0.0rc3`)
4. `specs/001-aether-v1-productization/evidence/RC2-IDENTITY.md` and `RC2-V3-MATERIALIZE.md` (historical rc.2 evidence records; immutable)
5. `specs/001-aether-v1-productization/tasks-rc2.md` (historical tasks breakdown; immutable)
6. `tests/test_public_artifacts.py:29` (in `ACCEPTED_PACKAGE_IDENTITIES` which preserves valid PEP 440 historical identities)

No stale `1.0.0rc2` references remain in active configuration, identity, or release surfaces.

## 10. Reproduction notes

- Every command above runs from `<aether-unit-worktree>` with `uv run --frozen`.
- `uv sync --frozen --reinstall-package aether-agents` was executed once after the `VERSION` edit
  so the local editable install's metadata reports the new version.
- Unit-level compatibility conclusion: this change advances the product version and release identity
  from `1.0.0rc2` / `v1.0.0-rc.2` to `1.0.0rc3` / `v1.0.0-rc.3` and repairs the coupled oracles.
  No `src/**` code, public interface, schema, or runtime state was changed, so no compatibility
  impact beyond that identity move is claimed. Prerelease status is not a compatibility impact,
  and no release or publication decision is made here.
