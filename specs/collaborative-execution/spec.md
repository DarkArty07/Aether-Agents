# Collaborative contract stewardship — scope extraction

**Status:** owner-approved objective and material design. Finalized Objective Contract `oc_a28ff9b7fa20d29d@v1` supplies the execution handoff after its validation/finalization; this specification is its owning design reference.
**Canonical objective Issue:** #334. Related dispositions: #317 and #407.
**Inspected Aether base:** `aaeacb211b892b5dd893ecaa4abba7933011d12c`.

## Accepted owner direction

The owner now prioritizes a coordinated change that makes Morfeo an active design/intent steward while Supervisor executes an Objective Contract, adopts the reviewed change into the provisioned runtime, and reconciles #334, #317 and #407 in one closeout. This supersedes #334's previously deferred-priority request. The latest owner instruction is to write the plan first, then proceed autonomously through implementation and runtime adoption. The plan was materialized before implementation; Supervisor receives the finalized contract only after material design is complete.

The owner explicitly accepts closure as an **unverified behavioral mitigation**: future real work will reveal whether the long-duration non-convergence recurs. No statement of permanent prevention, elapsed-time improvement, organic qualification, or successful completion of the stopped Telegram Monitor follows from this closure. #407 is already closed as a stopped-objective postmortem; it must not be relabeled as functional acceptance of #367.

The approved coordinated delivery uses one principal Aether PR and one linked, narrowly bounded maintained-Hermes-fork dependency because native intermediate delivery needs changes. Unreviewed local edits are not an alternative to maintained-fork delivery.

## Outcome and preserved role boundaries

Morfeo remains involved in material design, assumption and outcome questions during a contract, rather than only at initial handoff and terminal reception. Supervisor keeps execution breakdown, worker direction, review, integration and normal closeout. Implementer keeps unit-local implementation and reversible judgement. Collaboration does not transfer writable ownership or replace independent review.

A complete design must cover both explicit requests for help **and proactive consideration of relevant intermediate evidence**. A design that wakes Morfeo only after Supervisor labels a problem a contract defect does not fully satisfy the requested change.

Advice derived from an existing contract may clarify its application without silently changing obligations. Changes to material design/specification are recorded by Morfeo in the owning artifact, and finalized contract changes require supersession through the existing capability. Owner-reserved intent, acceptance and authority remain owner decisions. Unaffected independent work continues; only actually dependent work waits.

## Scope surfaces, not implementation units

1. **Normative coordination:** reconcile `DESIGN.md` role/communication/flow wording, R6 communication requirements and R7 convergence/flow routing. The present terminal-only origin wording must distinguish internal collaboration with Morfeo from owner-facing notifications. Reconcile R1/R2 and `specs/006-contract-execution-quality/` only where they state an affected interaction or adoption obligation; do not rewrite all stages.
2. **Role resources:** targeted amendments in the existing nine-sector `SOUL.md` files for Morfeo, Supervisor and Implementer. Keep the sector organization. Reuse existing sufficient-design, convergence, verification and independent-review obligations; do not create case-specific Telegram rules or duplicate every requirement.
3. **Canonical procedures:** adapt the existing `objective-contract-design`, `supervisor-decomposition`, `implementation-evidence` and, only for the early-advice/final-acceptance distinction, `contract-result-review` procedures. Clarify intermediate requests, evidence references, receipt, response and resolution. The Project Canonical observation procedure remains a read model, not a controller.
4. **Native runtime integration:** reuse board comments/events, subscription and flow identity, existing run/steering and continuation paths. Determine whether the installed/provisioned sources already support exact-recipient intermediate delivery and recoverable consumption; fill only demonstrated gaps. No parallel messaging bus, separate scheduler, additional role or generic automatic convergence judge is implied.
5. **Distribution/adoption:** use the existing package/profile/skill lifecycle. Install the reviewed source resources into the provisioned runtime, preserve owner configuration and unrelated profile data, verify identities and hashes, and establish when fresh/resumed sessions actually load the new instructions. Do not claim live adoption from source bytes alone; do not interrupt active workers to force adoption.
6. **Documentation/status/issue closeout:** update the execution guide, affected `AGENTS.md` guidance and capability traceability consistently. Reconcile #334 as the scoped capability/mitigation actually delivered, #317 as owner-directed closure of its open-ended observation requirement without invented organic PASS, and #407 by linking the mitigation to its preserved findings. Preserve historical contracts and evidence.

## Acceptance requirements

The observable requirement identifiers below are the unit/reception coverage keys. `plan.md` D1–D9 owns the mechanism and bounded local freedom. Supervisor supplies the execution breakdown, not a second product design.

| ID | Required outcome / oracle |
| --- | --- |
| CE-01 | Opt-in root captures the exact trusted origin and unique board/Project/contract/flow binding. Legacy roots remain unchanged; conflicting/absent/archived bindings reject before cross-role delivery. |
| CE-02 | An explicit source-backed peer question can be persisted and addressed before the source unit completes. Owner/task/run provenance is runtime-derived; no worker-provided session/author impersonation. |
| CE-03 | Native intermediate evidence produces an origin advisory without requiring Supervisor to label it a design defect. Busy-origin notices coalesce without deleting explicit requests; heartbeat/tool chatter and response-generated loops stay silent. |
| CE-04 | Persistence, enqueue, recipient acknowledgment, response and requester disposition are distinguishable in the existing board. Failed enqueue/process loss preserves recoverable unconsumed work; duplicate retries do not create duplicate resolutions or another worker. |
| CE-05 | A addressed peer receives source/evidence and original revision as non-owner content. An ordinary peer comment cannot become an out-of-band owner instruction. Invalid/malicious or transport-truncated input cannot silently widen authority or persist a partial request. |
| CE-06 | TUI and Telegram/gateway use the existing exact-origin delivery/continuation paths. Busy sessions are not run concurrently; missing/closed origin is visible/unavailable, not rerouted. Internal collaboration does not emit a passive human notification per exchange. |
| CE-07 | Active/idle same-affinity Supervisor can consume an addressed consultation without losing its execution role, lease, canonical workspace or parent gating. Advisory resolution never unblocks an unrelated parent. Independent implementation work is not halted. |
| CE-08 | Advice refers to the original source revision and is revalidated after resume; superseded contract/ended flow messages become stale. Decomposition-root completion alone must not expire collaboration. No completed unit or stopped monitor is restarted. |
| CE-09 | Morfeo's authored direction and Supervisor/Implementer responsibilities are reconciled in existing sectorized SOUL, existing skills and affected normative docs; owner authority, final independent review, scope and three-role boundary remain intact. |
| CE-10 | The maintained fork contains the reviewed native correction; Aether distribution contains coherent resources, lifecycle/manifest/ledger changes and tests. No hidden unversioned live implementation. |
| CE-11 | Reviewed source is adopted into the provisioned runtime with rollback, installed-byte and schema/load readback, no interference with active workers/unrelated data. Fresh-session loading is distinguished from cached-session behavior and from LLM compliance. |
| CE-12 | Coordinated normal GitHub closeout reaches green reviewed merges and objective-owned cleanup. #334 and #317 close with explicitly unverified long-term efficacy; #407 receives the mitigation reference without rewriting its historical failed acceptance. Release impact/action/channel are stated separately. |

## Testing standard — accepted with autonomous execution

The owner approved the proposed bounded mechanical/resource checks and runtime adoption, while explicitly declining an open-ended behavioral/non-recurrence campaign. Testing follows `quickstart.md`: isolated native SQLite/API/lifecycle/consumer tests for CE-01..08, resource/static/docs/package/lifecycle checks for CE-09..11, and the normal required CI path for CE-12. No model/provider/Telegram-effect qualification campaign is required or implicitly authorized; ordinary pipeline agent executions still use the already provisioned routes.

Resource presence, test counts and mocked final outputs are not evidence of organic collaboration quality. Deterministic fake delivery sinks may measure the native delivery branch, and must be labeled as such; data/state/API behavior uses actual native functions and disposable databases. Final installation readback uses the real native loader and tool registry without launching a model conversation. Missing code/import failures or failed required gates are not waived by accepting unverified long-term efficacy. No fixed wait or absence-of-incidents gate is required for issue closure.

No task-specific testing choices are left for Implementer to invent. Equivalent local fixture organization is free; acceptance, limits and positive/negative cases are not.

## Excluded

- Rebuilding or reactivating the stopped Telegram Monitor or rerunning its laboratory.
- A new broker, A2A/MCP inter-role channel, permanent watchdog, dashboard, model/provider, credential, worker pool, fourth role or generalized reliability framework.
- Automatically choosing strategy, acceptance or work route by score, keyword classifier, review-count threshold or elapsed time.
- Giving Morfeo ownership of Supervisor's implementation units or approval of code it authored.
- Retrospective edits to finalized contracts, cleanup of unrelated branches/boards, unrelated fixes or publication of private runtime state.
- Package publication, tags, release-channel changes or unrelated deployment. Local activation is distinct from a public release.

## Readiness

The owner has approved execution. `plan.md` D1-D9 settles material interfaces, native storage/consumption, role amendments, safety boundaries and adoption; `quickstart.md` settles the testing standard. Contract `oc_a28ff9b7fa20d29d@v1` is authored through the canonical tool using the verified portable UUID and an isolated authoring workspace in the same Git repository; it becomes handoff authority only when finalized and committed. Structural validation and Morfeo's design sufficiency check precede Supervisor receipt; no independent Supervisor review is claimed here. Project knowledge/work-memory were unavailable during initial source inspection, as recorded in research.md, and no graph result was substituted. There are no implementation units authored by Morfeo.
