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
