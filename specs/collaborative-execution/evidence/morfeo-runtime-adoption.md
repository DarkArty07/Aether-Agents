# Morfeo runtime adoption — direct operational handoff

## Authority and current state

The owner explicitly asked Morfeo to finish the bounded runtime adoption and operational closeout directly, rather than have Supervisor restart its own parent gateway. Supervisor CE-INT is parked; the separate accidentally duplicated recovery lane was also asked to stop expanding work. No product implementation is taken over here.

**Adoption state:** completed at `2026-09-14T05:22:44Z`. After the initial zero-worker wait, the owner explicitly authorized an abrupt restart, overriding the wait requirement for this one maintenance action. The service was stopped, the reviewed/reconciled sources and resources were adopted, installed checks passed, and the gateway restarted with a new process. CE-11 is now directly supported; CE-12 issue/residue closeout is recorded separately, not inferred from this receipt.

The cutover ran outside the gateway. It recorded the owner's explicit interruption authority, paused new work natively, rechecked preimage hashes, stopped the service, installed reconciled sources/resources, re-ran native tests against installed bytes, verified isolated interpreter/optional tool-argument loading, started a new service process and lifted its own pause. The owner's latest instruction authorized interrupting the two active jobs; it did not authorize discarding their persisted work, resetting usage counters or changing acceptance. No unrelated configuration/source was overwritten. The prior finite wait process was ended before the authorized cutover; rollback images remain retained.

## Exact reviewed inputs

- Aether PR #427 merge: `20f0d72e66f305fb68c3707460412f89bce5c780`.
- Maintained Hermes PR #11 merge: `bb5e9a422f3135371557e75bcd1db01c5f8fc3ba`.
- Native patch base: `3b81e9d91cc3a0662b910726a44c94ed328b1e90`.
- Previous Aether runtime: `de0a96826eae4022659aee9d943421e3226ec924`.
- Finalized contract remains `oc_a28ff9b7fa20d29d@v1`; D5 clarification is included in the merged plan.

## Preservation and bounded reconciliation

The live editable Hermes has pre-existing local changes; replacing it with the fork tree would discard them. Morfeo took private per-file rollback images and recorded every existing dirty/untracked source hash and role-config hash before constructing a disposable reconstruction.

Only four native production files are adopted: `hermes_cli/kanban_db.py`, `tools/kanban_tools.py`, `gateway/kanban_watchers.py`, and `tui_gateway/server.py`. Thirteen existing managed role resources are updated; reception skills absent from execution-only profiles are not newly installed. The package retains all canonical resources. This preserves the configured skill sets, profile configuration, credentials and unrelated source changes.

Two mechanical adaptation points are explicit, not hidden in a wholesale copy:

1. Preserve the installed blocked-parent recovery wording in the `else` branch of the reviewed new advisory-versus-recovery block.
2. Map the incoming `target_board` reference to the installed handler's already selected `board` variable at the new opt-in call. The unreconciled copy raised a `NameError` in the disposable test run; it was not installed.

The gateway/TUI files match the reviewed fork bytes exactly. The other two are compositions of the preserved live preimage and the reviewed addition plus those mechanical adaptations. Their exact private preimage/candidate digests and rollback manifests are retained.

For resources, exact historical canonical copies were identified and refreshed, including missing isolation guidance in older copies. Morfeo's existing local truncation-workaround note was preserved alongside the new canonical design-procedure text rather than silently removed. No private note was promoted into product authority.

## Direct verification by Morfeo

All native tests below used freshly isolated HOME/XDG/Hermes state with no inherited live board/task/run selector and controlled delivery sinks. Existing provisioned interpreters were used; no package installation or new provider/model request was performed.

| Check | Result | Limit |
| --- | --- | --- |
| Four collaboration test files on the reconciled live-source reconstruction | **53 passed** | Disposable native DB/API/consumers, no live Telegram/model canary |
| Adjacent tool/affinity/review-readiness/review-independence/worker-stop tests | **101 passed** | Same reconstruction; not a full Hermes rerun |
| Positive import receipt | All four modules resolve inside the exact reconstruction | Explicit nonempty receipt; not assumed from PYTHONPATH alone |
| Merged Aether resource/result-review/documentation/patch-reconciliation tests | **56 passed** | Resource/mechanical checks, not behavior or installed-session adoption |
| Native preimage/resource/config preservation checks | Passed before arming the cutover | Rechecked immediately before mutation; concurrent changes abort |
| Four collaboration test files against actual installed module paths | **53 passed** | Disposable state and fake delivery sinks; no live model campaign |
| Production interpreter with `-I`, without `PYTHONPATH` | All five native/Aether paths resolve to the installed trees; collaboration helpers and create/comment optional arguments present | New-process loader/registry evidence, not a cached TUI refresh |
| Installed resource/native fingerprints and unrelated-config preservation | Four native files and 13 role resources match the recorded adopted hashes; other recorded source and profile-config hashes preserved | One pre-existing local procedure overlay retained explicitly |
| Restart readiness | New gateway process active/running; Telegram connected; native pause absent | No claim of long-term uptime or agent obedience |
| Interrupted-task continuation | Both the unrelated Aether unit and Asclepio campaign obtained new native runs/processes on the same cards | A task relaunch is not proof that every interrupted model call or interview resumed at the exact instruction |

The first native test attempt used the production interpreter without the async test plugin; those async failures were a test-environment limitation, not product evidence. The existing candidate development interpreter supplied that test plugin for the passing reconstruction. The live production interpreter is separately checked with isolated import resolution at adoption. No plausible output was substituted for a failed run.

## CI precision

GitHub required-check configuration was read directly: `pull-request-target` and `policy (3.11/3.12/3.13)`. All four passed on PR #427 before its normal merge. The three **non-required** `observation-qualification` jobs finished red, not pending/green. Their failed run is `34804365459`; failures occur before the coverage floor and include the editable-installer and same-card predicate test files, unchanged by this PR. This is not automatically the same defect as #412 and is not repaired by this adoption. No check bypass or repository-settings mutation was performed.

## Remaining acceptance

CE-01..10 have the existing attributed implementation/review/integration evidence in CE-HF-CORE, CE-HF-DELIVER, CE-AE-RES, CE-AE-DOCS and CE-INT, with the direct reconstruction/installed checks above. CE-11 is directly verified by Morfeo. CE-12 still needs the resulting operational handoff, objective-owned residue audit and issue reconciliation. A complete board or source merge alone is not acceptance. Non-required CI failures are tracked separately in #428 and are not reported as PASS.

Existing cached TUI sessions are not forcibly restarted or described as upgraded. New process/session loading, mechanical delivery tests, and long-term agent collaboration remain distinct conclusions. The owner expressly accepted unverified long-term efficacy; there is no organic/non-recurrence PASS and no Telegram Monitor reactivation.

`release_impact = minor`; `release_action = defer`; `release_channel = none`.
