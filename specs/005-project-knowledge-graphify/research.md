# Investigación y decisiones: Graphify para Aether

**Fecha:** 2026-09-05. Complemento de [plan.md](plan.md), no autoridad de comportamiento del producto.
**Aether inspeccionado:** `ec182522082b4cdbe58bbd38a9e2bf7e627c1177`.
**Componente auditado:** `graphifyy` 0.9.54, `937e59a5476fcb2665d6c4f4b7c0d0a4142011b6`.

## 1. Evidencia experimental existente

La auditoría del 2026-09-05, anterior a esta revisión documental, ejecutó cinco módulos upstream y 13 pruebas específicas. Resultado conservado: 415 passed, 0 skipped, una advertencia; 402 casos upstream y 13 propios. No fue la suite completa. Algunos casos propios pasan al reproducir un defecto; no equivalen a garantías de seguridad.

Entorno: Python 3.11.15, MCP 1.29.0 y Linux; checkout fijado sin modificaciones upstream, entorno desechable con dependencias y tests. No agentes Aether reales ni extracción semántica con LLM. El informe y el código de reproducción se conservaron en `audit/AUDIT.md`, `audit/test_aether_graphify_findings.py` y `audit/final-results.xml` dentro del checkout externo. La ruta local de la investigación no se incorpora al producto.

Para preservar esta evidencia antes de eliminar el checkout, P0 debe revisar y copiar sólo el informe saneado y las pruebas propias/recibos necesarios a una ubicación versionada de 005; no copiar el entorno ni Graphify. El hash del archivo propio auditado es `90f44690041dfc982fe8cd5541a2dc929606b784eb47fd1d0fc16bb144e47264`.

## 2. Hallazgos y adaptación mínima

| ID | Evidencia del candidato | Adaptación elegida |
|---|---|---|
| H1 | MCP real completó initialize/list/call/close y diez consultas A/B correctas con configuración normal. El caso sin grafo devolvió error textual con isError=false. | No diagnosticar el fallo histórico por conjetura. Validar resultado funcional, no sólo transporte. |
| H2 | tools/list incluyó siete consultas y tres herramientas de PR; no update, save-result o reflect. | Plugin de Aether con catálogo común y ejecutor local. No conectar sólo MCP y llamarlo integración completa. |
| H3 | Guardado en carpetas distintas separó roles/proyectos; 30 guardados concurrentes conservaron 30 archivos. Contributor nativo es graphify. | Vincular proyecto/rol/autor y publicación desde Aether; la prueba de colisiones no demuestra crash-safety. |
| H4 | CLI reflect sin --graph autodetectó graph.json y dos roles reemplazaron el mismo sidecar. | Prohibir esa ruta por defecto en el adaptador, no prohibir reflexionar a un rol. |
| H5 | Función reflect con graph_path=None y CLI en contexto neutro produjeron informes separados. | Elegir explícitamente la función en un ejecutor aislado. Probarla de nuevo contra el wheel. |
| H6 | La respuesta técnica completa quedó en la nota, pero no en LESSONS.md. | Incluir búsqueda y lectura de originales; reflect es resumen de señales, no síntesis semántica. |
| H7 | Tres actualizaciones normales y un renombrado funcionaron; un intercalado controlado reprodujo dos escritores con inodos de lock diferentes. | Bloqueo externo estable para operaciones gestionadas; no eliminar el archivo al desbloquear. Publicación coherente. |
| H8 | GRAPHIFY_OUT absoluto apuntando a A hizo que una llamada para B respondiera desde A. | Saneamiento de entorno y destino inequívoco por snapshot; sin fallback multiproyecto. |

Los resultados no demuestran la frecuencia espontánea de la carrera, fuga previa en Aether, ahorro de tokens, corrección de notas redactadas por modelos, compatibilidad MCP 2.x o todo el soporte de plataformas. El candidato es evidencia de componentes, no una release Aether cualificada.

## 3. Archivos que sustentan las conclusiones

Todos los enlaces siguientes fijan el commit auditado, no una rama móvil:

- [graphify/serve.py](https://github.com/Graphify-Labs/graphify/blob/937e59a5476fcb2665d6c4f4b7c0d0a4142011b6/graphify/serve.py), 1617–1624: rutas; 1650–1803: herramientas; 2110–2176: resultados/registro.
- [graphify/cli.py](https://github.com/Graphify-Labs/graphify/blob/937e59a5476fcb2665d6c4f4b7c0d0a4142011b6/graphify/cli.py), 1493–1543: autodetección del grafo en reflect.
- [graphify/reflect.py](https://github.com/Graphify-Labs/graphify/blob/937e59a5476fcb2665d6c4f4b7c0d0a4142011b6/graphify/reflect.py), 104–160/364–523: agregación; 564–610 y 824–836: informe y sidecar.
- [graphify/ingest.py](https://github.com/Graphify-Labs/graphify/blob/937e59a5476fcb2665d6c4f4b7c0d0a4142011b6/graphify/ingest.py), 275–346: notas y contributor.
- [graphify/watch.py](https://github.com/Graphify-Labs/graphify/blob/937e59a5476fcb2665d6c4f4b7c0d0a4142011b6/graphify/watch.py), 161–218: lifecycle del lock.
- [pyproject.toml](https://github.com/Graphify-Labs/graphify/blob/937e59a5476fcb2665d6c4f4b7c0d0a4142011b6/pyproject.toml): dependencias, extras, distribución y avisos.

Huellas calculadas en la auditoría: `reflect.py` → `53d877f8009344cfc721d400444bbf2c7f7fcdcd3c4f97580a369c4f79b06db0`; `watch.py` → `16cdc86443004e5308def63ab53172e7639e3e71cdf679af96b18f733752e4ed`; `serve.py` → `3eaea8304a02177aeded910c295292cd5e00f51cc50ba37a0463c2cb1a4ae51a`.

## 4. Integraciones existentes que se reutilizan

En Aether: registro y resolver de `src/aether_agents/observation/context.py`, inicialización y marcador de proyecto, primitivas de `paths.py`, entrada de plugins y skills de `lifecycle.py`, laboratorio bajo `lab/`, registro de capacidades y generador de documentación. No se presupone que el contexto del plugin ya entregue todos los bindings: P1 lo cualifica.

Se leyeron los tres SOUL y la skill `canonical-skill-governance`. La nueva capacidad no sustituye sus responsabilidades. Las skills son procedimientos y no redefinen autoridad. La lista exacta de entry points y `_CANONICAL_SKILLS` aparece en lifecycle y tests; se cambia explícitamente cuando se materializan los recursos nuevos.

[Plugins oficiales de Hermes](https://hermes-agent.nousresearch.com/docs/developer-guide/plugins/) describen extensión pública por herramientas/skills. Ese manual no prueba compatibilidad del runtime seleccionado de Aether: se verifica con su artefacto exacto, sin actualizar Hermes como efecto colateral.

Se revisó la [plantilla de plan de Spec Kit](https://github.com/github/spec-kit/blob/4a7341a93d944d6efe153b71da4a1adb9c2b578c/templates/plan-template.md), 1–49 y 95–103: separación de contexto, investigación, interfaces y posterior tasks. No se ejecutó Spec Kit ni se inventó una nueva metodología; este plan redistribuye procedimientos entre roles.

## 5. Historial resumido de decisiones sustituidas

La revisión anterior del plan, hash `f1a006a9b8948e66ff1f8e5aad5e4a554eea99b35c7c85c9333109d343fe8924`, contenía decisiones de la investigación previa a ejecución. Esta revisión las reconcilia:

- «Sólo lectura/Morfeo primero» se sustituye por mismo catálogo y mantenimiento por los tres; piloto gradual es una táctica de pruebas, no un límite permanente.
- Identidades permanentes de implementadores efímeros se sustituyen por memoria del rol por proyecto y atribución de cada contribución.
- La frase «Graphify no se instaló ni ejecutó» sólo describe aquella investigación previa. La auditoría posterior sí ejecutó el componente; esta sesión documental no repitió las 415 pruebas.
- Suposición de reflexión independiente al omitir --graph: refutada por H4 y sustituida por la ruta explícita H5.
- Comparación de rutas únicamente estática: ampliada por H8 a reproducción MCP.
- Confianza genérica en el lock upstream: refutada por H7; se añade coordinación estable externa.
- Experiencias pospuestas o limitadas a reflect: ahora son parte de la entrega con guardar/buscar/leer/corregir/reflejar.

No se traslada investigación histórica a un supuesto ACTIVE ni se reescriben resultados para simular que la integración ya existe.
