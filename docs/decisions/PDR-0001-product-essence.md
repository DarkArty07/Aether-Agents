# PDR-0001: Product essence as an empirical personal project-production environment

- **Status:** SUPERSEDED
- **Date:** 2026-07-26
- **Owner:** Christopher (DarkArty07)
- **Supersedes:** None
- **Superseded by:** `PDR-0002-generic-adaptive-software-product.md`

## Context

Aether Agents has accumulated substantial architecture, agent roles, tools, memories, skills, and coordination experiments. Describing it primarily as a multi-agent framework or as an extension of `hermes-agent` explains its mechanics but not its product purpose.

The owner created Aether from repeated hands-on use of LLMs while developing projects alone. That experience exposed recurring limitations: generic assistance, loss of project context, drift from the owner's vision, uneven specialist depth, unverifiable completion claims, and coordination overhead. A durable product definition is required so that future agents do not infer purpose from whichever technical subsystem is newest.

## Decision

Aether Agents is the owner's personal environment for producing projects through specialized artificial intelligence. It is also the empirical convergence of the owner's experience working with LLMs: its agents, memories, tools, procedures, and coordination mechanisms exist to preserve useful model strengths while systematically compensating for observed model failures.

Its central purpose is to help one person turn ideas and vision into complete, high-quality projects without personally supplying every required specialty or manually coordinating every step.

Aether must not become:

- a generic coding assistant;
- a showcase whose value is merely having many agents;
- an autonomous bureaucracy that slows development;
- a system that substitutes specialist interpretation for the owner's vision;
- a collection of tools or integrations without demonstrated product value.

Multi-agent architecture is a means. Project quality, preserved intent, and reduced coordination burden are the product outcomes.

## Rationale

This definition starts from the owner's actual use case and observed failures rather than from an abstract multi-agent theory. It remains valid if models, providers, protocols, Daimon names, or implementation details change.

It also supplies a filter for future additions: a new Daimon, memory, MCP server, skill, workflow, or governance mechanism must correct an observed failure, materially improve project outcomes, or reduce the burden required to obtain those outcomes.

## Alternatives considered

### Define Aether as a Claude Code competitor

- **Benefits:** Familiar category and simple comparison.
- **Costs:** Reduces the project to code assistance and hides its project-production, specialization, continuity, and quality ambitions.
- **Decision:** Rejected as the governing identity.

### Define Aether as a multi-agent framework

- **Benefits:** Accurately describes an important mechanism.
- **Costs:** Treats agent count and orchestration as ends rather than as means; encourages architecture-led product drift.
- **Decision:** Rejected as the governing identity.

### Define Aether as a universal autonomous organization

- **Benefits:** Broad and ambitious positioning.
- **Costs:** Prematurely generalizes beyond the owner's validated needs and risks creating bureaucracy, configuration burden, and loss of direction.
- **Decision:** Rejected for the current product definition. Future audience and domain scope remain open discovery questions.

## Consequences

### Positive

- Product purpose becomes independent from the current technical stack.
- Future design can be evaluated against preserved vision, project quality, and coordination cost.
- Empirical learning becomes part of Aether's identity rather than an undocumented development history.
- The role of specialists, memories, MCP integrations, and skills must be justified by concrete value.

### Negative

- Some existing public descriptions centered on multi-agent mechanics will require later reconciliation.
- Attractive technical capabilities may be rejected when they do not improve the owner's project-production experience.

### Risks

- "High quality" and "complete project" still require later product definitions.
- The long-term audience and domain boundary are not decided by this record.
- Empirical experience can become anecdotal unless future claims are tied to observed failures and evidence.

## Validation or review gate

This decision is considered preserved when future product, architecture, roadmap, and public documentation can answer:

1. Which observed user or LLM failure does a capability address?
2. How does it improve the resulting project or reduce coordination burden?
3. How does it preserve the owner's intent rather than replace it?
4. Why is specialization necessary for this case?

Any future redefinition of Aether's essential identity requires a new product decision record that explicitly supersedes this one.

## Implementation authorization

Approval of this record authorizes product documentation alignment only. It does not authorize source-code changes, runtime activation, live agent sessions, configuration changes, deployment, publication, spending, migration, or release activity.

## References

- Product vision: `docs/product/VISION.md`
- Product mission: `docs/product/MISSION.md`
- Product scope: `docs/product/SCOPE.md`
- Product principles: `docs/product/PRINCIPLES.md`
- Product documentation map: `docs/product/README.md`
