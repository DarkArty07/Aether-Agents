# RC2-E2E-ORACLE Implementation Evidence — derive the website E2E docs-count oracle from the canonical corpus

**Unit:** RC2-E2E-ORACLE-FIX (task `t_5901d6cb`)
**Objective Contract:** `oc_742f9f4797494bf9@v1` (SHA-256 `f084eca7e703201c620408069df8f06b89cade82514ceb934c792f71bdda04fc`)
**Source:** card `t_5901d6cb` required change 1; owner disposition on issue [#446](https://github.com/DarkArty07/Aether-Agents/issues/446) ("Reopened: required E2E oracle remains stale on the merged rc.2 source", 2026-09-16T00:55:21Z); landed predecessor derivation `website/tests/content.test.mjs:154-161` (commits `ee5dc3d2`, `1ef647b7`)
**Base:** `acb89ca85c02c41dca10009b2806428850a0f0bc` (`git rev-parse HEAD` on a clean worktree before editing; `git status --porcelain` empty)
**Branch:** `aether-agents-2/t_5901d6cb-rc2-e2e-oracle-fix-derive-the-website-e2`
**Candidate:** the single commit above the base (`git log --format=%H acb89ca8..HEAD`); the modified spec file is byte-identical to the revision these runs measured, SHA-256 `c3eff3830db2d7c703d28a5dcabb254100856a02d485f2f6261f5508436a0fdb`
**Phase:** Implementer unit; **no live effect performed** — no push, PR, merge, tag, release, dispatch, deploy, activation, issue mutation, settings or workflow change. All scratch state is disposable (`/tmp/t_5901d6cb`, `test-results/`, `playwright-report/`).
**Unit compatibility impact:** `patch` — one test file, one derivation replacing one literal. No product surface, source, configuration, workflow, docs corpus or shared interface change. Aggregate `release_impact`/`release_action`/`release_channel` remain the integration lane's conclusion.
**Review lane:** same-card Supervisor review (`kanban_request_review`, reviewer `supervisor`).

---

## 1. RED facts reproduced on the unchanged base

Reproduced before any edit, with the base tree still intact (only the two ignored build directories generated).

| # | Observation | Command | Result |
| --- | --- | --- | --- |
| R1 | focused E2E RED, both projects, at `website/tests/browser/site.spec.ts:91` | `npx playwright test tests/browser/site.spec.ts -g "documentation search"` | `2 failed` — `[desktop]` and `[mobile]` both `documentation search, navigation and safe rendering` |
| R2 | full E2E RED on the same base | `npm run test:e2e` | `2 failed / 36 passed (2.2m)` — both failures the same test as R1 |
| R3 | corpus measurement | `git ls-files -- docs` (`18` tracked rows, `17` with `.md`) | corpus holds **17** canonical documents |
| R4 | rendered article measurement on the same base | `grep -o 'data-document=' dist/docs/index.html \| wc -l` after `npm run build` | **17** |

Exact failure message of R1, identical in both projects except the projector prefix (verbatim from the run):

```
Error: expect(locator).toHaveCount(expected) failed

Locator:  locator('.docs-index-list article:visible')
Expected: 16
Received: 17
Timeout:  5000ms

Call log:
  - Expect "toHaveCount" locator('.docs-index-list article:visible') with timeout 5000ms
  - waiting for locator('.docs-index-list article:visible')
    14 × locator resolved to 17 elements
       - unexpected value "17"

  89 |   await expect(page.locator('#no-results')).toBeVisible();
  90 |   await page.locator('#docs-search').fill('');
> 91 |   await expect(page.locator('.docs-index-list article:visible')).toHaveCount(16);
     |                                                                  ^
  92 |   await page.locator('.docs-index-list [href="/docs/guides/project-knowledge/"]').click();
```

This matches the card's statement (16 pinned vs 17 tracked, failing at that line) exactly.

### 1.1 The derivation rule the site actually uses (read, not assumed)

- `website/src/lib/docs.ts` enumerates `docs/**` recursively, keeps only paths present in `git ls-files -- docs` ("the tracked public corpus only"), derives each slug as the repository-relative path minus `docs/` and `.md`, and renders one entry per document.
- `website/src/pages/docs/index.astro:18` emits exactly one `<article data-document={slug}>` per document inside `.docs-index-list`, so the visible-article count and the tracked-document count are the same quantity by construction.
- The landed predecessor fix derives its expectation from the same rule through Git (`website/tests/content.test.mjs:154-161`); this unit applies that reference derivation to the E2E oracle instead of re-pinning a literal.

## 2. The change (derivation, not a new literal)

`website/tests/browser/site.spec.ts` — `12 insertions(+), 1 deletion(-)`:

- added `import { execFileSync } from 'node:child_process';`
- added the corpus derivation above the affected test, mirroring `content.test.mjs` (`git rev-parse --show-toplevel`, then `git ls-files -- docs` → keep `.md` → strip `docs/` and `.md` → sort):
  `const repository = execFileSync('git',['rev-parse','--show-toplevel'],{encoding:'utf8'}).trim();`
  `const canonicalDocSlugs = execFileSync('git',['ls-files','--','docs'],{cwd:repository,encoding:'utf8'}).trim().split('\n').filter(file=>file.endsWith('.md')).map(file=>file.replace(/^docs\//,'').replace(/\.md$/,'')).sort();`
- replaced `toHaveCount(16)` with `toHaveCount(canonicalDocSlugs.length)`.

**16 was not replaced by 17**, and no literal document count remains in the website tests (class scan in §5).

Every behavioural assertion around the oracle is untouched, verified by the diff hunks themselves and by the GREEN runs:

- the `guides/project-knowledge` search hit (`#docs-search` filled with `Graphify`) and its `toBeVisible()` assertion;
- the `zzznomatchzzz` no-results state (`#no-results` `toBeVisible()`);
- the navigation and heading assertion (click through to `/docs/guides/project-knowledge/`, `.prose h1` contains `Project knowledge`);
- the horizontal-overflow check and the console-error check (`errors == []`);
- the rest of the file (8 sections, artwork, reduced motion, illustrations, language switch, accessibility, skip link/local requests) is byte-unchanged, and `history.spec.ts`/`atmosphere.spec.ts`/`polish.spec.ts` are untouched.

No test was renamed, deleted, skipped, reordered or bypassed: the full E2E battery grows from `36 passed + 2 failed` to `38 passed`, i.e. the same 38 cases with the two previously failing ones green.

## 3. GREEN

| # | Observation | Command | Result |
| --- | --- | --- | --- |
| G1 | focused GREEN, post-change | `npx playwright test tests/browser/site.spec.ts -g "documentation search"` | `2 passed (3.9s)` — `[mobile]` 819ms, `[desktop]` 1.0s (test now at `site.spec.ts:94`) |
| G2 | full E2E GREEN | `npm run test:e2e` | `38 passed (1.5m)`, exit 0 |

### 3.1 Non-vacuity probe (the oracle still compares a live derived value)

A derived expectation is only worth the comparison it drives, so the assertion was probed before being accepted:

1. the GREEN revision was snapshotted (`sha256 c3eff383…`), then the expectation was locally perturbed to `canonicalDocSlugs.length+1`;
2. `npx playwright test tests/browser/site.spec.ts -g "documentation search"` → `2 failed`, both projects: `Expected: 18`, `Received: 17`, `14 × locator resolved to 17 elements` — the derived number reaches the assertion and the assertion still discriminates;
3. the file was restored and confirmed byte-identical to the snapshot (`sha256sum` equality and `diff` empty, both re-run), after which the complete battery in §4 was executed on the restored revision.

Scratch copies of every raw log live under `/tmp/t_5901d6cb/` (disposable, not committed): `red-focused.log`, `red-e2e-full.log`, `green-focused.log`, `probe-nonvacuity.log`, `npm-ci.log`, `check.log`, `build-local.log`, `test-content.log`, `e2e.log`, `build-pages.log`, `verify-pages.log`.

## 4. Complete website battery on the candidate revision

Run from `website/`, in the card's order, on the restored candidate (spec SHA-256 `c3eff383…`, base `acb89ca8`):

| Command | Exit | Observed |
| --- | --- | --- |
| `npm ci` | 0 | `added 320 packages, and audited 321 packages`, `found 0 vulnerabilities` |
| `npm run check` | 0 | `Result (32 files): 0 errors, 0 warnings, 0 hints` |
| `npm run build` (local-path candidate) | 0 | `21 page(s) built` |
| `npm test` | 0 | `# tests 20 / # pass 20 / # fail 0 / # skipped 0` |
| `npm run test:e2e` | 0 | `38 passed (1.5m)` (was `2 failed / 36 passed` on the base, §1 R2) |
| `AETHER_PAGES=1 npm run build` | 0 | `21 page(s) built` |
| `node scripts/verify-pages-build.mjs` | 0 | `GitHub Pages base-path verification passed for 21 HTML pages.` |

The E2E step ran against the local-path build exactly as the repository's own order prescribes; the `AETHER_PAGES=1` build and its path verification ran afterwards, so the Pages artefact was verified without being the server root for the browser battery.

## 5. Touched set, class scan and resource pre-check

**Touched set** (`git status --porcelain` / `git diff --numstat` before committing the record):

```
 M website/tests/browser/site.spec.ts
12	1	website/tests/browser/site.spec.ts
```

and this record, `specs/001-aether-v1-productization/evidence/RC2-E2E-ORACLE.md`. Nothing else: no `docs/**`, no other `website/**` file, no `.github/workflows/**`, no other objective's artifact, no rc.1/rc.2 byte. Ignored build output (`node_modules/`, `dist/`, `test-results/`, `playwright-report/`) is not part of the touched set.

**Same-class scan for the residual literal** (read-only): `grep -rn "toHaveCount([0-9]" website/tests website/src` finds only unrelated design constants — `site.spec.ts` sections `8` and team packets `3`, `polish.spec.ts` clock hours `24` and hands `2`; `grep -rn "\b17\b" website/tests` finds no literal at all. The docs count is now derived everywhere in the website surface.

**Resource pre-check** (measured before the battery, card's resource boundary is the single 12-CPU host):

| Resource | Value |
| --- | --- |
| CPU | 12 logical CPUs, `nproc` |
| Memory | `MemTotal 32131 MiB`, `available 5699 MiB` at start (5140 MiB after the battery); swap untouched |
| Disk | `/home` 8.6 GiB free (93% used), `/tmp` tmpfs 7.2 GiB free |
| Browser binaries | `~/.cache/ms-playwright` already holds `chromium-1243` / `chromium_headless_shell-1243` / `ffmpeg-1011` (658 MB) — no download, no network fetch |
| Toolchain | `git 2.55.0`, `node v22.23.2`, `npm 10.9.8` (satisfies `engines.node >=22.12.0`) |

The battery is CPU- and memory-modest (2 Playwright workers, no service, no network beyond localhost), and ran with ~5 GiB available while the host carried other work; no OOM, timeout or retry occurred in the final battery.

## 6. Deliberate boundary delta recorded during the unit

Mid-run peer evidence (worker, delivered while the battery executed) withdrew the sentence in the card's SHARED DECISIONS that claimed owner authorization for a further automatic Pages deployment, stating that only PR #452's already-completed `ee5dc3d`/`1ef647b`/`0144dfe` deployment is authorized, and instructed: finish the running local candidate, evidence and same-card review only. Disposition: **consumed as a narrowing of the boundary, not as new acceptance.** Nothing in this unit depended on that authorization — this role performs no push, PR, merge, dispatch or deploy in any reading — so the deliverable is unchanged; the local candidate is preserved after review, and no remote, issue or deployment action was taken.

## 7. What was NOT verified

- **No remote or live effect.** GitHub Pages' own workflow run, the deployed public site and the automatic deployment path caused by the integration lane are unverified here — that leg belongs to integration, not to this card. Nothing was pushed.
- **Corpus drift was not demonstrated end-to-end.** The derivation rule was read in `src/lib/docs.ts`/`docs/index.astro`, evaluated independently (`git ls-files -- docs` → 17 slugs printed), and the comparison it feeds was probed (§3.1), but I did not add, rename or remove a document to watch the oracle follow it, because `docs/**` is outside this unit's writable surface. A reviewer wanting that observation must grant corpus write access or run it on a disposable copy of the repository; the rule it would validate is already pinned by `content.test.mjs:154-176`.
- **The Python/Aether contract suites, the release gates and the fork pin were not run.** The card's evidence list defines the website battery; `uv`-based suites, `release.yml`/`policy.yml` verification, and the maintained-fork revision `7a4fdcd0…` are other lanes' evidence.
- **`npm run test:e2e` was not run against the `AETHER_PAGES=1` artefact** (the Pages build ran after the E2E step, per the repository's own order). No assertion in this unit depends on base-path rendering.
- **No engine cross-check.** Only the repository's pinned browser projects (`desktop` Chrome, `mobile` Pixel 7) were exercised, as before the change.
- **Prerelease/published bytes untouched.** rc.1 and the published rc.2 bytes were read-only for this unit and were not re-verified.
