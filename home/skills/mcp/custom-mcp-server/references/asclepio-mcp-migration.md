# Asclepio MCP Server — Session Notes (2026-06-26)

## Context

Asclepio is a health orientation chatbot for travelers (project for Sergio/Solsoft). Started as a Next.js prototype using the llmgateway-templates ai-chatbot template with Vercel AI SDK. After hitting tool-calling protocol issues (AI SDK v6 broken, v7 works but DeepSeek V4 ignores tools), Chris decided to migrate back to hermes-agent with a custom MCP server.

## Migration: Next.js → Hermes Agent + MCP

### What was preserved:
- System prompt (medical persona, conversation flow, disclaimers) → migrated to `agent/SOUL.md` (4,763 bytes)
- 150 fictitious doctors (JSON → SQLite via `init_db()`)
- LLM Gateway API key → `agent/.env`

### What was discarded:
- Entire Next.js app (route.ts, page.tsx, package.json, node_modules, .next, test scripts)
- AI SDK tool-calling workarounds (system prompt injection, protocol flags)
- Frontend components (chat UI, ApiKeyProvider, markdown rendering CSS)

### What was added:
- Custom MCP server (`mcp/server.py`) with FastMCP
  - `buscar_doctores`: SQLite query by city + specialty, fallback to general practitioners
  - `buscar_cerca`: Google Maps Places API (Nearby Search, 5km radius, top 10 results)
- `agent/config.yaml` with llmgateway provider + asclepio MCP registered
- SOUL.md updated to reference MCP tools (Paso 6: canalización, Paso 7: farmacias cercanas)

## MCP Server Implementation Details

- Uses `FastMCP` from `mcp.server` (not low-level `Server`/`stdio_server`)
- DB auto-creates from `doctors.json` on first run via `init_db()`
- Google Maps tool gracefully handles missing API key (returns clear error JSON)
- All tool returns are `json.dumps(..., ensure_ascii=False)` strings
- External HTTP via `urllib.request` (stdlib only, no `requests`/`httpx`)
- Python: `/home/prometeo/Aether-Agents/home/.venv-hermes/bin/python3.11` (shared venv, mcp SDK installed)

## Verification Results

- `hermes mcp test asclepio`: Connected in 654ms, 2 tools discovered
- `hermes config show`: Paths correct (Config: agent/config.yaml, Secrets: agent/.env)
- DB query: 150 doctors in 32 cities confirmed

## First Live Test (2026-06-26)

### Three config bugs found and fixed

The agent was created by Hefesto but failed to start on first launch. Three config.yaml errors, all in the custom_provider setup:

1. **`model.name` → `model.default`**: hermes-agent reads `model.default` for the model name, not `model.name`. Using `name` produced an empty model at runtime → HTTP 400 "Requested model  not supported".

2. **`provider: llmgateway` → `provider: custom:llmgateway`**: Custom providers must be referenced with the `custom:` prefix in `model.provider`. Without it, `hermes doctor` reported "not a recognised provider" and the runtime couldn't resolve the API key.

3. **`api_key: ${LLMGATEWAY_API_KEY}` → `key_env: LLMGATEWAY_API_KEY`**: hermes-agent does NOT expand `${...}` variables in the `api_key` field. Use `key_env` to point at the environment variable name. The runtime calls `os.getenv(key_env)`.

4. **API key typo**: The .env had `llmgtw_` instead of `llmgtwy_` (missing "y"). Verified by comparing `xxd` output between Asclepio's .env and Aether-Agents' .env byte-by-byte. Even after fixing the config format, the 401 persisted until the key itself was corrected.

### Debugging approach

- `hermes doctor` revealed the provider recognition issue immediately
- `hermes mcp test asclepio` confirmed MCP was working (not the problem)
- `curl` to the API endpoint with the key directly confirmed the key was bad
- `xxd` byte-level comparison caught the single-character typo that visual diff missed

### Successful test result

After all fixes, the agent responded correctly:
- Identified itself as Asclepio (medical orientation assistant)
- Asked diagnostic follow-up questions (pain type, intensity, other symptoms)
- Invoked `buscar_doctores` MCP tool to find a doctor in Guadalajara
- Returned Dr. Sandra Vargas Reyes from the SQLite database
- Offered to search nearby pharmacies (requiring lat/lng from user)

Test session ran via tmux: `tmux new-session -d -s asclepio` + `HERMES_HOME=/home/prometeo/Asclepio/agent /home/prometeo/Aether-Agents/home/.venv-hermes/bin/hermes chat`

## Pending

- Google Maps API key needs to be set in `agent/.env` (placeholder `TU_API_KEY_AQUI`)
- No git remote configured for the project
- `buscar_cerca` untested with real API key
