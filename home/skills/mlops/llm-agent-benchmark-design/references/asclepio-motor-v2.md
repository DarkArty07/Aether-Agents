# Asclepio Motor v2 — Built Implementation

**Location:** `/home/prometeo/Asclepio-Motor/`
**Built:** 2026-07-01
**Status:** Working end-to-end (frontend + backend + LLM + tools + logging)

## What It Is

A custom LLM conversation engine for Asclepio (health triage agent for travelers). Replaces the hermes-agent-based Asclepio with a transparent, controllable motor that has:
- assistant-ui React frontend (chat UI with streaming, markdown, tool call rendering)
- FastAPI Python backend (LLM calls, tool execution, verbatim logging, hooks)
- Dual endpoints: streaming for UI + headless JSON for benchmark scripts
- No hermes-agent, no MCP server, no tmux

## Startup Commands

```bash
# Terminal 1: Backend (port 8000)
cd /home/prometeo/Asclepio-Motor/backend
uvicorn main:app --host 0.0.0.0 --port 8000

# Terminal 2: Frontend (port 3000)
cd /home/prometeo/Asclepio-Motor/frontend
npm run dev

# Open: http://localhost:3000
```

## API Endpoints

### POST /assistant (streaming, for frontend)
Receives assistant-transport protocol commands, streams responses back via `assistant-stream`.
```json
{
  "commands": [{"type": "add-message", "message": {"role": "user", "parts": [{"type": "text", "text": "Hola"}]}}],
  "state": {"messages": []},
  "tools": {},
  "runConfig": {}
}
```

### POST /api/chat (headless, for benchmarking)
```bash
curl -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "Estoy en Merida, tengo diarrea", "model": "gpt-5.5"}'
```
Returns: `{response, tool_calls_made, usage, timing, model_used}`

### POST /api/model (runtime model switch)
```bash
curl -X POST http://localhost:8000/api/model \
  -H "Content-Type: application/json" \
  -d '{"model": "claude-opus-4-8"}'
```

### GET /health
Returns: `{"status": "ok", "model": "gpt-5.5"}`

## Backend Files (9 total)

| File | Purpose | Lines |
|------|---------|-------|
| `main.py` | FastAPI server, 4 endpoints, CORS | ~250 |
| `llm.py` | OpenAI client + tool calling loop (max 10 iter) | ~200 |
| `tools.py` | buscar_doctores (SQLite), buscar_cerca (Maps), TOOL_DEFINITIONS | ~300 |
| `soul.py` | Load/cache SOUL.md system prompt | ~30 |
| `logger.py` | Verbatim JSON logging per LLM call + conversation JSONL | ~90 |
| `hooks.py` | Pre/post-turn hooks (empty by default) | ~80 |
| `config.py` | API keys, model switching, paths | ~70 |
| `requirements.txt` | openai, fastapi, uvicorn, python-dotenv, assistant-stream | 5 |
| `__init__.py` | Package marker | 1 |

## LLM Gateway

- URL: `https://api.llmgateway.io/v1` (OpenAI-compatible)
- API key: from `.env` (LLMGATEWAY_API_KEY)
- Default model: `gpt-5.5`
- 12 benchmark models registered (see llm-model-benchmarking skill for model matrix)

## Tools (Plain Python Functions, NOT MCP)

### buscar_doctores(city, specialty="")
- Queries SQLite `doctors.db` (150 doctors, 32 cities MX, 8 specialties)
- Fallback to Medicina General if specialty not found
- Returns JSON: `{success, doctors: [{name, specialty, city, state, address, phone, schedule, rating, languages}]}`

### buscar_cerca(lat, lng, tipo)
- Google Maps Places API (nearbysearch, radius 5000m, language es)
- Type mapping: farmacia→pharmacy, hospital→hospital, clinica→doctor
- Returns top 10: `{success, places: [{name, address, rating, lat, lng}]}`

## Hooks System

```python
# In hooks.py — starts EMPTY, filled when benchmark design is ready
pre_turn_hooks = []   # [(messages, model) -> messages]
post_turn_hooks = []  # [(response, tool_calls, usage, timing) -> None]

register_pre_turn(my_scoring_function)
register_post_turn(my_safety_gate)
```

## Verbatim Logging

Each LLM call (including intermediate tool-calling iterations) saved as:
- `data/logs/{timestamp}_{model}.json` — full request/response with all messages, tool calls, usage, timing
- Also maintains `data/logs/conversation_{session_id}.jsonl` — one line per interaction

## Frontend (assistant-ui)

- Scaffolded via: `npx assistant-ui@latest create frontend --example with-assistant-transport --use-npm`
- Config: `.env.local` with `NEXT_PUBLIC_API_URL=http://localhost:8000/assistant`
- `MyRuntimeProvider.tsx` uses `useAssistantTransportRuntime` hook
- **CONVERTER FIX APPLIED:** Template's LangChain converter replaced with `fromThreadMessageLike` from `@assistant-ui/react` to handle OpenAI-format messages. Without this, frontend crashes with `Cannot read properties of undefined (reading 'role')`. See `references/assistant-ui-integration.md` Step 3.
- **DARK MEDICAL THEME APPLIED:** `globals.css` has dark OKLCH palette (blue-teal background, medical teal primary, green accent, alarm red). `layout.tsx` forces `className="dark"`. Header: ⚕️ Asclepio + "Orientación en Salud para Viajeros". Welcome: "¿Cómo puedo ayudarte?". Suggestions in Spanish.
- The frontend renders tool calls as visual cards, streams text responses, supports markdown

## What's NOT Here (Deferred to Benchmark Phase)

- Scoring rubric (D1-D6) — Chris designs the benchmark, hooks get filled later
- Safety gates — same, filled when benchmark design arrives
- Convergence tracking (T_orient, T_otc, T_tools) — same
- Test case runner script — built when benchmark cases are defined

## User Preferences (Chris)

- Does NOT want to test/debug frontend himself — orchestrator handles all testing
- Wants programmatic access (hooks) to manipulate the agent as if a user
- Designs the benchmark in parallel while the motor is being built
- The motor is left clean/functional; benchmark measurement hooks are added later
