# Aether Agents — Website

Status: published. The `Website Pages` workflow builds, tests and deploys this site to
<https://darkarty07.github.io/Aether-Agents/> on every merge to `main` that touches
`website/` or `docs/`. The site presents the stable Aether 1.0.0 release; earlier review
and polish history is kept in the plans linked below.

An animated one-page site in Spanish and English with the approved Greek/modern,
editorial tech-noir identity and Catppuccin Mocha palette. A separate documentation
surface renders the existing canonical Markdown corpus directly from this checkout.

## Preview and development

Requirements: Node >=22.12 and npm. Run these commands from `website/` inside the
Aether Git checkout (not from a copied standalone folder: documentation uses `../docs/`).

```bash
npm ci
npm run build
npm run preview
```

Local addresses:

```text
http://127.0.0.1:4321/        Spanish one-page
http://127.0.0.1:4321/en/     English one-page
http://127.0.0.1:4321/docs/   Documentation index and search
```

For live editing: `npm run assets && npm run dev`. Both servers bind loopback only.
After shutting down/restarting the machine, run `npm run preview` again; preview is a
local development process, not an autostart service. If it reports a running server,
open the existing address rather than starting a duplicate. Stop only the website
preview you started or select an explicit alternate port; never stop an unrelated
process. Public deployment happens only through the `Website Pages` workflow.

## What is implemented

| Section | Treatment |
| --- | --- |
| 00 / ORIGEN | Latest Morfeo/ether artwork, preserved headline, ambient lighting and foundation links |
| 01 / DESARROLLO | Create/extend/improve, long-horizon text and native SVG astrolabe |
| 02 / EQUIPO | Bidirectional SVG role diagram: advance, branch, wait, return, converge |
| 03 / PROCESO | Six-stage workflow with a visible review-to-execution correction loop |
| 04 / CONOCIMIENTO | Sharp interactive SVG graph; classical margins from approved art; GSAP query/return paths |
| 05 / CONTROL | Text-led scope, isolation, verification, observation and recovery |
| 06 / FUNDAMENTOS | Linked foundations, compatible model choice, optional Router note |
| 07 / AUTORÍA | Latest ether background, Christopher Hernández Jiménez, linked @DarkArty07 and MIT/open-source access |

The opening and closing use the two new owner-provided images; the knowledge graph
retains only decorative margins from its approved artwork. Original PNGs remain intact
in `assets/images/`. Incoming files are 1672 × 941, not claimed 4K/8K sources.
The build verifies their hashes and creates responsive WebP derivatives; native-size
hero and finale pixels are losslessly preserved. The knowledge image contributes masked architectural
margins: graph nodes, connections and localized labels are now SVG/HTML. Typography is
self-hosted through Fontsource. The browser loads no third-party scripts or assets.
Animated diagrams are conceptual, never fabricated live operational data.

Animations pause outside the viewport and in hidden tabs. The global pause preference
persists locally, and system reduced motion is respected. The page remains readable
without JavaScript; mobile navigation also works without it.

## Documentation and languages

The landing is fully rendered at `/` and `/en/`; language switching preserves the
current section anchor. Approved Spanish copy is never translated in place.

Spanish supporting copy was refined on the owner's explicit first-review request;
`COPY_REFINEMENT.md` owns this candidate. The headline “Del éter al software.” and the
hero description remain unchanged. Section numbers exist only as internal design IDs.

The documentation index introduces every canonical document in Spanish. The original
technical text stays in English, visibly labeled, and is rendered at `/docs/<slug>/`.
Search runs locally against a generated static index. Relative document links and
heading anchors resolve locally; other repository links point at the inspected Git
revision. No private profiles, graph snapshots, sessions or runtime databases are read.

## Maintain and verify

```bash
npm run build
npm run check
npm test
npx playwright install chromium
npm run test:e2e
```

With the preview running, `node scripts/capture.mjs` captures responsive layouts and
reports widths at 360, 390, 768, 1024, 1440 and 1920 pixels. Browser reports/screenshots
remain ignored under `test-results/` and `playwright-report/`.

- Copy and translations: `src/data/content.ts`.
- README banner and GitHub social preview: `npm run readme-assets` renders
  `../.github/assets/banner.png` and `social-preview.png` from the approved hero artwork
  with the site fonts and palette (local only, no network).
- Composition: `src/components/Homepage.astro`.
- Palette, typography and responsive rules: `src/styles/global.css`.
- Native animation: `src/scripts/motion.ts`.
- Knowledge exploration and lighting: `src/scripts/knowledge.ts` and `src/styles/knowledge.css`.
- Opening/closing ambient motion: `src/scripts/atmosphere.ts` and `src/components/Atmosphere.astro`.
- Documentation renderer: `src/lib/docs.ts`.
- Exact-copy, asset and route checks: `tests/content.test.mjs`.
- Browser, interaction and accessibility checks: `tests/browser/` (site, polish, atmosphere and history).

The history tests launch the installed full Chromium with its default bfcache-disable
flag removed. They assert a persisted `pageshow` and the same document identity across
actual navigation; a fresh load cannot pass as a successful cache-restoration test.

## Design and evidence

- [Visual Identity System](VISUAL_IDENTITY.md)
- [Website Content Architecture](CONTENT_ARCHITECTURE.md)
- [Approved source copy and design history](HOMEPAGE_PROPOSAL.md)
- [Implementation plan](IMPLEMENTATION_PLAN.md)
- [Executed checks and remaining review limits](VERIFICATION.md)
- [Approved artwork provenance](assets/README.md)

The website does not change Aether's runtime, Python dependencies or capability
registry. The current [product concept](../DESIGN.md), [capabilities](../docs/capabilities.toml)
and [technical manual](../docs/index.md) retain their own authority. This candidate
is not evidence of package release or live multi-agent qualification.
