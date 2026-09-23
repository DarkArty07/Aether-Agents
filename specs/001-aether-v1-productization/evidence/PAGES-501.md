# PAGES-501 — Website Docs Map Repair Evidence

**Unit**: `PAGES-501-MAP` (`t_c2fd26dc`), role Implementer, worktree branch
`aether-agents-2/t_c2fd26dc-pages-501-map-describe-both-missing-cano`.
**Authority**: Objective Contract `oc_ce1f17ebbb4968b4@v1`
(SHA-256 `d4812b5ba1fd8c36663f3f8a24453ff48f42fabdc4c54cc9da1225a7ad49ebee`), base commit
`1b0d3a36d98e29125191798a5edf867b1c4097ce`, Supervisor breakdown with shared decisions 1–10
(`specs/001-aether-v1-productization/tasks-501.md` at `ee4db72cb5643955851226eb18bc45b13a4bc0fa`).
Never edited, staged, or re-finalized the canonical contract.
**Delivered scope**: AC1, AC2, and AC3 (implementation half); related Issue `#501`.
**Unit compatibility conclusion**: `patch` (content correction to website documentation map).

---

## 1. Summary of Changes and Changed-File List

The implementation unit repairs the docs description map in `website/src/lib/docs.ts` by adding
curated Spanish entries for the two missing canonical guides in their contract-decided reading-order
positions.

### Changed files

- `website/src/lib/docs.ts`: inserted `'guides/objective-plans'` and `'guides/morfeo-tool-configuration'`
  into the `descriptions` map object literal.
- `specs/001-aether-v1-productization/evidence/PAGES-501.md`: this unit evidence artifact.

### Preserved files

- `website/tests/content.test.mjs` remains byte-untouched and unchanged; the bidirectional oracle
  passes against the corrected map without any modification to the test.
- `website/package.json` and `website/package-lock.json` are unchanged.
- All documentation sources in `docs/` and workflow definitions remain untouched.

---

## 2. Defect Reproduction at Base

Prior to modification, the defect was independently reproduced at base commit `1b0d3a36`:

1. **Corpus vs. Map computation**:
   - Tracked Markdown documents: `git ls-files -- docs | grep '\.md$'` yielded exactly 19 documents.
   - Existing keys in `website/src/lib/docs.ts`: 17 keys.
   - Missing keys: `guides/objective-plans` and `guides/morfeo-tool-configuration`.
2. **Oracle failure**:
   - Command: `npm test` from `website/`.
   - Result: 19 passed, 1 failed (19/20).
   - Failing test: `tests/content.test.mjs:163:1` (`documentation is rendered, linked to revision and searchable`).
   - Assertion error: `src/lib/docs.ts must describe every canonical document and nothing else`, with
     the diff showing missing `guides/morfeo-tool-configuration` and `guides/objective-plans`.
3. **Title fallback at base**:
   - In built `dist/docs/search.json`, both missing guides had fallback descriptions matching their
     titles (`Tool selection by role` and `Objective Plans and continuity`), and because their slugs
     were missing from `descriptions`, `order.indexOf(slug)` evaluated to `-1`, sorting them ahead
     of all described documents.

---

## 3. Decided Positions and Truthful Spanish Descriptions

The two entries were placed in the decided reading-order positions stamped by the Supervisor breakdown,
using Mexican Spanish descriptions strictly truthful to the canonical text of each guide, and
satisfying the oracle's syntax constraint (`^\s*'([^']+)':\s*'([^']+)',$` without straight apostrophes):

1. **`guides/objective-plans`**:
   - **Position**: immediately after `'guides/project-initialization'` and before `'guides/objective-contracts'`,
     matching `docs/index.md` lines 51–55 where Objective Plans lead the objective handoff section.
   - **Entry**: `'guides/objective-plans': 'Ruta y continuidad de objetivos entre sesiones y contratos.',`
   - **Grounding in guide text**: `docs/guides/objective-plans.md` lines 3–5 ("An Objective Plan helps
     Morfeo conduct one owner's objective across sessions and, when needed, multiple Objective Contracts.
     It is a working record, not another contract, task board or authority.") and line 25 ("Use it when
     the work needs a meaningful route, spans contracts or must continue in another session.").
2. **`guides/morfeo-tool-configuration`**:
   - **Position**: immediately after `'guides/policy-and-recovery'` and before `'reference/cli'`,
     at the end of operational guides before the reference section.
   - **Entry**: `'guides/morfeo-tool-configuration': 'Selección local de herramientas por rol, sus motivos y límites.',`
   - **Grounding in guide text**: `docs/guides/morfeo-tool-configuration.md` lines 5–10 ("This guide records
     an owner-selected operating recipe for Morfeo, Supervisor, and Implementer, including the reasons
     behind it. It is a reusable reference, not a mandatory product preset...") and line 22 ("Users can
     adapt local tool selection to their needs within existing role and safety boundaries.").

---

## 4. Verification and Observed Gate Results

All commands were executed in the repository and website workspace with observed outputs recorded below:

### Website gates (`website/`)

1. **Clean dependency installation**:
   - Command: `npm ci --include=dev --include=optional`
   - Result: added 320 packages, audited 321 packages, 0 vulnerabilities (exit code 0).
2. **Astro build**:
   - Command: `npm run build`
   - Result: 23 page(s) built in 1.30s (exit code 0).
   - Built routes include `/docs/guides/objective-plans/index.html` and
     `/docs/guides/morfeo-tool-configuration/index.html`.
3. **Astro type check**:
   - Command: `npm run check`
   - Result: 32 files checked, 0 errors, 0 warnings, 0 hints (exit code 0).
4. **Unit and content test suite**:
   - Command: `npm test`
   - Result: 20 passed, 0 failed (20/20 PASS) in 1.21s (exit code 0).
   - Subtest 18 (`documentation is rendered, linked to revision and searchable`) passed without changes
     to `tests/content.test.mjs`.
5. **Browser E2E test suite**:
   - Command: `npm run test:e2e`
   - Result: 38 passed across desktop + mobile Chromium in 1.4m (exit code 0).
   - Real Playwright execution on host; all visual, navigation, history, and accessibility tests green.
6. **Search index and reading order verification**:
   - Verified in `dist/docs/search.json`:
     - Index length: 19 records (matches the 19 canonical documents).
     - Slug `guides/objective-plans` has description: `Ruta y continuidad de objetivos entre sesiones y contratos.`.
     - Slug `guides/morfeo-tool-configuration` has description: `Selección local de herramientas por rol, sus motivos y límites.`.
     - Position order: `index` (0) -> `getting-started` (1) -> `product-boundary` (2) -> `roles-and-authority` (3) -> `authority` (4) -> `guides/project-initialization` (5) -> `guides/objective-plans` (6) -> `guides/objective-contracts` (7) -> `guides/execution` (8) -> `guides/lifecycle` (9) -> `guides/project-knowledge` (10) -> `guides/observation` (11) -> `guides/telegram-monitor` (12) -> `guides/policy-and-recovery` (13) -> `guides/morfeo-tool-configuration` (14) -> `reference/cli` (15) -> `reference/plugins-and-tools` (16) -> `reference/capabilities` (17) -> `reference/limitations-and-troubleshooting` (18).
   - Verified in `dist/docs/index.html`:
     - Navigation and index links render both guides in their decided positions.

### Repository controls (from repository root)

1. **Whitespace and patch check**:
   - Command: `git diff --check`
   - Result: clean, exit code 0.
2. **Documentation check**:
   - Command: `uv run --frozen python scripts/check_documentation.py`
   - Result: `documentation validation passed`, exit code 0.
3. **Public artifact scan**:
   - Command: `uv run --frozen python scripts/check_public_artifacts.py --root .`
   - Result: `public artifact path scan passed: tracked surface + 0 artifact(s)`, exit code 0.
4. **Pytest suite (public artifacts and documentation)**:
   - Command: `uv run --frozen python scripts/run_tests.py -- tests/test_public_artifacts.py tests/test_documentation.py -q`
   - Result: 27 passed in 3.04s, exit code 0.

---

## 5. Environment and Operational Bounds

- Host environment: Linux (WSL2), Node `22.23.2`, npm `10.9.8`, uv `0.12.15`, Python `3.13.15`.
- Browser runner: Playwright with bundled Chromium headless shell.
- Publication boundary preserved: Implementer commits locally only on the unit branch.
  No git push, pull request creation, merge, deployment, or issue state mutation was performed.
  All integration and terminal verification actions remain assigned to Supervisor unit `PAGES-501-INT`.
