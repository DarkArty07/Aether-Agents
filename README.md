# Aether Agents

Sistema multi-agente basado en el framework **hermes-agent** (Nous Research) que orquesta 6 Daimons especializados para desarrollo de software colaborativo.

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

| Daimon | Rol | Modelo | Herramientas |
|--------|-----|--------|--------------|
| **Hermes** | Orchestrator | `glm-5.1` (z.ai) | hermes-agent, opencode-go |
| **Ariadna** | Project Manager | `kimi-k2.5` (opencode.go) | opencode-go |
| **Hefesto** | Senior Developer | `glm-5.1` (z.ai) | opencode-go |
| **Etalides** | Web Researcher | `minimax-m2.7` (opencode.go) | opencode-go |
| **Daedalus** | UX/UI Designer | `mimo-v2-omni` (opencode.go) | opencode-go |
| **Athena** | Security Engineer | `kimi-k2.6` (opencode.go) | opencode-go |

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
│   ├── config.yaml                # Config del orquestador (glm-5.1 via z.ai)
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
├── .eter/                         # Estado del proyecto (Ariadna tracking)
│   ├── .hermes/                   # DESIGN.md + PLAN.md
│   └── .ariadna/                  # CURRENT.md + LOG.md
│
└── pyproject.toml                 # Olympus MCP package
```

---

## Instalación

### 1. Copiar el proyecto a WSL

Desde PowerShell o CMD en Windows:

```powershell
# Opción A: Copiar toda la carpeta
xcopy /E /I "C:\Users\chris\Desktop\DEVELOPERSPROJECTS\Aether-Agents" "%USERPROFILE%\Aether-Agents"

# Opción B: Usar rsync desde WSL
rsync -av /mnt/c/Users/chris/Desktop/DEVELOPERSPROJECTS/Aether-Agents/ ~/Aether-Agents/
```

### 2. Verificar la copia en WSL

```bash
cd ~/Aether-Agents
ls -la
```

Deberías ver todas las carpetas y archivos del proyecto.

---

## Configuración

### 1. Variables de entorno

El proyecto usa `shared/env.base` como template. Copia y configura tu `.env`:

```bash
cd ~/Aether-Agents
cp shared/env.base .env
```

Edita `.env` con tus API keys:

```bash
# API Keys requeridas
GLM_API_KEY=tu_api_key_de_z_ai
OPENCODE_GO_API_KEY=tu_api_key_de_opencode_go

# Configuración del proyecto
HERMES_HOME=~/Aether-Agents/home
AETHER_PROJECT_ROOT=~/Aether-Agents
```

### 2. API Keys necesarias

| Variable | Proveedor | Usado por |
|----------|-----------|-----------|
| `GLM_API_KEY` | z.ai | Hermes, Hefesto |
| `OPENCODE_GO_API_KEY` | opencode.go | Ariadna, Etalides, Daedalus, Athena |

Obtén tus keys en:
- z.ai: https://z.ai/api
- opencode.go: https://opencode.go/api

### 3. Configurar HERMES_HOME

HERMES_HOME debe apuntar a la carpeta `home/` del proyecto. Esto aísla la configuración de Aether Agents de tu instalación global de hermes-agent.

**Importante**: `~/.hermes/` NO se toca — es la herramienta de trabajo personal de Christopher.

---

## Cómo Arrancar

### Opción A: Usar el script de verificación

```bash
cd ~/Aether-Agents
bash scripts/start.sh
```

Este script verifica que el ecosistema esté configurado correctamente y muestra las instrucciones de inicio.

### Opción B: Inicio manual

```bash
# Cargar variables de entorno
source .env

# Iniciar Hermes (orquestador)
HERMES_HOME=~/Aether-Agents/home hermes --profile hermes
```

### Opción C: Iniciar un Daimon específico

```bash
# Iniciar Hefesto (desarrollador)
HERMES_HOME=~/Aether-Agents/home hermes --profile hefesto

# Iniciar Ariadna (project manager)
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

### Ejecutar un skill

Desde la sesión de Hermes:

```
hermes> run skill <nombre-del-skill> [argumentos]
```

O delegar a un Daimon específico:

```
hermes> talk_to hefesto "implementa esta feature usando hefesto-workflow"
```

---

## Convención de Parches (Workflow Windows ↔ WSL)

Este proyecto usa un flujo de trabajo híbrido entre Windows y WSL:

### Regla de oro

```
Editar código → Windows (/mnt/c/.../Aether-Agents/)
Probar → WSL (~/Aether-Agents/)
Parches en WSL → copiar de vuelta a Windows
```

### Flujo completo

1. **Editar en Windows**
   - Abre tu editor favorito en Windows (VS Code, etc.)
   - Trabaja en: `C:\Users\chris\Desktop\DEVELOPERSPROJECTS\Aether-Agents\`

2. **Probar en WSL**
   ```bash
   cd ~/Aether-Agents
   # Ejecutar tests, iniciar agentes, verificar cambios
   bash scripts/start.sh
   ```

3. **Sincronizar cambios de vuelta**
   
   Si hiciste cambios directamente en WSL (parches, configuraciones):
   ```bash
   # Desde WSL, copiar cambios a Windows
   rsync -av ~/Aether-Agents/ /mnt/c/Users/chris/Desktop/DEVELOPERSPROJECTS/Aether-Agents/
   ```

   O desde PowerShell en Windows:
   ```powershell
   # Los cambios en WSL ya son visibles en Windows automáticamente
   # porque ~/Aether-Agents/ está en el filesystem de WSL
   # Si necesitas copiar explícitamente:
   wsl rsync -av ~/Aether-Agents/ /mnt/c/Users/chris/Desktop/DEVELOPERSPROJECTS/Aether-Agents/
   ```

### Usando patch tool para edits

Para edits específicos en WSL:

```bash
# Navegar al proyecto
cd ~/Aether-Agents

# Usar la herramienta patch para edits seguros
# (si estás usando un agente que soporta patch)
```

### Estado del proyecto

El tracking del proyecto se mantiene en `.eter/`:

```
.eter/
├── .hermes/
│   ├── DESIGN.md    # Diseño del sistema
│   └── PLAN.md      # Planificación de features
└── .ariadna/
    ├── CURRENT.md   # Estado actual del proyecto
    └── LOG.md       # Log de actividades
```

---

## Comandos Útiles

```bash
# Navegar al proyecto en WSL
cd ~/Aether-Agents

# Verificar configuración
bash scripts/start.sh

# Generar .env para un perfil específico
bash scripts/setup-env.sh hermes

# Iniciar orquestador
HERMES_HOME=~/Aether-Agents/home hermes --profile hermes

# Iniciar Daimon específico
HERMES_HOME=~/Aether-Agents/home hermes --profile <daimon>

# Ver logs
tail -f ~/Aether-Agents/home/logs/*.log

# Sincronizar Windows → WSL
rsync -av /mnt/c/Users/chris/Desktop/DEVELOPERSPROJECTS/Aether-Agents/ ~/Aether-Agents/

# Sincronizar WSL → Windows
rsync -av ~/Aether-Agents/ /mnt/c/Users/chris/Desktop/DEVELOPERSPROJECTS/Aether-Agents/
```

---

## Troubleshooting

### HERMES_HOME no configurado
```bash
export HERMES_HOME=~/Aether-Agents/home
```

### API keys faltantes
```bash
# Verificar .env
cat .env | grep API_KEY

# Recargar variables
source .env
```

### Permisos de scripts
```bash
chmod +x scripts/*.sh
```

### Olympus MCP no disponible
```bash
# Instalar desde pyproject.toml
cd src/olympus
pip install -e .
```

---

## Licencia

Proyecto interno de desarrollo. Todos los derechos reservados.

---

## Contacto

Para preguntas o soporte, contactar al maintainer del proyecto.
