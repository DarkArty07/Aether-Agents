# Daimon API Quota Diagnostic

When `delegate()` returns `{thoughts: 0, messages: 0, tool_calls: 0, status: "active"}` — the Daimon spawned but never started thinking. The LLM API call is failing silently.

## Step-by-Step Diagnostic

### 1. Confirm the session spawned

Check `mcp-stderr.log` for the agent's spawn and session open:
```bash
grep "<agent-name>" /home/prometeo/Aether-Agents/home/logs/mcp-stderr.log | tail -5
```

Look for:
- "Spawning hefesto: ..." → process started
- "Agent hefesto initialized (protocol=1)" → ACP handshake done
- "Session opened: <uuid>" → session is live

If these exist but 0 thoughts → the LLM call failed after session opened.

### 2. Find the agent's model and provider

```bash
grep -A5 "^model:" /home/prometeo/Aether-Agents/home/profiles/<agent>/config.yaml
```

Note the `default` (model name), `provider`, and `base_url`.

### 3. Find the API key

```bash
grep <PROVIDER>_API_KEY /home/prometeo/Aether-Agents/home/profiles/<agent>/.env
```

### 4. Test the API directly

```bash
curl -s --max-time 10 -X POST <base_url>/chat/completions \
  -H "Authorization: Bearer *** <PROVIDER>_API_KEY <profile>/.env | cut -d= -f2)" \
  -H "Content-Type: application/json" \
  -d '{"model":"<model>","messages":[{"role":"user","content":"Hi"}],"max_tokens":10}'
```

### 5. Interpret the response

| Response | Diagnosis | Action |
|----------|-----------|--------|
| `GoUsageLimitError` | opencode-go monthly quota exhausted | Wait for reset, add balance, or ask user for new key |
| `RateLimitError` / `429` | Rate limited | Wait and retry, or use fallback provider |
| `AuthenticationError` / `401` | Invalid API key | Ask user for correct key |
| `500` / `520` | Server error (upstream) | Wait and retry |
| Valid JSON with tokens | Key works, problem is elsewhere | Check agent.log for other errors |

### 6. Fix

- **Quota exhausted:** Ask user for a new API key. ONLY change the key in `.env`. Do NOT change model/provider/base_url without explicit permission.
- **Invalid key:** Ask user for correct key.
- **Server error:** Wait and retry. If persistent, consider switching to fallback provider (with user permission).

## Key Lesson

The `GoUsageLimitError` from opencode-go includes a message like "Monthly usage limit reached. Resets in N days." This is a quota issue, not a code bug. Different models (e.g., `deepseek-v4-pro` vs `deepseek-v4-flash`) may have separate quotas — one can work while the other is exhausted.
