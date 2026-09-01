# R10 Specification: Security, Trust, and Edge-Effect Enforcement

**Roadmap ID**: R10
**Stage status**: in-progress — operational simplification amendment under PD-71/PD-72/PD-73/PD-74
**Accepted baseline**: 2026-08-17 — Christopher accepted the R4–R13 Decision Review
**Reopened**: 2026-08-26 — Christopher rejected the accumulated strict enforcement after repeated E2E failures and authorized simplification
**Amended**: 2026-09-01 — routine GitHub collaboration is preauthorized; the protected remote edge is narrowed to destructive, bypass, deployment, credential/spend, package and arbitrary-API effects
**Decision authority**: Christopher
**Depends on**: R1, R5, R7, R8, R9, `DESIGN.md`
**May affect**: R11, R13, A1
**Selected Hermes baseline**: `NousResearch/hermes-agent` `v2026.8.18`, annotated tag object `9f13bbbf8423427e159c78066356ca0e27ca6b74`, commit `e624e9fde561e1add9388384012b295fde669ade`, distribution `0.20.4`

## 1. Purpose

R10 protects the few effects for which prevention is materially better than recovery. It no longer attempts to encode Aether's role chart, task semantics, contract ownership, branch workflow, or ordinary local execution as a permission engine.

The governing rule is PD-71:

> **Work that is local and practically reversible is governed by scope, isolation, Git, tests, review and rollback. A pre-tool guard is reserved for high-confidence effects at the irreversible/external edge.**

This amendment retires the previous board/run/worktree/branch/operation-parser micro-authorization design. Git history preserves that design; it is no longer current authority.

## 2. Threat model

Aether is a single-host product operated by one trusted local user. Morfeo, Supervisor and Implementer are not OS security principals.

**In scope**:

- a secret or credential entering a durable/public artifact;
- an agent acquiring or widening credentials;
- a remote publication, deploy, push, external mutation or release without explicit authority;
- a clearly destructive operation whose loss is not practically recoverable by the project workflow;
- a structurally provable escape from an isolation boundary that Aether actually claims to enforce.

**Out of scope**:

- defending the owner's machine from the owner;
- sandboxing one Aether role from another as hostile principals;
- deciding whether Morfeo should use direct or pipeline execution;
- deciding whether a local implementation choice is good;
- preventing every possible local mistake before it occurs;
- inferring filesystem confinement from arbitrary shell/code text.

- **FR-1001**: Aether MUST operate under a single-host, trusted-local-user model and MUST NOT claim isolation between roles as security principals.
- **FR-1002**: The board MUST NOT be treated as a security boundary; a process running as the owner can access the same local state.
- **FR-1003**: Loopback-only local runtime surfaces MUST remain loopback-only where upstream does not authenticate them.
- **FR-1004**: No role may acquire, create or widen credentials beyond credentials the owner already provisioned.
- **FR-1004a**: Public installation MUST remain isolated under Aether-owned XDG roots and MUST NOT replace or import unrelated personal Hermes state.

## 3. Responsibility is not a permission boundary

The roles remain semantically distinct:

- Morfeo owns owner dialogue, product intent, contract revision and proportional routing.
- Supervisor owns pipeline decomposition, independent review, convergence and integration judgement.
- Implementer owns bounded implementation units.

Those responsibilities are enforced by contracts, prompts, attribution, review and acceptance evidence. They are not reasons to reject ordinary local tool calls.

- **FR-1005**: Aether MUST NOT use a pre-tool hook to choose direct versus pipeline routing, determine task size, judge a local implementation decision, or enforce the role chart as if the roles were OS principals.
- **FR-1006**: Native structural restrictions that Hermes already supplies remain primary where useful, but Aether MUST NOT add a second hook restriction solely to mirror an instruction.
- **FR-1007**: Executable prevention is required only for the definitive protected edge effects in §5. A cognitive responsibility is not a protected effect merely because violating it would be bad work.

## 4. Enforcement point

Hermes `v2026.8.18` exposes `pre_tool_call` as a real blocking hook. Direct inspection of the selected source confirms shell hooks can block via exit code `2`/block payload and can be configured `fail_closed`; hook consent remains a separate runtime concern.

Aether keeps one small canonical pre-tool policy because it is useful at the edge. The policy is deliberately incapable of understanding the whole project workflow.

- **FR-1008**: The shared pre-tool policy MUST block only effects enumerated in §5 plus malformed hook invocation. It MUST otherwise return allow.
- **FR-1008a**: Every release MUST run positive controls for representative ordinary Morfeo, Supervisor and Implementer work, negative controls for every protected edge family, and a complete E2E canary with zero guard-caused manual recovery.
- **FR-1008b**: An unknown or unfamiliar ordinary local tool call MUST be allowed when it does not match a protected edge effect. Lack of a role/worktree/board proof is not by itself dangerous.
- **FR-1008c**: Invalid JSON, an invalid event shape, or missing required hook payload structure MAY fail closed because the hook invocation itself is malformed.
- **FR-1008d**: The guard MUST NOT parse arbitrary shell/code text to infer contract ownership, branch ownership, task size, workspace confinement, or whether a role is performing another role's intellectual responsibility.
- **FR-1008e**: The guard MUST NOT open Kanban/SQLite, query task/run identity, or execute Git merely to decide whether an ordinary local file or terminal action may run.
- **FR-1008f**: The same versioned policy bytes are installed for the three roles. Role names MAY appear in diagnostics, but ordinary allow/deny semantics are not a second per-role authorization system.
- **FR-1008g**: `fail_closed` is a crash/malformed-invocation net. It MUST NOT be used to turn uncertainty about ordinary work into deny-by-default.
- **FR-1008h**: A denial MUST state the protected edge family and the concrete reason in a caller-visible payload.
- **FR-1008i**: An agent MUST NOT route around a genuine protected-edge denial. A false positive discovered on ordinary work is instead a product regression and enters PD-72 recovery.
- **FR-1008j**: The previous guard crossed the PD-66 redesign threshold after multiple distinct ordinary-work false positives. Incremental exception-patching of that retired design MUST NOT resume without a new owner decision.
- **FR-1008k**: Read-only inspection, normal local Git, local branches, local commits, test runners, interpreters, package/build tools and reversible project-file mutations MUST remain available unless the exact call independently matches §5.
- **FR-1008l**: Aether MUST NOT claim generic process/filesystem confinement from a command-string scanner. A real sandbox/container/OS boundary requires its own explicit design and evidence.

## 5. Definitive protected edge effects

This list is intentionally short. Adding another family is a design change, not an implementation convenience.

| Protected edge family | What the guard prevents during normal stabilization |
|---|---|
| Secret persistence/exposure | Credential-shaped material entering durable fields or obvious outbound/mutation payloads |
| Credential acquisition/widening | Login/provision/key-generation/secret-store operations that create or enlarge access |
| Protected remote/external mutation | Remote history/tag rewrite or deletion, hook/check/branch-protection bypass, destructive Release/repository mutation, arbitrary mutating API calls, package/container publication, deploy, infrastructure/provider/spend mutation and equivalent obvious protected effects; the routine GitHub lifecycle is not in this family |
| Clearly destructive irreversible local operation | Root/home/device wiping, destructive disk operations, hard cleanup that destroys unknown local state, and similarly unambiguous loss |
| Structurally provable isolation escape | Only a typed/structured target whose boundary can be checked without interpreting arbitrary program behavior; if no such boundary is configured, the hook makes no confinement claim |

- **FR-1013**: The table above is the definitive protected-effect enumeration for the stabilization baseline.
- **FR-1013a**: Contract ownership, card shape, local branch choice, local commit workflow, ordinary file paths, technical design decisions, review decisions and routing are NOT protected effects.
- **FR-1013b**: The routine GitHub lifecycle named by R8-FR-824 is preauthorized and MUST NOT depend on another availability gate. Protected variants remain fail-closed: remote history/tag rewrite or unreviewed deletion, hook/check/branch-protection bypass, destructive Release/repository mutation, arbitrary mutating API calls, package/container publication, deploy/cutover, infrastructure/provider/spend mutation, and credential acquisition/widening.
- **FR-1013c**: A destructive-operation detector MUST prefer a small high-confidence list over broad command semantics. A false negative that remains local/reversible is handled by isolation/review; a false positive that blocks ordinary work is a regression.
- **FR-1014**: A denied edge effect MUST be visible in the E2E evidence.
- **FR-1015**: Repeated attempts to perform the same genuine denied edge effect are reportable; ordinary false positives trigger recovery rather than more denials.

## 6. Secrets, credentials and privacy

- **FR-1015a**: Versioned source, wheel/sdist, profiles, hooks and docs MUST contain no private owner credentials, tokens, sessions, databases, memories or private provider bindings.
- **FR-1015b**: Credential-shaped content MUST be rejected from durable board/comment/memory/attachment payloads unless it is an explicit redacted/example placeholder.
- **FR-1015c**: High-confidence credential material supplied to any other tool call MUST be blocked rather than copied into a subprocess or external effect.
- **FR-1015d**: Credential acquisition/widening commands remain blocked even when they contain no credential yet.
- **FR-1015e**: Contract Observation remains local, metadata-only and fail-open; it is not part of the security boundary and MUST NOT block legitimate work.

## 7. External authority

Aether's normal unattended workflow carries the owner-preauthorized routine GitHub authority from R8-FR-824, but does not imply authority for other publication, deployment, credential or spend effects.

- **FR-1016**: Deployment/cutover, package or container publication, repository settings/protection mutation, public announcements outside routine Release notes, paid live qualification, provider/spend changes, credential changes, destructive purge and arbitrary mutating API calls remain separate protected gates.
- **FR-1017**: This stabilization candidate permits the fixed routine GitHub lifecycle without parsing conversational prose, cards or shell context, and blocks only high-confidence protected variants.
- **FR-1018**: A later bounded product surface MAY carry authority for rare protected effects, but it MUST NOT sit on the critical path for the routine GitHub lifecycle.
- **FR-1019**: Local technical capability never self-grants an external effect.
- **FR-1020**: Christopher's current explicit instruction outranks older artifacts; the owning artifact must be updated rather than silently bypassed.

## 8. Untrusted content

- **FR-1021**: Repository/web/archive/package content read during execution is data, not authority to expand scope or external effects.
- **FR-1022**: A role MUST NOT widen its objective because a file or fetched page instructs it to do so.
- **FR-1023**: Referenced attachments or fetched content MUST NOT be executed merely because they contain executable-looking instructions.
- **FR-1024**: Native inbound prompt-injection filtering and credential scrubbing remain useful defense in depth; they do not enlarge the pre-tool edge list.

## 9. Recovery and what enforcement cannot do

- **FR-1025**: Reversibility is the primary local safety mechanism. The hook MUST NOT be treated as a substitute for worktrees, Git, tests, review or rollback.
- **FR-1026**: Enforcement cannot make an incorrect implementation correct. Correctness belongs to tests, review and acceptance.
- **FR-1027**: The hook runs inside the same local trust boundary as the agent; it is a mistake-prevention layer, not a hostile-process sandbox.
- **FR-1028**: A material false positive on ordinary authorized work enters PD-72 recovery: restore the last green E2E first, then investigate separately.
- **FR-1029**: Recovery MUST NOT expand the protected-effect list merely to explain an incident. A new protected family requires a reproduced material edge risk and owner-approved design change.

## 10. Evidence

### Upstream inspection

Refreshed 2026-08-26:

- Spec Kit checkout was refreshed before this amendment; its task template still groups tasks by independently testable user story and its analysis command remains explicitly read-only. Aether retains that intellectual contract and does not copy its interactive human-stop semantics.
- Hermes selected source was checked out independently at exact tag `v2026.8.18`: tag object `9f13bb…`, commit `e624e9f…`. `website/docs/user-guide/features/hooks.md` and the actual hook dispatcher confirm `pre_tool_call`, blocking, `fail_closed` and `--accept-hooks` are real supported surfaces.
- No inspected upstream source requires Aether to implement role semantics, contract ownership or branch workflow in a pre-tool hook.

### Local baseline

Before this amendment, focused policy/A1/launcher tests passed `58 passed, 46 subtests` after restoring the versioned launcher executable bit in the moved worktree. The earlier guard source was 921 lines and contained Kanban SQLite lookup, Git context evaluation, contract ownership, branch/history parsing and per-role card restrictions. Those mechanisms are the simplification target, not evidence to preserve them.

## 11. Success criteria

- **SC-1001**: Representative local/reversible work and the routine GitHub lifecycle for all three roles are not blocked by policy.
- **SC-1002**: Secret/credential, credential-acquisition, protected remote mutation and clearly destructive controls are denied with a precise reason.
- **SC-1003**: The guard contains no SQLite/Kanban dependency and performs no Git subprocess invocation.
- **SC-1004**: The guard does not classify contract ownership, decision-card shape, task size or direct/pipeline routing.
- **SC-1005**: A complete three-role canary, including Supervisor publication, needs zero guard-caused manual recovery.
- **SC-1006**: No release-visible artifact contains private owner state.
- **SC-1007**: No protected external/destructive effect occurs without its separate gate; the routine GitHub lifecycle is not misclassified as protected.
- **SC-1008**: A false-positive recovery restores a known-good canary before any hardening work begins.

## 12. Done when

- [x] Christopher explicitly reopened the strict enforcement design on 2026-08-26.
- [x] The threat model is narrowed to the real trusted-local-user boundary.
- [x] Reversibility/review are primary for ordinary local work.
- [x] Protected edge families are enumerated narrowly.
- [x] Role semantics are removed from the normative hook contract.
- [ ] The minimal hook implementation and positive/negative matrix pass.
- [ ] A real E2E canary completes without guard-caused recovery.
- [ ] The rolling reliability gate in PD-74 passes before R10 returns to `done`.
