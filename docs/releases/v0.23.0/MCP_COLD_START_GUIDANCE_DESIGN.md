# v0.23.x Aether MCP Cold-Start Guidance Design

> **Status:** APPROVED DESIGN — IMPLEMENTATION AND ACTIVATION NOT AUTHORIZED
> **Recorded:** 2026-08-11 UTC
> **Product owner:** Christopher (DarkArty07)
> **Scope:** v0.23.x Aether MCP cold-session usability
> **Governing decision:** `../../decisions/PDR-0014-versioned-orca-production-adoption.md`
> **Parent plan:** `MCP_TOOL_SURFACE_LEARNING_PLAN.md`
> **Implementation plan:** `MCP_COLD_START_IMPLEMENTATION_PLAN.md`
> **Resume record:** `MCP_COLD_START_HANDOFF.md`

## 1. Decision

v0.23.x will make correct Aether MCP use available to Hermes in a cold session
without depending on conversation history, persistent memory, project-local
rules, or Hermes choosing to load an optional skill.

The approved architecture assigns each kind of guidance to the surface that can
reliably own it:

1. the Aether Hermes `SOUL.md` candidate carries a small mandatory boot contract;
2. MCP tool descriptions teach discovery, purpose, preconditions and effects;
3. JSON Schema property descriptions teach exact input and identity provenance;
4. typed results and errors provide state-dependent recovery guidance;
5. controlled cold-session evaluation proves the combined behavior before any
   prompt promotion or installed-runtime activation.

The current 15 callable tools remain the compatibility baseline. This design does
not remove, hide, rename, group or deprecate any tool. A smaller intent-level
surface remains a later comparative hypothesis, not part of this design.

## 2. Observed problem

The first M1.3 qualification found that all 15 tools were callable but each was
advertised with a description equivalent to:

```text
Aether operational capability: <tool_name>
```

That identifies an operation but does not teach the state machine required to use
it. Hermes had to infer or reverse-engineer:

- which tool begins a lifecycle;
- which prior state is required;
- which call produces each identifier;
- which identifiers are caller-generated versus server-generated;
- whether a call can create a worker or invoke a model;
- whether an uncertain effect must reconcile before retry;
- whether a denial is recoverable, terminal, or requires owner authority;
- whether the operation executes behavior or only validates/plans it.

Concrete examples are preserved in `M1_3_TOOL_QUALIFICATION_CHECKPOINT.md`:

- `swarm_message` requires participants admitted by successful Dispatches;
- `swarm_reconcile` currently reconciles uncertain `swarm_start` operations,
  not arbitrary Tasks or Dispatches;
- `orca_call` validates and plans one read-only public command but does not
  execute it;
- fixture workers are schema-admitted but unavailable in the active binding;
- FastMCP incorrectly coerced JSON-shaped strings before the accepted correction.

The primary product defect is therefore not proven to be the count of tools. It
is that the surface does not teach its own operational grammar at the point of
use.

## 3. Goal and acceptance meaning

### 3.1 Goal

A cold Hermes session should be able to decide whether Aether MCP is appropriate,
discover the correct operation, supply correctly sourced identities, respect
authority and effect gates, recover safely, and close cleanly without loading an
Aether skill or inspecting Aether MCP source code.

### 3.2 Meaning of “always”

No stochastic model can be given an unbounded mathematical guarantee. For this
release, “Hermes always knows how to use the MCP” means:

- every frozen mandatory case passes in every authorized independent repetition;
- no repetition uses an Aether skill to recover the protocol;
- no repetition invents an identifier or protected authority;
- no repetition performs a hidden effect or legacy fallback;
- every started Run reaches a verified terminal disposition with complete
  attempt-owned cleanup;
- claims are limited to the exact tested prompt, model, provider class, Hermes
  build, MCP catalog, schema digest and case distribution.

A result outside that tested identity is `UNKNOWN`, not automatically a pass.

## 4. Non-goals

This design does not authorize or include:

- editing active `home/SOUL.md`;
- modifying Hermes Agent core system-prompt code;
- implementing tool metadata, schema annotations or response guidance;
- installing a wheel, restarting Hermes, reloading MCP, or mutating runtime state;
- starting a Run, Task, Dispatch, worker or model call;
- modifying provider accounts, credentials, budgets or PAYG policy;
- promoting Hermes Prompt 3.0.0 or replacing the active 2.0.0 prompt;
- using skills, memory or `AGENTS.md` as the required protocol-teaching layer;
- relying on MCP server-level `instructions` that Hermes does not currently
  expose to the model;
- reducing the 15-tool catalog;
- beginning v0.24.0 work.

## 5. Verified Hermes presentation model

Hermes Agent 0.19.1 builds one system prompt at session creation and caches it for
the life of the agent. Its stable tier begins with `SOUL.md`; project rules such
as `AGENTS.md` belong to a separate context tier. Consequently:

- a new cold session receives the current active `SOUL.md` automatically;
- an already-open session does not acquire a changed SOUL mid-session;
- project-local context is not a universal teaching mechanism;
- memory is volatile and must not define protocol authority.

Hermes Tool Search defers MCP/plugin schemas behind `tool_search`,
`tool_describe` and `tool_call`. When the catalog fits its listing budget, Hermes
still sees tool names and short descriptions while full schemas remain deferred.
MCP registration currently forwards each tool's name, description and
`inputSchema` into that catalog.

No code path was found that promotes MCP server-level `instructions` into the
model-visible system prompt. Those instructions may remain useful to other MCP
clients, but v0.23.x acceptance must not depend on them.

Therefore the reliable architecture is:

```text
Hermes cold session
  |
  +-- stable system prompt
  |     `-- active Aether SOUL.md: mandatory boot contract
  |
  +-- Tool Search catalog
  |     `-- names + intent-oriented first sentences
  |
  +-- tool_describe
  |     `-- full description + input schema/property descriptions
  |
  +-- tool_call result
        `-- typed state-dependent guidance and safe error disposition
```

## 6. Layer A — mandatory SOUL boot contract

### 6.1 Ownership

The product-specific guidance belongs in the Aether Hermes `SOUL.md`, which
Hermes places in the stable system-prompt tier. It does not belong in Hermes
Agent's framework-wide base prompt because that would couple every Hermes user to
Aether and create update drift.

The active prompt is still 2.0.0. The prior 3.0.0 candidate was not promoted and
its files are immutable evidence. A future implementation must create a distinct
isolated candidate identified as:

```text
Hermes Prompt candidate 3.0.0-coldstart.1
```

It must derive from the byte-exact active 2.0.0 baseline and make the smallest
routing/cold-start change needed for this contract. It must not silently adopt the
entire rejected 3.0.0 candidate.

### 6.2 Normative candidate block

The future prompt candidate should contain the following semantics. Editorial
changes may improve clarity only if they do not alter the frozen behavior and are
made before the candidate benchmark is frozen.

```text
## Aether MCP and Orca cold-start contract

Hermes may work directly when one accountable owner is the shortest reliable
path. When a Task materially requires multiple admitted workers or specialist
judgment, Aether MCP plus Orca is the only multi-agent execution path.

Resolve the exact project root before MCP work. Admit or inspect the project,
validate the complete Task manifest and authority, then start the Run without
assuming that start dispatches a worker. Dispatch only ready admitted Tasks and
only under explicit provider, model, effect and budget authority. Preserve every
project, Run, Task, Dispatch, operation, contract and participant identity from
its authoritative response; never substitute one identity class for another.

Unknown mutation effects reconcile before retry. Messages require participants
admitted by successful Dispatches. Retry requires exact terminal evidence and an
admitted attempt budget. Before closure, inspect status, stop or fence active
work, close the Run, verify zero attempt-owned survivors, and retain trace
references.

Read the selected tool's complete description and schema when a precondition or
identity is uncertain. Treat typed denials as state evidence, not an invitation
to try unrelated tools. Never use Olympus, ACP, Harmonia, talk_to, aliases,
dual-write or silent fallback to complete a blocked Aether MCP Task.
```

### 6.3 Required behavior, not memorized syntax

The SOUL block teaches invariants and the state machine. It must not contain:

- all 15 full schemas;
- example UUIDs that the model may copy;
- exact current paths, digests, model names or account identities;
- release-temporary incident details;
- credentials, tokens or provider connection data;
- a claim that tool availability authorizes use;
- a command to dispatch automatically whenever multiple files are involved.

### 6.4 Budget

The final added boot contract must be measured with the same tokenizer/accounting
used by the prompt experiment. Design budget:

- target: no more than 300 input tokens;
- hard ceiling: 450 input tokens;
- any exception requires measured improvement and owner acceptance.

The budget applies to net new always-visible prompt content, not the complete
SOUL.

## 7. Layer B — MCP tool descriptions

### 7.1 Description structure

Every description has two deliberate regions:

1. an intent-oriented first sentence used in Tool Search listings;
2. a full just-in-time contract shown by `tool_describe`.

The first sentence must:

- begin with the user-visible intent or lifecycle effect;
- stay at or below 180 characters;
- name the primary precondition when omission would cause a wrong call;
- state model/worker execution when the call can cause it;
- avoid repeating only the tool name.

The full description must stay at or below 1,200 characters and use this order:

```text
WHEN
REQUIRES
ACCEPTS
EFFECT
RETURNS
NEXT
DO NOT USE FOR
RETRY / RECONCILE
```

`NEXT` is advisory. It must be omitted or state `state-dependent` when product
judgment, authorization or runtime evidence is required.

### 7.2 Frozen catalog-summary intent

The implementation may edit wording for grammar before preregistration, but it
must preserve the following exact semantics:

| Tool | Required first-sentence meaning |
|---|---|
| `project_admit` | Admit one exact local project root without starting a Run, Task or worker. |
| `project_inspect` | Read and freshly verify one trusted project admission by exact `project_id`. |
| `swarm_validate` | Validate a complete manifest, DAG, authority and provider binding without starting a Run. |
| `swarm_start` | Create the admitted Orca Run and Tasks from a validated manifest without dispatching workers. |
| `swarm_status` | Read current Run, Task, question, evidence or resource state; bounded wait is read-only. |
| `swarm_dispatch` | Dispatch ready admitted Tasks; this may start fixture/model workers and use the admitted provider. |
| `swarm_message` | Send structured messages only between the coordinator and participants admitted by successful Dispatches. |
| `swarm_reconcile` | Observe or fence the uncertain effect of a prior `swarm_start`; it is not generic reconciliation. |
| `swarm_retry` | Retry one exactly evidenced terminal fixture Dispatch; model-worker retry is unavailable in this candidate. |
| `swarm_cancel` | Cancel an admitted Dispatch, Task or Run and then require status/cleanup verification. |
| `swarm_close` | Close a terminal Run and clean attempt-owned resources; fail if work or survivors remain. |
| `swarm_trace` | Query trace or append an authorized decision/evidence event for an admitted project or Run. |
| `orca_search` | Search admitted read-only Orca public commands by intent without executing them. |
| `orca_describe` | Load one exact Orca command contract from the current catalog digest without executing it. |
| `orca_call` | Validate and plan one admitted read-only Orca CLI call; return a plan and do not execute it. |

### 7.3 Effect and cost wording

Descriptions must use the protocol effect classes verbatim. They must distinguish:

- `READ_ONLY`: no intended state mutation;
- `LOCAL_APPEND_ONLY`: durable local admission/trace data may be appended;
- `LOCAL_REVERSIBLE`: local runtime resources may be created or changed and must
  have cancellation/cleanup;
- destructive or external effects: never implied by availability;
- `UNKNOWN`: stop mutation and reconcile or obtain evidence.

`swarm_dispatch` must say explicitly that it can start a worker and invoke the
admitted provider/model. It must not claim that model use is free merely because
the current accepted account policy forbids PAYG spend. Authority, account class,
model, budget and timeout remain separate runtime gates.

`swarm_start` must say explicitly that it creates Run/Task state but does not
start a worker. `orca_call` must say explicitly that it does not execute its
returned argv plan.

## 8. Layer C — JSON Schema property descriptions

### 8.1 Rule

Every opaque identity or control field must state:

- semantic type;
- authoritative producer;
- allowed reuse;
- forbidden substitutes;
- null meaning where nullable;
- effect or reconciliation consequence where relevant.

Descriptions are standard JSON Schema annotations. They must not weaken strict
validation, add defaults that manufacture authority, or turn required fields into
optional fields.

### 8.2 Identity provenance table

| Field | Normative provenance |
|---|---|
| `project_id` | Exact UUID returned by `project_admit` and verified by `project_inspect`; never derive it from a path. |
| `run_id` | Logical Run UUID returned by `swarm_start`; do not use a provider Run ID. |
| `task_id` | Logical Task UUID returned by `swarm_start`/`swarm_status`; do not use `task_key` or provider Task ID. |
| `task_key` / `task_keys` | Stable manifest key validated by `swarm_validate` and projected by status; not a UUID. |
| `dispatch_id` | Logical Dispatch UUID returned by successful `swarm_dispatch` or `swarm_retry`; also serves as participant identity where admitted. |
| `operation_id` | Fresh caller-generated UUID for one exact canonical mutation intent; reuse only for byte-equivalent idempotent replay. |
| reconcile `target_id` | Prior `swarm_start.operation.operation_id` when `target_type=operation`; not the reconcile call's new operation ID. |
| cancel `target_id` | Exact Dispatch, Task or Run UUID matching `target_type` and belonging to `run_id`. |
| `contract_id` | Exact accepted Task-contract identity carried by the validated manifest/Run; never invent a new generation during an active Run. |
| `use_case_id` | Optional admitted use-case identity; null means no narrower case identity, not missing authority. |
| `sender_id` / `recipient_id` | Literal `coordinator` or an admitted logical `dispatch_id`; profile names and Task IDs are invalid. |
| `catalog_digest` | Exact digest returned with the current Orca catalog/search result; prevents catalog drift. |
| `schema_bundle_digest` | Exact installed schema-bundle digest when pinned; null only where the current contract explicitly permits it. |
| `provider_*_id` | Provider correlation returned for evidence; never pass it where an Aether logical identity is required. |
| `cursor` | Opaque value returned by the same query surface; never synthesize, decode or transfer it between tools. |

### 8.3 Operation metadata

The common `operation` object must explain:

- `operation_id`: idempotency identity, not resource identity;
- `project_id`: admitted project partition;
- `contract_id`: active immutable contract generation;
- `use_case_id`: optional narrower product case;
- `reason.code`: stable caller classification, not an error code;
- `reason.summary`: secret-safe bounded intent;
- `reason.authority_ref`: reference to the actual authority, not self-granted text;
- `expected_effect`: caller's asserted effect ceiling, validated rather than
  accepted as authority merely because it was supplied.

## 9. Layer D — typed result and error guidance

### 9.1 Additive guidance contract

The candidate adds one top-level `guidance` object to both success and error
envelopes. It is an advisory, machine-readable extension; it does not execute the
next tool or grant authority.

```json
{
  "contract": "aether.guidance/v1alpha1",
  "disposition": "CONTINUE",
  "next_tool": "swarm_status",
  "required_ids": ["project_id", "run_id"],
  "blocking_code": null,
  "safe_to_retry": false,
  "reconcile_before_retry": false,
  "decision_required": false,
  "model_or_cost_effect": "NONE"
}
```

Normative enums:

- `disposition`: `CONTINUE`, `WAIT`, `RECONCILE`, `RETRY`,
  `DECISION_REQUIRED`, `STOP`, `NONE`;
- `next_tool`: one of the same 15 tool names or null;
- `required_ids`: bounded unique array of public input-field names;
- `blocking_code`: stable public error/state code or null;
- `model_or_cost_effect`: `NONE`, `POSSIBLE`, `REQUIRES_AUTHORITY`, `UNKNOWN`.

Invariant combinations:

- `RECONCILE` requires `reconcile_before_retry=true`,
  `next_tool=swarm_reconcile`, and `safe_to_retry=false`;
- `RETRY` requires deterministic terminal evidence and `safe_to_retry=true`;
- `DECISION_REQUIRED` requires `decision_required=true` and `next_tool=null`;
- `STOP` and `NONE` cannot name a mutating next tool;
- `model_or_cost_effect=REQUIRES_AUTHORITY` cannot be paired with automatic
  mutation advice;
- an unknown effect always sets `safe_to_retry=false`.

### 9.2 When a next tool may be named

The server may name `next_tool` only when the transition is mechanically
supported by current state and does not make a product or authority decision.
Examples:

- a successful read-only catalog search may suggest `orca_describe`;
- a successful description may suggest `orca_call` only as a read-only plan;
- an uncertain accepted start operation must name `swarm_reconcile`;
- a successful dispatch may suggest `swarm_status`;
- a successful cancellation may suggest `swarm_status`;
- cleanup-incomplete state may suggest status/cancel only when the exact target
  identity is already known and admitted.

### 9.3 When the server must not recommend a next mutation

`next_tool` must be null when:

- product meaning, scope, acceptance or participant selection is unresolved;
- user authority for a protected effect is missing or ambiguous;
- provider, account, model, spending or credential choice is required;
- the effect is `UNKNOWN` and no supported reconciliation path exists;
- project identity or contract generation conflicts;
- evidence is insufficient to select retry versus cancel;
- a foreign resource or project boundary may be involved;
- the current candidate does not implement the required capability;
- the only apparent route would be a forbidden legacy fallback;
- the MCP cannot prove that the suggested identity belongs to the admitted Run.

In those cases `disposition` is `DECISION_REQUIRED` or `STOP`, and
`blocking_code` explains the mechanical boundary without exposing secrets.

### 9.4 Error-contract audit requirement

The current public protocol declares 50 stable error codes. A static source audit
found 27 additional literal codes emitted by implementation layers that are not
members of that public set and may collapse to `INTERNAL_ERROR` at the operational
runtime boundary:

```text
ERR_CAPABILITY_UNQUALIFIED
ERR_COORDINATOR_BINDING_REQUIRED
ERR_COORDINATOR_BINDING_STALE
ERR_COORDINATOR_BINDING_UNQUALIFIED
ERR_COORDINATOR_PRINCIPAL_MISMATCH
ERR_COORDINATOR_SCOPE_MISMATCH
ERR_INVALID_ARGUMENT
ERR_JOURNAL_RECORD
ERR_JOURNAL_SCOPE
ERR_JOURNAL_TAMPERED
ERR_OPERATION_CONFLICT
ERR_OPERATION_NOT_FOUND
ERR_OPERATION_REQUIRED
ERR_PROVIDER_BUILD_MISMATCH
ERR_PROVIDER_RECEIPT_SCOPE
ERR_PROVIDER_RECEIPT_SHAPE
ERR_RECONCILIATION_SCOPE
ERR_RECONCILIATION_SHAPE
EVIDENCE_REQUIRED
MESSAGE_CORRELATION_INVALID
PROVIDER_EFFECT_FAILED
RETRY_BUDGET_EXHAUSTED
RETRY_FORBIDDEN
RUN_NOT_CLOSED
STALE_ATTEMPT
TRACE_SCHEMA_UNSUPPORTED
WRITE_SCOPE_VIOLATION
```

Not every internal code must become public. Before structured guidance is
implemented, each code must receive one explicit disposition:

1. map to an existing stable public code;
2. admit a new stable public code with reference/tests; or
3. remain intentionally collapsed to `INTERNAL_ERROR`, with no fabricated next
   action and a documented diagnostic path.

The guidance map may depend only on the resulting public code and trusted runtime
state, never on raw exception text.

## 10. Context and disclosure budgets

The candidate must measure, not estimate, these surfaces:

| Surface | Target | Hard ceiling | Visibility |
|---|---:|---:|---|
| Net new SOUL contract | <=300 tokens | 450 tokens | Always visible |
| Tool first sentence | <=180 characters | 180 characters | Catalog listing when budget permits |
| Full tool description | <=900 characters preferred | 1,200 characters | On `tool_describe` |
| One property description | <=160 characters preferred | 240 characters | With loaded schema |
| Guidance object | <=160 serialized tokens typical | 300 tokens | Per result when applicable |

If Tool Search degrades to names-only or bare-server listing because of context
budget, cold-session tests must prove that the SOUL's domain cue can still issue a
successful `tool_search` query. The design does not require all schemas to remain
always visible.

## 11. Compatibility and versioning

### 11.1 Tool surface

The callable names remain exactly:

```text
project_admit
project_inspect
swarm_validate
swarm_start
swarm_status
swarm_dispatch
swarm_message
swarm_reconcile
swarm_retry
swarm_cancel
swarm_close
swarm_trace
orca_search
orca_describe
orca_call
```

No required input is added, removed or made less strict by description work.

### 11.2 Protocol identity

The default design keeps `aether.mcp/v1alpha2` because:

- input validation semantics and callable names remain unchanged;
- JSON Schema descriptions are non-validating annotations;
- `guidance` is additive, independently identified as
  `aether.guidance/v1alpha1`;
- existing consumers should be able to ignore the new field.

This compatibility claim is a gate, not an assumption. Before implementation,
contract tests must prove every known consumer tolerates an additive response
field. If any admitted consumer validates the old envelope as closed, work stops
and records a protocol-version decision; it must not silently change to
`aether.mcp/v1alpha3`.

Adding schema descriptions changes the deterministic schema-bundle bytes and
digest even though validation is unchanged. The implementation must:

- preserve the pre-change v1alpha2 bundle hash and wheel for rollback;
- regenerate the candidate snapshot deterministically;
- report old and new bundle/catalog digests;
- verify source, wheel, installed server, MCP discovery and loaded session agree;
- reject stale pinned digests instead of silently accepting them.

### 11.3 Product and prompt versions

Aether product SemVer and Hermes Prompt SemVer remain separate:

- this work stays inside v0.23.x;
- because v0.23.0 is not yet published, the default product target remains
  v0.23.0 rather than predeclaring v0.23.1;
- `3.0.0-coldstart.1` is an isolated Hermes prompt candidate identifier, not an
  Aether product release;
- only an accepted exact prompt candidate may later become active Hermes Prompt
  3.0.0;
- prompt promotion does not publish or activate an Aether product release.

## 12. Security and trust

Tool descriptions are model-visible instructions and therefore a prompt-injection
surface. The candidate descriptions must be:

- fixed in version-controlled Aether source;
- free of provider-returned or user-submitted text;
- scanned by Hermes' existing MCP description warning path;
- bounded and deterministic;
- reviewed to ensure they do not claim authority or conceal effects;
- secret-free and path-neutral except where a schema explicitly accepts a path.

Tool results and errors must remain secret-safe. Guidance cannot include raw
provider bodies, tracebacks, credentials, private paths from foreign projects, or
untrusted free-form instructions.

## 13. Cold-session acceptance contract

### 13.1 Cold session definition

Each evaluated repetition starts with:

- a fresh Hermes agent/session object and empty conversation;
- active baseline or isolated candidate SOUL loaded before session start;
- no Aether workflow memory;
- no project-specific MCP instructions;
- no Aether skill loaded before or during the case;
- normal Tool Search behavior and the exact current 15-tool catalog;
- frozen model, provider/account class, tool catalog, schema digest and case text;
- isolated local fixture state and no credentials or spending unless a later case
  is separately authorized for model use.

### 13.2 Mandatory case families

1. direct single-owner work: correctly avoid unnecessary swarm use;
2. new project: discover admission without creating a Run or worker;
3. known project: inspect the exact admission before mutation after drift/restart;
4. validate only: validate manifest/DAG/effects without starting;
5. start only: understand that Run/Task creation does not dispatch;
6. protected dispatch: stop when provider/model/budget authority is absent;
7. messaging precondition: never message a profile name or undispatched Task;
8. uncertain start: reconcile the prior start operation ID before retry;
9. retry gate: require exact terminal Dispatch evidence and admitted budget;
10. cancellation and close: status, cancel/fence, close and prove zero survivors;
11. trace: distinguish query from append-only decision/evidence recording;
12. Orca catalog: search, describe and plan without claiming execution;
13. unavailable capability: report the gap without legacy fallback;
14. malformed or stale identity: fail closed without substituting another ID.

### 13.3 Mandatory metrics

- correct direct-versus-MCP route;
- first correct tool or correct Tool Search query;
- complete operation ordering;
- identifier provenance violations;
- avoidable `INVALID_INPUT`/precondition calls;
- Aether skill calls;
- hidden or unauthorized effects;
- model/provider calls and reported cost;
- calls/tokens/time to first useful action;
- total calls, input/output tokens and latency;
- user corrections/manual steering;
- reconcile-before-retry correctness;
- final semantic outcome and zero-survivor cleanup;
- source/wheel/installed/catalog/prompt identity convergence.

### 13.4 Hard thresholds

Every authorized repetition must satisfy:

- 100% hard-invariant accuracy;
- zero invalid legacy fallback;
- zero skill dependency;
- zero invented or cross-class identities;
- zero unauthorized worker/model/provider effects;
- zero unsafe retries of unknown effects;
- zero attempt-owned survivors after any started Run;
- valid structured evaluator output;
- candidate no worse than baseline on direct-task routing and protected-effect
  gating.

Repeated-run count, comparative soft thresholds and model-backed cost ceiling must
be frozen before candidate execution. They cannot be lowered after observing
results.

## 14. Alternatives rejected for this increment

### Skills as the primary teaching mechanism

Rejected because loading is model-selected and therefore cannot guarantee cold
session behavior. Skills may later hold diagnostics, incident procedures or
maintainer detail, but acceptance must pass with zero skill calls.

### Put all 15 schemas in SOUL

Rejected because it permanently increases context, duplicates the authoritative
MCP contract, becomes stale, and weakens progressive disclosure.

### Modify Hermes Agent's global base prompt

Rejected because Aether-specific routing does not belong to every Hermes profile
and would create framework/product coupling.

### Depend on MCP server-level instructions

Rejected for v0.23.x acceptance because the installed Hermes build does not expose
those instructions to the model.

### Replace the 15 tools with one `aether(action=...)` tool

Rejected for this increment because it combines read-only and mutable effects,
creates invalid action/parameter combinations, hides recovery boundaries and has
no comparative evidence.

### Promote the rejected Prompt 3.0.0 candidate

Rejected. Its experiment stopped after three failed rounds. It remains immutable
evidence and cannot be repurposed as the cold-start candidate.

## 15. Frozen decisions and remaining gates

### Frozen by this design

- cold-session teaching cannot depend on skills, memory or history;
- Aether-specific always-visible guidance belongs in an isolated SOUL candidate;
- Hermes Agent core prompt code is not modified;
- the 15 tools remain public and distinct;
- descriptions, schema annotations and typed result guidance each have separate
  responsibilities;
- worker/model/cost effects are explicit;
- unknown effects reconcile before retry;
- the server does not recommend product or authority decisions;
- prompt candidate, MCP metadata candidate and installed activation remain
  separate gates;
- v0.24.0 remains inactive.

### Separately gated

- implementation authorization;
- preregistered baseline/candidate benchmark;
- any model-backed repetition, provider/account/model and budget;
- active SOUL promotion;
- wheel installation and MCP restart/reload;
- integration, release and installed runtime activation.

## 16. Design stop condition

This design is complete when the parent plan, roadmap, status and handoff all
agree that O1 is approved as design, the implementation sequence is reproducible,
and no source, schema, prompt, configuration or runtime mutation has occurred.
