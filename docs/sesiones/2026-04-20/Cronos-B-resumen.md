# Cronos B — 2026-04-20

## Sesión anterior
- Cronos A (2026-04-20) — Setup completo WSL: SDK hermes-agent instalado, 6 Daimons configurados, z.ai Coding Plan corregido, guía de instalación creada

## Resumen ejecutivo
Continuación directa de Cronos A. Objetivo principal: hacer el proyecto portable para GitHub eliminando rutas absolutas hardcodeadas, y ejecutar el primer push público.

## Trabajo realizado

| Tarea | Descripción | Resultado |
|-------|-------------|-----------|
| Análisis de portabilidad | Identificar rutas absolutas `/home/prometeo/` en configs | ✅ Encontradas en `home/config.yaml` (3 ocurrencias) |
| Fix `home/config.yaml` | Reemplazar rutas con `__AETHER_ROOT__` y `__HERMES_PYTHON__` | ✅ Windows y WSL actualizados |
| Template hermes profile | Crear `home/profiles/hermes/config.yaml.template` minimal+portable | ✅ Con mcp_servers y platform_toolsets correctos |
| `scripts/configure.sh` | Script que sustituye placeholders tras clonar | ✅ Compatible BSD/GNU sed |
| `.gitignore` update | Ignorar `home/profiles/hermes/config.yaml` (auto-expandido por hermes) | ✅ |
| Primer commit | `git init` + `git add` + commit limpio (43 archivos, 0 secretos) | ✅ c102d4c |
| GitHub push | `gh repo create --public` + push | ✅ https://github.com/DarkArty07/Aether-Agents |

## Decisiones de diseño

| # | Decisión |
|---|----------|
| 1 | `home/config.yaml` se commitea CON placeholders `__AETHER_ROOT__` (hermes no lo auto-expande, solo los profiles) |
| 2 | `home/profiles/hermes/config.yaml` se GITIGNORA — hermes lo sobreescribe a 300 líneas con rutas absolutas |
| 3 | `configure.sh` genera el profile de hermes desde el template antes de la primera ejecución |
| 4 | WSL copy (`~/Aether-Agents/`) mantiene rutas absolutas reales — es copia de trabajo, no fuente git |
| 5 | Fuente de verdad git: `/mnt/c/.../Aether-Agents/` (Windows); sincronizar con rsync cuando haya cambios |

## Estado del sistema

- **GitHub**: https://github.com/DarkArty07/Aether-Agents — público, branch `main`
- **43 archivos** en el repositorio, cero secretos, cero rutas personales
- **WSL (`~/Aether-Agents/`)**: copia de trabajo con rutas absolutas reales, hermes funcionando
- **`home/config.yaml`** Windows: usa placeholders → necesita `configure.sh` para funcionar
- **`home/config.yaml`** WSL: rutas absolutas reales → hermes arranca directamente

## Pendientes

- Sincronizar docs/sesiones/ de Windows → WSL: `rsync -av /mnt/c/.../Aether-Agents/ ~/Aether-Agents/`
- Cuando hermes auto-expanda `~/Aether-Agents/home/profiles/hermes/config.yaml` a 300 líneas, NO sincronizar ese archivo de WSL → Windows
- Agregar CLAUDE.md al repo (actualmente solo existe en WSL)

## Siguiente paso sugerido

Sesión C: Probar el ecosistema completo. Arrancar hermes, verificar que Olympus conecta, hacer un `talk_to(agent="ariadna", action="open")` para validar que el primer Daimon se spawna correctamente.
