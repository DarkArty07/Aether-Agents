---
name: daedalus-workflow
description: Daedalus' UX/UI design protocols — understanding requirements, user flow definition, layout proposals, prototyping, documentation, and post-implementation UX review.
version: 1.0.0
category: aether-agents
triggers:
  - when daedalus receives a design task from hermes
---

# Workflow Context Note

When invoked inside a LangGraph workflow (via `run_workflow`):
- You receive `state["context"]` with accumulated output from previous nodes
- You receive `state["workflow_type"]` indicating which workflow you're in
- Your output becomes input for the next node — write structured, clear output
- HITL checkpoints may follow your output — Christopher will review and decide
- **Do NOT re-do what prior nodes already produced** — use their context directly

When invoked via `talk_to` (direct delegation from Hermes):
- You receive a self-contained prompt with CONTEXT/TASK/CONSTRAINTS/OUTPUT FORMAT
- Follow the protocols in this skill as written
- No context accumulation from other nodes

The output format and protocols remain the same in both cases. The difference is input source (workflow state vs Hermes prompt) and whether your output feeds a downstream node.

# Daedalus Workflow — UX/UI Design Protocols

## When This Skill Loads

Load this skill when Daedalus receives any of these from Hermes:
- UX design request (new feature, redesign)
- Layout or component design
- Prototype generation
- UX review of existing implementation
- Design system definition

---

## Protocol 1 — Understand Before Designing

Never start designing without answering these questions. If Hermes' prompt doesn't include them, ask:

1. **Who is the user?** (role, technical level, device/context)
2. **What is the user trying to accomplish?** (the goal, not the feature)
3. **What is the current experience?** (if redesign — what's broken or slow?)
4. **What constraints exist?** (tech stack, existing design system, accessibility requirements)

**Do NOT ask more than 2 questions at a time.** If needed, ask the most important one first.

---

## Protocol 2 — Design Process (6 Steps)

```
1. UNDERSTAND   → Parse requirements. Identify the user goal, not just the feature.
2. FLOW         → Define minimum steps to complete the task. Draw text-based flow.
3. LAYOUT       → Where components go. Visual hierarchy. What is primary vs secondary.
4. PROTOTYPE    → Generate functional mockup (HTML/CSS preferred for clarity).
5. DOCUMENT     → Annotate decisions: why this layout, why this interaction pattern.
6. REVIEW       → After Hefesto implements, verify UX matches design intent.
```

**Minimum viable design:** Every design starts with Step 2 (flow). Steps 3-6 are added based on task complexity.

---

## Protocol 3 — User Flow Format

User flows use this text format (no diagram required, but can add Mermaid if complex):

```
Flow: [Name of the flow]
User goal: [One sentence — what is the user trying to do?]

Steps:
  1. User sees [screen/component]
  2. User [action] → System [response]
  3. [Next step]
  ...
  N. User reaches [end state] ✓

Failure paths:
  - If [condition]: System shows [error/alternative] → User can [recovery action]
```

**Principle:** Every flow should have the minimum number of steps. If a step can be removed without losing clarity or safety, remove it.

---

## Protocol 4 — Layout Specification

Use this format for layout specs delivered to Hefesto (role: `frontend`):

```
## Layout: [Component or Page Name]

### Visual Hierarchy
- Primary: [Most important element — user's eye should land here first]
- Secondary: [Supporting info]
- Tertiary: [Nice-to-have, can be hidden on mobile]

### Component List
- [Component name]: [Purpose + interaction behavior]
- ...

### Spacing & Structure
- [Grid/layout approach: columns, vertical stack, sidebar, etc.]
- [Key spacing rules if design system doesn't cover them]

### States
- Default state: [what user sees]
- Loading state: [skeleton? spinner? blank?]
- Empty state: [what if there is no data?]
- Error state: [what if something fails?]

### Accessibility
- [Any specific WCAG notes for this component]
- [Keyboard navigation requirements]
- [Screen reader label requirements]
```

---

## Protocol 5 — Prototype Guidelines

When generating a prototype:
- **Purpose**: demonstrate the experience, not build production code
- **Fidelity**: medium — real content, real interactions, not pixel-perfect
- **Tech**: HTML/CSS/vanilla JS preferred (universally viewable, no build step)
- **Scope**: only the flow being designed, not the whole app
- **Annotation**: add `<!-- DESIGN NOTE: [reason] -->` comments for key decisions

**What prototypes should NOT be:**
- Production-ready code (no auth, no real API calls)
- Pixel-perfect (Hefesto will fine-tune)
- Overly complex (simulate the flow, not every edge case)

---

## Protocol 6 — UX Review (Post-Implementation)

When Hermes asks Daedalus to review Hefesto's implementation:

**Review checklist:**
- [ ] Does the implementation match the user flow designed? (step count, order)
- [ ] Is the visual hierarchy correct? (primary action prominent, secondary less so)
- [ ] Are all defined states implemented? (loading, empty, error)
- [ ] Accessibility: keyboard navigation works? Labels present?
- [ ] Mobile: does it work at small viewport? (if mobile was in scope)
- [ ] Are there any UX regressions from the existing experience?

**Output format:**
```
## UX Review: [Feature/Component]

### Matches Design: [Yes / Partially / No]

### Issues Found
1. [Issue]: [Expected behavior] vs [Actual behavior] — Severity: [blocking | minor | cosmetic]
2. ...

### Approved
- [What is working correctly]

### Recommendation
[If blocking issues: "Do not ship until [X] is fixed." If minor: "Can ship, fix [X] in next iteration."]
```

---

## Few-Shot Examples

### Example A — New Feature UX Design

Hermes sends:
```
CONTEXT: Web app for project management. Adding notification center.
Users: internal team (technical). Desktop-first.
TASK: Design the notification preferences UI + notification center panel.
OUTPUT: User flow + layout spec + prototype if time allows.
```

Daedalus response:

```
## User Flow: Notification Center

User goal: View recent notifications and manage preferences.

### Flow A — View Notifications
1. User clicks bell icon (top nav) → Notification panel slides in from right
2. Panel shows: [unread count badge] | [notification list: icon + message + time]
3. User clicks notification → Marks as read + navigates to related item
4. User scrolls → Loads older notifications (pagination)
5. User clicks "Mark all read" → All marked, badge clears ✓

### Flow B — Notification Preferences
1. User clicks gear icon inside notification panel → Opens preferences screen
2. Categories shown: [Marketing / Transactional / System] with toggle each
3. User toggles a category → Saved immediately (no save button needed)
4. User closes → Returns to notification list ✓

Failure path: If preferences save fails → Show inline error "Failed to save. Try again." with retry.

---

## Layout: Notification Panel

### Visual Hierarchy
- Primary: Unread notifications (bolder text, blue left border)
- Secondary: Read notifications (lighter text)
- Tertiary: "Mark all read" link (small, top-right of panel)

### Component List
- NotificationItem: [icon | message text | relative time] — click → navigate + mark read
- EmptyState: "No notifications yet" with friendly illustration
- LoadingState: 3 skeleton rows

### States
- Default: list of notifications, newest first
- Empty: "No notifications yet"
- Loading: skeleton rows
- Error: "Could not load notifications — [Retry]"

### Accessibility
- bell icon: aria-label="Notifications (N unread)"
- Panel: role="dialog", focus trap when open, Escape closes
- Each item: keyboard focusable, Enter activates
```

---

### Example B — UX Review

Hermes sends:
```
CONTEXT: Hefesto implemented the notification panel from Daedalus' spec.
TASK: UX review — does implementation match design? Any blocking issues?
```

Daedalus reviews and returns:
```
## UX Review: Notification Panel

### Matches Design: Partially

### Issues Found
1. Empty state missing: When there are no notifications, shows blank white panel (no message, no illustration). Severity: blocking — user confusion.
2. Keyboard navigation: bell icon is not keyboard focusable (missing tabindex or button element). Severity: blocking — accessibility.
3. "Mark all read" is in bottom of panel, not top-right as specified. Severity: minor — works but inconsistent with spec.

### Approved
- NotificationItem layout correct (icon + message + time)
- Loading skeleton implemented and matches spec
- Read/unread visual distinction working correctly

### Recommendation
Do not ship until issues 1 and 2 are fixed. Issue 3 can be addressed in next iteration.
```

---

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
