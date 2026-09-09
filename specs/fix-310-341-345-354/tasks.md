# Repair #310/#354/#341/#345 — Supervisor task breakdown

**Status:** verified decomposition for Objective Contract `oc_0084270d940c98d9@v1`.

**Derived by:** Supervisor

**Source contract:** `.aether/objective-contracts/oc_0084270d940c98d9/v1.md`
(SHA-256 `7447fd890a24f6c7a82ca03f6b4aa7a992299d1beda2c78e078b5c6f578812cb`)
on Aether base `6562c09abc815738419c80d17929e4cefceb8a2d` (`origin/main`).

**Fork baseline:** `DarkArty07/aether-hermes` `aether-main`
`6243e40ea6b06e85061bf3fedffaad43eed51dec`.
Target-file SHA-256 at this SHA:
`tools/environments/base.py` `0903f43aff1dc26b156ecb31ce787e09166c3c715a49b85579e76042453c690b`,
`hermes_cli/kanban_db.py` `159b2b521d5c950c086fffe9c89204d8d1334b72b876e6b2a40078c601747910`.
Implementation units add nested isolated worktrees from the provisioned
research checkout of that remote/SHA. They must not mutate `aether-main` or
`morfeo/research-310-354` in place, and must not edit the live editable runtime.

**Owning issues:** [#310](https://github.com/DarkArty07/Aether-Agents/issues/310),
[#354](https://github.com/DarkArty07/Aether-Agents/issues/354),
[#341](https://github.com/DarkArty07/Aether-Agents/issues/341),
[#345](https://github.com/DarkArty07/Aether-Agents/issues/345).

This file is Supervisor-owned execution decomposition. It does not widen the
Objective Contract. Card bodies remain the executable unit deliveries.

## Receipt

| Check | Observed |
| --- | --- |
| Portable project | `.aether/project.toml` `project_id` equals envelope `12027989-a08f-41cd-a82c-54ff1bfb6b03` |
| Native project / board | envelope-bound; do not paste into child bodies |
| Contract bytes | SHA-256 matches the envelope |
| Aether HEAD / `origin/main` | `6562c09abc815738419c80d17929e4cefceb8a2d` (PR #361 merged the contract) |
| Contract canonical base cited in OC | `cebb811ea2407b5053002cc9398cfeb03ad41893` is the first parent of `6562c09`; implement from `6562c09` |
| Fork identity | `DarkArty07/aether-hermes` `origin/aether-main` `6243e40ea6b06e85061bf3fedffaad43eed51dec`; target-file hashes above; provisioned checkout is read-only evidence until a unit-owned nested worktree is added from that SHA |
| Design sufficiency | D310/D354/D341/D345, dual-repo closeout, preservation, and stop conditions are decided; `worktree_base_ref` is the shared #354 interface |
| Knowledge index | bound project matches; `available=false`; source inspection used; Graphify remains out of scope |
| Profiles | `implementer` and `supervisor` exist; no extra roles |
| Project Canonical Skills | none under `.aether/skills/`; Aether Canonical procedures apply |
| Issues | all four OPEN |
| Concurrent residue | many unrelated HLP-280 / Graphify / prior-OC worktrees exist; preserve them |

## Cross-artifact executability

| Concern | Settled conclusion | Execution consequence |
| --- | --- | --- |
| Dual repository | Maintained fork owns #310 snapshot exclusion and #354 Kanban worktree-base resolution. Aether owns #354 authoring/handoff, #341, #345, `HERMES_LOCAL_PATCHES.md`, this `tasks.md`, evidence, and Aether closeout | Never edit the live editable runtime. Never switch Project. Resolve the fork by remote/branch/SHA into an isolated nested worktree. Never mutate `aether-main` or `morfeo/research-310-354` in place |
| Four independent causes | #310 snapshot identity, #354 authoring root + worktree base, #341 memory freshness/integrity, #345 semantic route/finish_reason | Five implementation units with exclusive writable files. Keep issue attribution and regression evidence distinct |
| #354 split across repos | Aether writes validated `worktree_base_ref`; fork consumes it when creating new worktree branches. Shared field name and validation are identical in AE-354 and HF-354 | No invented Aether-only field on the fork. No second Project. `default_workdir` stays the registered primary path |
| `kanban_db.py` vs `base.py` | Different files, different bugs | HF-310 and HF-354 may run together |
| `memory.py` vs `semantic.py` | No import either way | AE-341 and AE-345 may run together |
| `test_knowledge_regressions.py` | Contains both a memory freshness test and semantic D36/D37 tests | Exclusive to AE-345 for this objective. AE-341 extends `tests/test_work_memory.py` and `tests/test_knowledge_failures.py` only |
| Ledgers | Concurrent edits to `HERMES_LOCAL_PATCHES.md` / fork `AETHER_FORK.md` are not independent | Implementation units do not edit either ledger. They supply the exact paragraph in the handoff. FIX-INT applies both after independent review |
| `policy.yml` | Non-`specs/` paths are allowlisted; `specs/` is excluded from that list | Prefer extending existing tracked Aether test files. If AE-354 must add one isolated handoff regression module, that unit updates `.github/workflows/policy.yml` in the same commit. AE-341 and AE-345 must not add new non-`specs/` files |
| Testing | Regression-first; synthetic/deterministic controls; no live paid model or real board | Identical new tests on unchanged bases (RED) then candidate (GREEN). Temporary trees and sanitized identities only |
| Publication / activation | Implementer commits locally and does not push/PR/merge/close issues | FIX-INT owns dual-repo closeout. `release_action=defer`, `release_channel=none`. No runtime reload/activation |
| Out of scope | Sandbox/helper-global redesign, PD-71, credentials, providers, models, profiles, Graphify install/upgrade, broad Hermes sync, concurrent-flow files, force/history rewrite | Report incidental defects; do not absorb them |

Inspected current baseline (`origin/main` `6562c09`, fork `6243e40`):

- Fork snapshot dump (`tools/environments/base.py` `_export_dump_excluding_session_vars`) unsets `HERMES_SESSION_*`, cron deliver vars, `AI_AGENT`, `HERMES_AGENT`, and `HERMES_UI_SESSION_ID`. It does not unset `HERMES_DELEGATED_CHILD_CONTEXT` or `HERMES_KANBAN_*`.
- Fork `_ensure_git_worktree` creates new branches from incidental `HEAD`.
- Aether `ObjectiveContractStore._project` requires Git toplevel == registered primary, so a linked worktree cannot author or prepare.
- Aether execution-board metadata stores `default_workdir` as the authoring `project_root` and has no worktree base ref.
- Work-memory freshness uses `git diff` only (tracked). Reflection cache hits skip note/hash validation. Missing `markdown_sha256` would KeyError rather than `MEMORY_CORRUPT`.
- Semantic fingerprint uses `get_model_identity_digest(aux_task)` with default provider/model and no `api_mode`. `_call_auxiliary_model` ignores `route_info` and `finish_reason`.

## Requirement coverage

| Source | Unit | Notes |
| --- | --- | --- |
| AC-310 / #310 / D310 | HF-310 | Snapshot excludes delegation marker and `HERMES_KANBAN_*`; child denial intact; parent later command clean |
| AC-354 authoring / D354 Aether half | AE-354 | Session-bound worktree authoring; primary unchanged; board identity + `worktree_base_ref` persisted |
| AC-354 worktree materialization / D354 fork half | HF-354 | New board worktrees start at recorded `worktree_base_ref` instead of incidental HEAD |
| AC-341 / #341 / D341 | AE-341 | Untracked dirty freshness; reflection validates notes/hashes before cache; `MEMORY_CORRUPT` for bad metadata |
| AC-345 / #345 / D345 | AE-345 | Fingerprint includes provider/model/api_mode; incomplete finish_reason not cached/applied as complete |
| Deliverables 1–6, dual closeout, residue, Telegram | FIX-INT | After independently reviewed units |
| Preservation / authority | every unit + FIX-INT | No Graphify, no activation, no credentials, no concurrent-flow mutation |

## Shared decisions (stamp into every implementation unit)

1. Authority is Objective Contract `oc_0084270d940c98d9@v1`. Skills grant no authority. Do not edit the canonical Objective Contract.
2. Aether product/evidence starts from `6562c09abc815738419c80d17929e4cefceb8a2d` (`origin/main`). Fork product edits start from isolated nested worktrees of `DarkArty07/aether-hermes` at `6243e40ea6b06e85061bf3fedffaad43eed51dec`. Locate the provisioned fork by remote URL `https://github.com/DarkArty07/aether-hermes.git` and that SHA. Cards remain Aether-project worktrees (`project=p_227bd972`). Each fork unit creates a nested isolated worktree from the provisioned research checkout of that remote/SHA (do not paste machine paths into public artifacts). Never copy or edit the live editable runtime. Never mutate a checkout whose current branch is `aether-main` or `morfeo/research-310-354` in place.
3. Before mutation, re-hash this unit's target production files at the unit base. Required SHA-256 values are in Receipt / the unit body. A mismatch is a stop condition: return to Supervisor; do not patch.
4. Do not modify Graphify, lockfiles, profiles, `home/`, credentials, providers, models, settings, or repository Actions except the single `policy.yml` case owned by AE-354 if it adds one new non-`specs/` file. Do not absorb unrelated issues or mutate concurrent flows.
5. Regression-first: add tests that fail on the unchanged unit base, record RED, then make them pass on the candidate. Use temporary trees and sanitized disposable HOME/HERMES_HOME/task identities. No live paid model and no real/live board or database.
6. Writable-file ownership below is exclusive. Concurrent edits to the same file are forbidden.
7. Do not edit `HERMES_LOCAL_PATCHES.md` or fork `AETHER_FORK.md`. Put the exact ledger paragraph (issue, commit, evidence, scope, upstream relationship, rollback, retirement) in the unit handoff. FIX-INT applies the ledgers.
8. Unit evidence path is unique: `specs/fix-310-341-345-354/evidence/<unit-id>.md` (and native task attachments for large logs). No secrets, operator paths, credentials, or private model responses.
9. Local judgement: private test helper names, equivalent reversible fixture structure, and whether a new focused *fork* test module is clearer than extending an owned existing fork test file. Public result shape, field names, preservation gates, and issue attribution may not vary.
10. Return to Supervisor for a shared-file collision, target-file hash mismatch, a required `snapshots.py` / `delegation_context.py` / `cli.py` behavior change, concurrent-flow overlap that would change public behavior, or any credential/settings/activation change.
11. Local commit on the unit branch; same-card Supervisor review; no push/PR/merge/issue close. Unit compatibility evidence is `patch`. Aggregate belongs to FIX-INT: `release_impact=patch`, `release_action=defer`, `release_channel=none` unless evidence contradicts, in which case stop for Morfeo.
12. `#354` shared interface (identical in AE-354 and HF-354; do not rename):
    - Field name: `worktree_base_ref`.
    - Value: exact prepared-contract HEAD, lowercase 40-char SHA-1 matching `^[0-9a-f]{40}$`.
    - Aether writes it during execution-board create/validate from `prepare_handoff` `base_commit`.
    - Aether `_validate_execution_metadata` requires the field to equal the current prepared `base_commit` on execution boards.
    - Native Hermes `project_id` and `default_workdir` remain the registered primary checkout path. Do not store the authoring worktree path as `default_workdir`. Do not add a second Project. Do not ask the model for a path or base.
    - Fork `_ensure_git_worktree` (or the single helper it already uses) reads board metadata: if `worktree_base_ref` is present and valid, new-branch `git worktree add` uses that ref instead of incidental `HEAD`. If present and invalid, fail closed; do not silently fall back to primary HEAD. If absent, keep current HEAD behavior for non-Aether boards.
13. Do not close an issue from an implementation unit.

## Execution graph

```text
t_3989b4e4 (Supervisor decomposition root)
    → HF-310 t_b6697b55 delegated-child snapshot identity (Implementer, Aether worktree + nested fork worktree)
    → HF-354 t_edf68cf0 Kanban worktree_base_ref materialization (Implementer, Aether worktree + nested fork worktree)
    → AE-354 t_ce292a4b session-worktree contract authoring and board base ref (Implementer, Aether worktree)
    → AE-341 t_757a5f82 work-memory freshness and note integrity (Implementer, Aether worktree)
    → AE-345 t_15c349ea semantic route fingerprint and incomplete finish_reason (Implementer, Aether worktree)
    → same-card Supervisor review on each implementation unit
    → FIX-INT t_ee567392 terminal integration/closeout (Supervisor, same flow, terminal=true)
```

HF-310, HF-354, AE-354, AE-341, and AE-345 are independent: different writable files, no invented shared Aether module, unique evidence paths. AE-354 and HF-354 share only the already-stamped `worktree_base_ref` contract; they do not share files. Same-card review is the unit review lane. FIX-INT consumes independently reviewed units and does not replace unit review.

Necessary serialization is ledger/closeout only (FIX-INT), not a false edge among the five implementation units.

## HF-310 — delegated-child snapshot identity

- Source: contract Owner Intent / Objective / D310 / AC-310; this unit.
- Outcome: a delegated child can run a disposable terminal command with `HERMES_DELEGATED_CHILD_CONTEXT` and genuine child Kanban mutation denial intact. After child scope/completion, the parent process and a later parent command do not observe that marker or stale child `HERMES_KANBAN_*` values from the reusable snapshot. Concurrent and failed/truncated child controls pass. Existing session-var snapshot exclusion remains. Excludes Kanban worktree-base work, Aether product files, ledgers, push/PR, activation.
- Inputs: fork `6243e40ea6b06e85061bf3fedffaad43eed51dec` with `tools/environments/base.py` SHA-256 `0903f43aff1dc26b156ecb31ce787e09166c3c715a49b85579e76042453c690b`. No prerequisite unit. Treat delegation marker and dispatcher-owned `HERMES_KANBAN_*` as transient per-command identity; exclude them from the persistent shell snapshot export; retain existing ContextVar/process propagation and fail-closed Kanban DB guard. Do not clear `os.environ` globally or weaken child denial.
- Boundaries: writable fork `tools/environments/base.py`, `tests/tools/test_snapshot_session_id_leak.py`, `tests/tools/test_delegate_kanban_isolation.py`, and optional new focused fork test module owned by this unit. Preserve `hermes_cli/kanban_db.py`, `agent/delegation_context.py`, `cli.py`, `AETHER_FORK.md`.
- Judgement: whether prefix-unset `${!HERMES_KANBAN_*}` plus the explicit marker is enough versus listing `KANBAN_ENV_KEYS`; fixture shape for parent-after-child snapshot source.
- Verification: fail-first ordinary and delegated-child snapshot cases on unchanged `6243e40` (expect marker and/or `HERMES_KANBAN_*` to persist in the snapshot). Candidate: dump snippet unsets them; a real LocalEnvironment parent command after child scope does not observe them; child denial still fails closed. Run `scripts/run_tests.sh` on the owned tests plus existing snapshot/delegate isolation tests with `HERMES_TEST_FILE_RETRIES=0` from a sterile HOME/HERMES_HOME; confirm imports resolve to the candidate; `git diff --check`; `python3 scripts/check-windows-footguns.py tools/environments/base.py` with zero findings.
- Dependencies: decomposition root only.
- Completion: local fork commit(s) attributable to #310 only; evidence `specs/fix-310-341-345-354/evidence/HF-310.md`; ledger paragraph in handoff; same-card review; unit compatibility `patch`; no push.

## HF-354 — Kanban `worktree_base_ref` materialization

- Source: contract Owner Intent / Objective / D354 fork half / AC-354 worktree start; this unit.
- Outcome: when board metadata carries a valid `worktree_base_ref`, newly materialized Kanban worktrees for new branches start at that commit, not incidental primary HEAD. Invalid present refs fail closed. Absent refs keep current HEAD behavior. `default_workdir` still anchors on the board's configured primary path. Existing occupied-path fallback and linked-worktree reuse stay intact. Excludes Aether store/plugin, snapshot identity, ledgers, push/PR, activation.
- Inputs: fork `6243e40ea6b06e85061bf3fedffaad43eed51dec` with `hermes_cli/kanban_db.py` SHA-256 `159b2b521d5c950c086fffe9c89204d8d1334b72b876e6b2a40078c601747910`. Shared interface from Shared decision 12 (identical to AE-354). No prerequisite unit. Disposable Project/board registries and linked Git worktrees only.
- Boundaries: writable fork `hermes_cli/kanban_db.py` (worktree materialization / metadata read path only), `tests/hermes_cli/test_kanban_worktree_isolation.py`, and a new focused fork test module (preferred name `tests/hermes_cli/test_kanban_worktree_base_ref.py`). Do not edit `tests/hermes_cli/test_kanban_db.py` unless an owned assertion cannot live in the new module, in which case return to Supervisor rather than colliding. Preserve `tools/environments/base.py`, `cli.py` `_resolve_worktree_base`, `AETHER_FORK.md`.
- Judgement: how `_ensure_git_worktree` receives the ref (argument vs metadata read); disposable repo fixture that puts primary HEAD on another commit than `worktree_base_ref`.
- Verification: fail-first on unchanged `6243e40`: with primary on branch B and metadata `worktree_base_ref=A`, a new worktree branch is rooted at B/HEAD. Candidate: it is rooted at A; invalid ref raises; missing field still uses HEAD; `default_workdir` unchanged. Run `scripts/run_tests.sh` on the owned tests with `HERMES_TEST_FILE_RETRIES=0` from a sterile HOME/HERMES_HOME; confirm imports resolve to the candidate; `git diff --check`; `python3 scripts/check-windows-footguns.py hermes_cli/kanban_db.py` with zero findings.
- Dependencies: decomposition root only.
- Completion: local fork commit(s) attributable to #354 only; evidence `specs/fix-310-341-345-354/evidence/HF-354.md`; ledger paragraph in handoff; same-card review; unit compatibility `patch`; no push.

## AE-354 — session-worktree contract authoring and board base ref

- Source: contract Owner Intent / Objective / D354 Aether half / AC-354 authoring and board identity; this unit.
- Outcome: with primary checkout on another branch and an exclusive linked worktree, a session-bound contract is finalized/prepared from that worktree. Exact marker UUID, common-dir, and base bytes are verified. Primary checkout remains byte/status unchanged. One exact board is provisioned with unchanged native Hermes Project identity, `default_workdir` equal to the registered primary path, and `worktree_base_ref` equal to the prepared contract HEAD. Excludes fork Kanban materialization, #341/#345, ledgers, push/PR, activation.
- Inputs: Aether `6562c09abc815738419c80d17929e4cefceb8a2d` with
  `src/aether_agents/objective_contracts/store.py` SHA-256 `a32ca69bc60eb1447393d3942627bfcc887382887e4c60009f7603638e19414e`,
  `src/aether_agents/objective_contracts/hermes_plugin.py` SHA-256 `3216c49e1199039a5557478e019a4f015240c48513324fb5b31059500afc8888`,
  `src/aether_agents/objective_contracts/execution_boards.py` SHA-256 `bb9c51cfe2812ae63fde5f6c1d79543d9bb23fb5d7d58b8b2855a8949dbb6bdc`.
  Shared interface from Shared decision 12 (identical to HF-354). Derive the authoring root from the exact native Hermes session workspace (read-only session binding). Accept only the registered project's primary checkout or a linked worktree sharing its Git common directory and carrying the same verified `.aether/project.toml` project UUID; store/read contract bytes there. Do not add a second Project or ask the model for an arbitrary path/base. Disposable Project/board registries only.
- Boundaries: writable `src/aether_agents/objective_contracts/store.py`, `src/aether_agents/objective_contracts/hermes_plugin.py`, `tests/test_objective_contracts.py`, and optionally `tests/test_project_init.py` or one new isolated handoff regression module. `execution_boards.py` is preserved by default; a tiny helper there is allowed only if it keeps Hermes imports out of `store.py` and introduces no new public slug behavior. If a new non-`specs/` test module is added, update `.github/workflows/policy.yml` in the same commit. Preserve `memory.py`, `semantic.py`, `snapshots.py`, `HERMES_LOCAL_PATCHES.md`.
- Judgement: how to reuse the knowledge-style native session workspace read without importing knowledge into the contract plugin; fixture for exclusive linked worktree + dirty-or-divergent primary.
- Verification: fail-first on unchanged `6562c09`: authoring from a linked worktree raises `AETHER-OBJECTIVE-CONTRACT-PROJECT-GIT-ROOT` (or equivalent) and/or writes through the primary. Candidate: finalize/prepare from the worktree succeeds; primary bytes and `git status` unchanged; prepared `base_commit` equals worktree HEAD; provisioned metadata has native `project_id`, `default_workdir` = primary path, `worktree_base_ref` = that commit. Use disposable registries, not the live board. Run `uv run pytest tests/test_objective_contracts.py tests/test_project_init.py` plus any new module; `git diff --check`.
- Dependencies: decomposition root only.
- Completion: local Aether commit(s) attributable to #354 only; evidence `specs/fix-310-341-345-354/evidence/AE-354.md`; ledger paragraph in handoff; same-card review; unit compatibility `patch`; no push.

## AE-341 — work-memory freshness and note integrity

- Source: contract Owner Intent / Objective / D341 / AC-341; this unit.
- Outcome: untracked source changes mark freshness dirty (`revalidate`). Reflection checks all current notes and markdown hashes before reusing cache. Missing/wrong required immutable metadata returns `MEMORY_CORRUPT`, never `KeyError`/`COMPONENT_UNAVAILABLE`. Valid namespaces, corrections, idempotency, and legitimate cache reuse after validation remain intact. Excludes semantic fingerprint/finish_reason, contract store, ledgers, push/PR, activation, Graphify.
- Inputs: Aether `6562c09abc815738419c80d17929e4cefceb8a2d` with
  `src/aether_agents/knowledge/memory.py` SHA-256 `049d574ebe244e2b79de222ef153391c4644846fdc8b1a48c586bf727560b621`.
  Use the existing tracked-plus-untracked dirty-source semantics from `snapshots.py` `_dirty` (`git diff --name-only` plus `git ls-files --others --exclude-standard`). Do not edit `snapshots.py`. Validate immutable note metadata and markdown hash before any consumer or cache hit. Preserve namespace isolation and cache invalidation. Isolated temporary state and fake Graphify where possible; do not install or modify provisioned dependencies.
- Boundaries: writable `src/aether_agents/knowledge/memory.py`, `tests/test_work_memory.py`, `tests/test_knowledge_failures.py`. Do not edit `tests/test_knowledge_regressions.py` (AE-345 exclusive). Do not add a new non-`specs/` Aether file. Preserve `semantic.py`, `snapshots.py`, `objective_contracts/`.
- Judgement: helper for required-metadata validation; whether to duplicate the two git invocations or call a tiny private helper inside `memory.py`.
- Verification: fail-first on unchanged `6562c09`: untracked file leaves freshness `same_revision`; reflection cache returns without hashing notes; missing `markdown_sha256` raises `KeyError`. Candidate: untracked marks `revalidate`; corrupt/missing required metadata and hash mismatch return `MEMORY_CORRUPT` on read/search/reflect including cache-hit path; valid replay/correction/idempotency still pass. Run `uv run pytest tests/test_work_memory.py tests/test_knowledge_failures.py`; `git diff --check`.
- Dependencies: decomposition root only.
- Completion: local Aether commit(s) attributable to #341 only; evidence `specs/fix-310-341-345-354/evidence/AE-341.md`; ledger paragraph in handoff; same-card review; unit compatibility `patch`; no push.

## AE-345 — semantic route fingerprint and incomplete finish_reason

- Source: contract Owner Intent / Objective / D345 / AC-345; this unit.
- Outcome: changing effective provider/model/API mode changes the semantic fingerprint and prevents stale reuse. Unchanged explicit route still yields zero model calls. Actual route is non-secret and verified. Explicit `finish_reason=length` or any other non-terminal reason produces pending/failed truthful coverage and is not applied or cached as complete. Previous complete snapshot remains preserved by existing store behavior (do not edit `snapshots.py`; if preservation is impossible without it, return to Supervisor). Missing legacy `finish_reason` remains compatible only where the runtime response supplies no reason at all. Excludes work-memory, contract store, Graphify implementation, live paid model, ledgers, push/PR, activation.
- Inputs: Aether `6562c09abc815738419c80d17929e4cefceb8a2d` with
  `src/aether_agents/knowledge/semantic.py` SHA-256 `866309a52748c3b9fff3e65381e8b37e5d9336e9bd095e8d734e7c5ed84622c1`.
  Resolve a non-secret concrete auxiliary route using the existing Hermes auxiliary resolution surface where available (`agent.auxiliary_client.call_llm` already accepts `route_info` and records provider/model; include `api_mode`). Include provider/model/api_mode in the fingerprint. Carry route metadata through the existing call. Refuse cache reuse or cache publication when the actual route is unresolved or mismatched. No provider/credential/config changes and no paid live-model call.
- Boundaries: writable `src/aether_agents/knowledge/semantic.py` and `tests/test_knowledge_regressions.py` (semantic D36/D37 extensions and new tests in that file). Do not edit `tests/test_work_memory.py` or `tests/test_knowledge_failures.py`. Do not add a new non-`specs/` Aether file. Preserve `memory.py`, `snapshots.py`, `objective_contracts/`.
- Judgement: how to resolve route identity without constructing a real SDK client (prefer existing resolve/`route_info` surfaces and fakes); which finish reasons are terminal (`stop` / `tool_calls`) versus incomplete.
- Verification: fail-first on unchanged `6562c09`: fingerprint ignores provider/model/api_mode; `finish_reason=length` with parseable JSON is cached/applied as complete. Candidate: route change invalidates fingerprint; unchanged explicit route makes zero model calls; unresolved/mismatched route is not reused or published; `finish_reason=length` (and other non-terminal reasons) yield pending/failed truthful coverage and do not cache as complete; omitted finish_reason still accepts a complete fake response. Use isolated temp state and fake auxiliary responses. Run `uv run pytest tests/test_knowledge_regressions.py`; `git diff --check`.
- Dependencies: decomposition root only.
- Completion: local Aether commit(s) attributable to #345 only; evidence `specs/fix-310-341-345-354/evidence/AE-345.md`; ledger paragraph in handoff; same-card review; unit compatibility `patch`; no push.

## FIX-INT — Terminal integration and dual-repo closeout

- Source: Deliverables 1–6, AC-310/AC-354/AC-341/AC-345 integrated, Authority, Stop Conditions; this unit.
- Outcome: independently reviewed unit commits integrated without squash/amend/rebase/force; latest compatible `origin/aether-main` and `origin/main` rechecked; fork PR to `aether-main` and Aether PR to `main`; required Aether checks green; fork Actions reported NOT RUN rather than green; issues reconciled with merged evidence and not closed before that evidence; ledgers written with distinct non-destructive #310/#354/#341/#345 records; residue audit limited to this objective; Telegram DM milestone updates where the provisioned profile supports it; aggregate release conclusions. No live activation, reload, reinstall, or publication.
- Inputs: independently reviewed HF-310, HF-354, AE-354, AE-341, AE-345 commits plus this `tasks.md`. Preserve each unit as its own commit. Merge the maintained-fork PR first and pin that SHA in the Aether ledger before the Aether PR.
- Boundaries: integration-owned conflict/import/wiring/path repairs that introduce no new behavior; `HERMES_LOCAL_PATCHES.md`; fork `AETHER_FORK.md`; `specs/fix-310-341-345-354/` integrated report and this `tasks.md` if needed. Behavior gaps return as implementation rework.
- Verification: canonical focused suites on the integrated Aether and fork candidates; Windows-footgun zero findings on fork production files; Aether documentation/policy gates as applicable; git-github-closeout in both repositories; independent re-check of AC-310/AC-354/AC-341/AC-345 oracles. Installed runtime remains unmodified/unreloaded. Preserve unrelated/pre-existing worktrees, branches, stashes, and processes (including HLP-280 residue).
- Dependencies: decomposition root and all five independently reviewed implementation units.
- Completion: aggregate `release_impact=patch` only with compatibility evidence, `release_action=defer`, `release_channel=none`. Local integration alone is not success.

## Authority and stop conditions

Follow the Objective Contract. Ordinary Supervisor/Implementer execution and routine Git/GitHub closeout in the two named repositories are authorized. Stop and return `needs-contract-revision` only for a genuine contract defect (target-file hash mismatch that invalidates the approved design, required sandbox/helper-global injection, PD-71/credential/settings change, Graphify reimplementation, or concurrent-flow mutation). Stop and return `needs-owner-input` only for genuine owner input. Protected denials are authoritative. Do not strand a finished phase awaiting a precreated review child; unit review is same-card. Preserve unrelated/pre-existing worktrees, branches, stashes, and processes.
