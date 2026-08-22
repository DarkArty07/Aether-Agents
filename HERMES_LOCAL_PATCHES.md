# Índice de parches locales de Hermes

**Estado:** registro operativo canónico de las diferencias funcionales que Aether mantiene sobre su Hermes cargado.

Este archivo evita que una actualización de Hermes elimine silenciosamente correcciones locales. Un issue de Aether puede cerrarse porque el runtime efectivo está corregido, aunque su entrada permanezca `ACTIVE_LOCAL` hasta que una revisión upstream equivalente sea integrada y verificada.

## Runtime de referencia

- Hermes: `0.20.1`
- Revisión base: `411903b6fa258f81afcc3869eb615f6218e1776a`
- Fuente editable cargada por Aether: `home/.venv-hermes/src/hermes-agent`
- Servicio que debe recargarse después de modificar el runtime: `hermes-gateway.service`
- Última conciliación de este índice: `2026-08-21 UTC`

## Estados

- `ACTIVE_LOCAL`: la corrección está presente y Aether depende de ella.
- `UPSTREAM_OPEN`: existe issue o PR upstream, pero todavía no forma parte de una revisión publicada y calificada por Aether.
- `UPSTREAM_VERIFIED`: la revisión objetivo ya contiene comportamiento equivalente y pasó la matriz de aceptación de esta entrada.
- `RELOAD_PENDING`: el código y la configuración locales están escritos y probados en proceso nuevo, pero el proceso de servicio aún no los ha recargado.
- `RETIRED`: el parche local fue retirado después de comprobar equivalencia upstream y revalidar el runtime efectivo.

## Registro activo

| ID | Issue Aether | Corrección local | Seguimiento upstream | Estado |
|---|---|---|---|---|
| `HLP-188` | `#188` | `initial_status=blocked` permanece bloqueado hasta un desbloqueo explícito | PR `NousResearch/hermes-agent#91180` | `ACTIVE_LOCAL / UPSTREAM_OPEN` |
| `HLP-189` | `#189` | `kanban_create` expone, valida y persiste `max_retries` | PR `NousResearch/hermes-agent#89590` | `ACTIVE_LOCAL / UPSTREAM_OPEN` |
| `HLP-191` | `#191` | una escalación de loop/`needs_input` permanece human-gated y no vuelve al trabajo automáticamente | PR `NousResearch/hermes-agent#91211`; la CLI local de recuperación explícita no está incluida en ese PR | `ACTIVE_LOCAL / UPSTREAM_OPEN` |
| `HLP-194` | `#194` | un worker requiere exactamente un handoff terminal exitoso y durable | PR `NousResearch/hermes-agent#91220` | `ACTIVE_LOCAL / UPSTREAM_OPEN` |
| `HLP-198` | `#198` | el primer spawn de un worktree recibe la rama efectiva ya resuelta | issue `NousResearch/hermes-agent#89677`; PR `#89688` | `ACTIVE_LOCAL / UPSTREAM_OPEN` |
| `HLP-204` | `#204`, `#205` | límites asimétricos por perfil aplicados de forma compartida a ready/review; topología inicial Supervisor 1 / Implementer 3 | issue `NousResearch/hermes-agent#91259`; PR `#91266` | `ACTIVE_LOCAL / UPSTREAM_OPEN` |
| `HLP-209` | sin issue/PR nuevo; `#209` conserva sólo la traza downstream previa | los directorios detectados por el walker no se tratan como scripts inseguros; dispositivos y scripts reales siguen fail-closed | issue upstream `#86753`; commit integrado `9ac1e65b0ae4e83dced9d5c8a406cc57cb589702` | `ACTIVE_LOCAL / UPSTREAM_VERIFIED` |

## HLP-188 — `initial_status=blocked` sticky

- **Motivo:** la recomputación del dispatcher podía promover una tarjeta creada bloqueada sin un `unblock` explícito.
- **Archivos activos principales:**
  - `hermes_cli/kanban_db.py`
  - `tests/hermes_cli/test_kanban_blocked_sticky.py`
- **Evidencia local:** pruebas focalizadas de base/herramienta y sonda post-reinicio con procesos y SQLite temporales; el estado sólo cambió mediante `unblock_task` explícito.
- **Upstream:** <https://github.com/NousResearch/hermes-agent/pull/91180>, abierto y mergeable; checks requeridos verdes al conciliar este índice.
- **Gate de retirada:** crear una tarjeta con `initial_status="blocked"` en la revisión objetivo, ejecutar recomputación, resolver dependencias, reabrir la base en otro proceso y demostrar que sólo un desbloqueo explícito la mueve a `ready`.

## HLP-189 — `max_retries` en `kanban_create`

- **Motivo:** CLI y base de datos soportaban el campo, pero la herramienta disponible para workers no lo exponía ni lo transmitía.
- **Archivos activos principales:**
  - `tools/kanban_tools.py`
  - `tests/tools/test_kanban_tools.py`
- **Evidencia local:** `8 passed`; Ruff y diff verdes; un proceso creó una tarjeta mediante el handler real con `max_retries=3` y otro proceso reabrió SQLite y verificó el valor persistido.
- **Upstream:** <https://github.com/NousResearch/hermes-agent/pull/89590>, abierto y mergeable, sin checks reportados al conciliar este índice.
- **Gate de retirada:** comprobar en la revisión objetivo que el esquema de `kanban_create` expone un entero con mínimo `1`, que el handler lo transmite y que otro proceso observa el mismo valor persistido.

## HLP-191 — escalaciones human-gated

- **Motivo:** una tarjeta escalada por loop de bloqueo podía volver a auto-descomposición o redispatch sin recuperación humana explícita.
- **Archivos activos principales:**
  - `gateway/kanban_watchers.py`
  - `hermes_cli/kanban_db.py`
  - `hermes_cli/kanban_decompose.py`
  - `hermes_cli/kanban.py`
  - `tests/hermes_cli/test_kanban_decompose.py`
  - `tests/hermes_cli/test_kanban_cli.py`
  - `tests/gateway/test_kanban_auto_decompose_recovery.py`
- **Diferencia local adicional:** `hermes kanban unblock --recover-escalated` registra `triage_escalation_recovered` y reinicia sólo el estado del loop; mantiene la tarjeta en `triage`. Esta superficie CLI no aparece en los archivos del PR upstream `#91211` y debe verificarse separadamente al actualizar.
- **Evidencia local:** suite focalizada `14 passed`; sonda post-reinicio con dos procesos confirmó que la escalación sobrevivía reconexión y reasignación y permanecía fuera del auto-decomposer.
- **Upstream:** <https://github.com/NousResearch/hermes-agent/pull/91211>, abierto y mergeable, sin checks reportados al conciliar este índice.
- **Gate de retirada:** probar escalación, reconexión, reasignación y tick de auto-descomposición; después probar una recuperación explícita que produzca un evento durable y no reanude por sí sola la tarjeta. Si upstream no incluye la recuperación CLI equivalente, conservar esa parte local aunque el resto del PR haya sido integrado.

## HLP-194 — handoff terminal durable y único

- **Motivo:** un worker podía terminar con código `0` sin `kanban_complete`, `kanban_block` u otro lifecycle terminal exitoso y durable.
- **Archivos activos principales:**
  - `agent/conversation_loop.py`
  - `agent/kanban_stop.py`
  - `agent/turn_finalizer.py`
  - `cli.py`
  - `hermes_cli/kanban_db.py`
  - `hermes_cli/kanban_exit_codes.py`
  - `tests/agent/test_kanban_stop.py`
  - `tests/hermes_cli/test_kanban_protocol_exit.py`
  - `tests/run_agent/test_kanban_terminal_guard_integration.py`
- **Evidencia local:** post-reinicio `49 passed`; compilación, Ruff y diff verdes; cobertura de salida `0`, violación explícita, excepción, señal, timeout, receipt real post-commit, receipt rechazado y handoffs contradictorios/duplicados.
- **Upstream:** <https://github.com/NousResearch/hermes-agent/pull/91220>, abierto y mergeable, sin checks reportados al conciliar este índice.
- **Gate de retirada:** repetir toda la matriz anterior en la revisión objetivo y verificar que `EX_PROTOCOL=76`, eventos y outcomes distinguen protocolo, crash, señal y timeout.

## HLP-198 — rama efectiva en el primer spawn

- **Motivo:** el dispatcher persistía la rama derivada, pero entregaba a `_default_spawn` el objeto reclamado obsoleto y omitía `HERMES_KANBAN_BRANCH` en el primer intento.
- **Archivos activos principales:**
  - `hermes_cli/kanban_db.py`
  - `tests/hermes_cli/test_kanban_db.py`
- **Evidencia local:** `32 passed, 1 skipped`; prueba con procesos reales confirmó igualdad entre `HERMES_KANBAN_BRANCH`, `git branch --show-current` y `branch_name` persistido en lanes `ready` y `review`; tareas `dir` no reciben rama inventada.
- **Upstream:** <https://github.com/NousResearch/hermes-agent/issues/89677> y <https://github.com/NousResearch/hermes-agent/pull/89688>; ambos abiertos, PR mergeable y checks requeridos verdes al conciliar este índice.
- **Gate de retirada:** repetir la prueba del primer spawn en lanes `ready` y `review`, más control `dir`/`scratch`, sobre la revisión objetivo sin el parche local.

## HLP-204 — límites asimétricos de concurrencia por perfil

- **Motivo:** `max_in_progress_per_profile` imponía el mismo techo a todos los perfiles y no podía expresar un único Supervisor junto con varios Implementers. Aether necesita acelerar la ruta crítica mediante unidades independientes sin permitir Supervisors duplicados ni relajar revisión.
- **Topología aceptada:** `max_in_progress: 4`, fallback uniforme `3`, override `supervisor: 1`, override `implementer: 3`. Morfeo no forma parte del dispatcher Kanban.
- **Semántica:** el límite efectivo es el override del assignee cuando existe y, en otro caso, el fallback uniforme. Ready y review comparten el mismo contador, incluidas tareas ya activas y dry-run.
- **Archivos activos principales:**
  - `hermes_cli/kanban_db.py`
  - `hermes_cli/kanban.py`
  - `hermes_cli/config_defaults.py`
  - `gateway/kanban_watchers.py`
  - `tests/hermes_cli/test_kanban_per_profile_cap.py`
  - `tests/hermes_cli/test_kanban_per_profile_overrides.py`
  - `tests/hermes_cli/test_kanban_cli_dispatch_passthrough.py`
  - `tests/gateway/test_kanban_watchers_mixin.py`
  - `home/config.yaml`
- **Evidencia local post-reload:** gateway activo con PID `1284969`, `Result=success`, `ExecMainStatus=0`, cero reinicios y cero errores del PID nuevo; `91 passed`; Ruff y `py_compile` verdes; `load_config()` resolvió `max_in_progress=4`, fallback `3` y overrides `{'supervisor': 1, 'implementer': 3}`. La prueba mixta cubre ready/review, tarea ya activa, dry-run y límite fallback.
- **Backup reversible:** `.aether/backups/issue-204-profile-concurrency/`; las nueve fuentes respaldadas fueron verificadas byte a byte por SHA-256 antes del port.
- **Upstream:** inicialmente desarrollado contra `origin/main` `76952ba54f5dd83f4f5bd0246059171b4b9d1c4a` y rebasado/calificado sin conflictos contra `533886c8b8eb67ff8b389b7f48e7d5e5d9c575b9`; `git range-diff` confirmó que los tres commits conservan contenido idéntico. Worktree: `/tmp/hermes-profile-caps-204`; issue <https://github.com/NousResearch/hermes-agent/issues/91259>; PR <https://github.com/NousResearch/hermes-agent/pull/91266>, abierto y mergeable. El PR preserva la autoría de las pruebas del intento previo `#70674` y completa kernel, ready/review, CLI, gateway, defaults, validación y documentación. La rama remota no fue reescrita tras el rebase local porque no había autorización para force-push; GitHub evalúa el mismo diff contra el `main` vivo.
- **Estado de activación:** activo y validado post-reinicio. El proceso anterior salió con código 1 durante el SIGTERM intencional; ese defecto separado no impidió el arranque nuevo y ya está registrado upstream en `NousResearch/hermes-agent#24344` con nuestra reproducción.
- **Gate de retirada:** sobre la revisión objetivo sin parche local, configurar overrides, verificar `Supervisor=1` e `Implementer=3` en una mezcla de ready/review con running previo y dry-run, probar passthrough CLI/gateway y normalización de valores inválidos, cargar la configuración efectiva y repetir la cualificación post-reinicio.

## HLP-209 — los directorios no son scripts de lifecycle

- **Motivo:** el walker de scripts referenciados interpretaba una ruta absoluta de directorio dentro de un `python3 -c` multilínea como candidato ejecutable. `_read_referenced_script` clasificaba todo objeto no regular como inseguro y producía el mensaje genérico de reinicio/detención del gateway aunque los escaneos directos no encontraran ninguna acción de lifecycle.
- **Decisión:** no abrir otro issue ni PR para esta corrección. El defecto y el arreglo ya existen upstream; `Aether-Agents#209`, creado antes de esta decisión, queda únicamente como traza downstream del bloqueo observado.
- **Archivos activos principales:**
  - `cron/lifecycle_guard.py`
  - `tests/hermes_cli/test_gateway_restart_loop.py`
- **Cambio local:** `stat.S_ISDIR(metadata.st_mode)` devuelve `(None, False)` —nada que escanear— antes del fail-closed general. Dispositivos, sockets, FIFO y scripts reales continúan bloqueándose.
- **Evidencia local y recarga:** RED focal `1 failed` con `exit_code=1`; GREEN focal `1 passed`; suite completa de la guardia `126 passed`; suite cron `710 passed, 1 skipped`; `py_compile`, Ruff y `git diff --check` verdes. La suite cron emitió una advertencia de coroutine no esperada en `hermes_cli/web_server.py`; el test señalado pasó sin advertencia sobre un árbol desechable del `HEAD` base, por lo que no se atribuye a HLP-209 y no se modificó fuera de alcance. El reinicio externo cambió el gateway de PID `1284969` a `1356904`; systemd reportó `active/running`, `Result=success` y `NRestarts=0`. La repetición por la ruta ordinaria de revisión B0 sigue pendiente porque la escalación previa mantiene la tarjeta en `triage` hasta recuperación humana explícita.
- **Upstream:** issue cerrado <https://github.com/NousResearch/hermes-agent/issues/86753>; corrección integrada en `origin/main` mediante commit <https://github.com/NousResearch/hermes-agent/commit/9ac1e65b0ae4e83dced9d5c8a406cc57cb589702>. La revisión upstream inspeccionada `a86569bd1134867e46b49f7cef1988083d7666d8` pasó la sonda equivalente: directorio inocuo permitido, script real de lifecycle y `/dev/null` bloqueados. No se necesita nuevo issue ni PR upstream.
- **Validación runtime pendiente:** la recarga del servicio está verificada; falta recuperar humanamente la escalación de B0, mover la misma tarjeta a `review`, repetir por la ruta ordinaria la validación que originó el falso positivo y confirmar que los controles negativos siguen bloqueados.
- **Gate de retirada:** en una futura revisión de Hermes sin el hunk local, ejecutar la regresión exacta, toda `test_gateway_restart_loop.py` y la sonda runtime post-reinicio; sólo entonces retirar el backport y marcar `RETIRED`.

## Procedimiento obligatorio antes de actualizar Hermes

1. Registrar aquí la versión y commit objetivo; no activar todavía esa revisión.
2. Consultar cada issue/PR upstream de las entradas `ACTIVE_LOCAL`.
3. Comparar comportamiento y hunks contra la revisión objetivo. Un PR fusionado o un número de versión no constituye evidencia suficiente.
4. Preparar la revisión objetivo en un checkout aislado.
5. Ejecutar el gate de retirada de **cada** entrada sin aplicar primero su parche local.
6. Para cada entrada:
   - si la revisión objetivo demuestra equivalencia, marcar `UPSTREAM_VERIFIED`;
   - si no demuestra equivalencia, portar/reaplicar el parche y mantener `ACTIVE_LOCAL`;
   - si upstream cubre sólo una parte —como la recuperación CLI de `HLP-191`— retirar únicamente los hunks equivalentes.
7. Ejecutar compilación, Ruff, `git diff --check` y las suites focalizadas combinadas.
8. Respaldar la instalación activa, cambiar la revisión de forma reversible y reiniciar `hermes-gateway.service`.
9. Repetir las sondas runtime post-reinicio usando bases temporales, nunca el tablero real de Aether para una cualificación destructiva.
10. Actualizar este índice con commit efectivo, resultados, fecha y estado. Sólo entonces marcar una entrada `RETIRED`.

## Hotspot y cambios no clasificados

`hermes_cli/kanban_db.py` contiene hunks de `HLP-188`, `HLP-191`, `HLP-194`, `HLP-198` y `HLP-204`. Nunca debe restaurarse el archivo completo para retirar un único parche; la conciliación debe hacerse por comportamiento y por hunk.

El checkout activo también tiene un cambio en `package-lock.json` generado por metadatos `peer`. No está atribuido a una corrección funcional de este registro. Debe preservarse y reconciliarse separadamente; no debe confundirse con un parche Hermes aceptado ni descartarse durante una actualización.
