# Hermes patch reconciliation preflight

Observation timestamp: `2026-09-01T19:51:46Z`

Upstream inspected: `https://github.com/NousResearch/hermes-agent@4f22543509d1b91dc45bcb369447126c5eb14fb7`

Source ledger SHA-256: `bbf0761468beede46e361371cc7f3e38bb51fcf797aed410f7c21e6c88df08c7`

## Remaining local guarantees

- `HLP-188`: Exact upstream source has the initial blocked status but not the durable sticky event. The isolated behavioral probe showed auto-promotion without unblock, so the local guarantee remains required.
- `HLP-189`: Upstream already supports max_retries in the database layer but does not expose or forward it through kanban_create. With no executed full gate, the local interface guarantee remains required.
- `HLP-191`: Upstream can escalate repeated blocks to triage but still treats all triage tasks as auto-decomposition candidates and lacks the durable recovery boundary. The local human gate must remain.
- `HLP-194`: Upstream has a name-based stop nudge and a clean-exit backstop, but it lacks durable exactly-one receipt validation and EX_PROTOCOL=76. The local terminal-handoff guarantee remains required.
- `HLP-198`: Retain HLP-198. Exact-target source and a disposable behavioral gate reproduce the stale claimed-task branch mismatch in ready and review dispatch.
- `HLP-204`: Retain HLP-204. The target retains only the uniform cap, while the required asymmetric override interface remains solely in an open upstream PR.
- `HLP-209`: The exact upstream target contains and behaviorally passes the HLP-209 directory exemption, but the recorded runtime retirement gate remains incomplete.
- `HLP-211`: Retain both HLP-211 and HLP-211b. The exact public snapshot lacks prerequisite runtime interfaces, and the linked open PR is a narrower same-task resumption change. The tracked HLP-211b patch checksum, parser check, and read-only effective-checkout byte reconstruction passed; only the ignored backup input remains unavailable.
- `HLP-226`: Retain HLP-226 and HLP-226b. Exact upstream lacks the affinity-terminal Project-source variant as well as the explicit-worktree and conflicting-Project behavior. The portable HLP-226b patch checksum and parser controls pass, but the documented reconstruction input and overall artifact verification remain unavailable.
- `HLP-246`: Retain HLP-246. The exact public snapshot accepts a synthetic truncated payload with valid base64 and has no sender identity claims, SHA-256 persistence, or readback verification.
- `HLP-247`: Retain HLP-247. The exact public snapshot still promotes an eventless blocked child on parent archive, while the required todo and non-sticky compatibility controls remain promotable.
- `HLP-262`: Retain HLP-262. Exact upstream has neither the origin_signal block API prerequisite nor sticky predicate support for origin_signal, and the portable patch checksum and parser controls pass without establishing full-patch reconstruction from unavailable inputs.
- `HLP-280`: Retain the reviewed HLP-280 candidate pending activation. The portable patch reconstructs the isolated exact-active-byte candidate and the active runtime remains unchanged.

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
- `HLP-226` (artifact): The documented private backup existence check was approval-denied under #264 and is neither rerun, replaced, nor inferred. The reconstruction input and full reconstruction remain unavailable; checksum and parser controls do not establish byte equivalence.
- `HLP-226` (retirement_gate): Retirement gate status is failed.
- `HLP-226` (uncertainty): The exact target is only partially equivalent: it retains omitted-workspace cross-profile routing but lacks the explicit-worktree, conflict-rejection, and affinity-terminal dir-source behavior required for retirement.
- `HLP-226` (uncertainty): Issue #226 is reopened, and the completing upstream PR remains open.
- `HLP-226` (uncertainty): The documented private backup reconstruction input is unavailable after its approval-denied existence check; no replacement or inferred reconstruction is recorded.
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
- `HLP-280` (retirement_gate): Retirement gate status is not_executed.
- `HLP-280` (uncertainty): The candidate is not activated; backup, reload, PID/state, live no-watcher canaries, and rollback facts remain pending for the second evidence-only PR.
- `HLP-280` (uncertainty): No upstream issue or pull request is proposed for the downstream HLP-280 candidate.

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
- `HLP-280`: passed

## Safe next decisions

- Retain every local guarantee whose exact-revision full behavioral gate is not passed.
- Execute the recorded gates on a separately selected, read-only candidate revision before any retirement decision.
- No final runtime is selected by this report, and it does not make a release claim.
