# #494 — RC15 exact-version adoption and effective-runtime qualification

**Status:** Morfeo successor design at Aether `82893e2f227a2f02d2c761f9f743aa38651a7178`, recovering the useful boundaries of the retired rc8→rc9→rc10 design against the current rc14 runtime. Owner direction authorizes this as the next release-candidate objective and requires Issue #494 to close once its effective-runtime acceptance is actually supported. This document is design, not activation evidence.

## Destination and current identities

The source-only #494 repair is already reviewed and integrated. Maintained-fork PR #16 merged HLP-428 at exact commit `58f8c37a49b341f25b8fdd6310542fe932031b8d`, Git tree `a93162c1a867202b03c12fa372c71029152fdcf7`. Aether's deterministic archived-source digest for that exact commit is `a2a9b374bd2022c7f96242b0ab2c95691119262c925389eb3820ca627c581144`. Aether main already contains the HLP-428 ledger/reconciliation and the candidate-HLP gate.

The effective installation at design time is Aether `1.0.0rc14`, release `1.0.0rc14-4a1ef558417d4873`, `aether doctor=result=ready`, with maintained-fork Hermes `aed6591a69f453a1867b73628603e7b53ba40ffc` and source-tree digest `cc1ebf94ad167979951e7b956ef3a8c448e96fd3389c93cddf60f8f883bb5ce7`. HLP-428 is therefore not active yet.

The fork later advanced to `621047dc1c10cceb2825013cc8bb611b4d0e8de1` for HLP-433. That later repair is intentionally **not** part of RC15. Keeping RC15 pinned to `58f8c37…` makes the #494 runtime proof causal and leaves HLP-433 for a separate successor RC.

## Release sequence

### RC15 — #494 adoption and closure candidate

RC15 is package `1.0.0rc15`, display `1.0.0-rc.15`, local annotated tag identity `v1.0.0-rc.15`. It carries the current rc14 Aether product surface and changes the selected Hermes source from `aed6591a69…` to exact `58f8c37a49…`.

The candidate MUST:

1. bind release-lock source mode `maintained_fork` to repository `https://github.com/DarkArty07/aether-hermes`, branch `aether-main`, commit `58f8c37a49…`, deterministic source-tree digest `a2a9b374…`, exact artifact closure and provenance;
2. make HLP-428 `candidate_requirement=required`;
3. keep HLP-433 `candidate_requirement=deferred`, visible and unretired;
4. preserve all rc14 schema/read compatibility, Morfeo MCP resources, project identity, mutable state and gateway ownership semantics;
5. remain local-only: no pushed tag, package publication, stable-release claim or unrelated fork adoption.

No compatibility bridge analogous to historical C9/M10 is required unless current executable evidence disproves the rc14 reader/candidate-gate premise. RC14 already emits schema 5, reads the needed prior forms and uses `--candidate-check` for exact fork qualification. If an exact rc14→rc15 isolation probe contradicts that premise, stop and return the incompatibility instead of inventing another bridge.

### RC16 — separate successor

The next fork adoption after #494 may select `621047dc1c10…` for HLP-433 under its own objective and canary. RC16 is not an acceptance criterion for #494 and MUST NOT be bundled into RC15 merely because it is the current fork tip.

## RC15 qualification design

### 1. Source and candidate identity

Prepare RC15 only from a clean reviewed Aether candidate descended normally from current `main`. Verify version/package/tag coherence, candidate wheel identity, release-lock schema, exact fork commit/tree/digest and HLP candidate coverage. Mutable branch tips, local checkout recency and patch replay are not release inputs.

Candidate HLP qualification MUST positively show HLP-428 present at `58f8c37…` and HLP-433 deferred/absent without retirement. Canonical reconciliation freshness remains a separate `--check` gate; a stale aggregate cannot be relabeled as a candidate PASS.

### 2. Isolated rc14 → rc15 transition oracle

Before live effect, qualify the exact transition with disposable Aether data/state/config/cache roots and isolated Kanban/Project registries. Use actual rc14-compatible and rc15 candidate readers/interpreters rather than one mocked manager.

At minimum prove:

- rc14 active-record/release-lock bytes remain readable and immutable;
- rc15 release/lock identifies `58f8c37…` and `a2a9b374…`;
- rc14 → rc15 succeeds in isolation with mutable profile/session/project/board state preserved;
- rollback target rc14 remains coherent and can be selected once if the authorized live transition requires fallback;
- rc15 can be reselected after the isolated rollback without rewriting old release records;
- wrong commit, wrong source digest, missing HLP-428 component, dirty/foreign fork checkout and malformed lock refuse before activation;
- HLP-433 remains explicitly deferred rather than silently disappearing.

Existing rc12→rc14 tests are patterns, not the oracle. RC15 evidence must exercise the actual rc14 predecessor and the new fork identity.

### 3. Review and integration gates

This objective touches release/lifecycle and Hermes-baseline identity. Apply the project testing standard in `CONTRIBUTING.md`:

- focused candidate-HLP/release-lock/lifecycle tests;
- HLP-428 fork regression module and affected fork surface at exact `58f8c37…`;
- `uv run --frozen python scripts/run_tests.py`;
- Ruff check and format-check;
- mypy;
- documentation/public-artifact checks;
- build of wheel/sdist and package-installed candidate checks;
- `git diff --check`;
- normal protected PR/check/merge path with no squash/rebase/force/bypass for pipeline integration.

Reuse source-phase HLP-428 evidence only where the exact bytes and criterion are unchanged. Final RC15 release/transition and installed behavior require new evidence at their own revisions.

### 4. Live cutover

A live effect is allowed only after the reviewed RC15 merge/candidate, exact isolation PASS, clean active-state preflight and a non-mutating `aether update --local ... --dry-run --json` returning the expected rc14→rc15 plan with no identity blocker.

Before effect, record private witnesses for:

- active release id/version and active-record hash;
- manager/runtime package identity;
- exact fork source commit/tree/digest;
- Project registry identity;
- relevant board/session counts or stable preservation witnesses;
- selector/projection/service identity;
- Aether-owned gateway process identity;
- unrelated service/process exclusions.

Use the supported managed lifecycle only. Do not edit `active.json`, `record.json`, state DBs or `runtime/current` manually. The transition launcher must survive the Aether-owned gateway refresh it initiates. After activation require `aether doctor=result=ready`, rc15 selected, exact HLP-428 fork identity loaded and no projection/service mismatch. A fallback, if needed, is one prequalified rc14 rollback followed by stop/reassessment, not a retry campaign.

### 5. Effective-runtime #494 canary

Issue #494 closes only after a real disposable canary on the selected rc15 runtime demonstrates the behavior that failed originally.

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

- RC15 source is normally reviewed and merged;
- local candidate identity is `1.0.0rc15` / `1.0.0-rc.15` / local-only `v1.0.0-rc.15`;
- release lock binds exact Hermes `58f8c37…` and digest `a2a9b374…`;
- HLP-428 is required/present and HLP-433 remains deferred;
- exact rc14→rc15 isolation qualification passes with state preservation and coherent rollback evidence;
- live managed cutover selects RC15 and `aether doctor` is ready;
- the effective-runtime Project/child/review canary passes every applicable #494 criterion;
- unrelated state/services remain preserved;
- Supervisor completes normal Git/GitHub closeout and records criterion-linked evidence.

Only then close GitHub Issue #494 as completed with the exact merge, candidate, active runtime and canary receipts. A source merge, tag, candidate check or doctor alone is insufficient.

## Authority, exclusions and release disposition

Owner instruction authorizes this bounded next-RC recovery, local managed activation needed to prove #494, normal reviewed Git/GitHub closeout, and closing #494 after acceptance. It does **not** authorize package publication, pushed release tags, stable `1.0.0`, PyPI, manual deployment, credential changes, router/model changes, unrelated Hermes upgrades, HLP-433 activation, or repair of #460/#475/#404.

Supervisor owns decomposition, independent review, integration, candidate preparation/cutover coordination, canary evidence and closeout. Implementers own reversible unit-local implementation/test choices. Morfeo remains design steward and performs final contract-result reception; Morfeo does not take over product implementation.

Current design classification: `release_impact=patch`, `release_action=prepare`, `release_channel=prerelease`. Publication remains excluded.
