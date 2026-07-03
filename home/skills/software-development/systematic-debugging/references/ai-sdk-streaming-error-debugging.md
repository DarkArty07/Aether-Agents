# Debugging AI SDK Streaming Errors in Next.js

## The Problem

Generic error surfaces to client:

```
data: {"type":"error","errorText":"An error occurred."}
```

— no detail, no status code, no context. The actual error is server-side only.

## The Root Cause Diagnostic

**curl (or browser) shows nothing useful** — the real diagnostic is in the Next.js dev server process logs.

### Step 1: Find the Server Process

If you started the dev server with `npm run dev &` (background), use:

```
process(action='log', session_id=<proc_id>)
```

The proc_id is returned when you started the background process.

### Step 2: Read the Full Log

The server log contains:

- **Full `AI_APICallError` stack trace** — includes the `statusCode`, `url`, `responseBody`, and crucially: **`requestBodyValues`**.
- **`convertToModelMessages` type errors** — when messages payload is malformed.
- **Next.js compile/build errors** — module resolution, type errors surfaced at runtime.

### Step 3: Inspect `requestBodyValues`

The AI SDK logs the exact payload sent to the upstream API inside the error object:

```
requestBodyValues: {
    model: 'deepseek-v4-flash',
    tools: [ [Object] ],
    tool_choice: 'auto',        // ← confirms toolChoice propagated correctly
    stream: true,
    ...
}
```

This is invaluable for verifying that configuration changes (toolChoice, model, tools, etc.) actually reached the API call layer.

### Step 4: Check for Auth vs Payload Errors

Common patterns visible in server logs:

| Symptom | Likely Cause | Evidence in Logs |
|---------|--------------|------------------|
| `tool_choice: 'auto'` in body but 401/403 | Invalid API key | `statusCode: 401`, `responseBody` contains auth error |
| Tool not called despite `toolChoice` | Auth blocking (401) masks the real issue | Same as above — fix auth first, then retest |
| 500 at `POST` handler | Type error parsing request | `TypeError: Cannot read properties of undefined (reading 'map')` + line number |
| Model returns text no tools | Model doesn't support tools | Check model capability in provider docs |

### Key Insight

A 401/403 **from the upstream API** will propagate as a generic `{"type":"error","errorText":"An error occurred."}` to the client. The client sees no `tool-call` events, but the root cause is **authentication**, not `toolChoice` configuration.

Always check server logs before changing client-side config when the error is generic.

## Full Diagnostic Command Sequence

```bash
# 1. Start dev server in background
cd /path/to/project && pkill -f "next" 2>/dev/null; rm -rf .next; npm run dev &

# 2. Wait for server to be ready
sleep 8  # or wait for "✓ Ready" message via process(log)

# 3. Test with curl
curl -s -N -X POST http://localhost:3000/api/chat \
  -H "Content-Type: application/json" \
  -d '{"messages":[...],"model":"model-name"}' 2>&1 | head -20

# 4. Check server process log for real error
# (use process(action='log', session_id='proc_xxx'))
```

## Pitfalls

- **Don't trust curl's `[DONE]` as success** — the stream completed but may have errored mid-stream.
- **Don't check server logs with `terminal()` alone** — use `process(action='log')` on the background session to see accumulated output.
- **`text-delta` events are not shown when grepping** — if you `grep -v "text-delta"` you only see start/error/finish events; the real diagnostic is server-side.
