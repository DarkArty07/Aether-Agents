# R3 Research: Distributing Spec Kit Across Three Roles

**Purpose**: Evidence and rationale for the phase assignment and for where standing standards live.  
**Upstream repository**: `https://github.com/github/spec-kit.git`  
**External checkout**: `<private-spec-kit-checkout>`
**Inspected revision**: `bf88c9f9a82fa370c7a7257aa2b3cf10b457b65c`  
**Boundary**: the checkout is outside Aether and is research evidence only.

## 1. Research Question

Spec Kit's process assumes one agent and a present human. Aether has three roles and an owner who leaves. Which role owns which phase, where does the handoff fall, and what replaces the human at every point where upstream stops to ask?

## 2. Evidence Inspected in This Stage

| Source | Finding |
|---|---|
| `docs/reference/agentic-sdd.md:5, 11` | The canonical order is `constitution → specify → clarify → plan → checklist → tasks → analyze → implement → converge`. Only `specify` is strictly required before `plan`; clarify, checklist and analyze are quality gates added where ambiguity is meaningful. |
| `docs/reference/agentic-sdd.md:16` | The constitution is run once up front and updated when principles change. It is "the guiding principles that every later phase is evaluated against". |
| `templates/commands/tasks.md:149-179` | Task format is mandatory: `- [ ] [TaskID] [P?] [Story?] Description with file path`. A task without a concrete file path is explicitly invalid. |
| `templates/commands/tasks.md:161` | The `[P]` marker is applied only when a task touches different files and has no dependency on incomplete work. Parallel safety is decided at breakdown time. |
| `templates/commands/tasks.md:145, 181-213` | Tasks are organized primarily by user story: Setup, Foundational, one phase per story in priority order, then Polish. "Each phase should be a complete, independently testable increment." |
| `templates/commands/tasks.md:147` | "Tests are OPTIONAL: Only generate test tasks if explicitly requested in the feature specification or if user requests TDD approach." |
| `templates/commands/tasks.md:136, 141` | The completion report suggests an MVP scope, typically User Story 1. Tasks must be specific enough that an LLM can complete one without additional context. |
| `templates/commands/implement.md:56-88` | Checklist state is a **read-only gate**. When any item is unchecked, `implement` **STOPS and asks the user** whether to proceed, and waits for a response. |
| `templates/commands/implement.md:149-155` | Phase-by-phase execution, sequential tasks in order, `[P]` tasks together, and file-based coordination: tasks touching the same files must run sequentially. |
| `templates/commands/implement.md:163-169` | Halt on failure of a non-parallel task; for `[P]` tasks continue with the successful ones and report the failures. |
| `templates/commands/implement.md:100-108` (via `agentic-sdd.md`) | For large features, upstream expects a **human** to scope `implement` across several runs and validate between them. |
| `templates/commands/analyze.md:54` | "This command MUST run only after `tasks` has successfully produced a complete `tasks.md`." |
| `templates/commands/checklist.md:30-37` | Custom checklists are reviewer-owned. The generating command "MUST NOT mark generated items `[x]`", and an agent may assist in evaluating them "only when explicitly asked by the reviewer". |
| `templates/commands/constitution.md:21-38` | A scope guard prevents the constitution phase from implementing anything; non-governance intents are extracted and deferred. |
| `templates/commands/constitution.md:77, 100-104, 123` | The constitution lives at `.specify/memory/constitution.md` — inside the project. Semantic versioning is mandatory, and principles must be declarative, testable, and free of vague language. |

## 3. Decisions

## R3-D01 — The handoff boundary falls between `plan` and `tasks`

- **Need**: R2 established the contract as the Spec Kit artifact set but did not say which artifacts Morfeo produces and which the receiving side produces.
- **Decision**: Morfeo owns `constitution` (drafting), `specify`, `clarify` and `plan`. The supervision role owns `tasks`, `analyze`, `checklist` and `converge`. Implementers own `implement`.
- **Rationale**: `tasks` cannot be produced without concrete file paths — upstream marks a task lacking one as invalid (`tasks.md:179`). On an existing project Morfeo does not know the real layout without exploring it, and exploring the codebase to lay out files is the tech lead's work, not the designer's. `DESIGN.md` already assigns decomposition, dependency identification and parallelism decisions to the supervision role, so placing `tasks` with Morfeo would be the re-concentration PD-13 forbids.
- **Evidence**: `tasks.md:149-179`, `tasks.md:161`, `DESIGN.md` §4.
- **Alternatives considered**: Morfeo producing `tasks.md` as part of the contract was rejected for the reasons above, and because it would make the contract brittle — a breakdown written without seeing the code is a guess. Splitting `tasks` across both roles was rejected as ambiguous ownership.
- **Change impact**: Revises R2-D03, because `analyze` requires `tasks.md` and therefore cannot run on Morfeo's side. Completeness is now measured on both sides of the handoff.

## R3-D02 — The supervision role's first act is establishing executability, and that has a mechanism

- **Need**: `DESIGN.md` says the supervision role "receives and reviews the contract; checks that it is executable" without saying how.
- **Decision**: On receipt it derives the task breakdown and runs cross-artifact consistency analysis. That pass **is** the executability review. A CRITICAL finding against the contract is a contract defect and escalates to Morfeo per R2-D04.
- **Rationale**: `analyze` already measures exactly what executability means — requirements with no task, tasks with no requirement, contradictions, unresolved ambiguity, constitution conflicts — and is strictly read-only. A vague responsibility becomes a measurement without inventing anything.
- **Evidence**: `analyze.md:54, 115-191`.
- **Alternatives considered**: A separate bespoke executability review was rejected as duplicating `analyze`. Trusting Morfeo's own assurance was rejected because self-certification is what R0's checklist showed to be unreliable.
- **Change impact**: R7 must treat a failed executability pass as a terminal branch that escalates, not as a retry.

## R3-D03 — The supervision role is the independent reviewer upstream assumes is human

- **Need**: Upstream forbids agent self-approval of requirements-quality checklists and has `implement` stop and ask a human when items are unchecked. During unattended execution no human exists, so `implement` would stall.
- **Decision**: The supervision role is the reviewer. It answers the checklist gate within the authority the contract carries.
- **Rationale**: Upstream's concern is self-approval, not humanity as such. The supervision role authored neither the requirements (Morfeo did) nor the implementation (implementers do), so it satisfies the independence the rule exists to protect. This is the strongest upstream-grounded argument for Aether's three-role separation: the split manufactures the independent reviewer that Spec Kit can only assume.
- **Evidence**: `checklist.md:30-37`; `implement.md:56-88`.
- **Alternatives considered**: Abandoning custom checklists and relying only on the built-in agent-maintained `requirements.md` was rejected as discarding a real quality mechanism. Routing the gate to the owner was rejected because it destroys autonomy. Letting the implementer answer its own gate was rejected as exactly the self-approval upstream forbids.
- **Change impact**: R10 must not treat this as a self-granted authority; it is an assigned role duty. R11 should record who answered which gate.

## R3-D04 — Standing standards have two homes, not one

- **Need**: An earlier framing treated "the constitution" as the owner's cross-project standards. That is wrong about where the artifact lives.
- **Decision**: The constitution lives inside the project being built (`.specify/memory/constitution.md`) and holds that project's standards. Preferences that are true of the owner regardless of project live in Morfeo's learned memory. Morfeo drafts a project's constitution from both, plus what the project already does.
- **Rationale**: `constitution.md:77` places the artifact in the project. Writing owner preferences into it would push personal taste into every project Aether touches, including other people's, which contradicts PD-12's universality. R1-D09 already made Morfeo's memory the sole personalization channel, and this keeps that true.
- **Evidence**: `constitution.md:77`; `DESIGN.md` PD-12; R1-D09.
- **Alternatives considered**: A single Aether-level constitution was rejected as incompatible with a universal, open-source product. Duplicating owner preferences into each project's constitution was rejected as guaranteed drift.
- **Change impact**: R9 must treat Morfeo's preference memory as structural. R4 must decide how that memory is realized in Hermes.

## R3-D05 — The testing standard is per project

- **Need**: The owner requires software that is tested, while upstream treats test tasks as optional unless requested. Asked directly, the owner answered "según el proyecto".
- **Decision**: Whether and how a project is tested is recorded in that project's constitution. Aether imposes no universal testing rule and does not require test-first discipline. The standard must be resolved during extraction rather than defaulted, and for an existing project it is read from what the project already does.
- **Rationale**: The owner's answer, combined with `tasks.md:147`. Resolution during extraction is required because nobody is available to be asked later — the same reasoning as R1-D02. Test-first is not imposed because requiring it of an economical implementer tends to produce tests written to pass rather than tests that verify.
- **Evidence**: Christopher's direct answer; `tasks.md:147`; `constitution-template.md:16-19`, where test-first appears as an example principle a project may adopt rather than a Spec Kit requirement.
- **Alternatives considered**: Mandating tests universally was rejected by the owner. Leaving the upstream default in place was rejected because "optional unless requested" plus an absent owner silently yields no tests.
- **Change impact**: R11 must treat test evidence as conditional on the project's declared standard rather than assumed. R12's model qualification must account for a cheaper implementer still having to satisfy that standard.

## R3-D06 — Execution does not pause between stories; each converged story is a runnable increment

- **Need**: Upstream expects a human to scope `implement` across runs and validate between them. The owner delegated this decision.
- **Decision**: Execution proceeds continuously through the story phases without pausing for the owner. Each user story that converges is delivered as an independently runnable increment with its own validation path, and the end-of-work report lists them.
- **Rationale**: This satisfies both readings of "regresa cuando tengas algo sólido" without introducing a gate the owner explicitly removed in R1-D12. It also makes "small corrections, not fatal" concrete: if a later story fails, earlier ones remain intact and runnable. Upstream already supplies the structure — story phases are required to be complete, independently testable increments.
- **Evidence**: `tasks.md:145, 206-213`; `spec-template.md:13-24`; `implement.md:100-108` for the human-scoped alternative that Aether replaces.
- **Alternatives considered**: A single monolithic delivery at the end was rejected because a wrong direction surfaces too late. Pausing for owner validation after P1 was rejected as reintroducing a gate.
- **Change impact**: R7 owns increment boundaries and their reporting. R8 must decide how increments are represented without a pre-merge gate.

## 4. The Recurring Adaptation, Enumerated

R2-FR-230 stated the rule. R3 applies it exhaustively to the phases:

| Upstream expects a human to | Aether assigns it to |
|---|---|
| Answer up to five clarification questions and remain available | The owner, during extraction, with no cap |
| Own and tick requirements-quality checklists | The supervision role, as independent reviewer |
| Decide whether to proceed past an unchecked checklist gate | The supervision role, within contract authority |
| Approve remediation suggestions from consistency analysis | The supervision role for what it owns; Morfeo for contract defects |
| Take the next step recommended after convergence | The supervision role, bounded by the attempt budget |
| Scope a large implementation across several runs | The story phases in the breakdown |

Not one of these is a rewrite of upstream behavior. Each is a decision about who acts when nobody is watching.

## 5. Risks

| Risk | Mitigation | Owner |
|---|---|---|
| The supervision role becomes a bottleneck holding four phases | Its phases are sequential by nature and mostly analytical; parallelism lives in `implement` | R7 |
| A project constitution grows until findings are ignored | Small and sharp is a requirement, not advice; the owner is the only authority that may add principles | R3 |
| "According to the project" silently becomes "no tests" | The testing standard must be resolved during extraction, never defaulted | R3, R11 |
| The supervision role answers a checklist gate it should have escalated | Its answer must be bounded by the contract, and R11 records who answered what | R10, R11 |
| Assigning `tasks` to supervision leaves Morfeo unable to verify executability | Accepted: R2-D03 revised so the measurement happens where it can run, with escalation back to Morfeo | R2, R7 |

## 6. Deferred

- Hermes realization of skills-mode installation and per-role phase availability — R4.
- Whether Morfeo is a process, profile or session, and how he stays reachable — R5.
- Numeric attempt budgets and concurrency policy — R7.
- How increments are represented in version control — R8.
- Storage of Morfeo's preference memory — R9.
- Enforcement of role-phase boundaries — R10.
- Evidence classes and who-answered-what records — R11.
