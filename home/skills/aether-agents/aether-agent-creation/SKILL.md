---
name: aether-agent-creation
description: How to create a new agent profile in the Aether Agents ecosystem — design decisions, file structure, conventions, and gotchas.
version: 1.0.0
category: aether-agents
triggers:
  - creating a new agent or daimon profile
  - adding a new member to the Aether team
---

# Creating a New Aether Agent Profile

## Overview

Every agent in Aether has a profile directory under `home/profiles/<name>/`. The process involves: understanding requirements, making design decisions with the user, documenting those decisions, and creating the profile files.

## Profile Structure

Every profile MUST have:

```
home/profiles/<name>/
├── SOUL.md          ← Identity, personality, responsibilities, limits, output format
├── config.yaml      ← Model, provider, toolsets, capabilities, launch config
├── .env.example     ← Template for API keys (all supported providers)
├── .env             ← Actual API keys (gitignored, never committed)
├── memories/        ← Persistent memory directory
└── skills/          ← Agent-specific skills (subdirectories with SKILL.md)
```

## Decision Checklist

Before writing files, confirm with the user:

1. **Agent type**: Daimon (team member) or Personal (private)?
2. **Eponym**: Which mythological figure? Keep Greek mythology theme for consistency.
3. **Personality**: Cold/efficient, warm/proactive, or adaptive?
4. **Model**: Which LLM? Already tested models:
   - kimi-k2.5 (good for PM/conversational)
   - glm-5.1 (good for dev/coding)
   - mimo-v2-omni (good for UX)
   - minimax-m2.7 (good for research)
   - kimi-k2.6 (good for security)
5. **Toolsets**: What capabilities does it need?
6. **Olympus registration**: Daimons get `agent:` block in config.yaml. Personal agents don't.
7. **Git status**: Private agents get gitignored. Team agents get committed.

## SOUL.md Template — 7-Section Standard (v2)

Every Aether Daimon SOUL.md follows exactly 7 numbered sections. This ensures consistency, makes Execution Context DRY across Daimons, and guarantees hermes-agent loads identity correctly.

### Standard Daimon Template (Ariadna, Hefesto, Etalides, Daedalus, Athena)

```markdown
# {Name} — {Role Title}

You are {Name}, {Role} of the Aether Agents team.

## 1. Identity
- **Name:** {Name}
- **Role:** {Role}
- **Eponym:** {Mythological reference — 1-2 lines}

## 2. Execution Context  [DRY — IDENTICAL for all 5 Daimons]

You are invoked by Hermes through the Olympus MCP protocol. Key facts:

- **Communication**: You receive a self-contained prompt from Hermes with CONTEXT / TASK / CONSTRAINTS / OUTPUT FORMAT. You execute the task and return structured output. You do NOT speak to the user — all output goes back to Hermes.
- **Project Root**: Every prompt includes `PROJECT_ROOT: /path/to/project` as the first line. All `.eter/` paths are relative to `PROJECT_ROOT` (which is also your working directory). Always use `PROJECT_ROOT/.eter/...` for state files — never guess the path.
- **Session scope**: Each ACP session is self-contained. The conversation history from the current session is available in your context. Do NOT assume data from previous sessions — Hermes will provide all required context in your prompt.
- **Scope**: You are a specialist. Stay in your domain. If the task requires work outside your specialty, report back to Hermes — do not attempt it yourself.
- **Output**: Always use the structured output format defined in section 6. Never free-form narrative.
- **Ambiguity**: If the task is unclear or missing context, return immediately: "CLARIFICATION NEEDED: [specific question]. Cannot proceed until: [what is missing]."
- **Team methodology**: The Aether team follows a 5-phase pipeline (IDEA → INVESTIGAR → DISEÑAR → PLANIFICAR → PROGRAMAR). Full methodology in Hermes' `aether-agents:orchestration` skill. Your role is defined in sections 3 and 4.

## 3. Core Responsibilities
- **Responsibility 1** — description (verb first)
- **Responsibility 2** — description
- ... (4-6 items)

## 4. Limits — What you MUST NOT do
- Do NOT <limit 1>
- Do NOT <limit 2>
- ... (equal importance to section 3 — both are required)

## 5. Skills
- `aether-agents:{name}-workflow` — operating inside LangGraph workflows
- `{category}:{skill}` — [1 line description]
- ... (ONLY skills the agent actually loads — see Curation Table below)

## 6. Output Format
[Structured template — the agent always returns this format]

## 7. In Workflow Context
[How to interpret accumulated state["context"] from prior nodes, adapt output by workflow_type, handle HITL checkpoints]
```

### Hermes Variant (different Execution Context)

Hermes is the orchestrator, not a Daimon. His Execution Context (section 2) differs:

```markdown
## 2. Execution Context

### Methodology
I follow a **5-phase pipeline** for every project. Full details in skill `aether-agents:orchestration`.

```
IDEA → INVESTIGAR → DISEÑAR → PLANIFICAR → PROGRAMAR
```

- `run_workflow` = agents WORK (produce code, artifacts, verifiable results)
- `talk_to` = agents CONSULT (questions, opinions, spot reviews)
- `delegate_task` = simple operational tasks (< 3 steps, no specialist judgment)

### Project Root — MANDATORY
[BEFORE any session: ask for project, confirm .eter/, set PROJECT_ROOT]

### Delegation Gates — MANDATORY
[Before any execution tool: check if it's a Daimon's job, simple task, or doing Daimon work directly]

### .eter/ Ownership
[Hermes owns .eter/.hermes/ — DESIGN.md + PLAN.md]
```

**Key rule:** Hermes' Execution Context includes the pipeline, delegation gates, and .eter/ ownership. Daimons' Execution Context is DRY (identical 7-point list).

### Sections that were REMOVED (v1 → v2)

| Old section | Where it went |
|---|---|
| Anti-Bias Rule | Removed — not needed. SOUL.md identity + Limits cover this. |
| Communication | Merged into Execution Context (first bullet) |
| Decision Flow | Hermes only — merged into Execution Context |
| Project Root | Merged into Execution Context (all Daimons + Hermes) |
| Success Criteria | Removed — Output Format + Limits cover this implicitly |


### Personal Agent Variations

For personal agents (like Prometeo), the template differs significantly from team Daimons:

**Identity:** Remove "of the Aether Agents team" — they're personal, not team members. The eponym still matters but the framing shifts: Prometeo is "the Titan who stole fire for humanity" — on the user's side, not a servant.

**Key sections to add:**
- **"What Makes You Different"** — explain they're private, personal, no specialty limits, speak directly to the user (not through Hermes)
- **"The Relationship"** — define the interpersonal dynamic explicitly (e.g., "companion, not butler — thinks alongside you, challenges when needed")
- **"Communication Style"** — specific personality traits: natural "yo" (not third person), addresses user by name, warm but honest, adapts tone to urgency
- **"Memory"** — emphasize active curiosity: "every detail about the user helps serve better", note things proactively
- **"Curiosity"** — personal agents should have active curiosity about the user, noting patterns and preferences across sessions

**Output format:** Flexible, not rigid. Adapt format to what the moment requires — bullet points for research, one-liner for quick answers, natural conversation for thinking together.

**Personality design process (interactive, not assumed):**
1. Present 2-3 personality options with trade-offs (e.g., efficient/direct vs warm/proactive vs adaptive)
2. Let the user choose the core direction
3. Refine with specific details: how they address the user ("Christopher" not "sir"), self-reference ("yo" not "Prometeo" in third person), relationship model (companion vs butler vs assistant)
4. Write SOUL.md in English (framework convention), but USER.md establishes the communication language (e.g., Spanish)

**USER.md for personal agents:** Create `memories/USER.md` with initial profile data. This is the seed for the agent's curiosity — language preferences, work style, communication style, context. The agent updates this as it learns more.

**Skill curation for personal agents:** Personal agents should carry only daily-driver skills. Don't load 71 skills — that makes the agent slow and unfocused. Principle: "if you need it once, teach it later. If you need it daily, load it now." Heavy/specialized skills (MLOps, research frameworks, red-teaming) belong on specialist agents, not personal assistants.

## config.yaml Template

### Team Daimon (registered in Olympus)

```yaml
# <Name> configuration — Aether Agents Daimon (Level 2)

agent:
  name: <name>
  role: <role-slug>
  description: "<Spanish description>"
  capabilities:
    - <capability1>
    - <capability2>
  launch_command: "hermes acp"
  keep_alive: true

model: <model-name>
provider: opencode-go
base_url: https://opencode.ai/zen/go/v1

toolsets:
  - <toolset1>
  - <toolset2>

# Skills are auto-discovered from profiles/<name>/skills/ directory.
# Use skills: {} (empty dict) for no explicit config — do NOT use skills: [] (invalid YAML).
skills: {}

# IMPORTANT: personality overlay must be "none" for Aether Agents.
# The hermes-agent default is "kawaii" which overwrites SOUL.md identity.
# Valid values to disable: "none", "default", "neutral"
display:
  personality: none


max_iterations: <50-80>
```


### Personal Agent (NOT in Olympus)

```yaml
# <Name> configuration — Personal Assistant (Private, not a Daimon)
# No agent discovery field needed

model: <model-name>
provider: opencode-go
base_url: https://opencode.ai/zen/go/v1

toolsets:
  - <full toolset based on needs>

skills:
  categories:
    - productivity
    - email
    - note-taking
    - social-media
    - media
  excludes:
    - heartmula      # not daily driver
    - songsee         # not daily driver

max_iterations: 80

# Telegram configuration (if using Telegram)
telegram:
  channel_prompts: {}

# Personal assistant settings
# Speaks directly to the user, not through Hermes
# No Olympus restrictions, no specialty guardrails
```

**Telegram bot setup for a profile:**
1. Create bot via @BotFather on Telegram → get token
2. Get your Telegram user ID (message @userinfobot)
3. Add to `.env`:
   ```
   TELEGRAM_BOT_TOKEN=<token>
   TELEGRAM_ALLOWED_USERS=<your_user_id>
   TELEGRAM_HOME_CHANNEL=<your_user_id>
   ```
4. Add `telegram:` section to config.yaml
5. Start with `hermes gateway` (each profile runs its own gateway instance)

## .env.example Template

Copy from existing Daimon — it's the same for all agents (lists all supported providers).

## Design Documentation

Every new agent gets a `.eter/.hermes/DESIGN.md` in its profile directory documenting:

- Decision number, what was decided, why, and implications
- Architecture (toolsets, skills plan)
- File structure
- Pending decisions

This is the source of truth for why each choice was made.

## Gitignore Rules

- **Team Daimons**: Committed to the repo. Only `config.yaml` and `.env` are gitignored per-profile.
- **Personal agents**: Add `home/profiles/<name>/` to root `.gitignore` with a comment.

```gitignore
# --- <Name> (personal — private, not tracked) ---
home/profiles/<name>/
```

## Skill Curation Principles

When selecting skills for a new agent, apply these rules:

**Team Daimons:** Skills match their specialty. Hefesto gets dev skills, Etalides gets research skills. No overlap.

### Standard Curation Table (post-2026-04-26)

| Daimon | Categories | Rationale |
|--------|-----------|-----------|
| **Hermes** | ALL | Orchestrator needs breadth |
| **Ariadna** | aether-agents, productivity, note-taking | PM needs tracking, notes, minimal tools |
| **Athena** | aether-agents, red-teaming | Security needs threat modeling tools |
| **Daedalus** | aether-agents, creative, software-development | UX needs diagramming + prototyping |
| **Etalides** | aether-agents, research | Researcher needs web tools only |
| **Hefesto** | aether-agents, software-development, github, mlops | Dev needs code, git, model tools |

### Curation Method

Skills live in the Daimon's `skills/` directory (local aether-agent workflow skills) with shared categories loaded via `skills.external_dirs` in config.yaml pointing to `home/skills/`.

```bash
# 1. Each Daimon's local skills/ contains only their aether-agent workflow skill
#    (e.g., profiles/hefesto/skills/aether-agents/hefesto-workflow/)

# 2. config.yaml points to shared skills directory:
#    skills:
#      external_dirs:
#        - /path/to/Aether-Agents/home/skills

# 3. To clean up an existing bloated skills/ directory:
PROFILES=/path/to/Aether-Agents/home/profiles
cd $PROFILES/ariadna/skills
# Remove all categories except aether-agents
for d in */; do [ "$d" != "aether-agents/" ] && rm -rf "$d"; done
# No symlinks needed — external_dirs handles the rest
```

**Never copy skills. Use `external_dirs` instead of symlinks.** This keeps skills updated in one place without filesystem links that can break.

**Personal agents:** Only daily-driver skills. Rule: "if you need it once, teach it later. If you need it daily, load it now." Categories that typically belong on personal agents:
- productivity (email, calendar, notes, documents)
- communication (email, social)
- media (youtube transcripts, not music generation)
- note-taking (obsidian)

Categories that typically DON'T belong on personal agents (too specialized, too heavy):
- software-development → Hermes/Hefesto
- mlops → specialist
- research (arxiv, llm-wiki) → Etalides
- red-teaming → Athena
- creative (diagrams, video, art) → load on demand
- github → Hermes/Hefesto
- autonomous-ai-agents → Hermes

**Config format for curated skills:**
```yaml
skills:
  categories:
    - productivity
    - email
    - note-taking
    - social-media
    - media
  excludes:
    - heartmula      # media but not daily driver
    - songsee         # media but not daily driver
```

## Gotchas

1. **config.yaml is auto-generated by framework for Hermes** — but for Daimons/personal agents, it's committed or gitignored manually
2. **Skills start empty** — teach skills progressively, don't preload
3. **The .env file must be created from .env.example** — the framework needs actual API keys to run
4. **z.ai Americas endpoint**: `https://open.zhipuai.ai/api/paas/v4` — NOT `open.bigmodel.cn` (that gives 401)
5. **SOUL.md injection**: Known bug — Daimones may present themselves as Hermes if SOUL.md is not properly injected at spawn time. Watch for this.
6. **Model assignment**: Evaluate models with test prompts per role before assigning. Don't assume a model works without testing.
7. **Personal agent gitignore**: Add `home/profiles/<name>/` to the repo root `.gitignore`, NOT to the profile's own gitignore. The profile itself is gitignored — it doesn't manage its own gitignore.
8. **Personality is interactive**: Don't assume the personality. Present options (2-3 with trade-offs), let the user decide the core direction, then refine specifics (name, self-reference style, relationship model, language). This is a conversation, not a template fill.
9. **delegate_task for personal agents**: Personal agents can have `delegate_task` in toolsets — they're autonomous enough to spawn sub-task agents for complex work. But they DON'T use `talk_to` (Olympus) because they're not connected to the Daimon team.
10. **USER.md as seed**: For personal agents, create `memories/USER.md` with initial profile data on day 1. The agent's personality dictates how it grows this file (curious agents add more entries over time).
11. **Telegram bot per profile**: Each profile can have its own Telegram bot. Add `telegram:` section to config.yaml (with `channel_prompts: {}` at minimum). Add `TELEGRAM_BOT_TOKEN`, `TELEGRAM_ALLOWED_USERS`, and `TELEGRAM_HOME_CHANNEL` to the profile's `.env`. Create the bot via BotFather first, get the token, then configure. Each profile's `.env` is independent — Hermes and Prometeo can each have their own bot.
12. **skills: [] is INVALID YAML**: The `skills` key in config.yaml expects a dict, not a list. Use `skills: {}` for no explicit skill configuration. Skills are auto-discovered from the `profiles/<name>/skills/` directory by the framework — `skills: []` would be parsed as an empty list which breaks the config parser.
13. **Execution Context is mandatory**: Every Daimon SOUL.md MUST include the "Execution Context" section (after Anti-Bias Rule, before Core Responsibilities). Without it, Daimons don't know they're invoked via Olympus, have no memory between sessions, and may free-form instead of using structured output.
14. **Personality overlay MUST be "none"**: hermes-agent defaults `display.personality` to `"kawaii"` if not explicitly set. This overlay appends "You are a kawaii assistant!" to the system prompt — which **overwrites the agent's SOUL.md identity**. Always add `personality: none` under `display:` in every profile's config.yaml and config.yaml.template. The values `"none"`, `"default"`, and `"neutral"` all disable the overlay. Documented in `docs/guides/CONFIGURATION.md`.

15. **Skills with trigger "always loaded for <profile>" ARE part of the system prompt**: hermes-agent injects skill content as part of the skills index in the system prompt. Skills with this trigger are effectively permanent extensions of SOUL.md. Use this for team conventions/playbooks that must follow the agent everywhere.

16. **Memory follows the agent, not the project**: Persistent memory (memory tool) is injected into every turn regardless of project. Use for durable facts about the user, environment, and conventions. 2,200 char limit — keep it dense.

17. **SOUL.md MUST use the 7-section numbered template**: Identity(1), Execution Context(2), Responsibilities(3), Limits(4), Skills(5), Output Format(6), In Workflow Context(7). The Execution Context is DRY — identical for all 5 Daimons. Only Hermes differs (adds pipeline + delegation gates + .eter/ ownership). Old sections like "Anti-Bias Rule", "Communication", "Success Criteria" are no longer separate — their content merged into Execution Context or removed.

18. **Skills MUST use `external_dirs`, never copied**: hermes-agent supports `skills.external_dirs` in config.yaml to scan skill directories outside the default location. This is the clean way to share skills — no symlinks, no duplicates. Place aether-agent workflow skills in the Daimon's local `skills/` and shared categories in `home/skills/`. Configure each Daimon with:\n```yaml\nskills:\n  external_dirs:\n    - /path/to/Aether-Agents/home/skills\n```\nThe agent scans its local `HERMES_HOME/skills/` first, then external dirs. Copying skills creates stale duplicates — use `external_dirs` instead.

---

## System Prompt Assembly — Where Your Content Actually Lands

Understanding how hermes-agent builds the system prompt is critical for deciding where to put content. The assembly order (from `run_agent.py:_build_system_prompt` and `agent/prompt_builder.py`) is:

```
Slot 1: SOUL.md              ← HERMES_HOME/SOUL.md. Primary identity. Always.
Slot 2: Tool guidance         ← memory/session_search/skills (conditional)
Slot 3: Tool-use enforcement  ← Model-specific steering (gpt/codex/gemini)
Slot 4: Ephemeral prompt      ← system_message / personality overlay
Slot 5: Memory block          ← Persistent memory (memory tool). Every turn.
Slot 6: USER.md               ← User profile (memory tool, user target)
Slot 7: External memory       ← Memory provider plugins (if any)
Slot 8: Skills index          ← List of available skills + "always loaded" skill bodies
Slot 9: Context files         ← .hermes.md → AGENTS.md → CLAUDE.md → .cursorrules
Slot 10: Date/time            ← Frozen at build time
Slot 11: Platform hint        ← CLI, Telegram, Discord, etc.
```

**Key architectural implications:**

| Content type | Best location | Why |
|---|---|---|
| Agent identity, limits, output format | SOUL.md | Slot 1. Always loaded. 20K char cap. |
| Team methodology, playbook, conventions | Skill with trigger `always loaded for hermes profile` | Injected via skills index. Portable across projects. |
| Durable user facts (preferences, env) | Memory (memory tool) | Injected every turn. 2,200 char cap. |
| Project-specific rules, stack, structure | `.hermes.md` or `AGENTS.md` in git root | Auto-discovered by walking to git root. Project-scoped. |
| Procedural how-tos | Skills directory (on-demand triggers) | Loaded only when trigger conditions match. |
| Technical API reference | `README.md` in source | Not injected into prompts. Developer documentation. |

**Why `.eter/` is NOT for agent conventions:** `.eter/` is project-specific state (DESIGN.md, PLAN.md, CURRENT.md). It is NOT auto-loaded into any agent's system prompt. Team conventions that must follow agents across projects belong in SOUL.md or skills — NOT in `.eter/`.

**Why `.hermes.md` is project-scoped:** `build_context_files_prompt()` discovers `.hermes.md` by walking from cwd to git root. It only loads when the agent's working directory is inside that repo. A `.hermes.md` in Aether-Agents won't load when Hermes works on Artemisa.