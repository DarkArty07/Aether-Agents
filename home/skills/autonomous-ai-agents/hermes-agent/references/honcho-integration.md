# Honcho Memory Provider Integration

## Overview

Honcho is a self-hosted memory layer for AI agents. Aether Agents integrates it as a git submodule at `honcho-server/` with unified environment configuration.

## Architecture

```
Aether-Agents/
├── home/.env              ← OPENCODE_GO_API_KEY defined here
├── honcho-server/         ← Git submodule (plastic-labs/honcho + patches)
│   ├── .env.template      ← Template with ${VARIABLE} references
│   ├── .env               ← Generated from template (NOT committed)
│   ├── PATCHES.md         ← Documents all applied patches
│   └── docker-compose.yml ← Honcho services
├── docker-compose.yml     ← Parent compose (includes Honcho)
└── scripts/setup-honcho.sh ← Automated setup
```

## Key Principle: Unified API Keys

**Problem:** Honcho's `.env` has API keys in 8+ places (deriver, dialectic levels, dream, summary, embeddings). When keys rotate, editing manually is error-prone.

**Solution:** Use `.env.template` with `${VARIABLE}` references. Generate `.env` from parent project's `.env`.

```bash
# .env.template (committed to git)
DERIVER_MODEL_CONFIG__OVERRIDES__API_KEY=${OPENCODE_GO_API_KEY}
DIALECTIC_LEVELS__minimal__MODEL_CONFIG__OVERRIDES__API_KEY=${OPENCODE_GO_API_KEY}
# ... 8 more occurrences ...

# Setup script substitutes from parent .env
sed "s|\${OPENCODE_GO_API_KEY}|${OPENCODE_GO_API_KEY}|g" .env.template > .env
```

**Benefit:** One key rotation → one update → all services inherit it.

## Docker Compose Port Mapping

Honcho containers use host ports **8010/5434/6380**, not the default 8000/5432/6379:

```yaml
services:
  api:
    ports:
      - "127.0.0.1:8010:8000"  # host:container
  
  database:
    ports:
      - "127.0.0.1:5434:5432"
  
  redis:
    ports:
      - "127.0.0.1:6380:6379"
```

**Pitfall:** If you use 8000/5432/6379, you'll conflict with other services or the existing Honcho installation.

## Setup Commands

```bash
make setup-honcho      # Initialize submodule, generate .env, start services
make honcho-up         # Start services
make honcho-down       # Stop services
make honcho-logs       # Follow logs
make honcho-status     # Check health
```

## Patches Applied

See `honcho-server/PATCHES.md` for details. Critical patches:

1. **3-level structured output fallback** — DeepSeek V4 via OpenCode Go doesn't support `response_format`. Falls back: parse → json_schema → prompt-only JSON.
2. **DeepSeek thinking disable** — Uses `extra_body` to suppress reasoning tokens.
3. **Embedding dimensions** — Qwen3 MRL embeddings need explicit `dimensions=1536`.
4. **Config validation relaxed** — Allow custom vector dimensions.

**Risk:** When updating Honcho submodule, check `src/llm/backends/openai.py` for conflicts in `complete()` and `_build_params()`.

## Troubleshooting

### RateLimitError in deriver logs

**Cause:** API key has no balance or hit rate limit.

**Fix:** Check `OPENCODE_GO_API_KEY` in `home/.env`. Regenerate if expired:
```bash
# Get new key from opencode.ai
echo "OPENCODE_GO_API_KEY=*** >> home/.env

# Regenerate honcho-server/.env
bash scripts/setup-honcho.sh
```

### "Structured output unsupported by provider"

**Normal** for DeepSeek V4. The 3-level fallback handles it automatically. Check logs for "falling back to prompt-only JSON".

### Containers won't start

```bash
# Verify .env exists and has keys
grep -c 'API_KEY=' honcho-server/.env

# Check Docker daemon
docker info

# View logs
docker compose logs api deriver
```