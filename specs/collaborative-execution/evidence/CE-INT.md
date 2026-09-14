# CE-INT — integration, dual-repo closeout, adoption

**Status:** terminal integration, publication, runtime adoption and independent readback complete;
issue and residue reconciliation recorded below. This is Supervisor terminal evidence, not
owner-objective acceptance — Morfeo's contract-result reception follows this card.

- **Task ID:** `t_c815d3a4`
- **Objective Contract:** `oc_a28ff9b7fa20d29d@v1` (SHA-256 `7a51dc2b3d2d62788b1228f823f9def58652e48d48fcecaecb5293f34dde7de5`)
- **Aether merge (PR #427):** `20f0d72e66f305fb68c3707460412f89bce5c780`
- **Maintained-fork merge (PR #11):** `bb5e9a422f3135371557e75bcd1db01c5f8fc3ba`
- **Portable patch:** `patches/hermes/HLP-334-native-collaboration.patch`, SHA-256 `94b95f2153bce69947a9f7369cebe559b56826c49fa22f4aa1eb2b587acdef30`
- **Fork Actions:** disabled (`enabled=false`) — NOT RUN, not green

## 1. Independently reviewed units consumed

Every implementation unit below was independently reviewed on the same-card Supervisor lane before
integration. History is merge-commit only; no squash, amend, or rebase.

| Unit | Card | Review | Aether tip | Fork candidate |
| --- | --- | --- | --- | --- |
| Root decomposition | `t_5fe2c707` | n/a (handoff) | `8f452ee7dfbb64cfbc97aeca96ab49e4333b078d` | — |
| CE-AE-RES | `t_08cec910` | round 2 approved | `08ae064e5051a27afac32982bd9bff7bb21c4da2` | — |
| CE-AE-DOCS | `t_e890e56a` | round 2 approved | `9f4ba65ea48163934ff14ee034655d23591330c2` | — |
| CE-HF-CORE | `t_07e9bbd7` | round 2 approved | `763d221134980576eb847a41e55643a56a59f1d3` | `20db06c0b8441190830aa72e3c0de6fdce6b8db4` |
| Morfeo D5 origin-route | design commits | Morfeo-owned | `dd2f1aa449b2e9fc7ab808089a98e35146b51fb8` | — |
| CE-HF-DELIVER | `t_8edf43f3` | round 4 approved | `7b6e28a1f4ff6b77cd8c2b464555a760b369dd42` | `2ec004ea54ab2401f63f1885a7c26f59bf1eb7db` |

Fork ancestors of `origin/aether-main` after PR #11: CORE `20db06c0` and DELIVER `2ec004ea` are both
ancestors of `bb5e9a422f`. The organizational adoption record and rollback manifest produced by the
origin role are consumed unchanged at
`specs/collaborative-execution/evidence/morfeo-runtime-adoption.md`.

## 2. Criterion matrix

| Criterion | Artifact / revision | Producer | Command / result | Direct vs reused | Limit |
| --- | --- | --- | --- | --- | --- |
| CE-01 opt-in binding | fork `2ec004ea54` / merge `bb5e9a422f` | CE-HF-CORE + D5 | Collaboration suites 53 passed on the candidate interpreter | reused unit review; INT re-ran 53 | Extra notify subscribers are not recipients; missing `origin_route` stays unavailable |
| CE-02 request before completion | same | CE-HF-CORE | `test_request_respond_ack_resolve_lifecycle` in the 53 | reused + INT re-run | No live Telegram/model |
| CE-03 proactive notices | same | CORE enqueue + DELIVER origin reach | lifecycle/coalesce tests in the 53 | reused + INT re-run | Controlled sinks only |
| CE-04 persist/enqueue/ack/respond/resolve | same | CE-HF-CORE | claim/lease/dedup tests in the 53 | reused + INT re-run | Synthetic live-board residue preserved, not deleted |
| CE-05 peer evidence / truncation | same | CE-HF-CORE | truncation/malformed/author-not-forged/peer-label tests in the 53 | reused + INT re-run | Not owner-instruction injection |
| CE-06 TUI/gateway exact origin | same | CE-HF-DELIVER | exclusivity both tick orders; no passive ping; notify cursor intact | reused + INT re-run (671 neighbors) | Fake sinks labeled as such |
| CE-07 controller lease / no duplicate Supervisor | same | CORE + DELIVER | advisory worker_context and flow_attention pins | reused unit review | No parent unblock from advisory |
| CE-08 stale / root-done not terminal | same | CE-HF-CORE | archive/flow_terminal vs root-done tests | reused + INT re-run | `resolution=stale` on archive |
| CE-09 roles/skills/docs | Aether `08ae064` + `9f4ba65` | CE-AE-RES + CE-AE-DOCS | resource/docs gates re-run at INT | INT re-run | Resource tests are not behavioral qualification |
| CE-10 fork + Aether distribution | PR #11 `bb5e9a422f`; portable patch SHA-256 `94b95f21…def30` | CE-INT | clean-base reconstruction 8/8 byte-equal; `git apply --check` exit 0 | direct | Fork Actions NOT RUN |
| CE-11 runtime adoption | live editable + `home/runtime/aether-agents-main` | origin role install; CE-INT readback | see §4: installed hashes 4/4, resources 13/13, installed-path suites 53 passed, schema/load readback | reused install + direct INT verification | Cached TUI sessions not restarted; no long-term behavioral PASS |
| CE-12 GitHub/issue/residue | this card + PR #427 + PR #11 | CE-INT | required checks green; both PRs merged without bypass; issues reconciled; residue audit see §7–§8 | direct | Unverified long-term efficacy retained |

## 3. Integrated fork and Aether verification (direct)

- Fork at `2ec004ea54` (`HERMES_TEST_FILE_RETRIES=0`, candidate interpreter, imports proven to the
  candidate tree): collaboration suites **53 passed** (8.07s); neighboring regression **671 passed**
  (39.66s); `git diff --check base...HEAD` clean.
- Integrated Aether tree before merge: docs/reconciliation/public-artifact suites **63 passed, 1
  skipped**; `check_documentation.py` and `check_public_artifacts.py` pass.
- PR #427 required contexts `pull-request-target` and `policy (3.11/3.12/3.13)`: **SUCCESS**, merged
  without bypass; every unit tip is an ancestor of `20f0d72e`.

## 4. Runtime adoption (CE-11) — installed by the origin role, independently read back here

The gateway that owns this worker was replaced by an owner-authorized cutover executed outside the
gateway. Adoption receipt: completed `2026-09-14T05:22:44Z`, gateway PID `893 → 589006`, status
`adopted`. This card performed no live mutation and never restarted its own parent.

| Check | Method | Result |
| --- | --- | --- |
| Installed native hashes | SHA-256 of the four files in the live editable tree | `kanban_db.py` `cb9874b1…`, `kanban_tools.py` `3f574c5b…`, `kanban_watchers.py` `192adcbf…` (= fork tip), `server.py` `410541e1…` (= fork tip); all equal the recorded candidate |
| Installed resources | SHA-256 of the 13 managed role resources against the receipt | **13/13 match** |
| Runtime checkout | `home/runtime/aether-agents-main` | advanced to `20f0d72e66f305fb68c3707460412f89bce5c780`, clean |
| Preservation (no collateral change) | All other recorded pre-adoption dirty/untracked files re-hashed | **58/58 byte-identical**; only status delta is `tui_gateway/server.py`, clean before (equal to fork base) and modified only by the adopted bytes |
| Mechanical composition points | Line-level delta audit `preimage → installed` vs the reviewed `3b81e9d → bb5e9a422f` delta | `kanban_db.py`: reviewed 47 removed/980 added vs 45/978 installed — the single difference is one docstring line reflowed at different indentation (installed recovery wording preserved). `kanban_tools.py`: identical 122 removed/319 added, with exactly one extra added line `board=board,` (the incoming `target_board` mapped to the installed handler's selected board) |
| Installed-path suites | The four collaboration test files run with imports asserted into the live tree (`--import-mode=importlib`; origin assert loaded and printed) | **53 passed in 8.81s** |
| Schema/load readback | Fresh disposable board created by the installed module | table `kanban_collaboration` (27 columns) plus indexes `idx_collab_root/task/recipient/request/lease`; the eight collaboration helpers present; production `-I` interpreters resolve the installed modules without `PYTHONPATH` |
| Non-contamination | Live objective-board fingerprint before/after the probe | 19 tasks / 3 collaboration rows unchanged |

Limits: existing cached TUI sessions were not restarted and are not described as upgraded; no live
Telegram or paid-model canary; `long_term_behavior_verified=false` — mechanical delivery and load
evidence only.

## 5. Rollback

- **Live editable tree:** restore the four preimages by byte: `kanban_db.py` `60f072b2…`,
  `kanban_tools.py` `2d4e1107…`, `kanban_watchers.py` `755091a3…`, `server.py` `39d2e7a3…`. No test
  files were installed into the live tree, so nothing else is removed. Never `reset --hard`/`clean`
  the other dirty or untracked entries.
- **Runtime checkout:** roll back `home/runtime/aether-agents-main` to `de0a96826eae4022659aee9d943421e3226ec924`.
- **Fork:** revert merge `bb5e9a422f`. **Aether:** revert `20f0d72e` through a normal PR.
- The installing role retains the private rollback manifest and per-file preimages.
- No force-push, history rewrite, or check bypass was used anywhere.

## 6. Live-board residue (preserved, never cleaned by SQL)

The objective board holds **19 rows**: the 6 objective cards, 12 disclosed synthetic rows written by
implementation/verification probes (`t_b421fb57`, `t_9acc568c`, `t_01a3ab74`, `t_2406142e`,
`t_0048472c`, `t_20202d6f`, `t_f3e60446`, `t_709f9ebd`, `t_6c84236c`, `t_1e75d385`, `t_ebd28f85`,
`t_c46db090`), and the origin role's separate runtime-recovery card (`t_318f2d12`, blocked), plus 3
`kanban_collaboration` rows. Direct SQL deletion of tasks/comments/events/runs is never cleanup;
these rows are preserved as evidence. The audit does **not** treat CE-HF-CORE's isolation
qualification as covering arbitrary ad-hoc probes: Aether **#267** remains open for that recurrence.

## 7. Issue reconciliation

| Issue | Disposition |
| --- | --- |
| [#334](https://github.com/DarkArty07/Aether-Agents/issues/334) | Closed as the delivered scoped collaboration mitigation, citing both merged revisions, the portable patch and the runtime adoption/readback — with long-term behavioral efficacy stated as unverified |
| [#317](https://github.com/DarkArty07/Aether-Agents/issues/317) | Closed as owner-directed retirement of the open-ended observation gate; no organic PASS claimed |
| [#407](https://github.com/DarkArty07/Aether-Agents/issues/407) | Already closed; a mitigation reference was added without rewriting its historical failed acceptance |
| [#267](https://github.com/DarkArty07/Aether-Agents/issues/267) | Left open — probe-to-live-board recurrence accounted in §6 |
| [#428](https://github.com/DarkArty07/Aether-Agents/issues/428) | Left open — the **non-required** `observation-qualification` matrix is red before the coverage floor and independent of this change; never reported as PASS. Aether **#412** (inherited coverage floor) remains separate |

## 8. Objective-owned residue cleanup

Removed only after merge and readback evidence:

- Aether worktrees `t_07e9bbd7`, `t_08cec910`, `t_e890e56a`, `t_8edf43f3` and their local branches.
- Nested maintained-fork worktrees `hermes-ce-hf-core`, `hermes-ce-hf-deliver`, their scratch
  fail-first overlays, and the fork branches `feat/334-native-collaboration-core` and
  `feat/334-deliver-tui-gateway` (local and remote).
- The root objective branch `aether-agents-2/t_5fe2c707-…` locally and remotely is removed after the
  closeout PR merges; this card's own worktree is retained until the card closes.

Preserved: the origin role's design worktree and branch (`morfeo/collaboration-scope-334`), the
origin role's recovery card, every other active/unmerged/blocked/concurrent/unrelated worktree,
branch and stash, and both rollback revisions.

## 9. Release conclusions (aggregate)

- `release_impact = minor` — compatible optional public additions (`kanban_create(..., collaboration="advisory")`, the optional `kanban_comment` collaboration object, the additive `kanban_collaboration` table and the additive `kanban_show` list) with legacy roots, ordinary comments and the terminal-notification cursor unchanged; no incompatible removal.
- `release_action = defer` — a merge does not imply a release; no version bump, tag, package publication or GitHub Release.
- `release_channel = none`

## 10. Out of scope (explicit)

Telegram Monitor restart; Aether #417 observer repair; Aether #421 TUI SIGBUS repair; #428/#412 CI
repairs; organic PASS, measured speedup or non-recurrence claims; force-push; check bypass; package
publication; deployment. The retirement of HLP-334 requires an adopted exact Hermes release with
equivalent semantics and passing focused suites.
