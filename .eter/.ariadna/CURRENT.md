# CURRENT.md — Aether Agents

---
fecha: 2026-04-26
fase: Estandarización — Formalización de convenciones
status: in-progress
---

## Estado actual

**Convenciones formalizadas.** Pipeline de 5 fases, taxonomía de artifactos, matriz de decisión talk_to vs run_workflow, .eter/ convention, SOUL.md estandarizado (7 secciones), skills curadas por especialidad, Olympus README ampliado.

## Completado hoy

| # | Tarea | Estado |
|---|-------|--------|
| F1 | Team playbook integrado en orchestration SKILL.md | ✅ |
| F2 | Olympus README ampliado (API ref, HITL guide, Daimon mapping, pitfalls) | ✅ |
| F3 | 6 SOUL.md estandarizados (7 secciones, Execution Context DRY) | ✅ |
| F4 | Skills curadas por especialidad (73→2-4 categorías por Daimon) | ✅ |
| F5 | DESIGN.md v2 + CURRENT.md actualizados | ✅ |

## Skills post-curación

| Daimon | Skills |
|--------|--------|
| Ariadna | aether-agents, productivity, note-taking |
| Athena | aether-agents, red-teaming |
| Daedalus | aether-agents, creative, software-development |
| Etalides | aether-agents, research |
| Hefesto | aether-agents, software-development, github, mlops |
| Hermes | Todas (orquestador) |

## Historial de fases

- **Phase 1:** Olympus MCP server + ACP client (commits 51f10aa → ...)
- **Phase 2:** LangGraph workflow engine — 6 workflows con HITL (commits df4f038 → 957d993)
- **Phase 2.5:** Audit + bug fixes + live testing (commit a868c78)
- **Phase 3:** SOUL.md + Skills adaptation for workflows (commit f14c3d8)
- **Phase 4 (actual):** Formalización de convenciones operativas

## Próximos pasos

1. Verificar que las skills symlink funcionan con `hermes -p <name> skills list`
2. Commit atómico con todos los cambios
3. Test E2E: workflow feature con los nuevos SOUL.md y skills curadas
