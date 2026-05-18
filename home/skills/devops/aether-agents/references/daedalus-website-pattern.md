# Daedalus Website Design Patterns

## Overview
Daedalus is the UX Designer Daimon. When creating website designs, he follows these patterns:

## Design System References
Daedalus uses the `popular-web-designs` skill which contains 54 real design systems (Stripe, Linear, Vercel) as HTML/CSS templates.

## Output Patterns

### Landing Pages
- Hero section with clear value proposition
- Feature cards with icons
- Social proof section
- CTA with gradient button

### Documentation Sites
- Sidebar navigation
- Code blocks with syntax highlighting
- Breadcrumbs
- Search integration

### Dashboard UIs
- Sidebar with collapsible sections
- Data tables with sorting/filtering
- Status cards with metrics
- Responsive grid layout

## Common Pitfalls
- Dark theme: always test contrast ratios (min 4.5:1 for text)
- Mobile-first: design for 375px viewport first
- Motion: prefer `prefers-reduced-motion` media query
- Accessibility: always include `alt` text and ARIA labels

## File Output
Daedalus produces single-file HTML artifacts using the `claude-design` skill. Output is delivered as HTML files or preview URLs.