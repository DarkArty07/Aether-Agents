# API Key Management Patterns

Centralized API key management prevents configuration drift and simplifies key rotation.

## Problem: Distributed Keys

**Anti-pattern**: Same API key hardcoded in multiple files
```
service-a/config.yml: api_key: abc123
service-b/.env: API_KEY=***
service-c/settings.json: "apiKey": "***"
```

**Issues**:
- Key rotation requires editing N files
- Easy to miss one location
- No single source of truth

## Solution: Centralized .env with Variables

**Pattern**: Single `.env` file with variable references

```bash
# Project root .env (single source of truth)
OPENCODE_API_KEY=***
OPENROUTER_API_KEY=***

# Service configs use variables
service-a/config.yml:
  api_key: ${OPENCODE_API_KEY}

service-b/.env:
  API_KEY=${OPEN...KEY}
```

## Implementation Strategies

### 1. Docker Compose env_file

```yaml
# docker-compose.yml
services:
  app:
    env_file:
      - .env  # Loads all variables
    environment:
      - SPECIFIC_VAR=override  # Optional overrides
```

**Pros**: Automatic variable substitution
**Cons**: All variables exposed to all services

### 2. .env.template Pattern

```bash
# .env.template (committed to git)
OPENCODE_API_KEY=${OPEN...KEY}
DATABASE_URL=postgresql://user:***@localhost/db

# .env (gitignored, created from template)
OPENCODE_API_KEY=***
DATABASE_URL=postgresql://user:***@localhost/db
```

**Setup script**:
```bash
#!/bin/bash
cp .env.template .env

# Read from parent .env if exists
if [ -f ../.env ]; then
  source ../.env
  # Substitute variables in .env
  envsubst < .env.template > .env
fi

echo "✓ .env created. Edit if needed."
```

### 3. Git Submodule with Parent .env

```
parent-project/
  .env                      # OPENCODE_API_KEY=***
  submodule/
    .env.template           # Uses ${OPENCODE_API_KEY}
    .env                    # Generated from template + parent vars
```

**Workflow**:
1. Parent `.env` defines keys
2. Submodule has `.env.template` with `${VAR}` references
3. Setup script reads parent `.env`, substitutes into submodule `.env`

## Key Rotation

When API key expires or is compromised:

### Fast Path (Centralized)
```bash
# 1. Update single .env
nano .env  # Change OPENCODE_API_KEY=***

# 2. Restart services
docker compose restart

# 3. Verify
curl -H "Authorization: Bearer $OPENC...KEY" https://api.example.com/health
```

### Slow Path (Distributed - Avoid This)
```bash
# 1. Find all occurrences
grep -r "old_api_key" .

# 2. Edit each file
vim service-a/config.yml
vim service-b/.env
vim service-c/settings.json
# ... repeat N times

# 3. Restart everything
docker compose restart

# 4. Hope you didn't miss one
```

## Security Best Practices

1. **Never commit .env files**
   ```gitignore
   .env
   .env.local
   */.env
   !.env.template
   ```

2. **Use .env.example for documentation**
   ```bash
   # .env.example (committed)
   OPENCODE_API_KEY=***
   OPENROUTER_API_KEY=***
   ```

3. **Validate required keys at startup**
   ```bash
   #!/bin/bash
   required_vars=(OPENCODE_API_KEY OPENROUTER_API_KEY)
   for var in "${required_vars[@]}"; do
     if [ -z "${!var}" ]; then
       echo "ERROR: $var not set"
       exit 1
     fi
   done
   ```

4. **Use secrets manager for production**
   - Development: `.env` files OK
   - Production: AWS Secrets Manager, HashiCorp Vault, etc.

## Monitoring Key Health

```bash
# Test key validity
curl -s -H "Authorization: Bearer $OPENC...KEY" \
  https://api.example.com/health | jq '.status'

# Check key usage (if API provides metrics)
curl -s -H "Authorization: Bearer $OPENC...KEY" \
  https://api.example.com/usage | jq '.remaining'

# Alert if usage > 90%
if [ $(echo "$usage > 0.9" | bc) -eq 1 ]; then
  echo "WARNING: API key usage at ${usage}%"
fi
```

## Example: Honcho Integration

**Before** (8 hardcoded locations):
```bash
# honcho-server/.env
DERIVER_API_KEY=***
DIALECTIC_API_KEY=***
DREAM_API_KEY=***
SUMMARY_API_KEY=***
# ... 4 more
```

**After** (centralized):
```bash
# Aether-Agents/.env (single source)
OPENCODE_GO_API_KEY=***

# honcho-server/.env.template
DERIVER_API_KEY=${OPEN...KEY}
DIALECTIC_API_KEY=${OPEN...KEY}
DREAM_API_KEY=${OPEN...KEY}
# ... all use same variable

# setup-honcho.sh
#!/bin/bash
source ../.env
envsubst < honcho-server/.env.template > honcho-server/.env
```

**Result**: Key rotation = edit 1 file instead of 8.