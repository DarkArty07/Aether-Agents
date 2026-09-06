# Plan de implementación: Graphify y experiencias de trabajo en Aether

**Fecha:** 2026-09-05. **Revisión del plan:** 2, posterior a la auditoría experimental.
**Base Aether inspeccionada:** `ec182522082b4cdbe58bbd38a9e2bf7e627c1177`.
**Graphify probado:** Python `graphifyy==0.9.54`, commit `937e59a5476fcb2665d6c4f4b7c0d0a4142011b6`.
**Status of this artifact:** historical planning baseline. The owner subsequently authorized implementation on a separate branch and integration of the reconciled candidate into `main`. The local structural implementation, current limits and executed checks are recorded in [implementation.md](implementation.md), [spec.md](spec.md) and the [capability registry](../../docs/capabilities.toml). Planning text below is not a claim that every proposed capability is implemented; live activation and semantic qualification remain separate.

## 1. Objetivo y alcance acordado

Reducir la exploración repetida de repositorios entre sesiones, conservar conocimiento técnico actualizado y reutilizar experiencias sin mezclar proyectos, revisiones o roles.

La solución tiene dos capas: un grafo técnico del proyecto mantenido por los tres roles y experiencias separadas por proyecto y rol. Morfeo, Supervisor e Implementer reciben exactamente las mismas herramientas. Los implementadores temporales contribuyen a la memoria del rol Implementer, conservando atribución de tarea y ejecución; no se inventa una identidad permanente para cada proceso.

El propietario pidió el plan y la preparación de cambios de SOUL y skills. Este paquete no instala el componente, modifica perfiles vivos, ejecuta modelos, crea tarjetas, publica cambios ni declara resuelta la congelación PD-74. El alcance funcional queda plasmado aquí; antes de implementar debe incorporarse a los propietarios normativos y al Objective Contract correspondiente. No se usará una regla documental como excusa para omitir esta planificación ni se impondrán autorizaciones nuevas para cada actualización ordinaria.

### Entregable final de la implementación

Un plugin de Aether, distribuido con el producto y basado en interfaces públicas de Hermes, que expone `project_knowledge` y `work_memory` a los tres roles; administra un componente Graphify aislado; mantiene índices coherentes; conserva y recupera experiencias; y llega acompañado de SOUL, dos skills canónicas, documentación y pruebas reales. No basta con que el plugin figure como instalado.

### Dentro y fuera

| Dentro de la entrega | Fuera de esta entrega |
|---|---|
| Consulta y actualización colaborativa, fuentes y revisiones identificadas. | Hindsight, grafo global y fusión automática entre proyectos. |
| Código y documentación seleccionada; semántica con backend y presupuesto habilitados. | Ingesta indiscriminada de chats, medios, credenciales o runtimes. |
| Guardar, buscar, leer, corregir y reflejar experiencias de cada rol. | Entrenamiento de pesos, evaluación autónoma de verdad o promoción automática a reglas. |
| Mismo catálogo, identidad automática, instalación reproducible y rollback. | Fork de Graphify, parches del núcleo de Hermes o nuevo scheduler. |
| Ajustes versionados de los tres SOUL y dos skills Aether Canonical compartidas. | Dashboard, servidor HTTP permanente, grafos de worktrees sin commit. |

## 2. Documentos de este paquete

- [Research](research.md): evidencia, límites y correcciones a la propuesta anterior.
- [Contratos de herramientas y datos](contracts/tools-and-data.md): operaciones y campos concretos.
- [Contrato de SOUL y distribución de skills](contracts/soul-and-skills.md): recursos aplicados, rutas canónicas y límites de activación.
- [Skill canónica de conocimiento del proyecto](../../src/aether_agents/resources/skills/project-knowledge/SKILL.md).
- [Skill canónica de experiencias](../../src/aether_agents/resources/skills/work-memory/SKILL.md).
- [Validación y aceptación](validation.md): pruebas funcionales, de comportamiento, packaging y coste.

Los archivos bajo `drafts/` quedaron reducidos a avisos históricos de reemplazo: no contienen procedimiento ejecutable y no son una segunda fuente. Las únicas skills canónicas están en `src/aether_agents/resources/skills/`. Los cambios de SOUL se aplicaron al recurso fuente correcto, no a copias privadas bajo `home/`.

## 3. Evidencia que manda sobre las suposiciones

La auditoría previa ejecutó 402 pruebas upstream y 13 propias: 415 pasaron, sin omitidas y con una advertencia. Algunas pruebas pasan al reproducir un defecto. No fue la suite completa ni una prueba de agentes Aether reales. Véase [research.md](research.md).

| Hallazgo probado | Decisión de integración |
|---|---|
| El MCP inicia en el entorno probado, pero no expone update/save-result/reflect. | Plugin común con operaciones Graphify existentes por debajo; MCP no es requisito del primer transporte. |
| La CLI reflect autodetecta un grafo aunque se omita `--graph`. | Ejecutor aislado que llama `reflect(..., graph_path=None)` explícitamente. |
| Reflect con grafo sustituye un sidecar compartido. | Sin `.graphify_learning.json` personal junto al grafo común. |
| Reflect agrega metadatos, no resume las respuestas técnicas completas. | Incluir `search` y `read` de notas originales desde la primera entrega. |
| Hay una carrera reproducible al eliminar el archivo de lock upstream. | Lock estable externo de Aether para operaciones gestionadas; no eliminarlo en el unlock. |
| Un GRAPHIFY_OUT absoluto común puede dirigir B al grafo de A. | Entorno saneado, destinos calculados por binding y sin fallback global. |
| Las notas se separan por directorios, no por perfiles nativos. | Aether añade proyecto, rol, tarea, procedencia y recuperación. |

No cambiar de versión del candidato sólo por existir una más nueva. La instalación desde wheel, los grandes corpus, la extracción semántica y la matriz exacta Hermes siguen pendientes.

## 4. Arquitectura elegida

```text
Morfeo / Supervisor / Implementer(s)
        mismas herramientas y mismas dos skills
                       |
          aether-project-knowledge (plugin)
                       |
        contexto verificado + adaptación pequeña
              /
     project_knowledge                work_memory
              |                         |
     Graphify aislado             registros por rol/proyecto
     CLI / ejecutor              save-result + búsqueda/lectura
              |                  reflect(graph_path=None)
     snapshots por proyecto             |
     y revisión                  notas y lecciones privadas
```

### Reutilización y responsabilidad

Graphify conserva parsers, grafo, caché y operaciones de consulta/actualización. Aether conserva sus Projects, registro de UUID, contextos, skills, lifecycle, tablero y primitivas de archivos privados. No crear otro registro de proyectos ni otra cola.

El plugin puede agrupar comandos en un ejecutor Python mínimo dentro del entorno del componente cuando la CLI no ofrece una salida o un modo seguro. Ese ejecutor adapta entradas/salidas y llama funciones existentes; no copia los algoritmos. Sus imports internos se fijan al candidato y se prueban contra el wheel instalado.

La primera ruta es CLI/ejecutor local, sin negociación MCP durante el arranque de los roles. Consultas avanzadas —vecinos, comunidades e impacto— se exponen por la misma interfaz cuando su adaptador esté verificado; son parte de la entrega prevista, no permisos exclusivos de un rol. MCP persistente sólo se considerará si la carga repetida del grafo demuestra un coste material, conservando idéntico contrato y aislamiento.

Un fallo funcional se normaliza a un error de la herramienta aunque el transporte devuelva éxito. No parsear frases humanas como única prueba de éxito. Cuando una operación no ofrece un resultado comprobable, usar una llamada al ejecutor con resultado tipado o declararla no disponible; nunca inventar un resultado estructurado.

## 5. Identidad, acceso y separación

### Grafo

Clave: proyecto portable + vista de checkout/worktree verificada + snapshot de fuentes + configuración/versión del indexador. Un nombre, una URL o una rama no sustituyen esa clave. El plugin recibe contexto confiable del runtime, no un `role` o una ruta inventada por el LLM.

Reutilizar `ProjectRegistry` y validar sus llamadores: que un UUID exista no autoriza una afirmación arbitraria de sesión. Vincular también la vista y revisión a la tarea/lanzamiento. Si falta contexto, ofrecer un diagnóstico acotado y lectura directa; no consultar el último grafo, el default o el primero disponible.

Dos clones con un marcador copiado requieren la resolución de identidad existente. Monorepos conservan una identidad con filtros internos; submódulos, repositorios anidados y comparaciones multiproyecto no se incorporan automáticamente. Comparaciones explícitas mantienen resultados etiquetados y separados.

### Experiencias

Clave: instancia local de Aether + `project_id` + `role_id`. `role_id` proviene del perfil verificado: `morfeo`, `supervisor` o `implementer`. Cambiar el modelo no cambia la memoria. Tarea, ejecución y revisión identifican cada aportación; no se mezclan preferencias del propietario en las notas compartidas del rol Implementer.

Mismo catálogo no significa mismo contenido. Ninguna llamada del agente selecciona otra carpeta, otro rol o un `memory_dir`. Inspección/exportación/borrado por el propietario tiene una superficie de operador explícita y no amplía las herramientas comunes para leer memorias ajenas.

Esto es aislamiento de datos en las rutas gestionadas, no una sandbox contra procesos hostiles ejecutados bajo el mismo usuario. Tampoco borra contexto de un proyecto anterior ya presente en el LLM: cambios de proyecto deben quedar vinculados y delimitados en la conversación; nunca exportar accidentalmente ese contexto a una nota de otro proyecto.

## 6. Actualización colaborativa y revisiones

Cualquiera de los tres roles puede ejecutar `project_knowledge(action="update")` tras sus cambios pertinentes. No requiere una autorización rutinaria adicional de Morfeo o del propietario. Consulta no dispara indexación; update es una operación explícita con los límites previamente configurados.

1. Resolver proyecto, vista y revisión autorizada. En la primera entrega, fuentes comprometidas en Git.
2. Seleccionar el corpus permitido y comprobar cobertura existente. Reusar una instantánea equivalente.
3. Adquirir un lock estable de Aether por vista de publicación; revalidar después de adquirirlo y deduplicar una solicitud ya atendida.
4. Ejecutar extracción sobre un snapshot de fuentes fijo, aprovechando caché compatible. No permitir otro escritor gestionado sobre esos mismos archivos de trabajo.
5. Comprobar resultado, huellas, exclusiones y referencias; publicar un manifiesto completo y cambiar el puntero coherentemente. Los lectores nunca consumen un candidato parcial.
6. Si la vista cambió durante la operación, conservar el resultado bajo su revisión original y no marcar la revisión nueva como actualizada. No permitir que un escritor atrasado haga retroceder el puntero.

Mantener el nombre del archivo de lock, incluso tras liberar `flock`; no heredar la carrera upstream. No adoptar hooks/watchers automáticos al margen de esa coordinación. Guardar los snapshots desde el principio en su ruta estable y publicarlos mediante manifiesto/puntero, evitando romper referencias internas al renombrar carpetas.

El grafo de una rama de Implementer no reemplaza el del resultado integrado. Tras un commit propio puede actualizar su revisión y seguir trabajando; Supervisor actualiza después la vista integrada. No usar unión ciega de nodos entre ramas. No crear commits ceremoniales sólo para indexar: cambios no comprometidos se declaran `dirty_not_indexed` y se leen directamente.

Las relaciones semánticas o de llamadas estáticas pueden ser incompletas. Ausencia de una arista no demuestra ausencia de dependencia. Ediciones de interfaces, configuración, documentos o dependencias pueden invalidar conclusiones relacionadas aunque un archivo concreto no cambie.

### Fuentes, semántica y privacidad

Incluir código, pruebas y documentación canónica seleccionada; excluir homes, sesiones, secretos, logs, dependencias instaladas, salidas generadas y notas privadas. Los archivos versionados no son seguros por definición. Capturar objetos Git permitidos sin ejecutar código, hooks o filtros del repositorio. Registrar exclusiones y lenguajes sin soporte como cobertura ausente.

La ruta estructural debe demostrar cero llamadas a modelos. `--no-cluster` no significa «sin LLM». La documentación semántica usa únicamente el backend y presupuesto configurados, sin autoelección de credenciales del proceso o archivos del corpus. `update(mode="configured")` opera bajo esa configuración; sin permiso de semántica mantiene cobertura pendiente y no inventa un grafo completo.

## 7. Experiencias: guardar, recuperar, corregir y reflejar

Se reutiliza `save_query_result` para el registro nativo; Aether añade procedencia y estado. La nota conserva situación, resultado técnico, condiciones de aplicación, fuentes y verificación. Guardar lecciones no triviales, no transcripciones completas ni una entrada por comando.

La búsqueda inicial es léxica/símbolos sobre registros de ese namespace, con resultados acotados y lectura de la nota completa. Reusar utilidades de búsqueda existentes donde sean aptas; no introducir otra base vectorial. `search` devuelve coincidencias, no sólo el informe de reflect. Una sesión nueva debe recuperar una solución escrita por una sesión anterior.

`correct` crea una revisión atribuible que sustituye al registro anterior. Un reintento con la misma clave de operación no duplica notas. La consulta normal y el conjunto de entrada de reflect excluyen versiones sustituidas; la historia sigue inspeccionable. Los estados de verificación no se deducen de `outcome`: `useful` no equivale a correcto. Una corrección no permite reescribir evidencia del resultado original.

Notas y metadatos se publican coherentemente mediante una unidad finalizada y primitives privadas existentes. Lectores y reflect ignoran escrituras incompletas. Si el formato necesita varios archivos, un recibo de publicación común evita ver media nota. No asumir que el `write_text` nativo es resistente a crashes.

### Reflexión elegida

Un ejecutor en el entorno aislado llama a `graphify.reflect.reflect` con `graph_path=None` explícito y un conjunto estable de notas vigentes del rol/proyecto. Nunca depende de omitir un flag de CLI. Producción del informe en un destino temporal privado y publicación atómica; por concurrencia, entradas/salidas de reflexión llevan generación. Si llegan notas durante la reflexión, el informe identifica la generación procesada y queda pendiente de refresco, sin perder notas.

No escribe ni lee el sidecar personal del grafo compartido. No añade valoraciones privadas a consultas comunes. Sin grafo se pierde agrupación por comunidades y filtrado nativo de nodos desaparecidos; la recuperación comprueba fuentes/revisión y marca antigüedad. `reflect` no extrae automáticamente procedimientos de las respuestas completas; el agente sigue leyendo las notas.

Una lección generalizable pasa al conocimiento común mediante el documento o skill de proyecto correspondiente, con evidencia y la revisión normal aplicable. No crear un gate humano por cada nota; no autoelevar una experiencia a decisión o skill canónica.

## 8. SOUL y skills son entregables funcionales

Materializar dos Aether Canonical Skills, iguales para los tres perfiles:

- `project-knowledge`: consulta selectiva, fuentes, límites de interpretación, actualizaciones colaborativas, revisión y fallback.
- `work-memory`: selección de experiencias, búsqueda/lectura, notas con evidencia, corrección, reflexión privada y promoción apropiada.

Las skills completas y sus ejemplos están únicamente en `src/aether_agents/resources/skills/`. El contrato aplicado a los tres SOUL está en [contracts/soul-and-skills.md](contracts/soul-and-skills.md); los recursos se integraron junto a las instrucciones existentes sin reescribir identidades ni duplicar manuales.

SOUL establece hábitos: orientar antes de explorar cuando ayuda, actualizar tras cambios pertinentes, recuperar experiencia relevante y registrar aprendizajes reales. Las skills enseñan cómo. No prohibir leer antes de consultar, no exigir notas ceremoniales, no recargar el grafo o toda la memoria en cada turno y no convertir una avería opcional en un bloqueo del objetivo.

Publicar ambas skills sólo junto a herramientas compatibles. Instalarlas con el mecanismo nativo existente; no copiar la skill upstream antigua que instala paquetes y modifica hooks. Reconciliar esa integración antigua sin borrar skills o configuración ajenas. Probar los bytes del wheel, su materialización en perfiles y su descubrimiento real. Los prompts de sesiones activas no se reescriben silenciosamente; validar nuevas sesiones y preservar otras conversaciones.

## 9. Packaging, configuración y retención

Plugin propuesto: `aether-project-knowledge`, entrada `aether_agents.knowledge.hermes_plugin`. Una distribución Aether, componente Graphify independiente; no otro framework de agentes. No importar Graphify al cargar un CLI/perfil que no usa la función. No descargar paquetes durante tool calls o arranque de sesión.

Fijar el candidato y sus transitivas compatibles por plataforma en un lock propio de componente. La auditoría con Python 3.11.15/MCP 1.29.0 no prueba automáticamente el wheel público ni todo Python 3.11–3.13. La vía inicial no necesita extras MCP; si se adopta deben cualificarse por separado. Conservar licencias/avisos del artefacto exacto, sin asumir una licencia histórica.

Layout propuesto, respetando resolutores XDG existentes:

```text
DATA/aether/components/graphify/<lock-id>/          componente inmutable
CACHE/aether/knowledge/<project>/<snapshot>/       índices reconstruibles
STATE/aether/knowledge/<project>/<view>/           punteros, recibos, locks
STATE/aether/work-memory/<project>/<role>/         notas, revisiones, lecciones
```

No versionar grafos, secretos o memorias privadas en Git. No alojar notas persistentes en caché descartable. Recolección de índices preserva snapshots utilizados por tareas/lectores y una base recuperable. Exportar/borrar notas debe eliminar también índices derivados, informes y copias operativas; informar el tratamiento de backups, sin prometer borrado universal fuera de la instalación.

Configuración inicial: opt-in local, corpus permitido, semántica deshabilitada hasta configurar envío/gasto, presupuesto de respuesta y límites de proceso. Propuesta a calibrar: 2,000 tokens de resultado por consulta, límite de bytes y truncamiento explícito. No son cifras de rendimiento demostradas. Desactivación conserva las fuentes y el trabajo; rollback cambia componente y recursos compatibles sin degradar datos en silencio.

## 10. Mapa de cambios del producto

| Propietario/superficie | Cambio implementable |
|---|---|
| `DESIGN.md`, R9 | Añadir índice técnico compartido y experiencias técnicas por rol/proyecto; conservar exclusividad de preferencias personales de Morfeo. Reformular frases amplias que sólo admiten recuerdo del propietario, sin dar autoridad a las notas. |
| Nueva `spec.md` de 005 | Normar los contratos de este plan antes de implementar, sin duplicar otro estado del producto. |
| R4/R5/R6 | Dependencia externa, mismo catálogo, binding y transporte de consultas sin modificar coordinación nativa. |
| R8/R10/R11/R12 | Revisiones, worktrees, privacidad, pruebas, presupuestos; referencias a 005 en vez de repetir todo. |
| A1/R13 | Instalación opcional, locks, rollback, perfiles y release qualification. |
| `INTEGRATIONS.md` | Corregir Python vs port TypeScript y estado efectivo. No marcar ACTIVE sin activación verificada. |
| Los tres `resources/profiles/*/SOUL.md` y `config.yaml` | Aplicar bloque común y cláusula propia; mismo plugin/catálogo y mismas skills. |
| `resources/skills/project-knowledge/SKILL.md`, `work-memory/SKILL.md` | Únicas fuentes canónicas finales de los procedimientos; retirar borradores tras materialización. |
| `lifecycle.py`, `pyproject.toml`, tests de packaging | Actualizar lista exacta de plugins y conjunto `_CANONICAL_SKILLS`; no relajar integridad por incorporar recursos nuevos. |
| `docs/authority.md`, roles y product-boundary | Diferenciar índice, experiencias y fuentes de verdad; privacidad por rol. |
| Guías `project-knowledge.md` y `work-memory.md`, CLI/plugins/limitaciones | Documentar sólo operaciones implementadas y su recuperación. |
| `docs/capabilities.toml` | Estados admitidos y evidencia real; no inventar `planned`. Regenerar referencia con el script existente. |
| README/índice/ROADMAP/CHANGELOG | Navegación, secuencia y cambios verificados, sin anunciar ahorro o aprendizaje garantizados. |
| `lab/`, tests, CI | Escenarios de colaboración, recuperación entre sesiones, aislamiento y uso de skills. |

No crear un nuevo documento de autoridad que compita con esta jerarquía. Reutilizar módulos de identidad y archivos privados; extraer una primitiva común sólo si lo necesita el consumidor, sin refactorizar todo el observador.

## 11. Secuencia de implementación con entregables y aceptación

| Fase | Trabajo y salida | Depende de |
|---|---|---|
| P0 — evidencia y alineación | Preservar auditoría y convertir defectos reproducidos en requisitos. Integrar alcance en propietarios normativos, resolver PD-74 para implementación y formalizar Objective Contract. | Este paquete. |
| P1 — componente y contexto | Wheel/lock aislado, ejecución sin credenciales heredadas, bindings de proyecto/vista/rol y errores tipados. Prueba de fallo sin afectar Hermes. | P0. |
| P2 — grafo colaborativo | Consultas completas previstas, actualización idempotente, lock estable, snapshots y revisión exacta. Dos proyectos/tres roles sin mezcla. | P1. |
| P3 — experiencias recuperables | Save/search/read/correct/reflect; publicación y generación; memoria de rol Implementer con atribución; acceso del propietario. | P1; referencias compatibles con P2. |
| P4 — comportamiento y materialización | Aplicar los tres SOUL, dos skills canónicas y configs; packaging, descubrimiento e instrucciones alineados con schemas reales. | P2/P3 para activación; preparar textos en paralelo. |
| P5 — E2E y coste | Flujo real de tres roles, sesión posterior, cambios de repo y fallos. Comparador de búsqueda/lectura dirigida, no lectura total artificial. | P4. |
| P6 — documentación y entrega | Registry/guías/changelog, pruebas de desactivación/rollback, cierre normal. Activar instalación real sólo bajo autoridad correspondiente. | P5. |

El piloto puede comenzar por Morfeo para diagnosticar; no elimina P5 con todos los roles ni establece catálogos diferentes. No se crea `tasks.md` ni se asignan tarjetas aquí: Supervisor conserva la descomposición ejecutable del contrato. Un PASS que reproduce un bug sigue siendo evidencia del bug; el adaptador necesita una prueba distinta que muestre la protección.

## 12. Pruebas y definición de terminado

[validation.md](validation.md) define casos concretos y resultados esperados. La entrega exige:

1. Mismo catálogo comprobado en los tres perfiles instalados y contexto correcto sin rutas del modelo.
2. Los tres actualizan sin solicitudes perdidas, publicaciones parciales o retroceso de revisión.
3. Una nota con la solución completa se recupera en una sesión nueva; otros roles/proyectos no la reciben.
4. Reflect nunca cambia el grafo o sidecar común; correcciones y generaciones no pierden notas.
5. SOUL y ambas skills se descubren y usan de verdad, además de pasar validación estática y packaging.
6. Fuentes viejas, documentación contradictoria, timeout y componente ausente producen el fallback correcto.
7. El flujo Aether existente no se degrada con la capacidad deshabilitada; nada se instala a escondidas.
8. Coste y calidad se miden con tareas emparejadas y límites transparentes. No confundir menor lectura con mejor resultado.

Pruebas de fase no amplían los criterios del contrato. No añadir cuotas arbitrarias de notas, consultas o rondas para cerrar; las regresiones corregidas conservan evidencia y pueden repetirse conforme al contrato.

## 13. Riesgos residuales, recursos y decisión de salida

La auditoría no resuelve semántica de documentos, rendimiento en grandes repositorios, selección de vista en el runtime público, ni estabilidad de imports del ejecutor. P1/P5 deben cerrarlos con evidencia. Si el binding exige modificar el núcleo de Hermes, no implementarlo ocultamente: utilizar un binding de sesión/lanzamiento soportado o registrar la incompatibilidad del candidato.

No prometer un porcentaje de ahorro. Medir indexación inicial/mantenimiento, consultas, prompts/skills, notas/reflexión, tokens de entrada/salida/caché, calidad, latencia y recuperación humana. El fallback no requiere mantener una IA secundaria.

La estimación anterior de 1,500–4,000 líneas correspondía a lectura y no es un presupuesto del alcance actual. La implementación se estima por entregables tras P1; no por producir líneas. Mantener la integración acotada y justificar cualquier ampliación a servicios permanentes, bases vectoriales o personalización del grafo.

**Decisión de diseño consolidada:** grafo compartido con mantenimiento colaborativo; experiencias recuperables separadas por rol/proyecto; mismas herramientas y skills; prompts breves; Graphify reutilizado con adaptación explícita a sus límites comprobados.
