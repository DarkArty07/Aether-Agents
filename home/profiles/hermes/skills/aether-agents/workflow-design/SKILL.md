---
name: workflow-design
description: Design principles and approved workflow definitions for the Olympus workflow engine. Defines the 6 canonical workflows, agent participation maps, state schema, and conditional edges.
version: 1.0.0
category: aether-agents
triggers:
  - when designing or modifying Olympus workflows
  - when adding new workflow definitions to definitions.py
  - when changing WorkflowState fields
---

# Workflow Engine Design — Aether Agents

## Critical Methodology Rule

**ALWAYS read SOUL.md + workflow skills before designing workflows.** Never design based on generic role assumptions. Each Daimon has specific constraints that affect workflow design. The first attempt at designing workflows used generic "security engineer" assumptions — that produced incorrect agent assignments (e.g., putting Ariadna in research synthesis, putting Daedalus only in "design-first" as a separate workflow). Reading the actual SOUL.md files corrected these mistakes.

Key traps to avoid:
- **Don't assume agent capabilities from their role name** — Read their SOUL.md "Limits" section. Etalides NEVER recommends (only reports facts). Daedalus ALWAYS generates specs (not just UI). Athena CANNOT research web.
- **Don't create workflows that duplicate each other** — "design-first" was proposed as a separate workflow, but design should be a conditional path within "feature", not its own workflow.
- **Don't put agents where they don't belong** — Ariadna synthesizes sprint data, NOT research. Research synthesis is Hermes' job outside the workflow.
- **Don't confuse workflow parameters with branching decisions** — `needs_research` and `has_ui` are set by Hermes BEFORE launching the workflow, not mid-workflow decisions.

---

## The 6 Canonical Workflows

These replace the 3 experimental workflows (dev_and_audit, research_and_implement, full_pipeline).

### 1. `project-init` — Fundacional (1x per project)

**Purpose:** Initialize project structure — `.eter/`, DESIGN.md, alignment.

```
INPUT: user_prompt, project_root
  |
  +-> Ariadna (create .eter/ structure + CURRENT.md + LOG.md)
  |
  +-> Finalize (project initialized)
```

- Only Ariadna participates — no code, no UI, no security at this stage
- Hermes provides project_root and user_prompt before invoking

### 2. `feature` — Daily workhorse (70% of usage)

**Purpose:** Implement a feature end-to-end, from research to audit.

**Conditional parameters (set by Hermes before launch):**
- `needs_research: bool` — skip Etalides if false
- `has_ui: bool` — changes Daedalus prompt (UI vs internal flow design)

```
INPUT: user_prompt, project_root, needs_research, has_ui
  |
  +-> Etalides (ONLY if needs_research=true)
  |     +-> skip if false, go directly to Daedalus
  |
  +-> Daedalus (ALWAYS — generates flow/layout specs for Hefesto)
  |     +-> context += design
  |
  +-> Hefesto (implements based on accumulated context)
  |     +-> code
  |
  +-> Athena (security audit)
  |     +-> PASSES -> finalize
  |     +-> FAILS -> Hefesto (fix) -> loop (max 3 cycles)
  |
  +-> Finalize
```

**Why Daedalus ALWAYS:** Even non-UI features need user flows and specs. Daedalus designs experiences (API flows, data flows), not just screens.

**Edges:**
- `should_enter_research`: if `needs_research` -> "research", else -> "design"
- `should_terminate_on_error`: if errors -> "finalize"
- `should_retry_implementation`: if audit failed & under max cycles -> "implement"

### 3. `bug-fix` — Reactive diagnosis and fix

**Purpose:** Diagnose root cause, implement fix, verify security.

```
INPUT: user_prompt, project_root
  |
  +-> Etalides (research: known issues, error docs, stack traces)
  |     +-> research += diagnosis
  |
  +-> Hefesto (implements fix based on diagnosis)
  |     +-> code
  |
  +-> Athena (verifies fix doesn't introduce vulnerabilities)
  |     +-> PASSES -> finalize
  |     +-> FAILS -> Hefesto (refine) -> loop (max 2 cycles)
  |
  +-> Finalize
```

**Why Etalides first:** Hefesto's SOUL says "Do NOT research broadly". Bug diagnosis requires web research (known issues, framework docs).

**No Daedalus:** Bugs don't need UX design. No Ariadna: bugs are reactive, no sprint planning.

**Max review cycles: 2** — bug fixes should be precise.

### 4. `security-review` — Proactive deep audit

**Purpose:** Comprehensive security audit with CVE research.

```
INPUT: user_prompt (audit scope), project_root
  |
  +-> Etalides (CVE research, dependency vulnerabilities, security context)
  |     +-> research += security context
  |
  +-> Athena (STRIDE threat modeling + full security review)
  |     +-> audit_result + audit_passed
  |
  +-> Has critical/high findings? -> Hefesto (fix) -> Athena (re-verify) -> loop (max 2)
  |
  +-> No critical findings -> Finalize
```

**Why Etalides first:** Athena's SOUL: "Do NOT research the web — request CVE research from Etalides via Hermes". In a workflow, Hermes isn't mid-loop, so Etalides goes first.

**Edge:** `has_critical_findings` -> if audit finds Critical/High severity -> "implement", else -> "finalize"

**Max review cycles: 2** — security fixes should be precise.

### 5. `research` — Pure knowledge gathering

**Purpose:** Research a technical topic. No code output, just structured findings.

```
INPUT: user_prompt (research question), project_root
  |
  +-> Etalides (investigate with standard link budget)
  |     +-> research
  |
  +-> Finalize (structured Findings/Sources/Confidence output)
```

**Why only Etalides:** He's the ONLY web researcher. Who synthesizes? **Hermes** — outside the workflow. Hermes receives the research output and presents options to the user.

**Ariadna does NOT synthesize research** — her SOUL is project tracking, not knowledge synthesis.

### 6. `refactor` — Improve existing code

**Purpose:** Rewrite, optimize, clean code without changing functionality.

```
INPUT: user_prompt (what to refactor), project_root
  |
  +-> Etalides (impact mapping: dependencies, breaking changes, relevant docs)
  |     +-> research += impact map
  |
  +-> Hefesto (refactors based on impact map)
  |     +-> code
  |
  +-> Athena (verifies security not degraded by refactor)
  |     +-> PASSES -> finalize
  |     +-> FAILS -> Hefesto (adjust) -> loop (max 2 cycles)
  |
  +-> Finalize
```

**Why Etalides:** Refactoring without knowing what depends on the code is dangerous. Etalides maps impact.

**No Daedalus:** Refactors don't change UX.

**Max review cycles: 2**

---

## Participation Map

| Daimon     | project-init | feature | bug-fix | security-review | research | refactor |
|------------|:---:|:---:|:---:|:---:|:---:|:---:|
| Ariadna    |  *  |     |     |      |    |         |
| Etalides   |     |  *c |  *  |   *  | *  |    *    |
| Daedalus   |     |  *  |     |      |    |         |
| Hefesto    |     |  *  |  *  |   c  |    |    *    |
| Athena     |     |  *  |  *  |   *  |    |    *    |

- * = always participates
- c = conditionally (security findings only / needs_research parameter)

---

## State Schema (WorkflowState)

### Existing fields (keep)
```python
user_prompt: str
context: str           # Accumulated context from prior nodes
code: str             # Implementation output
audit_result: str     # Athena's audit output
audit_passed: bool   # Whether audit passed
research: str         # Etalides research output
messages: Annotated[list, add_messages]
review_cycles: int
max_review_cycles: int
final_response: str
project_root: str
errors: Annotated[list[str], add_messages]
status: str           # "running" | "completed" | "failed" | "stalled"
started_at: float
node_name: str
```

### New fields needed
```python
needs_research: bool          # feature: skip Etalides if false
has_ui: bool                  # feature: changes Daedalus prompt
workflow_type: str            # "project-init" | "feature" | "bug-fix" | "security-review" | "research" | "refactor"
hitl_decisions: Annotated[list[str], add_messages]  # User decisions at interrupt points (audit trail, same reducer pattern as errors)
```

---

## Conditional Edge Functions

### Existing (keep)
- `should_terminate_on_error(state)` -> "continue" if no errors, "finalize" if errors
- `should_retry_implementation(state)` -> "implement" if audit failed & under max cycles, "finalize" otherwise

### New
- `should_enter_research(state)` -> "research" if `needs_research` is True, else skip to next node
- `has_critical_findings(state)` -> "implement" if severity is "critical" or "high", else "finalize"
- `should_enter_design(state)` -> "design" if `skip_design` is False, else skip to implement
- `should_enter_audit(state)` -> "audit" if `skip_audit` is False, else "finalize"

---

## Design Decisions Log

1. **Removed 3 experimental workflows** (dev_and_audit, research_and_implement, full_pipeline) — they proved LangGraph works, now replaced by purpose-built workflows.

2. **Daedalus always in `feature`** — Even non-UI features need user flow specs. A feature without design is Hefesto guessing.

3. **Etalides before Hefesto in bug-fix and refactor** — Hefesto's SOUL explicitly forbids broad research. Impact analysis must come first.

4. **Etalides before Athena in security-review** — Athena's SOUL says "Do NOT research the web — request CVE research from Etalides". In workflows, Hermes isn't mid-loop to route, so Etalides goes first.

5. **Hermes synthesizes research output, not Ariadna** — Ariadna tracks sprints. Etalides reports facts. Hermes synthesizes and decides.

6. **Conditional edges are STATE-BASED, not runtime decisions** — Parameters like `needs_research` are set by Hermes before launching `run_workflow`. LangGraph edges read state, not call Hermes.

7. **Max review cycles differ by workflow** — feature: 3, bug-fix: 2, security-review: 2, refactor: 2. Security and bug fixes should be precise.

8. **HITL (Human-in-the-Loop) via interrupt() is the key differentiator** — Without HITL, workflows run blind. With `interrupt()`, Christopher decides at critical points (design approval, diagnosis confirmation, security findings). This transforms workflows from pipelines into collaborative processes.

9. **Command routing replaces separate conditional edge functions** — Instead of `should_retry_implementation()` reading state and returning a string, nodes can return `Command(update={...}, goto=...)` that updates state AND decides next node simultaneously. Cleaner, fewer helper functions.

10. **InMemorySaver checkpointer is required for HITL** — `interrupt()` only works when the graph is compiled with a `Checkpointer`. Use `InMemorySaver()` for v2.0 (state lost on Hermes restart). Migrate to `SqliteSaver` for persistence in v2.1.

11. **delegate_task works for workflow engine code changes** — When Hefesto via talk_to has ACP bugs (empty responses from GLM-5.1), use `delegate_task` with a generic sub-agent instead. Sub-agents don't go through Olympus MCP, bypassing the ACP response bug. Added `langgraph-checkpoint-memory` and `langchain-core` imports (uuid7) to requirements.txt.

---

## LangGraph Features — Usage Priority

| Feature | Priority | Status | Notes |
|---------|----------|--------|-------|
| **interrupt() + Checkpointer** | 🔴 CRITICAL | Implement in Phase 2.1 | HITL is the difference between a blind pipeline and a collaborative workflow |
| **Command routing** | 🔴 CRITICAL | Implement in Phase 2.2 | Replaces conditional edge functions, simplifies definitions.py |
| **RetryPolicy** | 🟡 High | Implement in Phase 2.3 | `RetryPolicy(max_attempts=2)` on ACP nodes for resilience |
| **Send (fan-out)** | 🟢 Medium | Future (v3) | Parallel Etalides research targets. Requires state reducers. |
| **Subgraphs** | 🔵 Low | Future (v4) | Composition. Re-evaluate when workflows grow complex. |
| **Streaming** | 🔵 Low | Future | Requires MCP infrastructure change (SSE or similar). |

---

## HITL Checkpoints by Workflow

| Workflow | Checkpoint | Node | Question | Options |
|----------|-----------|------|----------|---------|
| feature | After Etalides | research_review | ¿Research suficiente para proceder? | approve / reject |
| feature | After Daedalus | design_review | ¿Apruebas este diseño? | approve / reject / modify |
| feature | After Athena | audit_review | Findings de seguridad — ¿Aplicar fixes? | approve / accept_risk / reject |
| bug-fix | After Etalides | diagnosis_review | ¿Confirmas este diagnóstico? | confirm / reject |
| security-review | After Athena | findings_review | Findings de seguridad — ¿Proceder con fixes? | approve / accept_risk / reject |
| refactor | After Etalides | scope_review | ¿Proceder con este alcance? | approve / reject |

HITL works via `interrupt()` in LangGraph. The workflow pauses, saves state to checkpointer, and returns `__interrupt__` to the caller. Christopher responds via `Command(resume="approve")` with the same thread_id.

---

## MCP Server API Changes for HITL

`run_workflow` now accepts:
- `thread_id`: Required for HITL. Auto-generated if not provided.
- `params`: Workflow-specific parameters (`needs_research`, `has_ui`, `max_review_cycles`).
- `resume`: Only for resuming paused workflows. Value = user's interrupt decision.

When a workflow hits an `interrupt()`, the response includes:
```json
{
    "status": "interrupted",
    "thread_id": "...",
    "interrupt": {
        "question": "¿Apruebas este diseño?",
        "context": "...",
        "options": ["approve", "reject", "modify"],
        "node": "design_review"
    }
}
```

---

## Implementation Phases

### Phase 2.1: Foundations (state.py, runner.py, server.py) — COMPLETED (commit df4f038)
- Expand WorkflowState with new fields
- Add InMemorySaver checkpointer
- Update run_workflow for thread_id, params, resume
- Implement HITL detection and response format
- Added langgraph-checkpoint-memory to requirements.txt

### Phase 2.2: Nodes, Prompts, HITL Factory — COMPLETED (commit 2da935e)
- Created `prompts.py` with 21 templates across 5 categories (research 5, design 2, implement 7, audit 5, onboard 1) + `get_prompt()` factory for reference/future use
- Refactored `make_node_design` — checks `has_ui` for UI vs internal prompts, includes research context
- Refactored `make_node_implement` — branches on `workflow_type` (bug-fix, security-review, refactor, feature) with audit refinement logic
- Refactored `make_node_audit` — branches on `workflow_type` + `review_cycles` (initial STRIDE for security, re-verification for fixes, standard for features)
- Refactored `make_node_research` — branches on `workflow_type` (diagnosis, CVEs, impact map, general)
- Refactored `node_finalize` — adapts output by `workflow_type`, includes `hitl_decisions` section, proper section headers
- Added `make_node_onboard` — Ariadna node for project-init
- Added `make_node_hitl` — factory that returns async nodes using `interrupt()` + `Command(update={...}, goto=...)` routing
- Updated `__init__.py` — exports all new factories + `get_prompt`
- **Implementation note:** Nodes inline prompts by `workflow_type` rather than calling `get_prompt()`. The `prompts.py` module is the canonical reference but nodes build prompts inline for now — avoids double indirection and makes debugging easier

### Phase 2.3: Workflows (definitions.py) — PENDING
- Delete 3 old workflows (dev_and_audit, research_and_implement, full_pipeline)
- Implement 6 new workflow definitions with HITL interrupt nodes and Command edges
- Add RetryPolicy(max_attempts=2) to ACP nodes

### Phase 2.4: Testing
- Unit tests per node with mock ACP
- Integration tests per workflow end-to-end
- HITL tests: interrupt → resume cycle
- Error propagation tests