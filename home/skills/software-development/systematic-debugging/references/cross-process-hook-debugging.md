# Cross-Process Hook & Guard-Condition Debugging

Debugging data flow across process boundaries in the Hermes Agent ecosystem (Olympus v3 MCP server ↔ ACP Daimon).

## When This Pattern Applies

One process writes data (tool calls, turns, file changes) via hooks, and a **different** process reads that data from a shared store (SQLite, file, etc.). The writer's hooks are guarded by conditions — when a guard silently blocks a hook, the reader sees stale/incomplete data with no error anywhere in the stack.

**Smell:** Table A has N rows, table B has 0 rows, and both are populated by hooks in the same process.

## The Multi-Layer Trace (4-Layer Stack)

```
Layer 1: MCP Server (server.py)
  → Exposes talk_to/discover tools to Hermes
  → Calls ACPManager for spawn/message/poll/close

Layer 2: ACP Manager (acp_manager.py)
  → Spawns Daimon as subprocess via agent-client-protocol
  → Sends prompts, polls SQLite, closes sessions
  → Writes PID-suffixed files for cross-process session ID

Layer 3: ACP Protocol / Daimon Process (hermes acp --profile <name>)
  → HermesACPAgent (acp_adapter/server.py) receives prompt
  → Runs AIAgent.run_conversation() in thread pool
  → Plugin hooks fire inside the Daimon process

Layer 4: Plugin Hooks (olympus_v3_hooks/hooks.py, aether_hooks/hooks.py)
  → post_tool_call, post_llm_call, on_session_end, pre_llm_call
  → Write synchronously to shared SQLite (WAL mode)
```

## The Guard-Condition Bug Pattern

**Definition:** A hook is wrapped in `if <condition>:` where the condition can fail silently, causing the hook to never execute. No error is raised, no warning is logged — data is simply absent.

### Classic Example: `post_llm_call` in run_agent.py

```python
# Guard condition — both must be truthy
if final_response and not interrupted:
    invoke_hook("post_llm_call", ...)
```

Two ways this fails:

| Guard | Fails when | Consequence |
|-------|-----------|-------------|
| `final_response` is falsy | Model returns `content: null` or `""` | Hook never fires |
| `not interrupted` is False | Agent was interrupted mid-turn | Hook never fires |

Meanwhile `post_tool_call` has NO guard and fires during the loop, so the `tool_calls` table is populated while the `turns` table stays empty.

### Diagnosis Technique

**Step 1: Identify the discrepancy.** Which tables/stores have data and which don't? This tells you which hooks fire and which don't.

**Step 2: Find all guards on the missing hook.** Search for:

```python
# In the agent's main loop file (run_agent.py or similar):
if <cond> and not <cond>:
    invoke_hook("hook_name", ...)
```

**Step 3: Trace when each guard variable is set.**

For `final_response`:
```python
# Initial value
final_response = None

# Set during loop (line ~14990):
final_response = assistant_message.content or ""

# Fallback after loop (line ~15388):
final_response = self._handle_max_iterations(messages, api_call_count)
```
Key insight: `""` is falsy — if the model returns empty content, the guard fails.

For `interrupted`:
```python
# Initial value
interrupted = False

# Set when interrupt detected (line ~12247):
if self._interrupt_requested:
    interrupted = True
    break  # ← Breaks BEFORE final_response is set
```

**Step 4: Understand what sets the interrupt.**

The ACP `cancel()` notification → `HermesACPAgent.cancel()` → `agent.interrupt()` → `self._interrupt_requested = True`. But `close_session()` (called by `acp_manager.close()`) does NOT call `cancel()`. The bug manifests in the normal close flow because the protocol-level close does not interrupt the agent, yet the guard still catches a stale `interrupted` flag from a prior signal or race condition.

### How to Fix

**Option A: Remove the guard (fire the hook unconditionally)**

```python
# Before
if final_response and not interrupted:
    invoke_hook("post_llm_call", ...)

# After — always fire, let hooks decide what to do with empty data
invoke_hook("post_llm_call", ...)
```

The hook itself can handle empty responses gracefully.

**Option B: Ensure fallback values**

```python
# Before the guard, ensure final_response is never falsy:
if not final_response:
    final_response = "(no text response)"
```

**Option C: Capture content from tool-calling turns**

When a model returns content alongside tool calls, save it as a fallback:
```python
if assistant_message.content and assistant_message.tool_calls:
    self._last_content_with_tools = assistant_message.content
```

Then use it if `final_response` is empty after the loop.

## Session ID Resolution Across Processes

When debugging cross-process hook issues, verify the session ID resolution at every level:

### Writer side (Daimon hooks)

The PID-suffixed file approach:
1. **Orchestrator** writes `{profile_dir}/.olympus_session.{pid}` where `pid` = Daimon's process PID
2. **Daimon** reads `{HERMES_HOME}/.olympus_session.{os.getpid()}`

Priority chain in `_get_session_id()`:
1. `OLYMPUS_SESSION_ID` env var
2. `{HERMES_HOME}/.olympus_session.{pid}` (PID-suffixed, concurrent-safe)
3. `{HERMES_HOME}/.olympus_session` (legacy file)
4. Previously cached value

### Key Pitfalls

- The PID-suffixed file is written in `send_message()` BEFORE `prompt()` is called — timing is reliable
- Files are cleaned up only in `shutdown_agent()`, NOT in `close()` — so they persist through the agent's execution
- If the Daimon process forks or reuses a PID, the old file might contain a stale session ID
- The `OLYMPUS_SESSION_ID` env var is NOT set during `_spawn_process()` — only the PID file is used for ACP sessions

## Shared SQLite Access Pattern

Both the MCP server (async, aiosqlite) and Daimon hooks (sync, sqlite3) write to the same `olympus_v3.db`.

| Aspect | MCP Server | Daimon Hooks |
|--------|-----------|--------------|
| Module | `OlympusDB` (async) | `OlympusDBSync` (sync) |
| Library | aiosqlite | stdlib sqlite3 |
| Connection | Long-lived singleton Per-call | open/close |
| WAL | `PRAGMA journal_mode=WAL` at connect | Same |

WAL mode allows concurrent reads/writes between processes. No locking conflicts expected.

### Verification

To confirm the hooks are installed and firing:

```bash
# Check plugin.yaml declares the hook
cat {profile_dir}/plugins/olympus_v3/plugin.yaml
# hooks: [post_llm_call, post_tool_call, on_session_end, pre_llm_call]

# Check __init__.py correctly imports the register function
cat {profile_dir}/plugins/olympus_v3/__init__.py
# from olympus_v3.olympus_v3_hooks.hooks import register
```

To check actual DB state during debugging:

```sql
SELECT * FROM turns WHERE session_id = '<session_id>';
SELECT * FROM tool_calls WHERE session_id = '<session_id>';
SELECT * FROM sessions WHERE session_id = '<session_id>';
```
