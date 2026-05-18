# Olympus v3 - Implementation Plan

## Overview

Replace Olympus v2 (Pi Agent RPC) with v3 (ACP + Plugin hooks + SQLite). Single implementation, no phases.

**Design doc:** src/olympus_v3/DESIGN.md
**Codebase:** src/olympus_v3/
**Legacy v2 code:** Removed in v0.8.1 (src/olympus_v2/ deleted)
**Existing v1 code:** git commit 732f60f, src/olympus/ (acp_client.py 450+ lines reusable)

## Implementation Order

Dependencies determine order. Each task has a verification gate before proceeding.

T1: db.py --------------------------------|
                                           |
T2: acp_manager.py -----------------------|
                                           |
T3: olympus_v3_hooks/ --------------------|  <- depends on T1 schema
                                           |
T4: server.py ----------------------------|  <- depends on T1, T2, T3
                                           |
T5: consult_action.py --------------------|  <- depends on T1, T4
                                           |
T6: Migrate config -----------------------|  <- depends on T4 working
                                           |
T7: Test integration ----------------------|  <- end-to-end
                                           |
T8: Restore write restrictions -----------+

---

## T1: db.py - SQLite Database

**File:** src/olympus_v3/db.py
**Estimated:** ~200 lines
**Dependencies:** None (foundation)
**Based on:** v2 consulting_db.py pattern (aiosqlite, auto-create, WAL mode)

### Acceptance Criteria
- 4 tables created: sessions, turns, tool_calls, steering
- WAL mode enabled on connection
- Path configurable via OLYMPUS_DB_PATH env var
- Default path: $HERMES_HOME/.olympus/olympus_v3.db
- All methods are async (aiosqlite)
- insert_session(), insert_turn(), insert_tool_call(), upsert_session_status()
- consume_steering() - reads and marks consumed in one transaction
- get_session_progress() - returns thoughts, messages, tool_calls counts + status
- get_latest_turn() - returns last assistant turn content + reasoning
- Indexes on session_id + turn_num, session_id + consumed
- Auto-creates .olympus/ directory if missing
- Connection pool / context manager pattern

### Schema (from DESIGN.md)
    sessions: session_id (PK), agent, status, started_at, completed_at, metadata
    turns: turn_id (auto), session_id (FK), turn_num, role, content, reasoning, timestamp, metadata
    tool_calls: call_id (PK), session_id (FK), turn_id (FK), tool_name, arguments, result, status, timestamp
    steering: session_id (FK), directive, priority, consumed, timestamp

---

## T2: acp_manager.py - ACP Session Manager

**File:** src/olympus_v3/acp_manager.py
**Estimated:** ~350 lines
**Dependencies:** None (uses ACP protocol, independent of db.py)
**Based on:** v1 src/olympus/acp_client.py (commit 732f60f)

### Key Changes from v1
- REMOVE session_update() and all streaming/callback code (AgentThoughtChunk, AgentMessageChunk)
- REMOVE SessionState registry (replaced by SQLite)
- ADD OLYMPUS_SESSION_ID and OLYMPUS_DB_PATH as env vars injected at spawn
- CHANGE poll() to read from SQLite instead of ACP events
- CHANGE discover() to use profiles.get_profile_dir() instead of .pi/ configs

### Acceptance Criteria
- spawn_agent(profile, session_id=None) - spawns hermes -p <profile> with ACP + env vars
- send_message(session_id, message) - sends prompt to ACP session
- poll(session_id) - reads from db.get_session_progress() + db.get_latest_turn()
- close(session_id) - terminates process, updates session status
- cancel(session_id) - force-terminates stuck process
- discover() - lists profiles from ~/.hermes/profiles/
- Uses agent-client-protocol package for ACP communication
- Process lifecycle managed via subprocess (start, track PID, cleanup on exit)
- Session ID generated via uuid4 if not provided

---

## T3: olympus_v3_hooks/ - Plugin Package

**Directory:** src/olympus_v3/olympus_v3_hooks/
**Files:** __init__.py, hooks.py
**Estimated:** ~150 lines total
**Dependencies:** T1 (db.py schema)

### Acceptance Criteria
- register(ctx) function that registers 4 hooks
- on_post_llm_call() - INSERT into turns table (content, reasoning, tokens)
- on_post_tool_call() - INSERT into tool_calls table (call_id, tool_name, args, result)
- on_session_end() - UPDATE sessions status to completed + completed_at
- on_pre_llm_call() - SELECT steering WHERE consumed=0, returns directive string or None, marks consumed
- All hooks read OLYMPUS_SESSION_ID and OLYMPUS_DB_PATH from env vars
- All hooks use SYNC sqlite3 (not aiosqlite) - hooks run inside the agent process, not async
- Plugin package installable into ~/.hermes/profiles/<daimon>/plugins/olympus_v3/

### Key Decision: SYNC vs ASYNC
Hooks run inside the hermes-agent process at specific lifecycle points. The plugin system calls hooks synchronously. Use sqlite3 (not aiosqlite) for hooks. The MCP server uses aiosqlite because it runs in an async event loop.

---

## T4: server.py - MCP Server

**File:** src/olympus_v3/server.py
**Estimated:** ~600 lines
**Dependencies:** T1 (db.py), T2 (acp_manager.py)

### Acceptance Criteria
- MCP server runs via stdio (same as v2)
- Tool: talk_to with actions: open, message, poll, close, cancel, delegate
- Tool: discover - lists available Daimon profiles
- Tool: consult with actions: start, run, sign, add_agent, status, complete
- talk_to delegate action = open + message + auto-poll loop (same pattern as v2)
- talk_to poll reads from SQLite (db.get_session_progress), NOT from ACP events
- talk_to response includes: thoughts, messages, tool_calls, status, response text
- consult reuses consulting logic from v2 but reads SQLite instead of SessionBuffer
- Config loaded from AETHER_HOME env var (same as v2)
- main() entry point for python -m olympus_v3.server
- Proper logging with olympus_v3 logger name

### Server Architecture
    MCP stdio -> server.py
                    |-- acp_manager.py (subprocess lifecycle)
                    |-- db.py (SQLite reads/writes)
                    +-- consult_action.py (consult workflow)

---

## T5: consult_action.py - Consult Workflow

**File:** src/olympus_v3/consult_action.py
**Estimated:** ~500 lines (migrated from v2, simplified)
**Dependencies:** T1 (db.py), T4 (server.py for talk_to)

### Key Changes from v2
- REMOVE PiAdapter dependency - use acp_manager instead
- REMOVE SessionBuffer - read from SQLite via db.get_session_progress()
- REMOVE translate_events_batch - responses come from db.get_latest_turn()
- KEEP consulting_db schema (sessions, agent_consultations, tasks) - stays as-is
- KEEP natural language prompt template (CONSULT_PROMPT_TEMPLATE)
- KEEP READ-ONLY mode restriction for consultants

### Acceptance Criteria
- All 6 actions work: start, run, sign, add_agent, status, complete
- run uses acp_manager.delegate() to send prompt to consultant Daimon
- Response extraction reads from SQLite turns table (not SessionBuffer)
- sign action reads consultant response from SQLite
- consulting_db stays SQLite at <project_root>/.eter/.consulting/consulting.db
- ROLE_LABELS, ROLE_DESCRIPTIONS, ROLE_LEVELS constants preserved from v2

---

## T6: Migration - Config and Plugin Setup

**Dependencies:** T4 (server.py working)

### Steps
1. CREATE src/olympus_v3/__init__.py and pyproject.toml entry point
2. COPY consulting_db.py from v2 (unchanged - independent SQLite DB)
3. COPY config_loader.py from v2, modify: remove Pi-specific config, add v3 config (db_path, profiles_dir, poll_interval)
4. UPDATE pyproject.toml scripts entry: olympus-v3 = olympus_v3.server:main
5. INSTALL plugin into each Daimon profile: ~/Aether-Agents/home/profiles/<daimon>/plugins/olympus_v3/
6. UPDATE Hermes config: Remove v2 MCP server, add v3 MCP server
7. TEST that hermes sees the v3 tools (talk_to, discover, consult)

### Acceptance Criteria
- python -m olympus_v3.server starts without errors
- MCP tools appear in Hermes tool list after config update
- Plugin loads in at least one Daimon profile (test with hermes -p hefesto)
- v2 MCP server deactivated in config (not deleted, just enabled: false)

---

## T7: Integration Testing

**Dependencies:** T6 complete

### Test Sequence
1. db.py unit test - create session, insert turns, poll progress, consume steering
2. acp_manager test - spawn a Daimon profile, send message, close
3. Plugin test - verify hooks write to SQLite when Daimon processes a turn
4. End-to-end test - talk_to(agent=hefesto, action=delegate, prompt=List files in /tmp) through Hermes
5. Consult test - consult(action=start, plan=..., agents=[daedalus]) through Hermes
6. Stall detection - verify that poll detects stuck sessions and reports correctly

### Acceptance Criteria
- Daimon spawns, processes prompt, writes to SQLite via hooks
- Hermes polls and reads full turn content from SQLite
- Session completes with on_session_end writing completed status
- Steering works: write directive -> Daimon reads it on next turn via pre_llm_call
- Consult workflow starts, runs, and closes sessions correctly

---

## T8: Restore Write Restrictions

After T7 passes:
1. ADD BACK file-write to disabled_toolsets in Hermes config
2. RESTORE pre_tool_call hook with block-write-commands.sh
3. RESTART Hermes (/reset or hermes gateway restart)
4. VERIFY write tools are blocked again

---

## Files to Create

| File | Lines (est) | Based on |
|------|-------------|----------|
| src/olympus_v3/__init__.py | 10 | New |
| src/olympus_v3/db.py | 200 | v2 consulting_db.py pattern |
| src/olympus_v3/acp_manager.py | 350 | v1 acp_client.py |
| src/olympus_v3/olympus_v3_hooks/__init__.py | 5 | New |
| src/olympus_v3/olympus_v3_hooks/hooks.py | 150 | New (plugin API) |
| src/olympus_v3/server.py | 600 | v2 server.py |
| src/olympus_v3/consult_action.py | 500 | v2 consult_action.py |
| src/olympus_v3/consulting_db.py | 694 | v2 (copy, unchanged) |
| src/olympus_v3/config_loader.py | 200 | v2 (modify) |
| **Total** | **~2,700** | |

## Files Removed (v0.8.1 cleanup)

| File | Lines | Reason |
|------|-------|--------|
| src/olympus_v2/pi_adapter.py | 438 | Replaced by acp_manager.py |
| src/olympus_v2/event_translator.py | 549 | Replaced by SQLite + hooks |
| src/olympus_v2/soul_to_system.py | 163 | Daimons use hermes-agent SOUL.md |
| src/olympus_v2/config_loader.py | 257 | Replaced by v3 config_loader |

**Kept:** consulting_db.py (moved to v3 unchanged)

## Delegation Strategy

Previous delegations to Hefesto failed due to vague prompts. New approach:
1. Provide exact code in the prompt - not write X but write this exact code to this exact file
2. One file per delegation - focused, concrete, with file path and content
3. Verify after each - read file, run imports, confirm it loads
4. If Hefesto fails again - implement directly (write restriction is lifted)

---

## Implementation Status (Updated 2026-05-09)

✅ T1: db.py (643 lines) - COMPLETE
✅ T2: acp_manager.py (572 lines) - COMPLETE
✅ T3: olympus_v3_hooks/ (297 lines) - COMPLETE
✅ T4: server.py (424 lines) - COMPLETE
✅ T5: consult_action.py (677 lines) - COMPLETE
✅ T6: Migration (config + plugins) - COMPLETE
✅ T7: Integration testing - COMPLETE
✅ T8: Restore write restrictions - COMPLETE

**Total:** 2,792 lines implemented
**Status:** Production-ready (T1-T8 complete)
**Completed improvements:**
- M3: Stale session cleanup (cleanup_stale_sessions methods in OlympusDB + OlympusDBSync)
- M4: DB path unification (AETHER_HOME priority in hooks.py)
- Plugin installed in 6 Daimon profiles
- Gateway tested, DB tables verified, MCP server registered

**Commits:**
- f3dfc07: feat: olympus v3 implementation (T1-T7)
- 4582119: PLAN.md update
- 153e0d3: fix: restore write restrictions (T8)
- eb3ff1f: feat: olympus v3 improvements - stale session cleanup + DB path unification
