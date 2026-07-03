# Requiem Agents — Architecture Audit (2026-06-24)

Full audit of Requiem Agents v0.3.0 after REQ-1 through REQ-4 fixes. Covers architecture, design decisions, and optimizations. Findings sorted by severity.

## CRITICAL Findings

### A1: Dead code — legacy MCP functions still in necromancer.py
`process_investigate()`, `process_execute()`, `process_implement()` (lines ~850-991) are legacy entry points from the old MCP server. The plugin v0.3.0 only calls `process_task()`. These functions:
- Are never called by any plugin handler
- Confuse anyone reading the code (3 entry points that look active)
- Can be accidentally invoked if someone adds a new handler
- ~150 lines of dead code

**Fix:** Delete all three functions. `process_task()` is the only entry point.

### A2: Duplicate execution loop — process_subtasks() duplicates process_task()
`process_subtasks()` (lines ~700-800) duplicates the shade→audit→retry loop already in `process_task()` (lines ~600-690). Two implementations of the same logic:
- If you fix a retry bug in one, the other stays broken
- process_task() has REQ-1 execution subtask injection; process_subtasks() does not
- process_task() has state_tracker; process_subtasks() has a different state_tracker interface

**Fix:** Delete `process_subtasks()`. The thread in `tools.py` calls `process_task()` which handles everything.

## HIGH Findings

### A3: Graphify graph contaminated with external code
graph.json has 23,942 nodes but god_nodes returns Honcho, Aether-Agents skills, and graphify-reference internals — NOT Requiem code. The graphify indexer is scanning:
- `graphify-reference/` (full clone of graphify's own repo, ~200+ files)
- Aether-Agents skills directory
- Honcho source code

**Impact:** `query_graph("necromancer process_task")` returns nodes from Aether-Agents audit skills, not from Requiem's necromancer.py. Raven's "explore before delegate" feature is broken — it gets ruido instead of real project structure.

**Fix:** Regenerate graph.json excluding external directories:
```bash
cd /home/prometeo/Requiem
# Create .graphifyignore or use --exclude
graphify update . --exclude graphify-reference/ --exclude raven/skills/hermes/
```
Verify: `god_nodes(top_n=10)` should return Requiem-specific nodes (process_task, audit, run_shade, etc.), not Honcho/Session/Peer.

### A4: Revenant uses expensive model for simple audits
REVENANT_MODEL = deepseek-v4-pro ($0.435/$0.87 per 1M). The Revenant's job is largely mechanical: read files, compile .py, check if what was asked exists, give PASS/FAIL. With 3 retries per subtask, audit costs can exceed Shade execution costs.

**Fix options:**
- Use deepseek-v4-flash for creation tasks with file verification (deterministic checks)
- Keep v4-pro only for complex audits (architecture, logic correctness)
- Or implement 100% deterministic audit (no LLM) for syntax-only checks

### D1: Auto-pass string matching is fragile
The Revenant auto-pass checks if output contains "passed" or "0 errors" — but these strings can appear in comments, string literals, or error messages. Example false positive: Shade writes `# all tests passed` in a comment, Revenant auto-passes without checking actual test output.

**Fix:** Auto-pass should verify `exit_code == 0` from terminal tool results (structured JSON), not grep for strings in free text.

### O1: read_file_simple counter never resets
`_read_counter` in tools.py increments per session_id but never resets between turns. After 3 reads in turn 1, the tool is permanently blocked for that session. Raven loses read capability after the first interaction.

**Fix:** Reset `_read_counter[session_id] = 0` at the start of each turn. Implement via a `pre_llm_call` hook or check if the tool is being called in a new turn context.

### O2: SwiftRouter client has no retries
`opencode_client.py` makes a single `httpx.post()` with no retry logic. A 429 (rate limit) or 503 (service unavailable) kills the entire task — even if it's a transient error after 4 minutes of Shade work.

**Fix:** Add retry with exponential backoff:
```python
for attempt in range(3):
    try:
        response = await client.post(...)
        response.raise_for_status()
        break
    except (httpx.HTTPStatusError, httpx.RequestError) as e:
        if attempt == 2:
            raise
        await asyncio.sleep(2 ** attempt)  # 1s, 2s, 4s
```

## MEDIUM Findings

### A5: process_task() mixes 3 phases in one function
Decomposition (Necromancer LLM), execution (Shade LLM), and audit (Revenant LLM) are all in one 100-line async function. Hard to test, hard to modify one phase without touching others.

**Fix:** Extract `_decompose()`, `_execute_subtasks()`, `_audit_cycle()`. process_task() only orchestrates.

### A6: _override_shade() heuristic is fragile
Pattern matching on task text to route Shades. "research how to create X" gets overridden to "programming" because "create" matches creation patterns. The LLM's routing choice should be primary; override only for obvious cases.

### D3: Shade timeout 300s with no graceful degradation
If the LLM provider has a latency spike >300s, the Shade dies and returns "timeout". No retry with a cheaper/faster model. The user has to manually re-trigger.

### O3: Dashboard polls every 5s unconditionally
App.jsx fetches 4 endpoints every 5 seconds regardless of activity. 48 requests/minute when idle. Should use adaptive polling (5s when active, 30s when idle) or WebSocket/SSE.

### O4: eval.py opens/closes SQLite on every call
`log_agent_call()` calls `init_db()` + `get_db()` + `close()` each time. In a 25-iteration Shade, that's 25 connections. Should use connection pooling or batch inserts.

## LOW Findings

### D5: Pricing table missing models in Config.jsx
MODEL_OPTIONS in Config.jsx includes `kimi-k2` but pricing.py doesn't have it. calculate_cost returns 0.0 for unlisted models, making telemetry inaccurate.

### O6: SOUL.md has duplicate workflow sections
"What Raven Does" (section 1) has old steps 5-7 (without check_progress). "How Raven Works" (section 2) has correct steps 5-8 (with Monitor). The LLM may follow either.

## Findings Discovered During Fix Phase

The original audit (above) was performed BEFORE fixes. During the fix phase, additional critical findings were discovered:

### A7: Plugin Not Enabled — Missing `plugins:` Section in config.yaml (CRITICAL)
The plugin `requiem_tools` existed on disk (plugin.yaml, __init__.py, tools.py, schemas.py all present) and the toolset name was in `toolsets:`, but config.yaml had NO `plugins:` section. hermes-agent never loaded the plugin. Raven had ZERO access to delegate_to_necromancer, check_progress, or read_file_simple.

This was the ROOT CAUSE of "Raven can't program, Shades summarize everything, tasks take 5 minutes." Without the plugin tools, Raven fell back to whatever default tools it had — which couldn't invoke the Necromancer pipeline at all.

**Fix:** Added `plugins: enabled: [requiem_tools]` to config.yaml.
**Lesson:** Always check `plugins:` section FIRST when a plugin's tools are invisible. No error is produced — the plugin simply doesn't exist from the agent's perspective.

### A8: Skill File Describes Non-Existent Tools (CRITICAL)
The `necromancer-delegation` SKILL.md was 523 lines and described the OLD plugin tools (investigate, execute, implement) that were replaced by delegate_to_necromancer/check_progress/read_file_simple. The LLM read the skill, tried to call investigate/execute/implement, failed, and degraded to verbose narration without action.

**Fix:** Rewrote the skill from scratch (523 → 93 lines) describing ONLY the current tools.
**Lesson:** After ANY tool interface migration, audit ALL skill files. A stale skill describing non-existent tools is worse than no skill — it actively misleads the LLM.

### O7: Revenant Auto-Pass by String Matching — Replaced with exit_code (MEDIUM)
The original audit (D1) noted auto-pass string matching was fragile. During the fix, the Revenant was upgraded to auto-pass based on `exit_code` from the terminal tool's JSON output (exit_code=0 → auto-pass, exit_code≠0 → auto-fail). No LLM call needed for obvious pass/fail cases.

### O8: Connection Pooling Added to eval.py (LOW)
`log_agent_call()` was opening/closing SQLite on every call. Fixed with `_db_lock` (threading.Lock) + `_db_conn` persistent connection.

### O9: Adaptive Dashboard Polling (LOW)
App.jsx was polling every 5s unconditionally (O3). Fixed with `activityRef` — 5s when active, 30s when idle.

## Top 3 Fixes (Budget-Limited)

1. **A7** — Add `plugins: enabled: [requiem_tools]` to config.yaml. 1 min. This was the ROOT CAUSE of the entire regression. Without this, no other fix matters.
2. **A1+A2** — Delete dead/duplicate code (process_investigate, process_execute, process_implement, process_subtasks). ~250 lines, 30 min. Prevents silent bugs from divergent retry logic.
3. **A8** — Rewrite stale skill file (523→93 lines). 15 min. Without this, the LLM tries to call non-existent tools and degrades.
