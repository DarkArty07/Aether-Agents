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
| #227 | Pre-tool policy rejects terminal truncation sentinels before Kanban persistence: 24 focused tests / 567 subtests; independent probe 72/72 sentinel cases blocked with a byte-identical disposable board and zero task/event/run rows | Integrated on the objective branch (`021440d`, unit `b6fba98`); runtime hook activation and the canary remain pending | open — closes on the runtime canary |
| #396 | Observation resolves its own execution board from canonical contract identity: 13 focused fixture nodes GREEN, RED at base 11 failed / 2 passed, mutation-pinned | Integrated (`09bad01`, unit `ef3d820`); provider-free contract canary remains pending | open — closes on the runtime canary |
| #397 | Write-capable probes construct one verified disposable context before the first writer; D15R consumed read-only; new gate and reviewer rule covered by 14 tests plus the live-board fingerprint canary | Integrated (`1b59a79`, unit `6f753d0`); writer-probe canary remains pending | open — closes on the runtime canary |
| #399 | One transactional editable-reconciliation operation with private backups, atomic rollback, `env -i` / `python -I` canaries and maintained-fork packaging coverage; 15 tests; both provisioned interpreters inspected read-only as editable targets | Integrated (`0d70c09`, unit `2fe83eb`); shared with the lifecycle installer (`82b7083`); runtime reconciliation canary remains pending | open — closes on the runtime canary |

Every row closes only after its exact `main`/runtime canary; terminal status alone is not
acceptance.

## Integration evidence (objective branch)

- Contract base `8d70acc8d9756db1f796e44e083c3baa77ede4d3`; breakdown `eaf6940`. The four
  units were integrated as merge commits `021440d`, `09bad01`, `1b59a79`, `0d70c09`; the
  then-current `origin/main` as `26f7a55`; the deferred wiring as `82b7083`. No accepted
  unit commit was squashed, amended, rebased or rewritten.
- Full exact-Hermes suite: **2 failed, 1646 passed, 70 skipped, 587 subtests passed**
  (588.74s). Both failures are inherited and reproduce identically at `origin/main`
  (`test_public_artifacts.py::test_tracked_public_surface_contains_no_operator_paths` and
  `tests/test_same_card_phase_predicates.py::test_initial_review_requires_an_independent_reviewer`);
  zero regressions are attributable to this objective.
- Focused lanes at the integrated tip: policy hooks 24 passed / 567 subtests; U396 fixture
  nodes 13 passed; writer isolation 12 passed / 2 environment-conditional skips; editable
  reconciliation 15 passed.
- Static and documentation gates: `compileall`, `mypy` (67 files), `ruff check`,
  `ruff format --check` (156 files), `scripts/check_documentation.py`, `uv build` — clean.
  Canonical base manifest emulation exact (389/389 entries, no duplicates); the CI policy
  steps (canonical base manifest, reproducible policy hooks, accepted R0 design baseline)
  were executed verbatim locally with exit 0.
- CI disclosure: the required checks on `main` are `policy (3.11)`, `policy (3.12)`,
  `policy (3.13)` and `pull-request-target`. The `observation-qualification` job is not a
  required check and is already failing on `main` (it stops at "Enforce integrated coverage
  floor"), so its later steps — including the public-artifact scan, which reports the
  inherited `.aether/objective-contracts/oc_0084270d940c98d9/v1.md` finding — do not run in
  CI and were executed locally instead. The inherited failure is disclosed, not weakened.
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

Post-merge runtime adoption, the three issue canaries, issue closure and residue cleanup are
recorded here by the terminal integration card after the merge to `main`.

## Limits

- Runtime canaries, issue closure and residue cleanup are pending in this record and are not
  claimed by it.
- Environment-conditional skips, inherited failures and the non-required CI job limitation
  are disclosed above rather than hidden or worked around.
