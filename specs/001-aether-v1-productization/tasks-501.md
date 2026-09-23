# Pages description map repair (#501) — Supervisor task breakdown

**Status:** verified decomposition for Objective Contract `oc_ce1f17ebbb4968b4@v1`.

**Derived by:** Supervisor, decomposition root card `t_9f59977b`.

**Source contract:** `.aether/objective-contracts/oc_ce1f17ebbb4968b4/v1.md`
(SHA-256 `d4812b5ba1fd8c36663f3f8a24453ff48f42fabdc4c54cc9da1225a7ad49ebee`)
on Aether base `1b0d3a36d98e29125191798a5edf867b1c4097ce`.

**Objective board:** `oc-12027989a08f41cda82c54ff1bfb6b03-ce1f17ebbb4968b4-v1`
(its `worktree_base_ref` is the base above; unit worktrees start at that base and do
not inherit this file — read it read-only with
`git show <breakdown-sha>:specs/001-aether-v1-productization/tasks-501.md`).

This file is Supervisor-owned execution decomposition. It does not widen the
Objective Contract, and card bodies remain the executable unit deliveries.

## Receipt

| Check | Observed |
| --- | --- |
| Portable project | `.aether/project.toml` `project_id` equals envelope `12027989-a08f-41cd-a82c-54ff1bfb6b03`; repository `DarkArty07/Aether-Agents`; default branch `main` |
| Contract bytes | SHA-256 `d4812b5ba1fd8c36663f3f8a24453ff48f42fabdc4c54cc9da1225a7ad49ebee` matches the envelope; the file is tracked at the base |
| Base commit | worktree HEAD is exactly `1b0d3a36d98e29125191798a5edf867b1c4097ce`; its parent is `4c1af201c18ced73235d7b49f22a32123c46fb22` = fetched `origin/main` |
| Contract materialization | the base commit itself adds the contract and its non-specs manifest line in `.github/workflows/policy.yml`; `origin/main` carries neither yet, so the integration branch must publish both |
| Board identity | board `aether_project_id` / `aether_contract_id` / version match the envelope; `worktree_base_ref` = base |
| Profiles | `morfeo`, `supervisor`, `implementer` exist; no extra roles were created |
| Project Canonical Skills | only `.aether/skills/aether-observe/SKILL.md`; it is an observation procedure, not a decomposition input |
| Defect reproduced at base | `npm test` = **19/20**, failing `website/tests/content.test.mjs:163` ("src/lib/docs.ts must describe every canonical document and nothing else"); both guides missing from the map |
| Base website gates | `npm run build` = 23 pages; `npm run check` = 32 files, 0 errors/warnings/hints; `npm run test:e2e` = **38 passed** (desktop+mobile Chromium) |
| Browser E2E feasibility | Playwright Chromium headless shell installs and runs on this host; the objective's hard browser gate is executable by a permitted worker, so no stop condition fires here |
| Repository controls at base | `scripts/check_documentation.py` passed; `tests/test_public_artifacts.py` + `tests/test_documentation.py` = 27 passed; `scripts/check_public_artifacts.py --root .` path scan passed |
| Live site baseline | published `docs/search.json` holds 17 records; both guide routes return 404 |
| Inherited red run | Pages run `35800534897` at `4c1af201` fails `build -> Test content and links`; `deploy` skipped |
| Concurrent work | `#492` OPEN with no pull request; PR `#375` open/CONFLICTING and not active; an unpublished Morfeo two-entry candidate sits uncommitted in the `morfeo-issue-501` worktree and is preserved as reference evidence only |
| Required checks | `main` protection: strict, `enforce_admins`, contexts `pull-request-target`, `policy (3.11)`, `policy (3.12)`, `policy (3.13)` |

## Cross-artifact executability

| Concern | Settled conclusion | Execution consequence |
| --- | --- | --- |
| Defect is a curated map, not a rendering gap | `website/src/lib/docs.ts` is the description map **and** the reading order (`order = Object.keys(descriptions)`); the tracked corpus is 19 documents, the map holds 17 keys | Exactly two entries are added; no other source file changes |
| Bidirectional oracle | `website/tests/content.test.mjs:163-175` asserts map-vs-corpus equality in both directions | The oracle stays byte-intact; the fix satisfies it instead of editing it |
| Order is contract-decided | `objective-plans` after `project-initialization`, before `objective-contracts`; the tool guide after the operational guides, before `reference/*` | Both positions are stamped into the unit body; no worker vote and no re-derivation |
| Wording is local judgement | Contract leaves reversible wording to Implementer; descriptions must follow the guides' canonical text | The unit may arrive at the same wording as the candidate, but must derive it from the guides and must not import PR `#375` |
| Browser gate | Pages CI runs `check`/`build`/`content` only and never Playwright | A green Pages run cannot substitute for the browser receipt; real `npm run test:e2e` output is required from the unit and re-run at integration |
| Publication | Implementer commits locally only | Push, PR, protected checks, merge, Pages observation, issue closeout and cleanup belong to the terminal Supervisor card |
| Release identity | The repair is a public-site content correction inside the repository | No `VERSION` change, no tag, no package, no activation, no manual Pages dispatch |
| New tracked spec files | Repository policy scans every tracked Markdown for balanced fences and resolving relative links | Both new evidence/breakdown files use code spans for paths and balanced fences; no relative Markdown links |
| Stop conditions | No stop condition fires at decomposition: `origin/main` still has the defect, no active PR or worker edits `website/src/lib/docs.ts`, `#492` has no PR | Integration must re-verify these three facts and stop-and-reconcile if any proves false |

## Requirement coverage

| Source | Unit | Owning surface | Notes |
| --- | --- | --- | --- |
| AC1 | `PAGES-501-MAP` | `website/src/lib/docs.ts`, `website/tests/content.test.mjs` | Both guide keys described exactly once, truthful Spanish descriptions, decided order, oracle intact and passing |
| AC2 | `PAGES-501-MAP` | built site routes and search index | Routes, curated descriptions in `docs/search.json`, resolving internal docs links, desktop+mobile browser E2E |
| AC3 | `PAGES-501-MAP` | candidate revision evidence | `npm run build` / `npm run check` / `npm test` / `npm run test:e2e` with actual counts, skips and environment; whitespace, public-artifact and documentation controls |
| AC4 | `PAGES-501-INT` | `main` merge, Pages run, live site | Normal reviewed PR, exact merge revision, automatic Pages run at that revision, live docs route and search readback |
| AC5 | `PAGES-501-INT` | Issue `#501`, preservation | Attributed closeout only after AC1–AC4; otherwise the issue stays open with the precise missing effect |

## Units

| Unit | Assignee | Outcome | Writable surface | Verification | Dependency |
| --- | --- | --- | --- | --- | --- |
| `PAGES-501-MAP` | implementer | Both missing canonical guides described once each, in the decided order, with descriptions supported by the guides | `website/src/lib/docs.ts`; new `specs/001-aether-v1-productization/evidence/PAGES-501.md` | Website gate set with real output, corpus/map equality through the untouched oracle, whitespace and public-artifact/documentation controls; native same-card Supervisor review | Decomposition root |
| `PAGES-501-INT` | supervisor | Integrated, published and closed objective result | its own integration candidate, the objective branch/PR, `specs/001-aether-v1-productization/evidence/PAGES-501-INT.md`, Issue `#501` | Integrated re-run of the website gates, repository controls, protected checks, merge identity, Pages run at the merge revision, live readback | Decomposition root and `PAGES-501-MAP` |

## Concentration and independence

The objective has exactly one independent implementation unit. That concentration is
material, not cosmetic:

- The whole production change is a two-entry edit to a single curated map file whose
  key order *is* the site's reading order. Both entries interleave into the same
  ordered object literal, so splitting them into separate units would create two
  writers for one file — not independent work under current policy — and would
  partition by arbitrary file/entry count rather than by testable outcome.
- The oracle that accepts the change (`content.test.mjs:163-175`) compares the map
  against the corpus in both directions, so neither entry is independently acceptable.
- The remaining obligations (integration, protected checks, deployment observation,
  live readback, issue reconciliation) are not implementation work; they are the
  terminal Supervisor lane that consumes the reviewed unit.

There are therefore no false edges to remove and no artificial parallelism to
manufacture. `PAGES-501-INT` is genuinely serialized behind `PAGES-501-MAP` because it
must consume the reviewed candidate revision and the reviewed evidence, and because a
second concurrent writer on the objective branch would break the merge-identity chain
that AC4 measures.

## Shared decisions stamped into the unit bodies

1. Insert `guides/objective-plans` immediately after `guides/project-initialization`
   and before `guides/objective-contracts`; insert `guides/morfeo-tool-configuration`
   immediately after `guides/policy-and-recovery` and before `reference/cli`.
2. `website/tests/content.test.mjs` stays intact. No literal document count, no skipped
   or weakened assertion, no generated-page-count substitute.
3. Descriptions are Implementer's reversible wording, truthful to each guide's canonical
   text: Objective Plans carry route and continuity across sessions and contracts; the
   tool guide describes local, user-selected tool choices with their reasons and limits.
   The unpublished candidate is reference evidence, not accepted text to copy.
4. Install with `npm ci --include=dev --include=optional`; never modify
   `website/package.json` or `website/package-lock.json`.
5. Real browser E2E is mandatory from a permitted worker and is runnable here; it is
   re-run at integration and cannot be replaced by a green Pages CI run.
6. New tracked files under `specs/` must keep balanced code fences and use code spans
   instead of relative Markdown links, because the protected policy lane scans every
   tracked Markdown file for resolving relative links.
7. Units commit locally on their own branch only. Push, pull request, merge, Pages
   observation, issue mutation and cleanup are Supervisor integration effects.
8. Post-merge receipts (merge revision, Pages run, live readback, issue closeout) are
   recorded durably in the pull-request comment, the Issue `#501` closing comment and
   the terminal board handoff — not by a direct push to `main`, not by a second
   record-only pull request, and never as a pre-filled placeholder.
9. The canonical contract bytes are read-only for every unit. The owner's primary
   checkout, the unpublished candidate worktree, unrelated branches/worktrees, release
   identities, live installation state and credentials are preserved untouched.
10. Environment for the recorded receipts: Node 22.x, npm 10.x, the repository Python
    toolchain through `uv`; report the versions actually used instead of assuming them.

## Preservation boundaries

- No change to `website/` outside the two map entries, and none to `website/AGENTS.md`,
  `website/IMPLEMENTATION_PLAN.md`, `website/VERIFICATION.md`, dependencies, lockfile,
  workflows, Pages configuration or the `docs/` corpus.
- No redesign, translation or reordering beyond the two decided positions; no new
  feature; no release tag, package publication, manual Pages dispatch, non-Pages
  deployment, runtime activation, provider or credential change, check bypass or
  history rewrite.
- Concurrent work is preserved: `#492` and the `#375` beginner-guide work, other
  sessions' worktrees, boards and branches, and the inherited red run's evidence.

## Terminal integration expectations

`PAGES-501-INT` composes the objective branch from the contract base plus this
breakdown commit plus the reviewed unit commits, re-runs the gates on that exact
revision, publishes through one normal reviewed pull request, observes the automatic
Pages run at the merge revision, reads back the published routes and search index,
reconciles `#501`, cleans up only objective-owned merged residue after durable
evidence, and reports the criterion-by-criterion acceptance trace together with these
separate conclusions:

- `release_impact`
- `release_action`
- `release_channel`

A merge is not a release, and unit-level success is not integrated product success.

## Limits

- Decomposition receipts were measured on this host at the contract base; none of them
  is evidence about a later revision or about the merged result.
- The inherited Pages failure and the live 404s describe the pre-fix public state only.
- No live paid provider, owner-authority or credential surface was used or widened to
  produce this breakdown.
