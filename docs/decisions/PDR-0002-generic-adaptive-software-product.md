# PDR-0002: Generic adaptive software project-production product

- **Status:** APPROVED
- **Date:** 2026-07-26
- **Owner:** Christopher (DarkArty07)
- **Supersedes:** `PDR-0001-product-essence.md`
- **Superseded by:** None

## Context

The first product-discovery round established Aether's empirical origin and its purpose of turning ideas and vision into high-quality projects through specialized artificial intelligence. It initially described Aether as a personal environment because it was born from the owner's own workflow.

The second round clarified that personal origin is not the intended product boundary. Aether should be usable by other people, begin from a coherent generic foundation, and adapt itself to each user over time. The same round also fixed the domain boundary to software and defined comparative project quality as the proof required for Aether's product thesis.

## Decision

Aether Agents is a **generic, adaptive AI environment for producing software projects**.

It begins with a reusable product foundation, but it learns each user's preferences, standards, recurring decisions, working patterns, and useful procedures. That learning must be persisted in the appropriate durable layer, such as user preferences, memory, or reusable skills. The exact storage and promotion mechanism remains a later design decision.

Aether's supported product domain is software. It may produce applications, services, tools, systems, infrastructure, libraries, experiments, and other software products. Research, design, architecture, documentation, and operations belong when they contribute to producing software. General non-software project production is outside the current product scope.

The Daimon set may grow. New Daimons are justified when a distinct software discipline can materially improve project quality and cannot be covered well enough by the existing specialists without becoming generic or incoherent.

Aether's product thesis must be validated through controlled comparison against strong general-purpose coding agents. Given the same project prompt and equivalent initial conditions, Aether should produce software projects whose quality equals or exceeds the projects produced by systems such as Claude Code, Codex, OpenCode, `hermes-agent`, or the relevant contemporary equivalents.

Aether must not claim superiority from agent count, activity, documentation volume, or internal complexity. It requires executed tests and a comparative quality evaluation across representative projects.

A specific project and the product thesis use different evidence:

- **Project acceptance:** project-appropriate tests and evidence show that the produced software satisfies its requirements.
- **Product validation:** a representative same-prompt benchmark shows that Aether produces projects of equal or higher overall quality than strong general-agent baselines.

The exact benchmark corpus, quality rubric, evaluator design, weighting, cost limits, and latency trade-offs remain open for later discovery and evaluation design.

## Rationale

A generic foundation makes Aether a real product rather than a private configuration, while adaptive learning preserves the value of personalization. Users should not need to manually recreate the owner's accumulated practices, but the product also should not force every user into one permanent workflow.

Restricting the domain to software keeps the system coherent with its current Daimons, tooling, memories, and empirical evidence. It allows specialization to deepen rather than expanding prematurely into unrelated intellectual work.

Comparative evaluation is necessary because Aether introduces substantial orchestration and specialization complexity. That complexity is justified only when the resulting projects are demonstrably as good as or better than those produced by a capable general agent under the same request.

## Alternatives considered

### Keep Aether exclusively personal

- **Benefits:** Maximum optimization for one workflow and fewer product-generalization costs.
- **Costs:** Prevents the system from becoming a reusable product and limits the value of its accumulated empirical design.
- **Decision:** Rejected.

### Make Aether generic without learning the user

- **Benefits:** Simpler product behavior and easier documentation.
- **Costs:** Recreates the limitations of generic assistants and fails to accumulate user-specific value.
- **Decision:** Rejected.

### Support any kind of intellectual project

- **Benefits:** Broader market and ambitious positioning.
- **Costs:** Weakens specialist coherence, creates undefined quality standards, and exceeds the domain supported by current evidence.
- **Decision:** Rejected for the current product scope.

### Validate success only through internal tests

- **Benefits:** Easier and more deterministic.
- **Costs:** Can prove mechanical correctness without proving that the multi-agent product produces better projects than simpler alternatives.
- **Decision:** Rejected as sufficient product validation.

## Consequences

### Positive

- Aether can be designed as a product for multiple users without losing adaptive personalization.
- User learning becomes an essential product capability rather than an optional convenience.
- Software provides a clear domain boundary for Daimons, tools, documentation, and evaluation.
- New Daimons can be evaluated against concrete software disciplines and quality impact.
- Comparative benchmarking becomes the final test of whether Aether's added complexity is worthwhile.

### Negative

- Personalization requires governance over what is learned, where it is stored, and how incorrect learning is corrected.
- Supporting multiple users introduces configuration, onboarding, privacy, portability, and reset concerns.
- Comparative evaluation will be more expensive and difficult than ordinary unit testing.
- Aether may fail its own thesis even when its internal architecture works correctly.

### Risks

- User preferences and reusable skills may become mixed without clear promotion boundaries.
- Benchmark prompts may favor one system or fail to represent real projects.
- Quality may be reduced to a narrow score unless the rubric covers product coherence, maintainability, correctness, usability, and fidelity to intent.
- Additional Daimons may increase coordination cost faster than they increase project quality.

## Validation or review gate

Later product and evaluation design must define:

1. a representative set of software project prompts;
2. equivalent starting conditions for Aether and general-agent baselines;
3. independent or reproducible quality evaluation;
4. project-appropriate test execution;
5. criteria covering more than code generation alone;
6. acceptable cost and time comparisons;
7. evidence that personalization improves outcomes without corrupting user intent.

Aether's architecture is not product-validated until this comparative evidence exists.

## Implementation authorization

Approval of this record authorizes documentation alignment and later benchmark design. It does not authorize source-code changes, creation of new Daimons, runtime activation, live agent sessions, collection of personal data, configuration changes, deployment, publication, spending, migration, or release activity.

## References

- Product vision: `docs/product/VISION.md`
- Product mission: `docs/product/MISSION.md`
- Product objectives: `docs/product/OBJECTIVES.md`
- Product scope: `docs/product/SCOPE.md`
- Product principles: `docs/product/PRINCIPLES.md`
- Superseded decision: `docs/decisions/PDR-0001-product-essence.md`
