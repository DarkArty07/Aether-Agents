# Execution breakdown: residual session stabilization

**Status:** verified executable decomposition for Objective Contract `oc_291b2fb34b413d92@v2`.
This is the Supervisor-owned execution breakdown; it does not widen the contract, redefine the
material design in `spec.md`/`plan.md`, or record acceptance.

**Derived by:** Supervisor (root task `t_124002ae`, flow
`aether.flow.v1:3090c5ea5fd0fbcd8f2646560b66c63d30b0199d6b9f2fedfc1f8a3d1d074a61`).

**Source contract:** `.aether/objective-contracts/oc_291b2fb34b413d92/v2.md`
(SHA-256 `9fd10684ba41c790f542836b69d0fa5056a36e1b6146e59ef17723c760431442`) on base
`8d70acc8d9756db1f796e44e083c3baa77ede4d3`.

## Receipt

| Check | Observed |
| --- | --- |
| Portable project | `.aether/project.toml` `project_id` `12027989-a08f-41cd-a82c-54ff1bfb6b03` matches the envelope; repository `DarkArty07/Aether-Agents` |
| Contract bytes | SHA-256 `9fd10684ba41c790f542836b69d0fa5056a36e1b6146e59ef17723c760431442`; `status: final`, `version: 2`, supersedes the immutable v1 |
| Base / branch | Base `8d70acc8d9756db1f796e44e083c3baa77ede4d3`; objective branch `aether-agents-2/t_124002ae-execute-oc_291b2fb34b413d92-v2-contract` |
| Design sufficiency | `spec.md` SR-227/SR-396/SR-397/SR-399 plus `plan.md` §D227/§D396/§D397/§D399 settle outcome, interfaces, negative/positive fixtures and acceptance; `quickstart.md` fixes gate commands and canaries; no missing material product decision found |
| v1 residue | The v1 root `t_e963488b` persisted a truncation sentinel body and produced no unique implementation work; its branch tip `ecf4353` is an ancestor of the base and its worktree is clean. Nothing is resumed from it |
| Monitor v4 dependency | Monitor `oc_f8c9fc9320587cf3@v4` is active (board `oc-12027989a08f41cda82c54ff1bfb6b03-f8c9fc9320587cf3-v4`; D16 `t_37daf6b2` running, terminal `t_84c2812b` in `todo`). Its reviewed D15R correction is integrated as the v4 base but the v4 result is not yet accepted; #397 consumes D15R read-only and the terminal phase waits for the Monitor result |
| Profiles / capacity | `implementer`, `supervisor`, `morfeo` exist; implementer cards are queue-bound by the existing per-profile limit. No new role, profile or limit is introduced |
| Project Canonical Skills | `.aether/skills/aether-observe/SKILL.md` is the observation procedure; it is read where relevant and grants no authority |
| Tracker | issues #227, #396, #397, #399 are open; they are tracking records, not contract authority |

## Unit map

| Source | Unit | Outcome |
| --- | --- | --- |
| SR-227, `plan.md` §D227, issue #227 | **U227** (Implementer, root-gated) | `kanban_create` title/body ending in a transport truncation sentinel is rejected by the Aether package-owned pre-tool policy before the Kanban handler, with zero task/event/run writes; covers all roles and both fields; non-terminal marker prose and ordinary cards stay allowed |
| SR-396, `plan.md` §D396, issue #396 | **U396** (Implementer, root-gated) | Observation resolves its own board from canonical contract identity and verified board metadata, never ambient default state; exact binding, terminal-outcome normalization, per-project collector selection; required negatives plus disposable GREEN |
| SR-397, `plan.md` §D397, issue #397 | **U397** (Implementer, root-gated) | Consumes/verifies the accepted D15R/v4 isolation result read-only and adds the residual general probe-entry and pre-write gate plus the reviewer prohibition on direct SQL cleanup; edits only files disjoint from the active Monitor flow |
| SR-399, `plan.md` §D399, issue #399 | **U399** (Implementer, root-gated) | One package-owned transactional editable-reconciliation core with structured receipt, atomic rollback, `env -i`/`python -I` canaries and maintained-fork packaging coverage, built in new/disjoint files; shared lifecycle/CLI/policy wiring stays deferred |
| Integrated verification, #399 deferred wiring, Monitor-v4-gated main integration, runtime canaries, issue closeout, evidence, knowledge and cleanup | **INT** `t_84c2812b`-analogue terminal card (Supervisor, terminal=true, same flow affinity) | terminal integration and closeout |

## Execution graph

```text
t_124002ae (root: receipt, breakdown, handoff)
    ├── U227  (Implementer; base 8d70acc)
    ├── U396  (Implementer; base 8d70acc)
    ├── U397  (Implementer; base 8d70acc; consumes D15R read-only)
    └── U399  (Implementer; base 8d70acc; new/disjoint files)

U227, U396, U397, U399  ->  INT (Supervisor, terminal=true, same flow affinity)
```

U227, U396, U397 and U399 are independent under the actual dependency rules: their
writable surfaces are disjoint (`policy/`+`tests/test_policy_hooks.py`;
`src/aether_agents/observation/**`; `src/aether_agents/lab/**`; new module/new tests),
and none requires another unit's deliverable to start. The real serialization is the
Monitor-v4 seam, not an artificial edge between these four units:

- **U397** must not mutate Monitor-overlapping files (`scripts/telegram_monitor_lab.py`,
  `scripts/qualify_telegram_monitor.py`, `src/aether_agents/monitor/**`,
  `specs/telegram-monitor/**`, `docs/guides/telegram-monitor.md`) while the Monitor flow
  is active; it consumes the accepted D15R result read-only.
- **U399** must not edit the shared `src/aether_agents/lifecycle.py`,
  `src/aether_agents/cli.py` or `.github/workflows/policy.yml` while the Monitor result is
  pending; those wirings are deferred to INT.
- **INT** merges the latest `origin/main` normally, returns semantic conflicts to the
  owning unit instead of resolving them as integration freedom, and only then performs the
  deferred wiring.

## Shared decisions stamped into the unit cards

1. Authority is Objective Contract `oc_291b2fb34b413d92@v2` plus the named owning artifacts
   and this breakdown; skills provide reusable procedure only.
2. Every candidate starts from the finalized contract base
   `8d70acc8d9756db1f796e44e083c3baa77ede4d3` and commits only on its own branch.
3. Implementation units make no remote mutation: no push, no PR, no issue mutation, no
   board-card mutation, no live Kanban writes by tests, no direct SQL cleanup, no service
   restart, no credential/provider/model change.
4. Test runs remove inherited `HERMES_DELEGATED_CHILD_CONTEXT`, `HERMES_KANBAN_*` and outer
   `HERMES_SESSION_*` selectors; probes and canaries use disposable boards/venvs only and
   record the scrubbed environment shape, never identity values.
5. Repository gates for every unit: `uv sync --frozen`; focused pytest; `ruff check` /
   `ruff format --check`; `mypy src/aether_agents`; coverage run; `scripts/run_tests.py`;
   `scripts/check_documentation.py`; `uv build`; public-artifact scan with inherited
   findings disclosed and baseline-compared, never a weakened gate.
6. Unit review uses the native same-card lane (`kanban_request_review`, reviewer
   `supervisor`); INT consumes reviewed units and does not replace their review.
7. Each unit writes one evidence record under `specs/007-session-residual-stability/evidence/`
   with requirement mapping, candidate commit, exact commands/results, fail-before/pass-after,
   compatibility impact and residual risk. The shared `evidence.md` ledger stays
   integration-owned.
8. Adding a tracked file outside `specs/` requires an `.github/workflows/policy.yml` manifest
   entry — a shared file owned by INT in this objective; units that add files record the exact
   expected manifest lines instead of editing it.
9. Release conclusions remain `release_impact=patch`, `release_action=defer`,
   `release_channel=none`; aggregation belongs to INT and must rest on observed evidence.

## Preservation and residue

- Never edit, stage, exact-copy or reformat the canonical Objective Contract artifacts;
  immutable v1/v2 stay intact.
- Preserve the active Monitor flow: its code, board, workers, receipts, labs, retained
  evidence and branches. No worker cancellation, branch mutation or speculative duplicate fix.
- Preserve unrelated worktrees, branches, stashes, jobs, boards, profiles, the operator's
  registry/sessions and the provisioned runtime; no data deletion, history rewrite, check
  bypass, package publication or deployment.
- INT removes only objective-owned merged residue after durable evidence and keeps every
  unmerged or concurrent branch with unique evidence.
