# Experimental decision — Harmonia lifecycle authority

**Status:** Experimentally validated; not yet approved as production implementation
**Issue:** [GitHub #107](https://github.com/DarkArty07/Aether-Agents/issues/107)
**Evidence:** [`README.md`](README.md), [`result.json`](result.json), executable [`main.py`](main.py)

## Context

The v0.19.1 Gate C rerun proved that Harmonia can admit, deduplicate and execute one real Hefesto ACP task, but the task completed about 0.78 seconds after its original ten-second dispatch lease expired. Harmonia then rejected `stop` as `authority_mismatch`, persisted no terminal observation and left its projection at `session_bound`.

A safe correction must support work lasting beyond the initial lease without weakening fencing, duplicating effects or equating technical ACP completion with semantic product completion.

## Provisional decision

Pursue a three-part production design:

1. **Renew the existing dispatch fence while work is observably active.**
   - Renew before expiry using the same resource, owner, epoch and token.
   - Validate active attempt, contract generation, revocation epoch and session binding before every renewal.
   - Never renew or reacquire after expiry, revocation, replacement or ownership mismatch.

2. **Persist a typed technical terminal observation.**
   - Poll only through the authorized Olympus adapter for the bound ACP session.
   - Persist one authenticated terminal observation for `completed`, `error` or `cancelled` tied to run/task/attempt/contract/message/session.
   - Keep technical terminal state distinct from semantic completion/release authority.
   - Stop heartbeat only after the terminal observation is durable.

3. **Make `stop` branch on durable lifecycle state.**
   - Active: preserve `cancel.intent` before external cancellation.
   - Trusted terminal: perform idempotent cleanup without manufacturing a cancellation or requiring the expired dispatch lease.
   - Expired without trusted terminal evidence: return `reconciliation_required` and perform no effect.
   - Repeated calls must return the same projection and create no duplicate event/effect.

## Why this decision

The spike demonstrated that production SQLite lease primitives already support safe same-epoch/same-token renewal and continue rejecting foreign tokens and replaced epochs. It also demonstrated that durable matching terminal evidence is sufficient to make cleanup idempotent after expiry while preserving fail-closed behavior when evidence is missing or mismatched.

## Alternatives considered

### Increase the fixed TTL

Rejected. Any fixed duration can be exceeded, delays failover after crashes and hides rather than resolves the lifecycle race.

### Reacquire an expired dispatch lease blindly

Rejected. A new epoch may belong to another owner or replacement attempt; blind reacquisition would weaken fencing and could duplicate effects.

### Force `stop` before the worker finishes

Rejected. It prevents collection of semantic evidence and converts successful natural completion into cancellation.

### Treat Olympus DB completion as sufficient without a kernel event

Rejected for production. The live failure showed that external status alone leaves Harmonia's durable projection stale. Terminal evidence must be authenticated and bound into the kernel ledger.

## Production invariants

- At most one live ACP session and one dispatch effect per durable request.
- Heartbeat changes expiry only; it never changes identity, epoch or token.
- No renewal after authority becomes stale, expired, revoked or replaced.
- Terminal evidence is session-bound and idempotent.
- Technical completion does not grant semantic completion or release authority.
- Active cancellation remains write-ahead.
- Terminal cleanup does not emit false cancellation.
- Missing or ambiguous evidence remains fail-closed.
- Restart reconciliation cannot create a second session or resurrect stale authority.
- Harmonia remains default-off.

## Expected production change surface

The implementation should remain bounded to the coordination equivalence class:

- `kernel_dispatcher.py`: explicit checked renewal and typed terminal observation/finalization operations;
- `harmonia_service.py`: one bounded monitor and lifecycle-aware status/stop projection;
- `olympus_adapter.py`: observe and close while preserving actual terminal status;
- workflow/runtime projection only as needed for a typed technical terminal event;
- focused dispatcher/service/adapter/server tests, including fake-clock and restart cases.

Exact files and event names remain subject to test-first implementation findings. This document does not authorize unbounded refactoring.

## Promotion gate

Before this decision becomes production behavior:

1. Write RED regressions for work exceeding the initial lease, terminal persistence, repeated stop, crash/restart and adversarial authority.
2. Implement the smallest coherent lifecycle path.
3. Run the nine focused groups, all coordination tests, full suite, Ruff, compileall, scope/default-off/compatibility/secret gates.
4. Independently verify that no stale/foreign authority can renew or finalize.
5. Close #107 only with deterministic evidence.
6. Request a new explicit authorization before any ACP live Gate C rerun.

## Decision boundary

The experiment validates feasibility and selects the preferred direction. It does **not** authorize production implementation, ACP live execution, issue closure, merge, tag, release, deployment or v0.19.2.
