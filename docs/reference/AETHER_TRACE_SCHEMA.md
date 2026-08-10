# Aether MCP Semantic Event Trace Schema

> **Status:** ACCEPTED AND FROZEN `v1alpha1` DESIGN; NOT IMPLEMENTED
> **Date:** 2026-08-06
> **Schema:** `aether.trace/v1alpha1`
> **Authority:** ADR-0001 and `../architecture/AETHER_MCP.md`
> **Implementation authorization:** M1.1 repository qualification only

## 1. Purpose

The trace answers, without reconstructing model reasoning:

- what happened;
- who initiated or observed it;
- why it was chosen;
- when it occurred;
- what contract/use case/Task/Dispatch it served;
- what authority and effect applied;
- what result and uncertainty were observed;
- what artifacts and evidence support the conclusion;
- whether resources and acceptance were reconciled.

It is the compact append-only semantic and evidence index, not a duplicate Orca
operational database and not the full learning corpus. Rich replayable content
is defined separately in `AETHER_LEARNING_EPISODE_SCHEMA.md` and referenced by
project-scoped content/event identities.

## 2. Core event

```json
{
  "schema": "aether.trace/v1alpha1",
  "event_id": "server-generated-uuidv7",
  "project_id": "immutable-project-uuid",
  "sequence": 184,
  "recorded_at_utc": "2026-08-06T20:10:33.120Z",
  "source_occurred_at_utc": "2026-08-06T20:10:32.901Z-or-null",
  "observed_monotonic_ns": 5432199912,

  "actor": {
    "kind": "user|hermes|worker|verifier|mcp|orca|tool",
    "principal_id": "safe-stable-id",
    "session_id": "safe-session-correlation-or-null",
    "profile": "safe-profile-alias-or-null"
  },

  "context": {
    "contract_id": "contract:onboarding/generation/3",
    "contract_generation": 3,
    "use_case_id": null,
    "variant": null,
    "aether_run_id": "uuid-or-null",
    "aether_task_id": "uuid-or-null",
    "operation_id": "caller-operation-id-or-null"
  },

  "orca": {
    "provider_build": "safe-build-id-or-null",
    "run_id": "safe-id-or-null",
    "task_id": "safe-id-or-null",
    "dispatch_id": "safe-id-or-null",
    "worker_id": "safe-id-or-null",
    "terminal_id": "safe-id-or-null",
    "worktree_id": "safe-id-or-null",
    "message_id": "safe-id-or-null"
  },

  "event_type": "operation_requested",
  "action": "dispatch_worker",

  "reason": {
    "code": "PARALLEL_INDEPENDENT_SCOPE",
    "summary": "The API contract is frozen and write scopes do not overlap.",
    "authority_ref": "contract:onboarding/generation/3",
    "evidence_refs": ["git:abc123:docs/design/onboarding.md"]
  },

  "effect": {
    "expected": "LOCAL_REVERSIBLE",
    "observed": "LOCAL_REVERSIBLE|UNKNOWN",
    "authorization_ref": "contract:onboarding/generation/3"
  },

  "outcome": {
    "classification": "SUCCEEDED|REJECTED|FAILED|PARTIAL|CANCELLED|UNKNOWN|OBSERVED",
    "code": "stable-code-or-null",
    "summary": "bounded-safe-summary-or-null",
    "retryable": false,
    "reconciliation_required": false,
    "unknown_fields": []
  },

  "operation_control": {
    "request_digest": "sha256-or-null",
    "normal_budget_ms": 120000,
    "reconcile_after_utc": "server-timestamp-or-null",
    "lease_deadline_utc": "server-timestamp-or-null",
    "state": "IN_FLIGHT|TERMINAL|UNKNOWN|RECONCILIATION_REQUIRED|null"
  },

  "references": {
    "artifact_refs": [],
    "evidence_refs": [],
    "decision_refs": [],
    "receipt_refs": []
  },

  "privacy": {
    "classification": "PUBLIC|INTERNAL|RESTRICTED",
    "redactions_applied": [],
    "contains_raw_content": false
  },

  "integrity": {
    "previous_event_hash": "sha256-or-null",
    "event_hash": "sha256"
  }
}
```

## 3. Field authority

- `event_id`, `sequence`, `recorded_at_utc`, the monotonic observation value,
  and integrity fields are server-generated.
- `source_occurred_at_utc` is a provider/user-source timestamp only when a
  structured authoritative source supplies it; otherwise it is `null`. It never
  replaces the MCP recording timestamp.
- `actor` is derived from admitted runtime/session context and provider receipts.
- `reason` for a mutation is supplied by Hermes/user through a typed request and
  stored as declared rationale.
- Orca IDs come from structured provider receipts or fresh reads.
- Artifact/evidence references are normalized and may include digests.
- Unknown or missing provider fields are `null` and listed under
  `unknown_fields`; they are not copied from another event or entity.

## 4. Event taxonomy

### 4.1 Contract and authority

```text
contract_created
contract_validated
contract_amended
project_admitted
project_rebound
route_selected_direct
route_selected_swarm
participant_admitted
participant_denied
scope_assigned
effect_authorized
effect_denied
user_decision_recorded
waiver_recorded
```

### 4.2 Provider and operation

```text
provider_pinned
provider_schema_changed
operation_requested
operation_accepted
operation_rejected
operation_failed
operation_partial
operation_unknown
reconciliation_required
reconciliation_started
operation_fenced
operation_reconciled
```

### 4.3 Runtime observation

```text
run_observed
task_observed
dispatch_observed
worker_observed
message_observed
question_observed
reply_observed
retry_created
cancellation_observed
recovery_observed
```

Runtime events are observations with source/freshness; they do not establish
semantic acceptance.

### 4.4 Artifact and evidence

```text
artifact_referenced
artifact_digest_recorded
evidence_requested
evidence_observed
evidence_verified
evidence_failed
evidence_insufficient
review_recorded
```

### 4.5 Acceptance and closure

```text
completion_proposed
product_accepted
product_rejected
limitation_accepted
cleanup_requested
resource_reconciled
resource_retained_authorized
cleanup_blocked
cleanup_unknown
run_closed
```

## 5. Operation receipt

Each consequential provider effect has a normalized receipt:

```json
{
  "operation_id": "uuid",
  "request_digest": "sha256",
  "provider": "orca",
  "provider_build": "id",
  "catalog_digest": "sha256",
  "command_id": "versioned-command-id",
  "effect": "LOCAL_REVERSIBLE",
  "requested_event_id": "uuid",
  "terminal_event_id": "uuid-or-null",
  "normal_budget_ms": 120000,
  "reconcile_after_utc": "server-timestamp",
  "lease_deadline_utc": "server-timestamp",
  "outcome": "SUCCEEDED|REJECTED|FAILED|PARTIAL|CANCELLED|UNKNOWN",
  "created_resources": [],
  "reused_resources": [],
  "removed_resources": [],
  "remaining_resources": [],
  "unknown_resources": [],
  "provider_receipt_digest": "sha256-or-null"
}
```

Raw provider bodies are not stored by default. A bounded redacted evidence file
may be referenced when diagnosis requires it.

## 6. Decision record

```json
{
  "decision_id": "uuid",
  "kind": "contract_amended|participant_admitted|product_accepted|...",
  "authority": "user|hermes|policy|separate-gate",
  "decision": "concise explicit decision",
  "reason": "concise declared rationale",
  "supersedes": ["decision-id"],
  "affected_contract_generation": 4,
  "affected_tasks": [],
  "evidence_refs": [],
  "event_id": "uuid"
}
```

Past decisions are never overwritten. Amendments create new events and identify
supersession.

## 7. Evidence record

```json
{
  "evidence_id": "uuid",
  "kind": "test|build|lint|e2e|render|review|artifact|resource_inventory|rollback",
  "producer": "safe-principal-or-tool",
  "reference": "bounded-reference",
  "artifact_digest": "sha256-or-null",
  "executed_at_utc": "timestamp-or-null",
  "outcome": "PASS|FAIL|BLOCKED|INSUFFICIENT|UNKNOWN",
  "criteria_covered": ["criterion-id"],
  "coverage": {"known": 4, "total": 5},
  "unknowns": [],
  "event_id": "uuid"
}
```

Passing evidence is not automatic technical or product acceptance.

## 8. Use-case binding and metrics

Evaluation Runs include:

```json
{
  "use_case_id": "UC-001",
  "use_case_version": "1",
  "variant": "direct-baseline|swarm-candidate",
  "hypothesis_ref": "measurement-contract-ref",
  "environment_digest": "sha256",
  "initial_state_digest": "sha256",
  "model_route": "safe-versioned-route",
  "acceptance_set": ["criterion-id"],
  "metric_set": ["metric-id"]
}
```

The trace supports metric facts for:

- timestamps and durations;
- participant/Task/Dispatch counts;
- parallel overlap;
- operations, messages, waits, questions, and user interventions;
- retries, cancellations, unknowns, and corrections;
- evidence coverage and defect findings;
- tokens/cost/latency with source and coverage when available;
- cleanup resources and duration;
- completion proposal and user disposition.

Metrics are derived from canonical events/receipts and executed evidence. Missing
values remain unknown. The complete contract is
`../releases/v0.22.0/MEASUREMENT_CONTRACT.md`.

Durations prefer one server monotonic clock. Cross-process/provider wall-clock
intervals identify their source and clock coverage instead of claiming
sub-second precision they cannot prove.

## 9. Integrity

- Events are appended transactionally with per-project sequence.
- Canonical serialization excludes mutable storage metadata.
- `event_hash = SHA-256(canonical_event_without_event_hash)`.
- Each event references the prior event hash in that project stream.
- A Run closeout manifest records first/last sequence, root hash, provider/build,
  contract/use-case identities, artifact/evidence digests, and closure state.
- Integrity failure blocks trusted export/acceptance claims and remains visible.

Canonical closeout shape:

```json
{
  "schema": "aether.closeout/v1alpha1",
  "project_id": "uuid",
  "aether_run_id": "uuid",
  "first_sequence": 101,
  "last_sequence": 244,
  "root_event_hash": "sha256",
  "contract_generation": 3,
  "manifest_digest": "sha256",
  "use_case": null,
  "provider_build": "safe-build-id",
  "provider_catalog_digest": "sha256",
  "resource_disposition": {
    "removed": [],
    "retained_authorized": [],
    "preexisting_untouched": [],
    "unknown": []
  },
  "artifact_digests": [],
  "evidence_digests": [],
  "learning_episode_manifest_digest": "sha256-or-null",
  "learning_content_root_digest": "sha256-or-null",
  "semantic_disposition": "accepted|rejected|not_requested|unknown",
  "integrity": "PASS|FAIL|UNKNOWN",
  "closed_at_utc": "server-timestamp"
}
```

Hash chaining detects corruption or non-coherent edits; it is not described as a
cryptographic signature unless an external signing authority is later added.

## 10. Privacy contract

### Forbidden in semantic event bodies

- raw prompts or chat transcripts;
- chain-of-thought or hidden reasoning;
- full worker messages;
- arbitrary tool arguments/results;
- terminal output;
- source/artifact bodies;

Raw prompts/chat transcripts, full worker messages, admitted tool exchanges,
bounded terminal excerpts, and source/artifact bodies may exist as
secret-redacted model-visible content only in the separately encrypted learning
episode store under an admitted `FULL_EPISODE` policy. Hidden chain-of-thought
remains prohibited everywhere.

### Forbidden in every persistent layer

- secrets, tokens, cookies, authorization headers, `.env` contents;
- raw account/provider identities when safe aliases suffice;
- private Orca database rows;
- unrelated session/project data;
- unredacted exceptions or tracebacks.

### Permitted bounded content

- concise declared reason/decision summaries;
- enumerated reason, effect, event, and outcome codes;
- safe principal/profile aliases;
- contract and provider identities;
- normalized resource IDs and correlations;
- artifact/evidence references and digests;
- structured counts, timings, coverage, and unknowns;
- bounded redacted error summaries.

The restricted project-admission registry may retain an exact canonical absolute
root because containment enforcement requires it. Ordinary events use
`project_id`/safe alias, and exports redact the root unless the requester has
explicit restricted-field authority.

### Query and export

- project-bound by default;
- progressive detail;
- server-side redaction reapplied at read time;
- no secret-bearing cursors or URLs;
- exported manifests contain only admitted fields;
- retention/deletion policy below applies before live collection.

### Retention classes

The proposed `v1alpha1` default is explicit-owner retention, not silent expiry:

| Class | Content | Default retention |
|---|---|---|
| R0 forbidden | credentials, secret environment values, hidden chain-of-thought, unadmitted cross-project/private provider data | never stored |
| R1 semantic | contract generations, decisions, reasons, authority, operation/effect receipts, evidence refs/digests, closeout | until owner-authorized `project_forget` |
| R2 operational observation | material normalized state transitions and source/freshness | until owner-authorized `project_forget` |
| R3 poll telemetry | counts, latency, wait, and coverage aggregates; no raw ordinary poll event stream | until owner-authorized `project_forget` |
| R4 learning episode | full secret-redacted model-visible context/messages/tool exchanges/artifact refs and labels under admitted policy | until lineage-aware prune/revoke/forget; no silent expiry |
| R5 diagnostic attachment | bounded redacted provider/incident material outside the admitted model-visible episode, disabled by default | explicit opt-in, maximum seven days, then verified deletion |

There is no automatic time-based deletion of R1–R4 because their primary
purpose is cumulative system learning and their secondary purpose is durable
what/why/when reconstruction. Quotas pause capture fail-visibly rather than
silently deleting learning data. The owner may prune eligible sealed episodes,
revoke datasets, export, or forget the complete project partition under lineage
rules.

Selective in-place deletion of individual semantic events is not supported in
`v1alpha1`, because it would invalidate event sequence/integrity and create an
unexplained history. Episode pruning is separate and allowed only when derived
dataset/export lineage is reconciled. A privacy defect or legal deletion request
uses lineage-aware project forget; live Orca resources and external derivatives
are reported separately and are never silently changed by trace deletion.

### Project forget

Normal forget requires:

- exact admitted project ID and safe-alias confirmation;
- owner-authorized `LOCAL_DESTRUCTIVE` operation and concise reason;
- every Run closed with zero unknown resources;
- optional export digest when the owner requires preservation;
- deletion verification for trace, episode/content, label, dataset, export
  lineage, restricted identity registry, and expired diagnostic attachments.

A `privacy_emergency` forget may proceed with exact owner authority even when a
Run is open/unknown. It deletes MCP-held project data only, explicitly returns
Orca/resource and external-derivative disposition as unknown, and cannot claim
operational cleanup or that an exported/trained derivative was erased.

For idempotency without retaining project content, the global MCP store may keep
only a non-enumerable tombstone containing the forget-operation ID, salted
project-ID digest, completion timestamp, and outcome. It stores no project path,
contract, reason body, actor identity, or artifact/evidence reference. A later
admission creates a new project ID.

## 11. Reconciliation rules

1. `operation_requested` without a terminal receipt is not failure.
2. Provider timeout after possible delivery becomes `operation_unknown`.
3. Reconciliation reads fresh provider and resource state before retry.
4. A new retry operation never overwrites the old operation/Dispatch.
5. Provider/resource disagreement remains explicit with both sources.
6. `run_closed` requires every created/reused resource to have known disposition
   or an authorized retention event.
7. Unknown state cannot be converted to zero, absent, successful, or clean.
8. Cleanup mutation is limited to resources bound to the Run by creation or
   admission receipts; similarly named pre-existing resources are not inferred
   as owned.

## 12. Migration rules

- Every event retains its original schema identifier.
- Readers support explicit version migrations to a current projection.
- Migrations never rewrite the declared meaning of past events.
- Destructive compaction requires a separately accepted retention policy and a
  verifiable closeout/export path.
- Historical `.aether` databases are not imported implicitly.

## 13. Final design gate

The proposed design now defines semantic-event and rich learning-episode
boundaries, storage/retention/lineage, project identity/admission behavior,
privacy fixtures/forbidden-field scans, crash/idempotency/schema-drift/
reconciliation cases, dataset contamination and closeout manifest shape.
Concrete cases and thresholds are in
`../releases/v0.22.0/USE_CASE_CATALOG.md`.

Implementation remains blocked until the product owner accepts or revises those
proposals and separately authorizes an implementation plan.
