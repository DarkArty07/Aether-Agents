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

**Fix:** Use `external_dirs` in each Daimon's `config.yaml` to point to the shared `home/skills/` directory. Never use symlinks or copies. Ensure the Daimon's local `skills/` directory only contains their aether-agent workflow skill.

```yaml
# In each Daimon's config.yaml:
skills:
  external_dirs:
    - /path/to/Aether-Agents/home/skills
```

```bash
# Verify: each Daimon sees the shared skills directory
for d in ariadna athena daedalus etalides hefesto hermes; do
  echo "$d: $(grep -A2 'external_dirs' /path/to/profiles/$d/config.yaml)"
done
```

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

### 12. Profile Resolution Fails for External Profiles (`-p` flag)

**Problem:** `hermes -p prometeo` fails with "Profile 'prometeo' does not exist" even though the profile directory exists and works with the wrapper script.

**Root cause:** `_apply_profile_override()` in `hermes_cli/main.py` resolves the profile name by calling `resolve_profile_env('prometeo')`, which calls `get_profile_dir('prometeo')` → `_get_profiles_root() / 'prometeo'`. The `_get_profiles_root()` function uses `get_default_hermes_root()` which checks `HERMES_HOME`:

- **HERMES_HOME unset** → `get_default_hermes_root()` returns `~/.hermes` → profiles searched in `~/.hermes/profiles/prometeo` → symlink resolves ✅
- **HERMES_HOME=/home/prometeo/.prometeo** (wrapper script) → `get_default_hermes_root()` returns `/home/prometeo/.prometeo` → profiles searched in `.prometeo/profiles/prometeo` → exists ✅
- **HERMES_HOME=/home/prometeo/Aether-Agents/home/profiles/hermes** (Aether session) → `get_default_hermes_root()` detects parent is `profiles/`, returns `/home/prometeo/Aether-Agents/home` → profiles searched in `Aether-Agents/home/profiles/prometeo` → **DOES NOT EXIST** ❌

The profile system always searches under the **effective hermes root**, not under `~/.hermes/`. When another profile's HERMES_HOME is active, profiles that only exist as symlinks under `~/.hermes/profiles/` become invisible.

**Diagnostic steps:**
```bash
# Step 1: Check current HERMES_HOME
echo $HERMES_HOME

# Step 2: Check if profile resolves correctly
hermes -p prometeo config path
# If ERROR: Profile doesn't exist under current hermes root

# Step 3: Check what profiles exist under current root
ls $(dirname $(hermes config path))/../profiles/
# These are the only profiles visible with the current HERMES_HOME

# Step 4: Verify profile exists under ~/.hermes (symlink)
ls -la ~/.hermes/profiles/prometeo
# Should show symlink → /home/prometeo/.prometeo/profiles/prometeo

# Step 5: Test with clean environment (unset HERMES_HOME)
env -u HERMES_HOME hermes -p prometeo config path
# If this works but Step 2 failed, the issue is HERMES_HOME interference
```

**Fix options (pick one):**

**Option A: Symlink in each external HERMES_HOME (recommended for multi-profile setups)**
```bash
# Add a symlink in the Aether Agents profiles directory
ln -s /home/prometeo/.prometeo/profiles/prometeo /home/prometeo/Aether-Agents/home/profiles/prometeo
```
This makes `prometeo` discoverable regardless of which HERMES_HOME is active. Repeat for any other external profile locations.

**Option B: Use the wrapper script (always works)**
```bash
~/.local/bin/prometeo chat
# or equivalently:
HERMES_HOME=/home/prometeo/.prometeo hermes -p prometeo chat
```
The wrapper sets HERMES_HOME before calling hermes, so profile resolution always searches the correct root.

**Option C: Unset HERMES_HOME before running**
```bash
env -u HERMES_HOME hermes -p prometeo chat
```
This forces fallback to `~/.hermes` where the symlink exists. Works but risks losing the current session's profile context.

**Important:** `hermes profile create prometeo` would create a NEW blank profile under `~/.hermes/profiles/prometeo/`, overwriting the symlink. Do NOT use this to "fix" a symlinked profile — it breaks the link and creates a separate, empty profile.

### 13. MCP Tools Not Propagating to LLM Context

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

### 15. Workflow Engine Technical Debt — FIXED (2026-04-26)

**All 7 critical issues resolved in commit `daed7e0`:**

| # | Issue | Fix |
|---|-------|-----|
| 1 | **Double-escape bug**: Prompts sent `\\n` (literal backslash-n) instead of `\n` (newline) | Changed all `\\n` to `\n` in nodes.py f-strings |
| 2 | **Session leak**: `_run_acp_session` never closed ACP sessions | Added `try/finally` with `close_session()` |
| 3 | **No stall detection**: `completion_event.wait()` blocked indefinitely if agent hung | Progress Watchdog: polls every 10s for activity (thoughts/messages/tool_calls). Stalls after 120s of no activity |
| 4 | **No error recovery**: Error strings fed into next nodes as valid input | Added `errors` list to WorkflowState, `should_terminate_on_error` edge, and per-node try/except |
| 5 | **No logging**: Nodes produced zero logs during execution | Added `[workflow]` start/complete/failed logging with timing |
| 6 | **State incomplete**: WorkflowState lacked error tracking and lifecycle metadata | Added `errors`, `status`, `started_at`, `node_name` fields |
| 7 | **No error edges**: Workflows continued even after node failures | Added `should_terminate_on_error` conditional edges to all 3 workflows |

**Progress Watchdog parameters:**
- `POLL_INTERVAL = 10s` — check for activity every 10 seconds
- `STALL_TIMEOUT = 120s` — if no activity for 2 minutes, mark as STALLED
- `STALL_TIMEOUT = 120s` — if no activity for 2 minutes, agent is considered stalled
- There is NO separate "hard timeout" or "30 min safety ceiling" — this was previously documented but never implemented. STALL_TIMEOUT is the only timeout mechanism.

**Key design principle:** Hard timeouts are wrong for agent workflows. An actively working agent (producing thoughts, tool calls) is given unlimited time. Only agents that emit ZERO activity for 120 seconds are considered stalled.

**Diagnostic:**
```bash
# Verify the fix is in place
grep 'STALL_TIMEOUT' /path/to/Aether-Agents/src/olympus/workflows/nodes.py
# Should show: STALL_TIMEOUT = 120

grep 'close_session' /path/to/Aether-Agents/src/olympus/workflows/nodes.py
# Should show: await acp.close_session(session.session_id) in finally block

grep 'should_terminate_on_error' /path/to/Aether-Agents/src/olympus/workflows/definitions.py
# Should show conditional edges after research, design, implement nodes

# Verify all 3 workflows compile
cd /path/to/Aether-Agents && python3 -c "
from src.olympus.workflows.definitions import get_workflow
class MockACP: pass
for name in ['feature', 'bug-fix', 'research']:
    g = get_workflow(name, MockACP())
    print(f'✅ {name}: OK')
"
```

### 15b. Workflow Runner — `send_message` AttributeError (HISTORICAL)

**Status: FIXED (2026-04-26)** in `src/olympus/workflows/nodes.py` and `pyproject.toml`.

**Symptom:** `run_workflow` tool returns `Error: 'ACPManager' object has no attribute 'send_message'`. Workflow completes its cycle counter but no Daimon actually runs.

**Root cause — 3 bugs in `nodes.py`:**

| # | Line | Bug | Fix |
|---|------|-----|-----|
| 1 | 18 | `acp.send_message(session_id, prompt)` — method doesn't exist on `ACPManager` | Changed to `acp.send_prompt(session.session_id, prompt)` |
| 2 | 14-15 | `session_id = await acp.open_session(agent_name)` — `open_session` returns `SessionState`, not a string | Changed to `session = await acp.open_session(agent_name)`, use `session` object directly |
| 3 | 20 | `acp.registry.get_session(session_id)` — redundant lookup with wrong type; `session` already holds the `SessionState` | Removed; use `session` from `open_session` directly |

**Additional bug:** `langgraph` was missing from `pyproject.toml` dependencies. The workflow imports `langgraph.graph.StateGraph` and `langgraph.graph.message.add_messages` but the package wasn't listed. Added `langgraph>=0.2.0` to dependencies.

**Diagnostic:** If workflows fail silently or with `AttributeError`, check:
```bash
# 1. Verify the fix is in place
grep 'send_prompt' /path/to/Aether-Agents/src/olympus/workflows/nodes.py
# Should show: await acp.send_prompt(session.session_id, prompt)

# 2. Verify langgraph is installed
pip show langgraph 2>/dev/null || echo "MISSING — install with: pip install langgraph"

# 3. Verify langgraph is in pyproject.toml
grep langgraph /path/to/Aether-Agents/pyproject.toml
```

**Key insight:** `_run_acp_session` is a synchronous-style helper that runs a full open→send→wait→collect cycle. It must use `open_session()` (which returns `SessionState`) and `send_prompt()` (which is fire-and-forget with `asyncio.create_task`), not `send_message` (which doesn't exist). The `SessionState` object has a `completion_event` that gets set when the background task finishes.

### 16. Daimon CWD and .eter/ Path Resolution

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

### 17. Profile Resolution — How `-p` and HERMES_HOME Interact

**Critical for anyone running multiple profiles (external HERMES_HOME).**

The `_apply_profile_override()` function in `hermes_cli/main.py` (line 99-160) runs **before any hermes module imports**. It parses `sys.argv` for `--profile/-p`, resolves the profile name to a directory via `resolve_profile_env()`, and sets `os.environ["HERMES_HOME"]` to that directory.

The resolution chain is:

```
-p prometeo
  → get_profile_dir('prometeo')
    → _get_profiles_root() / 'prometeo'
      → get_default_hermes_root() / 'profiles' / 'prometeo'
```

**The problem:** `get_default_hermes_root()` (in `hermes_constants.py`) behaves differently depending on whether `HERMES_HOME` is already set:

| Current HERMES_HOME | get_default_hermes_root() returns | Profiles root |
|---|---|---|
| Unset | `~/.hermes` | `~/.hermes/profiles/` |
| `~/.hermes/profiles/coder` (under ~/.hermes) | `~/.hermes` | `~/.hermes/profiles/` |
| `/opt/data/profiles/coder` (Docker, parent="profiles") | `/opt/data` | `/opt/data/profiles/` |
| `/home/prometeo/Aether-Agents/home/profiles/hermes` (parent="profiles") | `/home/prometeo/Aether-Agents/home` | `/home/prometeo/Aether-Agents/home/profiles/` |
| `/home/prometeo/.prometeo` (not under ~/.hermes, no "profiles" parent) | `/home/prometeo/.prometeo` | `/home/prometeo/.prometeo/profiles/` |

**This means:** When HERMES_HOME is set to Aether Agents (`/home/prometeo/Aether-Agents/home/profiles/hermes`), running `hermes -p prometeo` looks for the profile at `/home/prometeo/Aether-Agents/home/profiles/prometeo` — which doesn't exist. It does NOT fall back to `~/.hermes/profiles/prometeo`.

**The correct way to launch external profiles:** Always use the wrapper script created by `hermes profile create`. The wrapper sets HERMES_HOME explicitly:

```bash
# ~/.local/bin/prometeo
#!/bin/sh
export HERMES_HOME=/home/prometeo/.prometeo
exec hermes -p prometeo "$@"
```

This ensures profile resolution happens from the correct root, regardless of any HERMES_HOME already in the environment.

**Diagnostic:**
```bash
# 1. Check wrapper script for profile
cat ~/.local/bin/<profile-name>

# 2. Verify profile resolution from clean shell (no HERMES_HOME)
unset HERMES_HOME; hermes -p <name> config path

# 3. Verify wrapper works from any context
~/.local/bin/<profile-name> config path

# 4. If -p fails from within another session, check current HERMES_HOME
echo $HERMES_HOME
```

**Cross-profile isolation rule:** External profiles (Prometeo in `.prometeo/`, Aether in `Aether-Agents/home/`) are separate agents with separate homes. Do NOT create symlinks between their `profiles/` directories. Each agent uses its own wrapper script that sets the correct HERMES_HOME.

### 17. External Profile Launch Failure (`hermes -p <name>` fails from another session)

**Problem:** `hermes -p prometeo` returns "Profile 'prometeo' does not exist" when HERMES_HOME is already set to an external directory (e.g., Aether Agents).

**Root cause:** Profile resolution in `_apply_profile_override()` (hermes_cli/main.py:99-160) uses `get_profile_dir(name)` which calls `_get_profiles_root()` which calls `get_default_hermes_root()`. When HERMES_HOME is already set to an external path like `/home/prometeo/Aether-Agents/home/profiles/hermes`, `get_default_hermes_root()` detects the parent is `profiles/` and returns the grandparent `/home/prometeo/Aether-Agents/home`. Then `_get_profiles_root()` returns `/home/prometeo/Aether-Agents/home/profiles/`, and `get_profile_dir('prometeo')` looks for `/home/prometeo/Aether-Agents/home/profiles/prometeo/` which doesn't exist.

**Key insight:** Profiles are scoped to their HERMES_HOME root. An external agent (like Prometeo at `~/.prometeo/`) has its own profile tree invisible to a different root (like Aether Agents at `Aether-Agents/home/`).

**The correct way to launch external profiles:** Use the wrapper script at `~/.local/bin/<name>`. This script sets HERMES_HOME to the external root BEFORE calling hermes:

```bash
#!/bin/sh
export HERMES_HOME=/home/prometeo/.prometeo
exec hermes -p prometeo "$@"
```

**Diagnosis:**
```bash
# 1. Does the wrapper exist?
cat ~/.local/bin/prometeo

# 2. Does the profile directory exist?
ls -la ~/.prometeo/profiles/prometeo/  # External profile location
ls -la ~/.hermes/profiles/prometeo/     # Symlink (if created by hermes profile create)

# 3. Test resolution from clean environment
unset HERMES_HOME; hermes -p prometeo config path  # Should work via symlink
~/.local/bin/prometeo config path                    # Should work via wrapper

# 4. Test resolution with HERMES_HOME set to another root (FAILS for external profiles)
HERMES_HOME=/path/to/Aether-Agents/home/profiles/hermes hermes -p prometeo config path
# → ERROR: Profile 'prometeo' does not exist
```

**Fix options:**
- **Best:** Always use the wrapper script (`prometeo chat`) to launch external profiles
- **Alternative:** Create a symlink in the Aether profiles directory: `ln -s /home/prometeo/.prometeo/profiles/prometeo /home/prometeo/Aether-Agents/home/profiles/prometeo`
- **Never:** Set HERMES_HOME manually and rely on `-p` alone — it fails cross-root

**Profile resolution diagram:**
```
hermes -p <name> resolution:
  1. Parse -p <name> from argv (before any imports)
  2. resolve_profile_env(name) → get_profile_dir(name) → _get_profiles_root() / name
  3. _get_profiles_root() = get_default_hermes_root() / "profiles"
  4. get_default_hermes_root() depends on HERMES_HOME:
     - No HERMES_HOME → ~/.hermes
     - HERMES_HOME under ~/.hermes → ~/.hermes (standard profile mode)
     - HERMES_HOME outside ~/.hermes, parent is "profiles/" → grandparent (Aether mode)
     - HERMES_HOME outside ~/.hermes, other → HERMES_HOME itself (Docker/custom)
  5. If profile_dir.is_dir() is False → FileNotFoundError → "Profile does not exist"
```

### 18. Daimon Identity — SOUL.md Not Loading (Wrong Profile)

**Status: FIXED (2026-04-25)** in `src/olympus/acp_client.py`.

**Symptom:** All Daimons respond as "Hermes" — they use Hermes's SOUL.md, config, and identity instead of their own.

**Root cause — three-layer failure:**

1. **Olympus spawns without `--profile` flag:** `acp_client.py` spawned `hermes acp` with only `HERMES_HOME` env var set. The hermes CLI's `_apply_profile_override()` (line ~99 in `hermes_cli/main.py`) runs at startup BEFORE any module imports and reads `<hermes_root>/active_profile` to resolve the profile. It overwrites `os.environ["HERMES_HOME"]` with the resolved profile path.

2. **`active_profile` is sticky:** The file `<hermes_root>/active_profile` contains `hermes` (written by `hermes profile use hermes`). When Olympus sets `HERMES_HOME=/path/to/profiles/ariadna` but doesn't pass `-p ariadna`, `_apply_profile_override()` ignores that env var and sets `HERMES_HOME=/path/to/profiles/hermes`.

3. **SOUL.md loads from HERMES_HOME:** `agent/prompt_builder.py` calls `load_soul_md()` → `get_hermes_home() / "SOUL.md"`. With wrong HERMES_HOME, every Daimon loads Hermes's SOUL.md.

**Evidence of the bug:**
```bash
# HERMES_HOME env var is IGNORED without -p flag:
HERMES_HOME=/path/to/profiles/ariadna hermes config path
# → .../profiles/hermes/config.yaml  ← WRONG!

# -p flag correctly overrides:
hermes -p ariadna config path
# → .../profiles/ariadna/config.yaml  ← CORRECT!
```

**The fix** in `src/olympus/acp_client.py` (around line 192-195):
```python
# Add --profile flag so hermes CLI doesn't fall back to active_profile
if "--profile" not in args and "-p" not in args:
    args = args + ["--profile", agent.name]
```

This appends `--profile <name>` to the spawn command (e.g., `hermes acp --profile ariadna`), forcing the CLI to resolve HERMES_HOME to the correct profile directory regardless of `active_profile` contents.

**Verification procedure:**
```bash
# Step 1: Verify each profile resolves correctly
for d in ariadna athena daedalus etalides hefesto; do
  echo -n "$d: "
  hermes -p "$d" config path
done
# Expected: each shows /path/to/profiles/<name>/config.yaml

# Step 2: Verify active_profile is NOT being used by Olympus
cat /path/to/Aether-Agents/home/active_profile
# Should show "hermes" — this is expected, but Olympus now bypasses it

# Step 3: Verify the --profile flag is in the spawn code
grep -n 'profile\|--profile' /path/to/Aether-Agents/src/olympus/acp_client.py
# Should show lines adding --profile to spawn args

# Step 4: Live test — spawn a Daimon and check identity
cd /path/to/Aether-Agents && \
AETHER_HOME=/path/to/Aether-Agents/home \
PYTHONPATH=/path/to/Aether-Agents/src \
~/.hermes/hermes-agent/venv/bin/python3 -c "
import asyncio
from olympus.config import get_config, reset_config
from olympus.discovery import discover_agents
from olympus.registry import OlympusRegistry
from olympus.acp_client import ACPManager

async def test():
    reset_config()
    config = get_config()
    agents = discover_agents(config)
    registry = OlympusRegistry()
    registry.register_discovery(agents)
    manager = ACPManager(registry)
    agent = await manager.ensure_agent('ariadna')
    session = await manager.open_session('ariadna')
    await manager.send_prompt(session.session_id, 'Say only your name.')
    await asyncio.sleep(10)
    print('ariadna:', ' | '.join(session.messages[:3]))
    await manager.close_session(session.session_id)
    await manager.shutdown_agent('ariadna')

asyncio.run(test())
"
# Expected: response contains "Ariadna" (not "Hermes")
```

**Important note on `active_profile`:** Do NOT delete `/path/to/Aether-Agents/home/active_profile`. It's needed by the Hermes orchestrator profile. The fix works because `--profile` overrides `active_profile`, not because `active_profile` is removed.

**GLM-5.1 (Hefesto) ACP streaming note:** GLM-5.1 may stream response text as `AgentThoughtChunk` (spinner faces like `(°ロ°)`) instead of `AgentMessageChunk`. The ACP protocol defines two channels: `AgentMessageChunk` (response text) and `AgentThoughtChunk` (progress/spinner). The PromptResponse only contains `stop_reason`, no text. If `session.messages` is empty after completion, the recovery path in `_run_acp_session` (nodes.py) filters spinner noise from `session.thoughts` and uses the remaining substantive content as fallback. The primary fix (`asyncio.sleep(0)` in acp_client.py) addresses the race condition for well-behaved providers.

## Common Failure Patterns

| Symptom | Likely Cause | Fix |
|---------|-------------|-----|
| `talk_to()` fails / "unknown agent" | Olympus MCP not in active config | Add to `$HERMES_HOME/config.yaml` (check env var first!) |
| Daimons speak kawaii | Missing `personality: none` | Add to all profile configs (team Daimons + Hermes, not required for Prometeo) |
| Daimon has no identity | SOUL.md not loaded / wrong profile | See Section 17 for diagnosis |
| All Daimons have same skills | `external_dirs` not configured or local skills/ bloated | Curate with `external_dirs` in config.yaml — see Section 4 |
| No project state between sessions | Missing `.eter/` directory | Create with proper structure |
| `mcp_olympus_talk_to` not available to LLM | MCP tools registered but not in LLM tool schema | Check agent.log for registration; requires hermes-agent fix to propagate MCP tools to all execution contexts |
| `delegate_task` fails "no API key" | `delegation.api_key: ''` in config.yaml or env not propagated | Set delegation.api_key explicitly, ensure .env loaded, or remove empty string |
| Custom skin not applying (falls back to default) | `HERMES_HOME/skins/` dir missing in profile | Symlink `~/.hermes/skins` into profile dir |
| Skin loads but colors clash (green on pink etc.) | Missing `status_bar_*` keys fall back to gold/kawaii | Define ALL 27 color keys in custom skin YAML |
| `.eter/` files inside `home/` dir | Stale install prior to fix | Run `mv home/.eter .eter` to migrate |
| `hermes -p <profile>` says "does not exist" | HERMES_HOME already set to different profile's root; `-p` resolves profiles under that root, not `~/.hermes` | See Section 17: use wrapper script (`~/.local/bin/<name>`) which sets HERMES_HOME explicitly |
| `talk_to()` returns empty response | ACP race condition: streaming callbacks not yet processed | Fixed in `fa39ac8` — `asyncio.sleep(0)` after `prompt()` + thoughts recovery path |

## Skin Engine Field Reference

When diagnosing or creating custom skins, the `skin_engine.py` validates against these fields. From the source:

**All required color keys (27):** banner_border, banner_title, banner_accent, banner_dim, banner_text, ui_accent, ui_label, ui_ok, ui_error, ui_warn, prompt, input_rule, response_border, session_label, session_border, status_bar_bg, status_bar_text, status_bar_strong, status_bar_dim, status_bar_good, status_bar_warn, status_bar_bad, status_bar_critical, voice_status_bg, completion_menu_bg, completion_menu_current_bg, completion_menu_meta_bg, completion_menu_meta_current_bg

Missing keys inherit from `default` skin (gold/kawaii) which **clashes** with dark themes. Always define ALL status_bar_* keys.

**Tool emojis must be unique** — same emoji for two tools makes them indistinguishable in the UI.

## Pitfalls

- **Always verify HERMES_HOME first**: Before diagnosing ANY config issue, run `echo $HERMES_HOME`. If set, that directory is the source of truth for config.yaml, SOUL.md, skills/, skins/, .env — everything. `~/.hermes/` is the CLI fallback used only when no profile is active. Editing `~/.hermes/config.yaml` when a profile is active has NO effect on runtime behavior and will produce false diagnostics.
- **`hermes -p <name>` resolves profiles under the current HERMES_HOME root**: If HERMES_HOME is already set (e.g., from a wrapper script or within another agent session), `-p prometeo` looks for the profile under THAT root's `profiles/` directory, NOT under `~/.hermes/profiles/`. This means `hermes -p prometeo` fails when run inside a Hermes session whose HERMES_HOME points elsewhere. Always use the wrapper script (`~/.local/bin/<name>`) for external profiles, which explicitly sets HERMES_HOME before calling hermes.
- **External profiles must stay isolated**: Do NOT symlink external profiles into each other's `profiles/` directories. Prometeo lives in `.prometeo/`, Aether lives in `Aether-Agents/home/`. Cross-contaminating profile roots causes `hermes -p` to find the wrong home.
- **`skills: []` is INVALID YAML**: Must use `skills: {}` for empty dict. The parser expects a dict, not a list.
- **Daimon .env files**: Each Daimon needs its own `.env` with API keys. The `.env.example` is a template — must be copied and filled.
- **Olympus starts lazily**: Daimons are spawned on first `talk_to(action="open")`. Discovery works without running Daimons, but actual communication requires `hermes acp` to be functional.
- **Skins don't cross HERMES_HOME boundaries**: Custom skins in `~/.hermes/skins/` are invisible to Aether profiles whose `HERMES_HOME` points elsewhere. Symlink each profile's `skins/` dir to `~/.hermes/skins/`, or copy `.yaml` files manually.
- **Prometeo is personal, not a Daimon**: It has no `agent:` field, no Olympus registration, speaks directly to Christopher (not through Hermes), and is gitignored. Don't include it in Daimon-level diagnostic checks.
- **YAML validation catches silent errors**: `skills: []` parses OK but breaks at runtime. Use `yaml.safe_load()` to verify configs. System Python may lack `yaml` — use hermes-agent venv Python.
- **Stale documentation after major commits**: Memory, session history, and even skill documentation can fall out of sync with the actual files on disk. After major phase completions, always: (1) search the actual files for expected content (e.g., `search_files(pattern="Workflow Orchestration")`), (2) update memory, (3) update affected skills. Never trust memory or documentation at face value when diagnosing project state — always verify against the filesystem first. **Case in point**: Phase 3 was completed in commit `f14c3d8` but both memory and `workflow-design` SKILL.md still showed it as PENDING — only file search revealed the truth. `olympus/config.py` computes `project_root = aether_home.parent`, and `acp_client.py` uses this as the Daimon working directory. If you find `.eter/` inside the `home/` directory, your installation predates the fix — migrate with `mv home/.eter .eter`.
- **project_root derivation**: The current code derives `project_root = aether_home.parent`, which is correct for the standard layout where Aether-Agents IS the project. When working on external projects (Artemisa, Zeus), you must ensure `PROJECT_ROOT` in the Daimon prompt points to the correct external project so Daimons write `.eter/` to the right place — not into the Aether-Agents repo. Pass `PROJECT_ROOT: /path/to/external/project` explicitly in every delegation prompt.
- **MCP tools don't propagate to sub-agents**: Fixed locally (2026-04-25) with 3 patches to hermes-agent. Upstream issue #14986 pending. Patches will be lost on update — reapply if upstream hasn't fixed it yet.
- **Daimons identify as Hermes (SOUL.md not loading)**: Fixed in `src/olympus/acp_client.py` (2026-04-25). Root cause: hermes CLI's `_apply_profile_override()` reads `active_profile` file and overwrites `HERMES_HOME`, ignoring the env var set by Olympus. Fix: added `--profile <agent_name>` to spawn command so the CLI resolves the correct profile. Without this, all Daimons load Hermes's config/SOUL.md.
- **Fire-and-forget is not the only pattern**: The orchestration skill enforces `open → message → wait → close` but MCP supports `open → message → poll → message → poll → message → close` (multi-turn within session). Don't assume Daimons can only receive one prompt per session — keep-alive means the session persists and context carries over between messages.
- **ACP Response Collection (FIXED, commit `fa39ac8`)**: Three-layer fix for empty response bug:
  - **Layer 1 (acp_client.py)**: `await asyncio.sleep(0)` after `prompt()` returns — yields to event loop so pending `AgentMessageChunk` callbacks process before collecting `session.messages`. This is the primary fix for the race condition where streaming updates arrive asynchronously.
  - **Layer 2 (registry.py)**: `mark_done()` logs a warning when `response=""` AND `messages=[]` — makes the issue visible in logs for diagnosis.
  - **Layer 3 (nodes.py)**: Recovery path in `_run_acp_session` — if `session.final_response` is empty but `session.thoughts` has content, filters kawaii spinner noise with `_is_spinner_noise()` regex and uses remaining substantive thoughts as fallback. This handles providers that stream via `AgentThoughtChunk` instead of `AgentMessageChunk`.
  - **Spinner noise filter**: Matches bracket patterns `(...)`, kawaii faces `(°ロ°)`, status strings `thinking...`, and very short fragments (<5 chars). Everything else is considered substantive content.
  - **Diagnostic**: `grep "completed with empty response" $HERMES_HOME/logs/agent.log` and `grep "substantive thoughts" $HERMES_HOME/logs/agent.log`
  - **GLM-5.1 note**: GLM-5.1 sends kawaii spinner text as `AgentThoughtChunk`. With `personality: none` this is minimal but may still appear. This is SEPARATE from the race condition.
- **hermes config path uses profile resolution, not HERMES_HOME**: Running `HERMES_HOME=/path/to/profile hermes config path` does NOT respect the env var if `active_profile` exists. The CLI's `_apply_profile_override()` (in `hermes_cli/main.py` line ~99) reads `<root>/active_profile` and overwrites HERMES_HOME at import time. To verify profile resolution, always use `hermes -p <name> config path` instead.
- **Profile `-p` flag fails when HERMES_HOME points to a different root**: `hermes -p prometeo` searches for the profile under `get_default_hermes_root()/profiles/`, which changes based on the current HERMES_HOME. If HERMES_HOME is set to `/home/user/Aether-Agents/home/profiles/hermes` (an external profile), `get_default_hermes_root()` returns `/home/user/Aether-Agents/home` (the parent), and profiles are searched in `/home/user/Aether-Agents/home/profiles/` — NOT `~/.hermes/profiles/`. A symlink at `~/.hermes/profiles/prometeo` becomes invisible. Fix: add symlinks in each external root's profiles/ directory, or always use the wrapper script that sets HERMES_HOME correctly before calling hermes. See Section 12 for full diagnosis.
- **Daimon config.yaml gitignored = Daimons disappear from Olympus (FIXED 2026-04-28)**: In commit `346c837`, `home/profiles/*/config.yaml` was added to `.gitignore` as "auto-generated runtime files". This removed the `agent:` discovery field from all 5 Daimon configs, causing `discover()` to only find Hermes. **Diagnosis**: run `talk_to(action="discover")` — if only `hermes` appears, check if `home/profiles/<daimon>/config.yaml` exists on disk AND is tracked by git. If the files are missing, restore them from the last commit that had them (`git show <commit>^:home/profiles/<daimon>/config.yaml`). **Fix**: Changed `.gitignore` from `home/profiles/*/config.yaml` (blanket ignore) to only `home/profiles/hermes/config.yaml` (hermes has API keys). All other Daimon configs are tracked because the `agent:` field is essential for Olympus discovery. **Lesson**: Daimon `config.yaml` is NOT a runtime file — it's the Daimon registration manifest that Olympus reads at startup.
- **Daimon config.yaml overwritten by hermes-agent**: Running `hermes --profile <daimon>` regenerates config.yaml with 329+ lines of defaults, destroying your clean 38-line config (nested model block, agent, web, skills, etc.). This happens because hermes-agent writes a full config with all defaults when it exits. **Always keep a backup of Daimon configs.** After running any profile directly, check and restore. The essential fields are: `agent:` block, `model.default/provider/base_url` (nested!), `web.backend`, `toolsets`, `link_budget`, `skills.external_dirs`, `display.personality: none`, `max_iterations`. **NEVER let the regenerated file persist** — it replaces meaningful config with noise. Detection: `wc -l <profile>/config.yaml` — if >50 lines, it was overwritten.
- **Daimon config flat YAML silently ignored (FIXED 2026-04-28)**: Using `model: X` / `provider: Y` as flat top-level keys causes hermes-agent to silently ignore provider and fall back to delegation provider → HTTP 402 or empty responses. **Fix**: Use nested format: `model.default: X` / `model.provider: Y` / `model.base_url: Z`. Flat format has no effect — hermes-agent only reads the nested `model:` dict.
- **Daimons not following workflow protocols (FIXED 2026-04-28)**: Agents skip their workflow skill because hermes-agent loads ALL 50+ skills from the directory, drowning the relevant one. The workflow skill content gets lost in the noise. **Fix**: Merged all 5 workflow skill contents directly into each Daimon's SOUL.md as §8/§9 Workflow Protocols. SOUL.md is always loaded (Slot 1 in system prompt) so protocols are guaranteed. External skill references removed from §5 (Skills).
- **LangGraph Interrupt serialization (FIXED, commit `e69da51`)**: LangGraph's `interrupt()` returns `Interrupt` objects (not plain dicts) inside the `__interrupt__` list. Each `Interrupt` has `.value` (the payload dict) and `.ns` (namespace). JSON serialization of the workflow result fails with `"Object of type Interrupt is not JSON serializable"`. Fix in `runner.py`: iterate over `__interrupt__` entries, extract `.value` attribute (the dict we passed to `interrupt()`), convert to serializable dict. Without this fix, HITL workflows crash at the first interrupt point.
- **MCP tool call timeout kills long-running workflows**: The `run_workflow` MCP tool is synchronous — Hermes calls it and waits for the result. But workflows with real agent calls take 2-5+ minutes per node. The MCP tool call timeout (typically 2-3 minutes) expires BEFORE the workflow completes, causing: (1) Hermes gets a timeout error, (2) the Olympus server continues running, (3) when the workflow reaches an interrupt, there's no MCP caller to receive the result, and the workflow hangs. **Architectural limitation** — HITL workflows require async execution with polling, increased MCP timeout, or Hermes-level orchestration.