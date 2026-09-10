# Unit Evidence: ABR-AUX — Chat-only auxiliaries and title-fallback attribution

- **Unit:** ABR-AUX
- **Card:** `t_57e549db`
- **Issues:** [#296](https://github.com/DarkArty07/Aether-Agents/issues/296), [#303](https://github.com/DarkArty07/Aether-Agents/issues/303)
- **Objective Contract:** `oc_ddebf175a40251f7@v1`
- **Contract SHA-256:** `722100569399ac7b61e15bccdcba28fd5fafe1585e4a1f7fbbe3bf5dcf0aa4e8`
- **Review lane:** same-card Supervisor review (`reviewer="supervisor"`)
- **Unit compatibility impact:** `patch`

## 1. Source identity and boundary

| Item | Observed |
| --- | --- |
| Aether starting revision | `b52afd17a93d25e31a48e5c86bd569f45f2f04d4` |
| Supervisor breakdown source | `specs/autonomous-bug-remediation/tasks.md` at `5834212cfe8d6cb96325ab9d97671a637eef71c0` |
| Contract digest | Rechecked from `.aether/objective-contracts/oc_ddebf175a40251f7/v1.md`; matched the assigned digest |
| Maintained fork baseline | `DarkArty07/aether-hermes` `aether-main` at `28b593efa86bbc674b32f488c35932a4e7e85a51` |
| Code correction commits | `b1e3ca80a9a79cf8e0482d6621d329c7ae88e236`, `7b75f6e83f06badc09e73c87cba78f484d2625fd` |
| Test-environment correction commits | `a134c9c4f4d4963c811a30bad72e4be6ae67254a`, `1ccfb08b8bb86c215c09bc8ee3e45f7c290ae6fc` |
| Fork candidate HEAD | `7b75f6e83f06badc09e73c87cba78f484d2625fd` on `wt/t_57e549db` |
| Imported source check | `import agent.auxiliary_client` resolved to the candidate fork's `agent/auxiliary_client.py` |
| Runtime | Python 3.11.15; OpenAI SDK 2.24.0; pytest 9.1.1; pytest-asyncio 1.3.0; Anthropic SDK 0.87.0 |
| Candidate tree | Clean after the final fork commit; no push, PR, merge, issue mutation or publication |

The Supervisor breakdown identifies #296 and #303 as the concentrated `agent/auxiliary_client.py` hotspot and requires distinct dispositions. The selected Hermes public release source `NousResearch/hermes-agent@e624e9fde561e1add9388384012b295fde669ade` was inspected before adapting the fork: its auxiliary Responses adapter has request-header forwarding but no Chat-only directive negotiation and no request-scoped `extra_query` fallback attribution. No dependency upgrade or new provider/protocol was introduced. Tracked Aether profile YAML, live `home/` state, `model_metadata.py`, and `error_classifier.py` were not modified.

## 2. Implementation

### #296 — Chat-only auxiliary negotiation

`agent/auxiliary_client.py:_CodexCompletionsAdapter.create` now recognizes only a clear HTTP 400 Chat Completions directive (the directive's `/chat/completions`, `Chat Completions surface`, or `Chat Completions only` wording). A missing, non-400, or unrelated error is re-raised without issuing a second Chat request. A qualifying 400 retries through the already-supported raw `client.chat.completions.create()` path, filters private Hermes-only kwargs, removes non-streaming-only `stream_options`, and aggregates an explicitly streamed Chat response to retain the adapter's completed-response shape. Responses-native success does not issue a Chat request.

### #303 — fallback attribution and auth separation

`_FallbackDestination` carries request-scoped `extra_query` values extracted from only the configured `aether_service` and `aether_operation` query keys. Synchronous and asynchronous fallback calls, including credential-refresh retries, forward a fresh copy to the SDK/Responses adapter. Existing fallback `extra_headers` filtering remains in force; it excludes Authorization, Proxy-Authorization, Cookie, and API-key/provider-token header forms, while destination authentication is supplied by the fallback client.

Relevant candidate locations:

- `agent/auxiliary_client.py:1450` — directive classifier.
- `agent/auxiliary_client.py:1543-1548` — request query forwarding into Responses requests.
- `agent/auxiliary_client.py:1812-1851` — Chat fallback and response-shape preservation.
- `agent/auxiliary_client.py:4989-5053` — bounded fallback attribution query extraction.
- `agent/auxiliary_client.py:5212-5382` — sync/async fallback and refresh retry propagation.
- `tests/agent/test_auxiliary_client_chat_and_attribution.py` — loopback controls and regressions.

The test-only follow-up replaced a `pytest.mark.asyncio` test with the repository's established `asyncio.run()` bridge because the canonical runner's initially selected venv lacked pytest-asyncio. The final test file is formatted; no production behavior changed in those follow-up commits.

## 3. Baseline versus candidate

The identical final regression file was copied into a disposable fork worktree at the exact baseline and the committed candidate was run with the fork's canonical runner and retries disabled:

`HERMES_TEST_FILE_RETRIES=0 scripts/run_tests.sh tests/agent/test_auxiliary_client_chat_and_attribution.py`

| Revision | Result | Meaning |
| --- | --- | --- |
| Baseline `28b593e` | **4 passed, 4 failed** | The three negative boundary controls and Responses-only control passed; Chat-only sync/async requests raised the directive, and direct and genuine title fallback lost the configured attribution query. |
| Candidate `7b75f6e83f06badc09e73c87cba78f484d2625fd` | **8 passed, 0 failed** | Chat-only requests reached Chat Completions after the verified 400 directive; Responses-only remained on Responses; direct and genuine title fallback carried attribution; 400-unrelated, non-400 directive, and statusless directive-like errors re-raised without a Chat request. |

The candidate loopback tests use no live model or paid endpoint. The genuine fallback test runs `call_llm(task="title_generation")` against a local HTTP server, returns a synthetic primary 429, and observes the configured fallback request.

## 4. Acceptance coverage

| Obligation | Check and observed result | Evidence |
| --- | --- | --- |
| #296 normal Chat-only auxiliary | Loopback HTTP 400 directive followed by HTTP 200 Chat response; sync and async tests passed. | `test_chat_only_directive_retries_existing_chat_path`; `test_async_chat_only_directive_uses_same_compatible_path` |
| #296 negative boundary | HTTP 400 without directive wording, non-400 directive-like errors, and statusless directive-like errors were re-raised; no Chat request was recorded. | `test_non_400_or_unrelated_directives_are_reraised_without_chat_request` (3 parameter cases) |
| #296 Responses behavior preserved | Responses-only loopback returned successfully with exactly one `/v1/responses` request and no Chat retry. | `test_responses_native_model_keeps_responses_path_only` |
| #303 configured fallback attribution | Direct fallback seam and full primary-rate-limit → configured-fallback `call_llm` path observed `aether_service=morfeo` and `aether_operation=title_generation` on the fallback request. | `test_title_fallback_preserves_attribution_without_primary_auth`; `test_genuine_title_generation_fallback_uses_entry_attribution` |
| #303 destination/auth separation | Fallback HTTP request carried the synthetic fallback client's bearer credential and safe trace header, while primary Authorization, Proxy-Authorization, Cookie and API-key headers were absent. | The two #303 loopback tests above; existing `test_auxiliary_client_extra_headers.py` controls |
| Query preservation | An existing destination `api-version` query was retained alongside the two attribution values; request query order was not assumed. | `test_title_fallback_preserves_attribution_without_primary_auth` |
| Existing auxiliary compatibility | 25 auxiliary-focused files, 374 tests, 0 failures. | Final canonical fork runner output below |

## 5. Verification record

All commands below were run against the final candidate fork unless marked baseline or historical prior-candidate. The focused correction run used the already-provisioned Hermes development environment; the final 25-file suite used a frozen local `uv` environment with the repository's `dev` and `anthropic` extras. No source dependency change was made.

1. **Focused baseline reproduction:** canonical fork runner on the identical eight-outcome regression file at `28b593e`: **4 passed, 4 failed** (exit 1). The three negative boundary controls and Responses-only control passed; failures were the two Chat-only surface tests and both #303 attribution tests.
2. **Focused candidate:** `HERMES_TEST_FILE_RETRIES=0 scripts/run_tests.sh tests/agent/test_auxiliary_client_chat_and_attribution.py`: **8 passed, 0 failed** (exit 0), including the three negative boundary parameter cases.
3. **Required auxiliary suite:** `HERMES_TEST_FILE_RETRIES=0 scripts/run_tests.sh` over the 25 files selected by `tests/agent/test_auxiliary*.py` plus `tests/agent/test_minimax_auxiliary_url.py`: **374 passed, 0 failed** (exit 0).
4. **Candidate import:** `python -c 'import agent.auxiliary_client as m; print(m.__file__)'`: resolved to the candidate fork source.
5. **Static checks:** `python -m compileall -q agent/auxiliary_client.py tests/agent/test_auxiliary_client_chat_and_attribution.py`, Ruff check on both touched Python files, `ruff format --check tests/agent/test_auxiliary_client_chat_and_attribution.py`, `git diff --check 28b593e..HEAD`, and `git show --check` for the final commits: all **exit 0**. Full two-file `ruff format --check` still reports pre-existing formatting differences throughout the large baseline `agent/auxiliary_client.py`; no formatter-wide rewrite was applied to this hotspot.
6. **Broader context check (historical prior candidate):** the canonical `tests/agent` run at candidate `1ccfb08` reached **4552 passed, 27 skipped** and exited nonzero only because the unrelated `tests/agent/test_model_metadata.py` process exceeded the runner's 300-second per-file cap after partial progress. The final candidate's required 25-file auxiliary suite passed; `model_metadata.py` is outside this unit and unchanged.
7. **Issue state:** read-only GitHub checks observed #296 and #303 **OPEN**. This unit did not close or mutate issues.
8. **Knowledge tools:** `project_knowledge` status reported `available=false` with empty coverage at source revision `77741465385deca65340b6f0008f69388e130578`; source inspection and executable tests were used. `work_memory` search returned no matching prior note. No graph or memory update was fabricated.

## 6. Distinct dispositions and compatibility

- **#296:** reproduced-and-fixed. This is a compatible patch to the existing Responses adapter: only a clear HTTP 400 model-surface directive selects the already-existing Chat Completions client path; Responses success and all non-directive, non-400, or statusless failures retain existing behavior.
- **#303:** reproduced-and-fixed. Configured fallback attribution is made request-scoped and bounded; destination authentication is not copied from the primary request. No profile activation, live configuration edit, new provider, or protocol was added.
- **Unit compatibility:** `patch`. Aggregate release and publication decisions remain with Supervisor.

### Ledger paragraph for ABR-INT handoff (not applied here)

> Issues #296/#303 — reproduced-and-fixed in maintained-fork commits `b1e3ca80a9a79cf8e0482d6621d329c7ae88e236`, `a134c9c4f4d4963c811a30bad72e4be6ae67254a`, `1ccfb08b8bb86c215c09bc8ee3e45f7c290ae6fc`, and `7b75f6e83f06badc09e73c87cba78f484d2625fd`; evidence `specs/autonomous-bug-remediation/evidence/ABR-AUX.md`; scope `agent/auxiliary_client.py` plus `tests/agent/test_auxiliary_client_chat_and_attribution.py`; narrow downstream compatibility correction on maintained baseline `28b593efa86bbc674b32f488c35932a4e7e85a51`, with no new provider/protocol and no live profile edits; rollback is reverting the four fork commits; retire when an adopted exact Hermes release provides equivalent per-model Chat/Responses negotiation and preserves configured fallback attribution query metadata with the same boundary tests.

## 7. Publication and remaining risk

No remote or irreversible action was taken: no push, PR, merge, issue close, release, package publication, credential acquisition, live profile mutation, or paid model request. The Aether evidence commit and maintained-fork commits are local unit work only; the unit has no upstream publication target.

The remaining qualification limit is that attribution was proven on a controlled loopback HTTP seam and through the real Hermes `call_llm` fallback path, not against the live paid router/profile. Live activation is explicitly outside this unit and remains a separate Supervisor-owned gate. The unrelated model-metadata timeout remains visible and unmodified.
