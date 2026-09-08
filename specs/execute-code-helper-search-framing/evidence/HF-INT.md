# HF-INT integrated evidence — execute_code helper contract and search_files JSON framing (#313/#353)

**Objective Contract:** `oc_fd2332ffe34aa5f7@v1`
**SHA-256:** `6371b8f4900aa4266ffd1a9acd990d1072ecf5fbaf922fc065eee37828410515`
**Portable project:** `12027989-a08f-41cd-a82c-54ff1bfb6b03`
**Unit:** HF-INT (terminal Supervisor integration/closeout)
**Review lane:** same-card unit reviews already completed on parent cards `t_dcec38eb` (run 4) and `t_88ba2a9a` (run 5). This file is integrated evidence, not a substitute for those reviews.

## Source revisions

| Tree | Identity | SHA |
| --- | --- | --- |
| Aether `origin/main` at integration start | `DarkArty07/Aether-Agents` | `419fddc67826b28ae39e22b446c38065542131db` |
| Fork `aether-main` at integration start | `DarkArty07/aether-hermes` | `4b5772ff43de70f1222aabbf1daed4eefc7b44cf` |
| Fork integration branch HEAD (pre-PR) | `fix/execute-code-helper-search-framing` | `cd27d426291c5b956310454ecf623e26774d014f` |
| Fork merge to `aether-main` | PR `DarkArty07/aether-hermes#3` | `6243e40ea6b06e85061bf3fedffaad43eed51dec` |
| Upstream #313 citation | `NousResearch/hermes-agent` | `65f033a1a20e847b7a150fe6168cd345385c7d07` |
| Upstream #353 citation | `NousResearch/hermes-agent` | `7a6c3b41c33a61601132c6bbf737735bd4a07207` |

Unit commits remain individually inspectable (no squash/amend/rebase):

| Unit | Review run | Disposition | Aether commit | Fork commit | Compatibility |
| --- | --- | --- | --- | --- | --- |
| HF-313 | `t_dcec38eb` run 4 approved | reproduced-and-fixed | `16389a995df43d35372d83bfd8e69664b9b2ead5` (evidence) | `2d89a331f6378f42fc26f7a439e8591101289ca6` | patch |
| HF-353 | `t_88ba2a9a` run 5 approved | reproduced-and-fixed | `9074358f3c96f848ece821ee973320c4c412f751` (evidence) | `8a23d40eb93319ff6ea94e27c68e5643cc6d8852` | patch |

## Independent integrated controls

Integrated candidate `cd27d426291c5b956310454ecf623e26774d014f` (contains both unit commits plus `AETHER_FORK.md`):

- Canonical `scripts/run_tests.sh` (10 files, `HERMES_TEST_FILE_RETRIES=0`): **202 passed, 0 failed, 5 skipped** in 5.9s. Windows-only skips on linux as documented.
- `git diff --check` clean vs `4b5772ff`.
- `python3 scripts/check-windows-footguns.py tools/code_execution_tool.py tools/file_tools.py hermes_cli/tips.py` — zero findings.
- Schema contains `from hermes_tools import json_parse, shell_quote, retry` and not `Built-in helpers (no import)`.
- CLI tip is exactly `execute_code helpers require explicit imports: from hermes_tools import json_parse, shell_quote, retry.`
- NameError hint: `Import shell_quote before calling it: from hermes_tools import shell_quote`.
- Helper ImportError hint prescribes the working import plus stale-module / sys.path / `reset=true`; does not say remove the import.
- Truncated `search_tool` `json.loads` succeeds; `_hint` contains `offset={offset+limit}`; raw has no `\n\n[Hint:` suffix.
- Non-truncated control has no `_hint`.
- ACP legacy trailing-hint fixture still reports matches and truncation.
- ACP structured `_hint` payload also reports matches and truncation.
- Imports of `tools.code_execution_tool` and `tools.file_tools` resolved to the integrated candidate, not the live editable runtime.
- Live editable runtime was not modified or reloaded.

`execute_code` one-shot approval prompt in a Supervisor-session probe is a live-runtime guard, not a suite failure. Helper import success is covered by `tests/tools/test_execute_helper_contract.py` and existing `test_code_execution.py` helper tests (included in the 202-pass suite).

## GitHub / release / residue

| Effect | Result |
| --- | --- |
| Fork PR | https://github.com/DarkArty07/aether-hermes/pull/3 **MERGED** as `6243e40ea6b06e85061bf3fedffaad43eed51dec` onto `aether-main` |
| Fork Actions | `actions/permissions.enabled=false`. Inherited workflows **NOT RUN**, not green. `aether-main` is not branch-protected. |
| Aether PR | https://github.com/DarkArty07/Aether-Agents/pull/358 **MERGED** as `be6bfea60aa32ef94dcc26d20806901c28ae0762` onto `main` |
| Required Aether checks | `pull-request-target`, `policy (3.11)`, `policy (3.12)`, `policy (3.13)` SUCCESS. No bypass. |
| Non-required Aether checks | `observation-qualification (3.12)` and `(3.13)` SUCCESS. `(3.11)` still IN_PROGRESS at merge; not a required gate. Do not absorb later flake as this objective. |
| Issues | #313 remained CLOSED/COMPLETED; merged-evidence comment added. #353 CLOSED/COMPLETED with merged-evidence comments. |
| Installed runtime | Unmodified and unreloaded. Live `tools/code_execution_tool.py` SHA-256 still `928d7bc88696ee5ee2ca84977ad4909f357aac376fd9312457adf13fe0eab88b`; live `tools/file_tools.py` still `18b40343d3fd890692762e8a434fa7e2e96b953766108a797b4af2caef01dd19`. |
| Remote merged-branch cleanup | Aether `delete_branch_on_merge=true` already removed the PR head. `git push --delete` of fork `fix/execute-code-helper-search-framing` was a genuine protected-edge denial; remote head remains. Local nested fork worktrees and local unit/integration branches removed after durable merge evidence. |
| Preserved residue | `morfeo/research-313-353` checkout and Aether research worktree; concurrent HLP-280/Graphify/runtime-reliability worktrees; live editable Hermes; kanban Aether unit worktrees `t_1e09bbc5`/`t_dcec38eb`/`t_88ba2a9a` (runtime-owned). |

Aggregate conclusions (compatibility evidence is patch; merge is not a release):

- `release_impact = patch`
- `release_action = defer`
- `release_channel = none`

No live activation, credentials, settings mutation, tags, package publication, or deployment.
