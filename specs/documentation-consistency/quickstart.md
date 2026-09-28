# Verification quickstart — Aether documentation consistency

This is a runnable path for the implemented candidate, **not** a test receipt or a new quality gate. Resolve the exact Project/contract, commit and dependency environment; run from the assigned clean worktree. The baseline inspected for design is `4d60b418a19c21bacd01e503cb961d4240647f8f`, not automatically the later implementation revision.

## 1. Audit and source-bound inventory

```sh
git status --short --branch
git rev-parse HEAD
git ls-files AGENTS.md CLAUDE.md DESIGN.md ROADMAP.md README.md \
  CHANGELOG.md INTEGRATIONS.md CONTRIBUTING.md 'docs/*.md' 'docs/**/*.md' \
  'specs/*/spec.md' website/src/lib/docs.ts
```

For each disputed *current* requirement, inspect the semantic owner, active source/CLI/registry and expected test; identify historical evidence separately. The reconciliation receipt names the exact source revision and path:line, changed semantic owner and observed outcome. `docs/reference/capabilities.md` is generated from `docs/capabilities.toml` and not hand-edited.

## 2. Focused repository checks

After the relevant edits (adjust test selection only when source inspection shows the owner is unaffected):

```sh
uv run --frozen pytest -q \
  tests/test_documentation.py \
  tests/test_public_artifacts.py \
  tests/test_a1_contracts.py \
  tests/test_contract_quality_documents.py
uv run --frozen python scripts/check_documentation.py
uv run --frozen python scripts/check_public_artifacts.py
uv run --frozen ruff check tests scripts src/aether_agents
uv run --frozen ruff format --check tests scripts src/aether_agents
git diff --check
```

If the registry changes, use `uv run --frozen python scripts/check_documentation.py --write` once, review the exact generated diff and rerun the no-write check. If `AGENTS.md`/stage authority or policy changes create additional scoped tests, run their existing owners, not an invented agent campaign. A change to release/lifecycle, observation/Graphify executable code, baseline or CI policy invokes the full exact-Hermes bootstrap and other applicable CONTRIBUTING gates; a documentation-only change does not acquire an unrelated full-suite rerun by default. Never lower coverage or disable/skip a failing required check. Record genuine prerequisite skips and preexisting failures, without turning them into PASS.

## 3. Rendered documentation and site boundary

If any `docs/**` page changes, build its renderer from the same candidate revision *before* testing its generated search index; a stale `website/dist` caused a false 16-vs-20 corpus failure in #549 and passed after rebuilding. Check target storage capacity before a large build. From `website/`:

```sh
npm run check
npm run build
npm test
```

Check the source-to-rendered-page mapping and local links/search; when website application code/interaction also changes, follow `website/AGENTS.md` and its `npm run test:e2e` procedure if the executing role has that capability. Morfeo does not use browser execution. Reconcile a deleted/renamed docs slug against `website/src/lib/docs.ts` in the same change. These local checks do not prove the GitHub Pages deployment.

## 4. GitHub evidence and final stop

After independent review, compare the exact PR head/changed files with approved scope. Use normal green PR checks without admin bypass, no squash/force/history rewrite. A docs-path merge triggers the existing automatic GitHub Pages workflow **only if the owner authorized it for #552**; do not manually dispatch or use another deployment target. Verify exact merged commit and `origin/main`, required PR checks, the main-push policy run and, where triggered/authorized, Pages build+deploy with its environment/commit and public page. An absent main-run check is *unknown*, not green; #549's red main push remains red history after its corrected #550 PR. Record issue #552 and objective-owned worktree/branch cleanup only after durable verification. Then Morfeo applies `contract-result-review` against the exact final artifact; a source merge or board Done alone is insufficient.

The project graph may report no snapshot (`INDEX_MISSING`); ordinary source inspection is the honest fallback. No Graphify installation, live provider call, release candidate, runtime cutover or package publication is a documentation verification step.
