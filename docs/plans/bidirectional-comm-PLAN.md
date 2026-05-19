# Bidirectional Communication — Implementation Plan

**Branch:** `feature/bidirectional-comm` (from `dev`)
**Date:** 2026-05-19
**Status:** Analysis complete, implementation pending

## Problem Statement

When Hermes delegates to a Daimon via ACP, the orchestrator is blind:

1. **No visibility of progress** — `poll()` returns `{thoughts: 0, messages: 0, tool_calls: 10}` without content
2. **No final message until close** — `last_turn: null` during execution, response only accessible after `close()`
3. **No bidirectional communication** — Once the prompt is sent, Hermes cannot steer, clarify, or continue the conversation
4. **Session is destroyed on completion** — `delegate()` closes the session, requiring a new spawn for follow-ups

The TUI (`hermes` CLI) shows all this in real time. The ACP pipeline has all the data in SQLite but only delivers counts.

## Vision: tmux-like Sessions

A Daimon session should behave like a tmux pane:

```
Hermes → open(athena)                     → session_id
Hermes → poll(session_id)                 → {status: "active", recent: [{tool: "terminal", args: "ls -la"}]}
Hermes → poll(session_id)                 → {status: "working", recent: [{tool: "terminal", args: "stat .env"}]}
Hermes → poll(session_id)                 → {status: "completed", response: "7 findings..."}
Hermes → message(session_id, "Deepen #2")  ← CONVERSATION CONTINUES
Hermes → poll(session_id)                 → {status: "completed", response: "Finding #2: ..."}
Hermes → close(session_id)
```

## What Already Exists (No Changes Needed)

| Component | What it does | Where |
|-----------|-------------|-------|
| `turns` table | Stores full content + reasoning per turn | `db.py` → `insert_turn()` |
| `tool_calls` table | Stores tool name, args, result per call | `db.py` → `insert_tool_call()` |
| `steering` table | Stores directives, consumed by `pre_llm_call` hook | `db.py` → `insert_steering()` / `consume_steering()` |
| `on_post_llm_call` hook | Writes every turn to SQLite after each LLM call | `olympus_v3_hooks/hooks.py` |
| `on_post_tool_call` hook | Writes every tool call to SQLite | `olympus_v3_hooks/hooks.py` |
| `send_message()` | Supports sending multiple prompts to same session | `acp_manager.py` |
| ACP sessions | Are already persistent and reusable | `acp_manager.py` |

**Key insight:** The data is already in SQLite. The gap is in *delivery* — `get_session_progress()` only returns counts.

## Changes Required

### Change 1: Enrich `get_session_progress()` in `db.py`

**File:** `src/olympus_v3/db.py`
**Lines:** ~630-670 (async `get_session_progress`)

**Current output:**
```python
{
    "thoughts": 3,       # count only
    "messages": 2,        # count only
    "tool_calls": 10,     # count only
    "status": "active",
    "last_turn": None,    # often None during execution
    "last_reasoning": None
}
```

**New output:**
```python
{
    "thoughts": 3,
    "messages": 2,
    "tool_calls": 10,
    "status": "completed",           # NOW reflects actual status
    "last_turn": "7 findings...",     # NOW available as soon as written
    "last_reasoning": "I analyzed...",
    "recent_tool_calls": [            # NEW: last 5 tool calls
        {"tool_name": "terminal", "args_truncated": "ls -la /home/...", "status": "completed", "timestamp": 1716097200.0},
        {"tool_name": "read_file", "args_truncated": "db.py", "status": "completed", "timestamp": 1716097205.0},
    ],
    "clarification_needed": False,    # NEW: regex on last_turn
    "heartbeat_timestamp": 1716097210.0   # NEW: timestamp of last turn
}
```

**Implementation details:**
- `recent_tool_calls`: `SELECT tool_name, arguments, status, timestamp FROM tool_calls WHERE session_id = ? ORDER BY timestamp DESC LIMIT 5` — truncate `arguments` to 200 chars
- `clarification_needed`: regex `r"CLARIFICATION\s+NEEDED"` on `last_turn` content
- `heartbeat_timestamp`: `SELECT MAX(timestamp) FROM turns WHERE session_id = ?`
- Both `OlympusDB` (async) and `OlympusDBSync` need the update

**Estimated lines:** ~40 added to `db.py`

### Change 2: `steer` action in `server.py` + session persistence in `delegate()`

**File:** `src/olympus_v3/server.py`

**2a. New `steer` action in `talk_to` inputSchema:**

New action "steer" with fields:
- `session_id` (required, string)
- `directive` (required, string)
- `priority` (optional, integer, default 0)

Handler writes to steering table via `db.insert_steering()`. The Daimon's `pre_llm_call` hook ALREADY reads it. No Daimon code changes needed.

**2b. `delegate()` does NOT close session on completion:**

- On `status == "completed"`, check `last_turn` for "CLARIFICATION NEEDED"
  - If found → return with `status: "clarification_needed"`, session stays open
  - If not → return with `status: "completed"`, session stays open
- Return `session_id` so Hermes can `message()` or `close()`
- Only auto-close on timeout/stall (safety)

**Estimated lines:** ~50 in `server.py`

### Change 3: Clarification detection in `acp_manager.py`

**File:** `src/olympus_v3/acp_manager.py`

In `delegate()` method, after completion check: detect "CLARIFICATION NEEDED" regex in `last_turn`, set `status: "clarification_needed"` if found, keep session open. Normal completion also keeps session open.

**Estimated lines:** ~20 in `acp_manager.py`

## What Does NOT Change

- **No changes to hermes-agent upstream** — all changes in `src/olympus_v3/`
- **No changes to Daimon SOUL.md** — steering hook already works
- **No changes to ACP protocol** — sessions already persistent
- **No new MCP tools** — `steer` is a new action on existing `talk_to`
- **No filesystem files** — pure SQLite + MCP
- **No new database tables** — `turns`, `tool_calls`, `steering` suffice

## Phased Rollout

| Phase | Changes | Risk | Reversible |
|-------|---------|------|------------|
| **1** | Enrich `get_session_progress()` | Low — additive | `git revert` |
| **2** | Add `steer` action | Low — new action | `git revert` |
| **3** | `delegate()` don't close + clarification | Medium — lifecycle change | Revert phase 3 only |

## Success Criteria

1. `poll()` returns `recent_tool_calls` with tool names and truncated args
2. `poll()` returns `last_turn` with content when Daimon completes a turn
3. `delegate()` returns `session_id` and does NOT close the session on normal completion
4. `steer` action writes directives consumed by Daimon `pre_llm_call` hook
5. "CLARIFICATION NEEDED" pattern surfaced as `status: "clarification_needed"`
6. Hermes can `message()` a completed session for follow-up
7. Existing `close()` and `cancel()` still work

## Rollback

```bash
git checkout dev
git branch -D feature/bidirectional-comm
```

All changes in `src/olympus_v3/` only. No data migration. No schema changes.