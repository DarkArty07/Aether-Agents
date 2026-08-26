# Changelog

## Unreleased

### Retired shell-text classification in the pre-tool policy

- Retired the generic command-text filesystem confinement for Implementer `terminal`/`execute_code` (#233). It could not enforce anything — an allowed interpreter derives its destination internally, so no path appears in argv — while denying legitimate work whose argv merely named a workspace-local venv launcher symlinked to a managed interpreter.
- Retired the Supervisor and Implementer contract-ownership checks that classified shell command text (#237), which read the `>` inside a quoted Git pretty-format such as `<%ae>` as redirection toward a contract path.
- Contract ownership, workspace ownership, branch/history, external-effect, credential, Kanban and Git integration guards are unchanged; ownership is enforced on structured file tools where the target is a typed argument.
- Added regressions for both blocked real commands and for contract ownership still denying a typed `write_file` against an owned artifact.

### Objective Contract prose boundary

- Separated Objective Contract secret-shape rejection from the observation metadata scanner so UTF-8, multiline and long contract prose remains authorable while recognized credential values stay denied.
- Added source and built-wheel regressions for the pipeline-blocking `#236` case.

### Reproducible Morfeo TUI activation

- Added a versioned, standard-library launcher that binds Morfeo to the repository-local profile and project directory.
- Added a side-effect-free `--check` mode with visible validation of profile state, executable availability, and required `file`/`kanban` toolsets.
- Added clean-process regression coverage for cwd independence, environment cleanup, reserved argument rejection, and missing prerequisites.

### Reproducible policy hooks

- Added a sanitized, versioned canonical source for the shared Morfeo, Supervisor, and Implementer pre-tool policy.
- Added an explicit standard-library synchronization tool with atomic installation, content-and-mode parity checks, drift-safe rollback, and no process or network activation surface.
- Added clean-clone tests for installation, verification, rollback, secret exclusion, and the #199 Implementer branch-inspection regression.

## 0.24.0 — 2026-08-17

### R0 design-governance baseline

- Accepted and versioned Aether's R0 governance specification, pinned Spec Kit research, and evidence-linked quality checklist.
- Established prompt-native agentic stages: agents form and conduct cognitive work from intent, prompts, instructions, and artifacts without a code-instantiated workflow engine.
- Adopted a living-spec model, a shallow spec-of-specs roadmap, three documentary stage labels, selective impact regression, and one consolidated human decision review.
- Defined canonical ownership across conceptual design, roadmap, stage specs, research, derived artifacts, implementation evidence, and agent context.
- Preserved Git history as the design-baseline mechanism while deferring branch, commit, worktree, and publication mechanics to R8.
- Added an explicitly unauthorized walking-skeleton evidence checkpoint after R2 and R5 so R6, R7, and R9 do not close runtime claims from documentation alone.

### Repository consistency

- Replaced the obsolete detailed roadmap and seven-state decision model with an English shallow roadmap linked to the accepted R0 spec.
- Consolidated accepted and open product decisions in `DESIGN.md`, added review triggers, and left model hierarchy subject to controlled R12 evaluation.
- Made the repository policy allow future `specs/**` artifacts while retaining an exact canonical base manifest and rejecting local runtime state.
- Added CI checks for R0 closure metadata, sequential IDs, Markdown links and fences, document mode, rejected legacy paths, and the fully checked evidence-linked requirements checklist.

### Rationale and alternatives

- Chose prompt-native agent reasoning over a deterministic stage orchestrator because no executable controller is needed to preserve design scope, authority, evidence, or review.
- Rejected seven per-decision states and custom B0/B1 registries because the living spec, research rationale, three roadmap labels, and Git history provide the required recovery with less cognitive machinery.
- Kept Spec Kit as pinned external evidence rather than vendoring it; future integration must begin with project-local adaptation layers.

### Impact and rollback

- This release changes documentation and repository policy only. It does not install Spec Kit, create agents, modify the live Hermes profile, implement A2A, activate services, or authorize build work.
- R0 is complete; R1 is the next recommended design area but does not start automatically.
- To roll back the complete versioned baseline, use tag `v0.23.0`. Local Hermes runtime state is unaffected by either version.

## 0.23.0 — 2026-08-16

### Hermes-only design reset

- Reset Aether Agents to a single Hermes Agent profile with reproducible configuration and GitHub governance.
- Removed the retired multi-agent product runtime, secondary profiles, custom MCP implementation, orchestration stack, product documentation, tests, schemas, scripts, and repository-owned skill catalog.
- Kept credentials, sessions, memories, databases, and runtime skills private and outside Git.
- Preserved Aether Router and Orca as independent external projects; this release does not modify or retire them.
- Replaced code-oriented CI with policy validation for the canonical 17-file manifest and simplified SemVer release automation.

### Breaking impact

- Previous multi-agent control, worker, coordination, installation, and qualification interfaces are no longer shipped.
- Pull requests and issues targeting the removed architecture are superseded by this reset.
- To roll back the versioned repository, use the `v0.22.0` tag or another earlier release.
