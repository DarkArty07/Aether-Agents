# Conversation Engine Architecture

## Context

During Asclepio LLM benchmark design (2026-07-01), two approaches were evaluated and rejected before arriving at the recommended architecture.

## Rejected Approach 1: hermes-agent Framework

**What:** Used hermes-agent (the same framework that runs Asclepio in production) to drive benchmark conversations via tmux.

**Why it failed:**
- Opaque request/response cycle: the framework handles LLM calls internally; you can't intercept the raw API request and response for verbatim logging
- tmux `capture-pane` gives terminal fragments, not structured conversation data
- `/status` gives approximate token counts, not exact per-turn usage from the API response
- No hooks between turns: can't embed evaluation logic (scoring, safety gates) at the conversation layer
- Switching models requires editing `config.yaml` + killing/restarting the tmux session — error-prone and slow across 12 models x 5 cases

**Lesson:** Agent frameworks are designed for production use, not benchmarking. They optimize for user experience (streaming, retries, tool abstraction) at the cost of observability. For benchmarking you need the opposite: full observability, no abstraction.

## Adapted Approach: assistant-ui as Frontend + Custom Python Backend

**What:** github.com/assistant-ui/assistant-ui — MIT-licensed React/TypeScript library for building chat interfaces.

**Initial assessment (wrong):** Initially rejected because it's "just a frontend library" with no LLM integration. The Python backend components return static mock responses.

**User correction:** Chris said "pero yo si quiero frontend, si la necesito" — he WANTS a visual chat UI, not just a headless engine. This changed the architecture: use assistant-ui for the frontend, build a custom Python backend for the engine.

**What assistant-ui provides:**
- Production-grade React chat UI (streaming, markdown, tool call rendering, auto-scroll, attachments)
- `assistant-stream` Python library (v0.0.34) — streaming protocol bridge between React frontend and Python backend
- `assistant-transport` protocol — the frontend sends `AddMessageCommand`/`AddToolResultCommand`, backend streams responses back
- MIT license, actively maintained (Y Combinator backed)

**What we built (the custom backend):**
- FastAPI server with dual endpoints (see "Dual-Endpoint Architecture" below)
- Uses `assistant-stream`'s `create_run()`, `RunController`, `DataStreamResponse` for the streaming endpoint
- Uses `openai` library for LLM Gateway API calls (OpenAI-compatible)
- Tools as plain Python functions (not MCP server): `buscar_doctores` queries SQLite, `buscar_cerca` calls Google Maps API
- Verbatim logging of every LLM request/response
- Pre/post-turn hooks system (empty by default, filled when benchmark design is ready)
- Runtime model switching via `POST /api/model`

**Lesson:** Don't reject a library because it doesn't do everything. If it does ONE thing well (frontend UI), use it for that and build the rest. The dual-endpoint pattern lets you have both human-facing UI and script-facing API on the same engine.

## Built Architecture: Dual-Endpoint Engine (Asclepio Motor v2)

### Overview

A Python FastAPI backend + assistant-ui React frontend. The backend has TWO endpoints sharing the same core engine: one for the UI (streaming), one for benchmarking (headless JSON). No hermes-agent, no MCP server, no tmux.

### Directory Structure (actual built implementation)

```
/home/prometeo/Asclepio-Motor/
├── frontend/              # assistant-ui (Next.js, scaffolded via CLI)
│   ├── .env.local         # NEXT_PUBLIC_API_URL=http://localhost:8000/assistant
│   └── app/
│       ├── MyRuntimeProvider.tsx  # useAssistantTransportRuntime hook
│       └── toolkit.tsx           # Frontend tool definitions (render only)
├── backend/               # FastAPI Python (the engine)
│   ├── main.py            # 4 endpoints: /assistant, /api/chat, /health, /api/model
│   ├── llm.py             # OpenAI client + tool calling loop (max 10 iterations)
│   ├── tools.py           # buscar_doctores (SQLite), buscar_cerca (Maps API)
│   ├── soul.py            # Loads SOUL.md as system prompt (cached)
│   ├── logger.py          # Verbatim JSON logging per LLM call
│   ├── hooks.py           # Pre/post-turn hooks (empty by default)
│   ├── config.py          # API keys, model switching, paths
│   └── requirements.txt   # openai, fastapi, uvicorn, python-dotenv, assistant-stream
├── data/
│   ├── SOUL.md            # System prompt
│   ├── doctors.db         # SQLite database
│   └── logs/              # Verbatim transcripts ({timestamp}_{model}.json)
└── .env                   # LLMGATEWAY_API_KEY, GOOGLE_MAPS_API_KEY
```

### Dual-Endpoint Pattern (the key architectural insight)

**Endpoint 1: POST /assistant** (for the frontend UI)
- Implements the assistant-transport protocol
- Receives `{commands: [{type: "add-message", message: {role, parts}}], state}`
- Streams responses back using `assistant-stream`'s `DataStreamResponse`
- The frontend (assistant-ui React) renders streaming text, tool calls, markdown
- CORS enabled for localhost:3000

**Endpoint 2: POST /api/chat** (for benchmarking/scripts)
- Headless JSON API — no streaming, no UI
- Receives `{message: str, model?: str, history?: [{role, content}]}`
- Returns `{response, tool_calls_made, usage, timing, model_used}`
- This is what benchmark scripts call to simulate user turns programmatically
- Eliminates the need for tmux or manual interaction

**Both endpoints share:**
- Same SOUL.md system prompt (loaded once, cached)
- Same tool definitions (OpenAI function schemas)
- Same LLM client (openai library, LLM Gateway base_url)
- Same verbatim logger (every request/response saved to data/logs/)
- Same hooks system (pre/post-turn callbacks)

### Tool Calling Loop (in llm.py)

1. Load system prompt from SOUL.md
2. Run pre-turn hooks (can modify messages)
3. Call `client.chat.completions.create(model, messages, tools=TOOL_DEFINITIONS)`
4. If response has `tool_calls`:
   - For each tool_call: execute the function (buscar_doctores → SQLite, buscar_cerca → Maps API)
   - Append tool results to messages as `{role: "tool", tool_call_id, content}`
   - Call LLM again with updated messages (loop)
   - Repeat until no more tool_calls (max 10 iterations safety limit)
5. Run post-turn hooks (can register scoring/metrics)
6. Log everything verbatim to data/logs/{timestamp}_{model}.json
7. Return: `{content, tool_calls_made, usage, timing, raw_response}`

### Verbatim Logging Format

Each LLM call (including intermediate tool-calling iterations) is logged as a separate JSON file:
```json
{
  "timestamp": "20260701T231012_546727",
  "model": "gpt-5.5",
  "timing_seconds": 19.31,
  "messages": [
    {"role": "system", "content": "<full SOUL.md>"},
    {"role": "user", "content": "Estoy en Merida, tengo diarrea..."},
    {"role": "assistant", "content": null, "tool_calls": [...]},
    {"role": "tool", "tool_call_id": "call_...", "content": "{\"success\": true, ...}"},
    {"role": "assistant", "content": "Claro. Siento que estés pasando por eso..."}
  ]
}
```

### Hooks System (in hooks.py)

```python
pre_turn_hooks = []   # callables: (messages, model) -> messages
post_turn_hooks = []  # callables: (response, tool_calls, usage, timing) -> None

def register_pre_turn(fn): pre_turn_hooks.append(fn)
def register_post_turn(fn): post_turn_hooks.append(fn)
```

Hooks start EMPTY. When the benchmark design is ready, register scoring functions, safety gates, convergence trackers, etc. The engine doesn't need to know what the hooks do — it just calls them at the right time.

### Model Switching

Runtime model switch via API:
```
POST /api/model {"model": "claude-opus-4-8"} → {"status": "ok", "model": "claude-opus-4-8"}
```
No config file edits, no restart. The headless endpoint also accepts `model` per-request.

### How to Start

```bash
# Terminal 1: Backend
cd /home/prometeo/Asclepio-Motor/backend
uvicorn main:app --host 0.0.0.0 --port 8000

# Terminal 2: Frontend
cd /home/prometeo/Asclepio-Motor/frontend
npm run dev

# Open: http://localhost:3000
```

### Dependencies

```
openai            # LLM Gateway API client (OpenAI-compatible)
fastapi           # Web framework
uvicorn           # ASGI server
python-dotenv     # Load .env for API keys
assistant-stream  # Streaming protocol bridge (assistant-transport)
sqlite3           # Standard library (doctor database)
```

Frontend: Node >= 24, Next.js 16+, React 19+, assistant-ui packages.
