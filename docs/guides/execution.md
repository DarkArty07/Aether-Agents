# Execution: boards, sessions, worktrees, and review

A finalized Objective Contract receives an Aether-specific handoff boundary
before Supervisor work begins. This page describes Aether's role and evidence
rules; Hermes supplies the generic board, session, worktree, retry, reclaim, and
review lifecycle.

## Per-contract execution board

Morfeo relates contracts to the whole objective through its existing
[Objective Plan](objective-plans.md), when one is needed. Session/contract changes
do not erase prior failures or reset applicable convergence bounds. This local
record is not another board or authority, and workers still receive complete
executable obligations through their canonical handoff.

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
the root and all implementation units and is marked `terminal=true`. Ordinary
internal milestones stay silent to the origin as owner-facing notifications;
explicit peer questions and coalesced evidence notices may reach the originating
design steward without notifying the human owner. Only explicit owner input,
contract revision, or terminal outcomes return to the owner-facing session.

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
units or publish. Supervisor reviews work it did not author, may make an attributed
bounded repair under PD-73, integrates in dependency order, and runs integrated
verification. Verification of its own repair is not independent review; any required
independence remains applicable. Local integration alone is not terminal.

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

Write-capable probes and review steps construct one disposable board context with the
reviewed laboratory constructors and refuse a context that resolves outside their
private roots before the first native writer. Accidental mutation of a live or shared
board is preserved as evidence and escalated through the supported lifecycle: direct
SQL deletion of tasks, comments, events or runs is never cleanup. Isolation defects are
reproduced against disposable copies, and the fixing unit reports a byte/row-stable
live-board fingerprint.

## Review convergence

Supervisor owns convergence as well as defect detection. Repeated failure classes,
equivalent cases exposed by successive fixes, or increasing repair complexity require
a common-cause assessment before another piecemeal return. Review the affected mechanism
jointly, tie findings to current obligations, and keep optional improvements out of the
acceptance gate. From the first delivery, Supervisor may directly correct an understood,
bounded defect restoring agreed behavior when doing so is more economical than another
handoff and preserves its coordination capacity. Substantial implementation stays with
Implementer; material design, scope, interface, guarantee or authority decisions return
to Morfeo, even if the contract is complete. Attribute direct repairs and their checks.

Allow at most two ordinary review returns per logical unit, with the count taken from
existing durable history and recorded in the existing handoff. Stop earlier without
progress or a better diagnosis. After two returns, accept supported work, make a bounded
repair or consult originating Morfeo with evidence and a recovery proposal; no third
ordinary return or approval by exhaustion. A new session or replacement card does not
silently reset the budget. Preserve the candidate and healthy independent work.

The existing `supervisor-decomposition` canonical skill owns the detailed procedure and
illustrative contrasts. This is an instruction-level policy, not technical prevention
of a third return. The selected Hermes source adds `Previous review returns (this task)`
to native worker context (also returned by `kanban_show`), counted from all recorded
`changes_requested` events for that card. It neither tracks replacement cards nor
enforces the policy; older contexts can still use the complete event history.
The procedure uses existing history and collaboration without a separately stored counter,
schema, hook or workflow engine. Document and loader tests establish
instructional consistency, not observed improvement; the open-ended observation
gate in #317 was closed at owner direction without claiming organic PASS, and
unverified behavioral efficacy remains explicit.
See PD-73 and R7 FR-703, FR-734 and FR-736b–e for the owning requirements.

## Contract/execution procedure adoption

The explicit canonical resource set includes `objective-contract-design` for Morfeo,
`supervisor-decomposition` for Supervisor and `implementation-evidence` for Implementer,
alongside the existing governance and closeout procedures. Native distribution makes
the canonical files available to all roles; each role loads the applicable procedure,
without gaining another role's authority.

Adoption of these three procedures and the related role wording was tracked in
[issue #317](https://github.com/DarkArty07/Aether-Agents/issues/317). The owner directed
closure of that open-ended observation requirement without claiming organic PASS;
resource installation and historical document/loading checks do not establish
behavioral qualification or proven throughput. Historical expected-versus-observed
records remain preserved as evidence, not active gates. This is not a global
no-testing rule for future work or permission to bypass required checks. Do not restart
the owner-withdrawn #312 delegated flow or recreate its retired test adapter. See the
[objective specification](../../specs/006-contract-execution-quality/spec.md).

## Qualification limit

The handoff source and focused tests cover deterministic IDs, isolation checks,
idempotent provisioning, and profile instructions. The complete installed
runtime/session-affinity path remains a separately qualified boundary; see
[Capability coverage](../reference/capabilities.md) and
[limitations](../reference/limitations-and-troubleshooting.md).
