# Lifecycle

Aether has two routes for one owner-authorized objective. Route selection is
Morfeo's judgement over the complete objective, not a classifier, score, fixed
workflow state, file count, time threshold, or tool-availability test.

## Intake and project readiness

Morfeo inspects the project and establishes or confirms its constitution from
owner-approved principles and observed reality. If root `AGENTS.md` is absent,
Morfeo establishes accurate minimal guidance after that constitution
confirmation. Existing brownfield instructions are preserved and reconciled,
not generically overwritten. The agent whose authorized change invalidates
operating guidance updates it when the update is in scope; otherwise evidence
states a concrete non-applicability reason.

If project policy uses GitHub Issues and the authorized objective has no canonical
existing issue, Morfeo creates or reconciles one non-duplicate issue at intake.
An existing canonical issue or a project policy that does not use Issues carries
an explicit non-applicability reason instead of ceremonial duplication.

Every objective records compatibility impact separately from these conclusions:

- `release_impact = none|patch|minor|major`
- `release_action = defer|prepare|publish`
- `release_channel = none|prerelease|stable`

Prerelease is not a compatibility impact, and a merge does not imply a release.
Release action and channel follow the standing project policy; the fields do not
create a second lifecycle state machine.

## Bounded direct route

Morfeo may complete an understood, bounded, inspectable, practically reversible
objective directly when decomposition or independent review adds no proportionate
value. Direct work uses the managed project workspace, creates no ceremonial
board card or pipeline phase, and is verified from actual commands, state, and
diffs. Morfeo owns authorized direct-route closeout and reports its compatibility
and release conclusions with the observed evidence.

Routine direct closeout remains within the provisioned repository and existing
credentials. It does not authorize credential acquisition or widening, settings
mutation, force/history rewrite, bypass, package publication, deployment, or
destructive effects. If direct inspection reveals substantial or materially
uncertain work, Morfeo stops expanding mutation and uses the pipeline; it does
not fragment the objective to avoid review.

## Pipeline route

Substantial, multi-responsibility, architectural, or materially uncertain work
moves through these durable boundaries:

1. Morfeo finalizes one project-bound Objective Contract and creates one
   Supervisor handoff card; it creates no implementation units.
2. The handoff verifies the finalized contract and carries only the runtime's
   opaque routing data to the root card, not into portable contract content.
3. Supervisor performs executability analysis, settles shared decisions, and
   creates independently testable Implementer units with explicit acceptance.
4. Each Implementer works in its isolated branch/worktree, makes local commits,
   runs relevant tests, and records evidence including compatibility impact and
   guidance applicability.
5. Supervisor independently reviews work it did not author, integrates in
   dependency order, and runs integrated verification.
6. Supervisor owns the terminal GitHub-backed closeout below. Local integration
   alone is not terminal, and Morfeo must never claim a pipeline branch fully
   closed before that evidence exists.

Hermes owns generic card status, retry, reclaim, review, worktree, and dispatcher
behavior. See [Execution](execution.md) for Aether-specific card/evidence rules
rather than duplicating those generic interfaces here.

## Terminal GitHub-backed pipeline closeout

After acceptance and independent review, the normal terminal sequence is:

1. acceptance verification;
2. aggregate `release_impact`, `release_action`, and `release_channel` conclusions;
3. normal branch push;
4. pull request;
5. required checks;
6. bounded diagnosis/correction of objective-caused CI failures;
7. green merge without bypass;
8. applicable issue/milestone reconciliation;
9. remote merged-branch cleanup;
10. local objective branch/worktree cleanup only after durable evidence; and
11. final evidence report.

Every omitted step has a concrete non-applicability reason. Active, unmerged,
review-active, concurrent, and unrelated work is preserved. Cleanup does not
rewrite history or remove unknown residue. A merge is not itself a release, and
`release_channel = prerelease` is never a compatibility-impact class.

Pipeline publication is Supervisor's responsibility after independent review.
Implementer makes local commits and evidence but never publishes, pushes, opens
or merges a pull request, mutates issues, tags, or releases. Morfeo owns the
same routine closeout only for an authorized direct route.

## Failure evidence and recovery boundaries

The durable unit is the card, not a worker process. A retry or reclaim preserves
the unit but does not prove an interrupted external effect did not occur.
Completion and terminal reports state actual changes, verification, omissions and
remaining material risk. A genuine protected-edge denial is authoritative; an
unexpected denial of ordinary local/reversible work follows the rollback-first
bounded recovery boundary in [Policy and recovery](policy-and-recovery.md).
