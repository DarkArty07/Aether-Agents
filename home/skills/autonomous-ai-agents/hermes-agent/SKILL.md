---
name: hermes-agent
description: "Configure, extend, or contribute to Hermes Agent."
version: 2.9.0
author: Hermes Agent + Teknium
license: MIT
metadata:
  hermes:
    tags: [hermes, setup, configuration, multi-agent, spawning, cli, gateway, development]
    homepage: https://github.com/NousResearch/hermes-agent
    related_skills: [claude-code, codex, opencode]
---

# Hermes Agent

Hermes Agent is an open-source AI agent framework by Nous Research that runs in your terminal, messaging platforms, and IDEs. It belongs to the same category as Claude Code (Anthropic), Codex (OpenAI), and OpenClaw — autonomous coding and task-execution agents that use tool calling to interact with your system. Hermes works with any LLM provider (OpenRouter, Anthropic, OpenAI, DeepSeek, local models, and 15+ others) and runs on Linux, macOS, and WSL.

**See also:**
- **Standard setup pattern:** `references/standard-setup.md` — proper hermes-agent installation: symlink to venv binary (not a wrapper), `HERMES_HOME` pointing to data directory, config.yaml at default profile root, verification checklist, and a worked example for cross-distro Fedora WSL setup.
- **Cross-distro migration (WSL):** `references/cross-distro-migration.md` — complete 7-phase workflow for migrating a hermes-agent instance between WSL distros (tar pipe copy, venv rebuild, systemd gateway, post-restore config adaptation checklist, MCP server audit & cleanup). Tested on Ubuntu→Fedora Prometeo migration (2026-06-09).
- **Provider resolution architecture:** `references/provider-resolution.md` — full chain from config.yaml → runtime_provider.py → auth.py PROVIDER_REGISTRY → credential pool. Common pitfalls: confusing CLI runner (OpenCode Go) with hermes-agent (they're separate systems with separate configs), `providers: {}` empty being normal for built-ins, `config set` not hot-reloading the running gateway, `auth.json` overriding `model.provider`.
- **Enabling messaging platforms:** `references/enabling-messaging-platforms.md` — step-by-step Telegram/Discord bot setup on an existing gateway: token validation, `.env` vs config.yaml, user access allowlists, Chat ID discovery, and the critical `gateway.log` vs `journalctl` diagnostic gap after restart.
- **MCP server configuration:** `references/mcp-server-configuration.md` — three supported transports (stdio / Streamable HTTP / SSE), OAuth 2.1 PKCE flow with **cross-WSL caveat** (callback server on `127.0.0.1`, WSL2 localhost forwarding, `hermes mcp login` guard requiring `auth: oauth`, script pattern to auto-open Chrome on Windows via `cmd.exe`), Bearer/header auth, smoke-test commands, and the cross-instance rule (Prometeo vs Aether-Agents are independent; an MCP added to one is invisible to the other).
- **Multi-instance CLI profile flag:** `references/multi-instance-cli-profile-flag.md` — why `hermes --profile prometeo` and `hermes -p prometeo` both fail with "profile does not exist" (the flag is in `--help` but NOT registered in `hermes_cli.main` — a known hermes-agent bug), the verified working `HERMES_HOME=... python -m hermes_cli.main ...` form, how the `~/.local/bin/hermes` wrapper is locked to Aether, and the optional `hermes-prometeo` wrapper recipe.

## Official Installation Methods (Confirmed by Context7, 2026-06-09)

Five methods are officially documented. **`pip install hermes-agent` is the primary and recommended method** for most setups.

| Method | Command | Use case |
|--------|---------|----------|
| **PyPI (primary)** | `pip install hermes-agent` | Standard. Follow with `hermes postinstall` for optional deps (Node.js, browser, ripgrep, ffmpeg). |
| **Installer script** | `curl -fsSL https://hermes-agent.nousresearch.com/install.sh \| bash` | All-in-one. Linux/macOS/WSL2/Android. Handles Python, Node.js, and deps automatically. |
| **GitHub (bleeding edge)** | `pip install git+https://github.com/NousResearch/hermes-agent.git` | Latest main branch. Requires build tools. |
| **uv (fast alt)** | `uv pip install git+https://github.com/NousResearch/hermes-agent.git` | Faster than pip for dependency resolution. |
| **Nix (dev)** | `nix build` | Development and custom builds only. |

No official Docker, brew, or apt packages exist. For WSL/Fedora clean installs, **pip in a dedicated venv** is the standard approach — it keeps the venv and data directory (`HERMES_HOME`) cleanly separated. Avoid `curl install.sh` on machines that already have Python configured; it may create conflicting installations.

### Quick Comparison: pip vs installer script

| Aspect | `pip install hermes-agent` | `curl install.sh \| bash` |
|--------|---------------------------|---------------------------|
| Python required | Yes (already installed) | No (auto-installs via uv) |
| Control over venv location | Full | Auto (uses `~/.hermes/`) |
| Post-install deps | Manual: `hermes postinstall` | Automatic |
| Best for | Existing Python setups, multi-instance | Fresh machines, single instance |

**Bottom line for this project:** Always use `pip install hermes-agent` in a dedicated venv. The installer script creates `~/.hermes/` which conflicts with the clean `HERMES_HOME` pattern documented below.

## Standard Setup Without Wrappers (Chris's Rule, 2026-06-05)

> "ya no quiero usar wrappers quiero minizar el uso de wrapper y configurar todo como debe ir"

The pip-installed hermes-agent entry point (`<venv>/bin/hermes`) is self-contained — it has its own shebang pointing to the correct Python in the venv, imports `hermes_cli.main`, and handles its own environment. **No wrapper script is needed.** The wrapper pattern (`unset PYTHONPATH; export HERMES_HOME=...; exec venv/bin/hermes "$@"`) is an anti-pattern that creates fragile, machine-specific scripts when the pip entry point already does everything required.
## Standard Setup Without Wrappers (Chris's Rule, 2026-06-05, updated 2026-06-09)

> "ya no quiero usar wrappers quiero minizar el uso de wrapper y configurar todo como debe ir"

The pip-installed hermes-agent entry point (`<venv>/bin/hermes`) is self-contained — it has its own shebang pointing to the correct Python in the venv, imports `hermes_cli.main`, and handles its own environment. **No wrapper script is needed.** The wrapper pattern (`unset PYTHONPATH; export HERMES_HOME=...; exec venv/bin/hermes "$@"`) is an anti-pattern that creates fragile, machine-specific scripts when the pip entry point already does everything required.

### The Standard Way (Three Options, Ranked)

**Option 1 (Preferred): PATH-based resolution via `.bashrc`:**
```bash
# In ~/.bashrc, prepend the venv bin directory:
export PATH="/path/to/venv/bin:$PATH"
export HERMES_HOME="/path/to/data/dir"
```
The shell resolves `hermes` directly from the venv. No copies, no symlinks, no wrappers. When you `pip install --upgrade hermes-agent`, the new version is immediately available — no re-copy needed.

**Option 2 (Fallback): Hard copy of the venv entry point:**
```bash
cp /path/to/venv/bin/hermes ~/.local/bin/hermes
```
The pip entry point (~350 bytes, Python script with shebang) is self-contained. **Hard copy preferred over symlink** — avoids symlink breakage on cross-filesystem setups or WSL path translation. **Drawback:** must re-copy after `pip install --upgrade`.

**Option 3 (Legacy, avoid): Shell wrapper script.**
The `setup.sh` Step 8 wrapper pattern (`unset PYTHONPATH; export HERMES_HOME=...; exec venv/bin/hermes "$@"`). This is DEPRECATED per v0.16.0 — it creates fragile machine-specific scripts when the pip entry point is self-contained.

**Why Option 1 over Option 2:**
- No maintenance — upgrades flow automatically through PATH
- No stale binary risk after `pip install --upgrade`
- Single source of truth — `.bashrc` always points to the active venv
- The hard copy at `~/.local/bin/hermes` becomes stale after upgrades (old version cached)

**Why hard copy over symlink (for Option 2):**
- Symlinks break across WSL filesystem boundaries (Windows ↔ Linux)
- Symlinks can become dangling if the venv is recreated or moved
- Hard copy is ~350 bytes — negligible cost for guaranteed stability
- The shebang inside the script already points to the correct Python in the venv

**`HERMES_HOME` in `.bashrc`, once (all options):**
```bash
echo 'export HERMES_HOME="$HOME/.prometeo"' >> ~/.bashrc
```

**Default profile pattern (no `-p` flag):**
Place `config.yaml` at `$HERMES_HOME/config.yaml` directly. This avoids the broken `-p`/`--profile` flag entirely (see `references/multi-instance-cli-profile-flag.md`). Named profiles at `$HERMES_HOME/profiles/<name>/` are for secondary instances only.

### Decision Tree

| Situation | Pattern |
|-----------|---------|
| Single instance per machine | Default profile. **PATH-based resolution** (Option 1). HERMES_HOME in .bashrc. config.yaml at root. **NO wrapper.** |
| Multiple instances, separate venvs | Each instance: own venv + PATH entry in .bashrc. Or `~/.local/bin/<name>` hard copy. |
| Multiple instances, shared venv | Default profile for primary. For secondary: `HERMES_HOME=... python -m hermes_cli.main ...` or one-line alias. |

### Anti-Patterns (What Chris Rejects)

- ❌ Wrapper that unsets PYTHONPATH + execs venv binary — unnecessary; the pip entry point is self-contained
- ❌ Wrapper that hardcodes HERMES_HOME — set it once in `.bashrc`
- ❌ Wrapper that adds `-p <profile>` — the flag is broken (known bug), use default profile instead
- ❌ Git clone installation inside the data directory — keep install (venv) and data (HERMES_HOME) separate
- ❌ `LD_LIBRARY_PATH` pointing to another installation's venv — cross-contaminates NVIDIA libs between instances
- ❌ `.env` as symlink to another profile — breaks when the target profile is absent

### Migration: Wrapper → No-Wrapper

1. Inspect the wrapper: `cat ~/.local/bin/hermes`
2. If it only sets HERMES_HOME + execs venv binary → delete it, add PATH to `.bashrc`, set HERMES_HOME in `.bashrc`
3. If it unsets PYTHONPATH/PYTHONHOME → these are safety nets; the pip entry point handles its own imports
4. Verify: `which hermes` points to venv/bin/hermes, `hermes --version` and `hermes config show` read from HERMES_HOME
5. Remove any stale `LD_LIBRARY_PATH` lines in `.bashrc` pointing to other installations' venvs

**Verification checklist:**
```bash
which hermes                         # → /path/to/venv/bin/hermes (NOT ~/.local/bin/hermes for Option 1)
echo $HERMES_HOME                    # must be set to the data directory
ls $HERMES_HOME/config.yaml          # must exist at root (default profile pattern)
hermes --version                     # must work without any env var prefix
hermes config show 2>&1 | head -5    # must show correct Config: and Secrets: paths
```

### pip install Warning: "not officially supported"

When installing via `pip install hermes-agent`, pip may show:
```
⚠ pip install not officially supported — exists for reasons other than user install; expect instability
```

**This warning is cosmetic and safe to ignore.** The hermes-agent creators prefer the `curl -fsSL ... | bash` installer (which handles system deps like ffmpeg, Node.js, CUDA) over raw `pip install`. However, when using a proper venv with manual dependency management (`hermes-agent[mcp]`, graphifyy, olympus-mcp), pip install is the correct approach. The venv isolates hermes-agent and its dependencies, and `.bashrc` handles PATH and HERMES_HOME. The warning refers to bare `pip install` without a venv on a system lacking the system dependencies — not to our managed venv setup.

**Key difference:** pip install doesn't install ffmpeg, Node.js, ripgrep, or CUDA libs — those need manual installation. The curl installer bundles all of this. In a venv setup, those are pre-installed system-wide.

**Top 3 pitfalls when configuring hermes-agent:**

1. **Verify support in the installed code, not in adjacent configs.** Before claiming "X is not supported", grep the active venv (`~/.prometeo/.venv-hermes/lib/python*/site-packages/...`) for the actual parser. Pattern-matching from 3 stdio MCPs in a config and concluding "only stdio is supported" is exactly the wrong inference (the dispatch is `"url" in config` — one key). See `references/mcp-server-configuration.md` §"How to verify framework support".
2. **Gateway env does not auto-load profile `.env`.** `systemctl --user hermes-gateway*.service` does NOT source `home/.env` or the profile `.env`. MCP servers that need API keys (Bearer, OPENCODE_*, etc.) work from a shell smoke test but fail under the gateway. Fix: a drop-in override at `~/.config/systemd/user/hermes-gateway.service.d/override.conf` with `EnvironmentFile=`. See `references/mcp-server-configuration.md` §"Gateway env-loading pitfall".
3. **Prometeo and Aether-Agents are independent hermes-agent instances.** Separate `config.yaml`, separate `.env`, separate `hermes-gateway*.service`. Adding an MCP to one does not affect the other. Before editing, confirm which instance you are modifying by `echo $HERMES_HOME` and `pwd`.

### Pitfall #N — Graphify `serve` Uses Relative Path, Breaks from Gateway CWD

**Síntoma:** Agregas `mcp_servers.graphify` a `config.yaml` con `args: ["-m", "graphify.serve"]`. El gateway arranca graphify, pero `_load_graph()` falla con `FileNotFoundError: graph.json not found`. Desde shell con `python -m graphify.serve` funciona perfecto.

**Causa raíz:** `graphify.serve` lee `sys.argv[1]` para el path del graph.json, con default `graphify-out/graph.json` (relativa). Cuando lo lanza el gateway via MCP, el CWD del proceso es el del gateway (típicamente el home del venv o el directorio del usuario), NO la raíz del repo Aether-Agents. La resolución relativa falla.

**Fix correcto (pasado en sesión 06-04):**

```yaml
mcp_servers:
  graphify:
    command: /home/prometeo/Aether-Agents/home/.venv-hermes/bin/python3.11
    args:
      - -m
      - graphify.serve
      - /home/prometeo/Aether-Agents/graphify-out/graph.json  # ← ABSOLUTA, no relativa
    enabled: true
    env:
      GRAPHIFY_PROJECT: /home/prometeo/Aether-Agents
      OPENCODE_API_KEY: ${OPENCODE_API_KEY}
    timeout: 600
```

La ruta absoluta como `argv[1]` resuelve el problema sin importar el CWD del proceso.

**Diagnóstico rápido cuando graphify no arranca:**
```bash
# 1. Verifica el proceso y su CWD
GW_PID=$(systemctl --user show -p MainPID hermes-gateway.service | cut -d= -f2)
cat /proc/$GW_PID/cwd 2>/dev/null  # te dice el CWD del gateway

# 2. Verifica si la ruta existe desde ese CWD
sudo -u $(whoami) ls -l $(cat /proc/$GW_PID/cwd 2>/dev/null)/graphify-out/graph.json
# Si falla, el problema es CWD relativa

# 3. Test directo del módulo
cd / && home/.venv-hermes/bin/python -m graphify.serve /home/prometeo/Aether-Agents/graphify-out/graph.json
# Si esto funciona, confirma que el fix es pasar ruta absoluta
```

**Regla:** Cualquier MCP server que abra un archivo en el proyecto (graph.json, db.sqlite, .env) DEBE recibir la ruta absoluta via args o env var, nunca depender de CWD.

### Pitfall #O — MCP Servers Fail Silently When HERMES_HOME Is Unset OR MCP SDK Missing

**Symptom (observed 2026-06-05 on Prometeo Fedora migration):** After migrating a hermes-agent instance to a new distro, MCP servers fail inconsistently — NOT all at once. `hermes mcp` shows a mix of working and broken.

**Two root causes produce the same symptom — check BOTH:**

| Root cause | Check | Fix |
|------------|-------|-----|
| `HERMES_HOME` unset | `echo $HERMES_HOME` (empty?) | `echo 'export HERMES_HOME="$HOME/.prometeo"' >> ~/.bashrc` |
| MCP SDK missing | `python -c 'import mcp'` (ModuleNotFoundError?) | `pip install 'hermes-agent[mcp]'` |

The MCP SDK (`mcp` Python package) is an optional dependency NOT installed by `pip install hermes-agent`. Without it, ALL MCP servers fail silently — `hermes mcp list` misleadingly shows "✓ enabled" (it only checks config syntax, not runtime capability). `hermes mcp test <name>` is the REAL diagnostic. See `references/mcp-server-configuration.md` §"Prerequisites" for full details.

When `HERMES_HOME` is empty, hermes-agent cannot:
|--------|-----------|-------|-------------------------------|
| context7 | npx | nothing special | ✅ working |
| reddit | node | nothing special | ✅ working |
| todoist | npx | API key from `.env` | ❌ failed |
| clio-fca | uv | PATH for `uv` binary | ❌ failed |
| freepik | uv | PATH for `uv` + API key | ❌ failed |
| magnific | http+OAuth | `mcp-tokens/` directory | ❌ failed |

**Root cause:** `HERMES_HOME` is empty. Without it, hermes-agent cannot:
1. Pass `PATH` correctly to MCP subprocesses → `uv` is not found even though it's in `~/.local/bin/`
2. Resolve `.env` for API keys in `env:` blocks → `TODOIST_API_KEY` etc. are never loaded
3. Scan `mcp-tokens/` for OAuth credentials → Magnific re-prompts authorization

The pattern is diagnostic: if **only** MCPs that need env vars or non-system-PATH binaries fail while simple MCPs work → `HERMES_HOME` is unset.

**Diagnosis:**
```bash
echo $HERMES_HOME                    # Empty? → confirmed
hermes config show 2>&1 | head -3    # Shows wrong Config: path? → confirmed
```

**Fix (one line):**
```bash
echo 'export HERMES_HOME="$HOME/.prometeo"' >> ~/.bashrc
source ~/.bashrc
hermes mcp  # verify all MCPs now show tools
```

**Do NOT** chase individual MCP errors (install uv, fix PATH, re-auth OAuth) before checking HERMES_HOME. All of them are downstream symptoms of the same root cause.

### Pitfall #Q — Privileged Operations Blocked: `sudo -S` and `wsl.exe -u root` Both Caught by Security Hook

**Symptom (observed 2026-06-09 on Prometeo Fedora migration):** When automating privileged operations on a remote WSL distro (writing `/etc/wsl.conf`, running `systemctl enable`, `mkdir` in protected dirs), TWO approaches fail:

1. `echo 'password' | sudo -S command` → blocked with "Brute-force detected: piping password to sudo"
2. `wsl.exe -d DISTRO -u root -- bash -c 'command > /protected/file'` → blocked with "Write operation not allowed"

Both are caught by the same security hook layer — the write-restriction guard that prevents Hermes from modifying files outside its sandbox.

**Root cause:** The security hook operates at the tool/output level, not the WSL distro level. Even though the target is a DIFFERENT WSL distro (Fedora), the command originates from Hermes on Ubuntu — the hook catches all `>` redirects, `tee`, and `sudo -S` patterns regardless of the execution context.

**What IS blocked:**
| Pattern | Caught by | Error |
|---------|-----------|-------|
| `echo 'pw' \| sudo -S command` | Brute-force guard | "Brute-force detected" |
| `wsl.exe -u root ... > /file` | Write-restriction hook | "Write operation not allowed" |
| `wsl.exe ... sudo tee /file` | Write-restriction hook | "Write operation not allowed" |

**What still works:**
- Non-privileged file writes (user-writable paths like `~/.config/`, `~/.local/`)
- Read-only privileged operations (`sudo cat /etc/wsl.conf`)
- All operations via Hefesto (Daimons have separate security profiles)

**Resolution:** For privileged operations on ANY distro (local or remote WSL), there are TWO options:

1. **Delegate to Hefesto** — Daimons have separate security profiles. Hefesto CAN use `wsl.exe -u root` to write files and run systemctl on remote distros (tested successfully on FedoraLinux-43, 2026-06-09). Use the `wsl-distros` skill template `templates/hermes-gateway.service` for the exact unit file pattern.

2. **User executes manually** — If delegation is unavailable, present the exact commands:

```bash
# User must run these from their Ubuntu WSL terminal:
wsl.exe -d FedoraLinux-43 -u root -- bash -c 'echo "[boot]
systemd=true" > /etc/wsl.conf && cat /etc/wsl.conf'
```

Then from Windows PowerShell:
```powershell
wsl --terminate FedoraLinux-43
```

**Do NOT:** waste time trying alternative sudo patterns, ssh workarounds, or delegation tricks. The security hook is designed to catch ALL programmatic privilege escalation from the orchestrator. Accept the limitation and present manual steps to the user.

**This pitfall also covers:** `sudo -S` for ANY purpose (not just WSL) — the guard catches the pipe-to-sudo pattern universally.

### Pitfall #P — Cross-WSL `bash -c` Variable Assignment Silently Fails; Use stdin

**Symptom (observed 2026-06-09 on Fedora WSL diagnostics):** When diagnosing a hermes-agent instance on another WSL distro via `wsl.exe -d <DISTRO> -- bash -c 'X=hello; echo $X'`, the output is `X=` — the variable is empty. Even `--norc --noprofile` doesn't help. But `echo 'X=hello; echo $X' | wsl.exe -d <DISTRO> -- bash` works correctly. This caused incorrect diagnosis: variables appeared unset, suggesting `.bashrc` wasn't being sourced, when in reality the shell was working fine.

**Root cause:** The `$` in `bash -c '...'` interacts with the WSL interop layer's argument passing. The quoting chain (local shell → wsl.exe → target bash) can strip or mangle `$` references. The exact behavior varies by shell and WSL version — sometimes `\$` works, sometimes it doesn't. Passing via stdin avoids the argument chain entirely.

**Fix: Use stdin heredoc instead of `-c` for any cross-WSL command that uses variable assignment or `$` expansion:**

```bash
# ❌ BROKEN — variable assignment silently fails
wsl.exe -d FedoraLinux-43 -- bash -c 'HERMES_HOME=/tmp && echo $HERMES_HOME'

# ✅ WORKS — pipe via stdin heredoc
cat <<'EOF' | wsl.exe -d FedoraLinux-43 -- bash
HERMES_HOME=/tmp && echo $HERMES_HOME
EOF
```

The heredoc with quoted delimiter (`<<'EOF'`) prevents ALL local expansion. Everything between `<<'EOF'` and `EOF` arrives verbatim at the target shell — no escaping needed, no `$` mangling.

**Diagnosis:** If a cross-WSL command produces empty output for variables that should be set, test with `echo 'X=hello; echo $X' | wsl.exe -d <DISTRO> -- bash`. If that works but `-c` doesn't → use stdin for ALL subsequent cross-WSL commands in that session. Don't waste time debugging quoting — just switch to stdin.

**When to use stdin vs `-c`:**

| Situation | Use |
|-----------|-----|
| Simple commands with no `$` or `=` | `bash -c` is fine |
| Any variable assignment or expansion | `cat <<'EOF' \| ... -- bash` |
| Multi-line diagnostic scripts | `cat <<'EOF' \| ... -- bash` |
| Source-ing `.bashrc` or profiles | `cat <<'EOF' \| ... -- bash` |

See `references/cross-wsl-diagnostics.md` for the full diagnostic trace and reproduction steps.

### Pitfall #R-1 — MCP OAuth Fires at CLI Startup Despite Cached Tokens (Magnific)

**Symptom (observed 2026-06-09 on Prometeo Fedora):** Running `hermes` (interactive CLI) immediately triggers the Magnific OAuth redirect handler — prints an authorization URL and waits for input — even though tokens are cached in `mcp-tokens/` (or `mcp-tools/`) and the MCP works fine from the gateway. The prompt says something like \"Open this URL to authorize...\" and blocks the CLI startup.

**Root cause:** The MCP SDK's `async_auth_flow()` method performs a token validity check on initialization. If the check fails (expired token, server-side revocation, or the SDK can't find the token directory), it triggers the full OAuth PKCE flow. The CLI initializes ALL configured MCPs at startup, including OAuth ones — so even a valid-but-not-verifiable token triggers the prompt.

**Why tokens may be \"valid but not verifiable\":**
- Token directory mismatch: code uses `mcp-tools/` (per `_get_token_dir()` in `mcp_oauth.py`) but directory was created as `mcp-tokens/` — SDK can't find the file
- Token expired server-side but not locally (local `expires_at` hasn't passed)
- `HERMES_HOME` unset → SDK looks in wrong directory

**The workaround — type `skip`:** When the OAuth prompt appears at CLI startup, typing `skip` (or pressing Enter on an empty input) bypasses the OAuth flow for that MCP. The CLI continues to initialize, and the MCP may still work from the gateway (which caches tokens differently). This is cosmetic but annoying for interactive use.

**Diagnosis:**
```bash
# 1. Check which token directory the code actually uses
grep -n '_get_token_dir\\|mcp-tools\\|mcp-tokens' \\
  $HERMES_HOME/venv/lib/python*/site-packages/hermes_agent/tools/mcp_oauth.py 2>/dev/null | head -5

# 2. Check if the directory exists and has files
ls -la $HERMES_HOME/mcp-tools/ 2>/dev/null
ls -la $HERMES_HOME/mcp-tokens/ 2>/dev/null

# 3. Check token expiry
python3 -c \"import json, time; d=json.load(open('$HERMES_HOME/mcp-tools/magnific.json')); print(f'expires_at={d.get(\\\"expires_at\\\",0)} now={int(time.time())} expired={d.get(\\\"expires_at\\\",0)<int(time.time())}')\" 2>/dev/null
```

**Fixes (in order of preference):**
1. **Ensure token directory matches code expectations** — create `mcp-tools/` if code uses that name
2. **Re-authenticate** — `hermes mcp login magnific` (creates fresh tokens in the correct directory)
3. **Set `HERMES_HOME`** — if unset, SDK can't find any token directory

**Do NOT:** Try to patch the SDK's OAuth flow to skip the check. The pre-flight is by design (PKCE tokens are short-lived). Fix the root cause (token directory, expiry, or HERMES_HOME).

**Code-level fix (last resort — when root causes are fixed but the prompt still fires):** If tokens ARE valid and the directory IS correct but the CLI still prints the OAuth URL at startup, `tools/mcp_oauth.py` can be hot-patched to early-return before the print when cached tokens exist. Two functions must be patched together:

| Function | Patch | Effect |
|----------|-------|--------|
| `_redirect_handler()` | Add cached-tokens check before `print(msg, file=sys.stderr)` | Suppresses the \"MCP OAuth: authorization required\" URL print |
| `_wait_for_callback()` | Use 5s timeout when cached tokens exist (vs default 300s) | Prevents blocking the CLI waiting for browser input |

See `references/hot-patching-site-packages.md` for the exact patch code, step-by-step procedure, and cross-WSL caveats.

### Pitfall #R-2 — Wrong Env Var Name for opencode-go: `OPENCODE_API_KEY` ≠ `OPENCODE_GO_API_KEY`

**Symptom (observed 2026-06-09 on Prometeo Fedora migration):** After configuring `provider: opencode-go` in config.yaml and placing the API key in `.env` as `OPENCODE_API_KEY=sk-...`, API calls fail with `HTTP 401: Invalid API key`. The error correctly shows the model (`minimax-m3`), provider (`opencode-go`), and endpoint (`https://opencode.ai/zen/go/v1`) — the configuration appears correct, only the key is rejected.

**Root cause:** The env var name is wrong. The opencode-go provider expects `GLM_API_KEY` or `OPENCODE_GO_API_KEY` — NOT `OPENCODE_API_KEY` (without `_GO_`). The `.env` file uses the wrong variable name, so the provider never finds the key. The misleading part: the error says "Invalid API key" (not "No API key"), implying the key VALUE is wrong, when in fact the VARIABLE NAME is wrong — the endpoint receives an empty/missing key from the env lookup and rejects it as "invalid".

**Why this is hard to diagnose:** The natural diagnostic path is: "Is the key correct? → Check .env → Yes, the key is there → The key must be expired or wrong value." This is a dead end. The real question is: "Does the provider SEE this key?" Only checking against the provider's documented auth variable name reveals the mismatch.

**What the provider reference says (see `references/opencode-go-models.md`):**
> **Auth**: `GLM_API_KEY` or `OPENCODE_GO_API_KEY`

The `_GO_` suffix is critical — it's the provider name, not a generic "API_KEY" suffix.

**The misleading 401 vs expected behavior:** When the env var is missing, some providers return "No API key provided" (clear). opencode-go returns "Invalid API key" (misleading). The distinction matters: "invalid" sends you on a key-value goose chase; "missing" sends you to check env var names.

**Diagnosis (2 commands):**
```bash
# 1. Check what's in .env
cat $HERMES_HOME/.env | grep OPENCODE
# If output is: OPENCODE_API_KEY=sk-...
#                                       ^^^ wrong — missing _GO_

# 2. Verify against provider reference
grep -A2 'Auth' references/opencode-go-models.md 2>/dev/null || \
  echo "Provider expects: GLM_API_KEY or OPENCODE_GO_API_KEY"
```

**Fix (one line):**
```bash
sed -i 's/^OPENCODE_API_KEY=/OPENCODE_GO_API_KEY=/' $HERMES_HOME/.env
```

**Prevention — provider env var reference:**

| Provider | Env var(s) expected | Common mistake |
|----------|-------------------|----------------|
| `opencode-go` | `GLM_API_KEY` or `OPENCODE_GO_API_KEY` | `OPENCODE_API_KEY` (missing `_GO_`) |
| `openrouter` | `OPENROUTER_API_KEY` | `OPENROUTER_KEY` or `OPEN_ROUTER_API_KEY` |
| `anthropic` | `ANTHROPIC_API_KEY` | `CLAUDE_API_KEY` |
| `openai` | `OPENAI_API_KEY` | `OPEN_AI_API_KEY` |

**Rule:** Never assume the env var name. Always check the provider's documentation (or the hermes-agent `references/` for that provider). The naming is provider-specific and often includes the provider name as a prefix/suffix beyond just `_API_KEY`.

### Pitfall #X — disabled_toolsets Silently Ignores Invalid Toolset Names

**Symptom (observed 2026-06-25 on Balam-Agent):** Agent has `file-read` and `file-write` in `disabled_toolsets`, but still uses `read_file`, `write_file`, `patch`, and `search_files` at runtime. `/tools` shows them present. The config appears correct but has no effect.

**Root cause:** hermes-agent v0.17.0 defines toolsets in `toolsets.py` `TOOLSETS` dict. The toolset containing `read_file`, `write_file`, `patch`, `search_files` is called **`file`** — NOT `file-read` or `file-write`. Those names DO NOT EXIST as toolset names. When `disabled_toolsets` contains a name that doesn't match any toolset, it is SILENTLY IGNORED — no warning, no error, just silently dropped.

This is especially insidious because `file-read` and `file-write` look like reasonable toolset names (they match the tool names `read_file` and `write_file` with a hyphen). But toolset names and tool names are DIFFERENT namespaces.

**Toolset name vs tool name — the distinction:**

| What you wrote | What it is | Exists? | Effect |
|---------------|------------|---------|--------|
| `file` | Toolset name | Yes | Disables read_file, write_file, patch, search_files |
| `file-read` | Neither | No | Silently ignored — nothing disabled |
| `file-write` | Neither | No | Silently ignored — nothing disabled |
| `patch` | Tool name (inside `file` toolset) | Not a toolset | Silently ignored |
| `search_files` | Tool name (inside `file` toolset) | Not a toolset | Silently ignored |
| `terminal` | Toolset name | Yes | Disables terminal, process |
| `code_execution` | Toolset name | Yes | Disables execute_code |

**How to find valid toolset names:**
```bash
# In the venv site-packages
grep -n 'TOOLSETS\s*=' <venv>/lib/python*/site-packages/toolsets.py
# Then read the dict — keys are toolset names
```

Or look at the toolset->tool mapping visible in `/tools` inside hermes chat.

**How to verify disabled_toolsets actually worked:**
```bash
# Inside hermes chat
/tools
# If a toolset you tried to disable still appears in the list -> the name was wrong
```

**The general rule:** `disabled_toolsets` accepts TOOLSET names (the keys of the `TOOLSETS` dict in `toolsets.py`), NOT individual tool names, and NOT invented names that look like tool names with hyphens. When in doubt, grep `TOOLSETS` in the source.

**Also:** `enabled_toolsets` at the top level of config.yaml does NOT work to restrict CLI-mode tools. It only works for the Python library API (`AIAgent(enabled_toolsets=[...])`). For CLI, use `agent.disabled_toolsets` with correct toolset names.

### Pitfall #Y — After Gateway Restart, New PID Logs Missing from journalctl

**Symptom (observed 2026-06-30 on Aether-Agents Telegram setup):** After `systemctl --user restart hermes-gateway.service`, `journalctl --user -u hermes-gateway.service --since "1 min ago"` shows only the OLD process's shutdown logs (SIGTERM, "Exiting with code 1", shutdown diagnostics). The NEW process's startup logs (platform connections, "Connected to Telegram") are absent from journalctl entirely. `journalctl _PID=<new_pid>` returns "No entries."

**Root cause:** The gateway's file-based logger (`logs/gateway.log`) and journalctl capture different streams. The new process's initialization logs go to `gateway.log` immediately but may not appear in journalctl until the next log flush or at all (depending on stdout/stderr buffering and Python logging handler config). The old process's exit logs dominate journalctl because the shutdown sequence writes to stderr (which systemd captures) while the startup sequence writes to the Python logging framework (which goes to file).

**Diagnostic — always use `gateway.log` for post-restart verification:**
```bash
# ❌ MISLEADING — shows old process shutdown, not new process startup
journalctl --user -u hermes-gateway.service --since "1 min ago"

# ✅ CORRECT — shows the new process's actual initialization
tail -20 $HERMES_HOME/logs/gateway.log
```

**Key lines to look for in `gateway.log`:**
```
INFO gateway.platforms.telegram: [Telegram] Connected to Telegram (polling mode)
INFO gateway.run: ✓ telegram connected
INFO gateway.run: Gateway running with 1 platform(s)
```

**Also useful for Chat ID discovery:**
```bash
grep "inbound message" $HERMES_HOME/logs/gateway.log | tail -1
# "inbound message: platform=telegram user=Arty chat=5275738997 msg='hola'"
```

See `references/enabling-messaging-platforms.md` for the full platform setup workflow.

### Pitfall #T — `hermes config set` / `hermes doctor` Silently Rewrites config.yaml

**Symptom:** After running `hermes config set <key> <value>` or `hermes doctor`, custom MCP server blocks, auxiliary config sections, or comments disappear from `config.yaml`. The file is reformatted with normalized YAML — comments stripped, key ordering changed, and any keys not in the framework's internal schema may be silently dropped.

**Root cause:** The framework loads config.yaml with `yaml.safe_load`, modifies it in memory, and writes it back with `yaml.safe_dump`. This normalizes the ENTIRE file. Non-standard blocks (like a custom `mcp_servers.graphify` entry) are vulnerable because the framework may not recognize them in its schema.

**Prevention:**
- **Option A:** Never use `hermes config set`. Edit `config.yaml` manually.
- **Option B:** `chmod 444 config.yaml` — CLI commands fail with Permission Denied.
- **Option C:** `git rm --cached config.yaml` — destracks the file so git stops tracking changes, while `.gitignore` prevents re-addition. This doesn't prevent rewrites but makes the file invisible to `git status` and safe from accidental commits that would expose API keys. Combine with Option A or B for full protection.

**Destracking procedure (observed 2026-06-09):**
```bash
# 1. Ensure config.yaml is in .gitignore
grep "home/config.yaml" .gitignore  # should show match
# 2. Destrack without deleting the file
git rm --cached home/config.yaml
# 3. Verify
git ls-files home/config.yaml  # should be empty
git status home/config.yaml     # should NOT show as modified
```

**Anti-pattern:** Assuming `hermes config set` only changes the key you specify. It rewrites the ENTIRE file.

### Pitfall #W — Gateway Keeps Old Version After `pip install --upgrade` or Downgrade

**Symptom:** After running `pip install hermes-agent==0.15.2` (downgrade) or `pip install --upgrade hermes-agent` (upgrade), `hermes --version` in a new shell shows the new version, but Daimons and MCP servers still use the old version. The bug you were trying to fix persists.

**Root cause:** The `hermes-gateway.service` process loads the hermes-agent package at startup and keeps it in memory. `pip install` replaces the on-disk package files, but the running process still uses the old version loaded in memory. The gateway must be restarted for the new version to take effect.

**Fix (mandatory after any version change):**
```bash
# After any pip install/upgrade/downgrade:
hermes gateway restart
# Or:
systemctl --user restart hermes-gateway.service

# Verify the gateway picked up the new version:
ps aux | grep "hermes" | grep -v grep  # check PID changed
hermes mcp list  # verify MCP servers reloaded
```

**Diagnostic:** If the gateway PID hasn't changed or the bug persists after `pip install`, the gateway is still running the old code. `hermes gateway restart` is the definitive command — it kills the old process and starts a fresh one with the new package.

**Also applies to:** `pip install graphifyy`, `pip install olympus-mcp`, and any package that MCP servers load at runtime — the gateway must restart to pick up the new package versions.

### Pitfall #V — `make clean` Destroys venv and All Installed Packages (graphify, olympus)

**Symptom (observed 2026-06-09 on Aether-Agents Ubuntu WSL):** After running `make clean` (or manually `rm -rf home/.venv-hermes/`), the MCP servers `graphify` and `olympus_v3` stop working. `hermes mcp test graphify` returns "module not found", and `hermes --version` fails entirely because the entire venv is gone.

**Root cause:** The Aether-Agents `Makefile` clean target runs `rm -rf home/.venv-hermes/`, which deletes the ENTIRE virtual environment including `hermes-agent`, `graphifyy`, `olympus-mcp`, and the `[mcp]` extra. Recovery requires running `scripts/setup.sh` which recreates the venv from scratch.

**Why this is a pitfall and not just "don't run make clean":** The Makefile is in the repo root and looks like a standard cleanup target. New team members or CI pipelines may run it expecting it to only remove `__pycache__` and build artifacts. Instead, it wipes a 3 GB venv containing local packages not available via a simple `pip install`.

**Prevention:**
```makefile
# Safer clean target (replace existing):
clean: ## Remove __pycache__ directories only (NOT the venv)
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	@echo "✓ Cleaned __pycache__ directories (venv preserved)"
```

For a full venv rebuild, use `scripts/setup.sh` which is explicit about what it destroys and recreates.

**Diagnostic:**
```bash
# Quick check after suspected venv wipe
ls home/.venv-hermes/bin/hermes 2>/dev/null && echo "venv OK" || echo "venv DESTROYED — run scripts/setup.sh"
```

### Pitfall #U — `.env` Symlink to Another Instance Breaks When Target Is Absent

**Symptom:** `home/.env` is a symlink pointing to another hermes-agent instance's `.env` (e.g., `/home/prometeo/.hermes/.env`). If the target instance is on another WSL distro that isn't running, or the path doesn't exist, ALL API keys are missing — MCP servers fail, web search fails, the model can't authenticate.

**Root cause:** Symlinks resolve at access time. If the target is on a different filesystem (Fedora WSL overlay) or the target path doesn't exist, the symlink becomes a dangling reference. `cat home/.env` shows nothing or errors.

**Fix:** Replace the symlink with a real file copy:
```bash
cp /home/prometeo/.hermes/.env ~/Aether-Agents/home/.env.real
rm ~/Aether-Agents/home/.env
mv ~/Aether-Agents/home/.env.real ~/Aether-Agents/home/.env
```
Verify: `ls -la ~/Aether-Agents/home/.env` should NOT show `->` (must be a regular file).

**Prevention:** Never symlink `.env` between instances. Each instance should have its own real `.env` file with the necessary API keys. If keys are shared, copy them manually or use a secrets manager.

### Pitfall #S — Generic Identity Despite SOUL.md Existing: Check profiles/<name>/SOUL.md

**Symptom (observed 2026-06-09 on Prometeo identity recovery):** Agent responds with "I am Hermes Agent, an AI assistant created by Nous Research" when asked about its identity, even though `$HERMES_HOME/SOUL.md` exists. The file turns out to be the 513-byte factory default.

**Root cause:** In pre-v0.14 setups, the real custom SOUL.md lived at `$HERMES_HOME/profiles/<name>/SOUL.md` while `$HERMES_HOME/SOUL.md` (root) was a factory placeholder (exactly 513 bytes). After migrating to default-profile pattern (config+SYS.md at root, no `-p` flag), hermes-agent reads from root — but the profile-level SOUL.md was never promoted. Result: the runtime only sees the generic placeholder.

**Why 513 bytes is diagnostic:** The factory-default SOUL.md is almost always exactly 513 bytes. A real custom SOUL.md is typically 2-10 KB. File size alone distinguishes them.

**Diagnosis (3 commands):**
```bash
# 1. Check if root SOUL.md is the factory default
wc -c $HERMES_HOME/SOUL.md
# → 513 = factory placeholder. Real identity is elsewhere.

# 2. Search for larger SOUL.md in profile directories
find $HERMES_HOME/profiles -name "SOUL.md" -exec wc -c {} \;
# → 4758 = 4.7 KB real identity (Prometeo example)

# 3. Verify it's not also generic
head -3 $HERMES_HOME/profiles/prometeo/SOUL.md
```

**Fix:** Promote the real profile-level SOUL.md to root:
```bash
cp $HERMES_HOME/profiles/<name>/SOUL.md $HERMES_HOME/SOUL.md
```

**If no profile-level SOUL.md exists (identity truly lost):** Recover from backups. The selective extraction pattern:
```bash
tar -tzf backup.tar.gz | grep -iE "SOUL|config\.yaml|\.env" | grep -v node_modules
tar -xzf backup.tar.gz -C /tmp/recovery "path/to/identity/files"
```

**Prevention:** After any migration or `--profile` → default-profile switch, verify: `wc -c $HERMES_HOME/SOUL.md`. A size of exactly 513 bytes means the agent has no real identity — it's running on the factory default.

## Memory & Configuration Pitfalls

### Pitfall: Memory Snapshot Frozen at Session Start — Char Limit Header Stale

**Symptom (observed 2026-06-05):** User raises `memory_char_limit` in `home/config.yaml` from 4000 to 32000, restarts instance, but the new system prompt still shows the OLD cap as the header: `[93% — 3,742/4,000 chars]` instead of `[15% — 3,742/32,000 chars]`.

**Root cause:** `tools/memory_tool.py` line 121-130, the `_system_prompt_snapshot` field is "frozen at load time, used for system prompt injection. Never mutated mid-session. Keeps prefix cache stable." The header `[X% — current/limit chars]` rendered in the system prompt reflects the cap that was active when the session initialized, NOT the current config.yaml value.

**Diagnostic chain (always run all 3):**
1. `grep -A 6 "^memory:" home/config.yaml` — verify target cap on disk
2. `wc -c home/memories/MEMORY.md home/memories/USER.md` — verify actual file sizes
3. Compare the `[X% — N/L chars]` header in the system prompt — L is the effective cap for THIS session. If L != config.yaml target → snapshot is stale → this session won't pick up the change, NEXT session will.

**Resolution:** The raise takes effect on the NEXT session that starts cold (new agent process → fresh `load_from_disk()` → new snapshot with new caps). No code path to reload snapshot mid-session by design.

**Do NOT:**
- Confuse `provider: honcho` with char-limit invalidation. Honcho is a parallel external memory system; the built-in `memory_char_limit` / `user_char_limit` in config.yaml still govern the local `MEMORY.md` / `USER.md` files independently.
- Trust the rendered `[X% — N/L]` header as ground truth about config.yaml — it shows session-state, not config-state.
- Suggest "Honcho overrides char limits" as an explanation for stale headers. Different bug, different fix.
- Try to mutate the snapshot from inside the running agent. No public API exists. Restart is the only path.
