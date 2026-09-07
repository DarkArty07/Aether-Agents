# Validación y aceptación de la integración

**Estado:** contrato de aceptación vigente. Los carriles deterministas de componente, plugin, empaquetado y repositorio ya tienen resultados en [implementation.md](implementation.md); deben repetirse sobre la integración final con `main`. Los escenarios E01–E08 y la evaluación comparativa continúan pendientes y no se presentan como resultados actuales. La auditoría previa del componente se documenta por separado en [research.md](research.md).

## 1. Niveles de evidencia

| Nivel | Qué comprueba | Qué no prueba |
|---|---|---|
| Documentación/estático | Contratos, rutas, frontmatter, coherencia y packaging declarado. | Que agentes usen herramientas o que el runtime sea correcto. |
| Componente | Graphify exacto, ejecutor, errores, locking y persistencia. | Integración real de roles, ahorro o fidelidad del modelo. |
| Plugin integrado | Carga y mismas herramientas en perfiles instalados, bindings y aislamiento. | Uso inteligente y aprendizaje efectivo por el LLM. |
| E2E con agentes | Skills, consultas, updates, notas, reanudación y fallback en una tarea real. | Fiabilidad general para todo proyecto/modelo. |
| Evaluación comparativa | Calidad y coste frente al baseline en tareas seleccionadas. | Superioridad estadística universal o cumplimiento automático de PD-74. |

Las pruebas que reproducen errores upstream deben conservar su nombre/propósito. Añadir otras pruebas con el adaptador que demuestren que esos errores ya no afectan la ruta gestionada. No contar los 415 PASS de auditoría como 415 garantías de seguridad ni repetirlos para aparentar integración.

## 2. Aceptación determinista e integración

| ID | Escenario | Resultado esperado |
|---|---|---|
| D01 | Instalación del wheel en entorno limpio con dependencias fijadas. | Imports/ejecutor funcionan sin checkout editable, PATH especial ni credenciales del usuario. |
| D02 | Capacidad deshabilitada. | CLI y perfiles existentes funcionan sin importar parsers, descargar paquetes o iniciar Graphify. |
| D03 | Carga de tres perfiles candidatos. | Idénticos schemas de project_knowledge/work_memory y las mismas dos skills; diferencia sólo en contexto. |
| D04 | Proyecto A y B tienen el mismo nombre y símbolo. | Cada respuesta tiene proyecto/revisión/fuente correctos; canarios del otro nunca aparecen. |
| D05 | UUID conocido pero binding de sesión/tarea falso o contradictorio. | Error explícito sin usar registry como autorización universal ni fallback. |
| D06 | Clon con marcador copiado, rutas renombradas y detached HEAD. | Se aplica política de identidad existente; sólo equivalencia comprobada permite reutilizar snapshots. |
| D07 | GRAPHIFY_OUT absoluto heredado apuntando a A; solicitud de B. | Adaptador sanea entorno y usa B. Una prueba separada conserva reproducción upstream. |
| D08 | Traversal, symlink fuera de raíz, rutas con espacios/Unicode y argumentos que parecen flags. | Lectura/escritura limitada al destino gestionado sin ejecutar shell ni escapar del namespace. |
| D09 | Tres actualizaciones simultáneas de una misma revisión. | Reutilización/deduplicación, cero escrituras perdidas, una publicación coherente y recibos correctos. |
| D10 | Intercalado exacto de la carrera de lock auditada. | El lock externo estable mantiene exclusión; su archivo no se elimina al desbloquear. |
| D11 | Escritor antiguo termina después de otra revisión. | Su snapshot permanece histórico; no hace retroceder el puntero activo. |
| D12 | Ramas divergentes y worktrees de implementadores. | Snapshots distintos; no unión de fuentes incompatibles ni cambio silencioso a última main. |
| D13 | Cambios sucios/nuevos sin commit; archivo borrado/renombrado. | Dirty queda no cubierto; al indexar commit coherente se actualizan referencias y desapariciones. |
| D14 | Sólo cambia diseño, configuración o interfaz compartida. | Cobertura semántica/vigencia explícita; no dar por actuales conclusiones por hash de un único archivo. |
| D15 | Crash durante construcción, JSON parcial, disco lleno o cancelación. | Snapshot anterior legible; candidato no visible; ningún éxito ficticio y limpieza acotada. |
| D16 | Runtime recibe error como texto con transporte exitoso. | Normalización a error funcional por resultado comprobado; no tratar isError=false como garantía. |
| D17 | Secretos/canarios, homes, logs y notas privadas dentro del árbol. | No llegan a corpus, grafo, salidas o trazas comunes. Structural no realiza peticiones LLM/red. |
| D18 | Misma pregunta, notas distintas por proyecto/rol. | Save/search/read devuelven el namespace correcto con atribución real, no contributor genérico como autor. |
| D19 | Varios implementadores guardan simultáneamente; un cliente reintenta el mismo guardado. | Contribuciones independientes conservadas; retry idempotente no duplica evidencia. |
| D20 | Crash entre nota y metadatos. | Ningún lector o reflect ve una nota parcial; publicación y recuperación verificadas. |
| D21 | Se corrige una nota; dos correcciones parten de la misma versión. | History atribuible, una versión efectiva o conflicto explícito; no doble corroboración. |
| D22 | Reflect desde contexto donde existe un graph.json común. | Ejecutor fuerza graph_path=None; hashes de grafo y sidecar común no cambian. |
| D23 | Se guarda una solución que no aparece en LESSONS.md. | Search/read recuperan la solución original completa; no se atribuye síntesis semántica a reflect. |
| D24 | Llegan notas mientras se genera reflexión. | Informe identifica generación; nuevas notas no se pierden ni se declara cubierta la generación nueva. |
| D25 | Solicitud de borrar una nota. | No aparece en búsqueda/informes/índices operativos; tratamiento de historia y backups explicado. |
| D26 | Cambio de proyecto en una conversación. | Bindings/cachés/guardados cambian correctamente; no persiste contenido anterior como hecho del proyecto nuevo. |
| D27 | Retención, desactivación y rollback con lectores/tareas activos. | Snapshots en uso conservados, notas no tratadas como caché, fuentes y Hermes intactos. |
| D28 | Matriz Linux/WSL2 y Python soportado. | Evidencia por plataforma del componente exacto; no extrapolar prueba local a toda la matriz. |
| D29 | `query` nativa excede un presupuesto pequeño y Graphify omite nodos; una respuesta completa excede el presupuesto en un control separado. | El primer sobre devuelve `truncated=true`; el segundo conserva `truncated=false` y un aviso de exceso completo. Ningún contenido recomienda `get_node` ni otras operaciones ausentes del schema Aether. En la expansión #330, `context_filter` es una recuperación permitida exclusivamente para `query`. |
| D30 | `query`, `explain`, `neighbors`, `community`, `path` e `impact` devuelven nodos o relaciones con archivos/locators; un caso supera 50 referencias. | `references` contiene procedencia relativa, deduplicada, ordenada y ligada a la revisión para cada elemento fuente visible. El límite de 50 nunca es silencioso: activa `truncated` y un warning. No se filtran rutas privadas del snapshot. |
| D31 | Un agente consulta un símbolo, lo resuelve con `explain` y solicita su comunidad sin inspeccionar `graph.json`; se repite tras reconstruir el snapshot. | `resolved_node` entrega ID exacto, `community_id` y nombre; `community` se autoidentifica con el mismo ID y cardinalidad. Los metadatos quedan ligados al snapshot y no se presentan como portables tras la reconstrucción. |
| D32 | Matriz representativa de todas las acciones y campos de `project_knowledge`/`work_memory`, incluidos campos faltantes, inaplicables y prohibidos, antes y después del saneamiento Hermes. | El schema canónico discriminado y `validate_arguments` coinciden exactamente. `tool_describe` conserva la discriminación; el schema saneado mantiene propiedades/descripciones utilizables por backends estrictos y el handler sigue rechazando combinaciones inválidas. |

Si se introduce MCP persistente, añadir initialize/initialized/tools/list/tools/call/close, ausencia de descargas/modelos al conectar, errores de grafo, stdout sólo protocolo, aislamiento por proceso/contexto y terminación de procesos. No exige HTTP para la primera entrega.

### Expanded scope #330

These scenarios extend D01-D32 and use the oracles and runnable lanes in the
[expanded contract](contracts/expanded-tools-and-semantic.md). They are required evidence,
not assertions of already-executed implementation tests.

| ID | Scenario | Expected evidence |
|---|---|---|
| D33 | Expanded schemas on three roles, old calls and Hermes sanitization | 14/5 actions; exact action-field validity; no injected project/repo/path/provider authority. |
| D34 | Native stats, ranking, query controls, impact filters and direction | Native-equivalent results, references, bounded output and explicit uncertainty. |
| D35 | Real auxiliary extraction in two separate projects | Source-backed document/code relationships, selected existing model/transport, observed usage; no cross-project/private leakage or LLM-as-AST claims. |
| D36 | Same commit enrichment, repeat/update, rename/delete and config change | Correct semantic fingerprint, zero calls for complete unchanged input, scoped cache invalidation and resume. |
| D37 | Timeout, exhaustion, cancellation, malformed/hollow output and concurrency | Old complete artifact preserved; usable structural result; truthful partial/unavailable coverage; no endless retries or automatic fallback. |
| D38 | Real read-only PR plus controlled absent/error/moving/large cases | Correct repo, base/head, files and community coverage; no failure misreported as zero impact; local graph remains usable without GitHub. |
| D39 | Native graph/tree exports and aggregation | Real verified files, project/revision identity, valid data/JS, disclosed external assets; immutable snapshot preserved. |
| D40 | Full integration, fresh-profile load and local activation | Existing gates/coverage; independently reviewed source relationships; main and managed skills current, no secret/config residue in public artifacts. |

## 3. Packaging, SOUL y skills

| ID | Prueba | Resultado esperado |
|---|---|---|
| S01 | Frontmatter de ambas skills. | Nombre único, descripción breve, versión, licencia, autoría, plataformas reales y secciones completas. |
| S02 | Ejemplos contra schemas de herramientas. | Todas las acciones/argumentos se validan contra la implementación registrada; ejemplos ilustrativos no se ejecutan como datos reales. |
| S03 | Wheel/sdist. | Ambas skills y tres SOUL esperados presentes; ausencia de notas, rutas de máquina, credenciales y borradores empaquetados. |
| S04 | Lista exacta de plugins y skills. | Se añaden las entradas al contrato existente sin desactivar tests de integridad o usar comodines. |
| S05 | Materialización nativa en perfiles. | Bytes esperados y descubrimiento en los tres; ninguna instalación global desconocida usada por accidente. |
| S06 | Colisión con skill privada/antigua. | No se sobrescribe contenido ajeno; la integración antigua no reinstala paquetes ni contradice la nueva. |
| S07 | Sesiones activas durante activación. | No se reescribe un system prompt ni un catálogo en caliente a escondidas; nuevas sesiones verificadas. |
| S08 | Registry y docs. | Public surfaces reales trazables; referencia regenerada, estados admitidos y sin afirmaciones prematuras. |

Estas pruebas de distribución complementan, no sustituyen, los comportamientos siguientes.

## 4. E2E de agentes y procedimientos

### E01 — orientación útil sin reexploración global

Preparar un proyecto desechable con dos subsistemas y una decisión documentada. Pedir a Morfeo un cambio focalizado sin decirle que use Graphify. Con sólo los recursos empaquetados debe descubrir/cargar la skill pertinente, consultar conocimiento, reconocer cobertura y leer fuentes relevantes. Debe diferenciar una especificación de comportamiento implementado. El criterio no prohíbe un número fijo de archivos ni obliga a consultar en preguntas triviales.

### E02 — colaboración completa

Ejecutar un objetivo con Morfeo, Supervisor y al menos dos implementadores bajo el flujo nativo. Cada rol realiza un cambio pertinente dentro de su alcance y puede actualizar el grafo sin pedir permiso a otro. Comprobar recibos por revisión, deduplicación cuando procede y resultado integrado. No basta con scripts que etiqueten procesos con nombres de rol: observar llamadas de los agentes reales.

### E03 — sesión posterior recupera una solución

En la primera sesión, un rol resuelve un defecto no obvio y guarda una nota con detalles comprobables. Cerrar la sesión normalmente. En una nueva sesión del mismo rol/proyecto, plantear un problema relacionado sin entregar la solución. Debe buscar, abrir la nota original, verificar aplicabilidad y reutilizar el detalle que no está en LESSONS.md. El criterio requiere evidencia de recuperación y uso, no sólo una llamada a reflect.

Repetir con Morfeo, Supervisor y el rol Implementer. Para este último cambiar de trabajador temporal sin compartir homes y conservar atribución de la nota.

### E04 — igualdad de herramientas y privacidad

Dos roles guardan experiencias contradictorias sobre una misma palabra; el proyecto B usa los mismos símbolos. Consultar y reflejar por cada contexto. Cero filtraciones de canarios del rol/proyecto ajeno; el grafo común no cambia por reflexionar. El propietario conserva la vía administrativa de inspección, distinta de herramientas ordinarias de agentes.

### E05 — fuente cambió y nota debe corregirse

Modificar interfaz/configuración y generar una revisión nueva. El agente debe detectar que la lección antigua ya no aplica, leer fuentes actuales, corregir la nota y recuperar la versión efectiva en la siguiente sesión. El índice no debe persuadirlo de mantener un comportamiento obsoleto.

### E06 — componente caído y tarea trivial

Simular ausencia del componente, timeout e índice corrupto. El agente continúa con herramientas normales y declara límites, sin instalar Graphify, crear otro sistema de memoria o reparar Hermes fuera del objetivo. Una tarea que no requiere conocimiento de repositorio no debe producir consultas/notes ceremoniales.

### E07 — semántica de documentación y presupuesto

Con credenciales/gasto autorizados para un corpus desechable, procesar documentación canónica y medir llamadas/uso. Probar ausencia de credenciales, presupuesto agotado y documento con instrucciones maliciosas: coverage pendiente o datos no confiables, no ampliación de permisos ni envío a backend no configurado. La parte estructural sigue disponible.

### E08 — promoción pertinente

Un agente verifica un requisito de pruebas que beneficia al proyecto. Lo registra en la fuente/procedimiento correspondiente dentro del alcance y actualiza el grafo; no copia su historial personal ni convierte la nota en autoridad. Independent review y competencias de publicación permanecen como antes.

La prueba registra los perfiles, herramientas y skills efectivamente cargados, no sólo el contenido de la rama fuente. Logs de prueba saneados; ningún transcript privado completo en artefactos públicos.

## 5. Evaluación de ahorro y calidad

Comparador: mismo modelo/configuración con búsquedas y lectura dirigida, sin Graphify. Tratamiento: herramientas y skills del candidato. Corpus y tareas emparejados; separar contextos para evitar que la respuesta de una ejecución contamine otra. Alternar orden cuando sea posible y fijar criterios de corrección antes de ejecutar.

Matriz inicial propuesta: 20 tareas en al menos dos proyectos que cubran localización, arquitectura, decisiones, integración, depuración y fuentes obsoletas. Es una evaluación acotada del componente, no una nueva cardinalidad de PD-74 ni evidencia de superioridad universal.

Medir:

- Corrección, precisión de referencias y necesidad de intervención humana.
- Bytes/archivos leídos y llamadas a herramientas, sin usarlos como único objetivo.
- Tokens reales de entrada/salida/caché cuando el proveedor los reporte; estimaciones etiquetadas cuando no.
- Indexación inicial y actualizaciones semánticas/estructurales, notas/reflexión y coste de cargar skills.
- Latencia fría/caliente, memoria del proceso, disco, tiempo de recuperación y degradaciones.

Reportar coste inicial, coste por sesión recurrente y coste de mantenimiento por separado. El punto de equilibrio se calcula con datos observados; no prometer ahorro porcentual por instalar un grafo. Un fallo de calidad no se justifica por consumir menos tokens.

## 6. Orden de ejecución y cierre

Primero D01–D28 y S01–S08 en entornos desechables; después E01–E08 con autorización de modelos/gasto y el laboratorio existente. Un piloto sólo de Morfeo es diagnóstico, no aceptación final del alcance de tres roles.

Pruebas del repositorio se ejecutan mediante el wrapper de `CONTRIBUTING.md`/`scripts/run_tests.py` vigente; no inventar flags, rutas de evidencia pública ni comandos que aún no existen. Añadir escenarios al laboratorio actual sin crear un segundo runtime de pruebas.

Cierre: fuente, wheel, recursos materializados, documentación y registry concuerdan; no claims de función implementada basados sólo en prompts. Emitir resultados, fallos previos conservados, límites de cobertura y rollback. La activación real, publicación y release se realizan sólo por su vía autorizada. No fabricar aprobaciones adicionales para notas/updates locales dentro de un objetivo y configuración ya permitidos.

## 7. Verificación y registro de resultados

La entrega documental inicial sólo comprobó consistencia, enlaces, frontmatter y ejemplos. La implementación posterior añadió pruebas ejecutables y sus resultados se conservan en [implementation.md](implementation.md), separados de la auditoría histórica de 415 pruebas. Cada rebase o integración con `main` invalida cualquier afirmación de que el candidato final está verde hasta repetir los carriles afectados y registrar comandos y resultados nuevos. Las pruebas deterministas no sustituyen E01–E08 ni acreditan ahorro de tokens, conducta autónoma o la puerta PD-74.
