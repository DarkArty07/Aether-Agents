# DOCS — rc5 Identity, Capabilities, Lifecycle Guidance, and Policy Manifest Evidence

**Unit**: DOCS (`t_4bdae8a3`), role Implementer, worktree branch
`aether-agents-2/t_4bdae8a3-docs-rc5-identity-capabilities-lifecycle`.
**Authority**: Objective Contract `oc_a7a3cff05e82c148@v1`
(SHA-256 `ad216e2a71737fb0f324f8f3c3b2391473e0c8e7aa41077dfe1ce70ba241a588`), base commit
`e1c5f9a49d0513b1903c52368b29c4dd39033fdc`, Supervisor breakdown with shared decisions 1–10
(`specs/001-aether-v1-productization/tasks-rc5.md` at `4c4862e3`).
**Delivered scope**: contract in-scope 4; acceptance obligations AC-6 (identity/docs half),
documentation half of AC-1/AC-3; deliverable 2 and identity half of deliverable 3.
**Unit compatibility**: `patch`.

---

## 1. Summary of Changes and Attribution to Reviewed Units

All documentation, capability registry, lifecycle guidance, and policy manifest updates
faithfully reflect the frozen surfaces delivered and reviewed in predecessor units:

1. **GW-SERVICE (`9d262b2d046d44634986ce1508cc943a974e526c`)**:
   - **Hermes-owned service boundary**: Aether no longer writes or byte-owns
     `hermes-gateway-morfeo.service`, and does not include its exact bytes in projection digests.
     Fresh setup, update, rollback, and forward reactivation invoke the selected release's Hermes CLI
     (`hermes --profile morfeo gateway install --force --no-start-now --start-on-login`) to create or
     refresh the user unit before restarting it. Normal uninstall requests removal through Hermes
     (`hermes --profile morfeo gateway uninstall --profile morfeo`).
   - **Semantic doctor**: `aether doctor` validates the service exists as a regular user unit and
     semantically selects the active `runtime/current` Python, Morfeo profile and home, and active
     virtualenv, without requiring or rejecting `HERMES_TUI_DIR` or comparing incidental Hermes-owned
     unit bytes.
   - **Rollback qualification target**: Explicit rollback targets restored coherent `1.0.0rc3`
     rather than known-defective `1.0.0rc4`, followed by forward reactivation of `1.0.0rc5`.

2. **TUI-PRESERVE (`254e9973b81c33c4e8273e218bc2fe50e1f3e094`)**:
   - **Release-owned TUI preservation**: The packaged `aether` launcher continues exporting
     `HERMES_TUI_DIR=<runtime/current>/tui` to the launched Hermes process for fresh and
     `--resume latest` launches.
   - **Desktop and WSL launch actions**: Actions continue targeting the stable
     `runtime/current/venv/bin/aether` entry point with the exact initialized project root and
     hash-bound release TUI asset.
   - **Decoupling**: Gateway service operation does not depend on `HERMES_TUI_DIR`.
   - **Non-mutation**: TUI launch performs no npm/build/source mutation and leaves locked
     `hermes-source` bit-for-bit unchanged.

3. **Public rc5 Identity and Traceability**:
   - `VERSION` moved from `1.0.0rc4` to `1.0.0rc5`.
   - `CHANGELOG.md` records the `1.0.0rc5` release candidate entry: package `1.0.0rc5`, display
     `1.0.0-rc.5`, local annotated tag `v1.0.0-rc.5` never pushed; conclusions `release_impact=patch`,
     `release_action=prepare`, `release_channel=prerelease`; Hermes-owned gateway service boundary;
     preserved launcher/Desktop/WSL release-TUI delivery; rc3 rollback qualification; rc1–rc4 immutable
     history; issue #261 open.
   - `AGENTS.md` authorized objective paragraph moves to `oc_a7a3cff05e82c148@v1` with accurate
     fork pin `aed6591a...` unchanged.
   - `docs/capabilities.toml` replaces Aether-owned service projection wording with the Hermes-owned
     boundary and semantic doctor in `cli.doctor`, clarifies Hermes ownership in `cli.service-lifecycle`,
     and adds `tests/test_hermes_gateway_service.py` to verification.
   - `docs/reference/capabilities.md` regenerated via `scripts/check_documentation.py --write`.
   - `docs/guides/lifecycle.md` and `docs/reference/limitations-and-troubleshooting.md` updated to
     document Hermes service ownership and semantic doctor checks.
   - `README.md` and `docs/index.md` status and version statements updated.
   - `.github/workflows/policy.yml` registers `.aether/objective-contracts/oc_a7a3cff05e82c148/v1.md`
     and `tests/test_hermes_gateway_service.py` in the tracked non-specs manifest heredoc.
   - `tests/test_public_artifacts.py` registers `1.0.0rc5` in `ACCEPTED_PACKAGE_IDENTITIES` and updates
     README/status assertions for rc5.
   - `tests/test_release_bundle.py` asserts `1.0.0rc5` and `v1.0.0-rc.5`.
   - `tests/fixtures/observation/complete-summary.json` updates collector/reducer version to
     `1.0.0rc5` and recomputes `summary_id`.

---

## 2. Verified Test Execution and Gate Results

All commands executed in the worktree virtual environment (`uv run --frozen ...`):

| Command / Check | Result | Evidence |
| --- | --- | --- |
| `uv run --frozen python scripts/check_documentation.py` | PASS | `documentation validation passed` (registry matches CLI parser and reference markdown) |
| `uv run --frozen pytest -q tests/test_public_artifacts.py tests/test_documentation.py tests/test_release_bundle.py` | PASS | 65 passed in 7.58s (all public artifact, documentation, manifest, and bundle tests) |
| `uv run --frozen python -m unittest discover -s tests -p 'test_policy_hooks.py' -v` | PASS | 24 tests passed in 21.373s (clean policy hook execution, no forbidden mutations) |
| `uv run --frozen python scripts/check_public_artifacts.py --root .` | PASS | `public artifact path scan passed: tracked surface + 0 artifact(s)` |
| `uv run --frozen python -m compileall -q src tests scripts` | PASS | clean compilation across all Python sources |
| `uv run --frozen ruff check src/aether_agents tests scripts` | PASS | `All checks passed!` |
| `uv run --frozen ruff format --check src/aether_agents tests scripts` | PASS | `175 files already formatted` |
| `uv run --frozen mypy src/aether_agents` | PASS | `Success: no issues found in 68 source files` |
| `uv build` | PASS | built `dist/aether_agents-1.0.0rc5.tar.gz` and `dist/aether_agents-1.0.0rc5-py3-none-any.whl` |
| `git diff --check` | PASS | zero whitespace or merge conflict markers |
| `TMPDIR=/var/tmp uv run --frozen python scripts/run_tests.py` | PASS | 1871 passed, 70 skipped, 0 failed in 406.53s |

---

## 3. Truthfulness and Preservation Checks

- **No public rc5 tag/release link**: Grep for `releases/tag/v1.0.0-rc.5` confirms only negative assertions in `tests/test_public_artifacts.py`.
- **No Aether unit-byte ownership**: All references to Aether writing or byte-comparing `hermes-gateway-morfeo.service` removed from canonical documentation and capability notes.
- **No stale rc4 identity outside history**: `VERSION`, `README.md`, `docs/index.md`, `AGENTS.md`, `tests/fixtures/observation/complete-summary.json`, `tests/test_public_artifacts.py`, and `tests/test_release_bundle.py` all reflect `1.0.0rc5` / `1.0.0-rc.5`. rc4 mentions outside historical records exist only in `CHANGELOG.md` history and explicit backward-compatibility tests.
- **Preserved surfaces**: `src/aether_agents/**` (including `lifecycle.py` and `launcher.py`), `tests/test_lifecycle_projections.py`, `tests/test_tui_projections.py`, `tests/test_aether_tui_launcher.py`, and the canonical contract were untouched by this unit.

---

## 4. Residual Risks and Handoff

- **Downstream integration**: Merged commits from GW-SERVICE (`9d262b2d...`) and TUI-PRESERVE (`254e9973...`) are integrated into this worktree. Downstream Supervisor units INT (`t_f5ab4cf3`) and CLOSE (`t_fbc979fd`) will carry forward the combined candidate tree for final PR integration and local activation.
- **Local-only candidate**: Annotated tag `v1.0.0-rc.5` remains local-only. Issue #261 remains open for stable/PyPI/WSL2 gates.
