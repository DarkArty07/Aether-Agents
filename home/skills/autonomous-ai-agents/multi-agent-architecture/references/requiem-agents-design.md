# Requiem Agents — Design Example (v2)

Concrete implementation of the multi-agent-architecture patterns. Requiem Agents is the successor to Aether Agents, designed to solve two root problems: (1) expensive model reading code, (2) no real quality validation.

## Project Meta

- **Created:** 2026-06-20
- **Predecessor:** Aether Agents (306 sessions, 26 decisions, 6 Daimons — closed)
- **Directory:** /home/prometeo/Requiem/
- **Theme:** Gothic horror
- **License:** MIT
- **GitHub:** DarkArty07 (public repo)
- **Files:** DESIGN.md (281 lines, v2), PLAN.md (202 lines, 6 phases)

## The Problem It Solves

Aether Agents had Hermes (DeepSeek V4 Pro, $$$) doing everything — including reading code. ~80% of total cost was Hermes's input tokens reading code files. Additionally, Athena (the security reviewer) was a subordinate Daimon — Hermes could ignore her recommendations, so quality validation was theater.

## Architecture

```
USUARIO
   │
   ▼
┌──────────────────┐
│     RAVEN        │  ← Asistente (hermes-agent v0.17, DeepSeek V4 Pro $$$)
│  (vibecoding)    │     NUNCA lee código. Aprendizaje continuo.
└──────────────────┘
         │
    MCP: activate_necromancer(project_root, project_name, formal_task)
         │
         ▼
┌──────────────────┐     ┌──────────────────┐
│   NECROMANCER    │────►│    REVENANT       │
│  (orquestador)   │     │   (auditor peer)  │
│  Custom Python   │     │   Custom Python   │
│  On/off by Raven │     │   Veto power      │
│  Modelo medio $$ │     │   Modelo medio $$ │
└──────────────────┘     └──────────────────┘
    │        │        │
    ▼        ▼        ▼
┌───────┐ ┌───────┐ ┌───────┐
│Shade  │ │Shade  │ │Shade  │
│of Prog│ │of Res │ │of X   │
│ ¢¢    │ │ ¢¢    │ │ ¢¢    │
└───────┘ └───────┘ └───────┘
```

## Role Mapping

| Role | Name | Theme justification | Model | Framework |
|------|------|---------------------|-------|-----------|
| Assistant | Raven | Poe's messenger — carries words between worlds | DeepSeek V4 Pro ($$$) | hermes-agent v0.17 |
| Orchestrator | Necromancer | Commands the dead (shades) to do his bidding | GLM-5.2 / Kimi K2 ($$) | Custom Python |
| Auditor | Revenant | One who returns from the dead to judge the living | Modelo medio ($$) | Custom Python |
| Agents | Shade of X | Spectral executors — "Shade of Programming", "Shade of Research" | Flash/local (¢) | Custom Python |

## Key Design Decisions (v2 — all resolved)

1. **Framework:** Only Raven uses hermes-agent v0.17.0. Necromancer, Revenant, and Shades are custom Python using OpenAI/Anthropic API style. This was the #1 lesson from Aether Agents — the inference engine for sub-agents was the worst part.

2. **Communication:** MCP (Raven ↔ Necromancer), direct async invocation (Necromancer ↔ Shades), function call (Necromancer → Revenant). Not ACP — MCP is the standard hermes-agent v0.17 supports natively.

3. **Provider:** OpenCode Go as sole provider for now. API estilo OpenAI Chat Completions. Usage limits: $12/5h, $30/week, $60/month. More providers to be added later.

4. **Revenant implementation:** Function invoked by Necromancer after each Shade completes. Same process, different system prompt. Tools: read-only (read_file, search_files). Veto power — Necromancer cannot override. 3 rejections → escalate to Raven.

5. **Necromancer lifecycle:** On/off — Raven activates it with project_root + project_name (mandatory guard). Dies when Raven dies or explicitly shuts it down. Not a daemon.

6. **Raven character:** Vibecoding + learning continuity (same memory/skills tools as Hermes). Priority 1: form user preferences. Priority 2: continuous learning — if something seems like learning, it is, save it. Priority 3: workflows → skills. NOT Hermes in totality, but inherits the best for comfortable vibecoding.

7. **Telemetry (Eval):** SQLite shared database. Every agent call records: tokens, cost, duration, pass/fail, retries, escalations. Session status tool shows visual format: "glm-5.2 │ 65.5K/256K │ [███░░░] 26% │ 51m │ ⏲ 2m 42s".

8. **Frontend:** React + Vite + CSS Gothic Horror. FastAPI backend reading SQLite. Panel shows: active sessions, stats, configuration, activity log, project info. Theme: #0a0a0a background, #c0c0c0 text, #8b0000 accents, serif gothic titles, mono data.

9. **Installation:** pip install 'hermes-agent[mcp]'==0.17.0 in dedicated venv at ~/Requiem/raven/.venv/. No wrapper (Chris's rule). PATH-based resolution. HERMES_HOME=~/Requiem/raven/.

## Initial Shades

| Shade | Tools | Model | Aether equivalent |
|-------|-------|-------|-------------------|
| Shade of Programming | read_file, write_file, terminal, search_files | DeepSeek V4 Flash | Hefesto |
| Shade of Research | read_file, search_files, web_search | DeepSeek V4 Flash | Etalides |

Phase 2 Shades (future): Shade of UX, Shade of Security.

## Memory Separation

| Role | Memory |
|------|--------|
| Raven | User preferences, communication style, conversation history, skills |
| Necromancer | Codebase structure, delegation patterns, Shade capabilities |
| Revenant | Past failures, edge cases, rejection criteria |
| Shades | Domain-specific knowledge via system prompts |

## Plugin Migration (v2.1 — 2026-06-24)

Requiem migrated from MCP server to native hermes-agent plugin. The migration initially broke the architecture (3 critical failures documented in `references/requiem-plugin-reconstruction.md`). The reconstruction produced:

**Architecture (current):**
```
USUARIO
   │
   ▼
┌──────────────────┐
│     RAVEN        │  ← Asistente (hermes-agent v0.17, GLM-5.2 $$$)
│  (vibecoding)    │     NUNCA lee código (file/terminal disabled)
│  Graphify MCP    │     ENTIENDE código via knowledge graph (query_graph, etc.)
└──────────────────┘
         │
    Plugin: delegate_to_necromancer(prompt, project_root)
    (prompt uses structured template: OBJETIVO/CONTEXTO/RESTRICCIONES/CRITERIOS)
         │
         ▼
┌──────────────────┐     ┌──────────────────┐
│   NECROMANCER    │────►│    REVENANT       │
│  (orquestador)   │     │   (auditor peer)  │
│  Custom Python   │     │   Custom Python   │
│  Decomposes      │     │   Veto power      │
│  process_task()  │     │   3 strikes       │
└──────────────────┘     └──────────────────┘
    │        │        │
    ▼        ▼        ▼
┌───────┐ ┌───────┐ ┌───────┐
│Shade  │ │Shade  │ │Shade  │
│of Prog│ │of Res │ │of Exec│
│ ¢¢    │ │ ¢¢    │ │ ¢¢    │
└───────┘ └───────┘ └───────┘
```

**Key changes from v2:**
- MCP server (requiem-mcp) disabled, replaced by native plugin (requiem_tools v0.2.0)
- 3 tools (investigate/execute/implement) replaced by 1 (`delegate_to_necromancer`)
- All tools now route through `process_task()` — no bypassing the Necromancer
- LLM summarization eliminated — Raven receives raw worker output
- Graphify MCP server added as read-layer for Raven (independent of Aether Agents)
- Custom indexer.py discontinued in favor of graphify MCP
- Provider changed from OpenCode Go to SwiftRouter
- Models: Raven=GLM-5.2, Necromancer=deepseek-v4-pro, Shades=deepseek-v4-flash

**See also:** `references/requiem-plugin-reconstruction.md` for the full diagnosis and reconstruction session details.
