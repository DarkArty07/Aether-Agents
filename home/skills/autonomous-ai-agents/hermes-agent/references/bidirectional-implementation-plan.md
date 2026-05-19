# Bidirectional Communication — Implementation Plan

Concrete implementation path for two capabilities missing from Olympus v3:
1. **Heartbeat/progress visibility** (Daimon → Hermes: "I'm working on step 3/8")
2. **Bidirectional communication** (Daimon ↔ Hermes: clarification, steering)

Priority order per user (Chris): visibility FIRST, then clarification.

## Code Analysis Summary (2026-05-19)

### Steering Table: Built but Unexposed

The `steering` table in `db.py` has full CRUD on both async and sync sides:

```python
# Async (server side — OlympusDB)
async def insert_steering(self, session_id, directive, priority=0) -> int
async def consume_steering(self, session_id) -> list[str]

# Sync (plugin hooks side — OlympusDBSync)
def insert_steering(self, session_id, directive, priority=0) -> int
def consume_steering(self, session_id) -> list[str]
```

The `pre_llm_call` hook in `olympus_v3_hooks/hooks.py` ALREADY consumes steering:

```python
def on_pre_llm_call(...) -> dict | str | None:
    directives = db.consume_steering(olympus_sid)
    if directives:
        return {"context": f"[Olympus Steering]\n{context}"}
```

**Gap**: No MCP action writes to the steering table. The `talk_to` inputSchema
in `server.py` has actions: open, message, poll, close, cancel, delegate.
No `steer` action exists.

### get_session_progress(): Counts Only

```python
# db.py — returns only aggregate counts, not detail
async def get_session_progress(self, session_id) -> dict:
    # thoughts (count), messages (count), tool_calls (count),
    # status, last_turn (text), last_reasoning (text)
```

**Missing for visibility**:
- `recent_tool_calls`: which tools were called (names + status), not just count
- `clarification_needed`: detect "CLARIFICATION NEEDED" pattern in `last_turn`
- `last_activity`: timestamp of most recent progress update

The data IS available — `get_tool_calls(session_id)` returns full records with
`tool_name`, `arguments`, `result`, `status`, `timestamp`.

### delegate() Closes on Completion (But Sessions Stay in Memory)

In `acp_manager.py`, `delegate()` returns progress on completion but does NOT
call `close()` — the session stays open. This means follow-up `message()` calls
theoretically work. However, the MCP handler in `server.py` also doesn't close.

**Implication**: The infrastructure for persistent sessions already exists.
The gap is in `delegate()` — it should detect "CLARIFICATION NEEDED" in
`last_turn` and return `status: "clarification_needed"` instead of completing.

### SQLite Race Condition (Verified)

When `poll()` reads from SQLite, the final turn may not be written yet because
`on_session_end` hook fires asynchronously. The `close()` method reads from
in-memory `self.sessions[session_id]` which is more current.

**Workaround for implementation**: When detecting clarification or progress,
check both SQLite AND in-memory session state. The `poll()` method in
`acp_manager.py` already merges:

```python
session = self.sessions.get(session_id)
if session and session.status in ("completed", "error", "cancelled"):
    progress["status"] = session.status
```

Extend this pattern to also check in-memory state for response content.

## Implementation: Option A — Steering + Enriched Poll

### Change 1: Add `steer` action to talk_to (server.py, ~30 lines)

Add to the `talk_to` inputSchema enum: `"steer"`
Add handler in `_handle_talk_to()`:

```python
elif action == "steer":
    session_id = args.get("session_id", "")
    directive = args.get("directive", "")
    priority = args.get("priority", 0)
    # Write to steering table
    await _db.insert_steering(session_id, directive, priority)
    return [mcp_types.TextContent(type="text", text=json.dumps({
        "status": "sent", "session_id": session_id, "directive": directive
    }))]
```

This gives Hermes a steering channel: mid-execution directives that get injected
into the Daimon's context on the next LLM call via `pre_llm_call` hook.

### Change 2: Enrich get_session_progress() (db.py, ~20 lines)

Extend `get_session_progress()` to include:

```python
# Recent tool calls (last 5, names + status only)
recent_tool_calls = await self.get_recent_tool_calls(session_id, limit=5)
# → [{"tool_name": "read_file", "status": "completed", "timestamp": ...}, ...]

# Clarification detection
clarification_needed = bool(
    re.search(r"CLARIFICATION\s+NEEDED:", latest["content"] or "")
) if latest else False

# Last activity timestamp (from most recent turn)
```

Also extend the sync `OlympusDBSync.get_session_progress()` with the same fields
so plugin hooks can read them too.

### Change 3: Detect clarification in delegate() (acp_manager.py, ~15 lines)

In the `delegate()` method's completion check, after detecting `status: "completed"`:

```python
# Check for clarification pattern before returning
last_turn = progress.get("last_turn", "") or ""
if re.search(r"CLARIFICATION\s+NEEDED:", last_turn, re.IGNORECASE):
    progress["status"] = "clarification_needed"
    # Do NOT close the session — keep it open for follow-up message
    return progress
```

Similarly in `server.py`'s delegate handler.

### Change 4: SOUL.md protocol (Hermes + all Daimons)

Hermes SOUL.md §5:
- When `delegate` returns `clarification_needed`, send `talk_to(action="message")`
  with clarification in the same session_id, then poll again
- When `poll` shows `recent_tool_calls`, use them for progress reporting to user
- Use `talk_to(action="steer")` to send mid-execution directives

Daimon SOUL.md (all):
- After every 3 tool calls, emit a progress line in the response:
  "Progress: [step description] ([N] tool calls completed)"
- When needing clarification, output "CLARIFICATION NEEDED:" followed by questions

## Files Changed

| File | Change | Lines |
|------|--------|-------|
| `src/olympus_v3/db.py` | Extend `get_session_progress()` | ~20 |
| `src/olympus_v3/server.py` | Add `steer` action to inputSchema + handler | ~30 |
| `src/olympus_v3/acp_manager.py` | Clarification detection in `delegate()` | ~15 |
| `src/olympus_v3/olympus_v3_hooks/hooks.py` | No changes needed | 0 |
| `home/SOUL.md` (Hermes) | Document clarification + steering protocol | ~30 |
| Daimon SOUL.md files (6x) | Add progress + clarification conventions | ~15 each |

## What NOT to Do

- Do NOT create new MCP actions for clarification — reuse `message` + `poll`
- Do NOT create `ask_orchestrator` tool — that requires hermes-agent upstream changes
- Do NOT add file-based progress (`.olympus_progress.{PID}`) — steering table + enriched poll covers this
- Do NOT modify the ACP protocol itself — the changes are all in Olympus v3 layer