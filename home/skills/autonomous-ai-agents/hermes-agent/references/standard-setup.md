# Standard Hermes-Agent Setup Pattern

## Context

When setting up a hermes-agent instance from scratch — whether on a fresh WSL distro, a new Linux machine, or after a pip install — the setup should follow the **standard documented pattern**: no wrapper scripts, no `-p` profile flag, just `HERMES_HOME` pointing to the data directory.

## The Pattern

```
~/.prometeo/
  ├── config.yaml          # Default profile config (at root)
  ├── .env                 # Secrets (API keys, tokens)
  ├── auth.json            # Auth state
  ├── profiles/
  │   ├── hefesto/         # Daimon profiles (child profiles)
  │   └── metis/
  ├── sessions/            # Runtime state
  ├── state.db
  └── logs/

~/.local/bin/hermes        # Hard copy of venv entry point (NOT symlink, NOT wrapper)
```

### Binary: PATH-Based Resolution (Preferred) or Hard Copy (Fallback)

**Option 1 (Preferred): PATH-based resolution.** Prepend the venv's `bin/` directory to `PATH` in `.bashrc`:

```bash
# In ~/.bashrc:
export PATH="/path/to/venv/bin:$PATH"
export HERMES_HOME="/path/to/data/dir"
```

The shell resolves `hermes` directly from the venv. No copies, no symlinks, no wrappers. When you `pip install --upgrade hermes-agent`, the new version is immediately available — no re-copy needed. **This is the recommended approach for Aether Agents.**

**Option 2 (Fallback): Hard copy to `~/.local/bin/`.** Use when PATH manipulation isn't desired:

```bash
cp /path/to/venv/bin/hermes ~/.local/bin/hermes
```

**What NOT to do:**

```bash
# ❌ WRONG — wrapper shell script that unsets env vars then execs:
/bin/sh wrapper-script  # 128 bytes ← DELETE THIS

# ⚠️ AVOID — symlink (breaks on WSL cross-filesystem, becomes dangling on venv recreate):
ln -s /path/to/venv/bin/hermes ~/.local/bin/hermes  # ← AVOID
```

**Why PATH-based is preferred over hard copy:**
- No maintenance — upgrades flow automatically through PATH
- No stale binary risk after `pip install --upgrade`
- Single source of truth — `.bashrc` always points to the active venv
- A hard copy at `~/.local/bin/hermes` becomes stale after upgrades (old version cached)

**Why hard copy over symlink (for Option 2):**
- The hard copy is ~350 bytes — negligible cost for guaranteed stability
- Symlinks break across WSL filesystem boundaries (Windows ↔ Linux)
- Symlinks become dangling if the venv is recreated or moved
- The shebang inside the script already points to the correct Python in the venv

**How to verify which resolution method is in use:**

```bash
# PATH-based (Option 1):
which hermes
# → /home/user/Aether-Agents/home/.venv-hermes/bin/hermes  (PATH resolution)

# Hard copy (Option 2):
which hermes
# → /home/user/.local/bin/hermes  (static copy)

# Check if it's a wrapper (shell script) vs binary:
file $(which hermes)
# Wrapper: "Bourne-Again shell script, ASCII text executable" — DELETE THIS
# Binary/entry: "Python script text executable, ASCII text" — CORRECT

# For hard copy: verify it's not stale after an upgrade
$(which hermes) --version
# Compare with venv version:
/path/to/venv/bin/hermes --version
# If different → hard copy is stale, re-copy or switch to PATH-based
```

### HERMES_HOME: Data Directory

`HERMES_HOME` should point to the **data directory** that contains `config.yaml`, `.env`, `profiles/`, `sessions/`, etc. — NOT to the venv or the pip installation directory.

```bash
# In ~/.bashrc or equivalent:
export HERMES_HOME="$HOME/.prometeo"
```

When `HERMES_HOME` is set to a custom path, the framework uses that directory directly as the **default profile** — no `-p` flag needed. All runtime files live at `$HERMES_HOME/`:
- `$HERMES_HOME/config.yaml` — configuration
- `$HERMES_HOME/.env` — secrets
- `$HERMES_HOME/auth.json` — auth state
- `$HERMES_HOME/sessions/` — session persistence
- `$HERMES_HOME/profiles/<daimon>/` — Daimon child profiles

**How to verify HERMES_HOME is correct:**

```bash
HERMES_HOME=/home/user/.prometeo /home/user/.local/bin/hermes --version
# Should print: Hermes Agent vX.Y.Z ...

HERMES_HOME=/home/user/.prometeo /home/user/.local/bin/hermes config show | head -20
# Should show:
#   Config:   /home/user/.prometeo/config.yaml
#   Secrets:  /home/user/.prometeo/.env
```

### Config at Default Profile Root

The `config.yaml` must exist at `$HERMES_HOME/config.yaml` (directly, not inside a `profiles/<name>/` subdirectory). This is the **default profile** — used when no `-p` flag is given.

```bash
# If config exists only at profiles/prometeo/config.yaml, copy it to root:
cp "$HERMES_HOME/profiles/prometeo/config.yaml" "$HERMES_HOME/config.yaml"
```

**Do NOT delete** the original profile-specific config — it may be needed for gateway systemd units or other references.

### Verification Checklist

After setup, run these two commands to verify:

```bash
# 1. Version check
HERMES_HOME=/home/user/.prometeo /home/user/.local/bin/hermes --version
# Expected: "Hermes Agent vX.Y.Z (YYYY.M.D)" — no "command not found" or wrapper errors

# 2. Config path check
HERMES_HOME=/home/user/.prometeo /home/user/.local/bin/hermes config show | head -20
# Expected:
#   Config:   /home/user/.prometeo/config.yaml  ← should be root, not a subdirectory
#   Secrets:  /home/user/.prometeo/.env         ← should be in same dir as config
```

If `hermes --version` fails, stop and diagnose — do NOT proceed with further setup until the binary resolves correctly.

## Prerequisite: WSL Interop Must Work

When diagnosing or configuring a hermes-agent instance on another WSL distro from within WSL, the `wsl.exe -d <DISTRO>` command must be functional. If it returns "command not found" from within the Ubuntu WSL shell, the WSL interop handler is missing.

**Test interop:**
```bash
wsl.exe -d FedoraLinux-43 -- bash -c 'echo ok'
# Should print: ok
# Failure means: binfmt_misc handler for Windows PE executables is missing
```

**Fix (one-time, does not persist across WSL restart):**
```bash
sudo sh -c 'echo ":WSLInterop:M::MZ::/init:PF" > /proc/sys/fs/binfmt_misc/register'
# Verify: wsl.exe -d FedoraLinux-43 -- bash -c 'echo ok'
```

The non-persistent warning `wsl: Failed to translate '\\wsl.localhost\\Ubuntu\\home\\...'` is cosmetic — it appears on every `wsl.exe -d` call but does not affect command execution.

## Worked Example: Setting Up on a Fedora WSL Instance

Target: WSL distro `FedoraLinux-43`, user `prometeo_assistant`, hermes data at `~/.prometeo`.

Initial (broken) state:
```
~/.local/bin/hermes            → WRAPPER (128 B, unsets PYTHONPATH then execs)
~/.hermes/hermes-agent/venv/bin/hermes  → real binary (343 B, pip entry point)
~/.prometeo/profiles/prometeo/config.yaml → config exists but in subdirectory
~/.prometeo/config.yaml        → DOES NOT EXIST
HERMES_HOME                    → NOT SET in .bashrc
```

Step-by-step fix:

```bash
# 1. Delete wrapper → create hard copy
rm /home/prometeo_assistant/.local/bin/hermes
cp /home/prometeo_assistant/.prometeo/venv/bin/hermes /home/prometeo_assistant/.local/bin/hermes

# 1b. Install MCP extras (REQUIRED — base install does NOT include MCP SDK)
/home/prometeo_assistant/.prometeo/venv/bin/pip install 'hermes-agent[mcp]'

# 2. Set HERMES_HOME in .bashrc (idempotent)
grep -q "HERMES_HOME" /home/prometeo_assistant/.bashrc || \
  echo 'export HERMES_HOME="$HOME/.prometeo"' >> /home/prometeo_assistant/.bashrc

# 3. Copy config to default profile root
cp /home/prometeo_assistant/.prometeo/profiles/prometeo/config.yaml /home/prometeo_assistant/.prometeo/config.yaml

# 4. Verify
HERMES_HOME=/home/prometeo_assistant/.prometeo /home/prometeo_assistant/.local/bin/hermes --version
HERMES_HOME=/home/prometeo_assistant/.prometeo /home/prometeo_assistant/.local/bin/hermes config show | head -20
```

Expected verifications:
- `hermes --version` → `Hermes Agent v0.15.1 (2026.5.29)`
- `config show` → Config: `/home/prometeo_assistant/.prometeo/config.yaml`
- `config show` → Secrets: `/home/prometeo_assistant/.prometeo/.env`

### pip install Warning: "not officially supported"

When installing via `pip install hermes-agent`, pip may show:
```
⚠ pip install not officially supported — exists for reasons other than user install; expect instability
```

**This warning is cosmetic and safe to ignore in a managed venv setup.** The hermes-agent creators prefer the `curl -fsSL ... | bash` installer (which handles system deps like ffmpeg, Node.js, CUDA) over raw `pip install`. However, when using a proper venv with manual dependency management (`hermes-agent[mcp]`, graphifyy, olympus-mcp), pip install is the correct approach. The venv isolates hermes-agent and its dependencies, and `.bashrc` handles PATH and HERMES_HOME. The warning refers to bare `pip install` without a venv on a system lacking the system dependencies — not to our managed venv setup.

**Key difference:** pip install doesn't install ffmpeg, Node.js, ripgrep, or CUDA libs — those need manual installation. The curl installer bundles all of this. In a venv setup, those are pre-installed system-wide.

### setup.sh Step 8 Is Deprecated

The Aether Agents `scripts/setup.sh` Step 8 created wrapper scripts in `~/.local/bin/`. This is deprecated as of v0.16.0 — Step 8 is commented out with `# DEPRECATED: wrappers no longer needed — PATH resolves to venv binary directly`. The `.bashrc` PATH entry handles binary resolution.

## Anti-Patterns

1. **Wrapper that unsets PYTHONPATH/PYTHONHOME** — The standard pip entry point handles its own environment. Wrappers that strip environment variables before `exec` can silently break module resolution. Hard copy instead.

2. **Symlink to venv binary** — Symlinks break across WSL filesystem boundaries and become dangling on venv recreation. Hard copy is ~350 bytes and survives rebuilds.

3. **Config only in `profiles/<name>/`** — This forces the user to always specify `-p <name>` or set systemd unit paths with the subdirectory. The default profile pattern (config at `$HERMES_HOME/config.yaml`) is simpler and is the documented standard.

4. **`HERMES_HOME` pointing to the venv directory** — `HERMES_HOME` is the DATA directory, not the installation directory. The venv lives separately (typically at `~/.hermes/hermes-agent/venv/` or in the project's own `.venv-hermes`).

5. **Applying setup commands via imprecise cross-distro execution** — When running commands on another WSL distro via `wsl.exe -d <DISTRO> -- bash -c '...'`, always use absolute paths. The tilde `~` may not resolve correctly. Also be aware that `wsl: Failed to translate` warnings are cosmetic — the command still runs.

6. **`pip install hermes-agent` without `[mcp]` extra** — The base package does NOT include the MCP Python SDK. All MCP servers will fail silently (no errors in journal, `hermes mcp list` still shows "✓ enabled"). Always run `pip install 'hermes-agent[mcp]'` after the base install. Verify with `python -c 'import mcp'`. See `references/mcp-server-configuration.md` §Prerequisites for the full diagnostic pattern.

7. **`.env` as symlink to another instance** — If `home/.env` is a symlink pointing to another hermes-agent instance's `.env` (e.g., `/home/prometeo/.hermes/.env`), the file breaks when the target instance isn't running or is on a different WSL distro. Replace symlinks with real file copies: `cp target .env.real && rm .env && mv .env.real .env`. Verify with `ls -la .env` — must NOT show `->`.

8. **`make clean` destroys venv** — The Aether-Agents Makefile target `clean` runs `rm -rf home/.venv-hermes/`, which destroys the entire virtual environment including hermes-agent, graphifyy, olympus-mcp, and the `[mcp]` extra. Recovery requires running `scripts/setup.sh`. This is a foot-gun for anyone expecting `make clean` to only remove `__pycache__` and build artifacts.

9. **`LD_LIBRARY_PATH` contamination from other instances** — If `.bashrc` contains `LD_LIBRARY_PATH` pointing to another hermes-agent installation's venv (e.g., `~/.hermes/hermes-agent/venv/lib/.../nvidia/`), it contaminates NVIDIA library loading for the current instance. Remove cross-instance `LD_LIBRARY_PATH` entries from `.bashrc`. Each instance should manage its own library paths.

## Protecting config.yaml from `hermes config set` Overwrites

`hermes config set <key> <value>` and `hermes doctor` rewrite the ENTIRE config.yaml via `yaml.safe_dump`, which can drop custom blocks (like `mcp_servers.graphify`). To protect config.yaml:

1. **Destrack from git** — `git rm --cached home/config.yaml` combined with `.gitignore` prevents accidental commits that expose API keys, and prevents git from overwriting local changes. Verify with `git ls-files home/config.yaml` (should be empty).

2. **Never use `hermes config set`** — Edit `config.yaml` manually in a text editor. The CLI command rewrites the entire file.

3. **Optional: read-only** — `chmod 444 home/config.yaml` makes `hermes config set` fail with Permission Denied. Remember to `chmod 644` before manual edits.
