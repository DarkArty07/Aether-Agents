# Evidence — PR8-LEDGER (#372, #393, #385, #362, #388-framework)

**Unit:** PR8-LEDGER (`t_cf843ae0`)
**Objective:** `oc_c780a10d94b78d85@v1` (§R372, §R385, §R393, shared constraints)
**Issues:** #372, #393, #385, #362, and framework side of #388
**Fork Repository:** `DarkArty07/aether-hermes`
**Declared Fork Base Commit:** `6551b7c31cc665d59103c6d89cb5e0c60666f803` (`origin/aether-main`)
**Hermes Baseline (public release):** `v2026.8.18` (tag `9f13bbbf8423427e159c78066356ca0e27ca6b74`, commit `e624e9fde561e1add9388384012b295fde669ade`)
**Inspected Upstream Revisions:** `4f22543509d1b91dc45bcb369447126c5eb14fb7` (reconciliation baseline) and `31d0a2428e9db346d6781da66f5b37ff3e12def2` (current upstream `NousResearch/hermes-agent` tip)

---

## 1. Identifier Map and Patch Artifacts

| HLP ID | Issue | Description | Patch File | SHA-256 Digest | Fork Candidate Commit(s) |
|---|---|---|---|---|---|
| `HLP-362` | `#362` | Independent same-card review ownership | `patches/hermes/HLP-362-independent-review-ownership.patch` | `e6218c02d5da3eee1b620c4e2e845c840a8e86ce36616781c97ddcdcad7e5638` | `8afefe7e304f2b3c80cecbbb24bf9e60be72044b` (PR #5) |
| `HLP-372` | `#372` | Profile-scoped cron script root | `patches/hermes/HLP-372-profile-cron-script-root.patch` | `97152a6358b13b34b95341d5f82f7b7012c5174d917817d3e3934260d15ebdaf` | `bd0f0ad6db0f9552b824cfc495a314a48e218af2`, `4fc5141f8d764f1dbc2b4d37128b5351b8d0aa62` (PR #10) |
| `HLP-385` | `#385` | Review topology guidance cannot be mistaken for terminal integration | `patches/hermes/HLP-385-review-topology-guidance.patch` | `b3decd3e83ea0133765ce0204ddc3ad017bffa0cac657f6b0153a92fbb8e4003` | `9fba8552bba30004ab452823668a105dee1ee89d` (PR #9) |
| `HLP-388` | `#388` | Persisted launch workdir in cron session row | `patches/hermes/HLP-388-cron-session-launch-workdir.patch` | `1d3bdad267ae3e95a6db379f7f4fe24ff3e895f3b0941d41f42ef3d06d0a5210` | `62eee7baab1337a9e40a8312052cecd096caaed7` (PR #10) |
| `HLP-393` | `#393` | Trusted commissioning origin and kanban auto-subscription | `patches/hermes/HLP-393-cron-commissioning-origin-subscription.patch` | `d81191d1727361528864498d2ee41a3c9fa95302559932e300a7c15e6838f460` | `3c9f955ae4c9e9970a73db7fc435d102581b6350`, `4fc5141f8d764f1dbc2b4d37128b5351b8d0aa62` (PR #10) |

---

## 2. Fork Candidates and Base Verification

The fork candidate commits were verified directly against remote `https://github.com/DarkArty07/aether-hermes.git`:
- `git ls-remote origin fix/pr8-385-review-guidance` -> `9fba8552bba30004ab452823668a105dee1ee89d` (PR #9 head matches)
- `git ls-remote origin fix/pr8-cron-script-root-origin-cwd` -> `4fc5141f8d764f1dbc2b4d37128b5351b8d0aa62` (PR #10 head matches)

Every patch was tested with `git apply --check` against declared fork base `6551b7c31cc665d59103c6d89cb5e0c60666f803`:
- `HLP-362-independent-review-ownership.patch`: git apply --check passed (exit 0; also applies cleanly to pristine public baseline `e624e9fde561e1add9388384012b295fde669ade`)
- `HLP-372-profile-cron-script-root.patch`: git apply --check passed (exit 0)
- `HLP-385-review-topology-guidance.patch`: git apply --check passed (exit 0)
- `HLP-388-cron-session-launch-workdir.patch`: git apply --check passed (exit 0)
- `HLP-393-cron-commissioning-origin-subscription.patch`: git apply --check passed (exit 0)

Sequential application of `HLP-372` + `HLP-393` + `HLP-388` against `6551b7c31cc665d59103c6d89cb5e0c60666f803` reproduces fork tip `4fc5141f8d764f1dbc2b4d37128b5351b8d0aa62` with 0 diff.

---

## 3. Honest Baseline Expectation Evidence

The contract requires: "The Aether test suite must not falsely expect an unpatched upstream baseline to provide downstream behavior. Test the patch against a disposable authenticated baseline/fork candidate instead."

Previously, `tests/test_same_card_phase_predicates.py` asserted that `request_review` without `reviewer` returned `ok is False` on the unpatched baseline fixture (`isolated_board`), failing CI because the unpatched baseline permits review without a reviewer.

### Control 1: Unpatched Baseline (RED under old expectation)
Calling `kb.request_review` without `reviewer` on unpatched baseline `v2026.8.18`:
```text
Unpatched baseline request_review result: ok=True, reason=None
AssertionError: Expected ok to be False on unpatched baseline, but got True
Exit code: 1
```
This confirms that the unpatched baseline does NOT enforce independent review ownership without downstream HLP-362. Documented as a separate test: `test_unpatched_baseline_lacks_independent_review_ownership`.

### Control 2: Patched Baseline / Candidate (GREEN)
Executing against an isolated clone of the public baseline with `HLP-362-independent-review-ownership.patch` applied:
```text
{"ok": false, "reason": "an initial review requires an explicit independent reviewer; pass reviewer= (re-review may reuse durable reviewer provenance)", "status": "running", "claim_lock": true}
Exit code: 0
```
Verified by `test_initial_review_requires_an_independent_reviewer`: 11/11 tests in `tests/test_same_card_phase_predicates.py` pass.

---

## 4. Verification Suite Results

1. **Reconciliation Validator:**
   `uv run --frozen python scripts/validate_hermes_patch_reconciliation.py --observed-at-utc "2026-09-11T16:00:00Z" --upstream-repository "https://github.com/NousResearch/hermes-agent" --upstream-revision "4f22543509d1b91dc45bcb369447126c5eb14fb7"`
   Result: `reconciliation validation passed: specs/001-aether-v1-productization/evidence/hermes-patch-reconciliation.v1.json, specs/001-aether-v1-productization/evidence/hermes-patch-preflight.md` (exit 0)

2. **Reconciliation Suite:**
   `uv run --frozen pytest -v tests/test_hermes_patch_reconciliation.py`
   Result: 23 passed in 1.18s (exit 0)

3. **Predicate Suite with Corrected Baseline:**
   `uv run --frozen python scripts/run_tests.py -- tests/test_same_card_phase_predicates.py`
   Result: 11 passed in 2.94s (exit 0)

4. **Static Lint and Formatting:**
   `uv run --frozen ruff check tests/test_same_card_phase_predicates.py tests/test_hermes_patch_reconciliation.py scripts/validate_hermes_patch_reconciliation.py`
   Result: `All checks passed!` (exit 0)
   `uv run --frozen ruff format --check tests/test_same_card_phase_predicates.py tests/test_hermes_patch_reconciliation.py scripts/validate_hermes_patch_reconciliation.py`
   Result: `3 files already formatted` (exit 0)

5. **Type Checking:**
   `uv run --frozen mypy`
   Result: `Success: no issues found in 53 source files` (exit 0)

6. **Documentation and Public Artifact Scanners:**
   `uv run --frozen python scripts/check_documentation.py`
   Result: `documentation validation passed` (exit 0)
   `uv run --frozen python scripts/check_public_artifacts.py`
   Result: 0 findings from our files; inherited findings on `.aether/objective-contracts/oc_0084270d940c98d9/v1.md` owned by PR8-CI.

7. **Repository Whitespace Check:**
   `git diff --check 0a41438a13a0655b07703910b605e595f55aa660...HEAD`
   Result: exit 0 clean (0 trailing whitespace issues).

---

## 5. Compatibility and Release Conclusions

- `release_impact`: `patch`
- `release_action`: `defer`
- `release_channel`: `none`
- **Assessment:** Reconciles downstream fork patch evidence and makes the test suite honest without modifying public APIs or package distribution. Supervisor owns aggregate release conclusions and publication.
