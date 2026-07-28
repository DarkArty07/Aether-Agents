# PDR-0003: Quality doctrine and model economics

- **Status:** APPROVED
- **Date:** 2026-07-26
- **Owner:** Christopher (DarkArty07)
- **Supersedes:** None
- **Superseded by:** None

## Context

Aether's product thesis requires it to produce software projects whose quality equals or exceeds strong general-purpose coding agents. That thesis needs a product-level definition of quality and an economic rule for deciding where expensive models are worth using.

The owner's empirical experience identified several recurring failure modes:

- agents implement additional features, abstractions, or changes that were never requested;
- generated code contains logical, architectural, or syntactic defects;
- LLM-generated frontend work is often generic, visually weak, or insufficiently creative;
- project state and prior decisions are forgotten between sessions;
- tests are skipped when they are materially necessary;
- security review can add disproportionate complexity and delay when applied universally;
- documentation becomes stale unless ownership is explicit;
- using the most expensive model for every operation wastes capacity even though smaller models have become highly capable at routine coding.

A durable quality hierarchy and model-allocation doctrine are required so that future Daimons and orchestration designs optimize the product rather than isolated specialist preferences.

## Decision

### Product promise

Aether should turn a software idea into a project of higher quality than a strong general-purpose coding agent by combining only the specialist intelligence necessary and adapting to the user's standards.

### Quality hierarchy

Aether evaluates software-project quality through the following ordered dimensions:

1. **Fidelity to the request and scope.** Do not implement, redesign, generalize, optimize, or add capabilities the user did not request unless they are strictly necessary to satisfy the approved result. Unrequested work is a quality defect even when technically impressive.
2. **Technical correctness.** Minimize logical, architectural, integration, and syntactic errors. Correctness includes coherent behavior and proportional architecture, not merely code that parses.
3. **Product creativity and experience quality.** The produced software should avoid generic output and show appropriate creative judgment. Frontend and UX work require particular attention because general-purpose LLMs commonly produce weak or repetitive interfaces. Multiple specialists may be used when their combined contribution materially improves the product.
4. **Project order and continuity.** Decisions, context, structure, and progress must remain understandable across agents and sessions. Agents should resume from durable project knowledge rather than repeatedly rediscovering or contradicting prior work.
5. **Proportional verification.** Agents must execute the tests and checks needed for the project's risk and change scope. Testing is required when necessary, but ceremony and test volume are not goals by themselves.
6. **Proportional security.** Security analysis should match actual risk. It must not automatically impose maximal complexity, delay, or universal review. The temporary suspension of Athena is preserved as an empirical warning that a specialist can reduce total product quality when its process cost exceeds its risk reduction.
7. **Current documentation.** Product, architecture, decisions, usage, and operational documentation should remain aligned with the software. Documentation requires explicit ownership, potentially through a dedicated documentation or continuity Daimon, but the exact role design remains a later decision.

The hierarchy is ordered. A creative, secure, tested, or well-documented result still fails if it does work the user did not request or misunderstands the intended product.

### Model economics

Aether should allocate model capability according to cognitive difficulty and consequence rather than use one model tier universally.

- **Frontier or expensive models** should be reserved for orchestration, product interpretation, design, architecture, difficult reasoning, complex debugging, high-impact review, and other intellectually demanding or consequential tasks.
- **Smaller or cheaper models** should handle routine coding, mechanical transformations, bounded implementation, repetitive checks, summarization, and other tasks they can perform reliably.
- Routing must consider the actual task, evidence, and risk. A role name alone does not permanently require an expensive model.
- Cost savings are valid only when quality is preserved. Cheap execution that creates rework, drift, or defects is false economy.
- Expensive models should not be spent on coordination chatter, repeated context reconstruction, or work that a capable smaller model can perform with equivalent evidence.

Recent improvements in smaller models' coding capability are part of the empirical basis for this policy. Specific model names and thresholds remain configuration and evaluation decisions rather than permanent product doctrine.

## Rationale

The first quality criterion must be scope fidelity because LLM systems can produce polished but unwanted work. Preventing semantic drift protects user authority and avoids wasting implementation, review, and correction effort.

Correctness follows because software quality cannot be recovered through documentation or presentation when its logic or architecture is wrong. Creativity is elevated because Aether is meant to produce products, not generic codebases, and because frontend quality is a known weakness where specialist collaboration may provide real differentiation.

Continuity, proportional testing, proportional security, and current documentation make quality durable. They also prevent each project from depending on one uninterrupted conversation or one agent's private context.

Model allocation is treated as product doctrine because Aether's multi-agent structure can otherwise multiply expensive inference. High-capability models create the most value where judgment, synthesis, and uncertainty are highest; capable smaller models can execute many routine software tasks efficiently.

## Alternatives considered

### Use all available specialists and maximum review on every project

- **Benefits:** Broad coverage and apparent thoroughness.
- **Costs:** Slower work, higher cost, specialist-driven complexity, conflicting recommendations, and increased vision drift.
- **Decision:** Rejected.

### Define quality primarily through tests

- **Benefits:** Deterministic and easy to report.
- **Costs:** Tests can validate the wrong product, omit UX and creativity, and fail to detect unrequested scope or architectural excess.
- **Decision:** Rejected as sufficient.

### Use the most capable model for every task

- **Benefits:** Simple configuration and potentially higher local performance.
- **Costs:** High cost, wasted capacity, lower scalability, and no guarantee that routine work improves enough to justify the expense.
- **Decision:** Rejected.

### Use cheap models everywhere

- **Benefits:** Low inference cost and greater parallelism.
- **Costs:** Weak orchestration, design, architecture, and difficult reasoning can create rework and lower total project quality.
- **Decision:** Rejected.

### Make security review universal

- **Benefits:** Consistent security attention.
- **Costs:** Disproportionate complexity and latency for low-risk changes; reproduces the failure observed with Athena.
- **Decision:** Rejected in favor of risk-proportional review.

## Consequences

### Positive

- User-request fidelity becomes the first quality gate.
- Aether can distinguish project quality from code volume or test volume.
- Frontend and creative product quality become explicit differentiation targets.
- Continuity and documentation are treated as durable quality properties.
- Security and testing are required proportionally rather than ceremonially.
- Model spending can concentrate on tasks where advanced reasoning has the highest marginal value.

### Negative

- Quality evaluation becomes multidimensional and harder than counting tests.
- Determining whether work is "unrequested" can require careful contract interpretation.
- Creative quality and architecture proportionality need rubrics and human or independent evaluation.
- Dynamic model routing requires ongoing capability measurement as models improve.

### Risks

- Smaller models may be assigned work beyond their actual capability and create hidden rework.
- Expensive models may overcomplicate architecture or design if their authority is not bounded.
- A dedicated documentation Daimon could itself create bureaucracy or stale duplication.
- "Security proportional to risk" may become an excuse to omit necessary review unless risk classification is explicit.
- Multi-agent frontend work may increase inconsistency unless one approved product direction remains authoritative.

## Validation or review gate

Later evaluation and operating-model work must define evidence for:

1. detecting and penalizing unrequested scope;
2. logical, architectural, integration, and syntax defects;
3. frontend creativity, usability, and visual coherence;
4. continuity across cold sessions and different agents;
5. proportional test selection and execution;
6. risk-based security routing and complexity cost;
7. documentation freshness and contradiction detection;
8. comparative quality, cost, latency, and rework by model tier.

A model-routing policy is validated only when it preserves or improves project quality at lower total cost than uniform frontier-model use.

## Implementation authorization

Approval of this record authorizes documentation alignment and later evaluation design. It does not authorize source changes, model-route changes, provider configuration, new Daimons, Athena reactivation, live sessions, benchmarks that incur external cost, deployment, publication, or release activity.

## References

- Product vision: `docs/product/VISION.md`
- Product mission: `docs/product/MISSION.md`
- Product objectives: `docs/product/OBJECTIVES.md`
- Product scope: `docs/product/SCOPE.md`
- Product principles: `docs/product/PRINCIPLES.md`
- Generic adaptive product decision: `docs/decisions/PDR-0002-generic-adaptive-software-product.md`
