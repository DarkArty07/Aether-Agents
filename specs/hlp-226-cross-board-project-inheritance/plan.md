# Technical plan — HLP-226 cross-board Project inheritance

## Route and inspected baseline

**Route: pipeline.** The complete objective crosses the maintained Hermes fork and Aether's
patch/reconciliation surface, and it changes a coordination/security guarantee: which durable
state may recover a Project when the creating profile cannot resolve it locally. Independent
review adds concrete value by checking that the new positive case cannot turn an arbitrary
`dir` path into Project authority.

Implementation target: clean isolated source based on
`DarkArty07/aether-hermes@415056fee527c5a2302370bd6dba56f84b9a4202`, followed by Aether
integration based on the Objective Contract's recorded base. The currently loaded editable
runtime was observed dirty and behind the remote fork and is evidence only; it is not an
implementation workspace.

## Decided design

| Decision | Approved choice and reason | Evidence/assumption | Verification | Local freedom |
| --- | --- | --- | --- | --- |
| Recovery authority | Combine the current source task's stored Project/affinity with the current board metadata's matching `project_id` and `default_workdir`. Do not require the `.worktrees/<leaf>` to be a task in this board. | Native board creation already uses these fields as the board's Project/repository binding; the observed recurrence is specifically a prior-board leaf. | H226C-FR-001/004 matrix and disposable E2E. | Helper extraction, naming, and internal control flow are Implementer choices. |
| Repository identity | Accept only when the source shared path resolves beneath `<default_workdir>/.worktrees/` with exactly one opaque leaf; derive the repository from the board binding, not the leaf. | Prevents an arbitrary `dir` from becoming authority while supporting a prior-board root id. | Mismatch, traversal/symlink-equivalence as applicable, and outside-directory negatives. | Equivalent safe path comparison is local judgement; it must not trust string prefix matching. |
| Affinity continuity | Retain native tool-layer same-assignee/same-flow checks and DB parent-affinity validation. Recovery supplies Project identity; it does not redefine who may join a flow. | The failing path loses Project before existing affinity validation. | Same-flow terminal positive plus flow/assignee conflicts. | Existing private helper boundaries may be reorganized. |
| Cross-profile continuation | Same-affinity Supervisor terminal shares the root workspace; an Implementer child receives a fresh task-keyed worktree and deterministic branch. | Existing HLP-226/HLP-226b guarantees must compose with the new case. | Two-step disposable E2E including actual worktree materialization. | Exact temporary repository fixture layout is local. |
| Upstream relationship | Maintain a downstream patch. Current upstream at the inspected revision has no session-affinity/shared-directory equivalent. | Direct source inspection at `67764dc0863349a384c16425e73ee8571f3a94b7`. | Registry cites exact revision and retirement gate. | Later upstream comparison may update only with newly inspected evidence. |
| Runtime effect | No activation/reload in this objective. | Owner continuation excludes live activation and loaded source is shared dirty state. | Git/status/runtime audit. | None. |

## Component responsibilities

### Maintained Hermes fork

The Project-resolution path in `hermes_cli/kanban_db.py` owns reconstruction from the source
task and board metadata. The `kanban_create` tool in `tools/kanban_tools.py` owns propagating
the current task as the trusted source and explicit board identity to task creation. Existing
native Project conflict and session-affinity checks remain the enforcement boundaries.

Tests in the existing Kanban tool/DB/session-affinity suites own the positive, negative, and
preservation matrix. The change should extend the existing resolver rather than introduce a
parallel Aether-only execution path.

### Aether repository

`HERMES_LOCAL_PATCHES.md`, the existing portable patch area, patch-reconciliation manifest,
qualification harness/tests, and this objective's evidence file own the downstream provenance
and reproducibility. Aether source must not depend on a new downstream-only public API; this
is qualification and packaging of the maintained foundation behavior.

Supervisor owns decomposition and integration sequencing. Implementers may choose equivalent
private helpers and fixture structure but may not change the recovery authority, path/security
invariants, or runtime activation boundary.

## Data and control flow

1. A worker calls native `kanban_create` from a current source task.
2. The tool validates assignee/flow ownership and carries the source task id and exact board
   selection into native task creation.
3. Native creation first attempts the worker profile's Projects registry.
4. If unresolved, it reads only the source task in the already-open board and the metadata of
   that exact board.
5. Matching Project + board repository + canonical shared-worktree containment produces a
   transient Project object/repository root for this creation; no registry is copied or
   mutated.
6. Existing child affinity/parent gates run. The task is inserted only if all checks succeed.
7. A cross-profile worktree child derives its own path and branch from the recovered
   repository; dispatcher materialization remains unchanged.

There is no new persisted schema, global lookup, cross-board task query, migration, daemon,
credential, or external service.

## Error and recovery behavior

Identity mismatch, malformed/noncanonical path, absent board binding, or affinity conflict
fails through the existing native error surface before persisting an invalid child. No
fallback to scratch or `project_id=null` is acceptable for a request carrying session
affinity. Non-affinity legacy behavior remains as currently specified.

Rollback is a normal revert of the fork change plus exact reversal/removal of the corresponding
Aether portable patch/reconciliation update. Rollback does not restore whole files, mutate
board databases, or remove historical evidence.

## Compatibility and release disposition

- `release_impact = patch`: compatible correction of an existing Project/affinity guarantee.
- `release_action = defer`: merge does not authorize package publication or live rollout.
- `release_channel = none`: no release is prepared or published.

## Rejected alternatives

- **Look up the prior-board task globally:** rejected because it expands board coupling and
  treats historical task availability as a runtime prerequisite.
- **Trust any Project-bearing `dir` source:** rejected because a task row plus arbitrary path
  is insufficient repository authority.
- **Copy/register the Project in every worker profile:** rejected because it widens mutable
  profile state and recreates the already-solved cross-profile coupling.
- **Pass a manual workspace or create a non-affinity terminal:** rejected because it bypasses
  the product guarantee instead of repairing it.
- **Mutate the loaded editable checkout directly:** rejected because it is shared, dirty, and
  not the exact remote implementation baseline.
