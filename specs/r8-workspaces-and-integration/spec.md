# R8 Specification: Workspaces, Git, and Integration

**Roadmap ID**: R8
**Stage status**: done — reconciled 2026-08-21 for PD-52, PD-62, PD-67, and A1 public project isolation
**Accepted**: 2026-08-17 — Christopher accepted the R4–R13 Decision Review
**Amended**: 2026-08-18 — direct PD-44 workspace, Git, and publication rules
**Decision authority**: Christopher
**Autonomous design delegate for this stage**: Hermes
**Future role owner**: Supervisor
**Depends on**: R2, R5, R7, `DESIGN.md`
**May affect**: R9, R10, R11, R13
**Parent roadmap**: `../../ROADMAP.md`
**Selected Hermes baseline**: `NousResearch/hermes-agent` `v2026.8.18`, commit `e624e9fde561e1add9388384012b295fde669ade`, distribution version `0.20.4`

## 1. Purpose

R8 decides where work physically happens, where the contract physically lives, how parallel work becomes one integrated result, and how any of it is undone.

The stage carries one problem that R5 created and did not close: `tasks.md` was made the breakdown of record while implementation was moved into a worktree per card. Nothing said which tree holds the authoritative copy, and left implicit it would have made the contract's own record the most-contended file in the repository.

R8 does not choose retention (R9), design enforcement (R10), define evidence format (R11), or select models (R12).

## 2. Workspace Kinds

The runtime provides three workspace kinds. Aether uses each for exactly one purpose.

| Aether work | Workspace kind | Lifetime |
|---|---|---|
| Implementing a unit | A git worktree per card | Preserved |
| Morfeo direct stewardship | The existing managed project workspace | Preserved; no false implementation card |
| Morfeo canonical authoring for a board task | That exact task's linked worktree under PD-67 | Preserved through review and integration |
| Working on an existing project in place | An absolute directory path | Preserved |
| Decision cards, analysis, decomposition | Ephemeral scratch | Deleted on completion |

- **FR-801**: Implementation units MUST run in a per-card git worktree, so concurrent workers never share a working tree (PD-31).
- **FR-802**: A directory workspace MUST be an absolute path. Relative paths are rejected at dispatch as a confused-deputy vector, and Aether MUST NOT work around that rejection.
- **FR-803**: A unit whose workspace is ephemeral MUST declare its deliverables explicitly at completion, or they are destroyed with the workspace.
- **FR-804**: Decision cards (R7 §5) SHOULD use ephemeral workspaces. Their product is a decision recorded in the completion summary, not a file.
- **FR-804a**: A direct PD-44 action MUST use the managed project workspace in Morfeo's current context and follow that project's established Git/workspace conventions. It MUST NOT create a worktree or implementation card solely to imitate pipeline mechanics.
- **FR-804b**: The public product MUST install sanitized, package-owned profile/policy resources into Aether-owned XDG state. It MUST NOT reproduce a private installation by copying ignored live profiles, `.env`, credentials, sessions, databases, memories, tokens, or other private runtime state into a worker workspace.
- **FR-804c**: The selected upstream `0.20.4` tag still persists a derived worktree branch and then spawns the stale claimed object (`hermes_cli/kanban_db.py:10230-10265`), so the first spawn can omit `HERMES_KANBAN_BRANCH`. Aether issue `#198` is closed for the loaded local repair, but that does not make the selected public tag conforming. The transitional fork carries the patch until the exact ready/review first-spawn matrix passes on an upstream release. No deliberate failed first attempt, database edit, global branch variable, hook weakening, or branchless directory worker is permitted.
- **FR-804d**: Aether initialization MUST reuse Hermes's first-class Project and board binding. Aether owns portable project identity and the local mapping to a Hermes Project/board; Hermes owns task workspace creation and branch derivation.

## 3. Where the Contract Lives — and Who May Write It

Spec Kit's artifacts live inside the project being built, which means they are versioned alongside the code they govern. That is correct and Aether keeps it. The problem is concurrency, not location.

The resolution is a writer rule, not a new mechanism:

| Artifact | Writer | Readers |
|---|---|---|
| `constitution.md` | Morfeo, on owner authority | All roles |
| `spec.md`, `plan.md` | Morfeo only | Supervisor |
| `tasks.md` | Supervisor only | Supervisor |
| Source and tests in pipeline work | Implementers, in their own worktree | All roles |
| Bounded direct operational change | Morfeo, in the managed project workspace | Owner; relevant later roles if the work changes route |

- **FR-805**: Contract artifacts MUST be written only by the role that owns them. Morfeo may author `constitution.md`, `spec.md`, and `plan.md` either in the launcher-bound integration checkout or in the exact linked worktree of an active, board-verifiable Morfeo task under PD-67. Supervisor alone owns `tasks.md`. An Implementer never modifies any contract artifact. General project-file mutation by Morfeo during direct PD-44 work is not a contract-ownership violation.
- **FR-805a**: Task-bound Morfeo contract authorization MUST match the explicitly pinned board, task, task-owned run, Morfeo assignee, active state, `workspace_kind=worktree`, workspace, project root, branch, and absolute target path. Missing or conflicting identity fails closed.
- **FR-805b**: Task-bound contract writes MUST use native structured file operations. Shell, terminal, and code-execution paths are not authorized to mutate canonical contracts. The candidate remains non-canonical until independently reviewed and integrated into the integration branch.
- **FR-806**: An implementer MUST NOT read `tasks.md` to understand its work. Its card body carries every decision it depends on (R7-FR-704), and the copy in its worktree is a point-in-time snapshot that may already be stale.
- **FR-807**: Because no implementer writes a contract artifact, merging implementer branches MUST NOT produce contract-artifact conflicts. If one occurs, it is evidence that FR-805 was violated, not a merge problem to resolve.
- **FR-808**: Appending remaining work to `tasks.md` during convergence MUST happen on the integration branch, and each appended unit MUST be materialised as a new card (PD-34).

## 4. Branches

- **FR-809**: Each implementation card MUST have its own branch. The runtime derives a deterministic branch name per card; Aether MUST use that derivation rather than inventing a naming scheme it would then have to keep in sync.
- **FR-809a**: The selected Hermes source verifies both fallback and project-linked branch paths. `tests/hermes_cli/test_kanban_project_link.py:29-64` proves project-linked tasks use a deterministic project-scoped worktree and branch; unlinked tasks retain the fallback behavior. Aether MUST NOT hard-code either form.
- **FR-809b**: A project-linked task MUST inherit the board's project unless an explicit, valid project binding overrides it; this uses the native board-project contract verified by `tests/hermes_cli/test_kanban_board_project.py:40-87`.
- **FR-810**: A worker MUST NOT commit to, rebase, or force-push any branch other than its own.
- **FR-811**: Force-pushing MUST NOT occur on any shared branch under any circumstance. A correction is a new commit.
- **FR-812**: A branch MUST be preserved after its card completes. It is the evidence trail for that unit and the only way a merged unit can be inspected in isolation later.

## 5. Integration

This section governs pipeline work only. A direct PD-44 action has no delegated branches to integrate; Morfeo owns the bounded change and its verification.

- **FR-813**: Integration MUST be performed by the supervising role (R1-FR-126). An implementer never integrates its own work.
- **FR-814**: Integration MUST be materialised as its own card, gated on every unit it integrates, so it cannot start before its inputs exist.
- **FR-815**: Integration order MUST follow the dependency graph, not completion order. Two units that completed in an arbitrary order do not thereby acquire an integration order.
- **FR-816**: Each unit MUST enter the integration branch as its **own** commit or merge commit. Units MUST NOT be combined into one integration commit, because that would destroy the per-unit reversibility R1-FR-126 requires.
- **FR-817**: Integration MUST run the project's verification before the integrated result is declared done, and the result of that run is evidence (R11).
- **FR-817a**: Each converged story MUST yield an **independently runnable** increment. Integration order (FR-815) and one commit per unit (FR-816) preserve reversibility; this preserves deliverability — the increment for one story MUST be runnable without the sibling stories it was decomposed alongside (R3 §6).
- **FR-818**: A conflict between two units MUST NOT be adjudicated by either author. It is resolved by a reconciliation card whose parents are both conflicting cards, executed by a fresh worker that produced neither side (PD-31).
- **FR-819**: A reconciliation card MAY carry a stronger model and a pinned reconciliation procedure. Neither creates a new role (PD-33).
- **FR-819a**: A direct action MUST NOT create a fake integration card. If the objective grows until independent integration or review adds material value, Morfeo changes route before expanding the work.
- **FR-819b**: For the FR-804b ignored-state case, Supervisor integration MUST be byte-for-byte or reviewed-diff application of the approved candidate after independent review; it MUST NOT add, redesign, or “fix” content during application. The candidate worktree and baseline evidence remain preserved until the owner completes any deferred manual validation.

## 6. Reversibility

Reversibility replaces the confirmation gate the owner removed. It carries the weight that approval would otherwise carry.

- **FR-820**: Every integrated unit MUST be individually revertible after the fact, with history preserved.
- **FR-821**: History MUST NOT be rewritten on the integration branch. Squashing several units together, amending merged commits, and force-pushing are all prohibited because each destroys FR-820.
- **FR-822**: A revert MUST be a new commit, so the record shows both the change and its withdrawal.
- **FR-823**: An effect that cannot be reverted by a commit — a published release, a deployment, a destructive migration, an external write — MUST be identified in advance and constrained by R10. It MUST NOT be discovered at the moment it is performed.
- **FR-823a**: Morfeo MUST preserve a practical rollback for direct work when Git applies, using the project's ordinary diff, commit, revert, or restore mechanics as authorized and appropriate. Terminal capability alone does not authorize rewriting history, discarding unknown work, or committing or publishing when the current objective does not confer that authority.

## 7. Publication

Aether maintains the project end to end and the normal path contains no confirmation gate (PD-15). That authority is real but bounded.

- **FR-824**: Pipeline publication actions — pushing, opening a pull request, tagging, releasing, deploying, uploading packages, changing repository settings, or publishing Pages/announcements — MUST be performed by the supervising role as part of integration and only behind the contract's explicit external gate, never by an implementer. For direct PD-44 work, Morfeo MAY perform one only when the current instruction already authorizes that exact effect; technical access is not publication authority.
- **FR-825**: Publication MUST stay inside the authority the contract conferred (R2-FR-205). Absence of a stated limit is not permission for an irreversible effect; FR-823 governs.
- **FR-826**: When a pull request already exists for a unit, the runtime refuses to respawn that unit. Aether MUST treat that refusal as correct behaviour and MUST NOT defeat it by creating a duplicate card for the same unit.
- **FR-827**: Credentials MUST be the ones the owner already provisioned on that profile. No role acquires, creates, or widens access (R1-FR-114).

## 8. Brownfield

- **FR-828**: For an existing project, the brownfield boundary MUST be stated in the contract in advance: conventions to follow, areas not to touch, tests that must keep passing (R2-FR-208).
- **FR-829**: Established conventions in the existing project MUST outrank both the owner's general preference and any agent's preference (R3-FR-308).
- **FR-830**: A change outside the stated boundary MUST be surfaced as a question in the end-of-work report, and MUST NOT be silently kept or silently reverted (PD-16).

## 9. Evidence

From direct inspection at selected commit `e624e9f…`:

- `hermes_cli/kanban_db.py:102-135,3238-3246` defines the three workspace kinds and rejects invalid branch/workspace combinations; directory paths are required to be absolute at dispatch.
- `hermes_cli/projects_db.py:1-21,57-96` stores first-class Projects per profile while boards remain shared; `projects_cmd.py:22-104` exposes project and board binding operations.
- `tests/hermes_cli/test_kanban_project_link.py:29-64` and `test_kanban_board_project.py:40-87` verify deterministic project-linked worktrees/branches and board-project inheritance.
- `kanban_db.py:10230-10265` confirms the selected tag still has the first-spawn branch propagation defect, which is why A1 begins in transitional-fork mode.

**Verified by execution** in the pass recorded in [`../r13-synthesis-and-release/research.md`](../r13-synthesis-and-release/research.md): dispatching three worktree-backed units against a scratch repository created separate directories on separate branches from the same base commit. Two concurrent units genuinely do not share a working tree.

Still assumed for the public release: respawn-guard behavior and every first-spawn branch path until exercised against the exact locked artifact.

Not inspected: the terminal backends. Aether's design assumes local execution; a remote backend would change the meaning of every absolute path in this specification and MUST be re-read before one is adopted.

## 10. Requirements Inherited by Later Stages

| Requirement | Owner |
|---|---|
| Preserved worktrees and branches accumulate without bound and need retention | R9 |
| Irreversible effects must be enumerated and gated by enforcement, not instruction | R10 |
| Contract-artifact writes must be restricted to their owning role | R10 |
| Integration verification output is acceptance evidence | R11 |
| A reconciliation card may carry a stronger model | R12 |

## 11. Success Criteria

- **SC-801**: Two concurrent implementers never share a working tree.
- **SC-802**: No merge conflict ever occurs in a contract artifact.
- **SC-803**: Every integrated unit can be reverted individually, after the fact, without touching its siblings.
- **SC-804**: No history is rewritten on the integration branch.
- **SC-805**: Every conflict is resolved by a worker that authored neither side.
- **SC-806**: Every irreversible effect performed was identified in advance.
- **SC-807**: An out-of-boundary change in an existing project appears as a question, not as a silent edit.
- **SC-808**: A direct Morfeo change is inspectable and practically reversible without a false worktree, implementation card, or integration card, and no publication occurs merely because terminal access exists.
- **SC-809**: Task-bound Morfeo contract authoring succeeds only for exact board/run/workspace/branch identity through structured file tools; all listed negative controls remain denied.
- **SC-810**: Project initialization reuses native Hermes Project/board/worktree behavior and does not create a parallel coordination store.

## 12. Done When

- [x] Each workspace kind is assigned exactly one purpose.
- [x] The contract's physical location and its writer rule are decided, closing the gap R5 left.
- [x] Branch ownership and the prohibition on rewriting shared history are stated.
- [x] Integration is assigned, ordered, and made per-unit revertible.
- [x] Publication authority is bounded without adding a confirmation gate.
- [x] The brownfield boundary is carried into execution.
- [x] Public project identity, native Hermes Project adaptation, and PD-67 task-bound canonical authoring are reconciled.
- [x] Christopher has reviewed the stage (R4–R13 Decision Review, 2026-08-17).
- [ ] Remote terminal backends are re-read if one is ever adopted.
