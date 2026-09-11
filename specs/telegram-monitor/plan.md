# Telegram Monitor — selected technical design

**Owner:** Morfeo under TM-007. **Scope/test authority:** [spec.md](spec.md).
This is the material design for one Objective Contract, not an implementation breakdown.
Supervisor chooses testable units and dependency ownership after receipt review.

## 1. Foundation and explicit choices

Python follows existing `pyproject.toml` (3.11–3.13); standard library SQLite/JSON and
existing Aether privacy/path helpers suffice. Reuse native Hermes cron, SessionDB,
Projects, execution boards, plugin hooks and Telegram sender. Do not modify the Hermes
fork for this feature: its mutable checkout is an inspected integration target, not a
permission to change the release baseline. Fail a capability preflight if the deployed
native interfaces differ materially, rather than monkey-patching or replacing them.

The sub-analysis proposed adding a durable Hermes cron delivery hook/column. Morfeo
rejects that larger cross-repository change for this objective. Native cron delivery
bookkeeping does not persist a positive per-message acknowledgment and can treat an
in-flight timeout as assumed delivered. Instead the Aether plugin owns a small report
outbox and calls the existing native Telegram sender at the reporting turn's verified
end. The cron's ordinary auto-delivery is `local` to avoid sending twice. This does not
replace scheduling, inference, credentials or transport: it retains real sender receipts
at the one location that owns report coverage. A local cron result is NOT a Telegram
receipt. Failure/unknown status must survive the plugin callback returning.

No SOUL source or installed SOUL changes are necessary. Monitor instructions are a
packaged English reporting context; output language follows owner configuration (Spanish
for the currently authorized installation). Existing role authority is unchanged.

## 2. Product components and interfaces

Add a cohesive `src/aether_agents/monitor/` package. Required responsibilities (private
file/class splitting remains Implementer freedom):

- `store`: private monitor SQLite database, settings/enrollment/watermarks/snapshots/
  narratives/outbox, transactions, lease/duplicate fencing and retention.
- `sources`: strictly read-only normalized adapters to registry/marker, contract metadata,
  bound execution boards, persisted observation summaries and exact native session data.
- `collector`: hourly-window reconciliation and bounded snapshot construction; no LLM.
- `reporting`: packaged prompt, strict model-result validation, deterministic identity
  headers, plain-text Telegram splitting and evidence labels.
- `delivery`: destination verification, per-part native sender invocation, durable outcome
  recording and safe retry decisions. No new Telegram Bot polling instance.
- `hermes_plugin`: native hooks and tools, exact reporter-run recognition and turn capture.
- `commands`: `aether monitor` control/read commands delegating to the same service as the
  native TUI control tool. A product runtime subprocess boundary may be used where the
  manager interpreter lacks Hermes; do not install Hermes into the manager as a new dep.

Package one pre-run script resource and one narration-context resource. The installed
script resolves product paths using the existing installation boundary, not a checkout
hardcode. Register exactly one new plugin entry point under the existing package plugin
scheme and reconcile known entry-point validation/activation surfaces. Use supported
scoped profile plugin enablement on activation; do not overwrite unrelated settings or
SOUL files. Read the actual activation path before using it and retain a rollback diff.

### Public CLI and tool shapes

`aether monitor status [--json]`, `on [--json]`, `off [--json]`, and
`history [--limit N] [--json]` are required. No credential parameters. `on` resolves and
pins the existing native Telegram home chat/thread (never `origin`/`all`); it validates
that the runtime is Morfeo's provisioned Aether runtime and registers/reuses the one owned
job. Missing/changed/ambiguous destination returns a clear configuration error without
sending elsewhere or acquiring credentials. `off` persists off before pausing its job,
so a racing precheck/send rechecks it and stops. On/off never touch another job. Status
includes enabled state, native job state, next cut, source coverage gaps, last report and
per-delivery outcomes. History is paginated and excludes source raw content/credentials.

Native `aether_monitor` control tool accepts the same four actions and limit, available
only in ordinary Morfeo sessions. Reporter sessions get only a separate
`aether_monitor_report_snapshot` read tool in dedicated reporting toolset
`aether_monitor_reporting`; exclude terminal, files, messaging, board lifecycle,
delegation, cron and control tools from narration. Verify actual loaded tool definitions;
an empty toolset list that expands to defaults is not a restriction.

JSON responses use `schema_version: aether.telegram-monitor.v1`, `ok`, `action`, and an
`error:{code,message}` or `result` object. Preserve identifiers as exact strings. Public
monitor configuration is installation-local, never supplied by report-source text.

## 3. Persistent model and concurrency

Use `<Aether state_root>/monitor/monitor.sqlite3`, root 0700/database 0600 using existing
safe path primitives. No source DB is migrated. Persist:

- **settings** singleton: schema version, enabled, exact native job ID/profile binding,
  private pinned destination reference, first enabled time, timezone, last cutoff.
- **work_items**: stable work key; verified project UUID; origin native session identity;
  optional contract ID/version and verified local board binding; first seen/start/end;
  current observed lifecycle state; source cursor; final-outcome delivery marker.
- **snapshots**: immutable `report_id`, UTC cutoff, previous cutoff, collection time,
  per-source evidence watermarks, bounded snapshot JSON, coverage gaps and digest.
- **narratives**: report ID, validated structured result, native narrator session identity,
  attempt status; no credential or complete source conversation persisted.
- **deliveries**: report ID/part index, text hash, state `pending|sending|confirmed|failed|
  uncertain|suppressed`, attempts/timestamps, sanitized error class and message receipt.

These are monitor records, not a parallel execution-state authority. Use unique report
cutoff/key and part constraints plus short transaction/lease fencing so concurrent CLI,
callbacks and cron cannot duplicate collection/send. Do not hold source locks or a DB
write lock across LLM/network calls. A crash after network dispatch but before local
receipt commit leaves `uncertain`; do not assert sent or retry blindly. Track the exact
owner process/session for liveness and respect manual-off after lock acquisition.

Retain thirty days of resolved monitor history. Never purge pending/uncertain deliveries,
active attribution or any source history. Paths/JSON/types/size bounds are validated before
use; invalid data cannot redirect files, commands, source DB selection or recipients.

## 4. Enrollment and sources

Enumerate Aether `ProjectRegistry` and verify every marker/path; never a global last-project
pointer. Enumerate native board metadata read-only, requiring consistent portable project,
contract/version, canonical board grammar, Hermes project/path binding and finalized
contract. Do not create a board or call `prepare_handoff` during monitoring. Never call
`kanban_db.connect()` for source reading: it can create/migrate. Open existing files with
SQLite URI `mode=ro`, `PRAGMA query_only=ON`, bounded timeout and explicit select columns.
The same rule applies to SessionDB and observation projections; avoid `ReadModel.open()`
or `query.load_summary()` if they materialize state. Read validated persisted summaries.

Read open tasks plus task_runs/task_events since the durable watermark. `Task.session_id`
is creator/origin context, not necessarily a worker session. Prefer canonical contract
`created_in_session`/verified origin correlation for the source header. Worker evidence
may use exact `worker_session_id` metadata or affinity binding after verification of
source/profile/workspace. Read source session titles only by exact ID; title is display,
never identity. Validate authored-vs-finalized origin explicitly, do not pick by recency.

New work is auto-enrolled; first enable includes already open work but sets an initial
cursor that avoids replaying already completed historical flows. Once enrolled, terminal
changes between ticks remain pending until confirmed reporting. Root completion is not
closure: follow the exact board's downstream review/integration flow, using the native
terminal-affinity designation where present plus absence of outstanding required work.
Ambiguous closure remains `unknown/waiting` with a coverage diagnostic, not silently done.

### Direct Morfeo work without a contract

Use native turn callbacks with an exact native session/project binding (not a profile
name or unverified cwd). `post_tool_call` enrolls actual project-bound operational work;
`post_llm_call` supplies a bounded reported outcome; `on_session_end` marks a turn-ended
interval with completed/failed/interrupted/unknown flags. Source `on_session_end` fires
per conversation turn, not necessarily chat closure: name the state **turn ended**, not
project accepted. A session continuation opens a new interval; historical idle chats do
not create perpetual work. Exclude cron/report sessions, gateway service events and
nonproject conversational traffic. Existing active direct turns may be recovered from
exact bound runtime activity; if no safe live signal exists, explicitly show a coverage
gap rather than inventing activity or polling all transcripts. Do not require SOUL edits
or a model to remember to enroll itself.

## 5. Snapshot and narrative data contract

Snapshot shape:

```text
schema_version: aether.telegram-monitor.snapshot.v1
report_id, cutoff_utc, collected_at_utc, previous_cutoff_utc
items[]:
  work_key
  project: {id, name}
  origin_session: {id, title}
  contract: {id, version, title} | null
  observed_state, state_evidence_refs[], started_at_utc?, ended_at_utc?
  resolved[], current[], next[], complications[], pending[]
  coverage_gaps[]
coverage_gaps[]
```

Every narrative fact candidate carries `{ref, text, provenance, status}`; provenance is
`observed` or `reported`, status may be `verified|unverified|unknown`. Complications may
link remedy and verification refs but a mere fix claim is not resolved. `next` can be a
planned gate, never presented as executed. Keep counters distinct from progress.
Source selection allows task titles, bounded successful-run summaries, acceptance/test
metadata, known diagnostic codes and selectively redacted exact-session outcome excerpts.
Never raw transcripts, reasoning, tool arguments/results, auth objects or entire logs.
The observer privacy schema remains metadata-only; do not weaken it to store narratives.
Narrative excerpts live in the separate monitor boundary with validation/redaction.

Cap each prose item to 600 characters, source excerpts to 1,200 characters, and the total
model snapshot to 24,000 characters. Include every active work identity; if detailed
content cannot fit, emit count/coverage notices and compact item states, with deterministic
ordering, not silent omission. No live source text can instruct tool access, execution,
recipient selection or model behavior. Test seeded secret/token/path/PII canaries in
selected source fields; redact before snapshot persistence/model input. Reject malformed
or unsafe source fields and report a coverage gap. Existing Aether privacy patterns are
reusable, but arbitrary secret discovery is not guaranteed by a regex—avoid unnecessary
content at source and test the actual allowlisted fields.

Morfeo returns one JSON narrative envelope with `schema_version`, exact `report_id` and
`items:[{work_key,resolved[],current[],next[],complications[],pending[],status}]`. Each
claim references known source refs and the model cannot supply project/chat/session
headers. Validation rejects unknown items/refs, mixed identities, fabricated structured
completion and malformed output; preserve pending state, never turn rejected text into
an official report. `spec.md` D12 owns the precise distinction: typed lifecycle/status
validation is deterministic; arbitrary prose semantics is not certified with regex.
Keep the existing snapshot/narrative shapes. A model status must match the source's
canonical whole-work state (or the deterministic unknown mapping), never a prose synonym.
References and provenance cannot be upgraded by a sentence; all linked refs remain within
the source work item and compatible section. Reported/unverified content receives an
unverified/reporting label computed from source, not a model-supplied verification claim.
No natural-language semantic classifier, synonym denylist or verbatim-only narrative is
part of the contract. Seeded privacy/identity/shape validation remains mandatory.
Prompt guidance and representative actual model qualification own faithful paraphrase,
contradictory-source handling and no fabricated completion/time/percentage statements.
Renderer adds immutable identity/time headers and evidence labels,
then the accepted Spanish/owner-language section structure. Mark no evidence explicitly.
Plain-text splitting uses <=3,500 Unicode characters per Telegram part (leave header
headroom) and repeats identity for continued items, with report/part order markers. One
narration produces all parts; splitting never calls the model again.

## 6. Native job lifecycle and qualified delivery boundary

Create one ordinary `no_agent=False` native job with `schedule=0 * * * *`, the packaged
precheck script, bounded narrator context, dedicated reporting toolset and `deliver=local`.
No `monitor_script` or `monitor_url`: those suppress unchanged output and violate cadence.
No automatic dedicated chat/thread (`attach_to_session=false`). Persist the actual job ID,
not name matching as runtime authority. Manual invocations and cron cutoffs carry separate
attempt identities; a test cannot accidentally trigger every user's cron.

The successful precheck reconciles recoverable monitor state, validates enabled status,
binding and feature-hook readiness, and emits the snapshot plus final JSON wake gate.
It wakes for ongoing work, unreported final outcomes or source failure. Genuine idle emits
`{"wakeAgent":false}`. Failures are observable monitor errors, never idle. Native scheduler
owns the timer/claims/agent execution; no permanent monitor loop, nested job or daemon.

For the exact monitor cron session (native cron source, actual persisted owned job ID,
profile and pending snapshot lease must all match), `post_llm_call` validates and persists
the narrative; it neither claims delivery nor starts another model. `on_session_end`
checks completed/failed/interrupted and the exact pending record. A successful bounded
reporting turn commits outbox parts then calls the existing native sender through an
isolated delivery adapter using the pinned configured Telegram target. `deliver=local`
ensures native cron does not also send. Every other agent session's hooks only record
source evidence, never sends a report or transforms its response. If callback invocation
fails or process dies, the next precheck sees a pending/unknown report and surfaces it.

Do not infer the narrator's identity just from a guessed timestamp: verify native cron
session/source and the job-specific leased report context. The imported runtime creates
`cron_<job_id>_<timestamp>` in `cron/scheduler.py:4516` but this is corroboration, not a
replacement for explicit state binding. Handle session continuation/rotation by exact
native lineage where available; otherwise fail the reporter match safely.

Sender interface returns `{outcome,message_id?,error_class?}` per part. Only an explicit
successful native Telegram response with message ID is `confirmed` (Bot API acceptance,
not human receipt). Empty/no-success/timeout after dispatch is `uncertain`. A documented
failure before dispatch is retryable; honor retry-after, at most three bounded transport
attempts per part per reporting tick. Do not retry ambiguous partial network execution.
Reuse `_send_to_platform` or the qualified native platform sender behind a single tested
adapter rather than `_deliver_result`'s coarse None/string acknowledgment. Do not widen
native retry behavior silently; test ambiguous timeout with the actual selected sender.

Advance each work item's reported watermark/final marker only when all covering parts
are confirmed. Failed parts remain pending for a later tick. An uncertain part remains
visible in status/history and the next report; exclude ambiguous automatic replay.
A source final result is not silently forgotten merely because an LLM completed.

When narration fails or cannot match the report, persist `narration_failed` and a small
labeled service notice through the same outbox on this/next check. A fallback notice is
not reported-progress coverage and never marks final work reported. Source collection
failure is similarly a labeled service condition. Prevent more than one service notice
per affected report cut. Manual off blocks both narrative and retry delivery.

## 7. Packaging, activation and ownership boundaries

### D13: separate qualification from production activation

The owner-approved [qualification-isolation.md](qualification-isolation.md) defines the
remaining live path and preserved previous revisions. It replaces shared-registry
substitution with a private native scheduler-only laboratory, preserving the production
installation. Exactly one initial smoke, two active native hourly cuts and a following
native idle cut prove laboratory behavior. Independently verify the same candidate's
first hourly report on the existing production gateway before terminal acceptance.
A second temporary native scheduler instance is allowed only inside this private lab;
no second service/receiver/dispatcher or custom scheduling engine is authorized.
Retain private test evidence and stop the runner; do not self-delete or restore the
production registry. This is v2's explicit qualification/authority revision, not a
reason to omit remaining functional or privacy acceptance. Keep approved MON-01..05
and reviewed test corrections; Supervisor owns continuation of the unfinished work.

### D14: resolve the actual provisioned profile before live spending

Accept both the multi-profile-root and exact Morfeo-profile `HERMES_HOME` conventions,
normalizing either to one verified profile without using cwd/current worker identity.
Build the provisioned destination reference by running Hermes' native dotenv loader in a
restricted child rooted at that exact profile, then load gateway configuration and return
only a bounded digest/presence projection. Keep the lab's access in memory and require its
independently resolved destination/route to match that reference. Do not inject the lab
access into the reference probe, persist credentials, or add credential/destination CLI
inputs. The recorded no-effect `lab-config` refusal precedes the experiment boundary;
after this correction and review, one explicit corrected live attempt remains authorized.

Document `docs/guides/telegram-monitor.md`, relevant CLI/plugin references, and
`docs/capabilities.toml` plus generated reference. Keep status claims at observed capability
level only. Reconcile the workflow's **literal** tracked-file/entry-point allowlists with
exact new paths; never glob out or relax a check. Add package resources through existing
build conventions and verify an installed disposable wheel. Do not silently assume a new
entry point loaded in an already-running process.

After integrated verification, use the existing safe runtime installation/plugin lifecycle
to expose the monitor to the authorized installation. Do not kill active agents. If a
safe graceful reload cannot be established, preserve candidate and report activation as
blocked rather than killing work or announcing live success. Keep the old temporary build
reporter until one native monitor report covers this objective; then list and verify the
known temporary job before pausing/removing it. Local job IDs/private destination remain
in private operational handoff state, not this portable plan.

## 8. Verification and implementation freedom

[quickstart.md](quickstart.md) supplies executable gates and AC coverage. Independent review
must inspect identity/source-DB read-only behavior, no recursion/extra tool authority,
state/send races and exact positive receipt handling. A green source test does not prove
live activation. Require two native real-hour cuts and direct+pipeline/multiproject cases,
plus live idle/no-inference; no fabricated timestamps or forced ticks as substitutes.

Implementers choose private helper names, equivalent SQL/index shapes, fixture organization
and reversible local organization. They cannot add a fourth role, alter cadence, choose a
new recipient/provider, change public CLI/tool/data shapes, omit direct tracking/final
retention, convert source work into monitor-owned authority, or edit SOUL files. Supervisor
owns decomposition, same-card independent review where applicable, integration and normal
closeout. Morfeo's source design and self-check are not a claimed independent receipt.
