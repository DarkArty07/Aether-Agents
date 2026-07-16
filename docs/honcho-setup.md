# Honcho Memory Provider Setup

Honcho is a self-hosted memory layer for AI agents. Aether Agents integrates
Honcho as a Git submodule at `honcho-server/`. It can run with Docker Compose
or rootless Podman Compose.

## Architecture

```
Aether-Agents/
├── home/.env              ← OPENCODE_GO_API_KEY defined here
├── honcho-server/         ← Git submodule (plastic-labs/honcho + patches)
│   ├── .env.template      ← Template with ${VARIABLE} references
│   ├── .env               ← Generated from template (NOT committed)
│   ├── PATCHES.md         ← Documents all applied patches
│   └── docker-compose.yml ← Honcho services (api, deriver, redis, database)
├── docker-compose.yml     ← Parent compose (includes Honcho services)
└── scripts/setup-honcho.sh ← Automated setup script
```

## Services

| Service    | Host binding     | Description |
|------------|------------------|-------------|
| `api`      | `127.0.0.1:8010` | FastAPI server, hosts Dialectic agent |
| `deriver`  | —                | Background worker (deriver, dreamer, summarizer) |
| `database` | —                | PostgreSQL 15 + pgvector |
| `redis`    | —                | Redis 8.2 cache |

## Quick Start

```bash
# From Aether-Agents root
bash scripts/setup-honcho.sh
```

The script prefers Docker Compose when it is available; otherwise it uses
Podman Compose. Check the selected runtime without initializing the submodule,
writing `.env`, or starting containers:

```bash
bash scripts/setup-honcho.sh --detect-compose
```

The normal setup will:

1. Detect Docker Compose or Podman Compose
2. Initialize the Honcho git submodule
3. Generate `honcho-server/.env` from `honcho-server/.env.template`
4. Verify `OPENCODE_GO_API_KEY` is set in `home/.env`
5. Start all services with the detected Compose runtime

## Manual Setup

### 1. Environment Variables

Honcho reads configuration from `honcho-server/.env`. This file is generated
from `.env.template` and is **never committed to git**.

Required parent variables (in `home/.env`):
- `OPENCODE_GO_API_KEY` — OpenCode Go API key (used for all LLM calls)

Optional:
- `OPENROUTER_API_KEY` — OpenRouter API key (for embeddings; if not set,
  the setup script leaves its template placeholder unchanged)

### 2. LLM Configuration

All LLM features (deriver, dialectic, dream, summary) use:
- **Provider:** OpenCode Go (`https://opencode.ai/zen/go/v1`)
- **Model:** `deepseek-v4-flash`
- **Auth:** `${OPENCODE_GO_API_KEY}` from parent `.env`

Embeddings use:
- **Provider:** OpenRouter (`https://openrouter.ai/api/v1`)
- **Model:** `qwen/qwen3-embedding-8b` (Matryoshka, 1536 dimensions)

### 3. Patches Applied

Honcho includes several patches for DeepSeek/OpenCode Go compatibility.
See `honcho-server/PATCHES.md` for details.

Critical patches:
- **3-level structured output fallback** — DeepSeek V4 via OpenCode Go doesn't
  support `response_format`. Falls back: parse → json_schema → prompt-only JSON.
- **DeepSeek thinking disable** — Uses `extra_body` to fully suppress reasoning
  tokens on DeepSeek models.

### 4. Starting Services

Run the commands for the Compose runtime installed on your host:

```bash
# Docker Compose
docker compose up -d
docker compose logs -f api
docker compose ps
docker compose down

# Podman Compose
podman compose up -d
podman compose logs -f api
podman compose ps
podman compose down
```

### 5. Health Check

```bash
# API should respond with 200
curl http://localhost:8010/health

# Check service status with the runtime in use
docker compose ps | grep honcho
# or
podman compose ps | grep honcho
```

### 6. Data Persistence

- PostgreSQL data: Compose volume `pgdata`
- Redis data: Compose volume `redis-data`
- Database init: `honcho-server/database/init.sql`

To reset all data:

```bash
# Docker Compose
docker compose down -v   # Removes volumes!

# Podman Compose
podman compose down -v   # Removes volumes!
```

## Troubleshooting

### "Structured output unsupported by provider"

This is normal for DeepSeek V4 — the 3-level fallback kicks in automatically.
Check logs for "falling back to prompt-only JSON" messages.

### Container won't start

```bash
# Check if .env exists and has valid API keys
grep -c 'API_KEY=' honcho-server/.env

# Check the available container runtime
docker info
# or
podman info

# View service logs
docker compose logs api
# or
podman compose logs api
```

### Submodule not initialized

```bash
git submodule update --init --recursive
```
