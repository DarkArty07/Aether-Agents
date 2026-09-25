# PAGES-501-INT — Integration and closeout evidence

**Unit:** `PAGES-501-INT` terminal integration card, role Supervisor (Aether).
**Authority:** Objective Contract `oc_ce1f17ebbb4968b4@v1`
(SHA-256 `d4812b5ba1fd8c36663f3f8a24453ff48f42fabdc4c54cc9da1225a7ad49ebee`), base commit
`1b0d3a36d98e29125191798a5edf867b1c4097ce`, related Issue `#501`.
**Supervisor breakdown:** `specs/001-aether-v1-productization/tasks-501.md` at
`ee4db72cb5643955851226eb18bc45b13a4bc0fa`.
**Publication boundary:** this record is written by the integration lane before publication.
Merge revision, automatic Pages run and live readback receipts cannot be observed yet and are
therefore **not** claimed here; they are recorded in pull request `#503` and in the Issue `#501`
closing comment and terminal board handoff after they actually occur.

---

## 1. Composed integration revision

| Element | Identity |
| --- | --- |
| Contract base | `1b0d3a36d98e29125191798a5edf867b1c4097ce` |
| Supervisor breakdown commit | `ee4db72cb5643955851226eb18bc45b13a4bc0fa` |
| Reviewed implementation unit (`PAGES-501-MAP`, card `t_c2fd26dc`) | `57852d2da4273f2d780d5848086ff79c682f0cba` (single commit) |
| Integration merge preserving the unit commit individually | `0706b9c8188227f97fb1aef868d3a783ea244591` |
| Integration branch | `aether-agents-2/t_9f59977b-supervisor-verify-and-decompose-objectiv` |
| Pull request | `#503`, base `main` |

The reviewed unit commit `57852d2d` remains individually inspectable; the integration merge was
not squashed, amended, rebased or otherwise rewritten.

Diff of the integration branch against `origin/main` `4c1af201c18ced73235d7b49f22a32123c46fb22`:

- `.aether/objective-contracts/oc_ce1f17ebbb4968b4/v1.md` — required contract materialization (added).
- `.github/workflows/policy.yml` — one literal line registering the contract path in the non-specs
  base manifest (required by the repository's own policy lane; not a workflow behavior change).
- `specs/001-aether-v1-productization/tasks-501.md` — Supervisor execution breakdown (added).
- `specs/001-aether-v1-productization/evidence/PAGES-501.md` — unit verification record (added).
- `website/src/lib/docs.ts` — the production change: two curated entries (added).

The canonical contract file's SHA-256 in the composed tree remains
`d4812b5ba1fd8c36663f3f8a24453ff48f42fabdc4c54cc9da1225a7ad49ebee`.

## 2. Inherited red Pages run versus the candidate result

This distinction is the reason the objective exists and must not be conflated:

| | Inherited state | Candidate state |
| --- | --- | --- |
| Revision | `4c1af201c18ced73235d7b49f22a32123c46fb22` (`main` at base) | integration branch, composed revision `0706b9c8` |
| Pages run | `35800534897` — `build` failed at `Test content and links`; `deploy` skipped | not yet observed; recorded in pull request `#503` and the Issue `#501` closing comment after the automatic push-to-`main` run |
| Website content oracle | `website/tests/content.test.mjs` failed: `src/lib/docs.ts` described 17 of 19 tracked guides | same oracle passes byte-untouched: 20 of 20 |
| Live site | `docs/search.json` held 17 records; both guide routes returned HTTP 404 | not yet observed; read back after deployment |

A green pull request, or any earlier Pages PASS on a different revision, is explicitly not
substituted for the post-merge deployment receipt.

## 3. Integrated gates on the composed revision

Executed by the integration lane on the composed revision above; environment: Linux (WSL2),
Node `22.23.2`, npm `10.9.8`, uv `0.12.15`.

### Website gates (`website/`)

| Command | Observed result |
| --- | --- |
| `npm ci --include=dev --include=optional` | locked install, 0 vulnerabilities |
| `npm run build` | 23 page(s) built, exit 0 |
| `npm run check` | 32 files, 0 errors, 0 warnings, 0 hints |
| `npm test` | `1..20` — pass 20, fail 0, skipped 0 |
| `npm run test:e2e` | 38 passed (1.5m), real desktop + mobile Chromium |

Built-artifact readback at the same revision:

- `dist/docs/search.json` holds 19 records; both repaired slugs carry their curated description and
  neither falls back to the document title.
- Reading-order positions are 6 (`guides/objective-plans`, between `guides/project-initialization`
  and `guides/objective-contracts`) and 14 (`guides/morfeo-tool-configuration`, between
  `guides/policy-and-recovery` and `reference/cli`).
- The rendered documentation index and the guide-page sidebar navigation were compared against the
  search index: the three surfaces agree on the same order.
- Both repaired routes exist in the built output and their internal links resolve.

### Repository controls (repository root)

| Command | Observed result |
| --- | --- |
| `git diff --check 1b0d3a36...HEAD` | exit 0 |
| `uv run --frozen python scripts/check_documentation.py` | documentation validation passed |
| `uv run --frozen python scripts/check_public_artifacts.py --root .` | passed (tracked surface + 0 artifacts) |
| `uv run --frozen python scripts/run_tests.py -- tests/test_public_artifacts.py tests/test_documentation.py -q` | 27 passed |
| `tests/test_public_artifacts.py::test_canonical_base_manifest_matches_tracked_non_specs_files` | 1 passed (manifest oracle) |
| Protected policy step `Validate accepted R0 design baseline`, extracted verbatim from `.github/workflows/policy.yml` and executed locally | exit 0 (covers balanced fences and resolving relative links for every tracked Markdown file) |
| `uv run --frozen python -m compileall -q` (policy scope) | exit 0 |
| `uv run --frozen mypy src/aether_agents` | Success: no issues found in 69 source files |
| `uv run --frozen ruff check` / `ruff format --check` | all checks passed / 165 files already formatted |
| `uv build` + `scripts/check_public_artifacts.py` on both artifacts | wheel and sdist built; artifact scan passed |

Protected CI required contexts on pull request `#503` (`pull-request-target`, `policy` 3.11/3.12/3.13,
`observation-qualification` 3.11/3.12/3.13) belong to the pull request record; their final state at
the merge revision is reported in that record and in the terminal board handoff.

## 4. Stop conditions re-checked before publication

| Stop condition | Observed at integration |
| --- | --- |
| Current `main` still carries the defect | yes: at `4c1af201` the map held 17 keys against the 19-document corpus, missing exactly the two guides |
| Active PR or worker changing `website/src/lib/docs.ts` concurrently | no: `#492` had no pull request; PR `#375` remained `CONFLICTING`, unmodified since 2026-09-10, and touches a different scope |
| Tracked corpus changed (for example by merged `#492` docs work) | no new tracked guides since the base; corpus still 19 documents and the repaired map now agrees exactly in both directions |

## 5. Preservation

- `website/tests/content.test.mjs` (the bidirectional oracle), `website/package.json` and
  `website/package-lock.json` are byte-untouched; no check was weakened, skipped or replaced by a
  literal count.
- No change was made to `docs/**`, other website sources, dependencies, workflow behavior, Pages
  configuration, release identity or the live installation.
- Concurrent and unrelated work preserved: the unpublished two-entry candidate in the
  `morfeo-issue-501` worktree, PR `#375`, `#492`, the owner's primary checkout, and other sessions'
  worktrees and branches.
- No credential acquisition or widening, no settings change, no check bypass, no force push and no
  history rewrite occurred in this lane.

## 6. Acceptance trace

| Criterion | State at this record | Where the final receipt lives |
| --- | --- | --- |
| AC1 | Satisfied: 19 map entries equal the 19-document corpus in both directions through the untouched oracle, both repaired entries carry descriptions grounded in their guides, order as decided | this record, §3 |
| AC2 | Satisfied: both routes built, curated descriptions in the search index, internal links resolve, real desktop + mobile browser E2E passed (38) | this record, §3 |
| AC3 | Satisfied locally: build/check/test/test:e2e with actual counts and environment; repository, whitespace, documentation and public-artifact controls green | this record, §3; protected PR checks in pull request `#503` |
| AC4 | Pending publication: merge revision, automatic Pages run on that revision and live docs routes/search readback | pull request `#503` comments, Issue `#501` closing comment, terminal board handoff |
| AC5 | Pending AC4: Issue `#501` disposition, and preservation of unrelated dirty files, installation, profiles, boards, other PRs, release identities and credentials | Issue `#501`, terminal board handoff |

## 7. Release conclusions

Kept separate from one another and from the compatibility evidence:

- `release_impact = patch` — a compatible correction to published documentation-site content
  (two curated map entries). No public interface, dependency or configuration contract changed.
- `release_action = defer` — this objective performs no release preparation: no version bump, no
  changelog release entry, no tag, no package publication.
- `release_channel = none` — the only external effect is the repository's own automatic Pages
  deployment of the existing site, which is documentation hosting rather than a release channel.

A merge is not a release, and a green Pages run is not a release qualification.

## 8. Limits

- Website gates were measured on a WSL2 host with Playwright's bundled Chromium headless shell, not
  on physical devices, Safari/WebKit or Firefox.
- Build and test durations vary between runs; page, file and test counts above are the measured
  values at the composed revision.
- The merged result, the Pages run and the live site are separate observations and are only reported
  once actually observed; no placeholder or anticipated receipt appears in this record.
