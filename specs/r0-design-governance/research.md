# R0 Research: Spec Kit Governance Patterns for Aether

**Purpose**: Provide the evidence, alternatives, and rationale behind the R0 governance specification.
**Upstream repository**: `https://github.com/github/spec-kit.git`
**External checkout**: `/home/darkarty/Desktop/agentes/aether-research/spec-kit`
**Inspected revision**: `bf88c9f9a82fa370c7a7257aa2b3cf10b457b65c`
**Revision state at inspection**: local `main` matched `origin/main` with a clean working tree.
**Boundary**: the checkout is outside Aether and is research evidence only.

## 1. Research Question

How should Aether govern design work so that it absorbs the strongest intellectual patterns from GitHub Spec Kit, supports a future multi-agent workflow, minimizes Christopher's cognitive load, preserves authority and traceability, and remains reversible without installing Spec Kit or prematurely implementing the runtime?

## 2. Evidence Summary

| Evidence | Observed upstream behavior | R0 implication |
| --- | --- | --- |
| `docs/reference/agentic-sdd.md:3-16` | Spec Kit is an agentic, ordered SDD process. Only `specify` is strictly required before `plan`; clarify, checklist, and analyze are quality gates used for meaningful ambiguity. | Keep one clear artifact flow, but do not impose every gate on every stage. |
| `templates/commands/specify.md:117-140, 293-316` | The agent makes informed guesses, documents assumptions, limits clarification to critical decisions, and prioritizes scope/security/UX. | Autonomous defaults are the norm; questions are exceptional. |
| `templates/commands/clarify.md:125-179` | Clarifications are prioritized by impact and uncertainty, asked one at a time, capped at five, and include a recommended answer. | If R0 cannot responsibly decide, use the same bounded interaction contract. |
| `templates/commands/constitution.md:21-38, 75-125` | Constitution work is scope-confined, separates governance from implementation, derives values from user/repository context, and validates declarative/testable principles. | R0 must define governance only and defer implementation effects. |
| `templates/constitution-template.md:4-50` | A constitution contains principles, constraints/workflow, governance, and version metadata rather than a large decision-state registry. | Put stable cross-project rules in a concise constitution model. |
| `templates/commands/plan.md:114-159` | Planning resolves unknowns through research, records `Decision`, `Rationale`, and `Alternatives considered`, then produces design/contracts/validation artifacts. | Use a small research decision record beside the owning spec; avoid standalone decision bureaucracy. |
| `templates/commands/checklist.md:9-37, 139-172` | Checklists are unit tests for requirements writing, not implementation tests; built-in spec quality can be agent-maintained while custom checklists are reviewer-owned. | Use an agent-maintained R0 requirements checklist and do not make Christopher manage it. |
| `templates/commands/analyze.md:52-60, 106-160, 236-251` | Analysis is read-only, constitution conflicts are critical, and defects are fixed at the artifact that owns them. | Separate analysis from mutation and repair the source instead of downstream symptoms. |
| `templates/commands/converge.md:57-88, 133-176` | Spec, plan, and tasks are the source of intent under constitution constraints; code is assessed against them and does not redefine them. | Treat runtime/code as evidence, not product authority. |
| `docs/concepts/spec-persistence.md:1-8, 66-107` | Spec Kit intentionally leaves persistence strategy to the project. Living Spec updates `spec.md` first and treats downstream artifacts as derived. | Living Spec best matches Christopher's preference for current truth with low ceremony. |
| `docs/guides/evolving-specs.md:35-58` | Living-spec changes update the spec first, then plan/tasks, run analysis, and preserve important rationale before regeneration. | Define a bounded impact-and-reconciliation procedure. |
| `docs/concepts/spec-of-specs.md:20-55, 71-125` | Large work is decomposed into a shallow roadmap and independently specified slices. The roadmap uses stable IDs, dependencies, links, and only `planned`, `in-progress`, `done`. | Keep R0-R13 as a spec-of-specs and use the same three statuses. |
| `docs/concepts/complex-features.md:18-87` | The preferred complexity ladder is: scope a run, then delegate focused sub-agents, then decompose only when necessary. | Progressive disclosure and bounded delegation should precede additional process machinery. |
| `workflows/speckit/workflow.yml:43-78` | The built-in workflow automates specify/plan/tasks/implement with review gates at spec and plan boundaries. | Human review belongs at meaningful artifact boundaries, not every microdecision. Christopher's delegation permits one consolidated R0 boundary review. |
| `workflows/ARCHITECTURE.md:48-76` | Workflow state is persisted after steps and can resume. Runtime states serve execution recovery, not design-decision governance. | Do not copy workflow-run states into the design-decision model. |
| `docs/reference/workflows.md:118-157, 271-303` | Project overlays extend/replace workflow steps without editing upstream workflows. | Future Aether adaptation should layer on Spec Kit instead of forking core behavior by default. |
| `docs/reference/workflows.md:489-505, 529-553` | Workflows support gates, control flow, fan-out/fan-in, but shell steps have no capability sandbox and interpolated data can be unsafe. | Workflow availability is not authority or security. Protected effects require Aether enforcement and later security design. |
| `presets/ARCHITECTURE.md:7-73` | Overrides, presets, and extensions form a precedence stack; authored constitutions are preserved and not overwritten casually. | Prefer a project-specific adaptation layer and preserve authored governance. |
| `presets/lean/README.md:1-21` | Spec Kit itself provides a Lean preset for the core pipeline without full-template ceremony. | Minimal artifact contracts are an upstream-supported pattern, not a reduction of SDD discipline. |
| `extensions/git/README.md:1-14, 48-81` | Git behavior is an optional self-contained extension; auto-commit is disabled by default. | Design Git separately and do not bind R0 governance to an assumed branch/commit workflow. |
| `extensions/agent-context/README.md:1-16` | Agent-context management is opt-in and only owns a delimited section; Spec Kit core does not automatically rewrite agent instruction files. | System prompts and `AGENTS.md` are derived operating surfaces, not canonical product truth. |
| `extensions/assess/README.md:1-22, 90-105` | Discovery is a separate pipeline that researches, shapes, decides, and hands a surviving idea to specification; it does not silently merge discovery with delivery. | Preserve phase ownership and explicit handoffs between design and later delivery. |

## 3. Selected Design Decisions

## R0-D01 — Use an autonomous stage with one final Decision Review

- **Need**: Christopher wants Aether to decide routine design matters without repeated preference questions while preserving his final authority.
- **Decision**: The design agent autonomously researches and decides reversible choices, validates the full stage, and presents one material-decision review at the stage boundary.
- **Rationale**: This combines Spec Kit's informed-default behavior with its artifact-boundary review gates while minimizing human interruption.
- **Evidence**: `templates/commands/specify.md`, `templates/commands/clarify.md`, and `workflows/speckit/workflow.yml` at the inspected revision.
- **Alternatives considered**:
  - Ask Christopher every preference: rejected because it transfers agent work to the user.
  - No human review: rejected because Christopher remains final authority.
  - Gate every command: rejected for design stages because Christopher explicitly delegated bounded autonomous decisions.
- **Change impact**: Changing this affects R1 human interaction, R3 workflow mapping, R7 supervision, and R10 authority enforcement.

## R0-D02 — Adopt Living Spec for current design truth

- **Need**: Aether must remain current and reversible without forcing users to navigate obsolete decision files.
- **Decision**: Update the owning `spec.md` first; reconcile plans, contracts, tasks, prompts, and implementation afterward. Preserve rationale in `research.md` and history in Git.
- **Rationale**: Christopher prioritizes current truth. Living Spec minimizes drift and is explicitly supported by Spec Kit.
- **Evidence**: `docs/concepts/spec-persistence.md` and `docs/guides/evolving-specs.md`.
- **Alternatives considered**:
  - Flow-forward immutable specs: stronger audit trail but fragments current truth and duplicates context.
  - Flow-back co-equal artifacts: flexible but permits silent divergence and ambiguous ownership.
- **Change impact**: Changing this affects all later artifact lifecycles, especially R2, R3, R8, R9, and R11.

## R0-D03 — Use Spec of Specs with a shallow roadmap

- **Need**: The full Aether design is too broad for one spec or one agent context.
- **Decision**: Keep R0-R13 as stable roadmap slices and give each stage its own specification. `ROADMAP.md` owns only boundaries, dependencies, three-state status, and links.
- **Rationale**: This keeps each stage independently understandable and follows Spec Kit's documented decomposition pattern.
- **Evidence**: `docs/concepts/spec-of-specs.md` and `docs/concepts/complex-features.md`.
- **Alternatives considered**:
  - One 993-line roadmap as roadmap plus detailed design: rejected because it mixes decomposition with stage design.
  - Fully independent unlinked specs: rejected because cross-stage impact would be hidden.
- **Change impact**: Changing this affects documentation layout and traceability across every stage.

## R0-D04 — Use only three design-stage statuses

- **Need**: Aether needs progress and revision visibility without cognitive overhead.
- **Decision**: Stages use `planned`, `in-progress`, and `done`. A material change returns an affected `done` stage to `in-progress`; the reason is a note, not another status.
- **Rationale**: This is the minimal Spec Kit roadmap model and supports reopening without a decision-state machine.
- **Evidence**: `docs/concepts/spec-of-specs.md:53-73`.
- **Alternatives considered**:
  - Seven decision states from the proposed roadmap: rejected as unnecessary ceremony.
  - No stage status: rejected because dependency-aware progress would be invisible.
- **Change impact**: Only roadmap and stage-review behavior depend on this choice.

## R0-D05 — Do not create standalone decision records by default

- **Need**: Material rationale must survive, but separate ADR/PDR/DEC files for every choice would add maintenance and duplicate current truth.
- **Decision**: Put the normative result in `spec.md`; put need/decision/rationale/evidence/alternatives/change impact in `research.md`. Use stable IDs only when cross-reference is needed.
- **Rationale**: Spec Kit planning already uses Decision/Rationale/Alternatives in `research.md`; this preserves intellectual history without a parallel source tree.
- **Evidence**: `templates/commands/plan.md:114-135`.
- **Alternatives considered**:
  - One decision file per choice: rejected for default use; a later stage may justify an exceptional ADR for cross-cutting architecture.
  - No rationale artifact: rejected because Living Spec regeneration could lose why a choice was made.
- **Change impact**: R2 may refine the executable contract format, but it must not reintroduce ceremony without demonstrated value.

## R0-D06 — Use ownership by artifact type

- **Need**: A linear file hierarchy cannot correctly express that product vision, constitution, stage specs, plans, and runtime each own different questions.
- **Decision**: Define one owner per information class and resolve conflicts by semantic layer: product/constitution → spec → plan/contracts → tasks/implementation.
- **Rationale**: This matches Spec Kit's constitution authority and spec/plan/tasks derivation while preserving Christopher's current instruction as final human authority.
- **Evidence**: `templates/commands/analyze.md` and `templates/commands/converge.md`.
- **Alternatives considered**:
  - A single universal document: rejected because it becomes unbounded and mixes concerns.
  - Treat code as truth: rejected because accidental implementation would redefine product intent.
- **Change impact**: Affects every handoff and later source-of-truth design.

## R0-D07 — Treat Git history as baseline history but defer Git mechanics

- **Need**: R0 requires a durable baseline concept, while Christopher wants Git designed as its own subject.
- **Decision**: Define a design baseline as an exact repository revision containing coherent `done` artifacts. Do not create B0/B1 registries or decide branches, commit cadence, worktrees, or remotes in R0.
- **Rationale**: Git already provides immutable history; Spec Kit separates Git as an optional extension.
- **Evidence**: `extensions/git/README.md` and `docs/reference/core.md`.
- **Alternatives considered**:
  - Custom baseline registry: rejected as duplicate state.
  - No durable baseline concept: rejected because accepted design must be reproducible.
- **Change impact**: R8 must decide how revisions are created and integrated; R9 must decide retention and recovery.

## R0-D08 — Keep external frameworks as pinned evidence, not vendored truth

- **Need**: Aether must use current Spec Kit knowledge without embedding a foreign repository or allowing upstream changes to silently alter Aether.
- **Decision**: Keep research clones outside Aether, record upstream URL and inspected commit, refresh before current claims, and capture accepted adaptations in Aether's own artifacts.
- **Rationale**: This combines currency, reproducibility, and independence.
- **Evidence**: The verified external clone and Spec Kit's own preset/overlay model.
- **Alternatives considered**:
  - Vendor Spec Kit source into Aether: rejected by Christopher and unnecessary for design research.
  - Cite only a mutable `main` URL: rejected because findings would not be reproducible.
- **Change impact**: R3 and R4 will select compatibility/update policies.

## R0-D09 — Keep documentation and system prompts in English

- **Need**: The project needs one canonical technical language and compatibility with upstream artifacts.
- **Decision**: Canonical documentation and system prompts are English; conversation with Christopher may remain Spanish; official upstream terms remain untranslated where translation would reduce precision.
- **Rationale**: Christopher explicitly decided this, and it reduces drift when adapting Spec Kit and Hermes sources.
- **Evidence**: Christopher's current instruction.
- **Alternatives considered**: Bilingual canonical documents were rejected because they duplicate maintenance.
- **Change impact**: Canonical project documentation must remain in English. R0 closure migrated `DESIGN.md` and `ROADMAP.md`; future stage artifacts inherit this rule.

## R0-D10 — Separate design, build, and activation authority

- **Need**: A design decision must not accidentally authorize runtime or external effects.
- **Decision**: Use three scopes: design, build, activation. Each later scope requires its own authority; Git detail remains separate.
- **Rationale**: Spec Kit constitution commands explicitly scope governance work away from implementation, and workflows have no security sandbox.
- **Evidence**: `templates/commands/constitution.md` and `docs/reference/workflows.md:489-553`.
- **Alternatives considered**:
  - One broad project authorization: rejected because it would blur protected-effect boundaries.
  - Many effect-state categories in R0: rejected because R10 will design executable authorization.
- **Change impact**: R1 defines user authority, R8 defines Git effects, and R10 defines enforcement.

## R0-D11 — Use requirements-quality checks without transferring checklist labor to Christopher

- **Need**: Agent-generated specifications need a systematic quality gate, but Christopher should not manage internal checkboxes.
- **Decision**: Maintain one agent-owned requirements checklist for each significant stage spec. Custom reviewer checklists are optional and created only for a demonstrated domain risk.
- **Rationale**: This adopts Spec Kit's “unit tests for English” while preserving low cognitive load.
- **Evidence**: `templates/commands/specify.md` and `templates/commands/checklist.md`.
- **Alternatives considered**:
  - No checklist: rejected because omissions become downstream rework.
  - Require Christopher to mark every item: rejected because it defeats autonomous design.
- **Change impact**: R11 will define independent evidence and evaluation beyond requirements writing.

## R0-D12 — Adapt through project layers before changing upstream core

- **Need**: Aether must turn Spec Kit into a multi-agent workflow without prematurely forking or rewriting it.
- **Decision**: Prefer intellectual reuse first, then project-local templates/presets/workflow overlays/extensions when implementation is authorized. Core changes require a demonstrated incompatibility.
- **Rationale**: Spec Kit provides explicit layering and preserves project-authored constitution content.
- **Evidence**: `presets/ARCHITECTURE.md` and `docs/reference/workflows.md`.
- **Alternatives considered**:
  - Install and modify Spec Kit immediately: rejected because R3 has not designed the mapping.
  - Rebuild SDD from scratch: rejected because it discards mature upstream contracts.
- **Change impact**: R3 decides the exact multi-agent workflow; R4 decides Hermes/Aether extension boundaries.

## R0-D13 — Make design stages prompt-native cognitive constructs

- **Need**: Terms such as stage, workflow, gate, validation, and status could be misread as requiring a coded orchestrator even though Aether is intended to operate agentically through prompts and instructions.
- **Decision**: A design stage is formed and managed cognitively by the active agent from current intent, instructions, and artifacts. The documented workflow is a default reasoning pattern; stage labels and gates are documentary or instructional. No code is required to instantiate, sequence, advance, validate, or close design work. Programmatic checks validate produced artifacts or protected effects, not stage transitions.
- **Rationale**: This matches how Christopher and Hermes conducted R0 and preserves the central advantage of agentic work: the model can interpret context, define a useful scope, adapt its reasoning order, and produce verified artifacts without a deterministic controller.
- **Evidence**: Christopher's explicit clarification during R0; Spec Kit's prompt contracts in `templates/commands/*.md`; and its description of agentic SDD in `docs/reference/agentic-sdd.md`.
- **Alternatives considered**:
  - Require a workflow engine to define and advance stages: rejected because it replaces agent judgment with unnecessary machinery.
  - Require a parser or state database for roadmap labels and gates: rejected because documentary instructions already carry the needed meaning.
  - Treat scripts and tests as stage-transition authorities: rejected because they can only measure the artifacts or effects they inspect.
  - Prohibit all future coordination code: rejected because messaging, persistence, observability, scheduling, tools, or protected-effect enforcement may later need infrastructure; that infrastructure remains subordinate and does not define the design method.
- **Change impact**: R3, R7, R9, R10, and R11 must distinguish the prompt-native methodology from any optional coordination, persistence, enforcement, or evaluation mechanisms they later design.

## 4. Why the Earlier Seven-State Proposal Was Rejected

The proposed roadmap listed `DRAFT`, `IN REVIEW`, `ACCEPTED`, `REOPENED`, `REQUIRES REVIEW`, `SUPERSEDED`, and `DISCARDED`. That model was not derived from Spec Kit's design-stage practices and would require both Christopher and agents to track process metadata rather than improve specifications.

R0 replaces it with:

- three roadmap statuses;
- current truth in the living spec;
- rationale in research;
- history in Git;
- one end-of-stage review;
- a dependency-based return to `in-progress` when a completed stage is materially affected.

If later execution infrastructure uses operational states such as `created`, `running`, `paused`, `failed`, or `completed` for recovery, those are implementation details only. They do not define, instantiate, validate, or control Aether's prompt-native design stages.

## 5. Risks and Mitigations

| Risk | Mitigation | Later owner |
| --- | --- | --- |
| Living specs can lose rationale during regeneration | Preserve material rationale and alternatives in `research.md`; use Git history | R8/R9 |
| Autonomous defaults could drift from Christopher's intent | Load current instructions first; final Decision Review; affected-change procedure | R1 |
| A single final review could hide too much detail | Report every material decision once, include change impact, and retain full research artifact | R1/R11 |
| Spec Kit `main` may change after inspection | Record exact revision and refresh before new current claims | R3 |
| Workflow features may appear safe but lack enforcement | Treat capabilities as mechanisms, not authority; design security in R10 | R10 |
| Workflow terminology may be mistaken for mandatory orchestration code | Define stage, workflow, gate, validation, and status as prompt-native semantic constructs; keep optional infrastructure subordinate | R0/R3 |

## 6. Closure Audit and Resolutions

| Finding verified in the repository | Resolution in the accepted baseline |
| --- | --- |
| The exact tracked-file manifest would reject `ROADMAP.md` and `specs/**` | Preserve an exact canonical base manifest while allowing the scalable `specs/` prefix; CI validates the R0 baseline separately. |
| The detailed roadmap still carried the rejected seven-state model and B0/B1 registries | Replace it with the English shallow roadmap selected by R0 and link to the owning spec. |
| Product decisions were duplicated between design and roadmap | Keep accepted/open product decisions only in `DESIGN.md`; the roadmap now links rather than copying them. |
| FR-012 lacked stage-level dependency metadata | Add `Depends on` and `May affect` to the R0 header and a checklist item with a direct evidence pointer. |
| Fixed foundations lacked explicit review triggers | Add review triggers to each accepted product decision in `DESIGN.md`; Hermes can be reopened only by Christopher after demonstrated non-negotiable incompatibility without bounded adaptation. |
| The model-cost hierarchy was written as if already decided | Reclassify it as an R12 hypothesis subject to controlled role-specific evaluation; supervision may require equal or greater reasoning. |
| The checklist asserted success without evidence pointers | Link every checklist item to its owning section or observed repository artifact. |
| Later protocol, convergence, and recovery claims risked remaining paper-only through R13 | Add EC1: a separately authorized minimal walking-skeleton evidence checkpoint after R2 and R5, before empirical claims close in R6, R7, or R9. |
| The R0 directory had competing `001` and `R0` identifiers | Use the single stable path `specs/r0-design-governance/`. |
| Canonical design documents were Spanish | Migrate `DESIGN.md` and `ROADMAP.md` to English during the authorized R0 closure. |
| `DESIGN.md` had private-style mode and unreliable Mermaid line breaks | Normalize it to mode `0644` and use `<br/>` in Mermaid labels. |
| The target tree contained a misaligned `quickstart.md` entry | Correct the tree and verify Markdown fences and relative links. |

## 7. Intentionally Deferred Research

R0 did not research or decide details owned by later stages:

- exact Spec Kit release/preset to install;
- how Spec Kit commands map to Morfeo, supervisor, and implementers;
- Hermes integration mechanics;
- A2A protocol behavior;
- Git workflow and repository topology;
- security enforcement implementation;
- model routing and budgets.

Researching these now would violate the roadmap's stage boundaries and could bias R0 toward mechanisms before requirements exist.

## 8. Research Conclusion

The strongest R0 adaptation is not to copy Spec Kit's files blindly. It is to preserve its intellectual contract:

- constitution constrains all later artifacts;
- specification owns intent;
- research resolves unknowns and records decisions;
- plans and contracts derive from the spec;
- tasks derive from plan and spec;
- analysis is read-only and repairs defects at the source;
- convergence compares present outputs against stated intent;
- agents use informed defaults and bounded clarification;
- stages and workflows are formed and enacted by agent reasoning under prompts and instructions, without requiring an executable controller;
- tests and validators provide evidence about outputs rather than authorizing cognitive stage transitions;
- human review occurs at meaningful boundaries;
- project-local layers adapt upstream behavior;
- Git and agent-context management remain separable concerns.

R0 turns those principles into a low-ceremony governance model suitable for Aether's future multi-agent workflow.
