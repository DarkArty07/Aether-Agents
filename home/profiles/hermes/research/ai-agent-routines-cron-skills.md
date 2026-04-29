# Investigación: Rutinas, Skills y Automatización con Cron Jobs para Agentes IA

> Fecha: 2026-04-28 | Fuente: 10+ artículos de producción, frameworks y guías técnicas

---

## 1. ARQUITECTURA BASE: Los 3 Pilares de un Agente Autónomo

Un agente IA productivo necesita 3 capas operativas que trabajan juntas:

```
┌─────────────────────────────────────────────────┐
│                AGENTE AUTÓNOMO                   │
│                                                  │
│  ┌──────────┐  ┌──────────┐  ┌──────────────┐   │
│  │ HEARTBEAT │  │   CRON   │  │   MEMORIA    │   │
│  │ (Pulso)  │  │ (Horario)│  │  (Alma)      │   │
│  │          │  │          │  │              │   │
│  │ Conscien-│  │ Precisión│  │ Persistencia │   │
│  │ cia am-  │  │ temporal │  │ multi-capa   │   │
│  │ biental  │  │ exacta   │  │              │   │
│  └──────────┘  └──────────┘  └──────────────┘   │
│       ↓             ↓              ↓             │
│  "¿Necesito    "A las 9AM      "Lo que sé       │
│   hacer algo?"  publicar"      de sesiones       │
│                                  pasadas"       │
└─────────────────────────────────────────────────┘
```

### 1.1 Heartbeat (Pulso) — Consciencia Ambiental

- **Qué es:** Señal periódica (cada 5-30 min) que "despierta" al agente para evaluar su entorno
- **Para qué:** Monitoreo pasivo, revisiones de bandeja, checks de salud
- **Costo:** Bajo — un turno cada N minutos; si no hay nada que hacer, devuelve `HEARTBEAT_OK` y duerme
- **Tiene contexto:** Accede al historial de conversación reciente

### 1.2 Cron (Horario) — Precisión Temporal

- **Qué es:** Tareas que disparan a hora exacta usando expresiones cron estándar
- **Para qué:** Reportes diarios, publicación programada, limpieza nocturna, análisis pesado
- **Costo:** Turno completo por job; puede usar modelo más barato por job
- **Sin contexto:** Arranca limpio cada vez (cold start) — requiere prompts auto-contenidos

### 1.3 Cuándo usar cada uno

| Caso de uso | Recomendado | Por qué |
|---|---|---|
| Revisar inbox cada 30 min | Heartbeat | Batchea con otros checks, contextual |
| Enviar reporte diario a las 9AM | Cron (aislado) | Timing exacto requerido |
| Monitorear calendario | Heartbeat | Ajuste natural a periodicidad |
| Análisis profundo semanal | Cron (aislado) | Tarea standalone, puede usar otro modelo |
| Recordarme en 20 min | Cron (one-shot) | Timing preciso, una sola vez |
| Health check de proyecto | Heartbeat | Se sube al ciclo existente |

**Regla de oro:** Cron = precisión aislada. Heartbeat = consciencia ambiental. No mezclarlos.

---

## 2. LAS 5 REGLAS DE ORO PARA CRON AGENTS (Production-Proven)

De: "The Cron Agent Pattern" — probado con 0 misfires en 30 días tras implementar.

### Regla 1: Recargar identidad en CADA ejecución

Cada sesión cron arranca fresca. Si no recargas el archivo de identidad (SOUL.md o equivalente), el agente inventa una identidad desde el contexto reciente → deriva de personalidad.

```bash
# Cada cron job DEBE empezar así
*/30 * * * * agent run --instruction "Read SOUL.md and MEMORY.md first. Then..."
```

### Regla 2: Escribir estado ANTES de actuar

Antes de ejecutar, escribir qué va a hacer. Previene duplicados si cron dispara dos veces y crea audit trail.

```json
{
  "task": "publicar tweet matutino",
  "started": "2026-04-28T09:00:00Z",
  "status": "in_progress",
  "next_action": "redactar tweet desde cola de contenido"
}
```

### Regla 3: Condición de salida HARD

Definición concreta de "terminado" que NO requiere juicio subjetivo.

- **MAL:** "Parar cuando la tarea se sienta completa"
- **BIEN:** "Parar cuando se publicó 1 tweet y se logueó en content/daily/2026-04-28.md"

### Regla 4: Regla de silencio

Agentes que corren a las 3AM NO deben enviar emails, postear en redes, o mensajar gente dormida.

```markdown
# En SOUL.md
Regla de silencio: No enviar mensajes salientes entre 22:00-07:00 CST
a menos que estén explícitamente marcados como urgentes por el humano.
```

### Regla 5: Separar Heartbeats de Cron

- **Heartbeat:** batches de checks pequeños (inbox + calendario + Slack en 1 turno)
- **Cron:** 1 tarea específica, ejecución completa, output limpio
- **NO** hacer heartbeats pesados que hagan demasiado, ni cron jobs que "chequeen de paso"

---

## 3. EL AGENT LOOP — Patrón Anti-Runaway

Este ciclo de 11 pasos previene los 4 modos de fallo de agentes programados:
1. **State accumulation** — heredar ruido de runs anteriores
2. **Silent errors** — hacer lo incorrecto con confianza sin crashear
3. **Task scope creep** — decisiones menores que escalan en dirección
4. **Identity drift** — perder gradualmente la personalidad/instrucciones

```
AGENT LOOP (ejecutar en CADA disparo de cron):

1.  Leer SOUL.md (identidad)
2.  Leer MEMORY.md (contexto largo plazo)
3.  Leer current-task.json (¿qué estaba haciendo?)
4.  Si tarea completada → escribir log de completado → EXIT
5.  Si tarea in_progress → verificar última acción → retomar
6.  Si no hay tarea → leer cola de tareas → tomar siguiente
7.  Escribir estado de tarea ("empezando X")
8.  Ejecutar tarea
9.  Escribir estado de completado
10. Escribir en memory/YYYY-MM-DD.md
11. EXIT limpio
```

**Resultado real:** Antes del patrón ~3 misfires/semana. Después: 0 en 30 días. Costo: despreciable (lectura de archivos al inicio).

---

## 4. SISTEMAS DE MEMORIA — El Alma del Agente

### 4.1 Arquitectura de 5 Niveles (Production-Proven, 20+ agentes)

```
L1: Session Memory    — Historial de conversación inmediato (volátil)
L2: CONTEXT.md        — Actualizado tras cada acción significativa
                       Responde: "¿Qué estoy haciendo AHORA?"
L3: Daily Notes       — Log de todo lo que pasó hoy (YYYY-MM-DD.md)
                       Crítico para reportes end-of-day
L4: MEMORY.md         — Conocimiento permanente largo plazo
                       Preferencias, decisiones arquitectónicas, reglas
L5: RAG/Vector DB     — Búsqueda semántica a gran escala
                       Pinecone/Milvus/Chroma para miles de documentos
```

**Regla de oro:** "Lo escribo después" está PROHIBIDO. El agente DEBE escribir estado a L2/L3 inmediatamente tras completar cada sub-tarea.

### 4.2 Sistema de Memoria con Archivos Markdown (Simple, Sin vectores)

```
~/.agent/
├── learnings.md          # Conocimiento curado (cargado cada sesión, <100 líneas)
├── observations.md       # Observaciones crudas capturadas en el momento
├── goals.md              # Objetivos activos con progreso
├── data/
│   ├── daily-logs/       # YYYY-MM-DD.md logs de tareas
│   ├── analytics/        # Snapshots de datos estructurados
│   └── drafts/           # Trabajo en progreso
└── skills/               # Recetas de tareas reutilizables
```

**Clave:** learnings.md < 100 líneas. Si crece más, el agente gasta demasiados tokens en contexto irrelevante. Curar agresivamente.

### 4.3 Pipeline de Promoción de Memoria (Nightly "Dreaming")

```
Proceso nocturno (3 AM):

FASE LIGERA:
  - Ingesta: daily notes + transcripciones de sesión del día
  
FASE PROFUNDA:
  - Scoring y promoción de señales fuertes → MEMORY.md
  - Pesos: relevancia 0.30 | frecuencia 0.24 | recencia 0.15
  
FASE REM:
  - Extracción de temas y patrones

GATE DE GRADUACIÓN — nada promociona a MEMORY.md sin:
  - Score >= 0.70 (relevancia + frecuencia + recencia ponderada)
  - Recalls >= 2 (la señal fue recuperada Y usada al menos 2 veces)
  - Contenido es regla/preferencia/hecho durable — NO fragmento crudo
```

### 4.4 Memoria en Git (Versionable, Distribuible, Auditable)

```
.agents/memory/
├── finance/
│   ├── state.md           # Estado actual del squad
│   ├── learnings.md       # Lo aprendido
│   └── feedback.md        # Feedback de ejecución
├── engineering/
│   ├── state.md
│   └── ...
└── .last-sync             # Timestamp de sync con git
```

Ventajas de git: versionado de cambios en memoria, trabajo offline con sync al reconectar, múltiples agentes pueden trabajar en paralelo y hacer merge, audit trail completo.

---

## 5. SKILLS AGENTICOS — Lo Que Convierte un Agente en Compañero Real

### 5.1 Qué Hace un Skill "Agentic" (vs prompt estático)

Un skill agentic tiene:
- **Tool bindings** — ejecutar comandos shell, query DBs, llamar APIs, leer/escribir archivos
- **Memory access** — recuerda entre días/semanas/meses
- **State management** — trackea pending/done/failed, retoma donde quedó
- **Permissions** — sabe qué es autónomo vs qué requiere aprobación humana
- **Cross-agent coordination** — sincroniza con otros agentes, comparte learnings

### 5.2 Los 12 Skills Production-Grade (Resumen)

#### Skills de Memoria y Aprendizaje

**1. Deep Recall** — "Nunca digas 'no sé' sin buscar primero"
- Cascada de búsqueda obligatoria en 5 capas antes de responder sobre eventos pasados
- Orden: memory_search → FTS5 → DB query → grep daily/ → grep context files
- Insight: Layer 3 (raw DB queries) es la que más salva. Buscar en storage crudo primero, semántico después.

**2. Memory Tiering** — Pipeline de promoción de notas diarias a memoria durable
- 3 tiers: HOT (sesión actual) → WARM (preferencias estables) → COLD (MEMORY.md curado)
- Proceso nocturno de "dreaming" con gate de graduación

**3. Self-Learning** — "Convertir correcciones en mejoras concretas"
- Cuando corrigen al agente, falla una tarea, o se descubre mejor forma → log + causa raíz + fix durable
- Barra de calidad: un learning solo está completo cuando un skill fue mejorado O una instrucción rota fue removida
- Auto-flag: si un skill falla 3+ veces en 14 días → se reescribe

#### Skills de Coordinación y Red

**4. Agent Network Sync** — Sincronización diaria entre múltiples agentes
- Cada mañana a las 9:15, los agentes sincronizan estado, comparten blockers
- Cada agente trae su propio contexto de dominio. Ninguno ve el estado privado de otro.

**5. Cross-Session Awareness** — Saber todo sin duplicar nada
- Bridge entre sesiones aisladas: escanea sesiones activas, construye contexto unificado

#### Skills de Ejecución y Control

**6. Task Queue Management** — Cola de tareas con prioridad y reintentos
- Priorización automática: critical > high > medium > low
- Retry con backoff exponencial para fallos transitorios

**7. Permission Boundaries** — Qué es autónomo vs qué necesita humano
- Tres niveles: AUTONOMOUS (ejecutar libre) / NEEDS_APPROVAL (pausar y esperar OK) / FORBIDDEN (nunca permitido)
- Definido en GOALS.md por agente

**8. Scheduled Execution** — El skill de correr cosas en horario
- Wrapper de cron que agrega: timeouts, locks contra overlap, idempotency checks, logging

**9. Bounded Outputs** — Cada run produce algo concreto
- Un log line, un archivo, un mensaje, un digest, una métrica
- NUNCA un run que termina sin dejar rastro

#### Skills de Calidad y Seguridad

**10. Error Recovery** — Recuperación automática de errores
- Detecta fallos por tipo: API timeout, auth error, rate limit, bad output
- Estrategia por tipo: retry con backoff, re-auth, esperar y reintentar, escalar a humano

**11. Cost Guard** — Monitoreo y control de costos
- Track de tokens por job, por día, por agente
- Budget limits por job programado (prevenir runaway costs)
- Alertas cuando se pasa de umbral

**12. Audit Trail** — Historial completo de cada acción
- Cada acción del agente queda logged: timestamp, acción, resultado, tokens usados
- Consultable para debugging y compliance

---

## 6. ESTRUCTURA DE SKILL — Cómo Definirlos

### 6.1 Formato de Skill (Markdown)

```markdown
---
name: morning-briefing
trigger: always_loaded | on_demand | cron_scheduled
tools: [web_search, read_file, write_file, send_message]
model: sonnet          # modelo recomendado
timeout: 120           # segundos máximos
permission: autonomous # autonomous | needs_approval | forbidden
---

# Morning Briefing Skill

## When
Correr cada día a las 7:30 AM (cron: `30 7 * * *`)

## What
1. Leer MEMORY.md y CONTEXT.md para estado actual
2. Buscar noticias relevantes del día
3. Leer calendario del día
4. Compilar briefing con: noticias + calendario + tareas pendientes
5. Enviar briefing por Telegram
6. Escribir log en data/daily-logs/YYYY-MM-DD.md

## Rules
- No enviar entre 22:00-07:00 (regla de silencio)
- Si no hay nada nuevo, enviar "HEARTBEAT_OK" y no molestar
- Leer LEARNINGS.md antes de ejecutar, escribir en él después
- Timeout: 120 segundos máximo
```

### 6.2 Skill con Auto-Mejora (Compounding Loop)

```markdown
## Self-Improvement Rule

Al final de CADA ejecución:
1. Leer LEARNINGS.md
2. Evaluar: ¿Qué funcionó? ¿Qué falló? ¿Edge case encontrado?
3. Si hay aprendizaje durable:
   - Escribir en LEARNINGS.md con formato:
     YYYY-MM-DD | categoría | título corto
     - Trigger: qué pasó
     - Root cause: por qué
     - Durable fix: qué archivo/proceso/skill cambió
     - Verification: cómo verificar que se resolvió
4. Si el learning no produce un cambio de archivo/proceso → no es un learning válido
```

---

## 7. PATRONES DE CRON JOBS — Expresiones Comunes

### 7.1 Expresiones que Vas a Usar Realmente

```
# Diarios
30 7 * * *        # 7:30 AM cada día
0 9 * * 1-5       # 9:00 AM días de semana (Lun-Vie)
0 20 * * *        # 8:00 PM cada noche

# Cada N minutos/horas
*/15 * * * *      # Cada 15 minutos
*/30 * * * *      # Cada 30 minutos
0 * * * *         # Cada hora (en punto)

# Semanales
0 9 * * 1         # 9:00 AM cada lunes
0 17 * * 5        # 5:00 PM cada viernes

# Mensuales
0 0 1 * *         # Medianoche, primer día del mes
0 0 L * *         # Medianoche, último día del mes (algunos motores)

# One-shot (timestamps ISO)
2026-05-01T09:00:00  # Una vez, a esta hora exacta
```

### 7.2 Arquitectura de Scheduling en Capas

```
CAPA 1: Jobs pequeños aislados
  - Cada job: 1 tarea específica, 1 output concreto
  - Modelo barato (Haiku/Mini) para checks simples
  - Timeout estricto (5-15 min máximo)

CAPA 2: Wrapper scripts
  - Set de paths, env vars, logging, error handling
  - Lock files para prevenir overlap
  - Ejemplo: /usr/local/bin/agent-run healthcheck

CAPA 3: Logs y alertas
  - Cada run genera entrada de log
  - Alertas solo en fallos o anomalías
  - Métricas de tokens/costo por job

CAPA 4: Outputs acotados
  - Cada run deja algo: log line, archivo, mensaje, digest, métrica
  - NUNCA un run silencioso
```

### 7.3 Ejemplo: Flujo Nocturno Completo

```bash
# 1. Health check cada 15 min
*/15 * * * * /usr/local/bin/agent run healthcheck

# 2. Monitorear ventas cada 30 min
*/30 * * * * /usr/local/bin/agent run sales-monitor

# 3. Consolidar memoria a las 2:30 AM
30 2 * * * /usr/local/bin/agent run memory-consolidation

# 4. Investigación nocturna weekdays a las 3 AM
0 3 * * 1-5 /usr/local/bin/agent run overnight-research

# 5. Generar draft matutino a las 6:30 AM
30 6 * * 1-5 /usr/local/bin/agent run morning-draft

# 6. Briefing matutino a las 7:30 AM
30 7 * * 1-5 /usr/local/bin/agent run morning-brief
```

---

## 8. MEJORES PRÁCTICAS DE PRODUCCIÓN

### 8.1 Timeouts — Lo Aburrido Que Te Salva

CADA job programado necesita timeout. Sin timeout:
- Zombie jobs
- Runs superpuestos
- Gasto runaway
- Recursos bloqueados
- Pileup en colas

**Regla:** Si no puedes explicar por qué un job debería correr más de 15-30 min, divídelo.

### 8.2 Idempotencia

Diseñar asumiendo que retries y duplicados son posibles:
- Postear desde cola → marcar item como usado
- Consolidar memoria → usar inputs basados en fecha
- Check de ventas → trackear último event ID procesado

### 8.3 Prevenir Overlap de Runs

```bash
# Usar lock file
if ! mkdir /tmp/agent-job-lock 2>/dev/null; then
    echo "Job already running, exiting"
    exit 0
fi
trap "rmdir /tmp/agent-job-lock" EXIT

# O usar flock
flock -n /tmp/agent-job.lock /usr/local/bin/agent run job-name
```

### 8.4 Selección de Modelo por Job

3 buckets:
- **Barato (Haiku/Mini):** Health checks, monitoreo, rutinas simples
- **Medio (Sonnet):** Briefings, análisis moderado, toma de notas
- **Caro (Opus/GPT-4o):** Investigación profunda, planificación, razonamiento complejo

### 8.5 Budget Limits

Cada job programado DEBE tener budget limit. Un bug en un job horario puede acumular costos significativos de noche.

### 8.6 Quiet Hours

```markdown
# En configuración del agente
quiet_hours:
  start: "23:00"
  end: "07:00"
  timezone: "America/Mexico_City"
  except: [urgent]  # solo tareas marcadas urgentes pueden romper silencio
```

---

## 9. FRAMEWORKS Y HERRAMIENTAS COMPARADOS

### 9.1 Plataformas de Automatización con IA

| Herramienta | Tipo | Fortaleza | Costo |
|---|---|---|---|
| **n8n** | Visual workflow | 70+ nodos IA nativos, LangChain integrado, self-host gratis | $20/mes cloud, $0 self-host |
| **Zapier** | Integración simple | 8000+ apps, setup en minutos | $99-299/mes |
| **Make** | Visual branching | UI intuitiva, flujo visual | Moderado |
| **AgentC2** | Agent scheduling | Cron + webhooks + conditions nativo | SaaS |
| **Cloudflare Agents** | Serverless | Durable Objects + SQLite, sub-second intervals | Usage-based |
| **Agentspan** | Durable execution | Crash-safe, Netflix Conductor underneath | Open source |

**Cuándo cada uno:**
- n8n: agentes complejos, alto volumen, data sensible, self-hosting
- Zapier: integraciones SaaS simples, equipos no-técnicos
- Make: branching visual complejo sin código
- Cloudflare: escalabilidad serverless, sub-minute precision
- Agentspan: durable execution con crash recovery

### 9.2 Frameworks de Agentes con Scheduling

| Framework | Lenguaje | Scheduling | Memoria | Multi-agent |
|---|---|---|---|---|
| **LangChain Deep Agents** | Python | Planning loops | MongoDB checkpointing | Sub-agent delegation |
| **GuildBotics** | Python | Cron + routines | Person-based configs | Multi-person roles |
| **Graflow** | Python | Autonomy slider | DAG-based | Delegates to ADK/PydanticAI |
| **tetsuobot** | TypeScript | Cron + event triggers | Persistent queue | Planner/router/workers |
| **Autobot** | Crystal | Cron via message bus | Session-based | Via message bus |
| **Hermes/Aether** | Python/MCP | Built-in cronjob tool | File-based (MEMORY.md) | 6 Daimons + workflows |

### 9.3 Patrones de Scheduling Avanzados

**Scheduling Adaptativo:** El agente decide su próximo run time basado en sus hallazgos. Si las noticias están lentas, duerme más. Si hay crisis, se despierta antes.

```python
# Adaptive scheduling
async def adaptive_schedule(task_result):
    if task_result.urgency == "high":
        next_run = now + timedelta(minutes=5)
    elif task_result.urgency == "normal":
        next_run = now + timedelta(hours=1)
    else:
        next_run = now + timedelta(hours=4)
    schedule_next(task_id, next_run)
```

**Heartbeat→Cron Handoff:** Un heartbeat detecta algo que requiere trabajo pesado → crea un one-shot cron job en vez de ejecutar inline (bloquearía la sesión principal).

---

## 10. TEMPLATE: Setup Completo de Agente con Rutinas

### Estructura de Directorios

```
~/agent-project/
├── SOUL.md                  # Identidad del agente (cargado cada run)
├── MEMORY.md                # Conocimiento largo plazo (<100 líneas curadas)
├── LEARNINGS.md             # Loop de auto-mejora
├── GOALS.md                 # Objetivos con niveles de permiso
├── HEARTBEAT.md             # Instrucciones para checks periódicos
├── skills/                  # Skills reutilizables
│   ├── morning-brief.md
│   ├── health-check.md
│   ├── memory-consolidation.md
│   ├── overnight-research.md
│   └── content-publish.md
├── memory/
│   ├── daily-logs/          # YYYY-MM-DD.md
│   ├── context.md           # L2: ¿qué estoy haciendo ahora?
│   ├── observations.md      # Raw observations
│   └── drafts/              # WIP
├── state/
│   ├── current-task.json    # Estado actual de tarea
│   └── task-queue.json      # Cola de tareas pendientes
├── schedules/
│   ├── heartbeat.md         # Config de heartbeat
│   └── cron-jobs.md         # Lista de jobs cron con expresiones
└── logs/
    └── runs/                # Logs de cada ejecución
```

### Configuración de Cron para el Agente

```yaml
# schedules/cron-jobs.yaml
jobs:
  - name: morning-brief
    schedule: "30 7 * * 1-5"
    timezone: "America/Mexico_City"
    skill: morning-brief
    model: sonnet
    timeout: 120
    deliver: telegram
    budget_tokens: 10000
    
  - name: health-check
    schedule: "*/15 * * * *"
    skill: health-check
    model: haiku
    timeout: 60
    deliver: none  # solo si hay alerta
    budget_tokens: 2000
    
  - name: memory-consolidation
    schedule: "30 2 * * *"
    skill: memory-consolidation
    model: sonnet
    timeout: 300
    deliver: none
    budget_tokens: 20000
    
  - name: overnight-research
    schedule: "0 3 * * 1-5"
    skill: overnight-research
    model: opus
    timeout: 600
    deliver: email
    budget_tokens: 50000
    
  - name: weekly-report
    schedule: "0 17 * * 5"
    skill: weekly-report
    model: sonnet
    timeout: 300
    deliver: email
    budget_tokens: 15000

quiet_hours:
  start: "23:00"
  end: "07:00"
  timezone: "America/Mexico_City"
```

### Checklist de Auditoría Rápida

Para CUALQUIER agente programado, verificar:
- [ ] ¿Está separado del heartbeat?
- [ ] ¿Tiene regla de silencio para horas nocturnas?
- [ ] ¿Tiene condición de salida hard?
- [ ] ¿Escribe estado de tarea antes de actuar?
- [ ] ¿Recarga identidad en cada ejecución?
- [ ] ¿Tiene timeout configurado?
- [ ] ¿Tiene budget limit?
- [ ] ¿Es idempotente (correr 2 veces no rompe nada)?
- [ ] ¿Previene overlap de runs?
- [ ] ¿Deja output concreto (log/archivo/mensaje)?

---

## 11. INTEGRACIÓN CON HERMES/AETHER

Hermes ya tiene el tool `cronjob` integrado con:
- `action='create'` — crear jobs con schedule, prompt, skills, modelo
- `action='list'` — listar jobs existentes
- `action='update'` / `'pause'` / `'resume'` — gestionar jobs
- `action='run'` — disparar manualmente
- Soporte para: skills adjuntas, model override, context_from (chaining), script pre-run, workdir, enabled_toolsets, delivery a múltiples canales

**Mapeo directo de la investigación a capacidades de Hermes:**

| Patrón de investigación | Capacidades Hermes |
|---|---|
| Cron Agent Pattern (5 reglas) | cronjob tool + SOUL.md auto-loaded + MEMORY injected |
| Heartbeat | cronjob con schedule "*/15 * * * *" + prompt HEARTBEAT_OK |
| Memory Tiering | memory tool (user/memory stores) + files (MEMORY.md) |
| Skill System | skill_manage + skills_list + skill_view |
| Agent Loop (11 pasos) | Prompts auto-contenidos en cronjob + context_from |
| Model Selection | cronjob model override por job |
| Delivery Control | cronjob deliver parameter (telegram, discord, etc.) |
| Budget/Timeout | cronjob timeout + model selection |
| Quiet Hours | Incluir regla en prompt del job |
| Idempotency | script pre-run + check en prompt |
| Job Chaining | context_from (output de job A → input de job B) |
| State Persistence | write_file en script + memory tool |

---

## 12. RECURSOS CLAVE

1. **The Cron Agent Pattern** — dev.to/askpatrick — Las 5 reglas de oro + Agent Loop
2. **12 Production-Grade Skills** — dev.to/netanelabergel — Skills detallados con configs reales
3. **Building Autonomous AI Agents: Heartbeat, Cron, Memory** — n1n.ai — Arquitectura de 3 capas + 5-tier memory
4. **Complete Guide to AI Agent Cron Jobs** — dev.to/toji_openclaw — Expresiones comunes + arquitectura por capas
5. **Persistent Memory for AI Agents** — kjetilfuras.com — Sistema de archivos markdown sin vectores
6. **Memory Systems: Persistent State** — agents-squads.com — Memoria en git, 3 tipos (state/learnings/feedback)
7. **Agentic Operating System in Claude Code** — mindstudio.ai — Skills + auto-mejora + scheduling
8. **n8n AI Agent Workflows** — jahanzaib.ai — Comparativa n8n/Zapier/Make + 70+ nodos IA
9. **GuildBotics** — github.com/GuildBotics — Multi-agent con cron + routines en YAML
10. **Cloudflare Agents Scheduling** — developers.cloudflare.com — Durable Objects + SQLite scheduling
