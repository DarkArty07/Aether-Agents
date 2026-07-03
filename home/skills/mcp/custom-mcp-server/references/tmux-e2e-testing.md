# E2E Testing of Conversational Agents via tmux

Pattern for end-to-end testing of a hermes-agent instance with MCP tools,
using tmux as the terminal multiplexer. No browser needed — the agent
runs in a tmux pane and you interact via `send-keys` + `capture-pane`.

## When to Use

- After building/configuring a custom MCP server + hermes-agent instance
- After changing config.yaml, .env, or server.py
- After fixing env var passing or API key issues
- Smoke testing before demoing to user

## Setup: Spawn Agent in tmux

```bash
# Kill any existing session, start fresh
tmux kill-session -t myagent 2>/dev/null
tmux new-session -d -s myagent -x 140 -y 50

# Launch hermes-agent with the project's HERMES_HOME
tmux send-keys -t myagent "HERMES_HOME=/path/to/agent /path/to/venv/bin/hermes chat" Enter

# Wait for startup (6-8s typically)
sleep 8

# Verify it's ready
tmux capture-pane -t myagent -p | tail -10
# Should show the welcome banner and a ❯ prompt
```

## Sending Test Messages

```bash
# Send a message
tmux send-keys -t myagent "your test message here" Enter

# Wait for response (25-40s for deepseek-v4-flash with MCP tool calls)
sleep 35

# Capture the response
tmux capture-pane -t myagent -p | tail -50
```

## Test Scenario Design

Design 5-7 scenarios that cover:

1. **Primary tool — normal case** — e.g., "find pharmacies near lat/lng"
2. **Secondary tool — normal case** — e.g., "find doctors in [city]"
3. **Multi-turn conversation** — follow up on scenario 1 with symptoms/details
4. **Escalation/urgency** — "pain is now 9/10, find hospitals"
5. **Edge case — international location** — test Google Maps outside home country
6. **Edge case — missing data** — request specialty/city not in the database
7. **Context retention** — verify agent remembers details from earlier turns

## Verification Checklist per Scenario

For each scenario, verify:

- [ ] Agent called the correct MCP tool (look for `⚡ preparing mcp_<name>_<tool>…`)
- [ ] Tool returned real data (not error JSON)
- [ ] Agent synthesized the data naturally (not raw JSON dump)
- [ ] Response tone matches the situation (urgent for emergencies, calm for routine)
- [ ] Agent included relevant disclaimers (e.g., "this is not a medical diagnosis")
- [ ] Context from previous turns is retained
- [ ] No HTTP 401/400 errors in the output

## Common Failure Modes

| Symptom | Cause | Fix |
|---------|-------|-----|
| HTTP 401 "Invalid API token" | LLMGATEWAY_API_KEY corrupted in .env (often by Hefesto writing sanitized `***` value) | Verify with `xxd .env \| grep LLMGATEWAY` — key must start with `llmgtwy_rWzS`. If corrupted, restore from source .env using Hefesto with `patch` (NOT execute_code). See custom-mcp-server pitfall "Hefesto corrupts .env files" |
| "API key not configured" in tool response | MCP subprocess didn't receive env var | Add `env:` block in config.yaml mcp_servers section |
| Tool returns results but wrong specialty (e.g., "no cardiologists" when one exists) | Model passes specialty parameter differently than stored, or SQLite LIKE Unicode case sensitivity | Check what the model actually passed to the tool. SQLite LIKE is case-insensitive for ASCII but NOT for Unicode (á, é, ñ). Use `LOWER(specialty) LIKE LOWER(?)` for Spanish |
| Tool not called (agent says "I can't") | MCP server not connected | Run `HERMES_HOME=/path hermes mcp test <name>` |
| Agent responds but ignores tool results | SOUL.md doesn't mention the tools | Add tool descriptions to SOUL.md |
| `tmux capture-pane` shows truncated output | Pane height too small | Use `-y 50` or higher when creating session |

## Cleanup

```bash
tmux kill-session -t myagent 2>/dev/null
```

## Context Window Monitoring

Watch the context usage line at the bottom of the pane:
```
⚕ deepseek-v4-flash │ 25.7K/128K │ [██░░░░░░░░] 20% │ 5m │ ⏲ 11s
```

- Under 30% after 6+ messages = efficient context use (good)
- Over 50% after 3 messages = possible context bloat (check SOUL.md length)
- If context fills up, the agent may lose early conversation context

## Example: Full 6-Scenario E2E Run

Session: Asclepio (health orientation agent for travelers)
Agent: deepseek-v4-flash, 128K context
Tools: buscar_doctores (SQLite), buscar_cerca (Google Maps)

| # | Scenario | Tool | Result | Notes |
|---|----------|------|--------|-------|
| 1 | Pharmacies in CDMX Condesa | buscar_cerca | PASS | 4 real pharmacies with addresses + ratings |
| 2 | Cardiologists in Guadalajara | buscar_doctores | PASS (with bug) | Said "no cardiologists" but one EXISTS in BD (Dra. Claudia Ramírez Vargas, Cardiología, Guadalajara). Graceful fallback to GP was good UX, but tool missed a real match. Likely cause: model passes `specialty` as "cardiologo" or "cardiologia" and SQLite LIKE doesn't match "Cardiología" (Unicode accent mismatch). Fix: use `LOWER(specialty) LIKE LOWER(?)` in the SQL query. |
| 3 | Multi-turn stomach pain triage | (conversation) | PASS | Identified gastritis 70%, recommended omeprazol, recalled pharmacies from #1 |
| 4 | Emergency: hospitals near Condesa | buscar_cerca | PASS | 4 real hospitals, prioritized nearest, safety instructions |
| 5 | Pharmacies in Madrid, Spain | buscar_cerca | PASS | 4 real Madrid pharmacies, added local context (green cross symbol) |
| 6 | Neurosurgeon in Merida (not in DB) | buscar_doctores | PASS | No crash, suggested alternatives (Google Maps, hospitals, insurance) |

Context at end: 25.7K/128K (20%) across 6 messages — efficient.
Avg response time: 7-14s per message.
