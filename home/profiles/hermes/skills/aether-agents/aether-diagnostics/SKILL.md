---
name: aether-diagnostics
description: Health check and diagnostic procedure for the Aether Agents multi-agent ecosystem. Systematic verification that Olympus MCP, Daimon profiles, SOUL.md injection, personality overlay, and project state are all functioning correctly.
version: 1.0
triggers:
  - "ecosistema no funciona"
  - "daimons not working"
  - "olympus not connecting"
  - "check aether health"
  - "diagnose multi-agent"
---

# Aether Agents Ecosystem Diagnostics

Systematic health check for when the multi-agent system isn't working as expected.

## Diagnostic Checklist

Run these checks in order. Most can be done with `terminal()` and `read_file()`.

### 1. Olympus MCP Connectivity

Olympus MUST be in the **active** config — which is determined by `HERMES_HOME`, NOT necessarily `~/.hermes/`.

**⚠️ CRITICAL: Always check which config is active first!**
```bash
# Step 0: Find the ACTIVE config location
echo $HERMES_HOME
# If set → config is at $HERMES_HOME/config.yaml (e.g. /home/prometeo/Aether-Agents/home/profiles/hermes/config.yaml)
# If unset → fallback to ~/.hermes/config.yaml

# Step 1: Check the ACTIVE config (the one Hermes actually reads)
grep -A10 'olympus' $HERMES_HOME/config.yaml

# Step 2: Check the CLI fallback (only used when HERMES_HOME is unset)
grep -A10 'olympus' ~/.hermes/config.yaml
```

**Fix if missing:** Add to the ACTIVE config ($HERMES_HOME/config.yaml):
```yaml
mcp_servers:
  olympus:
    command: /path/to/hermes-agent/venv/bin/python
    args:
      - -m
      - olympus.server
    env:
      AETHER_HOME: /path/to/Aether-Agents/home
      PYTHONPATH: /path/to/Aether-Agents/src
    enabled: true
```

**Verify discovery works:**
```bash
# ⚠️ Must use hermes-agent venv Python — system Python lacks 'yaml' module
AETHER_HOME=/path/to/Aether-Agents/home \
PYTHONPATH=/path/to/Aether-Agents/src \
/home/<user>/.hermes/hermes-agent/venv/bin/python -c "from olympus.discovery import discover_agents; from olympus.config import get_config; cfg = get_config(); agents = discover_agents(cfg); print(f'Found {len(agents)} agents'); [print(f'  {k}: {v.role}') for k,v in agents.items()]"
```

Should discover 5 Daimons (profiles with `agent:` field). Hermes is the orchestrator, not discovered. Prometeo (personal agent) has no `agent:` field and is intentionally excluded from discovery.

**Important:** Prometeo is a **personal assistant** (Christopher's), not a team Daimon. It's excluded from Olympus discovery on purpose, has no `agent:` field in config.yaml, and follows different conventions. Do NOT treat it as a Daimon in diagnostic checks.

### 2. Personality Overlay Bug

hermes-agent ships with `display.personality: "kawaii"` as the **hardcoded default**. This appends kawaii prompts to system messages, **overwriting Daimon SOUL.md identities**.

**Check ALL profiles (exclude Prometeo — it's a personal agent, not a team Daimon):**
```bash
for d in ariadna athena daedalus etalides hefesto; do
  echo -n "$d: "
  grep 'personality' /path/to/Aether-Agents/home/profiles/$d/config.yaml 2>/dev/null || echo 'NOT SET (will default to kawaii!)'
done
```

**Fix:** Add `display.personality: none` to EVERY profile config.yaml AND to `~/.hermes/config.yaml`. Valid values to disable: `none`, `default`, `neutral`.

### 3. SOUL.md Injection

Verify each Daimon's SOUL.md is properly loaded when spawned.

**Check method:** Read the profile's SOUL.md and confirm it has the Execution Context section. Then test with `talk_to(agent="ariadna", action="open")` and inspect whether the Daimon introduces itself correctly.

Common issues:
- SOUL.md exists but `system_prompt_file` is not configured → Daimon loads default personality
- ACP spawns with wrong `HERMES_HOME` → Daimon doesn't find its SOUL.md

### 4. Daimon Skills Curation

Each Daimon should have skills matching their specialty, NOT a copy of all 22+ categories.

| Daimon | Expected categories |
|--------|-------------------|
| Ariadna | aether-agents, productivity, note-taking |
| Athena | aether-agents, red-teaming, security tools |
| Daedalus | aether-agents, creative (diagramming only), software-development |
| Etalides | aether-agents, research, web |
| Hefesto | aether-agents, software-development, github, mlops |
| Hermes | all categories (orchestrator needs breadth) |
| Prometeo | productivity, email, note-taking, social-media, media (curated) |

**Check:**
```bash
ls /path/to/Aether-Agents/home/profiles/<name>/skills/
```

**Fix:** Replace the symlinked categories with curated ones. Use `skills: { categories: [...] }` in config.yaml or physically curate the skills directories.

### 5. Project State (.eter/)

For any tracked project, .eter/ should exist with structure:
```
PROJECT/.eter/
├── .hermes/   ← DESIGN.md + PLAN.md
├── .ariadna/  ← CURRENT.md + LOG.md
├── .hefesto/  ← TASKS.md
└── .etalides/ ← RESEARCH.md (only if research done)
```

**Check:** `find <project> -name '.eter' -type d`

**If missing:** Create with `mkdir -p` and seed files.

### 6. Gateway Status

```bash
systemctl --user status hermes-gateway
```

If inactive/disabled:
```bash
hermes gateway install
systemctl --user start hermes-gateway
```

Known fix: if exit code 203/EXEC, ExecStart points to stale path → run `hermes gateway install` to regenerate.

### 7. Skins Not Loading in Aether Profiles

When using `--profile` with a custom `HERMES_HOME`, the skin engine looks for custom skins at `HERMES_HOME/skins/`. If that directory doesn't exist, custom skins silently fall back to `default` with a warning log.

**Check:**
```bash
# Current HERMES_HOME
echo $HERMES_HOME

# Does skins/ exist in the profile?
ls -la $HERMES_HOME/skins/ 2>/dev/null || echo "NO skins/ directory"

# Does the matrix (or other custom) skin exist?
ls $HERMES_HOME/skins/*.yaml 2>/dev/null || echo "No custom skins found"
```

**Fix:** Create a symlink from the profile's skins/ to the global skins directory:
```bash
ln -s /home/<user>/.hermes/skins /path/to/Aether-Agents/home/profiles/hermes/skins
```

This shares ALL custom skins across the global install and the Aether profile. Alternative: copy individual `.yaml` files if you want isolation.

**Key insight:** Each Aether Daimon profile (`home/profiles/hermes/`, `home/profiles/hefesto/`, etc.) has its own `HERMES_HOME`. Skins, skills, and other resources that live under `~/.hermes/skins/` are NOT automatically available to profiles with a different `HERMES_HOME`.

### 8. Context7 MCP Package Name

The correct npm package is `@upstash/context7-mcp` (NOT `@upstreamapi/context7-mcp` which returns 404).

Config entry:
```yaml
mcp_servers:
  context7:
    command: npx
    args:
      - -y
      - "@upstash/context7-mcp"
    enabled: true
```

### 9. Personal Agent SOUL.md Completeness

Personal agents (like Prometeo) that use `delegate_task` or `talk_to` need an **Execution Context** section in their SOUL.md, just like team Daimons. Without it, they may not understand their invocation model or tool constraints.

**Check:**
```bash
grep "Execution Context" home/profiles/prometeo/SOUL.md || echo "MISSING — Prometeo needs Execution Context"
```

**Fix:** Add an Execution Context section adapted for personal agents (they speak directly to the user, not through Hermes, but still need to know they can use delegate_task).

### 10. YAML Config Validation

Config parsing errors are silent and hard to debug. Validate all profiles parse correctly:

```bash
/path/to/hermes-agent/venv/bin/python -c "
import yaml
for d in ['ariadna','athena','daedalus','etalides','hefesto','hermes']:
    try:
        with open(f'/path/to/Aether-Agents/home/profiles/{d}/config.yaml') as f:
            yaml.safe_load(f)
        print(f'{d}: OK')
    except Exception as e:
        print(f'{d}: ERROR - {e}')
"
```

**⚠️ Use the hermes-agent venv Python** (`~/.hermes/hermes-agent/venv/bin/python`), NOT system Python — system Python may lack the `yaml` module.

### 11. Empty .eter/ Subdirectories

When `.eter/` directories exist but their required files don't, the project state system breaks. Each `.eter/` subdirectory should have at minimum:
- `.hermes/` → DESIGN.md (can be empty template)
- `.ariadna/` → CURRENT.md + LOG.md
- `.hefesto/` → TASKS.md
- `.etalides/` → RESEARCH.md (only if research was done)

**Check:**
```bash
for d in .hermes .ariadna .hefesto .etalides; do
  if [ -d ".eter/$d" ]; then
    count=$(find ".eter/$d" -type f | wc -l)
    echo "$d: $count files"
  else
    echo "$d: MISSING"
  fi
done
```

### 12. MCP Tools Not Propagating to LLM Context

### 12. MCP Tools Not Propagating to LLM Context

**Problem:** MCP server tools (e.g., `mcp_olympus_talk_to`, `mcp_olympus_discover`) are registered at agent startup (visible in agent.log) but are NOT available in the LLM's tool schema in ACP sessions or delegated contexts. This is an **upstream bug in hermes-agent SDK** (not in Aether or Olympus).

**Upstream issue:** [NousResearch/hermes-agent#14986](https://github.com/NousResearch/hermes-agent/issues/14986)

**Symptoms:**
- `talk_to` and `discover` appear in agent.log as registered
- But the LLM doesn't see them as callable tools (not in tool schema sent to model)
- `delegate_task` sub-agents also lack access to MCP tools

**Root cause — 5 interconnected gaps:**

| # | File | Line | Bug |
|---|------|------|-----|
| 1 | `acp_adapter/session.py` | 542 | `enabled_toolsets=["hermes-acp"]` hardcoded — no MCP toolsets |
| 2 | `toolsets.py` | 241-258 | `hermes-acp` toolset is static list, `"includes": []` — no MCP references |
| 3 | `acp_adapter/server.py` | 290 | After MCP registration, refreshes with `["hermes-acp"]` — discards MCP tools |
| 4 | `model_tools.py` | 223-227 | `get_tool_definitions()` only resolves explicit toolsets, skips dynamic MCP ones |
| 5 | `tools/delegate_tool.py` | 60-67 | `_SUBAGENT_TOOLSETS` evaluated at import time before MCP discovery; children inherit `["hermes-acp"]` |

**Diagnosis:**
```bash
# 1. Verify MCP tools are registered (they should be)
grep "mcp_olympus" $HERMES_HOME/logs/agent.log | tail -5
# Should show: "MCP server 'olympus' (stdio): registered 6 tool(s): mcp_olympus_talk_to, ..."

# 2. Verify Olympus process is running
ps aux | grep olympus | grep -v grep

# 3. Verify the gap: check if hermes-acp toolset includes MCP tools
# In Python (using hermes venv):
$HOME/.hermes/hermes-agent/venv/bin/python -c "
from toolsets import TOOLSETS
acp = TOOLSETS.get('hermes-acp', {})
mcp_tools = [t for t in acp.get('tools', []) if t.startswith('mcp_')]
print(f'MCP tools in hermes-acp: {mcp_tools}')  # Should show [] — that's the bug
"
```

**Patches APPLIED LOCALLY (2026-04-25, will be overwritten on hermes-agent update):**

All three patches have been applied to `~/.hermes/hermes-agent/`:

1. `acp_adapter/session.py:540+` — discovers MCP toolsets from registry and adds to `enabled_toolsets` at session creation
2. `acp_adapter/server.py:290+` — includes MCP toolsets in tool surface refresh after MCP registration
3. `tools/delegate_tool.py:60+` — `_SUBAGENT_TOOLSETS` is now lazy via `_get_subagent_toolsets()`, includes dynamic MCP toolsets from registry

**Upstream issue:** https://github.com/NousResearch/hermes-agent/issues/14986
state.agent.tools = get_tool_definitions(enabled_toolsets=all_toolsets, ...)
```

*Fix C (Delegation):* Make `_SUBAGENT_TOOLSETS` lazy/dynamic to include MCP toolsets discovered at runtime.

**Applied local patches (will be overwritten on hermes-agent update):**

Patch 1 — `~/.hermes/hermes-agent/acp_adapter/session.py` (~line 540):
```python
# BEFORE:
kwargs = {
    "platform": "acp",
    "enabled_toolsets": ["hermes-acp"],
    ...
}
# AFTER:
try:
    from tools.registry import registry
    mcp_toolsets = sorted(
        ts for ts in registry.get_registered_toolset_names()
        if ts.startswith("mcp-")
    )
except Exception:
    mcp_toolsets = []
kwargs = {
    "platform": "acp",
    "enabled_toolsets": ["hermes-acp"] + mcp_toolsets,
    ...
}
```

Patch 2 — `~/.hermes/hermes-agent/acp_adapter/server.py` (~line 290):
```python
# BEFORE:
enabled_toolsets = getattr(state.agent, "enabled_toolsets", None) or ["hermes-acp"]
disabled_toolsets = getattr(state.agent, "disabled_toolsets", None)
# AFTER:
enabled_toolsets = getattr(state.agent, "enabled_toolsets", None) or ["hermes-acp"]
disabled_toolsets = getattr(state.agent, "disabled_toolsets", None)
try:
    from tools.registry import registry as _reg
    mcp_ts = [ts for ts in _reg.get_registered_toolset_names() if ts.startswith("mcp-")]
    enabled_toolsets = sorted(set(list(enabled_toolsets) + mcp_ts))
except Exception:
    pass
```

Patch 3 — `~/.hermes/hermes-agent/tools/delegate_tool.py` (~line 60):
```python
# BEFORE:
_SUBAGENT_TOOLSETS = sorted(
    name for name, defn in TOOLSETS.items()
    if name not in _EXCLUDED_TOOLSET_NAMES
    and not name.startswith("hermes-")
    and not all(t in DELEGATE_BLOCKED_TOOLS for t in defn.get("tools", []))
)
_TOOLSET_LIST_STR = ", ".join(f"'{n}'" for n in _SUBAGENT_TOOLSETS)
# AFTER:
def _get_subagent_toolsets():
    base = sorted(
        name for name, defn in TOOLSETS.items()
        if name not in _EXCLUDED_TOOLSET_NAMES
        and not name.startswith("hermes-")
        and not all(t in DELEGATE_BLOCKED_TOOLS for t in defn.get("tools", []))
    )
    try:
        from tools.registry import registry
        mcp_ts = [ts for ts in registry.get_registered_toolset_names()
                   if ts.startswith("mcp-") and ts not in _EXCLUDED_TOOLSET_NAMES]
        base = sorted(set(base) | set(mcp_ts))
    except Exception:
        pass
    return base

def _get_toolset_list_str():
    return ", ".join(f"'{n}'" for n in _get_subagent_toolsets())

_SUBAGENT_TOOLSETS = _get_subagent_toolsets()
_TOOLSET_LIST_STR = _get_toolset_list_str()
```

**⚠️ These patches are in `~/.hermes/hermes-agent/` (installed package) and will be lost on `pip install --upgrade` or `uv sync`.** Re-apply after updating hermes-agent, or check if upstream #14986 is fixed first.

### 13. delegate_task API Key Propagation

**Problem:** `delegate_task` fails with "Delegation base_url is configured but no API key was found. Set delegation.api_key or OPENAI_API_KEY."

**Root cause:** In the profile's `config.yaml`, `delegation.api_key: ''` (empty string) overrides the inherited parent API key. The delegate_tool.py code resolves credentials as:
```python
effective_api_key = override_api_key or parent_api_key
```
An empty string `''` is falsy in Python, so `'' or parent_api_key` should return `parent_api_key`. BUT the framework's validation check may reject the delegation before reaching this resolution — checking `if not api_key` which evaluates `''` as falsy.

**The API key chain:**
1. `delegation.api_key` in config.yaml → if set, overrides everything
2. Parent agent's resolved API key (from provider auth resolution)
3. `OPENCODE_GO_API_KEY` env var (for opencode-go provider)
4. `.env` file in profile directory (loaded by hermes-agent at startup)

**Diagnostic steps:**
```bash
# 1. Check delegation config
grep -A5 'delegation:' $HERMES_HOME/config.yaml
# If api_key is empty string '', that's the problem

# 2. Check if env var is available (this is what the child process sees)
env | grep OPENCODE_GO_API_KEY

# 3. Check if .env has the key
grep OPENCODE_GO_API_KEY $HERMES_HOME/.env | sed 's/=.\{5\}/=***/'

# 4. Verify the provider auth can resolve the key
# The provider "opencode-go" resolves OPENCODE_GO_API_KEY from env
# Check /home/<user>/.hermes/hermes-agent/hermes_cli/auth.py for ProviderConfig
```

**Fix:** Either:
- (a) Set `delegation.api_key` to the actual key or remove it entirely (so parent key inherits)
- (b) Ensure `OPENCODE_GO_API_KEY` is in the environment when hermes runs
- (c) Ensure `.env` is loaded by the framework (it should be, from `$HERMES_HOME/.env`)

**Note:** The `.env` file IS loaded by hermes-agent at startup, but sub-agents spawned by `delegate_task` may NOT inherit that environment unless the framework explicitly passes it. This is a known gap.

### 14. Multi-Turn MCP Communication Not Used (Behavioral Pattern)

**This is NOT a bug — it's a design pattern gap.** The MCP infrastructure fully supports multi-turn conversations within a session, but the orchestration skill and Daimon SOUL.md enforce a fire-and-forget pattern.

**What MCP supports (but nobody uses):**
- `open` → Spawns Daimon, creates session. Daimon stays alive (keep-alive).
- `message` → Send prompt (async, returns immediately). Can send MULTIPLE messages within the same session.
- `poll` → Check progress: thoughts, messages, tool_calls — streaming updates in real-time.
- `wait` → Block until Daimon completes (with timeout).
- `close` → Close session. Daimon process stays alive for next `open`.

**What the current pattern does (fire-and-forget):**
```
open → message(self-contained prompt) → wait → receive response → close
```

**What the pattern COULD be (iterative consultation):**
```
open → message("What are 3 options?") → poll → read response 
     → message("I like option B, refine it") → poll → read response 
     → message("Add these details...") → wait → close
```

**Why it doesn't work this way:**
1. Orchestration skill says "send self-contained prompt, close session" — no iteration
2. Daimon SOUL.md says "NO memory between sessions" — but keep-alive means same session IS stateful
3. Hermes (the LLM) doesn't have multi-turn conversation patterns in its orchestration prompt

**Fix approach:** Evolve the orchestration skill to support three interaction modes:
- **One-shot** (current): `message → wait → close` — for simple delegation
- **Consultative**: `message → poll → refine → message → ... → close` — for design collaboration
- **Supervisory**: `message → poll → redirect → message → close` — for course correction

### 15. Daimon CWD and .eter/ Path Resolution

**Status: RESOLVED (as of 2026-04).** This bug has been fixed in `olympus/config.py`.

**What was the bug:** `acp_client.py` was setting `cwd=aether_home` when opening ACP sessions, meaning Daimons resolved `.eter/` paths relative to `AETHER_HOME` (e.g. `.../Aether-Agents/home/.eter/`) instead of the project root (`.../Aether-Agents/.eter/`).

**Current behavior (correct):** `olympus/config.py` computes `project_root = aether_home.parent`, and `acp_client.py` uses this value as the Daimon working directory. Verify with:

```bash
# Confirm the fix is in place
grep -n 'project_root' /path/to/Aether-Agents/src/olympus/config.py
# Should show: project_root = aether_home.parent

grep -n 'project_root\|cwd' /path/to/Aether-Agents/src/olympus/acp_client.py
# Should show cwd uses project_root, not aether_home

# Verify .eter/ lands at project root (NOT inside home/)
ls -la /path/to/Aether-Agents/.eter/ 2>/dev/null && echo "OK: .eter/ at project root"
ls -la /path/to/Aether-Agents/home/.eter/ 2>/dev/null && echo "BUG STILL PRESENT: .eter/ inside home/"
```

**If .eter/ is inside `home/`:** Your installation predates the fix. Migrate:
```bash
mv /path/to/Aether-Agents/home/.eter /path/to/Aether-Agents/.eter
```

## Common Failure Patterns

| Symptom | Likely Cause | Fix |
|---------|-------------|-----|
| `talk_to()` fails / "unknown agent" | Olympus MCP not in active config | Add to `$HERMES_HOME/config.yaml` (check env var first!) |
| Daimons speak kawaii | Missing `personality: none` | Add to all profile configs (team Daimons + Hermes, not required for Prometeo) |
| Daimon has no identity | SOUL.md not loaded | Check HERMES_HOME and system_prompt_file |
| All Daimons have same skills | Skills not curated per specialty | Curate skill categories per Daimon |
| No project state between sessions | Missing `.eter/` directory | Create with proper structure |
| `mcp_olympus_talk_to` not available to LLM | MCP tools registered but not in LLM tool schema | Check agent.log for registration; requires hermes-agent fix to propagate MCP tools to all execution contexts |
| `delegate_task` fails "no API key" | `delegation.api_key: ''` in config.yaml or env not propagated | Set delegation.api_key explicitly, ensure .env loaded, or remove empty string |
| Custom skin not applying (falls back to default) | `HERMES_HOME/skins/` dir missing in profile | Symlink `~/.hermes/skins` into profile dir |
| Skin loads but colors clash (green on pink etc.) | Missing `status_bar_*` keys fall back to gold/kawaii | Define ALL 27 color keys in custom skin YAML |
| `.eter/` files inside `home/` dir | Stale install prior to fix | Run `mv home/.eter .eter` to migrate |

## Skin Engine Field Reference

When diagnosing or creating custom skins, the `skin_engine.py` validates against these fields. From the source:

**All required color keys (27):** banner_border, banner_title, banner_accent, banner_dim, banner_text, ui_accent, ui_label, ui_ok, ui_error, ui_warn, prompt, input_rule, response_border, session_label, session_border, status_bar_bg, status_bar_text, status_bar_strong, status_bar_dim, status_bar_good, status_bar_warn, status_bar_bad, status_bar_critical, voice_status_bg, completion_menu_bg, completion_menu_current_bg, completion_menu_meta_bg, completion_menu_meta_current_bg

Missing keys inherit from `default` skin (gold/kawaii) which **clashes** with dark themes. Always define ALL status_bar_* keys.

**Tool emojis must be unique** — same emoji for two tools makes them indistinguishable in the UI.

## Pitfalls

- **Always verify HERMES_HOME first**: Before diagnosing ANY config issue, run `echo $HERMES_HOME`. If set, that directory is the source of truth for config.yaml, SOUL.md, skills/, skins/, .env — everything. `~/.hermes/` is the CLI fallback used only when no profile is active. Editing `~/.hermes/config.yaml` when a profile is active has NO effect on runtime behavior and will produce false diagnostics.
- **`skills: []` is INVALID YAML**: Must use `skills: {}` for empty dict. The parser expects a dict, not a list.
- **Daimon .env files**: Each Daimon needs its own `.env` with API keys. The `.env.example` is a template — must be copied and filled.
- **Olympus starts lazily**: Daimons are spawned on first `talk_to(action="open")`. Discovery works without running Daimons, but actual communication requires `hermes acp` to be functional.
- **Skins don't cross HERMES_HOME boundaries**: Custom skins in `~/.hermes/skins/` are invisible to Aether profiles whose `HERMES_HOME` points elsewhere. Symlink each profile's `skins/` dir to `~/.hermes/skins/`, or copy `.yaml` files manually.
- **Prometeo is personal, not a Daimon**: It has no `agent:` field, no Olympus registration, speaks directly to Christopher (not through Hermes), and is gitignored. Don't include it in Daimon-level diagnostic checks.
- **YAML validation catches silent errors**: `skills: []` parses OK but breaks at runtime. Use `yaml.safe_load()` to verify configs. System Python may lack `yaml` — use hermes-agent venv Python.
- **Daimons write .eter/ files at correct path**: `olympus/config.py` computes `project_root = aether_home.parent`, and `acp_client.py` uses this as the Daimon working directory. If you find `.eter/` inside the `home/` directory, your installation predates the fix — migrate with `mv home/.eter .eter`.
- **project_root derivation**: The current code derives `project_root = aether_home.parent`, which is correct for the standard layout where Aether-Agents IS the project. When working on external projects (Artemisa, Zeus), you must ensure `PROJECT_ROOT` in the Daimon prompt points to the correct external project so Daimons write `.eter/` to the right place — not into the Aether-Agents repo. Pass `PROJECT_ROOT: /path/to/external/project` explicitly in every delegation prompt.
- **MCP tools don't propagate to sub-agents**: Fixed locally (2026-04-25) with 3 patches to hermes-agent. Upstream issue #14986 pending. Patches will be lost on update — reapply if upstream hasn't fixed it yet.
- **Daimons identify as Hermes (SOUL.md not loading)**: Fixed in `src/olympus/acp_client.py` (2026-04-25). Root cause: hermes CLI's `_apply_profile_override()` reads `active_profile` file and overwrites `HERMES_HOME`, ignoring the env var set by Olympus. Fix: added `--profile <agent_name>` to spawn command so the CLI resolves the correct profile. Without this, all Daimons load Hermes's config/SOUL.md.
- **Fire-and-forget is not the only pattern**: The orchestration skill enforces `open → message → wait → close` but MCP supports `open → message → poll → message → poll → message → close` (multi-turn within session). Don't assume Daimons can only receive one prompt per session — keep-alive means the session persists and context carries over between messages.