# Installation Guide

Complete instructions for installing Aether Agents from scratch.

---

## 1. Prerequisites

| Requirement       | Details                                |
|-------------------|----------------------------------------|
| Operating system  | Linux, macOS, or WSL2 (Windows)        |
| Python            | 3.11 or newer                          |
| git               | Any recent version                     |
| curl              | For the hermes-agent installer         |
| API key           | OpenAI, Anthropic, or compatible provider |

Verify Python:

```bash
python --version   # must show 3.11+
```

---

## 2. Install hermes-agent

### Option A — Curl installer (recommended)

```bash
curl -fsSL https://raw.githubusercontent.com/NousResearch/hermes-agent/main/scripts/install.sh | bash
```

This downloads hermes-agent and makes the `hermes` CLI available in your `PATH`.

### Option B — From source

If you prefer to build from source or need a specific branch:

```bash
git clone https://github.com/NousResearch/hermes-agent.git
cd hermes-agent
bash scripts/setup-hermes.sh
```

Verify the installation:

```bash
hermes --version
```

---

## 3. Clone Aether Agents

```bash
git clone https://github.com/DarkArty07/Aether-Agents.git
cd Aether-Agents
```

The default branch is `dev`.

---

## 4. Create Virtual Environment and Install Olympus

Olympus is the MCP server that connects all Daimons. Install it in editable mode:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e ./src/olympus
```

---

## 5. Run configure.sh

`configure.sh` performs one-time project setup:

- Detects the absolute path to your Python interpreter inside `.venv`.
- Substitutes that path into every Daimon profile's `config.yaml` (`launch_command` field).
- Sets the project root path in the root `home/config.yaml`.

```bash
bash scripts/configure.sh
```

### Override the Python path

If you want to use a specific Python binary instead of the auto-detected one:

```bash
HERMES_PYTHON=/usr/bin/python3.12 bash scripts/configure.sh
```

---

## 6. Set HERMES_HOME Permanently

`HERMES_HOME` tells hermes-agent where to find the Aether Agents configuration tree. Add it to your shell profile so it persists:

```bash
# For Bash users
echo 'export HERMES_HOME="$HOME/Aether-Agents/home"' >> ~/.bashrc
source ~/.bashrc

# For Zsh users
echo 'export HERMES_HOME="$HOME/Aether-Agents/home"' >> ~/.zshrc
source ~/.zshrc
```

The `home/` directory structure:

```
home/
├── config.yaml          # Root configuration (model, toolsets, MCP servers, …)
├── SOUL.md              # Shared agent identity
├── active_profile       # Currently active profile name
└── profiles/
    ├── hermes/          # Orchestrator
    ├── ariadna/         # Project Manager
    ├── hefesto/         # Developer
    ├── etalides/        # Researcher
    ├── athena/          # Security
    └── daedalus/        # UX
```

Each profile directory contains its own `config.yaml`, `SOUL.md`, `.env`, and optional `skills/` folder.

---

## 7. Configure API Keys

Every Daimon profile ships an `.env.example` file. Copy it and fill in at least one provider key:

```bash
# Hermes (orchestrator) — required for first run
cp home/profiles/hermes/.env.example home/profiles/hermes/.env
```

Edit the `.env` file:

```
OPENAI_API_KEY=sk-...
# or
ANTHROPIC_API_KEY=sk-ant-...
```

Repeat for other profiles if you want them to use different models or keys:

```bash
for profile in ariadna hefesto etalides athena daedalus; do
  cp "home/profiles/${profile}/.env.example" "home/profiles/${profile}/.env"
done
```

> If a profile has no `.env`, it inherits the root model configuration from `home/config.yaml`.

---

## 8. Verify the Ecosystem

Run the built-in verification script:

```bash
bash scripts/start.sh
```

This script checks that:

1. The virtual environment is active.
2. `hermes` CLI is on `PATH`.
3. `HERMES_HOME` points to the correct directory.
4. Olympus MCP server can start and discover all six Daimon profiles.

A successful run ends with a summary table of discovered Daimons.

---

## 9. First Run

Launch the orchestrator:

```bash
hermes --profile hermes
```

Hermes connects to Olympus over the ACP protocol and registers the other five Daimons as callable agents. You can now issue tasks and Hermes will coordinate delegation automatically.

To launch a specific Daimon directly (for testing):

```bash
hermes --profile hefesto
```

---

## 10. Common Install Issues

| Symptom | Cause | Fix |
|---------|-------|-----|
| `hermes: command not found` | hermes-agent not on PATH | Re-run the hermes installer or open a new terminal |
| `ModuleNotFoundError: olympus` | Olympus not installed in venv | Run `pip install -e ./src/olympus` with venv active |
| `HERMES_HOME is not set` | Environment variable missing | Add the export to your shell profile (step 6) |
| Olympus does not discover Daimons | `configure.sh` not run | Run `bash scripts/configure.sh` again |
| Python version errors | Python < 3.11 | Upgrade Python and recreate the venv |

For more in-depth troubleshooting, see [TROUBLESHOOTING.md](./TROUBLESHOOTING.md).

---

## Quick Reference

| Step | Command |
|------|---------|
| Install hermes-agent | `curl -fsSL https://raw.githubusercontent.com/NousResearch/hermes-agent/main/scripts/install.sh \| bash` |
| Clone repo | `git clone https://github.com/DarkArty07/Aether-Agents.git` |
| Create venv | `python -m venv .venv && source .venv/bin/activate` |
| Install Olympus | `pip install -e ./src/olympus` |
| Configure paths | `bash scripts/configure.sh` |
| Set HERMES_HOME | `export HERMES_HOME="$HOME/Aether-Agents/home"` |
| Verify | `bash scripts/start.sh` |
| Launch | `hermes --profile hermes` |

---

**Next:** [CONFIGURATION.md](./CONFIGURATION.md) · [QUICKSTART.md](./QUICKSTART.md) · [TROUBLESHOOTING.md](./TROUBLESHOOTING.md)
