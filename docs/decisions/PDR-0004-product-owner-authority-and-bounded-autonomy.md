# PDR-0004: Product-owner authority and bounded technical autonomy

- **Status:** APPROVED
- **Date:** 2026-07-26
- **Owner:** Christopher (DarkArty07)
- **Supersedes:** None
- **Superseded by:** None

## Context

Aether is intended for software builders who act primarily as product owners. The user may have technical knowledge, but the product must not require a high technical level in order to obtain a high-quality software project.

A multi-agent system can easily expose its internal complexity to the user by asking them to choose architectures, frameworks, models, tools, test strategies, agent assignments, or recovery procedures. Doing so would transfer the coordination and technical burden back to the person Aether is meant to assist.

At the same time, autonomous technical execution must not silently change product vision, scope, visible behavior, accepted risk, cost commitments, or irreversible external state. A durable authority boundary is therefore required.

## Decision

### User role

The user acts primarily as the **product owner**.

The user is responsible for defining or approving:

- the product vision and purpose;
- the problem to solve and the intended users;
- requested features and visible behavior;
- material scope changes;
- priorities and product-level trade-offs;
- acceptance of known quality deviations or limitations;
- major commitments that materially constrain future product direction;
- meaningful cost, schedule, or service commitments;
- credentials, personal or sensitive information, and external accounts;
- publication, deployment, release, or communication to third parties;
- irreversible migrations, deletion, data loss, or other consequential external effects;
- exceptions to approved product decisions.

The user is not expected to decide routine technical mechanics. Aether must not require the user to understand agent topology, framework internals, model routing, file layout, test implementation, recovery mechanics, or low-level architecture merely to move the project forward.

### Aether responsibility

Aether must translate product intent into a clear technical and execution contract. It should make the best supported technical decisions within approved scope and quality constraints.

Aether may decide autonomously:

- task decomposition;
- specialist participation and sequencing;
- parallel versus sequential execution;
- model tier according to cognitive difficulty and consequence;
- tools, MCP integrations, and files required for the task;
- implementation details that do not alter requested behavior;
- proportional test and verification strategy;
- bounded defect correction;
- documentation and continuity maintenance;
- retries, recovery, and internal rerouting within approved limits;
- routine reversible architecture and engineering choices.

When a technical decision has material product consequences, Aether must present those consequences in accessible product language, provide a recommendation, and ask the user to choose the product trade-off. It should not ask the user to select among unexplained technologies.

For example, instead of asking "PostgreSQL or SQLite?", Aether should explain the consequential choice: local simplicity and single-machine operation versus concurrent multi-user scale and service administration, then recommend the option that best fits the approved product.

### Authority layers

The approved conceptual authority model is:

- **User / product owner:** owns vision, product outcomes, material scope, priorities, accepted trade-offs, consequential external effects, and final product acceptance.
- **Hermes:** interprets user intent, establishes and preserves the work contract, decides when product-owner input is required, and synthesizes the result in product language.
- **Harmonia and the coordination kernel:** coordinate bounded tasks, state, dependencies, handoffs, evidence, recovery, and semantic closure without redefining product intent. Olympus and ACPManager retain process and ACP-session lifecycle ownership.
- **Daimons:** exercise specialist judgment inside an assigned task, scope, authority, and evidence contract. They recommend outside those bounds but do not silently expand them.
- **Deterministic policy and tools:** enforce explicit mechanical constraints, permissions, budgets, gates, and irreversible-effect boundaries.

This is an approved target authority model. It does not assert that the current runtime fully implements these boundaries.

### Escalation rule

Aether must stop and request product-owner input when:

- ambiguity could produce materially different visible products;
- an unrequested change appears necessary to continue;
- there are multiple reasonable product directions without a clearly dominant interpretation;
- a specialist proposes changing vision, material scope, or a foundational product commitment;
- specialists disagree on a decision with material product consequences;
- a relevant cost, time, or external-service limit would be exceeded;
- credentials, sensitive information, publication, deployment, spending, or irreversible effects are required;
- prior preferences or memory conflict with the user's current instruction;
- the approved quality criteria cannot be met after bounded attempts;
- completion is possible only by accepting a known material deviation.

Aether should not stop for mechanical, reversible, low-consequence, or purely internal decisions that remain within the approved contract.

### Communication rule

Escalations must be product-owner-friendly:

1. state the product consequence;
2. explain why a decision is required;
3. provide a recommended choice;
4. describe the meaningful alternative and trade-off;
5. avoid unnecessary implementation jargon;
6. ask only for the decision that the user actually owns.

The system must not use technical uncertainty as a reason to make the user perform engineering analysis that Aether can perform itself.

## Rationale

Aether's purpose is to expand the user's capability, not require the user to become a technical project manager for a team of agents. Product-owner-first interaction preserves user authority while allowing substantial technical autonomy.

The user remains responsible for intent and consequential commitments because those cannot be recovered from technical reasoning alone. Aether owns routine technical execution because exposing those choices would recreate the coordination burden the product is intended to remove.

Separating product consequences from implementation mechanisms also lets non-expert users make valid decisions. A user can choose local simplicity, privacy, speed, or scalability without needing to know which database, framework, protocol, or agent topology realizes that outcome.

## Alternatives considered

### Require the user to approve major technical decisions directly

- **Benefits:** Maximum explicit control over implementation.
- **Costs:** Requires technical expertise, slows development, and transfers Aether's responsibility back to the user.
- **Decision:** Rejected. The user approves product consequences, not unexplained technical mechanisms.

### Give Aether full authority after the initial prompt

- **Benefits:** Maximum uninterrupted autonomy.
- **Costs:** Enables silent scope drift, unwanted product decisions, uncontrolled external effects, and acceptance of compromises the user did not authorize.
- **Decision:** Rejected.

### Ask the user whenever uncertainty exists

- **Benefits:** Minimizes autonomous interpretation risk.
- **Costs:** Creates approval fatigue and turns the user into an agent coordinator.
- **Decision:** Rejected. Escalation is reserved for material product uncertainty or consequential effects.

### Let every specialist escalate directly to the user

- **Benefits:** Preserves specialist nuance.
- **Costs:** Fragments the product conversation, exposes internal disagreement, and increases user management burden.
- **Decision:** Rejected as the default. Hermes should synthesize material escalations into one product-owner decision unless direct specialist interaction is explicitly useful.

## Consequences

### Positive

- Aether can serve users without requiring advanced technical knowledge.
- Product authority remains human while technical execution remains autonomous.
- User questions become fewer, higher-value, and easier to understand.
- Daimons can exercise real expertise without acquiring product authority.
- Architecture and model choices can evolve without repeatedly burdening the user.

### Negative

- Hermes must accurately distinguish product consequences from routine technical choices.
- Aether carries greater responsibility for technical judgment and explanation quality.
- Some users with deep technical preferences may need an explicit way to increase their desired control level later.

### Risks

- Aether may incorrectly classify a material architecture commitment as routine.
- Product-language simplification may hide important technical risk if poorly executed.
- Hermes may become a new bottleneck if every specialist disagreement is routed through it mechanically.
- Excessive escalation thresholds may permit drift; overly sensitive thresholds may recreate approval fatigue.

## Validation or review gate

Later operating-model and evaluation work must demonstrate:

1. a non-expert product owner can direct representative software projects without selecting low-level technologies;
2. Aether resolves routine technical decisions autonomously;
3. material scope and product changes are not made silently;
4. escalations describe consequences and recommendations clearly;
5. specialists remain bounded by task authority;
6. the user is not asked to coordinate agents or reconcile raw specialist disagreements;
7. current explicit instructions override stored preferences and prior inferences;
8. consequential external effects remain explicitly authorized.

## Implementation authorization

Approval of this record authorizes documentation alignment and later authority-model design. It does not authorize source-code changes, runtime activation, changes to Hermes, Harmonia, Daimons, permissions, credentials, spending, deployment, publication, or external effects.

## References

- Product vision: `docs/product/VISION.md`
- Product mission: `docs/product/MISSION.md`
- Product objectives: `docs/product/OBJECTIVES.md`
- Product principles: `docs/product/PRINCIPLES.md`
- Authority model: `docs/knowledge/AUTHORITY.md`
- Quality doctrine: `docs/decisions/PDR-0003-quality-doctrine-and-model-economics.md`
