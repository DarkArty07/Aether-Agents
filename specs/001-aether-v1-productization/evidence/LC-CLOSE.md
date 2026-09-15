# LC-CLOSE — real activation lane, issue truth, residue and final report

**Unit:** LC-CLOSE (Supervisor, terminal card) · card `t_f2dca8e1`
**Authority:** Objective Contract `oc_3397f9f05d780f8e@v1`
(SHA-256 `4d4c7650bf8ea93fc7cffe3d87f7f974e172d66cefcf6a74a2d83051568a4879`) on base
`410c172ae69ffa87f6e32960ae4aef3b8d6598f0`.
**Breakdown:** `specs/001-aether-v1-productization/tasks.md` at its current revision
(Shared decisions 1–18). This record is unit-level evidence; it is not an aggregate
release conclusion.
**Status:** pre-activation investigation recorded. Activation, rollback rehearsal, forward
activation, issue truth and residue remain blocked on the published RC identity that
LC-INT `t_7326adb7` must hand off.

> **Current state (annotation added at closeout — the sentence above is point-in-time and not
> rewritten):** the handoff completed, the RC was published, and the lane then closed as
> **rejected**: activation was **omitted by disposition** (no waiver) and the artifact is
> published-but-not-accepted. Read §5 for the disposition, §6 for the non-mutation witnesses,
> §7 for issue truth, §8 for residue and §9 for the final report.

## 1. Explicit non-claims

No activation, rollback, forward activation, tag, release, publication or issue mutation
has been performed by this card yet. The `1.0.0rc1` milestone is not stable `1.0.0`, not a
package-index publication and not a WSL2 qualification result. Every statement below is a
measured observation with its own evidence; none of them is an acceptance verdict.

## 2. Pre-state (read-only, recorded before any mutation)

At claim time the RC did not exist anywhere: no `v1.0.0-rc.1` tag and no RC GitHub release;
`VERSION` still named the previous stable line; the installed runtime still resolved to the
pre-RC release. The full pre-state identities (active record, `runtime/current` target,
launcher/Desktop/service projections, service PID and start time, and the mutable-state
identities that must survive) are re-captured immediately before the first interrupting
step, per Shared decision 12, and are therefore not claimed here.

## 3. HLP-310 delegated-child snapshot leak (issue #404) — reproduced and classified

LC-FORK `t_926a1913` reported (collaboration request 5) that a real five-child batch left
`HERMES_DELEGATED_CHILD_CONTEXT=1` in the originating parent terminal, and asked for a
classification against the maintained-fork candidate rather than acceptance from
historical focused tests. Both claims are now measured.

### 3.1 What was measured

| Leg | Tree under test | Canary verdict |
| --- | --- | --- |
| RED | Pre-RC installed runtime, Hermes source revision `0b288979e2322c02ab42c05f1e183bb31cfa5aa9` | **LEAK** |
| GREEN | Maintained-fork candidate `54eeb56dabefc98821d696656ed58c55dd777346` (a descendant of the RED revision) | **no-leak** |

Canary: `specs/001-aether-v1-productization/fixtures/hlp310_snapshot_canary.py`. It runs a
child-like command carrying `HERMES_DELEGATED_CHILD_CONTEXT=1` in the process environment
through the real `LocalEnvironment` reusable bash session, inspects the session snapshot,
then runs a parent-like command in the same session. It prints the resolved origin of every
imported Hermes module, and uses disposable `HERMES_HOME`/working directories only.

RED observations: `snapshot_has_delegated_marker: True`,
`snapshot_has_kanban_prefix: True`, and the later command reported
`parent_marker=[1]` — the marker persisted into the reusable session. Module origins
resolved to the installed pre-RC release tree, so the result cannot be attributed to the
wrong source.

GREEN observations: with the same interpreter and the candidate tree supplied through
`PYTHONPATH`, module origins resolved to the candidate tree,
`snapshot_has_delegated_marker: False`, `snapshot_has_kanban_prefix: False`,
`parent_marker=[]`, verdict `no-leak`.

Static corroboration, both trees read directly:

- RED tree `tools/environments/base.py`: `_SNAPSHOT_EXCLUDED_ENV_REGEX` covers only
  `HERMES_SESSION_`, `HERMES_UI_SESSION_ID`, `HERMES_CRON_AUTO_DELIVER_` and
  `HERMES_CRON_SESSION`; the dump unsets only `${!HERMES_SESSION_*}`,
  `${!HERMES_CRON_AUTO_DELIVER_*}`, `AI_AGENT` and `HERMES_AGENT`. The file contains zero
  occurrences of `HERMES_DELEGATED_CHILD_CONTEXT`.
- Candidate tree, same file: the regex additionally covers
  `HERMES_DELEGATED_CHILD_CONTEXT` and `HERMES_KANBAN_`, and the dump additionally unsets
  `${!HERMES_KANBAN_*}` and `HERMES_DELEGATED_CHILD_CONTEXT` before `export -p`.

Focused regression at the candidate revision (not a historical claim): running that tree's
`tests/tools/test_delegate_kanban_isolation.py` and
`tests/tools/test_snapshot_session_id_leak.py` produced `12 passed`.

### 3.2 Classification

The #404 recurrence is a property of the **pre-RC installed runtime**, whose Hermes source
predates HLP-310's snapshot exclusion, and not of the maintained-fork candidate, which
carries the exclusion and passes its focused regression. No fork source repair is required,
so no additional implementer unit was created for it.

Corroboration: LC-FORK independently reached the same classification by its own measurement
(candidate exclusion at `tools/environments/base.py:533/576/585`, focused regressions
`12 passed`, and zero occurrences of the marker in the effective runtime source, whose
snapshot prelude is the pre-HLP-310 `AI_AGENT HERMES_AGENT` form). Its record is
`specs/001-aether-v1-productization/evidence/LC-FORK.md` §11. The two measurements were made
separately and agree, which is why this classification is treated as settled rather than
single-author.

### 3.3 Remaining obligation (this card owns it)

The GREEN leg above ran the candidate **source** under the pre-RC runtime's interpreter
(module origin printed; the two trees are 83 commits apart) and did not use the fork's own
runner and dependency set. The confirmation that matters is therefore the same canary
re-run on the **activated RC runtime**, after LC-INT hands off the published identity and
this card activates it. That re-run, plus the fork-side focused modules at the accepted
merged commit, is the evidence ladder for issue #404.

Issue #404 stays open until all three legs hold: the accepted fork commit carries the
exclusion, its focused modules pass at that commit with the fork's runner, and the canary
passes on the activated RC. If any leg fails, the failure is commented on #404 and the
issue remains open rather than being closed on a partial result. This is recorded now so a
resumed run continues the ladder instead of relitigating the classification.

## 4. Resume checklist (post-restart, in order)

1. Re-verify the published identity handed off by LC-INT (release/tag/commit, artifact names
   and hashes) and that the RC bytes are the ones downloaded from the release.
2. Record the full pre-state, then run the non-mutating preview and the cheap refusal checks.
   The pre-state MUST include the exact bytes and mtime of the real user unit
   (`hermes-gateway-morfeo.service`) plus its `ExecStart`, `WorkingDirectory`, `VIRTUAL_ENV`
   and `HERMES_HOME` values, because §4.1 shows how that file can be silently rewritten.
   Capture them with a plain read; never run a lifecycle or activation test to obtain them.
3. Write the post-restart verification checklist durably **before** the interrupting step,
   activate, and let the session interruption happen as authorized.
4. After instances reopen: active record vs `runtime/current` vs launcher vs Desktop entry vs
   service projection agreement, `aether version`, `aether doctor --json`, `aether status`,
   TUI `--check` plus a real launch, gateway/dispatcher readiness with a post-activation PID,
   plugin/tool exposure, exact Project binding, Graphify probe/status/query, no legacy
   project-local runtime path, one real three-role pipeline E2E, and the HLP-310 canary of
   §3.1 re-run on the activated runtime. **Plus the §4.1 unit-file assertions below.**
5. Rollback rehearsal, then forward activation of the same RC and re-verification; preservation
   of every mutable-state identity and of post-cutoff data.
6. Issue truth: #437/#438 only with exact evidence; #261 updated with the RC outcome and the
   outstanding stable/PyPI/WSL2 gates, left open; #404 per §3.3; #439 per §4.1.
7. Residue: objective-owned merged branches/worktrees and bounded test processes only, with the
   preserved items reported.
8. Final report with `release_impact`/`release_action`/`release_channel` stated separately from
   the evidence supporting them.

### 4.1 Live-safety constraint from issue #439 (recorded before activation, not after)

While this card was blocked, an earlier run of the LC-RUNTIME candidate executed
`tests/test_observation_lifecycle.py::test_activation_materializes_three_explicit_profile_homes_under_store`,
which called the real `activate_existing()` without an injected disabled service controller.
The generated gateway unit was written to the **real** user systemd destination with that
test's `tmp_path` in `ExecStart`, `WorkingDirectory`, `PATH`, `VIRTUAL_ENV` and `HERMES_HOME`;
when pytest removed the directory the unit entered a five-second `203/EXEC` restart loop
(~474 failures), the dispatcher/ticker stopped, and four workers died. Issue #439 is the
record. This is the same file this card's activation lane legitimately rewrites, so the
incident is a direct hazard statement for step 3, not a curiosity.

Independently verified at claim time (read-only) that the restoration holds: the unit's
`ExecStart` and `VIRTUAL_ENV` resolve to the real release
`…/runtime/releases/20260914T135740-0600-a3d8475c-h0b28897/venv`, `WorkingDirectory` and
`HERMES_HOME` are the real `…/state/aether/hermes/profiles/morfeo`, and the service reports
`ActiveState=active`, `NRestarts=0`, a start time after the incident. The unrelated
`hermes-gateway-hestia.service` is active and was not touched.

Obligations this adds to the activation step:

- **Never run a lifecycle/activation test that can reach `SystemdUserController` or the real
  unit destination from this card.** Pre-state and verification are plain reads.
- Immediately after activation, assert the unit's `ExecStart`, `WorkingDirectory`,
  `VIRTUAL_ENV` and `HERMES_HOME` name the **new immutable release**, contain no `tmp`/
  `pytest-` path, and match `runtime/current`; then assert `NRestarts` is stable (not
  climbing) and that no `203/EXEC` failure appears. A partial or clamped transition is
  reported as a failed canary, never as success.
- Treat the owner-visible consequence of a bad write here as severe: the same failure mode
  stops the board's dispatcher and every concurrent flow.
- `#439` is *not* in the contract's issue list (`#437`, `#438`, `#261`). It is therefore
  **left open** by this card unless LC-RUNTIME's isolation fix is present in the accepted RC
  *and* verified, in which case the verification is commented on it with evidence; it is never
  closed on this card's own authority. The incident and its verified restoration are reported
  in the final evidence either way.

**Terminal outcome (annotated after the lane's last gate closed; §§1–4 above remain the
point-in-time pre-activation checkpoint and are not rewritten).** The lane's terminal state differs
from what §4's checklist anticipated: **activation was omitted by disposition** and the RC is
recorded as **published-but-rejected**. §§5–9 below are the terminal record.

## 5. Terminal disposition — activation omitted, rc.1 rejected

Authority chain (durable on card `t_f2dca8e1`, board comments 111/120/135/139):

- Design-steward response to collaboration request #13, and its resolution: **no waiver**.
  "`v1.0.0-rc.1` must not be activated or accepted as the objective result while its immutable
  wheel METADATA falsely denies that a release candidate was published." Request #13 is
  **resolved, not awaiting owner input**; no artifact or procedure grants that waiver.
- This card "must only record rc.1 as published-but-rejected, never activate it", preserve all
  rc.1 bytes and the tag, and close the v1 lane as **rejected — not accepted**. "Do not execute
  any rc.1 runtime transition."
- A corrected `v1.0.0-rc.2` requires **its own superseding finalized contract and handoff**; that
  authority is not inferable in this card.

Why the artifact is rejected: `README.md` is embedded into the published wheel's `METADATA` long
description, and at the tagged commit it stated that the checked-in tree was "not a release
candidate" and that **"no release candidate has been published from this repository"** — while
being that release candidate's own wheel. The condition was repaired in canonical source afterwards
(PR #449 → `main`), but the published rc.1 bytes are immutable without forbidden effects (asset
replacement, `--clobber`, or moving the tag), so the defect persists in the artifact itself.

**Steps omitted by this disposition** (card steps 2–5): local preview through `aether update`,
activation, the post-restart verification battery, the rollback rehearsal, and forward activation.
Consequently **no activated-runtime evidence exists for rc.1 and none is claimed anywhere in this
record**. Every issue whose closure or verification condition was an activated-runtime observation
is therefore recorded below as still open for that reason, not closed on a substitute result.

## 6. Non-mutation witnesses at closeout (read-only; nothing was written by this lane)

| Witness | Value at closeout |
| --- | --- |
| `runtime/current` | resolves to `…/runtime/releases/20260914T135740-0600-a3d8475c-h0b28897` — the pre-RC release, and the only release present under `…/runtime/releases/` |
| Aether-owned unit `hermes-gateway-morfeo.service` | `active`/`running`, `MainPID 1987954`, `NRestarts=1`, start 2026-09-15 00:40:42 CST — unchanged since the 00:40:42 liveness-watchdog restart recorded at §4.1 |
| Unrelated `hermes-gateway-hestia.service` | `active`/`running`, `MainPID 1987921`, `NRestarts=4` — **untouched** |
| Launcher projection | sha256 `4edab4f9…`, mtime `1789454504` — unchanged from the value recorded before closure |
| Desktop projection | sha256 `a6091be1…`, mtime `1789454504` — unchanged |
| User unit file | sha256 `1b7421b1…`, mtime `1789445613` — unchanged |
| Generic `~/.local/bin/hermes` | sha256 `b437aab8…`, mtime `1785564028` — untouched |
| rc.1 annotated tag | object `cda1ecca…` → commit `748aa24…` |
| rc.1 release | `prerelease=true`, `draft=false`, created 2026-09-15T13:16:34Z, **8 assets**, every `sha256:` digest identical to the LC-INT record (wheel `19c6cf52…`, sdist `f8eac2a4…`, fork source `61b7ee62…`, lock `0ac3b355…`, provenance `0a76c5d8…`, package-members `578257b0…`, clean-install `249affb5…`, `SHA256SUMS` `0c12d875…`) |
| Mutable state | board counters at closeout: 17 tasks / 337 runs / 172 comments; the Hermes Projects store present with 15 project rows |

Because **no transition occurred**, preservation of mutable state is trivially true and no
store-by-store census is claimed: the witnesses above are the ones needed to prove *non-mutation*,
which is the property this lane must establish. A full sessions/memories/observations/monitor census
would be required only if a transition had run.

## 7. Issue truth

| Issue | State | Evidence and disposition |
| --- | --- | --- |
| #437 | **CLOSED** | Closed with exact evidence at `main` `a1d6c5df…`: `.github/workflows/policy.yml` lines 145–146 list the HLP-420 and HLP-425 patches, so the literal non-`specs/` manifest matches the tracked file set; `scripts/qualify_telegram_monitor.py` names a **distinct explicit reviewer** (`SYNTHETIC_REVIEW_REVIEWER`) while the shipped writer still owns and enforces the reviewer rule; a cleared-environment detached-checkout run at `main` of `tests/test_telegram_monitor_ambient_isolation.py` + `tests/test_telegram_monitor_runtime.py` = **59 passed** |
| #438 | **CLOSED** | Same run: the isolation regression module landed and 59 passed at `main`. Review measurements: RED on base under a disposable language-configured profile (`1 failed, 56 passed`), GREEN on candidate (`57 passed`), mutation check reproduced. Production Monitor behavior unchanged |
| #261 | **OPEN** (required) | Terminal-outcome comment added: rc.1 published-but-rejected, activation omitted, the stable/PyPI/WSL2 gates explicitly outstanding. `1.0` stable was **never** claimed |
| #404 | **OPEN** | Ladder legs 1–2 hold: the accepted fork commit `9031bae0…` carries the snapshot exclusion (4 occurrences of `HERMES_DELEGATED_CHILD_CONTEXT` in `tools/environments/base.py`) and its focused modules pass. **Leg 3 — the canary on an activated RC — is removed by the omitted activation**, so the issue stays open rather than being closed on a partial result |
| #439 | **OPEN** | Outside the contract's issue list; left open per §4.1. Its verified restoration is recorded there and re-confirmed by the unit-file witness in §6 |
| #440 | **OPEN** | Its closure condition was an **activated-runtime canary**; with activation omitted it cannot close here and moves to the successor lane |
| #428 | **OPEN** | The coverage lane is green at `main` (post-merge `Repository Policy` run `35009308885`: `observation-qualification` 3.11/3.12/3.13 all success), but LC-FIX-COVLANE's own evidence records a residual it **escalated to the owning lane**. Not closed here |
| #445 | **CLOSED** | Repaired by PR #448 with empirical GitHub-acceptance proof in its own lane |
| #446 | **CLOSED** | Repaired by PR #452, deployed by the authorized automatic Pages run and verified against the live site |
| #239 | **OPEN** | Source statements corrected and landed (PR #449); the **published** rc.1 metadata remains self-contradictory and can only be resolved by a successor artifact |
| #450 | **OPEN** | Routed as bounded unit LC-FIX-WORKLIFE (`t_6094e616`): diagnosis, fork fix, HLP record with rollback/retirement evidence. Its accepted commit must reach the fork's `aether-main` and be pinned into rc.2 before any rc.2 activation |

## 8. Residue

- **Removed** — 14 clean objective-owned worktrees: the integration worktree plus the unit
  worktrees for LC-DOCS, LC-BLOCK, LC-FORK, LC-RUNTIME, LC-RELTOOL, LC-PORT420, LC-FIX-RELWF,
  LC-FIX-README, LC-FIX-WEBSITE, LC-FIX-INIT, LC-FIX-GOLDEN, LC-FIX-GUARD and LC-FIX-COVLANE.
  Removal was attempted **without** `--force`, so git itself guards against destroying scratch;
  **no removal was refused for dirtiness**, and the scratch audit checkout was also removed.
- **Preserved, objective-owned:** the LC-FIX-WORKLIFE worktree (its unit is still in review and
  unmerged); this card's flow-affinity workspace; this closeout's evidence worktree; and the
  preserved `aether-agents-2/t_a18b5fc7-lc-fix-website-pages-content-oracle-must` branch at
  `5eeccb6` with PR #451's record — kept unrewritten by explicit steward direction.
- **Preserved, not objective-owned:** 72 registered worktrees belonging to other flows and
  objectives plus the live runtime source checkout — untouched; the pre-RC runtime release and its
  migration backups; the unrelated gateway service; and the two pre-existing dirty paths in the
  owner's primary checkout (`scripts/aether_tui.py`, `tests/test_aether_tui_launcher.py`), reported
  and not modified.
- **Remote branches:** unit branches were deleted on merge by the repository's own setting; only the
  preserved #451 branch remains under the objective's prefix.
- **Processes:** no test process was killed and none needed to be; a per-PID `cwd` scan found no
  live process in the fork tree or the unit worktrees at closeout.

## 9. Final report

The three conclusions, stated **separately from their supporting evidence**:

- `release_impact = major`
- `release_action = publish`
- `release_channel = prerelease`

- **`release_impact=major`** — evidence: the milestone's recorded identity is package `1.0.0rc1` /
  annotated prerelease `v1.0.0-rc.1`, a major-version step from the pre-RC line, carried in the
  release lock and the tagged commit's identity surfaces.
- **`release_action=publish`** — evidence: annotated tag `v1.0.0-rc.1` (object `cda1ecca…` →
  commit `748aa24…`) and a GitHub prerelease with 8 assets were created and verified byte-for-byte
  against the qualified bundle. This records the action that **occurred**; it is **not** an
  acceptance verdict, and the artifact is rejected for acceptance and activation as recorded in §5.
- **`release_channel=prerelease`** — evidence: `prerelease=true`; there is no stable `1.0.0` tag,
  no PyPI or other package-index publication, and no WSL2 qualification result.

**Verified, and how:** the eight published assets against the qualified bundle (byte comparison and
digest agreement, exit 0 through the strict verifier); the artifact-installed CLI handshake from a
fresh environment; the release workflow's validity and GitHub parse acceptance (§ its own unit
record); the source corrections for the public status statements, the release workflow and the Pages
content oracle, each landed through a green PR with its own review; the canonical test suite at the
integration tip; and this lane's non-mutation witnesses (§6) plus the issue states read back (§7).

**Remaining unverified (explicitly):** the **WSL2** lane; **PyPI/OIDC** publication; **stable
`1.0.0`**; and the whole class of checks that depended on activation — the activated-runtime battery,
the rollback/forward-activation rehearsal, the activated-runtime canaries for #404 and #440, and the
three-role pipeline E2E on the new runtime. None of these was performed, and none is implied.

**Remaining material risk:** the published rc.1 artifact carries a self-contradictory `METADATA`
that is immutable and publicly visible until a successor artifact is published; the objective's
runtime lane was deliberately never exercised, so the activation path's live behavior remains
unproven; and the #450 kernel defect (a terminal worker outliving its run beside a successor) is real
and unfixed in the maintained fork until LC-FIX-WORKLIFE's accepted commit is merged and pinned into
rc.2.

**Verdict:** the v1 lane is closed as **REJECTED** — not accepted, not activated.
