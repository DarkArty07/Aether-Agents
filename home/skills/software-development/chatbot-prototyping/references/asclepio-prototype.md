# Asclepio Prototype — Session Notes (2026-06-25)

> **⚠️ APPROACH REVERSED (2026-06-26):** Chris decided to abandon the Next.js web template and migrate back to hermes-agent with a custom MCP server. The web template approach hit AI SDK tool-calling protocol issues (v6 broken, v7 works but DeepSeek V4 ignores tools). The Next.js app was deleted. See the `custom-mcp-server` skill and `references/asclepio-mcp-migration.md` in that skill for the current approach. The notes below are preserved for historical context and for the template adaptation patterns that may still be useful.

## Project Context

Asclepio: health orientation app for travelers. When someone gets sick in an unfamiliar city, they don't know what they have, don't know local doctors, don't know what medicine to take or where to buy it. Asclepio solves this with a conversational AI that:
1. Chats with the user (asks determining questions like a doctor's first review)
2. Gives preliminary orientation with probability percentages (NOT diagnoses)
3. Suggests OTC medications
4. Locates nearby pharmacies (Google Places API)
5. Refers to local doctors from a curated network

Client: Sergio (Solsoft). Chris is the developer. Target market: Mexico initially.

## Project Layout

- `/home/prometeo/Asclepio/` — project documents (DESIGN.md, RESEARCH.md, INFORME-VIABILIDAD.md, PROMPT-PRESENTACION.md, README-DEMO.md, Asclepio_Viabilidad.pptx)
- `/home/prometeo/asclepio-agent/` — hermes-agent CLI demo (SOUL.md, config.yaml, .env) — used for the presentation prototype, now superseded by web template approach
- `/home/prometeo/Asclepio/app/` — (planned) Next.js web prototype from template

## Architecture Decision (2026-06-25)

Chris decided to migrate from hermes-agent CLI demo to a Next.js web template:
- Template: github.com/theopenco/llmgateway-templates/tree/main/templates/ai-chatbot
- Reason: hermes-agent is too heavy for prototype needs ("500,000 líneas de código")
- Principle: system prompt + chat UI is all that's needed; tools connect incrementally as API endpoints
- Provider: LLM Gateway (api.llmgateway.io) — Chris chose LLM Gateway over OpenCode Go for the prototype. Template's `@llmgateway/ai-sdk-provider` works out of the box.
- System prompt: Asclepio SOUL.md (copied to /home/prometeo/Asclepio/SOUL.md before deleting asclepio-agent/)

## Template Analysis (llmgateway-templates/ai-chatbot)

- **Framework**: Next.js 16 (App Router), React 19, Tailwind CSS 4, shadcn/ui
- **AI**: Vercel AI SDK (`streamText` + `useChat`), LLM Gateway Provider
- **API**: Single route POST /api/chat — takes `{messages, model}`, returns SSE text stream
- **System prompt**: Hardcoded generic "You are a helpful, friendly assistant"
- **Model selector**: 19 models (OpenAI, Anthropic, Google, xAI, DeepSeek, Meta, Mistral)
- **Auth**: API key via header `x-api-key` or env `LLMGATEWAY_API_KEY`
- **Deploy**: Vercel one-click

### Key source files:
- `src/app/api/chat/route.ts` — LLM call (streamText), system prompt, provider init
- `src/app/page.tsx` — Chat UI (useChat, message bubbles, model selector, clear button)
- `src/components/api-key-provider.tsx` — API key dialog/state
- `.env.example` — just `LLMGATEWAY_API_KEY=***`

## Adaptation Plan

1. Clone template to /home/prometeo/Asclepio/app
2. Swap `@llmgateway/ai-sdk-provider` → `@ai-sdk/openai` with OpenCode Go base URL
3. Inject Asclepio SOUL.md as system prompt in route.ts
4. Update model selector (deepseek-v4-flash as default, plus kimi, glm)
5. Create doctors DB: JSON with fake Mexican doctors (Guadalajara, CDMX, Monterrey — general, cardiólogo, traumatólogo, etc.)
6. Add endpoint GET /api/doctors?city=X&specialty=Y
7. (Later) Add Google Places endpoint GET /api/pharmacies?lat=X&lng=Y

## Open Questions
- Default model for chat: deepseek-v4-flash (used in demo) — pending Chris confirmation
- API key source: from asclepio-agent/.env or direct from Chris — pending confirmation
- Google Places API key: not yet obtained — will add later as separate endpoint

---

## Implementation Notes (2026-06-25 Execution)

### What Actually Changed vs Plan

| Plan Step | Actual | Reason |
|-----------|--------|--------|
| 2. Swap provider | **Skipped** — kept `@llmgateway/ai-sdk-provider` | Chris chose LLM Gateway (not OpenCode Go). Template already had the provider; accepts any model via `model` parameter |
| 4. Default model | Changed to `deepseek-v4-flash` (root ID, no prefix) | LLM Gateway coding plans reject provider prefixes. Added DeepSeek V4 Flash & Pro. Stripped ALL prefixes from template's MODELS array + added cleanModel safety net in route.ts |
| 7. Google Places | Not started | Deliberately deferred |

### Files Deleted
- `/home/prometeo/asclepio-agent/` (entire directory)
- `/home/prometeo/Asclepio/sandboxes/`
- `/home/prometeo/Asclepio/README-DEMO.md`
- `Asclepio_Viabilidad.pptx:Zone.Identifier` (Windows sidecar)

### Files Created/Modified
- `/home/prometeo/Asclepio/SOUL.md` — copied from asclepio-agent/
- `/home/prometeo/Asclepio/app/` — cloned from llmgateway-templates/ai-chatbot
- `src/app/api/chat/route.ts` — system prompt replaced with full SOUL.md body as template literal
- `src/app/page.tsx` — title "Asclepio", empty state "¿Qué te trae por aquí?", placeholder "Escribe tu mensaje...", added DeepSeek V4 Flash & Pro models
- `.env.example` — value changed to `***`
- `.gitignore` — node_modules, .next, .env.local, *.tsbuildinfo, next-env.d.ts
- `data/doctors.json` — 17 fictitious doctors (6 GDL, 6 CDMX, 5 MTY, 8 specialties)
- `src/app/api/doctors/route.ts` — GET with ?city=&specialty= filtering

### Key Technique: Multi-line System Prompt Injection
Used a JavaScript template literal (backtick string) to embed the 78-line SOUL.md directly in `route.ts`. Avoids needing to read from a file at runtime and keeps the prompt visible in the route handler.

### Doctors DB Distribution
- **Guadalajara (6)**: Medicina General, Cardiología, Traumatología, Dermatología, Pediatría, Medicina Interna
- **CDMX (6)**: Medicina General, Gastroenterología, Neurología, Medicina Interna, Cardiología, Traumatología
- **Monterrey (5)**: Medicina General, Dermatología, Gastroenterología, Pediatría, Neurología

### Status
- ✅ Template cloned and adapted
- ✅ Doctors API working (17 fictitious doctors, 3 cities, 8 specialties)
- ✅ LLM Gateway API key configured (.env.local)
- ✅ npm install completed (414 packages — pnpm not available, npm works fine)
- ✅ Dev server running (localhost:3000, `npm run dev`)
- ✅ Chat working — Asclepio responds with correct system prompt (identity, disclaimer, determining questions, Mexican Spanish tone)
- ✅ LLM Gateway prefix issue fixed (root model IDs + cleanModel safety net)
- ⏳ Google Places endpoint future
- ✅ Model selector reduced to 2: DeepSeek V4 Flash + DeepSeek V4 Pro (Chris asked to remove all others)
- ✅ "Powered by LLM Gateway" badge removed from UI (import + JSX deleted)
- ✅ Tool calling wired: `buscar_doctores` tool in route.ts with `inputSchema` (AI SDK v6)
- ✅ Streaming protocol switched from text to data stream (`toUIMessageStreamResponse()` + `maxSteps: 3`) for tool support
- ✅ System prompt updated: Paso 6 now says "Canaliza con doctores" + LO QUE HACES item 6 says "Buscas doctores locales"
- ✅ End-to-end tool calling verified: model calls buscar_doctores(Guadalajara, Gastroenterología) autonomously
- ⏳ Google Places endpoint (next milestone)
- ⏳ Doctors data gap: no gastroenterologists in Guadalajara (only CDMX + Monterrey)
