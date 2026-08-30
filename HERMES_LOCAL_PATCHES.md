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
| `HLP-211` | `#211` | afinidad opt-in reanuda una sesión worker exacta dentro de un Project/flow/perfil y un workspace canónico, con lease/generation fencing, control Supervisor de blockers y retorno terminal/escalado al origen | Hermes `#75830`, `#59855`, `#68779`, `#71175`; PR `#75951` cubre sólo block→unblock de la misma card; extensión local `HLP-211b` aún sin issue/PR | `ACTIVE_LOCAL + HLP-211b CANDIDATE / UPSTREAM_PARTIAL` |
| `HLP-226` | `#226` | un hijo cross-profile con `workspace_kind=worktree` hereda el Project canónico del worker y recibe worktree propio | commit upstream `b9b5481d6`; PR previo `#89363` | `ACTIVE_LOCAL / UPSTREAM_VERIFIED` |
| `HLP-246` | `#246` | attachments validan identidad pre-transporte y readback; persisten tamaño y SHA-256 calculados | sin equivalente localizado en `origin/main` | `ACTIVE_LOCAL / UPSTREAM_MISSING` |

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
- **Diferencia local adicional:** `hermes kanban unblock --recover-escalated` ya no puede reconocer una escalación mientras la tarjeta siga en `triage`. La recuperación sólo se registra después de que una acción explícita de routing/decomposición la haya movido fuera de `triage`; por tanto, reconocer el bloqueo no autoriza trabajo ni expone la card al auto-decomposer. Esta superficie CLI no aparece en los archivos del PR upstream `#91211` y debe verificarse separadamente al actualizar.
- **Evidencia local:** `19 passed` en las suites focalizadas de CLI, decomposición y watcher, Ruff y `git diff --check` verdes. Una sonda con tres procesos independientes y DB temporal confirmó: `status=triage`, escalación activa, `block_recurrences=2`, ningún evento `triage_escalation_recovered` y `auto_listed=false` después del intento de reconocimiento prematuro.
- **Upstream:** <https://github.com/NousResearch/hermes-agent/pull/91211>, abierto y mergeable, sin checks reportados al conciliar este índice.
- **Gate de retirada:** probar escalación, reconexión, reasignación y tick de auto-descomposición; después probar que una recuperación prematura en `triage` se rechaza y que una recuperación posterior a routing explícito produce el evento durable sin redispatch autónomo. Si upstream no incluye la recuperación CLI equivalente, conservar esa parte local aunque el resto del PR haya sido integrado.

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

## HLP-211 — continuidad de sesión worker por flujo y HLP-211b blocker routing

- **Motivo:** cada card Supervisor abría una sesión nueva; descomposición, review e integración perdían historial y prompt cache aun perteneciendo al mismo Objective Contract. La corrección mantiene una sesión lógica por `(board, Project, flow_id, perfil)` y un único workspace Supervisor canónico por flujo; los Implementers conservan sesiones/worktrees independientes. La reproducción del 2026-08-29 añadió el hueco HLP-211b: un Implementer bloqueado podía emitir `origin_signal` sin ninguna suscripción originaria, saltarse Supervisor y dejar el flow detenido hasta el próximo mensaje del owner.
- **Archivos activos principales:**
  - `hermes_cli/kanban_affinity.py`
  - `hermes_cli/kanban_db.py`
  - `hermes_cli/kanban.py`
  - `hermes_cli/main.py`
  - `run_agent.py`
  - `tui_gateway/server.py`
  - `tools/kanban_tools.py`
  - `gateway/kanban_watchers.py`
  - `tests/hermes_cli/test_kanban_session_affinity.py`
- **Semántica local:** `session_affinity={flow_id, terminal}` es opt-in; sólo cards del mismo Project, perfil, flow y workspace pueden compartir sesión. El dispatcher reserva una lease generacional antes del spawn, registra la sesión real, usa `--resume --no-restore-cwd --in <workspace>` en procesos posteriores y rechaza leases/sesiones/workspaces obsoletos. Un hijo same-profile hereda flow y workspace; hijos cross-profile no heredan sesión. HLP-211b conserva una suscripción originaria silenciosa en la raíz; un blocker real de un parent despierta la única card terminal affinity hija mediante `flow_attention`; esa card puede resolver y volver a `dependency` (Hermes reanuda el parent), o escalar con `origin_signal="recovery"`. Sólo `origin_signal` (`input|revision|recovery`) y `flow_terminal` cruzan al origen; hitos internos siguen silenciosos. Grafos ambiguos fallan cerrado a la ruta legacy.
- **Hunks HLP-211b exactos (checkout activo previo `0b288979e`, upstream inspeccionado `105b8650`):** `hermes_cli/kanban_db.py`: línea 114 amplía `VALID_ORIGIN_SIGNALS`; líneas 5384–5514 añaden `_pending_flow_attentions`, `_wake_terminal_flow_controller` y `_resolve_flow_attention`; línea 7224 resuelve/reanuda el parent cuando el controller vuelve a `dependency`; líneas 7274 y 7344 conectan blockers normales y escalados al controller; línea 11883 y bloque siguiente inyectan el protocolo en `build_worker_context`; el claim conserva parent gating salvo attention pendiente. `tools/kanban_tools.py`: línea 1672 conserva auto-subscription en raíces affinity no terminales; líneas 2040 y 2050 exponen `recovery`. Tests: `tests/hermes_cli/test_kanban_session_affinity.py` líneas 579–713 y `tests/tools/test_kanban_tools.py` desde línea 1151.
- **Tamaño HLP-211b exacto contra el backup previo:** producción: `hermes_cli/kanban_db.py` `+180/-7`, `tools/kanban_tools.py` `+6/-4` (**186 añadidas / 11 retiradas; neto +175**). Tests: `tests/hermes_cli/test_kanban_session_affinity.py` `+137/-0` y un test de auto-subscription no terminal de `+40/-0` en `tests/tools/test_kanban_tools.py`. No se reformatearon hotspots ni se atribuyeron otros cambios locales al parche.
- **Aether:** `prepare_handoff` deriva un `flow_id` determinista; Morfeo lo pasa a la raíz Supervisor, y la review/integración terminal conserva la misma affinity/workspace. La política específica permanece en Aether, no en Hermes core.
- **Evidencia local:** HLP-211 base tenía `114 passed, 1 skipped`; E2E-16 probó reutilización exacta de sesión/workspace. HLP-211b registra RED previo (`flow_attention` ausente y `recovery` rechazado) y GREEN: `6 passed, 70 deselected` focalizados; suites afectadas `117 passed, 1 skipped`; Ruff check sin errores. Tras reiniciar el gateway de PID `877` a `181495`, una sonda en proceso/SQLite/Project desechables produjo `PASS`: unidad bloqueada → terminal controller `ready` → contexto `flow_attention` → mismo controller reclamable → `dependency` reanudó la unidad y devolvió controller a `todo`. La corrida live E2E-15 `e2e-15-20260829-200042-6466bb1c` con Sol/Terra fue **inconclusa para HLP-211b**: Morfeo one-shot hizo polling hasta el timeout fijo de 900 s (`rc=124`); entretanto raíz Supervisor y dos Implementers terminaron y la terminal Supervisor inició, pero el cleanup la interrumpió. No hubo blocker/`flow_attention`; confirma que la lane actual no crea el Morfeo persistente que pretende medir y no se atribuye el fallo al parche.
- **Backup HLP-211b:** `.aether/backups/hlp248-flow-blocker-routing-20260829T193117-0600`; `SHA256SUMS` conserva los cuatro archivos previos y `LEDGER.sha256` el ledger previo.
- **Upstream:** <https://github.com/NousResearch/hermes-agent/pull/75951> reanuda sólo la misma card después de block→unblock y no cubre afinidad multi-card, Project/workspace, fencing generacional ni routing terminal. Issues relacionados: `#59855`, `#68779`, `#71175`.
- **Estado de activación:** HLP-211/HLP-211b `ACTIVE_LOCAL_KERNEL_QUALIFIED`. Gateway Morfeo reiniciado el 2026-08-29 19:44 CST a PID `181495`; sonda post-reinicio verde. La guardia negó editar `SOUL.md` pese a autorización explícita; no se rodeó. `build_worker_context` inyecta el protocolo de controller, por lo que la corrección runtime no depende de prompts. La edición documental de SOUL y el canary conversacional TUI quedan pendientes de una superficie autorizada/turno separado; el kernel no se declara E2E completo hasta esa prueba.
- **Gate de retirada:** sobre una revisión upstream objetivo sin HLP-211/HLP-211b, ejecutar E2E-16 y el canary blocker completo: misma sesión entre raíz/recovery/review/integración, Implementer fresco, `dependency` silencioso, una sola attention por blocker, parent reanudado, `recovery` despertando Morfeo sin owner adicional, aislamiento y entrega exclusiva de `input|revision|recovery|flow_terminal`. Retirar sólo hunks equivalentes; la política Aether no se retira con Hermes.

## HLP-226 — herencia canónica de Project en hijos worktree

- **Motivo:** `kanban_create` desactivaba la herencia de Project cuando el worker pedía explícitamente `workspace_kind="worktree"`; el hijo quedaba con `project_id=null` y `workspace_path=null` y no podía ejecutarse.
- **Archivos activos principales:**
  - `tools/kanban_tools.py`
  - `hermes_cli/kanban_db.py`
  - `tests/tools/test_kanban_tools.py`
- **Cambio local:** cuando no existe `workspace_path` literal, el handler transmite la card worker como fuente canónica. Si el perfil creador no tiene el Project en su `projects.db`, `create_task` deriva repositorio y convención de rama desde esa card compartida, conserva el UUID y crea una ruta propia; un Project explícito diferente se rechaza.
- **Evidencia:** regresión upstream cross-profile portada y verde; suite focalizada herramienta + Projects `52 passed`; Ruff y `git diff --check` verdes. E2E de tres procesos/perfiles con board compartido y `projects.db` de Supervisor vacío (`0` Projects): Morfeo creó padre `t_455b8352`, Supervisor creó hijo `t_4d5f1488` con `project_id=p_1766de25`, ruta propia y rama determinista; `_resolve_worktree_workspace` materializó un worktree Git real en esa ruta y `git branch --show-current` coincidió exactamente.
- **Upstream:** corrección integrada en `origin/main` mediante commit <https://github.com/NousResearch/hermes-agent/commit/b9b5481d6236edb3ec8aae32cc4b5c661569b872>; el PR previo <https://github.com/NousResearch/hermes-agent/pull/89363> permanece abierto, pero ya no es el gate de retirada.
- **Estado de activación:** `ACTIVE_LOCAL / UPSTREAM_VERIFIED`; el checkout editable cargado conserva la corrección y cada worker nuevo la importa por proceso. No requiere reinicio del gateway.
- **Gate de retirada:** al actualizar al upstream que contiene `b9b5481d6`, repetir la regresión cross-profile y el E2E con registro de Projects vacío; retirar el hunk local sólo si el hijo conserva UUID, worktree y rama, materializa el checkout real y un Project conflictivo sigue rechazado.

## HLP-246 — identidad verificable de attachments Kanban

- **Motivo:** el attachment `qualification-failure-evidence-v2.tar.gz` llegó al write path ya truncado pero con base64 válido; DB y disco conservaron los mismos `8699` bytes corruptos y el sistema devolvió éxito porque sólo validaba sintaxis base64 y tamaño local.
- **Archivos activos principales:**
  - `hermes_cli/kanban_db.py`
  - `hermes_cli/kanban.py`
  - `tools/kanban_tools.py`
  - `plugins/kanban/dashboard/plugin_api.py`
  - `tests/plugins/test_kanban_attachments.py`
  - `tests/tools/test_kanban_tools.py`
- **Cambio local:** `kanban_attach` exige tamaño y SHA-256 calculados antes de base64, los compara con los bytes decodificados y rechaza cualquier mismatch antes de escribir. El kernel relee toda escritura, verifica tamaño/hash y sólo entonces inserta la fila. CLI, URL y dashboard calculan la identidad en servidor; listados/contexto exponen el SHA. La migración añade `sha256` nullable y deja attachments legacy en `NULL` para no certificar retroactivamente bytes posiblemente corruptos.
- **Evidencia:** RED focal `5 failed`; GREEN focal `5 passed`; suites completas relacionadas `93 passed, 1 skipped`; Ruff y `git diff --check` verdes. E2E de tres procesos con tar.gz real de `14191` bytes: tamaño esperado/DB/disco idénticos, SHA-256 `df5a060e1840aa77a61fdbb8f721cce810e6db48a8faa92e30bff76ac3cfe90d` idéntico en emisor/respuesta/DB/readback y archivo abierto con el miembro esperado. El v2 original completo ya no existe; el único archivo hallado es el corrupto y permanece `sha256=NULL`/no verificado.
- **Upstream:** no se encontró equivalente en `origin/main` ni issue/PR por búsqueda de attachments truncados, checksum o SHA-256.
- **Estado de activación:** `ACTIVE_LOCAL`; CLI y nuevos workers cargan la corrección por proceso. Procesos/TUI ya vivos conservan su schema de tool anterior hasta una sesión nueva; no se reinicia esta TUI para no destruir la conversación activa.
- **Gate de retirada:** sobre una revisión upstream objetivo, exigir claims pre-transporte para inline base64, identidad server-computed persistida y retornada, rechazo de escritura parcial, migración legacy no certificante y E2E tar.gz byte-for-byte antes de retirar el parche.

## HLP-247 — un padre archivado no es un padre completado

- **Motivo:** `recompute_ready` trataba `archived` como equivalente a `done` en la puerta de dependencias. Al archivar un padre, un hijo en `blocked` cuyo bloqueo precede al evento `blocked{initial:true}` (2026-08-20) no es visible para `_has_sticky_block`, se promovía a `ready` dentro de `archive_task` y el dispatcher lo despachaba sin ningún `unblock`. Observado en real: limpiar el tablero relanzó `t_b02bdbad`, bloqueada desde el 2026-08-18, que llegó a ejecutar trabajo contra un contrato obsoleto.
- **Archivos activos principales:**
  - `hermes_cli/kanban_db.py`
  - `tests/hermes_cli/test_kanban_blocked_sticky.py`
- **Cambio local:** en `recompute_ready`, las tareas en `blocked` exigen padres `done`; las tareas en `todo` conservan la puerta histórica `(done, archived)`. Una sola condición; no toca stickiness, circuit breaker ni migración de datos.
- **Evidencia:** RED `1 failed, 8 passed` (falla exactamente `assert 'ready' == 'blocked'` al archivar); GREEN `9 passed`; reproducción aislada `/tmp/repro_blocked_promotion.py` deja de reproducir.
- **Upstream:** `NousResearch/hermes-agent@main` verificado **no corregido** (mismo gate `("done","archived")`, mismo `_has_sticky_block`, `archive_task` sigue llamando a `recompute_ready`). Aether #247. Sin PR upstream todavía.
- **Estado de activación:** `ACTIVE_LOCAL`.
- **Gate de retirada:** sobre una revisión upstream objetivo sin este hunk, repetir las tres regresiones; retirar sólo si el hijo `blocked` sigue bloqueado al archivar el padre, el hijo `todo` sí se libera y el hijo no-sticky con padre `done` sí se promueve.

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
