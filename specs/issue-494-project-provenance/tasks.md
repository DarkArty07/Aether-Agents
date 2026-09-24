# #494 Project provenance and bounded review failure — Supervisor task breakdown

**Status:** verified decomposition for Objective Contract `oc_bc27d75a1165818f@v1`.

**Derived by:** Supervisor

**Source contract:** `.aether/objective-contracts/oc_bc27d75a1165818f/v1.md`
(SHA-256 `5c848f98c8adfb9fcd572e64a8d60bbb4825a147286fd4c3133a8d97cc83d8be`)
on Aether base `a27516f04843dca4f0ae77b5aa2acfbd41b80df1`.

**Maintained-fork baseline:** `DarkArty07/aether-hermes` `aether-main`
`aed6591a69f453a1867b73628603e7b53ba40ffc` (tree `2258311f9aa52c58fda9bdbd03183ba50ac85df0`).

**Owning issue:** [#494](https://github.com/DarkArty07/Aether-Agents/issues/494).

This file is the Supervisor-owned execution breakdown. It derives work from the
finalized Objective Contract and does not replace or widen it. Card bodies are the
executable deliveries and native board state is the durable execution record.

## Receipt

| Check | Observed |
| --- | --- |
| Portable Project | `.aether/project.toml` `project_id` is `12027989-a08f-41cd-a82c-54ff1bfb6b03`, identical to the task envelope and contract front matter |
| Contract bytes | Artifact present at the root commit and in the worktree; `sha256sum` equals the envelope exactly |
| Base commit | Clean root HEAD equals `a27516f04843dca4f0ae77b5aa2acfbd41b80df1`; contract commit is that single commit over `4c1af201c18ced73235d7b49f22a32123c46fb22` |
| Board binding | Board `oc-12027989a08f41cda82c54ff1bfb6b03-bc27d75a1165818f-v1` carries `aether_project_id` and `aether_contract_id`/version matching the contract, Hermes Project `p_227bd972`, `default_workdir` at the Aether root and `worktree_base_ref` equal to the base commit; it contains only this root card |
| Maintained fork | Remote `origin` is `https://github.com/DarkArty07/aether-hermes.git`; the contract revision exists as a commit, the checkout is clean, and no fork pull request is open. The local `aether-main` tip and the remote tip are two commits ahead (a change and its exact revert) whose tree is byte-identical to `2258311f9a…`; no unmerged branch touches the affected resolver |
| Baseline file digests | At `aed6591a69…`: `hermes_cli/kanban_db.py` `299d3580f72d54a767bb314b65d097326086871aed633e9b6ebdc33f26bbf001`, `tools/kanban_tools.py` `9e288c1e00cb00771cd4cc718103fda78fc5fc11fa08b97dcd70dfa221d629cc` |
| Fork execution environment | Supervisor prepared one isolated clean worktree of that repository at the exact accepted revision (branch `fix/494-project-provenance-and-bounded-failure`, HEAD and tree as above, clean including untracked files) and proved the documented runner executes there: `HERMES_TEST_FILE_RETRIES=0 scripts/run_tests.sh tests/hermes_cli/test_kanban_board_project.py tests/hermes_cli/test_kanban_project_link.py` → 2 files, 7 tests passed, exit 0, on Python 3.11.15 with pytest 9.1.1 |
| Aether gate baseline | On the untouched root: `scripts/check_documentation.py` passed; `scripts/check_public_artifacts.py --root .` passed; `scripts/validate_hermes_patch_reconciliation.py --check --fork-checkout <clean fork checkout at the accepted revision> --json` → `status: current`, `records: 31`, `present: 29`, `absent: 0`, `refusing: []`, `unverified: [HLP-246, HLP-247]`; `tests/test_hermes_patch_reconciliation.py` → 23 passed; `tests/test_public_artifacts.py` → 9 passed |
| Next free audit identifier | No `HLP-428` heading, fragment, digest row or patch exists in the Aether repository or the fork; the ledger's detailed sections end at `HLP-427` and the reconciliation roster has 31 entries |
| Preserved live state | Installed Aether reports `1.0.0rc8`; the loaded Hermes source remains the pre-existing editable runtime; the concurrently executing objective's board `oc-12027989a08f41cda82c54ff1bfb6b03-79b55027e7c3688d-v1` holds three `running` Supervisor cards, and other boards hold unrelated `running`/`review` cards. None of this is touched by decomposition or by the declared unit boundaries |
| Profiles and capacity | Existing `implementer` and `supervisor` profiles are sufficient; the board allows three in-progress Implementer cards and one Supervisor card. No new role, profile or capacity change is requested |
| Project Canonical Skills | `.aether/skills/aether-observe/SKILL.md` is installed and is a Morfeo observation surface; it supplies no acceptance authority here. Applicable Aether Canonical procedures govern execution |
| Design sufficiency | The contract settles the failing route, the preferred conjunctive recovery, the mandatory early refusal, the preserved generic scratch behavior, the required fail-closed review identity, the ban on reading another profile's registry, the disposable-state testing standard and the source-only boundary. No material product or interface decision is missing; the failure-route rollback remains an explicitly unproven hypothesis that must be reproduced before any correction |
| Root guidance | `AGENTS.md` remains coherent with the maintained-fork boundary, the `#492` preservation obligation and the no-activation constraint. Decomposition requires no guidance edit |
| Decomposition checks | `git diff --check` passed; documentation, public-artifact, contract-quality and public-artifact test files were executed on the untouched root and passed before this file was added |

## Cross-artifact executability

| Concern | Settled conclusion | Execution consequence |
| --- | --- | --- |
| Dual repository | The maintained Hermes fork owns the behavior and its focused tests. Aether owns the portable patch, the ledger/reconciliation records, the evidence and its own normal pull request | Fork work happens only in the isolated fork worktree Supervisor prepared at the exact accepted revision. The checkout whose branch is `aether-main`, the loaded editable runtime and the installed release are never modified or activated |
| Fork hotspot | Project recovery for creation (`create_task`, `_project_from_board_binding`) and the bounded failure/containment route (`_record_task_failure`, `block_task`, `_route_affinity_terminal`, `_default_flow_block_signal`) live in the same production file, and the second is an unproven hypothesis whose correction size is unknown | **One** concentrated fork unit (`HF-494`) owns both behaviors. Two units editing `hermes_cli/kanban_db.py` on parallel branches is a declared collision under current policy, and serializing them would buy no throughput while inviting a speculative second repair |
| Portable bytes | The Aether patch artifact, its digest and the reconciliation truth depend on the accepted exact fork delta | `AE-494` is serialized after same-card review of `HF-494`. The accepted commit is its required input, not an ordering preference |
| Patch identity | The contract names `HLP-428` as the proposed next free identifier, and it is verified free | Component id `HLP-428`; portable file `patches/hermes/HLP-428-project-provenance-and-bounded-failure.patch`; the `HERMES_LOCAL_PATCHES.md` detailed section uses the validator's `## HLP-428 — …` heading form; `tests/test_hermes_patch_reconciliation.py` gains the id in its active-id roster and digest table |
| Ledger hotspot | `HERMES_LOCAL_PATCHES.md`, `patches/hermes/**`, the reconciliation fragments, the generated aggregate/preflight and the policy base manifest share one digest/registry surface; the ledger digest is itself an input to the aggregate | `AE-494` owns that surface for this objective inside a single card. Fork units never edit it; they hand over the exact commit and the measured facts. This is a bounded serialization reason, not a new mechanism |
| Aggregate pin | The committed aggregate is pinned at the accepted revision `aed6591a69…`. A fragment that declares a path absent at its pin is recorded absent and refuses candidate preparation, and the new fork regression module does not exist at that pin | `AE-494` declares as `components` only paths present at the pin and describes the new module in the entry's artifact/retirement evidence and in the ledger section. `INT-494` may re-pin the aggregate to the merged fork revision after the fork merge and only then add the module; the validator is never weakened and no final fact is claimed before observation |
| Policy manifest | `patches/hermes/HLP-428-…patch` is a new tracked non-`specs/` path, and the base-manifest roster is an exact expected list; this review file lives under `specs/`, which that check excludes | `AE-494` adds exactly one allow-list line, plus one `.gitattributes` whitespace line for the new patch. Two concurrent branches touch the same workflow file; the conflict is textual and must be reconciled by an ordinary non-rewriting merge |
| Evidence hotspot | `specs/issue-494-project-provenance/evidence/HLP-428.md` is the single objective report | `AE-494` owns it and records producer facts; `INT-494` appends only observed final GitHub, check, merge, cleanup and release-readiness facts after review |
| Testing | The fork's own guidance requires `scripts/run_tests.sh`; the Aether side requires the documented bootstrap, focused tests and the static/public gates | `HF-494` owns RED-first disposable reproduction and the fork battery. `INT-494` independently repeats the decisive AC1/AC2 route and the AC6 preservation witnesses at the exact final revisions |
| Live preservation | The installed runtime pin, the `#492` workers and every unrelated live board must survive unchanged | Every unit works from disposable state only; read-only fingerprints of the preserved boards are taken before any writer runs, and any accidental live mutation is preserved as evidence rather than deleted |
| Publication and activation | Implementation units commit locally and stop at same-card review | `INT-494` alone pushes, opens and merges the fork and Aether pull requests normally, regenerates the aggregate where the accepted facts require it, reconciles the issue and cleans objective residue. No activation, restart, release, tag, publication or deployment |
| Exclusions | `#460` rootless decision topology and `#475` stale review lease remain separate; the real Kanban database, the incident card and its failed history are untouched | Report incidental findings without absorbing or mutating them; never weaken review identity, affinity, Project, protected-edge or secret rules |

## Requirement coverage

| Contract source | Unit | Observable coverage |
| --- | --- | --- |
| AC1 | `HF-494` | The exact supported route reproduces a null-Project scratch child on the unchanged accepted revision in entirely disposable state, with synthetic identifiers only and unchanged live-board witnesses |
| AC2 | `HF-494`, `INT-494` | At the fixed revision the same route persists the canonical Project on a fresh child worktree with the correct parent edge, or refuses before any task/run/event is persisted; a supported same-card review claim follows, and `INT-494` repeats the route independently |
| AC3 | `HF-494` | The complete mismatch matrix refuses without fallback, while generic non-Aether scratch creation, same-profile linked projects and the existing affinity recovery keep passing |
| AC4 | `HF-494` | The bounded failure/containment path is reproduced separately in disposable state, or its non-reproduction is reported as the measured limit instead of a speculative repair; no notification reaches an unverified identity and no review approval is claimed |
| AC5 | `HF-494`, `AE-494`, `INT-494` | Fork source, tests, portable patch, ledger/reconciliation evidence and Aether integration pass the stated focused and full applicable gates with independent review and merged-tree readback; no guard or test is weakened |
| AC6 | `INT-494` | The installed runtime pin is unchanged, `#492` workers and unrelated boards are preserved, and `#494` stays open with explicit successor obligations and no stable-release claim |
| Deliverables 1–3 | `HF-494`, `AE-494`, `INT-494` | Fork source with exact merge identity; Aether reconciliation evidence with reproducible commands; concise release-readiness handoff naming remaining adoption, rollback candidates, preservation witnesses and the specific acceptance not yet qualified |

## Shared decisions (stamped into every implementation unit)

1. Authority is Objective Contract `oc_bc27d75a1165818f@v1` at SHA-256
   `5c848f98c8adfb9fcd572e64a8d60bbb4825a147286fd4c3133a8d97cc83d8be` plus this
   breakdown. Skills are procedure only. No unit may edit, copy, stage, commit or
   supersede the canonical contract, and no unit may widen the objective.
2. Aether work starts from this committed decomposition. Each unit verifies, before
   mutation, that the contract artifact and digest, the base commit and this file at its
   committed revision are present. A mismatch returns to Supervisor; unrelated history is
   never imported to make the check pass.
3. Fork product work starts only in the isolated worktree of
   `https://github.com/DarkArty07/aether-hermes.git` at exact revision
   `aed6591a69f453a1867b73628603e7b53ba40ffc` prepared by Supervisor in that repository
   under `.worktrees/fix-494-prov` on branch `fix/494-project-provenance-and-bounded-failure`.
   Locate the repository by its remote URL. Never edit the checkout whose branch is
   `aether-main`, the loaded editable runtime, or an unrelated worker's worktree.
4. Before fork mutation, verify the two baseline file digests from the receipt. A mismatch
   is a stop condition; do not transplant a patch computed against different bytes.
5. The correction is the contract's conjunctive recovery, not a new design: recover only
   when the source task is the explicit direct parent on the current board and carries the
   requested Project, the board metadata carries that same Project and an absolute
   `default_workdir` for its repository, and the directory resolves to exactly one opaque
   leaf under that repository's `.worktrees/` — with traversal, symlink and cross-board
   mismatches refused. Never read or copy another profile's registry, never trust the leaf
   or a display name as authority, and never hand a resolved child the parent's literal
   directory.
6. When a Project was explicitly supplied in a recognized Aether board and safe recovery
   fails, refuse actionably **before** any task, run or event row is inserted, and never
   persist a null Project while reporting success. Preserve ordinary non-Aether scratch
   creation, same-profile linked projects, explicit cross-Project mismatch rejection and
   the existing affinity recovery exactly as they behave today.
7. The failure-route rollback is a hypothesis. Reproduce it in disposable state first. If
   it cannot be reproduced, record that limit as the result of AC4 and do not invent or
   apply a corrective patch. If it does reproduce, contain the defect without copying a
   subscription or emitting an origin signal to an unverified identity, without changing
   historical Project or evidence rows, without fabricating a reviewer claim, and without
   weakening the review session context.
8. Use disposable Git repositories, boards, Project registries, profile homes and state
   roots, and make every write-capable probe refuse a context that resolves outside its
   private roots before the first writer runs. Do not write to a live board or database.
   Take read-only byte and row fingerprints of the preserved live boards before and after
   the work. If an accidental live mutation is ever discovered, preserve it as evidence and
   escalate; direct deletion of tasks, comments, events or runs is never cleanup.
9. Sensitive material stays out of everything committed: no machine paths, operator
   layout, secrets, credentials, private model output or raw runtime state in the
   breakdown, the ledger, the reconciliation fragments, the patch or the evidence. The
   reconciliation validator fails closed on non-portable content, and the public-artifact
   scanner rejects operator paths.
10. Writable ownership below is exclusive. Concurrent edits to the same file across units
    are forbidden. Return to Supervisor for a shared-file collision, a material interface
    change, a baseline-digest mismatch, a required cross-board lookup or registry
    redesign, or any live mutation.
11. Implementers commit only intended paths with Conventional Commits, report exact
    commands, revisions, totals, skips and first-attempt failures, and then request
    same-card review with `kanban_request_review(reviewer="supervisor")`. No push, pull
    request, merge, issue mutation, release, deployment or activation from a unit.
12. Unit compatibility evidence is `patch`. The terminal aggregate conclusion is
    `release_impact=patch`, `release_action=defer`, `release_channel=none`, consistent with
    the contract's source-only boundary; contradictory evidence returns to Morfeo rather
    than being normalized.
13. `AGENTS.md` and the contract-owning artifacts are preserved unless an authorized change
    actually invalidates an operating instruction. `INT-494` rechecks coherence before
    closure.
14. Source merge is not issue closure. `#494` stays open after this phase with its live
    activation, effective-runtime and real review canary obligations named as successors.

## Execution graph

```text
t_2f97ef7a Supervisor decomposition root
    -> HF-494 fork behavior, refusal and bounded-failure evidence (Implementer)
       -> same-card Supervisor review
       -> AE-494 portable patch, ledger, reconciliation and evidence (Implementer)
          -> same-card Supervisor review
    -> INT-494 terminal integration and dual-repository closeout
       (Supervisor, same flow, terminal=true; depends on root and both reviewed units)
```

`HF-494` is concentrated because the creation/recovery authority path and the
failure-containment route share one production file and one review boundary; splitting
them would put two units on `hermes_cli/kanban_db.py` and invite a speculative repair of
an unproven hypothesis. `AE-494` cannot run independently: its byte artifact and its
reconciliation claims are derived from the accepted fork commit. `INT-494` is integration
and publication, not a substitute for either same-card unit review. There is no honest
implementation parallelism in this dependency chain, and none is manufactured.

## HF-494 — fork Project provenance, early refusal and bounded failure evidence

- **Source:** AC1 through AC4, Deliverable 1, contract Objective, Decisions, In Scope,
  Testing Standard and Stop Conditions; this breakdown's shared decisions 2–12.
- **Outcome:** on the unchanged accepted revision, the supported route is reproduced RED
  in entirely disposable state: a Project-bound `dir` parent without affinity and an
  explicit same-Project child with a direct parent edge and no declared workspace persists
  a null-Project scratch child. At the fixed revision that exact route persists the same
  canonical Project on a fresh child worktree with a correct parent edge, and same-card
  review can claim with review source status and no bypass; every insufficient-evidence
  case refuses actionably before any task, run or event row exists and never reports
  success with a null Project. The mismatch matrix refuses without fallback while generic
  scratch, same-profile linked projects and existing affinity recovery keep passing. The
  bounded failure/containment path is reproduced separately in disposable state, or its
  non-reproduction is reported as the measured limit. Excludes Aether portable artifacts,
  ledgers, publication and activation.
- **Inputs:** isolated clean fork worktree at
  `aed6591a69f453a1867b73628603e7b53ba40ffc` (tree
  `2258311f9aa52c58fda9bdbd03183ba50ac85df0`) with a working documented test environment;
  the two baseline file digests from the receipt; the observed incident shape recorded in
  issue `#494` as the reproduction reference, not as authority.
- **Boundaries:** writable fork `hermes_cli/kanban_db.py`, `tools/kanban_tools.py`,
  `tests/hermes_cli/test_kanban_board_project.py`,
  `tests/hermes_cli/test_kanban_project_link.py`,
  `tests/hermes_cli/test_kanban_session_affinity.py`, `tests/tools/test_kanban_tools.py`,
  existing review/block test modules under `tests/hermes_cli/`, and one new focused module
  for this defect if that avoids mixing unrelated fixture concerns. Preserve schemas and
  migrations, dispatcher workspace semantics, the Project registry implementation,
  unrelated tests, `AETHER_FORK.md`, lockfiles, workflows and every path outside the
  fork.
- **Judgement:** private helper names, exact safe path-resolution and containment mechanics,
  fixture organization, and the disposable harness layout. Do not change the decided
  conjunction, the one-leaf rule, the persisted API shape, the native affinity checks or
  the review identity guard.
- **Verification:** the identical focused recurrence test must fail RED on the unchanged
  revision and pass GREEN on the candidate with `HERMES_TEST_FILE_RETRIES=0` and no retry,
  timeout inflation, assertion weakening or skip-as-fix. Exercise the real
  two-registry/current-board route end to end with actual worktree materialization, the
  full negative and preservation matrix, and the separate disposable failure/containment
  reproduction. Minimum affected run: `HERMES_TEST_FILE_RETRIES=0 scripts/run_tests.sh`
  over the touched Kanban tool and `hermes_cli` modules plus any new module. Also run the
  fork's documented full suite, `python -m compileall -q` on touched trees, Ruff check and
  format status on touched scope, and `git diff --check`, recording exact commands,
  versions, totals, skips, first-attempt failures and unchanged baseline failures. Fork
  Actions are currently unavailable: report them NOT RUN, never green.
- **Dependencies:** decomposition root only. Concentrated by the shared production file and
  the single review boundary described above.
- **Completion:** local fork commit(s) attributable only to this objective; handoff with the
  exact commit and tree, RED/GREEN/matrix/failure-route evidence, preservation statement,
  compatibility `patch`, remaining risks and the exact proposed `AETHER_FORK.md`
  paragraph; same-card Supervisor review; no Aether edit, no push, no pull request and no
  activation.

## AE-494 — portable HLP-428 artifact, ledger reconciliation and evidence

- **Source:** AC5 and AC6 (Aether side), Deliverables 2 and 3 (fact supply), In Scope
  "Aether-side source reconciliation", shared decisions 9–12.
- **Outcome:** the accepted `HF-494` fork delta is represented byte for byte as the new
  `HLP-428` portable patch; `HERMES_LOCAL_PATCHES.md` gains its detailed section in the
  validator's heading form plus its summary row; the reconciliation fragment binds the
  required behavior, the upstream inspection identity, the retirement gate and the patch
  digest within the portable-content rules; the aggregate and preflight regenerate
  consistently at the accepted pin; the objective evidence report records producer facts,
  exact revisions and reproducible commands without claiming merge or issue state. Excludes
  fork source changes, pull requests, merges and activation.
- **Inputs:** independently reviewed `HF-494` commit and handoff in the fork worktree;
  verified baseline digests; the ledger, fragment, schema, validator and test surfaces as
  they exist at this decomposition.
- **Boundaries:** writable `patches/hermes/HLP-428-project-provenance-and-bounded-failure.patch`,
  the `HLP-428` fragment under
  `specs/001-aether-v1-productization/evidence/hermes-patch-reconciliation/entries/`,
  the generated aggregate and preflight under
  `specs/001-aether-v1-productization/evidence/`, `HERMES_LOCAL_PATCHES.md`,
  `.gitattributes` (one whitespace line), `.github/workflows/policy.yml` (one allow-list
  line for the new patch path), `tests/test_hermes_patch_reconciliation.py` (the new id in
  the active-id roster and digest table, plus focused controls if the existing rules need
  a positive/negative case), and
  `specs/issue-494-project-provenance/evidence/HLP-428.md`. Preserve every other patch and
  fragment, the validator and schema, all other ledger records, the Objective Contract,
  product source, lockfiles and `AGENTS.md`.
- **Judgement:** exact evidence table organization, the wording of the ledger section, and
  how the new regression module is described in the entry. Do not collapse or rename the
  existing records, do not declare a `components` path that does not exist at the pin, do
  not record merge or activation facts that have not been observed, and do not weaken the
  validator or any test to obtain green output.
- **Verification:** digest and parse checks for the new patch; `git apply --check` and
  byte-for-byte reconstruction against a freshly materialized tree at the exact base
  revision; positive and fail-closed controls for the new record; the reconciliation
  generator and `--check` with a clean checkout at the pinned revision; the focused
  reconciliation tests; documentation, public-artifact and baseline-drift checks;
  `tests/test_public_artifacts.py` and `tests/test_contract_quality_documents.py`; Ruff
  check and format, MyPy and compileall as applicable; and the documented Aether bootstrap
  runner with retries disabled. Record exact counts and attribute any unchanged unrelated
  failure rather than fixing it here. The known immutable-contract operator-path finding
  recorded for this repository is reported as pre-existing, not normalized.
- **Dependencies:** independently reviewed `HF-494`. The accepted fork commit and delta are
  the required input.
- **Completion:** local Aether commit(s) for portable artifacts and evidence only; handoff
  with the exact proposed `HERMES_LOCAL_PATCHES.md` content, digest, reconstruction result
  and any residual derived staleness; same-card Supervisor review; compatibility `patch`;
  no push, pull request, merge or issue mutation.

## INT-494 — terminal integration and dual-repository closeout

- **Source:** all Deliverables, AC1 through AC6, Authority, Testing Standard and Stop
  Conditions; shared decisions 1–14.
- **Outcome:** the accepted `HF-494` and `AE-494` commits are integrated in dependency
  order without squash, amend, rebase or force; the then-current fork and Aether branch
  tips are rechecked; the fork pull request is opened, its required checks observed where
  available and merged normally; the Aether pull request carries the portable evidence and
  its required checks and merges normally; the ledger, fragment and generated
  reconciliation files reflect the exact integrated identities, with the aggregate re-pinned
  to the merged fork revision once the declared paths exist there; the objective evidence
  report is completed with observed merge, check, cleanup and preservation facts; `#494`
  is reconciled only against merged evidence and explicitly left open for its successor
  obligations; objective-owned branches and worktrees are cleaned only after durable merge
  evidence while unrelated residue is preserved. No activation, restart, release, tag,
  publication or deployment.
- **Inputs:** this committed decomposition and the independently reviewed `HF-494` and
  `AE-494` commits and handoffs. Each implementation commit is preserved as inspectable
  history.
- **Boundaries:** integration-owned conflict, import, wiring, path and manifest
  corrections that introduce no new behavior; the fork `AETHER_FORK.md`; the Aether ledger,
  fragment, generated aggregate/preflight and objective evidence report; the branch
  carrying this decomposition. Any behavior, acceptance, shared-interface or security
  change returns as implementation rework rather than being absorbed here.
- **Verification:** independently re-run the decisive AC1/AC2 disposable route and the AC3
  matrix at the exact final fork revision; repeat the AC4 evidence or its recorded limit;
  run the fork's documented focused and full batteries, static and diff checks; run the
  Aether bootstrap runner, focused reconciliation tests, reconciliation `--check`,
  documentation, public-artifact, baseline-drift, contract-quality and static/type gates;
  observe the actual required checks on both repositories; audit the pull requests, the
  issue state, branch and worktree residue, the unchanged installed runtime pin and the
  preserved `#492` and unrelated live work; and recheck root `AGENTS.md` coherence.
  Diagnose and correct only objective-caused failures within bounded integration authority;
  record unavailable checks as NOT RUN rather than green.
- **Dependencies:** decomposition root plus both independently reviewed implementation
  units. Same Supervisor flow and session affinity with `terminal=true`.
- **Completion:** separate aggregate conclusions stated exactly as `release_impact=patch`,
  `release_action=defer`, `release_channel=none`; the release-readiness handoff naming
  remaining live adoption, rollback candidates, board and session preservation witnesses
  and the specific `#494` acceptance not yet qualified; local integration alone is not
  success.

## Authority and stop conditions

Follow the finalized Objective Contract. Ordinary isolated worktrees, disposable state,
tests, local commits and routine push, pull request, non-bypass merge, issue reconciliation
and objective cleanup in the two provisioned repositories are authorized, using only
existing access. Return a contract defect to Morfeo when the accepted revision cannot
reproduce the reported route, when the failure-route hypothesis cannot be reproduced and
no bounded in-scope repair is supported, when a required cross-board lookup or registry
redesign would be needed, when the manifest or ledger collides with concurrent objectives
and cannot be reconciled by an ordinary non-rewriting merge, or when a required gate is red
without a bounded in-scope fix. A protected-edge denial for real credential, external or
destructive effects is final; an unexpected denial of ordinary local work follows Aether's
bounded recovery procedure instead of a bypass. Preserve the candidate and its evidence,
never weaken a guard or a test to obtain green output, never treat a source-only merge as
issue closure, and stop before any runtime activation or restart, package or public release,
tag push or live board repair.
