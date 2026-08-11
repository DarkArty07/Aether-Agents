"""Canonical just-in-time guidance for the public Aether MCP tool surface."""

from __future__ import annotations

TOOL_DESCRIPTIONS: dict[str, str] = {
    "project_admit": """Admit one exact local project root without starting a Run, Task, or worker.
WHEN: A local project must enter the trusted Aether boundary before any Run is designed.
REQUIRES: A canonical absolute project_root, fresh operation metadata, safe alias, capture policy, and real consent authority reference.
ACCEPTS: One exact admission intent for one local root.
EFFECT: LOCAL_APPEND_ONLY admission metadata; no Run, Task, Dispatch, worker, or model is started.
RETURNS: The authoritative project_id and admission evidence for later calls.
NEXT: project_inspect; use swarm_validate only after the complete Task manifest exists.
DO NOT USE FOR: Inspecting an existing admission, admitting a foreign root, or granting provider, model, spending, or publication authority.
RETRY / RECONCILE: Reuse operation_id only for byte-equivalent replay; after an unknown result, inspect the exact admission before retrying.""",
    "project_inspect": """Read and freshly verify one trusted project admission by exact project_id.
WHEN: Confirm project identity, root binding, consent, or current admission evidence before another tool uses it.
REQUIRES: The exact project_id returned by project_admit; never derive it from a path or alias.
ACCEPTS: One admitted logical project identity.
EFFECT: READ_ONLY fresh inspection; no admission or runtime state changes.
RETURNS: Verified project binding, policy evidence, and current trusted metadata.
NEXT: State-dependent; swarm_validate is appropriate only when a complete manifest and authority already exist.
DO NOT USE FOR: Admitting a project, inventing authority, or discovering a project_id from an untrusted path.
RETRY / RECONCILE: A read may be repeated; identity or root conflicts require STOP and owner resolution, not mutation.""",
    "swarm_validate": """Validate a complete manifest, DAG, authority, and provider binding without starting a Run.
WHEN: A bounded multi-agent Task manifest is complete and must be checked before Run creation.
REQUIRES: Exact admitted project identity, complete tasks and dependencies, participant policy, effects, acceptance, and provider binding authority.
ACCEPTS: The full immutable manifest candidate, not a partial task fragment.
EFFECT: READ_ONLY validation; no Run, Task, Dispatch, worker, or model is started.
RETURNS: A validated manifest digest/reference or typed defects that must be corrected.
NEXT: swarm_start only after validation succeeds and start authority remains valid.
DO NOT USE FOR: Choosing product meaning, filling missing authority, dispatching workers, or validating an unrelated project.
RETRY / RECONCILE: Correct deterministic defects and revalidate; no reconciliation is needed because validation has no intended mutation.""",
    "swarm_start": """Create the admitted Orca Run and Tasks from a validated manifest without dispatching workers.
WHEN: swarm_validate succeeded for the exact manifest and Run creation is authorized.
REQUIRES: Fresh operation metadata plus exact manifest_digest, manifest_ref, provider_binding_digest, and admitted project/contract identities.
ACCEPTS: One byte-equivalent validated start intent; dispatch_ready does not authorize dispatch.
EFFECT: LOCAL_REVERSIBLE Run/Task creation through Orca; this does not start a worker or invoke a model.
RETURNS: Authoritative run_id, logical task_ids/task_keys, and provider correlation evidence.
NEXT: swarm_status; swarm_dispatch only for ready Tasks under separate worker/provider/model authority.
DO NOT USE FOR: Dispatch, implicit specialist selection, unvalidated manifests, or automatic model execution.
RETRY / RECONCILE: If the start effect is unknown, do not retry; call swarm_reconcile with the prior swarm_start operation_id.""",
    "swarm_status": """Read current Run, Task, question, evidence, or resource state; bounded wait is read-only.
WHEN: Observe progress, readiness, terminal evidence, questions, cleanup, or survivor state for one admitted Run.
REQUIRES: Exact project_id and run_id returned by authoritative Aether MCP responses; cursor must come from the same query surface.
ACCEPTS: Summary or bounded detail plus an optional bounded wait.
EFFECT: READ_ONLY observation, including bounded wait; no worker, message, retry, cancel, or close action occurs.
RETURNS: Current typed state, identities, evidence, questions, resources, and an opaque continuation cursor when present.
NEXT: State-dependent; choose dispatch, message, cancel, retry, close, or owner decision only from returned evidence and authority.
DO NOT USE FOR: Assuming semantic acceptance, manufacturing terminal evidence, or polling a foreign Run.
RETRY / RECONCILE: Reads may repeat with bounded waits; preserve cursors and stop on identity or contract conflict.""",
    "swarm_dispatch": """Dispatch ready admitted Tasks; this may start fixture or model workers and use the admitted provider.
WHEN: The Run exists, target task_keys are ready, participants are admitted, and worker/provider/model/effect/budget authority is explicit.
REQUIRES: Fresh operation metadata, exact run_id, ready task_keys, active provider binding, and all execution authority.
ACCEPTS: One bounded dispatch intent for admitted Tasks in the same Run.
EFFECT: LOCAL_REVERSIBLE dispatch; it may invoke the admitted provider/model and start workers, consume quota, and create attempt-owned resources.
RETURNS: Authoritative dispatch_ids, participant identities, provider correlations, and attempt evidence.
NEXT: swarm_status; use swarm_message only with coordinator or participant dispatch_ids returned by successful Dispatches.
DO NOT USE FOR: Selecting product scope, bypassing missing budget/model authority, retrying terminal work, or dispatching unready/foreign Tasks.
RETRY / RECONCILE: Never blindly retry an unknown dispatch effect; inspect status and STOP when exact acceptance cannot be proven.""",
    "swarm_message": """Send structured messages only between the coordinator and participants admitted by successful Dispatches.
WHEN: A running admitted participant needs steering, clarification, evidence, or a decision request within the same Run.
REQUIRES: Exact run_id; sender_id and recipient_id must be coordinator or logical dispatch_ids admitted by successful Dispatches.
ACCEPTS: One typed, secret-safe message with JSON payload text, safe summary, and explicit blocking/decision semantics.
EFFECT: LOCAL_REVERSIBLE delivery plus durable correlation; it does not admit a new participant or grant authority.
RETURNS: Message identity, delivery/correlation evidence, and typed outcome.
NEXT: swarm_status or an owner decision when decision_required is true.
DO NOT USE FOR: Profile names, task_ids, provider IDs, cross-project communication, hidden delegation, or authority grants.
RETRY / RECONCILE: Reuse operation_id only for exact replay; unknown delivery requires status/evidence and must not become duplicate steering.""",
    "swarm_reconcile": """Observe or fence the uncertain effect of a prior swarm_start; this is not generic reconciliation.
WHEN: A prior swarm_start returned an uncertain mutation effect and its exact operation must be observed or fenced before retry.
REQUIRES: Exact project/run identities, fresh reconcile operation metadata, target_type=operation, and target_id equal to the prior swarm_start operation_id.
ACCEPTS: Supported observe or fence mode with admitted evidence sources.
EFFECT: READ_ONLY observation or authorized LOCAL_REVERSIBLE fencing; it does not reconcile arbitrary Tasks, Dispatches, messages, or provider actions.
RETURNS: Typed reconciliation outcome and evidence proving accepted, absent, fenced, or still unknown state.
NEXT: State-dependent; retry start only when the result explicitly proves it safe, otherwise status, owner decision, or STOP.
DO NOT USE FOR: Generic repair, uncertain dispatch, guessed operation IDs, or cross-Run reconciliation.
RETRY / RECONCILE: Reconciliation is itself the required pre-retry boundary; an unresolved unknown remains non-retryable.""",
    "swarm_retry": """Retry one exactly evidenced terminal fixture Dispatch; model-worker retry is unavailable.
WHEN: A fixture Dispatch is terminal, correction is bounded, contract generation still matches, and the admitted retry budget permits another attempt.
REQUIRES: Fresh operation metadata and exact run_id, task_id, prior dispatch_id/outcome, correction summary, and contract_generation from trusted evidence.
ACCEPTS: One corrected retry intent for the same admitted logical Task.
EFFECT: LOCAL_REVERSIBLE new fixture attempt; this candidate does not retry model workers.
RETURNS: A new authoritative dispatch_id/attempt identity and retry evidence.
NEXT: swarm_status.
DO NOT USE FOR: Non-terminal work, model-worker retry, unchanged blind repetition, exhausted budgets, or new product scope.
RETRY / RECONCILE: Never retry a retry with unknown effect; inspect status and STOP unless exact terminal/acceptance evidence proves a safe next action.""",
    "swarm_cancel": """Cancel an admitted Dispatch, Task, or Run, then require status and cleanup verification.
WHEN: Authorized work must stop, be fenced, or enter cleanup before closure.
REQUIRES: Fresh operation metadata, exact run_id, target_type, and matching admitted target_id belonging to that Run.
ACCEPTS: One bounded cancellation intent for a Dispatch, Task, or Run.
EFFECT: LOCAL_REVERSIBLE cancellation/fencing request; cancellation acknowledgement is not proof of zero survivors.
RETURNS: Typed cancellation outcome and affected identities/evidence.
NEXT: swarm_status to verify terminal state, cleanup obligations, and survivors before swarm_close.
DO NOT USE FOR: Foreign resources, semantic rejection without runtime cancellation need, or substituting cancellation for closure.
RETRY / RECONCILE: After an unknown result, inspect status first; repeat only when the returned state and idempotency contract prove it safe.""",
    "swarm_close": """Close a terminal Run and clean attempt-owned resources; fail if work or survivors remain.
WHEN: All Tasks are terminal, acceptance disposition is known, active work is stopped, and cleanup can be verified.
REQUIRES: Fresh operation metadata, exact run_id, explicit effect_plan, retained_resource_ids, and terminal/cleanup evidence.
ACCEPTS: One bounded close-and-cleanup intent for the admitted Run.
EFFECT: Authorized local cleanup and durable closure; it may remove attempt-owned resources but cannot conceal survivors or unresolved work.
RETURNS: Closed outcome, cleanup evidence, retained resources, and any blocking survivor/failure state.
NEXT: swarm_trace or project-level reporting when closure succeeds; otherwise status/cancel/owner decision as mechanically supported.
DO NOT USE FOR: Forcing semantic acceptance, closing active work, deleting foreign resources, or hiding failed cleanup.
RETRY / RECONCILE: Inspect status after incomplete or unknown cleanup; retry only with exact ownership and state evidence.""",
    "swarm_trace": """Query trace or append an authorized decision or evidence event for an admitted project or Run.
WHEN: Read lifecycle history or durably record a real decision/evidence reference without changing Task execution authority.
REQUIRES: Exact project_id; run_id when Run-scoped; action-specific operation, decision, evidence, filters, cursor, and limits.
ACCEPTS: Query, record_decision, or record_evidence under the matching admitted identity and authority.
EFFECT: READ_ONLY for query; LOCAL_APPEND_ONLY for authorized decision/evidence records.
RETURNS: Ordered trace entries, durable record identity, evidence references, and opaque cursor where applicable.
NEXT: State-dependent; tracing never authorizes a mutation by itself.
DO NOT USE FOR: Fabricating acceptance, storing secrets/raw transcripts, rewriting history, or granting provider/model authority.
RETRY / RECONCILE: Queries may repeat; append replay must be byte-equivalent under the same operation_id, otherwise STOP on conflict.""",
    "orca_search": """Search admitted read-only Orca public commands by intent without executing them.
WHEN: The exact read-only Orca command is unknown and must be discovered from the admitted catalog.
REQUIRES: Exact project_id, bounded intent query, READ_ONLY effect filter, and result limit.
ACCEPTS: Search terms for public commands in the current bound Orca catalog.
EFFECT: READ_ONLY catalog search; no argv is executed and no Run, Task, or worker is created.
RETURNS: Matching command_ids, summaries, effects, and current catalog_digest.
NEXT: orca_describe with one exact command_id and returned catalog_digest.
DO NOT USE FOR: Mutable/private commands, execution, arbitrary shell discovery, or bypassing Aether MCP lifecycle tools.
RETRY / RECONCILE: Read-only search may repeat; catalog drift requires a fresh search rather than reusing stale command identity.""",
    "orca_describe": """Load one exact Orca command contract from the current catalog digest without executing it.
WHEN: orca_search identified a command and its arguments/effect contract must be inspected before planning.
REQUIRES: Exact project_id, command_id from search, and the matching current catalog_digest.
ACCEPTS: One admitted public read-only command identity.
EFFECT: READ_ONLY catalog description; no argv is executed.
RETURNS: Command schema, allowed arguments, effect, examples/limits where present, and schema/catalog digests.
NEXT: orca_call only when the described command is read-only, arguments are admitted, and the digest remains current.
DO NOT USE FOR: Guessing command IDs, mutable/private commands, runtime execution, or stale catalogs.
RETRY / RECONCILE: Description may repeat; digest mismatch requires a fresh orca_search, not mutation or guessed arguments.""",
    "orca_call": """Validate and plan one admitted read-only Orca CLI call; return a plan and do not execute it.
WHEN: orca_describe proved one public command is read-only and exact admitted arguments must be converted into a bounded argv plan.
REQUIRES: Exact project_id, command_id, arguments, catalog/schema digests, READ_ONLY expected_effect, reason, and any required operation metadata.
ACCEPTS: One schema-valid read-only planning request for the current catalog.
EFFECT: READ_ONLY validation/planning; this tool does not execute the returned argv, contact a worker, or mutate Orca state.
RETURNS: Validated argv plan, command/effect identity, and digest evidence.
NEXT: State-dependent external execution is not authorized by this result; Hermes must respect the current task and effect boundary.
DO NOT USE FOR: Mutable commands, shell execution, bypassing swarm tools, stale digests, or turning a plan into implicit authority.
RETRY / RECONCILE: Planning may repeat with the same current inputs; schema/catalog drift requires search and describe again.""",
}
