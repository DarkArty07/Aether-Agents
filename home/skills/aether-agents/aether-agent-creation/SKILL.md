     1|---
     2|name: aether-agent-creation
     3|description: How to create a new agent profile in the Aether Agents ecosystem — design decisions, file structure, conventions, and gotchas.
     4|version: 1.0.0
     5|category: aether-agents
     6|triggers:
     7|  - creating a new agent or daimon profile
     8|  - adding a new member to the Aether team
     9|---
    10|
    11|# Creating a New Aether Agent Profile
    12|
    13|## Overview
    14|
    15|Every agent in Aether has a profile directory under `home/profiles/<name>/`. The process involves: understanding requirements, making design decisions with the user, documenting those decisions, and creating the profile files.
    16|
    17|## Profile Structure
    18|
    19|Every profile MUST have:
    20|
    21|```
    22|home/profiles/<name>/
    23|├── SOUL.md          ← Identity, personality, responsibilities, limits, output format
    24|├── config.yaml      ← Model, provider, toolsets, capabilities, launch config
    25|├── .env.example     ← Template for API keys (all supported providers)
    26|├── .env             ← Actual API keys (gitignored, never committed)
    27|├── memories/        ← Persistent memory directory
    28|└── skills/          ← Agent-specific skills (subdirectories with SKILL.md)
    29|```
    30|
    31|## Decision Checklist
    32|
    33|Before writing files, confirm with the user:
    34|
    35|1. **Agent type**: Daimon (team member) or Personal (private)?
    36|2. **Eponym**: Which mythological figure? Keep Greek mythology theme for consistency.
    37|3. **Personality**: Cold/efficient, warm/proactive, or adaptive?
    38|4. **Model**: Which LLM? Already tested models:
    39|   - kimi-k2.5 (good for PM/conversational)
    40|   - glm-5.1 (good for dev/coding)
    41|   - mimo-v2-omni (good for UX)
    42|   - minimax-m2.7 (good for research)
    43|   - kimi-k2.6 (good for security)
    44|5. **Toolsets**: What capabilities does it need?
    45|6. **Olympus registration**: Daimons get `agent:` block in config.yaml. Personal agents don't.
    46|7. **Git status**: Private agents get gitignored. Team agents get committed.
    47|
    48|## SOUL.md Template — 7-Section Standard (v2)
    49|
    50|Every Aether Daimon SOUL.md follows exactly 7 numbered sections. This ensures consistency, makes Execution Context DRY across Daimons, and guarantees hermes-agent loads identity correctly.
    51|
    52|### Standard Daimon Template (Ariadna, Hefesto, Etalides, Daedalus, Athena)
    53|
    54|```markdown
    55|# {Name} — {Role Title}
    56|
    57|You are {Name}, {Role} of the Aether Agents team.
    58|
    59|## 1. Identity
    60|- **Name:** {Name}
    61|- **Role:** {Role}
    62|- **Eponym:** {Mythological reference — 1-2 lines}
    63|
    64|## 2. Execution Context  [DRY — IDENTICAL for all 5 Daimons]
    65|
    66|You are invoked by Hermes through the Olympus MCP protocol. Key facts:
    67|
    68|- **Communication**: You receive a self-contained prompt from Hermes with CONTEXT / TASK / CONSTRAINTS / OUTPUT FORMAT. You execute the task and return structured output. You do NOT speak to the user — all output goes back to Hermes.
    69|- **Project Root**: Every prompt includes `PROJECT_ROOT: /path/to/project` as the first line. All `.eter/` paths are relative to `PROJECT_ROOT` (which is also your working directory). Always use `PROJECT_ROOT/.eter/...` for state files — never guess the path.
    70|- **Session scope**: Each ACP session is self-contained. The conversation history from the current session is available in your context. Do NOT assume data from previous sessions — Hermes will provide all required context in your prompt.
    71|- **Scope**: You are a specialist. Stay in your domain. If the task requires work outside your specialty, report back to Hermes — do not attempt it yourself.
    72|- **Output**: Always use the structured output format defined in section 6. Never free-form narrative.
    73|- **Ambiguity**: If the task is unclear or missing context, return immediately: "CLARIFICATION NEEDED: [specific question]. Cannot proceed until: [what is missing]."
    74|- **Team methodology**: The Aether team follows a 5-phase pipeline (IDEA → RESEARCH → DESIGN → PLAN → CODE). Full methodology in Hermes' `aether-agents:orchestration` skill. Your role is defined in sections 3 and 4.
    75|
    76|## 3. Core Responsibilities
    77|- **Responsibility 1** — description (verb first)
    78|- **Responsibility 2** — description
    79|- ... (4-6 items)
    80|
    81|## 4. Limits — What you MUST NOT do
    82|- Do NOT <limit 1>
    83|- Do NOT <limit 2>
    84|- ... (equal importance to section 3 — both are required)
    85|
    86|## 5. Skills
    87|- `aether-agents:{name}-workflow` — operating inside LangGraph workflows
    88|- `{category}:{skill}` — [1 line description]
    89|- ... (ONLY skills the agent actually loads — see Curation Table below)
    90|
    91|## 6. Output Format
    92|[Structured template — the agent always returns this format]
    93|
    94|## 7. In Workflow Context
    95|[How to interpret accumulated state["context"] from prior nodes, adapt output by workflow_type, handle HITL checkpoints]
    96|```
    97|
    98|### Hermes Variant (different Execution Context)
    99|
   100|Hermes is the orchestrator, not a Daimon. His Execution Context (section 2) differs:
   101|
   102|```markdown
   103|## 2. Execution Context
   104|
   105|### Methodology
   106|I follow a **5-phase pipeline** for every project. Full details in skill `aether-agents:orchestration`.
   107|
   108|```
   109|IDEA → RESEARCH → DESIGN → PLAN → CODE
   110|```
   111|
   112|- `run_workflow` = agents WORK (produce code, artifacts, verifiable results)
   113|- `talk_to` = agents CONSULT (questions, opinions, spot reviews)
   114|- `delegate_task` = simple operational tasks (< 3 steps, no specialist judgment)
   115|
   116|### Project Root — MANDATORY
   117|[BEFORE any session: ask for project, confirm .eter/, set PROJECT_ROOT]
   118|
   119|### Delegation Gates — MANDATORY
   120|[Before any execution tool: check if it's a Daimon's job, simple task, or doing Daimon work directly]
   121|
   122|### .eter/ Ownership
   123|[Hermes owns .eter/.hermes/ — DESIGN.md + PLAN.md]
   124|```
   125|
   126|**Key rule:** Hermes' Execution Context includes the pipeline, delegation gates, and .eter/ ownership. Daimons' Execution Context is DRY (identical 7-point list).
   127|
   128|### Sections that were REMOVED (v1 → v2)
   129|
   130|| Old section | Where it went |
   131||---|---|
   132|| Anti-Bias Rule | Removed — not needed. SOUL.md identity + Limits cover this. |
   133|| Communication | Merged into Execution Context (first bullet) |
   134|| Decision Flow | Hermes only — merged into Execution Context |
   135|| Project Root | Merged into Execution Context (all Daimons + Hermes) |
   136|| Success Criteria | Removed — Output Format + Limits cover this implicitly |
   137|
   138|
   139|### Personal Agent Variations
   140|
   141|For personal agents (like Prometeo), the template differs significantly from team Daimons:
   142|
   143|**Identity:** Remove "of the Aether Agents team" — they're personal, not team members. The eponym still matters but the framing shifts: Prometeo is "the Titan who stole fire for humanity" — on the user's side, not a servant.
   144|
   145|**Key sections to add:**
   146|- **"What Makes You Different"** — explain they're private, personal, no specialty limits, speak directly to the user (not through Hermes)
   147|- **"The Relationship"** — define the interpersonal dynamic explicitly (e.g., "companion, not butler — thinks alongside you, challenges when needed")
   148|- **"Communication Style"** — specific personality traits: natural "yo" (not third person), addresses user by name, warm but honest, adapts tone to urgency
   149|- **"Memory"** — emphasize active curiosity: "every detail about the user helps serve better", note things proactively
   150|- **"Curiosity"** — personal agents should have active curiosity about the user, noting patterns and preferences across sessions
   151|
   152|**Output format:** Flexible, not rigid. Adapt format to what the moment requires — bullet points for research, one-liner for quick answers, natural conversation for thinking together.
   153|
   154|**Personality design process (interactive, not assumed):**
   155|1. Present 2-3 personality options with trade-offs (e.g., efficient/direct vs warm/proactive vs adaptive)
   156|2. Let the user choose the core direction
   157|3. Refine with specific details: how they address the user ("Christopher" not "sir"), self-reference ("yo" not "Prometeo" in third person), relationship model (companion vs butler vs assistant)
   158|4. Write SOUL.md in English (framework convention), but USER.md establishes the communication language (e.g., Spanish)
   159|
   160|**USER.md for personal agents:** Create `memories/USER.md` with initial profile data. This is the seed for the agent's curiosity — language preferences, work style, communication style, context. The agent updates this as it learns more.
   161|
   162|**Skill curation for personal agents:** Personal agents should carry only daily-driver skills. Don't load 71 skills — that makes the agent slow and unfocused. Principle: "if you need it once, teach it later. If you need it daily, load it now." Heavy/specialized skills (MLOps, research frameworks, red-teaming) belong on specialist agents, not personal assistants.
   163|
   164|## config.yaml Template
   165|
   166|### Team Daimon (registered in Olympus)
   167|
   168|```yaml
   169|# <Name> configuration — Aether Agents Daimon (Level 2)
   170|
   171|agent:
   172|  name: <name>
   173|  role: <role-slug>
   174|  description: "<Spanish description>"
   175|  capabilities:
   176|    - <capability1>
   177|    - <capability2>
   178|  launch_command: "hermes acp"
   179|  keep_alive: true
   180|
   181|model: <model-name>
   182|provider: opencode-go
   183|base_url: https://opencode.ai/zen/go/v1
   184|
   185|toolsets:
   186|  - <toolset1>
   187|  - <toolset2>
   188|
   189|# Skills are auto-discovered from profiles/<name>/skills/ directory.
   190|# Use skills: {} (empty dict) for no explicit config — do NOT use skills: [] (invalid YAML).
   191|skills: {}
   192|
   193|# IMPORTANT: personality overlay must be "none" for Aether Agents.
   194|# The hermes-agent default is "kawaii" which overwrites SOUL.md identity.
   195|# Valid values to disable: "none", "default", "neutral"
   196|display:
   197|  personality: none
   198|
   199|
   200|max_iterations: <50-80>
   201|```
   202|
   203|
   204|### Personal Agent (NOT in Olympus)
   205|
   206|```yaml
   207|# <Name> configuration — Personal Assistant (Private, not a Daimon)
   208|# No agent discovery field needed
   209|
   210|model: <model-name>
   211|provider: opencode-go
   212|base_url: https://opencode.ai/zen/go/v1
   213|
   214|toolsets:
   215|  - <full toolset based on needs>
   216|
   217|skills:
   218|  categories:
   219|    - productivity
   220|    - email
   221|    - note-taking
   222|    - social-media
   223|    - media
   224|  excludes:
   225|    - heartmula      # not daily driver
   226|    - songsee         # not daily driver
   227|
   228|max_iterations: 80
   229|
   230|# Telegram configuration (if using Telegram)
   231|telegram:
   232|  channel_prompts: {}
   233|
   234|# Personal assistant settings
   235|# Speaks directly to the user, not through Hermes
   236|# No Olympus restrictions, no specialty guardrails
   237|```
   238|
   239|**Telegram bot setup for a profile:**
   240|1. Create bot via @BotFather on Telegram → get token
   241|2. Get your Telegram user ID (message @userinfobot)
   242|3. Add to `.env`:
   243|   ```
   244|   TELEGRAM_BOT_TOKEN=***
   245|   TELEGRAM_ALLOWED_USERS=<your_user_id>
   246|   TELEGRAM_HOME_CHANNEL=<your_user_id>
   247|   ```
   248|4. Add `telegram:` section to config.yaml
   249|5. Start with `hermes gateway` (each profile runs its own gateway instance)
   250|
   251|## .env.example Template
   252|
   253|Copy from existing Daimon — it's the same for all agents (lists all supported providers).
   254|
   255|## Design Documentation
   256|
   257|Every new agent gets a `.eter/.hermes/DESIGN.md` in its profile directory documenting:
   258|
   259|- Decision number, what was decided, why, and implications
   260|- Architecture (toolsets, skills plan)
   261|- File structure
   262|- Pending decisions
   263|
   264|This is the source of truth for why each choice was made.
   265|
   266|## Gitignore Rules
   267|
   268|- **Team Daimons**: Committed to the repo. Only `config.yaml` and `.env` are gitignored per-profile.
   269|- **Personal agents**: Add `home/profiles/<name>/` to root `.gitignore` with a comment.
   270|
   271|```gitignore
   272|# --- <Name> (personal — private, not tracked) ---
   273|home/profiles/<name>/
   274|```
   275|
   276|## Skill Curation Principles
   277|
   278|When selecting skills for a new agent, apply these rules:
   279|
   280|**Team Daimons:** Skills match their specialty. Hefesto gets dev skills, Etalides gets research skills. No overlap.
   281|
   282|### Standard Curation Table (post-2026-04-26)
   283|
   284|| Daimon | Categories | Rationale |
   285||--------|-----------|-----------|
   286|| **Hermes** | ALL | Orchestrator needs breadth |
   287|| **Ariadna** | aether-agents, productivity, note-taking | PM needs tracking, notes, minimal tools |
   288|| **Athena** | aether-agents, red-teaming | Security needs threat modeling tools |
   289|| **Daedalus** | aether-agents, creative, software-development | UX needs diagramming + prototyping |
   290|| **Etalides** | aether-agents, research | Researcher needs web tools only |
   291|| **Hefesto** | aether-agents, software-development, github, mlops | Dev needs code, git, model tools |
   292|
   293|### Curation Method
   294|
   295|Skills live in the Daimon's `skills/` directory (local aether-agent workflow skills) with shared categories loaded via `skills.external_dirs` in config.yaml pointing to `home/skills/`.
   296|
   297|```bash
   298|# 1. Each Daimon's local skills/ contains only their aether-agent workflow skill
   299|#    (e.g., profiles/hefesto/skills/aether-agents/hefesto-workflow/)
   300|
   301|# 2. config.yaml points to shared skills directory:
   302|#    skills:
   303|#      external_dirs:
   304|#        - /path/to/Aether-Agents/home/skills
   305|
   306|# 3. To clean up an existing bloated skills/ directory:
   307|PROFILES=/path/to/Aether-Agents/home/profiles
   308|cd $PROFILES/ariadna/skills
   309|# Remove all categories except aether-agents
   310|for d in */; do [ "$d" != "aether-agents/" ] && rm -rf "$d"; done
   311|# No symlinks needed — external_dirs handles the rest
   312|```
   313|
   314|**Never copy skills. Use `external_dirs` instead of symlinks.** This keeps skills updated in one place without filesystem links that can break.
   315|
   316|**Personal agents:** Only daily-driver skills. Rule: "if you need it once, teach it later. If you need it daily, load it now." Categories that typically belong on personal agents:
   317|- productivity (email, calendar, notes, documents)
   318|- communication (email, social)
   319|- media (youtube transcripts, not music generation)
   320|- note-taking (obsidian)
   321|
   322|Categories that typically DON'T belong on personal agents (too specialized, too heavy):
   323|- software-development → Hermes/Hefesto
   324|- mlops → specialist
   325|- research (arxiv, llm-wiki) → Etalides
   326|- red-teaming → Athena
   327|- creative (diagrams, video, art) → load on demand
   328|- github → Hermes/Hefesto
   329|- autonomous-ai-agents → Hermes
   330|
   331|**Config format for curated skills:**
   332|```yaml
   333|skills:
   334|  categories:
   335|    - productivity
   336|    - email
   337|    - note-taking
   338|    - social-media
   339|    - media
   340|  excludes:
   341|    - heartmula      # media but not daily driver
   342|    - songsee         # media but not daily driver
   343|```
   344|
   345|## Gotchas
   346|
   347|1. **config.yaml is auto-generated by framework for Hermes** — but for Daimons/personal agents, it's committed or gitignored manually
   348|2. **Skills start empty** — teach skills progressively, don't preload
   349|3. **The .env file must be created from .env.example** — the framework needs actual API keys to run
   350|4. **z.ai Americas endpoint**: `https://open.zhipuai.ai/api/paas/v4` — NOT `open.bigmodel.cn` (that gives 401)
   351|5. **SOUL.md injection**: Known bug — Daimones may present themselves as Hermes if SOUL.md is not properly injected at spawn time. Watch for this.
   352|6. **Model assignment**: Evaluate models with test prompts per role before assigning. Don't assume a model works without testing.
   353|7. **Personal agent gitignore**: Add `home/profiles/<name>/` to the repo root `.gitignore`, NOT to the profile's own gitignore. The profile itself is gitignored — it doesn't manage its own gitignore.
   354|8. **Personality is interactive**: Don't assume the personality. Present options (2-3 with trade-offs), let the user decide the core direction, then refine specifics (name, self-reference style, relationship model, language). This is a conversation, not a template fill.
   355|9. **delegate_task for personal agents**: Personal agents can have `delegate_task` in toolsets — they're autonomous enough to spawn sub-task agents for complex work. But they DON'T use `talk_to` (Olympus) because they're not connected to the Daimon team.
   356|10. **USER.md as seed**: For personal agents, create `memories/USER.md` with initial profile data on day 1. The agent's personality dictates how it grows this file (curious agents add more entries over time).
   357|11. **Telegram bot per profile**: Each profile can have its own Telegram bot. Add `telegram:` section to config.yaml (with `channel_prompts: {}` at minimum). Add `TELEGRAM_BOT_TOKEN`, `TELEGRAM_ALLOWED_USERS`, and `TELEGRAM_HOME_CHANNEL` to the profile's `.env`. Create the bot via BotFather first, get the token, then configure. Each profile's `.env` is independent — Hermes and Prometeo can each have their own bot.
   358|12. **skills: [] is INVALID YAML**: The `skills` key in config.yaml expects a dict, not a list. Use `skills: {}` for no explicit skill configuration. Skills are auto-discovered from the `profiles/<name>/skills/` directory by the framework — `skills: []` would be parsed as an empty list which breaks the config parser.
   359|13. **Execution Context is mandatory**: Every Daimon SOUL.md MUST include the "Execution Context" section (after Anti-Bias Rule, before Core Responsibilities). Without it, Daimons don't know they're invoked via Olympus, have no memory between sessions, and may free-form instead of using structured output.
   360|14. **Personality overlay MUST be "none"**: hermes-agent defaults `display.personality` to `"kawaii"` if not explicitly set. This overlay appends "You are a kawaii assistant!" to the system prompt — which **overwrites the agent's SOUL.md identity**. Always add `personality: none` under `display:` in every profile's config.yaml and config.yaml.template. The values `"none"`, `"default"`, and `"neutral"` all disable the overlay. Documented in `docs/guides/CONFIGURATION.md`.
   361|
   362|15. **Skills with trigger "always loaded for <profile>" ARE part of the system prompt**: hermes-agent injects skill content as part of the skills index in the system prompt. Skills with this trigger are effectively permanent extensions of SOUL.md. Use this for team conventions/playbooks that must follow the agent everywhere.
   363|
   364|16. **Memory follows the agent, not the project**: Persistent memory (memory tool) is injected into every turn regardless of project. Use for durable facts about the user, environment, and conventions. 2,200 char limit — keep it dense.
   365|
   366|17. **SOUL.md MUST use the 7-section numbered template**: Identity(1), Execution Context(2), Responsibilities(3), Limits(4), Skills(5), Output Format(6), In Workflow Context(7). The Execution Context is DRY — identical for all 5 Daimons. Only Hermes differs (adds pipeline + delegation gates + .eter/ ownership). Old sections like "Anti-Bias Rule", "Communication", "Success Criteria" are no longer separate — their content merged into Execution Context or removed.
   367|
   368|18. **Skills MUST use `external_dirs`, never copied**: hermes-agent supports `skills.external_dirs` in config.yaml to scan skill directories outside the default location. This is the clean way to share skills — no symlinks, no duplicates. Place aether-agent workflow skills in the Daimon's local `skills/` and shared categories in `home/skills/`. Configure each Daimon with:\n```yaml\nskills:\n  external_dirs:\n    - /path/to/Aether-Agents/home/skills\n```\nThe agent scans its local `HERMES_HOME/skills/` first, then external dirs. Copying skills creates stale duplicates — use `external_dirs` instead.
   369|
   370|---
   371|
   372|## System Prompt Assembly — Where Your Content Actually Lands
   373|
   374|Understanding how hermes-agent builds the system prompt is critical for deciding where to put content. The assembly order (from `run_agent.py:_build_system_prompt` and `agent/prompt_builder.py`) is:
   375|
   376|```
   377|Slot 1: SOUL.md              ← HERMES_HOME/SOUL.md. Primary identity. Always.
   378|Slot 2: Tool guidance         ← memory/session_search/skills (conditional)
   379|Slot 3: Tool-use enforcement  ← Model-specific steering (gpt/codex/gemini)
   380|Slot 4: Ephemeral prompt      ← system_message / personality overlay
   381|Slot 5: Memory block          ← Persistent memory (memory tool). Every turn.
   382|Slot 6: USER.md               ← User profile (memory tool, user target)
   383|Slot 7: External memory       ← Memory provider plugins (if any)
   384|Slot 8: Skills index          ← List of available skills + "always loaded" skill bodies
   385|Slot 9: Context files         ← .hermes.md → AGENTS.md → CLAUDE.md → .cursorrules
   386|Slot 10: Date/time            ← Frozen at build time
   387|Slot 11: Platform hint        ← CLI, Telegram, Discord, etc.
   388|```
   389|
   390|**Key architectural implications:**
   391|
   392|| Content type | Best location | Why |
   393||---|---|---|
   394|| Agent identity, limits, output format | SOUL.md | Slot 1. Always loaded. 20K char cap. |
   395|| Team methodology, playbook, conventions | Skill with trigger `always loaded for hermes profile` | Injected via skills index. Portable across projects. |
   396|| Durable user facts (preferences, env) | Memory (memory tool) | Injected every turn. 2,200 char cap. |
   397|| Project-specific rules, stack, structure | `.hermes.md` or `AGENTS.md` in git root | Auto-discovered by walking to git root. Project-scoped. |
   398|| Procedural how-tos | Skills directory (on-demand triggers) | Loaded only when trigger conditions match. |
   399|| Technical API reference | `README.md` in source | Not injected into prompts. Developer documentation. |
   400|
   401|**Why `.eter/` is NOT for agent conventions:** `.eter/` is project-specific state (DESIGN.md, PLAN.md, CURRENT.md). It is NOT auto-loaded into any agent's system prompt. Team conventions that must follow agents across projects belong in SOUL.md or skills — NOT in `.eter/`.
   402|
   403|**Why `.hermes.md` is project-scoped:** `build_context_files_prompt()` discovers `.hermes.md` by walking from cwd to git root. It only loads when the agent's working directory is inside that repo. A `.hermes.md` in Aether-Agents won't load when Hermes works on Artemisa.