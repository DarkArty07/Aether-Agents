# Vercel AI SDK v4 → v6 Migration: Tool Definition

## What Changed

In Vercel AI SDK v4, tools were defined with `parameters`:

```typescript
tool({
  description: "...",
  parameters: z.object({  // v4 API
    city: z.string(),
  }),
  execute: async ({ city }) => { ... },
})
```

In v6, the field was renamed to `inputSchema`:

```typescript
tool({
  description: "...",
  inputSchema: z.object({  // v6 API
    city: z.string(),
  }),
  execute: async ({ city }) => { ... },
})
```

## Error Signal

If you pass `parameters` in v6, TypeScript produces a confusing error:

```
error TS2769: No overload matches this call.
  The last overload gave the following error.
    Type '({ city, specialty }: { city: any; specialty: any; }) => Promise<any>'
    is not assignable to type 'undefined'.
```

The `Tool<never, never>` overload is matched because no valid overload recognized your config shape. The fix is **always**: rename `parameters` → `inputSchema`.

## Why It Changed

The v6 `Tool` type has:

```typescript
type Tool<INPUT, OUTPUT> = {
  inputSchema: FlexibleSchema<INPUT>;  // required, not optional
  // ...
}
```

`FlexibleSchema<INPUT>` accepts several schema types directly:
- `Schema<INPUT>` (from `zodSchema()` or `jsonSchema()`)
- `LazySchema<INPUT>`
- `ZodSchema<INPUT>` (raw `z.object(...)`)
- `StandardSchema<INPUT>`

So `z.object({...})` works **directly** as `inputSchema` — no wrapper needed.

## Runtime Behavior

The `tool()` function is an **identity function** at runtime in both v4 and v6:

```javascript
// @ai-sdk/provider-utils/dist/index.mjs
function tool(tool2) {
  return tool2;
}
```

It only exists for TypeScript type checking. At runtime, the config object passes through unchanged. This means you can't rely on runtime errors if the shape is wrong — use `tsc --noEmit` before running.

## Migration Checklist

| v4 field | v6 field | Notes |
|----------|----------|-------|
| `parameters: z.object({...})` | `inputSchema: z.object({...})` | Direct replacement, same value |
| `parameters` | N/A | No fallback — v6 will not recognize `parameters` |
| `execute({...})` | Same | No change needed |
| `description` | Same | No change |

## Testing the Migration

After changing `parameters` → `inputSchema`:

```bash
npx tsc --noEmit
# Should produce zero errors
```

Then test end-to-end: the LLM should be able to call the tool during a chat conversation.

## Version Detection

To check which version you have:

```bash
npm list ai
# → ai@6.x.x  (v6 API: inputSchema)
# → ai@4.x.x  (v4 API: parameters)
```

Or check the import:
```typescript
// v6 re-exports from bundled @ai-sdk/provider-utils
import { tool, zodSchema, jsonSchema } from "ai";
// v4 had different export structure
```
