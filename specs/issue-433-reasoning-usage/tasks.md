# #433 auxiliary Responses reasoning usage — Supervisor task breakdown

**Status:** verified decomposition for Objective Contract `oc_3fdf70ccc94e14b1@v1`.

**Derived by:** Supervisor

**Source contract:** `.aether/objective-contracts/oc_3fdf70ccc94e14b1/v1.md`
(SHA-256 `6477561e1a62418af161f8a60f312540f151f8a789230d6cf5f1ec8055c7cb4a`)
on Aether base `c2a428cd3f9e89e4ac7cf0e00aa3309b653e2ab1`.

**Maintained-fork baseline:** `DarkArty07/aether-hermes` `aether-main`
`58f8c37a49b341f25b8fdd6310542fe932031b8d` (tree `a93162c1a867202b03c12fa372c71029152fdcf7`).

**Owning issue:** [#433](https://github.com/DarkArty07/Aether-Agents/issues/433) — stays **OPEN**
after this source phase.

**Technical design:** `specs/issue-433-reasoning-usage/plan.md` (Morfeo, Aether
`ad8387e47eab24e896846f8c9f29d5dd1677ddfb`). This file is the Supervisor-owned execution
breakdown; it derives work from the finalized contract and does not replace or widen it.
Card bodies are the executable deliveries and native board state is the durable record.

## Receipt

| Check | Observed |
| --- | --- |
| Portable Project | `.aether/project.toml` `project_id` `12027989-a08f-41cd-a82c-54ff1bfb6b03` equals the task envelope and the contract front matter; board `oc-12027989a08f41cda82c54ff1bfb6b03-3fdf70ccc94e14b1-v1` carries `aether_project_id`/`aether_contract_id`/version matching the contract, `default_workdir` at the Aether root and `worktree_base_ref` `c2a428cd3f9e89e4ac7cf0e00aa3309b653e2ab1` |
| Contract bytes | Present at the root commit and in this worktree; `sha256sum` equals the envelope exactly |
| Base commit | Clean root HEAD equals `c2a428cd3f9e89e4ac7cf0e00aa3309b653e2ab1`; the contract commit is that single commit over `ad8387e4` and is not yet an ancestor of `origin/main` |
| Maintained-fork pin | `origin/aether-main` is `58f8c37a49b341f25b8fdd6310542fe932031b8d` (tree `a93162c1a867202b03c12fa372c71029152fdcf7`), equal to the contract's inspected revision and the committed reconciliation pin; **no fork pull request is open** and no branch named for `#433` exists locally or remotely |
| Loss point re-verified | `agent/auxiliary_client.py` `_CodexCompletionsAdapter.create` reconstructs only `prompt_tokens`/`completion_tokens`/`total_tokens`; the adapter source contains neither `output_tokens_details` nor `reasoning_tokens`. `agent/usage_pricing.py` `normalize_usage` already returns `271` for the same usage in **both** object and mapping form on this pin |
| Baseline file digests at the pin | `agent/auxiliary_client.py` `2c5dfee035dd47a8bb8f2e652983f53f3ebc3b90c06adc87176f4cbf3adc0a30`; `agent/usage_pricing.py` `51ec125f03e5a2f686b8f669755712ef8f9956961fc49fdc33a0abc37cbfcd9e`; `agent/aux_accounting.py` `1ce741a528bbb9182c03fe486181f5c8d6f8d103ca859b864a4a274991cd2421`; `agent/codex_runtime.py` `37bd92f2c3573d70558602c5438b8198b4854ac86cefb9d5757cedc5a841ba0b`; `tests/agent/test_auxiliary_client_responses_terminal_420.py` `1c8a21d09950a7bef2fbbac3b03073970f23e3eab32fd15e6e2f12cc4a1434e6`; `tests/hermes_state/test_aux_usage_accounting.py` `574051fe09c67b358aa9e3b9d1b1e4a5486036e2b14f87c71e1bc9c72b58b401` |
| Fork execution environment | Supervisor materialized an isolated fork worktree at the exact pin on branch `fix/433-reasoning-usage`, clean including untracked files, with a working documented runner: `HERMES_TEST_FILE_RETRIES=0 scripts/run_tests.sh tests/agent/test_auxiliary_client_responses_terminal_420.py tests/hermes_state/test_aux_usage_accounting.py` → 2 files, 34 passed, 0 failed, exit 0 (Python 3.11.15, pytest 9.1.1, 48 workers) |
| Next free audit identifier | No `HLP-433` heading, summary row, fragment, digest row or patch exists in Aether or the fork; the ledger's detailed sections end at `HLP-428` and the reconciliation roster holds 32 entries |
| Aether baseline | On the untouched root: `scripts/check_documentation.py` passed; `scripts/run_tests.py -- tests/test_hermes_patch_reconciliation.py -q` → 23 passed; committed aggregate is `status: current` at pin `58f8c37a…` with 32 records |
| Objective-caused manifest defect | The contract commit `c2a428cd` tracked `.aether/objective-contracts/oc_3fdf70ccc94e14b1/v1.md` but did **not** add it to the `policy.yml` expected-manifest list, so the `Validate canonical base manifest` step fails on this branch. Simulated on the untouched root: expected 456 entries vs 457 tracked non-`specs/` paths, sole difference `.aether/objective-contracts/oc_3fdf70ccc94e14b1/v1.md`. Recorded as a bounded integration repair for `INT-433` (see shared decision 9), not a unit deliverable |
| Preserved live state | The installed Aether runtime pin, the concurrently executing `#494`/RC6 lanes and every unrelated live board are untouched by this decomposition. Read-only board inventory shows 92 board databases with unrelated `running`/`blocked`/`todo` cards; `#492` state is not read, moved or mutated |
| Profiles and capacity | Existing `implementer` and `supervisor` profiles are sufficient; no new role, profile or capacity change is requested |
| Design sufficiency | The contract fixes the failing boundary, the preferred carried shape, the subcount/no-double-count rule, the absence semantics, the source-only boundary and the HLP procedure. No material product or interface decision is missing |

## Cross-artifact executability

| Concern | Settled conclusion | Execution consequence |
| --- | --- | --- |
| Dual repository | The maintained fork owns the behavior and its focused tests. Aether owns the portable patch, ledger/reconciliation records, the public-artifact surfaces and its own PR | Fork work happens only in the isolated worktree at the exact pin. The checkout whose branch is `aether-main`, the loaded editable runtime and the installed release are never edited, re-pointed or activated |
| Fork hotspot | The whole fix is one boundary — the adapter's usage reconstruction (`agent/auxiliary_client.py`, inspected at `:2077-2086`) — plus its tests | **One** fork unit (`HF-433`). Two units editing `agent/auxiliary_client.py` on parallel branches is a declared collision under current policy, and the consumers (`agent/usage_pricing.py`, `agent/aux_accounting.py`, `agent/codex_runtime.py`) already behave correctly, so a second production unit would be speculative |
| Portable bytes | The Aether patch, its digest and the reconciliation truth depend on the accepted exact fork delta | `AE-433` is serialized after same-card review of `HF-433`; the accepted commit is its required input, not an ordering preference |
| Fork ledger | The fork's `AETHER_FORK.md` is the fork-side record | `HF-433` preserves it and supplies the exact proposed paragraph; `INT-433` applies it on the branch it merges. No two units edit it |
| Patch identity | `HLP-433` is verified free | Component id `HLP-433`; patch `patches/hermes/HLP-433-responses-reasoning-usage.patch`; ledger heading `## HLP-433 — …` (em dash); summary-table row; fragment `HLP-433.json`; roster and digest table in `tests/test_hermes_patch_reconciliation.py` |
| Aggregate pin | The committed aggregate is pinned at `58f8c37a…`, where the new fork test module does **not** exist. A declared path absent at the pin is recorded `absent` and refuses candidate preparation | `AE-433` generates at `58f8c37a…` and declares as `components` only paths present there. `INT-433` re-pins to the merged fork revision and may then declare the new module. The validator is never weakened and no unobserved fact is claimed |
| Ledger/registry hotspot | `HERMES_LOCAL_PATCHES.md`, `patches/hermes/**`, fragments, generated aggregate/preflight, `.gitattributes` and the `policy.yml` allow-list share one digest/registry surface; the ledger digest is itself an aggregate input | `AE-433` owns that surface inside one card. Fork units never edit it. `INT-433` alone re-generates after the fork merge |
| Aether integration branch | Implementation units must land on the branch that becomes the Aether PR | `AE-433` and `INT-433` are `dir` cards on the decomposition workspace/branch; `HF-433` commits only in the fork. Nothing is pushed by an implementation unit |
| Evidence hotspot | `specs/issue-433-reasoning-usage/evidence/HLP-433.md` is the single objective report | `AE-433` writes producer facts; `INT-433` appends only observed merge, check, cleanup and release-readiness facts |
| Publication and activation | Unit work stops at same-card review | `INT-433` alone pushes, opens and merges both normal PRs, re-pins the aggregate, comments on the issue and cleans objective residue. No tag, release, package publication, deployment, `aether update` or runtime activation |
| Exclusions | `#494`/`#492`, their boards, locks, worktrees and canaries remain out of scope; `#433` is not closed by a source-only merge | Incidental findings are reported without being absorbed or mutated |

## Requirement coverage

| Contract source | Unit | Observable coverage |
| --- | --- | --- |
| AC1 | `HF-433`, `INT-433` | Object-form, mapping-form and terminal-SSE synthetic Responses usage with nonzero nested reasoning survive the adapter and `_validate_llm_response` and produce exactly one correlated accounting operation and one disposable `session_model_usage` row carrying the exact reported reasoning, with unchanged input/output/total |
| AC2 | `HF-433`, `INT-433` | Explicit zero, absent detail and absent usage keep the existing zero/unknown behaviour; malformed detail neither breaks a valid response nor invents a value; Chat-provider fallback and error accounting remain green |
| AC3 | `HF-433`, `AE-433` | Pre-fix RED at the unchanged pin, GREEN at the reviewed candidate, neighbor regressions and byte-verified source/patch identity; the committed patch reconstructs the reviewed fork tree from its recorded base |
| AC4 | `AE-433`, `INT-433` | Ledger, fragment, aggregate/preflight, manifest and evidence reference the exact merged fork commit and applied test paths; relevant checks pass; `#433` stays open; `#494`/`#492` and live runtime state are unchanged; omitted steps and release conclusions are explicit |
| Deliverables 1–5 | all units | Fork source and merge identity; portable HLP-433 artifact with rollback and retirement gate; Aether ledger/fragment/aggregate/evidence; green merged Aether PR with readback; board handoff with separated release conclusions. No active-runtime artifact |

## Shared decisions (binding in every unit)

1. Authority is Objective Contract `oc_3fdf70ccc94e14b1@v1` at SHA-256
   `6477561e1a62418af161f8a60f312540f151f8a789230d6cf5f1ec8055c7cb4a` plus this breakdown.
   Skills are procedure only. No unit may edit, copy, stage, commit or supersede the canonical
   contract, and no unit may widen the objective.
2. Aether work starts from this committed decomposition. Each unit verifies, before mutation,
   the contract digest, the base commit and this file at its committed revision. A mismatch
   returns to Supervisor; unrelated history is never imported to make a check pass.
3. Fork product work starts only in the isolated worktree of
   `https://github.com/DarkArty07/aether-hermes.git` at exact revision
   `58f8c37a49b341f25b8fdd6310542fe932031b8d`, branch `fix/433-reasoning-usage`, prepared by
   Supervisor and reserved for `HF-433` as the single writer. Locate the repository by its
   remote URL. Never edit the checkout whose branch is `aether-main`, the loaded editable
   runtime or another worker's worktree, and never create a second worktree on that branch.
4. **Decided shape.** The adapter must carry the completed response's nested reasoning detail
   onto the chat-compatible `usage` object as `output_tokens_details`, the shape
   `normalize_usage` already reads, tolerating both object and mapping representations of the
   provider usage and of the detail. Do not add a second reasoning key, do not infer reasoning
   from visible text, do not subtract it from output, do not change `total_tokens`, do not
   emit a second request or a second accounting row, and do not replace a provider report with
   an estimate. A missing, null or empty detail leaves the usage object without that detail so
   the existing normalization contract yields zero; an explicit provider zero stays zero; a
   malformed optional detail must not raise and must not invent a nonzero value (the existing
   `usage_pricing` coercion is the oracle, not a new clamping rule).
5. **Already-correct consumers are out of bounds.** `agent/usage_pricing.py`,
   `agent/aux_accounting.py` and `agent/codex_runtime.py` already normalize, record and supply
   this usage at the pin. Do not modify them to make anything pass. If the loss is not at the
   inspected adapter boundary, stop and return to Supervisor instead of broadening the change.
6. **AC1 accounting decision.** The correlated operation observable at this boundary is (a)
   exactly one accepted auxiliary operation — one relay logical-call completion for the call —
   and (b) exactly one `session_model_usage` row with `api_call_count=1`, `input`/`output`
   equal to the provider report and the exact separate `reasoning_tokens` value. Assert the
   response **and** the row, not raw normalization alone. If the logical completion cannot be
   observed in a disposable harness without a live binding, record that as a measured limit
   and still assert the single-row correlation; never fabricate the completion.
7. **Aggregate pin.** `AE-433` generates the aggregate and preflight at selected revision
   `58f8c37a49b341f25b8fdd6310542fe932031b8d` with a clean checkout at that revision, and
   declares as `components` only paths that exist there. `INT-433` re-pins to the merged fork
   revision after the fork merge and may then add the new test module. `observed_at_utc` must
   postdate every input it summarizes.
8. Use disposable Git repositories, boards, Project registries, profile homes, SessionDB files
   and state roots. Stripe no live board, HOME, registry or session. Take read-only byte and
   row fingerprints of the preserved live boards before the first writer and after the work.
   If an accidental live mutation is discovered, preserve it as evidence and escalate; direct
   deletion of tasks, comments, events or runs is never cleanup.
9. `.github/workflows/policy.yml` carries exactly two new lines for this objective: the new
   patch path in the allow-list (`AE-433`), and the contract artifact
   `.aether/objective-contracts/oc_3fdf70ccc94e14b1/v1.md` in the expected-manifest list
   (`INT-433`, a bounded integration repair owned by Supervisor, attributed as such and
   verified by re-running the manifest simulation). Exactly one `.gitattributes` whitespace
   line for the new patch is added by `AE-433`. No other manifest entry is added, dropped or
   reordered, and a concurrent textual conflict is reconciled by an ordinary non-rewriting
   merge that drops neither side's entries.
10. Sensitive material stays out of everything committed: no machine paths, operator layout,
    secrets, credentials, private model output or raw runtime state in the patch, ledger,
    fragments, aggregate, evidence or card handoffs. Repository-relative references only. The
    reconciliation validator fails closed on non-portable content and the public-artifact
    scanner rejects operator paths.
11. Writable ownership below is exclusive; concurrent edits to one file across units are
    forbidden. Return to Supervisor for a shared-file collision, a material interface change,
    a baseline-digest mismatch, an unreproducible loss point or any live mutation.
12. Unit compatibility evidence is `patch`. The terminal aggregate conclusion is
    `release_impact=patch`, `release_action=defer`, `release_channel=none`, consistent with the
    source-only boundary. Contradictory evidence returns to Morfeo rather than being normalized.
13. Fork Actions remain disabled for `aether-hermes`: report them **NOT RUN**, never green.
    `#433` stays open after this phase; its effective-runtime and live-call obligations are
    successors. No activation, restart, service or profile edit, `aether update`, tag, release,
    package publication or deployment.
14. Implementers commit only intended paths with Conventional Commits, report exact commands,
    revisions, totals, skips and first-attempt failures, and then request same-card review with
    `kanban_request_review(reviewer="supervisor")`. No push, pull request, merge or issue
    mutation from an implementation unit.
15. `AGENTS.md` and the contract-owning artifacts are preserved unless an authorized change
    actually invalidates an operating instruction. `INT-433` records the explicit
    non-applicability or the coherent update, and rechecks root guidance before closure.

## Execution graph

```text
t_258102e9 Supervisor decomposition root
    -> HF-433 fork adapter reasoning preservation and focused tests (Implementer)
       -> same-card Supervisor review
       -> AE-433 portable HLP-433 artifact, ledger, reconciliation and evidence (Implementer)
          -> same-card Supervisor review
    -> INT-433 terminal integration and dual-repository closeout
       (Supervisor, same flow, terminal=true; depends on root and both reviewed units)
```

`HF-433` is concentrated because the correction is a single adapter boundary plus its tests,
and the alternative split would put two units on `agent/auxiliary_client.py`. `AE-433` cannot
run independently: its byte artifact and every reconciliation claim derive from the accepted
fork commit. `INT-433` is integration and publication, not a substitute for either same-card
unit review. There is no honest implementation parallelism in this dependency chain, and none
is manufactured.

## HF-433 — fork adapter preserves provider reasoning usage

- **Source:** AC1, AC2 and the fork half of AC3; contract Objective, Decisions and
  Assumptions, In Scope, Testing Standard, Stop Conditions; shared decisions 2–8, 10–14.
- **Outcome:** at the unchanged pin, the new focused test fails RED with the provider-reported
  reasoning present and the adapted/session value absent. At the candidate revision the same
  test passes GREEN: a completed Responses response whose usage reports `input`/`output`/total
  and a nonzero nested reasoning detail, in object form, in mapping form, and through a
  terminal `response.completed` SSE stream, reaches `_validate_llm_response` and produces
  exactly one accepted auxiliary operation and one disposable `session_model_usage` row with
  the exact separate reasoning value while `input`/`output`/total are unchanged and reasoning
  is never added to output or total a second time. Explicit zero, absent/null detail, absent
  usage and malformed detail keep the existing zero/unknown behaviour without raising or
  inventing a value, and existing Chat-provider fallback and error accounting stay green.
  Excludes Aether portable artifacts, ledgers, publication and activation.
- **Inputs:** the isolated fork worktree at `58f8c37a…` (tree `a93162c1…`) with the working
  documented environment; the baseline digests in the receipt; issue `#433` and the plan as
  reproduction reference, not authority.
- **Boundaries:** writable `agent/auxiliary_client.py` (the auxiliary Codex/Responses usage
  reconstruction only), `tests/agent/test_auxiliary_client_responses_terminal_420.py` and/or
  one new focused module for this defect, and `tests/hermes_state/test_aux_usage_accounting.py`
  only if a row-shape control is genuinely needed. Preserve `agent/usage_pricing.py`,
  `agent/aux_accounting.py`, `agent/codex_runtime.py`, the Codex/Responses terminal, phase,
  tool-call, fallback, timeout and cancellation behaviour, every unrelated test,
  `AETHER_FORK.md`, lockfiles, workflows and every path outside the fork.
- **Judgement:** private helper names, the exact defensive extraction of the nested detail, the
  fixture and harness layout, and whether the new cases extend the `#420` module or a new one.
  Do not change the decided shape, the no-double-count rule, the absence semantics or the
  source-only boundary.
- **Verification:** RED first with `HERMES_TEST_FILE_RETRIES=0` and no retry, timeout inflation,
  assertion weakening or skip-as-fix, recorded against the unchanged pin; then GREEN at the
  candidate. Minimum affected run: `HERMES_TEST_FILE_RETRIES=0 scripts/run_tests.sh` over the
  touched modules plus the neighboring auxiliary/accounting modules. Also run the fork's
  documented full suite, `python -m compileall -q` on touched trees, Ruff check and format
  status on touched scope, and `git diff --check`, recording exact commands, versions, totals,
  skips, first-attempt failures and unchanged baseline failures. Fork Actions are NOT RUN.
- **Dependencies:** decomposition root only.
- **Completion:** local fork commit(s) attributable to this objective; handoff with the exact
  commit and tree, the measured RED/GREEN and control-matrix evidence, the preservation
  statement, the exact proposed `AETHER_FORK.md` paragraph, compatibility `patch` and remaining
  risks; then same-card Supervisor review. No Aether edit, push, pull request or merge.

## AE-433 — portable HLP-433 artifact, ledger reconciliation and evidence

- **Source:** AC3 (patch identity) and AC4 (Aether side); Deliverables 2 and 3; shared
  decisions 2, 7–14.
- **Outcome:** the accepted `HF-433` fork delta is represented byte for byte as the new
  `HLP-433` portable patch with its SHA-256, apply/reconstruction proof and rollback and
  retirement-gate record; `HERMES_LOCAL_PATCHES.md` gains its detailed section in the
  validator's heading form plus its summary row; the reconciliation fragment binds the required
  behavior, the upstream inspection identity, the retirement gate and the patch digest inside
  the portable-content rules; the aggregate and preflight regenerate consistently at the
  accepted pin; `specs/issue-433-reasoning-usage/evidence/HLP-433.md` records producer facts,
  exact revisions and reproducible commands without claiming merge or issue state.
- **Inputs:** the independently reviewed `HF-433` commit and handoff, verified clean at the
  accepted revision before the patch is derived; the ledger, fragment, schema, validator and
  test surfaces as they exist at this decomposition.
- **Boundaries:** writable `patches/hermes/HLP-433-responses-reasoning-usage.patch`, the
  `HLP-433` fragment under
  `specs/001-aether-v1-productization/evidence/hermes-patch-reconciliation/entries/`, the
  generated aggregate and preflight under `specs/001-aether-v1-productization/evidence/`,
  `HERMES_LOCAL_PATCHES.md`, `.gitattributes` (one whitespace line),
  `.github/workflows/policy.yml` (one allow-list line for the new patch path),
  `tests/test_hermes_patch_reconciliation.py` (the new id in the roster and digest table, plus
  focused controls only if the existing rules need one), and
  `specs/issue-433-reasoning-usage/evidence/HLP-433.md`. Preserve every other patch and
  fragment, the validator and schema, all other ledger records, the Objective Contract, product
  source, lockfiles and `AGENTS.md`.
- **Judgement:** exact evidence-table organization, the wording of the ledger section, and how
  the new fork test module is described in the entry. Do not collapse or rename existing
  records, do not declare a `components` path that does not exist at the pin, do not record
  merge or activation facts that have not been observed, and do not weaken the validator or any
  test to obtain green output.
- **Verification:** digest, parse and `git apply --check` proof plus byte-for-byte tree
  reconstruction against a freshly materialized tree at the exact base; positive and
  fail-closed controls for the new record; the reconciliation generator and then `--check` with
  a clean checkout at the pinned revision; `tests/test_hermes_patch_reconciliation.py`,
  `tests/test_public_artifacts.py` and `tests/test_contract_quality_documents.py`;
  `scripts/check_documentation.py`, `scripts/check_public_artifacts.py --root .` and
  `scripts/check_hermes_baseline_drift.py --json`; Ruff check and format, MyPy and compileall as
  applicable; and the documented Aether bootstrap runner with retries disabled. Record exact
  counts and attribute any unchanged unrelated failure rather than fixing it here.
- **Dependencies:** independently reviewed `HF-433`; the accepted fork commit is the required
  input.
- **Completion:** local Aether commit(s) for portable artifacts and evidence on the
  decomposition branch; handoff with the digest, reconstruction result, the exact proposed
  ledger content, the regenerated outputs, exact gate commands and results, any residual
  derived staleness, compatibility `patch` and remaining risks; then same-card Supervisor
  review. No push, pull request, merge or issue mutation.

## INT-433 — terminal integration and dual-repository closeout

- **Source:** all Deliverables, AC1–AC4, Authority, Testing Standard and Stop Conditions;
  shared decisions 1–15.
- **Outcome:** the accepted `HF-433` and `AE-433` commits are integrated in dependency order
  without squash, amend, rebase or force; the fork branch is pushed, its pull request opened and
  merged normally, with the `AETHER_FORK.md` record applied on that branch; the Aether pull
  request carries the portable evidence and merges normally; the ledger, fragment and generated
  reconciliation files reflect the exact integrated identities with the aggregate re-pinned to
  the merged fork revision once the declared paths exist there; the bounded integration repair
  for the contract-artifact manifest line is applied and attributed; the evidence report is
  completed with observed merge, check, cleanup and preservation facts; `#433` receives a
  factual source-only comment and stays **OPEN**; objective-owned branches and worktrees are
  cleaned only after durable merge evidence while unrelated residue is preserved.
- **Inputs:** this committed decomposition and the independently reviewed `HF-433` and
  `AE-433` commits and handoffs, each preserved as inspectable history.
- **Boundaries:** integration-owned conflict, import, wiring, path and manifest corrections that
  introduce no new behavior (including the `policy.yml` contract-manifest line in shared
  decision 9 and the `AETHER_FORK.md` record); the ledger, fragment, generated
  aggregate/preflight and objective evidence report; the branch carrying this decomposition. Any
  behavior, acceptance, shared-interface or security change returns as implementation rework.
- **Verification:** independently re-run the decisive AC1 object/mapping/SSE route and the AC2
  control matrix at the exact final fork revision; run the fork's documented focused and full
  batteries, compileall, Ruff check/format on touched scope and `git diff --check`; run the
  Aether bootstrap runner, the focused reconciliation tests, reconciliation `--check` against a
  clean checkout at the final revision, documentation, public-artifact, baseline-drift,
  contract-quality and static/type gates; simulate the `policy.yml` manifest step to prove the
  repair; observe the actual required checks on both repositories; audit the pull requests, the
  issue state, branch and worktree residue, the unchanged installed runtime pin and the
  preserved `#494`/`#492` and unrelated live work; and recheck root `AGENTS.md` coherence.
  Diagnose and correct only objective-caused failures within bounded integration authority;
  record unavailable checks as NOT RUN rather than green.
- **Dependencies:** decomposition root plus both independently reviewed implementation units.
  Same Supervisor flow and session affinity with `terminal=true`.
- **Completion:** the three conclusions stated separately and exactly as `release_impact=patch`,
  `release_action=defer`, `release_channel=none`; the release-readiness handoff naming remaining
  live adoption, rollback candidates, board and session preservation witnesses and the specific
  `#433` acceptance not yet qualified; local integration alone is not success.

## Authority and stop conditions

Follow the finalized Objective Contract. Ordinary isolated worktrees, disposable state, tests,
local commits and routine push, pull request, non-bypass merge, issue comment and objective
cleanup in the two provisioned repositories are authorized, using only existing access. Stop and
return to Supervisor or Morfeo when the loss point is no longer the inspected adapter boundary,
the declared fork base changed incompatibly, patch reconstruction is not exact, a required test
cannot isolate provider usage and SessionDB without external access, preservation of `#494`/`#492`
would require live mutation, the full issue would require a new usage schema or provider/router
behavior, a manifest or ledger conflict cannot be reconciled by an ordinary non-rewriting merge,
or the same failure recurs without new evidence. Preserve the candidate and the exact failures
rather than changing owner intent or widening authority. A protected-edge denial for real
credential, external or destructive effects is final; an unexpected denial of ordinary local work
follows Aether's bounded recovery procedure instead of a bypass. Never weaken a guard or a test to
obtain green output, never treat a source-only merge as issue closure or runtime qualification,
and stop before any activation, restart, release, tag or live repair.
