# v0.22.0 — Orca Integration Foundation

Published 2026-08-09.

## Release claim

Aether Agents v0.22.0 publishes the bounded, source-level Aether MCP + Orca integration foundation accepted through M5.4. It proves that Aether can qualify and control the exact supported Orca binding in deterministic and bounded model-backed executions.

This Release is **default-off**. It does not install, register, restart or activate Orca in the current Aether runtime.

## Included

- Removes Olympus/ACP and the disconnected pre-emptive native core from candidate source without changing the currently installed runtime.
- Provides the provider-independent `aether-mcp` stdio package and accepted internal contracts through M5.4.
- Preserves admission, idempotency, uncertain-effect reconciliation, liveness, fencing, recovery, semantic trace and cleanup foundations.
- Qualifies deterministic one-worker and two-worker coordination, plus one bounded two-worker model-backed execution.
- Preserves historical v0.19/v0.20 evidence and existing local `.aether` stores without migration or deletion.

## Exact qualified binding

- Orca: `1.4.167`.
- Interface: desktop renderer plus public structured CLI.
- Worker client accepted at M5.4: Codex CLI `0.147.0`.
- Accepted model route: `gpt-5.6-terra`.
- Aether MCP: local stdio package, default-off and unregistered.
- Registered or callable Aether MCP tools: **0**.
- Headless-only support: not qualified.

## Not included or activated

- No live Aether MCP registration or callable tool surface.
- No persistent Orca service or production-operation claim.
- No stable generic-roster qualification.
- No process-specific workflow migration.
- No credentials, account changes, provider spend or deployment.
- No live Olympus retirement, restart or historical-store migration.

## Verification

The final source candidate passed:

- `198 passed` in a disposable Python 3.11 environment with non-editable package provenance under `site-packages`;
- Ruff and compileall;
- shell and YAML validation;
- release-governance policy;
- exact 16-file product-asset validation;
- default-off and zero-tool bootstrap checks;
- current-link, residue, secret and clean-tree checks;
- GitHub CI on Python 3.11 and 3.12 before integration.

The exact stable commit, annotated tag object, peeled tag commit, stable/tag CI run identifiers and formal completion timestamps are appended below as post-publication metadata.

## Compatibility and rollback

v0.22.0 performs no runtime migration. Existing `.aether` stores remain historical/local state and are not initialized, rewritten, truncated or deleted by this source Release.

Before any future activation, source rollback is repository-level: return to the previous published tag or remove the default-off package while preserving local stores. Runtime migration and rollback must be designed and proven separately in v0.23.0.

## Next gate

v0.23.0 begins only through a separately authorized implementation and activation Task. Its first gate must register and validate the real Aether MCP + Orca path and prove operational rollback; publishing v0.22.0 does not cross that boundary.
