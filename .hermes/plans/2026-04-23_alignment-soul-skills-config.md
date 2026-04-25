# Plan: Alineación SOUL.md, Skills y Config de Daimones

**Fecha:** 2026-04-23
**Problema raíz:** Hermes no delega a los Daimones a pesar de tener la infraestructura completa. Los LLM toman el camino de menor resistencia (ejecutar directamente) en vez de rutear por Olympus.

---

## Diagnóstico (5 problemas — corregido)

| # | Problema | Severidad |
|---|----------|-----------|
| 1 | SOUL.md de Hermes tiene permisos contradictorios (dice "delega" pero tiene todas las herramientas) | Alta |
| 2 | `skills: []` en config.yaml de Daimones — YAML incorrecto (debería ser dict o eliminarse) | Media |
| 3 | No hay enforcement mechanism — nada fuerza a verificar si un task debe delegarse | Alta |
| 4 | Los Daimones no explican su Execution Context (cómo son invocados, sin memoria) | Media |
| 5 | Skill de orchestration no tiene trigger implícito — es contexto pasivo sin pre-flight check | Alta |

**NOTA sobre Problema 2:** Investigando el framework, las skills se descubren automáticamente del directorio `profiles/<name>/skills/` por escaneo del filesystem. La key `skills:` en config.yaml espera un dict (`skills: { disabled: [], external_dirs: [] }`), no una lista. El `skills: []` actual es YAML incorrecto — el framework lo ignora. Las skills YA se están cargando del filesystem. El fix es limpiar el YAML, no agregar referencias.

---

## Plan por Fase

### FASE 1: Hermes — Enforcement de Delegación (Problemas 1, 3, 5)

**Objetivo:** Crear mecanismos obligatorios que fuerzan a verificar delegación antes de ejecutar.

#### 1.1 Modificar `home/profiles/hermes/SOUL.md`

**Agregar sección nueva** entre "Core Responsibilities" y "Limits":

```markdown
## Delegation Gates — MANDATORY CHECKS

Before using any execution tool (terminal, write_file, web_search, execute_code, read_file, patch), run this check:

1. **Is this a task that belongs to a Daimon?**
   - Code implementation or debugging → Hefesto via talk_to()
   - Web research beyond a single quick fact → Etalides via talk_to()
   - UX/UI design, layouts, user flows → Daedalus via talk_to()
   - Security review, threat modeling → Athena via talk_to()
   - Project status, sprint tracking, session state → Ariadna via talk_to()

2. **Is this a simple task (< 3 steps, no specialist judgment needed)?**
   - YES → Use delegate_task with an internal sub-agent
   - NO → Route to the appropriate Daimon via talk_to()

3. **Am I doing something a Daimon should be doing right now?**
   - If YES → STOP. Delegate instead.

Exceptions where Hermes executes directly:
- Reading files to gather context before delegating
- Simple web_search for a single quick fact (one query, no deep research)
- Writing .eter/ state files (DESIGN.md, PLAN.md — Hermes owns these)
- Communicating with the user (always Hermes, never delegates user-facing interaction)
- Coordinating Daimon sessions (open/message/poll/close on Olympus)

This is not optional. Every execution action must pass through this gate.
```

**Modificar la sección "Limits"** — reemplazar la lista completa:

```markdown
## Limits — What you MUST NOT do
- Do NOT implement code yourself — delegate to Hefesto via talk_to()
- Do NOT research the web deeply — delegate to Etalides via talk_to() (quick single web_search is OK for a fact)
- Do NOT manage project state yourself — delegate to Ariadna via talk_to()
- Do NOT make product decisions alone — present options, user decides
- Do NOT chain Daimons without user visibility — gate at each step
- Do NOT send vague prompts to Daimons — always use the full delegate template
- Do NOT skip session close — always update state with Ariadna when session ends
- Do NOT skip the Delegation Gate check — verify before every execution action
```

#### 1.2 Modificar `home/profiles/hermes/skills/aether-agents/orchestration/SKILL.md`

**Agregar AL INICIO** del archivo, antes de la sección "Core Principle":

```markdown
## ⚠️ PRE-FLIGHT CHECKLIST — Execute Before EVERY Response

Before responding to any user request, check:

- [ ] **Does this involve writing/implementing code?** → talk_to(agent="hefesto")
- [ ] **Does this involve web research (more than a quick fact check)?** → talk_to(agent="etalides")
- [ ] **Does this involve UX/UI design, layouts, user flows?** → talk_to(agent="daedalus")
- [ ] **Does this involve security, threat modeling, vulnerability review?** → talk_to(agent="athena")
- [ ] **Does this involve project status, sprint tracking, session state?** → talk_to(agent="ariadna")
- [ ] **Is this a simple operational task (< 3 steps)?** → delegate_task (no specialist needed)

If ANY check is YES → DELEGATE, do NOT execute yourself.
Exception: Hermes can use web_search for a single quick fact, read files for context, and write .eter/ state files.

This checklist is MANDATORY. Skipping it means doing a Daimon's job directly.
```

---

### FASE 2: Config.yaml — Limpiar YAML de Daimones (Problema 2)

**Objetivo:** Corregir el YAML incorrecto `skills: []` en los config de Daimones.

Las skills se cargan automáticamente del filesystem. El `skills: []` en config.yaml es YAML incorrecto (el framework espera un dict). Debería eliminarse o cambiarse al formato correcto.

**Acción por archivo:**

| Archivo | Cambio |
|---------|--------|
| `home/profiles/ariadna/config.yaml` | Cambiar `skills: []` → `skills: {}` (o eliminar la línea, ya que se cargan del filesystem) |
| `home/profiles/hefesto/config.yaml` | Cambiar `skills: []` → `skills: {}` |
| `home/profiles/etalides/config.yaml` | Cambiar `# Skills — methodology built into SOUL.md, no separate skills\nskills: []` → `skills: {}` |
| `home/profiles/daedalus/config.yaml` | Cambiar `# Skills — Aether-specific (to be created)\nskills: []` → `skills: {}` |
| `home/profiles/athena/config.yaml` | Cambiar `# Skills — Aether-specific (to be created)\nskills: []` → `skills: {}` |

---

### FASE 3: SOUL.md de Daimones — Agregar Execution Context (Problema 4)

**Objetivo:** Cada Daimón sabe cómo es invocado y que no tiene memoria entre sesiones.

**Sección a agregar en cada SOUL.md de Daimón** (después de "Anti-Bias Rule"):

```markdown
## Execution Context

You are invoked by Hermes through the Olympus MCP protocol. Key facts:

- **Communication**: You receive a self-contained prompt from Hermes with CONTEXT / TASK / CONSTRAINTS / OUTPUT FORMAT. You execute the task and return structured output. You do NOT speak to the user — all output goes back to Hermes.
- **No memory**: You have NO memory between sessions. Every task is self-contained. Do NOT assume context from previous invocations.
- **Scope**: You are a specialist. Stay in your domain. If the task requires work outside your specialty, report back to Hermes — do not attempt it yourself.
- **Output**: Always use the structured output format defined in your SOUL.md. Never free-form narrative.
- **Ambiguity**: If the task is unclear or missing context, return immediately: "CLARIFICATION NEEDED: [specific question]. Cannot proceed until: [what is missing]."
```

**Archivos a modificar:**

| Archivo | Nombre en sección |
|---------|-------------------|
| `home/profiles/ariadna/SOUL.md` | Ariadna |
| `home/profiles/hefesto/SOUL.md` | Hefesto |
| `home/profiles/etalides/SOUL.md` | Etalides |
| `home/profiles/daedalus/SOUL.md` | Daedalus |
| `home/profiles/athena/SOUL.md` | Athena |

---

### FASE 4: Verificación

**Objetivo:** Confirmar que los cambios producen el comportamiento esperado.

#### 4.1 Test de Skills Loading
Levantar cada Daimón y verificar que sus skills se cargan en el contexto del system prompt.

#### 4.2 Test de Delegation Enforcement
En la próxima sesión de Hermes:
1. Request de código → verificar que Hermes delega a Hefesto (no lo hace él)
2. Request de investigación → verificar que Hermes delega a Etalides
3. Request de session close → verificar que Hermes delega a Ariadna

#### 4.3 Test de Execution Context
Enviar un prompt incompleto a un Daimón y verificar que responde "CLARIFICATION NEEDED" en vez de intentar ejecutar con contexto faltante.

---

## Orden de Ejecución

```
FASE 1 (Hermes enforcement) → FASE 2 (config YAML) → FASE 3 (SOUL.md Daimones) → FASE 4 (verificación)
```

Las Fases 2 y 3 se pueden hacer en paralelo si se quiere.

---

## Archivos Totales a Modificar

| # | Archivo | Fase | Tipo cambio |
|---|---------|------|-------------|
| 1 | `home/profiles/hermes/SOUL.md` | 1 | Agregar sección "Delegation Gates", modificar "Limits" |
| 2 | `home/profiles/hermes/skills/aether-agents/orchestration/SKILL.md` | 1 | Agregar "PRE-FLIGHT CHECKLIST" arriba |
| 3 | `home/profiles/ariadna/config.yaml` | 2 | `skills: []` → `skills: {}` |
| 4 | `home/profiles/hefesto/config.yaml` | 2 | `skills: []` → `skills: {}` |
| 5 | `home/profiles/etalides/config.yaml` | 2 | `skills: []` → `skills: {}` |
| 6 | `home/profiles/daedalus/config.yaml` | 2 | `skills: []` → `skills: {}` |
| 7 | `home/profiles/athena/config.yaml` | 2 | `skills: []` → `skills: {}` |
| 8 | `home/profiles/ariadna/SOUL.md` | 3 | Agregar "Execution Context" |
| 9 | `home/profiles/hefesto/SOUL.md` | 3 | Agregar "Execution Context" |
| 10 | `home/profiles/etalides/SOUL.md` | 3 | Agregar "Execution Context" |
| 11 | `home/profiles/daedalus/SOUL.md` | 3 | Agregar "Execution Context" |
| 12 | `home/profiles/athena/SOUL.md` | 3 | Agregar "Execution Context" |

**Total: 12 archivos, 4 fases**

---

## Riesgos

1. **Token count**: Agregar secciones a SOUL.md aumenta el system prompt. Verificar que no exceda límites del modelo. Estimado: +300 tokens por SOUL.md de Daimón, +150 tokens para Hermes.
2. **Enforcement no es 100% garantizado**: Los LLM pueden leer "MANDATORY CHECK" e ignorarlo. Es un efecto soft. Si persiste, la solución más fuerte sería restringir los toolsets de Hermes (quitar herramientas de ejecución) — pero eso es invasivo y rompería los casos donde sí necesita ejecutar directamente.
3. **Skills loading**: Aunque las skills se descubren del filesystem, confirmar que los Daimones spawnados por Olympus sí las cargan correctamente. Tested in Fase 4.

---

## Correcciones vs Plan Original (v1)

- **Problema 2 corregido:** Las skills YA se cargan del filesystem automáticamente. El `skills: []` es YAML incorrecto pero no bloquea la carga. El fix es limpiar el YAML, no agregar referencias explícitas.
- **Problema 6 eliminado:** Se fusionó con Problema 1 (es el mismo problema: permisos contradictorios en Hermes).
- **Total de archivos reducido:** De 13 a 12 (se eliminó el cambio de skills por categorías en config.yaml).