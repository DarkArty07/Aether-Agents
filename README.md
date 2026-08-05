<div align="center">

# 🏛️ Aether Agents

**A multi-agent team built on [hermes-agent](https://github.com/NousResearch/hermes-agent)**

[![Version](https://img.shields.io/badge/version-0.22.0-blue)](CHANGELOG.md)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Tests](https://github.com/DarkArty07/Aether-Agents/actions/workflows/test.yml/badge.svg)](https://github.com/DarkArty07/Aether-Agents/actions/workflows/test.yml)
[![Python 3.11+](https://img.shields.io/badge/python-3.11%2B-blue.svg)](https://www.python.org/downloads/)
[![PRs Welcome](https://img.shields.io/badge/PRs-welcome-brightgreen.svg)](CONTRIBUTING.md)

**[hermes-agent](https://github.com/NousResearch/hermes-agent)** is a self-improving AI agent framework by [Nous Research](https://nousresearch.com). It handles LLM routing, tool execution, memory, skills, cron scheduling, and multi-platform gateways (Telegram, Discord, Slack, CLI). You give it a persona (SOUL.md), a config (config.yaml), and API keys — it becomes an autonomous agent.

**Aether Agents** adds product authority, project identity, continuity, evidence, review, effect controls, specialist profiles, and inert self-improvement primitives to hermes-agent. The v0.22.0 candidate has physically retired the legacy Olympus/ACP runtime and the obsolete v0.20 self-improvement plugin bootstrap. Multi-agent execution, automatic self-improvement instrumentation, `talk_to`, `discover`, and ACP-backed Ariadna curation are therefore intentionally unavailable until replacements pass their separate acceptance gates. No hidden fallback remains.

</div>

---

## ⚡ Quick Start

```bash
git clone https://github.com/DarkArty07/Aether-Agents.git
cd Aether-Agents
bash scripts/setup.sh
```

Run `aether` after setup, then configure the generated `home/config.yaml` and profile `.env` files for your provider credentials. `setup.sh` creates runtime configuration from the tracked templates without overwriting an existing config or `.env`. See [docs/guides/INSTALLATION.md](docs/guides/INSTALLATION.md) for detailed options.

---

## 🔥 Key Features

| | Feature | Description |
|---|---------|-------------|
| 🧠 | **6 Specialized Daimons** | Each a hermes-agent instance with its own model, persona (SOUL.md), and tools. Hefesto builds, Etalides researches, Ariadna curates, Athena audits, Daedalus designs, Ictinus architects. |
| 📜 | **Aether Continuity** | Project-scoped SQLite state, explicit session identity, bounded context injection, issues, decisions, and file-change evidence. |
| 🧭 | **Product Authority** | Substrate-neutral contracts, budgets, evidence, protected effects, review, closure, and human acceptance boundaries. |
| 🧹 | **No Legacy Runtime** | The Olympus package, ACP manager, lifecycle database, hooks, MCP facade, plugins, templates, and entry points are absent. |
| 🔌 | **Any Provider** | OpenAI, Anthropic, Google, DeepSeek, Qwen, Ollama, OpenRouter. Each Daimon can use a different model. |
| 🛠️ | **89 Skills** | Pre-built procedural memory for coding, research, DevOps, creative work, and more. |
| ✅ | **Reliability Contracts** | Six Daimon profiles use role-specific evidence and verification contracts, checked by a 19-case isolated benchmark. |
| 🔬 | **Inert Self-Improvement Primitives** | Schema-compatible redacted ledger, deterministic comparison, isolated candidates, and human promotion authority; no plugin or automatic instrumentation path. |
| ⏰ | **Cron Scheduling** | Automated tasks with delivery to Telegram, Discord, Slack. Reports, audits, maintenance — unattended. |
| 💬 | **Multi-Platform** | CLI, Telegram, Discord, Slack, WhatsApp. All via hermes-agent gateway. |

---

## 🏗️ Current candidate architecture

```
User
  │
  ▼
Hermes (hermes-agent)
  │
  ├── Aether product contracts / authority / evidence
  ├── Aether continuity hooks ──────────────┐
  └── inert ledger / causality / promotion  │
                                           ▼
                                  project-local .aether/
```

- **`aether_agents`** owns product semantics and continuity; it has no Olympus or Orca imports.
- **`.aether/aether.db`** preserves project continuity without migrating existing rows.
- **`.aether/self_improvement.db`** remains schema 5 and untouched; no candidate plugin opens it automatically.
- **Specialist profiles** remain versioned, but no runtime in this candidate spawns or controls them.
- **Historical v0.19/v0.20 evidence** remains under `docs/releases/` and does not describe an active execution path.

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

These profiles preserve the approved specialist roles and contracts. The v0.22.0
candidate does not currently provide a runtime that invokes them.

---

## 📁 Project Structure

```
Aether-Agents/
├── home/
│   ├── profiles/         ← Daimon configs (config.yaml.template)
│   ├── skills/            ← 89 pre-built skills
│   ├── SOUL.md            ← Hermes orchestrator personality
│   └── .aether/           ← Project continuity DB (gitignored)
├── src/aether_agents/     ← contracts, continuity, evidence, effects, review
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

---

## 🔑 Configuration

`setup.sh` generates `config.yaml` from templates and copies `.env.example` → `.env` without replacing existing local files. The tracked configuration schema is v32. Configure provider credentials in the generated `.env` files:

```bash
# After setup, edit API keys:
nano home/.env
```

Config templates use `__AETHER_ROOT__` and `__HERMES_PYTHON__` placeholders — `setup.sh` resolves them to your machine's paths. Primary routes are Hermes on `openai-codex/gpt-5.6-sol` and all six Daimons on `openai-codex/gpt-5.6-terra`; profile-specific OpenRouter entries are intentional fallback routes. See [docs/guides/CONFIGURATION.md](docs/guides/CONFIGURATION.md) for full options.

---

## 🧠 Memory and Learning

Aether uses Hermes Agent's built-in `USER.md`, `MEMORY.md`, session search,
skills, and Curator. No external semantic-memory service, submodule, container
stack, or separate memory authority is required by the candidate.

---

## 📜 License & Attribution

**Aether Agents** is [MIT licensed](LICENSE) © Christopher (DarkArty07).

Built on [hermes-agent](https://github.com/NousResearch/hermes-agent) by [Nous Research](https://nousresearch.com) (MIT). Aether Agents adds product contracts, project continuity, evidence and review boundaries, specialist profiles, self-improvement instrumentation, and automated setup.

---

## 🤝 Contributing

PRs are welcome! See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.