# Website polish — first owner review

Status: implemented and locally verified; owner review pending, isolated worktree only.

Final evidence is recorded at the top of VERIFICATION.md. No commit, push, merge or
public deployment was performed.

## Owner feedback and authority

The owner approved the prototype direction and requested removing visible sketch
numbering, making the Spanish more natural, checking image quality, adding the GitHub
handle beside the author name, and richer knowledge-graph animation/lighting.
This explicitly supersedes literal preservation of supporting Spanish paragraphs and
numbered presentation labels for this revision. Preserve the main headlines, especially
“Del éter al software.”, product meaning, Greek identity and Catppuccin Mocha. The
previous copy remains documented in HOMEPAGE_PROPOSAL.md; COPY_REFINEMENT.md will own
the new review candidate. Do not change technical product claims or the docs corpus.

## Plan

1. Remove visible section/item numbers, FIG labels and repeated drafting annotations.
   Keep stable internal section IDs for navigation and tests, not as visible content.
2. Rewrite supporting Spanish in direct, natural Mexican Spanish without slang or
   grandiose claims; preserve headings and the approved hero message. Present the
   corresponding English without sketch numbering as well.
3. Add a visible @DarkArty07 profile link beside Christopher Hernández Jiménez.
4. Preserve both approved original PNGs. Export the hero losslessly at its native
   resolution, with responsive smaller derivatives. Do not invent higher resolution.
5. Reconstruct the knowledge graph as sharp SVG nodes, paths and localized HTML labels.
   Retain only the classical decorative margins from the approved image as a masked
   derivative; remove embedded raster typography/graph from the active illustration.
   Keep experiences/preferences outside the shared technical graph.
6. Use a locally bundled, locked GSAP dependency with MotionPathPlugin for coordinated
   query-and-return pulses, selective line illumination and subtle node light. Support
   pointer, touch and keyboard exploration with a short, meaningful context panel.
   Stop timelines offscreen, in hidden tabs, or when paused/reduced-motion is selected.
   This remains an illustrative graph, not live Graphify data or telemetry.
7. Validate builds/types, full website content/link tests, interactive browser tests,
   pause/reduced-motion/no-JS, keyboard/touch, screenshots and responsive overflow.
   Keep the loopback preview available. No commit, push, merge or public deployment.

## Observed baseline

- Website HEAD: 0913ec636ab081654065be90b021cf1c47a41619.
- Main observed separately at start: 677df63fc0fa0d8be9349e8f35ed3202d1b3bf9b.
  Another workflow has advanced main; do not integrate it or overwrite it.
- Both originals are 1672 × 941. Existing WebP conversion used lossy quality 87.
- Existing knowledge animation was only a faint expanding ring on a flattened image.

## Primary implementation references

- https://gsap.com/docs/v3/Plugins/MotionPathPlugin/
- https://gsap.com/docs/v3/GSAP/Timeline/
- https://gsap.com/docs/v3/GSAP/gsap.quickTo()/
- https://sharp.pixelplumbing.com/api-output/

Original 3200–3840-pixel artwork would improve large/HiDPI hero presentation; requesting
it must not imply the current originals contain that resolution or were upscaled.
