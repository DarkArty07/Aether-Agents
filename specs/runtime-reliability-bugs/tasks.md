# Runtime reliability bugs — Supervisor task breakdown

**Status:** verified decomposition for Objective Contract `oc_5c2dad1b37b20a80@v1`.

**Derived by:** Supervisor

**Source contract:** `.aether/objective-contracts/oc_5c2dad1b37b20a80/v1.md`
(SHA-256 `8d9af05c77d7833675a8f985742c471963f77cd30aa8cd993837a1fcf9eeda4e`)
on Aether base `0dd27e0eff060f143f80879845f0d76561633f56` (design commit on
`docs/runtime-reliability-six-bugs`; `origin/main` remains
`8af2575ccc3233c43b44bf40a5629ebec26e21da`).

**Fork baseline:** `DarkArty07/aether-hermes` `aether-main`
`c185ee3bb5b6d609241432fd123c16143f065987`.

**Owning specs:** `specs/runtime-reliability-bugs/spec.md` (B267/B292/B294/B295/B301/B304),
`plan.md` (source anchors and preservation), `quickstart.md` (sterile launcher and matrix).
Issues: [#267](https://github.com/DarkArty07/Aether-Agents/issues/267),
[#292](https://github.com/DarkArty07/Aether-Agents/issues/292),
[#294](https://github.com/DarkArty07/Aether-Agents/issues/294),
[#295](https://github.com/DarkArty07/Aether-Agents/issues/295),
[#301](https://github.com/DarkArty07/Aether-Agents/issues/301),
[#304](https://github.com/DarkArty07/Aether-Agents/issues/304).

This file is Supervisor-owned execution decomposition. It does not widen the
Objective Contract. Card bodies remain the executable unit deliveries. No
implementation units were authored by Morfeo.

## Receipt

| Check | Observed |
| --- | --- |
| Portable project | `.aether/project.toml` `project_id` equals envelope `12027989-a08f-41cd-a82c-54ff1bfb6b03` |
| Native project | board envelope `p_227bd972`; do not paste into child bodies |
| Contract bytes | SHA-256 matches the envelope |
| Base / HEAD | `0dd27e0eff060f143f80879845f0d76561633f56` (`docs: finalize approved runtime reliability bug contract`) |
| Fork identity | `DarkArty07/aether-hermes` `aether-main` `c185ee3bb5b6d609241432fd123c16143f065987`; provisioned clone is read-only evidence until a unit-owned worktree is added from that SHA |
| Design sufficiency | B267/B292/B294/B295/B301/B304, dispositions, test matrix, dual-repo closeout, and stop conditions are decided; no missing product API |
| Knowledge index | bound project matches; `INDEX_MISSING` / `available=false`; source inspection used; Graphify remains out of scope |
| Profiles | `implementer` and `supervisor` exist; no extra roles |
| Project Canonical Skills | none under `.aether/skills/`; Aether Canonical procedures apply |

## Cross-artifact executability

| Concern | Settled conclusion | Execution consequence |
| --- | --- | --- |
| Dual repository | Aether owns B267, evidence, `tasks.md`, `HERMES_LOCAL_PATCHES.md`, Aether PR. Maintained fork owns B304/B295/B292/B301/B294 product code, `AETHER_FORK.md`, fork PR | Never edit the live editable runtime. Never switch Project. Resolve fork by remote/branch/SHA into an isolated worktree |
| Aether start point | Design artifacts live on `0dd27e0`, not `origin/main` | Every unit first verifies the Aether checkout contains `specs/runtime-reliability-bugs/` and the contract path; if the provisioned worktree is `main`/`8af2575`, integrate `0dd27e0` before edits |
| `auxiliary_client.py` hotspot | Named resolution, header forwarding, and configured fallback share one file | Concentrate B292 and B301 in RR-AUX; do not parallelize them |
| `error_classifier.py` vs auxiliary | B295 owns `_classify_by_status` 503 exhaustion; conversation_loop already consumes `classified.should_fallback` | RR-295 must not edit `auxiliary_client.py`. If the only honest proof requires that file, return to Supervisor |
| `conversation_loop.py` / `run_agent.py` | Stop call already delegates to `evaluate_kanban_stop`; new-turn already cancels pending review | Preserve both files by default. Capture expected task/run inside `kanban_stop`. A required product edit there is a Supervisor return, not a silent extra file |
| `AETHER_FORK.md` / `HERMES_LOCAL_PATCHES.md` | Concurrent edits to the same ledger file are not independent | Implementation units do not edit either ledger. They supply the exact paragraph in the handoff. RR-INT applies both after independent review |
| `policy.yml` | Literal non-`specs/` allowlist; `specs/` uses existing manifest handling; contract path is already listed | Only the unit that adds a new non-`specs/` Aether file updates `.github/workflows/policy.yml` in the same commit |
| B292 / B294 dispositions | Unchanged-baseline integrated success is an allowed qualification, not a speculative patch | No fake patch entry. B294 stays open if not reproduced. A different #294 cause returns to Morfeo |
| Testing | Owner-approved: deterministic regressions plus real isolated process/native-import/SQLite/loopback-HTTP; mocks alone are insufficient | Follow `quickstart.md` sterile `lab_run`. No paid/live models, profile edits, credentials, or production DB |
| Publication / activation | Implementer commits locally and does not push/PR/merge/close issues | RR-INT owns dual-repo closeout. `release_action=defer`, `release_channel=none` |
| Out of scope | Graphify, #348/#261, #353, #323/#329/#349/#352 repairs, live activation, settings, credentials | Report incidental defects; do not absorb them |

Inspected current baseline (HEAD / fork SHA behavior):

- Aether `isolated_hermes_env` (`src/aether_agents/lab/runner.py`) drops `HERMES_KANBAN_*` / `HERMES_SESSION_*` / `TERMINAL_CWD` / `HERMES_CWD` and pins home/DB/workspaces/XDG. It does not drop `HERMES_DELEGATED_CHILD_CONTEXT`, `HERMES_PROJECT_ID`, `HERMES_TENANT`, or `AETHER_PROJECT_ID`. Callers: live-run around 2140 and observation around 500 (observation rebinds `AETHER_PROJECT_ID` after the helper).
- Fork `evaluate_kanban_stop` allows VALID, fail-closes CONFLICT, nudges MISSING until budget; no durable same-run DB recovery.
- Fork `_classify_by_status` 503/529 preserves overflow then returns retryable overload without `should_fallback`.
- Fork `_CodexCompletionsAdapter.create` builds `resp_kwargs` without copying `kwargs['extra_headers']`. Immutable upstream `agent/auxiliary_client.py:1367-1370` at `NousResearch/hermes-agent@9fd44b4dfc44138b9e5d5689acb56c438364ff7b` copies a non-empty dict.
- Named-custom resolution currently retains `original_provider` before the normalized form; B292 is verification-first.

## Requirement coverage

| Source | Unit | Notes |
| --- | --- | --- |
| B267 / #267 | RR-267 | Disposable-probe isolation, witness DB, escaped destination, parent env |
| B304 / #304 | RR-304 | Same-run durable completion recovery; CONFLICT unchanged |
| B295 / #295 | RR-295 | Explicit exhausted-pool classification and authorized fallback |
| B292 / #292 | RR-AUX | Named-custom qualification; patch only if same-path loss is reproduced |
| B301 / #301 | RR-AUX | Responses `extra_headers` + retry/fallback attribution without auth leakage |
| B294 / #294 | RR-294 | Cancellation-ownership qualification; patch only if scoped race is reproduced |
| Ledgers, dual PR/merge, issues, residue, release | RR-INT | Non-build closeout after independently reviewed units |
| Preservation / authority | every unit + RR-INT | Graphify, unrelated issues, no activation, no credentials |

## Shared decisions (stamp into every implementation unit)

1. Authority is the Objective Contract plus `spec.md` / `plan.md` / `quickstart.md`. Skills grant no authority. Do not edit the canonical Objective Contract.
2. Aether product edits start from a checkout that contains `0dd27e0` (contract + design artifacts). Fork product edits start from isolated worktrees of `DarkArty07/aether-hermes` at `c185ee3bb5b6d609241432fd123c16143f065987`. Locate the provisioned fork by remote/branch/SHA; never copy or edit the live editable runtime; never mutate the provisioned `aether-main` working tree in place.
3. Do not modify Graphify, lockfiles, profiles, `home/`, credentials, providers, models, settings, or repository Actions. Do not absorb #353, #323, #329, #349, #352, #348, or #261.
4. Sterile outer launcher from `quickstart.md` wraps every test command. `HERMES_TEST_FILE_RETRIES=0`. Aether wrapper `uv run --frozen python scripts/run_tests.py` authenticates the exact release-locked Hermes baseline, not the maintained fork. Fork tests use `scripts/run_tests.sh` only. Record candidate source path before each run.
5. Identical new regression tests run against unchanged baseline and candidate. A causal patch requires baseline RED and candidate GREEN. Already-working B292 and not-reproduced B294 report identical baseline/candidate honestly.
6. B295 matches the reported `503` body phrase `no available Codex accounts` case-insensitively in bounded error text, after overflow handling and before generic overload. Do not generalize to generic unavailable/all 503s/all 529s. No unauthorized provider discovery.
7. B301 ports only the upstream `extra_headers` copy into `_CodexCompletionsAdapter.create`, then carries a fresh copy of safe request-scoped metadata through retry/fallback. Exclude Authorization, Proxy-Authorization, Cookie, API-key and provider-specific auth. Destination auth is resolved by the destination client. Cite immutable upstream `NousResearch/hermes-agent@9fd44b4dfc44138b9e5d5689acb56c438364ff7b`.
8. B304: transcript VALID/CONFLICT unchanged; only MISSING may read the pinned worker board read-only for the captured expected task/run. No writes, no fabricated receipts, no schema change, no weakened `expected_run_id`.
9. Writable-file ownership below is exclusive. Concurrent edits to the same file are forbidden. `conversation_loop.py` and `run_agent.py` are preserved unless Supervisor reopens them. Do not edit `auxiliary_client.py` outside RR-AUX, `error_classifier.py` outside RR-295, `kanban_stop.py` outside RR-304, `background_review.py` outside RR-294, or Aether `runner.py` outside RR-267.
10. Do not edit `AETHER_FORK.md` or `HERMES_LOCAL_PATCHES.md`. Put the exact ledger paragraph (issue, commit, evidence, scope, upstream relationship, rollback, retirement) in the unit handoff. RR-INT applies the ledgers.
11. Unit evidence path is unique: `specs/runtime-reliability-bugs/evidence/<unit-id>.md` (and native task attachments for large logs). No secrets, operator paths, credentials, or private model responses.
12. Local judgement: test module names, helper names, and equivalent read-only SQLite/HTTP harness details. Return to Supervisor for a shared-file collision, a required `conversation_loop.py`/`run_agent.py`/`auxiliary_client.py` edit outside ownership, unsafe cross-destination auth, a different #294 cause, or any credential/settings change.
13. Local commit on the unit branch; same-card Supervisor review; no push/PR/merge/issue close. Unit compatibility evidence is `patch` for a compatible fix or `none` for tests-only qualification. Aggregate belongs to RR-INT: patch / defer / none unless evidence contradicts, in which case stop for Morfeo.

## Execution graph

```text
t_6ebf2a50 (Supervisor decomposition root)
    → RR-267 t_ea6c98a6 B267 Aether laboratory isolation (Implementer, isolated Aether worktree)
    → RR-304 t_0e064c53 B304 fork stop-validator recovery (Implementer, isolated fork worktree)
    → RR-295 t_5894f87f B295 fork exhausted-pool classification (Implementer, isolated fork worktree)
    → RR-AUX t_2858d06b B292+B301 fork auxiliary named-resolution and headers (Implementer, isolated fork worktree)
    → RR-294 t_174a8028 B294 fork review-cancellation qualification (Implementer, isolated fork worktree)
    → same-card Supervisor review on each implementation unit
    → RR-INT t_ad396676 terminal integration/closeout (Supervisor, same flow, terminal=true)
```

RR-267, RR-304, RR-295, RR-AUX, and RR-294 are independent: different writable files,
no invented shared interface, and unique evidence paths. RR-AUX is concentrated
because `agent/auxiliary_client.py` is the named-resolution, header-forwarding, and
configured-fallback hotspot. Same-card review is the unit review lane. RR-INT
consumes independently reviewed units and does not replace unit review.

Necessary serialization is ledger/closeout only (RR-INT), not a false edge among
the five implementation units.

## RR-267 — B267 disposable-probe isolation

- Source: spec B267, plan B267, quickstart B267 row; this unit.
- Outcome: every executable disposable-probe entry point uses `isolated_hermes_env()` before native imports/subprocess launch; inherited worker/session/project/tenant/delegated-child identity is discarded; disposable home/DB/workspaces/XDG are assigned; escaped/symlink destinations are rejected before writes; a poisoned-identity subprocess uses only the laboratory board; a separate witness board is unchanged; parent environment is untouched. Excludes fork product code, Graphify, live boards, historical cleanup, observation live model spend.
- Inputs: Aether `0dd27e0` (or descendant containing the design artifacts). No prerequisite unit.
- Boundaries: writable `src/aether_agents/lab/runner.py` (`isolated_hermes_env` and its preflight, plus live-run caller only if the helper is not actually used before imports), `tests/test_e2e_harness.py`, and a new focused test module if the existing test cannot host witness-DB/escape controls. `tests/test_observation_qualification.py` only for preservation that observation still rebinds `AETHER_PROJECT_ID` after the helper. If a new non-`specs/` file is added, update `.github/workflows/policy.yml` expected list in the same commit. Preserve `observation.py` helper-call ordering, `persistent.py`, Objective Contract, lockfiles, Graphify.
- Judgement: how to resolve/reject escaped destinations inside the laboratory boundary; additional explicit names beyond the required set if inspection finds another leaked identity used by the real entry point.
- Verification: fail-first poisoned-env + witness-DB + native create/claim/complete + parent-env immutability + symlink/escape rejection. Direct assertions for cleared `HERMES_PROJECT_ID`, `HERMES_TENANT`, `HERMES_DELEGATED_CHILD_CONTEXT`, `AETHER_PROJECT_ID`. `lab_run uv run --frozen python scripts/run_tests.py -- -q --tb=short tests/test_e2e_harness.py` plus any new module; ruff/format on touched Python; `git diff --check`. Native Kanban imports only after isolation. No production board.
- Dependencies: decomposition root only.
- Completion: local Aether commit; evidence `specs/runtime-reliability-bugs/evidence/RR-267.md`; same-card review; unit compatibility `patch`; no push.

## RR-304 — B304 same-run durable completion recovery

- Source: spec B304, plan B304, quickstart B304 row; this unit.
- Outcome: on transcript `MISSING` only, `evaluate_kanban_stop()` may ALLOW when read-only durable proof matches the captured expected task/run on the pinned worker board; CONFLICT remains fail-closed; no writes; wrong board/task/run/event, unreadable DB, reopened task, and contradictory transcript are rejected. Excludes lifecycle-tool changes, schema changes, `conversation_loop.py` edits, auxiliary/classifier/review files.
- Inputs: fork `c185ee3bb5b6d609241432fd123c16143f065987`. No prerequisite unit.
- Boundaries: writable fork `agent/kanban_stop.py`, `tests/agent/test_kanban_stop.py`, and new fork tests discovered from the tree for native DB/tool coverage. Prefer existing `hermes_cli/kanban_db.py` read facilities; edit that file only if they cannot open SQLite read-only without write bootstrap, and then only a read-only helper. Preserve `tools/kanban_tools.py` `expected_run_id` fence, `conversation_loop.py`, other units' files, `AETHER_FORK.md`.
- Judgement: internal resolver function names; how to capture expected task/run from worker context at evaluation time without a conversation_loop change.
- Verification: identical new tests on unchanged baseline (RED for the recovery case) and candidate (GREEN). Native SQLite witness: complete once, hide call/result from conversation, validator allows exit, event/row/notification counts unchanged on repeated reads. Negatives from the spec row. `lab_run env HERMES_TEST_FILE_RETRIES=0 scripts/run_tests.sh tests/agent/test_kanban_stop.py` plus new files; `git diff --check`. Confirm imports resolve to the candidate fork source.
- Dependencies: decomposition root only.
- Completion: local fork commit; evidence `specs/runtime-reliability-bugs/evidence/RR-304.md` in the Aether checkout after integrating `0dd27e0`; ledger paragraph in handoff; same-card review; unit compatibility `patch`; no push.

## RR-295 — B295 explicit exhausted-pool fallback

- Source: spec B295, plan B295, quickstart B295 row; this unit.
- Outcome: explicit exhausted-pool `503` is classified with `should_fallback=True` before generic overload; ordinary transient overload/overflow/holder failures unchanged; only already configured authorized candidates are used; no configured secondary and all-candidates-fail remain bounded; completed local tool sentinel is not replayed. Excludes `auxiliary_client.py`, new routing frameworks, credential refresh, quota probing.
- Inputs: fork `c185ee3bb5b6d609241432fd123c16143f065987`. No prerequisite unit.
- Boundaries: writable fork `agent/error_classifier.py` (`_classify_by_status` 503/529 branch), `tests/agent/test_error_classifier.py`, and a new caller-exercise test module that does not modify `auxiliary_client.py` or RR-AUX tests. Preserve auxiliary named-resolution/header code, `conversation_loop.py`, `AETHER_FORK.md`.
- Judgement: whether an unambiguous structured pool-exhaustion code already on the wire may also be matched. Do not add guessed body variants.
- Verification: real loopback HTTP: exhausted primary then configured healthy secondary; capture destinations/counts and auth separation. Generic 503 overload still backoff; overflow unchanged; undeclared candidate never contacted; tool sentinel not repeated. Baseline RED / candidate GREEN for the exhaustion case. `lab_run env HERMES_TEST_FILE_RETRIES=0 scripts/run_tests.sh tests/agent/test_error_classifier.py` plus new files. If proof requires editing `auxiliary_client.py`, stop and return to Supervisor.
- Dependencies: decomposition root only.
- Completion: local fork commit; evidence `specs/runtime-reliability-bugs/evidence/RR-295.md`; ledger paragraph in handoff; same-card review; unit compatibility `patch`; no push.

## RR-AUX — B292 named-custom qualification and B301 header preservation

- Source: spec B292 and B301, plan “B292/B301: one coherent auxiliary request path”, quickstart B292 and B301 rows; this unit.
- Outcome: (B301) request-scoped extra headers reach actual Responses adapter HTTP on primary, retry, and configured fallback without forwarding destination auth; mappings/defaults are not mutated; subsequent independent requests have no stale attribution; secondary uses its own fake credential. (B292) both `custom:<name>` and admitted bare-name spellings use the named endpoint/credential/mode on direct and configured-fallback routes; anonymous/built-in preserved; missing named config is not silently another provider. If B292 integrated controls already pass on the unchanged baseline, deliver tests/evidence only and do not patch resolution. Excludes classifier exhaustion (RR-295), stop-validator, background review, Aether lab.
- Inputs: fork `c185ee3bb5b6d609241432fd123c16143f065987`. Immutable upstream citation for the extra_headers copy. No prerequisite unit.
- Boundaries: writable fork `agent/auxiliary_client.py` (adapter `extra_headers` copy; retry/fallback helpers carrying a fresh safe-header copy; named resolver only if a same-path loss is reproduced), `tests/agent/test_auxiliary_client.py`, `tests/agent/test_auxiliary_client_resolve_dedup.py`, `tests/agent/test_auxiliary_named_custom_providers.py`, and new focused tests as needed. Preserve `error_classifier.py`, `kanban_stop.py`, `background_review.py`, `AETHER_FORK.md`.
- Judgement: internal parameter names for the safe-header copy. Prefer the existing auxiliary attribution mapping over a universal header filter. If arbitrary provider-sensitive headers cannot be separated safely, return that material case.
- Verification: actual SDK/adapter HTTP to a local recorder covering sync/async and streaming/non-streaming where supported, primary retry, and configured fallback. B292: temporary named entry, two distinguishable synthetic credentials, bare model, explicit api_mode, both spellings, direct and fallback. No unrelated global key. Baseline vs candidate: B301 causal patch must be RED/GREEN; B292 may be identical pass. `lab_run env HERMES_TEST_FILE_RETRIES=0 scripts/run_tests.sh tests/agent/test_auxiliary_client.py tests/agent/test_auxiliary_client_resolve_dedup.py` plus named-custom and new files.
- Dependencies: decomposition root only. Concentrated because one writable hotspot file.
- Completion: local fork commit(s) that keep B301 and any B292 repair inspectable; evidence `specs/runtime-reliability-bugs/evidence/RR-AUX.md` with separate B292 and B301 dispositions; ledger paragraph only for actual code corrections; same-card review; unit compatibility `patch` for B301 and `patch` or `none` for B292; no push.

## RR-294 — B294 interruption-ownership qualification

- Source: spec B294, plan B294, quickstart B294 row; this unit.
- Outcome: controlled interleavings prove cancellation ownership with instance/request assertions and event/barrier synchronization: cancel before thread start/admission, new foreground turn while review is in a blocked HTTP call, review completion racing the next review, and intentional `/stop`. If these reproduce the scoped lifecycle race, adapt only the existing upstream run-token/admission/identity-qualified-cleanup behavior. If they do not, commit regression evidence and leave #294 open as not reproduced on the qualified baseline. Excludes log-timestamp correlation, sleep-inferred races, session-ID/cache policy changes, disabling the feature, unrelated lease/monitor work, and a newly identified different cause (return to Morfeo).
- Inputs: fork `c185ee3bb5b6d609241432fd123c16143f065987`. Immutable upstream `agent/background_review.py` around 914-1136 at `NousResearch/hermes-agent@9fd44b4dfc44138b9e5d5689acb56c438364ff7b` only if a patch is justified. No prerequisite unit.
- Boundaries: writable fork `agent/background_review.py` and tests `tests/run_agent/test_background_review.py`, `tests/run_agent/test_background_review_cache_parity.py`, `tests/run_agent/test_background_review_cost_controls.py`, `tests/test_background_review_session_isolation.py`, plus new event-controlled harness tests. Preserve `conversation_loop.py` and `run_agent.py` by default; preserve cache prefix and session ID policy; do not edit `AETHER_FORK.md`.
- Judgement: spy/harness placement at existing seams. Permanent telemetry is not required.
- Verification: real local HTTP with Events/Barriers (no sleep-as-ordering). Assert review cancellation does not abort the foreground client/flags/result; pre-admission cancel means no request; identity-qualified cleanup; intentional stop still propagates. Cache/session preservation. If all controls pass on unchanged baseline, no product patch and issue remains open. If a different interruption cause is demonstrated, capture it and return to Morfeo. `lab_run env HERMES_TEST_FILE_RETRIES=0 scripts/run_tests.sh tests/run_agent/test_background_review.py tests/run_agent/test_background_review_cache_parity.py tests/run_agent/test_background_review_cost_controls.py tests/test_background_review_session_isolation.py` plus new files.
- Dependencies: decomposition root only.
- Completion: local fork commit; evidence `specs/runtime-reliability-bugs/evidence/RR-294.md`; ledger paragraph only if a causal patch landed; same-card review; unit compatibility `patch` or `none`; no push.

## RR-INT — Terminal integration and dual-repo closeout

- Source: common acceptance/closeout in spec.md, plan integration section, quickstart closeout; this unit.
- Outcome: independently reviewed units integrated without squash/amend/rebase/force; fork PR to `aether-main` and Aether PR to `main`; required Aether checks green; fork Actions reported NOT RUN; issues reconciled with exact dispositions; ledgers written; residue audit; aggregate release conclusions. No live activation or publication.
- Inputs: independently reviewed RR-267, RR-304, RR-295, RR-AUX, RR-294 commits. Preserve each as its own commit. Commit this `tasks.md` if not already on the integrated branch.
- Boundaries: integration-owned conflict/import/wiring/path/`policy.yml` repairs that introduce no new behavior; `HERMES_LOCAL_PATCHES.md`; fork `AETHER_FORK.md`; `specs/runtime-reliability-bugs/evidence/` integrated report. Behavior gaps return as implementation rework.
- Verification: per-behavior matrix on the integrated candidates; Aether documentation/policy/exact-Hermes gates; fork local runner with retries disabled; git-github-closeout in both repositories; independent re-check of poisoned isolation, read-only same-run proof, cross-destination auth, and review cancellation ownership.
- Dependencies: decomposition root and all five independently reviewed implementation units.
- Completion: aggregate `release_impact=patch` only with compatibility evidence, `release_action=defer`, `release_channel=none`. Local integration alone is not success.

## Authority and stop conditions

Follow the Objective Contract. Ordinary Supervisor/Implementer execution and routine Git/GitHub closeout in the two named repositories are authorized. Stop and return `needs-contract-revision` only for a genuine contract defect (different material #294 cause, unsafe cross-destination auth, broader protocol/API change, missing Project/board/repository identity). Stop and return `needs-owner-input` only for genuine owner input. Protected denials are authoritative. Do not strand a finished phase awaiting a precreated review child; unit review is same-card. Preserve unrelated/pre-existing worktrees, branches, stashes and processes.
