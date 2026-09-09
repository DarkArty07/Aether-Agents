# Unit Evidence: ABR-META — LM Studio shape and advertised context windows

- **Unit:** ABR-META
- **Card ID:** `t_9f1c729d`
- **Issues:** [#306](https://github.com/DarkArty07/Aether-Agents/issues/306), [#293](https://github.com/DarkArty07/Aether-Agents/issues/293)
- **Objective Contract:** `oc_ddebf175a40251f7@v1` (SHA-256 `722100569399ac7b61e15bccdcba28fd5fafe1585e4a1f7fbbe3bf5dcf0aa4e8`)
- **Review lane:** Same-card Supervisor review (`kanban_request_review`, `reviewer="supervisor"`)
- **Unit compatibility impact:** `patch`

## 1. Source identity and boundary

| Tree | Revision / identity | Evidence |
| --- | --- | --- |
| Maintained fork baseline | `DarkArty07/aether-hermes` `aether-main` `28b593efa86bbc674b32f488c35932a4e7e85a51` | Verified before mutation in the nested unit worktree |
| Maintained fork candidate | `0d0fbecb54bde61e5caa1eac5d4d66923bc5e71f` | Local commit only; no push, PR, merge, or remote mutation |
| Candidate import | `agent/model_metadata.py` | Import probe resolved to the candidate fork source, not an installed release tree |

Pre-mutation hashes at fork baseline `28b593efa8`:

- `agent/model_metadata.py`: `50cdee849666035d4430f6c0c221e7678f7d9ad3b0fa8e8a4f3586d23917cb9b`
- `tests/agent/test_model_metadata.py`: `cca8cfe17223a7b1106cd350ff25a2cb882f6ba3da3d53e1ea167d7d914de767`
- `tests/agent/test_model_metadata_local_ctx.py`: `1367dc107b7f38113475a39a37884a6fb64f4cbb4e62bd76f3a8b919a99b03f9`

Candidate hashes:

- `agent/model_metadata.py`: `a547f3c844cfc24c5cc6a114f5ceedf2b6fae5ce82ad4443089c45d832f17ade`
- `tests/agent/test_model_metadata_gateway.py`: `8561fd3264301e4ff945113da6278488a78b86f3a5656bb2b9a365e8b54b446b`

The writable product surface was limited to `agent/model_metadata.py` and the new focused loopback test module. `auxiliary_client.py`, the existing model-metadata test files, ledgers, live profiles, credentials, and the canonical contract were not changed.

## 2. Upstream-first inspection and root cause

At the assigned fork baseline, `agent/model_metadata.py` had two relevant paths:

- `detect_local_server_type()` identified LM Studio from an HTTP-200 `/api/v1/models` response, but this unit deliberately preserved that shared detector because the same detector feeds other local-server consumers.
- `fetch_endpoint_model_metadata()` then parsed only `payload["models"]` in its LM Studio branch and returned its cache immediately, even when the response had no native models. The existing generic candidate loop immediately below already parsed OpenAI-compatible `data` rows and extracted `context_length`.

The actual fork file `hermes_cli/models.py` at the same baseline independently validates a top-level `models` list in `_lmstudio_fetch_raw_models()` (baseline lines 3957–4004). The candidate applies the same response-shape rule to the metadata parser without importing or broadening the model-picker path.

The bounded repair in `agent/model_metadata.py:677–679` and `:1293–1333`:

1. Checks that the LM Studio response is a mapping with a top-level `models` list before iterating native entries.
2. Returns the native cache only when at least one usable native model was parsed.
3. Falls through to the existing generic `/models` candidate loop for malformed, empty, or non-LM Studio-shaped responses, preserving generic `data[*].context_length` values.
4. Leaves global server detection, inference routing, payloads, auxiliary clients, and provider protocols unchanged.

This localizes the correction to endpoint metadata, avoiding the blast-radius change documented in the issue discussion for a global detector rewrite.

## 3. Baseline RED

The same focused test module was overlaid on a clean detached checkout of the unchanged fork baseline. Fixtures use a loopback HTTP server, synthetic model IDs, and no credentials.

**Command:**

```bash
HERMES_PYTHON=already-provisioned HERMES_TEST_FILE_RETRIES=0 scripts/run_tests.sh -j 1 tests/agent/test_model_metadata_gateway.py -q
```

**Observed baseline result:**

```text
Summary: 1 files, 2 tests passed, 4 failed (100% complete) in 9.9s (1 workers)
```

The four failures were the generic `data` response being discarded under an LM Studio verdict (including an empty native list and a stale disk verdict). The two passing controls covered a true native LM Studio payload and the explicit context override. No retry was used as evidence.

## 4. Candidate GREEN

**Focused ABR-META and adjacent local-probe suites:**

```bash
HERMES_PYTHON=already-provisioned HERMES_TEST_FILE_RETRIES=0 HERMES_TEST_WORKERS=1 scripts/run_tests.sh tests/agent/test_model_metadata_gateway.py tests/agent/test_model_metadata_local_ctx.py tests/agent/test_local_probe_disk_cache.py tests/agent/test_probe_cache_followups.py -q
```

Observed:

```text
Summary: 4 files, 46 tests passed, 0 failed (100% complete) in 7.4s (1 workers)
```

**Existing model-metadata cases affected by this path:**

```bash
HERMES_PYTHON=already-provisioned HERMES_TEST_FILE_RETRIES=0 HERMES_TEST_WORKERS=1 scripts/run_tests.sh tests/agent/test_model_metadata.py -k 'TestFetchEndpointModelMetadata or custom_endpoint_metadata_beats_fuzzy_default or custom_endpoint_without_metadata_falls_back_to_catalog or custom_endpoint_falls_back_to_hardcoded_catalog' -q
```

Observed:

```text
Summary: 1 files, 7 tests passed, 0 failed (100% complete) in 1.2s (1 workers)
```

**Static checks:**

```bash
python -m ruff check agent/model_metadata.py tests/agent/test_model_metadata_gateway.py
python -m ruff format --check tests/agent/test_model_metadata_gateway.py
python -m compileall -q agent/model_metadata.py tests/agent/test_model_metadata_gateway.py
git diff --check 28b593efa86bbc674b32f488c35932a4e7e85a51..HEAD -- agent/model_metadata.py tests/agent/test_model_metadata_gateway.py
```

Observed: Ruff check passed, the new test file was already formatted, compileall exited 0, and the candidate diff check exited 0. The full fork `agent/model_metadata.py` format check reports pre-existing formatting differences outside this unit; no whole-file reformat was applied.

## 5. Distinct issue dispositions and acceptance coverage

### #306 — generic gateway shape classification / parser fall-through

**Disposition:** Reproduced and fixed in the candidate; issue remains OPEN pending normal integrated closeout.

| Obligation | Check and observed result | Evidence |
| --- | --- | --- |
| Generic HTTP-200 `/api/v1/models` does not lose a valid OpenAI `data` list under the LM Studio branch | Baseline: generic loopback fixture failed. Candidate: `test_generic_data_shape_is_parsed_even_when_detector_reports_lmstudio` passed with stale detector forced to `lm-studio`; generic metadata returned a keyed model | `tests/agent/test_model_metadata_gateway.py` |
| Empty native LM Studio list falls through instead of returning an empty cache | Candidate: `test_empty_lmstudio_models_falls_through_to_generic_data` passed against loopback `/api/v1/models` with `models: []` and generic `/v1/models` data | `tests/agent/test_model_metadata_gateway.py` |
| Legacy/stale LM Studio verdict cannot discard generic metadata | Baseline: `test_generic_data_shape_revalidates_stale_disk_lmstudio_verdict` failed. Candidate passed while the disk probe returned synthetic `lm-studio` | `tests/agent/test_model_metadata_gateway.py` |
| Existing true LM Studio behavior remains | `test_true_lmstudio_models_shape_remains_supported` passed with native `models` and loaded `context_length=196608` | `tests/agent/test_model_metadata_gateway.py` |
| No unrelated detector/routing behavior changed | Adjacent local-probe and detector-cache suites passed: 17/17; no changes to detector implementation or routing modules | `tests/agent/test_local_probe_disk_cache.py`, `tests/agent/test_probe_cache_followups.py`, candidate diff |

### #293 — gateway-advertised per-model context windows

**Disposition:** Reproduced as the metadata-loss consequence of #306 and fixed through the existing provider context-resolution protocol; issue remains OPEN pending normal integrated closeout.

| Obligation | Check and observed result | Evidence |
| --- | --- | --- |
| Use an advertised per-model context window when present | Candidate loopback generic row carried synthetic `context_length=872000`; `fetch_endpoint_model_metadata()` preserved it and `get_model_context_length()` returned `872000` for the custom endpoint | `tests/agent/test_model_metadata_gateway.py` |
| Keep explicit fallback/override compatibility | `test_context_override_remains_available_when_gateway_has_no_context` returned explicit `config_context_length=123456`; existing custom-endpoint catalog fallback also passed | `tests/agent/test_model_metadata_gateway.py`, `tests/agent/test_model_metadata.py` |
| Do not guess or silently widen routing | Only the existing metadata parser/fallback and focused tests changed; no provider, routing, request, auth, or context-probe tier was widened | Candidate diff and 46-test adjacent suite |
| Preserve authentication boundaries | Loopback fixtures used no API key and did not exercise or copy credentials; existing adjacent probe tests remained green | `tests/agent/test_model_metadata_gateway.py`, `tests/agent/test_model_metadata_local_ctx.py` |

## 6. Downstream ledger paragraph (not applied by this unit)

```markdown
### ABR-META / #306 + #293 — shape-aware local gateway metadata

- **Issues:** [#306](https://github.com/DarkArty07/Aether-Agents/issues/306), [#293](https://github.com/DarkArty07/Aether-Agents/issues/293)
- **Commit:** `0d0fbecb54bde61e5caa1eac5d4d66923bc5e71f`
- **Evidence:** `specs/autonomous-bug-remediation/evidence/ABR-META.md`
- **Scope:** Maintained-fork `agent/model_metadata.py` local endpoint metadata parser and synthetic loopback regressions.
- **Behavior:** The existing LM Studio metadata branch now requires a top-level `models` list and only returns a non-empty native cache. Empty, malformed, or generic OpenAI-compatible responses fall through to the existing `/models` parser, which preserves advertised per-model context values. Explicit context overrides and fallback/catalog behavior remain available; global detector, inference routing, payload, authentication, and auxiliary-client behavior are unchanged.
- **Upstream relationship:** Candidate is based on maintained-fork `aether-main` `28b593efa86bbc674b32f488c35932a4e7e85a51`; no moving dependency or upstream upgrade was introduced. Retire this patch only after an exact released upstream artifact provides the same shape-aware fallback and the ABR-META regression suite passes without the local commit.
- **Rollback:** Revert local fork commit `0d0fbecb54bde61e5caa1eac5d4d66923bc5e71f`.
```

## 7. Limits and remaining risk

- Verification used the canonical fork runner with retries disabled and an already-provisioned Python environment. The complete legacy `test_model_metadata.py` file contains an unrelated network-bound test that exceeded the runner timeout; the relevant selected cases and all adjacent probe suites passed. This is not reported as a full-file pass.
- Project-knowledge status was unavailable (`available=false` / empty coverage), and the single configured update attempt timed out; source inspection, Git identity, issue records, and executable tests were used instead.
- The maintained fork has no CI result for this local-only commit; no Actions run was triggered.
- Issues #306 and #293 remain OPEN. No issue close, push, PR, merge, publication, deployment, live profile edit, credential use, or remote mutation was performed.
- Supervisor must independently review the candidate fork commit and this evidence before integration.
