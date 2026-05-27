# Olympus Flow TUI — UX Design Consultation

## Observations

### Strengths of Current Data Model
- **Clean schema**: `sessions`, `turns`, `tool_calls`, `steering` capture all necessary communication events.
- **Foreign keys**: Tool calls link to turns; turns link to sessions — supports hierarchical display.
- **Timestamps**: Unix epoch ordering enables timeline reconstruction.
- **WAL mode**: Supports concurrent reads from TUI while writes happen from MCP/plugin hooks.
- **Indexes**: Already present on (session, turn_num) and (session) for performance.
- **Steering table**: Unconsumed directives (`WHERE consumed = 0`) can be highlighted as live alerts.

### What's Missing for Visualization
- **Delegation link**: No explicit foreign key from Daimon session to parent Hermes session. Can be inferred from `tool_calls` where `tool_name = 'talk_to'` and `arguments` JSON contains `action = 'delegate'`.
- **Agent role field**: No column distinguishing Hermes (orchestrator) from Daimons. Derive from `agent` field (e.g., `'hermes'` vs `'hefesto'`).
- **Message directionality**: Not stored explicitly, but can be inferred: Hermes → Daimon = delegation tool call; Daimon → Hermes = turn with `role = 'assistant'` in Daimon's session.
- **Session labels**: Only UUIDs — no human-readable aliases or task descriptions.

---

## Risks

| Risk | Impact & Likelihood | Mitigation |
|------|---------------------|------------|
| **Panel overload with 3+ agents** | Cluttered layout, hard to follow flows. High likelihood during complex orchestration. | Stack panels vertically below 100 cols; allow collapsing completed sessions; implement scroll. |
| **Information overload** | Full tool call JSON/args overwhelm users. Medium likelihood (tool calls can be large). | Truncate to 120 chars with "…" and expand on demand (`Enter`). |
| **Live update flicker** | Frequent re-renders cause distracting flashes. High likelihood with 2‑s polling. | Batch state updates; animate transitions (slide-in/out); use Dirty‑flag rendering. |
| **Terminal Unicode support** | Arrows/symbols may render as `?` or boxes in older terminals. Low‑medium likelihood. | Provide `--ascii` fallback mode (`->`, `<-`, `[+]`, `[-]`). |
| **Performance with large DB** | SQLite reads may lag after thousands of sessions. Low likelihood (current DB is small). | Incremental polling (`WHERE timestamp > last_poll`); limit history to last N sessions. |
| **Session ID confusion** | Long UUIDs unreadable. High likelihood. | Show first 8 chars; optionally assign short aliases (e.g., `hefesto-0a3f`). |
| **Hermes idle state** | When no active delegation, Hermes panel appears empty. Medium likelihood. | Show "Orchestrator idle" with a subtle pulsing indicator; collapse until activity. |

---

## Recommendations

### 1. Layout Strategy: Adaptive Panel Grid

**Core principle**: Hermes always occupies the top row (orchestrator). Agent panels fill the remaining space, dividing horizontally (side‑by‑side) when width allows, stacking vertically when narrow.

#### Single Agent (Hermes + 1 Daimon)
```
┌─ Hermes (◉ active) ──────────────────────────────────────────────────┐
│  orchestrating                                                       │
│                                                                      │
│  → delegate ─────────────────────────────────────────────────────┐   │
│    to: Hefesto                                                    │   │
│    task: "Rewrite Athena SOUL.md..."                             │   │
│                                                                      │
│  ← completed ◄─────────────────────────────────────────────────┘   │
│    "Committed successfully."                                          │
└──────────────────────────────────────────────────────────────────────┘

┌─ Hefesto (● working) ────────────────────────────────────────────────┐
│  turn 3/6  ⬤●●○○○                                                    │
│                                                                      │
│  ├ read_file ✓                                                       │
│  │   path: SOUL.md                                                   │
│  │   content (first 3 lines)…                                        │
│  ├ patch ✓                                                           │
│  │   SOUL.md:342→121 lines                                          │
│  └ terminal ✓                                                        │
│      cmd: git commit -m "feat: simplify Athena"                      │
└──────────────────────────────────────────────────────────────────────┘
```
*Design note: Hermes panel shows both outgoing delegation and incoming response. Arrow direction indicates flow.*

#### Two Agents (side‑by‑side, 50/50 split)
```
┌─ Hermes (◉ active) ──────────────────────────────────────────────────┐
│  orchestrating  • 2 delegations                                      │
│                                                                      │
│  → delegate → Hefesto: "Rewrite Athena…"                            │
│  → delegate → Etalides: "Research OWASP…"                           │
└──────────────────────────────────────────────────────────────────────┘

┌─ Hefesto (● working) ─────────────┐  ┌─ Etalides (● researching) ───┐
│  turn 3/6  ⬤●●○○○                 │  │  turn 2/4  ⬤●○○              │
│                                    │  │                              │
│  ├ read_file ✓                     │  │  ├ web_search ✓             │
│  │   SOUL.md                       │  │  │   "Athena security…"     │
│  ├ patch ✓                         │  │  └ web_search ✓             │
│  │   SOUL.md:342→121              │  │      "OWASP standards…"     │
│  └ terminal ✓                      │  │                              │
│      git commit                    │  │                              │
└────────────────────────────────────┘  └──────────────────────────────┘
```
*Design note: Hermes panel condenses multiple delegations into a list. Side‑by‑side panels require ≥100 cols.*

#### Three+ Agents (vertical stack, equal height)
```
┌─ Hermes (◉ active) ──────────────────────────────────────────────────┐
│  orchestrating  • 3 delegations                                      │
│                                                                      │
│  → Hefesto: "Rewrite…"  → Etalides: "Research…"  → Athena: "Audit…" │
└──────────────────────────────────────────────────────────────────────┘

┌─ Hefesto (● working) ────────────────────────────────────────────────┐
│  turn 3/6  ⬤●●○○○  • 2 tool calls                                    │
└──────────────────────────────────────────────────────────────────────┘
┌─ Etalides (● researching) ───────────────────────────────────────────┐
│  turn 2/4  ⬤●○○  • 1 web search                                      │
└──────────────────────────────────────────────────────────────────────┘
┌─ Athena (◉ idle) ────────────────────────────────────────────────────┐
│  waiting for delegation…                                              │
└──────────────────────────────────────────────────────────────────────┘
```
*Design note: When width < 100 cols, panels stack vertically. Completed sessions collapse to a single line (`Hefesto ✓ completed • 6 turns`).*

---

### 2. Interaction Model: Keybindings & Navigation

| Key | Action |
|-----|--------|
| `q` / `Ctrl‑C` | Quit |
| `r` | Force refresh (poll DB immediately) |
| `Tab` / `Shift‑Tab` | Cycle focus between panels (Hermes → Agent1 → Agent2) |
| `Enter` | Expand selected turn/tool call to show full content |
| `Esc` | Collapse expanded content |
| `↑`/`↓` | Scroll within focused panel |
| `c` | Toggle compact mode (hide tool calls, show only turn summaries) |
| `a` | Toggle show/hide completed (archived) sessions |
| `f` | Filter by agent name (opens mini‑prompt) |
| `h` | Show/hide Hermes panel (default: always visible) |
| `?` | Help overlay |

**Zoom into a session**: Press `Enter` on a session panel to enter full‑screen view of that session (Hermes panel hidden, status bar shows "Zoomed: Hefesto · press Esc to exit").

**Filter by agent**: Press `f`, type agent name (e.g., `hefesto`), and only panels matching that name appear. Filter persists until cleared (`Esc`).

**Scroll**: Each panel has its own scroll region. Focus panel with `Tab`, then `↑`/`↓` to scroll. Long content wraps; horizontal scrolling not needed (truncate instead).

---

### 3. Visual Language: Arrows, States, and Icons

#### Arrow Semantics
| Symbol | Meaning | Example |
|--------|---------|---------|
| `→` | Hermes → Daimon (delegation, message) | `→ delegate: Hefesto` |
| `←` | Daimon → Hermes (response, completion) | `← completed: "Done"` |
| `⚡` | Steering directive (Hermes → Daimon) | `⚡ steer: "Focus only on db.py"` |
| `⇄` | Clarification needed (Daimon → Hermes) | `⇄ clarification: "Which file?"` |

#### Session State Icons
| Icon | State |
|------|-------|
| `◉` | Active (Hermes orchestrating) |
| `●` | Working (Daimon processing) |
| `○` | Idle (waiting) |
| `✓` | Completed |
| `✗` | Failed |
| `⋯` | Starting up |

#### Turn Progress
```
Turn 3/6  ⬤●●○○○   (completed turns = filled, pending = hollow)
```

#### Tool Call Status
```
├ read_file ✓     (green check = success)
├ patch ⋯         (spinning = in progress)
└ terminal ✗      (red cross = failed)
```

#### Color Palette (suggested)
- **Hermes panel**: Border color `#FFD700` (gold) — orchestrator.
- **Active Daimon**: Border color `#00BFFF` (deep sky blue).
- **Completed Daimon**: Border color `#556B2F` (dark olive green) — subdued.
- **Steering alert**: Background `#FF4500` (orange‑red) with white text.
- **Tool call success**: Text `#00FF7F` (spring green).
- **Tool call failure**: Text `#FF6347` (tomato).

---

### 4. Information Hierarchy: Default vs Expanded

#### Default View (Compact)
- **Hermes panel**: List of delegations (direction arrow + target agent + first 80 chars of task).
- **Agent panel**: Session header (name, status, turn progress), then list of tool calls (tool name + status icon + first 60 chars of result). Turn content shown only if short (< 80 chars).
- **Steering alerts**: Show as a highlighted banner at the top of Hermes panel.

#### Expanded View (Press `Enter`)
- **Turn content**: Full text (scrollable).
- **Tool call arguments/result**: Full JSON (syntax‑highlighted, collapsible).
- **Reasoning**: If present, show in a dimmed secondary pane.

#### Handling Long Content
- **Truncation**: Show first 120 chars + `…` (ellipsis). Press `Enter` to expand.
- **JSON**: Pretty‑print with indentation; collapse nested objects beyond depth 2.
- **Code blocks**: Use syntax highlighting (if Rich/Textual supports).
- **Images**: Not applicable (CLI only).

#### Auto‑Collapse Completed Sessions
- After a session completes, wait 10 seconds, then animate collapse to a single line.
- User can press `a` to show/hide completed sessions.

---

### 5. Language Choice: Go+BubbleTea vs Python+Textual

#### Assessment Matrix

| Criteria | Go + BubbleTea | Python + Textual | Winner for Olympus Flow |
|----------|----------------|------------------|-------------------------|
| **Existing ecosystem** | New toolchain, Go not installed | Python already in use, Rich v15 installed | **Textual** |
| **Integration with olympus_v3.db** | Requires Go SQLite driver, separate binary | Direct imports, same venv, async support | **Textual** |
| **Deployment** | Single binary (standalone) | Python package (needs venv) | **BubbleTea** (simpler distribution) |
| **Adaptive layout** | Lip Gloss (excellent) | CSS Grid / DockLayout (equally excellent) | **Tie** |
| **Live updates** | Goroutine + `p.Send()` | `set_interval()` + async updates | **Tie** |
| **Animations** | Lip Gloss + harmonica (physics‑based) | Rich live, CSS transitions | **BubbleTea** (smoother) |
| **Community/Docs** | Charm ecosystem (large, polished) | Textual (growing, excellent) | **Tie** |
| **Maintenance** | Two languages (Go + Python) | Single language (Python) | **Textual** |
| **Developer velocity** | Learning curve for Go | Rapid prototyping in Python | **Textual** |
| **"Bonito y adaptativo"** | ✅ Lip Gloss is stunning | ✅ Textual CSS is equally stunning | **Tie** |

#### Recommendation

**Choose Python + Textual** for the following reasons:

1. **Zero friction**: No new toolchain; Rich already installed; imports `olympus_v3` modules directly.
2. **Rapid iteration**: Chris can prototype in the same Python environment, reuse existing DB reader logic.
3. **Single codebase**: No Go‑Python boundary; easier debugging, testing, and CI.
4. **Textual’s power**: CSS‑like styling, built‑in widgets (Log, DataTable, Tree), and `set_interval()` for polling match the requirements perfectly.
5. **Deployment**: `pip install` alongside hermes‑agent; entry point in `pyproject.toml`.

**Caveat**: If Chris strongly values a standalone binary (no Python env needed on target machines), Go+BubbleTea is a viable alternative — but adds build complexity and a second language.

---

## Prototype Suggestion

**Prototype one screen**: **Two‑agent side‑by‑side view with Hermes panel** (the most common orchestration scenario).

**Why this screen?**
- Exercises adaptive layout (horizontal split).
- Shows delegation arrows (Hermes → Daimon) and response arrows.
- Demonstrates turn progress and tool call trees.
- Includes a steering alert (highlighted banner).
- Tests terminal width handling (≥100 cols needed).

**Prototype outline**:
1. **Hermes panel** (top): Two delegations (`→ Hefesto`, `→ Etalides`) and one completed response (`← Hefesto`).
2. **Hefesto panel** (left): 3 turns, 2 tool calls (one in progress).
3. **Etalides panel** (right): 2 turns, 1 web search completed.
4. **Steering alert**: `⚡ steer → Hefesto: "Focus only on db.py"`.
5. **Status bar**: `Last poll: 2s ago • Sessions: 3 • Turns: 5 • Tools: 4`.

**Tech**: Use Textual with CSS grid layout, `set_interval(2, poll_db)`, and Unicode arrows. Include `--ascii` fallback flag.

---

## Appendix: ASCII Mockup for Completed Session Collapse

```
┌─ Hefesto ✓ completed (6 turns, 4 tool calls) ───────────────────────┐
│  started 2m ago, completed 30s ago                                   │
└──────────────────────────────────────────────────────────────────────┘
```

When expanded (`Enter`):
```
┌─ Hefesto ✓ completed ────────────────────────────────────────────────┐
│  started: 2026‑05‑19 23:01:22                                        │
│  completed: 23:03:45                                                 │
│                                                                      │
│  Turn 1/6  ⬤○○○○○  user: "PROJECT_ROOT: …"                          │
│  Turn 2/6  ⬤●○○○○  assistant: "I'll start by…"                      │
│  ├ read_file ✓                                                       │
│  │   path: SOUL.md                                                   │
│  │   lines: 342                                                      │
│  Turn 3/6  ⬤●●○○○  assistant: "Now I'll patch…"                     │
│  ├ patch ✓                                                           │
│  │   SOUL.md:342→121 lines                                          │
│  Turn 4/6  ⬤●●●○○  assistant: "Committing…"                         │
│  ├ terminal ✓                                                        │
│  │   cmd: git commit -m "feat: simplify"                             │
│  Turn 5/6  ⬤●●●●○  assistant: "Done. Summary…"                      │
│  Turn 6/6  ⬤●●●●●  user: "Great. Close session."                    │
└──────────────────────────────────────────────────────────────────────┘
```

*Design note: Completed sessions show a timeline with tool call results collapsed by default. Expand individual tool calls with `Enter`.*