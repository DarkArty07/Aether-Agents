# Aether Agents — Mexican Spanish clarity candidate

This copy supersedes `COPY_REFINEMENT.md` for the current owner review. The owner
authorized a broader clarity pass and asked for Spanish that reads naturally in Mexico.
The wording remains sober and technical, but avoids translated corporate phrasing,
unnecessary jargon and regionalisms that would distract from the product. The English
landing remains a neutral adaptation.

### 00. Origen

```text
ORIGEN

AETHER AGENTS

Del éter al software.

Aether Agents es un sistema multiagente para desarrollar software: convierte lo que quieres lograr en especificaciones, código, pruebas, revisión e integración.

[ CÓMO FUNCIONA ↓ ]    [ GITHUB ↗ ]

BETA · CÓDIGO ABIERTO · SPEC-DRIVEN

BASADO EN / HERMES AGENT ↗ · GITHUB SPEC KIT ↗
CONOCIMIENTO OPCIONAL / GRAPHIFY ↗
```

### 01. Desarrollo

```text
DESARROLLO

Nuevos proyectos.
Nuevas capacidades.
Software que evoluciona.

Puedes arrancar un proyecto desde cero o trabajar sobre uno que ya existe.

Tú defines qué quieres crear, agregar, corregir o mejorar. Aether organiza el trabajo y coordina a los agentes hasta llegar a una entrega verificable.

El resultado no se queda en una respuesta.

Recibes cambios en el código, pruebas y una revisión del trabajo antes de integrarlo dentro del alcance que definiste.

CREAR
Empieza un proyecto desde cero.

AMPLIAR
Agrega capacidades a un proyecto existente.

MEJORAR
Corrige errores, refactoriza y mejora lo que ya funciona.

PROYECTOS NUEVOS · SOFTWARE EXISTENTE
```

```text
AUTONOMÍA / LARGO HORIZONTE

Trabajo autónomo de largo horizonte.

Está diseñado para mantener sesiones largas de trabajo sin que tengas que supervisar cada paso.

Los agentes comparten el mismo objetivo, avanzan por etapas, revisan lo que construyen y corrigen lo necesario antes de entregar.
```

### 02. Equipo

```text
EQUIPO

Diseñar, construir y revisar
no son la misma responsabilidad.

Un objetivo, tres responsabilidades distintas.
Morfeo define qué se busca; el Supervisor organiza y revisa; los implementadores construyen y prueban.

MORFEO / DISEÑO

Trabaja contigo para convertir lo que necesitas en un diseño claro, especificaciones y un contrato que el resto del equipo pueda ejecutar.

SUPERVISOR / COORDINACIÓN

Divide el objetivo en tareas, coordina el trabajo y revisa los resultados. Si algo no cumple, lo devuelve para corregirlo antes de integrar.

IMPLEMENTADORES / EJECUCIÓN

Construyen y prueban cambios concretos. Pueden trabajar en paralelo cuando las tareas no dependen unas de otras.

TÚ DECIDES QUÉ PRODUCTO QUIERES CONSTRUIR.
AETHER ORGANIZA Y EJECUTA EL TRABAJO.
```

### 03. Proceso

```text
PROCESO

Una intención clara.
Una entrega verificable.

Antes de escribir código, Aether define qué se va a hacer, qué queda fuera y cómo se sabrá si el resultado cumple con lo que pediste.

INTENCIÓN
Qué necesitas lograr.

CONTRATO
Alcance, restricciones y criterios para aceptar el resultado.

DESCOMPOSICIÓN
El Supervisor convierte el objetivo en tareas y ordena sus dependencias.

EJECUCIÓN
Los implementadores construyen y prueban cada tarea en espacios Git separados.

REVISIÓN
El Supervisor revisa cada resultado; si algo no cumple, regresa a corrección.

INTEGRACIÓN
Los cambios aprobados se reúnen y se prueba que funcionen juntos.

CONTRATO · EJECUCIÓN · REVISIÓN · INTEGRACIÓN
```

```text
No todo cambio necesita pasar por el flujo completo.
Si el cambio es pequeño, claro y fácil de revertir, Morfeo puede resolverlo directamente.
```

### 04. Conocimiento

```text
CONOCIMIENTO

Contexto compartido.
Experiencia por rol.

Para trabajar bien sobre un proyecto, los agentes necesitan entender cómo está conectado. Con Graphify, Aether puede construir un mapa técnico compartido para ubicar código, dependencias, pruebas, documentación y otras relaciones sin redescubrir todo en cada tarea.

CONOCIMIENTO DEL PROYECTO

Cuando Graphify está activo, Morfeo, Supervisor e implementadores consultan y actualizan el mismo mapa técnico del proyecto.

EXPERIENCIA POR ROL

Cada rol conserva por separado las lecciones que obtiene del trabajo. Esas notas no se mezclan entre roles ni proyectos.

MEMORIA DE MORFEO

Tus preferencias se quedan con Morfeo y fuera del mapa técnico. Tampoco se mezclan con las notas de los demás roles.

Graphify es una integración opcional.
El mapa ayuda a encontrar contexto y relaciones. La fuente de verdad sigue siendo el código, las especificaciones y las pruebas.

MAPA COMPARTIDO · EXPERIENCIA POR ROL · GRAPHIFY OPCIONAL
```

### 05. Control

```text
CONTROL

Delegar el trabajo
no significa perder la visibilidad.

Delegar trabajo sólo funciona si puedes ver qué ocurrió y recuperar el control cuando algo sale mal. Por eso Aether delimita el alcance, aísla cambios, verifica resultados y conserva evidencia del proceso.

ALCANCE

El objetivo deja claro qué debe cambiar, qué queda fuera y qué condiciones debe cumplir la entrega.

AISLAMIENTO

Cada tarea trabaja en un espacio Git separado para que el trabajo en paralelo no interfiera.

VERIFICACIÓN

Las pruebas y la revisión independiente comprueban los cambios antes de cerrar el trabajo.

OBSERVACIÓN

Queda evidencia del avance, los bloqueos, las revisiones y el resultado de cada trabajo.

RECUPERACIÓN

Si algo falla, Aether prioriza volver a un estado conocido y corregir de forma acotada en lugar de seguir acumulando cambios sobre algo incierto.

CONTRATOS · GIT · PRUEBAS · REVISIÓN · RECUPERACIÓN
```

```text
Autonomía no es perder el control.
Es delegar con límites, evidencia y una ruta clara para corregir o recuperar.
```

### 06. Fundamentos

```text
FUNDAMENTOS

Un sistema abierto.
Tus modelos. Tu proyecto.

Aether se construye sobre herramientas abiertas y no te obliga a usar un solo proveedor de modelos. Tú eliges qué modelos compatibles usar en cada rol.

HERMES AGENT

Es la base que ejecuta a los agentes y les da perfiles, herramientas, coordinación, worktrees y sesiones.

GITHUB SPEC KIT

Aporta el método para convertir una idea en especificaciones, planes, tareas y criterios de aceptación.

GRAPHIFY

Añade, de forma opcional, el mapa técnico compartido. Aether separa ese conocimiento de lo que aprende cada rol.

MODELOS Y PROVEEDORES

Tú eliges qué modelos compatibles usar por rol. Puedes repetir uno, mezclar modelos o cambiar de proveedor según lo que necesites.

CÓDIGO ABIERTO · MIT · TÚ ELIGES EL PROVEEDOR
```

```text
Aether Router es un proyecto aparte para acceder a modelos y dirigir solicitudes. Puede complementar Aether Agents, pero no es requisito para usarlo.
```

### 07. Autoría

```text
AUTORÍA

Christopher Hernández Jiménez

@DarkArty07

Creador de Aether Agents.

Aether Agents es un proyecto de código abierto publicado bajo licencia MIT.
Puedes revisar el código, entender su arquitectura, modificarlo y contribuir al proyecto.

[ VER EN GITHUB ↗ ]
[ DOCUMENTACIÓN → ]

CÓDIGO ABIERTO · MIT
```
