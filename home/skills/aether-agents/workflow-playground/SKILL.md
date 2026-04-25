---
name: workflow-playground
description: Architectural analysis and design direction for evolving the Olympus workflow engine from 6 hardcoded workflows to a dynamic playground where Hermes composes workflows from reusable node blocks using templates-as-data.
version: 0.1.0
triggers:
  - designing workflow engine changes
  - evaluating LangGraph vs alternatives
  - building dynamic workflow composition
  - template-based workflow system
---

# Workflow Playground — Architecture Direction

## Context

The Olympus workflow engine currently has 6 hardcoded workflows defined in `definitions.py` as Python code (StateGraphs with `add_node()`, `add_edge()`). The team wants to evolve toward a "playground" paradigm: Hermes composes workflows dynamically from reusable node blocks, choosing which nodes participate and how they connect based on each task's needs. Like n8n — create a diagram from legos once, save/reuse/modify as needed.

## Current State (What We Have)

### 9 Reusable Node Blocks

| # | Node Type | Agent | What It Does | Current Workflows |
|---|-----------|-------|-------------|-------------------|
| 1 | research | Etalides | Investigate (bugs, CVEs, impact, features) | feature, bug-fix, security-review, research, refactor |
| 2 | design | Daedalus | Design UX or data flows | feature |
| 3 | implement | Hefesto | Implement feature/fix/refactor | feature, bug-fix, refactor |
| 4 | implement_fix | Hefesto | Fix audit findings | feature, security-review |
| 5 | audit | Athena | Audit code (initial) | feature, bug-fix, refactor |
| 6 | re_audit | Athena | Re-audit after fixes | feature, security-review |
| 7 | onboard | Ariadna | Initialize .eter/ | project-init |
| 8 | finalize | — | Consolidate final output | All |
| 9 | HITL | — | Pause for user decision | feature (x3), bug-fix, security-review, refactor |

### Files That Would Change

- `src/olympus/workflows/definitions.py` → replaced by dynamic builder
- `src/olympus/workflows/nodes.py` → nodes stay, prompts separate from logic
- `src/olympus/workflows/state.py` → `WorkflowState` TypedDict replaced by generic dict or inferred schema
- `src/olympus/workflows/runner.py` → adapts to new format

### Key Design Principle

**Templates are data (JSON), not code.** Modifying a template never breaks the node blocks because they're tested independently. Connecting nodes is just specifying which blocks participate and how they link. The 6 current workflows become 6 default templates saved in a library.

## Framework Comparison

### LangGraph (Current)

**Pros:**
- Already working, tested, HITL ready via `interrupt()` + `Command(resume=)`
- AsyncSqliteSaver for checkpointing (survives restarts)
- State accumulation across nodes
- Conditional routing

**Cons:**
- State schema is a rigid TypedDict (18 fixed fields)
- Templates as data require a translation layer on top
- We use ~20% of LangGraph; the other 80% we don't touch
- API is verbose: `add_node()`, `add_edge()`, `add_conditional_edges()`

### Hypergraph

**Pros:**
- No state schema — edges inferred from output/input name matching
- Composition via `.as_node()` — graphs nest as nodes naturally
- `@interrupt` for HITL — cleaner than LangGraph's `interrupt()`
- Build-time validation — catches bad connections before runtime
- Immutable graphs — `bind()`, `select()` return copies
- Minimal API — nodes are decorated pure functions

**Cons:**
- Alpha framework — API may change, 3 contributors (1 is a bot)
- No template-as-data either — defines graphs in Python, not JSON/YAML
- Would require full rewrite
- Small community — bugs are our responsibility
- SqliteCheckpointer not battle-tested

### Custom Engine (~300-400 lines)

**Pros:**
- No dependencies — full control
- Templates are JSON — exactly the n8n-style paradigm
- State is a generic dict — no TypedDict constraints
- HITL = pause + save to SQLite + resume — simple
- ~300-400 lines total vs ~800 current

**Cons:**
- Build from scratch — no free validation, no composition primitives
- No community, no docs beyond ours
- Need to build: executor, checkpointing, HITL pause/resume, template validation

### Agnostic Layer (Works with Any Engine)

Regardless of the engine, the **template format** is the same. Example:

```json
{
  "name": "bug-fix-simple",
  "nodes": ["research", "hitl:diagnosis", "implement", "audit"],
  "hitl": {
    "diagnosis": {
      "question": "Confirm diagnosis?",
      "options": ["confirm", "reject"],
      "routing": {"confirm": "implement", "reject": "finalize"}
    }
  },
  "loops": [{"from": "audit", "to": "implement", "max": 2}]
}
```

This layer translates to whatever engine executes it. The builder takes a spec + available node factories → compiles a runnable graph.

## Open Design Questions (NOT YET DECIDED)

1. **Which engine?** LangGraph + builder layer, Hypergraph, or custom
2. **Template format** — JSON, YAML, or Python dicts? (JSON is most portable)
3. **Template storage** — File system, SQLite, or both?
4. **Template library** — Are the 6 current workflows default templates that users can modify?
5. **Dynamic prompts** — Current nodes branch on `workflow_type`. Without hardcoded workflows, how does each node know what prompt to use? Options: pass context dict, or each template specifies prompt variants
6. **Validation** — How to validate a template compiles to a valid graph before execution?
7. **MCP tool interface** — `run_workflow` currently takes `workflow` (name). New API would take a template or template name
8. **State schema** — Whether to keep TypedDict or go generic dict

## Decision Log

- **2026-04-25**: Phase 3 completed (commit f14c3d8). All SOUL.md and Skills updated.
- **2026-04-26**: Christopher proposed template/playground model. Key insight: "like n8n, templates as data never fail because modules are tested, you just connect them."
- **2026-04-26**: Framework research completed. Hypergraph evaluated. Conclusion: all three options require a template layer. The template layer is the core value, not the engine.