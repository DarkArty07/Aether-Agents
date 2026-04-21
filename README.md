# Aether Agents

Sistema multi-agente basado en el framework **hermes-agent** que orquesta 6 Daimons especializados para desarrollo de software colaborativo.

---

## ¿Qué es Aether Agents?

Aether Agents es un ecosistema de agentes de IA que trabajan coordinadamente para asistir en el desarrollo de software. El sistema está compuesto por:

- **Hermes**: El orquestador principal que coordina a todos los Daimons
- **6 Daimons**: Agentes especializados en diferentes áreas (gestión, desarrollo, investigación, diseño, seguridad)

La comunicación sigue este flujo:
```
Hermes → talk_to() → Olympus MCP (ACP protocol) → Daimon objetivo
```

Cada Daimon tiene su propio perfil de configuración, modelo de IA asignado y herramientas específicas.

---

## Los 6 Daimons

| Daimon | Rol | Modelo sugerido | Herramientas |
|--------|-----|-----------------|--------------|
| **Hermes** | Orchestrator | `glm-5.1` (z.ai) | hermes-agent |
| **Ariadna** | Project Manager | `kimi-k2.5` (opencode.go) | opencode-go |
| **Hefesto** | Senior Developer | `glm-5.1` (z.ai) | opencode-go |
| **Etalides** | Web Researcher | `minimax-m2.7` (opencode.go) | opencode-go |
| **Daedalus** | UX/UI Designer | `mimo-v2-omni` (opencode.go) | opencode-go |
| **Athena** | Security Engineer | `kimi-k2.6` (opencode.go) | opencode-go |

> **Nota sobre modelos**: Los modelos listados son sugerencias probadas que funcionaron bien para cada rol en nuestras pruebas. No son requisitos obligatorios — puedes asignar cualquier modelo que soporte el proveedor configurado. Te recomendamos evaluar modelos con prompts de dominio antes de asignarlos a cada Daimon.

### Descripción de roles

- **Hermes**: Coordina tareas, delega trabajo a los Daimons, mantiene el estado del proyecto
- **Ariadna**: Gestiona planificación, tracking de tareas, documentación de diseño y planes
- **Hefesto**: Desarrollo de código senior, refactorización, implementación de features
- **Etalides**: Investigación web, búsqueda de documentación, análisis de tecnologías
- **Daedalus**: Diseño de interfaces, UX/UI, prototipado visual
- **Athena**: Auditoría de seguridad, revisión de código, mejores prácticas de seguridad

---

## Estructura del Proyecto

```
Aether-Agents/
├── home/                          # HERMES_HOME del proyecto
│   ├── config.yaml                # Config del orquestador
│   ├── profiles/
│   │   ├── hermes/                # Orchestrator
│   │   ├── ariadna/               # Project Manager
│   │   ├── hefesto/               # Senior Developer
│   │   ├── etalides/              # Web Researcher
│   │   ├── daedalus/              # UX/UI Designer
│   │   └── athena/                # Security Engineer
│   ├── sessions/                  # Auto-creado por hermes
│   └── logs/                      # Auto-creado por hermes
│
├── skills/
│   └── aether-agents/             # Skills del ecosistema
│       ├── orchestration/         # Skill de orquestación de Hermes
│       ├── ariadna-workflow/
│       ├── hefesto-workflow/
│       ├── etalides-workflow/
│       ├── daedalus-workflow/
│       └── athena-workflow/
│
├── src/olympus/                   # MCP server (ACP protocol)
│   ├── server.py
│   ├── acp_client.py
│   ├── discovery.py
│   ├── registry.py
│   ├── config.py
│   └── log.py
│
├── shared/env.base                # Template de variables de entorno
├── scripts/
│   ├── setup-env.sh               # Genera .env por perfil
│   └── start.sh                   # Verifica ecosistema y muestra instrucciones
│
├── .eter/                         # Estado del proyecto (gitignored)
│   ├── .hermes/                   # DESIGN.md + PLAN.md
│   └── .ariadna/                  # CURRENT.md + LOG.md
│
└── pyproject.toml                 # Olympus MCP package
```

---

## Instalación

### 1. Clonar el repositorio

```bash
git clone https://github.com/DarkArty07/Aether-Agents.git
cd Aether-Agents
```

### 2. Crear entorno virtual e instalar dependencias

```bash
python3 -m venv venv
source venv/bin/activate
pip install -e .
```

### 3. Configurar variables de entorno

El proyecto usa `shared/env.base` como template. Ejecuta el script de setup para generar los `.env` de cada perfil:

```bash
bash scripts/setup-env.sh
```

Luego edita cada `.env` en `home/profiles/<daimon>/` con tus API keys según los modelos que hayas elegido.

---

## Configuración

### API Keys

Las API keys dependen de los proveedores de los modelos que elijas para cada Daimon. Configura las keys en el `.env` de cada perfil:

| Variable de ejemplo | Proveedor | Perfiles típicos |
|---------------------|-----------|------------------|
| `GLM_API_KEY` | z.ai | Hermes, Hefesto |
| `OPENCODE_GO_API_KEY` | opencode.go | Ariadna, Etalides, Daedalus, Athena |

> Estas variables son ejemplos basados en los modelos sugeridos. Si usas otros proveedores, configura las variables correspondientes.

### HERMES_HOME

`HERMES_HOME` debe apuntar a la carpeta `home/` del proyecto. Esto aísla la configuración de Aether Agents de tu instalación global de hermes-agent.

```bash
export HERMES_HOME=~/Aether-Agents/home
```

---

## Cómo Arrancar

### Opción A: Usar el script de verificación

```bash
cd ~/Aether-Agents
source venv/bin/activate
bash scripts/start.sh
```

### Opción B: Inicio manual

```bash
cd ~/Aether-Agents
source venv/bin/activate
HERMES_HOME=~/Aether-Agents/home hermes --profile hermes
```

### Iniciar un Daimon específico (para testing)

```bash
HERMES_HOME=~/Aether-Agents/home hermes --profile hefesto
HERMES_HOME=~/Aether-Agents/home hermes --profile ariadna
```

---

## Uso de Skills

Los skills están organizados en `skills/aether-agents/` y se cargan vía `external_dirs` en la configuración de cada perfil.

### Estructura de skills

```
skills/aether-agents/
├── orchestration/         # Habilidades de orquestación (Hermes)
├── ariadna-workflow/      # Flujo de trabajo de gestión de proyectos
├── hefesto-workflow/      # Flujo de trabajo de desarrollo
├── etalides-workflow/     # Flujo de trabajo de investigación
├── daedalus-workflow/     # Flujo de trabajo de diseño
└── athena-workflow/       # Flujo de trabajo de seguridad
```

### Cargar skills

Los skills se cargan automáticamente cuando inicias un perfil. La configuración en `home/profiles/<nombre>/config.yaml` debe incluir:

```yaml
external_dirs:
  - ~/Aether-Agents/skills/aether-agents/<workflow-name>/
```

---

## talk_to — Ciclo de vida de sesiones

El orquestador se comunica con los Daimons usando este flujo:

```
discover → open → message → poll (o wait) → close
```

| Acción | Descripción |
|--------|-------------|
| `discover` | Lista agentes disponibles |
| `open` | Spawnea el Daimon (si está muerto) y crea una sesión ACP |
| `message` | Envía un prompt (async, retorna inmediatamente) |
| `poll` | Consulta progreso — thoughts, mensajes, tool calls |
| `wait` | Bloquea hasta que termine (máx 300s) |
| `cancel` | Aborta una sesión en curso |
| `close` | Cierra la sesión; el proceso del agente se mantiene vivo |

Los Daimons son **keep-alive** — se spawnean en el primer `open` y se mantienen vivos entre sesiones.

---

## Troubleshooting

### HERMES_HOME no configurado
```bash
export HERMES_HOME=~/Aether-Agents/home
```

### API keys faltantes
```bash
cat home/profiles/hermes/.env
# Editar con tus keys
```

### Permisos de scripts
```bash
chmod +x scripts/*.sh
```

### Olympus MCP no disponible
```bash
source venv/bin/activate
pip install -e .
```

---

## Licencia

Proyecto privado. Todos los derechos reservados.
