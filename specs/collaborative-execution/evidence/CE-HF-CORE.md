# Implementation Evidence — Unit CE-HF-CORE

**Status:** Complete and verified. Candidate implemented in an isolated nested worktree of the maintained fork repository (`DarkArty07/aether-hermes`). All unit and regression tests pass deterministically. Ready for same-card Supervisor review.

- **Unit ID:** `CE-HF-CORE`
- **Task ID:** `t_07e9bbd7`
- **Issue:** [#334](https://github.com/DarkArty07/Aether-Agents/issues/334)
- **Objective Contract:** `oc_a28ff9b7fa20d29d@v1` (SHA-256 `7a51dc2b3d2d62788b1228f823f9def58652e48d48fcecaecb5293f34dde7de5`)
- **Review lane:** Same-card Supervisor review (`kanban_request_review`, `reviewer="supervisor"`)
- **Unit compatibility impact:** `minor` (additive optional arguments, additive backward-compatible adjunct table, legacy behavior preserved)

## 1. Repository identity and scope

| Tree | Revision / identity | Evidence |
| --- | --- | --- |
| Maintained fork baseline | `DarkArty07/aether-hermes` `aether-main` `3b81e9d91cc3a0662b910726a44c94ed328b1e90` | Verified before mutation (`git rev-parse`) |
| Baseline `hermes_cli/kanban_db.py` SHA-256 | `8e0e359e0e86200051069d02ca8ca7be44d1e594dca89ec8e118c7e68ab2e857` | Matches Receipt / task contract |
| Baseline `tools/kanban_tools.py` SHA-256 | `5648e720d37e91898acff2e137dff184230cacc8217fba420526b33bd37a5179` | Matches Receipt / task contract |
| Maintained fork candidate | `20db06c0b8441190830aa72e3c0de6fdce6b8db4` | Nested isolated worktree on branch `feat/334-native-collaboration-core` |
| Candidate `hermes_cli/kanban_db.py` SHA-256 | `a8e1fe3d33696b126fe04833996a79ff250885315899c721a11de8e1619ec617` | Re-measured after review corrections commit |
| Candidate `tools/kanban_tools.py` SHA-256 | `b6fe9f571f7152d986b120655cdd804fc575ebfdaab42e9b0fdb5886b6b4eedf` | Re-measured after review corrections commit |
| Candidate import | Resolved directly to candidate worktree | `python -c "import hermes_cli.kanban_db, tools.kanban_tools..."` resolved to `.worktrees/hermes-ce-hf-core` |

The permitted fork change is strictly limited to `hermes_cli/kanban_db.py`, `tools/kanban_tools.py`, `tests/hermes_cli/test_kanban_collaboration.py`, and `tests/tools/test_kanban_collaboration.py`. `gateway/kanban_watchers.py`, `tui_gateway/server.py`, `AETHER_FORK.md`, and `HERMES_LOCAL_PATCHES.md` were preserved untouched.

## 2. Technical judgement and changes implemented

1. **Adjunct collaboration table in board DB (`hermes_cli/kanban_db.py`):**
   - `SCHEMA_SQL`: defines table `kanban_collaboration` and indexes over `root_task_id`, `task_id`, `(recipient_kind, delivery_state)`, `request_id`, and `lease_expires`.
   - Additive migration: idempotent `CREATE TABLE IF NOT EXISTS` and index creation runs during `connect()` without altering or rebuilding existing tables.
2. **Root opt-in and descendant binding (`hermes_cli/kanban_db.py`, `tools/kanban_tools.py`):**
   - `opt_in_collaboration`: verifies root status (parents empty), reads `board.json` metadata via `_read_board_meta_for_conn` to populate `contract_id`, `contract_version`, and `project_id` when not passed explicitly; writes `collaboration_opted_in` event on the root with mode `advisory` and provenance.
   - `get_collaboration_root`: traverses upward through `task_links`. If a unique opted-in ancestor root exists with matching project, returns that root id. Fails closed (`None`) on mixed roots, foreign projects, or archived roots (unless `allow_archived=True`).
   - `kanban_create`: accepts `collaboration="advisory"` only on new roots from the trusted originating session; rejects child opt-in (`tool_error`); propagates board name to `opt_in_collaboration`.
3. **Request/respond/ack/resolve lifecycle (`hermes_cli/kanban_db.py`, `tools/kanban_tools.py`):**
   - `create_collaboration_request`: validates root binding, recipient existence/availability, idempotency key. Persists comment via `add_comment` and writes pending collaboration row atomically in `write_txn`. Persists `source_run_id` resolved via `_resolve_source_run_id` from explicit argument, environment (`HERMES_KANBAN_RUN_ID`), or task record. If recipient is `"controller"`, enqueues `flow_attention` tagged as collaboration advisory and promotes controller to `ready` if waiting.
   - `create_collaboration_response`: validates open request, adds response comment, inserts response row addressed back to requester with persisted `source_run_id`, and transitions request resolution to `responded`.
   - `advance_collaboration_message`: transitions delivery state (e.g. to `acknowledged`) and clears lease tokens.
   - `resolve_collaboration_request`: records resolution comment and transitions resolution to `resolved`.
   - `kanban_comment`: exposes optional `collaboration` object (`action` in `request`, `respond`, `ack`, `resolve`). Validates allowed keys and dispatches to DB methods with caller run id passed through. Returns structured dict `{ok, task_id, comment_id, collaboration_id, status, recipient_kind}`.
4. **Consumer claim API and bounded leases (`hermes_cli/kanban_db.py`):**
   - `claim_collaboration_messages`: reclaims expired queued leases (`lease_expires < now` without ack), claims pending messages under a token and lease TTL, transitions state `pending -> queued`.
   - `list_pending_collaboration`: returns pending and queued rows for consumers.
   - `list_collaboration_for_task`: returns bounded rows for `kanban_show`.
   - `kanban_show`: surfaces `collaboration` list in task inspection output.
5. **Proactive lifecycle notices and coalescing (`hermes_cli/kanban_db.py`):**
   - `_enqueue_lifecycle_collaboration_notice`: enqueues origin notice for opted-in roots with `contract_id`, `contract_version`, and `source_run_id`. If an unconsumed automatic notice is pending/queued, coalesces summaries and covered event references instead of spamming rows. Explicit requests are never coalesced.
   - Hooked in `request_review`, `request_changes`, `block_task`, and `complete_task` for decomposition root completion.
6. **Controller flow attention isolation (`hermes_cli/kanban_db.py`):**
   - `_resolve_flow_attention`: checks `attention.get("collaboration_advisory")`. If set, resolves attention without altering or unblocking blocked parent tasks.
   - `build_worker_context`: labels collaboration advisory attention distinctly under `## Flow collaboration advisory` with role-specific instruction and omits parent-recovery / capability-block recipes.
7. **Stale and flow expiration (`hermes_cli/kanban_db.py`):**
   - `_expire_collaboration_for_flow`: marks unresolved collaboration messages `stale` using `get_collaboration_root(conn, task_id, allow_archived=True)`. Called on `flow_terminal` and when archiving an execution root in `archive_task`.
   - `archive_task`: calls `_expire_collaboration_for_flow` on opted-in root; ensures `get_collaboration_root` fails closed for archived roots/children while marking open requests `stale`.
   - Decomposition root completion (`complete_task`) completes without emitting `flow_terminal` and does not call `_expire_collaboration_for_flow`, preserving descendant collaboration.
8. **Truncation sentinel and peer evidence guards (`tools/kanban_tools.py`):**
   - `_has_truncation_sentinel`: detects trailing terminal truncation markers (`[truncated]`, `...[truncated]`, `…[truncated]`). Refuses comment before persistence.
   - `inject_new_comments_from_env`: formats peer comments as `[PEER COLLABORATION EVIDENCE - Role: <author>]...[/PEER COLLABORATION EVIDENCE]`, explicitly stating non-owner informative evidence. Never uses the operator out-of-band message wrapper.
9. **Test isolation and negative control (`tests/hermes_cli/test_kanban_collaboration.py`, `tests/tools/test_kanban_collaboration.py`):**
   - Both test fixtures scrub `HERMES_KANBAN_DB`, `HERMES_KANBAN_BOARD`, `HERMES_KANBAN_TASK`, `HERMES_KANBAN_RUN_ID`, and `HERMES_KANBAN_WORKSPACES_ROOT`.
   - Explicit `assert_isolated_db_path` verifies the resolved DB path is strictly under the temporary fixture root before any native writer runs.
   - Negative control test `test_board_isolation_and_env_pin_rejection` proves that leftover pins outside the temporary root are rejected by the isolation check.

## 3. Requirement to test oracle mapping

| Req ID | Requirement Description | Verification check & file | Observed result | Status |
| --- | --- | --- | --- | --- |
| CE-01 | Opt-in root binding; legacy roots unchanged; mixed/foreign roots reject | `test_opt_in_binding_and_ancestor_inheritance`, `test_mixed_root_and_unrelated_project_rejection`, `test_kanban_create_collaboration_opt_in_and_child_refusal`, `test_opt_in_persists_contract_binding_from_board_metadata` in `tests/hermes_cli/test_kanban_collaboration.py` & `tests/tools/test_kanban_collaboration.py` | Opt-in recorded on root event; children inherit root id; legacy root returns `None`; mixed roots & foreign projects fail closed; contract id/version loaded from board.json metadata | **PASS** |
| CE-02 | Explicit request before completion; task claim/status preserved | `test_request_respond_ack_resolve_lifecycle` in `tests/hermes_cli/test_kanban_collaboration.py` | Source task remains `running`; sibling claims and runs independently; request row created | **PASS** |
| CE-03 | Proactive notices on lifecycle events; coalescing while origin unconsumed | `test_proactive_lifecycle_notices_and_coalescing` in `tests/hermes_cli/test_kanban_collaboration.py` | `review_requested` enqueues notice; `changes_requested` coalesces into same row; explicit request uncoalesced | **PASS** |
| CE-04 | Distinguishable pending/queued/ack and open/responded/resolved states; leases & redelivery; source_run_id persistence | `test_request_respond_ack_resolve_lifecycle`, `test_idempotency_and_dedup`, `test_claim_lease_expiration_and_recovery`, `test_source_run_id_persistence`, `test_kanban_tools_contract_metadata_and_source_run_id` in `tests/hermes_cli/test_kanban_collaboration.py` & `tests/tools/test_kanban_collaboration.py` | Lease recovery from expired queued -> pending verified; ack sets `acknowledged_at`; resolve sets `resolved_at`; dedup keys prevent duplicates; source_run_id populated from explicit arg and env | **PASS** |
| CE-05 | Peer evidence labeling; rejection of truncation sentinels & malformed metadata | `test_kanban_comment_truncation_sentinel_refusal`, `test_kanban_comment_malformed_metadata_refusal`, `test_inject_new_comments_peer_labeling_not_operator_wrapper` in `tests/tools/test_kanban_collaboration.py` | Sentinels refused before write (0 rows written); malformed metadata rejected; peer block injected without owner wrapper | **PASS** |
| CE-07 | Controller flow attention tagged as advisory; never unblocks parents; advisory worker_context | `test_controller_flow_attention_collaboration_advisory`, `test_controller_worker_context_collaboration_advisory` in `tests/hermes_cli/test_kanban_collaboration.py` | Controller receives `flow_attention` with `collaboration_advisory=True`; resolving attention leaves parent task `blocked`; worker_context labels advisory and omits recovery recipe | **PASS** |
| CE-08 | Root-done preserves collaboration; flow_terminal/archive expires stale | `test_root_done_preserves_collaboration_vs_terminal_flow_expires`, `test_archive_task_expires_collaboration_to_stale` in `tests/hermes_cli/test_kanban_collaboration.py` | Decomp root `done` keeps child collaboration active; flow terminal and `archive_task` on root transition unresolved rows to `stale`; get_collaboration_root fails closed after archive | **PASS** |
| D9 | Idempotent schema initialization; isolation safety guard | `test_schema_initialization_and_idempotence`, `test_board_isolation_and_env_pin_rejection` in `tests/hermes_cli/test_kanban_collaboration.py` | `kanban_collaboration` created on fresh DB; repeated connect runs cleanly; HERMES_KANBAN_DB pin outside tmp root rejected | **PASS** |

## 4. Verification commands and receipts

Environment: Python 3.11.15, `uv` managed venv in `.worktrees/hermes-ce-hf-core/.venv`, `HERMES_TEST_FILE_RETRIES=0`.

1. **Fail-first baseline check (on unchanged `3b81e9d91cc3a0662b910726a44c94ed328b1e90`):**
   ```text
   $ HERMES_TEST_FILE_RETRIES=0 .venv/bin/python -m pytest -q tests/hermes_cli/test_kanban_collaboration.py tests/tools/test_kanban_collaboration.py
   .FFFFFFFFFFFFFFFFFF.FFF
   21 failed, 2 passed in 1.45s
   ```
   (The 2 passed are `test_board_isolation_and_env_pin_rejection` fixture safety test and `test_author_cannot_be_forged_by_caller`).

2. **Candidate focused test suite execution (at `20db06c0b8441190830aa72e3c0de6fdce6b8db4`):**
   ```text
   $ HERMES_TEST_FILE_RETRIES=0 .venv/bin/python -m pytest -q tests/hermes_cli/test_kanban_collaboration.py tests/tools/test_kanban_collaboration.py
   .......................
   23 passed in 1.83s
   ```

3. **Regression suites execution:**
   ```text
   $ HERMES_TEST_FILE_RETRIES=0 .venv/bin/python -m pytest -q tests/tools/test_kanban_tools.py tests/hermes_cli/test_kanban_session_affinity.py
   ........................................................................ [ 91%]
   .......                                                                  [100%]
   79 passed in 8.44s
   ```

4. **All four suites combined:**
   ```text
   $ HERMES_TEST_FILE_RETRIES=0 .venv/bin/python -m pytest -q tests/hermes_cli/test_kanban_collaboration.py tests/tools/test_kanban_collaboration.py tests/tools/test_kanban_tools.py tests/hermes_cli/test_kanban_session_affinity.py
   ........................................................................ [ 70%]
   ..............................                                           [100%]
   102 passed in 9.79s
   ```

5. **Code formatting and linting:**
   ```text
   $ git diff --check 3b81e9d91cc3a0662b910726a44c94ed328b1e90...HEAD (exit code 0, 0 output)
   $ .venv/bin/ruff check hermes_cli/kanban_db.py tools/kanban_tools.py tests/hermes_cli/test_kanban_collaboration.py tests/tools/test_kanban_collaboration.py
   All checks passed!
   ```

## 5. Ledger paragraph for CE-INT handoff

```markdown
### HLP-334: Native collaboration store, tool surface, and non-owner peer evidence labeling
- **Status:** Candidate implemented in maintained fork at commit `20db06c0b8441190830aa72e3c0de6fdce6b8db4`.
- **Issue:** [Aether #334](https://github.com/DarkArty07/Aether-Agents/issues/334).
- **Objective Contract:** `oc_a28ff9b7fa20d29d@v1` (SHA-256 `7a51dc2b3d2d62788b1228f823f9def58652e48d48fcecaecb5293f34dde7de5`).
- **Files touched:** `hermes_cli/kanban_db.py`, `tools/kanban_tools.py`, `tests/hermes_cli/test_kanban_collaboration.py`, `tests/tools/test_kanban_collaboration.py`.
- **Scope & Behavior:** Adds `kanban_collaboration` adjunct table to SQLite board DB for opted-in roots with explicit request/respond/ack/resolve lifecycle via `kanban_comment`, root task opt-in (`collaboration="advisory"`) in `kanban_create` persisting canonical board/Project/contract bindings from `board.json`, distinct pending collaboration claim/list/advance consumer API with bounded leases, proactive lifecycle notices on `review_requested`, `changes_requested`, `blocked`, and root decomposition completion, controller flow attention tagged as collaboration advisory (never unblocking parents) with dedicated advisory worker context, task archiving expiring unresolved collaboration to stale, persistence of source run id on requests/responses/notices, truncation sentinel refusal before write, and labeled peer evidence blocks in comment injection.
- **Upstream Relationship:** Downstream enhancement to Hermes Agent kanban coordination; maintains 100% backward compatibility for legacy roots and ordinary comments.
- **Rollback:** Restore pre-image files from `3b81e9d91cc3a0662b910726a44c94ed328b1e90`. Board database migration is additive (`CREATE TABLE IF NOT EXISTS`); existing tasks and comments remain unaffected.
- **Maintenance / Retirement:** Retain while Aether contracts use active multi-role collaboration; candidate for upstream contribution if Nous adopts structured inter-agent collaboration.
```

## 6. Shared decisions stamped from tasks.md

1. **Authority:** Objective Contract `oc_a28ff9b7fa20d29d@v1` (SHA-256 `7a51dc2b3d2d62788b1228f823f9def58652e48d48fcecaecb5293f34dde7de5`).
2. **Dual-repo baseline:** Fork product edits start from isolated nested worktree of `DarkArty07/aether-hermes` at `3b81e9d91cc3a0662b910726a44c94ed328b1e90`. Live runtime, `aether-main`, and `home/` untouched.
3. **Target file re-hash:** Verified at baseline and candidate; all hashes recorded in section 1.
4. **Preserved native signatures:** `kanban_comment` remains `(task_id, body, board)`; `add_comment` remains `(conn, task_id, author, body) -> int`; author is runtime-derived; `create_task` signatures preserved with root opt-in event.
5. **Shared consume interface:** One adjunct table `kanban_collaboration` in board DB with required semantics, distinct claim/list/advance helpers, bounded delivery leases, flow attention tagged as collaboration advisory, and peer evidence labeled block.
6. **Proactive notices:** Enqueued on `review_requested`, `changes_requested`, `blocked`, and once on root decomposition completion; coalesced while origin unconsumed; explicit questions never erased.
7. **Stale/end-of-flow:** `flow_terminal` and archived roots expire collaboration to `stale`; decomposition root `done` preserves descendant collaboration.
8. **Scope containment:** No edits to Graphify, live profiles, lockfiles, credentials, or Telegram monitor.
9. **Testing:** Disposable scrubbed boards only; fail-first RED then candidate GREEN; no pass-on-retry.
10. **Exclusive file ownership:** Touched only fork CORE files and unique evidence file.
11. **Ledgers:** Ledgers not edited directly; exact paragraph provided for CE-INT.
12. **Unique evidence path:** `specs/collaborative-execution/evidence/CE-HF-CORE.md`.
13. **Local judgement:** SQL index factoring, helper names, and test module layout documented.
14. **No material collision:** No stop conditions encountered.
15. **Review lane:** Local commit; requesting same-card Supervisor review (`reviewer="supervisor"`); unit compatibility `minor`; no push/PR/merge.
16. **No retroactive migration:** Legacy boards and historical flows preserved unchanged.
17. **No issue close:** Issue #334 remains open for CE-INT closeout.
