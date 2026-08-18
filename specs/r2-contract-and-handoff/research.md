# R2 Research: The Contract and the Handoff

**Purpose**: Evidence for what Morfeo must hand to the supervision role.  
**Upstream repository**: `https://github.com/github/spec-kit.git`  
**External checkout**: `/home/darkarty/Desktop/agentes/aether-research/spec-kit`  
**Inspected revision**: `bf88c9f9a82fa370c7a7257aa2b3cf10b457b65c`  
**Revision state at inspection**: working tree clean, HEAD verified against the recorded revision.  
**Boundary**: the checkout is outside Aether and is research evidence only.

## 1. Research Question

R1 established that Morfeo extracts the owner's intent once and the owner then leaves. The same structure repeats one level down: Morfeo hands over a contract and is no longer the one executing. So the question is what the contract must contain for the supervision role to work without asking anyone, and how much of that Spec Kit already provides.

## 2. Central Finding

**Spec Kit already is the contract.** Aether does not need to invent a contract artifact. The handoff is the Spec Kit artifact set governed by the constitution:

```text
constitution.md   standing, project-wide, non-negotiable
spec.md           intent, user stories, acceptance scenarios, FR-###, SC-###, assumptions
plan.md           technical context, decided choices, structure, complexity justifications
data-model.md     entities, when the feature has data
contracts/        interfaces, when the feature has them
quickstart.md     runnable end-to-end validation
tasks.md          ordered executable work with parallel markers
```

Only three things Aether requires are absent upstream (section 5).

## 3. Verified Evidence

All references inspected directly at revision `bf88c9f9a82f…`.

### The convergence loop already exists as a prompt

`templates/commands/converge.md:57-83, 145-235`

`converge` reads `spec.md`, `plan.md` and `tasks.md` as the **sole source of intent** with the constitution as governing constraint, assesses the present state of the code, and appends remaining work to `tasks.md` as traceable tasks. It classifies every gap by type:

| Gap type | Meaning |
|---|---|
| `missing` | required work absent from the code entirely |
| `partial` | work exists but does not fully satisfy the requirement |
| `contradicts` | code conflicts with stated intent or a constitution MUST |
| `unrequested` | code contains work not called for by spec, plan or tasks |

Severity is CRITICAL / HIGH / MEDIUM / LOW, where CRITICAL means a constitution MUST violation or a gap blocking a P1 user story. Each appended task carries a `<source-ref>` tracing it to `FR-003`, `SC-002`, `US1/AC2` or `Constitution II`.

**Implication**: R7 does not design an orchestrator. It configures and bounds this loop.

### The executor cannot rewrite intent — enforced by prompt

`templates/commands/converge.md:71-83`

> "**APPEND-ONLY, NEVER REWRITE**: The command's **only** write is appending a new `## Phase N: Convergence` section to `tasks.md`. It MUST NOT modify `spec.md` or `plan.md` in any way."

This is PD-04 — lower roles cannot silently change higher intent — already realized as an instruction rather than as an enforcement mechanism. It is direct evidence that Aether's authority model is achievable prompt-natively.

### The terminal condition is clean and already specified

`templates/commands/converge.md:82-83, 222-234`

When nothing remains, `tasks.md` is left byte-for-byte unchanged, the outcome is reported as converged, and the recommended next step is review or opening a pull request. No empty phase header, no ceremony.

This is the operational form of the owner's "regresa cuando tengas algo sólido".

### `unrequested` is exactly R1-D13

`templates/commands/converge.md:156-158`

> "`unrequested`: the code contains work not called for by the spec, plan, or tasks (surfaced for awareness — converge does **not** delete code, it only appends a task to review/justify or remove it)."

The owner's instruction — *"si detecta algo me pregunta si quiero corregir algo que ya detectó"* — is upstream's existing handling of out-of-scope findings. R1-D13 is not an Aether invention and needs no new mechanism.

### Bounded blast radius is already structural

`templates/spec-template.md:13-24`

> "Each user story/journey must be INDEPENDENTLY TESTABLE — meaning if you implement just ONE of them, you should still have a viable MVP... Developed independently, Tested independently, Deployed independently, Demonstrated to users independently."

Stories are prioritized P1/P2/P3 and each carries an **Independent Test** statement. This satisfies R1-D07: decomposition into independently testable slices is what makes one wrong unit non-fatal. Aether inherits it rather than designing it.

### Contract completeness is measurable

`templates/commands/analyze.md:52-60, 115-191`

`analyze` is **strictly read-only** and repairs defects at the artifact that owns them:

> "Constitution conflicts are automatically CRITICAL and require adjustment of the spec, plan, or tasks—not dilution, reinterpretation, or silent ignoring of the principle."

Its detection passes are duplication, ambiguity (vague adjectives lacking measurable criteria, unresolved placeholders), underspecification, constitution alignment, coverage gaps, and inconsistency. It reports a **coverage percentage** of requirements having at least one task, plus unmapped tasks and ambiguity counts.

**Implication**: "the contract is complete when the supervisor needs to ask nobody" becomes a measured property — zero CRITICAL findings, full requirement coverage, no unresolved ambiguity markers — rather than a judgement call.

### Requirements quality is checkable, and reviewer-owned

`templates/commands/checklist.md:9-37, 224-227`

Checklists are "unit tests for English" — they validate requirement writing, never implementation behavior. Two ownership rules matter:

- Custom checklists are **reviewer-owned**: "This command generates or appends checklist items; it MUST NOT mark generated items `[x]`."
- `checklists/requirements.md` is the **explicit exception** — a built-in spec-quality checklist maintained by `specify` and `clarify`.

Traceability is a hard requirement: "MINIMUM: ≥80% of items MUST include at least one traceability reference", using `[Spec §X.Y]` or the markers `[Gap]`, `[Ambiguity]`, `[Conflict]`, `[Assumption]`. IDs are `CHK###` from `CHK001`.

### What the contract carries about technical freedom

`templates/plan-template.md:13-44, 106-113`

`plan.md` records Language/Version, Primary Dependencies, Storage, Testing, Target Platform, Project Type, Performance Goals, Constraints, Scale/Scope — each either decided or explicitly marked `NEEDS CLARIFICATION`. A **Constitution Check** gate precedes research and is re-checked after design, and **Complexity Tracking** requires any constitution violation to be justified against the simpler alternative that was rejected.

This is how the contract distinguishes what is already decided from where the executor still has freedom: a filled field is a decision, a `NEEDS CLARIFICATION` field is not yet one.

## 4. The Constitution Is Where "The Obvious" Lives

The owner defined quality as fidelity — *"bien implementados según la obviedad"* — and named Spec Kit's practices as the mechanism. The evidence identifies the specific artifact that carries it.

Both `analyze` and `converge` treat `/memory/constitution.md` as non-negotiable and score a MUST violation as CRITICAL, on every feature, automatically. The constitution is therefore the one place where a standing standard is written **once** and enforced **forever**, which is precisely the owner's value model applied to quality rather than to features.

`templates/constitution-template.md` carries principles, constraints and workflow, governance, and semantic version metadata — not a decision registry.

**Implication**: the highest-leverage artifact in Aether is not the per-feature contract. It is the constitution, because it is the only artifact where an extraction session pays off across every future contract.

## 5. What Spec Kit Does Not Provide

Three gaps, and they are the only genuinely new contract content Aether must define:

| Gap | Why Aether needs it | R1 source |
|---|---|---|
| **Authority and limits carried by the contract** | Nothing upstream states what the executor may do, since upstream assumes a human is present and holds authority | FR-110 to FR-116 |
| **Attempt and convergence budget** | The owner removed the spending gate, so the only bound on a non-converging loop must travel with the contract | FR-112, FR-116 |
| **Brownfield boundary** | Conventions that must be followed, code that must not be touched, tests that must keep passing. `converge` assesses present code and `unrequested` catches additions, but no artifact states the boundary in advance | PD-11, FR-118 |

## 6. The Structural Adaptation Aether Must Make

Every Spec Kit command ends by **recommending a next step to a human who is present**:

- `analyze:196-202` — "If CRITICAL issues exist: Recommend resolving before implement", then "Ask the user: Would you like me to suggest concrete remediation edits?"
- `converge:228-234` — recommends running implement, or proceeding to review and opening a PR
- `clarify:140-180` — an interactive sequential questioning loop

In Aether, during Phase 2, **no human is present**. The adaptation is therefore not a rewrite of these commands. It is a single consistent decision applied across all of them:

> When a Spec Kit command would stop and recommend a step to a human, Aether must have already decided which role takes that step unattended.

This is the same shape as R1-D10, where `clarify`'s five-question budget was removed because it assumed a user who stays. R3 owns the full mapping; R2 owns it for the contract handoff and the defect return.

## 7. Open Questions Requiring the Owner

- **OQ-201 — resolved 2026-08-17.** Morfeo remains available, but only for blocking situations. Christopher: *"Si, Morfeo se queda en bloqueante."* The supervisor does not consult Morfeo about preferences or choices it can responsibly make; it reaches him only when genuinely stuck. This is R1's interruption rule applied one level down.

  Two blocking kinds must be distinguished, because they have different destinations:

  | Blocking kind | Meaning | Goes to |
  |---|---|---|
  | **Contract defect** | The contract is contradictory, impossible, or missing something needed to proceed | Morfeo, the only role that may revise it |
  | **External failure** | A tool, framework, project or dependency did not do what it was expected to do | The end-of-work report to the owner; Morfeo cannot fix a broken framework either |

  This makes the owner's "small corrections, not fatal" achievable without him: a contract defect is repaired by its author mid-flight rather than waiting for the owner to return.
- **OQ-202 — resolved 2026-08-17, delegated.** Christopher asked for the constitution to be explained, then delegated the timing decision and closed R2. Decision: the extraction of his standing code-quality standards belongs to **R3**, not R2. R3 owns the Spec Kit method mapping, and the constitution is Spec Kit's governance artifact, so its content and amendment authority sit there without distortion. R3 is also the immediately following stage, so the highest-leverage extraction is not deferred into the indefinite future.

  Recorded as guidance for that session: keep the constitution small and sharp. `analyze` and `converge` score every MUST violation as CRITICAL, so a long or vague constitution produces findings on every feature until the owner stops reading them, which destroys the mechanism it was meant to provide.

## 9. Decisions

## R2-D01 — The contract is the Spec Kit artifact set; Aether adds no contract artifact

- **Need**: The roadmap originally called for a "contract metamodel", which implied designing a new object.
- **Decision**: The contract is `constitution` + `spec` + `plan` + `data-model` + `contracts/` + `quickstart` + `tasks`. No Aether-specific contract artifact is created.
- **Rationale**: Upstream already carries intent, prioritized independently testable stories, acceptance scenarios, measurable success criteria, assumptions, decided-versus-open technical choices, and a runnable validation path. A second artifact stating obligations would compete with the first, which R0-FR-004 forbids.
- **Evidence**: `templates/spec-template.md` and `templates/plan-template.md` in full; `templates/commands/converge.md:109-131`, which enumerates exactly what the executing side loads as intent.
- **Alternatives considered**: A dedicated `contract.md` was rejected as duplicated truth. Extending `spec.md` with execution concerns was rejected because `spec.md` owns intent, not execution constraints.
- **Change impact**: R3 must map phases onto these artifacts rather than onto invented ones. R7 configures a loop that already reads them.

## R2-D02 — Authority, budget and brownfield boundary live in `plan.md`

- **Need**: Three things Aether requires are absent upstream, and they need a home that the existing machinery reads.
- **Decision**: They form an execution envelope inside `plan.md`: the authority the executing side may exercise, the attempt and convergence budget, and the brownfield boundary (conventions to follow, areas not to touch, tests that must keep passing).
- **Rationale**: `plan.md` already constrains execution and is already loaded by `converge` for technical constraints and for the named file touch-points the plan says will be created or edited. Putting the envelope there means the existing loop reads it without modification. Placing it in `spec.md` would confuse intent with execution limits; placing it in a new artifact would recreate the problem R2-D01 avoids.
- **Evidence**: `templates/plan-template.md:13-44, 106-113`; `templates/commands/converge.md:117-122`; `templates/commands/analyze.md:87-92`.
- **Alternatives considered**: A separate `handoff.md` was rejected as a fourth source of obligations. Carrying authority only in the runtime message was rejected because it would not survive a resumed or re-read contract.
- **Change impact**: R7 sets the numeric budget. R10 enforces the authority and boundary rules. R6 must not assume authority travels only in transport.

## R2-D03 — Contract completeness is measured, not asserted — REVISED by R3

*Revised 2026-08-17 during R3. The original decision placed the full cross-artifact measurement on Morfeo's side before handoff. That is not possible: `templates/commands/analyze.md:54` requires a complete `tasks.md` to exist, and R3-D02 assigns task derivation to the supervision role. Completeness is therefore measured on **both** sides — requirements quality before handoff, cross-artifact consistency after receipt — and the supervisor's cross-artifact pass is what "reviewing the contract for executability" concretely means. The measurement is not weakened; it moves to the only place it can actually run. See `spec.md` §5.*

- **Need**: "The supervisor needs to ask nobody" must be checkable, or it becomes Morfeo's opinion of his own work.
- **Decision**: A contract is complete when no CRITICAL finding remains, every requirement maps to at least one task and vice versa, and no unresolved clarification marker or unquantified vague term is left. Requirements-quality validation carries traceability references.
- **Rationale**: `analyze` already produces precisely these measurements — coverage percentage, unmapped tasks, ambiguity counts, constitution alignment — and is strictly read-only, repairing defects at the owning artifact. `checklist` supplies the requirements-quality standard, including the ≥80% traceability minimum.
- **Evidence**: `templates/commands/analyze.md:56-60, 115-191`; `templates/commands/checklist.md:150-168, 224-227`.
- **Alternatives considered**: Morfeo self-certifying completeness was rejected; R0's own checklist demonstrated how an agent marking its own work misses real gaps.
- **Change impact**: R11 extends this from requirements quality to execution evidence.

## R2-D04 — Contract defects go to Morfeo; external failures go to the owner's report

- **Need**: Christopher decided Morfeo stays available "en bloqueante", which required distinguishing what counts as blocking and where each kind goes.
- **Decision**: A contradictory, impossible or incomplete contract escalates to Morfeo, the only role permitted to revise it. A tool, framework, project or dependency that failed goes to the end-of-work report. The supervision role must not improvise around either.
- **Rationale**: Morfeo can repair a contract and cannot repair a broken framework. Routing each to the party who can act on it is what makes "small corrections, not fatal" achievable without the owner present.
- **Evidence**: Christopher's instruction; `templates/commands/converge.md:71-83`, which already forbids the executing side from editing `spec.md` or `plan.md`.
- **Alternatives considered**: Letting the supervisor amend the contract was rejected as re-concentration of roles (PD-13) and a violation of PD-04. Stalling until the owner returns was rejected as the loss of autonomy the product exists to provide.
- **Change impact**: R5 must keep Morfeo reachable during execution. R7 must treat contract escalation as a terminal branch of a work unit, not a retry.

## R2-D05 — Deviations from upstream are recorded, never silent

- **Need**: Aether will keep adapting Spec Kit, and an unrecorded adaptation becomes indistinguishable from a misunderstanding at upgrade time.
- **Decision**: Every deviation is recorded with its rationale in the owning stage's research artifact. Adaptation may redistribute work across roles and remove assumptions of human presence; it may not quietly drop a normative principle.
- **Rationale**: Two deviations already exist — `clarify`'s question budget (R1-D10) and the human-recommendation endings across commands. Both are defensible and both would look arbitrary in six months without a written reason.
- **Evidence**: The method recorded in the repository's `AGENTS.md`; `templates/commands/analyze.md:60` on not diluting principles.
- **Alternatives considered**: Tracking deviations in a single central register was rejected as a competing source of truth; they belong beside the decision that created them.
- **Change impact**: Applies to every remaining stage, and to any future Spec Kit upgrade review.

## 8. Withdrawn Finding About R0's Checklist

An earlier version of this artifact recorded that `specs/r0-design-governance/checklists/requirements.md` failed upstream's traceability standard. **That finding is withdrawn as inaccurate.**

On inspection the file carries an explicit evidence pointer on every checked item and states the governing rule directly: *"A checked box without a valid evidence pointer is a checklist defect."* It meets `checklist.md:224-227` well above the ≥80% minimum.

The `CHK###` identifier convention also does not apply. `checklist.md:141-146` defines it for custom checklists generated by that command, and `checklist.md:37` explicitly excludes `checklists/requirements.md` as the built-in spec-quality checklist maintained by `specify` and `clarify`.

Recorded rather than deleted because the error is instructive: the claim came from reading an earlier revision of the file and not re-checking it before repeating it. That is exactly the failure the method in `AGENTS.md` exists to prevent, and it occurred against Aether's own artifacts rather than against upstream.
