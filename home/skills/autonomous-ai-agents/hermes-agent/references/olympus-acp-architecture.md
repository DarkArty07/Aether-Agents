# Olympus v3 ACP Architecture — Internal Reference

How Aether Agents' Daimon delegation works under the hood. This documents
the code paths, data flow, and key integration points for anyone modifying
the Olympus MCP server or the bidirectional communication system.

## Architecture Overview

```
Hermes (orchestrator)
  → mcp_olympus_v3_talk_to(action="delegate", agent="athena")
    → acp_manager.spawn_agent("athena")
    → Subprocess: hermes acp --profile athena
    → acp_adapter/server.py: ACPServer.prompt()
    → run_agent.py: AIAgent.run_conversation()
    → LLM loop (tool calls → execute → response)
    → Plugin hooks write progress to SQLite (olympus_v3.db)
    → acp_manager.poll() reads SQLite with enriched data
    → Returns result dict with session_id (session stays open)
```

**Key distinction:** Aether Agents uses Olympus MCP v3 with ACP (Agent Client
Protocol), NOT `delegate_task` from hermes-agent. The `delegate_tool.py`
blocked-tools list is irrelevant for Olympus-spawned Daimons — they are
full hermes-agent processes with their own config.yaml, SOUL.md, tools,
and plugin hooks. The `DELEGATE_BLOCKED_TOOLS` list only applies to
`delegate_task` subagents within a single hermes-agent process.

## Key Code Paths

### Agent Completion Detection

The agent loop in `run_event.py` decides it's done when the LLM response
has **no tool calls** — this is the "final response" branch:

```python
# run_agent.py ~line 14991
else:
    # No tool calls - this is the final response
    final_response = assistant_message.content or ""
```

The `turn_exit_reason` field tracks why the loop ended:
- `"text_response(finish_reason=stop)"` — normal completion
- `"max_iterations_reached(N/M)"` — budget exhausted
- `"interrupted_by_user"` — user sent new message
- `"budget_exhausted"` — iteration budget consumed

### ACP Server → PromptResponse

In `acp_adapter/server.py`, the `prompt()` method calls `run_conversation()`
and always returns:

```python
# acp_adapter/server.py ~line 1349
stop_reason = "cancelled" if state.cancel_event and state.cancel_event.is_set() else "end_turn"
return PromptResponse(stop_reason=stop_reason, usage=usage)
```

The `stop_reason` is either `"end_turn"` (normal) or `"cancelled"` (interrupted).
There is no `"clarification_needed"` status — all completions are `"end_turn"`.

### Olympus Poll → SQLite (Enriched)

`acp_manager.poll()` reads SQLite (not ACP streaming) for progress.
Since the bidirectional-comm feature (May 2026), poll returns enriched data:

```python
# db.py: get_session_progress() — enriched return dict
{
    "thoughts": 3,                    # count of assistant turns
    "messages": 2,                    # count of turns with content
    "tool_calls": 10,                 # count of tool calls
    "status": "completed",            # session status
    "last_turn": "7 findings...",     # latest assistant content (NOT null)
    "last_reasoning": "I analyzed...", # latest reasoning
    "recent_tool_calls": [             # NEW: last 5 tool calls
        {"tool_name": "terminal", "args_truncated": "ls -la /home/...", "status": "completed", "timestamp": ...},
        {"tool_name": "read_file", "args_truncated": "db.py", "status": "completed", "timestamp": ...},
    ],
    "clarification_needed": False,    # NEW: regex on last_turn
    "heartbeat_timestamp": 1716097210.0  # NEW: timestamp of last turn
}
```

### Delegate Auto-Poll Loop

```python
# acp_manager.py:delegate()
while True:
    await asyncio.sleep(poll_interval)
    progress = await self.poll(session_id)

    if status in ("completed", "error", "cancelled"):
        # Detect CLARIFICATION NEEDED pattern in last_turn
        if status == "completed" and re.search(r"CLARIFICATION\s+NEEDED", last_turn, re.IGNORECASE):
            progress["status"] = "clarification_needed"
            progress["clarification_needed"] = True
            progress["session_id"] = session_id
            return progress  # session stays OPEN for follow-up

        progress["session_id"] = session_id
        return progress  # session stays OPEN, Hermes can message() again

    if elapsed >= timeout:
        progress["session_id"] = session_id
        return progress  # timed out (session auto-closed for safety)
```

**Key change:** `delegate()` no longer closes the session on normal
completion. Only closes on error, timeout, or stall. Hermes can continue
the conversation with `message()` in the same session.

## Bidirectional Communication (Implemented May 2026)

### The Problem

Three gaps prevented bidirectional communication between orchestrator and
Daimon:

1. **`poll()` returned only counts** — `tool_calls: 10` with no tool names,
   arguments, or content. Orchestrator LLM sees "10" and assumes stuck.
2. **No way to send mid-execution directives** — Hermes could not steer a
   running Daimon. The steering table existed but wasn't exposed via MCP.
3. **`delegate()` destroyed sessions on completion** — one fire-and-forget
   exchange, then the session was gone. No follow-up possible.

The tmux analogy: the old behavior was `some_command &` (background a
process, only `wait` or `kill`). The new behavior is tmux — a persistent
session you can observe, speak to, and disconnect from.

### The Solution: Enriched Poll + Steer + Persistent Sessions

**Implemented on branch `feature/bidirectional-comm` (commits 767c12f,
710b3fa, e5bc81f). Three changes, all in `src/olympus_v3/`, no hermes-agent
upstream changes needed.**

#### Change 1: Enriched `get_session_progress()` (db.py)

Added three new fields to the poll return dict:

- `recent_tool_calls`: Last 5 tool calls with `tool_name`,
  `args_truncated` (200 chars), `status`, `timestamp`. Query:
  `SELECT tool_name, arguments, status, timestamp FROM tool_calls
  WHERE session_id = ? ORDER BY timestamp DESC LIMIT 5`
- `clarification_needed`: Boolean. `re.search(r"CLARIFICATION\s+NEEDED",
  last_turn, re.IGNORECASE)` on the content of `last_turn`.
- `heartbeat_timestamp`: `SELECT MAX(timestamp) FROM turns WHERE session_id = ?`

Both `OlympusDB` (async) and `OlympusDBSync` (sync) were updated.

#### Change 2: `steer` action + session persistence (server.py)

New `steer` action on `talk_to` MCP tool:

```python
talk_to(action="steer", session_id="...", directive="Focus on security", priority=5)
# → writes to steering table, Daimon's pre_llm_call hook reads it on next turn
```

No Daimon-side changes needed — the `pre_llm_call` hook already consumes
the `steering` table via `consume_steering()`.

`delegate()` now returns `session_id` in the result and does NOT
auto-close on completion. Only auto-closes on error, timeout, or stall.
Hermes can call `message()` on the same session for follow-up, then
`close()` explicitly.

#### Change 3: Clarification detection (acp_manager.py + server.py)

In the `delegate()` completion block, after detecting `status: "completed"`:
1. Check `last_turn` for `"CLARIFICATION NEEDED"` pattern (regex)
2. If found: return with `status: "clarification_needed"`,
   `clarification_needed: True`, session stays open
3. If not found: return with `status: "completed"`, session stays open
4. `session_id` always included in the return dict

### The tmux Analogy

The desired behavior is like tmux panes for agents:

```
Hermes → open(athena)                    → session_id
Hermes → poll(session_id)                → {recent_tool_calls: [{name: "terminal"}...]}
Hermes → poll(session_id)                → {status: "completed", last_turn: "7 findings..."}
Hermes → message(session_id, "Deepen #2")  ← CONVERSATION CONTINUES
Hermes → poll(session_id)                → {status: "completed", last_turn: "Finding #2: ..."}
Hermes → close(session_id)
```

### What Does NOT Change

- **No changes to hermes-agent upstream** — all changes in `src/olympus_v3/`
- **No changes to Daimon SOUL.md** — steering hook already works
- **No changes to ACP protocol** — sessions already persistent
- **No new MCP tools** — `steer` is a new action on existing `talk_to`
- **No filesystem files** — pure SQLite + MCP
- **No new database tables** — `turns`, `tool_calls`, `steering` suffice

### Integration Points (for future modifications)

| Location | File | What |
|----------|------|------|
| No-tool-calls branch | `run_agent.py` ~14991 | Where `final_response` is set |
| `PromptResponse` | `acp_adapter/server.py` ~1349 | Where `stop_reason` is set |
| Plugin `on_session_start` | `olympus_v3_hooks/hooks.py` | Creates session row in olympus_v3.db BEFORE turns are written |
| Plugin `post_llm_call` | `olympus_v3_hooks/hooks.py` | Writes turns + reasoning to SQLite |
| Plugin `post_tool_call` | `olympus_v3_hooks/hooks.py` | Writes tool names + args to SQLite |
| Plugin `on_session_end` | `olympus_v3_hooks/hooks.py` | Marks session as completed |
| `get_session_progress()` | `db.py` | Returns enriched poll data |
| `OlympusDBSync.insert_session()` | `db.py` | Sync session creation (for on_session_start hook) |

## olympus_v3 Plugin Hooks (Updated June 2026)

The `olympus_v3` plugin has 5 hooks registered in the hermes-agent lifecycle:

1. **`on_session_start`** — Creates session row in `olympus_v3.db.sessions` via `OlympusDBSync.insert_session()`. This ensures the FK parent row exists BEFORE `post_llm_call` or `post_tool_call` try to write to `turns` or `tool_calls`. Added June 2026 to fix the FK constraint bug.

2. **`post_llm_call`** — Writes turn content + reasoning to `olympus_v3.db.turns`. FK reference to `sessions(session_id)`.

3. **`post_tool_call`** — Writes tool name + args to `olympus_v3.db.tool_calls`. FK reference to `sessions(session_id)`.

4. **`on_session_end`** — Marks session as `completed` in `olympus_v3.db.sessions`.

5. **`pre_llm_call`** — Consumes steering directives from the `steering` table.

### Why `on_session_start` Was Needed (FK Constraint Bug)

The `acp_manager` (async, aiosqlite) calls `insert_session()` to create the session row, but this write is not guaranteed to be visible to the sync `sqlite3` connection used by the hooks. Without a sync `on_session_start` hook in the Daimon process, the `sessions` table was empty when `post_llm_call` tried to `INSERT INTO turns(session_id, ...)` — causing a `FOREIGN KEY constraint failed` error that was caught and silently logged as a WARNING.

The fix: `on_session_start` fires at session start in the Daimon process, creating the session row via `OlympusDBSync.insert_session()` (sync sqlite3), with `PRAGMA wal_checkpoint = TRUNCATE` in `ensure_tables()` to force WAL checkpoint visibility for async→sync reads.

**Key files modified:**
- `src/olympus_v3/olympus_v3_hooks/hooks.py` — Added `on_session_start()` function + `ctx.register_hook("on_session_start", on_session_start)` in `register()`
- `src/olympus_v3/db.py` — Added `OlympusDBSync.insert_session()` method + `PRAGMA wal_checkpoint = TRUNCATE` in `OlympusDBSync.ensure_tables()`

**Important:** The `aether` plugin also has an `on_session_start` hook, but it writes to `aether.db` (not `olympus_v3.db`). Both hooks fire for each session, each writing to its own database. The olympus_v3 hook is necessary because its `turns` and `tool_calls` tables have FK constraints referencing `olympus_v3.db.sessions(session_id)`.

## ACP Session Lifecycle

```
spawn_agent(name) → AgentState(status="spawning" → "idle")
  ↓
new_session(cwd) → acp_session_id
  ↓
send_message(session_id, prompt) → async task, returns immediately
  ↓  (Daimon runs: run_conversation → tool calls → final response)
  ↓
  ↓ on_session_start → INSERT INTO sessions (olympus_v3.db)
  ↓ post_llm_call   → INSERT INTO turns (olympus_v3.db)
  ↓ post_tool_call   → INSERT INTO tool_calls (olympus_v3.db)
  ↓
poll(session_id) → {thoughts, messages, tool_calls, status, last_turn,
                     last_reasoning, recent_tool_calls, clarification_needed,
                     heartbeat_timestamp}
  ↓
message(session_id, followup) → sends another prompt to SAME session  ← BIDIRECTIONAL
  ↓
poll(session_id) → enriched progress with cumulative context
  ↓
steer(session_id, directive) → writes to steering table                ← UPSTREAM
  ↓                                                              (consumed on next turn)
close(session_id) or cancel(session_id) → AgentState(status="idle" or "dead")
```

Sessions are reusable: `delegate()` now returns `session_id` and keeps
the session open. Hermes can send `message()` for follow-up, then `close()`
explicitly when done.

## `last_turn: null` Gap — Two Root Causes (Updated June 2026)

### Cause A (FIXED): FK Constraint — `sessions` table empty before `turns` INSERT

**Symptom:** `delegate()` returns `last_turn: null`, `tool_calls: 0`, `messages: 0`. The `olympus_v3.db` shows 0 rows in both `sessions` and `turns` tables. Agent log shows `stop_reason=end_turn` (the Daimon completed normally).

**Root cause:** The `olympus_v3_hooks` plugin registered hooks for `post_llm_call`, `post_tool_call`, `on_session_end`, and `pre_llm_call` — but NOT `on_session_start`. The `aether_hooks` plugin's `on_session_start` writes to `aether.db`, not `olympus_v3.db`. The `acp_manager`'s async `insert_session()` was not visible to the sync `sqlite3` connection used by the hooks (WAL race condition). Result: `INSERT INTO turns(session_id, ...)` failed with `FOREIGN KEY constraint failed`, silently caught by try/except, all turn data lost.

**Fix (applied June 2026):** Added `on_session_start` hook to `olympus_v3_hooks` that creates the session row sync in `olympus_v3.db`. Also added `OlympusDBSync.insert_session()` method and `PRAGMA wal_checkpoint = TRUNCATE` in `ensure_tables()`.

**Verification:**
```bash
# After fix, delegate a test task and check DB
sqlite3 ~/Aether-Agents/home/.olympus/olympus_v3.db \
  "SELECT session_id, agent, status FROM sessions; SELECT turn_num, role, substr(content,1,80) FROM turns;"
# Should show: 1 session (completed), 1+ turns with content
```

### Cause B (ONGOING): Protocol mismatch in `delegate()` response retrieval

**Symptom:** Even with Cause A fixed (DB now has sessions and turns), `delegate()` still returns `last_turn: null` via the MCP layer. Verified by calling `OlympusDB.get_session_progress()` directly — it returns full data including `last_turn` content.

**Root cause:** The MCP server's `delegate` handler reads the ACP response but doesn't propagate the `last_turn` field correctly. This is a protocol mismatch between hermes-agent v0.15.2's ACP and olympus_v3's response format. Investigation ongoing.

**Diagnosis:**
```python
# Direct DB query works (full data):
from olympus_v3.db import OlympusDB, get_db_path
db = OlympusDB(db_path=get_db_path())
await db.connect()
progress = await db.get_session_progress(session_id)
# → last_turn has content, tool_calls populated

# But delegate() via MCP returns null:
talk_to(action="delegate", agent="hefesto", prompt="...")
# → last_turn: null, tool_calls: 0
```

## TUI Visibility Gap (Resolved May 2026)

When hermes-agent runs directly (CLI/TUI), the user sees in real time:
- **Reasoning panel** — the LLM's chain-of-thought before each response
- **Tool calls** — name, arguments, duration (e.g., `💻 $ date '+%Y-%m-%d %H:%M:%S %Z' 0.4s`)
- **Progress bar** — tokens consumed/context, percentage, elapsed time
- **Streaming response** — text appears incrementally

The gap between TUI and ACP delegation has been **partially resolved**:

| Data | TUI shows | poll() returns (old) | poll() returns (new) | Status |
|------|-----------|----------------------|----------------------|--------|
| LLM reasoning | ✅ Full panel | ❌ Not returned | ✅ `last_reasoning` | ✅ Works (FK fixed) |
| Response text | ✅ Streaming | ❌ Only on close() | ✅ `last_turn` | ✅ Works via DB, ❌ Via MCP delegate |
| Tool names | ✅ With args+duration | ❌ Only count | ✅ `recent_tool_calls[].tool_name` | ✅ Works |
| Tool arguments | ✅ Visible | ❌ Not returned | ✅ `recent_tool_calls[].args_truncated` (200 chars) | ✅ Works |
| Session status | ✅ Always | ✅ Returned | ✅ Returned | ✅ Works |
| Timestamp | ✅ Duration | ❌ Not returned | ✅ `heartbeat_timestamp` | ✅ Works (FK fixed) |
| Clarification | ✅ Full response | ❌ Not detected | ✅ `clarification_needed` | ✅ Works (FK fixed) |
| Steering | ✅ Via /steer command | ❌ Not available | ✅ `steer` action on talk_to | ✅ Works |

## Empirical Verification (May-June 2026)

### Test 1: Multi-turn ACP context persistence ✅

**Agent:** Etalides (session `fe61b9eb`)
**Method:** `open` → `message("Turno 1")` → `poll` → `message("Turno 2: remember Turno 1?")` → `poll`
**Result:** Etalides correctly recalled Turno 1 details across messages in the same ACP session.

### Test 2: CLARIFICATION NEEDED detection ✅

**Agent:** Athena (session `158b6302`)
**Method:** `open` → `message("Necesito que audites un proyecto.")` (deliberately ambiguous) → `poll` (3x)
**Result:** Athena returned the SOUL.md clarification pattern in `last_turn`.

### Test 3: Enriched poll + session persistence ✅

**Agent:** Etalides (session `3a008882`)
**Result:** `recent_tool_calls` populated, `last_turn` with content, session persistence works.

### Test 4: FK constraint fix verification ✅ (June 2026)

**Agent:** Hefesto (session `f5a8d208`)
**Method:** `delegate(hefesto, "Respond: Fix verificado")` after adding `on_session_start` hook
**Result:**
- `olympus_v3.db` shows: 1 session (`completed`), 1 turn (`assistant`, content: "Fix verificado — olympus_v3 on_session_start hook activo")
- `get_session_progress()` returns full data with `last_turn` populated
- Agent log confirms: `olympus_v3.hooks: on_session_start: session f5a8d208... created for agent`
- FK constraint error is resolved

### Test 5: Protocol mismatch still present (June 2026)

**Method:** `delegate()` returns `last_turn: null, tool_calls: 0, thoughts: 0, messages: 0` even though DB has full data
**Diagnosis:** DB layer works, MCP response handler doesn't propagate `last_turn`
**Status:** Open investigation

## Pitfalls

### SQLite race condition on second message

After sending a second `message()` to a completed session, `poll()` may show stale data (same counters) for 5-10 seconds before SQLite catches up. **Workaround:** Wait 5-10 seconds after `message()` before the first `poll()`, or poll multiple times looking for counter changes.

### `delegate()` in `server.py` vs `acp_manager.py`

Both files have a `delegate()` function with overlapping stall/timeout logic. Changes to clarification detection or session persistence must be applied to **both** locations.

### Same agent, same project_root → session reuse

`spawn_agent()` reuses an existing agent process if it's idle for the same `(agent_name, project_root)` key. To run the same agent in parallel, use different `project_root` values or ensure the first session is closed before spawning the second.

### Daimon processes persist after session close

ACP agent processes (`hermes acp --profile <name>`) are not killed when the session closes. They remain idle, waiting for the next prompt. To fully stop a Daimon process, kill it with `pkill -f "hermes acp --profile <name>"` or let the ACP manager reuse it.