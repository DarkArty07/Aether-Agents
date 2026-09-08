# Approved runtime reliability corrections

**Owner approval:** 2026-09-08, current Morfeo conversation: the owner approved the six presented designs, the three subsequent qualifications, and autonomous execution. Approval does not activate the live runtime.

**Objective:** implement or evidence-qualify only Aether issues [#267](https://github.com/DarkArty07/Aether-Agents/issues/267), [#292](https://github.com/DarkArty07/Aether-Agents/issues/292), [#294](https://github.com/DarkArty07/Aether-Agents/issues/294), [#295](https://github.com/DarkArty07/Aether-Agents/issues/295), [#301](https://github.com/DarkArty07/Aether-Agents/issues/301) and [#304](https://github.com/DarkArty07/Aether-Agents/issues/304). These existing issues are the canonical intake records; a duplicate umbrella Issue is not applicable.

The [plan](plan.md) owns technical decisions and preservation; [quickstart](quickstart.md) owns verification. Supervisor owns decomposition and `tasks.md`, independent review, integrated evidence and closeout. No implementation units are authored by Morfeo.

## Authority and preservation

The [R0 constitution](../r0-design-governance/spec.md#4-r0-constitution) is confirmed unchanged: owner authority, specification-owned intent, bounded autonomy, traceable evidence, simplicity and separation of design/build/activation. No new project principle is inferred from a personal preference.

The current owner's maintained-fork decision in [DESIGN.md](../../DESIGN.md) governs this scoped downstream implementation over obsolete transitional/upstream-only guidance. Global fork packaging, release-lock migration and documentation reconciliation belong to #348/#261 and are excluded. Root `AGENTS.md` already exists and remains the operating guide; no generic replacement is warranted. Root names product-discovered canonical skills, and no `.aether/skills/` project override directory exists at intake. Applicable procedures: objective-contract-design, supervisor-decomposition, implementation-evidence, git-github-closeout, semver-release and canonical-skill-governance; procedures grant no authority.

Permitted repositories: Aether-Agents default `main` and the already provisioned maintained `DarkArty07/aether-hermes` default `aether-main`. Build in isolated managed checkouts; preserve their current baselines and all unrelated downstream changes. The editable runtime is read-only evidence, never the implementation target. No Graphify, knowledge/memory feature, other bug, live profile, model/provider selection, credential, live database or dispatcher configuration changes are authorized. No new endpoints, live model expenditure, upstream-wide update, package publication, tag/release, production restart, schema migration or destructive state cleanup. Normal branch pushes, reviewed PRs, non-rewriting merges, issue reconciliation and cleanup of this objective's proven merged resources are authorized with existing access and checks. Preserve unrelated/pre-existing worktrees, branches, stashes and processes.

## Observable requirements

### B267 — disposable probes must not escape their laboratory

Use the existing `isolated_hermes_env()` entry boundary, not another test runner or a global board-selection policy. Before native imports or subprocess launch, discard inherited worker/session/project/tenant/delegated-child identity, then explicitly assign the disposable home, database, workspaces and XDG roots. Enforce this on each executable disposable-probe entry point within the affected Aether laboratory lane; a Python helper not used by the real entry point is insufficient. Verify the resolved database/workspace destinations before test writes; reject an escaped destination without writes. Do not mutate the parent environment.

Acceptance: a subprocess started with deliberately poisoned identities uses only its disposable board. A separate disposable witness board and its rows/events remain unchanged. At least one real native create/claim/complete path runs against the laboratory DB. No production board access, external dispatch or historical residue cleanup is part of the test. Positive controls preserve unrelated configuration. Add direct assertions for cleared project/tenant/delegation markers; do not reinterpret the existing production `HERMES_KANBAN_DB` precedence.

### B304 — a durable same-run completion must not cause impossible retries

Keep the transcript receipt fast path and fail-closed conflict behavior. Only when transcript assessment is `MISSING`, read existing completion evidence from the exact worker board using the already captured expected task/run identity. The receipt must prove the assigned execution, not merely a currently `done` task. Permit the worker to exit without another transition when that evidence is valid. Do not invent a receipt, rewrite a task, reopen/recomplete it, weaken `expected_run_id`, create a schema or alter lifecycle tools.

Acceptance: a claimed task completes durably; with its call/result absent from conversation, stop validation allows exit. No extra events, runs, rows or notifications are written. Wrong board, task, run, mismatched event or contradictory transcript is rejected. Missing/unreadable evidence yields a bounded technical outcome using existing stop-budget semantics, never an unbounded retry or false success. Existing review/block/rework lifecycle semantics remain unchanged; this recovery is scoped to proven successful completion.

### B295 — explicit exhausted pool uses only an authorized fallback

Before generic `503` overload handling, recognize the reported explicit exhaustion condition and request the already configured fallback without exhausting same-pool retries. Keep ordinary transient overload, context overflow, holder/authority failures and other existing error classes unchanged. An ambiguous or empty `503` body is not proof of permanent pool exhaustion. No automatic discovery or undeclared provider is permitted as the result of this classification. If no authorized alternative works, return a bounded honest failure. Preserve partial-stream and already-executed tool-effect protections.

Acceptance: real loopback HTTP supplies a deterministic exhausted-pool response followed by a successful configured secondary. Capture request destinations/counts, authentication separation and final response. Generic overload still uses existing backoff; no configured secondary and all-candidates-fail controls end visibly without widening routing. Successful tool side effects are not repeated merely to change providers.

### B301 — preserve request attribution without leaking authentication

Port only the relevant upstream `extra_headers` forwarding behavior into the existing Responses adapter. Qualify the complete sync/async, streaming/non-streaming, retry and configured-fallback routes actually used by auxiliary calls. Forward only request-scoped attribution/correlation/other destination-independent headers allowed by existing semantics. Destination authentication and provider-specific defaults must be resolved by the destination client. Do not forward a primary Authorization, proxy authorization, cookie, API-key or provider-specific auth header to another destination. Do not invent new attribution headers or providers.

Acceptance: actual SDK/adapter traffic reaches a local HTTP recorder with the expected per-request attribution in primary and secondary paths. Input mappings and client defaults are not mutated; a subsequent independent request has no stale attribution. The secondary receives its own fake destination credential, never the primary's. Tests cover the fallback caller as well as the adapter; a two-line adapter patch alone is not evidence of end-to-end correctness.

### B292 — qualify named-custom resolution before changing it

Verify a configured `custom:<name>` entry and its admitted bare-name form through the real resolver and configured-fallback route, with a bare model, entry-specific endpoint, `key_env` and `api_mode`. Reuse the named-provider resolver rather than copying connection configuration into every fallback or introducing another routing abstraction. Preserve supported anonymous custom and built-in routes. Only repair a reproduced loss of this named identity on the approved path.

Acceptance: temporary configuration, synthetic distinct credentials and local endpoints prove both spellings use the intended named endpoint/credential/mode in direct and fallback calls. No unrelated global credential is chosen. Source inspection or a normalization-function test alone cannot close the issue. If all integrated controls already pass on the exact maintained baseline, deliver the regression/evidence and reconcile #292 as already working without a speculative implementation patch.

### B294 — reproduce interruption ownership before selecting a repair

The reviewer already creates another `AIAgent`; a `bg-review` log line identifies an executing thread, not the origin of the interruption. Qualify these controlled interleavings: cancellation before thread start/admission, a new foreground turn while the review is in a blocked HTTP call, review completion racing the next review, and intentional `/stop` propagation. Use instance/request ownership assertions and deterministic events/barriers, not log timestamp correlation or sleep-based races. Preserve the review feature, cache prefix, session ID policy, foreground responsiveness and intentional stop/reset behavior.

If these tests reproduce the proposed lifecycle race, adapt the minimal existing upstream run-token/admission/identity-qualified-cleanup behavior described in the plan. If they do not reproduce a defect on the selected baseline, commit useful regression evidence and leave #294 explicitly open as `not reproduced on the qualified baseline`; do not call the historical incident fixed. This is an approved conditional qualification disposition, not evidence that a patch exists. A newly identified different interruption cause needs a material design return to Morfeo, not generalized hardening or a change to unrelated lease/monitor code.

## Common acceptance and closeout

- Every behavior above has a per-issue result: reproduced-and-fixed, already-working-with-integrated-evidence, or the specifically allowed B294 not-reproduced disposition. Unexecuted or failed required checks are never represented as success.
- Every actual code correction has an unchanged-baseline RED and candidate GREEN, affected-suite results and an independent review. Tests-only already-working dispositions show identical baseline/candidate behavior honestly.
- Test real imports/processes/SQLite/HTTP under temporary state; mocked unit tests supplement but do not replace integration. No production model, credentials or DB are used.
- Preserve unrelated behavior and downstream patches. Required Aether GitHub checks remain enabled and must pass; inherited fork Actions are disabled at intake and must be reported as not run, not green. Use the fork's documented local runner and independent review without changing repository settings.
- Integrate through each repository's normal non-rewriting PR path. Record exact integrated commit(s), checks, review, issue disposition and residue audit in the evidence. Aether's integration ledger references the exact merged fork commit. An open PR or local merge is not objective closeout.
- Anticipated `release_impact=patch` for compatible bug corrections; `release_action=defer`, `release_channel=none`. No version bump/publication/activation follows from merging. If compatibility evidence contradicts patch impact, stop that change for Morfeo rather than inventing a release decision.

Supervisor produces the task coverage and independent review receipts after handoff. This document is not a claim that either already exists.
