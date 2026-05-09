# Aether Agents

[![Version](https://img.shields.io/badge/version-0.6.0-blue)](CHANGELOG.md)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

A **provider-agnostic** multi-agent orchestration system for collaborative software development. Hermes delegates to specialized Daimons through ACP sessions with plugin-powered observability and Human-in-the-Loop approval gates.

---

## What is Aether Agents?

Aether Agents is a 5-phase agent ecosystem:

```
IDEA → RESEARCH → DESIGN → PLAN → CODE
```

- **Hermes** — The orchestrator. Uses Hermes Agent (MCP, memory, skills) to route tasks, synthesize output, and manage workflows.
- **6 Daimons** — Specialized sub-agents that execute within their domain.
- **Olympus v3** — MCP server that bridges Hermes to Daimons via ACP + Plugin Hooks + SQLite.

**Communication stack:**
- Hermes ↔ **MCP** ↔ Olympus v3 ↔ **ACP** ↔ Daimon subprocess
- Plugin hooks write per-turn data to **SQLite** → Olympus reads it on `poll()`

Any OpenAI-compatible provider works — OpenAI, Anthropic, Google, DeepSeek, Qwen, OpenRouter, Ollama, and more. Each Daimon can use a different model.

---

## Olympus v3 Architecture

Replaces Pi Agent RPC with **ACP + Plugin Hooks + SQLite**:

- **ACP** — Standard session lifecycle (open, message, poll, close, delegate)
- **Plugin hooks** — Per-turn observability INSIDE the Daimon process:
  - `post_llm_call` → writes full turn + reasoning to SQLite
  - `post_tool_call` → writes every tool invocation to SQLite
  - `on_session_end` → marks session completed (always fires)
  - `pre_llm_call` → reads steering directives from SQLite
- **SQLite** — Shared data channel. No fragile buffer accumulation, no event translation.

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

### Why v3 Replaces v2

| Feature | Pi Agent RPC (v2) | Olympus v3 (ACP + Plugin + SQLite) |
|---------|-------------------|-------------------------------------|
| Per-turn visibility | Accumulated buffer (fragile) | `post_llm_call` hook writes each turn |
| Tool audit trail | Always reported 0 (Bug B) | `post_tool_call` captures every invocation |
| Session completion | `agent_end` not guaranteed | `on_session_end` always fires |
| Mid-conversation steering | Impossible | `pre_llm_call` reads steering from SQLite |
| Response extraction | 3 fallback sources, fragile | Canonical: SQLite turn row |
| Protocol | Pi JSONL (black-box) | ACP (standard) + Plugin (inside agent) + SQLite (shared) |

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

## Quick Start

### Prerequisites

- Python 3.11+
- [Hermes Agent](https://github.com/nousresearch/hermes-agent) installed

### Install

```bash
git clone https://github.com/DarkArty07/Aether-Agents.git
cd Aether-Agents

python3 -m venv venv
source venv/bin/activate
pip install -e .
```

### Configure

```bash
cp home/profiles/hermes/.env.example home/profiles/hermes/.env
# Edit .env with your API keys

cp home/config.yaml.example home/config.yaml
# Edit provider settings for your system
```

### Install Plugin

Each Daimon profile needs the `olympus_v3` plugin:

```yaml
# home/profiles/<daimon>/config.yaml
plugins:
  enabled:
    - olympus_v3
```

### Enable MCP Server

Add `olympus_v3` to your Hermes MCP servers config.

### Start

```bash
HERMES_HOME=/path/to/Aether-Agents/home hermes --profile hermes
```

---

## Configuration

Daimons are declared under the `daimons` key in `home/config.yaml`:

```yaml
daimons:
  hefesto:
    provider: opencode-go
    model: deepseek-v4-flash
    thinking: medium
    toolsets:
      - terminal
      - file
      - search_files
```

Each Daimon profile lives at `home/profiles/<name>/` with `config.yaml`, `SOUL.md`, and the `plugins/olympus_v3/` hook.

---

## Project Structure

```
Aether-Agents/
├── src/olympus_v3/           ← MCP server + ACP manager + SQLite
│   ├── server.py             ← MCP tools (talk_to, discover, consult)
│   ├── acp_manager.py        ← ACP session lifecycle
│   ├── db.py                 ← SQLite persistence (WAL mode)
│   ├── config_loader.py      ← Discovers Daimon profiles
│   ├── consult_action.py     ← Consulting workflow
│   └── olympus_v3_hooks/     ← Plugin hooks (per-turn observability)
├── home/
│   ├── profiles/             ← Daimon profiles (hefesto, athena, ictinus, ...)
│   ├── skills/               ← Shared skills
│   └── config.yaml           ← Daimon configs, providers, models
├── tests/
├── CHANGELOG.md
└── LICENSE
```

---

## License

MIT License. See [LICENSE](LICENSE) for details.