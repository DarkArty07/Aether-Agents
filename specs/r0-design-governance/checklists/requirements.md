# Specification Quality Checklist: R0 Design Governance

**Status:** complete
**Feature:** [`../spec.md`](../spec.md)
**Research:** [`../research.md`](../research.md)
**Closure authority:** Christopher kept the complete R0 Decision Review on 2026-08-17.
**Ownership:** agent-maintained requirements-quality evidence; these checks assess the specification and repository artifacts, not product implementation.

Each checked claim points to the artifact or section that makes it auditable. A checked box without a valid evidence pointer is a checklist defect.

## Content Quality

- [x] The specification is written in English. → [`spec.md`](../spec.md), entire artifact; FR-003 and §13.
- [x] R0 is design governance, not product implementation or activation. → [`spec.md` §1](../spec.md#1-purpose), §12, and §16.
- [x] Normative requirements use testable `MUST`, `MUST NOT`, or `MAY` language. → [`spec.md` §3](../spec.md#3-functional-requirements).
- [x] Scope and deferred subjects are explicit. → [`spec.md` §1](../spec.md#1-purpose) and §16.
- [x] The artifacts contain no unresolved drafting markers. → Repository Policy's R0 baseline validation plus the closure audit in [`research.md` §6](../research.md#6-closure-audit-and-resolutions).

## Requirement Completeness

- [x] Christopher's authority and current-instruction precedence are defined. → [`spec.md` FR-001–FR-002](../spec.md#3-functional-requirements), §4.I, and §5.
- [x] Autonomous defaults and their escalation boundary are defined. → [`spec.md` FR-005–FR-007](../spec.md#3-functional-requirements), §4.III, and §7.
- [x] The consolidated Decision Review contract is defined. → [`spec.md` §7](../spec.md#7-autonomous-design-workflow).
- [x] Source ownership and conflict resolution are defined. → [`spec.md` FR-004](../spec.md#3-functional-requirements) and §5.
- [x] Canonical and derived artifact roles are defined. → [`spec.md` §5](../spec.md#5-source-ownership-and-precedence) and [`DESIGN.md` §13](../../../DESIGN.md#13-canonical-artifact-relationships).
- [x] Documentation distribution and stable directory IDs are defined. → [`spec.md` §6](../spec.md#6-target-documentation-distribution).
- [x] Living-spec persistence is selected and bounded. → [`spec.md` FR-008](../spec.md#3-functional-requirements), §10, and [`research.md` R0-D02](../research.md#r0-d02--adopt-living-spec-for-current-design-truth).
- [x] Decision rationale and evidence storage are defined. → [`spec.md` FR-009](../spec.md#3-functional-requirements), §9, and [`research.md` §3](../research.md#3-selected-design-decisions).
- [x] The three documentary roadmap labels are defined. → [`spec.md` FR-010–FR-011](../spec.md#3-functional-requirements), §8, and [`ROADMAP.md` §4](../../../ROADMAP.md#4-documentary-status-model).
- [x] Selective change impact and regression are defined. → [`spec.md` FR-012–FR-013](../spec.md#3-functional-requirements) and §10.
- [x] R0 identifies upstream dependencies and downstream stages it may affect. → [`spec.md` header](../spec.md) fields `Depends on` and `May affect`.
- [x] External evidence provenance is defined. → [`spec.md` FR-014–FR-015](../spec.md#3-functional-requirements) and [`research.md` metadata and §2](../research.md#2-evidence-summary).
- [x] Design, build, and activation authority are separate. → [`spec.md` FR-016–FR-018](../spec.md#3-functional-requirements), §4.VI, and §12.
- [x] Agent context is distinguished from product truth. → [`spec.md` FR-019](../spec.md#3-functional-requirements) and §5.
- [x] Progressive disclosure and stage-quality validation are required. → [`spec.md` FR-020–FR-021](../spec.md#3-functional-requirements) and §14.
- [x] Stable identifiers are required only where cross-reference needs them. → [`spec.md` FR-022](../spec.md#3-functional-requirements) and §9.
- [x] Prompt-native agentic execution is explicit. → [`spec.md` FR-023–FR-026](../spec.md#3-functional-requirements), §4.III, and §7.
- [x] Artifact validation is distinguished from cognitive stage progression. → [`spec.md` FR-027](../spec.md#3-functional-requirements), US4, and SC-011.
- [x] Optional runtime infrastructure remains subordinate to the agentic method. → [`spec.md` FR-028](../spec.md#3-functional-requirements) and [`DESIGN.md` §5](../../../DESIGN.md#5-prompt-native-operating-method).
- [x] Versioning and design-baseline meaning are defined without B0/B1 state duplication. → [`spec.md` §11](../spec.md#11-versioning-and-baseline).
- [x] Assumptions and material unknowns are handled. → [`spec.md` §9](../spec.md#9-decision-record-and-knowledge-model) and §16.
- [x] Canonical language and prompt policy are defined. → [`spec.md` FR-003](../spec.md#3-functional-requirements) and §13.
- [x] Session start, stage closure, and Christopher's acceptance are recorded. → [`spec.md` header and §14](../spec.md#14-session-and-stage-closure).
- [x] The initial glossary defines the terms used by R0. → [`spec.md` §15](../spec.md#15-initial-glossary).

## Consistency and Traceability

- [x] R0 does not claim that A2A is selected. → [`spec.md` §16](../spec.md#16-deferred-by-r0) and [`DESIGN.md` §10](../../../DESIGN.md#10-communication-protocol).
- [x] R0 does not require or install Spec Kit. → [`spec.md` §1](../spec.md#1-purpose), §6, and §16.
- [x] Git baseline meaning is defined while future Git mechanics remain in R8. → [`spec.md` §11–§12](../spec.md#11-versioning-and-baseline) and [`ROADMAP.md` R8](../../../ROADMAP.md#5-roadmap).
- [x] Individual decisions have no lifecycle state machine. → [`spec.md` FR-011](../spec.md#3-functional-requirements) and §8.
- [x] Roadmap labels are documentary rather than executable transitions. → [`spec.md` §8](../spec.md#8-minimal-state-model) and [`ROADMAP.md` §2–§4](../../../ROADMAP.md#2-agentic-interpretation).
- [x] Workflow and gate terminology does not require an orchestrator. → [`spec.md` §7 and §15](../spec.md#7-autonomous-design-workflow).
- [x] Tests, scripts, checklists, and validators produce evidence rather than stage authority. → [`spec.md` US4, FR-027, and SC-011](../spec.md#us4--prompt-native-agentic-execution).
- [x] Every material R0 decision records need, decision, rationale, evidence, alternatives, and impact. → [`research.md` §3](../research.md#3-selected-design-decisions), R0-D01 through R0-D13.
- [x] External Spec Kit evidence identifies upstream URL, external checkout, and exact revision. → [`research.md` metadata and §2](../research.md#2-evidence-summary).
- [x] External research is evidence rather than Aether product truth. → [`spec.md` FR-015 and §5](../spec.md#5-source-ownership-and-precedence).
- [x] Later-stage subjects are deferred to their owners. → [`spec.md` §16](../spec.md#16-deferred-by-r0) and [`ROADMAP.md` §5](../../../ROADMAP.md#5-roadmap).
- [x] The roadmap is shallow and does not duplicate accepted/open product decisions. → [`ROADMAP.md` §1 and §3](../../../ROADMAP.md#1-purpose); [`DESIGN.md` §11–§12](../../../DESIGN.md#11-accepted-product-decisions-and-review-triggers).
- [x] The stage path uses only the canonical R0 identifier. → `specs/r0-design-governance/`; enforced by [Repository Policy](../../../.github/workflows/policy.yml).
- [x] Canonical design documents are English. → [`DESIGN.md`](../../../DESIGN.md) and [`ROADMAP.md`](../../../ROADMAP.md).
- [x] Fixed product foundations have explicit review triggers and model routing remains an evaluated hypothesis. → [`DESIGN.md` §7 and §11](../../../DESIGN.md#7-model-and-reasoning-policy).
- [x] Later empirical runtime claims have a separately authorized evidence path. → [`ROADMAP.md` §6](../../../ROADMAP.md#6-ec1--walking-skeleton-evidence-checkpoint).

## Acceptance Quality

- [x] User scenarios cover autonomy, current truth, reversible change, and prompt-native execution. → [`spec.md` §2](../spec.md#2-user-scenarios-and-acceptance).
- [x] Acceptance scenarios are observable and unambiguous. → [`spec.md` §2](../spec.md#2-user-scenarios-and-acceptance).
- [x] Success criteria are measurable without implementing runtime. → [`spec.md` §17](../spec.md#17-success-criteria).
- [x] `Done When` distinguishes design completion from implementation. → [`spec.md` §18](../spec.md#18-done-when) and §12.
- [x] Christopher reviewed the plain-language Decision Review and kept the complete R0 decision set. → [`spec.md` acceptance metadata and §14](../spec.md#14-session-and-stage-closure), 2026-08-17.

## Closure Evidence

- [x] The external closure audit findings are resolved in the owning artifacts. → [`research.md` §6](../research.md#6-closure-audit-and-resolutions).
- [x] Repository CI validates the scalable base manifest, accepted R0 metadata, IDs, links, fences, checklist closure, and document mode. → [`.github/workflows/policy.yml`](../../../.github/workflows/policy.yml).
- [x] R0 closure performs no Aether build or runtime activation. → [`spec.md` §12](../spec.md#12-authority-boundaries) and [`ROADMAP.md` §8](../../../ROADMAP.md#8-current-boundary).
