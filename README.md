     1|# Aether Agents
     2|
     3|A **provider-agnostic** multi-agent system built on the **hermes-agent** framework. Orchestrates 5 specialized Daimons for collaborative software development with structured workflows and Human-in-the-Loop (HITL) approval gates.
     4|
     5|---
     6|
     7|## What is Aether Agents?
     8|
     9|Aether Agents is an AI agent ecosystem where specialized agents work in coordination following a 5-phase methodology:
    10|
    11|```
    12|IDEA → RESEARCH → DESIGN → PLAN → CODE
    13|```
    14|
    15|**Hermes** orchestrates all communication. **5 Daimons** handle their specialties. Communication flows through **Olympus MCP**:
    16|
    17|```
    18|Hermes → talk_to() / run_workflow() → Olympus MCP (ACP protocol) → Target Daimon
    19|```
    20|
    21|### Provider Compatibility
    22|
    23|Aether Agents inherits the same extensive provider compatibility as hermes-agent. Any provider with an OpenAI-compatible API endpoint works — OpenAI, Anthropic, Google, Zhipu AI, DeepSeek, Qwen, OpenRouter, Ollama, vLLM, and many more. Each Daimon can use a different model/provider. No vendor lock-in.
    24|
    25|---
    26|
    27|## Agents
    28|
    29|| Agent | Role | Specialty |
    30||-------|------|-----------|
    31|| **Hermes** | Orchestrator | Coordinates, designs architecture, delegates, synthesizes |
    32|| **Ariadna** | Project Manager | Tracks state, detects blockers, manages `.eter/`, session audits |
    33|| **Hefesto** | Senior Developer | Implements specs, coordinates Ergates (sub-agents by role), debugging |
    34|| **Etalides** | Web Researcher | Searches, extracts, verifies web sources. 10-link budget. No opinions. |
    35|| **Daedalus** | UX/UI Designer | User flows, layouts, prototypes, design systems, accessibility |
    36|| **Athena** | Security Engineer | STRIDE threat modeling, code audit, dependency CVE review |
    37|
    38|---
    39|
    40|## Olympus MCP — Workflow Engine
    41|
    42|Olympus exposes 3 MCP tools to the orchestrator:
    43|
    44|| Tool | Purpose |
    45||------|---------|
    46|| `talk_to` | Direct communication with a single Daimon (open → message → poll → close) |
    47|| `discover` | List available Daimons and their capabilities |
    48|| `run_workflow` | Execute multi-agent LangGraph workflows with Human-in-the-Loop |
    49|
    50|### 6 Predefined Workflows
    51|
    52|| Workflow | Purpose | HITL Points | Daimons |
    53||----------|---------|-------------|---------|
    54|| `project-init` | Initialize new project `.eter/` structure | None | Ariadna |
    55|| `feature` | Full feature lifecycle (research→design→code→audit) | 3 | Etalides, Daedalus, Hefesto, Athena |
    56|| `bug-fix` | Diagnose → fix → verify | 1 | Etalides, Hefesto, Athena |
    57|| `security-review` | CVE research → audit → fix loop | 1 | Etalides, Athena, Hefesto |
    58|| `research` | Pure knowledge gathering | None | Etalides |
    59|| `refactor` | Scope → implement → audit | 1 | Etalides, Hefesto, Athena |
    60|
    61|### Human-in-the-Loop (HITL)
    62|
    63|Workflows pause at decision points for user approval. The orchestrator presents findings conversationally and the user decides: `approve`, `reject`, `modify`, `confirm`, or `accept_risk`. Workflow state persists via AsyncSqliteSaver.
    64|
    65|---
    66|
    67|## Project Status
    68|
    69|**Current version:** v0.3.0 — External Audit Fixes
    70|
    71|| Component | Status | Description |
    72||-----------|--------|-------------|
    73|| Olympus MCP server | ✅ Working | `talk_to`, `discover`, `run_workflow` functional |
    74|| LangGraph workflows | ✅ Working | 6 canonical workflows with HITL gates |
    75|| AsyncSqliteSaver | ✅ Working | Persistent checkpointing across sessions |
    76|| Progress Watchdog | ✅ Working | Stall detection (no hard timeouts on LLM tasks) |
    77|| .eter/ project state | ✅ Working | Persistent project state across sessions |
    78|| SOUL.md convention | ✅ Working | 7-section structure, DRY execution context |
    79|| Skills architecture | ✅ Working | Shared external_dirs, single source of truth |
    80|| Daimon identity | ✅ Fixed | `--profile` flag ensures correct SOUL.md loading |
    81|| MCP tool propagation | ✅ Patched | Subagents receive Olympus tools via delegation |
    82|| ACP response collection | ✅ Fixed | Race condition resolved, thoughts recovery path |
    83|| Collaborative multi-turn | 🔜 Planned | Multi-turn Daimon sessions (MCP supports it, skill doesn't use it yet) |
    84|| Website landing page | ✅ Working | Static site in `website/` |
    85|
    86|---
    87|
    88|## Project Structure
    89|
    90|```
    91|Aether-Agents/
    92|├── home/                              ← HERMES_HOME root
    93|│   ├── skills/                        ← Shared skills (single source of truth)
    94|│   │   ├── aether-agents/             ← Framework skills (10 skills)
    95|│   │   ├── productivity/              ← Generic skill categories
    96|│   │   ├── research/
    97|│   │   └── ... (24 categories total)
    98|│   ├── profiles/                      ← Agent profiles (HERMES_HOME per agent)
    99|│   │   ├── hermes/                    ← Orchestrator (SOUL.md + .env.example + config.yaml.template)
   100|│   │   ├── ariadna/                   ← Project Manager
   101|│   │   ├── hefesto/                   ← Senior Developer
   102|│   │   ├── etalides/                  ← Web Researcher
   103|│   │   ├── daedalus/                  ← UX/UI Designer
   104|│   │   └── athena/                    ← Security Engineer
   105|│   ├── sessions/                      ← Auto-created by hermes
   106|│   └── logs/                          ← Auto-created by hermes
   107|│
   108|├── src/olympus/                       ← MCP server + workflow engine
   109|│   ├── server.py                      ← MCP server (tools: talk_to, discover, run_workflow)
   110|│   ├── acp_client.py                  ← ACP protocol client
   111|│   ├── discovery.py                   ← Agent profile discovery
   112|│   ├── registry.py                    ← Session tracking
   113|│   ├── config.py                      ← Olympus configuration
   114|│   └── workflows/                     ← LangGraph workflow engine
   115|│       ├── state.py                   ← WorkflowState TypedDict
   116|│       ├── nodes.py                   ← Node factories + HITL
   117|│       ├── definitions.py             ← 6 workflow graphs
   118|│       └── runner.py                  ← WorkflowRunner (invoke, resume)
   119|│
   120|├── website/                           ← Landing page
   121|├── scripts/                           ← Setup scripts
   122|├── .eter/                             ← Project state (gitignored, local)
   123|├── pyproject.toml                     ← Olympus package definition
   124|└── .gitignore
   125|```
   126|
   127|### Skills Architecture
   128|
   129|Skills live in ONE place: `home/skills/`. Each profile's `config.yaml` points to this shared directory via `skills.external_dirs`. No symlinks, no duplicates.
   130|
   131|- **Aether skills** (`home/skills/aether-agents/`): Custom framework skills for orchestration, workflow design, diagnostics, and agent creation
   132|- **Generic skills** (`home/skills/{category}/`): Standard hermes-agent skill categories (productivity, research, github, etc.)
   133|
   134|Each agent's SOUL.md references the skills relevant to their specialty.
   135|
   136|---
   137|
   138|## SOUL.md Convention
   139|
   140|All agent profiles follow a 7-section structure:
   141|
   142|1. **Identity** — who I am, eponym, role
   143|2. **Execution Context** — how I'm invoked, project root, session scope (DRY for 5 Daimons)
   144|3. **Core Responsibilities** — what I do
   145|4. **Limits** — what I MUST NOT do
   146|5. **Skills** — skills I load (with 1-line descriptions)
   147|6. **Output Format** — how I structure my responses
   148|7. **In Workflow Context** — how I operate inside LangGraph workflows
   149|
   150|---
   151|
   152|## Project State (`.eter/`)
   153|
   154|Every project uses `.eter/` for persistence:
   155|
   156|```
   157|PROJECT_ROOT/.eter/
   158|├── .hermes/        ← DESIGN.md (append-top v{N}) + PLAN.md (append-top Sprint{N})
   159|├── .ariadna/       ← CURRENT.md (overwrite) + LOG.md (append-bottom)
   160|├── .hefesto/       ← TASKS.md (overwrite with cycles)
   161|└── .etalides/      ← RESEARCH.md (append-bottom)
   162|```
   163|
   164|---
   165|
   166|## Installation
   167|
   168|```bash
   169|git clone https://github.com/DarkArty07/Aether-Agents.git
   170|cd Aether-Agents
   171|
   172|python3 -m venv venv
   173|source venv/bin/activate
   174|pip install -e .
   175|```
   176|
   177|### Configure environment
   178|
   179|```bash
   180|# Each profile needs API keys
   181|cp home/profiles/hermes/.env.example home/profiles/hermes/.env
   182|# Edit .env with your keys — supports any OpenAI-compatible provider
   183|```
   184|
   185|### Start
   186|
   187|```bash
   188|HERMES_HOME=/path/to/Aether-Agents/home hermes --profile hermes
   189|```
   190|
   191|---
   192|
   193|## Best Practices
   194|
   195|### 1. Read the Aether skills before coding
   196|
   197|When starting a new coding session, ask Hermes to load the Aether skills first. These contain project-specific conventions, workflow protocols, and known pitfalls that aren't obvious from the code alone. Without them, Hermes may miss routing rules, HITL checkpoints, or the delegation matrix.
   198|
   199|### 2. Populate USER.md before your first session
   200|
   201|Before doing meaningful work, fill out `home/profiles/hermes/memories/USER.md` (or let Hermes ask you). Include basics: your name, preferred language, coding style, tech stack, and project context. This lets Hermes personalize interactions and avoid assumptions about what you know or prefer.
   202|
   203|### 3. Use talk_to for design-phase opinions
   204|
   205|During the DESIGN phase, ask for specialist opinions through `talk_to()`. Each Daimon offers a unique lens:
   206|
   207|- **Etalides** — "Are there established patterns or libraries for this?"
   208|- **Daedalus** — "Is the user flow intuitive? What would the UI look like?"
   209|- **Athena** — "What are the security implications of this architecture?"
   210|- **Hefesto** — "Is this technically feasible? What are the implementation trade-offs?"
   211|
   212|Don't jump to CODE without consulting at least one Daimon during DESIGN.
   213|
   214|### 4. Let Hermes decide the workflow
   215|
   216|When a task needs multiple agents, tell Hermes *what* you want done — not *how* to orchestrate it. Hermes will choose the right Olympus workflow based on the task type:
   217|
   218|- New feature? → `feature` workflow (4 Daimons, 3 HITL gates)
   219|- Bug? → `bug-fix`
   220|- Security audit? → `security-review`
   221|- Pure research? → `research`
   222|- Refactor? → `refactor`
   223|- New project? → `project-init`
   224|
   225|Trying to manually chain `talk_to` calls loses context, skips approval gates, and has no error recovery. Trust the workflow engine.
   226|
   227|---
   228|
   229|## Documentation
   230|
   231|- **Olympus MCP**: [`src/olympus/README.md`](src/olympus/README.md) — API reference, HITL guide, pitfalls
   232|- **Home directory**: [`home/README.md`](home/README.md) — profiles, skills architecture, adding new Daimons
   233|- **Team playbook**: `home/skills/aether-agents/orchestration/SKILL.md` — 5-phase pipeline, decision matrix, assignment rules
   234|- **Workflow engine**: `home/skills/aether-agents/workflow-design/SKILL.md` — technical reference
   235|- **Diagnostics**: `home/skills/aether-agents/aether-diagnostics/SKILL.md` — health checks
   236|
   237|---
   238|
   239|## License
   240|
   241|MIT License. See [LICENSE](LICENSE) for details.