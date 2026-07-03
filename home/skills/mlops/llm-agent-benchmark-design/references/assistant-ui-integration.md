# assistant-ui + Python Backend Integration Guide

How to pair assistant-ui (React/Next.js chat frontend) with a custom Python FastAPI backend that calls an OpenAI-compatible LLM Gateway with tool calling.

## When to Use This Pattern

- You need a visual chat UI for an LLM agent AND programmatic/headless access for benchmarking
- You want full control over the conversation loop (logging, hooks, tool execution) without an opaque agent framework
- You're benchmarking multiple models on the same agent (switch model = one API call, no restart)

## Architecture

```
[assistant-ui React frontend]  ←→  assistant-transport protocol  ←→  [FastAPI Python backend]  ←→  LLM Gateway
         (port 3000)                           assistant-stream              (port 8000)              (OpenAI-compatible)
                                                                                ↓
                                                                        ┌───────────────┐
                                                                        │ - SOUL.md     │
                                                                        │ - Tools (Py)  │
                                                                        │ - Verbatim log│
                                                                        │ - Hooks       │
                                                                        └───────────────┘
```

Two entry points on the same backend:
- `POST /assistant` — streaming (assistant-transport protocol, for the frontend)
- `POST /api/chat` — headless JSON (for benchmark scripts, no UI required)

## Step 1: Scaffold the Frontend

```bash
# NOTE: --yes does NOT exist. Use --use-npm and --skip-install.
npx assistant-ui@latest create frontend --example with-assistant-transport --use-npm --skip-install
cd frontend && npm install
```

The `with-assistant-transport` example is the right template — it uses `useAssistantTransportRuntime` to connect to a custom backend via the assistant-transport protocol.

**Requirements:** Node.js >= 24 (check with `node --version`).

## Step 2: Configure Frontend → Backend URL

Create `frontend/.env.local`:
```
NEXT_PUBLIC_API_URL=http://localhost:8000/assistant
```

The template's `app/MyRuntimeProvider.tsx` reads this via `process.env.NEXT_PUBLIC_API_URL` with a fallback to `http://localhost:8010/assistant`.

## Step 3: Fix the Message Converter (CRITICAL)

The template ships with a LangChain converter that crashes with OpenAI-format messages. You MUST replace it.

**Symptom:** `Runtime TypeError: Cannot read properties of undefined (reading 'role')` at `converter()` in `MyRuntimeProvider.tsx:57`

**What to do in `app/MyRuntimeProvider.tsx`:**

1. Remove these imports:
   ```ts
   // DELETE these:
   import { convertLangChainMessages, type LangChainMessage } from "@assistant-ui/react-langgraph";
   import { unstable_createMessageConverter as createMessageConverter } from "@assistant-ui/react";
   ```

2. Change the State type:
   ```ts
   // FROM: type State = { messages: LangChainMessage[] };
   // TO:
   type State = { messages: Array<{ role: string; content: string }> };
   ```

3. Remove the converter constant:
   ```ts
   // DELETE: const LangChainMessageConverter = createMessageConverter(convertLangChainMessages);
   ```

4. Rewrite the converter function to use `fromThreadMessageLike`:
   ```ts
   import { fromThreadMessageLike } from "@assistant-ui/react";

   const converter = (state: State, connectionMetadata: AssistantTransportConnectionMetadata) => {
     const optimisticMessages = connectionMetadata.pendingCommands
       .map((c) => {
         if (c.type === "add-message") {
           const text = c.message.parts
             .map((p) => (p.type === "text" ? p.text : ""))
             .join("\n");
           return { role: "user" as const, content: text };
         }
         return null;
       })
       .filter(Boolean);

     const allMessages = [...(state.messages || []), ...optimisticMessages];
     return {
       messages: allMessages.map((m: any) =>
         fromThreadMessageLike({
           role: m.role === "assistant" ? "assistant" : "user",
           content: [{ type: "text", text: typeof m.content === "string" ? m.content : JSON.stringify(m.content) }],
         })
       ),
       isRunning: connectionMetadata.isSending || false,
     };
   };
   ```

5. Verify: `npx tsc --noEmit` — must pass with 0 errors.

## Step 4: Build the Python Backend

Install the `assistant-stream` Python library (v0.0.34+, from the assistant-ui monorepo or PyPI):
```bash
pip install assistant-stream openai fastapi uvicorn python-dotenv
```

Backend structure (see `references/asclepio-motor-v2.md` for the full built example):
- `main.py` — FastAPI with `POST /assistant` (streaming via `DataStreamResponse`) + `POST /api/chat` (headless JSON)
- `llm.py` — OpenAI client + tool calling loop (max 10 iterations)
- `tools.py` — Plain Python functions (NOT MCP), TOOL_DEFINITIONS as OpenAI function schemas
- `soul.py` — Load system prompt from file
- `logger.py` — Verbatim JSON logging of every LLM call
- `hooks.py` — Pre/post-turn hooks (empty by default, filled for benchmark)
- `config.py` — API keys, model switching, paths

## Step 5: Customize the Theme

### Force dark mode
In `app/layout.tsx`, add `className="dark"` to `<html>`:
```tsx
<html lang="es" className="dark">
```

### Medical dark theme colors (OKLCH)
In `app/globals.css`, replace `:root` values:
```css
:root {
  --background: oklch(0.14 0.02 240);        /* deep dark blue-teal */
  --card: oklch(0.19 0.025 240);             /* slightly lighter */
  --primary: oklch(0.68 0.15 175);           /* medical teal */
  --accent: oklch(0.72 0.17 155);            /* medical green */
  --destructive: oklch(0.65 0.22 25);        /* alarm red */
  --border: oklch(0.5 0.02 240 / 15%);       /* subtle teal */
  --muted-foreground: oklch(0.65 0.015 240); /* gray-blue text */
  --ring: oklch(0.55 0.12 175);              /* teal focus ring */
}
```

### Welcome message
In `components/assistant-ui/thread.tsx`, find `"How can I help you today?"` and replace with your text (e.g., `"¿Cómo puedo ayudarte?"`).

### Suggestions
In `app/page.tsx`, replace the `Suggestions([...])` array with your own prompts.

## Step 6: Start Everything

```bash
# Terminal 1: Backend
cd backend && uvicorn main:app --host 0.0.0.0 --port 8000

# Terminal 2: Frontend
cd frontend && npm run dev

# Open: http://localhost:3000
```

## Verify End-to-End

```bash
# Health check
curl http://localhost:8000/health
# → {"status":"ok","model":"gpt-5.5"}

# Headless API test
curl -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "Hola", "model": "gpt-5.5"}'
# → {response, tool_calls_made, usage, timing, model_used}

# Streaming endpoint test
curl -N -X POST http://localhost:8000/assistant \
  -H "Content-Type: application/json" \
  -d '{"commands":[{"type":"add-message","message":{"role":"user","parts":[{"type":"text","text":"Hola"}]}}],"state":{"messages":[]},"tools":{},"runConfig":{}}'
# → aui-state:... + 0:"text..." + aui-state:...
```

## CORS

The backend must have CORS enabled for `http://localhost:3000`:
```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_methods=["*"],
    allow_headers=["*"],
)
```

## Model Switching (Runtime, No Restart)

```bash
curl -X POST http://localhost:8000/api/model \
  -H "Content-Type: application/json" \
  -d '{"model": "claude-opus-4-8"}'
```

## Common Pitfalls

| Pitfall | Symptom | Fix |
|---------|---------|-----|
| LangChain converter | `Cannot read properties of undefined (reading 'role')` | Replace with `fromThreadMessageLike` (Step 3) |
| `--yes` flag | `error: unknown option '--yes'` | Use `--use-npm --skip-install` instead |
| Wrong base_url | HTTP 401 from LLM Gateway | Verify against working agent's config.yaml |
| No `.env.local` | Frontend falls back to port 8010 | Create `frontend/.env.local` with `NEXT_PUBLIC_API_URL` |
| Missing CORS | Frontend can't reach backend | Add CORSMiddleware for localhost:3000 |
| Node version | Build errors | Need Node >= 24 |
