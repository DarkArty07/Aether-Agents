# v0.23.0 Aether MCP Tool-Surface Learning and Optimization Plan

> **Status:** PROPOSED DESIGN — DISCUSSION IN PROGRESS; IMPLEMENTATION NOT AUTHORIZED
> **Date:** 2026-08-11
> **Product owner:** Christopher (DarkArty07)
> **Current release:** v0.23.0 Orca Production Dogfood and MCP Optimization
> **Governing decision:** `../../decisions/PDR-0014-versioned-orca-production-adoption.md`
> **Roadmap:** `ROADMAP.md`
> **Current evidence:** `M1_3_TOOL_QUALIFICATION_CHECKPOINT.md`

## 1. Approved product boundary

The following decisions are approved:

1. v0.23.0 is the active release for learning, testing, debugging, and optimizing Aether MCP through real use.
2. v0.23.0 does not end merely because the current 15-tool surface becomes callable or one model-backed Task passes.
3. Tool descriptions, progressive disclosure, sequencing guidance, error usability, cognitive load, context cost, recovery behavior, and a possible smaller normal-use surface all belong to v0.23.0 investigation.
4. The current 15 tools remain the operative compatibility baseline until a later evidence-backed tool-surface decision explicitly changes that contract.
5. v0.24.0 does not start automatically after v0.23.0 acceptance or release. It requires a new explicit product-owner decision.
6. Process-specific workflow migration remains outside v0.23.0 unless the product owner explicitly changes that boundary.

The following are proposals, not approved architecture:

- enriching all 15 MCP tool and field descriptions;
- returning machine-readable next-action guidance;
- exposing approximately five intent-level tools for ordinary Hermes use;
- retaining the existing 15 operations as a diagnostic or advanced toolset;
- hiding low-level Orca catalog/planning operations from the normal surface;
- selecting any exact names, actions, compatibility aliases, or deprecation schedule.

## 2. Goal

Make Aether MCP understandable and efficient for Hermes without sacrificing exact authority, typed effects, reversibility, traceability, recovery, or access to low-level diagnostics.

The product question is:

> Can Hermes select and sequence the correct Aether MCP operation with less injected context, fewer avoidable calls, fewer invalid inputs, and no loss of safety or diagnostic power?

## 3. Current verified baseline

The installed v0.23.0 candidate exposes 15 callable tools. The first bounded qualification invoked every tool, closed its Run with zero survivors, found and corrected one FastMCP string-coercion defect, and identified usability gaps:

- every description is currently equivalent to `Aether operational capability: <name>`;
- tool preconditions and valid target identities are not visible in the catalog summary;
- Hermes must carry project, Run, Task, Dispatch, operation, contract, effect, and participant identities across calls;
- `swarm_message` requires a successful Dispatch and exact admitted participants;
- `swarm_reconcile` currently reconciles uncertain `swarm_start` operations, not arbitrary Tasks or Dispatches;
- `orca_call` validates and plans a read-only command but does not execute it;
- fixture workers are admitted by the manifest schema but unavailable in the active production binding;
- the full model-backed `dispatch -> message -> retry -> artifact` path remains pending.

This is the baseline to improve, not evidence that a smaller surface is already better.

## 4. Non-goals

This plan does not authorize or include:

- implementation during the current documentation task;
- deletion, renaming, hiding, or deprecation of an existing tool;
- automatic composition that conceals model, cost, credential, mutation, or publication effects;
- changes to Hermes core merely to compensate for weak MCP metadata;
- rebuilding Orca Run, Task, Dispatch, worker, message, worktree, recovery, or cleanup mechanics inside Aether;
- process-specific workflow migration;
- v0.24.0 implementation or planning activation;
- credentials, account changes, provider substitution, PAYG enablement, unbounded model use, deployment, merge, tag, or Release.

## 5. Design principles

1. **Intent before mechanics.** Hermes should express the product Task and acceptance contract; Aether MCP should carry mechanical correlations where it can do so without hiding authority.
2. **Progressive disclosure.** Keep the catalog summary short, load the full schema only when selected, and return conditional guidance only when relevant.
3. **Explicit effects.** A convenience tool must not hide model usage, mutation, cost, credentials, activation, publication, or destructive effects.
4. **One authority.** A higher-level surface composes the same Aether MCP and public Orca authority; it cannot introduce a second lifecycle store or coordinator.
5. **Typed recovery.** Unknown effects reconcile before retry. Errors state required state, safe retry semantics, and the exact next operation when deterministically known.
6. **Diagnostics remain available.** Reducing the ordinary surface must not remove the operations required to inspect, reproduce, reconcile, cancel, close, or trace an incident.
7. **Evidence before removal.** Tool count is not an optimization metric by itself. Fewer tools must improve the measured workflow without creating a giant ambiguous schema.
8. **No automatic version progression.** Completion of a v0.23.0 experiment does not open v0.24.0.

## 6. Progressive context contract

### 6.1 Catalog summary

The first sentence of each tool description should be short and self-contained so Hermes Tool Search can select the correct tool without loading the full schema. It should state the trigger rather than repeat the tool name.

Candidate examples, not frozen wording:

- `swarm_dispatch`: `Dispatch ready Tasks in an existing Run.`
- `swarm_message`: `Message an admitted participant in an active Run.`
- `swarm_reconcile`: `Reconcile an uncertain swarm_start operation.`
- `orca_call`: `Plan a validated read-only Orca CLI call.`

### 6.2 Full tool description

When the schema is loaded, every public tool should explain:

1. when to use it;
2. required prior state;
3. accepted identity type;
4. possible effects, including model or cost implications;
5. successful return and authoritative source;
6. normal next operation;
7. when not to use it;
8. reconcile and retry behavior.

### 6.3 Field descriptions

Opaque identifiers and control fields should identify their producer and consumer. For example, a field should say whether it expects a `project_id`, `run_id`, `task_id`, `dispatch_id`, or idempotent operation ID and which preceding operation returns it.

### 6.4 Result guidance

A candidate structured guidance block may contain:

```text
required_state
blocking_condition
recommended_next_tool
required_ids
safe_to_retry
reconcile_before_retry
protected_effect
```

This block is proposed. It must not fabricate a next action when product judgment or owner authority is required. In that case the result must expose the blocker and leave the decision with Hermes or the user.

### 6.5 Server-level instructions

Server instructions may summarize the lifecycle once, but they must not become a large always-injected manual. Tool descriptions and typed results remain the primary just-in-time surfaces.

## 7. Candidate surface alternatives

### Alternative A — Keep 15 tools and enrich metadata

Preserve all names and operation boundaries. Add concise descriptions, field documentation, effect warnings, and typed next-action guidance.

Advantages:

- smallest compatibility risk;
- clearest effect-specific schemas;
- direct mapping to existing tests and trace operations;
- immediate improvement without a new orchestration abstraction.

Risks:

- Hermes still carries substantial lifecycle identity and sequencing state;
- the normal catalog remains larger than the user-intent surface.

### Alternative B — Intent-level normal surface plus diagnostic tools

Expose a small ordinary surface conceptually similar to:

```text
aether_run
aether_status
aether_message
aether_stop
aether_evidence
```

Retain the existing operations in a separately discoverable diagnostic surface. Exact names, count, composition boundaries, and visibility are undecided.

Advantages:

- normal interaction is closer to product intent;
- mechanical IDs and safe sequence transitions can be carried by Aether MCP;
- low-level recovery remains available when needed.

Risks:

- convenience operations could conceal effects or over-compose product decisions;
- compatibility, authorization, idempotency, and partial-failure semantics become more demanding;
- a poorly designed high-level tool can become a giant ambiguous schema.

### Alternative C — Selective grouping

Group only strongly related read-only or lifecycle-equivalent operations while preserving distinct mutation and recovery tools.

Advantages:

- moderate reduction with less orchestration hidden than Alternative B.

Risks:

- may reduce names without reducing real cognitive complexity;
- discriminated unions can make schemas harder for models to call correctly.

No alternative is selected by this plan.

## 8. Evidence program

### O0 — Preserve the current baseline

**Status:** COMPLETE FOR THE FIRST FIXTURE-FIRST PASS; MODEL-BACKED PATH PENDING.

Evidence:

- all 15 tools invoked;
- exact successes, typed denials, and defect preserved;
- one FastMCP facade defect corrected through RED/GREEN;
- installed fresh-process discovery proves exactly 15 tools;
- bounded Run closed with zero survivors;
- no model-backed worker used.

Canonical record: `M1_3_TOOL_QUALIFICATION_CHECKPOINT.md`.

### O1 — Freeze the guidance contract

**Status:** PROPOSED; DISCUSSION REQUIRED.

Deliverables:

- exact description template and length budget;
- property-description convention;
- error and next-action guidance schema;
- effect/cost wording rules;
- list of information that remains always visible versus loaded on demand;
- compatibility and schema-digest impact assessment;
- explicit cases where the server must not recommend a next action.

**Gate:** product owner approves or corrects the guidance contract. Approval of O1 authorizes design only unless implementation is separately authorized.

### O2 — Pre-register the comparison

Freeze the model, provider/account class, initial context, tool catalog, cases, evaluator, thresholds, timeout, cost ceiling, cleanup, and rollback before changing descriptions or surface visibility.

Minimum case families:

1. project admission and inspection;
2. validate, start, and status;
3. unavailable worker capability;
4. dispatch and participant messaging;
5. uncertain start reconciliation;
6. authorized and unauthorized retry;
7. cancel, close, and zero survivors;
8. trace record and query;
9. Orca search, describe, and plan-only call;
10. one bounded real artifact-producing Task.

Minimum metrics:

- scope fidelity and correct final outcome;
- first correct tool selection;
- avoidable wrong-order calls;
- `INVALID_INPUT` and precondition failures;
- calls and tokens to first useful action;
- total calls, latency, and reported cost;
- user corrections and manual steering;
- hidden or unauthorized effects;
- recovery correctness and zero-survivor cleanup;
- diagnostic sufficiency after failure.

Mandatory safety thresholds are zero hidden protected effects, zero silent fallback, zero foreign-resource mutation, and complete attempt-owned cleanup. Comparative improvement thresholds are frozen only after the baseline distribution exists.

### O3 — Implement compatible metadata improvements

**Status:** BLOCKED ON O1 APPROVAL AND IMPLEMENTATION AUTHORIZATION.

Expected files:

- modify `src/aether_mcp/server.py` for versioned tool descriptions;
- modify `src/aether_mcp/protocol.py` only if field/result descriptions require protocol metadata;
- modify `tests/aether_mcp/test_operational_server.py` for exact catalog and metadata assertions;
- add focused protocol/schema tests under `tests/aether_mcp/` when response guidance changes;
- update `docs/reference/` and v0.23.0 evidence after behavior is verified.

Execution discipline:

1. add failing metadata and behavior tests;
2. prove RED against the current generic descriptions;
3. implement the smallest compatible description/guidance change;
4. run focused tests, full Aether MCP tests, Ruff, compileall, wheel build, isolated install, MCP handshake, and Tool Search discovery;
5. restart/reload the named session only under the relevant operational authority;
6. rerun the same case set;
7. record prompt-cache invalidation and loaded-versus-on-disk identity;
8. roll back if the candidate increases wrong calls or obscures effects.

### O4 — Complete the model-backed M1.3 path

Use the accepted provider/model/account/budget contract to prove:

```text
validate
-> start
-> dispatch
-> status
-> message
-> bounded failure or retry when pre-registered
-> artifact verification
-> cancel or semantic close
-> zero-survivor cleanup
-> trace review
```

A model gate remains separately authorized. A fixture cannot replace this evidence.

### O5 — Design an intent-level candidate

**Status:** NOT STARTED; NO IMPLEMENTATION AUTHORITY.

Only after O3/O4 evidence exists:

- inventory which inputs are product intent versus mechanical correlation;
- define which effects may be safely composed and which must remain separate;
- define partial-success, idempotency, reconciliation, resume, cancellation, and rollback semantics;
- preserve coordinator-only visibility and worker toolset restrictions;
- decide whether low-level operations remain public, advanced, diagnostic, or internal;
- produce exact schemas and compatibility policy for discussion.

### O6 — Compare candidates under equivalent conditions

Compare at least:

- baseline: current 15 generic descriptions;
- candidate A: 15 enriched tools;
- candidate B only if approved for implementation: intent-level normal surface plus diagnostics.

Use the same model, provider/account class, case inputs, acceptance authority, timeout, and evaluator. A candidate cannot change its cases or thresholds.

### O7 — Product-owner tool-surface decision

The product owner selects one disposition:

- `KEEP_15_ENRICHED`;
- `ADOPT_INTENT_PLUS_DIAGNOSTIC`;
- `ADOPT_SELECTIVE_GROUPING`;
- `INSUFFICIENT_CONTINUE_V0_23`;
- `REJECT_AND_ROLL_BACK`.

No tool is removed, hidden, renamed, or deprecated before this decision and its compatibility gate.

### O8 — Harden and release within v0.23.0

Integrate the selected surface into status, doctor, setup, restart/rebind, rollback, reference documentation, privacy review, clean-install verification, and exact-candidate acceptance. Continued incidents remain v0.23.0 product work until explicitly accepted, deferred, or blocked.

## 9. Verification matrix

| Claim | Required evidence |
|---|---|
| Descriptions improve selection | Frozen equivalent cases show fewer avoidable wrong selections without lower outcome quality |
| Context is reduced | Measured always-visible and loaded-on-demand tokens, not prose estimates |
| High-level composition is safe | Exact effect, idempotency, partial-failure, reconcile, retry, cancel, and rollback tests |
| Diagnostics remain sufficient | Incidents can still be reproduced and closed using admitted diagnostic operations |
| No authority moved | Hermes/Aether/Orca ownership invariants and worker visibility tests remain green |
| Runtime converged | Source, built wheel, installed package, MCP process, discovered catalog, and prompt cache identities agree |
| Cleanup remains correct | Zero attempt-owned survivors and zero foreign-resource mutation |
| Improvement is causal enough to accept | Same model and equivalent initial conditions; frozen evaluator and thresholds; regressions reported |

## 10. Rollback

Every candidate preserves:

- the exact current 15-tool source and wheel;
- active Hermes configuration backup and file mode;
- prior tool catalog and descriptions;
- rollback registration command/path;
- attempt-owned Run/Task/Dispatch/worktree/terminal correlations;
- diagnostic evidence and protected project data.

Rollback restores the accepted v0.23.0 surface and requires a fresh MCP process plus catalog readback. It does not authorize Olympus, ACP, Harmonia, `talk_to`, dual-write, or silent fallback.

## 11. Open discussion agenda

The following decisions remain open for later discussion:

1. whether enriched descriptions alone remove enough cognitive load;
2. which mechanical identities Aether MCP may carry automatically without hiding authority;
3. the exact normal-use tool count and names;
4. whether diagnostic tools remain discoverable by default or load only on demand;
5. whether next-action guidance belongs in every result or only typed errors and transitional states;
6. compatibility and deprecation policy if a smaller surface is accepted;
7. benchmark cases and comparative thresholds after the first baseline distribution is measured.

These are not user homework required to finish this documentation task. They define the next design discussion.

## 12. Current stop condition

This plan is complete as a planning artifact when the roadmap, decision record, active status, documentation index, and v0.24 gate agree that:

- MCP learning and optimization continue in v0.23.0;
- the five-tool concept is a proposal rather than an approved architecture;
- the 15-tool surface remains the current compatibility baseline;
- implementation remains separately gated;
- v0.24.0 remains inactive until an explicit product-owner decision.
