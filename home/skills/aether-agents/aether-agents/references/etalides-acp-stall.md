# ACP Session Stall — Known Issue

Moved from Etalides SOUL.md on 2026-05-05 during optimization. Retained for reference.

### Known Issue — ACP Session Stall (NOT model-specific)

Etalides (and potentially other Daimons) may enter an infinite "thinking" state through the Olympus MCP `talk_to` interface. The Daimon process is alive, thoughts show "formulating"/"analyzing"/"pondering", but **no messages or tool calls are ever produced**.

**This affects multiple models** — confirmed with both `minimax-m2.7` and `deepseek-v4-flash`. This is NOT a model speed issue. It's an ACP session-level problem where the model's response never fully completes the response cycle back to Olympus.

**Symptom:** `talk_to(agent="etalides")` → polls with `status: "active"` but `messages: []` and `tool_calls: []` forever. Only `thoughts` show kawaii faces ("formulating", "mulling", "cogitating"). Wait times exceed 5+ minutes with no output.

**Root cause hypothesis:** The model produces `AgentThoughtChunk` (thinking/spinner) but never transitions to `AgentMessageChunk` (actual response). The ACP session's `completion_event` is never set, so `wait()` blocks indefinitely. This may be related to the known ACP race condition (see aether-diagnostics Section about `asyncio.sleep(0)` fix) or may be a separate issue with how certain model responses are parsed.

**Workaround for Hermes:** If Etalides stalls on a research task:
1. Close the session (`talk_to(action="close")`)
2. Use `delegate_task` with `toolsets=["web"]` as fallback — sub-agents can use `web_search` directly
3. Alternatively, Hermes can use `web_search` for quick fact checks (single lookup)

**Model history (Etalides):**
- `minimax-m2.7` — timed out on research tasks (stall bug, infinite "thinking")
- `deepseek-v4-flash` — **CURRENT, WORKING** via `provider: opencode-go` (see routing fixes below)
- `qwen3.6-plus` — working fallback (less reasoning, cheaper)

**Multi-layer routing bug in hermes-agent (deepseek-v4-flash vs opencode-go):**
Three separate layers in hermes-agent intercept `deepseek-*` model names and route them away from `opencode-go`:

1. **`model_normalize.py` (~line 396):** The normalizer had a handler for `opencode-zen` but not `opencode-go`. **PATCHED 2026-04-28:** Added `opencode-go` to the same block so deepseek models pass through as-is.

2. **`models.py` — `_PROVIDER_MODELS` dict:** The catalog did not include `deepseek-v4-flash` or `deepseek-v4-pro` in the `opencode-go` list. **PATCHED 2026-04-28:** Added both to `models.py` and `setup.py`.

3. **Daimon config format (ROOT CAUSE of HTTP 402):** Daimon configs in Aether Agents use hermes-agent's `model.default` / `model.provider` / `model.base_url` nested YAML format. Using flat top-level keys (`model: X`, `provider: Y`) causes hermes-agent to silently ignore the provider setting and fall back to credential auto-detection, which routes `deepseek-v4-flash` to `kimi-coding` → HTTP 402. **All 5 Daimon configs corrected 2026-04-28.**

**Impact:** Any Daimon config using flat `model:` / `provider:` keys will silently fall back to auto-detection. Always use the nested `model:` block format.

**API key corruption:** Hefesto's `.env` had a 69-char OPENCODE_GO_API_KEY (correct: 67 chars). One corrupted character caused HTTP 401 "Invalid API key." Always verify key length matches across profiles.