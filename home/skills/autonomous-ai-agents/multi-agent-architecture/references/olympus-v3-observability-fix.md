# olympus_v3 Observability Fix — Detailed Programmer Prompt

Generated 2026-06-10. Concrete code changes to fix UNIQUE constraint and zero observability bugs.

## Bug A: on_session_start UNIQUE Constraint Violation

**Root cause:** `acp_manager.spawn_agent()` inserts the session row first (async, aiosqlite). Then `on_session_start` hook fires inside the Daimon process and tries `INSERT INTO sessions` with the same `session_id` → `UNIQUE constraint failed`.

**Evidence:**
```
grep "UNIQUE constraint" ~/Aether-Agents/home/profiles/hefesto/logs/agent.log
→ WARNING: on_session_start hook failed: UNIQUE constraint failed: sessions.session_id
```

### Fix: `src/olympus_v3/db.py`

**Async version (~line 200):**
```python
# BEFORE:
await self._execute(
    "INSERT INTO sessions (session_id, agent, status, started_at, metadata) "
    "VALUES (?, ?, 'active', ?, ?)",
    (sid, agent, now, meta_json),
)

# AFTER:
await self._execute(
    "INSERT OR IGNORE INTO sessions (session_id, agent, status, started_at, metadata) "
    "VALUES (?, ?, 'active', ?, ?)",
    (sid, agent, now, meta_json),
)
```

**Sync version (~line 540):**
```python
# BEFORE:
conn.execute(
    "INSERT INTO sessions (session_id, agent, status, started_at, metadata) "
    "VALUES (?, ?, 'active', ?, ?)",
    (sid, agent, now, meta_json),
)

# AFTER:
conn.execute(
    "INSERT OR IGNORE INTO sessions (session_id, agent, status, started_at, metadata) "
    "VALUES (?, ?, 'active', ?, ?)",
    (sid, agent, now, meta_json),
)
```

### No change needed in hooks.py

The `on_session_start` hook in `src/olympus_v3/olympus_v3_hooks/hooks.py` calls `db.insert_session()` which will now use `INSERT OR IGNORE`. If the row already exists (inserted by acp_manager), the hook silently skips — idempotent.

---

## Bug B: Zero Observability — Daimon Errors Invisible in delegate/poll

**Root cause:** When a Daimon fails (429 rate limit, auth error, timeout), no LLM response is produced. `post_llm_call` never fires. `post_tool_call` never fires. The DB stays empty. Hermes polls and sees `tool_calls: 0, messages: 0, last_turn: null, status: "active"`.

### Fix 1: Add `last_error` and `error_type` columns to sessions table

**`src/olympus_v3/db.py` — Schema (~line 37):**
```python
SCHEMA_SESSIONS = """
CREATE TABLE IF NOT EXISTS sessions (
    session_id  TEXT PRIMARY KEY,
    agent       TEXT NOT NULL,
    status      TEXT DEFAULT 'active',
    started_at  REAL NOT NULL,
    completed_at REAL,
    metadata    TEXT,
    last_error  TEXT,
    error_type  TEXT
)
"""
```

**Migration in `ensure_tables()` (after schema creation):**
```python
# Add columns if they don't exist (idempotent migration for existing DBs)
for col, coltype in [("last_error", "TEXT"), ("error_type", "TEXT")]:
    try:
        conn.execute(f"ALTER TABLE sessions ADD COLUMN {col} {coltype}")
    except sqlite3.OperationalError:
        pass  # Column already exists
```

### Fix 2: Add `record_error()` method to DB classes

**Async `OlympusDB` class:**
```python
async def record_error(self, session_id: str, error_message: str, error_type: str = "api_error") -> None:
    """Record an error for a session."""
    await self._execute(
        "UPDATE sessions SET last_error = ?, error_type = ?, status = 'error' WHERE session_id = ?",
        (error_message, error_type, session_id),
    )
    await self._db.commit()
```

**Sync `OlympusDBSync` class:**
```python
def record_error(self, session_id: str, error_message: str, error_type: str = "api_error") -> None:
    """Record an error for a session."""
    conn = self._connect()
    try:
        conn.execute(
            "UPDATE sessions SET last_error = ?, error_type = ?, status = 'error' WHERE session_id = ?",
            (error_message, error_type, session_id),
        )
        conn.commit()
    finally:
        conn.close()
```

### Fix 3: Write errors in `on_session_end` hook

**`src/olympus_v3/olympus_v3_hooks/hooks.py` — `on_session_end` (~line 270):**
```python
def on_session_end(
    session_id: str,
    completed: bool,
    interrupted: bool,
    model: str,
    platform: str,
    **kwargs: Any,
) -> None:
    olympus_sid = _get_session_id()
    if not olympus_sid:
        logger.debug("No OLYMPUS_SESSION_ID, skipping on_session_end")
        return

    status = "completed" if completed else ("cancelled" if interrupted else "error")

    try:
        db = _get_db()
        db.update_session_status(olympus_sid, status)

        # Record error info if the session ended abnormally
        if status == "error":
            error_msg = kwargs.get("error") or kwargs.get("last_error") or "Session ended with error"
            error_type_val = kwargs.get("error_type") or "session_error"
            db.record_error(olympus_sid, error_msg, error_type_val)

        logger.info("on_session_end: session %s marked as %s", olympus_sid, status)
    except Exception as e:
        logger.warning("on_session_end hook failed: %s", e)
```

### Fix 4: Propagate `last_error` in poll response

**`src/olympus_v3/db.py` — `get_session_progress` (sync version, ~line 709):**

Add after the session status query:
```python
# Error info
cursor = conn.execute(
    "SELECT last_error, error_type FROM sessions WHERE session_id = ?",
    (session_id,),
)
error_row = cursor.fetchone()
last_error = error_row[0] if error_row else None
error_type = error_row[1] if error_row else None
```

Add to the return dict:
```python
"last_error": last_error,
"error_type": error_type,
```

### Fix 5: Update `_build_response` in server.py

**`src/olympus_v3/server.py` (~line 96):**
```python
async def _build_response(session_id: str) -> dict:
    db = _get_db()
    progress = await db.get_session_progress(session_id)
    session = await db.get_session(session_id)

    return {
        "session_id": session_id,
        "status": progress.get("status", "unknown"),
        "thoughts": progress.get("thoughts", 0),
        "messages": progress.get("messages", 0),
        "tool_calls": progress.get("tool_calls", 0),
        "response": progress.get("last_turn"),
        "last_error": progress.get("last_error"),
        "error_type": progress.get("error_type"),
    }
```

---

## Bug C: Shared Provider Workspace (Config, Not Code)

All Daimons + Hermes use same opencode-go workspace. One rate limit kills entire fleet.

**Fix:** Add `fallback_models` to each Daimon profile config.yaml. Example for `profiles/hefesto/config.yaml`:
```yaml
model:
  default: deepseek-v4-flash
  provider: opencode-go
  base_url: https://opencode.ai/zen/go/v1
  fallback_models:
    - provider: openrouter
      model: deepseek/deepseek-chat-v3-0324
```

This is configuration, not a code change. Requires available API keys for fallback providers.

---

## Verification

After applying Bug A + B fixes:

```bash
# 1. Restart gateway
systemctl --user restart hermes-gateway.service

# 2. Delegate a test task
# 3. Verify no UNIQUE constraint errors
grep "UNIQUE constraint" ~/Aether-Agents/home/profiles/hefesto/logs/agent.log | tail -5

# 4. Check DB for error columns
sqlite3 ~/Aether-Agents/home/.olympus/olympus_v3.db "PRAGMA table_info(sessions);" | grep -E "last_error|error_type"

# 5. Verify delegate poll returns error info when Daimon fails
# Should see: {"last_error": "...", "error_type": "rate_limit", ...}
```

## Key File Paths

| File | Purpose |
|------|---------|
| `src/olympus_v3/db.py` | DB schema, insert_session, record_error, get_session_progress |
| `src/olympus_v3/olympus_v3_hooks/hooks.py` | on_session_start, on_session_end hooks |
| `src/olympus_v3/server.py` | _build_response, poll/delegate response |
| `src/olympus_v3/acp_manager.py` | spawn_agent (creates session row before hook) |
| `home/profiles/hefesto/config.yaml` | Daimon model config (fallback_models) |

## Important Context

- `acp_adapter/entry.py` does NOT need `discover_plugins()` added — plugins load via `model_tools.py` module-scope import (line 197). The initial diagnosis that plugins weren't loading was WRONG.
- The correct diagnostic flow is: check `agent.log` FIRST (grep for 429/RateLimitError/UNIQUE constraint), THEN check the DB, THEN check framework code.
- The UNIQUE constraint happens because `acp_manager.spawn_agent()` (async) creates the session row before the Daimon's `on_session_start` hook (sync) fires. The hook's INSERT is a duplicate attempt.