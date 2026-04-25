# Changelog

All notable changes to Aether Agents will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [2.0.0] — 2025-04-24

### Olympus Workflow Engine v2 — Complete Rewrite

The Olympus MCP server was rebuilt from scratch to support structured multi-step workflows with Human-in-the-Loop (HITL) using LangGraph. This replaces the previous ad-hoc Daimon communication with 6 pre-defined workflows, persistent checkpointing, and conversational HITL.

#### Added

- **6 workflow definitions** (`workflows/definitions.py`):
  - `project-init` (3 nodes, no HITL) — Quick project bootstrap
  - `feature` (11 nodes, 3 HITL) — Full feature lifecycle: research → design → implement → audit with review checkpoints
  - `bug-fix` (6 nodes, 1 HITL) — Research → diagnose → confirm → fix → audit loop
  - `security-review` (7 nodes, 1 HITL) — Security audit with fix loop
  - `research` (3 nodes, no HITL) — Simple research pipeline
  - `refactor` (6 nodes, 1 HITL) — Scope approval → implement → audit loop

- **Human-in-the-Loop (HITL) system** (`workflows/nodes.py`, `server.py`):
  - Conversational format — agent presents context naturally, user decides
  - LangGraph `interrupt()` with `Command(goto=...)` for resuming workflow after user decision
  - 5 HITL nodes: `research_review`, `design_review`, `audit_review`, `diagnosis_review`, `findings_review`, `scope_review`
  - `make_node_hitl()` factory for creating HITL nodes with custom questions and routing

- **Persistent checkpointing** with `AsyncSqliteSaver`:
  - Workflows survive server restarts
  - Database stored at `{AETHER_HOME}/.olympus_checkpoints.db`
  - Lazy initialization with async context manager lifecycle
  - Proper shutdown via `_shutdown_checkpointer()`

- **WorkflowRunner** (`workflows/runner.py`):
  - `run()` executes workflows with timeout and stall detection (120s stall, 30min hard limit)
  - `resume()` restarts interrupted HITL workflows using `ainvoke()` (async, required by AsyncSqliteSaver)
  - Serializes LangGraph `Interrupt` objects to JSON for MCP transport
  - `time.time()` wall-clock timestamps (not `time.monotonic()` which is meaningless across restarts)

- **WorkflowState** (`workflows/state.py`):
  - Shared TypedDict across all workflows
  - `errors` and `hitl_decisions` use `operator.add` (not `add_messages` — which coerces strings to `HumanMessage`)
  - Workflow routing fields: `needs_research`, `has_ui`, `workflow_type`
  - Lifecycle fields: `status`, `started_at`, `node_name`

- **Node factories** (`workflows/nodes.py`):
  - `make_node_design()`, `make_node_implement()`, `make_node_audit()`, `make_node_research()`, `make_node_onboard()`
  - `make_node_hitl()` — HITL node factory with interrupt + Command routing
  - `node_finalize()` — Terminal node that formats results
  - `should_terminate_on_error()` — Error check conditional edge

- **`run_workflow` MCP tool** (`server.py`):
  - Accepts `workflow`, `prompt`, `params`, `max_review_cycles`, `thread_id`, `resume`
  - Returns conversational HITL instructions on interrupt (question, context, options, thread_id)
  - Returns final result on completion

- **Olympus README** (`src/olympus/README.md`) — Complete documentation of architecture, workflows, HITL, and configuration

#### Changed

- **Project structure** — `src/olympus/` now contains `workflows/` subdirectory with state, nodes, definitions, and runner
- **Provider-agnostic design** — All fixes work across all LLM providers, not just specific ones

#### Removed

- **Dead code cleanup** (-299 lines, 12.1% reduction):
  - `prompts.py` — All prompts are now inline in `nodes.py` via `get_prompt()` calls
  - `log.py` — Placeholder module never imported
  - `should_audit_pass_feature()` — Never called (feature workflow uses should_reaudit_pass)
  - `should_retry_implementation()` — Never called
  - Unused imports: `OlympusConfig`, `AgentStatus`, `aiosqlite`, `Literal`
  - Dead exports from `__init__.py`: `should_retry_implementation`, `get_prompt`
  - Config fields: `log_file`, `session_timeout`, `shutdown_timeout`
  - Registry fields: `_discovered_profiles`, `acp_process`

#### Fixed

- **Critical:** `add_messages` reducer on `errors` and `hitl_decisions` → `operator.add` — LangGraph was converting strings to `HumanMessage`, crashing on `'; '.join()`
- **Critical:** `app.invoke()` → `app.ainvoke()` for resume — InMemorySaver and AsyncSqliteSaver both require async invocation
- **Critical:** InMemorySaver loses checkpoints on restart → AsyncSqliteSaver with persistent SQLite database
- **Redundant edge** in feature workflow — removed `add_edge(START, "research")` that conflicted with `add_conditional_edges`
- **Narrow exception catching** — `RuntimeError` → `Exception` in all 5 node factories
- **Meaningless timestamps** — `time.monotonic()` → `time.time()` for cross-restart wall-clock times

---

## [1.0.0] — 2025-03-xx

### Initial Release

- Olympus MCP server with `talk_to` and `discover` tools
- 5 Daimon profiles (Hefesto, Ariadna, Etalides, Daedalus, Athena)
- ACP protocol client for Daimon communication
- Session lifecycle management (open, message, poll, wait, cancel, close)
- Basic orchestration via Hermes agent

[2.0.0]: https://github.com/DarkArty07/Aether-Agents/compare/v1.0.0...v2.0.0
[1.0.0]: https://github.com/DarkArty07/Aether-Agents/releases/tag/v1.0.0