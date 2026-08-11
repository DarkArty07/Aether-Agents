# Aether MCP contract

Protocol: `aether.mcp/v1alpha2`. Transport: local stdio. Current tool count: 15.

| Tool | Primary behavior | Intended effect |
|---|---|---|
| `project_admit` | bind one exact trusted local project | append-only admission |
| `project_inspect` | freshly verify admission | read-only |
| `swarm_validate` | validate manifest, DAG, authority and provider binding | read-only |
| `swarm_start` | create Run and Tasks; no worker dispatch | local reversible |
| `swarm_status` | inspect state or bounded-wait | read-only |
| `swarm_dispatch` | dispatch ready admitted Tasks | declared authorized effect |
| `swarm_message` | message admitted participants | local reversible |
| `swarm_reconcile` | observe/fence uncertain `swarm_start` | read or local reversible |
| `swarm_retry` | retry one terminal fixture Dispatch | local reversible |
| `swarm_cancel` | cancel/fence Dispatch, Task or Run | local reversible |
| `swarm_close` | close and clean proven owned resources | declared cleanup effect |
| `swarm_trace` | query or append decision/evidence | read or append-only |
| `orca_search` | search public read-only provider commands | read-only |
| `orca_describe` | load one command schema | read-only |
| `orca_call` | validate and return argv plan; never execute | read-only |

## Common envelope rules

Requests are bounded by 65,536 bytes, arrays by 256 items, strings by 8,192 bytes and nesting by 16 levels. Successful responses carry request/operation identity, effect, outcome and result. Errors use stable codes and safe messages; secret request values are not reflected.

Mutable calls require fresh operation metadata unless an exact byte-equivalent idempotent replay is documented. `DELIVERY_UNKNOWN` and `RECONCILIATION_REQUIRED` are not success and must not trigger blind repetition.

Read the full description and generated input schema returned by `tools/list` before constructing a call. The description states preconditions, effects, next action, forbidden use and retry behavior.
