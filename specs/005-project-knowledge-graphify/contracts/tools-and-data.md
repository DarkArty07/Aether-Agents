# Contrato de herramientas y datos

**Estado:** contrato del candidato estructural implementado. Las interfaces están registradas en el paquete y verificadas de forma determinista, pero permanecen deshabilitadas en las plantillas portables y su calificación con agentes vivos sigue pendiente. Derivado de [plan.md](../plan.md) y trazado por [implementation.md](../implementation.md). Los ejemplos de las skills coinciden con los schemas registrados.

## 1. Contexto común

Plugin: `aether-project-knowledge`. Dos herramientas: `project_knowledge` y `work_memory`. Mismas operaciones en Morfeo, Supervisor e Implementer. No asignar catálogos distintos según rol.

El runtime/adaptador aporta un contexto validado: proyecto portable, vista actual, revisión resuelta, rol, sesión y tarea/ejecución cuando existen. Una acción directa puede no tener tarjeta; no crear una para consultar o guardar una nota. El contexto se resuelve por llamada o se vincula a la sesión de forma verificable; nunca mediante un singleton mutable «último proyecto».

Los argumentos del modelo no contienen `role`, `agent_id`, `project_path`, `graph_path`, `memory_dir`, ejecutable, variables de entorno ni URL. Las referencias a archivos son relativas al proyecto y se comprueba su pertenencia. Un campo manipulado no sustituye los bindings de la tarea.

## 2. project_knowledge

| action | Argumentos del modelo | Resultado esperado |
|---|---|---|
| `status` | Ninguno. | Snapshot disponible, revisión, cobertura y cambios no indexados. |
| `query` | `question`; `budget_tokens` opcional. | Contexto de nodos/relaciones y referencias; consulta técnica no personalizada. |
| `explain` | `node`; `budget_tokens` opcional. | Detalle del elemento y fuentes. |
| `neighbors` | `node`; `relation` y `budget_tokens` opcionales. | Vecinos pertinentes del mismo grafo. |
| `community` | `community_id`; `budget_tokens` opcional. | Contexto del grupo de esa instantánea; el ID no es portable entre reconstrucciones. |
| `path` | `source`, `target`; `max_hops` opcional. | Relación/conexión entre elementos; dirección y límites explícitos. |
| `impact` | `node`; `depth` y `budget_tokens` opcionales. | Dependencias inversas detectadas; no prueba exhaustiva de efectos en ejecución. |
| `update` | `reason`; `changed_paths` y `mode` opcionales. | Recibo de revisión/alcance realmente actualizado, reutilizado o pendiente. |

`mode`: `configured` por defecto o `structural`. `configured` usa sólo el alcance y presupuesto ya habilitados. No ofrece un flag para saltar autorización de envío o ampliar corpus. `changed_paths` es una sugerencia para eficiencia, nunca una fuente confiable de «todo lo cambiado»: el adaptador obtiene y valida las diferencias del snapshot para no omitir borrados o dependencias.

Consulta usa CLI pública o un ejecutor que invoca operaciones existentes. La representación texto de Graphify puede conservarse como `content`; no inventar un JSON nativo de `query`. Vecinos/comunidades/impacto requieren prueba de equivalencia del adaptador con el candidato instalado. Si alguno falla su cualificación, se reporta como limitación, no como una implementación falsa.

No duplicar consultas internas: `query` entrega también el estado mínimo del snapshot, por lo que no obliga a ejecutar `status` antes de cada pregunta. No imponer una llamada por tarea si no necesita conocimiento del repositorio.

### Sobre de respuesta propuesto

```json
{
  "schema_version": "aether.project-knowledge.v1",
  "ok": true,
  "action": "query",
  "project_id": "<verified-project-uuid>",
  "view_id": "<opaque-local-view>",
  "snapshot_id": "<snapshot-id>",
  "source_revision": "<git-commit>",
  "freshness": "current",
  "coverage": {"code": "indexed", "documents": "partial"},
  "dirty_paths": [],
  "content": "<bounded-native-result>",
  "references": [],
  "truncated": false,
  "warnings": []
}
```

Valores de frescura: `current`, `stale`, `dirty_not_indexed`, `unknown`. Son evidencia de una vista/cobertura, no garantía de verdad global. La respuesta sin snapshot o contexto puede usar `null` en los campos no resueltos; jamás inventar un UUID, commit o referencia.

`update` devuelve además `outcome=updated|unchanged|deferred`, `indexed_revision`, `uncovered_paths` y `semantic_pending`. `deferred` identifica una operación que no se completó; no implica que exista un proceso o trabajo asíncrono. El adaptador no promete ejecución posterior si no la ha registrado realmente mediante un mecanismo autorizado existente.

Errores tipados: `PROJECT_UNRESOLVED`, `PROJECT_CONFLICT`, `VIEW_MISMATCH`, `COMPONENT_UNAVAILABLE`, `INDEX_MISSING`, `INDEX_CORRUPT`, `BUSY`, `TIMEOUT`, `SCOPE_UNAVAILABLE`, `SEMANTIC_NOT_ENABLED`, `REVISION_CONFLICT` e `IDEMPOTENCY_CONFLICT`. `ok=false` puede incluir una sugerencia de lectura directa; no entrega resultados de otro proyecto. Distinguir un timeout sin escritura de una publicación completada cuyo recibo no llegó; recuperar por clave de operación antes de repetir.

Los tokens solicitados están limitados por configuración; adjuntar tamaño/medición o estimación, nunca afirmar tokenización exacta basada sólo en caracteres. Saneamiento del contenido es defensa adicional, no convierte documentación recuperada en instrucciones de sistema.

## 3. work_memory

Namespace automáticamente ligado a proyecto y rol. Todas las instancias temporales del rol Implementer comparten ese namespace de experiencias, no un home de Hermes. Cada nota conserva actor/tarea/ejecución individual cuando hay contexto fiable.

| action | Argumentos del modelo | Resultado esperado |
|---|---|---|
| `save` | `idempotency_key`, `situation`, `lesson`, `applicability`, `outcome`, `evidence`; `source_nodes` opcional. | ID estable y recibo de nota completa, con revisión, procedencia del runtime y estado de replay. |
| `search` | `query`; `limit` y `budget_tokens` opcionales. | Coincidencias por texto/símbolos, extracto, vigencia y note_id; no lee otro namespace. |
| `read` | `note_id`; `cursor` opcional. | Nota original con contenido completo o continuación explícita. |
| `correct` | `note_id`, `expected_revision`, `reason`, `replacement`, `evidence`. | Nueva revisión atribuible que sustituye la anterior en recuperación normal. |
| `reflect` | Ninguno. | Informe privado acotado y referencia al documento; generación de notas que cubre. |

`outcome` conserva la semántica nativa `useful|dead_end|corrected`. La verificación es otro campo: Aether distingue declaración del agente, fuente observada y evidencia comprobada; no confiar en un booleano suministrado por el LLM. `evidence` puede estar vacío si no existe, y la nota se marca no verificada. Cada referencia puede indicar ruta, revisión, locator y resultado observado; una prueba histórica no se marca vigente en HEAD nuevo sin revalidar.

`idempotency_key` es obligatorio, opaco y acotado. El agente o cliente genera una clave nueva por cada nota intencional y conserva exactamente la misma clave al reintentar esa operación. Aether persiste sólo su digest. Clave y payload originales devuelven la nota existente con `idempotent_replay=true`, incluso después de reiniciar el store; la misma clave con contenido o revisión fuente diferentes devuelve `IDEMPOTENCY_CONFLICT`. Dos contribuciones independientes, aunque tengan texto idéntico, usan claves distintas y se conservan por separado.

`replacement` contiene la nueva lección y condiciones, no un parche libre al filesystem. Corregir no borra la historia ni multiplica señales de corroboración: search y reflect consumen una sola versión efectiva de cada nota. Correcciones concurrentes sobre versiones incompatibles devuelven conflicto explícito y conservan ambos antecedentes; no gana silenciosamente el último escritor.

### Formato lógico de nota

- Identidad: schema, note_id, revision, project_id, role_id, tarea/ejecución/sesión confiables cuando existen y timestamps.
- Contenido: situación, respuesta/lección, condiciones, outcome, corrección y fuentes.
- Vigencia: revisión de origen, huellas pertinentes, estado de verificación y supersedes.
- Publicación: una unidad finalizada legible, no texto a medio escribir.

Graphify conserva un Markdown legible como salida de save-result. Metadatos de Aether pueden residir en un envelope asociado; el formato físico se fija en la implementación con prueba de publicación consistente. Usar funciones existentes en un staging privado y recibo final común. No copiar secretos de la sesión o el perfil a los campos de procedencia.

## 4. Búsqueda y reflexión privada

Primera búsqueda: texto y símbolos sobre notas del namespace, ordenación explicable por coincidencia/vigencia; usar búsqueda existente cuando sea suficiente. Sin vector DB nueva, ninguna llamada LLM automática ni un backend de memoria adicional. `reflect` no sustituye `search/read` ni prueba utilidad de una solución.

Reflexión mediante función Python `reflect(..., graph_path=None)` en proceso del componente. El adaptador controla import, entradas y destino. Capturar una generación estable de notas vigentes; el layout que Graphify lee puede materializarse temporalmente como Markdown plano, sin mezclar registros sustituidos o incompletos. Publicar lecciones por generación y permitir recuperar las originales fuera de ese resumen. No copiar ni escribir `.graphify_learning.json` junto al grafo compartido.

No exponer rutas arbitrarias de escritura ni un API genérico `exec` al agente. El import de Graphify se hace en el componente aislado, no en el proceso de Hermes. Una eventual incompatibilidad se detecta en bootstrap/tests y se devuelve sin desactivar las herramientas normales.

## 5. Estado interno y configuración

El manifiesto de snapshot registra proyecto, vista, commit, scope hash, digest de entradas, versión/lock del motor, schema, alcance AST/semántico y condición de finalización. Rutas internas permanecen privadas. Una función de status nunca autoriza otra vista por nombre de rama.

El registro de proyectos existente es la fuente de identidad; el manifiesto sólo identifica conocimiento derivado. No crear un segundo registro de proyectos o un almacén de autoridad.

Defaults propuestos: opt-in, generación estructural local, corpus acotado, semántica no habilitada hasta configurar envío y presupuesto, límites de bytes/tokens/tiempo/concurrencia en configuración. Una vez habilitado el objetivo y presupuesto, no pedir confirmación por cada `update`, nota o reflexión normal.

El propietario dispone de inspección, exportación y borrado mediante una superficie administrativa explícita. Borrar nota elimina versiones activas y sus proyecciones/índices, señala límites de backup y no deja un informe vigente citando contenido eliminado. No inventar una prohibición para corregir notas del mismo rol sólo porque cambió la instancia temporal del implementador.

## 6. Ejemplos de aceptación

Una consulta de la misma palabra en A y B devuelve sus revisiones y fuentes diferentes. Dos roles guardan lecciones distintas sobre esa palabra, y search/read/reflect recuperan sólo el namespace del llamador. Tres updates de la misma revisión deduplican, mientras updates de ramas diferentes producen snapshots diferentes. Las consultas o notas de una sesión cambiada de proyecto no reutilizan bindings o cachés previos. Véase [validation.md](../validation.md).
