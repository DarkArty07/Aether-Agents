# Execution breakdown: Aether 1.0.0-rc.2 prerelease, activation and rollback successor

**Status:** Supervisor-owned execution breakdown for Objective Contract
`oc_742f9f4797494bf9@v1`. It does not widen the contract, redefine material design, or
record acceptance. Unit and card identities, board values and live-state values are held
on the owning execution board and are not published here.

**Source contract:** `.aether/objective-contracts/oc_742f9f4797494bf9/v3.md`
(SHA-256 `2d7b4ff21cca41db14cc09623728a858d851542e54c687a2ff03d55d79009cbc`) on Aether tip
`e1af59c0d0f2684cc149fd362d6933dadb964c2c`, superseding the historical `@v1` breakdown
base documented below as receipt evidence. The `@v1` receipt rows remain historical;
current authority is `@v3`.

**Historical @v1 landing note (superseded):** the original breakdown targeted
`.aether/objective-contracts/oc_742f9f4797494bf9/v1.md`
(SHA-256 `f084eca7e703201c620408069df8f06b89cade82514ceb934c792f71bdda04fc`) on base
`acb89ca85c02c41dca10009b2806428850a0f0bc` (the contract-landing commit on top of the
contract's clean pre-contract base `5758b89dfb19a71719faa8d1821849f8d66acacb`).

**Owning issue:** [#261](https://github.com/DarkArty07/Aether-Agents/issues/261).

**Supersedes:** the breakdown in `specs/001-aether-v1-productization/tasks.md`, which
executed the rejected `oc_3397f9f05d780f8e@v1` lane and remains its historical record.

## Receipt

| Check | Observed |
| --- | --- |
| Portable project | Repository `DarkArty07/Aether-Agents`; contract `project_id` matches the provisioned project binding; contract bytes hash to the envelope digest, `status: final`, `version: 1`, `change_reason: null` |
| Base | Worktree HEAD equals the declared base commit; `origin/main` is `5758b89dfb19a71719faa8d1821849f8d66acacb` and the local `main` carries the contract-landing commit on top of it |
| Maintained fork | `https://github.com/DarkArty07/aether-hermes` `aether-main` tip is the revised accepted pin `aed6591a69f453a1867b73628603e7b53ba40ffc` (fork PR #15 merge, `MERGED`), superseding `7a4fdcd…` after the source-first #461 blocker repair; a clean checkout of that revision exists locally and the commit is present in the fork repository |
| Reused outcomes | The `v1` implementation outcomes the contract reuses are all merged: `#239`/PR #449, `#445`/PR #448, `#446`/PR #452, `#450`/fork PR #14 + PR #455; annotated tag `v1.0.0-rc.1` (object `cda1ecca…` → commit `748aa24…`) and its eight-asset prerelease exist, published-but-rejected |
| Design sufficiency | Owner intent, decisions, in-scope 1–9, out-of-scope, authority, D1–D10, AC-01–AC-10, testing standard and stop conditions settle outcome, interfaces, oracles and authority for the remaining work. No missing material product decision was found; one authority reading is recorded below and raised with the design steward |
| Measured base defect | `tests/test_public_artifacts.py::test_canonical_base_manifest_matches_tracked_non_specs_files` is red at the base for exactly one reason: the contract-landing file `.aether/objective-contracts/oc_742f9f4797494bf9/v1.md` is tracked but not declared in the `.github/workflows/policy.yml` literal manifest (measured: 407 declared vs 408 tracked non-`specs/` paths, one missing name) |
| Release inputs | `VERSION` is `1.0.0rc1`; `.github/workflows/release.yml` `FORK_COMMIT` still pins the rc.1 fork revision `9031bae0…`; no `v1.0.0-rc.2` tag, release or package version exists; the installed runtime is still the pre-RC live-tree-patched release |
| Pre-state baseline (design-steward note, independently re-read here) | The pre-RC runtime's `aether doctor --json` already returns `result: error` with `LIFECYCLE_INTEGRITY_FAILED` / `ACTIVE_RELEASE_INVALID` (`active_release_id=null`, manager `0.24.0`, observer unavailable) while the Aether-owned gateway stays active and the execution board is live. This is a **pre-existing baseline condition, not rc.2 evidence and not authority for a runtime-only edit**: the activation lane records it as its pre-state and must still reach a clean post-activation `doctor` plus the gateway/ticker/board/projection evidence |
| Environment limits | One 12-CPU host, memory and `/tmp` are shared with unrelated concurrent flows; the canonical full-suite bootstrap and the website suite are the load-sensitive surfaces, so the two heavy qualification units are serialized by an explicit edge |

## Cross-artifact executability

| Concern | Settled conclusion | Execution consequence |
| --- | --- | --- |
| What is actually left | The contract's in-scope 1–3 and D1–D4 are already merged into the clean base and are reused, not redone. The live work is in-scope 4–9: rc.2 identity, deterministic bundle, publication, local activation with rollback/forward proof, issue truth and residue | Units below cover the remaining scope only; reuse is verified from primary sources rather than re-executed |
| Publication ownership | Implementer units never push, open a PR, merge, tag, publish, activate or mutate issues. Publication steps belong to Supervisor after independent review | Two Supervisor integration cards own push/PR/checks/merge and tag/prerelease/verification |
| Release source identity | The published bundle is built by the repository's own release workflow at the tag commit, and the tag commit must equal `origin/main`. The rc.2 source, `VERSION` and the `FORK_COMMIT` pin must therefore land on `main` before the tag is pushed | Identity lands first, gates run at the merged tip, publication follows the gates |
| Rc.1 immutability | Rc.1's tag, commit, eight asset bytes and rejection warning are read-only evidence; no asset replacement, `--clobber`, tag move or `--force` is permitted at any point | Verification is read-only; the rc.1 defect is remedied only by the successor artifact |
| Promotion order | Source → independent review → green merge to `main` → tagged release → local runtime activation → canary. No runtime-only edit, live-tree patch or pre-release activation may substitute for a source change, and the graph below enforces the order through its parent edges | Each stage consumes only its predecessor's accepted output; the published bytes are the only activation input |
| `aether update` local route | The candidate's own CLI provides the pinned local-candidate route (`--local`, `--aether-checkout`, `--aether-commit`, `--fork-checkout`, `--fork-commit`, `--dry-run`, `--yes`, `--json`); it requires a clean Aether checkout whose HEAD is the exact commit carrying **exactly one** annotated release tag equal to `v` + the display version, a clean fork checkout at the exact commit reachable from `aether-main`, compatible Python, and current HLP coverage. Identity never comes from cwd, recency or a mutable branch tip | Activation can only run after the tag exists, from a clean checkout of the tagged commit and a clean checkout of the accepted fork commit; the preview is non-mutating and must be recorded before activation |
| Activation interruption | Activation rewrites the Aether-owned service/launcher/Desktop projections and restarts the Aether-owned gateway, which owns the dispatcher and every running worker, including this objective's controller session. The unrelated gateway service is never touched | The activation lane is the terminal card's work, sequenced so all evidence is durable first, with an explicit resume checkpoint |
| Deployment boundary | The repository's own Pages workflow triggers on pushes to `main` touching `docs/**`, `website/**` or the Pages workflow itself, and it deploys to the existing public site. The contract authorizes exactly one automatic existing-site deployment (the one caused by the reviewed #446 merge) and forbids manual dispatch, another target or any deployment beyond it. All programmatically required rc.2 changes live in root files (`.aether/**`, `VERSION`, `CHANGELOG.md`, `README.md`, `AGENTS.md`, `.github/workflows/{release,policy}.yml`, `tests/**`), which do **not** trigger that workflow | **No unit may modify `docs/**`, `website/**` or `.github/workflows/pages.yml`.** The public-capability registry's "activation lane pending" clause is falsified once rc.2 is activated; that coherence gap is recorded as an explicit residual and raised with the design steward instead of being fixed by an unauthorized deployment |
| Patch/ledger corpus | `.patch` files and HLP records are audit/reconstruction evidence and are never replayed onto the active runtime; the reconciliation corpus must nevertheless validate in check mode against the accepted fork revision, because the candidate's own local route consumes it | The bundle/release-input unit runs the validator in check mode with the fork checkout at the accepted revision |
| Publication mechanics | `gh release edit` accepts no file arguments, so a reconcile re-run verifies the published assets and attaches nothing; the create path attaches exactly the tool's qualified member set. Release notes carry the release's own truth statement | Publication verification is download-and-rehash against `SHA256SUMS` plus lock identity, exactly as the workflow's own verifier does |
| Test standard | `CONTRIBUTING.md` bootstrap plus the contract's testing standard; no gate weakening, no new skip, no fabricated platform evidence. WSL2/macOS/Windows remain explicitly unverified | Gate evidence is taken at the merged revision; a local run under concurrent load is not reported as a gate number |

## Unit map

| Source | Unit | Outcome |
| --- | --- | --- |
| AC-01, AC-03, AC-04, AC-05; reuse clause | **RC2-VERIFY-PRE** (Implementer, root-gated) | One independent primary-source verification record: clean pre-contract base and fork pin with reviewed PR/check/merge evidence; #446's three commits reviewed, merged and live on the existing site; #450's fork/Aether merges plus a re-run of the disposable-board canary; rc.1 tag/commit/asset bytes unchanged with its rejection warning. Read-only |
| In-scope 5; D6; AC-02 (source half); AC-01 (pin half) | **RC2-IDENTITY** (Implementer, root-gated) | The rc.2 release identity in canonical source: `VERSION` `1.0.0rc2`; a truthful changelog entry; a README status paragraph that is true of the tagged artifact and carries the non-claims; the accepted `FORK_COMMIT` pin; the contract-landing manifest line; root guidance coherence; every coupled oracle measured RED/GREEN. Excludes `docs/**`, `website/**` and the Pages workflow |
| In-scope 6 (bundle half), testing standard; D6 (source half) | **RC2-GATES** (Implementer, parent: identity integration) | The canonical gate battery measured at the merged revision: full bootstrap with `--clean-between-groups` and the coverage gate, Ruff check/format, mypy, documentation and public-artifact checks, build, whitespace checks, and the website `npm ci`/`check`/`build`/`test`/`e2e` plus Pages-path build and path verification, all local |
| In-scope 6 (determinism/privacy half); AC-06; D6 (bundle half) | **RC2-BUNDLE** (Implementer, parent: gate unit) | The deterministic release-bundle qualification at the merged revision: two clean roots produce byte-identical eight-member bundles, lock schema/identity validation, member inspection, privacy/secret scans, normal-resolver clean install into fresh roots, the shipped release step's attach/reconcile behaviour, and the HLP reconciliation check at the accepted fork revision |
| In-scope 7 (publication); D7; AC-07 | **RC2-INTEGRATE** (Supervisor, same flow, non-terminal) | Reviewed identity pushed, normal PR, required checks green, green merge without bypass; the accepted main revision recorded for the gate units |
| In-scope 6 (qualification acceptance), 7 (release); D6 (final bytes), D7; AC-06 (final), AC-07 | **RC2-PUBLISH** (Supervisor, same flow, non-terminal) | Annotated tag `v1.0.0-rc.2` on accepted main, pushed; the repository's own release workflow builds and attaches the qualified member set; prerelease properties, tag target, release notes truth and every downloaded asset verified against the qualified bundle and the lock identity |
| In-scope 4, 8, 9; D5, D7 (retention), D8, D9, D10; AC-05 (retention), AC-08, AC-09, AC-10 | **RC2-ACTIVATE-CLOSEOUT** (Supervisor, same flow, `terminal=true`) | Local preview and refusals, activation of the published bytes, post-restart runtime/state/projection battery, rollback rehearsal, forward reactivation, rc.1 non-mutation witness, issue truth for #261/#239/#440/#445/#446/#439/#450, objective-owned residue cleanup with preserved items reported, and the terminal report with its three release conclusions stated separately from their evidence |

## Execution graph

```text
decomposition root (Supervisor)
    ├── RC2-VERIFY-PRE  (Implementer; read-only verification)
    └── RC2-IDENTITY    (Implementer; rc.2 source identity)

RC2-IDENTITY → reviewed → RC2-INTEGRATE (Supervisor; PR, checks, green merge)
                                          ├── RC2-GATES   (Implementer; at the merged revision)
                                          │      └── RC2-BUNDLE (Implementer; after the gate unit)
                                          └── RC2-PUBLISH (Supervisor; tag, release workflow, verification)

RC2-PUBLISH → RC2-ACTIVATE-CLOSEOUT (Supervisor; terminal=true)
```

Same-card Supervisor review applies to each Implementer unit; the integration and
terminal cards consume reviewed units and never replace unit review.

## Dependency rationale

- `RC2-INTEGRATE` cannot start before the identity unit is reviewed and its branch is
  durably available, and before the read-only verification unit has reported, because the
  integration report must consume both.
- `RC2-GATES` and `RC2-BUNDLE` must run on the **merged** revision: the tag is created on
  that revision, so a candidate-branch measurement would not describe the published tree.
- `RC2-BUNDLE` is gated behind `RC2-GATES` for resource serialization only, and that edge
  is recorded as such: the two units share one 12-CPU host, and the canonical bootstrap
  plus the browser suite must not run beside the two bundle builds on a machine whose
  memory is already mostly committed. No functional prerequisite exists between them.
- `RC2-PUBLISH` consumes the gate and bundle evidence; publishing before the gates would
  contradict the stop condition on unreviewed or red source.
- `RC2-ACTIVATE-CLOSEOUT` depends on the published identity and is the only step that may
  interrupt Aether-owned instances.
- `RC2-VERIFY-PRE` and `RC2-IDENTITY` share no writable file (the first writes only its
  evidence record) and may run together.

## Shared decisions stamped into every unit card

1. Authority is Objective Contract `oc_742f9f4797494bf9@v3` (SHA-256
   `2d7b4ff21cca41db14cc09623728a858d851542e54c687a2ff03d55d79009cbc`) plus this
   breakdown. Skills are reusable procedure only. Never create, edit, stage or copy the
   canonical contract.
2. Release identity: package version `1.0.0rc2`; annotated tag and GitHub prerelease
   `v1.0.0-rc.2`; `release_impact=major`, `release_action=publish`,
   `release_channel=prerelease`. Rc.1 stays byte-immutable, published and rejected.
   Only the Supervisor integration cards push, merge, tag or publish.
3. Non-negotiable preservation: never edit the owner's primary checkout or its
   uncommitted paths, the live runtime release under the Aether XDG data root, any
   mutable state under the Aether XDG state root, `home/`, credentials or
   provider/model/router configuration, the unrelated gateway service, the generic
   `hermes` entry point, unrelated worktrees/branches/stashes/boards, or the migration
   backups. Implementer units make no remote or live effect.
4. Maintained-fork identity: executable Hermes source is `DarkArty07/aether-hermes`
   branch `aether-main`; this objective's accepted revision is
   `aed6591a69f453a1867b73628603e7b53ba40ffc`. This supersedes `7a4fdcd…`
   after the reviewed #461 recovery fix; Hermes keeps its own distribution
   identity (`hermes-agent`). `.patch` files and HLP records are audit/reconstruction
   evidence and are never replayed onto the active runtime.
5. Deployment boundary: no unit may change `docs/**`, `website/**` or
   `.github/workflows/pages.yml`, because a push to `main` touching them deploys the
   existing public site and only the #446-caused automatic deployment is authorized.
   Any status statement living in those paths is reported as a residual instead.
6. Environment identity: the installed runtime is still the pre-RC live-tree-patched
   release; the candidate CLI is the one in the source tree. Activation is the only step
   that may change the active release, and it must run from the candidate's own CLI with
   explicit clean checkouts.
7. Evidence: each unit writes exactly one record at
   `specs/001-aether-v1-productization/evidence/<unit-id>.md`; larger logs travel as
   native task attachments. No secrets, credentials, provider/model/router bindings,
   operator paths, live-state values, board/card identities or machine-specific paths in
   portable artifacts.
8. Test standard (`CONTRIBUTING.md`, not weakened): focused nodes first, then the
   canonical commands for the surfaces the unit touches; a skip is never added or
   weakened to obtain green, and a run under abnormal load is reported as such instead
   of as a gate number.
9. Tracked files outside `specs/` require a literal `.github/workflows/policy.yml`
   manifest entry; each unit records the exact expected line in its handoff.
10. Unit review is same-card (`kanban_request_review`, reviewer `supervisor`); the
    integration and closeout cards consume reviewed units. A unit reports its own
    compatibility evidence; only the terminal report aggregates the three release
    conclusions.
11. If inspection shows a unit is oversized, colliding or unsupported by the contract,
    stop expanding it and return a source-backed question through the card's
    collaboration path instead of widening scope or weakening an oracle.

## Correction: withdrawn post-canary lane (2026-09-15)

An earlier revision of this breakdown (commit `073aafa`, preserved in history as
evidence) recorded a post-canary docs-coherence lane and described it as
owner-authorized. That description was **withdrawn by the design steward**: neither the
Objective Contract nor the current owner instruction authorizes it, no such work was
performed, and the two board cards created for it were reconciled as not applicable. The
deployment boundary recorded in the receipt table therefore stands unchanged for this
objective — no `docs/**`, `website/**` or Pages-configuration change and no deployment.
The capability-registry staleness that rc.2 activation produces is reported as the
contract-defined out-of-scope residual rather than fixed within this objective.

## Verification of this decomposition

Traceability: every contract in-scope item 4–9, deliverable D5–D10 and acceptance
criterion AC-01–AC-10 maps to exactly one unit above; in-scope 1–3 and D1–D4 are the
reused, already-merged v1 outcomes that `RC2-VERIFY-PRE` re-derives from primary sources.
Independence: the two root-gated units write disjoint files; the gate and bundle units
run at a common revision with a declared resource serialization; publication and
activation are serialized by authority and by the interruption they cause. No unit is
created merely to fill capacity, and no acceptance criterion is waived to make the graph
look parallel.
