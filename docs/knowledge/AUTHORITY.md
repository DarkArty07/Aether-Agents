# Authority Model

> **Status:** APPROVED TARGET — v0.22.0 has no multi-agent execution runtime
> **Owner:** Christopher (DarkArty07)
> **Governing decisions:** `../decisions/PDR-0004-product-owner-authority-and-bounded-autonomy.md`, `../decisions/PDR-0005-multi-agent-participation-and-coordination.md`, `../decisions/PDR-0006-hermes-native-user-memory-without-honcho.md`, `../decisions/PDR-0008-canonical-definition-and-project-completion.md`, `../decisions/PDR-0011-orca-substrate-and-olympus-retirement.md`
> **Implementation authorization:** None

## Purpose

This document provides the canonical conceptual model for who decides what in Aether Agents. It is a product and target-system authority contract, not proof that the current runtime enforces every boundary mechanically.

## Core rule

The user owns the **product meaning and consequences**. Aether owns the **technical means** within approved boundaries.

Aether is designed for a user acting primarily as a product owner. Technical expertise may improve collaboration, but it is not a prerequisite for directing a high-quality software project.

## Authority matrix

| Decision or action | Primary authority | Aether responsibility |
|---|---|---|
| Product vision and purpose | User | Elicit, clarify, preserve, and document |
| Intended users and problem | User | Translate into requirements and acceptance criteria |
| Requirements discovery and active product contract | Hermes | Detect material ambiguity, structure intent, preserve exclusions, and maintain visible amendments |
| Visible behavior and features | User | Recommend coherent options and implement the approved direction |
| Material scope changes | User | Detect, explain consequences, recommend, and request approval |
| Product priorities and accepted compromises | User | Present evidence and product-level trade-offs |
| Routine implementation details | Aether | Decide autonomously within scope and quality constraints |
| Reversible architecture choices | Aether | Choose proportionally and document when durable |
| Architecture with material future consequences | User approves consequence; Aether recommends mechanism | Explain the product consequences without requiring low-level expertise |
| Global user profile and preference curation | Hermes | Detect, organize, correct, deduplicate, and apply durable user preferences |
| Specialist observations about the user | Daimon proposes; Hermes decides persistence | Preserve provenance and prevent specialist assumptions from becoming global truth |
| Daimon availability policy | User | Classify roles as required, allowed, disabled, or forbidden in the applicable scope |
| Agent selection, sequence, and parallelism | Aether within user policy | Optimize quality and coordination cost without invoking disabled or forbidden roles |
| Model selection | Aether | Route according to difficulty, consequence, quality, and cost |
| Tool and MCP selection | Aether | Use the minimum sufficient capabilities within permission boundaries |
| Tests and evidence | Aether | Select and execute proportionally; disclose unsupported claims |
| Bounded defect correction | Aether | Correct without changing requested behavior |
| Documentation and continuity | Aether | Keep canonical knowledge aligned and record supersession |
| Credentials and sensitive data | User | Provide or authorize explicitly; Aether minimizes exposure |
| Spending and external services | User | Explain need, expected consequence, and alternatives |
| Deployment, release, and publication | User | Prepare, verify, and execute only when authorized |
| Irreversible migration, deletion, or data loss | User | Fail closed and present recovery or safer alternatives |
| Completion proposal | Hermes | Compare delivered artifacts and evidence against the intended outcome; disclose gaps and uncertainty |
| Final product acceptance | User | Accept, reject, redirect, or accept named deviations based on the intended outcome and evidence |

## Roles

### User / product owner

The user decides what product should exist, who it serves, which outcomes matter, and which material compromises are acceptable.

The user is not expected to:

- select frameworks, databases, protocols, or model providers without product context;
- understand internal agent topology;
- coordinate Daimons;
- choose test implementations;
- diagnose routine technical failures;
- manage retries, recovery, or session state;
- reconcile raw specialist disagreements.

The user may also disable or forbid any Daimon globally, per project, per run, or per task. Aether may recommend consequences and alternatives, but may not override that policy silently.

A technically expert user may express implementation preferences. Those preferences become constraints only when stated or durably approved; expertise is optional, not assumed.

### Hermes

Hermes is the product-intent interpreter and primary user-facing synthesizer.

Hermes should:

- discover the problem, intended users, desired outcome, visible behavior, constraints, exclusions, priorities, and acceptance criteria;
- convert product-owner language into a bounded work contract;
- distinguish requirements from assumptions and recommendations;
- preserve current explicit intent over historical inference;
- detect durable user preferences and recurring corrections;
- organize, deduplicate, correct, and remove stale entries in the global user profile and memory;
- distinguish one-off instructions from durable preferences;
- decide which user context is relevant to pass to each Daimon;
- identify which uncertainty is product-material;
- decide when escalation is required;
- consolidate specialist reasoning into one understandable recommendation;
- detect requirement drift and maintain explicit contract amendments;
- validate delivered artifacts against the intended user outcome before proposing completion;
- present evidence, limitations, deviations, and trade-offs in product language;
- avoid asking the user to perform technical analysis that Aether can perform.

Hermes does not gain authority to redefine product vision merely by owning interpretation or synthesis.

### Coordination substrate

A future accepted coordination substrate may own operational coordination within an approved contract:

- task state;
- dependencies;
- assignment and handoff;
- evidence tracking;
- bounded retries and recovery;
- lifecycle and terminal-state consistency;
- coordination policy enforcement.

It does not own product meaning. Operational authority must not silently become product authority. Any accepted substrate must enforce user/project Daimon availability policy and may not select a disabled or forbidden role.

The v0.22.0 candidate has no active coordination substrate, specialist execution path, or curation facade. The historical Harmonia/Olympus runtime is retired and cannot be used as a fallback.

### Daimons

A Daimon owns specialist judgment inside an explicit task, scope, authority, and evidence boundary.

A Daimon may:

- make local specialist decisions;
- identify risks and alternatives;
- propose scope or product changes;
- reject unsupported completion claims;
- request escalation through the coordination path.

A Daimon may not silently:

- expand product scope;
- override current user intent;
- impose its discipline universally;
- create irreversible external effects;
- treat a specialist preference as product law;
- ask the user to resolve routine specialist mechanics;
- independently redefine or persist the global user profile without Hermes' curation;
- promote a specialist-local assumption into a global user preference;
- invoke, recommend as already authorized, or indirectly route through a Daimon that user/project policy marks disabled or forbidden.

### Deterministic policy and tools

Deterministic controls enforce boundaries that should not depend on model discretion, including:

- permissions;
- budgets and quotas;
- external-effect gates;
- credential boundaries;
- irreversible-operation confirmation;
- lifecycle invariants;
- evidence and terminal-state contracts.

Availability of a tool does not imply authority to use it.

## Escalation contract

Escalate only when the user owns the decision or when the system cannot proceed honestly inside the approved contract.

### Required escalation

- materially different visible product outcomes are possible;
- required work exceeds approved scope;
- a foundational product commitment may change;
- specialist disagreement affects product consequences;
- cost, schedule, or service limits would be exceeded materially;
- credentials, sensitive data, spending, publication, deployment, or irreversible effects are needed;
- current instructions conflict with stored preferences or prior decisions;
- quality gates cannot be met after bounded attempts;
- only a known material deviation permits completion.

### No escalation required

- file inspection and internal discovery;
- routine implementation choices;
- reversible low-consequence architecture;
- tool, model, or specialist routing within policy;
- proportional tests;
- defect correction that preserves requested behavior;
- documentation reconciliation;
- bounded retries and internal recovery.

## Product-owner communication format

A material escalation should contain:

1. **Decision:** the product choice the user actually owns.
2. **Consequence:** what changes for the product or user.
3. **Recommendation:** Aether's best supported choice.
4. **Alternative:** the meaningful competing option.
5. **Evidence or uncertainty:** why the decision cannot be made mechanically.

Avoid raw implementation questions when a product-level explanation is possible.

### Example

Do not ask:

> Should the project use SQLite or PostgreSQL?

Ask:

> Should the first version prioritize simple local operation on one machine, or support multiple simultaneous users through a separately managed service? I recommend local operation because the approved product does not yet require shared concurrency.

## Current versus target

This document defines the approved target authority model.

The current candidate contains Hermes-facing profiles, skills, policies and product decisions but no Aether Python runtime, continuity plugin, or multi-agent execution path. Future runtime mechanics must use Orca's operational ownership, be documented separately in architecture and release evidence, and be accepted under PDR-0012 before activation.

No current-runtime claim should be inferred solely from this target model.

## Open questions

- Whether users can select explicit autonomy profiles.
- How technical preferences are captured without burdening nontechnical users.
- Exact escalation budgets and bounded-attempt limits.
- How direct user–Daimon interaction should work when specialist nuance is useful.
- Which authority boundaries require deterministic enforcement versus prompt policy.
- Which disagreement and participant-policy boundaries require deterministic enforcement versus documented operating policy.
