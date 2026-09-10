# Beginner-first website documentation — Supervisor task breakdown

**Status:** verified decomposition for Objective Contract `oc_844dfc12880ee967@v1`.

**Derived by:** Supervisor

**Source contract:** `.aether/objective-contracts/oc_844dfc12880ee967/v1.md`
(SHA-256 `e53a80f647e6aa54eb749fd8b37148429abf9e41455d1f77a6c8af0107311302`)
on base `9bce0d222fdf0bfc581a26e282b81b08a1418d7c`.

**Owning issue:** [#368](https://github.com/DarkArty07/Aether-Agents/issues/368).

This is the Supervisor-owned execution decomposition. It does not widen the Objective
Contract or turn website presentation into evidence of a released/qualified runtime.
The executable unit deliveries are repeated in the native board cards because new
worktrees start at the contract base rather than this root branch's decomposition commit.

## Receipt

| Check | Observed result |
| --- | --- |
| Portable Project | `.aether/project.toml` equals envelope project `12027989-a08f-41cd-a82c-54ff1bfb6b03` and repository `DarkArty07/Aether-Agents` |
| Execution board | contract-bound board metadata identifies this Project and `worktree_base_ref` `9bce0d222fdf0bfc581a26e282b81b08a1418d7c` |
| Contract bytes | final v1 artifact exists and SHA-256 matches the envelope |
| Base / root worktree | deterministic task branch at exact required base; clean before decomposition |
| Design sufficiency | reader, truth boundary, IA groups, beginner deliverables, UI outcomes, verification, GitHub boundary, Telegram reporting and release conclusions are decided; no missing material product decision |
| Knowledge index | bound project matches; `available=false`; current source inspection is the fallback |
| Profiles | native `implementer` and `supervisor` profiles exist; no additional role is required |
| Project Canonical Skills | no `.aether/skills/` directory exists at the verified base; applicable Aether Canonical procedures govern |
| Issue | #368 is open and matches this objective; no milestone is attached |
| Upstream relation | contract base descends from extraction base `e9379c4712509c01f133745faaf810857b9a33a8`; `origin/main` was that extraction base at receipt |

## Cross-artifact conclusions

- The 16 tracked Markdown documents are accurate reference material, but do not form one
  explicit zero-context journey. The safe runnable entry remains a source checkout with
  provider-free parser/help/tests; no public installer or provider-backed run may be invented.
- `website/src/data/content.ts` currently presents greenfield and pipeline outcomes too
  categorically. It must distinguish intended product scope from the current narrow
  `aether init` requirement and unqualified end-to-end runtime state.
- The website already preserves tracked-only ingestion, sanitization, revision-pinned
  source links, local search, no-JavaScript reading, keyboard focus, local code/table
  scrolling and desktop/mobile rendering. These are preservation oracles.
- `/docs/` currently competes with generated `/docs/index/`; chapter navigation is flat;
  previous/next crosses conceptual categories; article pages lack in-page headings,
  search access and the canonical-English/status notice; no-JavaScript leaves an inert
  search visible. The accepted design below removes those gaps without translating or
  duplicating the canonical manual.
- The content corpus is one terminology/cross-link surface and the documentation renderer
  is one metadata/routing/navigation/test surface. Serializing the website unit after the
  independently reviewed content unit prevents an unclassified-corpus interval and a
  collision over new slugs. The Telegram monitor is independent local operational work.
- External defect #364 may make the base public-artifact check red. Units must record its
  exact baseline result and not absorb it. Terminal closeout rebases onto the independently
  corrected compatible `main` before requiring green checks.

## Shared decisions

1. Authority is Objective Contract `oc_844dfc12880ee967@v1`; canonical skills are
   procedure only. The contract is read-only and is never copied, staged or edited by an
   Implementer.
2. Exact new canonical pages are `docs/start-here.md`,
   `docs/guides/first-objective.md`, and `docs/reference/glossary.md`. They respectively
   own the zero-context mental model/route choice, the clearly non-normative end-to-end
   walkthrough, and concise Aether vocabulary. Existing pages are updated and cross-linked
   rather than duplicating their reference detail.
3. The explicit documentation groups, in order, are **Start here**, **Core concepts**,
   **Working with Aether**, **Operations and safety**, and **Reference**. Group labels and
   pedagogical order are explicit metadata, never inferred from filesystem order.
4. Canonical `docs/index.md` is represented at `/docs/` and must not also generate
   `/docs/index/`. Every other tracked `docs/**/*.md` page has exactly one article route.
   Every tracked page has exactly one explicit manifest record, navigation/search metadata,
   group and stable order. Unknown tracked pages, duplicate slugs/routes, missing manifest
   entries and manifest entries without tracked source fail tests.
5. Canonical technical pages remain English. `/docs/` may orient in Mexican Spanish and
   map Spanish beginner terms to canonical English search results. Article pages visibly
   state English/manual/revision/current-status context. No full translation or localization
   framework is introduced.
6. `docs/capabilities.toml` owns implemented/partial/transitional/unsupported status;
   design/specs own intended behavior. Beginner and landing copy must label that distinction,
   say this is a stabilization build rather than a public release, and identify provider-free
   source inspection as the guaranteed exercise.
7. The current `aether init` path requires an existing Git repository and an exact-path,
   non-archived native Hermes Project. Greenfield support may be described only as intended
   scope, not current behavior. Generic Hermes installation/provider/credential work links
   to `https://hermes-agent.nousresearch.com/docs/` rather than restating it.
8. Article chrome includes group/current-page context, a docs-index/search route, in-page
   heading navigation for long pages, accessible anchored headings, within-group adjacent
   pages, mobile navigation and fragment positioning below sticky chrome. Exact Astro/CSS
   component organization is Implementer judgement.
9. Search covers title, description, group metadata and body; representative Spanish and
   English beginner terms resolve useful results. It reports count/no-result/failure state.
   Without JavaScript, complete grouped navigation/index remains usable and an inert search
   input is hidden or explicitly unavailable.
10. Source-relative Markdown links and fragments must also resolve as generated routes.
    Only safe schemes are emitted. Source links remain pinned to the candidate commit.
    Code and table overflow stays local, keyboard reachable and accessible.
11. Test expectations derive the corpus with `git ls-files` rather than a literal count.
    Clean `website/dist`, `.astro`, reports and captures before evidence; run `npm run build`
    before content tests so stale output cannot satisfy revision assertions.
12. Implementation units commit only their owned paths, report compatibility evidence,
    and request same-card Supervisor review. They do not push, open PRs, merge to `main`,
    deploy Pages, publish, invoke providers, change credentials/settings, or close #368.
13. Terminal integration preserves accepted unit commits without squash/amend/rebase/force.
    It may make only mechanically implied conflict/import/path/build glue repairs. Behavior,
    truth, interface or accessibility gaps return to Implementer review/rework.
14. Contract-fixed aggregate conclusions are `release_impact=patch`,
    `release_action=defer`, `release_channel=none`. A PR does not imply release or deploy.
15. Telegram reporting is local operational state only. It uses the already provisioned
    destination without exposing identifiers, sends change-driven observed milestones
    rather than heartbeat noise, distinguishes inference, emits a terminal brief and then
    stops. Nothing about its destination/job/session is committed.

## Requirement coverage

| Contract source | Owning unit | Acceptance/evidence responsibility |
| --- | --- | --- |
| AC 1–5; deliverables 1–2 | BGD-CONTENT | beginner journey, concepts, route choice, first-objective example, glossary, truth/status, validated commands |
| AC 6–11; deliverables 3–6 | BGD-WEB | explicit complete manifest, routes, grouped navigation, article orientation, TOC/anchors, search, no-JS, responsive and accessibility evidence |
| AC 12 | every unit + BGD-INT | no private/local operational state in public artifacts; public-artifact gate |
| AC 13; deliverable 8 | BGD-CONTENT and BGD-WEB | corpus descriptions plus website operating/verification guidance match result |
| deliverable 10 | BGD-MON; BGD-INT terminal check | change-driven Telegram progress and terminal-stop behavior |
| AC 14; deliverables 7 and 9 | same-card review + BGD-INT | independent review, integrated gates, issue/PR/check reconciliation, merge/deploy deferral |
| Preservation / authority / stop conditions | every unit | no runtime capability implementation, credentials, provider invocation, deployment, release, bypass or unrelated defect absorption |

## Execution graph

```text
Supervisor decomposition root
    ├── BGD-CONTENT (Implementer; canonical beginner content and truthful landing copy)
    │       └── same-card Supervisor review
    │               └── BGD-WEB (Implementer; manifest, docs UX and website verification)
    │                       └── same-card Supervisor review
    └── BGD-MON (Implementer; local Telegram progress monitor)
            └── same-card Supervisor review

Supervisor decomposition root + all three independently reviewed units
    └── BGD-INT (Supervisor; terminal integration, PR, green checks, no merge/deploy)
```

BGD-MON is independent of repository implementation. BGD-WEB depends on reviewed
BGD-CONTENT because its explicit complete manifest must classify the final tracked corpus
and its local tests must build those actual pages; the dependency is not an arbitrary
sequence. The content unit is deliberately concentrated because prose terminology,
status labeling, route choice, walkthrough and cross-links form one truthfulness surface.
The website unit is deliberately concentrated because metadata, routing, navigation,
search, fragments, CSS and browser tests share one renderer contract and existing test files.

## BGD-CONTENT — canonical beginner journey and truthful presentation copy

- **Source:** Owner Intent, Objective, Decisions 1–5 and 7, Deliverables 1–2,
  AC 1–5, AC 12–13, Testing Standard; this unit.
- **Outcome:** Add the three decided pages; turn `docs/index.md` and
  `docs/getting-started.md` into a sequenced beginner path; audit all tracked canonical
  pages and update only those needing terminology, prerequisite, status, next-step or
  cross-link corrections. The walkthrough follows an owner-authorized pipeline objective
  through Morfeo, contract, board/worktree, implementation, independent review, GitHub
  evidence and terminal reporting, and contrasts one bounded direct example. It is clearly
  illustrative and does not claim provider execution. Correct Spanish and English landing
  copy that currently presents greenfield/init and end-to-end execution as unqualified
  current behavior. Exclude website renderer/IA styling, runtime changes and translation.
- **Inputs:** exact contract/base above; `DESIGN.md`; `docs/capabilities.toml`; relevant
  current design/specs; all 16 tracked docs; current parser/source; authoritative Hermes
  docs only when generic Hermes behavior is referenced. Revalidate source rather than
  copying this audit as proof.
- **Boundaries:** writable `docs/**/*.md` except generated
  `docs/reference/capabilities.md`; `website/src/data/content.ts`; new focused root test
  `tests/test_beginner_documentation.py`; unique evidence
  `specs/beginner-first-website-docs/evidence/BGD-CONTENT.md`. Preserve
  `docs/capabilities.toml`, Python/runtime source, website renderer/components/styles,
  existing website tests, historical website design proposals and Objective Contracts.
- **Judgement:** exact prose, examples, section arrangement, which existing reader pages
  need a correction, and private test helper names. Do not change product semantics,
  status values or shared filenames/groups.
- **Verification:** regression-first focused assertions for required pages, learning
  sequence, current-vs-intended markers, glossary/link/next-step coverage and forbidden
  public/private claims. Run `uv run --frozen python scripts/check_documentation.py`;
  `uv run --frozen pytest -q tests/test_beginner_documentation.py tests/test_documentation.py tests/test_public_artifacts.py` and identify any exact unchanged-base #364 failure;
  isolated temporary HOME with `HERMES_HOME` unset for `uv run --frozen aether --version`,
  `aether --help`, `aether observe --help` and every additional beginner-facing Aether
  help path; `git diff --check`. Record command exit codes and interpretations.
- **Dependencies:** decomposition root only. No file collision with BGD-MON.
- **Completion:** one or more local commits containing only owned files, unit compatibility
  `patch`, evidence report, risks/known baseline failures, and same-card Supervisor review.
  No push, PR, issue mutation, deployment or release.

## BGD-WEB — explicit corpus manifest, documentation UX and browser evidence

- **Source:** Decisions 2–3 and 6–7, Deliverables 2–6 and 8, AC 6–13,
  Testing Standard; this unit.
- **Outcome:** Consume the reviewed BGD-CONTENT commit without rewriting it. Implement the
  five-group explicit manifest and unique `/docs/` handling; grouped/current navigation;
  article language/revision/status/breadcrumb context; heading navigation and anchored
  headings; within-group previous/next flow; prominent article search/index access; useful
  search metadata/states; docs-oriented 404 recovery; mobile/keyboard/no-JS behavior;
  local overflow and fragment positioning. Add deterministic corpus/link/fragment/route/
  source-integrity checks and desktop/mobile browser coverage, including Axe A/AA. Reconcile
  website operating and verification docs. Preserve landing identity/artwork/motion.
- **Inputs:** exact base/contract plus independently reviewed BGD-CONTENT commit. Merge the
  accepted prerequisite commit into this unit branch with ordinary non-rewriting Git so
  the original commit remains inspectable; do not squash, amend or rebase it. Revalidate
  tracked corpus and current website source after that merge.
- **Boundaries:** writable `website/src/lib/docs.ts`, documentation-only components under
  `website/src/components/` (existing `DocsNavigation.astro` plus bounded new docs
  components), `website/src/pages/docs/**`, `website/src/pages/404.astro`, documentation
  sections of `website/src/styles/global.css`, `website/src/pages/docs/search.json.ts`,
  `website/tests/content.test.mjs`, documentation-focused files under
  `website/tests/browser/`, `website/playwright.config.ts`, `website/scripts/capture.mjs`,
  `website/AGENTS.md`, `website/README.md`, `website/VERIFICATION.md`, and unique evidence
  `specs/beginner-first-website-docs/evidence/BGD-WEB.md`. `website/package.json` and lock
  are writable only if an acceptance-required script change is necessary; do not add a
  dependency when existing tools suffice. Preserve inherited BGD-CONTENT files, landing
  components/art/assets/motion/copy, Python/runtime source, Objective Contracts and
  historical proposal documents.
- **Judgement:** local TypeScript interfaces, Astro component boundaries, TOC threshold,
  CSS layout, search failure wording and focused browser-test organization, provided the
  shared manifest/group/route and accessibility outcomes remain exact.
- **Verification:** clean ignored generated output; from `website/`, `npm ci`, `npm run build`,
  `npm run check`, `npm test`, `CI=1 npm run test:e2e`, `AETHER_PAGES=1 npm run build`,
  `node scripts/verify-pages-build.mjs`, then rebuild normal output before further browser
  inspection. Run/extend `node scripts/capture.mjs` for representative desktop/mobile docs
  index/start/walkthrough/long-reference pages and inspect captures. Tests derive tracked
  corpus, prove one route/manifest/search/navigation record per page, no `/docs/index/`,
  valid source and generated links/fragments/schemes, duplicate-heading rejection, pinned
  sources, unknown-page failure, search Spanish/English success/no-result/failure, article
  context, direct fragments below sticky header, within-group adjacency, keyboard/focus,
  no page overflow, code/table local scrolling, JavaScript-disabled reading/navigation and
  Axe A/AA on the contract's representative pages in both projects. Also run root
  documentation/public-artifact focused gates and `git diff --check`.
- **Dependencies:** decomposition root and independently reviewed BGD-CONTENT, because the
  explicit manifest and routes must classify/build the final corpus. No dependency on
  BGD-MON.
- **Completion:** inherited BGD-CONTENT commit remains distinct plus local website commits,
  unit compatibility `patch`, evidence/capture locations and limitations, and same-card
  Supervisor review. No push, PR, issue mutation, merge to main, Pages deployment or release.

## BGD-MON — change-driven Telegram progress reporting

- **Source:** Owner Intent, In Scope reporting bullet, Deliverable 10, AC 12 and authority;
  this unit.
- **Outcome:** Through existing Hermes/local operational surfaces and the already provisioned
  Telegram destination, configure one objective-specific reporter that observes this
  contract board and sends concise reports only for meaningful state transitions (unit
  start/completion, review/rework/blocker, PR/check state, terminal outcome). It labels
  observation versus inference, emits no heartbeat/status spam, sends no secrets/private
  paths/identifiers/logs, and stops or disables itself after terminal outcome. Send an
  initial objective-start brief only if it does not duplicate an observed existing report.
- **Inputs:** current native task/board binding and existing provisioned delivery. Inspect
  current objective-specific jobs first and update/reuse rather than duplicating. Do not
  expose destination identifiers. Terminal card identity will be added to the card thread
  before dispatch.
- **Boundaries:** writable local objective-specific scheduler/job state only. No repository
  files, profile/provider/model/credential/settings changes, gateway restart, external
  destination creation or unrelated job mutation.
- **Judgement:** bounded polling cadence and concise change-detection state shape, using
  existing supported Hermes interfaces. If no already provisioned destination can be used
  without acquiring/changing credentials or settings, block with exact capability evidence.
- **Verification:** inspect objective-specific job readback without printing sensitive
  fields; prove one job, correct board/objective scope, change-driven behavior, safe report
  text, terminal-stop condition, and no committed diff. A dry-run/local state transition
  may be used if it does not invoke providers or disclose private data. Do not claim a
  Telegram delivery unless the supported delivery surface reports it.
- **Dependencies:** decomposition root only; operationally independent of repository units.
- **Completion:** durable local job reference only in private/native state, sanitized
  handoff, unit compatibility `none`, and same-card Supervisor review. No repo commit is
  required and no identifier is copied into public evidence.

## BGD-INT — terminal integration, PR/check closeout, no merge or deployment

- **Source:** Deliverables 7 and 9–10, AC 12–14, Testing Standard and Stop Conditions;
  this unit.
- **Outcome:** Consume all independently reviewed units; preserve accepted commits; rebase
  by ordinary non-rewriting integration onto the latest compatible `origin/main`, including
  the independent #364 correction required for a green public-artifact gate. Integrate only
  this objective; run complete local acceptance; push the normal branch; open one PR to
  `main` linked to #368; obtain required green checks and reconcile actionable review/check
  findings without bypass. Do **not** merge because `main` triggers Pages deployment. Leave
  #368 open pending that unauthorized merge/deploy, send/verify the terminal Telegram brief,
  stop the objective reporter, and report durable board/Git/GitHub/test/residue evidence.
- **Inputs:** decomposition root plus accepted BGD-CONTENT, BGD-WEB and BGD-MON handoffs,
  commits and compatibility evidence. Re-fetch/read latest `origin/main`, workflow and issue
  state before integration. A concurrent target-file behavior conflict is a stop condition,
  not permission to absorb unrelated work.
- **Boundaries:** integration branch; mechanically implied conflict/import/path/build/test
  glue only; terminal evidence under `specs/beginner-first-website-docs/evidence/`; issue
  comment/PR metadata strictly needed for authorized closeout; local objective reporter
  stop. Behavior/truth/interface/accessibility changes return to implementation rework.
- **Verification:** full BGD-WEB website sequence from clean generated state; root
  `uv run --frozen python scripts/check_documentation.py` and
  `uv run --frozen pytest -q tests/test_beginner_documentation.py tests/test_documentation.py tests/test_public_artifacts.py`;
  all documented parser probes in isolated HOME; `git diff --check`; root `AGENTS.md` and
  `website/AGENTS.md` coherence; intended-path/privacy audit; normal push/PR; required check
  logs green. Confirm PR open/unmerged, Pages not triggered by this branch/PR, #368 linked
  and open, no release/tag/package/deployment, reporter terminal brief/stop, and preserve
  active/unmerged/concurrent/unrelated worktrees, branches, stashes and processes.
- **Dependencies:** decomposition root and every independently reviewed implementation unit.
- **Completion:** reviewed open PR with required checks green, no merge/deploy, omissions
  each with concrete reason, and aggregate conclusions kept separate:
  `release_impact=patch`; `release_action=defer`; `release_channel=none`. Local integration
  alone is not success.

## Stop conditions

Follow the contract exactly. Return a contract defect to Morfeo if current capability
truth conflicts materially with the accepted beginner path and cannot be solved by explicit
implemented/intended/unsupported labeling. Stop on protected-edge denial, missing
provisioned reporting destination, incompatible target-base change, un-attributable red
baseline that blocks acceptance, required runtime/provider/credential/settings/deployment/
release work, or concurrent-work collision. Ordinary prose iteration, local component/test
choices, independently fixed #364 integration and correctable review findings are not owner
input. Never modify the canonical Objective Contract or use a historical proposal as current
product authority.
