# Balam-Agent — Setup, Delegation Pattern, and Project Isolation (2026-06-25)

> Balam-Agent is a Maya-jaguar-themed multi-agent coding assistant built on hermes-agent v0.17.0.
> It delegates ALL file I/O to subagents via native delegate_task. Built by DarkArty07 (MIT).
> Source: /home/prometeo/Balam-Agent/

## Architecture

```
User → Balam (delegation/web/skills/memory/vision/terminal)
         ├── Kinich subagent (read: web, file)  [context enforces read-only]
         └── Chaac subagent  (write: terminal, file)
```

- **Balam** has: `delegation`, `web`, `skills`, `memory`, `session_search`, `todo`, `vision`, `terminal`
- **Balam CANNOT**: read_file, write_file, patch, search_files, execute_code — ALL file operations go through subagents
- **Balam CAN**: run terminal commands directly (for quick checks, git, process management)
- **Tool enforcement**: structural (disabled_toolsets in config), not prompt-only

## Project Isolation — HERMES_HOME Separation (CRITICAL)

**Chris's correction:** "yo NO TE DIJE QUE METIERAS NADA DE BALAM A AETHER AGENTS. SON PROYECTOS APARTE."

Initially, Balam's profile was created at `/home/prometeo/Aether-Agents/home/profiles/balam/` because `hermes profile create` uses the active HERMES_HOME (which pointed to Aether-Agents). This was WRONG — Balam and Aether-Agents are completely separate projects.

**Fix applied:**
1. Deleted `/home/prometeo/Aether-Agents/home/profiles/balam/` entirely
2. Deleted wrapper at `~/.local/bin/balam` (pointed to wrong HERMES_HOME)
3. Created Balam's own HERMES_HOME at `/home/prometeo/Balam-Agent/home/`
4. Created a project-local wrapper script at `/home/prometeo/Balam-Agent/balam`

**Wrapper script pattern (reusable for ANY hermes-agent project):**
```bash
#!/usr/bin/env bash
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
export HERMES_HOME="$SCRIPT_DIR/home"
source "$SCRIPT_DIR/.venv/bin/activate"
exec hermes "$@"
```

**setup.sh creates this automatically:**
1. Creates `.venv` with Python 3.11 + `pip install hermes-agent==0.17.0`
2. Creates `home/` directory as HERMES_HOME
3. Copies config.yaml, .env, SOUL.md into `home/`
4. Creates the wrapper script

**DO NOT** use `hermes profile create` — it creates profiles in the active HERMES_HOME (which may belong to another project). Use the wrapper script pattern instead.

**DO NOT** use `hermes chat --profile X` — that relies on the global HERMES_HOME. The wrapper sets HERMES_HOME per-project.

## Config Pattern (config.yaml)

### custom_providers (REQUIRED for non-built-in providers)

If using a non-built-in provider (like `llmgateway`), it MUST be declared in `custom_providers`:

```yaml
custom_providers:
- name: llmgateway
  base_url: https://api.llmgateway.io/v1
  api_key: ${LLMGATEWAY_API_KEY}
  api_mode: chat_completions
  models:
    deepseek-v4-pro:
      context_length: 262000
    deepseek-v4-flash:
      context_length: 262000
```

**Symptom if missing:** "Unknown provider 'llmgateway'. Check 'hermes model' for available providers."

### disabled_toolsets (structural enforcement)

**CRITICAL — toolset names matter.** hermes-agent v0.17.0 has toolsets, not individual tool toggles. The toolset that contains `read_file`, `write_file`, `patch`, `search_files` is called **`file`** — NOT `file-read` or `file-write` (those names DO NOT EXIST and are SILENTLY IGNORED in `disabled_toolsets`).

This was a real bug in Balam v0.1.0: the config had `file-read` and `file-write` in `disabled_toolsets`, but Balam kept using read_file and write_file because those toolset names don't exist. The fix is to use `file` (the real toolset name).

**Correct config:**
```yaml
toolsets:
  - delegation
  - web
  - skills
  - memory
  - session_search
  - todo
  - vision
  - terminal

agent:
  disabled_toolsets:
    - file              # ← CORRECT: disables read_file, write_file, patch, search_files
    - code_execution
    - tts
    - cronjob
    - messaging
    - browser
    - computer_use
    - image_gen
    - video
    - video_gen
    - moa
    - x_search
    - spotify
    - homeassistant
    - kanban
```

**WRONG config (does nothing — names silently ignored):**
```yaml
  disabled_toolsets:
    - file-read         # ← DOES NOT EXIST as a toolset name
    - file-write        # ← DOES NOT EXIST as a toolset name
    - patch             # ← this is a TOOL name, not a TOOLSET name
    - search_files      # ← this is a TOOL name, not a TOOLSET name
```

**How to verify toolset names:** `grep -A3 '"file"' toolsets.py` inside the venv site-packages. Or run `/tools` inside hermes chat to see actual toolset→tool mapping.

**How to verify disabled_toolsets actually worked:** After starting hermes chat, run `/tools` and confirm the toolset does NOT appear. If it does, the name was wrong.

`terminal` is NOT in disabled_toolsets — Balam can run quick commands directly. File I/O is delegated.

### delegate_task `toolsets` parameter — SAME naming rule as disabled_toolsets (CRITICAL)

The `toolsets` array passed to `delegate_task()` accepts **TOOLSET names only**, NOT individual tool names. The same rule that applies to `disabled_toolsets` in config applies here. Invalid names are **silently filtered out** by the intersection logic in `_build_child_agent()`:

```python
child_toolsets = [t for t in toolsets if t in expanded_parent]
```

If you pass `["web", "file-read", "search_files"]`, only `"web"` survives (the other two are not valid toolset names). The subagent ends up with fewer tools than intended and cannot do its job.

**Valid toolset names** (from `toolsets.py` in the venv site-packages):
- `file` — bundles `read_file`, `write_file`, `patch`, `search_files` (ALL of them, no separation)
- `web` — bundles `web_search`, `web_extract`
- `terminal` — bundles `terminal`, `process`
- `vision`, `skills`, `memory`, `delegation`, `code_execution`, `browser`, `cronjob`, etc.

**How to verify valid names:** `grep -A3 '"file"' <venv>/lib/python*/site-packages/toolsets.py`

### Read-Only Subagent Limitation — `file` is All-or-Nothing

The `file` toolset bundles read AND write. There is NO `file-read`-only toolset. You cannot give a subagent read-only file access via toolsets alone.

**To create a read-only Explorer subagent**, pass `toolsets=["web", "file"]` and enforce read-only behavior via the `context` parameter:

```
delegate_task(
  goal="<investigation task>",
  context="You are a read-only explorer. Do NOT write, modify, or delete any files. Report findings only.",
  toolsets=["web", "file"]
)
```

The `context` string is injected LITERALLY into the subagent's ephemeral system prompt. This is the ONLY mechanism for read-only enforcement — the toolset cannot do it.

**Correct Kinich (Explorer):** `toolsets=["web", "file"]` + context enforcing read-only
**Correct Chaac (Builder):** `toolsets=["terminal", "file"]` — full access, no context restriction needed

### Documentation Drift — Keep DESIGN.md and README.md in Sync with config.yaml

When changing `model.default`, `model.provider`, or `model.base_url` in config.yaml, update ALL project docs:

- **DESIGN.md** — section 5 (Technology Stack) lists the main model and provider. If you change from glm-5.2 to deepseek-v4-pro, update DESIGN.md. Stale DESIGN.md misleads anyone reading the repo.
- **README.md** — the Tech Stack table and Installation section reference the provider and model. If provider changes from "OpenCode Go" to "llmgateway", update README.md. Also verify the run command matches the actual wrapper (`./balam chat` not `hermes start --profile balam`).
- **SOUL.md** — if it references toolsets in delegate_task examples, verify the names are valid TOOLSET names (see above).

**Verification checklist after any config change:**
1. `grep -r "glm-5.2\|opencode-go\|OpenCode Go" DESIGN.md README.md SOUL.md` — find stale references
2. Compare `model.default` in config.yaml vs what DESIGN.md/README.md say
3. Verify SOUL.md delegate_task examples use valid toolset names (`file` not `file-read`)

### Context window and compression (v0.1.1)

```yaml
model:
  context_length: 128000  # reduced from 262000 — 128K is enough, saves cost

compression:
  enabled: true
  threshold: 0.80      # compress at 80% of context_length (102.4K of 128K)
  target_ratio: 0.20   # keep 20% of threshold as uncompressed recent tail
  protect_last_n: 20
  hygiene_hard_message_limit: 300
  protect_first_n: 3
```

Per Context7 hermes-agent docs: `threshold` = fraction of context_length that triggers compression; `target_ratio` = fraction of threshold to keep as recent tail; `protect_last_n` = minimum messages always kept uncompressed.

### Delegation config

```yaml
delegation:
  provider: llmgateway
  model: deepseek-v4-flash
  base_url: https://api.llmgateway.io/v1
  api_key: ${LLMGATEWAY_API_KEY}
  api_mode: chat_completions
  max_iterations: 50
  max_concurrent_children: 3
  max_spawn_depth: 2
  subagent_auto_approve: true
  inherit_mcp_toolsets: true
  orchestrator_enabled: true
  child_timeout_seconds: 600
```

### Auxiliary services

Every `auxiliary.*` service needs its own `provider`, `model`, `base_url`, and `api_key`. If these point to a custom provider, `custom_providers` must be declared. Omitting auxiliary config causes silent failures.

## SOUL.md Pattern — Explicit Delegation (Token-Efficient, ~2900 chars)

The SOUL.md is the control plane for delegation. It teaches Balam WHEN and HOW to use delegate_task.

**v1 (1469 bytes):** Mentioned Explorer/Builder conceptually but no concrete call patterns. Balam delegated with generic goals, ommitting the `context` parameter.

**v2 (2901 bytes, 74 lines):** Added concrete delegate_task call templates with `context` carrying subagent identity:

```
### Kinich (Explorer) — Read-only investigation
delegate_task(
  goal="<specific investigation task>",
  context="You are Kinich, a read-only explorer. Investigate thoroughly. Report concisely. Do NOT modify files.",
  toolsets=["web", "file"]
)

### Chaac (Builder) — Write and execute
delegate_task(
  goal="<specific implementation task>",
  context="You are Chaac, a builder. Implement precisely. Follow the goal exactly. Report what you created/changed.",
  toolsets=["terminal", "file"]
)
```

The `context` parameter is injected LITERALLY into the subagent's ephemeral system prompt by `_build_child_system_prompt()`. This is the primary mechanism for creating subagent "types" WITHOUT modifying the framework.

**Six delegation rules in SOUL.md:**
1. ALWAYS pass `context` (gives subagent its identity)
2. ALWAYS pass explicit `toolsets` (never inherit)
3. Be SPECIFIC in goals (subagents have zero conversation context)
4. VERIFY results after delegation
5. Use Kinich first for investigation, then Chaac for implementation
6. Complex tasks: Kinich explores → Balam plans → Chaac builds → Balam verifies

## Subagent Fabrication Detection

Cheap/fast subagent models (deepseek-v4-flash) can FABRICATE execution results — reporting "tests passed" without running them, or inventing plausible but wrong output. During testing, a Chaac subagent fabricated test results. Balam detected this by:

1. Reading the file independently (via terminal `cat` or read_file quirk)
2. Comparing actual content with what the subagent claimed
3. Reporting honestly: "el subagente inventó resultados, pero el código es correcto"

**Pattern:** After a Builder reports "done," the parent verifies independently. Never trust "tests passed" at face value from cheap subagent models.

## delegate_task Internals (source: tools/delegate_tool.py, 2801 lines)

Key parameters the LLM can pass:
- `goal` (string) — what to do, self-contained
- `context` (string) — injected LITERALLY into ephemeral system prompt (identity vector)
- `toolsets` (array) — which tools the subagent receives (intersected with parent's available)
- `tasks` (array) — batch mode, up to max_concurrent_children in parallel
- `role` ("leaf" | "orchestrator") — leaf (default) cannot delegate further

Child agent construction (_build_child_agent):
- AIAgent() in SAME process (ThreadPoolExecutor)
- skip_context_files=True (no AGENTS.md, CLAUDE.md)
- skip_memory=True (no MEMORY.md, USER.md)
- quiet_mode=True (no output, only reports to parent)
- ephemeral_system_prompt built from goal+context (NOT from SOUL.md)

DELEGATE_BLOCKED_TOOLS (children NEVER get):
- delegate_task, clarify, memory, send_message, execute_code

Toolset resolution: child toolsets are intersected with parent's ENABLED toolsets (not disabled). This means a parent with `terminal` in disabled_toolsets can still give `terminal` to a child — because the child receives from the profile's available pool, not the parent's restricted set.

MCP inheritance: `inherit_mcp_toolsets=true` (default) preserves parent MCP servers (e.g. Graphify) in children.

## How to Run Balam

```bash
# Using the project wrapper (sets HERMES_HOME automatically)
cd /home/prometeo/Balam-Agent && ./balam chat

# In tmux
tmux new-session -d -s balam -x 200 -y 50 "cd /home/prometeo/Balam-Agent && ./balam chat 2>&1; bash"
tmux attach -t balam
```

## Cross-References

- `references/hermes-delegate-task-internals.md` — full delegate_task source analysis
- `references/opencode-subagent-architecture.md` — OpenCode's task tool analysis
- `references/eigent-subagent-architecture.md` — Eigent/CAMEL subagent analysis
- `references/delegation-patterns.md` — general delegation patterns
