# HLP-226C evidence

## Pre-dispatch inspection

Evidence below is inspection/reproduction by Morfeo, not implementation or independent
Supervisor review.

| Criterion/question | Artifact and revision | Check and producer | Result/limit |
| --- | --- | --- | --- |
| Does the reported recurrence still exist? | `DarkArty07/aether-hermes@415056fee527c5a2302370bd6dba56f84b9a4202`; `hermes_cli/kanban_db.py`, `tools/kanban_tools.py` | Direct disposable two-profile/current-board reproduction by Morfeo | Reproduced. A Project-bearing nonterminal Supervisor `dir` source at `<repo>/.worktrees/<prior-board-id>`, with the leaf absent from the current board and zero Projects in the Supervisor profile, returned `kanban_create: session-affinity tasks require a canonical project_id` when creating the same-flow terminal. |
| Is the existing HLP-226b condition the cause? | Same fork revision; Project source fallback in `hermes_cli/kanban_db.py` | Direct source inspection by Morfeo | Yes. The fallback looks up the workspace leaf as a task in the already-open board and accepts the source only after obtaining a `workspace_kind="worktree"` anchor. A prior-board leaf is absent, leaving the current `dir` source ineligible and dropping Project before affinity validation. |
| Does current upstream already provide an equivalent fix? | `NousResearch/hermes-agent@67764dc0863349a384c16425e73ee8571f3a94b7`; `_project_from_source_task` and `kanban_create` handler | Direct fetched-source inspection and GitHub issue/PR search by Morfeo | No equivalent found. Current upstream accepts only a source task that itself is a canonical task-id-keyed `worktree`; it contains no same-flow terminal/shared-`dir` behavior. Search found no open matching upstream issue/PR. Limit: absence is proven for the inspected revision/search, not all future upstream history. |
| Is board metadata sufficient to identify the intended repository without cross-board task lookup? | Aether `src/aether_agents/objective_contracts/hermes_plugin.py`; fork `hermes_cli/kanban_db.py` | Direct source inspection by Morfeo | The execution board durably carries the Hermes Project id and `default_workdir`; native task creation already inherits the board Project and uses `default_workdir` for persistent workspace defaults. The selected design requires both fields to match the source Project and the repository containing the shared `.worktrees/<leaf>` path. |
| Is another active owner already implementing #226? | GitHub issue/PR state, active Kanban board titles, fork open PRs | Direct read-only inspection by Morfeo | No visible open Aether/fork PR or active board card matched #226 at dispatch design time. Issue #226 is open/reopened and unassigned. |

## Design self-check

A cold read of `spec.md`, `plan.md`, and `quickstart.md` fixes the material authority source,
positive lifecycle, cross-profile worktree outcome, negative matrix, exact implementation and
upstream baselines, reconciliation surfaces, test path, release disposition, and no-activation
boundary. Supervisor still owns decomposition, independent receipt review, unit sequencing,
integration, and proportionate adaptation to exact current test-file names. Implementers retain
private helper/fixture choices that preserve the stated invariants.

## Pipeline result reception

Supervisor/Implementer evidence is appended here after delivery. No pre-dispatch statement
below this heading is a claim that implementation, review, merge, activation, or objective
acceptance occurred.

## AE-226C implementation evidence — portable HLP-226c artifact and reconciliation

Producer: Implementer unit AE-226C (card `t_a26cf45a`) for Objective Contract
`oc_644c0b407d13366a@v1`, derived from the committed breakdown
`specs/hlp-226-cross-board-project-inheritance/tasks.md` at Aether decomposition
`a1f66117c2641266b3e76ea0da370e256b47ed41` on base
`63dd88790e3a0ec78c465d6d6c85e051502e2428`; the contract artifact was re-verified as SHA-256
`ca1264fb74ff07e1b0a5206e527e3dd6ec7676b8c82f07915f5f38a4308593a5` before mutation and was
not edited, copied, staged or committed. This section records implementation, artifact and
reconstruction evidence only. It is not independent review and it makes no claim about final
pull-request, merge, issue, activation or objective-acceptance state; H226C-INT owns
integration, the durable ledgers and closeout.

### Reviewed fork producer and exact revisions

| Item | Value |
| --- | --- |
| Behavior producer | HF-226C (card `t_3458185e`), approved by same-card Supervisor review at fork commit `7980bbf1f9f75efdcbee2196ae910bb77138541d` (tree `0f4912cc1a1f3ccae66d604d3960c259c7e9d618`) |
| Fork repository | `https://github.com/DarkArty07/aether-hermes.git` (resolved by remote URL) |
| Fork base | `415056fee527c5a2302370bd6dba56f84b9a4202` |
| Accepted commits | `d962b73e3d5c73aa21c500c6e1c51026dfb0d686`, `3f981f10924774afd4b9a72d81f525fafe64fd5c`, `7980bbf1f9f75efdcbee2196ae910bb77138541d` on `fix/226c-cross-board-project-inheritance` (local to the fork clone; not pushed) |
| Accepted scope | 3 files, `+805/-0`: `hermes_cli/kanban_db.py` +100, `tools/kanban_tools.py` +6, `tests/tools/test_kanban_cross_board_project.py` +699 (new file) |
| Producer evidence | fork evidence attachment `hlp226c-fork-evidence-r2.txt`, SHA-256 `294d297cbcae4642866b3c304f28fe6b76606f4a243a57989783185c6602fa10` |

Fork behavioral results are recorded here with their actual producers; AE-226C did not
execute the fork suites and does not restate them as its own result.

The reviewed HF-226C producer reports (attachment `hlp226c-fork-evidence-r2.txt`): identical
21-test module bytes failed 3 of 21 on the unchanged base with `kanban_create:
session-affinity tasks require a canonical project_id` and passed 21 of 21 on the accepted
candidate (the module contains the two-profile materialized E2E and the fail-closed matrix);
reverting only `tools/kanban_tools.py` to its base bytes left 20 passed / 1 failed (the
explicit-target-board regression); the minimum affected run passed 132 with 1 Windows-only
skip; `compileall`, Ruff check/format on touched scope and range `git diff --check` passed.
The producer's own documented full fork suite reported 31020 passed / 2392 failed / 262
skipped, and its only delta against the recorded 424-file baseline failure set was one
attributed parallel-run `test_coalesce_session_args.py` pytest teardown race whose file passed
3/3 in isolation.

The accepted same-card Supervisor review (round 2) independently reran at the exact candidate
revision and reproduced the baseline RED 18 passed / 3 failed, the tool-hunk sensitivity 20
passed / 1 failed, and the candidate minimum affected run 132 passed with 1 Windows-only
skip. Its independent documented full runner reported 31022 passed / 2393 failed / 262
skipped, with the new module passing 21 and `test_coalesce_session_args` passing 3, and its
sole delta against the recorded failure set was a `test_install_macos_launcher` failure
induced by the reviewer's sterile HOME lacking any shell configuration; that test passed 1/1
in an isolated zero-retry rerun under a disposable representative `.bashrc`, leaving the
recorded unrelated failure set behaviorally unchanged. Both full-suite observations ran once
each in a local dev environment: their pre-existing environment-driven failures are
unchanged, not resolved and not a qualification, and neither observation activates a live
runtime.

### Portable artifact

| Item | Value |
| --- | --- |
| Component | `HLP-226c` |
| Path | `patches/hermes/HLP-226c-cross-board-project-inheritance.patch` |
| SHA-256 | `6b1c5b498d7eab58b301340920d18f2d28b3c87c813ff614445515771dd8f418` |
| Size | 861 lines; `git apply --numstat` per file `100/0`, `699/0`, `6/0` (805 insertions, 0 deletions) |
| Corpus whitespace gate | the three whitespace-only context lines of the raw `git diff` text were normalized to empty context lines so the recorded artifact passes the repository's own `git diff --check` / `git diff-tree --check` gate; no added or removed line was touched, and the normalized patch re-passed `git apply --check` and reconstructed all three candidate files to the identical SHA-256 values. The raw pre-normalization `git diff` text alone hashed to SHA-256 `5532b3461c3563aadadceff7caad585d5bffd78cb7783f243746be6071bba945`; that value identifies only the pre-normalization raw diff and is never the portable artifact digest |
| Generation | file-scoped `git diff 415056fee527c5a2302370bd6dba56f84b9a4202 7980bbf1f9f75efdcbee2196ae910bb77138541d -- hermes_cli/kanban_db.py tools/kanban_tools.py tests/tools/test_kanban_cross_board_project.py`, run in the maintained-fork clone at the exact base and accepted candidate |
| Portability | repo-relative Hermes paths only; no operator path, home directory, credential or raw runtime state in the patch text |
| Preservation | the pre-existing `patches/hermes/HLP-226b-affinity-terminal-project-inheritance.patch` is byte-identical to the reviewed revision (SHA-256 `a28fd10888932f421d32d41e1012ec7aad17280ae9e289c4d0329ff492f6c040`), and it was not collapsed into or replaced by the new artifact |
| Both-artifact controls | the HLP-226b artifact was re-verified at its recorded SHA-256 and parsed with `git apply --numstat/--stat` (2 files, `+144/-7`); the HLP-226c artifact parses with the same controls (3 files, `+805/-0`). Neither parse is an application or reconstruction pass against this Aether tree, which does not contain the Hermes target files |

### Reconstruction against the exact fork base

| Step | Observed result |
| --- | --- |
| Disposable detached worktree of the maintained-fork clone at exact base `415056fee527c5a2302370bd6dba56f84b9a4202` | Created outside the repository; base `hermes_cli/kanban_db.py` SHA-256 `2c36ef7887320fffe3c993ac5bc0d03091a232ebc9a85746e8bf937e042af58d` and `tools/kanban_tools.py` SHA-256 `1a7939e87fb9300094c0a9f6e98de347ff31628bf59e5f89a52775a92d89ffb1` matched the recorded baseline values; `tests/tools/test_kanban_cross_board_project.py` absent as expected |
| `git apply --check -v <patch>` at the exact base | passed for all three files |
| `git apply <patch>` at the exact base | applied with no fuzz or fallback |
| Reconstructed file SHA-256 | `hermes_cli/kanban_db.py` `8e0e359e0e86200051069d02ca8ca7be44d1e594dca89ec8e118c7e68ab2e857`; `tools/kanban_tools.py` `1d967da8ea38fc545461e905894b43f8c12fae2f4732654de3aaf43d7a87728e`; `tests/tools/test_kanban_cross_board_project.py` `c33037250f2872576e4d65579d729f946d18166579b73846c66c8e57871ac59a` — identical to the reviewed candidate file hashes |
| Reconstructed Git object identity | blob IDs `00bb50193caa70e4a3415f832c0c750643f2963f`, `9071f38ce3b46e30e00c7ae82a3867f1f9e3f87d`, `7775e12df1ae06caa1f687c20214e216e7325bb9` — identical to the same paths at `7980bbf1f9f75efdcbee2196ae910bb77138541d` (tree `0f4912cc1a1f3ccae66d604d3960c259c7e9d618`) |

The disposable base worktree was removed after the reconstruction; the maintained-fork
checkout whose branch is `aether-main` and the loaded editable Hermes runtime were never
edited, reloaded or activated.

### Reconciliation fragment, tests and generated outputs

| Item | Change | Control |
| --- | --- | --- |
| `specs/001-aether-v1-productization/evidence/hermes-patch-reconciliation/entries/HLP-226.json` | `components` are now `["HLP-226", "HLP-226b", "HLP-226c"]`; the fragment declares both portable patch artifacts with their own SHA-256 values (HLP-226b `a28fd108…f6c040` unchanged, HLP-226c `6b1c5b498d7eab58b301340920d18f2d28b3c87c813ff614445515771dd8f418` new), plus a `passed` HLP-226c reconstruction input (`415056fee527c5a2302370bd6dba56f84b9a4202`) and reconstruction record; the HLP-226b reconstruction entries and the record-level `unavailable` status and blocker are preserved | the earlier HLP-226b digest was neither overwritten nor collapsed; the record-level blocker still carries the unavailability of the HLP-226b private reconstruction input |
| `tests/test_hermes_patch_reconciliation.py` | repository-set coverage now binds per-identifier patch digest tuples; one positive control asserts the exact three components, both patch references and both on-disk digests, and the presence of a passed reconstruction; fail-closed controls cover an absent `HLP-226c` component, an absent `HLP-226c` patch artifact, and digest drift parameterized over both HLP-226 patch artifacts | focused run `23 passed` (was `19 passed`); no assertion, validator rule or skip was weakened |
| `scripts/validate_hermes_patch_reconciliation.py` | the HLP-226 rule now requires the three declared components and both portable patch references instead of two components and the HLP-226b artifact only; the check is strictly stronger for the same record and no other record's rule changed | `test_repository_fragments_reject_hlp226_without_hlp226c_component`, `…_without_hlp226c_patch_artifact` and the parameterized `…_patch_digest_drift` fail closed through this rule |
| `.github/workflows/policy.yml` | canonical base manifest gains only `patches/hermes/HLP-226c-cross-board-project-inheritance.patch`, in sorted position | no other manifest line changed |
| `specs/001-aether-v1-productization/evidence/hermes-patch-reconciliation.v1.json` and `…/hermes-patch-preflight.md` | regenerated from the documented generator at observation timestamp `2026-09-10T17:04:30Z` with the recorded upstream revision; the HLP-226 record now shows the three components and both bound patches, and four fragments that had been committed earlier but never aggregated (`HLP-305`, `HLP-310`, `HLP-354`, `HLP-369`) are present for the first time | generated, not hand-edited; the file's ledger SHA-256 advanced to `04df9bc957958e0c62fba7f9d9877850db475b62e32f9218d02b08703741774d`, so H226C-INT must regenerate both outputs again after the HLP-226c ledger paragraph lands |

Local judgement exercised, with the round-1 review scope recorded: the card's exclusive
writable list named the fragment and the tests but not
`scripts/validate_hermes_patch_reconciliation.py`. A fail-closed control over all three
components is only real if validation requires the third component, so the HLP-226 branch of
that rule was extended to the same shape the repository already uses for the HLP-211b and
HLP-226b components: it now requires the three declared components and both portable patch
references. The change is additive, HLP-226-scoped, reversible in one hunk, and weakens no
existing rule. In review round 1 the Supervisor explicitly authorized retaining exactly this
existing HLP-226-scoped one-hunk strengthening for the rework and authorized no other
validator or schema change; this scope clarification is recorded here and in the AE-226C
rework handoff.

### Aether gates executed

| Command | Observed result |
| --- | --- |
| `uv run --frozen python scripts/validate_hermes_patch_reconciliation.py --observed-at-utc 2026-09-10T17:04:30Z --upstream-repository https://github.com/NousResearch/hermes-agent --upstream-revision 4f22543509d1b91dc45bcb369447126c5eb14fb7` | `reconciliation validation passed` |
| `HERMES_TEST_FILE_RETRIES=0 uv run --frozen python -m pytest tests/test_hermes_patch_reconciliation.py -q` | `23 passed` (baseline before this unit: `19 passed`) |
| `HERMES_TEST_FILE_RETRIES=0 uv run --frozen python -m pytest tests/test_documentation.py tests/test_public_artifacts.py -q` | `1 failed, 16 passed`; the sole failure is the pre-existing immutable-contract operator-path finding in `.aether/objective-contracts/oc_0084270d940c98d9/v1.md`, tracked by excluded #364 and unchanged by this unit (that contract is byte-identical to HEAD and was not touched) |
| `uv run --frozen python scripts/check_hermes_baseline_drift.py --json` | passed; selected baseline `v2026.8.18` / `e624e9fde561e1add9388384012b295fde669ade` / `0.20.4` unchanged |
| `uv run --frozen python scripts/check_documentation.py` | `documentation validation passed` |
| `uv run --frozen python scripts/check_public_artifacts.py --root .` and the same command with the freshly built wheel and sdist | only the same pre-existing #364 contract finding; no finding attributable to this unit's new artifacts |
| `uv run --frozen ruff check src tests scripts/check_documentation.py scripts/qualify_knowledge_expansion.py scripts/qualify_observation.py scripts/check_hermes_baseline_drift.py scripts/check_public_artifacts.py scripts/run_tests.py scripts/validate_hermes_patch_reconciliation.py` | `All checks passed!` |
| `uv run --frozen ruff format --check` on the same set | `4 files would be reformatted` — `src/aether_agents/knowledge/semantic.py`, `src/aether_agents/objective_contracts/hermes_plugin.py`, `tests/test_knowledge_regressions.py`, `tests/test_objective_contracts.py`; all four are byte-identical to HEAD (0 diff) and none is touched by this unit, so this is unchanged pre-existing format debt |
| `uv run --frozen mypy src/aether_agents` | `Success: no issues found in 53 source files` |
| `uv run --frozen python -m compileall -q` on the repository gate file set | exit 0 |
| `uv build --out-dir <scratch>` | `aether_agents-0.24.0-py3-none-any.whl` and `aether_agents-0.24.0.tar.gz` built |
| `HERMES_TEST_FILE_RETRIES=0 uv run --frozen python scripts/run_tests.py` | `2 failed, 1175 passed, 64 skipped in 224.37s`. Both failures are the recorded unrelated baseline findings — `tests/test_public_artifacts.py::test_tracked_public_surface_contains_no_operator_paths` (historical `oc_0084270d940c98d9` operator-path finding, excluded #364) and `tests/test_same_card_phase_predicates.py::test_initial_review_requires_an_independent_reviewer` (known review-lifecycle baseline behavior). Unchanged-baseline equivalence was established directly: the same two tests ran in the unmodified decomposition worktree at `a1f66117c2641266b3e76ea0da370e256b47ed41` and reproduced `2 failed, 14 passed`. The 64 skips match the recorded baseline; the higher pass count reflects tests added by later accepted units |
| `git diff --check` | clean |
| Locally simulated canonical base manifest check (workflow `policy.yml` step 1) | the only difference is `.aether/objective-contracts/oc_644c0b407d13366a/v1.md`, which is tracked from the objective base `63dd88790e3a0ec78c465d6d6c85e051502e2428` but was never added to the manifest list (`policy.yml` is unchanged since that base, and 42 of 43 tracked contracts are listed). The new `patches/hermes/HLP-226c-cross-board-project-inheritance.patch` entry is accounted for. This pre-existing gap is outside AE-226C's narrow `policy.yml` scope and is reported for H226C-INT: the objective's policy job cannot pass while the contract path is missing from the manifest |

Rework re-verification (round-1 evidence correction): the validator, the focused reconciliation
tests, `check_documentation.py`, `tests/test_documentation.py` with
`tests/test_public_artifacts.py` (`1 failed, 16 passed`, the same pre-existing
`oc_0084270d940c98d9` #364 finding), the public-artifact scan, the baseline drift check, Ruff
check/format on the touched Python files, the push-form `git diff-tree --check` and
`git diff --check` were re-run at the rework revision and returned the same results recorded
above; the validator regeneration left both generated outputs byte-identical (empty diff). The
full runner and the build were not re-executed for this documentation-only correction.

Toolchain: Python 3.13.15 through `uv 0.12.3` (`uv run --frozen`), Ruff 0.16.4, MyPy 1.20.2,
git 2.55.0. GitHub Actions and PR/check state are not claimed here: this unit performs no
push, pull request, merge or issue mutation.

### Preservation, no-activation audit and limits

- Preserved byte-for-byte: `patches/hermes/HLP-226b-affinity-terminal-project-inheritance.patch`,
  every other patch record, `HERMES_LOCAL_PATCHES.md`, the fork `AETHER_FORK.md`, the Objective
  Contract, product source, lockfiles and `AGENTS.md`. No ledger paragraph was applied by this
  unit; the proposed exact text is in the AE-226C handoff for H226C-INT.
- No live runtime, board, profile, configuration, model, provider, credential or settings
  mutation; no activation, reload or restart; no release, deployment or publication; no work on
  #275, #367, #368, #352 or #357.
- Limits: the fork suites and the two-step E2E were not re-executed by AE-226C (H226C-INT
  repeats them at the final integrated fork revision); no reconstruction was attempted against
  the inspected upstream revision, which does not contain the required behavior; the generated
  reconciliation aggregate and preflight will need one more regeneration by H226C-INT once the
  durable ledger records the HLP-226c SHA-256.

## H226C-INT terminal integration evidence

Producer: Supervisor terminal card `t_08c43ab2`. This section receives the two
independently reviewed units; it does not replace their same-card reviews.

### Integration provenance and maintained-fork closeout

- HF-226C was approved at exact fork commit
  `7980bbf1f9f75efdcbee2196ae910bb77138541d` (tree
  `0f4912cc1a1f3ccae66d604d3960c259c7e9d618`). Its three commits remain distinct:
  `d962b73e3d5c73aa21c500c6e1c51026dfb0d686`,
  `3f981f10924774afd4b9a72d81f525fafe64fd5c`, and
  `7980bbf1f9f75efdcbee2196ae910bb77138541d`.
- The terminal created a clean integration worktree from exact maintained-fork base
  `415056fee527c5a2302370bd6dba56f84b9a4202`, fast-forwarded to the reviewed head,
  and added only fork-ledger commit
  `311f1f4d737df7c2d465d4f16bcfae5334d190ba`. No squash, amend, rebase, force push,
  or history rewrite occurred.
- `DarkArty07/aether-hermes` PR
  [#7](https://github.com/DarkArty07/aether-hermes/pull/7) was clean and mergeable with
  exact head `311f1f4d737df7c2d465d4f16bcfae5334d190ba`; it merged normally to
  `aether-main` as `266e412fb83ad32af92ed391db942f88993d76a2`. The merge parents are exact
  prior `aether-main` `415056fee527c5a2302370bd6dba56f84b9a4202` and the reviewed-plus-ledger
  head `311f1f4d737df7c2d465d4f16bcfae5334d190ba`. The merged tree is
  `37d7a2b536ac15b6d25d85da97dfd06bae507f83`.
- Inherited fork Actions remain disabled; PR #7 has an empty check rollup. They are
  **NOT RUN**, not green. This objective did not enable or modify repository Actions.

### Independent final fork verification

All commands ran at exact fork source commit
`311f1f4d737df7c2d465d4f16bcfae5334d190ba`; PR merge
`266e412fb83ad32af92ed391db942f88993d76a2` contains that tree unchanged.
The provisioned CPython was 3.11.15 with pytest 9.1.1 and Ruff 0.16.1. Retries were
explicitly disabled.

| Check | Terminal observation |
| --- | --- |
| H226C-FR-001 through H226C-FR-004, including the real materialized two-profile terminal-to-Implementer path and explicit target-board/decoy-board control | `HERMES_TEST_FILE_RETRIES=0 scripts/run_tests.sh tests/tools/test_kanban_tools.py tests/hermes_cli/test_kanban_db.py tests/hermes_cli/test_kanban_session_affinity.py tests/tools/test_kanban_cross_board_project.py` passed `132`, failed `0`, skipped `1` Windows-only. The focused HLP-226c module passed all `21`; its E2E materialized and inspected the task-id-keyed checkout, while the negative matrix failed before invalid persistence and left worker Project registries empty. |
| Exact final full fork runner | One retained log-captured zero-retry run discovered `2997` files and reported `31022 passed, 2392 failed, 262 skipped` in 918.0 seconds with 24 workers. The HLP-226c module passed all `21`. The `421` failing files and `4` collection/no-test files are the already attributed missing-optional-dependency/async-plugin environment baseline; no objective-changed source/test file is in either set. An earlier terminal process run independently showed the same `2392` failures across `421` files and a green HLP-226c module; its exact summary was not retained by the process-log pagination surface, so it is not used for the exact total. No further full-suite restart was made. |
| Static and diff checks | `python -m compileall -q hermes_cli tools tests`, Ruff check on both production files and the new test, Ruff format check on the new test, and range/working-tree `git diff --check` passed. The known whole-production-file format debt predates this objective and was not reformatted. |
| Portable reconstruction | HLP-226c SHA-256 `6b1c5b498d7eab58b301340920d18f2d28b3c87c813ff614445515771dd8f418`; exact-base `git apply --check` and all three reconstructed file/blob identities match reviewed `7980bbf1`. HLP-226b remains byte-identical at SHA-256 `a28fd10888932f421d32d41e1012ec7aad17280ae9e289c4d0329ff492f6c040`; its historical private reconstruction input remains unavailable and is not inferred. |

### Aether integration state before publication

AE-226C was approved at `bf1bcb4c8580f87f5a5102d56d2161a310a08913` (tree
`cdadae123a8c32f0b6f095dec74da8110fd91257`). The terminal fast-forwarded the
Aether objective branch from decomposition `a1f66117c2641266b3e76ea0da370e256b47ed41`
through all four reviewed AE-226C commits without rewriting them. The terminal then:

- updated `HERMES_LOCAL_PATCHES.md` with the exact fork PR/merge, patch digest,
  compatibility, no-activation state, rollback, and retirement gate;
- re-pinned the HLP-226 reconciliation locator and status to distinguish existing live
  HLP-226/HLP-226b from maintained-fork-only HLP-226c;
- added the already-tracked finalized Objective Contract path to the canonical workflow
  manifest. This is mechanically implied policy/build glue: the contract existed at the
  objective base but the exact manifest omitted it; no policy behavior or authority changed;
- regenerated the aggregate reconciliation and preflight at
  `2026-09-10T18:18:11Z` from the updated ledger SHA-256
  `c5dfccb4108986a162fd4f84cd3d6686031d7c42ca185e8bcff66c44616dc487`; the
  aggregate binds the same ledger digest, the exact three HLP-226 components, both
  patch digests, and maintained-fork-only HLP-226c status.

Aether PR/check/merge, issue reconciliation, and merged-resource cleanup are recorded
below only after they occur. Local integration alone is not acceptance. The terminal
first established exact-final Aether evidence: the canonical full runner passed
`1175`, failed `2`, and skipped `64`. Both failures already exist on exact
`origin/main` `2f72fcf420c0634da262c2f6dcbad0574c4b6a01`, which produced the same
`2 failed, 14 passed` for the identical two modules; neither touched file is owned by
this objective.

### Owner steering and no-activation boundary

During terminal verification the owner instructed the campaign to stop after completion of
this current #226 objective. The terminal therefore finishes only the existing #226
verification, dual-repository PR/check/merge, evidence, issue reconciliation, and
objective-owned merged-resource cleanup. It starts no successor bug, batch, feature,
expanded repair chain, or #275 work; Morfeo owns final reception/report and will not restart
the backlog. A material new behavior/design/scope or unsafe-effect blocker would preserve
the current candidates/logs/PRs and stop through the native blocker path rather than widen
this objective.

No live Hermes source, TUI, gateway, service, installation, profile, Project registry,
configuration, model, provider, credential, repository setting/protection, or board database
was modified or activated. No reload/restart, release preparation/publication, package
publication, deployment, tag, history rewrite, bypass, or #275/#367/#368/#352/#357 work
occurred. Disposable test boards, repositories, profiles and worktrees were the only runtime
state used for behavioral qualification.
