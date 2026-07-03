# Requiem Agents — REQ Fixes Session (2026-06-24)

Session log of 4 requerimientos found during end-to-end testing of Requiem Agents v0.3.0.
Updated with post-fix session findings (graphify config loss, docker port conflict, ACP fix verification).

## REQ-1: Revenant auto-fail on syntax errors + orchestrator injects execution subtask

### Problem
The Revenant (peer-auditor) gave PASS to code that didn't compile. In Test 2, a Shade modified `counter.py` to inherit from `NonExistentBase` (non-existent class). The Revenant approved it because its checks were purely mechanical (`has_files=True`, `is_execution=True`).

### Fix Part A: Revenant auto-fail
In `revenant.py` `audit()`, after `compile_results` are generated, before LLM review:
```python
if compile_results and "SYNTAX ERROR" in compile_results:
    return {'verdict': 'fail', 'feedback': 'CODE DOES NOT COMPILE...', 'input_tokens': 0, 'output_tokens': 0}
```

### Fix Part B: Necromancer forces execution subtask
In `necromancer.py` `process_task()`, after subtasks are parsed from LLM:
```python
has_programming = any(st.get("shade") == "programming" for st in subtasks)
has_execution = any(st.get("shade") == "execution" for st in subtasks)
if has_programming and not has_execution:
    subtasks.append({"shade": "execution", "task": "Run pytest..."})
```

### Fix Part C: f-string syntax error in revenant.py (POST-FIX)
The auto-fail return statement used an f-string with `\n` escape sequences. When Hefesto patched the file, the `\n` in the patch `new_string` got interpreted as literal newlines, breaking the f-string with `SyntaxError: unterminated f-string literal` at line 205.

Original broken code:
```python
'feedback': f'CODE DOES NOT COMPILE. Syntax errors detected:
{compile_results}

Fix the syntax errors before resubmitting.',
```

Fix: replaced the f-string with string concatenation:
```python
'feedback': 'CODE DOES NOT COMPILE. Syntax errors detected:\n' + compile_results + '\n\nFix the syntax errors before resubmitting.',
```

**Lesson:** After ANY patch that modifies Python code containing f-strings with escape sequences, immediately run `python3 -m py_compile` to catch breakage. Prefer string concatenation over f-strings in patch content.

## REQ-2: Shade Programming efficiency rules

### Problem
13 iterations to add a `multiply` method to a Calculator class. The Shade entered a write→test→read→write cycle. First attempt was rejected by Revenant (has_files=False — write_file not detected). Then the Shade looped.

### Fix: Efficiency rules in programming.md soul
Added to `necromancer/shades/programming.md`:
- WRITE ONCE: Write the file, then STOP. Do not re-read what you just wrote.
- NO RE-READS: Never read_file a file you just wrote with write_file.
- NO SELF-TESTING: Do NOT run tests yourself. That's the Shade of Execution's job.
- MAX 5 ITERATIONS: For simple tasks (<50 lines), maximum 5 tool iterations.
- ONE WRITE PER FILE: Write each file exactly once. Max 2 writes per file (original + 1 fix).

These rules address system prompt dominance (Pitfall 13 in text-based-tool-calling-pitfalls.md) — without explicit efficiency rules, flash models enter read-write-test loops indefinitely.

### Also: Revenant extract_file_paths detection
The `extract_file_paths()` regex in `revenant.py` already matches `File written: /path` format. The detection issue in Test 1 was that the Shade's first write_file call didn't get tracked because the Shade didn't append the "Files Created/Modified" section to its output (this is done by `run_shade()` in necromancer.py, lines ~440-445). The tracking works when `run_shade()` appends the file list, but the Shade's final assistant message must also mention the files for the Revenant's `extract_file_paths()` to find them.

## REQ-3: Graphify as read-layer (resolved, no code change needed)

### Problem
Each file read required: Raven → delegate → Necromancer decompose → Shade Research → read_file → Revenant audit → result (~30 seconds per file).

### Resolution
Graphify MCP server integration (already done) gives Raven structural understanding without file reads. `query_graph`, `get_neighbors`, `god_nodes` provide architecture-level understanding. The remaining gap (reading file CONTENT) is addressed by REQ-3B (`read_file_simple` with rate limiter).

### Graphify boundary clarification
Graphify stores METADATA (label, type, location, relationships) — NOT file content. It parses code files (Python, JS, etc.) but not markdown/config files. When the user asked Raven to "read your SOUL.md", Raven had to delegate because SOUL.md is markdown (not parseable by graphify) and graphify doesn't store content anyway.

```
Graphify CAN:                   Graphify CANNOT:
  "What functions exist"          "Show me the code in stack.py"
  "Who calls parse_line"          "Read the content of config.yaml"
  "What's the core abstraction"   "Show me line 50 of necromancer.py"
  "How does parser connect to X"  "Read a .md file"
```

### POST-FIX: Graphify config block lost during Hefesto patching

After applying all REQ fixes via Hefesto delegation (patches to tools.py, schemas.py, __init__.py, plugin.yaml, SOUL.md, revenant.py, programming.md), the graphify MCP server block disappeared from `raven/config.yaml`.

**Root cause:** The config.yaml is git-tracked. Graphify was added manually during a previous session and never committed to git. When Hefesto patched config.yaml (or when the file was otherwise rewritten), the manually-added graphify block was silently dropped because it wasn't in the git version.

**Timeline:**
1. Graphify block added to config.yaml lines 593-600 (manual, not committed)
2. Hefesto patches multiple files in the same session
3. Config.yaml gets modified — graphify block disappears
4. Gateway restart — graphify MCP tools gone
5. User reports graphify "desconfigurado"

**Fix:** Re-added the graphify block to the end of config.yaml via Hefesto delegation:
```yaml
  graphify:
    command: /home/prometeo/Requiem/raven/.venv/bin/python3.11
    args:
      - -m
      - graphify.mcp_server
    enabled: true
    env:
      GRAPH_PATH: /home/prometeo/Requiem/graphify-out/graph.json
```

**Prevention:** Either commit config changes to git immediately, or add config.yaml to .gitignore. Always verify MCP blocks survive delegation: `grep -n "graphify\|mcp_servers" config.yaml` after any patch session.

## REQ-3B: read_file_simple with per-turn rate limiter

### Design
A `read_file_simple(path)` tool with a per-turn counter (max 3 reads per conversation turn). After 3 reads, returns:
```json
{"error": "LIMIT_REACHED", "message": "You have used read_file_simple 3 times this turn. For extensive code investigation, delegate to the Necromancer."}
```

### Why rate limiting beats prompt instructions
The expensive model's tool-affordance bias overrides SOUL.md instructions — if `read_file` exists, the model WILL use it excessively. By making the tool itself enforce the limit, the model is structurally forced to change strategy (delegate) rather than being told to. This is behavioral alignment through tool design, not prompt engineering.

### Implementation notes
- Counter is per-session_id, reset each turn
- Files truncated at 10K chars
- Returns `reads_remaining` so the model knows how many reads it has left
- Plugin version 0.3.0 registers 3 tools: delegate_to_necromancer, check_progress, read_file_simple

## REQ-4: Async delegation with check_progress

### Problem
`delegate_to_necromancer` was blocking — Raven called it and waited minutes with zero visibility. The MCP original had 4 granular tools (decompose/execute/progress/result).

### Fix: Split into 2 tools
1. `delegate_to_necromancer(prompt, project_root)` — launches `process_task()` in a background thread, returns `task_id` immediately
2. `check_progress(task_id)` — reads in-memory `_tasks` dict, returns current phase/subtask/status

### State tracking via shared dict
The Necromancer's `process_task()` accepts an optional `state_tracker: dict = None` parameter. The plugin passes a reference to the `_tasks[task_id]` dict. The Necromancer updates it in-place during execution:
- `phase`: "starting" → "executing" → "subtask 2/3: programming" → "completed"
- `current_subtask`, `total_subtasks`
- `status`: "running" → "completed" / "error"

### SOUL.md update for Raven
The workflow changes from:
```
Listen → Explore → Reason → Formalize → Delegate → Present
```
To:
```
Listen → Explore → Reason → Formalize → Delegate → Monitor (poll check_progress) → Present
```

### Implementation details (plugin v0.3.0)
- `tools.py`: threading.Thread with daemon=True, _tasks dict with _tasks_lock
- `schemas.py`: 3 schemas (DELEGATE_SCHEMA, CHECK_PROGRESS_SCHEMA, READ_FILE_SIMPLE_SCHEMA)
- `__init__.py`: registers 3 tools with ctx.register_tool + post_tool_call hook for logging
- `plugin.yaml`: version 0.3.0, provides_tools lists all 3

## ACP Edit Approval Fix — Zombie Process Pitfall

### The fix
After `new_session()` in `acp_manager.py`, call `set_session_mode("dont_ask", acp_session_id)` to auto-approve file edits for headless Daimon sessions.

### Verification (POST-FIX SESSION)
After gateway restart with the ACP fix applied:
- Single olympus_v3 process running (PID 342351, started 22:04) — no zombies
- Hefesto successfully applied 8 patches across 2 delegation sessions without any "Edit approval denied" errors
- All 5 Python files compiled cleanly: `python3 -m py_compile` passed for revenant.py, necromancer.py, tools.py, schemas.py, __init__.py

### Zombie process issue (from earlier in session)
After applying the fix and restarting the gateway, TWO olympus_v3 server processes were running:
- PID 2343 (started 13:41) — OLD process without the fix
- PID 335895 (started 21:56) — NEW process with the fix

The old process competed for MCP connections, causing "Connection closed" / "Error spawning agent" errors even after the fix was applied. The gateway restart spawned a new process but didn't kill the old one.

**Fix:** Manually kill stale olympus_v3 processes before restarting the gateway:
```bash
ps aux | grep "olympus_v3.server" | grep -v grep
kill <old_pid>
sudo systemctl restart hermes-gateway.service
```

This is a recurring pattern — olympus_v3 zombie processes accumulate across gateway restarts. Always check for and kill stale processes.

## Docker Port Conflict — Open-Wearables Blocking Requiem Dashboard

### Problem
The Requiem dashboard (Vite + React on port 3000, FastAPI on port 3001) was being shadowed by an unrelated Docker compose stack (open-wearables project) that also bound port 3000.

### Diagnosis
- `ss -tlnp | grep 3000` showed Docker-bound socket (not a native process)
- `docker ps` revealed container `frontend__open-wearables` mapping `0.0.0.0:3000->3000/tcp`
- The open-wearables compose stack had 8 services (frontend, backend, db, redis, celery-worker, celery-beat, flower, svix-server) all running from a different project
- Overwolf (Windows app) was also running but was NOT the cause — it's a Windows overlay, not a port competitor

### Fix
```bash
cd "/mnt/c/Users/chris/Desktop/DEVELOPERSPROJECTS/activos/darkarty-mcp/open-wearables"
docker compose down --remove-orphans
```

This stopped and removed ALL containers, networks, and orphans from the open-wearables stack. Port 3000 was freed for the Requiem dashboard.

### Prevention
When multiple projects share a development machine, use distinct ports per project (not all on 3000). Docker compose `down --remove-orphans` is the clean way to tear down a full stack. Check `docker ps` before debugging "why isn't my server on port X working."

## Final State After Session

### Files modified (all compiled clean):
- `necromancer/revenant.py` — REQ-1 auto-fail on syntax errors + f-string fix
- `necromancer/necromancer.py` — REQ-1 execution subtask injection + REQ-4 state_tracker
- `necromancer/shades/programming.md` — REQ-2 efficiency rules
- `raven/plugins/requiem_tools/tools.py` — REQ-4 async delegate + check_progress + REQ-3B read_file_simple
- `raven/plugins/requiem_tools/schemas.py` — 3 schemas
- `raven/plugins/requiem_tools/__init__.py` — 3 tool registrations, v0.3.0
- `raven/plugins/requiem_tools/plugin.yaml` — v0.3.0
- `raven/SOUL.md` — workflow update (Monitor step) + read_file_simple section
- `raven/config.yaml` — graphify MCP block restored (lines 588-595)
- `olympus_v3/acp_manager.py` — ACP edit approval fix (line 251, set_session_mode "dont_ask")
