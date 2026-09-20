# LG-DOCS — rc4 identity, docs, capabilities, policy

**Authority.** Objective Contract `oc_ff82ba151cdf3861@v2` (SHA-256
`e5c4fea02a5b1cee977c93a602d5af622b59e7325c9efb3be7d7b1e7bfc49bd0`), in-scope item 5;
acceptance obligations AC-9 (documentation and public artifacts) and AC-10 (identity);
issues #480, #481, #482; breakdown unit LG-DOCS from
`specs/001-aether-v1-productization/tasks-rc4.md` at `155c67ea`.

**Base.** Board `worktree_base_ref` = commit `00715d237d795e365c5e462b6b80d5a1bd8d8188`.
Worktree branch `aether-agents-2/t_555db066-lg-docs-rc4-identity-docs-capabilities-p`.
Following the Supervisor worktree directive, the independently reviewed parent units
were integrated prior to identity, documentation, and policy changes:
- **LG-CLI** (`t_7fab49b1`): commit `d9f801573e8a496f69714431296b784c3b86ac82`
  (packaged launcher `src/aether_agents/launcher.py`, exact project binding, `--json` plan)
- **LG-LIFE** (`t_3c6f6528`): commit `711b1962e3c051dd9a9f3d9147f80f48bbfe8bc1`
  (release-owned TUI, branded projections, `tests/test_tui_projections.py`)
- **LG-KNOW** (`t_8b46a2e8`): commit `160abe6c4b1fc6e5adb2db084447602b2417ce20`
  (operation-wide 300s Graphify deadline from `KnowledgeStore.update()` to pointer publication)

**Unit compatibility.** `patch` (metadata, documentation, test oracles, and policy manifest registration; no product API removed).

## 1. What changed

1. **Product Version (`VERSION`)**:
   - Updated from `1.0.0rc3` to `1.0.0rc4` as the single product-version source.

2. **Public Portal & Documentation Status (`README.md`, `AGENTS.md`, `docs/index.md`)**:
   - `README.md`: Status paragraph updated to state the owner-authorized `1.0.0rc4` candidate, package version `1.0.0rc4`, display `1.0.0-rc.4`, local-only annotated tag `v1.0.0-rc.4` (not pushed and not published), `release_impact = patch`, `release_action = prepare`, `release_channel = prerelease`. Predecessors rc.2 and rc.3 remain immutable non-accepting history; `v1.0.0-rc.1` remains published, immutable, and rejected. Standing non-claims preserved (not stable `1.0.0`, not PyPI, not WSL2 qualified, issue #261 open).
   - `AGENTS.md`: Reconciled authorized bounded objective to `1.0.0rc4` under `oc_ff82ba151cdf3861@v2` with `release_impact=patch`, `release_action=prepare`, `release_channel=prerelease`. Fork pin `aed6591a69f453a1867b73628603e7b53ba40ffc` unchanged; rc.2 and rc.3 history immutable.
   - `docs/index.md`: Updated reference to local-only `1.0.0rc4` candidate.

3. **Changelog (`CHANGELOG.md`)**:
   - Added `## 1.0.0rc4` entry documenting the packaged launcher (#480), release-owned TUI and branded projections (#480, #481), operation-wide 300s Graphify deadline (#482), manifest registration of contract v1/v2 and new unit paths, and standing non-claims. Predecessor entries remain immutable and byte-unchanged.

4. **Capability Registry & Reference (`docs/capabilities.toml`, `docs/reference/capabilities.md`)**:
   - `docs/capabilities.toml`:
     - `cli.aether-launch`: Updated status to `implemented`, summary and notes reflect packaged project-aware launcher (`src/aether_agents/launcher.py`), non-mutating `--json` launch plan, reserved-flag refusal, and `--resume latest` passthrough.
     - `knowledge.shared-project-graph`: Updated notes to reflect operation-wide 300s monotonic deadline from `KnowledgeStore.update()` entry through pointer publication, shared cancellation across prepare/validate/compose, and partial receipt with deadline attribution.
   - `docs/reference/capabilities.md`: Regenerated via `python scripts/check_documentation.py --write`.

5. **CLI & Guide Documentation**:
   - `docs/reference/cli.md`: Updated top-level `aether [--project PATH] [--json]` documentation to reflect the packaged launcher, exact project binding, non-mutating JSON plan with 9 sorted keys, reserved argument rejection, `--resume` passthrough, and operation-wide 300s Graphify budget.
   - `docs/getting-started.md`: Documents `aether [--project PATH] --json` non-mutating launch plan from packaged manager code.
   - `docs/guides/lifecycle.md`: Documents release-owned TUI asset layout (`runtime/current/tui`), branded desktop/terminal projections (`Aether`, `Continue Aether`), and fail-closed doctor checks.
   - `docs/guides/project-knowledge.md`: Documents authoritative 300s monotonic deadline from `KnowledgeStore.update()` entry to pointer publication, shared cancellation across prepare/validate/compose, post-call fences, host cancel `OPERATION_CANCELLED`, and partial receipts with deadline attribution.

6. **Policy Manifest (`.github/workflows/policy.yml`)**:
   - Registered 4 newly tracked non-`specs/` files in the expected manifest heredoc:
     - `.aether/objective-contracts/oc_ff82ba151cdf3861/v1.md`
     - `.aether/objective-contracts/oc_ff82ba151cdf3861/v2.md`
     - `src/aether_agents/launcher.py` (from LG-CLI)
     - `tests/test_tui_projections.py` (from LG-LIFE)
   - Expected count (426) exactly matches `git ls-files | grep -v '^specs/'` (426).

7. **Coupled Test Oracles**:
   - `tests/test_public_artifacts.py`: Added `"1.0.0rc4"` to `ACCEPTED_PACKAGE_IDENTITIES`; updated README status assertions for rc.4 identity, patch impact, and immutable rc.2/rc.3 history.
   - `tests/test_release_bundle.py`: Updated `test_version_file_carries_the_objective_release_identity` to expect `1.0.0rc4` / `v1.0.0-rc.4`.
   - `tests/fixtures/observation/complete-summary.json`: Regenerated the 3 version-derived lines (`collector_version: 1.0.0rc4`, `reducer_version: aether.observation.reducer.v1+1.0.0rc4`, `summary_id: sum_8a30e407100fd2c7bd5fe93f088767d6096b0e4c550a16896ebb92cb12c5c08d`).
   - `tests/test_observation_reducer.py`: Pre-condition `canonical_digest(verification) < canonical_digest(forged)` verified: candidate `implementer-1` immediately satisfies the condition under `1.0.0rc4`, requiring no test edits.

## 2. Tracked file manifest

Modified tracked paths:
- `.github/workflows/policy.yml`
- `AGENTS.md`
- `CHANGELOG.md`
- `README.md`
- `VERSION`
- `docs/capabilities.toml`
- `docs/getting-started.md`
- `docs/guides/lifecycle.md`
- `docs/guides/project-knowledge.md`
- `docs/index.md`
- `docs/reference/capabilities.md`
- `docs/reference/cli.md`
- `tests/fixtures/observation/complete-summary.json`
- `tests/test_public_artifacts.py`
- `tests/test_release_bundle.py`

New tracked path:
- `specs/001-aether-v1-productization/evidence/LG-DOCS.md` (this file)

Preserved boundaries:
- Implementation modules (preserved; no code edits outside launcher/lifecycle/knowledge delivered by parent units)
- `.aether/objective-contracts/oc_ff82ba151cdf3861/v2.md` (never created, edited, staged, or copied)
- No push, PR, merge, tag, activation, or issue mutation.

## 3. Verification evidence

| Check | Command | Observed result |
|---|---|---|
| Linter | `uv run --frozen ruff check src/aether_agents tests scripts` | All checks passed! (exit 0) |
| Formatter | `uv run --frozen ruff format --check src/aether_agents tests scripts` | 173 files already formatted (exit 0) |
| Type check | `uv run --frozen mypy src/aether_agents` | Success: no issues found in 68 source files (exit 0) |
| Doc validation | `uv run --frozen python scripts/check_documentation.py` | documentation validation passed (exit 0) |
| Public scan | `uv run --frozen python scripts/check_public_artifacts.py --root .` | public artifact path scan passed: tracked surface + 0 artifact(s) (exit 0) |
| Policy manifest | `diff -u <(sort expected) <(git ls-files \| grep -v '^specs/' \| sort)` | Exact match: 426 files = 426 expected (exit 0) |
| Artifact tests | `uv run --frozen pytest -q tests/test_public_artifacts.py` | 9 passed in 1.45s (exit 0) |
| Bundle tests | `uv run --frozen pytest -q tests/test_release_bundle.py` | 38 passed in 5.11s (exit 0) |
| Doc tests | `uv run --frozen pytest -q tests/test_documentation.py` | 18 passed in 0.75s (exit 0) |
| Reducer tests | `uv run --frozen pytest -q tests/test_observation_reducer.py` | 128 passed in 1.73s (exit 0) |
| Launcher tests | `uv run --frozen pytest -q tests/test_aether_tui_launcher.py` | 23 passed, 9 subtests passed in 2.97s (exit 0) |
| Projection tests | `uv run --frozen pytest -q tests/test_tui_projections.py` | 20 passed in 3.43s (exit 0) |
| Semantic tests | `uv run --frozen python scripts/run_tests.py -- tests/test_knowledge_semantic_manager.py` | 21 passed in 2.44s (exit 0) |
| Wheel build | `uv build` | Successfully built `dist/aether_agents-1.0.0rc4.tar.gz` and `dist/aether_agents-1.0.0rc4-py3-none-any.whl` (exit 0) |
