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
