# Research — Aether Contract Observation

**Research date**: 2026-08-21; deployed-runtime and owner-approved full-lifecycle amendments 2026-08-22
**Status**: accepted evidence baseline for [`spec.md`](spec.md)
**Issue**: [#195](https://github.com/DarkArty07/aether-agents/issues/195)

## 1. Question

Can Aether reconstruct exact contract duration, participant actions, tool totals, and semantic flow locally without introducing a second workflow authority or modifying Hermes core?

## 2. Current authoritative surfaces

Repository inspection at Aether commit `47e26c5` found:

- `specs/r11-evidence-and-observability/spec.md` already defines SessionDB, Kanban, logs, and tool discovery as native observability surfaces.
- `specs/r4-hermes-boundary/spec.md` reserves task lifecycle, retries, persistence, and runtime observability to Hermes while allowing stable product-owned adapters and plugins.
- `specs/001-aether-v1-productization/spec.md` previously treated issue #195 as a known non-blocking limitation and prohibited Aether-owned analytics/telemetry.
- `specs/r13-synthesis-and-release/spec.md` previously allowed #195 to remain an explicit accepted limitation at release.

Owner decision on 2026-08-21 changes the release relationship: a bounded local contract observer is required before `1.0.0`. Remote analytics and hosted telemetry remain outside scope.

## 3. Hermes surfaces observed

An earlier inspection looked at Aether's transitional runtime checkout at `home/.venv-hermes/src/hermes-agent`, base commit `411903b6fa258f81afcc3869eb615f6218e1776a`. That checkout contains pre-existing local Aether patches and is retained here only as a historical antecedent used to distinguish local behavior from upstream. It is non-qualifying and supplies no compatibility, implementation, test-count, callback, capture, unload, or release evidence for this contract. The current source claims below are governed by the exact clean public checkout recorded in §7.2. No source file was modified by this research.

### 3.1 Lifecycle and tool payload

- `hermes_cli/plugins.py:156-355` declares native hooks for tool, model, API, session, approval, subagent, command, skill, and Kanban lifecycles. `256-347` names Kanban precisely: `kanban_task_claimed/completed/blocked` plus `on_kanban_worker_spawned/exited/stale_claim/task_updated/dispatch_tick`, and documents sensitive `summary`, `reason`, `workspace_path`, and dispatcher-result fields. No per-heartbeat or task-timeout hook exists; those facts remain `task_runs` reconciliation inputs.
- `hermes_cli/lifecycle.py:11-37` dispatches first-party observation and plugin hooks and exposes `has_hook()` as the fast-path gate.
- `model_tools.py:1136-1187` emits terminal tool facts with `task_id`, `session_id`, `turn_id`, `api_request_id`, `tool_call_id`, `duration_ms`, `status`, and `error_type`. It also passes raw `args`, `result`, and `error_message`; those fields are prohibited from the Aether journal and must be dropped before writing.
- `model_tools.py:1471-1489` measures dispatch with a monotonic clock and binds the current correlation identifiers before registry dispatch.
- `tools/registry.py:1102-1136` passes `task_id`, `session_id`, and other bounded host context to plugin tool handlers and normalizes exceptions to a tool result.
- `hermes_cli/plugins.py:5071-5080` filters additive payloads for narrow callback signatures and isolates every plugin callback exception from the core loop.

### 3.2 Native extension surfaces

- `hermes_cli/plugins.py:1697-1789` supports tool registration without overriding core tools.
- `hermes_cli/plugins.py:2058-2096` supports native CLI subcommands; `2100-2124` separately supports in-session slash commands.
- `hermes_cli/plugins.py:3109-3132` supports lifecycle-hook registration.
- `hermes_cli/plugins.py:1315-1385` provides profile-scoped, quota-bounded JSON plugin state. It is suitable for small cursors/settings, not the observation journal.
- `hermes_cli/plugins.py:1621-1658` provides unload cleanup and supervised async tasks.
- `agent/agent_init.py:1483-1488` discovers plugins during agent setup; `hermes_cli/plugins.py:5821-5851` also lazy-discovers them across non-interactive delivery surfaces.
- `hermes_cli/web_server.py:17396-17499` discovers dashboard manifests and safe in-directory API files. `18016-18131` imports enabled user-plugin routers under `/api/plugins/<name>/`, with runtime enable/disable and path-traversal gates. Therefore the dashboard can be extended without a new listener or core patch.

### 3.3 Participants and existing observability

- `hermes_state_common.py:259-318` stores session identity, parent session, timestamps, counters, activity, tokens/costs, and profile; `320-344` stores integer message ID, role, timestamp, tool name/call ID, plus sensitive content/reasoning/tool-call JSON fields. There are no durable `turn_id` or `api_request_id` columns in these tables.
- `hermes_cli/kanban_db.py:1461-1468` stores task events with integer `run_id`; `1477-1496` stores each run attempt with integer ID, profile, status, PID, heartbeat, start/end, outcome, summary, metadata, and error. The observer uses the identifiers/status/timing fields but excludes the text/blob fields.
- `hermes_cli/profiles.py:1873-1897` resolves the active profile from `HERMES_HOME`.
- `tools/delegate_tool.py:1927-1940` emits parent/child session and role identity on `subagent_start`; `3284-3296` emits child status and duration on `subagent_stop`. Child goal, summary, and tool-history content are present in native payloads and are therefore explicitly dropped.
- `agent/session_activity.py:1-6` and `21-29` define durable activity as an observation-only heartbeat with bounded description/provenance and a 60-second minimum cadence. It is liveness/activity evidence, not semantic progress.
- `hermes_cli/observability/shared_metrics_contract.py:809-853` already provides bounded tool category and outcome normalization, including `blocked`, `cancelled`, `failed`, `success`, `timed_out`, and `unknown`.
- `hermes_cli/observability/relay_shared_metrics.py:1068-1101` shows shared metrics are profile-owned and enabled only by explicit `telemetry.shared_metrics.enabled: true`; `1104-1143` projects native hooks when enabled and isolates failures.
- `hermes_cli/observability/shared_metrics.py:48-61` persists aggregate allowlisted metrics under `telemetry/shared_metrics`. These aggregates do not preserve Aether contract causality and are not the observer journal.
- optional Langfuse and NeMo Relay plugins are explicitly opt-in (`plugins/observability/langfuse/plugin.yaml`, `plugins/observability/nemo_relay/plugin.yaml`) and may export richer traces. Aether observation must neither require nor activate them.

These findings strengthen the product-plugin design, eliminate the need for a shell hook, establish an exact native payload allowlist, and identify reusable bounded normalizers. They do not justify changing Hermes core or treating Hermes telemetry as contract authority.

Native CLI registration was verified but is not selected for the public query command: that API produces `hermes <subcommand>`, while the accepted product surface is `aether observe`. The Aether manager and plugin instead share one query/reducer library.

### 3.4 In-call work binding without an observation step

The locked runtime exposes claim/complete/block and worker lifecycle hooks but no task-created hook (`hermes_cli/plugins.py:258-333`). A binding observed only after `kanban_create` can therefore lose its callback before a dispatcher claim; that is a recovery problem, not justification for a required pre-create telemetry action.

The existing create tool supplies a safe bridge without a Hermes core patch: it accepts `idempotency_key` (`tools/kanban_tools.py:1397`), persists it in `create_task` before returning (`tools/kanban_tools.py:1444-1473`), and returns the created `task_id` (`tools/kanban_tools.py:1474-1483`). The Aether wrapper can attach a deterministic opaque `aether.obs.v1:<trace_ref>:<unit_ref>` token inside the same create call; `post_tool_call` captures the returned task ID, and a lost callback is reconciled later from the strict token plus durable parent edges. No title, body, workspace, or arbitrary idempotency value enters the journal, and no agent performs a separate reservation.

Hermes explicitly documents that the idempotency lookup is not a uniqueness constraint and concurrent creators may both insert (`hermes_cli/kanban_db.py:3419-3432`). The design therefore refuses automatic binding when one token maps to zero or multiple live tasks and reports reconciliation ambiguity instead of choosing by recency. Native descendants inherit trace membership through parent edges; semantic acceptance remains separate and may be `unknown`.

## 4. Alternatives considered

### A. Reconstruct only from SessionDB and Kanban

Rejected as the complete design. These stores provide durable native facts but do not encode Aether contract lifecycle markers, accepted/superseded decisions, semantic ambiguity state, or contract revision hashes with sufficient deterministic causality.

### B. Parse logs after completion

Rejected. Logs are diagnostic, vary in shape and retention, may contain unsafe text, and cannot be the canonical source for exact flow classification.

### C. Use an LLM to summarize the session

Rejected as the authoritative engine. It is not deterministic, may omit failed paths, can confuse liveness with progress, and cannot guarantee exact totals. Optional prose may paraphrase a deterministic summary only.

### D. Add a new workflow/telemetry backend

Rejected. It would duplicate Hermes authority and violate the current boundary. Remote ingestion is also unnecessary for the owner's local first release.

### E. Public-hook collector plus typed Aether markers and local reducer

Accepted. It preserves native authorities, records only the missing Aether-owned semantics, supports exact local counting, and can be packaged without a Hermes core patch.

### F. Reuse Hermes shared-metrics SQLite as the observer

Rejected as the contract store. Shared metrics are explicit opt-in telemetry, aggregate dimensions rather than preserving event causality, and have an export/outbox lifecycle unrelated to contract evidence. The bounded category/outcome normalization is reused; the storage and consent state are not.

## 5. Storage decision

Direct concurrent writes from all profiles to one SQLite event database would introduce contention inside synchronous hooks. The accepted baseline instead uses per-process append-only JSONL journal segments followed by deterministic idempotent ingestion into a derived SQLite read model.

Benefits:

- no cross-process writer lock in the hook path;
- crash leaves a recoverable final partial segment;
- read model can be rebuilt from retained events;
- the CLI human and JSON projections share one summary representation, while any future dashboard can reuse it only after owner approval;
- event schemas can reject unsafe arbitrary payloads before persistence.

## 6. Privacy decision

Only allowlisted metadata is stored. Raw prompts, messages, responses, file contents, diffs, terminal commands/output, web queries/content, secrets, fingerprint keys, raw HMAC inputs, and chain-of-thought are prohibited. Content-derived configuration values use project-keyed, field-domain-separated HMAC-SHA-256; only the fingerprint and non-secret key-epoch ID persist. This is stronger than merely avoiding remote upload: the sensitive data is not copied into the observation journal at all, and a published summary does not carry the key needed for offline dictionary enumeration.

## 7. Flow-analysis decision

Progress is measured through explicit semantic deltas, not heartbeat frequency, token volume, wall time, or tool-call count. During contract creation the normalized state contains decision, ambiguity, evidence, invariant, and artifact-hash facts. After handoff it additionally contains explicitly bound required work-unit states, latest run outcomes, required review states, and acceptance-criterion states/evidence. This permits deterministic distinctions:

- new semantic delta: useful iteration;
- explicit failure-linked repeat: technical retry;
- repeated zero-delta cycle: semantic loop;
- invariant passed→failed without owner supersession: regression;
- return to earlier artifact hash: reversion;
- linked owner supersession: authorized direction change, not regression.

## 7.1 Full-lifecycle boundary decision

On 2026-08-22 Christopher approved extending each trace through the entire contract generated by Morfeo. The trace therefore does not end at persistence or Supervisor handoff. It follows only the explicitly bound root/descendant Kanban graph through implementation, required review/QA/integration, acceptance verification, and final Morfeo reconciliation.

This amendment deliberately treats `blocked`, `review`, crashed, timed-out, failed, reclaimed, and retried runs as recoverable lifecycle facts rather than trace terminals. Hermes can resume or redispatch them, so closing there would erase the remaining history. Only verified fulfillment closes as `completed`; owner-authorized cancellation, abandonment, or verified unrecoverable failure close as distinct non-success outcomes.

## 7.2 Revalidation against locked Hermes (2026-08-22)

This design was re-researched against the clean public checkout `/tmp/aether-telemetry-hermes-baseline`, tag `v2026.8.18`, commit `e624e9fde561e1add9388384012b295fde669ade`. The locally patched Aether runtime checkout was inspected only to distinguish it from upstream and is not evidence for this contract. In particular, `/home/darkarty/Desktop/agentes/aether/home/.venv-hermes/src/hermes-agent` is a dirty, different-revision antecedent only and is non-qualifying: it cannot supply the recorded Hermes SHA/clean status, observation-test count, callback count, capture assertions, or unload result. The current official Hermes plugin/hook documentation was also reviewed on 2026-08-22 at:

- <https://hermes-agent.nousresearch.com/docs/user-guide/features/hooks>
- <https://hermes-agent.nousresearch.com/docs/guides/build-a-hermes-plugin>

The release-locked source remains the compatibility authority. Documentation describes the moving public surface; it does not authorize silently targeting a newer runtime.

A historical design-feasibility run was described as exercising seven Hermes test files covering plugin registration/isolation, Kanban task lifecycle, worker lifecycle, dispatch-tick hooks, relay shared metrics, progressive tool search, and approval hooks. Its raw log and machine-readable result are not retained in this repository, so this contract makes no test-count or pass/fail claim from that run.

The reproducible implementation gate instead recreates the exact tag/commit, verifies clean status, runs the locked observation corpus with a minimum of 119 observation tests, loads the public plugin through real `PluginContext`/`PluginManager`, checks 22 registered callbacks, captures tool/API events with raw prompt/response absent, and verifies zero hooks after unload. This research document defines the gate; only retained, reproducible outputs belong in implementation evidence.

### 7.2.1 Verified feasibility matrix

| Required fact | Locked native source / capture point | Correlation | Verdict and design consequence |
|---|---|---|---|
| Plugin isolation and lifecycle | `hermes_cli/plugins.py:156-337`, `hermes_cli/lifecycle.py`; callback failures are isolated and Kanban observers are declared read-only/best-effort | process/profile/session/task IDs supplied by each hook | **Directly viable without core change.** One Aether plugin subscribes to public hooks and immediately projects allowlisted metadata. |
| CLI read surface | plugin CLI registration/discovery in `hermes_cli/plugins.py` and `hermes_cli/main.py` proves extension support; Aether's manager CLI owns the accepted `aether observe` namespace and imports the same reducer/query library as the plugin | selected project + explicit trace/contract/task reference | **Directly viable without a dashboard.** The native plugin collects; the Aether CLI reads the shared local state. No `hermes observe` alias or second query meaning is introduced. |
| Effective model, provider, request identity and system-prompt fingerprint | `agent/conversation_loop.py:2875-2902` `pre_api_request` supplies `task_id`, `turn_id`, `api_request_id`, `session_id`, model/provider, exact `system_prompt`, message/tool counts and timing | `api_request_id`, then `turn_id`/`session_id`/`task_id` | **Directly viable.** Compute the project-keyed, domain-separated HMAC-SHA-256 in callback memory and discard the prompt before journal/logging. This observes effective request state, avoids a portable dictionary oracle, and does not modify prompt caching. |
| Model/context economics | `agent/conversation_loop.py:6540-6579` `post_api_request`; `run_agent.py:2764-2778`; `agent/usage_pricing.py:73-89` | same `api_request_id` plus start/end | **Directly viable when provider usage exists.** Normalize input/output/cache-read/cache-write/reasoning/total buckets, duration and finish reason. Missing provider fields stay unavailable. Never persist `response` or assistant content. |
| Tool calls, failures, denials and approvals | `model_tools.py:1136-1187` plus `pre_tool_call`, `post_tool_call`, `pre_approval_request`, `post_approval_response` | `tool_call_id`, `api_request_id`, `turn_id`, `session_id`, `task_id` | **Directly viable after projection.** Persist name/category, duration, terminal status, structured error/approval code only. Drop args/result/error text/commands/middleware traces before persistence. |
| Successful skill loads | `on_skill_lifecycle` in `hermes_cli/plugins.py:216-218` and skill manager call sites | session/task/profile where supplied; otherwise producer epoch | **Directly viable for observed loads.** It does not prove every skill merely present in the prompt index was consulted. |
| Kanban transitions, worker runs, review/rework and dispatch pressure | Kanban observer hooks in `hermes_cli/plugins.py:256-337`; `hermes_cli/kanban_db.py:299-356` fires dispatch tick after releasing the writer lock; `DispatchResult` at `kanban_db.py:8016-8084` includes per-profile caps, unassigned, rate-limit, respawn and memory-pressure buckets | task/run/board/profile plus durable parent edges and dispatch tick | **Directly viable, sampled at tick cadence.** Reconstruct task/run/review attempts from durable edges and transitions; use dispatch buckets only for the interval until the next observed tick and publish precision. |
| Root and descendant trace binding | existing `kanban_create` result, native task idempotency key, `HERMES_KANBAN_TASK`, task parent graph | exact Aether project/board mapping + materialized trace + opaque correlation token/task ID | **Viable without a separate marker.** Resolve one project first, capture the create result, use a strict token in the same call as crash recovery, inherit descendants only through durable same-project parent edges, and leave ambiguous roots unbound. |
| Full historical retention and local indexing | Aether-owned per-process append-only segments plus deterministic SQLite reducer | `project_id`, `trace_id`, producer epoch/sequence, event ID/hash | **Viable outside Hermes core.** Hermes shared metrics are aggregate and have a different consent/export/retention contract, so they are not reused as evidence storage. |

### 7.2.2 Limits found and normative response

1. **No exact final granted tool surface is guaranteed by the locked public hooks.** `pre_api_request` exposes `tool_count` and a sanitized request projection. `run_agent.py:2802-2849` applies depth/string/sequence bounds, so the request-correlated schemas may be incomplete. Configured toolsets, registered schemas, direct effective schemas, dynamically added tools, progressive-disclosure reachability, and the final provider payload are different facts. Therefore Aether records field coverage, never reports `never_used` from a partial surface, and labels schema tokens as an estimate unless exact provider serialization/tokenization is available.
2. **No dedicated lossless context-compression/overflow event exists in the locked plugin hook taxonomy.** API errors may expose structured classification and SessionDB may expose cumulative state, but parsing prose/errors or inferring from token drops would be false precision. Aether records the signal only when structured evidence exists and otherwise reports `unavailable`.
3. **Metadata cannot always determine semantic cause.** `capability`, `needs_input`, `changes_requested`, `protocol_violation`, and `skipped_unassigned` are evidence, not proof of `instruction_defect`, `contract_ambiguity`, `coordination_defect`, or `genuine_discovery`. Only bounded runtime and structured policy-denial mappings are deterministic; residual classes remain actor-declared, Morfeo judgment, or `undeclared`.
4. **Dispatch eligibility is sampled, not continuously observed.** Task/run/review edges and intervals are durable, but the cause for ready work not running is strongest at dispatcher ticks. Summaries carry sampling precision and use `unknown` for competing or missing causes.
5. **A telemetry layer cannot infer final owner-facing verification from mechanical completion alone.** Settled graph state produces `completion_candidate`. `completed` additionally requires authoritative canonical verification evidence or an optional bounded checkpoint emitted by an existing closing action. Absence never blocks the pipeline.
6. **Per-process monotonic clocks are not globally comparable.** Every event carries UTC instant plus originating offset, producer epoch, producer-local monotonic reference and sequence. Cross-process order comes from causal/native edges; wall-clock proximity never creates causality.
7. **Hermes stores more run outcomes than its older task-run schema comment lists.** The locked implementation durably writes `rate_limited`, `stale`, `review_requested`, `changes_requested`, and `scheduled` in addition to the traditional terminal values, while `protocol_violation` is a structured durable task-event marker associated with a run. The observer therefore carries a closed superset across event schema, projector, reducer, and summary totals instead of degrading those values to `unknown` or parsing private payload text.

### 7.2.3 Package and plugin-discovery choice

The locked Hermes plugin manager explicitly supports pip distributions through the `hermes_agent.plugins` entry-point group (`hermes_cli/plugins.py:5-20`, `394-472`). For an enabled standalone entry point it loads the target module and invokes its top-level `register(ctx)` (`4779-4795`, `5021-5037`). This public surface is preferable to writing product code under each active `HERMES_HOME/plugins/`: one installed distribution works across profile-scoped plugin managers while each profile retains explicit enable/disable configuration.

Aether therefore uses one source repository, one `aether-agents` distribution, and one product version. The exact staged wheel is installed in the manager environment and again with `--no-deps` in the versioned Hermes runtime. The entry point targets a module rather than `module:function`, matching the locked loader's expectation that `ep.load()` returns an object exposing `register`. Manager/runtime build/installed-file identity is release-locked and doctor-verifiable; external provenance and the local transition record bind the source wheel filename/SHA-256 without circular self-reference.

Rejected structures:

- a second `aether-observer` distribution or repository, because it creates an independent version/rollback/publication axis;
- copying a directory plugin into every profile, because product bytes can drift across Morfeo, Supervisor and Implementers;
- installing mutable source or using `PYTHONPATH`, because activation would no longer be release-atomic or digest-bound;
- embedding Hermes in the manager import graph, because a broken runtime would disable doctor/rollback;
- an observer daemon/service, because hook capture plus on-demand deterministic reduction requires no new autonomous process.

The supporting assumption is that shared observation code remains Hermes-independent and the runtime can install the same wheel with `--no-deps`. Qualification must prove this in two clean virtual environments. Failure of that assumption is not implementation freedom to split the product silently; it triggers an owner-visible contract revision.

### 7.2.4 Upstream boundary

The two missing generic signals that could improve later fidelity are: (a) a metadata-only, complete, request-correlated effective tool-surface snapshot/fingerprint after all dynamic filtering and progressive disclosure; and (b) a structured context lifecycle observer for compression start/end, overflow and resulting session lineage. They are generally useful Hermes observability capabilities, not Aether-specific semantics. If required later, they should be proposed upstream with privacy and fail-open tests. Aether 1.0 neither carries a private core patch nor pretends the fields are exact on `v2026.8.18`.

### 7.2.5 Deterministic reconstruction rules

- A **step** is an instance of a typed semantic/native transition, not a task ID and not a tool call. Retries and review returns create new step instances linked to prior attempts.
- A **round** starts at initial dispatch or an evidenced review/retry/resume/redispatch/protocol-correction/direction-change trigger and ends at its next barrier.
- A **wave** exists only when explicit durable parent/dependency references establish causally independent sibling steps inside the same evidenced round. Timestamp overlap alone never creates membership or a predecessor; after membership is established, timestamps may measure the observed overlap and clock uncertainty reduces only that measurement's coverage.
- The **critical path** is the longest measured path over the versioned attempt DAG, including evidenced wait nodes. It is descriptive, not a counterfactual productivity claim.
- A bottleneck interval is classified only from its native evidence snapshot; ambiguous simultaneous causes become `unknown` rather than being ranked heuristically.
- Event replay sorts first by causal/native edges, then by producer sequence, and only then by UTC time as a deterministic presentation tie-breaker. A clock anomaly is retained as evidence, never repaired silently.

### 7.2.6 Pre-implementation hardening decisions

- **Project resolution**: a task/run's exact Aether board mapping is the strongest source, followed by a verified session-to-Hermes-Project mapping and then a manager launch binding cross-checked against the Aether registry and portable marker. `cwd`, profile, repository name, timestamps, or an unverified environment value are hints only. Content-free health counters preserve visibility when no project can be safely selected.
- **Origin/continuation**: owner messages are candidates, not traces. An authoritative contract/root binding materializes the trace. Exact message/contract/task references decide origin and continuation; at most one candidate inside the exact session-lineage interval may be selected without a direct reference. Ambiguity yields null origin timing and no automatic merge.
- **Identity/replay**: project UUID is canonical; producer epoch and trace ID use independent 128-bit randomness; complete stable native tuples produce deterministic event IDs; incomplete tuples use once-allocated randomness and are never fuzzy-deduplicated. Reducers do not append to journals.
- **Evolution/rollback**: raw journal versions are immutable. New reducers upcast supported historical versions; old reducers preserve/index unknown newer bytes and use their own versioned projection. Re-update reingests preserved bytes. Summary diffs require a compatible normalization path.
- **Non-intrusive durability**: callbacks append once but never wait for `fsync`; supervised plugin work flushes outside the agent path. This deliberately accepts explicit coverage loss on power/IO failure rather than hiding synchronous latency.
- **Critical durability**: a critical append wakes the flusher, and its pending flag survives every failed `fsync` until a successful file durability boundary. Teardown remains bounded even if the worker is blocked. Compaction retains the source until archive plus manifest have crossed file-fsync, atomic rename, directory-fsync, and replay-verification boundaries.
- **Atomic derived state**: ingest treats one source event and every derived row as one transaction/savepoint. A derivation failure rolls back that event completely, records a content-free diagnostic separately, and remains replayable; bulk ingest isolates the failed item without undoing earlier valid events. Projection pointer changes are locked compare-and-swap transitions, not reader side effects, so an older reader cannot silently downgrade a newer active pointer.
- **Structural privacy and confinement**: native payloads are projected and provenance-validated before queue, logs, journal, SQLite, summaries, retries, or exceptions. Relative `XDG_STATE_HOME`, generated-component grammar violations, symlink/path escape, hard links, and non-private DB/WAL/SHM modes fail before persistence rather than relying on post-write redaction or chmod.
- **Partial native capability**: absent expected hooks, missing start/terminal span pairs, and missing turn/API identities become trace-visible coverage with stable `missing_hook_refs`/gap references. Heartbeat recency remains fresh/stale/unknown liveness evidence and never becomes semantic progress.
- **Fingerprint privacy**: content-derived configuration values use project-keyed, domain-separated HMAC-SHA-256. Random keys stay in private project state, rotation starts a comparison epoch, and 1.0 makes no cross-project fingerprint comparison.
- **Compaction**: only closed verified segments use deterministic gzip plus canonical manifest, dual hashes, atomic rename, directory fsync, and replay verification before source removal. Threshold selection remains a measured implementation parameter, not evidence-format freedom.
- **Performance evidence**: the accepted latency gates remain. A bounded disposable spike against a recreated clean checkout of `v2026.8.18`/`e624e9fde561e1add9388384012b295fde669ade` precedes broad fan-out. The previously used `/tmp/aether-telemetry-hermes-baseline` checkout was ephemeral and must be recreated; the patched local runtime is not a substitute for upstream evidence.

### 7.2.7 Adversarial implementation findings (#213–#220)

The implementation review issues refine the executable boundary without changing the architecture:

- **#213 — authority and completion**: the existence of `contract.completion_verified` is not authority. Product-owned identity/profile/role, exact root, assigned reviews, evidenced acceptance, all ten explicit invariants, and freshness after the last semantic delta jointly gate the observer's `completed` classification.
- **#214 — binding and causality**: unknown native relation/requirement values remain `unknown`/null; root and descendants bind only through create result, strict token, or durable parent edges. Conflicting native identity becomes a reproducible gap. Timestamp order remains a presentation tie-breaker and never creates a graph edge or wave.
- **#215 — coverage semantics**: missing span endpoints, turn/API identifiers, expected hooks, heartbeat recency, dispatch limits, protocol markers, and distinct native run outcomes remain individually visible. A terminal observation without its start may count as observed, but coverage cannot remain complete.
- **#216 — journal durability**: failed `fsync` retains critical urgency, critical events wake the flusher, teardown is bounded, and compaction cannot remove the only source before archive/manifest durability and replay verification.
- **#217 — transactional storage and evolution**: raw event plus derived rows are atomic, derivation diagnostics commit separately, bulk ingest isolates one failed event, pointer replacement includes file/directory durability and reader coordination, and rollback preserves unknown-newer bytes for re-update.
- **#218 — structural privacy**: projection and provenance validation precede every sink and are exercised with malicious native payload shapes, not a sanitized artificial dictionary. Raw command/output/error and host paths are rejected before persistence.
- **#219 — path confinement**: relative XDG state, generated-name grammar violations, symlink/hard-link escape, and non-private DB/WAL/SHM state fail before write; tests remain confined to disposable roots.
- **#220 — exact public compatibility**: qualification recreates the clean public Hermes tag/commit, exercises the public plugin and real callback lifecycle, keeps raw prompt/response absent, and records test/callback/unload/performance evidence without using the dirty local runtime.

## 8. Release implication

Issue #195 is no longer a post-1.0 enhancement. The MVP defined by `spec.md` is a release prerequisite. Qualification requires both deterministic fixtures and one controlled real trace reconciled against actual SessionDB, Kanban, artifact hashes, and tool outputs.

## 9. Open refinements after implementation evidence

The following may be reconsidered only through an owner-approved contract revision:

- compaction trigger thresholds and optional additional indexes after observed growth; archive format, integrity, atomicity, and no-pruning semantics are closed;
- the two-cycle loop threshold;
- performance thresholds if measured hook characteristics demonstrate they are unrealistic;
- whether and when a dashboard or separate read-only agent query surface is added after 1.0;

They are not implementation freedoms in the current baseline.
