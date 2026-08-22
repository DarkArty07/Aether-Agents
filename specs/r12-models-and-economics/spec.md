# R12 Specification: Models, Routing, and Economics

**Roadmap ID**: R12
**Stage status**: done — reconciled 2026-08-21 for the A1 public, provider-independent product baseline
**Accepted**: 2026-08-17 — Christopher accepted the R4–R13 Decision Review
**Amended**: 2026-08-18 — Morfeo's existing tier also serves direct stewardship
**Amended**: 2026-08-21 — private bindings removed from portable product truth; descending role allocation retained
**Decision authority**: Christopher
**Autonomous design delegate for this stage**: Morfeo
**Future role owner**: Morfeo
**Depends on**: R1, R7, R10, R11, `DESIGN.md`
**May affect**: R13
**Parent roadmap**: `../../ROADMAP.md`
**Selected Hermes baseline**: `NousResearch/hermes-agent` release `v2026.8.18`, annotated tag object `9f13bbbf8423427e159c78066356ca0e27ca6b74`, commit `e624e9fde561e1add9388384012b295fde669ade`, distribution version `0.20.4`

## 1. Purpose

R12 records how reasoning capability is allocated across roles and units, how users supply model/provider bindings, and what governs the trade between cost, throughput, and quality.

Model and provider identifiers are user-owned operational configuration. They are not portable product requirements, release defaults, prompt content, or evidence about every installation. The product preserves descending role allocation and unchanged quality gates even when a user selects the same model for several roles or later replaces a binding.

R12 does not authorize a run (R13).

## 2. Capability Is Allocated Per Profile

The runtime resolves each worker's model from its own profile when the dispatcher spawns it. Tiering is therefore a property of the role, expressed once, not a routing decision made per unit.

| Role | Product allocation | Binding ownership | Why |
|---|---|---|---|
| Morfeo | Highest capability available within the user's accepted set | User selects during setup | Extraction quality determines everything downstream; the same profile also performs bounded direct stewardship under PD-44 |
| Supervisor | Strong independent judgement | User selects during setup | Decomposition, analysis, review, integration, and contract-derived decisions are judgement work on a written contract |
| Implementer | Lowest cost that still passes every required gate | User selects during setup | Executes a bounded unit that already carries its goal, context, and decisions; lower unit cost makes parallel throughput economical |

The descending order is deliberate: capability and unit cost decrease as the decision space narrows. It does not create descending quality criteria. The contract, constitution, tests, evidence obligations, and Supervisor review remain unchanged across all three bindings.

- **FR-1201**: Model tiering MUST be expressed per profile.
- **FR-1202**: Morfeo MUST receive the highest-capability binding available within the user's accepted provider/model set. Extraction is the one phase with no second chance (R1 §2), and PD-44 direct stewardship uses the same profile tier.
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

- **FR-1213**: Aether imposes no hidden provider or model purchase. Credentials, account use, and spend remain user-owned inputs; a live release qualification run requires the explicit credential and spending authority required by PD-64 and A1.
- **FR-1213a**: Aether's throughput strategy is to reserve stronger, more expensive capability for upstream decisions whose errors propagate, then parallelize bounded implementation on the lower-cost Implementer tier. Greater speed MUST NOT be obtained by weakening review, tests, acceptance criteria, or evidence.
- **FR-1213b**: One Supervisor coordinates a contract. Increasing concurrency means more independent Implementer instances, not duplicate Supervisors competing over decomposition or integration (PD-47).
- **FR-1214**: Because no spending gate bounds a runaway loop, the attempt, turn, and wall-clock budgets of R7 are the only bound, and MUST be set before any unattended run (R1-FR-116).
- **FR-1215**: Cost MUST be observable per unit and per attempt, for visibility rather than control (R1-FR-134).
- **FR-1215a**: **The board records no cost.** Verified by inspecting its schema: neither the unit table nor the attempt table carries any column for cost, tokens, usage, or spend. Duration is available per attempt — start, end, wall-clock limit, and last liveness signal — but cost is not.
- **FR-1215b**: Per-unit cost MUST therefore be obtained by correlating a unit to its worker session through the session identifier the unit carries, and reading the runtime's own usage accounting there. Whoever builds this MUST treat it as an integration to write, not a field to read.
- **FR-1215c**: Aether MUST NOT add a cost column to the board. That would be a parallel record of execution, which R9-FR-902 forbids.
- **FR-1216**: An expensive outcome MUST be attributable to a unit, so the next tiering decision is made against evidence rather than an impression.

## 6. Selection Rules

- **FR-1217**: The descending allocation is the product baseline. Any concrete binding is installation-local and MUST NOT be described as experimentally optimal without a controlled comparison holding the contract constant and varying one model at one role or gate (R11-FR-1130).
- **FR-1218**: Cost MUST NOT substitute for demonstrated quality (R11-FR-1131). A cheaper tier is acceptable only while it satisfies the same constitution, tests, acceptance criteria, and review requirements.
- **FR-1219**: Future re-tiering and claims that one binding is superior MUST be supported by controlled evidence. Until then, setup preserves the user's explicit choices without promoting them to product truth.
- **FR-1220**: Model and provider identifiers MUST be bound only in installation-local profile configuration or an explicit per-unit override. They MUST NOT appear in a product prompt, public template/default, card body, project contract, or release claim. Binding them in work content would make a model change a content change across every project.
- **FR-1221**: The design MUST remain provider-agnostic. A provider or router is a configuration fact, and no requirement in this repository may depend on a specific vendor's model existing.
- **FR-1222**: Guided and declarative setup MUST use the same parser, desired-state model, validation, and merge rules. Setup input MUST carry identifiers only, never API keys, tokens, or credential-file contents.
- **FR-1223**: A user MAY choose the same supported binding for two or all three roles. The descending allocation is an optimization objective, not a fabricated capability distinction when the accepted set does not provide three suitable tiers.

## 7. Evidence

From direct inspection of the selected public baseline:

- `website/docs/user-guide/profiles.md:5-17` at commit `e624e9f…` documents separate profile homes with independent configuration and credentials; `profiles.md:129-153` explicitly states that profiles are not filesystem sandboxes.
- `hermes_cli/provider_catalog.py:1-33,83-140` at that commit derives the provider universe from the same canonical/plugin-backed registry used by the model picker rather than one Aether-owned provider list.
- `hermes_cli/kanban_db.py:3197-3246` exposes per-task model/provider overrides, with provider requiring a model override.
- `hermes_cli/config_defaults.py:2513-2586` keeps automatic decomposition and Kanban concurrency as explicit configuration, so Aether must set and validate its chosen behavior rather than infer it from a private runtime.

Not measured: a controlled comparison between concrete public bindings. No optimality or vendor-wide support claim is made without that experiment.

## 8. Requirements Inherited by Later Stages

| Requirement | Owner |
|---|---|
| Setup preserves explicit user bindings; claims of optimality or future re-tiering require comparative evidence | R13 |
| Budgets must be set before the first unattended run | R13 |

## 9. Success Criteria

- **SC-1201**: Every role's capability is set once, on its own profile.
- **SC-1202**: A unit needing more capability receives it by override, not by a new role.
- **SC-1203**: No auxiliary slot performs work Aether assigned to a role.
- **SC-1204**: No unconfigured slot silently falls back to the main model while its behaviour remains enabled.
- **SC-1205**: Concrete bindings remain user-owned local configuration; any claim of optimality or future re-tiering is supported by controlled comparative evidence.
- **SC-1206**: No model or provider identifier appears in a product prompt, public default/template, card body, project contract, or release claim.
- **SC-1207**: No requirement depends on a specific vendor's model existing.
- **SC-1208**: A clean setup can select supported bindings without exposing credentials and without private owner infrastructure.

## 10. Done When

- [x] Capability allocation is defined per profile, with the reasoning for each tier.
- [x] The per-unit override is made the first resort for capability, not a new role.
- [x] Every auxiliary slot is dispositioned, including the silent-fallback trap.
- [x] The economics of an ungated system are tied to R7's budgets.
- [x] Selection rules distinguish the descending product allocation from user-owned bindings and claims that require controlled evidence.
- [x] Provider-agnosticism is required rather than assumed.
- [x] Christopher has reviewed the stage (R4–R13 Decision Review, 2026-08-17).
- [ ] Concrete public bindings are compared only when an owner-authorized evaluation is preregistered.
