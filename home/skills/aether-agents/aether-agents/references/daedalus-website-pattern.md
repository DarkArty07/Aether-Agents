# Website / Landing Page Design Pattern

Moved from Daedalus SOUL.md on 2026-05-05 during optimization. Retained for reference.

## Website / Landing Page Design Pattern

When Daedalus receives a request to design website sections, landing pages, or UI updates for an existing site, use this proven pattern:

### What to Send Daedalus

1. **Current state** — existing CSS variables, layout patterns, class names, section order in HTML
2. **What's missing** — features/content that needs to be added, with specific data
3. **Technical context** — framework (vanilla/React/etc), fonts, breakpoints, dependencies
4. **OUTPUT FORMAT** — `For each section: Section structure → Layout approach → CSS classes → Responsive behavior → Wireframe`

### Why This Works

Daedalus produces specs that:
- Match the existing design system exactly (same CSS variables, same patterns)
- Include exact HTML structure with semantic elements and proper nesting
- Include complete CSS with variable reuse, hover states, transitions
- Include responsive breakpoints (desktop grid → mobile stack)
- Include wireframe descriptions for each section
- Include implementation notes (section order, nav updates, JS changes)

The output can be directly translated into `delegate_task` implementation specs with no ambiguity — exact insertion points, class names, and properties.

### Proven Results (2026-04-28)

Daedalus designed 3 sections for the Aether Agents landing page (Workflows grid, Pipeline flow, callout update) via `talk_to`. The spec was:
- Production-ready CSS (~190 lines) matching existing dark premium theme
- Complete HTML for 6 workflow cards and 5-phase pipeline flow
- Responsive behavior for both sections
- Implementation notes for Hefesto

The spec was directly executable by `delegate_task` — 0 back-and-forth, 0 ambiguity. Total: 438 lines of code added/modified in 3 files.