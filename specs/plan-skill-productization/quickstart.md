# Run and review the canonical `/plan` candidate (#504)

This is the acceptance path for candidate verification. Run from a clean candidate worktree at the exact reviewed commit. Use disposable profile/release roots and the already selected maintained Hermes fork. Never point these exercises at a live Morfeo, Supervisor or Implementer home, gateway, sessions or an active Aether release. See [spec.md](spec.md) for PS-001–011 and [plan.md](plan.md) for expected role inventories.

## 1. Source and documentation checks (PS-001–005, PS-010–011)

```sh
git rev-parse HEAD
git status --short
git diff --check
uv run --frozen python scripts/check_documentation.py
uv run --frozen python scripts/check_public_artifacts.py
uv run --frozen pytest -q tests/test_contract_quality_documents.py tests/test_documentation.py
```

Expected: one attributable candidate revision; no unrelated/local/private file staged; the canonical `plan` frontmatter and project-local `/plan` instructions are validated with R2/guide/SOUL coherence; generated docs and public-artifact/privacy checks pass. A static text test alone does **not** prove Morfeo follows the plan or that users have an installed release. If a command's documented arguments differ in the candidate, inspect its `--help` and record the actual supported invocation before claiming a result.

## 2. Packaged role closure and disposable candidate readback (PS-006–008)

```sh
uv run --frozen pytest -q tests/test_observation_packaging.py tests/test_observation_lifecycle.py
candidate_dist="$(mktemp -d)"
uv build --out-dir "$candidate_dist"
```

Expected tests: wheel and sdist carry byte-identical sanitized `skills/plan/SKILL.md`; candidate wheel digest equals its per-role bundle digest; fresh disposable Morfeo home has the canonical `plan`, other two role homes do not. Forged/duplicate/missing/extra candidate role entries, symlinks, unsafe permissions and resource drift still fail. Exercise a same-name private learned skill at the exact canonical path without silent loss and a nested learned skill preserved. These are candidate tests, **not** an old→compatible→new transition, failed-transition compensation or rollback campaign. Report the pre-existing installed manager's inability to accept an extra skill resource as an unqualified update path; do not make its qualification a source-merge gate.

Inspect the generated wheel/sdist names before passing each as `--artifact` to `scripts/check_public_artifacts.py`; keep exact artifacts with the review evidence until closeout. These are disposable local tests. A passing source test cannot be reported as an installed-profile qualification. Do not use an installed manager to operate on the live release as a substitute for this evidence.

## 3. Native `/plan` and project-binding scenarios (PS-001–005, PS-009)

In a disposable native Morfeo profile built from the candidate bytes and a disposable Aether Project with a valid portable marker, verify the selected Hermes fork resolves `/plan` to that profile's packaged `skills/plan/SKILL.md` even if a nested private learned `plan` also exists. Confirm the skill is **absent** in disposable Supervisor/Implementer profiles. Test an explicit `/plan` request for a bounded feature and inspect the actual result:

1. One plan at `.aether/plans/<objective-slug>.md` in the *selected project*, with outcome/scope, closure, revisable anticipated contract route, history and stop/replan; no implementation, Objective Contract or board is created by the planning-only invocation.
2. A second invocation for the same objective updates the same file; a different project gets its own directory, not Aether Agents' central repository. Ambiguous or missing project binding writes nothing.
3. A plan may foresee another justified contract without treating the initial count as a quota. For authorized direct bounded work without `/plan`, no extra plan/contract ceremony is imposed.
4. Compare direct observations with the proposed instructions; record the prompt/model/surface, inspected source revision and any limitation. If a selected Hermes build reports `/plan` as a core command, stop: a profile skill cannot claim that slash name merely because its text loads via `skill_view`.

A native loader readback proves selection, not behavioral compliance. At least one real planning-only invocation should be observed when provisioned access permits it; otherwise report the behavioral gap honestly and do not call the feature fully qualified.

## 4. Wider checks and source closeout (PS-006–011)

Run the repository's documented policy checks relevant to the changed lifecycle, package and guidance. In particular, exercise `uv run --frozen python scripts/run_tests.py -- <focused pytest args>` where tests require the exact **public reference Hermes checkout**; that harness does *not* qualify `/plan` on Aether's executable fork. Qualify the slash separately with the exact maintained-fork revision in §3. Review required PR CI (pytest, type/lint, docs, package and public artifacts). Record only commands actually run and their output. Supervisor reviews the diff independently, integrates source via green PR/merge and verifies the merged commit and issue disposition. **Stop there:** this objective does not qualify historical releases, publish a package, select a local release, restart live profiles or promise a stable channel. Compatibility/release impact is reported from actual evidence separately from release action/channel.
