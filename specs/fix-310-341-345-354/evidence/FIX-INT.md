# FIX-INT integrated evidence — #310/#354/#341/#345

**Objective Contract:** `oc_0084270d940c98d9@v1`
**SHA-256:** `7447fd890a24f6c7a82ca03f6b4aa7a992299d1beda2c78e078b5c6f578812cb`
**Portable project:** `12027989-a08f-41cd-a82c-54ff1bfb6b03`
**Unit:** FIX-INT (terminal Supervisor integration/closeout)
**Review lane:** same-card unit reviews already completed on parent cards. This file is integrated evidence, not a substitute for those reviews.

AE-354's completing board run was implementer-profile. Supervisor independently re-ran `tests/test_objective_contracts.py` and `tests/test_project_init.py` on `b7f67e7d0315cceccb966e6915c944b2d9d0090d` with the exact Hermes checkout: **63 passed**.

## Source revisions

| Tree | Identity | SHA |
| --- | --- | --- |
| Aether `origin/main` at integration start | `DarkArty07/Aether-Agents` | `6562c09abc815738419c80d17929e4cefceb8a2d` |
| Fork `aether-main` at integration start | `DarkArty07/aether-hermes` | `6243e40ea6b06e85061bf3fedffaad43eed51dec` |
| Fork integration branch HEAD (pre-PR) | `fix/310-354-snapshot-worktree-base` | `d12f9a2b4c3282fe6867c4e62b844b70cee740cd` |
| Fork merge to `aether-main` | PR `DarkArty07/aether-hermes#4` | `28b593efa86bbc674b32f488c35932a4e7e85a51` |

Unit commits remain individually inspectable (no squash/amend/rebase):

| Unit | Review | Disposition | Aether commit(s) | Fork commit | Compatibility |
| --- | --- | --- | --- | --- | --- |
| HF-310 | `t_b6697b55` run 6 approved | reproduced-and-fixed | `d1086225483c34def4114f5e9227cefd4eea87e3` (evidence) | `25cabeb25327199a03aa3cf1613ed2f815f646cb` | patch |
| HF-354 | `t_edf68cf0` round-2 approved | reproduced-and-fixed | `9c74427` + `ac0fd5467323cdd0a295cdd5d93a729af357166a` (evidence) | `7d3173e1f3dba107f9a389d4e35c95f215775ee1` | patch |
| AE-354 | independent Supervisor re-run 63 passed | reproduced-and-fixed | `0e6919c82dd52e8edd350d9507a9ec9074e34264` + `b7f67e7d0315cceccb966e6915c944b2d9d0090d` | n/a | patch |
| AE-341 | `t_757a5f82` run 11 approved | reproduced-and-fixed | `f7539e3e059a7a37fed4a0c0f6ac1fa5f807f6a1` | n/a | patch |
| AE-345 | `t_15c349ea` round-2 approved | reproduced-and-fixed | `d604c281ad611df05d53f1fde21df5eefb46b1f2` + `7902f6c1bbe0759a2ed818a45852267030ac0c84` | n/a | patch |

## Independent integrated controls

Fork candidate `d12f9a2b4c3282fe6867c4e62b844b70cee740cd` (contains both fork unit commits plus `AETHER_FORK.md`):

- Canonical `scripts/run_tests.sh` owned suites, `HERMES_TEST_FILE_RETRIES=0`, sterile HOME/HERMES_HOME: **64 passed, 0 failed, 1 Windows-only skipped**.
- `git diff --check` clean vs `6243e40ea6`.
- `python3 scripts/check-windows-footguns.py tools/environments/base.py hermes_cli/kanban_db.py` — zero findings.
- Imports of `tools.environments.base` and `hermes_cli.kanban_db` resolved to the integrated candidate, not the live editable runtime.

Aether integrated tree after unit merges:

- `uv run pytest tests/test_objective_contracts.py tests/test_project_init.py`: **63 passed**.
- `uv run pytest tests/test_work_memory.py tests/test_knowledge_failures.py`: **60 passed**.
- `uv run pytest tests/test_knowledge_regressions.py`: **27 passed, 1 skipped**.
- Integration-owned GX-06 cache-seed fingerprint repair in `tests/test_knowledge_regressions.py` so the seeded fragment uses the AE-345 route digest. No production behavior change.
- Operator worktree path redacted from `specs/fix-310-341-345-354/evidence/AE-354.md`.

## Residual risk

Unresolved or mismatched actual auxiliary routes skip chunk-cache publication but may still apply validated fragments to the current graph as `state=complete`. Independent AE-345 review recorded this as cache-scoped D345 residual risk; FIX-INT does not widen D345.

Live editable Hermes and `hermes-gateway.service` were not modified or reloaded.

## GitHub / release / residue

Recorded at closeout time. See the terminal FIX-INT handoff for the final PR/check/issue/cleanup state.

Aggregate conclusions (compatibility evidence is patch; merge is not a release):

- `release_impact = patch`
- `release_action = defer`
- `release_channel = none`

No live activation, credentials, settings mutation, tags, package publication, or deployment.
