# R9 Specification: State, Artifacts, Memory, and Recovery

**Roadmap ID**: R9
**Stage status**: in-progress
**Decision authority**: Christopher
**Autonomous design delegate for this stage**: Morfeo
**Future role owner**: Morfeo
**Depends on**: R2, R5, R6, R7, R8, `DESIGN.md`
**May affect**: R10, R11, R12, R13
**Parent roadmap**: `../../ROADMAP.md`
**Hermes evidence**: version 0.20.1, revision `411903b6fa258f81afcc3869eb615f6218e1776a`, source `home/.venv-hermes/src/hermes-agent`

## 1. Purpose

R9 decides what Aether remembers, where each kind of state lives, what survives a failure, and what is thrown away.

Its governing constraint is that Aether builds no persistence. Three durable stores already exist and each already has a clear owner. R9's work is to keep them from overlapping, to decide what Morfeo is allowed to remember, and to say what is discarded and when.

R9 does not design enforcement (R10), define evidence content (R11), or select models (R12).

## 2. Three Stores, Three Owners

| Store | Owns | Lifetime |
|---|---|---|
| The project repository | The contract and the code it governs | Permanent, versioned |
| The board's durable rows | What was executed, by whom, in how many attempts, with what result | Permanent until retention removes it |
| Each profile's own home | That role's memory, sessions, skills, credentials | Per profile, never shared |

- **FR-901**: Aether MUST NOT create a fourth store. Any question about what happened is answered from the board; any question about what was asked for is answered from the repository.
- **FR-902**: Aether MUST NOT maintain a parallel record of execution. The board's rows, events, comments, and attempt records are the record (R5-FR-534).
- **FR-903**: The same fact MUST NOT be authoritative in two stores. Where a fact appears in both, the owning store wins and the other copy is a snapshot.
- **FR-904**: Two agent processes MUST NOT share a profile home (PD-27). Where roles need shared memory, an external memory provider MUST be used rather than a shared home.

## 3. Artifacts

- **FR-905**: The contract artifacts are versioned in the project repository and are the durable record of intent (R2-FR-201).
- **FR-906**: Files a human is meant to receive MUST be declared as deliverables at completion. Paths mentioned only in prose or in structured metadata are not collected and are destroyed with an ephemeral workspace.
- **FR-907**: Large or binary products MUST be attached to their card rather than pasted, linked from a temporary location, or left in a workspace that will be deleted.
- **FR-908**: Secrets, tokens, credentials, and raw personal data MUST NOT be written into completion summaries, structured metadata, comments, or attachments. Those fields are durable and are read by every downstream role.

## 4. Morfeo's Memory

Owner preferences are Aether's only personalization mechanism (PD-12, PD-22). Everything else is per project.

- **FR-909**: Morfeo MAY remember the owner's durable preferences and working style. It MUST NOT remember project-specific standards, which belong to that project's constitution (R3-FR-306).
- **FR-910**: A remembered preference MUST NOT override a current instruction and MUST NOT constitute a decision (R1-FR-129). Precedence is: current instruction, then artifact, then memory.
- **FR-911**: Morfeo's memory MUST be inspectable and deletable by the owner (R1-FR-130).
- **FR-912**: Morfeo MUST NOT record a preference inferred from a single instance. A preference is a pattern the owner confirmed or repeated, and an unconfirmed inference recorded as memory becomes an invented decision on the next contract.
- **FR-913**: Supervisor and implementer profiles MUST NOT accumulate owner-facing memory. They exist per unit of work and their durable output is the card, not their recollection.
- **FR-914**: A profile's automatic memory writing MUST be considered when profiles are configured, because an unattended role that writes memory on every run compounds state that nobody reviews.

## 5. Recovery

The unit of durability is the card, not the process. This is what makes unattended execution survivable and it supersedes the earlier finding that it could not be (PD-26 superseded by PD-29).

| Failure | Native handling | Cost |
|---|---|---|
| Worker crashes | Reclaimed, returned to its source phase | One attempt **and one failure tick** |
| Worker hangs without liveness signals | Reclaimed after the stale window | One attempt, no failure tick |
| Worker exits without completing or blocking | Nudged, bounded retry, then auto-blocked | Attempts, then a block |
| Repeated spawn failure | Auto-blocked with the last error | The unit waits |
| Gateway restarts | Dispatcher restarts with it and reclaims in-flight work | In-flight attempts |

- **FR-915**: A crash or restart MUST cost at most one attempt, never the unit of work.
- **FR-915a**: **A crash is not free.** Verified by execution: crash detection returns the unit to its source phase *and increments the consecutive-failure counter*, while a stale-claim reclaim does not. Environmental failure and defective work therefore consume the same budget, which is why R7-FR-738 sets the attempt limit above the number of environmental failures one unattended session can plausibly produce.
- **FR-915b**: Recovery MUST NOT be described as free anywhere in this repository. The unit survives; its tolerance does not.
- **FR-916**: A re-dispatched unit MUST receive its prior attempts, their outcomes, and the full comment thread, so it does not repeat a path that already failed.
- **FR-917**: An interrupted run whose side effects cannot be established MUST be reported as indeterminate, never as success or failure (R4-FR-416).
- **FR-918**: Recovery MUST NOT be assumed for effects outside the repository and the board. An external write performed before a crash is not undone by a reclaim, which is why R8-FR-823 requires irreversible effects to be identified in advance.
- **FR-919**: Aether MUST NOT implement its own reclaim, retry, or heartbeat mechanism (FR-503).

## 6. Retention

Every durable surface grows without bound by default. Retention is therefore a design decision, not an operational afterthought.

| Surface | Disposition |
|---|---|
| Contract artifacts and code | Permanent. Never pruned. |
| Card rows, comments, attempt records | Permanent by default; the acceptance record of the project |
| Board events | Pruned on a schedule; they are execution telemetry, not the record |
| Worker logs | Pruned on a schedule |
| Preserved worktrees | Pruned once the unit is integrated and its branch is preserved |
| Branches | Permanent. They are the per-unit evidence trail (R8-FR-812) |
| Attachments | Retained with their card |
| Notification subscriptions | Removed when the work they watch reaches its irreversible end state |

- **FR-920**: Retention MUST distinguish the acceptance record from execution telemetry. Rows and branches are the record; events, logs, and worktrees are telemetry and may be pruned.
- **FR-921**: A retention sweep MUST NOT remove anything an unfinished unit depends on. Pruning is only ever applied to terminal work.
- **FR-922**: Pruning worktrees MUST NOT remove the corresponding branch. The branch is what makes a merged unit inspectable later; the worktree is only a checkout of it.
- **FR-923**: Retention values are calibration, not architecture, and MUST be recorded when set.

## 7. Boards Are the Project Boundary

- **FR-924**: One board per project (R5-FR-510). A worker is pinned to its board at spawn and cannot see another.
- **FR-925**: Namespacing inside a board is a soft filter and MUST NOT be used as an isolation boundary between projects (R5-FR-511).
- **FR-926**: Cross-project references MUST NOT be expressed as links, which the runtime does not permit across boards. Where a relationship exists, it belongs in the contract.

## 8. Evidence

From direct inspection and execution at the recorded revision:

- The board's schema carries tasks, links, comments, events, attempt records, attachments, and notification subscriptions as separate durable tables.
- Attempt records are created even for units that were never claimed, so a completion or block always has an attempt row behind it. Observed: two attempt rows for a unit blocked twice, each carrying its reason.
- A re-dispatched unit's assembled context contains prior attempts, parent handoffs, and the full comment thread. Observed directly.
- Deliverables are collected only when declared at completion; other files in an ephemeral workspace are removed.
- Retention sweeps exist for events, logs, workspaces, and terminal-state subscriptions.

Not inspected: the memory provider internals and the board's full event reference. Neither carries an accepted decision here beyond the ownership boundaries stated above, and both are read by whoever configures them.

## 9. Requirements Inherited by Later Stages

| Requirement | Owner |
|---|---|
| Durable fields must never carry secrets; this needs enforcement, not only instruction | R10 |
| An external write is not recoverable by reclaim | R10 |
| Attempt records and completion evidence are the evidence base | R11 |
| Retention values are set once a real run shows the growth rate | R13 |

## 10. Success Criteria

- **SC-901**: No fact about what happened is authoritative anywhere except the board.
- **SC-902**: No fact about what was asked for is authoritative anywhere except the repository.
- **SC-903**: A crash during unattended work costs at most one attempt.
- **SC-904**: A re-dispatched unit never repeats a path that already failed in a recorded attempt.
- **SC-905**: Morfeo's memory contains only owner preferences, and the owner can read and delete all of it.
- **SC-906**: No durable field contains a secret.
- **SC-907**: Every merged unit remains individually inspectable after its worktree is pruned.

## 11. Done When

- [x] The three stores are separated with a single owner each.
- [x] Deliverable declaration and the destruction of undeclared files are specified.
- [x] Morfeo's memory is bounded to owner preferences, with a rule against inferring from one instance.
- [x] Recovery semantics and the cost of each failure are stated.
- [x] The indeterminate outcome is preserved for unprovable side effects.
- [x] Retention separates the acceptance record from execution telemetry.
- [ ] Christopher has reviewed the stage.
- [ ] Retention values are set from an observed growth rate.
