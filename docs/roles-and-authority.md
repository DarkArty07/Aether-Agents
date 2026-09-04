# Roles and authority

Aether has one owner and exactly three product roles: Morfeo, Supervisor, and
Implementer. Role responsibility is semantic: contracts, attribution, worktree
isolation, tests, review, Git history, and rollback govern ordinary reversible
work. The pre-tool policy protects a narrow external/destructive edge; it is not
an operating-system separation between roles.

| Participant | Owns | Local or pipeline authority | Must not silently do |
| --- | --- | --- | --- |
| Owner | Product intent, constitutional principles, acceptance, and protected external effects | Decide objectives, constraints, and delegated authority | Delegate an unstated product decision by omission |
| Morfeo | Owner dialogue, contract architecture, memory/adaptation, project onboarding, and bounded direct stewardship | Establish/confirm constitution, create missing-root guidance, choose the complete-objective route, and own authorized direct-route closeout | Become the standing implementation role, invent intent, or claim a pipeline branch fully closed |
| Supervisor | Executability, decomposition, independent review, convergence, integration, and pipeline terminal closure | Resolve contract-settled shared questions; publish the normal pipeline path after review; verify final coherence and evidence | Change product intent, absorb feature implementation, or call local integration terminal |
| Implementer | One bounded contract-derived implementation unit | Make reversible technical choices, local commits, tests, and evidence | Fan out sibling work, widen scope, publish, or redefine contract meaning |

## Procedure discovery and precedence

Every role discovers task-relevant Aether Canonical Skills made available by the
product and Project Canonical Skills named by root `AGENTS.md`; a Project
Canonical procedure is read at `.aether/skills/<name>/SKILL.md`. Skills remain
procedure, never authority. Authority precedence is current owner instruction -> constitution/design/stage specs/Objective Contract -> repository operating rules. Among compatible procedures, Project Canonical is more specific than Aether Canonical; both outrank Learned Profile Skills.
An Implementer may not silently replace a canonical procedure with a learned skill. Role prompts name no hard-coded per-project skill list, and skills cannot grant authority.

## Route and onboarding ownership

Morfeo inspects the complete objective and chooses direct work when it is
understood, bounded, inspectable, and practically reversible without proportionate
value from decomposition or independent review. Otherwise Morfeo finalizes one
project-bound Objective Contract and hands one card to Supervisor. Direct work
creates no ceremonial card; pipeline work creates no implementation units at
Morfeo's handoff.

At project start, Morfeo establishes or confirms the constitution from owner-
approved principles and observed reality. If root `AGENTS.md` is absent, Morfeo
writes accurate minimal guidance after constitution confirmation. Brownfield
instructions are preserved and reconciled. The agent whose authorized change
invalidates build, test, run, version, release, deploy, generated-file, or skill
guidance updates it when that update is in scope; otherwise the completion report
contains a specific non-applicability reason. Supervisor verifies `AGENTS.md`
coherence before closure.

When project policy uses GitHub Issues and no canonical issue represents the
authorized objective, Morfeo creates or reconciles one non-duplicate issue at
intake. If policy does not use Issues or an issue already represents the
objective, the report records the concrete non-applicability reason. Supervisor
reconciles applicable issues and milestones at close.

## Release conclusions and publication

Every objective reports three separate conclusions:

- `release_impact = none|patch|minor|major`
- `release_action = defer|prepare|publish`
- `release_channel = none|prerelease|stable`

Compatibility impact is evidence for the first conclusion, not a synonym for
release action or channel. Prerelease is not a compatibility impact, and a merge
does not imply a release. Supervisor requires the aggregate values; Implementer
reports unit evidence and never publishes. Morfeo reports direct-route evidence
when it owns that closeout.

For a GitHub-backed pipeline, terminal closure requires acceptance verification,
normal branch push, pull request, required checks, bounded diagnosis/correction
of objective-caused CI failures, green merge without bypass, applicable
issue/milestone reconciliation, remote merged-branch cleanup, local objective
branch/worktree cleanup only after durable evidence, and final evidence. Every
omitted step has a concrete non-applicability reason. Local integration alone is
not terminal. Active/unmerged/review/concurrent/unrelated work is preserved.

Routine closeout stays inside the provisioned repository and existing
credentials. It does not authorize credential acquisition/widening, settings
mutation, force/history rewrite, bypass, package publication, deployment,
destructive operations, or weakening Aether's explicit `v1.0.0` gate. Genuine
protected-edge denials are authoritative; unexpected denials of ordinary local
reversible work enter bounded recovery rather than being bypassed.

See [Lifecycle](guides/lifecycle.md), [Execution](guides/execution.md), and
[Policy and recovery](guides/policy-and-recovery.md) for the reader-facing
route and evidence details.
