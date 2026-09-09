# Autonomous Aether bug remediation — Supervisor task breakdown

**Status:** verified decomposition for Objective Contract `oc_ddebf175a40251f7@v1`.

**Derived by:** Supervisor

**Source contract:** `.aether/objective-contracts/oc_ddebf175a40251f7/v1.md`
(SHA-256 `722100569399ac7b61e15bccdcba28fd5fafe1585e4a1f7fbbe3bf5dcf0aa4e8`)
on Aether base `b52afd17a93d25e31a48e5c86bd569f45f2f04d4` (contract commit on
`docs/runtime-reliability-six-bugs`). `origin/main` remains
`e9379c4712509c01f133745faaf810857b9a33a8`.

**Fork baseline:** `DarkArty07/aether-hermes` `aether-main`
`28b593efa86bbc674b32f488c35932a4e7e85a51` (revalidated at decomposition;
matches the contract's intake observation).

**Tracking:** [#366](https://github.com/DarkArty07/Aether-Agents/issues/366).
Scoped issues: #364 #343 #362 #315 #298 #323 #284 #346 #306 #293 #296 #303
#275 #360 #357 #352 #349 #329.

This file is Supervisor-owned execution decomposition. It does not widen the
Objective Contract. Card bodies remain the executable unit deliveries. No
implementation units were authored by Morfeo.

## Receipt

| Check | Observed |
| --- | --- |
| Portable project | `.aether/project.toml` `project_id` equals envelope `12027989-a08f-41cd-a82c-54ff1bfb6b03` |
| Native project / board | envelope-bound; do not paste into child bodies |
| Contract bytes | SHA-256 `722100569399ac7b61e15bccdcba28fd5fafe1585e4a1f7fbbe3bf5dcf0aa4e8` matches the envelope |
| Aether HEAD | `b52afd17a93d25e31a48e5c86bd569f45f2f04d4` (`docs: add autonomous bug remediation contract`) |
| `origin/main` | `e9379c4712509c01f133745faaf810857b9a33a8`; implement from a checkout that contains the contract commit, not from `origin/main` alone |
| Fork identity | `DarkArty07/aether-hermes` `aether-main` `28b593efa86bbc674b32f488c35932a4e7e85a51`; no provisioned local clone was found at decomposition; units resolve the remote/SHA into an isolated nested worktree |
| Design sufficiency | All 18 issue outcomes, priority waves, testing standard, dual-repo closeout, Telegram-as-monitor, stop conditions, and release conclusions are decided in the contract. No missing public API. |
| Knowledge index | bound project matches; `INDEX_MISSING` / `available=false`; source inspection used |
| Profiles | `implementer` and `supervisor` exist; no extra roles |
| Project Canonical Skills | none under `.aether/skills/`; Aether Canonical procedures apply |
| Issues | all 18 scoped issues OPEN; #366 OPEN; excluded #348 #334 #274 #317 #316 #261 #251 remain out of scope |
| Concurrent residue | many unrelated HLP-280 / Graphify / prior-OC worktrees exist; preserve them |
| Telegram | execution-board notify subscription is TUI; owner instruction: a separate monitor owns Telegram delivery. Do not block units on channel inspection. |

## Cross-artifact executability

| Concern | Settled conclusion | Execution consequence |
| --- | --- | --- |
| Dual repository | Aether owns #364 #343 #298 #323 #284 #346 #360 #357 #352 #329 and Aether-side #362/#315 tests/evidence. Maintained fork owns #362 review independence, #315 SOUL/approval if the loaded source is there, #306+#293 metadata, #296+#303 auxiliary, #275 vision if in-repo, #349 FTS trace | Never edit live `home/` or the live editable Hermes runtime. Never switch Project. Resolve fork by remote/branch/SHA into a nested isolated worktree. Never mutate `aether-main` in place |
| Priority waves | P0 before P1 before P2 before P3. Parallelism only inside a wave when files/interfaces allow | P1 cards parent-gate on independently completed P0 units, and so on. Do not skip a higher-risk wave |
| `agent/model_metadata.py` hotspot | #306 false LM Studio classification and #293 advertised context windows share one file | Concentrate as ABR-META. Distinct issue dispositions in one handoff |
| `agent/auxiliary_client.py` hotspot | #296 Chat-only auxiliaries and #303 title-fallback attribution share one file | Concentrate as ABR-AUX. Distinct dispositions. Do not mix with ABR-META |
| `policy.yml` hotspot | R0 `rglob('*.md')` (#323) and the non-`specs/` allowlist share one workflow file | ABR-323 owns the R0 scan restriction. Other units prefer extending existing test files. A required new non-`specs/` file updates only the expected-file list in the same commit and flags `hotspot: .github/workflows/policy.yml`. Decomposition already lists this contract path |
| `tests/test_knowledge_regressions.py` | Contains GitHub PR-impact/triage controls used by #346 | Exclusive to ABR-346. ABR-343 extends `tests/test_work_memory.py` only |
| Ledgers | Concurrent edits to `HERMES_LOCAL_PATCHES.md` / fork `AETHER_FORK.md` are not independent | Implementation units do not edit either ledger. They supply the exact paragraph in the handoff. ABR-INT applies both after independent review |
| Testing | Contract testing standard: identical new tests on unchanged baseline and candidate; Aether wrapper; fork `scripts/run_tests.sh` with `HERMES_TEST_FILE_RETRIES=0`; real seams, not mocks-only | A pass-on-retry is never deterministic proof. No live paid model, live board, credential, or production DB as fixture |
| Publication / activation | Implementer commits locally and does not push/PR/merge/close issues | ABR-INT owns dual-repo closeout. Aggregate `release_action=defer`, `release_channel=none` |
| Telegram | Operational delivery via the existing monitor; no private destination in public artifacts | Units record durable board/test/PR evidence only. INT writes Spanish milestone text from that evidence. Do not configure Telegram |
| Out of scope | #348 #334 #274 #317 #316 #261 #251, Dependabot PRs #290 #291, Graphify product changes, live activation, credentials, settings, force/bypass | Report incidental defects; do not absorb them |

Inspected current baseline (Aether `b52afd1`, fork `28b593e`):

- `ObjectiveContractStore` finalize/validate uses `contains_secret_shape` and truncation checks; it does not apply `scripts/check_public_artifacts.py` path grammar (`absolute-user-home`, `windows-user-home`, `operator-desktop-layout`).
- `work_memory` `_SECRETS` matches private-key blocks, `sk-...`, and `AKIA...` only; password assignment, GitHub token prefixes, and Bearer values are accepted.
- Aether same-card tests request `reviewer="supervisor"` on the first cycle; a second `request_review` omits reviewer and still expects assignee `supervisor`. Issue #362 records implementer reclaim when reviewer is omitted.
- Aether pre-tool hook has no SOUL/agent-instruction family; #315 denial text is an approval-timeout on protected instruction files, likely maintained-fork/runtime approval rather than this hook. #298 is this hook's CREDENTIAL path vs documentation placeholders.
- R0 policy step in `.github/workflows/policy.yml` uses `Path('.').rglob('*.md')`.
- Aether `.gitignore` already has `/.worktrees/`; `aether init` ignore policy does not ensure that rule on brownfield checkouts.
- `execute_pr_impact` still uses one `gh pr view --json ...files` then slices to 500; `execute_triage_prs` does not bind/verify `headRefOid` per PR.

## Requirement coverage

| Source | Wave | Unit | Owning repository | Notes |
| --- | --- | --- | --- | --- |
| #364 | P0 | ABR-364 | Aether | Reject nonportable operator-local paths before finalize; portable refs remain accepted |
| #343 | P0 | ABR-343 | Aether | Reject demonstrated credential-shaped work-memory text; preserve benign notes |
| #362 | P0 | ABR-362 | Fork + Aether tests | Independent review cannot be reclaimed by the implementing profile |
| #315 | P1 | ABR-315 | Fork (qualify Aether if loaded source is Aether) | Owner-authorized tracked SOUL source edits must not vanish into an unanswerable timeout; genuine protected effects stay denied |
| #298 | P1 | ABR-298 | Aether | Placeholder-only docs allowed; actual credential-shaped fixtures blocked |
| #323 | P1 | ABR-323 | Aether | Public policy link scan does not traverse ignored runtime dependencies |
| #284 | P1 | ABR-284 | Aether | Project-linked `.worktrees/` ignored on brownfield init without hiding tracked conflicts |
| #346 | P2 | ABR-346 | Aether | Bounded PR file pagination + moving-head consistency; zero-impact vs unavailable preserved |
| #306 #293 | P2 | ABR-META | Fork | LM Studio classification by response shape; gateway-advertised context windows with compatible fallback |
| #296 #303 | P2 | ABR-AUX | Fork | Chat-only auxiliaries on existing compatible path; title-fallback attribution without auth leakage |
| #275 | P2 | ABR-275 | Fork if in permitted repos | Valid local image reaches supported vision path, or honest out-of-repo disposition |
| #360 | P3 | ABR-360 | Aether | Exact Hermes baseline checkout is deterministic or retains bounded Git stderr |
| #357 | P3 | ABR-357 | Aether | PluginContext harness: product cause vs environment; no retry-as-fix |
| #352 | P3 | ABR-352 | Aether | Concurrent lifecycle timeout: product sync vs fixture deadline |
| #349 | P3 | ABR-349 | Fork | Search-projection trace on unchanged maintained baseline |
| #329 | P3 | ABR-329 | Aether | Journal-storage concurrency deterministic or honest flake disposition |
| #366 + closeout | INT | ABR-INT | Both | After independently reviewed units; issue reconciliation; dual PR/merge; residue; release conclusions |
| Preservation / authority | every unit + ABR-INT | — | No activation, no credentials, no excluded issues |

## Shared decisions (stamp into every implementation unit)

1. Authority is Objective Contract `oc_ddebf175a40251f7@v1` (SHA-256 `722100569399ac7b61e15bccdcba28fd5fafe1585e4a1f7fbbe3bf5dcf0aa4e8`). Skills grant no authority. Do not edit the canonical Objective Contract.
2. Aether product/evidence starts from a checkout that contains the contract commit `b52afd17a93d25e31a48e5c86bd569f45f2f04d4` and this `tasks.md`. Fork product edits start from isolated nested worktrees of `DarkArty07/aether-hermes` at `28b593efa86bbc674b32f488c35932a4e7e85a51`. Locate the fork by remote URL `https://github.com/DarkArty07/aether-hermes.git` and that SHA. Cards remain Aether-project worktrees. Never copy or edit the live editable runtime; never mutate a checkout whose current branch is `aether-main` in place; never edit `home/`.
3. Before mutation, resolve the actual imported source path, commit, Python/runtime version and clean-enough tree. A fork-target hash mismatch versus `28b593e` is a stop: return to Supervisor.
4. Do not modify Graphify product behavior, lockfiles, live profiles, credentials, providers, models, settings, dispatcher configuration, or repository Actions except the `policy.yml` cases owned below. Do not absorb excluded issues.
5. Testing: identical new regression/control tests against unchanged baseline and candidate with already-provisioned dependencies. Causal patch requires baseline RED and candidate GREEN. Already-working or allowed not-reproduced outcomes report identical baseline/candidate honestly and leave the issue open when required. Aether: `uv run --frozen python scripts/run_tests.py`. Fork: `HERMES_TEST_FILE_RETRIES=0 scripts/run_tests.sh`. `git diff --check` and Ruff on touched Python. No pass-on-retry as proof. No live paid model, live board, production DB, or real credential as fixture. Synthetic credentials/HTTP replies must be visibly fixtures.
6. Writable-file ownership below is exclusive. Concurrent edits to the same file are forbidden.
7. Do not edit `HERMES_LOCAL_PATCHES.md` or fork `AETHER_FORK.md`. Put the exact ledger paragraph (issue, commit, evidence, scope, upstream relationship, rollback, retirement) in the unit handoff when a downstream fix landed. ABR-INT applies the ledgers.
8. Unit evidence path is unique: `specs/autonomous-bug-remediation/evidence/<unit-id>.md` (native task attachments for large logs). No secrets, operator paths, credentials, private destinations, or private model responses.
9. Local judgement: private helper names, equivalent reversible fixture structure, and whether to extend an owned existing test file versus one new focused module. Public result shape, issue attribution, shared interfaces, and preservation gates may not vary.
10. Return to Supervisor for a shared-file collision, a required edit outside this unit's writable surface, a different material cause, unsafe cross-destination auth, a required live `home/` edit, or any credential/settings/activation change.
11. Local commit on the unit branch; same-card Supervisor review (`reviewer=supervisor`); no push/PR/merge/issue close. Unit compatibility evidence is `patch` for a compatible fix or `none` for tests-only / not-reproduced qualification. Aggregate belongs to ABR-INT: `release_impact=patch` only with compatibility evidence otherwise `none`; `release_action=defer`; `release_channel=none`.
12. #364 grammar (do not invent a second scanner): reuse the three kinds and regex construction in `scripts/check_public_artifacts.py` (`absolute-user-home`, `windows-user-home`, `operator-desktop-layout`). Valid portable relative/URL references remain accepted. Do not rewrite, delete, or exempt historical contract `oc_0084270d940c98d9@v1`.
13. #343 demonstrated shapes only (synthetic fixtures, never real secrets): password assignment, GitHub token prefixes (`ghp_` / `gho_` / `ghu_` / `ghs_` / `ghr_` / `github_pat_`), and Bearer authorization values. Preserve existing private-key / `sk-` / `AKIA` rejection and benign prose. Do not send suspected secret text to Graphify or an auxiliary model. Do not broaden from evidence-free guesses.
14. #362: a request for independent review with no independent reviewer must fail closed or resolve a configured reviewer; the implementing profile must not reclaim/approve that review run. Keep the existing review lifecycle explicit. Do not disable same-card review.
15. #298: placeholder-only documentation (including staging auth placeholders already treated as placeholders by the hook) is allowed; a fixture containing an actual credential-shaped value still fails closed. No broad guard exemption and no PD-71 weakening.
16. Provider/runtime units (#306 #293 #296 #303 #275): look upstream first; cite the actual loaded fork file. Do not upgrade a moving dependency. Do not guess or silently widen routing. Destination authentication must not leak across fallback/attribution.
17. P3 units: reproduce on unchanged baseline first. Correct only an in-scope deterministic product defect. A pass on retry, pre-existing upstream failure, or environment-only failure is an honest disposition, not a speculative patch.
18. Do not close GitHub issues from an implementation unit.

## Execution graph

```text
t_1a2e74ee (Supervisor decomposition root)
    P0 → ABR-364  #364 contract path grammar (Implementer, Aether worktree)
    P0 → ABR-343  #343 work-memory credential shapes (Implementer, Aether worktree)
    P0 → ABR-362  #362 independent review reclaim (Implementer, Aether worktree + nested fork worktree)
    P1 → ABR-315  #315 authorized SOUL source edit (Implementer; fork nested worktree if source is fork)
    P1 → ABR-298  #298 placeholder-only docs guard (Implementer, Aether worktree)
    P1 → ABR-323  #323 R0 scan ignore-boundary (Implementer, Aether worktree)
    P1 → ABR-284  #284 brownfield .worktrees ignore (Implementer, Aether worktree)
    P2 → ABR-346  #346 PR pagination / moving-head (Implementer, Aether worktree)
    P2 → ABR-META #306+#293 model metadata (Implementer, nested fork worktree)
    P2 → ABR-AUX  #296+#303 auxiliary client (Implementer, nested fork worktree)
    P2 → ABR-275  #275 local vision path (Implementer, nested fork worktree or evidence-only)
    P3 → ABR-360  #360 exact-baseline checkout (Implementer, Aether worktree)
    P3 → ABR-357  #357 PluginContext harness (Implementer, Aether worktree)
    P3 → ABR-352  #352 concurrent lifecycle timeout (Implementer, Aether worktree)
    P3 → ABR-349  #349 FTS projection trace (Implementer, nested fork worktree)
    P3 → ABR-329  #329 journal-storage concurrency (Implementer, Aether worktree)
    → same-card Supervisor review on each implementation unit
    → ABR-INT terminal integration/closeout (Supervisor, same flow, terminal=true)
```

P0 units are independent (different writable files). P1–P3 cards are parent-gated on the previous wave so higher-risk blockers are not skipped. Inside a wave, units are independent except the concentrated hotspots named above. Same-card review is the unit review lane. ABR-INT consumes independently reviewed units and does not replace unit review.

Necessary serialization is (1) wave priority and (2) ledger/closeout (ABR-INT), not a false edge among P0 units.

## ABR-364 — #364 contract finalization path grammar

- Source: contract In Scope #364; issue #364; this unit.
- Outcome: Objective Contract validate/finalize rejects operator-local absolute/home/desktop-layout paths using the bounded public-artifact grammar before immutable finalization. Valid portable relative paths and http(s) references remain accepted. Historical invalid contract bytes are not rewritten. Excludes hook/credential work, work-memory, review lifecycle, fork product code.
- Inputs: Aether checkout containing `b52afd1` + this `tasks.md`. No prerequisite unit.
- Boundaries: writable `src/aether_agents/objective_contracts/store.py`, `scripts/check_public_artifacts.py` only if sharing the grammar requires a call/extract that preserves scanner behavior, `tests/test_objective_contracts.py`, `tests/test_public_artifacts.py`. If a new `src/` helper is required, this unit owns it and updates the `policy.yml` expected-file list in the same commit. Preserve finalized contract files, `privacy.py` secret grammar except via existing `contains_secret_shape` use, other units' files.
- Judgement: call vs tiny shared helper for the three path kinds; where to attach the check (draft validate and finalize, not after immutability).
- Verification: fail-first finalize/validate with an operator-local path (expect accept on unchanged baseline, reject on candidate). Portable relative and URL refs still finalize. Scanner still flags the same three kinds. `uv run --frozen python scripts/run_tests.py -- -q --tb=short tests/test_objective_contracts.py tests/test_public_artifacts.py`; ruff/format; `git diff --check`.
- Dependencies: decomposition root only (P0).
- Completion: local Aether commit; evidence `specs/autonomous-bug-remediation/evidence/ABR-364.md`; same-card review; unit compatibility `patch`; no push.

## ABR-343 — #343 work-memory credential-shaped text

- Source: contract In Scope #343; issue #343; this unit.
- Outcome: durable work-memory input rejects the demonstrated password-assignment, GitHub token prefix, and Bearer authorization shapes across user-provided note text and evidence fields, while preserving benign prose and namespace behavior. Validation stays local and deterministic. Excludes observation privacy redesign, GitHub PR tools, Graphify.
- Inputs: Aether checkout containing `b52afd1` + this `tasks.md`. No prerequisite unit.
- Boundaries: writable `src/aether_agents/knowledge/memory.py`, `tests/test_work_memory.py`, and existing knowledge failure tests that already cover `SENSITIVE_CONTENT` if they live outside `tests/test_knowledge_regressions.py`. Do not edit `tests/test_knowledge_regressions.py` (ABR-346). Do not edit `observation/privacy.py` unless the only honest shared helper is already imported; prefer memory-local patterns for the three demonstrated shapes.
- Judgement: exact synthetic fixture strings (non-live, visibly fake) for the three shapes; whether evidence[] field scanning already shares `_text()`.
- Verification: baseline accepts the three synthetic shapes; candidate rejects them with `SENSITIVE_CONTENT`; benign notes, existing private-key/`sk-`/`AKIA` cases, and namespace isolation preserved. Never persist a real secret. `uv run --frozen python scripts/run_tests.py -- -q --tb=short tests/test_work_memory.py tests/test_knowledge_failures.py tests/test_knowledge_schema.py`.
- Dependencies: decomposition root only (P0).
- Completion: local Aether commit; evidence `specs/autonomous-bug-remediation/evidence/ABR-343.md`; same-card review; unit compatibility `patch`; no push.

## ABR-362 — #362 independent review reclaim

- Source: contract In Scope #362; issue #362; this unit.
- Outcome: when independent review is required and no independent reviewer is supplied, the implementing profile cannot reclaim or approve that review run. The request either requires an explicit reviewer or resolves a configured reviewer and fails closed if none exists. Existing review lifecycle remains explicit. Excludes SOUL/approval, credential hook, metadata/auxiliary.
- Inputs: fork `28b593efa86bbc674b32f488c35932a4e7e85a51`; Aether checkout containing `b52afd1` + this `tasks.md`. No prerequisite unit.
- Boundaries: writable fork `hermes_cli/kanban_db.py` and `tools/kanban_tools.py` (request_review / claim_review path only), fork tests under `tests/hermes_cli/` / `tests/tools/test_kanban_tools.py` as needed, Aether `tests/test_same_card_phase_predicates.py`. Preserve `conversation_loop.py`, `run_agent.py`, `background_review.py`, Aether policy hook, ledgers.
- Judgement: fail-closed missing reviewer vs configured default reviewer, as long as the implementing profile cannot self-approve. Do not invent a second review queue.
- Verification: isolated board: implementer requests review without reviewer; implementer claim of the review run is denied or never assigned; supervisor/configured reviewer can claim. Existing explicit-reviewer cycle still works. Baseline RED / candidate GREEN for the reclaim case. Fork `HERMES_TEST_FILE_RETRIES=0 scripts/run_tests.sh` on owned tests; Aether wrapper on `tests/test_same_card_phase_predicates.py`. Confirm imports resolve to the candidate fork.
- Dependencies: decomposition root only (P0). Concentrated dual-repo because the defect is native lifecycle plus Aether acceptance.
- Completion: local fork and/or Aether commits attributable to #362; evidence `specs/autonomous-bug-remediation/evidence/ABR-362.md`; ledger paragraph if fork product changed; same-card review; unit compatibility `patch`; no push.

## ABR-315 — #315 owner-authorized SOUL source edit

- Source: contract In Scope #315; issue #315; this unit.
- Outcome: an owner-authorized ordinary reversible edit of tracked package-source `SOUL.md` either proceeds or receives a usable approval interaction; it does not disappear into an unanswerable timeout. Genuine protected effects remain denied. If the defect exists only in untracked live runtime state, qualify and report without editing `home/`. Excludes credential-placeholder hook (#298), review reclaim (#362).
- Inputs: independently reviewed P0 units. Re-resolve the actually loaded approval/file-tool source at execution time (fork vs live runtime). Fork base `28b593e` if the loaded source is the maintained fork.
- Boundaries: if fork: writable `tools/approval.py` and/or the file-tool path that emits `protected agent-instruction file(s) (SOUL.md)`, plus its tests. Aether tracked `src/aether_agents/resources/profiles/*/SOUL.md` is evidence, not an activation target. Do not edit live profile SOUL files. Do not add a permanent bypass or new permission exception.
- Judgement: tracked source vs installed-profile distinction at the existing approval seam. If the only reproduction is live TUI timeout outside permitted repositories, stop with evidence.
- Verification: sterile fixture distinguishing tracked package SOUL vs live profile SOUL. Baseline timeout/false deny vs candidate usable path. Protected live-profile / unauthorized instruction writes still deny. No real owner TUI as the only proof if a local seam exists; if it does not, record that limit. Fork runner with retries disabled, or Aether wrapper if the loaded source is Aether.
- Dependencies: P0 units (priority wave), not a file dependency.
- Completion: local commit or tests-only qualification; evidence `specs/autonomous-bug-remediation/evidence/ABR-315.md`; same-card review; `patch` or `none`; no push.

## ABR-298 — #298 placeholder-only documentation guard

- Source: contract In Scope #298; issue #298; this unit.
- Outcome: documentation containing placeholders only is allowed through the Aether pre-tool credential guard; a fixture containing an actual credential-shaped value still fails closed. No broad exemption.
- Inputs: independently reviewed P0 units. Aether checkout containing the contract + this `tasks.md`.
- Boundaries: writable `policy/hooks/aether_pre_tool_policy.py`, `tests/test_policy_hooks.py`. Preserve PD-71 families, remote-mutation and destructive patterns. Do not edit live installed hooks under `home/`.
- Judgement: whether staging-runbook placeholders need an additional explicit placeholder token already consistent with `PLACEHOLDERS` / `_is_placeholder`; do not drop high-confidence patterns.
- Verification: regression with staging auth placeholders allowed on `write_file`/`patch` of a docs path; actual credential-shaped fixture still `CREDENTIAL` blocked; existing durable-secret and acquisition tests preserved. `python3 -m unittest discover -s tests -p 'test_policy_hooks.py' -q` and Aether wrapper on `tests/test_policy_hooks.py`.
- Dependencies: P0 units (priority wave). Independent files from ABR-323/ABR-284/ABR-315.
- Completion: local Aether commit; evidence `specs/autonomous-bug-remediation/evidence/ABR-298.md`; same-card review; `patch`; no push.

## ABR-323 — #323 R0 policy scan ignore boundary

- Source: contract In Scope #323; issue #323; this unit.
- Outcome: public policy link/fence scanning does not traverse ignored runtime dependencies, while existing public tracked-surface checks remain complete. No Graphify change and no runtime-dependency deletion.
- Inputs: independently reviewed P0 units.
- Boundaries: writable `.github/workflows/policy.yml` only in the "Validate accepted R0 design baseline" step (the `root.rglob('*.md')` loop). Do not weaken sequential-ID, checklist, or secret-like spec payload checks. Do not absorb allowlist edits owned by other units except to keep the file coherent if already changed on this branch.
- Judgement: `git ls-files '*.md'` vs skip-gitignored `rglob`. Prefer tracked files so CI and a dirty provisioned checkout agree.
- Verification: replay the R0 python against a tree that contains an ignored `home/.venv-hermes/.../Privacy.md` broken link (or equivalent fixture); candidate does not fail on that ignored file; a broken link in a tracked markdown still fails. Document that clean CI worktrees were never a sufficient reproduction.
- Dependencies: P0 units (priority wave). Exclusive owner of the R0 scan block.
- Completion: local Aether commit; evidence `specs/autonomous-bug-remediation/evidence/ABR-323.md`; same-card review; `patch`; no push.

## ABR-284 — #284 brownfield `.worktrees/` ignore

- Source: contract In Scope #284; issue #284; this unit.
- Outcome: project initialization/binding ensures the native project-linked worktree root is ignored without requiring each product objective to commit a Hermes-specific rule. Idempotent; preserves unrelated `.gitignore` content; refuses rather than hiding an already tracked conflicting `.worktrees` path. Worktree create/remove still works.
- Inputs: independently reviewed P0 units.
- Boundaries: writable `src/aether_agents/commands/init.py`, `tests/test_project_init.py`. Do not change this repository's already-correct `/.worktrees/` rule except as a preservation control. Do not write `.git/info/exclude` as the product mechanism (that was bounded recovery evidence only).
- Judgement: append `/.worktrees/` in the existing ignore-policy helper vs a dedicated local-only ensure step; fail-closed when `.worktrees` is tracked.
- Verification: fresh brownfield init + first project-linked task leaves owner `git status` clean of `.worktrees/`; unrelated ignore rules preserved; tracked `.worktrees` refuses; re-run idempotent. `uv run --frozen python scripts/run_tests.py -- -q --tb=short tests/test_project_init.py`.
- Dependencies: P0 units (priority wave).
- Completion: local Aether commit; evidence `specs/autonomous-bug-remediation/evidence/ABR-284.md`; same-card review; `patch`; no push.

## ABR-346 — #346 PR impact/triage pagination and moving-head

- Source: contract In Scope #346; issue #346; this unit.
- Outcome: PR impact/triage uses bounded complete pagination with honest total/truncated state and verifies moving-head consistency at the existing analysis boundary. Stale or changing PR data is not silently presented as current. Zero-impact vs unavailable remains distinct. Failures do not masquerade as zero impact.
- Inputs: independently reviewed P1 units.
- Boundaries: writable `src/aether_agents/knowledge/github.py`, `tests/test_knowledge_regressions.py` (this unit exclusive), and schema tests only if new fields are already contract-shaped. Preserve Graphify worker native behavior except through existing `backend.run` arguments. Fixed read-only `gh` argv; no live mutation.
- Judgement: pagination mechanism (explicit page loop vs documented `gh` cap handling) as long as omitted files cannot be analyzed as a complete set. Retry-at-most-once on head movement then `GITHUB_UNAVAILABLE`.
- Verification: controlled >page, >analysis-cap, moving-head once (retry success), moving-head twice (unavailable), and a real read-only PR probe using already-provisioned `gh` against this public repository. Baseline vs candidate. `uv run --frozen python scripts/run_tests.py -- -q --tb=short tests/test_knowledge_regressions.py tests/test_knowledge_schema.py tests/test_graphify_worker_native.py`.
- Dependencies: P1 wave (priority), not a file dependency on P1.
- Completion: local Aether commit; evidence `specs/autonomous-bug-remediation/evidence/ABR-346.md`; same-card review; `patch`; no push.

## ABR-META — #306+#293 model metadata

- Source: contract In Scope #306 and #293; issues #306 #293; this unit.
- Outcome: (306) generic OpenAI-compatible gateway metadata is parsed by response shape rather than HTTP-200 LM Studio assumption; advertised `context_length` is preserved; existing true LM Studio behavior remains. (293) use gateway-advertised per-model context windows where the existing provider protocol exposes them; compatible fallback/override when metadata is unavailable; no guessed/silent routing widen. Excludes auxiliary Chat/Responses (#296) and title attribution (#303).
- Inputs: independently reviewed P1 units. Fork `28b593e`.
- Boundaries: writable fork `agent/model_metadata.py`, `tests/agent/test_model_metadata.py`, `tests/agent/test_model_metadata_local_ctx.py`, plus new focused tests. Preserve `auxiliary_client.py`.
- Judgement: validate LM Studio `models` array vs fall through to generic `data` parser when the LM Studio branch yields no models. Do not treat every `/api/v1/models` 200 as LM Studio.
- Verification: loopback HTTP 200 `/api/v1/models` with `{data:[{id, context_length}]}` is not empty; true LM Studio `{models:[...]}` still classified; missing metadata uses existing fallback/override. Distinct 306/293 dispositions. `HERMES_TEST_FILE_RETRIES=0 scripts/run_tests.sh` on owned tests.
- Dependencies: P1 wave. Concentrated because one writable hotspot file.
- Completion: local fork commit(s) keeping 306 and 293 inspectable; evidence `specs/autonomous-bug-remediation/evidence/ABR-META.md`; ledger paragraph for actual code corrections; same-card review; `patch` or mixed `patch`/`none`; no push.

## ABR-AUX — #296+#303 auxiliary client

- Source: contract In Scope #296 and #303; issues #296 #303; this unit.
- Outcome: (296) auxiliary requests support already configured Chat-only models through the existing compatible request path; Responses-only behavior remains intact; no new provider/protocol. (303) genuine Hermes title-generation fallback preserves existing auxiliary attribution through the activated profile path without leaking destination authentication. Excludes model_metadata (#306/#293).
- Inputs: independently reviewed P1 units. Fork `28b593e`. Do not edit live profile YAML under `home/`. Tracked Aether profile templates only if inspection proves attribution cannot be preserved on the Hermes request path without them; otherwise keep the fix in the fork client.
- Boundaries: writable fork `agent/auxiliary_client.py` and owned auxiliary tests (`tests/agent/test_auxiliary_client*.py`, extra_headers tests). Preserve `model_metadata.py`, `error_classifier.py`.
- Judgement: Chat payload negotiation vs a clear configuration error naming the surface mismatch — prefer the existing compatible request path if it already exists. Attribution via supported extra headers / preserved request metadata, never by forwarding destination auth.
- Verification: loopback Chat-only 400-directive vs Chat 200; Responses path unchanged. Fallback title_generation carries service/operation attribution without Authorization/Cookie/API-key copy. Distinct 296/303 dispositions. Fork runner, retries disabled.
- Dependencies: P1 wave. Concentrated because one writable hotspot file.
- Completion: local fork commit(s); evidence `specs/autonomous-bug-remediation/evidence/ABR-AUX.md`; ledger paragraph for actual code corrections; same-card review; `patch` or mixed; no push.

## ABR-275 — #275 local vision path

- Source: contract In Scope #275; issue #275; this unit.
- Outcome: valid local PNG input reaches the supported vision path without the observed generic Codex upstream HTTP 400, or an honest disposition if the defect is outside the permitted repositories. Preserve provider/auth boundaries.
- Inputs: independently reviewed P1 units. Resolve actual loaded vision tool source before editing.
- Boundaries: writable fork vision tool/tests only if the loaded source is `DarkArty07/aether-hermes` (`tests/tools/test_vision_*.py`, `tests/agent/test_vision_*.py`, and the producing module). If the defect is live runtime/config/outside permitted repos, deliver evidence and keep #275 open. No live paid vision traffic required when a local recorder/fixture can prove request shape; if it cannot, stop rather than using production credentials.
- Judgement: request-shape repair vs actionable unsupported-combination error. Do not guess provider internals.
- Verification: 1×1 PNG fixture (synthetic bytes from the issue, regenerated locally). Baseline vs candidate. If unreproducible on the verified fork SHA, not-reproduced evidence and leave open.
- Dependencies: P1 wave.
- Completion: local commit or evidence-only; evidence `specs/autonomous-bug-remediation/evidence/ABR-275.md`; same-card review; `patch` or `none`; no push.

## ABR-360 — #360 exact Hermes baseline checkout

- Source: contract In Scope #360; issue #360; this unit.
- Outcome: exact-baseline recreation either succeeds consistently across the supported Python matrix or retains enough bounded Git stderr to diagnose a transient checkout failure without exposing credentials. No baseline tag/commit change.
- Inputs: independently reviewed P2 units.
- Boundaries: writable `scripts/qualify_observation.py` (`checkout_exact` and Git-failure reporting). If `scripts/run_tests.py` duplicates the same checkout helper and is the other caller, this unit may make the two share behavior. Preserve Hermes baseline constants. Do not edit workflows to hide the job.
- Judgement: retry policy is not a fix; bounded stderr hashing vs retained sanitized Git diagnostics.
- Verification: reproduce checkout failure mode with a controlled git-stub or documented 3.12 log comparison; candidate either succeeds deterministically or records usable bounded diagnostics. Unchanged baseline constants. Aether wrapper on `tests/test_hermes_baseline.py` plus any new unit tests.
- Dependencies: P2 wave (priority). Exclusive `checkout_exact` owner.
- Completion: local Aether commit or honest environment disposition; evidence `specs/autonomous-bug-remediation/evidence/ABR-360.md`; same-card review; `patch` or `none`; no push.

## ABR-357 — #357 PluginContext harness

- Source: contract In Scope #357; issue #357; this unit.
- Outcome: identify whether `test_real_plugin_context_captures_tool_and_api_then_unloads_every_hook` failure is a product defect, a harness race, or environment-only. Correct only an in-scope deterministic defect. A pass on retry is not a fix.
- Inputs: independently reviewed P2 units.
- Boundaries: writable `tests/test_observation_qualification.py` and the observation plugin/harness module actually causing the failure. Do not edit `qualify_observation.py` checkout (ABR-360) or journal storage (ABR-329). Do not increase deadlines without diagnosis.
- Judgement: product unload/hook leak vs qualification wrapper. Controlled events/barriers, not sleep-as-ordering.
- Verification: unchanged-baseline reproduction attempt; if intermittent, capture first failure and distinguish cause. Candidate GREEN only for a demonstrated product fix. Aether wrapper on the named test plus neighbors.
- Dependencies: P2 wave. Independent files from ABR-360/ABR-329/ABR-352.
- Completion: local commit or open-with-evidence; evidence `specs/autonomous-bug-remediation/evidence/ABR-357.md`; same-card review; `patch` or `none`; no push.

## ABR-352 — #352 concurrent lifecycle timeout

- Source: contract In Scope #352; issue #352; this unit.
- Outcome: `test_two_process_transitions_with_one_expected_active_have_one_commit` either exposes and fixes a product synchronization defect or is an honest fixture-deadline/environment disposition. Do not increase deadlines or weaken assertions without diagnosis.
- Inputs: independently reviewed P2 units.
- Boundaries: writable `tests/test_observation_lifecycle.py` and `src/aether_agents/lifecycle.py` only if causal. Preserve unrelated lifecycle behavior. Do not edit journal storage.
- Judgement: queue timeout vs missing commit invariant. Use controlled events/barriers.
- Verification: unchanged targeted rerun plus a controlled interleaving that does not rely on wall-clock luck. Aether wrapper on the named test.
- Dependencies: P2 wave.
- Completion: local commit or open-with-evidence; evidence `specs/autonomous-bug-remediation/evidence/ABR-352.md`; same-card review; `patch` or `none`; no push.

## ABR-349 — #349 FTS search-projection trace

- Source: contract In Scope #349; issue #349; this unit.
- Outcome: `tests/test_hermes_state.py::TestFTS5Search::test_search_projection_skips_context_enrichment_queries` is reconciled on the maintained baseline: either the product/trace connection is corrected or the test is honestly shown wrong for current connection handling without hiding coverage. Do not skip or weaken to go green.
- Inputs: independently reviewed P2 units. Fork `28b593e`.
- Boundaries: writable fork `hermes_state_search.py` / related FTS modules and `tests/test_hermes_state.py` as needed. Preserve unrelated FTS holder/lease behavior. Do not edit `auxiliary_client.py` or `kanban_db.py`.
- Judgement: install callbacks on the connection actually used vs product query-path repair. Diagnosis hypothesis in the issue is not the fix.
- Verification: unchanged baseline RED (`assert 0 == 1` as reported) then candidate GREEN for the same test, or a documented not-product disposition with the issue left open. `HERMES_TEST_FILE_RETRIES=0 scripts/run_tests.sh tests/test_hermes_state.py`.
- Dependencies: P2 wave.
- Completion: local fork commit or open-with-evidence; evidence `specs/autonomous-bug-remediation/evidence/ABR-349.md`; ledger paragraph if product changed; same-card review; `patch` or `none`; no push.

## ABR-329 — #329 journal-storage concurrency

- Source: contract In Scope #329; issue #329; this unit.
- Outcome: journal-storage concurrency tests deterministically pass when the implementation is correct, or deterministically expose a real synchronization defect. A retry with unchanged code is not acceptance.
- Inputs: independently reviewed P2 units.
- Boundaries: writable `src/aether_agents/observation/storage.py` (and journal helpers if causal), `tests/test_observation_journal_storage.py`. Do not weaken the qualification gate. Do not edit PluginContext tests (ABR-357).
- Judgement: harness scheduling flake vs product fence. Controlled interleavings for `test_rebuild_waits_for_open_reader_before_publishing_candidate` and `test_checkpoint_sink_uses_only_fsynced_active_evidence_without_rotation`.
- Verification: reproduce timing/interleaving without relying on CI retry. Candidate either fixes a demonstrated product race or leaves the issue open with evidence. Aether wrapper on the named tests.
- Dependencies: P2 wave.
- Completion: local commit or open-with-evidence; evidence `specs/autonomous-bug-remediation/evidence/ABR-329.md`; same-card review; `patch` or `none`; no push.

## ABR-INT — Terminal integration and dual-repo closeout

- Source: contract Deliverables 4–7, Acceptance 1–8, Testing Standard closeout; this unit.
- Outcome: independently reviewed units integrated without squash/amend/rebase/force; fork PR to `aether-main` when fork commits exist; Aether PR to `main`; required Aether checks green; fork Actions reported NOT RUN if that is standing state; #366 and applicable issues reconciled from durable merged evidence; ledgers written; residue audit; aggregate release conclusions; Spanish milestone text from durable evidence for the existing monitor. No live activation or publication.
- Inputs: independently reviewed implementation units. Preserve each as its own commit. Commit this `tasks.md` if not already on the integrated branch.
- Boundaries: integration-owned conflict/import/wiring/path/`policy.yml` allowlist repairs that introduce no new behavior; `HERMES_LOCAL_PATCHES.md`; fork `AETHER_FORK.md`; `specs/autonomous-bug-remediation/evidence/` integrated report. Behavior gaps return as implementation rework.
- Verification: coverage matrix for all 18 issues; Aether documentation/policy/exact-Hermes gates; fork local runner with retries disabled where fork changed; git-github-closeout; separate source-integrated / runtime-activated / operationally-qualified gates (activation and publication omitted with reason).
- Dependencies: decomposition root and all independently reviewed implementation units.
- Completion: aggregate `release_impact=patch` only with compatibility evidence otherwise `none`; `release_action=defer`; `release_channel=none`. Local integration alone is not success.

## Authority and stop conditions

Follow the Objective Contract. Ordinary Supervisor/Implementer execution and routine Git/GitHub closeout in the two named repositories are authorized. Stop and return `needs-contract-revision` only for a genuine contract defect (different material cause, unsafe cross-destination auth, broader protocol/API, missing Project/board/repository identity, required live `home/` edit). Stop and return `needs-owner-input` only for genuine owner input. Protected denials are authoritative. Do not strand a finished phase awaiting a precreated review child; unit review is same-card. Preserve unrelated/pre-existing worktrees, branches, stashes and processes. Telegram delivery failure does not stop source work.
