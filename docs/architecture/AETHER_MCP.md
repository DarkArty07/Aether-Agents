# Aether MCP architecture

Aether MCP is the local stdio control and trace boundary between Hermes and the qualified execution provider. It is not a second product supervisor and does not implement a hidden coordination kernel.

## Components

| Component | Responsibility |
|---|---|
| `server.py` | FastMCP registration and stable secret-safe envelopes |
| `guidance.py` | Canonical just-in-time descriptions for all 15 tools |
| `protocol.py` | v1alpha2 request schemas, limits, effects, outcomes and errors |
| `runtime.py` | Environment binding and routing to services |
| `admission.py` | exact project identity and consent boundary |
| `foundation.py` | admission, validation, trace and read-only provider catalog |
| `lifecycle.py` | Run/Task creation, observation, reconciliation and cancellation |
| `coordination.py` | dispatch, messages, retries and close behavior |
| `orca_provider.py` | exact public-provider adapter and owned-resource cleanup |
| `trace_store.py`, `journal.py`, `content_store.py` | durable local evidence and protected content |

## Tool surface

- Project: `project_admit`, `project_inspect`.
- Swarm lifecycle: `swarm_validate`, `swarm_start`, `swarm_status`, `swarm_dispatch`, `swarm_message`, `swarm_reconcile`, `swarm_retry`, `swarm_cancel`, `swarm_close`, `swarm_trace`.
- Read-only provider catalog: `orca_search`, `orca_describe`, `orca_call`.

`orca_call` returns a validated read-only command plan; it does not execute that plan. Mutable lifecycle work goes through the typed swarm tools.

## Invariants

- One admitted absolute project root produces one authoritative `project_id`.
- A complete immutable manifest is validated before a Run starts.
- `swarm_start` creates Run/Task state but does not dispatch a worker.
- Model/provider execution requires separate dispatch authority.
- IDs returned for projects, Runs, Tasks, Dispatches and operations are never substituted.
- Unknown start effects use `swarm_reconcile`; unknown dispatch effects are not blindly retried.
- Messages use coordinator or admitted Dispatch identities.
- Cancellation acknowledgement is not cleanup proof.
- Closure fails while active work or attempt-owned survivors remain.
- Retired Olympus/ACP/Harmonia paths are never fallback.

## Local state

Installation artifacts live under `home/.aether-mcp`; durable service state lives under `home/.aether-mcp-state`. Both are machine-local and ignored by Git. The installer writes an explicit MCP registration into the live Hermes config and maintains rollback material before changing it.

## Current limitation

The installed surface and deterministic tests prove the control contract, but do not by themselves accept unrestricted model-backed production operation. The current release status remains authoritative for that gate.
