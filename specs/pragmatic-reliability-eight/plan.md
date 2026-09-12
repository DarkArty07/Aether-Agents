# Technical plan: pragmatic reliability closure

## Verified starting point

- Aether contract base: `466ee72cbbc984cbeec48ad929e84eeaa4d24f87`.
- Maintained Hermes fork inspected at `6551b7c31cc665d59103c6d89cb5e0c60666f803`.
- Current upstream Hermes inspected at `31d0a2428e9db346d6781da66f5b37ff3e12def2`.
- The live installed checkout is evidence only: it is behind the maintained fork and contains unrelated dirty work. No unit edits or resets it.
- Existing residual contract `oc_291b2fb34b413d92@v2` already owns #396/#397/#399. Its #396 and #399 candidates are complete; #397 is gated on the active Monitor flow; terminal integration has not completed.

## D1 — reuse before building

Supervisor first verifies whether `oc_291b2fb34b413d92@v2` has merged #396/#397/#399 to `main`. It never recreates those implementations. If not merged, independent work on the other issues continues, while final integration waits for exact reviewed commits/evidence. A stale board summary is not acceptance: inspect the candidate revisions and issue canaries.

## D2 — execution graph that cannot reproduce #385

Until the #385 guidance fix is activated, use explicit two-card implementation/review lanes:

1. Implementer card produces one candidate and calls `kanban_complete` only because its named child is an explicit independent review card.
2. Supervisor review child inspects the exact candidate and either requests bounded rework through a new linked continuation or completes with a verdict.
3. The terminal integration card depends on review cards, not directly on unreviewed implementation cards.

Do not pre-create a terminal child directly under an implementation card and then rely on the currently ambiguous generic prompt. After activation, a disposable organic canary verifies that a unit with only a terminal integration child still requests same-card review before completion.

## D3 — coherent work units

### U-CRON — #372, framework side of #388, and #393

These three issues share cron creation/execution context and would collide if split by file. Implement them serially in one maintained-fork lane while retaining separate tests and patch-ledger attribution.

- Factor or reuse one script-path resolver used by API validation, lifecycle guard and scheduler execution. Resolve the effective profile home at call time; avoid import-time/default-home capture. Creation validates the exact file that execution will read.
- Persist a cron job's trusted commissioning origin separately from `deliver`. Capture TUI durable session key and optional live UI id from request context; gateway origins retain their full stable route. At fire time install a request-local notification-origin context around tool execution. `kanban_create` may consume it only when ordinary inbound session routing is intentionally absent. Never expose a model argument for session IDs.
- Preserve the scheduler's context-local effective workdir and make `run_agent._launch_cwd_for_session("cron")` persist that trusted value in the session row before tools run. Preserve null cwd for jobs with no workdir rather than inventing one.
- Keep stateless delivery semantics: local TUI cron output still is not a messaging delivery channel; the new route is solely for descendant Kanban terminal notification/wake.

Upstream equivalence must be checked per sub-behavior. Produce maintained-fork commits/tests and portable Aether patch/ledger entries with independent retirement gates. Do not make the feature depend on the dirty live checkout.

### U-CONTRACT — #388 Aether fail-closed boundary

Change `_native_session_workspace`/plugin construction so a non-empty native authoring session that cannot resolve a valid registered Git workspace returns a stable contract error before store construction or mutation. Do not change `ObjectiveContractStore` semantics for direct, intentionally sessionless use. Regression fixtures cover missing row, NULL/empty cwd, nonexistent cwd, non-Git cwd, unrelated project/worktree and a valid linked worktree. Assert zero primary/draft/final changes for every negative.

### U-REVIEW — #385 and maintained-fork HLP-362 reconciliation

- Preserve the maintained-fork invariant already present: first review requires an explicit canonical reviewer different from implementer; malformed re-review provenance fails closed.
- Correct `KANBAN_GUIDANCE`: a terminal/release/integration child alone does not replace same-card review; only a child explicitly identified as the candidate's review/QA phase does. Explicit card delivery remains authoritative.
- Export/reconstruct exact portable patch evidence for HLP-362 and the #385 prompt correction; add detailed ledger entries and retirement tests. The Aether test suite must not falsely expect an unpatched upstream baseline to provide downstream behavior. Test the patch against a disposable authenticated baseline/fork candidate instead.
- Preserve original FU-352 history; its prior prospective review remains correctly labelled as recovery evidence.

### U-CI — #357 disposition and #403 blocker

- Re-run the exact real PluginContext qualification on the integrated candidate under Python 3.11/3.12/3.13. If it passes, retain current diagnostics and make no #357 product change. If it fails, use the retained phase/class/source/runtime to reproduce and correct the smallest causal seam before proceeding.
- Reconcile #403 without changing a finalized contract's historical Git object and without scanner exemption. Remove the unsafe historical file from the current public artifact set and add a portable tombstone/redaction receipt containing the original digest, historical commit locator, reason and superseding safe locator; remove any separately exposed destination data. Update references that require a current-tree locator. Verify the scanner and contract-history documentation.

## D4 — integration and activation

1. Integrate only independently reviewed commits into an integration branch based on current `origin/main`; normal merges only, no rebase/squash/history rewrite.
2. Incorporate accepted #396/#397/#399 commits from their owning pipeline once available. For #399, verify that terminal integration exposes the candidate through a supported Aether operation; its currently completed core unit explicitly deferred wiring. Resolve semantic conflicts with the owning unit; do not copy partial worktree bytes.
3. Run focused gates, the maintained-fork suites and the full Aether matrix. Fix only issue-causal regressions or #403 as the recorded blocker.
4. Push one coherent Aether PR and the necessary maintained-fork PR(s), wait for required checks and merge normally. Cross-repository order is fork candidate first, Aether patch evidence/pinning second.
5. Activate exact reviewed Aether/fork revisions at a worker-safe boundary. Refresh editable mappings only through the accepted #399 operation; restart only if changed loaded modules require it.
6. Run runtime canaries. Close each issue with its evidence; keep any failed issue open. Update project knowledge/work memory if available.
7. Remove only objective-owned merged branches/worktrees and temporary canaries. Preserve unrelated worktrees, stashes, active Monitor state and unmerged evidence.

## Compatibility and release

`release_impact=patch`; `release_action=defer`; `release_channel=none`. These fixes change defect behavior and internal reliability contracts but do not authorize package publication or a release.
