# FBUG-INT — four-bug integration and closeout evidence

## Scope and receipt

This report executes terminal unit FBUG-INT from Objective Contract
`oc_7a35eca6393f18a7@v1`, SHA-256
`1478ba06eedd98ccea156f320c432dcc9c1ee9ad9f0149b3883b56d98b6ea6c3`.
The graph covers #354, #369, #357 and #352; #275 is excluded and was not changed.

The terminal consumed these independently approved revisions:

| Unit | Accepted revision | Review evidence | Compatibility |
| --- | --- | --- | --- |
| FU-354 | `d09c5747bc942c262c08d8103ddfb0a3c506b0d8` | same-card Supervisor approval after two review rounds | `none` |
| FU-369 | Aether `122829b47b25bdd1884e881412bb1bc0fc85eaed`; fork `8b600f3bf508326cd8defdb9da03757b838619b7` | same-card Supervisor approval after two review rounds | `patch` |
| FU-357 | `2169f73d7bcd728b27c625056ce9a56892f65246` | same-card Supervisor approval after two review rounds | `patch` |
| FU-352 | candidate `83ad2a50a37b54ec5cdf78d4fbc05f197d51f295`, review evidence `ab4eaa84bb4c8543e448135b6ccb7810f505c2dc` | prospective independent Supervisor continuation `t_456a4924`, preserving the original completed history | `none` |

FU-352's Implementer had completed its card without the required review transition.
Terminal integration stopped. Morfeo then linked the native review continuation as an
explicit prerequisite; it approved the exact candidate without rewriting or relabelling
history. Issue #385 tracks that separate routing defect.

## Integration provenance

The Aether branch first merged current `origin/main` without rewriting history, then
preserved each accepted unit as a distinct merge in contract priority order:

- `383982b84fb6813b99073bcbbf25104a900e59c0` — FU-354;
- `b3bcf1ad363256511af21b7ecafdff03e615da6d` — FU-369 Aether reconciliation;
- `8bb940c4bf12932e763bb1de8c57efb3f2bb29a4` — FU-357;
- `1900977d8cd29a320bab4c571d77b7b6d237e719` — independently reviewed FU-352 evidence.

No squash, amend, rebase, force operation or history rewrite occurred. The integration
repair `b259afc` added only the terminal-owned HLP-369 ledger/reconciliation facts.

## Maintained-fork closeout

`DarkArty07/aether-hermes` PR #6 merged normally to `aether-main` as
`415056fee527c5a2302370bd6dba56f84b9a4202`. The merge preserves the three reviewed
behavior/test commits and the fork-ledger commit. The PR was mergeable and clean; the
fork has no branch protection and inherited Actions are disabled. Its check rollup was
empty, so Actions are **NOT RUN**, not green.

The Aether ledger pins that merge and portable patch
`patches/hermes/HLP-369-goal-mode-review-recovery.patch`, SHA-256
`f90b2264fdf60a7b5da6476967366e7b5bd5d40acfc25ab7095ddfccb7f7ac1c`.
The detailed HLP-369 entry now joins the aggregate reconciliation snapshot. Exact
aggregate upstream `4f22543509d1b91dc45bcb369447126c5eb14fb7` and the newer unit
comparison `6e07eb48387044dbcaf12490931c2b8ca7ec8653` both lack equivalent behavior.

## Integrated acceptance

All results below were executed from the integrated source unless noted otherwise.
Operator paths and private environment values are deliberately omitted.

| Obligation | Command or lane | Observed result |
| --- | --- | --- |
| FU-354 real resolver lineage | canonical wrapper, `tests/test_objective_contracts.py -k reconstructed_maintained_resolver`, with the exact maintained source available | `1 passed, 39 deselected`; root/descendant ancestry, contract digest, unrelated-lineage absence and preservation oracles passed |
| FU-369 actual merged fork | four focused CLI/tool/review/session-affinity modules at fork merge `415056fee` | `97 passed`; complete-to-review, incomplete rejection, reviewer/re-review, whole-goal completion, exact recovery-origin, and arbitrary-block controls passed |
| FU-357 structured/privacy controls | full `tests/test_observation_qualification.py` | `60 passed, 1` documented Python-3.11-only benchmark skip |
| FU-357 exact runtime matrix | `qualify_observation.py test` against public Hermes `v2026.8.18` / `e624e9f` using verified CPython 3.11.15, 3.12.13 and 3.13.15 binaries | `453/453` passed on each; tool/API events captured, callback count 22, unload count 0, raw payload absent |
| FU-357 repeated Python 3.13 harness | ten fresh canonical-wrapper processes of the named real PluginContext node | `10/10` passed; no causal recurrence reproduced |
| FU-352 interleaving repetitions | exact spawned-process node in four sequential and eight bounded-concurrent fresh wrappers | `4/4` and `8/8` passed |
| FU-352 affected module | full `tests/test_observation_lifecycle.py` | `90 passed`; existing 10-second deadlines and exact one-commit/CAS/journal assertions unchanged |
| Cross-unit focused set | reconciliation, documentation, contract-quality, Objective Contract and Project-init modules | `111 passed` |
| Active reconciliation | deterministic validator against exact aggregate upstream snapshot | passed; HLP-369 digest and detailed-ledger coverage included |
| Aether full canonical runner | `uv run --frozen python scripts/run_tests.py` | `1171 passed, 64 skipped, 2 failed` |
| Type/syntax/docs/drift | MyPy over 53 source files, compileall, documentation validator, exact-Hermes drift check | passed |
| Build | `uv build` | wheel and source distribution built successfully for unchanged version `0.24.0` |
| Diff | `git diff --check origin/main..HEAD` | passed |

The two Aether full-run failures are retained known baselines, not called green:

1. `test_public_artifacts.py::test_tracked_public_surface_contains_no_operator_paths`
   reports only the immutable historical `oc_0084270d940c98d9@v1` findings. This
   objective neither changes nor exempts that contract.
2. `test_same_card_phase_predicates.py::test_initial_review_requires_an_independent_reviewer`
   is intentionally RED against selected public Hermes `v2026.8.18`; the maintained-fork
   review ownership and FU-369 matrices pass.

Whole-tree Ruff reports seven pre-existing findings in knowledge semantics and earlier
Objective Contract tests. Whole-tree format reports four pre-existing files. Focused
Ruff/format checks for the newly changed reconciliation and FU-357 sources pass; the
FU-354 reviewer independently located its existing-file findings outside the added
canary. Public-artifact validation reports only the historical contract above.

The maintained fork's canonical per-file runner ran with retries disabled. It reproduced
the reviewed optional/provider environment baseline: 20 files with failures (80 failed
tests) and one collection/no-tests file. No FU-369 focused file appears in that set. This
is reported as red; it is not represented as passing fork CI.

The first Aether PR #386 run failed all three required policy jobs in `Validate canonical
base manifest`: the accepted Objective Contract path was tracked but missing from the
workflow's exact non-`specs/` allowlist. The terminal applied the mechanically implied
one-line manifest correction without changing policy behavior. The locally reproduced
manifest then matched all `347` tracked non-`specs/` paths, the spec secret/mode boundary
passed, and the 50-test policy/TUI/documentation focus plus 434 subtests passed before a
normal follow-up push. No failed check was bypassed or relabelled.

## Issue dispositions

The final GitHub mutations occur only after the Aether PR is durably merged:

- #354: close after merged evidence for the real root/descendant canary.
- #369: close after the fork merge and merged Aether portable reconciliation evidence.
- #357: retain open. Diagnostics are now actionable and private, but no causal Python 3.13
  defect was reproduced; a green retry or diagnostic-only change is not a causal fix.
  The next boundary is any recurrence on the merged post-merge job, which should retain
  the qualified phase/class/source/runtime state.
- #352: retain open. No causal product/fixture defect was reproduced. The next boundary
  is the exact child admission/result or lock/CAS stage from another unchanged-source
  timeout.
- #371: close only when the whole four-issue component, issue reconciliation and cleanup
  are terminal.
- #275: remain open and untouched.
- #385: remain separate from this four-bug implementation scope; its routing recovery is
  recorded by the durable board and prospective review evidence.

No issue has a milestone, so milestone reconciliation is not applicable.

## Guidance, release and omitted effects

Current `AGENTS.md` remains coherent with the merged `origin/main`: it identifies the
maintained fork as transitional under PD-65 and now explicitly identifies Morfeo's final
contract-result reception while leaving execution closeout Supervisor-owned. Broad
#348/#261 source-mode reconciliation is outside this Objective Contract and no operating
instruction was invalidated by the scoped implementation.

Aggregate conclusions are independent:

- `release_impact=patch` — FU-369 is a compatible runtime correction and FU-357 adds a
  backward-compatible diagnostic failure subtype/state.
- `release_action=defer` — this objective authorizes source integration, not release
  preparation or publication.
- `release_channel=none` — no prerelease or stable publication is selected.

Version `0.24.0` is unchanged. No tag, GitHub Release, package publication, deployment,
service restart, profile/home change, credential acquisition/widening, settings/protection
change, live runtime activation, or #275 provider/backend work occurred.

The former objective-only monitor was repurposed by Morfeo as a cross-batch continuation
job. It and its retained authoring worktree are campaign-owned and must not be deleted by
this closeout. Therefore there is no objective monitor to remove here; progress and final
return use durable board state. Cleanup of merged objective branches/worktrees occurs only
after durable Aether merge evidence, while active, unmerged, concurrent, unrelated and
campaign-owned residue remains preserved.

## Morfeo contract-result reception

Aether artifact reviewed: `070452d04b61d480fe6b41cd7ec8c42e6f266b70`
(PR #386). Maintained-fork artifact: `415056fee527c5a2302370bd6dba56f84b9a4202`
(PR #6). Current owner instruction authorizes successive bug batches, excludes
#275, and preserves existing acceptance. The original finalized contract remains
byte-identical to its recorded digest.

Verdict: the four-issue remediation/disposition outcome is supported. This does
not mean four causal repairs, green full suites, a release or live activation.
#354 and #369 closed; #352 and #357 remain open with evidence and next boundaries.

### Criterion coverage

The following table separates direct Morfeo checks from reused pipeline evidence.

| Contract criterion | Artifact and evidence | Result / limit |
| --- | --- | --- |
| AC-1 scope and graph | Direct: native component has all four units, FU-352-R and terminal done. Disconnected test probe excluded. | Supported; no #275 unit. |
| AC-2 lineage | Direct: named concurrent-flow canary at Aether `070452d` passed; inspected exact source pin, ancestry, digest and primary/ref preservation assertions. | Supported for maintained-source behavior; live runtime was not activated. |
| AC-3 independent goal review | Reused: Supervisor's native tool/CLI/review/recovery matrix passed on fork `415056f`. Direct: inspected portable implementation/digest; GitHub comparison from reviewed `8b600f3` to `415056f` changes only `AETHER_FORK.md`. | Supported; no independent Morfeo rerun of the fork matrix or live model qualification. |
| AC-4 PluginContext | Direct: qualification/privacy module rerun on `070452d`; inspected nonce/source qualification and content-free fallback. Post-merge run `34481606730` passed the harness step on 3.11/3.12/3.13. Source/test bytes equal reviewed `2169f73`. | Diagnostic delivery supported; #357 stays OPEN, no causal fix established. |
| AC-5 concurrency | Direct: named competing-process oracle rerun at `070452d` passed. Reused: FU-352-R run24 independently approved `83ad2a5`, record `ab4eaa8`, including 90 module tests and bounded repetitions. | Evidence disposition supported; #352 stays OPEN, not claimed fixed. |
| AC-6 scope/tests | Direct: PR diff and all accepted commit ancestries verified; no diff-check errors. Reused: terminal full Aether/fork suites, build, static checks and attributed baseline failures above. | Focused reception passed; full suites were not rerun by Morfeo and are not globally green. |
| AC-7 GitHub | Direct: both PRs MERGED at the exact revisions above; four required Aether checks SUCCESS. Inspected failed post-merge logs: only historical public-artifact and selected-public-Hermes review assertions. Fork check rollup empty. | Source integrated; fork Actions NOT RUN, nonrequired Aether CI red. |
| AC-8 issue disposition | Direct: #354/#369/#371 CLOSED and #352/#357 OPEN. Reused terminal receipt records #275 unchanged timestamp; no #275 operation by this reception. | Honest dispositions supported; excluded work untouched. |
| AC-9 release/authority | Reused terminal no-activation/no-publication report; direct code/resource diff consistent with compatible review repair and additive diagnostics. | patch / defer / none; no live activation or release qualification claimed. |
| AC-10 cleanup | Direct: batch local branches absent, four unit directories absent, Aether remote branch absent; fork remote branch still exists. Root detached workspace remains for exit; campaign and receipt worktrees retained. | Documented residue, no blanket clean claim or bypass of denied deletion. |

### Direct reception execution and limits

On exact Aether `070452d`, CPython 3.13.15, using disposable Hermes/state homes
and no live board bindings, Morfeo executed the canonical wrapper with
`HERMES_TEST_FILE_RETRIES=0` and these targets:

- `tests/test_objective_contracts.py::test_concurrent_flow_handoff_preserves_lineage_through_reconstructed_maintained_resolver`
- `tests/test_observation_qualification.py`
- `tests/test_observation_lifecycle.py::test_two_process_transitions_with_one_expected_active_have_one_commit`

Observed: **62 passed, 1 skipped in 38.69s**, process exit 0. This is a focused
reception, not a rerun of the complete Aether/fork suites, their multi-Python
matrix or live provider traffic. The skip remains visible.

No material acceptance mismatch remains for the allowed issue dispositions.
The separately recorded process defects remain pending in the continuous campaign.
