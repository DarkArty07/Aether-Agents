# web_search "No provider configured" — Missing plugin.yaml Bug

**Date discovered:** 2026-05-27
**hermes-agent version:** v0.14.0 (pip install)
**Session:** 5+ hours of investigation across 6 restarts

## The Bug

`web_search` returns "No web search provider configured" even though:
- `config.yaml` has `web.backend: exa` and `web.search_backend: exa`
- `EXA_API_KEY` is present in `.env`
- `EXA_API_KEY` IS loaded into `os.environ` of the running process

**Root cause:** hermes-agent v0.14.0 pip package is missing `plugin.yaml` manifest files in `plugins/web/*/`. The plugin scanner skips directories without `plugin.yaml`, so `register()` is never called and `web_search_registry._providers` remains empty (`{}`).

## Investigation Timeline

### Pass 1: .env Corruption Hypothesis (DISPROVEN)

**Assumption:** `EXA_API_KEY=***` in cat/grep output meant the file was corrupted.

**What we found:** `xxd` confirmed zero occurrences of `2a2a2a` (hex for `***`). The file was intact. The `***` in tool output was `security.redact_secrets` intercepting tool stdout — not corruption on disk.

**Lesson:** ALWAYS verify with `xxd` before concluding corruption.

### Pass 2: HERMES_HOME / .env Loading Hypothesis (PARTIALLY CORRECT)

**Assumption:** `load_hermes_dotenv()` wasn't loading the .env because `HERMES_HOME` wasn't set.

**What we found:** The process launched with `--resume` from the venv binary directly (not the wrapper). `HERMES_HOME` was set by `_apply_profile_override()`, but `EXA_API_KEY` was not in `os.environ`. Creating `~/.hermes/.env` symlink fixed the env loading issue — but web_search STILL failed.

**Lesson:** Two problems can coexist. Fixing one doesn't fix both.

### Pass 3: Wrapper Fix (NECESSARY BUT INSUFFICIENT)

**Fix applied:** Modified `~/.local/bin/hermes` to export EXA_API_KEY from .env.

**Result:** After restart, `cat /proc/PID/environ` showed `EXA_API_KEY=4e1d19...f413`. The key WAS in the environment. But `web_search` STILL failed.

**Lesson:** The key being in `os.environ` is necessary but not sufficient. The provider must also be REGISTERED in the web_search_registry.

### Pass 4: Registry Inspection (DISCOVERED ROOT CAUSE)

**Heavy lifting by Hefesto** — inspected `agent.web_search_registry` via Python:

```python
from agent.web_search_registry import list_providers
providers = list_providers()
# Result: []  ← EMPTY. No providers registered.
```

Also checked `active search provider` → `NONE`.

Then checked the plugin scanner source in `hermes_cli/plugins.py`:
- `_scan_directory_level()` looks for `plugin.yaml` in each candidate directory
- Without `plugin.yaml`, the directory is silently skipped
- `register()` in `plugins/web/exa/__init__.py` is NEVER called

**Confirmed:** All 7 web plugin directories were missing `plugin.yaml`:
```
plugins/web/exa/plugin.yaml        → MISSING
plugins/web/firecrawl/plugin.yaml  → MISSING
plugins/web/tavily/plugin.yaml     → MISSING
plugins/web/parallel/plugin.yaml   → MISSING
plugins/web/searxng/plugin.yaml    → MISSING
plugins/web/brave_free/plugin.yaml → MISSING
plugins/web/ddgs/plugin.yaml       → MISSING
```

### Pass 5: The Fix

Created `plugins/web/exa/plugin.yaml`:
```yaml
name: exa
version: "1.0"
description: Exa web search and content extraction
author: Nous Research
kind: backend
```

After restart, the plugin scanner discovers it, calls `register()`, and `web_search` works.

## The Chain of Failure (Complete)

```
config.yaml: web.backend: exa           ✓
EXA_API_KEY in os.environ               ✓
  → _has_env("EXA_API_KEY") → True      ✓
  → _get_search_backend() → "exa"       ✓
      → _wsp_get_provider("exa") → ???  ← FAILS HERE
          → web_search_registry._providers.get("exa") → None
              → ActiveProviderSearchResult(None, "exa", False)
                  → provider is None → "No web search provider configured"

Why registry empty?
  → discover_plugins() scans plugins/web/
      → _scan_directory_level(".../plugins/web/")
          → For exa/ subdir:
              → Checks for plugin.yaml → MISSING
              → Skips directory entirely
                  → __init__.py never imported
                  → register() never called
```

## Persistence

This fix lives in `.venv-hermes/lib/python3.11/site-packages/plugins/web/exa/plugin.yaml` which is **inside the venv** and **gitignored**. If you:
- Recreate the venv (`rm -rf .venv-hermes && python -m venv .venv-hermes`)
- Upgrade hermes-agent (`pip install --upgrade hermes-agent`)

...the fix is lost and must be reapplied.

### Permanent Fix (for Aether Agents)

Add a post-install step to `scripts/setup.sh` that generates plugin.yaml files for all bundled web providers:

```bash
# In setup.sh, after pip install
for provider in exa firecrawl tavily parallel searxng brave_free ddgs; do
  dir="$VENV_DIR/lib/python3.11/site-packages/plugins/web/$provider"
  [ -d "$dir" ] && [ ! -f "$dir/plugin.yaml" ] && cat > "$dir/plugin.yaml" << EOF
name: $provider
version: "1.0"
description: $provider web search provider
author: Nous Research
kind: backend
EOF
done
```

## Cross-References

- Pitfall 10 Cause A: `HERMES_HOME` not set → .env not loaded (different problem, same symptom)
- Pitfall 10 Cause B: .env actually corrupted by `security.redact_secrets` (different problem, same symptom)
- `references/hermes-agent-env-loading-source-analysis.md`: How `load_hermes_dotenv()` works
- `references/dotenv-corruption-analysis.md`: How to verify .env corruption with xxd
