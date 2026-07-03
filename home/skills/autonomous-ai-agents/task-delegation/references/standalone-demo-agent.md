# Standalone Demo Agent Pattern

When you need a custom conversational agent for a demo/prototype (e.g., a health assistant, a customer service bot, a domain-specific chatbot), create a standalone Hermes agent profile in a dedicated directory.

## When to Use

- Product demo for a client (show how the final product would converse)
- Prototyping a system prompt before building the full app
- Testing conversation flow and tone without backend/frontend

## Directory Structure

Keep the agent profile and project documents SEPARATE:

```
/home/prometeo/Asclepio/              ← project documents only
  DESIGN.md
  RESEARCH.md
  INFORME-VIABILIDAD.md
  PROMPT-PRESENTACION.md
  README-DEMO.md

/home/prometeo/asclepio-agent/        ← agent profile + runtime
  SOUL.md                              ← system prompt (identity, rules, flow)
  config.yaml                          ← model, provider, toolsets
  .env                                 ← API keys
  (runtime files created automatically on first run)
```

## Files to Create

### SOUL.md
The system prompt. Define:
- Agent identity (name, role, what it does)
- Hard rules (what it NEVER does)
- Conversation flow (numbered steps)
- Tone and language style
- Mandatory disclaimers (if applicable)
- Alarm/escalation conditions (if applicable)

### config.yaml
```yaml
agent:
  name: <agent-name>
  role: <role-description>
  description: "<short description>"
  capabilities:
    - receives_from
  launch_command: "hermes chat"
  keep_alive: true

model:
  api_mode: chat_completions
  default: <model>
  provider: <provider>
  base_url: <url>

toolsets:
  - web
  - vision

display:
  personality: none

max_iterations: 40

approvals:
  mode: 'off'

plugins:
  enabled: []
```

### .env
Copy from an existing working profile (e.g., Hefesto's .env) to reuse API keys.

## Launch Command

```bash
HERMES_HOME=/home/prometeo/<agent-dir> hermes chat
```

## Key Lessons

1. **NEVER point HERMES_HOME at a project document directory** — it will pollute it with runtime files (state.db, sessions/, logs/, skills/, models_dev_cache.json at 2.3MB, etc.)
2. **Copy .env from a known-working profile** to avoid key issues
3. **Set `personality: none`** in config to prevent kawaii default overlay
4. **Set `plugins: enabled: []`** for demo agents — no need for olympus_v3 or aether hooks
5. **Test the demo yourself** before presenting — verify the agent responds with the right tone, follows the conversation flow, and includes disclaimers
6. **For medical/legal/sensitive domains**: include mandatory disclaimers in SOUL.md as explicit text the agent must output, plus alarm conditions that trigger immediate escalation
