# assistant-ui Integration Patterns

[assistant-ui](https://assistant-ui.com/) is a React component library for building AI chat UIs. Unlike Vercel AI SDK templates (which bundle provider and streaming), assistant-ui connects to custom backends via `useAssistantTransportRuntime` and a converter function.

## When to Use

- You have a custom backend (Python/FastAPI, Node.js, etc.) that sends/receives messages in OpenAI format (`{role, content}`)
- You need a rich, customizable chat UI without being tied to Vercel AI SDK's provider/tool-calling stack
- You want to control the transport protocol between frontend and backend

## Core Pattern: useAssistantTransportRuntime + Converter

The bridge between your backend's message format and assistant-ui's internal `ThreadMessage` type is the **converter** function, passed to `useAssistantTransportRuntime`:

```tsx
import {
  AssistantRuntimeProvider,
  fromThreadMessageLike,
  useAssistantTransportRuntime,
  type AssistantTransportConnectionMetadata,
} from "@assistant-ui/react";

type State = {
  messages: Array<{ role: string; content: string }>;
};

const converter = (
  state: State,
  connectionMetadata: AssistantTransportConnectionMetadata,
) => {
  // Convert received messages (OpenAI format) to ThreadMessages
  const stateMessages = (state.messages || []).map((m) =>
    fromThreadMessageLike(
      {
        role: m.role === "assistant" ? "assistant" : "user",
        content: typeof m.content === "string"
          ? m.content
          : JSON.stringify(m.content),
      },
      crypto.randomUUID(),
      { type: "complete", reason: "stop" },
    ),
  );

  // Handle optimistic messages (pending user sends)
  const optimisticMessages = connectionMetadata.pendingCommands
    .map((c) => {
      if (c.type === "add-message") {
        const text = c.message.parts
          .map((p) => (p.type === "text" ? p.text : ""))
          .join("\n");
        return fromThreadMessageLike(
          { role: "user", content: text },
          crypto.randomUUID(),
          { type: "complete", reason: "stop" },
        );
      }
      return null;
    })
    .filter((x): x is NonNullable<typeof x> => x !== null); // type predicate, NOT Boolean

  return {
    messages: [...stateMessages, ...optimisticMessages],
    isRunning: connectionMetadata.isSending || false,
  };
};
```

## fromThreadMessageLike — the key helper

`fromThreadMessageLike(like, fallbackId, fallbackStatus)` converts a simple `ThreadMessageLike` into a full `ThreadMessage` with all required fields (`id`, `createdAt`, `metadata`, `attachments`/`status`).

- **`like`**: a `ThreadMessageLike` — just needs `role` and `content`. Content can be a plain `string`.
- **`fallbackId`**: usually `crypto.randomUUID()`
- **`fallbackStatus`**: default status for assistant messages — usually `{ type: "complete", reason: "stop" }`

This is the correct way to construct messages in a converter. **Do NOT construct `ThreadMessage` objects manually** — the type is a complex intersection with many required fields.

## LangChain → OpenAI Migration

If migrating from `@assistant-ui/react-langgraph` (which ships a `LangChainMessageConverter` + `convertLangChainMessages`):

| Before | After |
|--------|-------|
| `import { convertLangChainMessages, type LangChainMessage } from "@assistant-ui/react-langgraph"` | Remove entirely |
| `import { unstable_createMessageConverter as createMessageConverter } from "@assistant-ui/react"` | Remove entirely |
| `State = { messages: LangChainMessage[] }` | `State = { messages: Array<{ role: string; content: string }> }` |
| `LangChainMessageConverter.toThreadMessages(messages)` | `fromThreadMessageLike(...)` per message |
| Message format: `{type: "human", content: [{type: "text", text: "..."}]}` | Message format: `{role: "user", content: "..."}` |

## Pitfalls

### 1. `.filter(Boolean)` does NOT narrow types in TypeScript

```tsx
// BROKEN: TypeScript still includes | null in the result type
const items = arr.map(fn).filter(Boolean);

// FIXED: use a type predicate
const items = arr
  .map(fn)
  .filter((x): x is NonNullable<typeof x> => x !== null);
```

### 2. AssistantTransportState requires ThreadMessage[], not ThreadMessageLike[]

The converter must return `{ messages: ThreadMessage[], isRunning: boolean }`. `fromThreadMessageLike` returns `ThreadMessage`, so use it directly. Do NOT try to return `ThreadMessageLike[]` and expect auto-conversion.

### 3. ThreadMessage has many required fields

`ThreadMessage` is an intersection of `BaseThreadMessage & (ThreadSystemMessage | ThreadUserMessage | ThreadAssistantMessage)`. Required fields include:
- `id: string`
- `createdAt: Date`
- `metadata: { custom: Record<string, unknown> }`
- `status: MessageStatus` (for assistant messages)
- `attachments: CompleteAttachment[]` (for user messages)

Constructing these manually is error-prone. Always use `fromThreadMessageLike`.

### 4. Remove unused imports to avoid verbatimModuleSyntax errors

After removing `@assistant-ui/react-langgraph`, ensure no leftover imports reference it. If your tsconfig has `verbatimModuleSyntax`, the unused import will produce a compile error.

### 5. The converter is called on every state update

Make it pure and fast — no side effects, no async operations. If you need to fetch data, do it outside the converter and update `state.messages` when it arrives.
