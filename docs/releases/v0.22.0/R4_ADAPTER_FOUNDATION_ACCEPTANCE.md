# R4 — Restricted Adapter and Reconciler Foundation Acceptance

> **Status:** CLOSED / PASS WITH MUTATIONS UNAVAILABLE
> **Date:** 2026-08-08
> **Provider:** exact-build planning only; no provider executor
> **Coordinator binding:** UNQUALIFIED / REQUIRED
> **MCP tools registered/callable:** 0 / 0
> **Provider mutation executed:** No
> **D1 granted:** No

## 1. Result

R4 implements the minimum default-off adapter foundation that remains valid after
R3's coordinator-bootstrap block. It does not claim that Orca mutation or full
agent orchestration works.

Implemented modules:

- `src/aether_mcp/adapter.py`
- `src/aether_mcp/journal.py`

The modules contain no subprocess runner, shell, network client, credential lookup,
MCP registration, service startup, background worker, or persistent daemon.

## 2. Provider/build and authority binding

`ProviderBuildBinding` binds planning to the exact:

- candidate ID and product version;
- manifest digest;
- catalog digest;
- launcher digest;
- AppImage digest.

`CoordinatorBinding` additionally binds:

- principal UUID;
- project UUID;
- Orca terminal handle;
- provider-build digest;
- positive admission generation.

Planner mismatches fail with stable local errors. Under
`AdapterPolicy.r3_restricted(...)`, the exact qualified read-only status argv is
available, while every mutation fails before intent/effect with:

```text
ERR_COORDINATOR_BINDING_UNQUALIFIED
```

A non-restricted policy exists only as a deterministic test/design seam. No current
runtime or MCP surface constructs or activates it.

## 3. Structured argv

The planner emits immutable argument tuples. It never accepts shell strings or
uses `shell=True`. Text fields reject empty values, boundary whitespace, control
characters, NUL and oversized UTF-8 values.

The synthetic qualified fixture proves the intended public shape:

```text
orchestration run-create --objective <one-argv-value> \
  --from <bound-terminal-handle> --json
```

That fixture proves argument construction and authority checks, not provider
availability.

## 4. Append-before-effect journal

`OperationJournal` is a local operation-intent/receipt ledger. It is not a second
Run/Task scheduler or provider-state database.

Properties:

- caller-supplied local root only;
- root/file symlinks rejected;
- regular file with mode `0600` on creation;
- canonical one-record-per-line JSON;
- monotonic sequence;
- SHA-256 predecessor chain and per-record digest;
- shared/exclusive `flock`;
- `fsync` after every append;
- atomic `prepare_intent()` critical section;
- operation-ID conflict detection;
- no raw objective or coordinator handle persisted;
- provider response stored only as structured IDs and response digest.

The atomic prepare closes the race where two callers could both observe no intent
and execute the same effect.

## 5. Idempotency and uncertainty

`AdapterRuntime.execute()` enforces:

1. atomically append `INTENT/PREPARED` before invoking the injected executor;
2. same operation + same digest after a terminal receipt returns replay without a
   second provider call;
3. same operation + changed request returns `ERR_OPERATION_CONFLICT`;
4. existing intent without receipt returns `UNKNOWN` without reexecution;
5. timeout/exception appends `RECEIPT/UNKNOWN` and does not retry;
6. foreign or malformed receipt appends `UNKNOWN` and fails closed.

The foundation never converts timeout or malformed response into success or
`NOT_APPLIED`.

## 6. Reconciliation

`reconcile()` accepts only an injected read-only probe and a structured
`ReconciliationObservation`:

- `APPLIED` → `SUCCEEDED`;
- `NOT_APPLIED` → terminal for the same operation identity; any retry needs a new
  operation;
- `UNKNOWN` → remains `UNKNOWN`.

Reconciliation validates project scope, response digest, provider request ID and
resource IDs before appending its receipt. A terminal reconciliation replays
without invoking the probe again.

No current Orca-specific inventory/reconciliation executor is implemented or
claimed qualified.

## 7. TDD and verification

Initial RED:

```text
ModuleNotFoundError: aether_mcp.adapter
```

Focused GREEN:

```text
16 passed
Ruff:      PASS
compileall: PASS
```

Covered:

- R3 mutation rejection;
- build/principal/project/generation mismatch;
- missing coordinator binding;
- argv/control-character safety;
- append-before-effect ordering;
- atomic duplicate fencing;
- success replay;
- timeout and `UNKNOWN`;
- operation conflict;
- `APPLIED` and `NOT_APPLIED` reconciliation;
- foreign/malformed receipt;
- journal tampering;
- symlink escape;
- zero MCP tools.

## 8. Explicit limitations and next gate

R4 does not provide:

- a live Orca executor;
- coordinator terminal admission;
- provider mutation;
- Run/Task state ownership;
- resource inventory implementation;
- cleanup execution;
- cancellation;
- a registered MCP tool;
- a real worker, model or provider account;
- an R5 slice.

R5 was blocked by `R3_LIFECYCLE_ACCEPTANCE.md` and later closed without executing
a provider-backed two-worker slice. A future R5-R1 requires a separate owner-
authorized coordinator-binding gate with new evidence.
