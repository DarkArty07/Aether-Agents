# Active Morfeo collaboration — Supervisor task breakdown

**Status:** verified decomposition for Objective Contract `oc_a28ff9b7fa20d29d@v1`.

**Derived by:** Supervisor

**Source contract:** `.aether/objective-contracts/oc_a28ff9b7fa20d29d/v1.md`
(SHA-256 `7a51dc2b3d2d62788b1228f823f9def58652e48d48fcecaecb5293f34dde7de5`)
on Aether base `183bd7a4944a5db7d22091c402a74383a80100fa`. Plan/spec/quickstart/research
landed at `b7914f73545b14389f92fcaeed05247cf86f5f7d`. Inspected `origin/main`
`aaeacb211b892b5dd893ecaa4abba7933011d12c` is an ancestor of the contract commit;
implement from a checkout that contains `183bd7a`, not from `origin/main` alone.

**Fork baseline:** `DarkArty07/aether-hermes` `aether-main`
`3b81e9d91cc3a0662b910726a44c94ed328b1e90`.
Target-file SHA-256 at this SHA:
`hermes_cli/kanban_db.py` `8e0e359e0e86200051069d02ca8ca7be44d1e594dca89ec8e118c7e68ab2e857`,
`tools/kanban_tools.py` `5648e720d37e91898acff2e137dff184230cacc8217fba420526b33bd37a5179`,
`gateway/kanban_watchers.py` `755091a353cc3e6a9928e2eee016aa3a2b74b95e690282aa59df442850a10f5d`,
`tui_gateway/server.py` `39d2e7a3c04e5810a803c8023719fb72b02c842122ba242553d37276b9a6e096`.
Implementation units add nested isolated worktrees from a fetch of that remote/SHA.
They must not mutate `aether-main`, must not use a stale research clone whose HEAD
is not this SHA, and must not edit the live editable runtime.

**Owning issue:** [#334](https://github.com/DarkArty07/Aether-Agents/issues/334).
Related dispositions: [#317](https://github.com/DarkArty07/Aether-Agents/issues/317)
(open; owner-directed retirement of the open-ended observation gate, not organic PASS)
and [#407](https://github.com/DarkArty07/Aether-Agents/issues/407) (already closed
postmortem; link the mitigation, do not rewrite failed acceptance).

This file is Supervisor-owned execution decomposition. It does not widen the
Objective Contract. Card bodies remain the executable unit deliveries. No
implementation units were authored by Morfeo. Root completion is decomposition
handoff, not feature acceptance.

## Receipt

| Check | Observed |
| --- | --- |
| Portable project | `.aether/project.toml` `project_id` equals envelope `12027989-a08f-41cd-a82c-54ff1bfb6b03` |
| Native project / board | envelope-bound; do not paste into child bodies or this file |
| Contract bytes | SHA-256 matches the envelope |
| Aether HEAD | `183bd7a4944a5db7d22091c402a74383a80100fa` (`docs(collaboration): finalize project-bound execution contract`) |
| `origin/main` | `aaeacb211b892b5dd893ecaa4abba7933011d12c`; ancestor of HEAD |
| Fork identity | remote `aether-main` = `3b81e9d91cc3a0662b910726a44c94ed328b1e90`; target-file hashes above |
| Design sufficiency | `spec.md` CE-01..CE-12, `plan.md` D1-D9, `quickstart.md` oracles, dual-repo closeout, preservation, and stop conditions are decided. Existing native signatures are reused. No missing public collaboration API. |
| Knowledge index | bound project matches; `INDEX_MISSING` / `available=false`; source inspection used |
| Profiles | `implementer`, `supervisor`, and `morfeo` exist; no extra roles |
| Project Canonical Skills | `.aether/skills/aether-observe/SKILL.md` only; observation is a read model. Aether Canonical procedures apply |
| Issues | #334 OPEN, #317 OPEN, #407 CLOSED |
| Observer | `aether_observe` status for this trace hit the outer timeout and is recorded as Aether #417. Direct board/logs remain usable. Not a blocker and not permission to repair the observer in this objective |
| Concurrent residue | many unrelated worktrees, the stopped Telegram Monitor, and live profiles exist; preserve them |

## Cross-artifact executability

| Concern | Settled conclusion | Execution consequence |
| --- | --- | --- |
| Dual repository | Maintained fork owns native store, tool surface, TUI/gateway consumers. Aether owns SOUL/skills, affected normative docs, packaging/manifest, evidence, ledger, and Aether closeout | Never edit the live editable Hermes runtime or `home/`. Resolve the fork by remote/SHA into an isolated nested worktree. Never mutate `aether-main` in place |
| DB/tool coupling | `add_comment(conn, task_id, author, body)` and `kanban_comment(task_id, body, board)` remain; collaboration is an adjunct table plus optional tool object. Atomic persist lives in the same board DB transaction. Quickstart allows one focused test module pair or one unit when DB/tool ownership is one unit | CE-HF-CORE owns both `hermes_cli/kanban_db.py` and `tools/kanban_tools.py`. Do not split them across workers. Stamp the shared consume API below for CE-HF-DELIVER |
| Delivery consumers | Gateway notifier and TUI poller must process collaboration independently of the legacy `kanban_notify_subs` cursor. They consume CORE's adjunct records; they do not invent a second table | CE-HF-DELIVER parent-gates on independently reviewed CE-HF-CORE. Exclusive files: `gateway/kanban_watchers.py` and the TUI notification-poller branch |
| Aether resources vs docs | D6 already authors the three role amendments. Resource files and normative docs must agree but do not share writable files if tests are partitioned | CE-AE-RES and CE-AE-DOCS run with the root; they do not wait for fork delivery |
| Ledgers | Concurrent edits to `HERMES_LOCAL_PATCHES.md` / fork `AETHER_FORK.md` are not independent | Implementation units do not edit either ledger. They supply the exact paragraph in the handoff. CE-INT applies both after independent review |
| `policy.yml` | Non-`specs/` paths are allowlisted; `specs/` is excluded from that list | CE-AE-DOCS adds the already-committed contract path to the literal canonical base manifest. Other units must not add new non-`specs/` Aether files; if one is required, return to Supervisor |
| Testing | Bounded mechanical/resource verification in disposable scrubbed state. Fake delivery sinks are labeled as such. No organic/Telegram/model campaign | Identical new tests RED on unchanged bases then GREEN on the candidate. Temporary trees only. No live board or paid model |
| Publication / activation | Implementer commits locally and does not push/PR/merge/close issues | CE-INT owns dual-repo closeout and scoped runtime adoption. Aggregate `release_action=defer`, `release_channel=none`. Provisional `release_impact=minor` unless inspected compatibility evidence proves otherwise |
| Observer / Telegram | #417 observer timeout and the stopped Telegram Monitor are out of scope | Do not call `aether_observe` to manufacture progress. Do not restart the monitor |
| Out of scope | Fourth role, second bus, numeric judge, credentials/providers, force/bypass, package release, live overwrite, long-term behavioral PASS | Report incidental defects; do not absorb them |

Inspected current baselines (Aether `183bd7a`, fork `3b81e9d`):

- `kanban_comment` persists via `add_comment(conn, task_id, author, body)` and returns `{ok, task_id, comment_id}`. Author is `HERMES_PROFILE`, never caller-supplied.
- `inject_new_comments_from_env` uses an in-memory watermark, advances it before `agent.steer`, and labels foreign comments as “from the operator”.
- `kanban_create` has no `collaboration` argument. Opt-in does not exist.
- Board schema has `tasks`, `task_comments`, `task_events`, `kanban_notify_subs`; no `kanban_collaboration` table.
- Gateway watchers deliver `TERMINAL_KINDS` including `origin_signal` / `flow_terminal` through the notify-sub cursor. TUI `_notification_poller_loop` polls the same subscriptions.
- Controller continuation uses `flow_attention` events. Decomposition-root `done` is not a terminal flow event.
- Aether SOUL/skills and `docs/guides/execution.md` still describe terminal-only origin routing and #317 as an open observation tracker.

## Requirement coverage

| Source | Unit | Notes |
| --- | --- | --- |
| CE-01 opt-in binding / legacy | CE-HF-CORE | Root event + inherit through unique same-board same-Project ancestor root; child cannot enable/override |
| CE-02 explicit request before completion | CE-HF-CORE | Optional `collaboration` object on `kanban_comment`; source task keeps claim/status |
| CE-03 proactive notices + coalesce | CE-HF-CORE enqueue; CE-HF-DELIVER origin reach | Lifecycle `review_requested` / `changes_requested` / `blocked` / root-decomposition handoff; no heartbeat/tool loop |
| CE-04 persist/enqueue/ack/respond/resolve | CE-HF-CORE | Distinct fields; failed enqueue and process loss remain recoverable; dedup |
| CE-05 peer evidence / truncation / no owner promotion | CE-HF-CORE | Labeled peer block; no out-of-band owner wrapper; refuse truncated/malformed before mutation |
| CE-06 TUI/gateway exact origin, no passive ping | CE-HF-DELIVER | Independent collaboration cursor; existing exact-session continuation; `NO_REPLY` / non-passive path |
| CE-07 controller lease/workspace/parent gating | CE-HF-CORE attention record; CE-HF-DELIVER must not spawn another Supervisor | Advisory resolution does not unblock an unrelated parent |
| CE-08 stale / root-done is not terminal | CE-HF-CORE | Ended/archived/owner-stopped expire; superseded contract stale; no restart of completed units |
| CE-09 role resources + normative agreement | CE-AE-RES + CE-AE-DOCS | D6 wording; independent acceptance preserved |
| CE-10 fork + Aether distribution | CE-HF-CORE + CE-HF-DELIVER + CE-AE-RES + CE-AE-DOCS; CE-INT ledger/PRs | No hidden live implementation |
| CE-11 runtime adoption / rollback / readback | CE-INT | After independently reviewed units and green merges |
| CE-12 GitHub/issue/residue closeout | CE-INT | Unverified behavioral efficacy retained |
| Preservation / authority | every unit + CE-INT | No credentials, no monitor restart, no observer repair (#417), no check bypass |

## Shared decisions (stamp into every implementation unit)

1. Authority is Objective Contract `oc_a28ff9b7fa20d29d@v1` (SHA-256 `7a51dc2b3d2d62788b1228f823f9def58652e48d48fcecaecb5293f34dde7de5`). Skills grant no authority. Do not edit the canonical Objective Contract.
2. Aether product/evidence starts from `183bd7a4944a5db7d22091c402a74383a80100fa`. Fork product edits start from isolated nested worktrees of `DarkArty07/aether-hermes` at `3b81e9d91cc3a0662b910726a44c94ed328b1e90`. Locate the fork by remote URL `https://github.com/DarkArty07/aether-hermes.git` and that SHA. Cards remain Aether-project worktrees. Never copy or edit the live editable runtime. Never mutate a checkout whose current branch is `aether-main` in place. Never edit `home/`.
3. Before mutation, re-hash this unit's target production files at the unit base. Required SHA-256 values are in Receipt / the unit body. A mismatch is a stop condition: return to Supervisor; do not patch.
4. Preserve existing native signatures; do not replace them with illustrative ones:
   - `kanban_comment` remains `(task_id, body, board)` and does not implicitly request a peer turn.
   - `add_comment(conn, task_id, author, body) -> int` remains the comment writer. Collaboration text is stored in existing comments (or an existing lifecycle event for automatic notices); the adjunct row references them. Do not duplicate raw logs.
   - Comment `author` stays runtime-derived (`HERMES_PROFILE` / trusted origin), never a model-supplied author/session.
   - `create_task(...)` existing kwargs stay. Opt-in is `kanban_create(..., collaboration="advisory")` on a **new root** from the trusted originating session only, persisted as a **root task event**. Child creation cannot enable or override. Missing/null keeps legacy behavior.
5. Shared consume interface (CE-HF-CORE implements; CE-HF-DELIVER consumes after CORE is independently reviewed; do not invent a second store):
   - One adjunct table `kanban_collaboration` in the existing board database.
   - One row is an addressed message: explicit request, response, or automatic evidence notice.
   - Required semantics (column/index factoring is local): assigned integer id; root/subject task and source run/event/comment references; source and recipient kind/binding; root contract/version binding; request/response linkage; immutable evidence references; delivery state `pending|queued|acknowledged`; resolution `open|responded|resolved|unavailable|stale`; enqueue/ack/resolution times; bounded delivery lease; deduplication key.
   - Persist comment/event + adjunct row in one native `write_txn`. Unique dedup keys prevent duplicate source-event/recipient messages.
   - Delivery success and a response update different fields. A wake/steer return is only `queued`; `ack`/`respond` is attributable consumption.
   - Recipients: `"origin"` | `"controller"` | exact task id. Routing IDs are runtime-derived from board/root/Project/contract/subscription/affinity. Missing/ambiguous/archived identity returns explicit unavailable/conflict; never current board, profile name alone, or most recent session.
   - Optional `kanban_comment` object (D2): `action=request|respond|ack|resolve` with the fields named in `plan.md` D2. Return includes `{comment_id, collaboration_id, status, recipient_kind}` plus existing `ok/task_id`. IDs are database-assigned.
   - `kanban_show` adds a bounded `collaboration` list with pending/acknowledged/responded/resolved/unavailable state, provenance, and comment/evidence references.
   - Request/response/resolve are idempotent within originating board/root and caller key or referenced message.
   - Unknown keys/actions, truncation sentinels, conflicting binding, unauthorized recipient/response, or secret-containing unsafe payloads follow native validation/redaction **before** mutation.
   - Consumers **must not** reuse `advance_notify_cursor` / the terminal-notification cursor for collaboration. CORE exposes a distinct pending-collaboration claim/list/advance path. DELIVER uses that path only.
   - Controller-recipient records reuse the existing same-affinity `flow_attention` continuation. Tag them as collaboration advisory so attention consumption cannot clear blocked parent dependencies. Do not create a parallel Supervisor, bypass an active lease, or invent a second workspace.
   - Origin-recipient internal delivery is wake-only: no passive human ping per exchange. Gateway successful internal work ends with existing `NO_REPLY` unless a genuine owner decision / material status / unresolved capability needs reporting. TUI uses existing same-session pending/idle continuation and retains the durable message until explicit consumption.
   - Peer content is a labeled native peer-evidence block (trusted role/session/task provenance + cannot expand owner authority). Do not call `agent.steer` with the operator/out-of-band owner wrapper for peer collaboration.
6. Proactive notices (opted-in roots only): enqueue origin advisories on `review_requested`, `changes_requested`, `blocked`, and once on root decomposition completion. Coalesce automatic unconsumed notices for the same root while origin is busy; retain covered source event IDs and the latest summary/reference. Explicit questions are never erased. No notice from ack/response/resolution except the addressed response delivery. No heartbeat/tool/ordinary-comment wake loop. No numeric judge or scheduler.
7. Stale/end-of-flow: terminal flow event, archived execution root, or owner-stopped flow makes unresolved messages stale/unavailable and stops new autonomous wakes; preserve the record. Decomposition root `done` is **not** terminal and must not expire descendant collaboration. A changed run/candidate never silently rebinds old advice. Unavailable origin does not create another session or cross-board route. Completed/stopped tasks are not restarted to manufacture an answer.
8. Do not modify Graphify, lockfiles, live profiles, credentials, providers, models, settings, dispatcher configuration, or repository Actions except the single `policy.yml` manifest line owned by CE-AE-DOCS. Do not absorb #417 or Telegram Monitor work.
9. Testing: identical new tests against unchanged baseline and candidate with already-provisioned dependencies. Causal patch requires baseline RED and candidate GREEN. Aether: `uv run --frozen pytest` on owned tests plus the quickstart resource commands that the unit owns. Fork: `HERMES_TEST_FILE_RETRIES=0` and the candidate interpreter, never the dirty editable install HEAD. `git diff --check` and Ruff on touched Python. No pass-on-retry as proof. No live paid model, live board, production DB, or real credential as fixture. Assert the intended temporary board path before any native writer. Fake delivery sinks prove only their measured mechanical branches and must be labeled as such.
10. Writable-file ownership below is exclusive. Concurrent edits to the same file are forbidden.
11. Do not edit `HERMES_LOCAL_PATCHES.md` or fork `AETHER_FORK.md`. Put the exact ledger paragraph (issue, commit, evidence, scope, upstream relationship, rollback, retirement) in the unit handoff. CE-INT applies the ledgers.
12. Unit evidence path is unique: `specs/collaborative-execution/evidence/<unit-id>.md` (native task attachments for large logs). No secrets, operator paths, credentials, private destinations, or private model responses.
13. Local judgement: private helper names, SQL index factoring, fixture layout, equivalent bounded queue/lease implementation, and whether a new focused fork test module is clearer than extending an owned existing file. Public result shape, D1–D9 semantics, preservation gates, and issue attribution may not vary.
14. Return to Supervisor for a shared-file collision, target-file hash mismatch, a required edit outside this unit's writable surface, a missing material design, or any credential/settings/activation change. Return a genuine design contradiction through Supervisor to Morfeo.
15. Local commit on the unit branch; same-card Supervisor review (`reviewer=supervisor`); no push/PR/merge/issue close from an implementation unit. Unit compatibility evidence is `minor` for compatible optional additions or `patch` for a compatible fix of existing behavior. Aggregate belongs to CE-INT: `release_impact=minor` unless evidence contradicts (then stop for Morfeo); `release_action=defer`; `release_channel=none`.
16. This objective starts on the old runtime (D7). Do not require the new optional arguments to dispatch this graph. Do not retroactively enable collaboration on unrelated historical flows or the stopped monitor.
17. Do not close GitHub issues from an implementation unit.

## Execution graph

```text
t_5fe2c707 (Supervisor decomposition root)
    → CE-HF-CORE     t_07e9bbd7  native store + tool surface (Implementer, Aether worktree + nested fork worktree)
    → CE-AE-RES      t_08cec910  three SOULs + four canonical procedures (Implementer, Aether worktree)
    → CE-AE-DOCS     t_e890e56a  affected normative docs + manifest (Implementer, Aether worktree)
    → CE-HF-DELIVER  t_8edf43f3  TUI/gateway consumers (Implementer; parent-gated on independently reviewed CE-HF-CORE)
    → same-card Supervisor review on each implementation unit
    → CE-INT         t_c815d3a4  terminal integration/closeout/adoption (Supervisor, same flow, terminal=true)
```

CE-HF-CORE, CE-AE-RES, and CE-AE-DOCS are independent: different writable files, different repositories for CORE vs Aether, unique evidence paths. CE-HF-DELIVER is serialized only because it consumes CORE's adjunct table and claim API; that is a real prerequisite, not a false edge. Same-card review is the unit review lane. CE-INT consumes independently reviewed units and does not replace unit review.

Necessary serialization is (1) DELIVER after reviewed CORE and (2) ledger/closeout/adoption (CE-INT).

## CE-HF-CORE — native collaboration store and tool surface

- Source: contract CE-01, CE-02, CE-04, CE-05, CE-07 (attention record), CE-08; plan D1–D4, D5 (comment-bridge labeling and controller attention tag), D9; this unit.
- Outcome: opted-in roots persist exact origin/board/Project/contract binding; legacy roots unchanged. Explicit source-backed request/respond/ack/resolve and proactive lifecycle enqueue work in the same board DB with distinguishable pending/queued/acknowledged and open/responded/resolved/unavailable/stale states. `kanban_show` lists bounded collaboration. Peer inject is labeled non-owner evidence. Controller-recipient advisory cannot unblock parents. Decomposition-root `done` does not expire collaboration. Excludes TUI/gateway consumer loops, Aether SOUL/docs, ledgers, push/PR, activation.
- Inputs: fork `3b81e9d91cc3a0662b910726a44c94ed328b1e90` with the CORE file hashes in Receipt. No prerequisite unit. Shared decisions 1–17. Disposable scrubbed boards/sessions only.
- Boundaries: writable fork `hermes_cli/kanban_db.py`, `tools/kanban_tools.py`, new focused tests `tests/hermes_cli/test_kanban_collaboration.py` and `tests/tools/test_kanban_collaboration.py` (both required unless one file can honestly own both DB and tool oracles; prefer the two paths named by quickstart). May extend `tests/tools/test_kanban_tools.py` only for schema-registration assertions that cannot live in the new module. Preserve `gateway/kanban_watchers.py`, `tui_gateway/server.py`, `AETHER_FORK.md`, and `tests/hermes_cli/test_kanban_session_affinity.py` unless a preservation assertion cannot live in the new module (then stop and flag the hotspot rather than colliding).
- Judgement: SQL column/index factoring; private helper names; whether opt-in is recorded only as a root event after existing `create_task` (preferred) versus an additional internal kwarg that does not change the public `create_task` signature. Do not invent a second comment writer.
- Verification: fail-first on unchanged `3b81e9d` for opt-in, request-before-completion, durable ack/respond/resolve, dedup, truncation/malformed refusal, peer-vs-operator labeling, controller advisory vs parent recovery, root-done vs terminal-flow, and idempotent schema init (quickstart cases 1–3, 6–9 as they apply to store/tools). Candidate: those cases pass using real native SQLite/API functions in disposable environments. Run from the nested candidate with `HERMES_TEST_FILE_RETRIES=0`:
  `python -m pytest -q tests/hermes_cli/test_kanban_collaboration.py tests/tools/test_kanban_collaboration.py`
  `python -m pytest -q tests/tools/test_kanban_tools.py tests/hermes_cli/test_kanban_session_affinity.py`
  Confirm imports resolve to the candidate; `git diff --check`; record interpreter, revision, pass/skip/fail. No live board.
- Dependencies: decomposition root only.
- Completion: local fork commit(s) attributable to #334; evidence `specs/collaborative-execution/evidence/CE-HF-CORE.md`; ledger paragraph in handoff; same-card review; unit compatibility `minor`; no push.

## CE-HF-DELIVER — TUI and gateway collaboration consumers

- Source: contract CE-03 (origin reach), CE-06, CE-07 (no duplicate Supervisor); plan D4–D5; this unit.
- Outcome: for an opted-in root, TUI and gateway process collaboration records independently of the legacy terminal-notification cursor. Exact origin session/chat/thread is used. Busy sessions are not run concurrently. Internal collaboration does not emit a passive human notification per exchange. Ordinary terminal notifications and real escalation remain unchanged. Two origins with identical display names on separate boards never receive each other's notices. Missing/closed origin is visible/unavailable, not rerouted. Excludes store/tool schema, Aether resources, ledgers, push/PR, activation, Telegram Monitor.
- Inputs: independently reviewed CE-HF-CORE at its accepted fork commit (inspect actual adjunct claim/list/advance helpers; do not invent a second table). Fork base remains `3b81e9d` with DELIVER file hashes in Receipt until CORE's candidate is the parent input. Shared decisions 1–17, especially decision 5 consume rules.
- Boundaries: writable fork `gateway/kanban_watchers.py`, `tui_gateway/server.py` **only** on the notification-poller / kanban-sub delivery branch (`_notification_poller_loop`, `_collect_kanban_notifications`, and the analogous gateway mixin path). Writable tests: `tests/gateway/test_kanban_watchers_mixin.py`, `tests/test_tui_gateway_server.py`, `tests/tui_gateway/test_kanban_notify_poller.py`, and/or a new focused `tests/gateway/test_kanban_collaboration_delivery.py` / `tests/tui_gateway/test_kanban_collaboration_poller.py`. Preserve CORE files, `AETHER_FORK.md`, unrelated TUI/gateway features, and notify-sub terminal behavior.
- Judgement: how the independent collaboration cursor is stored (adjunct field vs existing unused column is CORE's; DELIVER only calls the reviewed API); fixture sinks for TUI/gateway without a live dispatcher.
- Verification: fail-first on CORE-less / pre-consumer `3b81e9d` behavior (collaboration never wakes; terminal notify path unchanged). On CORE+DELIVER candidate: quickstart cases 4–5 and the TUI/gateway parts of 6–7 with controlled sinks. Run `HERMES_TEST_FILE_RETRIES=0 python -m pytest -q tests/gateway/test_kanban_watchers_mixin.py tests/test_tui_gateway_server.py tests/tui_gateway/test_kanban_notify_poller.py` plus owned new modules. Confirm no passive ping for internal collaboration; `NO_REPLY` / non-passive path used; notify cursor still handles ordinary terminal events. `git diff --check`. No live Telegram.
- Dependencies: independently reviewed CE-HF-CORE (parent edge) plus decomposition root.
- Completion: local fork commit(s) attributable to #334; evidence `specs/collaborative-execution/evidence/CE-HF-DELIVER.md`; ledger paragraph in handoff; same-card review; unit compatibility `minor`; no push.

## CE-AE-RES — sectorized SOULs and four canonical procedures

- Source: contract CE-09; plan D6 and D7 (bootstrap wording only as procedure text); this unit.
- Outcome: the three existing nine-sector SOULs and the four existing procedures (`objective-contract-design`, `supervisor-decomposition`, `implementation-evidence`, `contract-result-review`) carry D6's authored amendments with equivalent wording, not a second contradictory rule set. Independent review, three-role boundary, owner authority, and early-advice-is-not-final-acceptance remain intact. No new canonical skill and no fourth role. Excludes DESIGN/R6/R7/006/docs/manifest, fork product code, ledgers, push/PR, activation.
- Inputs: Aether `183bd7a4944a5db7d22091c402a74383a80100fa` with resource hashes:
  `src/aether_agents/resources/profiles/morfeo/SOUL.md` `0977c1ebcd284b89c8ccd07473276bdeeb7926bedcf3d29039951d5195b78a09`,
  `.../supervisor/SOUL.md` `910f3464f5ffda8ac1a84ff18725ccd9c2806c97ba169af0a0e7ba93db24bb94`,
  `.../implementer/SOUL.md` `01df686e8070e12bc8a29bdc587446c51195c64f8c590c4f4fca3e3acdffde7b`,
  `.../skills/objective-contract-design/SKILL.md` `f263de3ec462fb7060f9037bf4974ff40bdeb292d568b1cde151edb3694c64d2`,
  `.../skills/supervisor-decomposition/SKILL.md` `0361e44ccd0fdce3fdb7fbe46ed0d84e9b186d05aa1be08cf7cc82d988690021`,
  `.../skills/implementation-evidence/SKILL.md` `e6104a0fe2520f607c322a9227f3f4c7174124dc36e163c84d3af39fae857d0f`,
  `.../skills/contract-result-review/SKILL.md` `75883a60482207994706e55193f2a71192a2ad422560c441aa6eaf58ef6f9cf6`.
  Apply D6's three quoted amendments in the named sectors. Keep skill versions `0.1.1` (supervisor-decomposition) and `0.1.0` (others) so packaging tests stay coherent; do not bump versions in this unit.
- Boundaries: writable the seven resource files above, `tests/test_contract_quality_documents.py`, `tests/test_contract_result_review.py`. Preserve `tests/test_observation_packaging.py`, `tests/test_observation_lifecycle.py`, `tests/test_observation_cli_plugin.py`, DESIGN/docs, `policy.yml`. If a required phrase change would break packaging version pins, keep the versions and adjust only this unit's owned tests.
- Judgement: exact insertion points inside existing sectors; examples of request/response/disposition in the four skills without pasting the whole Objective Contract.
- Verification: resource tests still distinguish documents from behavior. `uv run --frozen pytest -q tests/test_contract_quality_documents.py tests/test_contract_result_review.py`; ruff/format on touched Python if any; `git diff --check`. Confirm nine-sector headings remain and D6 sentences (or equivalent) are present. No model call.
- Dependencies: decomposition root only.
- Completion: local Aether commit; evidence `specs/collaborative-execution/evidence/CE-AE-RES.md`; same-card review; unit compatibility `minor`; no push.

## CE-AE-DOCS — normative docs, #317 disposition, canonical manifest

- Source: contract CE-09 (docs agreement), CE-10 (manifest/lifecycle docs only), CE-12 (honest #317/#407 wording in docs); plan D6 (PD-77/FR-714e distinction) and D7; this unit.
- Outcome: `DESIGN.md`, affected R6/R7 (and R1/R2/006 only where they currently imply terminal-only origin routing or #317 as an open-ended gate), `AGENTS.md`, `docs/guides/execution.md`, and capability traceability distinguish internal Morfeo collaboration from owner-facing notifications, and they no longer treat #317 as an open observation gate. Historical evidence and unverified-behavior limits remain explicit. Canonical base manifest gains the new Objective Contract path in sorted position. Excludes SOUL/skill files, fork product code, ledgers, issue close comments, push/PR, activation.
- Inputs: Aether `183bd7a4944a5db7d22091c402a74383a80100fa`. Shared D6/D7 wording. Preserve FR-736b convergence phrases already asserted by `tests/test_contract_quality_documents.py` (owned by CE-AE-RES): do not delete those strings from `specs/r7-supervision-and-convergence/spec.md`.
- Boundaries: writable `DESIGN.md`, `AGENTS.md`, `docs/guides/execution.md`, `docs/capabilities.toml`, `docs/reference/capabilities.md`, `docs/roles-and-authority.md` only if it currently states the affected terminal-only rule, `specs/r6-protocol-and-communication/spec.md`, `specs/r7-supervision-and-convergence/spec.md` (FR-714e distinction only), `specs/r1-foundation-and-roles/spec.md` and `specs/r2-contract-and-handoff/spec.md` only if a matching sentence exists, `specs/006-contract-execution-quality/spec.md` (and its `plan.md`/`quickstart.md` only for the #317 gate sentence), `tests/test_documentation.py`, `.github/workflows/policy.yml` (add `.aether/objective-contracts/oc_a28ff9b7fa20d29d/v1.md` to the literal manifest in sorted order; never a glob). Preserve SOUL/skills, `tests/test_contract_quality_documents.py`, observation CLI digest tests, `HERMES_LOCAL_PATCHES.md`.
- Judgement: whether an R1/R2 file actually contains an affected sentence (record non-applicability if not). Exact PD-77 wording that keeps owner-facing silence for ordinary milestones while allowing internal collaboration.
- Verification: `uv run --frozen pytest -q tests/test_documentation.py tests/test_contract_quality_documents.py` (the latter must still pass because FR-736b phrases are preserved); `uv run --frozen python scripts/check_documentation.py`; emulate the policy.yml canonical-base-manifest step on the candidate tree; `git diff --check`. No organic PASS claim in the edited docs.
- Dependencies: decomposition root only.
- Completion: local Aether commit; evidence `specs/collaborative-execution/evidence/CE-AE-DOCS.md`; same-card review; unit compatibility `minor`; no push.

## CE-INT — integration, dual-repo closeout, adoption

- Source: contract CE-10..CE-12, deliverables, testing standard section 3–4; plan steps 4–6; `docs/guides/execution.md`; this unit.
- Outcome: independently reviewed units are integrated without squashing unit attribution. Maintained-fork PR merges through its normal path first (fork Actions disabled means NOT RUN, never green). Aether ledger/patch evidence updated from unit paragraphs. Principal Aether PR merges through required checks without bypass. Scoped runtime adoption with rollback, installed-byte and schema/load readback, no worker interrupt. Compact criterion matrix under `specs/collaborative-execution/evidence/`. #334 and #317 close with explicitly unverified long-term efficacy; #407 gets a linked mitigation note without rewriting history. Objective-owned residue cleaned after durable evidence; unrelated work and the stopped monitor preserved. Separate `release_impact` / `release_action=defer` / `release_channel=none`.
- Inputs: independently reviewed CE-HF-CORE, CE-HF-DELIVER, CE-AE-RES, CE-AE-DOCS plus this root. Shared decisions 1–17. Adoption uses the existing PR8/HLP-362 reconciliation workflow and `hermes-runtime-activation-canary`. If gateway replacement would kill this Supervisor worker, park with a durable recipe and request the already-authorized Morfeo cutover through the native origin path in a verified zero-worker window; do not self-restart.
- Boundaries: integration-owned conflict/import/wiring/path/`policy.yml` allowlist repairs that introduce no new behavior; `HERMES_LOCAL_PATCHES.md`; fork `AETHER_FORK.md`; `specs/collaborative-execution/evidence/` integrated matrix/report; normal GitHub closeout in `DarkArty07/Aether-Agents` and `DarkArty07/aether-hermes`. Behavior gaps return as implementation rework. Do not repair #417. Do not restart Telegram Monitor. Do not force-push, bypass checks, publish packages, or tag a release.
- Judgement: bounded integration repairs only when mechanically implied. Classify `release_impact` from inspected compatibility evidence (plan's provisional `minor` is a hypothesis, not a result).
- Verification: quickstart sections 2–4 on the integrated candidate; required Aether checks (`pull-request-target` and `policy` are the required contexts; inherited reds on main stay inherited); fork focused suites at the merged SHA; installation hash/schema readback without a model call; issue/residue audit. Record commands/results/limits in the matrix.
- Dependencies: decomposition root and all four independently reviewed implementation units. `terminal=true` same-flow Supervisor card.
- Completion: dual merged PRs, issue reconciliation, adoption/rollback evidence, owned-residue cleanup, terminal report with the three release conclusions. Not owner-objective acceptance (Morfeo reception remains after this card).
