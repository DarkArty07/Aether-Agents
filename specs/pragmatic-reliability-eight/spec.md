# Specification: pragmatic reliability closure

Status: contract design for `oc_c780a10d94b78d85`.

Owning issues: #357, #372, #385, #388, #393, #396, #397 and #399. Issue #403 is an incidental CI blocker, not a ninth product objective.

## Objective

Close eight demonstrated reliability failures with the smallest changes at their owning Aether or Hermes seam, independent review, integrated evidence and ordinary GitHub closeout. Reuse reviewed work already in progress instead of recreating it.

## Shared constraints

- The active `oc_291b2fb34b413d92@v2` execution remains the sole implementation lane for #396, #397 and #399 until its accepted commits reach `main`. This objective consumes those commits and evidence; it does not duplicate or race them.
- Hermes-owned fixes start from the verified maintained fork, not the dirty live checkout. Current upstream must be inspected first. Every downstream-only behavior receives portable patch/ledger evidence, a rollback and a retirement gate.
- Tests and probes use disposable state. They may not write to a live board, delete audit records, inject `PYTHONPATH` as a runtime repair, rewrite Git history or weaken a required check.
- A failing unrelated check is attributed. Only a defect that actively blocks this objective may be folded in, and then only as the smallest separately tracked unblocker.

## R357 — close the PluginContext recurrence causally or as demonstrated non-reproduction

The exact real PluginContext lane must execute on Python 3.11, 3.12 and 3.13 against the locked public Hermes baseline. A recurrence must retain the existing provenance-qualified, content-free diagnostic and drive a causal correction; retries, skips, timeouts and assertion weakening are not fixes.

If the named failure does not recur, no speculative product change is made. Under the owner's explicit autonomous/pragmatic closure authority, #357 may close as no longer reproducible only after the current integrated candidate and its post-merge `main` revision both show the exact harness passing on Python 3.13, with the historical failure and diagnostic limitation preserved. Failures elsewhere in the same workflow are reported separately and are not attributed to #357.

## R372 — one effective cron script root

Creation/update validation, lifecycle scanning, execution and user-facing diagnostics must resolve `script` and `monitor_script` through one effective profile-scoped script-root contract. Relative paths stay confined to the active `HERMES_HOME/scripts`; absolute, home-relative, traversal, symlink escape and non-regular targets fail closed. A create accepted for an existing script must execute that same file. Error text names the effective profile root rather than the default-profile shorthand.

## R385 — review topology cannot be mistaken for terminal integration

A first same-card review requires an explicit reviewer different from the implementer and fails before mutation otherwise. More importantly, worker guidance must not treat a terminal integration or release child alone as a substitute for unit review. Only an explicitly defined distinct review/QA child consumes `kanban_complete` as the implementation handoff; otherwise a unit requiring review uses `kanban_request_review`.

The already-present maintained-fork HLP-362 behavior is reconciled into portable patch/ledger evidence rather than reimplemented. The additional guidance correction is independently tested. Existing completed history is not rewritten and no prospective review is described as a past same-card verdict.

## R388 — contract authoring never falls back from an unbound session

A cron session with an explicit workdir persists or exposes that verified workdir as its session cwd. Independently, `objective_contract` fails before any draft/final/primary-checkout mutation when a non-empty native session identity has no valid Git workspace binding. It may not silently pass `authoring_root=None` and fall back to the registered Project primary checkout. Direct store uses that intentionally have no native session remain supported.

## R393 — cron-started work preserves a trusted exact return route

Creating a cron job from a TUI/desktop or gateway session captures a trusted durable notification origin separately from ordinary cron delivery. At fire time that origin is restored only to Kanban auto-subscription; it does not impersonate inbound authority, become a model-supplied session ID, leak through process-global environment or alter stateless cron delivery.

A root created by that cron run must report `subscribed=true`, persist exactly the originating TUI/gateway subscription, and wake that origin once on terminal flow. An unattached cron, CLI or test still creates no subscription. Wrong/stale origins fail closed and are surfaced in the creation receipt.

## R396 — observation follows the exact execution board

Consume the independently reviewed existing correction. A contract trace resolves its provisioned board from verified project UUID, contract/version, board metadata and root correlation; it never reads `default` as fallback. Root and descendant transitions update freshness and coverage while unrelated boards remain untouched and raw content remains absent.

## R397 — write-capable probes are isolated before first write

Consume the existing correction after its Monitor prerequisite. Any Aether-owned writer probe scrubs inherited board/session/task identity, pins disposable roots and verifies the loaded writer resolves those roots before its first mutation. A mismatch refuses. Live-board byte/row canaries remain stable, and SQL deletion is never cleanup.

## R399 — editable mappings are reconciled transactionally

Consume the existing correction. A supported product-owned entry point reconciles explicit verified Hermes source and explicit interpreters as one transaction, backs up generated metadata, uses local no-dependency reinstall, rolls back prior interpreter updates on a later failure and verifies every intended top-level module under `python -I` without `PYTHONPATH`. Source bytes and dirty status remain unchanged; an internal module left unwired is not accepted.

## B403 — minimum blocking CI reconciliation

The historical contract implicated by #403 must leave the current public artifact surface without operator-local path or destination data while preserving an auditable locator and original digest. Do not weaken the scanner, exempt all contracts or rewrite Git history. Prefer removal from the current artifact set plus a portable redaction/tombstone receipt over rewriting the finalized bytes in place. This is accepted only as the minimum action that returns the public-artifact check to green.

## Aggregate acceptance

All eight issues have issue-specific evidence at the exact integrated revision; #403 has separate blocker evidence. Required PR checks pass without bypass. Post-merge checks distinguish the exact #357 harness from other jobs. Runtime activation uses the reviewed maintained-fork revision and Aether revision at a worker-safe boundary, followed by focused #372/#385/#388/#393 canaries and the #396/#397/#399 canaries or accepted equivalent evidence. Close only the issue whose criterion passed; an independently blocked issue stays open without stopping healthy units.
