# Aether Agents — Conceptual Multi-Agent Design

**Status:** accepted current conceptual design through PD-64
**Accepted baseline:** 2026-08-17
**Last amended:** 2026-08-21
**Product authority:** Christopher

## 1. Purpose and scope

This document owns Aether's current product concept: participants, roles, authority boundaries, selected foundations, and explicitly open technical questions.

It does not define the final process topology, concurrency mechanism, Git strategy, persistence technology, communication protocol, model allocation, deployment, or implementation. Those decisions belong to the stages linked from `ROADMAP.md`.

Aether is deliberately **prompt-native and agentic**. A stage is a cognitive work frame that an agent recognizes or forms from current intent, instructions, context, and relevant artifacts. No workflow engine, parser, scheduler, database, state machine, or executable transition is required to create or advance a design stage.

Future code may provide communication, persistence, observability, tools, objective artifact validation, or enforcement of protected effects. Such code is supporting infrastructure: it does not define product intent, cognitive stages, or the agents' reasoning sequence.

## 2. Product model

### What Aether builds

Aether builds software. The owner states an idea once — "build me a website", a new feature, a change to something that already exists — and the system produces working code that is tested, validated, and well implemented, without further supervision.

Both greenfield and brownfield work are first-class. Aether is used by a working programmer on new projects and on projects that already exist and already run; neither case is the exception.

Aether is not specialized to a stack, a domain, or a project type, and it is not tailored to any individual. It is public and open source, and intended to be usable by any owner. The only personalization is the preferences Morfeo learns about its owner through the Hermes framework, which makes that memory structural rather than convenient: it is the system's single adaptation mechanism.

**Success** is fidelity to intent, achieved without supervision. Aether fails if the agents cannot work alone, or if they work alone and produce something that is not the idea the owner asked for.

**Quality** means the software does what the owner wanted. The specification is the quality mechanism, and Spec Kit's practices are how it earns that role. The corollary is load-bearing: what is obvious to the owner does not exist for the agent, so the job of the specification is to write the obvious down.

### Why the roles are separated

Aether was previously hub-and-spoke: a single Hermes agent permanently designed, delegated, supervised, implemented, held the conversation with the owner, and maintained its own skills. That overload failed. The current role separation corrects a diagnosed failure, not an architectural preference, so **permanent re-concentration remains the standing failure mode**. It is distinct from a bounded operational action performed directly by Morfeo: punctual stewardship does not transfer the Supervisor's or Implementer's standing responsibilities to Morfeo.

The split mirrors a software team: the owner is the product owner, Morfeo is the designer, the supervision role is the tech lead, and the implementation role writes the code. A design decision that would make no sense in a human team is probably wrong.

### Participants

Aether separates one human authority and three AI-agent roles:

1. **Christopher designs and decides.**
2. **Morfeo turns intent into coherent design, specifications, and contracts, and is the owner's direct operational steward for proportional bounded work.**
3. **The unnamed supervision role conducts execution against an accepted contract.**
4. **The unnamed implementation role executes bounded units of work and may be replicated as A, B, C...N instances.**

This separation prevents an economical implementation agent from taking product decisions or a supervisor from silently changing design. It also prevents the opposite inefficiency: waking the full pipeline for bounded operational work that Morfeo can complete confidently without gaining proportionate assurance from decomposition and independent review.

## 3. Conceptual flow

```mermaid
flowchart LR
    U["Christopher<br/>User · Designer · Final authority"]
    M["Morfeo<br/>Design · Contract architecture · Operational stewardship<br/>Highest design reasoning"]
    D["Direct bounded action<br/>Morfeo executes and verifies"]
    S["Supervision role<br/>Decomposition · Supervision · Convergence"]

    I1["Implementer A<br/>Bounded execution"]
    I2["Implementer B<br/>Bounded execution"]
    I3["Implementer C<br/>Bounded execution"]
    IN["Implementer N<br/>Bounded execution"]

    U <-->|"Joint design, decisions, and feedback"| M
    M -->|"Bounded operational objective"| D
    M -->|"Substantial objective: accepted contract and specs"| S

    S -->|"Bounded work unit"| I1
    S -->|"Bounded work unit"| I2
    S -->|"Bounded work unit"| I3
    S -->|"Bounded work unit"| IN

    I1 -->|"Result and evidence"| S
    I2 -->|"Result and evidence"| S
    I3 -->|"Result and evidence"| S
    IN -->|"Result and evidence"| S

    S -->|"Contract or design defect"| M
    M -->|"Revised contract when required"| S
```

## 4. Roles and authority

| Role | Primary responsibility | May decide | Must escalate | Primary output |
| --- | --- | --- | --- | --- |
| **Christopher — user and designer** | Own product intent and final technology authority | Vision, objectives, constraints, priorities, preferences, acceptance, and protected external effects | Nothing inside product authority; safety and platform constraints still apply | Current intent and final decisions |
| **Morfeo — design and specification** | Convert Christopher's intent into coherent design and executable contracts | Evidence-backed reversible design defaults within delegated scope | Material ambiguity without a defensible default; conflicts with Christopher's intent; protected effects | Accepted specs and contracts |
| **Morfeo — operational stewardship** | Complete bounded operational objectives directly when the full pipeline adds no proportionate guarantee | Route selection for the complete owner objective; local reversible execution choices inside existing authority | A direct action that expands into substantial work; any authority or protected effect not already delegated | Verified direct result, or one executable contract handed to Supervisor |
| **Morfeo — learning and adaptation** | Improve long-term collaboration with Christopher | Durable memory, preferences, reusable design skills, and context strategy | Any inference that would contradict current instruction or turn temporary state into a permanent preference | Better context and future contracts |
| **Supervision role — unnamed** | Conduct execution until the accepted contract is satisfied or shown defective | Work decomposition, dependencies, parallelism, assignment, retries, evidence review, and operational convergence within the contract | Any need to change product intent, selected technology, authority, or acceptance criteria | Integrated result and evidence, or a structured contract defect |
| **Implementation role — unnamed, replicable** | Execute one bounded work unit correctly | Local implementation choices allowed by the task and contract | Missing authority, contract ambiguity, blockers, or any required redesign | Executed change, evidence, and status or blocker |

Each lower level has a narrower decision space. A lower role must never silently repair a higher-level defect by changing intent.

```text
Implementer
    ↓ blocker or contract defect
Supervision
    ↓ product or design defect
Morfeo
    ↕ Christopher when material authority is required
Revised accepted contract
    ↓
Supervision and implementation resume
```

## 5. Prompt-native operating method

Aether's multi-agent workflow means a pattern of prompts, instructions, contracts, handoffs, and agent reasoning. It is not a deterministic pipeline.

Morfeo selects between direct stewardship and the multi-agent pipeline by reasoning about the owner's complete objective. No classifier, score, numeric threshold, workflow state, or external gate makes that decision. A direct route is appropriate when scope is understood and bounded, consequences are inspectable, correction or reversal is reasonably simple, decomposition is unnecessary, and independent review would not add proportionate value. A feature, architectural change, multi-responsibility objective, complex integration, or materially uncertain build belongs to the pipeline.

The unit of classification is the objective the owner requested, not each technical mutation. Morfeo must not split a substantial objective into apparently small steps to execute it directly. Inspection to discover scope is allowed and does not itself select the direct route. If direct inspection reveals substantial work, Morfeo stops expanding the change, produces the canonical contract, and hands it to Supervisor.

The governing rule is: use the process that fits the problem, not the maximum process available.

An agent may infer, define, split, combine, revisit, or reorder practical work stages as evidence requires. Roadmap labels and gates are documentary or instructional signals. Tests, checklists, scripts, and validators measure artifacts, implementations, or effects; they do not authorize cognitive stage transitions.

Aether may later automate transport or safeguards. Automation remains subordinate to the agentic method and cannot become the source of product intent.

## 6. Replicable implementation role

The implementation role is one role with multiple possible instances, not a set of personalities or permanently named specialties.

```text
Supervision
    ├── Implementer A
    ├── Implementer B
    ├── Implementer C
    └── Implementer N
```

Replication is intended to accelerate independent or sufficiently decoupled work. R5 and R7 must still determine isolation, synchronization, concurrency limits, evidence independence, failure handling, and integration. The conceptual ability to replicate does not authorize creating workers now.

## 7. Model and reasoning policy

Aether uses a descending capability-and-cost methodology aligned with the narrowing decision space of each role:

| Role | Capability position | Economic rationale |
|---|---|---|
| Morfeo | Highest-capability selected model | Intent extraction, product decisions, contract architecture, and bounded direct stewardship have the widest error propagation. |
| Supervisor | Strong independent-judgement model | Decomposition, dependency analysis, review, integration, and convergence require judgement independent from both intent authoring and implementation. |
| Implementer | Lowest-cost model that still passes the role's quality gates | Its unit already fixes the goal, context, shared decisions, and acceptance criteria; parallel throughput must not relax correctness. |

The public distribution binds no provider, Router, or model identifier. The installing user chooses the provider and role bindings, may use different vendors, and may select the same model for two or all three roles. Descending allocation is the methodology for choosing among qualified models, not a requirement to buy three distinct services.

Every binding is held to the same contract, project constitution, tests, and review standard. Future re-tiering and claims that one model is superior require controlled evaluation by role and gate under R11 and R12. Model identifiers remain local configuration facts; prompts, work cards, and public product requirements depend on role capability rather than a vendor-specific name.

## 8. Spec-Driven Development and GitHub Spec Kit

Aether uses Spec-Driven Development: accepted specifications and contracts govern implementation rather than documenting code after the fact.

GitHub Spec Kit is the selected methodological foundation for constitution, specification, clarification, research, planning, tasks, requirements-quality checks, analysis, implementation, and convergence.

Aether will absorb Spec Kit's intellectual contracts before choosing an integration mechanism. The preferred adaptation order is:

```text
methodological reuse
    → Aether prompts, skills, and contracts
    → project-local templates, presets, overlays, or extensions if needed
    → upstream-core changes only for demonstrated incompatibility
```

Spec Kit is not installed or vendored by this design baseline. R3 owns the future mapping of phases across Morfeo, supervision, and implementation.

## 9. Hermes Framework

Hermes Agent / Hermes Framework is the selected agent foundation. Selection does not mean every native mechanism is automatically adopted.

Hermes provides **three coordination primitives**, and Aether builds none of them (PD-28):

- **In-process delegation** — a function call that forks anonymous subagents and joins their results. Fast, observable, hierarchical, steerable mid-flight, and not durable across a restart.
- **The durable multi-profile board** — a shared task queue where every worker is a full OS process with its own profile and persistent memory, every handoff is a durable row, work survives crashes by reclaim, humans can intervene at any point, and each task may pin its own model.
- **A2A** — the Agent2Agent protocol v1.0, bidirectional, for crossing process, machine, or framework boundaries.

An earlier version of this section declared the board subsystem not selected. **That declaration is withdrawn**: it was made without evidence, and R4's verified research established that upstream describes the board's purpose in terms that match Aether's architecture directly — decompose, implement in parallel worktrees, review, iterate, open a pull request — and that every criterion upstream gives for choosing it is an accepted Aether requirement. The choice among the three primitives belongs to R5 and must be argued from those criteria.

R4 classifies relevant capabilities as reusable, adaptable, insufficient, incompatible, or unselected. A capability must not be classified as unselected on unverified evidence. The foundation itself may be reopened only by Christopher, and only if a non-negotiable Aether requirement proves incompatible with Hermes with no responsible bounded adaptation; a missing native capability alone is not sufficient.

## 10. Communication protocol

A2A is the preferred communication candidate, and Hermes 0.20.1 — the version Aether runs — **ships a complete bidirectional implementation** as a platform plugin: protocol v1.0, agent cards, JSON-RPC methods, streaming, signed push notifications, per-peer tokens, prompt-injection filtering, credential redaction, an audit log, and anti-loop caps. It interoperates with agents built on other frameworks.

Availability is still not adoption. Upstream's own guidance is that A2A is for crossing process, machine or framework boundaries, and that multiple agents on one machine should prefer in-process delegation or the durable multi-profile work queue.

R6 must therefore decide against that guidance and against Aether's chosen topology, not against availability. The question is which Aether role boundaries genuinely cross a process, and R5 owns that.

*A previous version of this section claimed Hermes contained no A2A implementation. That claim was researched against version 0.19.1, which is not the source Aether runs, and is withdrawn. See `specs/r4-hermes-boundary/research.md` §11.*

## 11. Accepted product decisions and review triggers

| ID | Current decision | Reopen when |
| --- | --- | --- |
| **PD-01** | Christopher owns final product and technology authority. | Christopher explicitly changes the authority model. |
| **PD-02** | Aether has Morfeo, one supervision role, and one replicable implementation role in addition to Christopher. | Evidence from R2, R5, or R7 shows the separation cannot preserve authority, quality, or useful execution. |
| **PD-03** | Only Morfeo currently has a proper name; the other roles remain unnamed. Profile identifiers such as `supervisor` and `implementer` are role descriptors used as runtime names, not proper names. | Christopher explicitly names or restructures them. |
| **PD-04** | Lower roles cannot silently change higher-level intent or contracts. | Only a Christopher-approved authority redesign in R1 or R10. |
| **PD-05** | Hermes Framework is the selected agent foundation. | R4 demonstrates a non-negotiable incompatibility with no responsible bounded adaptation, and Christopher chooses to reopen it. |
| **PD-06** | GitHub Spec Kit is the methodological foundation. | Upstream change or R3 evidence shows a core principle conflicts with an accepted Aether requirement and cannot be adapted without weakening either source. |
| **PD-07** | The implementation role is replicable as A...N instances. | R5 or R7 evidence shows replication cannot preserve isolation, authority, integration, or acceptable economics. |
| **PD-08** | Design stages are prompt-native cognitive constructs, not code-instantiated workflow objects. | A later stage demonstrates a specific safety or correctness property that requires bounded executable enforcement; the cognitive method remains authoritative. |
| **PD-09** | Design, build, and activation are separate authority scopes. | Christopher explicitly replaces the scope model after R1 or R10 analysis. |
| **PD-10** | Aether builds software from a stated intent: tested, validated, working code produced without supervision. | Christopher redefines what the product does. |
| **PD-11** | Greenfield and brownfield work are both first-class. | Christopher restricts the product to one of the two. |
| **PD-12** | Aether is universal and open source; the only personalization is Morfeo's learned owner preferences. | Christopher decides Aether is personal infrastructure rather than a distributable product. |
| **PD-13** | Permanent re-concentration of roles is the standing architectural risk, since the prior hub-and-spoke design failed by role overload. Punctual proportional execution by Morfeo under PD-44 is legitimate stewardship, not reassignment of Supervisor or Implementer as standing responsibilities. | Evidence shows the proportional boundary causes Morfeo to become Aether's general implementer or weakens the three-role separation. |
| **PD-14** | Completed work is reviewed by running the product, not by reading the diff, and review is retrospective. | Christopher changes how he accepts work. |
| **PD-15** | **Aether** maintains the project end to end. The owner operates no part of the repository, toolchain, or release path, and the normal path contains no confirmation gate. Pipeline effects are performed by the role that owns the phase; PD-44 additionally permits Morfeo to perform bounded operational work directly without assuming pipeline implementation as a permanent role. | An irreversible failure demonstrates that recoverability and R10 enforcement cannot carry the safety burden alone. |
| **PD-16** | Defects noticed outside the requested scope are raised as a question, never fixed or discarded silently. | Christopher delegates in-scope judgement for incidental repairs. |
| **PD-17** | The contract is the Spec Kit artifact set. Aether introduces no competing contract artifact, and carries its own authority, budget, and brownfield boundary inside `plan.md`. | Evidence shows the upstream artifact set cannot carry an Aether obligation without distortion. |
| **PD-18** | Contract defects reach Morfeo and external failures reach the owner. **Resolved by PD-32:** both are raised by blocking the card with a reason, which waits durably instead of interrupting anyone. | — |
| **PD-19** | Aether borrows Spec Kit's intellectual practices and builds its own workflow on top. Upstream is read before anything is designed, only genuine gaps are designed, and every deviation is recorded. | Spec Kit ceases to be maintained or diverges from Spec-Driven Development. |
| **PD-20** | When Morfeo selects the pipeline, the handoff falls between technical planning and task breakdown. Morfeo delivers intent and approach; the supervision role makes it executable and owns breakdown, analysis, review, and convergence. A direct PD-44 action creates no delegated unit or role boundary. | Evidence shows the supervision role cannot derive a breakdown faithful to the contract. |
| **PD-21** | In the pipeline, the supervision role is the independent reviewer that Spec Kit assumes must be human, because it authors neither the requirements nor the code. Direct PD-44 stewardship is selected only when independent review would not add proportionate value; it is not disguised pipeline work. | A separate reviewing capability proves necessary beyond the three roles, or direct-route defects show review cannot remain a proportional judgement. |
| **PD-22** | Owner preferences live in Morfeo's learned memory; a project's standards live in that project's constitution. The two are never merged. | Aether becomes single-user infrastructure rather than a distributable product. |
| **PD-23** | Testing is a per-project standard recorded in that project's constitution, resolved during extraction and never defaulted. Test-first is optional. | Christopher imposes a universal testing rule. |
| **PD-24** | Execution never pauses for the owner between units of work. Each converged increment is independently runnable. A unit blocked on a defect is the exception and does not stop its siblings. | Christopher asks to validate between units. |
| **PD-25** | Hermes already implements most of the multi-agent runtime and structurally enforces several Aether invariants. Where a native capability satisfies a requirement, it is the primary mechanism and Aether's instruction is reinforcement. | A Hermes upgrade removes or weakens an enforced invariant. |
| **PD-26** | **Superseded by PD-29.** Recorded as "unattended execution cannot survive a runtime restart"; that was a property of in-process delegation, not of Hermes. | — |
| **PD-27** | Every agent gets its own profile. Two agent processes MUST NOT share one Hermes home, because both write memory and each loads the other's writes into its prompt. Shared memory, where needed, uses an external memory provider. | Upstream withdraws the constraint. |
| **PD-28** | Hermes provides three coordination primitives — in-process delegation, a durable multi-profile board, and A2A. Aether selects among them on upstream's stated criteria, and builds none of them. | A requirement is found that no primitive satisfies. |
| **PD-29** | Aether's coordination primitive is Hermes's durable multi-profile board. The unit of durability is the card, not the process: a crash or restart costs at most one attempt. Work crossing a role boundary always moves as a card. A direct PD-44 action crosses no role boundary and therefore does not require a ceremonial card. | A requirement is found that the board cannot satisfy and delegation or A2A can. |
| **PD-30** | Three profiles, one per role, matching PD-02 exactly; the Implementer remains replicable and Supervisor remains separate. **Partially superseded by PD-44:** absence of Morfeo's operational tools is no longer the mechanism separating the roles. Parallelism is a concurrency setting, never additional roles or profiles. | Christopher restructures the roles. |
| **PD-35** | Role containment is **asymmetric**, verified in source. Morfeo has broad operational capability bounded by current authority and agentic self-control; Supervisor and Implementer retain their role limits, including the enforced restriction on arbitrary implementer fan-out. Capability must never be described as authority, and instructed or hook-enforced limits must never be described as structural. | Upstream changes the relevant capability gates or observed direct execution shows a missing protected-effect boundary. |
| **PD-31** | Implementation work runs in a git worktree per card, so parallel workers never share a working tree. A conflict is resolved by a fresh worker that produced neither side, carrying both intents through parent links — neutrality comes from fresh context, not from a new role. | — |
| **PD-32** | Escalation is a blocked card with a reason. It waits durably, any role or Christopher may act on it, and sibling work is untouched. Non-convergence blocks for review rather than exiting silently. | — |
| **PD-33** | An execution problem is never solved by adding an agent role. Fresh context, a card-pinned skill, or a per-card model override are tried first; a new role requires Christopher's explicit decision against PD-02. | Christopher decides a fourth role is warranted. |
| **PD-34** | `tasks.md` is the breakdown of record and belongs to the contract; cards are execution instances of its units. There is one plan and one execution surface, never two plans. | — |
| **PD-36** | **Escalation is two-tier.** A question the contract can answer is resolved by the system: the asking unit addresses a decision card to the supervisor, links it as a parent of its own card, and resumes automatically when it is answered. No human is involved and no block is spent. Only a question the contract genuinely cannot answer becomes a block, which reaches Morfeo, who alone may revise a contract, and who then asks Christopher. Christopher's instruction, 2026-08-17. Verified end to end against the runtime. | Christopher changes who answers a stuck unit. |
| **PD-37** | **The human-visible block budget is effectively one attempt per unit.** After one block, one release, and a second block for the same cause, the runtime routes the unit out of the work pool. The threshold is a source constant, absent from configuration, and raising it would mean modifying upstream core. Aether designs so this budget is rarely spent. | Upstream makes the threshold configurable. |
| **PD-38** | **A native behaviour that performs a phase Aether assigned to a role is incompatible and is disabled, not tolerated.** Automatic triage decomposition and automatic triage specification are both on by default and both do the supervisor's work without reading the contract. Availability is not adoption, and a default is not a decision. | The supervisor role is removed or upstream removes the behaviours. |
| **PD-39** | **Contract artifacts are written only on the integration branch, by their owning role.** Morfeo owns the specification and the plan; in pipeline work Supervisor owns the breakdown and Implementers own code in their worktrees. In direct PD-44 work, Morfeo owns and manages the bounded change it performs without creating a false implementation card. An Implementer never reads the breakdown to understand its work — its card body carries every decision it depends on. | Evidence shows a card body cannot carry a unit's decisions or direct stewardship cannot preserve attributable reversible changes. |
| **PD-40** | **The board is the only inter-role transport.** A2A is implemented as a platform adapter, is complete, and is deliberately unused while every role runs on one host; MCP is an outward integration surface and never a work transport. | A role must run on another machine, or a non-Hermes agent must participate as a role. |
| **PD-42** | **Recovery is not free.** A crashed worker's unit survives, but the crash consumes an attempt *and* increments the failure counter, while a stale-claim reclaim does not. Environmental failure and defective work draw on the same budget, so the attempt limit must exceed the number of environmental failures one unattended session can plausibly produce. Verified by execution. | Upstream separates environmental failure from work failure. |
| **PD-43** | **Enforcement can be fully configured and completely inert.** A hook that is not on the runtime's first-use allowlist does not fire at all — it does not fail closed, it is absent. Dispatcher-spawned workers are immune because the dispatcher accepts hooks explicitly when spawning; **Morfeo is the exposed role**, because it runs as a persistent interactive session. Enforcement must be verified as live, never assumed from configuration. This runtime fact does not require a hook that restricts Morfeo to contract-file writes; PD-44 removes that conceptual dependency. | Upstream removes the consent gate or applies it differently to persistent sessions. |
| **PD-44** | **Morfeo executes proportionally.** Morfeo is the owner's interlocutor, contract architect, and operational steward. It may use terminal and general project file access to complete a bounded objective directly when the full pipeline adds no proportionate guarantee. It chooses agentically against the complete owner objective: no classifier, score, numeric threshold, special workflow, or external gate selects the route. It must not fragment substantial work into small mutations, and if inspection reveals feature-scale, architectural, multi-responsibility, or materially uncertain work, it stops expansion and hands one executable contract to Supervisor. Existing authority and protected-effect limits remain unchanged; Git rollback is used when appropriate. **Amended 2026-08-20:** Morfeo also receives `code_execution`, `cronjob`, and `delegation` (`delegate_task`) on both CLI and Telegram; browser execution and computer use remain excluded. Cron may either schedule Morfeo's own follow-up on direct work or schedule a future pipeline start, chosen case by case by the same whole-objective reasoning as the direct/pipeline route, and never creates permanent autonomy outside an owner-requested objective. Delegated subagents may only assist Morfeo's own bounded direct work, never receive product implementation that belongs to Supervisor/Implementer; this delegation boundary is agentic doctrine, not hook enforcement. | Evidence shows the agentic boundary is unreliable enough to require an owner-approved redesign, or Christopher changes Morfeo's stewardship authority. |
| **PD-45** | **`skills` and `vision` are base toolsets for Morfeo, Supervisor, and Implementer.** Every role may manage skill documents for continuous self-improvement and inspect images or frontends within work it is already authorized to perform. Tool access does not widen any role's decision authority or responsibility boundary. | Evidence shows `skills` or `vision` access produced an unforeseen effect that requires containment, or Christopher restricts either capability to fewer roles. |
| **PD-46** | **Capability and cost descend with role scope without binding the public product to a provider.** The installer selects the strongest qualified model for Morfeo, a strong independent-judgement model for Supervisor, and the lowest-cost model that still passes the Implementer gates. The same model may serve multiple roles, and every tier retains the same contract, tests, and review standard. Provider, Router, and model identifiers are private installation facts and never public product requirements. | Christopher changes the methodology, or controlled role-and-gate evaluation demonstrates a materially better allocation. |
| **PD-47** | **The initial pipeline capacity is one Supervisor and three concurrent Implementers.** One Supervisor owns decomposition, review, and integration for a contract; speed comes from independent Implementer instances, not duplicate Supervisors. The board-wide cap remains four, with explicit profile limits `supervisor: 1` and `implementer: 3`. | Measured collision rate, integration cost, provider throttling, resource saturation, or contract duration justify recalibration. |
| **PD-48** | **Aether 1.0 is a public stable product release, not a design snapshot.** A third party must be able to install and update it, supply their own credentials, and reproduce the supported three-role product. The public artifact contains only product-owned identities, portable configuration, policy and hooks, Aether-specific skills, lifecycle commands, documentation, and tests. It excludes Christopher's private profiles, Router and model bindings, credentials and authentication, memories, sessions, preferences, personal skill catalog, logs, databases, caches, and machine-specific configuration. | Christopher changes the release promise or evidence shows a narrower public product is the only responsible scope. |
| **PD-49** | **Aether qualifies and ships against a public downstream distribution of Hermes.** The downstream remains a minimal, auditable patch set over upstream; generally applicable fixes continue upstream, merged equivalents retire local patches after qualification, and every Aether release pins an exact downstream tag and commit. Upstream changes are never adopted automatically. Aether installs this runtime in isolation and does not replace a user's personal Hermes installation. | A qualified upstream Hermes release satisfies every Aether dependency without downstream patches, or the maintenance burden demonstrably exceeds the guarantees the downstream provides. |
| **PD-50** | **Aether 1.0 officially supports Linux native and WSL2 only.** Windows-native and macOS operation are outside the 1.0 support contract. WSL2 support requires a Linux distribution with `systemd`, Linux-side Git and tooling, and both repositories and Hermes state on the Linux filesystem rather than `/mnt/c`. The release matrix uses Ubuntu 24.04 LTS native, Ubuntu 24.04 LTS on WSL2, and continued Garuda/Arch validation. | Christopher changes the platform scope, or qualified evidence supports another platform or requires narrowing an existing one. |
| **PD-51** | **Aether 1.0 has a product release test standard distinct from each downstream project's constitution.** The release cannot be tagged until deterministic CI, clean installation, one real complete Morfeo → Supervisor → Implementer → independent review → integration flow, state-preserving update, rollback, uninstall, secret scanning, and the accepted native-Linux and WSL2 platform checks all pass against the exact release candidate. | Christopher changes the release evidence standard, or a test is shown not to exercise the guarantee it claims. |
| **PD-52** | **Aether is initialized per project.** From a greenfield or brownfield Git repository, `aether init` creates or validates that project's constitution, contract surface, board, workspace isolation, and Git integration; subsequent `aether` launches Morfeo in that project. Each project has its own board and execution state, and no project silently shares cards or workspaces with another. | Evidence shows Hermes's project/board isolation cannot support this mapping, or Christopher chooses a machine-global work queue. |
| **PD-53** | **Issues #192 and #195 are non-blocking known limitations for Aether 1.0 and target future minor releases.** Version 1.0 does not claim semantically exact retry accounting, live useful-work progress, or that a heartbeat proves progress. The limitations remain public and must not be hidden by release language or UI. | Either limitation is shown to threaten correctness, authority, recovery, or the accepted 1.0 release evidence. |
| **PD-54** | **A packaged CLI is Aether's canonical public distribution and operating surface.** The package installs the `aether` command and owns setup, per-project initialization, launch, diagnosis, update, rollback, and uninstall while keeping Aether source and dependency locks auditable. A repository clone may remain a development path, but it is not the normal user installation. | Packaging proves materially less reliable or maintainable than a tagged-source installer, or Christopher changes the desired product experience. |
| **PD-55** | **Aether updates are explicit, compatible, and recoverable.** Only `aether update` updates the product; it previews current and target versions, creates a backup, updates the CLI, pinned downstream runtime, profiles, and policy as one compatible set, verifies the result, and restores the previous set if verification fails. Aether never performs a silent product update or automatic upstream adoption. | Christopher authorizes unattended updates, or evidence requires a different atomicity or rollback mechanism. |
| **PD-56** | **Aether follows Semantic Versioning and qualifies prereleases before stable publication.** The 1.0 path includes at least one `v1.0.0-rc.N` release candidate, public installation and accepted release evidence against that exact candidate, and only then `v1.0.0`. Release automation must understand SemVer prereleases and must never present an RC as stable. | Christopher changes the versioning policy or a release channel requires a compatible additional representation. |
| **PD-57** | **The public Python distribution is `aether-agents`, its executable is `aether`, and PyPI is the canonical package index.** The normal installation is `uv tool install aether-agents`; releases publish both wheel and source distribution from GitHub Actions through PyPI Trusted Publishing with OIDC, no long-lived PyPI token. Git tags use SemVer (`v1.0.0-rc.1`) and Python metadata uses the equivalent PEP 440 form (`1.0.0rc1`). | The package name becomes unavailable, PyPI or uv cannot preserve an accepted guarantee, or Christopher changes the distribution channel. |
| **PD-58** | **Setup has one validation engine and two supported interfaces.** `aether setup` is the guided human path; `aether setup --config <file>` is the reproducible automation path. Both produce and verify the same state. Secrets are never accepted as command-line arguments or stored in versioned setup files; provider authentication remains in native Hermes credential mechanisms or user-supplied environment state. | Evidence shows one interface cannot preserve parity or a supported deployment requires another non-secret input mechanism. |
| **PD-59** | **Aether's public repository is also a portfolio-quality product surface.** It provides a product-oriented README, executable quickstart, architecture diagram, short real-flow demonstration, published GitHub Pages documentation, Linux/WSL2 support matrix, visible known limitations, release artifacts with checksums and provenance, and reciprocal links among GitHub, documentation, and PyPI. Presentation must demonstrate verified behaviour and never substitute polish for release evidence. | Christopher changes the public presentation goal or a medium cannot be maintained without weakening product work. |
| **PD-60** | **Aether 1.0 adds no product telemetry.** Logs remain local and redact sensitive content; Aether never uploads projects, prompts, contracts, credentials, or usage metrics. Public support uses GitHub Issues for defects and features, GitHub Discussions for questions, and private vulnerability reporting for security disclosures, with no implied response-time SLA. | Christopher explicitly authorizes bounded telemetry or changes the support model after a privacy and threat review. |
| **PD-61** | **The downstream Hermes runtime is a verified GitHub Release artifact, not a renamed PyPI package.** The public fork builds its original `hermes-agent` wheel and source archive in CI and publishes them with checksums and provenance. Each Aether release locks the exact fork tag, commit, artifact URL, SHA-256, Python compatibility, and Aether compatibility; setup verifies that lock before installing the wheel into an isolated versioned runtime. | The fork can be consumed from a package index without renaming or weakening provenance, or GitHub Release delivery cannot meet the accepted availability or verification guarantees. |
| **PD-62** | **Aether follows the Linux XDG boundary.** Non-secret configuration lives under `~/.config/aether`; versioned runtimes and profiles under `~/.local/share/aether`; local state, logs, and backups under `~/.local/state/aether`; replaceable downloads under `~/.cache/aether`. Project repositories contain only portable project identity and contract artifacts. Boards, credentials, runtime state, and workspaces are local and remain outside tracked project content. | A supported Linux/WSL2 environment cannot provide the XDG mapping or Hermes requires a different isolation boundary. |
| **PD-63** | **External package-manager upgrades are detectable but not silently trusted.** `aether update` is the only supported coherent product update. If `uv tool upgrade aether-agents` or another external action changes the manager independently, `aether doctor` detects the CLI/runtime/profile/lock mismatch, refuses incompatible activation, and offers explicit reconciliation or rollback. Aether does not claim it can prevent the user from changing their own installation. | uv supplies an enforceable atomic multi-artifact update primitive, or evidence requires a different mismatch-recovery contract. |
| **PD-64** | **Release qualification uses the public path.** The preregistered 1.0 release-candidate scenario installs from PyPI, consumes the verified public downstream artifact, uses a public Hermes-supported provider rather than private owner infrastructure, and runs a realistic Git repository through the complete three-role path on the accepted native-Linux and WSL2 matrix. Credentials and any model spend require explicit owner authorization at the execution gate and never enter release artifacts. | Christopher changes the qualification path, or the selected public provider cannot exercise an accepted guarantee. |
| **PD-41** | **Every claim about runtime behaviour is labelled verified or assumed.** Executing the behaviour outranks reading the code, which outranks reading the documentation; where they disagree, the more direct evidence wins and the disagreement is recorded. This project has paid twice for treating documentation as evidence. | — |
A current explicit instruction from Christopher always supersedes older project content; the owning artifact must then be updated.

## 12. Design areas and owners

Every area below now has a written specification. The table records which artifact owns each question, not which questions remain open; what remains open within a stage is listed in that stage's `Done When` and in `specs/r13-synthesis-and-release/spec.md` §7.


| Topic | Owning stage |
| --- | --- |
| Christopher–Morfeo interaction, authority matrix, and operational experience | R1 |
| Contract metamodel, handoffs, acceptance, and defect return | R2 |
| Multi-agent mapping of Spec Kit methods | R3 |
| Native Hermes boundary and Aether extensions | R4 |
| Agent topology, identity, process/profile boundary, and isolation | R5 |
| A2A adoption and communication envelope | R6 |
| Supervision, parallelism, retries, and convergence | R7 |
| Git, workspaces, ownership, and integration | R8 |
| Persistence, artifacts, memory, skills, and recovery | R9 |
| Security, trust, and executable authority enforcement | R10 |
| Evidence, observability, and controlled evaluation | R11 |
| Models, routing, budgets, and role-specific quality gates | R12 |
| Coherent design release and implementation-entry contract | R13 |

No open decision in this table is authorized merely because a framework already provides a mechanism.

## 13. Canonical artifact relationships

- `DESIGN.md` owns the current conceptual product design and accepted high-level product decisions.
- `ROADMAP.md` owns only stage boundaries, dependencies, documentary status, and links.
- `specs/<stage>/spec.md` owns current requirements and decisions for one stage.
- `specs/<stage>/research.md` owns evidence, rationale, alternatives, and change impact.
- Plans, contracts, tasks, prompts, code, and runtime state are derived artifacts or implementation evidence.
- Agent prompts, skills, memories, and conversations are operational context, not competing product truth.

## 14. Reference sources

- Hermes Agent / Nous Research: <https://github.com/NousResearch/hermes-agent>
- GitHub Spec Kit: <https://github.com/github/spec-kit>
- Agent2Agent Protocol: <https://github.com/a2aproject/A2A>

The existence of a capability in any reference source does not imply its adoption by Aether.
