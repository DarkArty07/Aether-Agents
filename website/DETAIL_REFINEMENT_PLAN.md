# Aether Agents website — clarity and detail refinement

Status: implemented and locally verified in the isolated website worktree on 2026-09-07.
Owner direction: improve the clock, remove ambiguous decorative symbols, make the
copy easier to understand and make Spanish read naturally for Mexico. English stays
clear and neutral. This pass may correct additional clarity/usability issues discovered
during implementation, but it must preserve the approved visual identity and product
meaning.

## Boundaries

- Work only in `feat/website-onepage` / `website/`.
- No commit, push, merge, deployment or Aether runtime changes.
- Preserve the Greco-futurist / tech-noir editorial direction, Catppuccin palette,
  selected hero/finale artwork, documentation routes and accessibility contracts.
- Do not turn illustrative motion into fake telemetry or measured product claims.
- Keep the English landing neutral; this pass primarily rewrites Spanish for Mexico.

## 1. Make the autonomy clock unmistakable

The current astrolabe reads as technical ornament before it reads as a clock. Replace
that ambiguity with an explicit 24-hour conceptual dial:

- show readable hour labels around the face;
- distinguish major time quadrants from minor ticks;
- keep restrained orbital/astrolabe geometry as identity rather than the main signal;
- localize the center label instead of leaving English inside the Spanish page;
- slow and clarify hand motion so it reads as time passing rather than a spinner;
- state that the dial is conceptual and does not report measured runtime.

## 2. Give every symbol a job

Audit arrows, plus signs and ornamental signals. Apply a consistent visual grammar:

- `↗` means an external/outbound link;
- `↓` means navigation to content below;
- `↶` means a real correction/return loop in the process illustration;
- `+` is reserved for an actual expand/reveal interaction and otherwise removed;
- non-interactive ornament must not look like a button or affordance.

In particular, remove the decorative arrows from the three development mode cards and
the decorative plus signs from Control. Preserve arrows in actual links and diagrams
where they describe direction.

## 3. Rewrite Spanish for comprehension first

Create a second copy refinement that supersedes the first owner-review candidate.
Write natural Mexican Spanish without slang, forced regionalisms or translated
corporate phrasing. Prefer short concrete sentences and explain technical ideas at the
point where a visitor needs them.

Primary goals by section:

- Hero: define Aether in one sentence a non-user can parse quickly.
- Development: explain what the visitor asks for and what Aether returns.
- Team: make role hand-offs and owner authority obvious.
- Process: describe the path from request to verified integration without jargon where
  plain Spanish works.
- Knowledge: explain what Graphify contributes and what remains separate.
- Control: explain why autonomy is bounded and observable.
- Foundations: explain dependencies without making them sound mandatory when optional.

## 4. Polish supporting visual semantics

- Clarify labels/captions on diagrams where they are currently abstract.
- Keep interactive states only where interaction reveals information (knowledge graph).
- Avoid adding controls simply to justify decorative symbols.
- Preserve keyboard, touch, reduced-motion and no-JS behavior.

## 5. Verification

Update exact-copy tests to the new candidate and add regressions for the new clock and
symbol grammar. Then run:

- `npm run build`
- `npm run check`
- `npm test`
- `npm run test:e2e`
- responsive capture/overflow checks if the clock changes affect layout

Document final evidence in `VERIFICATION.md`. Leave the loopback preview available for
owner review. Integration remains a separate decision.

## Execution result

Implemented as planned. The autonomy instrument is now an explicit conceptual 24-hour
clock with all `00`–`23` labels, four quarter-hour subdivisions per hour, two clock
hands, slower orbital decoration, localized center text and an explicit non-telemetry
caption. Browser regression coverage checks all 24 labels at desktop and mobile sizes
and asserts that their rendered bounding boxes do not overlap.

Decorative development arrows and Control plus signs were removed. Internal navigation
uses `→`; outbound links use `↗`; vertical navigation keeps `↓`/`↑`; correction/direct
flow keeps `↶`/`↳`. Documentation index links were corrected to the same convention.

Spanish copy is now sourced from `COPY_REFINEMENT_MX.md`. It was rewritten across the
landing and graph context panel for direct, sober Mexican Spanish, without slang or a
change in product claims. English remains neutral and only received the global internal
arrow correction.

Final evidence: build PASS (20 static pages), Astro check PASS (30 files, zero
diagnostics), content tests PASS (19/19), Playwright PASS (36/36 desktop/mobile), and
responsive capture PASS at 360/390/768/1024/1440/1920 px with no overflow. Preview
responds 200 on loopback. Main is clean at `4771b9d`; the website worktree remains at
`0913ec6` with `website/` intentionally untracked and no commit/push/merge performed.
