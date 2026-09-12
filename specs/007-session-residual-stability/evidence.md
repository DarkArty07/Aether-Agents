# Evidence ledger: residual session stabilization

## Intake

- Owner requests all demonstrated residual bugs resolved, intended artifacts integrated to
  `main`, objective residue cleaned and durable lessons recorded.
- #354 closed directly after 7 focused tests and repeated E2E worktree-base canaries.
- #227, #396, #397 and #399 were open at intake.
- Telegram Monitor `oc_f8c9fc9320587cf3@v4` was integrated to `main` by PR #405 and the
  `oc_f8c9fc9320587cf3@v5` repair (D18) by PR #406 before this objective's integration; the
  owner then stopped the Monitor objective (no further programming; closed as
  stopped/incomplete, not accepted). This objective preserves the Monitor's integrated
  candidate, evidence, paused production job and rollback, and touches no Monitor-owned
  file.
- `project_knowledge` had no snapshot at base; source inspection is the declared fallback.

## Acceptance ledger

| Issue | Candidate evidence | Integrated / runtime evidence | Result |
|---|---|---|---|
| #227 | Pre-tool policy rejects terminal truncation sentinels before Kanban persistence: 24 focused tests / 567 subtests; independent probe 72/72 sentinel cases blocked with a byte-identical disposable board and zero task/event/run rows | Merged in PR #408 (`39a0946`); hook installed through the reviewed sync operation from the merged runtime checkout (`morfeo`/`supervisor`/`implementer` `in_sync`, `sha256 0c1abe9b9275…`); runtime canary **24/24 sentinel cases blocked** (3 roles × 4 spellings × title/body) and **6/6 controls allowed** | **closed** |
| #396 | Observation resolves its own execution board from canonical contract identity: 13 focused fixture nodes GREEN, RED at base 11 failed / 2 passed, mutation-pinned | Merged in PR #408; runtime canaries on the merged runtime: tool-level isolated canary `units=2, events=8, db_unchanged=true`, fresh `as_of`, three live boards byte/row unchanged; CLI-level `aether observe <trace> --project <path> --json` reported `contract_id oc_2222222222222222`, `units=2`, fresh `as_of`, 5 explicit coverage gaps and **no raw task titles** | **closed** |
| #397 | Write-capable probes construct one verified disposable context before the first writer; D15R consumed read-only; new gate and reviewer rule covered by 14 tests plus the live-board fingerprint canary | Merged in PR #408; packaged reviewer rule installed into the live Supervisor profile (`sha256 0361e44c…`); runtime canary: reviewed writer-probe lane (`test_lab_writer_isolation` + neighbours) **70 passed, 1 skipped** while the selected live board stayed **byte-identical** and foreign content unchanged | **closed** |
| #399 | One transactional editable-reconciliation operation with private backups, atomic rollback, `env -i` / `python -I` canaries and maintained-fork packaging coverage; 15 tests; both provisioned interpreters inspected read-only as editable targets | Merged in PR #408; shared with the lifecycle installer; runtime reconciliation on the adopted runtime returned `status=reconciled` for both provisioned interpreters with the source tree and 49-line dirty status **byte-identical**, and both interpreters resolve all **20/20** declared top-level modules from the exact source under `env -i` / `python -I` | **closed** |

No issue closed on source presence, a board flag or a test using injected `PYTHONPATH`.

## Integration evidence (objective branch)

- Contract base `8d70acc8d9756db1f796e44e083c3baa77ede4d3`; breakdown `eaf6940`. The four
  units were integrated as merge commits `021440d`, `09bad01`, `1b59a79`, `0d70c09`; the
  then-current `origin/main` as `26f7a55`; the deferred wiring as `82b7083`; the ledger as
  `a83df7b`; PR #408 merged as `39a0946`. No accepted unit commit was squashed, amended,
  rebased or rewritten.
- Full exact-Hermes suite: **2 failed, 1646 passed, 70 skipped, 587 subtests passed**
  (588.74s). Both failures are inherited and reproduce identically at `origin/main`
  (`test_public_artifacts.py::test_tracked_public_surface_contains_no_operator_paths` and
  `tests/test_same_card_phase_predicates.py::test_initial_review_requires_an_independent_reviewer`);
  zero regressions are attributable to this objective.
- Coverage lane in its CI form (disposable Graphify component provisioned): **2 failed,
  1704 passed, 9 skipped, 587 subtests**; total **79** against the floor of 78. The two
  failures are the same inherited pair.
- Focused lanes at the integrated tip: policy hooks 24 passed / 567 subtests; U396 fixture
  nodes 13 passed; writer isolation 12 passed / 2 environment-conditional skips; editable
  reconciliation 15 passed.
- Static and documentation gates: `compileall`, `mypy` (67 files), `ruff check`,
  `ruff format --check` (156 files), `scripts/check_documentation.py`, `uv build` — clean.
  Canonical base manifest emulation exact (389/389 entries, no duplicates); the CI policy
  steps (canonical base manifest, reproducible policy hooks, accepted R0 design baseline)
  were executed verbatim locally with exit 0 and passed as the required checks on PR #408.
- CI disclosure: the required checks on `main` are `policy (3.11)`, `policy (3.12)`,
  `policy (3.13)` and `pull-request-target` — all green on PR #408. The
  `observation-qualification` job is not a required check and is already failing on `main`
  (it stops at "Enforce integrated coverage floor"), so its later steps — including the
  public-artifact scan, which reports the inherited
  `.aether/objective-contracts/oc_0084270d940c98d9/v1.md` finding — do not run in CI and
  were executed locally instead. The inherited failure is disclosed, not weakened.
- Deferred routing decisions recorded instead of decided locally: (1) the
  `aether hermes reconcile-editable` CLI command suggestively recorded by U399 was not
  added — a new public CLI command requires a capabilities-registry entry and reference
  documentation, and it would change the aggregate compatibility class from `patch` to a
  compatible public addition, which belongs to the contract owner; the reviewed operation is
  instead shared with the lifecycle installer through
  `LifecycleManager.reconcile_runtime_editable`. (2)
  `scripts/qualify_observation.py::_qualification_environment` (the exact-Hermes
  qualification lane, not a Kanban probe) is left unchanged per the U397 deferred notes.

## Runtime acceptance

Runtime adoption on the merged `main` (`39a0946`), performed in order:

1. The dedicated runtime checkout was advanced from `6fefa39` to `39a0946` and the
   installed `aether_agents` was verified resolving from it (including
   `hermes_editable.py` and `lab/isolation.py`).
2. The Hermes editable mappings were refreshed **only** through the reviewed #399
   operation (`status=reconciled`, `rolled_back=false`, both provisioned interpreters;
   source tree `f9b6edde…` and the dirty status byte-identical across reconciliation).
3. The updated pre-tool policy hook was installed through the reviewed sync operation,
   from the merged runtime checkout, with a fresh backup; all three roles report `in_sync`
   at `sha256 0c1abe9b9275…`. An earlier install during the same run used the integration
   worktree's copy of the tool; the correction and its byte-level proof are recorded on the
   terminal card.
4. The packaged reviewer rule was projected into the live Supervisor profile
   (`supervisor-decomposition` `sha256 0361e44c…`, containing the disposable-context
   requirement and the no-direct-SQL-cleanup rule). The `morfeo` and `implementer` profile
   copies are left at their previously installed revision: they do not perform decomposition
   review, and no reviewed cross-profile write path exists for them.
5. **No gateway restart was performed.** The only change that must be live for correctness —
   the pre-tool policy hook — runs as a fresh process per tool call and is already in force;
   the remaining changes load with new processes. A restart was therefore not required, and
   at this point it would have terminated the still-running terminal card itself rather than
   reaching a worker-safe boundary. The new code applies from the next natural restart.
6. The three issue canaries plus the #227 hook canary were executed on the merged runtime
   (see the acceptance ledger); no canary mutated a live board, and every canary used
   disposable state or read-only fingerprints.

## Limits and observations

- The `observation-qualification` job remains red on `main` at the inherited coverage-floor
  step; the public-artifact scan it skips is executed locally and reports only the inherited
  `.aether/objective-contracts/oc_0084270d940c98d9/v1.md` finding, which is not owned by this
  objective and was left untouched.
- The operator note delivered to the terminal card arrived truncated at 216 bytes ending in
  the `...[truncated]` sentinel — the same transport-truncation class as #227, but on a
  `kanban_comment` field rather than a `kanban_create` title/body, which is outside
  SR-227's stated scope. The loss is recorded here as an observation for the contract
  owner; the stored row cannot be recovered.
- Environment-conditional skips, the non-required CI job limitation and every inherited
  finding are disclosed rather than hidden or worked around.
