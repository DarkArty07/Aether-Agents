# R11 session handoff — 2026-07-25

## Exact stop point

The session was stopped at the user's request while R11 verification and closeout remained incomplete.

- Repository: `/home/arty/Escritorio/agentes/aether`
- Branch: `feature/v0.19.0-autonomous-coordination-design`
- Implementation base before this documentation checkpoint: `c276f88 feat(coordination): establish durable kernel workflow`
- This handoff is versioned by the exact commit subject `docs: checkpoint R11 verification`; verify that commit's parent is `c276f88`.
- Committed R11 RED contract: `869efee test(coordination): define R11 dispatch fencing contract`
- R11 state: **IMPLEMENTED AND FOCUSED-GREEN, PENDING CANONICAL VERIFICATION**
- Staging area: empty at stop
- Runtime activation: not performed
- Live ACP execution: not performed
- Pilot, merge, tag, deployment and publication: not performed
- Athena remains suspended by user policy.

Do not mark R11 complete or begin R12 from this checkpoint. The candidate remains uncommitted because full regression, lint/format, compile, migration/fault review, staged-candidate inspection and final scope scans have not all passed.

## What was implemented

R11 now has a kernel-backed dispatch composition candidate covering:

1. durable `dispatch.staged` before an Olympus/ACP effect;
2. deterministic immutable authority bound to installation, project, run, task, attempt, contract generation/revocation epoch, agent, plan revision, snapshot, logical session and attempt fence;
3. a per-attempt authority lease separate from the transport/outbox claim lease;
4. public ledger APIs for aggregate version, event lookup, lease lookup and exact outbox-message lookup;
5. outbox claim by `message_id`, preventing claims of unrelated workflow rows;
6. complete outbox visibility instead of hiding pre-R11 durable rows;
7. asynchronous dispatch, observe and cancel delivery through `OlympusRuntimeAdapter` public seams;
8. Olympus lifecycle composition through public `spawn_agent`, `send_message`, `poll` and `close` operations;
9. durable logical/ACP session binding;
10. delivery ACK separated from semantic task completion;
11. pre-acceptance retry classification and post-acceptance uncertainty as durable `UNKNOWN`;
12. retry suppression while uncertainty remains unresolved;
13. typed reconciliation evidence bound to the exact dispatch authority;
14. cancellation intent persisted before cancellation effect;
15. stale/expired/superseded fence rejection before runtime effects or result acceptance;
16. durable/idempotent technical observations without asserting semantic completion;
17. exact R11 event schemas and transition validation through generic append/replay;
18. explicit rejection of forged `dispatch.staged`, `dispatch.unknown` and expanded `session.bound` events;
19. no dispatcher access to the ledger's private SQLite connection;
20. no new `PilotStore` path or dual-write in kernel dispatch.

Primary production candidate:

- `src/olympus_v3/coordination/kernel_dispatcher.py` — new, untracked at stop.

Narrow supporting modifications:

- `src/olympus_v3/coordination/__init__.py`
- `src/olympus_v3/coordination/kernel_runtime.py`
- `src/olympus_v3/coordination/ledger.py`
- `src/olympus_v3/coordination/olympus_adapter.py`
- `src/olympus_v3/coordination/projections.py`
- `src/olympus_v3/coordination/workflow.py`
- `tests/coordination/test_kernel_dispatcher.py`
- `tests/coordination/test_kernel_fencing.py`

## Defects found and corrected during direct audit

The initial delegated GREEN suite was not accepted as sufficient. Direct review found and corrected:

- the attempt authority incorrectly reused the shared `outbox` lease;
- dispatcher code read `ledger.conn` directly;
- generic outbox claim could lease unrelated workflow messages;
- `outbox()` hid existing durable rows to satisfy an R11 test;
- a global `UNKNOWN` blocked independent tasks;
- a persistence failure after an accepted effect could escape without durable uncertainty;
- observations were not durably idempotent;
- live attempts could be reconciled as expired;
- supersession accepted non-monotonic replacements;
- R11 event kinds lacked exact semantic validation at generic append/replay boundaries;
- the Olympus adapter had no explicit authoritative kernel dispatch/observe/cancel seam;
- cancel intent had no separate async delivery path;
- future `RETRY_WAIT` rows could be redelivered too early;
- `reconciliation.completed` was missing from projection/authority event registries.

Adversarial tests were added for these equivalence classes, including effect-accepted/binding-write-failed → `UNKNOWN`, task-local uncertainty, generic-event forgery, attempt-vs-transport fencing, real adapter composition with a public manager fake, live-fence reconciliation rejection and monotonic supersession.

## Executable evidence

Fresh focused R11 result after the final behavioral changes:

```text
pytest -q tests/coordination/test_kernel_dispatcher.py tests/coordination/test_kernel_fencing.py
37 passed in 1.32s
```

An earlier expanded coordination regression, before the final hardening edits, passed:

```text
105 passed in 1.71s
```

It included dispatcher, fencing, workflow, workflow security, budget, ledger transport fencing, native transport and Olympus adapter tests. Because later production/test changes were made, this earlier 105-pass result is historical evidence only and must be rerun.

The latest Ruff invocation did not pass. It reported **48 editorial errors**, concentrated in the two R11 test files: unsorted imports, unused import/local, and compressed semicolon/one-line `with` statements. Production syntax checks performed by patch tooling passed, but that is not a substitute for the canonical lint/compile gate.

`git diff --check` passed before the final small hardening edits. It must be rerun against the final candidate.

No full repository suite was run after the final R11 changes. No completion commit exists.

## Verification still required

These are required before an R11 completion claim:

1. format the two R11 tests without changing assertions or behavior;
2. rerun the focused 37-test matrix;
3. rerun the expanded coordination regression against the final files;
4. run the complete repository suite;
5. run focused Ruff and compile checks;
6. rerun `git diff --check` and ownership/forbidden-dependency scans;
7. inspect every R11 test body against the roadmap invariants;
8. test the outbox schema migration from a legacy database, including row preservation, rollback/fault behavior and index recreation;
9. verify the `UNKNOWN` event/outbox projection remains fail-closed at every crash boundary; determine whether an atomic ledger primitive or deterministic recovery repair is required;
10. review transport-worker identity: the default stable owner is useful for restart recovery but may be insufficient for multiple concurrent dispatchers sharing one owner; prove the approved concurrency-1 boundary or introduce an explicit worker identity/fence contract;
11. inspect retry timing so a future `RETRY_WAIT` neither redispatches early nor blocks an independent due message;
12. verify exact public exports/signatures and no private ACP/SQLite access;
13. verify no `PilotStore`, dual-write, subprocess or semantic-completion path entered the R11 candidate;
14. stage only the declared R11 implementation paths and inspect the complete cached diff, including the untracked dispatcher; this handoff and the two convergence documents are already preserved by the documentation checkpoint;
15. only after all gates pass, create one atomic R11 implementation commit and update continuity/roadmap to COMPLETE.

## Dirty-tree and staging boundaries

The staging area was empty at stop. All R11 implementation changes are unstaged; `kernel_dispatcher.py` and this handoff are untracked.

The worktree also contains substantial pre-existing or unrelated changes. In particular, do not absorb:

- `home/**` configuration, skill, backup, state or runtime artifacts;
- `.olympus/**` and profile-local `.olympus/**`;
- `uv.lock` unless separately justified;
- R8 pilot source/tests and `R8_SESSION_HANDOFF_2026-07-23.md`;
- router/provider migration artifacts;
- research files unrelated to R11.

Some modified coordination files belong to uncommitted R8 work:

- `scripts/run_r8_snake_pilot.py`
- `src/olympus_v3/coordination/pilot.py`
- `src/olympus_v3/coordination/pilot_evidence.py`
- `src/olympus_v3/coordination/pilot_model.py`
- `src/olympus_v3/coordination/pilot_store.py`
- pilot tests.

Use explicit path staging only. Never use `git add -A` or broad coordination-directory staging.

## Olympus session anomaly

Continuity projected Hefesto session `094d77f6-c4ec-4844-9d5e-d3bd194829f2` as active with no heartbeat and only old completed tool calls. `talk_to(close)` returned `Unknown session`.

- No duplicate writer was launched.
- Treat the continuity row as stale, not as proof of active work.
- Project continuity issue: `#46`.
- GitHub framework issue: `DarkArty07/Aether-Agents#99`.

## Exact resume procedure

1. Read this handoff, `.aether/CONTEXT.md`, the R11 roadmap block and current Git status.
2. Confirm branch/HEAD and preserve the full dirty baseline.
3. Format only the R11 tests:

```bash
ruff format tests/coordination/test_kernel_dispatcher.py tests/coordination/test_kernel_fencing.py
ruff check --fix tests/coordination/test_kernel_dispatcher.py tests/coordination/test_kernel_fencing.py
```

4. Review the formatting diff to ensure no assertion or fixture semantics changed.
5. Run the focused gate:

```bash
pytest -q tests/coordination/test_kernel_dispatcher.py tests/coordination/test_kernel_fencing.py
```

6. Run the final subsystem regression:

```bash
pytest -q \
  tests/coordination/test_kernel_dispatcher.py \
  tests/coordination/test_kernel_fencing.py \
  tests/coordination/test_kernel_workflow.py \
  tests/coordination/test_kernel_workflow_security.py \
  tests/coordination/test_kernel_budget.py \
  tests/coordination/test_ledger_transport_fencing.py \
  tests/coordination/test_native_transport.py \
  tests/coordination/test_olympus_adapter.py
```

7. Add durable migration/fault/concurrency tests for the pending equivalence classes, then rerun steps 5–6.
8. Run full gates:

```bash
pytest -q
ruff check src/olympus_v3/coordination tests/coordination
python -m compileall -q src/olympus_v3 tests/coordination
git diff --check
```

9. Run negative source scans for `PilotStore`, `pilot_store`, private `.conn`, private ACP manager registries, subprocesses and semantic completion in the R11 path.
10. Reconcile every R11 roadmap bullet with exact production and test evidence.
11. Stage only:

```text
src/olympus_v3/coordination/__init__.py
src/olympus_v3/coordination/kernel_runtime.py
src/olympus_v3/coordination/ledger.py
src/olympus_v3/coordination/olympus_adapter.py
src/olympus_v3/coordination/projections.py
src/olympus_v3/coordination/workflow.py
src/olympus_v3/coordination/kernel_dispatcher.py
tests/coordination/test_kernel_dispatcher.py
tests/coordination/test_kernel_fencing.py
```

12. Inspect cached names/stat/diff, cached diff-check and secret scan. Commit only after the complete gate is green.
13. Update `.aether` phase/task, curate, read back `CONTEXT.md`, and only then advance to R12.

## Scope exclusions preserved

This checkpoint does not authorize or claim:

- live ACP execution;
- a real Daimon dispatch;
- R12 evidence/review implementation;
- R13 closure implementation;
- R14 Snake execution;
- Athena use;
- gateway/config/auth mutation;
- PilotStore migration or historical R8 rewriting;
- merge, tag, deployment, release or publication.
