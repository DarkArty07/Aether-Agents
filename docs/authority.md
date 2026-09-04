# Authority and artifact ownership

Aether separates design intent, stage requirements, execution coordination, current-build behavior, implementation status, and historical evidence into distinct artifacts. Ownership is assigned by **semantic question**, not by a single global linear precedence stack.

When artifacts appear to conflict, resolve the question at the artifact that owns that semantic domain, update that owner first, and reconcile dependent derived artifacts. Historical evidence is preserved as an immutable record rather than rewritten to match present conditions.

## Architectural principles

1. **Ownership by semantic question** — No single artifact holds universal precedence. Each artifact has an explicit domain of authority and explicit non-ownership.
2. **Current owner instructions** — An explicit instruction from the project owner governs immediately for the specific question it addresses, but it must be captured into the authoritative artifact for that question. Protected-effect boundaries (credential acquisition, unauthorized remote mutation, destructive operations) remain firm.
3. **Derived artifacts cannot widen intent** — Plans, task cards, worktrees, generated references, and runtime observations are derived execution artifacts or evidence. They cannot expand scope, grant new authority, or contradict upstream normative specifications.
4. **Unmistakable separation** — Current-build user guidance (`docs/`), implementation status registry (`docs/capabilities.toml`), and effective runtime state represent three different concerns and must never be conflated.
5. **Preservation of history** — Specifications, research, plans, test records, changelogs, and audit trails document why the system reached its current state. They are never rewritten or retrofitted to mimic current behavior.

## Semantic information classes and artifact map

The table below maps each information class to its authoritative artifact, defines what each artifact does not own, specifies its scope and portability, and provides safe placement and update rules.

| Information class | Authoritative artifact | Owns | Does not own | Scope & portability | Safe placement & update rule |
| --- | --- | --- | --- | --- | --- |
| **Framework-wide (Constitutional)** | Project Constitution ([`specs/r0-design-governance/spec.md`](../specs/r0-design-governance/spec.md)) | Foundational project governance principles, non-negotiable architectural tenets, and constitutional constraints | Component-level design, stage implementation requirements, or operational prompt wording | Public, portable | Updated only via formal governance amendment; `.specify/memory/constitution.md` is derived materialization. |
| **Framework-wide (Conceptual design)** | Conceptual product design ([`DESIGN.md`](../DESIGN.md)) | Framework-wide conceptual product design, role definitions, authority boundaries, accepted high-level decisions | Project constitution principles, detailed stage requirements, implementation status, or release proof | Public, portable | Updated when framework-wide architecture, role boundaries, or system definitions are revised by owner decision. |
| **History & requirements (Stage specs)** | Stage specifications (`specs/<stage>/spec.md`) | Normative scope, functional requirements, acceptance criteria, and technical decisions for a named stage | Current source behavior when implementation differs, or framework-wide conceptual design | Public, portable | Authored in formal stage specifications under `specs/`; updated through stage specification revisions. |
| **History & rationale (Research & alternatives)** | Research and rationale (`specs/<stage>/research.md`, plans, evidence) | Upstream research citations, rationale, evaluated alternatives, qualification evidence, and background context | Current normative intent or current source behavior | Public, portable | Historical research remains immutable once accepted; new evaluations append new records. |
| **Role-specific (Prompt wording)** | Versioned role prompts ([`home/SOUL.md`](../home/SOUL.md) and prompt templates) | Executable role-local prompt wording, persona phrasing, and role-internal reasoning structure | Role definitions, authority boundaries, or product truth (owned by `DESIGN.md` and stage specifications) | Public, portable (versioned templates); local profile copy is local runtime config | Refine prompt instructions within established role authority; never grant new permissions or alter role authority. |
| **Role-specific (Procedures & skills)** | Reusable skills (`home/skills/`, profile skills) | Procedural step-by-step recipes, tool usage guidance, known pitfalls, and verification steps | Product intent, role authority, or constitutional principles | Public/portable (in-repo skills) or local profile state | Update steps and pitfalls as tool interfaces evolve; do not store product decisions or principles in skills. |
| **User-private (Preferences & recall)** | Private user profile and memory (`USER.md`, `MEMORY.md` in private profile home) | Private user preferences, working style, personal context, and durable cross-session notes | Project principles, architectural decisions, public specifications, or shared repository rules | Private, local (never committed) | Maintained via memory tools during private interactions; never placed in public artifacts, commits, or shared docs. |
| **Environment-specific (Runtime state & local setup)** | Effective runtime state (local project mappings, profile homes, XDG product state, configured services/providers, sessions, live observations) | Transient runtime facts, local machine paths, active process IDs, provider configuration, session histories, direct observations | Product intent, current-build behavior guidance, or capability implementation status | Private, local (never committed) | Discloses operational facts of the local environment; never cited as normative product intent or committed to git. |
| **Project-specific (Identity & binding)** | Portable project identity ([`.aether/project.toml`](../.aether/project.toml)) | Portable project identifier, project slug, and canonical project binding declaration | Local machine paths, user preferences, or runtime session state | Public, portable | Written or updated during explicit project initialization (`aether init`). |
| **Project-specific (Repo instructions)** | Repository operating instructions ([`AGENTS.md`](../AGENTS.md)) | Checkout-specific operating rules, research citations, source resolution, and contributor boundaries | Conceptual product design, normative stage requirements, or product truth | Public, portable | Updated when repository development conventions or upstream research baselines change. |
| **Objective-specific (Contracts)** | Finalized Objective Contracts (`.aether/objective-contracts/<id>/v<n>.md`) | One objective's executable outcome, scope, delegated authority, deliverables, acceptance, testing, and stop conditions | Framework-wide conceptual design, constitution principles, or stage requirements (constrained by them) | Public, portable | Finalized versions are read-only; revisions supersede with a new version. Derived artifacts (plans, tasks) cannot widen scope. |
| **Execution (Coordination & status)** | Native board state (`kanban.db` rows, events, comments, runs) | Delegated execution status, task assignments, run history, and worker handoffs | Contract intent, role authority, or product truth | Local coordination state (not committed) | Updated via native Kanban lifecycle tools during execution. |
| **Execution (Task unit)** | Task card body | Detailed execution instructions and acceptance criteria for one delegated unit of work | Wider project scope, contract authority, or independent product decisions | Bounded execution unit | Authored during task decomposition; cannot expand beyond the parent Objective Contract. |
| **Execution (Isolation)** | Git worktree and branch | Isolated workspace and branch state for one task's changes | Status authority or contract intent | Mutable isolation | Created for task isolation; discarded or merged upon task review and completion. |
| **Current-status (Current-build behavior)** | Current documentation (`docs/`) | Current behavior available in this build, user guides, references, and diagnostic steps | Conceptual design, normative stage requirements, implementation status registry, or live runtime state | Public, portable | Updated when public surfaces, user-facing behavior, or diagnostic commands change. |
| **Current-status (Implementation registry)** | Capability registry ([`docs/capabilities.toml`](capabilities.toml), generated [reference](reference/capabilities.md)) | Authoritative implementation status (`implemented`, `partial`, `transitional`, `unsupported`, `deprecated`) and traceability links | Behavioral contracts, design authority, or runtime observation | Public, portable | Updated when capability surface status changes; generated reference generated by script. |
| **History (Roadmap & tracking)** | Future work and tracking ([`ROADMAP.md`](../ROADMAP.md), issue tracker) | Stage index, sequencing dependencies, planned future work, visible release limitations | Current capability implementation status or workflow execution authority | Public, portable | Updated as roadmap milestones progress and stages complete. |
| **History (Release deltas)** | Release history ([`CHANGELOG.md`](../CHANGELOG.md), release tags) | Release deltas, version-to-version changes, and unreleased change entries | The complete current user manual or design authority | Public, portable | Updated upon preparing a release or recording an unreleased user-visible delta. |
| **Evidence (Auditability)** | Verification evidence (Git commits, PRs, test suites/runs, qualification records) | Auditable record of changes made, commands executed, and verified test results | Normative intent or current manual behavior | Public, portable (within git history) | Append-only audit record; verified by tool execution and automated test runners. |
| **Current owner instruction** | Explicit owner instruction | Immediate governing effect for the specific semantic question it addresses | Permanent bypass of protected-edge safety (credentials, unauthorized remote mutations, destructive actions) | Immediate operational directive | Governs immediately; must be captured into the authoritative artifact that owns that semantic domain. |

## Separating current docs, capability status, and runtime state

A frequent failure mode in automated multi-agent environments is confusing what the software is designed to do, what has actually been verified as implemented, and what a specific running machine happens to observe. Aether enforces strict boundaries between these three concepts:

1. **Current behavior documentation (`docs/`)**
   - *Question answered:* "How is this build intended to be used, configured, or diagnosed?"
   - *Characteristics:* Public, portable, user-facing guidance. It explains available commands, flags, workflows, and troubleshooting.
   - *Boundary:* It does not prove that a feature is bug-free or verified, nor does it replace the traceability registry.

2. **Capability implementation status (`docs/capabilities.toml`)**
   - *Question answered:* "What is the verified implementation status of each public surface in this build?"
   - *Characteristics:* Public, portable, structured TOML registry. It is the **sole** authority on whether a capability is `implemented`, `partial`, `transitional`, `unsupported`, or `deprecated`. It links each surface to its specifications, documentation, implementation files, and tests.
   - *Boundary:* It does not define behavioral contracts or design intent; it tracks implementation reality against specifications.

3. **Effective runtime state (local environment and observation)**
   - *Question answered:* "What is occurring on this specific host or process right now?"
   - *Characteristics:* Private, local, transient facts (e.g., active process IDs, local file paths, configured environment variables, live telemetry).
   - *Boundary:* Runtime state discloses operational reality of the moment, but it cannot redefine product intent, amend current documentation, or alter capability statuses.

## How to read capability status

The capability registry ([`docs/capabilities.toml`](capabilities.toml)) admits only these status values:

- **`implemented`** — The source code and focused automated verification support the documented current behavior.
- **`partial`** — Functional behavior exists, but a stated functional boundary or qualification requirement remains incomplete.
- **`transitional`** — A transitional mechanism is deliberately present while public qualification or upstream retirement conditions remain open.
- **`unsupported`** — The interface exists (e.g. as a CLI placeholder) but explicitly refuses execution rather than simulating the promised product effect.
- **`deprecated`** — A retained compatibility surface has a documented replacement or planned retirement path.

The generated reference ([`docs/reference/capabilities.md`](reference/capabilities.md)) is automatically derived from `docs/capabilities.toml` via `scripts/check_documentation.py`. Never edit the generated reference directly.

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
   (Never rewrite research, test evidence, or past logs.)
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
| **Role prompt wording vs. role authority** | A role prompt needs new wording to guide tool selection. | Prompt wording belongs in versioned role SOUL resources. Role responsibilities and authority limits belong in `DESIGN.md` and stage specs. Prompt wording cannot grant authority. |
| **Owner preference vs. constitution** | The owner expresses a personal coding or interaction preference. | Private preferences belong in private `USER.md` or `MEMORY.md`. They do not redefine shared constitutional principles or public architectural specifications. |
| **Machine-specific fact vs. behavior docs** | Documenting a command that requires a workspace directory. | `docs/` explains portable command syntax and relative directory structure. Absolute machine paths, local usernames, or environment-specific PIDs belong only in private local runtime state. |
| **Objective scope vs. task expansion** | A worker discovers a helpful feature outside the current task. | Finalized Objective Contracts own objective scope. Task cards and worktrees are derived units and cannot widen scope. New scope requires a new contract or child task request. |
| **Board status vs. observer projection** | An external monitoring tool reports a task status different from the board. | Native Hermes Kanban board rows, events, and runs own execution coordination. Observer projections or third-party tools cannot redefine board truth. |
| **Source behavior vs. stage requirement** | A command's implementation differs from its specification in `specs/`. | The stage specification owns normative intent. The divergent source code contains a defect or incomplete feature; `docs/capabilities.toml` reflects the accurate status (`partial` or `unsupported`). |
| **Capability registry vs. roadmap claim** | A future stage in `ROADMAP.md` lists a feature that is partly written. | `ROADMAP.md` owns planning and dependencies. `docs/capabilities.toml` alone owns current implementation status. The feature remains unreleased or partial in the registry. |
| **Release delta vs. current manual** | Documenting how a feature changed from the previous release. | `CHANGELOG.md` records the release delta between versions. `docs/` provides the complete, self-contained user manual for the current build. |
| **Conflicting normative artifacts** | `DESIGN.md` and a stage specification contain contradictory statements. | Neither artifact may silently overwrite the other. Stop execution and escalate to the project owner and Morfeo for an authoritative architectural decision. |

## Historical artifacts remain historical

Specifications, research, plans, evidence, the changelog, and `INCOMPLETE_IMPLEMENTATIONS.md` remain in place because they explain why the present state exists. They must not be rewritten or treated as an active implementation-status registry. In particular, a candidate lifecycle implementation or a local qualification result is not an installed service, public release, or provider-backed success claim.

## Safe placement and public boundary rules

1. **No private data in public artifacts** — Never commit or document owner identifiers, private usernames, credentials, API keys, provider/model bindings, absolute machine paths, or local profile state.
2. **Portability** — Public documentation and specifications must remain independent of machine environments, local paths, and private setups.
3. **No premature capability or mission claims** — Documentation describes current-build behavior without anticipating unapproved mission, autonomy envelopes, or unverified capabilities.
