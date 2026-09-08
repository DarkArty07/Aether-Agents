# Changelog

## Unreleased

### Execute-code helper contract and search_files JSON framing

- Taught the actual explicit-import contract for `execute_code` helpers `json_parse`, `shell_quote`, and `retry` in schema, CLI tip, and sandbox failure hints (#313).
- Kept truncated `search_files` output as one JSON document by moving the pagination hint into structured `_hint`, so `execute_code` receives a dictionary instead of `JSONDecodeError` (#353).
- Exact maintained-fork merge: `DarkArty07/aether-hermes` PR #3, `6243e40ea6b06e85061bf3fedffaad43eed51dec`.
- No version bump, package publication, tag, or live runtime activation is part of this delivery (`release_action=defer`, `release_channel=none`).

### Runtime reliability (laboratory isolation and maintained-fork bugs)

- Isolated disposable-probe laboratory destinations so poisoned parent identity cannot reach a native Kanban child, and rejected symlink/escaped sandbox paths before writes (#267).
- Qualified named-custom auxiliary resolution as already working on the maintained Hermes fork and added integrated regressions for both admitted spellings (#292).
- Adapted background-review run-token admission and identity-qualified cleanup so pre-admission cancel and a superseding turn do not send review HTTP (#294).
- Classified the explicit exhausted-pool `503` phrase before generic overload so an authorized configured fallback is used (#295).
- Forwarded request-scoped extra headers through the Responses adapter, retries, and configured fallback without leaking destination authentication (#301).
- Recovered a durable same-run Kanban completion from a read-only snapshot when the transcript receipt is missing, without fabricating a terminal tool receipt (#304).
- No version bump, package publication, tag, or live runtime activation is part of this delivery (`release_action=defer`, `release_channel=none`).

### Contract design and execution procedures

- Added the personally authored `objective-contract-design`, `supervisor-decomposition`, and `implementation-evidence` canonical resources and focused role wording: material design before handoff, useful independent decomposition, and requirement-linked unit evidence.
- Registered the resources through the existing explicit skill distribution surface and reconciled the corresponding inventory expectations; no new tool, loader, role, schema, model, or concurrency setting is introduced.
- New behavior is under organic observation in [#317](https://github.com/DarkArty07/Aether-Agents/issues/317). At the owner's direction this delivery does not run a local synthetic qualification campaign; source registration and resource installation do not establish behavioral quality or speedup.

### Optional shared project knowledge and role experiences

- Fixed #342: work-memory corrections honor the published 16,000-character limits, retain readable maximum-length Unicode records, and reuse the configured component backend so subprocess timeouts are not reset to defaults.
- Fixed #344: work-memory evidence now checks the exact regular-file entry at a valid Git commit, rejecting directories, symlinks, gitlinks, missing objects and path-pattern expansion without claiming independent verification.
- Added the native `aether-project-knowledge` plugin with identical `project_knowledge` and `work_memory` action catalogs for Morfeo, Supervisor and Implementer; portable templates remain disabled until explicitly configured.
- Added revision/worktree-scoped structural Graphify snapshots, stable collaborative publication locks, native-session/operator bindings and explicit dirty-file coverage instead of a global graph or last-project fallback.
- Added project/role experiences with complete original notes, lexical retrieval, paginated reads, revision-aware corrections, idempotent save retries, private signal-only reflection, operator export and deletion. Save keys are stored only as digests; changed payload reuse fails explicitly, and reflection cannot write a personal sidecar into the shared technical graph.
- Added the two package-owned canonical skills and availability-guarded guidance in all three SOUL resources, plus optional hash-locked component installation and diagnostics outside the Hermes environment.
- Fixed boundary defects #324–#327: cumulative `truncated` flag reporting native omission, byte bounds, or the 50-reference cap; complete-over-budget native answers remain `truncated=false` with an explicit warning; unsupported upstream recovery wording is normalized to supported Aether actions.
- Added structured provenance: source-bearing actions (`query`, `explain`, `neighbors`, `community`, `path`, `impact`) return project-relative, revision-bound, deduplicated `{path, location, revision}` references in stable order; path queries include path nodes and relation sites; the 50-reference cap sets `truncated=true` with a warning; no private absolute paths escape.
- Added query→explain→community discovery: `explain` returns `resolved_node` with snapshot-local `community_id` and name; `community` returns community metadata matching the requested ID.
- Added canonical action-discriminated schemas for `project_knowledge` and `work_memory` with root properties retained and field descriptions naming accepted actions; runtime validation strictly rejects inapplicable fields and identity injection.
- Updated the `project-knowledge` and `work-memory` canonical skills and project knowledge guides with validated examples, discovery procedures, and honest truncation/reference semantics.
- Documented setup, all commands, ownership, isolation and limitations. Structural Markdown navigation is supported; live-agent E2E and measured token savings remain separate qualification work. No live profiles or services are activated by these source changes.
- Expanded the reusable project-knowledge catalog to fourteen project actions (`stats`, `god_nodes`, read-only PR views and graph/tree visualization included) while retaining the five work-memory actions. Query-only `context_filter`, path-only `undirected`, bounded traversal controls, semantic coverage metadata, and optional configured auxiliary maintenance are documented without enabling a primary-model fallback or watcher.
- Added `scripts/qualify_knowledge_expansion.py`, which validates the 14/5 schemas and exercises production service paths with disposable two-project fixtures offline. Optional auxiliary/GitHub lanes report unavailable access honestly; no token-saving, universal-superiority, live-agent adoption or release claim is made.
- Paged `semantic_prepare` so a full eligible corpus stays under the unchanged 2MB Graphify transport cap (#333). Deadline-deferred chunks stay pending rather than failed, and a file is covered only when every chunk that includes it succeeded (#337).

### Current beta project and documentation surface

- Added the user-visible `aether init` path for an existing Git repository root: it writes the portable project marker, preserves the required ignore boundary, and binds exactly one existing native Hermes Project by exact primary path; `--hermes-project ID` resolves an otherwise ambiguous exact match without creating or changing a native Project.
- Added the Morfeo-only Objective Contract authoring surface, including draft `validate`, immutable final versions, Git-base verification, and `prepare_handoff` routing data for one isolated execution board per `(project_id, contract_id, version)`.
- Added project-scoped execution-board routing, per-flow Supervisor session continuity, and isolated Implementer worktrees; board and Hermes Project identifiers remain local routing data rather than portable contract content.
- Added the bounded Contract Observer surface and deterministic observation summaries, including the read-only `aether observe` path and Morfeo-only observation views.
- Established maintainable current documentation and capability traceability: `docs/` owns current behavior and `docs/capabilities.toml` owns implementation status, while this changelog records deltas and root reports link rather than compete.

These entries describe Unreleased beta work only. They do not claim package publication, release qualification, public availability, or activation of any protected external effect.

### Routine GitHub lifecycle no longer deadlocks the pipeline

- Fixed #281 by removing normal branch/tag push, pull-request lifecycle, issue reconciliation, and non-destructive GitHub Release creation/edit/upload from the common pre-tool denial path. These operations are owner-preauthorized for already provisioned project repositories; Supervisor still owns pipeline publication after independent review, while role ownership remains a contract/review responsibility rather than a shell-text permission.
- Kept precise fail-closed controls for force/lease/mirror/history or tag rewrite, direct default-branch push, `--no-verify`, remote ref deletion, administrative PR merge, destructive Release/repository mutation, workflow dispatch/enable/disable and run cancel/delete, secret/variable mutation, arbitrary mutating APIs, package/container publication, deployment/infrastructure effects, credential widening, and irreversible destruction. Routine same-candidate CI reruns remain part of the allowed GitHub lifecycle.
- Added positive and negative three-role regressions, including global Git/GitHub flags and abbreviated force variants. Rollback is one Git revert plus restoration of the pre-install policy-hook backup; hook synchronization requires no process restart.

### Exact Hermes evidence lane restored

- Fixed the `hermes_exact` lane resolving its checkout from the *installed* Hermes runtime (#234). Under the declared `transitional_fork` mode that runtime always carries the local patch set and a newer commit, so it could never satisfy the locked baseline and the lane failed permanently on an environment fact that said nothing about Aether. The runner already documents that it "never consults a private/editable Hermes installation"; the tests now follow the same rule.
- Lanes that only read the Hermes tree honour `AETHER_EXACT_HERMES_CHECKOUT`; lanes that import the installed plugin skip with the baseline they need instead of failing.
- Reconciled the locked qualification manifest with the collected suite (#228): `core_test_files` now matches the runner's `CORE_TESTS`, which had gained `test_observation_path_confinement.py` and `test_projection_transition_runner.py` in the same checkpoint without the assertion following.
- Reproduce with `python scripts/qualify_observation.py checkout --path <dir>`, then run pytest with `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=<dir> AETHER_EXACT_HERMES_CHECKOUT=<dir>`.

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
