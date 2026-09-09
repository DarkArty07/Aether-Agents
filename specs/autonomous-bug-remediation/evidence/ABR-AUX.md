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
| Supervisor breakdown source | `specs/autonomous-bug-remediation/tasks.md` at `5834212cfe8d6cb96325ab9d97671a637eef71c0` (inspected from the Supervisor branch) |
| Contract digest | Rechecked from `.aether/objective-contracts/oc_ddebf175a40251f7/v1.md`; matched the assigned digest |
| Maintained fork baseline | `DarkArty07/aether-hermes` `aether-main` at `28b593efa86bbc674b32f488c35932a4e7e85a51` |
| Fork candidate | Local commit `b1e3ca80a9a79cf8e0482d6621d329c7ae88e236` on `wt/t_57e549db` |
| Imported source check | `import agent.auxiliary_client` resolved to the candidate fork's `agent/auxiliary_client.py` |
| Runtime | Python 3.11.15; OpenAI SDK 2.24.0; pytest 9.1.1; already-provisioned test environment |
| Candidate tree | Clean after the fork commit; no push, PR, merge, issue mutation or publication |

The selected Hermes public release source `NousResearch/hermes-agent@e624e9fde561e1add9388384012b295fde669ade` was inspected before adapting the fork. Its auxiliary Responses adapter includes the existing request-header forwarding behavior used by #301, but does not negotiate a clear Chat-only surface directive or preserve configured fallback attribution query metadata. No dependency upgrade or new provider/protocol was introduced. Tracked Aether profile YAML, live `home/` state, `model_metadata.py`, and `error_classifier.py` were not modified.

## 2. Implementation

### #296 — Chat-only auxiliary negotiation

`agent/auxiliary_client.py:_CodexCompletionsAdapter.create` now recognizes only a clear HTTP 400 Chat Completions directive (the directive's `/chat/completions`, `Chat Completions surface`, or `Chat Completions only` wording). It retries through the already-supported raw `client.chat.completions.create()` path, filters private Hermes-only kwargs, removes non-streaming-only `stream_options`, and aggregates an explicitly streamed Chat response to retain the adapter's completed-response shape. Other errors still raise through the existing recovery path, and Responses-native success does not issue a Chat request.

### #303 — fallback attribution and auth separation

`_FallbackDestination` carries request-scoped `extra_query` values extracted from only the configured `aether_service` and `aether_operation` query keys. Synchronous and asynchronous fallback calls, including credential-refresh retries, forward a fresh copy to the SDK/Responses adapter. Existing fallback `extra_headers` filtering remains in force; it excludes Authorization, Proxy-Authorization, Cookie, and API-key/provider-token header forms, while destination authentication is supplied by the fallback client.

Relevant candidate locations:

- `agent/auxiliary_client.py:1450` — directive classifier.
- `agent/auxiliary_client.py:1543-1548` — request query forwarding into Responses requests.
- `agent/auxiliary_client.py:1789-1851` — Chat fallback and response-shape preservation.
- `agent/auxiliary_client.py:4989-5053` — bounded fallback attribution query extraction.
- `agent/auxiliary_client.py:5212-5382` — sync/async fallback and refresh retry propagation.
- `tests/agent/test_auxiliary_client_chat_and_attribution.py` — loopback controls and regressions.

## 3. Baseline versus candidate

The identical new regression file was copied into a disposable fork worktree at the exact baseline and candidate was run from the committed fork tree. Both runs used the fork's canonical runner with retries disabled:

`HERMES_TEST_FILE_RETRIES=0 scripts/run_tests.sh tests/agent/test_auxiliary_client_chat_and_attribution.py`

| Revision | Result | Meaning |
| --- | --- | --- |
| Baseline `28b593e` | **1 passed, 4 failed** | Chat-only sync/async requests raised the directive; direct and genuine title fallback lost the configured attribution query. The Responses-only control passed. |
| Candidate `b1e3ca8` | **5 passed, 0 failed** | Chat-only requests reached Chat Completions after the directive; Responses-only remained on Responses; direct and genuine title fallback carried attribution. |

The candidate loopback tests use no live model or paid endpoint. The genuine fallback test runs `call_llm(task="title_generation")` against a local HTTP server, returns a synthetic primary 429, and observes the configured fallback request.

## 4. Acceptance coverage

| Obligation | Check and observed result | Evidence |
| --- | --- | --- |
| #296 normal Chat-only auxiliary | Loopback HTTP 400 directive followed by HTTP 200 Chat response; sync and async tests passed. | `test_chat_only_directive_retries_existing_chat_path`; `test_async_chat_only_directive_uses_same_compatible_path` |
| #296 Responses behavior preserved | Responses-only loopback returned successfully with exactly one `/v1/responses` request and no Chat retry. | `test_responses_native_model_keeps_responses_path_only` |
| #303 configured fallback attribution | Direct fallback seam and full primary-rate-limit → configured-fallback `call_llm` path observed `aether_service=morfeo` and `aether_operation=title_generation` on the fallback request. | `test_title_fallback_preserves_attribution_without_primary_auth`; `test_genuine_title_generation_fallback_uses_entry_attribution` |
| #303 destination/auth separation | Fallback HTTP request carried the synthetic fallback client's bearer credential and safe trace header, while primary Authorization, Proxy-Authorization, Cookie and API-key headers were absent. | The two #303 loopback tests above; existing `test_auxiliary_client_extra_headers.py` controls |
| Query preservation | An existing destination `api-version` query was retained alongside the two attribution values; request query order was not assumed. | `test_title_fallback_preserves_attribution_without_primary_auth` |
| Existing auxiliary compatibility | 24 auxiliary-focused files, 359 tests, 0 failures. | Canonical fork runner output below |

## 5. Verification record

All commands below were run against the candidate fork unless marked baseline.

1. **Focused baseline reproduction:** canonical fork runner on the identical five-test file at `28b593e`: **1 passed, 4 failed** (exit 1). Failures were the two Chat-only surface tests and both #303 attribution tests; the Responses-only control passed.
2. **Focused candidate:** `HERMES_TEST_FILE_RETRIES=0 scripts/run_tests.sh tests/agent/test_auxiliary_client_chat_and_attribution.py`: **5 passed, 0 failed** (exit 0).
3. **Required auxiliary suite:** `HERMES_TEST_FILE_RETRIES=0 scripts/run_tests.sh` over the 24 owned auxiliary test files (`test_auxiliary_client*.py`, auxiliary fallback/config/transport/concurrency/streaming controls and `test_minimax_auxiliary_url.py`): **359 passed, 0 failed** (exit 0).
4. **Candidate import:** `python -c 'import agent.auxiliary_client as m; print(m.__file__)'`: resolved to the candidate fork source.
5. **Static checks:** `python -m compileall -q agent/auxiliary_client.py tests/agent/test_auxiliary_client_chat_and_attribution.py`, candidate Ruff check on both touched Python files, and `git diff --check`: all **exit 0**. `git show --check b1e3ca80a9...`: **exit 0**.
6. **Broader context check:** the canonical `tests/agent` run at the candidate reached **4552 passed, 27 skipped**. It exited nonzero because the unrelated/excluded `tests/agent/test_model_metadata.py` process exceeded the runner's 300-second per-file cap after partial progress; `model_metadata.py` is outside this unit and unchanged. No other `tests/agent` file failed.
7. **Issue state:** read-only GitHub checks with `-R DarkArty07/Aether-Agents` observed #296 and #303 **OPEN**. This unit did not close or mutate issues.
8. **Knowledge tools:** `project_knowledge` status reported `available=false` with empty coverage; source inspection and executable tests were used. `work_memory` search returned no matching prior note. No graph or memory update was fabricated.

The fork's `ruff format --check` reports pre-existing formatting differences throughout the large baseline `agent/auxiliary_client.py`; the touched test file is formatted. No formatter-wide rewrite was applied to this hotspot.

## 6. Distinct dispositions and compatibility

- **#296:** reproduced-and-fixed. This is a compatible patch to the existing Responses adapter: a clear model-surface directive selects the already-existing Chat Completions client path; Responses success and all non-directive failures retain existing behavior.
- **#303:** reproduced-and-fixed. Configured fallback attribution is made request-scoped and bounded; destination authentication is not copied from the primary request. No profile activation, live configuration edit, new provider, or protocol was added.
- **Unit compatibility:** `patch`. Aggregate release and publication decisions remain with Supervisor.

### Ledger paragraph for ABR-INT (not applied here)

> Issues #296/#303 — reproduced-and-fixed in maintained-fork commit `b1e3ca80a9a79cf8e0482d6621d329c7ae88e236`; evidence `specs/autonomous-bug-remediation/evidence/ABR-AUX.md`; scope `agent/auxiliary_client.py` plus `tests/agent/test_auxiliary_client_chat_and_attribution.py`; narrow downstream compatibility correction on maintained baseline `28b593efa86bbc674b32f488c35932a4e7e85a51`, with no new provider/protocol and no live profile edits; rollback is reverting the fork commit; retire when an adopted exact Hermes release provides equivalent per-model Chat/Responses negotiation and preserves configured fallback attribution query metadata with the same boundary tests.

## 7. Publication and remaining risk

No remote or irreversible action was taken: no push, PR, merge, issue close, release, package publication, credential acquisition, live profile mutation, or paid model request. The unit branch has no upstream publication target.

The remaining qualification limit is that attribution was proven on a controlled loopback HTTP seam and through the real Hermes `call_llm` fallback path, not against the live paid router/profile. Live activation is explicitly outside this unit and remains a separate Supervisor-owned gate. The unrelated model-metadata timeout remains visible and unmodified.
