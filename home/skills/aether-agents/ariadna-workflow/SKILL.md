---
name: ariadna-workflow
description: Ariadna's PM protocols — session onboarding, sprint tracking, blocker detection, and session close. Step-by-step procedures with output templates.
version: 1.0.0
category: aether-agents
triggers:
  - when ariadna receives a task from hermes
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

# Ariadna Workflow — Project Management Protocols

## When This Skill Loads

Load this skill when Ariadna receives any of these requests from Hermes:
- Session start / onboarding
- Status report
- Blocker update
- Sprint planning or review
- Session close / state save

---

## Protocol 1 — Session Onboarding

Triggered every time a new Hermes session starts.

**Steps:**
1. Read `.eter/.ariadna/CURRENT.md`
2. Read `.eter/.ariadna/LOG.md` (last 3 entries)
3. Identify: current phase, open blockers, last session summary
4. Format and return to Hermes (do NOT summarize further — Hermes will do that)

**Output template:**
```
## Status
Phase: [captura | diseño | ejecución | pausado | completado]
Sprint: [current sprint name or "no sprint active"]

## Blockers
- [BLOCKER]: [description] — since [date] — needs: [what to unblock]
(none if no blockers)

## Risks (not yet blockers)
- [RISK]: [description] — likelihood: [high|medium|low]

## Next Steps
1. [Most urgent action]
2. [Second priority]
3. [Third priority]

## Last Session (summary)
[1-2 sentences of what was accomplished in the last session]
```

---

## Protocol 2 — Blocker Detection

Triggered when Hermes asks "are there any blockers?" or when Ariadna sees a pattern that indicates risk.

**Blockers vs Risks — definitions:**
- **Blocker**: Work cannot proceed until this is resolved. Active now.
- **Risk**: Could become a blocker. Not active yet. Monitor.

**Steps:**
1. Review CURRENT.md for pending tasks > 2 sessions without progress
2. Review LOG.md for tasks that were started but have no completion entry
3. Check if any dependency on external teams/tools/APIs is noted
4. Report each blocker with: what it blocks, since when, and what's needed to resolve

**Escalation rule:** If a risk has been tracked for 3+ sessions without movement → escalate to Hermes as a blocker.

---

## Protocol 3 — Sprint Tracking

Triggered when Hermes asks for sprint status or wants to plan a sprint.

**Sprint structure:**
```
Sprint: [name]
Duration: [start date] → [end date]
Goal: [one sentence — what does done look like?]

Tasks:
  [ ] [task] — Owner: [Daimon or Hermes] — Est: [S/M/L]
  [x] [task] — Owner: [Daimon] — Completed: [date]
  [/] [task] — Owner: [Daimon] — In progress

Done criteria: [what must be true for sprint to be "done"]
```

**Sprint review output:**
```
## Sprint Review: [name]

Completed: [N] tasks
Incomplete: [N] tasks → moved to next sprint
Velocity: [rough estimate — S=1pt, M=3pt, L=8pt]
Retrospective note: [one thing that slowed us / one thing that worked well]
```

---

## Protocol 4 — Session Close

Triggered when Hermes signals session end.

**Steps:**
1. Receive from Hermes: what was accomplished, what is pending, any new blockers
2. Update `.eter/.ariadna/CURRENT.md` — overwrite with current state
3. Append to `.eter/.ariadna/LOG.md` — add new entry (do not overwrite)
4. Confirm to Hermes: "State saved. Next session will resume from: [phase] / [next step]"

**LOG.md entry format:**
```
---
date: [ISO8601]
session_summary: [2-3 sentences of what was done]
completed: [list of tasks completed]
pending: [list of pending tasks]
blockers: [active blockers or "none"]
---
```

---

## Few-Shot Examples

### Example A — Session Start

Hermes sends:
```
CONTEXT: New session starting for the Aether Agents project.
TASK: Deliver current project status for onboarding.
OUTPUT FORMAT: Status / Blockers / Risks / Next Steps / Last Session
```

Ariadna reads CURRENT.md and returns:
```
## Status
Phase: ejecución
Sprint: Sprint 3 — Auth Module

## Blockers
- none

## Risks
- Stripe webhook timeout under high load — likelihood: medium — no test coverage yet

## Next Steps
1. Complete auth middleware (Hefesto)
2. Write integration tests for magic link flow
3. Deploy to staging

## Last Session
Implemented magic link token generation and email dispatch. Backend complete. Frontend integration pending.
```

---

### Example B — Blocker Escalation

Ariadna reviewing LOG.md notices:
- "Implement Stripe integration" has been in LOG.md entries for 4 sessions with status "in progress" and no completion.

Ariadna reports to Hermes:
```
## Blocker Detected (escalated from risk)
Task: Stripe integration
Status: In progress for 4 sessions without completion
Blocked by: [as noted in log] API key from finance team not received
Since: 2026-04-15
Needs: Finance team to provide STRIPE_SECRET_KEY for staging environment
Recommendation: Hermes should surface this to user as active blocker
```

---

### Example C — Session Close

Hermes sends:
```
CONTEXT: Session ending.
SESSION SUMMARY: Implemented auth middleware. Magic link flow now works end-to-end. Tests written and passing.
OPEN ITEMS: Deploy to staging. Frontend integration.
BLOCKERS: none
```

Ariadna updates CURRENT.md and LOG.md, returns:
```
State saved. CURRENT.md updated to phase: ejecución, Sprint 3.
Next session resumes from: staging deploy + frontend integration.
LOG.md entry added for [date].
```
