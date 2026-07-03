# Honcho Integration

Honcho is the official memory provider for Aether Agents, integrated as a git submodule with centralized configuration.

## Architecture

```
~/Aether-Agents/
  .env                      # Single source of truth for API keys
  honcho-server/            # Git submodule (plastic-labs/honcho)
    .env.template           # Uses ${OPENCODE_GO_API_KEY}
    PATCHES.md              # Custom patches applied
    docker-compose.yml      # Honcho services
```

## Setup

```bash
# 1. Initialize submodule
git submodule update --init

# 2. Copy template and fill API keys
cp honcho-server/.env.template honcho-server/.env
# Edit .env: replace ${OPENCODE_GO_API_KEY} with actual key from parent .env

# 3. Start services
docker compose up -d
```

## Patches Applied

Honcho has 4 custom patches for OpenCode Go compatibility:

### 1. Response Format Fallback (Critical)
**File**: `src/llm/backends/openai.py`

Adds 3-level fallback for structured output:
- Level 0: `client.chat.completions.parse()` (Pydantic)
- Level 1: `json_schema` format
- Level 2: Prompt-only JSON with instruction injection

**Why**: DeepSeek V4 models don't support `response_format` parameter.

### 2. Embedding Dimensions
**File**: `src/embedding_client.py`

Passes `dimensions=1536` to embedding API calls for Qwen3-Embedding-8B MRL.

### 3. Config Validation Relaxed
**File**: `src/config.py`

Comments out forced `VECTOR_DIMENSIONS=1536` validation to allow custom dimensions.

### 4. Thinking Disable via extra_body
**File**: `src/llm/backends/openai.py` (`_build_params`)

Sets `extra_body={"thinking": {"type": "disabled"}}` when `thinking_effort="none"`.

**Why**: DeepSeek still generates reasoning tokens with just `reasoning_effort="none"`.

## API Key Management

**Problem**: Honcho uses API key in 8+ places (deriver, dialectic, dream, summary, embeddings).

**Solution**: 
- Single `OPENCODE_GO_API_KEY` in parent `.env`
- Honcho `.env` uses `${OPENCODE_GO_API_KEY}` variable
- When key changes, update only parent `.env`

## Upgrading Honcho

```bash
cd honcho-server
git fetch origin
git merge origin/main
# Check PATCHES.md for conflicts in:
# - src/llm/backends/openai.py (complete(), _build_params())
# - src/embedding_client.py
# - src/config.py
# Re-apply patches if overwritten
```

## Verification

```bash
# Check Honcho is running
docker compose ps

# Test memory provider
curl http://localhost:8010/health

# Test Hermes can access Honcho
hermes honcho_status
```

## Common Issues

### Honcho Not Starting (Port Conflicts)
**Symptom**: `docker compose up` fails with "Bind for 127.0.0.1:8010 failed: port is already allocated", but `ss -tlnp` and `lsof` show no listeners.
**Cause**: Orphaned docker-proxy processes from previous compose instances.
**Fix**:
```bash
# Kill docker-proxy holding the ports
sudo fuser -k 8010/tcp 5434/tcp 6380/tcp

# Clean Docker state
docker container prune -f
docker network prune -f

# Retry
docker compose up -d
```

### Data Loss: docker compose down --volumes
**Symptom**: All Honcho memory, profiles, and observations disappear after restart.
**Cause**: `docker compose down --volumes` deletes named volumes (pgdata, redis-data).
**⚠️ NEVER use --volumes unless you intend to wipe all data.**
**Safe**: `docker compose down` or `docker compose down --remove-orphans` (removes containers, keeps data).

### docker compose up -d Blocked by Terminal
**Symptom**: Hermes terminal refuses "long-lived server process" even with `-d` flag.
**Fix**: Use `terminal(background=true, notify_on_complete=true)` for docker compose commands.

### Honcho Not Starting (Env)
**Symptom**: `docker compose up` fails
**Fix**: Check `.env` has all required variables (not `${...}` placeholders)

### Memory Provider Unavailable
**Symptom**: Hermes says "Honcho not configured"
**Fix**: Verify `HONCHO_URL=http://localhost:8010` in Hermes config

### API Key Not Working
**Symptom**: Honcho logs show 401/403 errors
**Fix**: Update `OPENCODE_GO_API_KEY` in parent `.env`, restart Honcho

### Patches Lost After Upgrade
**Symptom**: Structured output fails
**Fix**: Re-apply patches from `PATCHES.md`

## Backup Strategy

**Critical**: Honcho's PostgreSQL database contains all accumulated memory. Without backups, `docker compose down --volumes` or disk failure means permanent data loss.

### Scheduled pg_dump Backup

```bash
# Create backup directory
mkdir -p ~/Aether-Agents/backups/honcho

# Dump the Honcho database (runs inside postgres container)
docker exec honcho-server-database-1 pg_dump -U honcho -d honcho \
  > ~/Aether-Agents/backups/honcho/honcho-$(date +%Y%m%d-%H%M).sql

# Keep only last 7 backups
ls -t ~/Aether-Agents/backups/honcho/honcho-*.sql | tail -n +8 | xargs rm -f
```

### Restore

```bash
# Stop services
docker compose down

# Restore from backup
cat ~/Aether-Agents/backups/honcho/honcho-YYYYMMDD-HHMM.sql | \
  docker exec -i honcho-server-database-1 psql -U honcho -d honcho

# Restart
docker compose up -d
```

### Cron Automation

Set up a cron job in Hermes to dump every 6 hours:
```bash
hermes cron create "0 */6 * * *" --name "honcho-backup" --prompt \
  "Run: docker exec honcho-server-database-1 pg_dump -U honcho -d honcho > ~/Aether-Agents/backups/honcho/honcho-$(date +%Y%m%d-%H%M).sql && ls -t ~/Aether-Agents/backups/honcho/honcho-*.sql | tail -n +8 | xargs rm -f"
```