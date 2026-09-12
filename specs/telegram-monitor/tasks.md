# Telegram Monitor — Supervisor continuation breakdown (v2)

**Status:** verified executable continuation/decomposition for Objective Contract
`oc_f8c9fc9320587cf3@v2`.

**Derived by:** Supervisor (root task `t_69c40036`, flow
`aether.flow.v1:57226b362e0f17741ce491044f8569d959521b16f499f8b24226b839e5f9b3ba`).

**Source contract:** `.aether/objective-contracts/oc_f8c9fc9320587cf3/v2.md`
(SHA-256 `1e5aaef54d3ca312af3888bb5fdef97bb374fc4daadb26ba610bf7cf0866624d`) on base
`10e51404ce83ea9fd26d73ad7f4c01c094a30baa`.

**Owning artifacts:** `spec.md` (TM-001…007, D1…D13, AC-1…9), `plan.md`, `quickstart.md`,
`qualification-isolation.md` (D13, normative laboratory design), issue #367.

This file is Supervisor-owned execution decomposition. It supersedes the v1 breakdown at the
same path (decomposition `8399978d47757d7d10aaa756a779b4eb812938ee`, D12 alignment
`2631fa586858dbfc527f215c20921134a2881f9c`, both preserved in Git, plus immutable
`oc_f8c9fc9320587cf3/v1.md`). It does not widen the contract or record feature acceptance.
Card bodies on the v2 board are the executable unit deliveries.

## Receipt

| Check | Observed |
| --- | --- |
| Portable project | `.aether/project.toml` `project_id` is `12027989-a08f-41cd-a82c-54ff1bfb6b03`, matching the envelope; repository `DarkArty07/Aether-Agents` |
| Contract bytes | SHA-256 matches the envelope; `status: final`, `version: 2`, supersedes `oc_f8c9fc9320587cf3@v1` (immutable, preserved) |
| Base / HEAD | `10e51404ce83ea9fd26d73ad7f4c01c094a30baa`; clean objective worktree on the v2 root branch |
| Design sufficiency | D13 plus `qualification-isolation.md` settle bootstrap, source/scenario, native execution, receipt, shutdown, retention, activation and continuation boundaries; no missing material product decision |
| Prior units | MON-01…MON-05 and the independently reviewed MON-05-R1 are preserved with actual commits, trees and evidence (below); v2 reopens and re-reviews none of them |
| Unsafe lane | The shared-registry synthetic-scope lane is rejected and unreachable; the harness refuses with `scope-isolation-unsupported` until a real isolated preflight replaces it |
| Profiles / capacity | `implementer`, `supervisor`, `morfeo` exist; no new role or profile is required |
| Project Canonical Skills | no `.aether/skills/` directory exists; Aether Canonical procedures apply |
| Tracker | issue #367 is open; it is tracking, not contract authority |

## Accepted predecessor units (reused evidence, integrated by MON-INT2)

| Outcome | Commit | Tree | Evidence |
| --- | --- | --- | --- |
| MON-01 approved | `cfbab930727c2e68fb6a0391088e77918b712edd` | `8be7dfe0f046` | `specs/telegram-monitor/evidence/MON-01.md` |
| MON-02 approved | `55334be6fb0d187fef341689775e929a8a286b56` | `f4c35aafbba1` | `specs/telegram-monitor/evidence/MON-02.md` |
| MON-03 approved | `dc19fe31d3c7cf21dbf35cb6669f495f39ee97e2` (receipt `53e1b2da92e872823c56626ab716cc1ebce7fc77`) | `126543d03eba` | `specs/telegram-monitor/evidence/MON-03.md` |
| MON-04 approved | `d908c033d139e9dfeddfedf4461f85b40faedadc` | `39a5a2e78976` | `specs/telegram-monitor/evidence/MON-04.md` |
| MON-05 approved | `2d49418b2ac9a3f64764b84e1b071df48b85070f` | `6dea7a7fc73e` | `specs/telegram-monitor/evidence/MON-05.md` |
| MON-05-R1 approved (test-only) | `704b729bc418f0d009ec32ac6a01e47197f36774` | `4f5574caaa02` | `specs/telegram-monitor/evidence/MON-05-R1.md` |
| MON-06 candidate preserved, NOT accepted | `21d44b5d87deaed2f3e5eccfea15dcd2a740ca6b` | `f9a1a9dfb77b` | `specs/telegram-monitor/evidence/MON-06.md` |

Verified lineage facts: MON-01…MON-05 are ancestors of `2d49418`; `21d44b5` carries that
reviewed chain plus the preserved MON-06 candidate; `704b729` (MON-05-R1) branches from
`2d49418` and is **not** an ancestor of `21d44b5`; the chain diverges from the current
`origin/main` at `b52afd17a93d25e31a48e5c86bd569f45f2f04d4`. Integration of that divergence
belongs to MON-INT2 and must not rewrite history.

## Continuation map

| Source | Unit | Outcome |
| --- | --- | --- |
| D13 bootstrap/scenarios/native execution/receipt/shutdown, quickstart §4, preparation half of AC-2/AC-4/AC-5/AC-7, docs/package half of AC-8 | **MON-06R** (Implementer) | qualification harness, tests, guidance and evidence reworked onto the isolated native-runtime laboratory; deterministic lane stays effect-free |
| AC-8 plugin allowlist coherence with the accepted MON-05 packaging | **MON-LC1** (Implementer) | the approved Aether plugin entry-point set admits the accepted monitor plugin; the six lifecycle allow-list failures disappear without weakening any integrity check |
| AC-1…AC-9 integrated verification, laboratory live qualification, production first delivery/activation/rollback, PR/checks/merge/#367/residue | **MON-INT2** (Supervisor, terminal) | terminal integration and closeout |
| Preservation, authority, privacy, no new credential/provider/model/expense | every unit plus MON-INT2 | bounded local and reversible work only |

## Execution graph

```text
t_69c40036 (v2 root: decomposition and verified continuation handoff)
    ├── MON-06R (Implementer; base 21d44b5)
    └── MON-LC1 (Implementer; base 21d44b5)

MON-06R + MON-LC1  →  MON-INT2 (Supervisor, terminal=true, same flow affinity)
```

MON-06R and MON-LC1 are independent: disjoint writable surfaces (the harness script,
monitor tests/docs and `evidence/MON-06.md` versus `src/aether_agents/lifecycle.py`,
`docs/product-boundary.md` and `evidence/MON-LC1.md`), different observable outcomes, no
shared interface and no shared file. Both branch from the same reviewed chain tip, so
integration is a clean two-parent merge.

MON-INT2 is serialized by design: it consumes independently reviewed units, merges the
preserved chain into `main`, runs the multi-hour laboratory and the production
first-delivery verification, and owns closeout. That is terminal integration, not a
Supervisor implementation unit.

`scripts/qualify_telegram_monitor.py` is a single hotspot file owned exclusively by MON-06R;
the retired registry-swap machinery inside it is removed there, never in a parallel unit.

## Shared decisions stamped into the unit cards

1. Authority is Objective Contract `oc_f8c9fc9320587cf3@v2` plus the named owning artifacts
   and this breakdown; skills provide procedure only.
2. Establish the declared base commit and verify it before editing; treat result-shape,
   `work_memory` and `project_knowledge` summaries as context, not as proof of current source.
3. The harness public contract is unchanged: `--json`, `--live`, `--output`,
   `--wait-hourly-boundaries 2`; without `--live` there are zero model and zero sender calls.
4. Native Hermes code owns due selection, execution and receipts inside the laboratory; the
   harness drives scenarios and observes evidence only.
5. Implementation units make no live external effect: no `--live`, no model or Telegram call,
   no profile/job/plugin/service activation, no push/PR/merge/issue mutation.
6. `.github/workflows/policy.yml` is exclusive to MON-06R.
7. `aether-telegram-monitor = aether_agents.monitor.hermes_plugin` is part of the approved
   Aether plugin entry-point set, because accepted MON-05 packaging already ships it; the
   correction is mechanical and must not weaken any verifier.
8. Each unit writes one portable evidence file under `specs/telegram-monitor/evidence/` with
   requirement mapping, candidate commit, exact commands/results and residual risk.
9. Unit review uses the native same-card review lane; MON-INT2 does not replace it.
10. Units report their own compatibility conclusion; the aggregate release conclusions belong
    to MON-INT2 (`release_impact=minor`, `release_action=defer`, `release_channel=none`, only
    if observed evidence confirms).

## Preservation and residue

- Never edit, stage or exact-copy the canonical Objective Contract; immutable v1 stays intact.
- No SOUL edits, no credential acquisition or widening, no provider/model/router change, no
  production registry replacement/restoration, no forced restart or active-agent interruption,
  no package publication or deployment.
- Preserve concurrent and unrelated branches, worktrees, stashes, jobs, boards, profiles and
  native source databases.
- Expected integration conflict: this file is new on the v2 root branch and also exists on the
  v1 root branch. MON-INT2 resolves that add/add by taking this v2 continuation version; the v1
  text remains preserved in Git history and in immutable `v1.md`.

## v3 continuation — D14 provisioned preflight correction (Supervisor)

**Status:** verified executable continuation/decomposition for Objective Contract
`oc_f8c9fc9320587cf3@v3`.

**Derived by:** Supervisor (root task `t_53a2f761`, flow
`aether.flow.v1:b7e864b140fbb0a9451fc675cb5f1f69fb96673fa3b4ca8d9fae7ad0ee122b20`).

**Source contract:** `.aether/objective-contracts/oc_f8c9fc9320587cf3/v3.md`
(SHA-256 `f21facaf58af20a2d0595cdaa927a99ca6336e5b14b5d073ec3501bbfbf7f47c`) on base
`db4bb59439a3b381901f0f3d00a01f21026aa02d`.

The v2 sections above remain the accepted historical breakdown. This section is the
executable continuation for the remaining work; it does not widen the contract, re-implement
any accepted unit or record feature acceptance.

### v3 receipt

| Check | Observed |
| --- | --- |
| Portable project | `.aether/project.toml` `project_id` `12027989-a08f-41cd-a82c-54ff1bfb6b03` matches the envelope; repository `DarkArty07/Aether-Agents` |
| Contract bytes | SHA-256 `f21facaf58af20a2d0595cdaa927a99ca6336e5b14b5d073ec3501bbfbf7f47c`; `status: final`, `version: 3`, supersedes the immutable v2 |
| Base / branch | Base `db4bb59439a3b381901f0f3d00a01f21026aa02d`; clean objective branch `aether-agents-2/t_53a2f761-telegram-monitor-v3-verify-d14-preflight` |
| Preserved candidate | `19dfc9d68e797f7d365f078ef65be70fbd16f158` verified present with the full accepted monitor chain, harness, tests and evidence; its deterministic verification is recorded on v2 card `t_e7a3aafb` |
| Integration base | Clean merge `3db391a747579605304ceea91f2bdeac50c7dd67` (parents `db4bb594` + `19dfc9d6`); the only path both sides changed, `.github/workflows/policy.yml`, auto-merged keeping both manifest additions — no manual resolution, no behavior change, no accepted commit dropped |
| Design sufficiency | D14 (`spec.md` §D14, `qualification-isolation.md` §"D14 provisioned profile and destination preflight") settles normalization, the native dotenv reference probe, lab/reference independence, the negative control and the one-attempt budget; the inspected native interfaces `hermes_cli.env_loader.load_hermes_dotenv` and `gateway.config.load_gateway_config` exist in the pinned baseline revision |
| Preserved refusal | Private receipt sha256 `eb2f3ad3…`, log sha256 `5a9ca1fe…`; bootstrap-preflight refusal before the attempt boundary, budget unconsumed; left untouched |
| Prior units | MON-01..MON-06R and MON-LC1 commits/evidence are preserved inputs; none is re-implemented or re-reviewed |
| Profiles / capacity | `implementer`, `supervisor`, `morfeo` exist; no new role or profile required |
| Project Canonical Skills | no `.aether/skills/` directory exists; Aether Canonical procedures apply |
| Tracker | issue #367 is open; tracking, not contract authority |

### v3 continuation map

| Source | Unit | Outcome |
| --- | --- | --- |
| D14 profile normalization, provisioned reference destination through the native dotenv loader, lab/reference independence, the testing standard's D14 focused tests, AC-8 documentation coherence | **D14** `t_5a7b776a` (Implementer, root-gated) | corrected harness bootstrap preflight with reproduction-first tests and one evidence record; no live effect |
| AC-1..AC-9 integrated verification, the single corrected live attempt, production activation/first delivery/rollback, PR/checks/merge/#367/residue | **MON-V3-INT** `t_b8077e66` (Supervisor, terminal) | terminal integration and closeout |
| Preservation, authority, privacy, no profile/config/credential/provider/model change, no new expense | every unit plus MON-V3-INT | bounded local and reversible work only |

### v3 execution graph

```text
t_53a2f761 (v3 root: receipt, integration base, continuation handoff)
    └── D14 t_5a7b776a (Implementer; base 3db391a7 + this breakdown commit)

D14  →  MON-V3-INT t_b8077e66 (Supervisor, terminal=true, same flow affinity)
```

D14 is the only implementation unit: `scripts/qualify_telegram_monitor.py` remains a
single-writer hotspot, so no second unit may touch it. MON-V3-INT is serialized by design —
it consumes the reviewed correction, pins the exact final tree, spends the single authorized
live attempt and owns closeout.

### Shared decisions stamped into the v3 unit cards

1. Authority is Objective Contract `oc_f8c9fc9320587cf3@v3` plus the named owning artifacts
   and this breakdown; skills provide procedure only.
2. `HERMES_HOME` accepts both the installation multi-profile root and the exact
   `profiles/morfeo` home and normalizes both to one verified Morfeo profile; missing,
   ambiguous, linked, conflicting or wrong-named candidates and any cwd/worker identity
   fallback are refused; public evidence records only the path class and a digest.
3. The provisioned reference destination is resolved by a restricted child rooted at the
   normalized profile home that calls the native `load_hermes_dotenv()` before
   `load_gateway_config()`, returning only bounded digests/presence and making no
   model/transport call; lab access is never injected into the reference probe (a negative
   control must prove the reference side receives none).
4. The lab receives only already-provisioned access in ephemeral memory and must digest-match
   the reference; the preserved refusal stays unchanged and does not consume the budget.
5. Implementation units make no live external effect: no `--live`, no model or Telegram call,
   no profile/job/plugin/service activation, no push/PR/merge/issue mutation.
6. Unit review uses the native same-card lane; MON-V3-INT consumes the reviewed unit and does
   not replace its review.
7. The unit writes one evidence record under `specs/telegram-monitor/evidence/` with
   requirement mapping, candidate commit, exact commands/results and residual risk; the
   sanitized AC mapping and the aggregate release conclusions belong to MON-V3-INT
   (`release_impact=minor`, `release_action=defer`, `release_channel=none`, only if observed
   evidence confirms).
8. Exactly one corrected live attempt is authorized after review, with a new no-overwrite
   private target; a later live failure stops the experiment with no automatic rerun.

### Preservation and residue (v3)

- Never edit, stage or exact-copy the canonical Objective Contract; immutable v1/v2 stay intact.
- No SOUL edits, no credential acquisition/widening or persisted copies, no
  profile/config/provider/model/router change, no production registry replacement or
  restoration, no forced restart or active-agent interruption, no package publication or
  deployment.
- Preserve the blocked v2 board cards (`t_e7a3aafb`, `t_d22ba5b9`, `t_287d682d`) and their
  evidence, the operator's registry/boards/sessions/jobs, and every concurrent or unrelated
  branch, worktree, stash and job.
- The terminal phase spends the environment's single corrected live attempt and stops on the
  contract's stop conditions; failure preserves integrated HEAD and keeps issue #367 open.

## v4 continuation — D16 accelerated laboratory schedule (Supervisor)

**Status:** verified executable continuation/decomposition for Objective Contract
`oc_f8c9fc9320587cf3@v4`.

**Derived by:** Supervisor (root task `t_43b26502`, flow
`aether.flow.v1:8ea1f13c3800fae8d22534c349f03a5ff1d6cfbf3e6d3342c3c29d812d705481`).

**Source contract:** `.aether/objective-contracts/oc_f8c9fc9320587cf3/v4.md`
(SHA-256 `765a2f48842835d91049f959defd6c3bd15cd43de9ef97da67a37d1a819bcfe0`) on base
`2aec2b73789a0baf14093b6fbb8de04b852fc157`.

The v2 and v3 sections above remain the accepted historical breakdown. This section is the
executable continuation for the remaining work; it does not widen the contract, re-implement
any accepted unit or record feature acceptance.

### v4 receipt

| Check | Observed |
| --- | --- |
| Portable project | `.aether/project.toml` `project_id` `12027989-a08f-41cd-a82c-54ff1bfb6b03` matches the envelope; repository `DarkArty07/Aether-Agents` |
| Contract bytes | SHA-256 `765a2f48842835d91049f959defd6c3bd15cd43de9ef97da67a37d1a819bcfe0`; `status: final`, `version: 4`, supersedes the immutable v3 |
| Base / branch | Base `2aec2b73789a0baf14093b6fbb8de04b852fc157`; objective branch `aether-agents-2/t_43b26502-telegram-monitor-v4-accelerate-isolated` |
| Design sufficiency | D16 (`spec.md` §D16, `qualification-isolation.md` §"D16 proportionate accelerated laboratory schedule", `plan.md`, `quickstart.md`) settles the lab-only minute schedule, the native `cron.jobs.update_job` interface used inside the private lab store, the two-active/one-idle minute cuts, the truthful accelerated labelling rule, the unchanged `0 * * * *` production cadence and the single natural production hour; the inspected native `cron.jobs.compute_next_run`/`update_job`/`get_due_jobs` and `cron.scheduler_provider.InProcessCronScheduler` exist in the pinned baseline. No missing material product decision |
| Preserved candidate chain | D14/D14R candidate `f603f8f1ace4dbb112afb05e032da620642e7050` and the D15R correction `7d433b3835654d605056d4d4e7826bbf9c6feb28` (code candidate `b59e0e06bcffe6722f84aadd3c44995a165a479a`), approved by the independent same-card Supervisor review on v3 card `t_125d63bf` (run 22 "round-3 contract-lens review APPROVED", 0 live runs / 0 model calls / 0 sends), are consumed inputs; harness, monitor modules, tests and evidence records arrive intact |
| Integration base | `828b736745fe1cd86ef51e5620ffc1094a952c32`, the merge of `2aec2b7` with the approved D15R tip `7d433b3`; computed with `git merge-tree` before the merge: no conflict, `.github/workflows/policy.yml` is the only path both sides changed and auto-merged keeping both manifest additions. `git diff --check` clean and the policy manifest emulation exact (377 = 377, no missing/extra) on the integrated tree |
| Preserved live evidence | The private qualification receipts/logs under the operator's private evidence directory and the retained laboratory roots stay untouched; the preserved pre-D14 refusal is unchanged |
| Prior units | MON-01…MON-06R, MON-LC1, D14, D14R and D15R commits/evidence are preserved inputs; none is re-implemented or re-reviewed |
| Profiles / capacity | `implementer`, `supervisor`, `morfeo` exist; no new role or profile required |
| Project Canonical Skills | `.aether/skills/aether-observe/SKILL.md` (present after integration) is a procedure for contract observation using the native `aether_observe` tool; no other `.aether/skills/` entry is relevant to this objective |
| Tracker | issue #367 is open; tracking, not contract authority |

### v4 continuation map

| Source | Unit | Outcome |
| --- | --- | --- |
| D16 (`spec.md` §D16, `qualification-isolation.md` §D16, `plan.md`, `quickstart.md` §live sequence), the D16 half of the testing standard and of AC-2/AC-7/AC-9 | **D16** `t_37daf6b2` (Implementer, root-gated) | bounded harness/tests/docs change: the one private lab job is created and validated through the shipped control service with production shape `0 * * * *`, then only its private lab record is updated through the native `cron.jobs.update_job` interface to `* * * * *`; the same native due selection and `InProcessCronScheduler` cross two active and one idle real minute boundaries; receipts name the actual accelerated expression/timestamps and never claim elapsed-hour evidence; deterministic controls prove the unchanged hourly production shape and reject manual/fake-clock/custom-scheduler evidence; no live effect |
| AC-1..AC-9 integrated verification, the accelerated laboratory live qualification, production activation + one natural hourly due/report/ack, PR/checks/merge/#367/residue | **MON-V4-INT** `t_84c2812b` (Supervisor, terminal) | terminal integration and closeout |
| Preservation, authority, privacy, no clock mutation, no production cadence change, no new credential/provider/model/destination/expense | every unit plus MON-V4-INT | bounded local and reversible work only |

### v4 execution graph

```text
t_43b26502 (v4 root: receipt, integration base, continuation handoff)
    └── D16 t_37daf6b2 (Implementer; base 828b7367 + this breakdown)

D16  ->  MON-V4-INT t_84c2812b (Supervisor, terminal=true, same flow affinity)
```

D16 is the only implementation unit: `scripts/qualify_telegram_monitor.py` remains a
single-writer hotspot, so no second unit may touch it. MON-V4-INT is serialized by design —
it consumes the reviewed unit, pins the exact final tree, spends the single authorized
accelerated live qualification, activates the same candidate in production and owns
closeout.

### Shared decisions stamped into the v4 unit cards

1. Authority is Objective Contract `oc_f8c9fc9320587cf3@v4` plus the named owning artifacts
   and this breakdown; skills provide procedure only.
2. The isolated lab job is created and validated through the normal monitor service with the
   production shape `0 * * * *`; only its private lab record is then updated, through the
   native `cron.jobs.update_job` interface and inside the private lab store, to
   `* * * * *`. Production and every non-lab job remain exactly hourly.
3. No system-clock mutation, no monkeypatched/fake scheduler clock, no manual or forced tick
   as evidence, no custom scheduler, no production cadence change. The existing
   `--wait-hourly-boundaries 2` spelling stays fixed and now selects two accelerated lab
   scheduled boundaries plus one accelerated lab idle boundary.
4. Receipts state the actual lab cron expression and timestamps and never label those cuts
   as production-hourly or elapsed-hour evidence; the single natural production due/report/
   ack after activation remains the only wall-clock hourly oracle.
5. Implementation units make no live external effect: no `--live`, no model or Telegram
   call, no lab job enable, no scheduler start, no profile/job/plugin/service activation, no
   push/PR/merge/issue mutation.
6. Unit review uses the native same-card lane; MON-V4-INT consumes the reviewed unit and does
   not replace its review.
7. The unit writes one evidence record under `specs/telegram-monitor/evidence/` with
   requirement mapping, candidate commit, exact commands/results and residual risk; the
   sanitized AC mapping and the aggregate release conclusions belong to MON-V4-INT
   (`release_impact=minor`, `release_action=defer`, `release_channel=none`, only if observed
   evidence confirms).
8. Exactly one accelerated live qualification attempt is authorized after review, with a new
   no-overwrite private target; a failure after lab job/scheduler/model/Telegram effects
   begin stops with durable private evidence and no automatic rerun. The superseded
   multi-hour lane and the superseded v3 terminal card `t_b8077e66` are not resumed.

### Preservation and residue (v4)

- Never edit, stage or exact-copy the canonical Objective Contract; immutable v1/v2/v3 stay intact.
- No SOUL edits, no credential acquisition/widening or persisted copies, no
  profile/config/provider/model/router change, no production registry replacement or
  restoration, no forced restart or active-agent interruption, no package publication or
  deployment.
- Preserve the blocked v2 board cards (`t_e7a3aafb`, `t_d22ba5b9`, `t_287d682d`), the v3
  board and its cards/evidence, and every concurrent or unrelated branch, worktree, stash,
  job, board, profile and native source database.
- The terminal phase spends the environment's single accelerated live qualification and
  stops on the contract's stop conditions; failure preserves integrated HEAD and keeps
  issue #367 open.

## v5 continuation — D18 production attribution from the board base (Supervisor)

**Status:** verified executable continuation/decomposition for Objective Contract
`oc_f8c9fc9320587cf3@v5`.

**Derived by:** Supervisor (root task `t_c8da0c97`, flow
`aether.flow.v1:2d96ab2db76f5c515b051254662a0a1e1b46118177662ac13933072f4996a5e7`).

**Source contract:** `.aether/objective-contracts/oc_f8c9fc9320587cf3/v5.md`
(SHA-256 `709aebb5bf01d11f5e9758bcd9f4d5fd664b55fa50f222843fd9ac165e1107d5`) on base
`fa164c5a4c7d5080378c28b19d80a74839850c05`.

The v2–v4 sections above remain the accepted historical breakdown. This section is the
executable continuation for the remaining work; it does not widen the contract,
re-implement any accepted unit or record feature acceptance.

### v5 receipt

| Check | Observed |
| --- | --- |
| Portable project | `.aether/project.toml` `project_id` `12027989-a08f-41cd-a82c-54ff1bfb6b03` matches the envelope and the v5 board metadata; repository `DarkArty07/Aether-Agents` |
| Contract bytes | SHA-256 `709aebb5…`; `status: final`, `version: 5`, supersedes the immutable v4, v1–v4 preserved |
| Base / branch | Base `fa164c5` (clean objective worktree, branch `aether-agents-2/t_c8da0c97-telegram-monitor-v5-repair-production-at`), equal to the v5 board `worktree_base_ref` |
| Defect | `sources.py::_contract_metadata` (lines 543-582) reads `.aether/objective-contracts/<contract>/v<version>.md` only from `project.path`; the reception board's contract was absent from the primary working tree, so `_read_board_bindings` reported `FINAL_CONTRACT_UNREADABLE` and the natural report carried `items: []` with 11 coverage gaps while reportable work existed (`rpt_26ad1a292db123d939ee37720c7075c8`) |
| Design sufficiency | D18 (`spec.md` §D18, `plan.md` §4 "Canonical board contract before merge", `quickstart.md` §5, `evidence/authoring.md` §"v5 reception discrepancy") settles the Git-object source, the validated-ref authority, the marker/contract identity checks, the fail-closed gaps, the legacy primary fallback and the read-only rule; no missing material product decision |
| Preserved state | Merged v4 monitor (main `42bf4b9` + docs `fa164c5`), paused production job `a3bfd97f92af` at `0 * * * *`, production store `~/.local/state/aether/monitor/monitor.sqlite3`, rollback backup `home/profiles/morfeo/backups/telegram-monitor-activation-20260911T211250Z`, recovery manifest `home/profiles/morfeo/recovery/monitor-production-activation/`, retained private v7 laboratory evidence |
| Canary oracle | Boards whose contract exists only at their `worktree_base_ref`, verified at `fa164c5`: `oc_291b2fb34b413d92@v2` base `8d70acc8…` (2 open units), `oc_c780a10d94b78d85@v1` base `0a41438a…` (4 open), `oc_844dfc12880ee967@v1` base `9bce0d2…` (1 blocked); the v5 board itself also resolves from `fa164c5` |
| Profiles / capacity | `implementer`, `supervisor`, `morfeo` exist; no new role or profile required |
| Project Canonical Skills | `.aether/skills/aether-observe/SKILL.md` (observation procedure, Morfeo surface); no other `.aether/skills/` entry is relevant |
| Tracker | issue #367 is open; tracking, not contract authority |

### v5 continuation map

| Source | Unit | Outcome |
| --- | --- | --- |
| D18 (`spec.md` §D18, `plan.md` §4, `quickstart.md` §5), the D18 half of the testing standard and of AC-6/AC-8 | **D18** `t_29621955` (Implementer, root-gated) | read-only source binding resolves the project marker and the finalized contract bytes from the board's validated `worktree_base_ref` Git object in the registered repository through an argument-array Git object read; marker and contract identity validated against board metadata before binding; invalid format, unreachable object, missing blob or mismatch fail closed as that board's labeled gap; ref-less legacy boards keep the current primary-filesystem path; real-temporary-Git-repository tests with fail-before/pass-after and negative controls; no live effect |
| AC-1…AC-9 integrated verification, merged default-branch revision, provisioned-runtime update, monitor off/on and the one production attribution canary, #367 reconciliation, residue | **MON-V5-INT** `t_71d4b7c6` (Supervisor, terminal) | terminal integration and closeout |
| Preservation, authority, privacy, no source mutation, no legacy cleanup, no new laboratory | every unit plus MON-V5-INT | bounded local and reversible work only |

### v5 execution graph

```text
t_c8da0c97 (v5 root: receipt, v5 breakdown handoff)
    └── D18 t_29621955 (Implementer; base fa164c5, board worktree_base_ref)

D18 t_29621955  ->  MON-V5-INT t_71d4b7c6 (Supervisor, terminal=true, same flow affinity)
```

D18 is the only implementation unit: `src/aether_agents/monitor/sources.py` is the single
writable product surface, so no second unit may touch it. MON-V5-INT is serialized by design
— it consumes the reviewed unit, pins the exact merged revision, updates the provisioned
runtime, re-enables the preserved job and spends the one production attribution canary before
closeout.

### Shared decisions stamped into the v5 unit cards

1. Authority is Objective Contract `oc_f8c9fc9320587cf3@v5` plus the named owning artifacts
   and this breakdown; skills provide procedure only.
2. A present, format-valid (lowercase 40-character SHA-1) `worktree_base_ref` is
   authoritative: `.aether/project.toml` and `.aether/objective-contracts/<contract>/v<version>.md`
   are read from that exact commit in the registered repository through a read-only Git object
   read passed as an argument array (no shell interpolation, no `checkout`/`worktree`/`fetch`).
   The primary working tree, task workspaces, current branch, recency and other boards are
   never authority.
3. Marker UUID and contract identity/version/status/session fields must agree with the board
   metadata and canonical board slug; a disagreement is that board's labeled gap.
4. Absent ref = unchanged legacy primary-filesystem path. Present-but-invalid format,
   unreachable object, missing marker/contract blob or mismatch = labeled gap for that board
   only, never a silent fallback and never another board's contract.
5. Unrelated invalid boards contribute their own gaps without erasing a separately valid
   binding; SQLite sources stay `mode=ro` and no Git worktree, index, ref or object store is
   modified.
6. Implementation units make no live external effect: no `--live`, no model or Telegram call,
   no job enable/disable, no scheduler, no profile/plugin/service change, no push/PR/issue
   mutation, no runtime change.
7. Unit review uses the native same-card lane; MON-V5-INT consumes the reviewed unit and does
   not replace its review.
8. D18 tests stay inside the existing `tests/test_telegram_monitor_sources.py` (no new tracked
   non-spec path, so the policy manifest needs no addition) and use a real temporary Git
   repository with canonical board metadata.
9. The unit writes one evidence record under `specs/telegram-monitor/evidence/`; the sanitized
   AC mapping and the aggregate release conclusions (`release_impact=patch`,
   `release_action=defer`, `release_channel=none`, unless observed evidence requires
   otherwise) belong to MON-V5-INT.
10. D17 remains in force: no further live laboratory; the retained private v7 evidence stays
    the laboratory record and only the production canary is spent.

### Preservation and residue (v5)

- Never edit, stage or exact-copy the canonical Objective Contract; immutable v1–v4 stay intact.
- Preserve the installed/merged v4 monitor, the paused job `a3bfd97f92af`, its production
  store/receipts, the activation rollback backup and recovery manifest, the retained private
  laboratory evidence, and every concurrent or unrelated branch, worktree, stash, job, board,
  profile and native source database.
- No SOUL edits, no credential acquisition/widening or persisted copies, no
  profile/config/provider/model/router/destination change, no new laboratory, no legacy-source
  cleanup, no forced restart or active-worker interruption outside the authorized verified
  zero-worker window, no package publication, tag or release.
- The terminal phase re-enables the preserved job and spends the one immediate production
  canary; failure preserves integrated HEAD, leaves issue #367 open and applies the documented
  scoped rollback.
