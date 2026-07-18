# v0.19.0 Autonomous Coordination — Research

**Status:** initial evidence. Research is incomplete and no migration recommendation has been approved.

**Date:** 2026-07-18

## 1. Research objective

Evaluate protocols, frameworks, and architectural patterns that could let Aether Daimons coordinate autonomously inside a contract approved by Hermes and the user. Candidates must be assessed against Aether's current continuity, QA, specialization, observability, security, and human-governance requirements.

The first candidate is [Cotal](https://github.com/Cotal-AI/Cotal), described by its maintainers as an open standard for topology-independent agent coordination.

## 2. Cotal: verified role in the stack

Cotal is primarily a coordination and transport plane, not a complete cognitive orchestrator.

It defines:

- presence and agent identity;
- multicast channels;
- unicast instance messaging;
- anycast dispatch by role/service;
- live and durable delivery over NATS/JetStream;
- manager and process-runtime interfaces;
- ACL and credential mechanisms;
- connector surfaces for agent hosts, including Hermes.

It does not itself define:

- how user intent becomes an execution contract;
- product or architectural decision authority;
- semantic task decomposition;
- Aether QA gates;
- correctness criteria for work products;
- `.aether` continuity and curation;
- when evidence is sufficient to close a task.

Primary sources:

- [Cotal SPEC.md](https://github.com/Cotal-AI/Cotal/blob/main/SPEC.md)
- [Cotal architecture](https://github.com/Cotal-AI/Cotal/blob/main/docs/architecture.md)
- [Channels and permissions](https://github.com/Cotal-AI/Cotal/blob/main/docs/channels-and-permissions.md)

## 3. Delivery and coordination semantics

Cotal supports three addressing modes:

| Mode | Meaning | Relevant Aether use |
|---|---|---|
| Multicast | Publish to a channel | Shared project/status/review context |
| Unicast | Address one agent instance | Direct specialist collaboration |
| Anycast | Address one available instance of a role | Dynamic delegation and load balancing |

Verified delivery properties:

- live channels are at-most-once;
- durable channels, direct messages, and anycast work are at-least-once within retention limits;
- clients must deduplicate deliveries by message ID;
- no global ordering is guaranteed across routes and consumers;
- presence exposes states such as idle, waiting, working, and offline;
- attention settings influence wake/interrupt behavior but are not authorization controls.

Aether therefore could not treat message delivery as equivalent to successful work. It would need separate business acknowledgements, evidence, idempotency, and completion gates.

## 4. Hermes connector findings

Cotal contains a real Hermes connector implemented through:

- a TypeScript launcher;
- a persistent TypeScript sidecar;
- a Python Hermes platform plugin;
- Unix sockets connecting the plugin and sidecar;
- generated `cotal_*` tool descriptors;
- Hermes lifecycle hooks used to update mesh state.

Sources:

- [Connector documentation](https://github.com/Cotal-AI/Cotal/blob/main/docs/connect-hermes.md)
- [`launch.ts`](https://github.com/Cotal-AI/Cotal/blob/main/extensions/connector-hermes/src/launch.ts)
- [`sidecar.ts`](https://github.com/Cotal-AI/Cotal/blob/main/extensions/connector-hermes/src/sidecar.ts)
- [`hooks.py`](https://github.com/Cotal-AI/Cotal/blob/main/extensions/connector-hermes/plugin/cotal/hooks.py)

Current incompatibilities with Aether:

1. The connector is documented as alpha.
2. It pins Hermes Agent to the 0.16 line; Aether currently runs Hermes Agent v0.17.0.
3. It creates an isolated temporary `HERMES_HOME` instead of attaching existing persistent Aether profiles.
4. It does not preserve Aether Daimon session continuity as currently implemented through Olympus ACP.
5. It generates a profile with approvals disabled.
6. It introduces Cotal Manager as a lifecycle owner, potentially conflicting with Olympus process ownership.
7. It does not provide an Aether-specific trust boundary for promoting peer messages into agent instructions.

These are adaptation requirements, not proof that integration is impossible.

## 5. Size comparison

### Method

- Cotal checkout: commit `c378569779af1b4a0426d0b9087ff3c34349b187`.
- Aether checkout: local v0.18.2 source state on 2026-07-18.
- Tool: `pygount 3.2.0`.
- Metric: code lines, excluding comments and blank lines.
- Excluded dependencies and generated build directories such as `.git`, `node_modules`, `dist`, `build`, and caches.

### Results

| Scope | Production code | Relevant tests | Combined |
|---|---:|---:|---:|
| Olympus v3 | 3,449 | 1,096 | 4,545 |
| Cotal complete repository | 60,336 | Not isolated in this row | — |
| Cotal packages + implementations + extensions | 50,156 | Not isolated in this row | — |
| Cotal subset relevant to Aether | 11,024 | 9,464 | 20,488 |
| Cotal protocol/core | 5,555 | 5,690 | 11,245 |
| Cotal manager + delivery | 3,096 | 2,637 | 5,733 |
| Cotal connector-core + connector-hermes | 2,373 | 1,161 | 3,534 |

Derived comparison:

- the complete Cotal repository has 17.49 times the production code of Olympus v3;
- the Aether-relevant Cotal subset has 3.20 times the production code of Olympus;
- Cotal core alone has 1.61 times the production code of Olympus;
- manager plus delivery is approximately 90% of Olympus production size;
- connector-core plus connector-hermes is approximately 69% of Olympus production size;
- the connector adaptation surface including its tests is 3,534 lines, approximately the same scale as Olympus's 3,449 production lines.

## 6. Preliminary fork viability

### Full divergent fork

A deep fork would inherit roughly 60,000 lines of code across CLI, web UI, authentication, deployment, manager, delivery, multiple connectors, terminal runtimes, examples, and protocol core. This is technically possible but creates a substantial maintenance and upstream-divergence burden, especially while the protocol is still draft.

### Focused downstream fork or extension

A narrower path appears more viable:

```text
Cotal core, manager, and delivery       track upstream where possible
connector-core                          adapt only when required
connector-hermes                        adapt for current Hermes
connector-aether                        add Aether-specific contract bridge
Aether policy and continuity            remain Aether-owned
```

The initial code surface directly relevant to connector adaptation is comparable to Olympus itself rather than to the entire Cotal repository.

A focused approach could preserve upstream compatibility while adding:

- persistent `HERMES_HOME` support;
- current Hermes compatibility;
- mapping between Cotal identity and Aether Daimon/project/session identity;
- Aether contract and event schemas;
- role-aware authorization;
- idempotent task effects;
- `.aether` evidence and continuity integration;
- a single unambiguous lifecycle owner.

No fork strategy is approved yet. The role and authority model must be settled before deciding whether these changes belong in an upstream contribution, extension package, focused fork, or replacement architecture.

## 7. Security and operational risks requiring study

| Risk | Initial concern |
|---|---|
| Prompt injection through peer messages | Coordination content cannot automatically inherit instruction authority. |
| Duplicate delivery | At-least-once delivery can repeat side effects without idempotency. |
| Split lifecycle ownership | Olympus and Cotal Manager cannot both own the same process safely. |
| Role privilege drift | Lateral communication must not erase Actor/Consultant boundaries. |
| Completion ambiguity | Message acknowledgement is not evidence that work is correct. |
| Credential compromise | A valid peer identity may still represent a compromised agent. |
| History confidentiality | Replay settings are not equivalent to access control or encryption. |
| Protocol evolution | Cotal's wire specification and Hermes connector are still evolving. |
| Continuity fragmentation | Broker state, Olympus state, and `.aether` could diverge without a clear source-of-truth model. |
| Operator visibility | Autonomous interaction must remain inspectable without requiring Hermes to relay every message. |

## 8. Preliminary conclusion

Cotal addresses a genuine Aether gap: durable multi-agent presence and lateral communication without a mandatory central message relay. It is not, by itself, a replacement for Hermes's design authority, Aether's execution policy, Olympus session semantics, or `.aether` continuity.

A focused adaptation appears plausible by size. A deep migration is not yet justified. Viability depends less on raw lines of code than on authority, trust, lifecycle, idempotency, evidence, and continuity semantics.

## 9. Research still required

- Establish a verified baseline of current Olympus and `.aether` responsibilities.
- Inspect Cotal task/control schemas and lifecycle boundaries in greater depth.
- Determine whether existing Hermes profiles can be attached without Cotal-owned temporary homes.
- Evaluate upstream contribution policy and expected compatibility evolution.
- Compare Cotal with other coordination protocols/frameworks rather than anchoring on the first candidate.
- Model failure cases: duplicate work, dead agents, conflicting reviewers, partial side effects, stale contracts, and network partitions.
- Define the new coordination Daimon's role before evaluating which infrastructure best supports it.
