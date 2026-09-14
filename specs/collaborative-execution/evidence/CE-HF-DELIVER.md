# Implementation Evidence — Unit CE-HF-DELIVER

**Status:** Round-4 corrections implemented and locally verified; ready for same-card
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
- **Round-1 review:** `changes_requested` on `3b569a345b`.
- **Round-2 review:** `changes_requested` on `4942a7cfa3`.
- **Round-3 review:** `changes_requested` on `d1d1f9e9f4` after Morfeo D5 at
  `162a27e` / `dd2f1aa` withdrew dual-success fan-out. Corrected in `2ec004ea54`.

## 1. Repository identity, prerequisites and scope

| Tree | Observed identity | Evidence |
| --- | --- | --- |
| Aether contract/base | `183bd7a4944a5db7d22091c402a74383a80100fa` | Task/decomposition input; only this evidence file changed in Aether |
| Maintained fork base | `DarkArty07/aether-hermes` `3b81e9d91cc3a0662b910726a44c94ed328b1e90` | Isolated nested worktree |
| Reviewed CORE parent | `20db06c0b8441190830aa72e3c0de6fdce6b8db4` | Completed CORE card not reopened |
| Round-3 candidate (superseded) | `d1d1f9e9f41b72b9178b52bdf5c7ff4a6f40457f` | Exact git rev-parse of the prior candidate |
| **DELIVER candidate** | `2ec004ea54ab2401f63f1885a7c26f59bf1eb7db` | Local commit on `feat/334-deliver-tui-gateway` |
| `gateway/kanban_watchers.py` | `192adcbf537a4fbded71f823516c80cd764a0876998ef0891fa78379ac09b824` | `git show HEAD:gateway/kanban_watchers.py \| sha256sum` |
| `tui_gateway/server.py` | `410541e1e5ad053605744f0d7e353c72620865a346f2bea2517f38dfb09bce5a` | `git show HEAD:tui_gateway/server.py \| sha256sum` |
| `hermes_cli/kanban_db.py` | `12dbba5be4ed5823d6282ddc451847b6efac59d63bf8c869e24f108af2fab5af` | `git show HEAD:hermes_cli/kanban_db.py \| sha256sum` |
| `tools/kanban_tools.py` | `9e288c1e00cb00771cd4cc718103fda78fc5fc11fa08b97dcd70dfa221d629cc` | `git show HEAD:tools/kanban_tools.py \| sha256sum` |
| Morfeo D5 | Aether `dd2f1aa449b2e9fc7ab808089a98e35146b51fb8` | `plan.md` origin-binding + `evidence/morfeo-direction-origin.md` |

Writable files for this correction: `hermes_cli/kanban_db.py`, `tools/kanban_tools.py`,
their focused collaboration tests, plus the DELIVER consumer files
`gateway/kanban_watchers.py`, `tui_gateway/server.py`,
`tests/gateway/test_kanban_collaboration_delivery.py`,
`tests/tui_gateway/test_kanban_collaboration_poller.py`.
`AETHER_FORK.md`, `HERMES_LOCAL_PATCHES.md`, live runtime, and `home/` were not
edited. No push, PR, merge, issue close, activation, live Telegram, or paid model.

## 2. Implementation and local technical judgement

Round-4 implements Morfeo D5 origin-binding (`dd2f1aa`): supporting TUI and gateway
means either surface may **be** the commissioning origin, not fan-out of one origin
row to every notify subscriber.

1. **Capture (`tools/kanban_tools.py`, `hermes_cli/kanban_db.py`).**
   `_resolve_commissioning_origin_route` reads the same trusted create context as
   `_maybe_auto_subscribe` (gateway platform/chat/thread, TUI `HERMES_SESSION_KEY`,
   or notification origin). Advisory `kanban_create` refuses opt-in when that context
   is missing. `opt_in_collaboration` persists `origin_route` on the existing
   `collaboration_opted_in` event and refuses a route without `platform`+`chat_id`.
   `origin_session_id` remains the raw SessionDB id and is not treated as a chat id.
2. **Match before claim.** `get_collaboration_origin_route` plus
   `collaboration_origin_route_matches_sub` are the common native accessors. Gateway
   and TUI match that one route before `claim_collaboration_messages`. Extra notify
   subs, `active_platforms`, and tick order do not select the origin. Missing route,
   closed session, or tuple mismatch leaves the row pending/unavailable with no
   fallback and no backfill of older opted-in records.
3. **D3 preserved.** Process-lifetime wake memory still prevents re-enqueue to a
   still-live origin after lease reclaim; process-loss still redelivers to the same
   commissioned origin. Filter-before-claim / rewind remain same-consumer D3 hygiene,
   not fairness so another platform can consume the same origin row.
4. **Fixtures.** Consumer tests stamp distinct `session_id` vs `chat_id` /
   TUI session key. Dual-success pins were replaced with exclusivity in both tick
   orders.

## 3. Requirement-to-evidence coverage

| Obligation | Check and observed result | Evidence |
| --- | --- | --- |
| CE-01 / D5: persist commissioning origin_route | Tool create with distinct SessionDB id and TUI session key persists `origin_route.platform=tui`, `chat_id=tui-origin-session-tools`, `origin_session_id=session-db-raw-tools`. Incomplete route raises. Missing session context refuses advisory create. | `test_kanban_create_collaboration_opt_in_and_child_refusal`; `test_kanban_create_advisory_requires_commissioning_context`; `test_opt_in_origin_route_persist_match_and_refusal` — PASS |
| CE-06 / D5: extra subscribers are not recipients | Telegram commissioning origin + extra TUI sub: gateway 1 internal wake, TUI collect 0, both orders, D3 hold after lease expiry. TUI commissioning origin + extra telegram sub: TUI collect 1, gateway 0, both orders. | `test_exclusivity_commissioned_telegram_origin_*`; `test_exclusivity_commissioned_tui_origin_*` — PASS |
| CE-06: same-surface foreign chat | Extra telegram chat on the same root does not wake; commissioned `chat-100` does. Duplicate exact route remains unavailable. | `test_gateway_same_surface_foreign_chat_ignored`; `test_gateway_two_telegram_chats_on_one_root_stay_unavailable` (now extra chat-101) — PASS |
| CE-06: missing origin_route stays unavailable | Opt-in without `origin_route` (older record): gateway 0 wakes, TUI collect 0, row `pending`. | `test_origin_route_missing_stays_unavailable` — PASS |
| CE-06 / D3: still-live origin not re-enqueued | Expire lease, second tick/collect stays 1 wake / 0 extra TUI items. | Gateway and TUI live-session pins plus exclusivity D3 hold — PASS |
| CE-06 / D3: process-loss redelivery | Fresh consumer redelivers the unconsumed record to the same origin. | `test_gateway_process_loss_redelivers_unconsumed_record`; TUI process-loss pin — PASS |
| CE-06: no passive ping; notify cursor intact | `adapter.send==[]` for collaboration; TUI no `status.update`; `last_event_id` unchanged. | Existing gateway/TUI peer-block and coexistence tests — PASS |
| Preservation | Ordinary terminal notify still uses `adapter.send`; CORE files remain additive; ledgers not edited. | Required 619 + CORE 105; `git diff --name-only` excludes ledgers |

## 4. Verification receipts

All commands from the isolated fork worktree with live-board selectors unset,
`HERMES_TEST_FILE_RETRIES=0`, `-p no:randomly`. Interpreter:
`.venv/bin/python` (Python 3.11.15).

```text
# Focused CORE + DELIVER collaboration modules
52 passed in 8.48s   # then format-only of owned tests; re-run via required set

# Required DELIVER set
HERMES_TEST_FILE_RETRIES=0 python -m pytest -q \
  tests/gateway/test_kanban_watchers_mixin.py \
  tests/test_tui_gateway_server.py \
  tests/tui_gateway/test_kanban_notify_poller.py \
  tests/gateway/test_kanban_collaboration_delivery.py \
  tests/tui_gateway/test_kanban_collaboration_poller.py
619 passed in 38.58s

# CORE regression (includes new origin_route tests)
HERMES_TEST_FILE_RETRIES=0 python -m pytest -q \
  tests/hermes_cli/test_kanban_collaboration.py \
  tests/tools/test_kanban_collaboration.py \
  tests/tools/test_kanban_tools.py \
  tests/hermes_cli/test_kanban_session_affinity.py
105 passed in 9.58s

ruff check <touched Python>: All checks passed
ruff format --check owned tests: 4 files already formatted (after ruff format of those four)
git diff --check 3b81e9d... : exit 0
```

Collect-only of the required DELIVER set: **619**. Focused collaboration modules
in that set: gateway 17 + TUI 10 = **27**. CORE collaboration pair is 16+10=**26**
inside the 105 CORE regression.

Round-2/3 attributed receipts (pre-consumer 592, fail-first overlays) are unchanged
and not re-run this round. Dual-success pins
`test_dual_consumers_compose_without_starvation_*` were removed.

## 5. Isolation incident and live-board preservation

Incident cards `t_ebd28f85` (root, blocked) → `t_c46db090` (child, todo) remain.
Collaboration rows 1-3 unchanged, `pending`/`open`. No SQL delete.

Read-only fingerprint after the required suites (this run):

```text
tasks=18/max_id=t_f3e60446
task_comments=26
kanban_notify_subs=4
kanban_collaboration=3/max=3
task_runs=30
task_attachments=0
task_links=15
```

Event growth during this implementer run was heartbeats, claimed/spawned, and
review-thread comments — not new collaboration rows or incident-card mutation.

## 6. Shared decisions

Stamped 1–17 from `tasks.md`. Round-4 additionally consumes Morfeo D5 at `dd2f1aa`:
persist `origin_route` on the existing opt-in event; match one route before claim;
do not equate SessionDB id, chat id, and TUI session key; dual-consumer tests are
exclusivity controls. Completed CORE `t_07e9bbd7` was not reopened as a card; the
helper/test scope required by D5 is on this DELIVER card only.

## 7. Exact ledger paragraph for CE-INT

```markdown
### HLP-334: TUI and gateway collaboration consumers
- **Status:** Candidate implemented in maintained fork at commit `2ec004ea54ab2401f63f1885a7c26f59bf1eb7db`.
- **Issue:** [Aether #334](https://github.com/DarkArty07/Aether-Agents/issues/334).
- **Objective Contract:** `oc_a28ff9b7fa20d29d@v1` (SHA-256 `7a51dc2b3d2d62788b1228f823f9def58652e48d48fcecaecb5293f34dde7de5`).
- **Files touched:** `hermes_cli/kanban_db.py`, `tools/kanban_tools.py`, `gateway/kanban_watchers.py`, `tui_gateway/server.py`, `tests/hermes_cli/test_kanban_collaboration.py`, `tests/tools/test_kanban_collaboration.py`, `tests/gateway/test_kanban_collaboration_delivery.py`, `tests/tui_gateway/test_kanban_collaboration_poller.py`.
- **Scope & Behavior:** Persists a runtime-derived commissioning `origin_route` on the existing `collaboration_opted_in` event (platform, chat_id as native TUI session key, thread_id, notifier_profile, origin_session_id, reconstruct fields) captured from the same trusted create context as auto-subscribe. Gateway and TUI consumers match that one route before claiming collaboration records; extra notify subscribers are not recipients. Missing/conflicting/older routes stay unavailable without backfill. Still-live origin is not re-enqueued after lease reclaim; process-loss still redelivers to the same commissioned origin. Internal collaboration remains wake-only with labeled peer evidence and no passive ping; ordinary terminal notifications are unchanged.
- **Upstream Relationship:** Downstream enhancement to Hermes Agent kanban coordination; extends the reviewed CORE opt-in event without a second table, tool, or bus.
- **Rollback:** Restore `hermes_cli/kanban_db.py`, `tools/kanban_tools.py`, `gateway/kanban_watchers.py`, and `tui_gateway/server.py` from `d1d1f9e9f41b72b9178b52bdf5c7ff4a6f40457f` (or CORE parent `20db06c0` for the full unit). Additive event payload; no down-migration.
- **Maintenance / Retirement:** Retain while Aether contracts use active multi-role collaboration; retire with the native collaboration contract or an equivalent upstream capability.
```

## 8. Remaining limits and handoff

- Controlled sinks only; no live Telegram/gateway/model qualification.
- Older opted-in records without `origin_route` stay unavailable by design (no guessed backfill).
- Integration, dual-repository publication, runtime adoption, and aggregate release
  conclusions belong to CE-INT. Unit compatibility `minor`; `release_action` remains
  `defer` for CE-INT.
