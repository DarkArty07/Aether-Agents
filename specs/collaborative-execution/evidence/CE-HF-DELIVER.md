# Implementation Evidence — Unit CE-HF-DELIVER

**Status:** Candidate implemented and locally verified; ready for same-card Supervisor review.
This is unit evidence, not integrated project acceptance, release evidence, or live
messaging qualification.

- **Unit ID:** `CE-HF-DELIVER`
- **Task ID:** `t_8edf43f3`
- **Issue:** [#334](https://github.com/DarkArty07/Aether-Agents/issues/334)
- **Objective Contract:** `oc_a28ff9b7fa20d29d@v1` (SHA-256
  `7a51dc2b3d2d62788b1228f823f9def58652e48d48fcecaecb5293f34dde7de5`)
- **Review lane:** Same-card Supervisor review (`reviewer="supervisor"`)
- **Unit compatibility impact:** `minor` (optional collaboration delivery is
  additive; the legacy terminal-notification cursor and ordinary delivery path
  remain intact)

## 1. Repository identity, prerequisites and scope

| Tree | Observed identity | Evidence |
| --- | --- | --- |
| Aether contract/base | `183bd7a4944a5db7d22091c402a74383a80100fa` | Task/decomposition input; no Aether production files changed |
| Maintained fork base | `DarkArty07/aether-hermes` `3b81e9d91cc3a0662b910726a44c94ed328b1e90` | Verified before the nested fork was created |
| Reviewed CORE parent | `20db06c0b8441190830aa72e3c0de6fdce6b8db4` | Parent handoff; actual reviewed helpers were inspected before editing |
| DELIVER candidate | `3b569a345b2c4ba94d20b9216234d8f897e6b281` | Local commit on isolated fork branch `feat/334-deliver-tui-gateway` |
| `gateway/kanban_watchers.py` at candidate | `1f91ac1130777a8c8043f4a544da5a9ad9c59f94888e7ed7903c0598a768667f` | SHA-256 measured after the final local commit |
| `tui_gateway/server.py` at candidate | `001f88d0e95632c475d8dd2689610ba5c0f54a6bdc557c7e2a967b2e32dc162c` | SHA-256 measured after the final local commit |
| Baseline target hashes | `gateway/kanban_watchers.py` `755091a353cc3e6a9928e2eee016aa3a2b74b95e690282aa59df442850a10f5d`; `tui_gateway/server.py` `39d2e7a3c04e5810a803c8023719fb72b02c842122ba242553d37276b9a6e096` | Both matched before mutation and matched the CORE tip before this unit began |
| CORE consume API | `claim_collaboration_messages`, `get_collaboration_message`, `advance_collaboration_message`, `get_collaboration_root` | Inspected in the reviewed CORE candidate; no second table/cursor was added |

Writable fork files were limited to `gateway/kanban_watchers.py`,
`tui_gateway/server.py`, `tests/gateway/test_kanban_collaboration_delivery.py`,
and `tests/tui_gateway/test_kanban_collaboration_poller.py`. `hermes_cli/kanban_db.py`,
`tools/kanban_tools.py`, `AETHER_FORK.md`, the Aether runtime, `home/`, and unrelated
TUI/gateway features were not changed. No push, PR, merge, issue mutation, activation,
Telegram Monitor action, live Telegram call, or paid model call was performed.

The project-knowledge status action returned `available=false` with source revision
`183bd7a4944a5db7d22091c402a74383a80100fa`; direct source inspection and tests were
used instead. No knowledge graph claim is used as acceptance evidence.

## 2. Implementation and local technical judgement

1. **Gateway consumer (`gateway/kanban_watchers.py:167-240, 703-799, 879-882`).**
   The existing notifier tick discovers pending origin collaboration through CORE's
   `list_pending_collaboration` and `claim_collaboration_messages` APIs. It resolves
   each message on the current board to the root's own notification subscription,
   checks route identity (platform/chat/thread/chat type/profile/metadata), and refuses
   ambiguous, missing, inactive, or cross-profile routes rather than rerouting. It never
   calls `advance_notify_cursor` for collaboration.
2. **Gateway delivery (`gateway/kanban_watchers.py:274-428`).** A claimed collaboration
   message is delivered through the existing `gateway.wake.deliver_wake` path only;
   `adapter.send()` is not called for the collaboration branch. Push adapters receive a
   `SessionSource` reconstructed from the exact subscription, including chat type,
   thread, user, profile and scope. The stateless API-server path receives the raw
   subscription chat/session id. A busy-session probe fences delivery, push adapters
   retain their native active-session queue, and failed/busy/disconnected delivery
   rewinds only the matching lease to `pending`. Acknowledgment is not inferred from
   enqueue; the CORE row remains `queued` until the native recipient explicitly
   acknowledges/responds.
3. **Peer evidence formatting (`gateway/kanban_watchers.py:167-240`; `tui_gateway/server.py:9739-9816`).**
   Source role is taken from the trusted source comment/event payload when available,
   with task provenance as fallback. The native block carries collaboration/task/root,
   board and source references, explicitly says it is informative peer evidence, and
   forbids owner-authority promotion. Gateway text directs the model to use native
   ack/respond and to return `NO_REPLY` when no owner-facing decision/status is needed;
   the block is not passed through the operator/out-of-band wrapper.
4. **TUI consumer (`tui_gateway/server.py:9817-9941, 10015-10043`).** The TUI poller
   has a separate collaboration collector using CORE's claim API and the root's exact
   `platform="tui"`, `chat_id=session_key` route. It requires the root subscription,
   rejects missing/ambiguous routes, and leaves the terminal cursor untouched. Claimed
   text is retained in the existing same-session pending buffer, never emits a
   collaboration `status.update` passive ping, and starts a turn only after the
   existing `history_lock` observes the session idle. The durable row remains queued
   until explicit consumption; an expired lease can be claimed again.
5. **Legacy compatibility guard (`tui_gateway/server.py:9834-9847`; gateway collection
   guard at `gateway/kanban_watchers.py:663-670`).** Pre-consumer runtimes without the
   reviewed CORE helpers return no collaboration work while retaining the legacy
   terminal poller. No collaboration branch was added to the terminal cursor path.

The local choices above preserve the stamped D4-D5 interface: one adjunct store, one
independent collaboration claim/lease path, exact origin routing, no passive ping per
internal exchange, same-session continuation, no parallel Supervisor, and no parent
unblock from an advisory message.

## 3. Requirement-to-evidence coverage

| Obligation | Check and observed result | Evidence |
| --- | --- | --- |
| CE-03: proactive/origin evidence reaches the exact origin | Gateway and TUI focused fixtures create CORE lifecycle/request rows, claim them via the reviewed API, and assert the formatted peer block contains source role, task/root and summary. | `tests/gateway/test_kanban_collaboration_delivery.py::test_gateway_collaboration_delivery_wakes_origin_without_passive_ping`; `tests/tui_gateway/test_kanban_collaboration_poller.py::test_collect_kanban_collaboration_claims_and_formats_peer_block` — PASS |
| CE-06: independent cursor and no passive human ping | Both focused tests assert the legacy subscription `last_event_id` is unchanged. Gateway asserts `adapter.send()` is empty and only `deliver_wake` is called; TUI asserts zero `status.update` events for collaboration. | Gateway first test and TUI `test_poller_loop_dispatches_collaboration_without_passive_status_update` — PASS |
| CE-06: exact gateway chat/thread/API session | Gateway controlled sink verifies `SessionSource.chat_id` and `thread_id`; API-server fixture verifies `deliver_wake(session_id=raw subscription id, source=None)`. | `test_gateway_collaboration_delivery_wakes_origin_without_passive_ping`; `test_gateway_api_server_collaboration_uses_exact_session_without_ping` — PASS |
| CE-06: exact TUI origin and no reroute | Mismatched/finalized TUI sessions return no item and preserve the pending row; missing root route in the gateway leaves the row pending despite an inherited child route. | TUI `test_finalized_or_mismatched_origin_never_reroutes`; gateway `test_gateway_missing_root_route_is_not_rerouted_to_child` — PASS |
| CE-06: separate boards | Two disposable boards use the same chat key; only the board-A row is claimed and delivered, and board-B root identity is absent from the delivered text. | `test_gateway_separate_boards_never_cross_deliver`; TUI `test_two_origins_separate_boards_never_receive_each_others_notices` — PASS |
| CE-06/CE-07: busy sessions do not run concurrently | Gateway busy fixture rewinds a claimed row to `pending`, then delivers once idle. TUI busy fixture observes no turn while running and flushes its existing pending buffer after the lock-protected idle transition. | Gateway `test_gateway_busy_session_defers_wake_and_delivers_when_idle`; TUI `test_busy_session_does_not_run_concurrently` — PASS |
| Preservation: ordinary terminal notifications | Mixed fixture asserts a normal terminal event still uses `adapter.send()` while the separate collaboration row uses internal wake. Existing baseline and candidate notifier/TUI suites pass. | `test_gateway_terminal_and_collaboration_coexist`; candidate regression below — PASS |
| Preservation: no duplicate Supervisor / parent mutation | DELIVER handles only `recipient_kind="origin"`; controller records are not spawned or unblocked here. CORE's reviewed controller advisory tests remain green. | Candidate CORE suites `102 passed`; reviewed parent handoff `CE-HF-CORE.md` — PASS/reused |

Controlled sinks prove only the measured mechanical consumer branches. They do not prove
long-term LLM collaboration efficacy, provider delivery, or live gateway qualification.

## 4. Verification receipts

### Pre-consumer fail-first / preservation baseline

The unchanged fork `3b81e9d91cc3a0662b910726a44c94ed328b1e90` was run with temporary
`HERMES_HOME` and all inherited kanban DB/board/task/run/workspace selectors unset:

```text
pre-consumer 3b81e9d: no collaboration consumer symbols; no wake path available
HERMES_TEST_FILE_RETRIES=0 python -m pytest -q \
  tests/gateway/test_kanban_watchers_mixin.py \
  tests/test_tui_gateway_server.py \
  tests/tui_gateway/test_kanban_notify_poller.py
592 passed in 30.96s
```

The baseline therefore has no collaboration wake path, while its existing TUI/gateway
terminal-notification behavior passes unchanged. The new candidate-focused tests are
causal tests for the CORE-dependent behavior and are not expected to run as positive
consumer tests on this pre-consumer commit.

### Candidate focused and required suites

Candidate interpreter: fork worktree `.venv/bin/python` created by
`uv sync --extra dev --frozen`; Python 3.11.15; `HERMES_TEST_FILE_RETRIES=0`.
The final required command was:

```text
HERMES_TEST_FILE_RETRIES=0 python -m pytest -q \
  tests/gateway/test_kanban_watchers_mixin.py \
  tests/test_tui_gateway_server.py \
  tests/tui_gateway/test_kanban_notify_poller.py \
  tests/gateway/test_kanban_collaboration_delivery.py \
  tests/tui_gateway/test_kanban_collaboration_poller.py
605 passed in 31.74s
```

The candidate-only focused consumer run was:

```text
HERMES_TEST_FILE_RETRIES=0 python -m pytest -q \
  tests/gateway/test_kanban_collaboration_delivery.py \
  tests/tui_gateway/test_kanban_collaboration_poller.py
13 passed in 3.26s
```

The reviewed CORE candidate suites were also executed from this candidate import
context:

```text
HERMES_TEST_FILE_RETRIES=0 python -m pytest -q \
  tests/hermes_cli/test_kanban_collaboration.py \
  tests/tools/test_kanban_collaboration.py \
  tests/tools/test_kanban_tools.py \
  tests/hermes_cli/test_kanban_session_affinity.py
102 passed in 8.99s
```

Static checks on the committed fork candidate:

```text
ruff check gateway/kanban_watchers.py tui_gateway/server.py \
  tests/gateway/test_kanban_collaboration_delivery.py \
  tests/tui_gateway/test_kanban_collaboration_poller.py
All checks passed!

ruff format --check tests/gateway/test_kanban_collaboration_delivery.py \
  tests/tui_gateway/test_kanban_collaboration_poller.py
2 files already formatted

git diff --check
exit code 0
```

The pre-existing fork files contain unrelated formatting drift, so the production
files were checked with Ruff rather than reformatted wholesale. No source-level
formatting changes outside this unit were made.

## 5. Isolation incident and live-board preservation

A first diagnostic native-writer probe in this task process redirected only
`HERMES_KANBAN_HOME` while inherited `HERMES_KANBAN_DB`/`HERMES_KANBAN_BOARD` still
pointed at the active objective board. It created the live cards `t_ebd28f85` and
`t_c46db090` and observed existing live collaboration rows. This was an isolation
incident, not contract work. The cards and rows are preserved; no SQL deletion,
cleanup, or counting of those cards as acceptance occurred. Aether issue #267 was
reopened with sanitized evidence by the operator.

The corrective probe unset `HERMES_KANBAN_DB`, `HERMES_KANBAN_BOARD`,
`HERMES_KANBAN_TASK`, `HERMES_KANBAN_RUN_ID`, and
`HERMES_KANBAN_WORKSPACES_ROOT`, then asserted the resolved DB path was under its
unique disposable root before any native writer. The new consumer fixtures apply the
same boundary and assert each board path in `_isolated_connect` before calling
`connect()`; no live board is used by the candidate tests.

Read-only live-board fingerprints around the final required regression were:

```text
before final regression: tasks=18/max=18, task_events=409/max=409,
  task_comments=15/max=15, kanban_notify_subs=4/max=4,
  kanban_collaboration=3/max=3
final regression: 605 passed in 31.74s
after final regression: tasks=18/max=18, task_events=410/max=410,
  task_comments=15/max=15, kanban_notify_subs=4/max=4,
  kanban_collaboration=3/max=3
new task_events after checkpoint: heartbeat=1
```

The only live-board event delta during the final test interval was one operational
`heartbeat` for this still-running task (run 22); there were no new task, comment,
subscription, or collaboration rows. Earlier read-only checks likewise found the
additional event deltas to be only `heartbeat` events for run 22. This is reported
explicitly rather than presented as a zero-event claim. The live incident cards and
pre-existing rows remain untouched.

## 6. Shared decisions stamped from `tasks.md`

1. Authority is Objective Contract `oc_a28ff9b7fa20d29d@v1`, digest
   `7a51dc2b3d2d62788b1228f823f9def58652e48d48fcecaecb5293f34dde7de5`; skills grant
   no authority and the contract was not edited.
2. Aether evidence starts from `183bd7a4944a5db7d22091c402a74383a80100fa`; fork
   edits use an isolated nested worktree from `3b81e9d91cc3a0662b910726a44c94ed328b1e90`;
   live runtime, `aether-main`, and `home/` were not edited.
3. DELIVER target hashes matched the stamped base before mutation; candidate hashes
   are recorded in section 1.
4. Existing native signatures and CORE's reviewed adjunct API were reused; no second
   table, comment writer, or terminal cursor was introduced.
5. One `kanban_collaboration` table and distinct claim/list/advance lease path are
   consumed. Wake/steer is only queued; explicit ack/respond is consumption. Origin
   delivery is internal wake-only and peer text is a labeled native evidence block.
6. Proactive notices are CORE-owned on the specified lifecycle events and coalesced
   there; DELIVER only routes the resulting records and does not add a heartbeat/tool
   wake loop.
7. Terminal flow/archive and parent-gating semantics remain CORE-owned; DELIVER never
   unblocks an unrelated parent or starts another Supervisor.
8. No Graphify, lockfile, live profile, credential, provider/model, dispatcher setting,
   repository Actions, Telegram Monitor, or observer repair was added.
9. Tests use disposable scrubbed state, asserted temporary paths, baseline RED/no-wake
   evidence, candidate GREEN suites, Ruff and `git diff --check`; no live board,
   Telegram, paid model, or credential fixture was used.
10. Exclusive writable ownership was respected: only the two consumer production files,
    two focused test modules and this unique Aether evidence file were touched.
11. Neither `HERMES_LOCAL_PATCHES.md` nor fork `AETHER_FORK.md` was edited; the exact
    ledger paragraph below is handed to CE-INT.
12. Evidence path is the unique `specs/collaborative-execution/evidence/CE-HF-DELIVER.md`.
13. Local judgement covered fixture sinks, route-key factoring and use of CORE's
    reviewed helpers; public D4-D5 semantics were not varied.
14. The isolation incident was recorded and preserved; no further live contract rows
    were written by the regression, and no cross-unit collision was absorbed.
15. The fork candidate is committed locally and this unit requests same-card Supervisor
    review; compatibility is `minor`; no publication or issue close was performed.
16. The objective remains optional/off for generic and historical flows; no retroactive
    enablement or stopped-monitor restart was performed.
17. GitHub issue #334 remains open for CE-INT closeout; this unit did not close it.

## 7. Exact ledger paragraph for CE-INT

```markdown
### HLP-334: TUI and gateway collaboration consumers
- **Status:** Candidate implemented in maintained fork at commit `3b569a345b2c4ba94d20b9216234d8f897e6b281`.
- **Issue:** [Aether #334](https://github.com/DarkArty07/Aether-Agents/issues/334).
- **Objective Contract:** `oc_a28ff9b7fa20d29d@v1` (SHA-256 `7a51dc2b3d2d62788b1228f823f9def58652e48d48fcecaecb5293f34dde7de5`).
- **Files touched:** `gateway/kanban_watchers.py`, `tui_gateway/server.py`, `tests/gateway/test_kanban_collaboration_delivery.py`, `tests/tui_gateway/test_kanban_collaboration_poller.py`.
- **Scope & Behavior:** Adds maintained-fork gateway and TUI consumers for CORE's `kanban_collaboration` adjunct. Each consumer claims collaboration records through the distinct bounded lease API rather than `advance_notify_cursor`, routes only to the exact root subscription/session/chat/thread on its board, fences busy sessions, keeps queued work durable until explicit consumption, labels peer evidence as non-owner advice, emits no passive human ping for internal collaboration, preserves ordinary terminal notifications, and leaves missing/ambiguous/closed origins unavailable instead of rerouting.
- **Upstream Relationship:** Downstream enhancement to Hermes Agent kanban coordination; consumes the reviewed CORE native collaboration store/tool surface without adding a second bus or changing legacy notification semantics.
- **Rollback:** Restore `gateway/kanban_watchers.py` and `tui_gateway/server.py` from the reviewed CORE parent commit `20db06c0b8441190830aa72e3c0de6fdce6b8db4`; the additive CORE schema/history remains intact and no down-migration is required for this consumer-only unit.
- **Maintenance / Retirement:** Retain while Aether contracts use active multi-role collaboration; retire the consumer delta when the native collaboration contract is retired or an equivalent upstream Hermes capability passes its behavior gate.
```

## 8. Remaining limits and handoff

- Fake adapter/TUI sinks establish only the measured local delivery branches. No live
  Telegram, gateway, model, or long-term behavioral efficacy claim was made.
- The candidate requires the reviewed CORE parent at `20db06c...`; the pre-consumer
  baseline intentionally has no positive collaboration API.
- Integration, dual-repository publication, runtime adoption/readback, rollback
  qualification, residue reconciliation and aggregate release conclusions belong to
  CE-INT. Provisional unit compatibility is `minor`; this unit does not decide the
  aggregate release action (`defer` / `none`).
