# Hermes patch reconciliation preflight

Observation timestamp: `2026-09-11T22:55:11Z`

Upstream inspected: `https://github.com/NousResearch/hermes-agent@4f22543509d1b91dc45bcb369447126c5eb14fb7`

Source ledger SHA-256: `43b25f9497e9b84b7108d40878b1e2f09694c7a70edab7bd75759000d66b0890`

## Remaining local guarantees

- `HLP-188`: Exact upstream source has the initial blocked status but not the durable sticky event. The isolated behavioral probe showed auto-promotion without unblock, so the local guarantee remains required.
- `HLP-189`: Upstream already supports max_retries in the database layer but does not expose or forward it through kanban_create. With no executed full gate, the local interface guarantee remains required.
- `HLP-191`: Upstream can escalate repeated blocks to triage but still treats all triage tasks as auto-decomposition candidates and lacks the durable recovery boundary. The local human gate must remain.
- `HLP-194`: Upstream has a name-based stop nudge and a clean-exit backstop, but it lacks durable exactly-one receipt validation and EX_PROTOCOL=76. The local terminal-handoff guarantee remains required.
- `HLP-198`: Retain HLP-198. Exact-target source and a disposable behavioral gate reproduce the stale claimed-task branch mismatch in ready and review dispatch.
- `HLP-204`: Retain HLP-204. The target retains only the uniform cap, while the required asymmetric override interface remains solely in an open upstream PR.
- `HLP-209`: The exact upstream target contains and behaviorally passes the HLP-209 directory exemption, but the recorded runtime retirement gate remains incomplete.
- `HLP-211`: Retain both HLP-211 and HLP-211b. The exact public snapshot lacks prerequisite runtime interfaces, and the linked open PR is a narrower same-task resumption change. The tracked HLP-211b patch checksum, parser check, and read-only effective-checkout byte reconstruction passed; only the ignored backup input remains unavailable.
- `HLP-226`: Retain HLP-226, HLP-226b and HLP-226c. Exact upstream lacks the affinity-terminal Project-source variant as well as the explicit-worktree and conflicting-Project behavior. The portable HLP-226b patch checksum and parser controls pass, but the documented reconstruction input and overall artifact verification remain unavailable. The new portable HLP-226c patch is bound by digest and reconstructs the reviewed fork candidate 7980bbf1f9f75efdcbee2196ae910bb77138541d byte for byte from maintained fork base 415056fee527c5a2302370bd6dba56f84b9a4202 with git apply --check and all three changed files matching on file SHA-256 and Git blob identity.
- `HLP-246`: Retain HLP-246. The exact public snapshot accepts a synthetic truncated payload with valid base64 and has no sender identity claims, SHA-256 persistence, or readback verification.
- `HLP-247`: Retain HLP-247. The exact public snapshot still promotes an eventless blocked child on parent archive, while the required todo and non-sticky compatibility controls remain promotable.
- `HLP-262`: Retain HLP-262. Exact upstream has neither the origin_signal block API prerequisite nor sticky predicate support for origin_signal, and the portable patch checksum and parser controls pass without establishing full-patch reconstruction from unavailable inputs.
- `HLP-275`: Retain HLP-275. The auxiliary vision path now applies the repository's existing embed policy before the first request, so oversized small-byte images are normalized by the existing resizer with scale disclosure and within-policy images stay byte-identical. Upstream already carries a stricter-threshold variant of the same mechanism, so this entry is a retirement candidate only after oracle requalification.
- `HLP-280`: Retain the bounded HLP-280 recovery. Local 15 recovery probes, 129 affected tests with one Windows skip, 44 notifier tests and a native-origin canary passed. This records a downstream repair, not the rejected v4/v5 architecture or a Hermes release upgrade.
- `HLP-305`: Retain HLP-305 in maintained fork c185ee3bb. Source hash readback and normal SessionDB activation passed after consistent backup/quick_check/SHA-256. Live owner TUI tool result retains complete11576-character message with8203-character index(prefix+metadata), proving writer-side activation without restarting TUI. Existing Python processes still require graceful reload for their cached code paths. Expanded testing retains baseline failure #349.
- `HLP-310`: Retain HLP-310. Inspected upstream does not exclude delegated child identity or Kanban environment variables from terminal snapshots. Maintained fork commit 25cabeb25327199a03aa3cf1613ed2f815f646cb provides the causal repair in PR #4.
- `HLP-335`: Retain HLP-335. The local respawn-guard recovery releases only independently verifiable CLOSED/MERGED PR references so Graphify closeout can resume; OPEN/unknown/auth failures stay guarded. This records a downstream repair, not a Hermes upgrade or a Graphify product delivery.
- `HLP-354`: Retain HLP-354. Inspected upstream lacks worktree_base_ref materialization and fail-closed validation. Maintained fork commit 7d3173e1f3dba107f9a389d4e35c95f215775ee1 provides the causal repair in PR #4.
- `HLP-362`: Retain HLP-362. Initial same-card review requires an explicit independent reviewer; self-review is rejected and legacy unassigned review claims remain parked. Verified by regression tests on the maintained fork and candidate testing in Aether.
- `HLP-369`: Retain HLP-369. Exact upstream retains the circular goal-mode review gate and recovery-kind mismatch; maintained-fork PR #6 merge 415056fee527c5a2302370bd6dba56f84b9a4202 separates review readiness from completion, preserves independent review and completion gates, and accepts only the exact pending controller recovery signal while retaining origin attention.
- `HLP-372`: Retain HLP-372. Cron scripts and monitor scripts resolve dynamically through one effective profile-scoped root at call time with fail-closed confinement on traversal, symlink escapes, and non-regular files.
- `HLP-382`: Retain HLP-382. Transcript publication is now bounded and atomic: staged batches in the existing store, exact-once preservation of interleaved concurrent appends, one metadata-only cutover, and bounded target-local cleanup. The unchanged oracle is deterministically RED at the fork base and green on the candidate and integrated tree.
- `HLP-385`: Retain HLP-385. Guidance in KANBAN_GUIDANCE explicitly states that terminal integration or release children alone do not replace unit review, requiring an explicit review/QA phase child before kanban_complete is called as an implementation handoff.
- `HLP-388`: Retain HLP-388. The framework persists the verified cron launch workdir in the session row before tools run, preventing ungrounded contract authoring while keeping null cwd when unset.
- `HLP-389`: Retain HLP-389. Referenced-script discovery now uses a syntax-aware view for inert interpreter heredoc bodies while direct detection keeps the original text, so the harmless log-read path is accepted and every recorded executable control remains blocked.
- `HLP-393`: Retain HLP-393. Cron jobs commissioned from TUI or gateway capture durable origin, restored at fire time as request-local context so spawned Kanban root tasks auto-subscribe and wake the exact origin upon completion.

## Qualified upstream equivalents

- `HLP-209`: Qualified source disposition: upstream_verified; retirement recommendation: retain.

## Retirement blockers

- `HLP-188` (retirement_gate): Retirement gate status is failed.
- `HLP-188` (uncertainty): The direct isolated probe establishes the failing prerequisite; the separate-process dispatcher-spawn portion of the recorded matrix was not run.
- `HLP-189` (retirement_gate): Retirement gate status is not_executed.
- `HLP-189` (uncertainty): The full schema-to-separate-process persistence gate was not executed.
- `HLP-189` (uncertainty): Source inspection shows the required agent-facing interface is absent at the inspected revision, but source inspection is not substituted for a retirement pass.
- `HLP-191` (retirement_gate): Retirement gate status is not_executed.
- `HLP-191` (uncertainty): The complete reconnect, reassignment, and auto-decompose behavioral matrix was not executed.
- `HLP-191` (uncertainty): The ledger's additional explicit-recovery CLI surface is not represented by the linked upstream PR and remains unqualified independently.
- `HLP-194` (retirement_gate): Retirement gate status is not_executed.
- `HLP-194` (uncertainty): The full receipt and process-outcome matrix was not executed.
- `HLP-194` (uncertainty): Source inspection demonstrates that a successful retirement gate cannot be inferred from the current stop nudge and dispatcher backstop.
- `HLP-198` (retirement_gate): Retirement gate status is failed.
- `HLP-198` (uncertainty): No material uncertainty remains for the target: both required lanes fail before a valid retirement gate can pass, and the linked upstream PR is still open.
- `HLP-204` (retirement_gate): Retirement gate status is failed.
- `HLP-204` (uncertainty): The broader gate was not executable because its prerequisite override-map interface is absent at the exact target; the linked upstream PR remains open.
- `HLP-209` (retirement_gate): Retirement gate status is partial.
- `HLP-209` (uncertainty): The required post-restart runtime probe and ordinary review-path validation were not run because this unit may not mutate the effective runtime or service; retain until the full recorded gate passes.
- `HLP-211` (artifact): Backup-based reconstruction is unavailable because the documented ignored backup inputs are absent; the independent read-only effective-checkout reconstruction passed.
- `HLP-211` (retirement_gate): Retirement gate status is failed.
- `HLP-211` (uncertainty): PR 75951 remains open and only covers same-task session respawn, not the combined HLP-211/HLP-211b behavior.
- `HLP-211` (uncertainty): No linked upstream issue or PR covers HLP-211b terminal-controller flow routing.
- `HLP-211` (uncertainty): The full live retirement canary remains unexecuted under this unit's no-spend and no-runtime-mutation constraints.
- `HLP-226` (artifact): The documented private backup reconstruction input was approval-denied under #264 and is neither rerun, replaced, nor inferred, so the HLP-226b reconstruction and the record-level artifact verification remain unavailable; the HLP-226c patch checksum, parser control, and byte-for-byte reconstruction against maintained fork base 415056fee527c5a2302370bd6dba56f84b9a4202 passed and do not establish HLP-226b byte equivalence. No reconstruction has been performed against the inspected upstream revision, which does not contain the required behavior.
- `HLP-226` (retirement_gate): Retirement gate status is failed.
- `HLP-226` (uncertainty): The exact target is only partially equivalent: it retains omitted-workspace cross-profile routing but lacks the explicit-worktree, conflict-rejection, and affinity-terminal dir-source behavior required for retirement.
- `HLP-226` (uncertainty): Issue #226 is reopened, and the completing upstream PR remains open.
- `HLP-226` (uncertainty): The documented private backup reconstruction input is unavailable after its approval-denied existence check; no replacement or inferred reconstruction is recorded.
- `HLP-226` (uncertainty): HLP-226c remains a downstream component: the objective's pre-dispatch inspection at applied upstream revision 67764dc0863349a384c16425e73ee8571f3a94b7 recorded in specs/hlp-226-cross-board-project-inheritance/evidence/HLP-226C.md found no equivalent shared-dir/board-bound recovery, and no recurrence-level upstream inspection exists at this record's inspected revision 4f22543509d1b91dc45bcb369447126c5eb14fb7.
- `HLP-246` (retirement_gate): Retirement gate status is failed.
- `HLP-246` (uncertainty): No linked upstream issue or PR was located for equivalent attachment identity behavior.
- `HLP-246` (uncertainty): A future upstream change must still pass the full pre-transport, readback, legacy-row, and byte-for-byte tarball gate; source similarity or a merged label is insufficient.
- `HLP-247` (retirement_gate): Retirement gate status is failed.
- `HLP-247` (uncertainty): No linked upstream issue or PR was located for the archived-parent dependency distinction.
- `HLP-247` (uncertainty): The active detailed ledger section is reconciled independently even though it is absent from the active summary table.
- `HLP-262` (artifact): The documented reconstruction input is unavailable, and the exact upstream lacks the origin-signal prerequisite needed to apply the full patch; checksum and parser controls do not establish a reconstruction pass.
- `HLP-262` (retirement_gate): Retirement gate status is failed.
- `HLP-262` (uncertainty): The exact upstream lacks both the origin_signal API prerequisite and sticky handling for origin_signal events.
- `HLP-262` (uncertainty): The full input, revision, and recovery regression with database reopen and native-controller resolution was not executable after the prerequisite failure.
- `HLP-262` (uncertainty): The documented pre-change reconstruction input is unavailable; no byte-equivalence claim is recorded.
- `HLP-275` (retirement_gate): Retirement gate status is not_executed.
- `HLP-275` (uncertainty): The provider's exact per-side image limit remains bounded but unknown; the reused policy (4 MiB encoded data / 7,900 px) lies between the largest observed-accepted side and the smallest observed-rejected side.
- `HLP-275` (uncertainty): The upstream mechanism's stricter thresholds change within-cap byte behavior relative to this objective's documented controls, so it is not a drop-in replacement without a new oracle run.
- `HLP-280` (artifact): The exact local reconstruction passed, but its already-modified operator runtime preimage is private and not a public release artifact. Public readers must not infer clean upstream applicability from this patch checksum.
- `HLP-280` (retirement_gate): Retirement gate status is failed.
- `HLP-280` (uncertainty): The inventory upstream lacks the affinity origin primitives.
- `HLP-280` (uncertainty): Clean public-baseline reconstruction is not claimed; the exact local preimage is retained privately.
- `HLP-305` (artifact): The exact local reconstruction passed, but the already-modified editable runtime preimages are private and are not public release artifacts. Public readers must not infer clean upstream applicability from the portable patch checksum.
- `HLP-305` (retirement_gate): Retirement gate status is failed.
- `HLP-305` (uncertainty): The already-running TUI and gateway have not yet reloaded the installed bytes; live activation and the real recurrence canary remain pending.
- `HLP-305` (uncertainty): Current upstream still contains the unconditional refresh-exception interrupt and no equivalent issue or pull request was found.
- `HLP-310` (artifact): The documented reconstruction input is based on maintained fork base 6243e40ea6b06e85061bf3fedffaad43eed51dec rather than the historical inspected upstream revision 4f22543509d1b91dc45bcb369447126c5eb14fb7; checksum and parser controls pass without establishing full-patch upstream reconstruction.
- `HLP-310` (retirement_gate): Retirement gate status is failed.
- `HLP-310` (uncertainty): The inspected upstream lacks snapshot exclusions for HERMES_DELEGATED_CHILD_CONTEXT and HERMES_KANBAN_*.
- `HLP-310` (uncertainty): Maintained fork commit 25cabeb25327199a03aa3cf1613ed2f815f646cb is downstream-only; no equivalent upstream change exists.
- `HLP-335` (artifact): No public portable patch exists under patches/hermes. The exact dirty runtime preimage is private and not a public release artifact. Public readers must not infer clean upstream applicability from the recorded hashes.
- `HLP-335` (retirement_gate): Retirement gate status is failed.
- `HLP-335` (uncertainty): Upstream PR 95199 remains open and is not an exact-revision behavioral pass of this local delta.
- `HLP-335` (uncertainty): No public portable patch is checked into patches/hermes; reconstruction uses a private dirty preimage.
- `HLP-354` (artifact): The documented reconstruction input is based on maintained fork base 6243e40ea6b06e85061bf3fedffaad43eed51dec rather than the historical inspected upstream revision 4f22543509d1b91dc45bcb369447126c5eb14fb7; checksum and parser controls pass without establishing full-patch upstream reconstruction.
- `HLP-354` (retirement_gate): Retirement gate status is failed.
- `HLP-354` (uncertainty): The inspected upstream roots new worktrees at incidental HEAD and lacks worktree_base_ref.
- `HLP-354` (uncertainty): Maintained fork commit 7d3173e1f3dba107f9a389d4e35c95f215775ee1 is downstream-only; no equivalent upstream change exists.
- `HLP-362` (artifact): The exact maintained-fork reconstruction, focused candidate checks, and fork PR #5 merged source passed, but public upstream equivalence remains unavailable because upstream has no equivalent independent-review requirement.
- `HLP-362` (retirement_gate): Retirement gate status is not_executed.
- `HLP-362` (uncertainty): The upstream Hermes Kanban protocol does not distinguish self-review from independent review at the inspected revision.
- `HLP-369` (artifact): The exact maintained-fork reconstruction, focused candidate checks, and fork PR #6 merged source passed, but the public upstream revision is not an equivalent reconstruction input; upstream artifact equivalence therefore remains unavailable.
- `HLP-369` (retirement_gate): Retirement gate status is failed.
- `HLP-369` (uncertainty): The inspected upstream revision retains the circular request-review judge gate and has no equivalent exact recovery-controller route.
- `HLP-372` (artifact): The exact maintained-fork reconstruction, focused candidate checks, and PR #10 candidate passed, but public upstream equivalence remains unavailable because upstream lacks profile-scoped script root resolution.
- `HLP-372` (retirement_gate): Retirement gate status is not_executed.
- `HLP-372` (uncertainty): Upstream hardcodes default ~/.hermes/scripts in validation and diagnostic error strings at the inspected revision.
- `HLP-382` (retirement_gate): Retirement gate status is not_executed.
- `HLP-382` (uncertainty): The historical holder that first exhausted the append budget was never identified; the causal class (unbounded publication transaction) is proven and the repair is verified against that class, not against the unavailable historical identity.
- `HLP-385` (artifact): The exact maintained-fork reconstruction, prompt size checks, and PR #9 candidate passed, but public upstream equivalence remains unavailable because upstream prompt guidance remains ambiguous.
- `HLP-385` (retirement_gate): Retirement gate status is not_executed.
- `HLP-385` (uncertainty): Upstream KANBAN_GUIDANCE conflates pre-created review/QA and release children at the inspected revision.
- `HLP-388` (artifact): The exact maintained-fork reconstruction, focused candidate checks, and PR #10 candidate passed, but public upstream equivalence remains unavailable because upstream omits launch cwd persistence for cron sessions.
- `HLP-388` (retirement_gate): Retirement gate status is not_executed.
- `HLP-388` (uncertainty): Upstream does not persist cron launch workdir in the session row at the inspected revision.
- `HLP-389` (retirement_gate): Retirement gate status is not_executed.
- `HLP-389` (uncertainty): The syntax-aware view intentionally matches the already-permitted `python3 -c` form: a path that appears only inside a quoted non-shell interpreter heredoc body is no longer scanned as a shell script. Direct lifecycle text in that body is still blocked.
- `HLP-393` (artifact): The exact maintained-fork reconstruction, focused candidate checks, and PR #10 candidate passed, but public upstream equivalence remains unavailable because upstream lacks cron commissioning origin and kanban auto-subscription.
- `HLP-393` (retirement_gate): Retirement gate status is not_executed.
- `HLP-393` (uncertainty): Upstream does not capture or restore durable commissioning origin for cron-spawned tasks at the inspected revision.

## Artifact integrity

- `HLP-188`: not_applicable
- `HLP-189`: not_applicable
- `HLP-191`: not_applicable
- `HLP-194`: not_applicable
- `HLP-198`: not_applicable
- `HLP-204`: not_applicable
- `HLP-209`: not_applicable
- `HLP-211`: unavailable
- `HLP-226`: unavailable
- `HLP-246`: not_applicable
- `HLP-247`: not_applicable
- `HLP-262`: unavailable
- `HLP-275`: passed
- `HLP-280`: unavailable
- `HLP-305`: unavailable
- `HLP-310`: unavailable
- `HLP-335`: unavailable
- `HLP-354`: unavailable
- `HLP-362`: unavailable
- `HLP-369`: unavailable
- `HLP-372`: unavailable
- `HLP-382`: passed
- `HLP-385`: unavailable
- `HLP-388`: unavailable
- `HLP-389`: passed
- `HLP-393`: unavailable

## Safe next decisions

- Retain every local guarantee whose exact-revision full behavioral gate is not passed.
- Execute the recorded gates on a separately selected, read-only candidate revision before any retirement decision.
- No final runtime is selected by this report, and it does not make a release claim.
