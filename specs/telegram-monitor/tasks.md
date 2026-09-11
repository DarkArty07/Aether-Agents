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
