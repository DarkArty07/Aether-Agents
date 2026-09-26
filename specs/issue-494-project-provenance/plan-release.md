# #494 — RC16 exact-version adoption and effective-runtime qualification

**Status:** RC16 design reconciled against Aether `420a79fc0492022236a208edff75ed9b09f112cb` and the selected RC15 runtime. The owner directs autonomous #494 completion through RC16 while observing the recently activated Supervisor review changes in real work. This supersedes the RC15 version/transition premise of `oc_c770cea3db51d97e@v1`, not its #494 acceptance boundary. The old RC15 execution root remains blocked by the owner's earlier stop and must not be resumed as RC16. This document is design, not activation evidence.

## Destination and current identities

The source-only #494 repair is already reviewed and integrated. Maintained-fork PR #16 merged HLP-428 at exact commit `58f8c37a49b341f25b8fdd6310542fe932031b8d`, Git tree `a93162c1a867202b03c12fa372c71029152fdcf7`. Aether's deterministic archived-source digest for that exact commit is `a2a9b374bd2022c7f96242b0ab2c95691119262c925389eb3820ca627c581144`. Aether main already contains the HLP-428 ledger/reconciliation and the candidate-HLP gate.

The effective installation at design time is Aether `1.0.0rc15`, release `1.0.0rc15-5dc9cd69da8d18f3`, `aether doctor=result=ready`, with maintained-fork Hermes `5b2b6ba543680c6fe8a62de4b467d1107be3abf4` and source-tree digest `adf77d5840028f490818a3f78304a9f3835bff176df3ad34255aea2f9882aba2`. RC15 was published as a GitHub prerelease and is selected locally, but its fork commit contains only the optional review-return count on the earlier `aed6591a69…` base, not HLP-428. RC15 does not close #494. Reverify the selected reader and preservation state immediately before any new live effect.

The fork advanced through `621047dc1c10cceb2825013cc8bb611b4d0e8de1` for HLP-433 and then merged RC15's optional review-return count at `938bc34fbc797402ccc61d352192e122a344d052`. Selecting that later tip would silently adopt HLP-433, excluded from #494. Selecting earlier reviewed `58f8c37…` for RC16 keeps the HLP-428 runtime proof causal and HLP-433 deferred. It omits Hermes's **optional** six-line review-return count; preserve RC15's Aether Supervisor SOUL and canonical review procedure, use their specified fallback to durable history when the count is absent, and explicitly qualify/report that absence-tolerant path. Do not call the Hermes context count an enforcement gate or claim measured review speed from packaging tests. If the optional count is found to be a material required guarantee for RC16, stop for an owner disposition rather than adopting HLP-433 or changing fork source under this contract.

## Release sequence

### RC16 — #494 adoption and closure candidate

RC16 is package `1.0.0rc16`, display `1.0.0-rc.16`, local annotated tag identity `v1.0.0-rc.16`. It carries the current RC15 Aether product surface, including the Supervisor instructions, and changes the selected Hermes source from `5b2b6ba543…` to exact `58f8c37a49…`. Preserve the RC15 release/tag/installed records unchanged.

The candidate MUST:

1. bind release-lock source mode `maintained_fork` to repository `https://github.com/DarkArty07/aether-hermes`, branch `aether-main`, commit `58f8c37a49…`, deterministic source-tree digest `a2a9b374…`, exact artifact closure and provenance;
2. make HLP-428 `candidate_requirement=required`;
3. keep HLP-433 `candidate_requirement=deferred`, visible and unretired;
4. preserve applicable RC15 schema/read compatibility, Morfeo MCP resources, RC15 Supervisor instructions, project identity, mutable state and gateway ownership semantics; qualify the optional Hermes review-return count's absence/fallback as a disclosed candidate difference;
5. remain local-only: no pushed tag, package publication, stable-release claim or unrelated fork adoption.

No compatibility bridge analogous to historical C9/M10 is presumed. RC15 emits schema 5 and the candidate path uses `--candidate-check` for exact fork qualification, but an exact RC15→RC16 isolated reader/transition probe must establish applicability. If it contradicts the premise, stop before live effect and return the incompatibility instead of inventing another bridge.

### Later fork adoption — separate objective

The separate later fork adoption may select HLP-433 under its own authority and canary. It is not an acceptance criterion for #494 and MUST NOT be bundled into RC16 merely because it is present in the current fork tip.

## RC16 qualification design

### 1. Source and candidate identity

Prepare RC16 only from a clean reviewed Aether candidate descended normally from current `main`. Verify version/package/tag coherence, candidate wheel identity, release-lock schema, exact fork commit/tree/digest and HLP candidate coverage. Mutable branch tips, local checkout recency and patch replay are not release inputs. Keep the RC15 Aether SOUL and canonical review-skill bytes unless an authorized issue-specific adjustment requires a reviewed correction.

Candidate HLP qualification MUST positively show HLP-428 present at `58f8c37…` and HLP-433 deferred/absent without retirement. Assert the selected fork source lacks the optional RC15 count, that Aether's review guidance accepts missing context by consulting durable task history, and report that compatibility limitation. Canonical reconciliation freshness remains a separate `--check` gate; a stale aggregate cannot be relabeled as a candidate PASS.

### 2. Isolated RC15 → RC16 transition oracle

Before live effect, qualify the exact transition with disposable Aether data/state/config/cache roots and isolated Kanban/Project registries. Use actual installed RC15-compatible and RC16 candidate readers/interpreters rather than one mocked manager. RC15 was published; do not rebuild its immutable distribution into a fictitious predecessor or write to its live store. Preserve unrelated owner TUIs, profiles and service/process identities when later moving to the live cutover.

At minimum prove:

- RC15 active-record/release-lock bytes remain readable and immutable;
- RC16 release/lock identifies `58f8c37…` and `a2a9b374…`;
- RC15 → RC16 succeeds in isolation with mutable profile/session/project/board state preserved;
- rollback target RC15 remains coherent and can be selected once if the authorized live transition requires fallback;
- RC16 can be reselected after the isolated rollback without rewriting old release records;
- wrong commit, wrong source digest, missing HLP-428 component, dirty/foreign fork checkout and malformed lock refuse before activation;
- HLP-433 remains explicitly deferred rather than silently disappearing.

Earlier RC12→RC14 and RC14→RC15 tests are patterns, not the oracle. RC16 evidence must exercise the actual RC15 predecessor and the new fork identity.

### 3. Review and integration gates

This objective touches release/lifecycle and Hermes-baseline identity. Apply the project testing standard in `CONTRIBUTING.md`:

- focused candidate-HLP/release-lock/lifecycle tests;
- HLP-428 fork regression module and affected fork surface at exact `58f8c37…`, plus focused missing-count fallback verification for the retained RC15 review guidance;
- `uv run --frozen python scripts/run_tests.py`;
- Ruff check and format-check;
- mypy;
- documentation/public-artifact checks;
- build of wheel/sdist and package-installed candidate checks;
- `git diff --check`;
- normal protected PR/check/merge path with no squash/rebase/force/bypass for pipeline integration.

Reuse source-phase HLP-428 evidence only where the exact bytes and criterion are unchanged. Final RC16 release/transition and installed behavior require new evidence at their own revisions. Observe ordinary review elapsed-time/rework evidence against #425 without asserting faster agent behavior on the basis of these deterministic checks or creating a synthetic campaign.

### 4. Live cutover

A live effect is allowed only after the reviewed RC16 merge/candidate, exact isolation PASS, clean active-state preflight and a non-mutating `aether update --local ... --dry-run --json` returning the expected RC15→RC16 plan with no identity blocker. If other objectives or owner sessions cannot be preserved, defer the effect rather than close them for convenience.

Before effect, record private witnesses for:

- active release id/version and active-record hash;
- manager/runtime package identity;
- exact fork source commit/tree/digest;
- Project registry identity;
- relevant board/session counts or stable preservation witnesses;
- selector/projection/service identity;
- Aether-owned gateway process identity;
- unrelated service/process exclusions.

Use the supported managed lifecycle only. Do not edit `active.json`, `record.json`, state DBs or `runtime/current` manually. The transition launcher must survive the Aether-owned gateway refresh it initiates and remain independent of the originating TUI and gateway process trees/cgroups. After activation require `aether doctor=result=ready`, RC16 selected, exact HLP-428 fork identity loaded and no projection/service mismatch. A fallback, if needed, is one prequalified RC15 rollback followed by stop/reassessment, not a retry campaign.

### 5. Effective-runtime #494 canary

Issue #494 closes only after a real disposable canary on the selected RC16 runtime demonstrates the behavior that failed originally. Observe the RC15 review guidance as available during ordinary execution; this canary proves #494, not a general reduction in task duration.

Use an isolated Aether board plus separate profile Project registries. Construct the supported shape:

1. Project-bound Supervisor continuation with an explicit `dir` workspace and no session affinity;
2. canonical Project exists in the origin binding while the child-creating profile lacks a convenient local registry row, reproducing the cross-profile boundary;
3. create an Implementer child with explicit canonical Project and direct parent edge, leaving child workspace selection to the supported path;
4. assert persistence keeps the canonical non-null Project and materializes a fresh project worktree rather than scratch;
5. child reaches same-card review;
6. a distinct Supervisor review claim/receipt exists with `source_status=review`;
7. review completes without a claim/reclaim loop, null worker identity or lost Project;
8. cross-Project mismatch refuses before task/run/event insertion;
9. generic non-Aether scratch compatibility remains constructible;
10. bounded deterministic review failure reaches an inspectable terminal/blocked state with cleared claim/worker ownership and no unverified origin signal.

Do not replay or repair the historical incident board. Canary artifacts are disposable; unrelated live boards/sessions/projects are preservation witnesses, not fixtures.

## Acceptance and closeout

#494 is accepted only when all of the following are supported at exact revisions:

- RC16 source is normally reviewed and merged;
- local candidate identity is `1.0.0rc16` / `1.0.0-rc.16` / local-only `v1.0.0-rc.16`;
- release lock binds exact Hermes `58f8c37…` and digest `a2a9b374…`;
- HLP-428 is required/present and HLP-433 remains deferred;
- exact RC15→RC16 isolation qualification passes with state preservation and coherent rollback evidence;
- live managed cutover selects RC16 and `aether doctor` is ready;
- the effective-runtime Project/child/review canary passes every applicable #494 criterion;
- unrelated state/services remain preserved;
- Supervisor completes normal Git/GitHub closeout and records criterion-linked evidence.

Only then close GitHub Issue #494 as completed with the exact merge, candidate, active runtime and canary receipts. A source merge, tag, candidate check or doctor alone is insufficient.

## Authority, exclusions and release disposition

Owner instruction authorizes autonomous #494 recovery as RC16, local managed activation needed to prove #494, normal reviewed Git/GitHub closeout, and closing #494 after acceptance. It does **not** authorize package publication, pushed release tags, stable `1.0.0`, PyPI, manual deployment, credential changes, router/model changes, unrelated Hermes upgrades, HLP-433 activation, or repair of #460/#475/#404. Keep the prior RC15-tagged release immutable and its stopped execution board blocked rather than silently repurposing it.

Supervisor owns decomposition, independent review, integration, candidate preparation/cutover coordination, canary evidence and closeout. Implementers own reversible unit-local implementation/test choices. Morfeo remains design steward and performs final contract-result reception; Morfeo does not take over product implementation.

Current design classification: `release_impact=patch`, `release_action=prepare`, `release_channel=prerelease`. Publication remains excluded.
