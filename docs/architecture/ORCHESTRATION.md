# Orchestration

## Routing decision

Hermes owns the direct-versus-orchestrated decision. It does not ask the user to choose a coordination mechanism when the current request, standing participant policy, configured budget and protected-effect policy already cover the work.

Use the direct path for tightly coupled or single-owner work. Use admitted multi-agent execution when a distinct specialist contribution, independent verification, conflict-safe parallelism or economical execution of a frozen contract is expected to improve the result after coordination overhead.

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

## Authority and model economics

Authority may come from the current request, durable owner policy, exact project policy and admitted runtime configuration. “Explicit worker/provider/model/effect/budget authority” does not mean “ask the user again”; it means each value must be identifiable and within an authorized boundary before dispatch. Missing, conflicting or exceeded authority is a real stop condition.

Hermes uses high-capability capacity to interpret intent, design the Task contract, resolve architecture and accept the result. Bounded mechanical work should use the cheapest qualified model that preserves quality. The selected route, actual model and available cost evidence must be inspectable; a label or expected model string is insufficient.

The current v0.23 manifest has no provider/account/model/cost fields, and the public model-worker adapter does not pass a model selector to Orca. Therefore the installed candidate cannot yet prove autonomous economical model routing. Prompt policy may choose the desired tier, but production claims wait for a typed runtime contract and qualification evidence.

## Supervision and acceptance

Hermes remains active while workers execute: it observes material progress, resolves bounded questions, continues independent coordinator work and synthesizes results. Worker completion is not semantic acceptance. Hermes verifies artifacts and the integrated user outcome before disposition and closure.

Failure is classified before recovery. Depending on cause and total cost, Hermes may correct the contract, perform a bounded retry, select another qualified economical worker or take over directly. No one fallback is automatic.

## Failure behavior

Typed denials are state evidence. Fix deterministic request defects and revalidate. Reconcile an uncertain `swarm_start` before retry. Do not retry an uncertain model Dispatch without authoritative status evidence. Stop on identity, authority, contract-generation, budget or cleanup conflicts.

A provider integration failure never authorizes Olympus, ACPManager, Harmonia, `talk_to`, an alias or a direct private CLI mutation. Hermes may repair the Aether-provider path only within the current task authority.
