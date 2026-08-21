# R12 Specification: Models, Routing, and Economics

**Roadmap ID**: R12
**Stage status**: done
**Accepted**: 2026-08-17 — Christopher accepted the R4–R13 Decision Review
**Amended**: 2026-08-18 — Morfeo's existing tier also serves direct stewardship
**Decision authority**: Christopher
**Autonomous design delegate for this stage**: Morfeo
**Future role owner**: Morfeo
**Depends on**: R1, R7, R10, R11, `DESIGN.md`
**May affect**: R13
**Parent roadmap**: `../../ROADMAP.md`
**Hermes evidence**: version 0.20.1, revision `411903b6fa258f81afcc3869eb615f6218e1776a`, source `home/.venv-hermes/src/hermes-agent`

## 1. Purpose

R12 decides how reasoning capability is allocated across roles and units, and what governs the trade between cost and quality.

It does **not** name models. Naming them is a build decision that requires two things this stage does not have: the catalogue the owner's provider actually exposes, and comparative evidence from a real run. R12 specifies the allocation scheme, the override mechanism, and the rule that decides when a cheaper configuration may be adopted.

R12 does not authorize a run (R13).

## 2. Capability Is Allocated Per Profile

The runtime resolves each worker's model from its own profile when the dispatcher spawns it. Tiering is therefore a property of the role, expressed once, not a routing decision made per unit.

| Role | Tier | Why |
|---|---|---|
| Morfeo | Frontier | Extraction quality determines everything downstream; the same profile also performs bounded direct stewardship under PD-44 |
| Supervisor | Capable | Decomposition, analysis, review, and contract-derived decisions are judgement work on a written contract |
| Implementer | Inexpensive | Executes a unit that already carries its goal, its context, and its decisions |

- **FR-1201**: Model tiering MUST be expressed per profile.
- **FR-1202**: Morfeo MUST run on the strongest available tier. Extraction is the one phase with no second chance (R1 §2), and PD-44 direct stewardship uses the same established profile tier.
- **FR-1202a**: Selecting direct action versus pipeline MUST NOT invoke a special model router, model switch, classifier slot, or auxiliary model. It is Morfeo's reasoning responsibility inside the existing profile.
- **FR-1203**: The implementer tier is where nearly all tokens are spent, and is therefore where cost is governed. Reducing cost anywhere else is optimising the wrong term.
- **FR-1204**: A cheaper implementer tier MUST still satisfy the project constitution, which is scored identically regardless of which model produced the work (R11-FR-1132).
- **FR-1205**: Aether MUST NOT express capability differences by adding roles or profiles (PD-30, PD-33).
- **FR-1205a**: Enabling a messaging channel is a **per-profile** configuration decision, not a system-wide one. Where one is enabled it attaches to Morfeo's profile alone (R6-FR-616); no other profile acquires it as a side effect of how tiers are assigned.

## 3. Per-Unit Override

- **FR-1206**: A per-unit model override MUST be available for quality-sensitive work, and MUST be the mechanism of first resort when a unit needs more capability.
- **FR-1207**: A reconciliation unit MAY carry a stronger model, since adjudicating two intents is harder than executing one (PD-31).
- **FR-1208**: An override MUST be recorded on the unit, so evidence can attribute an outcome to the capability that produced it (R11-FR-1121).
- **FR-1209**: Repeated overrides on the same class of unit MUST be read as evidence that the profile tier is wrong, and MUST trigger a re-tiering decision rather than becoming standing practice.

## 4. Auxiliary Slots

The runtime routes several internal functions to separately configured auxiliary models. Aether must decide each deliberately, because an unconfigured slot silently falls back to the main model and an unwanted slot silently performs work Aether assigned to a role.

| Slot | Aether's disposition |
|---|---|
| Triage decomposer | **Unused.** Automatic decomposition is disabled (R7-FR-706); the supervisor decomposes |
| Triage specifier | **Unused.** Automatic specification rewriting is disabled (R7-FR-707) |
| Convergence judge | **Used**, wherever a unit runs in goal mode (R7-FR-729) |
| Other auxiliary functions | Unselected until a requirement needs one |

- **FR-1210**: An auxiliary slot Aether does not use MUST be left unused **and** the behaviour that would invoke it MUST be disabled. Leaving the behaviour enabled while the slot is unconfigured produces a silent fallback to the main model.
- **FR-1211**: The convergence judge's tier MUST be chosen for judgement quality, not cost. A weak judge either ends work early or never ends it, and both failures are expensive in the term that matters.
- **FR-1212**: Adopting any further auxiliary function MUST record why, so a later stage does not silently reverse it (R4-FR-420).

## 5. Economics

- **FR-1213**: Spending is unrestricted (R1-FR-112). Cost is a design consideration, not a gate.
- **FR-1214**: Because no spending gate bounds a runaway loop, the attempt, turn, and wall-clock budgets of R7 are the only bound, and MUST be set before any unattended run (R1-FR-116).
- **FR-1215**: Cost MUST be observable per unit and per attempt, for visibility rather than control (R1-FR-134).
- **FR-1215a**: **The board records no cost.** Verified by inspecting its schema: neither the unit table nor the attempt table carries any column for cost, tokens, usage, or spend. Duration is available per attempt — start, end, wall-clock limit, and last liveness signal — but cost is not.
- **FR-1215b**: Per-unit cost MUST therefore be obtained by correlating a unit to its worker session through the session identifier the unit carries, and reading the runtime's own usage accounting there. Whoever builds this MUST treat it as an integration to write, not a field to read.
- **FR-1215c**: Aether MUST NOT add a cost column to the board. That would be a parallel record of execution, which R9-FR-902 forbids.
- **FR-1216**: An expensive outcome MUST be attributable to a unit, so the next tiering decision is made against evidence rather than an impression.

## 6. Selection Rules

- **FR-1217**: A tier assignment MUST NOT be selected by preference or reputation. It requires a controlled comparison holding the contract constant and varying one thing (R11-FR-1130).
- **FR-1218**: Cost MUST NOT substitute for demonstrated quality (R11-FR-1131).
- **FR-1219**: Until such evidence exists, tier assignments are **provisional** and MUST be labelled as such wherever they are recorded.
- **FR-1220**: Model names MUST be bound in profile configuration at build time, never in a prompt, a card body, or a contract artifact. Binding them in content would make a model change a content change across every project.
- **FR-1221**: The design MUST remain provider-agnostic. A provider or router is a configuration fact, and no requirement in this repository may depend on a specific vendor's model existing.

## 7. Evidence

From direct inspection at the recorded revision:

- Each profile carries its own model configuration, and the dispatcher injects the profile-scoped home when spawning, so a worker resolves its own tier.
- A per-unit model and provider override exists and takes effect on the next dispatch.
- Auxiliary functions resolve through separately configured slots and fall back to the main model when a slot is unset.
- Automatic decomposition is enabled by default and re-read by the dispatcher on every tick, so disabling it takes effect without a restart.

Observed on the owner's live profile: the runtime is pointed at a locally hosted router rather than a public provider, which is exactly why FR-1221 is stated as a requirement rather than assumed.

Not measured: any comparison between tiers. No run has occurred, so every tier assignment in §2 is provisional under FR-1219.

## 8. Requirements Inherited by Later Stages

| Requirement | Owner |
|---|---|
| Tier assignments are provisional until the first authorized run produces comparative evidence | R13 |
| Budgets must be set before the first unattended run | R13 |

## 9. Success Criteria

- **SC-1201**: Every role's capability is set once, on its own profile.
- **SC-1202**: A unit needing more capability receives it by override, not by a new role.
- **SC-1203**: No auxiliary slot performs work Aether assigned to a role.
- **SC-1204**: No unconfigured slot silently falls back to the main model while its behaviour remains enabled.
- **SC-1205**: Every tier assignment is either supported by comparative evidence or labelled provisional.
- **SC-1206**: No model name appears in a prompt, a card body, or a contract artifact.
- **SC-1207**: No requirement depends on a specific vendor's model existing.

## 10. Done When

- [x] Capability allocation is defined per profile, with the reasoning for each tier.
- [x] The per-unit override is made the first resort for capability, not a new role.
- [x] Every auxiliary slot is dispositioned, including the silent-fallback trap.
- [x] The economics of an ungated system are tied to R7's budgets.
- [x] Selection rules forbid preference-based choice.
- [x] Provider-agnosticism is required rather than assumed.
- [x] Christopher has reviewed the stage (R4–R13 Decision Review, 2026-08-17).
- [ ] Tier assignments are confirmed or revised against comparative evidence.
