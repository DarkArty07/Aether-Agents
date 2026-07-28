<div align="center">

# 🏛️ Aether Agents

**A multi-agent team built on [hermes-agent](https://github.com/NousResearch/hermes-agent)**

[![Version](https://img.shields.io/badge/version-0.18.2-blue)](CHANGELOG.md)
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
git clone --recurse-submodules https://github.com/DarkArty07/Aether-Agents.git
cd Aether-Agents
bash scripts/setup.sh
```

Run `aether` after setup, then configure the generated `home/config.yaml` and profile `.env` files for your provider credentials. `setup.sh` creates runtime configuration from the tracked templates without overwriting an existing config or `.env`. See [docs/guides/INSTALLATION.md](docs/guides/INSTALLATION.md) for detailed options.

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
| ✅ | **Reliability Contracts** | Six Daimon profiles use role-specific evidence and verification contracts, checked by a 19-case isolated benchmark. |
| 🧪 | **Default-Off Coordination Lab** | v0.19 R7 adds an isolated shadow observer, typed failure/recovery evidence, and disposable durable correlation. It is not active in the gateway and never replaces Olympus lifecycle ownership. |
| 🔬 | **Self-Improvement Instrumentation Bootstrap** | v0.20.0 adds a default-off Hermes lifecycle plugin, project-scoped redacted ledger, interruption reconciliation, and deterministic release-evidence projection. Runtime activation remains separately gated; GitHub integration and release publication follow ODR-0001. |
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

### v0.19 experimental coordination closeout

v0.19.0 is frozen at R11 as an **experimental, default-off, and not operationally validated** baseline. R7 demonstrated observational shadow correlation; R8 is legacy-blocked; R9–R11 have deterministic evidence. The live `talk_to` path still goes directly through Olympus/`ACPManager`: the kernel does not replace Hermes hub-and-spoke, no kernel-backed live pilot was completed, and production migration/rollback was not exercised. See the [canonical closeout](docs/releases/v0.19.0-autonomous-coordination/RELEASE_CLOSEOUT.md).

The [v0.19.x incremental kernel migration](docs/releases/v0.19.x-kernel-migration/ROADMAP_CLOSEOUT.md) is closed at v0.19.5 with verdict **VIABLE — BOUNDED**. It demonstrated one source, two immutable successor candidates, deterministic committed selection, trusted semantic handoff, cleanup and zero survivors. v0.19.6 was closed without a separate patch. Harmonia remains default-off, and v0.19.5 remains an unpublished technical candidate.

### v0.20.0 self-improvement bootstrap

The candidate [v0.20.0 instrumentation bootstrap](docs/releases/v0.20.0/CYCLE.yaml) has an implemented but **default-off** Hermes Agent plugin. It verifies Aether project identity before creating `.aether/self_improvement.db`, records only allowlisted lifecycle/router/coordination metadata, preserves interrupted and concurrent sessions, and can project deterministic release evidence without approving a version. `hermes plugins list` discovers `aether-self-improvement` as `not enabled`. Activation, runtime restart and a live bounded pilot remain separately gated. Commits, push, PR integration, annotated tags and GitHub Releases follow the standing deterministic authority in [ODR-0001](docs/decisions/ODR-0001-main-integration-and-release-automation.md).

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

## 📚 Documentation

The documentation is organized by authority and audience so product intent is not inferred from implementation or release evidence:

- **[Documentation map](docs/README.md)** — canonical index and source-of-truth hierarchy
- **[Agent onboarding](docs/AGENT_ONBOARDING.md)** — required reading order before changing the project
- **[Product](docs/product/README.md)** — vision, mission, objectives, scope, and principles
- **[Architecture](docs/architecture/README.md)** — current and target technical system documentation
- **[Knowledge](docs/knowledge/README.md)** — shared terminology, constraints, capabilities, and limitations
- **[Guides](docs/guides/)** — installation, configuration, and task-oriented usage
- **[Operations](docs/operations/README.md)** — health, updates, recovery, and troubleshooting runbooks
- **[Technical reference](docs/reference/README.md)** — tools, commands, configuration, and compatibility
- **[Contributing](docs/contributing/README.md)** — development and documentation workflow
- **[Decisions](docs/decisions/README.md)** — durable product, architecture, and operational decisions

Release plans, benchmarks, handoffs, and evidence remain under `docs/releases/`; they document specific execution history and do not replace the product vision.

---

## 🔧 Scripts & Makefile

| Command | What it does |
|---------|-------------|
| `bash scripts/setup.sh` | Full setup: venv, pip, config, wrappers |
| `bash scripts/update.sh` | Git pull + pip upgrade (preserves config) |
| `bash scripts/start-gateway.sh start` | Start/stop/restart gateway service |
| `make doctor` | Verify installation health |
| `make setup` | Shortcut for setup.sh |
| `make setup-honcho` | Initialize Honcho and start it with detected Docker Compose or Podman Compose |
| `make honcho-up` / `make honcho-down` | Start or stop Honcho with the detected Compose runtime |
| `make honcho-logs` | Follow Honcho API logs with the detected Compose runtime |

---

## 🔑 Configuration

`setup.sh` generates `config.yaml` from templates and copies `.env.example` → `.env` without replacing existing local files. The tracked configuration schema is v32. Configure provider credentials in the generated `.env` files:

```bash
# After setup, edit API keys:
nano home/.env
```

Config templates use `__AETHER_ROOT__` and `__HERMES_PYTHON__` placeholders — `setup.sh` resolves them to your machine's paths. Primary routes are Hermes on `openai-codex/gpt-5.6-sol` and all six Daimons on `openai-codex/gpt-5.6-terra`; profile-specific OpenRouter entries are intentional fallback routes. Graphify is the explicit exception: its semantic inference uses `llmgateway/deepseek-v4-flash`. See [docs/guides/CONFIGURATION.md](docs/guides/CONFIGURATION.md) for full options.

---

## 🧠 Memory Provider (Honcho)

Aether Agents uses [Honcho](https://github.com/plastic-labs/honcho) as a self-hosted memory layer for all Daimons. Honcho provides:

- **Persistent user profiles** — traits, preferences, communication style
- **Semantic memory search** — cross-session context recall
- **Dialectic reasoning** — synthesized answers from accumulated observations

### Prerequisites

- A supported Compose runtime: Docker Compose v2, legacy `docker-compose`, or Podman Compose.
- 4 GB free RAM for the API, deriver, PostgreSQL + pgvector, and Redis containers.

### Setup

    make setup-honcho

The setup script detects the available Compose runtime, initializes the Honcho submodule, generates `honcho-server/.env` from its template using configured keys, and starts the services.

### Commands

    make honcho-up       # Start services with the detected Compose runtime
    make honcho-down     # Stop services while preserving named volumes
    make honcho-logs     # Follow API logs with the detected Compose runtime

### Architecture

Honcho runs as four internal containers: API, deriver, PostgreSQL + pgvector, and Redis. Only the API is host-bound at `127.0.0.1:8010`; PostgreSQL and Redis remain internal to the Compose network. Daimons query Honcho through MCP tools (`honcho_profile`, `honcho_search`, `honcho_reasoning`).

The submodule includes compatibility patches for its configured providers. See `honcho-server/PATCHES.md` for details.

Full documentation: docs/honcho-setup.md

---

## 📜 License & Attribution

**Aether Agents** is [MIT licensed](LICENSE) © Christopher (DarkArty07).

Built on [hermes-agent](https://github.com/NousResearch/hermes-agent) by [Nous Research](https://nousresearch.com) (MIT). Aether Agents extends it with Olympus v3 (MCP/ACP orchestration), .aether (project continuity), 6 Daimon profiles, and automated setup.

---

## 🤝 Contributing

PRs are welcome! See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.