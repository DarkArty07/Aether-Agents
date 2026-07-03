# In-Process Delegation vs Subprocess Orchestration

Comparative analysis of three multi-agent systems, their delegation mechanisms, and why they converge on the same pattern. Source: session analyzing OpenCode, hermes-agent delegate_task source code, and Eigent/CAMEL.

## The Convergence Pattern

Three independently developed systems all converged on the same architecture:

| System | Delegation mechanism | Process model | Depth |
|--------|---------------------|---------------|-------|
| OpenCode `task` tool | Subagent session in same process | 1 process | 1 (leaf) |
| hermes-agent `delegate_task` | AIAgent object in ThreadPoolExecutor | 1 process | 1 (leaf, configurable to 3) |
| Eigent/CAMEL `DepthLimitedAgentToolkit` | ChatAgent child in same process | 1 process | 1 (leaf) |

All three: same process, 1 level of delegation, no recursion, fresh context per subagent, restricted toolsets.

## Overhead Taxonomy — What Makes Multi-Agent Slow

| Overhead source | Subprocess approach (Aether/Requiem) | In-process approach (delegate_task) |
|----------------|--------------------------------------|-------------------------------------|
| Agent startup | 3-8s (launch hermes subprocess) | ~0ms (Python object creation) |
| Communication | ACP pipes + JSON-RPC over stdio | Direct function calls |
| State sync | PID files + SQLite WAL + race conditions | In-memory (shared process state) |
| Context transfer | Packaged between levels (token cost) | Fresh context, no transfer |
| Process count | N processes (one per agent) | 1 process, N threads |
| MCP client init | Per-process (6x graphify, context7, etc.) | Shared from parent |

## OpenCode `task` tool (TypeScript, ~346 lines)

Key design decisions from source (`packages/opencode/src/tool/task.ts`):

1. **Single tool, 3 params**: `subagent_type`, `prompt`, `background`
2. **No nesting**: subagents have `task` tool DENIED by default (via `subagent-permissions.ts`)
3. **Two native subagent types**: `explore` (read-only: grep, glob, list, bash, read, websearch, webfetch) and `general` (full permissions)
4. **Specialization by permissions, not role**: same model, same base prompt, different toolsets
5. **Background mode at framework level**: `background: true` returns immediately, framework notifies on completion
6. **Context management**: Truncate (2000 lines/50KB), Prune (old tool outputs compacted after 40K tokens), Compaction (LLM summarizes old conversation when context overflows)
7. **Subagent returns only final text**: no intermediate tool calls visible to parent

## hermes-agent `delegate_task` (Python, 2801 lines)

Key design decisions from source (`tools/delegate_tool.py`):

1. **In-process AIAgent**: `from run_agent import AIAgent; child = AIAgent(...)` — same Python process, ThreadPoolExecutor
2. **Fresh context**: `skip_context_files=True`, `skip_memory=True`, `ephemeral_system_prompt=child_prompt`, `quiet_mode=True`
3. **Depth limiting**: `MAX_DEPTH=1` default, configurable via `delegation.max_spawn_depth` (cap: 3)
4. **Blocked tools**: `delegate_task`, `clarify`, `memory`, `send_message`, `execute_code` — no recursion, no user interaction, no side effects
5. **Per-subagent model override**: `delegation.provider`, `delegation.model`, `delegation.base_url`, `delegation.api_mode` in config.yaml
6. **Batch parallel**: up to `max_concurrent_children` (default 3) subagents in parallel via ThreadPoolExecutor
7. **Auto-approve**: `subagent_auto_approve` config — deny (safe default) or approve (YOLO for cron/batch)
8. **System prompt builder**: `_build_child_system_prompt()` creates focused prompt from goal + context + workspace path
9. **Role parameter**: `leaf` (default, cannot delegate) or `orchestrator` (retains delegation toolset, subject to depth cap)
10. **Heartbeat**: child periodically touches parent's activity timestamp to prevent gateway timeout
11. **Credential pool sharing**: subagents can share parent's credential pool for rate-limit rotation

### Key config pattern for cost optimization:
```yaml
model:
  default: expensive-reasoning-model  # orchestrator
delegation:
  provider: cheap-provider
  model: fast-cheap-model  # subagents
  max_iterations: 50
  max_spawn_depth: 2
  subagent_auto_approve: true
```

## Eigent/CAMEL `DepthLimitedAgentToolkit` (Python)

Key design decisions from source (`backend/app/agent/toolkit/depth_limited_agent_toolkit.py`):

1. **Wrapper on CAMEL's AgentToolkit**: removes delegation tools from child toolsets
2. **Depth tracking**: `current_depth` and `max_depth` — children can't delegate
3. **System message injection**: appends "You are a child sub-agent. Complete the task directly and do not create or delegate to any further sub-agents."
4. **Workforce mode** (separate): CAMEL Workforce with Coordinator + Task Planner + Worker Nodes + shared task channel — but all in same process
5. **Toolkits as specialization**: DeveloperAgent (terminal, file, web_deploy), BrowserAgent (search, browser), DocumentAgent (file, pptx, excel), MultiModalAgent (video, audio, image)
6. **"Hands" abstraction**: capabilities determined by deployment environment, not agent type

## What "Agent Collaboration" Really Means in Production

The difference between "agents collaborating" (idealistic) and "agents delegating" (practical):

- **Collaborating** implies: bidirectional communication, shared state, coordination overhead
- **Delegating** implies: here is the task, do it, return the result — minimal overhead

All three production systems chose delegating. None chose collaborating for their core loop.

Eigent's Workforce mode (coordinator + task planner + shared channel) is the closest to "collaboration", but it's still single-process with objects, not subprocesses.

## Designing a New Framework on delegate_task

When building a new multi-agent framework on hermes-agent:

1. **Enable `delegation` in toolsets** (it's disabled by default in Aether's Hermes config — `disabled_toolsets: [delegation]`)
2. **Disable direct file/terminal tools** on the orchestrator — force delegation:
   ```yaml
   disabled_toolsets:
     - file          # disables read_file, write_file, patch, search_files (all bundled in "file")
     - terminal      # if you want pure delegation (Balam keeps terminal for quick checks)
   ```
3. **Define subagent "profiles" as toolset + ephemeral prompt combos** (not separate processes)
4. **Use delegation config for model split** — expensive model reasons, cheap model executes
5. **Don't build custom orchestration** (Olympus v3, ACP, SQLite coordination) — delegate_task already handles it
6. **SOUL.md must be token-efficient** — Requiem's Raven SOUL was optimized to use very few tokens. This is a competitive advantage.

## Reference Implementation: Balam-Agent

Balam-Agent (DarkArty07/Balam-Agent) is a reference implementation of the in-process delegation approach:

- Main agent: deepseek-v4-pro (strong reasoning) — NO file tools (terminal IS enabled for quick checks)
- Subagents: deepseek-v4-flash (fast, cheap, good code) via delegate_task
- Two subagent types: Explorer (read-only, enforced via context not toolsets) + Builder (full access)
- Graphify MCP shared from parent
- Maya-themed identity from day one
- SOUL.md ~2900 bytes — token-efficient (v1 was 1469 bytes, v2 grew to include concrete delegation templates)

## Key Lesson

The market has spoken: **1 agent + flat subagents in same process** is the winning pattern. Multi-agent systems that use subprocesses, multiple levels of hierarchy, or custom orchestration layers pay 2-10x overhead for no quality benefit. hermes-agent already has the right tool (`delegate_task`) — use it instead of building around it.
