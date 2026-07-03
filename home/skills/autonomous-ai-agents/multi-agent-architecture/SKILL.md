---
name: multi-agent-architecture
description: Design multi-agent systems from scratch — role separation, agent profile design, cost-alignment, orchestration patterns, peer-auditor patterns, escalation protocols, and thematic naming. Also covers operational best practices for running multi-agent fleets.
version: 1.3.0
category: autonomous-ai-agents
triggers:
  - when designing a new multi-agent system or framework
  - when re-architecting an existing multi-agent system
  - when deciding model-to-role assignments based on cost
  - when designing agent profiles (SOUL.md), toolsets, and role taxonomy
  - when designing quality assurance / validation patterns for agent systems
  - when choosing naming conventions and thematic identity for an agent team
  - when debugging or testing a custom multi-agent system with text-based tool calling
  - when operating agents day-to-day (delegation, monitoring, polling discipline)
  - when deciding between subprocess-based vs in-process delegation
  - when evaluating whether to use hermes-agent's native delegate_task vs a custom orchestration layer
---

# Multi-Agent Architecture Design

Patterns and principles for designing multi-agent systems. distilled from three iterations: Aether Agents (greek mythology, single-orchestrator + 6 Daimon subprocesses via ACP), Requiem (gothic horror, 3-level hierarchy: Raven→Necromancer→Shades), and Balam-Agent (Maya jaguar, flat delegation via native delegate_task). Includes comparative analysis of OpenCode, hermes-agent delegate_task internals, and Eigent/CAMEL.

> **See `references/in-process-delegation-analysis.md`** for the full three-way comparison of OpenCode's `task` tool, hermes-agent's `delegate_task` (2801 lines), and Eigent's `DepthLimitedAgentToolkit` — including source code findings, overhead taxonomy, and architectural convergence patterns.ator) and Requiem Agents (gothic horror, separated roles with peer-auditor).

## When to Use

- Designing a new multi-agent system from scratch
- Re-architecting an existing system to solve cost or quality problems
- Deciding how many roles/layers an agent system needs
- Designing validation and quality gates between agents
- Debugging or testing a custom multi-agent system that uses text-based tool calling (see `references/text-based-tool-calling-pitfalls.md` for 16 critical pitfalls + structured debugging methodology)

## In-Process Delegation vs Subprocess Orchestration

**Critical lesson from 3 iterations (Aether→Requiem→Balam):** The #1 performance killer in multi-agent systems is not the LLM — it's the orchestration overhead between agents.

Three independently developed systems (OpenCode, hermes-agent `delegate_task`, Eigent/CAMEL) all converged on: **1 agent + flat subagents, same process, depth=1, fresh context, restricted toolsets.**

**Subprocess overhead (Aether/Requiem approach):** 3-8s startup per agent, ACP pipes, PID files, SQLite WAL, context transfer between levels.
**In-process overhead (delegate_task approach):** ~0ms (Python object), direct function calls, shared process state, no transfer.

hermes-agent's `delegate_task` (2801 lines) already provides everything needed: AIAgent in ThreadPoolExecutor, fresh context, depth limiting, per-subagent model override, batch parallel, auto-approve. **Use it instead of building custom orchestration.**

**Key config pattern:**
```yaml
model:
  default: expensive-reasoning-model  # orchestrator reasons
delegation:
  provider: cheap-provider
  model: fast-cheap-model  # subagents execute
  max_spawn_depth: 2
  subagent_auto_approve: true
```

> **See `references/in-process-delegation-analysis.md`** for the full three-way source code comparison, overhead taxonomy, and Balam-Agent reference implementation.

---

## Core Principles

### 1. Cost-Alignment — match model cost to task value

The most expensive model should do the most valuable work (understanding the user). The cheapest model should do the most mechanical work (executing tasks). Reading code is NOT high-value work — it's mechanical — so it should NOT use the expensive model.

```
WRONG (Aether Agents):  Hermes (DeepSeek V4 Pro $$$) reads code → 80% of cost is input tokens
RIGHT (Requiem Agents):  Raven (V4 Pro $$$) only reasons → Necromancer (GLM-5 $$) reads code
```

Rule: if a task is "read X and summarize," it doesn't need the expensive model. If a task is "understand what the user actually means when they say something vague," it does.

**Inverted pyramid — when the orchestrator outvalues the assistant:** The principle above says "most expensive model = most valuable work." But "most valuable" is not always "understanding the user." Formalizing user intent ("create a Stack class with tests") is cognitively cheaper than decomposing it into subtasks, routing to the right agent, and coordinating retries. When the assistant only formalizes and narrates (Raven) while the orchestrator does the heavy decomposition and routing (Necromancer), the orchestrator warrants the MORE expensive model:

```
Requiem Agents v2 (inverted):
  Raven (GLM-5.2 $$)       — formalizes intent, narrates progress (less cognitive load)
  Necromancer (V4 Pro $$$) — decomposes, reads code, routes, coordinates (most cognitive load)
  Revenant (GLM-5.2 $$)   — audits
  Shades (V4 Flash ¢)     — execute
```

Match model cost to COGNITIVE LOAD of the task, not hierarchy position. The assistant sits at the top of the hierarchy but may do the least cognitively demanding work — formalizing what the user said is not the same as figuring out how to build it.

### 2. Role Separation — one agent, one job

Each agent has exactly ONE primary responsibility. Mixing roles creates bloated SOULs, confused identity, and single points of failure.

| Anti-pattern | Problem | Fix |
|--------------|---------|-----|
| One agent does everything | 30K-token SOUL, SPOF, expensive | Split into focused roles |
| Auditor is subordinate of executor | Can be ignored, no real veto | Make auditor a peer |
| User-facing agent also reads code | Burns expensive tokens on mechanical work | Separate assistant from orchestrator |

### 3. Peer-Auditor — checks and balances

The quality-validation agent must be a PEER of the execution agent, not a subordinate. This means:

- The auditor can VETO outputs — the executor cannot override
- The auditor cannot be ignored — escalation is the only bypass
- Both report to the same authority (the assistant/user layer)

This is the single most important architectural decision. Subordinate auditors are theater; peer auditors are real.

**Implementation detail — artifact metadata passing:** For a peer auditor to work, it must receive the worker's actual outputs (file paths, artifacts), not just the worker's summary. The orchestrator must collect tool-call arguments from the worker's agentic loop and append them to the output. See `references/custom-agent-implementation-patterns.md` → "Artifact Metadata Passing" sub-pattern for code examples.

### 4. Escalation Protocol — bounded disagreement

When executor and auditor disagree, there must be a deterministic escalation path:

```
Attempt 1: Auditor rejects → Executor retries with feedback
Attempt 2: Auditor rejects → Executor retries with expanded context
Attempt 3: Auditor rejects → Escalate to assistant with full dossier
```

The assistant (or user) breaks the tie in one decision. This prevents infinite loops and bounds the cost of disagreement.

**Executor-of-last-resort:** In practice, when workers fail repeatedly (API errors, malformed output), the assistant doesn't just arbitrate — it becomes the executor. During 2-hour testing of Requiem Agents, the ORM task escalated after 3 Shade failures (API errors + JSON malformation). Raven received the escalation, read the partial work, fixed the code directly, and ran the tests itself. This is a desirable emergent behavior: the most capable model handles the hardest cases, and the system degrades gracefully rather than failing outright.

### 5. Memory Separation — each role remembers what it needs

| Role | Memory scope |
|------|-------------|
| Assistant | User preferences, communication style, conversation history |
| Orchestrator | Codebase structure, delegation patterns, agent capabilities |
| Auditor | Past failures, edge cases, rejection criteria |
| Agents | Domain-specific knowledge, skills |

Mixing these into one memory store creates noise and bloats context for every agent.

## Role Taxonomy

The minimum viable multi-agent architecture has four roles:

| Role | Function | Model tier | User-facing? |
|------|----------|-----------|-------------|
| **Assistant** | Interpret user, formalize ideas, deliver results | Expensive ($$$) | Yes |
| **Orchestrator** | Read code, decompose tasks, delegate | Medium ($$) | No |
| **Auditor** | Validate outputs, challenge orchestrator | Medium ($$) | No |
| **Agents** | Execute atomic tasks | Cheap (¢) | No |

### Why four and not three

A three-role system (assistant + orchestrator + agents) has no independent quality gate. The orchestrator self-validates, which is theater. The auditor role is what makes the system trustworthy.

### Why four and not five

Five+ roles add handoff latency and context fragmentation without proportional value. Four roles cover: understand (assistant), plan (orchestrator), validate (auditor), execute (agents). More roles = more coordination overhead.

### 6. Telemetry-First — no blind operation

Every agent call must be logged: tokens consumed, duration, cost, result (pass/fail), retries, escalations. This is non-negotiable. Without telemetry you cannot answer "is this architecture actually cheaper?" or "which Shade is burning tokens?".

```
SQLite schema (agent_calls table):
  timestamp | session_id | agent_name | action | task_id
  input_tokens | output_tokens | cost_usd | duration_seconds | result | metadata
```

Build the telemetry layer BEFORE the first real task, not after. Retrofitting telemetry means you lose the first N sessions of data — and those are often the ones where bugs surface.

The telemetry layer includes a dashboard: FastAPI backend reading the shared SQLite, React frontend polling every 5s, themed CSS matching the project identity. See `references/dashboard-and-testing-patterns.md` for concrete implementation (endpoint inventory, component structure, CSS theme variables, Vite proxy config).

### 8. Hierarchy Depth — flat beats nested for most tasks

The number of delegation levels directly multiplies LLM calls. A 3-level hierarchy (assistant→orchestrator→worker) makes 3 LLM calls per task; a 2-level (primary→subagent) makes 1. For tasks under ~500 lines of code, the overhead of intermediate levels exceeds the value of specialization.

**Reference implementation — OpenCode (source code analysis):** OpenCode uses a flat 1-level delegation model. A single `task` tool spawns a subagent that CANNOT delegate further (task permission is denied in subagent sessions, enforced structurally in `subagent-permissions.ts`). Subagents specialize by PERMISSIONS (read-only `explore`, full-power `general`), not by separate SOULs. Each subagent starts with fresh context (no transfer overhead), returns its last text message (no structured protocol), and uses the same model as the parent by default. Context management is automatic: truncate at 2000 lines/50KB, prune old tool outputs at 40K tokens, compact via LLM summary when context overflows. See `references/opencode-subagent-architecture.md` for full source code analysis.

**When nested hierarchy IS justified:** Tasks large enough that a single context window would overflow (>100K tokens of tool output), tasks with 5+ independent parallel workstreams, or tasks requiring a peer auditor with veto power. For everything else, flat delegation with a fast-path classifier is more efficient.

### 9. Framework Boundary — hybrid systems

Not every agent needs the same framework. A common pattern: the user-facing assistant uses a full agent framework (hermes-agent, etc.) for vibecoding, memory, and tool use — while the orchestrator, auditor, and workers are custom Python making raw API calls.

```
Assistant (framework) ──MCP──► Orchestrator (custom Python)
                                    ├──► Auditor (custom, same process)
                                    └──► Workers (custom, async LLM calls)
```

MCP is the natural bridge: the framework agent calls MCP tools exposed by a thin server, which invokes the custom orchestrator. The custom agents never know about the framework — they just call the LLM API directly with their soul file as system prompt.

Advantages:
- Sub-agents have zero framework dependency — no pip install, no version lock-in
- The expensive framework license/footprint is paid only once (for the assistant)
- Custom agents can use different API formats, retry logic, or inference backends without touching the framework
- The MCP server is the only coupling point — swap the assistant framework without rewriting sub-agents

## Architectural Classification — Formal Names

When documenting or discussing a multi-agent system design, use the formal names:

| Pattern | What it means | Requiem example |
|---------|--------------|-----------------|
| **Hierarchical Multi-Agent Orchestration** | Tree of N levels, not flat — each level delegates downward | Raven → Necromancer → Shades (3 levels) |
| **Orchestrator-Worker Pattern** | A "manager" agent decomposes work and routes to specialized workers; it never executes itself | Necromancer decomposes → routes to Shades |
| **Cost-Tiered Model Assignment** (Pirámide de Costos) | Expensive model where cognitive load is highest; cheap model for mechanical work | Raven $$$ reasons, Shades ¢ execute |
| **Peer-Auditor with Veto (Checks-and-Balances)** | Quality-validation agent is a PEER, not subordinate — can veto, only escalation overrides | Revenant audits Shade output, Necromancer cannot override |
| **Nested Agent Orchestration (Subagent Delegation)** | Each agent spawns subagents with isolated context, tools, and model | Raven delegates to Necromancer, Necromancer delegates to Shades |

These names are useful when writing DESIGN.md, communicating with stakeholders, or searching for academic/industry references on the pattern.

## Layered Communication

```
USER ⇄ Assistant    (bidirectional, vibecoding)
         ↓ ideas formalizadas
Orchestrator ⇄ Auditor    (bidirectional, peer dialogue)
         ↓ delegated tasks
Agents    (one-way from orchestrator, results return)
```

Key rules:
- Agents never talk to the user
- The auditor never delegates to agents directly
- The assistant never reads code or debugs
- The orchestrator never talks to the user

## Formal Architectural Classification

When discussing a multi-agent system with stakeholders, searching for literature, or comparing with other systems, use the accepted industry/academic vocabulary. A hierarchical system like Requiem or Aether Agents maps to:

| Term | Meaning | Maps to |
|------|---------|---------|
| **Hierarchical Multi-Agent Orchestration** | Tree-structured delegation across N levels, not flat | Raven → Necromancer → Shades (3 levels) |
| **Orchestrator-Worker Pattern** | A "manager" agent receives work, decomposes, distributes to specialized workers | Necromancer + Shades |
| **Cost-Tiered Model Assignment** | Expensive model where cognitive load is high, cheap model for mechanical work | Raven ($$$) → Shades (¢) |
| **Peer-Auditor (Checks-and-Balances)** | Quality gate agent is a peer, not subordinate; has real veto power | Revenant vs Necromancer |
| **Nested Agent Orchestration (Subagent Delegation)** | Each agent spawns specialized subagents with isolated context, tools, model | Raven → Necromancer → Shades |

The governing principle: the expensive model reasons (understands the human), the cheap models execute (understand the code). The separation between "understanding the human" and "understanding the code" is the core innovation.

## Thematic Naming

Give the agent team a cohesive thematic identity. This isn't cosmetic — it aids memory, communication, and system cohesion.

| System | Theme | Roles |
|--------|-------|-------|
| Aether Agents | Greek mythology | Hermes, Hefesto, Etalides, Athena, Daedalus, Ariadna, Ictinus |
| Requiem Agents | Gothic horror | Raven (messenger), Necromancer (commands shades), Revenant (returns to judge), Shade of X (executors) |
| Balam-Agent | Maya culture | Balam (jaguar, super agent), Explorer (read-only), Builder (full access) |

Naming patterns:
- The theme should map to FUNCTION, not just aesthetics (Raven = messenger of Poe, Necromancer = commands the dead/shades)
- Agent names should be self-explanatory within the theme
- "Shade of X" pattern allows infinite extensibility while maintaining cohesion

## Common Pitfalls

- **Expensive model reads code:** The #1 cost problem. If your assistant/orchestrator is using a $$ model to read_file and search_files, you're burning money. Move code-reading to a cheaper model.
- **Auditor without veto:** An auditor whose recommendations can be ignored is not an auditor — it's a suggestion box. Give it real power or don't have one.
- **Bloated SOUL per agent:** If one agent's SOUL exceeds ~150 lines, it's doing too many things. Split the role.
- **No escalation bound:** Without a "3 strikes → escalate" rule, auditor-executor disagreements loop forever, burning tokens.
- **User-facing agent with technical tools:** If the assistant has terminal, file, and code tools, it WILL use them — and you're back to the expensive-model-reads-code problem. Give the assistant ONLY delegation, memory, and communication tools. **Concrete example:** Balam-Agent's `references/balam-delegator-only-pattern.md` shows the exact config.yaml `disabled_toolsets` block + SOUL.md structure for a delegator-only agent. Key: `disabled_toolsets` under `agent:` removes tools structurally for ALL interfaces, not just messaging platforms — superior to prompt-based restrictions.
- **Context fragmentation without .aether:** Each handoff loses context. A continuity system (like .aether/CONTEXT.md) is essential — each agent receives curated context at session start, not raw history.
- **MCP server can't find its own module:** When using `-m module_name` in config.yaml, Python resolves the module BEFORE the server script runs. `sys.path.insert` in the server can't fix this. Either name the directory with underscores, create a symlink, or set `PYTHONPATH` in the config.yaml `env:` section. See `references/custom-agent-implementation-patterns.md` — "Directory name vs Python import name" pitfall.
- **Text-based tool calling needs `json.loads(strict=False)`:** Custom agents using a text-based JSON tool-calling protocol will fail silently if the JSON parser uses `strict=True` (the default). Models emit JSON with literal newlines inside string values (e.g., file content in a `write_file` call). `strict=True` rejects these. Always use `json.loads(json_str, strict=False)` when parsing model-generated JSON. See `references/custom-agent-implementation-patterns.md` Pattern 5.
- **Testing multi-agent systems by structured test plans:** Do NOT propose a phased test plan (smoke test, integration, end-to-end). Instead, simulate being a real user: start the assistant in tmux, give it real tasks, monitor the SQLite telemetry DB for progress, fix bugs as they surface, and iterate for the allotted time. The system is meant for vibecoding — test it by vibecoding. See `references/dashboard-and-testing-patterns.md` — "Vibecoding Test Approach".
- **json.loads(strict=False) for model JSON:** Models output JSON with literal newlines inside string values (especially in write_file content). Default `strict=True` rejects these. ALWAYS use `json.loads(str, strict=False)` when parsing model-generated JSON. This is the #1 reason tool calls fail to parse — the JSON looks correct but json.loads silently rejects it. See `references/text-based-tool-calling-pitfalls.md`.
- **Infinite loop in custom JSON parsers:** When brace-counting to find JSON blocks in model output, unbalanced braces cause `search_start` to never advance. ALWAYS ensure the search position advances on every iteration, even when parsing fails. See `references/text-based-tool-calling-pitfalls.md` — Pitfall 3.
- **Context explosion in agentic loops:** Tool results appended to messages grow unboundedly over iterations. Truncate results to ~2000 chars and add a total token budget check (e.g., stop at 50K input tokens). See `references/text-based-tool-calling-pitfalls.md` — Pitfall 4.
- **Auditor approves empty output:** If the task says "create" and no files exist, auto-fail without calling the model. This saves tokens and prevents false passes. See `references/text-based-tool-calling-pitfalls.md` — Pitfall 5.
- **Model outputs incomplete JSON (truncated braces):** Flash models sometimes truncate output before closing all JSON braces. A `write_file` call with long content ends with `"}}` instead of `"}}}`. Fix: when braces are unbalanced, count the deficit and append missing `}` characters before parsing. See `references/text-based-tool-calling-pitfalls.md` — Pitfall 7.
- **Model uses \' in JSON strings:** `\'` is NOT valid JSON (only `\"`, `\\`, etc. are defined). `json.loads()` rejects it even with `strict=False`. Fix: `json_str.replace("\\'", "'")` before parsing. See `references/text-based-tool-calling-pitfalls.md` — Pitfall 8.
- **Research agent loops forever:** Read-only agents (research shades) have no natural "done" signal — they keep reading indefinitely. Fix: inject a "wrap up and write summary" message at a midpoint iteration (e.g., iteration 10 of 15). See `references/text-based-tool-calling-pitfalls.md` — Pitfall 9.
- **Path extraction matches directories:** `os.path.exists()` returns True for directories. Use `os.path.isfile()` when extracting file paths from agent output, or the auditor will try to read directories as files. See `references/text-based-tool-calling-pitfalls.md` — Pitfall 10.
- **Dashboard frontend running without backend:** Vite serves the frontend but proxies `/api/*` to a FastAPI backend. If the backend isn't running, the user sees "Connection error: HTTP 500". Start BOTH processes. Backend deps (fastapi, uvicorn) are separate from the agent venv — install with `--break-system-packages` on PEP 668 Python. See `references/dashboard-and-testing-patterns.md` — Common Pitfalls.
- **System prompt dominance suppresses non-dominant tools:** An executor agent's system prompt creates a behavioral gravity well. If the prompt says "ALWAYS write files," the model (especially flash/cheap models) will try `write_file` even when the task requires `terminal` commands. The agent won't use tools that exist but are de-emphasized by the prompt. Connected failures: the auditor can't verify command output (only files), and there's no role for "execute and report" tasks. Fix: either soften the prompt with conditional language, add an auditor path for command output, or create a dedicated executor role whose identity matches the task type. See `references/text-based-tool-calling-pitfalls.md` — Pitfall 13.
- **Auditor auto-fail must be execution-task-aware:** The auto-fail pre-check (no files + creation keywords = fail) incorrectly fires for execution tasks that legitimately produce no files. Fix: check for terminal output in the Shade's response, exempt execution tasks, and require all four conditions (creation + not execution + no files + no terminal output) for auto-fail. See `references/text-based-tool-calling-pitfalls.md` — Pitfall 14.
- **Auditor must judge execution quality, not test results:** When auditing an execution task (run commands, report results), the auditor LLM sees test failures in the output and fails the audit — but the Shade's job was to RUN and REPORT, not make tests pass. Fix: add execution-task auditing rules to the auditor's soul (PASS if command was run and output is faithfully reported, DO NOT fail because tests have failures). See `references/text-based-tool-calling-pitfalls.md` — Pitfall 15.
- **New agent roles need explicit routing rules in orchestrator's soul:** Listing a new agent in the decomposition prompt's available agents is insufficient — the LLM defaults to the most familiar agent. Fix: add explicit routing rules to the orchestrator's SOUL (system prompt) specifying WHEN to use each agent, not just a list. See `references/text-based-tool-calling-pitfalls.md` — Pitfall 16.
- **Prompt-based routing is insufficient — add code-level override:** Even with explicit routing rules in the SOUL, the LLM still misroutes tasks (e.g., sends "run pytest" to Programming Shade instead of Execution Shade). Fix: implement a `_override_shade()` function in the orchestrator code that pattern-matches the subtask text and deterministically overrides the LLM's shade selection. Check execution keywords FIRST (pytest, run tests, execute), then creation (create, write, implement), then research (investigate, analyze). Only override when keywords from ONE category are present — mixed tasks keep the LLM's choice. See `references/text-based-tool-calling-pitfalls.md` — Pitfall 17.
- **Shade output doesn't include tool results — auditor can't verify execution:** The shade_output passed to the auditor is only the Shade's last assistant message, NOT the tool results from the agentic loop. When the Shade of Execution runs pytest, the "11 passed" output is in a tool result message, not in the final assistant message. Fix: in `run_shade()`, append terminal tool results to `final_content` for execution shades so the auditor can see the actual command output. See `references/text-based-tool-calling-pitfalls.md` — Pitfall 18.
- **Revenant false-negatives on execution tasks — add auto-pass:** The auditor LLM often returns FAIL for execution tasks even when tests pass, because it doesn't follow "DO NOT fail because tests pass" instructions. Fix: add an auto-pass pre-check in the audit function: if `shade_name == "execution"` AND output contains "passed" AND output does NOT contain "failed"/"traceback" (with exceptions for "0 failed", "0 errors", "no errors"), return PASS immediately without calling the LLM (0ms, 0 tokens). See `references/text-based-tool-calling-pitfalls.md` — Pitfall 19.

- **Plugin/tool migration silently bypasses orchestrator decomposition:** When migrating a multi-agent system from MCP server to native plugin (or any tool abstraction layer change), the orchestrator's decompose→shade→audit pipeline can be silently bypassed. In Requiem's case, the MCP server had granular tools that preserved the Necromancer's full pipeline. The native plugin replaced them with flat tools (investigate/execute/implement) that sent prompts directly to Shades WITHOUT decomposition, added LLM summarization (a cheap model compressing results before the expensive model saw them), and created blocking calls with no visibility. The migration looked like a simplification but destroyed the hierarchical architecture. **Prevention:** After ANY tool-layer migration, verify that the new tools still invoke the orchestrator's full pipeline (process_task with decompose→shade→audit), not just the Shade directly. Check: (1) does the handler call the orchestrator's decompose function? (2) does the auditor receive the raw Shade output? (3) is there any LLM summarization between the Shade and the assistant? See `references/requiem-plugin-reconstruction.md` for the full diagnostic and fix.
- **LLM summarization between worker and assistant destroys the architecture:** Adding an LLM summarization layer (e.g., a cheap model compressing Shade output before Raven sees it) defeats the purpose of having an expensive model at the top. The expensive model is there to reason about results — if results are pre-compressed by a cheaper model, the expensive model is reasoning about a lossy proxy. The assistant must see raw (or head+tail truncated) output. Disk-saving for audit is fine; context summarization for the assistant is not.
- **SOUL.md must not reference tools the agent doesn't have:** If the config disables `terminal` and `file` toolsets for an agent (correctly, to enforce delegation), the SOUL.md must NOT instruct the agent to use `read_file`, `search_files`, or `terminal`. The SOUL and the config must be aligned — a contradiction creates an agent that tries tools it doesn't have, gets errors, and degrades to verbose narration without action.
- **Plugin migration can silently bypass the orchestrator:** When migrating a multi-agent system from MCP server to native plugin (or vice versa), the new plugin tools may accidentally send prompts directly to workers (Shades) instead of routing through the orchestrator's decomposition phase. The MCP version had granular tools (decompose/execute/progress/result) that enforced the orchestrator flow; the plugin replacement collapsed them into direct-to-worker calls. Symptom: tasks that took 1 minute with MCP now take 5 minutes and produce worse results — the orchestrator never decomposes, workers receive raw prompts, and the auditor has nothing to validate against. Fix: every plugin tool MUST call the orchestrator's `process_task()` (or equivalent) internally. Never bypass the orchestrator's decomposition phase for any entry point. A single `delegate_to_orchestrator(prompt, project_root)` tool with a structured template is cleaner than multiple tools that each bypass decomposition.

- **LLM summarization of worker output blinds the expensive model:** A plugin layer that summarizes worker (Shade) results with a cheaper model before the expensive model (Raven) sees them defeats the architecture. The expensive model exists to reason about and present results — if it receives a compressed summary instead of real output, it cannot make quality decisions or present accurate results to the user. Fix: pass raw worker output to the expensive model. Use head+tail truncation (not LLM summarization) only if the output exceeds a generous threshold (50K+ chars). Never use a cheaper model to summarize results FOR the expensive model — that's backwards cost optimization.

- **SOUL.md must match enabled toolsets or the agent enters a contradiction loop:** If the SOUL.md tells an agent to "read code with read_file and search_files" but the config.yaml disables `file` and `terminal` toolsets, the agent tries to use tools it doesn't have, fails, and degrades. The SOUL is the behavioral specification; the config is the capability boundary. They MUST be aligned. When you disable a toolset for cost reasons (e.g., removing file tools from an expensive assistant to force delegation), update the SOUL to reflect what the agent CAN and CANNOT do. The SOUL should frame the restriction as identity ("You NEVER read code — that's the Shades' job"), not as a missing capability.

- **Custom LLM summarization of tool results is inferior to simple truncation:** Writing a custom `_summarize_tool_result()` function that uses heuristics (join first N lines, add metadata suffix) to compress tool outputs is fragile — it can produce summaries LONGER than the original for small files (observed in Requiem), loses information unpredictably, and requires maintenance. OpenCode's approach is simpler and more robust: (1) Truncate each tool output at 2000 lines / 50KB, save the full output to a file for later recovery; (2) Prune old tool outputs (mark as compacted) when total exceeds 40K tokens, protecting the last 2 turns; (3) When context overflows, use a dedicated compaction agent to LLM-summarize the conversation (not individual tool results). The compaction agent summarizes DIALOGUE, not raw tool output — a much better fit for LLM summarization. Rule: never use LLM or heuristic summarization on individual tool results. Truncate, save full, and let the compaction agent handle conversation-level summarization when needed. See `references/opencode-subagent-architecture.md` → "Context Management" section.

- **Knowledge-graph (graphify) as read-layer for cost-tiered assistants:** An expensive assistant model that cannot read files directly (file/terminal toolsets disabled for cost reasons) can still understand the codebase through a knowledge-graph MCP server (graphify). The assistant queries the graph (query_graph, get_neighbors, god_nodes, shortest_path) to learn structure, dependencies, and architecture BEFORE delegating to workers. This gives the expensive model code understanding WITHOUT burning tokens on raw file reads. The pattern: expensive model explores the graph (cheap, structured, token-efficient) → fills a structured delegation template with real data → delegates to the orchestrator with accurate context instead of guesses. The knowledge graph is generated via AST parsing (graphify update, no API cost) and served as a standalone MCP server. Each project has its own graph and MCP server instance.

- **Structured delegation template for assistant→orchestrator handoff:** When an assistant delegates to an orchestrator, a structured prompt template produces dramatically better decomposition than a free-form description. Template: `OBJETIVO: [what to achieve, technical specifics]`, `CONTEXTO: [stack, structure, conventions, relevant files from graphify exploration]`, `RESTRICCIONES: [scope limits, what NOT to touch]`, `CRITERIOS DE ACEPTACION: [how to verify completion — the auditor uses this]`. The acceptance criteria section is critical: it gives the peer-auditor (Revenant) concrete test conditions to validate against, turning vague "looks good" audits into pass/fail decisions. The template should be embedded in the tool schema description AND taught in the assistant's SOUL.md as mandatory.

- **Single MCP tool that runs a full multi-agent pipeline blocks the calling agent:** When one MCP tool call (e.g., `activate_necromancer`) triggers the entire pipeline (decompose → shade → audit → retry loop), the calling agent (assistant) blocks for 2-10 minutes with zero user visibility. The user sees nothing during execution — breaking the vibecoding interaction loop. Fix: split the single blocking tool into 4 granular tools: (1) `decompose` — synchronous, returns the subtask plan; (2) `execute` — async, launches the pipeline in background, returns immediately; (3) `progress` — reads in-memory state, returns current subtask/phase/iteration/audit result; (4) `result` — returns final results if completed, or "still_running." The assistant polls `progress` every few seconds and narrates each phase to the user. See `references/mcp-visibility-pattern.md` for the full pattern.
- **Verifying MCP server refactors requires the project venv + mock pattern:** System Python lacks the `mcp` module, so import tests fail with `ModuleNotFoundError`. Use the project's venv (`raven/.venv/bin/python3`). Hermes blocks `python3 -c` (can write files), so pipe a heredoc: `cat << 'TESTEOF' | raven/.venv/bin/python3`. Mock the async background function (`srv.process_subtasks = mock_fn`) to test execute→progress→result flow without real LLM calls. See `references/mcp-verification-testing.md` for the full 9-step checklist.
- **print() to stdout corrupts MCP stdio protocol:** Custom agents using `print()` for debugging in an MCP server context silently break the protocol — MCP uses stdio as the transport, so any print output gets mixed with MCP messages. Fix: always use `print(..., file=sys.stderr, flush=True)` in MCP server code and any modules imported by it. stderr is not part of the MCP stdio channel.
- **ACP edit approval timeout blocks ALL Daimon file writes (CRITICAL, recurring across sessions):** When olympus_v3 spawns a Daimon via ACP, `new_session()` defaults to mode `"default"` → edit approval policy `"ask"`. This sends an interactive approval request for every `write_file`/`patch` call. Since olympus_v3 is headless (no interactive client like Zed to click "Allow"), the request times out (60s) and returns `"Edit approval denied by ACP client"`. This silently blocks ALL file modifications by ALL Daimons — Hefesto reports success but verifier says "NOT modified". Root cause is in `acp_adapter/edit_approval.py`: the `maybe_require_edit_approval()` function checks for an `EditApprovalRequester` bound via ContextVar. In headless ACP sessions spawned by olympus_v3, the requester exists but the `request_permission_fn()` callback has no client to answer it. **Fix:** After `new_session()` in `acp_manager.py` (line ~248), call `await agent.connection.set_session_mode("dont_ask", acp_session_id)`. This sets policy to `"session"` which auto-approves all edits except sensitive paths (.env, .ssh, .git). See `references/acp-edit-approval-headless-daimons.md` for the complete fix with 3 ACP modes explained.
- **Rate-limited tool design for behavioral alignment:** Instead of relying on SOUL.md prompts to limit an expensive agent's code reading ("don't read too many files"), enforce the limit IN THE TOOL. A `read_file_simple` tool with a per-turn counter (max 3 reads, then returns `"LIMIT_REACHED — delegate to orchestrator for extended research"`) structurally prevents the expensive model from reading the entire codebase while still allowing targeted verification. The counter resets each turn. This is superior to prompt-based limits because the LLM's tool-affordance bias overrides SOUL instructions — if `read_file` exists, the model WILL use it excessively. By making the tool itself enforce the limit, the model is forced to change strategy (delegate) rather than being told to. Generalizable pattern: any tool that risks expensive-model overuse should have a built-in rate limit, not just a prompt instruction.
- **Auditor must auto-fail code with syntax errors before LLM review:** A peer-auditor (Revenant) that only checks structural artifacts (files exist, has_terminal_output) will give PASS to code that doesn't compile. During testing, a Shade modified code to inherit from a non-existent class — the Revenant approved it because `has_files=True`. Fix: after compiling modified .py files (`python -m py_compile`), if ANY file has a syntax error, auto-fail immediately WITHOUT calling the LLM auditor. This saves tokens (no LLM call for obviously broken code) and prevents false passes. The compile check is already happening (the auditor reads files to verify content) — just add the auto-fail gate after compile_results are generated.
- **Orchestrator must always inject execution subtask when programming subtasks exist:** When the orchestrator decomposes a task into programming subtasks but no execution subtask, the code is never tested. The auditor can't catch runtime errors (like `NameError` from inheriting non-existent classes) because nobody ran the code. Fix: after parsing decomposed subtasks, if ANY subtask is `programming` and NO subtask is `execution`, automatically append an execution subtask: `"Run pytest in {project_root} to verify the code changes compile and tests pass."`. This is a code-level guarantee, not a prompt instruction — the orchestrator's decomposition LLM may forget to include testing.
- **MCP tool `required` array over-specification breaks per-action validation:** When an MCP tool has multiple actions (open, poll, close, delegate), the `required` array must ONLY include fields needed by ALL actions — typically just `["action"]`. Putting `daimon` or `prompt` in `required` (to force the framework to serialize them) breaks actions like `close`/`poll`/`cancel` that only need `session_id`. The framework rejects the call with `Input validation error: 'prompt' is a required property` before the handler runs. Fix: `required: ["action"]` only; validate per-action fields in the handler. See `references/mcp-visibility-pattern.md` — Issue 2.
- **Executor efficiency rules prevent iteration loops in flash models:** Without explicit efficiency rules in the executor's SOUL.md, cheap/flash models enter write→test→read→write cycles that burn 10+ iterations on simple tasks. The system prompt's "ALWAYS write files" instruction creates a behavioral gravity well (Pitfall 13) that makes the model keep writing and re-reading. Fix: add MANDATORY efficiency rules to the executor soul: WRITE ONCE (write then stop), NO RE-READS (never read_file a file you just wrote), NO SELF-TESTING (don't run tests — that's a separate executor role's job), MAX 5 ITERATIONS (for simple tasks), ONE WRITE PER FILE (max 2 writes: original + 1 fix). These rules are especially important for the programming shade when a separate execution shade handles testing.
- **Patch-generated f-strings with escape sequences break silently:** When patching Python code containing f-strings with `\n` in string content, the `\n` in the patch `new_string` gets interpreted as a literal newline, not an escape sequence — breaking the f-string with `SyntaxError: unterminated f-string literal`. This happened when patching the Revenant's auto-fail return statement. Fix: after ANY patch that modifies Python code containing f-strings with escape sequences, immediately run `python3 -m py_compile` to catch the breakage. Prefer string concatenation or triple-quoted f-strings in patch content to avoid the newline interpretation problem.
- **Olympus v3 zombie processes cause "Connection closed" after gateway restart:** When the gateway restarts, a new olympus_v3.server process spawns but the old one may not die — especially if the old process has active MCP connections. Two processes competing for the same MCP server name cause intermittent "Error spawning agent: Connection closed" failures. After applying the ACP edit approval fix (or any olympus_v3 code change), always: (1) `ps aux | grep olympus_v3.server | grep -v grep`, (2) kill ALL stale processes, (3) THEN restart the gateway. This is a recurring pattern across sessions.
- **Knowledge graph contamination by external code:** When using graphify (or any code knowledge graph) for a multi-agent system, the graph MUST exclude external/vendored directories. If `graphify-reference/` (a clone of graphify's own repo), skills directories from other projects, or dependency source code gets indexed, `god_nodes()` returns irrelevant abstractions (Honcho's `Session`, `Peer`, `Message` instead of Requiem's `process_task`, `audit`, `run_shade`). The assistant's explore-before-delegate feature breaks silently — `query_graph("necromancer")` returns nodes from unrelated projects. Fix: use `.graphifyignore` or `--exclude` flags to limit indexing to the project's own source. Verify by checking `god_nodes(top_n=10)` — if the results don't include your project's core functions, the graph is contaminated. See `references/requiem-audit-2026-06-24.md` — Finding A3.
- **Rate-limited tool counters must reset between turns:** A `read_file_simple` tool with a per-turn rate limit (max 3 reads) must reset its counter at the start of each conversation turn. If the counter persists across turns, the tool becomes permanently blocked after the first turn — the expensive model loses its read capability entirely. The counter is typically a dict keyed by `session_id`; it needs a reset mechanism (e.g., a `pre_llm_call` hook, or checking turn boundaries). This is a structural design flaw that defeats the purpose of the rate limiter — instead of limiting per-turn, it limits per-session. See `references/requiem-audit-2026-06-24.md` — Finding O1.
- **Dead code from MCP-to-plugin migration creates divergent execution paths:** After migrating a multi-agent system from MCP to native plugin, the old MCP entry points (`process_investigate`, `process_execute`, `process_implement`) remain in the orchestrator code even though the plugin only calls `process_task()`. Additionally, helper functions like `process_subtasks()` may duplicate the execution loop already in `process_task()` — with slightly different logic (e.g., missing REQ-1 execution subtask injection, different state_tracker interface). If someone modifies the retry loop in `process_task()` but not in `process_subtasks()`, bugs diverge silently. Fix: after any interface migration, audit for and delete all entry points that are no longer called. Verify with `grep -rn "process_investigate\|process_execute\|process_implement\|process_subtasks" --include="*.py"` — if they're not called by any handler, delete them. See `references/requiem-audit-2026-06-24.md` — Findings A1+A2.
- **Auditor auto-pass based on string matching is unreliable:** When an auditor auto-passes execution tasks by checking if the output text contains "passed" or "0 errors", it can false-positive on strings in comments, docstrings, or error messages. Example: a Shade writes `# all tests passed` in a comment, and the auditor auto-passes without checking actual test results. Fix: auto-pass should verify structured data (exit_code from terminal tool JSON output), not grep for success strings in free text. If structured data isn't available, don't auto-pass — call the LLM auditor. See `references/requiem-audit-2026-06-24.md` — Finding D1.
- **API client without retries kills long-running tasks:** A custom LLM API client that makes a single HTTP request with no retry logic will kill entire tasks on transient errors (429 rate limit, 503 service unavailable). A 429 after 4 minutes of Shade work loses everything. Fix: add retry with exponential backoff (3 attempts: 1s, 2s, 4s delays) for transient HTTP errors. This is especially critical for multi-agent systems where a single API call failure cascades through the decomposition→execution→audit pipeline. See `references/requiem-audit-2026-06-24.md` — Finding O2.
- **Migrating granular MCP tools to blocking plugin tools regresses visibility:** When an MCP server exposes async granular tools (decompose/execute/progress/result) and you migrate to a native plugin that collapses them into synchronous blocking calls (investigate/execute/implement), you lose: (1) user visibility — no polling means no narration during multi-minute pipelines; (2) responsiveness — the calling agent blocks for the entire pipeline; (3) routing — without a decompose step, non-implement tasks skip the orchestrator and send raw prompts directly to workers. The migration must preserve the decompose-delegate-poll-result granularity, not just the function names. See `references/mcp-to-plugin-migration-pitfalls.md`.
- **`disabled_toolsets` contradicts SOUL.md creates silent degradation:** When config sets `agent.disabled_toolsets: [terminal, file]` but the agent's SOUL.md instructs it to "read code with read_file, search_files, terminal," the agent tries to follow its SOUL, can't find the tools, and silently degrades. Unlike `toolsets` (which only restricts messaging platforms like Telegram/Discord in v0.17+), `disabled_toolsets` under the `agent:` key disables tools for ALL interfaces including CLI. Always audit `disabled_toolsets` against SOUL.md instructions after config changes.
See `references/mcp-visibility-pattern.md` — Issue 2.
|-

- **Plugin/native migration silently strips orchestration logic:** When migrating a multi-agent system from MCP server to native plugin (or vice versa), the new handlers often bypass the orchestrator's decomposition step entirely. In Requiem Agents, the MCP server had granular tools that called `process_task()` (decompose → shades → audit → retry → escalate). The native plugin replacement introduced 3 new handler functions (`handle_investigate`, `handle_execute`, `handle_implement`) that imported DIFFERENT entry points (`process_investigate`, `process_execute`, `process_implement`) which sent raw prompts directly to individual Shades, skipping decomposition, routing, and audit. The orchestrator code (`process_task`, `process_subtasks`) still existed but was never called. Additionally, the plugin added `_summarize_result()` which used a cheap model to compress all worker output before the assistant saw it — effectively blinding the expensive model to actual results. Symptoms: tasks that took 1 minute via MCP now take 5 minutes via plugin with worse quality; the assistant receives summaries instead of real output; the telemetry DB shows no decomposition/audit entries. Fix: after ANY interface migration (MCP↔plugin, plugin↔direct), verify the new entry points call the same pipeline functions as the old ones. Test with a real task and check telemetry — if there are no decomposition/audit records, the orchestrator was bypassed. See `references/requiem-plugin-reconstruction.md` for the full diagnosis and fix.

- **LLM summarization of worker output blinds the assistant:** A plugin handler that summarizes worker (Shade) results with a cheap model before returning them to the expensive assistant model defeats the purpose of the architecture. The expensive model needs the REAL output to make informed decisions and present accurate results to the user. If results are summarized by a cheaper model, the assistant is working with degraded information — it cannot verify file contents, spot errors the summarizer missed, or make architectural decisions based on actual code. Fix: pass raw output to the assistant, using only head+tail truncation for extremely long results (>50K chars). Never use an LLM to summarize another agent's output for a more capable model's consumption. Disk-based full-result saving (`_save_full_result`) is fine for audit trails — but the assistant must see the real content.

- **Expensive model needs read-only code awareness without file tools:** An assistant with disabled file/terminal tools (to enforce delegation) loses ALL codebase awareness — it delegates blind, writing the CONTEXTO section of delegation prompts from memory or user description rather than actual project structure. Fix: provide a read-only knowledge graph tool (graphify MCP server, or equivalent) so the assistant can query code structure (callers, callees, dependencies, god nodes, shortest paths) without touching files. This cleanly separates "understanding code" (graph query, read-only, no file access) from "touching code" (worker delegation). The assistant uses the graph to fill delegation prompts with real data — file names, function signatures, dependency chains — then delegates execution. The expensive model reasons about structure; the cheap model reads/writes the actual files.

- **Don't maintain custom parsers when a specialized tool exists:** A 244-line custom graph indexer (`indexer.py`) duplicated graphify's functionality but with fewer features (basic query only vs query_graph, get_neighbors, god_nodes, shortest_path, graph_stats), no community detection, and no maintenance cycle. When a specialized tool already provides richer capabilities with its own versioning and bugfixes, discontinue the custom implementation. The maintenance cost of duplicating a specialized tool always exceeds the integration cost of using the original. Rule: if you're writing a parser/indexer for a format that an existing tool already handles better, stop and integrate the tool instead.
- **Don't build custom orchestration when the framework already has it:** hermes-agent's `delegate_task` (2801 lines) provides in-process subagent delegation with AIAgent in ThreadPoolExecutor, fresh context, depth limiting, model override, batch parallel, and auto-approve. Aether's Olympus v3 (5700+ lines) + ACP + SQLite coordination + PID files was a custom orchestration layer that duplicated this functionality with subprocess overhead. The result: 2-10x more tokens and time for no quality benefit. Before building orchestration, read the framework's delegate/delegation tool source code. Rule: if the framework already provides in-process delegation, use it — don't wrap it in subprocesses.
- **Disable direct tools on the orchestrator to force delegation:** If the orchestrator has `file-read`, `file-write`, `terminal`, and `patch` tools, it will use them directly instead of delegating. This defeats the purpose of a multi-agent system — the expensive model wastes tokens on mechanical work. Disable those toolsets on the orchestrator and only enable them on subagents via `delegate_task(toolsets=[...])`.

## Agent Profile Design

Every agent in a multi-agent system needs a profile that defines its identity, capabilities, and limits. This section covers agent types, profile structure (SOUL.md), toolset selection, and the consulting workflow.

### Agent Type Taxonomy

Every agent falls into one of two types, which determines its toolset and authority:

| Type | Purpose | Writes code? | Reads code? | Key toolsets |
|------|---------|-------------|-------------|-------------|
| **Actor** | Implements, creates, modifies files | Yes | Yes | file, terminal, browser, web |
| **Consultant** | Advises, reviews, researches | No* | Yes | web, browser, file (read-only), terminal (read-only) |

*Exception: Consultant-Creators write prototypes (HTML/CSS mockups), not production code.

#### Consultant Sub-types

| Sub-type | Writes? | Example | What it writes |
|----------|---------|---------|----------------|
| **Consultant-Creator** | Yes (non-production) | Design agent | Prototypes, diagrams, mockups |
| **Consultant-Analyst** | No | Security auditor, arch reviewer | Nothing — opinions and analysis only |

#### Invocation Modes

Agents are invoked in one of two ways:

| Mode | Invocation | Session | Examples |
|------|-----------|---------|---------|
| **Delegate** | Orchestrator calls delegate() | Multi-turn, persistent | Implementation agents, researchers, auditors |
| **Function** | MCP tool spawns agent programmatically | Single-turn, auto-closed | Curation agents, automated reviewers |

Function agents have different constraints: minimal toolsets (only what the function requires), no need for `memory`, `session_search`, `todo`, or `clarify` (no conversational continuity), and they never run via delegate — the MCP tool constructs and sends the prompt, then auto-closes.

#### Key Implication: File Toolset Bundling

The `file` toolset bundles `read_file`, `write_file`, `patch`, and `search_files` together. If the framework doesn't support per-tool disabling:

- **Option A (recommended):** Give `file` toolset + SOUL.md restriction ("NEVER modify files"). Models generally respect strong role instructions.
- **Option B (structural):** Create a `custom_toolsets` entry listing only `read_file` and `search_files`. This is purely manual and doesn't auto-update with framework releases.
- **Option C (future):** Per-tool granularity. Not available in most frameworks yet.

For Consultant-Analyst agents, Option A is usually best because: Consultant-Creators need `write_file` for prototypes, and Consultant-Analysts can have strong SOUL.md restrictions that models respect.

### SOUL.md Design Principles

Each agent's SOUL.md (system prompt / identity document) should be designed as a concise role definition, not a bloated manual.

#### Structure (target: 80-130 lines)

A good SOUL.md contains:
1. **Identity** (5-8 lines) — name, role, eponym, one-line purpose
2. **Execution Context** (5-10 lines) — how the agent receives tasks, project root, session scope
3. **Core Responsibilities** (5-8 lines) — numbered list of what the agent does
4. **Hard Limits** (5-8 lines) — what the agent MUST NOT do (with clear boundary)
5. **Protocol sections** — concise rules specific to the agent's domain
6. **Output Format** — mandatory response structure

#### What NOT to put in SOUL.md

- **Few-shot examples** — more than 1 compact example belongs in a skill that loads on-demand
- **Technique references** — curl fallback strategies, API patterns, etc. belong in skills
- **Workflow context** — the agent doesn't need to know about pipeline phases (the orchestrator handles routing)
- **Duplicate definitions** — output format and limits defined once, never repeated
- **Search strategy details** — belongs in a skill, loaded when needed

#### Pitfalls

- **Bloat kills signal:** A 400-line SOUL.md burns tokens every turn. Target 80-130 lines.
- **Duplication equals inconsistency:** If output format appears twice, they'll diverge. Define once.
- **Skills are on-demand, not bloat:** Don't prune an agent's skill list thinking it's loaded every turn. Skills load when the agent decides it needs them. A large skill list = more options, not more context.
- **Empty SOUL.md = silent identity crisis:** An agent with 0-line SOUL.md falls back to the framework's generic default prompt with no role, no limits, no identity. Always verify SOUL.md isn't empty after config changes.
- **Consultant-Creator needs write_file for prototypes:** These agents must write files to prototype and iterate. Don't strip `file` (which bundles write_file) from Consultant-Creators. But DO strip `patch` and `execute_code` — those are Actor tools for modifying production code.
- **Config-template identity drift:** When an agent's role evolves, the config template often still has the OLD role, description, capabilities, and toolsets. Always audit config template against the new SOUL.md after a rework.
- **Content extraction is the primary SOUL reduction mechanism:** For Consultant-Analyst agents, the biggest line savings come from moving detailed checklists, protocols, and few-shot examples into a dedicated skill. Keep a compact reference ("For detailed checklists, load the `reference-skill` skill").

### Consultant Workflow (Delegate-Based)

Consultations use the same delegate mechanism as task execution, but with different prompt structure:

```
When consulting (not implementing), use this prompt structure:
CONTEXT: [2-4 lines]
TASK: [Specific question, NOT an implementation request]
CONSTRAINTS: [Scope limits]
OUTPUT FORMAT: Observations / Risks / Recommendations
```

**Sequential Consultation:** When multiple consultants review the same thing, delegate to the first consultant, receive response, include relevant parts in the next consultant's CONTEXT, filter and synthesize results, present consolidated recommendations to the user.

**Important:** Do NOT document an aspirational `consult` tool that doesn't exist. Only document what actually works: `delegate` with structured prompts.

### Task Decomposition Belongs to the Orchestrator

The orchestration agent owns task decomposition. Individual execution agents should receive atomic tasks, not decompose further. This is a critical architectural boundary:

- **Orchestrator responsibility:** Read the user's request, break into atomic tasks (one agent, one deliverable per task), assign each task using a routing table, delegate with CONTEXT + TASK + CONSTRAINTS + OUTPUT FORMAT
- **Executor responsibility:** Receive atomic tasks and execute them. Do NOT decompose further or spawn sub-agents.
- **What NOT to put in an executor's SOUL.md:** Role catalogs, decomposition protocols, delegation templates. These are orchestrator concerns.

### Structured Delegation Template

When the assistant delegates to the orchestrator via a single tool call, the prompt must be structured — not free-form text. A structured template ensures the orchestrator can decompose correctly and the auditor can validate against explicit criteria:

```
OBJETIVO: [What to accomplish — specific, with technical details: file names, function signatures, expected behavior]
CONTEXTO: [Stack, project structure, conventions, relevant files — filled with data from graphify queries, not guesses]
RESTRICCIONES: [Scope limits, what NOT to do, edge cases, existing dependencies to preserve]
CRITERIOS DE ACEPTACION: [How to verify completion — the auditor (Revenant) uses this to PASS/FAIL]
```

Why one structured tool beats multiple granular tools:
- Fewer tool schemas = less confusion for the model (1 tool vs 3-4)
- The template enforces completeness — missing sections = missing information for decomposition
- The orchestrator owns routing — the assistant shouldn't pre-assign workers
- Acceptance criteria flow directly to the auditor, creating a closed validation loop: the auditor checks what the assistant defined as "done"
- The assistant fills CONTEXTO with real data from graphify queries, not assumptions

The template is MANDATORY for every delegation. Without it, the orchestrator decomposes with insufficient information and the auditor has no explicit criteria to validate against.

## Orchestration Best Practices

Running a multi-agent system day-to-day requires disciplined delegation, monitoring, and failure handling.

### Autonomous Batch Execution

When the user says "hazlo todo de manera autónoma" (do it all autonomously),
execute multi-phase plans without HITL gates. See the `task-delegation` skill
for the full pattern — the key points specific to multi-agent architecture:

1. **Batch by phase** — group tasks by priority. Send all tasks in a phase to
   Hefesto in ONE delegate call with numbered tasks and clear specs.
2. **Verify between phases** — `python3 -m py_compile` on ALL modified files.
   This is ORCHESTRATOR-driven verification, not Daimon-driven.
3. **Handle partial completion** — if Hefesto times out or returns error,
   verify what landed (grep/compile), then re-delegate ONLY the remaining tasks.
4. **Clean .gitignore before committing** — exclude caches, sessions, results,
   venvs, graphify-out/cache, graphify-reference/, raven/sessions/, pastes/.
   These accumulate during agent operation and should never be committed.
5. **Single commit at the end** — `git add -A && git commit` with a summary
   of all phases.

### Delegation: Blocking vs Background

| Mode | Use When | Risks |
|------|----------|-------|
| **Blocking (synchronous)** | Quick tasks (< 2 min), need immediate result, user is waiting | Blocks the orchestrator for the task duration |
| **Background (async)** | Long-running tasks (> 5 min), user wants to work on other things, multi-phase implementations | Need polling/monitoring mechanism |

**Anti-pattern: Blocking on long tasks.** A blocking delegate with a 600s timeout that takes 10 minutes will timeout, lose the session, and leave no way to resume. Use background delegation + monitoring instead.

**When to SKIP delegation entirely:**
- User explicitly says "just do it", "don't ask", "proceed"
- The path is obvious from context (restoring tools after a known experiment)
- User prefers execution over options

### Monitoring Active Sessions

**Polling discipline:**
- Poll every 15-30 seconds (not more frequently)
- Check `tool_calls` count and `last_turn` for progress
- If `status: "completed"` → retrieve result
- If stalled (same `tool_calls` count for 3+ polls) → report to user

**Do NOT narrate each poll to the user.** Just monitor internally and report when: task completes, error occurs, stalled progress needs attention, or user decision is needed.

**Correct tool:** Use `delegate.poll()` (or equivalent) for agent sessions. Do NOT use process-monitoring tools — those are for terminal background processes, not agent sessions.

### Structured Delegation Template for Orchestrator-Worker Systems

When the user-facing agent (expensive model) delegates to an orchestrator, the delegation prompt must be STRUCTURED — not a flat string. The structure serves two consumers: the orchestrator (needs clear objectives to decompose) and the auditor (needs explicit acceptance criteria to validate).

**Template (embed in the assistant's SOUL.md as mandatory):**

```
OBJETIVO: [Qué hay que lograr. Detalles técnicos específicos — nombres de archivos, funciones, comportamiento esperado]
CONTEXTO: [Stack tecnológico, estructura del proyecto, convenciones, archivos relevantes que el assistant conoce]
RESTRICCIONES: [Qué NO hacer. Edge cases. Límites de scope. Dependencias existentes que no tocar]
CRITERIOS DE ACEPTACION: [Cómo verificar que está completo — el auditor usa esto para validar]
```

**Why each section matters:**
- OBJETIVO: gives the orchestrator a clear decomposition target. Vague objectives → bad subtask splits.
- CONTEXTO: prevents Shades from re-discovering the project structure from scratch (saves iterations).
- RESTRICCIONES: prevents scope creep — Shades latch onto tangential details easily.
- CRITERIOS DE ACEPTACION: THE critical section. Without explicit criteria, the auditor has nothing concrete to validate against — it either rubber-stamps or rejects arbitrarily. With criteria like "pytest passes, tests exist for empty-stack edge case, type hints present," the auditor can make a deterministic pass/fail.

**Design decision — single structured tool vs multiple flat tools:** Prefer ONE structured tool (`delegate_to_necromancer(prompt, project_root)`) over multiple flat tools (`investigate`, `execute`, `implement`). A single tool with a mandatory template enforces the architecture — the orchestrator decides decomposition, not the assistant. Multiple flat tools encourage the assistant to route directly to workers, bypassing decomposition.

### Verification After Delegation

**Never trust delegation "completed" without verification.** Agents sometimes report completion when the actual work is incomplete or broken.

**Verification checklist after delegation:**
1. **File existence is not file correctness** — Check file content, not just that files exist
2. **Import resolution** — Can the target runtime actually import all modules? Don't trust "installed" claims
3. **Correct toolchain** — If multiple runtimes exist (venv vs system Python), verify the agent used the right one
4. **Execution test** — Run the entry point. A CLI that exits with `ModuleNotFoundError` is not "done"
5. **Config integrity** — Check API keys aren't truncated with literal "..." placeholders
6. **Acceptance criteria match** — Re-read your own prompt. Did you ask for "CLI running" but only got "all files created"?
7. **Service reachability** — Verify services are reachable (health endpoints) and containers show correct status

### Common Operational Pitfalls

**Pure Orchestrator anti-pattern:** Removing tools from the orchestrator (terminal, file, web) to force full delegation creates unacceptable latency on trivial operations, breaks the orchestrator's diagnostic ability, and removes its programming capability. The real cost optimization is model-tier separation + aggressive decomposition, not tool removal.

**Task drift:** Agents sometimes latch onto ancillary details in the prompt (e.g., "WSL" keyword triggers WSL diagnostics) and investigate unrelated issues instead of the task. Fix with steering directives with explicit STOP commands and, if needed, close and re-delegate with tighter constraints. Prevention: use atomic task format with ANTI-DRIFT guard (DO NOT investigate or modify any system not listed in TASK).

**Scope creep:** When the user authorizes a specific change (e.g., "replace this API key"), execute EXACTLY that change — no more, no less. If additional changes are needed to make the fix work, PRESENT them, don't execute them silently. The user's instruction defines the scope; any expansion requires explicit authorization.

**Rate limit cascading:** When all agents share the same provider/workspace, one rate limit kills the entire fleet. Mitigate with fallback_models per agent profile or different providers for different agents.

**Pipeline visibility:** A single MCP tool that runs the full multi-agent pipeline blocks the calling agent for minutes with zero user visibility. Split into granular tools: decompose (synchronous, returns plan), execute (async, launches pipeline), progress (reads state, returns current phase), result (returns final results). See `references/mcp-visibility-pattern.md`.

**Ghost merge — code in repo, absent from runtime:** A feature is merged to main with full code, dependencies, and documentation — but the runtime tools are NOT loaded. The root cause is almost always a missing MCP server block in config.yaml, not a broken package or venv. Always check the MCP server block first.

**Over-interrogating early-stage ideas:** When a user brings a rough idea for viability assessment, produce a DESIGN.md with what's known and mark gaps. Do NOT demand business model, legal certifications, or team details — those are undefined at the idea stage. Extract what IS defined, assess viability on what's given, and mark gaps as "Por definir."

## Design Process

1. **Identify the problem** — what's wrong with the current/imagined system? (cost? quality? latency? scalability?)
2. **Choose roles** — which of the four roles do you need? Start with all four, remove only if justified
3. **Assign models** — expensive at top, cheap at bottom. The assistant gets the best model; agents get the cheapest that works
4. **Define communication** — who talks to whom? What format? What protocol?
5. **Design the escalation** — how are disagreements resolved? What's the bound?
6. **Choose a theme** — pick a mythology/aesthetic that maps to function
7. **Name the agents** — each name should imply its function within the theme
8. **Write DESIGN.md** — formalize before implementing
9. **Iterate with the user** — present, get feedback, refine
10. **Implement** — delegate to builders

- **Agent operational artifacts must be gitignored before any commit:** Multi-agent systems generate large volumes of operational artifacts during runs: graphify cache (hundreds of AST JSON files), session request dumps (raven/sessions/), paste buffers (raven/pastes/), task results (requiem/results/), debug logs, memory locks, and embedded git repos (graphify-reference/). If these aren't in .gitignore, a `git add -A` produces a commit with 300+ files of noise and triggers embedded-git-repo warnings. Fix: before the first commit after any agent run, audit and add to .gitignore: `graphify-out/cache/`, `graphify-out/.graphify_*`, `raven/sessions/`, `raven/pastes/`, `requiem/results/`, `raven/interrupt_debug.log`, `raven/memories/*.lock`, `graphify-reference/`. Then `git rm -r --cached` any that were already staged.

- **Manually-added MCP server blocks in git-tracked config files get silently overwritten:** When you manually add an MCP server block (e.g., graphify) to a config.yaml that IS tracked in git, any subsequent Daimon delegation that patches or rewrites that file will use the git version as the base — silently dropping the manually-added block. Symptom: graphify was working, then after a Hefesto patch session + gateway restart, graphify MCP tools disappear. Root cause: the MCP block was never committed to git, so any file write operation loses it. Fix: either (A) commit the config changes to git immediately after manual additions, or (B) add config.yaml to .gitignore so git operations don't touch it. Always verify MCP server blocks survive any delegation that touches config files: `grep -n "graphify\|mcp_servers" config.yaml` after patches.

- **Native plugin exists on disk but never loads — missing `plugins:` section in config.yaml:** A plugin can be fully implemented (plugin.yaml, __init__.py, tools.py, schemas.py all present in the plugins/ directory) and listed in `toolsets:` — but if the `plugins:` section is missing from config.yaml, hermes-agent never discovers or loads it. The agent reports "no plugins found" and the plugin's tools are invisible. This is distinct from the "Ghost merge" pitfall (which is about MCP server blocks). Symptom: agent says "I don't have tool X" despite the tool being fully implemented. Fix: verify config.yaml has BOTH `toolsets: [..., plugin_toolset_name]` AND `plugins:\n  enabled:\n    - plugin_directory_name`. The toolset name (registered by the plugin via `ctx.register_tool(toolset="name")`) and the plugin directory name may differ. See `references/requiem-audit-2026-06-24.md` — Finding A1 (plugin enablement).

- **Agent skills go stale after tool interface migrations:** When a multi-agent system migrates its tool interface (e.g., MCP→native plugin, or investigate/execute/implement→delegate_to_necromancer/check_progress/read_file_simple), the agent's skill files (SKILL.md) that teach how to use the OLD tools become actively harmful. A 523-line skill that describes non-existent tools (investigate, execute, implement) confuses the agent more than having no skill at all — the LLM tries to call tools that don't exist. Fix: after ANY tool interface migration, audit and rewrite ALL skills that reference the old tool names. The rewritten skill should be concise (target 90-100 lines) and describe ONLY the current tools. This is a class-level pattern: tool migrations require synchronized updates to config.yaml, SOUL.md, plugin.yaml, AND skill files — missing any one creates a contradiction the LLM cannot resolve.

- **ACP subprocess delegation is 10x heavier than native delegate_task (CRITICAL discovery):** hermes-agent has a built-in `delegate_task` tool (`tools/delegate_tool.py`, 2801 lines) that spawns subagents AS IN-PROCESS AIAgent instances in a ThreadPoolExecutor — zero subprocess overhead. It already implements everything OpenCode does: fresh context per subagent (skip_memory, skip_context_files, ephemeral_system_prompt), nesting prevention (MAX_DEPTH=1, blocked tools), model override per subagent (delegation.provider/model in config), batch parallel execution (up to max_concurrent_children), progress callbacks to parent, timeout + stale detection. Aether/Requiem DISABLES this tool (`disabled_toolsets: [delegation]`) and instead uses olympus_v3 (ACP subprocesses with PID files, SQLite WAL, JSON-RPC over stdio). That means every Daimon delegation spawns a full Python process (3-8s startup), loads its own MCP clients, skills, and config — multiplying overhead 10x. The fix is architectural: enable `delegation` toolset, configure subagent profiles via the `delegation:` config section, drop olympus_v3 entirely. Subagent specialization by permissions (read-only vs full-power) is done via the `toolsets` parameter, not separate profile directories. See `references/hermes-delegate-task-internals.md` for full source code analysis, comparison table, and redesign path.

- **Cross-system convergence: flat 1-level delegation is the industry-standard pattern:** Three independent production systems — OpenCode (github.com/anomalyco/opencode), hermes-agent's built-in delegate_task, and Eigent (github.com/eigent-ai/eigent, built on CAMEL-AI) — all converge on the SAME architecture: 1 primary agent spawns subagents in the SAME PROCESS at depth=1, subagents CANNOT delegate further (structurally enforced), specialization is by permissions/toolsets (not separate SOULs), context is fresh per subagent (no transfer), and result is the last text message (no structured protocol). None uses subprocesses for subagents. None uses 3+ levels. None has a middleman that only routes. The conclusion for Requiem/Aether: the multi-agent collaboration vision (many specialized agents communicating freely) is architecturally inferior to flat delegation for all task sizes tested. The collaboration overhead (context transfer, coordination, state synchronization) exceeds the value of specialization for tasks under ~500 lines of code. See `references/opencode-subagent-architecture.md`, `references/hermes-delegate-task-internals.md`, and `references/eigent-subagent-architecture.md` for full source code analysis of each system.

## Post-Eval Architectural Pitfalls (from comparative eval Requiem vs OpenCode)

The following pitfalls were identified from a comparative eval where Requiem (multi-agent, 0/3 bugs, 18m+, 98K tokens) lost to OpenCode (single-agent, 3/3 bugs, 8m48s, 43K tokens) with the SAME model (glm-5.2). These are structural failures, not model failures. See `references/requiem-eval-results-2026-06-24.md` for full analysis.

After implementing all 8 fixes (commit b3d7c03), a second eval showed Requiem BEATING OpenCode: 3/3 bugs, 3m23s, 29.6K tokens (23% context), 58/58 tests pass — vs OpenCode's 8m48s, 43K tokens. The multi-agent system went from 0/3 to 3/3 and 2.6x faster than the single-agent. See `references/requiem-eval-post-optimization-2026-06-25.md` for full analysis.

- **Shades must be instructed to make PARALLEL tool calls:** If the Shade's system prompt says "output a JSON block" (singular), the LLM generates exactly 1 tool call per response. This makes each read+grep+write take 3 LLM calls instead of 1. Fix: explicitly tell the LLM "You CAN output MULTIPLE tool calls in a single response. Do this whenever possible." This single change provides ~2.5x speedup. The instruction belongs in the tool instructions template, not just the SOUL — it's a protocol rule, not a behavioral preference.

- **Multi-agent overhead exceeds work for simple tasks:** The full pipeline (Raven reads issue → Necromancer decomposes → Shade research investigates → Shade programming writes → Revenant audits → Shade execution tests → Revenant audits → Raven presents) makes 17-28 LLM calls for a 10-line bug fix. A single-agent (OpenCode) does the same in 4-6 calls. Fix: implement a task-complexity classifier at the orchestrator entry point. Simple tasks (1 file, clear fix instruction) skip decomposition + research and go directly to programming + execution with lightweight Revenant (py_compile + pytest only, no LLM audit call). This is NOT a failure of the multi-agent concept — it's a failure of task routing. The architecture works for complex tasks; it just needs to NOT apply itself to simple ones.

- **Polling wastes orchestrator context:** If the assistant agent (Raven) must manually poll check_progress with execute_code(time.sleep()) between polls, each poll cycle consumes a full LLM turn. 15 polling turns = 15 wasted LLM calls = 77% of context budget. Fix: check_progress should accept a `wait=true` parameter that blocks internally (3s poll loop) until completion or timeout. The assistant makes 1 call instead of 15. The blocking happens in the plugin handler, not in the LLM.

- **Retry loops must carry forward context, not restart from scratch:** When the auditor rejects a Shade's work (e.g., has_files=False), the retry should pass the previous attempt's context ("Do NOT re-read files you already know. Go directly to writing the fix.") not just the rejection feedback. Without this, the Shade re-reads the same files in the same order, burning the same tokens, and likely failing the same way. Additionally, add a guard at iteration 15: if no files have been written, force a "write NOW" message.

- **The assistant must NOT solve the bug in its delegation prompt:** If the expensive assistant model (Raven) reasons about the fix and includes it in the delegation prompt ("The fix should use str.rfind() to find the last position"), it defeats the purpose of delegation. The assistant is burning expensive tokens on analysis that the workers should do. Fix: SOUL.md rule — paste the issue verbatim into the template. Fill OBJETIVO/CONTEXTO/RESTRICCIONES/CRITERIOS with information FROM THE ISSUE, not from the assistant's own analysis. The assistant routes; the workers solve.

- **Tool result pruning must preserve enough context for re-use:** When _summarize_tool_result reduces a read_file result to 1 line, the Shade loses the file content it needs and re-reads the same file in later iterations (observed: 6 reads of the same file across iterations 1, 3, 4, 10, 14, 18). Fix: preserve the first 5 lines of read_file output in the summary (not just first_line). Increase _PROTECT_LAST_N from 5 to 8 to protect more recent tool results from pruning.

- **Shade of Research is wasted overhead for specific bug fixes:** When the issue already names the file and function ("fix parse_verdict() in necromancer/revenant.py line 86"), a Research Shade that reads the file for 7 iterations produces information the Programming Shade will rediscover independently. Fix: skip Research for tasks with clear file references. Research only for vague tasks ("improve dashboard performance"). This can be enforced in the decomposition prompt or via the fast-path classifier.

- **Eval cloning from a repo with existing fix commits contaminates results:** When cloning from a local repo that already has fix commits (from a previous eval), the clones contain the fixes. The agent detects the code is already fixed, investigates why issues are still open, and verifies tests pass without writing new code — producing a meaningless eval. Fix: clone from the GitHub remote (which doesn't have the fix commits), or reset the clone to a known pre-fix commit: `git reset --hard <pre-fix-commit-sha>`. This applies to ANY eval that reuses the same repo across runs.

- **Copied .venv is not portable across HERMES_HOME paths:** When setting up an eval environment by copying a Raven profile directory (including `.venv`) from the original project to an eval directory, the `.venv` contains absolute paths (in `pyvenv.cfg`, bin scripts, and `.pth` files) that point to the original location. Launching `hermes` from the copied venv fails with `FileNotFoundError` in `cli.py` (`os.getcwd()`) or `ModuleNotFoundError`. Fix: either (A) use the ORIGINAL project's `.venv` binary with the new `HERMES_HOME` env var (`HERMES_HOME=/eval/path /original/path/.venv/bin/hermes chat --yolo`), or (B) create a fresh venv in the eval directory and `pip install` hermes-agent. Option A is faster for evals — the venv's hermes binary works regardless of HERMES_HOME, which only controls where config.yaml/SOUL.md/plugins/ are found. Always verify with a smoke test (`hermes -z "responde OK" --yolo`) before the real eval run.

- **Eval setup workflow — prepare everything, hand user only the launch commands:** When running a comparative eval between two agents (e.g., Requiem vs OpenCode), the user prefers a fully autonomous setup: delegate all preparation (copy profiles, replace paths in config, verify venv, create SPEC.md) to Hefesto in one batch, then present the user with ONLY the two terminal commands to launch each agent. Do NOT give step-by-step instructions for the user to run — prepare it all yourself and hand over just the final commands. This matches the user's preference: "no se tu prepara todo y nada mas dime que ejecutar."

- **Agent launch via HERMES_HOME, not --config:** Hermes-agent profiles with custom SOUL.md (like Raven) are launched via `HERMES_HOME=/path/to/raven hermes chat --yolo`, NOT `hermes --config config.yaml chat`. The --config flag doesn't exist in hermes-agent's CLI. HERMES_HOME tells the framework where to find config.yaml, SOUL.md, plugins/, and the venv. The --yolo flag enables autonomous mode (no confirmation prompts — essential for evals).

- **_summarize_tool_result can produce summaries longer than the original content:** When preserving 5 lines of read_file output (an optimization to prevent re-reads), the summary with " | " separators and metadata suffix can exceed the original content length for small files. This breaks the pruning contract: a summary longer than the original defeats the purpose. Fix: add a final guard at the end of _summarize_tool_result: `if len(summary) >= len(content): return content[:200] + "..." if len(content) > 200 else content`. This applies to ALL branches, not just read_file.

- **Multi-agent CAN beat single-agent with proper optimization:** The second eval proved that a well-optimized multi-agent system OUTPERFORMS a single-agent (3m23s vs 8m48s, 29.6K vs 43K tokens, same model). The key is matching pipeline depth to task complexity via a fast-path classifier. The multi-agent advantage is parallel specialization — but only when the overhead doesn't exceed the work. This validates the architecture: the problem was task routing, not the multi-agent concept itself.

## References

### Next-Generation Framework Design
- `references/balam-agent-design-2026-06-25.md` — Balam-Agent: third-gen multi-agent framework design (high-level architecture, identity principles, design decisions)
- `references/balam-delegator-only-pattern.md` — Balam as a concrete example of the delegator-only agent pattern: config.yaml `disabled_toolsets` block, token-efficient SOUL.md structure, subagent toolset separation, and 5 design rules for structural enforcement over prompt instructions from Aether (v1), Requiem (v2), and source-code analysis of OpenCode/hermes-agent/Eigent. Documents the "super agent aided by agents" mental model (vs "collaborative team"), flat delegation using native delegate_task, Maya-themed identity, cost-tiered models (glm-5.2 orchestrates, deepseek-v4-flash executes), and the evolution path: Aether->Requiem->Balam. Full DESIGN.md at `/home/prometeo/Balam-Agent/DESIGN.md`.

### Evaluation
- `references/eval-methodology.md` — End-to-end eval methodology for multi-agent systems using real codebase bugs (NOT synthetic benchmarks). Covers: bug scanning, difficulty classification, GitHub issue creation, pipeline measurement (time/tokens/compilation/audit/correctness), independent verification, and autonomous batch execution pattern. Includes the user's explicit rejection of SWE-bench in favor of "problemas REALES, controlados y con respuesta."
- `references/requiem-eval-results-2026-06-24.md` — First comparative eval results: Requiem vs OpenCode, same model (glm-5.2), same 3 bugs. Requiem 0/3 (18m+, 98K tokens, did not finish) vs OpenCode 3/3 (8m48s, 43K tokens, 53 tests). 8 architectural failure modes identified with fixes. Includes optimization plan and key insight: multi-agent overhead exceeds work for simple tasks — need task-complexity classifier at entry point.
- `references/requiem-eval-post-optimization-2026-06-25.md` — Second comparative eval results after implementing all 8 fixes (commit b3d7c03). Requiem BEATS OpenCode: 3/3 bugs, 3m23s, 29.6K tokens (23%), 58/58 tests — vs OpenCode 8m48s, 43K tokens. Includes: optimization impact analysis, eval setup pitfalls (clone contamination, HERMES_HOME launch command), _summarize_tool_result regression discovered by OpenCode, and the key insight that multi-agent CAN beat single-agent with proper task routing.
- `references/requiem-eval3-build-from-scratch-2026-06-25.md` — Eval 3: build-from-scratch (Task Queue System) setup and observations. Tests "understand requirements → design → implement from zero" vs bug-fixing. Documents: venv portability issue across HERMES_HOME paths, user's "prepare everything, just tell me what to run" workflow preference, and check_progress returning errors during long Necromancer tasks (active investigation, not yet resolved).

### General Patterns
- `references/hermes-delegate-task-internals.md` — Deep source-code analysis of hermes-agent's built-in `delegate_task` tool (2801 lines, `tools/delegate_tool.py`). Documents: in-process AIAgent spawning (ThreadPoolExecutor, no subprocess), ephemeral system prompts (not SOUL.md), fresh context (skip_memory, skip_context_files), nesting prevention (MAX_DEPTH=1, blocked tools), model override per subagent (delegation.provider/model), batch parallel execution, progress callbacks, timeout + stale detection. Includes comparison table: delegate_task (native) vs olympus_v3 (ACP subprocess) showing 10x overhead reduction. The critical architectural insight: Aether/Requiem disables `delegation` toolset and uses heavyweight olympus_v3 instead — the fix is to enable native delegation and drop olympus_v3 entirely. — Deep source-code analysis of OpenCode's subagent system (cloned from github.com/anomalyco/opencode). Documents: single-tool flat delegation (1 level, subagents can't nest), permission-based specialization (explore=read-only, general=full), fresh context per subagent (no transfer), framework-level background mode, truncate+prune+compaction context management (no custom summarization), same model for parent and subagent, AGENTS.md for project context. Includes architecture comparison table (OpenCode vs Requiem) and 8 design lessons for multi-agent systems.
- `references/eigent-subagent-architecture.md` — Deep source-code analysis of Eigent's multi-agent system (cloned from github.com/eigent-ai/eigent, built on CAMEL-AI). Documents two modes: (1) Single Agent + DepthLimitedAgentToolkit delegation (same pattern as OpenCode/hermes-agent — depth=1, no recursion, fresh context); (2) CAMEL Workforce mode with coordinator, task planner, and shared task channel. Includes: Brain/Hands architecture (capability=environment), toolkit assembly from config dict, NoteTakingToolkit for lightweight inter-agent communication, cross-system convergence analysis (all three systems converge on flat 1-level delegation), and what's relevant vs not relevant for Requiem/Aether.
- `references/requiem-agents-design.md` — Full DESIGN.md v2 for Requiem Agents (gothic horror theme, 4-role architecture, all design decisions resolved). First system designed using these patterns. Updated with v2.1 plugin migration section: native plugin replacing MCP, graphify as read-layer, structured delegation template, and 3 critical migration failures. Includes implementation plan, installation method (hermes-agent v0.17 pip install), and provider config.
- `references/requiem-plugin-reconstruction.md` — Session log (2026-06-24) of the Requiem MCP→plugin migration reconstruction. Documents the 3 critical failures (orchestrator bypass, LLM summarization blinding, SOUL/config contradiction), the structured delegation template design, graphify as read-layer integration, and the migration verification checklist. Read this before migrating any multi-agent system between integration mechanisms.
- `references/custom-agent-implementation-patterns.md` — Concrete code patterns from Phase 3 implementation: tool registry with role-based subsets, soul-based system prompts, decompose-delegate-audit-retry orchestration loop, MCP server integration, verification pattern, and Pattern 5: text-based tool calling protocol (agentic loop with JSON parsing, `json.loads(strict=False)`, brace escaping in `.format()` templates, infinite loop prevention, context budget management, auditor auto-fail, and telemetry-based debugging). Useful when building a custom multi-agent system without an agent framework.
- `references/text-based-tool-calling-pitfalls.md` — Critical bugs found during integration testing of Requiem Agents. 16 pitfalls covering: json.loads strict=False, .format() brace escaping, infinite loop prevention, context budget, auditor auto-fail, file path tracking, incomplete JSON brace repair, `\'` escaping, research shade looping, directory vs file matching, toolset restriction via `toolsets` key (NOT `platform_toolsets` — that key is silently ignored in v0.17.0; CLI sessions always load all 30 tools regardless — `toolsets` only restricts messaging platforms like Telegram/Discord), decomposition test-running, system prompt dominance suppressing non-dominant tools (with combined A+B+C fix validation: conditional prompts + auditor dual-path + dedicated execution shade), auditor auto-fail must be execution-task-aware, auditor must judge execution quality not test results, and new agent roles need explicit routing rules in orchestrator's soul. Includes performance characteristics (observed token/time metrics per task type, before/after fix comparisons) and a 5-phase structured debugging methodology (telemetry triage → debug prints → filesystem verification → root cause identification → fix and retest). READ THIS before building or debugging any text-based tool calling protocol.
- `references/dashboard-and-testing-patterns.md` — Dashboard implementation (FastAPI backend reading shared SQLite, React + Vite + themed CSS frontend, endpoint inventory, component structure, polling pattern), testing patterns for multi-agent systems without API keys (4 test categories: telemetry, tools, API, structural; temp_db fixture; test environment considerations; verification checklist), and the vibecoding test approach (tmux-based interactive testing with telemetry monitoring instead of structured test plans).
- `references/necromancer-invocation.md` — Direct Necromancer invocation from Hermes' terminal when ACP Daimon spawning fails. Covers the `printf | python3` pipe pattern (bypasses Hermes' orchestrator rule), OPENCODE_GO_API_KEY sourcing from `~/.hermes/.env`, required env vars, terminal tool restriction table, and pitfalls.
- `references/mcp-visibility-pattern.md` — Solving the MCP blocking/visibility problem in multi-agent systems: when a single MCP tool runs the full pipeline, the calling agent blocks for minutes with zero user feedback. Covers the granular split pattern (decompose/execute/progress/result), async background execution with in-memory state tracking, the assistant's polling loop SOUL pattern, the model pyramid inversion (orchestrator gets the expensive model, assistant gets the cheaper one when formalizing is less cognitively demanding than decomposing), testing MCP servers without a full MCP client (import + asyncio.run), the `agent` keyword conflict in hermes-agent MCP framework (use `daimon` instead), and the Hefesto file-mutation verifier false positive pattern.
- `references/mcp-to-plugin-migration-pitfalls.md` — 4 regression patterns observed when migrating a multi-agent system from MCP server to native plugin: blocking tools replacing granular async tools, `disabled_toolsets` contradicting SOUL.md, result summarization stripping decision signal, and process routing skipping decomposition. Includes a general migration checklist.
- `references/requiem-plugin-reconstruction.md` — Diagnostic and fix for when a MCP→native-plugin migration silently bypasses the orchestrator's decomposition pipeline. Covers the 3 failure modes (bypassed decomposition, LLM summarization of results, SOUL/config contradiction), the single-tool-with-template fix, and why "simplify the tools" is the wrong instinct. Includes the OBJETIVO/CONTEXTO/RESTRICCIONES/CRITERIOS delegation template.
- `references/requiem-plugin-reconstruction.md` — Diagnosis and fix of the MCP→native plugin migration that silently stripped orchestration logic (bypassed decomposition, LLM summarization blinding the assistant, SOUL/config contradiction). Documents the single-tool structured delegation pattern (OBJETIVO/CONTEXTO/RESTRICCIONES/CRITERIOS template), the graphify MCP integration decision (read-only code understanding for expensive assistant model), and the indexer.py deprecation in favor of the specialized graphify tool.
- `references/requiem-req-fixes-2026-06-24.md` — Session log of 4 requerimientos from end-to-end testing: REQ-1 (Revenant auto-fail syntax errors + orchestrator injects execution subtask, including f-string patch pitfall), REQ-2 (Shade Programming efficiency rules — max 5 iterations, no self-testing, no re-reads), REQ-3B (read_file_simple rate limiter design), REQ-4 (async delegate + check_progress with state_tracker), and the ACP zombie process pitfall after the edit approval fix.
- `references/requiem-audit-2026-06-24.md` — Architecture audit of Requiem v0.3.0 after REQ fixes. 14 findings across 3 dimensions (architecture, design, optimization). Critical: dead code from MCP migration (process_investigate/execute/implement + process_subtasks duplicating process_task), graphify graph contaminated by external code. High: read_file_simple counter never resets (permanent block after turn 1), auditor auto-pass string matching unreliable, API client without retries. Includes top-3 budget-limited fix priorities.
- `templates/project-audit-prompt.md` — Reusable prompt template for auditing a multi-agent project's architecture, design decisions, and optimizations. Produces severity-ordered findings table with top-3 priorities. Customizable for any project hierarchy.
- `references/mcp-verification-testing.md` — End-to-end verification pattern for async MCP server refactors: 9-step checklist (compile → grep → pytest → functional mock), mocking async background functions to test execute→progress→result flow without real LLM calls, using project venv (not system Python) for MCP SDK dependencies, heredoc-pipe pattern to bypass `python3 -c` orchestrator block, and stderr audit for MCP protocol safety.

### Absorbed Reference Files (from daimon-design + aether-agents-orchestration)
The following reference files were absorbed from the consolidated `daimon-design` and `aether-agents-orchestration` skills. They document Aether Agents-specific case studies, bugs, and operational patterns:
- `references/etalides-v0.10-rework.md` — Etalides rework case study (417→126 lines, web+codebase researcher)
- `references/daedalus-v0.10.1-design.md` — Daedalus Consultant-Creator rework design
- `references/ariadna-function-agent.md` — Ariadna function agent architecture & invocation modes
- `references/athena-v0.11.1-rework-design.md` — Athena rework: Security Engineer → Consultant-Analyst
- `references/hefesto-v0.11-rework-design.md` — Hefesto rework: removing decomposition protocols from executor
- `references/release-workflow.md` — Aether Agents release workflow (CHANGELOG, tagging, GitHub Releases)
- `references/olympus-v3-data-model.md` — Olympus v3 inter-agent communication DB schema
- `references/mcp-content-limits.md` — Delegation content-size limits investigation & workarounds
- `references/acp-client-file-operations.md` — ACP client workarounds for write_file/patch denial
- `references/toolset-dependency-audit.md` — How to trace references when removing a toolset from an agent (toolset trimming ripple effects)
- `references/olympus-acp-debugging.md` — Olympus ACP delegation errors: 7 root causes, diagnostic flow prioritization
- `references/olympus-v3-full-diagnostic.md` — Complete olympus_v3 MCP health diagnostic: systematic 9-step checklist testing all 5 MCP actions, zombie process detection, DB verification, and gateway status. Use when user asks "is everything working?" — not just when delegation fails.
- `references/gateway-mcp-env-injection.md` — Gateway MCP server environment variable injection (systemd EnvironmentFile)
- `references/hermes-pure-orchestrator.md` — Pure Orchestrator experiment post-mortem (why removing tools breaks UX)
- `references/delegation-patterns.md` — Delegation patterns reference (blocking vs background, polling discipline)
- `references/daimon-config-changes.md` — Guidelines for changing Daimon config without scope creep
- `references/early-stage-idea-handling.md` — Handling Phase 1/IDEA stage without over-interrogation
- `references/cost-optimization.md` — Cost optimization strategies for multi-agent fleets
- `references/honcho-integration.md` — Honcho memory integration patterns
- `references/api-key-management.md` — API key management across multi-profile fleets
- `references/v016-upgrade-refactoring.md` — v0.16.0 upgrade and refactoring notes
- `references/wsl-cross-distro-pitfalls.md` — Cross-distro WSL delegation patterns and pitfalls
- `references/opencode-go-usage-limit.md` — OpenCode Go usage limit and fallback strategies
- `references/plugin-yaml-missing-bug.md` — Plugin YAML discovery bug investigation
- `references/graphify-usage-patterns.md` — Graphify knowledge graph navigation patterns
- `references/user-preference-check-own-tools-first.md` — User preference: check own tools before asking questions
- `references/external-agent-research-pattern.md` — External agent research delegation pattern
- `references/expanding-team-reach.md` — Expanding agent team reach patterns
- `references/olympus-v3-observability-fix.md` — Fix: zero-observability gap in Daimon delegation
