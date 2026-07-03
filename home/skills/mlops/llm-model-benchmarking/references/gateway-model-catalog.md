# LLM Gateway Model Catalog

Snapshot of model families and tiers available on `api.llmgateway.io/v1`.
Re-query with the curl command in Step 0 to get the latest list — new models appear frequently.

## Query Command
# Query to a shell variable with the correct name (e.g. $LLMGATEWAY_API_KEY)
# NEVER use literal placeholders like "***" — curl will send an empty Bearer token
export $(grep -v '^#' /path/to/hermes/home/.env | xargs)
curl -s "https://api.llmgateway.io/v1/models" \
  -H "Authorization: Bearer $LLMGATEWAY_API_KEY" | \
  jq -r '.data[] | "\(.family)\t\(.id)\t\(.name)"' | sort
```

## Model Families (as of 2026-06-30)

### Major LLM Brands — Cheap/Expensive Tiers

| Family | Cheap Tier | Expensive Tier | Notes |
|--------|-----------|---------------|-------|
| **openai** | `gpt-5.4-mini`, `gpt-5.4-nano`, `gpt-5.5` | `gpt-5.5-pro`, `gpt-5.4-pro` | 5.5 is latest standard; 5.5-pro is top tier |
| **anthropic** | `claude-sonnet-4.6`, `claude-haiku-4.5` | `claude-opus-4.8`, `claude-opus-4.7` | User prefers sonnet over haiku as "cheap"; opus-4.8 is newest |
| **google** | `gemini-3.5-flash`, `gemini-3.1-flash-lite` | `gemini-3.1-pro-preview`, `gemini-pro-latest` | 3.5-flash confirmed; 3.0-flash is outdated |
| **deepseek** | `deepseek-v4-flash` | `deepseek-v4-pro` | Clear cheap/expensive split |
| **moonshot** | `kimi-k2.5` | `kimi-k2.6` | No dedicated "flash/mini" tier — both are full-size models |
| **xiaomi** | `mimo-v2.5` | `mimo-v2.5-pro` | v2.5 base vs pro |

### Other Notable Families

| Family | Models | Notes |
|--------|--------|-------|
| **alibaba** | qwen3-max, qwen3.7-max, qwen3.6-max-preview, qwen3-coder-480b | Huge lineup; qwen3.7-max is newest |
| **zai** | glm-5.2, glm-5.1, glm-5, glm-4.7 | GLM-5.2 is what Hermes runs on |
| **xai** | grok-4.3, grok-4.20-reasoning, grok-4.1-fast | Grok-4.3 is newest |
| **mistral** | mistral-large-2512 (Mistral Large 3), devstral-2 | |
| **meta** | llama-3.3-70b, llama-4-maverick, llama-4-scout | |
| **minimax** | minimax-m3, minimax-m2.7 | |
| **bytedance** | seed-1.8, seed-1.6-flash | Seed 1.8 is newest |
| **perplexity** | sonar, sonar-pro, sonar-reasoning-pro | Online/web-search models |

## Tier Selection Methodology

1. **User names brands** (e.g., "Claude, GPT, Gemini, MiMo, DeepSeek, Kimi")
2. **Query gateway** with the curl command above
3. **Filter by family** — list all models under each requested brand
4. **Identify cheap tier** — look for: flash, mini, nano, haiku, air suffixes
5. **Identify expensive tier** — look for: pro, opus, max, ultra suffixes (or the highest version number with no suffix)
6. **Pick most recent** — highest version number available
7. **Handle exceptions** — some brands don't have a cheap tier (e.g., Kimi). Present only one model for those.
8. **Present confirmed matrix** — never propose a model you haven't verified exists

## User Preferences (Chris)

- Prefers sonnet as Claude's "cheap" tier (not haiku)
- Wants the most recent models only — rejects outdated versions (e.g., gemini-3.0-flash was rejected as "algo viejo")
- Tests with 2 models per brand: cheap + expensive
- Brands to include: Claude, GPT, Gemini, MiMo, DeepSeek, Kimi
- Total benchmark size: ~11-12 models
