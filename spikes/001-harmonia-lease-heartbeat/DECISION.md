# Experimental decision — Harmonia lifecycle authority

**Status:** Experimentally validated and approved for test-first production implementation; Gate C live remains unauthorized
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

## Frozen production specification

The production correction is intentionally narrower than the full lifecycle architecture discussed during consultation.

### Durable events

- `runtime.terminal.observed`: one authenticated technical terminal observation bound to run, task, attempt, contract generation/revocation epoch, message, logical session and ACP session. Allowed statuses are `completed`, `error` and `cancelled`.
- `cleanup.requested`: one durable terminal-cleanup intent. It is distinct from `cancel.intent` and never implies cancellation.
- `cleanup.completed`: the matching idempotent cleanup effect was acknowledged.
- `cleanup.unknown`: the cleanup effect may have occurred but cannot be verified; replay performs no blind second effect.
- `reconciliation.required`: authority expired or evidence became ambiguous before a trusted terminal event could be persisted.

Lease renewal itself remains represented by the authoritative SQLite lease row. No additional renewal event is required in this increment because renewal changes only expiry and the production ledger already fences it by resource, owner, epoch and token.

`runtime.terminal.observed` is technical evidence only. It must not call or weaken `KernelRunService.complete_task()` and must not grant semantic completion, acceptance, release or publication authority.

### Public projection compatibility

The existing `state` vocabulary remains compatible. Terminal and cleanup facts are exposed through additional fields rather than representing product completion:

```json
{
  "state": "session_bound",
  "technical_status": "completed",
  "semantic_completion": false,
  "cleanup_state": "pending"
}
```

`reconciliation_required` remains the fail-closed public state. Cleanup transitions may use `cleanup_state` values `pending`, `requested`, `completed` and `unknown`; they do not change semantic authority.

### Monitor ownership and timing

- `ProjectRuntimeContext` owns exactly one monitor task per durable dispatch `message_id`.
- A monitor starts only after `session.bound` is durable and is deduplicated by message ID.
- It polls only through `OlympusRuntimeAdapter`, renews the same dispatch lease before expiry, and persists terminal evidence before stopping.
- Renewal preserves resource, owner, epoch and token. It never falls back to `acquire_lease()` after expiry.
- Registry/context shutdown signals and awaits monitors with a bound before closing the ledger. Shutdown cannot append a false terminal event.
- Poll failures are retried only while authority remains valid. Expiry, revocation, replacement or terminal-evidence conflict stops normal monitoring and enters reconciliation.

### Stop semantics

- Active authority: retain `cancel.intent` before the external cancellation effect.
- Trusted terminal evidence: append `cleanup.requested`, call a dedicated cleanup operation that preserves the observed terminal status, then append `cleanup.completed` or `cleanup.unknown`. Do not emit `cancel.intent`.
- Expired authority without terminal evidence: persist/return `reconciliation.required`; perform no poll, cancel, close, dispatch or lease reacquisition.
- Repeated and concurrent stop calls produce at most one intent and one external effect for their branch.

### Restart policy

- Rebuild lifecycle solely from the project ledger and public Olympus session evidence.
- A bound dispatch with a still-live lease may resume one monitor; it must not stage, spawn or send again.
- Durable terminal evidence permits terminal cleanup without requiring the expired dispatch lease.
- Expired dispatch authority without trusted terminal evidence becomes `reconciliation.required` using only the fresh ledger-writer fence; it performs no ACP effect and creates no replacement session.
- Restart-safe observation/cleanup must use public adapter/ACPManager methods. Coordination code may not inspect `ACPManager.sessions`, `agents` or `prompt_tasks` directly.
- If a persisted terminal session cannot be transport-cleaned after restart, report `cleanup.unknown`; do not manufacture success or cancellation.

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

The experiment validates feasibility and the user has authorized a test-first production correction plus deterministic Gate B. This does **not** authorize ACP live execution, Gate C, merge, tag, release, deployment or v0.19.2. GitHub #107 remains open until the production regression matrix and Gate B are green.
