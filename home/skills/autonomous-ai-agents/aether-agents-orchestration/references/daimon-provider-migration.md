# Daimon Provider Migration — Config, Auth, Templates, Runtime Verification

This reference covers provider migrations across all Daimon profiles. The original opencode-go → llmgateway incident remains below, followed by the OAuth-provider pattern learned from the openai-codex migration.

## Context

June 2026. Migrating from Ubuntu/WSL to Nobara Linux 43 (Fedora) dual-boot. The opencode-go provider (opencode.ai/zen/go/v1) ran out of credits (HTTP 401 Insufficient balance). All 6 Daimons + Prometeo were broken. Migration target: llmgateway with deepseek-v4-flash.

## The Trap

An external agent was given a prompt to change `model:` sections in all Daimon configs. It correctly changed:

```yaml
model:
  default: deepseek-v4-flash
  provider: llmgateway
  base_url: https://api.llmgateway.io/v1
  api_key: ${LLMGATEWAY_API_KEY}
```

But it did NOT add a `providers:` section. The configs looked correct on inspection. The agent reported success with verification commands passing (grep showed the right provider).

## The Failure

When Hermes tried `talk_to(action="delegate", daimon="hefesto", ...)`, the result was:

```json
{"status": "completed", "tool_calls": 0, "last_turn": null, "elapsed_seconds": 18.1}
```

Zero tool calls, null last_turn, "completed" status. The Daimon silently failed.

## Diagnostic Chain

### Step 1: Check agent.log

```bash
tail -20 ~/Escritorio/agentes/aether/home/profiles/hefesto/logs/agent.log
```

Key lines:
```
WARNING agent.auxiliary_client: resolve_provider_client: unknown provider 'llmgateway'
INFO agent.turn_context: conversation turn: model=deepseek-v4-flash provider=unknown
INFO run_agent: OpenAI client created ... provider= base_url=https://openrouter.ai/api/v1/
ERROR: Non-retryable client error: Error code: 401 - Missing Authentication header
```

The chain:
1. `resolve_provider_client()` doesn't find 'llmgateway' in the `providers:` dict (because it's empty/missing)
2. Logs `unknown provider` warning
3. Sets `provider=unknown` in turn context
4. Falls back to OpenRouter (default fallback) using the model name `deepseek-v4-flash` as-is
5. OpenRouter doesn't recognize that model name AND has no API key → 401

### Step 2: Compare with working config

Requiem's config.yaml had:
```yaml
providers:
  swiftrouter:
    base_url: https://api.swiftrouter.com/v1
    key_env: SWIFTROUTER_API_KEY
  llmgateway:
    base_url: https://api.llmgateway.io/v1
    key_env: LLMGATEWAY_API_KEY
```

Hermes' config had `providers: {}` (empty). Daimon configs had NO `providers:` section at all.

### Step 3: The fix

Add to each Daimon config.yaml:
```yaml
providers:
  llmgateway:
    base_url: https://api.llmgateway.io/v1
    key_env: LLMGATEWAY_API_KEY
```

The `key_env` field tells hermes-agent which environment variable to read for the API key. The .env file must contain that variable.

## Also Found During Migration

### Stale skills.external_dirs paths

All 6 Daimons had:
```yaml
skills:
  external_dirs:
    - /home/prometeo/Aether-Agents/home/skills
```

This path doesn't exist on Fedora (user is `arty`, not `prometeo`). Correct path:
```
/home/arty/Escritorio/agentes/aether/home/skills
```

Skills silently fail to load when the path doesn't exist — no error in logs, just empty skill list.

### Fallback providers also broken

```yaml
fallback_providers:
  - provider: openrouter
    model: deepseek/deepseek-chat-v3-0324
```

OPENROUTER_API_KEY was in the .env, but the fallback kicked in incorrectly (due to the unknown provider) and failed because the model name format was wrong for OpenRouter's naming convention.

### .env symlink required in Daimon profile dir

After adding the `providers:` section, Daimons STILL failed with 401 "Invalid LLMGateway API token." The provider was now resolved correctly (`provider=custom`, correct `base_url` in agent.log), but the API key was empty.

**Root cause:** `acp_manager.py` loads the .env from `agent.profile_path / ".env"` — the Daimon's profile directory, NOT the HERMES_HOME root. The HERMES_HOME root .env has all keys. The Daimon profile dirs (`profiles/hefesto/`, `profiles/etalides/`, etc.) did not have a .env at all.

**Fix:**
```bash
for d in hefesto etalides ariadna daedalus athena ictinus; do
  ln -sf ~/Escritorio/agentes/aether/home/.env \
         ~/Escritorio/agentes/aether/home/profiles/$d/.env
done
```

Symlink is preferred over copy: single source of truth, no stale keys on rotation.

### model: section clean pattern

Having `api_key: ${LLMGATEWAY_API_KEY}` and `base_url` in the `model:` section does NOT work. hermes-agent ignores credential fields in `model:` — it only resolves them via the `providers:` section's `key_env`.

**WRONG (looks correct, fails silently):**
```yaml
model:
  api_mode: chat_completions
  default: deepseek-v4-flash
  provider: llmgateway
  base_url: https://api.llmgateway.io/v1      # ← ignored
  api_key: ${LLMGATEWAY_API_KEY}              # ← never read from here
```

**CORRECT (clean model: section):**
```yaml
model:
  api_mode: chat_completions
  default: deepseek-v4-flash
  provider: llmgateway

providers:
  llmgateway:
    base_url: https://api.llmgateway.io/v1
    key_env: LLMGATEWAY_API_KEY               # ← resolved here, reads from .env
```

## Global Provider Migration — auxiliary: and delegation: Sections

When doing a GLOBAL provider migration (e.g., opencode-go → llmgateway), the `model:` and `providers:` sections are not the only places the old provider appears. The `auxiliary:` section in `config.yaml` has 10+ sub-sections that each independently reference the provider:

- `auxiliary.vision` — vision model for image analysis
- `auxiliary.web_extract` — model for web page extraction
- `auxiliary.compression` — model for context compression
- `auxiliary.skills_hub` — model for skill operations
- `auxiliary.approval` — model for approval prompts
- `auxiliary.mcp` — model for MCP operations
- `auxiliary.title_generation` — model for session titles
- `auxiliary.curator` — model for context curation
- `auxiliary.session_search` — model for session search
- `auxiliary.flush_memories` — model for memory flushing
- `delegation:` — model for delegate_task operations

Each has its own `provider:`, `base_url:`, and `api_key:` fields. If these still point to the old (dead) provider, those auxiliary operations silently fail even though the main model works.

**Diagnostic:**
```bash
grep -c "opencode-go" $HERMES_HOME/config.yaml    # should be 0 after migration
grep -c "opencode.ai/zen/go" $HERMES_HOME/config.yaml  # should be 0
grep -c "OPENCODE_GO_API_KEY" $HERMES_HOME/config.yaml  # should be 0
```

If any return >0, there are residual references that need replacing.

**Fix — global sed replacement (covers all sections at once):**
```bash
sed -i \
  -e 's/provider: opencode-go/provider: llmgateway/g' \
  -e 's#base_url: https://opencode.ai/zen/go/v1#base_url: https://api.llmgateway.io/v1#g' \
  -e 's/api_key: ${OPENCODE_GO_API_KEY}/api_key: ${LLMGATEWAY_API_KEY}/g' \
  $HERMES_HOME/config.yaml
```

This is safe because the `providers:` section's `key_env` field is separate from the `api_key` field in auxiliary sections. The `auxiliary:` sub-sections use `api_key: ${ENV_VAR}` directly (not `key_env`), so replacing `${OPENCODE_GO_API_KEY}` with `${LLMGATEWAY_API_KEY}` in those sections is correct.

**Lesson:** When migrating providers, run `grep -c "<old_provider>"` on the main config.yaml. If >0, there are auxiliary or delegation references that need the same migration. The `model:` section is only the tip of the iceberg.

## Migration Checklist (Complete)

For each Daimon config.yaml being migrated to a new provider:

- [ ] `model.provider` — changed to new provider name
- [ ] `model.default` — model name available on new provider
- [ ] `model:` section is clean — only `default`, `provider`, `api_mode`. NO `api_key` or `base_url` (they go in `providers:` section, not `model:`)
- [ ] `providers:` section — declares the provider with `base_url` and `key_env`
- [ ] `skills.external_dirs` — paths point to current filesystem locations
- [ ] `fallback_providers` — either working or removed
- [ ] `.env` file — contains the `key_env` variable
- [ ] `.env` symlink in Daimon profile dir — `ln -sf $HERMES_HOME/.env $HERMES_HOME/profiles/<daimon>/.env` (acp_manager.py loads from profile_path/.env, NOT HERMES_HOME/.env)
- [ ] **Global grep on HERMES_HOME config** — `grep -c "<old_provider>" $HERMES_HOME/config.yaml` returns 0 (checks auxiliary:, delegation:, and any other sections)
- [ ] **Prometeo (or other top-level agent) configs** — check their `providers:` section too; if `providers: {}`, add the provider declaration
- [ ] Verify with: `tail -20 <daimon>/logs/agent.log` — no `unknown provider` warning, no 401
- [ ] Verify with: `talk_to(action="delegate")` — `tool_calls > 0` and `last_turn` has content

## Provider Verification

Before migrating, verify the provider has the model available:

```bash
curl -s https://api.llmgateway.io/v1/models \
  -H "Authorization: Bearer $(grep LLMGATEWAY_API_KEY ~/Escritorio/agentes/aether/home/.env | cut -d= -f2)" \
  | python3 -c "import json,sys; data=json.load(sys.stdin); [print(m['id']) for m in data.get('data',[])]" \
  | grep deepseek
```

Confirmed available on llmgateway: deepseek-v3.1, deepseek-v3.2, deepseek-v4-pro, deepseek-v4-flash.

---

## OAuth Provider Migration Pattern — openai-codex

Use this pattern when moving Daimons from an API-key provider to an OAuth-backed built-in provider such as `openai-codex`.

### 1. Update both runtime configs and templates

For every Daimon, modify both:

- `home/profiles/<daimon>/config.yaml` — active runtime configuration, usually gitignored.
- `home/profiles/<daimon>/config.yaml.template` — tracked source of truth used by `setup.sh`.

If only the live config changes, a later setup/update can silently restore the old provider. If only the template changes, the current runtime remains unchanged.

Minimal built-in-provider model block:

```yaml
model:
  api_mode: chat_completions
  default: gpt-5.6-terra
  provider: openai-codex
```

Built-in providers do not need a custom `providers.<name>.base_url/key_env` declaration. Remove only the stale custom-provider block; preserve unrelated fallback providers unless the user explicitly requests strict single-provider operation.

### 2. Provision profile-local OAuth authentication

Each Daimon has its own `auth.json`. Changing `model.provider` is insufficient if the profile lacks credentials for that provider. Safely copy only the selected provider entries from the authenticated orchestrator `auth.json` into every profile while preserving all existing providers and credential pools:

- `providers["openai-codex"]`
- `credential_pool["openai-codex"]`
- `active_provider = "openai-codex"`

Do not replace the whole profile `auth.json`; doing so can destroy fallback credentials and profile-specific state. Perform the merge without printing token values. Write atomically and enforce mode `0600` because these files contain access and refresh tokens.

OAuth token copies are operationally convenient but can share refresh-token lifecycle. If later refreshes produce `invalid_grant` or token-rotation races under concurrent agents, authenticate profiles independently rather than hardening a claim that copied OAuth credentials are always durable.

### 3. Validate the configuration structure

For every live config and template, parse YAML and assert:

- `model.provider` is the target provider.
- `model.default` is the exact target model ID.
- stale custom-provider blocks are absent.
- `api_mode` remains correct.
- existing fallback lists and toolsets were not accidentally changed.

Do not trust a delegate's completion report or a grep-only check. Read/parse the resulting files directly, especially when a file-mutation verifier reports denied edits even if a later workaround claims success.

### 4. Run one real ACP smoke session per Daimon

A successful config parse does not prove authentication, provider resolution, or model availability. Spawn every Daimon with a no-tool exact-response prompt, close every session afterward, and verify the session records—not merely the text response.

Required evidence per profile:

- `status = completed`
- expected exact response is present
- `.aether/aether.db sessions.model` equals the requested model ID
- no authentication/provider error is recorded

This catches the common false-positive where a session responds through a fallback provider while the target provider is misconfigured.

### 5. Preserve repository hygiene

Provider migration commonly touches 12 files for six Daimons (six live configs plus six templates), so treat it as bulk configuration work. Keep tracked template changes on a feature branch. Before committing, inspect the existing worktree and avoid bundling unrelated skill edits, submodule dirt, caches, or runtime artifacts into the provider-migration commit.

### Compact completion checklist

- [ ] Exact model ID confirmed in a current model catalog.
- [ ] All live `config.yaml` files updated.
- [ ] All tracked `config.yaml.template` files updated.
- [ ] Stale provider declarations removed only where appropriate.
- [ ] OAuth provider and credential-pool entries merged into every profile.
- [ ] Existing credentials/fallbacks preserved.
- [ ] Every `auth.json` is mode `0600`.
- [ ] YAML parsed successfully for every config/template.
- [ ] Every Daimon completed a real ACP smoke test.
- [ ] Session database records the target model for every smoke session.
- [ ] All Daimon sessions explicitly closed.
- [ ] `.aether` decision/task/context updated after a significant migration.
