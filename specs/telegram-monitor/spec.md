# Telegram Monitor — autonomous hourly progress

**Status:** requirements resolved under owner-delegated pragmatic design; implementation and qualification pending.
**Authority:** the owner explicitly authorized autonomous documentation, implementation and progress reporting through the existing Telegram while unavailable. Morfeo resolves the remaining reversible design decisions; Supervisor owns decomposition, independent review and normal pipeline closeout. This is a scoped exception to the feature freeze for this objective only, not a waiver of the reliability/release gates.
**Tracking:** [issue #367](https://github.com/DarkArty07/Aether-Agents/issues/367).
**Canonical foundation:** existing R0 constitution, DESIGN.md three roles/PD-70 observation, specification 002, and qualified native Hermes scheduling/messaging. No constitutional principle is added or changed.

## Owner-confirmed requirements

- **TM-001 — Product surface:** a dedicated Telegram Monitor section is a principal Aether capability for long-horizon work.
- **TM-002 — Narrative:** Morfeo writes the accepted structure: resolved, current work, next step, complications/remedies and their verification, pending/blockers/owner action, and objective/milestone status. Evidence and reported intentions remain distinguishable.
- **TM-003 — Existing destination:** use the bot and single Telegram conversation already configured in Aether. No new bot, token onboarding, polling receiver, per-project conversation, topic or thread is introduced.
- **TM-004 — Multiproject:** support concurrent Aether sessions in different projects/contracts, independently of the focused TUI or most recent session.
- **TM-005 — Hourly trigger:** start the reporting cycle once per hour, not per milestone or detected change. Every interval is reportable while tracked work remains; no-change suppression must not conceal a wait or stall. This supersedes the earlier thirty-minute requirement.
- **TM-006 — Identity first:** each report/block begins with project name plus portable identity, originating work-session title plus a short native identifier, and contract title plus identifier/version. The narrator's cron session never substitutes for the originating session. All reports go to the same bound conversation. Direct work explicitly says no contract; ambiguity is not guessed.
- **TM-007 — Autonomous delivery:** the current instruction authorizes pragmatic remaining decisions, autonomous build/test/integration, and real progress reports through provisioned access while the owner is absent. Do not repeatedly wait for a design preference that has a safe, reversible resolution.

## Delegated design decisions and assumptions

These choices are Morfeo's decisions under TM-007, not inferred preferences or a change to the constitution.

- **D1 — Native mechanism:** one native Hermes recurring cron per installation's Morfeo monitor and exact configured Telegram destination. A successful deterministic pre-check uses the supported `wakeAgent: false` gate only when there is neither ongoing tracked work nor an unreported result. Otherwise it supplies a bounded evidence snapshot for Morfeo. Keep the recurring job registered; do not require another watcher to resume a paused job. Assumption: the inspected native gate/delivery/persistence qualify on the activated Hermes revision; verify before activation, do not silently replace the scheduler.
- **D2 — Calendar:** common wall-clock hours (`0 * * * *`) using the installation's existing timezone, with UTC cutoffs and explicit local offsets in records. Resuming monitoring schedules the next future boundary; no burst of invented missed snapshots. A healthy scheduler begins collection within 120 seconds of the boundary, and ordinary healthy narration/delivery targets completion within ten minutes. Late intervals remain visible, not silently discarded. These are delegated operational acceptance limits, not guarantees of network delivery.
- **D3 — Scope:** one installation initially, all exactly registered reachable Aether projects and their bound active execution flows, plus direct Morfeo project-bound work observed by native lifecycle callbacks. Do not scan arbitrary directories, use a latest-session pointer, or collect unrelated generic chats. Previously started flows still open when the monitor is enabled are included; already completed historical work before first enablement is not replayed. Direct work has no invented contract. Cross-machine aggregation is out of scope.
- **D4 — Lifecycle:** follow an executing flow through queued work, review, waits, blocked states and final authoritative resolution, not just while worker PIDs exist. Root decomposition `done` is not overall closure. Capture final results even when work starts and finishes between hourly ticks. After the final report is durably accepted for delivery and no other work remains, future checks are silent without model inference. Native direct-session lifecycle marks its observed work interval; an idle conversation does not remain perpetually active. Never count the reporting run as work to report.
- **D5 — Controls:** pragmatic first product surface is an `aether monitor` CLI section with status/on/off/history and a matching native Morfeo tool for TUI control. No new Desktop/web frontend. `on` means automatic; `off` pauses the monitor's cron persistently and must not be undone by agent activity/restart. On/off must be idempotent and leave other jobs untouched. Installation of code does not auto-enroll a different user's installation; the current owner explicitly authorized activating this installation.
- **D6 — Packaging/interaction:** one hourly digest with a distinct identity header per source work item; split over Telegram's size limit into ordered parts, repeating source identity as needed. Outbound information only. Existing unrelated interactive Telegram behavior is preserved, but this feature adds no reply-to-source dispatch or remote work-control command.
- **D7 — Time/percentage:** report the actual observation period and attributable elapsed time when known, with pending/unknown labels for unavailable values. Do not claim active CPU/agent hours, budgets, forecast completion or overall percentages. Milestone completion requires existing acceptance evidence; no second milestone workflow is added.
- **D8 — Degradation:** explicitly label unavailable/stale source data and unresolved complications. Collection failure is not idle. Preserve pending reports on failure; retry definitive non-delivery in a bounded manner through qualified native transport. If model narration fails, a fixed minimal service-error notice may explain that Morfeo's report is unavailable; never pass a deterministic technical summary off as Morfeo's narrative. Telegram acknowledgment uncertainty is recorded as uncertain, not as exactly-once success or a reason to spam retries. Never send to an alternative destination as a fallback.
- **D9 — Inference/access:** use only Morfeo's already provisioned configured model route and fallback policy, with no provider/model rebinding, credential acquisition/widening or new paid service. At most one normal narration execution per hourly digest (message splitting is not additional inference); respect existing runtime bounds and do not create recursive reporting jobs. Qualification may perform a bounded live smoke using the same provisioned route and destination. Unexpected new expense or access requirement is a protected blocker, not a delegated design choice.
- **D10 — Closeout:** implement on native isolated workspaces; preserve all preexisting branches/worktrees/stashes/jobs and concurrent remediation work. Scope includes normal authorized commit/push/PR/checks/review/merge and reversible local activation of this monitor after verification, using existing access and safe native lifecycle. No restart that kills active work. Package publication, deployment, infrastructure migration and unrelated runtime/profile changes remain out of scope. Expected compatibility impact is minor (additive public capability), release action defer, channel none; evidence must confirm these separate conclusions.
- **D11 — Retention:** own operational snapshot/report history is bounded to thirty days by default; unsent/uncertain reports and ongoing-work attribution are retained until resolved. Raw source SessionDB/Kanban/observation data is never purged or rewritten by the monitor. This is monitor-owned cache retention, not a replacement project history policy.

### D12 — Clarified division between structured facts and Morfeo prose

Under the owner's renewed instruction to resolve the objective autonomously, Morfeo
clarifies the existing `fabricated structured completion` requirement (plan §5). This
corrects the implementation's unbounded semantic-parser interpretation; it does not
change report cadence, identity, data shape, authority, privacy or independent review.

The deterministic boundary owns exact project/session/contract/report/ref binding,
canonical observed lifecycle and timestamps, source provenance/verification labels,
length/shape/privacy limits, recipient and delivery receipts. A model-controlled status
must agree with canonical observed state; readiness, a test passing or a report saying
`finished` can never change whole-flow completion. Renderer-owned time/state headers are
not model prose. Unknown/mixed refs and malformed/unsafe content still fail closed.

Morfeo owns explaining selected evidence faithfully, including qualifications and
contradictions. Source `reported/unverified` text is data, not an authority or an
instruction. A matching reference proves attribution, not truth or semantic entailment.
The prompt must prefer canonical state over worker claims, not elevate unverified
statements to verified resolution, not invent time/percentages/deadlines, and preserve
legitimate partial success with pending review. Output retains deterministic provenance
labels and an authoritative state header. A diagnostic stays diagnostic, not an action.

No regex, vocabulary expansion, exact-text requirement or second model/classifier is
required or accepted as universal certification of arbitrary natural-language meaning.
Remove semantic synonym/status-word guessing as the prose gate; keep typed lifecycle,
reference, section/provenance, syntax, bounds and privacy validation. Do not remove secret
or cross-identity checks while removing semantic completion/forecast/time guessing.
Free paraphrase within the requested sections remains Morfeo's task; template-only
messages or verbatim-worker-output substitution do not satisfy it.

AC-5's actual narrative fidelity is verified by representative provisioned Morfeo runs
with contradictory worker claims, partial test success plus pending review, blocked/no
change, missing evidence, Spanish/English phrasing and malicious source instructions.
A wrong emitted claim is a real failure of that observed qualification case, not a reason
to demand a universal prose theorem or expand an endless denylist. Preserve and reclassify
historical adversarial examples as semantic prompt/live quality cases, and keep structural
and privacy regressions executable and green. No claim of perfect hallucination detection
is permitted. Changes to verification allocation are explicit here, never silently weakened.

### D13 — Owner-approved isolated qualification and real activation

The owner approved the presented laboratory design and renewed handoff to Supervisor.
[qualification-isolation.md](qualification-isolation.md) owns the exact bootstrap,
source/scenario, scheduler, receipt, shutdown, retention and continuation design.
The single production monitor and D3 installation-wide scope are unchanged. Explicitly
permit one temporary scheduler-only native instance with isolated HOME/HERMES_HOME/XDG
state for qualification; no second receiver, permanent service or custom scheduler.
Never swap or restore the real registry. Use existing access ephemerally without new
credential copies. Qualify one smoke, two active real hourly cuts and a subsequent real
idle cut in the lab; then independently verify the same candidate's first normal hourly
report on the existing production gateway. Keep private lab evidence through closure
instead of self-deleting it. No active-agent interruption or relaxed acceptance.
This explicit method/authority amendment supersedes v1's blanket second-scheduler ban
only for the isolated bounded test, and requires Objective Contract v2. Preserve the
reviewed code/commits; Supervisor owns the remaining continuation and its review.

### D16 — Accelerated lab boundaries and one real production hour

The owner replaced the disproportionate multi-hour laboratory wait. The private lab uses
the native scheduler on `* * * * *` for two active and one idle real minute boundaries;
production remains exactly `0 * * * *` and supplies one natural hourly execution after
activation. No system-clock mutation, fake scheduler, manual tick evidence or production
cadence change is allowed. Lab receipts label the accelerated expression/timestamps and
cannot claim elapsed-hour evidence. Deterministic schedule/DST/restart controls plus the
single production cut preserve the original hourly product oracle. Objective Contract v4
supersedes v3 for this testing-standard change.

## Acceptance criteria

| ID | Observable outcome |
| --- | --- |
| AC-1 | `aether monitor status/on/off/history` and the Morfeo tool expose the same monitor state; repeated on creates no duplicate job; off persists through restart/activity and changes no unrelated job. Missing existing destination fails explicitly without requesting a new credential. |
| AC-2 | Two real scheduled hourly boundaries produce corresponding interval records and reports while work remains; collection starts within 120 seconds in a healthy local runtime. An unchanged/blocked interval still invokes narration, idle with no unreported outcome does not. Model/Telegram lateness is distinct from cutoff time. |
| AC-3 | Concurrent work in two exactly bound projects, at least two origin sessions, multiple contracts and a direct no-contract session is attributed correctly. No focused-project, default-board or narrator-session substitution and no unapproved destination/topic occurs. |
| AC-4 | Review/wait/block states remain tracked; root decomposition completion does not close the flow; a short job completed between ticks receives one final report and subsequently becomes idle. Monitoring does not modify work or mark acceptance complete. |
| AC-5 | Actual Morfeo-generated text follows TM-002/TM-006, distinguishes verified results from reported work, and includes genuine complications/remedies only when supported. Missing evidence is explicit; no percentages or false time accounting. Sensitive test canaries do not leak into snapshots, prompts, reports or published evidence. |
| AC-6 | Native cron duplicate registration, concurrent invocations, restart, malformed/stale evidence, narration failure, explicit send failure, ambiguous acknowledgment and split-message partial failure have the specified durable outcomes. No silent lost final report, unbounded retry, narrator recursion, alternative recipient, or promised exactly-once guarantee. |
| AC-7 | A live, consented test through the provisioned route produces real Telegram message identifiers; source identity and report period agree with the runtime facts. Bot API acceptance is labeled as such and never as proof that the human read the message. A real hourly run and a no-work skip are evidenced; forced/manual runs alone are insufficient. |
| AC-8 | Packaged entry points/resources, plugin allowlist, CLI/tool contracts, capability registry and user guide agree. Existing observation, cron delivery and Telegram interaction regressions pass; docs/artifact checks and repository quality gates pass without weakening them. |
| AC-9 | Independent Supervisor review and integrated tests precede scoped activation and normal GitHub closeout. After native monitor delivery is verified, retire the temporary build reporter by its verified identity, or record a precise remaining blocker. Audit objective-owned residue separately from preserved preexisting work; record rollback and all three release conclusions. |

## Testing standard and owning design

Under delegated authority, use behavior-focused regression tests, deterministic controlled-clock/concurrency/fault tests, the repository's existing quality/coverage gates and live provisioned Telegram/model qualification. No blanket test-first mandate is added. The material interfaces, state and recovery design belong to [plan.md](plan.md); exact commands and acceptance-to-evidence mapping belong to [quickstart.md](quickstart.md). These artifacts must exist and be committed before the finalized Objective Contract is handed off. Self-review and structural validation are not independent receipt review.

## Preservation and exclusions

Retain the three roles. A reporting execution of Morfeo is not a fourth role. Reporting is read-only with respect to source work: it cannot advance tasks, accept milestones, repair blockers or change a contract. Its own enrollment/report/cursor records and the identified monitor cron may change under the product controls. Do not expose credentials, raw transcripts, user identifiers, machine paths or private provider bindings in public artifacts. Avoid unrelated cleanup. Except for D13's isolated bounded native scheduler instance, no new bot, scheduler daemon, Telegram poller, Desktop frontend, cross-machine collector, percentage engine, time-billing service, inbound command router, provider or package release is included. The owner requested up-front review of protected identity edits; all three SOUL sources were inspected and require no modification. They and installed SOUL copies remain outside scope. The sole protected AGENTS exception link was applied through its normal guard after that explicit owner instruction.

### D14 — Provisioned-profile and destination resolution

The owner-authorized continuation accepts both actual Hermes `HERMES_HOME` conventions:
the multi-profile installation root and the exact named Morfeo profile home. The harness
must normalize either to the same verified Morfeo profile and reject ambiguity. Its
reference destination probe loads that profile's provisioned dotenv through Hermes'
native loader, emits only bounded digests/presence, and makes no model/send call. Lab
children receive only already-provisioned access in ephemeral memory and must resolve an
identical destination/route. No credential value is copied or accepted as CLI input.
The preserved preflight refusal consumed no live budget; one corrected attempt is allowed
after independent review, and a later live failure stops normally.

Objective Contract `oc_f8c9fc9320587cf3@v4` supersedes v3 with D16 at `.aether/objective-contracts/oc_f8c9fc9320587cf3/v4.md`; immutable v1/v2/v3 remain preserved. This is executable design and authority, not implementation or qualification success. Supervisor receipt review and execution are separate evidence.
