# Hermes patch-preflight dogfood report

Observation cutoff: `2026-08-31T02:01:37Z`

This report records the real Aether flow used to reconcile the active local Hermes patch ledger. It is execution evidence, not a release-readiness claim and not a selection of a final Hermes baseline or runtime strategy.

## Canonical binding

- Portable Project: `12027989-a08f-41cd-a82c-54ff1bfb6b03` (`DarkArty07/Aether-Agents`).
- Final contract: `oc_d7d067bf87e67cba@v4`, SHA-256 `654a074e03fd9b711312cb506e81e6e0b6194445c0e4c654eb2b2de3d05a7d8d`.
- Authorized v4 base: `8b76497a37475f060cfd65dd37119e9cc3515564`.
- Public upstream inspected: `NousResearch/hermes-agent@4f22543509d1b91dc45bcb369447126c5eb14fb7`.
- The v2 root, all four initial Implementer units, both bounded rework units, and the v4 terminal lane carried the same canonical board Project. Initial Implementer work used distinct Project worktrees; terminal Supervisor work shared its root worktree through same-flow affinity.
- `goal_mode` was false for every implementation and terminal unit. Implementer units used fresh sessions; only same-profile terminal Supervisor work propagated flow affinity.

## Timing and decomposition

The executable v2 root started at board time `1788117673`. The four useful Implementer cards were created at `1788117974`, so time to first child was 301 seconds. They were created together before context compression and released together after the root recovery completed.

Initial unit sizes were deliberately bounded by non-overlapping evidence ownership:

| Unit | Scope | Files in accepted source commit | Added | Deleted |
|---|---|---:|---:|---:|
| `t_0c974e88` | HLP-188, HLP-189, HLP-191, HLP-194 | 4 | 267 | 0 |
| `t_4e4b7419` | HLP-198, HLP-204, HLP-209, HLP-226 | 4 | 264 | 0 |
| `t_5bb86eb3` | HLP-211/HLP-211b, HLP-246, HLP-247 | 3 | 170 | 0 |
| `t_f13bee6c` | Schema, strict validator, deterministic renderer, tests | 3 | 968 | 0 |

Independent review found one shared schema/evidence incompatibility and the newly active HLP-262 record. The bounded Project-bound normalization rework `t_da75506d` changed 14 files (+372/-129). A second focused rework `t_016ab85f` corrected only HLP-226b coverage and its validator bindings across 3 files (+116/-15). No duplicate normal Implementer graph was created for v3 or v4.

The superseding v3 root reached its sole terminal child in 324 seconds. It reused the accepted v2 units rather than recreating them. After the owner-authorized #264 recovery required a contract correction, the v4 root reached its sole terminal child in 296 seconds and again reused the completed units.

## Review and rework

1. Supervisor cold-read the four initial commits and identified that entry evidence shapes conflicted with the strict schema; the validator was kept strict rather than weakened.
2. The first attempted normalization card, `t_21b8341a`, lost its Project/workspace binding and failed three spawn attempts. It performed no implementation work and remains blocked as contained administrative evidence.
3. After HLP-226b recovery, replacement `t_da75506d` was created with the exact Project and a distinct worktree. It normalized the 11 existing fragments, added HLP-262, retained all limitations, and added RED→GREEN consistency tests.
4. Supervisor integrated and tested the five accepted commits, then found the combined HLP-226/HLP-226b evidence gap. Project-bound `t_016ab85f` added the missing component, portable patch binding, unavailable reconstruction input, and negative tests. Supervisor independently accepted the resulting six-commit candidate.
5. The v4 terminal replayed the six accepted changes as separate commits over the exact v4 base. Focused reconciliation verification passed 18 tests before final artifact generation.

## Recovery and stop history

### Superseded v1: contract and routing evidence

The v1 root `t_2548a58b` stopped before decomposition because its immutability language contradicted the required real-board dogfood. Its `origin_signal=revision` block then auto-promoted without a controller or contract revision. The row remains triage-only administrative history and must not run again.

### #262 / HLP-262

- The auto-promotion defect was recorded first in public issue `https://github.com/DarkArty07/Aether-Agents/issues/262`.
- Durable recovery evidence records owner notification before repair, a RED regression, affected suites, a post-reload canary that survived three readiness recomputations, and explicit unblock as the only resume.
- Portable artifact: `patches/hermes/HLP-262-origin-signal-sticky.patch`, SHA-256 `abb3215645f400019c1eb5746f288a5ba517c3ba76547533d3d0693a1acb2f1a`.
- The recovery changed the effective Hermes identity before normal v4 integration; v4 explicitly classifies it as an allowed issue-first recovery rather than as normal reconciliation work.

### #226 / HLP-226b

- The Project-loss class already existed in owner-visible issue `https://github.com/DarkArty07/Aether-Agents/issues/226`. The terminal-affinity recurrence was added to that issue before repair, and the original unbound card was contained without work.
- RED→GREEN evidence and 80 affected tests qualified the smallest correction. A real replacement card inherited the canonical Project, distinct worktree, and deterministic branch.
- Portable artifact: `patches/hermes/HLP-226b-affinity-terminal-project-inheritance.patch`, SHA-256 `a28fd10888932f421d32d41e1012ec7aad17280ae9e289c4d0329ff492f6c040`.
- The documented private backup existence check was approval-denied. It was not retried, replaced, or inferred; reconstruction input and overall artifact verification remain unavailable.

### #264 and the v3→v4 transition

- A read-only Python inventory was approval-gated in a headless worker. Public issue `https://github.com/DarkArty07/Aether-Agents/issues/264` and durable board evidence record the defect and owner notification before attempted repair.
- The denial recurred on a read-only backup-existence check and again on the v3 pre-integration identity gate. Every denial stopped normal work; no alternative was used to infer the unavailable backup input.
- The owner explicitly selected broad `approvals.mode: off` for Supervisor and Implementer. Morfeo remained non-off. Active and packaged modes were verified, the previously blocked read-only command class passed, the unconditional hardline guard still denied root-filesystem deletion in dry-run evaluation, and Aether policy-hook tests still blocked protected remote mutation.
- Packaged recovery commit `7b0651ac9fa2ae91eadb3dbf1a2564b3459fd0b2` is tree-equivalent to terminal-workspace commit `81f95c37c2498fcdc856692d045cf87e0d0f683d`.
- v3 stopped because its acceptance boundary did not yet allow the active configuration delta. Final v4 explicitly added #264 to the permitted recovery set. The v3 terminal remains triage-only administrative history.

## Normal-work immutability boundary

Before v4 integration, the effective Hermes checkout identity was commit `0b288979e2322c02ab42c05f1e183bb31cfa5aa9`, tree `b433de234467cfa91f74b3b8427b57f93449be3a`, with tracked-delta digest `ff612990209143809b80f38b61f62cf9317f5409cf7be3ab82142f0e388747ab`. Secret-safe profile/config, credential-file metadata, memory/session-directory metadata, and gateway-process identity were captured without reading credential contents. A post-integration comparison is required before terminal completion. Objective-created board events, worktrees, Git commits, tests, PR/CI records, and versioned evidence are expected deltas; no further effective-runtime, service, profile, credential, memory, or unrelated user-data mutation is authorized.

## Generated product evidence

- `hermes-patch-reconciliation.v1.json` contains exactly 12 canonical active detailed ledger records in deterministic ID order.
- All 12 recommendations are `retain`; no local patch is retired.
- Upstream dispositions: 6 partial, 2 open, 1 verified, 3 missing.
- Retirement gates: 8 failed, 3 not executed, 1 partial.
- Artifact verification: 9 not applicable, 3 unavailable. All three referenced portable patches pass checksum and parser controls; unavailable reconstruction inputs remain explicit.
- The fixed-input generator was run twice at `2026-08-31T02:01:37Z`; JSON and Markdown were byte-identical.

## Acceptance A–K map at the evidence cutoff

- **A — PASS:** the validator derives 12 detailed ledger sections, rejects omissions/duplicates/unknown IDs, and generated output contains each exactly once.
- **B — PASS:** every disposition and recommendation carries structured source, public API, test, or artifact evidence at the exact inspected revision; no label alone establishes equivalence.
- **C — PASS WITH EXPLICIT UNAVAILABLE RESULTS:** checksums and parser controls pass for HLP-211b, HLP-226b, and HLP-262. Apply/reconstruction outcomes and missing inputs are recorded without silent success.
- **D — PASS:** fixed timestamp/revision/input reruns are byte-identical and path/secret checks reject non-portable content.
- **E — PASS:** all 12 entries retain local behavior; the validator rejects retirement candidacy without a passed exact-revision test gate.
- **F — PENDING FINAL POST-COMPARISON:** #262, #226b, and #264 are separately evidenced authorized recoveries. No further normal-work runtime delta is permitted; final identity comparison remains part of terminal closeout.
- **G — PASS TO CUTOFF:** no release, tag, package publication, deploy, credential change, service restart/activation, or final baseline choice occurred.
- **H — PASS TO CUTOFF:** implementation used RED→GREEN tests and deterministic generation; complete integrated quality/build verification remains in the terminal lane.
- **I — PASS FOR NEW DEFECTS:** #262 and #264 have issue-first and durable owner-notification evidence. #226 was a pre-existing owner-visible issue; its terminal recurrence was appended before the bounded HLP-226b repair.
- **J — PASS:** this report records timings, exact Project/worktree strategy, unit sizes, review/rework, stop/recovery events, reuse, current terminal state, and residual administrative rows.
- **K — PENDING REMOTE CLOSEOUT:** protected PR/check/merge evidence and the #261 comment are terminal steps. Issue #261 must remain open.

## Terminal and residual-card state at cutoff

The v4 terminal card `t_dc150162` is the sole runnable integration/closeout lane. Local integration and deterministic generation are complete, but full verification, protected PR checks/merge, the #261 update, final post-identity comparison, and final residual audit remain pending; their final results belong in the durable terminal handoff.

Known residual rows are intentionally non-runnable administrative evidence: superseded v1 root `t_2548a58b`, superseded v2 terminal `t_e729952b`, superseded v3 terminal `t_a2cfb68b`, and unbound orphan `t_21b8341a`. They must remain triage/blocked rather than being resumed. Completed v2 units and reworks are immutable handoff history, not residual work.
