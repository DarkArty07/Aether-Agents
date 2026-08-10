<div align="center">

# 🏛️ Aether Agents

**A multi-agent team built on [hermes-agent](https://github.com/NousResearch/hermes-agent)**

[![Version](https://img.shields.io/badge/version-0.22.0-blue)](CHANGELOG.md)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Tests](https://github.com/DarkArty07/Aether-Agents/actions/workflows/test.yml/badge.svg)](https://github.com/DarkArty07/Aether-Agents/actions/workflows/test.yml)
[![Python 3.11+](https://img.shields.io/badge/python-3.11%2B-blue.svg)](https://www.python.org/downloads/)
[![PRs Welcome](https://img.shields.io/badge/PRs-welcome-brightgreen.svg)](CONTRIBUTING.md)

**[hermes-agent](https://github.com/NousResearch/hermes-agent)** is a self-improving AI agent framework by [Nous Research](https://nousresearch.com). It handles LLM routing, tool execution, memory, skills, cron scheduling, and multi-platform gateways (Telegram, Discord, Slack, CLI). You give it a persona (SOUL.md), a config (config.yaml), and API keys — it becomes an autonomous agent.

**Aether Agents** defines the product vision, Hermes behavior, specialist roles,
participation policy, skills, verification expectations, and release authority for
an AI software team. The v0.22.0 candidate physically retires Olympus/ACP and the
disconnected Python core, provides the unregistered 15-tool Aether MCP operational facade,
and qualifies the exact Orca 1.4.167 desktop-renderer/public-CLI binding through
deterministic M3-M5 and one bounded two-worker model-backed M5.4 pass. It remains
unregistered and inactive. PDR-0014 closes v0.22.0 at that integration boundary,
makes real repair-first Orca operation the goal of v0.23.0, and defers gradual
process-specific migration to v0.24.0. No hidden fallback remains.

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
| 🧠 | **Stable Generic Roster** | Hefesto, Daedalus, and Ictinus are retained generic archetypes; Ariadna is conditional/disabled, while Athena and Etalides are retired/forbidden. Production qualification belongs to v0.23.0. |
| 🧭 | **Product Layer** | Hermes behavior, product decisions, specialist participation, verification policy, semantic acceptance, and release authority. |
| 🐋 | **Qualified Orca Integration** | v0.22.0 proves bounded lifecycle, one/two-worker execution, overlap, messaging, integration, recovery, and cleanup on the exact qualified binding; v0.23.0 turns it into the normal real-work path. |
| 🔒 | **Unregistered MCP Operational Facade** | `aether-mcp` exposes the approved 15-tool control/trace and Orca adapter surface with explicit state-root and trusted-launch requirements; registration, status, doctor, rollback, and live production entry remain v0.23.0 gates. |
| 🔌 | **Any Provider** | OpenAI, Anthropic, Google, DeepSeek, Qwen, Ollama, OpenRouter. Each Daimon can use a different model. |
| 🛠️ | **95 Skills** | Pre-built procedural memory for coding, research, DevOps, creative work, and more. |
| ✅ | **Reliability Contracts** | Six Daimon profiles use role-specific evidence and verification contracts, checked by a 19-case isolated benchmark. |
| 🗃️ | **Protected History** | Existing `.aether` stores and release evidence are preserved without an active candidate reader, writer, migration, or deletion path. |
| ⏰ | **Cron Scheduling** | Automated tasks with delivery to Telegram, Discord, Slack. Reports, audits, maintenance — unattended. |
| 💬 | **Multi-Platform** | CLI, Telegram, Discord, Slack, WhatsApp. All via hermes-agent gateway. |

---

## 🏗️ Target architecture and current boundary

```
User
  │
  ▼
Hermes (hermes-agent)
  ├── interprets product intent and decomposes work
  ├── implements bounded work in parallel
  └── owns product routing and semantic acceptance
                      │
       Aether MCP v1alpha2 (unregistered; 15 approved tools)
       admission / receipts / protected trace / catalog
                      │
       qualified internally through M5.4
       v0.23.0 production registration pending
                      ▼
                  Orca Run
                      │
            independent Tasks / Dispatches
             ┌────────┴────────┐
             ▼                 ▼
         Worker A  ← messages → Worker B
             └────────┬────────┘
                      ▼
          one feature integration branch
```

- **Aether** owns product meaning through Hermes, profiles, skills, decisions, and acceptance policy—not through a parallel coordination kernel.
- **Aether MCP operational entry** composes the typed control/trace and qualified public Orca adapter services into the approved 15-tool surface while remaining unregistered; it does not own Run, Task, worker, terminal, worktree, or message state.
- **Orca** owns Run, Task, Dispatch, messages, workers, terminals, worktrees, recovery, and cleanup mechanics on the exact qualified binding. Pure Headless support remains unqualified.
- **One feature branch** is the integration line; potentially conflicting writers use Orca child worktrees, while strictly disjoint scopes may share the current checkout.
- **Existing `.aether` stores** are preserved and untouched; this candidate has no continuity or self-improvement reader/writer.
- **Specialist profiles** remain versioned, but no accepted runtime in this candidate invokes them yet.
- **Historical v0.19/v0.20 evidence** remains under `docs/releases/` and does not describe an active execution path.

---

## 🎭 The Daimons

| Daimon | Role | Level | Description |
|--------|------|-------|-------------|
| **Hefesto** | Senior Developer | 2 | Builds, fixes, implements. Your senior developer. |
| **Etalides** | Retired research profile | — | Forbidden; no new workflow may depend on it. |
| **Ariadna** | Conditional context curator | — | Disabled until distinct value is proved in v0.23.0. |
| **Athena** | Retired security profile | — | Forbidden under the approved roster policy. |
| **Daedalus** | UX/UI Designer | 2 | Designs experiences, not just mockups. |
| **Ictinus** | Backend Architect | 1 | Scales databases, APIs, infrastructure. Consultant on demand. |

These tracked profiles preserve current and historical contracts; physical
presence does not grant participation. The v0.22.0 candidate does not currently
provide a registered runtime that invokes them. v0.23.0 will qualify only the
retained generic roster through the repair-first Orca production path.

---

## 📁 Project Structure

```
Aether-Agents/
├── home/
│   ├── profiles/         ← Daimon configs (config.yaml.template)
│   ├── skills/            ← 95 pre-built skills
│   ├── SOUL.md            ← Hermes orchestrator personality
│   └── config.yaml.template ← Hermes configuration template
├── scripts/
│   ├── setup.sh           ← Install Hermes + generate configs/wrappers
│   ├── update.sh          ← Git pull + Hermes/config update
│   └── start-gateway.sh  ← Systemd gateway manager
├── src/aether_mcp/       ← unregistered M1 operational MCP facade
├── schemas/              ← versioned Aether MCP and Orca catalog bundles
├── .aether/               ← protected local/historical state (gitignored)
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
| `bash scripts/setup.sh` | Install Hermes, generate config, and create wrappers |
| `bash scripts/update.sh` | Git pull + Hermes upgrade + config check |
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

Built on [hermes-agent](https://github.com/NousResearch/hermes-agent) by [Nous Research](https://nousresearch.com) (MIT). Aether Agents adds product vision, Hermes policy, specialist profiles, skills, verification and acceptance doctrine, release governance, and automated setup. Orca is the intended multi-agent execution substrate after separate acceptance.

---

## 🤝 Contributing

PRs are welcome! See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.
