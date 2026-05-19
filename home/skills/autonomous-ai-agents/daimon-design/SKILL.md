---
name: daimon-design
description: Design and rework Aether Agents Daimon profiles — SOUL.md, config.yaml, toolset selection, and agent type taxonomy. Covers the full rework cycle from role definition to implementation.
version: 1.0.0
category: autonomous-ai-agents
triggers:
  - when creating or reworking a Daimon agent profile
  - when deciding toolsets for an agent
  - when writing or refactoring a SOUL.md
  - when designing research persistence patterns
  - when classifying agents as Actor vs Consultant
---

# Daimon Design

Design and rework Aether Agents Daimon profiles. This skill covers role definition, SOUL.md writing, config.yaml toolset selection, and the Agent Type Taxonomy.

## Agent Type Taxonomy

Every Daimon falls into one of two types, which determines its toolset:

| Type | Purpose | Writes code? | Reads code? | Key toolsets |
|------|---------|-------------|-------------|-------------|
| **Actor** | Implements, creates, modifies files | Yes | Yes | file, terminal, browser, web |
| **Consultant** | Advises, reviews, researches | No* | Yes | web, browser, file (read-only), terminal (read-only) |

*Exception: Daedalus writes prototypes (HTML/CSS mockups), not production code. See sub-types below.

### Consultant Sub-types

| Sub-type | Writes? | Example | What it writes |
|----------|---------|---------|----------------|
| **Consultant-Creator** | Yes (non-production) | Daedalus | Prototypes, diagrams, mockups |
| **Consultant-Analyst** | No | Ictinus, Athena | Nothing — opinions and analysis only |

### Invocation Modes

Agents are invoked in one of two ways:

| Mode | Invocation | Session | Examples |
|------|-----------|---------|---------|
| **Delegate** | Hermes calls `talk_to(action="delegate")` | Multi-turn, persistent | Hefesto, Etalides, Daedalus, Athena, Ictinus |
| **Function** | MCP tool spawns agent programmatically | Single-turn, auto-closed | Ariadna (via `aether_curate`) |

Function agents have different constraints:
- Minimal toolsets (only what the function requires — Ariadna needs only `file`)
- No need for `memory`, `session_search`, `todo`, `clarify` (no conversational continuity)
- Level 1 (simple, single-purpose)
- SOUL.md format rules may be redundant with the calling code's hardcoded prompt (server.py is authoritative)
- Never invoked via `delegate` — the MCP tool constructs and sends the prompt, then auto-closes the session

### Key Implication

The `file` toolset bundles `read_file`, `write_file`, `patch`, `search_files` together. hermes-agent does NOT support disabling individual tools within a toolset. For Consultant-Analyst agents that should never write:

- **Option A (recommended):** Give `file` toolset + SOUL.md restriction ("NEVER modify files"). Models generally respect strong role instructions.
- **Option B (structural):** Create a `custom_toolsets` entry listing only `read_file` and `search_files`. This is purely manual and doesn't auto-update with hermes-agent releases.
- **Option C (future):** hermes-agent may add `disabled_tools` per-tool granularity. Not available yet.

For the Aether Agents project, we use **Option A** because:
1. Daedalus needs `write_file` for prototypes (Consultant-Creator)
2. Ictinus/Athena have strong SOUL.md restrictions that models respect
3. The overhead of custom toolsets per agent isn't worth the maintenance

## SOUL.md Design Principles

### Structure (target: 80-130 lines)

A SOUL.md should contain:
1. **Identity** (5-8 lines) — name, role, eponym, one-line purpose
2. **Execution Context** (5-10 lines) — how the agent receives tasks, project root, session scope
3. **Core Responsibilities** (5-8 lines) — numbered list of what the agent does
4. **Hard Limits** (5-8 lines) — what the agent MUST NOT do (with clear boundary)
5. **Protocol sections** — concise rules specific to the agent's domain
6. **Output Format** — mandatory response structure

### What NOT to put in SOUL.md

- **Few-shot examples** — more than 1 compact example belongs in a skill that loads on-demand
- **Technique references** — curl fallback strategies, API patterns, etc. belong in skills
- **Workflow context** — the agent doesn't need to know about the 5-phase pipeline (Hermes handles routing)
- **Duplicate definitions** — output format and limits defined once, never repeated
- **Search strategy details** — belongs in a skill, loaded when needed

### Pitfalls

- **Bloat kills signal:** A 400-line SOUL.md burns tokens every turn. Target 80-130 lines.
- **Duplication equals inconsistency:** If output format appears twice, they'll diverge. Define once.
- **Skills are on-demand, not bloat:** Don't prune an agent's skill list thinking it's loaded every turn. Skills load when the agent decides it needs them. A large skill list = more options, not more context.
- **"Architecture by tools, not prompts" is the goal, but pragmatism wins:** If hermes-agent doesn't support per-tool disabling, SOUL.md restrictions + toolset selection is the practical compromise.
- **Empty SOUL.md = silent identity crisis:** An agent with 0-line SOUL.md falls back to hermes-agent's generic default prompt with no role, no limits, no identity. Always verify SOUL.md isn't empty after config changes. (Ictinus had this issue — v0.10.2 will fix it.)
- **Consultant-Creator needs write_file for prototypes:** Daedalus must write HTML/CSS files to prototype and iterate. Don't strip `file` (which bundles write_file) from Consultant-Creators. But DO strip `patch` and `execute_code` — those are Actor tools for modifying production code, not creating new prototypes.
- **CHANGELOG gap before release:** Always run `git tag -l` and compare tags against CHANGELOG headings before cutting a release. Tags can exist with GitHub releases but no CHANGELOG entry (v0.9.0 was missing from CHANGELOG). The release sequence must include verifying and filling any gaps.
- **Config-template identity drift:** When a Daimon's role evolves (e.g., Etalides: web-researcher → researcher, Daedalus: frontend-developer → consultant-creator, Ariadna: project-manager → context-curator), the config.yaml.template often still has the OLD role, description, capabilities, and toolsets. Always audit config.yaml.template against the new SOUL.md after a rework. The #1 contradiction pattern: config says one identity, SOUL.md says another.
- **Non-English config descriptions:** Old configs sometimes had Spanish descriptions (e.g., Athena v0.10.x: "Security Engineer del ecosistema. Protección proactiva, threat modeling, security review."). Always rewrite descriptions in English. The model reads the description field; mixed-language configs confuse role identity.
- **Content extraction is the primary SOUL reduction mechanism:** For Consultant-Analyst agents (Athena, Ictinus), the biggest line savings come from moving detailed checklists, protocols, and few-shot examples into a dedicated skill. Athena went from 342→121 lines primarily by extracting ~60 lines of checklists + ~60 lines of few-shots into `athena-security-checklists`. The SOUL.md keeps a compact reference ("For detailed checklists, load the `athena-security-checklists` skill") and the full content lives in `SKILL.md` + `references/`. This pattern should be applied to any Consultant whose SOUL exceeds 130 lines.
- **Function agents don't need session toolsets:** Agents invoked programmatically (Ariadna via `aether_curate`) don't need `memory`, `session_search`, `todo`, `clarify`, or `terminal`. They run single-turn, auto-close. Check the invocation path in server.py before deciding toolsets.
- **`gh pr create --body` breaks with special characters** — quotes, parentheses, em-dashes, and other shell-problematic characters in PR body text cause `gh` to misparse arguments. Always use `--body-file /tmp/pr-body.md` instead. Write body to temp file, then reference it.
- **Batch delegation for releases:** When doing multiple releases in one session (e.g., v0.10.0 + v0.10.1 + v0.10.2), provide ALL tasks in a single delegation to Hefesto. Don't gate-check between steps — include EXACT content for every file change so Hefesto can execute without ambiguity.
- **Squash merge PRs change commit hashes:** When PRs are squash-merged, the commit hash differs from the feature branch. Verify with `git log` rather than relying on reported hashes.
- **Task decomposition belongs to Hermes, not Hefesto:** Hefesto's SOUL.md should NOT contain role catalogs or decomposition protocols. Hermes breaks tasks into atomic units and delegates; Hefesto receives atomic tasks and executes. The Role Catalog is a reference for Hermes, not an internal tool for Hefesto.
- **MCP delegation content size limit blocks large transfers:** When Hermes needs to pass large content (e.g., a full SOUL.md of 15K-24K chars) to a Daimon via `talk_to(action="delegate")`, the Daimon's response can get truncated. The user's preferred fix is to increase `tool_output.max_bytes` in config.yaml (default 50K → 200K for large-context models). The MCP `prompt` parameter has no `maxLength` — it's not a schema limit. For glm-5.1 the 32K output token limit (~90K chars) is ample for SOUL.md transfers; the real truncation happens on the response side at 50K. The 3-layer persistence system (`DEFAULT_RESULT_SIZE_CHARS=100K`, `DEFAULT_TURN_BUDGET_CHARS=200K`) auto-persists oversized tool results to disk, replacing them with a 1.5K preview + file path. Interim workaround: include exact file references (path + line ranges) in delegation prompts so Hefesto can `read_file` the target content himself. See `references/mcp-content-limits.md` for full investigation, diagnosis checklist, model data, and config recommendations.
- **Design-then-decompose workflow:** The operational pattern is: (1) User + Hermes design together — architectural decisions, trade-offs, what stays and goes. (2) Hermes decomposes into atomic tasks with CONTEXT + TASK + CONSTRAINTS + ACCEPTANCE CRITERIA. (3) Hermes delegates to Daimons autonomously. The user does NOT review each atomic task — they approve the design and Hermes handles execution. This is how v0.10.0-0.11.0 actually shipped.

## Config.yaml Design

### Toolset Selection Rules

1. **Only include toolsets the agent NEEDS.** Every tool adds token cost and cognitive load.
2. **Document WHY each toolset is included** — inline comments explaining the justification.
3. **Use the Agent Type Taxonomy** to determine toolsets.
4. **Keep config.yaml.template in sync** — after ANY change to live config, update the template.

### Template Sync Pitfall

The #1 config drift pattern: you update `config.yaml` (live, gitignored) but forget `config.yaml.template` (committed). The template generates configs for new installs. If it's out of sync, new installs get stale role descriptions, missing capabilities, and missing toolsets.

**Always update both.** After updating `config.yaml`, immediately update `config.yaml.template` with the same changes (keeping `__AETHER_ROOT__` and `__VENV_PYTHON__` placeholders).

### Comments Convention

```yaml
# Toolsets — each has a documented justification
toolsets:
  - web        # web_search + web_extract — primary web research tools
  - browser    # browser_navigate/snapshot/click/type/etc — JS-heavy pages
  - file       # read_file, write_file, patch, search_files — persistence + code research
  - terminal   # terminal + process — secondary tool (git, wc, structure analysis)
```

## Research Persistence Pattern

Web research and code research have different persistence needs:

| Research Type | Persisted? | Format | Where |
|---------------|-----------|--------|-------|
| **Web research** | Yes | Obsidian-flavored markdown with YAML frontmatter | `__AETHER_ROOT__/research/YYYY-MM-DD-HHMM-topic-slug.md` |
| **Code research** | No | Direct response to Hermes in standard output format | N/A — situational, not indexed |

### Why This Distinction

Web research produces reusable knowledge — "how does framework X work" is valuable across sessions. Code research answers situational questions — "how is X implemented in THIS project" changes every time. Persisting situational answers creates noise.

### Obsidian Vault Structure

```
research/
├── .gitkeep
├── .obsidian/
│   ├── app.json
│   └── workspace.json
├── README.md
├── INDEX.md
├── YYYY-MM-DD-HHMM-topic-slug.md
└── ...
```

Each research file has YAML frontmatter:
```yaml
---
date: YYYY-MM-DDTHH:MM:SSZ
author: etalides
depth: fast | standard
confidence: high | medium | low
model: [agent model]
links_used: N
links_budget: N
tags: [topic, framework, category]
---
```

Wikilinks `[[YYYY-MM-DD-topic-slug]]` connect related research. Anyone cloning the repo can open `research/` as an Obsidian vault.

## Rework Process

When reworking a Daimon agent, follow this sequence:

1. **Diagnose current state** — read SOUL.md, config.yaml, check sessions in .aether
2. **Define the role** — what is this agent FOR? (Chris decides, Hermes proposes)
3. **Design SOUL.md** — apply the design principles above, target 80-130 lines
4. **Extract domain content to skills** — if SOUL.md contains detailed checklists, protocols, or few-shot examples that push it past 130 lines, extract them into a dedicated skill under the appropriate category (e.g., `red-teaming/athena-security-checklists` for Athena's checklists). Skill loads on-demand; SOUL.md loads every turn. This is the primary reduction mechanism for Consultant-Analyst SOULs. Add a one-line reference in SOUL.md §5 (Skills) pointing to the extracted skill.
5. **Select toolsets** — use the Agent Type Taxonomy to determine which toolsets
6. **Create/verify persistence** — research vault, template directories
7. **Update Hermes SOUL.md** — routing table must reflect new role
8. **Implement** — delegate to Hefesto for file writes
9. **Test** — delegate a real task to the agent and verify output format, tool usage, and role adherence
10. **Sync template** — update config.yaml.template with same changes as live config
11. **Add design reference** — create `references/<agent>-v<version>-rework-design.md` under the daimon-design skill, documenting what changed, what was removed, and where content moved
12. **Commit, push, and release** — feature branch → PR → dev → merge → tag → GitHub Release (see `references/release-workflow.md` for the full sequence)

## Consultant Workflow (delegate-based, v0.10.1+)

Hermes' SOUL.md §13 must document the **actual** consulting workflow, not an aspirational one. The `consult` tool does not exist in olympus_v3. The real workflow uses `delegate` with structured prompts.

### SOUL.md §13 Structure (what to write)

The consulting section in Hermes' SOUL.md should contain:

1. **Agent Types table** — maps every Daimon to its type and what it can write:
   | Type | Agents | Writes code? | Reads code? |
   |------|--------|-------------|-------------|
   | Actor | Hefesto, Etalides | Yes | Yes |
   | Consultant-Creator | Daedalus | Prototypes only | Yes |
   | Consultant-Analyst | Ictinus, Athena | No | Yes |

2. **How to Consult** — delegate prompt format for consultations:
   ```
   When consulting (not implementing), use this prompt structure:
   CONTEXT: [2-4 lines]
   TASK: [Specific question, NOT an implementation request]
   CONSTRAINTS: [Scope limits]
   OUTPUT FORMAT: Observations / Risks / Recommendations
   ```

3. **Sequential Consultation** — when multiple consultants review the same thing:
   - Delegate to first consultant → receive response
   - Include relevant parts in next consultant's CONTEXT
   - Hermes filters and synthesizes (Hermes has final word)
   - Present consolidated recommendations to user

4. **Current Consultants** — table mapping agent to consultation domain:
   | Agent | Role | Consult on |
   |-------|------|-----------|
   | Daedalus | Consultant-Creator | UX, usability, user flows, prototypes |
   | Ictinus | Consultant-Analyst | Backend architecture, scalability |
   | Athena | Consultant-Analyst | Security, edge cases, acceptance criteria |

### Important: Do NOT document the aspirational `consult` tool

Previous versions of §13 described `consult(action="start")`, `consult(action="run")`, `consult(action="sign")` — this confused both Hermes and users into expecting a tool that doesn't exist. Only document what actually works: `delegate` with structured prompts.

The structured `consult` action is planned for v0.11.0+. Until then, `delegate` IS the consulting workflow.

## Task Decomposition: Hermes Owns It

A critical architectural lesson from the Hefesto rework (v0.11.0 planning): **task decomposition is Hermes' responsibility, not Hefesto's**. Hefesto's v0.10.x SOUL.md contained a Role Catalog (backend, frontend, devops, qa, security, data, docs, architect, perf) and protocols for decomposing specs into sub-tasks with `delegate_task()` calls. This was wrong because:

1. **Hermes already decomposes tasks** — in every session, Hermes reads the user's request, breaks it into atomic tasks, and delegates each one to the right Daimon with a structured prompt.
2. **Hefesto should receive atomic tasks, not decompose further** — when Hermes says "update config.yaml.template and sync the live config", Hefesto should execute it, not decompose it into sub-tasks.
3. **The Role Catalog is a reference for Hermes** — the granularity of roles (backend, frontend, devops) helps Hermes decide who gets what task, not Hefesto.

### Athena Rework (v0.11.1) — COMPLETED

Athena was reworked from a generic Daimon with LangGraph workflow context to a **Consultant-Analyst** (342 → 121 lines):

| What | Before | After |
|------|--------|-------|
| Type | Generic Daimon with LangGraph workflows | Consultant-Analyst (reads code, never implements) |
| Role | security-engineer | security-analyst |
| Toolsets | terminal, file, search_files, execute_code, memory, skills | file, terminal, skills |
| Capabilities | +dependency-audit, +risk-communication | removed (merged into security-review) |
| Config description | Spanish text | English |

Removed from SOUL.md:
- §7 "In Workflow Context" (LangGraph/workflows don't exist in olympus_v3)
- Duplicate Protocol 5 and dead reference to non-existent file
- Detailed security checklists → moved to `athena-security-checklists` skill
- Few-shot Examples A and B → moved to `athena-security-checklists` skill
- "Communicate with Ariadna" → Athena reports to Hermes only
- `execute_code` toolset (Athena doesn't execute code)
- `memory` toolset (single-turn consultant, no persistent state)
- `search_files` separate toolset (already bundled in `file`)

Added to SOUL.md:
- Context-aware severity guidance ("plaintext .env on dev laptop is LOW risk, same on prod server is CRITICAL")
- Explicit "Do NOT write files" hard limit (Consultant-Analyst boundary)
- Skill reference to `athena-security-checklists` for on-demand loading
- Compact STRIDE table (was verbose list)

Key lesson: Athena over-escalated severity without considering deployment context. The new SOUL.md includes explicit context-aware severity guidance.

### Hefesto Rework (v0.11.0) — COMPLETED

The following were stripped from Hefesto's SOUL.md (284 → 114 lines):
- **Ergates references** — the sub-agent concept with role-based delegation via `delegate_task` doesn't match current architecture
- **LangGraph workflow context** — `state["workflow_type"]`, `state["context"]`, `state["audit_result"]` — doesn't exist in olympus_v3
- **`.hefesto/TASKS.md`** — replaced by `.aether/` state management
- **Role-Based Task Decomposition protocol** — moved to Hermes §6 as Task Decomposition section
- **Delegate Sub-Agent Template** — Hermes owns delegation via `talk_to(action="delegate")`
- **Skill: `subagent-driven-development`** — removed from Hefesto config (still useful as a general pattern)
- **config.yaml changes** — removed `delegate_task` toolset, removed `delegation` section, added `receives_from` capability, English description

### What was added to Hermes' SOUL.md (v0.11.0)

A **Task Decomposition** section in §6 that makes explicit what Hermes already does:
1. Read the user's request
2. Break into atomic tasks (one Daimon, one deliverable per task)
3. Assign each task to the right Daimon using the routing table
4. For implementation tasks, use the Role Catalog as reference for sub-task granularity
5. Delegate with CONTEXT + TASK + CONSTRAINTS + OUTPUT FORMAT

Plus **Hard Rule #10**: "NEVER delegates a vague task — decompose into atomic tasks with CONTEXT + TASK + CONSTRAINTS + ACCEPTANCE CRITERIA before delegating"

And the **Manifesto** update: "I plan, I decompose, I delegate, I synthesize" (was "I plan, I delegate, I synthesize")

### Role Catalog (now in Hermes §6, not Hefesto)

| Task Type | Description | Assign to |
|-----------|-------------|-----------|
| backend | APIs, DB, models, business logic | Hefesto |
| frontend | UI components, client state, styling | Hefesto |
| devops | Infra, CI/CD, deployment, config | Hefesto |
| data | Schema, migrations, queries, optimization | Hefesto |
| docs | API docs, READMEs, guides | Hefesto |
| design | UX flows, layouts, prototypes | Daedalus |
| architect | Architecture proposals, trade-offs, specs | Ictinus |
| security | Security audit, vulns, hardening | Athena |
| research | Web/codebase investigation | Etalides |
| curate | Context curation, .aether maintenance | Ariadna (via aether_curate) |

## Hefesto SOUL.md Obsolete References (COMPLETED in v0.11.0)

The following in Hefesto's SOUL.md (v0.10.x, 284 lines) were obsolete and **were removed in v0.11.0**:

| Section | Lines | Problem | Status |
|---------|-------|---------|--------|
| §3 "Coordinate Ergates" | ~6 | Ergates concept doesn't exist in current architecture | ✅ Removed |
| §4 "Do NOT manage projects — that is Ariadna" | 1 | Ariadna is now Context Curator, not PM | ✅ Removed |
| §7 "In Workflow Context" | ~25 | LangGraph, `run_workflow`, `state["workflow_type"]` — doesn't exist | ✅ Removed |
| §8 Protocol 2 "Role-Based Task Decomposition" | ~35 | Hermes owns decomposition, not Hefesto | ✅ Removed (moved to Hermes §6) |
| §8 Protocol 3 "Delegate Sub-Agent Template" | ~25 | `delegate_task` with role-based prompts is Hermes' job | ✅ Removed |
| Few-Shot Example C "Sub-Agent Delegation" | ~40 | Uses `delegate_task(role="backend")` — not current pattern | ✅ Removed |
| `.hefesto/TASKS.md` reference | §3 | Replaced by `.aether/` state management | ✅ Removed |
| Skill `subagent-driven-development` | §5 | Obsolete — Hefesto no longer spawns sub-agents | ✅ Removed from config |

What Hefesto kept (v0.11.0, ~114 lines): Protocols 1 (Receiving a Spec → Protocol 1), 4 (Code Review → Protocol 2), 6 (Debugging → Protocol 3), Output Format, Identity, Limits, and Example B (Debugging). Protocol 5 (Integration) was consolidated into "Core Responsibilities".

### Athena Rework (v0.11.1) — COMPLETED

Athena went from Security Engineer (generic Daimon with LangGraph workflows) to Security Analyst (Consultant-Analyst). The primary reduction mechanism was **content extraction to a domain skill**.

| Metric | Before | After |
|--------|--------|-------|
| SOUL.md | 342 lines | 121 lines |
| Role | security-engineer | security-analyst |
| Type | Generic Daimon | Consultant-Analyst |
| Toolsets | terminal, file, search_files, execute_code, memory, skills | file, terminal, skills |
| Capabilities | receives_from, threat-modeling, security-review, dependency-audit, risk-communication | receives_from, threat-modeling, security-review |

**What moved to `athena-security-checklists` skill:** ~60 lines of security review checklists, ~15 lines of dependency audit detail, ~60 lines of few-shot examples. SOUL.md keeps compact references ("For detailed checklists, load the `athena-security-checklists` skill").

**What was removed entirely:** §7 "In Workflow Context" (LangGraph), Protocol 4 (Risk Communication to Ariadna — Athena reports to Hermes only), duplicate Protocol 5 (output format appeared twice). `dependency-audit` and `risk-communication` merged into `security-review`.

**Key design pattern validated:** Consultant-Analyst SOULs benefit most from content extraction because their domain expertise (checklists, protocols, examples) is highly structured and self-contained — perfect for on-demand skill loading. This reduced Athena's per-turn token cost by 65% without any capability loss.

See `references/athena-v0.11.1-rework-design.md` for full before/after analysis.

## References

- `references/etalides-v0.10-rework.md` — Full case study of the Etalides rework session
- `references/daedalus-v0.10.1-design.md` — Design decisions for Daedalus Consultant-Creator rework
- `references/ariadna-function-agent.md` — Ariadna as function agent: invocation architecture, config contradictions, and v0.10.2 rework plan
- `references/mcp-content-limits.md` — Investigation: where the content size limits are, what's configurable, and workarounds for delegation
- `references/release-workflow.md` — Full release sequence for Aether Agents: CHANGELOG, version bumps, tagging, GitHub releases
- `references/hefesto-v0.11-rework-design.md` — Hefesto rework design: removing decomposition, obsolete references, and scoping