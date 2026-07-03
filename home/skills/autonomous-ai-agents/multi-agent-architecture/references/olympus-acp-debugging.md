# Olympus v3 ACP Debugging Reference

Complete diagnostic reference for observability failures when delegating to Daimons via ACP.

## Pitfall #25 — ACP Plugin Hooks: Corrected Diagnosis

### Initial Hypothesis (INCORRECT)

It was initially believed that `acp_adapter/entry.py` never calls `discover_plugins()`, causing `PluginManager._hooks` to be empty and all olympus_v3 hooks to silently skip. **This was wrong.**

### Corrected Diagnosis (2026-06-10)

**Plugins DO load in ACP mode.** The `model_tools.py` module-scope import (line 197) calls `discover_plugins()` when `model_tools` is first imported by `acp_adapter/server.py`. This happens on the first tool definition request in each Daimon session. Evidence:

```
# From hefesto/logs/agent.log (prove that hooks register):
INFO olympus_v3.hooks: Olympus v3 hooks registered (on_session_start, post_llm_call, post_tool_call, on_session_end, pre_llm_call)
INFO hermes_cli.plugins: Plugin discovery complete: 35 found, 29 enabled
```

**Two REAL issues were found behind the `tool_calls: 0` symptom:**

### Issue A — UNIQUE Constraint on session insert (REAL BUG)

`acp_manager.spawn_agent()` inserts the session row via async `aiosqlite`. Then `on_session_start` hook fires inside the Daimon process and tries to INSERT the same row again. Result: `UNIQUE constraint failed: sessions.session_id`.

```bash
grep "UNIQUE constraint" ~/Aether-Agents/home/profiles/hefesto/logs/agent.log
# → WARNING: on_session_start hook failed: UNIQUE constraint failed: sessions.session_id
```

**Fix needed:** Change `on_session_start` hook to use `INSERT OR IGNORE` or `INSERT OR REPLACE` instead of bare `INSERT`.

### Issue B — 429 Rate Limit Masquerading as Observability Bug (REAL CAUSE)

When the Daimon's LLM provider returns HTTP 429, the Daimon never generates output, never calls tools, so `post_tool_call` never fires. The symptom is IDENTICAL to "hooks not working" but the cause is upstream.

```bash
grep "429\|RateLimitError\|Monthly usage limit" ~/Aether-Agents/home/profiles/hefesto/logs/agent.log
# → WARNING: API call failed (attempt 1/3) error_type=RateLimitError
# → HTTP 429: Monthly usage limit reached
```

### Proof That discover_plugins() Runs in ACP Mode

The comment in `model_tools.py` (line 188) explicitly lists the ACP entry point:

```python
# Each entry point now runs discovery explicitly at its own startup:
#   - gateway/run.py            -> start_gateway() uses run_in_executor
#   - cli.py, hermes_cli/*      -> inline on startup (no event loop)
#   - tui_gateway/server.py     -> inline on startup (no event loop)
#   - acp_adapter/server.py     -> asyncio.to_thread on session init
```

And lines 196-199:
```python
try:
    from hermes_cli.plugins import discover_plugins
    discover_plugins()
except Exception as e:
    logger.debug("Plugin discovery failed: %s", e)
```

This module-scope code runs when `acp_adapter/server.py` imports `get_tool_definitions` from `model_tools` (lines 788, 1691). The import triggers `discover_plugins()`, which loads all plugins including `olympus_v3`.

### Why the Initial Hypothesis Was Wrong

The investigation traced through:
1. `acp_adapter/entry.py` — truly has NO `discover_plugins()` call ✓
2. BUT `model_tools.py` HAS module-scope `discover_plugins()` at line 197 ✓
3. `acp_adapter/server.py` imports `model_tools` lazily at line 788 ✓
4. On first import, module-scope code runs, including `discover_plugins()` ✓
5. Hefesto's `agent.log` confirms: "Olympus v3 hooks registered" ✓
6. Hefesto's `agent.log` confirms: "Plugin discovery complete: 35 found, 29 enabled" ✓

**Adding `discover_plugins()` to `acp_adapter/entry.py` is NOT needed** — it would be redundant since `model_tools.py` already calls it on import. The real fixes are: (A) use INSERT OR IGNORE in `on_session_start`, and (B) check for 429 rate limits before assuming observability bugs.

### Diagnostic Commands

```bash
# 1. FIRST: Check agent.log for 429 rate limits (most common cause of tool_calls=0)
grep "429\|RateLimitError\|Monthly usage limit" ~/Aether-Agents/home/profiles/hefesto/logs/agent.log

# 2. Check if plugins loaded (rules out missing discover_plugins)
grep "Olympus v3 hooks registered\|Plugin discovery complete" ~/Aether-Agents/home/profiles/hefesto/logs/agent.log

# 3. Check for UNIQUE constraint in session creation (Issue A)
grep "UNIQUE constraint" ~/Aether-Agents/home/profiles/hefesto/logs/agent.log

# 4. Confirm DB state
sqlite3 ~/Aether-Agents/home/.olympus/olympus_v3.db \
  "SELECT COUNT(*) FROM sessions; SELECT COUNT(*) FROM turns; SELECT COUNT(*) FROM tool_calls;"

# 5. Check for zombie olympus processes (Pitfall #24)
for pid in $(pgrep -f 'olympus_v3.server'); do
  echo "PID $pid:"
  ls -la /proc/$pid/fd 2>/dev/null | grep -E "db.*deleted"
done
```

---

## Pitfall #23 — FK Constraint: `post_llm_call` Silently Drops Turn Data

**Symptom:** `delegate()` returns `last_turn: null`, `tool_calls: 0`. `agent.log` shows `stop_reason=end_turn`. DB has 0 sessions, 0 turns.

**Root cause:** `olympus_v3` plugin had no `on_session_start` hook. The `acp_manager` async `insert_session()` wrote to `olympus_v3.db` via aiosqlite, but the WAL wasn't checkpointed before sync hooks tried to `INSERT INTO turns(session_id, ...)` with a FOREIGN KEY referencing `sessions(session_id)`. The FK constraint failed silently (caught by try/except), dropping all turn data.

**Fix (applied 2026-06-09):** Added `on_session_start` hook to `hooks.py` + `OlympusDBSync.insert_session()` + WAL checkpoint. See full SKILL.md Pitfall #23.

**NOTE:** This fix introduced Issue A above — the hook now fires but tries to INSERT a row that `acp_manager` already created, causing a UNIQUE constraint violation. Follow-up fix needed: INSERT OR IGNORE.

---

## Pitfall #24 — Zombie MCP Server Processes After Gateway Restart

**Symptom:** After `systemctl restart hermes-gateway.service`, MCP polls return stale/empty data.

**Root cause:** Old `olympus_v3.server` processes persist after gateway restart. They hold FDs to the deleted DB file. MCP requests route to either old or new processes.

**Fix:** Always `pkill -f 'olympus_v3.server'` before restarting the gateway. See full SKILL.md Pitfall #24.

---

## Pitfall #21 — ACP `LimitOverrunError` (v0.16.0 regression)

**Symptom:** Daimon processes start but produce no output. Gateway logs show `LimitOverrunError: Separator is found, but chunk is longer than limit`.

**Root cause:** v0.16.0 regression in ACP stdio protocol. `asyncio.StreamReader` default buffer limit (64 KB) exceeded by Daimon responses.

**Fix:** Downgrade to v0.15.2. See full SKILL.md Pitfall #21.

---

## Pitfall #27 — Reserved Word in MCP Tool Parameter Name + Missing `required` Fields

**Symptom:** `delegate()` returns `"Error: 'agent' is required for delegate action."` even when `agent` is passed in the prompt. `discover()` also fails.

**Root cause (two bugs combined):**

1. **Reserved word `agent`**: The MCP tool schema used `"agent"` as a parameter name. hermes-agent's MCP client treats `agent` as a reserved internal field and STRIPS it before serialization. The server always receives `agent=""`. Fix: rename to `"daimon"` in both the JSON schema (line ~137) and handler code (lines ~304, ~407).

2. **Missing `required` fields**: The JSON schema had `"required": ["action"]` only. The model could (and did) omit `daimon` and `prompt` from tool calls because they weren't declared required. The server then rejected the call with `"X is required"`. Fix: add `"daimon"` and `"prompt"` to the `required` array (line ~178).

**Full fix in `olympus_v3/server.py`:**
```python
# Change 1: Schema (~line 137)
"agent" → "daimon"

# Change 2: Handler (~lines 304, 407)
args.get("agent") → args.get("daimon") or args.get("agent")

# Change 3: Required array (~line 178)
# DO NOT add "prompt" to required — it breaks close/cancel/steer/poll (see Pitfall #27b)
"required": ["action"] → "required": ["action", "daimon"]
```

**Validation:** After fix, `talk_to(action="delegate", daimon="hefesto", ...)` works. The `or args.get("agent")` backward-compat fallback ensures old tool calls with `agent` still work.

**Gateway restart required** after applying the fix: `systemctl --user restart hermes-gateway.service`. After restart, check for zombie olympus processes (Pitfall #24).

### Pitfall #27b — Adding `prompt` to `required` Breaks Non-Delegate Actions

**Symptom:** After adding `"prompt"` to the `required` array (to force the model to always include it in delegate calls), `close()`, `cancel()`, `steer()`, and `poll()` fail with:
```
Input validation error: 'prompt' is a required property
```

**Root cause:** JSON Schema `required` is all-or-nothing — every field in the array is mandatory for EVERY call, regardless of action. `close`, `cancel`, `steer`, and `poll` don't need `prompt`, but the schema rejects them anyway.

**Workaround (temporary):** Pass a dummy `prompt="close"` on non-delegate actions. This satisfies the schema validator but is a hack that wastes tokens and context.

**Real fix:** Do NOT put `prompt` in `required`. Instead, validate it in the handler for actions that need it (`open`, `delegate`, `message`):
```python
if action in ("open", "delegate", "message") and not prompt:
    return error("'prompt' is required for this action")
```
This keeps the schema loose enough for all actions while enforcing prompt where needed.

**Why the model omission problem (original #27) still gets solved:** The `required: ["daimon"]` in the schema is sufficient — the model learns the pattern from tool descriptions that say "REQUIRED" in the parameter description. The real problem in #27 was `agent` being stripped, not `prompt` being missing. With `daimon` in `required`, the fix holds.

---

## Diagnostic Decision Tree (Corrected)

```
delegate() returns empty data (tool_calls=0, last_turn=null)
│
├─ Check agent.log FIRST:
│  ├─ 429 / RateLimitError → Issue B: LLM provider blocked. Fix rate limit, not hooks.
│  ├─ "Olympus v3 hooks registered" present → Plugins loaded. NOT a discovery bug.
│  ├─ "UNIQUE constraint failed" → Issue A: Double session insert. Fix: INSERT OR IGNORE.
│  └─ No agent.log entries → Daimon process may not have started. See #11 or #21.
│
├─ Is Daimon process running? (ps aux | grep "hermes acp")
│  ├─ NO → See Pitfall #21 (LimitOverrunError) or #11 (Internal error)
│  └─ YES ↓
│
├─ Does agent.log show stop_reason=end_turn?
│  ├─ NO → Daimon didn't produce output (429 rate limit, auth error, model issue)
│  └─ YES but tool_calls=0 in DB → Check UNIQUE constraint or FK issues
│
├─ Does olympus_v3.db have sessions?
│  ├─ NO → See Pitfall #11 (ACP spawn failure)
│  └─ YES ↓
│
├─ Does olympus_v3.db have turns/tool_calls?
│  ├─ NO but agent.log has 429 → Fix rate limit (Issue B)
│  ├─ NO and agent.log has FK error → Fix FK constraint (Pitfall #23)
│  ├─ NO and agent.log has UNIQUE error → Fix INSERT OR IGNORE (Issue A)
│  └─ YES but poll returns empty → Pitfall #24 (zombie processes)
│
└─ Other → check for stale DB FDs, restart gateway after killing orphan processes
```

### Issue C — Zero Observability of Daimon Errors in delegate/poll

When a Daimon's LLM call fails (429, auth error, timeout), no `post_llm_call` or `post_tool_call` hooks fire. The olympus_v3 DB stays empty. `talk_to(poll)` returns `tool_calls: 0, last_turn: null, status: "active"` with NO error information. Hermes has no way to distinguish between "Daimon is working slowly" and "Daimon's provider returned 429 three times and gave up."

**What's missing from `get_session_progress()`:**
- `last_error`: Most recent error message from the Daimon
- `error_type`: Category (rate_limit, auth, timeout, crash)
- `status: "error"` instead of `"active"` when the Daimon process has failed

**Planned fix:** Add error fields to the DB schema and `get_session_progress()`. Capture LLM errors via `post_llm_call` or a new hook. Return `"error"` status when appropriate.

### Issue D — Shared Provider Workspace: Single Point of Failure

All Daimon profiles use the same `opencode-go` provider with the same workspace. When the workspace's monthly quota is exhausted (HTTP 429), every Daimon using that provider fails simultaneously. No `fallback_models` are configured. This makes the entire fleet fragile — one billing limit hits all 6 Daimons at once.

**Fix:** Configure `fallback_models` in each Daimon's `config.yaml` to use an alternate provider (e.g., openrouter) when the primary is rate-limited. See `references/fallback-providers.md`.

### Pitfall #26 — File-Mutation Verifier False Positive

When a Daimon writes files via `terminal` (e.g., `cat > file << EOF`) instead of the `write_file` tool, the olympus_v3 file-mutation verifier reports:

```
⚠️ File-mutation verifier: 1 file(s) were NOT modified this turn despite any wording above that may suggest otherwise.
  • /path/to/file — [write_file] Edit approval denied by ACP client; file was not modified.
```

**The file IS actually created.** The verifier only tracks `write_file` tool calls, not terminal-based file writes. Hefesto often falls back to `terminal` + `cat >` when `write_file` is denied by ACP approval settings.

**Verification:** Always check the filesystem directly (`ls -la`, `wc -l`, `head`) after delegation — do NOT rely on the verifier message. If the file exists and has content, the delegation succeeded regardless of the verifier warning.

---

### Anti-pattern: Assuming "hooks not firing" Without Checking agent.log

The most dangerous diagnostic mistake is jumping to framework-level conclusions (missing discovery, broken hooks) without first checking the Daimon's own logs. Always check `agent.log` for:
1. **429 rate limits** — the #1 cause of empty delegation results
2. Plugin registration confirmations
3. Hook execution errors (UNIQUE, FK)
4. Actual LLM response status

The Daimon process logs (`<profile>/logs/agent.log`) are the single most important diagnostic for delegation failures. Check them BEFORE assuming a framework bug.

**Priority order for diagnosing `delegate()` returning empty data:**
1. Check `agent.log` for 429/rate limit → Fix provider, not framework
2. Check `agent.log` for "Olympus v3 hooks registered" → Confirms plugins load
3. Check `agent.log` for "UNIQUE constraint failed" → Fix INSERT OR IGNORE
4. Check DB for sessions vs turns/tool_calls discrepancy → FK or UNIQUE issue
5. Check for zombie olympus processes → Kill and restart gateway