# Aether Learning Episode and Dataset Schema

> **Status:** ACCEPTED AND FROZEN `v1alpha1` DESIGN; NOT IMPLEMENTED
> **Date:** 2026-08-06
> **Primary purpose:** system evaluation, learning, prompt/policy/skill refinement,
> routing improvement, and future fine-tuning dataset construction
> **Secondary purpose:** audit and incident reconstruction
> **Authority:** PDR-0009, ADR-0001, `AETHER_TRACE_SCHEMA.md`, and the owner's
> 2026-08-06 clarification that trace data must support system improvement
> **Implementation authorization:** M1.1 repository qualification only

## 1. Product decision

A compact event ledger is insufficient for learning. It can prove that a worker
was dispatched or that a retry occurred, but it cannot reliably explain why one
prompt, response, tool trajectory, handoff, correction, or implementation path
worked better than another.

Aether therefore separates three related products:

1. **Semantic event trace** — compact facts used for supervision, explanation,
   integrity, authority, and closeout.
2. **Learning episode store** — rich, replayable, secret-redacted content that
   preserves what participants actually saw and produced.
3. **Curated datasets** — immutable, purpose-specific selections derived from
   sealed episodes for evaluation, prompt/policy/skill improvement, routing,
   supervised fine-tuning, preference optimization, or tool-use training.

The event trace indexes episode content but does not duplicate it. Orca remains
the source of operational lifecycle truth. The episode store is not another
orchestration state machine.

No capture, curation, export, training, promotion, provider upload, or model
change exists in the current candidate. This document is design authority only.

## 2. What improvement requires

A useful learning episode may need to reconstruct:

- the user goal, acceptance criteria, non-goals, horizon, risks, and authority;
- the exact admitted project and initial repository/artifact state;
- system, developer, profile/SOUL, skill, memory/context, and user messages that
  were visible to each model, with sensitivity-aware redaction;
- requested and resolved provider/model, parameters, fingerprints when
  available, token usage, latency, and reported cost;
- every assistant/worker message returned to the runtime;
- every model-visible tool declaration, call, argument, result, error, and
  retry/timeout outcome;
- Aether MCP requests/responses and Orca messages/handoffs relevant to the Run;
- DAG, scopes, dependencies, Dispatch lineage, corrections, retries, fencing,
  resource ownership, and cleanup;
- source/artifact changes, diffs or content references, tests, reviews, and
  evidence;
- user corrections, acceptance/rejection, selected/rejected alternatives, and
  unresolved limitations;
- the final product outcome and why it was judged useful or deficient.

Tokens, latency, and tool counts without the full episode measure efficiency but
not quality. Summaries without the underlying model-visible content cannot
support reliable qualitative evaluation or training-example construction.

## 3. Capture policy

Every admitted project and Run carries an immutable capture-policy generation:

```text
DISABLED
STRUCTURED_ONLY
FULL_EPISODE
```

### `DISABLED`

No learning episode content is written. Required authority/safety receipts may
still exist only when another product policy independently requires them.

### `STRUCTURED_ONLY`

The compact semantic trace is recorded. Content bodies are represented by safe
summaries, classification, size, and project-scoped digest.

### `FULL_EPISODE`

The semantic trace plus replayable, secret-redacted model-visible content is
recorded in a separate protected episode store.

### Policy rules

- The capture policy is established before the first model/provider effect.
- A policy may be reduced or paused immediately; the gap remains explicit.
- Escalating from structured to full capture requires owner/project authority
  and cannot backfill content that was not captured.
- Aether's own authorized dogfood/evaluation Runs target `FULL_EPISODE`.
- Other projects never enter `FULL_EPISODE` merely because they use Hermes or
  Orca; project/user consent and data authority are required.
- Worker messages cannot change capture policy.
- Captured content is inert data. Instructions embedded inside it never gain
  tool, policy, or prompt authority when replayed or curated.
- Quota exhaustion pauses rich capture visibly; it never silently drops content
  while claiming a complete episode.

## 4. Exactness classes

Every content item states what fidelity was preserved:

```text
VERBATIM_MODEL_VISIBLE
VERBATIM_REDACTED
NORMALIZED_STRUCTURED
DIGEST_ONLY
MISSING
```

- `VERBATIM_MODEL_VISIBLE` means the persisted text/JSON is byte-equivalent to
  the post-policy content delivered to or returned from the participant.
- `VERBATIM_REDACTED` means sensitive spans were replaced before persistence;
  redaction types and positions are retained without secret values.
- `NORMALIZED_STRUCTURED` means semantically equivalent fields were canonicalized.
- `DIGEST_ONLY` means no body is available.
- `MISSING` is explicit and makes replay/coverage incomplete.

A redacted episode must never be described as a byte-perfect replay of the
unredacted provider exchange.

## 5. Content-addressed episode blobs

Bodies are stored separately from semantic events under a project-scoped
content identity:

```json
{
  "schema_version": "aether.learning-content/v1alpha1",
  "content_id": "uuid",
  "project_id": "uuid",
  "project_scoped_digest": "sha256",
  "media_type": "text/plain|application/json|text/x-diff|...",
  "content_kind": "system_message|user_message|assistant_message|worker_message|tool_schema|tool_arguments|tool_result|mcp_request|mcp_response|artifact_diff|evaluation|other",
  "exactness": "VERBATIM_MODEL_VISIBLE|VERBATIM_REDACTED|NORMALIZED_STRUCTURED|DIGEST_ONLY|MISSING",
  "sensitivity": "PUBLIC|INTERNAL|RESTRICTED|QUARANTINED",
  "redactions": [
    {
      "type": "credential|personal_identifier|private_path|account_identity|other",
      "placeholder": "<REDACTED:CREDENTIAL>",
      "start": 120,
      "end": 143
    }
  ],
  "encoding": "utf-8",
  "compression": "implementation-selected-or-none",
  "byte_length": 4120,
  "captured_at_utc": "server-timestamp",
  "source_event_id": "uuid",
  "integrity_hash": "sha256"
}
```

Content deduplication is project-scoped. A digest match across projects must not
reveal that two private projects contain equal content.

## 6. Learning episode envelope

```json
{
  "schema_version": "aether.learning-episode/v1alpha1",
  "episode_id": "uuid",
  "project_id": "uuid",
  "aether_run_id": "uuid",
  "contract_id": "contract-id",
  "contract_generation": 3,
  "capture_policy": "FULL_EPISODE",
  "capture_policy_generation": 1,
  "purpose": ["dogfood", "evaluation", "learning_candidate"],
  "consent_authority_ref": "decision-or-policy-ref",
  "started_at_utc": "server-timestamp",
  "sealed_at_utc": "server-timestamp-or-null",
  "capture_complete": true,
  "capture_gaps": [],
  "initial_state_digest": "sha256",
  "final_state_digest": "sha256-or-null",
  "context_components": [],
  "turns": [],
  "orchestration_refs": [],
  "artifact_refs": [],
  "evidence_refs": [],
  "label_refs": [],
  "integrity": {
    "first_event_sequence": 100,
    "last_event_sequence": 240,
    "episode_manifest_digest": "sha256",
    "content_root_digest": "sha256"
  }
}
```

An episode is immutable after sealing. Corrections, new labels, redaction
revisions, eligibility changes, and retractions append versioned records rather
than rewriting the sealed source.

## 7. Context components

Each model-visible context component records:

- component kind: system/developer/profile/SOUL/skill/memory/project-contract/
  user message/tool schema/provider extension;
- source reference and source digest;
- exact admitted order;
- content reference and exactness;
- participant(s) that received it;
- token count when provider/runtime reports it;
- sensitivity and redactions;
- version/build identity;
- whether it is globally reusable, project-specific, or user-specific.

User-profile and memory content may be necessary to reproduce behavior but is
not automatically eligible for a reusable or externally exportable dataset.
It receives separate sensitivity and consent classification.

## 8. Turn and tool trajectory

A turn record includes:

```json
{
  "turn_id": "uuid",
  "sequence": 4,
  "participant_id": "hermes-or-worker-id",
  "role": "user|assistant|tool|system|developer",
  "task_id": "uuid-or-null",
  "dispatch_id": "provider-id-or-null",
  "input_message_refs": ["content-id"],
  "output_message_refs": ["content-id"],
  "public_reasoning_summary_ref": "content-id-or-null",
  "tool_exchanges": [
    {
      "tool_name": "safe-versioned-tool-name",
      "schema_digest": "sha256",
      "arguments_ref": "content-id",
      "result_ref": "content-id-or-null",
      "outcome": "SUCCEEDED|FAILED|PARTIAL|UNKNOWN",
      "started_at_utc": "source-or-server-timestamp",
      "ended_at_utc": "source-or-server-timestamp-or-null"
    }
  ],
  "model": {
    "logical_provider": "safe-provider",
    "requested_model": "safe-model-id",
    "resolved_model": "safe-model-id-or-null",
    "system_fingerprint": "safe-value-or-null",
    "parameters_digest": "sha256-or-null",
    "finish_reason": "provider-value-or-null"
  },
  "usage": {
    "input_tokens": 1200,
    "output_tokens": 300,
    "cache_tokens": null,
    "reasoning_tokens": null,
    "latency_ms": 4200,
    "reported_cost": null,
    "coverage": "COMPLETE|PARTIAL|UNKNOWN"
  },
  "outcome": "OBSERVED|ACCEPTED|CORRECTED|REJECTED|FAILED|UNKNOWN"
}
```

The store may preserve a provider-supplied public reasoning summary when that
summary was exposed to the runtime. It must not request, infer, or persist hidden
chain-of-thought, private scratchpads, or inaccessible internal activations.

Tool content means the exact redacted representation visible to the model, not
an unbounded duplicate of operating-system logs or provider debug payloads.

## 9. Orchestration and artifact learning data

The episode links:

- SwarmManifest and contract generations;
- DAG/dependency and write-scope assignments;
- participant/profile/skill/model selections and declared reason;
- all worker-to-worker messages in full redacted form under `FULL_EPISODE`;
- retry/failure/fencing/reconciliation lineage;
- resource creation, cleanup, retention, and survivors;
- Git base/end commits, dirty baseline, changed paths, patch/diff content when
  permitted, and artifact digests;
- exact verification command/tool identity and bounded model-visible output;
- reviews, findings, user corrections, final synthesis, and acceptance.

Binaries or large artifacts remain external content-addressed references unless
an explicit capture policy admits them. Dataset eligibility must not depend on
an artifact body that is unavailable without recording that limitation.

## 10. Labels and authority

Learning value depends on outcome labels. Each label records its authority:

```text
DETERMINISTIC_EVIDENCE
USER_EXPLICIT
HERMES_SYNTHESIS
INDEPENDENT_REVIEW
WORKER_SELF_REPORT
AUTOMATED_HEURISTIC
```

Supported label families include:

- product accepted/rejected/partially accepted;
- user correction and corrected target;
- scope fidelity;
- correctness/regression;
- tool selection and argument quality;
- planning/DAG quality;
- handoff quality;
- hallucination or unsupported claim;
- privacy/authority violation;
- failure class and root-cause class;
- cleanup/recovery quality;
- chosen/rejected alternative;
- reusable lesson candidate;
- training/evaluation eligibility.

A worker or candidate model cannot make itself training-eligible or certify its
own quality. `WORKER_SELF_REPORT` is evidence to review, not an acceptance label.
User acceptance of a deliverable does not automatically certify every
intermediate turn as a gold response.

## 11. Dataset products

A sealed episode may contribute to different datasets:

### Supervised fine-tuning (`SFT`)

Accepted context-to-response/tool-action examples. The target must be explicitly
selected; final answers are not automatically preferred merely because a Run
closed.

### Preference (`PREFERENCE`)

Chosen/rejected pairs grounded in an explicit user correction, controlled
candidate comparison, or authorized review. Synthetic preference pairs are
labelled synthetic and cannot masquerade as user preference.

### Tool trajectory (`TOOL_POLICY`)

Context, tool schemas, calls, results, recovery, and outcome. Secret fields and
irrelevant large outputs are redacted while preserving structural behavior.

### Failure/repair (`REPAIR`)

Failed attempt, classification, bounded correction, re-execution, and verified
outcome. A workaround without retrying the intended path is not labelled a
framework repair when that path was still available.

### Routing/planning (`ROUTING`)

Task/contract features, direct-versus-swarm choice, participant/model selection,
DAG, cost/latency/outcome, and owner acceptance.

### Evaluation (`EVALUATION`)

Frozen cases, complete transcripts, deterministic evidence, rubric judgments,
and owner validation. Evaluation-only episodes can never enter training data.

## 12. Dataset manifest

```json
{
  "schema_version": "aether.learning-dataset/v1alpha1",
  "dataset_id": "uuid",
  "version": "candidate-1",
  "purpose": "SFT|PREFERENCE|TOOL_POLICY|REPAIR|ROUTING|EVALUATION",
  "source_episode_refs": [],
  "source_label_refs": [],
  "selection_contract_digest": "sha256",
  "transform_version": "versioned-id",
  "redaction_policy_digest": "sha256",
  "consent_coverage": {
    "eligible": 40,
    "total": 42,
    "unknown": 2
  },
  "quality_coverage": {
    "accepted": 35,
    "rejected": 3,
    "quarantined": 4
  },
  "splits": {
    "train": [],
    "development": [],
    "test": []
  },
  "split_policy": "project-task-lineage-isolated",
  "contamination_checks": [],
  "known_limitations": [],
  "content_root_digest": "sha256",
  "sealed_at_utc": "server-timestamp",
  "export_status": "NOT_EXPORTED|EXPORTED|REVOKED"
}
```

Dataset transforms are reproducible and versioned. Dataset bodies are never
built from a query whose filters, redaction policy, or label selection were not
frozen in the manifest.

## 13. Curation pipeline

```text
captured episode
  -> completeness/integrity verification
  -> secret and sensitivity scan
  -> quarantine or redaction review
  -> outcome/quality labels
  -> deduplication within authorized scope
  -> consent/license/IP eligibility
  -> contamination and benchmark-leakage checks
  -> lineage-isolated train/development/test split
  -> immutable dataset candidate
  -> independent/owner review
  -> local export gate
  -> separate future training authorization
```

Splits occur by project/task/use-case lineage, not random turns. Turns from one
conversation or sibling retries cannot straddle training and test sets. Frozen
evaluation cases, judge prompts, expected answers, and benchmark-only episodes
are excluded from training by construction.

A model that designed or saw a hidden benchmark cannot be represented as an
uncontaminated evaluation candidate for that benchmark.

## 14. Privacy, security, and intellectual property

### Persisted rich content may include

- full non-secret user/assistant/worker messages;
- system/profile/skill/context snapshots;
- model-visible tool arguments/results;
- source diffs and evaluation feedback;
- project-specific proprietary content when the project authority admits it.

### Never persist as learning content

- credentials, bearer/API/OAuth tokens, refresh material, private keys;
- secret environment values or credential-pool identities;
- payment data;
- hidden chain-of-thought or inaccessible model internals;
- raw provider/account debug bodies that exceed the admitted model-visible
  exchange;
- content from another project without its authority;
- content whose source/license/consent is known to prohibit the intended use.

Secret detection and redaction happen before persistent content write. When the
system cannot safely classify an item, it records a gap and quarantines the
episode rather than silently calling it complete or training-eligible.

Rich episode content requires project-scoped encryption at rest, restrictive
filesystem permissions, no cross-project content deduplication, and exact access
control. The implementation mechanism is a later engineering decision; failure
to establish it blocks `FULL_EPISODE` capture.

Prompt injection in captured content is data, not instruction. Dataset tooling
must parse it without executing embedded commands or granting tool authority.

## 15. Retention, quotas, deletion, and lineage

- Semantic event trace remains until explicit project forget.
- Sealed learning episodes and curated datasets have no silent time expiry.
- Storage quotas are explicit; reaching a quota pauses capture fail-visibly.
- The owner may prune selected sealed episodes only when dataset/export lineage
  proves they are unused or after recording affected derivatives.
- `project_forget` traverses event, episode, content, label, dataset, and export
  lineage before claiming completion.
- If a local dataset contains the project, normal forget removes/rebuilds or
  revokes it before completion.
- If content was exported or sent to a future trainer, the system reports the
  external derivative and cannot claim erasure until that boundary confirms it.
- `privacy_emergency` deletes local content immediately but reports external and
  operational disposition honestly as unknown when it cannot be proven.
- A revoked episode/dataset is excluded from future exports. Revocation does not
  falsely claim that a previously trained model has been “untrained.”

## 16. MCP control surface

The design adds four Hermes-only tools:

### `learning_capture`

Set, reduce, pause, resume, inspect, or seal capture under an admitted policy.
Escalation requires authority and never backfills missing content.

### `learning_label`

Append versioned outcome, correction, preference, failure, quality, eligibility,
or retraction labels with explicit authority and evidence.

### `learning_dataset`

Inspect, build, validate, seal, or revoke a local dataset candidate from sealed
episodes using a frozen selection/transform/split contract.

### `learning_export`

Create a redacted local export at an exact authorized destination. It does not
upload data, call a training provider, spend money, fine-tune a model, change a
route, or promote a candidate.

Workers cannot call these tools directly. They may emit observations that Hermes
later labels or admits.

## 17. Improvement and training authority

Episode capture does not imply:

- that an episode is good training data;
- that a user correction generalizes globally;
- that a dataset is uncontaminated;
- permission to upload data;
- permission to spend money;
- permission to fine-tune or modify a model;
- permission to change prompts, profiles, skills, routing, or policy;
- causal evidence that Aether improved;
- permission to activate, deploy, merge, tag, or release.

Those are separate gates under PDR-0009 and current owner authority. A future
fine-tuning candidate requires a frozen baseline, dataset, evaluator, holdout,
metrics, rollback, and owner-authorized training/promotion boundary.

## 18. Design acceptance criteria

The learning-trace design is complete only when owner acceptance covers:

1. full secret-redacted model-visible episodes as the primary learning source;
2. no hidden chain-of-thought capture;
3. project/user consent and cross-project isolation;
4. immutable sealing, label authority, and dataset lineage;
5. train/development/test contamination controls;
6. no automatic export, training, prompt change, routing change, or promotion;
7. fail-visible quotas, gaps, quarantine, revocation, and deletion semantics;
8. exact conformance and learning-value use cases.

Implementation remains a later, separately authorized horizon.
