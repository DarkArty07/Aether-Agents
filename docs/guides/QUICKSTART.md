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
HERMES_HOME="$PWD/home" home/.venv-hermes/bin/hermes
```

## 4. Verify

Verify Hermes, the root template, all six profile templates, and the absence of a native runtime plugin:

```bash
make doctor
```

The v0.22.0 candidate does not expose a multi-agent execution runtime. Specialist profiles are installed as product contracts, but no process discovers or spawns them until the Hermes-led Orca path is accepted.

## 5. Current execution boundary

Hermes performs bounded work directly. Do not use `talk_to`, `delegate_task`, a
profile wrapper, or a restored compatibility shim to simulate specialist
execution. The target is one Hermes-supervised Orca Run with independent Tasks,
worker-to-worker messages, and child worktrees for potentially conflicting
writers; that target is not activated in this candidate.

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