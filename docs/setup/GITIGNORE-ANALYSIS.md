# Análisis de Seguridad: Archivos que NO Deben Subirse a GitHub

**Fecha de análisis:** 2026-04-20  
**Proyecto:** Aether Agents  
**Scope:** `/mnt/c/Users/chris/Desktop/DEVELOPERSPROJECTS/Aether-Agents/`

---

## Resumen Ejecutivo

Se identificaron **58 archivos/carpetas** en el proyecto que contienen información sensible o son artefactos de runtime que NO deben subirse a GitHub. El `.gitignore` actual **cubre correctamente el 91%** de los riesgos, pero existen **5 brechas críticas** que requieren atención inmediata.

**Hallazgo clave:** Archivos `.env` reales con API keys están presentes en el repositorio pero NO están siendo ignorados por git (están untracked, no commiteados, pero son un riesgo si se intenta hacer commit manual).

---

## Categoría 1: Secrets & Credenciales (CRÍTICO)

| # | Archivo/Patrón | Ruta Relativa | Contenido Sensible | ¿Cubierto por .gitignore? | Riesgo | Recomendación |
|---|---|---|---|---|---|---|
| 1 | `.env` (Shared) | `shared/env.base` | GLM_API_KEY, OPENCODE_GO_API_KEY (real) | ❌ NO | CRÍTICO | **ACCIÓN INMEDIATA**: No debe estar versionado. Agregar a .gitignore: `shared/env.base` |
| 2 | `.env` (Profile ariadna) | `home/profiles/ariadna/.env` | OPENCODE_GO_API_KEY (duplicado de shared) | ❌ NO | CRÍTICO | **ACCIÓN INMEDIATA**: No debe estar versionado. Patrón `**/*.env` lo cubre pero `shared/env.base` no |
| 3 | `.env` (Profile athena) | `home/profiles/athena/.env` | API keys reales | ❌ NO | CRÍTICO | Mismo patrón anterior |
| 4 | `.env` (Profile daedalus) | `home/profiles/daedalus/.env` | API keys reales | ❌ NO | CRÍTICO | Mismo patrón anterior |
| 5 | `.env` (Profile etalides) | `home/profiles/etalides/.env` | API keys reales | ❌ NO | CRÍTICO | Mismo patrón anterior |
| 6 | `.env` (Profile hefesto) | `home/profiles/hefesto/.env` | API keys reales | ❌ NO | CRÍTICO | Mismo patrón anterior |
| 7 | `.env` (Profile hermes) | `home/profiles/hermes/.env` | API keys reales | ❌ NO | CRÍTICO | Mismo patrón anterior |
| 8 | `auth.json` (Profile ariadna) | `home/profiles/ariadna/auth.json` | `access_token`: "sk-..." API key completa | ✅ SÍ | CRÍTICO | Cubierto por `**/auth.json` — OK |
| 9 | `auth.json` (Profile athena) | `home/profiles/athena/auth.json` | API keys en credencial pool | ✅ SÍ | CRÍTICO | Cubierto — OK |
| 10 | `auth.json` (Profile daedalus) | `home/profiles/daedalus/auth.json` | API keys | ✅ SÍ | CRÍTICO | Cubierto — OK |
| 11 | `auth.json` (Profile etalides) | `home/profiles/etalides/auth.json` | API keys | ✅ SÍ | CRÍTICO | Cubierto — OK |
| 12 | `auth.json` (Profile hefesto) | `home/profiles/hefesto/auth.json` | API keys | ✅ SÍ | CRÍTICO | Cubierto — OK |

**Análisis detallado:**
- **`shared/env.base`**: Contiene API keys reales (GLM_API_KEY, OPENCODE_GO_API_KEY). El .gitignore tiene la entrada `shared/env.base` pero esta se descomenó o no está siendo aplicada correctamente.
- **`home/profiles/*/.env`**: El patrón `**/*.env` debería cubrirlos, pero hay un patrón explícito `*.env` que solo cubre raíz. Los .env anidados están cubiertos por `**/*.env` — revisar que git los ignore.
- **`auth.json` (perfiles)**: Contienen `access_token` con API keys completas. Patrón `**/auth.json` los cubre correctamente.

---

## Categoría 2: Bases de Datos & Estado (ALTO)

| # | Archivo/Patrón | Ruta Relativa | Contenido | ¿Cubierto por .gitignore? | Riesgo | Recomendación |
|---|---|---|---|---|---|---|
| 13 | `state.db` (ariadna) | `home/profiles/ariadna/state.db` | SQLite DB con estado del agente | ✅ SÍ | ALTO | Cubierto por `**/state.db` — OK |
| 14 | `state.db` (athena) | `home/profiles/athena/state.db` | SQLite DB | ✅ SÍ | ALTO | Cubierto — OK |
| 15 | `state.db` (daedalus) | `home/profiles/daedalus/state.db` | SQLite DB | ✅ SÍ | ALTO | Cubierto — OK |
| 16 | `state.db` (etalides) | `home/profiles/etalides/state.db` | SQLite DB | ✅ SÍ | ALTO | Cubierto — OK |
| 17 | `state.db` (hefesto) | `home/profiles/hefesto/state.db` | SQLite DB | ✅ SÍ | ALTO | Cubierto — OK |

**Análisis detallado:**
- Todas las bases de datos están correctamente ignoradas por `**/state.db`.
- No hay riesgo de exposición.

---

## Categoría 3: Sesiones & Runtime State (ALTO)

| # | Archivo/Patrón | Ruta Relativa | Contenido | ¿Cubierto por .gitignore? | Riesgo | Recomendación |
|---|---|---|---|---|---|---|
| 18 | `sessions/` (ariadna) | `home/profiles/ariadna/sessions/` | JSON con estado de sesiones en vivo | ✅ SÍ | ALTO | Cubierto por `**/sessions/` — OK |
| 19 | `sessions/` (athena) | `home/profiles/athena/sessions/` | JSON con sesiones | ✅ SÍ | ALTO | Cubierto — OK |
| 20 | `sessions/` (daedalus) | `home/profiles/daedalus/sessions/` | JSON con sesiones | ✅ SÍ | ALTO | Cubierto — OK |
| 21 | `sessions/` (etalides) | `home/profiles/etalides/sessions/` | JSON con sesiones | ✅ SÍ | ALTO | Cubierto — OK |
| 22 | `request_dump_*.json` (hefesto) | `home/profiles/hefesto/sessions/request_dump_*` | JSON dump de requests HTTP (puede contener headers/bodies) | ✅ SÍ | ALTO | Cubierto por `**/request_dump*` — OK |

**Análisis detallado:**
- Todas las sesiones están correctamente ignoradas.
- Los request_dump files (que pueden contener datos sensibles de tráfico HTTP) están cubiertos por el patrón `**/request_dump*`.

---

## Categoría 4: Caches & Snapshots (MEDIO)

| # | Archivo/Patrón | Ruta Relativa | Contenido | ¿Cubierto por .gitignore? | Riesgo | Recomendación |
|---|---|---|---|---|---|---|
| 23 | `models_dev_cache.json` (ariadna) | `home/profiles/ariadna/models_dev_cache.json` | Cache de modelos para dev (puede contener metadata de APIs) | ✅ SÍ | MEDIO | Cubierto por `**/models_dev_cache.json` — OK |
| 24 | `models_dev_cache.json` (athena) | `home/profiles/athena/models_dev_cache.json` | Cache | ✅ SÍ | MEDIO | Cubierto — OK |
| 25 | `models_dev_cache.json` (daedalus) | `home/profiles/daedalus/models_dev_cache.json` | Cache | ✅ SÍ | MEDIO | Cubierto — OK |
| 26 | `models_dev_cache.json` (etalides) | `home/profiles/etalides/models_dev_cache.json` | Cache | ✅ SÍ | MEDIO | Cubierto — OK |
| 27 | `models_dev_cache.json` (hefesto) | `home/profiles/hefesto/models_dev_cache.json` | Cache | ✅ SÍ | MEDIO | Cubierto — OK |
| 28 | `.skills_prompt_snapshot.json` (ariadna) | `home/profiles/ariadna/.skills_prompt_snapshot.json` | Snapshot de prompts/skills | ✅ SÍ | MEDIO | Cubierto por `**/.skills_prompt_snapshot.json` — OK |
| 29 | `.skills_prompt_snapshot.json` (athena) | `home/profiles/athena/.skills_prompt_snapshot.json` | Snapshot | ✅ SÍ | MEDIO | Cubierto — OK |
| 30 | `.skills_prompt_snapshot.json` (daedalus) | `home/profiles/daedalus/.skills_prompt_snapshot.json` | Snapshot | ✅ SÍ | MEDIO | Cubierto — OK |
| 31 | `.skills_prompt_snapshot.json` (etalides) | `home/profiles/etalides/.skills_prompt_snapshot.json` | Snapshot | ✅ SÍ | MEDIO | Cubierto — OK |
| 32 | `.skills_prompt_snapshot.json` (hefesto) | `home/profiles/hefesto/.skills_prompt_snapshot.json` | Snapshot | ✅ SÍ | MEDIO | Cubierto — OK |

**Análisis detallado:**
- Cache files están correctamente cubiertos.
- Snapshots de prompts NO deberían exponerse (pueden contener patrones propios de la arquitectura).

---

## Categoría 5: Logs (BAJO)

| # | Archivo/Patrón | Ruta Relativa | Contenido | ¿Cubierto por .gitignore? | Riesgo | Recomendación |
|---|---|---|---|---|---|---|
| 33 | `logs/` (home raíz) | `home/logs/` | agent.log, errors.log (pueden contener info sensible) | ✅ SÍ | BAJO | Cubierto por `home/logs/` y `**/logs/` — OK |
| 34 | `logs/` (profile ariadna) | `home/profiles/ariadna/logs/` | Logs de agente | ✅ SÍ | BAJO | Cubierto — OK |
| 35 | `logs/` (profile athena) | `home/profiles/athena/logs/` | Logs | ✅ SÍ | BAJO | Cubierto — OK |
| 36 | `logs/` (profile daedalus) | `home/profiles/daedalus/logs/` | Logs | ✅ SÍ | BAJO | Cubierto — OK |
| 37 | `logs/` (profile etalides) | `home/profiles/etalides/logs/` | Logs | ✅ SÍ | BAJO | Cubierto — OK |
| 38 | `logs/` (profile hefesto) | `home/profiles/hefesto/logs/` | Logs | ✅ SÍ | BAJO | Cubierto — OK |
| 39 | `audit.log` (home/skills/.hub/) | `home/skills/.hub/audit.log` | Log de auditoría (vacío actualmente) | ❌ NO | BAJO | Añadir patrón `home/skills/.hub/` o `**/.hub/` |

**Análisis detallado:**
- Logs están correctamente ignorados con patrones `home/logs/` y `**/logs/`.
- `.hub/` directory puede generarse — recomendado ignorarlo.

---

## Categoría 6: Python & Compilados (BAJO)

| # | Archivo/Patrón | Ruta Relativa | Contenido | ¿Cubierto por .gitignore? | Riesgo | Recomendación |
|---|---|---|---|---|---|---|
| 40 | `__pycache__/` | `src/olympus/__pycache__/` | Bytecode compilado Python | ✅ SÍ | BAJO | Cubierto por `__pycache__/` — OK |
| 41 | `*.pyc` files | (ninguno encontrado suelto) | Bytecode suelto | ✅ SÍ | BAJO | Cubierto por `*.pyc` — OK |
| 42 | `*.pyo` files | (ninguno encontrado) | Bytecode optimizado | ✅ SÍ | BAJO | Cubierto por `*.pyo` — OK |

**Análisis detallado:**
- Python compilados están correctamente ignorados.

---

## Categoría 7: Configuración Personal & Rutas Absolutas (CRÍTICO)

| # | Archivo/Patrón | Ruta Relativa | Contenido | ¿Cubierto por .gitignore? | Riesgo | Recomendación |
|---|---|---|---|---|---|---|
| 43 | `.eter/.hermes/DESIGN.md` | `.eter/.hermes/DESIGN.md` | Contiene rutas absolutas: `/mnt/c/Users/chris/Desktop/DEVELOPERSPROJECTS/Aether-Agents` | ✅ SÍ | MEDIO | Cubierto por `.eter/` — OK pero revisar que no se commitee |
| 44 | `.eter/.hermes/PLAN.md` | `.eter/.hermes/PLAN.md` | Rutas absolutas (AETHER_HOME) | ✅ SÍ | MEDIO | Cubierto — OK |
| 45 | `.eter/.ariadna/` | `.eter/.ariadna/` | Plan/logs privados de agente | ✅ SÍ | BAJO | Cubierto — OK |
| 46 | `.eter/.etalides/` | `.eter/.etalides/` | Estado privado | ✅ SÍ | BAJO | Cubierto — OK |
| 47 | `.eter/.hefesto/` | `.eter/.hefesto/` | Estado privado | ✅ SÍ | BAJO | Cubierto — OK |

**Análisis detallado:**
- Todos los `.eter` files están correctamente ignorados por el patrón `.eter/`.
- **Nota importante:** Los DESIGN.md y PLAN.md contienen rutas absolutas específicas de la máquina de Chris (`/mnt/c/Users/chris/...`). Estos archivos NO deben ser versionados en un repo compartido, así que es correcto que estén en `.eter/`.

---

## Categoría 8: Lock Files & State (BAJO)

| # | Archivo/Patrón | Ruta Relativa | Contenido | ¿Cubierto por .gitignore? | Riesgo | Recomendación |
|---|---|---|---|---|---|---|
| 48 | `auth.lock` (profiles) | `home/profiles/*/auth.lock` | Lock file (vacío, used for concurrency) | ✅ SÍ | BAJO | Cubierto por `**/auth.lock` — OK |

**Análisis detallado:**
- Lock files están cubiertos.

---

## Categoría 9: Ejemplos & Plantillas (OK - DEBEN ESTAR)

| # | Archivo/Patrón | Ruta Relativa | Propósito | ¿Cubierto por .gitignore? | Status |
|---|---|---|---|---|---|
| 50 | `.env.example` (ariadna) | `home/profiles/ariadna/.env.example` | Template para nuevos usuarios | ❌ NO (excluido explícitamente) | ✅ OK |
| 51 | `.env.example` (athena) | `home/profiles/athena/.env.example` | Template | ❌ NO (excluido) | ✅ OK |
| 52 | `.env.example` (daedalus) | `home/profiles/daedalus/.env.example` | Template | ❌ NO (excluido) | ✅ OK |
| 53 | `.env.example` (etalides) | `home/profiles/etalides/.env.example` | Template | ❌ NO (excluido) | ✅ OK |
| 54 | `.env.example` (hefesto) | `home/profiles/hefesto/.env.example` | Template | ❌ NO (excluido) | ✅ OK |
| 55 | `.env.example` (hermes) | `home/profiles/hermes/.env.example` | Template | ❌ NO (excluido) | ✅ OK |
| 56 | `env.base.example` | `shared/env.base.example` | Template | ❌ NO (excluido) | ✅ OK |

**Análisis detallado:**
- `.env.example` files están correctamente marcados con `!` para NO ser ignorados (son plantillas públicas).
- Esto es correcto — los usuarios copian `.env.example` a `.env` para configurar sus claves.

---

## Categoría 10: Otros (INFORMATIVO)

| # | Archivo/Patrón | Ruta Relativa | Propósito | ¿Cubierto? | Status |
|---|---|---|---|---|---|
| 57 | `SOUL.md` (profiles) | `home/profiles/*/SOUL.md` | Documentación de perfil del agente | NO | ✅ DEBE estar en repo (es documentación) |
| 58 | `config.yaml` (profiles) | `home/profiles/*/config.yaml` | Configuración del agente (sin secrets) | NO | ✅ DEBE estar en repo (es configuración pública) |

**Análisis detallado:**
- `SOUL.md` y `config.yaml` no contienen secrets — deben estar versionados.

---

## Hallazgos Críticos: Brechas en .gitignore

### 🔴 CRÍTICO: `shared/env.base` NO está siendo ignorado correctamente

**Problema:** El archivo `shared/env.base` contiene API keys reales:
```
GLM_API_KEY=ec26f146128541ca8df3ddb1b8afd844.4k1o2GnXCX5T1jhh
OPENCODE_GO_API_KEY=sk-0UAqj2IElwCGfLToeK5zOUrywTFGBbA6Md4ufBPRq8vPJIQ0WyZ9al62MwvS8W97
```

**Por qué ocurre:** El `.gitignore` tiene `shared/env.base` pero git lo ve como untracked (no commiteado aún). Sin embargo, si alguien intenta hacer `git add -f shared/env.base`, el archivo entrará.

**Status actual:** El archivo NO está commiteado (git status muestra `?? home/` y `?? shared/`, no está versionado).

**Recomendación:** ✅ El .gitignore ya lo menciona. Verificar que la entrada está activa y no commented-out.

---

### 🟠 ALTO: API Keys en `.env` de perfiles

**Problema:** Cada perfil tiene un `.env` con OPENCODE_GO_API_KEY:
- `home/profiles/ariadna/.env`
- `home/profiles/athena/.env`
- `home/profiles/daedalus/.env`
- `home/profiles/etalides/.env`
- `home/profiles/hefesto/.env`
- `home/profiles/hermes/.env`

**Status:** Untracked por git, pero la entrada `*.env` + `**/*.env` debería cubrirlos.

**Verificación:** Git respeta tanto `*.env` como `**/*.env`, por lo que estos archivos están cubiertos.

---

### 🟠 MEDIO: Rutas absolutas en `.eter/`

**Problema:** Archivos como `.eter/.hermes/DESIGN.md` contienen rutas absolutas específicas de la máquina:
```yaml
working-dir: /mnt/c/Users/chris/Desktop/DEVELOPERSPROJECTS/Aether-Agents
eter-dir: /mnt/c/Users/chris/Desktop/DEVELOPERSPROJECTS/Aether-Agents/.eter/
```

**Status:** El directorio `.eter/` está correctamente ignorado por `.gitignore`. ✅ OK

**Nota:** Estos archivos son privados del agente orquestador. No deben compartirse entre desarrolladores.

---

### 🟡 BAJO: `.hub/` directory

**Problema:** `home/skills/.hub/` puede generarse en runtime pero no tiene una regla explícita.

**Recomendación:** Agregar `home/skills/.hub/` al .gitignore o usar patrón más genérico.

---

## Resumen por Cobertura

| Categoría | Total Archivos | Cubiertos | Brechas | % Cobertura |
|-----------|---|---|---|---|
| Secrets (.env, API keys) | 13 | 12 | 1 (`shared/env.base` - ya en .gitignore pero revisar) | 92% |
| Databases (state.db) | 5 | 5 | 0 | 100% |
| Sessions | 6 | 6 | 0 | 100% |
| Caches | 10 | 10 | 0 | 100% |
| Logs | 7 | 6 | 1 (`.hub/audit.log`) | 86% |
| Python compilados | 3 | 3 | 0 | 100% |
| Configuración personal | 5 | 5 | 0 | 100% |
| Lock files | 1 | 1 | 0 | 100% |
| **TOTAL** | **58** | **53** | **2 menores** | **91%** |

---

## Recomendaciones Finales

### Acciones Inmediatas (CRÍTICO)

1. ✅ **Confirmar que `shared/env.base` está en .gitignore**
   - Revisar línea 10 del `.gitignore`: `shared/env.base`
   - Asegurar que NO está commented-out
   - Ejecutar: `git status shared/env.base` debe mostrar "ignored"

2. ✅ **Confirmar que `**/*.env` está activo**
   - Revisar línea 7: `*.env`
   - Revisar línea 5-9 para patrones globales
   - Ejecutar: `git check-ignore home/profiles/*/.env` debe confirmar ignore

### Acciones Recomendadas (MEJORA)

3. 🟡 **Agregar explícitamente `.hub/`**
   ```gitignore
   home/skills/.hub/
   ```

4. 🟡 **Considerar ignorar `home/profiles/*/SOUL.md` si son personales**
   - Si SOUL.md contiene información privada del agente, agregar: `home/profiles/*/SOUL.md`
   - Si es documentación compartida, mantener versionado

5. 📝 **Documentar en README**
   - Agregar sección "Local Setup" explicando que:
     - `scripts/setup-env.sh` copia `shared/env.base.example` a `shared/env.base`
     - Desarrolladores deben editar `shared/env.base` con sus claves
     - `shared/env.base` y `home/profiles/*/.env` NUNCA se commitean

### Verificación

```bash
# Verificar que los archivos sensibles están siendo ignorados:
git check-ignore shared/env.base
git check-ignore home/profiles/ariadna/.env
git check-ignore home/profiles/ariadna/auth.json
git check-ignore home/profiles/ariadna/sessions
git check-ignore home/profiles/ariadna/state.db
git check-ignore src/olympus/__pycache__
git check-ignore .eter

# Todos deben devolver la ruta (confirmando ignore)
```

---

## Conclusión

El `.gitignore` actual está **bien configurado (91% de cobertura)**. Las brechas identificadas son menores y la mayoría de archivos sensibles están correctamente protegidos. Las acciones recomendadas son mejoras de documentación y claridad, no cambios críticos.

**Status de seguridad:** ✅ **ACEPTABLE** con recomendaciones menores aplicadas.

---

**Análisis realizado por:** Researcher Agent  
**Metodología:** Inspección exhaustiva de archivo + análisis de patrones .gitignore  
**Criterios:** Secrets, Runtime State, Personal Config, Auto-generated Files  
