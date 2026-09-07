# Aether Agents — Estrategia de contenido de la portada

> Historial del contenido y diseño aprobados para el primer prototipo. La primera
> revisión del propietario solicita retirar numeración visible y mejorar el español.
> El texto de esa nueva versión está en [COPY_REFINEMENT.md](COPY_REFINEMENT.md);
> los ajustes visuales, en [POLISH_PLAN.md](POLISH_PLAN.md). Los bloques anteriores
> se conservan aquí como historial, no como un impedimento para esa revisión autorizada.

**Estado:** secciones 00–07 aprobadas y autorizadas para implementación local.
Las decisiones específicas de cada sección sustituyen las propuestas históricas.
La integración en main y la publicación requieren revisión posterior del propietario.
**Fecha:** 2026-09-06.
**Idioma de trabajo:** español. La adaptación al inglés será posterior.

## 1. Alcance y fuentes

Esta propuesta desarrolla las decisiones de [arquitectura de contenido](CONTENT_ARCHITECTURE.md)
y respeta el [sistema de identidad visual](VISUAL_IDENTITY.md). No cambia la identidad
aprobada, las capacidades de Aether, su método, su estado de publicación ni sus tecnologías.

La aprobación se registra en `CONTENT_ARCHITECTURE.md`. Este documento conserva el
análisis histórico y los textos aprobados. Los ejemplos de catálogo y las demostraciones
no seleccionadas no forman parte de la implementación. El plan de ejecución local vive
en `IMPLEMENTATION_PLAN.md`.

La base del producto inspeccionada es la revisión
`0913ec636ab081654065be90b021cf1c47a41619`. Se consultaron los documentos de trabajo
del sitio y las siguientes fuentes del repositorio:

| Pregunta | Fuente de producto |
| --- | --- |
| Propósito, nuevos proyectos y proyectos existentes | [DESIGN.md](../DESIGN.md), sección 2 |
| Roles, trabajo directo y ejecución delegada | [DESIGN.md](../DESIGN.md), secciones 3–5 |
| Modelos y proveedores | [DESIGN.md](../DESIGN.md), sección 7 |
| Qué aporta Aether frente a Hermes | [Límite del producto](../docs/product-boundary.md) |
| Estado de implementación | [Registro de capacidades](../docs/capabilities.toml) |
| Uso actual del conocimiento | [Guía de conocimiento](../docs/guides/project-knowledge.md) |
| Primeros pasos reales | [Guía inicial](../docs/getting-started.md) |
| Estado beta y publicación | [README](../README.md) y [ROADMAP](../ROADMAP.md) |
| Demostración pública y privacidad | [Contrato A1](../specs/001-aether-v1-productization/spec.md), A1-FR-067–078 |

Esta revisión es editorial y documental. No se ejecutó una nueva calificación del
producto ni se seleccionó o verificó una demostración pública para el sitio.
El registro de capacidades conserva la autoridad sobre el estado actual; una frase
antigua en una guía no debe imponerse sobre él.

## 2. Objetivo editorial

La portada debe permitir que alguien ajeno al proyecto entienda qué desarrolla Aether,
qué responsabilidad delega, cómo se organiza el trabajo y qué puede explorar hoy.
No debe convertirse en un inventario de herramientas ni en una documentación resumida.

Hipótesis de audiencia inicial, pendiente de validar: desarrolladores y responsables
técnicos que quieren delegar trabajo de software, seguidos de posibles colaboradores
del proyecto abierto. Esto orienta la redacción; no restringe los usuarios, dominios o
tecnologías del producto. No hay investigación de mercado que valide esta hipótesis.

La acción principal propuesta es consultar la documentación inicial; la secundaria,
examinar el repositorio. Comprender el sistema dentro de la misma página es una acción
de descubrimiento, no una instalación ni una activación de agentes.

## 3. Diagnóstico de la propuesta anterior

La propuesta inicial contenía los ingredientes técnicos adecuados, pero dedicaba mucho
espacio a las piezas internas antes de mostrar una necesidad concreta y un entregable.

Se propone mantener el problema como una transición breve, no como un manifiesto
independiente. La separación de roles responde a la historia de Aether; no demuestra
que cualquier agente individual sea incapaz o que todo sistema multiagente sea mejor.

Se propone incorporar temprano casos de uso y un ejemplo de resultado; unir contratos,
ejecución, revisión e integración en un único recorrido; y conservar una sección
separada de equipo porque responde quién hace cada cosa, no cuáles son las etapas.

Graphify debe aparecer como conocimiento opcional del proyecto, no como la identidad
completa de Aether. La flexibilidad de modelos merece explicación breve junto a las
bases abiertas. El estado beta debe verse desde la apertura, con detalle al final.

La secuencia editorial aprobada es:

**Qué es → para qué sirve → quién trabaja → cómo entrega → qué conserva → qué límites tiene → sobre qué se construye → cómo empezar.**

## 4. Ocho secciones aprobadas

Las categorías y su orden están aprobados. Los bloques marcados como texto aprobado
se conservan literalmente. El apartado 07 fue sustituido por autoría y código abierto.

Las ocho secciones no equivalen a ocho pantallas completas. Sólo la apertura, la
demostración y el equipo necesitan gran protagonismo visual. El resto puede alternar
composiciones amplias con bloques editoriales compactos.

| Orden | Categoría | Pregunta del visitante | Peso visual propuesto |
| --- | --- | --- | --- |
| 00 | Qué es Aether | ¿Qué estoy viendo y por qué me interesa? | Muy alto |
| 01 | Qué puedes desarrollar | ¿Qué le encargo y qué recibo? | Alto |
| 02 | Un equipo con responsabilidades claras | ¿Quién diseña, implementa y revisa? | Muy alto |
| 03 | Del objetivo al resultado | ¿Cómo se convierte una idea en una entrega? | Alto |
| 04 | Conocimiento que permanece | ¿Cómo reutiliza el contexto del proyecto? | Medio-alto |
| 05 | Autonomía con límites y evidencia | ¿Qué puedo comprobar y controlar? | Alto |
| 06 | Abierto y configurable | ¿De qué depende y qué puedo elegir? | Medio |
| 07 | Autoría y código abierto | ¿Quién lo creó y dónde está el código? | Editorial |

### 00. Qué es Aether

**Texto aprobado para el hero — conservar literalmente:**

```text
00 / ORIGEN

AETHER AGENTS

Del éter al software.

Aether Agents es un sistema multiagente de ingeniería de software diseñado para
convertir objetivos en especificaciones, implementación, revisión e integración.

[ CÓMO FUNCIONA ↓ ]    [ GITHUB ↗ ]

BETA · OPEN SOURCE · SPEC-DRIVEN
```

No reescribir, resumir, traducir ni recolocar palabras dentro de este bloque sin una
nueva decisión explícita del propietario. La adaptación inglesa se hará después desde
este texto fuente aprobado.

Debajo o junto a la metadata del hero se añade una franja secundaria de referencias
externas. Debe tener menor peso visual que el copy principal y funcionar como enlaces
de salida, no como parte del mensaje principal:

```text
FOUNDATIONS / HERMES AGENT ↗ · GITHUB SPEC KIT ↗
OPTIONAL KNOWLEDGE / GRAPHIFY ↗
```

- `HERMES AGENT` → https://hermes-agent.nousresearch.com/docs
- `GITHUB SPEC KIT` → https://github.com/github/spec-kit
- `GRAPHIFY` → https://github.com/Graphify-Labs/graphify

La separación entre `FOUNDATIONS` y `OPTIONAL KNOWLEDGE` es intencional: Hermes Agent
y GitHub Spec Kit son bases seleccionadas del producto; Graphify es una integración
opcional de conocimiento y no debe presentarse como dependencia obligatoria.

La documentación permanece accesible desde la navegación.

La pieza artística introduce la identidad, pero el nombre, la explicación y las acciones
no esperan una animación de entrada ni deben leerse dentro de una imagen.
No usar una consola decorativa como supuesto estado operativo real.

**Profundidad:** explicación del producto y límites en documentación.

### 01. Qué puedes desarrollar

**Estado:** contenido y representación visual aprobados por el propietario el 2026-09-06.

**Texto aprobado — conservar literalmente:**

```text
01 / DESARROLLO

Nuevos proyectos.
Nuevas capacidades.
Software que evoluciona.

Aether está diseñado para trabajar tanto en proyectos nuevos como en software que ya existe.
Define el objetivo: crear, ampliar, corregir o transformar una parte del sistema.

El resultado no es sólo una respuesta.
Es trabajo de ingeniería implementado, probado, revisado e integrado dentro del alcance acordado.

CREAR
Un proyecto desde cero.

AMPLIAR
Una nueva capacidad sobre un proyecto existente.

MEJORAR
Corregir, refactorizar o evolucionar una parte del software.

GREENFIELD · BROWNFIELD · SPEC-DRIVEN
```

El punto 01 incorpora además un bloque lateral aprobado sobre trabajo autónomo de largo horizonte:

```text
LONG HORIZON / UNATTENDED

Trabajo de largo horizonte.

Diseñado para sostener horas de trabajo autónomo sin atención constante.

Aether mantiene el objetivo mientras los agentes diseñan, implementan,
revisan y corrigen hasta converger en una entrega verificable.
```

Como metadata técnica breve del mismo bloque pueden utilizarse estas etiquetas:

```text
LONG-HORIZON TASKS
HOURS OF AUTONOMOUS WORK
MINIMAL SUPERVISION
```

La frase «Diseñado para sostener horas de trabajo autónomo sin atención constante»
describe la intención del producto y no debe convertirse en una garantía de duración,
porcentaje de éxito o ausencia absoluta de intervención en la beta actual.

Una publicación o un despliegue no son resultados automáticos de cualquier encargo.

Un ejemplo conductor propuesto para toda la portada es: «Añade búsqueda y filtros a
este catálogo, conservando el comportamiento existente». Permite enseñar una intención,
un criterio de aceptación y un resultado sin convertir a Aether en un producto exclusivo
para sitios web. Es un ejemplo ilustrativo, no un trabajo ya realizado.

La demostración es un activo pendiente. Antes de publicar un caso real deben existir
revisión identificada, alcance, resultado verificable y permiso sobre los materiales.
Una grabación futura debe preservar la procedencia de la evidencia y retirar datos
privados. Un storyboard o prototipo se etiqueta como conceptual y no simula éxito.
Sin evidencia suficiente se publica el ejemplo conceptual, no un caso de éxito inventado.

**Profundidad:** caso completo y evidencia en documentación cuando existan.

**Representación visual aprobada:** un gran reloj orbital / astrolabio greco-futurista
animado, construido en el frontend (SVG/CSS o tecnología equivalente) y no como una
imagen adicional. La pieza debe representar trabajo autónomo de largo horizonte sin
convertir una duración concreta en una métrica o garantía del producto.

La composición combina referencias a un astrolabio o esfera armilar griega con
instrumentación computacional moderna. Los anillos y órbitas se mueven a velocidades
distintas y una aguja o señal activa sugiere el paso de horas. Alrededor de la pieza
pueden aparecer las acciones `CREAR`, `AMPLIAR` y `MEJORAR`; en el núcleo, los conceptos
`LONG HORIZON` y `UNATTENDED`. La metadata secundaria puede utilizar las frases
`HOURS OF AUTONOMOUS WORK` y `MINIMAL SUPERVISION`.

La pieza no debe mostrar un cronómetro con una duración específica, una medición de
rendimiento ni una promesa de horas exactas. El lenguaje visual debe conservar la
identidad griega de Aether mediante marcas radiales, geometría clásica reinterpretada
y, si resulta compositivamente útil, un meandro griego discreto. La paleta sigue el
sistema Catppuccin Mocha ya aprobado, con Mauve como señal activa principal.

**Estado visual:** aprobado. El reloj orbital / astrolabio greco-futurista animado es
la representación principal del punto 01.

### 02. Un equipo con responsabilidades claras

**Estado:** contenido y representación visual aprobados por el propietario el 2026-09-06.

**Texto aprobado — conservar literalmente:**

```text
02 / EQUIPO

Diseñar, construir y revisar
no son la misma responsabilidad.

Aether separa el desarrollo en tres roles con responsabilidades distintas.
Cada uno trabaja sobre el mismo objetivo, pero con un espacio de decisión diferente.

MORFEO / DISEÑO

Convierte tu intención en diseño, especificaciones y contratos ejecutables.
Es el vínculo entre el propietario y el sistema.

SUPERVISOR / CONVERGENCIA

Descompone el trabajo, coordina la ejecución, revisa los resultados
y conduce el proyecto hasta su integración.

IMPLEMENTERS / EJECUCIÓN

Construyen unidades de trabajo acotadas.
Pueden trabajar en paralelo cuando el proyecto lo permite.

TÚ CONSERVAS LA DIRECCIÓN DEL PRODUCTO.
AETHER SE ENCARGA DE LA EJECUCIÓN.
```

**Representación visual aprobada:** un diagrama animado del sistema con flujo
bidireccional. Debe mostrar `TÚ → MORFEO → SUPERVISOR → IMPLEMENTERS`, pero sin
representarlo como una cadena rígida. Un pulso o “paquete” visual recorre las aristas,
se bifurca hacia varios Implementers, regresa a Supervisor y puede volver a Morfeo
cuando el trabajo requiere revisión, corrección o ajuste de diseño.

El movimiento debe comunicar que el trabajo puede avanzar, regresar, quedarse
temporalmente en una parte del sistema y volver a circular hasta converger. Las aristas
y nodos permanecen visibles en reposo; los pulsos en Mauve (`#CBA6F7`) indican actividad.
La pieza debe construirse como diagrama nativo del frontend (preferentemente SVG/CSS/JS
o tecnología equivalente), no como imagen estática ni como organigrama empresarial.

No crear nombres propios para los otros roles ni presentar tres implementadores como un
límite intrínseco, tres especialidades fijas o una garantía de rendimiento.

**Profundidad:** [roles y autoridad](../docs/roles-and-authority.md).

### 03. Del objetivo al resultado

**Estado:** contenido y representación visual aprobados por el propietario el 2026-09-06.

**Texto aprobado — conservar literalmente:**

```text
03 / PROCESO

Una intención clara.
Una entrega verificable.

Aether transforma un objetivo en trabajo de ingeniería con alcance, restricciones
y criterios de aceptación explícitos antes de ejecutar cambios sustanciales.

INTENCIÓN
Qué quieres conseguir.

CONTRATO
Qué se hará, qué queda fuera y cómo se comprobará el resultado.

DESCOMPOSICIÓN
El Supervisor convierte el objetivo en unidades de trabajo coordinadas.

EJECUCIÓN
Los Implementers construyen y verifican sus unidades en espacios de trabajo aislados.

REVISIÓN
El trabajo se inspecciona, se corrige y puede regresar a ejecución cuando sea necesario.

INTEGRACIÓN
Los resultados convergen en una entrega coherente y verificable.

OBJECTIVE CONTRACT · EXECUTION · REVIEW · INTEGRATION
```

Bloque secundario aprobado:

```text
No todo objetivo necesita recorrer el pipeline completo.
El trabajo pequeño, claro y reversible puede ser resuelto directamente por Morfeo.
```

**Representación visual aprobada:** un diagrama de proceso animado distinto al diagrama
de roles de 02. Debe representar la transformación `INTENCIÓN → CONTRATO →
DESCOMPOSICIÓN → EJECUCIÓN → REVISIÓN → INTEGRACIÓN`, con estados de progreso y
retornos visibles, especialmente `REVISIÓN → EJECUCIÓN` cuando se requiere corrección.

El diagrama debe sentirse como un pipeline editorial vivo, con líneas finas, pulsos o
paquetes recorriendo el flujo y al menos un bucle de rework. No debe aparentar que todas
las tareas avanzan linealmente en una sola pasada ni que el esquema es un motor de estados
determinista. La pieza se construirá en el frontend, no como imagen estática.

**Profundidad:** [contratos](../docs/guides/objective-contracts.md),
[ejecución](../docs/guides/execution.md) y [ciclo de vida](../docs/guides/lifecycle.md).

### 04. Conocimiento que permanece

**Estado:** contenido conceptual y representación visual aprobados por el propietario el
2026-09-06.

**Texto fuente de la conversación de diseño — conservado en la implementación:**

```text
04 / CONOCIMIENTO

Contexto compartido.
Experiencia por rol.

Aether puede mantener un mapa técnico compartido del proyecto para ayudar a sus agentes
a comprender estructura, relaciones y cambios sin redescubrir todo desde cero.

CONOCIMIENTO DEL PROYECTO

Morfeo, Supervisor e Implementers pueden consultar y mantener una representación
compartida de la estructura técnica del proyecto.

EXPERIENCIA POR ROL

Cada rol conserva sus propias experiencias y aprendizajes del trabajo realizado,
separados por proyecto y responsabilidad.

MEMORIA DE MORFEO

Las preferencias del propietario pertenecen a Morfeo y permanecen separadas
del conocimiento técnico compartido.

SHARED PROJECT KNOWLEDGE · ROLE-SCOPED EXPERIENCE · OPTIONAL GRAPHIFY
```

```text
Graphify es una integración opcional.
El conocimiento ayuda a navegar y recuperar contexto, pero no sustituye al código, las especificaciones ni la verificación.
```

Mostrar dos capas diferentes: un mapa técnico del proyecto consultable y mantenible
por los tres roles, y experiencias conservadas en espacios separados por proyecto
y rol. La memoria de preferencias del propietario de Morfeo no debe confundirse con
esas experiencias ni con el grafo técnico.

La función editorial es explicar continuidad y consulta de contexto, no enumerar las
acciones de la herramienta. Atribuir la capacidad a la integración opcional de Graphify.
El grafo es una ayuda de navegación vinculada a una revisión, no una fuente infalible
ni un sustituto del código y las especificaciones.

No prometer ahorro de tokens, aprendizaje universal, entrenamiento de modelos ni
actualización omnisciente. El registro actual conserva estado parcial para componentes
de conocimiento; su inclusión no prueba adopción real ni beneficio medido.

**Representación visual aprobada:** una reinterpretación editorial y simplificada del
grafo de Graphify, basada en la imagen de referencia suministrada por el propietario y
en la composición greco-futurista generada para esta sección. La pieza muestra un grafo
de nodos y aristas distribuido en pequeños clusters/comunidades, con un nodo central y
algunas relaciones destacadas en Mauve, sobre el fondo oscuro Catppuccin Mocha.

La composición incorpora de forma secundaria la identidad griega de Aether mediante
escultura/arquitectura clásica y geometría editorial, sin convertir la sección en una
reproducción literal de la interfaz blanca de Graphify. El objetivo es enseñar de forma
inmediata qué clase de mapa técnico usa Aether, no reproducir cada control, etiqueta o
detalle de la aplicación original.

La visualización puede recibir movimiento sutil durante la implementación —por ejemplo,
pulsos por algunas aristas, respiración de nodos destacados o una ligera aparición de
clusters—, pero no necesita convertirse en otro diagrama complejo ni en una simulación
completa del producto. La composición visual aprobada queda cerrada; el timing y la
técnica exacta de esa animación se resolverán al implementar el frontend.

**Profundidad:** [conocimiento y experiencias](../docs/guides/project-knowledge.md).

### 05. Autonomía con límites y evidencia

**Estado:** contenido aprobado por el propietario el 2026-09-06. La sección no necesita
un elemento visual fuerte; su peso debe recaer en la tipografía, la composición editorial
y pequeños detalles de interfaz coherentes con la identidad del sitio.

**Texto aprobado — conservar literalmente:**

```text
05 / CONTROL

Delegar el trabajo
no significa perder la visibilidad.

Aether está diseñado para trabajar de forma autónoma dentro de un alcance definido,
manteniendo evidencia de lo que ocurre y preservando la capacidad de revisar,
corregir y revertir.

ALCANCE

El objetivo y sus criterios de aceptación delimitan qué debe hacerse
y qué queda fuera.

AISLAMIENTO

El trabajo se ejecuta en espacios Git separados para reducir interferencias
entre unidades concurrentes.

VERIFICACIÓN

Pruebas, revisión independiente e integración comprueban el resultado
antes de darlo por concluido.

OBSERVACIÓN

Aether conserva señales sobre avance, bloqueos, revisiones, cobertura
y resolución del trabajo.

RECUPERACIÓN

Cuando algo falla, el sistema prioriza corrección y rollback
antes que continuar sobre un estado incierto.

CONTRACT · WORKTREES · TESTS · REVIEW · OBSERVATION · ROLLBACK
```

Frase secundaria aprobada:

```text
Autonomía no significa ausencia de control.
Significa delegar con límites, evidencia y capacidad de recuperación.
```

**Tratamiento visual aprobado:** no añadir una ilustración, imagen hero, grafo ni
diagrama protagonista. La sección debe funcionar como un descanso editorial dentro de
la one-page, apoyándose en jerarquía tipográfica, divisores, numeración, pequeños estados
o marcas técnicas y movimiento ambiental muy discreto si resulta útil. No crear una
interfaz ficticia de observabilidad para rellenar espacio.

El copy debe conservar los límites reales del producto: no promete seguridad absoluta,
aislamiento entre usuarios hostiles ni ausencia total de intervención. Los worktrees son
aislamiento de trabajo, no una frontera de seguridad del sistema operativo. La observación
local tampoco debe traducirse en «100 % offline», porque proveedores y efectos externos
autorizados conservan sus propios límites.

**Profundidad:** [observación](../docs/guides/observation.md) y
[política y recuperación](../docs/guides/policy-and-recovery.md).

### 06. Abierto y configurable

**Estado:** contenido y tratamiento visual aprobados por el propietario el 2026-09-06.

**Texto aprobado — conservar literalmente:**

```text
06 / FUNDAMENTOS

Un sistema abierto.
Tus modelos. Tu proyecto.

Aether se construye sobre herramientas abiertas y separa la arquitectura del producto
de las decisiones de proveedor, modelo e infraestructura.

HERMES AGENT

Aporta el runtime de agentes, perfiles, herramientas, coordinación,
worktrees y sesiones.

GITHUB SPEC KIT

Aporta la base metodológica para convertir intención en especificaciones,
planes, tareas y criterios de calidad.

GRAPHIFY

Aporta conocimiento técnico opcional del proyecto mediante un grafo estructural
y experiencias separadas por rol.

MODELOS Y PROVEEDORES

La instalación puede elegir modelos y proveedores compatibles por rol.
No es obligatorio utilizar tres modelos distintos ni un único proveedor.

OPEN SOURCE · MIT · PROVIDER-FLEXIBLE
```

Nota secundaria aprobada:

```text
Aether Router es un proyecto compañero para routing y acceso a modelos, no un requisito universal de Aether Agents.
```

**Tratamiento visual aprobado:** esta sección no necesita un elemento visual fuerte.
Debe resolverse principalmente con composición editorial, tipografía, líneas, divisores,
pequeños símbolos o marcas monocromáticas y jerarquía clara entre fundamentos, sin añadir
otra ilustración protagonista ni una pared de logotipos. Cualquier movimiento debe ser
ambiental y discreto.

**Profundidad:** [límite del producto](../docs/product-boundary.md), documentación
de configuración compatible y [licencia](../LICENSE).

### 07. Autoría y código abierto

**Estado:** contenido y tratamiento visual aprobados por el propietario el 2026-09-06.

**Texto aprobado — conservar literalmente:**

```text
07 / AUTORÍA

Christopher Hernández Jiménez
Creador de Aether Agents.

Aether Agents es un proyecto de código abierto publicado bajo licencia MIT.
Puedes explorar el código, estudiar su arquitectura, modificarlo y contribuir al proyecto.

[ VER EN GITHUB ↗ ]
[ DOCUMENTACIÓN ↗ ]

OPEN SOURCE · MIT
```

**Tratamiento visual aprobado:** cierre editorial simple, sin otro elemento visual fuerte.
La sección debe presentar autoría y acceso al código con jerarquía tipográfica clara,
manteniendo la identidad Catppuccin Mocha del sitio. Puede recuperar de forma muy sutil
el ambiente del hero mediante textura, líneas o partículas, pero no debe introducir una
nueva ilustración protagonista, roadmap, estado de beta o resumen de capacidades.

**Profundidad:** [licencia](../LICENSE) y [contribución](../CONTRIBUTING.md).

## 5. Navegación propuesta

No es necesario reproducir las ocho secciones en el menú. Se proponen anclas a
«Sistema», «Proceso» y «Conocimiento», más «Documentación» y «GitHub».
La marca devuelve al inicio; un índice de sección puede acompañar el scroll sin
sustituir las etiquetas descriptivas.

La selección ES/EN se resuelve más adelante. Los titulares, la navegación y los
botones se redactan primero en español; los identificadores de herramientas y marcas
conservan sus nombres reales. No se publica una versión inglesa vacía.

## 6. Distribución de profundidad y ritmo visual

Como presupuesto editorial de trabajo, se proponen aproximadamente 650–900 palabras
de contenido principal en la landing, excluyendo navegación, pie y transcripción de
una demostración. No es un estándar de usabilidad ni una medida validada; se ajustará
al probar la composición y la comprensión.

La lectura rápida debe funcionar con titulares y subtítulos; los párrafos deben dar
la explicación suficiente; la documentación vinculada debe aportar instrucciones y
evidencia. No esconder las ideas esenciales dentro de acordeones, hover, vídeo o scroll
obligatorio para revelar cada palabra.

El estilo tech-noir y Catppuccin Mocha se aplican a la composición. Los títulos
editoriales pueden ser expresivos, pero cada sección conserva un rótulo descriptivo.
Los términos poéticos no deben ser los únicos nombres de navegación.

Las animaciones propuestas explican la separación de roles, la división y reunión
del trabajo y la consulta del conocimiento. No deben inventar estados o métricas,
secuestrar el desplazamiento ni bloquear la información. Proponer alternativa de
movimiento reducido, controles de reproducción cuando correspondan y una lectura
estática equivalente; la implementación y la verificación quedan pendientes.

La documentación comparte paleta y marca, pero prioriza texto, búsqueda y navegación.
No hereda automáticamente el collage, los efectos CRT o el ritmo cinematográfico.

## 7. Contenido que no merece sección propia en esta portada

El problema se resume entre apertura y equipo. Morfeo tiene protagonismo en el mapa
de roles sin requerir otra biografía. Contratos, paralelismo y revisión se agrupan
en el recorrido. Integraciones y elección de modelos comparten una sección compacta.

No incluir por ahora precios por planes, testimonios, empresas usuarias, comparativas
ganadoras, métricas de ahorro o contadores de actividad sin evidencia verificable.
No se recomiendan blog, noticias, newsletter o historia extensa como requisitos de
la primera portada. Una atribución de autoría puede vivir en el pie sin convertir el
producto en un currículum personal.

Los comandos completos, matrices de autoridad, especificaciones, política de parches,
guías de instalación, diagnósticos y detalle de versiones pertenecen a documentación.
Las limitaciones materiales sí se resumen en la portada y se enlazan para ampliación.

## 8. Fundamento de experiencia de usuario

Se consultaron las siguientes fuentes primarias el 2026-09-06:

- [Nielsen Norman Group: Homepage Design — 5 Fundamental Principles](https://www.nngroup.com/articles/homepage-design-principles/).
  Recomienda explicar propósito, mostrar ejemplos concretos y ofrecer acciones claras.
  Su recomendación general de sencillez y movimiento limitado se aplica aquí manteniendo
  la estética elegida sin exigir interacciones inusuales para comprender el contenido.
- [Nielsen Norman Group: Defer Secondary Content When Writing for Mobile Users](https://www.nngroup.com/articles/defer-secondary-content-for-mobile/).
  Sustenta priorizar información esencial y desplazar detalles a superficies secundarias.
- [W3C: Understanding SC 2.3.3 — Animation from Interactions](https://www.w3.org/WAI/WCAG22/Understanding/animation-from-interactions.html).
  El criterio AAA permite desactivar movimiento no esencial iniciado por interacción;
  la explicación incluye respetar la preferencia de movimiento reducido.
- [W3C: Understanding SC 2.2.2 — Pause, Stop, Hide](https://www.w3.org/WAI/WCAG22/Understanding/pause-stop-hide.html).
  El criterio A requiere mecanismos para pausar, detener u ocultar contenido automático
  en las condiciones definidas por el criterio; no toda animación se trata igual.

Estas fuentes respaldan principios, no un número universal de secciones, una tasa de
conversión, el presupuesto de palabras ni una validación del mercado de Aether.

## 9. Criterios de revisión de la propuesta

Antes de cerrar textos y diseño, comprobar que un lector nuevo puede explicar qué
es Aether, nombrar un encargo y su entregable, distinguir los tres roles, reconocer
el estado beta y encontrar documentación sin recorrer toda la página. Esa comprobación
con lectores todavía no se ha realizado.

Cada afirmación pública de capacidad debe tener fuente y alcance; cada caso real,
evidencia trazable; cada enlace, un destino disponible. La información esencial debe
seguir siendo comprensible en móvil y sin animaciones. Una imagen espectacular no
sustituye ninguna de estas condiciones.

El orden, la agrupación y los detalles de las secciones ya están aprobados. El ejemplo
conductor y la demostración no fueron seleccionados. Las decisiones técnicas delegadas
para el candidato local se registran en IMPLEMENTATION_PLAN.md; no autorizan integración
ni publicación antes de la revisión del propietario.

## 10. Registro de decisiones

### 2026-09-06 — Aprobación de la estructura

El propietario aprobó registrar la propuesta de ocho secciones como base de la
monopágina. La siguiente conversación definirá los elementos visuales para representarla.
Esta aprobación no selecciona recursos gráficos ni inicia la implementación del sitio.
