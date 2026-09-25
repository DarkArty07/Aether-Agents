# PLAN-CANDIDATE — unit evidence

**Card:** `t_e2c6f3bd` (PLAN-CANDIDATE), Objective Contract
`oc_c29c2b0ed38d5030@v1` (SHA-256
`e8ab6fd7d21eb7b65b4887206bc0b2aaae5c02a60f411b970da2696963651af0`),
Issue `#504`.

**Branch:** `aether-agents-2/t_e2c6f3bd-plan-candidate-ship-the-role-scoped-plan`

**Ancestry (exactly two commits on top of base `2e347ab3`):**

- Commit 1 (reader-capable): adds the role-aware inventory knowledge and keeps
  the exact old nine-skill profile-resource inventory (wheel set = 15 resources,
  no `plan` anywhere in the wheel resource set). Touches
  `.github/workflows/policy.yml` (one line), `scripts/release_bundle.py`,
  `src/aether_agents/lifecycle.py`.
- Commit 2 (the candidate): adds `src/aether_agents/resources/skills/plan/SKILL.md`,
  scopes it to Morfeo only, and uses that reader (wheel set = 16 resources). It
  also carries this evidence record. Touches the remaining three policy-yml
  lines, `src/aether_agents/resources/skills/plan/SKILL.md`,
  `tests/test_observation_lifecycle.py`, `tests/test_observation_packaging.py`
  and this file.

Exact SHAs for both commits are recorded in the kanban handoff metadata
(`ancestry_commit_1`, `ancestry_commit_2`); the branch holds exactly two commits
above the base, and `git log --oneline` on it was used to confirm that count.

This is the frozen predecessor measurement (all on this host, disposable
checkouts; no live state touched):

    rc8 (3d480b25) reader on rc8's own wheel    ACCEPTED digest 603c3538...
    rc8 (3d480b25) reader on commit-1 wheel     ACCEPTED digest 603c3538...
    rc8 (3d480b25) reader on commit-2 wheel     REJECTED IntegrityError:
        "candidate wheel profile resource set mismatch"

The rejection of the commit-2 wheel by the frozen predecessor is the disclosed
expected incompatibility observation. It is not a passing upgrade, and no bridge
release, tag, publication, activation or live profile edit was attempted. Note
`aa8de7ca` (rc6) does not carry the exact-set wheel check at all; the frozen
reader used for this measurement is `3d480b25` (rc8), plus rc7 `93d6d96d` which
carries the same check shape.

## What changed

- `src/aether_agents/resources/skills/plan/SKILL.md` (new): the portable public
  canonical skill `plan`. Frontmatter `name: plan`, `description`
  "Author a project-local Objective Plan for Morfeo." (49 chars, ends in `.`,
  contains `Morfeo`), `version: "0.1.0"`, `author: Morfeo (Aether role), Hermes
  Agent`, `license: MIT`, `platforms: [linux, macos, windows]`,
  `metadata.hermes.tags: [planning, objective, morfeo]`,
  `metadata.hermes.related_skills: []`. Body carries `## When to Use` (single
  planning-only trigger), `## Prerequisites`, `## Procedure`, `## Pitfalls`,
  `## Verification`; states that the skill cannot grant authority, names the
  `project-relative` convention, keeps the plan at one stable
  `.aether/plans/<objective-slug>.md` inside the explicitly resolved project,
  treats anticipated Objective Contracts as a revisable forecast (never a cap),
  and defers deeper method to `objective-contract-design` by reference. No
  generic microtask/TDD/commit/delegate recipe, no private learned text, no
  operator path, no secret, no machine-specific location.
- `src/aether_agents/lifecycle.py`: one coherent role-aware source inventory.
  `_CANONICAL_SKILLS` keeps its meaning of "the common nine" and the per-role
  sets are derived from it (`_CANDIDATE_ROLE_SKILLS`), so the suites that
  iterate the common-set name (tests/test_lifecycle_adoption.py lines 115, 196,
  311, 339; tests/test_lifecycle_projections.py line 943) keep their meaning.
  Both producers (`_materialize_profile_bundle` and `profile_bundle_sha256`)
  derive skills per role from the same inventory. `_skill_sources(role=None)`
  stays callable without a role for the common nine.
- `_wheel_profile_bundle_sha256` now accepts exactly two known inventory shapes
  and rejects any other set (missing, extra, forged, cross-role, mismatched
  names). The historical shape maps all three roles to the common nine; the
  candidate shape maps Morfeo to common-nine + `plan` and Supervisor/Implementer
  to the common nine. All drift, ownership, digest and permission guards are
  unchanged.
- Materialization (`_materialize_profile_homes`) writes the target release's
  per-role set, and rolls back a retired role skill only after proving its bytes
  against the owning release's bundle. Deactivation (`_deactivate_profile_homes`)
  and validation (`_validate_profile_homes`, `_validate_profile_bundle`) use the
  release's own authenticated inventory rather than the current candidate list.
  Adoption before replacement is backstopped by the existing
  `_backup_profile_adoption_bytes` receipt; the nested
  `skills/software-development/plan/SKILL.md` is never touched.
- `scripts/release_bundle.py::profile_bundle_sha256` derives skills per role
  from `manager._skill_sources(role)`.
- `.github/workflows/policy.yml`: three literal heredoc lines added — (a) the
  previously missing `.aether/objective-contracts/oc_c29c2b0ed38d5030/v1.md`,
  (b) `src/aether_agents/resources/skills/plan/SKILL.md`, (c) the pre-decided
  `tests/test_plan_skill_dispatch.py` (authored later by `PLAN-NATIVE`). No
  globs, no reordering, single writer for this objective.
- Tests updated to the two-shape rule without loosening to supersets:
  `tests/test_observation_packaging.py` (`CANONICAL_SKILLS` now includes `plan`
  and the wheel set comparison is exact equality), `tests/test_observation_lifecycle.py`
  (`_profile_bundle_sha256` locks are role-aware; the materialization oracle now
  asserts Morfeo = common nine + `plan` and Supervisor/Implementer = common nine;
  new negative cases below).

## Verification actually run (candidate = commit 2)

Focused lane:

    uv run --frozen pytest tests/test_observation_packaging.py tests/test_lifecycle_adoption.py
    uv run --frozen pytest tests/test_lifecycle_projections.py
    uv run --frozen pytest tests/test_lifecycle_profile_transfer.py
    uv run --frozen pytest tests/test_release_bundle.py

Result: 9 + 11 + 34 + 3 + 38 = **95 passed**.

    uv run --frozen pytest tests/test_observation_lifecycle.py \
        -k "not test_exact_public_lifecycle_uses_real_plugin_profiles_query_and_recovery"

Result: **94 passed, 1 deselected** (263s). The deselected test needs
`hermes_cli` importable; the environment-class failure at base is unchanged and
is not caused by this unit.

    uv run --frozen python scripts/check_public_artifacts.py --root .
    uv run --frozen python scripts/check_documentation.py
    uv build --out-dir "$(mktemp -d)"

Result: all three passed (wheel
`/tmp/tmp.uieXi1T0Fp/aether_agents-1.0.0rc8-py3-none-any.whl`).

The frozen-reader and digest-agreement measurements above were reproduced at the
final candidate revision (commit 2) with a fresh build
(`/tmp/tmp.gHMStaL0is/`): `COUNT 16`, `PLAN_PRESENT True`,
`WHEEL_EQ_SDIST_EQ_SOURCE True`, and `MAT` = `LOCK` = `WHEEL` =
`3150371774be93c76ed2bb64892d25221017f1ae99101064cd4011878540dbaf`.

## Requirement coverage

| Source | Check actually run | Observed result |
| --- | --- | --- |
| US-PS-1 disposition | planning-only skill bytes: `## When to Use`, project-relative, `.aether/plans/<objective-slug>.md`, forecast not cap | asserted content present in the shipped resource and matched byte-for-byte in wheel and sdist |
| US-PS-2 disposition | the same shipped bytes are a procedure, not a contract or a quota | static resource assertion in `test_observation_packaging.py`; no quota or contract-creation wording present |
| US-PS-3 / PS-006 | wheel and sdist carry byte-identical sanitized `skills/plan/SKILL.md`; wheel profile-resource set is exactly the 16 expected names; fresh disposable Morfeo home receives `plan`; disposable Supervisor and Implementer homes do not | `WHEEL PROFILE RESOURCE COUNT: 16`, `PLAN PRESENT: True`, `WHEEL==SDIST==SOURCE: True`; `test_candidate_activation_delivers_plan_only_to_morfeo` passed |
| US-PS-4 / PS-007 | two accepted shapes only; forged/missing/extra/cross-role entries, symlinks and drift still fail closed | `test_profile_bundle_validation_accepts_only_two_exact_shapes` passed including two negative taints |
| US-PS-4 / PS-008 | pre-existing exact-path `plan` is proven against the owning release, backed up with a retained receipt, replaced only after backup; learned `plan` in Morfeo under historical release or in Supervisor/Implementer under candidate release is preserved without unverified overwrite or refusal; unowned-skill refusal is strictly confined to proven package-owned bytes from authenticated releases; nested learned `plan` untouched; rollback removes only proven managed `plan` bytes; a drifted `plan` blocks rollback and is not deleted | `test_first_install_adopts_pre_existing_exact_path_plan_with_backup`, `test_historical_release_preserves_pre_existing_learned_plan_in_morfeo`, `test_candidate_release_preserves_learned_plan_in_supervisor_and_implementer`, `test_candidate_release_rejects_canonical_plan_bytes_in_unowned_role`, `test_rollback_removes_managed_plan_and_preserves_nested_learned_plan`, `test_rollback_preserves_drifted_plan_skill_and_refuses` passed |
| Digest agreement | `_materialize_profile_bundle`, `profile_bundle_sha256`, `scripts/release_bundle.py::profile_bundle_sha256` and `_wheel_profile_bundle_sha256` on the built wheel (including duplicate-member rejection) | all four `3150371774be93c76ed2bb64892d25221017f1ae99101064cd4011878540dbaf`; `test_profile_bundle_digest_matches_the_product_materialization` and `test_wheel_profile_bundle_sha256_rejects_duplicate_member` passed |
| Ancestry | frozen predecessor's exact-set rule against each commit's wheel | rc8 reader accepts the commit-1 wheel (15 resources) and rejects the commit-2 wheel (16 resources) |
| Base-defect repair | manifest oracle with the contract line added | `test_canonical_base_manifest_matches_tracked_non_specs_files` passed for both of this unit's own lines |

Negative tamper checks (deliberately tainted, all required):

    supervisor := supervisor + plan  -> IntegrityError (cross-role)
    morfeo := morfeo + plan + bogus-skill -> IntegrityError (extra)
    wheel carrying duplicate member -> IntegrityError (duplicate member)
    unowned role with package canonical bytes -> IntegrityError (unowned skill)

All fail closed at the candidate revision (`7c580309` and its corrected successor; `f643ea5d` was a superseded local working revision).

### Pre-existing learned `plan` preservation in Supervisor and Implementer

Invariant 3 requires that Supervisor and Implementer must never receive a `plan` resource in the bundle or their homes. Invariant 1 and PS-008 require preserving operator/private state across adoption, upgrade and rollback without unverified overwrites.

Accordingly, a pre-existing learned `plan` skill in a Supervisor or Implementer home (or in a Morfeo home under a historical release) is preserved across activation: neither role receives `plan` in its target package skills, and `_validate_profile_homes` confines unowned-skill refusal strictly to bytes proven to be owned by the target release or an authenticated previous release. Operator-authored learned skills whose bytes differ from package canonical bytes are preserved, while any leaked or forged canonical package bytes in an unowned role home fail closed with `IntegrityError('managed profile activation contains unowned skill')`.

## Known red (composition-owned, not candidate-owned)

`tests/test_public_artifacts.py::test_canonical_base_manifest_matches_tracked_non_specs_files`
fails in this worktree because the heredoc now literally names
`tests/test_plan_skill_dispatch.py` while that file does not exist here.
`PLAN-NATIVE` (`t_4b5cdf5f`) writes it in its own worktree; the oracle goes green
only on the composed integration revision. The other two lines this unit owns
(`.aether/objective-contracts/oc_c29c2b0ed38d5030/v1.md` and
`src/aether_agents/resources/skills/plan/SKILL.md`) are both real repairs and are
green in this worktree. No test was skipped or weakened to pass.

## Remaining risk and limits

- Static resource, digest, materialization and transition evidence only. Nothing
  here qualifies an installed release, the native `/plan` dispatch on the
  selected fork, model behavior, or a merge as a release.
- No live profile, release, gateway, session, credential, tag, publication,
  deployment or history rewrite was touched. All measurements used disposable
  checkouts and stores.
- `PLAN-HISTORICAL` owns the isolated old→compatible→new qualification on
  real per-revision wheels; this unit supplied the two commits but did not
  perform that two-hop proof.
- The local hook environment blocks `--no-verify`; every commit here was made
  with hooks enabled and no bypass.
