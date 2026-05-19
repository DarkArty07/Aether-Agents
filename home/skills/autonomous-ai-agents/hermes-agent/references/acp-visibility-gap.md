# ACP Visibility Gap — TUI vs Poll Comparison

## Problem Statement

When hermes-agent runs directly (TUI), the user sees real-time:
- **Reasoning panel** — LLM chain-of-thought before each response
- **Tool calls** — name, arguments, duration (e.g., `💻 $ date ... 0.4s`)
- **Progress bar** — tokens consumed/context, percentage, elapsed time
- **Streaming response** — text appears incrementally

When a Daimon runs via ACP delegation, Hermes (orchestrator) sees:
```
poll → {thoughts: 0, messages: 0, tool_calls: 10, status: "active", last_turn: null}
```

A counter. No reasoning, no tool names, no progress, no "reading files (3/8)...".

## The Data Is Already in SQLite

The gap is **delivery**, not **collection**. Daimon hooks already write to SQLite:

| Data | Table | Column | TUI shows | poll() returns |
|------|-------|--------|-----------|----------------|
| LLM reasoning | turns | reasoning | ✅ Full panel | ❌ Not returned |
| Response text | turns | content | ✅ Streaming | ❌ Only last_turn |
| Tool names | tool_calls | tool_name | ✅ With args | ❌ Only count |
| Tool arguments | tool_calls | arguments | ✅ Visible | ❌ Not returned |
| Tool results | tool_calls | result | ✅ Visible | ❌ Not returned |
| Session status | sessions | status | ✅ Visible | ✅ Returned |
| Timestamp | turns/tool_calls | timestamp | ✅ Duration | ❌ Not returned |

`get_session_progress()` only returns counts + last turn. The rich data exists — poll just doesn't fetch it.

## Priority: Visibility Before Clarification

Chris's directive (May 2026): **visibility/progress FIRST, clarification SECOND.**

Quote: "Los LLM son muy desesperados" — LLMs are impatient. When an orchestrator LLM sees
`tool_calls: 10` with no context about what those tools are doing, it assumes the agent is
stuck and either times out, re-sends the prompt, or cancels.

The tmux analogy: what Chris wants is like tmux panes for agents. Each Daimon should be
observable — seeing what it's doing — without having to kill the process to interact with it.

## Implementation: Enrich get_session_progress()

Add to `db.py` `get_session_progress()` return dict:

```python
"recent_tool_calls": [
    {"tool_name": "read_file", "status": "completed", "timestamp": ...},
    {"tool_name": "terminal", "status": "completed", "timestamp": ...},
    # Last 5-10 entries from tool_calls table
],
"clarification_needed": bool,  # regex /CLARIFICATION\s+NEEDED:/i on last_turn
"heartbeat_timestamp": float,   # timestamp of most recent turn
```

This requires ~10 lines in db.py — a new query joining tool_calls for the last N entries.

## Production Evidence

Delegated a security audit to Athena (May 2026):
- **Attempt 1** (delegate, timeout=300s): timed out after 5 minutes, 11 tool_calls, no response
- **Attempt 2** (delegate, timeout=600s): timed out after 10 minutes
- **Attempt 3** (manual: open→message→poll×5): polls showed `tool_calls: 10` unchanged
  for 2+ minutes. Response only available after `close()`

Key observations:
1. Poll returns counters, not content
2. No progress visibility between tool calls
3. Result only on close() — poll() doesn't deliver final content
4. Without visibility, the LLM orchestrator wastes time on repeated polls