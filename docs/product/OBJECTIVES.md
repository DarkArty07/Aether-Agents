# Product Objectives

> **Status:** APPROVED PRODUCT BASELINE — discovery complete
> **Owner:** Christopher (DarkArty07)
> **Governing decisions:** `../decisions/PDR-0002-generic-adaptive-software-product.md`, `../decisions/PDR-0003-quality-doctrine-and-model-economics.md`, `../decisions/PDR-0004-product-owner-authority-and-bounded-autonomy.md`, `../decisions/PDR-0005-multi-agent-participation-and-coordination.md`, `../decisions/PDR-0006-hermes-native-user-memory-without-honcho.md`, `../decisions/PDR-0007-studio-experience-progressive-visibility-and-ui.md`, `../decisions/PDR-0008-canonical-definition-and-project-completion.md`
> **v0.22.0 runtime decision:** `../decisions/PDR-0011-orca-substrate-and-olympus-retirement.md`
> **Implementation authorization:** None

## Outcome model

Objectives describe user or product outcomes, not features such as adding a tool, model, protocol, integration, test suite, or Daimon.

## Primary objectives

### Objective 1: Produce higher-quality software projects

- **Outcome:** From the same representative project prompt and equivalent starting conditions, Aether produces software projects whose overall quality equals or exceeds the output of strong general-purpose coding agents.
- **Beneficiary:** Software builders using Aether.
- **Why it matters:** Multi-agent coordination, memories, tools, and specialist roles are justified only when the resulting project is better than a simpler general-agent alternative.
- **Evidence:** Executed project tests plus controlled comparative evaluation against systems such as Claude Code, Codex, OpenCode, `hermes-agent`, or contemporary equivalents.
- **Failure condition:** Aether produces lower-quality projects, or any quality gain is unsupported by representative same-prompt evidence.
- **Horizon:** Governing long-term product objective; benchmark implementation remains pending.

### Objective 2: Preserve the requested vision and scope

- **Outcome:** Aether implements the project the user asked for without adding features, abstractions, redesigns, generalizations, or process that were not requested and are not strictly necessary.
- **Beneficiary:** The user and every downstream contributor.
- **Why it matters:** LLM systems often produce polished but unwanted work. Unrequested work consumes time, creates maintenance burden, and can displace the user's actual vision.
- **Evidence:** Traceable requirements, explicit scope boundaries, diff and artifact review, and evaluation that penalizes unnecessary additions.
- **Failure condition:** Aether changes product direction, expands scope, or introduces complexity without user authority or a necessity tied to acceptance.
- **Horizon:** Immediate and permanent quality gate.

### Objective 3: Minimize technical defects

- **Outcome:** Produced code contains the fewest practical logical, architectural, integration, and syntactic errors.
- **Beneficiary:** Users, maintainers, and operators of the produced software.
- **Why it matters:** A project cannot be high quality when it merely looks complete but fails in behavior, structure, integration, or execution.
- **Evidence:** Project-appropriate tests, static checks, runtime validation, architectural review proportional to risk, and defect discovery during comparative evaluation.
- **Failure condition:** Avoidable defects remain, architecture is disproportionate or internally incoherent, or passing syntax is treated as sufficient correctness.
- **Horizon:** Immediate and permanent quality gate.

### Objective 4: Improve creative product and frontend quality

- **Outcome:** Aether produces software with appropriate originality, visual coherence, usability, and product judgment rather than generic LLM output, with special attention to frontend and UX work.
- **Beneficiary:** End users and product owners.
- **Why it matters:** General-purpose LLMs commonly generate repetitive, weak, or visually generic interfaces. Specialist collaboration is justified where it materially improves the product experience.
- **Evidence:** Visual and interaction review, rendered artifacts, product-specific design criteria, usability checks, and comparative evaluation against general-agent baselines.
- **Failure condition:** The frontend is generic, incoherent, difficult to use, disconnected from the product vision, or judged only from source code without visual evidence.
- **Horizon:** Core differentiation objective.

### Objective 5: Maintain project order and continuity

- **Outcome:** Different agents and later sessions can resume the project with its vision, decisions, structure, current state, and unresolved issues intact.
- **Beneficiary:** Users, agents, and maintainers working across long project lifecycles.
- **Why it matters:** Repeated context loss causes contradictory work, duplicated investigation, and drift from prior decisions.
- **Evidence:** Cold-session resumption tests, durable decision and context records, continuity checks, and contradiction detection across documentation and implementation.
- **Failure condition:** Agents repeatedly rediscover the project, forget approved decisions, contradict prior work, or depend on one uninterrupted conversation.
- **Horizon:** Core product objective.

### Objective 6: Verify proportionally

- **Outcome:** Agents execute the tests and checks necessary for the project's actual risk and change scope without maximizing ceremony or test volume for its own sake.
- **Beneficiary:** Users and maintainers.
- **Why it matters:** Skipping necessary tests creates false completion, while universal heavy validation can make simple work unnecessarily slow.
- **Evidence:** A risk-appropriate verification plan, executed evidence, negative tests when relevant, and explicit reasons when a test class is not needed.
- **Failure condition:** A material claim lacks evidence, or low-risk work is burdened with validation that adds no meaningful confidence.
- **Horizon:** Immediate operating objective; detailed policy remains pending.

### Objective 7: Apply security proportionally to risk

- **Outcome:** Security expertise reduces meaningful risk without automatically adding maximal complexity, delay, or universal review.
- **Beneficiary:** Users and operators of the produced software.
- **Why it matters:** The owner's prior experience with Athena showed that a specialist can lower total project quality when its process and complexity costs exceed the risk reduction it provides.
- **Evidence:** Explicit risk classification, targeted security review, findings tied to realistic threats, and measurement of remediation value versus complexity and delay.
- **Failure condition:** Security is omitted where risk is material, or security review overengineers low-risk work and blocks useful progress without proportional benefit.
- **Horizon:** Core quality objective; detailed routing remains pending.

### Objective 8: Keep documentation current

- **Outcome:** Product, architecture, decision, usage, and operational documentation remains aligned with the actual project and approved direction.
- **Beneficiary:** Users, agents, contributors, and maintainers.
- **Why it matters:** Stale documentation causes agents to infer intent, repeat mistakes, and act from obsolete architecture or product assumptions.
- **Evidence:** Explicit documentation ownership, link and contradiction checks, release reconciliation, and cold-reader tests showing that a new agent can understand the project without guessing.
- **Failure condition:** Documentation is stale, contradictory, incomplete at important boundaries, or maintained only as an afterthought.
- **Horizon:** Core product objective. A dedicated documentation or continuity Daimon is a possible mechanism, not yet an approved role design.

### Objective 9: Adapt to the individual user

- **Outcome:** Aether becomes increasingly aligned with each user's preferences, standards, recurring decisions, and effective working procedures.
- **Beneficiary:** Each individual user.
- **Why it matters:** A generic product that never learns the user repeats a central limitation of general-purpose assistants.
- **Evidence:** Later evaluation must show that persisted user knowledge improves fidelity, reduces repeated correction, or improves project quality without introducing silent drift.
- **Failure condition:** Personalization is forgotten, misapplied, impossible to correct, or causes Aether to override current user intent.
- **Horizon:** Core product direction; governance and implementation remain pending.

### Objective 10: Expand specialist capacity without multiplying management burden

- **Outcome:** Aether can bring additional software disciplines into a project while requiring less manual coordination than the user would need to manage those specialists directly, and while respecting the user's right to require, allow, disable, or forbid individual Daimons.
- **Beneficiary:** Software builders, especially those working alone or in small teams.
- **Why it matters:** Specialist intelligence is valuable only when its quality contribution exceeds its coordination cost and remains under product-owner policy.
- **Evidence:** Workflow evaluation comparing project quality, user interventions, elapsed time, inference cost, correction burden, participant-policy compliance, and indirect invocation attempts.
- **Failure condition:** Additional Daimons make work slower, less coherent, or more demanding without a compensating quality improvement, or a disabled/forbidden Daimon is invoked through direct, peer, fallback, or renamed routing.
- **Horizon:** Approved product direction; runtime enforcement remains pending.

### Objective 11: Spend model capability where it creates the most value

- **Outcome:** Expensive or frontier models are concentrated on orchestration, design, architecture, difficult reasoning, and consequential tasks, while capable smaller models execute routine and bounded work without lowering total project quality.
- **Beneficiary:** Users and operators paying the inference and latency cost.
- **Why it matters:** Smaller models have become highly capable at routine coding, and uniform frontier-model use wastes capacity that could be reserved for difficult intellectual work.
- **Evidence:** Quality, cost, latency, and rework comparisons by task class and model tier.
- **Failure condition:** Cheap routing creates hidden defects and rework, or expensive models are consumed on mechanical work without measurable benefit.
- **Horizon:** Approved product doctrine; implementation and thresholds remain pending.

### Objective 12: Let the user act as product owner, not technical coordinator

- **Outcome:** A user can direct representative software projects through product goals, desired behavior, priorities, and accepted trade-offs without needing advanced technical knowledge or managing internal agents.
- **Beneficiary:** Software builders using Aether, especially individuals and small teams without every technical specialty.
- **Why it matters:** Requiring the user to choose frameworks, route Daimons, reconcile specialist disagreements, or diagnose routine failures transfers Aether's complexity back to the user.
- **Evidence:** Product-owner usability tests, counts and quality of escalations, successful autonomous resolution of routine technical decisions, and evaluation of whether questions are framed through understandable consequences and recommendations.
- **Failure condition:** The user must become a technical project manager, repeatedly approve reversible mechanics, or select unexplained implementation technologies to make progress.
- **Horizon:** Approved product objective; detailed autonomy profiles and enforcement remain pending.

### Objective 13: Remove routine Hermes relay without decentralizing product vision

- **Outcome:** Authorized Daimons can exchange bounded work, artifacts, evidence, review requests, and dependency handoffs directly after contract admission, while Hermes remains responsible for intent, amendments, escalation, and final synthesis.
- **Beneficiary:** Users, specialist agents, and operators paying the context, latency, and inference cost.
- **Why it matters:** Using the strongest model as the message bus for every handoff wastes capacity and constrains specialist autonomy, but unrestricted self-organization would endanger vision and authority.
- **Evidence:** A future accepted runtime must prove a fixed two-agent handoff with zero routine Hermes relay, durable traceability, no duplicate semantic authority, representative fault tests, and no hidden fallback.
- **Failure condition:** Hermes still relays routine results, selects every next agent, or dispatches every retry; the runtime becomes a second product authority; lateral work escapes contract or participant bounds.
- **Horizon:** Approved target direction. v0.19.5 remains historical bounded evidence; PDR-0011 retired its runtime, and v0.22.0 provides no replacement execution path.

### Objective 14: Build a coherent user model through Hermes

- **Outcome:** Hermes detects, organizes, corrects, and applies durable user preferences so Aether becomes more aligned over time without requiring the user to repeat the same corrections.
- **Beneficiary:** Every Aether user and every Daimon receiving delegated context.
- **Why it matters:** Hermes is the primary user-facing agent and the only role positioned to reconcile current intent, repeated preferences, project context, and specialist observations into one coherent user model.
- **Evidence:** Cross-session preference retention, correction and deletion tests, current-instruction precedence, deduplication, relevant-context delegation, and absence of conflicting Daimon-owned profiles.
- **Failure condition:** The user repeatedly restates durable preferences, stale memory overrides a current request, project-specific facts become global preferences, or different agents act from conflicting user profiles.
- **Horizon:** Approved product objective; implementation evaluation remains pending.

### Objective 15: Operate without Honcho or a parallel memory framework

- **Outcome:** Aether uses Hermes-native memory and learning mechanisms without requiring Honcho or another external semantic memory service for installation, personalization, continuity, or normal operation.
- **Beneficiary:** Users and operators installing and maintaining Aether.
- **Why it matters:** Honcho caused operational problems, adds service and data complexity, and duplicates memory responsibilities already present in Hermes.
- **Evidence:** Clean installation and runtime without Honcho, native cross-session preference persistence, no hidden dependency, and retired setup documentation.
- **Failure condition:** Aether cannot start or personalize without Honcho, silently loses required behavior after removal, or introduces another competing general memory engine.
- **Horizon:** Implemented in the v0.22.0 candidate; tracked configuration, setup, documentation, and distribution surfaces no longer require Honcho.

### Objective 16: Make complex coordination understandable without making the user manage it

- **Outcome:** A product owner can understand what Aether is delivering, where work stands, which decisions matter, and why a result is trustworthy without reading routine internal agent activity.
- **Beneficiary:** Product owners and small teams using Aether.
- **Why it matters:** Transparency is necessary for trust, but exposing every message and tool call recreates the coordination burden Aether should remove.
- **Evidence:** Product-owner usability tests, low unnecessary-intervention counts, successful identification of blockers and decisions, and on-demand access to task, agent, evidence, cost, and ledger detail.
- **Failure condition:** The user must inspect raw agent chatter to understand progress, or the default experience hides material risk and unsupported completion claims.
- **Horizon:** Approved product objective; dedicated UI implementation remains future work.

### Objective 17: Become an adaptive AI software production studio

- **Outcome:** Individuals and small teams can direct Aether through product goals and obtain coordinated software-project outcomes approaching the quality of a competent multidisciplinary team.
- **Beneficiary:** Solo builders and small software teams.
- **Why it matters:** This is the long-term expression of Aether's product thesis: broad specialist capacity, continuity, creativity, execution, and evidence should become accessible without staffing every discipline directly.
- **Evidence:** Representative project outcomes across product, UX, architecture, implementation, testing, documentation, and operations; same-prompt baseline comparison; user-coordination burden; and multidisciplinary quality review.
- **Failure condition:** Aether remains only a code assistant, produces fragmented specialist output, or requires the user to coordinate the equivalent of a full team manually.
- **Horizon:** Long-term product ambition, limited to software.

### Objective 18: Deliver the outcome the user actually wanted

- **Outcome:** Hermes discovers and preserves sufficient product requirements so Aether delivers software the user recognizes and accepts as the intended result.
- **Beneficiary:** The product owner and every downstream contributor.
- **Why it matters:** Technical excellence cannot compensate for building the wrong product. Requirements misunderstanding is an Aether failure even when implementation is competent.
- **Evidence:** Traceable product contracts, material ambiguity escalations, explicit requirement amendments, scope-drift detection, acceptance evidence, and user confirmation or previously approved objective acceptance.
- **Failure condition:** Aether silently interprets material ambiguity, rewrites requirements after implementation, declares completion from technical terminality alone, or delivers something the user says is not what they wanted.
- **Horizon:** Immediate and permanent product objective.

## Approved quality hierarchy

Aether evaluates project quality in this order:

1. Fidelity to the user's request and scope, including not doing things that were not requested.
2. Technical correctness across logic, architecture, integration, and syntax.
3. Creative product, frontend, and UX quality.
4. Project order and continuity across agents and sessions.
5. Tests and verification proportional to need and risk.
6. Security proportional to actual risk and complexity cost.
7. Current, coherent documentation.

A lower-ranked dimension cannot compensate for violating a higher-ranked one. A polished, secure, tested project is still poor quality when it solves the wrong problem or adds unwanted scope.

## Project completion versus product validation

A specific software project is complete when the user obtained the intended outcome and accepts it, supported by requirements and evidence proportional to that project. Technical terminality, tests, commits, and documentation are supporting conditions rather than the semantic definition of completion.

Aether as a product is validated only through representative same-prompt comparison against strong general-purpose coding agents. Mechanical correctness of Aether's own runtime does not by itself prove that Aether produces better projects.

## Cost and speed doctrine

Aether does not optimize for the lowest possible inference cost or the fastest possible completion in isolation.

It first preserves requested scope and technical correctness. It then seeks creative, durable project quality while controlling unnecessary model spending, specialist participation, and ceremony.

Model cost should be proportional to cognitive difficulty and consequence. Cheap execution that causes defects, drift, or rework is false economy; expensive execution of routine work is waste.

## Non-objectives

The following must not drive product decisions by themselves:

- maximizing the number of Daimons;
- maximizing tool calls, delegations, tokens, generated files, tests, or documentation volume;
- maximizing benchmark scores that ignore real project quality;
- increasing process formality without demonstrated benefit;
- applying maximum security review to every task;
- using the most expensive model for every operation;
- claiming superiority from internal architecture or unit-test volume alone.

## Objective hierarchy

1. Understand, preserve, and deliver the user's intended outcome and requested scope.
2. Produce technically correct software.
3. Produce a coherent and creative product.
4. Preserve continuity and maintainability.
5. Apply proportional verification, security, and documentation discipline.
6. Minimize coordination, inference cost, latency, and rework without degrading the objectives above.
7. Treat technical enabling outcomes and experiment-specific measures as subordinate.

The exact acceptable cost and latency limits remain later evaluation decisions.
