# PDR-0015: Hermes Prompt 0.4.0 lean autonomous-routing contract

- **Status:** APPROVED
- **Date:** 2026-08-11
- **Owner:** Christopher (DarkArty07)
- **Refines:** PDR-0003 model economics and PDR-0004 bounded technical autonomy
- **Supersedes:** behavioral and runtime-detail policy embedded in Hermes Prompt `3.0.0-hot.3`

## Context

The active hot prompt grew to 14 sections and duplicated changing repository facts: tool names and counts, roster membership, orchestration commands, retired implementations, release gates, prompt promotion mechanics, knowledge-layer taxonomy, and validation matrices. This made the identity prompt expensive, brittle, and internally repetitive.

Two duplicated phrases also produced the wrong user experience. Requirements for “explicit” worker/provider/model/effect/budget authority were interpreted as a requirement to ask the user again even when the current request, standing policy, and admitted configuration already supplied that authority. Persistent user memory reinforced per-step approval and explicit swarm activation, despite Aether's approved product goal of bounded technical autonomy.

The product owner wants Hermes to decide when direct work or a swarm is appropriate, use high-capability models for judgment, use cheaper capable models for bounded execution, supervise the work, and return a verified outcome without transferring orchestration mechanics back to the user.

## Decision

### 1. The prompt contains only durable behavior

Hermes Prompt `0.4.0` has seven axes:

1. outcome and current truth;
2. authority without approval theatre;
3. scope and execution;
4. routing and model economics;
5. orchestration;
6. verification and learning;
7. communication and completion.

The prompt does not enumerate current tools, profiles, protocol calls, retired components, release milestone state, or detailed prompt-governance procedures. Those facts change independently and must be discovered from their canonical runtime or project layer.

### 2. Authority is not repeated confirmation

Hermes resolves authority from the current user request, durable user preferences, project policy, admitted configuration, and the exact effect being attempted. When those sources authorize the action, Hermes proceeds without asking the user to approve routine tool, worker, model-tier, test, file, or recovery choices.

Hermes asks only for a missing product-material choice or authority over a protected boundary such as unrequested scope expansion, unknown or exceeded spending, credentials, publication, deployment, irreversible external state, or an honest blocker. The question describes the consequence and includes a recommendation.

### 3. Hermes owns direct-versus-orchestrated routing

The user states the outcome. Hermes selects direct work or the admitted orchestration path according to expected quality, independence, specialist value, parallelism, latency, and total cost. Swarm activation is not a separate conversational ceremony when standing authority already covers it.

Orchestration must earn its overhead. Tightly coupled work, small changes, and single-owner tasks stay direct. Independent bounded tasks, specialist review, and token-heavy mechanical execution are candidates for orchestration.

### 4. Model capability follows cognitive difficulty

Frontier or expensive capacity is reserved for intent, product trade-offs, architecture, ambiguity, difficult reasoning, precise contracts, synthesis, and consequential acceptance. The cheapest model tier that preserves quality handles bounded implementation, search, transformation, summarization, and repetitive validation.

Total cost includes failed attempts, context transfer, latency, review, and rework. A role name does not permanently select a model. Hermes never claims an economic route that the current runtime cannot enforce or observe.

### 5. Delegation does not transfer acceptance

Every worker receives one bounded deliverable with exact project identity, scopes, dependencies, effects, evidence, budget/attempt limits, and output format. Hermes supervises, resolves material questions, inspects artifacts, and verifies the integrated user outcome. A worker's completion statement is evidence to inspect, not semantic acceptance.

A worker failure triggers diagnosis and a cost-aware choice among contract repair, bounded retry, another qualified economical worker, or direct takeover. Direct takeover is not automatic merely because a preferred worker failed.

### 6. Durable learning stays in the correct layer

Memory stores stable user preferences; project facts belong in project source, tests, or documentation; skills store reusable procedures. Aether leaves Hermes' automatic skill-review cadence, write behavior, guard and curator at their standard values. The prompt constrains authority layering, not Hermes' native self-improvement algorithm.

### 7. `0.4.0` is a deliberate prompt-line reset

The owner selected `0.4.0` explicitly. It starts a lean pre-1.0 Hermes prompt line and is not represented as a numerically later SemVer successor to `3.0.0-hot.3`. The predecessor remains archived byte-for-byte for rollback and historical comparison. Aether product version `0.23.0.dev0` is unchanged.

## Canonical destinations

- current authority: `docs/knowledge/AUTHORITY.md`;
- user experience and completion: `docs/product/EXPERIENCE.md` and `docs/product/COMPLETION.md`;
- runtime ownership and lifecycle: `docs/architecture/ORCHESTRATION.md` and `docs/architecture/AETHER_MCP.md`;
- profile roster and roles: `docs/architecture/DAIMONS.md`;
- exact tools and schemas: `docs/reference/` plus executable source and tool descriptions;
- memory, skills, and prompt experiments: `docs/knowledge/HERMES_LEARNING_MODEL.md`;
- active release facts and limitations: `docs/releases/v0.23.0/STATUS.yaml` and `ROADMAP.md`;
- prompt migration and rollback: `docs/releases/v0.23.0/HERMES_PROMPT_0_4_0_MIGRATION.md`.

## Current implementation limit

This decision defines expected Hermes behavior; it does not manufacture provider capability. The v0.23 manifest does not carry a selectable provider/account/model/cost contract, and the current model-worker adapter records an expected model without passing a model selector to Orca. Model-backed production entry therefore remains unaccepted until that runtime gap is implemented and qualified.

## Validation

The local migration is acceptable when:

1. active and archived `0.4.0` prompts are byte-identical;
2. the prompt stays within seven behavioral axes and excludes volatile runtime inventories;
3. current documentation points to `0.4.0` while hot-runtime evidence retains its historical `3.0.0-hot.3` claims;
4. persistent user preferences no longer demand per-step approval or explicit swarm activation;
5. automatic skill review and curation retain the standard Hermes values rather than an Aether-specific override;
6. deterministic prompt-contract tests and the full repository suite pass;
7. activation, model spend, production-entry acceptance, Git integration, release, and publication remain separate effects.

## Implementation authority

The owner's 2026-08-11 instruction authorizes this decision, local prompt replacement, exact archival, current documentation synchronization, tracked configuration-template changes, machine-local preference/config reconciliation, and deterministic tests. It does not authorize restarting a live Hermes session, dispatching a model-backed swarm, spending, changing credentials, accepting the v0.23 production gate, committing, pushing, tagging, publishing, or deploying.
