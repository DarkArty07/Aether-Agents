# Implementation Evidence — Unit CE-HF-DELIVER

**Status:** Round-3 corrections implemented and locally verified; ready for same-card
Supervisor re-review. This is unit evidence, not integrated project acceptance, release
evidence, or live messaging qualification.

- **Unit ID:** `CE-HF-DELIVER`
- **Task ID:** `t_8edf43f3`
- **Issue:** [#334](https://github.com/DarkArty07/Aether-Agents/issues/334)
- **Objective Contract:** `oc_a28ff9b7fa20d29d@v1` (SHA-256
  `7a51dc2b3d2d62788b1228f823f9def58652e48d48fcecaecb5293f34dde7de5`)
- **Review lane:** Same-card Supervisor review (`reviewer="supervisor"`)
- **Unit compatibility impact:** `minor` (optional collaboration delivery is additive;
  the legacy terminal-notification cursor and ordinary delivery path remain intact)
- **Round-1 review:** `changes_requested` on `3b569a345b` (two CE-06/D3/D5 defects);
  both corrected in `4942a7cfa3`.
- **Round-2 review:** `changes_requested` on `4942a7cfa3` (exclusive CORE claim + skip-after-claim
  starved concurrent still-live consumers watching the same opted-in root); corrected in `d1d1f9e9f4`.

## 1. Repository identity, prerequisites and scope

| Tree | Observed identity | Evidence |
| --- | --- | --- |
| Aether contract/base | `183bd7a4944a5db7d22091c402a74383a80100fa` | Task/decomposition input; no Aether production files changed |
| Maintained fork base | `DarkArty07/aether-hermes` `3b81e9d91cc3a0662b910726a44c94ed328b1e90` | Re-verified; baseline worktree created from this exact commit |
| Reviewed CORE parent | `20db06c0b8441190830aa72e3c0de6fdce6b8db4` | Parent handoff; actual reviewed helpers inspected before editing |
| Round-1 candidate (superseded) | `3b569a345b2c4ba94d20b9216234d8f897e6b281` | Review target that received round-1 `changes_requested` |
| Round-2 candidate (superseded) | `4942a7cfa304cc5e240adea07779a0be18299bd1` | Review target that received round-2 `changes_requested` |
| **DELIVER candidate** | `d1d1f9e9f4eb8fc5998a44274c5d5e16541f6e24` | Local commit on isolated fork branch `feat/334-deliver-tui-gateway` |
| `gateway/kanban_watchers.py` @ candidate | `3350441f69cd881ad5c5ac4ae333d366ba7a1189c227679812c6faafcc4fbf31` | `git show d1d1f9e9f4:gateway/kanban_watchers.py \| sha256sum`; equals the clean worktree file |
| `tui_gateway/server.py` @ candidate | `140824eadf8a676fc6ecbdc405cff7a432904330945fa636e0d869a1def8bfa0` | `git show d1d1f9e9f4:tui_gateway/server.py \| sha256sum`; equals the clean worktree file |
| Baseline target hashes | `gateway/kanban_watchers.py` `755091a353cc3e6a9928e2eee016aa3a2b74b95e690282aa59df442850a10f5d`; `tui_gateway/server.py` `39d2e7a3c04e5810a803c8023719fb72b02c842122ba242553d37276b9a6e096` | Both matched before mutation and matched the CORE tip before this unit began; unchanged by this unit |
| CORE consume API | `list_pending_collaboration`, `claim_collaboration_messages`, `get_collaboration_message`, `advance_collaboration_message`, `get_collaboration_root` | Inspected in the reviewed CORE candidate; no second table/cursor was added |

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

1. **Gateway consumer (`gateway/kanban_watchers.py:174-265, 765-888, 955-958`).**
   The existing notifier tick discovers pending origin collaboration through CORE's
   `list_pending_collaboration` and `claim_collaboration_messages` APIs. It resolves
   each message on the current board to the root's own notification subscription,
   checks route identity (platform/chat/thread/chat type/profile/metadata), and refuses
   ambiguous, missing, inactive, or cross-profile routes rather than rerouting. It never
   calls `advance_notify_cursor` for collaboration.
2. **Gateway delivery (`gateway/kanban_watchers.py:400-518`).** A claimed collaboration
   message is delivered through the existing `gateway.wake.deliver_wake` path only;
   `adapter.send()` is not called for the collaboration branch. Push adapters receive a
   `SessionSource` reconstructed from the exact subscription, including chat type,
   thread, user, profile and scope. The stateless API-server path receives the raw
   subscription chat/session id. A busy-session probe fences delivery, push adapters
   retain their native active-session queue, and failed/busy/disconnected delivery
   rewinds only the matching lease to `pending`. Acknowledgment is not inferred from
   enqueue; the CORE row remains `queued` until the native recipient explicitly
   acknowledges/responds.
3. **Peer evidence formatting (`gateway/kanban_watchers.py:174-265`; `tui_gateway/server.py:9751-9826`).**
   Source role is taken from the trusted source comment/event payload when available,
   with task provenance as fallback. The native block carries collaboration/task/root,
   board and source references, explicitly says it is informative peer evidence, and
   forbids owner-authority promotion. Gateway text directs the model to use native
   ack/respond and to return `NO_REPLY` when no owner-facing decision/status is needed;
   the block is not passed through the operator/out-of-band wrapper.
4. **TUI consumer (`tui_gateway/server.py:9850-9978, 10058-10092`).** The TUI poller
   has a separate collaboration collector using CORE's claim API and the root's exact
   `platform="tui"`, `chat_id=session_key` route. It requires the root subscription,
   rejects missing/ambiguous routes, and leaves the terminal cursor untouched. Claimed
   text is retained in the existing same-session pending buffer, never emits a
   collaboration `status.update` passive ping, and starts a turn only after the
   existing `history_lock` observes the session idle. The durable row remains queued
   until explicit consumption.
5. **Legacy compatibility guard (`tui_gateway/server.py:9866-9878`; gateway collection
   guard at `gateway/kanban_watchers.py:771`).** Pre-consumer runtimes without the
   reviewed CORE helpers return no collaboration work while retaining the legacy
   terminal poller. No collaboration branch was added to the terminal cursor path.

### Round-2 corrections (both defects from the round-1 review)

6. **Origin-route uniqueness scoped to platforms this consumer can deliver to
   (`gateway/kanban_watchers.py:794-836`).** Round 1 computed the ambiguity check over
   *every* notify subscription on the root, so a `tui` session subscription (a platform
   the gateway has no adapter for — the `tui_gateway` process owns those sessions) made a
   unique telegram origin look ambiguous and left the record `pending` with zero wakes.
   Uniqueness is now computed over the root's subscriptions whose platform is in
   `active_platforms` (the platforms this gateway actually hosts, already resolved earlier
   in the tick), and the deliverable route is selected from the notifier-profile
   subscriptions restricted to those same reachable platforms. Consequences: a `tui`
   subscription no longer blocks or is blocked by a telegram origin (the TUI collector
   already scoped itself to `platform="tui"` rows); two chat routes on one reachable
   platform remain genuinely ambiguous and stay visible/unavailable; a root whose only
   route is unreachable, missing, or owned by another gateway still delivers nothing and
   is never rerouted to a child. The now-redundant post-hoc
   `_origin_platform not in active_platforms` skip was removed because the same predicate
   is applied when the route is selected.
7. **A wake is queued once per live consumer (`gateway/kanban_watchers.py:281-322, 508-512, 591-595, 844-856`; `tui_gateway/server.py:9472-9482, 9829-9847, 9959-9974`).**
   CORE's `claim_collaboration_messages` deliberately resets an expired `queued` lease to
   `pending` so a lost process can redeliver. Round 1 consumed that reclaim as a fresh
   wake: the gateway woke the same live origin again (`wakes 1 -> 2`) and the TUI buffered
   and dispatched the same record again after `lease_expires = now - 10` (1 then 1),
   which D3 / shared decision 5 forbids for a still-live session. Each consumer now keeps
   a process-lifetime record of the wakes it already queued — keyed by `(board, record id)`
   in the gateway (instance attribute `_kanban_collab_wakes`, created on the notifier loop
   thread before the first tick because collection runs in a worker thread via
   `asyncio.to_thread`) and by `(resolved board DB, session key, record id)` in the TUI
   (module-level `_KANBAN_COLLAB_ENQUEUED`, guarded by a lock because one TUI process runs
   a poller thread per session) — and skips those records on a later claim.
   The record is written only after a wake is actually queued (never on the busy-session,
   disconnected-adapter, or failure rewind paths), is bounded at 512 entries with
   insertion-order eviction, and is dropped only with the process, so CORE's reclaim keeps
   working as the process-loss/resumed-recipient redelivery path. The durable row is
   untouched by this: it stays `queued` with no inferred acknowledgment. Each consumer
   carries a boundary pin proving that scope: a fresh gateway consumer instance, and a
   TUI process whose record was reset, both redeliver the still-unconsumed record.
8. **Round-2 local judgement.** Two reversible local choices were made and are recorded
   here rather than as a design change: (a) the dedupe memory is process-scoped rather
   than stored in the durable row, because "still live" is exactly a process-lifetime
   property, no CORE field distinguishes "already woken by this consumer" from
   "reclaimed after process loss", and the unit forbids a second table or state; (b) the
   ambiguity scope is the platform-reach dimension only, so the previously reviewed
   conservative behaviour (two routes on one reachable platform → unavailable, never
   rerouted) is preserved and only cross-platform subscriptions are disregarded.
   No stamped D4-D5 semantic was varied, and the CORE claim/list/advance API is still the
   only collaboration state interface used.

### Round-3 corrections (defect from the round-2 review)

9. **No starvation between concurrent live consumers (filter-before-claim and rewind-on-remembered,
   `gateway/kanban_watchers.py:325-351, 788-809, 876-886`; `tui_gateway/server.py:9850-9875, 9975-10020`).**
   Round 2 recorded queued wakes per process to prevent re-wake loops on lease reclaim.
   However, because CORE's `claim_collaboration_messages` grants an exclusive lease upon claim,
   a live consumer that claimed an expired row and then skipped it would refresh the lease,
   holding exclusive ownership and starving other concurrent consumers (e.g. gateway tick
   holding the lease and starving TUI from collecting, and vice versa in TUI-first).
   Both consumers now implement two composing safeguards:
   (a) **Filter before claim:** before calling `claim_collaboration_messages`, each consumer
   inspects pending root records (via `list_pending_collaboration`). If all pending records for
   that root have already been processed by this live consumer, claiming is skipped entirely,
   leaving the expired or pending record free for other consumers.
   (b) **Immediate rewind:** if `claim_collaboration_messages` ever returns a record already
   remembered, `_kanban_rewind_collaboration` immediately restores `delivery_state="pending"`
   using the matching lease token, releasing exclusive ownership without waiting for lease expiry.
   Process-loss redelivery to a fresh consumer remains intact (empty in-process record).

## 3. Requirement-to-evidence coverage

| Obligation | Check and observed result | Evidence |
| --- | --- | --- |
| CE-03: proactive/origin evidence reaches the exact origin | Gateway and TUI focused fixtures create CORE lifecycle/request rows, claim them via the reviewed API, and assert the formatted peer block contains source role, task/root and summary. | `test_gateway_collaboration_delivery_wakes_origin_without_passive_ping`; `TestTuiCollaborationPoller::test_collect_kanban_collaboration_claims_and_formats_peer_block` — PASS |
| CE-06 / D3: a queued wake is not endlessly re-enqueued to a still-live origin (round-2 fix) | Gateway: one tick queues exactly one internal wake (`wake.internal is True`, `adapter.sends == []`), then after `UPDATE kanban_collaboration SET lease_expires = now-10` a second tick on the same live runner keeps `len(adapter.wakes) == 1`, `adapter.sends == []`, and the row at `delivery_state="queued"`. TUI: after the same lease expiry, `_collect_kanban_collaboration` returns `[]`, the row stays `queued` with `acknowledged_at is None`, and the notify cursor is unchanged; the running poller submits exactly one agent turn across two further passes. | `test_gateway_live_origin_not_rewoken_after_lease_reclaim`; `TestTuiCollaborationLeaseAndRouteScope::test_live_session_is_not_rewoken_after_lease_reclaim`, `::test_poller_loop_does_not_resubmit_after_lease_reclaim` — PASS (RED before the fix: 5 failed / 3 passed) |
| CE-06 / D3: process loss still redelivers an unconsumed record (round-2 boundary) | Gateway: a fresh consumer instance on the same board (same adapter) re-wakes the aged record (`wakes 1 -> 2`, `internal is True`, no `adapter.send`) and the row stays `queued` with `acknowledged_at is None`. TUI: with the process-lifetime record reset, the collector returns the same record id again, still `queued`. | `test_gateway_process_loss_redelivers_unconsumed_record`; `TestTuiCollaborationLeaseAndRouteScope::test_process_loss_redelivers_unconsumed_record` — PASS |
| CE-06 / D5: uniqueness is among routes this consumer would use (round-2 fix) | Gateway with telegram + tui subscriptions on one root: exactly one internal wake on the telegram route, `source.chat_id == "chat-100"`, row `queued`. Two distinct telegram chats on one root: no wake, no `adapter.send`, row left `pending`. TUI on the same shape: one collected item for the matching `session_key`, `recipient_kind="origin"`, still `queued`. | `test_gateway_tui_sub_does_not_make_telegram_origin_ambiguous`; `test_gateway_two_telegram_chats_on_one_root_stay_unavailable`; `TestTuiCollaborationLeaseAndRouteScope::test_telegram_sub_on_same_root_does_not_block_tui_origin` — PASS |
| CE-06 / D5: dual-consumer composition on one root without starvation (round-3 fix) | Both orders tested against the same root with telegram + tui notify subs and origin request. Order 1 (Gateway first): gateway queues 1 wake, immediate TUI collect returns 0 while lease live, lease expires, second gateway tick stays at 1 wake and does not refresh lease, TUI collects 1 item; subsequent passes do not re-enqueue. Order 2 (TUI first): TUI collects 1 item, gateway ticks 0 wakes while lease live, lease expires, second TUI collect returns 0 and does not refresh lease, gateway ticks 1 wake; subsequent passes do not re-enqueue. In both orders: adapter.send == [], no TUI status.update, delivery_state remains queued, acknowledged_at is None, notify cursors untouched. | `test_dual_consumers_compose_without_starvation_gateway_first`; `test_dual_consumers_compose_without_starvation_tui_first` — PASS (RED on 4942a7cfa3: 2 failed) |
| CE-06: independent cursor and no passive human ping | Both focused suites assert the legacy subscription `last_event_id` is unchanged. Gateway asserts `adapter.send()` is empty and only `deliver_wake` is called; TUI asserts zero `status.update` events for collaboration. | Gateway first test and TUI `test_poller_loop_dispatches_collaboration_without_passive_status_update` — PASS |
| CE-06: exact gateway chat/thread/API session | Gateway controlled sink verifies `SessionSource.chat_id` and `thread_id`; API-server fixture verifies `deliver_wake(session_id=raw subscription id, source=None)`. | `test_gateway_collaboration_delivery_wakes_origin_without_passive_ping`; `test_gateway_api_server_collaboration_uses_exact_session_without_ping` — PASS |
| CE-06: exact TUI origin and no reroute | Mismatched/finalized TUI sessions return no item and preserve the pending row; missing root route in the gateway leaves the row pending despite an inherited child route. | `TestTuiCollaborationPoller::test_finalized_or_mismatched_origin_never_reroutes`; `test_gateway_missing_root_route_is_not_rerouted_to_child` — PASS |
| CE-06: separate boards | Two disposable boards use the same chat key; only the board-A row is claimed and delivered, and board-B root identity is absent from the delivered text. | `test_gateway_separate_boards_never_cross_deliver`; `TestTuiCollaborationPoller::test_two_origins_separate_boards_never_receive_each_others_notices` — PASS |
| CE-06/CE-07: busy sessions do not run concurrently | Gateway busy fixture rewinds a claimed row to `pending`, then delivers once idle. TUI busy fixture observes no turn while running and flushes its existing pending buffer after the lock-protected idle transition. | `test_gateway_busy_session_defers_wake_and_delivers_when_idle`; `TestTuiCollaborationPoller::test_busy_session_does_not_run_concurrently` — PASS |
| Preservation: ordinary terminal notifications | Mixed fixtures assert a normal terminal event still uses `adapter.send()` while the separate collaboration row uses internal wake. Pre-consumer baseline and candidate regression below. | `test_gateway_terminal_and_collaboration_coexist`; `TestTuiCollaborationPoller::test_ordinary_terminal_event_and_collaboration_coexist`; baseline `592 passed` — PASS |
| Preservation: no duplicate Supervisor / parent mutation | DELIVER handles only `recipient_kind="origin"`; controller records are not spawned or unblocked here. CORE's reviewed controller advisory tests remain green. | Candidate CORE suites `102 passed`; reviewed parent handoff `CE-HF-CORE.md` — PASS/reused |
| Quickstart cases 4-5 (TUI/gateway parts) | Case 4: busy-origin coalescing and no wake loop for replies/acks/heartbeats — collaboration is wake-only, the reclaim pin forbids repeat wakes, and no collaboration branch touches the terminal cursor. Case 5: two origins with identical display names on separate boards never cross-deliver, exact TUI session and gateway source are used, internal collaboration emits no passive ping while ordinary terminal notification is unchanged. | The focused rows above plus the candidate/baseline receipts in section 4 — PASS with controlled sinks |
| Quickstart case 6 (TUI/gateway parts) | Peer content is formatted as a labeled `[PEER COLLABORATION EVIDENCE - Role: ...]` block that states it cannot expand owner authority, and the gateway/TUI collaboration text is never routed through the operator/out-of-band steer wrapper (wake is internal; TUI buffers session text without a user-facing status ping). | `test_gateway_collaboration_delivery_wakes_origin_without_passive_ping`; `TestTuiCollaborationPoller::test_collect_kanban_collaboration_claims_and_formats_peer_block` — PASS |
| Quickstart case 7 (TUI/gateway parts) | DELIVER never claims or spawns `recipient_kind="controller"` records and never unblocks a parent; the idle continuation reuses the existing session buffer/`deliver_wake` path and the same session key, so no second Supervisor or lease bypass is introduced. | DELIVER collection filters `recipient_kind="origin"`; CORE controller advisory tests `102 passed` — PASS/reused |

Controlled sinks prove only the measured mechanical consumer branches. They do not prove
long-term LLM collaboration efficacy, provider delivery, or live gateway qualification.

## 4. Verification receipts

All commands were run from the isolated fork worktrees with `HERMES_HOME` untouched and
the inherited live-board selectors (`HERMES_KANBAN_DB`, `HERMES_KANBAN_BOARD`,
`HERMES_KANBAN_TASK`, `HERMES_KANBAN_RUN_ID`, `HERMES_KANBAN_WORKSPACES_ROOT`,
`HERMES_KANBAN_CLAIM_LOCK`) unset, plus `HERMES_TEST_FILE_RETRIES=0` and
`-p no:randomly`. Each test module's autouse fixture additionally asserts the resolved
board DB path is under its `tmp_path` before opening a connection.

### Pre-consumer baseline `3b81e9d91c` (round-2 re-run, fresh worktree)

```text
git worktree add --detach /tmp/ce-hf-deliver-baseline-3b81e9d 3b81e9d91cc3a0662b910726a44c94ed328b1e90
uv sync --extra dev --frozen            # Python 3.11.15 venv in that worktree

.venv/bin/python -c "import gateway.kanban_watchers as m; \
  print(any('collaboration' in n for n in dir(m.GatewayKanbanWatchersMixin)))"
collaboration consumer symbols present: False

HERMES_TEST_FILE_RETRIES=0 python -m pytest -q \
  tests/gateway/test_kanban_watchers_mixin.py \
  tests/test_tui_gateway_server.py \
  tests/tui_gateway/test_kanban_notify_poller.py
592 passed in 37.78s

# Same candidate focused modules copied onto the pre-consumer tree:
HERMES_TEST_FILE_RETRIES=0 python -m pytest -q \
  tests/gateway/test_kanban_collaboration_delivery.py \
  tests/tui_gateway/test_kanban_collaboration_poller.py
21 failed in 0.96s        # CORE claim/list API absent: no collaboration wake path exists
```

The pre-consumer tree therefore has no collaboration consumer and its existing
terminal-notification behaviour (592 tests) is unchanged. The focused modules are
CORE-dependent causal tests and fail on this commit for the expected reason (missing
CORE API), not as a behavioural positive.

### Round-2 fail-first on the round-1 candidate `3b569a345b`

The eight new pins were run against the round-1 candidate's committed production sources
(`git checkout 3b569a345b -- gateway/kanban_watchers.py tui_gateway/server.py`, pins kept
in the worktree; sources restored afterwards and their hashes re-verified against
section 1):

```text
5 failed, 3 passed in 3.12s
FAILED tests/gateway/test_kanban_collaboration_delivery.py::test_gateway_live_origin_not_rewoken_after_lease_reclaim
FAILED tests/gateway/test_kanban_collaboration_delivery.py::test_gateway_tui_sub_does_not_make_telegram_origin_ambiguous
FAILED tests/tui_gateway/test_kanban_collaboration_poller.py::TestTuiCollaborationLeaseAndRouteScope::test_live_session_is_not_rewoken_after_lease_reclaim
FAILED tests/tui_gateway/test_kanban_collaboration_poller.py::TestTuiCollaborationLeaseAndRouteScope::test_poller_loop_does_not_resubmit_after_lease_reclaim
FAILED tests/tui_gateway/test_kanban_collaboration_poller.py::TestTuiCollaborationLeaseAndRouteScope::test_process_loss_redelivers_unconsumed_record
```

The TUI process-loss pin fails on the round-1 sources at its middle assertion (the
collector re-claims the record after lease expiry, which is the D3 defect), then passes on
the candidate at the same assertion — the boundary half of that pin is green on both
revisions, so the RED is the defect, not the boundary.

The three passing pins are the guards that must stay green on both revisions
(`test_gateway_two_telegram_chats_on_one_root_stay_unavailable`,
`test_gateway_process_loss_redelivers_unconsumed_record`,
`TestTuiCollaborationLeaseAndRouteScope::test_telegram_sub_on_same_root_does_not_block_tui_origin`).
The gateway reclaim pin uses the real `gateway.wake.deliver_wake` path against the
controlled fake adapter — not a monkeypatched wake — so the recorded wake count is the
one the consumer actually produced. The round-1 sources were restored with
`git checkout HEAD -- …` and their hashes re-verified against section 1 before the
candidate suites below were run.

### Round-3 fail-first on the round-2 candidate `4942a7cfa3`

The two new dual-consumer composition pins were run against the round-2 candidate's committed production sources (`git checkout 4942a7cfa3 -- gateway/kanban_watchers.py tui_gateway/server.py`):

```text
2 failed in 0.92s
FAILED tests/gateway/test_kanban_collaboration_delivery.py::test_dual_consumers_compose_without_starvation_gateway_first (assert 0 == 1 where 0 = len([]), TUI starved by gateway tick)
FAILED tests/gateway/test_kanban_collaboration_delivery.py::test_dual_consumers_compose_without_starvation_tui_first (assert 0 == 1 where 0 = len([]), Gateway starved by TUI collect)
```

The round-2 sources were restored and their hashes re-verified against section 1 before the candidate suites below were run.

### Candidate `d1d1f9e9f4` (committed revision, working tree clean)

Interpreter: this fork worktree's `.venv/bin/python` (Python 3.11.15, created with
`uv sync --extra dev --frozen`).

```text
HERMES_TEST_FILE_RETRIES=0 python -m pytest -q \
  tests/gateway/test_kanban_watchers_mixin.py \
  tests/test_tui_gateway_server.py \
  tests/tui_gateway/test_kanban_notify_poller.py \
  tests/gateway/test_kanban_collaboration_delivery.py \
  tests/tui_gateway/test_kanban_collaboration_poller.py
615 passed in 39.19s (repeat 38.21s)         # required set; 613 in round 2 plus the 2 dual-consumer pins

# Owned focused modules only:
23 passed in 6.20s

# Reviewed CORE regression from the candidate import context:
HERMES_TEST_FILE_RETRIES=0 python -m pytest -q \
  tests/hermes_cli/test_kanban_collaboration.py \
  tests/tools/test_kanban_collaboration.py \
  tests/tools/test_kanban_tools.py \
  tests/hermes_cli/test_kanban_session_affinity.py
102 passed in 9.32s

ruff check gateway/kanban_watchers.py tui_gateway/server.py \
  tests/gateway/test_kanban_collaboration_delivery.py \
  tests/tui_gateway/test_kanban_collaboration_poller.py
All checks passed!
ruff format --check tests/gateway/test_kanban_collaboration_delivery.py \
  tests/tui_gateway/test_kanban_collaboration_poller.py
2 files already formatted
git diff --check 3b81e9d91cc3a0662b910726a44c94ed328b1e90...HEAD
exit code 0
```

The pre-existing fork files contain unrelated formatting drift, so the production files
were checked with Ruff rather than reformatted wholesale. The only formatting action in
this unit was `ruff format` on the owned test modules.

### Reused (not re-run this round)

- Round-1 receipt of the pre-consumer baseline (592 passed) — superseded by the fresh
  round-2 re-run above.
- Supervisor's independent overlay of the CORE-parent `gateway/kanban_watchers.py` and
  `tui_gateway/server.py` under the candidate tests (`18 failed / 3 passed`) — independent
  evidence recorded in the round-2 review comment; not re-run by the implementer.

## 5. Isolation incident and live-board preservation

A first diagnostic native-writer probe in this task's round-1 session redirected only
`HERMES_KANBAN_HOME` while inherited `HERMES_KANBAN_DB`/`HERMES_KANBAN_BOARD` still
pointed at the active objective board. It created the live cards `t_ebd28f85` and
`t_c46db090` and observed existing live collaboration rows. This was an isolation
incident, not contract work. The cards and rows are preserved; no SQL deletion, cleanup,
or counting of those cards as acceptance occurred. Aether issue #267 was reopened with
sanitized evidence by the operator.

Both consumers' test fixtures unset `HERMES_KANBAN_DB`, `HERMES_KANBAN_BOARD`,
`HERMES_KANBAN_TASK`, `HERMES_KANBAN_RUN_ID`, and `HERMES_KANBAN_WORKSPACES_ROOT`, then
assert the resolved DB path is under their unique disposable root before any native
writer (`_isolated_connect`); the round-2 test commands additionally unset those
selectors in the environment itself.

Read-only live-board fingerprints around the final required regression (613 passed):

```text
before final regression: tasks=18/max_id=t_f3e60446, task_events=516/516,
  task_comments=16/16, kanban_notify_subs=4/4, kanban_collaboration=3/3,
  task_runs=26/26, task_attachments=0/0
final regression: 613 passed in 39.10s
after final regression:  tasks=18/max_id=t_f3e60446, task_events=517/517,
  task_comments=16/16, kanban_notify_subs=4/4, kanban_collaboration=3/3,
  task_runs=26/26, task_attachments=0/0
new task_events after checkpoint: [('heartbeat', 1)]
```

The only live-board event delta during the final test interval was one operational
`heartbeat` for this still-running task (run 26); there were no new task, comment,
subscription, run, attachment, or collaboration rows. Over the whole round-2 session the
first fingerprint checkpoint (task_events 505) to the last (517) added only
`heartbeat` events (`[('heartbeat', 12)]`, no non-heartbeat kind) with every other table
count unchanged. Incident cards verified preserved with their link: `t_ebd28f85`
(root, blocked) → `t_c46db090` (child, todo), and collaboration rows 1-3 (pre-existing
route-residue rows) unchanged and `open`.

## 6. Shared decisions stamped from `tasks.md`

1. Authority is Objective Contract `oc_a28ff9b7fa20d29d@v1`, digest
   `7a51dc2b3d2d62788b1228f823f9def58652e48d48fcecaecb5293f34dde7de5`; skills grant
   no authority and the contract was not edited.
2. Aether evidence starts from `183bd7a4944a5db7d22091c402a74383a80100fa`; fork
   edits use an isolated nested worktree from `3b81e9d91cc3a0662b910726a44c94ed328b1e90`;
   live runtime, `aether-main`, and `home/` were not edited.
3. DELIVER target hashes matched the stamped base before mutation; candidate hashes are
   recorded in section 1 and re-verified against `git show` at the candidate commit.
4. Existing native signatures and CORE's reviewed adjunct API were reused; no second
   table, comment writer, or terminal cursor was introduced.
5. One `kanban_collaboration` table and distinct claim/list/advance lease path are
   consumed. Wake/steer is only queued; explicit ack/respond is consumption; a queued
   wake is not re-enqueued to a consumer that is still live. Origin delivery is internal
   wake-only and peer text is a labeled native evidence block.
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
13. Local judgement covered fixture sinks, route-key factoring, platform-reach scoping,
    the process-scoped wake record, and use of CORE's reviewed helpers; public D4-D5
    semantics were not varied.
14. The isolation incident was recorded and preserved; no further live contract rows
    were written by the regression, and no cross-unit collision was absorbed.
15. The fork candidate is committed locally and this unit requests same-card Supervisor
    re-review; compatibility is `minor`; no publication or issue close was performed.
16. The objective remains optional/off for generic and historical flows; no retroactive
    enablement or stopped-monitor restart was performed.
17. GitHub issue #334 remains open for CE-INT closeout; this unit did not close it.

## 7. Exact ledger paragraph for CE-INT

```markdown
### HLP-334: TUI and gateway collaboration consumers
- **Status:** Candidate implemented in maintained fork at commit `d1d1f9e9f4eb8fc5998a44274c5d5e16541f6e24`.
- **Issue:** [Aether #334](https://github.com/DarkArty07/Aether-Agents/issues/334).
- **Objective Contract:** `oc_a28ff9b7fa20d29d@v1` (SHA-256 `7a51dc2b3d2d62788b1228f823f9def58652e48d48fcecaecb5293f34dde7de5`).
- **Files touched:** `gateway/kanban_watchers.py`, `tui_gateway/server.py`, `tests/gateway/test_kanban_collaboration_delivery.py`, `tests/tui_gateway/test_kanban_collaboration_poller.py`.
- **Scope & Behavior:** Adds maintained-fork gateway and TUI consumers for CORE's `kanban_collaboration` adjunct. Each consumer claims collaboration records through the distinct bounded lease API rather than `advance_notify_cursor`, routes only to the exact root subscription/session/chat/thread on its board within the platforms that consumer can reach, fences busy sessions, queues each wake once per live process (bounded process-lifetime record; a lease reclaim after expiry never re-wakes a still-live origin/session, while process loss still redelivers), prevents concurrent consumer starvation by filtering remembered IDs before claim and immediately rewinding skipped claims, keeps queued work durable until explicit consumption, labels peer evidence as non-owner advice, emits no passive human ping for internal collaboration, preserves ordinary terminal notifications, and leaves missing/ambiguous/closed origins unavailable instead of rerouting.
- **Upstream Relationship:** Downstream enhancement to Hermes Agent kanban coordination; consumes the reviewed CORE native collaboration store/tool surface without adding a second bus or changing legacy notification semantics.
- **Rollback:** Restore `gateway/kanban_watchers.py` and `tui_gateway/server.py` from the reviewed CORE parent commit `20db06c0b8441190830aa72e3c0de6fdce6b8db4`; the additive CORE schema/history remains intact and no down-migration is required for this consumer-only unit.
- **Maintenance / Retirement:** Retain while Aether contracts use active multi-role collaboration; retire the consumer delta when the native collaboration contract is retired or an equivalent upstream Hermes capability passes its behavior gate.
```

## 8. Remaining limits and handoff

- Fake adapter/TUI sinks establish only the measured local delivery branches. No live
  Telegram, gateway, model, or long-term behavioral efficacy claim was made.
- The wake record is process-scoped by design: a gateway/TUI process restart makes CORE's
  lease reclaim redeliver an unconsumed record to the origin again. That is the intended
  process-loss path, not a suppression failure; a still-live consumer is woken once.
- The candidate requires the reviewed CORE parent at `20db06c...`; the pre-consumer
  baseline intentionally has no positive collaboration API (all 21 focused tests fail
  there for the expected missing-API reason, with the 592 existing tests still passing).
- The dedupe boundary is pinned in both consumers (fresh process → redelivery), but a
  resumed *recipient* session that never acknowledges a record will not be re-pinged by
  the same live process; the record stays visible in the durable store for explicit
  consumption or later process-loss redelivery.
- Integration, dual-repository publication, runtime adoption/readback, rollback
  qualification, residue reconciliation and aggregate release conclusions belong to
  CE-INT. Provisional unit compatibility is `minor`; this unit does not decide the
  aggregate release action (`defer` / `none`).
