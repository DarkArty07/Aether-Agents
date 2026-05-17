# Hermes Agent: pip Installation & Migration Guide

## v0.14.0 Changes (2026-05-16)

Hermes Agent v0.14.0 is the first release available on PyPI via `pip install hermes-agent`. Key changes affecting installation:

- **Wheel includes Ink TUI bundle and shell launcher** — no separate build step needed
- **Lazy dependency installation** — heavy backends (Slack, Matrix, voice/TTS, image-gen) auto-install on first use
- **Cold start ~19s faster** — fewer packages loaded at startup
- **Tiered install fallback** — if a wheel fails on your platform, falls back through compatibility tiers
- **Supply-chain advisory** — scans for unsafe versions during install

## Migration: Git Clone → pip Install

### Current Setup (Pre-Migration)

```
~/.local/bin/aether      → wrapper: HERMES_HOME=~/Aether-Agents/home exec ~/.hermes/hermes-agent/venv/bin/hermes -p orchestrator
~/.local/bin/hermes      → same wrapper, different name
~/.hermes/hermes-agent/  → git clone with Python 3.11 venv
~/.hermes/               → default HERMES_HOME (not used — overridden by wrapper)
~/Aether-Agents/home/    → active HERMES_HOME (config, profiles, skills, sessions)
~/Aether-Agents/home/profiles/orchestrator/ → active profile with SOUL.md, config.yaml, etc.
```

The wrapper scripts solve the "binary in ~/.hermes/hermes-agent/ but config in Aether-Agents/home/" split by setting `HERMES_HOME` and `-p orchestrator`.

### Target Setup (Post-Migration)

```
~/Aether-Agents/home/.venv-hermes/          → Python 3.11 venv with pip-installed hermes-agent
~/Aether-Agents/home/.venv-hermes/bin/hermes → hermes binary (from pip wheel)
~/.local/bin/aether                          → wrapper pointing to new venv
~/.hermes/hermes-agent/                      → REMOVED (no longer needed)
```

### Migration Steps

1. **Create clean venv with Python 3.11**
   ```bash
   cd ~/Aether-Agents/home
   python3.11 -m venv .venv-hermes
   source .venv-hermes/bin/activate
   ```

2. **Install hermes-agent via pip**
   ```bash
   pip install hermes-agent
   ```

3. **Verify installation**
   ```bash
   hermes --version
   which hermes  # should show ~/Aether-Agents/home/.venv-hermes/bin/hermes
   ```

4. **Update wrapper script** (`~/.local/bin/aether`)
   ```bash
   #!/bin/bash
   export HERMES_HOME=/home/prometeo/Aether-Agents/home
   exec /home/prometeo/Aether-Agents/home/.venv-hermes/bin/hermes -p orchestrator "$@"
   ```

5. **Update hermes wrapper** (`~/.local/bin/hermes`) — same content as aether if desired

6. **Test**: Run `aether` and verify profile loads, skills load, gateway works

7. **Update systemd service** — The gateway service file points to the old venv binary. Update:
   ```bash
   # Find the service file
   ls ~/.config/systemd/user/hermes-gateway-*.service
   # Edit the ExecStart line to point to new venv
   systemctl --user daemon-reload
   systemctl --user restart hermes-gateway-prometeo
   ```

8. **Remove git clone** (only after confirming everything works):
   ```bash
   rm -rf ~/.hermes/hermes-agent/
   ```

### Pitfalls

- **Python 3.14 vs 3.11**: System Python (linuxbrew) is 3.14. Hermes requires >=3.11 but 3.14 may have compatibility issues with C extensions. Use a dedicated 3.11 venv.
- **Systemd service path**: The gateway service file has an absolute path to the venv binary. After migration, this must point to the new `.venv-hermes/bin/hermes`.
- **`~/.hermes/` still exists**: Some files remain useful (sessions, logs, cache). Only remove `~/.hermes/hermes-agent/` (the git clone + venv), not the entire `~/.hermes/` directory.
- **Profile symlink**: `~/Aether-Agents/home/profiles/orchestrator/skins → ~/.hermes/skins` — verify this symlink still resolves after cleanup.
- **Lazy deps**: First use of heavy features (browser, voice, etc.) will trigger a pip install. Expect a delay on first invocation. If behind a proxy or with restricted network, this will fail silently.
- **updating**: `pip install --upgrade hermes-agent` replaces `cd ~/.hermes/hermes-agent && git pull && pip install -e .`. Much simpler.

### Key v0.14.0 Features (for reference)

| Feature | Detail |
|---------|--------|
| `pip install hermes-agent` | PyPI package, no git clone needed |
| xAI Grok | SuperGrok OAuth provider, grok-4.3 with 1M context |
| OpenAI-compatible proxy | OAuth providers → local endpoint for Codex/Aider/Cline |
| `x_search` | Native X/Twitter search tool (OAuth or API key) |
| Microsoft Teams | Full stack: Graph auth + webhook + pipeline + delivery |
| LINE + SimpleX Chat | 2 new platforms (22 total) |
| Native Windows beta | PowerShell installer, MinGit bundled |
| `/handoff` | Transfer live sessions between instances |
| `clarify` buttons | Native UI on Telegram and Discord |
| LSP diagnostics | Semantic diagnostics on every file write |
| Browser CDP | 180x faster |
| Cold start | ~19s faster launch |
| Debloated install | Heavy backends lazy-install on first use |

## ~/.hermes/ Audit: What to Keep and What to Remove

After migration, `~/.hermes/hermes-agent/` (the git clone + venv, 5.8 GB) can be safely deleted. The rest of `~/.hermes/` should be reviewed item by item:

| Path | Size | Status | Action |
|------|------|--------|--------|
| `hermes-agent/` | 5.8 GB | **DELETE** — git clone + venv, replaced by pip | `rm -rf ~/.hermes/hermes-agent/` |
| `.env` | 19 KB | Legacy (Aether has its own per-profile .env) | Backup, then delete after 1 week |
| `config.yaml` | 48 KB | Legacy (Aether profiles have their own) | Backup, then delete after 1 week |
| `state.db` | 68 KB | Legacy (Aether has 1.1 MB state.db) | Safe to delete |
| `skills/` | 9 MB | Partial — Aether has 24 skills, this has 22 (no aether-agents) | Keep as backup reference, then delete |
| `sessions/` | 0 | Empty | Delete |
| `memories/` | 0 | Empty | Delete |
| `bin/tirith` | 12 MB | Ships with hermes, regenerated | Delete (lazy-dep reinstalls) |
| `.olympus/` | 4 KB | Legacy DB (Aether has 17 MB one) | Delete |
| `channel_directory.json` | 399 B | Empty channels (Aether has real data) | Delete |
| `gateway_state.json` | 315 B | Stopped/April (Aether has active one) | Delete |
| `skins/` | 7 KB | `matrix.yaml` copied to Aether | Keep as reference, then delete |
| `cache/` | 9 MB | Regenerated | Delete |
| `logs/` | 28 KB | Regenerated | Delete |
| `audio_cache/`, `image_cache/` | 0 | Empty | Delete |
| `cron/`, `hooks/`, `pairing/`, `sandboxes/` | 0 | Empty | Delete |
| `profiles/prometeo` | 4 KB | Symlink to `~/.prometeo/profiles/prometeo` | **KEEP** — points to active gateway |

**CRITICAL**: `~/.prometeo/` (150 MB) is 100% live data — the gateway runs from this profile. Do NOT touch it during migration. It has its own `.env` (22 API keys), sessions (84), state.db (14 MB), and config.yaml. After migration, update its LD_LIBRARY_PATH separately.

## Dual-Profile Architecture

The Aether Agents setup uses two Hermes profiles simultaneously:

| Profile | Path | Purpose | Model | Interface |
|---------|------|---------|-------|-----------|
| **orchestrator** | `~/Aether-Agents/home/profiles/orchestrator/` | CLI/TUI, SOUL.md orchestration | glm-5.1 via opencode-go | `aether` command |
| **prometeo** | `~/.prometeo/profiles/prometeo/` | Gateway (Telegram, cron) | mimo-v2.5-pro via opencode-go | systemd service |

Both profiles share:
- The same hermes binary (currently `~/.hermes/hermes-agent/venv/bin/hermes`, will be `.venv-hermes/bin/hermes`)
- The same API keys (but different `.env` files)
- The same skills directory structure (but separate copies)

The orchestrator profile has the full SOUL.md with Daimon orchestration instructions. The prometeo profile has a shorter SOUL.md for gateway operation.

**After migration**: Both profiles must use the new venv binary. Update:
1. `~/.local/bin/aether` wrapper (for orchestrator)
2. Systemd service files (for prometeo gateway)
3. LD_LIBRARY_PATH in BOTH `.env` files

## CUDA / LD_LIBRARY_PATH Dependency

The orchestrator `.env` has a `LD_LIBRARY_PATH` with 8 nvidia library paths pointing to the old venv:

```
/home/prometeo/.hermes/hermes-agent/venv/lib/python3.11/site-packages/nvidia/cublas/lib:
/home/prometeo/.hermes/hermes-agent/venv/lib/python3.11/site-packages/nvidia/cudnn/lib:
/home/prometeo/.hermes/hermes-agent/venv/lib/python3.11/site-packages/nvidia/cufft/lib:
/home/prometeo/.hermes/hermes-agent/venv/lib/python3.11/site-packages/nvidia/curand/lib:
/home/prometeo/.hermes/hermes-agent/venv/lib/python3.11/site-packages/nvidia/cusolver/lib:
/home/prometeo/.hermes/hermes-agent/venv/lib/python3.11/site-packages/nvidia/cusparse/lib:
/home/prometeo/.hermes/hermes-agent/venv/lib/python3.11/site-packages/nvidia/cuda_runtime/lib:
/home/prometeo/.hermes/hermes-agent/venv/lib/python3.11/site-packages/nvidia/cuda_nvrtc/lib:
/home/prometeo/.hermes/hermes-agent/venv/lib/python3.11/site-packages/nvidia/nvjitlink/lib:
```

**After migration**: These 8 paths must be updated to point to the new venv:
```
/home/prometeo/Aether-Agents/home/.venv-hermes/lib/python3.11/site-packages/nvidia/cublas/lib:
... (same pattern, replacing .hermes/hermes-agent/venv with .venv-hermes)
```

This is needed for faster-whisper (STT) to use CUDA. Without it, STT falls back to CPU.

**Automation**: After `pip install hermes-agent`, install `faster-whisper` which pulls in the nvidia packages, then update `.env`:
```bash
source ~/Aether-Agents/home/.venv-hermes/bin/activate
pip install faster-whisper  # installs nvidia CUDA packages
# Then update .env with the new nvidia lib paths
```

## Systemd Service Files

Three service files reference the old venv binary and need updating:

1. **`hermes-gateway-prometeo.service`** — Active gateway (profile: prometeo)
   - ExecStart: `/home/prometeo/.hermes/hermes-agent/venv/bin/python -m hermes_cli.main --profile prometeo gateway run --replace`
   - WorkingDirectory: `/home/prometeo/.hermes/hermes-agent`
   - VIRTUAL_ENV: `/home/prometeo/.hermes/hermes-agent/venv`
   - HERMES_HOME: `/home/prometeo/.prometeo/profiles/prometeo`

2. **`hermes-gateway-hermes.service`** — Legacy gateway (profile: hermes)
   - Same ExecStart pattern, HERMES_HOME: `/home/prometeo/Aether-Agents/home/profiles/hermes`

3. **`hermes-gateway.service`** — Default gateway (no profile)
   - ExecStart: `/home/prometeo/.hermes/hermes-agent/venv/bin/python -m hermes_cli.main gateway run --replace`
   - HERMES_HOME: `/home/prometeo/.prometeo`

**After migration**: Change all ExecStart, WorkingDirectory, and VIRTUAL_ENV to point to `.venv-hermes`. The HERMES_HOME values remain the same.

## Updating After Migration

```bash
# Old way (git clone):
cd ~/.hermes/hermes-agent && git pull && pip install -e ".[all]"

# New way (pip):
source ~/Aether-Agents/home/.venv-hermes/bin/activate
pip install --upgrade hermes-agent
```

Or use the built-in update command:
```bash
hermes update   # auto-detects pip installation and uses pip
```