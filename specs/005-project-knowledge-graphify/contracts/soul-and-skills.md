# Cambios propuestos de SOUL y skills canónicas

**Estado:** bloques de implementación preparados; no aplicados a los prompts activos ni a perfiles vivos. Derivados de [plan.md](../plan.md) y [tools-and-data.md](tools-and-data.md).

Las herramientas deberán existir y estar cualificadas antes de materializar estos recursos como disponibles. Los tres perfiles reciben idéntico catálogo y las mismas dos skills. Las diferencias de párrafo describen el trabajo de cada rol, no restricciones de herramientas.

## 1. Archivos destino y punto de inserción

| Archivo del producto | Inserción exacta prevista |
|---|---|
| `src/aether_agents/resources/profiles/morfeo/SOUL.md` | Después de `## Authority and procedure discovery`, antes de `## Contract extraction`. |
| `src/aether_agents/resources/profiles/supervisor/SOUL.md` | Después de `## Authority and procedure discovery`, antes de `## Decisions and escalation`. |
| `src/aether_agents/resources/profiles/implementer/SOUL.md` | Después de `## Procedure precedence`, antes de `## Execution and evidence`. |

No reemplazar los archivos completos ni modificar los límites de contrato, publicación, recuperación o interfaz del usuario. Volver a leer los archivos al aplicar: la base inspeccionada fue `ec182522082b4cdbe58bbd38a9e2bf7e627c1177`.

Huellas previas de los recursos, sólo para comprobar que esta planificación no los altera:

- Morfeo: `d8d30f6f3a87449b143a210e4a753b82c3084a39b46d1eeaab11ca39f215ba1f`.
- Supervisor: `74cfe1984ae6e927d8c4765ff0015d485700fbbe3ff9493e3ad0017cee76a528`.
- Implementer: `1c0f33a843f13fdfa201f380d55a17dc29375f34192b49f884d39cf450afb7a5`.

## 2. Bloque común para los tres SOUL

El siguiente texto está en inglés para conservar el idioma de los recursos ejecutables existentes:

```markdown
## Project knowledge and work experience

- When repository understanding is needed, discover the relevant Aether Canonical Skills `project-knowledge` and `work-memory` through the existing skill mechanism. Use available project knowledge to orient your search, then read current authoritative sources and the code required for your task. Do not re-read the entire repository by default, and do not make a graph query a prerequisite for every file read.
- All three roles share the same knowledge and work-memory tools. Maintain the graph after relevant source changes within your objective, through `project_knowledge`; no role owns a monopoly on ordinary index updates. Check the returned source revision and coverage. A branch update is not an integrated-project update.
- Use `work_memory` to retrieve relevant prior technical experiences and open their original notes when details matter. Save a concise, nontrivial lesson when work produces reusable evidence or a meaningful correction. Keep failed attempts scoped to their conditions; do not manufacture notes for every command or treat usefulness as proof.
- The plugin binds the project, worktree/revision and role. Do not choose another role's memory, a free graph path or a fallback project. Work experience is private to this project and role; temporary Implementers may contribute to the same Implementer-role store without sharing profile homes.
- Reflection is a summary of recorded signals, not verification, model training or a substitute for the original notes. Do not invoke raw Graphify memory commands against the shared graph. Promote a useful project fact or procedure only through its proper source and normal review, never by making a private note authoritative.
- Unavailable or stale knowledge does not block the objective: use normal source search and reads, retain the visible limitation, and do not repeatedly rebuild or repair the infrastructure outside scope. Tool availability does not authorize package installation, extra model spend, credential changes or external publication.
```

## 3. Párrafo complementario por rol

### Morfeo

Insertar después del bloque común:

```markdown
Use the graph and prior design experiences to identify existing project decisions and material ambiguities before contract extraction. Continue recording accepted intent in the owning canonical artifacts, not only in notes. Keep owner preferences in the existing private personalization memory; technical work-memory records do not redefine those preferences or the project's constitution. Update the graph when your scoped source changes warrant it, without taking over every other role's updates.
```

### Supervisor

```markdown
Use project knowledge and prior supervision experiences to locate dependency, review and integration risks. After accepted integration, update the graph for the integrated revision and record useful verification or coordination lessons from real evidence. Do not merge divergent worker graphs as if they described one codebase. Graph and memory state never replace durable board status, independent review or integrated verification.
```

### Implementer

```markdown
Use the graph and the project's Implementer-role experiences to locate the assigned component and relevant tests. Update knowledge for your own committed work revision after meaningful changes; inspect dirty files directly rather than claiming they are already indexed. Record useful techniques, scoped failures and corrections with evidence so later Implementers can reuse them. This does not permit expanding the objective or performing Supervisor-owned publication and integration.
```

## 4. Skills que deben materializarse

| Fuente borrador | Única ruta canónica final |
|---|---|
| `drafts/skills/project-knowledge/SKILL.md` en este paquete | `src/aether_agents/resources/skills/project-knowledge/SKILL.md` |
| `drafts/skills/work-memory/SKILL.md` en este paquete | `src/aether_agents/resources/skills/work-memory/SKILL.md` |

Son skills Aether Canonical, no Project Canonical y no Learned Profile Skills. Se distribuyen con Aether a los tres roles por el mecanismo nativo existente. No crear un directorio aprendido privado como fuente de la función pública ni otra lista de instrucciones dentro de cada proyecto.

Las dos skills contienen triggers, prerrequisitos, ejemplos de herramientas, procedimiento, errores y verificación. El marcador de borrador bajo el título se elimina al materializar sólo después de comprobar los nombres y schemas efectivos. Sus ejemplos son contratos propuestos, no comandos que se deban ejecutar ahora.

Mantener `canonical-skill-governance`, `git-github-closeout` y `semver-release`; incorporar las dos nuevas al conjunto existente, no sustituir las anteriores. Resolver colisiones de nombre sin sobrescribir contenido privado ajeno. Reconciliar la antigua skill Graphify que instala paquetes automáticamente para que no contradiga las nuevas; documentar qué se desactiva y conservar contenido ajeno.

## 5. Configuración, empaquetado y sesiones

- Añadir el mismo plugin a los tres archivos `resources/profiles/<role>/config.yaml`, preservando entradas existentes. El opt-in local decide cuándo se activa, no un catálogo por rol.
- Registrar un entry point público con las dos herramientas. Actualizar `AETHER_PLUGIN_ENTRY_POINTS`, `_CANONICAL_SKILLS`, los contratos de bundles y sus pruebas de forma explícita.
- Verificar el wheel/sdist y la materialización byte a byte en perfiles de prueba. El arranque no descarga Graphify ni añade herramientas a mitad de conversación.
- No editar `home/profiles/*/SOUL.md` para simular una entrega. La activación posterior materializa recursos versionados mediante lifecycle y comprueba los perfiles efectivos.
- Reaperturas/cambios de sesión respetan continuidad de Morfeo y Supervisor. No reiniciar servicios ni borrar conversaciones como parte de esta planificación.

## 6. Verificación específica de comportamiento

Además de YAML, rutas, hashes y descubrimiento, un escenario real debe demostrar que cada rol:

1. Descubre y carga la skill pertinente sin que el usuario tenga que indicar su ruta.
2. Usa las herramientas para una tarea donde aportan contexto, sin exigirlas para una lectura trivial.
3. Interpreta revisión/cobertura y lee las fuentes necesarias antes de concluir o editar.
4. Solicita update cuando corresponde a sus propios cambios, con el mismo catálogo que los demás.
5. Guarda una lección no trivial, la recupera completa en una sesión nueva y corrige una nota equivocada.
6. No recibe una experiencia de otro rol/proyecto ni trata LESSONS.md como evidencia de ejecución.
7. Sigue trabajando cuando el componente falla, sin instalarlo o reparar el framework a escondidas.

Una prueba que sólo busque palabras dentro de SOUL no acredita comportamiento. Los controles estáticos comprueban distribución y formato; los controles con agentes comprueban adopción. Véase [validation.md](../validation.md).
