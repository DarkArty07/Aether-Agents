# Execution breakdown: Aether 1.0.0-rc.1 lifecycle, maintained-fork runtime and prerelease

**Status:** verified executable decomposition for Objective Contract
`oc_3397f9f05d780f8e@v1`. This is the Supervisor-owned execution breakdown; it does not
widen the contract, redefine the material design in `spec.md`/`plan.md`/`research.md`, or
record acceptance.

**Derived by:** Supervisor (root task `t_a3b2d549`, flow
`aether.flow.v1:914a7478187c08169337f2a765a77b4f656ce2a172ebafac93621b34494354db`).

**Source contract:** `.aether/objective-contracts/oc_3397f9f05d780f8e/v1.md`
(SHA-256 `4d4c7650bf8ea93fc7cffe3d87f7f974e172d66cefcf6a74a2d83051568a4879`) on base
`410c172ae69ffa87f6e32960ae4aef3b8d6598f0`.

**Owning issue:** [#261](https://github.com/DarkArty07/Aether-Agents/issues/261); consumed
blockers [#437](https://github.com/DarkArty07/Aether-Agents/issues/437),
[#438](https://github.com/DarkArty07/Aether-Agents/issues/438).

## Receipt

| Check | Observed |
| --- | --- |
| Portable project | `.aether/project.toml` `project_id` `12027989-a08f-41cd-a82c-54ff1bfb6b03` matches the envelope; repository `DarkArty07/Aether-Agents` |
| Contract bytes | SHA-256 `4d4c7650bf8ea93fc7cffe3d87f7f974e172d66cefcf6a74a2d83051568a4879`; `status: final`, `version: 1`, `change_reason: null` |
| Base / branch | Base `410c172ae69ffa87f6e32960ae4aef3b8d6598f0` (`main`, PR that lands the contract); objective branch as provisioned by the dispatcher |
| Maintained fork | `https://github.com/DarkArty07/aether-hermes` remote `aether-main` `bb5e9a422f3135371557e75bcd1db01c5f8fc3ba`; provisioned checkout clean at `54eeb56dabefc98821d696656ed58c55dd777346` (three commits ahead, no open PR) |
| Design sufficiency | Decisions (release identity, maintained fork, layout, authority selector, local updates, interrupting activation, publication, service) plus owner intent, in-scope 1–12, out-of-scope, authority, D1–D12, AC-01–AC-15, testing standard and stop conditions settle outcome, interfaces, oracles and authority; no missing material product decision found |
| Release blockers | #437 (tracked `HLP-425` patch missing from the `.github/workflows/policy.yml` literal manifest; Monitor D15R laboratory fixture requests review without a distinct reviewer) and #438 (exact-runtime Monitor test leaks imported Hermes modules across test order into ambient live state) are open and reproduced by the contract |
| Observed layout | `$XDG_DATA_HOME/aether/{runtime,components}` holds one immutable release (`runtime/current` symlink, `manifests/release-origin.txt` still records a live-tree patch digest) and `$XDG_STATE_HOME/aether/{hermes,knowledge,monitor,observations,projects,migrations}` holds all mutable state; the Aether-owned gateway unit currently hardcodes one release path, so it does not follow the active selector yet |
| Authority / profiles | `implementer`, `supervisor`, `morfeo` profiles exist; no new role, profile or limit is introduced; implementer capacity is queue-bound by the existing per-profile limit |
| Project Canonical Skills | `.aether/skills/aether-observe/SKILL.md` (observation procedure, no authority) |
| Preserved residue | Two uncommitted launcher-separation changes in the primary checkout (`scripts/aether_tui.py`, `tests/test_aether_tui_launcher.py`), many unrelated worktrees/branches/stashes, the pre-separation runtime and migration backups, the unrelated `hermes-gateway-hestia` service and the generic `~/.local/bin/hermes` |

## Cross-artifact executability

| Concern | Settled conclusion | Execution consequence |
| --- | --- | --- |
| Two repositories | Aether owns source identity, update/rollback lifecycle, reconciliation evidence, release tooling, docs and closeout; the fork owns its runtime source, docs and tests | Fork units work in nested isolated worktrees resolved by remote URL; never mutate a checkout whose current branch is `aether-main` in place, never copy or edit the live runtime |
| Obsolete source model | `hermes-baseline.json` + `transitional_fork` lock mode replay residual `.patch` files; the contract retires that for the RC and binds the maintained fork by repository, exact commit, tree digest, artifacts and provenance | `LC-RUNTIME` owns lock/schema/baseline reconciliation and must refuse the retired mode with an actionable message; `.patch` files stay audit evidence and are never applied to `runtime/current` |
| Local candidate route | `aether update` gains a non-mutating local preview and explicit interrupting activation from explicit clean commits; identity never comes from cwd or recency | `LC-RUNTIME` implements it under the pinned CLI surface (Shared decision 5); `LC-DOCS` documents exactly that surface and the derived capability registry must match the real parser |
| Release tooling split | `LC-RELTOOL` authors and unit-tests build/qualification/workflow tooling on a clean commit of its own; the integration card runs the accepted tooling against the integrated commit | No implementation unit needs another unit's accepted commit as its base; the bundle is built once, from the integrated tree |
| Activation interruption | Activating the RC rewrites the Aether-owned service/launcher/Desktop projections and restarts the Aether-owned gateway, which owns the dispatcher and every running worker (including this objective's controller session) | The real activation/rollback/forward-activation lane is terminal-card work, sequenced so all evidence is durable first (Shared decision 12); the unrelated `hermes-gateway-hestia` service is never touched |
| `policy.yml` literal manifest | Every tracked non-`specs/` file must appear in the workflow heredoc; units that add or rename such files record the exact lines instead of editing it | Measured at `410c172`: the heredoc holds 400 entries against 402 tracked non-`specs/` files, missing `patches/hermes/HLP-425-review-flow-continuity.patch` (#437) and `.aether/objective-contracts/oc_3397f9f05d780f8e/v1.md` (added by the contract commit itself). `LC-BLOCK` corrects both lines, because the manifest test compares the whole list and #437 cannot be shown green with only one; the integration card applies lines recorded for files other units add |
| Test standard | `CONTRIBUTING.md` Python 3.11–3.13 exact-Hermes bootstrap; no gate weakening, no new skip | Units run focused nodes first, then the canonical commands for the surfaces they touch (Shared decision 11) |
| Publication | Implementer units never push, PR, merge, tag, release, activate or mutate issues | `LC-INT` and `LC-CLOSE` own all remote and live effects under Shared decision 3 |

## Unit map

| Source | Unit | Outcome |
| --- | --- | --- |
| In-scope 1, 7, 11; D1; AC-15 | **LC-DOCS** (Implementer, root-gated) | Canonical design/spec/guide/capability/changelog reconciliation for maintained fork, XDG layout, interrupting update/rollback and RC scope, with the derived capability registry matching the real CLI surface and no competing authority |
| In-scope 2; D7; AC-10 (focused) | **LC-BLOCK** (Implementer, root-gated) | #437 and #438 closed by reproduced fixes: literal manifest entry for `patches/hermes/HLP-425-review-flow-continuity.patch`, a D15R fixture that names a distinct reviewer, and order-independent exact-Hermes Monitor tests that never read ambient live state |
| In-scope 8; D6; AC-01 (fork half), AC-02 (fork half) | **LC-FORK** (Implementer, root-gated) | One clean reviewed `aether-hermes:aether-main` candidate carrying every accepted active HLP behavior, with fork docs/tests and packaging identity reconciled, ready for a normal PR without history rewrite |
| In-scope 3, 4, 5, 6, 9, 10 (disposable); D2, D3, D4, D5; AC-01–AC-08 | **LC-RUNTIME** (Implementer, root-gated) | Maintained-fork release lock and deterministic validation, one `aether update` local-candidate route with non-mutating preview and clean-source refusal, XDG active record with versioned staging/`runtime/current`/launcher/Desktop/service projections, transition recovery, state-preserving rollback, doctor mismatch diagnostics, reconciled HLP ledger/evidence generation, and disposable-home tests including interruption/fault injection |
| In-scope 7, 11; D8; AC-05, AC-11, AC-12 (tooling) | **LC-RELTOOL** (Implementer, root-gated) | `VERSION`/changelog/release-workflow/closeout tooling that builds, inspects and hash-binds one exact release bundle (wheel, sdist, fork runtime closure, release lock, provenance, `SHA256SUMS`) and produces package-member and clean-install reports |
| In-scope 12; D7, D8, D10; AC-10 (integrated), AC-11, AC-12 | **LC-INT** (Supervisor, same flow, terminal=false) | Integrated gates on the merged candidate, fork PR and Aether PR through required checks and green merge without bypass, annotated tag `v1.0.0-rc.1`, GitHub prerelease carrying the exact qualified artifacts, and downloaded-artifact identity verification |
| In-scope 10 (real lane), 12; D9, D10, D11, D12; AC-06–AC-09, AC-13, AC-14 | **LC-CLOSE** (Supervisor, same flow, terminal=true) | Bounded real local update → verify → rollback → forward-activate lane on the published bytes, three-role pipeline E2E, issue/state truth, objective-owned residue cleanup and the final evidence report |

## Execution graph

```text
t_a3b2d549 (Supervisor decomposition root)
    ├── LC-DOCS     (Implementer; base 410c172)
    ├── LC-BLOCK    (Implementer; base 410c172)
    ├── LC-FORK     (Implementer; base 410c172; nested fork worktree)
    ├── LC-RUNTIME  (Implementer; base 410c172)
    └── LC-RELTOOL  (Implementer; base 410c172)

LC-DOCS, LC-BLOCK, LC-FORK, LC-RUNTIME, LC-RELTOOL
    → same-card Supervisor review on each unit
    → LC-INT    (Supervisor, same flow, consumes every reviewed unit)
    → LC-CLOSE  (Supervisor, same flow, terminal=true)
```

The five implementation units are disjoint in writable surface and none requires another
unit's accepted commit as its base, so they can run together within existing capacity.
Real serialization is the integration/closeout chain:

- `LC-INT` cannot start before every consumed unit is independently reviewed and its
  branch is durably available; it merges the reviewed units, applies the recorded
  manifest lines, regenerates HLP reconciliation evidence at the accepted fork revision
  with the accepted generator, then runs the integrated gates.
- `LC-CLOSE` consumes the published identity, so it depends on `LC-INT`; and its real
  activation lane is the only step that may interrupt Aether-owned instances.
- `LC-RUNTIME` is materially concentrated by necessity: the lock/source-identity,
  prepare/activate/recover/rollback, CLI and layout semantics live in one module
  (`src/aether_agents/lifecycle.py`) whose regions are byte-coupled, and concurrent edits
  to one file are not independent. Splitting it into two cards would create a real
  same-file collision and a chained base that no implementer card can pin.

## Shared decisions stamped into every unit card

1. Authority is Objective Contract `oc_3397f9f05d780f8e@v1` (SHA-256
   `4d4c7650bf8ea93fc7cffe3d87f7f974e172d66cefcf6a74a2d83051568a4879`) on base
   `410c172ae69ffa87f6e32960ae4aef3b8d6598f0`, plus this breakdown. Skills are reusable
   procedure only. Never edit, stage or exact-copy the canonical contract.
2. Release identity: Aether package version `1.0.0rc1`; annotated tag and GitHub
   prerelease `v1.0.0-rc.1`; `release_impact=major`, `release_action=publish`,
   `release_channel=prerelease`. Only `LC-INT`/`LC-CLOSE` publish.
3. Non-negotiable preservation: never edit or overwrite the owner's primary checkout
   (including its two uncommitted launcher changes), the live runtime release in
   `$XDG_DATA_HOME/aether/runtime`, any mutable state under `$XDG_STATE_HOME/aether`,
   `home/`, credentials/provider/model/router configuration, the unrelated
   `hermes-gateway-hestia` service, the generic `~/.local/bin/hermes`, unrelated
   worktrees/branches/stashes/boards, or the pre-separation backup trees. Implementer
   units make no remote or live effect: no push, PR, merge, tag, release, issue mutation,
   service restart, activation, or direct SQL board cleanup.
4. Maintained-fork identity: executable Hermes source is `DarkArty07/aether-hermes`
   branch `aether-main`; the candidate revision for this objective is
   `54eeb56dabefc98821d696656ed58c55dd777346`, three commits ahead of remote
   `bb5e9a422f3135371557e75bcd1db01c5f8fc3ba`. Hermes keeps its own distribution
   identity (`hermes-agent` 0.20.1) unless an independently required packaging
   correction is accepted in review. `.patch` files and HLP records are
   audit/reconstruction evidence; they may never be replayed onto `runtime/current`.
5. Pinned local-route CLI surface (must match the real parser and the capability
   registry): `aether update --local --aether-checkout PATH --aether-commit SHA
   --fork-checkout PATH --fork-commit SHA [--dry-run] [--yes] [--json]`. `--local` is
   mutually exclusive with `[VERSION]`, `--prerelease`, `--wheel`, `--hermes-checkout`
   and `--release-lock`; preview is non-mutating; dirty trees, ambiguous or missing
   checkouts, wrong repository/branch, unknown or mismatched commits, bad hashes and
   incompatible Python are refused without staging or activation; identity is never
   derived from cwd, recency or a mutable branch tip. `docs/reference/cli.md` and
   `docs/capabilities.toml` (`cli.option.aether.update.--local`, `--aether-checkout`,
   `--aether-commit`, `--fork-checkout`, `--fork-commit`) must declare exactly these
   surfaces. If real inspection proves the vocabulary materially wrong, return the delta
   to Supervisor instead of silently diverging in one unit.
6. Pinned release-lock identifiers: `schema_version` 4; `hermes.source_mode`
   `maintained_fork` with `hermes.repository` const `https://github.com/DarkArty07/aether-hermes`,
   exact `commit`, `source_tree_sha256`, Hermes `version`/`tag`, `python_requires` and an
   `artifacts` closure; the packaged resource copy under
   `src/aether_agents/resources/schemas/` and the contract copy under
   `specs/001-aether-v1-productization/contracts/` stay byte-identical. The retired
   `transitional_fork` mode (fixed public baseline + residual patch replay) is refused for
   new preparation with an actionable message, and no `.patch` replay path is enabled.
7. Layout: immutable releases/components stay under the Aether XDG data root
   (`$XDG_DATA_HOME/aether/{runtime,components}`); every mutable state stays under the
   Aether XDG state root (`$XDG_STATE_HOME/aether/...`); the lifecycle reconciles to this
   installed layout rather than moving or copying live state; rollback never rolls user
   state backward.
8. Authority selector: exactly one authenticated active-release record is authoritative;
   `runtime/current`, the launcher, the Desktop entry and the Aether-owned systemd unit
   projection must agree with it after one transition; a partial transition is detected
   and recoverable; `aether doctor` reports actionable fail-closed diagnostics instead of
   silently degrading.
9. Interruption: activation may stop and restart Aether-owned TUI/gateway/workers
   immediately with no drain semantics; durable state must stay recoverable when the
   owner reopens instances; unrelated services must keep running.
10. Evidence: each unit writes exactly one record at
    `specs/001-aether-v1-productization/evidence/<unit-id>.md`; larger logs travel as
    native task attachments. No secrets, credentials, provider/model/router bindings,
    operator paths, live-state values or machine-specific paths in portable artifacts.
11. Test standard (`CONTRIBUTING.md`, do not weaken): focused nodes first, then
    `uv run --frozen python scripts/run_tests.py`, `uv run --frozen ruff check
    src/aether_agents tests scripts`, `uv run --frozen ruff format --check src/aether_agents
    tests scripts`, `uv run --frozen mypy src/aether_agents`, `uv run --frozen pytest -q
    --cov=aether_agents --cov-report=term-missing`, `uv run --frozen python
    scripts/check_documentation.py`, `uv build`, `git diff --check`,
    `git diff --cached --check`, and `scripts/validate_hermes_patch_reconciliation.py` in
    its documented check mode. A skip is never added or weakened to obtain green.
12. Sequencing for the real activation lane: capture every pre-state identity, preview
    and disposable-home result durably before the first interrupting step, then run
    activation, rollback rehearsal and forward activation in that order; the final
    verification happens after the owner's instances reopen. Never restart an unrelated
    service, never edit `.env`/credentials, and never fabricate post-restart evidence.
13. Unit review is same-card (`kanban_request_review`, reviewer `supervisor`); the
    integration and closeout cards consume reviewed units and never replace unit review.
    A unit reports its own compatibility evidence; only the terminal report aggregates
    `release_impact`/`release_action`/`release_channel`.
14. Adding, renaming or removing a tracked file outside `specs/` requires a literal
    `.github/workflows/policy.yml` manifest entry. Record the exact expected lines in the
    handoff; only `LC-BLOCK` edits the manifest directly (for the `HLP-425` line), and the
    integration card applies every other recorded line as bounded integration repair.
15. If real inspection shows this unit is oversized, colliding or unsupported by the
    contract, stop expanding it: return a source-backed question to Supervisor through the
    card's collaboration request path (`recipient: controller`) and keep unaffected parts
    moving. Do not silently widen scope, weaken an oracle, or create sibling cards.

16. Integration-bound gates (measured at `410c172`). Two required verification gates span
    more than one unit's exclusive surface and are therefore satisfied on the merged tree,
    not on a unit branch:
    - `scripts/check_documentation.py` enforces its registry/parser mapping
      bidirectionally (`uncovered derived surface` at `scripts/check_documentation.py:419`,
      `derived surface is not source-derived` at `:422`). `LC-DOCS` owns the registry rows
      and `LC-RUNTIME` owns the parser options, so each branch reports exactly the errors
      attributable to the other unit's pending deliverable, in opposite directions.
      Neither unit may take the other's surface, neither may claim green, and both record
      the exact attributable error text in their evidence. `LC-INT` verifies green on the
      merged tree and may run the generator's `--write` mechanically, proving the rendered
      reference is byte-identical.
    - The literal `policy.yml` manifest is compared as a whole list by
      `tests/test_public_artifacts.py::test_canonical_base_manifest_matches_tracked_non_specs_files`,
      so `LC-BLOCK` corrects both missing lines (see the executability row).
17. Owning-artifact reconciliation for the four decisions (in-scope 1, D1, AC-15). A1
    `spec.md` §10 "Impact and reconciliation" already requires it in its own words: the
    owning and derived artifacts MUST be reconciled before implementation closes, and it
    names R4, R9, R11 and R13 among them; `DESIGN.md` §12/§13 assigns those questions to
    those stages and states that another artifact "may not become a competing source of
    truth". Measured at the LC-DOCS review: live normative statements still contradict the
    contract decisions and must be reconciled in the owning stage artifacts.
    - maintained fork: `specs/r4-hermes-boundary/spec.md` FR-403a/FR-403b (a release lock
      "MUST declare `upstream` or `transitional_fork`") and FR-425;
      `specs/r11-evidence-and-observability/spec.md` FR-1138 ("the exact locked public
      `upstream` or `transitional_fork` artifact");
      `specs/r13-synthesis-and-release/spec.md` FR-1337 and its component list;
      `specs/r13-synthesis-and-release/research.md` §18.3 and
      `specs/r4-hermes-boundary/research.md` (release-mode decision records).
    - post-separation layout: `specs/r9-state-and-recovery/spec.md` §2.1 places `profiles/`
      and `projects/` under `~/.local/share/aether/`, and
      `specs/r13-synthesis-and-release/plan.md` repeats that tree; the accepted layout puts
      every operational Hermes home and all product state under the XDG state root.
    - release-lock schema: `specs/r13-synthesis-and-release/plan.md` states "release-lock
      schema is integer `3`", which
      `tests/test_a1_contracts.py::test_release_lock_schema_and_plan_agree_on_version_three`
      asserts together with the schema constant. `LC-RUNTIME` owns the schema and that test;
      the plan line is `LC-DOCS`'s. Neither may change alone, and the test must not be
      weakened.
    - historical records are preserved, not rewritten: research decision records and
      completed checklists receive a dated superseding note rather than deletion, matching
      the treatment already applied to the A1 artifacts.
    - `ROADMAP.md` must stop designating a contradicting artifact as the current
      synthesis/entry while pointing readers at it for the testing standard.
18. Delegated-child snapshot leak (issue #404, HLP-310). Measured by the terminal card
    before activation: the pre-RC installed runtime leaks `HERMES_DELEGATED_CHILD_CONTEXT`
    and `HERMES_KANBAN_*` into the reusable terminal snapshot, while the maintained-fork
    candidate excludes both. Canary (portable, disposable roots, module origins printed):
    `specs/001-aether-v1-productization/fixtures/hlp310_snapshot_canary.py`; its RED and
    GREEN legs and the candidate's focused regression are recorded in
    `specs/001-aether-v1-productization/evidence/LC-CLOSE.md` §3. No fork source repair is
    required, so no additional implementer unit exists for it. Obligations: `LC-INT` runs
    the candidate's `tests/tools/test_delegate_kanban_isolation.py` and
    `tests/tools/test_snapshot_session_id_leak.py` at the merged fork commit with the
    fork's own runner; `LC-CLOSE` re-runs the canary on the activated RC. Issue #404 closes
    only when the accepted commit carries the exclusion, those modules pass at it, and the
    canary passes on the activated runtime — otherwise it stays open with the failure
    recorded. This is a directly evidenced behavioral claim about HLP-310, so it is never
    accepted from historical focused tests alone.

## LC-DOCS — canonical design, docs and capability reconciliation

- Source: contract Owner Intent / Decision "Maintained fork" / "Layout" / "Activation
  interruption" / "Release identity"; in-scope 1 and 11; deliverable D1; AC-15.
- Outcome: the owning design, roadmap, root guidance, guide/reference docs, capability
  registry and the owning stage artifacts state the accepted RC reality without competing
  authority (`CHANGELOG.md` and `VERSION` remain `LC-RELTOOL`'s exclusive surface): the
  maintained fork (not the fixed public baseline, not a `.patch`/editable replay) as
  executable Hermes source, the post-separation XDG data/state layout, the supported
  interrupting `aether update` local-candidate route and state-preserving rollback, the
  bounded RC scope (`1.0.0rc1`, tag `v1.0.0-rc.1`, prerelease, `major`/`publish`), and
  the explicit remaining stable/PyPI/WSL2 gates. Excludes runtime code, schema,
  ledger/evidence machinery, release tooling, push/PR/tag/publication, and any live effect.
- Inputs: base `410c172`; Contract decisions and AC-15; the pinned CLI surface and release
  identity (Shared decisions 2, 5); observed live layout as evidence only; the
  owning-artifact reconciliation debt and its measured statement list (Shared decision 17).
  No prerequisite unit.
- Boundaries: writable `DESIGN.md`, `ROADMAP.md`, root `AGENTS.md`, `README.md`,
  `docs/**` including `docs/capabilities.toml` and the generated
  `docs/reference/capabilities.md`, `specs/001-aether-v1-productization/spec.md`,
  `plan.md`, `research.md` and `contracts/cli.md`,
  `specs/r4-hermes-boundary/{spec.md,research.md}`,
  `specs/r9-state-and-recovery/spec.md`,
  `specs/r11-evidence-and-observability/spec.md`,
  `specs/r13-synthesis-and-release/{spec.md,plan.md,research.md}` — the stage surfaces only
  as far as Shared decision 17's measured statements — plus this objective's
  `specs/001-aether-v1-productization/evidence/LC-DOCS.md`. Preserve
  `HERMES_LOCAL_PATCHES.md`, `specs/001-aether-v1-productization/tasks.md`,
  `specs/001-aether-v1-productization/evidence/**` other than the unit record,
  `specs/001-aether-v1-productization/contracts/release-lock.schema.json`,
  `src/**`, `scripts/**`, `tests/**`, `.github/**`, `VERSION`, `CHANGELOG.md`, and every
  R0–R12 stage artifact other than the three named above.
- Judgement: wording, structure, which documents need the RC statement, and whether a
  capability row is added, re-scoped or re-statused — provided the registry keeps
  matching the real parser and no second authority is created.
- Verification: `uv run --frozen python scripts/check_documentation.py` is green on the
  merged tree; on the unit branch alone the five pinned `cli.option.aether.update.*` rows
  are pending `LC-RUNTIME`'s parser surface, so the branch reports exactly those five
  `derived surface is not source-derived` errors and nothing else, recorded verbatim
  (Shared decision 16); focused `tests/test_documentation.py`,
  `tests/test_contract_quality_documents.py`, `tests/test_a1_contracts.py`,
  `tests/test_public_artifacts.py`; `uv run --frozen ruff check` / `ruff format --check`
  on touched paths; `git diff --check`. For Shared decision 17 the unit additionally proves
  by re-grep that no tracked artifact outside the surfaces that LC-RUNTIME owns still
  asserts the retired source mode, an `upstream`-or-`transitional_fork` release-lock
  requirement, or the retired XDG placement — reporting the exact search and its empty
  result — and states that
  `tests/test_a1_contracts.py::test_release_lock_schema_and_plan_agree_on_version_three`
  only passes once `LC-RUNTIME` lands the schema constant and the test's own expected
  version together (integration-bound; neither unit may weaken the test). Evidence record
  lists each reconciled claim with the file and line that carries it, and states explicitly
  that the RC is not a stable 1.0.0 claim.

## LC-BLOCK — release blockers #437 and #438

- Source: contract in-scope 2; deliverable D7; AC-10 (focused regressions); issues #437,
  #438.
- Outcome: both canonical gates are green on the objective base. #437: the tracked
  `patches/hermes/HLP-425-review-flow-continuity.patch` appears in the literal
  `.github/workflows/policy.yml` non-`specs/` manifest, and the Telegram Monitor D15R
  laboratory fixture request is accepted by the shipped writer because it names a
  distinct reviewer. #438: the exact-Hermes Monitor tests are order-independent and stop
  reading ambient live profile configuration, so a disposable suite cannot be influenced
  by whatever native module a previous test imported or by the operator's active profile.
  Excludes the HLP-425 fork behavior itself, runtime lifecycle work, release tooling and
  any weakening of the review rule or manifest check.
- Inputs: base `410c172`; issue descriptions and reproduction steps in #437/#438;
  `patches/hermes/HLP-425-review-flow-continuity.patch`; the exact-Hermes bootstrap. No
  prerequisite unit.
- Boundaries: writable `.github/workflows/policy.yml` (only the manifest entry required by
  #437 plus entries for files this unit adds), the specific Monitor lab fixture and
  exact-runtime test modules implicated by #437/#438, an optional new focused test module
  owned by this unit, and `specs/001-aether-v1-productization/evidence/LC-BLOCK.md`.
  Preserve review/independence rules, the manifest's other entries, `src/aether_agents/**`
  unless the diagnosed defect is genuinely there, and every other unit's files.
- Judgement: fixture shape, whether the isolation fix belongs in a test helper, fixture or
  module-scoped cleanup, and the smallest change that removes the ambient-state read
  without weakening a real gate.
- Verification: reproduce both failures on the unchanged unit base and record RED; then
  GREEN with the canonical exact-Hermes bootstrap for the affected Monitor modules and for
  the manifest check (`git ls-files` comparison logic run locally); run the focused Monitor
  suites in the order that previously failed and a randomized/alphabetical order; then
  `uv run --frozen python scripts/run_tests.py` for the touched nodes plus `ruff check`,
  `ruff format --check`, `git diff --check`. No skip is added or removed to obtain green.
- Dependencies: decomposition root only.

## LC-FORK — maintained-fork candidate for the RC

- Source: contract in-scope 8; D6; AC-01 (fork half), AC-02 (fork half), shared decision 4.
- Outcome: one clean, reviewable `aether-main` candidate in
  `DarkArty07/aether-hermes` that carries every accepted active HLP behavior as source
  (never as replayed patches), with fork documentation/tests and the Hermes distribution
  identity reconciled, a nested-worktree branch ready for a normal PR, and fork-side
  evidence naming the exact candidate revision and the coverage of every active HLP entry.
  Excludes Aether-side files, push/PR/merge (Supervisor publishes), history rewrite, and
  any change to the live runtime or the installed editable state.
- Inputs: provisioned fork checkout resolved by remote URL
  `https://github.com/DarkArty07/aether-hermes` at clean
  `54eeb56dabefc98821d696656ed58c55dd777346` (three commits ahead of remote
  `bb5e9a422f3135371557e75bcd1db01c5f8fc3ba`); `HERMES_LOCAL_PATCHES.md` active entries
  read as evidence; fork `AETHER_FORK.md`, `AGENTS.md`, `CONTRIBUTING.md`, `pyproject.toml`,
  `uv.lock` and affected source/tests. No prerequisite unit.
- Boundaries: writable fork paths only, inside a nested isolated worktree created from that
  checkout: the reconciliation of the three candidate commits into one reviewable branch,
  `AETHER_FORK.md`, fork docs/tests required by the affected surfaces, and packaging
  metadata only if an independently required correction is justified. Never mutate the
  checkout whose branch is `aether-main`; never edit the live runtime; never apply a
  `.patch` file. Record the unit evidence in
  `specs/001-aether-v1-productization/evidence/LC-FORK.md` on the Aether branch.
- Judgement: commit/branch organization for the PR, whether a packaging correction is
  genuinely required (with justification and rollback), and which fork test modules prove
  the affected behaviors.
- Verification: run the fork's own required suite for the affected surfaces plus
  `ruff`/format/`git diff --check`; where runtime assets or JS/TS surfaces changed, run the
  npm/frontend build and tests; prove the candidate contains each accepted active HLP
  behavior by source inspection at the exact revision with the file/line evidence; prove
  the tree is clean and the branch is a normal fast-forwardable candidate without history
  rewrite; report the exact candidate revision, tree digest inputs and any residual risk.
- Dependencies: decomposition root only.

## LC-RUNTIME — maintained-fork lock, local candidate route and state-preserving lifecycle

- Source: contract in-scope 3–6, 9 and 10 (disposable lane); D2, D3, D4, D5; AC-01–AC-08;
  shared decisions 4–9, 12.
- Outcome: source identity, preparation, activation, recovery and rollback are driven by
  one validated maintained-fork release lock instead of the obsolete fixed public baseline
  or an editable/live-tree coupling. Concretely: schema v4 + packaged resource + baseline
  reconciliation that refuse the retired mode; `aether update --local` with a
  non-mutating preview and clean-source refusals per Shared decision 5; an authoritative
  active-release record with versioned staging, `runtime/current`, launcher, Desktop and
  Aether-owned systemd projections that follow the selector; transition recovery; a
  state-preserving rollback that never rolls user state backward; `aether doctor`
  fail-closed mismatch diagnostics; the HLP ledger and reconciliation evidence generation
  reconciled to the maintained fork with retirement claims kept evidence-bound; and
  disposable-home tests covering update, interruption (before/after candidate publication
  and selector/service projection), mismatch, fault injection, activation and rollback.
  The two uncommitted launcher-separation changes are integrated (or equivalently
  replaced) inside this unit's worktree without touching the primary checkout. Excludes
  the bounded real activation lane, remote effects, publication, and other units' files.
- Inputs: base `410c172`; Shared decisions 4–9; the current lifecycle module's existing
  `setup`/`update`/`rollback` semantics and its packaged schemas/profiles as the starting
  point; the observed live layout as evidence; the primary checkout's uncommitted launcher
  diff read-only via `git diff`. No prerequisite unit.
- Boundaries: writable `src/aether_agents/lifecycle.py`, `cli.py`, `hermes_baseline.py`,
  `paths.py`, `hermes_editable.py` (only as far as removing an obsolete coupling the RC
  must not use), `src/aether_agents/resources/hermes-baseline.json` and
  `src/aether_agents/resources/schemas/**`, `scripts/validate_hermes_patch_reconciliation.py`,
  `scripts/check_hermes_baseline_drift.py`, `scripts/aether_tui.py`,
  `HERMES_LOCAL_PATCHES.md`, `specs/001-aether-v1-productization/contracts/release-lock.schema.json`,
  `specs/001-aether-v1-productization/contracts/hermes-patch-reconciliation.schema.json`,
  `specs/001-aether-v1-productization/evidence/hermes-patch-*` and `entries/**`,
  the lifecycle/monitor-adjacent tests this unit owns
  (`tests/test_hermes_baseline.py`, `tests/test_hermes_editable.py`,
  `tests/test_hermes_patch_reconciliation.py`, `tests/test_aether_tui_launcher.py`,
  `tests/test_observation_lifecycle.py`, `tests/test_a1_contracts.py`,
  `tests/test_observation_packaging.py`, plus new focused modules), and
  `specs/001-aether-v1-productization/evidence/LC-RUNTIME.md`. Preserve `VERSION`,
  `CHANGELOG.md`, `.github/**`, `docs/**`, `DESIGN.md`, `AGENTS.md`, the unit records of
  other units, and the canonical contract.
- Judgement: internal staging names, private metadata representation, helper
  decomposition, migration/reading of historical records, and the exact test module
  organization — provided atomicity, exact identity, preservation, the pinned CLI surface
  and public behavior stay satisfied. Return any need to change a shared interface or the
  pinned identifiers instead of diverging.
- Verification: focused nodes first (lock schema/validation, update preview/refusals,
  activation/selector coherence, transition recovery, rollback preservation, doctor
  mismatches, patch reconciliation, launcher separation); disposable homes only, with
  never a live board, live runtime or ambient profile; fault injection at interruption
  before and after candidate publication and at the selector/service projection, each with
  restart recovery; hash-level proof that mutable state is byte-identical across
  update/rollback; `scripts/validate_hermes_patch_reconciliation.py` in check mode with
  generated evidence current at the pinned fork candidate revision; then the canonical
  commands of Shared decision 11 for the touched surfaces; `uv build` and a clean-install
  smoke of the produced wheel in a fresh disposable root. Evidence record maps each AC-01
  to AC-08 obligation to the exact command and observed result.
- Dependencies: decomposition root only.

## LC-RELTOOL — release bundle, workflow and closeout tooling

- Source: contract in-scope 7 and 11; D8; AC-05, AC-11, AC-12 (tooling half); testing
  standard "build release artifacts once".
- Outcome: reproducible tooling (repository script and/or `.github/workflows/release.yml`
  reconciliation) that, given exact clean Aether and fork revisions, produces one release
  bundle — `aether-agents` wheel and sdist for `1.0.0rc1`, the maintained-fork runtime
  source closure, the release lock, provenance/manifest and `SHA256SUMS` — inspects
  wheel/sdist/archive members, scans public bytes for private paths/secrets, clean-installs
  the exact wheel plus locked runtime closure into fresh disposable roots with the normal
  resolver, and exercises `aether --version`, update preview/refusals,
  setup/update/doctor/status/rollback, Hermes import/version/plugin discovery and TUI
  `--check`, emitting package-member and clean-install reports plus the declared identity
  set. It also reconciles `VERSION` to `1.0.0rc1` and adds the changelog entry that
  describes the RC scope honestly. Excludes publication, tagging, activation, and any
  unit's source files.
- Inputs: base `410c172`; Shared decisions 2, 5, 6, 11; existing `.github/workflows/release.yml`
  (tag validation and prerelease reconciliation already exist; artifacts are not attached
  yet) and `scripts/**` conventions; `CONTRIBUTING.md` build standard. No prerequisite
  unit.
- Boundaries: writable `VERSION`, `CHANGELOG.md`, `.github/workflows/release.yml`,
  `pyproject.toml` only if a build-metadata correction is genuinely required, new
  `scripts/**` release tooling plus its tests, and
  `specs/001-aether-v1-productization/evidence/LC-RELTOOL.md`. Preserve `src/**`,
  `docs/**`, `DESIGN.md`, `AGENTS.md`, `HERMES_LOCAL_PATCHES.md`, other units' test
  modules, and the canonical contract. Record the exact bundle file names and identity
  list in the handoff so the integration card attaches and verifies the same bytes.
- Judgement: tool flags, internal helper layout, whether the workflow builds or verifies
  the artifacts, and the report format — provided the bundle is built once from exact
  clean revision inputs, the attached bytes are the qualified bytes, and every attached
  artifact is download-verifiable by SHA-256 and a fresh artifact-installed CLI handshake.
- Verification: run the tool against this unit's own clean commit to produce a real
  candidate bundle; prove member inspection, private-path/secret scan, clean-install in a
  fresh disposable root with the normal resolver and the CLI handshake; prove
  refusal/negative behavior for dirty trees, wrong revision and tampered digest; run
  `uv build`, `uv run --frozen python scripts/run_tests.py` for the new tests, `ruff
  check`/`ruff format --check`, `mypy src/aether_agents` and the `git diff --check`
  standard; verify the workflow YAML parses and its validation logic matches the tag
  contract. Evidence record lists the produced artifact names, byte sizes and SHA-256
  values, and states that this is a tooling qualification, not a publication.

## LC-INT — integration, gates, dual-repository merge and prerelease publication

- Source: contract in-scope 12; D7, D8, D10; AC-10 (integrated), AC-11, AC-12; shared
  decisions 2, 3, 14. Owner authority for pushes, PRs, checks, green merges, the annotated
  RC tag and non-destructive prerelease creation/edit plus artifact upload.
- Outcome: every reviewed unit is integrated in dependency order; the recorded manifest
  lines are applied as bounded integration repair; HLP reconciliation evidence is
  regenerated at the accepted fork revision with the accepted generator; the integrated
  gates of Shared decision 11 pass on the merged candidate; the fork candidate and the
  Aether candidate each travel through normal push → PR → required checks → green merge
  without bypass or history rewrite; annotated tag `v1.0.0-rc.1` points exactly to
  accepted `origin/main` with `VERSION` `1.0.0rc1`; a GitHub prerelease carries the exact
  qualified bundle; and every attached artifact is downloaded, re-hashed and handshaken
  after download. Excludes closing #261, calling 1.0 stable, PyPI/OIDC/settings mutation,
  force pushes, and the real local activation lane.
- Inputs: reviewed unit branches and their handoffs; the pinned base; accepted bundle
  tooling; existing GitHub credentials and required checks. Depends on the root card and
  on LC-DOCS, LC-BLOCK, LC-FORK, LC-RUNTIME and LC-RELTOOL.
- Boundaries: integration-owned branch/worktree, the mechanical application of recorded
  `policy.yml` manifest lines and regeneration of reconciliation evidence at the accepted
  revision, release-identity constants, and
  `specs/001-aether-v1-productization/evidence/LC-INT.md`. May merge the latest
  `origin/main` normally. Semantic conflicts, behavioral changes, acceptance changes and
  any other unit's source semantics return to the owning unit as rework instead of being
  resolved as integration freedom. Preserve every unmerged, concurrent and unrelated
  branch, worktree, stash, board and release.
- Judgement: branch/PR granularity, conflict resolution that is mechanically implied by
  accepted work, ordering of merges, and bounded diagnosis/correction of objective-caused
  CI failures — with behavioral corrections returned to the owning unit.
- Verification: full integrated gates (all canonical commands plus `uv build`, documentation
  and policy checks, the patch-reconciliation check mode, and the focused lifecycle,
  rollback, Monitor, patch and public-artifact nodes); `git ls-files` manifest equality;
  PR check state green on the required lanes; merged commit identity and ancestry recorded;
  annotated tag object identity and its dereferenced commit equal to accepted
  `origin/main`; release flags (`prerelease=true`, not draft); every attached artifact
  re-hashed after download plus one fresh artifact-installed CLI handshake. Evidence
  record includes run URLs/ids, commit ids, tag object id, artifact names with local and
  downloaded SHA-256 values, and the exact qualified release identity handed to LC-CLOSE.
- Completion: hand off the exact published identity (release id/URL, tag object and
  commit, artifact names and hashes, the installed release id to activate) to LC-CLOSE;
  aggregate compatibility conclusions stay with LC-CLOSE's final report.

## LC-CLOSE — real activation lane, issue truth, residue and final evidence

- Source: contract in-scope 10 (real lane) and 12; D9, D10, D11, D12; AC-06–AC-09, AC-13,
  AC-14; shared decisions 3, 8, 9, 12. Terminal card, same flow affinity.
- Outcome: the published RC bytes are activated locally on this machine and proven: one
  authoritative active record plus matching `runtime/current`, launcher, Desktop and
  Aether-owned systemd unit projections; `aether version/doctor/status` ready for the RC;
  TUI launch in the verified Aether Project; gateway/dispatcher ready; intended plugins and
  tools exposed; Projects binding exact; Graphify probe/status/query working; no legacy
  project-local runtime path loaded; one real three-role pipeline E2E passing on the new
  runtime; then a rollback rehearsal that restores the prior release, proves every mutable
  state identity and post-cutoff data preserved, and a forward activation of the exact same
  RC re-verified; #437 and #438 closed with exact evidence; #261 updated with RC outcomes
  and explicitly outstanding stable/PyPI/WSL2 gates, left open; objective-owned merged
  branches/worktrees and bounded test processes cleaned only after durable evidence, with
  the two pre-existing dirty launcher paths, unknown worktrees/stashes, old runtime and
  backups preserved and reported; and one final report carrying the three release
  conclusions separately from their supporting evidence. Excludes stable/PyPI/container
  publication, deployment to another machine, user-state rollback, and any credential,
  provider, model or router change.
- Inputs: LC-INT's published identity and downloaded artifact hashes; the accepted runtime
  lifecycle and tooling; the recorded pre-state; existing provisioned providers and
  profiles for the E2E lane. Depends on the root card, every implementation unit and
  LC-INT.
- Boundaries: live local activation/rollback of the RC, the Aether-owned service and
  projections, issue comments/closure with evidence, objective-owned residue cleanup, and
  `specs/001-aether-v1-productization/evidence/LC-CLOSE.md`. The unrelated
  `hermes-gateway-hestia` service, the generic `~/.local/bin/hermes`, provider/model/router
  configuration, Telegram Monitor state and every unknown/preexisting artifact are out of
  bounds. When a restart interrupts this session, resume from the durable evidence and
  continue the remaining checks rather than redoing settled ones.
- Judgement: ordering of the interrupting steps, the resumable post-restart checklist,
  how the E2E lane is scoped to existing provisioned providers without live-board misuse,
  and which residue is genuinely objective-owned.
- Verification: pre-state identities recorded before any mutation; active record,
  `runtime/current`, launcher, Desktop entry and service projection compared for exact
  agreement; `aether doctor --json` `result=ready`; TUI `--check` plus a real launch in the
  verified Project; gateway/dispatcher liveness with a post-activation PID; plugin/tool
  discovery; Project binding equality; Graphify probe/status/query; one real three-role
  E2E; rollback with before/after state identity comparison and post-cutoff data presence;
  forward activation re-verified; issue states read back after mutation; residue inventory
  with preserved items separated from cleaned items. Report raw commands/results, exact
  limits of what was verified, and remaining material risk.
- Completion: terminal objective closeout with the final evidence report; no step is
  omitted without a concrete non-applicability reason.

## Preservation and residue

- Preserve the canonical Objective Contract artifacts byte-for-byte; never stage, edit,
  reformat or exact-copy them.
- Preserve the owner's primary checkout including its two uncommitted launcher changes,
  the currently installed runtime release and its manifests, the migration backup trees,
  `home/`, all mutable state under the Aether state root, and every unrelated
  worktree/branch/stash/board/profile/service.
- Preserve the pre-existing `patches/hermes/**` evidence and the HLP ledger as
  reconstruction records even where the RC no longer deploys them.
- Only objective-owned, durably merged residue is cleaned, and only after the publication
  and activation evidence exists.
