# Documentation reconciliation — aggregate audit record (#552)

**Objective Contract:** `oc_593cb1275b24ea19@v1` (AC1–AC4 / DC-01–DC-06).
**Owning design:** [spec.md](../spec.md), [plan.md](../plan.md), [research.md](../research.md).
**Base revision:** `62ec14653baa8f84449f41a68d64cf64d50939d6`.
**Execution breakdown:** [tasks.md](../tasks.md).
**Role:** this note is the D2 inventory of confirmed findings and their dispositions. It
grants no authority and is not an acceptance claim; Morfeo performs the separate
contract-result reception against the integrated revision.

Scope audited: the tracked current root portals (`AGENTS.md`, `CLAUDE.md`, `README.md`,
`ROADMAP.md`, `CHANGELOG.md`, `INTEGRATIONS.md`, `CONTRIBUTING.md`, `DESIGN.md`), the 20
tracked current `docs/` Markdown pages, `docs/capabilities.toml` with its generated
reference, the active stage-specification entry points, and the website docs map. This is
a documented, reviewable sweep at the recorded base revision, not a claim that no sentence
in any historical evidence file can ever conflict.

## 1. Confirmed findings and corrections

Each row names the semantic owner that was corrected, the cited source at base, and the
disposition. Unit evidence: [U3 corpus note](u3-docs-corpus.md).

| # | Finding (at base) | Owning question | Disposition |
| --- | --- | --- | --- |
| 1 | `DESIGN.md:3` claimed the accepted conceptual design ran "through PD-76" while `DESIGN.md:402` already contained accepted PD-77. | DC-02 current accepted-decision set | Corrected at the owning artifact: the status header now names PD-77 with a one-line guide distinguishing PD-76 from PD-77; the `Accepted baseline` date is unchanged and a dated amendment note records that only the claim was corrected. |
| 2 | `ROADMAP.md:4` repeated the stale bound "`DESIGN.md` through PD-76". | DC-05 derived roadmap map | Corrected to name the actual accepted set, deferring to `DESIGN.md` §11 as normative. |
| 3 | `tests/test_a1_contracts.py:266-267` enforced the superseded PD-76 wording as an exact-string oracle. | DC-05 derived oracle | Corrected only on the two lines enforcing the revised claim; the PD-74 assertions in the same test are preserved verbatim. No gate weakened, skipped or deleted. |
| 4 | `ROADMAP.md:4` attributed the date `2026-09-23` to PD-76. | DC-02 provenance truthfulness | Corrected: git provenance shows the PD-76 row was added by `b51d0f59` on 2026-08-27, and 2026-09-23 is PD-52's owner amendment (`DESIGN.md:377`). |
| 5 | `specs/r5-topology-and-isolation/spec.md:90-91` required "one board per project" as a current MUST, superseded by the accepted per-`(project_id, contract_id, version)` execution board in `specs/003-objective-contracts/spec.md:48-62`. | DC-02 board isolation | Reconciled at R5 (the topology owner) with the project binding, worker board pin and trusted-local-user boundary preserved; the earlier text is preserved as history in the R5 research file §10. |
| 6 | `specs/r5-topology-and-isolation/spec.md:139-140` (FR-518) said the supervising role "MUST NOT perform the implementation itself" with no boundary, against accepted PD-73. | DC-02 bounded repair | FR-518 keeps the prohibition and adds the accepted PD-73 boundary, citing `DESIGN.md` PD-73/PD-77, `R8-FR-819b`/§7.1 and `R7-FR-703`; no new lane, role or product authority. |
| 7 | `specs/r9-state-and-recovery/spec.md:253-254` (FR-924/FR-925) mirrored the coarse board requirement. | DC-02 board isolation (derivative) | Reconciled to the per-contract-version board, the project-level mapping and the no-board-at-init fact; namespacing prohibition extended to contract versions. |
| 8 | `specs/r9-state-and-recovery/spec.md:258` still led with "One board and workspace root per portable project identity". | DC-02 board isolation | Corrected: the stale board *and workspace root* claim was removed; `A1-FR-052` and `contracts/cli.md` §2 own the fact that initialization creates no board or execution workspace. |
| 9 | `specs/r13-synthesis-and-release/spec.md:131` (FR-1334) mapped initialization to one native Project, board and workspace root. | DC-02 board isolation (derivative) | Corrected to Project only, with the board provisioned by a ready handoff; the same workspace-root claim was removed. |
| 10 | `docs/reference/limitations-and-troubleshooting.md:18` called source `1.0.0rc16` the current candidate and concatenated a second limit row into the same Markdown line (9 pipe fields). | DC-03 source/release/runtime honesty; DC-04 limits | Split into three valid rows: current-source, labelled Historical RC16 candidate with exact locators, and State export as its own current-limit row. Every row now has exactly 3 cells. |
| 11 | `docs/guides/morfeo-mcp.md:20` directed activation at "the managed rc9-then-rc10 update path" in the present tense. | DC-03 stale present-tense status | Now names the managed `aether update` preparation/activation boundary and labels the RC9/RC10 bridge as history. |
| 12 | Five current pages plus the registry owner described the maintained-fork release lock as `schema_version` 4 only (`docs/reference/limitations-and-troubleshooting.md:17`, `docs/reference/cli.md:59`, `docs/guides/policy-and-recovery.md:81`, `docs/getting-started.md:111`, `docs/product-boundary.md:45`, `docs/capabilities.toml:136`). | DC-04 capability/status accuracy | Each surface now distinguishes the emitted schema 5 with the closed `hermes.extras` allowlist from the accepted reader schemas 4 and 5. The registry was corrected first and the generated reference regenerated once with the repository script. |
| 13 | `docs/index.md:18` stated the fork binding as "release-lock schema 4 or 5" without distinguishing emission from read compatibility. | DC-03 | Reworded to name the emitted schema and the accepted reader range. |
| 14 | `AGENTS.md:28,30,32,35-54,101-108` presented RC6, RC8, RC14, RC15, #426/#459, #541/#542 and #515 as current standing authority for new work. | DC-03 root operating-map temporal authority | The earlier-objective paragraphs are preserved verbatim under a dated "Historical objectives" heading that explicitly disclaims standing authority for new work; the RC17/#541 paragraphs were re-labelled in place. Links and preservation gates retained; no approval text deleted or rewritten. |
| 15 | `INTEGRATIONS.md:18-25,47-62` stated installation-specific Context7/Exa status as portable current product status. | DC-04 integration-index honesty | The ACTIVE vocabulary now carries an installation-specificity qualifier; the Context7 entry states the verified limit (packaged profiles ship no `context7` entry) and re-attributes the unpinned `@upstash/context7-mcp` invocation to the owner-selected local template; the Exa entry cites the packaged profile resources and the local-credential dependency. No owner-selected integration was dropped and no credential or private runtime state was read. |
| 16 | `AGENTS.md:26`, `AGENTS.md:216` and `README.md:42` described the maintained-fork binding as release-lock `schema_version` 4 only. | DC-03 root portals | Brought into line with finding 12: each line states the emitted schema 5 and the accepted reader range. |
| 17 | `.github/workflows/policy.yml` canonical base manifest omitted the tracked path `.aether/objective-contracts/oc_593cb1275b24ea19/v1.md`, so the required step "Validate canonical base manifest" and its oracle failed (397 expected vs 398 actual). | DC-06 required checks | Exactly one data line added in sorted position. No CI logic changed, no check weakened, and the workflow's own data-only classifier still treats the diff as manifest data. |
| 18 | `ROADMAP.md:6,8,70,98` and `specs/r13-synthesis-and-release/spec.md:20` still stated release-lock `schema_version` 4 as the *current* binding. Findings 12 and 16 reconciled the same claim class in `docs/`, `AGENTS.md`, `README.md` and the registry, but omitted the roadmap and the stage-spec/plan headers, so the objective's own DC-03/DC-05 sweep was incomplete. | DC-03 source/release honesty; DC-05 derived roadmap + stage owners | Reconciled at each semantic owner: `ROADMAP.md` (derived roadmap), `specs/r13-synthesis-and-release/spec.md` and `plan.md` (stage owner), plus the same present-tense claim in `specs/r4-hermes-boundary/spec.md:42`, `specs/r8-workspaces-and-integration/spec.md:44`, `specs/001-aether-v1-productization/{spec,plan,research,tasks,contracts/cli}.md` and the coupled oracle. Each now distinguishes emission from read compatibility (current preparation emits `schema_version` 5 with the closed `hermes.extras` allowlist; readers accept 4 and 5). Dated 2026-09-15 reconciliation records keep their schema-4 wording and gain an explicit superseding pointer. See the continuation note below. |

## 2. Verified non-applicability (audited, deliberately not edited)

- `docs/guides/objective-plans.md:37` names "RC16 updater compatibility" and "RC17's
  bounded release evidence" as dated functional history with its own storage-key
  rationale — not a present-tense current-candidate claim.
- `docs/index.md:20,26` frames the rc3 qualification and rc2 rollback explicitly as "the
  historical rc3 qualification" — correctly attributed history.
- `docs/product-boundary.md:41` describes the authorized `1.0.0rc1` milestone as a
  pre-stable candidate that is not stable `1.0.0`, a package-index publication or WSL2
  qualification — truthful and boundary-preserving.
- `docs/capabilities.toml` rc3 activation, rollback and trace evidence is explicitly
  bounded as installation-local, "not public release or cross-platform qualification".
- `specs/r5-topology-and-isolation/spec.md:77-78` (FR-508/FR-508a) describes two different
  routes rather than a contradiction: the native dispatcher buckets a non-profile assignee
  into `skipped_nonspawnable` and never auto-spawns it, while `claim_task` still serves a
  terminal-pulled lane. Verified in the installed runtime before deciding not to edit.
- `specs/001-aether-v1-productization/spec.md:13-14` pins `PD-01 through PD-74` and
  `Product-definition version: PD-74` as that contract's own deliberate definition anchor,
  asserted verbatim by the A1 oracle. Widening it would be a new owner-scoped contract
  decision, not documentation reconciliation, so it was reported rather than edited.
- Eleven further `docs/` pages contain no RC-label or active-release status claim.
  Spot-verified behavioural numbers matched source: the 300-second semantic budget, the
  128–8,000 `budget_tokens` range, the 32,768-byte result ceiling and the 10,000-note
  lexical search bound.
- Graphify's configured/optional boundary is preserved: every packaged role template ships
  `aether-project-knowledge` with `enabled: false`.
- Lab/Monitor retirement wording already preserved native Hermes cron, ordinary Telegram
  interaction and native notifications; no edit was required.

## 3. Test effect

No gate was weakened, skipped, deleted or re-scoped anywhere in this objective. Existing
oracles required correction only where they enforced the exact revised current claim
(finding 3), and one required CI gate was repaired by data registration (finding 17).

- Focused suites on the integrated revision: 77 passed, 1 skipped, 11 subtests passed.
- `scripts/check_documentation.py` and `scripts/check_public_artifacts.py` pass.
- The required policy steps "Validate accepted R0 design baseline" and "Validate canonical
  base manifest" both pass, the latter verified against an independent recount that the
  heredoc equals `git ls-files | grep -v '^specs/'` exactly.
- Website (`docs/**` renders from this corpus): `npm run check` 0 errors, `npm run build`
  24 pages, `npm test` 20/20.
- `ruff check` and `ruff format --check` pass; `git diff --check` is clean.

## 4. Open limits

- No installed release is claimed anywhere: local runtime state stays private evidence and
  `aether doctor --json` remains the only portable route to live state.
- This objective reconciles current documentation; it qualifies no runtime behaviour beyond
  the checks recorded above.
- The prior #549 red main push and its #550 correction remain immutable history and are not
  retroactively made green.

## 5. Continuation — finding 18 correction (post-PR-#555, card `t_d87c50d8`)

Morfeo's exact-result reception of the merged revision found finding 18: findings 12 and 16
corrected the schema-4-as-current claim in `docs/`, `AGENTS.md`, `README.md` and the
capability registry, but left the same present-tense claim in the derived roadmap and the
active stage-spec/plan headers. That was a real gap in this audit's DC-03/DC-05 coverage,
not new product intent, so the same Objective Contract `oc_593cb1275b24ea19@v1` continued
under card `t_d87c50d8` at base `21beed80` (the current `origin/main`, which contains the
`f745cd32` merge of PR #555).

Sections 1–4 above are preserved as the PR #555 record and are not rewritten. This section
records only the continuation.

**Corrected at the semantic owner** (source of truth: `scripts/release_bundle.py:43-45`
emits schema 5, accepts readers 4/5, with the closed `hermes.extras` allowlist):

- `ROADMAP.md:6,8,70,98` — derived roadmap map.
- `specs/r13-synthesis-and-release/spec.md` (header and the 2026-09-15/reconciliation notes)
  and `plan.md` (header, §2.1 schema table and paragraph, §2.5, Phase 3) — stage owner.
- `specs/r4-hermes-boundary/spec.md` (FR-403a and the reconciliation note) and
  `specs/r8-workspaces-and-integration/spec.md` (FR-804c) — stage owners for the same claim.
- `specs/001-aether-v1-productization/`: `spec.md` (A1-FR-021d plus a dated supersession
  note), `plan.md` (§2.2 import-boundary paragraph and the update path), `research.md`
  (artifact-identity paragraph plus a superseding note), `tasks.md` (pinned identifiers),
  `contracts/cli.md` (`--release-lock` requirement, accepted-lock paragraph, `doctor`).

**Coupled oracle corrected, gate preserved.** `tests/test_a1_contracts.py` pinned the exact
stale literal `"release-lock schema is integer \`4\`"`. The test was renamed to
`test_release_lock_schema_and_plan_agree_on_accepted_versions` and now asserts the shipped
schema enum `[4, 5]` together with the revised plan wording, keeping the same coupling gate,
the same `assertNotIn` guard, and every neighbouring PD-74 assertion verbatim. No test was
deleted, skipped, weakened or re-scoped.

**Deliberately not edited (verified, not assumed).** Dated records whose schema-4 wording is
correct history: the 2026-09-15 reconciliation notes in R4/R13 and A1 research (they keep
their wording and gain a superseding pointer), `CHANGELOG.md:153` (RC9 *did* emit schema 4),
`specs/008-morfeo-mcp/{spec,plan,tasks}.md` (RC9's bridge behavior), `tasks-rc2.md` (RC2's
own bundle identity), `src/aether_agents/lifecycle.py:512` (`schema_version == 4` is the
reader branch that must accept schema 4) and `:4375` (a docstring about schema-4 lock
qualification), and the `docs/**` and root-portal surfaces already corrected before PR #555.

**Verification of this continuation** (exact commands run in the objective worktree):
focused `tests/test_a1_contracts.py` → 29 passed, 11 subtests; `tests/test_documentation.py`
+ `tests/test_a1_contracts.py` + `tests/test_contract_quality_documents.py` → 59 passed,
1 skipped, 11 subtests; `scripts/check_documentation.py` → passed;
`scripts/check_hermes_baseline_drift.py --json` → exit 0; `ruff check`/`ruff format --check`
on the changed test file → clean (the 3 `ruff check` and 8 `ruff format` findings elsewhere
are pre-existing, in files this change does not touch); `git diff --check` → clean.
A full class re-sweep for the claim pattern over all tracked files leaves only the
deliberately-preserved sites listed above.

**Boundary.** Documentation and its coupled oracle only: no `VERSION`, tag, release-lock,
runtime, credential or provider change, no manual Pages dispatch, and no check bypassed.
Pages is not applicable to this change — `.github/workflows/pages.yml` triggers on
`website/**`, `docs/**` and its own path, and this delta touches none of them.
`release_impact=none`, `release_action=defer`, `release_channel=none`.
