---
name: workflow-design
description: Design principles and approved workflow definitions for the Olympus workflow engine. Defines the 6 canonical workflows, agent participation maps, state schema, and conditional edges.
version: 1.1.0
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
messages: Annotated[list, add_messages]  # OK — this IS for chat messages
review_cycles: int
max_review_cycles: int
final_response: str
project_root: str
errors: Annotated[list[str], operator.add]  # MUST use operator.add, NOT add_messages
status: str           # "running" | "completed" | "failed" | "stalled"
started_at: float     # MUST use time.time(), NOT time.monotonic()
node_name: str
```

### New fields needed
```python
needs_research: bool          # feature: skip Etalides if false
has_ui: bool                  # feature: changes Daedalus prompt
workflow_type: str            # "project-init" | "feature" | "bug-fix" | "security-review" | "research" | "refactor"
hitl_decisions: Annotated[list[str], operator.add]  # MUST use operator.add, NOT add_messages
```

---

## Conditional Edge Functions

### In use (definitions.py)
- `should_terminate_on_error(state)` -> "continue" if no errors, "finalize" if errors
- `should_enter_research(state)` -> "research" if `needs_research` is True, else skip to next node
- `should_audit_pass(state)` -> "implement" if audit failed & under max cycles, "finalize" if passed
- `should_reaudit_pass(state)` -> "implement" if re-audit failed & under max cycles, "finalize" if passed
- `has_critical_findings(state)` -> "implement" if severity is "critical" or "high", else "finalize"

### Removed (dead code — never called)
- `should_audit_pass_feature()` — removed in cleanup commit 042ac20
- `should_retry_implementation()` — removed in cleanup commit 042ac20

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

10. **AsyncSqliteSaver checkpointer is required for HITL** — `interrupt()` only works when the graph is compiled with a `Checkpointer`. **MUST use `AsyncSqliteSaver` from `langgraph.checkpoint.sqlite.aio`**, NOT `InMemorySaver` or sync `SqliteSaver`. InMemorySaver loses all checkpoints on server restart (HITL resumes fail because thread_id no longer exists). Sync SqliteSaver raises `"The SqliteSaver does not support async methods"` when used with `ainvoke()`. AsyncSqliteSaver persists checkpoints to `{AETHER_HOME}/.olympus_checkpoints.db`, surviving restarts. **Pitfall:** `AsyncSqliteSaver.from_conn_string()` returns an `AsyncContextManager`, not an instance directly. Use `await cm.__aenter__()` to get the saver, and store the CM in a global to keep the connection alive. The `langgraph-checkpoint-sqlite` package must be installed in the SAME venv that runs the Olympus MCP server (the hermes-agent venv, not just the project venv).

11. **delegate_task works for workflow engine code changes** — When Hefesto via talk_to has ACP bugs (empty responses from GLM-5.1), use `delegate_task` with a generic sub-agent instead. Sub-agents don't go through Olympus MCP, bypassing the ACP response bug. Added `langgraph-checkpoint-memory` and `langchain-core` imports (uuid7) to requirements.txt.

12. **LangGraph Interrupt objects are NOT plain dicts** — When `ainvoke()` hits an `interrupt()`, the result dict contains `__interrupt__` key with a list of `Interrupt` objects (NOT plain dicts). Each `Interrupt` has `.value` (the payload dict you passed to `interrupt()`) and `.ns` (namespace). You MUST extract `.value` before JSON serialization, or you get `"Object of type Interrupt is not JSON serializable"`. See runner.py for the conversion pattern.

13. **Resume MUST use `ainvoke()` (async), NOT `invoke()` (sync)** — Both fresh starts and resumes must use `ainvoke()`. Using `app.invoke()` for resume crashes with checkpointer errors. Always use `await app.ainvoke()` with thread_id config. This applies to InMemorySaver, SqliteSaver, and AsyncSqliteSaver — all require async invocation for LangGraph's interrupt/checkpoint mechanism.

14. **HITL responses must be conversational, NOT raw JSON** — The MCP tool should return human-readable messages at interrupt points, not the raw internal JSON structure. The calling agent (Hermes or any other) receives a formatted message explaining: what happened, the context, available options, and instructions to resume. This is critical because raw JSON interrupts confuse agents — they don't know what to do with `{"status": "interrupted", ...}`. The tool description itself serves as the behavior contract: it instructs the agent to present the context conversationally, ask the user for their decision, then resume with that decision. This is cleaner than modifying agent soul.md because any agent using the tool gets the instructions automatically.

15. **HITL nodes with Command(goto=...) do NOT need outgoing edges** — When a node returns `Command(update={...}, goto="next_node")`, LangGraph routes to `goto` directly. Do NOT add `add_conditional_edges` from that node. But ALL possible goto targets must be registered as nodes in the graph. This is different from traditional conditional edges — Command nodes are self-routing.

16. **Hermes MUST restart for workflow engine changes to take effect** — Olympus MCP server runs as a subprocess under the Hermes gateway. Code changes to `src/olympus/workflows/` are not hot-reloaded. Use `hermes gateway restart` to load new code. This kills the current session — the user must reconnect to Telegram.

17. **MCP server restart = InMemorySaver data loss** — If the Olympus MCP server process restarts (crash, gateway restart, code update), InMemorySaver checkpoints vanish. Any attempt to `resume` with a thread_id from before the restart starts the workflow from scratch. AsyncSqliteSaver with persistent `.db` file fixes this completely — checkpoints survive process restarts, gateway restarts, and machine reboots.

18. **langgraph-checkpoint-sqlite must be installed in the Hermes agent venv** — The Olympus MCP server runs as a subprocess of the Hermes gateway, using the Hermes agent's Python (`/home/prometeo/.hermes/hermes-agent/venv/bin/python`). Installing the package only in the project venv causes `ModuleNotFoundError` at runtime. Use `uv pip install --python /home/prometeo/.hermes/hermes-agent/venv/bin/python langgraph-checkpoint-sqlite`.

19. **`add_messages` reducer MUST NOT be used for plain string lists** — LangGraph's `add_messages` reducer is designed for chat message objects. When used on `errors: Annotated[list[str], add_messages]` or `hitl_decisions: Annotated[list[str], add_messages]`, it converts plain strings into `HumanMessage` objects. This crashes `node_finalize` with `TypeError: expected str instance, HumanMessage found` when calling `'; '.join(errors)`. **Always use `operator.add` for plain string list accumulators, NOT `add_messages`.** Only use `add_messages` for actual chat message fields.

20. **Redundant START edges break conditional routing** — In LangGraph, if you add both `add_edge(START, "node_a")` and `add_conditional_edges(START, func, {...})`, the conditional edges override the static ones. This produces confusing code and may break in future LangGraph versions. **Never add a static `add_edge(START, ...)` when there's also a `add_conditional_edges(START, ...)` for the same source.** Remove the static edge.

21. **AsyncSqliteSaver context manager lifecycle** — `AsyncSqliteSaver.from_conn_string(path)` returns an `AsyncContextManager`, NOT an instance. You MUST call `await cm.__aenter__()` to get the saver and keep the CM alive in a global variable. Call `await cm.__aexit__(None, None, None)` on shutdown. Simply assigning `AsyncSqliteSaver.from_conn_string(path)` to a variable and calling `.setup()` crashes with `AttributeError: '_AsyncGeneratorContextManager' object has no attribute 'setup'`.

22. **Node exception handling must catch `Exception`, not just `RuntimeError`** — ACP sessions can fail with `ValueError` (unknown agent), connection errors, or any exception. Nodes that only catch `RuntimeError` let these propagate and crash the entire `ainvoke()`. Always use `except Exception as e:` in node factories to return error state dicts gracefully.

23. **`time.monotonic()` is meaningless across server restarts** — `started_at` used `time.monotonic()` which returns time since an arbitrary reference (usually boot). After restart, this value is garbage. Use `time.time()` (wall clock) for timestamps that need to survive checkpoints.

24. **Dead code removal is safe after live testing** — After all 3 workflow live tests passed (bug-fix, research, refactor), a systematic dead code audit found 16 items. 299 lines removed (2473 → 2174) with zero regressions. Key removals: `prompts.py` (prompts inline in nodes.py), `log.py` (placeholder never imported), `should_audit_pass_feature` and `should_retry_implementation` (never called), `_discovered_profiles` from OlympusRegistry, unused config fields (`log_file`, `session_timeout`, `shutdown_timeout`), `acp_process` from SessionState, dead exports from `__init__.py`, and 4 `# CHANGE N:` comments + "A hack" comment. Lesson: remove dead code only AFTER live verification, not before — some "dead" functions may be called indirectly via dynamic dispatch or reflection.

25. **`log.py` was a phantom module** — Created as a placeholder during initial development but never imported by any module. For workflow engines, logging should use the existing `logging` module or `structlog` rather than creating custom log abstractions. The Olympus server uses FastAPI/MCP logging.

26. **Don't export convenience functions from `__init__.py` that nobody imports** — `should_retry_implementation` and `get_prompt` were exported from `__init__.py` but never imported by any module. Dead exports create false assumptions that code is "in use" and make refactoring harder. Only export what's actually imported.

--- — Usage Priority

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

When a workflow hits an `interrupt()`, the response is a **conversational message** (not raw JSON) that includes:
- What happened and which node interrupted
- The thread_id needed to resume
- The question being asked (e.g., "¿Apruebas este diseño?")
- Available options (e.g., approve / reject / modify)
- Agent context (research findings, design specs, etc.)
- Instructions: present this to the user conversationally, ask for their decision, then call `run_workflow` with `resume=<decision>` and `thread_id=...`

This conversational format was chosen over raw JSON or button-based UX because: (1) agents using the MCP tool need clear instructions on how to handle interrupts, (2) the tool description itself is the behavior contract — any agent using it gets the instructions automatically, (3) the user explicitly rejected button-based UX in favor of natural conversation.

---

## Hermes Usage Guide — Practical Few-Shots

### Tip 1: Elegir el workflow correcto

| Diálogo del usuario | Workflow | Parámetros |
|---------------------|----------|-----------|
| "Implementa X desde cero" | `feature` | needs_research=true, has_ui=variable |
| "Arregla este bug" | `bug-fix` | — |
| "Audita la seguridad" | `security-review` | — |
| "Investiga X" | `research` | — |
| "Refactoriza X" | `refactor` | — |
| "Nuevo proyecto" | `project-init` | — |
| "Diseña la UI de X" | `talk_to(daedalus)` | No es workflow |
| "Quick security check" | `talk_to(athena)` | No es workflow |
| "Un endpoint simple" | `delegate_task` | No es workflow |

### Tip 2: Manejar interrupts

Interrupts vienen en este formato:
```json
{
  "status": "interrupted",
  "thread_id": "01923abc-...",
  "interrupt": [{
    "question": "¿Apruebas este diseño?",
    "options": ["approve", "reject", "modify"],
    "context": "Daedalus diseñó: ...",
    "workflow": "feature",
    "node": "design_review"
  }]
}
```

SIEMPRE presentar al usuario de forma conversacional, NO como JSON crudo.
SIEMPRE incluir el thread_id al reanudar.

### Tip 3: Parámetros de feature

- `needs_research=true`: Feature nuevo que requiere investigación previa (librerías, patrones, APIs)
- `needs_research=false`: Feature bien definido, no necesita research (ej: implementar endpoint específico)
- `has_ui=true`: Feature con interfaz de usuario → Daedalus diseña UI flows
- `has_ui=false`: Feature interno (API, middleware, backend) → Daedalus diseña API/data flows

### Tip 4: Contexto acumulado

Cada nodo en el workflow recibe `state["context"]` con el output de nodos previos.
Etalides pasa research a Daedalus, Daedalus pasa diseño a Hefesto, etc.
NO es necesario pasar contexto manualmente — el workflow lo acumula automáticamente.

---

## Implementation Phases

### Phase 2.1: Foundations (state.py, runner.py, server.py) — COMPLETED (commit df4f038, then migrated to AsyncSqliteSaver in commit 91f6cf5)
- Expand WorkflowState with new fields
- Add checkpointer for HITL (migrated from InMemorySaver → AsyncSqliteSaver)
- Update run_workflow for thread_id, params, resume
- Implement HITL detection and response format
- AsyncSqliteSaver persists checkpoints to `{AETHER_HOME}/.olympus_checkpoints.db`
- `langgraph-checkpoint-sqlite` must be installed in hermes-agent venv

### ⚠️ PITFALL: Interrupt object serialization

LangGraph returns `Interrupt` objects (not plain dicts) inside the `__interrupt__` list. Each `Interrupt` has `.value` (the payload dict) and `.ns` (namespace). `json.dumps()` fails with `"Object of type Interrupt is not JSON serializable"`. Fix in runner.py: iterate `__interrupt__`, extract `.value` attribute, convert dicts to serializable form. Without this fix, HITL workflows crash at the first interrupt point.

### ⚠️ PITFALL: MCP tool call timeout kills long workflows

The `run_workflow` MCP tool is synchronous — Hermes blocks until result. But workflows take 2-5+ min per node (Etalides researching, Hefesto coding). The MCP framework timeout (2-3 min) expires before the workflow reaches an interrupt point. This causes: (1) Hermes gets TimeoutError, (2) Olympus continues running in background, (3) workflow hangs at interrupt with no caller listening. **Architectural limitation** — needs async execution with polling, increased timeout, or Hermes-level orchestration. **Fix applied:** Set `timeout: 600` in the Olympus MCP config in `config.yaml` (10 minutes). This covers most single-node agent calls (Etalides research took 223.9s in live test).

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
- **Implementation note:** Nodes inline prompts by `workflow_type`. The `prompts.py` module was removed in cleanup (commit 042ac20) — all prompts are now inline in `nodes.py`. The `get_prompt()` export was also removed from `__init__.py`. No double indirection; all prompt text is co-located with node logic

### Phase 2.3: Workflows (definitions.py) — COMPLETED (commit 957d993)
- Deleted 3 old workflows (dev_and_audit, research_and_implement, full_pipeline) — now raise ValueError
- Implemented 6 new workflow definitions with HITL interrupt nodes and Command edges
- Conditional routing functions: should_research, should_audit_pass_feature, should_audit_pass, should_reaudit_pass

### Phase 2.4: Testing — COMPLETED
- All 10 tests passed: imports, compilations, HITL flow, conditional edges, server.py, runner.py, graph structure, invalid names, exports, prompts coverage
- Real HITL test (bug-fix workflow) revealed critical serialization bug

### Phase 2.5: Audit & Live Testing — COMPLETED (commit a868c78)

Comprehensive audit of all workflow engine code found 5 bugs (2 critical, 3 warning). All fixed and verified with 3 live workflow tests.

**Critical bugs fixed:**
1. `add_messages` reducer on `errors` and `hitl_decisions` state fields → converted strings to HumanMessage objects, crashing `node_finalize` with TypeError. Fix: `operator.add`.
2. Redundant `add_edge(START, "research")` in feature workflow conflicting with `add_conditional_edges(START, should_research, ...)`. Fix: removed the static edge.

**Warning bugs fixed:**
3. `InMemorySaver` → `AsyncSqliteSaver` (checkpoints lost on server restart, breaking HITL resume). Sync `SqliteSaver` also fails: `"does not support async methods"`. Fix: `AsyncSqliteSaver.from_conn_string()` with `__aenter__()` lifecycle.
4. `except RuntimeError` in all 5 node factories → broadened to `except Exception` (ValueError, connection errors, ACP failures were uncaught).
5. `time.monotonic()` in state `started_at` → changed to `time.time()` (monotonic is meaningless across restarts).

**Live test results (3 workflows verified):**
- `bug-fix`: ✅ HITL interrupt at diagnosis_review → resume with "confirm" → full pipeline completion
- `research`: ✅ No-HITL workflow completed end-to-end without errors
- `refactor`: ✅ HITL interrupt at scope_review → resume with "approve" → full pipeline completion

**Key lesson:** Bug-after-bug pattern (InMemorySaver → SqliteSaver sync → AsyncSqliteSaver context manager) showed that HITL workflow engines need comprehensive audit before testing, not incremental fix-test cycles.

### Runtime Bug Fix (commit e69da51)
- **LangGraph Interrupt objects are NOT JSON-serializable** — `__interrupt__` returns a list of `Interrupt` objects, each with `.value` (dict payload) and `.ns` (namespace). Must extract `.value` before passing to `json.dumps()`.
- **Fix in runner.py**: iterate over `interrupt_data`, check `hasattr(entry, "value")`, extract `entry.value` if dict, else `str(entry)`.
- **Also added**: `final_state` normalization for non-dict returns from LangGraph (`dict(final_state)` fallback).
- **Pitfall**: When HITL nodes return `Command(goto=...)`, do NOT add outgoing edges from them in `add_conditional_edges`. LangGraph routes via the Command's goto value automatically. However, you must register the possible goto targets as nodes in the graph.

---

## SOUL.md + Skills Adaptation for Workflows (Phase 3 — PENDING)

When the workflow engine was built (Phases 1-2.5), SOUL.md files and workflow Skills were designed for the **fire-and-forget model** (`talk_to` — one prompt, one response). The new workflow system introduces three paradigms that existing configs don't cover:

### Gap Summary

| Gap | Impact | Affected Files |
|-----|--------|----------------|
| No `run_workflow` routing in Hermes SOUL.md or orchestration skill | Hermes doesn't know when/how to use workflows vs `talk_to` | Hermes SOUL.md, orchestration SKILL.md |
| No HITL handling instructions | Hermes won't know what to do when a workflow interrupts | Hermes SOUL.md, orchestration SKILL.md |
| Daimon SOULs only describe fire-and-forget model | Daimons won't leverage accumulated context from prior nodes | All 5 Daimon SOUL.md files |
| Daimon workflow Skills lack "In Workflow Context" guidance | Skills don't adapt output format for workflow context vs manual `talk_to` | All 5 Daimon workflow Skills |
| Orchestration skill references old workflows | Shows `dev_and_audit`, etc. instead of the 6 canonical workflows | orchestration SKILL.md | ✅ Fixed — now references 6 canonical workflows with HITL and run_workflow

### Routing Decision: `talk_to` vs `run_workflow`

**Use `talk_to` when:**
- Single Daimon, single task, no iteration needed
- Quick question (Ariadna status, Etalides fact-check)
- Session onboarding/close (Ariadna)
- The task doesn't fit any of the 6 workflow patterns

**Use `run_workflow` when:**
- 2+ Daimons in sequence with clear dependency chain
- HITL decision points are needed (approve design, confirm diagnosis, accept risk)
- Automatic audit loops are needed (implement → audit → fix → re-audit)
- The task matches one of the 6 canonical patterns

**Routing matrix by task type:**

| Task type | Tool | Workflow |
|-----------|------|----------|
| Initialize new project | `run_workflow` | `project-init` |
| Add a feature (research + design + implement + audit) | `run_workflow` | `feature` |
| Fix a bug (diagnosis + fix + verify) | `run_workflow` | `bug-fix` |
| Security audit | `run_workflow` | `security-review` |
| Research a topic | `run_workflow` | `research` |
| Refactor code | `run_workflow` | `refactor` |
| Quick security question | `talk_to` | athena |
| Single Daimon task (no workflow needed) | `talk_to` | — |
| Project status check | `talk_to` | ariadna |
| Session close | `talk_to` | ariadna |

### Hermes HITL Handling Protocol

When `run_workflow` returns `status: "interrupted"`, Hermes MUST:

1. **Parse the interrupt payload** — extract `thread_id`, context, question, options
2. **Present conversationally to user** — NOT raw JSON. Example:
   > "Etalides researched JWT libraries. Two strong candidates found: jsonwebtoken (14M downloads/week, last updated 2024) and jose (2M downloads, more modern). ¿Apruebas esta investigación para proceder al diseño?"
3. **Collect user decision** — match to available options (approve/reject/confirm/accept_risk)
4. **Resume workflow** — `run_workflow(workflow="...", thread_id="...", resume="<decision>")`

### Changes Needed Per File

| Priority | File | Change Description |
|----------|------|--------------------|
| 🔴 Critical | `orchestration/SKILL.md` | Replace old 3-workflow section with 6 canonical workflows + routing matrix + HITL few-shots + `run_workflow` examples + update pre-flight checklist |
| 🔴 Critical | `Hermes SOUL.md` | Add "Workflow Orchestration" section: routing decision, HITL handling, parameter guide by workflow type |
| 🟡 High | `workflow-design/SKILL.md` | Add "Hermes Usage Guide" section with few-shots per workflow type, parameter recommendations, interrupt handling patterns |
| 🟢 Medium | Each Daimon SOUL.md (5 files) | Add "In Workflow Context" section: how to interpret accumulated context, adapt output, handle `workflow_type` parameter |
| 🟢 Medium | Each Daimon Skill (5 files) | Add workflow context note: adapt output format when receiving enriched context from prior nodes |
| 🔵 Low | `ariadna/SOUL.md` | Minimal — only `project-init` uses her, add note about workflow participation |

### Suggested Implementation Approach

Use the **`refactor` workflow** to implement these changes:
1. Etalides maps impact (which files reference workflows, what sections, what breaks)
2. `scope_review` HITL — Christopher approves the exact scope
3. Hefesto implements the changes following the plan
4. Athena verifies cross-file consistency (references match, terminology aligned)

This is a refactor because: the files already exist, we're restructuring them to align with a new system, and the changes need cross-file consistency checks.