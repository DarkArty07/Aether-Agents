# hermes-agent delegate_task — Source Code Analysis

## Location
`tools/delegate_tool.py` (2801 lines) inside the hermes-agent package.

## Key Finding
hermes-agent has a **built-in in-process subagent system** that does exactly what OpenCode's `task` tool does. Aether/Requiem does NOT use it — instead using olympus_v3 (ACP subprocesses) which is 10x heavier.

## Architecture

```
Parent AIAgent
  └── delegate_task(goal="...", context="...", toolsets=[...])
        └── _build_child_agent() → AIAgent(...)   # NEW instance, SAME process
              └── child.run_conversation()           # runs in ThreadPoolExecutor
                    └── returns summary text to parent
```

No subprocess. No ACP. No pipes. No PID files. No SQLite coordination. Just a Python object in a thread.

## How It Works (step by step)

### 1. Child Agent Construction (_build_child_agent, line 870)

```python
from run_agent import AIAgent

child = AIAgent(
    base_url=effective_base_url,        # inherits parent or override
    api_key=effective_api_key,
    model=effective_model,              # can be different from parent
    provider=effective_provider,
    enabled_toolsets=child_toolsets,    # restricted subset
    quiet_mode=True,                    # no output to user
    ephemeral_system_prompt=child_prompt,  # NOT from SOUL.md
    skip_context_files=True,            # no AGENTS.md, CLAUDE.md
    skip_memory=True,                   # no MEMORY.md
    session_db=parent_agent._session_db,  # shares session DB
    parent_session_id=parent_agent.session_id,
    log_prefix=f"[subagent-{task_index}]",
)
```

### 2. System Prompt Construction (_build_child_system_prompt, line 569)

NOT the SOUL.md. A focused prompt built from the delegation call:

```
You are a focused subagent working on a specific delegated task.

YOUR TASK:
{goal}

CONTEXT:
{context}

WORKSPACE PATH:
{workspace_path}

Complete this task using the tools available to you.
When finished, provide a clear, concise summary of:
- What you did
- What you found or accomplished
- Any files you created or modified
- Any issues encountered
```

No theming, no persona, no mythology. Pure task execution.

### 3. Fresh Context — No History Transfer

```python
# Child gets a completely fresh conversation
# No parent messages, no accumulated state
child.run_conversation(user_message=goal)
```

### 4. Nesting Prevention (flat by default)

```python
MAX_DEPTH = 1  # parent (0) -> child (1); grandchild rejected

DELEGATE_BLOCKED_TOOLS = frozenset([
    "delegate_task",   # no recursive delegation
    "clarify",         # no user interaction
    "memory",          # no writes to shared MEMORY.md
    "send_message",    # no cross-platform side effects
    "execute_code",    # children should reason step-by-step
])
```

Configurable via `delegation.max_spawn_depth` (cap: 3).

Children with role='leaf' (default) have delegate_task stripped from their toolset.
Children with role='orchestrator' retain it (bounded by depth).

### 5. Model Override Per Subagent

Config section:
```yaml
delegation:
  provider: openrouter        # different provider for subagents
  model: deepseek/deepseek-chat-v3-0324
  max_iterations: 50
  max_concurrent_children: 3
  max_spawn_depth: 2
  subagent_auto_approve: true  # auto-approve dangerous commands (YOLO)
  reasoning_effort: low        # cheaper reasoning for subagents
```

When `delegation.provider` is set, children use those credentials instead of inheriting parent's.

### 6. Batch Parallel Execution

```python
# Multiple tasks run in parallel via ThreadPoolExecutor
tasks: [
    {"goal": "research A", "toolsets": ["web"]},
    {"goal": "research B", "toolsets": ["web"]},
    {"goal": "implement C", "toolsets": ["terminal", "file"]},
]
# Up to max_concurrent_children (default 3) run simultaneously
```

### 7. Progress Callbacks

The parent agent receives real-time progress:
- `subagent.start` — child begins
- `subagent.tool` — each tool call
- `subagent.thinking` — reasoning text
- `subagent.complete` — child finishes

These are relayed via the parent's `tool_progress_callback` — visible in TUI and gateway.

### 8. Timeout + Stale Detection

- Hard timeout per child (configurable via `delegation.timeout`)
- Heartbeat thread monitors child activity (iteration count + current tool)
- If no progress for N heartbeat cycles → stop heartbeating, let gateway timeout fire
- Diagnostic dump on 0-API-call timeouts

## vs olympus_v3 (Aether/Requiem approach)

| Aspect | delegate_task (native) | olympus_v3 (Aether) |
|--------|----------------------|---------------------|
| Process model | Same process, ThreadPoolExecutor | Subprocess `hermes acp --profile X` |
| Startup time | ~0ms (Python object) | 3-8s (full Python boot) |
| Communication | Direct Python call | ACP pipes (JSON-RPC over stdio) |
| State sync | None needed (same process) | PID files + SQLite WAL |
| System prompt | Ephemeral, built from goal | SOUL.md from profile dir |
| Memory | skip_memory=True (no MEMORY.md) | Full memory per profile |
| Context files | skip_context_files=True | Full AGENTS.md/CLAUDE.md per profile |
| MCP servers | Inherits parent's | Each Daimon loads its own |
| Skills | Inherits parent's | Each Daimon loads its own |
| Process count | 1 | Up to 7 (Hermes + 6 Daimons) |
| Config needed | `delegation:` section in config.yaml | Full profile dir per Daimon |

## Why Aether Doesn't Use It

Aether's Hermes config has:
```yaml
agent:
  disabled_toolsets:
    - delegation    # ← DISABLED
```

This was done because Hermes is meant to be a pure orchestrator (no direct implementation). But disabling `delegation` kills the in-process subagent mechanism, forcing the fallback to olympus_v3 subprocesses.

## The Redesign Path

Requiem (or any hermes-agent multi-agent system) can use delegate_task natively:

1. **Enable delegation** in orchestrator config: remove `delegation` from `disabled_toolsets`
2. **Configure subagent profiles** via `delegation:` section (provider, model, max_iterations)
3. **Use role='orchestrator'** for the first delegation level if further nesting is needed
4. **Drop olympus_v3** (ACP subprocesses, PID files, SQLite coordination hooks)
5. **Keep .aether** — can be injected via ephemeral_system_prompt or a lightweight pre_llm_call hook

The subagent "Hefesto" becomes:
```yaml
delegation:
  provider: opencode-go
  model: deepseek-v4-flash
  max_iterations: 50
  max_concurrent_children: 3
```

Invoked as:
```python
delegate_task(
    goal="Implement the Task model with UUID, status enum, priority validation",
    context="FastAPI + SQLite project at /path/to/project. Use raw SQL, no ORM.",
    toolsets=["terminal", "file", "patch"]
)
```

No subprocess. No ACP. Same process. Thread pool.

## Toolset Resolution — How Child Tools Are Selected

### Parent toolset expansion (_expand_parent_toolsets, line ~470)

When the parent uses composite toolsets (e.g. `hermes-cli` which bundles all core tools), the child can request individual toolsets like `web` or `terminal`. A simple name intersection would reject them because `"web" != "hermes-cli"`. This function expands parent toolsets into their constituent tool names, then adds any individual toolset whose tools are a subset.

### Toolset intersection rule

Child toolsets are INTERSECTED with the parent's available toolsets. BUT — the parent's available toolsets are derived from `enabled_toolsets` (what the parent HAS), NOT from `disabled_toolsets`. This means:

  - If the parent has `terminal` in `disabled_toolsets`, the child CAN still receive `terminal` — because the intersection is against what the parent's profile makes available, not what the agent chose to disable.

This is critical for Balam's architecture: Balam has file operations and terminal in `disabled_toolsets` (forced delegation), but subagents CAN receive those tools because they're available in the profile. The toolset name is `file` (NOT `file-read`/`file-write`).

### MCP inheritance (_preserve_parent_mcp_toolsets, line ~530)

Controlled by `delegation.inherit_mcp_toolsets` (default `true`). When a child receives narrowed toolsets, parent MCP toolsets (e.g. `graphify`) are preserved. This means subagents automatically get access to Graphify or other MCP servers configured on the parent.

### Blocked tools (DELEGATE_BLOCKED_TOOLS, line 45)

Children NEVER get these, regardless of what toolsets are requested:
- `delegate_task` — no recursive delegation (unless role="orchestrator")
- `clarify` — no user interaction
- `memory` — no writes to shared MEMORY.md
- `send_message` — no cross-platform side effects
- `execute_code` — children reason step-by-step, not write scripts

## The `context` Parameter — Subagent Customization Vector

The `context` string passed to delegate_task is embedded LITERALLY in the child's ephemeral system prompt via `_build_child_system_prompt()`. This is the primary mechanism for creating "subagent types" (Explorer vs Builder) WITHOUT modifying the framework:

```python
# Explorer subagent — read-only identity injected via context
delegate_task(
    goal="Investigate the Stripe API payment endpoint structure",
    context="You are Kinich (Explorer). Read-only investigator. Report findings concisely. Do NOT modify any files.",
    toolsets=["web", "file"]       # "file" bundles read_file+write_file+patch+search_files; context enforces read-only
)

# Builder subagent — full access identity injected via context
delegate_task(
    goal="Create src/api/stripe.py with payment intent creation",
    context="You are Chaac (Builder). Full access. Implement cleanly. Run tests after.",
    toolsets=["terminal", "file"]  # "file" bundles read+write+patch+search; no need to list them individually
)
```

**PITFALL:** The toolset is called `file` (NOT `file-read` or `file-write` — those names DO NOT EXIST in hermes-agent's TOOLSETS dictionary and are SILENTLY IGNORED in disabled_toolsets). The `file` toolset bundles: `read_file`, `write_file`, `patch`, `search_files`. You cannot disable individual tools within a toolset — you disable the whole toolset or you don't.

The child sees this in its system prompt:
```
YOUR TASK:
{goal}

CONTEXT:
{context}    ← your identity and rules appear here
```

No framework modification needed. The SOUL.md of the parent agent teaches it WHEN and HOW to use each delegation pattern.

## Orchestrator Kill Switch

`delegation.orchestrator_enabled: false` in config.yaml silently forces ALL role="orchestrator" requests to "leaf". This is a global kill switch for nested delegation — useful when you want flat-only architecture (like Balam v0.1).

## Full Tool Schema (what the LLM sees)

```json
{
  "name": "delegate_task",
  "parameters": {
    "goal": "string — what the subagent should accomplish (self-contained)",
    "context": "string — background info: file paths, errors, constraints, IDENTITY",
    "toolsets": ["array of toolset names — default inherits parent's"],
    "tasks": [{"goal": "...", "context": "...", "toolsets": [...], "role": "leaf|orchestrator"}],
    "role": "leaf (default) | orchestrator (can spawn children)",
    "acp_command": "string — override ACP CLI (e.g. 'copilot')",
    "acp_args": ["array — args for acp_command"]
  }
}
```

- `max_iterations` parameter exists but is IGNORED — config value is authoritative
- `tasks` array enables batch parallel execution (up to max_concurrent_children)
- Per-task `role` overrides the top-level `role`

## Key Internals for Customization

- `_build_child_system_prompt()` (line 569) — builds the ephemeral prompt from goal+context. The `context` param is the customization vector for subagent identity.
- `_expand_parent_toolsets()` (line ~470) — expands composite toolsets so children can request individual tools
- `_preserve_parent_mcp_toolsets()` (line ~530) — keeps parent MCP servers in children (controlled by inherit_mcp_toolsets)
- `_resolve_delegation_credentials()` (line ~2100) — resolve provider/model from config
- `_get_subagent_approval_callback()` (line ~120) — control dangerous-command approval
- `_get_max_spawn_depth()` (line ~400) — depth cap (default 2, hard cap 3)
- `_get_orchestrator_enabled()` (line ~432) — kill switch for orchestrator role
- `_normalize_role()` (line ~312) — coerces unknown role strings to "leaf"
- `interrupt_subagent()` (line ~210) — kill a running subagent
- `list_active_subagents()` (line ~225) — enumerate running subagents for monitoring
