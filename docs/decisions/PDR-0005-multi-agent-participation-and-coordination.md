# PDR-0005: User-controlled Daimon participation and lateral coordination

- **Status:** APPROVED
- **Date:** 2026-07-26
- **Owner:** Christopher (DarkArty07)
- **Supersedes:** None
- **Superseded by:** None

## Context

Aether's specialist agents exist to improve software-project quality, but specialist participation is not automatically beneficial. The owner's experience with Athena demonstrated that a Daimon can add disproportionate complexity and delay even when its discipline is valuable in principle.

Aether is also migrating away from Hermes acting as both strategic authority and routine message relay. The v0.19.0 design correctly identifies the current problem: Hermes decomposes work, calls each Daimon, receives every result, transports context to the next Daimon, drives correction loops, and synthesizes completion. The target design moves routine coordination into contract-bounded lateral collaboration, a durable ledger, Harmonia, and the kernel while preserving Hermes as user-facing strategic authority.

A product-level doctrine is required to govern when Daimons participate, how the user may disable them, how specialists collaborate without a mandatory Hermes relay, and how disagreements are resolved.

## Decision

### 1. Daimon participation must be justified

A Daimon participates only when its expected specialist contribution has a reasonable probability of improving the project materially beyond the coordination, cost, latency, and drift risk it introduces.

Valid reasons include:

- the task requires distinct specialist knowledge;
- a general-purpose agent has a known weakness in the relevant discipline;
- independent review or adversarial analysis is proportionate to risk;
- the deliverable materially benefits from design, research, architecture, security, documentation, or another bounded specialty;
- the work can be delegated under a clear scope, authority, evidence, and completion contract.

A Daimon must not participate merely because it exists, appears in a workflow diagram, or historically served as a universal phase gate.

### 2. The user controls specialist availability

The product owner may control Daimon participation globally, per project, per run, or per task.

Each Daimon may be classified as:

- **required** — must participate for the named gate or task;
- **allowed** — may be selected when Aether determines that the expected value justifies it;
- **disabled** — must not be selected unless the user explicitly re-enables it;
- **forbidden** — must not be invoked in the applicable scope, including by automatic routing, fallback, or another Daimon's proposal.

Current explicit user policy overrides default routing, historical workflows, learned preferences, and role recommendations.

Athena is the current empirical example: she remains suspended until explicit user reactivation. The same product-level control must generalize to every Daimon rather than being a special case hard-coded only for Athena.

When the user disables a Daimon, Aether must respect the decision. It may explain the product consequence and recommend an alternative, but it may not silently reactivate or substitute the same role under a different name.

Disabling a Daimon does not waive quality automatically. Aether should use proportionate alternatives such as deterministic checks, another authorized specialist with genuinely different scope, direct Hermes review, narrower acceptance, or explicit product-owner risk acceptance. When no honest substitute can satisfy a required criterion, Aether must escalate rather than violate the participation policy.

### 3. Vision remains centralized; routine coordination becomes lateral

Hermes remains responsible for:

- understanding user intent;
- preparing and preserving the approved contract;
- product and architecture synthesis;
- material amendments and escalations;
- communicating meaningful outcomes to the user.

Hermes must not remain the mandatory relay for every specialist message, result, review, correction, or handoff.

Authorized Daimons may collaborate laterally within an approved contract by:

- handing off bounded work directly;
- requesting a relevant specialist consultation;
- sharing artifacts, context, and evidence;
- reporting blockers and findings;
- requesting focused review;
- continuing a pre-approved dependency chain without returning to Hermes between every step.

Lateral collaboration is not unrestricted self-organization. Every interaction remains bounded by:

- the approved user intent and scope;
- the active contract generation;
- the participant policy and Daimon status;
- role authority and prohibited actions;
- task ownership and dependencies;
- evidence and acceptance requirements;
- budgets, attempts, model limits, and side-effect permissions;
- durable traceability.

### 4. Harmonia and the kernel coordinate without becoming product authority

Harmonia is the coordination steward. She may manage contract state, dependency eligibility, task admission, budgets, stalls, evidence, retries, and escalation signals within approved bounds.

The kernel is the deterministic semantic authority for admitted workflow state and must validate and commit coordination decisions.

Harmonia must not:

- amend product intent or contract scope;
- override user Daimon participation policy;
- invoke a disabled or forbidden specialist;
- become the mandatory message relay;
- make direct ACP lifecycle calls when that authority belongs to Olympus;
- approve her own work or resolve domain disputes by preference.

Olympus remains the ACP process and session lifecycle owner.

### 5. Disagreements are resolved by authority and evidence, not voting

When Daimons disagree, use this hierarchy:

1. current explicit user instruction;
2. approved product vision and durable decisions;
3. active scope, contract, and acceptance criteria;
4. reproducible evidence and actual artifacts;
5. approved quality hierarchy and proportionality;
6. specialist judgment within the role that owns the relevant domain;
7. Hermes synthesis when multiple domains or product consequences intersect;
8. product-owner decision only when the disagreement changes the product materially, accepts risk, or cannot be resolved honestly inside the contract.

No Daimon wins through repetition, confidence, seniority, mythology, model size, or majority vote.

Independent domain gates remain separate. Contradictory factual claims require additional reproducible evidence or another authorized assessment. Risk-priority conflicts escalate through Hermes to the product owner when necessary.

## Analysis of v0.19.0 and v0.19.x

### Alignment with the approved doctrine

The v0.19.0 design is conceptually aligned with this product direction:

- it explicitly separates Hermes' strategic authority from routine execution coordination;
- it defines a lateral team with one accountable owner rather than isolated tool calls;
- it allows authorized participants to contact relevant roles directly;
- it gives Harmonia bounded coordination responsibility without product or lifecycle authority;
- it uses a Coordination Ledger for durable semantic intent, tasks, gates, evidence, and closure;
- it preserves Olympus as ACP lifecycle owner;
- it resolves review conflicts through evidence, independent gates, bounded correction, waiver authority, and escalation rather than majority voting;
- it already records that user/project policy can disable Athena and take precedence over default routing.

### What v0.19.0 did not prove

v0.19.0 is a frozen, default-off experimental baseline. Its closeout explicitly states that it did not demonstrate replacement of Hermes' live hub-and-spoke path.

The release produced deterministic coordination components, authority primitives, a shadow observer, and a kernel dispatch candidate, but it did not demonstrate:

- a production composition root making the kernel operational authority;
- a trusted end-to-end kernel-backed ACP run;
- complete evidence and independent-review binding;
- verified closure and cleanup;
- production migration and rollback;
- routine Daimon-to-Daimon handoff without Hermes on the live path.

The live path therefore remained `Hermes -> talk_to -> ACPManager -> Daimon -> Hermes`.

### How the v0.19.x migration was designed to prove it

The incremental migration is correctly staged:

- **v0.19.1:** compose one default-off kernel-backed task through the real server boundary;
- **v0.19.2:** bind trusted evidence;
- **v0.19.3:** prove semantic closure and cleanup;
- **v0.19.4:** execute a fixed two-task handoff where Task B begins from Task A's durable result with zero routine Hermes relay;
- **v0.19.5:** allow Harmonia to select the next eligible task from a bounded contract candidate set while the kernel validates and commits the decision;
- **v0.19.6:** originally planned as a separate fault-pilot patch and verdict.

This sequence is aligned with the product doctrine because it removes Hermes relay incrementally while retaining one authority per fact and preserving failure evidence.

### Recorded implementation outcome

The roadmap later closed at v0.19.5 with a `VIABLE — BOUNDED` verdict. v0.19.4 demonstrated a fixed real two-agent handoff with zero routine Hermes relay. v0.19.5 demonstrated revision-bound deterministic Harmonia selection, kernel validation and commit, trusted semantic successor consumption, durable closure, and fail-closed behavior in the approved bounded topology. The planned v0.19.6 patch was cancelled at closeout because its decision was absorbed by the deterministic fault matrix, live corrections, and final real Gate C evidence.

This outcome does not authorize production activation or establish arbitrary DAG support, open-ended planning, dynamic worker substitution, multi-project load, or global replacement. Canonical evidence is in `docs/releases/v0.19.x-kernel-migration/V0.19.5_GATE_C_EVIDENCE.md` and `docs/releases/v0.19.x-kernel-migration/ROADMAP_CLOSEOUT.md`.

### Required product correction

The technical design already contains participant rosters and contract authority, but the product requirement must be explicit: user/project Daimon policy is authoritative for every selection path.

The contract and runtime should eventually make `required`, `allowed`, `disabled`, and `forbidden` enforceable states. Harmonia, Hermes, Daimons, fallback routing, and the kernel must all respect the same policy.

This record approves that product requirement only. It does not authorize its implementation.

## Rationale

The user should gain specialist capability without losing control over which specialists participate. A system that automatically invokes a costly or disruptive Daimon against explicit user policy contradicts the product-owner model.

Lateral coordination removes avoidable flagship-model relay cost and allows specialists to cooperate more naturally. Contract, role, evidence, and participant boundaries preserve coherence and prevent decentralization of routine communication from becoming decentralization of product vision.

Evidence-based disagreement resolution preserves genuine specialist independence without allowing review loops to become political voting or indefinite blocking.

## Alternatives considered

### Invoke every Daimon in a fixed lifecycle

- **Benefits:** Predictable ceremony and broad nominal coverage.
- **Costs:** High cost, latency, duplicated work, specialist overreach, and poor fit for simple tasks.
- **Decision:** Rejected.

### Let Aether ignore user-disabled specialists when it believes they are necessary

- **Benefits:** Maximum system discretion.
- **Costs:** Violates product-owner authority and recreates the Athena failure mode.
- **Decision:** Rejected. Aether may recommend and escalate, but not override.

### Keep all coordination through Hermes

- **Benefits:** Strong centralized context and simple mental model.
- **Costs:** Expensive model becomes message bus, every handoff requires relay, context grows, and specialist work cannot progress autonomously.
- **Decision:** Rejected as the target operating model.

### Fully self-organizing agents without a contract or central intent authority

- **Benefits:** Maximum autonomy and flexibility.
- **Costs:** Vision drift, unclear authority, uncontrolled task creation, duplicated work, and unreliable completion claims.
- **Decision:** Rejected.

### Resolve specialist disagreements by majority vote

- **Benefits:** Mechanically simple.
- **Costs:** Ignores role authority, evidence quality, product intent, and the possibility that several agents share the same error.
- **Decision:** Rejected.

## Consequences

### Positive

- The user can disable any Daimon, not only Athena.
- Specialist selection becomes a product policy rather than an internal preference.
- Hermes can focus expensive reasoning on intent, synthesis, and escalation.
- Daimons can collaborate without repetitive Hermes relays.
- Harmonia gains useful coordination responsibility without acquiring product authority.
- Disagreements preserve evidence and domain independence.

### Negative

- Contracts and routing need an explicit participant-policy model.
- A disabled specialist may reduce available assurance or product quality in some contexts.
- Direct collaboration requires stronger traceability, state, and authority enforcement than simple hub-and-spoke delegation.
- Debugging distributed coordination is harder than inspecting a single relay conversation.

### Risks

- Aether may disguise a forbidden Daimon through an equivalent role or fallback path.
- Harmonia may become a practical bottleneck even if she is not formally the relay.
- Lateral agents may share too much context or create unauthorized subtasks.
- Hermes may continue routine relay informally even after technical no-relay paths exist.
- User-disabled quality gates may be treated as silently waived rather than replaced or escalated.

## Validation or review gate

Later operating-model and runtime work must demonstrate:

1. user policy can mark any Daimon required, allowed, disabled, or forbidden;
2. every routing and fallback path respects that policy;
3. disabled Daimons are not invoked indirectly;
4. alternative assurance remains explicit and does not create a silent waiver;
5. a fixed two-agent handoff completes with zero routine Hermes relay;
6. bounded Harmonia selection cannot exceed the approved participant set or scope;
7. all lateral communication remains traceable and authority-bound;
8. disagreement resolution follows evidence and role authority rather than voting;
9. a fault does not silently restore hub-and-spoke or create duplicate semantic authority;
10. project quality and coordination cost improve relative to the legacy path.

## Implementation authorization

Approval of this record authorizes documentation alignment and later operating-model and evaluation design. It does not authorize source changes, runtime activation, new Daimons, Athena reactivation, model or provider changes, live ACP sessions, migration, deployment, publication, or release activity.

## References

- Product vision: `docs/product/VISION.md`
- Product principles: `docs/product/PRINCIPLES.md`
- Authority model: `docs/knowledge/AUTHORITY.md`
- Multi-agent model: `docs/knowledge/MULTI_AGENT_MODEL.md`
- v0.19.0 design: `docs/releases/v0.19.0-autonomous-coordination/DESIGN.md`
- v0.19.0 closeout: `docs/releases/v0.19.0-autonomous-coordination/RELEASE_CLOSEOUT.md`
- v0.19.0 Athena routing debt: `docs/releases/v0.19.0-autonomous-coordination/TECHNICAL_DEBT.md`
- v0.19.x migration design: `docs/releases/v0.19.x-kernel-migration/DESIGN.md`
- v0.19.x roadmap: `docs/releases/v0.19.x-kernel-migration/ROADMAP.md`
