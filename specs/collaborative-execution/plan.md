# Active Morfeo collaboration — execution plan

**Status:** owner-approved execution objective and material design; canonical contract validation/commit precedes pipeline handoff.
**Owner decision:** proceed autonomously with the full scoped change, leave this plan first, then execute. One coordinated delivery may include the principal Aether PR and the necessary maintained-Hermes-fork PR. This is not authority for unrelated runtime changes or a new behavioral qualification campaign.
**Base:** Aether `aaeacb211b892b5dd893ecaa4abba7933011d12c`; maintained Hermes `3b81e9d91cc3a0662b910726a44c94ed328b1e90`.
**Canonical objective:** #334; reconcile #317 and preserve #407 as an already-closed postmortem.

## Ordered work and ownership

1. **Morfeo — finalize the material design and contract.** Reuse the completed scope/source investigation. Resolve the exact intermediate-event, recipient, response, recovery and authority semantics against the native interfaces; write them below and in the specification/quickstart. Capture owner-approved closure as an unverified behavioral mitigation. Finalize exactly one project-bound Objective Contract. No product implementation is dispatched from an incomplete API or test oracle.
2. **Supervisor — inspect and decompose.** Independently check design sufficiency, preserve one execution owner and the exact flow, and derive bounded implementation/review units. Release independent work without duplicating ownership. Morfeo does not pre-create those units.
3. **Implementer under Supervisor — implement the narrow native gap and packaged guidance.** Reuse board comments/events, subscriptions and existing continuation. Add no alternate bus, scheduler, autonomous semantic judge or review-count gate. Build the Hermes candidate from the maintained fork, not the dirty provisioned installation. Keep Aether resources, owning documentation and test changes consistent with the material design.
4. **Supervisor — independent review and integrated verification.** Check each changed mechanism and the actual shared interfaces. Repeated equivalent defects require a consolidated cause/response, not blind successive returns. Route a genuine design contradiction to Morfeo; unaffected work continues. Record actual results and preservation limits.
5. **Supervisor — ordinary GitHub closeout.** Merge the reviewed fork dependency through its normal checks, update the Aether traceable dependency/patch evidence as required by existing packaging, then merge the principal Aether PR through required checks. Preserve each accepted unit's attribution. No tags, package publication or public release are requested.
6. **Supervisor — scoped runtime adoption.** Apply the reviewed changes through the existing lifecycle and documented fork reconciliation, preserving unrelated local modifications and owner profile/configuration. Verify imported source, installed resource identity and fresh instruction loading. Reload only in a verified no-active-worker window; do not kill ongoing workers or pretend cached sessions adopted changed files.
7. **Morfeo — final owner-objective reception.** Inspect the exact final revision and runtime evidence against this objective, without repeating a long synthetic model campaign. Supervisor reconciles #334/#317 and adds the mitigation link to #407; #367 remains functionally unaccepted and the stopped Telegram Monitor is not reactivated. Audit only this objective's residue. Report separately what was mechanically verified and what remains behaviorally unverified.

## Testing standard resolved from the approved scope

The owner approved implementation with ordinary proportionate verification and runtime adoption, while explicitly declining to require a long-term recurrence/organic-behavior qualification before closure. Therefore:

- Use deterministic tests of the real native APIs in disposable, isolated state, focused resource/document/packaging/lifecycle tests, affected regression suites, and the normal required repository checks.
- Verification must distinguish persistence, technical delivery, explicit acknowledgment/response and resolution. It must test correct recipient/binding, recipient busy/restart behavior, recoverable failure, peer-vs-owner provenance, stale references and preservation of independent work.
- Exercise final source/resource loading through the provisioned interpreter and confirm runtime adoption. No live LLM/Telegram test campaign, new provider, credential, arbitrary message destination or paid verification request is added by this plan.
- Resource assertions are not evidence of model obedience. Event tests are not evidence that a model will make the right design decision. No absence-of-incidents, elapsed-time or throughput claim is required to close #317.
- Preserve required checks and compare any unrelated existing failure against the baseline; do not weaken them or absorb unrelated work silently.

## Convergence and stop boundaries

- Work remains one owner objective. Do not split a product change into direct edits to evade independent review.
- A same-class defect is consolidated with its producer; a missing or unsuitable material design returns to Morfeo. Owner-reserved changes to intent, acceptance or authority still need the owner.
- No unbounded retries, new framework, guessed routing IDs, cross-project broadcast, early issue closure or source-private-state publication.
- Runtime activation waits rather than interrupts workers. A protected-edge denial is authoritative. Runtime failure uses the existing rollback-first recovery procedure, not a new product pipeline.
- Expected declared mutations of a disposable test board/session are permitted; unrelated live boards, sessions, registries and owner settings are preserved. A test is not required to leave its own legitimate run records byte-identical.

## Delivery classification

- `release_action = defer`
- `release_channel = none`
- `release_impact` will be classified against the implemented compatibility surface; local activation is not a published release.

## Material design — decided within the approved scope

### D1. Extend native comments and events, not the coordination architecture

Use an additive optional `collaboration` object on the existing `kanban_comment` tool and an opt-in `collaboration="advisory"` argument on `kanban_create` for a new root. Missing/null keeps legacy behavior. Only the trusted originating session may opt in its own root; child creation cannot enable or override the origin. Store opt-in as a root task event. Inherit it only through the unique same-board, same-Project ancestor root and its verified affinity. Keep all routing IDs runtime-derived.

Native Hermes remains role-neutral: the origin is the root's recorded commissioning session; the controller is the existing same-affinity execution controller; the peer may be an exact task in that root's dependency graph. Aether's procedures map origin to Morfeo and controller to Supervisor. No hard-coded role names, model IDs, chat destinations or project IDs belong in native routing.

Decision assumption: board dependencies, root origin subscription and controller affinity already provide the necessary identities. Missing/ambiguous/archived identity returns an explicit unavailable/conflict result; never use the current board, profile name alone or most recent session as a substitute. Canonical board metadata supplies contract identity/version. No backfill of opt-in to already running unrelated contracts.

### D2. Shared tool input and response semantics

Existing `kanban_comment(task_id, body, board)` remains valid and does not implicitly request a peer turn. The optional object supports:

- `{"action":"request", "recipient":"origin"|"controller"|<exact task id>, "evidence_refs":[...], "idempotency_key":<caller key>}` — create an addressed request on the owning task thread. Body contains the question, what it blocks, and requested answer; refs contain project-relative path, optional full Git revision and optional locator. The runtime supplies source task/run/session, root, board, Project and contract/version. A non-worker origin supplies the subject task through `task_id` and is authenticated against the root subscription.
- `{"action":"respond", "request_id":<returned id>, "disposition":"advice"|"continue"|"design_revision"|"owner_input"|"unavailable", "evidence_refs":[...]}` — a response by the verified recipient, recorded on the original thread and addressed back to the requester. A response is evidence/advice, not a change of authority. `design_revision` points to Morfeo's owning artifact/contract action; it does not itself mutate a contract.
- `{"action":"ack", "message_id":<returned id>}` — the intended recipient explicitly records receipt. This is a model/tool acknowledgment, not proof of understanding.
- `{"action":"resolve", "request_id":<returned id>, "disposition":"applied"|"not_applicable"|"stale"}` — the requester records the attributable disposition after checking the response against current sources. Body explains the result. Resolution never automatically completes/unblocks a task or approves a review.

A `kanban_comment` return with collaboration includes `{comment_id, collaboration_id, status, recipient_kind}` and the existing `ok/task_id`. IDs are database-assigned opaque handles from the native board, not guessed by an agent. `kanban_show` adds a bounded `collaboration` list with pending/acknowledged/responded/resolved/unavailable state, provenance and comment/evidence references. Request/response/resolve are idempotent within the originating board/root and caller key or referenced message; duplicate retries do not produce another peer run. Unknown keys/actions, truncation sentinels, conflicting binding, unauthorized recipient/response or secret-containing unsafe payloads follow native validation/redaction before mutation. Bounded body/reference limits reuse native limits; no arbitrary provider/network operation is accepted.

### D3. Durable state in the same board database

Add one narrowly scoped native adjunct table `kanban_collaboration` rather than a separate service/database. One row is an addressed collaboration message (explicit request, response or automatic evidence notice). Required data: assigned integer id; root/subject task and source run/event/comment references; source and recipient kind/binding; root contract/version binding; request/response linkage; immutable evidence references; delivery state `pending|queued|acknowledged`; resolution `open|responded|resolved|unavailable|stale`; enqueue/ack/resolution times; a bounded delivery lease and a deduplication key. Exact SQL column factoring and indexes are Implementer's local choice, but these data semantics and atomic transitions are shared design.

Persist the comment, message record and event in one native transaction. Store immutable text in the existing comments (or an existing lifecycle event for automatic notices); do not duplicate raw logs. Unique dedup keys prevent duplicate source-event/recipient messages. Delivery success and a response update different fields. A wake/steer return is only `queued`; `ack`/`respond` provides attributable consumption. Claim leases fence concurrent consumers and expire using native short delivery timing, not a business-progress timeout. A lost enqueue/failed steer does not advance to acknowledged or permanently remove pending work. On process loss, unacknowledged queued records are eligible for idempotent redelivery; a resumed recipient re-reads the record and current revision. Unanswered delivered requests stay visible but are not endlessly re-enqueued to a still-live session.

A terminal flow event, archived execution root or owner-stopped flow makes unresolved messages stale/unavailable and stops new autonomous wakes; preserve the record. A decomposition root merely becoming `done` is not terminal flow completion and must not expire collaboration. If only a recipient worker run ended, include the pending request in the next legitimate run of that same task, not another worker by profile. A changed run or candidate never silently rebinds old advice: show original revision and require requester revalidation; materially superseded contract/root advice is stale. Unavailable origin/closed session does not create another session or route to a different topic.

### D4. Proactive evidence without a convergence judge

For an opted-in root, native lifecycle transitions `review_requested`, `changes_requested`, and `blocked` enqueue an advisory evidence notice for the origin; root decomposition completion enqueues its handoff evidence once. These are notification opportunities, not automatic failure classifications, stops, approvals or a fixed review quota. Reports include exact source event/task/run and the existing summary/evidence references. Do not forward heartbeat, every tool call or unaddressed ordinary comment.

Coalesce automatic unconsumed notices for the same root while the origin is busy; retain covered source event IDs and the latest applicable summary/reference, not a growing raw transcript. Explicit questions are never erased by coalescing. The receiver is free to acknowledge `continue` without writing a second review. Emit no new notice from acknowledgment, peer response or resolution itself except the addressed response delivery, preventing a feedback loop. No periodic progress scheduler, numeric non-convergence classifier, semantic acceptance engine or permanent polling process is introduced; use existing notifier/agent safe-boundary loops.

### D5. Delivery and non-owner attribution

Extend the existing gateway notifier and TUI poller to process the collaboration records independently of the legacy terminal-notification cursor. The root's trusted subscription/commissioning identity selects the exact original session/chat/thread. Collaboration is internal wake only: no passive user ping for each exchange. Gateway successful internal work ends with the existing `NO_REPLY` mechanism unless a genuine owner decision, material status/result or unresolved capability needs reporting. The native envelope tells the model this; do not globally hide genuine errors or material owner-facing output. TUI uses the existing same-session pending/idle continuation and retains the durable message until explicit consumption; do not start a concurrent agent turn or discard it when an in-memory queue vanishes.

**Origin-selection clarification (Morfeo, during DELIVER review):** supporting both TUI and gateway means honoring the commissioning origin on either surface, not broadcasting one collaboration message to both surfaces. Other notification subscriptions on the same root are not additional collaboration recipients. With a TUI commissioning origin and an extra Telegram notification subscriber, only the exact TUI origin is eligible; with a Telegram commissioning origin and an extra TUI subscriber, only that exact Telegram origin is eligible. If persisted trusted origin identity cannot distinguish the eligible recipient, preserve the message with an explicit unavailable/conflict result rather than select by consumer reachability, recency or by allowing every platform to consume it. A dual-consumer test is an isolation/exclusivity control in both tick orders, not a requirement for two successful wakes. Existing terminal-notification fan-out remains unchanged. D3 recovery/redelivery concerns the same addressed origin after failed enqueue/process loss, never a second notification subscriber.

For an active addressed task/controller, integrate with the existing per-tool/safe-boundary comment bridge but do not call the owner-impersonating `steer` presentation for peer content. Deliver an explicitly labeled native peer-evidence block, retaining trusted role/session/task provenance and the statement that it cannot expand owner authority. Plain legacy notes keep compatibility but are labeled by their actual source; do not call every foreign profile the operator. Updating a durable enqueue state happens after successful enqueue, not before it.

If the controller is between phases, use its existing same-affinity controller continuation/attention path with a collaboration reference. Do not create a parallel Supervisor instance, bypass its active lease, invent a second workspace or falsely unblock a dependency. Extend the controller's existing attention consumption to distinguish a collaboration advisory from a blocked-parent recovery; only the latter may affect the parent state. Missing/ambiguous controller waits visibly. Unaffected Implementer tasks keep running. A task-recipient question does not create a new run of a completed implementation unit.

### D6. Canonical ownership and authored role amendments

Morfeo owns these prompt decisions. Preserve all existing nine-sector organization, authority, preservation and independent-review rules; amend the relevant sections with equivalent wording, not a second contradictory rule set:

- **Morfeo working method / observation:** "Remain the design steward after handoff. On an addressed question or intermediate evidence notice, inspect the exact current obligation and candidate, distinguish a local correction from a false premise, and provide a bounded direction or canonical design revision. Acknowledge a sound continuation without duplicating Supervisor's review. Do not wait for the final result when current evidence already invalidates the approach; do not take over implementation."
- **Supervisor communication / convergence:** "Share concrete questions and material execution evidence with the originating design steward during the contract. An existing design may be unsuitable even when no section is missing. Consume and disposition the answer against current sources; retain execution, review and integration ownership, and keep unaffected work moving. Peer advice never supplies owner authority or independent approval of coauthored changes."
- **Implementer verification / escalation:** "Before encoding a test oracle, verify that the required state or transition is possible in the actual interface. Ask a bounded, source-backed question when the agreed design contradicts that interface; continue unrelated authorized work. Record consumption and disposition of peer help without transferring writable ownership or inventing new acceptance."

Reconcile PD-77/FR-714e terminal-only wording as an owner-approved distinction between internal collaboration and human notification; preserve one board channel, three roles and owner authority. Update affected R1/R2/006 references only where necessary. Existing four canonical skills explain the exact comment lifecycle and examples. Early advice is not final result acceptance. Do not add a fourth role, another mandatory review phase or a new canonical skill merely for this objective.

### D7. Contract updates and current-objective bootstrap

Clarifications within existing accepted obligations go in the owning plan/evidence and addressed response; a material change to finalized contract terms uses `objective_contract supersede`, not an in-place edit. The request resolves with the new artifact/reference and affected work is routed through supported continuation. No requirement to auto-migrate running boards to a new contract version is added.

This objective starts on the old runtime; it does not depend on the new optional arguments to dispatch itself. Morfeo uses existing explicit board observation/comments and real `revision`/`recovery` paths during its implementation. The new opt-in becomes the default instruction for future Aether root handoffs only after installed tool support is verified. It remains optional/off for generic Hermes users and historical flows. Do not retroactively enable the stopped monitor.

### D8. Source, installation and compatibility

Implement Hermes in the provisioned maintained repository on `aether-main` with a clean task worktree at the recorded remote baseline. Preserve existing fork deltas. Do not apply a released-upstream transplant, rebase, force push, or edit the dirty live source as the candidate. Record focused delta, evidence, rollback and maintenance/retirement boundary in the existing `HERMES_LOCAL_PATCHES.md`/patch manifest if required by current distribution. Aether resource changes ship through existing profile/skill materialization; no additional loader.

Integrate and activate only reviewed commits. Reconcile the live editable bytes with the maintained candidate using the already documented PR8/HLP-362 adoption workflow, preserving unrelated installed deltas; runtime HEAD alone is insufficient. Snapshot the specific affected sources/profile resources for rollback. Verify no active workers before a required gateway reload. New/fresh sessions must load the exact new bytes; existing cached sessions are not silently rewritten or claimed upgraded. Tool schema exposure, installed bytes and model behavior are reported separately.

Additive optional comment/create arguments and a backward-compatible same-board table imply `release_impact=minor` unless final inspected compatibility evidence proves a different class. `release_action=defer`, `release_channel=none`; no version/tag/package release is requested. Idempotent migration must leave old tasks/comments/subscriptions usable. Rollback disables new opt-ins/routing and restores the reviewed preimage without deleting durable history; no destructive down-migration.

### D9. Local implementation freedom and rejected alternatives

Private helper names, SQL index factoring, fixture layout and equivalent bounded queue/lease implementation belong to Implementer; Supervisor owns unit decomposition. Shared input, binding, delivery/ack/resolution semantics and source of authority above are not worker defaults.

Rejected: SOUL-only claim of native collaboration; a second bus/inbox service; wake on every tool/heartbeat; automatic judge after a number of revisions or hours; independent Morfeo-created implementation units; treating every foreign comment as a user command; copying mutable runtime as source; a new long-lived verification laboratory. The moderate native table and optional comment metadata are chosen because existing in-memory cursors do not preserve the requested recoverable state.
