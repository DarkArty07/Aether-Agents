# HLP-226 cross-board Project inheritance recurrence

## Status and authority

This objective is the next owner-authorized bug-remediation objective under
[`specs/followup-aether-bugs/continuation.md`](../followup-aether-bugs/continuation.md).
GitHub issue [#226](https://github.com/DarkArty07/Aether-Agents/issues/226) is the
existing canonical defect issue; no duplicate tracker is applicable. This specification
narrows the reopened recurrence. It does not amend an earlier finalized Objective Contract
or authorize a feature, runtime activation, release, deployment, settings change, credential
change, provider/model change, history rewrite, or work on #275.

## Problem and observed baseline

HLP-226 and HLP-226b preserve a canonical Hermes Project when a worker creates a fresh
cross-profile worktree from either a direct Project worktree card or a same-board terminal
Supervisor sharing that root. A later superseding-contract flow exposed a third shape:

1. the current board's trusted Supervisor root already persisted its Project and session
   affinity;
2. it intentionally used `workspace_kind="dir"` to share a canonical worktree created for
   an earlier board;
3. the shared path's `.worktrees/<task-id>` leaf therefore did not name a task in the current
   board; and
4. the Supervisor profile had no matching entry in its profile-local Projects registry.

Creating the required same-affinity terminal Supervisor then failed with
`session-affinity tasks require a canonical project_id`. The existing fallback interpreted
that path leaf as a current-board task anchor, failed to find it, discarded the Project
already stored on the source row, and reached affinity validation with no Project.

The recurrence is independently reproducible against maintained fork
`DarkArty07/aether-hermes@415056fee527c5a2302370bd6dba56f84b9a4202`. Current upstream
`NousResearch/hermes-agent@67764dc0863349a384c16425e73ee8571f3a94b7` retains only the
direct-worktree source fallback and has no equivalent cross-board/shared-directory repair.
Pre-dispatch evidence is recorded in [`evidence/HLP-226C.md`](evidence/HLP-226C.md).

## User-visible outcome

A project-bound Supervisor flow can continue across a superseding Objective Contract board:
the trusted root can create its same-flow terminal Supervisor, and that terminal can create a
fresh cross-profile Implementer worktree, without manual workspace paths or a duplicate
Project registration in the worker profile. Invalid or conflicting directory sources remain
fail-closed.

## Requirements

### H226C-FR-001 — Board-bound Project recovery

When all of the following are true, Project recovery MUST use the current board's canonical
Project/repository binding rather than require the shared worktree leaf to name a task in the
current board:

- the creating worker's source task exists in the current board and already carries the
  requested Project;
- the source task carries session affinity and an absolute `dir` workspace of the form
  `<repo>/.worktrees/<leaf>`;
- the current board metadata carries the same Hermes Project and a `default_workdir` that
  resolves to `<repo>`; and
- the native same-assignee/same-flow affinity checks accept the requested child.

The `<leaf>` is opaque for this recovery. It MAY name a root task in a prior board and MUST
NOT be required to resolve in the current board. Recovery MUST NOT open or copy another
profile's Projects registry.

### H226C-FR-002 — Terminal continuity

From the H226C-FR-001 source, `kanban_create` of the explicit same-affinity terminal
Supervisor MUST succeed through the native API. The child MUST retain the exact Project,
share the exact existing workspace as `workspace_kind="dir"`, retain the exact flow with
`terminal=true`, and preserve native parent gating and origin/session provenance.

### H226C-FR-003 — Fresh cross-profile worktree continuation

From that terminal Supervisor, a child assigned to Implementer with a fresh worktree request
MUST retain the same Project and receive its own canonical task-id-keyed worktree path and
deterministic project branch. The worktree MUST materialize and be usable through the native
dispatch workspace resolver. No literal parent workspace is reused for this cross-profile
child.

### H226C-FR-004 — Fail-closed preservation

No Project/repository recovery is allowed when any material identity relation is absent or
conflicts. Tests MUST cover at least:

- board Project differs from the source/requested Project;
- board `default_workdir` does not equal the repository containing the shared worktree;
- `dir` is not an absolute `<repo>/.worktrees/<leaf>` path;
- source task Project is absent or conflicting;
- requested affinity differs by flow or assignee; and
- an explicit conflicting Project is supplied.

Failure MUST use existing native validation/error behavior and MUST NOT persist a child with
a fabricated, conflicting, or silently downgraded Project. Existing direct HLP-226,
same-board HLP-226b, ordinary scratch, and non-affinity task behavior MUST remain unchanged.

### H226C-FR-005 — Maintained-fork and Aether reconciliation

The corrected behavior MUST land in the maintained fork from the exact inspected baseline,
with focused tests and independent review. Aether MUST record the fork commit, upstream
difference, patch/compatibility disposition, rollback, retirement gate, and reproducible
qualification in its existing Hermes patch registry and evidence surfaces. Portable patch
bytes and reconciliation manifests MUST match the integrated fork source exactly where the
current Aether policy requires them.

### H226C-FR-006 — No activation or unrelated mutation

The objective MUST NOT mutate the loaded dirty editable runtime, restart/reload Hermes,
activate the patch, change profiles/configuration/models/providers/credentials/settings, or
alter unrelated boards/tasks/worktrees. The failed historical cards and disconnected probes
remain evidence and are not deleted. #275, Telegram Monitor #367, documentation #368, and
unrelated open bugs are outside this objective.

## Representative scenarios

1. **Normal recurrence:** empty Supervisor Projects registry; current board metadata binds
   Project P to repository R; current root P uses `R/.worktrees/<prior-board-id>` as a shared
   `dir`; same-flow terminal creation succeeds with P and the shared workspace.
2. **End-to-end continuation:** the terminal creates an Implementer child; the child obtains
   P, `R/.worktrees/<child-id>`, a deterministic branch, and a real materialized checkout.
3. **Board mismatch:** source P on a board bound to Q is rejected; no child with P or Q is
   silently substituted.
4. **Path mismatch:** source P uses a `dir` outside the board repository's `.worktrees`
   directory; recovery is rejected.
5. **Regression preservation:** direct cross-profile worktree inheritance and the original
   same-board terminal-root case continue to pass.

## Preservation and exclusions

Preserve task lineage, affinity ownership, dependency gating, task status, Project isolation,
per-task worktree isolation, source repository bytes, unrelated runtime state, prior patch
history, and public-artifact privacy. Do not generalize cross-board task lookup, introduce a
new global Project registry, weaken the explicit conflicting-Project rejection, or treat a
path-shaped string alone as authority.
