# R9 Specification: State, Artifacts, Memory, and Recovery

**Roadmap ID**: R9
**Stage status**: done — reconciled 2026-08-21 for PD-55, PD-62, PD-63, and A1 public recovery
**Accepted**: 2026-08-17 — Christopher accepted the R4–R13 Decision Review
**Amended**: 2026-08-18 — direct PD-44 actions distinguished from delegated board execution
**Amended**: 2026-09-04 — canonical skill domains and terminal residue retention reconciled
**Decision authority**: Christopher
**Autonomous design delegate for this stage**: Morfeo
**Future role owner**: Morfeo
**Depends on**: R2, R5, R6, R7, R8, `DESIGN.md`
**May affect**: R10, R11, R12, R13
**Parent roadmap**: `../../ROADMAP.md`
**Selected Hermes baseline**: `NousResearch/hermes-agent` `v2026.8.18`, commit `e624e9fde561e1add9388384012b295fde669ade`, distribution version `0.20.4`

## 1. Purpose

R9 decides what Aether remembers, where each kind of state lives, what survives a failure, and what is thrown away.

Its governing constraint is ownership, not an obsolete store count. The public manager needs product-owned XDG state for immutable releases, profiles, project mappings, transition journals, bounded contract-observation metadata, and safe recovery; it must not create a second authority for project intent or delegated execution.

R9 does not design enforcement (R10), define evidence content (R11), or select models (R12).

## 2. State Domains and Owners

| Store | Owns | Lifetime |
|---|---|---|
| The project repository | The contract and the code it governs | Permanent, versioned |
| The board's durable rows | What was delegated, by whom, in how many attempts, with what result | Permanent until retention removes it |
| Each profile's own home | That role's memory, sessions, learned profile skills, credentials | Per profile, never shared |
| Aether XDG product state | Installed releases, active-release record, sanitized product resources, project mappings, transition journals, backups, bounded contract-observation metadata/read models, and local redacted logs | Product-managed; user-preserving update/uninstall rules |

- **FR-901**: Aether MUST NOT create a second authoritative contract or execution store. Any question about delegated pipeline status is answered from the board; any question about what was accepted is answered from the repository. PD-68 permits a metadata-only contract journal and rebuildable summary projection for observation, but neither can alter or overrule those owning stores. A direct PD-44 action is evidenced by the project repository, actual tool output, and Morfeo's profile session, not by a manufactured card.
- **FR-902**: Aether MUST NOT maintain a parallel authority for delegated execution. The board's rows, events, comments, and attempt records are the pipeline record (R5-FR-534). The 002 observer may reference native task/run/session IDs and cache derived counts, but it MUST label them as projections and expose coverage gaps. Direct action MUST NOT manufacture a card merely to appear in that record.
- **FR-903**: The same fact MUST NOT be authoritative in two stores. Where a fact appears in both, the owning store wins and the other copy is a snapshot.
- **FR-904**: Two agent processes MUST NOT share a profile home (PD-27). Where roles need shared memory, an external memory provider MUST be used rather than a shared home.

### 2.1 Public XDG layout

All roots honor the corresponding `XDG_*_HOME` variable and fall back to the standard paths below:

```text
~/.config/aether/             # non-secret product choices and generated-service source/records
~/.local/share/aether/        # active.json, immutable releases, isolated runtimes, profiles, projects
~/.local/state/aether/        # transition journals, backups, observations, local redacted logs
~/.cache/aether/downloads/    # replaceable verified-download staging
```

Inside data, each immutable `releases/<aether-semver>/` owns its release lock, isolated Hermes runtime, and product-resource bundle. Persistent role profiles and `projects/<project-uuid>/` live outside release directories so update/rollback does not erase user state. A project's product state owns its board/workspace location and local mapping; portable identity remains in the project repository and contains no absolute machine path.

- **FR-904a**: `active.json` MUST be an atomic coherent-release record, never a partially updated set of independent pointers.
- **FR-904b**: Immutable release-owned artifacts MUST be separated from persistent user/profile/project state and from replaceable cache.
- **FR-904c**: Credentials remain in Hermes-supported installation-local stores. They MUST NOT enter setup files, release locks, backups intended for publication, project Git, or logs.

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

## 4.1 Canonical and learned skills

Skills are reusable procedure, never authority. Aether Canonical Skills are public,
versioned, package-owned procedures whose source files are
`src/aether_agents/resources/skills/<skill-name>/SKILL.md`. Project Canonical Skills are
tracked, versioned, project-visible procedures whose source files are
`.aether/skills/<skill-name>/SKILL.md`. Learned Profile Skills are private, local,
adaptive procedures held by one profile and never become canonical automatically.

- **FR-914a**: The frontmatter and body of each `SKILL.md` are its source. Aether MUST
  NOT add a duplicate skill registry, generic loader, queue, role, or state machine to
  make canonical procedures available.
- **FR-914b**: Authority precedence is current owner instruction → constitution/design/stage specs/Objective Contract → repository operating
  rules. Among compatible procedures only, a Project Canonical Skill is more specific
  than an Aether Canonical Skill, and both are more specific than a Learned Profile
  Skill. No skill can grant authority or replace intent or acceptance.
- **FR-914c**: Agents MUST discover project procedures through the current root
  `AGENTS.md`, direct project-relative reads, card pinning, or an existing native skill
  mechanism, and MUST load only procedures relevant to the current task. A project
  skill follows that project's repository visibility; a learned skill remains private
  and MUST NOT be copied into public artifacts.
- **FR-914d**: Promoting a Learned Profile Skill requires sanitization, generalization,
  verification, independent review, commit, and pull request. Learning alone MUST NOT
  promote a skill or change any role's authority.

## 5. Recovery

For delegated work, the unit of durability is the card, not the process. This is what makes unattended pipeline execution survivable and it supersedes the earlier finding that it could not be (PD-26 superseded by PD-29). A direct Morfeo action is bounded to the current session and relies on the managed project's ordinary reversibility; if work needs durable multi-attempt recovery, that is evidence that the pipeline adds value.

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
- **FR-919a**: Install, update, rollback, reconcile, and uninstall MUST use a transition journal and staging area. A failed transition leaves the previous coherent release active or an explicit recoverable mismatch; it MUST NOT leave mixed manager/runtime/profile-policy versions active.
- **FR-919b**: Before changing persistent Aether-owned profile/project state, the manager MUST create a safe metadata/state backup sufficient for rollback. It MUST NOT back up or restore an unrelated personal Hermes installation.
- **FR-919c**: `aether doctor` MUST detect external package-manager drift between CLI, active release, runtime, profiles, and lock. It MUST refuse incompatible activation and offer explicit reconciliation or rollback; it MUST NOT silently trust an external upgrade.
- **FR-919d**: Normal uninstall MUST remove only Aether-owned service/runtime/cache state and preserve user profiles/projects by default. Destructive purge requires a separately explicit operation and confirmation.
- **FR-919e**: Every install/update/reconcile transition record MUST identify the one staged `aether-agents` wheel by filename and SHA-256, the release-lock schema/version and immutable Aether pre-build tuple, both target environments, and their installed-file fingerprints. The wheel-contained release lock MUST NOT contain its own final digest. Activation fails before pointer switch when manager/runtime identities, entry point, or profile enablement differ.
- **FR-919f**: Observation JSONL is immutable forward state and is never migrated, rewritten, or restored from an older release. Each reducer uses a versioned disposable projection, pure upcasters for every historical event version it claims, and a quarantine index that preserves exact unknown-newer bytes. Rollback cannot delete or downgrade those bytes; forward re-update MUST reingest them.
- **FR-919g**: A project fingerprint key is private persistent state, not a credential, product resource, or public artifact. It MUST use `0600`, survive ordinary update/rollback/uninstall-preserve, enter only private local recovery backup or a separately authorized protected export, and never enter logs, summaries, transition records, release artifacts, public evidence, or ordinary export. Rotation/loss creates a new key epoch and a visible comparison boundary; it MUST NOT be classified as a configuration change.

## 6. Retention

Every durable surface grows without bound by default. Retention is therefore a design decision, not an operational afterthought.

| Surface | Disposition |
|---|---|
| Contract artifacts and code | Permanent. Never pruned. |
| Card rows, comments, attempt records | Permanent by default; the acceptance record of the project |
| Board events | Pruned on a schedule; they are execution telemetry, not the record |
| Worker logs | Pruned on a schedule |
| Preserved worktrees | Retained through review, integration, and publication; pruned after durable terminal evidence |
| Branches | Retained through review, integration, and publication; objective-owned merged branches are removed after durable evidence while unrelated/pre-existing branches remain |
| Attachments | Retained with their card |
| Notification subscriptions | Removed when the work they watch reaches its irreversible end state |
| Immutable release directories | Retained while active or rollback-eligible; pruned only after a newer coherent release is proven |
| Transition journals and backups | Retained through the rollback window; never published |
| Contract observation summaries | Immutable summaries retained with project state; current/older reducer versions remain addressable until explicit owner purge |
| Contract observation detailed events | Retained indefinitely with preserved UTC instant and local offset; only verified closed segments may enter deterministic lossless compaction and source removal after verified replay; no pruning; deletion only through explicit owner purge |
| Observation projections/quarantine indexes | Versioned, rebuildable, non-authoritative; may be replaced only by deterministic rebuild while source/unknown bytes remain untouched |
| Observation fingerprint keys | Private persistent project state across update/rollback/uninstall-preserve; never published or included in ordinary export |
| Download cache | Freely replaceable after integrity verification and activation |

- **FR-920**: Retention MUST distinguish the acceptance record from execution telemetry. Board rows, Git commits, pull requests, and final evidence preserve the record; events, logs, and worktrees are telemetry and may be pruned only after terminal evidence is durable.
- **FR-921**: A retention sweep MUST NOT remove anything an unfinished unit depends on. Pruning is only ever applied to terminal work.
- **FR-922**: An objective-owned worktree or merged branch MUST be removed only after durable PR, merge, board, and final-verification evidence exists. Git history, the PR, and board evidence preserve merged-unit inspectability; active, unmerged, blocked, review-active, concurrent, unrelated, and pre-existing residues MUST remain.
- **FR-923**: Retention values are calibration, not architecture, and MUST be recorded when set.
- **FR-923a**: Observation has no pruning path. Compaction MUST preserve exact uncompressed event bytes, final schema-valid summaries, invariant results, coverage/gap declarations, safe evidence references, and decision references; raw content never enters any retained layer. Explicit purge deletes the selected observation state rather than manufacturing a reduced historical record.
- **FR-923b**: Remote merged-branch cleanup and local objective branch/worktree cleanup are terminal closeout steps, not independent product state. They MUST use ordinary non-destructive operations and MUST NOT rewrite history or delete evidence for unfinished or unrelated work.

## 7. Boards Are the Project Boundary

- **FR-924**: One board and workspace root per portable project identity (R5-FR-510). `aether init` maps that identity to a native Hermes Project and board; a worker is pinned to the exact board at spawn.
- **FR-925**: Namespacing inside a board is a soft filter and MUST NOT be used as an isolation boundary between projects (R5-FR-511).
- **FR-926**: Cross-project references MUST NOT be expressed as links, which the runtime does not permit across boards. Where a relationship exists, it belongs in the contract.
- **FR-927**: A moved clone may be remapped explicitly after repository-identity validation. A UUID or canonical-repository collision MUST fail rather than attach to another project's state.
- **FR-928**: Hermes `projects.db` remains per profile while the board store is shared across profiles (`hermes_cli/projects_db.py:1-18`). Aether's mapping MUST make all three role profiles resolve the same portable project and board without sharing a profile home or duplicating the board kernel.

## 8. Evidence

From direct inspection of selected commit `e624e9f…` and prior isolated execution:

- The board's schema carries tasks, links, comments, events, attempt records, attachments, and notification subscriptions as separate durable tables.
- Attempt records are created even for units that were never claimed, so a completion or block always has an attempt row behind it. Observed: two attempt rows for a unit blocked twice, each carrying its reason.
- A re-dispatched unit's assembled context contains prior attempts, parent handoffs, and the full comment thread. Observed directly.
- Deliverables are collected only when declared at completion; other files in an ephemeral workspace are removed.
- Retention sweeps exist for events, logs, workspaces, and terminal-state subscriptions.
- `hermes_cli/projects_db.py:1-21,57-96` separates per-profile Project state from shared boards and supports board binding; `tests/hermes_cli/test_kanban_board_project.py:40-87` verifies project inheritance at task creation.
- The XDG release layout, atomic active-release record, transitions, backups, and mismatch handling are Aether requirements from PD-55/PD-63; they are not claimed as native Hermes behavior.

Not inspected: the memory provider internals and the board's full event reference. Neither carries an accepted decision here beyond the ownership boundaries stated above, and both are read by whoever configures them.

## 9. Requirements Inherited by Later Stages

| Requirement | Owner |
|---|---|
| Durable fields must never carry secrets; this needs enforcement, not only instruction | R10 |
| An external write is not recoverable by reclaim | R10 |
| Attempt records and completion evidence are the evidence base | R11 |
| Retention values are set once a real run shows the growth rate | R13 |

## 10. Success Criteria

- **SC-901**: No fact about delegated execution is authoritative anywhere except the board; direct action evidence remains in existing project and profile/session surfaces without a shadow execution store.
- **SC-902**: No fact about what was asked for is authoritative anywhere except the repository.
- **SC-903**: A crash during unattended work costs at most one attempt.
- **SC-904**: A re-dispatched unit never repeats a path that already failed in a recorded attempt.
- **SC-905**: Morfeo's memory contains only owner preferences, and the owner can read and delete all of it.
- **SC-906**: No durable field contains a secret.
- **SC-907**: Every merged unit remains individually inspectable after its worktree is pruned.
- **SC-908**: A failed update or rollback never activates mixed release components and never damages unrelated Hermes/user state.
- **SC-909**: Two initialized projects and three role profiles resolve isolated project state while sharing no profile home and duplicating no board.
- **SC-910**: Default uninstall preserves profiles/projects; destructive purge is explicit and separately confirmed.
- **SC-911**: Update, rollback, and forward re-update preserve every observation source byte and key epoch; incompatible readers use separate projections and never destroy unknown newer evidence.
- **SC-912**: No public/release/log/ordinary-export surface contains a fingerprint key, and key rotation is visible without fabricating a configuration delta.
- **SC-913**: Aether Canonical, Project Canonical, and Learned Profile Skills remain procedural, correctly located and visible, ordered only within the procedural tier, and never auto-promoted or authoritative.
- **SC-914**: Objective-owned merged branches and worktrees are removed only after durable terminal evidence, while active or unrelated residues and all acceptance evidence remain preserved.

## 11. Done When

- [x] Repository, board, profile, and Aether XDG product-state domains are separated with explicit ownership.
- [x] Deliverable declaration and the destruction of undeclared files are specified.
- [x] Morfeo's memory is bounded to owner preferences, with a rule against inferring from one instance.
- [x] Recovery semantics and the cost of each failure are stated.
- [x] The indeterminate outcome is preserved for unprovable side effects.
- [x] Retention separates the acceptance record from execution telemetry.
- [x] Public install/update/rollback/uninstall, project mapping, backup, and mismatch ownership are explicit.
- [x] Christopher has reviewed the stage (R4–R13 Decision Review, 2026-08-17).
- [ ] Retention values are set from an observed growth rate.
