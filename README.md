# Aether Agents

[![Version](https://img.shields.io/badge/version-0.6.0-blue)](CHANGELOG.md)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

A **provider-agnostic** multi-agent orchestration system for collaborative software development. Hermes delegates to specialized Daimons through typed RPC workflows with Human-in-the-Loop approval gates.

---

## What is Aether Agents?

Aether Agents is a 5-phase agent ecosystem:

```
IDEA → RESEARCH → DESIGN → PLAN → CODE
```

- **Hermes** — The orchestrator. Uses Hermes Agent (MCP, memory, skills) to route tasks, synthesize output, and manage workflows.
- **5 Daimons** — Specialized sub-agents that execute within their domain.
- **Olympus v2** — MCP server that bridges Hermes to Daimons. Same `talk_to` interface, backend-agnostic.

**Communication stack:**
- Hermes ↔ **MCP** ↔ Olympus v2 ↔ **Pi Agent RPC** ↔ Daimon subprocess

Any OpenAI-compatible provider works — OpenAI, Anthropic, Google, DeepSeek, Qwen, OpenRouter, Ollama, and more. Each Daimon can use a different model.

---

## v5.0.0 — Pi Agent RPC

**Headline:** All Daimons now use **Pi Agent RPC** instead of ACP for sub-agent communication. ACP remains available as instant rollback (`backend: acp` in `config.yaml`).

### Why we replaced ACP

ACP had 3 critical bugs that made Daimon delegation unreliable:

1. **Spinner noise** — `AgentThoughtChunk` mixed progress spinners with reasoning. Regex filters leaked Unicode artifacts, breaking stall detection.
2. **Invisible tool calls** — `total_tool_calls` was always `0`, even when 8+ tools ran. No execution events were emitted.
3. **No reasoning visibility** — Provider chain-of-thought (DeepSeek `reasoning_content`, Anthropic `thinking`) was silently dropped, causing empty Daimon responses.

### ACP vs Pi Agent RPC

| Feature | ACP (old) | Pi RPC (new) |
|---------|-----------|--------------|
| Protocol | Binary stream (spinner noise) | Typed JSONL (`text_delta`, `thinking_delta`, `tool_call`) |
| Tool calls | Always 0 | Explicit `tool_execution_start/end` events |
| Reasoning | Lost | `thinking_delta` events + configurable levels |
| Live steering | None | `steer` command mid-stream |
| Thinking levels | None | `off/minimal/low/medium/high/xhigh` |
| Session persistence | None | Built-in with `--session-dir` |
| Model switching | Restart required | `set_model` at runtime |
| Compaction | Manual | `compact` + auto-compaction |

### New: `delegate` Action (Single-Call Auto-Poll)

One MCP call replaces the entire open→message→poll→close cycle:

```
delegate(agent, prompt, poll_interval=15, timeout=300) → done
```

The server polls internally. Returns final result with `delegate: {timed_out, elapsed_seconds, poll_iterations}` metadata. Manual `open/message/poll/close` remains available for fine-grained control.

---

## Architecture

```
Hermes (Hermes Agent)
    │
    ▼
Olympus v2 MCP Server
    │
    ├── backend: pi_rpc  →  Pi Agent RPC subprocess  →  Daimon
    └── backend: acp     →  ACP protocol (rollback)
```

- **Per-agent backend** — Each Daimon selects `pi_rpc` or `acp` independently in `config.yaml`.
- **Pi configs** — Live at `home/.pi-daimons/{name}/.pi/` (SYSTEM.md, settings.json, extensions).

---

## Daimons

| Daimon | Role | Backend | Tools | Thinking |
|--------|------|---------|-------|----------|
| **Hefesto** | Senior Developer / Implementation Lead | `pi_rpc` | read, write, edit, bash, grep, find, ls | medium |
| **Etalides** | Web Researcher | `pi_rpc` | read, write, edit, bash, grep, find, ls | medium |
| **Ariadna** | Project Manager | `pi_rpc` | read, write, edit, bash | medium |
| **Athena** | Security Engineer | `pi_rpc` | read, write, edit, bash, grep, find, ls | high |
| **Daedalus** | UX/UI Designer | `pi_rpc` | read, write, edit, bash, grep, find, ls | medium |

---

## Quick Start

### Prerequisites

- Python 3.11+
- Node.js 18+ (for Pi Agent RPC backend)
- npm

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
# Edit paths and provider settings for your system
```

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
    backend: pi_rpc      # or acp for rollback
    provider: opencode-go
    model: deepseek-v4-flash
    thinking: medium     # off/minimal/low/medium/high/xhigh
    tools:
      - read
      - write
      - edit
      - bash
      - grep
      - find
      - ls
```

Each entry points to a profile directory at `home/.pi-daimons/{name}/` containing SYSTEM.md, settings.json, and optional extensions.

---

## Project Structure

```
Aether-Agents/
├── src/
│   └── olympus_v2/              ← MCP server + Pi RPC adapter
│       ├── server.py            ← MCP tools (talk_to, delegate, discover, run_workflow)
│       ├── pi_adapter.py        ← Pi Agent RPC lifecycle
│       └── event_translator.py  ← JSONL → MCP events
│
├── home/
│   ├── .pi-daimons/             ← Pi Agent profiles (hefesto, athena, ...)
│   ├── profiles/hermes/         ← Orchestrator profile + SOUL.md
│   ├── skills/                  ← Shared skills (single source of truth)
│   └── config.yaml              ← Daimon backends, providers, models
│
├── tests/                       ← Test suite
├── website/                     ← Landing page
├── CHANGELOG.md
└── LICENSE
```

---

## License

MIT License. See [LICENSE](LICENSE) for details.
