---
name: objective-contract-design
description: Use when Morfeo adopts projects or designs objectives.
version: 0.2.2
author: Morfeo (Aether role), Hermes Agent
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [contracts, design, requirements, verification]
    related_skills: []
---

# Objective Contract Design

Establish project-local methodology and turn approved intent into discoverable
requirements, material technical design and observable acceptance before a pipeline
handoff. This is Morfeo's procedure, not a
new source of requirements or a competing artifact format. It cannot grant authority.
The owner and canonical artifacts govern; Supervisor owns independent receipt review
and decomposition, and Implementer retains reversible unit-local judgement.

## When to Use

- Use the project-adoption and predesign entry when arriving at a new or existing project, reconciling its operating guidance, or preserving a useful exploratory topic. This does not require a contract.
- Use the objective-planning entry below when work needs a route or cross-session continuity, including a planning-only request. It is not required for a simple question or routine bounded adjustment.
- Use the full contract procedure when Morfeo designs, checks or supersedes a pipeline Objective Contract.
- Use for resolving a contract defect returned by Supervisor at its owning artifact.
- Do not require a contract or this full procedure for bounded direct work.
- Do not use to decompose tasks, implement a product, or certify your own independent review.
- Other roles may inspect these criteria as evidence; this procedure does not assign
  Morfeo's design or contract-authoring phase to them.

## Prerequisites

Read the owner instruction, constitution, relevant design/specifications and root
`AGENTS.md`. For initial adoption, inspect what exists: missing principles/guidance
are onboarding questions, not permission to invent them or a prerequisite to reading
the folder. Discover relevant Project Canonical Skills through their named
project-relative `.aether/skills/<name>/SKILL.md` paths and Aether Canonical Skills
through native discovery. Preserve brownfield guidance and confirm the actual Project.
Resolve testing standard, authority and convergence bounds explicitly from the owner
or their delegated project policy; a skill does not supply universal defaults.

## Objective planning and continuity

Use the project-adoption and predesign entry below when guidance or exploratory
context needs attention; do not repeat adoption for every objective. Explicit
`/aether-plan` invokes the focused `aether-plan` skill, which uses this same method
and stops at planning. Generic `/plan` is not an Aether entry.

This entry does not require a contract or authorize execution. Honor a planning-only
request. For authorized work, missing material intent is resolved before execution;
do not add routine confirmation gates to an already delegated route.

1. Resolve the project and objective explicitly, not by global recency, display name
   or an unrelated cwd. Reuse the exact plan when continuing. Do not initialize a
   project merely to save a plan; surface an ambiguous binding instead.
2. Maintain one `.aether/plans/<objective-slug>.md` in that project. Keep it local and
   ignored by default, subject to the project's accepted privacy/versioning policy;
   do not silently publish it, rewrite ignore rules or migrate historical plans.
   This Aether convention takes precedence over a generic planning skill's default
   location. Reuse an appropriate existing objective plan rather than duplicating it.
3. Use the following compact outline, omitting empty ceremony:

   - **Stable destination:** requested outcome, scope/exclusions, preservation and
     closure evidence; reference the canonical owners of accepted obligations.
   - **Current route:** independently useful milestones, necessary dependencies,
     related contracts and current approach. Do not prescribe every future task.
   - **Operational continuity:** current disposition, exact project/plan identity,
     last material update, verified results with producer/revision, failed approaches
     and reasons, untried ideas marked unverified, questions, and next step or stop.

   This is not a new source of authority and does not replace technical `plan.md`,
   finalized contracts or native board state. A worker's executable obligations must
   not depend on private notes. `todo` tracks the current segment, not the whole scope.
4. Update at material decisions, milestones, failures and session handoff, not every
   tool call and not only when the owner asks to save. Reread before editing to avoid
   overwriting concurrent changes. On resumption, reconcile changeable facts against
   current artifacts/Git/board evidence without repeating resolved investigation.
5. Before a successor handoff, material prerequisite, repeated same-cause failure or
   change of approach, identify the unmet obligation, new evidence for continuing,
   and what would require stopping or replanning. Classify the next step as an agreed
   milestone, bounded correction, invalidated premise or separate objective. A new
   session, card or contract does not reset prior failures or convergence bounds.
   Preserve an incomplete result when continuation is unjustified; do not waive
   acceptance, absorb unrelated work or require the owner to supervise every command.

## Procedure

### Project adoption and predesign

This entry is independent of pipeline extraction. Its output is sufficient local
guidance or exploratory context, not a mandatory contract, folder tree or task board.

1. **Inspect before prescribing.** Resolve the actual folder/project, current sources,
   constitution and existing harness instructions. Distinguish an empty folder,
   brownfield project and continuation. Do not initialize Git, register a Project or
   start workers merely to make a documentation step possible. Confirm missing
   principles with the owner; tool availability is not product intent.
2. **Establish a concise operating map.** After constitution confirmation, create or
   reconcile root `AGENTS.md` from what exists: governing documents, code/spec/doc
   locations, applicable procedures and actual setup/run/test/distribution guidance.
   State unknowns rather than inventing commands or a testing standard. Distribution
   guidance does not authorize publication. Preserve other harnesses' instructions;
   use project-relative references, not copies of another project's history, a SOUL,
   or every installed skill. Another file-capable harness must be able to locate the
   necessary obligations without private memory or native Aether tools. State any
   genuine capability requirement instead of inventing an equivalent.
3. **Separate product artifacts from methodology.** Product code, tests, specs, technical
   plans, research and deliverables stay outside `.aether`, in the project's established
   structure (`specs/` and `docs/` are examples, not mandatory retroactive migrations).
   Use `.aether/project.toml`, `objective-contracts/` and `skills/` for their existing
   portable roles; `drafts/`, `plans/` and `observations/` for their local purposes;
   `.aether/tmp/<work-scope>/` for discretionary scratch work. Create only needed
   artifacts. Check the existing privacy/versioning policy: `.aether` is neither all
   public nor all disposable. Never force-add local continuity or rewrite identity.
   Tool-managed runtime, worktrees, caches and externally required research locations
   retain their own rules; no implicit migration or broad cleanup is authorized.
4. **Preserve useful exploration without committing work.** Use one local, ignored
   `.aether/observations/<topic>.md` per unresolved topic that warrants continuity.
   Reuse it, with a descriptive name; no registry, numbered IDs or empty template is
   needed. Keep the originating concern, sourced facts, hypotheses, questions,
   decisions and last meaningful update/next step distinguishable. `noted`,
   `investigating` and `ready` are optional descriptive dispositions, not workflow
   states or proof that an agent is running. Mark unsupported claims unverified.
   Do not create a note for every simple question or read all observations by default.
5. **Transfer, then retire.** An exploration may end with an answer, an accepted decision
   recorded in its owning artifact, or a justified objective. Hypotheses never become
   requirements by being copied into a plan. Research inside an accepted specification
   remains in its `research.md`; memory destinations retain their existing ownership.
   Before removing a resolved observation, preserve enduring decisions and necessary
   evidence in their proper destinations and confirm no consumer still needs the note.
   Remove only the eligible owned note; do not erase source evidence or sweep the folder.

### Pipeline extraction

The following full extraction procedure applies to pipeline handoffs only. If an
Objective Plan exists, locate the contract's milestone there before proceeding;
one handoff still uses exactly one finalized Objective Contract.

### Contract boundary and scope fidelity

Conduct the whole objective, but make each contract an independently acceptable outcome.
Use separate contracts when dependencies, effect authority or useful delivery boundaries
justify them; do not bundle an entire release program merely because its stages are related.
Source repair, artifact preparation and live adoption are possible boundaries, not mandatory
phases for every bug. Keep an indivisible change together; neither splitting nor consolidation
is justified by a file, card or contract quota.

The owner requests another Implementer harness when a contract is started; without that
explicit request every role runs on Hermes and Morfeo neither proposes, asks about nor
selects another harness.

For every mandatory deliverable/check, identify the accepted outcome, preservation obligation
or applicable project gate that requires it. Preserve alternatives, quantities, destinations,
conditions and exclusions when deriving acceptance. An example, reviewer preference or a
passing test cannot create authority. Remove unsupported additions before finalizing; return
an accepted material conflict to its owner instead of silently weakening it.

### Extraction and handoff

1. **Inspect before prescribing.** With `read_file`, `search_files` and `terminal`,
   locate the actual implementation, public interfaces, tests, dependencies and
   repository state. Record stable project-relative paths/symbols and the inspected
   revision. Separate observed behavior, intended behavior and unqualified assumptions.
   Finish when the proposed change can be located in the real project.
   Keep each further inspection tied to an unanswered material question and the
   decision it can change. Reuse already verified references at the same revision;
   do not repeatedly rediscover them or investigate every future unit's local details.
2. **Extract intent.** Write the problem, user-visible outcome, representative user
   stories, exclusions and preservation boundary in their existing canonical homes.
   Identify each material question; resolve it with the owner when no delegated answer
   exists. Persist each accepted clarification immediately, not only in conversation.
   Finish when the next role need not reconstruct intent from a chat.
3. **Make requirements observable.** Give obligations stable references and describe
   relevant normal, error and boundary scenarios. Distinguish product acceptance from
   method, authority and operational closeout. Replace vague adjectives with the
   project's agreed observable criterion, not an invented numeric target.
4. **Resolve material feasibility.** Inspect or perform an authorized bounded probe
   for a central uncertainty such as whether a required framework interface exists.
   Record what the probe proves and what it does not. If feasibility remains unknown,
   do not label the build ready: resolve an explicitly bounded research objective with
   its own acceptance or return the missing decision. Never disguise research as a
   trivial Implementer detail or acquire access to make a design appear feasible.
5. **Design only the applicable material boundaries.** Use the technical `plan.md`
   and existing canonical owners to specify component responsibilities and data/control
   flow. Specify shared input/output/error interfaces, data lifecycle, states,
   invariants, concurrency and recovery where the objective needs them. Name selected
   decisions, evidence-backed assumptions, rejected alternatives and change impact.
   Use diagrams, schema fragments, examples or pseudocode when they remove ambiguity;
   omit empty templates. Finish when workers cannot invent incompatible shared answers.
6. **Preserve local judgement.** Explicitly distinguish owner-reserved decisions,
   Morfeo's material design, Supervisor's contract-supported shared execution decisions
   and Implementer's equivalent reversible local choices. An internal function name
   need not be prescribed; a shared response shape may need to be. References to code
   lines are inspection evidence, not a permanently fixed patch instruction.
7. **Design verification.** Map each acceptance obligation to a scenario, expected
   observable result and intended evidence in the owning artifacts. Provide the
   canonical runnable validation required by the resolved standard, including prerequisites,
   commands/tool actions and pass/fail observations. Product end-to-end validation is not a
   mandate to build fresh qualification machinery for every source or documentation change.
   Prefer the smallest sufficient existing check; justify new instrumentation by a concrete
   risk those checks cannot cover. Do not add a live rollback, cross-version matrix or agent
   campaign merely because a previous release used one. Preserve actual mandatory gates.
   Distinguish proposed from executed checks and unit evidence from integrated acceptance;
   do not impose test-first, live calls or behavioral qualification unless required.
   Check the representative starting state and decisive oracle before expensive
   qualification. Distinguish a product defect, a verification/oracle defect, and a
   coordination failure. Preserve useful failure evidence and reuse the reviewed
   method at closure rather than casually rebuilding the instrumentation.
8. **Check contradictions before finalizing.** Compare scope, deliverables, acceptance,
   authority, dependencies, preservation and expected test effects. A real-flow test
   cannot also require its own board/session records never to change. Preservation
   normally names unrelated state and declared product invariants, not all bytes on
   the machine. Verify every referenced owning artifact exists at the intended base.
   Record the reason for genuinely non-applicable design dimensions without filler.
   Perform a cold-read self-check: given only the referenced artifacts, list the
   decisions the receiver would still have to invent and remove each material gap.
   This is an author self-check, not an independent reviewer verdict.
9. **Materialize one handoff.** Use the authorized `objective_contract` capability with
   explicitly verified portable Project identity and incremental sections. Set optional
   `implementer_harness` on `begin` or `supersede` only when the owner explicitly requests
   another Implementer harness for that contract; without that explicit request omit the
   parameter or use `hermes`. Reference owning artifacts rather than copying a competing
   spec/plan. Validate, finalize and checkpoint exact bytes through the normal Git workflow. Carry only the prescribed
   short envelope to Supervisor; keep returned opaque routing values in root-card
   side data exactly as the capability requires. Never invent or repair routing identity.
10. **State what is and is not complete.** Report design self-check evidence and any
    remaining material risk. Structural validation/finalization is not semantic
    approval. Supervisor independently checks receipt quality and derives `tasks.md`;
    do not claim cross-artifact task coverage before that breakdown exists. If review
    returns a contract defect, repair the owning artifact and supersede final bytes
    when required; never patch an immutable contract in place.
11. **Remain design steward after handoff.** On an addressed question or intermediate
    evidence notice (such as lifecycle notices on `review_requested`, `changes_requested`,
    `blocked`, or root decomposition handoff), inspect the exact current obligation
    and candidate. Distinguish a local correction from a false premise, and provide
    a bounded direction or canonical design revision. Acknowledge a sound continuation
    without duplicating Supervisor's review. Do not wait for the final result when
    current evidence already invalidates the approach; do not take over implementation.
    Early advice is not final result acceptance. Clarifications within existing accepted
    obligations go in the owning plan/evidence and addressed response; material changes
    to finalized contract terms use `objective_contract supersede`, not an in-place edit.
    On supported runtimes, opt in via `kanban_create(..., collaboration="advisory")` from
    the trusted originating session. Otherwise use available explicit observation/comments;
    do not assume this portable procedure runs on a particular installation or bootstrap.

## Writing rules and compact evidence

Separate four kinds of statement in the owning artifact: **decided** (authority and
rationale), **assumed** (evidence and what would invalidate it), **locally delegated**
(choice and boundaries), and **illustrative** (example, not a new obligation). A
material unverified assumption cannot become a build-ready decision by changing its
label. Use MUST only for an existing or accepted requirement, not a stylistic preference.
Write an action, its observable output and its completion condition rather than a list
of adjectives. Avoid repeating the same rule in the Objective Contract, plan and skill.

Keep the approved choice, reason, evidence/assumption and local freedom together in the
existing plan when material. Use existing identifiers and references, not another registry,
schema or file created merely to hold a decision table.
If design is incomplete, return the specific question, why it changes the outcome,
known alternatives and evidence, and which owner can decide. Do not ask the owner to
repeat context that the repository or prior accepted artifact can answer.

### Collaboration comment lifecycle and examples (illustrative)

Peer collaboration uses an optional `collaboration` object on `kanban_comment`:

- **Addressed request to origin:**
  `kanban_comment(task_id="t_...", body="Design question: ...", collaboration={"action": "request", "recipient": "origin", "evidence_refs": ["specs/plan.md#L10"]})`
- **Morfeo response:**
  `kanban_comment(task_id="t_...", body="Direction: ...", collaboration={"action": "respond", "request_id": 12, "disposition": "advice", "evidence_refs": ["specs/spec.md#L45"]})`
- **Requester ack and resolution:**
  `kanban_comment(task_id="t_...", body="...", collaboration={"action": "ack", "message_id": 12})`
  `kanban_comment(task_id="t_...", body="Applied design clarification", collaboration={"action": "resolve", "request_id": 12, "disposition": "applied"})`

Dispositions for respond include `advice`, `continue`, `design_revision`, `owner_input`,
or `unavailable`. Early advice is not final result acceptance; peer responses provide
guidance, never owner authority or independent review approval.

## Worked contrast (illustrative, not executed evidence)

Weak: "Add robust cache recovery; test adequately."

Better, only if approved: "The existing cache is optional. On a corrupt cache record,
fall back to the canonical source without altering it; return the same public result
as a cold read. The shared adapter returns the existing result type and records the
existing cache-miss code. Acceptance compares cold and corrupt-cache reads and checks
source preservation. The local eviction data structure remains an Implementer choice."

The improvement is a decided behavior, interface and oracle, not extra prose or a
prescribed implementation. An objective with durable concurrent writers would need
additional applicable state/atomicity decisions; this example does not supply them.

## Pitfalls

- Proposing, asking about, or selecting an alternative Implementer harness without an explicit owner request.
- Treating eleven nonempty sections, a digest or `finalize` as proof of good design.
- Saying "Supervisor will design the API" when the API is material missing intent.
- Prescribing every line of code, inventing architecture for a small change, or copying
  the same authority into several competing documents.
- Making downstream workers locate artifacts that exist only in a chat or dirty base.
- Treating an expected objective-owned test mutation as damage to unrelated user state.
- Claiming every revision is a design failure: new owner intent and corrected repository
  baselines are different from an initially contradictory acceptance criterion.
- Treating intermediate collaboration advice or continuation acknowledgment as final contract acceptance.
- Taking over product implementation or directly editing board tasks during post-handoff stewardship.

## Verification

For the contract being authored, check sufficiency, missing material decisions,
contradictions and applicable interface/state boundaries. A small objective must not acquire
irrelevant architecture. Record exact references and local discretion; do not call author
self-check independent review. These dimensions are not a mandatory synthetic case campaign
for every skill edit. Resource checks verify text/packaging, not agent behavior; when the owner
chooses ordinary-use observation, state that limit rather than adding E2E qualification.
