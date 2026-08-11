# Product Documentation

> **Status:** APPROVED PRODUCT BASELINE — discovery Phases 1 through 8 complete
> **Authority:** Christopher (DarkArty07), product owner
> **Governing decisions:** [`PDR-0002`](../decisions/PDR-0002-generic-adaptive-software-product.md), [`PDR-0003`](../decisions/PDR-0003-quality-doctrine-and-model-economics.md), [`PDR-0004`](../decisions/PDR-0004-product-owner-authority-and-bounded-autonomy.md), [`PDR-0005`](../decisions/PDR-0005-multi-agent-participation-and-coordination.md), [`PDR-0006`](../decisions/PDR-0006-hermes-native-user-memory-without-honcho.md), [`PDR-0007`](../decisions/PDR-0007-studio-experience-progressive-visibility-and-ui.md), [`PDR-0008`](../decisions/PDR-0008-canonical-definition-and-project-completion.md)
> **v0.22.0 runtime decisions:** [`PDR-0012`](../decisions/PDR-0012-hermes-orca-swarm-boundary.md), [`PDR-0013`](../decisions/PDR-0013-swarm-roster-and-personality-model.md)
> **Implementation authorization:** Documentation and design only; no swarm activation or profile mutation

This directory defines what Aether Agents is, why it exists, what it should become, and which boundaries all technical work must preserve.

Aether was born from the owner's empirical experience, but its approved product direction is generic, adaptive to each user, limited to software project production, and governed by an explicit quality hierarchy.

## Canonical definition

Aether Agents is an adaptive AI software production studio built on specialized artificial intelligence and Hermes Agent. It is the empirical convergence of experience with the strengths and recurring failures of LLMs.

Aether allows a person to act primarily as product owner and turn their vision into complete, high-quality software through appropriate specialists, tools, memory, continuity, coordination, and evidence without requiring that person to manage the internal technical complexity.

Its multi-agent architecture is a means rather than the product. Aether's value must be demonstrated by producing, under equivalent requests and conditions, software whose overall quality equals or exceeds strong general-purpose coding agents while imposing less manual coordination on the user.

## Canonical product set

| Document | Governing question | Current discovery state |
|---|---|---|
| [VISION.md](./VISION.md) | What future should Aether Agents create? | Identity, audience, software domain, product promise, and validation thesis approved |
| [MISSION.md](./MISSION.md) | What does the product do, for whom, and why? | Generic adaptive mission and quality commitment approved |
| [OBJECTIVES.md](./OBJECTIVES.md) | Which outcomes define progress and success? | Requirements fidelity, quality hierarchy, adaptation, continuity, verification, documentation, experience, and model economics approved |
| [SCOPE.md](./SCOPE.md) | What belongs inside, later, or outside the product? | Software boundary, Daimon growth rule, and foundational exclusions approved |
| [PRINCIPLES.md](./PRINCIPLES.md) | Which rules constrain product and technical decisions? | Phases 1 through 7 principles, authority, multi-agent doctrine, learning governance, and experience rules approved |
| [EXPERIENCE.md](./EXPERIENCE.md) | How should Aether feel, communicate progress, and expose internal work? | Intelligent-studio experience, progressive visibility, and future UI direction approved |
| [COMPLETION.md](./COMPLETION.md) | When is a software project truly complete? | User-outcome completion contract and Hermes requirements responsibility approved |

## Approved foundation

Aether Agents is:

- a generic, adaptive AI environment for producing software projects;
- the empirical convergence of practical experience working with LLMs;
- a product that learns each user's preferences, standards, recurring decisions, and useful procedures;
- a system intended to turn user ideas and vision into complete, high-quality software projects;
- a way to gain specialist intellectual capacity without manually coordinating every step;
- a product whose added complexity must be justified through same-prompt comparison against strong general-purpose coding agents.

## Approved quality hierarchy

1. Do not do things the user did not request.
2. Minimize logical, architectural, integration, and syntactic errors.
3. Produce a coherent and creative product, especially in frontend and UX work.
4. Preserve project order and continuity across agents and sessions.
5. Execute tests and verification when necessary and proportional to risk.
6. Apply security expertise proportionally rather than adding universal complexity.
7. Keep documentation current and authoritative.

A lower-ranked dimension cannot compensate for violating a higher one.

## Approved model-economics principle

Aether allocates model capability according to cognitive difficulty and consequence:

- expensive or frontier models for orchestration, product interpretation, design, architecture, difficult reasoning, complex debugging, and consequential work;
- capable smaller or cheaper models for routine coding, bounded implementation, mechanical transformations, repetitive checks, and similar work when they satisfy the same evidence gates.

Using a cheap model that creates defects or rework is false economy. Using a frontier model for mechanical work without measurable benefit is waste.

## Approved authority model

The user acts primarily as product owner and is not expected to provide advanced technical decisions.

- The **user** owns vision, visible behavior, material scope, priorities, accepted compromises, consequential external effects, and final acceptance.
- **Hermes** translates product intent into a bounded work contract and synthesizes material escalations in product language.
- **Aether product decisions and Hermes policy** define participation, verification, protected effects, review, and semantic acceptance without granting product authority to an execution substrate.
- **The named local v0.23.0 MCP candidate is active but not yet accepted as the normal multi-agent path.** It exposes 15 tools and M1.2 passes; model-backed M1.3 and the M1.4 production-entry decision remain incomplete. v0.22.0 remains the official default-off, zero-tool source boundary.
- **Daimons** exercise specialist judgment inside explicit task and authority boundaries.
- **Deterministic policy and tools** enforce permissions, budgets, evidence gates, and irreversible-effect boundaries.

Aether decides routine, reversible technical mechanics autonomously. It escalates only when the user owns the product consequence or the approved contract cannot be satisfied honestly. The canonical target matrix is [`docs/knowledge/AUTHORITY.md`](../knowledge/AUTHORITY.md).

## Approved multi-agent doctrine

- A Daimon participates only when its expected specialist value exceeds its coordination, cost, latency, and drift risk.
- The product owner may classify any Daimon as `required`, `allowed`, `disabled`, or `forbidden` globally, per project, per run, or per task.
- Current user policy overrides defaults, historical workflows, learned preferences, peer proposals, and fallback routing.
- Disabling a Daimon does not silently waive quality; Aether must use an honest alternative or escalate the residual consequence.
- Hermes centralizes user intent and product synthesis, but must not remain the mandatory relay for every specialist message or handoff.
- Authorized Daimons may collaborate laterally only after an accepted runtime enforces bounded authority, evidence, budgets, traceability, and participant policy.
- No retired runtime, renamed adapter, or hidden fallback may be used to simulate that capability.
- Disagreements resolve through current intent, approved decisions, contract, evidence, quality doctrine, and domain authority—not majority vote.
- Aether uses a small set of stable specialist archetypes and may create several workers from one archetype for independent Tasks; it does not create a new personality per technology or subtask.
- The target roster retains Hefesto, Daedalus, and Ictinus; keeps Ariadna conditional and disabled; proposes an unimplemented Independent Verifier; and retires Athena and Etalides from future routing.

The historical v0.19 operating model is retained in [`docs/knowledge/MULTI_AGENT_MODEL.md`](../knowledge/MULTI_AGENT_MODEL.md). PDR-0012 and [`docs/architecture/ORCHESTRATION.md`](../architecture/ORCHESTRATION.md) govern the Hermes-led Orca replacement; PDR-0013 and [`docs/architecture/DAIMONS.md`](../architecture/DAIMONS.md) govern the target roster; amended PDR-0014 governs v0.22.0 integration, active v0.23.0 production dogfooding/MCP optimization, and the explicit owner gate before any proposed v0.24.0 workflow migration.

## Approved learning and memory doctrine

- Hermes Agent's native memory, `skill_manage`, `/learn`, session search, and Curator are Aether's canonical learning mechanisms.
- Aether must not build a competing general memory engine, skill format, or skill curator without a verified Hermes limitation.
- Honcho is excluded from the approved target product because it caused operational problems and creates an unnecessary external memory dependency.
- Hermes is the custodian of the global user profile: it detects preferences, separates durable patterns from one-off requests, organizes and corrects memory, and passes only relevant context to Daimons.
- Daimons may report observations but do not independently own or redefine the global user model.
- `USER.md` stores user identity and preferences; `MEMORY.md` stores stable environment facts and conventions; skills store reusable procedures; version-controlled project documents preserve current project authority and continuity. Existing `.aether` stores remain protected historical/local state until a new continuity surface is accepted.
- Current explicit instructions always override stored preferences and learned procedures.
- Shared skills should remain reusable and user-neutral rather than hard-coding one user's preferences.

The verified current implementation and approved target governance are documented in [`docs/knowledge/HERMES_LEARNING_MODEL.md`](../knowledge/HERMES_LEARNING_MODEL.md).

## Approved product experience

- Aether should feel like directing an intelligent software studio, not administering agents.
- The user remains product owner and interacts primarily with Hermes in product language.
- The default view shows outcome, stage, meaningful progress, decisions, blockers, risks, and evidence-backed results.
- Detailed Daimon activity, task graphs, handoffs, models, costs, tests, findings, and ledger events remain available through progressive drill-down.
- Routine peer chatter, tool calls, and retries are hidden by default.
- A dedicated future UI is approved as a product direction, but its platform and implementation remain open.
- The UI is a projection of authoritative product, ledger, runtime, continuity, memory, artifact, and evidence state; it must never become a competing source of truth.
- Aether's long-term ambition is an adaptive AI software production studio for individuals and small teams, with quality approaching a competent multidisciplinary software team.

The canonical experience contract is [`EXPERIENCE.md`](./EXPERIENCE.md).

## Explicit non-goals

Aether is not:

- a static generic coding assistant that never learns its user;
- a producer of unrelated non-software projects;
- a system that equates extra unrequested work with helpfulness;
- a multi-agent showcase;
- an autonomous bureaucracy;
- a system that allows specialists or stale preferences to replace current user vision;
- a system that silently rewrites requirements to match what it produced;
- a system that treats agent, session, test, commit, or workflow terminality as product acceptance;
- a system that applies maximum testing or security ceremony to every task;
- a system that uses the most expensive model for every operation;
- a collection of integrations without demonstrated product value.

## Product discovery record

| Phase | Subject | Status |
|---|---|---|
| 1 | Product essence, enduring problem, and non-vision | APPROVED and persisted; original PDR superseded by Phase 2 refinement |
| 2 | User strategy, supported project domain, and proof of project quality | APPROVED and persisted in `PDR-0002` |
| 3 | Product promise, quality hierarchy, and model economics | APPROVED and persisted in `PDR-0003` |
| 4 | Product-owner authority and bounded technical autonomy | APPROVED and persisted in `PDR-0004` |
| 5 | User-controlled Daimon participation, lateral coordination, and disagreement resolution | APPROVED and persisted in `PDR-0005` |
| 6 | Hermes-native learning, user profile, memory, skills, and Honcho exclusion | APPROVED and persisted in `PDR-0006` |
| 7 | Intelligent software studio experience, progressive visibility, and future UI | APPROVED and persisted in `PDR-0007` |
| 8 | Requirements responsibility, project completion, non-negotiable boundaries, and canonical validation | APPROVED and persisted in `PDR-0008` |

Phase 6 is grounded in the installed Hermes Agent implementation and Aether's tracked template: [`docs/knowledge/HERMES_LEARNING_MODEL.md`](../knowledge/HERMES_LEARNING_MODEL.md). Hermes' native learning loop is canonical, Hermes owns global user-profile and memory management, and the v0.22.0 candidate has retired the tracked Honcho configuration and installation surfaces.

## Important distinctions

### Project completion versus product validation

- **Project completion** means the user obtained and accepts the intended software outcome, supported by project-appropriate evidence and honest disclosure of known deviations.
- **Product validation** requires representative same-prompt comparison showing that Aether produces projects whose overall quality equals or exceeds strong general-agent baselines.

### Security versus bureaucracy

Security remains a quality dimension, but it is proportional to actual risk. Athena has target retirement and forbidden participation status under PDR-0013 because its process cost and added complexity exceeded its risk reduction. Critical work that materially requires unavailable independent security judgment must expose that capability gap rather than route through a hidden equivalent.

### Documentation ownership versus role design

Current documentation is required. Ariadna is a conditional, disabled handoff-curation archetype whose distinct value over Hermes-native continuity must be proven before activation; she is not a standing project manager or documentation owner.

## Product change rules

1. Treat the approved baseline as authority rather than an invitation to reinterpret Aether from current architecture.
2. Present material product changes with a recommendation and consequences, but persist only what the product owner approves.
3. Separate current behavior, approved target direction, proposals, and historical experiments.
4. Do not derive product purpose from architecture alone.
5. Do not authorize implementation through documentation approval.
6. Record exclusions and non-negotiable boundaries as carefully as included capabilities.
7. Mark contradictions and superseded interpretations explicitly.
8. Use a new PDR to supersede any material change to identity, completion, authority, or non-negotiable boundaries, then reconcile every derived document.

## Approved baseline

Product discovery Phases 1 through 8 are complete. The canonical set now answers:

- what Aether Agents is;
- which problem it solves;
- who benefits from it;
- how it learns and adapts to the user;
- why and when specialist agents participate;
- what Hermes, Aether product policy, Orca execution mechanics, and Daimons are meant to accomplish;
- how requirements are discovered and preserved;
- when a software project is complete;
- how quality and comparative product value are evaluated;
- how models are allocated according to cognitive difficulty;
- how product authority and technical autonomy are divided;
- how Aether should feel and what the future UI should reveal;
- which values may be traded and which are non-negotiable;
- which capabilities are current, future, experimental, optional, retired, or excluded.

Open implementation, UI, benchmark, migration, market, and runtime-enforcement questions remain. They refine the approved baseline but do not silently redefine it. A material change to Aether's identity, completion contract, authority model, or non-negotiable boundaries requires a new approved PDR that explicitly supersedes the affected decision.
