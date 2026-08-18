# R8 Specification: Workspaces, Git, and Integration

**Roadmap ID**: R8
**Stage status**: in-progress
**Decision authority**: Christopher
**Autonomous design delegate for this stage**: Hermes
**Future role owner**: Supervisor
**Depends on**: R2, R5, R7, `DESIGN.md`
**May affect**: R9, R10, R11, R13
**Parent roadmap**: `../../ROADMAP.md`
**Hermes evidence**: version 0.20.1, revision `411903b6fa258f81afcc3869eb615f6218e1776a`, source `home/.venv-hermes/src/hermes-agent`

## 1. Purpose

R8 decides where work physically happens, where the contract physically lives, how parallel work becomes one integrated result, and how any of it is undone.

The stage carries one problem that R5 created and did not close: `tasks.md` was made the breakdown of record while implementation was moved into a worktree per card. Nothing said which tree holds the authoritative copy, and left implicit it would have made the contract's own record the most-contended file in the repository.

R8 does not choose retention (R9), design enforcement (R10), define evidence format (R11), or select models (R12).

## 2. Workspace Kinds

The runtime provides three workspace kinds. Aether uses each for exactly one purpose.

| Aether work | Workspace kind | Lifetime |
|---|---|---|
| Implementing a unit | A git worktree per card | Preserved |
| Working on an existing project in place | An absolute directory path | Preserved |
| Decision cards, analysis, decomposition | Ephemeral scratch | Deleted on completion |

- **FR-801**: Implementation units MUST run in a per-card git worktree, so concurrent workers never share a working tree (PD-31).
- **FR-802**: A directory workspace MUST be an absolute path. Relative paths are rejected at dispatch as a confused-deputy vector, and Aether MUST NOT work around that rejection.
- **FR-803**: A unit whose workspace is ephemeral MUST declare its deliverables explicitly at completion, or they are destroyed with the workspace.
- **FR-804**: Decision cards (R7 §5) SHOULD use ephemeral workspaces. Their product is a decision recorded in the completion summary, not a file.

## 3. Where the Contract Lives — and Who May Write It

Spec Kit's artifacts live inside the project being built, which means they are versioned alongside the code they govern. That is correct and Aether keeps it. The problem is concurrency, not location.

The resolution is a writer rule, not a new mechanism:

| Artifact | Writer | Readers |
|---|---|---|
| `constitution.md` | Morfeo, on owner authority | All roles |
| `spec.md`, `plan.md` | Morfeo only | Supervisor |
| `tasks.md` | Supervisor only | Supervisor |
| Source and tests | Implementers, in their own worktree | All roles |

- **FR-805**: Contract artifacts MUST be written only on the integration branch, by the role that owns them. No implementer worktree ever modifies a contract artifact.
- **FR-806**: An implementer MUST NOT read `tasks.md` to understand its work. Its card body carries every decision it depends on (R7-FR-704), and the copy in its worktree is a point-in-time snapshot that may already be stale.
- **FR-807**: Because no implementer writes a contract artifact, merging implementer branches MUST NOT produce contract-artifact conflicts. If one occurs, it is evidence that FR-805 was violated, not a merge problem to resolve.
- **FR-808**: Appending remaining work to `tasks.md` during convergence MUST happen on the integration branch, and each appended unit MUST be materialised as a new card (PD-34).

## 4. Branches

- **FR-809**: Each implementation card MUST have its own branch. The runtime derives a deterministic branch name per card; Aether MUST use that derivation rather than inventing a naming scheme it would then have to keep in sync.
- **FR-809a**: The derivation was observed directly: a unit dispatched with an explicit worktree path produced the branch `wt/<task-id>`, in its own directory, based on the same commit as its siblings. A project-linked unit is documented to produce a project-scoped form, which has not been exercised. Aether MUST NOT hard-code either form.
- **FR-810**: A worker MUST NOT commit to, rebase, or force-push any branch other than its own.
- **FR-811**: Force-pushing MUST NOT occur on any shared branch under any circumstance. A correction is a new commit.
- **FR-812**: A branch MUST be preserved after its card completes. It is the evidence trail for that unit and the only way a merged unit can be inspected in isolation later.

## 5. Integration

- **FR-813**: Integration MUST be performed by the supervising role (R1-FR-126). An implementer never integrates its own work.
- **FR-814**: Integration MUST be materialised as its own card, gated on every unit it integrates, so it cannot start before its inputs exist.
- **FR-815**: Integration order MUST follow the dependency graph, not completion order. Two units that completed in an arbitrary order do not thereby acquire an integration order.
- **FR-816**: Each unit MUST enter the integration branch as its **own** commit or merge commit. Units MUST NOT be combined into one integration commit, because that would destroy the per-unit reversibility R1-FR-126 requires.
- **FR-817**: Integration MUST run the project's verification before the integrated result is declared done, and the result of that run is evidence (R11).
- **FR-818**: A conflict between two units MUST NOT be adjudicated by either author. It is resolved by a reconciliation card whose parents are both conflicting cards, executed by a fresh worker that produced neither side (PD-31).
- **FR-819**: A reconciliation card MAY carry a stronger model and a pinned reconciliation procedure. Neither creates a new role (PD-33).

## 6. Reversibility

Reversibility replaces the confirmation gate the owner removed. It carries the weight that approval would otherwise carry.

- **FR-820**: Every integrated unit MUST be individually revertible after the fact, with history preserved.
- **FR-821**: History MUST NOT be rewritten on the integration branch. Squashing several units together, amending merged commits, and force-pushing are all prohibited because each destroys FR-820.
- **FR-822**: A revert MUST be a new commit, so the record shows both the change and its withdrawal.
- **FR-823**: An effect that cannot be reverted by a commit — a published release, a deployment, a destructive migration, an external write — MUST be identified in advance and constrained by R10. It MUST NOT be discovered at the moment it is performed.

## 7. Publication

Aether maintains the project end to end and the normal path contains no confirmation gate (PD-15). That authority is real but bounded.

- **FR-824**: Publication actions — pushing, opening a pull request, tagging, releasing, deploying — MUST be performed by the supervising role as part of integration, never by an implementer.
- **FR-825**: Publication MUST stay inside the authority the contract conferred (R2-FR-205). Absence of a stated limit is not permission for an irreversible effect; FR-823 governs.
- **FR-826**: When a pull request already exists for a unit, the runtime refuses to respawn that unit. Aether MUST treat that refusal as correct behaviour and MUST NOT defeat it by creating a duplicate card for the same unit.
- **FR-827**: Credentials MUST be the ones the owner already provisioned on that profile. No role acquires, creates, or widens access (R1-FR-114).

## 8. Brownfield

- **FR-828**: For an existing project, the brownfield boundary MUST be stated in the contract in advance: conventions to follow, areas not to touch, tests that must keep passing (R2-FR-208).
- **FR-829**: Established conventions in the existing project MUST outrank both the owner's general preference and any agent's preference (R3-FR-308).
- **FR-830**: A change outside the stated boundary MUST be surfaced as a question in the end-of-work report, and MUST NOT be silently kept or silently reverted (PD-16).

## 9. Evidence

From direct inspection at the recorded revision:

- The board provides three workspace kinds; worktree and directory workspaces are preserved on completion, scratch is deleted with declared deliverables copied out first.
- A directory workspace must be absolute; relative paths are rejected at dispatch.
- A per-card worktree path and a deterministic per-card branch name are provided to the worker through its environment.
- The dispatcher refuses to respawn a unit when a recent comment links a pull request.

**Verified by execution** in the pass recorded in [`../r13-synthesis-and-release/research.md`](../r13-synthesis-and-release/research.md): dispatching three worktree-backed units against a scratch repository created separate directories on separate branches from the same base commit. Two concurrent units genuinely do not share a working tree.

Still assumed: the respawn guard's behaviour in a live run.

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

## 12. Done When

- [x] Each workspace kind is assigned exactly one purpose.
- [x] The contract's physical location and its writer rule are decided, closing the gap R5 left.
- [x] Branch ownership and the prohibition on rewriting shared history are stated.
- [x] Integration is assigned, ordered, and made per-unit revertible.
- [x] Publication authority is bounded without adding a confirmation gate.
- [x] The brownfield boundary is carried into execution.
- [ ] Christopher has reviewed the stage.
- [ ] Remote terminal backends are re-read if one is ever adopted.
