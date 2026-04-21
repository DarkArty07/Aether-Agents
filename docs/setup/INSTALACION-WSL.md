# Guía de Instalación — Aether Agents en WSL

Fecha: 2026-04-20
Sesión: Cronos B

---

## Arquitectura de instalación

```
~/.hermes/hermes-agent/     ← SDK global (binario hermes)
~/.hermes/                  ← Perfil personal (NO tocar)
~/Aether-Agents/home/       ← HERMES_HOME de Aether (aislado)
~/Aether-Agents/src/olympus/ ← Olympus MCP Server
```

El binario `hermes` es global. La configuración de Aether vive completamente en `~/Aether-Agents/home/` y no toca `~/.hermes/`.

---

## Paso 1 — Instalar hermes-agent SDK

```bash
curl -fsSL https://raw.githubusercontent.com/NousResearch/hermes-agent/main/scripts/install.sh | bash
```

Instala en `~/.hermes/hermes-agent/` y deja el symlink en `~/.local/bin/hermes`.

**Verificar:**
```bash
hermes --version
# Hermes Agent v0.10.0 (2026.4.16)
```

> Playwright (browser tools) puede fallar si no hay TTY — no es crítico para Aether.

---

## Paso 2 — Copiar el proyecto a WSL

```bash
rsync -av /mnt/c/Users/chris/Desktop/DEVELOPERSPROJECTS/Aether-Agents/ ~/Aether-Agents/
cd ~/Aether-Agents
```

---

## Paso 3 — Crear el virtualenv de Olympus

El `pyproject.toml` requiere Python 3.11 y usa `uv`:

```bash
cd ~/Aether-Agents
uv venv --python 3.11 venv
source venv/bin/activate
uv pip install setuptools
uv pip install -e .
```

**Verificar:**
```bash
python -c "from olympus.config import get_config; print('OK')"
```

> **Nota:** El `build-backend` del `pyproject.toml` debe ser `setuptools.build_meta` (no `setuptools.backends._legacy:_Backend`). Ya está corregido.

---

## Paso 4 — Configurar variables de entorno

Copiar el template a cada perfil Daimon:

```bash
bash scripts/setup-env.sh
```

Esto copia `shared/env.base` a `home/profiles/<daimon>/.env` (solo si no existe).

Luego editar cada `.env` con las API keys reales. Los Daimons usan:
- `OPENCODE_GO_API_KEY` — todos los Daimons excepto Hermes
- `GLM_API_KEY` — Hermes (en `home/profiles/hermes/.env`)

**Crear manualmente el .env de Hermes:**
```bash
cat > ~/Aether-Agents/home/profiles/hermes/.env << 'EOF'
GLM_API_KEY=tu_key_aqui
GLM_BASE_URL=https://api.z.ai/api/coding/paas/v4
EOF
```

---

## Paso 5 — Configurar hermes para usar Aether por defecto

### 5a. Exportar HERMES_HOME en `.bashrc`

```bash
echo 'export HERMES_HOME=/home/prometeo/Aether-Agents/home' >> ~/.bashrc
```

> Cambiar `prometeo` por tu usuario WSL si es diferente.

### 5b. Establecer el perfil sticky

```bash
HERMES_HOME=~/Aether-Agents/home hermes profile use hermes
```

Desde ahora, `hermes` arranca directo el orchestrador de Aether.

---

## Paso 6 — Verificar el ecosistema

```bash
bash ~/Aether-Agents/scripts/start.sh
```

Output esperado:
```
Step 2: Verifying Olympus module...
  Discovered 6 Daimon(s): ['ariadna', 'athena', 'daedalus', 'etalides', 'hefesto', 'hermes']

Step 4: Verifying Daimon profiles...
  ariadna ✓
  hefesto ✓
  etalides ✓
  daedalus ✓
  athena ✓

=== Aether Agents Ready ===
```

---

## Paso 7 — Arrancar

```bash
hermes
```

Hermes arranca, conecta con Olympus MCP, y los Daimons se spawnean lazy cuando los necesites.

---

## Comandos de uso

```bash
# Arrancar Aether
hermes

# Ver perfiles del ecosistema
hermes profile list

# Logs de Olympus (cuando está corriendo)
tail -f ~/Aether-Agents/home/logs/olympus.log

# Sincronizar cambios Windows → WSL
rsync -av /mnt/c/Users/chris/Desktop/DEVELOPERSPROJECTS/Aether-Agents/ ~/Aether-Agents/

# Sincronizar cambios WSL → Windows
rsync -av ~/Aether-Agents/ /mnt/c/Users/chris/Desktop/DEVELOPERSPROJECTS/Aether-Agents/

# Si necesitas el hermes personal
HERMES_HOME=~/.hermes hermes
```

---

## Formato correcto de config.yaml en perfiles Daimon

El formato que hermes espera:

```yaml
# Correcto ✓
model:
  default: kimi-k2.5
  provider: opencode-go
  base_url: https://opencode.ai/zen/go/v1

platform_toolsets:
  cli:
    - file
    - memory
    - todo
```

```yaml
# Incorrecto ✗ (formato plano — hermes lo ignora)
model: kimi-k2.5
provider: opencode-go

toolsets:
  - file
  - memory
```

### Toolsets disponibles

| ID | Herramienta |
|----|-------------|
| `web` | Web Search & Scraping |
| `browser` | Browser Automation |
| `terminal` | Terminal & Processes |
| `file` | File Operations (read, write, patch, search) |
| `code_execution` | Execute Code |
| `memory` | Persistent Memory |
| `session_search` | Search past sessions |
| `todo` | Task Planning |
| `clarify` | Clarifying Questions |
| `delegation` | delegate_task (spawn subagents) |
| `skills` | Skills system |
| `hermes-cli` | Preset: todos los tools del CLI |

---

## Olympus MCP — configuración en config.yaml

El orchestrador (hermes) conecta con Olympus via MCP. En `home/profiles/hermes/config.yaml`:

```yaml
mcp_servers:
  olympus:
    command: /home/prometeo/.hermes/hermes-agent/venv/bin/python
    args:
      - -m
      - olympus.server
    env:
      AETHER_HOME: /home/prometeo/Aether-Agents/home
      PYTHONPATH: /home/prometeo/Aether-Agents/src
    enabled: true
```

> El Python usado es el del venv de hermes-agent, no el venv de Aether.
> Olympus se carga vía `PYTHONPATH` apuntando a `src/` del proyecto.

---

## Troubleshooting

### `hermes: command not found`
```bash
# El symlink está roto — reinstalar SDK
curl -fsSL https://raw.githubusercontent.com/NousResearch/hermes-agent/main/scripts/install.sh | bash
```

### `pip install` falla con `BackendUnavailable`
El `pyproject.toml` tenía el build-backend incorrecto. Usar `uv pip` en vez de `pip`:
```bash
source venv/bin/activate
uv pip install setuptools
uv pip install -e .
```

### Olympus no descubre Daimons
Cada perfil en `home/profiles/*/config.yaml` necesita el campo `agent:` con `name`, `role` y `description`. Sin ese campo, Olympus omite el perfil.

### Hermes arranca con el perfil personal en vez de Aether
Verificar que `.bashrc` tenga el export y abriste una terminal nueva:
```bash
echo $HERMES_HOME
# Debe mostrar: /home/prometeo/Aether-Agents/home
```

### Error 429 `Insufficient balance` en z.ai con Coding Plan activo

El Coding Plan de z.ai tiene **tres endpoints distintos** según el uso:

| Endpoint | Para qué sirve |
|----------|----------------|
| `https://api.z.ai/api/paas/v4` | API normal (créditos de pago por uso) |
| `https://api.z.ai/api/anthropic` | Herramientas compatibles con Anthropic (Claude Code, Cline) |
| `https://api.z.ai/api/coding/paas/v4` | **Hermes-agent y herramientas OpenAI-compatible** ✓ |

El error `Insufficient balance` aparece cuando se usa `paas/v4` (API normal) con una cuenta que solo tiene Coding Plan — los créditos del plan solo se consumen desde `coding/paas/v4`.

**Config correcto para Hermes en `home/profiles/hermes/config.yaml`:**
```yaml
model:
  default: glm-5.1
  provider: zai
  base_url: https://api.z.ai/api/coding/paas/v4
```

**`.env` correcto:**
```bash
GLM_API_KEY=tu_key_aqui
GLM_BASE_URL=https://api.z.ai/api/coding/paas/v4
```
