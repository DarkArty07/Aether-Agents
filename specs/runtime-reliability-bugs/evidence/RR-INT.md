# RR-INT integrated evidence — runtime reliability (#267/#292/#294/#295/#301/#304)

**Objective Contract:** `oc_5c2dad1b37b20a80@v1`
**SHA-256:** `8d9af05c77d7833675a8f985742c471963f77cd30aa8cd993837a1fcf9eeda4e`
**Portable project:** `12027989-a08f-41cd-a82c-54ff1bfb6b03`
**Unit:** RR-INT (terminal Supervisor integration/closeout)
**Review lane:** same-card unit reviews already completed on the parent cards; this file is integrated evidence, not a substitute for those reviews.

## Source revisions

| Tree | Identity | SHA |
| --- | --- | --- |
| Aether `origin/main` at integration start | `DarkArty07/Aether-Agents` | `3ded6953ab9db44281a6c67fcdf93189546126a1` |
| Design/contract base | `0dd27e0eff060f143f80879845f0d76561633f56` | merged `--no-ff` |
| Decomposition `tasks.md` | `7a45aa4715bc6f5a2746a7289fc5a2bcbff6fe7e` | merged `--no-ff` |
| Aether integration branch HEAD (pre-PR) | `fix/runtime-reliability-six-bugs` | `853c9bea7348f989a059c8bed6b790835bcb4164` |
| Fork `aether-main` | `DarkArty07/aether-hermes` | `c185ee3bb5b6d609241432fd123c16143f065987` |
| Fork integration branch HEAD (pre-PR) | `fix/runtime-reliability-six-bugs` | `55ab4c0603e6f8a8f7944bdd78d5ef7b7bcbf8bd` |
| Fork merge to `aether-main` | PR `DarkArty07/aether-hermes#2` | `4b5772ff43de70f1222aabbf1daed4eefc7b44cf` |
| Exact Hermes baseline (Aether wrapper) | tag `v2026.8.18` | `e624e9fde561e1add9388384012b295fde669ade` |
| Immutable upstream citation | `NousResearch/hermes-agent` | `9fd44b4dfc44138b9e5d5689acb56c438364ff7b` |

GitHub merge SHAs and PR numbers are recorded in the closeout section after merge.

Unit commits remain individually inspectable (no squash/amend/rebase):

| Unit | Review run | Disposition | Aether commit(s) | Fork commit(s) | Compatibility |
| --- | --- | --- | --- | --- | --- |
| RR-267 | t_ea6c98a6 run 18 approved | reproduced-and-fixed | `66bb4dd6638ab1da8e9a56fd9e63211906fafeb6`, `a67f3d78bad49cac3c8debf3b5ef118c14590f19` | n/a | patch |
| RR-304 | t_0e064c53 run 14 approved | reproduced-and-fixed | `6aa83af1ea768c1f908d1a70088d44506836716c` (evidence) | `169572a845f30bda0231cb97035bfce5fb9e981d` | patch |
| RR-295 | t_5894f87f run 16 approved | reproduced-and-fixed | `d06cbd265fd9932585279b5d23da1a25ea7145ff` (evidence) | `b58db22b4968e837a745a42cae5cb007f3819a8c` | patch |
| RR-AUX B292 | t_2858d06b run 12 approved | already-working-with-integrated-evidence | `5c38247e07352098cca4f0534cd4dc12bb388479` (evidence) | `2337bd2d9efbf0421ac121877936e92bb9486e70` (tests only) | none |
| RR-AUX B301 | same | reproduced-and-fixed | same evidence | `0f56400b1603c8195590a04da47424a0df40b145` | patch |
| RR-294 | t_174a8028 run 20 approved | reproduced-and-fixed | `99f6271631cb4a6f8cadbe351aed3723ece40fc6` (evidence) | `cf5ff5fe2f51116364a10a9941f58f280e7ff4c4` | patch |

## Independent reviewer controls (integrated trees)

- B267: `_observe_native_affinity_controls` uses `isolated_hermes_env`, not `os.environ.copy()`; leaked identity names and `preflight_disposable_destinations` present. Focused sterile suite `48 passed, 1 skipped`.
- B304: `evaluate_kanban_stop` keeps transcript `MISSING` while ALLOW-ing on durable proof; `_verify_durable_completion` uses `mode=ro` and `BEGIN`.
- B295: 503/529 branch matches phrase `no available Codex accounts` after overflow; guessed `pool_exhausted` code is not in that branch.
- B301: `_CodexCompletionsAdapter.create` copies `kwargs['extra_headers']` into `resp_kwargs`; `_safe_request_extra_headers` exists for fallback.
- B294: `_BackgroundReviewRun` / cancel-before-admission path present. Assigned interruption file `8 passed` on the integrated candidate.

`conversation_loop.py`, `run_agent.py`, `tools/kanban_tools.py`, and `hermes_cli/kanban_db.py` are unchanged vs fork `c185ee3`. Objective Contract bytes remain `8d9af05c77d7833675a8f985742c471963f77cd30aa8cd993837a1fcf9eeda4e`.

## Per-issue integrated matrix

Sterile `lab_run` from `quickstart.md`; `HERMES_TEST_FILE_RETRIES=0`. Aether wrapper authenticates exact `v2026.8.18`. Fork runner is `scripts/run_tests.sh`.

| Requirement | Disposition | Integrated command result |
| --- | --- | --- |
| B267 | reproduced-and-fixed | `uv run --frozen python scripts/run_tests.py -- -q --tb=short tests/test_e2e_harness.py tests/test_observation_qualification.py` → **48 passed, 1 skipped in 10.50s** |
| B304 | reproduced-and-fixed | fork `scripts/run_tests.sh tests/agent/test_kanban_stop.py tests/agent/test_kanban_stop_durable_recovery.py` → **14 + 12 passed** (part of 372/0 assigned matrix) |
| B295 | reproduced-and-fixed | fork `test_error_classifier.py` **87 passed**, `test_exhausted_pool_fallback.py` **6 passed** |
| B301 | reproduced-and-fixed | fork `test_auxiliary_client_extra_headers.py` **5 passed**; `test_auxiliary_client.py` **181 passed** |
| B292 | already-working-with-integrated-evidence | fork `test_auxiliary_named_custom_providers.py` **24 passed**; no product-code patch |
| B294 | reproduced-and-fixed | fork interruption file **8 passed**; assigned background-review files **30 passed** of the 38 |

Assigned fork matrix (13 files): **372 passed, 0 failed in 16.1s**.

Aether documentation/drift/lint: `check_hermes_baseline_drift.py --json` exit 0 (exact `e624e9fde561e1add9388384012b295fde669ade`); `check_documentation.py` passed; ruff check/format on touched Python passed; `git diff --check` clean after RR-AUX trailing-whitespace repair.

Aether full exact-Hermes suite: **1062 passed, 59 skipped, 373 subtests passed in 280.09s**.

Fork `tests/agent/` + `tests/run_agent/`: **6195 passed, 0 failed, 31 skipped** across 574 files, plus one unrelated timeout of `tests/agent/test_model_metadata.py` (300s file timeout after 82 collected). The same file timed out at 60s on unchanged `c185ee3bb5b6d609241432fd123c16143f065987`. Not in this objective's writable surface. macOS/Windows-only tests skipped on Linux as documented by the runner.

## GitHub / release / residue

Filled at closeout.

Anticipated aggregate conclusions (compatibility evidence supports patch; merge is not a release):

- `release_impact = patch`
- `release_action = defer`
- `release_channel = none`

Fork Actions: repository `actions/permissions.enabled=false`. Inherited workflows in-tree are **NOT RUN**, not green.

No live activation, credentials, settings mutation, tags, or package publication.
