# PR8-FINAL — terminal integration, activation and closeout evidence

**Objective:** `oc_c780a10d94b78d85@v1` (SHA-256
`0fdd7931cc77e75eecc20e37c32f1352afbd8bf91869340aa092ac20e12905a5`), sources
`specs/pragmatic-reliability-eight/{spec,plan,research,quickstart,tasks}.md`.

**Scope of this record:** the terminal integration, publication, runtime activation,
per-issue canary reconfirmation, issue reconciliation, cleanup audit and the three
release conclusions. It complements the per-unit records (`PR8-review.md`,
`PR8-contract.md`, `PR8-ci.md`, `PR8-cron.md`, `PR8-ledger.md`, `PR8-consume.md`) and
does not restate them beyond the terminal facts.

## 1. Reviewed and merged revisions

Every unit below was independently reviewed by its Supervisor review card before
integration; no unreviewed candidate was merged.

| Unit | Aether branch tip | Fork candidate → merge (maintained fork `aether-main`) |
| --- | --- | --- |
| Root decomposition | `14d934adf1b467e425e274898eda1119ac56315c` | — |
| PR8-CONTRACT (#388) | `02157dfe06a8586deb4f188f5fba1645e684852e` | — |
| PR8-REVIEW (#385 guidance) | `d34219787da21e59df9dace7281a583db6da88ab` | `9fba8552bba30004ab452823668a105dee1ee89d` → `3b81e9d91cc3a0662b910726a44c94ed328b1e90` (PR #9) |
| PR8-CI (#357/#403) | `8f1eea56026595e2757a59ccd463688025375d81` | — |
| PR8-CRON (#372/#388/#393) | `870457d1d9a41ddf4ddc96606dc3243cf9aa6016` | `4fc5141f8d764f1dbc2b4d37128b5351b8d0aa62` → `ae8db40834e51d827e4130c6ceb9f4077a679221` (PR #10) |
| PR8-LEDGER (patches/ledger) | `177c7e200cf6e8b7812c9dfdd63f39519c76ea33` | — |
| PR8-CONSUME (#396/#397/#399) | `75d834e8ec47edb6ab297117e29638ddc69469ed` | — |

Fork candidates were verified as ancestors of the fork's `aether-main` after merge.
Fork Actions are disabled on the maintained fork (`enabled=false`, zero runs), so no
fork check result exists to cite; acceptance for fork content rests on the executed
suites and reviews recorded in the unit evidence.

**Integration:** one Aether branch, one pull request — **PR #413 merged** without
bypass, squash or history rewrite at
`de0a96826eae4022659aee9d943421e3226ec924` (previous `origin/main`
`67d7226d393da923d8cdb6f6c3781849b4ded273`).

## 2. Required checks (PR #413, run `34670434306`)

| Check | Result | Job |
| --- | --- | --- |
| `policy (3.11)` | pass | `103490657489` |
| `policy (3.12)` | pass | `103490657509` |
| `policy (3.13)` | pass | `103490657447` |
| `pull-request-target` | pass | `103490657400` |

Local replication of the policy job at the integrated revision: canonical base manifest
step PASS (heredoc extraction → empty `diff -u`; spec-manifest safety checks; VERSION;
forbidden paths; forbidden vocabulary), reproducible policy hooks `24 + 8` tests OK,
`py_compile` and file modes OK, R0 baseline files OK.

**Non-required observation matrix (red, inherited — reported, never green):** the
`observation-qualification` jobs for 3.11/3.12/3.13 are red **only** in the step
`Enforce integrated coverage floor` (`coverage report --format=total` = `76`, floor
`78`). The identical command on `origin/main` before the merge reports the same `76`,
so this is inherited debt tracked by issue **#412**; the floor was not lowered or
bypassed, and every other step of those jobs (suite, harness, benchmarks, static
gates) passes. Local CI-shape lane at the merged revision: **1650 passed / 0 failed**,
Graphify native lane 27 passed.

## 3. #357 post-merge confirmation (Python 3.13)

At `de0a9682` with no retry, skip or timeout increase: core **466/466 passed**
(expected 466; node manifest `b9879d323fa5c36bedee667008324f159885f054782f3bba1fa310797b260ee4`),
real PluginContext harness **1 passed** — `plugin_callback_count=22`,
`unload_hook_count=0`, tool/API capture true, raw payload absent. Qualified source:
git-archive of public baseline `e624e9fde561e1add9388384012b295fde669ade`
(sha256 `080afdc171d239a7b7076b008c66160dda2a689a7bd3b3de3f52cad8c5a14dc8`), tag
`v2026.8.18`, tag object `9f13bbbf8423427e159c78066356ca0e27ca6b74`. Other workflow
failures are not attributed to #357.

## 4. Runtime activation

- **Dedicated runtime checkout** advanced to the merged revision `de0a9682` (clean);
  previous revision `67d7226d` retained as rollback. Both provisioned interpreters
  resolve `aether_agents` from it.
- **Hermes editable source checkout** (branch `main`, pinned `0b288979e2`, dirty by
  design) adopted, as a supported source adoption, the 13-file merged fork delta, then
  the reviewed six-file HLP-362 patch; each adoption was rehearsed in disposable state
  first (0 rejects) and the live result verified byte-identical to the rehearsal.
- **Transactional editable refresh** through the accepted #399 operation
  (`LifecycleManager.reconcile_runtime_editable`, offline): `status=reconciled`,
  `rolled_back=false`, both provisioned interpreters `reconciled`, source bytes and
  dirty status unchanged across the call, both `python -I` import canaries green. Run
  twice: once for the merged delta, once after the HLP-362 adoption.
- **Two worker-safe gateway restarts** of the single gateway unit were required and
  performed by the operator role (PIDs `3908848 → 177206 → 194174`). This card was the
  terminal worker and did not restart its own parent unit.
- **Rollback points retained:** runtime checkout `67d7226d`; Hermes source
  pre-advance snapshot `1bb6a833f677cd93fa598db4ab19d3bb4f96b402`; pre-HLP-362
  snapshot `7c695593bcf41f2c3fa5d67eb6b530ad4a02561b`.
- **No `PYTHONPATH`, manual metadata edit, settings/provider/model/credential or
  unrelated-state change** was used for activation.

## 5. Canary results at the final activated revision

All canaries below were re-executed after the HLP-362 adoption (i.e. against the final
revision) on disposable state; live boards were read-only.

| Issue | Final-revision result |
| --- | --- |
| #357 | §3 above (466/466 + harness 1/1 at the merged revision). |
| #372 | Focused suite **9 passed**; probe: create-accepted script executes the same file (same inode/content), absolute / home-relative / traversal / symlink-escape / non-regular all blocked at validation *and* execution, root follows the active profile at call time; extended canary `RESULT_372_EXTENDED_PASS` (update path resolves the same profile file, same-named default-root decoy untouched and not resolved, default root confirmed, lifecycle scan blocked for `script` and `monitor_script`). |
| #385 | Review suites **56 passed** (surfaces + lifecycle + lifecycle_complete + independence); native transitions `RESULT_385_NATIVE_PASS` — missing reviewer refused (status/run unchanged, 0 events), self reviewer refused ("reviewer must be independent from the implementing profile", 0 events), explicit supervisor accepted (review/supervisor/1 event); CLI canary: refusals create 0 runs/0 events; behavioral canary on a disposable board: a dispatcher-spawned worker whose only child was a terminal integration stage emitted `review_requested` (no completion), and the review lane was claimed and approved by a Supervisor reviewer, promoting the terminal child. |
| #388 | Workdir suite **3 passed**; Aether probe at the activated runtime: six negatives fail closed with zero primary/draft/final mutation (five × `AETHER-OBJECTIVE-CONTRACT-WORKSPACE-UNRESOLVED`, unrelated project/worktree × `AETHER-OBJECTIVE-CONTRACT-PROJECT-CONFLICT`); valid linked worktree, direct sessionless store and primary-root authoring all still succeed. |
| #393 | Focused suite **7 passed**; gateway-origin probe `MISMATCHED_OR_MISSING=[]` with the full route preserved; end-to-end canary: owner-originated one-shot root reports `subscribed=true`, exactly one originating subscription persists, terminal flow wakes the origin exactly once (first collect 1, second 0), unattached cron creates no subscription and the board total is unchanged, no process-global env leak. |
| #396 | `status=pass`; bound units `t_10000001`/`t_10000002`, root/unknown relations, the five expected coverage-gap codes, raw titles absent, unrelated board unchanged. |
| #397 | Writer lane **70 passed / 1 skipped**; live-board window: 58 boards with **zero row changes**. |
| #399 | `status=pass`; reconciliation `reconciled`/`reconciled`, forced second-interpreter failure → `rolled_back` with first-interpreter metadata restored. |

HLP-362 did not invalidate any other activated canary: the two files it touches
(`hermes_cli/kanban_db.py`, `tools/kanban_tools.py`) were re-exercised by the #385 and
#393 canaries above, and the #372/#388/#396/#397/#399 lanes were re-run unchanged.

## 6. Issue reconciliation

Closed with revision-bound evidence: **#357, #372, #385, #388, #393, #396, #397,
#399** — the eight objective issues — plus **#403** recorded separately as the
incidental CI blocker (scanner green on tracked surface, wheel and sdist; tombstone
digest matches history; no scanner exemption).

Open incidental issues, not part of the eight and **not green**:
**#412** (integrated coverage `76 < 78`; identical on base and tip; floor unchanged)
and **#411** (transport-truncated durable comment; #227 guard context). Neither blocks
this objective's acceptance; both remain open for their own owners.

## 7. Integration-authored mechanical repairs (disclosed)

| Commit | Change | Verification |
| --- | --- | --- |
| `55a94bb` | Five generated patch paths added to the canonical base manifest. | Manifest step PASS end-to-end; no behavior change. |
| `58cf57d` | Repository formatter output for the PR8-CI manifest test (drift introduced by `befd0b2`, proven by revision-by-revision format checks). | `ruff format --check` clean; suite unchanged (8 passed). |

This record adds only `specs/pragmatic-reliability-eight/evidence/PR8-final.md`; the
canonical base manifest does not cover `specs/` paths, and the spec-manifest safety
checks pass for it.

## 8. Disclosed incident (self-reported by the terminal role)

While building the disposable environment for the #385 behavioral canary, five
disposable canary cards were accidentally created on the live objective board because
the harness inherited the live board selector; the live dispatcher spawned workers for
them. Containment: all five cards were reclaimed/archived within minutes, their
workspaces removed, and this was disclosed on the board with a full evidence capture;
no objective card, issue or repository state was damaged. The five archived rows are
**preserved** as disclosed evidence. The formal #385 behavioral canary was then
re-executed on a fully scrubbed, disposable board with the recorded result above.

## 9. Cleanup audit

Removed (objective-owned, merged, verified by `git merge-base --is-ancestor` before
deletion): the objective's Aether branches and worktrees (root, contract, review, ci,
cron, ledger, consume, integration, and the rework branches that share those tips),
the two temporary integration/verification worktrees under the system temp directory,
the fork-side verification worktrees, the HLP-362 rehearsal copy/venv, the disposable
canary homes and boards, and this record's evidence branch/worktree after merge.

Preserved deliberately: the five archived incident rows; the three rollback points in
§4; the active Telegram Monitor flow; the residual session-residuals flow; every
unrelated worktree, branch, stash and board observed in the repository (including
other objectives' merged-but-retained branches).

## 10. Release conclusions (kept distinct from the evidence above)

- `release_impact = patch` — compatible fixes and internal guidance/guard behavior;
  no public API, CLI, configuration or compatibility-contract change; no new
  capability surface (`PR8-consume` verified the CLI/parser surface is unchanged).
- `release_action = defer` — a merge is not a release; no version bump, changelog,
  tag, package publication or deployment was performed or implied by this objective.
- `release_channel = none` — no prerelease or stable artifact was produced; the
  runtime adoption in §4 is a local activation of source, not a published channel.

## 11. Morfeo result reception

Recorded at `2026-09-12T05:24:15+00:00` against Aether `053a5a8937d0cb40427b57a144ac6c15f01361a9`,
the clean runtime checkout `de0a96826eae4022659aee9d943421e3226ec924`, and the restarted
Morfeo gateway.

| Criterion | Evidence and producer | Reception result |
| --- | --- | --- |
| #357 | Pipeline evidence: exact Python 3.13 lane, 466/466 plus real harness 1/1; GitHub issue state checked by Morfeo. | Supported; no speculative product change. |
| #372/#385/#388/#393 | Direct Morfeo rerun on the activated Hermes source: the four focused files completed **25 passed**. Runtime imports and active gateway were also checked directly. | Supported at the active revision. |
| #396/#397/#399 and #403 | Direct Morfeo rerun on the clean Aether runtime: affected files completed **197 passed / 1 skipped**; pipeline canaries supply the exact board, rollback and multi-interpreter effects. | Supported; live-effect claims are reused pipeline evidence where a second run would add mutation. |
| Git/GitHub closeout | Morfeo checked fork PRs #9/#10 and Aether PRs #413/#414 as merged, all four required checks green on both Aether PRs, all eight issue states closed, and final-evidence bytes equal to the board attachment. | Supported. |
| Preservation and cleanup | Morfeo independently removed the missed authoring worktree/branch, pruned already-deleted remote refs, archived the temporary Project and removed the finite gate jobs/scripts and its own scratch. Five archived incident rows and three Hermes rollback stashes remain intentionally. | Supported with the disclosed incident and rollback residue. |

Direct reception did not repeat the full three-version matrix or the owner-origin wake; those are reused from
revision-bound pipeline evidence. The optional observation matrix remains red only on the unchanged coverage
floor defect #412. Incidental #404, #411 and #412 remain open and are not accepted as part of this objective.
The five archived live-board canary rows remain a disclosed procedural incident, not a claim of zero live writes.
