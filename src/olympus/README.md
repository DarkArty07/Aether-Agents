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

---

## MCP Tools API Reference

Olympus exposes 3 MCP tools to the orchestrator. All communication happens via MCP stdio.

### `mcp_olympus_discover`

Lists all available Daimon agents and their capabilities.

```
Parameters: none
Returns: { "agents": [...], "total": N }
```

### `mcp_olympus_talk_to`

Direct communication channel with a single Daimon. Session-based (open → message → poll/wait → close).

**Parameters:**

| Parameter | Type | Required | Description |
|---|---|---|---|
| `agent` | string | Yes | Daimon name: ariadna, hefesto, etalides, daedalus, athena. Use `?` to discover. |
| `action` | string | Yes | One of: discover, open, message, poll, wait, cancel, close |
| `prompt` | string | Only for `message` | Self-contained prompt with CONTEXT/TASK/CONSTRAINTS/OUTPUT FORMAT |
| `session_id` | string | For poll/wait/cancel/close | Returned by `open` |
| `timeout` | int | Optional | Wait timeout in seconds (default 120, max 300) |

**Actions:**

| Action | Description | Returns |
|---|---|---|
| `discover` | List all available agents | Agent list with capabilities |
| `open` | Create ACP session on a Daimon | `{ status: "open", session_id: "..." }` |
| `message` | Send prompt (async, returns immediately) | Confirmation |
| `poll` | Check session progress (thoughts, messages, tool_calls) | Current state + last activity |
| `wait` | Block until session completes or timeout | Final response + stop_reason |
| `cancel` | Abort a running session | Cancellation confirmation |
| `close` | Close session (agent stays alive for keep-alive) | Close confirmation |

**Session lifecycle:**
```
discover → open → message → poll (optional) → wait (or cancel) → close
```

**Key behaviors:**
- Daimons are **keep-alive** — spawned on first `open`, stay alive between sessions
- `message` is **async** — returns immediately. Use `poll` to check progress or `wait` to block
- Self-talk prevention: sending to "hermes" or "olympus" returns an error
- Unknown agents trigger automatic discovery before returning an error

### `mcp_olympus_run_workflow`

Execute a multi-agent LangGraph workflow with Human-in-the-Loop support.

**Parameters:**

| Parameter | Type | Required | Description |
|---|---|---|---|
| `workflow` | string | Yes | One of: project-init, feature, bug-fix, security-review, research, refactor |
| `prompt` | string | For new workflows | Task description. Not needed for resume. |
| `max_review_cycles` | int | Optional | Max Hefesto↔Athena audit cycles (default: 3 for feature, 2 for others) |
| `params` | object | Optional | Workflow-specific: `needs_research` (bool), `has_ui` (bool) |
| `thread_id` | string | For resume | Thread ID from a previous interrupt. Required with `resume`. |
| `resume` | string | For resume | User decision: approve, reject, confirm, modify, accept_risk |

**Return values:**

| Status | Meaning | Hermes action |
|---|---|---|
| `success` | Workflow completed | Present final result to user |
| `interrupted` | HITL checkpoint reached | Present question + context conversationally, ask user, resume |
| `error` | Workflow failed | Inform user, suggest next step |

---

## Human-in-the-Loop (HITL) Decision Guide

When a workflow interrupts, the orchestrator receives a conversational message with the checkpoint context, question, and options.

| Checkpoint | Workflow | Question | Options | Resume with |
|---|---|---|---|---|
| `research_review` | feature | ¿Research suficiente para proceder? | approve / reject | `approve`, `reject` |
| `design_review` | feature | ¿Apruebas este diseño? | approve / reject / modify | `approve`, `reject`, `modify` |
| `audit_review` | feature | ¿Aplicar fixes de seguridad? | approve / accept_risk / reject | `approve`, `accept_risk`, `reject` |
| `diagnosis_review` | bug-fix | ¿Confirmas este diagnóstico? | confirm / reject | `confirm`, `reject` |
| `findings_review` | security-review | ¿Proceder con fixes de seguridad? | approve / accept_risk / reject | `approve`, `accept_risk`, `reject` |
| `scope_review` | refactor | ¿Apruebas el alcance del refactor? | approve / reject | `approve`, `reject` |

**What happens on each decision:**

| Decision | Effect |
|---|---|
| `approve` | Continue to next node |
| `reject` | Terminate workflow immediately (goto finalize) |
| `modify` | Return to design node for revisions (design_review only) |
| `accept_risk` | Skip fixes, proceed to finalize (audit_review, findings_review only) |
| `confirm` | Confirm diagnosis, proceed to fix (diagnosis_review only) |

---

## Daimon-to-Node Mapping

Which Daimon executes each node in each workflow:

| Node | Daimon | Workflows | What it does |
|---|---|---|---|
| `research` | **Etalides** | feature, bug-fix, security-review, research, refactor | Web research, CVE lookup, diagnosis, impact mapping |
| `design` | **Daedalus** | feature | UX/UI flows (has_ui=true) or API/data flows (has_ui=false) |
| `implement` | **Hefesto** | feature, bug-fix, refactor | Implements code from design spec or diagnosis |
| `implement_fix` | **Hefesto** | feature, security-review | Fixes code based on audit findings |
| `audit` | **Athena** | feature, bug-fix, refactor | Security review, bug fix verification, refactor safety check |
| `re_audit` | **Athena** | feature, security-review | Re-verification after fixes applied |
| `onboard` | **Ariadna** | project-init | Creates .eter/ directory structure |
| `finalize` | — (system) | All | Consolidates final output from all nodes |

---

## Progress Watchdog

The workflow engine monitors Daimon activity to detect stalls without cutting off legitimate long-running work.

| Parameter | Value | Description |
|---|---|---|
| `POLL_INTERVAL` | 10s | Check for activity every 10 seconds |
| `STALL_TIMEOUT` | 120s | If no activity for 2 minutes → STALLED |
| Safety timeout | 1800s (30 min) | Emergency ceiling in runner.py |

**Design principle:** Hard timeouts are wrong for agent workflows. An agent actively producing thoughts, messages, or tool calls gets unlimited time. Only agents emitting ZERO activity for 120 seconds are considered stalled.

Activity is measured by:
- New `thoughts` in session state
- New `messages` in session state
- New `tool_calls` in session state

---

## How to Add a New Workflow

1. **Define the workflow graph** in `workflows/definitions.py`:
   - Add to `VALID_WORKFLOWS` list
   - Create a new `elif name == "your-workflow":` block in `get_workflow()`
   - Register nodes with `workflow.add_node()`
   - Connect edges with `workflow.add_edge()` and `workflow.add_conditional_edges()`

2. **Create HITL nodes** (if needed) using `make_node_hitl()`:
   ```python
   my_review = make_node_hitl(
       "my_review",
       "Question for the user?",
       ["approve", "reject"],
       {"approve": "next_node", "reject": "finalize"},
       include_context_key="research",
   )
   workflow.add_node("my_review", my_review)
   ```

3. **Add workflow_type handling** in `nodes.py` if your workflow needs custom prompts.

4. **Register the workflow** in `server.py`'s `run_workflow` tool schema (add to the `enum` in inputSchema).

5. **Compile with checkpointer**: `workflow.compile(checkpointer=checkpointer)` — already handled by `get_workflow()`.

---

## Known Pitfalls

| # | Pitfall | Symptom | Fix |
|---|---------|---------|-----|
| 1 | **add_messages on string lists** | `TypeError: expected str, HumanMessage found` in finalize | Use `operator.add` for `errors` and `hitl_decisions` accumulators |
| 2 | **Redundant START edges** | Conditional routing overridden, confusing code | Don't add `add_edge(START, ...)` when `add_conditional_edges(START, ...)` exists |
| 3 | **InMemorySaver data loss** | HITL resume fails after server restart | Use `AsyncSqliteSaver` with persistent `.db` file |
| 4 | **Sync SqliteSaver with async** | `"does not support async methods"` | Use `AsyncSqliteSaver` from `langgraph.checkpoint.sqlite.aio` |
| 5 | **AsyncSqliteSaver CM** | `AttributeError: 'object has no attribute setup'` | `from_conn_string()` returns a CM — use `await cm.__aenter__()` |
| 6 | **except RuntimeError** | ValueError, connection errors crash ainvoke() | Use `except Exception` in node factories |
| 7 | **time.monotonic() across restarts** | Garbage timestamps after restart | Use `time.time()` (wall clock) for `started_at` |
| 8 | **Personality overlay** | Daimons speak kawaii instead of their identity | Set `display.personality: none` in every profile config.yaml |
| 9 | **MCP timeout on long workflows** | Workflow times out before first HITL | Increase MCP timeout to 600s in config, or use delegate_task fallback |
| 10 | **Interrupt object serialization** | `"Object of type Interrupt is not JSON serializable"` | Extract `.value` attribute from Interrupt objects before JSON dump |
| 11 | **langgraph-checkpoint-sqlite not installed** | `ModuleNotFoundError` at runtime | Install in hermes-agent venv, not just project venv |
| 12 | **HITL nodes missing goto targets** | Workflow crashes after user decision | Register all possible goto target nodes in the graph |