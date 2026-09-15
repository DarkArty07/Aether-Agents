# LC-DOCS — canonical design, docs and capability reconciliation for the `1.0.0rc1` RC

**Unit:** LC-DOCS (Implementer) · card `t_c0ff1794`
**Authority:** Objective Contract `oc_3397f9f05d780f8e@v1` (SHA-256
`4d4c7650bf8ea93fc7cffe3d87f7f974e172d66cefcf6a74a2d83051568a4879`), base commit
`410c172ae69ffa87f6e32960ae4aef3b8d6598f0`, plus the Supervisor breakdown
`61124bc1dea787fbc5408fcc7f7b4f654f342e78:specs/001-aether-v1-productization/tasks.md`.
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

The single failure is pre-existing and unrelated to this unit (§5.3).
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
2. **Manifest lines to apply (LC-BLOCK/LC-INT).** `.aether/objective-contracts/oc_3397f9f05d780f8e/v1.md`
   and `patches/hermes/HLP-425-review-flow-continuity.patch`, each as a literal manifest line
   in `.github/workflows/policy.yml`, are required for
   `test_public_artifacts.py::test_canonical_base_manifest_matches_tracked_non_specs_files`
   to pass. LC-DOCS does not own that workflow.
3. **Release-lock schema version has a second consumer.** `tests/test_a1_contracts.py::test_release_lock_schema_and_plan_agree_on_version_three`
   asserts `release-lock.schema.json` const `3` **and** the string `release-lock schema is
   integer `3`` in `specs/r13-synthesis-and-release/plan.md:35` (a file in no unit's declared
   surface). Moving the schema to 4 therefore requires that test (LC-RUNTIME) and that r13
   plan line to change together.
4. **`CHANGELOG.md` non-applicability.** The card's outcome sentence mentions the changelog,
   but the card's explicit do-not-touch list and the breakdown's file-disjoint assignment
   place `CHANGELOG.md` and `VERSION` with LC-RELTOOL. The design steward confirmed this
   reading mid-run. LC-DOCS therefore recorded the RC scope in README/ROADMAP/docs/spec and
   did not edit or gate on the changelog; the RC changelog entry is LC-RELTOOL's.
5. **Residual risk.** The five pinned registry surfaces are not exercised by this branch's
   parser until LC-RUNTIME lands; the documentation describes a pinned interface that the
   integration must confirm. Everything else in this unit is verifiable from the committed
   diff, the focused tests and the documentation gate.
