# Aether Contract Observation Specification

**Feature**: Aether Contract Observation
**Feature ID**: 002
**Status**: owner-approved full-lifecycle design baseline, strengthened against the release-locked Hermes runtime; implementation candidate under validation, controlled real-trace/release qualification pending
**Decision date**: 2026-08-21
**Runtime-evidence amendment**: 2026-08-22
**Full-lifecycle scope amendment**: 2026-08-22
**Owner authority**: Christopher
**Contract architect**: Morfeo
**Implementation recipient**: Supervisor
**Source issue**: [#195](https://github.com/DarkArty07/aether-agents/issues/195)
**Release relationship**: required before Aether Agents `1.0.0`

---

## 1. Purpose

Aether MUST make contract work inspectable without turning Kanban, SessionDB, logs, or model prose into a second execution authority. For each observed contract, the product MUST reconstruct and summarize:

1. the complete duration from the owner's originating message through the contract's authoritative terminal resolution;
2. the actions performed and the participants responsible for them;
3. the tools used and exact totals;
4. the real flow, including useful iterations, technical retries, semantic loops, regressions, and reversions;
5. the causal process by which the contract was developed: ordered semantic steps, parallel deployment waves, execution/rework rounds, agents and work units deployed in each wave, barriers, and critical-path evidence needed to audit whether more concurrency or a different sequence could materially accelerate delivery.

A second purpose is explicit: the recorded evidence MUST be sufficient to later decide, from comparable traces rather than impression, whether to grant or withdraw tools, strengthen prompt/skill engineering, change a model, or change pipeline topology. The observer supplies that evidence; it never makes, recommends, or applies such a change.

The first release is a local, metadata-only observer. It records observable actions and artifact transitions; it MUST NOT record or expose private chain-of-thought.

## 2. Constitutional alignment and authority

This feature preserves the current project constitution:

- Hermes remains the execution substrate.
- Kanban remains authoritative for task lifecycle, dependencies, retries, liveness, and completion.
- SessionDB remains authoritative for persisted conversation messages and tool-call/result records that it already owns.
- Canonical project artifacts remain authoritative for contract content and accepted decisions.
- Aether's observer owns only its local append-only observation journal, optional bounded semantic checkpoints, and deterministic derived summaries.
- No observer result may activate work, complete a task, change a gate, approve an effect, alter credentials, or override the owner.
- Owner decisions supersede inferred classifications. A changed owner decision is not a regression when the supersession is explicitly linked.
- Heartbeats prove liveness only. They never prove semantic progress.

The observer is therefore a read model plus Aether-owned contract metadata, not a parallel workflow engine or audit authority.

## 3. Scope

### 3.1 In scope for 1.0.0

- Contract traces logically beginning at an exactly linked owner message when available and materialized only by an authoritative objective/contract/root binding.
- Contract creation through canonical persistence, with creation duration preserved as its own phase.
- Handoff to Supervisor, decomposition, implementation, required review/QA/integration, acceptance verification, and authoritative terminal resolution.
- The complete causally bound Kanban task/run graph, including resumptions, redispatches, recoverable blocks, crashes, timeouts, review returns, and final completion.
- Deterministic reconstruction of semantic process steps, dependency barriers, parallel execution waves, execution/rework rounds, deployed participants/work units, and critical-path/queue/wait evidence. Aggregate totals alone are insufficient.
- Improvement-decision capture: field-covered per-trace/per-participant configuration fingerprints, observed tool/skill use, effective granted/never-used inventory only when the source snapshot is complete, model/context economics, sampled bottleneck attribution, and bounded defect attribution with explicit provenance.
- Participants: owner, Morfeo, bounded subagents, Supervisor, Implementers, reviewers, and any other explicitly bound profile.
- Typed native lifecycle facts, model/tool spans available through public Hermes hooks, canonical artifact revisions, optional semantic checkpoints, and evidence references.
- Deterministic duration, participant, tool-usage, coverage, and flow summaries.
- One local CLI review surface with human and JSON projections optimized for Morfeo's whole-contract review.
- Crash-safe local journal, rebuildable read model, visible coverage gaps, and explicit retention.
- Existing-project operation and clean release installation through the Aether product package.

### 3.2 Out of scope for 1.0.0

- Remote analytics, hosted telemetry, remote ingestion, or cloud dashboards.
- Raw prompt, response, file, terminal, secret, credential, message, or chain-of-thought capture.
- Productivity scoring, worker ranking, performance bonuses, or quality judgements based only on activity volume.
- Predictive alerts, autonomous remediation, or automatic task reassignment.
- Replacing Hermes SessionDB, Kanban, logs, tools, hooks, or dashboard infrastructure.
- Changing Hermes core solely to add this observer.
- Unrelated project analytics or activity not explicitly and causally bound to the observed contract.
- Monetary cost, billing, price-table maintenance, or provider-invoice reconciliation. Native input/output/cache-read/cache-write/reasoning/total token counters and request duration remain in scope when exposed as structured metadata; unavailable counters stay unavailable and model requests remain separate from tools.

## 4. Decisions and provisional assumptions

The owner authorized Morfeo to complete this baseline with current evidence and refine it after implementation findings.

| ID | Delegated design decision | Supporting assumption |
|---|---|---|
| OBS-D-001 | Use one local Aether observation journal and a derived SQLite read model. | Exact cross-session reconstruction requires durable typed metadata, while Kanban and SessionDB must retain their native authority. |
| OBS-D-002 | Retain every observation event, summary, and hash indefinitely under the project's observation state, indexed for retrieval and compressed after trace closure. Deletion happens only through the explicit owner purge contract. | The owner requires a durable, indexed history: improvement decisions compare traces recorded months apart, and a pruned event can never be recovered. Metadata-only events are small enough to keep. |
| OBS-D-003 | Define a semantic loop as at least two consecutive returns to the same normalized lifecycle state without a new decision, evidence, resolved ambiguity, artifact revision, bound-work transition, review result, or acceptance delta. | One return can be an ordinary correction; repeated zero-delta cycles are the smallest useful deterministic loop signal. |
| OBS-D-004 | Require deterministic synthetic validation plus one controlled real local trace before a release candidate can pass. | Reducers need reproducibility, while the live trace proves that actual Hermes hooks and Aether packaging work together. |
| OBS-D-005 | Collection degradation never blocks legitimate contract work. | Observation must diagnose failures, not create a new single point of failure; incomplete coverage must be explicit instead. |
| OBS-D-006 | Use the originating owner-message timestamp as `started_at`; preserve persistence, handoff, execution start, final verification, and terminal closure as separate milestones; define total lifecycle duration as `closed_at - started_at`. | The owner approved observation of the whole contract, while separate milestones preserve creation, routing, execution, review, and closure latency. |
| OBS-D-007 | Implement collection as a native in-process Hermes plugin, never as a shell hook. | Native plugin hooks are delivered across CLI, TUI, gateway, cron, and query surfaces, isolate callback exceptions, and avoid spawning one subprocess per observed call. |
| OBS-D-008 | Use `pre_tool_call` only to open a span and `post_tool_call` as the terminal tool fact. | The locked runtime already emits IDs, duration, normalized status, and error class at `post_tool_call`; duplicating this logic would reduce parity. |
| OBS-D-009 | Reuse Hermes shared-metrics tool category/outcome normalization, but not its aggregate database as the contract journal. | The taxonomy is already bounded and tested, while shared metrics are opt-in, aggregate away contract causality, and have a different retention/export purpose. |
| OBS-D-010 | For 1.0, expose observation reads only through `aether observe`; defer the dashboard and a separate read-only agent query tool. The default CLI output is one coherent Morfeo-oriented review brief, not atomic section retrieval. | The owner needs high-quality summarized evidence for Morfeo now; extra read surfaces and per-section tool calls add implementation and review overhead without proportional 1.0 value. |
| OBS-D-011 | Keep one trace across Morfeo, Supervisor, Implementers, reviewers, and integration; bind each work unit explicitly through the root handoff or an authorized bound parent. | Project identity or timestamp proximity cannot prove that work belongs to the owner's objective. |
| OBS-D-012 | Report `blocked`, `review`, crash, timeout, reclaim, and retry as non-terminal lifecycle facts; close successfully only after the required graph is settled and acceptance is verified. | Hermes can resume blocked tasks and retry failed runs, so premature closure would truncate the real contract history. |
| OBS-D-013 | The observer may classify a trace as `completed` only after an exact authoritative root binding has materialized the trace and authoritative graph, assigned-review, acceptance, invariant, and final-verification state all agree. For every authority-bearing checkpoint, actor identity, profile, and role are resolved from product-owned context and never trusted from the event payload. Only the exact Morfeo authority may verify the whole contract; review approval must come from the assigned review authority. Missing, unresolvable, or forged authority yields at most `completion_candidate`. Every required unit is done, every required review is approved, every acceptance criterion is passed with evidence, and every OBS-INV-001 through OBS-INV-010 is present and passed. Any later semantic delta invalidates the prior verification and requires a fresh authoritative Morfeo verification. | Implementers, subagents, generic actors, and unassigned reviewers may supply bounded work or evidence but may not self-certify the owner's objective. Product-owned authority and a fresh closing view prevent a syntactically valid event from fabricating completion, while telemetry gaps remain fail-open for native work. |
| OBS-D-014 | Bind work without a required pre-create marker. The Aether Kanban wrapper SHOULD attach a deterministic opaque `aether.obs.v1:<trace_ref>:<unit_ref>` idempotency token to the existing `kanban_create` call; the observer also captures the returned task ID and reconciles descendants through durable parent edges. Missing or ambiguous linkage reduces coverage and never blocks task creation. | Hermes durably stores idempotency keys and parent edges, while `post_tool_call` observes the create result. This avoids a separate measurement step and preserves a recovery path after a lost callback without changing Hermes core. |
| OBS-D-015 | Model process reconstruction with three separate units: a semantic **step**, a concurrent **wave**, and an execution/rework **round**. A wave exists only when explicit durable parent/dependency references establish causally independent siblings inside the same evidenced round. Timestamp overlap never creates wave membership, predecessor, round, retry, regression, or critical-path edges; timestamps may measure and present intervals only after causal membership is known. | The owner needs to audit how Supervisor decomposed the contract without converting scheduling coincidence or clock skew into invented process structure. Aggregate agent/tool totals and wall-clock proximity cannot supply causality. |
| OBS-D-016 | Observation is strictly non-intrusive. It MUST NOT introduce a required workflow step, mandatory declaration, extra approval, or behavioural obligation for any role, and no lifecycle action may fail or be withheld because observation metadata is missing. | The owner's decision: this is a telemetry layer for better decisions, not a control layer. A required declaration would change how the pipeline behaves and would make the measurement instrument part of the process it measures. |
| OBS-D-017 | Derive defect and bottleneck attribution from native structured signals first; accept optional declarations second; and allow Morfeo to classify unresolved causes only during the closing verification it already performs. Every attribution carries its evidence source and is never presented as measurement when it is judgment. | Native block kinds, run outcomes, dispatcher skip reasons, policy denials, and tool error classes already carry most of the taxonomy without asking anyone for anything. Only the residual semantic distinction needs judgment, and Morfeo is already reading the whole contract at closure. |
| OBS-D-018 | Record a per-trace and per-participant configuration fingerprint with field-level coverage: effective model/provider and exact project-keyed system-prompt fingerprint when exposed by the request hook; project-keyed observed loaded-skill set and declared toolset; project-keyed effective tool surface only from a demonstrably complete snapshot; effective concurrency limits; fingerprint key epoch; and observer/runtime versions. | Tool, prompt, model, and topology decisions are longitudinal within one project, but configured toolsets and the final schema surface are different facts. Unknown/partial coverage is more useful than a false exact fingerprint, and OBS-D-028 prevents the fingerprint from becoming a portable dictionary oracle. |
| OBS-D-019 | Implement the 1.0 observer against the public observer/plugin surfaces of locked Hermes `v2026.8.18` (`e624e9fde561e1add9388384012b295fde669ade`). Do not carry a downstream core patch. Any missing generic signal is either represented as partial/unknown or contributed upstream and adopted only through a later qualified Hermes release. | Revalidation found sufficient public hooks for the causal core, but no complete metadata-only snapshot of the final direct/deferred tool surface and no dedicated lossless context-compression event in the locked release. |
| OBS-D-020 | Replace event-by-event `aether_contract_mark` obligations with automatic native capture and reconciliation. An optional bounded semantic checkpoint may be emitted as a fail-open side effect of an existing canonical contract write or closing verification; no role is instructed to call it, and its absence is never a pipeline violation. | Mechanical lifecycle is reconstructable from hooks and native stores. Some semantic facts are not inferable from metadata alone, so they remain `unknown`/`undeclared` unless an already-authorized action supplies a checkpoint. |
| OBS-D-021 | Package the observer inside the single `aether-agents` distribution and install the exact same wheel in both the isolated manager environment and the versioned Hermes runtime. Hermes discovers only `aether_agents.observation.capture.hermes_plugin` through the official `hermes_agent.plugins` entry point; no per-profile source copy or second observer distribution exists. | One wheel and one version eliminate manager/plugin drift. The manager can remain independent of Hermes when the plugin adapter is the sole Hermes-facing module and shared observation modules use no Hermes imports. |
| OBS-D-022 | Resolve project context through one `ObservationContextResolver`: exact Aether project/board mapping for a bound task or run first, verified session-to-Hermes-Project mapping second, and a manager-supplied launch binding verified against the local Aether project registry and portable marker third. `cwd`, profile name, timestamps, repository name, and an environment value without registry verification never establish project identity. Conflicting or unresolved sources produce no project event and increment bounded observer-health diagnostics; when a project later resolves, the trace receives an explicit coverage gap for the unresolved interval. | Every event must have one stable project UUID, while multiple profiles and projects can share the runtime. It is safer to lose coverage visibly than to contaminate another project's history. |
| OBS-D-023 | Treat owner messages as bounded candidates, not automatically as separate durable traces. A trace is materialized only when an authoritative contract persistence, existing trace/contract reference, or root Kanban binding establishes the objective. An exact message reference is linked when supplied; otherwise only one candidate in the same session lineage between the previous bound action and the first authoritative action may be selected. Zero or multiple candidates leave `started_at`/origin coverage unavailable and never trigger automatic trace merge. | A message may start a new objective or continue one. Session co-location and timestamp proximity alone cannot decide that semantic boundary. |
| OBS-D-024 | Use explicit durable identities: canonical lower-case project UUID; a cryptographically random 128-bit `trace_id` allocated once at authoritative materialization; a cryptographically random 128-bit `producer_epoch` per process; and a strictly increasing sequence within that epoch. Use a deterministic event ID from canonical native identity when a complete stable source tuple exists, otherwise allocate a random 128-bit event ID once before append. Reconciliation deduplicates on the same native tuple and never guesses an incomplete match. | PIDs are reusable and wall clocks collide. Stable source identities prevent replay duplicates, while random IDs safely cover events with no complete native key. |
| OBS-D-025 | Keep the journal as source evidence only. Its source kinds are `hermes_hook`, `native_reconciliation`, `aether_checkpoint`, and `observer_diagnostic`; the obsolete `aether_marker` and `reducer` kinds do not exist. Collector-known gaps may be appended as diagnostic events, but reducer-discovered corruption, incompatibility, or unknown schema is a reproducible read-model/summary diagnostic and is never written back into the source journal. | A reducer that writes into its own input makes replay history-dependent and can recursively duplicate diagnostics. |
| OBS-D-026 | Never migrate or rewrite retained journal bytes. Every current reducer carries deterministic pure upcasters for every released event schema it claims to read, records all collector/runtime/schema versions present, and writes a versioned rebuildable projection. An older rollback release preserves and indexes unknown newer bytes as quarantined coverage, without modifying them; a later compatible release reingests them. Immutable historical summaries remain addressable by summary/reducer/schema version, and semantic comparison refuses incompatible summary schemas rather than inventing a diff. | Indefinite retention and rollback require forward preservation even though old code cannot understand future schemas. SQLite and summaries are replaceable projections; JSONL remains the durable source. |
| OBS-D-027 | Keep synchronous hook work bounded to allowlist projection, canonical serialization, and one append-only write. The callback never waits for `fsync`; a plugin-owned supervised flusher performs bounded flush/fsync and segment close outside the agent path. A critical event wakes that flusher immediately. `critical_pending` remains set until the corresponding file `fsync` succeeds, including after a failed attempt, so urgency is retryable. Graceful teardown is genuinely bounded even if an `fsync` worker is blocked and never waits while holding the journal lock. Process crash, power loss, ENOSPC, short write, or flush failure remains fail-open and produces content-free health/coverage evidence when possible. | Power-loss durability cannot be guaranteed without potentially stalling the observed agent. The accepted priority is non-intrusion plus honest loss visibility, not clearing durability intent before the durable boundary succeeds. |
| OBS-D-028 | Use project-keyed HMAC-SHA-256 for content-derived configuration fingerprints, including system prompt, observed skill set, declared toolset, and complete effective surface. The 32 random key bytes live as `keys/<fingerprint_key_id>.key` with `0600`; `fingerprint_key_id = fpk_ + first_16_bytes_hex(SHA-256(key))`. The HMAC input is `b"aether-observation/v1\0" + UTF8(field_name) + b"\0" + canonical_JSON_bytes(value)`, so fields are domain-separated. The current non-secret key pointer changes atomically. Key material survives update/rollback and enters only private local recovery backup or an explicitly protected export. Owner-requested rotation or detected key loss starts a new epoch, records a coverage boundary, and never masquerades as a configuration change. Comparisons are valid only within one project and key ID; cross-project comparison is out of 1.0. Artifact/runtime hashes remain ordinary SHA-256. | Plain SHA-256 of small catalogs and common prompts is vulnerable to offline dictionary enumeration if a summary is copied. Project-keyed fingerprints preserve within-project comparison without exposing a portable oracle. |
| OBS-D-029 | Compact only closed segments through the normative `contracts/observation-segment-manifest.schema.json`: one deterministic standard-library gzip member at level 9 with `mtime=0`, no filename/comment, and OS byte 255. `segment_id = seg_ + uncompressed_sha256`; source/archive names encode producer epoch and inclusive first/last sequence. The canonical manifest records event/line count, lengths/hashes, and sorted unique event-schema/collector/runtime sets; reducer validation additionally requires `first_seq <= last_seq` and `event_count = line_count`. Write and verify temporary archive/manifest, fsync both, atomically rename both, fsync the directory, and replay-check exact uncompressed bytes and summary. Source removal is forbidden until the archive and manifest are durable and replay-verified; after removal, fsync the containing directory. Any failure before that boundary preserves the JSONL source, even when the temporary or renamed gzip can already be read. Active segments are never compacted, and interrupted temporaries/orphans/retries are recovered idempotently without stale-reference deletion. | Lossless retention must survive crashes and prove that compaction changed representation only, not evidence. |
| OBS-D-030 | Retain the existing release performance budgets as qualification gates and require a disposable pre-implementation spike against the locked clean Hermes checkout before broad fan-out. The spike measures projection/schema validation, append, asynchronous flush, incremental reduction at 10,000 and 100,000 events, corruption, and ENOSPC. A failed budget returns as a contract finding; it does not authorize silent architecture or threshold changes. | The targets are explicit but not yet supported by a measured baseline. Early measurement can expose an invalid assumption before the implementation graph hardens around it. |
| OBS-D-031 | Detect unclean producer tails through one POSIX advisory lock `locks/<producer_epoch>.lock` held for the writer lifetime. Clean close flushes/fsyncs, atomically renames the active segment into `closed/`, fsyncs the directory, and only then releases the lock. A reducer/recovery process never touches a lock held by a writer; if it can acquire the lock while the epoch still has an `active` segment, that epoch ended uncleanly. It ingests only the valid LF-terminated prefix, preserves the exact original/tail, and derives `coverage=incomplete` from the last visible event until a conservative next authoritative native boundary or the trace's current `as_of`; absent such a boundary, the gap remains open. It never claims that contiguous visible sequence numbers prove a clean tail. | Per-producer sequences detect internal gaps but cannot detect events never appended before a crash. Kernel-released advisory locks plus conservative gap semantics make lost tails visible without synchronous callback durability or PID identity. |

Changing any decision above requires an owner-approved contract revision; implementation findings alone do not silently redefine it.

## 5. Terminology

- **Contract trace**: one observation boundary logically beginning at an exactly linked owner message when available, materialized by an authoritative objective/contract/root binding, and ending only after verified completion or an explicit terminal cancellation, abandonment, or failure.
- **Owner-message candidate**: bounded metadata in memory or recovered from native SessionDB containing only message/session identity, role, and timestamp; it is not a trace or journal event until one authoritative objective binding selects it.
- **Producer epoch**: one cryptographically random process identity whose local sequence orders that process's journal events; it is never a PID.
- **Fingerprint key epoch**: one project-local HMAC key identity under which content-derived configuration fingerprints are comparable.
- **Contract-creation phase**: the interval from `started_at` through canonical `persisted_at`; it is a milestone inside the trace, not the trace boundary.
- **Bound work graph**: the root Kanban task plus required descendants explicitly linked to the trace with their parent relation and responsibility class.
- **Verified completion**: all required bound units are settled, every required review is approved, every acceptance criterion is passed with evidence, and Morfeo records final verification against authoritative state.
- **Terminal resolution**: `completed`, `cancelled`, `abandoned`, or `failed`; recoverable `blocked`, `review`, crashed, timed-out, reclaimed, or failed runs do not by themselves terminate the trace.
- **Semantic checkpoint**: optional typed metadata emitted as a fail-open side effect of an already-authorized canonical write or closing verification. It enriches facts that native metadata cannot express; roles never call it as a required workflow step.
- **Tool span**: one observable tool invocation with start, completion, duration, status, and safe classification metadata.
- **Semantic delta**: at least one new accepted/superseded decision, evidence reference, resolved material ambiguity, invariant result, or changed contract artifact hash.
- **Iteration**: a contract revision or investigation cycle with a non-zero semantic delta.
- **Technical retry**: repeated operation caused by an explicit tool/provider/process failure and not by unchanged contract reasoning.
- **Cycle**: a return to a previously observed normalized contract state without a semantic delta.
- **Semantic process step**: one causally bounded, human-auditable transition such as contract persistence, Supervisor decomposition, dispatch, implementation, review, rework, integration, acceptance, or terminal verification. Tool calls are evidence nested under a step, not separate process steps by default.
- **Parallel wave**: the maximal set of causally independent work-unit steps observed as eligible/running between dependency, review, owner, capacity, or terminal barriers. A wave records how many units and distinct agents were deployed and which work remained ready but not running.
- **Execution round**: one causally linked pass from an initial dispatch or explicit recovery/rework trigger through its next review, acceptance, blocking, or terminal barrier. Review changes, resumption, redispatch, protocol correction, and owner-authorized direction change open a new linked round rather than being hidden in totals.
- **Critical path**: the longest causally ordered chain of observed process steps and barriers. It is evidence about where wall time accumulated, not an automatic recommendation to add agents.
- **Semantic loop**: at least two consecutive zero-delta cycles over the same normalized state transition.
- **Regression**: an invariant that was satisfied becomes unsatisfied without an owner-linked superseding decision.
- **Reversion**: the canonical contract hash returns to an earlier revision hash.
- **Authorized reversion**: a reversion linked to an owner decision that explicitly supersedes the intervening decision or revision.
- **Coverage gap**: an interval or event class that the collector could not observe completely.

## 6. Component architecture

```text
Owner-message candidate / Morfeo contract / bound execution and review graph
                         |
                         v
      Aether observer module from the product wheel
       (native hooks + source reconciliation +
          optional bounded semantic checkpoints)
                         |
                         v
     per-process append-only JSONL journal segments
           (local metadata; crash recoverable)
                         |
                         v
          deterministic ingest + reducer
                         |
            +------------+-------------+
            |                          |
            v                          v
   derived SQLite read model     coverage diagnostics
            |
            v
  Aether CLI review brief
```

The product has one Python distribution, `aether-agents`, and one product version. Its exact immutable wheel is installed twice: once in the isolated `uv tool` manager environment that owns the public `aether` CLI, and once with `--no-deps` in the Aether-managed versioned runtime beside the release-locked Hermes distribution. The runtime discovers `aether_agents.observation.capture.hermes_plugin` through `[project.entry-points."hermes_agent.plugins"]`; profile configuration enables that entry-point name for every participating Aether role. The release lock records distribution name, normalized version, pre-build identity, and entry-point target. External release provenance and the local transition record bind the staged wheel filename/SHA-256 without placing a circular self-digest inside that wheel; `aether doctor` verifies installed build/file fingerprints against those records.

The import boundary is one-way and testable. Manager command, transition, release, update, rollback, service, and authentication modules never import Hermes. The Hermes adapter never imports those manager modules. Shared observation contracts, privacy projection, journal, reducer, storage, and report code import no Hermes modules; the adapter receives the public plugin context and is the only module allowed to register Hermes hooks. Installing the same distribution in the runtime does not authorize Hermes to update the manager or expose the runtime-local `aether` script as the public CLI.

The plugin computes the Aether XDG state root from product-owned installation context; a profile cannot redirect it to an arbitrary path. `ObservationContextResolver` validates candidate project sources against the Aether project registry, portable `.aether/project.toml`, canonical repository identity, and exact board mapping. Task/run binding outranks verified session-project binding, which outranks a verified manager launch binding. Agreement resolves one canonical lower-case UUID. Disagreement or no verified source suppresses project-journal output, increments only bounded content-free observer-health counters under `observations/health/`, and is surfaced by `aether doctor`. No unresolved message/task/session identifier is persisted in global health state.

### 6.1 Collector

The Aether observer is materialized from the runtime-installed product wheel as one product-owned Hermes entry-point plugin and enabled by product-owned configuration in every participating Aether profile. It MUST use public Hermes plugin hooks and tool registration APIs. It MUST NOT monkey-patch Hermes internals, require mutable upstream source, or copy an editable plugin implementation into per-profile plugin directories.

Required native observation inputs:

- session start/end/finalize/reset;
- user and assistant message identifiers/timestamps available through SessionDB or hooks;
- `pre_api_request`, `post_api_request`, and `api_request_error` for request identity, effective model/provider, project-keyed prompt fingerprint, bounded request counters, normalized usage, duration, finish reason, and error class;
- `pre_tool_call` to open an identifiable span;
- `post_tool_call` as the terminal tool fact, including `task_id`, `session_id`, `turn_id`, `api_request_id`, `tool_call_id`, `duration_ms`, `status`, and stable `error_type` where present;
- subagent start/stop with parent/child session identity and terminal status;
- exact Kanban hooks `kanban_task_claimed`, `kanban_task_completed`, `kanban_task_blocked`, `on_kanban_worker_spawned`, `on_kanban_worker_exited`, `on_kanban_worker_stale_claim`, `on_kanban_task_updated`, and `on_kanban_dispatch_tick`, plus authoritative task/run reads;
- `on_skill_lifecycle` for observed successful skill loads/uses, without assuming that it exposes the complete skill index or every failed consultation;
- task/run identifiers from runtime environment and Kanban read APIs;
- optional semantic checkpoints produced by an existing Aether canonical-write/verification path, when available;
- canonical artifact hash transitions.

Registration has a closed compatibility inventory for the locked runtime. A partially available plugin surface remains fail-open, but each unavailable expected hook produces a content-free capability gap and its stable name appears in the summary capability field `missing_hook_refs`; a global counter alone is insufficient because it cannot explain the affected trace. Qualification against the exact locked runtime expects 22 registered callbacks, exactly one callback per hook, and zero hooks after unload.

The collector writes only allowlisted metadata to a unique per-process journal segment. A process allocates one random `producer_epoch`, owns exactly one active segment at a time, and never shares its file descriptor. Contract-critical native facts or optional checkpoints (`contract.persisted`, `handoff.completed`, `work_unit.bound`, `acceptance.evaluated`, `contract.completion_verified`, terminal resolution, explicit coverage gaps) are queued for the earliest bounded plugin-owned flush, but the synchronous callback performs no `fsync` and never waits for that flush. Ordinary tool spans may remain buffered longer. This is process-crash recoverable on the ordinary local filesystem path but not falsely claimed power-loss-proof; any detected loss reduces coverage.

The hook callback MUST project the native payload into the observation schema before any sink can observe the native payload: queue, logs, journal, SQLite, summary, retry storage, or exception report. In particular, native `args`, `result`, `error_message`, `middleware_trace`, `user_task`, prompt, response, child goal/summary, raw commands, output, and error text MUST be discarded. Projection validates both bounded shape and permitted provenance; a string's length alone cannot make an absolute path or prompt-like content safe. Redaction is defence in depth after projection, not permission to persist those fields.

Hermes hook result normalization is adopted as the compatibility boundary: native `ok|success` becomes `completed`, `error|failed` becomes `failed`, and `blocked|cancelled|timed_out|timeout` remain distinct. Tool category is derived with the locked runtime's bounded `tool_category()` mapping. Aether MUST add a compatibility test before changing runtime revisions; an unknown native value becomes `unknown` plus a coverage diagnostic, never an invented success/failure.

Plugin callbacks MUST be observer-only: they return no directive and may not mutate tool arguments, results, model context, approval decisions, Kanban, or SessionDB. Callback exceptions are allowed to reach Hermes's plugin isolation boundary only after a best-effort local coverage diagnostic; they MUST never escape into the agent loop.

Native reconciliation is deliberately narrower than the native schemas. From SessionDB, the collector may read session/message identifiers, roles, timestamps, parent session, profile, counters, activity timestamp/provenance, tool name/call ID, and terminal metadata; it MUST NOT copy message content, tool-call JSON, reasoning fields, `api_content`, origin JSON, display metadata, or handoff error text. From Kanban it may read task/run IDs, profile/assignee, statuses, timestamps, heartbeat, runtime cap, and bounded outcome; it MUST NOT copy task body, result, run summary, run metadata, run error, event payload text, comments, or attachments. Hermes has no per-heartbeat or per-timeout task hook in the locked taxonomy: `last_heartbeat_at`, timed-out status/outcome, and their timestamps are reconciled from authoritative `task_runs`. Hook payload `summary`, block `reason`, `workspace_path`, and dispatcher `result` are also discarded.

SessionDB does not durably columnize `turn_id` or `api_request_id` in the locked runtime. Those identifiers are authoritative only when captured from native hooks. Reconciliation may match a missed event by `session_id` and `tool_call_id`, but it MUST NOT synthesize missing turn/API identifiers. Their absence becomes an explicit coverage gap when it affects causality or exactness.

A terminal-without-start tool/API event remains a visible observed call but creates an unpaired-span gap and makes the affected coverage incomplete; a start without a terminal event does the same after reconciliation. An event with missing `turn_id` or `api_request_id` never receives a time-derived substitute. Native heartbeat recency is `fresh`, `stale`, or `unknown` under the versioned threshold policy; `unknown` never becomes `fresh`, and no heartbeat state proves activity, semantic progress, waiting cause, or termination.

Every callback and optional checkpoint sink uses a process-local re-entrancy guard. Direct journal/database writes never call back through the Hermes tool registry. Observer-internal serialization, ingestion, reconciliation, and CLI queries produce no nested model/tool span.

Owner-message candidate metadata is bounded and process-local. The collector keeps at most the latest candidate per active session in an LRU of at most 1,024 sessions for at most 24 hours; eviction changes only observer-health counters because authoritative later materialization can still reconcile message identity/timestamp from SessionDB. No candidate content is read or stored. These bounds limit measurement memory, not workflow/session lifetime.

### 6.2 Journal

- Format: newline-delimited instances of `contracts/observation-event.schema.json`; one canonical JSON event and one trailing LF per append. A canonical line larger than 65,536 bytes including LF is rejected before append as forbidden payload rather than split.
- Ordering: `producer_epoch` plus strictly increasing `producer_seq` is authoritative within one process; non-null `monotonic_ns` validates local hook timing and `occurred_at` supplies wall time. Reconciled events without a native monotonic sample set it to null. Explicit causal edges resolve cross-process order. Wall-clock proximity never orders causal events.
- Identity: `trace_id = ctr_` plus 32 lowercase hexadecimal characters from 128 random bits at materialization; `producer_epoch = prd_` plus the same; `project_id` is the canonical lower-case portable UUID. `event_id` is deterministic from canonical stable native source identity when complete, otherwise `evt_` plus 32 lowercase hexadecimal random characters allocated once before append. Ingest deduplicates on `event_id` and on the complete native identity tuple; an incomplete tuple is never fuzzy-matched.
- Source boundary: source kinds are exactly `hermes_hook`, `native_reconciliation`, `aether_checkpoint`, and `observer_diagnostic`. Collector-known diagnostics can be events. Reducer-discovered diagnostics remain derived rows/summary coverage and are never appended to a source segment.
- Compatibility: every event records `collector_version` and a SHA-256 `runtime_fingerprint` over the locked compatibility files; summaries retain every distinct pair seen across a resumed/upgraded trace. The fingerprint is SHA-256 over canonical JSON mapping each normalized relative path to its file SHA-256, sorted by path, for `hermes_cli/plugins.py`, `hermes_cli/lifecycle.py`, `model_tools.py`, `hermes_cli/observability/shared_metrics_contract.py`, `hermes_cli/profiles.py`, `hermes_state_common.py`, `hermes_cli/kanban_db.py`, `tools/delegate_tool.py`, and `hermes_cli/web_server.py`. A missing file yields `compatibility_mismatch`; the collector never invents a fingerprint.
- Path and permissions: `XDG_STATE_HOME` MUST be absolute when supplied; a relative value produces an explicit unavailable/error state and never a cwd-dependent path. Every generated project, trace, producer, segment, projection, key, and sidecar component follows a closed grammar. Product-owned directories are `0700`, and journal, key, DB, WAL, and SHM files are `0600` on POSIX. Symlinks, path escape, ownership mismatch, hard links (`st_nlink != 1`), or a link/rename race are rejected before the first byte is written.
- Flush/failure: synchronous collection is allowlist projection, canonical serialization, and one bounded append-only write only. A supervised plugin flusher owns periodic and critical-queue flush/fsync outside the callback. Critical work wakes the flusher; `critical_pending` remains set until file `fsync` succeeds and survives a failed attempt. Graceful unload attempts one bounded final flush and closes/renames the segment, but `stop()` remains bounded even when an `fsync` is blocked. Short write, ENOSPC, process death, power loss, or flush failure cannot escape into Hermes; content-free health counters and the next resolvable trace report the gap when possible.
- Unclean tail: the writer holds `locks/<producer_epoch>.lock` by POSIX advisory lock for its lifetime. Clean close fsyncs and renames the active segment before releasing it. An acquireable lock paired with a remaining active segment is an unclean epoch even when visible sequences are contiguous; ingestion preserves the source/tail and derives incomplete coverage until the next conservative authoritative native boundary or open-ended `as_of`.
- Corruption: ingestion stops at the last valid LF-terminated schema-valid line in a segment, records a derived coverage gap, and preserves both the original segment and exact corrupt tail for local diagnosis until explicit owner-authorized purge. It never appends the derived diagnosis back to that segment.

### 6.3 Read model

The reducer ingests journal events into a versioned local SQLite database in WAL mode under `projections/<read-model-schema>.sqlite3`, with an atomic derived pointer selecting the projection for the active release. Each source event is isolated by a per-event savepoint: the event row and all derived rows commit atomically, `_derive()` failure rolls that event back completely, and its content-free diagnostic is recorded only in an independent transaction. Replay retries the failed source event; bulk ingest preserves earlier valid events and isolates a later invalid event rather than committing a half-derived row or rolling valid work back. The database is derived and rebuildable from retained journal data plus native SessionDB/Kanban references. It MUST NOT be consulted to decide task lifecycle or effect authority.

Projection rebuild writes and file-fsyncs a complete candidate, atomically renames it, directory-fsyncs the transition, and coordinates readers under a product-owned advisory lock. A reader that merely encounters a newer compatible projection must not downgrade the active projection pointer. Pointer changes require the lifecycle/rebuild owner, the lock, and a compare-and-swap against the expected active identity; an explicit rollback selects its compatible prior projection while preserving newer projection and source bytes for re-update. Rebuild, update, rollback, and re-update recover idempotently after interruption at every boundary.

Minimum logical tables:

- `observation_trace`;
- `observation_event`;
- `contract_decision`;
- `contract_revision`;
- `tool_span`;
- `participant_contribution`;
- `bound_work_unit`;
- `work_unit_run`;
- `process_step`;
- `process_wave`;
- `execution_round`;
- `configuration_fingerprint`;
- `model_request_economics`;
- `tool_surface_snapshot`;
- `dispatch_observation`;
- `bottleneck_interval`;
- `defect_attribution`;
- `review_transition`;
- `acceptance_criterion`;
- `invariant_transition`;
- `coverage_gap`;
- `observation_summary`.

Schema versions are explicit. Released journal bytes are immutable. A reducer declares the exact event versions it reads, the summary version it writes, and its read-model schema. It applies deterministic pure upcasters from every supported historical event version before reduction. Unknown newer events remain in their original segments and are indexed by segment/byte range/hash in quarantine with a visible derived coverage gap; no source event is moved, rewritten, or discarded. A later compatible release reingests them. Historical summaries remain immutable/addressable. `--since` refuses semantic comparison when summary schemas cannot be losslessly normalized to one comparison schema.

### 6.4 Reducer and flow analyzer

The reducer is deterministic: the same ordered event set and reducer version MUST produce byte-equivalent JSON summaries after canonical JSON serialization. `as_of` is the maximum `occurred_at` among included events (or `started_at` for an opening-only trace), never query wall time. `summary_id` is `sum_` plus SHA-256 of the canonical JSON summary with `summary_id` omitted. It performs no LLM call. Natural-language explanation may be generated later, but it is non-authoritative and must link to the deterministic summary it paraphrases.

### 6.5 Existing Hermes observability reuse boundary

Hermes already contains an opt-in shared-metrics subsystem and optional Langfuse/NeMo Relay observability plugins. Aether MUST NOT enable, configure, or export through any of them merely to satisfy this feature.

Aether MAY import the bounded shared-metrics normalization functions for tool category and outcome when they are part of the locked runtime. It MUST NOT treat `telemetry/shared_metrics/metrics.sqlite3`, a Langfuse trace, a Relay export, or ATIF/ATOF output as contract authority because those surfaces may be disabled, remote, aggregate, content-bearing, or causally incomplete. If the reusable normalizer is unavailable after an upgrade, the compatibility gate fails before release rather than silently forking the taxonomy.

### 6.6 Native extension packaging

The package has one native agent plugin identity. It registers:

- hooks through `ctx.register_hook`;
- unload cleanup through `ctx.on_unload` and only supervised background tasks through `ctx.spawn_task` when an event loop exists.

The observer registers no mandatory agent-facing telemetry tool. Aether's canonical contract writer or closing verifier MAY call the observer library's bounded checkpoint sink after its own authoritative action succeeds. The sink accepts only schema-enumerated kinds and opaque references, is fail-open, and is not an independent workflow action.

`aether observe` calls the product-owned query/reducer library directly from the Aether manager CLI and does not require a live Hermes process. Aether setup installs/enables the collector package in each managed participant profile; upgrade and rollback keep those copies at one package version. No observation API listener, dashboard extension, or separate read-only agent query tool ships in 1.0.

## 7. Trace lifecycle

### 7.1 Required timestamps

Each trace records:

- `started_at`: exactly linked originating owner-message timestamp, otherwise null with origin coverage incomplete; a later materialization timestamp never substitutes for an unknown origin;
- `first_action_at`: first Morfeo contract action or tool span;
- `executable_at`: first point at which all executable-contract invariants pass;
- `persisted_at`: successful canonical persistence of that executable revision;
- `handed_off_at`: successful Supervisor handoff, if any;
- `execution_started_at`: first authoritative running state for a required bound work unit;
- `last_verified_progress_at`: latest event that changed the normalized lifecycle state;
- `completed_at`: successful final acceptance verification, if achieved;
- `terminated_at`: explicit non-success terminal resolution, if one occurs;
- `closed_at`: `completed_at` or `terminated_at`; never persistence, handoff, recoverable block, review, crash, timeout, or reclaim.

### 7.2 Opening and correlation

The collector records at most one bounded owner-message candidate per active session, never its content. It materializes a trace only after `ObservationContextResolver` resolves one project and an authoritative canonical persistence, existing trace/contract reference, or root Aether Kanban handoff establishes the objective. The trace receives a random `trace_id` at that point but may carry the earlier exactly linked owner-message timestamp as `started_at`.

An exact originating message reference wins. Without one, deterministic reconciliation may select a candidate only when exactly one owner-role message exists in the same native session lineage after the previous bound trace action and no later than the first authoritative materialization action. Zero or multiple candidates set `started_at = null`, record `reconciliation_ambiguous`, and make origin-dependent durations null. They do not select the nearest timestamp. A reference to an existing trace/contract resumes it; a new authoritative contract/root identity materializes a new trace. Two traces are never automatically merged. A later exact reference may bind a previously unknown origin append-only, but it may not erase the earlier ambiguity diagnostic or rewrite source events.

Aether's canonical contract writer and closing verifier MAY emit an optional semantic checkpoint after their existing authoritative action succeeds. A checkpoint accepts only schema-enumerated kinds and bounded opaque references; it never accepts rationale, prompt text, contract clauses, shell commands, file content, or arbitrary dictionaries. The sink derives profile/role authority from the active Aether installation, ignores all return values for workflow purposes, and fails open. Missing checkpoints reduce only the corresponding semantic coverage.

The root Kanban task is bound from the observed `kanban_create` result plus the current project/trace context. The Aether wrapper SHOULD attach a deterministic opaque `aether.obs.v1:<trace_ref>:<unit_ref>` idempotency token within that same native call. The observer persists only the validated prefix and opaque hashes, never an arbitrary idempotency key. Descendants inherit membership through durable parent edges from an already bound task in the same project; every inherited edge remains visible and reversible by later reconciliation.

No separate binding reservation is required. If the create-result hook is lost, reconciliation uses the strict idempotency token and parent graph. Zero or multiple matches, project/parent mismatch, malformed/reused tokens, or conflicting roots produce `reconciliation_ambiguous`; none auto-bind and none blocks or rolls back the native task creation.

A trace may bind later participants through bound task/run/session identifiers. A participant's events count only when they are causally linked to the trace. Merely sharing a profile, project, tenant, branch, or time window is insufficient. All native descendants of a bound root are observed as graph members; whether they satisfy an original acceptance criterion is derived only from canonical references or remains `unknown`.

### 7.3 Creation, execution, and completion

Contract creation completes only when:

1. the executable-contract invariants pass;
2. the accepted revision is written to its canonical artifact;
3. the persisted artifact hash is recorded;
4. the persistence operation reports success.

A handoff is a separate event linked to the persisted revision. Failed or blocked handoffs do not change `persisted_at` and are reported in routing latency/coverage. Execution begins when the first required bound work unit enters authoritative `running` state.

The trace reaches verified successful completion only when all of the following hold:

1. one exact authoritative root binding has materialized the trace without a competing candidate or contradictory binding;
2. the root task and every required bound work unit are `done` in authoritative Kanban state;
3. no required unit remains in `triage`, `todo`, `scheduled`, `ready`, `running`, `blocked`, or `review`;
4. every required review/QA/integration unit is approved and terminal, and the approval resolves to the assigned review authority;
5. every declared acceptance criterion is `passed` with at least one safe evidence reference;
6. every `OBS-INV-001` through `OBS-INV-010` is explicitly present and `passed`; an absent, `failed`, `pending`, or `unknown` invariant blocks only the observer's completed classification;
7. an authoritative canonical record or optional bounded checkpoint records Morfeo's completed reconciliation against Kanban, SessionDB references, canonical artifacts, and evidence, with identity/profile/role resolved from product-owned context rather than checkpoint claims; and
8. no later event has changed contract, artifact, bound-work, review, acceptance, or invariant semantics. Any such semantic delta invalidates the prior verification until a fresh authoritative Morfeo verification observes the new state.

If mechanical state is settled but any authority, root, assigned-review, evidence, invariant, or freshness condition above is unavailable, the observer reports at most `completion_candidate` with the corresponding coverage `unknown`/incomplete; it never blocks the native work or fabricates `completed`. A root task reaching `done` before its required graph settles is also a completion candidate, never verified completion. `blocked` and `review` are open states. A run ending `crashed`, `timed_out`, `failed`, `spawn_failed`, `gave_up`, `reclaimed`, or `stale` is recorded as an anomaly/outcome and the trace remains open while a legitimate resume, retry, rework, or owner decision remains possible. The observer also preserves the distinct native outcomes `rate_limited`, `review_requested`, `changes_requested`, and `scheduled`; it never folds any of those values into `unknown`, a generic failure, or successful completion.

Non-success closure requires authoritative owner/Morfeo resolution already present in a canonical artifact/session lifecycle or an optional bounded checkpoint: cancellation, abandonment of the objective, or verified terminal failure with no accepted recovery path. In its absence the observer reports an open/unknown terminal state rather than guessing. Those outcomes never satisfy acceptance and never count as completed.

### 7.4 Abandoned and resumed traces

An open trace survives process and worker restarts, blocks, reviews, retries, handoff gaps, collector upgrades, and fingerprint-key epochs. Morfeo or an authorized bound participant resumes the same trace only when project plus contract or bound task/run references match. Session identity alone cannot resume a trace. The summary reports every observable inactive interval. Cancelled, failed, and abandoned traces are never reported as completed and are excluded from successful-completion calculations. A new owner objective cannot reuse a terminal trace ID.

### 7.5 Independent current-state dimensions

The reducer exposes six independent dimensions and never collapses them into one progress label:

- `liveness`: derived from current bound run/process state and heartbeat recency (`alive|stale|dead|not_applicable|unknown`);
- `activity`: derived from current model/tool/wait/review spans (`idle|model_call|tool_running|working|waiting|reviewing|unknown`);
- `progress`: derived only from normalized lifecycle deltas (`verified|no_verified_progress|suspected_loop|suspected_stall|complete|unknown`);
- `waiting`: the highest-precedence open wait class (`none|owner|dependency|approval|provider_backoff|process|review|unknown`);
- `anomalies`: whether unresolved crash/timeout/gap/regression/loop or incompatible-state evidence exists (`clear|present|unknown`);
- `termination`: `open|completed|cancelled|abandoned|failed`.

For multiple concurrent required units, aggregate liveness/activity use explicit precedence documented by the reducer version: any active required run prevents `not_applicable`; unresolved stale/dead evidence prevents a clean aggregate; simultaneous states remain visible in each `work_graph.units` row. Heartbeats can change liveness but never progress.

## 8. Event contract

The normative event schema is `contracts/observation-event.schema.json`.

### 8.1 Required event classes

- Trace: `trace.opened`, `trace.resumed`, `trace.closed`, `trace.cancelled`, `trace.abandoned`, `trace.failed`.
- Clarification: `clarification.requested`, `clarification.resolved`.
- Decision: `decision.recorded`, `decision.superseded`, `decision.rejected`.
- Contract: `contract.revision`, `contract.executable`, `contract.persisted`, `contract.execution_started`, `contract.completion_candidate`, `contract.completion_verified`.
- Evidence: `evidence.added`, `evidence.rejected`.
- Participant: `participant.joined`, `participant.left`.
- Configuration: `configuration.observed`, `tool_surface.observed`, `skill.loaded`.
- Model/context: `model.request_started`, `model.request_completed`, `model.request_failed`, `context.compression_observed`, `context.overflow_observed`.
- Tool: `tool.started`, `tool.completed`, `tool.failed`, `tool.blocked`, `tool.cancelled`, `tool.timed_out`, `tool.interrupted`.
- Wait: `wait.started`, `wait.ended`.
- Handoff: `handoff.started`, `handoff.completed`, `handoff.failed`, `handoff.blocked`.
- Work graph: `work_unit.bound`, `work_unit.unbound`, `work_unit.status`, `dispatch.observed`.
- Run: `run.started`, `run.finished`.
- Review: `review.requested`, `review.approved`, `review.changes_requested`.
- Acceptance: `acceptance.declared`, `acceptance.evaluated`.
- Invariant: `invariant.passed`, `invariant.failed`.
- Attribution: `bottleneck.attributed`, `defect.attributed`.
- Coverage: `coverage.gap`, `coverage.restored`.

### 8.2 Causality

Every event belongs to one trace and identifies its producer process. Decision, revision, evidence, invariant, handoff, model-request, and dispatch events MUST carry stable references. A summary may claim causality only from explicit `parent_event_id`/domain references, native task-session-turn-request-call identifiers, one span's matching start/end identity, durable parent/run/review edges, or an optional checkpoint/canonical-reference link. Timestamp proximity alone is not sufficient.

The schema conditionally requires `tool`, `work_unit`, `acceptance`, `wait`, `configuration`, `model_request`, `tool_surface`, `dispatch`, `attribution`, or `coverage` metadata for their corresponding event classes. Reducer validation additionally requires top-level `task_id` to equal `work_unit.task_ref` when both are present and a non-null `run_id` for run events. Optional checkpoints are accepted only from the bounded Aether sink after its owning authoritative action; mismatch is rejected and reported without copying the native payload.

### 8.3 Safe metadata allowlist

Allowed metadata includes:

- opaque identifiers;
- timestamps and durations;
- actor kind, profile, and role;
- tool name and category;
- success/failure/interruption status;
- numeric exit code;
- stable error class/code without raw error text;
- project-relative artifact reference;
- SHA-256 artifact hashes;
- project-keyed, domain-separated HMAC-SHA-256 configuration fingerprints plus their non-secret `fingerprint_key_id` epoch;
- producer sequence plus decision, evidence, invariant, acceptance-criterion, task, parent-task, run, session, turn, API-request, tool-call, and message references;
- host-neutral target kind such as `contract_artifact`, `web_domain`, `project_file`, or `process`.

Forbidden metadata includes:

- raw prompts or responses;
- chain-of-thought or hidden reasoning;
- message text;
- file contents or diffs;
- terminal commands, stdout, or stderr;
- web query text or extracted page content;
- absolute home paths;
- secrets, credentials, tokens, cookies, credential-store identifiers, fingerprint keys, or raw HMAC input material;
- arbitrary unvalidated payload dictionaries.

Fields not named by `contracts/observation-event.schema.json` are rejected because `additionalProperties` is false. The collector also maintains a negative allowlist test using real native payloads to prove that sensitive source keys never reach the serializer.

## 9. Functional requirements

### 9.1 Duration

- **OBS-FR-001**: The observer MUST calculate total lifecycle wall duration as `(closed_at || as_of) - started_at` and contract-creation duration as `persisted_at - started_at` when persistence exists.
- **OBS-FR-002**: It MUST calculate time to first action, time to executable contract, handoff latency, post-handoff dispatch latency, execution duration, time to verified completion, and non-success termination latency separately.
- **OBS-FR-003**: It MUST partition the full lifecycle interval into unioned active time, owner-wait time, external/dependency wait time, review wait time, and unclassified time without double-counting overlapping parallel spans.
- **OBS-FR-004**: Unclassified time MUST remain visible; it MUST NOT be silently labeled as productive or waiting.
- **OBS-FR-005**: An incomplete trace MUST show duration through deterministic `as_of` and its real current state; it MUST never fabricate `persisted_at`, `completed_at`, `terminated_at`, or `closed_at`.

### 9.2 Participants and actions

- **OBS-FR-006**: The summary MUST list each causally linked participant by actor kind, stable identity, profile/role where available, and observed action totals by event class.
- **OBS-FR-007**: Owner messages count as participation only when linked to trace opening, clarification, decision, approval, rejection, or scope change.
- **OBS-FR-008**: Contributions MUST be stated as observable actions and references, not inferred mental effort or quality.
- **OBS-FR-009**: Spawned subagents count as participants only after a linked `participant.joined` or delegated run reference and at least one returned or terminal event.
- **OBS-FR-010**: A generated prose summary MAY be shown, but the deterministic action table is authoritative and the prose MUST expose its summary ID.

### 9.3 Tools

- **OBS-FR-011**: Each tool invocation MUST be counted once by resolved tool name, causally linked participant, and terminal status.
- **OBS-FR-012**: Parallel tool calls MUST remain separate spans; active duration uses interval union while call totals remain exact.
- **OBS-FR-013**: Technical retries MUST be linked to the failed/interrupted call they repeat.
- **OBS-FR-014**: `delegate_task` counts both as a tool call and, when a child actually starts, as participant delegation.
- **OBS-FR-015**: Model/provider calls MUST NOT be counted as tools. They are recorded in their own required economics section under `9.8`, never folded into tool totals.
- **OBS-FR-016**: Any missing pre/post pair, including terminal-without-start, dropped journal event, missing required hook, unknown schema, or inaccessible native source MUST make `coverage.complete = false` and identify the affected interval/class. A terminal observation may still count as one call, but it can never make an unpaired span complete.
- **OBS-FR-032**: SessionDB/Kanban reconciliation MUST use only the native-field allowlist; text/blob fields are never copied into observation state.
- **OBS-FR-033**: Missing `turn_id` or `api_request_id` MUST remain null and affect coverage when material; the reducer MUST NOT infer either identifier from timestamps.
- **OBS-FR-034**: `blocked`, `cancelled`, `timed_out`, `failed`, `interrupted`, `completed`, and `unknown` calls MUST remain separate totals; no terminal state may be folded into success. For a complete trace, `total_calls` MUST equal both the sum of terminal-status totals and the sum of `by_name.calls`; `total_duration_ms` MUST equal the sum of `by_name.duration_ms`; every `by_actor` bucket MUST satisfy the same name/status arithmetic for that actor.
- **OBS-FR-035**: A process death after `pre_tool_call` without a terminal hook MUST yield one abandoned/unpaired span after reconciliation, not both a completed call and a gap.
- **OBS-FR-036**: Observer-internal writes, reconciliation, reduction, checkpoint sinks, and CLI queries MUST never generate recursive model/tool spans. If an existing authoritative Aether action invokes a normal Hermes tool, that outer tool call remains counted exactly once.

### 9.4 Flow

- **OBS-FR-017**: The reducer MUST version normalized lifecycle state by accepted decisions, unresolved material ambiguities, evidence references, invariant results, artifact hashes, required work-unit states, latest run outcomes, review states, and acceptance states.
- **OBS-FR-018**: A contract, artifact, bound-work, review, or acceptance transition with non-zero semantic delta MUST be classified as a useful iteration or verified progress according to its phase.
- **OBS-FR-019**: A repeat caused by an explicit failure class and linked retry MUST be classified as a technical retry, not a semantic loop.
- **OBS-FR-020**: Two consecutive zero-delta cycles over the same normalized transition MUST be classified as one semantic loop with `cycle_count >= 2`.
- **OBS-FR-021**: An invariant, accepted review, or acceptance criterion transitioning from passed/approved to failed/changes-requested without an owner-linked superseding decision MUST be classified as a regression.
- **OBS-FR-022**: Returning to an earlier artifact hash MUST be classified as a reversion; it is authorized only with an explicit linked owner supersession.
- **OBS-FR-023**: A changed owner decision with a valid supersession edge MUST be reported as a decision/scope change, not a regression.
- **OBS-FR-024**: The summary MUST expose the evidence/event IDs behind every loop, regression, and reversion classification.

### 9.5 Authority and resilience

- **OBS-FR-025**: The observer MUST be read-only with respect to Kanban, SessionDB, canonical artifacts, credentials, and effect gates.
- **OBS-FR-026**: Collector, reducer, or CLI-query failure MUST NOT block legitimate contract work.
- **OBS-FR-027**: Degraded collection MUST produce a visible coverage gap at the next available durable write; summaries with gaps MUST NOT claim exact completeness.
- **OBS-FR-028**: Collection, reduction, and CLI query MUST perform no outbound or non-loopback network request. The 1.0 observer exposes no network listener.
- **OBS-FR-029**: An observer purge affects only Aether observation events/read models and cannot delete native Kanban, SessionDB, logs, projects, or canonical artifacts.
- **OBS-FR-030**: Enabling Aether observation MUST NOT enable Hermes shared metrics, Langfuse, NeMo Relay, remote export, or any telemetry setting.
- **OBS-FR-031**: Plugin unload/reload MUST close buffers, cancel only plugin-owned supervised tasks, and preserve already flushed journal segments for deterministic resume.

### 9.6 Full-lifecycle graph and termination

- **OBS-FR-037**: One trace MUST span contract creation, handoff, the entire required execution/review graph, acceptance verification, and terminal closure.
- **OBS-FR-038**: Every observed work unit MUST carry a trace-binding status, relation, task ID, parent-task references, and requirement classification when authoritative evidence provides it; unavailable classifications remain `unknown`. Shared project/time/profile alone is insufficient.
- **OBS-FR-039**: A root binds only through its observed create result or strict opaque correlation token. A native descendant of a bound task inherits graph membership through its durable parent edge; ambiguous/cross-project edges remain unbound. Binding and unbinding history is append-only and cannot be erased by archive or deletion.
- **OBS-FR-040**: Root-task `done` MUST NOT produce `completed` while any required descendant, review, or acceptance criterion remains open, blocked, failed, pending, or unknown.
- **OBS-FR-041**: Successful observation closure MUST require one exact authoritative root, authoritative done state for every required unit, approval from every assigned required review authority, every declared acceptance criterion passed with evidence, every OBS-INV-001 through OBS-INV-010 present and passed, and fresh authoritative Morfeo verification evidence from a canonical record or optional bounded checkpoint whose actor identity/profile/role resolve from product-owned context. If only the graph is settled, authority is missing/forged, an invariant is absent/non-passing, or a semantic delta follows verification, the observer reports at most `completion_candidate`; it does not block native completion. Work-unit, review, acceptance, and invariant totals MUST reconcile exactly with their arrays and per-state buckets; inconsistency prevents only the observer's `completed` classification and produces a coverage/anomaly fact.
- **OBS-FR-042**: Task `blocked` and `review` states are non-terminal and MUST retain an open trace with explicit waiting/activity state.
- **OBS-FR-043**: Native run outcomes `completed`, `blocked`, `crashed`, `timed_out`, `failed`, `spawn_failed`, `gave_up`, `reclaimed`, `protocol_violation`, `rate_limited`, `stale`, `review_requested`, `changes_requested`, `scheduled`, and `unknown` MUST remain losslessly distinct and machine-countable. Crash, timeout, failure, spawn failure, give-up, reclaim, protocol violation, and stale MUST NOT close the trace while recovery or an owner decision remains possible; provider backoff and review/scheduling states likewise never prove completion.
- **OBS-FR-044**: Every summary MUST expose liveness, activity, verified progress, waiting, anomalies, and termination as separate state dimensions.
- **OBS-FR-045**: Heartbeats, elapsed time, token volume, model calls, and tool-call volume MUST NOT create verified progress without a normalized lifecycle delta.
- **OBS-FR-046**: Cancellation, abandonment, and terminal failure MUST be explicitly authorized/evidenced, close with their own outcome, leave acceptance incomplete, and never count as successful completion.
- **OBS-FR-047**: Implementers and subagents may attach safe evidence references but MUST NOT mark whole-contract completion; reviewers may evaluate only criteria assigned to their product-owned review identity, an unassigned/generic reviewer cannot approve, Supervisor may bind work/review units but cannot verify closure, and only product-owned Morfeo identity plus role may verify final contract completion. Event-supplied `actor_id`, `profile`, or `role` never grants that authority.
- **OBS-FR-048**: The Aether Kanban wrapper SHOULD attach the strict opaque correlation token inside the existing `kanban_create` call, and the observer MUST capture the returned task ID when the public hook supplies it. There is no separate reservation action and native task creation never depends on observation success.
- **OBS-FR-049**: Missing, malformed, reused, cross-project, cross-parent, or multiply matched correlation tokens/results MUST NOT auto-bind a root; they produce `reconciliation_ambiguous`. Parent-inherited descendants are bound only through an already bound same-project parent.
- **OBS-FR-050**: Worker startup resolves trace membership from `HERMES_KANBAN_TASK`, the durable parent graph, and a strict stored correlation token when present. Ordinary arbitrary idempotency keys are discarded, not journaled; unresolved membership remains explicit and does not suppress native events.

### 9.7 Causal process reconstruction

- **OBS-FR-051**: Every summary MUST expose an ordered causal process reconstruction in addition to aggregate durations, participants, tools, and work-graph totals.
- **OBS-FR-052**: Process order and membership MUST come from explicit durable parent/dependency edges, task/run/review transitions, typed handoff/checkpoint references, and matching native span identifiers. Cross-process wall-clock proximity or overlap MUST NOT assign a predecessor, step, wave, round, retry, regression, or critical-path edge.
- **OBS-FR-053**: Each semantic process step MUST expose its stable index, kind, responsible participant/profile, related task/run references, causal predecessors, round/wave membership, start/end/duration, outcome, semantic-delta flag, and evidence event IDs. Unknown fields remain explicit and reduce coverage when material.
- **OBS-FR-054**: Each parallel wave MUST expose its round, member steps/work units, distinct deployed participants, deployed-unit count, observed peak parallelism, dispatch-tick-sampled eligible-unit and ready-but-not-running counts/time, effective concurrency limits when durably captured, start/end/duration, and the evidenced or `unknown` barrier that ended/constrained the wave. A wave exists only when explicit durable parent/dependency references establish eligible sibling membership; Timestamp overlap never creates wave membership, though timestamps may measure overlap after membership is established.
- **OBS-FR-055**: Each execution round MUST expose its trigger (`initial_dispatch`, `review_rework`, `resumption`, `redispatch`, `protocol_correction`, `owner_direction_change`, or `other`), member steps/waves, deployed units/participants, start/end/duration, outcome, and link to the preceding round when one exists.
- **OBS-FR-056**: The reducer MUST expose the observed critical path and measured acceleration evidence: dispatch/queue wait, dispatch-tick-sampled ready-but-not-running time, dependency wait, review wait, rework time, peak parallelism, maximum observed eligible units, maximum deployed units, and captured concurrency limits. Precision/coverage MUST accompany sampled values. It MUST NOT infer that adding agents improves quality or schedule, and MUST NOT emit a productivity score.
- **OBS-FR-057**: The default CLI review brief MUST show the process reconstruction before aggregate tool totals: what Morfeo did, what Supervisor did, each execution round in order, each parallel wave and its deployed agents/units, review/rework returns, the critical path, and the measured facts relevant to an acceleration decision. Tool detail is nested under the responsible step/wave and summarized unless anomalous.

### 9.8 Improvement-decision evidence

- **OBS-FR-058**: Every trace and bound participant MUST record a field-covered configuration fingerprint: effective model/provider from request hooks; exact project-keyed system-prompt fingerprint when the full hook value is available; project-keyed observed loaded-skill-set fingerprint; project-keyed declared enabled/disabled-toolset fingerprint; project-keyed effective direct/deferred tool-surface fingerprint only when the captured snapshot is demonstrably complete; effective concurrency limits; observer package version; runtime fingerprint; and `fingerprint_key_id`. Content-derived values use HMAC-SHA-256 over canonical domain-separated input and are discarded before persistence. Each field is `exact`, `partial`, `estimated`, `unavailable`, or `not_applicable`; configured and effective values are never conflated. Fingerprints with different key IDs are not equality-comparable and key rotation is a comparison-boundary fact, not a configuration delta.
- **OBS-FR-059**: Tool/skill evidence MUST report observed tools used/failed/blocked/cancelled/timed out and observed successful skill loads. It MAY report an effective granted/never-used inventory only against a complete request-correlated direct/deferred surface snapshot. Otherwise it reports configured toolsets, observed tool count, used set, and `granted_inventory = unavailable|partial`; it MUST NOT infer `never_used`. Schema cost is `exact_bytes` for a complete canonical serialization plus `estimated_tokens` with algorithm/version, never provider-exact tokens unless the exact provider tokenizer/serialization is available. Approval/guardrail reasons use only structured native codes; missing codes remain `unknown` rather than parsed from text.
- **OBS-FR-060**: Model/context economics MUST record per request, step, and participant what public hooks expose: input/output/cache-read/cache-write/total token counts with availability, API-call attempts/retries, duration, model/provider, message/tool counts, turns, turns without semantic delta, and finish-reason distribution. Lifecycle protocol violations are reconciled from native run metadata. Invalid-argument and context compression/overflow facts are emitted only from structured native evidence; on locked Hermes `v2026.8.18`, absent dedicated signals remain `unavailable`/coverage-limited rather than inferred from error text. Prompt, response, reasoning, request body, and error text remain forbidden.
- **OBS-FR-061**: Every dispatch-tick-observed interval in which eligible work was not running MUST carry one primary class: `dependency_bound`, `capacity_bound`, `review_bound`, `owner_bound`, `provider_bound`, `unassigned`, or `unknown`, plus evidence source and sampling precision. `capacity_bound` requires a native per-profile cap signal or a captured effective global cap with saturated running count; waiting alone is insufficient. `rate_limited` maps to provider evidence, `needs_input` to owner-declared wait, and unresolved/multiple causes map to `unknown`.
- **OBS-FR-062**: Defect attribution MUST use a bounded class set (`instruction_defect`, `missing_capability`, `contract_ambiguity`, `coordination_defect`, `runtime_failure`, `policy_denial`, `genuine_discovery`, `undeclared`). Each attribution carries `native_observed`, `deterministic_derived`, `actor_declared`, `morfeo_judgment`, or `undeclared` provenance. Only `spawn_failed|crashed|timed_out` derive `runtime_failure`; only structured tool/approval denial derives `policy_denial`; `capability`, `needs_input`, `protocol_violation`, `changes_requested`, and `skipped_unassigned` remain evidence/declarations and do not mechanically prove the corresponding semantic defect. `genuine_discovery` requires explicit authorized declaration/judgment. `undeclared` is valid and not a coverage gap.
- **OBS-FR-063**: The observer MUST NOT require any declaration, extra step, or approval from any role. No lifecycle action, review, block, completion, or dispatch may fail, stall, or be withheld because observation metadata is absent, and no role's instructions may be changed to make an observation call mandatory. Missing optional semantics reduce signal quality only.
- **OBS-FR-064**: A judgment-sourced attribution MUST be visually and structurally distinguishable from a natively derived fact in every projection, consistent with the project's verified-versus-assumed discipline.
- **OBS-FR-065**: Improvement evidence MUST declare the number of traces supporting it. A signal derived from a single trace MUST be labeled as anecdotal and MUST NOT be presented as an established pattern, and `insufficient_evidence` MUST be a first-class reported value.
- **OBS-FR-066**: The observer MUST NOT emit a productivity score, worker ranking, quality judgement of a participant, or an automated configuration recommendation.

### 9.9 Deterministic CLI review brief

- **OBS-FR-067**: Every summary MUST contain one deterministic `review_brief` with a bounded verdict and primary reason code, priority-ordered findings, changes since the explicitly selected prior summary when supplied, unfinished required work/acceptance counts, evidence status, and exactly one next gate. It MUST cite source event/work/acceptance references and MUST NOT invoke a model.
- **OBS-FR-068**: Verdict precedence MUST be stable: authoritative terminal failure/cancellation/abandonment; active owner/dependency/provider/policy block; required review changes; other evidence-backed anomaly; unfinished required work/acceptance; completion candidate; verified completion; otherwise `unknown`. Ties use severity, causal position on the observed critical path, earliest causal index, then stable reference.
- **OBS-FR-069**: `--since SUMMARY_ID` MUST compare two summaries of the same trace and show only semantic changes in verdict, next gate, required work/acceptance, anomaly/bottleneck/defect set, process structure, comparable configuration fingerprint, or coverage. Token/tool-count growth alone is not a semantic change unless it creates an anomaly or coverage transition. Different fingerprint-key epochs are reported as a comparison boundary rather than a configuration change; incompatible summary schemas return a bounded comparison error.
- **OBS-FR-070**: `--watch` MUST perform incremental local ingest/reduction and emit only when the summary ID, verdict, priority findings, coverage state, or next gate changes. It MUST NOT tail raw journal events, print unchanged heartbeat/request/tool activity, busy-loop, or full-replay on every check. The baseline fallback polls directory/segment metadata no more than once per second, backs off to at most one check every five seconds while unchanged, and resets after change; a platform notification optimization may replace polling only with identical semantics.

### 9.10 Packaging and runtime installation

- **OBS-FR-071**: Observation MUST ship inside the single `aether-agents` wheel and share the Aether product version. No `aether-observer` distribution, separate repository, daemon, or independently versioned observer artifact may be introduced in 1.0.
- **OBS-FR-072**: `pyproject.toml` MUST declare exactly one observer entry point in group `hermes_agent.plugins`: `aether-contract-observer = "aether_agents.observation.capture.hermes_plugin"`. The target module exposes `register(ctx)` and registration is idempotent per Hermes plugin-manager generation.
- **OBS-FR-073**: The exact staged manager wheel MUST also be installed with `--no-deps` inside each staged versioned Hermes runtime. Activation MUST verify distribution name, normalized version, pre-build identity, entry-point target, installed-file fingerprint parity, transition-record wheel filename/SHA-256, and that every participating profile enables the expected plugin name before switching the active release. The wheel MUST NOT contain its own final digest.
- **OBS-FR-074**: Manager modules MUST remain importable and capable of doctor/rollback when Hermes is missing or broken. Static import tests and isolated-venv execution MUST prove that manager modules never import Hermes and that the plugin adapter never imports manager command, transition, release, service, update, rollback, or authentication modules.
- **OBS-FR-075**: The observer's normative schemas have one editable source under `specs/002-aether-contract-observation/contracts/`. Wheel/sdist build MAY copy those bytes into package resources, but packaging tests MUST prove byte-for-byte equality and digest parity; no second hand-maintained schema copy is permitted.
- **OBS-FR-076**: Installing the same wheel in the runtime MUST NOT make its runtime-local `aether` script authoritative or place it on the public manager path. The manager environment remains the sole public CLI owner; the runtime copy exists only to provide the entry-point plugin and shared observation modules.

### 9.11 Context, evolution, and source integrity

- **OBS-FR-077**: Every project event and summary MUST use a canonical lower-case UUID matching the initialized portable project and exact Aether registry/board mapping. The context resolver precedence and refusal rules in OBS-D-022 are normative. Unresolved/conflicting context emits no project event and never writes into a guessed project's directory.
- **OBS-FR-078**: Owner-message candidates are not durable events. Trace materialization, origin selection, null `started_at`, append-only late binding, continuation, and no-auto-merge behavior MUST follow OBS-D-023. Any origin-dependent duration is null when `started_at` is null.
- **OBS-FR-079**: `trace_id`, `producer_epoch`, `producer_seq`, and deterministic-or-random `event_id` MUST follow OBS-D-024. PID, wall time, profile, or path cannot be a durable identity. Reconciliation MUST deduplicate complete native identities across captured and reconciled events.
- **OBS-FR-080**: Journal source kinds and diagnostic ownership MUST follow OBS-D-025. Reduction MUST be side-effect-free with respect to all source segments.
- **OBS-FR-081**: Event/schema upcasters, projection versioning, rollback preservation, quarantine indexing, historical summaries, and semantic-comparison compatibility MUST follow OBS-D-026. No update, rollback, rebuild, or compaction may rewrite retained event bytes.
- **OBS-FR-082**: Hook-path append and out-of-band flush semantics MUST follow OBS-D-027. No `fsync`, compression, SQLite transaction, native-store reconciliation, or full schema migration may execute synchronously inside a Hermes callback.
- **OBS-FR-083**: Every content-derived configuration fingerprint MUST follow OBS-D-028 and carry its key ID. Fingerprint keys MUST NOT enter journal events, summaries, logs, public provenance, release artifacts, repositories, or unprotected exports. Key loss/rotation starts a new epoch with explicit coverage and preserves old events.
- **OBS-FR-084**: Closed-segment compaction MUST follow OBS-D-029. The manifest and both hashes are required; active, unverified, corrupt, or unknown-schema segments cannot have their source JSONL removed.
- **OBS-FR-085**: Before implementation fan-out, the bounded spike in OBS-D-030 MUST run against a recreated clean checkout at the release-locked Hermes tag/commit. The patched local runtime cannot substitute as upstream evidence. Results and machine description become implementation evidence, not a silent design mutation.
- **OBS-FR-086**: Every producer MUST hold the epoch advisory lock for its lifetime and release it only after clean segment close. An acquireable epoch lock with a remaining active segment MUST produce an unclean-tail diagnostic and incomplete coverage even when no sequence gap is visible; PID reuse or absence of a later event MUST NOT be used to infer clean shutdown.

## 10. Duration algorithm

When `started_at` is exact, the lifecycle interval is `[started_at, closed_at || as_of]`, where `as_of` is the latest included event timestamp and therefore deterministic for the event set:

1. normalize all timestamps to UTC while preserving source offset metadata;
2. union all linked active intervals (`tool`, explicit contract action, reducer-recognized participant span);
3. union owner waits from `clarification.requested` to its linked `clarification.resolved`;
4. union dependency/external waits from explicit wait markers and bound blocked intervals;
5. union review waits from `review.requested` to approved/changes-requested/terminal review state;
6. resolve overlap precedence as owner wait > dependency/external wait > review wait > active for reporting categories, while preserving overlap counters separately;
7. calculate `unclassified_ms = wall_ms - union(classified intervals)`;
8. reject negative or impossible intervals into a coverage gap rather than repairing timestamps silently.

Parallel spans increase call counts but not wall duration. Contract creation is `[started_at, persisted_at]`; handoff latency is `[persisted_at, handed_off_at]`; dispatch latency is `[handed_off_at, execution_started_at]`; execution is `[execution_started_at, completed_at || terminated_at || as_of]`. For a completed pipeline trace with exact phase boundaries these ordered phases MUST exactly sum to `wall_ms`; reversal or unexplained overlap is a clock/causality gap, not silently repaired. Review wait is an interval partition inside execution, not an additional phase duration. When `started_at` is null, `wall_ms`, contract-creation duration, time-to-first-action, time-to-executable, time-to-completion/termination, and every whole-lifecycle partition that depends on the origin are null with incomplete origin coverage. Later independently bounded phases remain measurable and no materialization timestamp substitutes for the missing origin.

## 11. Flow algorithm

### 11.1 Normalized state signature

```text
SHA256(canonical-json({
  accepted_decision_ids,
  unresolved_material_ambiguity_ids,
  evidence_refs,
  invariant_results,
  current_contract_artifact_sha256,
  required_work_units: [{task_id, relation, task_status, latest_run_outcome}],
  required_reviews: [{task_id, state}],
  acceptance_criteria: [{criterion_ref, state, evidence_refs}]
}))
```

Arrays are sorted; duplicate references are removed; timestamps and participant identities are excluded. This makes state equality deterministic.

### 11.2 Classification order

For each transition, the reducer applies this precedence:

1. owner-authorized decision supersession;
2. authorized reversion;
3. explicit technical retry;
4. regression;
5. useful iteration;
6. zero-delta cycle;
7. semantic loop once the same zero-delta cycle occurs consecutively twice.

A transition receives one primary classification and may carry secondary evidence flags. Classification never changes task status or artifact content.

## 12. Persistence and retention

- Observation state uses the XDG state root selected by Aether setup, scoped by stable canonical project UUID. Content-free unresolved-context health counters live outside project directories and never contain message/task/session identifiers.
- The repository stores no generated observation database or journal.
- Every event, summary, hash, and coverage declaration is retained indefinitely. No automatic time-based pruning exists, and the reducer MUST NOT delete source events to reclaim space.
- Every event MUST preserve its UTC instant, its originating local offset, and a monotonic ordering reference, so an archived trace remains correctly ordered and correctly dated years later.
- Only closed, verified segments MAY be compacted. Compaction uses the deterministic gzip/manifest/atomic-transition protocol in OBS-D-029 and MUST remain lossless with respect to the exact uncompressed event bytes and byte-equivalent summary replay. Active, corrupt, unknown-schema, unverified, or interrupted temporary segments retain their source JSONL.
- Retained history MUST be indexed for retrieval by project, trace, contract, time range, participant, configuration fingerprint, and defect/bottleneck class, so later comparison does not require a full scan.
- Storage growth and health MUST be reportable: `aether doctor` surfaces observation storage size, event count, active/closed/archive/quarantine counts, unresolved-context/IO-loss counters, projection versions, fingerprint-key epochs, and archive verification state so the owner can decide on compaction or protected export before it becomes a surprise.
- `aether uninstall` preserves observation state by default. `aether uninstall --purge` may remove it only under the existing explicit purge contract, which remains the sole deletion path.

## 13. Public interfaces

### 13.1 CLI

```text
aether observe [REF] [--project PATH] [--since SUMMARY_ID] [--watch] [--json]
```

- `REF` resolves an exact `trace_id`, `contract_id`, or bound `task_id`. Without `REF`, one open trace is selected; zero traces produces an empty-state report and multiple open traces produce a bounded ambiguity error rather than guessing.
- Default human output is one coherent review brief for Morfeo. It prioritizes conclusion, a causal step/round/wave reconstruction, current state, verified progress, blockers/anomalies, unfinished required work and acceptance, critical-path/acceleration evidence, execution quality, evidence coverage, and the next decision required; it does not force the caller to assemble atomic section queries.
- `--since SUMMARY_ID` emphasizes semantic changes from one prior deterministic summary.
- `--watch` refreshes only when the summary ID, anomaly set, or next gate changes; it is not a raw journal tail.
- `--watch` and `--json` are mutually exclusive. Since the stable JSON contract emits
  exactly one envelope, the combination returns one bounded `WATCH_JSON_UNSUPPORTED`
  error envelope instead of changing `--json` into an undocumented NDJSON stream.
- `--json` emits the standard Aether CLI envelope and, for a resolved summary, its
  `data` is exactly `{ "state": "summary", "summary": <observation-summary> }`.
- With no open trace, JSON and human output are projections of the same empty state:
  `data` is exactly `{ "state": "empty", "summary": null }`; no absent or empty
  `data` object is used as an implicit discriminator.
- This closes the previously underspecified `{}` empty payload without changing the
  standard envelope's `schema_version: 1`: consumers MUST discriminate on
  `data.state`, accept `empty` and `summary`, and treat `{}` as non-conforming.
- The command is read-only and valid even when the Hermes service is stopped, provided local state is readable.

### 13.2 Optional semantic checkpoint sink

The observer library exposes a bounded internal checkpoint sink to other Aether product components; it is not an agent-facing required tool. Its enum is limited to semantic facts an existing canonical contract write or closing verification already owns. The caller cannot supply role, free text, content, or arbitrary payload. A checkpoint is written only after the authoritative action succeeds, cannot modify that source, and failure changes coverage only. Mechanical lifecycle remains hook-derived.

### 13.3 Deferred read surfaces

A separate read-only agent query tool and dashboard/API are explicitly deferred beyond 1.0. Morfeo inspects observation state by invoking `aether observe` through its existing terminal capability. Adding another read surface later requires an owner-approved contract revision and MUST reuse the same deterministic summary rather than define a second observation meaning.

## 14. Required executable-contract invariants

A contract may emit `contract.executable` only when:

- **OBS-INV-001**: the originating owner objective is referenced;
- **OBS-INV-002**: every material ambiguity is resolved or explicitly retained as an owner decision gate;
- **OBS-INV-003**: every accepted owner clarification is persisted in its canonical artifact;
- **OBS-INV-004**: delegated decisions state their supporting assumptions;
- **OBS-INV-005**: scope and non-scope are explicit;
- **OBS-INV-006**: acceptance criteria are testable;
- **OBS-INV-007**: the testing standard is explicitly resolved;
- **OBS-INV-008**: authority and protected effects are explicit;
- **OBS-INV-009**: no unresolved contradiction remains between owning canonical artifacts;
- **OBS-INV-010**: the implementation recipient and completion boundary are named when a handoff is intended.

The observer reports invariant facts supplied by the contract-authoring process; it does not decide product intent.

## 15. Testing standard

This standard is an explicit delegated design decision for the baseline, not a project-wide default.

### 15.1 Deterministic tests

The implementation MUST include fixed synthetic event fixtures and golden summary JSON for at least:

1. straight-line contract creation;
2. owner clarification wait and later response;
3. owner decision supersession;
4. parallel tool calls with exact totals and interval union;
5. tool failure plus linked technical retry;
6. useful investigation/revision iteration;
7. two-cycle semantic loop;
8. unauthorized regression;
9. authorized and unexplained reversion;
10. subagent participation;
11. process restart and trace resume;
12. missing/corrupt event and explicit coverage gap;
13. lossless closed-segment compaction preserving byte-equivalent replay without event pruning;
14. malicious/raw-content-shaped metadata rejected by schema/allowlist;
15. native `post_tool_call` payload projection proving `args`, `result`, `error_message`, `middleware_trace`, and `user_task` are absent on disk;
16. `blocked`, `cancelled`, `timed_out`, `failed`, `completed`, and unknown tool outcomes remain distinct;
17. process death after `pre_tool_call` produces one unpaired-span gap;
18. producer-local ordering remains deterministic when wall clocks collide or move backwards;
19. observer callbacks/checkpoint sinks produce zero recursive self-observation spans;
20. one trace resumed across collector/runtime versions reports all compatibility pairs and remains reducible or declares a coverage gap;
21. global, per-name, and per-actor tool count/duration equations reconcile exactly.
22. one complete Morfeo → Supervisor → Implementer → review → integration → Morfeo verification trace closes as completed;
23. root task done while one required child remains open does not close;
24. blocked task resumes in the same trace and preserves waiting duration;
25. crashed/timed-out/failed/reclaimed runs followed by retry remain one trace and never close prematurely;
26. review changes-requested followed by rework and approval records a regression/useful iteration without duplicating the unit;
27. a dynamically created same-project descendant inherits the bound graph through its parent edge while unrelated same-project work is excluded;
28. every acceptance criterion requires evidence before completion;
29. cancellation, abandonment, and terminal failure close distinctly and never satisfy acceptance;
30. liveness, activity, verified progress, waiting, anomalies, and termination remain independent under heartbeat-only activity.
31. an observed create result or strict in-call correlation token resolves the root, and descendants resolve through parent edges before their first worker event;
32. missing/duplicate/reused/cross-project correlation tokens/results remain unbound with explicit ambiguity coverage and never block native creation;
33. configuration fingerprint fields preserve `exact|partial|estimated|unavailable|not_applicable` coverage and never conflate declared toolsets with an effective surface;
34. `never_used` is produced only from a complete request-correlated direct/deferred surface snapshot; partial snapshots produce no negative claim;
35. request token/cache/duration/finish-reason economics reconcile against hook fixtures while unavailable fields remain explicit;
36. dispatch-tick sampling reconstructs dependency/capacity/review/owner/provider/unassigned intervals with precision and uses `unknown` for competing causes;
37. only the closed native rules in OBS-FR-062 derive runtime/policy defects; semantic classes remain declared, judgment, or undeclared;
38. a complete pipeline lifecycle runs with no semantic checkpoint and no changed role instruction, ending with partial semantic coverage rather than blocking;
39. missing dedicated context-compression/overflow or exact tool-surface hooks remain `unavailable` on the locked runtime instead of being inferred from text.
40. review-brief verdict/finding precedence is deterministic under simultaneous block, review, anomaly, and unfinished-work facts;
41. `--since` reports semantic changes and suppresses token/tool-count-only growth;
42. `--watch` emits on verdict/finding/coverage/next-gate change and suppresses unchanged heartbeat/request/tool activity.
43. one staged `aether-agents` wheel is installed into an isolated manager venv and an isolated Hermes runtime venv; both installed distributions match name, normalized version, pre-build identity, and installed-file fingerprint, while external provenance/transition evidence identifies the one source wheel filename/SHA-256;
44. the manager CLI, doctor, and rollback import and execute with Hermes deliberately absent/broken;
45. the runtime discovers exactly `aether-contract-observer` from `aether_agents.observation.capture.hermes_plugin`, enables it for every participating profile, and registers each hook once per plugin-manager generation;
46. import-graph tests reject any manager→Hermes import and any plugin-adapter→manager-command/transition/release/service/auth import;
47. wheel and sdist observer schemas are byte-identical to the single normative source and match its digest;
48. the runtime-local `aether` script is never selected as the public manager executable and does not shadow the `uv tool` command.
49. exact task/run mapping outranks verified session/launch binding; agreeing sources resolve one UUID, while unresolved/conflicting/cross-project sources emit no project event and increment content-free health counters;
50. one exact owner-message candidate binds as origin, zero/multiple candidates produce null `started_at` and null origin-dependent durations, continuation resumes only through exact trace/contract/work references, and two traces never auto-merge;
51. process restarts allocate new producer epochs, sequences never cross epochs, deterministic native event identities deduplicate hook/reconciliation duplicates, and incomplete identities are never fuzzy-matched;
52. reduction over corrupt/unknown input produces derived diagnostics without changing source-segment bytes or appending reducer events;
53. v1 historical events upcast deterministically into the current reducer, an older rollback preserves unknown newer bytes/projections, and forward re-update reingests them without journal migration;
54. hook callbacks perform no `fsync`, compression, SQLite transaction, native-store reconciliation, or schema migration; async flush success/failure and bounded teardown preserve fail-open behavior;
55. content-derived fingerprints are HMAC-SHA-256 domain-separated by field and project key epoch; different key IDs are incomparable, rotation is not a configuration change, and key bytes never enter public/durable observation payloads;
56. deterministic gzip compaction proves manifest/hash/sequence/count parity, atomic crash recovery at each transition, no active-segment compaction, and no source deletion before verified replay;
57. `--watch` performs incremental bounded polling/backoff, stays silent under non-semantic churn, and never full-replays on each check;
58. an event canonical line over 65,536 bytes is rejected before append and cannot create a partial line.
59. a producer crash after its final visible append but before clean close leaves contiguous sequence numbers; the released advisory lock plus active segment still produces an unclean-tail gap, preserves exact bytes, and never blocks native work.

Golden tests MUST prove byte-equivalent canonical JSON across repeated reductions.

### 15.2 Integration tests

Integration tests MUST exercise public Hermes plugin hooks against the release-locked runtime and prove:

- the reproducible locked qualification corpus runs at least 119 observation tests against the exact clean `v2026.8.18` checkout rather than a mutable or dirty runtime;
- one real `PluginContext`/`PluginManager` instance exposes 22 registered callbacks, captures tool and API events without raw prompt/response content, and reports zero hooks after unload;
- hook registration and teardown;
- pre/post tool correlation with native `task_id`, `session_id`, `turn_id`, `api_request_id`, and `tool_call_id`;
- profile identity resolution from the active `HERMES_HOME`;
- subagent parent/child session correlation without persisting goal, summary, or tool history content;
- session/message/task/run linkage;
- root binding from create result/strict in-call token and descendant inheritance through durable parent edges;
- task-return correlation, worker-start resolution, and ambiguous-idempotency refusal without a pre-create observation action;
- native task/run/review state reconciliation through final Morfeo verification;
- pre/post/error API correlation and model/context usage projection;
- configuration fingerprint field coverage and configured-versus-effective distinction;
- dispatch-tick capture after the native lock plus sampled bottleneck attribution;
- deterministic review-brief verdict, finding ordering, semantic-diff, and next-gate projection;
- dual isolated installation of one wheel, official entry-point discovery, per-profile enablement, and import-boundary enforcement;
- release-lock/doctor verification of manager/runtime build/installed-file parity plus external provenance/transition binding to one wheel and runtime-local CLI non-shadowing;
- byte-equivalent normative schemas in source, wheel, and sdist;
- concurrent profile/process journal segments;
- crash recovery and idempotent ingestion;
- unclean producer-tail detection with a remaining active segment, released epoch lock, and no visible sequence gap;
- exact project-context resolution across task, run, session-project, and manager-launch cases without cross-project leakage;
- origin candidate selection, ambiguous origin, continuation, late binding, and no-auto-merge behavior against native SessionDB identifiers;
- update/rollback/re-update across event, summary, and projection versions with immutable journals and preserved unknown-newer bytes;
- project fingerprint-key creation/permissions, private backup, rotation/key-loss boundary, and rejection from every public artifact/log/payload;
- deterministic closed-segment compaction and recovery from every interrupted temp/rename/verification stage;
- CLI human and JSON projections agree on one summary ID and underlying facts;
- no outbound/non-loopback network access during collection, reduction, or CLI query;
- collector failure does not block a contract action;
- coverage becomes incomplete when events are dropped;
- POSIX permissions and repository exclusion;
- the packaged 1.0 observer exposes no dashboard/API or separate read-only agent query tool;
- proof that Aether observation does not enable or write Hermes shared metrics, Langfuse, NeMo Relay, ATIF, or ATOF.

### 15.3 Performance and resilience gates

Before broad implementation fan-out, a disposable spike MUST recreate the clean release-locked Hermes checkout and measure native callback projection/validation/append, out-of-band flush, incremental reduction at 10,000 and 100,000 events, corrupt tails, and ENOSPC. The patched local runtime is not upstream evidence. The full implementation MUST then satisfy, under the supported local stress fixture:

- collector callback overhead MUST be `<= 5 ms` at p95 and `<= 20 ms` at p99; asynchronous flush/fsync is measured separately and no synchronous flush is excluded from the callback result because none is permitted there;
- the benchmark MUST measure the native in-process plugin callback; a shell-hook subprocess result is invalid;
- ordinary event recording MUST add no network call and no model call;
- reduction of `10,000` retained events MUST finish in `<= 2 s` on the release validation machine, with the machine description recorded;
- the 100,000-event spike result MUST be recorded for scaling evidence even though 1.0 sets no separate pass/fail threshold for it;
- a full/corrupt journal MUST degrade coverage, not crash Hermes or prevent contract persistence.

### 15.4 Controlled real trace

Before `1.0.0-rc.1` qualification, the release procedure MUST capture one real local owner-approved contract trace using the packaged profiles and locked Hermes runtime. The produced summary MUST be compared against SessionDB, Kanban, artifact hashes, and actual tool outputs. Provider spending or reauthentication remains subject to the existing owner gate; it is never silently acquired or widened.

## 16. Acceptance criteria

Aether Contract Observation is complete for 1.0.0 only when:

- [ ] all OBS-FR requirements pass automated validation;
- [ ] all three normative JSON Schemas validate every fixture and reject forbidden arbitrary payloads;
- [ ] one summary reports the complete owner-message-to-terminal lifecycle and all four owner-required dimensions;
- [ ] exact tool totals reconcile with the trace's native tool records or visibly declare a coverage gap;
- [ ] owner waits, active time, external waits, and unclassified time reconcile to wall duration without double-counting;
- [ ] contract-creation, routing, execution, review, and total-lifecycle durations reconcile without premature closure;
- [ ] root completion cannot hide an open required descendant, review, or acceptance criterion;
- [ ] blocked/crashed/timed-out/retried work remains in the same trace and only explicit terminal resolution closes it;
- [ ] serial, parallel fan-out/fan-in, review-rework, resumption, redispatch, and protocol-correction fixtures reconstruct the exact ordered steps, waves, rounds, deployed participants/units, barriers, and critical path;
- [ ] queue, ready-but-not-running, dependency, review, rework, peak-parallelism, eligible-unit, deployed-unit, and captured-capacity facts reconcile without producing an automatic productivity or acceleration score;
- [ ] every trace and bound participant records a field-covered configuration fingerprint, and two traces with different exact fields are distinguishable without reading instruction, skill, or schema content;
- [ ] tool/skill use and failures are exact where observed; granted/never-used inventory and schema cost declare completeness/estimation and make no negative claim or removal recommendation from partial data;
- [ ] model/context economics reconcile with native hook usage data, unavailable context signals remain explicit, and no prompt, response, reasoning, request body, or error text is stored;
- [ ] every dispatch-tick-sampled non-running eligible interval carries one evidenced attribution class or `unknown`, and `capacity_bound` is evidenced by a native cap/saturation signal;
- [ ] the JSON summary and default human CLI share one deterministic review brief with priority findings, semantic changes, unfinished counts, evidence status, and exactly one next gate; watch mode stays silent for non-semantic churn;
- [ ] a complete pipeline trace executes end to end with no observation declaration supplied at all, proving that no lifecycle action depends on observation metadata;
- [ ] judgment-sourced attributions are structurally distinguishable from natively derived facts, and single-trace signals are labeled anecdotal;
- [ ] retention keeps every event with UTC instant and local offset; only verified closed segments compact through the deterministic manifest/hash/atomic protocol; interrupted/unknown/corrupt sources remain intact; and no automatic pruning path exists;
- [ ] only `completed` represents fulfilled acceptance; cancelled, abandoned, and failed outcomes remain distinct;
- [ ] iterations, retries, loops, regressions, and reversions are deterministically distinguishable;
- [ ] a changed owner decision is not misclassified as regression;
- [ ] no raw content or secret-shaped field is stored;
- [ ] real native payload fixtures prove that dangerous keys are dropped before every persistence/logging boundary;
- [ ] CLI human and JSON projections expose the same summary ID and underlying values;
- [ ] one staged immutable `aether-agents` wheel is installed in both manager and runtime environments; distribution/version/build identity/installed-file fingerprints agree, and external provenance plus the transition record identify its filename/SHA-256 without a circular self-digest;
- [ ] all participant profiles enable the one official entry-point observer and report the same distribution version/build identity without per-profile plugin source copies;
- [ ] source, wheel, and sdist contain byte-identical normative observer schemas, and the runtime-local `aether` script cannot shadow the public manager command;
- [ ] Hermes shared metrics and optional remote observability remain unchanged from their prior disabled/enabled state;
- [ ] observer failure does not block legitimate contract work;
- [ ] release lock, upgrade, rollback, uninstall-preserve, and purge behavior include observer state;
- [ ] every project event resolves through the exact context chain to one canonical UUID, while unresolved/conflicting contexts create no cross-project write and remain visible through content-free health/coverage evidence;
- [ ] exact, ambiguous, resumed, new-objective, late-bound, and terminal-trace origin fixtures prove null-safe timing and no automatic trace merge;
- [ ] producer/event identity and reconciliation remain idempotent across process restart, lost callbacks, and repeated native-store scans;
- [ ] every released event schema remains replayable through deterministic upcasters; rollback preserves unknown newer bytes/projections and forward update reingests them without journal mutation;
- [ ] project-keyed fingerprints are comparable only within one key epoch, rotation is not a configuration delta, and key material survives only through private local recovery/protected export paths;
- [ ] callback performance includes all synchronous work and proves that `fsync`, compaction, SQLite, reconciliation, and migration remain off the agent path;
- [ ] an unclean active producer epoch is detected by advisory-lock ownership and remains coverage-incomplete even when its visible sequence has no internal gap;
- [ ] the clean-checkout spike records the accepted latency and scaling evidence before implementation fan-out;
- [ ] the controlled real trace is reviewed against durable sources;
- [ ] issue #195 is closed with evidence rather than carried as an accepted 1.0 limitation.

## 17. Implementation handoff contract

When the owner authorizes implementation, Morfeo MUST hand Supervisor exactly one objective:

> Implement Aether Contract Observation as specified here. First execute the clean-checkout qualification spike and return any failed budget as a contract finding. Then deliver the normative event/summary/segment-manifest schemas; exact project-context resolver and bounded owner-message correlation; restart-safe trace/producer/event identity; product-owned Hermes observer plugin plus optional internal checkpoint sink; append-only source journal with out-of-callback flusher; pure schema upcasters and versioned rebuildable projections; project-keyed fingerprint epochs; deterministic closed-segment compaction; deterministic full-lifecycle reducer; bound task/run/review/acceptance graph; causal semantic steps, parallel waves, execution/rework rounds, critical-path and acceleration evidence; field-covered configuration/tool/model evidence; and one Morfeo-oriented `aether observe` review brief with human and JSON projections, packaging/lifecycle integration, tests, and release evidence. Do not ship a dashboard/API, cross-project comparison, or separate read-only agent query tool in 1.0. Trace each contract from its exactly linked owner-originating message when available through verified completion or explicit non-success terminal resolution where authoritative evidence exists; otherwise preserve null/unknown/partial state without fuzzy matching or trace merging. Preserve Kanban/SessionDB/canonical-artifact authority and immutable journal bytes; add no remote telemetry, mandatory role action, synchronous durability/reduction work in callbacks, or downstream Hermes core patch.

Supervisor owns decomposition and routing. Implementers do not redefine schema, lifecycle, flow classification, retention, authority, or test gates. Any discovered incompatibility that requires one of those decisions returns to Morfeo and the owner as a contract change.

## 18. Required evidence at completion

The implementation handoff back to Morfeo MUST include:

- changed-file and component inventory;
- event, summary, and segment-manifest schema validation output;
- deterministic/golden test results;
- clean-checkout spike plus integration/performance results with environment description;
- update/rollback/re-update evidence proving immutable source bytes, preserved unknown-newer input, per-version projections, and key epochs;
- privacy evidence proving fingerprint keys never entered source events, summaries, logs, release artifacts, transition records, or ordinary export;
- real-trace summary ID and reconciliation report;
- repository diff and clean generated-state check;
- release package install/update/rollback/uninstall evidence;
- open findings, each linked to a GitHub issue;
- explicit statement that no remote telemetry, credential change, or downstream core dependency was introduced.
