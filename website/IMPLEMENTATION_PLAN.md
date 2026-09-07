# Aether Agents — Website implementation plan

Status: implemented and locally verified; owner review required before integration.

The subsequent owner-review refinements are scoped in [POLISH_PLAN.md](POLISH_PLAN.md).
That amendment authorizes supporting-copy changes, hidden numbering and locally bundled
GSAP for the knowledge graph; it supersedes the original native-only animation choice.
Baseline: `0913ec636ab081654065be90b021cf1c47a41619`.
Branch: `feat/website-onepage`.

## Authority and scope

The owner closed the section-by-section design and authorized autonomous creation,
first planning and then implementation. Keep all work in this worktree. Do not merge,
commit, push, publish, deploy, activate Aether/Hermes, change providers, or modify main.
The website is a presentation surface, not a new agent runtime or hosted service.

The approved literal Spanish copy in HOMEPAGE_PROPOSAL.md and the conversation is the
source. Section 04 uses the previously proposed and accepted Spanish knowledge copy.
Section 07 is AUTHORSHIP AND OPEN SOURCE, not the superseded beta/1.0 roadmap section.
The approved BETA metadata in 00 stays unchanged. Only two raster illustrations are
used: the Morfeo/ether hero and the simplified knowledge graph. No control-room image.

## Implementation decisions for the review candidate

- Astro static output: one Spanish landing at `/`, an adapted English landing at `/en/`,
  a separate documentation index and pages at `/docs/`, and a useful 404 page.
- Plain CSS and native SVG/JavaScript animation; no React hydration, WebGL, external
  animation engine, analytics, account system, model calls, or artificial live metrics.
- Scoped Node package and lock inside `website/`; do not modify Python dependencies.
- Self-hosted open-licensed display, body and monospace fonts through Fontsource.
- Native scrolling, working anchors, keyboard navigation, visible focus, reduced-motion
  support and a persistent pause control. Content remains readable without JavaScript.
- Documentation reads only the existing tracked `docs/*.md` / `docs/**/*.md` corpus at
  build time. The canonical English text stays English and is clearly labeled; do not
  invent translations of the technical manual or copy private runtime files.
- Transform documentation links into local routes when available and revision-pinned
  public repository links otherwise. Add a local browser-side documentation search.
- Spanish first and then English adaptation. Preserve proper names and approved English
  technical metadata. Navigation and small controls are implementation wording.
- Local preview bound to loopback only. Public domain, canonical production URL and
  deployment remain deliberately unset until owner approval.

## Sequence

### 1. Reconcile inputs

Verify branch/base, instructions, exact copy, current documentation and actual local
assets. Preserve source PNGs and record SHA-256. Produce optimized WebP derivatives;
do not regenerate or replace approved artwork. Correct stale planning status only.

### 2. Establish the static shell

Add the isolated package, static configuration, shared layout, self-hosted fonts,
Catppuccin Mocha tokens, responsive grid, header/footer and language switch.

### 3. Build the eight sections

| Section | Implementation |
| --- | --- |
| 00 / ORIGEN | Approved Morfeo illustration, exact copy, action links and foundations |
| 01 / DESARROLLO | Three modes, long-horizon block, native orbital clock/astrolabe |
| 02 / EQUIPO | Role text and SVG topology with forward, reverse, branching and paused packets |
| 03 / PROCESO | Six-stage editorial process with correction loop; distinct from role tree |
| 04 / CONOCIMIENTO | Approved graph image, shared knowledge, role experience, owner memory |
| 05 / CONTROL | Text-led scope/isolation/verification/observation/recovery, no major visual |
| 06 / FUNDAMENTOS | Linked foundation names and model choice, restrained editorial layout |
| 07 / AUTORÍA | Christopher Hernández Jiménez, open-source/MIT, repository/docs links |

Animations illustrate concepts only. Do not render invented live task statistics,
hour counts, throughput, reliability percentages or production dashboards.

### 4. Documentation and English

Render the existing manual through a readable documentation layout with sidebar,
headings, source links, code blocks, search and mobile navigation. Complete the English
landing after the Spanish source. Do not move technical reference onto the homepage.

### 5. Verification and review

- Build and static/type checks; reproducible lock and package audit.
- Automated exact-copy checks against approved Spanish blocks (normalize whitespace
  only), all eight sections, real routes, local link/anchor and resource integrity.
- Browser checks at mobile, tablet and desktop sizes; screenshots and overflow checks.
- Real animation progression, reverse/branch/rework behavior and pause/reduced-motion.
- Keyboard/menu/language/docs-search interactions; no-JS essential content.
- Automated accessibility inspection plus visual review; record any remaining limits.
- Relevant repository checks and the required full test bootstrap; no test weakening.
- Independent bounded review if the existing DevSpace provider works.
- Final `main` unchanged, no runtime edits, no commit/push/merge, local preview and
  reproducible commands reported to the owner.

## Primary implementation references

- Astro static routes: https://docs.astro.build/en/guides/routing/
- Astro static endpoints: https://docs.astro.build/en/guides/endpoints/
- Reduced motion: https://developer.mozilla.org/en-US/docs/Web/CSS/@media/prefers-reduced-motion
- SVG geometry: https://developer.mozilla.org/en-US/docs/Web/API/SVGGeometryElement/getPointAtLength

Plan written before frontend implementation. Executed checks and remaining review limits
are recorded in [VERIFICATION.md](VERIFICATION.md). No integration or publication occurred.
