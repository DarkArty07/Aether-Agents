# TASK M2.2 — Canonical Protocol and Stable Errors

> **Status:** AUTHORIZED AND FROZEN
> **Authorized by:** Christopher, 2026-08-08
> **Milestone:** Aether Agents v0.22.0 M2.2
> **Execution owner:** Hermes
> **Prerequisites:** M2.1a-R1 and M1.1b accepted

## Goal

Implement the provider-independent `aether.mcp/v1alpha1` protocol contract:
canonical request encoding, 24 exported input schemas, result/error envelopes,
stable error codes, operation identity, effect classes and bounded input
validation.

## Allowed implementation paths

- `src/aether_mcp/protocol.py` (new)
- `src/aether_mcp/__init__.py`
- `tests/aether_mcp/test_protocol.py` (new)
- `schemas/aether-mcp/v1alpha1/bundle.json` (generated snapshot)
- M2.2 acceptance/status/roadmap/long-horizon documentation

No new runtime dependency is authorized.

## Exact tool inventory

### High-level Aether tools (14)

`project_admit`, `project_inspect`, `swarm_validate`, `swarm_start`,
`swarm_status`, `swarm_dispatch`, `swarm_message`, `swarm_reconcile`,
`swarm_retry`, `swarm_cancel`, `swarm_record_decision`,
`swarm_record_evidence`, `swarm_close`, `swarm_trace`.

### Dynamic Orca tools (5)

`orca_search`, `orca_describe`, `orca_call`, `orca_batch`, `orca_events`.

### Learning tools (4)

`learning_capture`, `learning_label`, `learning_dataset`, `learning_export`.

### Retention maintenance (1)

`project_forget`.

## Behavior contract

1. `PROTOCOL_VERSION` is exactly `aether.mcp/v1alpha1`.
2. All 24 input schemas are strict objects with bounded fields and unknown request
   fields rejected.
3. Canonical encoding is deterministic UTF-8 JSON with sorted keys, compact
   separators and no NaN/Infinity/floats.
4. Request bodies are bounded to 65,536 bytes; cursors to 1,024 bytes; strings,
   arrays and nested objects have explicit bounds.
5. Caller-supplied principal identity is rejected.
6. UUIDs and SHA-256 digests are canonical and validated.
7. `orca_call` accepts a structured `command_id` and arguments only; no shell,
   command line or interpolation field exists.
8. Exact idempotent replay is accepted; a reused operation with differing
   canonical digest returns `IDEMPOTENCY_CONFLICT`.
9. Public errors select messages only from the committed stable-code registry;
   caller/provider bodies, secrets and tracebacks cannot enter envelopes.
10. Result and error envelopes always contain the frozen protocol, request and
    operation identity, trace IDs, effect, outcome, result/unknowns/warnings and
    error fields.
11. Snapshot generation is deterministic and must exactly match
    `schemas/aether-mcp/v1alpha1/bundle.json`.
12. M2.2 registers no callable MCP tools. It exports schemas for all 24; actual
    registration occurs only in the owning functional milestones. The M2.1a
    server therefore remains default-off and zero-tool.

## RED matrix

- missing protocol module;
- schema count/name drift;
- snapshot absent/drifted;
- unknown request fields;
- oversized body/cursor/string/array;
- malformed or noncanonical UUID/digest;
- wrong protocol version;
- caller-asserted principal;
- arbitrary shell/command string;
- unsupported numeric float/NaN;
- idempotency mismatch;
- secret-bearing error source;
- mutable exported schema state;
- nonzero MCP tool registration.

## Acceptance

- focused M2.2 tests pass;
- all 24 exact schemas are exported;
- generated bundle equals committed snapshot byte-for-byte;
- stable error-code list matches the canonical contract;
- negative matrix returns stable codes without submitted values;
- deterministic canonical bytes/digests reproduce;
- full repository suite, Ruff, compileall and `make mcp-smoke` pass;
- existing M1.1b exact-candidate evidence remains unchanged;
- no provider/network/process/storage/config/profile effect occurs.

## Forbidden effects and stop condition

Do not implement principal derivation, project admission behavior, persistence,
migrations, encryption, provider calls, lifecycle, learning capture, registration,
activation, merge, tag or Release. Stop after deterministic protocol/schema
artifacts, tests, documentation, pushed Draft-PR update and terminal CI.
