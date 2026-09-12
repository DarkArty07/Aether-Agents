# Implementation Evidence — PR8-CI

**Status:** Unit execution complete. Real PluginContext qualification executed against exact public Hermes baseline across Python 3.11, 3.12, and 3.13 with no recurrence; disposition recorded as "no longer reproducible with evidence" with zero speculative changes. Minimum #403 CI unblocker executed: unsafe bytes in historical finalized contract `oc_0084270d940c98d9/v1.md` removed from active tracked surface, portable tombstone receipt established, and canonical base manifest updated. Public-artifact scanner and public-artifact test suite verified green with no exemptions.

**Unit:** PR8-CI (`t_7953714b`)

**Objective Contract:** `oc_c780a10d94b78d85@v1` (SHA-256 `0fdd7931cc77e75eecc20e37c32f1352afbd8bf91869340aa092ac20e12905a5`)

**Source Requirements:** `specs/pragmatic-reliability-eight/spec.md` §R357, §B403; `plan.md` §D3 U-CI; `quickstart.md`; Supervisor breakdown `tasks.md` §Unit deliveries PR8-CI.

**Base revision:** `0a41438a13a0655b07703910b605e595f55aa660`

**Unit compatibility impact:** `patch` — public-artifact verification unblocked and tombstone recorded; no public product interface, objective-contract API, or runtime behavior modified.

---

## 1. Scope, Boundaries, and Writable Surface Adherence

Execution was restricted strictly to the authorized exclusive writable surface:
- `.aether/objective-contracts/oc_0084270d940c98d9/**`:
  - `git rm .aether/objective-contracts/oc_0084270d940c98d9/v1.md`
  - Created portable tombstone `.aether/objective-contracts/oc_0084270d940c98d9/tombstone.json`
- `.github/workflows/policy.yml`:
  - Replaced line 73 (`.aether/objective-contracts/oc_0084270d940c98d9/v1.md`) with `.aether/objective-contracts/oc_0084270d940c98d9/tombstone.json`.
  - Added line for `.aether/objective-contracts/oc_c780a10d94b78d85/v1.md` to expected-file manifest (PR8-CI-REWORK-1).
  - Touched no other lines or jobs.
- `tests/test_public_artifacts.py`:
  - Added `test_historical_contract_oc_0084270d940c98d9_tombstone_preserves_locator`.
  - Added `test_canonical_base_manifest_matches_tracked_non_specs_files` (PR8-CI-REWORK-1).
- `specs/pragmatic-reliability-eight/evidence/PR8-ci.md`:
  - Authoring this evidence artifact.

Reserved surfaces strictly preserved and untouched:
- `src/aether_agents/objective_contracts/**` (reserved for PR8-CONTRACT)
- `HERMES_LOCAL_PATCHES.md`, `patches/hermes/**`, reconciliation ledgers (reserved for PR8-LEDGER)
- Fork sources and branches (reserved for PR8-CRON, PR8-REVIEW)
- Live runtime checkouts (`home/.venv-hermes/src/hermes-agent`, `home/runtime/aether-agents-main`)

---

## 2. Outcome A — #357 Qualification and Disposition

### 2.1 Methodology and Execution

The exact real PluginContext qualification was executed against the exact public Hermes baseline:
- Repository: `https://github.com/NousResearch/hermes-agent.git`
- Annotated tag: `v2026.8.18`
- Tag object SHA: `9f13bbbf8423427e159c78066356ca0e27ca6b74`
- Locked commit: `e624e9fde561e1add9388384012b295fde669ade`
- Clean checkout target: `/tmp/hermes-exact`

Execution used the repository's own canonical entry points:
1. `uv run --frozen python scripts/qualify_observation.py checkout --path /tmp/hermes-exact --json`
   - Verified output: `{"clean":true,"commit":"e624e9fde561e1add9388384012b295fde669ade","path":"/tmp/hermes-exact","tag":"v2026.8.18","tag_object":"9f13bbbf8423427e159c78066356ca0e27ca6b74"}`
2. Tested across all three required Python versions: Python 3.11.15, Python 3.12.13, and Python 3.13.15.
   - Command:
     ```bash
     uv sync --frozen --python <version>
     python_path="$(uv run --frozen python -c 'import sys; print(sys.executable)')"
     env -u HERMES_DELEGATED_CHILD_CONTEXT \
       uv run --frozen python scripts/qualify_observation.py test \
         --checkout /tmp/hermes-exact \
         --python "$python_path" \
         --output /tmp/observation-tests-python-<version>.json \
         --json
     ```
   - No retry, no skip, no timeout increase, no assertion relaxation.

### 2.2 Results Across Python Matrix

| Python Version | Interpreter Environment | Core Tests Outcome | Real PluginContext Harness Outcome | Result JSON Path | Result JSON SHA-256 |
|---|---|---|---|---|---|
| **Python 3.11.15** | `<operator-home>/.local/share/uv/python/cpython-3.11-linux-x86_64-gnu/bin/python3.11` | 453/453 passed (manifest `d7cedc7d...`) | 1/1 passed in 1.33s (22 callbacks, 0 unload hooks, tool/API capture true, raw payload absent) | `/tmp/observation-tests-python-3.11.json` | `bdfd52dc113b76ab40f5b2396cd512bb6c9c0df35ca2f519bcd8910010b7caee` |
| **Python 3.12.13** | `<operator-home>/.local/share/uv/python/cpython-3.12-linux-x86_64-gnu/bin/python3.12` | 453/453 passed (manifest `d7cedc7d...`) | 1/1 passed in 1.20s (22 callbacks, 0 unload hooks, tool/API capture true, raw payload absent) | `/tmp/observation-tests-python-3.12.json` | `3d423170301c11256d94217e36ddbfe40c6c18fa7b42524c9e5a1d9eca20ffcc` |
| **Python 3.13.15** | `<operator-home>/.local/share/uv/python/cpython-3.13-linux-x86_64-gnu/bin/python3.13` | 453/453 passed (manifest `d7cedc7d...`) | 1/1 passed in 1.13s (22 callbacks, 0 unload hooks, tool/API capture true, raw payload absent) | `/tmp/observation-tests-python-3.13.json` | `4bc1755d0d59959e3557af812f401929641a94f1a1f5bedde5cf85fae7e06a2c` |

### 2.3 Disposition

- The operator-supplied direct evidence receipt (SHA-256 `9c6b92731f379c3da62bb82e4ed4f401e1bd018694f82c8231c0cf8b9ffe1611`) was used as an input and independently reproduced in full.
- The failure named in #357 did **not** recur on Python 3.11, 3.12, or 3.13.
- In accordance with `spec.md` §R357 and the card body, **no** speculative product change was made.
- **Disposition:** "no longer reproducible with evidence".
- Post-merge confirmation on `main` is delegated to PR8-INT.

---

## 3. Outcome B — #403 Minimum CI Reconciliation

### 3.1 Defect Analysis

- Historical finalized contract `.aether/objective-contracts/oc_0084270d940c98d9/v1.md` (introduced at commit `dad66f7e592b6a172ba9168f63df5080e7a31ec2`) contained operator-local path data (an absolute user home path and desktop project layout) and destination data (a private messaging destination identifier (redacted)), triggering the public-artifact scanner with `absolute-user-home` and `operator-desktop-layout` violations.
- Because finalized contracts are immutable Git objects, rewriting the historical file in place or rewriting Git history is forbidden.
- Per contract instructions: remove the unsafe bytes from the current tracked artifact set and establish a portable tombstone/redaction receipt.

### 3.2 Tombstone Receipt Specification

File: `.aether/objective-contracts/oc_0084270d940c98d9/tombstone.json`
```json
{
  "artifact_type": "aether.objective-contract-tombstone.v1",
  "project_id": "12027989-a08f-41cd-a82c-54ff1bfb6b03",
  "contract_id": "oc_0084270d940c98d9",
  "version": 1,
  "status": "tombstone",
  "reason": "Issue #403: removed from active tracked public release surface because pre-validation historical contract bytes contained operator-local path data. Immutable original preserved in Git history.",
  "original_sha256": "7447fd890a24f6c7a82ca03f6b4aa7a992299d1beda2c78e078b5c6f578812cb",
  "historical_commit_locator": "dad66f7e592b6a172ba9168f63df5080e7a31ec2",
  "historical_path": ".aether/objective-contracts/oc_0084270d940c98d9/v1.md",
  "superseding_safe_locator": ".aether/objective-contracts/oc_0084270d940c98d9/tombstone.json"
}
```

Audit properties:
1. Original SHA-256 digest preserved: `7447fd890a24f6c7a82ca03f6b4aa7a992299d1beda2c78e078b5c6f578812cb`
2. Historical commit locator preserved: `dad66f7e592b6a172ba9168f63df5080e7a31ec2`
3. Superseding safe locator points to the portable tombstone.
4. No operator-local paths or private destinations exposed.
5. Scanner grammar was not modified, not weakened, and no scanner exemption was introduced.

### 3.3 Reference and Manifest Updates

1. `.github/workflows/policy.yml`:
   - Line 73 replaced `.aether/objective-contracts/oc_0084270d940c98d9/v1.md` with `.aether/objective-contracts/oc_0084270d940c98d9/tombstone.json`.
   - Line 66 added `.aether/objective-contracts/oc_c780a10d94b78d85/v1.md` (PR8-CI-REWORK-1) to restore canonical base manifest verification to green.
2. `tests/test_public_artifacts.py`:
   - Added `test_historical_contract_oc_0084270d940c98d9_tombstone_preserves_locator` asserting:
     - `tombstone.json` is present and well-formed.
     - `v1.md` is deleted from the current surface.
     - All audit locators and digests match.
   - Added `test_canonical_base_manifest_matches_tracked_non_specs_files` asserting:
     - Expected files extracted from `.github/workflows/policy.yml` match `git ls-files | grep -v '^specs/'` sorted.

---

## 4. Verification Evidence: Pre-Fix Red and Post-Fix Green

### 4.1 Public Artifact Scanner (`scripts/check_public_artifacts.py`)

- **Pre-fix Command:** `uv run --frozen python scripts/check_public_artifacts.py`
  - **Exit Code:** `1`
  - **Observed Output:**
    ```text
    public artifact path scan failed:
    - .aether/objective-contracts/oc_0084270d940c98d9/v1.md: absolute-user-home
    - .aether/objective-contracts/oc_0084270d940c98d9/v1.md: operator-desktop-layout
    ```
- **Post-fix Command:** `uv run --frozen python scripts/check_public_artifacts.py`
  - **Exit Code:** `0`
  - **Observed Output:**
    ```text
    public artifact path scan passed: tracked surface + 0 artifact(s)
    ```

### 4.2 Public Artifact Test Suite (`tests/test_public_artifacts.py`)

- **Pre-fix Command:** `uv run --frozen pytest -q tests/test_public_artifacts.py`
  - **Exit Code:** `1`
  - **Observed Output:**
    ```text
    FAILED tests/test_public_artifacts.py::test_tracked_public_surface_contains_no_operator_paths - AssertionError: public artifact path scan failed: ...
    1 failed, 5 passed in 1.14s
    ```
- **Post-fix Command:** `uv run --frozen pytest -q tests/test_public_artifacts.py`
  - **Exit Code:** `0`
  - **Observed Output:**
    ```text
    .......                                                                  [100%]
    7 passed in 1.51s
    ```

### 4.3 Wheel and Sdist Distribution Scan

- **Command:**
  ```bash
  uv build
  uv run --frozen python scripts/check_public_artifacts.py \
    --artifact dist/aether_agents-0.24.0.tar.gz \
    --artifact dist/aether_agents-0.24.0-py3-none-any.whl
  ```
- **Exit Code:** `0`
- **Observed Output:**
  ```text
  Building source distribution...
  Building wheel from source distribution...
  Successfully built dist/aether_agents-0.24.0.tar.gz
  Successfully built dist/aether_agents-0.24.0-py3-none-any.whl
  public artifact path scan passed: tracked surface + 2 artifact(s)
  ```

### 4.4 Canonical Base Manifest Step Verification

- **Command:** Self-contained local reproduction of `.github/workflows/policy.yml` lines 26-395:
  ```bash
  expected=$(mktemp)
  actual=$(mktemp)
  awk "/cat >\"\\\$expected\" <<'EOF'/{flag=1;next}/^          EOF\$/{flag=0}flag" .github/workflows/policy.yml > "$expected"
  sed -i 's/^          //' "$expected"
  sort -o "$expected" "$expected"
  git ls-files | grep -v '^specs/' | sort > "$actual"
  diff -u "$expected" "$actual"
  ```
- **Pre-fix Finding (Objective-caused defect):**
  - Commit `0a41438a13a0655b07703910b605e595f55aa660` introduced this objective's own contract file `.aether/objective-contracts/oc_c780a10d94b78d85/v1.md` into the tracked repository without adding it to the expected-file list inside `.github/workflows/policy.yml`.
  - Because this objective's PR integrates `0a41438a`, the resulting diff failure (`+ .aether/objective-contracts/oc_c780a10d94b78d85/v1.md`) is objective-caused and will fail the required Repository Policy check for the PR8-INT PR.
  - Pre-fix command output (`diff -u "$expected" "$actual"`):
    ```diff
    --- /tmp/tmp.expected
    +++ /tmp/tmp.actual
    @@ -30,6 +30,7 @@
     .aether/objective-contracts/oc_ba23edf6f74b7b43/v1.md
     .aether/objective-contracts/oc_c0abec2179f6b09c/v1.md
     .aether/objective-contracts/oc_c53c85ffb6c24f69/v1.md
    +.aether/objective-contracts/oc_c780a10d94b78d85/v1.md
     .aether/objective-contracts/oc_d7d067bf87e67cba/v1.md
     .aether/objective-contracts/oc_d7d067bf87e67cba/v2.md
     .aether/objective-contracts/oc_d7d067bf87e67cba/v3.md
    ```
- **Post-fix Result:**
  - Added `.aether/objective-contracts/oc_c780a10d94b78d85/v1.md` to `.github/workflows/policy.yml` in the sorted neighborhood between `oc_c53c85ffb6c24f69/v1.md` and `oc_d7d067bf87e67cba/v1.md`.
  - Re-executed reproduction command: diff is empty and exit code is `0`.
  - Verified remaining step sub-checks: spec manifest mode/stage/safety/extension/UTF-8/secret scan passed, `VERSION` regex passed, forbidden tracked paths absent, and forbidden vocabulary absent.
  - Added regression test `test_canonical_base_manifest_matches_tracked_non_specs_files` in `tests/test_public_artifacts.py` to pin the exact CI comparison against the workflow heredoc.

---

## 5. Auxiliary Policy and Quality Gates

| Check | Command | Exit Code | Observed Output / Details |
|---|---|---|---|
| Ruff Linter | `uv run --frozen ruff check src/aether_agents tests scripts` | `0` | All checks passed! |
| Documentation Checker | `uv run --frozen python scripts/check_documentation.py` | `0` | `documentation validation passed` |
| Baseline Drift | `uv run --frozen python scripts/check_hermes_baseline_drift.py --json` | `0` | Baseline matches locked tag `v2026.8.18`, commit `e624e9fde561e1add9388384012b295fde669ade` |
| Type Checker | `uv run --frozen mypy src/aether_agents` | `0` | `Success: no issues found in 53 source files` |
| Baseline Tests | `AETHER_EXACT_HERMES_CHECKOUT=/tmp/hermes-exact uv run --frozen pytest -q tests/test_hermes_baseline.py tests/test_observation_qualification.py` | `0` | `65 passed, 12 skipped in 2.97s` |
| Unit Test Suite | `uv run --frozen pytest -q tests/test_public_artifacts.py` | `0` | `8 passed in 3.87s` |

---

## 6. Review Handoff Notes

- Child review card: `PR8-CI-REVIEW` (`t_f23c6d5f`) is pre-created and ready to claim upon completion of this task.
- Per card instructions, `kanban_complete` is called directly without `kanban_request_review`.
- No remote branches were pushed and no GitHub PR was opened (publication belongs to PR8-INT).
- PR8-CI-REWORK-2: redacted the private messaging destination identifier previously cited in Section 3.1; no destination identifiers remain in tracked evidence or artifacts.
