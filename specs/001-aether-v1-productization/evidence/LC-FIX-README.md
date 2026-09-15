# LC-FIX-README Evidence — public README status corrected to the published RC (#239)

**Unit:** LC-FIX-README (task `t_191474c2`, Implementer; same-card Supervisor review pending)
**Objective Contract:** `oc_3397f9f05d780f8e@v1` (SHA-256 `4d4c7650bf8ea93fc7cffe3d87f7f974e172d66cefcf6a74a2d83051568a4879`)
**Canonical breakdown:** `specs/001-aether-v1-productization/tasks.md` (read-only for this unit)
**Base tip before the change:** `748aa24` (`release: Aether 1.0.0-rc.1 lifecycle, maintained-fork runtime and prerelease (#442)`)
**Branch:** `aether-agents-2/t_191474c2-lc-fix-readme-public-readme-status-must`
**Delivered change:** `README.md` (1 hunk, line 5), `tests/test_public_artifacts.py` (coupled oracle, disclosed in §5), this record
**Status of this record:** unit-local implementation evidence. It is not an aggregate release conclusion, not a publication claim and not independent review. Compatibility impact is reported at unit level only; Supervisor owns the aggregate release conclusions.

---

## 1. Primary-source verification of the publication

Read from the live repository/release, not from a summary or another artifact:

| Fact | Value | How read |
| --- | --- | --- |
| Annotated tag | `refs/tags/v1.0.0-rc.1` → tag object `cda1eccae588197251ca22e9a0fdffaf81c4d599` → commit `748aa24ce5684185f65aa88b0e85919627ff6538` | `git for-each-ref refs/tags/v1.0.0-rc.1 --format='%(refname) %(objecttype) %(objectname) %(*objectname)'` |
| GitHub release | `v1.0.0-rc.1`; `isPrerelease=true`, `isDraft=false`; published `2026-09-15T13:24:54Z` | `gh release view v1.0.0-rc.1 --json …` (read-only) |
| Published wheel | `aether_agents-1.0.0rc1-py3-none-any.whl`, release asset digest `sha256:19c6cf52…` | same read; then downloaded with `gh release download -R DarkArty07/Aether-Agents -p …` and re-hashed locally: `19c6cf5248c05485ec883cfea5ee29c7b1fbbdf7b8f352d085b29b3bfced354a` (identical to the digest stated in the card) |
| Published METADATA | `aether_agents-1.0.0rc1.dist-info/METADATA` line 44 carries the stale sentence; `grep -c 'no release candidate has been published'` = **1** | read from the downloaded published wheel |

## 2. The defect as measured

`README.md:5` at `748aa24` stated (exact, quoted below in §3.1) that the checked-in tree is "still a beta stabilization build, not a release candidate" and that **"no release candidate has been published from this repository"**, with the release described in the future tense ("targets"). Both halves were false at the tagged commit: the annotated prerelease `v1.0.0-rc.1` **is** published from this repository and points at that commit (§1). Because `pyproject.toml` declares `readme = "README.md"`, the same sentence was embedded in the published wheel's long description — the published public artifact stated that no release candidate had been published while being the release candidate's wheel.

`git grep -n "no release candidate has been published"` over the whole tree returns **one** tracked hit at the base tip: `README.md:5` (§6 lists neighbouring statements with different wording).

## 3. Correction — `README.md`, single hunk at line 5

### 3.1 Before (`README.md:5` at `748aa24`)

```
**Status:** the checked-in tree is still a beta stabilization build, not a release candidate — no release candidate has been published from this repository. The owner-authorized `1.0.0rc1` objective targets package version `1.0.0rc1` and annotated GitHub prerelease `v1.0.0-rc.1` (`release_impact = major`, `release_action = publish`, `release_channel = prerelease`) as a bounded pre-stable milestone: explicitly **not** stable `1.0.0`, **not** a PyPI or other package-index publication, and **not** a WSL2 qualification result. Issue #261 therefore stays open with the stable, PyPI/OIDC and WSL2 gates outstanding. Feature expansion and nonessential Hermes changes remain frozen while the rolling reliability gate is qualified.
```

### 3.2 After (delivered `README.md:5`)

```
**Status:** the owner-authorized `1.0.0rc1` objective's annotated GitHub prerelease [`v1.0.0-rc.1`](https://github.com/DarkArty07/Aether-Agents/releases/tag/v1.0.0-rc.1) **has been published** from this repository, at annotated tag `v1.0.0-rc.1` on commit `748aa24` with package version `1.0.0rc1` (`release_impact = major`, `release_action = publish`, `release_channel = prerelease`). That milestone is bounded and pre-stable: explicitly **not** stable `1.0.0`, **not** a PyPI or other package-index publication, and **not** a WSL2 qualification result. Issue #261 therefore stays open with the stable, PyPI/OIDC and WSL2 gates outstanding. Feature expansion and nonessential Hermes changes remain frozen while the rolling reliability gate is qualified.
```

`git diff --numstat` → `1 1 README.md`: one line replaced, no other hunk in the file.

### 3.3 What was deliberately preserved, and what was not touched

Preserved verbatim in substance (each is asserted by the repaired oracle in §5):

- annotated tag named and the release named/linked (`v1.0.0-rc.1`);
- package version `1.0.0rc1` and the three conclusions `release_impact = major`, `release_action = publish`, `release_channel = prerelease`;
- **not** stable `1.0.0`; **not** a PyPI or other package-index publication; **not** a WSL2 qualification result;
- issue **#261 stays open** with the stable, PyPI/OIDC and WSL2 gates outstanding;
- the feature-freeze sentence.

Not touched: the README's portal role (no capability claim added, no duplication of `docs/capabilities.toml`, no changelog entry), the rest of `README.md`, and every file named as out of surface in the card. The publication date and asset inventory were deliberately left out of the README — a portal should not carry a release manifest.

## 4. Reach verification — the text reaches the artifact future builds produce

| Measurement | Result |
| --- | --- |
| Build command | `uv build --wheel --out-dir /tmp/lcfixreadme-dist2` (from this worktree, at the delivered tip) |
| Built wheel | `aether_agents-1.0.0rc1-py3-none-any.whl`, sha256 `4d244eb54fff2ca8f51938b2e45ea4e6c4610a3edc48141c9a6e1b8bec7534a4` (674 855 bytes) |
| Repeat build | an earlier build of the same tree produced the **same** digest `4d244eb5…`; the wheel packages only `aether_agents/` and the dist-info (158 members), so `tests/` and `specs/` — not packaged — cannot change the artifact bytes |
| `METADATA` line 44 (local build) | the corrected sentence of §3.2, verbatim |
| `grep -c 'no release candidate has been published'` on local `METADATA` | **0** |
| `METADATA` line 44 (published wheel) | the stale sentence of §3.1, verbatim; stale-sentence count **1** |

### 4.1 The published bytes are unchanged and were not repaired

**Explicit statement:** the already-published wheel and sdist and their embedded
`METADATA` bytes are **unchanged** by this unit and were **not** repaired. The published
wheel still carries the stale sentence measured in §4; only future builds from canonical
source carry the correction. Repairing the published bytes would require replacing the
release assets (delete → re-upload or `--clobber`) or moving the `v1.0.0-rc.1` tag onto a
new commit and re-running publication — all forbidden for this unit by the card (no
delete, no re-upload, no `--clobber`, no history rewrite, no tag move, no release
mutation). None of those effects was attempted, and nothing on the release was written:
the only release-side operations in this unit were reads (`gh release view`,
`gh release download`). The consequence is recorded in §9 rather than hidden.

## 5. Coupled oracle repair — disclosed boundary extension

`tests/test_public_artifacts.py::test_readme_is_a_current_beta_portal_and_package_metadata_is_stable`
pinned the stale sentence as a **pass condition**:

```
assert "beta stabilization build, not a release candidate" in readme
```

That assertion is the same stale claim encoded as an oracle, so the correction could not be
true *and* green without inverting it. Measurements, in order:

| Step | Command | Result |
| --- | --- | --- |
| RED (after the README correction, before the oracle repair) | `uv run --frozen pytest tests/test_public_artifacts.py -q -k readme_is_a_current` | `1 failed` — `AssertionError: assert 'beta stabilization build, not a release candidate' in '# Aether Agents…'` at `tests/test_public_artifacts.py:138` |
| Repair | line 138 replaced by the eight assertions below | diff shown by `git diff --numstat` → `10 1 tests/test_public_artifacts.py` |
| GREEN | `uv run --frozen pytest tests/test_public_artifacts.py -q` | `9 passed` |
| Mutation control (guard still has teeth) | stale sentence re-appended to `README.md`, test re-run, file restored byte-exactly | `1 failed` — `AssertionError` naming `no release candidate has been published from this repository` (the negative control), then `9 passed` after restore |

Repaired assertions: the README must link the release (`releases/tag/v1.0.0-rc.1`), must
state `**has been published**`, must **not** contain `beta stabilization build, not a
release candidate` or `no release candidate has been published`, and must still contain
`**not** stable \`1.0.0\``, `**not** a PyPI or other package-index publication`, `**not** a
WSL2 qualification result`, and the open-#261 sentence. The guard's intent — the README is
a current portal that must not overclaim — is preserved and inverted to the true status; no
assertion was deleted, skipped or weakened, and no other assertion in the file changed.

**Disclosure:** the card's writable surface is `README.md` and this record, and it names
`tests/**` as not-to-be-touched-without-saying-so. This one oracle is a genuinely
invalidated neighbouring statement (the defect's own claim, encoded as an expectation), so
it was repaired rather than left red, and it is disclosed here, in a board comment on
`t_191474c2`, and in the review request. `git grep -n "test_readme_is_a_current_beta_portal"`
finds no other pin (only `specs/001-aether-v1-productization/evidence/LC-DOCS.md:153`, a
frozen record of another unit, and the test definition itself), and no workflow or coverage
lane names that test node.

## 6. Reported, not changed — neighbouring statements with the same defect class

Fixable only outside this unit's writable surface; reported for Supervisor routing as a
bounded follow-up rather than widened into silently.

| Location | Text now false/stale | Why unchanged here |
| --- | --- | --- |
| `CHANGELOG.md:3` | heading `## 1.0.0rc1 — release candidate (pre-stable, not yet published)` | `CHANGELOG.md` is named out of surface. Re-wording a released entry is a documentation-authoring decision (the entry doubles as the release-notes source), not a mechanical edit. |
| `docs/reference/limitations-and-troubleshooting.md:17` | "The authorized `1.0.0rc1` / `v1.0.0-rc.1` milestone is pre-stable and **unpublished here**." | `docs/**` is named out of surface. The non-claims in the same row remain correct; only "unpublished here" is stale. |
| `docs/index.md:4` (borderline) | "It is not a release claim: the project remains in operational-reliability stabilization, and **its release path is not qualified**." | `docs/**` out of surface, and it is a judgement call: the *publication* path is now qualified by the published prerelease, while the stable/PyPI/WSL2 gates remain open. The wording decision belongs to the docs owner. |

Classified as **not** invalidated (no change proposed): `INCOMPLETE_IMPLEMENTATIONS.md:165`
("the build is a beta stabilization build, not an RC") sits inside a dated historical
snapshot whose own notice says its "Current behavior" wording "must not be read as
current-build claims" — the same frozen-record classification `LC-DOCS.md` used. Test and
spec records citing the retired wording (`tests/test_observation_lifecycle.py:521`,
`tests/test_observation_qualification.py:122,722`) are untouched and non-normative.

## 7. Gates at the delivered tip

| Check | Command | Result |
| --- | --- | --- |
| Documentation registry | `uv run --frozen python scripts/check_documentation.py` | `documentation validation passed` (rc 0) |
| Public-artifact path scan | `uv run --frozen python scripts/check_public_artifacts.py` | `public artifact path scan passed: tracked surface + 0 artifact(s)` (rc 0) |
| Ruff lint (CI scope) | `uv run --frozen ruff check src tests scripts/…` (the 12 paths `.github/workflows/policy.yml:697` uses) | `All checks passed!` (rc 0) |
| Ruff format (CI scope) | same path list, `ruff format --check` | `160 files already formatted` (rc 0) |
| Focused tests | `uv run --frozen pytest tests/test_public_artifacts.py tests/test_documentation.py tests/test_contract_quality_documents.py -q -rs` | `39 passed, 1 skipped` — the skip is pre-existing and environmental (`test_contract_quality_documents.py:151`: native loader requires the already provisioned Hermes interpreter), in a file this unit did not touch |
| Whitespace | `git diff --check` | clean (rc 0) |
| Python touched? | — | **Yes**: one test file (the oracle in §5). `README.md` and the evidence record are not Python. |

Full-suite and merged-tree gates are **not** claimed here: they belong to the integration
lane on the merged commit (resource pressure on this machine makes a full run
non-attributable, as recorded by LC-BLOCK and LC-RUNTIME).

## 8. Coverage of the card's required outcomes

| Card item | Check actually run | Result |
| --- | --- | --- |
| 1. Status paragraph true as of the publication, naming tag and release | §3.2 text; published-facts read in §1 | corrected; tag `v1.0.0-rc.1` and the release are named and linked |
| 1. Boundaries retained (not stable / not PyPI / not WSL2 / #261 open) | §3.3; oracle assertions in §5 | all present and unweakened; the negative control proves the denial is gone |
| 2. README's other roles intact | `git diff --numstat` (1 line), §3.3 | single-hunk change; no capability claim, registry duplication or changelog added |
| 3. No published artifact adjusted | §4.1 | only reads on the release; no asset/tag/workflow/issue mutation |
| 4. Corrected text reaches a future build's artifact | §4 build + METADATA before/after | corrected sentence present (line 44), stale sentence count 0 |
| Verification: `git diff` for the single file | §3 diff/numstat | one file, one hunk, other statements unmangled |
| Verification: wheel METADATA before/after | §4 table | quoted for both artifacts |
| Verification: doc and public-artifact scripts pass | §7 | rc 0 both |
| Verification: ruff unaffected | §7 | clean at CI scope (Python touched: the oracle) |
| Verification: `git diff --check` clean | §7 | clean |
| Verification: explicit statement on immutability | §4.1 | stated |

## 9. Limits and remaining risk

- **The published artifact remains self-contradictory.** The `v1.0.0-rc.1` wheel still
  embeds the stale sentence, and no effect allowed to this unit can change that. Issue
  #239 therefore cannot be closed by a source-only repair; it needs either a future
  published build carrying this correction or an explicit owner/steward decision about
  whether published-asset replacement is authorized. I did not read or mutate issue state.
- **`CHANGELOG.md` / `docs/**` still carry the stale wording** (§6); until a follow-up unit
  lands, the public documentation set is internally inconsistent about the publication.
- **Unit-level conclusions only:** nothing here decides the aggregate release conclusion,
  qualifies the artifact, or performs activation. LC-INT owns integration/publication and
  LC-CLOSE owns activation, rollback proof and closeout.
- **Compatibility impact of this unit:** documentation-only, plus one test assertion;
  no runtime, CLI, schema, artifact or interface behavior changed, so no compatibility
  impact is claimed beyond the correction itself.
- **No forbidden effect occurred:** no tag/release/asset/workflow/issue mutation, no push,
  no force-push or history rewrite, no publication, no credentials touched.
