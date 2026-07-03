# MCP Subprocess Environment Filtering

## Problem

MCP server's `buscar_cerca` tool (Google Maps Places API) returned "API key not configured" even though `GOOGLE_MAPS_API_KEY` was correctly set in `HERMES_HOME/.env`.

## Root Cause

hermes-agent passes a **filtered environment** to MCP server subprocesses. Variables loaded from `.env` into the main process's `os.environ` are NOT automatically forwarded to MCP subprocesses. Only "safe system vars" pass through.

Source: `hermes_cli/tips.py` line 211:
> "MCP subprocesses receive a filtered environment — only safe system vars pass through."

And line 337:
> "MCP ${ENV_VAR} placeholders in config are resolved at server spawn — including vars from ~/.hermes/.env."

## Fix

Add an `env:` block to the mcp_servers entry in config.yaml:

```yaml
mcp_servers:
  asclepio:
    command: /path/to/python3.11
    args:
      - /path/to/mcp/server.py
    enabled: true
    timeout: 60
    env:
      GOOGLE_MAPS_API_KEY: ${GOOGLE_MAPS_API_KEY}
```

The `${VAR_NAME}` syntax IS expanded in the `env:` block at server spawn time. This is different from `custom_providers.api_key` where `${...}` is NOT expanded (use `key_env` there instead).

## Key Distinction: env block vs key_env

| Mechanism | Where | `${VAR}` expanded? | Purpose |
|-----------|-------|--------------------|---------| 
| `env:` block | mcp_servers | YES | Pass env vars to MCP subprocess |
| `key_env:` | custom_providers | N/A (takes var name, not value) | Resolve provider API key |

## Debugging Steps

1. Check if the tool reads from `os.environ`: `grep "os.environ\|os.getenv" server.py`
2. Verify the key is in `.env`: `xxd HERMES_HOME/.env | grep KEYNAME` (use xxd, not cat — cat sanitizes)
3. Add the `env:` block to config.yaml with `${VAR_NAME}` syntax
4. Restart the agent and test the tool
5. The MCP server subprocess now receives the variable

## Session Context

Discovered while configuring Asclepio (health orientation app for travelers). The MCP server had two tools: `buscar_doctores` (SQLite, worked fine — no env vars needed) and `buscar_cerca` (Google Maps, failed — needed `GOOGLE_MAPS_API_KEY`). The error message was "Google Maps API key no configurada" because `os.environ.get("GOOGLE_MAPS_API_KEY", "")` returned empty string.
