# Ariadna: Function Agent Architecture

## Key Insight

Ariadna is NOT a normal Daimon. She is a **function agent** — invoked programmatically by the `aether_curate` MCP tool, not by Hermes via `delegate`.

This distinguishes her from Daimons like Hefesto, Etalides, Daedalus, and Athena, which are **session agents** invoked via `talk_to(action="delegate")`.

## How aether_curate Invokes Ariadna

The invocation chain in `src/olympus_v3/server.py` (`_handle_aether_curate`):

1. Read raw data from `aether.db` (hot_state, recent_sessions, recent_files, decisions, issues)
2. Build a prompt string with format rules **hardcoded in Python** (5 sections, max 1500 chars, no JSON, etc.)
3. Spawn Ariadna via ACP: `manager.spawn_agent(agent_name="ariadna")`
4. Send the constructed prompt: `manager.send_message(session_id, prompt)`
5. Close the session: `manager.close_session(session_id)`
6. Return confirmation to Hermes

The format rules are **duplicated** between server.py (lines building the prompt) and SOUL.md (§4). The server.py prompt is the authoritative source — it's what the model actually sees.

## What Ariadna Actually Needs

| Item | Pre-v0.10.2 (obsolete) | Post-v0.10.2 (current) |
|------|------------------------|------------------------|
| role | `project-manager` | `context-curator` |
| description | Spanish PM description | English Context Curator description |
| capabilities | project-tracking, blocker-detection, session-audit, sprint-tracking | receives_from, context-curation, synthesis |
| toolsets | file, terminal, memory, session_search, todo, clarify | **file + skills** only |
| level | 2 | 1 |
| model | kimi-k2.5 | kimi-k2.5 (unchanged) |

Only `file` is needed because:
- `terminal` — not needed, Ariadna doesn't run commands
- `memory` — not needed, no conversational continuity between curations
- `session_search` — not needed, data comes from aether.db, not past sessions
- `todo` — not needed, Ariadna doesn't manage tasks
- `clarify` — doesn't exist as a hermes-agent toolset (was never implemented)

## v0.10.2 Rework — COMPLETED

- config.yaml.template: minimal toolsets (file + skills), correct role/description/capabilities, level 1 ✅
- SOUL.md: mostly fine (73 lines), added clarifying note about programmatic invocation ✅
- Hermes SOUL.md: verified §4, §6, §7 references remain accurate ✅

## Future Architecture: Direct Model API Call (v0.11.0+, NOT STARTED)

Replace the ACP invocation in server.py (`spawn_agent → send_message → close_session`) with a direct model API call (`client.chat.completions.create`).

**Three tiers of Ariadna evolution:**

| Version | Change | Risk | Impact |
|---------|--------|------|--------|
| v0.10.2 (done) | Clean config to match reality | Low | Config reflects actual role |
| v0.11.0+ (future) | Remove ACP, call model directly | Medium | +50x speed (2-5s vs 1-2min), -1 profile |
| v0.12.0+ (far future) | `aether_curate` as native Python function, no MCP roundtrip | High | Redesign of server.py |

**Complexity of direct API call:**
- server.py needs an HTTP client (or `openai` library) — currently no model dependencies
- API key management: spawn_agent inherits from profile; direct call needs explicit key handling
- Observability loss: no plugin hooks (olympus_v3), no aether.db session tracking
- Format rules would live only in server.py (single source, no SOUL.md duplication)

## The Format Rules Duplication Problem

Server.py hardcodes the format rules (5 sections, max 1500 chars, etc.) in the prompt it sends to Ariadna. The SOUL.md also has these rules. They are semantically identical but maintained in two places. This is acceptable because:
1. Server.py is the authoritative source (the model sees it)
2. SOUL.md serves as identity documentation for agent discovery
3. If they diverge, server.py wins (the model gets that prompt, not SOUL.md)

## The Bigger Pattern: Two Invocation Modes

| Mode | Invocation | Session | Example |
|------|-----------|---------|---------|
| **Delegate** | Hermes calls `talk_to(action="delegate")` | Multi-turn, persistent | Hefesto, Etalides, Daedalus, Athena, Ictinus |
| **Function** | MCP tool spawns agent programmatically | Single-turn, auto-closed | Ariadna (via `aether_curate`) |

Function agents are a subclass worth recognizing in the Agent Type Taxonomy. They have different constraints:
- No need for `memory`, `session_search`, `todo`, `clarify`
- Minimal toolsets (only what the function requires)
- SOUL.md rules may be redundant with the calling code's prompt
- Level 1 (simple, single-purpose)
- Never invoked via `delegate` — the MCP tool constructs and sends the prompt, then auto-closes the session