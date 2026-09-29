# Execution breakdown: Aether current-documentation consistency (#552)

**Owning design:** `specs/documentation-consistency/spec.md` (DC-01–DC-06), `plan.md`,
`research.md`, `quickstart.md`; finalized Objective Contract `oc_593cb1275b24ea19@v1`.
**Breakdown owner:** Supervisor. This is a derived artifact: it cannot widen the contract,
the stage specifications or accepted authority, and it is not a second requirements source.
**Base revision:** `62ec14653baa8f84449f41a68d64cf64d50939d6` (identical to the board
`worktree_base_ref`; the design commits are not yet on `main`, so the objective branch's pull
request carries them together with the unit commits).
**Parallel markers:** U1–U5 are independent `[P]` units with disjoint writable files.
T is the terminal integration card and depends on the root handoff plus all five units.

## 1. Receipt facts verified before decomposition

- Contract digest `89a938565fdb534286d08d09fc586dc9bd51ff5d5b4008738bd1581c3a6693f1`, portable
  project `12027989-a08f-41cd-a82c-54ff1bfb6b03` and base commit
  `62ec14653baa8f84449f41a68d64cf64d50939d6` all match the assigned root card; the board's
  `worktree_base_ref` is the same commit.
- Required pull-request checks at this revision: `pull-request-target`, `policy (3.11)`,
  `policy (3.12)`, `policy (3.13)`, `observation-qualification (3.11)`,
  `observation-qualification (3.12)`, `observation-qualification (3.13)`. Branch protection
  rejects force pushes and requires no administrative bypass. Every push to `main` runs the
  exhaustive three-version matrix, and `.github/workflows/pages.yml` rebuilds and deploys the
  existing GitHub Pages site when `docs/**` or `website/**` changes.
- Base gates checked directly at the base revision: `scripts/check_documentation.py` passes;
  `scripts/check_public_artifacts.py` passes; the `policy` job's R0 design-baseline, policy-hook,
  bytecode, mode, `VERSION` and forbidden-identifier steps pass.
- **Base-state defect corrected by U5.** The required `policy` job step "Validate canonical base
  manifest" and the oracle
  `tests/test_public_artifacts.py::test_canonical_base_manifest_matches_tracked_non_specs_files`
  fail at the base revision, because the literal manifest heredoc in
  `.github/workflows/policy.yml` omits the tracked path
  `.aether/objective-contracts/oc_593cb1275b24ea19/v1.md` (reproduced: 397 expected entries,
  398 actual, exactly one extra path). A pull request opened from this base would fail a
  required check without that repair.

## 2. Units

| Unit | Requirements | Independently testable outcome | Writable surface | Depends on |
| --- | --- | --- | --- | --- |
| U1 | DC-01, DC-02, DC-05 (AC2) | `DESIGN.md` and `ROADMAP.md` name the actual accepted decision set and their exact-wording oracle agrees | `DESIGN.md`, `ROADMAP.md`, `tests/test_a1_contracts.py` | root handoff |
| U2 | DC-01, DC-02, DC-05 (AC2, AC3) | Current stage-spec normative owners agree with the accepted per-contract-version board and the accepted bounded-repair boundary without widening role authority | `specs/r5-topology-and-isolation/spec.md`, `specs/r5-topology-and-isolation/research.md`, `specs/r9-state-and-recovery/spec.md`, and any other current stage-spec statement that contradicts those two accepted rules | root handoff |
| U3 | DC-01, DC-03, DC-04, DC-05 (AC1, AC3) | The tracked current `docs/` corpus, the capability registry and its generated reference are truthful about source/tag/installed state, implementation status and documented limits | `docs/**`, `docs/capabilities.toml` and its regenerated reference, `tests/test_documentation.py`, `tests/test_observation_usage_guidance.py` | root handoff |
| U4 | DC-01, DC-03, DC-05 (AC1, AC3) | The root operating map no longer presents earlier objectives as current authority, and the integration index no longer states installation-specific status as portable current product status | `AGENTS.md`, `INTEGRATIONS.md`, `README.md`, `CHANGELOG.md`, `CONTRIBUTING.md`, `CLAUDE.md`, `website/src/lib/docs.ts` (only if a tracked docs path changes), `tests/test_contract_quality_documents.py` (only if a spec-adjacent assertion it owns must change) | root handoff |
| U5 | DC-01, DC-05, AC4 | The required canonical-base manifest gate is green at the candidate revision with no CI-logic change and no weakened check | `.github/workflows/policy.yml` (manifest heredoc region only), `tests/test_public_artifacts.py` | root handoff |
| T | DC-06 (AC4) | Integrated, independently reviewed candidate published through the normal green path with exact `main`/Pages evidence, issue disposition, three separate release conclusions and scoped cleanup | integration, evidence and closeout artifacts only | root + U1–U5 |

`[P]` U1–U5 may run concurrently: their writable surfaces are disjoint and no unit consumes
another unit's intermediate output. U5 is a separate unit rather than part of U4 because the
required-gate repair has its own semantic owner (the canonical base manifest) and its own
oracle, and can be verified independently of any prose wording; folding it into U4 would make
one card span two independently deliverable outcomes. T is genuinely serialized: it consumes
all five reviewed candidates and the single integration branch.

## 3. Shared decisions stamped into every unit

1. Base revision `62ec14653baa8f84449f41a68d64cf64d50939d6`; contract digest
   `89a938565fdb534286d08d09fc586dc9bd51ff5d5b4008738bd1581c3a6693f1`.
2. Work and commit only in your own assigned worktree. No push, pull request, tag, release,
   deployment, runtime activation, credential change or provider call from an Implementer;
   publication belongs to T.
3. Read-only and preserved: `.aether/objective-contracts/**`, `VERSION`, release locks, tags,
   historical evidence and prior failures, and the unrelated uncommitted `DESIGN.md` edit in
   the shared primary checkout (never inspected, staged, reset, copied or deleted).
4. The tracked non-specs surface is frozen: create no new tracked file outside `specs/`. New
   evidence notes live only under `specs/documentation-consistency/evidence/`.
5. Oracle rule: correct an existing assertion only where it enforces the exact revised current
   claim, state why, and never weaken, skip, delete or re-scope a real gate.
6. Committed artifacts stay portable: project-relative paths only, no absolute machine paths,
   no credentials, no private runtime state.
7. Every tracked Markdown file is validated by the required `policy` job: balanced code fences
   and every relative link must resolve. New evidence files must satisfy this.
8. Findings handoff: return a compact structured list (finding, owning question, cited source
   `path:line` at base, correction or reasoned historical/non-applicable classification, files
   changed, test effect, open limit) in the review handoff metadata. T assembles the aggregate
   DC-01/DC-02 inventory from these.
9. Stop-and-report: if a contradiction can only be resolved by changing product behaviour,
   redefining an accepted principle, or making a material owner-reserved decision, stop that
   item and return the evidence instead of expanding scope.
10. Accepted grounding for corrections: `DESIGN.md` PD-73/PD-77;
    `specs/003-objective-contracts/spec.md:54-62`; `specs/r8-workspaces-and-integration/spec.md`
    FR-819b and §7.1; `docs/authority.md` semantic ownership.
11. Oracle file ownership (one writer per file): `tests/test_a1_contracts.py` → U1;
    `tests/test_documentation.py` and `tests/test_observation_usage_guidance.py` → U3;
    `tests/test_contract_quality_documents.py` → U4; `tests/test_public_artifacts.py` → U5.
    A required correction outside your ownership is reported in the handoff, not edited; edits
    must preserve marker text that existing oracles assert.

## 4. Non-build obligations

- **Preservation.** Historical specs, evidence, failed runs, immutable contracts and release
  records stay attributable; at most a dated supersession/status label on a mutable owning entry
  point. The concurrent uncommitted multiharness `DESIGN.md` edit in the primary checkout is
  neither absorbed nor deleted.
- **Source versus release versus runtime.** `VERSION`, the RC17 tag and the installed release
  stay distinct; no document edit may imply activation or qualification.
- **Authority.** Documentation reconciliation only. No product implementation, Hermes fork
  change, new release candidate, installed cutover, manual Pages dispatch, other deployment,
  history rewrite or check bypass.
- **Proportionality.** Focused documentation/contract/capability oracles plus the required
  checks; no synthetic agent campaign, no broad release qualification, no unrelated full-suite
  rerun.

## 5. Terminal closure (T)

Consume the five reviewed units; merge them into the objective branch with one commit or merge
commit per unit; assemble `specs/documentation-consistency/evidence/audit-summary.md` and an
integration receipt; run the integrated verification from `quickstart.md` §2 plus the website
`check`/`build`/`test` path because `docs/**` changed; push and open the pull request against
`main`; obtain every required check without bypass; merge green; verify the exact merged commit
and `origin/main`, the `main` push policy run and the automatic Pages build/deploy with its
public output; reconcile issue #552 with the exact revision; record `release_impact` /
`release_action` / `release_channel` separately from their supporting evidence; retire the
objective-owned unit worktrees and branches after durable evidence and report any retained path
with its concrete reason (the root worktree is T's own workspace and is recorded for post-run
retirement). Morfeo then performs the separate contract-result reception against the exact
integrated revision.

## 6. Local judgement and limits

Wording, ordering, table layout, which narrow existing oracle to run, and equivalent
implementations of an agreed correction belong to Implementer. The initial examples in
`research.md` are a starting inventory, not an exhaustive list: the unit of route judgement is
the whole audit, so confirmations found inside a unit's own corpus are corrected there and
reported. Where a candidate turns out to be already truthful, or correctly labelled history,
record the reasoned non-applicability instead of editing. No claim of unbounded proof is made
by this breakdown.
