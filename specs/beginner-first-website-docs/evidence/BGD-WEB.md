# BGD-WEB unit evidence

Status: Implementer self-review evidence for the grouped documentation website unit.
This record is not independent review, integrated acceptance, a release decision, a
GitHub publication claim, or proof of Pages deployment.

## Unit and source basis

- Objective Contract: `oc_844dfc12880ee967@v1`, on required base
  `9bce0d222fdf0bfc581a26e282b81b08a1418d7c`.
- Unit: BGD-WEB, covering the explicit documentation manifest, grouped routes and
  navigation, article orientation, search, fragments, responsive/no-JavaScript behavior,
  accessibility checks and website verification.
- The reviewed BGD-CONTENT changes are preserved as two discrete, patch-identical
  recovered-lineage commits: `c087de52eacf41aae1d854986ba64e743a327b2b` and
  `74cc16336d70390d5dfdc14e0d53d252034c2325`. Their original local commits
  `82a7d7bfb0138b6b6713faa3604b85aa9adcf239` and
  `954445f271c12c22dc1ea5a09bb2ac14f62ae499` were not amended, rebased or deleted.
- Website implementation was replayed without content changes as
  `8c289cd91579513803163d0e3ea13b8c89da0bbe`; its stable patch ID exactly matches the
  original local implementation commit `9f58447585fac049ac687d6c749afea0ab4ea725`.
- Supervisor review correction is isolated in website commit
  `63ba7f31e290bc1bbb46227cfabf55708ad9b9d0`: the docs index now marks the canonical
  English Markdown and English card/group-label metadata with `lang="en"`, explicitly
  identifies Spanish orientation descriptions as `es-MX`, adds static/browser
  regressions, and reconciles the current README wording without changing historical
  `website/VERIFICATION.md` records.
- Recovery was necessary because the original unit worktrees were materialized from an
  incidental unrelated checkout tip rather than the contract base. The recovered chain
  starts with the Supervisor decomposition commits on required base
  `9bce0d222fdf0bfc581a26e282b81b08a1418d7c`; the contract is an ancestor and its exact
  artifact is present. Original contaminated refs remain preserved outside the candidate
  rather than being rewritten or merged. The inherited canonical Markdown and
  `website/src/data/content.ts` remain in the content commits; the website implementation
  commit changes only its assigned website boundary.
- Project knowledge status reported `available=false` with no indexed snapshot for this
  revision. Direct source and test inspection was used as the accepted fallback.

## Delivered paths

- `website/src/lib/docs.ts`: explicit 19-record manifest, five ordered groups, strict
  tracked-corpus validation, unique `/docs/` index handling, source-relative link and
  fragment validation, revision-pinned source links, safe Markdown sanitization and
  accessible heading/code/table metadata.
- `website/src/components/DocsNavigation.astro`: shared grouped navigation with stable
  ordering, current-page semantics and source metadata.
- `website/src/pages/docs/index.astro`: beginner-oriented index, canonical index Markdown
  rendering, grouped cards, language-of-parts metadata, Spanish/English search orientation
  and explicit degraded state.
- `website/src/pages/docs/[...slug].astro` and `website/src/pages/docs/search.json.ts`:
  one article route per non-index source, group/breadcrumb/current/revision/status context,
  in-page heading navigation, within-group previous/next links and complete static search
  records.
- `website/src/pages/404.astro` and documentation CSS: manual/search recovery,
  responsive/mobile navigation, deep-link offset, visible focus, local scroll regions and
  no page overflow rules.
- `website/tests/content.test.mjs`, `website/tests/browser/docs.spec.ts`, and the
  documentation assertions in `website/tests/browser/site.spec.ts`: corpus, manifest,
  route, link, fragment, source, search, language-of-parts, navigation, accessibility,
  keyboard, mobile and no-JavaScript coverage.
- `website/scripts/capture.mjs`, `website/AGENTS.md`, `website/README.md` and
  `website/VERIFICATION.md`: representative docs captures and reconciled website guidance.

No package or lockfile change was required. No runtime/provider/profile/credential,
repository setting, remote, issue, PR, deployment or release state was changed.

## Requirement-to-evidence map

| Contract obligation | Check and observed result | Evidence location |
| --- | --- | --- |
| AC-6: every tracked Markdown page has one explicit manifest record, stable group/order/search/navigation metadata and one route; `/docs/index/` is forbidden | `npm test`: PASS, 14 tests. The generated search record count equals `git ls-files -- docs` Markdown count (19); source, slug and route sets are unique; all generated article paths exist; exactly one `/docs/` card exists and `/docs/index/index.html` is absent. Manifest mutation tests reject unknown, stale, duplicate source/slug/route, invalid slug/order and wrong navigation records. | `website/tests/content.test.mjs`; `website/src/lib/docs.ts`; generated `website/dist/docs/` |
| AC-7: source-relative/generated links, fragments, safe schemes and pinned source links | `npm test`: PASS. Build-time link handling validates repository-relative targets and local heading fragments, maps local Markdown links to generated routes, emits external repository links with the candidate revision, and rejects unsafe schemes. Generated-link and duplicate-ID checks pass. | `website/src/lib/docs.ts`; `website/tests/content.test.mjs`; generated HTML/search JSON |
| AC-8: article group/current context, return/search access, headings, fragments, within-group adjacency, mobile and keyboard behavior | `CI=1 npm run test:e2e`: PASS, 57 passed and 1 intentionally skipped across desktop/mobile Chromium. Article checks observed `Working with Aether`, `CHAPTER 3 OF 6`, current sidebar/mobile links, status/search actions, 12 walkthrough TOC links, previous `objective-contracts` and next `execution`. Direct-fragment and keyboard-focus checks passed. | `website/tests/browser/docs.spec.ts`; generated article routes |
| AC-9: title/description/group/body search, Mexican-Spanish and English terms, count/no-result/failure, no-JavaScript degradation | Browser search passed for `conocimiento`, `worktree`, and a no-result term; failed-index interception reported the load failure while retaining all five groups; no-JavaScript checks found the grouped index/navigation and article content usable, with the search panel hidden and an explicit `noscript` unavailable message. | `website/tests/browser/docs.spec.ts`; `website/src/pages/docs/index.astro`; generated `docs/search.json` |
| AC-10: desktop/mobile overflow and local code/table scrolling | `node scripts/capture.mjs`: PASS at 360, 390, 768, 1024, 1440 and 1920 pixels; all reported document widths equal viewport widths and all reported overflow arrays are empty. Browser representatives passed no-overflow checks; start page code/table regions were focusable (`tabIndex=0`) with `overflow-x:auto`. | `website/scripts/capture.mjs`; `website/test-results/visual/layout.json` (ignored generated output); `website/tests/browser/docs.spec.ts` |
| AC-11: WCAG A/AA checks on index/start/walkthrough/long reference and mobile | `CI=1 npm run test:e2e`: PASS, 57 passed and 1 intentional skip across desktop/mobile Chromium. Axe checks on `/docs/`, `/docs/start-here/`, `/docs/guides/first-objective/` and `/docs/reference/capabilities/` in both configured desktop and mobile projects reported no WCAG 2A/2AA/2.1A/2.1AA violations. The index regression additionally verifies the Spanish `es-MX` document, `lang="en"` canonical Markdown, five English group labels, five explicit `es-MX` orientation descriptions and all 19 English card title/description pairs in both projects. | `website/tests/browser/docs.spec.ts`; `website/tests/content.test.mjs` |
| AC-12: no private/opaque operational data in public artifacts | `uv run --frozen pytest -q tests/test_beginner_documentation.py tests/test_documentation.py tests/test_public_artifacts.py`: 24 passed and one known unchanged-base public-artifact failure. The only failure is `test_tracked_public_surface_contains_no_operator_paths`, reporting the pre-existing `oc_0084270d940c98d9` `absolute-user-home` and `operator-desktop-layout` findings. No new finding points to this unit; no operational state is committed. | Root test output; inherited `specs/beginner-first-website-docs/evidence/BGD-CONTENT.md`; `git diff --name-only` |
| AC-13: website guidance/verification coherence and preservation | Website guidance describes the 19-page tracked corpus, direct Markdown rendering, five groups, stabilization status, no-JavaScript behavior and required commands. README now points to the earlier owner-acceptance gate as historical while accurately identifying this docs candidate as a local same-card review item; historical `VERIFICATION.md` records remain unchanged. Landing components, artwork, motion and inherited content paths are unchanged by this unit. | `website/AGENTS.md`; `website/README.md`; `website/VERIFICATION.md`; `git diff --stat` |
| AC-14 unit portion: independently reviewable implementation and truthful evidence | The content prerequisite remains a distinct ancestor, and this unit is a separate implementation commit with a separate evidence record. Same-card Supervisor review is still required; this self-review is not approval. | `git log --oneline`; this file; native Kanban review handoff |

## Executed verification

All website commands below ran after `npm ci`. The requested scoped cleanup of ignored
`dist`, `.astro`, Playwright reports and captures was denied by the pre-tool guard as a
destructive operation; no alternate destructive cleanup was attempted. Each normal build
regenerated `dist`, and the capture/e2e commands rewrote their representative outputs.
The final normal build was restored after the Pages-mode check.

| Command or action | Observed result | Interpretation |
| --- | --- | --- |
| `npm ci` from `website/` | PASS: 320 packages added/audited; 0 vulnerabilities | Existing locked dependencies suffice; no package change was introduced. |
| Scoped generated-output cleanup | Guard denial: `git clean -fdX -- website/dist website/.astro website/test-results website/playwright-report` was classified as a destructive local operation | The denial was recorded; verification continued with the required build/test sequence and no generated output was treated as tracked evidence. |
| `npm run build` | PASS: Astro static build completed with 22 pages | Normal local output includes `/docs/`, 18 non-index article pages, 404, search JSON and the two landing pages. |
| `npm run check` | PASS: 33 files; 0 errors, warnings or hints | Astro/type diagnostics are clean. |
| `npm test` | PASS: 14 tests; 0 failed, skipped or cancelled | Content, manifest, generated-link, source and preservation checks pass. |
| First `CI=1 npm run test:e2e` attempt | Environment setup failure: port `127.0.0.1:4321` was already occupied by an earlier unit preview process | The process was identified as the prior local preview, stopped, and the exact command was rerun. This is not counted as browser qualification. |
| Rerun `CI=1 npm run test:e2e` | PASS: 57 passed, 1 intentionally skipped; 58 tests across desktop/mobile Chromium | The sole skip is the desktop-only guard on the mobile-navigation case; the same case passes in the mobile project. No failure was skipped. |
| `AETHER_PAGES=1 npm run build` | PASS: static build completed with 22 pages | Project-site base path mode builds successfully. |
| `node scripts/verify-pages-build.mjs` | PASS: GitHub Pages base-path verification passed for 22 HTML pages | Internal Pages-base links/resources resolve in the local artifact. This is local build evidence, not deployment evidence. |
| Normal `npm run build` after Pages verification | PASS: static build completed with 22 pages | Required local output was restored before inspection. |
| `node scripts/capture.mjs` | PASS: representative landing/docs captures at all configured widths; every document width matched viewport and overflow list was empty | Capture output is at ignored `website/test-results/visual/`; the JSON manifest is `website/test-results/visual/layout.json`. |
| Capture inspection | DOM/CSS inspection of the final representative routes at 390 and 1440 pixels observed viewport-equal document widths, visible grouped/search/status regions, readable in-page navigation boxes, and focusable local scroll regions. The generated PNG dimensions were verified for all eight docs captures. Pixel-level visual inspection could not be completed because the available image-analysis backend rejected each local image request (`opencode rejected the request`); no visual pass is claimed. | `website/scripts/capture.mjs`; `website/test-results/visual/layout.json`; Playwright geometry inspection output; remaining limitation below |
| `uv run --frozen python scripts/check_documentation.py` | PASS: `documentation validation passed` | Root documentation/registry coherence remains green. |
| `uv run --frozen pytest -q tests/test_beginner_documentation.py tests/test_documentation.py tests/test_public_artifacts.py` | Exit 1: 24 passed, 1 failed | The one failure is the known unchanged-base #364 public-artifact defect documented above; it is outside this unit and was not weakened or absorbed. |
| Provider-free beginner probes in isolated temporary HOME with `HERMES_HOME` unset | `aether --version`, top-level/help paths and documented JSON paths were executed. Help/version paths exited 0. Expected diagnostics were observed: `doctor --json` exit 4 (`LIFECYCLE_INTEGRITY_FAILED`/`ACTIVE_RELEASE_INVALID`), `init --dry-run --json` exit 3 (`AETHER-INIT-HERMES-PROJECTS-UNAVAILABLE`), `observe --json` exit 0 with empty state, `knowledge doctor --json` exit 1 (`COMPONENT_UNAVAILABLE`), and `version --json` exit 0 with `MANAGER_DETAIL_UNAVAILABLE` warning. | Provider-free parser and current-boundary behavior were exercised without credentials or provider calls; temporary paths and runtime state are omitted. Full command output is in the worker run, while the parent content evidence records the same interpretation. |
| `git diff --check` | PASS | No whitespace errors before the implementation commit or evidence commit. |

## Compatibility and remaining risk

Unit compatibility impact: `patch`. The change expands the static documentation reading
surface and tightens validation around an existing tracked-only renderer; it does not
change Python/runtime APIs, CLI semantics, capability registry values, product authority or
external integrations. This is unit-level compatibility evidence only; Supervisor owns the
aggregate release conclusion.

Remaining limitations and risks:

- The root focused test command remains red only because of the known unchanged-base #364
  public-artifact defect in an inherited Objective Contract. Terminal integration must
  reconcile that independently corrected baseline; this unit must not modify it.
- PNG visual inspection could not be performed through the available image-analysis backend
  in this run. Automated browser geometry, overflow, interaction and Axe checks passed;
  independent human/reviewer visual inspection remains part of Supervisor review.
- The website is a local stabilization candidate. Passing local builds, Pages-base
  verification and browser tests do not imply merge, deployment, release qualification,
  provider-backed execution or a public installation path.
- Same-card Supervisor review remains outstanding; this self-review is not independent
  acceptance.
