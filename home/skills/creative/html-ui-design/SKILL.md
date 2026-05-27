---
name: html-ui-design
description: Design HTML UI artifacts — from rapid multi-variant mockups (sketches) to polished single-artifact landing pages, decks, and prototypes. Includes design theology, anti-slop rules, and comparison workflows.
version: 1.0.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [design, html, prototype, ux, ui, creative, mockup, sketch, variants, wireframe]
    related_skills: [popular-web-designs, design-md, excalidraw, spike]
---

# HTML UI Design

## Overview

Two complementary workflows for producing HTML UI artifacts. Use **Rapid Variants** when exploring a direction (2-3 throwaway mockups to compare). Use **Polished Artifacts** when the design direction is set and you need one high-quality deliverable.

| Need | Workflow | Output |
|------|----------|--------|
| "Show me what X could look like" | Rapid Variants | 2-3 HTML files in `sketches/` |
| "Design a landing page / deck / prototype" | Polished Artifact | 1 self-contained HTML file |
| "Make it look like Stripe/Linear/Vercel" | Load `popular-web-designs` + use either workflow | Branded output |

## How to choose

| User says | Use |
|-----------|-----|
| "sketch this screen", "compare layouts", "2-3 takes" | **Rapid Variants** |
| "design a landing page", "prototype this flow", "make me a deck" | **Polished Artifact** |
| "mockup this before I build", "show me variants" | **Rapid Variants** |
| (User gives a specific brand / design system as reference) | Load `popular-web-designs` alongside this skill |

## Rapid Variants (formerly `sketch`)

Use when the user wants to **see a design direction before committing** — 2-3 interactive HTML mockups to compare side-by-side.

### Core method

```
intake  →  variants  →  head-to-head  →  pick winner (or iterate)
```

### 1. Intake

Before generating, get three things:
1. **Feel** — "What should this feel like? Adjectives, emotions, a vibe."
2. **References** — "What apps, sites, or products capture the feel?"
3. **Core action** — "What's the single most important action on this screen?"

### 2. Variants (2-3, never 1)

Each variant takes a different design stance:
- **Density:** compact / airy
- **Emphasis:** content-first / action-first / tool-first
- **Layout:** single-column / sidebar / split-pane

Stance naming: describe the stance, not the number.
```
sketches/001-calm-editorial/index.html + README.md
sketches/001-utilitarian-dense/index.html + README.md
```

### 3. Make them real HTML

- Single self-contained HTML file per variant
- Tailwind via CDN is fine
- Realistic fake content (not lorem ipsum)
- **Interactive**: links clickable, hovers real, at least one state transition
- **Verify visually** with `browser_navigate` + `browser_vision`

Default CSS reset + system font stack:
```html
<style>
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, ...; }
</style>
```

### 4. Head-to-head comparison

```markdown
| Dimension | Calm editorial | Utilitarian dense | Playful split |
|-----------|----------------|-------------------|---------------|
| Density   | Low            | High              | Medium        |
| Primary action | Low       | High              | Medium        |
| **My take:** Utilitarian dense for power users, calm editorial for content-forward.
```

### 5. Interactivity bar

User must be able to:
1. Click a primary action with visible feedback
2. See one meaningful state transition
3. Hover recognizable affordances

### 6. Output structure

```
sketches/ (or .planning/sketches/)
├── 001-calm-editorial/
│   ├── index.html
│   └── README.md
├── 001-utilitarian-dense/
│   ├── index.html
│   └── README.md
```

## Polished Artifact (formerly `claude-design`)

Use when the user wants **one high-quality designed artifact** (landing page, deck, prototype, component lab, motion study) with a complete design process.

### Before starting

Check for web-design skills: `popular-web-designs` (ready-to-paste design systems) and `design-md` (token spec files). They compose with this workflow.

### Workflow

1. **Understand the brief** — What, who, artifact, constraints
2. **Gather context** — Read supplied docs, screenshots, repo files
3. **Define the design system** — colors, type, spacing, radii, shadows, motion
4. **Choose the format** — static comparison, clickable prototype, HTML deck, component lab
5. **Build the artifact** — single self-contained HTML file
6. **Verify** — open in browser, check console, check responsiveness
7. **Report** — file path, what was created, caveats, next step

### Design principles

- **Start from context, not vibes.** Read existing themes, components, tokens first.
- **Avoid AI design slop.** See `references/design-theology.md` for the full anti-slop guide.
- **Ask focused questions** when context is missing — don't produce generic mockups.
- **Content discipline:** Every element must earn its place. No filler, fake metrics, or decorative stats.

### Artifact format rules

- Self-contained HTML with embedded `<style>` and `<script>`
- No remote dependencies (unless explicitly useful)
- Responsive behavior unless intentionally fixed-size
- CSS variables for tokens, CSS grid for layout
- Semantic HTML, real focus/hover states
- Mobile hit targets ≥ 44px

### Deck rules

- Fixed 1920×1080 canvas, scales to fit
- Keyboard navigation, visible slide count, localStorage persistence
- 1-2 background colors max
- Keep slides sparse — solve emptiness with layout, not filler text

### Prototype rules

- Make primary path clickable
- Include key states: default, hover/focus, loading, empty, error, success
- Expose variations with in-page controls (`Tweaks` panel)
- Persist important state in localStorage

### Variation exploration (when requested)

Three options:
1. **Conservative** — closest to existing patterns
2. **Strong-fit** — best interpretation of the brief
3. **Divergent** — most novel

### Verification

- File exists at the stated path
- HTML is complete (no truncation)
- Open in browser, check console errors
- Test key interactions and responsive breakpoints
- **Never say "done" if the file wasn't actually written**

See `references/design-theology.md` for the full design reference (color, typography, layout, motion, anti-slop rules).