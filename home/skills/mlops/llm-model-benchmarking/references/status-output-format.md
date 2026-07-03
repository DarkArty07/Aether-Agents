# /status Output Format (Observed 2026-06-30, hermes-agent v0.15.2)

## After 0 messages (fresh session)

```
Hermes CLI Status

Session ID: 20260630_135100_9476ee
Path: ~/Asclepio/agent
Model: gpt-5.5 (custom:llmgateway)
Created: 2026-06-30 13:51
Last Activity: 2026-06-30 13:51
Tokens: 0
Agent Running: No

Session recap — 20260630
  (nothing to recap — no messages yet)
```

## After 1 user message + 1 assistant response

```
Hermes CLI Status

Session ID: 20260630_135100_9476ee
Path: ~/Asclepio/agent
Title: Evaluación inicial de malestar
Model: gpt-5.5 (custom)
Created: 2026-06-30 13:51
Last Activity: 2026-06-30 13:51
Tokens: 32,589
Agent Running: No

Session recap — Evaluación inicial de malestar
  Recent: 1 user turn / 2 assistant replies, 1 tool result
  Tools used: skill_view×1
  Last ask: hola, me siento mal
  Last reply: Hola, siento que te estés sintiendo mal. Estoy contigo. Primero
necesito descartar algo urgente: ¿tienes alguno de estos síntomas ahorita? ...
```

## Status Bar Format

The bottom status bar of the hermes TUI shows real-time metrics:

```
 ⚕ gpt-5.5 │ 16.8K/128K │ [█░░░░░░░░░] 13% │ 40s │ ⏲ 10s
```

| Segment | Example | Meaning |
|---------|---------|---------|
| `⚕ gpt-5.5` | Model name | Current model in use |
| `16.8K/128K` | Context tokens / max context | Current context window usage |
| `[█░░░░░░░░░] 13%` | Progress bar | Context window percentage |
| `40s` | Session timer | Total time since session start |
| `⏲ 10s` | Response timer | Time of last LLM response (wall clock) |

## Key Observations

1. **Tokens field is cumulative** — shows total tokens for the entire session, not per-turn
2. **`/status` includes tool usage** — `Tools used: skill_view×1` shows which tools were called
3. **Session title is auto-generated** — useful for identifying what the conversation was about
4. **"Agent Running: No"** — confirms the agent finished processing (not still generating)
5. **Context bar updates in real-time** — can be read from the status bar even without `/status`
6. **First turn has high token cost** — 32,589 tokens for a single "hola, me siento mal" because the system prompt, SOUL.md, skills, and MCP tool definitions all count as prompt tokens
7. **Skill auto-loading** — the agent loaded `travel-health-orientation` skill automatically, adding to token count. This is expected behavior when skills match the conversation topic.

## Parsing Tips for Automated Benchmarking

When capturing tmux output programmatically:

```python
# Extract token count from /status output
import re
match = re.search(r'Tokens:\s*(\d+)', status_output)
total_tokens = int(match.group(1)) if match else None

# Extract context usage from status bar
match = re.search(r'(\d+\.?\d*)K/(\d+)K', status_bar)
context_tokens_k, max_tokens_k = match.groups() if match else (None, None)

# Extract last response time from status bar
match = re.search(r'⏲\s*(\d+)s', status_bar)
last_response_seconds = int(match.group(1)) if match else None

# Extract tools used
match = re.search(r'Tools used:\s*(.+)', status_output)
tools_str = match.group(1) if match else "none"
```
