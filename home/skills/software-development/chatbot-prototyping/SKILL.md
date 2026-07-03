---
name: chatbot-prototyping
description: Build chatbot prototypes using lightweight web templates (Next.js + Vercel AI SDK) instead of heavy agent frameworks. Covers template evaluation, provider swapping, system-prompt injection, and incremental tool connection via API endpoints.
---

# Chatbot Prototyping from Templates

## When to Use This Approach

Use a lightweight web template instead of a full agent framework (hermes-agent, etc.) when the prototype needs:
- A system prompt (persona/behavior definition)
- A chat interface with streaming responses
- Incremental tool connection (API endpoints added over time)

This covers 90% of prototype demos. Agent frameworks add hundreds of thousands of lines of runtime infrastructure that a demo doesn't need. Chris's principle: "solo necesitamos el system prompt y la interfaz de chat, es todo lo que necesitamos, lo demas se lo vamos conectando."

## When NOT to Use This Approach

- The prototype needs autonomous multi-step reasoning, tool-use loops, or agent orchestration → use a real agent framework
- The prototype needs persistent sessions, memory, or cross-conversation state → use an agent framework
- The final product is a CLI tool, not a web app → use hermes-agent directly
- **The prototype outgrows the web template** — when you need custom tools (database queries, external API integration), migrating from Next.js to hermes-agent + custom MCP is cleaner than fighting the AI SDK's tool-calling protocol issues. See "Migration Pattern: Web Template → Hermes Agent + Custom MCP" below.
- **Chris's explicit reversal (Asclepio, 2026-06-26):** "Ya no vamos a ocupar ese motor" — after hitting AI SDK v6/v7 tool-calling incompatibilities and LLM Gateway + DeepSeek V4 not invoking tools, Chris decided to go back to hermes-agent with a custom MCP server. The web template was a detour, not the destination.

## Migration Pattern: Web Template → Hermes Agent + Custom MCP

When a chatbot prototype evolves past simple chat + system prompt into needing real tools (database queries, external APIs), the web template approach breaks down. AI SDK tool-calling protocol issues (v6 broken, v7 works but model may not invoke tools) and the complexity of maintaining API routes make hermes-agent + a custom MCP server the better path.

### Decision triggers (any one):
- Tool calling doesn't work with your provider/model (LLM Gateway + DeepSeek V4 ignores tools)
- You need SQLite or other local data sources that are awkward to expose via Next.js API routes
- You need external API integration (Google Maps, etc.) with API keys that shouldn't be in client-side code
- The prototype is becoming a product and needs persistent sessions, memory, or multi-step reasoning

### Migration steps:
1. **Preserve the system prompt** — copy the system prompt from `route.ts` into a `SOUL.md` file. This is the core asset.
2. **Create a standalone HERMES_HOME** — separate directory (e.g., `project/agent/`) with `SOUL.md`, `config.yaml`, `.env`. NOT inside the Aether-Agents home.
3. **Build a custom MCP server** — Python stdio server using FastMCP. See the `custom-mcp-server` skill for the full pattern.
4. **Migrate data files** — JSON data → SQLite database (the MCP server can auto-create the DB from JSON on first run).
5. **Delete the web app** — once the hermes-agent instance works, delete the Next.js app entirely. Don't leave dead code.
6. **Verify** — `hermes mcp test <name>` to confirm MCP tools are discovered, then `HERMES_HOME=... hermes chat` to test the full experience.

### What you keep vs discard:
| Keep | Discard |
|------|---------|
| System prompt text (→ SOUL.md) | Next.js app (route.ts, page.tsx, package.json) |
| Data files (JSON → SQLite) | node_modules, .next cache |
| API keys (→ .env) | AI SDK protocol workarounds |
| Project documents (DESIGN.md, RESEARCH.md) | Frontend components, CSS |

### Related skill:
- **`custom-mcp-server`** — Full guide for building the custom Python MCP server (FastMCP, SQLite tools, external API tools, config.yaml registration, verification workflow). Includes a copy-and-adapt server.py template.

## Template Evaluation Technique

When evaluating a GitHub template for chatbot use, don't clone first — inspect remotely:

1. Fetch the file tree via GitHub Contents API:
   ```
   curl -sL "https://api.github.com/repos/<owner>/<repo>/contents/<path>"
   ```
2. For directories, use the git tree API with `recursive=1` to see all nested files at once:
   ```
   curl -sL "https://api.github.com/repos/<owner>/<repo>/git/trees/<tree_sha>?recursive=1"
   ```
3. Read key files via raw.githubusercontent.com (no auth needed for public repos):
   - `README.md` — features, tech stack, setup instructions
   - `package.json` — dependencies, scripts, versions
   - API route files (e.g., `app/api/chat/route.ts`) — how the LLM is called, what provider, what system prompt
   - Frontend page files (e.g., `app/page.tsx`) — UI structure, model selector, features
   - `.env.example` — what credentials/keys are required

4. Assess against your needs:
   - Does it use Vercel AI SDK (`streamText` + `useChat`)? → standard streaming pattern, easy to adapt
   - Is the system prompt hardcoded? → you'll replace it with your project's prompt
   - Is the provider swappable? → OpenAI-compatible providers can be swapped via `@ai-sdk/openai` with a custom `baseURL`
   - Does it have a model selector? → useful for testing different models with the same prompt

## Template Adaptation Checklist

When adapting a Next.js chatbot template (Vercel AI SDK based):

### 0. Check If the Template's Provider Already Matches
Before swapping providers, check if the template already bundles your desired provider. The `@llmgateway/ai-sdk-provider` (LLM Gateway) template, for example, accepts any OpenAI-compatible model via its `model` parameter — no provider swap needed. Only replace the provider if the template's default doesn't support your models or gateway.

### 1. Inject System Prompt (Multi-line Template Literal)
Replace the hardcoded generic prompt (usually `"You are a helpful, friendly assistant..."`) in the API route with your project's system prompt. Use a JavaScript template literal (backtick string) to embed multi-line prompts directly — no escaping issues, no separate file to load:
```typescript
// Strip provider prefix as safety net (LLM Gateway coding plans reject "deepseek/xxx")
const cleanModel = model?.includes('/') ? model.split('/').pop()! : model;
const result = streamText({
  model: llmgateway(cleanModel || "deepseek-v4-flash"),
  system: `# Your Project Name — Role

## Identity
You are an assistant for [use case]...

## LO QUE HACES
1. First step
2. Second step

## LO QUE NUNCA HACES
- Never do X
- Never do Y

## TONO Y ESTILO
- Tone guidance here`,
  messages,
});
```
This keeps the system prompt visible in the route file and avoids the complexity of loading external files at runtime. No escaping issues with backticks inside the prompt if they don't exist — for rare cases that conflict, use `\``.

### 2. Update the .env.example
Set the placeholder to `***` (not `your_api_key_here`):
```
LLMGATEWAY_API_KEY=***
```
This avoids confusion with real key formats and signals clearly that the value must be replaced.

### 3. Update Model Selector
Replace the template's model list with models available through your provider/gateway. Keep the UI pattern (dropdown `<select>`). Add new models to the existing `MODELS` array:
```typescript
const MODELS = [
  // existing models from template...
  // Add your models (root IDs, NO provider prefix — see Pitfalls):
  { id: "deepseek-v4-flash", name: "DeepSeek V4 Flash" },
  { id: "deepseek-v4-pro", name: "DeepSeek V4 Pro" },
];
```

**LLM Gateway coding plans reject provider prefixes.** If using LLM Gateway (the template's default provider), model IDs must be root names without a `provider/` prefix: `deepseek-v4-flash`, not `deepseek/deepseek-v4-flash`. Strip all existing prefixes from the template's MODELS array. See `references/llm-gateway-quirks.md` for the full error message and fix patterns.

### 4. Add Tool Endpoints
Create separate API routes for each tool the chatbot needs. Use Next.js App Router route handlers:
```typescript
// src/app/api/doctors/route.ts
import { NextRequest, NextResponse } from "next/server";
import { readFile } from "node:fs/promises";
import { join } from "node:path";

export async function GET(request: NextRequest) {
  const { searchParams } = new URL(request.url);
  const city = searchParams.get("city");
  const specialty = searchParams.get("specialty");

  const filePath = join(process.cwd(), "data", "doctors.json");
  const raw = await readFile(filePath, "utf-8");
  let doctors: Doctor[] = JSON.parse(raw);

  if (city) {
    doctors = doctors.filter(
      (d) => d.city.toLowerCase() === city.toLowerCase(),
    );
  }
  if (specialty) {
    doctors = doctors.filter(
      (d) => d.specialty.toLowerCase() === specialty.toLowerCase(),
    );
  }
  return NextResponse.json(doctors);
}
```
**Filtering pattern**: case-insensitive `.toLowerCase()` comparison on query params. This handles user-input mismatches naturally.

Wire these either as:
- **Frontend-called**: the UI calls the endpoint directly (simpler, no LLM function calling needed)
- **LLM function-calling**: register tools with `streamText` so the model calls endpoints autonomously (more natural conversation, requires function-calling-capable model)

#### LLM Function-Calling Pattern (Vercel AI SDK v6+)

> **⚠️ AI SDK v6 API change**: The `tool()` function uses `inputSchema` (not `parameters` as in v4). Passing `parameters` causes a confusing TypeScript error:
> ```
> Type '({ city, specialty }) => Promise<any>' is not assignable to type 'undefined'.
> ```
> This means the `Tool` type didn't recognize your config shape. Fix: rename `parameters` to `inputSchema`.

Wire tools directly into `streamText` so the LLM can autonomously decide when to query data:

```typescript
import { streamText, tool } from "ai";
import { z } from "zod";
import { readFile } from "node:fs/promises";
import { join } from "node:path";

// Inside POST handler:
const result = streamText({
  model: llmgateway(cleanModel || "deepseek-v4-flash"),
  system: `... your system prompt ...`,
  messages,
  tools: {
    buscar_doctores: tool({
      description:
        "Busca doctores en la base de datos por ciudad y/o especialidad. " +
        "Usa esta herramienta cuando el usuario pida ver a un doctor.",
      // v6 API: inputSchema, NOT parameters
      inputSchema: z.object({
        city: z.string().describe(
          "Ciudad donde buscar doctores (ej: Guadalajara, CDMX, Monterrey)"
        ),
        specialty: z.string().optional().describe(
          "Especialidad médica a buscar (ej: Cardiología, Medicina General)"
        ),
      }),
      execute: async ({ city, specialty }) => {
        const filePath = join(process.cwd(), "data", "doctors.json");
        const raw = await readFile(filePath, "utf-8");
        let doctors = JSON.parse(raw);
        doctors = doctors.filter((d: any) =>
          d.city.toLowerCase() === city.toLowerCase()
        );
        if (specialty) {
          doctors = doctors.filter((d: any) =>
            d.specialty.toLowerCase().includes(specialty.toLowerCase())
          );
        }
        return doctors;
      },
    }),
  },
});
```

**Streaming protocol choice for tools** — depends on SDK version:

**With ai@7.0.2 + @ai-sdk/react@4.0.2 (current, recommended):**

- **UI message protocol** (`createUIMessageStreamResponse` + `toUIMessageStream({ sendReasoning: false })` + `DefaultChatTransport`): WORKS. The v7 upgrade fixes the v6 rendering bug. `sendReasoning: false` is CRITICAL — without it, reasoning events break the frontend. Use `message.parts` (filter `type === "text"`) for rendering, NOT `message.content`.
- **Text protocol** (`toTextStreamResponse()` + `streamProtocol: "text"`): Also works, but does NOT support multi-step tool calling. Use only for simple chat without tools.

**With ai@6.0.211 + @ai-sdk/react@1.2.12 (legacy, DO NOT USE):**

- **Text protocol** is the ONLY option that works. Data protocol is broken (see pitfalls). If stuck on v6, use text protocol + dynamic system prompt injection instead of tool calling.

```typescript
// route.ts — v7 pattern (ai@7.0.2 + @ai-sdk/react@4.0.2)
import {
  convertToModelMessages,
  createUIMessageStreamResponse,
  streamText,
  tool,
  stepCountIs,
  UIMessage,
} from "ai";
import { DefaultChatTransport } from "ai"; // moved from @ai-sdk/react in v7
import { z } from "zod";

export async function POST(request: Request) {
  const { messages, model }: { messages: UIMessage[]; model?: string } =
    await request.json();

  const result = streamText({
    model: llmgateway(cleanModel || "deepseek-v4-flash"),
    system: `... your system prompt ...`,
    messages: await convertToModelMessages(messages), // MUST await (returns Promise)
    stopWhen: stepCountIs(5), // allows 5 tool-call round trips
    toolChoice: "auto", // explicit, ensures tools are sent
    tools: {
      buscar_doctores: tool({
        description: "Busca doctores por ciudad y/o especialidad.",
        inputSchema: z.object({  // v6+: inputSchema, NOT parameters
          city: z.string().describe("Ciudad donde buscar"),
          specialty: z.string().optional().describe("Especialidad"),
        }),
        execute: async ({ city, specialty }) => {
          // tool implementation
        },
      }),
    },
  });

  // CRITICAL: sendReasoning: false prevents reasoning events from breaking frontend
  return createUIMessageStreamResponse({
    stream: result.toUIMessageStream({ sendReasoning: false }),
  });
}
```

```typescript
// page.tsx — v7 pattern
import { useChat } from "@ai-sdk/react";
import { DefaultChatTransport } from "ai"; // moved from @ai-sdk/react in v7

const { messages, sendMessage } = useChat({
  transport: new DefaultChatTransport({
    api: "/api/chat",
    body: { model },
  }),
  // NO streamProtocol — default data protocol works in v7
  // NO maxSteps needed — stopWhen handles it server-side
});

// Render: use message.parts, NOT message.content
function messageText(message) {
  return message.parts
    .filter((p) => p.type === "text")
    .map((p) => p.text)
    .join("");
}
// <ReactMarkdown>{messageText(message)}</ReactMarkdown>
```

**When text protocol tools don't trigger** (model ignores tool and says "let me look that up" but never calls it): fall back to the dynamic system prompt injection pattern. See the "Alternative to tool calling" pitfall below.

**CRITICAL: LLM Gateway + DeepSeek V4 does NOT invoke tools.** Even with ai@7.0.2 (data protocol works, `tool_choice: 'auto'` confirmed in server logs, tools correctly mapped to OpenAI format by `@llmgateway/ai-sdk-provider`), DeepSeek V4 Flash and Pro respond with text instead of calling the tool. The provider maps tools correctly (`tool.function.parameters = tool.inputSchema`), LLM Gateway receives them, but the model ignores them. This is a provider/model limitation, not an SDK issue. Options: (1) use a different provider that supports tool calling with DeepSeek (e.g., DeepSeek API direct, OpenRouter), (2) use a different model through LLM Gateway that supports tool calling, (3) use manual tool calling (model outputs a sentinel pattern, frontend detects and fetches from API).

#### Data protocol rendering: v6 BROKEN, v7 FIXED

**ai@6.0.211 + @ai-sdk/react@1.2.12 (BROKEN):** All data protocol attempts failed to render. The stream sends correct `text-start`/`text-delta` events (verified via curl), but `useChat` never creates the assistant message in the DOM. `sendReasoning: false` suppresses reasoning events but doesn't fix rendering. This is a version mismatch bug between the server and client packages.

**ai@7.0.2 + @ai-sdk/react@4.0.2 (FIXED):** Upgrade resolves the rendering issue. `createUIMessageStreamResponse({ stream: result.toUIMessageStream({ sendReasoning: false }) })` works correctly. The frontend renders assistant messages via `message.parts` (filter `type === "text"`). API changes in v7:
- `DefaultChatTransport` moves from `@ai-sdk/react` to `ai` package
- `sendMessage()` replaces the old `handleSubmit` pattern
- `useChat` takes `transport` instead of `api`/`body` directly
- `inputSchema` (not `parameters`) for tool definitions
- `await convertToModelMessages(messages)` (returns Promise)
- `stepCountIs` (not `isStepCount` as Context7 docs show)

**Key details**:
- `inputSchema` accepts a raw `z.object()` directly — no need for `zodSchema()` wrapper. The `Tool` type's `inputSchema: FlexibleSchema<INPUT>` accepts Zod schemas natively.
- The `tool()` function is an **identity function at runtime** — it only provides TypeScript type checking. The object shape is what matters.
- `city` is required, `specialty` is optional — declared via `z.string().optional()`
- Case-insensitive comparison in `execute`: `.toLowerCase()` on both sides
- The `execute` function's parameters are **automatically typed** by TypeScript inference from the `inputSchema`

**Update the system prompt** to tell the LLM about the tool:
```markdown
### Paso 6: Canalización con doctores
Cuando el usuario necesite ver a un médico, usa la herramienta buscar_doctores para encontrar 
doctores en su ciudad. Si sabes qué especialidad necesita, filtra por especialidad. 
Preséntale las opciones con nombre, especialidad, dirección, teléfono y horario.
```

Also update the "what you do" section:
```markdown
## LO QUE HACES
6. Buscas doctores locales en tu base de datos y los recomiendas al usuario
```

**Pitfalls**:
- The `tool()` function identity at runtime means TypeScript will catch shape errors but the code always runs — a tool with wrong keys silently does nothing. Always `tsc --noEmit` after adding tools.
- Specify `description` on the tool AND each parameter — the LLM uses these to decide when to call and with what values.
- If the execute function references `fs` or reads files, the path must use `process.cwd()` (which equals the Next.js project root at runtime).
- See `references/ai-sdk-v4-to-v6-migration.md` for the full migration guide if adapting v4-style tool definitions.

### 5. Database for Prototype
For prototypes, use a JSON file with fake/mock data rather than setting up a real database. Place it in the project and read it from the API route. Example: `data/doctors.json` with entries like:
```json
{ "name": "Dr. Juan Pérez", "specialty": "Médico General", "city": "Guadalajara", "address": "...", "phone": "...", "hours": "..." }
```

### 6. Initial Setup and Git Init
When migrating from an older prototype (e.g., hermes-agent CLI → Next.js template):
1. Copy only the system prompt file (`SOUL.md`) — do NOT carry over agent config, CLI files, or sandbox directories
2. Delete the old prototype directory entirely
3. Delete any stray template files (README-DEMO.md, sandboxes)
4. Initialize git in the new `app/` directory with a proper `.gitignore`:
   ```
   node_modules/
   .next/
   .env.local
   *.tsbuildinfo
   next-env.d.ts
   ```
5. Make an initial commit with all template + adaptation files

## Architecture Pattern

```
User → Next.js Chat UI (useChat) → POST /api/chat (streamText)
                                          ↓
                                   LLM (OpenAI-compatible API)
                                   System prompt = project persona
                                          ↓
                              Tool endpoints (/api/doctors, /api/places, ...)
```

## Reference Files

- `references/asclepio-prototype.md` — Full session notes from the Asclepio health-orientation chatbot project: template analysis, architecture decision (hermes-agent CLI → Next.js template), adaptation plan, and project layout.
- `references/frontend-troubleshooting.md` — Diagnostic path for common frontend issues: hangs after message, ApiKeyProvider removal, streamProtocol mismatch, LLM Gateway model ID format, AI SDK v6 tool calling differences.
- `references/ai-sdk-v6-export-issues.md` — When Context7/official docs reference exports that don't exist in your installed ai@6.0.x version. How to verify available exports via `.d.ts` grep. The correct `convertToModelMessages` + `result.toUIMessageStreamResponse()` pattern vs the broken `toUIMessageStream` standalone import.
- `references/markdown-and-datasource-patterns.md` — Markdown rendering in chat, alternative to tool calling (system prompt injection), tradeoff comparison.
- `references/assistant-ui-integration.md` — Building chatbot UIs with [assistant-ui](https://assistant-ui.com/) + custom backend transport. Covers `useAssistantTransportRuntime`, `fromThreadMessageLike`, migrating from LangChain to OpenAI message format, and TS type pitfalls. — Markdown rendering in chat (react-markdown + manual CSS for Tailwind v4, NOT @tailwindcss/typography). Alternative to tool calling: embed reference data directly in system prompt when tools don't work with text protocol. Tradeoff comparison and fictitious data generation tips.

## Pitfalls

- **Don't use a full agent framework for a simple chat prototype.** It's overkill and adds unnecessary complexity, runtime overhead, and configuration burden. Chris explicitly rejected this: "las 500,000 líneas de código que tiene hermes agent" are not needed when all you need is prompt + chat.
- **The template's default provider may require a separate API key** (e.g., LLM Gateway). Check `.env.example` for the required key name. LLM Gateway keys work out of the box — no provider swap needed if Chris provides a key.
- **LLM Gateway coding plans reject provider-prefixed model IDs.** `deepseek/deepseek-v4-flash` fails with `permission_denied`. Use root IDs: `deepseek-v4-flash`. The error is silent from the client (empty curl response) — check `next dev` server logs for the actual error. Fix: strip prefixes from MODELS array AND add a `cleanModel` safety net in route.ts (see `references/llm-gateway-quirks.md`).
- **npm works when pnpm isn't installed.** The template README says `pnpm install` but `npm install` works fine for prototyping. No need to install pnpm globally just for a prototype.
- **Empty chat response → check server logs.** If `curl -s -N -X POST /api/chat` returns empty, the LLM provider rejected the request. Read the background dev server output via `process(action='log')` to see the actual error (usually a 4xx with a JSON error body in the Next.js error output).
- **Vercel AI SDK's `streamText` + `useChat` is the standard streaming pattern.** Don't reinvent it.
- **CRITICAL: SDK version determines protocol choice.** With ai@6.0.211 + @ai-sdk/react@1.2.12, use text protocol (`toTextStreamResponse()` + `streamProtocol: "text"`) — data protocol is broken (see above). With ai@7.0.2 + @ai-sdk/react@4.0.2, use data protocol (`createUIMessageStreamResponse` + `toUIMessageStream({ sendReasoning: false })`) — it works and supports tool calling. Always verify with Playwright e2e after upgrading.
  **Upgrading from v6 to v7**: `npm install ai@latest @ai-sdk/react@latest`. Breaking changes: `DefaultChatTransport` imported from `ai` (not `@ai-sdk/react`), `sendMessage()` instead of `handleSubmit`, `inputSchema` (not `parameters`) in tool definitions, `await convertToModelMessages(messages)`.
- **`convertToModelMessages` is required for data protocol, forbidden for text protocol.** With data protocol (v7): `messages: await convertToModelMessages(messages)` — MUST await (returns Promise). With text protocol: pass `messages` directly, do NOT use `convertToModelMessages` (crashes with `TypeError: Cannot read properties of undefined (reading 'map')`).
- **CRITICAL: Do NOT trust Context7 or official docs blindly for AI SDK v6 exports.** The docs reference `toUIMessageStream` as a standalone function, but it does NOT exist in ai@6.0.211. Always verify available exports before importing:
  ```bash
  # Check what's actually exported by the installed version:
  grep -oP '^\s*(functionNameYouNeed)\b' node_modules/ai/dist/index.d.ts | sort -u
  # Or grep the full export list:
  grep "^export {" node_modules/ai/dist/index.d.ts
  ```
  See `references/ai-sdk-v6-export-issues.md` for the full diagnostic trail.
- **`maxSteps` is ONLY for data protocol (UI message stream).** It controls multi-turn tool loops but is irrelevant with text protocol. Remove it when using `streamProtocol: "text"`.
- **Alternative to tool calling: dynamic system prompt injection.** When tools don't work — either because of SDK version issues (v6 text protocol) or because the provider/model doesn't invoke tools (LLM Gateway + DeepSeek V4) — read the data JSON at runtime and inject it into the system prompt dynamically. This is BETTER than hardcoding because the JSON stays the single source of truth:
  ```typescript
  // In route.ts POST handler, before streamText:
  const filePath = join(process.cwd(), "data", "doctors.json");
  const raw = await readFile(filePath, "utf-8");
  const doctors = JSON.parse(raw);
  const byCity: Record<string, any[]> = {};
  for (const d of doctors) {
    if (!byCity[d.city]) byCity[d.city] = [];
    byCity[d.city].push(d);
  }
  let doctorsSection = "\n\n## Doctores disponibles (BASE DE DATOS - NO INVENTAR)\nUsa SOLO estos doctores.\n";
  for (const [city, docs] of Object.entries(byCity)) {
    doctorsSection += "\n**" + city.toUpperCase() + "**: ";
    const entries = docs.map(
      (d: any) => d.name + " (" + d.specialty + ") — " + d.address + " — " + d.phone + " — " + d.schedule
    );
    doctorsSection += entries.join(" | ");
  }
  // Then append doctorsSection to the system prompt template literal
  ```
  This works because the LLM can reference the data directly when composing its response. No tool calling, no API endpoint, no protocol issues. The tradeoff: the data is static per request (no dynamic queries within a conversation) and consumes context window tokens. For prototypes with small datasets (<200 entries), this is the simplest and most reliable approach.
- **Render markdown in chat messages.** LLM responses contain markdown (bold, headers, lists). Without a markdown renderer, the user sees raw `**text**` and `### headers`. Install `react-markdown` and render assistant messages with it:
  ```typescript
  import ReactMarkdown from "react-markdown";
  
  // In the message rendering:
  <CardContent className="text-sm markdown-content">
    {message.role === "assistant" ? (
      <ReactMarkdown>{message.content}</ReactMarkdown>
    ) : (
      message.content
    )}
  </CardContent>
  ```
  **Do NOT use `@tailwindcss/typography` plugin with Tailwind v4.** It fails with `Can't resolve '@tailwindcss/typography'` even when installed. Instead, write manual CSS classes for markdown elements in `globals.css`:
  ```css
  .markdown-content h1, .markdown-content h2, .markdown-content h3 { font-weight: 600; margin-top: 1em; margin-bottom: 0.5em; }
  .markdown-content h1 { font-size: 1.5rem; }
  .markdown-content h2 { font-size: 1.25rem; }
  .markdown-content p { margin-bottom: 0.75em; }
  .markdown-content ul, .markdown-content ol { padding-left: 1.5em; margin-bottom: 0.75em; }
  .markdown-content ul { list-style-type: disc; }
  .markdown-content ol { list-style-type: decimal; }
  .markdown-content strong { font-weight: 600; }
  .markdown-content em { font-style: italic; }
  .markdown-content hr { margin: 1em 0; border-color: var(--color-border); }
  .markdown-content blockquote { border-left: 3px solid var(--color-muted-foreground); padding-left: 1em; color: var(--color-muted-foreground); }
  .markdown-content code { background-color: var(--color-secondary); padding: 0.125rem 0.25rem; border-radius: 0.25rem; font-size: 0.875em; }
  ```
  Use the class name `markdown-content` on the container element. Remove `whitespace-pre-wrap` from the container since markdown handles spacing.
- **Web templates are web-only.** If the final product is mobile (React Native/Flutter), the template is for prototyping only — plan the migration later, don't try to make the web template work as a mobile app.
- **Start with chat + system prompt, add tools incrementally.** Don't try to wire all endpoints on day one. Get the conversation working first, then add one tool at a time.
- **Remove the ApiKeyProvider dialog from LLM Gateway templates.** The template ships with a client-side dialog (`src/components/api-key-provider.tsx`) that pops up asking the user for their API key. When the key is configured server-side in `.env.local`, this dialog is unnecessary and breaks UX (dialog blocks interaction, `if (!mounted) return null` prevents render until localStorage check completes). Remove it entirely:
  1. In `layout.tsx`: remove `<ApiKeyProvider>` wrapper, replace with `{children}`, remove import
  2. In `page.tsx`: remove `useApiKey` import, remove `apiKey`/`headers`/`setApiKeyOpen` variables, remove `KeyRound` import, remove the API key `<Button>` from header JSX, remove `headers` from `useChat` config, remove `useMemo` import if no longer used
  3. Do NOT delete `api-key-provider.tsx` itself — just remove its usage
- **Frontend hangs after message? Diagnose with backend curl first.** If the user reports the chat UI not responding after sending a message:
  1. Test backend directly: `curl -s -N -X POST http://localhost:3000/api/chat -H "Content-Type: application/json" -d '{"messages":[{"role":"user","content":"Hola"}],"model":"deepseek-v4-flash"}'`
  2. If curl works (streaming text-delta events), the problem is frontend-only
  3. Most common cause: `ApiKeyProvider` dialog blocking render (`if (!mounted) return null` prevents the whole app from mounting until localStorage check finishes, and if the dialog was dismissed it may leave the app in a broken state)
  4. Second cause: `streamProtocol: "text"` left in `useChat` after switching to `toUIMessageStreamResponse()` — protocol mismatch
  5. Browser console errors like "No Listener: tabs:outgoing.message.ready" are from browser extensions, NOT the app — don't chase them
- **Hard reload after template changes.** Next.js dev server hot-reloads, but cached client bundles can persist. After structural changes (removing providers, changing stream protocol), instruct the user to Ctrl+Shift+R (hard reload) to clear cached JS.
- **Use Playwright for e2e testing when frontend won't render.** When the user reports "frontend doesn't respond" and you can't reproduce via curl (backend works fine), install Playwright in the app directory (`npm install playwright --save-dev` + `npx playwright install chromium`) and write a headless test that navigates, sends a message, and captures: console logs, network response body, and full DOM text. This replaces manual browser DevTools debugging and gives you the exact data to diagnose rendering failures. See `references/frontend-troubleshooting.md` section 6 for the test script template.
- **CRITICAL: Be transparent about architectural changes.** If a planned approach (e.g., tool calling) doesn't work and you need to fall back to an alternative (e.g., system prompt injection), TELL THE USER before making the change. Do not silently swap architectures. The user explicitly called this out: "No me dijiste que habías quitado el tool calling, no habíamos quedado en eso." If you discover a workaround mid-debugging, report it as a finding and let the user decide whether to accept the tradeoff or keep trying the original approach. This applies to any architectural decision: protocol choices, provider swaps, data injection patterns, removing features, etc.
