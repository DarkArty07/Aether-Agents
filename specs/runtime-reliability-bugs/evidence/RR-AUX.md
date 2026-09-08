# RR-AUX: B292 Named-Custom Qualification and B301 Header Preservation Evidence

**Objective Contract:** `oc_5c2dad1b37b20a80@v1`  
**Unit:** RR-AUX (concentrated unit for B292 and B301 in `agent/auxiliary_client.py`)  
**Assignee:** Implementer  
**Status:** Implementation complete; handoff for same-card Supervisor review  
**Aether evidence base:** `0dd27e0eff060f143f80879845f0d76561633f56`  
**Maintained fork baseline:** `DarkArty07/aether-hermes` `aether-main` (`c185ee3bb5b6d609241432fd123c16143f065987`)  
**Maintained fork candidate:** `rr-aux-candidate`  
- Commit 1: `2337bd2d9efbf0421ac121877936e92bb9486e70` (`test(auxiliary): qualify named-custom resolution and fallback routes (#292)`)  
- Commit 2: `0f56400b1603c8195590a04da47424a0df40b145` (`fix(auxiliary): forward extra_headers in responses adapter and fallback (#301)`)  

## Dispositions

| Issue / Feature | Disposition | Summary | Unit Compatibility |
| --- | --- | --- | --- |
| **B292 (#292)** | `already-working-with-integrated-evidence` | All integrated named-custom controls passed on unchanged baseline (`c185ee3bb5b6d609241432fd123c16143f065987`). Preserved existing resolver without speculative code patches; delivered comprehensive regression coverage in `tests/agent/test_auxiliary_named_custom_providers.py`. | `none` |
| **B301 (#301)** | `reproduced-and-fixed` | Baseline failed with dropped `extra_headers` on Responses adapter and fallback (RED: 4 failed, 1 passed). Ported upstream `extra_headers` forwarding into `_CodexCompletionsAdapter.create`, added safe header filtering to fallback helpers, and enabled `extra_headers` on async auxiliary callers. All candidate tests pass (GREEN: 5 passed). | `patch` |

## Changes Implemented

### Maintained Fork (`DarkArty07/aether-hermes`)

1. **`agent/auxiliary_client.py`:**
   - **Upstream hunk port (`_CodexCompletionsAdapter.create`):**
     Ported the upstream `kwargs.get("extra_headers")` copy into `resp_kwargs["extra_headers"]`, citing immutable upstream `NousResearch/hermes-agent@9fd44b4dfc44138b9e5d5689acb56c438364ff7b` `agent/auxiliary_client.py:1367-1370`. Forwarded to the underlying `self._client.responses.create(**stream_kwargs)`.
   - **Safe request metadata filtering (`_safe_request_extra_headers`):**
     Added a sanitizer that produces a fresh dictionary copy of request-scoped metadata, explicitly stripping authorization, proxy authorization, cookie, and provider-specific key/token headers to prevent cross-destination authentication leakage.
   - **Fallback candidate helpers:**
     Updated `_call_fallback_candidate_sync` and `_call_fallback_candidate_async` to accept `extra_headers: Optional[Dict[str, str]] = None` and forward sanitized safe headers to `fb_kwargs` and auth-refresh `retry_kwargs`.
   - **Fallback invocations:**
     Passed `extra_headers=extra_headers` into `_call_fallback_candidate_sync` (in `_call_llm_impl`) and `_call_fallback_candidate_async` (in `_async_call_llm_impl`).
   - **Async auxiliary caller parity:**
     Updated `async_call_llm` and `_async_call_llm_impl` to accept `extra_headers`, forward them to `kwargs`, pass them through `_retry_same_provider_async`, and forward them to fallback.
   - **Preservation:**
     Preserved caller input dictionary immutability (`dict(extra_headers)`), client defaults immutability, `error_classifier.py`, `kanban_stop.py`, `background_review.py`, and `AETHER_FORK.md`.

2. **`tests/agent/test_auxiliary_named_custom_providers.py`:**
   - Preserved all 19 pre-existing tests in the module.
   - Added class `TestNamedCustomQualificationB292` with 5 integrated test cases:
     - `test_direct_named_custom_both_spellings`: direct calls using both `custom:<name>` and bare `<name>` route to the named endpoint with credentials from `key_env`, explicit `api_mode`, and bare model.
     - `test_configured_fallback_named_custom_both_spellings`: configured fallback routes to named custom provider with distinct credentials for both spellings.
     - `test_missing_named_custom_not_silently_another_provider`: unconfigured named custom provider fails cleanly with `RuntimeError` rather than silently resolving to another provider.
     - `test_anonymous_custom_preservation`: `provider="custom"` with explicit `base_url` remains preserved.
     - `test_builtin_provider_preservation_not_shadowed`: canonical built-in providers (`openrouter`, `openai`, `auto`) are not shadowed.

3. **`tests/agent/test_auxiliary_client_extra_headers.py`:**
   - Dedicated test suite for B301 with 5 integrated test cases using local HTTP recorder servers:
     - `test_sync_codex_adapter_forwards_extra_headers`: sync Responses adapter streams request-scoped headers (`x-initiator`, `x-request-id`) to the recording endpoint.
     - `test_async_codex_adapter_forwards_extra_headers`: async Responses adapter streams request-scoped headers.
     - `test_subsequent_request_clean_no_stale_attribution`: requests without `extra_headers` do not inherit stale attribution from prior calls.
     - `test_sync_fallback_forwards_safe_headers_and_distinct_auth`: primary fails (connection error), fallback receives safe metadata (`x-initiator`, `x-request-id`) and destination fake auth, while primary authorization and cookie headers are stripped.
     - `test_async_fallback_forwards_safe_headers_and_distinct_auth`: async fallback receives safe metadata and destination auth without leakage.

## Verification Matrix and Execution Results

Commands were executed using the sterile outer launcher (`lab_run`) defined in `quickstart.md`:

- Test files:
  - `tests/agent/test_auxiliary_client.py`
  - `tests/agent/test_auxiliary_client_resolve_dedup.py`
  - `tests/agent/test_auxiliary_named_custom_providers.py`
  - `tests/agent/test_auxiliary_client_extra_headers.py`
- Environment: `HERMES_TEST_FILE_RETRIES=0` under disposable sandbox root.

### Baseline vs Candidate Test Results

| Test File | Baseline (`c185ee3bb`) | Candidate (`0f56400b1`) | Delta / Notes |
| --- | --- | --- | --- |
| `tests/agent/test_auxiliary_client_extra_headers.py` | **4 FAILED, 1 PASSED** (RED) | **5 PASSED** (GREEN) | Causal patch: adapter and fallback header forwarding verified |
| `tests/agent/test_auxiliary_named_custom_providers.py` | **24 PASSED** (GREEN) | **24 PASSED** (GREEN) | Identical pass: proves B292 already working on baseline |
| `tests/agent/test_auxiliary_client.py` | 181 PASSED | **181 PASSED** (GREEN) | Full auxiliary client suite preserved |
| `tests/agent/test_auxiliary_client_resolve_dedup.py` | 5 PASSED | **5 PASSED** (GREEN) | Dedup resolution preserved |
| **Combined Target Suite** | **211 PASSED, 4 FAILED** | **215 PASSED, 0 FAILED** in 7.7s | Zero regressions across all 4 files |

### Behavioral Checks

| Check | Required Behavior | Observed Result | Evidence |
| --- | --- | --- | --- |
| **B301 sync adapter** | `extra_headers` reaches Responses HTTP stream | `x-initiator` and `x-request-id` received by local server | `test_sync_codex_adapter_forwards_extra_headers` PASS |
| **B301 async adapter** | `extra_headers` reaches async Responses HTTP stream | `x-initiator` and correlation id received | `test_async_codex_adapter_forwards_extra_headers` PASS |
| **B301 fallback sync** | Fallback receives safe metadata; destination auth separated | Secondary receives safe headers and its own destination credential; primary auth and cookie stripped | `test_sync_fallback_forwards_safe_headers_and_distinct_auth` PASS |
| **B301 fallback async** | Async fallback receives safe metadata without auth leakage | Secondary receives safe headers and destination key; primary auth stripped | `test_async_fallback_forwards_safe_headers_and_distinct_auth` PASS |
| **B301 immutability** | Input `extra_headers` dict and defaults not mutated | Input dict equals original snapshot after call | Verified in sync and async tests |
| **B301 no stale attribution** | Subsequent request has no leftover headers | Second request without `extra_headers` has no `x-initiator` | `test_subsequent_request_clean_no_stale_attribution` PASS |
| **B292 direct spellings** | Both `custom:<name>` and bare `<name>` route to named endpoint | Both spellings use `base_url`, `key_env` credential, explicit `api_mode`, bare model | `test_direct_named_custom_both_spellings` PASS |
| **B292 fallback spellings** | Fallback chain uses named provider for both spellings | Fallback requests reach named endpoint with distinct credential | `test_configured_fallback_named_custom_both_spellings` PASS |
| **B292 missing config** | Missing named custom config fails fast | Raises `RuntimeError` without silent fallthrough to another provider | `test_missing_named_custom_not_silently_another_provider` PASS |
| **B292 anonymous custom** | Anonymous custom preserved | `provider="custom"` with explicit `base_url` routes as expected | `test_anonymous_custom_preservation` PASS |
| **B292 built-in preservation**| Built-in providers preserved | Canonical built-in provider names not shadowed | `test_builtin_provider_preservation_not_shadowed` PASS |
| **Static checks** | `git diff --check` clean | Exit 0, zero whitespace/lint errors | `git diff --check` PASS |

## Downstream Ledger Entry (for RR-INT)

The following ledger paragraph is prepared for incorporation into `HERMES_LOCAL_PATCHES.md` and `AETHER_FORK.md` by the terminal integration unit (RR-INT):

> **B301 — Auxiliary request attribution preservation without authentication leakage (#301)**  
> **Commit:** `0f56400b1603c8195590a04da47424a0df40b145`  
> **Scope:** `agent/auxiliary_client.py` (`_CodexCompletionsAdapter.create`, `_safe_request_extra_headers`, `_call_fallback_candidate_sync`, `_call_fallback_candidate_async`, `_call_llm_impl`, `async_call_llm`, `_async_call_llm_impl`), `tests/agent/test_auxiliary_client_extra_headers.py`.  
> **Upstream Relationship:** Ports the `extra_headers` copy from immutable upstream `NousResearch/hermes-agent@9fd44b4dfc44138b9e5d5689acb56c438364ff7b` `agent/auxiliary_client.py:1367-1370` into `_CodexCompletionsAdapter.create`. Extends safe request-scoped metadata forwarding to auxiliary fallback candidates (`_call_fallback_candidate_sync` and `_call_fallback_candidate_async`) and async callers (`async_call_llm`), while enforcing strict exclusion of authorization, proxy authorization, cookie, and provider-specific key headers across destination boundaries.  
> **Rollback:** `git revert 0f56400b1603c8195590a04da47424a0df40b145`.  
> **Retirement Gate:** Retires when upstream releases an artifact containing `extra_headers` forwarding in both Responses adapter and auxiliary fallback routes with destination authentication isolation.

*(Note: B292 has no patch entry because it was qualified as already working on the maintained baseline without code modification.)*

## Boundaries and Residue Audit

- **Files modified in candidate:**
  - `agent/auxiliary_client.py` (exclusive writable)
  - `tests/agent/test_auxiliary_named_custom_providers.py` (exclusive writable)
  - `tests/agent/test_auxiliary_client_extra_headers.py` (new focused test file)
- **Preserved files (untouched):**
  - `agent/error_classifier.py` (owned by RR-295)
  - `agent/kanban_stop.py` (owned by RR-304)
  - `agent/background_review.py` (owned by RR-294)
  - `agent/conversation_loop.py`
  - `AETHER_FORK.md`
  - `HERMES_LOCAL_PATCHES.md`
- **Aether workspace:**
  - Only `specs/runtime-reliability-bugs/evidence/RR-AUX.md` authored.
- **Publication boundary:**
  - No git push, no pull request, no issue modification, and no package publication performed. All commits are local.
