# Olympus v3 Data Model — Inter-Agent Communication

Database location: `{AETHER_HOME}/.olympus/olympus_v3.db` (shared across all Daimon profiles).
Current live data (as of v0.11.1): 102 sessions, 111 turns, 1192 tool_calls, 2 steering directives across 4 agents (hefesto, ariadna, etalides, daedalus).

## Schema

### sessions

| Column | Type | Description |
|--------|------|-------------|
| session_id | TEXT PK | UUID, e.g. `507d1106-8799-4e1d-b93a-3f5d2ec1bfd0` |
| agent | TEXT NOT NULL | Daimon name: hefesto, ariadna, etalides, daedalus, athena, ictinus |
| status | TEXT | `active`, `completed`, `error`, `cancelled` |
| started_at | REAL | Unix timestamp |
| completed_at | REAL | Unix timestamp (NULL if active) |
| metadata | TEXT | JSON blob |

### turns

| Column | Type | Description |
|--------|------|-------------|
| turn_id | INTEGER PK AUTOINCREMENT | Auto-incremented |
| session_id | TEXT FK | References sessions |
| turn_num | INTEGER NOT NULL | Sequential turn number |
| role | TEXT NOT NULL | `user`, `assistant`, `system` |
| content | TEXT | Full response text (can be large) |
| reasoning | TEXT | Chain-of-thought / reasoning content |
| timestamp | REAL NOT NULL | Unix timestamp |
| metadata | TEXT | JSON: `{"model": "glm-5.1", "platform": "acp"}` |

### tool_calls

| Column | Type | Description |
|--------|------|-------------|
| call_id | TEXT PK | Tool call ID or fallback `tool_{timestamp_ms}` |
| session_id | TEXT FK | References sessions |
| turn_id | INTEGER FK | References turns |
| tool_name | TEXT NOT NULL | e.g. `read_file`, `patch`, `terminal`, `write_file` |
| arguments | TEXT | JSON-serialized tool arguments |
| result | TEXT | Tool result (truncated at 10KB by hooks) |
| status | TEXT | `pending`, `completed` |
| timestamp | REAL NOT NULL | Unix timestamp |

### steering

| Column | Type | Description |
|--------|------|-------------|
| id | INTEGER PK AUTOINCREMENT | Auto-incremented |
| session_id | TEXT FK | References sessions |
| directive | TEXT NOT NULL | Injected text for Daimon context |
| priority | INTEGER | Higher = more important (default 0) |
| consumed | INTEGER | 0=pending, 1=delivered (consumed by pre_llm_call hook) |
| timestamp | REAL NOT NULL | Unix timestamp |

## Indexes

- `idx_turns_session_turn` on `turns(session_id, turn_num)`
- `idx_tool_calls_session` on `tool_calls(session_id)`
- `idx_steering_session_consumed` on `steering(session_id, consumed)`

## Data Flow

```
Hermes (orchestrator)
  → talk_to(action="open")     → ACPManager.spawn_agent() → sessions INSERT
  → talk_to(action="message")   → ACPManager.send_message() → .olympus_session.{PID} written
  → talk_to(action="delegate") → open + message + poll loop

Daimon (hermes-agent process)
  → pre_llm_call hook    → reads steering directives → injects [Olympus Steering] context
  → post_llm_call hook   → writes turn (content + reasoning) to turns table
  → post_tool_call hook  → writes tool call + result to tool_calls table
  → on_session_end hook  → updates session status to completed/cancelled/error

Hermes (poll loop)
  → talk_to(action="poll") → reads from SQLite via get_session_progress()
```

## Poll Response Shape

`get_session_progress()` returns:

```json
{
  "thoughts": 3,           // count of assistant turns
  "messages": 2,           // count of turns with content
  "tool_calls": 10,        // count of tool calls
  "status": "active",      // active/completed/error/cancelled
  "last_turn": "...",       // latest assistant content (truncated)
  "last_reasoning": "...",  // latest reasoning content
  "recent_tool_calls": [    // last 5, newest first
    {"tool_name": "patch", "arguments_truncated": "...(200 chars)", "status": "completed", "timestamp": 1234.5}
  ],
  "clarification_needed": false,  // regex check for "CLARIFICATION NEEDED" in last_turn
  "heartbeat_timestamp": 1234.5   // max(turns.timestamp) for session
}
```

## Session ID Resolution (in hooks)

Priority: `OLYMPUS_SESSION_ID` env var → `.olympus_session.{PID}` file → `.olympus_session` file

## DB Path Resolution

Priority: `OLYMPUS_DB_PATH` env → `{AETHER_HOME}/.olympus_db_path` file → `get_db_path()` fallback

Current canonical path: `{AETHER_HOME}/.olympus/olympus_v3.db` (AETHER_HOME-based for cross-profile sharing).

## Async vs Sync

- **OlympusDB** (async): used by `server.py` MCP server (runs in asyncio event loop)
- **OlympusDBSync** (sync): used by plugin hooks (run inside hermes-agent process, synchronous callbacks)
- Both read/write to the same SQLite file with WAL mode enabled
- Async side runs `PRAGMA wal_checkpoint = TRUNCATE` before reads to ensure fresh data

## aether.db (separate, project-level)

Location: `{PROJECT_ROOT}/.aether/aether.db`
Purpose: Project state, not session observability.

| Table | Purpose |
|-------|---------|
| hot_state | Single-row project snapshot (phase, task, blockers) |
| sessions | Per-Daimon session history (request, result_summary, model, platform) |
| file_changes | File write/patch/commit tracking per session |
| decisions | Architectural decisions (title, rationale, alternatives, status) |
| issues | Blockers and errors (description, resolution, status) |

Note: `aether.sessions` and `olympus_v3.sessions` are DIFFERENT tables in DIFFERENT databases. The aether one stores project-level summaries (request, result_summary); the olympus one stores per-turn observability data (content, reasoning, tool_calls).

## Existing Visualization Commands

```
hermes sessions list       # List recent sessions from hermes-agent's own SQLite
hermes sessions browse     # Interactive session picker
hermes sessions stats      # Session store statistics
hermes insights            # Token usage, costs, tool patterns, activity trends
hermes dashboard           # Web UI on port 9119
hermes dashboard --tui     # In-browser chat tab
```

These operate on hermes-agent's internal session store (`~/.hermes/sessions/` or profile-specific), NOT on olympus_v3.db. The olympus observability data has no CLI viewer yet — this is the v0.12.0 gap.

## Agent Session Counts (current)

| Agent | Sessions |
|-------|----------|
| hefesto | 59 |
| ariadna | 21 |
| athena | 11 |
| etalides | 9 |
| daedalus | 2 |

## Content Size Characteristics

- Turn content: varies, can be 200-5000+ chars per turn
- Tool call arguments: JSON-serialized, 50-500 chars typically
- Tool call results: truncated at 10KB by hooks, raw results can be much larger
- Poll `arguments_truncated`: first 200 chars of arguments
- MCP tool `max_bytes`: 50K default (configurable per tool in config.yaml)
- Model output: glm-5.1 has 32K output tokens (~90K chars), unlikely to be the bottleneck