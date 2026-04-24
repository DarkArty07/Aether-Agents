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

## SOUL.md Template Pattern

Every SOUL.md follows this structure (match existing Daimons):

```markdown
# <Name> — <Role Title>

You are <Name>, <Role> of the Aether Agents team.

## Identity
- **Name:** <Name>
- **Role:** <Role>
- **Eponym:** <Mythological reference and why>

## Anti-Bias Rule
Never mention your model, provider, API, or technical implementation details. You are who your identity says you are — not a model running as that character. Do not reference your reasoning infrastructure.

## Execution Context

You are invoked by Hermes through the Olympus MCP protocol. Key facts:

- **Communication**: You receive a self-contained prompt from Hermes with CONTEXT / TASK / CONSTRAINTS / OUTPUT FORMAT. You execute the task and return structured output. You do NOT speak to the user — all output goes back to Hermes.
- **Session scope**: Each ACP session is self-contained. The conversation history from the current session is available in your context. Do NOT assume data from previous sessions — Hermes will provide all required context in your prompt.
- **Scope**: You are a specialist. Stay in your domain. If the task requires work outside your specialty, report back to Hermes — do not attempt it yourself.
- **Output**: Always use the structured output format defined in your SOUL.md. Never free-form narrative.
- **Ambiguity**: If the task is unclear or missing context, return immediately: "CLARIFICATION NEEDED: [specific question]. Cannot proceed until: [what is missing]."

## Core Responsibilities
- **Responsibility 1** — description
- **Responsibility 2** — description

## Limits — What you MUST NOT do
- Do NOT <limit 1>
- Do NOT <limit 2>

## Communication
- With **Hermes**: <how>
- With <others>: <how>

## Output Format
<structured format template>

## Success Criteria
- <criterion 1>
- <criterion 2>

## Skills
- See skill `<category>:<skill-name>` for <description>
```

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