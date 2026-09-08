# Execute-code helper contract and search_files JSON framing — Supervisor task breakdown

**Status:** verified decomposition for Objective Contract `oc_fd2332ffe34aa5f7@v1`.

**Derived by:** Supervisor

**Source contract:** `.aether/objective-contracts/oc_fd2332ffe34aa5f7/v1.md`
(SHA-256 `6371b8f4900aa4266ffd1a9acd990d1072ecf5fbaf922fc065eee37828410515`)
on Aether base `419fddc67826b28ae39e22b446c38065542131db` (`origin/main`).

**Fork baseline:** `DarkArty07/aether-hermes` `aether-main`
`4b5772ff43de70f1222aabbf1daed4eefc7b44cf` (concurrent runtime-reliability merge).
Target-file parity at this SHA still matches the contract's inspected hashes:
`tools/code_execution_tool.py` `928d7bc88696ee5ee2ca84977ad4909f357aac376fd9312457adf13fe0eab88b`,
`tools/file_tools.py` `18b40343d3fd890692762e8a434fa7e2e96b953766108a797b4af2caef01dd19`.
The older inspected revision `c185ee3bb5b6d609241432fd123c16143f065987` is an ancestor;
do not implement on it. Implementation units add nested isolated worktrees from the
provisioned research checkout of that remote/SHA; they must not mutate `aether-main`
or `morfeo/research-313-353` in place.

**Owning issues:** [#313](https://github.com/DarkArty07/Aether-Agents/issues/313),
[#353](https://github.com/DarkArty07/Aether-Agents/issues/353).

This file is Supervisor-owned execution decomposition. It does not widen the
Objective Contract. Card bodies remain the executable unit deliveries.

## Receipt

| Check | Observed |
| --- | --- |
| Portable project | `.aether/project.toml` `project_id` equals envelope `12027989-a08f-41cd-a82c-54ff1bfb6b03` |
| Native project / board | envelope-bound; do not paste into child bodies |
| Contract bytes | SHA-256 matches the envelope |
| Aether HEAD / `origin/main` | `419fddc67826b28ae39e22b446c38065542131db` (concurrent OC already merged) |
| Fork identity | `DarkArty07/aether-hermes` `origin/aether-main` `4b5772ff43de70f1222aabbf1daed4eefc7b44cf`; target-file hashes match the contract; provisioned checkouts are read-only evidence until a unit-owned worktree is added from that SHA |
| Design sufficiency | #313 explicit-import contract and #353 producer `_hint` framing are decided, with upstream citations, preservation, dual-repo closeout, and stop conditions; no missing product API |
| Knowledge index | bound project matches; `available=false`; source inspection used; Graphify remains out of scope |
| Profiles | `implementer` and `supervisor` exist; no extra roles |
| Project Canonical Skills | none under `.aether/skills/`; Aether Canonical procedures apply |
| Issue #313 tracker | already `CLOSED` / `completed` with no comments and no merged patch; source still defective. Closeout reconciles evidence; do not skip the fix |
| Concurrent flow | `oc_5c2dad1b37b20a80@v1` finished; do not reuse or mutate its cards, worktrees, branches, processes, or board |

## Cross-artifact executability

| Concern | Settled conclusion | Execution consequence |
| --- | --- | --- |
| Dual repository | Maintained fork owns product fixes for #313 and #353. Aether owns `HERMES_LOCAL_PATCHES.md`, this `tasks.md`, evidence, issue closeout, and the Aether documentation PR | Never edit the live editable runtime. Never switch Project. Resolve the fork by remote/branch/SHA into an isolated worktree. Never mutate `aether-main` or a Morfeo research branch in place |
| Newer compatible bases | Contract assumed `origin/main` `8af2575` and `aether-main` `c185ee3`; both advanced. Aether is now `419fddc`. Fork tip is `4b5772ff` with unchanged target-file hashes | Implement from `4b5772ff` / `419fddc`. If either advances again with compatible unchanged target files, integrate. If target-file hashes diverge, stop and return to Supervisor |
| Two independent causes | #313 is schema/hint/import-contract. #353 is producer JSON framing. Keep attribution and regression evidence distinct | Two implementation units with exclusive writable files. Do not mix causes in one commit |
| Shared `tests/tools/test_code_execution.py` | Contract allows concentrating both issues if this file is shared. Owner steering requires two bounded units and independent causes | HF-313 owns `tests/tools/test_code_execution.py`. HF-353 puts the execute_code-bridge regression in a new focused test module. Concurrent edits to the same file are forbidden |
| `acp_adapter/tools.py` | Inspect and preserve. Change only if an acceptance test shows structured `_hint` breaks an existing public rendering invariant. Legacy trailing-hint input must remain renderable | Default: no ACP production edit. Existing ACP fixture with trailing hint is a preservation oracle |
| Ledgers | Concurrent edits to `HERMES_LOCAL_PATCHES.md` / `AETHER_FORK.md` are not independent | Implementation units do not edit either ledger. They supply the exact paragraph in the handoff. HF-INT applies both after independent review |
| Testing | Regression-first on the inspected fork behavior; canonical `scripts/run_tests.sh` list in the contract; `git diff --check`; Windows-footgun scan on production files must be zero findings | Identical new tests on unchanged `4b5772ff` (RED) and candidate (GREEN) for causal patches. Temporary trees and sanitized identities only |
| Publication / activation | Implementer commits locally and does not push/PR/merge/close issues | HF-INT owns dual-repo closeout. `release_action=defer`, `release_channel=none`. No runtime reload/activation |
| Out of scope | Helper injection, generic JSON parser, RPC redesign, sandbox redesign, Graphify, concurrent OC, credentials, settings, Hermes upgrade, vendoring upstream | Report incidental defects; do not absorb them |

Inspected current baseline (`origin/aether-main` `4b5772ff`, target files hash-identical to inspected `c185ee3`):

- `build_execute_code_schema()` advertises `Built-in helpers (no import): json_parse...`.
- `hermes_cli/tips.py` advertises `execute_code has built-in helpers: json_parse()...`.
- `_sandbox_failure_hint` tells NameError callers to call helpers without importing, and tells helper ImportError callers to remove the import.
- Helpers actually live in generated `hermes_tools.py` (`_COMMON_HELPERS`) and already work with `from hermes_tools import ...`.
- `search_tool` does `json.dumps(result_dict)` then appends `\n\n[Hint: Results truncated. Use offset=...]` when `truncated` is true.
- `tests/agent/test_file_safety_credentials.py` splits on `\n\n[Hint:` before `json.loads` and asserts the trailing hint substring.
- `acp_adapter/tools.py` `_json_loads_maybe` already `raw_decode`s a leading JSON value, so legacy trailing-hint fixtures still parse.

Upstream behavior to adapt (do not vendor or blindly cherry-pick; fork layout is older):

- #313: `NousResearch/hermes-agent@65f033a1a20e847b7a150fe6168cd345385c7d07` / PR `#83772`.
- #353: PR `#104472` / `NousResearch/hermes-agent@7a6c3b41c33a61601132c6bbf737735bd4a07207`.
- Rejected alternatives: PRs `#74100` and `#81622`.

## Requirement coverage

| Source | Unit | Notes |
| --- | --- | --- |
| AC-313-1, AC-313-2, AC-313-3 / #313 | HF-313 | Schema, CLI tip, import success, NameError hint, helper ImportError skew hint, UDS/file generated-module coverage |
| AC-353-1, AC-353-2, AC-353-3 / #353 | HF-353 | Single JSON document, `_hint` next offset, execute_code dict bridge, pagination/filter/`_warning`/`_omitted` preservation |
| AC-PRES-1 | HF-353 inspect; HF-INT verify | ACP rendering and legacy trailing-hint compatibility |
| AC-PRES-2 | every unit + HF-INT | execute_code limits, allowed tools, sandbox isolation, UDS/file/TCP framing, unrelated tools |
| AC-INTEGRATION-1, AC-AETHER-1, AC-CLOSE-1 | HF-INT | Dual-repo closeout, ledgers, issues, residue, non-activation |
| Preservation / authority | every unit + HF-INT | No concurrent-OC mutation, no Graphify, no activation, no credentials |

## Shared decisions (stamp into every implementation unit)

1. Authority is Objective Contract `oc_fd2332ffe34aa5f7@v1`. Skills grant no authority. Do not edit the canonical Objective Contract.
2. Aether evidence/docs start from `419fddc67826b28ae39e22b446c38065542131db` (`origin/main`). Fork product edits start from isolated worktrees of `DarkArty07/aether-hermes` at `4b5772ff43de70f1222aabbf1daed4eefc7b44cf`. Locate the provisioned fork by remote URL `https://github.com/DarkArty07/aether-hermes.git` and SHA `4b5772ff`. Cards remain Aether-project worktrees; each Implementer creates a nested isolated fork worktree from the provisioned research checkout of that remote/SHA (do not paste machine paths into public artifacts). Never copy or edit the live editable runtime. Never mutate a checkout whose current branch is `aether-main` or `morfeo/research-313-353` in place.
3. Before mutation, re-hash `tools/code_execution_tool.py` and `tools/file_tools.py` at the unit base. Required SHA-256 values are in Receipt. A mismatch is a stop condition: return to Supervisor; do not patch.
4. Do not modify Graphify, lockfiles, profiles, `home/`, credentials, providers, models, settings, or repository Actions. Do not absorb #267/#292/#294/#295/#301/#304 or mutate that flow.
5. Regression-first: add or adapt tests that fail on unchanged `4b5772ff`, then make them pass on the candidate. `HERMES_TEST_FILE_RETRIES=0`. Fork tests use `scripts/run_tests.sh` only. Confirm imports resolve to the candidate source before each run. Use temporary trees and sanitized disposable HOME/HERMES_HOME/task identities.
6. Public #313 strings (adapt to this fork's older `_sandbox_failure_hint` / `build_execute_code_schema` layout; do not inject helpers into globals/builtins):
   - Schema must require `from hermes_tools import json_parse, shell_quote, retry` and must not say the helpers are no-import globals. Follow upstream wording: `Helpers require imports: \`from hermes_tools import json_parse, shell_quote, retry\`.`
   - CLI tip becomes `execute_code helpers require explicit imports: from hermes_tools import json_parse, shell_quote, retry.`
   - NameError for a direct `shell_quote(...)` (and the other two helpers) remains an ordinary NameError; the hint is `Import {name} before calling it: from hermes_tools import {name}`.
   - Helper `ImportError: cannot import name '{name}' from 'hermes_tools'` reports stale/generated-module or sys.path skew and the working import; it must not tell the user to remove the import.
7. Public #353 framing:
   - If `result_dict.get("truncated")`, set `result_dict["_hint"]` to `Results truncated. Use offset={offset + limit} to see more, or narrow with a more specific pattern or file_glob.` then return one `json.dumps(result_dict, ensure_ascii=False)`.
   - Do not append a plain-text suffix. Do not make the UDS/file/TCP RPC parser tolerate arbitrary suffixes.
8. Writable-file ownership below is exclusive. Concurrent edits to the same file are forbidden.
9. Do not edit `AETHER_FORK.md` or `HERMES_LOCAL_PATCHES.md`. Put the exact ledger paragraph (issue, commit, evidence, scope, upstream relationship, rollback, retirement) in the unit handoff. HF-INT applies the ledgers.
10. Unit evidence path is unique: `specs/execute-code-helper-search-framing/evidence/<unit-id>.md` (and native task attachments for large logs). No secrets, operator paths, credentials, or private model responses.
11. Local judgement: private test helper names, equivalent reversible fixture structure, and whether to add a new focused test module versus extending an owned existing test file. Public result shape, hints, preservation gates, and issue attribution may not vary.
12. Return to Supervisor for a shared-file collision, a required `acp_adapter/tools.py` behavior change, target-file hash mismatch, concurrent-flow file overlap that would change public behavior, or any credential/settings/activation change.
13. Local commit on the unit branch; same-card Supervisor review; no push/PR/merge/issue close. Unit compatibility evidence is `patch`. Aggregate belongs to HF-INT: `release_impact=patch`, `release_action=defer`, `release_channel=none` unless evidence contradicts, in which case stop for Morfeo.
14. Canonical fork verification (minimum), after a sterile outer env that does not inherit live board/profile identity:

```bash
scripts/run_tests.sh tests/tools/test_code_execution.py tests/tools/test_code_execution_modes.py tests/tools/test_code_execution_windows_env.py tests/tools/test_sandbox_failure_hints.py tests/tools/test_file_tools.py tests/agent/test_file_safety_credentials.py tests/hermes_cli/test_tips.py tests/acp/test_tools.py
git diff --check
python3 scripts/check-windows-footguns.py tools/code_execution_tool.py tools/file_tools.py hermes_cli/tips.py
```

Add any new test modules to the runner invocation. Production-file Windows-footgun result must have zero findings. Contract inspected baseline for the four primary files was 105 passed, 0 failed, 2 Windows-only skipped, with eight pre-existing unrelated warnings that must not increase. Re-record the actual unchanged-`4b5772ff` counts before mutation.

## Execution graph

```text
t_1e09bbc5 (Supervisor decomposition root)
    → HF-313 t_dcec38eb execute_code helper import contract (Implementer, Aether worktree + nested fork worktree)
    → HF-353 t_88ba2a9a search_files truncated JSON framing (Implementer, Aether worktree + nested fork worktree)
    → same-card Supervisor review on each implementation unit
    → HF-INT t_9233a3ac terminal integration/closeout (Supervisor, same flow, terminal=true)
```

HF-313 and HF-353 are independent: different writable files, no invented shared interface, unique evidence paths. Same-card review is the unit review lane. HF-INT consumes independently reviewed units and does not replace unit review.

Necessary serialization is ledger/closeout only (HF-INT), not a false edge between the two implementation units.

## HF-313 — execute_code helper import contract

- Source: contract Owner Intent / Objective / AC-313-1..3 / AC-PRES-2; this unit.
- Outcome: schema and CLI tip state that `json_parse`, `shell_quote`, and `retry` require `from hermes_tools import ...` and neither says they are no-import globals. A sandbox script using that import executes each helper. Equivalent generated-module coverage passes for UDS and file transport. Direct `shell_quote(...)` without import remains NameError whose hint prescribes the working import. A true helper ImportError reports stale/generated-module or sys.path skew rather than telling the user to remove the import. Excludes search_files framing, ACP production edits, ledgers, push/PR, activation.
- Inputs: fork `4b5772ff43de70f1222aabbf1daed4eefc7b44cf` with verified target-file hashes. Immutable upstream citation `65f033a1a20e847b7a150fe6168cd345385c7d07` / PR `#83772`, using the older-layout test shape of that PR where appropriate. No prerequisite unit.
- Boundaries: writable fork `tools/code_execution_tool.py`, `hermes_cli/tips.py`, `tests/hermes_cli/test_tips.py`, `tests/tools/test_sandbox_failure_hints.py`, `tests/tools/test_code_execution.py`, and optional new `tests/tools/test_execute_helper_contract.py` (or equivalent owned name). Preserve `tools/file_tools.py`, `acp_adapter/tools.py`, `tests/tools/test_file_tools.py`, `tests/agent/test_file_safety_credentials.py`, `AETHER_FORK.md`.
- Judgement: how to structure UDS/file generated-module assertions; private test names; whether helper-contract tests live in the existing modules or the optional new file.
- Verification: fail-first schema/tip/NameError/ImportError tests on unchanged base. Candidate GREEN for those plus existing helper-import success tests. Run the canonical suite including new files; `git diff --check`; Windows-footgun scan on `tools/code_execution_tool.py` and `hermes_cli/tips.py` with zero findings. Do not claim Windows-only tests passed unless a required CI lane actually ran them.
- Dependencies: decomposition root only.
- Completion: local fork commit(s) attributable to #313 only; evidence `specs/execute-code-helper-search-framing/evidence/HF-313.md`; ledger paragraph in handoff; same-card review; unit compatibility `patch`; no push.

## HF-353 — search_files truncated JSON framing

- Source: contract Owner Intent / Objective / AC-353-1..3 / AC-PRES-1 / AC-PRES-2; this unit.
- Outcome: truncated and non-truncated `search_tool` output is one JSON document; `json.loads(raw)` succeeds; truncated output contains `_hint` with the correct next offset. The reproduced `search_files(pattern='*providers*', target='files', limit=15)` shape, or a deterministic temporary-tree equivalent, traverses `execute_code` and returns a dict without `JSONDecodeError`; a non-truncated control remains unchanged. Existing `total_count` / `truncated` / files-or-matches data, `_warning`, `_omitted`, credential/path filtering, and pagination remain intact; no secret-bearing test path becomes visible. ACP search rendering still reports matches and truncation and remains compatible with legacy trailing-hint input. Excludes helper-schema/hint work, ledgers, push/PR, activation, generic parser tolerance.
- Inputs: fork `4b5772ff43de70f1222aabbf1daed4eefc7b44cf` with verified target-file hashes. Immutable upstream citation PR `#104472` / `7a6c3b41c33a61601132c6bbf737735bd4a07207`, adapted to this fork. No prerequisite unit.
- Boundaries: writable fork `tools/file_tools.py` (`search_tool` truncation path only), `tests/tools/test_file_tools.py`, `tests/agent/test_file_safety_credentials.py`, and a new focused execute_code-bridge module (preferred name `tests/tools/test_search_truncation_json.py`). Do not edit `tests/tools/test_code_execution.py` (HF-313 exclusive). Inspect `acp_adapter/tools.py` and `tests/acp/test_tools.py`; preserve them unless a new acceptance test proves structured `_hint` breaks public rendering, in which case return to Supervisor rather than silently redesigning ACP. Preserve `tools/code_execution_tool.py`, `hermes_cli/tips.py`, `AETHER_FORK.md`.
- Judgement: temporary-tree fixture for the providers-shape reproduction; how to update credential-filter tests so they `json.loads` the whole document and still hide secret paths.
- Verification: fail-first `json.loads` of truncated output on unchanged base (expect `JSONDecodeError` or trailing-suffix assertions). Candidate: `json.loads` succeeds, `_hint` has `offset={offset+limit}`, non-truncated control has no new suffix and existing fields intact, execute_code bridge returns a dict, credential test still omits secret paths and no longer requires a trailing `[Hint:` substring. Run the canonical suite including the new module; `git diff --check`; Windows-footgun scan on `tools/file_tools.py` with zero findings.
- Dependencies: decomposition root only.
- Completion: local fork commit(s) attributable to #353 only; evidence `specs/execute-code-helper-search-framing/evidence/HF-353.md`; ledger paragraph in handoff; same-card review; unit compatibility `patch`; no push.

## HF-INT — Terminal integration and dual-repo closeout

- Source: AC-INTEGRATION-1, AC-AETHER-1, AC-CLOSE-1, AC-PRES-1, AC-PRES-2, deliverables 4–6; this unit.
- Outcome: independently reviewed HF-313 and HF-353 commits integrated without squash/amend/rebase/force; latest compatible `origin/aether-main` and `origin/main` rechecked; fork PR to `aether-main` and Aether PR to `main`; required Aether checks green; fork Actions reported NOT RUN rather than green; issues reconciled with merged evidence (including #313 already closed without a patch); ledgers written with distinct non-destructive #313/#353 records and concurrent runtime-reliability entries preserved; residue audit limited to this objective; aggregate release conclusions. No live activation, reload, reinstall, or publication.
- Inputs: independently reviewed HF-313 and HF-353 commits plus this `tasks.md`. Preserve each unit as its own commit.
- Boundaries: integration-owned conflict/import/wiring/path repairs that introduce no new behavior; `HERMES_LOCAL_PATCHES.md`; fork `AETHER_FORK.md`; `specs/execute-code-helper-search-framing/evidence/` integrated report. Behavior gaps return as implementation rework.
- Verification: canonical suite on the integrated fork candidate; Windows-footgun zero findings on the three production files; Aether documentation/policy gates as applicable; git-github-closeout in both repositories; independent re-check of helper import contract, truncated JSON parse through execute_code, credential filtering, and ACP legacy trailing-hint rendering. Installed runtime remains unmodified/unreloaded.
- Dependencies: decomposition root and both independently reviewed implementation units.
- Completion: aggregate `release_impact=patch` only with compatibility evidence, `release_action=defer`, `release_channel=none`. Local integration alone is not success.

## Authority and stop conditions

Follow the Objective Contract. Ordinary Supervisor/Implementer execution and routine Git/GitHub closeout in the two named repositories are authorized. Stop and return `needs-contract-revision` only for a genuine contract defect (target-file hash mismatch that invalidates the approved design, required helper-global injection, generic parser tolerance, guard/sandbox/RPC redesign, or concurrent-flow mutation). Stop and return `needs-owner-input` only for genuine owner input. Protected denials are authoritative. Do not strand a finished phase awaiting a precreated review child; unit review is same-card. Preserve unrelated/pre-existing worktrees, branches, stashes, and processes.
