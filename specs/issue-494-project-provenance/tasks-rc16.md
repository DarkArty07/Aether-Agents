# #494 RC16 adoption — Supervisor execution breakdown

**Status:** verified decomposition for Objective Contract `oc_c770cea3db51d97e@v2`.

**Derived by:** Supervisor

**Source contract:** `.aether/objective-contracts/oc_c770cea3db51d97e/v2.md`
(SHA-256 `cd80efb52125f45af5340baf8119aeaddc4756f9d04ae7722137ae5df1f9adc7`)
on Aether base `dc4872834a2c670c506100fd60c69960247124f2`.

**Material design:** `specs/issue-494-project-provenance/plan-release.md` (RC16).

**Owning issue:** [#494](https://github.com/DarkArty07/Aether-Agents/issues/494).

This file is the Supervisor-owned execution breakdown. It derives work from the finalized
Objective Contract and does not replace or widen it. Card bodies are the executable
deliveries; native board state is the durable execution record. Children materialize at the
board's `worktree_base_ref`, so every card body repeats the decisions it needs.

## Receipt

| Check | Observed |
| --- | --- |
| Portable Project | `.aether/project.toml` `project_id` `12027989-a08f-41cd-a82c-54ff1bfb6b03` equals registry row `p_227bd972` and the contract front matter |
| Contract bytes | `sha256sum .aether/objective-contracts/oc_c770cea3db51d97e/v2.md` = envelope digest exactly |
| Base commit | Clean root HEAD equals `dc4872834a2c670c506100fd60c69960247124f2`; the primary worktree carries one unrelated dirty file (`specs/001-aether-v1-productization/plan-rc6.md`) that no unit may touch |
| Board binding | Board `oc-12027989a08f41cda82c54ff1bfb6b03-c770cea3db51d97e-v2` carries `aether_project_id`, `aether_contract_id`/version 2, the Hermes Project row for this repository, a `default_workdir` resolving to the repository root, and `worktree_base_ref` equal to the base commit; it contains only this root card |
| Selected Hermes pin | Fork `https://github.com/DarkArty07/aether-hermes` `aether-main` `58f8c37a49b341f25b8fdd6310542fe932031b8d`, tree `a93162c1a867202b03c12fa372c71029152fdcf7`. Re-derived on this machine through `aether_agents.lifecycle._materialize_git_archive` + `_tree_sha256` over 9 378 materialized files: digest `a2a9b374bd2022c7f96242b0ab2c95691119262c925389eb3820ca627c581144`, matching the contract. HLP-433's merge `621047dc1c` is a descendant, and neither `tests/agent/test_auxiliary_client_responses_reasoning_433.py` nor any `Previous review returns` context line exists at the pin |
| Fork checkout shape | Proven with the product's own `LifecycleManager._verify_fork_candidate_checkout` on a disposable clone: a clean checkout at the exact commit, branch exactly `aether-main`, origin the maintained fork is **accepted** and re-derives the pinned digest; a dirty checkout and a foreign origin are refused. The fork's local `aether-main` (`84139ae9d8`, a revert) and the published remote tip (`938bc34fbc`, carries HLP-433 plus the RC15 count) are the **wrong** pins |
| Live selection (design premise) | `aether doctor --json --project …` → `result=ready`, `active_version=1.0.0rc15`, release `1.0.0rc15-5dc9cd69da8d18f3`, Hermes `5b2b6ba543…` / digest `adf77d58…`, service unit active, no diagnostics. RC15 is published as a GitHub prerelease and its local tag exists |
| RC15 Supervisor resources | Source `src/aether_agents/resources/profiles/supervisor/SOUL.md` and `.../skills/supervisor-decomposition/SKILL.md` are byte-identical to the installed RC15 release copies (`805cf49d…` / `d201fee7…`), and the RC15 instructions carry the durable-history fallback for the optional count |
| Base-commit red that the objective inherits | `tests/test_public_artifacts.py::test_canonical_base_manifest_matches_tracked_non_specs_files` **fails at the base**: the contract commit tracked `.aether/objective-contracts/oc_c770cea3db51d97e/{v1,v2}.md` without adding them to the CI manifest (manifest 472 vs 474 tracked non-`specs/` files). `origin/main` is consistent; this lane must fix it |
| Test lane | Plain `uv run pytest` lacks `hermes_cli` on `PYTHONPATH` (8 spurious `test_objective_contracts.py` failures). The exact-Hermes runner `uv run --frozen python scripts/run_tests.py -- <paths>` is the authoritative lane and shows only the manifest red |
| Live-effect boundary | Worker and dispatcher both run inside `hermes-gateway-morfeo.service`; a managed cutover restarts that unit, so any live transition must be launched from a durable launcher outside its cgroup |
| Capacity | Existing `supervisor` and `implementer` profiles; `max_in_progress_per_profile` is `implementer: 3`, `supervisor: 1`. No new role, profile or limit change |

## Cross-artifact executability

| Concern | Settled conclusion | Execution consequence |
| --- | --- | --- |
| Identity surface | `VERSION`, `CHANGELOG.md`, `README.md`, `docs/index.md`, `docs/reference/limitations-and-troubleshooting.md`, `AGENTS.md`, `.github/workflows/release.yml` and three test files currently state the RC14/RC15 candidate | One identity unit owns all of them; a second unit must not touch them |
| Reconciliation surface | `entries/HLP-*.json`, the generated aggregate, the preflight, `HERMES_LOCAL_PATCHES.md` and `tests/test_hermes_patch_reconciliation.py` share one digest/registry surface; the aggregate is an input to the lifecycle candidate check | One reconciliation unit owns that surface inside a single card. It also owns the one `tests/test_lifecycle_projections.py` assertion that hard-codes the old deferred set |
| Selected revision | RC16 selects `58f8c37…`, which is *earlier* than the revision the committed aggregate is pinned to (`621047dc1c`) | The aggregate/preflight are regenerated at the selected revision; a stale aggregate may not be relabelled as a candidate PASS, so `--check` must be current too |
| CI manifest | The literal CI roster must list every tracked non-`specs/` path; the base already violates it for the two contract files | The identity unit repairs the base red. New unit-created files (a new script and fixtures) are completed by the integration unit, mirroring the accepted LC-INT precedent; a manifest-only workflow change does not promote the CI matrix |
| Transition oracle | The existing mixed-version entry is frozen to the rc3/rc4/rc5 → rc6 shape; AC3 requires the *actual* RC15 reader and the RC16 candidate, not one simulated manager | A new focused entry is authored and run against a composed candidate tagged only inside a disposable clone; the earlier RC12→RC14 pattern and the rc6 entry are patterns, not the oracle, and neither may be weakened |
| Tag timing | The supported `update --local` route requires exactly one annotated release tag `v1.0.0-rc.16` at the candidate commit; tags are repository-wide and the guard refuses `git tag --force` | Pre-merge qualification tags only inside disposable clones. The real local tag is created once, on the merged commit, during integration, and is never pushed |
| Live effect | The cutover restarts the Aether-owned gateway unit, killing the initiating worker | The transition is launched from a durable unit outside the gateway cgroup and writes a private receipt; the card is written to be resumed after restart and to verify rather than repeat the effect |
| Canary runtime | AC6/AC7 need the *installed* RC16 runtime with the fixed Hermes resolver | The canary runs after the cutover, on disposable boards and separated profile registries, and reports the exercised module's own origin |
| Evidence portability | Tracked evidence is scanned for private paths and secrets | Every evidence file uses project-relative references and generic placeholders; no machine paths, usernames, provider bindings, board ids or credentials |
| Exclusions | `#460`, `#475`, `#404` and HLP-433 remain separate; the stopped RC15 board and the historical incident board are preservation witnesses | Report incidental findings without absorbing them; never clear, repurpose or edit the historical boards |

## Requirement coverage

| Contract source | Unit | Observable coverage |
| --- | --- | --- |
| AC1, AC2 (preservation/disclosure), AC4 (static/docs/manifest) | `RC16-IDENT` | rc16 identity across source, docs, workflow pin and focused tests; RC15 SOUL/skill bytes preserved; manifest red closed |
| AC2 (HLP/preservation), AC4 (candidate tests) | `RC16-HLP` | HLP-428 required/present at the pin; HLP-433 deferred/absent/unretired; refusals; retained-guidance fallback verified without claiming behavior |
| AC3, AC4 (fork regression) | `RC16-TRANS` | Exact RC15→RC16 isolated transition, immutability, state preservation, rollback/reselection and the refusal matrix with the real readers |
| AC1 (merged identity), AC4 (full gates), AC8 (pipeline) | `RC16-INT` | Reviewed merge set, full exact-Hermes runner and static gates, build/package, protected PR checks, green merge, local annotated tag |
| AC5 | `RC16-CUTOVER` | Non-mutating preview, durable-launcher managed cutover, post-cutover doctor/source/projection/service coherence, preservation and one prequalified fallback |
| AC6, AC7 | `RC16-CANARY` | Installed-runtime Project/child/worktree/review canary plus the refusal, generic-scratch and bounded-failure control paths |
| AC8 | `RC16-CLOSE` | Criterion-linked AC1–AC8 evidence by producer and revision, truthful #494 disposition, residue audit/cleanup and observed #425 review signals |

## Units, dependencies and parallelism

| Unit | Assignee | Writable surface (primary) | Depends on | Why the edge exists |
| --- | --- | --- | --- | --- |
| `RC16-IDENT` | implementer | `VERSION`, `CHANGELOG.md`, `README.md`, `docs/index.md`, `docs/reference/limitations-and-troubleshooting.md`, `AGENTS.md`, `.github/workflows/release.yml`, `.github/workflows/policy.yml`, `tests/test_release_bundle.py`, `tests/test_public_artifacts.py`, evidence `RC16-IDENT.md` | root | Independent of the reconciliation surface |
| `RC16-HLP` | implementer | `entries/HLP-*.json`, aggregate + preflight, `HERMES_LOCAL_PATCHES.md`, `tests/test_hermes_patch_reconciliation.py`, one assertion in `tests/test_lifecycle_projections.py`, evidence `RC16-HLP.md` | root | Independent of the identity surface; runs concurrently with `RC16-IDENT` |
| `RC16-TRANS` | implementer | `scripts/qualify_rc16_transition.py`, `tests/test_rc16_transition_qualification.py`, fixtures, evidence `RC16-TRANS.md` | `RC16-IDENT`, `RC16-HLP` | The oracle must bind the real rc16 identity and the real required/deferred reconciliation; authoring against a half-built identity would force rework. Declared concentration: one entry plus its decisive run and the fork regression |
| `RC16-INT` | supervisor (affinity) | integration branch, local annotated tag, evidence `RC16-INT.md`, manifest completion | root + all three units | Consumes only reviewed tips; preserves their commits |
| `RC16-CUTOVER` | supervisor (affinity) | cutover script + private receipt, evidence `RC16-CUTOVER.md` | `RC16-INT` | Needs the merged, tagged candidate |
| `RC16-CANARY` | supervisor (affinity) | disposable board/registries, evidence `RC16-CANARY.md` | `RC16-CUTOVER` | Needs the installed RC16 runtime |
| `RC16-CLOSE` | supervisor (affinity, `terminal=true`) | final report, issue disposition, residue audit | root + all units | Terminal closeout |

One real ordering chain remains: identity/reconciliation → isolated oracle → reviewed merge and
tag → managed cutover → installed canary → closeout. It is inherent to the contract's
evidence-before-effect rule, so it is serialized deliberately rather than padded with
artificial edges. The only parallel lanes are the two disjoint source units.
`supervisor: 1` in-progress and `implementer: 3` are accepted as constraints, not tuned.

## Board and card plan

Children produced together from the verified root: `RC16-IDENT`, `RC16-HLP` (independent
implementer units), `RC16-TRANS` (implementer, after the two), `RC16-INT`, `RC16-CUTOVER`,
`RC16-CANARY` and `RC16-CLOSE` (Supervisor, same session affinity, terminal on the last).
The root completes once this handoff exists; it is not held open for implementation.

## Unit completion and review lane

Each unit commits locally on its own branch and stops at same-card review
(`kanban_request_review`, reviewer `supervisor`); the review verdict is issued only from the
claimed review run. Integration consumes reviewed tips and preserves their commits. The
terminal card consumes reviewed units and does not replace unit review.
