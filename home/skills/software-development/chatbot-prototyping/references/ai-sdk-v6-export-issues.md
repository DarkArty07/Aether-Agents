# AI SDK v6 Export Issues: When Docs Lie About Available APIs

## The Problem

Context7 and the official Vercel AI SDK docs (which may track the latest beta) show
patterns using `createUIMessageStreamResponse` and `toUIMessageStream` as standalone
imports. But in **ai@6.0.211** (the version installed by the llmgateway-templates
chatbot template as of June 2026), `toUIMessageStream` does NOT exist as an export.

## Symptom

Following the docs pattern:
```typescript
import {
  convertToModelMessages,
  createUIMessageStreamResponse,
  streamText,
  toUIMessageStream,  // ← DOES NOT EXIST in 6.0.211
} from "ai";

return createUIMessageStreamResponse({
  stream: toUIMessageStream({ stream: result.stream }),
});
```

Produces this build error (seen in browser as a 500 error page):
```
Export toUIMessageStream doesn't exist in target module
The export toUIMessageStream was not found in module
node_modules/ai/dist/index.mjs [app-route] (ecmascript).
Did you mean to import UIMessageStreamError?
```

## Root Cause

The AI SDK v6 is actively evolving. Context7's `/vercel/ai` library may index
a newer beta (e.g., `ai_6.0.0-beta.128`) than what's actually installed.
Exports are statically known — there's no dynamic export fallback.

## What IS Available in ai@6.0.211

Verified by grepping `node_modules/ai/dist/index.d.ts`:

| Export / Method | Available? | Notes |
|----------------|------------|-------|
| `convertToModelMessages` | YES | Converts `UIMessage[]` → `ModelMessage[]` |
| `streamText` | YES | Core streaming function |
| `tool` | YES | Identity function for type-checking tool configs |
| `UIMessage` (type) | YES | UI message type |
| `createUIMessageStreamResponse` | YES | But not needed — use method on result instead |
| `toUIMessageStream` | NO | Use `result.toUIMessageStreamResponse()` instead |
| `result.toUIMessageStreamResponse()` | YES | Method on streamText result — the correct way |
| `result.toTextStreamResponse()` | YES | For text-only streaming (no tools) |

## The Correct Pattern for ai@6.0.x

> **⚠️ IMPORTANT UPDATE (post-Asclepio debugging)**: The pattern below using
> `convertToModelMessages` + `toUIMessageStreamResponse()` WORKS for the LLM
> API call, but `toUIMessageStreamResponse()` sends `reasoning-start`/
> `reasoning-delta` events that `useChat`'s default rendering does NOT display
> as visible text. The assistant's response never appears in the DOM.
>
> **For working frontend rendering, use text stream protocol instead**:
> ```typescript
> // Remove convertToModelMessages — it crashes with text protocol.
> // Pass messages directly. Use text stream for rendering.
> const result = streamText({
>   model: llmgateway(cleanModel),
>   system: `...`,
>   messages,  // NOT convertToModelMessages(messages)
>   tools: { ... },
> });
>
> return result.toTextStreamResponse();
> ```
> Frontend: `useChat({ streamProtocol: "text" })`, render `{message.content}`.

### Pattern for API compatibility (if UI protocol is needed later)

```typescript
import {
  convertToModelMessages,
  streamText,
  tool,
  UIMessage,
} from "ai";
import { z } from "zod";

export async function POST(request: Request) {
  const { messages, model }: { messages: UIMessage[]; model?: string } =
    await request.json();

  const result = streamText({
    model: llmgateway(cleanModel),
    system: `... your system prompt ...`,
    messages: convertToModelMessages(messages),
    tools: { ... },
  });

  // Use the METHOD on result, not a standalone function:
  return result.toUIMessageStreamResponse();
}
```

## Diagnostic Technique

When an import fails with "doesn't exist in target module":

1. **Check the actual exports** of the installed version:
   ```bash
   # Quick check for a specific export:
   grep -oP '^\s*(toUIMessageStream|createUIMessageStreamResponse)\b' \
     node_modules/ai/dist/index.d.ts | sort -u

   # Or dump the entire export list:
   grep "^export {" node_modules/ai/dist/index.d.ts
   ```

2. **Check the version**:
   ```bash
   cat node_modules/ai/package.json | grep '"version"'
   ```

3. **Check methods on the result type** (for method-based alternatives):
   ```bash
   grep -A5 "toUIMessageStreamResponse\|toTextStreamResponse" \
     node_modules/ai/dist/index.d.ts | head -10
   ```

4. **Don't blindly trust Context7** — it may index a different version.
   Cross-reference with the actual installed package's type definitions.

## Additional Findings (Asclepio Session 2 — Tool Calling Investigation)

### `sendReasoning: false` option

`result.toUIMessageStreamResponse()` and `result.toUIMessageStream()` both accept
a `sendReasoning: false` option. Verified in the type definitions:

```bash
grep -A3 "sendReasoning" node_modules/ai/dist/index.d.ts
# sendReasoning?: boolean;
```

Setting `sendReasoning: false` DOES suppress `reasoning-start`/`reasoning-delta`
events from the stream. The stream then sends `text-start`/`text-delta` events
correctly (verified via curl). However, **the frontend still does not render
the assistant message**. The `useChat` hook in @ai-sdk/react@1.2.12 does not
create the assistant message in the DOM even with clean text-delta events
in data protocol.

### `stepCountIs` (NOT `isStepCount`)

The Context7 docs show `isStepCount(5)` but the actual export in ai@6.0.211
is `stepCountIs`. Used with `stopWhen`:

```typescript
import { stepCountIs } from "ai";

streamText({
  // ...
  stopWhen: stepCountIs(5),  // allows 5 tool-call round trips
});
```

### `result.toUIMessageStream()` method (NOT standalone function)

While `toUIMessageStream` does NOT exist as a standalone import, it DOES exist
as a METHOD on the streamText result:

```bash
grep "toUIMessageStream\b" node_modules/ai/dist/index.d.ts
# toUIMessageStream<UI_MESSAGE>(options?): AsyncIterableStream<...>
```

So this pattern works (compiles and runs):
```typescript
import { createUIMessageStreamResponse } from "ai";

return createUIMessageStreamResponse({
  stream: result.toUIMessageStream({ sendReasoning: false }),
});
```

But it still doesn't fix the frontend rendering issue.

### `convertToModelMessages` requires `await`

`convertToModelMessages` returns a `Promise<ModelMessage[]>`, not `ModelMessage[]`.
TypeScript error if not awaited:
```
TS2740: Type 'Promise<ModelMessage[]>' is missing the following properties
from type 'ModelMessage[]': length, pop, push, concat, and 35 more.
```

Fix: `messages: await convertToModelMessages(messages)`

### Exhaustive data-protocol debugging trail

All of these were tested with Playwright e2e and FAILED to render:

1. `result.toUIMessageStreamResponse()` — reasoning events break rendering
2. `result.toUIMessageStreamResponse({ sendReasoning: false })` — still broken
3. `createUIMessageStreamResponse({ stream: result.toUIMessageStream({ sendReasoning: false }) })` — still broken
4. Various combinations with `maxSteps`, `stopWhen: stepCountIs(5)`, `convertToModelMessages`

**Root cause hypothesis**: The `useChat` hook in @ai-sdk/react@1.2.12 expects a
specific data stream format that `toUIMessageStreamResponse` in ai@6.0.211 doesn't
produce correctly. The events are valid SSE but the client-side state management
doesn't create the assistant message. This is likely a version mismatch bug that
will be resolved in a future @ai-sdk/react release.

## Key Lesson

The AI SDK v6 has TWO valid response patterns depending on sub-version:
- **6.0.x stable**: `result.toUIMessageStreamResponse()` (method on result)
- **6.x beta (newer)**: `createUIMessageStreamResponse({ stream: toUIMessageStream({...}) })` (standalone functions)

Always verify against the installed version's `.d.ts` file before writing imports.

**For prototypes: upgrade to ai@7.0.2 + @ai-sdk/react@4.0.2.** Data protocol works correctly in v7. Use `createUIMessageStreamResponse({ stream: result.toUIMessageStream({ sendReasoning: false }) })` + `DefaultChatTransport` (imported from `ai`, not `@ai-sdk/react`). If stuck on v6, use text protocol (`toTextStreamResponse()` + `streamProtocol: "text"`).

---

## UPDATE: ai@7.0.2 + @ai-sdk/react@4.0.2 Upgrade (Asclepio Session 3)

Upgrading from ai@6.0.211 + @ai-sdk/react@1.2.12 to ai@7.0.2 + @ai-sdk/react@4.0.2
**fixes the data protocol rendering bug**. The frontend now correctly renders
assistant messages when using `createUIMessageStreamResponse`.

### API Changes in v7

| Concept | v6 (ai@6.0.211 + @ai-sdk/react@1.2.12) | v7 (ai@7.0.2 + @ai-sdk/react@4.0.2) |
|---|---|---|
| Chat transport | `useChat({ api, body })` | `useChat({ transport: new DefaultChatTransport({ api, body }) })` |
| Transport import | `DefaultChatTransport` from `@ai-sdk/react` (doesn't exist) | `DefaultChatTransport` from `ai` |
| Send message | `handleSubmit` | `sendMessage({ text })` |
| Tool param name | `parameters` (v4-style) | `inputSchema` |
| Message rendering | `message.content` | `message.parts.filter(p => p.type === "text").map(p => p.text).join("")` |
| `convertToModelMessages` | Crashes / not needed for text protocol | `await convertToModelMessages(messages)` — required for data protocol |
| `streamProtocol: "text"` | Required for rendering | NOT needed — default data protocol works |
| `maxSteps` | Only for data protocol (which was broken) | Handled server-side via `stopWhen: stepCountIs(5)` |

### What STILL doesn't work: LLM Gateway + DeepSeek V4 tool calling

Even after the v7 upgrade fixes the SDK layer, **DeepSeek V4 Flash and Pro via
LLM Gateway do not invoke tools**. Confirmed:

1. `tool_choice: 'auto'` appears in server logs (`requestBodyValues`) — the SDK sends it
2. `@llmgateway/ai-sdk-provider` maps tools to OpenAI format correctly (`tool.function.parameters = tool.inputSchema`)
3. The model responds with `finishReason: "stop"` and text — never `finishReason: "tool-calls"`
4. Both Flash and Pro exhibit the same behavior

This is a provider/model limitation. The SDK is not at fault. Options:
- Use DeepSeek API directly (not through LLM Gateway)
- Use OpenRouter with `deepseek/deepseek-chat`
- Use a different model through LLM Gateway that supports tool calling
- Use manual tool calling (sentinel pattern in model output + frontend fetch)
