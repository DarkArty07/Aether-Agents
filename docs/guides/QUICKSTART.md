# Quickstart Guide

Get Aether Agents running in under five minutes.

## 1. Clone and Setup

```bash
git clone https://github.com/DarkArty07/Aether-Agents.git
cd Aether-Agents
bash scripts/setup.sh
```

`setup.sh` is idempotent — safe to re-run. It handles Python detection, venv creation, hermes-agent installation, config generation, and shell wrappers.

## 2. Configure API Key

Edit the orchestrator profile environment file and add at least one provider key:

```bash
nano home/.env
```

```
# Uncomment and set your key:
OPENAI_API_KEY=sk-...
# ANTHROPIC_API_KEY=sk-ant-...
```

## 3. Launch

**Restart your terminal first** — `setup.sh` updates your PATH and `HERMES_HOME`.

```bash
aether
```

Or run directly without the wrapper:

```bash
home/.venv-hermes/bin/hermes --profile orchestrator
```

## 4. Verify

On startup, Olympus discovers Daimon profiles. You should see something like:

```
[olympus] discovered: ariadna, athena, daedalus, etalides, hefesto, hermes
```

Quick smoke test:

```bash
make doctor
```

## 5. First Delegation

Talk to a Daimon right from the Hermes prompt:

```
> Talk to Hefesto about implementing a feature
```

Or use `delegate_task` in a session to hand work to a specific agent.

## 6. Gateway (Optional)

For an always-on background service:

```bash
bash scripts/start-gateway.sh start
# or:
make gateway ARGS=start
```

## 7. Next Steps

- **Full installation walkthrough:** [INSTALLATION.md](./INSTALLATION.md)
- **Configuration reference:** [CONFIGURATION.md](./CONFIGURATION.md)