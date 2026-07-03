# Hefesto v0.11 Rework Design

## Current State (v0.10.x)

- **SOUL.md**: 284 lines
- **Identity**: Senior Developer / Tech Lead
- **Core issues**: Contains task decomposition that belongs to Hermes, references to obsolete concepts (Ergates, LangGraph, .hefesto/TASKS.md)

## Architectural Insight: Hermes Owns Decomposition

In practice, Hermes decomposes tasks into atomic units and delegates each one. Hefesto receives atomic tasks, not specs that need further decomposition.

The Role Catalog (backend, frontend, devops, qa, security, data, docs, architect, perf) is useful as a **reference for Hermes** when deciding task granularity, not as an internal tool for Hefesto.

### What Moves to Hermes

| What | Where it lives now | Where it belongs |
|------|-------------------|-----------------|
| Task decomposition into atomic units | Hefesto §8 Protocol 2 | Hermes SOUL.md (new section) |
| Role Catalog | Hefesto §8 Protocol 2 | Hermes SOUL.md (reference table) |
| Delegate prompt template (CONTEXT/TASK/CONSTRAINTS/OUTPUT) | Hefesto §8 Protocol 3 | Hermes §5 already has this |
| Deciding which Daimon gets which task | Implicit in Hefesto | Hermes routing table §6 |

### What Stays in Hefesto

| What | Lines | Purpose |
|------|-------|---------|
| §1 Identity | ~5 | Who I am |
| §2 Execution Context | ~15 | How I receive tasks, project root, session scope |
| §3 Core Responsibilities (revised) | ~6 | Implement specs, code review, integration, debugging |
| §4 Limits (revised) | ~7 | Don't design, don't make product decisions, don't research broadly |
| §5 Skills (revised) | ~5 | Keep relevant skills, remove `subagent-driven-development` |
| §6 Output Format | ~5 | Implementation Report |
| Protocol 1 — Receiving a Spec | ~10 | When to stop and ask for clarification |
| Protocol 4 — Code Review | ~15 | Review checklist |
| Protocol 5 — Integration | ~12 | Merge, test, verify |
| Protocol 6 — Debugging | ~20 | Systematic root cause (reference skill, don't duplicate) |
| Example B — Debugging | ~20 | Concrete debugging example |

## Obsolete References in Current SOUL.md

| Section | Problem |
|---------|---------|
| §3 "Coordinate Ergates" | Ergates don't exist in current architecture |
| §4 "Do NOT manage projects — that is Ariadna" | Ariadna is now Context Curator, not PM |
| §7 "In Workflow Context" (LangGraph) | `run_workflow`, `state["workflow_type"]` don't exist in olympus_v3 |
| §8 Protocol 2 "Role-Based Task Decomposition" | Hermes owns decomposition |
| §8 Protocol 3 "Delegate Sub-Agent Template" | Hermes owns delegation prompts |
| Example C "Sub-Agent Delegation" | Uses `delegate_task(role="backend")` — not current pattern |
| `.hefesto/TASKS.md` reference | Replaced by `.aether/` state management |
| Skill: `subagent-driven-development` | Obsolete — Hefesto no longer spawns sub-agents |

## Key Decisions

1. **Hefesto receives atomic tasks from Hermes** — no further decomposition by Hefesto
2. **Remove Ergates, LangGraph, TASKS.md references** — architecture changed
3. **Keep Code Review, Integration, Debugging protocols** — these are genuinely Hefesto's domain
4. **Keep Example B (Debugging)** — good concrete example of systematic debugging
5. **Remove Example C (Sub-Agent Delegation)** — not the current pattern
6. **Update Limits** — replace "Ariadna manages projects" with accurate references
7. **Remove skill `subagent-driven-development`** from Hefesto's skill list
8. **Reference the debugging skill** instead of duplicating content

## Open Questions (for user decision)

- ~~Should Hefesto keep `delegate_task` toolset?~~ → **No. Removed in v0.11.0.**
- ~~Target SOUL.md length: ~120-130 lines?~~ → **114 lines in v0.11.0.**
- ~~Should Hermes get a new "Task Decomposition" section with the Role Catalog?~~ → **Yes. Added to Hermes SOUL.md §6 in v0.11.0.**

## Completion Notes (v0.11.0 — 2026-05-19)

All items above were implemented in v0.11.0:

### Hermes SOUL.md Changes
- Manifesto updated: "I plan, I decompose, I delegate, I synthesize"
- Hard Rule #10 added: "NEVER delegates a vague task — decompose into atomic tasks with CONTEXT + TASK + CONSTRAINTS + ACCEPTANCE CRITERIA before delegating"
- Task Decomposition section added before §7 (Workflow Patterns) with:
  - Atomic task format (`[#N] [Task Type] Brief description → Daimon / CONTEXT / CONSTRAINTS / ACCEPTANCE`)
  - Decomposition protocol (5 steps: LIST, ASSIGN, ORDER, DELEGATE, TRACK)
  - Role Catalog table (10 task types, mapping to Daimons)
  - One task type per delegation rule

### Hefesto SOUL.md Changes
- Rewritten from 284 → 114 lines
- Identity: "Senior Developer / Tech Lead" → "Senior Developer"
- Responsibilities: Removed "Decompose by role" and "Coordinate Ergates"
- Limits: Added "Do NOT decompose tasks"
- Skills: Removed `subagent-driven-development`, kept `systematic-debugging`, `test-driven-development`, `writing-plans`, `github-pr-workflow`
- Protocols renumbered: Receiving Spec (1), Code Review/Self-Review (2), Debugging (3)
- Removed: Protocol 4 (Integration), Protocol 3 (Sub-Agent Template), §7 (LangGraph), Examples A and C

### Hefesto config Changes
- Removed `delegate_task` from toolsets and capabilities
- Removed `delegation` section (subagent_auto_approve)
- Removed `estimation` from capabilities
- Added `receives_from` capability
- English description (was Spanish)
- Added YAML comments explaining toolsets and removed features