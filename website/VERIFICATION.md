# Aether Agents website — Local verification

## Final owner acceptance gate and GitHub Pages readiness — 2026-09-07

Status: the owner accepted the website for integration after one final copy correction
in the team diagram and explicitly authorized moving the website to `main` and publishing
it through GitHub. This record captures the final gate **before** that integration; the
remote deployment result is intentionally not claimed here.

The team-diagram caption no longer says `Trabajo que avanza y regresa`, wording that
could imply regressions. It now says `El trabajo pasa entre etapas y agentes`, matching
the intended concept: work changes according to its stage and may move through multiple
agent responsibilities. A browser regression protects the new wording and rejects the
superseded caption.

GitHub Pages preparation keeps local development at `/` while production uses the
repository project-site base `/Aether-Agents/`. Internal navigation, documentation,
images, favicon, generated Markdown links and documentation search are base-aware. The
Pages workflow builds a normal local-path candidate first, runs checks/content tests,
then builds the deployment artifact with `AETHER_PAGES=1` and verifies that every
root-local HTML resource resolves under the project-site prefix before upload.

Final pre-integration commands/results:

| Check | Result |
| --- | --- |
| `ASTRO_TELEMETRY_DISABLED=1 npm run build` | PASS, 20 static pages |
| `ASTRO_TELEMETRY_DISABLED=1 npm run check` | PASS, 32 files; 0 errors, warnings or hints |
| `npm test` | PASS, 20 tests |
| `npm run test:e2e` | PASS, 38 tests across desktop/mobile Chromium |
| `AETHER_PAGES=1 npm run build` | PASS, 20 static pages |
| `node scripts/verify-pages-build.mjs` | PASS, all 20 HTML pages use resolvable `/Aether-Agents/` production paths |
| `git diff --cached --check` | PASS after removing inherited Markdown whitespace |

At the moment this gate was recorded, the work remained staged on
`feat/website-onepage`; no merge, push or Pages deployment had yet occurred. The next
authorized operation is the integration/publishing action requested by the owner.

## Production-copy and microtype cleanup — 2026-09-07

Status: implemented and locally verified for owner review. This pass supersedes the
prototype-style clock wording described in the earlier same-day refinement record
below; that earlier section is retained as historical execution evidence.

The Development clock no longer labels itself as conceptual and no longer carries a
runtime disclaimer. Its visible center copy is now `TRABAJO AUTÓNOMO / LARGO HORIZONTE /
24 H`, and the explanatory figcaption was removed entirely. The accessible SVG title is
the neutral `Reloj de 24 horas para trabajo autónomo de largo horizonte.` The generic
diagram label `Recorrido ilustrativo` was replaced by `Flujo de trabajo`, and the
knowledge graph caption was reduced to `MAPA TÉCNICO COMPARTIDO · GRAPHIFY OPCIONAL`
instead of explaining that the visitor is looking at an example or non-live data.

Microtype on the landing was enlarged as a system rather than only in the foundations
strip. Foundations, section labels, metadata, team/process annotations, graph labels,
author handle, footer metadata and mobile overrides now use materially larger sizes;
the browser regression enforces a 14px minimum on representative editorial metadata in
both desktop and mobile projects. Decorative SVG markings remain proportionate to the
clock while the informational diagram text was also increased. Documentation keeps its
separate reading scale so code blocks and tables are not inflated by the landing-page
change.

Final commands/results for this pass:

| Check | Result |
| --- | --- |
| `npm run build` | PASS, 20 static pages |
| `npm run check` | PASS, 30 files; 0 errors, warnings or hints |
| `npm test` | PASS, 20 tests |
| `npm run test:e2e` | PASS, 38 tests across desktop/mobile Chromium |
| Production-copy regression | PASS; no conceptual/illustrative/runtime-disclaimer copy on the rendered Spanish landing |
| Editorial metadata size regression | PASS on desktop/mobile; representative metadata >= 14px |
| Responsive overflow/browser checks | PASS, including narrow viewport graph and landing checks |

The worktree remains `feat/website-onepage` at
`0913ec636ab081654065be90b021cf1c47a41619`. `website/` is still intentionally
untracked as a whole, so Git cannot provide a tracked-file diff for these files; the
source was checked through the application tests and targeted review. No commit, push,
merge, deployment or Aether runtime change occurred. The existing loopback preview on
`127.0.0.1:4321` remains available for owner review.

## Clarity, Mexican Spanish and clock refinement — 2026-09-07

Historical status: implemented and locally verified for owner review, then superseded
by the production-copy cleanup above. Plan:
`DETAIL_REFINEMENT_PLAN.md`. Current Spanish source: `COPY_REFINEMENT_MX.md`.

The autonomy illustration in Development now reads explicitly as a clock instead of an
abstract astrolabe. It uses a 24-hour face with all `00`–`23` labels, four subdivisions
per hour, two differently paced hands, clearly moving orbital decoration and localized
Spanish center copy. The clock face is drawn behind the hands and a visible center pivot
keeps both hands visually anchored; the redundant CSS transform origin was removed so
the SVG rotation uses only its explicit `280 280` center. The two orbit groups now move
at 10°/s and -7°/s instead of the previous near-static rates. Its title and caption
explicitly describe it as conceptual and state that it does not report measured runtime.
A browser regression verifies all 24 labels, no rendered label overlap, fixed hand pivots
and perceptible orbital movement in desktop and mobile layouts.

Ambiguous visual affordances were reduced rather than made artificially interactive.
The three non-clickable Development cards no longer show outbound arrows, Control no
longer places decorative plus signs beside static text, and the documentation index no
longer uses an external-link glyph for internal navigation. The current symbol grammar
is: `↗` outbound link, `→` internal navigation, `↓`/`↑` vertical navigation and
`↶`/`↳` only when the process illustration actually communicates return/direct flow.

The Spanish landing was rewritten for comprehension and natural Mexican usage while
retaining its sober editorial tone and technical meaning. The visitor-facing flow now
states more directly what the owner defines, what Aether organizes, what each role does,
how work returns for correction, what Graphify contributes, and how control/recovery
work. Graph detail explanations were also clarified. The prior wording remains in
`COPY_REFINEMENT.md`; the current candidate is separately preserved in
`COPY_REFINEMENT_MX.md`. English remains neutral and was not broadly rewritten.

Final commands/results for this pass:

| Check | Result |
| --- | --- |
| `ASTRO_TELEMETRY_DISABLED=1 npm run build` | PASS, 20 static pages |
| `ASTRO_TELEMETRY_DISABLED=1 npm run check` | PASS, 30 files; 0 errors, warnings or hints |
| `npm test` | PASS, 19 tests |
| `npm run test:e2e` | PASS, 36 tests across desktop/mobile Chromium |
| Clock-specific desktop/mobile browser regression | PASS, 24 hour labels, 2 hands, fixed pivots, perceptible orbit motion, no label overlap |
| `node scripts/capture.mjs` | PASS at 360/390/768/1024/1440/1920 px; no document or painted overflow |
| Loopback preview | HTTP 200 at `http://127.0.0.1:4321/` |

The main checkout advanced independently during website review and is currently clean at
`4771b9d00a7867b7830eca3f700c0b3eeb8c9792`. This website worktree remains on
`feat/website-onepage` at `0913ec636ab081654065be90b021cf1c47a41619`; no merge, commit,
push, deployment or runtime activation occurred. `website/` is still intentionally
untracked as a directory, so normal tracked-file `git diff` evidence is not presented as
coverage for this pass; the application checks above operate on the actual website files.

## Final artwork, motion and post-restart verification — 2026-09-07

Status: implemented and locally verified; no outstanding verification from the host
shutdown. Owner visual/content acceptance remains required before any integration.
Plan: FINAL_POLISH_PLAN.md. Copy source: COPY_REFINEMENT.md.

The new Morfeo image is used by the opening, the selected abstract ether image is used
by the authorship finale, and the knowledge illustration remains SVG/HTML with masked
classical margins. Opening/closing ambient lighting, sparse particles and bounded
pointer parallax use the same visibility/pause/reduced-motion contract as the graph.
All four preserved PNGs are present on the DevSpace host and retain their recorded
hashes. The current hero/finale native-size derivatives preserve source pixels; their
1672 × 941 source resolution is not described as 4K or 8K.

The machine shutdown stopped the local preview. After access returned, the pending
`knowledge.ts` pageshow-listener correction was rebuilt and verified. No additional
application-code change was required. Added `tests/browser/history.spec.ts` to prevent
regression: it uses the full Chromium binary with bfcache enabled, navigates to the
documentation and back, asserts `pageshow.persisted` and unchanged document identity,
and repeats restoration three times. Thus a fresh page load cannot falsely satisfy
the test. Graph selection resets coherently, handlers do not multiply, all motion
continues when permitted, and pause/reduced-motion survives restoration.

Commands executed against the final application source:

| Check | Result |
| --- | --- |
| `ASTRO_TELEMETRY_DISABLED=1 npm run build` | PASS, 20 static pages |
| `ASTRO_TELEMETRY_DISABLED=1 npm run check` | PASS, 30 files; 0 errors, warnings or hints |
| `npm test` | PASS, 17 tests; no failures or skips |
| `npm run test:e2e` | PASS, 34 tests across desktop/mobile Chromium; no failures or skips |
| Real browser-cache history tests | PASS, 4 cases; repeated actual restores and paused/reduced-motion restores |
| `node scripts/capture.mjs` | PASS, 360/390/768/1024/1440/1920px; no horizontal painted/document overflow |
| `npm audit --omit=dev` | 0 vulnerabilities reported at execution time |
| `uv run --frozen python scripts/check_documentation.py` | documentation validation passed |
| Original artwork SHA-256 | All four preserved originals match their recorded hashes |
| `git diff --check` and `git diff --cached --check` | PASS; no tracked/staged changes |

Newly captured desktop opening and finale, mobile knowledge and mobile finale images
were actually inspected. Text is legible, the selected final background is visible,
and the author profile link is present. Screenshot/report files remain ignored under
`test-results/` and `playwright-report/`. Automated accessibility checks passed for the
tested Spanish/English landings and documentation routes; this is not a complete WCAG
certification, a physical-device test, or evidence about Firefox/Safari.

Worktree HEAD stayed `0913ec636ab081654065be90b021cf1c47a41619` on
`feat/website-onepage`. Main stayed clean at
`677df63fc0fa0d8be9349e8f35ed3202d1b3bf9b`, without a website directory. Only the website
workstream was modified. No commit, push, merge, deployment, service installation or
Aether/Hermes activation occurred. The full Python suite was not rerun for these
website-only lifecycle tests; earlier runtime regression results below are historical.

The loopback preview has been restarted for owner review at `http://127.0.0.1:4321/`.
It is a development process, not a boot-time service. Restart it with `npm run preview`
from website after a future host shutdown, and build first after source changes.

## First owner-review polish — 2026-09-07

The scoped plan is in POLISH_PLAN.md and the new Spanish review candidate is in
COPY_REFINEMENT.md. The previous prototype evidence below remains historical.

Implemented: no visible sketch numbering/FIG annotations, more direct Spanish with
unchanged main headlines and hero definition, @DarkArty07 linked beside the author,
lossless native-size hero, and GSAP 3.15.0/MotionPathPlugin for an interactive SVG
knowledge map. The map supports pointer highlighting, touch/keyboard selection,
context explanations, query-and-return pulses and soft lighting. The original approved
graph contributes masked classical margins, not flattened text or graph geometry.
The scene is explicitly illustrative, not live product telemetry or shared private memory.

Final commands and results:

| Check | Result |
| --- | --- |
| `npm run build` | PASS, 20 static pages |
| `npm run check` | PASS, 26 files; 0 errors, 0 warnings, 0 hints |
| `npm test` | PASS, 17 tests; current exact-copy, links, assets and lossless pixel equality |
| `npm run test:e2e` | PASS, 24 tests across desktop/mobile Chromium |
| `node scripts/capture.mjs` | PASS at 360, 390, 768, 1024, 1440, 1920px; document width matches viewport, no painted overflow |
| `npm audit --omit=dev` | 0 vulnerabilities reported at execution |
| Original PNG hashes | Both approved originals unchanged |
| Preview HTTP | 200 at the existing loopback port 4321 |
| `git diff --check` | PASS |

The first capture found narrow-viewport SVG overflow; this was fixed by clipping the
drawing inside its scene. Added a regression for both static and animated layouts,
and made the capture command fail on real overflow. No checks were dropped. The full
site suite still checks no-JS content, local-only requests, language navigation, real
team/process animation, and automated WCAG A/AA checks on selected landing/docs pages.

Actually inspected rendered desktop hero, desktop/mobile knowledge and desktop
authorship screenshots using image reads; inspected the final desktop knowledge
capture after removing residual baked-in text from the background margins.

No Safari/Firefox or independent human acceptance is claimed. The original images are
1672 × 941: lossless encoding cannot invent more detail. Full-size hero is about 2.1 MiB;
the graph's full-size decorative margin derivative is about 252 KiB and loads lazily.
The graph's nodes, paths and labels are vector/HTML rather than upscaled raster content.

Only website/ was changed. Worktree HEAD remains 0913ec6; main remained clean at
677df63 throughout this pass, although its remote-tracking ref advanced independently.
No main integration, branch commit, push, runtime change or deployment occurred.
Two additional PNGs, aether-ether-finale.png and aether-morfeo-refined.png, appeared in
assets/images during the work. They were not created, modified, deleted or adopted by
this pass; both are also 1672 × 941. Their presence does not change the selected artwork.
No new Aether runtime qualification was run: this change is confined to the website.

## Initial prototype evidence (historical)

Date: 2026-09-06 (local review session).
Status: local implementation complete; owner visual/content review pending.
Branch: `feat/website-onepage`.
Source baseline: `0913ec636ab081654065be90b021cf1c47a41619`.

## Delivered scope

The implementation follows the plan written before frontend work. It contains the
eight approved one-page sections in Spanish, an English adaptation, two original
approved illustrations with checked hashes and optimized derivatives, the animated
astrolabe, bidirectional role packets, a distinct process/correction diagram, restrained
knowledge motion, and text-led sections 05–07. Section 07 is authorship/open source.

The separate documentation site renders all 16 tracked canonical Markdown documents
without duplicating the manual. The source text stays in English, visibly identified.
The index, local search, relative links, heading anchors, source-revision links, mobile
chapter navigation and adjacent-page links are implemented. The build produces 20 HTML
pages plus the static search index and local assets.

## Commands actually executed

| Check | Observed result |
| --- | --- |
| `npm run build` | PASS; 20 static HTML pages, no server-side runtime required |
| `npm run check` | PASS; 23 files, 0 errors, 0 warnings, 0 hints |
| `npm test` | PASS; 15 tests, 0 failed, 0 skipped |
| `npm run test:e2e` | PASS; 16 Chromium browser tests across desktop and mobile |
| `node scripts/capture.mjs` | PASS; 360, 390, 768, 1024, 1440, 1920px layouts with no horizontal overflow |
| `npm audit --audit-level=moderate` | 0 vulnerabilities reported at execution time |
| `uv run --frozen python scripts/run_tests.py` | 1052 passed, 41 skipped, 0 failed; 311.22 seconds |
| `uv run --frozen python scripts/check_documentation.py` | documentation validation passed |
| `git diff --check` | PASS; no tracked source diff outside website |
| Source/config/design text inspection | UTF-8, final newlines and whitespace checks passed |
| Loopback preview HTTP request | `200 OK` at `http://127.0.0.1:4321/` |

The repository suite's 41 skips were its existing optional-dependency/qualification
conditions. No tests were removed, weakened or explicitly skipped by this change.
The repository suite is regression evidence, not a live-agent qualification or a website
coverage claim; the dedicated website tests exercise the new frontend.

## Website coverage

- Every approved Spanish text block in 00–07 is compared against the rendered HTML,
  normalizing whitespace only. The wording is not rewritten for presentation.
- The two approved original PNG SHA-256 values are checked before derivative generation.
  Self-hosted font license texts accompany the generated font assets.
- All built local links, local resources, heading anchors and unique IDs are checked.
- Both full landing languages, section preservation on language switch, mobile menu,
  documentation search (including empty/no-result/reset states) and linked reading work.
- The real requestAnimationFrame clock is observed through branching, reverse return
  and review-to-execution correction phases. Pause freezes animation and persists
  through reload; system reduced motion is honored. Essential copy survives disabled JS.
- Keyboard skip navigation is exercised. Code and table scrolling regions are focusable.
- Axe WCAG 2 A/AA and 2.1 A/AA scans found no violations on the two landings, the docs
  index and the project-knowledge guide in both tested viewports. This is automated
  evidence for those routes, not a claim of complete WCAG certification.
- Browser request inspection found no remote scripts, fonts, images, analytics or
  runtime endpoints. Outbound project references remain ordinary user-activated links.

## Visual review

Desktop/mobile hero, complete desktop composition, development/astrolabe, role diagram,
process diagram, mobile vertical process and documentation index screenshots were
inspected. The selected illustration preserves Morfeo's face on mobile; the sections
retain their typographic hierarchy and do not require animation to be understood.

Screenshots and the layout report are under ignored `test-results/visual/`; browser
reports are under ignored `playwright-report/`. Element-only screenshots deliberately
hide sticky/fixed chrome during capture to avoid viewport-resize overlay artifacts;
the actual site keeps its header, pause control and keyboard skip link.

## Corrections made during verification

1. Corrected document-root resolution during Astro prerendering: bundled module URLs
   are not reliable repository paths; the build now resolves the current Git root.
2. Added missing Node types and excluded generated browser-report bundles from the
   project type-check scope, without excluding application or test source.
3. Restored the accessible literal foundation separator and a word boundary in the hero
   name. All approved source-copy checks now pass.
4. Made documentation code blocks and overflowing tables keyboard-focusable after
   the first accessibility scan identified those scroll regions.
5. Replaced the test harness's late-installed synthetic animation clock with observation
   of the real clock. The forward/branch/reverse/rework assertions remain required.
6. Recovered the missing 00 artwork onto the actual user-machine worktree via DevSpace;
   a previous container copy was not evidence of a user-machine asset. Both originals
   are now present and hash-verified on the user machine.

## Limits and pending review

- Browser validation used Playwright Chromium desktop/mobile emulation, not physical
  mobile devices, Safari/WebKit or Firefox. The host OS uses Playwright's Ubuntu fallback
  browser build; it ran successfully but is not Playwright's officially supported host.
- An independent read-only Codex review was attempted through DevSpace. It failed with
  `PROVIDER_EXECUTION_ERROR` and returned no review report. No independent-review pass
  is claimed. The checks above and direct visual inspection were completed by the
  implementing assistant.
- The English landing is an adaptation for owner review. The technical manual is not
  translated; its existing status statements refer to the inspected source revision.
- The artwork and animations illustrate the method; they are not interactive access to
  a real project graph, live runtime telemetry, measured hours, or throughput evidence.
- No production hostname, deployment, publishing workflow, account service or external
  analytics was added. A production deployment may require its own base-path/URL policy.
- The remote tracking branch advanced seven commits during this work. Local main and
  the website worktree remain on the agreed baseline; no fetch/pull/rebase/merge was
  performed to absorb unrelated updates. Integration should reconcile the then-current
  main only after owner approval.

## Isolation and review handoff

The actual main checkout was checked after implementation: clean at the original
baseline, no `website/` directory and no website files tracked there. The website
worktree remains on `feat/website-onepage`; its new files are uncommitted. No main
modification, commit, push, merge, deployment or Aether/Hermes activation occurred.

Preview routes on the user's machine:

```text
http://127.0.0.1:4321/
http://127.0.0.1:4321/en/
http://127.0.0.1:4321/docs/
```

The loopback preview was left running for the owner. If stopped, restart from `website/`
with `npm run preview`; after edits, run `npm run build` first. All installation/build
commands and source locations are documented in README.md. Owner corrections and
explicit integration approval are the next gates, not automatic publication.
