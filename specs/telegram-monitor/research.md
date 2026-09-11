# Telegram Monitor — preliminary evidence and design discussion

This file preserves source research, superseded proposals and decision rationale. Current accepted/delegated requirements live in [spec.md](spec.md) and selected architecture in [plan.md](plan.md). Research is not implementation or independent qualification evidence.

## Spec Kit reasoning reuse

The upstream source `github/spec-kit` at inspected historical revision
`bf88c9f9a82fa370c7a7257aa2b3cf10b457b65c`, `templates/spec-template.md`, was read directly:
its User Scenarios & Testing section requires independently testable user journeys,
normal/edge cases, observable functional requirements and measurable success criteria.
The current feature adopts this reasoning as concrete TM/AC obligations and a runnable
verification map, not a vendored workflow. The only procedural adaptation is the
owner's explicit delegation of pragmatic choices while absent, followed by Supervisor
receipt review rather than waiting for human answers. Spec Kit does not supply the
Aether/Telegram source-attribution or delivery mechanism; those gaps are the feature.
The current remote HEAD resolved to `86b7a01420a42b479f55296554030c8962744759`.
After raw extraction was unavailable, GitHub Contents API returned the actual files at
that revision: `templates/spec-template.md:11-37` retains testable journeys and
Given/When/Then outcomes; `templates/plan-template.md:13-56` calls for technical context,
constitution check, concrete project structure and a distinct quickstart/contracts
before tasks. These bytes were read directly rather than inferred from the historical
comparison. This design reuses those responsibilities and keeps work decomposition
with Supervisor.

## Inspected evidence

- Aether Agents revision `e9379c4712509c01f133745faaf810857b9a33a8`: `src/aether_agents/observation/brief.py:43-124` exposes project/trace/contract identity, observation timestamp, completion/runtime states, work and acceptance counters, changes and diagnostic/next-gate fields. These are structural facts; this does not establish that every requested human-readable complication/resolution narrative is already captured.
- Same revision, `src/aether_agents/observation/brief.py:151-190`: the curated view is Morfeo-only and explicitly handles unresolved projects, ambiguous traces and unreadable state. Monitoring must retain explicit identity instead of selecting the latest session.
- Same revision, `specs/002-aether-contract-observation/spec.md:19-44`: observation includes durations and actions but does not gain workflow authority; heartbeats do not prove semantic progress. `docs/capabilities.toml` registers `cli.observe` as implemented. No current full Telegram Monitor behavior was qualified by this inspection.
- Maintained Hermes fork revision `0b288979e2322c02ab42c05f1e183bb31cfa5aa9`, `cron/scheduler.py:1-8`: native due-job ticking and a file lock already exist; its module documentation describes a sixty-second gateway cadence. This is not an exact-deadline delivery guarantee. Native scheduling remains a reuse candidate; cadence, run isolation, failure recovery and precise binding require qualification before selection.
- Official Hermes documentation consulted: <https://hermes-agent.nousresearch.com/docs/user-guide/features/cron> describes persistent schedules, fresh reporting sessions, delivery and missed-fire handling. <https://hermes-agent.nousresearch.com/docs/user-guide/messaging/telegram> describes bot setup and Telegram destinations. Current online documentation is not proof that every described upstream feature is present in the inspected fork.
- Root `AGENTS.md` names the Project Canonical Skill convention, but this checkout has no `.aether/skills/` directory. Relevant native skills were loaded. The accepted R0 constitution remains unchanged.

## Proposed approach for owner review

A product-level monitor, independent of each interactive session, uses supported native scheduling and Telegram transport where qualified. At each fixed boundary it creates a bounded evidence snapshot for explicitly monitored project/session/contract identities, compares it with the previous interval, invokes Morfeo in an isolated reporting context, and delivers through a durable delivery queue. The queue records pending/sent/failed/uncertain delivery instead of pretending that every timeout can be retried with exactly-once guarantees.

The monitor would enumerate registered monitored work, not scan arbitrary project folders or read a global last-session pointer. Several sessions contributing to one contract could be grouped without being confused with independent contracts. A session without a contract retains its session identity; no contract is invented for reporting. One receiver integration owns a given bot rather than starting competing Telegram polling loops per session.

Superseded setup proposal: a new token-entry and pairing flow was initially considered. The owner subsequently selected the bot already configured in Aether and one existing Telegram conversation for every monitored objective. Reuse that configured transport and explicit destination; do not create a new bot, pairing system, or per-project chat/topic. The earlier thirty-minute cadence is also superseded by hourly cron invocation. These amendments are requirements in `spec.md`, not activation authority.

Proposed report structure: project/objective identity and time window; short overall state; work completed in this interval with evidence; work currently in progress; next planned step; complication, remedy and verification outcome; remaining blocker or owner action; honest time summary. Distinguish reported intentions from verified results, and report missing/stale evidence explicitly. Do not fabricate improvements during a quiet interval or derive scope percentage from time, heartbeat, or tool-call counts.

Proposed visible controls: connection and paired destination, monitored scope, fixed cadence and next cutoff, latest report, and failed/late delivery history. Terminal notifications, milestone-triggered messages and inbound work commands are not assumed additions.

## Hourly automatic-monitor recommendation (not yet owner-approved)

The owner accepted the message structure and changed the cadence to hourly, using the existing Aether Telegram bot and a single conversation, with project, originating session and contract in every report header. The owner is considering automatic monitoring while the pipeline works; the following mechanism remains a recommendation.

**Reuse native Hermes scheduling, not a second scheduler.** One registered hourly Morfeo cron per monitoring installation/destination can remain scheduled while automatic mode is enabled. A bounded deterministic pre-run collector reads only explicitly bound work and report-delivery state. If there is no monitored unresolved execution and no new or still-unreported activity/result, it emits the native `wakeAgent: false` gate. This skips model generation and delivery for that tick. If work is ongoing (including review, queued continuations, waits or blockers), or work ended since the previous report, it supplies a scoped evidence snapshot and permits Morfeo narration. An unchanged but ongoing objective still produces an hourly report; hash-based change-only suppression is not appropriate.

This source discovery refines the initial conversational suggestion of automatically pausing/resuming the cron on every execution transition. Keeping a cheap deterministic hourly preflight avoids creating another always-running watcher just to restart a paused cron. Manual monitor-off maps to native pause and must not be overridden by automatic activity detection. Re-enabling uses native resume; no agent has to remember to create or destroy jobs per conversation.

The new Aether-owned work is the scoped evidence collector and persistent report coverage/delivery bookkeeping, not a replacement timer, board or Telegram receiver. Do not infer active work merely from a process being alive. Do not stop at Supervisor's decomposition completion while downstream implementation/review/integration is pending. Preserve final results for the next hourly report, including objectives that start and finish between ticks; successful report delivery, not snapshot creation, determines whether a result was reported. Exclude monitor-generated sessions and cron runs from the monitored population to avoid self-reporting loops. Unknown/unreadable evidence is a diagnostic, not evidence of no work.

Recommended initial packaging: one fully attributed block per originating session/contract, delivered to the same exact configured Telegram conversation; blocks may be consolidated without losing their headers. Use the owner's originating work session, not the temporary narration session or an arbitrary worker's session. Multiple origin sessions must remain visible rather than be collapsed to a guessed origin. Sessions without a contract and independent-machine aggregation remain unresolved in `spec.md`.

Recommended hourly anchoring: wall-clock hour boundaries (`0 * * * *`) so sessions share one schedule. This remains a recommendation, not acceptance of on-the-hour timing. Generation/delivery latency is separate from the logical cutoff. A service must be running for the cron to execute; a closed TUI must not be the scheduler's lifecycle owner.

### Verified native surfaces and limits

Maintained Hermes source revision `0b288979e2322c02ab42c05f1e183bb31cfa5aa9`, inspected without executing jobs or reading credentials:

- `cron/scheduler.py:3351-3374` (`_parse_wake_gate`) and `:4462-4484` (`run_job`): a successful pre-run script whose last non-empty stdout line contains JSON `{"wakeAgent": false}` returns before agent execution and suppresses delivery. This is supported on the normal LLM-driven job path; do not select `no_agent=true` for Morfeo narration. Empty output, absent/invalid flags and failed preflight are NOT equivalent to a reliable no-work decision; specify and test explicit failure behavior.
- `cron/jobs.py:2066-2103`: native pause retains a job and disables it; resume computes the next future occurrence. This supports manual off/on without recreating jobs.
- `cron/scheduler.py:2269-2300`: delivery resolves configured targets; a TUI-created origin-only job can become local-only. Monitoring must bind the existing Telegram destination explicitly, not use this TUI's origin or a global fanout.
- `cron/scheduler.py:2305-2327`: the native sender can add a generic cron header. Meeting the owner-required project/session/contract-first presentation must be qualified without silently changing formatting of unrelated cron jobs.
- `cron/scheduler.py:6314-6336`: native ticking includes a file lock against duplicate overlapping ticks. This does not prove cross-installation singleton behavior or exactly-once Telegram delivery.

These are inspected source capabilities, not a live qualification of the monitor. The precise evidence projection, failure/retry semantics, scope subscription, clock policy and tests must be resolved in a later build-ready plan. Current Aether repository revision at this clarification is `b52afd17a93d25e31a48e5c86bd569f45f2f04d4`; the prior observation-module review above remains attributed to its actual earlier revision.

## Owner authorization and bounded denial

The owner subsequently authorized autonomous documentation, implementation and progress
reporting and delegated pragmatic design decisions. The current decisions now belong to
`spec.md` D1-D11; earlier discussion-only language and proposed token onboarding above
are historical, not current requirements. The single existing Telegram destination was
resolved through native configuration without exposing its credential. A real start notice
was accepted by the native Telegram sender; this is transport evidence, not completed
feature qualification. A separate temporary native hourly job reports only this build.

A native patch to root `AGENTS.md` initially timed out on a protected-instruction
approval prompt and was recorded against existing issue #315. The owner then explicitly
asked to present all planned protected edits before leaving. Morfeo verified that none of
the three SOUL documents requires a change for this monitor, presented the sole AGENTS
exception link, and resubmitted it through the same native guard. The guarded patch
succeeded. No alternate writer, guard/configuration change or runtime repair was used.
AGENTS, DESIGN and ROADMAP now agree with the scoped exception. No SOUL change is in scope;
monitor-specific narration belongs to the job context and packaged feature resources.

## Final native-adapter selection

The read-only sub-analyses identified exact source surfaces: project registry/marker;
final Objective Contract metadata (`created_in_session`); board metadata with portable
project/contract/version; task_runs/task_events for short-lived work; and exact native
session attribution rather than latest-session inference. `kanban_db.connect()` and
observation materialization APIs can mutate their state, so the plan selects explicit
existing-DB read-only queries and source normalization. There is no existing complete
progress narrative schema or durable contractless enrollment; those are monitor features.

Hermes `cron/executions.py:44-57` stores execution status but not positive per-message
Telegram acknowledgment. A sub-analysis proposed a new terminal delivery hook/column in
Hermes; Morfeo instead selected an Aether-owned outbox using native sender calls on the
exact successful reporting turn. `agent/turn_finalizer.py:586-603` supplies the finalized
text through `post_llm_call`; `:787-805` supplies completed/failed/interrupted turn state
through `on_session_end`. `cron/scheduler.py:4516` creates a distinct cron session, and
`:2269-2299` establishes that `deliver=local` suppresses the generic auto-send. The
chosen monitor job therefore uses local ordinary delivery plus a scoped deterministic
Aether callback to the native Telegram sender, preserving exact positive receipts and
avoiding duplicate auto-delivery. Source-reference/run binding, failure recovery and
receipt edge cases remain mandatory qualification, not source-inspection proof.

The proposed Desktop-tab path is deliberately not selected: owner-delegated pragmatic
scope chooses a CLI section and native TUI control tool. All SOUL identities remain
unchanged. This design needs no new framework hook or fork mutation. Shared private data
shapes are fixed in plan.md; Supervisor still owns the independently reviewed work units.

## Limits and follow-up boundary

Graph and work-memory navigation returned `VIEW_MISMATCH` because the native session workspace was not a reachable checkout. Direct inspection of the verified repository was used; no substitute graph, profile edit or runtime repair was attempted. This is a navigation limitation, not evidence of Telegram Monitor feasibility or a proven new product defect.

The current review has not run code, live Telegram delivery, scheduler timing measurements, model generation, or the future test standard. Implementation belongs to Supervisor/Implementer after material decisions and a finalized project-bound Objective Contract: meaningful independent review should catch cross-project data leakage, cadence drift, incomplete recovery and interference with active conversations.
