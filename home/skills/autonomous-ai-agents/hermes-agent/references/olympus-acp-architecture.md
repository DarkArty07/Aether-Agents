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
| Plugin `pre_llm_call` | `olympus_v3_hooks/hooks.py` | Consumes steering directives |
| Plugin `post_llm_call` | `olympus_v3_hooks/hooks.py` | Writes turns + reasoning to SQLite |
| Plugin `post_tool_call` | `olympus_v3_hooks/hooks.py` | Writes tool names + args to SQLite |
| `get_session_progress()` | `db.py` | Returns enriched poll data |

### ⚠ Historical: Previous failed approach (commit 62e59c8, reverted)

A previous implementation added a `clarify` action to `talk_to` and a
`continue_session()` method in `acp_manager`. This was rejected — the
correct approach reuses existing `message`/`poll` actions in the same
ACP session. No new inputSchema fields, no new enums, no new methods.

### Future: Native `ask_orchestrator` tool (upstream change)

For true mid-execution dialogue (Daimon pauses to ask Hermes a question),
a new tool in hermes-agent core would be needed:
- New tool `tools/ask_orchestrator.py` exempt from `DELEGATE_BLOCKED_TOOLS`
- `delegate_tool.py` intercepts the tool call, pauses the child, sends
  the question to the parent, receives answer, injects as `tool_result`
- This requires an upstream change to hermes-agent, not just Aether

## ACP Session Lifecycle

```
spawn_agent(name) → AgentState(status="spawning" → "idle")
  ↓
new_session(cwd) → acp_session_id
  ↓
send_message(session_id, prompt) → async task, returns immediately
  ↓  (Daimon runs: run_conversation → tool calls → final response)
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

## TUI Visibility Gap (Resolved May 2026)

When hermes-agent runs directly (CLI/TUI), the user sees in real time:
- **Reasoning panel** — the LLM's chain-of-thought before each response
- **Tool calls** — name, arguments, duration (e.g., `💻 $ date '+%Y-%m-%d %H:%M:%S %Z' 0.4s`)
- **Progress bar** — tokens consumed/context, percentage, elapsed time
- **Streaming response** — text appears incrementally

The gap between TUI and ACP delegation has been **partially resolved**:

| Data | TUI shows | poll() returns (old) | poll() returns (new) | Status |
|------|-----------|----------------------|----------------------|--------|
| LLM reasoning | ✅ Full panel | ❌ Not returned | ✅ `last_reasoning` | ⚠ NULL — turns table empty |
| Response text | ✅ Streaming | ❌ Only on close() | ✅ `last_turn` | ⚠ NULL — turns table empty |
| Tool names | ✅ With args+duration | ❌ Only count | ✅ `recent_tool_calls[].tool_name` | ✅ Works |
| Tool arguments | ✅ Visible | ❌ Not returned | ✅ `recent_tool_calls[].args_truncated` (200 chars) | ✅ Works |
| Session status | ✅ Always | ✅ Returned | ✅ Returned | ✅ Works |
| Timestamp | ✅ Duration | ❌ Not returned | ✅ `heartbeat_timestamp` | ⚠ NULL — depends on turns |
| Clarification | ✅ Full response | ❌ Not detected | ✅ `clarification_needed` | ⚠ Depends on `last_turn` being populated |
| Steering | ✅ Via /steer command | ❌ Not available | ✅ `steer` action on talk_to | ✅ Works (writes to steering table) |

### ⚠ Confirmed Gap: `last_turn: null` after agent completion (May 2026)

Enriched `recent_tool_calls` works — tool names, truncated args, status, and
timestamps are correctly written to `tool_calls` table. But **`last_turn`
remains null** even when the agent completes with 23 tool calls and
`status: "completed"`. The `turns` table in `olympus_v3.db` has **0 rows**
for the session. The `post_tool_call` hook writes to `tool_calls`, but the
`post_llm_call` hook does NOT write the agent's text response to `turns`.

This means `get_session_progress()` reads from `turns` for `last_turn` and
`last_reasoning`, and since `turns` is empty, both fields are always null.

**Test evidence (session `d5d5342e`):**
- 23 tool calls registered in `tool_calls` table ✅
- 0 rows in `turns` table ❌
- `status: "completed"` ✅
- `last_turn: null` ❌
- `last_reasoning: null` ❌
- `response: null` on `close()` ❌

**Root cause (hypothesis):** The `post_llm_call` hook in
`olympus_v3_hooks/hooks.py` fires inside the hermes-agent subprocess (the
Daimon), and may be writing to a different SQLite path, or the hook is not
firing for ACP sessions, or the turn content is being written but to a
different database than `home/.olympus/olympus_v3.db` that
`get_session_progress()` reads from.

**Next step:** Verify which database (if any) the `post_llm_call` hook
writes to during an ACP session, and whether the hook fires at all for
ACP-spawned agents.

### Remaining gaps (future work)

- **Streaming** — poll is still interval-based, not real-time push
- **Reasoning during execution** — `last_reasoning` is only updated on
  turn completion, not during thinking
- **Progress percentage** — no `step 3/8` equivalent yet
- **Tool call results** — `recent_tool_calls` shows args but not result
  (too large to include in poll)

### Priority: Visibility Before Clarification

Chris's directive (May 2026): **visibility/progress FIRST, clarification SECOND.**

Quote: "Los LLM son muy desesperados" — when an orchestrator LLM sees
`tool_calls: 10` with no context, it assumes the agent is stuck and either
times out, re-sends the prompt, or cancels. Progress signals prevent this.

The tmux analogy: what Chris wants is like tmux panes for agents.
Each Daimon should be observable — seeing what it's doing — without
having to kill the process to interact with it.

### Priority: The End Turn Is What Matters Most

Chris's directive (May 2026): **the agent's final message is the most
important output**, more important than intermediate reasoning, tool calls,
or token counts. The TUI shows this naturally (the response appears in
full). The old ACP delegation hid it until `close()`. The new enriched
poll delivers `last_turn` as soon as the agent completes a turn.

When evaluating delegation success, focus on:
1. Is `last_turn` populated with the agent's response? (not null)
2. Does `status` accurately reflect the session state?
3. Can you continue the conversation with `message()`?

Do NOT focus on:
- Token counts or progress bars (the LLM's "desperation" signal)
- Reasoning content (interesting but not the deliverable)
- Individual tool call details (the journey, not the destination)

## Empirical Verification (May 2026)

### Test 1: Multi-turn ACP context persistence ✅

**Agent:** Etalides (session `fe61b9eb`)
**Method:** `open` → `message("Turno 1")` → `poll` → `message("Turno 2: remember Turno 1?")` → `poll`
**Result:** Etalides correctly recalled Turno 1 details across messages in the same ACP session.
- Progress counters: thoughts:2, messages:2 — context persisted.
- **Conclusion:** ACP sessions maintain conversation history across multiple `message()` calls.

### Test 2: CLARIFICATION NEEDED detection ✅

**Agent:** Athena (session `158b6302`)
**Method:** `open` → `message("Necesito que audites un proyecto.")` (deliberately ambiguous) → `poll` (3x)
**Result:** Athena returned the SOUL.md clarification pattern in `last_turn`.
- **Conclusion:** Daimons follow their SOUL.md clarification protocol via ACP.
  The "CLARIFICATION NEEDED" pattern is detectable in `last_turn` for routing.

### Test 3: Enriched poll + session persistence ✅ (bidirectional-comm branch)

**Agent:** Etalides (session `3a008882`)
**Method:** `open` → `message("List files in src/olympus_v3/")` → `poll` (active) → `poll` (completed)
  → `message("Now tell me about db.py specifically")` → `poll` (completed)
  → `close()`
**Result:**
- Poll during active work showed `recent_tool_calls` with tool names and truncated args
- Poll after completion showed `last_turn` with full response content
- Second `message()` on same session worked — Etalides remembered the conversation
- `clarification_needed: false`, `heartbeat_timestamp` updated correctly
- **Conclusion:** Bidirectional communication works. Session persistence works.
  The orchestrator can now observe progress and continue conversations.

### Test 4: Production timeout experience (before bidirectional-comm)

**Agent:** Athena (security audit)
- **Attempt 1** (delegate, timeout=300s): timed out. 11 tool_calls, no response visible.
- **Attempt 2** (delegate, timeout=600s): MCP call timed out.
- **Attempt 3** (manual: open → message → poll × 5): polls showed `tool_calls: 10`
  with no content change for 2+ minutes. Response only available after `close()`.
- **Root cause:** poll() returned counts only, last_turn was null during execution,
  delegate() closed the session on completion.
- **All three issues resolved by bidirectional-comm branch.**

### Test 5: Parallel orchestration ✅ (bidirectional-comm branch)

**Agents:** Hefesto + Etalides (two concurrent sessions)
**Method:** `open(hefesto)` + `open(etalides)` → `message(hefesto, "count lines")` + `message(etalides, "what Python version?")` → alternate `poll()` on both → `message(hefesto, "what % is DB code?")` while Etalides still working → `poll()` both → `close()` both
**Result:**
- Both sessions ran concurrently, each with independent context
- Hefesto completed first (5,544 lines), poll showed `status: "completed"` with `last_turn` content
- Sent follow-up message to Hefesto while Etalides was still active — Hefesto answered (39.4%) without any conflict
- Etalides completed separately with correct findings (Python >=3.11, SQLite)
- `recent_tool_calls` showed each agent's tool usage independently
- **Conclusion:** Multiple Daimon sessions can run in parallel. Hermes can
  alternate polls, continue conversations with completed agents while
  others are still working, and close sessions independently.

### Test 6: `last_turn: null` gap confirmed (May 2026)

**Agent:** Athena (security audit)
**Method:** `delegate(athena, timeout=300)` → timed out at 21 tool_calls → `message("send report")` → `poll` → `close()`
**Result:**
- `recent_tool_calls` populated correctly ✅ (saw search_files, read_file, terminal tool calls with arguments and timestamps)
- `tool_calls` table in `olympus_v3.db`: 23 entries ✅
- `turns` table in `olympus_v3.db`: **0 rows** ❌
- `last_turn: null` across all polls ❌
- `last_reasoning: null` ❌
- `response: null` on `close()` ❌
- `clarification_needed: false` (correct, no clarification pattern) ✅
- **Conclusion:** The enrichment of `recent_tool_calls` in `get_session_progress()`
  works correctly and delivers real-time visibility into what the agent is doing.
  However, the agent's **text response** (the final deliverable) is never
  persisted to the `turns` table. The `post_tool_call` hook writes to
  `tool_calls` but `post_llm_call` does NOT write to `turns` for ACP sessions.

### Pitfall: SQLite race condition on second message

After sending a second `message()` to a completed session, `poll()` may
show stale data (same counters) for 5-10 seconds before SQLite catches up.
**Workaround:** Wait 5-10 seconds after `message()` before the first `poll()`,
or poll multiple times looking for counter changes. The `close()` method
reads in-memory session state which is more current than SQLite.

### Pitfall: `delegate()` in `server.py` vs `acp_manager.py`

Both files have a `delegate()` function with overlapping stall/timeout
logic. Changes to clarification detection or session persistence must be
applied to **both** locations. The `acp_manager.py` version is used by
`talk_to(action="delegate")`, and the `server.py` version has its own
inline poll loop.

### Pitfall: Same agent, same project_root → session reuse

`spawn_agent()` reuses an existing agent process if it's idle for the same
`(agent_name, project_root)` key. If you open two sessions with the same
agent and project_root, the second `spawn_agent()` will return the existing
idle agent — not a new process. To run the same agent in parallel, use
different `project_root` values or ensure the first session is closed
before spawning the second.