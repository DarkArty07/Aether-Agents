# Implementation Evidence — Unit Q-HLP (HLP-310/HLP-354 Portable Patches and Reconciliation Coverage)

**Status:** Fail-first reproduced on unchanged baseline `cc1ea19` (RED: 4 failed, 14 passed in `tests/test_hermes_patch_reconciliation.py`); candidate verified (GREEN: 18 passed in 0.84s; `git apply --stat` succeeded on both patches; `git apply --check` on fork base `6243e40` succeeded with 0 byte drift against unit commits; schema validation clean; `git diff --check origin/main...HEAD` clean exit 0). Ready for same-card Supervisor review.

**Unit ID:** `Q-HLP`
**Task ID:** `t_d38c0622`
**Objective Contract:** `oc_0084270d940c98d9@v1` (SHA-256 `7447fd890a24f6c7a82ca03f6b4aa7a992299d1beda2c78e078b5c6f578812cb`)
**Source Requirements:** Contract Deliverable 3 / `HERMES_LOCAL_PATCHES.md` reconciliation; `specs/fix-310-341-345-354/tasks.md` unit Q-HLP; workflow run `34301307930` failure repair.
**Unit Compatibility Impact:** `patch`

---

## 1. Repositories and Revisions

- **Aether Worktree Root:** project-linked worktree for task `t_d38c0622`
- **Aether Branch:** `aether-agents-2/t_d38c0622-q-hlp-hlp-310-hlp-354-portable-patches-a`
- **Aether Base Commit:** `cc1ea19e267afd4b2d278b6a05afd6526eb5fa42` (`origin/main`)
- **Pre-mutation Target File SHA-256 (verified before mutation):**
  - `.github/workflows/policy.yml`: `224b81824891b78b11f5e04684def63f52819525b693b1091c10e43ed3f2603e`
  - `tests/test_hermes_patch_reconciliation.py`: `62e40890133af47820e4a2f36caf28a004302a9ce946744c7349f8ee75e8d686`
- **Fork Remote:** `https://github.com/DarkArty07/aether-hermes.git`
- **Fork Base Commit:** `6243e40ea6b06e85061bf3fedffaad43eed51dec` (`origin/aether-main`)
- **Fork Unit Commits vs Base:**
  - HF-310: `25cabeb25327199a03aa3cf1613ed2f815f646cb`
  - HF-354: `7d3173e1f3dba107f9a389d4e35c95f215775ee1`
  - Fork Merge: `28b593efa86bbc674b32f488c35932a4e7e85a51` (PR #4)

---

## 2. Generated Portable Patch Artifacts

Both patches were generated as file-scoped unified diffs of each unit's owned fork files only against fork base `6243e40ea6b06e85061bf3fedffaad43eed51dec`:

1. `patches/hermes/HLP-310-delegated-child-snapshot-exclusion.patch`:
   - Owned files: `tools/environments/base.py`, `tests/tools/test_snapshot_session_id_leak.py`, `tests/tools/test_delegate_kanban_isolation.py`
   - SHA-256: `85522d5d5b9bf6609894b1a50f199334d8842bd8c2265d2425e2b920e184f413`
   - `git apply --stat`: 3 files changed, 136 insertions(+), 7 deletions(-)

2. `patches/hermes/HLP-354-kanban-worktree-base-ref.patch`:
   - Owned files: `hermes_cli/kanban_db.py`, `tests/hermes_cli/test_kanban_worktree_base_ref.py`
   - SHA-256: `d0f185207c4ff953902c2f40aa9c48f2b27499e1b5f4a264e39a70d0a2383fc1`
   - `git apply --stat`: 2 files changed, 349 insertions(+), 7 deletions(-)

---

## 3. Scope and Modification Boundaries

Exclusive writable boundary for Q-HLP:
- `patches/hermes/HLP-310-delegated-child-snapshot-exclusion.patch` (new)
- `patches/hermes/HLP-354-kanban-worktree-base-ref.patch` (new)
- `specs/001-aether-v1-productization/evidence/hermes-patch-reconciliation/entries/HLP-310.json` (new)
- `specs/001-aether-v1-productization/evidence/hermes-patch-reconciliation/entries/HLP-354.json` (new)
- `tests/test_hermes_patch_reconciliation.py` (modified: `EXPECTED_ACTIVE_IDS`, `PATCH_DIGESTS`, `_copy_repository_evidence`)
- `.github/workflows/policy.yml` (modified: allowlist entries for the two new patches only)
- `specs/fix-310-341-345-354/evidence/Q-HLP.md` (this unit evidence file)

Preserved intact (zero modifications):
- `scripts/validate_hermes_patch_reconciliation.py`
- `specs/001-aether-v1-productization/contracts/hermes-patch-reconciliation.schema.json`
- `HERMES_LOCAL_PATCHES.md`
- `src/aether_agents/knowledge/semantic.py`
- `tests/test_knowledge_regressions.py`
- `.aether/objective-contracts/oc_0084270d940c98d9/v1.md`
- No live runtime mutation, profile modification, branch push, or PR opening.

---

## 4. Requirement to Evidence Mapping

| Acceptance Obligation | Source Ref | Check Executed | Observed Result | Evidence Location |
|---|---|---|---|---|
| HLP-310 portable patch artifact generated from fork commit `25cabeb` | AC-310, tasks.md Q-HLP | `git apply --stat` & `sha256sum` | 3 files, 136(+), 7(-); SHA-256 `85522d5d5b9bf6609894b1a50f199334d8842bd8c2265d2425e2b920e184f413` | `patches/hermes/HLP-310-delegated-child-snapshot-exclusion.patch` |
| HLP-354 portable patch artifact generated from fork commit `7d3173e` | AC-354, tasks.md Q-HLP | `git apply --stat` & `sha256sum` | 2 files, 349(+), 7(-); SHA-256 `d0f185207c4ff953902c2f40aa9c48f2b27499e1b5f4a264e39a70d0a2383fc1` | `patches/hermes/HLP-354-kanban-worktree-base-ref.patch` |
| Schema-valid reconciliation fragments for HLP-310 and HLP-354 | Contract Deliverable 3 | jsonschema `Draft202012Validator.validate()` against `hermes-patch-reconciliation.schema.json` | Both fragments schema valid; `upstream.inspected_revision` is `4f22543509d1b91dc45bcb369447126c5eb14fb7` | `specs/.../entries/HLP-310.json`, `specs/.../entries/HLP-354.json` |
| `EXPECTED_ACTIVE_IDS` matches `active_detailed_ledger_ids` in numeric order | tasks.md Q-HLP | `test_active_detailed_ledger_ids_include_hlp247_not_in_summary_table` | PASSED (HLP-310 before HLP-335, HLP-354 after HLP-335) | `tests/test_hermes_patch_reconciliation.py:38-56` |
| Repository fragments cover active ledger and bind patch digests | tasks.md Q-HLP | `test_repository_fragments_cover_active_ledger_and_bind_patch_digests` | PASSED (all 17 records verified; HLP-310 and HLP-354 patch digests bound and verified) | `tests/test_hermes_patch_reconciliation.py:204-232` |
| HLP-226 negative controls restore original regex failures | tasks.md Q-HLP | `test_repository_fragments_reject_hlp226_without_hlp226b_component` & `test_repository_fragments_reject_hlp226b_digest_drift` | PASSED (expected regexes `HLP-226b` and `artifact digest mismatch for HLP-226` matched; no missing ledger ID error) | `tests/test_hermes_patch_reconciliation.py:253-286` |
| `_copy_repository_evidence` copies all patch artifacts referenced by entries | tasks.md Q-HLP | Inspection of `_copy_repository_evidence` and test run on tmp_path | Dynamically copies all `kind=patch` artifacts referenced across all JSON fragments | `tests/test_hermes_patch_reconciliation.py:160-172` |
| Policy allowlist includes new patches | tasks.md Q-HLP | Inspection of `.github/workflows/policy.yml` diff | Both patch paths listed under allowlist | `.github/workflows/policy.yml:119-120` |

---

## 5. Verification Results

### 5.1 Fail-First (RED) on Unchanged `cc1ea19`
Running `uv run pytest tests/test_hermes_patch_reconciliation.py` on baseline `cc1ea19`:
```text
=================================== FAILURES ===================================
_____ test_active_detailed_ledger_ids_include_hlp247_not_in_summary_table ______
E       AssertionError: assert ('HLP-188', '...HLP-204', ...) == ('HLP-188', '...HLP-204', ...)
E         At index 14 diff: 'HLP-310' != 'HLP-335'
_____ test_repository_fragments_cover_active_ledger_and_bind_patch_digests _____
E       hermes_patch_reconciliation.ReconciliationError: missing ledger IDs: HLP-310, HLP-354
______ test_repository_fragments_reject_hlp226_without_hlp226b_component _______
E       AssertionError: Regex pattern did not match.
E         Expected regex: 'HLP-226b'
E         Actual message: 'missing ledger IDs: HLP-310, HLP-354'
____________ test_repository_fragments_reject_hlp226b_digest_drift _____________
E       AssertionError: Regex pattern did not match.
E         Expected regex: 'artifact digest mismatch for HLP-226'
E         Actual message: 'missing ledger IDs: HLP-310, HLP-354'
========================= 4 failed, 14 passed in 0.88s =========================
```

### 5.2 Candidate (GREEN) Verification
Running `uv run pytest tests/test_hermes_patch_reconciliation.py -v`:
```text
============================= test session starts ==============================
collected 18 items

tests/test_hermes_patch_reconciliation.py::test_reconciliation_contract_and_validator_are_present PASSED [  5%]
tests/test_hermes_patch_reconciliation.py::test_active_detailed_ledger_ids_include_hlp247_not_in_summary_table PASSED [ 11%]
tests/test_hermes_patch_reconciliation.py::test_repository_fragments_cover_active_ledger_and_bind_patch_digests PASSED [ 16%]
tests/test_hermes_patch_reconciliation.py::test_repository_fragments_reject_hlp262_omission PASSED [ 22%]
tests/test_hermes_patch_reconciliation.py::test_repository_fragments_reject_hlp226_without_hlp226b_component PASSED [ 27%]
tests/test_hermes_patch_reconciliation.py::test_repository_fragments_reject_hlp226b_digest_drift PASSED [ 33%]
tests/test_hermes_patch_reconciliation.py::test_reconcile_sorts_records_binds_provenance_and_writes_deterministic_outputs PASSED [ 38%]
tests/test_hermes_patch_reconciliation.py::test_reconcile_rejects_omitted_duplicate_or_unknown_ledger_ids[records0-missing ledger IDs] PASSED [ 44%]
tests/test_hermes_patch_reconciliation.py::test_reconcile_rejects_omitted_duplicate_or_unknown_ledger_ids[records1-duplicate] PASSED [ 50%]
tests/test_hermes_patch_reconciliation.py::test_reconcile_rejects_omitted_duplicate_or_unknown_ledger_ids[records2-unknown ledger IDs] PASSED [ 55%]
tests/test_hermes_patch_reconciliation.py::test_reconcile_rejects_hlp211_without_combined_hlp211b_component PASSED [ 61%]
tests/test_hermes_patch_reconciliation.py::test_reconcile_rejects_schema_enum_and_version_drift PASSED [ 66%]
tests/test_hermes_patch_reconciliation.py::test_reconcile_rejects_stale_artifact_hashes PASSED [ 72%]
tests/test_hermes_patch_reconciliation.py::test_reconcile_rejects_passed_artifact_status_with_nonpassing_artifact[failed] PASSED [ 77%]
tests/test_hermes_patch_reconciliation.py::test_reconcile_rejects_passed_artifact_status_with_nonpassing_artifact[unavailable] PASSED [ 83%]
tests/test_hermes_patch_reconciliation.py::test_reconcile_rejects_retirement_candidate_without_full_exact_gate PASSED [ 88%]
tests/test_hermes_patch_reconciliation.py::test_reconcile_rejects_private_content_or_upstream_disagreement[<lambda>-non-portable] PASSED [ 94%]
tests/test_hermes_patch_reconciliation.py::test_reconcile_rejects_private_content_or_upstream_disagreement[<lambda>-upstream revision] PASSED [100%]

============================== 18 passed in 0.84s ==============================
```

Additional verification commands:
- `git apply --stat patches/hermes/HLP-310-delegated-child-snapshot-exclusion.patch`: 0 exit, cleanly parsed (3 files, 136+, 7-)
- `git apply --stat patches/hermes/HLP-354-kanban-worktree-base-ref.patch`: 0 exit, cleanly parsed (2 files, 349+, 7-)
- `git apply --check` against fork base `6243e40ea6b06e85061bf3fedffaad43eed51dec` in isolated worktree: 0 exit on both patches; byte reconstruction against HF-310 commit `25cabeb` and HF-354 commit `7d3173e` confirmed exact (0 diff)
- `git diff --check`: 0 exit, clean
- `git diff --check origin/main...HEAD`: 0 exit, clean
- Direct jsonschema validation against `hermes-patch-reconciliation.schema.json`: both fragments valid
- Round-1 review whitespace fix: empty context lines formatted with trailing space (`' \n'`) by default git diff were sanitized to empty lines (`'\n'`), ensuring `git diff --check` and `git diff-tree --check` pass with 0 exit code while preserving patch applicability and byte-identical reconstruction.

---

## 6. Local Judgements & Preservations

1. **Artifact Verification Status**: Set to `"unavailable"` with honest blockers explaining that the reconstruction input is based on maintained fork base `6243e40ea6b06e85061bf3fedffaad43eed51dec` rather than historical inspected upstream revision `4f22543509d1b91dc45bcb369447126c5eb14fb7`, consistent with HLP-262 and HLP-305.
2. **Inspected Upstream Revision**: Kept at `4f22543509d1b91dc45bcb369447126c5eb14fb7` across both fragments as instructed, preserving set-level reconciliation coherence without inventing a second inspected revision.
3. **Evidence Artifact Preservation**: Excluded generated reconciliation summary files (`hermes-patch-reconciliation.v1.json` and `hermes-patch-preflight.md`) from unit commit so they are owned by integration or validator runs.
