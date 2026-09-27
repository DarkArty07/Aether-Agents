# Expected behavior of Aether agents

This guide explains what the **source instructions in this revision** ask Aether's
agents to do, when that expectation applies, and where it is written. It is derived
from the owning specifications, SOULs and canonical skills; it creates no requirement
or permission of its own. It is not a test report, a new capability registry or a
promise that a model always complies.

Keep three claims separate: **documented instruction**, **installed instruction** and
**observed conduct**. The website links to its source revision; an installed release may
carry different wording. The [capability reference](../reference/capabilities.md) describes
implementation status, not obedience. The #541 methodology and `aether-plan` amendments
are source maintenance with diff/reference inspection only, not new runtime qualification.

## How to read an expectation

Each entry identifies its trigger and role, expected action, limits, instruction sources
and observable signs. A conditional obligation is not optional when its conditions hold;
an optional integration does not make its applicable instructions optional. Repetition in
prompts is not a measured strength or a guarantee. Historical evidence must retain its
producer, revision and limits; no entry receives an invented compliance percentage.

## Adopt a project without copying another one

- **When / who:** Morfeo arrives at a new or existing project or reconciles its guidance.
- **Expected:** inspect reality and existing instructions, confirm missing principles, then
  establish a concise root `AGENTS.md` and project-relative operating map. Preserve other
  harness conventions. Product specs/docs/code stay outside `.aether`; Aether-specific
  coordination and auxiliaries use their own conventions.
- **Limits:** no invented product intent, automatic Git initialization, empty folder tree,
  migration, duplicated SOUL or reliance on private Hermes memory for shared obligations.
- **Sources:** [R2 §3.1](../../specs/r2-contract-and-handoff/spec.md#31-objective-plans-route-and-continuity-not-contract-authority),
  [R9 §3.1](../../specs/r9-state-and-recovery/spec.md#31-portable-methodology-and-exploratory-observations-541),
  [Morfeo SOUL §04](../../src/aether_agents/resources/profiles/morfeo/SOUL.md#04-working-method),
  [project-adoption procedure](../../src/aether_agents/resources/skills/objective-contract-design/SKILL.md#project-adoption-and-predesign).
- **Observable signs:** the instructions describe the actual project, point to accessible
  sources and distinguish unknown decisions from delegated local freedom.

## Orient with project knowledge, then verify sources

- **When / who:** the first substantive request to understand a bound project's
  architecture, dependencies, implementation or documented decisions; each role within
  its assigned work.
- **Expected:** discover `project-knowledge` and consult an available graph through
  `project_knowledge` before repository content searches and answer-bearing source reads.
  Check identity, revision, coverage and warnings; inspect current sources afterwards.
- **Limits:** not a ritual before every read, greeting, trivial question or directly supplied
  source/URL. An unbound project, missing index/component or unborn repository calls for
  honest ordinary source inspection, not installing a dependency or inventing a graph.
  A graph is navigation, never authority or behavioral proof.
- **Sources:** [Morfeo SOUL §08](../../src/aether_agents/resources/profiles/morfeo/SOUL.md#08-knowledge-memory-and-learning),
  [project-knowledge triggers and prerequisites](../../src/aether_agents/resources/skills/project-knowledge/SKILL.md#when-to-use),
  [knowledge guide](project-knowledge.md).
- **Observable signs:** correctly bound graph results followed by source inspection, or a
  disclosed availability limitation and an ordinary source-based answer. A successful
  status call with no available index is not successful graph-assisted exploration.

## Keep exploration distinct from a commitment

- **When / who:** Morfeo needs continuity for an unresolved predesign or research topic.
- **Expected:** reuse one `.aether/observations/<topic>.md`; distinguish concern, sourced
  facts, hypotheses, questions, decisions and meaningful continuity. On resolution,
  transfer enduring decisions/evidence before retiring an eligible owned note.
- **Limits:** no note for every question, numbered registry or mandatory predesign phase.
  A disposition such as `investigating` is not a running worker. An observation grants
  no execution authority and is unrelated to the runtime `aether observe` projection.
  Research within an accepted specification stays in that specification's `research.md`.
- **Sources:** [R9 §3.1](../../specs/r9-state-and-recovery/spec.md#31-portable-methodology-and-exploratory-observations-541),
  [project-adoption and predesign procedure](../../src/aether_agents/resources/skills/objective-contract-design/SKILL.md#project-adoption-and-predesign).
- **Observable signs:** unresolved ideas remain labeled, and a transferred decision can be
  found in its actual owning artifact rather than only in a private note.

## Plan explicitly without silently starting execution

- **When / who:** the owner invokes `/aether-plan` or asks Morfeo for planning only.
- **Expected:** resolve the project and objective, reuse relevant exploratory context,
  and create/update one `.aether/plans/<objective-slug>.md` with destination, route,
  continuity, closure evidence and stop/replan conditions. Stop at the plan.
- **Limits:** generic `/plan` is not an Aether alias. No code implementation, cards,
  workers or publication follows merely from planning. Contract forecasts are not quotas;
  observations do not become approved scope. Native dispatch/adoption of the renamed
  resource must not be inferred from the source file alone.
- **Sources:** [aether-plan](../../src/aether_agents/resources/skills/plan/SKILL.md),
  [Objective Plans](objective-plans.md), [R2 §3.1](../../specs/r2-contract-and-handoff/spec.md#31-objective-plans-route-and-continuity-not-contract-authority).
- **Observable signs:** a project-local plan with preserved history, and no planning-only
  request misreported as permission to execute.

## Preserve objective continuity without requiring a command

- **When / who:** authorized work needs a meaningful route or spans sessions/contracts;
  Morfeo conducts the objective.
- **Expected:** maintain the same plan after material decisions, results, failures and
  handoff; revalidate changeable facts on resumption. Explain the unmet obligation,
  evidence for continuing and stopping condition before a material successor step.
- **Limits:** no plan ceremony for routine bounded work, no global newest-plan selection,
  and no retry-budget reset because a session or contract changed. `todo` is local segment
  tracking, not a replacement for durable continuity or board state.
- **Sources:** [planning and continuity procedure](../../src/aether_agents/resources/skills/objective-contract-design/SKILL.md#objective-planning-and-continuity),
  [Objective Plans](objective-plans.md#continue-close-or-stop).
- **Observable signs:** settled decisions and failed attempts survive resumption, while
  stale notes are not presented as fresh verification.

## Use a proportionate route and preserve scope

- **When / who:** Morfeo selects how to conduct the owner's whole objective.
- **Expected:** act directly on understood, bounded, inspectable and reversible work;
  use Supervisor/Implementer when meaningful decomposition, uncertainty or review warrants
  it. Resolve missing material intent before delegation and preserve accepted alternatives,
  exclusions and local implementation freedom.
- **Limits:** no pipeline by file/time quota, no ceremonial card for direct work, and no
  splitting a substantial objective into small edits to avoid its appropriate route.
- **Sources:** [Morfeo SOUL §03](../../src/aether_agents/resources/profiles/morfeo/SOUL.md#03-decision-criteria),
  [contract design](../../src/aether_agents/resources/skills/objective-contract-design/SKILL.md#contract-boundary-and-scope-fidelity).
- **Observable signs:** the chosen route has an objective-specific reason and introduces
  neither unrequested outcomes nor needless approval steps.

## Delegate, implement and review traceable work

- **When / who:** Morfeo hands a finalized contract to Supervisor; Supervisor decomposes
  and reviews; Implementer executes its bounded unit.
- **Expected:** use the exact project/contract binding, short handoff envelope, traceable
  units and actual acceptance evidence. Preserve independent review and the native task
  lifecycle. Update guidance invalidated by an authorized change.
- **Limits:** a card is not a contract; a root decomposition being done is not product
  completion. An observation, tool capability or worker summary cannot invent authority.
- **Sources:** [Supervisor SOUL](../../src/aether_agents/resources/profiles/supervisor/SOUL.md),
  [Implementer SOUL](../../src/aether_agents/resources/profiles/implementer/SOUL.md),
  [supervisor-decomposition](../../src/aether_agents/resources/skills/supervisor-decomposition/SKILL.md),
  [implementation-evidence](../../src/aether_agents/resources/skills/implementation-evidence/SKILL.md).
- **Observable signs:** each delivery can be traced to accepted obligations and attributed
  evidence, with gaps returned rather than hidden by a terminal board state.

## Put memory and learning in their owning destinations

- **When / who:** a durable preference, reusable procedure or useful project experience
  is learned; each role within its memory authority.
- **Expected:** owner preferences go to personal memory, decisions to canonical artifacts,
  role/project experiences to `work_memory`, and procedures to skills under their governance.
  Read original notes and check current applicability before reuse; confirm a save receipt.
- **Limits:** no task diary in personal memory, private-note publication, invented evidence
  or automatic promotion of a learned skill into a rule. An unavailable memory component
  must be disclosed; writing a file elsewhere is not a successful `work_memory` save.
- **Sources:** [Morfeo SOUL §08](../../src/aether_agents/resources/profiles/morfeo/SOUL.md#08-knowledge-memory-and-learning),
  [work-memory](../../src/aether_agents/resources/skills/work-memory/SKILL.md),
  [skill governance](../../src/aether_agents/resources/skills/canonical-skill-governance/SKILL.md).
- **Observable signs:** the destination and receipt match the claim; no remembered fact
  overrides current instruction or verified sources.

## Read progress without confusing it with acceptance

- **When / who:** Morfeo reports pipeline progress or receives a completed result.
- **Expected:** use durable board/observation evidence with exact identity and coverage;
  use `contract-result-review` before accepting the owner's objective. Compare the exact
  final artifact with current intent and every material criterion.
- **Limits:** observation is a navigation/projection surface, not independent approval.
  Green checks or a Supervisor summary alone do not establish acceptance. Attribute reused
  evidence; do not claim unexecuted reruns or percentages.
- **Sources:** [result reception](../../src/aether_agents/resources/skills/contract-result-review/SKILL.md),
  [Morfeo SOUL §06](../../src/aether_agents/resources/profiles/morfeo/SOUL.md#06-evidence-acceptance-and-closeout),
  [observation guide](observation.md). This repository's specific compact-query procedure
  is a [Project Canonical Skill](../../.aether/skills/aether-observe/SKILL.md), not a file
  every future project must copy.
- **Observable signs:** reported status and acceptance have separate evidence and limits.

## Close with accurate guidance and scoped cleanup

- **When / who:** each role manages its own auxiliaries; Morfeo owns direct-route closure
  and Supervisor owns pipeline closure.
- **Expected:** keep discretionary project scratch under `.aether/tmp/<work-scope>/`,
  preserve deliverables and necessary evidence, then retire only verified owned residue.
  Reconcile affected project guidance and applicable authorized Git/issue steps.
- **Limits:** no blanket `.aether` or shared-temp purge, removal by age alone, unrelated
  cleanup, unauthorized push/merge or claim that a local edit is fully published. Preserve
  tool-managed/external locations. Release impact, action and channel are separate.
- **Sources:** [storage and closeout procedure](../../src/aether_agents/resources/skills/git-github-closeout/SKILL.md#workspace-and-temporary-storage-hygiene),
  [release procedure](../../src/aether_agents/resources/skills/semver-release/SKILL.md),
  [R9 §3.1](../../specs/r9-state-and-recovery/spec.md#31-portable-methodology-and-exploratory-observations-541).
- **Observable signs:** retained and retired resources have clear ownership and reasons;
  final claims name what was actually verified and what remains.

## Maintain this catalogue without creating another authority

When changing a meaningful expectation in source SOULs or skills, reconcile the affected
entry in the same authorized change or explain non-applicability. Link to stable headings
and the owning requirements instead of copying full procedures or scoring prompt emphasis.
Keep proposals separate until accepted in their owning artifacts. Ordinary-use evidence
belongs in existing evidence/issue locations with its producer and revision; this guide
neither requires a new agent campaign nor records a global behavioral PASS.
