# RC2-IDENTITY — the rc.2 release identity and its coupled oracles

**Unit.** RC2-IDENTITY (Implementer) of the Aether `1.0.0-rc.2` objective.

**Authority.** Objective Contract `oc_742f9f4797494bf9@v1`, SHA-256
`f084eca7e703201c620408069df8f06b89cade82514ceb934c792f71bdda04fc`, plus the
Supervisor-owned breakdown `specs/001-aether-v1-productization/tasks-rc2.md` (unit entry
RC2-IDENTITY). The contract's in-scope item 5 and AC-02's source half, the fork-pin half of
AC-01, and the testing standard govern this unit.

**Base.** `acb89ca85c02c41dca10009b2806428850a0f0bc` — the contract-landing commit on top of
the clean pre-contract base `5758b89dfb19a71719faa8d1821849f8d66acacb` (`origin/main` at
measurement time). The delivered change is one local commit on the unit branch; the branch
name embeds the execution-card identity and is therefore not published here. The owning card
handoff names the exact branch and commit.

**Effects.** Local and reversible only: file edits in `<aether-unit-worktree>`, one local
commit, one wheel built into `<scratch-root>`, and read-only test/scan runs. No push, PR,
merge, tag, release, asset write, package-index publication, workflow dispatch or
deployment, service restart or activation, issue mutation, or credentials use. The rc.1
release was read (a retained local copy of the published wheel) and never written.

**Status of this record.** Unit-local implementation evidence. It is not an aggregate
release conclusion, not a publication or activation claim, and not independent review. Only
the terminal lane aggregates the three release conclusions; `RC2-GATES`, `RC2-BUNDLE`,
`RC2-INTEGRATE`, `RC2-PUBLISH` and the activation lane own the measurements listed in §7 as
not taken here.

## 0. Reading conventions

- Every measurement states the command that produced it and the observed result.
- **Sanitization.** The unit worktree appears as `<aether-unit-worktree>`, scratch roots as
  `<scratch-root>`, the execution card/branch as "the unit branch". Commit ids, tag/release
  names, SHA-256 digests and public URLs are published verbatim: the measurement is
  meaningless without them.
- The measured transcript behind §5 travels as a digest file attached to the owning card
  (`rc2-identity-gate-digest-<commit>.txt`), naming the commit and tree it was measured at;
  the untrimmed transcript stays at the scratch root named in §9. That digest was taken at
  `3076d61adc4909d2fa3bd2ade6a746db9a34169d`, the revision of this record immediately
  before this paragraph was reworded: the only difference to the delivered commit is this
  record's own text, so the measured code, identity and test files are byte-identical.
- One post-review correction is recorded in §3 (the built wheel's size, a transcription
  error) and carried by `rc2-identity-gate-digest-correction.txt`, attached to the owning
  card; it lands as the follow-up commit on the unit branch, touches no delivered file, and
  supersedes that single line of the digest named above.
- `git status --porcelain` and `git diff --numstat` below are the pre-commit state of the
  exact delivered set; this record is added by the same commit and therefore appears as one
  new tracked path in it.

## 1. What changed

```console
$ git status --porcelain
 M .github/workflows/policy.yml
 M .github/workflows/release.yml
 M AGENTS.md
 M CHANGELOG.md
 M README.md
 M VERSION
 M tests/fixtures/observation/complete-summary.json
 M tests/test_observation_reducer.py
 M tests/test_public_artifacts.py
 M tests/test_release_bundle.py

$ git diff --numstat
1	0	.github/workflows/policy.yml
7	4	.github/workflows/release.yml
1	1	AGENTS.md
35	0	CHANGELOG.md
1	1	README.md
1	1	VERSION
3	3	tests/fixtures/observation/complete-summary.json
37	9	tests/test_observation_reducer.py
12	1	tests/test_public_artifacts.py
2	2	tests/test_release_bundle.py
```

| Path | Change | sha256 (delivered) |
| --- | --- | --- |
| `VERSION` | `1.0.0rc1` → `1.0.0rc2` (the single product-version source) | `edac39095241d5567f131a7cf9eb471c5953535df83ea048bc3cf54c02e0aa4d` |
| `README.md` | status paragraph (line 5) now states the rc.2 identity, the activation eligibility and the rc.1 disposition | `121c0b5319c488ac9ee299ad3b8f17ede8ceb11baaaa5482947e9cd1e0aedf2f` |
| `CHANGELOG.md` | new `1.0.0rc2` entry above the rc.1 entry (35 insertions, 0 deletions: rc.1 entry byte-unchanged) | `43fd8033ddf5e3bd5f8c501c34bc2ab108adef6328efc6f0d651615f9440ca42` |
| `AGENTS.md` | "currently authorized bounded objective" paragraph reconciled with rc.2, the rc.1 disposition and the single authorized automatic existing-site Pages deployment | `df3a05e892440675141c4832849a07b55e8d854b7aabfef0e967af37a299e4f6` |
| `.github/workflows/release.yml` | `FORK_COMMIT` → `7a4fdcd0…`; comment block reconciled with the rc.2 pin | `688e9a33ffbb2396dc0dae39c6203d91ddb6386dc40b3629d24c064c1fa687ee` |
| `.github/workflows/policy.yml` | one manifest line added in sorted position | `dd3d857f410f243286008d3911ec077362b62a45958b5201f8655e505ab11f0e` |
| `tests/test_public_artifacts.py` | README oracle repaired | `f6d2a36dbc5e0c8832e65b0cc98d3b365920aca87851c187369533e2e1ca219f` |
| `tests/test_release_bundle.py` | `VERSION` identity oracle repaired | `a5967b1c9e20061b58a07360e6bac1de5d6efcd587b7944e0fcfd332974d884b` |
| `tests/test_observation_reducer.py` | digest-order oracle repaired | `75c1547f79f5ddff4fca7ad0d49cebb0fbef337b13ae0fc02ccff52f517645c8` |
| `tests/fixtures/observation/complete-summary.json` | reviewed golden summary regenerated | `b26d086105f3b67bb8cdd3be422f6a58cfcf65e3d01a87adf2b6863924973136` |

Content notes:

- `VERSION` carries no trailing content beyond the single line `1.0.0rc2`.
- The changelog entry states the rc.2 identity (`1.0.0rc2` / `v1.0.0-rc.2`,
  `major`/`publish`/`prerelease`), that rc.2 supersedes rc.1 as the candidate eligible for
  activation while rc.1 remains published, byte-immutable and rejected, the maintained-fork
  pin this release carries, the manifest/guidance reconciliation, and the standing non-claims
  (not stable `1.0.0`, no package-index publication, WSL2/macOS/Windows unverified, issue
  #261 open with the stable/PyPI/OIDC/WSL2 gates). It claims no qualification, publication or
  activation outcome; those belong to the objective's later units, which the entry says.
- The README paragraph names `1.0.0rc2`, links the `v1.0.0-rc.2` release and the immutable
  `v1.0.0-rc.1` predecessor, keeps the three conclusions, the three non-claims, the
  open-#261 sentence and the feature-freeze sentence, and states that rc.1 must not be
  activated. It cites no commit id for rc.2 — the tag link is the identity — and carries no
  time-bound wording (see §3).
- `release.yml` keeps its fail-closed placeholder discipline, the tag/identity validation
  block (`VERSION` equality, annotated-tag type, tag target equal to `origin/main`) and the
  single create/reconcile release path; only the pin and its comment changed.
- `policy.yml` gains exactly `.aether/objective-contracts/oc_742f9f4797494bf9/v1.md`
  between `oc_644c0b407d13366a/v1.md` and `oc_75401d18c602d787/v1.md` (sorted position).

## 2. Measured base defect (§1 of the breakdown) — RED then GREEN

```console
$ uv run --frozen pytest tests/test_public_artifacts.py tests/test_a1_contracts.py \
    tests/test_release_bundle.py tests/test_documentation.py \
    tests/test_contract_quality_documents.py -q -rs     # base, before any edit
1 failed, 102 passed, 1 skipped, 11 subtests passed in 26.13s
E  At index 20 diff: '.aether/objective-contracts/oc_75401d18c602d787/v1.md' !=
                      '.aether/objective-contracts/oc_742f9f4797494bf9/v1.md'
E  Right contains one more item: 'website/tsconfig.json'
tests/test_public_artifacts.py:206: AssertionError
```

The declared manifest held 407 names against 408 tracked non-`specs/` paths, missing exactly
the contract-landing file. After the §1 manifest line was added:

```console
$ uv run --frozen pytest tests/test_public_artifacts.py tests/test_release_bundle.py -q
44 passed in 5.95s
```

## 3. Reach proof — the corrected status reaches the built wheel's `METADATA`

Before/after are the same ten required sentences and the same six denial/time-bound phrases
counted in the artifact's own `METADATA` long description (whole metadata, and the
`**Status:**` paragraph alone). The *before* artifact is the published rc.1 wheel retained
locally at `<scratch-root>/lcfixreadme-pub/`, whose sha256
`19c6cf5248c05485ec883cfea5ee29c7b1fbbdf7b8f352d085b29b3bfced354a` equals the
release-advertised digest recorded in `specs/001-aether-v1-productization/evidence/LC-FIX-README.md`
§1 (a second retained copy in `<scratch-root>/lcint-downloaded/` hashes identically). The
*after* artifact is this unit's build:

```console
$ uv build --wheel --out-dir <scratch-root>/dist
Successfully built <scratch-root>/dist/aether_agents-1.0.0rc2-py3-none-any.whl
# sha256 d3393e07fefe6a7d27ae82086e49334ba79c502e841feec7ea4176c68fa197d6, 674 913 bytes
```

**Corrected figure (post-review).** An earlier revision of this record stated `674 916 bytes`
for the wheel above. The file that carries sha256 `d3393e07…` is **674 913 bytes**:
re-measured on the retained build, `stat -c '%s'` and `os.path.getsize` both report `674 913`
for `<scratch-root>/dist/aether_agents-1.0.0rc2-py3-none-any.whl`, whose sha256 re-verifies as
`d3393e07…` — one byte string cannot carry two sizes. The figure was transcribed, not
measured: no gate step prints a wheel-size line, so the wrong value never had a source in the
transcript. The corrected figure appears above and in §5; the immutable attachments
`rc2-identity-gate-digest-3076d61.txt:22` and `rc2-identity-gate-digest.txt:22` keep the
superseded one, and `rc2-identity-gate-digest-correction.txt`, attached alongside this record,
supersedes that line.

| Measurement | rc.1 wheel (published) | rc.2 wheel (this unit) |
| --- | --- | --- |
| `METADATA` `Version:` | `1.0.0rc1` | `1.0.0rc2` |
| `METADATA` size / status-paragraph size | 7 522 / 730 bytes | 7 763 / 971 bytes |
| `package version \`1.0.0rc2\`` | 0 / 0 | 1 / 1 |
| `releases/tag/v1.0.0-rc.2` | 0 / 0 | 1 / 1 |
| `Rc.2 is the candidate eligible for activation` | 0 / 0 | 1 / 1 |
| `remains published and byte-immutable but rejected, and must not be activated` | 0 / 0 | 1 / 1 |
| `` `release_impact = major`, `release_action = publish`, `release_channel = prerelease` `` | 1 / 1 | 1 / 1 |
| `**not** stable \`1.0.0\`` | 1 / 1 | 1 / 1 |
| `**not** a PyPI or other package-index publication` | 1 / 1 | 1 / 1 |
| `**not** a WSL2 qualification result` | 1 / 1 | 1 / 1 |
| `#261 therefore stays open with the stable, PyPI/OIDC and WSL2 gates outstanding` | 1 / 1 | 1 / 1 |
| `Feature expansion and nonessential Hermes changes remain frozen while the rolling reliability gate is qualified` | 1 / 1 | 1 / 1 |
| **denial** `no release candidate has been published` | **1 / 1** | **0 / 0** |
| **denial** `beta stabilization build, not a release candidate` | **1 / 1** | **0 / 0** |
| **time-bound** `will be published` | 0 / 0 | 0 / 0 |
| **time-bound** `not yet` | 0 / 0 | 0 / 0 |
| **time-bound** `pending` | 1 / **0** | 1 / **0** |
| **time-bound** `to be superseded` | 0 / 0 | 0 / 0 |

The published rc.1 wheel is the defect this objective exists for: its own status paragraph
denied that any release candidate had been published (`1` in the status paragraph). The new
wheel carries every required sentence in the same paragraph and no denial phrase. The single
whole-document `pending` hit is the unrelated Telegram Monitor sentence (`README.md:26`,
"remain pending terminal integration"), outside the status paragraph, and it is unchanged by
this unit; it is counted here rather than hidden by a narrower grep.

## 4. Coupled oracles — RED, repair, GREEN, control

All five oracles below were measured, not assumed. Every mutation control mutated, ran, and
restored the file **byte-exactly** (restored sha256 printed by the control equals the
delivered sha256 in §1).

| # | Oracle | RED (observed) | Repair | GREEN | Mutation control |
| --- | --- | --- | --- | --- | --- |
| 1 | `test_public_artifacts.py::test_canonical_base_manifest_matches_tracked_non_specs_files` | base: `1 failed` (§2) | add the one missing manifest line | included in the 103-passed focused run | line removed again → `1 failed in 0.03s`; restored `dd3d857f410f2432…` |
| 2 | `test_public_artifacts.py::test_readme_is_a_current_beta_portal_and_package_metadata_is_stable` | `AssertionError: assert '**has been published**' in readme` (line 139) | the rc.1-era positive assertion is replaced by rc.2 identity assertions plus a status-paragraph durability guard; the negative controls, the three conclusions and the #261 sentence stay | 103 passed (§5) | denial phrase inserted → `1 failed in 0.03s`; time-bound phrase inserted → `1 failed in 0.03s`; an rc.2 commit id inserted → `1 passed` (the no-commit-id rule of the card is satisfied by the delivered wording but is **not** oracle-enforced — recorded, not hidden); restored `121c0b5319c488ac…` |
| 3 | `test_release_bundle.py::test_version_file_carries_the_objective_release_identity` | `AssertionError: assert '1.0.0rc2' == '1.0.0rc1'` (line 127) | expected identity becomes `1.0.0rc2` / `v1.0.0-rc.2` (the oracle's purpose — `VERSION` carries the objective's identity — is unchanged) | 44 passed (§2) | `VERSION` reverted to `1.0.0rc1` → `1 failed in 0.07s`; restored `edac39095241d556…` |
| 4 | `test_observation_reducer.py::test_complete_pipeline_matches_the_reviewed_golden_summary_byte_for_byte` | `AssertionError: assert actual == expected`, differing in `reducer_version`, `summary_id` and `provenance.compatibility_pairs[*].collector_version` (line 52) | the reviewed golden is regenerated from this build's own pipeline | 167 passed for the two observation modules that run here | regeneration procedure validated first: `json.dumps(summary, indent=2, sort_keys=True) + "\n"` reproduced the committed 24 373-byte document exactly, differing in exactly the three version-derived lines; the delivered fixture diff is `3 3` and nothing else |
| 5 | `test_observation_reducer.py::test_completion_event_id_conflict_neutralizes_authority_in_any_order` | `AssertionError: assert 'b05b9c2f…' < 'ae410fd6…'` (line 1759) | the conflicting envelope is selected by the digest relation the reducer's `min(canonical_digest)` rule retains, instead of an assumed product version, and the assertion still proves the dangerous side was selected | 167 passed (same run) | rc.1-era single-actor construction restored in the test → `AssertionError: no conflicting envelope keeps the authorized bytes canonical`; restored `75c1547f79f5ddff…` |

Why oracle 3 and 4 were repaired rather than pinned elsewhere:

- The `VERSION` oracle is the only check that the repository's product-version file derives
  the objective's release identity; pinning it to a stale literal would have deleted that
  coverage, so the expected identity moved with the objective.
- The golden fixture embeds the product version, but the same test still asserts the
  derivation it rests on — `COLLECTOR_VERSION == product_version()` and
  `REDUCER_VERSION == f"aether.observation.reducer.v1+{COLLECTOR_VERSION}"`
  (`tests/test_observation_reducer.py:40–41`). Regenerating therefore keeps the promise
  covered instead of freezing a literal the artifact no longer satisfies.
- Oracle 5's assertion was a *precondition* that the sample exercises the conflict case the
  reducer once left `completed`. Under rc.2 the digest relation flipped, so the rc.1-era
  construction silently stopped exercising the dangerous representative. The repair restores
  the dangerous sample and proves it, and the control demonstrates the loss it would
  otherwise have hidden.
- No assertion was deleted, skipped or weakened: the two README negative controls, the three
  conclusion assertions, the non-claim assertions, the #261 assertion, the digest-equality
  checks and every behaviour assertion around them are unchanged.

The locked observation qualification node manifest was re-measured after the test edits:

```console
$ uv run --frozen python <scratch-root>/check_core_node_manifest.py
expected_core_tests=466 collected=466
expected_node_manifest=b9879d323fa5c36bedee667008324f159885f054782f3bba1fa310797b260ee4
measured_node_manifest=b9879d323fa5c36bedee667008324f159885f054782f3bba1fa310797b260ee4
match=True
```

The repair added a module-level helper, not a test node, so the pinned 466-node manifest is
unchanged.

## 5. Gates at the delivered tree

| Check | Command | Result |
| --- | --- | --- |
| Focused modules | `uv run --frozen pytest tests/test_public_artifacts.py tests/test_a1_contracts.py tests/test_release_bundle.py tests/test_documentation.py tests/test_contract_quality_documents.py -q -rs` | `103 passed, 1 skipped, 11 subtests passed` (identical counts in two runs of the delivered state; elapsed time moves with machine load — 6.93 s idle, 32.19 s in the attached transcript) |
| Observation + adjacent modules | `uv run --frozen pytest tests/test_observation_*.py tests/test_lifecycle_projections.py tests/test_project_init.py tests/test_lab_formalization.py tests/test_objective_contracts.py -q -rs` (the eleven matching observation modules) | `32 failed, 721 passed, 14 skipped in 174.10s` — all 32 failures are the environmental class of §6 |
| Documentation registry | `uv run --frozen python scripts/check_documentation.py` | `documentation validation passed`, rc 0 |
| Public-artifact path scan | `uv run --frozen python scripts/check_public_artifacts.py --root .` | `public artifact path scan passed: tracked surface + 0 artifact(s)`, rc 0 |
| Ruff lint (CI scope, 12 paths) | `uv run --frozen ruff check src tests scripts/check_documentation.py scripts/qualify_knowledge_expansion.py scripts/qualify_observation.py scripts/qualify_telegram_monitor.py scripts/telegram_monitor_lab.py scripts/check_hermes_baseline_drift.py scripts/check_public_artifacts.py scripts/release_bundle.py scripts/run_tests.py scripts/validate_hermes_patch_reconciliation.py` | `All checks passed!`, rc 0 |
| Ruff format (CI scope) | same path list, `ruff format --check` | `160 files already formatted`, rc 0 |
| Types | `uv run --frozen mypy src/aether_agents` | `Success: no issues found in 67 source files`, rc 0 |
| Whitespace | `git diff --check` | no output, rc 0 |
| Workflow parse | `yaml.safe_load` on both edited workflows | `release.yml: parse=ok jobs=['release'] env_keys=['FORK_COMMIT','FORK_REPOSITORY']`, `FORK_COMMIT=7a4fdcd083409c31c09cfa3bfa345354e8576a7e`; `policy.yml: parse=ok jobs=['observation-qualification','policy','pull-request-target']` |
| Release-workflow contract tests | `uv run --frozen pytest tests/test_release_bundle.py -q -k "workflow or version_file or release_identity"` | `6 passed, 29 deselected` |
| Wheel build | `uv build --wheel --out-dir <scratch-root>/dist` | `aether_agents-1.0.0rc2-py3-none-any.whl`, sha256 `d3393e07fefe6a7d27ae82086e49334ba79c502e841feec7ea4176c68fa197d6`, 674 913 bytes (§3 corrects the earlier figure) |

Deployment boundary: `.github/workflows/pages.yml` triggers on pushes to `main` touching
`website/**`, `docs/**` or itself. No delivered path matches, so this change cannot cause a
Pages build or deployment.

## 6. Environment-limited results (not unit defects)

The observation sweep reports failures caused only by an absent interpreter in this local
environment:

- `ModuleNotFoundError: No module named 'hermes_cli'` at import/collection: 23 nodes in
  `tests/test_observation_cli_plugin.py` and 1 in `tests/test_observation_lifecycle.py`
  (`test_exact_public_lifecycle_uses_real_plugin_profiles_query_and_recovery`), plus 8 board
  nodes in `tests/test_objective_contracts.py`. Those nodes' test code is untouched by this
  unit, the error occurs before any assertion, and the same class of lane is the source of
  the pre-existing skips the focused run reports
  (`tests/test_contract_quality_documents.py:151`, "native loader requires the already
  provisioned Hermes interpreter"). `uv run --frozen python -c "import hermes_cli"` fails
  identically with no repository change.
- Skips: `tests/test_observation_brief_tool.py:197`,
  `tests/test_observation_qualification.py` (147, 736, 1129×7, 1314, 1711),
  `tests/test_observation_qualification.py:1500` (100k lane) and
  `tests/test_lab_formalization.py:643` — all pre-existing and environmental.

No skip was added, and no assertion was weakened to obtain green.

## 7. Not verified here, with reasons

1. **Full canonical bootstrap, coverage gate, website suite and the merged-revision numbers**
   belong to `RC2-GATES`, which must run at the merged revision; a candidate-branch run is
   not that measurement. This unit ran the focused modules the card names.
2. **Bundle determinism, member/privacy inspection, clean install and the HLP reconciliation
   check** belong to `RC2-BUNDLE`. The wheel built here is a reach proof only; it is not
   qualified, and no second-root byte-identity is claimed.
3. **Publication and activation.** No tag, release, asset or runtime state was created or
   changed, so nothing here proves that rc.2 is published, activatable or accepted. The
   README/changelog wording is durable *for the artifact this tree becomes*, verified against
   the built wheel's `METADATA`, not against a published release.
4. **rc.1 non-mutation.** This unit read a retained local copy of the published wheel and
   performed no release-side write; it cannot and does not claim an audit trail over rc.1
   (the read-only verification unit owns that measurement).
5. **Platforms.** WSL2, macOS and Windows remain unverified; nothing above is platform
   evidence.
6. **The fork pin's remote state.** `7a4fdcd0…` is used as the accepted pin because the
   contract fixes it; this unit did not re-resolve the remote fork tip (the read-only
   verification unit owns that re-derivation).

## 8. Residuals — stale statements left unchanged, with reasons

Excluded surfaces (`docs/**`, `website/**`, `.github/workflows/pages.yml`) may not be edited
by this objective: a push to `main` touching them deploys the existing public site, and only
the #446-caused automatic deployment is authorized.

| Path | Stale/superseded statement | Reason not changed |
| --- | --- | --- |
| `docs/capabilities.toml:136` | the registry note names "the authorized `1.0.0rc1` / `v1.0.0-rc.1` milestone" as the current bounded milestone and its "bounded real activation/rollback lane on published bytes" as pending | `docs/**` is excluded; the generated public site is served from this corpus. Editing it would deploy the existing public site |
| `docs/reference/capabilities.md:694` | same sentence, generated from the registry above | same; also generated, so the registry change has to land first |
| `docs/index.md:7–11` | "The executable Hermes source for the authorized `1.0.0rc1` milestone … That milestone is a bounded pre-stable release candidate" | `docs/**` is excluded |
| `docs/product-boundary.md:36` | "The authorized `1.0.0rc1` milestone is a pre-stable release candidate" | `docs/**` is excluded |
| `docs/reference/limitations-and-troubleshooting.md:17` | the release-candidate scope row names only `1.0.0rc1` / `v1.0.0-rc.1` and the never-activate disposition of rc.1, with no successor | `docs/**` is excluded; the row stays *true* of rc.1, it is only incomplete about rc.2 |
| `ROADMAP.md:76–78, 111–112, 122, 171, 203` | the roadmap still describes "the authorized `1.0.0rc1` objective" and `oc_3397f9f05d780f8e@v1` as the current bounded authorization | outside this card's enumerated writable surface (the card requires exactly the seven changes of §1 and names only `AGENTS.md` for root guidance); re-wording the roadmap is a documentation-authoring decision like the rc.1 precedent that needed steward direction |
| `DESIGN.md:351` (PD-57) | uses `v1.0.0-rc.1` / `1.0.0rc1` as the illustrative tag-to-metadata mapping | not a status statement — the mapping stays true as a grammar illustration — and canonical design is Morfeo-owned |

Also recorded, and already known to this objective: the capability registry's
"activation lane pending" clause is falsified once rc.2 is activated; the breakdown raises
that coherence gap with the design steward (deployment boundary, not this unit's surface).

## 9. Reproduction notes

- Every command above runs from `<aether-unit-worktree>` with
  `uv run --frozen` (the locked toolchain); `uv sync --frozen --reinstall-package
  aether-agents` was needed once after the `VERSION` edit so the local editable install's
  metadata reports the new version — an environment step, not a repository change.
- Scratch artifacts referenced here: `<scratch-root>/dist/` (the rc.2 wheel),
  `<scratch-root>/lcfixreadme-pub/` and `<scratch-root>/lcint-downloaded/` (retained copies of
  the published rc.1 wheel), `<scratch-root>/metadata_reach_proof.py`,
  `<scratch-root>/regenerate_golden.py`, `<scratch-root>/check_core_node_manifest.py`,
  `<scratch-root>/mutation_controls.py`, `<scratch-root>/mutation_controls_readme.py`,
  `<scratch-root>/mutation_control_digest_order.py`, `<scratch-root>/focused_after.txt`,
  `<scratch-root>/obs_related_after.txt`.
- Unit-level compatibility conclusion: this change moves the product version and the release
  identity from `1.0.0rc1`/`v1.0.0-rc.1` to `1.0.0rc2`/`v1.0.0-rc.2` and repairs the oracles
  that encoded the predecessor. No `src/**` behavior, public interface, schema or runtime
  state changed, so no compatibility impact beyond that identity move is claimed. Prerelease
  status is not itself a compatibility impact, and no release or publication decision is made
  here.
