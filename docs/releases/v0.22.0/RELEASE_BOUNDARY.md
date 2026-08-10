# v0.22.0 Release Boundary — Orca Integration Foundation

> **Status:** RELEASED SOURCE BOUNDARY — DEFAULT-OFF; RUNTIME NOT ACTIVATED
> **Date:** 2026-08-09
> **Governing decision:** `../../decisions/PDR-0014-versioned-orca-production-adoption.md`

## Product statement

v0.22.0 establishes that Aether can integrate with, qualify, and control an exact Orca provider through the accepted Aether MCP architecture in bounded deterministic and model-backed executions.

It is the baseline that authorizes the separate v0.23.0 production-entry effort. It is not itself an activated production runtime.

## Exact accepted binding

- Orca: `1.4.167`;
- interface: desktop renderer plus public structured CLI;
- worker client at accepted M5.4: Codex CLI `0.147.0`;
- accepted M5.4 model route: `gpt-5.6-terra`;
- Aether MCP: provider-independent stdio package, default-off;
- installed/registered MCP tools: `0`;
- provider spend accepted by M5.4: USD 0 PAYG using the authorized system-default OAuth route;
- Headless-only support: not qualified.

No credential value, token, password, connection string, or private prompt body is part of this boundary.

## Strongest accepted evidence

- M3 lifecycle acceptance: exact Run/two-Task lifecycle, restart/rebind, recovery, cancel/close, and zero survivors;
- M4 worker acceptance: failed first attempt, retry generation/worktree, question/reply, artifact, replay, cancellation, and zero survivors;
- M5 parallel acceptance: Dispatches created before polling, deterministic overlap, handoff, integration, partial failure, aggregate cancellation, and zero survivors;
- M5.4 model-backed acceptance: two Dispatches before polling, two public liveness markers, positive overlap, two verified artifacts, two technical completions, integration, semantic close, zero automatic retries, and zero survivors.

Canonical files:

- `M3_LIFECYCLE_ACCEPTANCE.md`;
- `M4_WORKER_ACCEPTANCE.md`;
- `M5_PARALLEL_ACCEPTANCE.md`;
- `M5_4_MODEL_ACCEPTANCE.md`;
- `M5_4_WORKER_LIVENESS_CORRECTION.md`;
- `M5_MODEL_LIVENESS_CORRECTED_EVIDENCE.json`.

Historical M5.4 closure reported 22 focused tests and 198 repository tests. Final release acceptance must rerun the exact committed release tree; historical counts are not substituted for that gate.

## Included source capability

- Olympus/ACP and disconnected native-core retirement in the candidate source;
- exact provider identity/catalog and provider-seam qualification;
- contracts, schemas, admission, receipts, semantic trace, protected content, idempotency, and reconciliation foundations;
- deterministic and bounded model-backed coordination implementation through M5.4;
- fail-closed liveness and cleanup evidence;
- no hidden legacy fallback in the candidate.

## Limitations and exclusions

- Aether MCP remains unregistered and exposes zero callable tools in the installed runtime.
- Orca is not yet the normal path for real Aether sessions.
- Stable generic profiles are not production-qualified.
- Process-specific workflows are not migrated.
- Full dataset/export/training infrastructure is not part of this release.
- Olympus remains active in the current installed Aether runtime until a separately authorized cutover.
- No deployment, persistent service, credential mutation, provider spend, or activation is implied.

## Compatibility and migration

v0.22.0 preserves existing `.aether` stores as historical/local state and does not initialize, migrate, rewrite, truncate, or delete them. The new Aether MCP store is separate and default-off. Installed-runtime migration and rollback belong to v0.23.0.

## Source rollback

Before runtime activation, source rollback is repository-level: return to the previous published release or remove the default-off candidate package while preserving historical stores. Because v0.22.0 performs no registration or activation, it has no accepted claim that live Orca state can be restored by source rollback alone.

The first v0.23.0 activation Task must inventory the named installation and prove a separate configuration/runtime rollback.

## Publication result

The final v0.22.0 source candidate:

1. contains only the bounded release scope and documentary rebaseline;
2. passed exact committed-tree validation in isolation;
3. preserves the no-runtime/no-activation boundary;
4. passed secret and residue scans;
5. was accepted by the product owner;
6. converges across integrated `main`, annotated tag, and GitHub Release.

The final merge SHA, annotated tag object, peeled commit, stable/tag CI runs and
formal completion timestamp are recorded in immutable GitHub Release metadata.

## Successor

v0.23.0 starts real Aether MCP + Orca production dogfooding. Once its cutover gate passes, every multi-agent Task follows the repair-first, no-hidden-fallback policy in `../v0.23.0/PRODUCTION_OPERATING_POLICY.md`.
