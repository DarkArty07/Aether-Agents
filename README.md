<div align="center">

# 🏛️ Aether Agents

**A multi-agent team built on [hermes-agent](https://github.com/NousResearch/hermes-agent)**

[![Version](https://img.shields.io/badge/version-0.15.0-blue)](CHANGELOG.md)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Tests](https://github.com/DarkArty07/Aether-Agents/actions/workflows/test.yml/badge.svg)](https://github.com/DarkArty07/Aether-Agents/actions/workflows/test.yml)
[![Python 3.11+](https://img.shields.io/badge/python-3.11%2B-blue.svg)](https://www.python.org/downloads/)
[![PRs Welcome](https://img.shields.io/badge/PRs-welcome-brightgreen.svg)](CONTRIBUTING.md)

**[hermes-agent](https://github.com/NousResearch/hermes-agent)** is a self-improving AI agent framework by [Nous Research](https://nousresearch.com). It handles LLM routing, tool execution, memory, skills, cron scheduling, and multi-platform gateways (Telegram, Discord, Slack, CLI). You give it a persona (SOUL.md), a config (config.yaml), and API keys — it becomes an autonomous agent.

**Aether Agents** extends hermes-agent into a multi-agent team. Six specialized Daimons — each a hermes-agent instance with its own model, personality, and toolset — are orchestrated by Hermes through **Olympus v3**, an MCP server that manages sessions, routes tasks, and maintains project continuity via **.aether**. The result: a crew of experts that think independently but coordinate through structured delegation. Any OpenAI-compatible provider. Any model per Daimon.

</div>

---

## ⚡ Quick Start

```bash
git clone https://github.com/DarkArty07/Aether-Agents.git
cd Aether-Agents
bash scripts/setup.sh
```

Edit `.env` with your API keys, restart your terminal, and run `aether`.

`setup.sh` handles everything: Python venv, pip dependencies, config generation from templates, and shell wrappers. See [docs/guides/INSTALLATION.md](docs/guides/INSTALLATION.md) for detailed options.

---

## 🔥 Key Features

| | Feature | Description |
|---|---------|-------------|
| 🧠 | **6 Specialized Daimons** | Each a hermes-agent instance with its own model, persona (SOUL.md), and tools. Hefesto builds, Etalides researches, Ariadna curates, Athena audits, Daedalus designs, Ictinus architects. |
| 🏛️ | **Olympus v3 MCP** | ACP sessions, plugin hooks, SQLite shared state. The bridge between orchestrator and executors. |
| 📜 | **.aether Continuity** | Automatic capture → curation → injection. Daimons always know what project they're on. No blind delegations. |
| 🔄 | **5-Phase Pipeline** | IDEA → RESEARCH → DESIGN → PLAN → CODE. Sequential quality gates. Hermes decides, Daimons execute. |
| 🔌 | **Any Provider** | OpenAI, Anthropic, Google, DeepSeek, Qwen, Ollama, OpenRouter. Each Daimon can use a different model. |
| 🛠️ | **89 Skills** | Pre-built procedural memory for coding, research, DevOps, creative work, and more. |
| ⏰ | **Cron Scheduling** | Automated tasks with delivery to Telegram, Discord, Slack. Reports, audits, maintenance — unattended. |
| 💬 | **Multi-Platform** | CLI, Telegram, Discord, Slack, WhatsApp. All via hermes-agent gateway. |

---

## 🏗️ Architecture

```
User
  │
  ▼
Hermes (Orchestrator)
  │ MCP (stdio)
  ▼
Olympus v3 Server
  │ ACP (HTTP, localhost)
  ▼
┌─────────────────────────────────────┐
│  Daimon (hermes-agent instance)    │
│  ┌─────────────────────────────┐   │
│  │ Plugin: olympus_v3_hooks    │   │
│  └─────────────────────────────┘   │
│  ┌─────────────────────────────┐   │
│  │ Plugin: aether_hooks       │   │
│  └─────────────────────────────┘   │
└─────────────────────────────────────┘
  ↕ SQLite (.aether/)
```

- **MCP** — Hermes speaks to Olympus via Model Context Protocol (stdio)
- **ACP** — Olympus manages Daimon sessions via Agent Client Protocol (HTTP)
- **Plugin Hooks** — Per-turn observability inside each Daimon: `post_llm_call`, `post_tool_call`, `on_session_end`, `pre_llm_call`
- **.aether** — 3-layer continuity: capture (hooks) → curate (Ariadna) → inject (first turn)

---

## 🎭 The Daimons

| Daimon | Role | Level | Description |
|--------|------|-------|-------------|
| **Hefesto** | Senior Developer | 2 | Builds, fixes, implements. Your senior developer. |
| **Etalides** | Researcher | 2 | Finds facts. Never opinions, only verifiable data. |
| **Ariadna** | Context Curator | 2 | Curates project context. Keeps everyone on the right page. |
| **Athena** | Security Engineer | 2 | Audits security. Finds vulnerabilities before they ship. |
| **Daedalus** | UX/UI Designer | 2 | Designs experiences, not just mockups. |
| **Ictinus** | Backend Architect | 1 | Scales databases, APIs, infrastructure. Consultant on demand. |

Level 2 Daimons execute tasks. Level 1 Consultants provide expert input when summoned.

---

## 📁 Project Structure

```
Aether-Agents/
├── home/
│   ├── profiles/         ← Daimon configs (config.yaml.template)
│   ├── skills/            ← 89 pre-built skills
│   ├── SOUL.md            ← Hermes orchestrator personality
│   └── .aether/           ← Project continuity DB (gitignored)
├── src/olympus_v3/        ← MCP server + ACP + plugin hooks
├── scripts/
│   ├── setup.sh           ← Full automated setup
│   ├── update.sh          ← Git pull + pip upgrade
│   └── start-gateway.sh  ← Systemd gateway manager
├── docs/guides/           ← Installation, configuration, quickstart
└── Makefile               ← setup, update, doctor, clean, test
```

---

## 🔧 Scripts & Makefile

| Command | What it does |
|---------|-------------|
| `bash scripts/setup.sh` | Full setup: venv, pip, config, wrappers |
| `bash scripts/update.sh` | Git pull + pip upgrade (preserves config) |
| `bash scripts/start-gateway.sh start` | Start/stop/restart gateway service |
| `make doctor` | Verify installation health |
| `make setup` | Shortcut for setup.sh |

---

## 🔑 Configuration

`setup.sh` generates `config.yaml` from templates and copies `.env.example` → `.env` for each profile. Edit your API keys in the `.env` files:

```bash
# After setup, edit API keys:
nano home/.env
```

Config templates use `__AETHER_ROOT__` and `__HERMES_PYTHON__` placeholders — `setup.sh` resolves them to your machine's paths. See [docs/guides/CONFIGURATION.md](docs/guides/CONFIGURATION.md) for full options.

---

## 🧠 Memory Provider (Honcho)

Aether Agents uses [Honcho](https://github.com/plastic-labs/honcho) as a self-hosted memory layer for all Daimons. Honcho provides:

- **Persistent user profiles** — traits, preferences, communication style
- **Semantic memory search** — cross-session context recall
- **Dialectic reasoning** — synthesized answers from accumulated observations

### Setup

    make setup-honcho

This initializes the Honcho git submodule, generates honcho-server/.env from template (using your OPENCODE_GO_API_KEY), and starts all services.

### Commands

    make honcho-up       # Start services (api, deriver, postgres, redis)
    make honcho-down     # Stop services
    make honcho-logs     # Follow logs
    make honcho-status   # Check service health

### Architecture

Honcho runs as 4 containers on localhost:8010 (API), localhost:5434 (Postgres+pgvector), localhost:6380 (Redis). All Daimons query Honcho via MCP tools (honcho_profile, honcho_search, honcho_reasoning).

The submodule includes 4 patches for DeepSeek/OpenCode Go compatibility (3-level structured output fallback, thinking disable, embedding dimensions, config validation). See honcho-server/PATCHES.md for details.

Full documentation: docs/honcho-setup.md

---

## 📜 License & Attribution

**Aether Agents** is [MIT licensed](LICENSE) © Christopher (DarkArty07).

Built on [hermes-agent](https://github.com/NousResearch/hermes-agent) by [Nous Research](https://nousresearch.com) (MIT). Aether Agents extends it with Olympus v3 (MCP/ACP orchestration), .aether (project continuity), 6 Daimon profiles, and automated setup.

---

## 🤝 Contributing

PRs are welcome! See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.