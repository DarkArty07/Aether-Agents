# LC-FIX-WEBSITE — Website Pages content oracle must match the canonical docs corpus (#446)

Unit of Objective Contract `oc_3397f9f05d780f8e@v1` (base `410c172ae69ffa87f6e32960ae4aef3b8d6598f0`).
Owning public-surface issue: [#446](https://github.com/DarkArty07/Aether-Agents/issues/446) (OPEN at time of writing).

## 1. The defect

`Website Pages` was red at the release revision `748aa24ce5684185f65aa88b0e85919627ff6538`
(run `34972975522`), failing at the step `Test content and links`:

```
website/tests/content.test.mjs:156
  assert.equal(index.length,16);
```

The site renders every tracked canonical document under `docs/`; the corpus holds **17**. The
oracle pinned a literal that had silently stopped matching reality.

## 2. Root cause and attribution

- The literal entered with `312d964` while the corpus held exactly 16 documents.
- The 17th document, `docs/guides/telegram-monitor.md`, entered with `2209cb8` — an ancestor of
  the *old* `main`, and **not** part of this objective. The card's original attribution to
  `59a0c8f` was corrected by the unit and re-confirmed by review.
- Two consequences followed from the same cause: the count drifted, and `src/lib/docs.ts` — which
  is at once the description map and the reading order — did not describe the new document, so its
  search result rendered with the title as its description and sorted ahead of every described
  document.

## 3. Candidate identity

Branch `aether-agents-2/t_a18b5fc7-lc-fix-website-pages-content-oracle-must`:

| Commit | Subject |
| --- | --- |
| `ee5dc3d` | `fix(website): derive the docs search-index oracle from the canonical corpus` |
| `1ef647b` | `fix(website): describe every canonical document in the docs order map` |
| `0144dfe` | `docs(website): reconcile workstream guidance with objective authority` |

Independent-review HEAD before landing: `0144dfee4c5ab21c60051cddb83716c121e4f5e2`
(`website/src/lib/docs.ts` sha256 `4998fa4eb4db00c517eefc5d7ee233585821955a6afd25379cd9abece1d699fb`).
The branch was then synced with `main` by merge (no rebase; the commits are already reviewed) and
re-gated before landing.

## 4. What changed

1. `website/tests/content.test.mjs` — the fixed count is replaced by an expectation derived from
   the repository through Git (`git ls-files -- docs` → slug set), asserted as an exact sorted-slug
   equality, plus bidirectional equality between the `src/lib/docs.ts` description map and the
   corpus, plus a per-entry check that each search result carries the mapped description rather
   than the title fallback. `index.length` is still asserted; the neighbouring `Graphify`,
   execution-guide heading, revision-link and `.docs-sidebar` assertions are unchanged.
2. `website/src/lib/docs.ts` — adds the missing `guides/telegram-monitor` description at its
   coherent `guides/*` position. One line.
3. `website/AGENTS.md` — workstream guidance reconciled with the objective authority: the
   workstream still performs no deployment and no runtime activation and Implementer still never
   publishes, while recording that an owner-authorized Supervisor merge of a `website/` or `docs/`
   change may trigger the repository's own Pages workflow, and that the run is then observed and
   verified rather than assumed.
4. `website/VERIFICATION.md` — the unit's website-side evidence record, with the Supervisor review
   outcome appended under its own attribution.

## 5. Independent verification (Supervisor same-card review, run 285)

Executed on the merged tree, in the Pages workflow's own step order:

| Step | Command | Result |
| --- | --- | --- |
| Check Astro | `npm run check` | rc 0 — 0 errors, 0 warnings, 0 hints (32 files) |
| Build local-path candidate | `npm run build` | rc 0 — 21 pages |
| Test content and links | `npm test` | rc 0 — `# tests 20 / # pass 20 / # fail 0 / # skipped 0` |
| Build GitHub Pages artifact | `AETHER_PAGES=1 npm run build` | rc 0 — 21 pages |
| Verify GitHub Pages paths | `node scripts/verify-pages-build.mjs` | rc 0 — "GitHub Pages base-path verification passed for 21 HTML pages" |

Deployed-artifact content, read from the `AETHER_PAGES=1` build: `docs/search.json` holds **17**
entries, `guides/telegram-monitor` carries the mapped description
`Reportes horarios de progreso y límites del monitor de Telegram.` at position 11, and entries
whose description falls back to the title are **0**.

### 5.1 Negative controls (the oracle must catch the drift class, not just today's number)

Run on the exact committed candidate; the tree was restored byte-exactly after each (docs.ts
sha256 and `git status` re-checked):

- **Remove the map entry** (`guides/telegram-monitor` deleted from `docs.ts`): build rc 0,
  `npm test` **rc 1**, `not ok 18 — documentation is rendered, linked to revision and searchable`,
  reason `src/lib/docs.ts must describe every canonical document and nothing else` (19 pass / 1 fail).
- **Stage one new canonical document** (`docs/guides/zz-control-drift.md`, corpus 17 → 18): build
  rc 0, `npm test` **rc 1** with the same assertion — i.e. the repair catches a *newly entering*
  document, which is exactly the class that broke CI. Control removed; corpus returned to 17.

`website/package-lock.json` and `website/package.json` are unchanged against `main`, so the
workflow's `npm ci` step is unaffected by this unit.

## 6. Landing authority and the Pages consequence

The owner decision (board comments of 2026-09-15) authorizes the existing automatic GitHub Pages
deployment for **this exact #446 correction only**, as the consequence of a normal reviewed green
merge — no manual dispatch, no settings/workflow change, no bypass, no alternate target. An earlier
authorization had been revoked and is superseded by that decision.

Sequencing fact recorded at review time: the documentation correction previously landed in
`README.md`/`CHANGELOG.md`/`docs/**` (#449) touched the workflow's path filter, so `Website Pages`
ran and failed at `Test content and links` with the Pages build, path verification, configuration
and the `deploy` job all skipped — no public mutation occurred from that earlier merge.

## 7. Non-claims

- The candidate is reviewed and accepted locally; at the time of writing this record the branch is
  not yet pushed, merged or deployed, and `#446` is **not** closed.
- The post-merge automatic Pages run, the live-site readback, and the closure of `#446` are
  recorded on the issue and in the terminal closeout record for this objective.
- This unit performs no runtime activation, no release or tag mutation, and changes no artifact of
  the published `v1.0.0-rc.1`, which remains published-but-rejected and immutable.
