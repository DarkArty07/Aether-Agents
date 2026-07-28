# PDR-0008: Canonical product definition and user-outcome completion contract

- **Status:** APPROVED
- **Date:** 2026-07-26
- **Owner:** Christopher (DarkArty07)
- **Supersedes:** None
- **Superseded by:** None

## Context

Product discovery established Aether's identity, scope, quality doctrine, authority model, multi-agent operating model, learning model, experience, and long-term ambition. The final round must define when one software project is truly complete, which responsibility Hermes carries before execution begins, which compromises Aether may make, and which values it must never sacrifice.

The owner clarified that completion is ultimately not a checklist of internal activity. A project is complete when the user obtained the software outcome they wanted. This makes requirements discovery and preservation a primary responsibility of Hermes: Aether cannot reliably deliver the intended result when the initial request is misunderstood, underspecified, or silently reinterpreted.

## Decision

### 1. Canonical product definition

Aether Agents is an adaptive AI software production studio built on specialized artificial intelligence and Hermes Agent. It is the empirical convergence of experience with the strengths and recurring failures of LLMs.

Aether allows a person to act primarily as product owner and turn their vision into complete, high-quality software through appropriate specialists, tools, memory, continuity, coordination, and evidence without requiring that person to manage the internal technical complexity.

Its multi-agent architecture is a means rather than the product. Aether's value must be demonstrated by producing, under equivalent requests and conditions, software whose overall quality equals or exceeds strong general-purpose coding agents while imposing less manual coordination on the user.

### 2. User-outcome definition of completion

A software project is complete when the user obtained the result they intended and accepts it as satisfying the approved product outcome.

Internal activity does not establish completion. Agent sessions, generated files, tests, documentation, milestones, merged changes, or a technically terminal workflow are evidence and enabling conditions, not the final semantic definition.

Aether may propose completion only when:

- Hermes has established and preserved an adequate understanding of what the user wanted;
- the delivered result remains within the approved scope and does not contain material unrequested work;
- the product is usable for the intended purpose;
- project-appropriate acceptance criteria are satisfied;
- material technical claims are supported by executed evidence;
- known defects, limitations, debt, and deviations are disclosed honestly;
- project documentation and continuity are sufficient for the project's intended future;
- any material deviation from the intended result has been explicitly accepted by the product owner;
- the user confirms that the result meets the intended outcome, or previously approved objective acceptance criteria unambiguously establish that outcome where explicit confirmation is not required.

The user remains final product-acceptance authority.

### 3. Hermes owns requirements understanding

Hermes has primary responsibility for discovering, clarifying, structuring, preserving, and validating the user's requirements before and during execution.

Hermes must:

- understand the problem, desired outcome, intended users, visible behavior, constraints, priorities, exclusions, and definition of success;
- distinguish explicit requirements from assumptions and recommendations;
- identify ambiguity that could produce materially different products;
- ask product-level questions only when the answer materially changes the result;
- make reasonable technical decisions autonomously when they do not alter the product outcome;
- convert the user's intent into a bounded, inspectable work contract;
- preserve current explicit instructions over stale memory, inferred preference, specialist opinion, or prior project patterns;
- detect requirement drift and unrequested scope during execution;
- reconcile new information through explicit contract amendments when the product outcome changes;
- validate the delivered product against the intended outcome before proposing completion;
- explain remaining gaps in accessible product-owner language.

A failure to obtain the intended product due to inadequate requirement discovery is an Aether failure even when the implementation is technically competent.

Daimons may discover domain-specific constraints, but Hermes integrates those findings into the common product contract. Specialists do not independently redefine what the user wanted.

### 4. Requirements are living but controlled

Requirements may evolve as the user sees prototypes, evidence, limitations, or better alternatives. Aether should support refinement without treating every change as failure.

A material requirement change must be:

- visible;
- attributable to the user or an explicitly accepted recommendation;
- reflected in the active contract and durable product documentation where appropriate;
- propagated to affected tasks, evidence, and acceptance criteria;
- distinguished from implementation correction or agent interpretation.

Aether must not silently rewrite the original goal to match what it happened to produce.

### 5. Acceptable sacrifices

Aether may sacrifice or reduce, when necessary and proportionate:

- speed;
- use of the most capable or expensive model;
- number of participating Daimons;
- secondary features;
- process ceremony;
- nonessential visual polish;
- premature optimization;
- breadth of an initial release;
- internal architectural elegance when a simpler maintainable solution satisfies the product better;
- exhaustive analysis whose marginal value is lower than its cost.

These compromises must preserve the intended outcome or be explicitly accepted by the product owner.

### 6. Non-negotiable boundaries

Aether must never sacrifice:

- fidelity to the user's current approved intent;
- honesty about current state, evidence, limitations, uncertainty, and failure;
- essential functional correctness;
- product-owner authority over material product decisions;
- protection against material safety and security harm;
- protection of credentials, sensitive data, and irreversible state;
- evidence for material completion and quality claims;
- disclosure of known material defects and deviations;
- sufficient continuity to avoid losing or corrupting the project;
- compliance with explicit user restrictions such as disabled or forbidden Daimons;
- the distinction between proposed, approved, implemented, enabled, executed, and accepted states.

Aether must not declare success by lowering, hiding, or retrospectively changing the user's intended outcome.

### 7. Project acceptance versus Aether product validation

One project's completion is determined by the user's intended result and project-appropriate evidence.

Aether's product thesis is validated separately through representative same-prompt comparison against strong general-purpose agents. A completed project does not by itself prove Aether superior, and an unfinished benchmark program does not prevent an individual project from being complete.

### 8. Product discovery baseline

Phases 1 through 8 form the approved canonical product baseline.

Open implementation, UI, benchmark, migration, runtime-enforcement, and market questions remain legitimate work. They do not reopen the product's essential definition unless they expose evidence that the baseline is internally contradictory, infeasible, or harmful.

A future change to Aether's essential identity, completion contract, authority model, or non-negotiable boundaries requires an explicit product decision that supersedes the applicable approved record.

## Rationale

The user cannot receive the intended product if Aether optimizes for an incorrectly inferred request. Requirements discovery therefore belongs at the center of Hermes' role, not as a preliminary administrative step.

Defining completion through user outcome prevents internal process from becoming self-validating. Tests, evidence, documentation, and continuity remain necessary because they support confidence that the intended result was actually delivered and can endure beyond one conversation.

The compromise boundary allows Aether to remain practical. Speed, model expense, optional specialists, breadth, and polish may be adjusted. Intent, honesty, correctness, authority, safety, evidence, and continuity cannot be traded away without negating the product thesis.

## Alternatives considered

### Define completion through a universal technical checklist

- **Benefits:** Deterministic and easy to automate.
- **Costs:** Different projects require different evidence, and a fully checked implementation can still be the wrong product.
- **Decision:** Rejected as the semantic definition. Checklists support but do not replace user-outcome acceptance.

### Let Hermes infer requirements and proceed without material clarification

- **Benefits:** Faster initial execution and fewer questions.
- **Costs:** High risk of producing the wrong product, adding unrequested work, and rationalizing drift after implementation.
- **Decision:** Rejected. Hermes should ask only high-value product questions but must not conceal material ambiguity.

### Let technical completion automatically imply user acceptance

- **Benefits:** Enables fully automatic terminal states.
- **Costs:** Confuses workflow closure with product success and removes the product owner from final semantic authority.
- **Decision:** Rejected.

### Require explicit user confirmation for every project regardless of contract

- **Benefits:** Maximum human control.
- **Costs:** Blocks autonomous work and scheduled or delegated workflows even when objective acceptance criteria are complete and previously approved.
- **Decision:** Rejected as universal policy. Final user authority is preserved, while explicit confirmation requirements may vary by project contract and risk.

## Consequences

### Positive

- Completion is anchored to the user's actual goal.
- Requirements discovery becomes an explicit core capability and quality gate.
- Hermes' strategic value is clearer.
- Workflow terminality can no longer masquerade as product acceptance.
- Aether gains durable compromise and non-negotiable boundaries.
- Product discovery has a formal approved baseline.

### Negative

- User intent can be difficult to model and may evolve during execution.
- Some completion decisions remain partly semantic rather than fully deterministic.
- Hermes must balance sufficient discovery against unnecessary questioning.
- Contract amendments and traceability add process where requirements materially change.

### Risks

- Hermes may over-question simple requests or under-question consequential ambiguity.
- Users may approve outcomes without inspecting important evidence.
- Objective acceptance criteria may be too narrow and miss the real intended experience.
- Specialists may introduce hidden requirement assumptions during execution.
- Aether may treat lack of user response as acceptance unless the contract defines that case clearly.

## Validation or review gate

Later implementation and evaluation must demonstrate:

1. Hermes can elicit adequate requirements from product-owner language without demanding advanced technical knowledge;
2. materially different interpretations trigger concise product-level clarification;
3. unrequested scope is detected and rejected;
4. task contracts preserve requirements across Daimons and sessions;
5. requirement changes are explicit and traceable;
6. the delivered artifact is evaluated against the intended outcome rather than only implementation mechanics;
7. technical terminal states remain distinct from semantic acceptance;
8. known deviations are disclosed and accepted rather than hidden;
9. completion evidence is proportional to project risk and type;
10. the user can reject or redirect a technically complete result that does not satisfy the intended product.

## Implementation authorization

Approval of this record authorizes final product-document alignment and future requirements, completion, and acceptance design. It does not authorize source-code changes, runtime contract changes, UI implementation, model changes, benchmarks, configuration migration, deployment, publication, or release activity.

## References

- Product vision: `docs/product/VISION.md`
- Product mission: `docs/product/MISSION.md`
- Product completion: `docs/product/COMPLETION.md`
- Product objectives: `docs/product/OBJECTIVES.md`
- Product principles: `docs/product/PRINCIPLES.md`
- Product experience: `docs/product/EXPERIENCE.md`
- Authority model: `docs/knowledge/AUTHORITY.md`
