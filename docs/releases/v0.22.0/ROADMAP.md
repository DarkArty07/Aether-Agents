# Aether Agents v0.22.0 Roadmap — Orca Integration Foundation

> **Status:** SCOPE CLOSED AT M5.4 — SOURCE RELEASE PENDING
> **Date rebaselined:** 2026-08-09
> **Product owner:** Christopher (DarkArty07)
> **Governing decision:** `../../decisions/PDR-0014-versioned-orca-production-adoption.md`
> **Draft PR:** https://github.com/DarkArty07/Aether-Agents/pull/163
> **Release ledger:** https://github.com/DarkArty07/Aether-Agents/issues/166

## 1. Release claim

v0.22.0 proves the bounded **Aether MCP + Orca integration foundation**. It does not claim normal production operation or installed-runtime activation.

The former M0-M12 roadmap was accepted as a design on 2026-08-06. The product owner rebaselined its version placement on 2026-08-09 after M5.4 provided enough evidence to close the integration question and begin a separate production-dogfooding version. The exact former roadmap is preserved as `HISTORICAL_M0_M12_ROADMAP.md`; its future milestones are not current v0.22.0 authority.

## 2. Accepted technical boundary

| Milestone | Accepted result | Canonical evidence |
|---|---|---|
| M0 | Architecture, authority, contracts, cases, and original roadmap accepted | `M0_DESIGN_ACCEPTANCE.md` |
| M1 | Exact Orca identity/catalog, canonical bytes, provider seam, and lifecycle prerequisites qualified | M1 acceptance/evidence files in this directory |
| M2 | Provider-independent default-off Aether MCP foundation and bounded Orca adapter accepted | M2 acceptance/evidence files in this directory |
| M3 | Deterministic Run and Task lifecycle, restart/rebind, reconciliation, cancellation, closure, and zero-survivor cleanup accepted | `M3_LIFECYCLE_ACCEPTANCE.md` |
| M4 | Deterministic one-worker retry, question/reply, artifact, replay, cancellation, and cleanup accepted | `M4_WORKER_ACCEPTANCE.md` |
| M5 | Deterministic two-worker overlap, handoff, integration, partial failure, aggregate cancellation, and cleanup accepted | `M5_PARALLEL_ACCEPTANCE.md` |
| M5.4 | Bounded two-worker model-backed Orca/Codex execution accepted after liveness correction | `M5_4_MODEL_ACCEPTANCE.md` and `M5_4_WORKER_LIVENESS_CORRECTION.md` |

The strongest committed technical baseline before this documentation rebaseline is `bb0723188bddb9da0807653763347f759be0c64e`. The final release commit remains unknown until the release tree is reconciled, committed, independently verified, integrated, tagged, and published.

## 3. Included scope

- candidate-source retirement of Olympus/ACP and the disconnected pre-emptive native core;
- `aether-mcp` provider-independent stdio distribution, default-off and zero-tool;
- approved 15-tool operational contract and internal planning/admission/receipt/trace foundations without registration;
- exact Orca 1.4.167 desktop-renderer/public-structured-CLI qualification;
- deterministic M3-M5 behavior and M5.4 model-backed evidence;
- idempotency, uncertain-effect reconciliation, liveness, recovery, fencing, cleanup, and preserved evidence;
- documentation of limitations and the transition to v0.23.0.

## 4. Explicit exclusions

v0.22.0 does not include or imply:

- live Aether MCP registration or callable tools in the installed Hermes runtime;
- persistent activation or production operation through Orca;
- Headless-only Orca qualification;
- stable-roster production qualification;
- process-specific workflow migration;
- full learning-dataset construction, export, training, fine-tuning, or promotion;
- live Olympus cutover or removal from the current installation;
- credentials, account changes, provider spend, deployment, or recurring services.

## 5. Moved work

| Former milestone | Current authority |
|---|---|
| M6 | v0.23.0 generic roster and policy qualification |
| M7 | Minimal diagnostic trace in v0.23.0; full dataset program separately deferred |
| M8 | v0.23.0 optional-role evidence gate |
| M9 | v0.23.0 production entry and operability; workflow packaging evolves with v0.24.0 |
| M10 | Evaluation repeated separately in v0.23.0 and v0.24.0 |
| M11 | v0.22.0 release-only closeout below; each later version receives its own release gate |
| M12 | Controlled production entry moved to the beginning of v0.23.0; process cutover belongs to v0.24.0 |

Moved work is neither implemented nor accepted by v0.22.0.

## 6. Remaining v0.22.0 source closeout

### R0 — Documentation and GitHub rebaseline — COMPLETE

- preserve the former roadmap/status as historical;
- approve PDR-0014 and current version roadmaps;
- reconcile README, AGENTS, decision index, release boundary, status, and Draft PR #163;
- create separate GitHub milestones and ledgers for v0.22.0, v0.23.0, and v0.24.0.

**Pass:** documentation-only diff, valid links/YAML, no secrets, and no source/runtime/config/profile changes.

**Evidence:** commit `51e7aa6f277551ed31753eef7d6999c353752721`, GitHub milestones/issues #166-#168, Draft PR #163, 198/198 local tests, release-governance PASS, zero staged secret findings, four valid status YAML mappings, and 76 changed local links with zero missing targets.

### R1 — Exact source candidate acceptance — BLOCKED BY #169

The required GitHub `product-assets` job currently fails because
`.github/workflows/test.yml` still asserts the exact 13-file M2 source inventory,
while the accepted M3-M5 candidate correctly tracks 16 files. The rejected files
are `coordination.py`, `lifecycle.py`, and `orca_provider.py`. The documentation
rebaseline changed none of those paths.

Issue #169 must reconcile the restrictive product-asset contract with the exact
accepted v0.22.0 boundary. Removing accepted M3-M5 source to satisfy the stale
assertion is forbidden. This documentation task does not authorize editing the
workflow, source, tests, scripts, configuration, profiles, or runtime.

- reconcile package/version/changelog/release identity without adding capabilities;
- reconcile the stale product-assets inventory under separately frozen authority;
- run the exact release gate in an isolated committed checkout;
- verify focused/full tests, lint, compile, schemas, docs/links, setup/default-off behavior, forbidden-runtime scans, secret review, and clean-tree invariants;
- present exact SHA/tree, scope, limitations, compatibility, evidence, and rollback.

**Pass:** one exact candidate is approved for source integration. Historical test counts remain evidence; they do not replace the final exact-tree gate.

### R2 — GitHub integration and publication

When R1 is green and source publication authority applies:

- push/update Draft PR #163;
- make it ready only when candidate acceptance is complete;
- preserve atomic history through normal merge unless repository policy changes;
- verify integrated `main` tree equivalence;
- create annotated `v0.22.0` on integrated `main`;
- publish and read back the GitHub Release;
- reconcile issues, milestone, branch, and remote convergence.

**Stop:** source publication does not install, register, restart, activate, spend, or begin v0.23.0 runtime work.

## 7. Completion definition

v0.22.0 is released only when:

1. its exact bounded scope and limitations are current;
2. one committed candidate passes the final isolated source gate;
3. product-owner candidate acceptance is recorded;
4. Draft PR #163 is integrated without losing traceability;
5. `origin/main`, peeled annotated tag, and GitHub Release converge;
6. Release notes explicitly state default-off, zero registered tools, qualified binding, and no live activation;
7. GitHub issue #166 and the v0.22.0 milestone are reconciled.

Production activation remains a v0.23.0 gate.

## 8. Next version

After v0.22.0 publication, start `../v0.23.0/ROADMAP.md`. Its first material task creates and separately activates the real Aether MCP + Orca production path. After that cutover, real multi-agent work must use Orca and integration failures must be repaired and retried through the same path.
