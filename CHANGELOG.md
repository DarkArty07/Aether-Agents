# Changelog

All notable changes to Aether Agents are documented here.

## [5.0.0] - 2026-05-07

### 🔥 Breaking Change: ACP → Pi Agent RPC

All 5 Daimons (Hefesto, Etalides, Ariadna, Athena, Daedalus) now use **Pi Agent RPC** instead of Hermes Agent's ACP protocol for sub-agent communication. ACP remains available as instant rollback (`backend: acp` in config).

### Why This Change

ACP had 3 critical bugs that made Daimon delegation unreliable:

1. **Spinner noise (Bug A):** ACP's `AgentThoughtChunk` mixed kawaii progress indicators with substantive reasoning. A regex filter tried to separate them but leaked Unicode spinners (ಠ_ಠ), inflating `substantive_thoughts` and making stall detection unreliable.

2. **Tool calls invisible (Bug B):** `total_tool_calls` was always `0` even when the Daimon executed 8+ tools. The ACP event stream never emitted tool execution events, making it impossible to distinguish a working agent from a frozen one.

3. **No reasoning visibility (Bug C):** Provider chain-of-thought (DeepSeek `reasoning_content`, Anthropic `thinking`) was never forwarded. LLMs that stream via thoughts had their reasoning lost entirely, causing empty responses from Daimons.

These bugs meant Daimon sessions could: stall for minutes with zero output, complete work but report no tool calls, or return empty responses when the LLM used the thoughts channel exclusively.

### What Pi Agent RPC Solves

| Feature | ACP (old) | Pi RPC (new) |
|---------|-----------|---------------|
| Event protocol | ACP binary (spinner noise) | Typed JSONL (text_delta, thinking_delta, tool_call) |
| Tool calls | Always 0 (Bug B) | Explicit `tool_execution_start/end` events |
| Reasoning visibility | None (Bug C) | `thinking_delta` events, configurable via `set_thinking_level` |
| Spinner filtering | Regex whitelist (leaks) | Not needed — events are typed |
| Steering (live intervention) | None | `steer` command mid-stream |
| Thinking levels | None | `off/minimal/low/medium/high/xhigh` |
| Session persistence | None | Built-in with `--session-dir` |
| Model switching | Restart required | `set_model` at runtime |
| Compaction | Manual | `compact` + auto-compaction |

### New: `delegate` Action (Single-Call Auto-Poll)

The biggest UX improvement: `delegate` replaces the entire open→message→poll→close cycle with one MCP call.

**Before (10-20 tool calls, LLM-driven polling):**
```
open(agent) → session_id
message(session_id, prompt) → active
poll(session_id) → active ... (repeat 8-15 times)
poll(session_id) → done
close(session_id) → closed
```

**After (1 tool call, server-driven polling):**
```
delegate(agent, prompt, poll_interval=15, timeout=300) → done
```

The MCP server handles polling internally with `asyncio.sleep(poll_interval)`. Parameters:
- `poll_interval`: seconds between polls (default 15, min 1)
- `timeout`: max seconds to wait (default 300, max 600)

Returns final result with `delegate: {timed_out, elapsed_seconds, poll_iterations}` metadata. On timeout: returns last known state WITHOUT closing session (allows manual follow-up).

Manual `open/message/poll/close` actions remain available for fine-grained control.

### Architecture

- **Hermes** continues using Hermes Agent (orchestrator with MCP, memory, skills)
- **Daimons** now use Pi Agent RPC (headless subprocess, `@mariozechner/pi-coding-agent`)
- **Olympus v2** MCP server bridges the two — same `talk_to` interface, different backend
- **Per-agent backend** in `config.yaml`: `backend: pi_rpc` (default) or `backend: acp` (rollback)
- **Pi configs** at `home/.pi-daimons/{name}/.pi/` with SYSTEM.md, settings.json, extensions

### 5 Optimizations to Olympus MCP v2 Server

1. **Buffer reset timing fix (CRITICAL):** Moved from `_action_poll` (after done) to `_action_message` (before new prompt). Prevents losing the final response between polls.

2. **Response truncation (HIGH):** Responses >4000 chars auto-truncate with `response_truncated: true` + `response_total_length` metadata. Prevents MCP token overflow.

3. **Progress metadata (MEDIUM):** `progress` field in every poll: `{total_thoughts, substantive_thoughts, total_messages, total_tool_calls, elapsed_seconds}`. Enables stall detection.

4. **Better error messages (MEDIUM):** Distinct `"expired"` (process terminated) vs `"unknown"` (never existed) session errors.

5. **Tool name fallbacks (LOW):** Chain: `name` → `toolName` → `function.name` → `"unknown"`. Fixed empty tool names in `tool_calls_detail`.

### SOUL.md Reinforcement (Hermes Orchestrator)

Hermes' SOUL.md received 4 surgical patches establishing orchestrator identity:

1. **HARD RULES** (§1): Never edit configs, never write SYSTEM.md, never execute implementation commands, never work >2 turns without delegating, never bypass Daimons, never poll >5 times without reporting.
2. **Delegation checkpoint** (§2): Mandatory check before starting any task — "Can a Daimon do this?"
3. **Expanded anti-patterns** (§12): 6 new rows covering config editing, SYSTEM.md writing, implementation, answering+implementing, solo architecture decisions, session close skipping.
4. **Known issues update** (§13): GLM-5.1 AgentThoughtChunk, LLM delegation reluctance, workflow MCP timeout, personality override, platform_toolsets override.

### All 5 Daimons Migrated

| Daimon | Backend | Tools | Thinking | Status |
|--------|---------|-------|----------|--------|
| Hefesto | pi_rpc | read/write/edit/bash/grep/find/ls | medium | ✅ Production |
| Etalides | pi_rpc | read/write/edit/bash/grep/find/ls | medium | ✅ Production |
| Ariadna | pi_rpc | read/write/edit/bash | medium | ✅ Production |
| Athena | pi_rpc | read/write/edit/bash/grep/find/ls | high | ✅ Production |
| Daedalus | pi_rpc | read/write/edit/bash/grep/find/ls | medium | ✅ Production |

### 10 Bugs Fixed (Olympus V2 Development)

| # | Bug | Fix |
|---|-----|-----|
| A | auth.json `${ENV_VAR}` not resolved | Hardcode real key, extension reads process.env |
| B | `--provider` validated before extension loads | Use settings.json instead of CLI flags |
| C | `--cwd` CLI flag doesn't exist in Pi | Use `subprocess.Popen(cwd=...)` |
| D | registerProvider models[] requires per-model apiKey | Remove models[], let Pi auto-discover via /v1/models |
| E | No stderr reader thread | Added _stderr_reader() daemon |
| F | OPENCODE_GO_API_KEY not in subprocess env | Added _load_dotenv() to read AETHER_HOME/.env |
| G | event_translator didn't handle Pi's JSONL format | Rewrote for assistantMessageEvent nesting |
| H | Server deleted session before draining events | Drain buffer on process death |
| I | agent_end killed Pi process with --session-dir | Reset buffer for next turn, keep process alive |
| J | `arguments` vs `args` NameError in _action_delegate | Fixed parameter name in route handler |

### Files Changed

- `src/olympus_v2/server.py` — delegate action, buffer reset, truncation, progress metadata, error messages
- `src/olympus_v2/event_translator.py` — tool name fallbacks, progress metadata builder
- `src/olympus_v2/pi_adapter.py` — get_state, multi-turn fixes, session-dir support
- `home/profiles/hermes/SOUL.md` — HARD RULES, delegation checkpoint, anti-patterns
- `home/.pi-daimons/ariadna/` — Pi config (SYSTEM.md, settings.json, extension)
- `home/.pi-daimons/athena/` — Pi config (SYSTEM.md, settings.json, extension)
- `home/.pi-daimons/daedalus/` — Pi config (SYSTEM.md, settings.json, extension)
- `home/.pi-daimons/etalides/` — Pi config (SYSTEM.md, settings.json, extension)
- `.gitignore` — Removed old profile-level pi-daimons entry
