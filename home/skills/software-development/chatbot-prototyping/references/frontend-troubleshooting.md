# Frontend Troubleshooting for LLM Gateway Chatbot Templates

## Symptom: Frontend hangs after sending message (backend works)

### Diagnostic Path

1. **Verify backend works** with a direct curl:
   ```bash
   curl -s -N -X POST http://localhost:3000/api/chat \
     -H "Content-Type: application/json" \
     -d '{"messages":[{"role":"user","content":"Hola"}],"model":"deepseek-v4-flash"}'
   ```
   If you see `data: {"type":"text-delta",...}` events, backend is fine.

2. **Check for ApiKeyProvider blocking render**
   The LLM Gateway template's `api-key-provider.tsx` has:
   ```tsx
   if (!mounted) return null;  // Blocks ENTIRE app render until localStorage check
   ```
   And on mount, if no stored key, it opens a dialog. If the user dismisses it,
   `apiKey` stays `null` but the app should still render. However, the dialog
   can interfere with event propagation and React state.

   **Fix: Remove ApiKeyProvider entirely** (key is server-side):
   - `layout.tsx`: `{children}` instead of `<ApiKeyProvider>{children}</ApiKeyProvider>`
   - `page.tsx`: remove all apiKey/headers/KeyRound/useApiKey references

3. **Check streamProtocol and response type**
   The MOST COMMON cause of "assistant response never renders" is using
   `toUIMessageStreamResponse()` in route.ts — this sends `reasoning-start`/
   `reasoning-delta` events that `useChat`'s default rendering does NOT display
   as visible text. The backend returns 200, the stream has data, but the DOM
   stays empty. Verified via Playwright e2e test (see section 6 below).

   **Fix: Use text stream protocol, even with tools**:
   - Route: `return result.toTextStreamResponse()`
   - Frontend: `useChat({ streamProtocol: "text" })`
   - Render: use `{message.content}` (NOT `message.parts.filter(...)`)
   - Remove `convertToModelMessages` — pass `messages` directly to `streamText`
   - Tools with `execute` callbacks still work — the model's text response
     (which includes tool data) streams via text protocol normally

4. **Browser extension errors are noise**
   These are NOT from your app:
   - `Uncaught Error: No Listener: tabs:outgoing.message.ready`
   - `A listener indicated an asynchronous response by returning true`
   - `Unable to add filesystem: <illegal path>`
   
   These come from browser extensions (often dev tools or ad blockers).

5. **Hard reload**
   After structural changes, Next.js dev server may serve cached client bundles.
   Instruct user to Ctrl+Shift+R or clear browser cache.

6. **Playwright e2e testing (when frontend won't render)**
   When the frontend doesn't render but backend works, use Playwright headless
   to reproduce and diagnose without a human browser:
   ```javascript
   // test-e2e.mjs — place in app directory (where playwright is installed)
   import { chromium } from 'playwright';
   const browser = await chromium.launch({ headless: true });
   const page = await browser.newPage();
   const logs = [];
   page.on('console', msg => logs.push(`[CONSOLE ${msg.type()}] ${msg.text()}`));
   page.on('pageerror', err => logs.push(`[PAGE ERROR] ${err.message}`));
   page.on('response', async res => {
     if (res.url().includes('/api/chat')) {
       console.log(`[RESPONSE] ${res.status()}`);
       try { console.log(`[BODY] ${(await res.text()).substring(0, 500)}`); } catch {}
     }
   });
   await page.goto('http://localhost:3000', { waitUntil: 'networkidle' });
   await page.waitForTimeout(2000);
   await page.fill('input[placeholder*="mensaje"]', 'Hola');
   await page.click('button[type="submit"]');
   await page.waitForTimeout(30000); // wait for streaming
   const allText = await page.evaluate(() => document.body.innerText);
   console.log(`=== PAGE TEXT ===\n${allText}`);
   console.log('=== CONSOLE LOGS ===');
   logs.forEach(l => console.log(l));
   await browser.close();
   ```
   Install: `npm install playwright --save-dev` in the app directory.
   Chromium: `npx playwright install chromium`.
   This captures: console errors, network request/response bodies, and full
   DOM text — the same diagnostics you'd get from F12 DevTools manually.

## LLM Gateway Model ID Format

LLM Gateway on coding plans rejects provider-prefixed model IDs:
- `deepseek/deepseek-v4-flash` → ERROR 403 permission_denied
- `deepseek-v4-flash` → works

Always strip the provider prefix. Add a safety net in route.ts:
```typescript
const cleanModel = model?.includes('/') ? model.split('/').pop()! : model;
```

## Vercel AI SDK v6 Tool Calling

Key differences from v4:
- Use `inputSchema: z.object({...})` not `parameters: z.object({...})`
- **Use `toTextStreamResponse()` for ALL cases** — including with tools.
  Despite docs suggesting `toUIMessageStreamResponse()` for tool support,
  in ai@6.0.211 + @ai-sdk/react@1.2.12 the UI protocol sends reasoning
  events that the frontend silently fails to render.
- Frontend: `useChat({ streamProtocol: "text" })`, render `{message.content}`
- `convertToModelMessages` crashes with `TypeError: Cannot read properties
  of undefined (reading 'map')` when used with text protocol — remove it,
  pass `messages` directly to `streamText`
- Tools with `execute` callbacks work fine with text protocol: the model
  calls the tool server-side, gets the result, and includes it in the
  text response that streams to the frontend normally

