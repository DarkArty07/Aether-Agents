# Hermes patch reconciliation preflight

Observation timestamp: `2026-09-27T13:25:51Z`

Upstream inspected: `https://github.com/NousResearch/hermes-agent@4f22543509d1b91dc45bcb369447126c5eb14fb7`

Source ledger SHA-256: `ed2a6a27184dee253f2b3e6d86f83907ae7a2ab18061ec112a8dc88e6b05c84a`

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
- `HLP-334`: Retain HLP-334. Optional native collaboration adds an adjunct same-board table, optional create/comment arguments, and origin-bound TUI/gateway delivery without replacing the terminal-notification cursor or promoting peer evidence to owner authority.
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
- `HLP-420`: Retain HLP-420. The auxiliary Responses adapter now preserves phase, top-level and item status, incomplete reason, output-text fallback and tool calls, never turns incomplete/cancelled output into finish_reason=stop, keeps commentary/analysis narration out of assistant content, and carries tool_choice through call_llm/_build_call_kwargs without sending the unsupported Router fields.
- `HLP-425`: Retain HLP-425. The maintained fork and active Aether runtime now preserve one flow-bound Supervisor conversation across same-card review while keeping the candidate workspace and generic Hermes semantics separate.
- `HLP-426`: Retain HLP-426. The maintained fork now terminates a worker whose run has ended and is no longer current before the dispatcher can spawn a successor on the same workspace, with elapsed time never a criterion; no upstream equivalent was found at the inspected revision, so this remains a downstream-only correction for the maintained fork.
- `HLP-427`: Retain HLP-427. The maintained fork preserves the latest explicit review/ready retry phase across a phase-less Aether recovery signal, with exact source, runtime bootstrap and live same-card review evidence; no equivalent public upstream interaction exists.
- `HLP-428`: Retain HLP-428. The maintained fork recovers canonical Project provenance for non-affinity direct parent worktree children, refuses cross-project mismatches before task persistence, and cleanly bounds review failure containment without unverified notifications; verified by RED/GREEN reproduction, four-round strict contract audit, and exact tree reconstruction.
- `HLP-433`: Retain HLP-433. The maintained fork preserves provider reasoning tokens across the Responses adapter boundary into chat-compatible usage and SessionDB accounting without altering input/output/total tokens or double-counting; verified by RED/GREEN reproduction, strict contract audit, and exact tree reconstruction. Merged at 621047dc1c10cceb2825013cc8bb611b4d0e8de1 but deferred for RC16 (selected pin 58f8c37a49b341f25b8fdd6310542fe932031b8d) and not yet adopted by the effective runtime, hence MAINTAINED_FORK_ONLY.
- `HLP-435`: HLP-435 corrects the two observed normalized-only quote imbalances in maintained-fork source. PR #19 merged as b287195d63d47d73788653bdd012c2fbfe00c0ac with tree identical to reviewed f459cfa0. Keep deferred at unchanged RC16 pin 58f8c37a49b341f25b8fdd6310542fe932031b8d; no RC17, runtime adoption or upstream retirement is claimed.
- `HLP-460`: Retain HLP-460. The maintained fork refuses prospective parentage that would give an opted-in Aether flow a second root, inside the native write transaction, while preserving generic multi-root DAGs, valid rootless promotion and review fail-closed behavior; the portable patch reconstructs the reviewed candidate tree exactly and reverses to the base tree exactly.
- `HLP-473`: Base 54abacd1c38ce6300997289628fe2f2a7569df18; implementation c81053679cd57a24f5a7a6c93b6cd450eee47343; reviewed implementation tree 49189104a6888ef604ff0733d97b6b05e25b0d33; merged source 30b4846a2c8063528d491f48950b3b341b0ce7d7 (fork PR #21). Source-only. RC16 still selects 58f8c37a49b341f25b8fdd6310542fe932031b8d. Declared paths can exist at that old pin without this fix. No runtime restart, configuration/credential change, tag, RC17 or installed-behavior claim. Fork Actions disabled (NOT RUN). Retirement is not qualified.
- `HLP-474`: Base b287195d63d47d73788653bdd012c2fbfe00c0ac; implementation 7755f82df15786285378732ef17544b4736c4b81; reviewed implementation tree 105071996d00bfbb361771d82d0863552380fccb; merged source 54abacd1c38ce6300997289628fe2f2a7569df18 (fork PR #20). Source-only. RC16 still selects 58f8c37a49b341f25b8fdd6310542fe932031b8d. Declared paths can exist at that old pin without this fix. No runtime restart, configuration/credential change, tag, RC17 or installed-behavior claim. Fork Actions disabled (NOT RUN). Retirement is not qualified.
- `HLP-475`: Base 30b4846a2c8063528d491f48950b3b341b0ce7d7; reviewed implementation f21c733b800a2dcc8a29639c90e5f84eb7d6278b; implementation tree c69e40e7c9f362458833778b89f88430fb9e10c4; maintained-fork PR #22 merged at 58750d6cf8182c0ff5093719b9e7cc5026621fbf. Source-only. Selected fork source is merged; installed runtime remains unchanged. No runtime restart, configuration/credential change, tag, RC17 or installed-behavior claim. Fork Actions disabled (NOT RUN). Retirement is not qualified.

## Qualified upstream equivalents

- `HLP-209`: Qualified source disposition: upstream_verified; retirement recommendation: retain.
- `HLP-473`: Qualified source disposition: upstream_verified; retirement recommendation: retain.

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
- `HLP-246` (selected_source_evidence): no repository-relative component path or declared portable patch path is recorded for this entry
- `HLP-246` (uncertainty): No linked upstream issue or PR was located for equivalent attachment identity behavior.
- `HLP-246` (uncertainty): A future upstream change must still pass the full pre-transport, readback, legacy-row, and byte-for-byte tarball gate; source similarity or a merged label is insufficient.
- `HLP-247` (retirement_gate): Retirement gate status is failed.
- `HLP-247` (selected_source_evidence): no repository-relative component path or declared portable patch path is recorded for this entry
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
- `HLP-334` (artifact): The exact maintained-fork reconstruction, focused candidate checks, and PR #11 merge passed, but public upstream equivalence remains unavailable because upstream lacks optional collaboration opt-in, the adjunct table, origin-route matching, and labeled peer delivery.
- `HLP-334` (retirement_gate): Retirement gate status is not_executed.
- `HLP-334` (uncertainty): Upstream Hermes at the inspected public revision has no optional collaboration store or origin-bound TUI/gateway delivery.
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
- `HLP-420` (artifact): Portable reconstruction passed and the focused candidate checks are green, but public upstream equivalence is unavailable: both inspected upstream revisions still synthesize finish_reason=stop for incomplete/cancelled terminals and still concatenate every message item. No live runtime was activated by this unit.
- `HLP-420` (retirement_gate): Retirement gate status is not_executed.
- `HLP-420` (uncertainty): tool_choice passthrough covers call_llm, _call_llm_impl, _build_call_kwargs, the Responses adapter and the synchronous same-provider retry; the asynchronous auxiliary entry point and the emergency fallback candidate builders still omit tool_choice, so a fallback attempt keeps the route default instead of forcing the structured call.
- `HLP-420` (uncertainty): The forced submit_graph_fragment structured-call contingency is not implemented here; this unit only makes the transport capable of carrying it deterministically, and the async path would need its own change before a forced call could be proven there.
- `HLP-420` (uncertainty): A completed response with empty output and no top-level output_text still returns no content with finish_reason=stop; classifying that hollow response as retryable remains the caller's decision.
- `HLP-425` (artifact): The exact local patch reconstructs and is active in the Aether runtime, but public upstream equivalence remains unavailable at the inspected revision.
- `HLP-425` (retirement_gate): Retirement gate status is not_executed.
- `HLP-425` (uncertainty): Long-term reduction in review time and repeated-review frequency has not yet been measured on representative organic work.
- `HLP-425` (uncertainty): Existing already-running conversations retain their cached prompt until restarted; adoption does not rewrite stored conversation history.
- `HLP-426` (artifact): The patch reconstructs exactly in the maintained fork and is active in that lineage, but no public upstream equivalence exists at the inspected revision, and the live runtime still runs the pre-RC release. The structured record therefore cannot claim a verified public artifact.
- `HLP-426` (retirement_gate): Retirement gate status is not_executed.
- `HLP-426` (uncertainty): The fix guarantees the successor boundary, not instantaneous exit: a superseded process can still run until the next dispatch tick reaps it (bounded by one dispatch interval).
- `HLP-426` (uncertainty): Runs spawned by an older runtime carry no (pid, start_time) fingerprint in their `spawned` event and are therefore never signalled — a deliberate fail-safe, not an unverified guess.
- `HLP-426` (uncertainty): The withheld-spawn path is proven by the focused unit test (signal made a no-op) rather than by the canary, because a SIGKILL-surviving process cannot be fabricated.
- `HLP-427` (artifact): The patch reconstructs exactly in the maintained fork and has a verified temporary runtime bootstrap, but no public upstream equivalent or immutable Aether rc.2 artifact carrying it exists yet.
- `HLP-427` (retirement_gate): Retirement gate status is not_executed.
- `HLP-427` (uncertainty): The temporary runtime bootstrap proves the behavior in the pre-RC runtime but is not a substitute for immutable rc.2 publication and activation.
- `HLP-427` (uncertainty): The fix intentionally skips only phase-less origin_signal records; every other legacy event without phase metadata keeps the historical ready fallback.
- `HLP-428` (artifact): The patch reconstructs exactly in the maintained fork and is integrated at merged revision 58f8c37a49b341f25b8fdd6310542fe932031b8d (PR #16) with the aggregate pinned there; only a public upstream equivalent is still missing, which is why this entry stays unavailable rather than passed.
- `HLP-428` (retirement_gate): Retirement gate status is not_executed.
- `HLP-428` (uncertainty): Upstream hermes-agent lacks board-level Project recovery and origin-signal bounding for review-lane containment.
- `HLP-428` (uncertainty): The regression test module tests/hermes_cli/test_kanban_project_provenance.py is introduced by this patch and does not exist at pre-merge base aed6591a69. It is now declared as a component and resolves present at the merged revision 58f8c37a49b341f25b8fdd6310542fe932031b8d that the aggregate is pinned to.
- `HLP-428` (uncertainty): The optional 'Previous review returns (this task)' context line introduced in RC15 does not exist at selected pin 58f8c37a49b341f25b8fdd6310542fe932031b8d; retained RC15 review guidance uses its documented durable-history fallback when this optional context is absent. This absence is a disclosed candidate limitation, not an enforcement gate or retirement claim.
- `HLP-433` (artifact): The patch reconstructs exactly in the maintained fork and candidate checks pass, but public upstream equivalence is unavailable: inspected upstream revisions reconstruct only flat prompt/completion/total tokens from Responses usage. Merged revision 621047dc1c10cceb2825013cc8bb611b4d0e8de1 (PR #17) is a descendant of the selected pin 58f8c37a49b341f25b8fdd6310542fe932031b8d; the merged source has not been installed, reloaded or otherwise adopted by the effective Aether runtime.
- `HLP-433` (retirement_gate): Retirement gate status is not_executed.
- `HLP-433` (uncertainty): Upstream hermes-agent lacks reasoning token preservation across the Responses adapter boundary.
- `HLP-433` (uncertainty): The regression test module tests/agent/test_auxiliary_client_responses_reasoning_433.py is introduced by this patch and does not exist at selected pin 58f8c37a49b341f25b8fdd6310542fe932031b8d, making its absence visible in candidate reconciliation.
- `HLP-433` (uncertainty): The merged maintained-fork revision 621047dc1c10cceb2825013cc8bb611b4d0e8de1 carrying this behavior is a descendant of the selected pin 58f8c37a49b341f25b8fdd6310542fe932031b8d and has not been adopted by the effective Aether runtime; live adoption and effective-runtime qualification remain deferred successors under issue #433, so no installed behavior is asserted.
- `HLP-435` (retirement_gate): Retirement gate status is not_executed.
- `HLP-435` (uncertainty): Both modified paths exist at the frozen RC16 selected pin 58f8c37a49b341f25b8fdd6310542fe932031b8d, but path presence is not proof of the #435 fix. The repair is only in later maintained-fork source b287195d63d47d73788653bdd012c2fbfe00c0ac; it has not been adopted by the installed runtime.
- `HLP-435` (uncertainty): The accepted fork candidate retains the pre-existing escaped-quote bypass difference documented against newer upstream and the baseline-shared real-binary test failure; neither is repaired by this patch.
- `HLP-460` (retirement_gate): Retirement gate status is not_executed.
- `HLP-460` (uncertainty): Source-only. Reviewed implementation 34a7f1e5678ba78cb011147a7462370e5b7343bb (tree b26638974fc134da866b821ab3c4b34ab430aeb3) merged into maintained-fork aether-main through PR #23 at 007cfb77676b6b024d2c0986f4585e6cfdcf18d6 with the same tree. The selected installed/release pin remains 58750d6cf8182c0ff5093719b9e7cc5026621fbf; the aggregate deliberately evaluates HLP coverage at that unchanged pin and HLP-460 remains deferred there. Fork PR reports no checks (Actions run count 0; branch not protected), not a green CI claim. No runtime restart, installed-behavior qualification, tag, RC17 or credential change.
- `HLP-460` (uncertainty): Upstream hermes-agent lacks the ancestor-root helpers, collaboration-root query and Aether opt-in corroboration at the historical inspected revision, inspected v2026.9.24 release (commit f97608f178d1ffeca59860195ab7da295f7c8e5f) and main f039f028f2bd5c6e2131b4ffaa4b200c81db68a3 at review; retirement remains unqualified.
- `HLP-460` (uncertainty): Full fork test suite and cross-platform/Windows CI are NOT RUN by this unit; the focused 3-file hermetic reproduction above plus the parent unit's independently reviewed RED/GREEN are the whole verification basis.
- `HLP-473` (retirement_gate): Retirement gate status is not_executed.
- `HLP-473` (uncertainty): Source-only. RC16 still selects 58f8c37a49b341f25b8fdd6310542fe932031b8d. Declared paths can exist at that old pin without this fix. No runtime restart, configuration/credential change, tag, RC17 or installed-behavior claim. Fork Actions disabled (NOT RUN). Retirement is not qualified.
- `HLP-474` (retirement_gate): Retirement gate status is not_executed.
- `HLP-474` (uncertainty): Source-only. RC16 still selects 58f8c37a49b341f25b8fdd6310542fe932031b8d. Declared paths can exist at that old pin without this fix. No runtime restart, configuration/credential change, tag, RC17 or installed-behavior claim. Fork Actions disabled (NOT RUN). Retirement is not qualified.
- `HLP-475` (retirement_gate): Retirement gate status is not_executed.
- `HLP-475` (uncertainty): Source-only. Selected maintained-fork revision 58750d6cf8182c0ff5093719b9e7cc5026621fbf contains the reviewed fix; installed runtime remains unchanged. No runtime restart, configuration/credential change, tag, RC17 or installed-behavior claim. Fork Actions disabled (NOT RUN). Retirement is not qualified.

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
- `HLP-334`: unavailable
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
- `HLP-420`: unavailable
- `HLP-425`: unavailable
- `HLP-426`: unavailable
- `HLP-427`: unavailable
- `HLP-428`: unavailable
- `HLP-433`: unavailable
- `HLP-435`: passed
- `HLP-460`: passed
- `HLP-473`: passed
- `HLP-474`: passed
- `HLP-475`: passed

## Selected maintained-fork source

Selected source: `https://github.com/DarkArty07/aether-hermes@58750d6cf8182c0ff5093719b9e7cc5026621fbf` (presence resolved from a checkout: `true`)

| Verdict | Entries |
| --- | --- |
| present | 36 |
| partial | 0 |
| absent | 0 |
| unverified | 2 |

- `HLP-246`: unverified — no repository-relative component path or declared portable patch path is recorded for this entry
- `HLP-247`: unverified — no repository-relative component path or declared portable patch path is recorded for this entry

## Safe next decisions

- Retain every local guarantee whose exact-revision full behavioral gate is not passed.
- Execute the recorded gates on a separately selected, read-only candidate revision before any retirement decision.
- No final runtime is selected by this report, and it does not make a release claim.
