# Index of local Hermes patches

**Status:** canonical operational record of the functional differences that Aether maintains over its loaded Hermes.

This file prevents a Hermes update from silently removing local repairs. An Aether issue may be closed because the effective runtime is fixed, even though its entry remains `ACTIVE_LOCAL` until an equivalent upstream revision is integrated and verified.

## Reference runtime

- Hermes: `0.20.1`
- Base revision: `411903b6fa258f81afcc3869eb615f6218e1776a`
- Editable source loaded by Aether: `home/.venv-hermes/src/hermes-agent`
- Service that must be reloaded after modifying the runtime: `hermes-gateway.service`
- Last reconciliation of this index: `2026-08-21 UTC`

## States

- `ACTIVE_LOCAL`: the repair is present and Aether depends on it.
- `UPSTREAM_OPEN`: an upstream issue or PR exists, but it is not yet part of a revision published and qualified by Aether.
- `UPSTREAM_VERIFIED`: the target revision already contains equivalent behavior and passed this entry's acceptance matrix.
- `RELOAD_PENDING`: local code and configuration are written and tested in a new process, but the service process has not yet reloaded them.
- `RETIRED`: the local patch was removed after proving upstream equivalence and revalidating the effective runtime.

## Operational record (active and pending reload)

| ID | Aether issue | Local repair | Upstream tracking | Status |
|---|---|---|---|---|
| `HLP-188` | `#188` | `initial_status=blocked` remains blocked until an explicit unblock | PR `NousResearch/hermes-agent#91180` | `ACTIVE_LOCAL / UPSTREAM_OPEN` |
| `HLP-189` | `#189` | `kanban_create` exposes, validates, and persists `max_retries` | PR `NousResearch/hermes-agent#89590` | `ACTIVE_LOCAL / UPSTREAM_OPEN` |
| `HLP-191` | `#191` | a loop/`needs_input` escalation remains human-gated and does not automatically return to work | PR `NousResearch/hermes-agent#91211`; the explicit local recovery CLI is not included in that PR | `ACTIVE_LOCAL / UPSTREAM_OPEN` |
| `HLP-194` | `#194` | a worker requires exactly one successful, durable terminal handoff | PR `NousResearch/hermes-agent#91220` | `ACTIVE_LOCAL / UPSTREAM_OPEN` |
| `HLP-198` | `#198` | the first worktree spawn receives the already-resolved effective branch | issue `NousResearch/hermes-agent#89677`; PR `#89688` | `ACTIVE_LOCAL / UPSTREAM_OPEN` |
| `HLP-204` | `#204`, `#205` | shared profile-asymmetric limits applied to ready/review; initial topology Supervisor 1 / Implementer 3 | issue `NousResearch/hermes-agent#91259`; PR `#91266` | `ACTIVE_LOCAL / UPSTREAM_OPEN` |
| `HLP-209` | no new issue/PR; `#209` retains only the prior downstream trace | directories discovered by the walker are not treated as unsafe scripts; devices and actual scripts remain fail-closed | upstream issue `#86753`; integrated commit `9ac1e65b0ae4e83dced9d5c8a406cc57cb589702` | `ACTIVE_LOCAL / UPSTREAM_VERIFIED` |
| `HLP-211` | `#211` | opt-in affinity resumes an exact worker session within a Project/flow/profile and canonical workspace, with lease/generation fencing, Supervisor control of blockers, and terminal/escalated return to the origin | Hermes `#75830`, `#59855`, `#68779`, `#71175`; PR `#75951` covers only block→unblock of the same card; local `HLP-211b` extension still has no issue/PR | `ACTIVE_LOCAL + HLP-211b CANDIDATE / UPSTREAM_PARTIAL` |
| `HLP-226` | `#226` | a cross-profile child with `workspace_kind=worktree` inherits the worker's canonical Project and receives its own worktree, even from a terminal affinity card that shares the root worktree as `dir` | upstream commit `b9b5481d6` covers the direct worktree source; local `HLP-226b` extension has no equivalent | `ACTIVE_LOCAL + HLP-226b / UPSTREAM_PARTIAL` |
| `HLP-246` | `#246` | attachments validate identity before transport and readback; they persist the computed size and SHA-256 | no equivalent found in `origin/main` | `ACTIVE_LOCAL / UPSTREAM_MISSING` |
| `HLP-262` | `#262` | a non-dependency block that emits `origin_signal` remains sticky until explicit resolution/unblock | no equivalent in `NousResearch/hermes-agent@4f2254350` | `ACTIVE_LOCAL / UPSTREAM_MISSING` |
| `HLP-263` | `#263` | terminal and direct CLI guards use actual supervised-gateway ownership, not inherited markers | PR `NousResearch/hermes-agent#93267`, issue `#92560`, tip `aa9aaaa6cb31753c3b274db6825fbd0af5f27120` | `ACTIVE_LOCAL / UPSTREAM_VERIFIED` |
| `HLP-305` | `#305` | transient SQLite contention during a turn-lease refresh is retried only while the current TTL leaves a complete retry budget; a confirmed lease miss or non-transient failure still interrupts | no equivalent in `NousResearch/hermes-agent@4810074d73d9419dc82545202d595507a73f4f0e` | `RELOAD_PENDING / UPSTREAM_MISSING` |
| `HLP-310` | `#310` | reusable terminal snapshots exclude `HERMES_DELEGATED_CHILD_CONTEXT` and `HERMES_KANBAN_*` | no equivalent in `NousResearch/hermes-agent` at contract inspection | `ACTIVE_LOCAL / UPSTREAM_MISSING` |
| `HLP-354` | `#354` | new-branch Kanban worktrees start at a valid board `worktree_base_ref` instead of incidental `HEAD` | no equivalent in `NousResearch/hermes-agent` at contract inspection | `ACTIVE_LOCAL / UPSTREAM_MISSING` |
| `HLP-369` | `#369` | review readiness is distinct from final approval; native controller resume retains pending recovery attention | equivalent absent in inspected upstream `1675f1f2c25ce164f07c42e829f2c17a723db94f` and maintained-fork source | `LOCAL_CANARY_GREEN / NATIVE_REVIEW_REACHED` |

### HLP-369 — bounded review-flow recovery

- **Reason:** a goal-mode candidate could not request independent review because the judge demanded that future approval; subsequent recovery parked its controller behind the very parent it had to resume.
- **Scope:** `tools/kanban_tools.py` and `hermes_cli/kanban.py` provide review-readiness context only for `request_review`. `hermes_cli/kanban_db.py:unblock_task` preserves the native pending-attention exception already honored by claim/recovery; ordinary todo children remain rejected/gated. No judge disabling or completion bypass.
- **Evidence:** `tests/hermes_cli/test_goal_review_phase_recovery.py` plus review-surfaces, session-affinity and sticky-blocking suites: 53 passed. Controller regression first failed with `todo != ready`. Existing concurrent runtime edits were preserved; the exact local pre-change bytes were backed up before editing. No new service, schema, provider or dependency.
- **Activation:** fresh processes import the local repair; already-running TUI/gateway-cron callers retain old modules. A fresh Morfeo CLI process invoked the native unblock tool once, and durable board readback confirmed the controller reached ready and then running. No worker-killing restart, board CLI mutation or direct SQLite update. Actual configured judge accepted review readiness on the real card without mutating it; 54 focused tests now cover stale-caller todo as well as blocked controller recovery and normal-child refusal. The real previously failing MON-02 handoff subsequently reached native `review` assigned to Supervisor, ending bounded recovery. This is not MON-02 independent approval or full product delivery. The block-kind/origin-signal mismatch is not repaired by this patch.
- **Rollback:** restore only the three backed-up file hunks introduced by #369 and remove only its new regression file; never replace other concurrent uncommitted runtime changes. The original pre-change snapshot has private checksums. If the two focused repairs cannot recover the canary, restore that baseline and stop.
- **Retirement:** remove after the exact maintained/release runtime without this patch passes review-readiness rejection/acceptance, ordinary parent-gating, controller recovery and real independent-review canaries. No upstream PR or package release was made in recovery.


## HLP-188 — sticky `initial_status=blocked`

- **Reason:** dispatcher recomputation could promote a card created as blocked without an explicit `unblock`.
- **Primary active files:**
  - `hermes_cli/kanban_db.py`
  - `tests/hermes_cli/test_kanban_blocked_sticky.py`
- **Local evidence:** focused base/tool tests and a post-restart probe with temporary processes and SQLite; the state changed only through explicit `unblock_task`.
- **Upstream:** <https://github.com/NousResearch/hermes-agent/pull/91180>, open and mergeable; required checks were green when this index was reconciled.
- **Retirement gate:** create a card with `initial_status="blocked"` on the target revision, run recomputation, resolve dependencies, reopen the database in another process, and demonstrate that only an explicit unblock moves it to `ready`.

## HLP-189 — `max_retries` in `kanban_create`

- **Reason:** CLI and database supported the field, but the tool available to workers neither exposed nor transmitted it.
- **Primary active files:**
  - `tools/kanban_tools.py`
  - `tests/tools/test_kanban_tools.py`
- **Local evidence:** `8 passed`; Ruff and diff green; one process created a card through the real handler with `max_retries=3`, and another process reopened SQLite and verified the persisted value.
- **Upstream:** <https://github.com/NousResearch/hermes-agent/pull/89590>, open and mergeable, with no checks reported when this index was reconciled.
- **Retirement gate:** verify on the target revision that the `kanban_create` schema exposes an integer with minimum `1`, that the handler transmits it, and that another process observes the same persisted value.

## HLP-191 — human-gated escalations

- **Reason:** a card escalated by a block loop could return to auto-decomposition or redispatch without explicit human recovery.
- **Primary active files:**
  - `gateway/kanban_watchers.py`
  - `hermes_cli/kanban_db.py`
  - `hermes_cli/kanban_decompose.py`
  - `hermes_cli/kanban.py`
  - `tests/hermes_cli/test_kanban_decompose.py`
  - `tests/hermes_cli/test_kanban_cli.py`
  - `tests/gateway/test_kanban_auto_decompose_recovery.py`
- **Additional local difference:** `hermes kanban unblock --recover-escalated` can no longer recognize an escalation while the card remains in `triage`. Recovery is recorded only after an explicit routing/decomposition action has moved it out of `triage`; therefore, acknowledging the block does not authorize work or expose the card to the auto-decomposer. This CLI surface does not appear in the upstream PR `#91211` files and must be verified separately on update.
- **Local evidence:** `19 passed` in the focused CLI, decomposition, and watcher suites; Ruff and `git diff --check` green. A probe with three independent processes and a temporary DB confirmed: `status=triage`, active escalation, `block_recurrences=2`, no `triage_escalation_recovered` event, and `auto_listed=false` after the premature acknowledgement attempt.
- **Upstream:** <https://github.com/NousResearch/hermes-agent/pull/91211>, open and mergeable, with no checks reported when this index was reconciled.
- **Retirement gate:** test escalation, reconnection, reassignment, and the auto-decomposition tick; then test that premature recovery in `triage` is rejected and that recovery after explicit routing produces the durable event without autonomous redispatch. If upstream does not include the equivalent CLI recovery, retain that local part even if the remainder of the PR is integrated.

## HLP-194 — durable, unique terminal handoff

- **Reason:** a worker could terminate with code `0` without a successful, durable `kanban_complete`, `kanban_block`, or other terminal lifecycle handoff.
- **Primary active files:**
  - `agent/conversation_loop.py`
  - `agent/kanban_stop.py`
  - `agent/turn_finalizer.py`
  - `cli.py`
  - `hermes_cli/kanban_db.py`
  - `hermes_cli/kanban_exit_codes.py`
  - `tests/agent/test_kanban_stop.py`
  - `tests/hermes_cli/test_kanban_protocol_exit.py`
  - `tests/run_agent/test_kanban_terminal_guard_integration.py`
- **Local evidence:** post-restart `49 passed`; compilation, Ruff, and diff green; coverage for exit `0`, explicit violation, exception, signal, timeout, real post-commit receipt, rejected receipt, and contradictory/duplicate handoffs.
- **Upstream:** <https://github.com/NousResearch/hermes-agent/pull/91220>, open and mergeable, with no checks reported when this index was reconciled.
- **Retirement gate:** repeat the full preceding matrix on the target revision and verify that `EX_PROTOCOL=76`, events, and outcomes distinguish protocol, crash, signal, and timeout.

## HLP-198 — effective branch on the first spawn

- **Reason:** the dispatcher persisted the derived branch but passed the stale claimed object to `_default_spawn`, omitting `HERMES_KANBAN_BRANCH` on the first attempt.
- **Primary active files:**
  - `hermes_cli/kanban_db.py`
  - `tests/hermes_cli/test_kanban_db.py`
- **Local evidence:** `32 passed, 1 skipped`; a real-process test confirmed equality among `HERMES_KANBAN_BRANCH`, `git branch --show-current`, and persisted `branch_name` in `ready` and `review` lanes; `dir` tasks do not receive an invented branch.
- **Upstream:** <https://github.com/NousResearch/hermes-agent/issues/89677> and <https://github.com/NousResearch/hermes-agent/pull/89688>; both open, PR mergeable, and required checks green when this index was reconciled.
- **Retirement gate:** repeat the first-spawn test in `ready` and `review` lanes, plus the `dir`/`scratch` control, on the target revision without the local patch.

## HLP-204 — profile-asymmetric concurrency limits

- **Reason:** `max_in_progress_per_profile` imposed the same cap on every profile and could not express a single Supervisor alongside multiple Implementers. Aether needs to accelerate the critical path with independent units without allowing duplicate Supervisors or relaxing review.
- **Accepted topology:** `max_in_progress: 4`, uniform fallback `3`, override `supervisor: 1`, override `implementer: 3`. Morfeo is not part of the Kanban dispatcher.
- **Semantics:** the effective limit is the assignee override when it exists and otherwise the uniform fallback. Ready and review share the same counter, including already-active tasks and dry-run.
- **Primary active files:**
  - `hermes_cli/kanban_db.py`
  - `hermes_cli/kanban.py`
  - `hermes_cli/config_defaults.py`
  - `gateway/kanban_watchers.py`
  - `tests/hermes_cli/test_kanban_per_profile_cap.py`
  - `tests/hermes_cli/test_kanban_per_profile_overrides.py`
  - `tests/hermes_cli/test_kanban_cli_dispatch_passthrough.py`
  - `tests/gateway/test_kanban_watchers_mixin.py`
  - `home/config.yaml`
- **Post-reload local evidence:** active gateway with PID `1284969`, `Result=success`, `ExecMainStatus=0`, zero restarts, and zero errors from the new PID; `91 passed`; Ruff and `py_compile` green; `load_config()` resolved `max_in_progress=4`, fallback `3`, and overrides `{'supervisor': 1, 'implementer': 3}`. The mixed test covers ready/review, an already-active task, dry-run, and fallback limit.
- **Reversible backup:** `.aether/backups/issue-204-profile-concurrency/`; the nine backed-up sources were verified byte for byte by SHA-256 before the port.
- **Upstream:** initially developed against `origin/main` `76952ba54f5dd83f4f5bd0246059171b4b9d1c4a` and rebased/qualified without conflicts against `533886c8b8eb67ff8b389b7f48e7d5e5d9c575b9`; `git range-diff` confirmed that the three commits retained identical content. Worktree: `/tmp/hermes-profile-caps-204`; issue <https://github.com/NousResearch/hermes-agent/issues/91259>; PR <https://github.com/NousResearch/hermes-agent/pull/91266>, open and mergeable. The PR preserves test authorship from the prior `#70674` attempt and completes kernel, ready/review, CLI, gateway, defaults, validation, and documentation. The remote branch was not rewritten after the local rebase because force-push was not authorized; GitHub evaluates the same diff against live `main`.
- **Activation status:** active and validated after restart. The preceding process exited with code 1 during intentional SIGTERM; that separate defect did not prevent the new start and is already recorded upstream in `NousResearch/hermes-agent#24344` with our reproduction.
- **Retirement gate:** on the target revision without the local patch, configure overrides, verify `Supervisor=1` and `Implementer=3` in a ready/review mix with prior running and dry-run, test CLI/gateway passthrough and invalid-value normalization, load the effective configuration, and repeat post-restart qualification.

## HLP-209 — directories are not lifecycle scripts

- **Reason:** the referenced-script walker interpreted an absolute directory path within multiline `python3 -c` as an executable candidate. `_read_referenced_script` classified every non-regular object as unsafe and produced the generic gateway restart/stop message even though direct scans found no lifecycle action.
- **Decision:** do not open another issue or PR for this repair. The defect and fix already exist upstream; `Aether-Agents#209`, created before this decision, remains only as a downstream trace of the observed block.
- **Primary active files:**
  - `cron/lifecycle_guard.py`
  - `tests/hermes_cli/test_gateway_restart_loop.py`
- **Local change:** `stat.S_ISDIR(metadata.st_mode)` returns `(None, False)`—nothing to scan—before the general fail-closed behavior. Devices, sockets, FIFOs, and actual scripts remain blocked.
- **Local evidence and reload:** focused RED `1 failed` with `exit_code=1`; focused GREEN `1 passed`; complete guard suite `126 passed`; cron suite `710 passed, 1 skipped`; `py_compile`, Ruff, and `git diff --check` green. The cron suite emitted an unexpected-coroutine warning in `hermes_cli/web_server.py`; the indicated test passed without warning over a disposable tree from the base `HEAD`, so it is not attributed to HLP-209 and nothing outside scope was modified. External restart changed the gateway from PID `1284969` to `1356904`; systemd reported `active/running`, `Result=success`, and `NRestarts=0`. Repetition through the ordinary B0 review path remains pending because the prior escalation keeps the card in `triage` until explicit human recovery.
- **Upstream:** closed issue <https://github.com/NousResearch/hermes-agent/issues/86753>; fix integrated into `origin/main` by commit <https://github.com/NousResearch/hermes-agent/commit/9ac1e65b0ae4e83dced9d5c8a406cc57cb589702>. The inspected upstream revision `a86569bd1134867e46b49f7cef1988083d7666d8` passed the equivalent probe: innocuous directory allowed, actual lifecycle script and `/dev/null` blocked. No new upstream issue or PR is needed.
- **Pending runtime validation:** service reload is verified; the escalation of B0 must be recovered by a human, moved to the same `review` card, the validation that originated the false positive repeated through the ordinary path, and negative controls confirmed to remain blocked.
- **Retirement gate:** on a future Hermes revision without the local hunk, run the exact regression, all of `test_gateway_restart_loop.py`, and the post-restart runtime probe; only then retire the backport and mark `RETIRED`.

## HLP-211 — worker-session continuity by flow and HLP-211b blocker routing

- **Reason:** each Supervisor card opened a new session; decomposition, review, and integration lost history and prompt cache despite belonging to the same Objective Contract. The repair keeps one logical session per `(board, Project, flow_id, perfil)` and one canonical Supervisor workspace per flow; Implementers retain independent sessions/worktrees. The 2026-08-29 reproduction added the HLP-211b gap: a blocked Implementer could emit `origin_signal` with no origin subscription, bypass Supervisor, and leave the flow stopped until the next owner message.
- **Primary active files:**
  - `hermes_cli/kanban_affinity.py`
  - `hermes_cli/kanban_db.py`
  - `hermes_cli/kanban.py`
  - `hermes_cli/main.py`
  - `run_agent.py`
  - `tui_gateway/server.py`
  - `tools/kanban_tools.py`
  - `gateway/kanban_watchers.py`
  - `tests/hermes_cli/test_kanban_session_affinity.py`
- **Local semantics:** `session_affinity={flow_id, terminal}` is opt-in; only cards of the same Project, profile, flow, and workspace may share a session. The dispatcher reserves a generational lease before spawn, records the real session, uses `--resume --no-restore-cwd --in <workspace>` in subsequent processes, and rejects stale leases/sessions/workspaces. A same-profile child inherits flow and workspace; cross-profile children do not inherit a session. HLP-211b retains a silent origin subscription at the affinity root; a real parent blocker wakes the single terminal-affinity child through `flow_attention`; that card can resolve and return to `dependency` (Hermes resumes the parent), or escalate with `origin_signal="recovery"`. Only `origin_signal` (`input|revision|recovery`) and `flow_terminal` cross to the origin; internal milestones remain silent. Ambiguous graphs fail closed to the legacy route.
- **Exact HLP-211b hunks (active prior checkout `0b288979e`, inspected upstream `105b8650`):** `hermes_cli/kanban_db.py`: line 114 expands `VALID_ORIGIN_SIGNALS`; lines 5384–5514 add `_pending_flow_attentions`, `_wake_terminal_flow_controller`, and `_resolve_flow_attention`; line 7224 resolves/resumes the parent when the controller returns to `dependency`; lines 7274 and 7344 connect normal and escalated blockers to the controller; line 11883 and the following block inject the protocol into `build_worker_context`; the claim retains parent gating except when attention is pending. `tools/kanban_tools.py`: line 1672 retains auto-subscription on non-terminal affinity roots; lines 2040 and 2050 expose `recovery`. Tests: `tests/hermes_cli/test_kanban_session_affinity.py` lines 579–713 and `tests/tools/test_kanban_tools.py` from line 1151.
- **Exact HLP-211b size against the prior backup:** production: `hermes_cli/kanban_db.py` `+186/-7`, `tools/kanban_tools.py` `+6/-4` (**192 added / 11 removed; net +181**). Tests: `tests/hermes_cli/test_kanban_session_affinity.py` `+159/-0` and one non-terminal auto-subscription test of `+40/-0` in `tests/tools/test_kanban_tools.py`. Hotspots were not reformatted, and no other local changes were attributed to the patch.
- **Aether:** `prepare_handoff` derives a deterministic `flow_id`; Morfeo passes it to the root Supervisor, and terminal review/integration retains the same affinity/workspace. The specific policy remains in Aether, not Hermes core.
- **Local evidence:** HLP-211 base had `114 passed, 1 skipped`; E2E-16 proved exact session/workspace reuse. HLP-211b records prior RED (`flow_attention` absent and `recovery` rejected) and GREEN: `6 passed, 70 deselected` focused; affected suites `117 passed, 1 skipped`; Ruff check with no errors. After restarting the gateway from PID `877` to `181495`, a disposable process/SQLite/Project probe produced `PASS`: blocked unit → terminal controller `ready` → `flow_attention` context → same controller claimable → `dependency` resumed the unit and returned the controller to `todo`. The live E2E-15 run `e2e-15-20260829-200042-6466bb1c` with Sol/Terra was **inconclusive for HLP-211b**: one-shot Morfeo polled until the fixed 900 s timeout (`rc=124`); meanwhile the root Supervisor and two Implementers completed and the terminal Supervisor started, but cleanup interrupted it. There was no blocker/`flow_attention`; it confirms that the current lane does not create the live Morfeo process it intends to measure and does not attribute failure to the patch.
- **HLP-211b backup and artifact:** `.aether/backups/hlp248-flow-blocker-routing-20260829T193117-0600`; `SHA256SUMS` retains the four preceding files and `LEDGER.sha256` the preceding ledger. Versioned portable patch: `patches/hermes/HLP-211b-flow-blocker-routing.patch`, SHA-256 `7dceea9b9561c626fa6106f4bcd049592d9cb3627e2e0caed07a34df7d088bda`; `git apply --check` and byte-for-byte comparison against the four active files passed on a reconstruction from the backup.
- **Upstream:** <https://github.com/NousResearch/hermes-agent/pull/75951> resumes only the same card after block→unblock and does not cover multi-card affinity, Project/workspace, generational fencing, or terminal routing. Related issues: `#59855`, `#68779`, `#71175`.
- **Activation status:** HLP-211/HLP-211b `ACTIVE_LOCAL_E2E_QUALIFIED`. Morfeo gateway restarted on 2026-08-29 19:44 CST to PID `181495`; post-restart probe green. Live E2E-15A `e2e-15-20260829-220207-c384343e` terminated `PASS` with `native_same_session_wake=true`, one owner submit, four cards, and green acceptance. The live blocker canary `e2e-17-20260829-231107-c50462c6` produced two `flow_attention`, one `origin_signal=recovery`, same Supervisor session generation 3, wake of the same Morfeo session, restored Implementer hook, controller `blocked→completed`, and terminal verification exit 0; evidence: `evidence/hlp211b-live-gate.json`. Its aggregate status was `FAIL` only because the harness acceptance read the root checkout rather than the integrated worktree; that aggregate is not presented as PASS. `build_worker_context` makes runtime independent of SOUL.
- **Retirement gate:** on a target upstream revision without HLP-211/HLP-211b, execute E2E-16 and the complete blocker canary: same session across root/recovery/review/integration, fresh Implementer, silent `dependency`, one attention per blocker, resumed parent, `recovery` waking Morfeo without another owner message, isolation, and exclusive delivery of `input|revision|recovery|flow_terminal`. Retire only equivalent hunks; Aether policy is not retired with Hermes.

## HLP-226 — canonical Project inheritance in worktree children

- **Reason:** `kanban_create` disabled Project inheritance when the worker explicitly requested `workspace_kind="worktree"`; the child was left with `project_id=null` and `workspace_path=null` and could not run.
- **Primary active files:**
  - `tools/kanban_tools.py`
  - `hermes_cli/kanban_db.py`
  - `tests/tools/test_kanban_tools.py`
- **Local change:** where no literal `workspace_path` exists, the handler transmits the worker card as the canonical source. If the creating profile does not have the Project in its `projects.db`, `create_task` derives repository and branch convention from that shared card, retains the UUID, and creates its own path; a different explicit Project is rejected.
- **HLP-226b extension:** a terminal Supervisor affinity card correctly shares the root worktree and therefore persists `workspace_kind=dir`, `workspace_path=.worktrees/<root-id>`, and a distinct task id. The prior fallback required `workspace_kind=worktree` and `workspace leaf == source task id`; it discarded that canonical source and created rework with `project_id=null`/`workspace_path=null`. HLP-226b accepts only the actual root indicated by the leaf when root and terminal match on Project, assignee, flow, and path; any arbitrary `dir` remains without inheritance.
- **Evidence:** real reproduction `t_e729952b → t_21b8341a` produced the runnable orphan and reopened #226. Exact regression RED `1 failed` (`project_id None`); GREEN `1 passed`; inherited controls `4 passed`; affinity/tools/worktree suites `80 passed`; `py_compile`, Ruff check, and `git diff --check` green. The same test includes a negative control where a `dir` outside `.worktrees` retains null Project/path.
- **HLP-226b backup and artifact:** prior backup `.aether/backups/hlp226b-affinity-terminal-20260830T144501-0600`; preceding SHA-256 values: `kanban_db.py` `dcb073c15f9e439a7f0a82f958e95f77e13831993e5f881514d4a024c82d9d0f`; test `90b0cc59e76c4727eb30aad28fde7c80ce134e1892bd48369f079b7481e5ac01`. Portable patch `patches/hermes/HLP-226b-affinity-terminal-project-inheritance.patch`, SHA-256 `a28fd10888932f421d32d41e1012ec7aad17280ae9e289c4d0329ff492f6c040`; `git apply --check` and byte-for-byte reconstruction green.
- **Upstream:** `b9b5481d6236edb3ec8aae32cc4b5c661569b872` covers only the direct worktree source. `NousResearch/hermes-agent@4f22543509d1b91dc45bcb369447126c5eb14fb7` does not recognize the terminal affinity/`dir` card; HLP-226b remains local.
- **Activation status:** `ACTIVE_LOCAL + HLP-226b`; every new worker imports the handler/DB from the editable checkout, so no gateway restart is required.
- **Retirement gate:** repeat both E2Es with an empty Project registry: direct worktree source and shared terminal-affinity source; retire only if both children retain UUID, worktree, and branch, the real checkout materializes, a conflicting Project is rejected, and a noncanonical `dir` is not used as a source.

## HLP-246 — verifiable Kanban attachment identity

- **Reason:** attachment `qualification-failure-evidence-v2.tar.gz` reached the write path already truncated but with valid base64; the DB and disk retained the same corrupt `8699` bytes and the system returned success because it validated only base64 syntax and local size.
- **Primary active files:**
  - `hermes_cli/kanban_db.py`
  - `hermes_cli/kanban.py`
  - `tools/kanban_tools.py`
  - `plugins/kanban/dashboard/plugin_api.py`
  - `tests/plugins/test_kanban_attachments.py`
  - `tests/tools/test_kanban_tools.py`
- **Local change:** `kanban_attach` requires size and SHA-256 computed before base64, compares them with decoded bytes, and rejects every mismatch before writing. The kernel rereads every write, verifies size/hash, and only then inserts the row. CLI, URL, and dashboard compute the identity server-side; listings/context expose the SHA. The migration adds nullable `sha256` and leaves legacy attachments as `NULL` so it does not retroactively certify potentially corrupt bytes.
- **Evidence:** focused RED `5 failed`; focused GREEN `5 passed`; related complete suites `93 passed, 1 skipped`; Ruff and `git diff --check` green. Three-process E2E with a real `14191` byte tar.gz: expected/DB/disk size identical, SHA-256 `df5a060e1840aa77a61fdbb8f721cce810e6db48a8faa92e30bff76ac3cfe90d` identical at sender/response/DB/readback, and the file opened with the expected member. The original complete v2 file no longer exists; the only found file is corrupt and remains `sha256=NULL`/unverified.
- **Upstream:** no equivalent was found in `origin/main` or by searching for truncated attachments, checksum, or SHA-256 issues/PRs.
- **Activation status:** `ACTIVE_LOCAL`; CLI and new workers load the repair by process. Already-live processes/TUI retain their prior tool schema until a new session; this TUI is not restarted so as not to destroy the active conversation.
- **Retirement gate:** on a target upstream revision, require pre-transport claims for inline base64, server-computed identity persisted and returned, rejection of partial write, non-certifying legacy migration, and byte-for-byte tar.gz E2E before retiring the patch.

## HLP-247 — an archived parent is not a completed parent

- **Reason:** `recompute_ready` treated `archived` as equivalent to `done` at the dependency gate. When archiving a parent, a child in `blocked` whose block predates the `blocked{initial:true}` event (2026-08-20) is invisible to `_has_sticky_block`, was promoted to `ready` inside `archive_task`, and dispatched without any `unblock`. Observed in reality: board cleanup relaunched `t_b02bdbad`, blocked since 2026-08-18, and it ran against an obsolete contract.
- **Primary active files:**
  - `hermes_cli/kanban_db.py`
  - `tests/hermes_cli/test_kanban_blocked_sticky.py`
- **Local change:** in `recompute_ready`, `blocked` tasks require parents in `done`; `todo` tasks retain the historical `(done, archived)` gate. One condition; it does not touch stickiness, circuit breaker, or data migration.
- **Evidence:** RED `1 failed, 8 passed` (fails exactly `assert 'ready' == 'blocked'` when archiving); GREEN `9 passed`; isolated reproduction `/tmp/repro_blocked_promotion.py` no longer reproduces.
- **Upstream:** `NousResearch/hermes-agent@main` verified **not fixed** (same `("done","archived")` gate, same `_has_sticky_block`, `archive_task` still calls `recompute_ready`). Aether #247. No upstream PR yet.
- **Activation status:** `ACTIVE_LOCAL`.
- **Retirement gate:** on a target upstream revision without this hunk, repeat the three regressions; retire only if the `blocked` child remains blocked when the parent is archived, the `todo` child is released, and the non-sticky child with a `done` parent is promoted.

## HLP-262 — `origin_signal` sticky until explicit resolution

- **Reason:** `block_task(..., origin_signal="revision|recovery|input")` persists `blocked` state but emits an `origin_signal` event rather than `blocked`. `_has_sticky_block()` queried that event but returned true only for `blocked`; the following `recompute_ready()` promoted a root with no parents and dispatched it again without a new contract, `unblock`, or Morfeo resolution. Real reproduction: `t_2548a58b` was promoted 33 s after `origin_signal=revision`; `t_0701d31b` repeated the defect 37 s after `origin_signal=recovery`; both ended in a second block loop/triage.
- **Active files:** `hermes_cli/kanban_db.py` and `tests/hermes_cli/test_kanban_blocked_sticky.py`.
- **Minimal change:** the most recent `origin_signal` event counts as sticky just like `blocked`; `unblocked` remains the only explicit exit for this path. Dependency waits, circuit-breaker recovery, and flow-controller routing do not change.
- **Inspected upstream:** `NousResearch/hermes-agent@4f22543509d1b91dc45bcb369447126c5eb14fb7` retains `_has_sticky_block()` limited to `blocked|unblocked`; it contains no equivalent `origin_signal` semantics.
- **RED/GREEN:** exact regression `test_origin_signal_revision_block_is_sticky_until_explicit_unblock`: RED `1 failed` (`False is True`); GREEN `10 passed` in `test_kanban_blocked_sticky.py`; affected Kanban suites `86 passed`; Ruff check with no errors. The disposable SQLite/process probe produced `PASS`: three recomputations `0`, state `blocked` all three times, and only `unblock_task` moved it to `ready`.
- **Pre-change backup:** `.aether/backups/hlp262-origin-signal-sticky-20260830T133410-0600`; preceding SHA-256 values: `kanban_db.py` `2a71e14e2e5abb9d354bd7dcd2175d5683f8eafb708632542db37c82a8bc9c8d`; test `5d50b67c3386364e8ca147b9bc8daff496ad923e762d95d9f25c2a0a2e224ba2`.
- **Portable artifact:** `patches/hermes/HLP-262-origin-signal-sticky.patch`, SHA-256 `abb3215645f400019c1eb5746f288a5ba517c3ba76547533d3d0693a1acb2f1a`; it requires `git apply --check`, byte-for-byte reconstruction, and post-reload canary before being marked `ACTIVE_LOCAL`.
- **Activation:** Morfeo gateway reloaded on 2026-08-30 13:38 CST from PID `359325` to `475712`; the post-reload canary in a disposable process/SQLite repeated `PASS` with three recomputations without promotion and a single exit through `unblock_task`. Status `ACTIVE_LOCAL`.
- **Retirement gate:** on an upstream revision without this hunk, execute `block_task` with each `origin_signal=input|revision|recovery`, close/reopen SQLite, execute several recomputations, and demonstrate zero promotions; then verify that `unblock_task` or native controller resolution resumes exactly once.

## Candidates pending reload

### HLP-263 — actual supervised-gateway identity

- **Exact reason and scope:** lifecycle guards treated `_HERMES_GATEWAY=1` as process identity. The marker is inherited by CLI/TUI and also appears after importing `gateway.run`; it could therefore block an external session that should manage the gateway. This candidate ports exclusively the accumulated hunks from `NousResearch/hermes-agent#93267` at tip `aa9aaaa6cb31753c3b274db6825fbd0af5f27120`: `tools/terminal_tool.py`, `hermes_cli/gateway.py`, and `tests/hermes_cli/test_gateway_restart_loop.py`. It excludes the contributor email mapping and every other upstream change. The cron guard does not change.
- **Minimal change:** the three lifecycle guards (terminal, `gateway stop`, and `gateway restart`) query `tools.process_registry._is_supervised_gateway_process()` instead of the inheritable marker. A genuinely supervised gateway therefore remains denied, while an external CLI/TUI with inherited markers and a false probe reaches execution. A foreground execution without a supervisor also passes: no KeepAlive turns stop/restart into a loop.
- **Pre-patch identity and reversible backup:** active pre-patch revision `0b288979e2322c02ab42c05f1e183bb31cfa5aa9`; `status --porcelain=v1` had `28` modified and `5` untracked entries (listing SHA-256 `0bc1f45145ea3463423bd27f46faab0924086750aa73b4cc9fefff509523491f`). Of the three targets, only the test was modified (`+44/-8`) before this hunk. Pre-patch SHA-256: `tools/terminal_tool.py` `2a6e3260f42e1bb992b167d294544197d8320b28a7e79067e95f7e186f659d19`; `hermes_cli/gateway.py` `760da366030f65b671f735a0138fa4b7a53992ca4aee5fe28e3e8fe879788ce7`; `tests/hermes_cli/test_gateway_restart_loop.py` `1fe5a7dd249fa6297d6d1a71c7a8fdf60edbb127639c8435e1016eeb72c17117`. Those three hashes are the verifiable backup; private copies are not versioned.
- **Portable artifact and reconstruction:** `patches/hermes/HLP-263-gateway-process-ownership.patch`, SHA-256 `b70f5436d2fbe63ffaa9d62adce97c6361622255b2b6768fa6bbe2874393664b`. In a disposable copy of the already-dirty active tree, `git apply --check` passed before application. Applying the patch and reconstructing again from the pre-patch copy produced the three patched files byte for byte; SHA-256 of `cron/lifecycle_guard.py` was identical before/after (`702e88957840c64d6669122ca42f3246d013bee4a8730ec1f2c6357a18bb8914`), and all non-target source bytes were preserved.
- **RED/GREEN and controls:** RED for `test_cli_agent_session_not_blocked_by_inherited_env`: `1 failed`, exactly `assert 1 == 0`, by first applying only the regression hunk. GREEN: the regression, direct CLI guard, and nine supervised lifecycle commands gave `12 passed`; the complete real focused suite `tests/hermes_cli/test_gateway_restart_loop.py` gave `127 passed`; `py_compile`, Ruff, and `git diff --check` passed. The nonmutating help `python -m hermes_cli.main gateway restart --help` terminated `0` and showed only options. The direct upstream test exercises `stop` denial under the supervised probe; the `restart` hunk uses the same probe/condition. A separate inline CLI probe attempt was denied by the external hardline because it contained a literal lifecycle action; that control was not retried or circumvented.
- **Activation and retirement:** Morfeo backed up the three files to `.aether/backups/hlp263-gateway-ownership-20260831T003539-0600`, verified the pre-patch hashes, `git apply --check`, applied only HLP-263, and repeated `127 passed`, `3 passed` for ownership, Ruff, `py_compile`, and `git diff --check`. The gateway reloaded from PID `475712` to `675455` and became `active`; a fresh CLI process with `_HERMES_GATEWAY=1` and `HERMES_GATEWAY_SESSION=1` executed `gateway restart --help` with `rc=0` and showed usage. Status `ACTIVE_LOCAL / UPSTREAM_VERIFIED`. To retire on Hermes update, the target revision must contain equivalence to `aa9aaaa6cb31753c3b274db6825fbd0af5f27120`; afterward run `git apply --check -R`, revert only these hunks, and repeat the same matrix/canary before reloading. Never restore complete files or touch the cron guard.

## HLP-335 — terminal PR references must not strand Graphify closeout

- **Authority and scope:** owner-authorized bounded recovery of the existing Graphify #330 execution, after GX-05 was approved but GX-INT was refused as `active_pr`. No new Objective Contract, implementation unit, queue or permission override was created. The TUI interruption #305 remains out of scope.
- **Defect:** the respawn guard treated any recent PR URL as active for 24 hours, including the already-merged PR #332. The same terminal task was left unable to resume after its repair dependency completed.
- **Upstream:** reviewed existing NousResearch/hermes-agent issues #29458, #80231, #80514 and proposals #95199, #104277. Adapted the terminal-state approach from still-open PR #95199 rather than upgrading Hermes or adding a requeue bypass. No upstream PR was created by this recovery.
- **Minimal runtime change:** only `hermes_cli/kanban_db.py`, 53 added / 7 removed lines against the exact dirty preimage. A bounded five-second `gh pr view --json state` read releases only verifiable CLOSED/MERGED references. OPEN, malformed links, missing gh, network/auth failures and unknown states remain guarded. Duplicate links are memoized for one guard check, not cached indefinitely. Review-lane, auth, cooldown and recent-success guards remain unchanged.
- **Identity and preservation:** preimage SHA-256 `10d60a61000b02457381cac3de2b202bf5ecc84bff9ad0f52e4f8f35809a1eb0`; patched file SHA-256 `159b2b521d5c950c086fffe9c89204d8d1334b72b876e6b2a40078c601747910`; exact recovery delta SHA-256 `7f971b5f73701ac7903e3ce955c323c263bcd8fa24edbf78b0d7e026026b7adf`. Private reversible source/diff/test receipts were preserved. All other pre-existing dirty source bytes were verified unchanged; no full-file restoration or unrelated cleanup was performed.
- **Verification:** disposable RED 5 failed / 15 passed; GREEN 20 passed; existing Kanban DB/review suites 51 passed / 1 skipped. All fixture board selectors were isolated. Ruff and syntax checks passed. A fresh read-only guard check against the exact real closeout returned no guard, using actual GitHub state, without editing its comments or database records.
- **Activation/canary:** used the existing graceful gateway restart path, with no forced stop and no TUI restart. The replacement service was active/running. Native `kanban_unblock` resumed the same GX-INT card, and native dispatcher readback confirmed a new running Supervisor execution. Canary passed and runtime repair stopped; Graphify integration/semantic activation remain Supervisor's separate closeout responsibility.
- **Rollback:** compare the installed hash, reverse only the preserved HLP-335 delta after `git apply --check -R`, then reload gracefully. Never restore the complete `kanban_db.py`, which contains unrelated accepted patches. Retirement requires a qualified upstream version to pass terminal/open/unknown/auth/duplicate-link controls and the same legitimate continuation canary without this delta. Do not retire merely because an upstream PR merges.
- **Disposition:** ACTIVE_LOCAL; `release_impact=patch`, `release_action=defer`, `release_channel=none`. No credential/router/settings changes, package publication or deployment. Evidence and closure tracked in Aether issue #335.

## HLP-305 — transient turn-lease refresh contention must not impersonate a user interrupt

- **Authority and scope:** owner-authorized bounded recovery of the foreground TUI after the live Graphify audit was aborted without owner input. The reproduction was appended to Aether issue `#305` before implementation. This repair does not change Graphify, session history, SQLite schema, write patience, lease TTL, provider configuration or concurrency limits.
- **Observed defect:** at `2026-09-07 15:11:50 -06:00`, `SessionDB._execute_write()` exhausted its 20-second `BEGIN IMMEDIATE` patience while the active turn renewed its session lease. `run_agent.py` treated that transient `database is locked` exception as authority loss, called `interrupt(..., hard_cancel=True)`, persisted a cancelled tool result, and ended the TUI turn as `interrupted_by_user` / `Operation interrupted.` at `15:12:17`, although no owner interrupt occurred. The TUI process tree remained alive and accepted the next prompt; background audit workers also remained live.
- **Root-cause boundary:** a holder-qualified refresh returning `False` proves the holder lost the lease and still interrupts immediately. A non-lock persistence error still interrupts immediately. Only errors classified by the existing `classify_persistence_error()` as `locked` are retried, and only while the monotonic expiry estimate leaves enough time for one refresh interval plus the database's complete write-patience budget. Successful refresh resets the estimate; persistent contention therefore fails closed before the known TTL can expire.
- **Loaded baseline and files:** Hermes editable source `home/.venv-hermes/src/hermes-agent` at base `0b288979e2322c02ab42c05f1e183bb31cfa5aa9`; implementation `run_agent.py`; regression `tests/run_agent/test_cross_process_turn_lease.py`. Preimage SHA-256: implementation `768653554e25291394c05dee613fa90fdb99e24357ca4449912d744347457a39`, test `d2066cbb619b59ef515a7fe51da01cd7f2e2fcfd9f9c841f7612cb7692762bb1`. Installed SHA-256: implementation `925db8839ef5c0c4132e8e93c6974d0385393f0b8d11922817b0f920578847c3`, test `ef2ff991e56d35ddb754de31f577887bc069030e2af82b4de72632336be52851`.
- **Reversible backup and artifact:** preimages are under `.aether/backups/hlp305-tui-lease-refresh-20260907T153529-0600/`. Portable patch `patches/hermes/HLP-305-tui-lease-refresh-contention.patch`, SHA-256 `05a655cf2a4509d6f6d64895decec20922cc9ae42dfeaa737fe0488678d3dab1`; `git apply --unidiff-zero --check` passed and application to the two preimages reconstructed the installed files byte for byte.
- **RED/GREEN evidence:** disposable exact-loaded-source RED failed `1` regression with `final_response == ''` after the first locked refresh. Candidate GREEN passed the same regression (`1 passed`), the complete cross-process turn-lease suite (`13 passed`), and the storage lease suite (`19 passed`). The installed editable source repeated `13 passed` and `19 passed`; Ruff, `py_compile`, and `git diff --check` passed. Ruff reported one pre-existing invalid `# noqa` warning at `run_agent.py:117`, outside this patch.
- **Upstream inspection:** current `NousResearch/hermes-agent@4810074d73d9419dc82545202d595507a73f4f0e` moves the behavior to `agent/turn_facade_lease.py` but retains the same unconditional interrupt for every refresh exception. Searches found no matching issue or PR. Recovery creates no upstream PR; upstream publication is a separate objective.
- **Activation:** `RELOAD_PENDING`. Fresh Python processes import and pass from the patched editable source. The already-running TUI and gateway retain their old in-memory module; they were deliberately not restarted during the owner-visible Graphify audit. After graceful reload, the canary must inject one transient locked refresh followed by success and observe completion with no hard interrupt; the real lost-lease and non-lock controls must still interrupt.
- **Rollback and retirement:** before rollback, require the two installed hashes above, run `git apply --unidiff-zero --check -R` against the portable patch, reverse only these hunks, reload gracefully, and rerun the three controls. Retire only when an upstream revision without HLP-305 passes the transient-lock completion, persistent/no-budget contention fail-closed, holder-miss interrupt, non-lock interrupt, late-refresh cleanup and real TUI continuation checks. `release_impact=patch`, `release_action=defer`, `release_channel=none`.

### HLP-305 maintained-fork holder repair (2026-09-08)

The waiter-only record above is retained as historical evidence. Current source also includes the legacy FTS holder correction in `DarkArty07/aether-hermes`, PR #1, merge `c185ee3bb5b6d609241432fd123c16143f065987`; source and reproducible qualification are in that fork's `AETHER_FORK.md`, `hermes_state_common.py`, `hermes_state_schema.py`, `hermes_state_search.py`, `tests/test_fts_tool_write_bounds.py` and `scripts/qualify_legacy_fts_contention.py`. A maintained fork is now owner-approved under amended PD-65; the prior mandatory transition-only policy does not govern Aether-specific adaptations.

This is an intellectual adaptation of upstream `57162d0cc1875ef6307aebe6cb599b5a1d052dd2` (fangliquanflq), not a Hermes upgrade. Only existing inline/legacy FTS triggers are changed, transactionally. Prior index entries and complete canonical messages survive; new tool-result index bodies use an 8192-character prefix. Explicit tool-role searches retain full-body canonical fallback. Fresh external-content/CJK schemas are not changed. No full rebuild, VACUUM, pruning or credential/provider change is part of this recovery.

Evidence: baseline regression `3 failed, 1 passed`; final focused `6 passed`; neighboring FTS/lease suite `73 passed`; expanded persistence/TUI `867 passed, 1 pre-existing failure` independently reproduced on unchanged baseline and recorded in #349. The reviewer found no blockers. A real disposable 384-row/204471936-byte batch held the insertion lock for 27.576s and caused the separate lease refresh to time out at 20.397s; the same payload after the repair inserted in 2.078s and renewed the lease in 2.159s, with all canonical rows intact. Repeating the shipped canary also passed (2.287s insertion / 2.496s refresh). These measurements prove the failure mechanism, not the exact payload of the original incident.

Activation completed through normal `SessionDB` startup after a consistent read-only online backup passed `quick_check` and SHA-256 verification. Three installed source modules were hash-matched to the maintained fork. The native startup verified all four legacy bounded triggers, preserved the complete pre-activation row count and unchanged sampled canonical-content hashes, and added no synthetic messages to the live store. A real `read_file` result from the still-running owner TUI retained all 11576 canonical characters while both FTS indexes held the 8192-character prefix plus metadata (8203 characters). Thus the SQLite writer-side correction is active for existing processes; Python search-fallback/waiter code in already-running processes still needs a graceful reload before claiming those in-memory paths are current.

After new prefix-indexed rows exist, reverting source alone is not a complete search rollback: retain the full-body fallback until deliberate reconstruction is qualified. Never restore an older whole database over newer conversations. Inherited fork Actions are disabled; these are local test and review receipts, not a claimed remote CI pass. `release_impact=patch`, `release_action=defer`, `release_channel=none`.

## Runtime reliability on the maintained fork (2026-09-08)

These entries record independently reviewed source on `DarkArty07/aether-hermes` for Objective Contract `oc_5c2dad1b37b20a80@v1`. They are not live-runtime activation. Inherited fork Actions remain disabled and are not claimed green. Exact integrated fork merge SHA: `4b5772ff43de70f1222aabbf1daed4eefc7b44cf` (`DarkArty07/aether-hermes` PR #2).

### B267 / #267 — Disposable probe laboratory isolation

- **Issue:** [#267](https://github.com/DarkArty07/Aether-Agents/issues/267)
- **Evidence:** `specs/runtime-reliability-bugs/evidence/RR-267.md`
- **Scope:** Aether `src/aether_agents/lab/runner.py`, `tests/test_e2e_harness.py`
- **Behavior:** `preflight_disposable_destinations` rejects symlinked and escaping database/workspace destinations before writes; `isolated_hermes_env` and `_observe_native_affinity_controls` clear `HERMES_DELEGATED_CHILD_CONTEXT`, `HERMES_PROJECT_ID`, `HERMES_TENANT`, and `AETHER_PROJECT_ID` while preserving parent environment immutability.
- **Upstream relationship:** Aether-specific laboratory harness isolation; no upstream Hermes patch.
- **Rollback:** Revert Aether commits `66bb4dd6638ab1da8e9a56fd9e63211906fafeb6` and `a67f3d78bad49cac3c8debf3b5ef118c14590f19`.
- **Retirement:** Permanent laboratory integrity gate.

### B292 / #292 — Named-custom auxiliary resolution (already working)

- **Issue:** [#292](https://github.com/DarkArty07/Aether-Agents/issues/292)
- **Evidence:** `specs/runtime-reliability-bugs/evidence/RR-AUX.md`
- **Disposition:** already-working-with-integrated-evidence on maintained baseline `c185ee3bb5b6d609241432fd123c16143f065987`. No product-code patch. Regression commit `2337bd2d9efbf0421ac121877936e92bb9486e70` (`tests/agent/test_auxiliary_named_custom_providers.py`).
- **Fake patch entry:** none.

### B294 / #294 — Background review cancellation ownership

- **Issue:** [#294](https://github.com/DarkArty07/Aether-Agents/issues/294)
- **Commit:** `cf5ff5fe2f51116364a10a9941f58f280e7ff4c4`
- **Evidence:** `specs/runtime-reliability-bugs/evidence/RR-294.md`
- **Scope:** `agent/background_review.py`
- **Upstream relationship:** Adapts upstream `_BackgroundReviewRun`, `prepare_background_review_run`, `finish_background_review_run`, and `_track_review_fork` from `NousResearch/hermes-agent@9fd44b4dfc44138b9e5d5689acb56c438364ff7b` (lines 914-1136).
- **Behavior:** Reserves run token on parent before `Thread.start()`, atomically denies admission after cancellation, tracks cancellation separately from foreground, and cleans references only when they still name that run.
- **Rollback:** Revert fork commit `cf5ff5fe2f51116364a10a9941f58f280e7ff4c4`.
- **Retirement gate:** Retires when an upstream release including `_BackgroundReviewRun` / PR #84423 is adopted in the Aether baseline.

### B295 / #295 — Explicit exhausted-pool 503 fallback

- **Issue:** [#295](https://github.com/DarkArty07/Aether-Agents/issues/295)
- **Commit:** `b58db22b4968e837a745a42cae5cb007f3819a8c`
- **Evidence:** `specs/runtime-reliability-bugs/evidence/RR-295.md`
- **Scope:** `agent/error_classifier.py` (`_classify_by_status` 503/529 branch)
- **Upstream relationship:** Downstream fix. Phrase-only match of `no available Codex accounts` after overflow and before generic overload sets `should_fallback=True`. Transient overload backoff is preserved.
- **Rollback:** Revert fork commit `b58db22b4968e837a745a42cae5cb007f3819a8c`.
- **Retirement gate:** Upstream Hermes adopts equivalent explicit pool-exhaustion classification.

### B301 / #301 — Responses extra_headers without auth leakage

- **Issue:** [#301](https://github.com/DarkArty07/Aether-Agents/issues/301)
- **Commit:** `0f56400b1603c8195590a04da47424a0df40b145`
- **Evidence:** `specs/runtime-reliability-bugs/evidence/RR-AUX.md`
- **Scope:** `agent/auxiliary_client.py` (`_CodexCompletionsAdapter.create`, `_safe_request_extra_headers`, fallback/async callers), `tests/agent/test_auxiliary_client_extra_headers.py`
- **Upstream relationship:** Ports the `extra_headers` copy from immutable upstream `NousResearch/hermes-agent@9fd44b4dfc44138b9e5d5689acb56c438364ff7b` `agent/auxiliary_client.py:1367-1370`. Destination authentication is not forwarded.
- **Rollback:** Revert fork commit `0f56400b1603c8195590a04da47424a0df40b145`.
- **Retirement gate:** Upstream releases equivalent Responses-adapter and fallback header forwarding with destination-auth isolation.

### B304 / #304 — Same-run durable completion recovery

- **Issue:** [#304](https://github.com/DarkArty07/Aether-Agents/issues/304)
- **Commit:** `169572a845f30bda0231cb97035bfce5fb9e981d`
- **Evidence:** `specs/runtime-reliability-bugs/evidence/RR-304.md`
- **Scope:** `agent/kanban_stop.py`, `tests/agent/test_kanban_stop.py`, `tests/agent/test_kanban_stop_durable_recovery.py`
- **Upstream relationship:** Downstream stop-guard recovery. Transcript `CONFLICT` remains fail-closed; `MISSING` may ALLOW from one read-only SQLite snapshot of the pinned worker board without fabricating a `kanban_complete` receipt.
- **Rollback:** Revert fork commit `169572a845f30bda0231cb97035bfce5fb9e981d`.
- **Retirement gate:** Upstream `evaluate_kanban_stop()` natively provides equivalent durable DB completion recovery.

## Execute-code helper contract and search_files JSON framing (2026-09-08)

These entries record independently reviewed source on `DarkArty07/aether-hermes` for Objective Contract `oc_fd2332ffe34aa5f7@v1`. They are not live-runtime activation. Inherited fork Actions remain disabled and are not claimed green. Exact integrated fork merge SHA: `6243e40ea6b06e85061bf3fedffaad43eed51dec` (`DarkArty07/aether-hermes` PR #3). Concurrent runtime-reliability records above are unchanged.

### HLP-313 / #313 — execute_code helper explicit import contract

- **Issue:** [#313](https://github.com/DarkArty07/Aether-Agents/issues/313)
- **Commit:** `2d89a331f6378f42fc26f7a439e8591101289ca6`
- **Evidence:** `specs/execute-code-helper-search-framing/evidence/HF-313.md`
- **Scope:** `tools/code_execution_tool.py`, `hermes_cli/tips.py`, `tests/hermes_cli/test_tips.py`, `tests/tools/test_sandbox_failure_hints.py`, `tests/tools/test_execute_helper_contract.py`
- **Upstream relationship:** Adapted from merged upstream commit `65f033a1a20e847b7a150fe6168cd345385c7d07` (PR `NousResearch/hermes-agent#83772`).
- **Behavior:** Schema and CLI tip require `from hermes_tools import json_parse, shell_quote, retry`. NameError hints prescribe that import. Helper ImportError hints report stale generated-module or sys.path skew rather than telling the user to remove the import. Helpers remain generated `hermes_tools.py` exports; they are not injected into globals or builtins.
- **Rollback:** Revert fork commit `2d89a331f6378f42fc26f7a439e8591101289ca6`.
- **Retirement gate:** An adopted Hermes release requires the explicit-import contract and `tests/tools/test_execute_helper_contract.py` passes without this patch.

### HLP-353 / #353 — search_files truncated JSON framing

- **Issue:** [#353](https://github.com/DarkArty07/Aether-Agents/issues/353)
- **Commit:** `8a23d40eb93319ff6ea94e27c68e5643cc6d8852`
- **Evidence:** `specs/execute-code-helper-search-framing/evidence/HF-353.md`
- **Scope:** `tools/file_tools.py` (`search_tool` truncation path), `tests/tools/test_file_tools.py`, `tests/agent/test_file_safety_credentials.py`, `tests/tools/test_search_truncation_json.py`
- **Upstream relationship:** Adapted from upstream PR `NousResearch/hermes-agent#104472` / commit `7a6c3b41c33a61601132c6bbf737735bd4a07207`. Rejected parser-tolerance alternatives: PRs `#74100` and `#81622`.
- **Behavior:** Truncated and non-truncated `search_tool` output is one JSON document. Pagination guidance is `result_dict["_hint"]` with next offset `offset + limit`. No trailing plain-text suffix. No generic RPC JSON-suffix tolerance. Credential filtering, `_warning`, `_omitted`, and ACP legacy trailing-hint rendering are preserved.
- **Rollback:** Revert fork commit `8a23d40eb93319ff6ea94e27c68e5643cc6d8852`.
- **Retirement gate:** An adopted Hermes release contains PR `#104472` equivalent producer framing.

## Mandatory procedure before updating Hermes

1. Record the target version and commit here; do not activate that revision yet.
2. Consult every upstream issue/PR for `ACTIVE_LOCAL` entries.
3. Compare behavior and hunks against the target revision. A merged PR or version number is not sufficient evidence.
4. Prepare the target revision in an isolated checkout.
5. Run the retirement gate of **every** entry without first applying its local patch.
6. For each entry:
   - if the target revision demonstrates equivalence, mark `UPSTREAM_VERIFIED`;
   - if it does not demonstrate equivalence, port/reapply the patch and retain `ACTIVE_LOCAL`;
   - if upstream covers only part—as with `HLP-191`'s CLI recovery—retire only the equivalent hunks.
7. Run compilation, Ruff, `git diff --check`, and the combined focused suites.
8. Back up the active installation, switch revisions reversibly, and restart `hermes-gateway.service`.
9. Repeat post-restart runtime probes using temporary databases, never the real Aether board for destructive qualification.
10. Update this index with effective commit, results, date, and status. Only then mark an entry `RETIRED`.

## Hotspot and unclassified changes

`hermes_cli/kanban_db.py` contains hunks from `HLP-188`, `HLP-191`, `HLP-194`, `HLP-198`, and `HLP-204`. Never restore the complete file to retire one patch; reconcile by behavior and hunk.

The active checkout also has a change in `package-lock.json` generated by `peer` metadata. It is not attributed to a functional repair in this record. It must be preserved and reconciled separately; it must not be confused with an accepted Hermes patch or discarded during an update.

## HLP-280 — bounded recovery of the existing HLP-211b path

- **Authority:** current owner instruction explicitly selects direct recovery after the rejected design pipeline. No Objective Contract or worker was created for this repair. This does not approve or implement the v4/v5 architecture.
- **Reason:** exact active source reproduces four silent paths: controller `needs_input` without a signal, non-affinity child exhaustion, bootstrap root block, and unresolved attention despite refreshed heartbeat/lease. The repairable internal recovery control already passed.
- **Rollback investigation:** the pre-HLP-211b source failed all five controls in a disposable reconstruction, including the previously working internal recovery path. It was not installed. The exact active preimage, dirty diff and untracked runtime files were backed up before modification.
- **Scope:** one existing runtime file, `hermes_cli/kanban_db.py`. Reuse block/failure transactions and the native dispatcher/notifier; no schema/table/migration, provider, worker, polling service or receipt protocol was introduced. A 300-second unresolved-attention signal does not kill, unclaim or cancel the controller. Scheduled controllers are promoted; blocked controllers cannot suppress fallback escalation. Circuit-breaker routing deduplicates by durable `gave_up` event under the writer lock. Genuine non-flow blocks remain unchanged.
- **Portable artifact:** `patches/hermes/HLP-280-bounded-flow-recovery.patch`, SHA-256 `59f873ad50e0b3386223bac1fbe2a63699a19dd757175879fefc5bf923f1738b`; 143 added / 23 removed lines against the active preimage `58d97754650280db9fd1e7ad545b9af151b86d83d73d653dd84fb531f34a29b3`. Resulting file SHA-256 `10d60a61000b02457381cac3de2b202bf5ecc84bff9ad0f52e4f8f35809a1eb0`.
- **Evidence:** `specs/004-operational-simplification-and-e2e-reliability/evidence/direct-source-probe/`. Candidate: 15 direct recovery/compatibility probes, 129 existing affected tests (1 Windows-only skip), 44 notifier tests. The asynchronous test dependency was isolated outside the runtime. Failed harness attempts and the fixed candidate event-order incompatibility are recorded, not hidden.
- **Activation:** exact file `10d60a61000b02457381cac3de2b202bf5ecc84bff9ad0f52e4f8f35809a1eb0` installed with a compare-before-replace guard and reversible preimage backup. The normal graceful gateway reload replaced the process; the service was verified active/running. All 15 installed-source probes passed. An isolated, non-executable native canary generated `origin_signal=input` without the caller supplying it; the existing TUI subscriber for the exact originating session consumed the event. Machine/session/board identifiers remain in the private evidence archive. The subsequent automatic Morfeo turn received the exact native canary notification without another owner instruction. Canary PASS: task completed, sole subscription removed, and only the canary board archived recoverably. Recovery stopped immediately; no additional production change followed the PASS. No TUI, Hestia or router restart occurred.
- **Limits:** this is not qualification of the rejected model against arbitrary externally corrupted DBs, cross-DB exactly-once receipts, or all v4/v5 criteria. Existing unrelated dirty runtime changes and rejected worktrees remain preserved. Issue #280 must not be closed solely from local test counts.
- **Upstream:** `NousResearch/hermes-agent` main was observed at `96ed0e71ea2d75d325cc05c3e6468d213de2408d`; the affinity/origin-signal PR search found no equivalent. No upstream PR or dependency upgrade is part of recovery.
- **Rollback/retirement:** reverse only this exact patch after hash checking, then gracefully reload the gateway and rerun the internal recovery control. Preserve every other local hunk. Retire when a qualified upstream primitive passes the same direct regression/notification probes without this patch.
- **Release:** `release_impact=patch`, `release_action=defer`, `release_channel=none`; no release, deploy or package publication.

## HLP-310 — delegated-child identity and Kanban environment snapshot exclusion

- **Reason:** terminal snapshot dumps (`_export_dump_excluding_session_vars` in `tools/environments/base.py`) did not unset `HERMES_DELEGATED_CHILD_CONTEXT` or dispatcher-owned `HERMES_KANBAN_*`. A delegated child's marker could persist into the reusable bash snapshot and reappear in later parent commands.
- **Primary active files:**
  - `tools/environments/base.py`
  - `tests/tools/test_snapshot_session_id_leak.py`
  - `tests/tools/test_delegate_kanban_isolation.py`
- **Local evidence:** `specs/fix-310-341-345-354/evidence/HF-310.md`. Fail-first on unchanged `6243e40ea6b06e85061bf3fedffaad43eed51dec` leaked the marker and Kanban vars. Candidate `25cabeb25327199a03aa3cf1613ed2f815f646cb` unsets `${!HERMES_KANBAN_*}` and `HERMES_DELEGATED_CHILD_CONTEXT` before `export -p`. Integrated fork suites: 64 passed, 0 failed, 1 Windows-only skip. Child Kanban denial remains fail-closed. Exact maintained-fork merge: `DarkArty07/aether-hermes` PR #4, `28b593efa86bbc674b32f488c35932a4e7e85a51`.
- **Portable artifact:** `patches/hermes/HLP-310-delegated-child-snapshot-exclusion.patch`, SHA-256 `85522d5d5b9bf6609894b1a50f199334d8842bd8c2265d2425e2b920e184f413`.
- **Upstream:** no equivalent snapshot exclusion found. Downstream-only.
- **Rollback:** revert fork commit `25cabeb25327199a03aa3cf1613ed2f815f646cb`. Do not restore whole files that also contain unrelated downstream hunks.
- **Retirement gate:** an adopted Hermes release excludes `HERMES_DELEGATED_CHILD_CONTEXT` and `HERMES_KANBAN_*` from terminal session snapshots with equivalent tests.
- **Activation:** not part of this delivery. Live runtime remains unmodified.

## HLP-354 — Kanban `worktree_base_ref` materialization

- **Reason:** `_ensure_git_worktree` created new branches from incidental primary `HEAD`, so Objective Contract execution boards could spawn task worktrees on the wrong commit while another session owned the primary checkout.
- **Primary active files:**
  - `hermes_cli/kanban_db.py`
  - `tests/hermes_cli/test_kanban_worktree_base_ref.py`
- **Local evidence:** `specs/fix-310-341-345-354/evidence/HF-354.md`. Fail-first overlay on unchanged `6243e40ea6`: 14 failed / 2 passed. Candidate `7d3173e1f3dba107f9a389d4e35c95f215775ee1` uses a valid lowercase 40-character SHA-1 `worktree_base_ref` for new-branch `git worktree add`; invalid present refs raise `ValueError`; absent refs keep `HEAD`. Exact maintained-fork merge: `DarkArty07/aether-hermes` PR #4, `28b593efa86bbc674b32f488c35932a4e7e85a51`.
- **Portable artifact:** `patches/hermes/HLP-354-kanban-worktree-base-ref.patch`, SHA-256 `d0f185207c4ff953902c2f40aa9c48f2b27499e1b5f4a264e39a70d0a2383fc1`.
- **Upstream:** downstream-only contract requirement. Upstream roots new branches at incidental `HEAD`.
- **Rollback:** revert fork commit `7d3173e1f3dba107f9a389d4e35c95f215775ee1`. Do not restore whole `kanban_db.py`.
- **Retirement gate:** upstream Hermes adopts board-level worktree base ref configuration with equivalent validation and fail-closed semantics.
- **Activation:** not part of this delivery. Live runtime remains unmodified.
