# LC-DOCS — canonical design, docs and capability reconciliation for the `1.0.0rc1` RC

**Unit:** LC-DOCS (Implementer) · card `t_c0ff1794`
**Authority:** Objective Contract `oc_3397f9f05d780f8e@v1` (SHA-256
`4d4c7650bf8ea93fc7cffe3d87f7f974e172d66cefcf6a74a2d83051568a4879`), base commit
`410c172ae69ffa87f6e32960ae4aef3b8d6598f0`, plus the Supervisor breakdown
`specs/001-aether-v1-productization/tasks.md` at its current revision
`5ede8524df57ecc5b1c1a9b5bf2d056cf19d2a55` (supersedes `61124bc1` for reading shared decisions; shared decision 16
owns the integration-bound gates recorded in §5.1 and §6.1). Supervisor independently re-measured the five-error
attribution, the bidirectional registry/parser mapping (`scripts/check_documentation.py:419` and `:422`) and the
400-versus-402 manifest gap before closing the request.
**Scope delivered:** in-scope 1 (owning-artifact reconciliation), 7 and 11 as they touch
documentation; deliverable D1; AC-15.
**Unit-level only:** this record reports LC-DOCS's own compatibility evidence. It is not an
aggregate release conclusion, not a publication and not an acceptance verdict.

## 1. Explicit non-claims

The `1.0.0rc1` milestone is **not** a stable `1.0.0` claim, **not** a PyPI or other
package-index publication, and **not** a WSL2 qualification result. This unit produced
documentation changes only: no release candidate was published, tagged, activated, pushed
or uploaded by LC-DOCS, and no issue was mutated. `release_impact`, `release_action` and
`release_channel` are recorded here only as the contract's stated values for the objective
(`major` / `publish` / `prerelease`); their aggregation belongs to the terminal closeout.

## 2. Starting point actually verified

| Item | Observed |
| --- | --- |
| Workspace / branch | assigned worktree clean at `410c172`, branch `aether-agents-2/t_c0ff1794-lc-docs-...` |
| Prerequisites | none (root-gated unit); no parent unit's commit is consumed |
| Base parser | `src/aether_agents/cli.py:95-105` has no `--local`, `--aether-checkout`, `--aether-commit`, `--fork-checkout`, `--fork-commit` |
| Base release-lock schema | `specs/001-aether-v1-productization/contracts/release-lock.schema.json` still `schema_version` const `3`; the contract pins `4` for the RC, and that schema is LC-RUNTIME's surface |
| Base manifest gate | `tests/test_public_artifacts.py::test_canonical_base_manifest_matches_tracked_non_specs_files` already fails at base (see §5.3) |

### 2.1 Pinned identifiers — real inspection (read-only)

| Pinned fact | Evidence inspected | Result |
| --- | --- | --- |
| Executable source is `DarkArty07/aether-hermes` | provisioned checkout resolved by its Git remote URL | remote `https://github.com/DarkArty07/aether-hermes.git`, current branch `aether-main`, `HEAD` `54eeb56dabefc98821d696656ed58c55dd777346` — matches the breakdown's candidate |
| Hermes keeps `hermes-agent` `0.20.1` | fork `pyproject.toml` (`version = "0.20.1"`) and the installed runtime's `hermes_agent-0.20.1.dist-info` | confirmed; no rename is documented anywhere |
| Immutable releases/components under the data root; mutable state under the state root | `ls`/`readlink` of the Aether data and state roots | data root holds `runtime/` (versioned `releases/<id>` plus a `current` selector) and `components/`; state root holds the mutable Hermes home, `projects`, `observations`, `knowledge`, `monitor`, `migrations` |
| Base is the fixed public `v2026.8.18` baseline with `.patch`/editable coupling | installed release `manifests/release-origin.txt` | shows an editable `hermes_worktree_patch_sha256` — i.e. the pre-separation state the RC replaces, exactly as documented |

No pinned identifier proved materially wrong, so no delta was returned. Machine paths and
live-state values observed during this inspection are deliberately **not** reproduced here.

## 3. Reconciled claims and where they now live

| # | Reconciled claim | Stated at |
| --- | --- | --- |
| 1 | Executable Hermes source is the maintained fork, bound by release-lock `schema_version` 4 `maintained_fork` (repository, branch, exact commit, source-tree digest, artifact closure, provenance) | `AGENTS.md:15`, `AGENTS.md:97-99`, `ROADMAP.md:8-9`, `README.md:20`, `DESIGN.md:355` (PD-61), `DESIGN.md:359` (PD-65), `DESIGN.md:362` (PD-68), `docs/index.md:7-13`, `docs/product-boundary.md:38-42`, `docs/reference/limitations-and-troubleshooting.md:16` |
| 2 | Not the fixed public `v2026.8.18` baseline and not a `.patch`/editable replay; the retired `transitional_fork` mode is refused | `AGENTS.md:15`, `AGENTS.md:97`, `ROADMAP.md:9`, `ROADMAP.md:91-99`, `README.md:20`, `DESIGN.md:355`, `docs/guides/policy-and-recovery.md:83-85`, `docs/reference/cli.md:81-85`, `specs/001-aether-v1-productization/spec.md:5` and `160-173`, `contracts/cli.md:36-44` |
| 3 | Immutable release code/components under the XDG data root; every mutable Hermes home and product state under the XDG state root; no second move of live state | `DESIGN.md:356` (PD-62 reconciliation note), `specs/001-aether-v1-productization/plan.md:119-152`, `README.md:22`, `docs/capabilities.toml:136` |
| 4 | `aether update` is the sole promotion/activation boundary, with a non-mutating local-candidate preview, explicit interrupting activation, transition recovery and state-preserving rollback | `contracts/cli.md:29`, `contracts/cli.md:36`, `contracts/cli.md:92-130`, `docs/reference/cli.md:56` and `62-93`, `docs/guides/policy-and-recovery.md:58-85` (local route at `64-79`), `docs/getting-started.md:36-44`, `docs/reference/limitations-and-troubleshooting.md:37-42`, `specs/001-aether-v1-productization/plan.md:336-347` |
| 5 | Pinned CLI surface: `aether update --local --aether-checkout PATH --aether-commit SHA --fork-checkout PATH --fork-commit SHA [--dry-run] [--yes] [--json]`, `--local` mutually exclusive with `[VERSION]`, `--prerelease`, `--wheel`, `--hermes-checkout`, `--release-lock` | `contracts/cli.md:107-130`, `docs/reference/cli.md:56` and `62-89` (lock/schema note at `81`), `docs/guides/policy-and-recovery.md:64-79` (lock/schema note at `81`), `docs/getting-started.md:37-40`, `docs/capabilities.toml:106-116` (registry) and the generated `docs/reference/capabilities.md` |
| 6 | Bounded RC scope: package `1.0.0rc1`, annotated tag and GitHub prerelease `v1.0.0-rc.1`, `major`/`publish`/`prerelease`; explicitly not stable, not PyPI, not WSL2 | `README.md:5`, `ROADMAP.md:74-81`, `docs/index.md:7-13`, `docs/reference/limitations-and-troubleshooting.md:17`, `AGENTS.md:17`, `docs/product-boundary.md:36`, `docs/guides/lifecycle.md:32-36`, `specs/001-aether-v1-productization/spec.md:5` |
| 7 | #261 stays open with the stable/PyPI/WSL2 gates outstanding | `README.md:5`, `ROADMAP.md:81`, `docs/index.md:11-12`, `docs/reference/limitations-and-troubleshooting.md:17`, `specs/001-aether-v1-productization/spec.md:5` |
| 8 | Historical wording is preserved, not rewritten: A1 decisions, the six historical indispensable guarantees, the 2026-08-21 and 2026-09-07 amendments | `specs/001-aether-v1-productization/research.md:19` and `31-38` (new RC amendment) and `206`, `227`, `310` (marked historical); `ROADMAP.md:91-99`; `DESIGN.md` decision cells keep their original text plus a dated reconciliation clause |
| 9 | Registry matches the real parser and gains one RC traceability row | `docs/capabilities.toml:106` (`cli.update` re-scoped), `docs/capabilities.toml:128` (new `lifecycle.immutable-release-and-update-boundary`), regenerated `docs/reference/capabilities.md` |

Normative-owner discipline: `DESIGN.md` keeps its decision wording and gains dated
reconciliation clauses (PD-61/62/65/68); the A1 spec, plan and research keep their history
and mark superseded statements as historical; no new product principle, role, interface or
authority was invented, and no canonical contract file was touched.

## 4. Files changed

`AGENTS.md`, `DESIGN.md`, `README.md`, `ROADMAP.md`, `docs/capabilities.toml`,
`docs/getting-started.md`, `docs/guides/lifecycle.md`, `docs/guides/policy-and-recovery.md`,
`docs/index.md`, `docs/product-boundary.md`, `docs/reference/capabilities.md` (generated),
`docs/reference/cli.md`, `docs/reference/limitations-and-troubleshooting.md`,
`specs/001-aether-v1-productization/contracts/cli.md`,
`specs/001-aether-v1-productization/plan.md`,
`specs/001-aether-v1-productization/research.md`,
`specs/001-aether-v1-productization/spec.md`, and this record.

No tracked file was added, renamed or removed outside `specs/`, so no
`.github/workflows/policy.yml` manifest line is required for LC-DOCS itself (two
pre-existing gaps are recorded in §5.3). `VERSION`, `CHANGELOG.md`, `src/**`, `scripts/**`,
`tests/**`, `.github/**`, `HERMES_LOCAL_PATCHES.md`, the release-lock schema, other unit
records, `home/` and the owner's primary checkout were not touched.

The review-8 delta (§7) additionally changed `ROADMAP.md`,
`specs/r4-hermes-boundary/{spec.md,research.md}`, `specs/r9-state-and-recovery/spec.md`,
`specs/r11-evidence-and-observability/spec.md` and
`specs/r13-synthesis-and-release/{spec.md,plan.md,research.md}` within the extended surface. It
still adds, renames and removes no tracked file, so it also requires no manifest line.

## 5. Verification actually run

### 5.1 Documentation gate — raw result

```text
$ uv run --frozen python scripts/check_documentation.py
documentation validation failed:
- derived surface is not source-derived: cli.option.aether.update.--aether-checkout
- derived surface is not source-derived: cli.option.aether.update.--aether-commit
- derived surface is not source-derived: cli.option.aether.update.--fork-checkout
- derived surface is not source-derived: cli.option.aether.update.--fork-commit
- derived surface is not source-derived: cli.option.aether.update.--local
EXIT=1
```

Exactly five errors and no others: they are precisely the five surfaces Shared decision 5
assigns to `docs/capabilities.toml` while `src/aether_agents/cli.py` (LC-RUNTIME
`t_359beef2`, still `ready`) owns the parser half. `scripts/check_documentation.py` enforces
the surface/parser mapping bidirectionally, so this unit's branch cannot be green alone
whichever order the two units land in; the end-state-correct choice is to declare the pinned
surfaces now. No `uncovered derived surface` and no `generated reference is stale` error
appears, i.e. nothing else in the registry is inconsistent or stale.

**This unit does not claim `check_documentation.py` green in isolation.** The accepted
disposition of the controller request below is candidate (a): a bounded cross-unit
verification dependency, not a waiver. LC-INT must merge LC-RUNTIME before LC-DOCS
verification, run the plain documentation check and require it green, and use `--write` only
if the deterministic generated bytes genuinely differ — inspecting that mechanical delta and
never using it to hide a semantic mismatch. AC-15 itself is unchanged.

Interface-consistency proof (disposable, not committed): in a copy of this tree under the
system temporary directory I added only the five pinned `add_argument` calls to that copy's
`_build_parser` (simulating — not claiming — LC-RUNTIME's deliverable) and ran the same
script with `--write`:

```text
documentation validation passed
WRITE_EXIT=0
grep -c "cli.option.aether.update.--local" docs/reference/capabilities.md → 1
```

`docs/reference/capabilities.md` in this unit is that generator's output for this registry,
copied back byte-for-byte from the disposable run, so the merged tree needs a confirming
re-run rather than a `--write`. The simulation is labelled as such and is not evidence about
LC-RUNTIME's code.

### 5.2 Focused tests — raw result

```text
$ uv run --frozen python scripts/run_tests.py tests/test_documentation.py \
    tests/test_contract_quality_documents.py tests/test_a1_contracts.py tests/test_public_artifacts.py
1 failed, 65 passed
FAILED tests/test_public_artifacts.py::test_canonical_base_manifest_matches_tracked_non_specs_files
```

The single failure is pre-existing and unrelated to this unit (§5.3). The review-8 delta (§7.3) adds
one further attributable failure, `test_release_lock_schema_and_plan_agree_on_version_three`, which is
integration-bound to LC-RUNTIME and analysed in §7.4; this section's §5.1 honesty rules are unchanged.
`tests/test_documentation.py`, `tests/test_contract_quality_documents.py` and
`tests/test_a1_contracts.py` are green, including the registry-content assertions
(`test_canonical_skill_capabilities_are_statused_and_traceable`,
`test_stewardship_capabilities_are_distinct_and_honest`,
`test_monitor_capability_is_registered_statused_and_traceable`) and the README assertions
(`test_readme_is_a_current_beta_portal_and_package_metadata_is_stable`).

### 5.3 Pre-existing manifest failure (not caused by LC-DOCS)

Measured with the test's own heredoc extraction on this worktree: manifest 400 entries,
`git ls-files` minus `specs/` 402 entries. Missing lines:

```text
.aether/objective-contracts/oc_3397f9f05d780f8e/v1.md
patches/hermes/HLP-425-review-flow-continuity.patch
```

Both files are already tracked at base `410c172` (`git ls-tree -r 410c172`), and the manifest
at `410c172` contains neither (`git show 410c172:.github/workflows/policy.yml | grep -c
oc_3397f9f05d780f8e` → `0`), so the gate was already red before this unit. The second line is
issue #437's stated defect (LC-BLOCK); the first is the same literal-manifest requirement for
the contract file the base commit added. LC-DOCS adds no tracked file, so it recorded the
exact lines via the controller collaboration path instead of editing the workflow.

### 5.4 Style and hygiene — raw results

```text
$ uv run --frozen ruff check <touched paths>
warning: No Python files found under the given path(s)
All checks passed!            (exit 0)
$ uv run --frozen ruff format --check <touched paths>
25 files already formatted    (exit 0)
$ git diff --check
(exit 0)
```

## 6. Cross-unit items and residual risk

1. **Registry/parser coupling — resolved as a bounded cross-unit verification dependency.**
   Controller collaboration request `#4` was answered by the design steward: keep the
   end-state-correct registry and generated reference, record the five exact parser-derived
   errors and the disposable simulated-parser confirmation, and never claim the check green in
   isolation. LC-INT merges LC-RUNTIME before LC-DOCS verification and requires the plain
   check green; `--write` is only for a genuine deterministic byte difference. Manifest
   finding acknowledged and routed separately.
2. **Manifest lines — routed to LC-BLOCK by Supervisor.** `.aether/objective-contracts/oc_3397f9f05d780f8e/v1.md`
   and `patches/hermes/HLP-425-review-flow-continuity.patch`, each as a literal manifest line
   in `.github/workflows/policy.yml`, are required for
   `test_public_artifacts.py::test_canonical_base_manifest_matches_tracked_non_specs_files`
   to pass. Supervisor extended LC-BLOCK's boundary to correct **both** base-missing lines (the
   contract-file line attributed as a directly evidenced same-class blocker under contract
   in-scope 2, not as part of #437), because the test compares the whole list. LC-DOCS does not
   own that workflow and changed nothing there.
3. **Release-lock schema version has a second consumer — resolved into this unit's delta.** `tests/test_a1_contracts.py::test_release_lock_schema_and_plan_agree_on_version_three`
   asserts `release-lock.schema.json` const `3` **and** the string `release-lock schema is integer
   `3`` in `specs/r13-synthesis-and-release/plan.md` (then in no unit's declared surface). Supervisor's
   review extended LC-DOCS's surface to that plan line, and §7.1 item 3 reconciles it to the accepted
   schema `4`. Moving the schema to `4` therefore needs LC-RUNTIME's schema constant and matching test
   update, which the review recorded as an integration-bound condition; the test is red on this branch
   for exactly that reason and is not weakened here (§7.4).
4. **`CHANGELOG.md` non-applicability.** The card's outcome sentence mentions the changelog,
   but the card's explicit do-not-touch list and the breakdown's file-disjoint assignment
   place `CHANGELOG.md` and `VERSION` with LC-RELTOOL. The design steward confirmed this
   reading mid-run. LC-DOCS therefore recorded the RC scope in README/ROADMAP/docs/spec and
   did not edit or gate on the changelog; the RC changelog entry is LC-RELTOOL's.
5. **Residual risk.** The five pinned registry surfaces are not exercised by this branch's
   parser until LC-RUNTIME lands; the documentation describes a pinned interface that the
   integration must confirm. Everything else in this unit is verifiable from the committed
   diff, the focused tests and the documentation gate.

## 7. Review-8 delta — owning-stage reconciliation debt (Shared decision 17)

Supervisor's review run 8 verified the attempt-1 delivery sound but returned it: the card outcome
"without creating a competing authority" was not met while live normative statements in the owning
stage artifacts still contradicted the contract's decisions. This section records that bounded
correction. The §5.1 honesty rules are unchanged, and the correction invented no principle, role,
interface or authority. R10's supply-chain gates and R12's model-identifier items from A1 spec §10
were deliberately **not** absorbed, as the review directed.

### 7.1 Reconciled statements (post-edit line numbers)

| # | Superseded statement | Where it lived | Reconciled at |
| --- | --- | --- | --- |
| 1 | `transitional_fork` as a permitted/initial release mode or as the declared lock enum | `specs/r4-hermes-boundary/spec.md:42-43,156`; `specs/r4-hermes-boundary/research.md:333`; `specs/r11-evidence-and-observability/spec.md:125`; `specs/r13-synthesis-and-release/spec.md:122,139`; `specs/r13-synthesis-and-release/plan.md:9-10,20,22`; `specs/r13-synthesis-and-release/research.md:1190,1211` | `r4/spec.md:42` (FR-403a), `:43` (FR-403b: `upstream` or `maintained_fork`), `:150-157` (dated §9 note), `:164` (FR-425), `:204` (SC-407); `r4/research.md:335` (dated superseding note); `r11/spec.md:125` (FR-1138); `r13/spec.md:11,19-20` (header), `:124` (component 2), `:139` (dated §4 note), `:143` (FR-1337), `:222-227` (dated note on the completed checklist); `r13/plan.md:9-13` (header), `:22`, `:24`, `:102-111` (§2.5), `:168-176` (Phase 2), `:178` (Phase 3), `:255` (§6 risk), `:274` (§7 item 3); `r13/research.md:1194` (dated superseding note) |
| 2 | `profiles/` and `projects/` placed under the data root | `specs/r9-state-and-recovery/spec.md:44,49`; `specs/r13-synthesis-and-release/plan.md:62,68-69` | `r9/spec.md:44-45` (tree split) and `:50` (dated reconciliation clause); `r13/plan.md:64-73` (tree split) and `:87` |
| 3 | `release-lock schema is integer `3`` in the r13 plan (the coupling assertion) | `specs/r13-synthesis-and-release/plan.md:35` | `r13/plan.md:37` states integer `4` (with the historical `3` marked as such); `:43` states the schema-4 `upstream`/`maintained_fork` modes and the refused `transitional_fork` mode |
| 4 | Research decision records and one completed checklist | `specs/r4-hermes-boundary/research.md:321-337`; `specs/r13-synthesis-and-release/research.md:1170-1230`; `specs/r13-synthesis-and-release/spec.md:210-216` | dated superseding notes added at `r4/research.md:335`, `r13/research.md:1194` and `r13/spec.md:222-227`; the original wording was **not** rewritten, matching the discipline already applied to the A1 artifacts in §3 |
| 5 | `ROADMAP.md` routing readers into the unreconciled r13 artifacts | `ROADMAP.md:6,122` (plus `:173`'s stale "transitional-patch" descriptor) | `ROADMAP.md:6` (A1-reconciled pointer), `:122` (r13 plan named as A1-reconciled, RC objective bound to the A1 plan), `:173` |

### 7.2 Verification greps — exact searches and results

```text
$ git grep -nF '`upstream` or `transitional_fork`'          # retired lock enum
(no output)                                                  # EMPTY

$ git grep -nE '(MUST declare|begins in|enters build work in|initial candidate uses|Initial release mode|release mode is)[^.]*transitional_fork'
specs/r4-hermes-boundary/research.md:333   # retained historical decision, immediately followed by the dated superseding note at :335
```

The retired mode is therefore asserted nowhere as current policy. A whole-tree census of the token
`transitional` (86 tracked hits) separates the survivors: explicit negations ("the retired … mode is
refused"), the capability-registry status value `transitional` (a different vocabulary owned by
`docs/authority.md` and required by `scripts/check_documentation.py:30`), dated historical records
whose sections carry superseding notes, and LC-RUNTIME's own surfaces
(`specs/001-aether-v1-productization/contracts/release-lock.schema.json:47,92`,
`src/aether_agents/resources/hermes-baseline.json:68`, `tests/**`). Three out-of-surface residues
remain and are reported, not edited, in §7.5.

```text
$ git grep -nE '(share/aether|XDG_DATA_HOME)[^"`)]*(profiles|projects)'   # retired XDG placement
specs/002-aether-contract-observation/evidence/implementation-validation.md:149   # out-of-surface historical record, §7.5
```

No reconciled artifact places profiles or projects under the data root any more.

### 7.3 Re-run verification — raw results

```text
$ uv run --frozen python scripts/check_documentation.py
documentation validation failed:
- derived surface is not source-derived: cli.option.aether.update.--aether-checkout
- derived surface is not source-derived: cli.option.aether.update.--aether-commit
- derived surface is not source-derived: cli.option.aether.update.--fork-checkout
- derived surface is not source-derived: cli.option.aether.update.--fork-commit
- derived surface is not source-derived: cli.option.aether.update.--local
EXIT=1        # unchanged from §5.1; integration-bound, not claimed green

$ uv run --frozen python scripts/run_tests.py tests/test_documentation.py \
    tests/test_contract_quality_documents.py tests/test_a1_contracts.py tests/test_public_artifacts.py
2 failed, 64 passed
FAILED tests/test_a1_contracts.py::CanonicalContractConsistencyTests::test_release_lock_schema_and_plan_agree_on_version_three   # this delta, §7.4
FAILED tests/test_public_artifacts.py::test_canonical_base_manifest_matches_tracked_non_specs_files                              # pre-existing at base, §5.3

$ uv run --frozen ruff check <touched paths>      → "No Python files found under the given path(s)" / All checks passed!  exit 0
$ uv run --frozen ruff format --check <touched paths> → 8 files already formatted  exit 0
$ git diff --check                                → exit 0
$ uv run --frozen python scripts/check_public_artifacts.py --root . → public artifact path scan passed: tracked surface + 0 artifact(s)
```

Manifest re-measured with the test's own extraction logic: 400 manifest entries versus 402 tracked
non-`specs/` files, missing exactly
`.aether/objective-contracts/oc_3397f9f05d780f8e/v1.md` and
`patches/hermes/HLP-425-review-flow-continuity.patch` — unchanged from §5.3 and still LC-BLOCK's.

### 7.4 Coupling test — exact attribution and integration condition

```text
        self.assertEqual(schema["properties"]["schema_version"]["const"], 3)          # PASSES
>       self.assertIn("release-lock schema is integer `3`", plan)                     # FAILS
E       AssertionError: 'release-lock schema is integer `3`' not found in ...
tests/test_a1_contracts.py:201
```

`test_release_lock_schema_and_plan_agree_on_version_three` asserts the schema constant **and** that
literal string; its `A1_PLAN_PATH` (`tests/test_a1_contracts.py:22`) is
`specs/r13-synthesis-and-release/plan.md`. LC-RUNTIME owns `release-lock.schema.json` and the test;
this unit owns the plan line. **The test passes only after LC-RUNTIME lands the schema constant `4`
with its matching test update** — integration-bound, the same temporal class as §5.1. Neither unit
weakens the test: LC-DOCS edited neither the test nor the schema, and the plan now states the
accepted schema version rather than the retired one.

### 7.5 Residual findings outside this unit's surface (reported, not edited)

| Path / line | What it still states | Why LC-DOCS did not edit it |
| --- | --- | --- |
| `specs/r8-workspaces-and-integration/spec.md:44,174` | "The transitional fork carries the patch until …" and "which is why A1 begins in transitional-fork mode" | R8 is outside the review's surface extension; needs a Supervisor decision (extend the surface or route it). **Resolved in §8**: run 17 extended the surface for these statements and both are reconciled there |
| `specs/002-aether-contract-observation/evidence/implementation-validation.md:132,135,139-141,152,672,1363` | canonical/local release-lock schema as version 3 | Historical implementation-validation record outside the extension; same class as the manifest lines routed in §6.2 |
| `specs/002-aether-contract-observation/evidence/implementation-validation.md:148-150` | product-owned profile homes under `XDG_DATA_HOME/aether/profiles/...` | Same file; out-of-surface historical record |
| `INCOMPLETE_IMPLEMENTATIONS.md:123`, `specs/followup-aether-bugs/evidence/FBUG-INT.md:125`, `specs/telegram-monitor/evidence/MON-04.md:165,181` | "transitional" used as a historical descriptor of the pre-separation runtime | Trackers/historical evidence outside the declared surface; no normative claim about the RC |
| `CHANGELOG.md:111` | historical changelog entry under the declared `transitional_fork` mode | LC-RELTOOL's exclusive surface (§6.4) |

These are surfaced rather than fixed; resolving them is Supervisor's call (surface extension or a
separate routed correction), exactly as the manifest lines were handled in §6.2.

## 8. Re-review-17 delta — final class-closing corrections

Supervisor's re-review run 17 verified the §7 delta sound and required three remaining live references to
the retired source mode to be reconciled, plus a tree-wide sweep report in which every remaining hit is
classified. This section records that correction. §1's non-claims and §5.1's honesty rules are unchanged:
the RC is not a stable `1.0.0` claim, not a PyPI publication and not WSL2-qualified, and no check is
claimed green where it is integration-bound.

### 8.1 Corrections applied (post-edit line numbers)

| # | Superseded statement | Reconciled at |
| --- | --- | --- |
| 1 (required) | `specs/r8-workspaces-and-integration/spec.md:44` — FR-804c: "The transitional fork carries the patch until the exact ready/review first-spawn matrix passes on an upstream release." | `:44` — the repair is carried as the accepted maintained-fork source (`DarkArty07/aether-hermes`, branch `aether-main`, the release lock's `maintained_fork` source mode, `schema_version` 4), never as a replayed `.patch`, and it retires when the matrix passes on an exactly released upstream artifact. The selected-tag defect and the `#198` closure fact are preserved. |
| 2 (required) | `specs/r8-workspaces-and-integration/spec.md:174` — "…which is why A1 begins in transitional-fork mode." | `:174` — "…which is why A1 carries the repair as maintained-fork source (`DarkArty07/aether-hermes`, branch `aether-main`) instead of relying on that public tag — never as a replayed `.patch`", plus the dated reconciliation clause (2026-09-15, `oc_3397f9f05d780f8e@v1`). |
| 3 (required) | `specs/001-aether-v1-productization/plan.md:644` — §14 gate row "Transitional-fork push/release \| authorize remote publication, only if that source mode is selected \| local residual-patch reconciliation, tests, artifact build". | `:644` — "Maintained-fork push/release \| authorize remote publication of the maintained-fork source and its release bundle, only if that source mode is selected \| local fork-source reconciliation, tests, artifact build"; the dated paragraph at `:655` records the former wording. The owner's authorization requirement itself is unchanged. |
| 4 (additional, same class) | `specs/001-aether-v1-productization/plan.md:659` (pre-edit) — §15 risk row "Transitional fork becomes permanent or drifts into a general Hermes product \| upstream-default source mode, … residual patch ledger, stable-tag bases, … executable retirement criteria". | `:661` — "The maintained fork drifts into a general Hermes product or becomes a permanent architecture destination \| deliberate upstream adoption instead of a default source mode, prohibition on new downstream-only capability, the fork's retirement-bound boundary with recorded per-change retirement conditions, upstream every general fix"; the dated paragraph at `:673` records the superseded wording. |

Item 4 was **not** among the three named in the review. It lies inside this unit's original writable
surface (`plan.md` in whole) and is the same class the review is closing: it was the only further
statement found by the required sweep whose live text still carried retired source-mode policy
("upstream-default source mode", "residual patch ledger") as a mitigation. It is reported here and
flagged in the re-review request rather than changed silently.

`specs/r8-workspaces-and-integration/spec.md` was used only at those two statements, as the extension
allowed; R8's header, tables, other requirements, criteria and sections are untouched.

### 8.2 Sweep — exact commands and complete hit classification

```text
$ git grep -nE 'transitional[ _-]fork'            # the exact sweep the review required (case-sensitive)
62 hits

$ git grep -niE 'transitional[ _-]fork'           # case-insensitive census; adds the capital form only
63 hits

$ git grep -nE 'Transitional[ _-]fork'
specs/001-aether-v1-productization/plan.md:655    # the single extra hit: this unit's own new dated note quoting the former gate name
```

Per-file census of the 63 case-insensitive hits, every one classified:

| Class | Hits | Locations |
| --- | --- | --- |
| A — reconciled negation: the retired mode appears only as refused/retired/superseded, or as quoted history inside this delta's dated notes | 36 | `AGENTS.md:15,97`; `ROADMAP.md:9,72,91`; `docs/capabilities.toml:136`; `docs/getting-started.md:45`; `docs/guides/policy-and-recovery.md:83`; `docs/product-boundary.md:40`; `docs/reference/capabilities.md:694`; `docs/reference/cli.md:83`; `docs/reference/limitations-and-troubleshooting.md:16`; `specs/001-aether-v1-productization/spec.md:5,163,170,388`; `…/plan.md:104,324,384,506,655,673`; `…/research.md:19,34,206,227`; `…/contracts/cli.md:39`; `specs/r4-hermes-boundary/spec.md:42,155`; `specs/r13-synthesis-and-release/spec.md:139,143,214,226`; `specs/r13-synthesis-and-release/plan.md:11,24,43` |
| B — historical decision records carrying a dated superseding note in the same section | 6 | `specs/r4-hermes-boundary/research.md:325,333` (note at `:335`); `specs/r13-synthesis-and-release/research.md:1190,1213` (note at `:1194`, whose "elsewhere in this section" clause covers the `:1213` historical schema sentence) |
| C — frozen records, never edited | 3 | `.aether/objective-contracts/oc_5c2dad1b37b20a80/v1.md:32`; `.aether/objective-contracts/oc_fd2332ffe34aa5f7/v1.md:64`; `CHANGELOG.md:111` (LC-RELTOOL adds the RC entry) |
| D — LC-RUNTIME-owned surfaces | 7 | `specs/001-aether-v1-productization/contracts/release-lock.schema.json:47,92`; `tests/test_a1_contracts.py:102,105,134,135,138` |
| E — test-owned historical comments, outside this unit's surface | 3 | `tests/test_observation_lifecycle.py:521`; `tests/test_observation_qualification.py:122,722` (issue `#234` rationale comments; no RC-normative claim) |
| F — this unit's own evidence record | 7 | `specs/001-aether-v1-productization/evidence/LC-DOCS.md` — §3/§7 quoted commands and superseded-statement references (7 hits when the census was taken, before this section was written; §8 adds its own quoted occurrences of the same kind) |
| G — historical caution, frozen at the review's direction | 1 | `specs/006-tools-memory-stability/spec.md:16` ("stale transitional-fork wording does not authorize copying dirty …") — an explicit caution, not a mode assertion |

36 + 6 + 3 + 7 + 3 + 7 + 1 = 63. Re-running the identical census after this section was written returns
70 hits: 14 inside this record (§8's own quotations, class F) and the same 56 elsewhere, distributed
exactly as classified above (36 + 6 + 3 + 7 + 3 + 1). No remaining hit asserts the retired mode as
current policy.
`specs/r8-workspaces-and-integration/` now contains **zero** `transitional` hits: both former statements
are reconciled (`$ git grep -niE 'transitional' -- specs/r8-workspaces-and-integration/` → no output,
exit 1).

The two class-specific greps re-run with this unit's record excluded:

```text
$ git grep -nF '`upstream` or `transitional_fork`' -- ':!specs/001-aether-v1-productization/evidence/LC-DOCS.md'
(no output)                                                 # EMPTY — no upstream-or-transitional_fork lock requirement remains

$ git grep -nE '(share/aether|XDG_DATA_HOME)[^"`)]*(profiles|projects)' -- ':!specs/001-aether-v1-productization/evidence/LC-DOCS.md'
specs/002-aether-contract-observation/evidence/implementation-validation.md:149   # out-of-surface historical record, ruled "do not edit" (§8.4)
```

### 8.3 Re-run verification — raw results (post-edit)

```text
$ uv run --frozen python scripts/check_documentation.py
documentation validation failed:
- derived surface is not source-derived: cli.option.aether.update.--aether-checkout
- derived surface is not source-derived: cli.option.aether.update.--aether-commit
- derived surface is not source-derived: cli.option.aether.update.--fork-checkout
- derived surface is not source-derived: cli.option.aether.update.--fork-commit
- derived surface is not source-derived: cli.option.aether.update.--local
EXIT=1        # unchanged from §5.1/§7.3; integration-bound per shared decision 16 — not claimed green

$ uv run --frozen python scripts/run_tests.py tests/test_documentation.py \
    tests/test_contract_quality_documents.py tests/test_a1_contracts.py tests/test_public_artifacts.py
2 failed, 64 passed
FAILED tests/test_a1_contracts.py::CanonicalContractConsistencyTests::test_release_lock_schema_and_plan_agree_on_version_three   # §7.4, integration-bound to LC-RUNTIME
FAILED tests/test_public_artifacts.py::test_canonical_base_manifest_matches_tracked_non_specs_files                               # pre-existing at base, §5.3 / LC-BLOCK

$ uv run --frozen ruff check <touched paths>          → "No Python files found under the given path(s)" / All checks passed!  exit 0
$ uv run --frozen ruff format --check <touched paths> → 2 files already formatted  exit 0
$ git diff --check                                    → exit 0
$ uv run --frozen python scripts/check_public_artifacts.py --root . → public artifact path scan passed: tracked surface + 0 artifact(s)
```

Manifest re-measured with the test's own extraction logic: 400 manifest entries versus 402 tracked
non-`specs/` files, missing exactly `.aether/objective-contracts/oc_3397f9f05d780f8e/v1.md` and
`patches/hermes/HLP-425-review-flow-continuity.patch` — identical to §5.3/§7.3 and still LC-BLOCK's.
(Pytest's `assert expected == actual` view prints a shifted "first extra item" because of list
alignment; the measured set difference is exactly those two paths.)

### 8.4 Review rulings consumed (no edits made)

Run 17's rulings on the §7.5 residues were consumed as direction; none of these files was edited in this
delta:

| Residue | Ruling | Disposition |
| --- | --- | --- |
| `.aether/objective-contracts/**` | frozen contracts, never edited | non-applicable, untouched |
| `CHANGELOG.md:111` | historical entry describing a past release; LC-RELTOOL adds the RC entry | non-applicable to this unit (also §6.4) |
| `specs/002-aether-contract-observation/evidence/implementation-validation.md` | point-in-time evidence record, do **not** edit; reported as preserved in the terminal residue report | untouched; its single hit is reproduced in §8.2 |
| `INCOMPLETE_IMPLEMENTATIONS.md`, `specs/followup-aether-bugs/**`, `specs/telegram-monitor/**` | historical descriptors with no normative RC claim | non-applicable, untouched |
| `specs/001-aether-v1-productization/contracts/release-lock.schema.json` | LC-RUNTIME's authoritative change (source mode `maintained_fork`, retired mode refused) | not this unit's; §8.2 class D |
| `specs/r8-workspaces-and-integration/spec.md:44,174` | surface extended for these statements only | **applied in §8.1**; R8 has zero remaining `transitional` hits |

Integration-bound expectations are unchanged: §5.1 (documentation gate green after LC-RUNTIME merges),
§7.4 (coupling test moves with the schema constant) and §5.3 (manifest lines, LC-BLOCK).
