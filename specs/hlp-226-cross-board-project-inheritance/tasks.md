# HLP-226 cross-board Project inheritance — Supervisor task breakdown

**Status:** verified decomposition for Objective Contract `oc_644c0b407d13366a@v1`.

**Derived by:** Supervisor

**Source contract:** `.aether/objective-contracts/oc_644c0b407d13366a/v1.md`
(SHA-256 `ca1264fb74ff07e1b0a5206e527e3dd6ec7676b8c82f07915f5f38a4308593a5`)
on Aether base `63dd88790e3a0ec78c465d6d6c85e051502e2428`.

**Maintained-fork baseline:** `DarkArty07/aether-hermes` `aether-main`
`415056fee527c5a2302370bd6dba56f84b9a4202`.

**Owning issue:** [#226](https://github.com/DarkArty07/Aether-Agents/issues/226).

This file is the Supervisor-owned execution breakdown. It derives work from the
finalized Objective Contract and does not replace or widen it. Card bodies are the
executable deliveries and native board state is the durable execution record.

## Receipt

| Check | Observed |
| --- | --- |
| Portable Project | Bound project tool reports `12027989-a08f-41cd-a82c-54ff1bfb6b03`, matching the envelope and contract |
| Contract bytes | Artifact is present at HEAD and SHA-256 matches the envelope exactly |
| Base / HEAD | Clean root HEAD equals `63dd88790e3a0ec78c465d6d6c85e051502e2428`; the base is therefore present and ancestral |
| Recovery | The first receipt correctly blocked on unrelated `f0e7978`; bounded recovery re-provisioned only this empty objective worktree at the declared base and preserved the unrelated primary lineage |
| Maintained fork | `DarkArty07/aether-hermes` remote `aether-main` resolves to exact baseline `415056fee527c5a2302370bd6dba56f84b9a4202`; baseline SHA-256 values are `2c36ef7887320fffe3c993ac5bc0d03091a232ebc9a85746e8bf937e042af58d` for `hermes_cli/kanban_db.py` and `1a7939e87fb9300094c0a9f6e98de347ff31628bf59e5f89a52775a92d89ffb1` for `tools/kanban_tools.py` |
| Current Aether main | Remote `main` was `2f72fcf420c0634da262c2f6dcbad0574c4b6a01` at decomposition; terminal closeout must fetch and reconcile the then-current compatible tip rather than assume it remains fixed |
| Design sufficiency | `spec.md`, `plan.md`, `quickstart.md`, pre-dispatch evidence and the Objective Contract settle recovery authority, path containment, affinity preservation, negative matrix, exact fork baseline, dual-repository closeout and no-activation boundary; no material product decision is missing |
| Knowledge | Bound Project and source revision match; the derived graph is unavailable, so current source, Git, issue and canonical artifacts were inspected directly |
| Profiles | Existing `implementer` and `supervisor` profiles are available; no new role, profile or capacity is required |
| Project Canonical Skills | None are installed under `.aether/skills/`; applicable Aether Canonical procedures govern |
| Root guidance | `AGENTS.md` remains coherent with the current downstream-fork authority and no-activation boundary; no guidance edit is required by decomposition |
| Issue state | #226 is OPEN and records the reproduced cross-board/shared-`dir` recurrence and this finalized contract |
| Decomposition checks | `git diff --check` and documentation validation passed. Documentation/public tests reported `16 passed, 1 failed`; the sole failure is the known immutable-contract operator-path finding tracked by excluded #364, and this decomposition changes only this new `tasks.md` |

## Cross-artifact executability

| Concern | Settled conclusion | Execution consequence |
| --- | --- | --- |
| Dual repository | Maintained Hermes owns the behavior and focused tests. Aether owns portable patch/reconciliation/evidence and its normal PR | Fork work occurs only in a nested isolated worktree at the exact fork baseline. Never edit the loaded editable runtime or the protected `aether-main` checkout in place |
| Fork hotspot | Project reconstruction spans `hermes_cli/kanban_db.py` and source/board propagation in `tools/kanban_tools.py`; their positive and negative tests exercise one authority boundary | One concentrated HF-226C unit owns both production paths and their fork tests. Splitting them would make two units decide and edit the same interface/tests |
| Portable bytes | Aether patch bytes, digest and reconciliation truth depend on the accepted exact fork delta | AE-226C is serialized after same-card review of HF-226C. This is a real artifact dependency, not an artificial risk-order edge |
| Patch identity | The existing HLP-226 and HLP-226b records remain historical components. This recurrence is the next bounded component | Name it `HLP-226c`; add `patches/hermes/HLP-226c-cross-board-project-inheritance.patch`; preserve the existing HLP-226b patch. The HLP-226 reconciliation fragment must carry all three components and bind both portable patch digests |
| Ledgers | `HERMES_LOCAL_PATCHES.md`, fork `AETHER_FORK.md`, and final merge evidence depend on reviewed/integrated commit identities | Implementers do not edit either ledger. They return exact proposed paragraphs. H226C-INT applies them after review and updates final evidence |
| Evidence hotspot | `specs/hlp-226-cross-board-project-inheritance/evidence/HLP-226C.md` is the single required objective report | AE-226C owns implementation/reconstruction evidence before integration. H226C-INT may append final review/merge/check/issue/cleanup facts only after AE-226C is accepted |
| Testing | The same disposable test must fail on unchanged `415056f` and pass on the candidate; row-only tests do not replace the two-step materialized-worktree E2E | HF-226C owns fail-first and candidate fork evidence. H226C-INT independently repeats AC-1/AC-2 and exact-byte reconstruction at final revisions |
| Current #354 runtime defect | The preceding receipt proved runtime worktree-base lineage can be wrong until manually recovered | Create cards parent-gated, then materialize their Aether worktrees from the committed decomposition root before completing this root. This is workspace preparation only; no product workaround or live-runtime mutation |
| Publication / activation | Implementers produce local commits and same-card review only | H226C-INT alone pushes, opens PRs, waits for checks, merges normally, reconciles #226 and cleans objective residue. No runtime activation, release or deployment |
| Exclusions | #275, #367, #368, unrelated #352/#357, profiles/config/providers/models/credentials/settings, database rewrites and the dirty editable Hermes runtime are excluded | Report incidental findings without absorbing or mutating them |

## Requirement coverage

| Contract source | Unit | Observable coverage |
| --- | --- | --- |
| H226C-FR-001 / AC-1 | HF-226C | Board-bound recovery from current source row plus exact board metadata; opaque prior-board leaf; no worker Project registration |
| H226C-FR-002 / AC-1 | HF-226C | Same-flow terminal retains Project, shared `dir`, exact path/flow, `terminal=true`, provenance and dependency gate |
| H226C-FR-003 / AC-2 | HF-226C | Terminal creates cross-profile child with Project, task-keyed worktree, deterministic branch and usable materialized checkout |
| H226C-FR-004 / AC-3 | HF-226C | Complete mismatch/malformed/conflict matrix plus HLP-226/HLP-226b/scratch/non-affinity controls |
| H226C-FR-005 / AC-4 | AE-226C | Exact portable HLP-226c patch, reconciliation fragment/tests/generated outputs and implementation evidence |
| H226C-FR-005 / AC-4 | H226C-INT | Reviewed fork and Aether integration, normal PR/check/merge, ledgers and byte equivalence |
| H226C-FR-006 / AC-5 | Every unit + H226C-INT | No runtime/profile/config/provider/model/credential/settings/release/deploy/unrelated mutation |
| Deliverables 2/4 and AC-6 | AE-226C + H226C-INT | Reproducible evidence with producer, exact revisions, commands/results/limits, final GitHub and residue state |
| Issue and release closeout | H226C-INT | #226 cites merged evidence; `release_impact=patch`, `release_action=defer`, `release_channel=none` |

## Shared decisions (stamp into every implementation unit)

1. Authority is Objective Contract `oc_644c0b407d13366a@v1` at SHA-256
   `ca1264fb74ff07e1b0a5206e527e3dd6ec7676b8c82f07915f5f38a4308593a5` plus its
   cited `spec.md`, `plan.md` and `quickstart.md`. Skills are procedure only. An
   Implementer must not edit, copy, supersede, stage or commit the canonical contract.
2. Aether work starts from the committed Supervisor decomposition descending from
   `63dd88790e3a0ec78c465d6d6c85e051502e2428`. Each unit verifies that this `tasks.md`
   and the contract artifact/digest are present before mutation. A mismatch returns to
   Supervisor. Do not import unrelated primary-worktree history to make the check pass.
3. Fork product work starts only in a nested isolated worktree of
   `DarkArty07/aether-hermes@415056fee527c5a2302370bd6dba56f84b9a4202`, located by remote
   URL and SHA. Never edit the checkout whose branch is `aether-main`, never copy or
   modify the loaded editable Hermes runtime, and never activate/reload/restart it.
4. Before fork mutation, verify baseline SHA-256 values
   `hermes_cli/kanban_db.py=2c36ef7887320fffe3c993ac5bc0d03091a232ebc9a85746e8bf937e042af58d`
   and
   `tools/kanban_tools.py=1a7939e87fb9300094c0a9f6e98de347ff31628bf59e5f89a52775a92d89ffb1`.
   A mismatch is a stop condition; do not transplant a patch.
5. Recovery authority is conjunctive: current source task exact Project + affinity,
   exact current-board metadata with the same Project and repository binding, and an
   absolute resolved shared path contained as exactly one opaque leaf under
   `<board default_workdir>/.worktrees/`. Do not trust string prefix matching, the path
   alone, a cross-board task lookup or another profile's Project registry.
6. Recovery only supplies Project/repository identity. Existing native same-assignee,
   same-flow, parent-affinity, provenance, dependency and conflicting-explicit-Project
   checks remain authoritative. Same-flow terminal shares the existing `dir`; a
   cross-profile Implementer gets a fresh task-id-keyed worktree and branch.
7. Use component `HLP-226c` and portable file
   `patches/hermes/HLP-226c-cross-board-project-inheritance.patch`. Preserve the existing
   HLP-226b patch and its evidence. The HLP-226 reconciliation record contains
   `["HLP-226", "HLP-226b", "HLP-226c"]` and explicitly validates both patch digests.
8. Use disposable Git repositories, boards, Project registries, profile homes and state
   roots. The prior-board worktree leaf is deliberately absent from the current board.
   Do not access a live board/database or add a Project to a worker registry.
9. Regression-first is mandatory: run the identical new recurrence test against unchanged
   `415056f` and candidate with `HERMES_TEST_FILE_RETRIES=0`. Record first-attempt RED and
   GREEN; no retries, timeout inflation, assertion weakening or skip-as-fix.
10. Writable ownership below is exclusive. Return to Supervisor for a shared-file
    collision, material interface change, baseline-hash mismatch, required cross-board
    lookup/registry redesign, or required live mutation.
11. Implementers do not edit `HERMES_LOCAL_PATCHES.md` or fork `AETHER_FORK.md`; include
    proposed exact ledger text in the handoff. Evidence contains no machine paths,
    secrets, credentials, private model responses or raw runtime state. Attach large logs
    to the native task rather than committing them.
12. Implementers commit intended files with Conventional Commits, report exact commands,
    totals/skips/failures, tree identity, preservation and unit compatibility, then call
    same-card `kanban_request_review(reviewer="supervisor")`. No push, PR, merge, issue
    mutation, release, deployment or activation.
13. Unit compatibility is `patch`. Terminal aggregate is fixed by the accepted contract as
    `release_impact=patch`, `release_action=defer`, `release_channel=none`; contradictory
    evidence returns to Morfeo rather than being normalized.
14. `AGENTS.md` is preserved unless an authorized change actually invalidates an operating
    instruction. H226C-INT rechecks coherence before closure.

## Execution graph

```text
t_0550cdec Supervisor decomposition root
    -> HF-226C maintained-fork behavior/tests (Implementer)
       -> same-card Supervisor review
       -> AE-226C portable patch/reconciliation/evidence (Implementer)
          -> same-card Supervisor review
    -> H226C-INT terminal dual-repository integration/closeout
       (Supervisor, same flow, terminal=true; depends on root and both reviewed units)
```

HF-226C is concentrated because the tool-to-DB authority path and its security matrix
share two fork production files and existing tests. AE-226C cannot run independently:
its byte artifact and claims require an accepted exact HF-226C commit. H226C-INT is
integration and publication, not a substitute for either same-card unit review. There
is no honest implementation parallelism in this small dependency chain; manufacturing
it would duplicate the security decision or make reconciliation consume unreviewed bytes.

## HF-226C — maintained-fork cross-board recovery

- **Source:** H226C-FR-001 through H226C-FR-004, AC-1 through AC-3, Deliverables 1/2,
  `plan.md` decided design and `quickstart.md` sections 1–4; this unit.
- **Outcome:** with zero matching worker Projects, a current-board Project/affinity root
  sharing `R/.worktrees/<prior-board-leaf>` as `dir` creates a same-flow terminal that
  retains exact Project/path/kind/flow/terminal/provenance/gate. The terminal then creates
  a cross-profile Implementer with Project, distinct task-keyed worktree, deterministic
  branch and usable materialized checkout. Every required mismatch fails before invalid
  persistence. Existing direct HLP-226, same-board HLP-226b, scratch and non-affinity
  behavior remains unchanged. Excludes Aether portable artifacts, ledgers, publication
  and runtime activation.
- **Inputs:** fork `415056fee527c5a2302370bd6dba56f84b9a4202` and verified baseline
  hashes from Shared Decision 4; current upstream comparison is the immutable design
  citation `67764dc0863349a384c16425e73ee8571f3a94b7`, not an upgrade target.
- **Boundaries:** writable fork `hermes_cli/kanban_db.py`, `tools/kanban_tools.py`,
  `tests/hermes_cli/test_kanban_db.py`, `tests/hermes_cli/test_kanban_session_affinity.py`,
  `tests/tools/test_kanban_tools.py`, and one new focused HLP-226c test module if that
  avoids mixing fixture concerns. Preserve schemas/migrations, dispatcher workspace
  semantics, Project registry code, unrelated tests, `AETHER_FORK.md`, lockfiles and
  repository Actions.
- **Judgement:** private helper names, exact safe `Path.resolve`/relative containment
  mechanics, and fixture organization. Do not change the decided authority conjunction,
  one-leaf rule, persisted API shape or native affinity checks.
- **Verification:** identical focused recurrence test RED on unchanged base and GREEN on
  candidate; two-profile/current-board terminal-to-Implementer E2E with actual worktree
  materialization; full negative/preservation matrix. Minimum affected command is
  `HERMES_TEST_FILE_RETRIES=0 scripts/run_tests.sh tests/tools/test_kanban_tools.py tests/hermes_cli/test_kanban_db.py tests/hermes_cli/test_kanban_session_affinity.py`
  plus a new module. Also run the fork's documented full test path, `python -m compileall
  -q hermes_cli tools tests`, Ruff check/format on touched files/tests, and
  `git diff --check`; record exact versions, totals, skips, first-attempt failures and
  known unchanged baseline failures.
- **Dependencies:** decomposition root only. Concentrated due the shared tool/DB authority
  interface and test matrix.
- **Completion:** local fork commit(s) attributable only to HLP-226c; exact proposed
  `AETHER_FORK.md` paragraph in handoff; same-card Supervisor review; compatibility
  `patch`; no Aether product/evidence edit and no push.

## AE-226C — portable patch, reconciliation and evidence

- **Source:** H226C-FR-005/006, AC-4 through AC-6, Deliverables 3/4 and
  `quickstart.md` sections 5–6; this unit.
- **Outcome:** the accepted HF-226C fork delta is represented byte-for-byte as the new
  HLP-226c portable patch; existing HLP-226/HLP-226b history remains intact; the HLP-226
  reconciliation fragment and tests bind all three components and both patch digests;
  generated reconciliation outputs agree; HLP-226C evidence records the reviewed fork
  producer, exact base/candidate, RED/GREEN/E2E and reconstruction results without
  claiming final PR/merge/issue state. Excludes ledgers, fork source changes, final
  GitHub closeout and activation.
- **Inputs:** independently reviewed HF-226C commit and handoff. Generate from exact
  `415056f..accepted-commit` file-scoped fork diff; do not recreate source by prose or
  copy from the loaded runtime.
- **Boundaries:** writable
  `patches/hermes/HLP-226c-cross-board-project-inheritance.patch`,
  `specs/001-aether-v1-productization/evidence/hermes-patch-reconciliation/entries/HLP-226.json`,
  `tests/test_hermes_patch_reconciliation.py`, `.github/workflows/policy.yml` only for
  the new portable path allowlist, generated reconciliation aggregate/preflight files,
  and `specs/hlp-226-cross-board-project-inheritance/evidence/HLP-226C.md`. Preserve
  HLP-226b bytes, all other patch records/tests, `HERMES_LOCAL_PATCHES.md`, Objective
  Contract, product source, lockfiles and `AGENTS.md`.
- **Judgement:** test collection shape for multiple HLP-226 artifacts and exact evidence
  table organization. Do not collapse old/new patches, overwrite the old digest, or mark
  final GitHub/activation facts not yet observed.
- **Verification:** SHA-256 and parse checks for both HLP-226b/HLP-226c artifacts;
  `git apply --check` and byte-for-byte reconstruction of HLP-226c against exact
  `415056f`; positive/negative fragment controls; `uv run --frozen python
  scripts/validate_hermes_patch_reconciliation.py`; baseline drift, documentation and
  public-artifact checks; focused reconciliation tests; Ruff check/format, MyPy and
  compileall as applicable; canonical full runner with retries disabled; `uv build` and
  `git diff --check`. Record exact counts and unchanged unrelated failures.
- **Dependencies:** independently reviewed HF-226C. The accepted fork commit/delta is the
  required input.
- **Completion:** local Aether commit(s) for portable artifacts/evidence only; exact
  proposed `HERMES_LOCAL_PATCHES.md` paragraph in handoff; same-card Supervisor review;
  compatibility `patch`; no push/PR/merge/issue mutation.

## H226C-INT — terminal integration and dual-repository closeout

- **Source:** all Deliverables, AC-1 through AC-6, Testing Standard, Authority and Stop
  Conditions; this unit.
- **Outcome:** accepted HF-226C and AE-226C commits integrated in dependency order without
  squash/amend/rebase/force; latest compatible fork `aether-main` and Aether `main`
  rechecked; fork and Aether PRs opened, required checks observed and both merged normally;
  fork `AETHER_FORK.md` and Aether `HERMES_LOCAL_PATCHES.md` updated with exact integrated
  identities; final HLP-226C evidence completed; #226 reconciled only after merged
  evidence; objective-owned remote/local branches and worktrees cleaned only after durable
  merge evidence; unrelated residue preserved. No runtime activation, release or deploy.
- **Inputs:** this committed decomposition and independently reviewed HF-226C/AE-226C
  commits/handoffs. Preserve each implementation commit as inspectable history.
- **Boundaries:** integration-owned conflict/import/wiring/path corrections that introduce
  no new behavior; fork `AETHER_FORK.md`; Aether `HERMES_LOCAL_PATCHES.md`; final sections
  of `specs/hlp-226-cross-board-project-inheritance/evidence/HLP-226C.md`; generated
  reconciliation outputs if exact final identities require regeneration. Any behavior,
  acceptance, shared-interface or security change returns as implementation rework.
- **Verification:** independently re-run AC-1/AC-2 disposable E2E and full AC-3 matrix at
  exact final fork revision; full fork documented tests/static/diff checks; exact portable
  reconstruction and Aether reconciliation/baseline/documentation/public/static/type/full
  runner/build gates; required GitHub checks; PR/issue/branch/worktree/residue/no-activation
  audits; root `AGENTS.md` coherence. Diagnose and correct only objective-caused CI failures
  within bounded integration authority. Record non-applicable fork Actions as NOT RUN, not
  green.
- **Dependencies:** decomposition root plus both independently reviewed implementation
  units. Same Supervisor flow/session affinity with `terminal=true`.
- **Completion:** separate aggregate conclusions exactly
  `release_impact=patch`, `release_action=defer`, `release_channel=none`; local integration
  alone is not success.

## Authority and stop conditions

Follow the finalized Objective Contract. Ordinary isolated worktrees, tests, local commits
and routine push/PR/check/non-bypass merge/issue reconciliation/objective cleanup in the two
provisioned repositories are authorized. Return `needs-contract-revision` for a genuine
contract defect: clean-baseline non-reproduction, missing board Project/repository authority,
required global/cross-board lookup, registry redesign or materially different native affinity
behavior. Return `needs-owner-input` only for genuine owner input. A protected-edge denial is
final. Preserve and report unrelated baseline failures and pre-existing branches/worktrees;
do not strand completed units awaiting a separate review card because unit review is same-card.
