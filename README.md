# Aether Agents

[![Version](https://img.shields.io/badge/version-0.8.0-blue)](CHANGELOG.md)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Tests](https://github.com/DarkArty07/Aether-Agents/actions/workflows/test.yml/badge.svg)](https://github.com/DarkArty07/Aether-Agents/actions/workflows/test.yml)
[![Python 3.11+](https://img.shields.io/badge/python-3.11%2B-blue.svg)](https://www.python.org/downloads/)
[![PRs Welcome](https://img.shields.io/badge/PRs-welcome-brightgreen.svg)](CONTRIBUTING.md)

A **provider-agnostic** 5-phase agent ecosystem: **IDEA → RESEARCH → DESIGN → PLAN → CODE**. Hermes orchestrates 6 specialized Daimons through Olympus v3, an MCP server with ACP sessions and plugin-powered observability.

Any OpenAI-compatible provider works — OpenAI, Anthropic, Google, DeepSeek, Qwen, Ollama, and more. Each Daimon can use a different model.

---

## Quick Start

```bash
git clone https://github.com/DarkArty07/Aether-Agents.git
cd Aether-Agents
bash scripts/setup.sh
```

Then: edit `.env` with your API keys, restart your terminal, and run `aether`.

That's it. `setup.sh` handles venv, pip dependencies, config templating, and shell wrappers automatically.

---

## Requirements

- **Python 3.11+**
- **Git**
- NVIDIA GPU optional (for STT with faster-whisper)

For detailed installation options, see [docs/guides/INSTALLATION.md](docs/guides/INSTALLATION.md).

---

## Architecture

```
Hermes (Orchestrator)
    │ MCP (stdio)
    ▼
Olympus v3 MCP Server
    │ ACP (HTTP, localhost)
    ▼
Daimon (hermes-agent -p <daimon>)
    │ Plugin: olympus_v3_hooks
    ▼
SQLite ← both sides read/write
```

- **ACP** — Standard session lifecycle (open, message, poll, close, delegate)
- **Plugin Hooks** — Per-turn observability inside the Daimon process (`post_llm_call`, `post_tool_call`, `on_session_end`, `pre_llm_call`)
- **SQLite** — Shared data channel; no fragile buffer accumulation or event translation

---

## Project Structure

```
Aether-Agents/
├── home/
│   ├── profiles/         ← Daimon profiles (hefesto, athena, etc.)
│   ├── skills/            ← Shared skills
│   ├── .venv-hermes/      ← Hermes venv (created by setup.sh)
│   └── config.yaml        ← Root Daimon configuration
├── src/olympus_v3/        ← MCP server, ACP manager, SQLite, plugin hooks
├── scripts/
│   ├── setup.sh           ← Full automated setup
│   ├── update.sh          ← Git pull + pip upgrade
│   └── start-gateway.sh   ← Systemd gateway manager
├── docs/guides/           ← Installation, configuration, quickstart guides
├── tests/
└── Makefile
```

---

## Available Scripts

| Script | Command | Description |
|--------|---------|-------------|
| setup.sh | `bash scripts/setup.sh` | Full automated setup (venv, pip, config, wrappers) |
| update.sh | `bash scripts/update.sh` | Git pull + pip upgrade (preserves config) |
| start-gateway.sh | `bash scripts/start-gateway.sh start` | Start/stop/restart Hermes gateway service |
| Makefile | `make setup` / `make doctor` | Shortcuts for common tasks |

---

## Configuration

Copy and edit the provided templates:

```bash
cp home/config.yaml.template home/config.yaml   # Edit providers, models, toolsets
cp .env.example .env                             # Add your API keys
```

`config.yaml.template` uses `__AETHER_ROOT__` and `__HERMES_PYTHON__` placeholders — `setup.sh` resolves them automatically.

For full configuration docs, see [docs/guides/CONFIGURATION.md](docs/guides/CONFIGURATION.md).

---

## Daimons

| Daimon | Role | Level | Thinking |
|--------|------|-------|----------|
| **Hefesto** | Senior Developer / Implementation Lead | 2 | medium |
| **Etalides** | Web Researcher | 2 | medium |
| **Ariadna** | Project Manager | 2 | medium |
| **Athena** | Security Engineer | 2 | high |
| **Daedalus** | UX/UI Designer | 2 | medium |
| **Ictinus** | Backend Architect | 1 | medium |

Level 2 Daimons execute tasks. Level 1 Consultants provide expert input on demand.

---

## Contributing

PRs are welcome! See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

---

## License

[MIT](LICENSE)