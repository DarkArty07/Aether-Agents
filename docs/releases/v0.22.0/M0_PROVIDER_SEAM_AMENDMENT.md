# M0 Provider Seam Fast-Path Amendment

> **Status:** ACCEPTED
> **Accepted by:** Christopher (DarkArty07)
> **Acceptance date:** 2026-08-07
> **Scope:** Design authority only; no Orca lifecycle or Aether MCP source implementation
> **Supersedes only:** The requirement that every admitted provider result/effect/timeout/recovery contract must be published by Orca's catalog itself

## 1. Decision

M1.2 is accepted with verdict `INSUFFICIENT`, not treated as a provider rejection.
Aether may proceed with a version-pinned adapter contract under two bounded
extensions:

1. Aether may own machine-readable result, effect, timeout and recovery schemas
   learned from separately authorized, isolated and deterministic public-command
   fixtures when the Orca catalog does not publish those semantics.
2. Aether may implement aggregate semantics by composing only version-pinned
   public Orca commands when no single public aggregate command exists.

This is the approved fast path. It does not authorize implementation or execution
of those fixtures in this amendment.

## 2. Preserved authority boundary

Orca remains the sole owner of Run, Task, Dispatch, worker, terminal, message,
worktree, recovery and cleanup mechanics. Aether may own:

- validation and normalization of public structured requests/responses;
- product policy, admission and semantic acceptance;
- an idempotent operation journal and conservative receipts;
- version-pinned composition plans over public Orca commands;
- schemas and fixtures that describe observed public behavior.

Aether must not create a second operational state machine, write Orca private
state, infer success from silence, source/eval shell, scrape GUI state or restore
Olympus/Harmonia/ACP as a fallback.

## 3. Version-pinned schema bundles

Every Aether-owned provider schema bundle must pin:

- canonical launcher manifest digest;
- launcher and AppImage paths, sizes and SHA-256 digests;
- Orca product version;
- catalog schema, command count, bytes and SHA-256 digest;
- adapter and schema-bundle version;
- exact public command/argv;
- request schema;
- observed response schema and fixture digest;
- declared effect class;
- timeout and ambiguity classification;
- reconciliation/cleanup evidence;
- capability and use-case coverage.

Unknown fields may be preserved as inert data, but unknown required semantics or a
material identity/schema mismatch fail closed. Mutation remains blocked while a
schema is missing, stale or ambiguous. Read-only diagnosis may report the drift.

## 4. Public-command composition

A missing aggregate command may be implemented only when a later accepted design
and isolated fixture prove an explicit plan containing:

1. ordered public Orca operations;
2. preconditions and effect class for every step;
3. one caller operation identity and step identities;
4. timeout and `UNKNOWN` handling;
5. observation/reconciliation steps;
6. cleanup and zero-survivor evidence;
7. partial-result semantics;
8. rollback limits without fabricated atomicity.

Composition is not permission to substitute shell commands, private databases,
filesystem internals or undocumented UI behavior. Aether must label normalized or
composed observations distinctly from provider-native events.

## 5. Six missing M1.2 aggregates

M1.2 identified these missing public aggregate seams:

- provider event stream read;
- Run resource inventory;
- aggregate Run resource cleanup;
- Run cancel;
- Run close;
- Task cancel.

They are candidates for public-command composition, not assumed supported. M1.3
must either prove each required composition in isolation or leave it unsupported.
No design prose may promote one to `SUPPORTED`.

## 6. Required sequence

```text
accepted fast-path amendment
-> M1.1b canonical candidate verifier
-> Hermes independent acceptance
-> separately authorized isolated M1.3 fixture/lifecycle qualification
-> M1.4 provider decision
-> M2 source implementation
```

M1.1b must replace the generic Bash-mutation blacklist with the canonical manifest
`ORCA_PROVIDER_MANIFEST.json` and close cleanup/inventory evidence before any M1.3
operation.

## 7. Current authorization

Authorized now:

- versioned documentation for this decision;
- canonical Orca identity manifest;
- one repository-local external-agent M1.1b implementation task;
- read-only identity/catalog probes and AppImage metadata extraction bounded by
  that task.

Not authorized:

- Runs, Tasks, Dispatches, workers, messages, terminals or worktrees;
- mapped Orca operations other than `agent-context --json`;
- adapter or Aether MCP source;
- schema fixture capture for operational commands;
- M1.3, M2, activation, deployment, merge, tag or Release.

## 8. Acceptance evidence

- M1.2 independent review:
  `docs/releases/v0.22.0/M1_2_INDEPENDENT_REVIEW.md`
- frozen matrix:
  `docs/releases/v0.22.0/M1_ORCA_PROVIDER_SEAM_MATRIX.json`
- canonical candidate manifest:
  `docs/releases/v0.22.0/ORCA_PROVIDER_MANIFEST.json`
- next implementation contract:
  `docs/external-agent/TASK-M1.1B.md`
