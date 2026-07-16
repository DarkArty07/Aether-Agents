# Git-Tracked config.yaml Overwrite — July 2026 Incident

## Timeline

| Date | Event |
|------|-------|
| May 27 | `config.yaml` re-added to git tracking (commit `b57caac`) with `opencode-go`/`deepseek-v4-pro` |
| July 6 | Manual migration: opencode-go → llmgateway/glm-5.2, providers section added, 11 auxiliary + delegation migrated. Config works. **NOT committed to git.** |
| July 8 | Commit `b581075` ("Hermes Can Write Now") touches config.yaml. Forked from May 27 state. All July 6 changes silently overwritten. |
| July 8 (later) | User discovers regression: "esta mal, deberia ser glm 5.2 de llm gateway lo recuerdas? que fue lo que ocurrio github sobreescribio?" |

## What Was Overwritten

| Section | Before (July 6, correct) | After (July 8, overwritten) |
|---------|--------------------------|---------------------------|
| `model.default` | `glm-5.2` | `deepseek-v4-pro` |
| `model.provider` | `llmgateway` | `opencode-go` |
| `model.base_url` | (removed) | `https://opencode.ai/zen/go/v1` |
| `providers` | `{llmgateway: {base_url, key_env}}` | `{}` |
| `auxiliary.vision.provider` | `llmgateway` | `opencode-go` |
| `auxiliary.web_extract.provider` | `llmgateway` | `opencode-go` |
| `auxiliary.compression.provider` | `llmgateway` | `opencode-go` |
| `auxiliary.session_search.provider` | `llmgateway` | `opencode-go` |
| `auxiliary.skills_hub.provider` | `llmgateway` | `opencode-go` |
| `auxiliary.approval.provider` | `llmgateway` | `opencode-go` |
| `auxiliary.mcp.provider` | `llmgateway` | `opencode-go` |
| `auxiliary.title_generation.provider` | `llmgateway` | `opencode-go` |
| `auxiliary.curator.provider` | `llmgateway` | `opencode-go` |
| `auxiliary.flush_memories.provider` | `llmgateway` | `opencode-go` |
| `delegation.provider` | `llmgateway` | `opencode-go` |

## Why It Happened

1. `config.yaml` is tracked in git (re-added May 27 after being removed in commit `67cf6cc`)
2. Manual edits on July 6 were never committed — they existed only in the working tree
3. The July 8 commit was made from a branch forked at the May 27 git state
4. Git merged/diffed against the last committed version, which had `opencode-go`
5. The working tree manual changes were silently replaced with the committed state

**This is NOT a git bug** — it's the expected behavior when a tracked file has uncommitted changes and a new commit replaces the file with a version from a different branch state. Git can't preserve uncommitted changes across a commit that touches the same file.

## How It Was Fixed

Used `hermes config set` (not `patch`/`write_file` — blocked by security guard):

```bash
hermes config set model.default glm-5.2
hermes config set model.provider llmgateway
hermes config set providers.llmgateway.base_url "https://api.llmgateway.io/v1"
hermes config set providers.llmgateway.key_env "LLMGATEWAY_API_KEY"

# 11 auxiliary sections
for section in vision web_extract compression session_search skills_hub approval mcp title_generation curator flush_memories; do
  hermes config set "auxiliary.${section}.provider" llmgateway
  hermes config set "auxiliary.${section}.base_url" "https://api.llmgateway.io/v1"
done

hermes config set delegation.provider llmgateway
hermes config set delegation.base_url "https://api.llmgateway.io/v1"
```

## Verification Chain

```bash
# Zero opencode-go references remaining
grep -c "opencode-go\|opencode.ai" home/config.yaml  # → 0 ✓

# MCP servers survived hermes config set
grep -c "mcp_servers" home/config.yaml  # → 1 ✓

# LLMGATEWAY_API_KEY present in .env
grep -c "LLMGATEWAY_API_KEY" home/.env  # → 1 ✓

# Providers section correctly configured
grep -A3 "^providers:" home/config.yaml
# providers:
#   llmgateway:
#     base_url: https://api.llmgateway.io/v1
#     key_env: LLMGATEWAY_API_KEY
```

## Permanent Fix — Applied (Commit fbd598b, July 8 2026)

The permanent fix was applied the same day the regression was discovered. Option A (untrack config.yaml, use template pattern) was chosen and executed end-to-end.

### Steps Taken

```bash
# 1. Create template with placeholder variables (same pattern as Daimon configs)
sed -e 's|/home/arty/Escritorio/agentes/aether|__AETHER_ROOT__|g' \
    -e 's|/home/arty/.hermes/hermes-agent/venv/bin/python3.11|__PYTHON_BIN__|g' \
    home/config.yaml > home/config.yaml.template

# 2. Add config.yaml to .gitignore
# (patched .gitignore: added "home/config.yaml" under Secrets section)

# 3. Remove from git tracking (file stays on disk)
git rm --cached home/config.yaml

# 4. Stage and commit
git add .gitignore home/config.yaml.template
git commit -m "fix: untrack home/config.yaml to prevent git overwrites"
# → commit fbd598b, 2 files changed, rename detected (72% similarity)
```

### Verification After Permanent Fix

```bash
# Config.yaml still on disk with correct values
head -11 home/config.yaml
# model.default: glm-5.2, provider: llmgateway ✓

# Git no longer tracks it
git ls-files home/config.yaml
# (empty = no longer tracked) ✓

# .gitignore protects it
git check-ignore home/config.yaml
# home/config.yaml ✓
```

### Template Placeholders

The template uses the same placeholder convention as Daimon configs:
- `__AETHER_ROOT__` — replaced with the absolute path to the Aether Agents repo
- `__PYTHON_BIN__` — replaced with the absolute path to the shared venv's Python

Anyone cloning the repo copies `config.yaml.template` → `config.yaml`, replaces placeholders with their local paths, and sets their model/provider. The actual `config.yaml` is never version-controlled.
