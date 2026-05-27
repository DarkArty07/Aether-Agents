# Design Theology — Color, Typography, Layout, Motion, Anti-Slop

> Extracted from the consolidated `html-ui-design` umbrella. Reference for producing high-quality visual design in HTML artifacts.

## Design Principles

- **Start from context, not vibes.** Read brand docs, screenshots, repo components, design tokens before designing.
- **Good design does not start from scratch.** Inspect theme files, global stylesheets, layout scaffolds, component files.
- **Ask focused questions** when context is missing. Skip questions when the user gave enough direction.
- **Content discipline:** Every element must earn its place. No filler content, fake metrics, decorative stats, or generic feature grids.

## Anti-Slop Rules

Avoid common AI design sludge:
- Aggressive gradient backgrounds
- Glassmorphism by default
- Emoji unless the brand uses them
- Generic SaaS cards with icons everywhere
- Left-border accent callout cards
- Fake dashboards filled with arbitrary numbers
- Stock-photo hero sections
- Oversized rounded rectangles as a substitute for hierarchy
- Rainbow palettes
- Vague labels like "Insights," "Growth," "Scale," "Optimize" without content
- Decorative SVG illustrations pretending to be product imagery

**Minimal is not automatically good. Dense is not automatically cluttered. Choose intentionally.**

## Typography

Use the existing type system if one exists. If not, choose deliberately:
- **Editorial:** serif or humanist headline with restrained sans body
- **Software/productivity:** precise sans with strong numeric treatment
- **Luxury/minimal:** fewer weights, more spacing discipline
- **Technical:** mono accents only, not mono everywhere
- **Deck:** large, clear, high contrast

Avoid overused defaults. Use type as hierarchy before adding boxes, icons, or color.

## Color

Use brand/design-system colors first. If no palette exists:
- Define a small system: neutrals, surface, ink, muted text, border, accent, danger/success
- Use one primary accent unless the assignment calls for a broader palette
- Prefer oklch for harmonious invented palettes
- Check contrast for important text and controls
- Do not invent lots of colors from scratch

## Layout and Composition

Design with rhythm: scale, whitespace, density, alignment, repetition, contrast, interruption.
- Avoid making every section the same card grid
- Product UIs: prioritize speed of comprehension over decoration
- Marketing surfaces: one idea per section
- Dashboards: only show data that helps the user decide or act

## Motion

Use motion as discipline, not theater.

**Good motion:** clarifies state changes, reduces anxiety during loading, shows continuity between surfaces, gives controls tactility, stays subtle.
**Bad motion:** loops without purpose, delays the user, calls attention to itself, hides poor hierarchy.

Respect `prefers-reduced-motion` for non-trivial animation.

## HTML/CSS/JS Standards

- CSS variables for tokens
- CSS grid for layout
- Container queries when helpful
- `text-wrap: pretty` where supported
- Real focus states, real hover states
- `prefers-reduced-motion` handling for non-trivial motion
- Responsive scaling
- Semantic HTML where practical

Avoid: huge monolithic files, fragile hard-coded viewport assumptions, inaccessible tiny hit targets, decorative JS that fights usability.

Mobile hit targets ≥ 44px. Print text ≥ 12pt. Deck text ≥ 24px.

## Variation Rules

When exploring, default to at least three options:
1. **Conservative** — closest to existing patterns
2. **Strong-fit** — best interpretation of the brief
3. **Divergent** — most novel

Variations can explore: layout, hierarchy, type scale, density, color posture, surface treatment, motion, interaction model, copy structure, component shape.

Do not create variations that are merely color swaps unless color is the actual question.

## React in Standalone HTML

Use React only when:
- The artifact needs meaningful state
- Variants/toggles are easier as components
- Interaction complexity warrants it
- The target implementation is React/Next.js

If using React from CDN: pin exact versions, avoid `type="module"` unless necessary, give global style objects specific names.

## Copyright and Reference Models

Do not recreate a company's distinctive UI or proprietary visual identity unless the user has rights.
It is acceptable to extract general design principles (density, command-first interaction, monochrome with one accent, etc.).
Transform posture and principles into an original design.