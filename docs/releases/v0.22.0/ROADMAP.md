# Aether Agents v0.22.0 Roadmap — Orca Integration Foundation

> **Status:** RELEASED — SOURCE DEFAULT-OFF; RUNTIME NOT ACTIVATED
> **Date published:** 2026-08-09
> **Product owner:** Christopher (DarkArty07)
> **Governing decision:** `../../decisions/PDR-0014-versioned-orca-production-adoption.md`
> **Release PR:** https://github.com/DarkArty07/Aether-Agents/pull/163
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

The strongest committed technical baseline before the documentation rebaseline is `bb0723188bddb9da0807653763347f759be0c64e`. The exact final merge commit, annotated tag object, peeled tag commit, CI runs, and formal completion time are recorded in immutable Git/GitHub release metadata rather than self-referentially inside the tagged tree.

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

### R1 — Exact source candidate acceptance — COMPLETE

Issue #169 identified that the required `product-assets` job still asserted the
13-file M2 source inventory while the accepted M3-M5 candidate correctly tracked
16 files. Commit `13a916a38d6b580a3e71a710fe5d218a7eba34a1` added
`coordination.py`, `lifecycle.py`, and `orca_provider.py` to both Test and Release
contracts and to a local regression test. No accepted source was removed.

Issue #170 identified that protected `main` still required a `build` context
after the legacy Olympus distribution job had been removed. The candidate
restores a real bounded `aether-mcp==0.22.0` wheel build/import in PR CI and
requires the same verification before tag publication. Branch protection was
not bypassed, disabled, or weakened.

The final candidate reconciled package, changelog and Release identity without
adding capability. A fresh detached checkout with a non-editable installation
passed the full 199-test suite, Ruff, compileall, bounded wheel/sdist build,
shell/YAML validation, release-governance policy, the exact 16-file inventory,
current-link checks, secret review and clean-tree invariants.

**Pass:** one exact candidate was accepted for source integration. Its immutable
SHA/tree and final CI evidence are recorded on PR #163 and in the GitHub Release.

### R2 — GitHub integration and publication — COMPLETE

- PR #163 was made ready only after exact-candidate acceptance;
- atomic history was preserved through normal merge into `main`;
- integrated tree identity was verified;
- annotated tag `v0.22.0` was created on integrated `main`;
- the GitHub Release was published and read back;
- issue, milestone, branch, and remote convergence were reconciled.

**Boundary:** source publication did not install, register, restart, activate,
spend, retire the live Olympus runtime, or begin v0.23.0 runtime work.

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
