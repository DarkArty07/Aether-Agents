# Quickstart Guide

Get Aether Agents running in under five minutes.

## 1. Prerequisites

| Requirement | Minimum Version |
|-------------|-----------------|
| Python      | 3.11+           |
| git         | Any recent      |
| hermes-agent| Latest          |

Install hermes-agent:

```bash
curl -fsSL https://raw.githubusercontent.com/NousResearch/hermes-agent/main/scripts/install.sh | bash
```

## 2. Clone and Install

```bash
git clone https://github.com/DarkArty07/Aether-Agents.git
cd Aether-Agents
python -m venv .venv
source .venv/bin/activate
pip install -e ./src/olympus
bash scripts/configure.sh
```

`configure.sh` is a one-time setup that substitutes absolute paths into config files so every Daimon profile can find the correct Python interpreter and project root.

## 3. Configure API Key

Copy the example environment file into the Hermes profile and add your key:

```bash
cp home/profiles/hermes/.env.example home/profiles/hermes/.env
```

Edit `home/profiles/hermes/.env` and set at least one provider API key:

```
OPENAI_API_KEY=sk-...
# or
ANTHROPIC_API_KEY=sk-ant-...
```

## 4. Start

```bash
export HERMES_HOME=~/Aether-Agents/home
hermes --profile hermes
```

> Tip: add the `HERMES_HOME` export to your `~/.bashrc` or `~/.zshrc` so it persists across sessions.

## 5. Verify

When Hermes starts it connects to the Olympus MCP server. You should see log output confirming that Olympus discovered the six Daimon profiles:

```
[olympus] discovered: ariadna, athena, daedalus, etalides, hefesto, hermes
```

If all six appear, the system is ready. You can also run a quick smoke test:

```bash
bash scripts/start.sh
```

## 6. Next Steps

- **Full installation walkthrough:** [INSTALLATION.md](./INSTALLATION.md)
- **Configuration reference:** [CONFIGURATION.md](./CONFIGURATION.md)
- **Troubleshooting:** [TROUBLESHOOTING.md](./TROUBLESHOOTING.md)
