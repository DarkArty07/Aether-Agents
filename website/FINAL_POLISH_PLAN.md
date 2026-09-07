# Aether website — final artwork and motion refinement

Status: implemented and verified after host restart on 2026-09-07; owner approval
required before integration. Final results are recorded at the top of VERIFICATION.md.

## Current owner direction

Continue the existing refinement of typography, natural Spanish and the live vector
knowledge graph. Preserve those changes and the approved primary headlines. Use the
new Morfeo composition for the hero and the owner's second image for the closing
authorship section. Add restrained motion and lighting; choose implementation details
autonomously. Do not commit, push, merge, publish or change the Aether runtime.

The new closing art supersedes the earlier text-only finale. Keep the graph vector-led;
its approved classical margins may remain as subtle decoration. No additional images.

## Plan before implementation

1. Verify incoming images on the actual DevSpace host, keep originals and SHA-256.
2. Produce responsive derivatives without inventing resolution. Both new files are
   1672 × 941, not 4K/8K sources; native-size lossless WebP avoids added compression loss.
3. Wire the new opening image and a full-width atmospheric closing background, with
   legible text and the linked @DarkArty07 next to the author's name.
4. Retain the already installed, locked GSAP + MotionPathPlugin for the graph. Add
   ambient light, sparse motes and bounded pointer parallax to the opening and closing.
   Stop animation offscreen, in hidden tabs and for pause/reduced-motion preferences.
5. Validate the complete site: content/link tests, types/build, browser interactions,
   keyboard/touch, no-JavaScript, reduced motion, multiple viewport sizes and screenshots.
6. Fix observed failures, update verification and leave loopback preview for owner review.

## Inputs verified on the DevSpace host

| Asset | Dimensions | SHA-256 |
| --- | --- | --- |
| `assets/images/aether-morfeo-refined.png` | 1672 × 941 | `25a0d29e28dda00f2c1c598e1605d99dcfb858e7df9d5a5c1898a0c06118159d` |
| `assets/images/aether-ether-finale.png` | 1672 × 941 | `86d7df0e7c5452dbef3e699f9ffcaf492871ee811553832435e0507e46a0a93e` |

The older hero and knowledge originals stay intact. The new hero can use the same
public URL stem through an explicit source mapping in the build script.

## Scope and evidence

Worktree: `feat/website-onepage`, HEAD `0913ec636ab081654065be90b021cf1c47a41619`.
Main observed before this work: `677df63fc0fa0d8be9349e8f35ed3202d1b3bf9b`.
Other workflows have advanced main since initial site creation; do not integrate it.
An illustrative diagram is not live Graphify data, a benchmark or operational telemetry.

Primary implementation references checked for this pass:
- https://gsap.com/docs/v3/Plugins/MotionPathPlugin/
- https://gsap.com/docs/v3/GSAP/gsap.matchMedia()/

Execution evidence is recorded in VERIFICATION.md after the final build and browser
verification. Earlier interrupted results remain historical.

## Resume after host restart — 2026-09-07

The owner restored access and authorized completing the interrupted verification.
The existing worktree and all four preserved PNGs are present; loopback preview was
stopped by the host shutdown. Worktree HEAD remains `0913ec6`; the main checkout is
clean at `677df63`. No branch integration is authorized.

1. Rebuild the current source, including the pending `pageshow` lifecycle correction.
2. Add regression coverage for repeated history restoration and ensure selection,
   global pause and reduced motion do not create duplicate or frozen controllers.
   Distinguish synthetic lifecycle tests from actual browser cache restoration.
3. Rerun all website checks, inspect responsive screenshots, and fix any reproducible
   defects without changing the approved composition or copy.
4. Update execution evidence and leave only the loopback review server running.

Completed: the pending graph `pageshow` correction passes real back/forward-cache
restoration tests in desktop and mobile Chromium. Three successive restores retain
working graph selection, motion, pause and ambient-light controls without duplicated
listeners; separate restore tests preserve pause/reduced motion. Build, types, 17
content tests, 34 browser tests and all six responsive captures pass. No additional
application-code correction or design change was needed on resumption.

Lifecycle test references inspected during this verification:
- https://developer.mozilla.org/en-US/docs/Web/API/Window/pageshow_event
- https://playwright.dev/docs/api/class-browsertype#browser-type-launch-option-ignore-default-args
