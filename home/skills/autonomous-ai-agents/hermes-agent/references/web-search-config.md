# Web Search Configuration Pitfall

## Symptom

`web_search` or `web_extract` return "No web search provider configured. Run 'hermes tools' to set one up." even though:
- `EXA_API_KEY` (or other provider key) is present in `.env`
- `web.backend: exa` is set in `config.yaml`
- The API key works when tested directly with `curl`

## Root Cause

In `config.yaml`, when `search_backend: ''` or `extract_backend: ''` (empty YAML strings) appear under `web:`, they **override** the `backend:` key — even though they look inert. An empty string means "no provider" → error. These per-capability keys take precedence over the generic `backend` key regardless of their value.

## Fix

Remove the empty-string keys entirely so `backend` cascades to both capabilities:

```yaml
# BROKEN — empty strings override backend
web:
  backend: exa
  search_backend: ''      # ← overrides backend for search
  extract_backend: ''     # ← overrides backend for extract

# FIXED — backend applies to both
web:
  backend: exa
  use_gateway: false
```

Alternatively, set them to explicit values:
```yaml
web:
  backend: exa
  search_backend: exa
  extract_backend: exa
```

## Config Caching Pitfall

Config changes require starting a **new CLI session** to take effect. Restarting the gateway (`systemctl restart`) is NOT sufficient for an already-running CLI session — the config is loaded once at startup and cached in memory.

**To apply a config fix:**
1. Edit `config.yaml` (or run `hermes config set ...`)
2. For gateway/Telegram: `systemctl --user restart hermes-gateway.service`
3. For CLI: exit and re-enter the session (new `hermes` process)

Just restarting the gateway while the CLI session is still running will NOT reload the config for that CLI session.

## Diagnostic Approach

When `web_search` fails:

1. **Verify `.env` has the API key:**
   ```bash
   grep '^EXA_API_KEY=' ~/.hermes/.env  # or $HERMES_HOME/.env
   ```

2. **Check `config.yaml` web section:**
   ```bash
   grep -A5 '^web:' config.yaml
   ```
   Confirm `backend: exa` (or your provider) and NO empty `search_backend` / `extract_backend`.

3. **Test the key directly:**
   ```bash
   EXA_KEY=$(grep '^EXA_API_KEY=' .env | cut -d= -f2)
   curl -s -X POST "https://api.exa.ai/search" \
     -H "x-api-key: $EXA_KEY" \
     -H "Content-Type: application/json" \
     -d '{"query":"test","numResults":1}'
   ```
   If this returns results, the key is valid — the problem is config, not auth.

4. **Run `hermes doctor`** — reports tool availability and config status.

5. **Start a new CLI session** after any config change to verify.

## Provider Reference

| Backend | Env Var | Search | Extract | Crawl |
|---------|---------|--------|---------|-------|
| **Exa** | `EXA_API_KEY` | ✔ | ✔ | — |
| **Firecrawl** | `FIRECRAWL_API_KEY` | ✔ | ✔ | ✔ |
| **Tavily** | `TAVILY_API_KEY` | ✔ | ✔ | ✔ |
| **Parallel** | `PARALLEL_API_KEY` | ✔ | ✔ | — |
| **SearXNG** | `SEARXNG_URL` | ✔ | — | — |

When mixing providers (e.g., free search + paid extract):
```yaml
web:
  search_backend: searxng
  extract_backend: exa
```

Only set `search_backend` / `extract_backend` when you intentionally want different providers for each capability. Never leave them as empty strings.