# OpenCode Go — Model Reference

**Endpoint**: `https://opencode.ai/zen/go/v1` (chat/completions)
**Provider name in Hermes**: `opencode-go`
**Auth**: `GLM_API_KEY` or `OPENCODE_GO_API_KEY`

## Available Models (May 2026)

| Model | ID | Multimodal? | Notes |
|-------|---|-------------|-------|
| GLM-5.1 | `glm-5.1` | **Text only** | Best reasoning in Go. Main model. |
| GLM-5 | `glm-5` | **Text only** | Previous gen. |
| Kimi K2.5 | `kimi-k2.5` | **Yes (vision)** | Best value multimodal. Chat/completions format. |
| MiMo-V2-Pro | `mimo-v2-pro` | **Text only** | |
| MiMo-V2-Omni | `mimo-v2-omni` | **Yes (vision)** | |
| MiniMax M2.7 | `minimax-m2.7` | **Text only** | |
| MiniMax M2.5 | `minimax-m2.5` | **Text only** | Cheapest, most requests. |
| Qwen3.5 Plus | `qwen3.5-plus` | **Text only** | Good value. |
| Qwen3.6 Plus | `qwen3.6-plus` | **Yes (vision)** | 1M context, strong vision. |

**CRITICAL**: DeepSeek V4 Pro/Flash are NOT in Go — they are text-only regardless. Kimi K2.6 is text-only despite K2.5 being multimodal. Always verify multimodal support per model, not per family.

## Usage Limits (Go)

- 5-hour limit: $12
- Weekly limit: $30
- Monthly limit: $60
- Can enable "Use balance" to continue past limits with Zen credits

## Hermes Configuration Pattern

All Go models share the same `base_url` and `api_key`. Configuration shorthand:

```yaml
auxiliary:
  MODEL_NAME:
    provider: opencode-go
    model: <model-id>
    base_url: https://opencode.ai/zen/go/v1
    api_key: ${GLM_API_KEY}
```

Auxiliary model assignments (optimized for speed + cost):
- **Main**: glm-5.1
- **Vision**: qwen3.6-plus (only multimodal with good vision)
- **Everything else** (compression, session_search, skills_hub, title_generation, approval, mcp, curator, flush_memories, web_extract, delegation): deepseek-v4-flash through opencode-go endpoint

Delegation:
```yaml
delegation:
  model: deepseek-v4-flash
  provider: opencode-go
  base_url: https://opencode.ai/zen/go/v1
  max_spawn_depth: 2
  subagent_auto_approve: true
```

Note: `deepseek-v4-flash` and `deepseek-v4-pro` are accessed through the OpenCode Go provider endpoint, NOT through a separate DeepSeek provider. They use the same `GLM_API_KEY`.

## Reasoning Effort and GLM-5.1

GLM-5.1 has **thinking mode enabled by default** — it natively reasons before responding using an internal "Interleaved Thinking" pattern. This is NOT the same as OpenAI's `reasoning_effort` parameter.

| Model | Reasoning Control | API Format |
|-------|-------------------|------------|
| OpenAI o1/o3 | `reasoning_effort: "low"/"medium"/"high"` | Responses API |
| Claude | `thinking: { type: "enabled", budget_tokens: N }` | Anthropic native |
| **GLM-5.1** | `thinking: { "type": "enabled"/"disabled" }` | Chat completions |

Key points:
- **GLM-5.1 thinks by default.** No configuration needed — `reasoning_effort: ''` (empty) in Hermes config is correct.
- **No gradual levels.** Unlike OpenAI models, GLM-5.1 doesn't have `low`/`medium`/`high` reasoning. It's either thinking ON (default) or thinking OFF.
- **`reasoning_effort` config may be ignored** when using OpenCode Go with `chat_completions` API mode. The `reasoning_effort` parameter from Hermes may not map to GLM-5.1's `thinking.type` parameter — it gets passed as-is and likely ignored.
- **Forces thinking off**: Set `thinking: { "type": "disabled" }` via extra_body, but this is rarely useful since thinking mode is GLM-5.1's core strength.
- **Delegation `reasoning_effort`**: Same applies — with deepseek-v4-flash or glm-5.1 delegates, the `reasoning_effort` field in delegation config may not map correctly to the provider's thinking control. Leave empty for default behavior.

**Practical advice**: Leave `reasoning_effort: ''` in all Hermes config sections. GLM-5.1 and DeepSeek V4 already reason natively. Don't set `none`/`minimal`/`low` unless you specifically want to disable thinking (which defeats the purpose of using these models).

## STT Model Selection by Hardware

When using `stt.provider: local` (faster-whisper), model choice should match available GPU:

| Model | VRAM needed | Accuracy (es-MX) | Speed | Recommendation |
|-------|-------------|-------------------|-------|----------------|
| `tiny` | ~1 GB | Low | Very fast | Embedded/headless only |
| `base` | ~1.5 GB | Basic | Fast | Low-resource |
| `small` | ~2 GB | Decent | Good | Default |
| `medium` | ~5 GB | Very good | Medium | **Best for 8-16 GB GPU** |
| `large-v3` | ~10 GB | Excellent | Slow | Best for 16+ GB GPU |

Configure: `hermes config set stt.local.model medium`

First use auto-downloads the model (~1.5 GB for medium). GPU acceleration is automatic when CUDA is available.