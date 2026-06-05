---
name: aether-agents-orchestration
description: "Orchestrate Daimon specialists in Aether Agents — delegation, monitoring, Pure Orchestrator pattern, cost optimization, and common pitfalls."
version: 1.11.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [aether-agents, daimon, orchestration, delegation, monitoring]
    related_skills: [hermes-agent]
---

# Aether Agents Orchestration

Aether Agents uses 6 Daimon specialists (Hefesto, Etalides, Athena, Daedalus, Ariadna, Ictinus) managed by Hermes orchestrator. This skill covers delegation patterns, monitoring protocols, and common pitfalls.

## Delegation Patterns

### Blocking vs Background Delegation

**When to use blocking `delegate` (talk_to):**
- Quick tasks (< 2 minutes expected)
- Need immediate result to proceed
- User is waiting for answer

**When to use background delegation:**
- Long-running tasks (> 5 minutes)
- User wants to continue working on other things
- Multi-phase implementations

**When to SKIP investigation and act directly:**
- User explicitly says "just do it", "don't ask", "proceed"
- The path is obvious from context (e.g., restoring tools after a known experiment)
- User prefers execution over options: *"no me preguntes termina el plan original"*

**Background pattern:**
```python
# 1. Open session
session = talk_to(action="open", agent="hefesto", project_root="/path")

# 2. Send task (non-blocking)
talk_to(action="message", session_id=session["session_id"], prompt="...")

# 3. User says "let me know when done" — use cron job to monitor
cronjob(action="create", 
        schedule="every 30s",
        prompt=f"Poll session {session_id}, notify user when completed",
        repeat=10)

# 4. OR: Tell user you'll check back, then poll manually every 30-60s
```

**Anti-pattern: Blocking on long tasks**
```python
# WRONG — blocks for 600s, user can't do anything else
talk_to(action="delegate", agent="hefesto", timeout=600)
# If task takes >600s, you get timeout and lose the session
```

### Monitoring Active Sessions

**Polling discipline:**
- Poll every 15-30 seconds (not more frequently)
- Check `tool_calls` count and `last_turn` for progress
- If `status: "completed"` → retrieve result
- If `clarification_needed: true` → respond with `message`
- If stalled (same `tool_calls` count for 3+ polls) → report to user

**Silent monitoring (user preference):**
Do NOT narrate each poll to the user. Just monitor internally and report when:
- Task completes
- Error occurs
- Stalled progress (5+ polls with no change)
- Need user decision

**Wrong:**
```
Poll 1: Hefesto reading file (1 tool call)
Poll 2: Hefesto reading .env (2 tool calls)
Poll 3: Hefesto reading Makefile (3 tool calls)
...
```

**Right:**
```
[silently polling every 30s]
[after 5 minutes]
Hefesto completed phases 3-5. Here's what was done:
- Phase 3: .env created with unified API key
- Phase 4: docker-compose.yml created at root
- Phase 5: setup-honcho.sh + Makefile targets added
```

### Tool Selection for Monitoring

**Correct tool:** `talk_to(action="poll", session_id="...")`
- Returns session status, tool_calls count, last_turn
- Works for Daimon sessions (Hefesto, Etalides, etc.)

**Wrong tool:** `process(action="wait", session_id="...")`
- Only works for terminal processes with `background=true`
- Returns "not_found" error for Daimon sessions
- Daimon sessions are NOT terminal processes

## Common Pitfalls

### 1. Delegating Multi-Phase Tasks Without Checkpoints

**Problem:** Delegate 5-phase task with 600s timeout. Task takes 10 minutes. Timeout occurs, session lost, no way to resume.

**Solution:**
- Option A: Use background delegation + cron monitoring
- Option B: Break into smaller delegations (2-3 phases each)
- Option C: Increase timeout if task is critical (but user waits)

### 2. Polling Too Frequently

**Problem:** Poll every 5 seconds, spam user with "Poll 1... Poll 2... Poll 3..."

**Solution:**
- Poll every 15-30 seconds minimum
- Do NOT narrate polls to user
- Only report meaningful state changes

### 3. Using Wrong Monitoring Tool

**Problem:** Use `process.wait` on Daimon session → "not_found" error.

**Solution:** Use `talk_to(action="poll")` for Daimon sessions. Use `process(action="wait")` only for terminal background processes.

### 4. Not Handling Partial Progress

**Problem:** Daimon times out after completing 2 of 5 phases. User asks "what happened?" and you have no answer.

**Solution:**
- Before timeout: poll to capture `last_turn` and `recent_tool_calls`
- After timeout: check filesystem for artifacts (files created, commits made)
- Report: "Phases 1-2 completed (submodule added, PATCHES.md created). Phases 3-5 pending."

### 5. Docker Port Conflicts from Orphaned docker-proxy Processes

**Problem:** `docker compose up` fails with "Bind for 127.0.0.1:PORT failed: port is already allocated", but `ss`/`lsof` show no listeners. Multiple compose instances create orphaned docker-proxy processes that hold ports.

**Root cause:** Running docker compose up from different directories creates separate project networks, but docker-proxy processes from "downed" containers may linger.

**Fix:**
```bash
# 1. Kill orphaned docker-proxy processes
sudo fuser -k PORT/tcp

# 2. Clean up all Docker orphans
docker container prune -f
docker network prune -f

# 3. Retry
docker compose up -d
```

### 6. Data Loss: docker compose down --volumes DESTROYS Persistent Data

**Problem:** `docker compose down --volumes` deletes named volumes containing PostgreSQL and Redis data. All Honcho memory, profiles, and observations are permanently lost.

**NEVER use `--volumes` unless you explicitly intend to wipe all data.**

**Safe commands:**
```bash
docker compose down              # Stop + remove containers, keeps volumes
docker compose down --remove-orphans  # Also clean orphan containers, keeps volumes
```

**If you need a fresh start:**
```bash
# WARNING: This wipes ALL Honcho memory
docker compose down --volumes
```

### 7. docker compose up -d Requires background=true

**Problem:** Hermes terminal blocks `docker compose up -d` as "long-lived server process" even though `-d` detaches immediately.

**Fix:** Always use `background=true` with `notify_on_complete=true`:
```bash
terminal(background=true, command="docker compose up -d", notify_on_complete=true)
```

### 8. Trusting Delegation "Completed" Without Verification

**Problem:** Daimon reports `status: "completed"` but the actual work is incomplete or broken. Files may exist but have wrong content (missing services, incorrect ports/credentials). Containers may show "Created" but never actually start.

**Solution:** Always verify after delegation:
- Check files exist with correct content (not just file existence)
- Verify services are reachable (health endpoints)
- Check container status (not just "Created" — must be "Up" or "healthy")
- Compare output against acceptance criteria from the prompt

**Example (this session):** Hefesto claimed docker-compose.yml was done but it was missing the `deriver` service, had wrong DB credentials (postgres/postgres vs honcho/honcho), and containers showed "Created" but never "Running". Caught by verification.

#### Code Implementation Verification

Daimons sometimes report implementation as "complete" when the code has import errors, missing dependencies, or broken logic. File existence ≠ working code. Always run a smoke test.

**Verification checklist after code delegation:**
1. **Import resolution** — Can the target Python actually import all modules? Don't trust "installed" claims — run `python -c "import module"` yourself
2. **Correct toolchain** — If multiple Pythons exist (venv vs Homebrew, pip vs pip3.14), verify the Daimon used the right one. Daimons may install deps in a different Python's site-packages
3. **Execution test** — Run the entry point. A CLI that exits with `ModuleNotFoundError` on import is not "done", regardless of tests passing
4. **Config integrity** — Check API keys aren't truncated with literal "..." placeholders. Verify with `xxd` if redaction is suspected
5. **Acceptance criteria match** — Re-read your own prompt. Did you ask for "CLI running" but only got "all files created"? Close the gap

**Example (ZeusAgent session):** Hefesto reported all 18 tests passing, all files created. Actual audit found: (a) `prompt_toolkit` not installed in Python 3.14 (only in Hermes venv), (b) `compress()` inserted summary with `role: "system"` breaking OpenAI alternation, (c) API key truncated with literal "..." in config.yaml. None of these were caught by the test suite. All blocked the CLI from actually running.

### 9. The Pure Orchestrator Experiment — When Removing Tools Breaks the Product

**Context:** In v0.13.0, Hermes' toolset was stripped to 7 toolsets (removed `file-read`, `web`, `terminal`, `tts`) to reduce API costs. The theory: Hermes reasons only, all execution delegates to Daimons. The experiment was reverted within hours.

**What failed:**

1. **Unacceptable latency on trivial operations.** Checking `git tag -l` — a 200ms terminal command — required delegating to Etalides, which took 2+ seconds. The user explicitly called this unacceptable: *"tener que bajar a cualquier termino a leer un enlace es demasiado lento."*

2. **Lost programming capability.** The user: *"te limite tanto las herramientas que ya no podias hacer la esencia del proyecto, programar."* Hermes could no longer write code, edit configs, or fix problems directly — the core value proposition of the system.

3. **Diagnostic paralysis + hallucination.** Without `read_file`, Hermes could not diagnose configuration problems (e.g., web search returning "No provider configured"). Unable to verify the actual config, Hermes hallucinated a fictional "config caching" problem — which the user immediately caught and called out.

**Root cause:** The Pure Orchestrator pattern works structurally (Etalides CAN read files, Hefesto CAN execute) but the delegation overhead makes it unsuitable for interactive, latency-sensitive work. Every trivial operation becomes a full session lifecycle: open → message → poll → wait → retrieve.

**Correct optimization (what actually works):**

| Approach | Status | Why |
|----------|--------|-----|
| Remove tools from Hermes | ❌ Reverted | Breaks UX, adds latency, destroys programming capability |
| Model-tier separation | ✅ Active | Hermes = flagship, Hefesto = cheaper tier — biggest cost win |
| Aggressive decomposition | ✅ Active | More atomic tasks → cheaper models viable for Daimons |
| SOUL compression | ✅ Active | Shorter system prompts = fewer tokens per turn |

**Rule:** Hermes MUST retain `terminal`, `web_search`, and `read_file` for interactive work. The viable cost optimization is **model-tier separation + aggressive decomposition**, NOT removing tools from the orchestrator.

### 10. web_search Fails Despite Correct Config — THREE Root Causes

[... content unchanged, see references/web-search-backend-bug.md]

### 11. Olympus v3 ACP Returns "Internal error" or "ClosedResourceError"

**Problem:** `talk_to(action="delegate")` consistently returns "Error spawning agent: Internal error" or "ClosedResourceError" for ALL Daimons, even though gateway is running and `talk_to(action="open", agent="?")` returns the agent list.

**Root causes (in diagnostic order):**

1. **Multiple olympus processes** (most common) — competing for SQLite DB
2. **Session interrupted without cleanup** — leaves olympus orphans + corrupt WAL
3. **`raise err from None`** in `acp/connection.py:248` — suppresses real exception, you only see "Internal error"
4. **RequestError details lost** in `server.py:315,425` — `{e}` doesn't include `.data`/`.code`
5. **Daimon missing .env** — `acp_manager.py` loads `agent.profile_path / ".env"` but only orchestrator has one
6. **stdin PermissionError** — asyncio can't read stdin in subprocess, breaks ACP handshake
7. **ClosedResourceError** — MCP client pipe broken after gateway restart

**Quick fix (covers #1):**
```bash
kill $(ps aux | grep 'olympus_v3.server' | grep -v grep | awk '{print $2}')
systemctl --user restart hermes-gateway.service
ps aux | grep olympus | grep -v grep  # verify exactly 1
```

**If "ClosedResourceError" after restart:** Retry once. If it persists after 3 retries with clean single-olympus state, escalate for **chat session restart** — the MCP pipe is permanently broken.

**Full diagnostic flow with all 7 patterns, log paths, and code-level root causes:** `references/olympus-acp-debugging.md`

### 12. Reading Files Manually Instead of Querying Graphify First

**Problem:** Hermes reads source files with `read_file` to understand dependencies, imports, or call chains. This burns expensive model context (~15K tokens for 3-4 file reads) when a single Graphify query (~500 tokens) would return the same information.

**User directive:** Graphify is a PRIMARY codebase navigation tool for Hermes, not optional. The user explicitly said: "hacerlo una herramienta principal de hermes."

**Solution:** Query Graphify FIRST, then read files only for implementation details (specific line content, exact values).

| Task | Before (slow, expensive) | After (fast, cheap) |
|------|--------------------------|---------------------|
| Trace imports | `read_file` × 3 + `search_files` | `get_neighbors("node_id")` — 1 call |
| Understand a class | `read_file` + grep + manual tracing | `get_node` → `get_neighbors` — 2 calls |
| Find call chain | `grep` + `read_file` × 4 | `shortest_path` with method labels — 1 call |
| Explore subsystem | Manual file hopping | `get_community(community_id)` — 1 call |

**Noise reduction:** Use `context_filter` on `query_graph` to exclude skill/doc content when searching for code relationships:
- `["call","method","contains"]` — code structure tracing
- `["imports","imports_from"]` — dependency analysis
- Omit filter only for truly open-ended exploration

**Skip Graphify when:** code area is already well-known from this session, task is trivial (single-file edit), or user explicitly says they know the code.

**Reference:** `references/graphify-usage-patterns.md` for full query patterns, pitfalls, and extraction modes.

### 13. "Ghost Merge" — Code Is in Repo, Absent from Runtime

**Problem:** A feature (PR #42 Graphify) was merged to main with full code, dependency declaration, SOUL.md documentation, knowledge graph generation, and a CHANGELOG entry. The user later reports the feature is "no longer available" and asks for investigation. Investigation finds: code is present, tag exists, git log shows the merge commit, `pyproject.toml` declares the dependency. But the runtime tools (`mcp_graphify_*`) are NOT loaded by Hermes.

**Root cause:** The PR added everything EXCEPT the `mcp_servers.<feature>` block in `home/config.yaml`. The merge to main succeeded because config.yaml was either:
- Already in a clean state when the PR was opened, so the diff looked complete
- Modified locally post-merge for unrelated reasons, dropping the MCP server block
- The PR author tested with the MCP server block in a local config override, never committed it

The gateway loads MCP servers exclusively from `mcp_servers:` in `home/config.yaml`. No MCP server block = no tools loaded, regardless of how much code/SOUL.md/dependency exists in the repo.

**Diagnostic flow when "feature is gone but PR is merged":**

1. **Verify the merge** — `git log --oneline --all | grep <keyword>` to confirm the feature commit is on main
2. **Verify code artifacts** — check `pyproject.toml`, SOUL.md, generated artifacts (`graphify-out/graph.json`), provider configs
3. **Verify the package** — `home/.venv-hermes/bin/pip show <package>` and `python -m <module> --help`
4. **CHECK THE MCP SERVER BLOCK** — `cat home/config.yaml | grep -A 10 mcp_servers`. If the feature isn't there, that's the bug.
5. **Compare to working MCPs** — if `context7` and `olympus_v3` are present but `<feature>` is missing, you have a config drift, not a code bug
6. **Check for merged-but-not-rebuilt** — if a sub-quirk requires absolute paths (like `graphify.serve` needing the full `graph.json` path, not the default relative `graphify-out/graph.json`), the fix may need argv injection

**Fix procedure (5 steps):**
```yaml
# 1. Add the missing mcp_servers block in home/config.yaml
mcp_servers:
  <feature>:
    command: /home/prometeo/Aether-Agents/home/.venv-hermes/bin/python3.11
    args:
      - -m
      - <feature>.serve
      # Include absolute paths if the module resolves relative paths from site-packages
      - /home/prometeo/Aether-Agents/<generated>/<artifact>
    enabled: true
    env:
      <REQUIRED_ENV>: ${<REQUIRED_ENV>}
    timeout: 600
```

```bash
# 2. Verify the env var is loaded in the gateway environment
grep <KEY> home/.env

# 3. Restart the gateway
systemctl --user restart hermes-gateway.service
sleep 5 && systemctl --user status hermes-gateway.service

# 4. Verify the MCP server started (no errors in stderr log)
tail -30 home/logs/mcp-stderr.log | grep -i <feature>

# 5. Smoke test — load the artifact directly to confirm it's not corrupt
python -c "from <feature>.serve import _load_graph; g = _load_graph('<artifact>'); print(f'nodes={g.number_of_nodes()}, edges={g.number_of_edges()}')"
```

**Sub-quirk — relative paths from MCP server context:** MCP servers launched by the gateway have a CWD that may NOT be the project root. If `<module>.serve` resolves a default relative path (e.g., `graphify-out/graph.json`), it may resolve against `site-packages/` instead of the project. **Always pass absolute paths as `argv` arguments** when the module has a path argument.

**Anti-pattern: blaming the package or the venv**

When `pip show <package>` returns "not found" but the code is clearly in the repo, don't conclude the package is broken or the venv is corrupt. The `pip show` failure often comes from the venv being orphaned, but the MCP server can still run from the existing site-packages. Investigate the config first, the package second.

**Reference:** `references/ghost-merge-diagnosis.md` — full transcript of the Graphify v0.13.0 → v0.15.0 ghost merge, with exact diagnostic steps, the `graphify.serve` argv quirk, and the verification chain.

### 14. Gateway MCP Servers Lack `.env` Environment Variables

**Problem:** A restored MCP server (e.g., graphify) works correctly when invoked from a shell with the right env vars, but the gateway's MCP process does NOT receive them. Symptom: AST queries work, semantic/LLM-dependent calls fail silently or with 401/403. The MCP server block is in `config.yaml`, the `.env` file has the keys, but `/proc/<gateway-PID>/environ` is missing them.

**Root cause:** The `hermes-gateway.service` systemd unit loads `VIRTUAL_ENV` and `PATH` but does NOT load `home/.env`. The shell where you run smoke tests has the `.env` sourced or exported, so direct invocations succeed — but the gateway's child MCP processes inherit the gateway's clean environment.

**Diagnosis (when MCP server "works in shell, fails from gateway"):**
```bash
# 1. Confirm the .env has the key the MCP server needs
grep -E "^(OPENCODE_API_KEY|EXA_API_KEY|GRAPHIFY_)" home/.env

# 2. Confirm the gateway process does NOT have it
GW_PID=$(systemctl --user show -p MainPID hermes-gateway.service | cut -d= -f2)
cat /proc/$GW_PID/environ | tr '\0' '\n' | grep -E "OPENCODE|EXA|GRAPHIFY"
# Empty result → confirmed: gateway env missing these vars

# 3. Confirm MCP server works from shell with the same key (rules out other bugs)
OPENCODE_API_KEY="..." python -m graphify.serve /abs/path/graph.json
```

**Fix (two options — pick one):**

**Option A — `EnvironmentFile=` in the systemd unit (preferred for production):**
```ini
# ~/.config/systemd/user/hermes-gateway.service
[Service]
EnvironmentFile=/home/prometeo/Aether-Agents/home/.env
ExecStart=/home/prometeo/Aether-Agents/home/.venv-hermes/bin/python -m hermes_cli.main
```
```bash
systemctl --user daemon-reload
systemctl --user restart hermes-gateway.service
```

**Option B — `set -a; source` in the start script (preferred for dev simplicity):**
```bash
# scripts/start-gateway.sh — add BEFORE exec
set -a
. /home/prometeo/Aether-Agents/home/.env
set +a
exec /home/prometeo/Aether-Agents/home/.venv-hermes/bin/python -m hermes_cli.main
```

**Why this matters beyond graphify:** ANY MCP server that calls out to a third-party API (exa, context7, a custom LLM-backed tool) needs its env vars in the gateway's process. If you're using Option B, you don't need to edit the unit file when adding new MCP servers — the .env is the single source of truth. If you're using Option A, you need to restart the gateway every time `.env` changes.

**Reference:** `references/gateway-mcp-env-injection.md` — full diagnostic transcript for the graphify restoration (June 2026) including the shell-vs-gateway comparison, the systemd unit diff, and the verification chain.

### Pitfall #15 — Gateway MCP Servers Don't Inherit home/.env

**Síntoma:** Un MCP server local (graphify, ollama, lo que sea) funciona perfectamente desde la shell del usuario (`OPENCODE_API_KEY=$(grep ... home/.env) python -m foo.serve`), pero falla silenciosamente cuando lo invoca el gateway (`hermes-gateway.service`). El gateway corre, el MCP arranca, pero las llamadas que requieren LLM devuelven 401/403 o errores de autenticación.

**Causa raíz:** El unit file `~/.config/systemd/user/hermes-gateway.service` solo inyecta `Environment=PATH`, `Environment=VIRTUAL_ENV` y `Environment=HERMES_HOME`. **NO** carga `home/.env`, así que las API keys (OPENCODE_API_KEY, OPENCODE_GO_API_KEY, ANTHROPIC_API_KEY, etc.) nunca llegan al proceso del gateway ni a sus subprocesos MCP. Verificar con: `cat /proc/$(systemctl --user show -p MainPID hermes-gateway.service | cut -d= -f2)/environ | tr '\0' '\n' | grep OPENCODE` → si está vacío, este es tu bug.

**Fix estándar (drop-in override, NO editar el unit file):**

```bash
mkdir -p ~/.config/systemd/user/hermes-gateway.service.d
cat > ~/.config/systemd/user/hermes-gateway.service.d/override.conf <<'EOF'
[Service]
EnvironmentFile=/home/prometeo/Aether-Agents/home/.env
EOF
systemctl --user daemon-reload
systemctl --user restart hermes-gateway.service
```

El drop-in override sobrevive `git pull` y updates de repo porque NO modifica el unit file original en el repo. Convención systemd estándar para personalizaciones locales.

**Alternativa (si no quieres drop-in):** Agregar `set -a; source /home/prometeo/Aether-Agents/home/.env; set +a` antes del `exec` en `scripts/start-gateway.sh`. Pero el drop-in es más limpio.

**Anti-pattern:** NO hardcodear keys en el unit file (`Environment=OPENCODE_API_KEY=sk-agI7...`) — quedan en git log, no rotan fácil, son inseguras. SIEMPRE via EnvironmentFile apuntando a .env (que está gitignored).

## Toolset Recovery (Post-Experiment)
```yaml
web:
  backend: exa
  search_backend: exa
```
And `EXA_API_KEY` appears to be present in `.env`.

**CRITICAL: There are THREE distinct causes for this error. Diagnose in order.**

---

#### Cause A: `$HERMES_HOME` Not Set (MOST COMMON — pip install users)

**When this happens:** You installed hermes-agent via `pip install` and run it directly. The binary (`~/.venv-hermes/bin/hermes`) does NOT set `HERMES_HOME`. The framework's `load_hermes_dotenv()` falls back to `~/.hermes/.env`, which doesn't exist.

**Diagnosis:**
```bash
echo $HERMES_HOME         # Empty? → Cause A
ls -la ~/.hermes/.env     # Missing? → Confirmed
```

**Fix:** Set `HERMES_HOME` permanently, create a wrapper, or symlink the .env. See Pitfall 10 Cause A for the original diagnosis.

---

#### Cause B: `.env` File Actually Corrupted (RARE — verify with xxd first)

**When this happens:** Older versions of hermes-agent with `security.redact_secrets: true` physically wrote `***` into .env files.

**Diagnosis:**
```bash
grep "EXA_API_KEY" .env | xxd | grep "2a2a2a"
# Any matches → CORRUPTED (real asterisks on disk)
# No matches → File is fine, the `***` you see is output redaction
```

**Fix:** Restore keys from backup, disable `security.redact_secrets`, verify with xxd.

**Important:** ALWAYS verify with `xxd` before concluding corruption. `cat`/`grep` output is redacted by the framework even when the file is intact.

---

#### Cause C: Missing `plugin.yaml` in Bundled Web Plugins (hermes-agent v0.14.0 pip install)

**When this happens:** `EXA_API_KEY` IS in `os.environ`, `web.backend: exa` IS in config.yaml, but `web_search` STILL returns "No web search provider configured".

**Root cause:** Hermes Agent v0.14.0 was packaged for pip without `plugin.yaml` manifest files in `plugins/web/*/`. The plugin scanner skips directories without `plugin.yaml`, so `register()` is never called and `web_search_registry._providers` remains empty.

**Confirmed chain of failure:**
```
config.yaml: web.backend: exa        ✓
  → plugin scanner finds plugins/web/exa/  ✓
      → looks for plugin.yaml        ✗ NOT PACKAGED
          → _scan_directory_level() skips dir
              → register() NEVER called
                  → _providers = {}
                      → get_provider("exa") → None
                          → "No web search provider configured"
```

**Diagnosis:**
```bash
# Check if plugin.yaml exists
ls ~/.venv-hermes/lib/python3.11/site-packages/plugins/web/exa/plugin.yaml
# "No such file" → Cause C confirmed

# Check if providers are registered (via Python in venv)
python -c "
from agent.web_search_registry import list_providers
providers = list_providers()
print(f'Registered: {[p.name for p in providers]}')
print(f'Count: {len(providers)}')
"
# Output: "Registered: []", "Count: 0" → Confirmed
```

**Fix:**
```bash
# Create plugin.yaml for exa
cat > ~/.venv-hermes/lib/python3.11/site-packages/plugins/web/exa/plugin.yaml << 'EOF'
name: exa
version: "1.0"
description: Exa web search and content extraction
author: Nous Research
kind: backend
EOF
```
Then restart Hermes. The scanner discovers the plugin on startup and registers the provider.

**⚠️ Persistence:** The fix lives inside `.venv-hermes/` which is gitignored. If you recreate the venv or run `pip install --upgrade hermes-agent`, the fix is lost. Keep this documented.

**Full investigation:** See `references/plugin-yaml-missing-bug.md` for the complete diagnostic chain (5-pass investigation, xxd verification, registry inspection, scanner source analysis).

## Toolset Recovery (Post-Experiment)

When reverting from a failed toolset experiment (like v0.13.0 Pure Orchestrator), follow this procedure to restore Hermes' capabilities without reintroducing cost leaks.

### Recovery Checklist

1. **Read current config** — Check `~/Aether-Agents/home/config.yaml` toolsets lists
2. **Add read tools** — Ensure `file-read`, `terminal`, `web` are in:
   - `toolsets:` (main list)
   - `platform_toolsets.cli:`
   - `platform_toolsets.telegram:`
3. **Keep write tools blocked** — Ensure `file-write` is NOT in any list (it contains `write_file`, `patch`)
4. **Verify web backend** — Check `web.search_backend` is set to `exa` (or your provider)
5. **Test each tool** — Before declaring recovery complete:
   - `terminal`: run `echo test`
   - `read_file`: read a known file
   - `web_search`: run a test query (may fail due to hermes-agent bug — see Pitfall 10)
6. **Restart gateway** — If config was modified, restart `hermes-gateway.service` to reload

### When the Primary Daimon is Unavailable

If Hefesto is blocked (quota exhausted, provider down), use fallback options:

| Fallback | Method | When to use |
|----------|--------|-------------|
| Another coding agent | Claude Code, Codex, OpenCode | Hefesto quota exhausted |
| Manual edit | User edits config.yaml directly | Quick fix, user is technical |
| Etalides | For read-only investigation | Hefesto blocked, need diagnosis only |

**Prompt template for alternative agent:**
```
TAREA: Restaurar herramientas de LECTURA al perfil de Hermes en hermes-agent.

ARCHIVOS:
- ~/Aether-Agents/home/config.yaml (perfil principal)
- ~/.prometeo/profiles/prometeo/config.yaml (si existe, perfil Telegram)

CAMBIOS:
- En toolsets: AGREGAR file-read, terminal, web
- En platform_toolsets.cli: AGREGAR file-read, terminal, web
- En platform_toolsets.telegram: AGREGAR file-read, terminal, web
- Asegurar que NO esté: file-write
- En web.search_backend: exa (si falta)

NO reiniciar servicios. Solo modificar archivos y reportar.
```

## Hermes Pure Orchestrator (Architectural Cost Optimization)

> ⚠️ **EXPERIMENT STATUS: TESTED AND REVERTED (v0.13.0 → v0.12.0)**
>
> **Standalone implementation exists:** The Pure Orchestrator pattern was successfully reimplemented as Zeus Agent — a natively autonomous orchestrator built from scratch with NO tools, minimal system prompt (3 lines), and JSON session persistence. See `daimon-design` skill → `references/zeus-minimal-orchestrator.md` for the full case study. Zeus validates the pattern architecturally; it failed on Hermes because of UX expectations (latency, programming capability), not because the pattern itself is invalid.
> 
> The Pure Orchestrator pattern was implemented in v0.13.0 and reverted within hours. It works structurally but breaks interactive UX. See **Pitfall 9** below for the full post-mortem. The correct cost optimization is **model-tier separation + aggressive decomposition**, NOT removing tools from the orchestrator.

The highest-impact cost optimization is NOT downgrading Daimon models — it's removing tools from Hermes himself. Every tool in Hermes' system prompt costs tokens every turn. Each file Hermes reads directly burns expensive model context. The solution is architectural: strip Hermes to reasoning + delegation only.

### Principle

Hermes is a **reasoning-only orchestrator**. His sole interface to the world is delegation to Daimons via `talk_to`. He does NOT read files, search the web, execute terminal commands, or generate speech directly. His job: understand the user, decompose tasks, determine which Daimon does what.

### Hermes Target Toolset

| Kept (7) | Removed (4) | Consumer Daimon |
|----------|-------------|-----------------|
| `messaging` (talk_to, send_message) | `file-read` (read_file, search_files) → | Etalides |
| `vision` (vision_analyze) | `web` (web_search, web_extract) → | Etalides |
| `skills` (skill_view, skill_manage) | `terminal` → | Hefesto |
| `todo` | `tts` → | (none) |
| `memory` | | |
| `session_search` | | |
| `cronjob` | | |

### Consumer-Daimon Rule

**Every tool removed from Hermes MUST be verified as present in the consumer Daimon's config.** Before removing a toolset from Hermes' `config.yaml`, check that the receiving Daimon has the equivalent toolset enabled.

### Etalides as Eyes Pattern

To read any project file or search the web, Hermes delegates to Etalides:

```
talk_to(action="delegate", agent="etalides", project_root=PROJECT_ROOT,
  prompt="Read FILE and report: [specific question]")
```

For quick facts, use fast mode (≤5 action budget). For codebase investigation, use standard mode (10 actions). Etalides returns structured analysis with exact line numbers — Hermes synthesizes for the user.

### Implementation Checklist

1. Remove `file-read`, `web`, `terminal`, `tts` from Hermes `toolsets:` in config.yaml
2. Remove same from `platform_toolsets.cli` and `platform_toolsets.telegram`
3. Delete `terminal:` and `tts:` config sections
4. Update SOUL.md §6 Routing table (quick facts → Etalides), Economy rule, Code research rule
5. Verify Etalides config.yaml retains `web`, `file-read`, `terminal` toolsets
6. Verify Hefesto config.yaml retains `terminal` toolset

### Anti-pattern: Tactical Thinking for Cost Problems

When API costs spike, the instinct is to tweak Daimon configs (downgrade models, trim toolsets). The user explicitly redirected away from this: *"lo demas que dices no tiene sentido, nuestro ahorro tiene que ser a nivel arquitectura."* The correct first response to cost problems is: **what tools can Hermes lose?** — not what tools can Daimons trim.

### Anti-pattern: Over-Investigation Before Action

When the user asks for a concrete action (restore tools, fix config, run command), the instinct is to investigate first ("let me check how this works", "I need to research the hook mechanism"). The user explicitly rejected this: *"Mejor pide directamente a hefesto que te restablezca las herramientas"* — when the path is clear, act immediately. Investigation is for ambiguous problems, not for known procedures.

### Autonomy Levels — When to Interrupt the User

The user has explicitly defined when Hermes should act autonomously vs. when to ask for help. This is a hard rule, not a suggestion.

**Level 1 — FULL AUTONOMY (do NOT interrupt):**
- The user says "eres autonomo", "no me interrumpas", "adelante", "proceed", "BUSCALO"
- The task is investigation, diagnosis, or analysis — even if complex
- The path forward is clear from context — just execute
- The user explicitly says "no me preguntes termina el plan original"

**Level 2 — REPORT ONLY (interrupt only at completion or blockage):**
- Long-running tasks with clear acceptance criteria
- Multi-step investigations where intermediate results aren't useful
- The user says "dime cuando termine" or "let me know when done"
- For batch workflows: "adelante no me interrumpas hasta que acaben" — single uninterrupted delegation, no gate-checking between steps

**Level 3 — CONSULT USER (interrupt for decisions):**
- Architectural decisions with trade-offs (model selection, provider change)
- Irreversible actions (deleting data, changing production configs)
- 3+ consecutive failures on the same task — escalate with failure report
- External blockers (missing credentials, provider down, quota exhausted)

**Anti-pattern: Interrupting for trivial confirmations or options**

**Wrong (user will be annoyed):**
> "Should I search for the error in the logs or check the config first?"
> "Do you want me to delegate to Etalides or do it myself?"
> "I found the problem. Should I fix it?"
> "Here are 3 options: A, B, C. Which do you prefer?"

**Right (user's explicit preference):**
> [silently investigates, finds root cause, presents solution]
> "Found it: `$HERMES_HOME/.env` doesn't have EXA_API_KEY. The profile .env has it but the framework reads from `$HERMES_HOME/.env`. Two fixes: (A) copy key to `$HERMES_HOME/.env`, (B) set symlink. Implementing (A) now."

**The user's explicit words:** *"ERES AUTONOMO, no me interrumpas hasta que de verdad necesites mi ayuda. Caray"* — Act autonomously. Only interrupt when genuinely stuck or when a decision is required.

**Additional user preference on monitoring:** When delegating long tasks, do NOT narrate each poll. The user said: *"no me hables cada rato solo verifica el estatus final"* — wait for completion or report status only if stuck >2 minutes. Don't describe each intermediate step.

> **Reference:** `references/hermes-pure-orchestrator.md` — Full implementation plan with exact line numbers, config.yaml + SOUL.md changes, risk assessment, and **failure post-mortem documenting why the experiment was reverted**.

---

## Cost Optimization

The orchestration model is inherently cost-optimized: Hermes (expensive) does reasoning/decomposition once, Daimons (cheap) execute atomic tasks. But misconfigurations can leak cost.

**Priority order for cost work:**
1. **Architectural (Hermes toolset reduction)** — Remove tools from Hermes. See "Hermes Pure Orchestrator" section above. Highest impact per change.
2. **Model downgrade** — Daimons should not use Hermes' model tier
3. **Toolset trimming** — Each toolset adds ~200-500 tokens/system prompt per turn
4. **SOUL compression** — Trim Daimon SOUL.md to hard rules + tool protocols only

### Core Principle

**Hermes reasons, Daimons execute.** Daimons receive already-decomposed atomic tasks — they don't need flagship models. The Hermes model should be the ONLY expensive model in the system.

### Cost Audit Checklist

Run this audit periodically or when API bills spike:

1. **List all Daimon models** — Check `model.default` in each profile's `config.yaml`
2. **Identify the most-used Daimon** — Usually Hefesto (implementation is 80%+ of sessions)
3. **Flag duplicates of Hermes' model** — Any Daimon using the same model as the orchestrator is a cost leak
4. **Audit toolsets** — Each toolset adds ~200-500 tokens to system prompt per turn
5. **Prioritize by impact** — Hefesto downgrade >> other Daimons >> toolset trimming

### Optimization Layers (priority order)

**Layer 1 — Model Downgrade (HIGH impact):**
- Hefesto: should use a cheaper model than Hermes. If Hermes=deepseek-v4-pro, Hefesto should be deepseek-v4-flash or cheaper. Hefesto executes pre-decomposed tasks — doesn't need flagship reasoning.
- Etalides: already on flash — good.
- Consultants (Athena, Daedalus, Ictinus): analyze code and provide opinions, don't implement. Can use the cheapest capable models (kimi, glm, mimo).

**Layer 2 — Toolset Trimming (MEDIUM impact):**\n- Hefesto: needs `terminal`, `file`, `search_files`, `patch`. Does NOT need `execute_code` (use `terminal` for tests).\n- Consultants (Daedalus, Ictinus): need `file`, `search_files`, `terminal` for code reading. Do NOT need `execute_code` or `patch` — they don't write code.\n- Athena: needs `file`, `search_files`, `skills`. Trim if `terminal` is unused.\n- **After trimming:** Run the "Toolset Dependency Audit" procedure in the `daimon-design` skill to clean up SOUL.md references and `platform_toolsets` that still assume the removed toolset is available.

**Layer 3 — SOUL Compression (MEDIUM impact):**
- Daimons that only execute (Hefesto) don't need architectural context in their SOUL.md. Remove Role Catalog, workflow descriptions, capability lists owned by Hermes.
- Target: Daimon SOUL.md should be 50-150 lines of hard rules + tool protocols only.

**Layer 4 — Local Models (VERY HIGH impact, requires infra):**
- Fine-tuned local model (e.g., Qwen on RTX 4070+) can serve Hefesto at zero API cost.
- Requires: fine-tuning dataset, GPU with enough VRAM, latency testing.

**Layer 5 — Aggressive Decomposition (MEDIUM impact):**
- More atomic tasks → less Daimon reasoning needed → cheaper models become viable.
- Trade-off: more Hermes turns for decomposition.

### Anti-pattern: Hefesto uses same model as Hermes

The most common cost leak. Hefesto is the most-used Daimon and receives pre-decomposed tasks — giving it the same flagship model as the orchestrator doubles API costs for no benefit. Always use a cheaper tier for Hefesto.

### Reference

- `references/cost-optimization.md` — Detailed audit methodology with concrete examples from this project.

## Daimon Specializations

| Daimon | Role | Current Model | Recommended | Use For |
|--------|------|---------------|-------------|---------|
| Hefesto | Senior Developer | deepseek-v4-flash | deepseek-v4-flash ✓ | Code implementation, config changes, scripts |
| Etalides | Researcher | deepseek-v4-flash | deepseek-v4-flash ✓ | Web research, documentation, analysis, **Hermes' eyes for file/code reading** |
| Athena | Security Engineer | kimi-k2.6 | kimi-k2.6 ✓ | Security audits, threat modeling, code review |
| Daedalus | UX/UI Designer | mimo-v2-omni | mimo-v2-omni ✓ | UI/UX design, architecture diagrams |
| Ariadna | Context Curator | kimi-k2.5 | kimi-k2.5 ✓ | .aether database curation, context synthesis |
| Ictinus | Backend Architect | glm-5.1 | glm-5.1 ✓ | System design, scalability review, API design |

> **Cost optimization applied (May 2026):** Hefesto downgraded from deepseek-v4-pro to deepseek-v4-flash — single largest cost win. Etalides role expanded: now serves as Hermes' exclusive file-reading and web-research delegate (Hermes Pure Orchestrator pattern).

## Backup Recovery Workflow

When reverting from a failed experiment or release, follow this pattern to recover valuable work without dragging in junk.

### 6-Step Pattern

1. **Create backup branch** before reverting: `git branch backup/pre-<version>`
2. **Reset to clean state**: `git reset --hard <clean_tag_or_commit>`
3. **Diff backup vs clean**: `git diff clean..backup --stat` to see everything that changed
4. **Categorize each changed file**:
   - **Valuable** — skills, references, design docs, case studies
   - **Junk** — config backups (*.bak.*), cache files, runtime artifacts, duplicate images
   - **Dangerous** — modified config.yaml, SOUL.md changes from the experiment
5. **Cherry-pick only valuable files** to a feature branch from clean state
6. **Verify structure** before committing — directory layouts may have changed between versions

### Critical: Verify Directory Structure

The most common mistake in backup recovery is copying files to the wrong paths because the project structure changed between the backup version and the current version.

**Real example from this project:**
- Backup (v0.13.0 experiment): skills lived at `home/skills/`
- Current (v0.12.0): skills live at `skills/` (repo root)
- Wrong: `cp -r home/skills/ .` → creates duplicate `home/skills/` directory
- Right: Extract each file to its current correct path

**Before writing any recovered file:**
```bash
# Check where the file lives in current HEAD
git ls-tree HEAD --name-only | grep '<filename>'

# If the path differs from the backup, extract to the CURRENT path
git show backup/pre-v0.13.0:home/skills/devops/kanban/SKILL.md > skills/devops/kanban/SKILL.md
```

### What to Recover vs. What to Discard

| Recover | Discard |
|---------|---------|
| Skills (SKILL.md + references/) | Config backups (`*.bak.*`, `config.yaml.bak*`) |
| Design docs and case studies | Cache files (`*.json` caches, `model_catalog.json`) |
| Skin definitions | Runtime artifacts (`processes.json`, `.update_check`) |
| Research references | Duplicate clipboard images |
| Prototypes and mockups | Modified configs from the failed experiment |

### Post-Recovery Checklist

- [ ] All files are in the correct directory structure for the current version
- [ ] No duplicate or nested directory structures (`home/skills/` inside `skills/`)
- [ ] No junk files staged (run `git status --short` and review `??` entries)
- [ ] No dangerous config changes included (diff config.yaml, SOUL.md root)
- [ ] Commit is clean: only intended files, no runtime artifacts

## Framework Source Investigation

When a framework tool behaves unexpectedly, the default instinct is to guess at causes ("config caching", "race condition", "framework bug"). This produces hallucinations. The correct approach is to read the framework source code.

### When to Investigate Source Code

- Tool returns an error that contradicts visible configuration
- Documentation is ambiguous or contradicts observed behavior
- You find yourself saying "probably" or "likely" about framework internals
- User explicitly says "BUSCALO" or challenges your assumption

### How to Read Framework Source

**1. Find the installed package:**
```bash
# For hermes-agent
ls .venv-hermes/lib/python3.*/site-packages/hermes_cli/

# For any pip-installed package
python -c "import hermes_cli; print(hermes_cli.__file__)"
```

**2. Search for relevant functions:**
```bash
grep -r "load_dotenv\|\.env" hermes_cli/
grep -r "web_search\|search_backend" hermes_cli/
```

**3. Read the actual source code:**
```bash
cat hermes_cli/env_loader.py
```

**4. Trace call sites:**
```bash
grep -r "load_hermes_dotenv" hermes_cli/
```

**5. Check wrapper scripts and environment variables:**
```bash
cat ~/.local/bin/hermes
echo $HERMES_HOME
```

### What the Source Code Revealed (This Session)

**Initial assumption (hallucination):** "CLI mode doesn't load .env automatically — that's why EXA_API_KEY is missing."

**What the source actually shows:**
- `env_loader.py` DOES load `.env` automatically in ALL modes
- But it loads from `$HERMES_HOME/.env`, NOT from the profile directory
- The wrapper sets `HERMES_HOME` before running Python
- Without the wrapper, `HERMES_HOME` falls back to `~/.hermes`
- The profile's `.env` (`~/.prometeo/profiles/prometeo/.env`) is never read by the framework

**Correct conclusion:** The `.env` IS loaded in CLI mode — but from `$HERMES_HOME/.env`. The issue was not "CLI mode doesn't load .env" but "the key exists in the profile .env but the framework reads from `$HERMES_HOME/.env`".

### Anti-pattern: Guessing Framework Behavior

**Wrong:**
> "Probably the framework caches the config and needs a restart."
> "Likely there's a race condition in the provider initialization."
> "I think CLI mode doesn't load .env."

**Right:**
> "Let me read `env_loader.py` to see exactly how .env is loaded."
> "The source shows `load_hermes_dotenv()` is called in `main.py` line 212. Let me check what arguments are passed."
> "`env_loader.py` line 45 shows it loads from `$HERMES_HOME/.env`, not the profile directory."

### Diagnosing "Works in Isolation, Not in Production"

The most frustrating class of bug: a function works when called directly (Hefesto verifies `load_hermes_dotenv()` loads `EXA_API_KEY` into `os.environ`), but doesn't work in the running process. The gap is usually: the running process started before the fix, or has a different environment than expected.

**Key technique — Inspect process environment directly:**
```bash
# 1. Find the Hermes process PID
ps aux | grep "hermes " | grep -v grep

# 2. Read its environment (null-separated)
cat /proc/PID/environ | tr '\0' '\n' | grep KEY_NAME
# e.g., cat /proc/459942/environ | tr '\0' '\n' | grep EXA

# Compare with your shell's environment
env | grep KEY_NAME
```

**Diagnostic flow when a tool fails but config/env look correct:**
1. Verify file on disk is intact → `xxd file | grep "2a2a2a"` (check for actual `***` bytes, not redacted output)
2. Verify env var in process → `cat /proc/PID/environ | tr '\0' '\n' | grep KEY`
3. If env var IS present but tool still fails → the problem is NOT env loading. Check registries, plugin loading, initialization order.
4. If env var is NOT present → trace why `load_hermes_dotenv()` didn't fire (wrong `HERMES_HOME`, missing fallback .env)

**Real example (this session):**
- Step 1: `xxd` showed 0 occurrences of `2a2a2a` → .env NOT corrupted
- Step 2: `cat /proc/459942/environ` showed `EXA_API_KEY=4e1d19...f413` → key IS loaded
- Step 3: web_search still failed → problem is NOT env. Delegated to Hefesto to inspect `web_search_registry._providers` → found empty dict → traced to missing `plugin.yaml`
- Without Step 2, we would have spent hours debugging env loading for a problem that was already solved.

### Reference

- `references/hermes-agent-env-loading-source-analysis.md` — Complete source code analysis of `env_loader.py`, `main.py`, and wrapper scripts from this session.

```
~/Aether-Agents/
  home/                    # Hermes home directory
    .env                   # API keys (OPENCODE_GO_API_KEY, etc.)
    config.yaml            # Hermes config
    profiles/              # Daimon profiles (orchestrator, hefesto, etc.)
  honcho-server/           # Memory provider (git submodule)
  src/                     # Aether Agents source
  scripts/                 # Setup scripts (setup.sh, setup-honcho.sh)
  .gitmodules              # Submodule declarations
```

## References

- `references/graphify-usage-patterns.md` — **Graphify MCP query patterns, pitfalls, and extraction modes** — tested June 2026 on feature/graphify-integration branch. Covers: BFS/DFS Honcho bias, ambiguous shortest_path, focused extraction scope, provider config, context_filter noise reduction, shortest_path with method labels.
- `references/honcho-integration.md` — How to integrate Honcho as memory provider (submodule, unified .env, docker-compose)
- `references/hermes-pure-orchestrator.md` — Full Pure Orchestrator implementation plan, post-mortem, and failure analysis
- `references/cost-optimization.md` — Detailed cost audit methodology with concrete findings
- `references/delegation-patterns.md` — Blocking vs background delegation, monitoring protocols
- `references/api-key-management.md` — API key setup and rotation procedures
- `references/web-search-backend-bug.md` — hermes-agent web_search initialization bug: diagnosis and workarounds
- `references/hermes-agent-env-loading-source-analysis.md` — Source code analysis of `env_loader.py` and `main.py`: how .env loading actually works
- `references/dotenv-corruption-analysis.md` — **CRITICAL:** How `security.redact_secrets: true` physically corrupts `.env` files (xxd evidence, recovery steps)
- `references/plugin-yaml-missing-bug.md` — **CRITICAL:** hermes-agent v0.14.0 pip package missing `plugin.yaml` in bundled web plugins (registry stays empty, web_search fails silently)
- `references/olympus-acp-debugging.md` — Olympus v3 ACP spawn failures: "Internal error" / "ClosedResourceError" diagnosis (stale processes, SQLite contention, MCP reconnection)
- `references/gateway-mcp-env-injection.md` — **NEW (June 2026):** Gateway MCP servers lack `.env` env vars — diagnostic chain, both fix options (EnvironmentFile vs set -a; source), and the Graphify restoration transcript
- `references/fallback-providers.md` — Provider failover for Daimons: config format, per-profile setup, supported providers (from hermes-agent skill)"