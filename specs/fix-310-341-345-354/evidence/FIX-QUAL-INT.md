# FIX-QUAL-INT integrated evidence — post-merge qualification repair

**Objective Contract:** `oc_0084270d940c98d9@v1`
**SHA-256:** `7447fd890a24f6c7a82ca03f6b4aa7a992299d1beda2c78e078b5c6f578812cb`
**Portable project:** `12027989-a08f-41cd-a82c-54ff1bfb6b03`
**Unit:** FIX-QUAL-INT (terminal Supervisor integration/closeout)
**Review lane:** same-card unit reviews already completed on `t_d38c0622` (Q-HLP, round-2 PASS) and `t_6259a45a` (Q-345, round-1 PASS). This file is integrated evidence, not a substitute for those reviews.

## Source revisions

| Tree | Identity | SHA |
| --- | --- | --- |
| Aether `origin/main` at integration start | `DarkArty07/Aether-Agents` | `cc1ea19e267afd4b2d278b6a05afd6526eb5fa42` |
| Fork `aether-main` | `DarkArty07/aether-hermes` | `28b593efa86bbc674b32f488c35932a4e7e85a51` |
| Fork unit HF-310 | already merged in fork PR #4 | `25cabeb25327199a03aa3cf1613ed2f815f646cb` |
| Fork unit HF-354 | already merged in fork PR #4 | `7d3173e1f3dba107f9a389d4e35c95f215775ee1` |

No new fork product PR. Portable Aether patches are derived from those fork unit commits.

Unit commits remain individually inspectable (no squash/amend/rebase/force):

| Unit | Review | Disposition | Aether commit | Compatibility |
| --- | --- | --- | --- | --- |
| Q-HLP | `t_d38c0622` round-2 approved | reproduced-and-fixed | `74595f90903ed267fc8c9fcb5d2de74ebab0e2e9` | patch |
| Q-345 | `t_6259a45a` round-1 approved | reproduced-and-fixed (stale fixtures, production `semantic.py` unchanged) | `ef0e16f2062803a4cadd720d890068ab7d778716` | patch |

Integration merges that preserve those commits:

- `bb81547fd0666eb9aa9eeab7d9c9d82fdcbbf795` — merge Q-HLP
- `162fd6595fe12ced5bbd9bb3166bf931b0d336e8` — merge Q-345

## Independent integrated controls

Re-executed on the integrated branch after merging both unit commits (no squash/amend/rebase/force):

- `git diff --check origin/main...HEAD`: exit 0
- `git apply --stat` of both portable patches: parsed (HLP-310 3 files 136+/7-; HLP-354 2 files 349+/7-)
- `uv run --frozen pytest tests/test_hermes_patch_reconciliation.py`: **18 passed**
- exact Hermes `v2026.8.18` (`e624e9fde561e1add9388384012b295fde669ade`) + Graphify component: `uv run --frozen pytest tests/test_knowledge_regressions.py`: **26 passed, 2 skipped**
- same suite without `AETHER_GRAPHIFY_PYTHON`: **2 passed, 26 skipped**
- Contract bytes unchanged: SHA-256 `7447fd890a24f6c7a82ca03f6b4aa7a992299d1beda2c78e078b5c6f578812cb`
- Production `src/aether_agents/knowledge/semantic.py` SHA-256 remains `dec917ad404b9a3efd51cadf41a7e3a93ace34f25376969deadb5da64f2d1423`

Portable patch SHA-256 values (Q-HLP, independently reviewed and rehashed on the integrated tree):

- HLP-310: `85522d5d5b9bf6609894b1a50f199334d8842bd8c2265d2425e2b920e184f413`
- HLP-354: `d0f185207c4ff953902c2f40aa9c48f2b27499e1b5f4a264e39a70d0a2383fc1`

Optional integration-owned ledger lines added in `HERMES_LOCAL_PATCHES.md` HLP-310/HLP-354 sections naming those portable SHA-256 values. Unit commits were not rewritten. The FIX-QUAL breakdown in `specs/fix-310-341-345-354/tasks.md` is recorded here as Supervisor-owned execution evidence.

## Residual risk

- Unresolved or mismatched actual auxiliary routes skip chunk-cache publication but may still apply validated fragments to the current graph as `state=complete` (cache-scoped D345; not widened).
- Finalized Objective Contract `oc_0084270d940c98d9@v1` still contains an operator-local path rejected by public artifact policy. Tracked as Aether #364. Not edited, not exempted from scanning.
- Aether #362 (review reassignment) remains separate and OPEN.

Live editable Hermes and gateway were not modified or reloaded.

## GitHub / release / residue

Filled at closeout. Local integration alone is not terminal.

Aggregate conclusions (compatibility evidence is patch; merge is not a release):

- `release_impact = patch`
- `release_action = defer`
- `release_channel = none`

No live activation, credentials, settings mutation, tags, package publication, or deployment. Aether `v1.0.0` gate remains firm.
