# R3 Specification: Spec Kit as a Multi-Agent Method

**Roadmap ID**: R3  
**Stage status**: done  
**Decision authority**: Christopher  
**Autonomous design delegate for this stage**: Hermes  
**Future role owner**: Morfeo  
**Depends on**: R0, R1, R2, `DESIGN.md`  
**May affect**: R4, R5, R7, R8, R9, R10, R11  
**Parent roadmap**: `../../ROADMAP.md`  
**Research**: `research.md`  
**Spec Kit evidence revision**: `bf88c9f9a82fa370c7a7257aa2b3cf10b457b65c`

## 1. Purpose

R3 assigns Spec Kit's phases to Aether's roles, and decides where standing quality standards live.

Spec Kit's process is designed for one agent working with a present human. Aether has three roles and an absent owner. R3 does not rewrite the process — it distributes it, and resolves every point where upstream would stop and ask a human.

R3 does not decide Hermes integration mechanics (R4), topology (R5), numeric budgets or concurrency policy (R7), branch mechanics (R8), memory storage (R9), or enforcement (R10). It does not install Spec Kit, write any prompt, or author any constitution — those are build.

## 2. Phase Assignment

The upstream order is `constitution → specify → clarify → plan → tasks → analyze → checklist → implement → converge`. Only `specify` is strictly required before `plan`; the quality phases are added where ambiguity is real.

| Phase | Owner in Aether | Rationale |
|---|---|---|
| `constitution` | Owner decides, Morfeo drafts and maintains | Standing project governance, not per-contract work |
| `specify` | Morfeo | Intent into requirements; this is the extraction |
| `clarify` | Morfeo, with the owner present | Phase 1 of R1, with the upstream question budget removed |
| `plan` | Morfeo | Technical approach plus Aether's execution envelope (R2 §4) |
| `tasks` | Supervision | Requires concrete file paths and knowledge of the real codebase |
| `analyze` | Supervision | Establishes contract executability on receipt |
| `checklist` | Supervision | Independent reviewer; see §4 |
| `implement` | Implementers | Parallel where the breakdown marks it safe |
| `converge` | Supervision | The convergence loop, bounded by the contract's budget |

- **FR-301**: Each Spec Kit phase MUST have exactly one owning role.
- **FR-302**: A role MUST NOT perform a phase owned by another role, per PD-13.
- **FR-303**: The handoff boundary is between `plan` and `tasks`. Morfeo delivers intent and approach; the supervision role makes it executable.
- **FR-304**: Deriving the task breakdown MUST NOT alter intent. It expresses the contract as executable work and nothing more.
- **FR-305**: Quality phases MUST be applied where ambiguity or risk is material, not ceremonially on every unit of work.

## 3. Where Standing Standards Live

Spec Kit's constitution is an artifact **inside the project being built**, not inside Aether. Standing standards therefore have two homes, and conflating them would put owner preferences into every project Aether touches.

| Scope | Home | Enforcement |
|---|---|---|
| True of the owner across all projects | Morfeo's learned preferences | Morfeo's judgement; inspectable and deletable by the owner |
| True of one project | That project's constitution | Scored as CRITICAL on every feature by `analyze` and `converge` |

- **FR-306**: Owner preferences MUST NOT be written into a project's constitution as if they were that project's standards.
- **FR-307**: Morfeo drafts a project's constitution from what he knows of the owner and what the project already does.
- **FR-308**: For an existing project, established conventions MUST take precedence over the owner's general preference and over the agent's own preference.
- **FR-309**: Establishing or confirming the constitution MUST be part of starting work on a project, not an afterthought.
- **FR-310**: A constitution MUST be small and sharp. Principles MUST be declarative and testable, and vague language MUST be replaced by normative statements with a stated reason.
- **FR-311**: A constitution MUST NOT grow so large that findings against it stop being read. Breadth is not the goal; enforceability is.
- **FR-312**: The owner is the only authority that may add, remove, or redefine a constitution principle. Morfeo may propose and draft.
- **FR-313**: Constitution changes MUST use semantic versioning: incompatible removal or redefinition is major, a new or materially expanded principle is minor, clarification is patch.

### Testing standard

- **FR-314**: Whether and how a project is tested is a **per-project** decision recorded in that project's constitution. Aether MUST NOT impose a universal testing rule.
- **FR-315**: Upstream treats test tasks as optional unless requested. In Aether the testing standard MUST be resolved during extraction rather than left to default, since the owner is not present to be asked later.
- **FR-316**: For an existing project, the testing standard MUST be read from what the project already does before anything is proposed.
- **FR-317**: Test-first discipline MUST NOT be imposed universally. A project may adopt it; Aether does not require it.

## 4. Resolving Upstream's Human Assumptions

Every point where a Spec Kit phase expects a present human, with Aether's resolution:

| Upstream assumption | Aether resolution |
|---|---|
| `clarify` asks at most five questions of a user who stays available | Budget removed; extraction continues until no material gap remains (R1-D10) |
| Custom checklists are reviewer-owned and an agent must not self-approve | The supervision role is the reviewer: it wrote neither the spec nor the code |
| `implement` stops and asks the human when checklist items are unchecked | The supervision role answers, within the authority the contract carries |
| `analyze` offers remediation and waits for approval | The supervision role repairs what it owns and escalates contract defects to Morfeo |
| `converge` recommends a next step to the user | The supervision role takes it, bounded by the contract's attempt budget |
| `implement` is scoped by a human across several runs for large features | The task breakdown's story phases provide the scoping; increments are delivered per converged story |

- **FR-318**: Requirements-quality review MUST be performed by a role that authored neither the requirements nor the implementation.
- **FR-319**: Self-approval of one's own requirements or implementation is prohibited. Where upstream relies on a human reviewer, Aether MUST substitute a different role, never the same one.
- **FR-320**: No phase may block waiting for the owner during unattended execution.
- **FR-321**: Where a resolution grants a role an answer a human would have given, that answer MUST be bounded by the contract, not invented.

## 5. Adaptation Policy

- **FR-322**: Aether MUST reuse upstream's intellectual contracts and MUST NOT vendor, fork, or modify upstream core by default.
- **FR-323**: Adaptation MUST be expressed through project-local layers when implementation is eventually authorized.
- **FR-324**: Every deviation MUST be recorded with its rationale in the owning stage's research artifact.
- **FR-325**: An upstream upgrade MUST be reviewed against recorded deviations and MUST NOT silently change an accepted Aether decision.
- **FR-326**: Adaptation MUST NOT weaken Spec-Driven Development. Redistribution and removal of human-presence assumptions are permitted; dropping a normative principle is not.

## 6. Requirements Inherited by Later Stages

| Requirement | Owner |
|---|---|
| Skills-mode installation is the native form on Claude- and Hermes-class agents | R4 |
| Each role needs the phases it owns available, and no more | R4, R5 |
| The supervision role must reach Morfeo for contract defects during execution | R5 |
| Bound the convergence loop by attempts; configure, do not rebuild | R7 |
| Parallelism follows the breakdown's own safety markers, not an independent concurrency policy | R7 |
| Deliver an independently runnable increment per converged story | R7, R8 |
| Constitution conflicts are the highest-severity evidence class | R11 |
| A cheaper implementer model must still satisfy the constitution, which is scored the same regardless of model | R12 |

## 7. Success Criteria

- **SC-301**: Every upstream phase has exactly one owning role, and no role performs another's phase.
- **SC-302**: No phase in unattended execution waits for the owner.
- **SC-303**: No role reviews requirements it wrote or implementation it produced.
- **SC-304**: Owner preferences appear in Morfeo's memory, never as a project's constitutional principle.
- **SC-305**: A project's testing standard is resolved during extraction and recorded in that project's constitution.
- **SC-306**: For an existing project, the conventions actually in use win over any general preference.
- **SC-307**: Every deviation from upstream has a recorded rationale.

## 8. Done When

- [x] Every Spec Kit phase is assigned to exactly one role.
- [x] The handoff boundary is located between `plan` and `tasks`.
- [x] The two homes for standing standards are separated.
- [x] The testing standard is decided as per-project.
- [x] Every upstream human assumption has a stated Aether resolution.
- [x] The adaptation policy is stated.
- [x] Requirements inherited by later stages are recorded.
- [x] Christopher reviewed the Decision Review and kept all R3 decisions.
