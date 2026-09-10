# HLP-226C evidence

## Pre-dispatch inspection

Evidence below is inspection/reproduction by Morfeo, not implementation or independent
Supervisor review.

| Criterion/question | Artifact and revision | Check and producer | Result/limit |
| --- | --- | --- | --- |
| Does the reported recurrence still exist? | `DarkArty07/aether-hermes@415056fee527c5a2302370bd6dba56f84b9a4202`; `hermes_cli/kanban_db.py`, `tools/kanban_tools.py` | Direct disposable two-profile/current-board reproduction by Morfeo | Reproduced. A Project-bearing nonterminal Supervisor `dir` source at `<repo>/.worktrees/<prior-board-id>`, with the leaf absent from the current board and zero Projects in the Supervisor profile, returned `kanban_create: session-affinity tasks require a canonical project_id` when creating the same-flow terminal. |
| Is the existing HLP-226b condition the cause? | Same fork revision; Project source fallback in `hermes_cli/kanban_db.py` | Direct source inspection by Morfeo | Yes. The fallback looks up the workspace leaf as a task in the already-open board and accepts the source only after obtaining a `workspace_kind="worktree"` anchor. A prior-board leaf is absent, leaving the current `dir` source ineligible and dropping Project before affinity validation. |
| Does current upstream already provide an equivalent fix? | `NousResearch/hermes-agent@67764dc0863349a384c16425e73ee8571f3a94b7`; `_project_from_source_task` and `kanban_create` handler | Direct fetched-source inspection and GitHub issue/PR search by Morfeo | No equivalent found. Current upstream accepts only a source task that itself is a canonical task-id-keyed `worktree`; it contains no same-flow terminal/shared-`dir` behavior. Search found no open matching upstream issue/PR. Limit: absence is proven for the inspected revision/search, not all future upstream history. |
| Is board metadata sufficient to identify the intended repository without cross-board task lookup? | Aether `src/aether_agents/objective_contracts/hermes_plugin.py`; fork `hermes_cli/kanban_db.py` | Direct source inspection by Morfeo | The execution board durably carries the Hermes Project id and `default_workdir`; native task creation already inherits the board Project and uses `default_workdir` for persistent workspace defaults. The selected design requires both fields to match the source Project and the repository containing the shared `.worktrees/<leaf>` path. |
| Is another active owner already implementing #226? | GitHub issue/PR state, active Kanban board titles, fork open PRs | Direct read-only inspection by Morfeo | No visible open Aether/fork PR or active board card matched #226 at dispatch design time. Issue #226 is open/reopened and unassigned. |

## Design self-check

A cold read of `spec.md`, `plan.md`, and `quickstart.md` fixes the material authority source,
positive lifecycle, cross-profile worktree outcome, negative matrix, exact implementation and
upstream baselines, reconciliation surfaces, test path, release disposition, and no-activation
boundary. Supervisor still owns decomposition, independent receipt review, unit sequencing,
integration, and proportionate adaptation to exact current test-file names. Implementers retain
private helper/fixture choices that preserve the stated invariants.

## Pipeline result reception

Supervisor/Implementer evidence is appended here after delivery. No pre-dispatch statement
below this heading is a claim that implementation, review, merge, activation, or objective
acceptance occurred.
