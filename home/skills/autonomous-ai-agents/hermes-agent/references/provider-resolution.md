# Hermes Agent — Provider Resolution Architecture

Source: runtime_provider.py, auth.py, config.py (hermes-agent source code, v2026.4.16)

## Resolution Flow (runtime_provider.py:961)

```
resolve_runtime_provider()
  │
  ├─ 1. resolve_requested_provider()           # runtime_provider.py:357
  │      ├─ explicit arg? → return
  │      ├─ model.provider in config.yaml? → return
  │      ├─ HERMES_INFERENCE_PROVIDER env? → return
  │      └─ default → "auto"
  │
  ├─ 2. _resolve_named_custom_runtime()        # runtime_provider.py:~550
  │      ├─ bare "custom" + explicit base_url → direct-alias
  │      ├─ _get_named_custom_provider()
  │      │    ├─ providers: dict in config.yaml (new-style)
  │      │    └─ custom_providers: list (legacy)
  │      └─ _try_resolve_from_custom_pool()     # credential pool lookup
  │
  ├─ 3. resolve_provider() from auth.py         # auth.py:1433
  │      ├─ PROVIDER_REGISTRY lookup
  │      ├─ If not found + not "auto" → AuthError
  │      ├─ If "auto" → check auth.json active_provider
  │      ├─ If "auto" → auto-detect by env vars (OPENROUTER_API_KEY, etc.)
  │      └─ If "auto" → Bedrock (boto3) → AuthError if nothing
  │
  ├─ 4. _resolve_explicit_runtime()             # runtime_provider.py:814
  │      └─ Only fires when explicit_api_key or explicit_base_url passed
  │
  ├─ 5. Credential pool: load_pool(provider)    # auth.json credential_pool
  │      └─ Pool entry → _resolve_runtime_from_pool_entry()
  │
  └─ 6. Provider-specific resolution
         ├─ anthropic, openai, openrouter, zai, kimi-coding, etc.
         └─ Returns: {provider, api_mode, base_url, api_key, source, ...}
```

## PROVIDER_REGISTRY (auth.py:161)

Built-in providers with their env vars and base URLs:
- opencode-go: OPENCODE_GO_API_KEY → https://opencode.ai/zen/go/v1
- opencode-zen: OPENCODE_ZEN_API_KEY → https://opencode.ai/zen/v1
- openrouter: OPENROUTER_API_KEY → https://openrouter.ai/api/v1
- openai: OPENAI_API_KEY → https://api.openai.com/v1
- anthropic: ANTHROPIC_API_KEY → https://api.anthropic.com
- zai: ZAI_API_KEY → https://api.z.ai/api/coding/paas/v4
- kimi-coding: KIMI_API_KEY → https://api.kimi.com/coding
- glm: GLM_API_KEY → (via ZAI registry)
- minimax: MINIMAX_API_KEY
- Nous: OAuth (agent_key, short-lived ~30min TTL)
- copilot: GitHub CLI auth → https://api.githubcopilot.com
- bedrock: boto3 IAM/SSO

Aliases (auth.py:1401):
  opencode → opencode-zen, go → opencode-go, kimi → kimi-coding

## Key Sources of Truth

| Component | File | Purpose |
|-----------|------|---------|
| Provider registry | auth.py:161 | Built-in providers, env vars, base URLs |
| Provider resolution | auth.py:1433 (resolve_provider) | Maps name → canonical ID, handles auto-detect |
| Runtime resolution | runtime_provider.py:961 | Full chain: config → pool → API key |
| Credential pool | agent/credential_pool.py | Multi-key rotation, cooldowns |
| Auth store | ~/.hermes/auth.json | OAuth tokens, pool entries, active_provider |
| Config | ~/.hermes/config.yaml | model.provider, model.default, providers: dict |
| Custom providers | config.yaml providers: or custom_providers: | User-defined endpoints |
| Config migrations | config.py:3399+ | Auto-patches config on version bumps |

## config set (config.py:5017)

`hermes config set <dotted.key> <value>`:
- API keys → goes to .env (not config.yaml)
- Other keys → reads raw user config, applies _set_nested(), writes back
- Does NOT touch merged defaults — only user overrides
- Migrations run on next startup if _config_version is stale

## Gateway Hot-Reload Behavior

Gateway DOES hot-reload (without restart):
- compression.* keys
- model.context_length
- Some display settings

Gateway DOES NOT hot-reload (requires restart):
- model.provider
- model.default
- model.base_url
- API keys
- toolset changes
- providers: dict additions

Fix: `systemctl --user restart hermes-gateway`

## auth.json active_provider Override (Issue #29285)

When auth.json has `active_provider` set (from `hermes login` or OAuth):
- resolve_provider("auto") checks active_provider BEFORE env vars
- This can silently override model.provider in config.yaml
- Fix: manually edit auth.json to set active_provider: null
- Or: explicitly set model.provider in config.yaml (resolve_requested_provider returns before hitting auto path)

## providers: {} vs custom_providers: []

- `providers:` (dict) — new-style, keyed by provider name, uses key_env or api_key
- `custom_providers:` (list) — legacy, list of {name, base_url, api_key/key_env}
- Empty `providers: {}` is NORMAL for built-in providers (opencode-go, openrouter, etc.)
- providers: block only needed for user-defined custom endpoints
