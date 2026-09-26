# RC16-HLP evidence — HLP-428 required/present, HLP-433 deferred, pin-accurate reconciliation

## Context and boundaries

- **Unit:** `RC16-HLP` (task `t_eef61de8`)
- **Producer:** Implementer (Aether role)
- **Objective Contract:** `oc_c770cea3db51d97e@v2` (`cd80efb52125f45af5340baf8119aeaddc4756f9d04ae7722137ae5df1f9adc7`)
- **Execution breakdown:** `specs/issue-494-project-provenance/tasks-rc16.md` (commit `96c200e0`)
- **Base commit:** `dc4872834a2c670c506100fd60c69960247124f2`
- **Selected maintained-fork source:**
  - Repository: `https://github.com/DarkArty07/aether-hermes`
  - Branch: `aether-main`
  - Commit: `58f8c37a49b341f25b8fdd6310542fe932031b8d`
  - Git tree: `a93162c1a867202b03c12fa372c71029152fdcf7`
  - Materialized-source digest: `a2a9b374bd2022c7f96242b0ab2c95691119262c925389eb3820ca627c581144`
- **Unit nature:** unit-level implementation evidence and verification only. This document does not constitute independent review, integration, activation, deployment, or behavior qualification.

## Pinned fork checkout derivation

The checkout used for candidate qualification was initialized as a clean disposable clone targeting the maintained fork's remote-tracking `aether-main` at commit `58f8c37a49b341f25b8fdd6310542fe932031b8d`:
- Origin URL: `https://github.com/DarkArty07/aether-hermes`
- Branch: `aether-main`
- HEAD commit: `58f8c37a49b341f25b8fdd6310542fe932031b8d`
- Working tree status: clean (`git status --porcelain=v1` returned empty)

The source-tree digest was independently re-derived through the product's own code path (`LifecycleManager._verify_fork_candidate_checkout` executing `_materialize_git_archive` and `_tree_sha256` over the checkout at the pin):
- Computed `source_tree_sha256`: `a2a9b374bd2022c7f96242b0ab2c95691119262c925389eb3820ca627c581144` (9,378 materialized files, exactly matching the contract).

Fetch provenance note: the pinned commit `58f8c37a49b341f25b8fdd6310542fe932031b8d` is reachable via the fork's remote-tracking `origin/aether-main`. The fork's local branch `aether-main` (`84139ae9d8adff23ba790c9289aa631a2490ce38`) and published remote tip (`938bc34fbc`) are divergent/descendant revisions and were not used.

## Reconciled candidate obligations

### HLP-428 (`specs/001-aether-v1-productization/evidence/hermes-patch-reconciliation/entries/HLP-428.json`)
- Set `candidate_requirement: "required"` (promoted from `deferred` for RC16 adoption).
- Declared components: `HLP-428`, `hermes_cli/kanban_db.py`, `tests/hermes_cli/test_kanban_project_provenance.py`. Both files exist at the selected pin `58f8c37a49` and resolve present.
- Disclosed limitation recorded in `blocking_uncertainty`: the optional `Previous review returns (this task)` context line introduced in RC15 does not exist at selected pin `58f8c37a49b341f25b8fdd6310542fe932031b8d`. Retained RC15 review guidance uses its documented durable-history fallback when this optional context is absent. This absence is a disclosed candidate limitation, not an enforcement gate, fork source addition, hard workflow gate, or retirement claim.

### HLP-433 (`specs/001-aether-v1-productization/evidence/hermes-patch-reconciliation/entries/HLP-433.json`)
- Retained `candidate_requirement: "deferred"`, unretired, and visible.
- Declared components: `HLP-433`, `agent/auxiliary_client.py`.
- Evidenced absence: the regression test module `tests/agent/test_auxiliary_client_responses_reasoning_433.py` does not exist at selected pin `58f8c37a49b341f25b8fdd6310542fe932031b8d`. Merged revision `621047dc1c10cceb2825013cc8bb611b4d0e8de1` (PR #17) is an excluded descendant of the pin; live adoption and effective-runtime qualification remain deferred successors under issue #433.

## Exact execution commands and raw results

### 1. Canonical aggregate and preflight regeneration

Command:
```bash
uv run --frozen python scripts/validate_hermes_patch_reconciliation.py \
  --observed-at-utc "2026-09-26T00:15:00Z" \
  --selected-revision "58f8c37a49b341f25b8fdd6310542fe932031b8d" \
  --fork-checkout "<clean-fork-checkout-at-58f8c37a49>" \
  --json
```

Raw JSON output:
```json
{"status": "generated", "schema_version": "aether.hermes-patch-reconciliation.v1", "observed_at_utc": "2026-09-26T00:15:00Z", "selected_source": {"repository": "https://github.com/DarkArty07/aether-hermes", "revision": "58f8c37a49b341f25b8fdd6310542fe932031b8d", "resolved_from_checkout": true, "present": 31, "partial": 0, "absent": 0, "unverified": 2}, "records": 33, "refusing": [], "unverified": ["HLP-246", "HLP-247"]}
```
Standard output:
```
reconciliation validation passed: specs/001-aether-v1-productization/evidence/hermes-patch-reconciliation.v1.json, specs/001-aether-v1-productization/evidence/hermes-patch-preflight.md
```
Exit code: `0`.

### 2. Canonical check verification (`--check`)

Command:
```bash
uv run --frozen python scripts/validate_hermes_patch_reconciliation.py \
  --check \
  --fork-checkout "<clean-fork-checkout-at-58f8c37a49>" \
  --json
```

Raw JSON output:
```json
{"status": "current", "schema_version": "aether.hermes-patch-reconciliation.v1", "observed_at_utc": "2026-09-26T00:15:00Z", "selected_source": {"repository": "https://github.com/DarkArty07/aether-hermes", "revision": "58f8c37a49b341f25b8fdd6310542fe932031b8d", "resolved_from_checkout": true, "present": 31, "partial": 0, "absent": 0, "unverified": 2}, "records": 33, "refusing": [], "unverified": ["HLP-246", "HLP-247"]}
```
Standard output:
```
reconciliation validation passed: reconciliation evidence is current
```
Exit code: `0`.

### 3. Candidate check qualification (`--candidate-check`)

Command:
```bash
uv run --frozen python scripts/validate_hermes_patch_reconciliation.py \
  --candidate-check \
  --selected-revision "58f8c37a49b341f25b8fdd6310542fe932031b8d" \
  --fork-checkout "<clean-fork-checkout-at-58f8c37a49>" \
  --json
```

Raw JSON output:
```json
{"status": "qualified", "schema_version": "aether.hermes-patch-reconciliation.v1", "observed_at_utc": "2026-09-26T00:15:00Z", "selected_source": {"repository": "https://github.com/DarkArty07/aether-hermes", "revision": "58f8c37a49b341f25b8fdd6310542fe932031b8d", "resolved_from_checkout": true, "present": 31, "partial": 0, "absent": 0, "unverified": 2}, "selected_revision": "58f8c37a49b341f25b8fdd6310542fe932031b8d", "records": 33, "required_hlps": ["HLP-188", "HLP-189", "HLP-191", "HLP-194", "HLP-198", "HLP-204", "HLP-209", "HLP-211", "HLP-226", "HLP-246", "HLP-247", "HLP-262", "HLP-275", "HLP-280", "HLP-305", "HLP-310", "HLP-334", "HLP-335", "HLP-354", "HLP-362", "HLP-369", "HLP-372", "HLP-382", "HLP-385", "HLP-388", "HLP-389", "HLP-393", "HLP-420", "HLP-425", "HLP-426", "HLP-427", "HLP-428"], "deferred_hlps": [{"id": "HLP-433", "presence": "present", "missing": []}], "refusing": [], "refusing_hlps": [], "unverified": ["HLP-246", "HLP-247"]}
```
Standard output:
```
candidate qualification passed: candidate runtime satisfies required HLP coverage
```
Exit code: `0`.

Key observations from raw candidate-check JSON:
- `status`: `"qualified"`
- `required_hlps`: contains `HLP-428` alongside 31 earlier required HLPs
- `deferred_hlps`: contains `HLP-433` (`presence: "present"`, `missing: []`)
- `refusing`: `[]`
- `refusing_hlps`: `[]`

### 4. Real validator refusal matrix

Each refusal condition was exercised directly against the validator:

| Test Case | Injected Fault | Observed stderr | Exit Code | Result |
| --- | --- | --- | --- | --- |
| Wrong commit | `--selected-revision 1111111111111111111111111111111111111111` | `reconciliation validation failed: --fork-checkout HEAD 58f8c37a49b341f25b8fdd6310542fe932031b8d is not the selected revision 1111111111111111111111111111111111111111` | `2` | PASS (refused early) |
| Dirty checkout | Untracked file created in fork checkout | `reconciliation validation failed: --fork-checkout is dirty` | `2` | PASS (refused early) |
| Foreign origin | Origin remote URL changed to `https://github.com/foreign/hermes-agent` | `reconciliation validation failed: --fork-checkout origin is not the maintained fork` | `2` | PASS (refused early) |
| Missing required path | `tests/hermes_cli/test_kanban_project_provenance.py` removed from checkout | `candidate qualification failed: required HLP behavior is absent at the selected revision: HLP-428` | `2` | PASS (refused early) |

### 5. Test battery verification

Command:
```bash
uv run --frozen python scripts/run_tests.py -- tests/test_hermes_patch_reconciliation.py tests/test_lifecycle_projections.py -q
```
Result: `66 passed in 39.89s` (exit code `0`).

Command:
```bash
uv run --frozen python scripts/run_tests.py -- tests/test_hermes_patch_reconciliation.py tests/test_lifecycle_projections.py tests/test_public_artifacts.py -q
```
Result: `1 failed, 74 passed in 40.86s` (exit code `1`).
The single failure is `tests/test_public_artifacts.py::test_canonical_base_manifest_matches_tracked_non_specs_files`, which is the base-commit manifest red (472 vs 474 tracked non-specs files) explicitly assigned to and owned by concurrent unit `RC16-IDENT`.

### 6. Code quality and formatting checks

Commands:
```bash
uv run --frozen ruff check src/aether_agents tests scripts
uv run --frozen ruff format --check src/aether_agents tests scripts
git diff --check
```
Result: all checks passed cleanly; 0 formatting or whitespace defects.

## Modified surface audit

All modified files strictly match the card's declared writable surface:
- `specs/001-aether-v1-productization/evidence/hermes-patch-reconciliation/entries/HLP-428.json` (requirement -> required, disclosure added)
- `specs/001-aether-v1-productization/evidence/hermes-patch-reconciliation/entries/HLP-433.json` (components and uncertainty aligned to pin)
- `specs/001-aether-v1-productization/evidence/hermes-patch-reconciliation.v1.json` (regenerated at revision `58f8c37a49`)
- `specs/001-aether-v1-productization/evidence/hermes-patch-preflight.md` (regenerated at revision `58f8c37a49`)
- `HERMES_LOCAL_PATCHES.md` (HLP-428 candidate requirement updated)
- `tests/test_hermes_patch_reconciliation.py` (updated requirement assertion for HLP-428)
- `tests/test_lifecycle_projections.py` (updated deferred assertion in forward activation test)
- `specs/issue-494-project-provenance/evidence/RC16-HLP.md` (this evidence document)

## Remaining risks and downstream handoff

- **Manifest completion:** the base-commit manifest red in `tests/test_public_artifacts.py` is resolved by unit `RC16-IDENT`; the new evidence path `specs/issue-494-project-provenance/evidence/RC16-HLP.md` is within `specs/` and therefore does not alter the non-`specs/` manifest count.
- **Downstream dependencies:** unit `RC16-TRANS` consumes the reconciled HLP state to verify the isolated transition oracle against RC15 and candidate RC16.
- **Authority boundary:** local commits on branch `aether-agents-2/t_eef61de8-rc16-hlp-hlp-428-required-present-hlp-43`. No push, tag, release, publication, or deployment.
