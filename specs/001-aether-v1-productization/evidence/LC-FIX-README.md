# LC-FIX-README Evidence — public README status corrected to the published RC (#239)

**Unit:** LC-FIX-README (task `t_191474c2`, Implementer; same-card Supervisor review requested — round 2 after a steward-directed bounded extension, §6)
**Objective Contract:** `oc_3397f9f05d780f8e@v1` (SHA-256 `4d4c7650bf8ea93fc7cffe3d87f7f974e172d66cefcf6a74a2d83051568a4879`)
**Canonical breakdown:** `specs/001-aether-v1-productization/tasks.md` (read-only for this unit)
**Base tip before the change:** `748aa24` (`release: Aether 1.0.0-rc.1 lifecycle, maintained-fork runtime and prerelease (#442)`)
**Branch:** `aether-agents-2/t_191474c2-lc-fix-readme-public-readme-status-must`
**Delivered change:** `README.md` (1 hunk, line 5), `CHANGELOG.md` (1 hunk, line 3, §6.1), `docs/reference/limitations-and-troubleshooting.md` (1 hunk, line 17, §6.2), `tests/test_public_artifacts.py` (coupled oracle, disclosed in §5), this record
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
`t_191474c2`, and in the review request. (Round 2's writable surface is the steward-extended set
recorded in §6; no further `tests/**` change was made in that round, §6.3.) A
`git grep -n "test_readme_is_a_current_beta_portal"`
finds no other pin (only `specs/001-aether-v1-productization/evidence/LC-DOCS.md:153`, a
frozen record of another unit, and the test definition itself), and no workflow or coverage
lane names that test node.

## 6. Neighbouring statements — class sized, correction extended on steward direction (round 2)

**Review history stated rather than silently reversed.** The first delivery (`38d2e6d`) reported
`CHANGELOG.md:3` and `docs/reference/limitations-and-troubleshooting.md:17` here as *audited but
not changed*, on the grounds that `CHANGELOG.md` and `docs/**` are named out of the card's writable
surface and that re-wording a released changelog entry is a documentation-authoring decision. Both
were real instances of the same defect class. On review, the design steward (#239, 2026-09-15)
directed that the bounded source correction be extended to exactly these two files, and
Supervisor's changes request carried the same scope: extend to the two files, leave
`docs/index.md:3` as-is (confirmed accurate), add no requirement to the README. The earlier
disposition was therefore **overridden by authority**; this section replaces it.

### 6.0 Class sizing (re-measured here, not inherited from the review)

```
git grep -n -E "not yet published|unpublished here|no release candidate has been published" \
  -- . ':!specs/001-aether-v1-productization/evidence/LC-FIX-README.md'
```

- Before this round: `README.md:5` (already repaired in §3), `CHANGELOG.md:3`, and
  `docs/reference/limitations-and-troubleshooting.md:17` — three tracked hits, no others.
- After this round: exactly one hit, `tests/test_public_artifacts.py:141`
  (`assert "no release candidate has been published" not in readme`) — the negative control, not a
  claim. The class is closed.

### 6.1 `CHANGELOG.md:3`

```
before: ## 1.0.0rc1 — release candidate (pre-stable, not yet published)
after:  ## 1.0.0rc1 — release candidate (pre-stable, published but not accepted for activation)
```

`git diff --numstat` → `1 1 CHANGELOG.md`; the rest of the entry is byte-identical.

Temporally robust: "published but not accepted for activation" is the durable state — LC-INT's
recorded lane verdict is *published but NOT accepted; not eligible for activation*, and the
published release body carries that warning. No time-bound promise was introduced: no "not yet",
no "will be published", no "rc.2 pending", no "to be superseded".

**Sweep of the rest of the rc1 entry (lines 1–41) — what was checked and what was found:**

| Claim in the entry | Verdict |
| --- | --- |
| `:5–7` release identity (`1.0.0rc1`, annotated tag/prerelease `v1.0.0-rc.1`, `major`/`publish`/`prerelease`, `VERSION` as the single source) | accurate; unchanged |
| `:9–18` bundle-tool description ("Added `scripts/release_bundle.py`…") | past-tense history of the entry's own work; unchanged |
| `:19–26` "Qualified the bundle before publication…" | past tense and consistent with the published state; unchanged |
| `:27–34` release-workflow reconciliation | describes what this entry reconciled; unchanged. The separate question of whether `.github/workflows/release.yml` is valid at the tagged commit is a **different defect class**, owned by LC-FIX-RELWF `t_5cd52e79` / [#445]; it was deliberately not absorbed here |
| `:35–41` pre-stable non-claims (not stable `1.0.0`, no package-index publication, WSL2 unverified, #261 open) | accurate; retained in substance |

### 6.2 `docs/reference/limitations-and-troubleshooting.md:17`

The full row, before and after (`git diff --numstat` → `1 1`, no other line in the 53-line file
changed):

```
before: | Release-candidate scope | The authorized `1.0.0rc1` / `v1.0.0-rc.1` milestone is pre-stable and unpublished here. It is not stable `1.0.0`, not a package-index publication and not WSL2-qualified. | Treat `release_channel = prerelease` as a bounded milestone only; issue #261 remains open with the stable, PyPI/OIDC and WSL2 gates outstanding. |

after:  | Release-candidate scope | The authorized `1.0.0rc1` / `v1.0.0-rc.1` milestone is pre-stable; its annotated GitHub prerelease `v1.0.0-rc.1` is published from this repository at the tagged commit without being accepted for activation. It is not stable `1.0.0`, not a package-index publication and not WSL2-qualified. | Treat `release_channel = prerelease` as a bounded milestone only; never read the publication as acceptance and do not activate it; issue #261 remains open with the stable, PyPI/OIDC and WSL2 gates outstanding. |
```

All four boundaries survive in the same row (not stable / not package-index / not WSL2-qualified /
#261 open with the three gates), and the row gains the true publication fact plus the
published-but-not-accepted disposition.

**Sweep of the whole file — what was checked and what was found:**

- `:3` page preamble ("does not turn a candidate interface, package source file, or historical
  qualification artifact into a release/readiness claim") — accurate; unchanged.
- `:11` "installed project-aware launch is not fully qualified" — about the launcher, not the
  milestone; unchanged.
- `:23` "…and public release qualification remain outside this local build" with "do not invoke
  providers or publish" — a statement about what a *local build's* evidence is, not a claim that
  the milestone is unpublished; still true; unchanged.
- `:9–22, :24–53` every other row, the provider-free diagnostics, the update/rollback paragraph,
  policy denials and preservation rules — no publication-state claim of this class; unchanged.

### 6.3 Deliberately not changed, and the reasoning the review asked for

- `docs/index.md:3–4` ("its release path is not qualified") — the steward confirmed this remains
  accurate and explicitly scoped the extension away from it; unchanged.
- **No new content pin for the two files.** The review asked for a reason if one were added; it is
  not, and the reason is the §5 defect itself: `pyproject.toml` declares
  `readme = "README.md"` only, so only the README is embedded in distribution metadata and only the
  README needs a byte-level guard tied to the artifact. Pinning a sentence-level changelog heading
  or limitations row would freeze editorial wording rather than guard the defect class, and a
  content pin that encodes a status sentence is exactly what had to be inverted in §5. No
  assertion was added or modified in `tests/**` in this round.
- No other file was touched: `VERSION`, `pyproject.toml`, workflows, `src/**`, other tests, other
  units' evidence and issue state are all untouched by this round.

## 7. Gates at the delivered tip (re-run after the round-2 extension)

| Check | Command | Result |
| --- | --- | --- |
| Documentation registry | `uv run --frozen python scripts/check_documentation.py` | `documentation validation passed` (rc 0) |
| Public-artifact path scan (tracked surface) | `uv run --frozen python scripts/check_public_artifacts.py` | `public artifact path scan passed: tracked surface + 0 artifact(s)` (rc 0) |
| Public-artifact scan including the built wheel | `… check_public_artifacts.py --root . --artifact /tmp/lcfixreadme-dist3/aether_agents-1.0.0rc1-py3-none-any.whl` | `public artifact path scan passed: tracked surface + 1 artifact(s)` (rc 0) |
| Ruff lint (CI scope) | the exact 12-path list `.github/workflows/policy.yml` passes to `ruff check` | `All checks passed!` (rc 0) |
| Ruff format (CI scope) | same path list, `ruff format --check` | `160 files already formatted` (rc 0) |
| Focused tests | `uv run --frozen pytest tests/test_public_artifacts.py tests/test_documentation.py tests/test_contract_quality_documents.py -q -rs` | `39 passed, 1 skipped` — the skip is pre-existing and environmental (`test_contract_quality_documents.py:151`: native loader requires the already provisioned Hermes interpreter), in a file this unit did not touch |
| Whitespace | `git diff --check` | clean (rc 0) |
| Wheel build (reach proof, §4) | `uv build --wheel --out-dir /tmp/lcfixreadme-dist3` | `aether_agents-1.0.0rc1-py3-none-any.whl` sha256 `4d244eb54fff2ca8f51938b2e45ea4e6c4610a3edc48141c9a6e1b8bec7534a4` — **identical** to the round-1 build, so the extension cannot reach the artifact bytes |
| Python touched in round 2? | — | **No**: only `CHANGELOG.md` and the limitations doc changed in this round. Round 1's Python change (the oracle in §5) is byte-identical to `38d2e6d`, as is `README.md` (§7.1) |

### 7.1 Byte identity of the round-1 surface (the review asked explicitly)

`git diff --stat 38d2e6d -- README.md tests/test_public_artifacts.py` is **empty** — the README and
the test oracle were not touched in round 2:

| File | sha256 | vs `38d2e6d` |
| --- | --- | --- |
| `README.md` | `761a02e868f41fcabb6d60c9000669f22446b582c7d67a6ef2f4ab42c6d36791` | unchanged |
| `tests/test_public_artifacts.py` | `7ed0adb88cf52e1d9db480e8bdc147cca71f8431f3bd511a01901526d1c80551` | unchanged |

Files changed in round 2: `CHANGELOG.md` (`1 1`), `docs/reference/limitations-and-troubleshooting.md`
(`1 1`), and this record.

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
| Round 2 (steward/supervisor): extend to the two named files | §6.0 class-sizing grep, §6.1 and §6.2 diffs | both corrected; class closed (the only remaining hit is the negative control) |
| Round 2: temporally robust wording | §6.1, §6.2 wording review | states the published fact and the not-accepted disposition; no "not yet"/"will be published"/"rc.2 pending"/"to be superseded" |
| Round 2: no further widening | §6.3 | `docs/index.md:3–4` unchanged; no README requirement added; no assertion added in `tests/**` |
| Round 2: sweep each file, not only the flagged line | §6.1 and §6.2 sweep lists | every other claim in both files checked and classified |
| Round 2: record must not claim the files were untouched | this §6 | replaced, with the earlier disposition and the overriding directive recorded |
| Round 2: no new content pin (reason required if added) | §6.3 | not added; reason stated (`readme = "README.md"` only is embedded in metadata) |
| Round 2: README bytes and oracle bytes unchanged | §7.1 | sha256 `761a02e8…` / `7ed0adb8…`, `git diff --stat 38d2e6d` empty |

## 9. Limits and remaining risk

- **The published artifact remains self-contradictory.** The `v1.0.0-rc.1` wheel still
  embeds the stale sentence, and no effect allowed to this unit can change that. Issue
  #239 therefore cannot be closed by a source-only repair; it needs either a future
  published build carrying this correction or an explicit owner/steward decision about
  whether published-asset replacement is authorized. This unit proposes no remedy and
  promises no future publication: that disposition is Supervisor/owner-owned. I did not
  read or mutate issue state.
- **The neighbouring stale statements are corrected in canonical source** (§6), including the two
  the design steward named; the public documentation set no longer denies the publication. The
  only remaining inconsistent bytes are the immutable published assets of §4.1.
- **Unit-level conclusions only:** nothing here decides the aggregate release conclusion,
  qualifies the artifact, or performs activation. LC-INT owns integration/publication and
  LC-CLOSE owns activation, rollback proof and closeout.
- **Compatibility impact of this unit:** documentation-only, plus one test assertion;
  no runtime, CLI, schema, artifact or interface behavior changed, so no compatibility
  impact is claimed beyond the correction itself.
- **No forbidden effect occurred:** no tag/release/asset/workflow/issue mutation, no push,
  no force-push or history rewrite, no publication, no credentials touched.
