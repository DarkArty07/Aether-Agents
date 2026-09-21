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

A pre-stable milestone is a legitimate objective outcome: an authorized objective may
publish a release candidate to its prerelease channel while the stable gates stay open.
`release_channel = prerelease` never implies stable `1.0.0`, a package-index publication,
a WSL2 qualification or a completed `#261`. The Implementer reports only its own
compatibility evidence; the aggregate conclusions belong to the terminal closeout.

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

## Managed runtime projections and release-owned TUI

Active release installation (`aether update`) provisions release-owned runtime projections:

1. **Release-owned TUI asset**: The prebuilt TUI (`ui-tui`) is built once from the exact maintained-fork commit in a disposable workspace, hash-bound outside `hermes-source` under `<release>/tui/`, and exposed at `runtime/current/tui`. `HERMES_TUI_DIR` is set to this release-owned directory across launcher, update, and rollback. Runtime launch never runs `npm` or builds assets in place. Gateway service operation does not depend on `HERMES_TUI_DIR`.
2. **Branded desktop and terminal projections**: Candidate activation installs branded `Aether` (fresh session) and `Continue Aether` (`--resume latest`) actions. Their `Exec` lines invoke the stable `runtime/current/venv/bin/aether` selector with an explicit `--project <path>` binding, never guessing cwd or targeting version-specific Hermes paths. On WSL hosts, Windows Terminal fragments project the same actions into the host terminal.
3. **Hermes-owned gateway service and semantic doctor**: The gateway service (`hermes-gateway-morfeo.service`) is owned and materialized by Hermes Agent via the selected runtime's Hermes CLI (`hermes --profile morfeo gateway install`). Aether neither writes nor byte-compares the service unit. `aether doctor` semantically verifies that the service selects the active `runtime/current` Python, Morfeo profile and home, and active virtualenv, while checking byte-level integrity across the active-release record, `runtime/current`, the packaged launcher, and desktop entries.

## Recovery surfaces

Three supported surfaces act on an existing installation, and none of them installs a package, acquires credentials, or rolls user state backward. `aether doctor` and `aether reconcile --to active` inspect or repair the release that is already active; `aether rollback` is the one surface that selects a different release, switching the product-owned runtime, launcher and service pointers to the most recent prior coherent release or to an explicitly named one.

- `aether doctor [--project PATH] [--json]` is the read-only coherence inspection: active-release record, `runtime/current`, packaged launcher, desktop entries, the Hermes-owned gateway service selection, profiles, observation counters, projection compatibility, and platform constraints. A non-zero integrity result is an honest diagnostic, not an instruction to install, authenticate, or activate anything.
- `aether reconcile --to active [--dry-run] [--yes] [--json]` reconciles the projections and selector of the **already active, authenticated** release against its own authoritative record. Without `--yes` (or with `--dry-run`) it only plans: it reports the current mismatches and changes nothing. With `--yes` it repairs those managed projections and reports the reconciled count; a second run is idempotent and reports no change. It refuses `--to installed` and a missing `--to` with `UNSUPPORTED_RECONCILE_MODE`, and it refuses an active release that cannot prove authentication — for example a legacy record without an installed-file fingerprint — before any byte moves, as an unsupported legacy route rather than a repaired installation. It never replaces a full `aether update` promotion.
- `aether rollback [VERSION] [--dry-run] [--yes] [--json]` switches the product-owned runtime, launcher and service pointers back to the most recent prior coherent release, or to the explicitly named one. Observation journals, key epochs and other user state continue forward unchanged.

An observation error with the bounded codes `STATE_BUSY` or `CATCHUP_INCOMPLETE` is a retryable contention signal rather than a broken installation; see [Observation](observation.md).

## Failure evidence and recovery boundaries

The durable unit is the card, not a worker process. A retry or reclaim preserves
the unit but does not prove an interrupted external effect did not occur.
Completion and terminal reports state actual changes, verification, omissions and
remaining material risk. A genuine protected-edge denial is authoritative; an
unexpected denial of ordinary local/reversible work follows the rollback-first
bounded recovery boundary in [Policy and recovery](policy-and-recovery.md).
