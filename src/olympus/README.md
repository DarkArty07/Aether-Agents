# Olympus — Workflow Engine for Aether Agents

Olympus is the MCP server that powers Aether Agents' multi-agent orchestration. It exposes two tools to Hermes (or any MCP-compatible agent):

- **`talk_to`** — Communicate with Daimons (open, message, poll, wait, cancel, close)
- **`run_workflow`** — Execute structured multi-step workflows with Human-in-the-Loop (HITL)

---

## Architecture

```
Hermes (MCP client)
    → MCP stdio
        → Olympus Server (server.py)
            → ACPManager (acp_client.py)
                → Daimons (hermes acp processes)
            → WorkflowRunner (workflows/runner.py)
                → LangGraph StateGraph
                    → Nodes → Daimons via ACP
                    → HITL interrupts → Hermes presents to user
```

### Components

| File | Purpose |
|------|---------|
| `server.py` | MCP server entry point. Tool handlers for `talk_to` and `run_workflow`. Manages checkpointer lifecycle. |
| `acp_client.py` | ACP protocol client. Spawns and communicates with Daimon processes via stdin/stdout JSON. |
| `config.py` | Configuration from environment variables and AETHER_HOME path resolution. |
| `discovery.py` | Discovers available Daimon profiles from the filesystem. |
| `registry.py` | Session tracking — manages open sessions, status, and cleanup. |
| `workflows/state.py` | `WorkflowState` TypedDict — shared state across all workflow nodes. |
| `workflows/nodes.py` | Node factories — `make_node_*()` functions that create LangGraph nodes wrapping Daimon calls. |
| `workflows/definitions.py` | 6 pre-defined workflow graphs built with LangGraph's `StateGraph`. |
| `workflows/runner.py` | `WorkflowRunner` — invokes LangGraph graphs with checkpointing and HITL resume. |

---

## Workflows

Olympus provides 6 pre-defined workflows, each tailored to a specific development task:

### 1. `project-init` (3 nodes, no HITL)

Quick project bootstrap. Hermes onboards the project and produces initial documentation.

```
START → onboard → finalize → END
```

### 2. `feature` (11 nodes, 3 HITL checkpoints)

Full feature development lifecycle with research, design, implementation, and auditing.

```
START → [research?] → research → research_review ★
     → design → design_review ★
     → implement → audit → audit_review ★
     → implement_fix → re_audit → (loop or finalize)
     → finalize → END
```

**HITL points:** research_review, design_review, audit_review

### 3. `bug-fix` (6 nodes, 1 HITL)

Research → diagnose → confirm → fix → audit loop.

```
START → research → diagnosis_review ★ → implement → audit → (loop or finalize) → END
```

**HITL point:** diagnosis_review

### 4. `security-review` (7 nodes, 1 HITL)

Security-focused research and audit with fix loop.

```
START → research → audit → findings_review ★
     → implement_fix → re_audit → (loop or finalize)
     → finalize → END
```

**HITL point:** findings_review

### 5. `research` (3 nodes, no HITL)

Simple research pipeline — Etalides researches, then finalizes.

```
START → research → finalize → END
```

### 6. `refactor` (6 nodes, 1 HITL)

Analyze scope → approve → implement → audit loop.

```
START → research → scope_review ★ → implement → audit → (loop or finalize) → END
```

**HITL point:** scope_review

---

## Human-in-the-Loop (HITL)

HITL is the core interactive mechanism. When a workflow reaches a review node, it **interrupts** and returns control to the calling agent (Hermes) with:

- **Context** — what was produced (research, design, audit results)
- **Question** — what the user needs to decide
- **Options** — valid choices (approve, reject, modify, accept_risk, confirm)
- **`thread_id`** — required to resume the workflow

The agent (Hermes) presents this information **conversationally** — not as JSON buttons or structured forms. The user responds naturally, and the agent maps that response to the appropriate option and resumes the workflow.

### HITL Flow

```
1. User: "Fix the login bug"
2. Hermes → run_workflow(workflow="bug-fix", prompt="Fix the login bug")
3. Workflow runs research...
4. Workflow interrupts at diagnosis_review
5. Server returns: "🛑 Workflow paused for human review..."
6. Hermes presents: "Etalides encontró que el bug es X. Confirmas?"
7. User: "Sí, confirma"
8. Hermes → run_workflow(thread_id="...", resume="confirm")
9. Workflow continues → implement → audit → finalize
10. Server returns final result
```

### Checkpointing

HITL interrupts are persisted using **AsyncSqliteSaver** (LangGraph's SQLite checkpointer). This means:

- **Workflows survive server restarts** — checkpoint data is stored in `{AETHER_HOME}/.olympus_checkpoints.db`
- **No data loss** — if Olympus restarts, the user can still resume their workflow
- **`ainvoke()` for resume** — all resume operations use async invocation (required by AsyncSqliteSaver)

---

## WorkflowState

All workflows share a single `WorkflowState` TypedDict:

| Field | Type | Purpose |
|-------|------|---------|
| `user_prompt` | `str` | Original task description |
| `context` | `str` | Accumulated context for Daimons |
| `code` | `str` | Generated/modified source code |
| `audit_result` | `str` | Audit findings from Athena |
| `audit_passed` | `bool` | Whether audit passed |
| `research` | `str` | Research results from Etalides |
| `messages` | `Annotated[list, add_messages]` | LangGraph message accumulator |
| `review_cycles` | `int` | Count of audit-implement loops |
| `max_review_cycles` | `int` | Maximum loops before force-finalize |
| `final_response` | `str` | Workflow result for the user |
| `project_root` | `str` | Project directory path |
| `errors` | `Annotated[list[str], operator.add]` | Accumulated errors (operator.add, NOT add_messages) |
| `status` | `str` | "running" \| "completed" \| "failed" \| "stalled" |
| `started_at` | `float` | Wall-clock timestamp (time.time()) |
| `node_name` | `str` | Current node name for logging |
| `needs_research` | `bool` | feature: whether to include research step |
| `has_ui` | `bool` | feature: whether the feature has UI components |
| `workflow_type` | `str` | Workflow identifier string |
| `hitl_decisions` | `Annotated[list[str], operator.add]` | Accumulated user decisions (operator.add, NOT add_messages) |

> **Important:** `errors` and `hitl_decisions` use `operator.add` (not LangGraph's `add_messages`). Using `add_messages` causes strings to be coerced into `HumanMessage` objects, which crashes on `'; '.join()`.

---

## Error Handling

- **Node-level:** Each node catches `Exception` (broad, not just `RuntimeError`) and stores errors in `state["errors"]`
- **Workflow-level:** `should_terminate_on_error()` checks if errors exist and routes to `finalize` instead of continuing
- **Stall detection:** If no node produces output within 120 seconds, the workflow marks status as "stalled"
- **Safety net:** Hard timeout of 30 minutes per workflow execution

---

## Configuration

The MCP server runs as a stdio subprocess. Configure it in `home/config.yaml`:

```yaml
mcp_servers:
  olympus:
    command: /path/to/venv/bin/python
    args: ["-m", "olympus.server"]
    env:
      AETHER_HOME: /path/to/Aether-Agents/home
```

Required Python packages (installed via `pip install -e .`):

- `mcp` — MCP protocol server
- `langgraph` — Workflow graph engine
- `langgraph-checkpoint-sqlite` — Persistent checkpointing (AsyncSqliteSaver)
- `langgraph-graph` — Graph primitives (StateGraph, Command, interrupt)