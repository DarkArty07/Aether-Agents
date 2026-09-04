# Execution: boards, sessions, worktrees, and review

A finalized Objective Contract receives an Aether-specific handoff boundary
before Supervisor work begins. This page describes Aether's role and evidence
rules; Hermes supplies the generic board, session, worktree, retry, reclaim, and
review lifecycle.

## Per-contract execution board

`prepare_handoff` derives one deterministic execution-board identity from
`(project_id, contract_id, version)` and resolves the exact project binding
before returning success. The returned board and native Project identifiers are
root-card routing data, not portable contract content and never child-body
content. There is no fallback to the default/current board.

This isolates execution-board task graphs, claims, logs, and workspaces. It does
not solve source-level merge collisions; worktree isolation, independent review,
and Supervisor integration still matter.

## Session affinity and worktrees

Supervisor phases for one flow use the runtime's same-profile session-affinity
boundary and canonical Supervisor workspace. Implementer cards receive fresh
sessions and isolated worktrees, so a worker does not inherit a Supervisor
conversation or a sibling checkout. A final Supervisor terminal phase depends on
the root and all implementation units and is marked `terminal=true`; internal
milestones stay internal and do not signal the origin unless a genuine owner
input or contract revision is required.

## Card inputs and canonical procedures

Every card body carries its explicit acceptance criteria, scope, shared decisions,
compatibility-impact reporting obligation, authority boundary, and evidence
expectation without requiring sibling context. Workers discover task-relevant
Aether Canonical Skills made available by the product and Project Canonical
Skills named by root `AGENTS.md` at `.aether/skills/<name>/SKILL.md`. Skills are procedure, never authority: current owner instruction -> constitution/design/stage specs/Objective Contract -> repository operating rules govern authority.
Among compatible procedures, Project Canonical is more specific than Aether
Canonical; both outrank Learned Profile Skills. An Implementer may not silently
replace a canonical procedure with a learned skill.

If an authorized unit invalidates `AGENTS.md` or a canonical procedure, the unit
updates that guidance only when the update is in scope. Otherwise its evidence
records a specific non-applicability reason. Supervisor verifies root guidance
coherence at integration.

## Review, integration, and terminal evidence

Implementers make local commits and evidence; they do not integrate their own
units or publish. Supervisor reviews work it did not author, integrates in
dependency order, and runs integrated verification. That local integration is a
checkpoint: local integration alone is not terminal.

For a GitHub-backed pipeline, terminal evidence covers acceptance verification,
normal branch push, pull request, required checks, bounded diagnosis/correction
of objective-caused CI failures, green merge without bypass, applicable
issue/milestone reconciliation, remote merged-branch cleanup, local objective
branch/worktree cleanup only after durable evidence, and final evidence. Every
omitted step has a concrete non-applicability reason. Active/unmerged/review/
concurrent/unrelated work is preserved.

Supervisor's report requires the independent conclusions
`release_impact = none|patch|minor|major`,
`release_action = defer|prepare|publish`, and
`release_channel = none|prerelease|stable`, plus compatibility evidence kept
separate from those fields. Prerelease is not a compatibility impact, and a
merge does not imply a release. Any routine closeout remains within the
provisioned repository and existing credentials; bypass, settings mutation,
force/history rewrite, credential acquisition/widening, package publication,
deployment, and destructive variants remain separately protected.

A worker flags repeated collision pressure as a hotspot rather than absorbing
another unit's scope. Unfinished, blocked, review-active, concurrent, or
unrelated work is preserved. Completion evidence states what changed, what was
actually verified, and what material risk or non-applicability remains.

## Qualification limit

The handoff source and focused tests cover deterministic IDs, isolation checks,
idempotent provisioning, and profile instructions. The complete installed
runtime/session-affinity path remains a separately qualified boundary; see
[Capability coverage](../reference/capabilities.md) and
[limitations](../reference/limitations-and-troubleshooting.md).
