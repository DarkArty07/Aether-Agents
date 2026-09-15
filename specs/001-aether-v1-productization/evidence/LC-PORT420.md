# LC-PORT420 — HLP-420 responses terminal fidelity landed as fork source

**Unit:** LC-PORT420 (implementer), card `t_56d86e11`.
**Authority:** Objective Contract `oc_3397f9f05d780f8e@v1`
(SHA-256 `4d4c7650bf8ea93fc7cffe3d87f7f974e172d66cefcf6a74a2d83051568a4879`) on
Aether base `410c172ae69ffa87f6e32960ae4aef3b8d6598f0`, plus the Supervisor
breakdown at `specs/001-aether-v1-productization/tasks.md` (commit
`61124bc1dea787fbc5408fcc7f7b4f654f342e78`) and its shared decisions 1–15.
`HERMES_LOCAL_PATCHES.md` §"HLP-420 — auxiliary Responses terminal and phase
fidelity" and `specs/001-aether-v1-productization/evidence/hermes-patch-reconciliation/entries/HLP-420.json`
are the authoritative local-semantics and record inputs. No canonical artifact
was edited.

**Result:** HLP-420's behavior now exists as ordinary reviewed source on
maintained-fork branch `fix/420-responses-terminal-fidelity` at revision
`70569d1025b64cb98114e78840cef83baf1fc9d2` (parent `54eeb56dabefc98821d696656ed58c55dd777346`),
together with its focused regression module
`tests/agent/test_auxiliary_client_responses_terminal_420.py`. The ported source
is byte-identical to the reviewed HLP-420 candidate recorded in
`patches/hermes/HLP-420-responses-terminal-fidelity.patch`: both recorded
content SHA-256 values and both recorded blob ids reproduce exactly. Local
commits only — nothing was pushed, opened as a pull request, merged, tagged,
released, published, restarted, activated or pointed at the live runtime.

## 1. Starting point and receipt

| Check | Observed |
| --- | --- |
| Fork resolved by remote URL | `origin` = `https://github.com/DarkArty07/aether-hermes` (provisioned checkout `/home/darkarty/Desktop/03_PROYECTOS/01_ACTIVOS/aether-hermes`) |
| Provisioned revision | `aether-main` = `54eeb56dabefc98821d696656ed58c55dd777346`, working tree clean before and after this unit; `rev-parse aether-main` unchanged at the end |
| Port isolation | nested worktree `<fork>/.worktrees/lc-port420` on branch `fix/420-responses-terminal-fidelity`, created from that checkout at `54eeb56dab`; the checkout whose branch is `aether-main` was never checked out, staged or committed |
| Base prerequisite absent | at `54eeb56dab` `agent/auxiliary_client.py` carried **0** occurrences of `AuxiliaryResponsesTerminalError` and **0** of `incomplete_details`, and the regression module did not exist — the port target was genuinely missing, matching the card's measurement |
| Ported revision | `agent/auxiliary_client.py` now carries **2** / **10** occurrences respectively; `git diff --name-only 54eeb56dab..70569d1025` lists exactly the two writable files |
| Aether side | this unit's Aether worktree (`aether-agents-2/t_56d86e11-…`); the only Aether file written is this record |
| Live runtime / editable state | not read, copied, modified or activated; no service, board, profile or installation action |
| Recorded inputs re-verified | patch SHA-256 `e0caa198c9c61e1235cedbc021c6e1a4d35b114c9c155df3fe1515040c420fa6`; test module content SHA-256 `1c8a21d09950a7bef2fbbac3b03073970f23e3eab32fd15e6e2f12cc4a1434e6`; base file content SHA-256 `93275ed4d6c5d7a84b8607b3f0fcbad998bfdd2f52f6e2516372de66ca6b7ec0` |

Test environment: the fork worktree's `.venv` (Python 3.11.15, pytest 9.1.1,
ruff 0.15.10) driven through `scripts/run_tests.sh` as the fork's own guidance
requires. `anthropic` is not installed in that environment (the known
environment-driven class, see §4); no dependency was installed and no network
call was made by this unit.

## 2. Method: source port, and a corrected replay premise

The card directed a source port because it believed the patch could not be
replayed. Real inspection shows the premise was a hash-type conflation, not a
content difference:

| Fact | Measured value |
| --- | --- |
| Patch `index` line | `index 93b185c9eb..e71d241ed7 100644` |
| `agent/auxiliary_client.py` blob at `54eeb56dab` | `93b185c9ebeed872703c038799af763dbbc13e80` — **equals the patch preimage blob** |
| `git log 3b81e9d91c..54eeb56dab -- agent/auxiliary_client.py` | empty — the file did not change between the patch's recorded base and the candidate tip |
| Recorded "preimage SHA-256" `93275ed4…` | the file's raw-content SHA-256 (measured `sha256sum` at `54eeb56dab`), not a blob id |

So a byte-exact replay of the HLP-420 hunks was available; the two recorded
values describe the same bytes under different hash functions. The card
explicitly required a source port and forbade applying `patches/hermes/**`, so
that is what this unit did: the 15 recorded hunks were ported onto the current
file as source edits (**+219 / −13**), with no other region touched. Because the
base file is byte-identical to the patch preimage, the two methods are provably
equivalent, and the port's outcome reproduces the reviewed candidate exactly:

| Identity | Reviewed candidate (recorded) | Ported result (measured at `70569d1025`) |
| --- | --- | --- |
| `agent/auxiliary_client.py` content SHA-256 | `2c5dfee035dd47a8bb8f2e652983f53f3ebc3b90c06adc87176f4cbf3adc0a30` | `2c5dfee035dd47a8bb8f2e652983f53f3ebc3b90c06adc87176f4cbf3adc0a30` |
| `agent/auxiliary_client.py` blob id | `e71d241ed7` (patch postimage) | `e71d241ed720648b285c63e12ceabd68fbeb3110` |
| Regression module content SHA-256 | `1c8a21d09950a7bef2fbbac3b03073970f23e3eab32fd15e6e2f12cc4a1434e6` | `1c8a21d09950a7bef2fbbac3b03073970f23e3eab32fd15e6e2f12cc4a1434e6` |
| Regression module blob id | `b347d8577d` (patch postimage) | `b347d8577dfd6f4740158c8412000a935f8b246f` |

Diff-footprint check: `git diff -U0` against `54eeb56dab` expands to 22 atomic
sub-hunks whose preimage line numbers and enclosing function contexts
(`_is_chat_completions_directive`, `_CodexCompletionsAdapter`,
`_retry_same_provider_sync`, `_build_call_kwargs`, `call_llm`, `_call_llm_impl`)
correspond one-to-one with the patch's 15 hunks. The `#301`/`#303`/`#296`
extra-headers and Chat-directive behavior in the same file is therefore
preserved unchanged, as required.

No action is needed from this correction for LC-PORT420's deliverable; it only
means the ledger sentence "the patch does not apply as a replay" should be
corrected if a future unit reasons about replayability (the practical
consequence is confined to LC-FORK/LC-INT method choice).

## 3. Verification — raw measurements

| Check | Command | Observed |
| --- | --- | --- |
| Causal RED on the unchanged candidate | `scripts/run_tests.sh tests/agent/test_auxiliary_client_responses_terminal_420.py -q` before any edit | `20 failed, 5 passed in 0.62s` — exactly the recorded RED |
| Acceptance case, isolated | same file `-k test_incomplete_max_output_tokens_is_length_not_stop` | `assert 'stop' == 'length'` (diff `- length` / `+ stop`), `1 failed, 24 deselected` |
| GREEN, focused module after the port | `scripts/run_tests.sh tests/agent/test_auxiliary_client_responses_terminal_420.py -q` | `=== Summary: 1 files, 25 tests passed, 0 failed (100% complete) in 1.0s (24 workers) ===` |
| Existing auxiliary-client suite, candidate | `scripts/run_tests.sh tests/agent/test_auxiliary_client.py -q` | `=== Summary: 1 files, 181 tests passed, 0 failed (100% complete) in 8.8s (24 workers) ===` |
| Existing auxiliary-client suite, base | same file in a detached `54eeb56dab` worktree | `181✓` inside the base selection run (§4) — identical to the candidate |
| `ruff check` | `.venv/bin/ruff check agent/auxiliary_client.py` | `All checks passed!` (exit 0) |
| Whitespace | `git diff --check` | clean (exit 0) |
| Module origin | `.venv/bin/python -c "import agent.auxiliary_client as m; print(m.__file__)"` from the port worktree | `<fork>/.worktrees/lc-port420/agent/auxiliary_client.py` — the candidate, not the live tree |
| Ported symbols reachable | `inspect.signature` on the imported module | `AuxiliaryResponsesTerminalError`, `_responses_tool_choice_shape` present; `tool_choice` present on `call_llm`, `_build_call_kwargs`, `_retry_same_provider_sync`; **absent on `_retry_same_provider_async`** (route default preserved) |

`ruff format --check` still reports the file's pre-existing drift and was
deliberately not applied (reformatting is out of this unit's scope):

| Measure | Base `93275ed4…` | Ported `2c5dfee0…` |
| --- | --- | --- |
| `ruff format --diff` hunks | 287 | 287 |
| Formatter-removed lines | 656 | 655 |
| Added lines falling inside a formatter change hunk | — | 3 (`:2073` in the `tool_calls_raw.append` hunk, `:9690` and `:9691` in the compact `_build_call_kwargs(...)` call hunk) |

Those three sites are the same pre-existing drift the formatter already flagged
at base (`agent/auxiliary_client.py:1919` and `:9485–9489` respectively), and the
total formatter-removed line count is one **lower** on the ported file: the
touched region adds no new `ruff format` delta.

## 4. Wider selection and environment-driven failure attribution

The whole `tests/agent/` directory was measured on both revisions with the same
runner and venv (the recorded `852 passed / 4 failed` figures name an earlier
objective's narrower "affected selection" whose exact file list is not recorded
in the ledger; this unit therefore reports a reproducible superset and the
measured delta instead of claiming an unreproducible number):

| Revision | Result |
| --- | --- |
| Base `54eeb56dab` | `=== Summary: 397 files, 4549 tests passed, 7 failed, 29 skipped (100% complete) in 651.2s (24 workers) ===` |
| Ported `70569d1025` | `=== Summary: 398 files, 4574 tests passed, 7 failed, 29 skipped (100% complete) in 657.7s (24 workers) ===` |
| Delta | +1 file, **+25 passed** (exactly the new regression module), **0** delta in failures and skips |

The same 7 tests fail on both revisions; each was re-run individually on both
sides and every one is environment-driven (missing `anthropic` package or
missing Anthropic credentials), not an effect of this port:

| Failing test | Base | Candidate | Observed cause |
| --- | --- | --- | --- |
| `tests/agent/test_auxiliary_transport_autodetect.py::test_resolve_provider_client_kimi_coding_wraps_anthropic` | 15P / 1F | 15P / 1F | "The 'anthropic' package is required for the Anthropic provider" → OpenAI-wire fallback |
| `tests/agent/test_command_token_source.py::TestCallableKeyGetsBearerAuth::test_callable_takes_the_bearer_hook_path` | 28P / 1F | 28P / 1F | `ImportError` raised from `_get_anthropic_sdk()` |
| `tests/agent/test_auxiliary_named_custom_providers.py::TestProvidersDictApiModeAnthropicMessages::test_resolve_provider_client_returns_anthropic_client` | 23P / 1F | 23P / 1F | expected `AnthropicAuxiliaryClient`, got OpenAI-wire client |
| `tests/agent/test_nous_portal_anthropic_wire.py::TestClientShape::test_portal_bearer_does_not_also_send_env_anthropic_api_key` | 23P / 2F | 23P / 2F | same anthropic-SDK-missing path |
| `tests/agent/test_nous_portal_anthropic_wire.py::TestClientShape::test_portal_jwt_authenticates_with_bearer_not_x_api_key` | (above) | (above) | same anthropic-SDK-missing path |
| `tests/agent/test_set_runtime_main_custom_provider.py::TestResolveAutoCustomEndToEnd::test_named_custom_anthropic_messages_keeps_full_name_and_url` | 4P / 1F | 4P / 1F | expected `AnthropicAuxiliaryClient`, got OpenAI-wire client |
| `tests/agent/test_vision_routing_31179.py::TestTextOnlyMainSkippedForVision::test_vision_capable_main_used` | 7P / 1F | 7P / 1F | "anthropic requested but no Anthropic credentials found" → client `None` |

Unmeasured, and reported as such rather than as a pass: on both revisions one
file exceeded the runner's 300 s per-file cap and was SIGKILL'd before any test
ran — `tests/agent/test_model_metadata.py` ("300s exceeded; process tree
SIGKILL'd", listed under "1 file where no tests ran"). Only `tests/agent/` was
run; the fork's complete suite and other directories were not.

## 5. Per-requirement behavior mapping

Line references are `<fork>:agent/auxiliary_client.py:<line>` at `70569d1025`;
test names are in `tests/agent/test_auxiliary_client_responses_terminal_420.py`.

| Card requirement | Code landmark | Regression coverage | Result |
| --- | --- | --- | --- |
| `failed`/`cancelled` terminal raises the typed failure carrying `status`, `incomplete_details` and provider error instead of a successful `stop` | `AuxiliaryResponsesTerminalError` (`:1471`), raise at `:1980` | `test_cancelled_terminal_raises_typed_failure`, `test_failed_terminal_raises_typed_failure_with_provider_error` | pass |
| `status=incomplete` → `content_filter` when the reason is `content_filter`, otherwise `length` | `:2108` | `test_incomplete_max_output_tokens_is_length_not_stop`, `test_unknown_incomplete_reason_is_still_length_not_stop`, `test_content_filter_incomplete_is_not_stop`, `test_stream_incomplete_frame_preserves_reason` | pass |
| `queued`/`in_progress` and unfinished `message`/`function_call` items → `incomplete` | `:2108`, item-status guard at `:2023` | `test_in_progress_function_call_is_not_a_completed_tool_call`, `test_incomplete_message_item_never_reports_stop` | pass |
| `commentary`/`analysis` message items never enter assistant content and never satisfy the output-text fallback | phase handling `:2032`, `message.reasoning` at `:2131`, fallback guard `:2101` | `test_commentary_phase_does_not_contaminate_final_answer`, `test_analysis_phase_is_not_final_content`, `test_analysis_plus_final_answer_is_a_completed_answer`, `test_commentary_only_response_is_not_recovered_as_final` | pass |
| A completed empty output with a valid top-level `output_text` is recovered | `:2104` | `test_empty_output_with_output_text_is_recovered`, `test_completed_empty_response_stays_empty_not_incomplete` | pass |
| Completed `function_call` items become `tool_calls` | `:2068` | `test_completed_function_call_is_tool_calls` | pass |
| `tool_choice` threaded through `call_llm` → `_call_llm_impl` → `_build_call_kwargs` → adapter and the same-provider retry; chat-style `{"type": "function", "function": {"name": …}}` translated to `{"type": "function", "name": …}`; string forms passed through; only sent together with tools | `_responses_tool_choice_shape` (`:1494`), adapter (`:1686`, `:1688`), params `:4873`, `:8715`, `:9448`, `:9521`, call sites `:4908`, `:9474`, `:9690`, retries `:10019`, `:10069`, tools guard `:8833` | `TestToolChoicePassthrough` (5), `TestBuildCallKwargsToolChoice` (2), `TestCallLlmToolChoicePassthrough` (1) | pass |
| Unsupported Router fields `max_output_tokens`, `response_format` and `text` are never sent on the Responses request | adapter request construction (`create`, tools/`tool_choice` region) | `test_unsupported_router_fields_are_not_sent` | pass |
| The async auxiliary entry point and the emergency-fallback candidate builders keep the route default | `_retry_same_provider_async` (`:4933`) has no `tool_choice` parameter (0 occurrences in that function); diff footprint contains no async fallback hunk | inspection (§3) | confirmed |
| Robustness cases kept from the reviewed matrix | item/arg coercion and output handling | `test_malformed_items_do_not_fabricate_content`, `test_non_list_output_is_treated_as_empty`, `test_unrepresentable_tool_choice_is_not_sent`, `test_tool_choice_without_tools_is_not_sent` | pass |

## 6. Fork tree state, boundaries and effects

| Item | Value |
| --- | --- |
| Branch | `fix/420-responses-terminal-fidelity` (pre-existing branch at `54eeb56dab`; now one commit ahead) |
| Commit | `70569d1025b64cb98114e78840cef83baf1fc9d2`, parent `54eeb56dabefc98821d696656ed58c55dd777346`, no amend/rebase/squash |
| Files in the commit | `agent/auxiliary_client.py`, `tests/agent/test_auxiliary_client_responses_terminal_420.py` (2 files, +758 / −13) |
| Working tree after commit | clean (`git status --short` empty) |
| `aether-main` | `54eeb56dabefc98821d696656ed58c55dd777346`, checkout clean — never mutated |
| Auxiliary measurement worktree | detached `54eeb56dab` worktree created under `/tmp` for the base-side comparison and removed afterwards; the port worktree and the fork's other worktrees are untouched |
| Effects | local commit only. No push, PR, merge, tag, release, package publish, issue mutation, service restart, activation or live-tree/installed-editable change |
| Out of scope by design | `AETHER_FORK.md`, the review-flow tests, `VERSION`, `CHANGELOG.md`, `.github/**`, `docs/**`, `HERMES_LOCAL_PATCHES.md`, the reconciliation entries, the live runtime and `home/` were not touched; the candidate commits themselves remain LC-FORK's |

## 7. Unit-level compatibility and residual risk

- Compatibility impact of this unit: additive and self-contained. New exception
  type and new optional keyword-only parameters defaulting to `None`; the
  returned chat-shaped response gains `status`, `incomplete_details`,
  `incomplete_reason` and `message.reasoning`; `finish_reason` now reports
  `length` / `content_filter` / `incomplete` where a truncated, filtered,
  cancelled or unfinished terminal previously reported `stop`. That semantic
  change is the accepted HLP-420 contract behavior, and the accepted
  `blocking_uncertainty` items (async path keeps the route default, no forced
  structured-call contingency, hollow completed responses still `stop`) are
  unchanged by this port.
- No regression was observed in the measured surface: focused module 25 passed,
  existing auxiliary-client suite 181 passed on both revisions, whole
  `tests/agent/` delta is exactly the +25 new tests with an identical 7-failure
  environment set.
- Residual risk is low because the delivered bytes are provably identical to the
  already reviewed candidate. The material limits are measurement scope, not
  correctness: (a) only `tests/agent/` was executed; (b) `test_model_metadata.py`
  was unmeasured on both revisions due to the 300 s per-file cap; (c) the
  ledger's `852 / 827` "affected selection" is not reproducible from the record
  as written, so this unit substitutes a reproducible superset and its measured
  delta; (d) the Aether-side consumption half (SemanticManager) is a separate
  unit by the ledger's Activation line and was not exercised here.
- This is unit-level compatibility evidence only. No aggregate release,
  publication or activation conclusion is made or implied.
