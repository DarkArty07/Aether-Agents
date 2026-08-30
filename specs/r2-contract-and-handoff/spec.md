# R2 Specification: The Contract and the Handoff

**Roadmap ID**: R2  
**Stage status**: done  
**Amended**: 2026-08-24 — Objective Contract identity/materialization added after #227; prior 2026-08-18 pipeline scoping retained
**Decision authority**: Christopher  
**Autonomous design delegate for this stage**: Hermes  
**Future role owner**: Morfeo  
**Depends on**: R0 (`../r0-design-governance/spec.md`), R1 (`../r1-authority-and-interaction/spec.md`), `DESIGN.md`  
**May affect**: R3, R5, R7, R8, R9, R10, R11  
**Parent roadmap**: `../../ROADMAP.md`  
**Research**: `research.md`  
**Spec Kit evidence revision**: `bf88c9f9a82fa370c7a7257aa2b3cf10b457b65c`

## 1. Purpose

R2 defines what Morfeo hands to the supervision role, and what comes back, after Morfeo selects the PD-44 pipeline route. A bounded direct operation crosses no role boundary and therefore creates no contract handoff merely to satisfy R2.

The governing finding is that **Aether does not need to invent a contract**. Spec Kit's artifact set already carries almost all of it, and its `analyze` and `converge` commands already implement the completeness check and the convergence loop as prompts. R2's real work is small: name what the handoff consists of, add the three things upstream has no reason to carry, and decide who acts where upstream would stop and ask a human.

R2 does not map Spec Kit phases across roles or decide constitution content (R3), define topology or whether Morfeo is a process (R5), select a transport (R6), decide how work is decomposed or set numeric limits (R7), define branch mechanics (R8), choose persistence (R9), or design enforcement (R10).

## 2. The Handoff Completeness Principle

R1 established that the owner states intent once and then leaves, so Morfeo must extract everything before he goes. The same structure repeats one level down: **Morfeo also leaves**, and the supervision role is left with only what is written.

The failure mode is therefore identical at every handoff — what the upstream party found obvious and did not write does not exist for the downstream party. This yields the completeness test:

> **The contract is finished when the supervision role needs to ask nobody.**

Section 5 makes that test measurable rather than a judgement call.

## 3. What the Contract Is

The normative obligation set remains the Spec Kit artifact set governed by the constitution. An Aether **Objective Contract** now gives that set one durable, project-bound, versioned handoff identity and may state only objective-level bindings that have no other owning artifact. It references canonical Spec Kit obligations rather than copying or contradicting them. This amendment is specified by `../003-objective-contracts/spec.md` and was required by the demonstrated transport failure in #227.

| Artifact | What it owns in the handoff |
|---|---|
| `constitution.md` | Standing, project-wide, non-negotiable principles. Applies to every contract, not one. |
| `spec.md` | Intent, prioritized and independently testable user stories, acceptance scenarios, `FR-###`, measurable `SC-###`, assumptions, edge cases. |
| `plan.md` | Technical context, which choices are decided and which remain open, project structure, justified complexity, and Aether's execution envelope (section 4). |
| `data-model.md` | Entities, when the work involves data. |
| `contracts/` | Interfaces, when the work has them. |
| `quickstart.md` | The runnable end-to-end validation the owner uses to review. Required by R1-FR-118. |
| `tasks.md` | Ordered executable work, and the only artifact the executing side may append to. |

- **FR-201**: The normative obligation set MUST remain the Spec Kit artifact set. An Objective Contract MUST provide only durable handoff identity, provenance, project binding and objective-level content without contradicting an existing owning artifact.
- **FR-201a**: Every Morfeo → Supervisor pipeline handoff MUST reference one finalized, versioned Objective Contract. Bounded direct Morfeo work creates none.
- **FR-201b**: The Kanban body MUST be a short Contract Handoff Envelope and MUST NOT substitute for or duplicate the full Objective Contract.
- **FR-201c**: The authoring capability MUST bind every Objective Contract to one explicitly verified portable project UUID; unresolved or conflicting identity causes zero write and zero dispatch.
- **FR-202**: Optional artifacts MUST be created only when they have content.
- **FR-203**: A contract MUST include `quickstart.md`, since delivery is reviewed by running the product. This is the contract-level runnable validation the owner uses; per-unit verification evidence is a separate, narrower record produced at each unit's completion.
- **FR-204**: A decided technical choice is a filled field; an open one is explicitly marked as needing clarification. Absence MUST NOT be read as freedom.

## 4. Aether's Execution Envelope

Three things Spec Kit has no reason to carry, because upstream assumes a human is present who holds authority and judges when to stop. They live in `plan.md`, because `plan.md` is already the artifact that constrains execution and is already loaded by `converge` as a source of intent.

- **FR-204a**: The envelope is contract-level and lives in `plan.md`. A per-unit instance of it — which profile executes, which model, which workspace kind — is set when the unit is materialized for execution (R5 §6). The envelope constrains those instances; it is not replaced by them.
- **FR-205**: The contract MUST carry the authority the executing side may exercise, per R1-FR-110 to R1-FR-116.
- **FR-206**: Authority MUST NOT be inherited or self-granted. The supervision role MUST NOT confer on an implementer more than the contract conferred on it, and MUST NOT widen its own.
- **FR-207**: The contract MUST carry an attempt and convergence budget. Since the owner removed the spending gate, this is the only bound on a non-converging loop.
- **FR-208**: For work on an existing project, the contract MUST state the brownfield boundary: conventions that must be followed, areas that must not be touched, and tests that must keep passing.
- **FR-209**: The brownfield boundary MUST be stated in advance. Detecting an unrequested change afterwards is a safety net, not a substitute for the boundary.

## 5. When the Contract Is Complete

Completeness is measured with mechanisms that already exist upstream, not asserted by the party who wrote the artifact. It is measured **twice, on both sides of the handoff**, because cross-artifact analysis requires a task breakdown that does not exist until the receiving side produces it.

### Before handoff — Morfeo's side

- **FR-210**: Morfeo MUST validate the requirements quality of what he wrote: completeness, clarity, consistency, measurability, and scenario coverage.
- **FR-211**: No unresolved clarification marker or unquantified vague term may remain at handoff.
- **FR-212**: Requirements-quality validation MUST use traceability references, per upstream's standard of at least 80% of items carrying one.
- **FR-213**: Morfeo MUST NOT claim cross-artifact consistency he cannot yet measure.

### After receipt — the supervision side

- **FR-214**: The receiving side MUST establish executability by deriving the task breakdown and then running cross-artifact consistency analysis. This is what "reviewing the contract" concretely means.
- **FR-215**: Every requirement MUST map to at least one task, and every task MUST map to at least one requirement.
- **FR-216**: A CRITICAL finding against the contract itself MUST be treated as a contract defect and escalated, not worked around.
- **FR-217**: Consistency analysis MUST be read-only, and a defect MUST be repaired in the artifact that owns it rather than patched downstream.
- **FR-218**: A constitution conflict MUST be resolved by changing the spec, plan, or tasks — never by diluting, reinterpreting, or silently ignoring the principle.

## 6. What Comes Back

- **FR-219**: The executing side MUST treat `spec.md` and `plan.md` as read-only. Remaining work is appended to `tasks.md`, traced to the requirement that originated it, and each appended unit is then materialized as a new execution instance rather than reopening a completed one. R5 §6 owns that seam.
- **FR-220**: Findings MUST be classified by gap type — absent, incomplete, contradicting stated intent, or present but never requested.
- **FR-221**: Work present but never requested MUST be surfaced as a question and MUST NOT be deleted or silently kept, per R1-FR-122 and PD-16.
- **FR-222**: A contract defect — contradictory, impossible, or missing something needed to proceed — MUST be escalated to Morfeo, the only role permitted to revise the contract.
- **FR-223**: An external failure — a tool, framework, project or dependency not doing what it was expected to do — MUST go to the owner's end-of-work report rather than being silently absorbed into dispatched scope. A separately authorized direct operational objective MAY ask Morfeo to inspect or repair that failure under PD-44; technical capability alone does not widen the current objective.
- **FR-224**: The supervision role MUST NOT improvise around a contract defect. Improvisation is the mechanism by which the owner's stated failure mode occurs.
- **FR-225**: Convergence MUST terminate either as converged, or as not converged with the budget exhausted. Both are legitimate outcomes.
- **FR-226**: When nothing remains, the outcome MUST be reported as converged without producing empty ceremony.

### Incremental return

- **FR-227**: Execution MUST NOT pause for the owner between user stories. There is no routine gate. A unit blocked on a contract defect or an external failure is the exception, and it waits without stopping its siblings (R5 §7).
- **FR-228**: Each user story that converges MUST be delivered as an independently runnable increment with its own validation path.
- **FR-229**: The end-of-work report MUST list the increments, so that a failure in a later story leaves earlier ones intact, inspectable, and runnable.

## 7. The Structural Adaptation

- **FR-230**: Wherever a Spec Kit command would stop and recommend a step to a human, Aether MUST have already decided which role takes that step unattended.
- **FR-231**: Every deviation from upstream MUST be recorded with its rationale in the owning stage's research artifact, so that a future upstream upgrade is reviewed rather than rediscovered.
- **FR-232**: Adaptation MUST NOT weaken Spec-Driven Development. Redistributing work across roles and removing assumptions of human presence is permitted; quietly dropping a normative principle is not.

## 8. Requirements Inherited by Later Stages

| Requirement | Owner |
|---|---|
| Map Spec Kit phases to Morfeo, supervision, and implementers; decide constitution content and amendment authority | R3 |
| Extract the owner's standing code-quality standards into constitution principles — small and sharp, not comprehensive | R3 |
| Morfeo must remain reachable for contract defects during execution | R5 |
| Configure and bound the existing convergence loop rather than designing an orchestrator | R7 |
| Set the numeric attempt and convergence budget the contract carries | R7 |
| Decompose along independently testable user stories, which is what makes one wrong unit non-fatal | R7 |
| Make every integrated change individually reversible; there is no pre-merge gate | R8 |
| Enforce the brownfield boundary and the no-self-granted-authority rule | R10 |
| Treat the runnable validation path as evidence, not a report | R11 |

## 9. Success Criteria

- **SC-201**: A supervision role given only the contract can execute to a terminal outcome without contacting the owner. Raising a blocker is not contacting the owner — it queues durably and interrupts nobody.
- **SC-202**: Every task in a completed contract traces to a requirement, and every requirement to at least one task.
- **SC-203**: No contract reaches handoff carrying a CRITICAL finding or an unresolved clarification marker.
- **SC-204**: A contract defect discovered during execution is repaired by Morfeo without waiting for the owner.
- **SC-205**: An unrequested change is surfaced as a question in the end-of-work report, neither applied nor discarded.
- **SC-206**: Aether introduces no artifact that duplicates obligations already carried by a Spec Kit artifact.
- **SC-207**: Every Aether deviation from upstream has a recorded rationale.

## 10. Done When

- [x] The handoff completeness principle is stated.
- [x] The contract is identified as the Spec Kit artifact set, with per-artifact ownership.
- [x] The three genuinely missing pieces are specified and located.
- [x] Contract completeness is made measurable.
- [x] The return path, defect escalation, and terminal outcomes are specified.
- [x] The recurring adaptation to upstream is stated as a rule.
- [x] Upstream evidence is verified by direct inspection at a recorded revision.
- [x] Requirements inherited by later stages are recorded.
- [x] Christopher delegated the remaining decisions and closed the stage.
