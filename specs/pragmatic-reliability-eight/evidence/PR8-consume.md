# PR8-CONSUME — consumed #396/#397/#399 revisions, supported #399 wiring and canaries

**Unit:** PR8-CONSUME of Objective Contract `oc_c780a10d94b78d85@v1`
(SHA-256 `0fdd7931cc77e75eecc20e37c32f1352afbd8bf91869340aa092ac20e12905a5`), sources
`specs/pragmatic-reliability-eight/spec.md` §R396/§R397/§R399 and "Aggregate acceptance",
`plan.md` §D1/§D4.2.

**Delivered:** verification of the merged `oc_291b2fb34b413d92@v2` results from the exact
revisions, verification and consumption of the supported product-owned #399 entry point, and
revision-bound canaries for #396/#397/#399. No accepted candidate was reimplemented,
duplicated or rewritten, and this unit changes **no source, test, documentation, workflow or
public surface** — it adds this evidence record plus the integration-base merge.

## 1. Revision

| Item | Value |
| --- | --- |
| Unit branch | `aether-agents-2/t_d9886b56-pr8-consume-consume-accepted-396-397-399` |
| Contract base | `0a41438a13a0655b07703910b605e595f55aa660` |
| Integration base merged into the unit branch | `8323a789f11b1537f6d5029e4ea2cc677dc6892a` (parents `0a41438a` and `67d7226d393da923d8cdb6f6c3781849b4ded273`) |
| `origin/main` at consumption | `67d7226d393da923d8cdb6f6c3781849b4ded273` (PR #410 merge) |
| Measurement tree | the worktree at `8323a78` — its source tree is identical to `origin/main`; every command below ran there |

## 2. Consumed revisions (verified on `main`, not from a board summary)

Each row was verified with `git merge-base --is-ancestor <revision> origin/main` (all
"yes") and with `git rev-parse <revision>:<evidence path>` + `git cat-file -e <blob>` for
the evidence file at that exact revision.

| Issue | Accepted unit tip (review card) | Evidence reachable at that revision | Merged to `main` |
| --- | --- | --- | --- |
| #396 | `ef3d820653b05a2e919db96455877c615679d8d3` (`t_ee6374fa`, round-4 approved) | `specs/007-session-residual-stability/evidence/SR-396.md` blob `aee02d7bdd927e22fdf32645638d369d5673e212` | merge `09bad01cb0e90a51af76176b6e52ab0a07302741`, then PR #408 → `39a094653209cc022a2afb7ce509a0aa4ebc5ba7` |
| #397 | `6f753d0c7c8d1984b68c7bcff4ac5678b746b057` (`t_9f54c3cf`, round-2 approved) | `specs/007-session-residual-stability/evidence/SR-397.md` blob `b8dba5539dbdf99c44c0128a04530fcdf684c050` | merge `1b59a792b2769b1382ae17b16827f3b4d327a4b2`, then PR #408 → `39a0946` |
| #399 | `2fe83ebb2cc06a2041f1f9f6caa2bd4973159efc` (`t_435b2b6b`, round-2 approved) | `specs/007-session-residual-stability/evidence/SR-399.md` blob `449a58099ab676522ec8e83c9b3675be3916b40d` | merge `0d70c09e19ac7787557a1a1b047a57cdec26855c`, then PR #408 → `39a0946` |
| #227 (context) | `b6fba98fbd4ba91bc1ecd8e29d3c14983436c334` | `specs/007-session-residual-stability/evidence/SR-227.md` blob `5bd881b3bbe75636a730d55f32fddb02ecd10a7c` | merge `021440db9c0713544342a483dc1055b6ba121eda`, then PR #408 → `39a0946` |

Additionally consumed: the deferred wiring `82b7083cc5fde23e50379a0373af5eb8c2fa1f67`, the
integration ledger `a83df7b75dc9607168c9772ca372859727525ceb`, the `origin/main` merge
`26f7a55`, and the acceptance ledger `1334e2b` (PR #409). The residual terminal closeout
(comment 18 on `t_9695446a`, board
`oc-12027989a08f41cda82c54ff1bfb6b03-291b2fb34b413d92-v2`) records the same revisions and
that #227/#396/#397/#399 were closed on this main/runtime evidence.

### External gate

- Residual flow `oc_291b2fb34b413d92@v2`: every card on its board is `done`, including the
  terminal integration `t_9695446a` and `t_124002ae`; PR #408 merged `39a0946`. Gate open.
- Monitor prerequisite `oc_f8c9fc9320587cf3@v4` was **not accepted**: the owner stopped that
  objective ("closed as stopped/incomplete, not accepted"); its integrated candidate and the
  D18 repair reached `main` through PR #405/PR #406, and the residual flow consumed only
  that. This unit touched no Monitor-owned file, board state or job.
- The gate check `git merge-base --is-ancestor` confirms the accepted commits are on `main`
  rather than only on an integration branch.

## 3. Supported #399 entry point (verified and consumed)

- Accepted core: `aether_agents.hermes_editable.reconcile_hermes_editable`
  (`src/aether_agents/hermes_editable.py:731`) with the transactional guarantees of
  SR-399 (pre-flight editable-target refusal, private backups, local `--no-deps --offline`
  reinstall, atomic rollback, `env -i`/`python -I` canaries, source/status fingerprints).
- Supported product-owned entry point: `LifecycleManager.reconcile_runtime_editable`
  (`src/aether_agents/lifecycle.py:4714`, delivered by the consumed wiring `82b7083`), which
  delegates to that operation with only `offline` and `verify_imports` exposed. It is shared
  with the lifecycle installer and was the operation the consumed flow used for the live
  runtime adoption.
- Reachability was proven by execution, not by reading: both canary parts in §4.3 reach the
  core **exclusively** through
  `LifecycleManager(store=ReleaseStore(data_root(), state_root=state_root()),
  python_executable=...)`. Constructing that seam is inert (it created no data/state
  directory before the call).
- **No new public surface was added.** SR-399 §6.2 recorded an intended operator CLI surface
  (`aether hermes reconcile-editable`); the residual terminal integration explicitly deferred
  it as a *public-interface and compatibility-class decision*
  (`specs/007-session-residual-stability/evidence.md`, "Deferred routing decisions" item 1),
  and the Morfeo material-design clarification delivered to this card during the run
  prohibits adding a public command, parser surface, docs command or capability entry:
  "#399 is already wired through the reviewed … operation and proven in merged runtime. This
  unit should verify/consume that exact supported product-owned lifecycle seam and add
  evidence only". The clarification names that seam `reconcile_hermes_editable_runtime`; the
  delivered symbol is `reconcile_runtime_editable` (file:line above). No rename was performed
  — that symbol is merged public API and renaming it is not this unit's decision. An initial
  CLI draft was reverted **uncommitted** when the clarification arrived; `git diff` against
  the integration base shows no source change.
- The two other items of the unit's deferred-wiring list were delivered by the consumed flow:
  the lifecycle-installer sharing and the `.github/workflows/policy.yml` manifest lines for
  the new tracked files (both in `82b7083`).

## 4. Canaries at the integrated revision (disposable state)

Window: `2026-09-12T02:24:59Z` → `2026-09-12T02:26:37Z`, in the worktree at `8323a78`.
The disposition is stated once for the whole section: every canary below used disposable
state (temporary directories and disposable boards/virtualenvs); no live board, live
interpreter, source checkout or runtime state was mutated.

Canary tooling is disposable (the same practice the consumed flow recorded for its own
canary wrappers). Commands are given with `<worktree>` / `<aether-home>` placeholders:

```bash
# live-state capture/compare (read-only)
python3 /tmp/pr8-consume/live_board_fingerprint.py <aether-home>/kanban/boards capture t_d9886b56
uv run --frozen python /tmp/pr8-consume/live_runtime_fingerprint.py <worktree> \
  <aether-home>/.venv-hermes/src/hermes-agent \
  <aether-home>/.venv-hermes/bin/python \
  <aether-home>/.venv-hermes/src/hermes-agent/.venv/bin/python
# canaries (isolated exact-Hermes test bootstrap, as scripts/run_tests.py uses)
uv run --frozen python /tmp/pr8-consume/run_with_exact_hermes.py <worktree> /tmp/pr8-consume/canary_396.py
uv run --frozen python /tmp/pr8-consume/run_with_exact_hermes.py <worktree> /tmp/pr8-consume/canary_399.py \
  <aether-home>/.venv-hermes/src/hermes-agent \
  <aether-home>/.venv-hermes/bin/python \
  <aether-home>/.venv-hermes/src/hermes-agent/.venv/bin/python
# reviewed writer-probe lane (#397) and the focused lanes of the consumed areas
python3 scripts/run_tests.py -- -q tests/test_lab_writer_isolation.py tests/test_e2e15_qualification.py \
  tests/test_e2e_harness.py tests/test_lab_formalization.py
python3 scripts/run_tests.py -- -q -k "test_u396_" tests/test_observation_cli_plugin.py
python3 scripts/run_tests.py -- -q tests/test_hermes_editable.py
```

### 4.1 #396 — a contract trace reads its own provisioned board

Disposable Kanban home with two isolated, canonically-provisioned contract boards that carry
the *same* observation trace id under different project/contract identities. The reviewed
capture-plugin path (`prepare_handoff` hook → native reconciliation → ingest/reduce/query)
runs against the bound board.

| Check | Observed |
| --- | --- |
| Bound board root + child resolved | `units = ["t_10000001", "t_10000002"]`, `relations = ["t_10000001:root", "t_10000002:unknown"]`, `project_id` = the bound project |
| Freshness | `as_of = 2026-09-12T02:25:27.285Z`, measured age 0.23 s |
| Explicit coverage gaps retained | 5 codes (`AUTHORITY_CONTEXT_UNAVAILABLE`, `NEGATIVE_OR_REVERSED_INTERVAL`, `ORIGIN_NO_CANDIDATE`, `WORK_UNIT_CLASSIFICATION_UNKNOWN` ×2) |
| No raw content | no raw task-title sentinel and no foreign task id appears anywhere in the compact summary |
| Unrelated board untouched | the unrelated board (same trace id, other project/contract) is logically identical before/after: main-file digest, write-ahead log and every table unchanged; only the transient `-shm` index digest moved |
| Disposable bound board changed | yes — the trace wrote its own board's events (expected) |
| Focused fixture lane | `13 passed, 46 deselected in 2.47s` (`-k "test_u396_"`, incl. all §D396 negatives) |

### 4.2 #397 — a write-capable probe changes only disposable state

| Check | Observed |
| --- | --- |
| Reviewed writer-probe lane | `70 passed, 1 skipped in 7.95s` (`test_lab_writer_isolation` + `test_e2e15_qualification` + `test_e2e_harness` + `test_lab_formalization`) |
| Live-board canary around the lane | 58 live boards fingerprinted read-only before/after: 57 byte- and content-identical; the only change is on this unit's own execution board and only in this running card's rows (see §4.4) |
| Row-level attribution on this card's board | a separate 8.3 s window around the same lane: **zero** added/removed/changed rows in any table |
| SQL cleanup | none ran anywhere in this unit |
| No live-board mutation | no canary writes a live board; the writer probes construct verified disposable contexts first |

### 4.3 #399 — provisioned interpreters and the transaction, through the product seam

Part A mirrors the provisioned shape on disposable state: the source checkout lives inside
the virtualenv directory and its `.venv` entry is the same relative symlink the installation
uses, so both provisioned interpreter paths reach one shared environment.

| Check | Observed |
| --- | --- |
| RED before the call | newly intended module unresolvable (`find_spec` → `None`) on both interpreter paths |
| Transaction through the seam | receipt `status = reconciled`, `rolled_back = false`, both interpreters `reconciled` |
| GREEN after the call | both interpreter paths resolve **2/2** declared modules from the exact source and import them, under `env={}` + `python -I`, no `PYTHONPATH` |
| Source preservation | source-tree digest and the dirty `git status` (4 lines) byte-identical across the transaction |
| Forced second-interpreter failure | a real (non-injected) probe module raises only under the second disposable virtualenv; the transaction returns `status = rolled_back`, `rolled_back = true`, both interpreters `rolled_back`, reason `Canary check failed on … for modules: ['hermes_probe_failure']` |
| Metadata restoration | the first interpreter's editable metadata is byte-identical to its pre-transaction fingerprints (same for the second); after rollback the probe module is unresolved again on the first interpreter while the module reconciled by the previous successful transaction still resolves |
| Provisioned interpreters (read-only) | both paths resolve **20/20** declared modules from the exact live source, import them, and keep 24 editable artifacts each; the whole provisioned runtime fingerprint (source tree `f9b6edde…`, 49-line dirty status, both interpreters' artifacts) is **byte-identical** before/after the window |
| Focused lane | `15 passed in 25.37s` (`tests/test_hermes_editable.py`) |

### 4.4 Live-state preservation over the window

| Object | Observed |
| --- | --- |
| Provisioned Hermes source | tree digest `f9b6edde0bf50331901b2529ac763ebcf77e4d0efb95e8b68d393eca2889831f`, 49-line dirty status — identical before/after (matches the consumed flow's adoption record) |
| Provisioned interpreters | 24 editable artifacts each, all digests identical before/after |
| Live Kanban boards (58) | content view: 57 boards unchanged; this unit's own board changed **only** in this running card's rows — `task_events` heartbeat rows for `t_d9886b56` (4 rows between the two captures), `task_runs` row 46 `last_heartbeat_at`, and the matching `tasks` heartbeat column. A direct event query confirms those are the only rows written in the window |
| Foreign-content view (excluding this card's rows) | every table of every board identical; the only difference is the board file's byte digest, which moves when those heartbeat rows are written |
| Comparison rules | main-file digest, write-ahead-log content and every table (row counts + content digests) decide; an absent/empty `-wal` and a moved `-shm` index are transient SQLite artifacts and are reported, never counted as content |

## 5. Gates

| Gate | Command | Observed |
| --- | --- | --- |
| Environment | `uv sync --frozen` | resolved the locked 32-package dev environment, exit 0 |
| Focused suites for the consumed areas | §4.1–§4.3 commands | `70 passed / 1 skipped`, `13 passed`, `15 passed` |
| Byte-compile | `uv run --frozen python -m compileall -q <CI file set>` | exit 0 |
| Lint | `uv run --frozen ruff check <CI file set>` | `All checks passed!` |
| Format | `uv run --frozen ruff format --check <CI file set>` | `155 files already formatted` |
| Types | `uv run --frozen mypy src/aether_agents` | `Success: no issues found in 67 source files` |
| Documentation registry | `uv run --frozen python scripts/check_documentation.py` | `documentation validation passed` |
| Public artifacts | `uv run --frozen python scripts/check_public_artifacts.py --root .` | only the inherited `.aether/objective-contracts/oc_0084270d940c98d9/v1.md` findings (`absolute-user-home`, `operator-desktop-layout`); the file is byte-identical to `origin/main` (`git diff origin/main -- .aether` empty) and is the separately disclosed #403 blocker owned by PR8-CI. No new finding |
| Diff sanity | `git diff --stat origin/main` | no source/test/docs/workflow change from this unit beyond the contract-design files that `main` does not yet carry |

## 6. Compatibility impact (unit level)

`none` for this unit: no existing interface, behavior, packaging surface or public CLI
command is changed, and no new surface is added. The consumed revisions were already merged
to `main` before this unit ran; this unit contributes the integration-base merge, the
canary evidence and the deferred-wiring verification. Aggregate release conclusions remain
PR8-INT's.

## 7. Limits, observations and residual risk

1. **Operator CLI surface not delivered — by direction, not by omission.** SR-399 §6.2's
   `aether hermes reconcile-editable` remains unimplemented; the residual terminal lane
   deferred that public-interface/compatibility-class decision and Morfeo's clarification
   prohibits adding it. #399 is reachable through the supported lifecycle seam and the
   packaged operation, both proven by execution here. If the owner later authorizes the
   command, it needs a capabilities-registry entry and reference documentation (a compatible
   public addition) — recorded, not decided here.
2. **Symbol-name discrepancy recorded, not renamed.** The clarification refers to
   `reconcile_hermes_editable_runtime`; the merged symbol is
   `LifecycleManager.reconcile_runtime_editable` (`src/aether_agents/lifecycle.py:4714`).
3. **Canary tooling is disposable.** The wrappers live outside the repository (accepted
   practice in this objective); the repository-internal fixtures and lanes cited in §4 are
   re-runnable in place, and the canary logic is described above so an independent reviewer
   can re-derive it without this run's conversation.
4. **Byte-level vs content-level stability.** Live-board byte digests move whenever the
   supervising runtime writes its own heartbeat rows on the running card. Only content-level
   attribution is claimed, with the row-level proof in §4.4.
5. **Monitor prerequisite was stopped, not accepted.** Recorded in §2; this unit neither
   depends on nor modifies the Monitor flow.
6. **Observation canary coverage gaps** (5 codes) are the expected explicit gaps of a
   disposable trace with no authority context; they are retained, not suppressed.
7. **Runtime guard observations (reported, not routed around).** During the run: one
   unconditional command-parser block on an oversized inline shell command (recovered by
   using simple commands), and one pre-tool policy-hook timeout (recovered by reissuing the
   same read-only command, which then succeeded). Neither affected a result in this record;
   both are runtime-quality signals for Morfeo.
8. **No `PYTHONPATH` runtime workaround** was introduced. The canaries' origin/import checks
   execute with an empty environment (`env -i` + `python -I`); the only `PYTHONPATH` in play
   is `scripts/run_tests.py`'s documented exact-Hermes test bootstrap, which the repository
   already uses for its own suites.
