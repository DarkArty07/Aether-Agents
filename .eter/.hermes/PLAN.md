# PLAN v2: Formalización de Convenciones del Ecosistema Aether Agents

**Fecha:** 2026-04-26
**Proyecto:** Aether-Agents (`/home/prometeo/Aether-Agents/`)
**Branch:** `dev`
**Fase:** Estandarización de metodología operativa
**Versión plan:** 2 (ajustado tras investigación de hermes-agent)

---

## Objetivo

Definir y documentar cómo trabaja el equipo Aether Agents: pipeline de trabajo, taxonomía de artifactos, reglas de asignación por especialidad, cuándo usar workflows vs `talk_to` vs `delegate_task`, y estandarizar la estructura de SOUL.md y skills de todos los Daimons.

---

## Investigación previa: Cómo hermes-agent carga contenido

Se investigó `agent/prompt_builder.py` y `run_agent.py` en `~/.hermes/hermes-agent/`. El system prompt se ensambla en este orden:

```
1. SOUL.md          ← HERMES_HOME/SOUL.md. Slot #1. SIEMPRE cargado (max 20K chars).
2. Tool guidance    ← Condicional (memory, session_search, skills tools).
3. Tool-use enforce ← Model-specific.
4. Ephemeral prompt ← system_message (personality overlay).
5. Memory           ← Persistente. Inyectado CADA turno (max 2,200 chars).
6. USER.md          ← Perfil de usuario.
7. Skills index     ← Lista de skills disponibles (cargadas por triggers).
8. Context files    ← .hermes.md, AGENTS.md, CLAUDE.md, .cursorrules (project-specific).
9. Date/time + platform hint.
```

| Mecanismo | Portable | Siempre cargado | Límite | Uso |
|---|---|---|---|---|
| **SOUL.md** | ✅ Sigue al perfil | ✅ Slot #1 | 20K chars | Identidad, responsabilidades, límites |
| **Skills (always)** | ✅ Sigue al perfil | ✅ Si trigger match | Skill entera | Procedimientos, few-shots |
| **Memory** | ✅ Sigue al agente | ✅ Cada turno | 2,200 chars | Datos durables |
| **`.hermes.md`** | ❌ Solo git root | ⚠️ Si cwd en ese repo | 20K chars | Project-specific |
| **`.eter/`** | ❌ Project-specific | ❌ No se carga | — | Estado del proyecto |

### Decisión arquitectónica: dónde vive el "team playbook"

| Contenido | Dónde vive | Por qué |
|---|---|---|
| **Pipeline + Matriz de decisión + .eter/ convention** | `skills/aether-agents/orchestration/SKILL.md` | Ya se carga siempre (trigger: "always loaded for hermes profile"). Es el manual operativo de Hermes. |
| **Resumen compacto (5-8 líneas)** | `SOUL.md` de Hermes | Identidad: referencia al pipeline y a la orchestration skill. |
| **Execution Context + .eter/ rules** | `SOUL.md` de cada Daimon | Cada Daimon necesita saber cómo lo invocan y dónde escribir. |
| **API reference técnica** | `src/olympus/README.md` | Documentación para desarrolladores. |
| **Few-shots específicos** | Skill del Daimon que ejecuta | ej: bug-fix few-shots en `hefesto-workflow`. |

**NO se crea `CONVENTION.md` como archivo separado.** Su contenido se integra en artifacts existentes que el framework ya carga automáticamente.

---

## Decisiones confirmadas por Christopher

| # | Decisión | Detalle |
|---|----------|---------|
| D1 | **Pipeline 5 fases** | IDEA → INVESTIGAR → DISEÑAR → PLANIFICAR → PROGRAMAR |
| D2 | **Workflows = trabajar** | `run_workflow` para implementaciones, features, bugs, auditorías — producen artifacts |
| D3 | **talk_to = consultar** | `talk_to` para preguntas, opiniones, consultas puntuales — sin estado persistente |
| D4 | **delegate_task = operacional** | Tareas < 3 pasos, sin juicio de especialista |
| D5 | **SOUL.md 7 secciones** | Identity, Execution Context, Responsibilities, Limits, Skills, Output Format, In Workflow Context |
| D6 | **Progresión de artifactos** | DESIGN.md, PLAN.md, RESEARCH.md usan Append-top con versionado `v{N}` |
| D7 | **CURRENT.md = overwrite** | Foto del ahora, una sola versión |
| D8 | **LOG.md = append-bottom** | Historial cronológico inmutable |
| D9 | **TASKS.md = overwrite con ciclos** | Cada ciclo de Hefesto genera nueva sección |
| D10 | **Skills curadas por especialidad** | Cada Daimon solo carga skills de su dominio. No 73 skills duplicadas |
| D11 | **Team playbook en orchestration skill** | Pipeline, matriz, taxonomía, .eter/ en `orchestration/SKILL.md` (cargada siempre) |
| D12 | **Execution Context DRY** | Idéntico para 5 Daimons. Solo cambia en Hermes |

---

## Archivos a modificar

### FASE 1: Orchestration Skill — Team Playbook

| # | Archivo | Acción | Prioridad |
|---|---------|--------|-----------|
| 1.1 | `home/profiles/hermes/skills/aether-agents/orchestration/SKILL.md` | AMPLIAR — Integrar pipeline 5 fases + taxonomía de artifactos + matriz de decisión extendida + .eter/ convention + reglas de asignación | 🔴 CRÍTICA |

### FASE 2: Documentación Técnica

| # | Archivo | Acción | Prioridad |
|---|---------|--------|-----------|
| 2.1 | `src/olympus/README.md` | AMPLIAR — API reference + HITL guide + Daimon-to-Node mapping + Progress Watchdog + Known Pitfalls + How to Add a Workflow | 🔴 CRÍTICA |

### FASE 3: SOUL.md — Estandarización (7 secciones)

| # | Archivo | Acción | Prioridad |
|---|---------|--------|-----------|
| 3.1 | `home/profiles/hermes/SOUL.md` | ACTUALIZAR — Ref pipeline, ref orchestration skill, sección Workflow Orchestration | 🟡 ALTA |
| 3.2 | `home/profiles/ariadna/SOUL.md` | ACTUALIZAR — 7 secciones, Execution Context DRY, ref skills curadas, ref .eter/ | 🟡 ALTA |
| 3.3 | `home/profiles/hefesto/SOUL.md` | ACTUALIZAR — 7 secciones, Execution Context DRY, ref skills curadas, ref .eter/ | 🟡 ALTA |
| 3.4 | `home/profiles/etalides/SOUL.md` | ACTUALIZAR — 7 secciones, Execution Context DRY, ref skills curadas, ref .eter/ | 🟡 ALTA |
| 3.5 | `home/profiles/daedalus/SOUL.md` | ACTUALIZAR — 7 secciones, Execution Context DRY, ref skills curadas, ref .eter/ | 🟡 ALTA |
| 3.6 | `home/profiles/athena/SOUL.md` | ACTUALIZAR — 7 secciones, Execution Context DRY, ref skills curadas, ref .eter/ | 🟡 ALTA |

### FASE 4: Skills — Curación por especialidad

| # | Archivo | Acción | Prioridad |
|---|---------|--------|-----------|
| 4.1 | `home/profiles/ariadna/skills/` | LIMPIAR — solo aether-agents + productivity + note-taking | 🟡 ALTA |
| 4.2 | `home/profiles/athena/skills/` | LIMPIAR — solo aether-agents + red-teaming | 🟡 ALTA |
| 4.3 | `home/profiles/daedalus/skills/` | LIMPIAR — solo aether-agents + creative(diagram) + software-dev | 🟡 ALTA |
| 4.4 | `home/profiles/etalides/skills/` | LIMPIAR — solo aether-agents + research + web | 🟡 ALTA |
| 4.5 | `home/profiles/hefesto/skills/` | LIMPIAR — solo aether-agents + software-dev + github + mlops | 🟡 ALTA |
| 4.6 | `home/profiles/hermes/skills/` | SIN CAMBIOS — orquestador necesita todas las categorías | — |

### FASE 5: .eter/ state files — Actualización

| # | Archivo | Acción | Prioridad |
|---|---------|--------|-----------|
| 5.1 | `.eter/.hermes/DESIGN.md` | ACTUALIZAR — Progresión v{N}, limpiar paths obsoletos | 🟢 MEDIA |
| 5.2 | `.eter/.ariadna/CURRENT.md` | ACTUALIZAR — Estado real post-Phase 3 | 🟢 MEDIA |
| 5.3 | `.eter/.hermes/PLAN.md` | REEMPLAZAR — Este archivo (v2) | 🟢 MEDIA |

---

## Especificación detallada

---

### FASE 1: Orchestration SKILL.md — Team Playbook

**Archivo:** `home/profiles/hermes/skills/aether-agents/orchestration/SKILL.md`

**Propósito:** Único punto de carga del team playbook. Hermes lo lee SIEMPRE (trigger "always loaded for hermes profile"). Ya contiene la Routing Matrix, Delegation Gates, Delegate Template, Session Management. Se amplía con:

**Nuevas secciones a agregar** (después de "Step-by-Step Design Protocol", antes de "Multi-Daimon Coordination"):

```markdown
## Project Methodology — 5-Phase Pipeline

IDEA → INVESTIGAR → DISEÑAR → PLANIFICAR → PROGRAMAR

### Phase 1 — IDEA
- Who: Christopher + Hermes
- Input: "I want to build X"
- Output: DESIGN.md v1 (problem sketch, context, constraints)
- Gate: Hermes asks "Did I understand the problem?"

### Phase 2 — INVESTIGAR
- Who: Etalides (via talk_to or research workflow)
- Input: DESIGN.md v1 sketch
- Output: RESEARCH.md (findings, sources, confidence)
- Gate: Hermes synthesizes → presents options to user

### Phase 3 — DISEÑAR
- Who: Hermes + Christopher (decision)
- Input: RESEARCH.md + DESIGN.md v1
- Output: DESIGN.md v2 (architecture decision, trade-offs, stack)
- Gate: Christopher approves the design

### Phase 4 — PLANIFICAR
- Who: Hermes + Ariadna
- Input: DESIGN.md v2
- Output: PLAN.md (sequenced tasks, assigned by specialty)
- Gate: Ariadna reviews: everything covered? dependencies mapped?

### Phase 5 — PROGRAMAR
- Who: Hefesto + Ergates + Athena
- Input: PLAN.md + DESIGN.md
- Output: Code, tests, TASKS.md updated
- Gate: Athena audits → passes or loops back to Hefesto

## Artifact Taxonomy

| Artifact | Owner | Location | Write Mode | Phase |
|---|---|---|---|---|
| DESIGN.md | Hermes | .eter/.hermes/ | Append-top (v{N}) | 1, 3 |
| RESEARCH.md | Etalides | .eter/.etalides/ | Append-bottom | 2 |
| PLAN.md | Hermes | .eter/.hermes/ | Append-top (Sprint {N}) | 4 |
| TASKS.md | Hefesto | .eter/.hefesto/ | Overwrite (Cycle {N}) | 5 |
| CURRENT.md | Ariadna | .eter/.ariadna/ | Overwrite | session |
| LOG.md | Ariadna | .eter/.ariadna/ | Append-bottom | session |

## .eter/ Convention

```
PROJECT_ROOT/.eter/
├── .hermes/        ← DESIGN.md + PLAN.md (Hermes)
├── .ariadna/       ← CURRENT.md + LOG.md (Ariadna)
├── .hefesto/       ← TASKS.md (Hefesto)
└── .etalides/      ← RESEARCH.md (Etalides)
```

Write rules:
- Append-top: newest version FIRST (v3, v2, v1). Section header includes version + date.
- Append-bottom: chronological order. Newest at bottom.
- Overwrite: single snapshot of current state.
- Every prompt to a Daimon MUST include PROJECT_ROOT as first line of CONTEXT.

## Assignment by Specialty

| Task Type | Primary Daimon | Secondary |
|---|---|---|
| Research (web, docs, CVEs) | Etalides | — |
| UX/UI Design, flows | Daedalus | — |
| Architecture design | Hermes | — |
| Code implementation | Hefesto | Ergates (by role) |
| Security audit | Athena | Hefesto (fixes) |
| Project tracking | Ariadna | — |
| Multi-agent coordination | Hermes | Workflows |

## Decision Matrix — talk_to vs run_workflow vs delegate_task

**Regla principal:**
- `run_workflow` = agents WORK (produce code, artifacts, verifiable results)
- `talk_to` = agents CONSULT (questions, opinions, spot reviews)
- `delegate_task` = simple operational tasks (< 3 steps, no specialist judgment)

| Situation | Tool | Phase |
|---|---|---|
| "Research X for Y" | talk_to(etalides) or research workflow | 2 |
| "Let's design the architecture together" | Direct conversation | 3 |
| "Implement feature X end-to-end" | run_workflow(feature) | 5 |
| "Fix bug Y" | run_workflow(bug-fix) | 5 |
| "Audit security of Z" | run_workflow(security-review) or talk_to(athena) | 5 |
| "Refactor module W" | run_workflow(refactor) | 5 |
| "Initialize new project" | run_workflow(project-init) | 1 |
| "Is exposing this endpoint safe?" | talk_to(athena) | — |
| "What do you think of this architecture?" | talk_to(hefesto) | 3 |
| "Update project status" | talk_to(ariadna) | session |
| "Simple endpoint, 2 files" | delegate_task(backend) | 5 |
```

---

### FASE 2: Olympus README.md — Documentación Técnica

**Archivo:** `src/olympus/README.md`

**Estado actual:** Cubre arquitectura, 6 workflows, HITL mechanism, WorkflowState, error handling, configuración.

**Secciones a agregar:**

1. **MCP Tools API Reference** — Parámetros completos de las 3 tools:
   - `mcp_olympus_talk_to` — agent, action (open|message|poll|wait|cancel|close), prompt, session_id, timeout
   - `mcp_olympus_discover` — sin parámetros, retorna lista de agentes
   - `mcp_olympus_run_workflow` — workflow, prompt, max_review_cycles, params, thread_id, resume

2. **HITL Decision Guide** — Tabla por checkpoint:

   | Checkpoint | Workflow | Question | Options | Resume values |
   |---|---|---|---|---|
   | research_review | feature | ¿Research suficiente? | approve / reject | approve, reject |
   | design_review | feature | ¿Apruebas el diseño? | approve / reject / modify | approve, reject, modify |
   | audit_review | feature | ¿Aplicar fixes de seguridad? | approve / accept_risk / reject | approve, accept_risk, reject |
   | diagnosis_review | bug-fix | ¿Confirmas el diagnóstico? | confirm / reject | confirm, reject |
   | findings_review | security-review | ¿Proceder con fixes? | approve / accept_risk / reject | approve, accept_risk, reject |
   | scope_review | refactor | ¿Apruebas el alcance? | approve / reject | approve, reject |

3. **Daimon-to-Node Mapping** — Qué Daimon ejecuta cada nodo:

   | Node | Daimon | Workflows |
   |---|---|---|
   | research | Etalides | feature, bug-fix, security-review, research, refactor |
   | design | Daedalus | feature |
   | implement | Hefesto | feature, bug-fix, refactor |
   | implement_fix | Hefesto | feature, security-review |
   | audit | Athena | feature, bug-fix, refactor |
   | re_audit | Athena | feature, security-review |
   | onboard | Ariadna | project-init |

4. **Progress Watchdog** — POLL_INTERVAL=10s, STALL_TIMEOUT=120s, safety_timeout=1800s.

5. **Few-Shots para Hermes** — Ejemplos de uso de `talk_to` (open→message→wait) y `run_workflow` (con HITL resume).

6. **Known Pitfalls** — 5 bugs del audit, AsyncSqliteSaver CM, personality overlay, timeout MCP, add_messages vs operator.add.

7. **How to Add a New Workflow** — Paso a paso.

---

### FASE 3: SOUL.md — 7 secciones estandarizadas

**Template estándar (5 Daimons):**

```markdown
# {Name} — {Role}

You are {Name}, {Role} of the Aether Agents team.

## 1. Identity
- **Name:** {Name}
- **Role:** {Role}
- **Eponym:** {Mythological reference — 1 line}

## 2. Execution Context  [IDÉNTICO para Ariadna, Hefesto, Etalides, Daedalus, Athena]

You are invoked by Hermes through the Olympus MCP protocol.

- **Communication**: Self-contained prompt from Hermes (CONTEXT / TASK / CONSTRAINTS / OUTPUT FORMAT).
- **Project Root**: PROJECT_ROOT is the first line of every prompt. All .eter/ paths relative to it. It is also your working directory.
- **Session scope**: Each ACP session is self-contained. Context from current session is available.
- **Scope**: Specialist. Stay in domain. If outside specialty, report to Hermes.
- **Output**: Structured format defined in section 6. Never free-form narrative.
- **Ambiguity**: Return "CLARIFICATION NEEDED: [question]. Cannot proceed until: [what's missing]."
- **Team Playbook**: Orchestration methodology is in Hermes' orchestration skill. Your role: execute your phase, produce your artifact, stay in your domain.

## 3. Core Responsibilities
- [4-6 verb items]

## 4. Limits — What you MUST NOT do
- [Explicit list — same importance as #3]

## 5. Skills
- `aether-agents:{name}-workflow` — operating inside LangGraph workflows
- `{category}:{skill}` — [1 line description]

## 6. Output Format
[Structured template]

## 7. In Workflow Context
[How to interpret accumulated context + workflow_type adaptation]
```

**Execution Context para Hermes** (diferente porque él es el orquestador):

```markdown
## 2. Execution Context
- **Pipeline**: I work in 5 phases: IDEA → RESEARCH → DESIGN → PLAN → PROGRAM.
  Full methodology in skill `aether-agents:orchestration`.
- **Orchestration tools**: talk_to (consult Daimons), run_workflow (multi-agent pipelines), delegate_task (simple tasks).
- **Workflows = agents WORK** (produce artifacts). **talk_to = agents CONSULT** (opinions, reviews).
- **Project Root**: Every Daimon prompt includes PROJECT_ROOT. Daimons write to PROJECT_ROOT/.eter/.
```

**Cambios específicos por Daimon:**

| Daimon | Cambios |
|--------|---------|
| **Hermes** | Execution Context incluye pipeline ref, tools de orquestación, .eter/ OWNERSHIP |
| **Ariadna** | Skills ref: `ariadna-workflow`. Execution Context DRY. Output Format: Status/Blockers/Risks/Next Steps. |
| **Hefesto** | Skills ref: `hefesto-workflow`, `subagent-driven-development`, `systematic-debugging`, `test-driven-development`. Execution Context DRY. |
| **Etalides** | Skills ref: `etalides-workflow`. Output Format: Findings/Sources/Confidence/Limitations. Execution Context DRY. |
| **Daedalus** | Skills ref: `daedalus-workflow`. Output Format: User flow / Layout spec / States / Accessibility. Execution Context DRY. |
| **Athena** | Skills ref: `athena-workflow`. Output Format: Threats/Recommendations/Residual Risk/Confidence. Execution Context DRY. |

---

### FASE 4: Skills — Curación por especialidad

**Mapeo post-curación:**

| Daimon | Categorías | Skills incluidas |
|--------|-----------|-----------------|
| **Ariadna** | aether-agents | ariadna-workflow |
|  | productivity | maps |
|  | note-taking | obsidian |
| **Athena** | aether-agents | athena-workflow |
|  | red-teaming | godmode |
| **Daedalus** | aether-agents | daedalus-workflow |
|  | creative | architecture-diagram, excalidraw |
|  | software-dev | test-driven-development |
| **Etalides** | aether-agents | etalides-workflow |
|  | research | arxiv, llm-wiki, blogwatcher, polymarket |
| **Hefesto** | aether-agents | hefesto-workflow |
|  | software-dev | subagent-driven-development, systematic-debugging, test-driven-development, writing-plans, requesting-code-review, plan |
|  | github | github-pr-workflow, github-issues, github-code-review, github-repo-management, github-auth, codebase-inspection |
|  | mlops | huggingface-hub |
| **Hermes** | TODAS | Orquestador. Sin cambios. |

**Método de limpieza:**

```bash
cd /home/prometeo/Aether-Agents/home/profiles

# Para cada Daimon: borrar todo y recrear con symlinks a home/skills/
# Ejemplo Ariadna:
rm -rf ariadna/skills/*
ln -s ../../../skills/aether-agents ariadna/skills/aether-agents
ln -s ../../../skills/productivity ariadna/skills/productivity
ln -s ../../../skills/note-taking ariadna/skills/note-taking
```

---

### FASE 5: .eter/ state files — Actualización

**5.1 DESIGN.md:**
- Versión v1 (2026-04-19 original) y v2 (2026-04-26 actual con workflow engine + convenciones)
- Limpiar paths Windows → Linux
- Agregar referencia a la orchestration skill como fuente metodológica

**5.2 CURRENT.md:**
- Actualizar de "Sesión 2 — Perfiles (20 abril)" a estado real
- Fase actual: Estandarización de convenciones
- Workflows operativos, Phase 3 completado

**5.3 PLAN.md:**
- Reemplazar con este documento (v2)

---

## Orden de ejecución

```
FASE 1: Orchestration SKILL.md  ← Team playbook (fuente de verdad operativa)
  │
FASE 2: Olympus README.md       ← Documentación técnica (API ref, HITL, pitfalls)
  │
FASE 3: SOUL.md × 6             ← Estandarizar 7 secciones c/u
  │
FASE 4: Skills × 5              ← Curar por especialidad
  │
FASE 5: .eter/ state            ← Actualizar DESIGN.md + CURRENT.md
```

---

## Riesgos y mitigaciones

| Riesgo | Mitigación |
|--------|-----------|
| Skills symlinks rotos | Verificar `hermes -p <name> skills list` post-curación |
| SOUL.md > 20K chars | Mantener < 100 líneas por Daimon. Execution Context DRY. |
| Orchestration SKILL muy extensa | Tablas + listas. Navegable. Ya tiene 600+ líneas, ~200 más es manejable. |
| Olympus README duplica skill | README = técnico (API). SKILL = operativo (metodología). No compiten. |
| Git diff enorme | Un commit por fase. Atómicos. |
