# Aether Agents

A multi-agent system built on the **hermes-agent** framework that orchestrates 6 specialized Daimons for collaborative software development.

---

## What is Aether Agents?

Aether Agents is an AI agent ecosystem that works in a coordinated way to assist in software development. The system consists of:

- **Hermes**: The main orchestrator that coordinates all Daimons
- **6 Daimons**: Specialized agents in different areas (management, development, research, design, security)

Communication follows this flow:
```
Hermes → talk_to() → Olympus MCP (ACP protocol) → Target Daimon
```

Each Daimon has its own configuration profile, assigned AI model, and specific tools.

---

## The 6 Daimons

| Daimon | Role | Suggested Model | Tools |
|--------|------|-----------------|-------|
| **Hermes** | Orchestrator | `glm-5.1` (z.ai) | hermes-agent |
| **Ariadna** | Project Manager | `kimi-k2.5` (opencode.go) | opencode-go |
| **Hefesto** | Senior Developer | `glm-5.1` (z.ai) | opencode-go |
| **Etalides** | Web Researcher | `minimax-m2.7` (opencode.go) | opencode-go |
| **Daedalus** | UX/UI Designer | `mimo-v2-omni` (opencode.go) | opencode-go |
| **Athena** | Security Engineer | `kimi-k2.6` (opencode.go) | opencode-go |

> **Note on models**: The models listed above are tested suggestions that performed well for each role in our testing. They are not hard requirements — you can assign any model supported by the configured provider. We recommend evaluating models with domain-specific prompts before assigning them to each Daimon.

### Role descriptions

- **Hermes**: Coordinates tasks, delegates work to Daimons, maintains project state
- **Ariadna**: Manages planning, task tracking, design documentation and plans
- **Hefesto**: Senior code development, refactoring, feature implementation
- **Etalides**: Web research, documentation search, technology analysis
- **Daedalus**: Interface design, UX/UI, visual prototyping
- **Athena**: Security auditing, code review, security best practices

---

## Project Structure

```
Aether-Agents/
├── home/                          # Project HERMES_HOME
│   ├── config.yaml                # Orchestrator config
│   ├── profiles/
│   │   ├── hermes/                # Orchestrator
│   │   ├── ariadna/               # Project Manager
│   │   ├── hefesto/               # Senior Developer
│   │   ├── etalides/              # Web Researcher
│   │   ├── daedalus/              # UX/UI Designer
│   │   └── athena/                # Security Engineer
│   ├── sessions/                  # Auto-created by hermes
│   └── logs/                      # Auto-created by hermes
│
├── skills/
│   └── aether-agents/             # Ecosystem skills
│       ├── orchestration/         # Hermes orchestration skill
│       ├── ariadna-workflow/
│       ├── hefesto-workflow/
│       ├── etalides-workflow/
│       ├── daedalus-workflow/
│       └── athena-workflow/
│
├── src/olympus/                   # MCP server (ACP protocol)
│   ├── server.py
│   ├── acp_client.py
│   ├── discovery.py
│   ├── registry.py
│   ├── config.py
│   └── log.py
│
├── shared/env.base                # Environment variable template
├── scripts/
│   ├── setup-env.sh               # Generates .env per profile
│   └── start.sh                   # Verifies ecosystem and shows instructions
│
├── .eter/                         # Project state (gitignored)
│   ├── .hermes/                   # DESIGN.md + PLAN.md
│   └── .ariadna/                  # CURRENT.md + LOG.md
│
└── pyproject.toml                 # Olympus MCP package
```

---

## Installation

### 1. Clone the repository

```bash
git clone https://github.com/DarkArty07/Aether-Agents.git
cd Aether-Agents
```

### 2. Create virtual environment and install dependencies

```bash
python3 -m venv venv
source venv/bin/activate
pip install -e .
```

### 3. Configure environment variables

The project uses `shared/env.base` as a template. Run the setup script to generate `.env` files for each profile:

```bash
bash scripts/setup-env.sh
```

Then edit each `.env` in `home/profiles/<daimon>/` with your API keys based on the models you've chosen.

---

## Configuration

### API Keys

API keys depend on the model providers you choose for each Daimon. Configure keys in each profile's `.env` file:

| Example variable | Provider | Typical profiles |
|------------------|----------|------------------|
| `GLM_API_KEY` | z.ai | Hermes, Hefesto |
| `OPENCODE_GO_API_KEY` | opencode.go | Ariadna, Etalides, Daedalus, Athena |

> These variables are examples based on the suggested models. If you use other providers, configure the corresponding variables.

### HERMES_HOME

`HERMES_HOME` must point to the project's `home/` directory. This isolates Aether Agents configuration from your global hermes-agent installation.

```bash
export HERMES_HOME=~/Aether-Agents/home
```

---

## Getting Started

### Option A: Use the verification script

```bash
cd ~/Aether-Agents
source venv/bin/activate
bash scripts/start.sh
```

### Option B: Manual start

```bash
cd ~/Aether-Agents
source venv/bin/activate
HERMES_HOME=~/Aether-Agents/home hermes --profile hermes
```

### Start a specific Daimon (for testing)

```bash
HERMES_HOME=~/Aether-Agents/home hermes --profile hefesto
HERMES_HOME=~/Aether-Agents/home hermes --profile ariadna
```

---

## Using Skills

Skills are organized in `skills/aether-agents/` and loaded via `external_dirs` in each profile's configuration.

### Skill structure

```
skills/aether-agents/
├── orchestration/         # Orchestration skills (Hermes)
├── ariadna-workflow/      # Project management workflow
├── hefesto-workflow/      # Development workflow
├── etalides-workflow/     # Research workflow
├── daedalus-workflow/     # Design workflow
└── athena-workflow/       # Security workflow
```

### Loading skills

Skills are loaded automatically when you start a profile. The configuration in `home/profiles/<name>/config.yaml` must include:

```yaml
external_dirs:
  - ~/Aether-Agents/skills/aether-agents/<workflow-name>/
```

---

## talk_to — Session Lifecycle

The orchestrator communicates with Daimons using this flow:

```
discover → open → message → poll (or wait) → close
```

| Action | Description |
|--------|-------------|
| `discover` | Lists available agents |
| `open` | Spawns the Daimon (if dead) and creates an ACP session |
| `message` | Sends a prompt (async, returns immediately) |
| `poll` | Checks progress — thoughts, messages, tool calls |
| `wait` | Blocks until done (max 300s) |
| `cancel` | Aborts a running session |
| `close` | Closes the session; agent process stays alive |

Daimons are **keep-alive** — spawned on first `open` and kept alive between sessions.

---

## Troubleshooting

### HERMES_HOME not configured
```bash
export HERMES_HOME=~/Aether-Agents/home
```

### Missing API keys
```bash
cat home/profiles/hermes/.env
# Edit with your keys
```

### Script permissions
```bash
chmod +x scripts/*.sh
```

### Olympus MCP not available
```bash
source venv/bin/activate
pip install -e .
```

---

## License

Private project. All rights reserved.
