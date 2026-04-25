# Aether Agents — Home Directory

This is the `HERMES_HOME` for the Aether Agents ecosystem. All agent profiles, shared skills, sessions, and logs live here.

---

## Directory Layout

```
home/
├── skills/                  ← Shared skills (single source of truth)
├── profiles/                ← Agent profiles (one per agent)
├── sessions/                ← Auto-created by hermes-agent
├── logs/                    ← Auto-created by hermes-agent
├── active_profile           ← Currently active profile name
└── state.db                 ← SQLite session store
```

---

## Skills Architecture

Skills are stored in ONE place and shared across all profiles:

```
home/skills/
├── aether-agents/           ← Framework-specific skills (10)
│   ├── orchestration/       ← Team playbook (always loaded for Hermes)
│   ├── workflow-design/     ← Workflow engine technical reference
│   ├── workflow-playground/ ← Future dynamic workflow composition
│   ├── aether-diagnostics/  ← Ecosystem health checks
│   ├── aether-agent-creation/ ← How to create new Daimon profiles
│   ├── ariadna-workflow/    ← Ariadna's workflow context
│   ├── athena-workflow/     ← Athena's workflow context
│   ├── daedalus-workflow/   ← Daedalus' workflow context
│   ├── etalides-workflow/   ← Etalides' workflow context
│   └── hefesto-workflow/    ← Hefesto's workflow context
│
├── productivity/            ← Generic skill categories
├── creative/
├── research/
├── github/
├── software-development/
├── mlops/
├── red-teaming/
├── note-taking/
└── ... (24 categories total)
```

Each profile's `config.yaml` points here via `skills.external_dirs`:

```yaml
skills:
  external_dirs:
    - /home/prometeo/Aether-Agents/home/skills
```

Skills are loaded based on their **trigger conditions** (YAML frontmatter), not by directory filtering. Each Daimon's SOUL.md references the skills relevant to their specialty.

---

## Profiles

```
home/profiles/
├── hermes/                  ← Orchestrator
│   ├── SOUL.md              ← 7-section identity
│   ├── config.yaml          ← gitignored (local config)
│   ├── config.yaml.template ← tracked (template for new installs)
│   ├── .env.example         ← tracked (API key template)
│   ├── .env                 ← gitignored (actual keys)
│   ├── skills/              ← empty (loaded via external_dirs)
│   ├── memories/            ← persistent memory
│   └── sessions/            ← session history
│
├── ariadna/                 ← Project Manager
├── hefesto/                 ← Senior Developer
├── etalides/                ← Web Researcher
├── daedalus/                ← UX/UI Designer
└── athena/                  ← Security Engineer
```

### Profile files tracked in git

| File | Tracked? | Purpose |
|------|----------|---------|
| `SOUL.md` | ✅ Yes | Agent identity (7 sections) |
| `config.yaml` | ❌ No (hermes only) / ✅ Yes (daimons) | Agent configuration |
| `config.yaml.template` | ✅ Yes | Template for new installs |
| `.env.example` | ✅ Yes | API key template |
| `.env` | ❌ No | Actual API keys |
| `skills/` | ❌ No | Loaded via external_dirs |
| `memories/` | ❌ No | Local memory |
| `sessions/` | ❌ No | Session history |

---

## SOUL.md Convention

All agent SOUL.md files follow a 7-section structure:

| # | Section | Content |
|---|---------|---------|
| 1 | Identity | Name, role, eponym |
| 2 | Execution Context | How invoked, project root, session scope (DRY for 5 Daimons) |
| 3 | Core Responsibilities | What the agent does (4-6 verbs) |
| 4 | Limits | What the agent MUST NOT do |
| 5 | Skills | Referenced skills with 1-line descriptions |
| 6 | Output Format | Structured output template |
| 7 | In Workflow Context | How the agent operates inside LangGraph workflows |

**Execution Context is identical for all 5 Daimons** (Ariadna, Hefesto, Etalides, Daedalus, Athena). Only Hermes' differs because he's the orchestrator.

---

## Adding a New Daimon

See `home/skills/aether-agents/aether-agent-creation/SKILL.md` for the full process.

Quick steps:
1. Create `home/profiles/{name}/` directory
2. Write `SOUL.md` (7 sections, Execution Context from template)
3. Write `config.yaml` with `agent:` field for discovery + `skills.external_dirs`
4. Add `.env.example`
5. Create workflow skill in `home/skills/aether-agents/{name}-workflow/SKILL.md`
