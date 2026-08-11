# Architecture Documentation

> **Status:** TARGET SWARM DESIGN CURRENT; EXECUTION NOT IMPLEMENTED OR ACTIVATED

Architecture documentation explains how approved product intent is realized technically. It must distinguish the active system from experimental or target designs.

## Architecture set

| Document | Purpose |
|---|---|
| `SYSTEM_CONTEXT.md` | Users, external systems, trust boundaries, and system responsibilities |
| `SYSTEM_OVERVIEW.md` | Components and runtime topology |
| [`AETHER_MCP.md`](./AETHER_MCP.md) | Accepted detailed design for MCP-first Hermes control, compact semantic trace, protected learning episodes/dataset lineage, explanation, measurement and the Orca-provider boundary; bounded integration is implemented through M5.4 while the installed surface remains default-off with zero callable tools |
| [`ORCHESTRATION.md`](./ORCHESTRATION.md) | Approved target flow from user intent through Hermes, Orca, workers, review, acceptance, and cleanup; not an active runtime claim |
| [`DAIMONS.md`](./DAIMONS.md) | Approved target roster, archetypes, authority, lifecycle, participation policy, and non-goals |
| `RUNTIME_SUBSTRATE.md` | Accepted execution substrate, lifecycle, isolation, recovery, and cleanup after PDR-0011 gates pass |
| `CONTINUITY.md` | `.aether` capture, intentional state, curation, and injection |
| `CONFIGURATION_MODEL.md` | Project/profile isolation, templates, environment, and resolution |
| `DATA_MODEL.md` | Durable stores, ownership, retention, and consistency |
| `SECURITY_MODEL.md` | Permissions, credentials, trust boundaries, and threat assumptions |
| [`EXPERIMENTAL_COORDINATION.md`](./EXPERIMENTAL_COORDINATION.md) | Historical coordination-maintenance baseline; current retirement evidence lives under v0.22.0 |

## Current boundary

The v0.22.0 repository still tracks six specialist profile directories, but no
registered runtime invokes any of them. PDR-0013 defines a smaller target roster:
Hefesto, Daedalus, and Ictinus are retained; Ariadna is conditional and disabled;
an Independent Verifier is proposed but unimplemented; Athena and Etalides have
target retirement disposition. The physical profile inventory will not change
until a separately authorized implementation cut.

PDR-0012 governs the preserved Hermes–Orca ownership boundary. PDR-0013 governs
the swarm roster and personality model. Amended PDR-0014 places bounded
integration in v0.22.0; production dogfooding, MCP learning, and tool-surface
optimization in v0.23.0; and preserves gradual workflow migration as an
inactive proposal requiring a later explicit owner decision. ADR-0001
supersedes the prior CLI-first assumption and approves an Aether MCP control and
trace plane between Hermes and Orca. The trace primarily supports system
learning/refinement and future
fine-tuning evidence; audit is secondary. The detailed MCP/learning contracts
remain separately gated. Decision approval alone does not implement, register,
or activate a runtime; the executed v0.23.0 installation and its incomplete
production-entry state are recorded in release evidence and status.

## Architecture rules

1. Product documents define why; architecture defines how.
2. Current and target diagrams must never be combined without labels.
3. Every authority boundary names its owner and failure behavior.
4. Public contracts and internal implementation details are documented separately.
5. Major changes require a durable decision record and explicit supersession.
6. Experimental architecture must remain visibly default-off until validated and activated.
