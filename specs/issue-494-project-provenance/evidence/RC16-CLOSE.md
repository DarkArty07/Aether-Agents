# RC16-CLOSE — final report: acceptance map, disposition, residue and observations

## Context

- **Unit:** `RC16-CLOSE` (Supervisor, terminal card)
- **Objective Contract:** `oc_c770cea3db51d97e@v2` AC8
- **Material design:** `specs/issue-494-project-provenance/plan-release.md`
- **Integrated revision:** `main` at `4800690aed7eb030b7568881ad7af744992335ba` (tree
  `3b7fc87fcae99e324d21a3d9447f51894b58c575`)
- **Precondition asserted, not assumed:** every prior lane is `done`, `main` carries the merged
  candidate, and `aether doctor` is ready on `1.0.0rc16` with the pinned Hermes source. A green
  merge, a tag or a doctor result alone was not treated as acceptance.

## Acceptance map (AC1–AC8)

| Criterion | Producer | Exact revision / artifact | Observed result |
| --- | --- | --- | --- |
| **AC1** Identity and lock binding | `RC16-IDENT` (`513c9dd3`), `RC16-INT` (`d9e39646`), `RC16-HLP` (`c2b4a901`) | `VERSION` = `1.0.0rc16`; display `1.0.0-rc.16`; annotated local tag `v1.0.0-rc.16` at `d9e396462948ef3721612f6909371e22efb10115`; fork pin `58f8c37a49…` / digest `a2a9b374…` | Supported: identity coherent across source, workflow pin and tests; release lock binds the exact fork commit and digest; the tag is local-only (absent from the remote) and RC15 is immutable |
| **AC2** HLP coverage and preservation | `RC16-HLP` (`c2b4a901`) | reconciliation aggregate + entries at the pin | Supported: HLP-428 **required/present**; HLP-433 **deferred/absent/unretired**; `refusing_hlps` empty; wrong/missing HLP-428 source refuses before preparation; the retained review guidance's documented durable-history fallback covers the missing *optional* count, disclosed as a limitation rather than an enforcement gate |
| **AC3** Exact transition | `RC16-TRANS` (`72713359`) + independent verification (`t_936c3948`) | oracle receipt at the integrated revision | Supported: 8/8 scenarios pass (isolation, predecessor immutability, candidate identity, transition cycle with rollback/reselection, refusal matrix, HLP reconciliation, review fallback, fork regression); independent verification reproduced the confinement invariant over 21 adversarial vectors with a pre-fix/fixed discriminator and zero live mutation |
| **AC4** Repository/package gates | `RC16-INT` (`1038b0a9`) | integrated `main` | Supported: exact-Hermes runner **2054 passed / 73 skipped / 0 failed**; Ruff check + format-check; mypy 77 files; documentation and public-artifact scanners; `git diff --check` clean; release bundle built and re-verified with no failed probes; protected PR merged with all seven required checks passing without bypass |
| **AC5** Live cutover | `RC16-CUTOVER` (evidence merged `8814b485`) | installed release `1.0.0rc16-14fa64728b9aaeae` | Supported: non-mutating preview planned RC15→RC16 with no blockers; exactly one managed cutover succeeded from a durable launcher outside the gateway process tree; doctor ready on rc16 with the pinned source; hooks 22/22; no pending transitions or projection mismatch; the one pre-effect refusal is recorded with its zero-mutation proof and the RC15 fallback was never consumed |
| **AC6** Effective supported path | `RC16-CANARY` (evidence merged `daeb3354`, corrected `4800690a`) | selected installed runtime, exercised-module origin printed | Supported: Project-bound continuation with explicit `dir` workspace and no affinity; cross-profile boundary reproduced; the child persisted the **non-null canonical Project** and a **fresh real git worktree**; it reached same-card review and was claimed by a **distinct reviewer identity with `source_status=review`**; no claim/reclaim loop, no null worker, no lost Project |
| **AC7** Error/control paths | `RC16-CANARY` | same runtime | Supported: explicit cross-Project mismatch refuses **before persistence** (identical task/run/event counts = zero rows); generic non-Aether scratch collaboration constructible; bounded deterministic failure reaches an inspectable `blocked` state with claim/worker cleared, `gave_up` present, **no `origin_signal`**, zero notified subscribers and no re-claim |
| **AC8** Closeout | this card | this report | Supported with one recorded limitation (see below): acceptance map by producer and revision, three separate release conclusions, integrated verification on merged `main`, truthful issue disposition, residue audit and observation record |

**Unsupported or partially supported:** none of AC1–AC7 is unsupported. AC8 carries one
non-applicability rather than a defect — the root guidance update was **not** performed (see
"Limitations").

## Release conclusions (three separate fields)

- `release_impact = patch`
- `release_action = prepare`
- `release_channel = prerelease`

Supporting compatibility evidence: the candidate carries RC15's product surface forward with one
bounded adoption (HLP-428 required, previously deferred) and no public interface removal; the
release-lock schema remains 5 and RC15's schema-readable state is preserved. These three fields are
independent of one another: a merge does **not** imply a release, and `prepare` with a
`prerelease` channel is not a compatibility impact. Nothing was published; the annotated tag is
**local-only** and the prerelease channel describes the candidate class, not a published artifact.

## Integrated verification (final, on merged `main`)

| Gate | Result |
| --- | --- |
| Exact-Hermes runner | 2054 passed, 73 skipped, 0 failed (999 s) |
| Ruff check | All checks passed |
| Ruff format-check | 200 files already formatted |
| mypy | no issues in 77 source files |
| Documentation checker | passed |
| Public-artifact scanner | passed |
| Reconciliation `--check` at the pin | `current`; 33 records, present 30, absent 1 (the deferred HLP-433 module), unverified 2 |
| `git diff --check` over the objective range | clean |
| Pinned fork digest re-derivation | 9,378 materialized files → `a2a9b374…` = contract |

## Issue disposition

Issue #494 is **CLOSED / completed**, and the criteria above support that disposition.

One mechanism fact is recorded rather than smoothed over: the issue was closed automatically at
merge time (2 seconds after PR #524 merged, referencing its merge commit), because the
pull-request **title** contained a closing keyword. That closure therefore preceded the cutover
and canary evidence rather than following it, so GitHub's sequencing was not the contract's
"close only after acceptance" order. No pull request in this objective used a closing keyword
intentionally; this was an unintended side effect of the title wording. Because all criteria are
now supported, the completed disposition is correct on the merits, and the criterion-linked
receipts were attached to the issue for the reader. No further state change is required, and no
other issue was affected.

## Residue audit and cleanup

Audited inventory and action taken (each removal justified by durable merge evidence):

| Item | State | Action |
| --- | --- | --- |
| Objective root card and seven lane cards | all `done` | kept (board record is the durable execution evidence) |
| Objective worktrees for the closed lanes | clean, zero unpushed commits, all merged into `main` | removed; their private receipts were copied into the objective's collected receipts area first |
| Merged objective branches (six) | ancestors of `main` | deleted locally with `-d` (merge-checked) |
| Superseded duplicate local branch (an earlier draft of the canary correction, its intent already in `main` via the correction PR) | unmerged by ancestry, but content superseded | deleted locally only, after diffing it against `main` to confirm the intent was delivered |
| Remote duplicate branch of that same superseded draft | still present on the remote | **preserved**: remote ref deletion was refused by the protected-edge guard as an unauthorized external mutation. Not routed around. It is harmless dead residue whose content is already in `main`; removing it needs owner/authorized action if desired |
| Live root objective branch and its worktree | active lane record | preserved |
| Local annotated tag `v1.0.0-rc.16` | points at the rc16 merge commit | preserved, **not pushed** |
| RC15 (release, tag, records) | predecessor | preserved untouched |
| Stopped RC15 execution board and the historical incident board | preservation witnesses | untouched, not revived, not edited |
| Unrelated worktrees, branches, stashes and services | other objectives | preserved |
| Transient closeout verification checkout | disposable | removed after use |

A state drift was found and corrected during this audit: the **primary checkout** was sitting on
this objective's branch rather than `main`, and the objective's own worktree was on a temporary
evidence branch. Both were restored to their correct branches, and local `main` was
fast-forwarded to the integrated revision. The unrelated dirty file was preserved byte-for-byte
across the fast-forward (its upstream content is unchanged in that range).

## Preservation statement

The stopped RC15 board, the historical incident board, other objectives' boards and worktrees,
and unrelated services remain intact. The RC15 release record and lock are byte-identical to the
pre-state and its tag is unmoved. The unrelated dirty file
`specs/001-aether-v1-productization/plan-rc6.md` is preserved and still dirty with the same
content hash. Live board task/comment/run totals are unchanged across the canary window, and only
this objective's own board saw control-plane writes.

## Limitations (recorded, not smoothed)

1. **Root guidance was not reconciled to RC16.** The locally archived root guidance still
   describes the earlier RC15 framing for this issue. The intended update was **denied by a real
   protected-instruction guard** whose message forbids retrying the same edit by another path, and
   the denial stands as a stop rather than a workaround. No acceptance criterion depends on that
   text (verified: no test gate reads RC16 identity from it), so this is a guidance-maintenance
   limitation, not a blocked criterion. It is **not** reported as reconciled, and no owner
   approval is inferred for it.
2. **Evidence-density differences between documents.** The navigation index does not restate the
   rejected-candidate and immutability clauses that the README and the troubleshooting row carry;
   parity across those three documents is not claimed.
3. **One unit's evidence quoted a weaker whitespace check** (an argless `git diff --check`, a
   no-op once committed). The committed-range form is clean and is what this report cites.
4. **One evidence record required correction after merge.** An earlier revision of the canary
   record claimed a live-board byte comparison that was not an independent second measurement;
   it was withdrawn in `main` and replaced with the checks actually observed. Recorded here so the
   objective's history shows the correction rather than only its result.
5. **Canary scope.** The canary ran on a disposable board with a simulated reviewer process, so it
   evidences the runtime's lane semantics for this defect, not a second live process.

## Observation record for the review-flow question

Real, observed signals from this objective's own lanes. **No synthetic campaign was run**, no
minimum speedup is claimed, and this is **not** agent-behaviour qualification.

| Lane | Runs | Review returns (`changes_requested`) | Wall span from first start to last end |
| --- | --- | --- | --- |
| Root decomposition | 1 | 0 | 92.7 min |
| `RC16-IDENT` | 2 | 0 | 48.7 min |
| `RC16-HLP` | 4 | 1 | 82.0 min |
| `RC16-TRANS` | 6 | 2 | 217.6 min |
| `RC16-TRANS-DELTA` (independent verification) | 2 | 0 | 21.3 min |
| `RC16-INT` | 2 | 0 | 188.4 min |
| `RC16-CUTOVER` | 2 | 0 | 20.3 min |
| `RC16-CANARY` | 1 | 0 | 12.8 min |

Observations, stated as observations: the two-return ceiling was reached exactly once
(`RC16-TRANS`), and that unit's third round was resolved by one bounded reviewer-authored
correction followed by an independent verification lane rather than by a third ordinary return —
consistent with the convergence guidance. The longest lane spans include genuine waiting on
sequential gates (isolation before live effect, live effect before canary) and one worker restart
caused by the cutover's own gateway restart; they are elapsed spans, not work content. Several
spans include test suites exceeding fifteen minutes on a loaded host, which is why wall-clock
durations are not a measure of review efficiency. No claim is made that any of this is faster or
slower than an earlier release.

## Terminal result

RC16 is prepared, merged, locally tagged (unpublished), selected on this machine and coherent;
the defect's behaviour is reproduced working on the selected runtime; the issue's completed
disposition is supported by criterion-linked evidence; objective-owned residue is cleaned with
every preservation obligation intact; and the remaining limitations are recorded above.
