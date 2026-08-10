# Product and Architecture Decisions

> **Status:** STRUCTURE CURRENT

Durable decisions belong here when they shape product direction, authority, architecture, compatibility, operations, or long-term maintenance. `.aether` may mirror hot decision state but does not replace version-controlled rationale.

## Decision types

- **PDR** — Product Decision Record: purpose, audience, scope, policy, or product principle.
- **ADR** — Architecture Decision Record: technical structure, boundaries, interfaces, or migration strategy.
- **ODR** — Operational Decision Record: deployment, recovery, compatibility, or service policy.

## File naming

```text
PDR-0001-short-title.md
ADR-0001-short-title.md
ODR-0001-short-title.md
```

Sequences are independent by decision type.

## Product decisions

| Record | Status | Governing decision |
|---|---|---|
| [PDR-0014](./PDR-0014-versioned-orca-production-adoption.md) | APPROVED | v0.22.0 closes at the accepted Orca integration/M5.4 boundary; v0.23.0 begins repair-first production dogfooding with generic agents; v0.24.0 migrates process-specific workflows incrementally. |
| [PDR-0013](./PDR-0013-swarm-roster-and-personality-model.md) | APPROVED | Aether uses a small stable roster of reusable archetypes, permits multiple workers per archetype, retires Athena and Etalides from the target, keeps Ariadna conditional, and designs an Independent Verifier before implementation. |
| [PDR-0012](./PDR-0012-hermes-orca-swarm-boundary.md) | PARTIALLY SUPERSEDED | Its Hermes–Orca authority boundary, direct/swarm choice, and retirement of the disconnected native coordination core remain; ADR-0001 supersedes its demand-driven-adapter/CLI-first assumption. |
| [PDR-0011](./PDR-0011-orca-substrate-and-olympus-retirement.md) | PARTIALLY SUPERSEDED | Its Olympus source retirement, capability-gap honesty, historical evidence, and non-destructive store policy remain; PDR-0012 supersedes pre-emptive `aether_agents` core retention. |
| [PDR-0009](./PDR-0009-semver-self-improvement-cycle.md) | APPROVED | Evidence, not assumption, shapes SemVer-governed improvement; the proposed MCP trace primarily preserves protected rich learning episodes for evaluation/refinement and future fine-tuning, without automatic training or promotion. |
| [PDR-0008](./PDR-0008-canonical-definition-and-project-completion.md) | APPROVED | Canonical product definition approved; a project is complete when the user obtains the intended outcome, with Hermes accountable for requirements understanding and honest acceptance evidence. |
| [PDR-0007](./PDR-0007-studio-experience-progressive-visibility-and-ui.md) | APPROVED | Aether should feel like an intelligent software studio, use progressive visibility, and eventually provide a UI that projects authoritative state without duplicating it. |
| [PDR-0006](./PDR-0006-hermes-native-user-memory-without-honcho.md) | APPROVED | Hermes Agent is the canonical learning framework; Honcho is excluded; Hermes owns the global user profile, preferences, and memory. |
| [PDR-0005](./PDR-0005-multi-agent-participation-and-coordination.md) | APPROVED | The user controls Daimon availability; specialists collaborate laterally under contract; disagreements resolve through intent, authority, and evidence rather than voting. |
| [PDR-0004](./PDR-0004-product-owner-authority-and-bounded-autonomy.md) | APPROVED | The user acts as product owner without needing advanced technical knowledge; Aether owns routine technical means and escalates material product consequences. |
| [PDR-0003](./PDR-0003-quality-doctrine-and-model-economics.md) | APPROVED | Quality begins with not doing unrequested work, then technical correctness, creative product quality, continuity, proportional verification and security, current documentation, and cost-aware model allocation. |
| [PDR-0002](./PDR-0002-generic-adaptive-software-product.md) | APPROVED | Aether is a generic adaptive software project-production product; its value requires representative same-prompt quality parity or superiority against strong general agents. |
| [PDR-0001](./PDR-0001-product-essence.md) | SUPERSEDED | Preserved the empirical product essence but incorrectly framed the intended product as personal rather than generic and adaptive. |

## Architecture decisions

| Record | Status | Governing decision |
|---|---|---|
| [ADR-0001](./ADR-0001-aether-mcp-control-and-trace-plane.md) | APPROVED | Hermes controls an Orca-backed swarm through one Aether MCP; Aether owns typed validation, a compact semantic index, protected learning episodes/labels/datasets, and measurement while Orca remains the only operational source of truth. |

## Operational decisions

| Record | Status | Governing decision |
|---|---|---|
| [ODR-0001](./ODR-0001-main-integration-and-release-automation.md) | APPROVED | `main` is the integration branch, releases are tag/GitHub Release boundaries, and agents have standing authority to complete gated GitHub lifecycle operations without per-action approval. |

## Required fields

```markdown
# [Type]-NNNN: Title

- Status: PROPOSED | APPROVED | SUPERSEDED | REJECTED
- Date: YYYY-MM-DD
- Owner: decision authority
- Supersedes: optional record
- Superseded by: optional record

## Context
## Decision
## Rationale
## Alternatives considered
## Consequences
## Validation or review gate
## Implementation authorization
## References
```

## Rules

1. A decision is not approved merely because a file exists.
2. Corrections name the record they supersede.
3. Rejected alternatives remain visible with rationale.
4. Product decisions require product-owner authority.
5. Architecture approval does not automatically authorize implementation.
6. Implementation and release evidence link back to governing decisions.
