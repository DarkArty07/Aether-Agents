# Project Audit Prompt Template

When asking an orchestrator (Hermes, Raven, or any reasoning agent) to audit a multi-agent project's architecture, use this prompt structure. It produces structured, actionable findings — not vague prose.

## Template

```
OBJETIVO: Auditar el estado actual de [PROJECT] en 3 dimensiones: arquitectura, decisiones de diseño, y optimizaciones.

ALCANCE: Todo el proyecto en [PATH] — [list key directories].

DIMENSIONES A REVISAR:

1. ARQUITECTURA — ¿La jerarquía [describe hierarchy] tiene cuellos de botella? ¿Hay separación de responsabilidades clara? ¿El flujo async está bien cableado? ¿[Key integration] fue la decisión correcta?

2. DECISIONES DE DISEÑO — ¿El modelo de costos se cumple en la práctica? ¿El auditor tiene veto real o es decorativo? ¿Los workers están bien especializados o se traslapan? ¿[Key feature] es suficiente?

3. OPTIMIZACIONES — ¿Qué se puede mejorar en latencia, uso de tokens, rate limiting, caching, manejo de errores, reintentos? ¿[Dashboard/API] consume bien? ¿Hay código muerto o redundante?

OUTPUT:
- Tabla de hallazgos ordenados por severidad (CRÍTICO / ALTO / MEDIO / BAJO)
- Cada hallazgo con: qué está mal, impacto, recomendación específica
- No implementar nada — solo diagnosticar
- Al final, top 3 mejoras que harías primero si tuvieras presupuesto limitado

RESTRICCIONES: No delegues a Daimons para esto — usa [graphify/knowledge graph] y [read_file_simple] tú mismo. Quiero tu análisis directo, no un resumen de otro agente.
```

## Why this works

- **3 dimensions defined** — not "review everything" which produces vague results
- **Concrete scope** — which directories to look at
- **Specific output format** — severity table, not free-form prose
- **No implementation** — diagnostic only, prevents scope creep
- **Forces direct analysis** — no delegation, uses knowledge graph + direct file reads
- **Ends with prioritization** — top 3 for budget-limited scenarios

## Key elements to customize

1. `[PROJECT]` — project name
2. `[PATH]` — absolute path to project root
3. `[describe hierarchy]` — e.g., "Raven → Necromancer → Shades → Revenant"
4. `[Key integration]` — e.g., "Graphify como MCP vs nativo"
5. `[Key feature]` — e.g., "el state_tracker es suficiente visibilidad"
6. `[Dashboard/API]` — e.g., "el dashboard consume bien la API"
7. `[graphify/knowledge graph]` — the read-only exploration tool available
8. `[read_file_simple]` — the direct file read tool available

## Observed results

Used on Requiem Agents v0.3.0 (2026-06-24). Produced 14 findings (2 CRÍTICO, 4 ALTO, 5 MEDIO, 3 BAJO) including:
- Dead code from MCP migration (CRÍTICO)
- Graphify graph contaminated by external code (ALTO)
- Rate limiter counter never resets (ALTO)
- API client without retries (ALTO)
- Auditor auto-pass string matching unreliable (ALTO)

All findings were specific, actionable, and included impact assessment. The top-3 prioritization enabled immediate decision-making.

**Fix-phase discovery:** The audit was performed BEFORE fixes. During the fix phase, the ROOT CAUSE of the entire regression was discovered: the `plugins:` section was missing from config.yaml (the plugin existed on disk but was never loaded). This finding was NOT in the original audit because the audit assumed the plugin was loaded. Lesson: when auditing a system with a regression, FIRST verify that all plugins/MCP servers are actually loaded and enabled before analyzing code-level issues. A code audit of a system where the tools aren't loaded is misleading — you're auditing dead code paths.

Additional fix-phase findings: stale skill file describing non-existent tools (523 lines → 93), Revenant auto-pass upgraded from string matching to exit_code, connection pooling for eval.py, adaptive dashboard polling.
