# Research: eight reliability issues

This record distinguishes directly inspected evidence from delegated design suggestions. Exact source and current issue/CI evidence outrank delegated summaries.

## Directly verified evidence

### Existing work

`oc_291b2fb34b413d92@v2` already owns #396/#397/#399. Durable board inspection found completed #396 and #399 candidates, #397 blocked on the active Monitor prerequisite, and a dependency-gated terminal integration. Starting a second implementation of those issues would create collision without adding review value.

### Hermes source boundary

Current upstream Hermes and the maintained Aether fork were freshly cloned and inspected at the revisions named in `plan.md`. Upstream still permits first-review `reviewer=None`; the maintained fork rejects a missing or same-as-implementer reviewer before mutation. The Aether ledger names HLP-362 but current `main` lacks its detailed portable patch artifact/reconciliation entry, while an Aether regression test expects the downstream behavior from the exact unpatched upstream baseline. This is the current three-version CI failure associated with review.

Cron script validation and execution both intend profile-scoped `HERMES_HOME/scripts`, but the creation error still instructs users to place files under the default `~/.hermes/scripts` shorthand and does not establish that the accepted filename is the runtime file. The issue reproduction shows a create accepted after following that message and a fire-time lookup under the active profile.

Cron captures gateway delivery origin, while a TUI has only a durable `HERMES_SESSION_KEY`; `_maybe_auto_subscribe` intentionally treats unattached cron as no-channel. Scheduler isolation clears inbound routing. Therefore Telegram delivery success cannot create the missing TUI Kanban subscription. The safe seam is trusted persisted commissioning metadata restored only as request-local subscription context.

### Aether authoring boundary

`src/aether_agents/objective_contracts/hermes_plugin.py::_native_session_workspace` returns `None` for a missing row, NULL/empty cwd, invalid directory or non-Git directory. The caller constructs `ObjectiveContractStore(authoring_root=None)`, allowing normal Project-primary fallback. The #388 incident demonstrates that this path wrote finalized bytes into an occupied unrelated checkout. A valid native session must therefore fail before constructing a mutating store when its workspace is unresolved.

### #357 current state

Historical #357 failures named only the exact PluginContext test and retained content-free line hashes. The already-merged diagnostic work added provenance-qualified phase/class/source/runtime reporting without exposing raw output and repeatedly failed to reproduce the recurrence locally.

On Aether `main` run `34579592766`, the exact qualification succeeded independently under Python 3.11, 3.12 and 3.13. The Python 3.13 result records 453/453 core tests, one real PluginContext harness pass, 22 callbacks, zero hooks after unload, tool/API capture and raw-payload absence. The later full-suite step failed for #403 and the unadopted HLP-362 test, not for #357. This supports a no-speculative-change disposition, subject to one final integrated/post-merge recurrence check.

### Incidental findings

Issue #403 was filed immediately with current run evidence. The current public-artifact scan rejects a pre-validator finalized contract containing an operator-local path; #364 fixed future validation but intentionally left this historical artifact unresolved. The smallest non-bypass correction is to remove unsafe bytes from the current artifact set while retaining an auditable tombstone and the original immutable Git object in history.

Issue #404 records a separate recurrence of #310: after the delegated design batch, the parent terminal retained delegated-child/Kanban identity. Seven contract tests were correctly denied by the Hermes guard; the identical controlled run passed 66/66 after the already-required environment scrub. This is reported but not absorbed because it does not block the eight-issue objective.

## Delegated design method

Six independent read-only design investigations were dispatched: #399; #397/#385; #396; #393; #388/#372; and #357. All six completed. Morfeo checked their material claims against current issue bodies, source, tests, CI and board state before incorporating them; they do not independently widen scope or authority.

The useful consensus was: retain the existing #396/#397/#399 candidates but verify exact integration; #399 still needs supported wiring, not another core; isolate writers before import/first write without changing production precedence; preserve a cron commissioning origin as a narrow trusted subscription capability; persist cron workdir at the session-creation seam and also fail closed in the Aether plugin; reconcile HLP-362 while correcting the generic child/review guidance; and close #357 without speculative code only after an unretried final 3.13 pass. The #388/#372 investigation correctly found related context drift but two distinct roots, so the design shares an execution lane without pretending they are one defect.

## Rejected approaches

- Reimplementing #396/#397/#399 in this contract.
- Treating Telegram cron delivery as proof of TUI wake routing.
- Passing a model-supplied session ID or restoring all inbound cron environment variables.
- Fixing #372 by copying every script into both default and profile roots.
- Fixing #388 only by moving already-written contract bytes after the fact.
- Marking a done Implementer card as historically reviewed or reopening it with SQL.
- Fixing #357 with retry, skip, timeout increase or speculative concurrency changes.
- Making the public-artifact scanner ignore finalized contracts or rewriting Git history for #403.
- Editing, resetting or cleaning the dirty live Hermes checkout as an implementation base.
