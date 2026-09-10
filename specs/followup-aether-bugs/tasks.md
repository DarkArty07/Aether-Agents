# Follow-up Aether bugs — Supervisor task breakdown

**Status:** verified decomposition for Objective Contract `oc_7a35eca6393f18a7@v1`.

**Derived by:** Supervisor

**Source contract:** `.aether/objective-contracts/oc_7a35eca6393f18a7/v1.md`
(SHA-256 `1478ba06eedd98ccea156f320c432dcc9c1ee9ad9f0149b3883b56d98b6ea6c3`)
on Aether base `efa698ea8f4c5b62aa79670ac57e90f12dece7ab`.

**Maintained-fork baseline:** `DarkArty07/aether-hermes` `aether-main`
`8a6b33ae480373015178b80e87c88fe0abda3919`.

**Current upstream comparison:** `NousResearch/hermes-agent`
`6e07eb48387044dbcaf12490931c2b8ca7ec8653`; it retains the whole-card
review goal gate and the recovery-kind mismatch described by #369. This is
comparison evidence, not an upgrade target.

**Owning issues:** [#354](https://github.com/DarkArty07/Aether-Agents/issues/354),
[#369](https://github.com/DarkArty07/Aether-Agents/issues/369),
[#357](https://github.com/DarkArty07/Aether-Agents/issues/357),
[#352](https://github.com/DarkArty07/Aether-Agents/issues/352), with tracker
[#371](https://github.com/DarkArty07/Aether-Agents/issues/371). Issue
[#275](https://github.com/DarkArty07/Aether-Agents/issues/275) is explicitly
excluded and remains untouched.

This file is the Supervisor-owned execution breakdown. It derives work from the
finalized Objective Contract and does not replace or widen it. Card bodies are
the executable deliveries and board state is the durable execution record.

## Receipt

| Check | Observed |
| --- | --- |
| Portable project | `.aether/project.toml` contains `project_id = "12027989-a08f-41cd-a82c-54ff1bfb6b03"`, repository `DarkArty07/Aether-Agents`, default branch `main` |
| Contract bytes | SHA-256 matches the handoff envelope exactly |
| Recovered root | root HEAD equals contract base `efa698ea8f4c5b62aa79670ac57e90f12dece7ab`; the base is an ancestor, the contract path is present at HEAD, and unrelated primary-flow commit `da7bcef5854763bf5b70a5540f707722c158dfbb` is not an ancestor |
| Primary / remote | `origin/main` is `89c372fa6af09c6cbd5ce9a18dc7dd78ed70dfc4`; the contract commit is one commit ahead and the primary's unrelated active lineage is preserved rather than published wholesale |
| Maintained fork | remote `aether-main` is `8a6b33ae480373015178b80e87c88fe0abda3919`; the provisioned checkout is read-only evidence until a unit creates an isolated nested worktree from that SHA |
| Upstream | current inspected `HEAD` is `6e07eb48387044dbcaf12490931c2b8ca7ec8653`; current source still judges request-review against the whole task goal and restricts goal-mode blocks to dependency/needs_input |
| Issues | #354, #369, #357, #352 and #371 are OPEN; #275 is OPEN and excluded |
| Design sufficiency | Objective Contract decisions and acceptance settle source ownership, priority, dispositions, privacy, review, closeout and stop conditions; no missing product interface blocks decomposition |
| Knowledge | bound project and revision match; derived graph is unavailable, so current source, Git, issues and prior evidence were inspected directly |
| Profiles / capacity | the existing `implementer` and `supervisor` profiles are available; no new role/profile/capacity is required |
| Project Canonical Skills | none under `.aether/skills/`; applicable Aether Canonical procedures govern |
| Root guidance | `AGENTS.md` is usable for local work and tests; its historical transition-only fork sentence is superseded by current `DESIGN.md` PD-49/PD-65 but broad source-mode reconciliation remains out of this objective |

The first receipt attempt correctly blocked because the provisioned root had the
wrong lineage and no contract artifact. Morfeo's bounded #354 recovery moved only
the clean unpublished objective branch to the recorded base. The wrong ref and
concurrent primary work remain preserved. Implementation card worktrees must be
materialized from the committed decomposition root before dispatch so this
known live-runtime defect cannot contaminate another unit while it is being fixed.

## Cross-artifact executability

| Concern | Settled conclusion | Execution consequence |
| --- | --- | --- |
| #354 current source | Aether already writes and validates `worktree_base_ref`; maintained fork `8a6b33a` already consumes it for new worktrees. Real root and descendant flows still reproduced wrong lineage because the active runtime ignored that source | FU-354 is an Aether-owned end-to-end qualification/hardening unit. It must exercise actual reconstructed/maintained behavior for both root and descendant worktrees, not restate metadata tests. Maintained-fork product bytes are read-only for this unit; a newly required fork behavior change returns to Supervisor |
| #369 current source | fork `tools/kanban_tools.py` and `hermes_cli/kanban.py` judge request-review against the same full goal as completion; `hermes_cli/kanban_db.py` tells recovery controllers to emit capability/recovery while the goal-mode tool allowlist rejects capability | One concentrated fork unit owns the phase-aware review gate and recovery signal path. Current upstream retains the defect, so there is no broader upstream adoption to import |
| #357 diagnostics | the failure recurred post-merge on Python 3.13; current runner preserves the test node plus outcome/hash summaries but not an actionable structured assertion/state class | One Aether unit owns privacy-safe structured failure evidence and conditional causal repair. A green retry alone keeps the issue open |
| #352 prior repair | current source already event-gates spawned-process admission and preserves the 10-second deadlines/one-commit invariant; prior bounded runs did not reproduce a product defect | One Aether unit requalifies the integrated source with deterministic interleavings and either makes the smallest causal correction or records a retained-open disposition |
| Priority | the contract requires #354/#369 first because they affect handoff/review authority | FU-357 and FU-352 are parent-gated on both reviewed P0 units. This edge is risk-order authority, not a file dependency |
| File ownership | P0 units use distinct repositories/Aether files. Wave-two units use qualification runner/plugin files versus lifecycle files | FU-354 and FU-369 may run together; FU-357 and FU-352 may run together after P0. No implementation unit shares writable files with a same-wave sibling |
| Reconciliation hotspot | a new #369 fork correction requires one portable patch, reconciliation entry, manifest update and both ledgers | FU-369 owns the Aether patch artifact/entry/reconciliation-test/policy surface. Terminal integration alone writes `HERMES_LOCAL_PATCHES.md` and fork `AETHER_FORK.md` after independent review |
| Publication | Implementers commit locally and never push, open/merge PRs, close issues, activate or publish | FBUG-INT owns fork-first then Aether closeout, checks, issue dispositions, cleanup and aggregate release conclusions |
| Telegram | progress is a projection of durable board state, not implementation evidence | FBUG-INT records whether the provisioned objective monitor existed/worked and removes only this objective's monitor at terminal closure; channel failure does not rewrite product evidence |

Inspected behavior at the exact baselines:

- Aether `ObjectiveContractStore.prepare_handoff` reads the authoring worktree HEAD,
  verifies exact final and marker bytes, and passes the primary Project path only to
  board provisioning. `hermes_plugin` writes/validates the exact 40-character
  `worktree_base_ref`.
- Maintained fork `8a6b33a` resolves `worktree_base_ref` from board metadata and uses
  it for new-branch worktree creation, including the occupied-path fallback.
- Maintained fork `8a6b33a` still uses `_goal_mode_handoff_rejection(task, evidence)`
  for both completion and request-review, so the review handoff can be judged against
  the independent verdict it is trying to request.
- Its recovery-controller context explicitly instructs capability/recovery, while
  `_GOAL_MODE_BLOCK_ALLOWED_KINDS` accepts only dependency/needs_input.
- `scripts/qualify_observation.py` converts arbitrary pytest detail to bounded hashes
  and safe node IDs. That preserves privacy but did not retain the exact safe
  assertion/state class needed after the Python 3.13 recurrence.
- `tests/test_observation_lifecycle.py` already waits for both spawned contenders to
  reach a ready Event, catches child exceptions into result strings, keeps existing
  result/join deadlines and asserts one committed plus one stale transition.

## Requirement coverage

| Contract source | Unit | Observable coverage |
| --- | --- | --- |
| AC-2 / deliverable 4 / #354 | FU-354 | concurrent-flow root and descendant ancestry, exact artifact/digest, unrelated-lineage absence, primary/ref preservation |
| AC-3 / deliverable 5 / #369 | FU-369 | complete-to-review without circular verdict, independent reviewer, incomplete rejection, changes cycle, recovery origin signal/triage semantics |
| AC-4 / deliverable 6 / #357 | FU-357 | privacy-safe actionable diagnostic, exact Python 3.13 repeated qualification, conditional causal repair and post-merge disposition |
| AC-5 / deliverable 7 / #352 | FU-352 | deterministic interleaving and bounded repeated runs, exact one-commit invariant, causal repair or retained-open boundary |
| AC-1 / #275 exclusion | every unit + FBUG-INT | exactly four source bugs; no #275/provider/backend work or mutation |
| Deliverables 8–10 / AC-6–10 | FBUG-INT | reviewed commit integration, fork/Aether PR/check/merge, tracker/source-issue reconciliation, release fields, monitor/process/branch/worktree cleanup audit |
| Preservation / authority | every unit + FBUG-INT | no live activation/profile/home/credentials/settings, no raw DB, no force/history rewrite, no unrelated cleanup |

## Shared decisions (stamp into every implementation unit)

1. Authority is Objective Contract `oc_7a35eca6393f18a7@v1` at SHA-256
   `1478ba06eedd98ccea156f320c432dcc9c1ee9ad9f0149b3883b56d98b6ea6c3`.
   Skills are procedure only. Do not edit, supersede, exact-copy or stage the canonical
   contract from an implementation unit.
2. Aether work starts from the committed Supervisor decomposition rooted at contract
   base `efa698ea8f4c5b62aa79670ac57e90f12dece7ab`. Every unit independently verifies
   that base, this `tasks.md`, and the exact contract artifact/digest are in its ancestry,
   and that unrelated primary-flow commit `da7bcef5854763bf5b70a5540f707722c158dfbb`
   is not. A mismatch is a stop condition before mutation.
3. Fork work starts only in a nested isolated worktree of
   `DarkArty07/aether-hermes@8a6b33ae480373015178b80e87c88fe0abda3919`.
   Locate by remote/branch/SHA; never edit the protected `aether-main` checkout or the
   live/imported runtime. Recheck current upstream source before a correction; upstream
   movement never authorizes a broad merge.
4. Issue #275 is excluded. Do not inspect its provider/backend path, use credentials or
   paid traffic, or mutate/comment/close it. Do not absorb #367/#368/#348/#334/#317/
   #316/#274/#261/#251 or a newly noticed non-blocker.
5. Regression/cause first: execute identical failing behavior on the unchanged assigned
   base before a product correction. Tests-only qualification may pass identically when
   the contract permits a not-reproduced disposition; report that honestly. No timeout
   increase, assertion weakening, skip, retry-as-fix or fabricated GREEN.
6. Use temporary repositories, Projects, boards, databases, state roots and fake content.
   No live board/database, profile/home mutation, activation/reload, model request,
   credential, setting or service change.
7. Writable ownership below is exclusive. Return to Supervisor on a shared-file collision,
   target hash mismatch, new material interface, required live-runtime change, required
   #275 work, or third repair variant for one cause.
8. Unique portable evidence lives at
   `specs/followup-aether-bugs/evidence/<unit-id>.md`. No machine paths, raw private
   transcripts/responses, secrets, credentials or owner identity. Attach large logs to
   the native task rather than committing them.
9. Run `git diff --check`, focused/affected tests, Ruff check/format, MyPy/compileall as
   applicable, documentation/public-artifact gates, and the canonical full runner
   `uv run --frozen python scripts/run_tests.py`. Preserve and attribute known unrelated
   baseline failures rather than hiding them.
10. Implementers commit intended files with Conventional Commits, report exact commands,
    counts, skips/failures, commit/tree identity, preservation and unit compatibility,
    then use same-card `kanban_request_review(reviewer="supervisor")`. No push, PR,
    merge, issue mutation, ledger edit, monitor mutation, release or activation.
11. Unit compatibility is `patch` for a backward-compatible product/diagnostic fix and
    `none` for evidence/tests-only qualification. Terminal aggregate is expected
    `release_impact=patch`, `release_action=defer`, `release_channel=none`; contradictory
    compatibility evidence returns to Morfeo rather than being normalized.
12. `AGENTS.md` is preserved unless a unit's authorized change invalidates an actual
    operating instruction. The historical fork-policy inconsistency is owned by excluded
    reconciliation work and is recorded, not silently redesigned here.

## Execution graph

```text
Supervisor decomposition root
    ├── FU-354  #354 handoff lineage canary/hardening (Implementer, P0)
    ├── FU-369  #369 goal-mode review and recovery (Implementer, P0)
    ├── after both reviewed P0 units: FU-357 #357 PluginContext diagnostics (Implementer)
    ├── after both reviewed P0 units: FU-352 #352 lifecycle concurrency (Implementer)
    ├── same-card Supervisor review on every implementation unit
    └── FBUG-INT terminal integration/closeout (Supervisor, same flow)
```

FU-354 and FU-369 are independent: different production repositories and disjoint
Aether writable files. FU-357 and FU-352 are independent after the risk-order gate:
qualification runner/plugin versus lifecycle test/product surfaces. FBUG-INT is the only
ledger/publication/integration owner and does not replace unit review.

### FU-352 review-continuation recovery

FU-352 card `t_380c3e40` completed from its Implementer run without the required
same-card `review_requested` transition. Preserve that completed record; do not rewrite it
or claim that a same-card review occurred. The one-time downstream card `t_456a4924`
prospectively reviews exact candidate `83ad2a50a37b54ec5cdf78d4fbc05f197d51f295` and
records a distinct Supervisor verdict before FBUG-INT continues. This routing repair does
not weaken FU-352 acceptance or replace the normal same-card review lane. Terminal closeout
must name both the original omission and the separate recovery verdict; issue #385 tracks
the lifecycle defect.

## FU-354 — contract-root and descendant worktree lineage

- **Source:** Objective Contract AC-2, deliverable 4, #354; this unit.
- **Outcome:** a deterministic disposable concurrent-flow canary exercises actual Aether
  handoff provisioning plus actual reconstructed maintained-fork worktree resolution.
  With the primary checkout advanced on unrelated lineage, a root task and at least one
  descendant task begin at the recorded base or verified descendants containing the exact
  contract bytes/digest; the unrelated primary commit is absent from both ancestries; the
  primary status/bytes and all unrelated refs/worktrees remain unchanged. If current
  Aether + maintained source already passes, commit regression/evidence without a
  speculative product patch. Excludes #369, live runtime activation and fork product edits.
- **Inputs:** Aether `efa698ea8f4c5b62aa79670ac57e90f12dece7ab` with
  `src/aether_agents/objective_contracts/store.py` SHA-256
  `7d4473547c35ff142afd613d6ed4c98c9c785c22341d56a005d4ba97cf8e9d30`,
  `src/aether_agents/objective_contracts/hermes_plugin.py`
  `6e803f59f8b2e0fb2b74b85e51a8ec8776b6e44c18821f820e16dc1dbc53e130`,
  and `tests/test_objective_contracts.py`
  `8d38c15600ab5c44de5fe423b471da43decc4d39fb99623faed9227568386ff8`.
  Maintained fork `8a6b33a` and existing portable HLP-354 patch are read-only behavior
  inputs; test the real code in a disposable reconstructed checkout, not a copied helper
  or mock of worktree selection.
- **Boundaries:** writable `tests/test_objective_contracts.py`; Aether
  `src/aether_agents/objective_contracts/store.py`, `hermes_plugin.py`, and
  `execution_boards.py` only if the canary proves the defect remains in that Aether side;
  evidence `specs/followup-aether-bugs/evidence/FU-354.md`. Extend existing tests—do not
  add a new non-`specs/` file or edit policy/reconciliation/ledger files. Preserve every
  maintained-fork file, #369 surfaces, qualification/lifecycle files and the contract.
- **Judgement:** disposable subprocess/module-loading arrangement for the reconstructed
  maintained source; whether a demonstrated Aether defect belongs in store, provisioner
  or their existing tests. A required maintained-fork behavior change is not local
  judgement under this contract—return it.
- **Verification:** fail-first by running the canary against the unpatched exact public
  baseline/old HEAD behavior and observe root/descendant contamination; GREEN against
  reconstructed HLP-354/maintained behavior. Verify root and descendant `merge-base`,
  exact artifact SHA-256, unrelated-commit absence, stable refs/worktree list and primary
  status/bytes. Run the complete objective-contract suite, affected project-init and
  patch-preservation controls, then full canonical runner and static gates.
- **Dependencies:** decomposition root only; P0. Independent of FU-369 by repository and
  writable-file ownership.
- **Completion:** local Aether commit; FU-354 evidence; same-card Supervisor review; unit
  compatibility `none` if tests/evidence only or `patch` for a demonstrated Aether fix;
  no fork commit and no push.

## FU-369 — phase-aware goal-mode review and recovery

- **Source:** Objective Contract AC-3, deliverable 5, #369; this unit.
- **Outcome:** a complete goal-mode implementation can request independent review without
  the judge requiring the verdict that review will produce; incomplete work still fails
  the readiness gate; the independent reviewer alone approves or requests changes; self-
  approval remains impossible. The controller's exact recovery signal is accepted or
  deterministically translated through native APIs so it reaches the origin and preserves
  blocked/triage attention without widening arbitrary goal-mode block escape. Completion
  still evaluates the whole objective. Excludes live reload, permission widening and #354.
- **Inputs:** maintained fork `8a6b33ae480373015178b80e87c88fe0abda3919` with
  `tools/kanban_tools.py` SHA-256
  `2976db9ea59596d63461b0b2c548d75b1456d259127a57f68d7f654e26fac7cd`,
  `hermes_cli/kanban.py`
  `7ca3fbfaac25da7db9f5c4be009f414f440346d6cd861e5d6c910bece943dd25`,
  `hermes_cli/kanban_db.py`
  `e3c5e3a727afd82bda70cca82fd7bf5f63767a554e1191643bc6f4f8dfd3acab`.
  Current upstream `6e07eb4` retains the defect; compare exact current bytes again before
  implementation but do not import unrelated changes.
- **Shared interface decision:** completion and review request are distinct goal phases.
  Completion keeps the full objective gate. Review request judges implementation
  readiness using truthful summary/structured metadata and may not require an already-
  accepted reviewer verdict. Recovery may special-case or translate only the exact
  authoritative recovery route; simply adding every capability/transient block to the
  general goal-mode allowlist is forbidden.
- **Boundaries:** writable fork `tools/kanban_tools.py`, `hermes_cli/kanban.py`, and the
  narrowly required recovery-controller/context/unblock path in `hermes_cli/kanban_db.py`;
  fork tests `tests/hermes_cli/test_kanban_review_surfaces.py`,
  `tests/tools/test_kanban_tools.py`, `tests/hermes_cli/test_kanban_session_affinity.py`,
  and `tests/hermes_cli/test_kanban_cli.py` as required. Aether writable:
  `patches/hermes/HLP-369-goal-mode-review-recovery.patch`, the matching
  `specs/001-aether-v1-productization/evidence/hermes-patch-reconciliation/entries/HLP-369.json`,
  `tests/test_hermes_patch_reconciliation.py`, and only the exact new patch allowlist
  entries in `.github/workflows/policy.yml`; FU-369 evidence. Preserve `goals.py` unless
  the existing phase input cannot express readiness, all #354 files/tests, both ledgers,
  live runtime and the Objective Contract.
- **Judgement:** helper/API internal name; whether exact recovery is accepted as the
  capability/recovery pair or translated to an allowed durable kind while retaining the
  origin signal. Return if this needs lifecycle authority redesign, goal_mode disablement,
  generic permission expansion or a change to independent-review rules.
- **Verification:** RED on unchanged `8a6b33a`: readiness summary rejected for missing
  independent verdict and capability/recovery rejected. GREEN through real tool and CLI
  paths on a disposable board: complete implementation enters review; incomplete stays
  running; reviewer is different and can approve/request changes; re-review works;
  complete retains whole-goal gate; exact recovery reaches subscribed origin once;
  unresolved attention/triage is preserved; unrelated capability block cannot bypass the
  judge. Run focused tool/CLI/review/session-affinity suites with retries disabled, full
  fork runner, Windows-footgun check, Aether reconciliation tests, full Aether runner and
  `git diff --check` in both trees.
- **Dependencies:** decomposition root only; P0. Concentrated because review and recovery
  share native goal-mode lifecycle; independent of FU-354's Aether files.
- **Completion:** local fork commit(s) plus local Aether portable patch/entry/test commit;
  exact patch SHA and ledger paragraphs in FU-369 evidence; same-card Supervisor review;
  unit compatibility `patch`; no push/ledger edit/runtime reload.

## FU-357 — actionable PluginContext qualification diagnostics

- **Source:** Objective Contract AC-4, deliverable 6, #357; this unit.
- **Outcome:** the exact real PluginContext lane retains privacy-safe structured failure
  state sufficient to identify the failing phase and assertion/exception class without
  raw transcript, payload, local path or secret exposure. Diagnose the recurrent Python
  3.13 failure and make the smallest causal product/harness correction only when
  demonstrated. Repeated exact 3.13 qualification and 3.11/3.12 compatibility pass; a
  green retry or diagnostic-only improvement does not by itself close #357.
- **Inputs:** reviewed FU-354 and FU-369. Aether base contains
  `scripts/qualify_observation.py` SHA-256
  `f05ce794ea0dc1e01e97f91213ad79fb509376cb4129f935ec89f14f046a8082`,
  `tests/test_observation_qualification.py`
  `ae53b596df013a1cf4941e7caea5c3bdbad661ca74b61ffea4e4bd0afaecb1b4`.
  Historical passing 100-process evidence is not proof against the retained post-merge
  recurrence; preserve both histories.
- **Boundaries:** writable `scripts/qualify_observation.py`,
  `tests/test_observation_qualification.py`, and
  `src/aether_agents/observation/capture/hermes_plugin.py` only if a reproducible causal
  product defect points there; FU-357 evidence. Do not edit workflow policy, lifecycle,
  journal/storage, Objective Contracts or Hermes fork files. No raw pytest tail or private
  assertion values may be retained.
- **Judgement:** bounded allowlisted diagnostic schema and failure-phase names; custom
  exception/result plumbing versus an equally safe existing runner seam. Return if an
  actionable diagnosis would require raw output or secret/path-bearing fields.
- **Verification:** deterministic synthetic failures for registration, tool capture, API
  capture, unload and persisted-event/privacy phases first fail to provide structured
  classification on the baseline, then emit bounded allowlisted state on the candidate.
  Negative tests prove payload/assertion text, credentials, tokens and local paths remain
  absent. Run the named real harness and neighbors repeatedly in fresh Python 3.13
  processes with retries disabled, exact qualification on 3.13 and available 3.11/3.12,
  affected observation suite, full canonical runner, Ruff/MyPy/compileall and diff check.
  Terminal post-merge CI decides close versus retained-open.
- **Dependencies:** decomposition root plus reviewed FU-354 and FU-369; contract priority
  gate, not a source dependency. Independent of FU-352 files.
- **Completion:** local Aether commit or evidence-only disposition; FU-357 evidence;
  same-card Supervisor review; compatibility `patch` for diagnostic/product change or
  `none` for evidence only; no push or issue mutation.

## FU-352 — concurrent lifecycle result collection

- **Source:** Objective Contract AC-5, deliverable 7, #352; this unit.
- **Outcome:** current integrated lifecycle behavior is exercised under deterministic
  competing transitions and bounded repeated unchanged/candidate runs. Exactly one
  transition commits, one becomes stale with `ACTIVE_RELEASE_CAS_MISMATCH`, both child
  results are collected, and active/journal invariants hold. Correct a demonstrated
  product/fixture cause without deadline inflation/assertion weakening, or retain #352
  open with exact non-reproduction evidence and next boundary.
- **Inputs:** reviewed FU-354 and FU-369. Aether current
  `tests/test_observation_lifecycle.py` SHA-256
  `8a1fa15733cbe496d2d76a327fce35d92f0eb54e05d52ce368bb2807e854783d` and
  `src/aether_agents/lifecycle.py`
  `cbea7f1ffd3efcbb8c98904a0541314944370827a4c0187108b33053bb32ad87`.
  The merged fixture already uses per-child ready Events and catches child exceptions;
  do not repeat that change as new proof.
- **Boundaries:** writable `tests/test_observation_lifecycle.py` and
  `src/aether_agents/lifecycle.py` only for a demonstrated causal synchronization defect;
  FU-352 evidence. Preserve PluginContext/qualification, journal/storage, Objective
  Contract, policy and fork files.
- **Judgement:** deterministic barrier/interleaving placement, bounded repetition count
  sufficient to test the demonstrated boundary, and fixture versus product attribution.
  A new materially different lifecycle cause returns to Supervisor/Morfeo.
- **Verification:** unchanged-base named test and bounded sequential/concurrent fresh-
  process repetitions with retries disabled; instrumented child admission/result
  collection and lock/CAS boundaries without sleep-as-ordering; candidate reruns only
  after a causal RED. Keep existing deadlines and exact one-commit assertions. Run the
  full lifecycle module, full canonical runner, Ruff/MyPy/compileall and `git diff --check`.
- **Dependencies:** decomposition root plus reviewed FU-354 and FU-369; contract priority
  gate. Independent of FU-357 files.
- **Completion:** local Aether commit or evidence-only disposition; FU-352 evidence;
  same-card Supervisor review; compatibility `patch` only for a causal compatible product
  fix, otherwise `none`; no push or issue mutation.

## FBUG-INT — terminal integration and closeout

- **Source:** Objective Contract deliverables 8–10, AC-6–10, all four reviewed units;
  this unit.
- **Outcome:** preserve each accepted unit commit and integrate in dependency order
  without squash/amend/rebase/force. Merge the maintained-fork correction first when
  FU-369 changed it; pin its merge SHA in Aether patch/ledger evidence; then integrate
  Aether commits, run combined acceptance, push the normal branch, open the PR, obtain
  required checks, diagnose only objective-caused failures, merge green without bypass,
  reconcile #354/#369/#357/#352 and tracker #371 from exact dispositions, and clean only
  proven merged objective residue. #275 remains open and unchanged. No release,
  activation or deployment.
- **Inputs:** independently reviewed FU-354, FU-369, FU-357 and FU-352 commits/evidence,
  this breakdown and exact contract. Preserve discrete commit provenance; a behavior gap
  returns through the implementation unit review path.
- **Boundaries:** mechanically implied conflict/import/wiring/path/build glue only;
  `HERMES_LOCAL_PATCHES.md`, fork `AETHER_FORK.md`, final FU-369 portable SHA/entry
  reconciliation, `specs/followup-aether-bugs/evidence/FBUG-INT.md`, and this `tasks.md`
  for factual integrated evidence. Any behavior/acceptance/interface change returns as
  implementation work. Do not edit the canonical contract or #275.
- **Verification:** re-run all four acceptance canaries on integrated trees, focused and
  affected suites, fork full runner with retries disabled, Aether canonical full runner,
  Ruff/format/MyPy/compileall/build/documentation/public-artifact/policy gates and diff
  checks. Inspect required and non-required GitHub checks. #357 closes only with causal
  repair plus repeated 3.13 and merged post-merge success; #352 closes only with causal
  reproduction/fix; otherwise keep either issue open with exact next boundary. Verify
  root `AGENTS.md` coherence and record the excluded fork-policy reconciliation reason.
- **Closeout:** use normal fork PR to `aether-main` if applicable, then Aether PR to
  `main`; issue/milestone reconciliation; remote merged-branch cleanup; local cleanup
  after durable merge evidence; preserve active/unmerged/review/concurrent/unrelated
  worktrees, branches, stashes and processes. Remove only the objective's monitor and
  record monitor/channel non-applicability if no provisioned monitor exists.
- **Dependencies:** decomposition root and all four independently reviewed units. Same
  Supervisor flow/session affinity; terminal=true. This card is integration, not unit
  review.
- **Completion:** aggregate conclusions reported separately:
  `release_impact=patch` only with compatible fixes (otherwise evidence-backed `none` if
  no product/diagnostic fix remains), `release_action=defer`,
  `release_channel=none`. Local integration alone is not success.

## Authority and stop conditions

Follow the Objective Contract. Routine local work, normal commits and authorized fork/
Aether GitHub closeout are permitted. Block the affected unit without stopping independent
siblings for missing/mismatched project/contract/base/source identity, contaminated
worktree ancestry, protected denial, required live/profile/credential/settings/activation
change, #275 scope, raw private diagnostics, material lifecycle/authority redesign, third
repair variant, or unowned shared-file collision. Correctable implementation failures use
same-card review/rework, not human-visible blocking. Preserve every unrelated ref and
runtime resource.
