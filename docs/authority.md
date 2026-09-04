# Authority and artifact ownership

Aether separates design intent, stage requirements, execution coordination, current-build behavior, implementation status, and historical evidence into distinct artifacts. Ownership is assigned by **semantic question**, not by a single global linear precedence stack.

When artifacts appear to conflict, resolve the question at the artifact that owns that semantic domain, update that owner first, and reconcile dependent derived artifacts. Historical evidence is preserved rather than rewritten to match present conditions.

## Architectural principles

1. **Ownership by semantic question** — No single artifact holds universal precedence. Each artifact has an explicit domain of authority and explicit non-ownership.
2. **Current owner instructions** — An explicit instruction from the project owner governs immediately for the specific question it addresses, but it must be captured into the authoritative artifact for that question. Protected-effect boundaries (credential acquisition, unauthorized remote mutation, destructive operations) remain firm.
3. **Derived artifacts cannot widen intent** — Plans, task cards, `tasks.md`, worktrees, generated references, and runtime observations are derived execution artifacts or evidence. They cannot expand scope, grant new authority, or contradict upstream normative specifications.
4. **Unmistakable separation** — Current-build user guidance (`docs/`), implementation status registry (`docs/capabilities.toml`), and effective runtime state represent three different concerns and must never be conflated.
5. **Preservation of history and living specifications** — Active stage specifications are living normative owners and may be revised owner-first when requirements evolve. Superseded decisions, rationale, and evidence are preserved through research artifacts (`specs/<stage>/research.md`), Git history, test/evidence records, changelogs, and release records; historical evidence is not rewritten or retrofitted to mimic current behavior.

## Semantic information classes and artifact map

The table below maps each information class to its authoritative artifact, defines what each artifact does not own, specifies its scope and portability, and provides safe placement and update rules.

| Information class | Authoritative artifact | Owns | Does not own | Scope & portability | Safe placement & update rule |
| --- | --- | --- | --- | --- | --- |
| **Current owner instruction** | Current explicit owner instruction | Immediate governing effect for the specific semantic question it addresses | Permanent bypass of protected-edge safety (credentials, unauthorized remote mutations, destructive actions), durable project history until recorded, or unrecorded project-wide precedent | Live/private until captured in the owning artifact (then public/portable or private/local matching the owner) | Governs immediately; must be captured into the authoritative artifact that owns that semantic domain before closure. Objective-specific delegated authority is recorded in the finalized Objective Contract. |
| **Framework-wide (Constitutional)** | Project Constitution ([`specs/r0-design-governance/spec.md`](../specs/r0-design-governance/spec.md)) | Foundational project governance principles, non-negotiable architectural tenets, and constitutional constraints | Component-level design, stage implementation requirements, execution plans, or operational prompt wording | Public, portable | Updated via owner-approved updates to `specs/r0-design-governance/spec.md`; `.specify/memory/constitution.md` is a derived local materialization, not a second authority. |
| **Framework-wide (Conceptual design)** | Conceptual product design ([`DESIGN.md`](../DESIGN.md)) | Framework-wide conceptual product design, framework role definitions, authority boundaries, accepted high-level decisions | Project constitution principles, detailed stage requirements, execution plans, implementation status, release proof, or runtime state | Public, portable | Updated when framework-wide architecture, role boundaries, or system definitions are revised by owner decision. Stage specifications state stage-scoped role requirements only and cannot redefine framework roles. |
| **Stage requirements (Stage specs)** | Stage specifications (`specs/<stage>/spec.md`) | Normative scope, functional requirements, acceptance criteria, stage-scoped role requirements, and technical decisions for a named stage | Rationale and history (owned by `research.md`), current source behavior when implementation differs, or framework-wide conceptual design | Public, portable | Active stage specifications are living normative owners; updated through owner-approved stage specification revisions. Superseded history is preserved in research, not retrofitted. |
| **Stage rationale (Research & history)** | Research and rationale (`specs/<stage>/research.md`) | Stage rationale, decision evidence, evaluated alternatives, upstream research citations, and change impact as evidence | Current normative intent (owned by `spec.md`), execution approach (owned by `plan.md`), or current source behavior | Public, portable | Research records preserve rationale and history as evidence; updates capture new evaluations while preserving historical rationale. Does not replace current normative intent in `spec.md`. |
| **Execution approach (Plans & contracts)** | Execution approach and interface handoffs (Derived: `plan.md` and stage `contracts/`) | Derived execution approach and interface handoffs | Product intent, stage specifications, or delegated authority (cannot widen accepted specifications or applicable Objective Contracts) | Public, portable | Constrained by accepted specifications and applicable Objective Contracts; cannot widen product intent, specs, or delegated authority. |
| **Role-specific (Prompt wording)** | Packaged versioned role resources ([`src/aether_agents/resources/profiles/<role>/SOUL.md`](../src/aether_agents/resources/profiles/)) | Executable role-local prompt wording, persona phrasing, and role-internal reasoning structure | Role definitions, authority boundaries, or product truth (owned by `DESIGN.md` and stage specifications). `home/SOUL.md` is a generic source-tree Hermes prompt, not the Aether role-resource owner. Local installed/profile copies remain local runtime state. | Public, portable (packaged versioned resources); local profile copies are private/local runtime state | Refine prompt instructions within established role authority; never grant new permissions or alter role authority. |
| **Role-specific (Procedures & skills)** | Canonical and learned skill procedures | Reusable method, step-by-step procedural recipes, tool usage guidance, known pitfalls, and verification steps | Product intent, project truth, execution status, constitutional principles, or role authority | Aether Canonical Skills are public/versioned/package-owned at `src/aether_agents/resources/skills/<skill-name>/SKILL.md`; Project Canonical Skills are tracked/versioned/portable at `.aether/skills/<skill-name>/SKILL.md`; Learned Profile Skills are private/local/adaptive | Skills own procedure only and never grant authority. Discover project skills through root `AGENTS.md` and direct project-relative reads; use the existing package/native profile mechanism for Aether skills. Promote learned procedures only after sanitization, generalization, verification, independent review, commit, and PR. |
| **User-private (Preferences & recall)** | Private user profile and memory (`USER.md`, `MEMORY.md` in private profile home) | Private user preferences, working style, personal context, and durable cross-session recall | Project principles, architectural decisions, public specifications, or shared repository rules | Private, local (never committed) | Maintained via memory tools during private interactions; never placed in public artifacts, commits, or shared docs. |
| **Environment-specific (Runtime state & local setup)** | Effective runtime state (local project mappings, profile homes, XDG product state, configured services/providers, sessions, runtime observations) | Transient runtime facts, local machine paths, active process IDs, provider configuration, session histories, direct observations | Product intent, current-build behavior guidance, or capability implementation status | Private, local (never committed) | Discloses operational facts of the local environment; never cited as normative product intent, committed to git, or placed in public docs. Public docs describe artifact classes and boundaries only. |
| **Project-specific (Portable identity)** | Portable project identity ([`.aether/project.toml`](../.aether/project.toml)) | Tracked, portable project identity and configuration actually represented by the marker (`project_id`, project name, repository metadata) | Local machine paths, project slugs, local/native Hermes Project bindings (owned by local project mappings), user preferences, or runtime session state | Public, portable | Written or updated during explicit project initialization (`aether init`). Contains no machine-specific runtime mapping or credential material; local project mappings own runtime binding and location. |
| **Project-specific (Repo instructions)** | Repository operating instructions ([`AGENTS.md`](../AGENTS.md)) | Checkout-specific operating rules, research citations, source resolution, and contributor boundaries | Conceptual product design, normative stage requirements, or product truth | Public, portable | Updated when repository development conventions or upstream research baselines change. Links to documentation maps rather than duplicating product truth. |
| **Objective-specific (Contracts)** | Finalized Objective Contracts (`.aether/objective-contracts/<contract-id>/v<N>.md`) | One objective's executable outcome, scope, delegated authority, deliverables, acceptance, testing, and stop conditions | Framework-wide conceptual design, constitution principles, or stage requirements (constrained by them) | Public, portable | Finalized versions are read-only; revisions supersede with a new version. Drafts and handoff envelopes do not widen scope. Derived artifacts (plans, tasks) cannot widen scope. |
| **Execution (Coordination & status)** | Native board state (`kanban.db` rows, events, comments, runs) | Delegated execution status, task assignments, run history, and worker handoffs | Product intent, contract authority, acceptance meaning, or implementation status outside the execution record | Private/local, durable coordination state (not committed) | Updated via native Kanban lifecycle tools during execution. Does not redefine contract intent or product truth. |
| **Execution breakdown (Tasks)** | Versioned execution breakdown (Derived: `tasks.md`) | Tracked public/portable derived execution breakdown and task ordering | Product intent, stage specifications, architecture, or the finalized Objective Contract (cannot widen specifications or contract intent) | Public, portable | Authored during task planning; tracked public/portable derived execution breakdown and task ordering artifact. Neither `tasks.md` nor native task cards widen specifications or the finalized Objective Contract. |
| **Execution (Task unit)** | Native task-card body | Private/local durable board coordination, execution instructions, and acceptance criteria scoping one execution unit | Wider project scope, contract authority, architecture, specifications, or independent product decisions (cannot widen specifications or the finalized Objective Contract) | Private, local (durable board coordination; not committed) | Authored during task decomposition and dispatch; scopes one execution unit and cannot expand beyond the parent Objective Contract. Scope outside the task but within the contract returns to Supervisor; scope outside the contract requires Morfeo and the project owner. |
| **Execution (Isolation)** | Git worktree and branch | Isolated workspace and branch state for one task's changes (mutable write isolation) | Status authority, contract intent, or permanent architecture | Local, mutable workspace isolation (not an authority) | Created for task isolation; source overlap is reconciled by the integration process. Never treated as an intent or status store. |
| **Current-status (Current-build behavior)** | Current documentation (`docs/`) | Current behavior available in this build, user guides, references, and diagnostic steps | Conceptual design, normative stage requirements, implementation status registry, or live runtime state | Public, portable | Updated when public surfaces, user-facing behavior, or diagnostic commands change. Explains how to use the current build; does not prove implementation status or replace registries. |
| **Current-status (Implementation registry)** | Capability registry ([`docs/capabilities.toml`](capabilities.toml)) | Sole authoritative implementation status (`implemented`, `partial`, `transitional`, `unsupported`, `deprecated`) and traceability links for public surfaces | Behavioral contracts, design authority, or runtime observation | Public, portable | Sole authority on capability implementation status. Updated when capability surface status changes; the generated reference ([`docs/reference/capabilities.md`](reference/capabilities.md)) is explicitly derived via `scripts/check_documentation.py` and must not be edited directly. |
| **History (Roadmap & tracking)** | Future work and tracking ([`ROADMAP.md`](../ROADMAP.md), issue tracker) | Stage index, sequencing dependencies, planned future work, visible release limitations, and issue history | Current capability implementation status, current product manual, or workflow execution authority | `ROADMAP.md` is public, portable; issue records are remote tracking records | Updated as roadmap milestones progress and stages complete; does not serve as the capability status registry. |
| **History (Release deltas)** | Release history ([`CHANGELOG.md`](../CHANGELOG.md), Git release tags, hosted release records) | Release deltas, version-to-version changes, and unreleased change entries | The complete current user manual, capability registry, or design authority | `CHANGELOG.md` and Git release tags are tracked/portable; hosted release records are public remote records, not portable project files | Updated upon preparing a release or recording an unreleased user-visible delta; does not replace the current documentation manual. |
| **Evidence (Auditable change & verification)** | Auditable change and verification history (Git commits/tags, pull requests, test records, qualification evidence) | Auditable record of changes made and verification evidence supporting claims | Normative intent or current manual behavior (all evidence supports claims and cannot redefine intent) | Git commits/tags and committed evidence are tracked/portable; hosted pull-request and release records are public remote records, not portable project files; local test outputs, scratch logs, and runtime observations are private/local transient evidence | All evidence supports claims and cannot redefine intent. Committed change and verification history is preserved; local test runs and scratch logs are private/local transient evidence and are not all append-only public records. |
| **Evidence (Implemented behavior)** | Implemented behavior and reproducible runtime facts (Source code and direct execution) | Demonstrable behavior of the source code and observed direct execution facts | Normative intent or design authority (all evidence supports claims and cannot redefine intent) | Source code is public, portable; local direct execution output is private/local, transient evidence | Reveals what is implemented or observed and may expose drift, but all evidence supports claims and cannot redefine normative intent. |
| **Reader explanation** | Reader-facing placement and conflict explanation (Derived: [`docs/authority.md`](authority.md)) | Explanatory reader guide mapping artifact ownership, non-ownership, and conflict resolution | Normative architectural decisions, stage requirements, or capability status (derived from `DESIGN.md` section 13) | Public, portable | Explains canonical relationships for readers without competing with normative owners. [`docs/index.md`](index.md) provides navigation only and owns no semantic project truth. |

## Canonical skill discovery and precedence

Aether has three procedural skill classes, not a second authority system:

- **Aether Canonical Skills** are public, versioned, package-owned resources under
  `src/aether_agents/resources/skills/<skill-name>/SKILL.md`.
- **Project Canonical Skills** are tracked and portable with the project under
  `.aether/skills/<skill-name>/SKILL.md`. Root `AGENTS.md` points file-capable agents to
  this convention, and any applicable file is read directly from the worktree.
- **Learned Profile Skills** remain private, local, adaptive, and non-canonical. They
  never auto-promote and are not copied into public resources.

For compatible procedures, a Project Canonical Skill is more specific than an Aether
Canonical Skill; both outrank a Learned Profile Skill. This procedural ordering never
overrides owner instruction, the constitution, conceptual design, stage specifications,
the Objective Contract, repository rules, or protected-effect policy. No skill grants
authority. Promotion of a learned procedure requires sanitization, generalization,
verification, independent review, commit, and pull request; private text, identities,
machine paths, runtime state, providers, models, repositories, and credentials stay out
of the promoted resource.

## Separating current docs, capability status, and runtime state

A frequent failure mode in automated multi-agent environments is confusing what the software is designed to do, what has actually been verified as implemented, and what a specific running machine happens to observe. Aether enforces strict boundaries between these three concepts:

1. **Current behavior documentation (`docs/`)**
   - *Question answered:* "How is this build intended to be used, configured, or diagnosed?"
   - *Characteristics:* Public, portable, user-facing guidance. It explains available commands, flags, workflows, and troubleshooting.
   - *Boundary:* It does not prove that a feature is bug-free or verified, nor does it replace the traceability registry.

2. **Capability implementation status (`docs/capabilities.toml`)**
   - *Question answered:* "What is the verified implementation status of each public surface in this build?"
   - *Characteristics:* Public, portable, structured TOML registry. It is the **sole** authority on whether a capability is `implemented`, `partial`, `transitional`, `unsupported`, or `deprecated`. It links each surface to its specifications, documentation, implementation files, and tests.
   - *Boundary:* It does not define behavioral contracts or design intent; it tracks implementation reality against specifications. The generated reference ([`docs/reference/capabilities.md`](reference/capabilities.md)) is explicitly derived from this registry.

3. **Effective runtime state (local environment and observation)**
   - *Question answered:* "What is occurring on this specific host or process right now?"
   - *Characteristics:* Private, local, transient facts (e.g., active process IDs, local file paths, configured environment variables, runtime session observations).
   - *Boundary:* Runtime state discloses operational reality of the moment, but it cannot redefine product intent, amend current documentation, or alter capability statuses.

## How to read capability status

The capability registry ([`docs/capabilities.toml`](capabilities.toml)) is the sole authority on capability implementation status and admits only these status values:

- **`implemented`** — The source code and focused automated verification support the documented current behavior.
- **`partial`** — Functional behavior exists, but a stated functional boundary or qualification requirement remains incomplete.
- **`transitional`** — A transitional mechanism is deliberately present while public qualification or upstream retirement conditions remain open.
- **`unsupported`** — The interface exists (e.g. as a CLI placeholder) but explicitly refuses execution rather than simulating the promised product effect.
- **`deprecated`** — A retained compatibility surface has a documented replacement or planned retirement path.

The generated reference ([`docs/reference/capabilities.md`](reference/capabilities.md)) is explicitly derived from `docs/capabilities.toml` via `scripts/check_documentation.py`. Never edit the generated reference directly.

## Conflict resolution flow

When two artifacts or instructions appear to conflict, follow this deterministic resolution sequence:

```
[Conflict Detected]
        │
        ▼
1. Identify the semantic question
   (What exact decision, rule, or fact is in dispute?)
        │
        ▼
2. Determine the authoritative artifact class
   (Consult the artifact map above to find the sole owner.)
        │
        ▼
3. Is an explicit owner instruction present?
   ├── Yes ──► Apply immediately for that semantic question,
   │           then capture it into the owning artifact.
   │           (Respect protected-effect safety boundaries.)
   └── No  ──► Follow the existing owning artifact.
        │
        ▼
4. Update the owning artifact first
   (Do not patch around the discrepancy in derived files.)
        │
        ▼
5. Reconcile dependent derived artifacts
   (Update generated docs, task instructions, or materializations.)
        │
        ▼
6. Preserve historical evidence
   (Preserve research rationale, test evidence, and commit history;
    do not rewrite history to match present conditions.)
        │
        ▼
7. Irreconcilable conflict or foundational scope change?
   └── If two accepted normative owners conflict irreconcilably,
       or if resolution requires defining mission, capabilities,
       autonomy envelopes, or use cases:
       STOP work and escalate to the project owner and Morfeo.
```

## Representative placement and conflict scenarios

The following scenarios illustrate how artifact ownership applies to common development decisions:

| Scenario | Conflict or placement question | Resolution rule |
| --- | --- | --- |
| **New framework principle** | A contributor proposes a fundamental rule governing agent execution. | The project constitution (`specs/r0-design-governance/spec.md`) owns constitutional principles. It cannot be placed in `AGENTS.md`, a task card, or a prompt. |
| **Role prompt wording vs. role authority** | A role prompt needs new wording to guide tool selection. | Prompt wording belongs in packaged versioned role `SOUL` resources (`src/aether_agents/resources/profiles/<role>/SOUL.md`). Role responsibilities and authority limits belong in `DESIGN.md` and stage specs. Prompt wording cannot grant authority. |
| **Owner preference vs. constitution** | The owner expresses a personal coding or interaction preference. | Private preferences belong in private `USER.md` or `MEMORY.md`. They do not redefine shared constitutional principles or public architectural specifications. |
| **Machine-specific fact vs. behavior docs** | Documenting a command that requires a workspace directory. | `docs/` explains portable command syntax and relative directory structure. Absolute machine paths, local usernames, or environment-specific PIDs belong only in private local runtime state. |
| **Objective scope vs. task expansion** | A worker discovers additional work outside the current task. | Finalized Objective Contracts own objective scope; `tasks.md`, task cards, and worktrees are derived units and cannot widen scope. If the work is outside the current task but still within the scope of the finalized Objective Contract, it returns to Supervisor for a separately scoped unit. Scope outside the finalized contract requires Morfeo and the project owner, resulting in a new or superseding Objective Contract. A child card never widens the contract. |
| **Board status vs. observer projection** | An external monitoring tool reports a task status different from the board. | Native Hermes Kanban board rows, events, and runs own execution coordination. Observer projections or third-party tools cannot redefine board truth. |
| **Source behavior vs. stage requirement** | A command's implementation differs from its specification in `specs/`. | The stage specification owns normative intent. The divergent source code contains a defect or incomplete feature; `docs/capabilities.toml` reflects the accurate status (`partial` or `unsupported`). |
| **Capability registry vs. roadmap claim** | A future stage in `ROADMAP.md` lists a feature that is partly written. | `ROADMAP.md` owns planning and dependencies. `docs/capabilities.toml` alone owns current implementation status. The feature remains unreleased or partial in the registry. |
| **Release delta vs. current manual** | Documenting how a feature changed from the previous release. | `CHANGELOG.md` records the release delta between versions. `docs/` provides the complete, self-contained user manual for the current build. |
| **Conflicting normative artifacts** | `DESIGN.md` and a stage specification contain contradictory statements. | Neither artifact may silently overwrite the other. Stop execution and escalate to the project owner and Morfeo for an authoritative architectural decision. |

## Historical artifacts remain historical

Active stage specifications (`specs/<stage>/spec.md`) are living normative owners and may be revised owner-first when stage requirements evolve. Superseded decisions, research rationale, alternatives, qualification evidence, and release history remain preserved through research artifacts (`specs/<stage>/research.md`), Git commits, test and evidence records, changelogs, and release records. They explain why the present state exists and must not be retrofitted or treated as an active implementation-status registry. In particular, a candidate lifecycle implementation or a local qualification result is not an installed service, public release, or provider-backed success claim.

## Safe placement and public boundary rules

1. **No private data in public artifacts** — Never commit or document owner identifiers, private usernames, credentials, API keys, provider/model bindings, absolute machine paths, or local profile state.
2. **Portability** — Public documentation and specifications must remain independent of machine environments, local paths, and private setups.
3. **No premature capability or mission claims** — Documentation describes current-build behavior without anticipating unapproved mission, autonomy envelopes, or unverified capabilities.
