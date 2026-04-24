# Workflow Engine Experiment — 2026-04-26

## Resumen

Se implementó y debugueó el motor de workflows de Olympus usando LangGraph.
Resultado: **funciona**. Los 3 workflows (dev_and_audit, research_and_implement, full_pipeline)
se ejecutan correctamente, los Daimons se comunican vía ACP y los ciclos de revisión operan.

## Bugs encontrados y corregidos

| # | Archivo | Bug | Fix | Commit |
|---|--------|-----|-----|--------|
| 1 | `src/olympus/workflows/nodes.py:18` | `acp.send_message()` no existe en `ACPManager` | Cambiado a `acp.send_prompt(session.session_id, prompt)` | 51f10aa |
| 2 | `src/olympus/workflows/nodes.py:14-20` | `open_session()` retorna `SessionState`, no string. Se pasaba como id | Usar objeto directamente + `session.session_id` para send_prompt | 51f10aa |
| 3 | `pyproject.toml` | `langgraph` no estaba en dependencies (import error) | Agregada `langgraph>=0.2.0` | 51f10aa |

## Arquitectura del Workflow Engine

```
Olympus MCP Server (server.py)
  └── _handle_run_workflow()
        └── WorkflowRunner (runner.py)
              └── LangGraph StateGraph (definitions.py)
                    ├── Nodes (nodes.py) — cada uno invoca un Daimon vía ACP
                    ├── State (state.py) — WorkflowState TypedDict
                    └── Conditional edges — should_retry_implementation()
```

### Flujo interno

```
_run_acp_session(acp, agent_name, prompt):
  1. session = await acp.open_session(agent_name)   # spawn si no existe
  2. await acp.send_prompt(session.session_id, prompt)  # fire-and-forget
  3. await session.completion_event.wait()             # bloquea hasta done
  4. return session.final_response
```

### Workflows disponibles

| Workflow | Nodos | Flujo | Loop? |
|----------|-------|-------|-------|
| `dev_and_audit` | design → implement → audit → finalize | Daedalus→Hefesto→Athena | Sí (audit→implement si falla) |
| `research_and_implement` | research → design → implement → finalize | Etalides→Daedalus→Hefesto | No |
| `full_pipeline` | research → design → implement → audit → finalize | Etalides→Daedalus→Hefesto→Athena | Sí (audit→implement si falla) |

## Prueba exitosa

```
run_workflow(workflow="dev_and_audit", prompt="Crea hello.py...", max_review_cycles=1)
→ Status: Approved, Review Cycles: 0
→ Daedalus diseñó → Hefesto implementó → Athena auditó y aprobó
```

## Mejoras pendientes (TODO)

### Alta prioridad
- [ ] **Timeout handling**: El MCP client timeout corta workflows largos. Necesitamos un
  mecanismo async donde run_workflow retorne inmediatamente un workflow_id y Hermes
  pueda hacer poll del estado. Actualmente si el workflow tarda >300s, se pierde.
- [ ] **Error recovery**: Si un Daimon falla (crash, timeout), `_run_acp_session` retorna
  un string de error pero el workflow sigue corriendo. Agregar manejo de errores por nodo.
- [ ] **Session cleanup**: `_run_acp_session` abre sesiones pero nunca las cierra. Los
  Daimons quedan con sesiones abiertas acumuladas. Agregar `close_session` al final.

### Media prioridad
- [ ] **Nuevos workflows**: bug_fix, code_review, iterate_design, refactor, doc_and_test, explore_and_spec
- [ ] **Workflow configurables**: Permitir al usuario elegir qué nodos participan en lugar de workflows hardcoded
- [ ] **Progress reporting**: Los nodos deberían reportar progreso intermedio (no solo resultado final)
- [ ] **State richer**: WorkflowState debería trackear más metadata (timestamps, intent, agent IDs)

### Baja prioridad
- [ ] **Parallel nodes**: LangGraph soporta ejecución paralela. Investigar para nodos independientes
- [ ] **Human-in-the-loop**: Integrar `clarify` de Hermes como nodo intermedio para aprobación
- [ ] **Persistent state**: Guardar estado del workflow en `.eter/` para reanudar después de crash
- [ ] **Streaming responses**: Enviar respuestas parciales de Daimons al caller en tiempo real

## Dependencias

- `langgraph>=0.2.0` — motor de grafos con estado
- `agent-client-protocol>=0.1.0` — comunicación ACP con Daimons
- `mcp>=1.0.0` — servidor MCP