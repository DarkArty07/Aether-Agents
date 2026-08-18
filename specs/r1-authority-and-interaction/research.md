# R1 Research: Authority and Human Interaction

**Purpose**: Evidence and rationale behind the R1 specification.  
**Primary evidence**: Christopher's direct statements during the R1 design session, 2026-08-17.

## 1. Source Statements

Recorded verbatim because they are the governing evidence for this stage:

> "Mi valor en Aether está en que yo hago el trabajo una sola vez bien. DISEÑAR DECIDIR E INNOVAR, una vez que está plasmado eso los agentes trabajan solos durante horas trabajando en lo que una vez ya decidí bien y si se equivocan en el futuro hacer pequeñas precisiones pero no deberían ser fatales."

> "Que piense mejor conmigo, pero cuando ya tengan toda la información de mí. Que trabajen sin mí."

> "Me puede buscar al inicio o si hay una situación realmente bloqueante como que una herramienta un proyecto o un framework no sirvió como debía. Pero lo correcto es que trabaje solo y me diga las dificultades o los bloqueantes al final, es decir no que se me detenga a cada rato porque lo que busco es autonomía."

> "Puede gastar lo que quiera."

## 2. Decisions

## R1-D01 — Two asymmetric phases instead of one interaction model

- **Need**: Christopher asked for both "think better with me" and "work without me", which read as contradictory until separated in time.
- **Decision**: Phase 1 is high-bandwidth extraction with Christopher present. Phase 2 is unattended autonomy with end-of-work reporting.
- **Rationale**: His statement resolves the contradiction explicitly — depth is wanted *before* the agents have his full intent, autonomy *after*.
- **Evidence**: Source statements 1 and 2.
- **Alternatives considered**: A single uniform interaction model was rejected because it forces either constant interruption or under-specified autonomy.
- **Change impact**: Reverses R0-D01's default for Phase 1. R0-D01 tells the agent not to ask; R1 requires Morfeo to ask thoroughly during extraction. The two do not conflict because they govern different activities, but the distinction must be preserved in R7 and any future prompt.

## R1-D02 — Extraction is Morfeo's primary capability

- **Need**: If the system runs unattended for hours, the cost of an unasked question is hours of misdirected work.
- **Decision**: Interrogation quality outranks design quality in Morfeo's instructions and receives the largest share of prompt attention.
- **Rationale**: There is no second opportunity to ask. Every downstream guarantee depends on Phase 1 being complete.
- **Evidence**: "cuando ya tengan toda la información de mí".
- **Alternatives considered**: Allowing mid-execution clarification was rejected by Christopher explicitly.
- **Change impact**: Shapes `morfeo.md`; affects R2, since a contract can only be as good as the extraction behind it.

## R1-D03 — Blocking means external reality failed

- **Need**: An agent permitted to interrupt "when blocked" will classify difficulty, uncertainty and preference gaps as blocking, defeating the autonomy requirement.
- **Decision**: Blocking is restricted to a tool, framework, project or dependency not doing what it was expected to do. Uncertainty, missing preference, disagreement and difficulty are explicitly not blocking.
- **Rationale**: Christopher's own definition was already narrow and external-facing; making it literal prevents erosion.
- **Evidence**: Source statement 3.
- **Alternatives considered**: A severity threshold was rejected as unenforceable through instructions and as an invitation to negotiate.
- **Change impact**: R7 must apply the same definition to the supervisor.

## R1-D04 — The effect boundary is shared truth, not the local machine

- **Need**: Christopher delegated the effects list. A boundary drawn at "leaves the machine" would gate `push` and destroy long autonomous runs.
- **Decision**: Free through pushing to a working branch and opening a pull request. Confirmation required for merge to main, tag, release, deploy, credentials, and deleting work Morfeo did not produce.
- **Rationale**: A working branch harms nothing and is fully reversible; the main branch is where a mistake becomes fatal. This directly serves "pequeñas precisiones pero no deberían ser fatales".
- **Evidence**: Source statements 1 and 3; Christopher delegated this decision.
- **Alternatives considered**: Gating `push` was rejected because it stalls unattended work with no safety gain. Gating local commits was rejected as incompatible with hours of autonomy.
- **Change impact**: R8 owns the branch model that makes this real.

## R1-D05 — The pull request is the confirmation mechanism — SUPERSEDED by R1-D12

*Superseded 2026-08-17. Christopher removed the confirmation model entirely: Morfeo maintains the project and the owner does not gate it. With no confirmation to give, the pull request is a record, not a mechanism. Retained here because the reasoning explains why the gated model was attempted.*

- **Need**: Confirmation normally implies interrupting Christopher, which contradicts the autonomy requirement.
- **Decision**: Where a pull request already presents the change and its evidence, it serves as the request for confirmation. No separate interruption is issued.
- **Rationale**: It carries the diff and evidence, waits without blocking the agent, and is reviewed when Christopher returns — satisfying both "confirm before merge" and "tell me at the end".
- **Evidence**: Derived from statements 3 and Christopher's acceptance-at-the-end reading.
- **Alternatives considered**: A separate approval channel was rejected as redundant machinery.
- **Change impact**: R8 and R11 rely on the pull request carrying evidence, not only the diff.

## R1-D06 — Unrestricted spending moves the bound to convergence

- **Need**: Christopher removed the spending limit while also requiring hours of unattended execution.
- **Decision**: No spending authorization exists. Runaway execution is bounded by attempt and convergence limits in R7 instead.
- **Rationale**: Without any bound, a non-converging supervisor can iterate indefinitely. The correct control is "stop looping", not "ask permission to spend".
- **Evidence**: Source statement 4; concern raised to Christopher and his decision reaffirmed.
- **Alternatives considered**: A soft advisory limit was rejected as a spending gate in disguise.
- **Change impact**: R7 must own attempt limits. R12 keeps cost accounting for visibility, not authorization.

## R1-D07 — Recoverability is a hard requirement

- **Need**: "No deberían ser fatales" was stated as an expectation, but it constrains architecture.
- **Decision**: Treated as a requirement: bounded blast radius per unit of work, reversibility until merge, evidence per unit.
- **Rationale**: Small corrections are only possible if a wrong unit is isolated from correct ones. Recorded now so R7, R8 and R11 inherit it rather than rediscovering it.
- **Evidence**: Source statement 1.
- **Alternatives considered**: Leaving it as a quality aspiration was rejected because nothing downstream would enforce it.
- **Change impact**: R7, R8, R11.

## 3. Open Questions

- **OPEN-101**: No artifact records what Aether is for. `DESIGN.md` specifies roles, authority and foundations but never the work the system performs. Every stage so far has designed the machinery of a product whose purpose is unstated. This must be resolved in `DESIGN.md`.
- **OPEN-102**: The repository carries `LICENSE`, `CODE_OF_CONDUCT.md`, `CONTRIBUTING.md` and issue templates, implying external contributors, while the authority model assumes Christopher is the only principal. One of the two is wrong.

## 4. Risks

| Risk | Mitigation | Owner |
|---|---|---|
| An incomplete extraction silently produces hours of wrong work | Extraction is the primary capability; Morfeo states assumptions explicitly | R1 |
| "Blocking" erodes into "difficult" over time | The definition is literal and external-facing | R7 |
| Unbounded spend plus unattended execution allows an infinite loop | Attempt limits replace the spending gate | R7 |
| Pull requests accumulate faster than Christopher reviews them | Acceptance is batched; volume becomes a visibility requirement | R11 |
| Designing R2–R13 without knowing Aether's purpose | Resolved — see section 5 | closed |

## 5. Extraction Session 2 — Purpose, History and Review

Conducted 2026-08-17. Christopher's answers are the governing evidence; recorded close to verbatim because they resolve OPEN-101 and OPEN-102.

### What Aether does

> "Aether programa lo que quiero, testeado validado y bien implementado. Si le digo haz un website, una sola vez defino qué quiero y los agentes se ponen a trabajar sobre eso."

Aether is a software factory. Input is a short statement of intent; output is working, tested, validated code.

> "No siempre trabajo sobre cosas nuevas, soy programador, trabajo sobre proyectos ya existentes y sobre proyectos nuevos."

Greenfield and brownfield are both first-class. Brownfield is the harder case for parallel agents and must be designed for, not treated as an extension.

### Why the previous architecture died

> "Aether era hub and spoke, Hermes tenía que hacer todo: delegar, diseñar, hablar conmigo, mantener sus skills, y desde ahí he intentado darle la arquitectura que necesito y por fin pensé en esta. Yo product owner, Morfeo designer, supervisor tech lead, implementador el que escribe el código bruto."

This is the most important evidence in the stage. The prior system did not crash — it failed by role overload. The three-role split is a corrective, and its inverse is the standing risk.

### Review and completion

> "Miro el proyecto funcional, es lo que miro."

> "Lo del tiempo es relativo, era una expresión para decir haz esto y vete, regresa cuando tengas algo sólido."

Review is by running the product, not reading the diff. Completion is defined by solidity, not by elapsed time.

### Universality

> "Esto no debe estar adaptado a mí, debe ser universal. Lo único que se adapta a mí son las preferencias que Morfeo genera a través de Hermes framework. ¿De qué me sirve que sea específico para websites? Estamos trabajando en varias cosas."

> "Es público, es código abierto."

### Failure condition

> "Esto me haría tirarlo a la basura si veo que los agentes no trabajan solos, o hacen porquerías porque no materializaron la idea que quería."

### Quality

> "Bien implementados según la obviedad. Si el programa no hace lo que quiero, ¿de qué sirvió la autonomía? Nada más para hacerme perder tiempo. Por eso es importante trabajar con specs y por eso estoy basándome MUCHO en las buenas prácticas que ya tiene Spec Kit."

Quality is fidelity, and the specification is its mechanism. The operational consequence is that "obvious" must be written down, since it is precisely what does not survive the trip to an agent.

## 6. Decisions from Session 2

## R1-D08 — The deliverable is a runnable project, not a diff

- **Need**: Christopher's value model collapses if reviewing is expensive. A pull request containing an entire website is hours of review, which means working twice.
- **Decision**: A completed body of work is reviewed by running it. Every delivery ships a quickstart validation guide with prerequisites, run commands, and expected outcomes.
- **Rationale**: He reviews the functional product, not the code. Spec Kit already produces exactly this artifact, so nothing needs inventing.
- **Evidence**: `templates/commands/plan.md:152-155` at revision `bf88c9f9a82fa370c7a7257aa2b3cf10b457b65c`, inspected directly: *"Create quickstart validation guide → quickstart.md: Document runnable validation scenarios that prove the feature works end-to-end. Include prerequisites, setup commands, test/run commands, and expected outcomes."*
- **Alternatives considered**: Code review as the acceptance mechanism was rejected because it reintroduces the labor the system exists to remove. A summary report was rejected because it is the agent's claim rather than observable evidence.
- **Change impact**: R7 must treat the runnable artifact as a completion requirement; R11 must treat it as evidence.

## R1-D09 — Aether is universal; personalization lives only in memory

- **Need**: Whether to tailor the system to Christopher's stacks and habits.
- **Decision**: No specialization by stack, domain or project type. Morfeo's instructions address the project owner generically, not Christopher by name. The sole adaptation channel is the preferences Morfeo learns through Hermes.
- **Rationale**: Christopher works across varied projects and publishes Aether as open source; hardcoding him would be wrong on both counts.
- **Evidence**: Christopher's direct statement.
- **Alternatives considered**: A Christopher-specific prompt was rejected; it is a one-line saving now and an awkward rewrite later.
- **Change impact**: Elevates R9's memory design from convenience to structural requirement — it is the only personalization mechanism the system has.

## R1-D10 — Extraction is not capped at five questions

- **Need**: Spec Kit's clarification budget is calibrated for a user who remains available afterwards. Aether's user leaves for hours.
- **Decision**: Aether keeps `clarify`'s ambiguity taxonomy, prioritization and question-quality rules, and removes its budget. Extraction continues until no material coverage gap remains.
- **Rationale**: Verified directly in `templates/commands/clarify.md` at the inspected revision: line 130 caps the session at five questions, line 133 constrains answers to multiple choice or five words, line 136 excludes stylistic preferences. Those constraints are correct for interactive development and wrong for a single-pass handoff into hours of unattended work. The R1 design session itself required twelve open-ended questions to surface Aether's purpose and the hub-and-spoke failure — neither would have been reached within the upstream budget.
- **Evidence**: `templates/commands/clarify.md:129-138`, revision `bf88c9f9a82f…`, inspected directly.
- **Alternatives considered**: Raising the cap to a larger fixed number was rejected as arbitrary; the correct terminal condition is coverage, not count.
- **Change impact**: This is a recorded deviation from upstream Spec Kit and R0-FR-014 requires it to be justified and revisited on upgrade. R3 owns the full Spec Kit profile.

## R1-D11 — Re-concentration is the standing architectural risk

- **Need**: The prior system failed by one agent holding four jobs. Nothing yet prevents the same drift.
- **Decision**: Recorded as a standing design constraint. Morfeo does not take implementation work, the supervisor does not redesign, and implementers do not decide scope. A later stage that blurs a role boundary is rebuilding the abandoned architecture.
- **Rationale**: The separation is corrective, not aesthetic, so its erosion is the specific regression to guard against.
- **Evidence**: Christopher's account of the hub-and-spoke failure.
- **Alternatives considered**: None; this is a direct reading of the stated history.
- **Change impact**: Applies to R2, R5, R7 and R13 as a review criterion.

## 7. Spec Kit Evidence Verified Directly

Inspected in this session at revision `bf88c9f9a82fa370c7a7257aa2b3cf10b457b65c`, working tree clean:

| File | Finding |
|---|---|
| `src/specify_cli/integrations/` (`AGENTS.md:34,84,144-168`) | `SkillsIntegration` installs `speckit-<name>/SKILL.md`; Claude is implemented as a subclass. On Claude- and Hermes-class agents, Spec Kit is natively skills, not slash commands. Confirms Christopher's premise. |
| `templates/commands/clarify.md:73-127` | Eleven-category ambiguity scan marking each `Clear / Partial / Missing`, producing an internal coverage map used for prioritization. This is the extraction machinery R1 requires, already built. |
| `templates/commands/clarify.md:129-138` | Five-question cap, five-word answers, stylistic preferences excluded. Basis for R1-D10. |
| `templates/commands/clarify.md:140-180` | Question-quality contract: one question at a time, real interrogative, mandatory "why it matters" sentence, recommendation stated first, answerable by a reader unfamiliar with Spec Kit. |
| `templates/commands/clarify.md:182-190` | Accepted answers are written back into the spec under a dated `## Clarifications` section, incrementally. Extraction is captured in the artifact by construction. |
| `templates/commands/plan.md:152-159` | `quickstart.md` is a planning output: runnable end-to-end validation with prerequisites, commands and expected outcomes. Basis for R1-D08. |
| `templates/commands/clarify.md:23-54` | Extension hook system via `.specify/extensions.yml` (`hooks.before_clarify`). This is the real surface for R1's three automations. |

Not yet inspected directly: `checklist.md`, `analyze.md`, `converge.md`. Claims about those remain secondhand from R0's research and must be verified before R3 relies on them.

## 8. Decisions from Session 3 — Removing the Gates

## R1-D12 — Morfeo maintains the project; the normal path has no confirmation gate

- **Need**: A confirmation boundary was proposed at merge to main, with tags, releases, deploys and credentials also gated.
- **Decision**: Rejected. Morfeo maintains the project end to end — commits, branches, pushes, pull requests, merges, tags, releases, deploys. The owner operates none of it. Two scope limits remain, and they are not confirmation steps: Morfeo uses only credentials and access already provisioned to him and does not widen them, and he does not delete or overwrite work he did not produce unless instructed.
- **Rationale**: Christopher's words: *"MORFEO MANTIENE EL PROYECTO YO NO, así como tú todo lo estás haciendo él hace TODO."* A gate at merge makes the owner the repository operator, which is the labor the product exists to remove. It also contradicts the value model directly: an unattended run that stops at merge is not unattended.
- **Evidence**: Christopher's explicit instruction, given after the gated model was presented for review and rejected.
- **Alternatives considered**: Gating only merge to main was the proposal and was rejected. Gating only irreversible external effects such as production deploys was not selected either — Christopher answered "TODO" to a question that listed deploy, release, tags and credentials together.
- **Change impact**: Supersedes R1-D05. Rewrites the effects and acceptance requirements. Moves the entire burden of safety from human approval to recoverability and to R10 enforcement. R8 must make every integrated change individually reversible, because reversal after the fact is now the only correction mechanism. R10 must constrain irreversible effects by design, since nothing human precedes them.

## R1-D13 — Out-of-scope findings are surfaced as a question, never acted on silently

- **Need**: While working on an existing project Morfeo will notice defects he was not asked to fix. Fixing them silently expands scope; ignoring them wastes the observation.
- **Decision**: He does neither. Findings are reported in the end-of-work report as a question about whether to fix them.
- **Rationale**: Christopher's words: *"Si detecta algo me pregunta si quiero corregir algo que ya detectó."* Placing it in the end-of-work report satisfies both this and the no-interruption rule — it is a question that waits rather than a question that interrupts.
- **Evidence**: Christopher's explicit instruction.
- **Alternatives considered**: Autonomous repair was rejected as silent scope expansion. Discarding the observation was rejected as waste. Mid-flight questioning was rejected as a violation of R1-D03.
- **Change impact**: The end-of-work report gains a required section. R2 must keep such findings outside the contract's scope until the owner accepts them.

## 9. Consequence Christopher Should Know

Removing the gates concentrates all protection in two places that were previously secondary:

1. **Recoverability (R8).** Reversal after the fact is now the only correction mechanism. If a change cannot be individually reverted, a mistake is permanent.
2. **Irreversible effects (R10).** Published releases, deployments and third-party effects cannot be reverted by Git. These must be constrained by design, because no human sees them first.

This is not an argument to reinstate the gates. It is the bill that comes with removing them, and it must be paid in R8 and R10 rather than deferred.
