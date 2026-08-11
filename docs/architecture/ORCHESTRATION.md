# Orchestration

## Direct path

Hermes implements directly when one accountable owner can satisfy the request with equivalent quality and less coordination. Direct work is a deliberate product choice, not a runtime failure fallback.

## Admitted multi-agent path

```text
resolve root
  → project_admit / project_inspect
  → freeze manifest, authority, effects and acceptance
  → swarm_validate
  → swarm_start
  → swarm_status
  → swarm_dispatch (only with worker/model/budget authority)
  → status / message / bounded retry or cancel
  → semantic disposition
  → swarm_close
  → verify cleanup and retain trace references
```

Independent Tasks may run concurrently only when their scopes and writers do not conflict. The provider may allocate attempt-owned isolation for such Tasks. Those resources are temporary, correlated to a Dispatch and removed at close; they do not become another canonical repository checkout.

## Failure behavior

Typed denials are state evidence. Fix deterministic request defects and revalidate. Reconcile an uncertain `swarm_start` before retry. Do not retry an uncertain model Dispatch without authoritative status evidence. Stop on identity, authority, contract-generation, budget or cleanup conflicts.

A provider integration failure never authorizes Olympus, ACPManager, Harmonia, `talk_to`, an alias or a direct private CLI mutation. Hermes may repair the Aether-provider path only within the current task authority.
