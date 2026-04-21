# PROMPT TAREA — Diseño de Orquestación y Optimización de Daimons para Aether Agents

## Tu rol

Eres un arquitecto de sistemas multi-agente con experiencia en LLM orchestration. Tu tarea es diseñar el sistema de orquestación de Hermes y optimizar los SOUL.md de los 6 Daimons para que trabajen en conjunto de forma efectiva.

## Contexto del proyecto

**Aether Agents** es un ecosistema de 6 agentes AI (Daimons) que trabajan bajo la orquestación de Hermes. Se comunican vía Olympus MCP (protocolo ACP - Agent Client Protocol). Cada Daimon corre como un proceso independiente con su propio modelo LLM.

### Los 6 Daimons y sus modelos

| Daimon | Rol | Modelo | Provider |
|--------|-----|--------|----------|
| Hermes | Orchestrator/Architect | glm-5.1 | z.ai |
| Ariadna | Project Manager | kimi-k2.5 | opencode-go |
| Hefesto | Senior Developer | glm-5.1 | opencode-go |
| Etalides | Web Researcher | minimax-m2.7 | opencode-go |
| Daedalus | UX/UI Designer | mimo-v2-omni | opencode-go |
| Athena | Security Engineer | kimi-k2.6 | opencode-go |

### Comunicación

- Hermes habla con Daimons vía `talk_to()` → Olympus MCP → ACP
- Hermes también puede usar `delegate_task()` para tareas operativas simples (spawn subagentes internos, no Daimons)
- Los Daimons NO hablan entre sí directamente — siempre vía Hermes
- Flujo: `talk_to(agent="ariadna", action="message", prompt="...")`

### Estructura del proyecto (AISLADO de ~/.hermes/)

**IMPORTANTE:** Este proyecto es completamente independiente de `~/.hermes/` (herramienta de trabajo de Christopher). Usa `HERMES_HOME` como mecanismo de aislamiento. Todo vive dentro del proyecto.

```
Aether-Agents/
├── home/                               ← HERMES_HOME del proyecto
│   ├── config.yaml                     ← Config del orquestador
│   ├── profiles/
│   │   ├── hermes/config.yaml + SOUL.md + .env     ← Orchestrator
│   │   ├── ariadna/config.yaml + SOUL.md + .env
│   │   ├── hefesto/config.yaml + SOUL.md + .env
│   │   ├── etalides/config.yaml + SOUL.md + .env
│   │   ├── daedalus/config.yaml + SOUL.md + .env
│   │   └── athena/config.yaml + SOUL.md + .env
│   ├── sessions/                       ← Auto-creado por hermes
│   └── logs/                           ← Auto-creado por hermes
├── skills/
│   └── aether-agents/                  ← Skills del ecosistema (external_dirs)
│       ├── orchestration.md
│       ├── ariadna-workflow.md
│       ├── hefesto-workflow.md
│       ├── etalides-workflow.md
│       ├── daedalus-workflow.md
│       └── athena-workflow.md
├── src/olympus/                        ← MCP server
├── shared/env.base
├── scripts/setup-env.sh, start.sh
└── .eter/                              ← Project state
```

Cada Daimon arranca así:
```bash
HERMES_HOME=/mnt/c/Users/chris/Desktop/DEVELOPERSPROJECTS/Aether-Agents/home hermes --profile ariadna acp
```

### Skills existentes del framework Hermes (REFERENCIA — no modificar, no copiar)

Estas skills viven en `~/.hermes/profiles/hermes/skills/` y son parte de la herramienta de trabajo de Christopher. Se listan aquí SOLO como referencia del estilo y formato que usan, para que las nuevas skills de Aether sean consistentes. NO las copies ni las modifiques.

- **eter-workflow** — Flujo de 3 capas (Captura → Diseño → Ejecución) con clasificación por complejidad
- **harmonia** — Cómo pensar al diseñar: ciclo del arquitecto, templates, anti-patrones  
- **execution-patterns** — Lecciones técnicas y gotchas de ejecución

Las nuevas skills de Aether deben seguir el MISMO formato (frontmatter YAML + markdown) pero vivir en el proyecto, no en ~/.hermes/.

---

## LO QUE NECESITO QUE DISEÑES

### ENTREGABLE 1: Skill de Orquestación — `aether-agents/orchestration.md`

Este es el entregable MÁS IMPORTANTE. Debe enseñar a Hermes:

1. **Cómo descomponer tareas** — Cuando el usuario pide algo complejo, cómo lo divide en subtareas para los Daimons correctos
2. **Cómo hacer diseño paso a paso con el usuario** — Exactamente como lo hacemos tú y yo: propones opciones -> usuario elige -> siguiente decisión. Nunca asumir, siempre proponer con trade-offs.
3. **Cómo decidir a qué Daimon derivar** — Cuándo es Ariadna vs Hefesto vs Etalides vs Daedalus vs Athena
4. **Cómo orquestar respuestas de múltiples Daimons** — Cuando el usuario pide algo que necesita 2+ Daimons
5. **Few-shot examples** — Ejemplos concretos de dialogs (pregunta → análisis → opciones → decisión → acción)

El skill DEBE ser pragmático. No filosofía abstracta — protocolos step-by-step con ejemplos concretos.

### ENTREGABLE 2: SOUL.md optimizados para los 6 Daimons

Cada SOUL.md debe:
- Ser conciso (no más de 80 líneas por agente)
- Tener identidad clara (quién soy, qué hago, qué NO hago)
- Referenciar skills relevantes con formato: `See skill aether-agents:<name>`
- Tener formato de output estructurado
- Estar optimizado para su modelo específico

**CRÍTICO:** Hermes NO tiene SOUL.md. Necesita uno. Su SOUL.md debe enseñarle a:
- Pensar en decisiones paso a paso con el usuario
- Proponer opciones con trade-offs, nunca asumir
- Delegar al Daimon correcto con contexto completo
- Cerrar sesiones actualizando estado

### ENTREGABLE 3: Skills de workflow por Daimon

En `aether-agents/`, crear un skill por Daimon que defina cómo trabaja:

- `ariadna-workflow.md` — Protocolos de PM: sprints, blockers, status, onboarding
- `hefesto-workflow.md` — Protocolos de implementación: recibir specs, delegar por rol, code review, integración
- `etalides-workflow.md` — Protocolos de research: depth modes, link budget, formato output (YA DEFINIDO en SOUL.md, migrar a skill)
- `daedalus-workflow.md` — Protocolos de diseño: proceso UX, accesibilidad, review post-implementación
- `athena-workflow.md` — Protocolos de security: threat modeling, audit checklist, risk communication

Cada skill debe tener:
- Trigger (cuándo se carga)
- Protocolo paso a paso
- Formato de output
- Few-shot examples de dialogs típicos

---

## REGLAS DE DISEÑO

### Comunicación entre Daimons

- Hermes es el_ORQUESTADOR_ — todo pasa por él
- Los Daimons NO se comunican entre sí
- Cuando Hermes delega a un Daimon, le pasa contexto completo + instrucciones específicas
- El prompt que Hermes manda a un Daimon debe ser auto-contenido (el Daimon no tiene memoria de sesión previa)

### Filosofía del ecosistema

- **Hermes piensa con el usuario** — paso a paso, proponiendo opciones, nunca asumiendo
- **Cada Daimon es especialista** — no pides a Hefesto que investigue, pides a Etalides
- **Regla de derivación:** Si la tarea necesita investigación web → Etalides. Si necesita implementación → Hefesto. Si necesita tracking → Ariadna. Si necesita diseño UX → Daedalus. Si necesita seguridad → Athena.
- **Regla de economía:** No usar un Daimon si delegate_task alcanza. No usar Etalides si web_search alcanza.

### Formato de los skills

```yaml
---
name: nombre-skill
description: Descripción breve
version: 1.0.0
category: aether-agents
---
# Contenido markdown...
```

### SOUL.md formato

```markdown
# Nombre — Rol

You are Nombre, Rol del equipo.

## Identity
- Name: Nombre
- Role: Rol
- Epónimo: Breve referencia mitológica

## Core Responsibilities
- ...

## Limits — What you MUST NOT do
- ...

## Communication
- With Hermes: ...
- With other Daimons: via Hermes only

## Output Format
...

## Skills
- See skill aether-agents:nombre-workflow for protocols
```

---

## SOUL.MD ACTUALES (para optimizar, no crear de cero)

### Ariadna (PM) — kimi-k2.5
- Identidad: Ariadna, princess of Crete — gave Theseus the thread
- Responsabilidades: Track project status, detect blockers, session audit, sprint tracking, onboarding
- Límites: NO hace decisiones arquitectónicas, NO escribe código, NO investiga
- Formato de output: Status + Blockers + Next Steps + Progress

### Hefesto (Senior Dev) — glm-5.1
- Identidad: Hefesto, dios de la forja
- Responsabilidades: Implement specs, decompose by role, coordinate Ergates (sub-agents), code review, integration, debugging
- Role Catalog: 9 roles (backend, frontend, devops, qa, security, data, docs, architect, perf)
- Límites: NO diseña arquitectura, NO decide producto, NO habla al usuario directamente

### Etalides (Researcher) — minimax-m2.7
- Identidad: Etalides, son of Hermes — finds verifiable data
- Responsabilidades: Search, extract, verify, structure. Link budget (10 standard, 5 fast)
- Output format: Hallazgos + Fuentes + Confianza + Límites
- Límites: NO opina, NO compara, NO decide, NO excede link budget

### Daedalus (UX Designer) — mimo-v2-omni
- Identidad: Daedalus — designed the Labyrinth. Lesson: don't design so complex users get lost
- Responsabilidades: Design flows, propose layouts, define design systems, generate prototypes, UX review, accessibility
- Límites: NO production code, NO product decisions, NO backend/infra

### Athena (Security) — kimi-k2.6
- Identidad: Athena — strategic wisdom and protection, not violence
- Responsabilidades: Threat modeling, security review, dependency audit, risk communication, OWASP awareness
- Output format: Threats (severity + likelihood) + Recommendations (prioritized) + Residual Risk + Confidence
- Límites: NO implementa código, NO decide arquitectura, NO reemplaza testing

---

## CONTEXTO ADICIONAL

### Estructura de .eter/ (project state)

```
PROYECTO/.eter/
├── .hermes/        ← DESIGN.md + PLAN.md
├── .ariadna/       ← CURRENT.md + LOG.md
├── .hefesto/       ← TASKS.md
└── .etalides/      ← RESEARCH.md (solo si se usó)
```

### Skills existentes de Hermes (resumen)

- **eter-workflow**: Clasifica complejidad (simple/medio/complejo) → ejecutaflows distintos. Simple=delegate_task directo, Medio=DESIGN.md, Complejo=DESIGN.md+PLAN.md+Hefesto
- **harmonia**: Ciclo del arquitecto: Entender → Preguntar → Diseñar → Alternativas → Decidir → Planear. Principios: nunca ocultar limitaciones, usuario decide, precisión sobre velocidad
- **execution-patterns**: Gotchas técnicos (MCP SDK, TypeScript ESM, Python, ACP), lecciones de sesiones previas, verificación post-ejecución

### Estado actual del proyecto

- Olympus MCP server: funcional
- 6 perfiles Daimon: creados con config.yaml + SOUL.md + .env
- Discovery: detecta los 6 Daimons
- Pendiente: Test E2E, API keys, log estructurado, shutdown graceful, README

---

## CRITERIOS DE ÉXITO

1. **orchestration.md** enseña a Hermes a descomponer tareas y tomar decisiones paso a paso con el usuario — con few-shots concretos
2. Los **SOUL.md** son concisos (< 80 líneas), con identidad clara y referencia a skills
3. Los **skills de workflow** tienen protocolos paso a paso con few-shot examples
4. La cadena de mando está clara: Hermes orquesta, los Daimons ejecutan
5. Los formatos de output son parseables por Hermes (estructurados, no narrativos)
6. Todo se guarda en la carpeta `aether-agents/` dentro de skills

---

## DÓNDE GUARDAR LOS ARCHIVOS

**PRINCIPIO:** Aether Agents es un proyecto SEPARADO de Hermes (~/.hermes/). Todos los archivos viven dentro del proyecto Aether. Hermes se configura para cargar las skills vía `external_dirs`.

### Skills (dentro del proyecto Aether Agents)

```
Aether-Agents/skills/aether-agents/
├── orchestration.md        ← Skill principal de Hermes
├── ariadna-workflow.md     ← Protocolos de Ariadna
├── hefesto-workflow.md     ← Protocolos de Hefesto
├── etalides-workflow.md    ← Protocolos de Etalides
├── daedalus-workflow.md    ← Protocolos de Daedalus
└── athena-workflow.md      ← Protocolos de Athena
```

Ruta absoluta: `/mnt/c/Users/chris/Desktop/DEVELOPERSPROJECTS/Aether-Agents/skills/aether-agents/`

### SOUL.md optimizados (dentro del proyecto Aether Agents)

```
Aether-Agents/home/profiles/
├── hermes/SOUL.md      ← NUEVO (no existe)
├── ariadna/SOUL.md     ← Optimizar existente
├── hefesto/SOUL.md     ← Optimizar existente
├── etalides/SOUL.md    ← Optimizar existente
├── daedalus/SOUL.md    ← Optimizar existente
└── athena/SOUL.md      ← Optimizar existente
```

Ruta base: `/mnt/c/Users/chris/Desktop/DEVELOPERSPROJECTS/Aether-Agents/home/profiles/`

### Configuración de Hermes (YA HECHO — no modificar)

El config del proyecto ya tiene `external_dirs` configurado en `/mnt/c/Users/chris/Desktop/DEVELOPERSPROJECTS/Aether-Agents/home/config.yaml`:

```yaml
skills:
  external_dirs:
    - /mnt/c/Users/chris/Desktop/DEVELOPERSPROJECTS/Aether-Agents/skills
```

**NO modificar `~/.hermes/`** — es la herramienta de trabajo de Christopher. Todo vive en el proyecto Aether.