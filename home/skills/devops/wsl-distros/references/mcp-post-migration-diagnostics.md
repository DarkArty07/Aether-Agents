# MCP Post-Migration Diagnostics

Checklist for MCP server failures after migrating a hermes-agent instance (Prometeo, Aether, etc.) across WSL distros or machines. Run this AFTER the service starts in the target distro.

---

## Diagnostic Protocol: 6-Point Checklist

### ⬛ #0 — Gateway-Level Preconditions (BEFORE checking MCPs)

These are "you can't even start" issues — the gateway won't launch, so MCPs
can't be tested. Check these FIRST.

**a) `hermes` binary in PATH?**
```bash
which hermes && hermes --version
```
If missing, create a wrapper:
```bash
mkdir -p ~/.local/bin
cat > ~/.local/bin/hermes << 'EOF'
#!/bin/bash
export HERMES_HOME=/path/to/.prometeo
exec /path/to/venv/bin/hermes "$@"
EOF
chmod +x ~/.local/bin/hermes
```

**b) `HERMES_HOME` set?**
```bash
echo $HERMES_HOME
# Should point to ~/.prometeo (the agent's data directory)
```
If empty, add `export HERMES_HOME=/home/<user>/.prometeo` to `~/.bashrc`
AND to the systemd unit `Environment=` line.

**c) systemd user directory exists?**
```bash
ls ~/.config/systemd/user/
```
If this directory doesn't exist, no user services can run. The gateway
has no way to auto-start. Create the directory and the unit file.

**d) `gateway_state.json` stale from old distro?**
```bash
cat ~/.prometeo/gateway_state.json | python3 -c "import sys,json; d=json.load(sys.stdin); print(f'PID:{d.get(\"pid\")} State:{d.get(\"gateway_state\")} Path:{d.get(\"argv\",[])}')"
```
If it shows paths from the OLD distro (e.g., `/home/prometeo/` instead of
`/home/prometeo_assistant/`), delete it — the gateway regenerates it:
```bash
rm ~/.prometeo/gateway_state.json
```

### 🔴 #1 — Node.js Missing (npx-based MCPs)

**Symptom:** MCP servers with `command: npx` fail silently. Gateway logs show `ENOENT` or `spawn npx ENOENT`.

**Why:** Fedora/Alma/Arch minimal don't ship Node.js. The hermes-agent installer may skip Node.js if `xz` or `tar` dependencies are missing.

**Check:**
```bash
which node && node --version
which npx && npx --version
```

**Fix:**
```bash
# Fedora
sudo dnf install -y nodejs npm
# Ubuntu
sudo apt install -y nodejs npm
```

---

### 🔴 #2 — systemd PATH Missing `/bin` and `/usr/bin` (spawn ENOENT)

**Symptom:** ALL MCP servers fail with `ENOENT spawn sh` or similar. `journalctl --user -u <service>` shows `spawn sh ENOENT`.

**Why:** systemd user units don't inherit the full user PATH. `/bin` and `/usr/bin` are often missing.

**Check:**
```bash
systemctl --user show <service> | grep Environment
# Should show PATH=/usr/local/bin:/usr/bin:/bin
```

**Fix — systemd drop-in override:**
```bash
mkdir -p ~/.config/systemd/user/<service>.service.d
cat > ~/.config/systemd/user/<service>.service.d/override.conf << 'EOF'
[Service]
Environment=PATH=/usr/local/bin:/usr/bin:/bin
EOF
systemctl --user daemon-reload
systemctl --user restart <service>
```

---

### 🔴 #3 — Config.yaml Absolute Paths Point to Old Distro

**Symptom:** Some MCP servers fail, others work. The failing ones have hardcoded paths.

**Why:** `config.yaml` was copied from the source distro. Fields like `command`, `args`, `env`, `cwd` may reference `/home/<old_user>/...` instead of `/home/<new_user>/...`.

**Check:**
```bash
grep -n '/home/' ~/.prometeo/config.yaml | grep -v '^#' | head -20
# Any paths that don't resolve? Fix them.
```

**Common path differences in Prometeo migration (Ubuntu → Fedora):**

| Ubuntu (source) | Fedora (target) |
|-----------------|-----------------|
| `/home/prometeo/.prometeo/...` | `/home/prometeo_assistant/.prometeo/...` |
| `/home/prometeo/Aether-Agents/home/.venv-hermes/bin/python` | `/home/prometeo_assistant/.prometeo/venv/bin/python` |

---

### 🟡 #4 — OAuth Tokens Not Migrated

**Symptom:** MCP servers that use OAuth (Magnific, etc.) prompt for re-authentication on every gateway restart, or fail with 401.

**Why:** The token cache directory (`~/.prometeo/mcp-tokens/`) was either not included in the snapshot or was cleared. The gateway can't find cached tokens.

**Check:**
```bash
ls -la ~/.prometeo/mcp-tools/
# Should contain .json files for each OAuth MCP server (e.g., magnific.json)
# ⚠️ Directory is mcp-tools/ (NOT mcp-tokens/) — per _get_token_dir() in mcp_oauth.py
```

**Fix:** Re-authenticate once:
```bash
hermes mcp login <server-name>
# Or copy the token file from the source distro's backup
```

---

### 🟡 #5 — Playwright System Dependencies Missing

**Symptom:** `playwright-mcp` or `browser-tools-mcp` fails. Logs mention missing `.so` libraries or "Failed to launch browser."

**Why:** Playwright/Chromium needs ~30 system libraries that Fedora minimal doesn't install.

**Check:**
```bash
npx playwright install --dry-run 2>&1 | head -5
# If it lists missing deps, install them
```

**Fix (Fedora):**
```bash
sudo dnf install -y \
  libnss3 libnspr4 atk at-spi2-atk cups-libs libdrm \
  dbus-libs libxkbcommon libXcomposite libXdamage libXfixes \
  libXrandr mesa-libgbm pango cairo alsa-lib
npx playwright install chromium
```

---

### 🟡 #6 — Python MCP Servers with Broken venv Path

**Symptom:** Python-based MCP servers fail with `ModuleNotFoundError` or `No such file or directory`.

**Why:** The MCP server's `command` field points to a Python binary that doesn't exist on the target distro. The snapshot preserved the old venv path.

**Check:**
```bash
# Find all Python-based MCP servers in config
grep -B2 'command:.*python' ~/.prometeo/config.yaml
# For each one, verify the python path exists
```

**Fix:** Rewrite the `command` field to point to the target's venv Python:
```yaml
command: /home/prometeo_assistant/.prometeo/venv/bin/python
# NOT /home/prometeo/Aether-Agents/home/.venv-hermes/bin/python
```

---

## Quick One-Shot Diagnostic Script

Run this in the target distro to get a full health report:

```bash
#!/bin/bash
echo "=== MCP Post-Migration Health Check ==="
echo ""

echo "0a. hermes in PATH:"
which hermes 2>/dev/null && hermes --version 2>/dev/null || echo "  ❌ MISSING — create ~/.local/bin/hermes wrapper"
echo ""

echo "0b. HERMES_HOME:"
echo "  HERMES_HOME=${HERMES_HOME:-(empty)}" && [ -n "$HERMES_HOME" ] || echo "  ❌ NOT SET — add to ~/.bashrc + systemd Environment"
echo ""

echo "0c. systemd user dir:"
[ -d ~/.config/systemd/user/ ] && echo "  ✓ exists" || echo "  ❌ MISSING — create ~/.config/systemd/user/"
echo ""

echo "0d. gateway_state.json:"
if [ -f ~/.prometeo/gateway_state.json ]; then
  python3 -c "import sys,json; d=json.load(open('$HOME/.prometeo/gateway_state.json')); print(f'  PID:{d.get(\"pid\",\"?\")} State:{d.get(\"gateway_state\",\"?\")}')" 2>/dev/null || echo "  ⚠️  unreadable"
else
  echo "  (no file — OK, will be regenerated)"
fi
echo ""

echo "1. Node.js:"
which node 2>/dev/null && node --version || echo "  ❌ MISSING — npx MCPs will fail"
echo ""

echo "2. systemd PATH:"
systemctl --user show hermes-gateway-prometeo.service 2>/dev/null | grep Environment || echo "  ⚠️  No Environment set — may need PATH override"
echo ""

echo "3. Config paths to /home/:"
grep -n '/home/' ~/.prometeo/config.yaml 2>/dev/null | grep -v '^#' | head -10 || echo "  ⚠️  config.yaml not found"
echo ""

echo "4. MCP tokens:"
ls ~/.prometeo/mcp-tools/ 2>/dev/null || echo "  ⚠️  No mcp-tools/ directory — OAuth will re-prompt (NOT mcp-tokens/)"
echo ""

echo "5. Playwright deps:"
ldconfig -p 2>/dev/null | grep -c libnss3 || echo "  ⚠️  libnss3 not found — Playwright needs system deps"
echo ""

echo "6. Service status:"
systemctl --user status hermes-gateway-prometeo.service 2>/dev/null | head -5 || echo "  ❌ Service not found"
echo ""

echo "=== Done ==="
```

Save as `~/.local/bin/mcp-health-check` and run after every migration.
