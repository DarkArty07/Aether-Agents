# #475 Same-card cross-profile review on affinity-bound Supervisor card — Supervisor task breakdown

**Status:** verified decomposition for Objective Contract `oc_de8365729879a0cd@v1`.

**Derived by:** Supervisor

**Source contract:** `.aether/objective-contracts/oc_de8365729879a0cd/v1.md`
(SHA-256 `54b6e9d00aaff5b95422c2204fd9747b093eaad43678d66c7cb16aab44f8eb57`)
on Aether base `79a0827805df5a4d7936cf450eea308b1e0e42f8`.

**Maintained-fork baseline:** `DarkArty07/aether-hermes` `aether-main`
`30b4846a2c8063528d491f48950b3b341b0ce7d7` (tree `49189104a6888ef604ff0733d97b6b05e25b0d33`).

**Owning issue:** [#475](https://github.com/DarkArty07/Aether-Agents/issues/475) — stays **OPEN**
after this source phase.

**Technical design:** `specs/issue-475-review-affinity/plan.md` and `specs/issue-475-review-affinity/research.md`
(Morfeo, Aether `91bebcee57d9d4b745ce45eb62c30cd2150f3043`). This file is the Supervisor-owned
execution breakdown; it derives work from the finalized contract and does not replace or widen it.
Card bodies are the executable deliveries and native board state is the durable record.

## Receipt

| Check | Observed |
| --- | --- |
| Portable Project | `.aether/project.toml` `project_id` `12027989-a08f-41cd-a82c-54ff1bfb6b03` equals the task envelope and the contract front matter; board `oc-12027989a08f41cda82c54ff1bfb6b03-de8365729879a0cd-v1` carries `aether_project_id`/`aether_contract_id`/version matching the contract, Hermes Project `p_227bd972`, `default_workdir` at the Aether root and `worktree_base_ref` `79a0827805df5a4d7936cf450eea308b1e0e42f8` |
| Contract bytes | Present at root commit `79a08278` and in this worktree; `sha256sum` equals `54b6e9d00aaff5b95422c2204fd9747b093eaad43678d66c7cb16aab44f8eb57` exactly |
| Base commit | Clean root HEAD equals `79a0827805df5a4d7936cf450eea308b1e0e42f8`; contract commit is that single commit over `91bebcee` and is not yet an ancestor of `origin/main` |
| Maintained-fork pin | `origin/aether-main` is `30b4846a2c8063528d491f48950b3b341b0ce7d7` (tree `49189104a6888ef604ff0733d97b6b05e25b0d33`), equal to the contract's inspected revision; **no fork pull request is open** and no branch named for `#475` exists locally or remotely |
| Loss point re-verified | `hermes_cli/kanban_db.py` `dispatch_once` calls `reserve_session_affinity` for direct-affinity cards with key `(board, project_id, flow_id, current_assignee)`. When `current_assignee` changes to a distinct reviewer on `request_review`, lookup fails and raises `AffinityRegistrationError("session affinity lease is missing or stale")`. No lease timeout is checked in that branch |
| Baseline file digests at the pin | `hermes_cli/kanban_db.py` git blob `3a0998054144a39963abdf4e2f61ee0174c5b5fe`, SHA-256 `9ed38688acba3d039985139a0b3cd928dd9ac1d65280c073bee87c384ed03af1`; `tests/hermes_cli/test_kanban_session_affinity.py` git blob `b253834b4949d2281b38af766888a4cda7e52f5b`, SHA-256 `0372fd675c04088d940e8a22363c6cc98fd225333dab78e6b4d77852d29c7cf9` |
| Fork execution environment | Supervisor materialized an isolated fork worktree at `/home/darkarty/Desktop/03_PROYECTOS/01_ACTIVOS/aether-hermes/.worktrees/fix-475-review-affinity` on branch `fix/475-review-affinity` at the exact pin, clean including untracked files, with working runner: `HERMES_TEST_FILE_RETRIES=0 scripts/run_tests.sh tests/hermes_cli/test_kanban_session_affinity.py -q` → 1 file, 73 passed, 0 failed, exit 0 (Python 3.11.15, pytest 9.1.1, 48 workers) |
| Next free audit identifier | `HLP-475` verified free in Aether and the fork; ledger sections end at `HLP-474` and reconciliation roster holds 37 entries |
| Aether baseline | On the untouched root: `scripts/check_documentation.py` passed; `scripts/check_public_artifacts.py --root .` passed; `scripts/check_hermes_baseline_drift.py --json` passed; `uv run --frozen python scripts/run_tests.py -- tests/test_hermes_patch_reconciliation.py -q` → 33 passed; git diff --check clean |
| Objective-caused manifest defect | The contract commit `79a08278` tracked `.aether/objective-contracts/oc_de8365729879a0cd/v1.md` but did **not** add it to the `policy.yml` expected-manifest list, so the `Validate canonical base manifest` step fails on this branch. Recorded as a bounded integration repair for `INT-475` (see shared decision 9), not a unit deliverable |
| Preserved live state | The installed Aether runtime pin, gateway service, and unrelated live boards are untouched by this decomposition. Historical failed card `t_c94430a7` is preserved read-only |
| Profiles and capacity | Existing `implementer` and `supervisor` profiles are sufficient; no new role, profile or capacity change is requested |
| Design sufficiency | The contract and plan settle the failing boundary, the qualification gate, the fresh subprocess launch semantics, absence of reviewer lease, return/rework restoration, fail-closed handling on damaged identity, and the source-only boundary. No material product or interface decision is missing |

## Cross-artifact executability

| Concern | Settled conclusion | Execution consequence |
| --- | --- | --- |
| Dual repository | The maintained fork owns the behavior and its focused tests. Aether owns the portable patch, ledger/reconciliation records, the public-artifact surfaces and its own PR | Fork work happens only in the isolated worktree at `/home/darkarty/Desktop/03_PROYECTOS/01_ACTIVOS/aether-hermes/.worktrees/fix-475-review-affinity`. The checkout whose branch is `aether-main`, the loaded editable runtime and the installed release are never edited or activated |
| Fork hotspot | The whole fix is localized to `hermes_cli/kanban_db.py` (`dispatch_once`, review provenance verification, and `_default_spawn` override suppression) plus its tests | **One** fork unit (`HF-475`). Two units editing `hermes_cli/kanban_db.py` on parallel branches is a declared collision under current policy |
| Portable bytes | The Aether patch, its digest and the reconciliation truth depend on the accepted exact fork delta | `AE-475` is serialized after same-card review of `HF-475`; the accepted commit is its required input, not an ordering preference |
| Fork ledger | The fork's `AETHER_FORK.md` is the fork-side record | `HF-475` preserves it and supplies the exact proposed paragraph; `INT-475` applies it on the branch it merges |
| Patch identity | `HLP-475` is verified free | Component id `HLP-475`; patch `patches/hermes/HLP-475-review-affinity-dispatch.patch`; ledger heading `## HLP-475 — …` (em dash); summary-table row; fragment `HLP-475.json`; roster and digest table in `tests/test_hermes_patch_reconciliation.py` |
| Aggregate pin | Pinned at `30b4846a…`. A declared path absent at the pin is recorded `absent` and refuses candidate preparation | `AE-475` generates at `30b4846a…` and declares as `components` only paths present there. `INT-475` re-pins to the merged fork revision and may then declare the new module |
| Ledger/registry hotspot | `HERMES_LOCAL_PATCHES.md`, `patches/hermes/**`, fragments, generated aggregate/preflight, `.gitattributes` and the `policy.yml` allow-list share one digest/registry surface | `AE-475` owns that surface inside one card. Fork units never edit it. `INT-475` alone re-generates after the fork merge |
| Aether integration branch | Implementation units must land on the branch that becomes the Aether PR | `AE-475` and `INT-475` operate on the decomposition branch; `HF-475` commits only in the fork. Nothing is pushed by an implementation unit |
| Evidence hotspot | `specs/issue-475-review-affinity/evidence/HLP-475.md` is the single objective report | `AE-475` writes producer facts; `INT-475` appends only observed merge, check, cleanup and release-readiness facts |
| Publication and activation | Unit work stops at same-card review | `INT-475` alone pushes, opens and merges both normal PRs, re-pins the aggregate, comments on the issue and cleans objective residue. No tag, release, package publication, deployment, `aether update` or runtime activation |
| Exclusions | Historical failed card `t_c94430a7`, live gateway, and unrelated boards remain untouched; `#475` is not closed by a source-only merge | Incidental findings are reported without being absorbed or mutated |

## Requirement coverage

| Contract source | Unit | Observable coverage |
| --- | --- | --- |
| 475-01 | `HF-475`, `INT-475` | Verified Aether root/Project/contract/board identity + direct-affinity Supervisor card + registered Supervisor session + durable distinct-profile `review_requested` event launches fresh reviewer under its own profile in same candidate worktree without Supervisor resume/session/token/flow/overrides or reviewer lease; reviewer can claim run and issue verdict |
| 475-02 | `HF-475`, `INT-475` | Reviewer `request_changes` restores original Supervisor assignee and registered session; second review is fresh; approval preserves terminal bit and downstream dependency behavior |
| 475-03 | `HF-475`, `INT-475` | Missing/corrupt review event, root, identity, original row/session/workspace, wrong flow or live owner fails closed through existing lifecycle without fresh fallback, transferred lease or synthetic board repair |
| 475-04 | `HF-475`, `INT-475` | Existing same-profile opted-in unit review (FR-735a/737c) and generic Hermes review retain their respective behavior |
| 475-05 | `HF-475`, `AE-475`, `INT-475` | RED at base, GREEN at candidate, affected fork regressions, HLP apply/reconstruction provenance, Aether reconciliation tests, protected PR checks and green merges; Issue #475 commented with source-only record and stays OPEN |
| Deliverables 1–3 | all units | Fork source repair with exact merge identity; portable HLP-475 artifact, ledger, fragment, aggregate and evidence; normal PRs and final merge receipts with separated release conclusions |

## Shared decisions (binding in every unit)

1. Authority is Objective Contract `oc_de8365729879a0cd@v1` at SHA-256
   `54b6e9d00aaff5b95422c2204fd9747b093eaad43678d66c7cb16aab44f8eb57` plus this breakdown.
   Skills are procedure only. No unit may edit, copy, stage, commit or supersede the canonical
   contract, and no unit may widen the objective.
2. Aether work starts from this committed decomposition. Each unit verifies, before mutation,
   the contract digest, the base commit and this file at its committed revision. A mismatch
   returns to Supervisor; unrelated history is never imported to make a check pass.
3. Fork product work starts only in the isolated worktree of
   `https://github.com/DarkArty07/aether-hermes.git` at exact revision
   `30b4846a2c8063528d491f48950b3b341b0ce7d7`, branch `fix/475-review-affinity`, prepared by
   Supervisor at `/home/darkarty/Desktop/03_PROYECTOS/01_ACTIVOS/aether-hermes/.worktrees/fix-475-review-affinity`
   and reserved for `HF-475` as the single writer. Locate the repository by its remote URL.
   Never edit the checkout whose branch is `aether-main`, the loaded editable runtime, or another
   worker's worktree.
4. **Decided qualification and launch semantics.**
   - At a claimed **review** run of a direct-affinity Supervisor card, qualify the exception only when:
     (a) the latest matching `review_requested` transition shows original assignee is the Supervisor profile,
     current assignee is a different reviewer profile, and the claimed run has review provenance (`source_status == "review"`);
     (b) exact Aether opt-in root and exact native Project/portable Project/contract/board identity are corroborated
     using the existing FR-737c standard;
     (c) the card's normalized direct flow matches the original Supervisor flow;
     (d) the exact registered original-profile row, session, and workspace exist and match the card's canonical flow
     workspace, with live owner/lease or superseded-worker holds respected.
   - For a qualified case:
     - Keep `session_affinity`, skills, and model/provider/reasoning fields unchanged on disk.
     - Launch the reviewer under its own profile in the same candidate worktree with `affinity=None` (no `--resume`,
       no session ID, no lease token, no flow selector env vars).
     - Suppress Supervisor-pinned skills, model, provider, and reasoning overrides for the reviewer subprocess
       (do not inherit Supervisor pins; reviewer policy may supply the reviewer's own procedure).
     - Do NOT reserve or create a reviewer-affinity row or lease.
   - On `request_changes`, the existing return path restores the original Supervisor assignee and registered session.
   - Fail closed on damaged/missing identity, missing original row/session/workspace, wrong flow or live owner.
     Do not fall back to fresh on `AffinityRegistrationError`.
5. **Existing review classes out of bounds.** Same-profile unit review (FR-735a/737c) and generic Hermes
   review must retain their behavior unchanged. Do not remove direct affinity from the card.
6. Use disposable Git repositories, boards, Project registries, profile homes, SessionDB files and
   state roots for testing. Strip no live board, HOME, registry or session. Verify outer board is
   unchanged before and after test runs.
7. **Aggregate pin.** `AE-475` generates the aggregate and preflight at selected revision
   `30b4846a2c8063528d491f48950b3b341b0ce7d7` with a clean checkout at that revision, and declares as
   `components` only paths that exist there. `INT-475` re-pins to the merged fork revision after the fork
   merge and may then add any new test module. `observed_at_utc` must postdate every input it summarizes.
8. `.github/workflows/policy.yml` carries exactly two new lines for this objective: the new patch path
   in the allow-list (`AE-475`), and the contract artifact `.aether/objective-contracts/oc_de8365729879a0cd/v1.md`
   in the expected-manifest list (`INT-475`, a bounded integration repair owned by Supervisor, attributed
   as such and verified by simulating the manifest check). Exactly one `.gitattributes` whitespace line
   for the new patch is added by `AE-475`.
9. Sensitive material stays out of everything committed: no machine paths, operator layout, secrets,
   credentials, private model output or raw runtime state in the patch, ledger, fragments, aggregate,
   evidence or card handoffs. Repository-relative references only.
10. Writable ownership below is exclusive; concurrent edits to one file across units are forbidden.
11. Unit compatibility evidence is `patch`. The terminal aggregate conclusion is
    `release_impact=patch`, `release_action=defer`, `release_channel=none`, consistent with the source-only
    boundary.
12. Fork Actions remain disabled for `aether-hermes`: report them **NOT RUN**, never green.
    `#475` stays open after this phase; its effective-runtime and live-call obligations are successors.
    No activation, restart, service or profile edit, `aether update`, tag, release, package publication
    or deployment.
13. Implementers commit only intended paths with Conventional Commits, report exact commands, revisions,
    totals, skips and first-attempt failures, and then request same-card review with
    `kanban_request_review(reviewer="supervisor")`. No push, pull request, merge or issue mutation from
    an implementation unit.
14. `AGENTS.md` and the contract-owning artifacts are preserved. `INT-475` records explicit non-applicability
    or coherent update and rechecks root guidance before closure.

## Execution graph

```text
t_7588d486 Supervisor decomposition root
    -> HF-475 fork cross-profile review dispatch on affinity-bound Supervisor card (Implementer)
       -> same-card Supervisor review
       -> AE-475 portable HLP-475 artifact, ledger reconciliation and evidence (Implementer)
          -> same-card Supervisor review
    -> INT-475 terminal integration and dual-repository closeout
       (Supervisor, same flow, terminal=true; depends on root and both reviewed units)
```

`HF-475` is concentrated because the correction is localized to the review dispatch gate in
`hermes_cli/kanban_db.py` plus its tests, and parallel production units on that file are a declared
collision under current policy. `AE-475` cannot run independently: its byte artifact and every
reconciliation claim derive from the accepted fork commit. `INT-475` is integration and publication,
not a substitute for either same-card unit review. There is no honest implementation parallelism
in this dependency chain, and none is manufactured.

## HF-475 — fork cross-profile review dispatch on affinity-bound Supervisor card

- **Source:** 475-01, 475-02, 475-03, 475-04, and the fork half of 475-05; contract Objective,
  Decisions and Assumptions, In Scope, Testing Standard, Stop Conditions; shared decisions 2–6, 9–13.
- **Outcome:**
  1. Immediate RED reproduced at the unchanged base `30b4846a...` demonstrating `session affinity lease is missing or stale`
     when a distinct reviewer is dispatched for a claimed review run on a direct-affinity Supervisor card.
  2. At candidate revision, the same scenario passes GREEN: the distinct reviewer launches under its own profile
     in the same candidate worktree with `affinity=None` (no resume, no session ID, no token, no flow env vars)
     and without Supervisor-pinned skills/overrides. The reviewer has a claimed review run and can issue a verdict.
  3. `request_changes` restores original Supervisor assignee and registered session/affinity.
  4. Second review on the same card qualifies and launches fresh; approval preserves terminal bit and dependencies.
  5. Negative cases pass: missing/corrupt event, missing original row/session/workspace, wrong flow or live owner fail
     closed through existing lifecycle without fresh fallback or transferred lease.
  6. Existing unit review (FR-735a/737c) and generic Hermes review remain green.
  7. Subprocess argv/env inspection proves reviewer isolation.
  Excludes Aether portable artifacts, ledgers, publication and activation.
- **Inputs:** the isolated fork worktree at `/home/darkarty/Desktop/03_PROYECTOS/01_ACTIVOS/aether-hermes/.worktrees/fix-475-review-affinity`
  at `30b4846a...` (tree `49189104...`) with the working documented runner; baseline digests in receipt;
  spec.md, plan.md and research.md as technical references.
- **Boundaries:** writable `hermes_cli/kanban_db.py` and `tests/hermes_cli/test_kanban_session_affinity.py`
  (and/or one new focused test module). Preserve existing affinity fencing, `register_session_affinity`,
  card `session_affinity` column on disk, `AETHER_FORK.md`, lockfiles, workflows, and all paths outside the fork.
- **Judgement:** private helper functions, event parsing details, internal structure of qualification checks,
  fixture layout and test case organization. Do not weaken fail-closed semantics, do not transfer leases/tokens
  across profiles, and do not introduce blanket fresh fallbacks.
- **Verification:** RED first with `HERMES_TEST_FILE_RETRIES=0` recorded against unchanged base; then GREEN at candidate.
  Minimum affected run: `HERMES_TEST_FILE_RETRIES=0 scripts/run_tests.sh tests/hermes_cli/test_kanban_session_affinity.py -q`.
  Run compilation, Ruff check/format on touched scope, and `git diff --check`. Outer board must remain unchanged.
- **Dependencies:** decomposition root `t_7588d486`.
- **Completion:** local fork commit(s) on `fix/475-review-affinity` attributable to this objective; handoff with
  exact commit and tree, measured RED/GREEN evidence, negative matrix, subprocess argv/env evidence, proposed
  `AETHER_FORK.md` paragraph, compatibility `patch` and remaining risks; then `kanban_request_review(reviewer="supervisor")`.
  No Aether edit, push, pull request or merge.

## AE-475 — portable HLP-475 artifact, ledger reconciliation and evidence

- **Source:** 475-05 (Aether side); Deliverables 2 and 3; shared decisions 2, 7–13.
- **Outcome:**
  1. The accepted `HF-475` fork delta is captured byte for byte as `patches/hermes/HLP-475-review-affinity-dispatch.patch`
     with SHA-256, apply/reconstruction proof, rollback and retirement-gate record.
  2. `HERMES_LOCAL_PATCHES.md` gains detailed `## HLP-475 — …` section and summary table row.
  3. Reconciliation fragment `specs/001-aether-v1-productization/evidence/hermes-patch-reconciliation/entries/HLP-475.json`
     created according to schema.
  4. `specs/issue-475-review-affinity/evidence/HLP-475.md` records producer facts, exact revisions, and reproducible commands.
  5. `tests/test_hermes_patch_reconciliation.py` updated with HLP-475 in roster and digest table.
  6. `.gitattributes` gains one whitespace line for the patch.
  7. `.github/workflows/policy.yml` gains one allow-list line for the patch.
  8. Aggregate and preflight regenerated consistently.
- **Inputs:** independently reviewed `HF-475` commit and handoff; clean tree at accepted revision before patch derivation.
- **Boundaries:** writable `patches/hermes/HLP-475-review-affinity-dispatch.patch`, `specs/001-aether-v1-productization/evidence/hermes-patch-reconciliation/entries/HLP-475.json`,
  `specs/001-aether-v1-productization/evidence/hermes-patch-reconciliation.v1.json`, `specs/001-aether-v1-productization/evidence/hermes-patch-preflight.md`,
  `HERMES_LOCAL_PATCHES.md`, `.gitattributes`, `.github/workflows/policy.yml` (allow-list line only), `tests/test_hermes_patch_reconciliation.py`,
  and `specs/issue-475-review-affinity/evidence/HLP-475.md`. Preserve every other patch, fragment, validator, and contract.
- **Judgement:** exact wording of ledger entry, summary table placement, evidence presentation. Do not collapse or rename
  existing records, do not declare paths absent at pin, and do not record unobserved facts.
- **Verification:** patch apply/reconstruction against clean fork base; `tests/test_hermes_patch_reconciliation.py`;
  `scripts/check_documentation.py`; `scripts/check_public_artifacts.py --root .`; `scripts/check_hermes_baseline_drift.py --json`;
  Ruff check/format, MyPy and `git diff --check`.
- **Dependencies:** independently reviewed `HF-475`; accepted fork commit is the required input.
- **Completion:** local Aether commit(s) on decomposition branch; handoff with digest, reconstruction result, proposed
  ledger content, test outputs, compatibility `patch` and remaining risks; then `kanban_request_review(reviewer="supervisor")`.
  No push, pull request, merge or issue mutation.

## INT-475 — terminal integration and dual-repository closeout

- **Source:** all Deliverables, 475-01–05, Authority, Testing Standard and Stop Conditions; shared decisions 1–14.
- **Outcome:**
  1. Accepted `HF-475` and `AE-475` commits integrated in dependency order without squash, amend, rebase or force.
  2. Bounded integration repairs: `policy.yml` expected-manifest list gains `.aether/objective-contracts/oc_de8365729879a0cd/v1.md`;
     `AETHER_FORK.md` record applied on fork branch.
  3. Fork PR opened, checks verified, green merged into `aether-main`.
  4. Aggregate re-pinned if declared paths require it; Aether PR opened, checks verified, green merged into `main`.
  5. Issue #475 commented with truthful source-only record and stays **OPEN**.
  6. Objective-owned branches and worktrees cleaned only after durable merge evidence; unrelated residue preserved.
  7. Terminal report with separated release conclusions: `release_impact=patch`, `release_action=defer`, `release_channel=none`.
- **Inputs:** this committed decomposition and independently reviewed `HF-475` and `AE-475` commits and handoffs.
- **Boundaries:** integration-owned conflict, import, wiring, path and manifest corrections; `AETHER_FORK.md`;
  ledger/fragment/aggregate re-pinning; objective evidence report.
- **Verification:** repeat decisive 475-01/02 and negative routes at final fork revision; run fork test suite; run Aether
  bootstrap and quality gates; simulate `policy.yml` manifest check; observe protected PR checks; audit PRs, issue,
  branch/worktree cleanup, unchanged runtime pin and live board preservation; recheck root `AGENTS.md` coherence.
- **Dependencies:** decomposition root `t_7588d486` plus both independently reviewed implementation units.
  Same Supervisor flow and session affinity with `terminal=true`.
- **Completion:** the three release conclusions stated separately; release-readiness handoff naming remaining live adoption,
  rollback candidates, preservation witnesses and specific #475 acceptance not yet qualified.

## Authority and stop conditions

Follow the finalized Objective Contract. Ordinary isolated worktrees, disposable state, tests, local commits and routine
push, pull request, non-bypass merge, issue comment and objective cleanup in the two provisioned repositories are authorized,
using only existing access. Stop and return to Supervisor or Morfeo when the loss point is no longer the inspected review dispatch
boundary, the declared fork base changed incompatibly, patch reconstruction is not exact, a required test cannot isolate
state without external access, preservation of unrelated work would require live mutation, a manifest or ledger conflict
cannot be reconciled by an ordinary non-rewriting merge, or a protected/live effect is required.
