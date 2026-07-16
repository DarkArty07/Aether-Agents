# Installation Guide — Aether Agents v0.18.1

Complete instructions for installing and configuring Aether Agents.

---

## 1. Prerequisites

| Requirement | Details |
|-------------|---------|
| **OS** | Linux, macOS, or WSL2 (Windows) |
| **Python** | 3.11 or newer |
| **Git** | Any recent version |
| **NVIDIA GPU** | Optional — required for local STT via faster-whisper |

Verify Python:

```bash
python3 --version   # must show 3.11+
```

On Ubuntu/Debian, install Python and venv support:

```bash
sudo apt install python3.12 python3.12-venv python3.12-dev
```

On macOS:

```bash
brew install python@3.12
```

---

## 2. Quick Install (Recommended)

```bash
git clone https://github.com/DarkArty07/Aether-Agents.git
cd Aether-Agents
bash scripts/setup.sh
```

`setup.sh` automates the entire installation:

1. **Checks Python** — verifies Python 3.11+ is available
2. **Creates venv** — at `home/.venv-hermes/` inside the project
3. **Installs hermes-agent** — from PyPI via `pip install hermes-agent`
4. **Installs olympus_v3** — editable `pip install -e .` from `pyproject.toml`
5. **Installs CUDA extras** — if `nvidia-smi` is detected, installs faster-whisper
6. **Generates config.yaml** — copies `.yaml.template` → `config.yaml` per profile, substituting `__AETHER_ROOT__` and `__HERMES_PYTHON__` with real paths
7. **Creates .env files** — copies `.env.example` → `.env` per profile (skips existing)
8. **Creates wrapper scripts** — `aether` and `hermes` in `~/.local/bin/`
9. **Sets HERMES_HOME** — adds export to `~/.bashrc`
10. **Updates .gitignore** — adds `home/.venv-hermes/`

The script is **idempotent** — safe to re-run. It preserves existing `config.yaml` and `.env` files.

After setup, restart your terminal (or run `source ~/.bashrc`) and start Aether:

```bash
aether
```

---

## 3. Manual Install (Step-by-Step)

If you prefer not to use `setup.sh`, follow these steps:

### 3.1 Clone the repository

```bash
git clone https://github.com/DarkArty07/Aether-Agents.git
cd Aether-Agents
```

### 3.2 Create and activate the virtual environment

```bash
python3 -m venv home/.venv-hermes
source home/.venv-hermes/bin/activate
```

### 3.3 Install packages

```bash
pip install hermes-agent
pip install -e .
```

> The `pip install -e .` installs the `olympus_v3` MCP server from `src/olympus_v3/` in editable mode using the project's `pyproject.toml`.

### 3.4 Generate config.yaml for each profile

For every profile that has a `config.yaml.template`:

```bash
for template in home/profiles/*/config.yaml.template; do
    config="${template%.template}"
    cp "$template" "$config"
    sed -i "s|__AETHER_ROOT__|$(pwd)|g" "$config"
    sed -i "s|__HERMES_PYTHON__|$(pwd)/home/.venv-hermes/bin/python|g" "$config"
done
```

> On macOS, use `sed -i ''` instead of `sed -i`.

### 3.5 Create .env files

For every profile that has an `.env.example`:

```bash
for example in home/profiles/*/.env.example; do
    envfile="${example%.example}"
    [ -f "$envfile" ] || cp "$example" "$envfile"
done
```

### 3.6 Set HERMES_HOME permanently

Add to your shell profile (`~/.bashrc` or `~/.zshrc`):

```bash
export HERMES_HOME="/path/to/Aether-Agents/home"
```

Then reload:

```bash
source ~/.bashrc   # or source ~/.zshrc
```

---

## 4. WSL Setup (Windows Users)

Aether Agents runs on **WSL2 only** — WSL1 does not support the required filesystem and networking features.

- `setup.sh` auto-detects WSL and adjusts output messages accordingly.
- **NVIDIA GPU in WSL**: install the CUDA toolkit inside your WSL distribution for faster-whisper STT support.
- **Paths**: Windows paths (`C:\Users\...`) do not work in `config.yaml`. Always use Linux paths (`/home/<user>/...`).
- **Permissions**: if you encounter `Permission denied` on scripts, run:

```bash
chmod +x scripts/*.sh
```

---

## 5. GPU / CUDA Setup (Optional — faster-whisper STT)

### 5.1 Check for NVIDIA GPU

```bash
nvidia-smi
```

### 5.2 If GPU is available

Install CUDA-accelerated STT packages inside the venv:

```bash
source home/.venv-hermes/bin/activate
pip install faster-whisper nvidia-cublas-cu12
```

Then in each profile's `config.yaml`, set:

```yaml
stt:
  enabled: true
  provider: local
  local:
    model: medium
    language: en
```

### 5.3 If no GPU

Use cloud-based STT (OpenAI Whisper API). In `config.yaml`:

```yaml
stt:
  enabled: true
  provider: openai
  openai:
    model: whisper-1
```

This requires `OPENAI_API_KEY` set in the profile's `.env` file.

---

## 6. Configuration

### 6.1 API Keys

Edit the `.env` file in each profile to set your API keys. At minimum, configure the orchestrator:

```bash
nano home/.env
```

Available providers (uncomment and fill in the ones you need):

| Variable | Provider |
|----------|----------|
| `OPENAI_API_KEY` | OpenAI |
| `ANTHROPIC_API_KEY` | Anthropic |
| `OPENROUTER_API_KEY` | OpenRouter (aggregates multiple providers) |
| `DEEPSEEK_API_KEY` | DeepSeek |
| `GLM_API_KEY` | Zhipu AI (GLM models) |
| `MOONSHOT_API_KEY` | Moonshot (Kimi) |
| `MINIMAX_API_KEY` | MiniMax |
| `AIPRIMETECH_API_KEY` | AI Prime Tech |

See each profile's `.env.example` for the full list.

### 6.2 config.yaml Templates

Each profile ships a `config.yaml.template` containing two placeholders:

- `__AETHER_ROOT__` — replaced with the absolute path to the Aether-Agents repo
- `__HERMES_PYTHON__` — replaced with the venv Python path (`<repo>/home/.venv-hermes/bin/python`)

`setup.sh` handles substitution automatically. For manual install, see [§3.4](#34-generate-configyaml-for-each-profile).

For the full configuration reference, see [CONFIGURATION.md](./CONFIGURATION.md).

---

## 7. Updating

To update Aether Agents to the latest version:

```bash
bash scripts/update.sh
```

`update.sh` performs:

1. **git pull** — fetches latest changes (stashes local changes if needed)
2. **pip upgrade hermes-agent** — updates to the latest PyPI release
3. **pip install -e .** — reinstalls olympus_v3 in editable mode
4. **Checks config.yaml** — regenerates only if placeholders are still unresolved

It **preserves** your local `config.yaml`, `.env` files, and the venv. It does **not** overwrite `config.yaml` unless it contains unresolved `__AETHER_ROOT__` or `__HERMES_PYTHON__` placeholders.

To force regeneration of all config files from templates:

```bash
bash scripts/update.sh --regen-config
```

---

## 8. Troubleshooting

| Symptom | Cause | Fix |
|---------|-------|-----|
| `aether: command not found` | Wrapper script not on PATH | Restart terminal or run `source ~/.bashrc` |
| `python3: command not found` | Python not installed | Install Python 3.11+ (`sudo apt install python3.12` on Ubuntu) |
| `ModuleNotFoundError: olympus_v3` | Olympus not installed in venv | Run `bash scripts/setup.sh` again |
| venv creation fails | `python3-venv` package missing | `sudo apt install python3-venv` (Ubuntu/Debian) |
| `nvidia-smi not found` | No NVIDIA drivers installed | Install CUDA toolkit or use cloud STT (`provider: openai`) |
| `pip install` fails (SSL errors) | Corporate proxy or cert issues | `pip install --trusted-host pypi.org --trusted-host files.pythonhosted.org hermes-agent` |
| Hermes can't find Daimons | `HERMES_HOME` not set | `setup.sh` adds it to `~/.bashrc`; restart terminal |
| `Permission denied` on scripts | No execute permission | `chmod +x scripts/*.sh` |
| `hermes` works but `aether` doesn't | Missing wrapper script | Run `bash scripts/setup.sh` to create the `aether` wrapper |

For more help, see [QUICKSTART.md](./QUICKSTART.md).

---

## 9. Upgrading from v0.7.x

v0.8.0 introduces significant structural changes. Key migrations:

| v0.7.x (Old) | v0.8.0 (New) |
|---------------|---------------|
| `~/.hermes/hermes-agent/` venv | `home/.venv-hermes/` inside project |
| `~/.local/bin/hermes` symlink | `~/.local/bin/aether` and `~/.local/bin/hermes` wrapper scripts |
| `HERMES_HOME=~/.hermes/hermes-agent/home` | `HERMES_HOME=<project>/home/` |
| `configure.sh` (removed in v0.8.1) | `setup.sh` (full automation) |
| `pip install -e .` (project root) | `pip install hermes-agent` + `pip install -e .` (olympus_v3) |

To upgrade:

```bash
cd Aether-Agents
git pull
bash scripts/setup.sh
```

`setup.sh` is idempotent and will clean up old artifacts. It overwrites the wrapper scripts in `~/.local/bin/` and updates `HERMES_HOME` in your shell profile.

> **Note**: If you had a venv at `~/.hermes/hermes-agent/`, you can safely remove it after `setup.sh` completes — the new venv lives at `home/.venv-hermes/` inside the project.

For detailed migration instructions, see the pip-installation migration guide in the hermes-agent documentation.

**Next:** [CONFIGURATION.md](./CONFIGURATION.md) · [QUICKSTART.md](./QUICKSTART.md)