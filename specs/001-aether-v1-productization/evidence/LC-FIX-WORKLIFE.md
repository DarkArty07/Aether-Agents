# LC-FIX-WORKLIFE — a terminal non-current worker must not outlive its run (#450)

- **Unit:** `LC-FIX-WORKLIFE`, routed by the LC-CLOSE flow-controller lane under the design steward's recovery directive.
- **Tracked defect:** [Aether Agents #450](https://github.com/DarkArty07/Aether-Agents/issues/450) — "bug(kanban): terminal blocked worker remains alive beside successor run". Owner obligation: canonical source fix, not runtime cleanup.
- **Authority:** root `AGENTS.md` (upstream-first method; maintained-fork corrections under PD-65), `DESIGN.md` PD-65, and the tracked defect. This unit does not create rc.2 authority.
- **Deliverable status:** source fix produced and proven in a maintained-fork worktree; **nothing pushed, no PR, no merge, no dispatch, no activation, no runtime/service/tag/release change** by the unit itself. Publication of the sanitized successor lineage was performed afterwards by the review lane — §10.
- **Maintained-fork lineage:** published commit `21628fc3790d825b8dc8082134f5cd382ec551f2` on branch `fix/450-terminal-worker-reap-clean`, based on `origin/aether-main` tip `9031bae0e8b0ab40c4fd7ba50c644972ff512611`, merged to `aether-main` as `7a4fdcd083409c31c09cfa3bfa345354e8576a7e`. The pre-publication candidate `622678ef…` was preserved locally, unpushed, as exact evidence per review direction; §10 records the single delta and its proof.
- **Aether-side artifacts:** `patches/hermes/HLP-426-terminal-worker-reap.patch`, `HERMES_LOCAL_PATCHES.md` (index-table row + `### HLP-426` section), `specs/001-aether-v1-productization/fixtures/qualify_superseded_worker_reap_450.py` (qualification canary), this note.
- **Exact local evidence** (task/run ids, epochs, worker pids, the installed release directory identity, the stale worker's own transcript behaviour) is kept in the unit card handoff notes, not in this public artifact, per root `AGENTS.md`'s boundary between local runtime evidence and public source. The reads that produced it are described in §1 and §7.

## 1. The defect, verified from the record

The tracked issue was read directly (`gh issue view 450 --repo DarkArty07/Aether-Agents`, read-only). The board's own history for the affected task was then read with `mode=ro` SELECTs only — **no `sqlite3` write of any kind was performed anywhere in this unit**, no task/event/run row was mutated, and nothing was deleted or rewritten.

What the board history shows, in order:

| offset from the run's claim | event | what it means |
|---|---|---|
| +1 s | `spawned` | the dispatcher recorded the worker's pid |
| +7 s | `heartbeat` | the worker was alive and working |
| +14 s | `block_loop_detected` | the **board** ended the run: `status=blocked`, `outcome=blocked`, `ended_at` set, task routed to `triage`, both `worker_pid` columns cleared |
| +13 min | `unblocked`, then `claimed`/`spawned` | a successor run was created with a different worker pid, while the earlier process was still alive |

The stale worker's own session transcript (read-only, in the profile's session store) shows why this is a hazard rather than bookkeeping noise: its first board action succeeded, its `kanban_block` call was rejected because the board had already terminalized the run, and the process then kept working — failed `kanban_request_review` and `kanban_complete` calls, files written into the task worktree, the website build and test executed, and further board reads that discovered the successor was current. Its last recorded activity is roughly twenty-five minutes after terminalization.

## 2. Source-first diagnosis (the tree the runtime actually loads)

**Resolving the tree came before any claim about it.** The runtime selector points at one installed release directory; that release installs Hermes in editable mode, and its package-mapping finder sends every Hermes package into the release's own `src/hermes-agent` copy; the release-origin manifest records that copy's revision as `0b288979e2322c02ab42c05f1e183bb31cfa5aa9` **plus a recorded local worktree patch**, and the gateway service runs out of the same release venv. So the loaded source is that revision with its local deltas, not the fork's clean tip.

All coordinates below are `hermes_cli/kanban_db.py` in that loaded tree; the maintained-fork coordinate is given where the file differs.

**What terminalizes the run: not the worker.** `block_task` (`:8409`) is the out-of-band terminalization path; at `BLOCK_RECURRENCE_LIMIT` (`:8548`) it routes the card to `triage`, clears `tasks.worker_pid` (`:8557`) and ends the current run through `_end_run` (`:6228`), which clears `task_runs.worker_pid` (`:6265`). The block-loop breaker therefore ends the run *while the worker process is mid-run* — exactly what the history shows, fourteen seconds after the run was claimed.

**What owns the process.** `_default_spawn` (`:13017`) starts the worker with `subprocess.Popen(..., start_new_session=True)` (`:13250-13263`) and deliberately abandons the Popen handle (comment at `:13270`), so the child stays a direct child of the gateway with no reaper except `reap_worker_zombies` (`:10491`) — which only reaps children that have *already exited*.

**Why nothing reaps it before the successor is spawned.** Two independent gaps:

1. **The identity is destroyed at terminalization.** `_end_run` and every block/reclaim transition set `worker_pid = NULL` on both the task and the run row, and `_set_worker_pid` (`:11708`) only ever wrote `{"pid": N}` into the durable `spawned` event, with no PID-reuse guard. From the moment the run ends, no board row names the process any more, so the old code had nothing to compare a live process against.
2. **No pass looks for it.** Worker termination exists only on the *reclaim* paths (`release_stale_claims` `:7157` via `_terminate_reclaimed_worker` `:10578`, `enforce_max_runtime` `:10748`, `detect_stale_running` `:10884`, `reconcile_orphaned_running` `:11014`) and on `detect_crashed_workers` (`:11186`), which by definition requires the pid to be *dead*. `_dispatch_once_locked` (`:12153`) goes straight from the tick's phases to claiming and spawning (`claim_task` at `:12545`, `claim_review_task` at `:12714`) with no check for a live process belonging to an earlier, finished run. An out-of-band terminal transition appears on none of those paths, so the successor was spawned minutes later while the old process was still alive.

## 3. Upstream-first search (before writing any patch)

Per root `AGENTS.md`, upstream was checked before patching:

- **Baseline named by the task, verified rather than trusted:** release `v2026.8.18`, commit `e624e9fde561e1add9388384012b295fde669ade` (present in the local fork's history).
- **Latest released artifact at inspection time:** `v2026.9.14` (`v0.21.3`, commit `345cd2b057a452236de401d3534b8502a7465e8d`), cloned read-only into a scratch partial checkout (`git clone --depth 1 --filter=blob:none --sparse --branch v2026.9.14 https://github.com/NousResearch/hermes-agent.git`) and identified additionally through `gh release list` / `gh api .../tags`.

What that released source contains and does not:

- **`block_task` still clears `worker_pid` without signalling anything** (upstream `hermes_cli/kanban_db.py:2933` — the same behavior as the loaded tree).
- **The dispatch lane still claims and spawns with no superseded-worker check** (upstream `hermes_cli/kanban_db.py_dispatch.py:1490` `_dispatch_lane_task`; upstream has since split the dispatcher into modules).
- **Upstream fixed the same class of defect behind a different trigger:** `archive_task` (upstream `hermes_cli/kanban_db.py:3541`) snapshots pid+claim, calls `_terminate_reclaimed_worker` after commit and records `archive_worker_termination`, with the comment "Clearing `worker_pid` in the DB alone left the OS process running past its own archive … (#76196)". That is a deliberate action on one transition: no successor-boundary guarantee, no coverage of a block/triage terminalization, no spawn-time check.
- **Run ownership is pinned** for the lifecycle tools (`HERMES_KANBAN_RUN_ID` plus expected-run validation), but nothing makes a *superseded* worker exit, and no code queries a terminal run for a live process.

**Conclusion: no released upstream artifact fixes #450.** The fix is downstream-only under PD-65 and does **not** automatically retire when the upstream archive-path fix is adopted; the retirement gate is recorded in §6.

## 4. The fix (one focused, reviewable change)

Commit `21628fc…` (the sanitized successor of the reviewed candidate; §10) — `hermes_cli/kanban_db.py`, `hermes_cli/kanban.py`, one new test module. Every changed line and why it is necessary:

| Change | Why it is necessary |
|---|---|
| `_set_worker_pid` (`:11985`) records `start_time` and `claimer_host` next to `pid` in the durable `spawned` event | The run row's `worker_pid` is cleared by every terminal transition, so this event is the only identity that survives a run ending. The start-time fingerprint is the runtime's existing `(pid, start_time)` PID-reuse guard (`gateway/status.py:288`), so the later reap can never kill a recycled pid; the host keeps the decision host-local, like every other termination path. |
| New `_process_start_time` (`:10768`) | One lazy wrapper over the gateway's fingerprint helper, so the Kanban reap uses the same identity convention instead of inventing a second one. |
| New `reap_superseded_workers` (`:10783`) | Rebuilds identity from the spawn record and terminates a live process whose run **has ended** (`task_runs.ended_at IS NOT NULL`) **and is no longer current** (`tasks.current_run_id` differs). SIGTERM → bounded 5 s wait → SIGKILL mirrors `_terminate_reclaimed_worker`/`enforce_max_runtime`; the outcome is durable as `superseded_worker_termination`, so the action is inspectable even in a tick that did nothing else. A candidate needs all three identity halves to agree; a record without a fingerprint is left alone rather than guessed at. Elapsed time is never an input. |
| New `_record_superseded_hold` (`:10900`) plus the guards at `:12738` (ready lane) and `:12915` (review lane) | If a superseded process survives termination, no successor may start beside it. The tick withholds that card's spawn and records `superseded_worker_hold`, so the invariant holds even for a process that cannot be killed. |
| `_dispatch_once_locked`: new step 0 (`:12507`), documented in the tick docstring | The pass must complete **before** the tick's spawn phase; that ordering is what makes "a terminal non-current worker exits or is reaped before a successor can mutate the same workspace" true rather than best-effort. |
| `DispatchResult.superseded_reaped` / `.superseded_held` (`:10526`, `:10532`) and the daemon summary field in `kanban.py` | Ticks are otherwise silent about what they did; an operator reading `hermes kanban dispatch` needs to see that a stale worker was reaped (or held). |

Explicitly **not** changed: `_end_run`, `block_task`, the reclaim paths, the lanes' claim sequence, the worker's own spawn/log/env handling, the schema, and any configuration. No new CLI surface beyond one field on the existing tick summary line.

## 5. Verification

All commands were run against the candidate tree unless stated otherwise; the fork venv was provisioned with the repository's own documented step (`uv sync --locked --python 3.11 --extra all --extra dev`). The raw output of every run below is recorded in the unit card's handoff notes (the exact local identifiers, per-run canary verdicts, and the failed-node A/B list), because local board ids, epochs and process ids do not belong in a public artifact.

### 5.1 Focused and affected-surface tests

```
$ scripts/run_tests.sh tests/hermes_cli/test_kanban_superseded_worker_reap_450.py -q
=== Summary: 1 files, 11 tests passed, 0 failed (100% complete) in 8.4s (24 workers) ===
FOCUSED_EXIT=0

$ scripts/run_tests.sh tests/hermes_cli/test_kanban*.py tests/gateway/test_kanban*.py \
    tests/tools/test_kanban*.py tests/run_agent/test_kanban*.py tests/plugins/test_kanban*.py -q
=== Summary: 74 files, 650 tests passed, 0 failed, 1 skipped (100% complete) in 25.4s (24 workers) ===
AFFECTED_EXIT=0
```

The new module's 11 cases cover: the exact incident shape end to end (out-of-band block → no identity left on the board → the reap terminates the process and records it), the successor-boundary ordering (the spawn observes the predecessor already gone), the withheld-spawn path when termination does not take, the current-run counter-case across eight hours of wall clock and a stale heartbeat, a recycled pid with a mismatching fingerprint, a spawn record with no fingerprint, a record claiming another host, an already-exited worker, idempotency, and `dry_run`.

### 5.2 Complete maintained-fork suite, with base attribution

```
$ scripts/run_tests.sh                      # reviewed candidate (pre-publication)
=== Summary: 3009 files, 33408 tests passed, 90 failed, 296 skipped (100% complete) in 692.6s (24 workers) ===
EXIT=1
=== 21 files with test failures (90 tests failed) ===
=== 1 file where no tests ran (collection/import error, ...) === tests/agent/test_model_metadata.py

$ scripts/run_tests.sh <the same 21 files + test_model_metadata.py>    # base 9031bae0e8, no fix applied
=== Summary: 22 files, 720 tests passed, 90 failed, 4 skipped (100% complete) in 300.0s (24 workers) ===
EXIT=1
```

The failure set is **identical at node level**, not merely at file level: 90 failed node IDs on the candidate and 90 on the base, and `diff` of the two sorted node lists is empty (same files, same per-file counts, same nodes). No changed-path regression, and no delta to diagnose. Two failures sit in Kanban/lifecycle-adjacent files and are worth naming explicitly because they are the only ones a reviewer might suspect: `tests/cron/test_cron_kanban_env_isolation.py::test_every_dispatcher_kanban_var_is_identity_gated` (its invariant enumerates the `HERMES_KANBAN_*` environment variables the dispatcher injects; this change adds no environment variable) and the ten `tests/hermes_cli/test_gateway_restart_loop.py::TestLifecycleGuardModule` nodes (script-based lifecycle detection in `cron/lifecycle_guard.py`, untouched here) — both fail with the same assertion on the unmodified base. The rest are auxiliary/provider, plugin and tool-environment nodes. No test was weakened, skipped, or made conditional to obtain these numbers.

### 5.3 Disposable-board canary (the coexistence proof)

`specs/001-aether-v1-productization/fixtures/qualify_superseded_worker_reap_450.py` drives the real board surface — `claim_task`, `_set_worker_pid`, `block_task`, `unblock_task`, `_dispatch_once_locked` with a stub `spawn_fn` — on a scratch `HERMES_HOME`/board. Only the *worker binary* is a stand-in (a process that appends to a marker file inside the task workspace and dies on SIGTERM); the claim bookkeeping, the spawn-time identity record, the out-of-band terminalization, the tick, the reap and both lanes are the real code paths. The script refuses to run if its resolved DB is not inside the scratch root, and prints the live board path it leaves untouched.

Runs are parameterized by tree only (`<BASE>` = base worktree at `9031bae0e8`, `<FIX>` = the reviewed candidate worktree; the published lineage differs only in the test module's docstring, §10). Stand-in pids below are shown as the run's own placeholders rather than literal process ids; the card handoff carries the unmodified values.

```
$ A=<unit>; BASE=<BASE>; FIX=<FIX>; PY=$FIX/.venv/bin/python; S=$A/specs/001-aether-v1-productization/fixtures/qualify_superseded_worker_reap_450.py
$ CANARY_LIVE_BOARD_DB="$HERMES_KANBAN_DB" PYTHONPATH=$BASE $PY $S --case coexist --scratch <scratch> --json-out <out>
case          : coexist
task A       : run=2 pid=<pid A2> event=block_loop_detected run_status=blocked task_status=triage
identity     : tasks.worker_pid=None task_runs.worker_pid=None (cleared by the terminal transition)
task B       : run=3 pid=<pid B1> run_status=blocked task_status=blocked
successor    : spawned=['<successor task>']
stale at spawn: {"<pid A1>": true, "<pid A2>": true, "<pid B1>": true}
reap         : []
hold         : []
event kinds  : A=['created', 'claimed', 'spawned', 'blocked', 'unblocked', 'claimed', 'spawned', 'block_loop_detected'] B=['created', 'claimed', 'spawned', 'blocked', 'unblocked', 'claimed', 'spawned']
stale after  : alive={"<pid A1>": true, "<pid A2>": true, "<pid B1>": true} exit_codes=null workspace_writes_after_successor={"<pid A1>": 8, "<pid A2>": 8, "<pid B1>": 8}
verdict       : pass
EXIT=0
```

That is the pre-fix coexistence: the incident's own shape (`block_loop_detected`, run `blocked`, task `triage`, both `worker_pid` columns cleared) reproduced on one card, a second blocked card beside it, and a successor spawned while **all three** superseded processes were alive — each of which then wrote into its workspace eight more times *after* the successor started.

```
$ CANARY_LIVE_BOARD_DB="$HERMES_KANBAN_DB" PYTHONPATH=$FIX $PY $S --case coexist --scratch <scratch> --json-out <out>
case          : coexist
task A       : run=2 pid=<pid A2> event=block_loop_detected run_status=blocked task_status=triage
identity     : tasks.worker_pid=None task_runs.worker_pid=None (cleared by the terminal transition)
task B       : run=3 pid=<pid B1> run_status=blocked task_status=blocked
successor    : spawned=['<successor task>']
stale at spawn: {"<pid A1>": false, "<pid A2>": false, "<pid B1>": false}
reap         : [{"task_id": "<card A>", "run_id": 1, "run_outcome": "blocked", "task_status": "triage", "prev_pid": <pid A1>, "recorded_start_time": 16784601, "termination_attempted": true, "terminated": true, "sigkill": false},
                {"task_id": "<card A>", "run_id": 2, "run_outcome": "blocked", "task_status": "triage", "prev_pid": <pid A2>, "recorded_start_time": 16784603, "termination_attempted": true, "terminated": true, "sigkill": false},
                {"task_id": "<successor task>", "run_id": 3, "run_outcome": "blocked", "task_status": "ready", "prev_pid": <pid B1>, "recorded_start_time": 16784805, "termination_attempted": true, "terminated": true, "sigkill": false}]
hold         : []
event kinds  : A=['created', 'claimed', 'spawned', 'blocked', 'unblocked', 'claimed', 'spawned', 'block_loop_detected', 'superseded_worker_termination', 'superseded_worker_termination'] B=['created', 'claimed', 'spawned', 'blocked', 'unblocked', 'superseded_worker_termination', 'claimed', 'spawned']
stale after  : alive={"<pid A1>": false, "<pid A2>": false, "<pid B1>": false} exit_codes={"<pid A1>": -15, "<pid A2>": -15, "<pid B1>": -15} workspace_writes_after_successor={"<pid A1>": 0, "<pid A2>": 0, "<pid B1>": 0}
verdict       : pass
EXIT=0
```

The action is *processed*, not merely absent: the tick reports the three reap payloads, each with `termination_attempted: true` and `terminated: true`; `exit_code -15` shows the SIGTERM that ended each stand-in; two durable `superseded_worker_termination` events land on the incident-shaped card and one on the second card; and the successor's own spawn callback observed every predecessor already dead. Zero superseded writes reach a workspace after the successor starts, and the successor is still spawned — the fix cannot deadlock progress.

```
$ CANARY_LIVE_BOARD_DB="$HERMES_KANBAN_DB" PYTHONPATH=$FIX $PY $S --case current --scratch <scratch> --json-out <out>
case          : current
current run  : id=1 pid=<pid> (no terminal transition)
tick 1       : elapsed=0.002s reaped=[] held=[] worker_alive=True
tick 2       : elapsed=6.004s reaped=[] held=[] worker_alive=True
tick 3       : elapsed=12.007s reaped=[] held=[] worker_alive=True
tick 4       : elapsed=18.009s reaped=[] held=[] worker_alive=True
worker alive : True after 18.01s and 4 ticks
event kinds  : ['created', 'claimed', 'spawned']
verdict       : pass
EXIT=0
```

The counter-case: a genuinely live worker whose run is still current is never a candidate — no reap, no hold, no termination event, after four ticks and 18 s of wall clock (and the eight-hour/current-run case is pinned in the unit test). Duration alone never kills live work.

**Known limitation of the canary, stated rather than papered over:** a process that survives SIGKILL cannot be fabricated for a real demonstration, so the *held-spawn* path is proven by the unit test `test_dispatch_tick_withholds_spawn_when_the_worker_survives_termination` (which makes the signal a no-op for the stand-in pid) instead of by the canary. The canary proves the reap, the ordering and the counter-case.

### 5.4 Artifact reconstruction

```
$ cd <BASE> && git rev-parse HEAD
9031bae0e8b0ab40c4fd7ba50c644972ff512611
$ git apply --check <unit>/patches/hermes/HLP-426-terminal-worker-reap.patch
APPLY-CHECK: PASS
$ git apply <unit>/patches/hermes/HLP-426-terminal-worker-reap.patch
applied
$ for f in hermes_cli/kanban.py hermes_cli/kanban_db.py tests/hermes_cli/test_kanban_superseded_worker_reap_450.py; do …; done
hermes_cli/kanban.py                                         IDENTICAL
hermes_cli/kanban_db.py                                      IDENTICAL
tests/hermes_cli/test_kanban_superseded_worker_reap_450.py   IDENTICAL
$ git checkout -- . && git status --short
(base worktree restored clean)
```

The patch's SHA-256 is `97dc0294b9909e9648bce9d6dbdde4ce7dd379d6cf2114b8c1713b8ee07b2e81` (regenerated for the published lineage); applying it to the base revision reconstructs the three changed paths into tree `0253df7de573ea695206a5f3bf2407cb3e48e320`, exactly the tree of published fork commit `21628fc3790d825b8dc8082134f5cd382ec551f2` and of the `aether-main` merge `7a4fdcd…`.

## 6. HLP record, rollback and retirement

The downstream record is `patches/hermes/HLP-426-terminal-worker-reap.patch` with its evidence section in `HERMES_LOCAL_PATCHES.md` (`### HLP-426` plus the index-table row), following the existing `patches/hermes/` convention and PD-65:

- **Rollback:** reverse only this portable patch after a hash check (`git apply --check -R` on a tree at the exact base revision), or revert fork commit `21628fc…`. Nothing else is touched by reverting: `_end_run`, `block_task`, every reclaim path, both lanes' claim sequence and the existing dispatch phases are unchanged, there is no schema or state migration, and boards/runs/events/sessions/workspaces created before the revert stay readable. The only residue is inert history (the new events and the two extra `spawned` payload keys).
- **Retirement:** an adopted exact Hermes release must terminate (or refuse to spawn a successor for) a worker whose run has already ended and is no longer current, must not use elapsed time as the criterion, and must pass the new focused module plus the canary without this patch. Adopting upstream's `archive_task` termination (its `#76196` fix) is explicitly **not** sufficient: different trigger, no successor-boundary guarantee.
- **Structured reconciliation entry (produced in the integration lane):** `entries/HLP-426.json` and the regenerated aggregate were produced **after** the merge into `aether-main`, as designed — this patch adds a test file that did not exist at the previously selected revision, so an entry declared earlier would have been recorded as `selected_source: absent` and refused preparation. Two structural requirements had to be corrected for the entry to be accepted at all, and both were found by reading the validator rather than guessing: the ledger's HLP-426 heading was promoted from `###` to `##` (detailed sections are recognised only at that level, so the section was invisible and the entry would have been rejected as an unknown ledger ID), and the entry carries the corpus's shared `upstream.inspected_revision`, which the validator enforces identically across every entry. The regenerated aggregate records the merged fork revision `7a4fdcd…`.

## 7. Board integrity

- The live board was read twice, both times through a read-only SQLite URI (`mode=ro`) SELECT (run/event history for the affected card, plus the owning session's stored transcript). **No write, no mutation, no deletion, no schema change** — no SQLite write statement was executed anywhere in this unit, and no state-mutating board tool was called against the live board.
- All canary and test activity ran against disposable scratch boards, each a fresh `HERMES_HOME` with its own `kanban.db`; the canary fails closed if its resolved DB is not inside its scratch root.
- The recovery evidence for #450 (issue body/comment, board rows, events) was not edited or rewritten.

## 8. Scope corrections applied mid-unit, and residual limitations

- **`.github/workflows/policy.yml` restored.** The base-manifest allow-list entry for the new patch was drafted and then reverted to the unit base on the design steward's scope correction: `.github/workflows/*` is outside this unit's writable surface. The consequence is measured, not estimated — emulating the workflow's own manifest check (`heredoc` from `policy.yml` vs `git ls-files | grep -v '^specs/'`, both sorted) yields exactly one unlisted tracked path:

  ```
  unlisted tracked paths: ['patches/hermes/HLP-426-terminal-worker-reap.patch']
  manifest entries with no tracked file: []
  ```

  Supervisor adds that one line under its own authority; the fix and its evidence do not depend on it.
- **Committed reconciliation evidence is stale in one derived section, for the same reason.** The HLP convention requires the `HERMES_LOCAL_PATCHES.md` record, and that file's digest is one of the aggregate's committed inputs, so `scripts/validate_hermes_patch_reconciliation.py --check --fork-checkout <clean checkout at the selected revision>` now reports `status: stale`, `differing sections: source_ledger_sha256` — nothing else differs: `records: 29`, `present: 27`, `partial: 0`, `absent: 0`, `unverified: [HLP-246, HLP-247]`, `refusing: []`. Regenerating the derived aggregate/preflight is the same mechanical step the merge already requires (the entry for `HLP-426` can only be declared once the pinned revision contains the patch), and that step belongs to the Supervisor/integration lane, so it is recorded here rather than absorbed:

  ```bash
  uv run --frozen python scripts/validate_hermes_patch_reconciliation.py \
      --observed-at-utc <UTC timestamp> \
      --fork-checkout <checkout at the revision the release lock will pin>
  ```
- **Scratch removed from the deliverable.** The canary's scratch `HERMES_HOME`/board directory (databases, logs, marker files) is disposable and was deleted before handoff; the raw verdicts and the exact local identifiers it produced are recorded in the unit card's handoff notes.
- **Aether-side checks run locally on this commit:** `scripts/check_public_artifacts.py` → passed; `scripts/check_documentation.py` → passed; `uv run --frozen python -m pytest tests/test_hermes_patch_reconciliation.py -q` → 23 passed; `python3 -m unittest discover -s tests -p 'test_policy_hooks.py'` → 24 tests OK; the reconciliation `--check` result quoted above.
- **Source-only delivery.** The fix is *not* active in the running installation: the live runtime still loads its own release tree, and this unit performed no activation, reload, selector change, service restart or runtime promotion. No claim is made that the live environment is repaired.
- **Between the run ending and the next tick** a superseded process can still run (up to one dispatch interval). What the fix guarantees is the accepted invariant — no successor starts beside it — not instantaneous exit. The "exits" half is satisfied by termination at the successor boundary; making a worker observe its own supersession mid-turn would be a separate, larger change and was not authorized here.
- **Runs spawned before this change** carry no fingerprint in their `spawned` event and are therefore never signalled by the reap (it refuses to guess). That is a deliberate fail-safe; a pre-existing stale worker from an older runtime remains an operator action.
- **Forward obligation (not fulfilled here, recorded):** the accepted commit must be merged into the maintained fork's `aether-main` and pinned into rc.2 before any rc.2 activation; the Supervisor review lane owns that publication, and rc.2's own contract must carry the pin. The reconciliation entry/aggregate regeneration and the workflow allow-list entry belong to that same step.
- **Not attempted:** no push, PR, merge, dispatch, tag, release, issue mutation, workflow change, `VERSION`/`CHANGELOG.md`/`README.md` edit, and no change to the live runtime selector, launcher, service unit or any live service. The published `v1.0.0-rc.1` tag and its release assets are untouched.

## 9. Reproduction recipe

```bash
# 1. worktree (from the maintained fork, after fetching aether-main)
git -C <fork> fetch origin aether-main
git -C <fork> worktree add .worktrees/<name> -b <branch> origin/aether-main
cd <fork>/.worktrees/<name> && uv sync --locked --python 3.11 --extra all --extra dev

# 2. focused tests + affected surface
scripts/run_tests.sh tests/hermes_cli/test_kanban_superseded_worker_reap_450.py -q
scripts/run_tests.sh tests/hermes_cli/test_kanban*.py tests/gateway/test_kanban*.py \
    tests/tools/test_kanban*.py tests/run_agent/test_kanban*.py tests/plugins/test_kanban*.py -q

# 3. disposable-board canary, base vs candidate (never the live board)
CANARY_LIVE_BOARD_DB="$HERMES_KANBAN_DB" PYTHONPATH=<tree> <tree>/.venv/bin/python \
    <unit>/specs/001-aether-v1-productization/fixtures/qualify_superseded_worker_reap_450.py \
    --case coexist --scratch <scratch>
CANARY_LIVE_BOARD_DB="$HERMES_KANBAN_DB" PYTHONPATH=<tree> <tree>/.venv/bin/python \
    <unit>/specs/001-aether-v1-productization/fixtures/qualify_superseded_worker_reap_450.py \
    --case current --scratch <scratch>
```

## 10. Publication, review outcome and integration corrections (review lane)

The unit delivered proven, unpushed source plus its evidence. The review lane then
consumed the design-steward review direction and published a **sanitized lineage**,
and completed the three integration obligations the unit had correctly routed. This
section is the review record; §§1–9 above stay as the delivering unit wrote them,
with the identity references updated in place.

### 10.1 What was published, and how equivalence was proved

- The pre-publication candidate **`622678ef…` was not pushed.** It is preserved
  locally, unpushed and unrewritten, as exact evidence, per the direction.
- Published commit **`21628fc3790d825b8dc8082134f5cd382ec551f2`**, whose parent is
  the pinned base `9031bae0e8b0ab40c4fd7ba50c644972ff512611`, merged to `aether-main`
  by fork PR #14 as **`7a4fdcd083409c31c09cfa3bfa345354e8576a7e`**. The merge tree and
  the sanitized commit's tree are the same object (`0253df7de5…`), so the published
  content is exactly what the merge records.
- **Delta against the reviewed candidate: exactly one file, 6 insertions / 6
  deletions** — the new test module's docstring. Nothing else differs.
- **Executable content is proved identical, not assumed:** with the module docstring
  removed, the parsed syntax tree of the test module is byte-identical to the
  candidate's, and `hermes_cli/kanban_db.py` and `hermes_cli/kanban.py` are unchanged
  against the candidate.
- **Behavior re-verified at the sanitized commit:** `scripts/run_tests.sh
  tests/hermes_cli/test_kanban_superseded_worker_reap_450.py -q` → **11 passed, 0
  failed** (8.2 s, same runner and interpreter as the unit's runs).

### 10.2 A bounded extension of the same correction, and why it was necessary

The review direction stated that "its commit message contains the private Objective
Contract/card/run identities" and asked for the reviewed tree to be reproduced. A
full audit found the same identity class **inside the tree as well**: the new test
module's docstring named the task and both run numbers. Root `AGENTS.md` excludes
boards and runtime state from public artifacts, and a commit message is not the only
public surface — the tree is too, and the Aether-side patch and fixture carried the
same references.

So the same bounded sanitization was applied to the tree and the fixture, and the
direction's equivalence step was satisfied in the only form the two requirements
admit together: **the sole delta from the reviewed candidate is the sanitized
docstring**, with executable content proved identical and the focused suite green at
the published commit. The alternative — publishing the tree byte-identically — would
have written board identities into a public repository, which the canon forbids.
Deviating from a direction's *method* while satisfying its *purpose* is recorded here
rather than left implicit; if the intended reading was literal byte-equality
including those references, the preserved candidate allows the decision to be revisited
without any history rewrite.

### 10.3 Aether-side corrections completed in this lane

- **`.gitattributes`** gains `patches/hermes/HLP-426-terminal-worker-reap.patch
  whitespace=-trailing-space`, following the existing convention for unified patches
  whose blank context lines require the prefix space. `git diff --check` over the full
  range (`d2559cd..HEAD`) is now clean (rc 0), where it previously exited 2 on ten
  required context lines.
- **Policy base-manifest allow-list** gains the new patch path. Emulating the
  workflow's own check (heredoc list vs `git ls-files | grep -v '^specs/'`, both
  sorted) now reports `407 == 407`, **no** unlisted tracked path and **no** phantom
  manifest entry.
- **Portable patch regenerated** for the published lineage: SHA-256
  `97dc0294b9909e9648bce9d6dbdde4ce7dd379d6cf2114b8c1713b8ee07b2e81`. Applying it to a
  freshly materialized tree at `9031bae0e8b0ab40c4fd7ba50c644972ff512611` reconstructs
  the three changed paths into tree `0253df7de573ea695206a5f3bf2407cb3e48e320` — equal
  to the published fork commit and to the `aether-main` merge. The regeneration method
  itself was validated first by reproducing the pre-publication patch **byte for byte**
  from the candidate.
- **Structured reconciliation entry** `entries/HLP-426.json` created, and the aggregate
  regenerated at the merged revision: `status: current`, `records: 30`,
  `present: 28`, `partial: 0`, `absent: 0`, `unverified: [HLP-246, HLP-247]`,
  `refusing: []`.
- **Two structural requirements were found by reading the validator, not by guessing,
  and both were corrected:** detailed ledger sections are recognised only at `##`
  level, so the section heading was promoted from `###` (otherwise the entry is
  rejected as an unknown ledger id and the section is invisible), and the entry must
  carry the corpus's shared `upstream.inspected_revision`, which the validator enforces
  identically across every entry.
- **The corpus expectations in `tests/test_hermes_patch_reconciliation.py` grew with
  the corpus:** the new id joins `EXPECTED_ACTIVE_IDS` and its patch digest joins
  `PATCH_DIGESTS`. No assertion was weakened and none was removed — the count is
  unchanged at **23 passed**, matching the pre-change baseline at the same revision.
- **Fixture references sanitized:** the two incident-shape mentions that named a board
  run number now read as the incident recorded in #450, keeping the causal description
  without the board identifiers.

### 10.4 Observations recorded, not corrected

- **The new canary fixture adds one lint finding and one format difference, and both sit
  outside the CI gate.** `specs/…/qualify_superseded_worker_reap_450.py` has an unused
  `board_db` assignment (`F841`) and one string-literal style difference. The repository's
  ruff gate lints `src`, `tests` and named `scripts/` files — not `specs/**` — and the
  `specs/` corpus already carries two findings and six unformatted files at the current
  `main`, so this matches the corpus rather than regressing a gate. It was left byte-identical
  to the bytes the canary runs used: editing the fixture would invalidate the RED/GREEN runs
  recorded in §5.3 without re-running them, which a review lane should not do silently.
- **Pre-existing board identifiers elsewhere in the ledger were reported, not touched.**
  Three lines of `HERMES_LOCAL_PATCHES.md` (from earlier HLPs) carry five distinct task ids;
  every one is already present at the current `main`, and this unit introduced none. Correcting
  that corpus is a separate bounded change, not part of this integration.
- **Both were measured against the pre-change tree at the same revision** (baseline: two lint
  findings and six unformatted files under `specs/`; the new fixture accounts for exactly the
  +1/+1 delta), and the CI-scope gate itself is clean here (`ruff check src tests` →
  "All checks passed!", `ruff format --check src tests` → 150 files already formatted).

### 10.5 Non-claims

No `v1.0.0-rc.2` authority is created or implied here; rc.2 needs its own superseding
finalized contract. Nothing was activated: the live runtime, its selector, launcher,
service, profile and the published `v1.0.0-rc.1` tag, release and assets are untouched
by this lane. Fork Actions are inherited and remain disabled, so no fork CI result is
claimed — the evidence above is from the repository's own test runner. The forward
obligation stands recorded rather than fulfilled: the accepted fork revision
`7a4fdcd…` must be pinned by rc.2 before any rc.2 activation.
