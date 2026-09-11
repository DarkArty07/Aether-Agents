# Pragmatic reliability closure — Supervisor task breakdown

**Status:** verified decomposition for Objective Contract `oc_c780a10d94b78d85@v1`.

**Derived by:** Supervisor (role). Material design remains Morfeo's; this file is
execution decomposition and does not widen the contract.

**Source contract:** `.aether/objective-contracts/oc_c780a10d94b78d85/v1.md`
(SHA-256 `0fdd7931cc77e75eecc20e37c32f1352afbd8bf91869340aa092ac20e12905a5`).

**Objective board:** `oc-12027989a08f41cda82c54ff1bfb6b03-c780a10d94b78d85-v1`
(project `p_227bd972`, `worktree_base_ref` `0a41438a13a0655b07703910b605e595f55aa660`).

Card bodies remain the executable unit deliveries; this file is the canonical
breakdown and coverage map.

## Receipt

| Check | Observed |
| --- | --- |
| Portable project | `.aether/project.toml` project id matches the envelope `12027989-a08f-41cd-a82c-54ff1bfb6b03` |
| Contract bytes | `sha256sum` = `0fdd7931cc77e75eecc20e37c32f1352afbd8bf91869340aa092ac20e12905a5`; matches the card envelope |
| Base commit | `0a41438a13a0655b07703910b605e595f55aa660` is the executed HEAD of this objective worktree and the board `worktree_base_ref` |
| `origin/main` at receipt | `466ee72cbbc984cbeec48ad929e84eeaa4d24f87` (the contract commit's parent) |
| Maintained fork | `DarkArty07/aether-hermes`; remote `refs/heads/aether-main` = `6551b7c31cc665d59103c6d89cb5e0c60666f803` (matches the contract). Fork Actions are disabled, so fork "required checks" do not exist; fork acceptance is the unit's own executed suites plus independent review |
| Live runtime (evidence only) | Hermes editable checkout `home/.venv-hermes/src/hermes-agent` (dirty, behind the fork) and Aether runtime `home/runtime/aether-agents-main` (clean at `466ee72`). Neither is an implementation base |
| Design sufficiency | `specs/pragmatic-reliability-eight/{spec,plan,research,quickstart}.md` decide all eight outcomes, the reuse-before-build rule, the serialized cron lane, the fail-closed boundary, the ledger/retirement requirement, the #403 tombstone choice, activation and the release conclusions. No missing product decision was found; no unit may invent one |
| Profiles | `implementer`, `supervisor`, `morfeo` exist. Kanban capacity: `max_in_progress_per_profile_overrides` supervisor=1, implementer=3 |
| Concurrent state | Active Monitor flow `oc_f8c9fc9320587cf3@v4` (terminal card `MON-V4-INT-R` running) and residual contract `oc_291b2fb34b413d92@v2` (U396/U399 candidates complete, U397 blocked on Monitor, terminal integration not done). Preserve both; do not race them |
| Project Canonical Skills | `.aether/skills/aether-observe/SKILL.md` applies to progress/observation; `aether-observe` is Morfeo's surface and this flow does not stand in for it |

## Cross-artifact executability

| Concern | Settled conclusion | Execution consequence |
| --- | --- | --- |
| Reuse before building | `oc_291b2fb34b413d92@v2` is the sole implementation lane for #396/#397/#399 until its accepted commits reach `main` | This objective consumes them in `PR8-CONSUME`, which is an explicit blocked gate. No unit reimplements them |
| Dual repository | Aether owns #388 (product guard), #357/#403 (CI evidence and public-artifact reconciliation); the maintained fork owns #372, #393, the #388 framework side and the #385 guidance correction | Fork units work in isolated disposable worktrees of `DarkArty07/aether-hermes@6551b7c…`; Aether units work in Aether project worktrees. Never edit the live editable runtime or `home/runtime/aether-agents-main` |
| Ledger hotspot | `HERMES_LOCAL_PATCHES.md`, `patches/hermes/**`, `specs/001-aether-v1-productization/evidence/hermes-patch-reconciliation/**`, `scripts/validate_hermes_patch_reconciliation.py` and `tests/test_hermes_patch_reconciliation.py` share one digest/registry surface across all fork behaviors | One serialized Aether evidence lane (`PR8-LEDGER`). Fork units never edit those files; they hand over exact commits and behavior facts. This is a bounded serialization reason, not a reason for new architecture |
| Fork file ownership | The cron lane needs `cron/**`, `tools/cronjob_tools.py`, `tools/kanban_tools.py`, `gateway/**`, `agent/**` (auto-subscribe path); the review lane needs `agent/prompt_builder.py` (`KANBAN_GUIDANCE`) and its focused tests | `PR8-CRON` and `PR8-REVIEW` are two disjoint fork branches; `agent/prompt_builder.py` is `PR8-REVIEW`-exclusive, `tools/kanban_tools.py` and `hermes_cli/kanban_db.py` are `PR8-CRON`-exclusive. A unit that finds it must edit a file outside its surface stops and returns to Supervisor |
| Publication | Implementation units commit on their unit branch, push fork feature branches and open the fork PR; they never merge, never open/merge the Aether PR and never close issues | Fork PR merges, the single Aether integration PR, checks, merge, activation, canaries, issue reconciliation and cleanup belong to `PR8-INT` |
| Activation | The runtime loads Aether from `home/runtime/aether-agents-main/src` (editable `.pth`) and Hermes from `home/.venv-hermes/src/hermes-agent` | `PR8-INT` adopts the exact merged revisions at a worker-safe boundary, uses the accepted #399 operation for any editable-metadata refresh, and restarts only if changed loaded code requires it |
| Testing | Regression-first with RED on the pristine base and GREEN on the candidate, on disposable state | No retry, skip, timeout increase, `PYTHONPATH` runtime workaround or check bypass counts as a fix. Probes scrub inherited `HERMES_KANBAN_*` and delegated-child identity. Aether gates per `quickstart.md` |
| Out of scope | #227, #352, unrelated issues, the Monitor feature itself, #348 fork-adoption redesign, providers/models/credentials, publication, deployment, bypass, history rewrite, direct SQL repair of live boards | Report incidental defects separately; only a defect that actively blocks this objective may be folded in as the smallest tracked unblocker (#403 is the only pre-authorized one) |

## Requirement coverage

| Source | Unit | Owning repository | Notes |
| --- | --- | --- | --- |
| R372 | `PR8-CRON` | Fork | One effective profile-scoped script-root contract across validation, lifecycle scan, execution and diagnostics |
| R393 | `PR8-CRON` | Fork | Trusted commissioning origin restored only as request-local Kanban subscription context |
| R388 (framework side) | `PR8-CRON` | Fork | Cron session workdir persisted from the trusted launch context before tools run |
| R385 | `PR8-REVIEW` | Fork | `KANBAN_GUIDANCE` no longer treats a terminal/release child alone as a substitute for unit review; the HLP-362 invariant is preserved, not reimplemented |
| #372/#385/#393 + HLP-362 portable evidence | `PR8-LEDGER` | Aether | Patch artifacts, ledger entries, reconciliation registry/digests, retirement tests, and removal of the false expectation that the unpatched pinned baseline provides downstream behavior |
| R388 (Aether side) | `PR8-CONTRACT` | Aether | `objective_contract` fails before any draft/final/primary mutation when a non-empty native session has no valid Git workspace binding |
| R357 | `PR8-CI` | Aether | Exact PluginContext lane passes on 3.11/3.12/3.13 without retry; otherwise a causal fix. No speculative change |
| B403 | `PR8-CI` | Aether | Minimum non-bypass reconciliation: unsafe historical bytes leave the current artifact set with a portable tombstone; scanner returns green |
| R396, R397, R399 | `PR8-CONSUME` | Aether (external gate) | Consume the accepted `oc_291b2fb34b413d92@v2` results and expose the #399 operation through a supported Aether entry point |
| Aggregate integration, activation, closeout | `PR8-INT` | Both | Reviewed-commit integration, PR/checks/merge, exact runtime adoption, canaries, issue reconciliation, cleanup, release conclusions |

## Execution graph

```text
t_b92559c8 (Supervisor decomposition root)
    ├─ PR8-CRON      (implementer, fork lane: #372 + #393 + #388-framework)
    │     └─ PR8-CRON-REVIEW      (supervisor, independent unit review)
    ├─ PR8-CONTRACT  (implementer, Aether: #388 fail-closed boundary)
    │     └─ PR8-CONTRACT-REVIEW  (supervisor)
    ├─ PR8-REVIEW    (implementer, fork lane: #385 guidance)
    │     └─ PR8-REVIEW-REVIEW    (supervisor)
    ├─ PR8-CI        (implementer, Aether: #357 disposition + #403)
    │     └─ PR8-CI-REVIEW        (supervisor)
    ├─ PR8-CONSUME   (implementer, BLOCKED: external oc_291b2fb34b413d92@v2)
    │     └─ PR8-CONSUME-REVIEW   (supervisor)
    └─ PR8-LEDGER    (implementer, Aether ledger lane; parents: PR8-CRON, PR8-REVIEW)
          └─ PR8-LEDGER-REVIEW    (supervisor)

    PR8-INT (supervisor, terminal: integrate, publish, activate, canary, close)
      parents: root + all six review cards
```

Edges and why they exist:

- One review card per implementation unit (`plan.md` §D2): the implementation card's
  named child is an explicit review card, so completing it is the correct handoff even
  under the still-ambiguous worker guidance, and no unit can reach `done` unreviewed.
- `PR8-LEDGER → {PR8-CRON, PR8-REVIEW}`: it needs the exact pushed fork candidate
  revisions and it is the only writer of the shared ledger/digest surface. No other
  edge is inferred from listing order.
- `PR8-INT → {root, six review cards}`: integration consumes independently reviewed
  units plus the external consume gate, never an unreviewed implementation card.
- `PR8-CONSUME` has **no** parent edge and starts `blocked`: a parent edge would
  auto-promote it when the root completes, which would defeat the external gate.

Declared independence: `PR8-CRON`, `PR8-CONTRACT`, `PR8-REVIEW` and `PR8-CI` share no
writable file and can execute concurrently; implementer capacity (3) simply queues the
fourth. `PR8-LEDGER` is serialized by the shared ledger surface, not by preference.

## Shared decisions (stamped into every implementation unit)

1. Authority is `oc_c780a10d94b78d85@v1`; skills grant none. Never edit the contract artifact.
2. Aether work starts in this objective's project worktree on a branch based at `0a41438a…`. Fork work starts from `DarkArty07/aether-hermes` `origin/aether-main` = `6551b7c31cc665d59103c6d89cb5e0c60666f803` in an isolated disposable worktree/clone; never check out `aether-main` in place and never edit the live editable runtime `home/.venv-hermes/src/hermes-agent` or `home/runtime/aether-agents-main`.
3. Fork target hash mismatch versus `6551b7c…`, or an Aether tree that does not contain `0a41438a…`, is a stop: return to Supervisor.
4. Regression-first: identical focused tests RED on the pristine base and GREEN on the candidate. Fork suites run with `HERMES_TEST_FILE_RETRIES=0`. No pass-on-retry, skip, timeout increase, `PYTHONPATH` runtime workaround, real credential, live board, production DB or paid model as fixture.
5. Writable-file ownership is exclusive. A needed edit outside the unit's surface returns to Supervisor instead of being taken.
6. Unit evidence is `specs/pragmatic-reliability-eight/evidence/PR8-<unit>.md` on the unit branch, unique per unit. No secrets, operator-local paths, private destinations or raw private model output in evidence or artifacts.
7. **Review topology while #385 is still inactive.** The activated worker guidance
   treats *any* pre-created dependent child as sufficient reason to `kanban_complete`
   instead of requesting review, which is exactly the #385 defect. Every unit therefore
   gets its own pre-created Supervisor review card (the contract's `plan.md` §D2
   two-card lane): the implementation card completes because its named child is an
   explicit review card, and the terminal card depends on review cards, never directly
   on unreviewed implementation cards. The reviewer issues its verdict from that review
   card's own claimed run. A bounded correction returns as a new linked rework card
   gated into the review card, not as an inline same-card round.

8. Implementation units do not merge, do not open/merge the Aether PR and do not close issues. Fork units may push their feature branch and open the fork PR only (no merge).
9. `HERMES_LOCAL_PATCHES.md`, `patches/hermes/**`, `specs/001-aether-v1-productization/evidence/hermes-patch-reconciliation/**`, `scripts/validate_hermes_patch_reconciliation.py` and `tests/test_hermes_patch_reconciliation.py` are `PR8-LEDGER`-exclusive.
10. Local judgement belongs to the implementer (private helper names, fixture arrangement, equivalent reversible structure, whether to extend an owned test file). Public result shape, issue attribution, shared interfaces, acceptance oracles and preservation gates may not vary.
11. No provider/model/credential/settings change, no destructive or irreversible operation, no force-push or history rewrite, no package publication, no deployment, no check bypass, no live-board SQL.
12. Preserve the active Monitor flow, unrelated worktrees/branches/stashes/boards and unmerged evidence.

## Unit deliveries

Each card body carries the full executable delivery (source, outcome, inputs,
boundaries, judgement, verification, dependencies, completion). Summary:

- **PR8-CRON** — fork candidate for #372, #393 and the #388 framework side, plus the
  pushed branch, open fork PR, and `evidence/PR8-cron.md` describing exact commits and
  executed suites.
- **PR8-CONTRACT** — Aether fail-closed boundary in the objective-contract plugin path,
  with the six negative fixtures and zero-mutation assertions.
- **PR8-REVIEW** — fork candidate correcting `KANBAN_GUIDANCE` about terminal/release
  children versus same-card review, with focus on the already-present review invariant
  left intact.
- **PR8-CI** — #357 integrated/post-merge no-retry evidence (Morfeo's direct receipt is
  an input, not the acceptance oracle) and the #403 tombstone/removal reconciliation
  that returns the public-artifact check to green without bypass.
- **PR8-LEDGER** — the single Aether representation of the fork behaviors: portable
  patches, ledger entries, reconciliation registry and digests, retirement tests, and
  the corrected baseline expectation.
- **PR8-CONSUME** — blocked; consumes the external #396/#397/#399 results and exposes
  the #399 reconciliation through a supported Aether entry point.
- **PR8-INT** — terminal Supervisor integration: reviewed-commit integration on current
  `origin/main`, fork PR merges, one Aether PR with required checks, normal merge, exact
  runtime adoption, focused canaries, issue reconciliation, cleanup and the separate
  release conclusions.

## Compatibility and release

Unit-level compatibility evidence is collected per unit; aggregate conclusions belong
to `PR8-INT`. The contract fixes defect behavior without changing a public product
interface: expected aggregate `release_impact=patch`, `release_action=defer`,
`release_channel=none`. No unit may publish or deploy.
