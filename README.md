# Aether Agents

A **provider-agnostic** multi-agent system built on the **hermes-agent** framework. Orchestrates 5 specialized Daimons for collaborative software development with structured workflows and Human-in-the-Loop (HITL) approval gates.

---

## What is Aether Agents?

Aether Agents is an AI agent ecosystem where specialized agents work in coordination following a 5-phase methodology:

```
IDEA → INVESTIGAR → DISEÑAR → PLANIFICAR → PROGRAMAR
```

**Hermes** orchestrates all communication. **5 Daimons** handle their specialties. Communication flows through **Olympus MCP**:

```
Hermes → talk_to() / run_workflow() → Olympus MCP (ACP protocol) → Target Daimon
```

---

## Agents

| Agent | Role | Specialty |
|-------|------|-----------|
| **Hermes** | Orchestrator | Coordinates, designs architecture, delegates, synthesizes |
| **Ariadna** | Project Manager | Tracks state, detects blockers, manages `.eter/`, session audits |
| **Hefesto** | Senior Developer | Implements specs, coordinates Ergates (sub-agents by role), debugging |
| **Etalides** | Web Researcher | Searches, extracts, verifies web sources. 10-link budget. No opinions. |
| **Daedalus** | UX/UI Designer | User flows, layouts, prototypes, design systems, accessibility |
| **Athena** | Security Engineer | STRIDE threat modeling, code audit, dependency CVE review |

---

## Olympus MCP — Workflow Engine

Olympus exposes 3 MCP tools to the orchestrator:

| Tool | Purpose |
|------|---------|
| `talk_to` | Direct communication with a single Daimon (open → message → poll → close) |
| `discover` | List available Daimons and their capabilities |
| `run_workflow` | Execute multi-agent LangGraph workflows with Human-in-the-Loop |

### 6 Predefined Workflows

| Workflow | Purpose | HITL Points | Daimons |
|----------|---------|-------------|---------|
| `project-init` | Initialize new project `.eter/` structure | None | Ariadna |
| `feature` | Full feature lifecycle (research→design→code→audit) | 3 | Etalides, Daedalus, Hefesto, Athena |
| `bug-fix` | Diagnose → fix → verify | 1 | Etalides, Hefesto, Athena |
| `security-review` | CVE research → audit → fix loop | 1 | Etalides, Athena, Hefesto |
| `research` | Pure knowledge gathering | None | Etalides |
| `refactor` | Scope → implement → audit | 1 | Etalides, Hefesto, Athena |

### Human-in-the-Loop (HITL)

Workflows pause at decision points for user approval. The orchestrator presents findings conversationally and the user decides: `approve`, `reject`, `modify`, `confirm`, or `accept_risk`. Workflow state persists via AsyncSqliteSaver.

---

## Project Structure

```
Aether-Agents/
├── home/                              ← HERMES_HOME root
│   ├── skills/                        ← Shared skills (single source of truth)
│   │   ├── aether-agents/             ← Framework skills (10 skills)
│   │   ├── productivity/              ← Generic skill categories
│   │   ├── research/
│   │   └── ... (24 categories total)
│   ├── profiles/                      ← Agent profiles (HERMES_HOME per agent)
│   │   ├── hermes/                    ← Orchestrator (SOUL.md + config.yaml)
│   │   ├── ariadna/                   ← Project Manager
│   │   ├── hefesto/                   ← Senior Developer
│   │   ├── etalides/                  ← Web Researcher
│   │   ├── daedalus/                  ← UX/UI Designer
│   │   └── athena/                    ← Security Engineer
│   ├── sessions/                      ← Auto-created by hermes
│   └── logs/                          ← Auto-created by hermes
│
├── src/olympus/                       ← MCP server + workflow engine
│   ├── server.py                      ← MCP server (tools: talk_to, discover, run_workflow)
│   ├── acp_client.py                  ← ACP protocol client
│   ├── discovery.py                   ← Agent profile discovery
│   ├── registry.py                    ← Session tracking
│   ├── config.py                      ← Olympus configuration
│   └── workflows/                     ← LangGraph workflow engine
│       ├── state.py                   ← WorkflowState TypedDict
│       ├── nodes.py                   ← Node factories + HITL
│       ├── definitions.py             ← 6 workflow graphs
│       └── runner.py                  ← WorkflowRunner (invoke, resume)
│
├── scripts/                           ← Setup scripts
├── .eter/                             ← Project state (gitignored, local)
├── pyproject.toml                     ← Olympus package definition
└── .gitignore
```

### Skills Architecture

Skills live in ONE place: `home/skills/`. Each profile's `config.yaml` points to this shared directory via `skills.external_dirs`. No symlinks, no duplicates.

- **Aether skills** (`home/skills/aether-agents/`): Custom framework skills for orchestration, workflow design, diagnostics, and agent creation
- **Generic skills** (`home/skills/{category}/`): Standard hermes-agent skill categories (productivity, research, github, etc.)

Each agent's SOUL.md references the skills relevant to their specialty.

---

## SOUL.md Convention

All agent profiles follow a 7-section structure:

1. **Identity** — who I am, eponym, role
2. **Execution Context** — how I'm invoked, project root, session scope (DRY for 5 Daimons)
3. **Core Responsibilities** — what I do
4. **Limits** — what I MUST NOT do
5. **Skills** — skills I load (with 1-line descriptions)
6. **Output Format** — how I structure my responses
7. **In Workflow Context** — how I operate inside LangGraph workflows

---

## Project State (`.eter/`)

Every project uses `.eter/` for persistence:

```
PROJECT_ROOT/.eter/
├── .hermes/        ← DESIGN.md (append-top v{N}) + PLAN.md (append-top Sprint{N})
├── .ariadna/       ← CURRENT.md (overwrite) + LOG.md (append-bottom)
├── .hefesto/       ← TASKS.md (overwrite with cycles)
└── .etalides/      ← RESEARCH.md (append-bottom)
```

---

## Installation

```bash
git clone https://github.com/DarkArty07/Aether-Agents.git
cd Aether-Agents

python3 -m venv venv
source venv/bin/activate
pip install -e .
```

### Configure environment

```bash
# Each profile needs API keys
cp home/profiles/hermes/.env.example home/profiles/hermes/.env
# Edit with your keys
```

### Start

```bash
HERMES_HOME=/path/to/Aether-Agents/home hermes --profile hermes
```

---

## talk_to — Session Lifecycle

```
discover → open → message → poll (or wait) → close
```

Daimons are **keep-alive** — spawned on first `open`, stay alive between sessions.

---

## Documentation

- **Olympus MCP**: [`src/olympus/README.md`](src/olympus/README.md) — API reference, HITL guide, pitfalls
- **Team playbook**: `home/skills/aether-agents/orchestration/SKILL.md` — 5-phase pipeline, decision matrix, assignment rules
- **Workflow engine**: `home/skills/aether-agents/workflow-design/SKILL.md` — technical reference
- **Diagnostics**: `home/skills/aether-agents/aether-diagnostics/SKILL.md` — health checks

---

## Best Practices

### 1. Read the Aether skills before coding

When starting a new coding session, ask Hermes to load the Aether skills first. These contain project-specific conventions, workflow protocols, and known pitfalls that aren't obvious from the code alone. Without them, Hermes may miss routing rules, HITL checkpoints, or the delegation matrix.

### 2. Populate USER.md before your first session

Before doing meaningful work, fill out `home/profiles/hermes/memories/USER.md` (or let Hermes ask you). Include basics: your name, preferred language, coding style, tech stack, and project context. This lets Hermes personalize interactions and avoid assumptions about what you know or prefer.

### 3. Use talk_to for design-phase opinions

During the DESIGN phase, ask for specialist opinions through `talk_to()`. Each Daimon offers a unique lens:

- **Etalides** — "Are there established patterns or libraries for this?"
- **Daedalus** — "Is the user flow intuitive? What would the UI look like?"
- **Athena** — "What are the security implications of this architecture?"
- **Hefesto** — "Is this technically feasible? What are the implementation trade-offs?"

Don't jump to PROGRAMAR without consulting at least one Daimon during DISEÑAR.

### 4. Let Hermes decide the workflow

When a task needs multiple agents, tell Hermes *what* you want done — not *how* to orchestrate it. Hermes will choose the right Olympus workflow based on the task type:

- New feature? → `feature` workflow (4 Daimons, 3 HITL gates)
- Bug? → `bug-fix`
- Security audit? → `security-review`
- Pure research? → `research`
- Refactor? → `refactor`
- New project? → `project-init`

Trying to manually chain `talk_to` calls loses context, skips approval gates, and has no error recovery. Trust the workflow engine.

---

## License

MIT License. See [LICENSE](LICENSE) for details.
