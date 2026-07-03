# Standalone HERMES_HOME for Project-Specific Agents

## Pattern

When a project needs its own hermes-agent instance (custom persona, custom MCP tools, isolated config), create a standalone HERMES_HOME directory inside the project, separate from the main Aether-Agents home.

## Directory Layout

```
project-root/
├── agent/                    # HERMES_HOME
│   ├── SOUL.md              # Agent identity (system prompt)
│   ├── config.yaml          # Model, provider, MCP servers
│   └── .env                 # API keys
├── mcp/                     # Custom MCP server(s)
│   ├── server.py
│   ├── data.db
│   └── data.json
├── DESIGN.md                # Project documents (not in agent/)
├── RESEARCH.md
└── ...
```

## Why Separate agent/ from project root?

- Keeps HERMES_HOME clean (only config + identity + env)
- MCP server code lives with its data files
- Project documents don't clutter the agent directory
- Clear separation: agent config vs project artifacts

## Launch Command

```bash
HERMES_HOME=/path/to/project/agent hermes chat
```

No wrapper script needed. The venv's `hermes` binary is self-contained (see hermes-agent skill, "Standard Setup Without Wrappers").

## config.yaml Template (LLM Gateway + Custom MCP)

```yaml
model:
  provider: custom:llmgateway   # "custom:" prefix required for custom_providers
  default: deepseek-v4-flash    # "default", NOT "name"
  base_url: https://api.llmgateway.io/v1
  api_mode: chat_completions
  context_length: 128000

custom_providers:
- name: llmgateway
  base_url: https://api.llmgateway.io/v1
  key_env: LLMGATEWAY_API_KEY   # key_env, NOT api_key: ${VAR}
  api_mode: chat_completions
  models:
    deepseek-v4-flash:
      context_length: 128000

mcp_servers:
  project-name:
    command: /path/to/venv/bin/python3.11
    args:
      - /absolute/path/to/mcp/server.py
    enabled: true
    timeout: 60

agent:
  disabled_toolsets:
    - code_execution
```

## Verification Checklist

1. `HERMES_HOME=/path/to/agent hermes config show` — paths point to agent/
2. `HERMES_HOME=/path/to/agent hermes mcp test <name>` — MCP connected, tools discovered
3. `HERMES_HOME=/path/to/agent hermes chat` — agent starts, responds with SOUL.md identity
4. Ask agent to use a tool — tool executes and returns data

## Asclepio Example (2026-06-26)

Migrated from Next.js prototype to hermes-agent + custom MCP:

- HERMES_HOME: `/home/prometeo/Asclepio/agent/`
- MCP server: `/home/prometeo/Asclepio/mcp/server.py`
- MCP tools: `buscar_doctores` (SQLite, 150 doctors), `buscar_cerca` (Google Maps)
- Provider: llmgateway with deepseek-v4-flash
- Venv: shared with Aether-Agents (`/home/prometeo/Aether-Agents/home/.venv-hermes/`)

The venv is shared (same hermes-agent installation), but the HERMES_HOME, config.yaml, SOUL.md, and .env are completely separate. This follows Chris's rule: "PROYECTOS SEPARADOS — NUNCA mezclar perfiles/config/state de un proyecto en el HERMES_HOME de otro."
