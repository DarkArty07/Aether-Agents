# Cross-Distro hermes-agent Migration (WSL)

Complete, tested workflow for migrating a hermes-agent instance between WSL distros
(e.g., Ubuntu → Fedora). Validated 2026-06-09 on the Prometeo migration.

## Prerequisites

- Source distro has the hermes-agent data directory (HERMES_HOME) with skills, sessions,
  config, memories, skins, etc.
- Source distro's venv should NOT be copied — venvs are distro-specific (system libs,
  compiled extensions). Build a fresh venv on the target.
- The target distro must be running (`wsl.exe -l -v` shows "Running").
- You know the target username (e.g., `prometeo_assistant` on Fedora).
- If systemd is needed (gateway service): the target distro must have systemd enabled
  in `/etc/wsl.conf` with `[boot] systemd=true`.

## Phase 1: Snapshot and Inventory

```bash
# On source distro: catalog what's being migrated
du -sh $SOURCE_HERMES_HOME
ls $SOURCE_HERMES_HOME/          # skills/ sessions/ cache/ memories/ skins/ etc.
echo $HERMES_HOME                # Confirm the data dir
hermes --version                 # Note the version (for matching pip install)

# CRITICAL — Verify config.yaml EXISTS (it may not survive prior migrations):
ls -la $SOURCE_HERMES_HOME/config.yaml 2>/dev/null && echo "✓ config.yaml exists" || echo "✗ NO config.yaml — create one before migrating"
ls -la $SOURCE_HERMES_HOME/.env 2>/dev/null && echo "✓ .env exists" || echo "✗ NO .env — API keys will need manual recreation"
ls -la $SOURCE_HERMES_HOME/skills/ 2>/dev/null && echo "✓ skills/ exists" || echo "✗ NO skills/"
ls -la $SOURCE_HERMES_HOME/sessions/ 2>/dev/null && echo "✓ sessions/ exists" || echo "✗ NO sessions/"
```

> **⚠️ MANDATORY GATE:** If `config.yaml` does NOT exist in the source, STOP.
> Create a minimal `config.yaml` first (see `references/standard-setup.md`), then
> resume migration. Migrating without config.yaml means the target instance
> will have no model, no provider, no toolsets — it won't work.

## Phase 2: Clean Target

Delete any pre-existing corrupt installations on the target:

```bash
echo 'rm -rf /home/TARGET_USER/.hermes/ /home/TARGET_USER/.prometeo/' | \
  wsl.exe -d TARGET_DISTRO -- bash
```

Verify:
```bash
echo 'ls -d /home/TARGET_USER/.hermes /home/TARGET_USER/.prometeo 2>&1' | \
  wsl.exe -d TARGET_DISTRO -- bash
# Expected: "No such file or directory" for both
```

## Phase 3: Install hermes-agent on Target (pip + venv)

Use `pip install hermes-agent` in a dedicated venv — the official method (v0.14+):

```bash
cat <<'INSTALL_EOF' | wsl.exe -d TARGET_DISTRO -- bash
# Create dedicated venv
python3 -m venv /home/TARGET_USER/.prometeo/venv/
# Install hermes-agent
/home/TARGET_USER/.prometeo/venv/bin/pip install hermes-agent
# Install MCP extras (REQUIRED — base install does NOT include MCP SDK)
/home/TARGET_USER/.prometeo/venv/bin/pip install 'hermes-agent[mcp]'
# Verify
/home/TARGET_USER/.prometeo/venv/bin/hermes --version
# Verify MCP SDK
/home/TARGET_USER/.prometeo/venv/bin/python -c 'import mcp; print("mcp", mcp.__version__)'
INSTALL_EOF
```

For Python 3.14+ (Fedora): `python3` is available. For older distros, use `python3.11` or the system Python.

## Phase 4: Copy Data (tar pipe, exclude venv)

**CRITICAL:** Use `tar` pipe via stdin, NOT `bash -c` (see Pitfall #P — cross-WSL
bash -c swallows variables). The source distro's venv is excluded.

```bash
# From source distro, pipe to target distro
cat <<'COPY_EOF' | wsl.exe -d TARGET_DISTRO -- bash
sudo -S mkdir -p /home/TARGET_USER/.prometeo
COPY_EOF
# (sudo password via echo or interactive)

tar czf - -C $SOURCE_HERMES_HOME . --exclude=venv --exclude='*.pyc' --exclude=__pycache__ | \
  wsl.exe -d TARGET_DISTRO -- bash -c 'tar xzf - -C /home/TARGET_USER/.prometeo/'
```

**Why tar pipe instead of cp/scp:**
- Single command, no intermediate files (~881MB handled cleanly)
- `--exclude` filters out venv (distro-specific) and pycache
- tar preserves permissions, symlinks, and directory structure
- Pipe avoids disk I/O for temp archives

**Verify copy:**
```bash
echo 'du -sh /home/TARGET_USER/.prometeo/ && ls /home/TARGET_USER/.prometeo/' | \
  wsl.exe -d TARGET_DISTRO -- bash
```

## Phase 5: Configure Target

All via stdin pattern:

```bash
cat <<'CONFIG_EOF' | wsl.exe -d TARGET_DISTRO -- bash

# 5a. Symlink venv binary (NOT a wrapper script)
rm -f ~/.local/bin/hermes
ln -s ~/.prometeo/venv/bin/hermes ~/.local/bin/hermes

# 5b. Set HERMES_HOME in .bashrc (only if not already present)
grep -q 'HERMES_HOME' ~/.bashrc || \
  echo 'export HERMES_HOME="$HOME/.prometeo"' >> ~/.bashrc

# 5c. Verify symlink
ls -la ~/.local/bin/hermes
# Must show: ... -> /home/TARGET_USER/.prometeo/venv/bin/hermes

CONFIG_EOF
```

### 5d. Create config.yaml (default profile pattern)

Use `cat <<'EOF'` to create the config.yaml at `$HERMES_HOME/config.yaml`
directly (no `-p` flag needed — use default profile, not named profile).

> **Note:** This step requires the actual config content. Use the source distro's
> config as reference, or build from scratch with the `standard-setup.md` reference.
> Key sections: model, provider, toolsets, mcp_servers, display.skin.

### 5e. Replicate .env with API keys

The `.env` file (API keys) does NOT survive migrations. You need:
- Telegram bot token
- Provider API keys (OpenRouter, OpenCode, etc.)
- Any service-specific keys

These must be recreated manually or restored from a secure backup.

## Phase 6: Gateway Service (systemd)

### 6a. Enable systemd on target WSL distro

**⚠️ Hermes CANNOT execute this step automatically.** The security hook blocks both
`sudo -S` (brute-force guard) and `wsl.exe -u root` with file writes (write-restriction
hook). The user MUST run these commands manually.

**User — run from your Ubuntu WSL terminal:**
```bash
wsl.exe -d TARGET_DISTRO -u root -- bash -c 'echo "[boot]
systemd=true" > /etc/wsl.conf && cat /etc/wsl.conf'
```

**User — then from Windows PowerShell/CMD:**
```powershell
wsl.exe --terminate TARGET_DISTRO
```

**User — reopen the distro and verify:**
```bash
wsl.exe -d TARGET_DISTRO -- bash -c 'systemctl --user status 2>&1 | head -3'
# Should show systemd running, not "Failed to connect to bus"
```

### 6b. Create systemd user unit

```bash
cat <<'UNIT_EOF' | wsl.exe -d TARGET_DISTRO -- bash
mkdir -p ~/.config/systemd/user/
cat > ~/.config/systemd/user/hermes-gateway-prometeo.service <<'SVC'
[Unit]
Description=Hermes Gateway - Prometeo
After=network.target

[Service]
Type=simple
ExecStart=/home/TARGET_USER/.prometeo/venv/bin/python -m hermes_cli.main gateway run --replace
WorkingDirectory=/home/TARGET_USER/.prometeo
Environment=HERMES_HOME=/home/TARGET_USER/.prometeo
Environment=PATH=/home/TARGET_USER/.prometeo/venv/bin:/usr/local/bin:/usr/bin:/bin
Restart=on-failure
RestartSec=5

[Install]
WantedBy=default.target
SVC
UNIT_EOF
```

### 6c. Enable and start

```bash
echo 'systemctl --user daemon-reload && systemctl --user enable --now hermes-gateway-prometeo.service' | \
  wsl.exe -d TARGET_DISTRO -- bash
```

## Phase 7: Verification

```bash
cat <<'VERIFY_EOF' | wsl.exe -d TARGET_DISTRO -- bash
echo "=== Symlink ==="
ls -la ~/.local/bin/hermes

echo "=== HERMES_HOME ==="
echo $HERMES_HOME

echo "=== Config ==="
hermes config show 2>&1 | head -5

echo "=== Gateway ==="
systemctl --user status hermes-gateway-prometeo.service --no-pager -l

echo "=== MCPs ==="
hermes mcp 2>&1 | head -20
VERIFY_EOF
```

## Post-Restore Config Adaptation Checklist

After restoring a config.yaml from backup (especially cross-distro or cross-user),
FOUR fields must be verified before the instance will work. This checklist was
validated 2026-06-09 on the Prometeo backup restoration (Ubuntu → Fedora).

### 1. `api_mode` — Must match the current provider

The backup config may have been authored with a different provider or API format.
For example: a config using `opencode-go` must have `api_mode: chat_completions`,
NOT `api_mode: anthropic_messages`. The wrong mode causes silent API failures
(401 errors or empty responses).

```bash
# Check current api_mode
grep 'api_mode' $HERMES_HOME/config.yaml

# Fix for opencode-go (chat_completions):
sed -i 's/api_mode: anthropic_messages/api_mode: chat_completions/' $HERMES_HOME/config.yaml
```

**Why this bites:** A 401 looks like a key problem, but the key is correct — the
provider can't parse the request format. The `chat_completions` mode sends JSON
in OpenAI-compatible format; `anthropic_messages` sends Anthropic-native format.
opencode-go only accepts `chat_completions`.

### 2. `external_dirs` — Skills paths from other projects

If the backup config references skill directories from a different project
(e.g., `Aether-Agents/home/skills`), these won't exist on the target distro.
Fix: point to the local skills directory or remove the entry (skills inside
`$HERMES_HOME/skills/` are auto-discovered, `external_dirs` is for extras).

```bash
# Check what external_dirs points to
grep -A3 'external_dirs' $HERMES_HOME/config.yaml

# Fix: point to local skills (or remove the block entirely)
sed -i 's|/home/olduser/Aether-Agents/home/skills|/home/newuser/.prometeo/skills|' $HERMES_HOME/config.yaml
```

### 3. All absolute paths — User home, cwd, env blocks

After migrating between users (`prometeo` → `prometeo_assistant`), every
absolute path in config.yaml is wrong. Use a single `sed` to batch-adapt:

```bash
sed -i 's|/home/olduser/|/home/newuser/|g' $HERMES_HOME/config.yaml
```

This catches: `terminal.cwd`, MCP server `args:`, `env:` blocks, `working_dir`,
and any custom path keys. Verify with `grep '/home/' $HERMES_HOME/config.yaml`
that no old paths remain.

### 4. Auth variable names — Provider-specific env vars

The `.env` file from backup may use wrong variable names for the current provider.
The most common trap: `OPENCODE_API_KEY` (generic) vs `OPENCODE_GO_API_KEY`
(provider-specific). See hermes-agent Pitfall #R for full diagnosis.

```bash
# Verify the variable name matches the provider
grep '^OPENCODE' $HERMES_HOME/.env
# If OPENCODE_API_KEY=... → should be OPENCODE_GO_API_KEY=... for opencode-go
```

### Quick all-in-one diagnostic:

```bash
echo "=== 1. api_mode ===" && grep 'api_mode' config.yaml
echo "=== 2. external_dirs ===" && grep -A3 'external_dirs' config.yaml
echo "=== 3. Old paths ===" && grep '/home/' config.yaml | grep -v "newuser"
echo "=== 4. Auth vars ===" && grep '^[A-Z_]*API_KEY' .env | cut -d= -f1
echo "=== 5. MCP SDK ===" && python -c 'import mcp; print("mcp", mcp.__version__)' 2>&1 || echo "MISSING — pip install 'hermes-agent[mcp]'"
```

**Run this checklist after EVERY backup restoration.** The 4 items above are
silent misconfigurations — hermes-agent won't error on startup, but API calls
will fail, skills won't load, and MCP servers will behave unpredictably.

## Post-Migration MCP Server Audit & Cleanup

After restoring a config.yaml from backup onto a different distro, MCP servers
will fail until their prerequisites are verified and paths are adapted. This
workflow was validated 2026-06-09 on Prometeo's Fedora restoration.

### The Problem

Backup configs carry MCP server definitions that assume:
- Binaries (`node`, `npx`, `uv`, `uvx`) exist at specific paths from the old distro
- stdio MCPs reference `node` or `uv` commands that may not be installed on the target
- HTTP MCPs with OAuth tokens don't work across instances (tokens are instance-bound)
- Some MCPs reference Windows paths (`/mnt/c/...`) that may or may not be mounted

### Audit Step: What fails and why

```bash
# List all MCPs and their commands
python3 -c "
import yaml
with open('config.yaml') as f:
    cfg = yaml.safe_load(f)
for name, mcp in cfg.get('mcp_servers', {}).items():
    cmd = mcp.get('command', mcp.get('url', '?'))
    mtype = mcp.get('type', 'stdio')
    enabled = mcp.get('enabled', True)
    print(f'{name}: {mtype}, enabled={enabled}, cmd={cmd[:80]}')
"
```

### Verify Binaries Exist on Target

For each stdio MCP, the command's first word (binary/runner) must exist:

```bash
# Check key runners
which node 2>&1    # Required by: reddit MCP (if using node directly)
which npx 2>&1     # Required by: context7, todoist (npm packages)
which uv 2>&1      # Required by: clio-fca (uv run)
which uvx 2>&1     # Required by: some Python MCPs
```

### Prerequisite Installation (Fedora)

```bash
# Node.js + npm (for npx-based MCPs)
sudo dnf install -y nodejs

# Verify after install
node --version  # Should show v22+
npx --version
```

`uv`/`uvx` come from the hermes-agent installer. If missing, re-run the
hermes-agent install script or `pip install uv`.

> **⚠️ PITFALL: `pip install hermes-agent` does NOT install `uv`.** On a fresh
> venv, `hermes-agent` is installed as a pip package but `uv` (a separate Rust
> binary) is not pulled in as a dependency. Any MCP using `uv run ...` (common
> for Python-based MCPs like clio-fca) will fail with a silent command-not-found.
> **Fix:** `source venv/bin/activate && pip install uv` after `pip install hermes-agent`.
> Verify with `which uv` — it should resolve inside the venv.

### "All MCPs Failing After Restart" — Diagnostic Pattern

When ALL MCP servers show as `failed` simultaneously after restarting a
freshly-restored instance, the cause is almost always **systemic** — a missing
binary, an absent directory, or a PATH/HERMES_HOME issue — not individual MCP
configs. This pattern was validated 2026-06-09 on Prometeo's Fedora migration.

**Symptoms:**
- All MCPs (stdio and http) show `failed` in the gateway dashboard
- Gateway starts, shows the banner, then exits with `status=1/FAILURE`
- Journalctl shows the banner followed immediately by exit code 1 — NO error
  messages visible between banner and exit
- Running the gateway manually with `timeout 10` shows the actual MCP startup
  errors that systemd's journal filters out

**Diagnostic workflow (run ALL 4 steps before fixing anything):**

```bash
# STEP 1: Verify the systemd unit has correct HERMES_HOME and PATH
cat /etc/systemd/system/hermes-gateway-*.service
# Check: Environment=HERMES_HOME=... and Environment=PATH=... are present

# STEP 2: Check journal for the crash pattern
journalctl -u hermes-gateway-*.service --no-pager -n 30
# Look for: "Hermes Gateway Starting..." immediately followed by "status=1/FAILURE"

# STEP 3: Verify binaries from the user context (same env as the service)
which node && echo "OK" || echo "MISSING — install: dnf install -y nodejs"
which npx && echo "OK" || echo "MISSING — npx needs nodejs"
which uv && echo "OK" || echo "MISSING — install: pip install uv in venv"
ls -d $HERMES_HOME/mcp-tokens/ 2>/dev/null && echo "OK" || echo "MISSING — create: mkdir -p $HERMES_HOME/mcp-tokens/"
ls -d $HERMES_HOME/mcp-servers/ 2>/dev/null && echo "OK" || echo "MISSING"

# STEP 4: Run gateway manually to see the REAL errors
HERMES_HOME=$HERMES_HOME timeout 10 $HERMES_HOME/venv/bin/python -m hermes_cli.main gateway run --replace 2>&1
# This will show actual MCP startup errors that journalctl hides
```

**Common root causes (in order of likelihood):**

| Cause | Symptom | Fix |
|-------|---------|-----|
| MCP Python SDK missing | ALL MCPs fail (stdio + http), `hermes mcp test` says "requires the 'mcp' Python SDK" | `pip install 'hermes-agent[mcp]'` in venv |
| `uv` not in venv | clio-fca MCP fails (`uv run` not found) | `source venv/bin/activate && pip install uv` |
| `mcp-tokens/` absent | OAuth MCPs fail (can't write tokens) | `mkdir -p $HERMES_HOME/mcp-tokens/` |
| `node` not installed | reddit MCP fails (`node` not found) | `dnf install -y nodejs` |
| SYSTEMD_PATH missing venv | `uv`/`hermes` binaries not found by service | Add `/home/user/.prometeo/venv/bin` to `Environment=PATH=` |
| HERMES_HOME unset in service | Config/.env not found | Add `Environment=HERMES_HOME=...` to unit |

**Key insight:** After `pip install hermes-agent`, `uv` is NOT automatically
installed. Check `which uv` — if it returns empty, run `pip install uv` inside
the same venv. This is NOT a hermes-agent bug; `uv` is a separate tool that MCP
configs may explicitly reference via `uv run ...`.

### Decision Gate: Which MCPs to Keep

Present the audit to the user. Let THEM decide which MCPs to keep vs discard.
This is a business decision, not a technical one:

- Some MCPs may reference Windows paths unreachable from WSL → discard
- Some may be disabled (`enabled: false`) and unused → safe to discard
- OAuth-based MCPs (like Magnific) need fresh authorization → keep config but re-auth

### Removal

```bash
python3 -c "
import yaml
with open('config.yaml') as f:
    cfg = yaml.safe_load(f)
for name in ['mcp-to-remove-1', 'mcp-to-remove-2']:
    if name in cfg.get('mcp_servers', {}):
        del cfg['mcp_servers'][name]
        print(f'REMOVED: {name}')
with open('config.yaml', 'w') as f:
    yaml.dump(cfg, f, default_flow_style=False, allow_unicode=True, sort_keys=False)
"
```

### Restart Gateway After MCP Changes

Config changes to `mcp_servers` require a gateway restart:

```bash
wsl.exe -d TARGET_DISTRO -u root -- bash -c \
  "systemctl restart hermes-gateway-prometeo.service && sleep 2 && systemctl status hermes-gateway-prometeo.service --no-pager | head -10"
```

### Notes

- **OAuth tokens do NOT survive cross-instance migration.** Even if `mcp-tokens/`
  is copied, the tokens are bound to the original instance. OAuth must be
  re-initiated on the target: `hermes mcp auth <name>`.
- **Windows paths (`/mnt/c/...`) work from WSL** as long as the Windows drive is
  mounted. Verify with `ls /mnt/c/` before keeping MCPs that reference Windows paths.
- **`npx` falls back to Windows interop** on WSL — `npx` may resolve to
  `/mnt/c/Program Files/nodejs/npx`. This works but is slower than a native install.

## Common Issues

### 1. `bash -c` swallows variables
**Symptom:** `echo $HERMES_HOME` returns empty even though `.bashrc` sets it.
**Fix:** Use stdin heredoc (`cat <<'EOF' | wsl.exe ... -- bash`) for ALL cross-WSL
commands. See `hermes-agent` skill Pitfall #P.

### 2. `systemctl --user` fails with "Failed to connect to bus"
**Symptom:** `systemctl --user` returns "No such file or directory".
**Fix:** systemd is not enabled in WSL. Add `[boot] systemd=true` to `/etc/wsl.conf`,
terminate the distro from Windows, and reopen.

### 3. `wsl: Failed to translate` warning (cosmetic)
When invoking `wsl.exe` from within a WSL distro, you may see:
`wsl: Failed to translate '\\wsl.localhost\Ubuntu\home\prometeo'`
This is cosmetic — WSL can't resolve the source distro's CWD path on the target
distro, but the command executes correctly.

### 4. `sudo` without password prompt
Use `echo 'password' | sudo -S command` in the stdin stream. Never store the
password in scripts or version control.

### 5. Venv path issues after Python upgrade
If the target distro has a different Python version (e.g., 3.14 vs 3.11), build
a fresh venv — never copy the source venv. Compiled `.so` files and shebangs
are Python-version-specific.
