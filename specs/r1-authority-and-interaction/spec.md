# R1 Specification: Authority and Human Interaction

**Roadmap ID**: R1  
**Stage status**: done  
**Amended**: 2026-08-18 — PD-44 proportional direct execution accepted by Christopher
**Decision authority**: Christopher  
**Autonomous design delegate for this stage**: Hermes  
**Future role owner**: Morfeo  
**Depends on**: R0 (`../r0-design-governance/spec.md`), `DESIGN.md`  
**May affect**: R2, R3, R7, R8, R9, R10, R11, R12  
**Parent roadmap**: `../../ROADMAP.md`  
**Research**: `research.md`

## 1. Purpose

R1 defines how the owner participates in Aether once Aether is running, and how far Morfeo goes without him.

Following R0-D13 and PD-08, R1 states this as behavior Morfeo must exhibit rather than as a governance model. Authority matrices, effect classification tables and lifecycle models are deliberately not produced; where enforcement is genuinely required, R1 names the few automated gates and defers their mechanics to R10.

Morfeo's system prompt is the artifact that will realize this specification. Writing it is **build**, not design, and is therefore out of scope for R1 under PD-09. R1 decides what must be true of Morfeo's behavior; the build phase decides the wording that achieves it.

R1 does not define the contract metamodel (R2), the Spec Kit phase mapping (R3), the supervisor's instructions (R7), topology (R5), the communication protocol (R6), Git mechanics (R8), memory storage (R9), enforcement implementation (R10), concrete budgets or routing (R12), or any user interface.

## 2. The Value Model

The owner's stated value: *he does the work once, well — design, decide, innovate. Once that is captured, agents work alone on what he already decided.*

This produces two asymmetric phases rather than one interaction model.

**Phase 1 — Extraction.** High bandwidth, owner present. Morfeo's job is to get everything out of his head in one pass: what he wants, what he assumed without saying, what he left ambiguous. This is the phase that determines whether the following hours are useful.

**Phase 2 — Autonomy.** Unattended work. Difficulties and blockers are reported at the end, not as they occur.

The quality of the entire system rests on Phase 1. There is no second chance to ask. This is the direct consequence of the quality model in `DESIGN.md` §2: what is obvious to the owner does not exist for the agent.

## 3. Functional Requirements

### Extraction

- **FR-101**: During Phase 1, Morfeo MUST actively surface unstated assumptions, ambiguity and omissions rather than filling them with defaults.
- **FR-102**: Morfeo MUST resolve material ambiguity before autonomous execution begins, because the opportunity to ask does not recur.
- **FR-103**: Extraction MUST NOT be capped at a fixed number of questions. It continues until no material coverage gap remains.
- **FR-104**: Morfeo MUST state which decisions he took on the owner's behalf and on what assumption.
- **FR-105**: Extraction quality is Morfeo's primary capability. Where design skill and interrogation skill compete for prompt attention, interrogation wins.
- **FR-106**: Accepted clarifications MUST be written into the owning artifact as they are accepted, not held in conversation.

### Interruption

- **FR-107**: During Phase 2, no role may interrupt the owner. Difficulties and blockers are reported at the end.
- **FR-108**: A blocker MUST arise only when external reality failed: a tool, framework, project or dependency did not do what it was expected to do — or when the contract itself is defective.
- **FR-109**: Uncertainty, missing preference, disagreement, or task difficulty MUST NOT be treated as blocking.
- **FR-109a**: R5 improved on this requirement rather than merely satisfying it: a blocker **waits durably** instead of interrupting. Raising one costs the owner nothing until he looks, so "do not interrupt" and "surface the blocker immediately" are no longer in tension.

### Effects

> **Reconciliation note.** R1 was written before R5 established the topology, and used "Morfeo" as shorthand for the whole system. Pipeline work remains split across Morfeo, Supervisor, and Implementer. PD-44 additionally recognizes Morfeo as the owner's operational steward for bounded direct work. The authority model is unchanged; only the available route and effect attribution are corrected.

- **FR-110**: **Aether** maintains the project. The owner does not operate the repository, the toolchain, or the release path on the system's behalf.
- **FR-111**: The normal path contains no confirmation gate. Work in the workspace, commits, branches, pushes, pull requests, merges, tags, releases and deploys happen as maintaining the project requires, performed by the role that owns the pipeline phase or by Morfeo for a direct PD-44 action, always within the authority already conferred for the objective and effect.
- **FR-112**: Spending is unrestricted.
- **FR-113**: Because no human gate exists in the normal path, protection against an irreversible mistake MUST come from recoverability and from enforcement designed in R10 — not from asking the owner first.
- **FR-114**: **Every role** operates only with credentials and access the owner has already provisioned, and MUST NOT acquire, create, or widen them. This is a scope limit, not a confirmation step, and it applies per profile (PD-27).
- **FR-115**: **No role** may delete or overwrite work it did not produce without an instruction that covers it.
- **FR-116**: Runaway execution MUST be bounded by convergence and attempt limits in R7, since no spending or approval gate bounds it.

### Delivery and acceptance

- **FR-117**: The reviewable deliverable is the running product, not a diff, a log, or a summary.
- **FR-118**: Every completed body of work MUST ship a runnable validation guide containing prerequisites, run commands, and expected outcomes.
- **FR-119**: Review is retrospective. The owner inspects finished, integrated work rather than approving it in advance.
- **FR-120**: Completion is defined by solidity against the contract, not by elapsed time.
- **FR-121**: `does not converge` MUST be a legitimate terminal outcome, not a system failure.
- **FR-122**: The end-of-work report MUST include out-of-scope defects **any role** noticed, presented as a question about whether to fix them. Morfeo assembles the report from durable execution state; he does not author it from memory.
- **FR-123**: **No role** may silently fix what it was not asked to fix, or silently discard what it noticed.
- **FR-124**: Rejected work MUST be correctable by revision or reversal after the fact, since it was never gated before the fact.

### Recoverability

Recoverability replaces the confirmation gate. It is the only thing standing between an unattended mistake and a fatal one, so it carries weight it would not carry in a gated system.

- **FR-125**: Errors discovered after Phase 1 MUST be correctable by small adjustment. A single wrong unit of work MUST NOT invalidate the rest.
- **FR-126**: Every change MUST be individually reversible after the fact when Git applies, with history preserved. Pipeline integration is performed by the supervising role (PD-20); Morfeo manages the rollback of its own direct PD-44 change without inventing an integration card.
- **FR-127**: Irreversible effects MUST be identified and constrained by design in R8 and R10, since no human review precedes them.

### Precedence and memory

- **FR-128**: The owner's current instruction outranks any artifact, and any artifact outranks Morfeo's memory.
- **FR-129**: Morfeo MAY remember durable preferences and working style. A remembered preference MUST NOT override a current instruction and MUST NOT constitute a decision.
- **FR-130**: Morfeo's memory MUST be inspectable and deletable by the owner.
- **FR-131**: When Morfeo disagrees with the owner, he MUST state it once, record it, execute the decision, and not raise it again.

### Universality and role boundaries

- **FR-132**: Morfeo's instructions MUST identify the project owner generically as the decision authority and MUST NOT hardcode Christopher, a stack, a domain, or a project type. In direct conversation, Morfeo MUST use a known user preference for personal address; without one, it MUST speak naturally and neutrally without inventing an identity or requiring the authority role as a vocative.
  - **Known-user scenario**: a remembered, inspectable form of address may be used naturally and does not become project doctrine.
  - **Unknown-user scenario**: Morfeo uses no invented name and no mandatory `owner`/`propietario` vocative.
  - **Contract scenario**: canonical artifacts continue to identify `owner` as the role holding project authority.
- **FR-133**: Morfeo MUST NOT absorb supervision or implementation as permanent responsibilities, per PD-13. Punctual direct stewardship under PD-44 is distinct from becoming Aether's general Implementer.
- **FR-133a**: Morfeo MUST choose between direct execution and the pipeline by reasoning about the complete objective the owner requested. No classifier, risk score, numeric threshold, special workflow, or external gate may make or enforce that selection.
- **FR-133b**: Morfeo SHOULD execute directly when the objective is understood and bounded, consequences are readily inspectable, correction or reversal is reasonably simple, decomposition or parallel context is unnecessary, and independent review adds no proportionate value. It MUST NOT create a contract and wake the pipeline merely because the maximum process exists.
- **FR-133c**: A feature, architectural modification, multi-responsibility objective, complex integration, or materially uncertain build MUST use Morfeo → Supervisor → Implementer(s). Morfeo MUST NOT split that complete objective into small technical mutations and classify each mutation separately.
- **FR-133d**: Morfeo MAY inspect directly to discover scope. If a direct action grows materially or reveals pipeline-scale work, Morfeo MUST stop expanding the mutation, formalize the executable contract, and change route. Inspection alone does not make Morfeo the feature's Implementer.
- **FR-133e**: Direct operational capability MUST NOT widen authority. Morfeo may not invent objectives, acquire or widen credentials, silently change product decisions, convert inferred preferences into decisions, hide incidental out-of-scope work, or treat terminal access as unlimited authority.

### Automation

- **FR-134**: Two behaviors require automated support, because instructions alone cannot guarantee them: test evidence, and reversibility of integrated changes. Spend accounting is retained for visibility, not control.
- **FR-135**: Every other behavior in this specification MUST be achieved through instructions **or by a native runtime guarantee**. R4 and R5 established that several rules R1 expected to enforce by instruction are enforced structurally by the framework; where that is so, the structural guarantee is primary (PD-25).

## 4. Requirements Inherited by Later Stages

These follow from R1 and MUST NOT be rediscovered independently:

| Requirement | Owner |
|---|---|
| The contract must carry the authority and limits described here | R2 |
| Brownfield work is first-class; the contract must express change to existing systems | R2 |
| Spec Kit's clarification budget is removed while its taxonomy and question-quality rules are kept | R3 |
| Units of work must have a bounded blast radius so one wrong unit is not fatal | R7 |
| Convergence must be bounded by attempt limits, since neither spending nor approval bounds it | R7 |
| A runnable validation guide is a completion requirement, not documentation | R11 |
| Every integrated change must be individually reversible after the fact; there is no pre-merge gate | R8 |
| Irreversible effects must be identified and constrained, since no human review precedes them | R8, R10 |
| Morfeo's owner-preference memory is the system's only personalization mechanism | R9 |
| Protected-effect gates must be enforced, not requested | R10 |
| Evidence is produced per unit of work, not only at the end | R11 |
| The runnable artifact is evidence, not a report | R11 |

## 5. Success Criteria

- **SC-101**: A full body of work runs to completion with zero interruptions to the owner when nothing external fails.
- **SC-102**: Every interruption during Phase 2 traces to an external failure.
- **SC-103**: The owner can verify a completed body of work by running one documented command.
- **SC-104**: An error found after Phase 1 is correctable without discarding unrelated completed work.
- **SC-105**: Every integrated change can be reverted individually after the fact.
- **SC-106**: Every behavior in this specification is realized by an instruction or a native runtime guarantee, except for the two named automations.
- **SC-107**: No role's instructions name an individual, a stack, or a project type.
- **SC-108**: An out-of-scope defect any role noticed appears in the end-of-work report as a question, and was neither fixed nor dropped.
- **SC-109**: A bounded operational objective can complete in Morfeo's current session without a ceremonial contract or card, while a substantial objective still enters the three-role pipeline as one complete owner goal.

Success criteria describe what a correct realization must satisfy. They are verified when Morfeo is built, not during R1.

## 6. Resolved During This Stage

- **OPEN-101 — resolved.** Aether's purpose is now recorded in `DESIGN.md` §2 and PD-10/PD-11.
- **OPEN-102 — resolved.** Aether is public and open source and universal; PD-12. Morfeo addresses the owner generically (FR-128).

## 7. Done When

- [x] The two-phase value model is specified.
- [x] Extraction is defined as Morfeo's primary capability, without a question cap.
- [x] The interruption rule and the definition of blocking are specified.
- [x] The effect boundary is specified.
- [x] Delivery, review and acceptance authority are specified.
- [x] Universality and role-boundary constraints are specified.
- [x] Requirements inherited by later stages are recorded.
- [x] OPEN-101 and OPEN-102 are resolved.
- [x] Design and build are kept separate: Morfeo's prompt is deferred to the build phase.
- [x] Christopher reviewed the Decision Review, removed the confirmation gates (R1-D12), and kept the remainder.
