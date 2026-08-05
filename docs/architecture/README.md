# Architecture Documentation

> **Status:** STRUCTURE CURRENT; experimental coordination maintenance boundary documented

Architecture documentation explains how approved product intent is realized technically. It must distinguish the active system from experimental or target designs.

## Planned architecture set

| Document | Purpose |
|---|---|
| `SYSTEM_CONTEXT.md` | Users, external systems, trust boundaries, and system responsibilities |
| `SYSTEM_OVERVIEW.md` | Components and runtime topology |
| `ORCHESTRATION.md` | Hermes routing, decomposition, delegation, monitoring, and synthesis |
| `DAIMONS.md` | Specialist roles, authority, lifecycle, and non-goals |
| `RUNTIME_SUBSTRATE.md` | Accepted execution substrate, lifecycle, isolation, recovery, and cleanup after PDR-0011 gates pass |
| `CONTINUITY.md` | `.aether` capture, intentional state, curation, and injection |
| `CONFIGURATION_MODEL.md` | Project/profile isolation, templates, environment, and resolution |
| `DATA_MODEL.md` | Durable stores, ownership, retention, and consistency |
| `SECURITY_MODEL.md` | Permissions, credentials, trust boundaries, and threat assumptions |
| [`EXPERIMENTAL_COORDINATION.md`](./EXPERIMENTAL_COORDINATION.md) | Historical coordination-maintenance baseline; current retirement evidence lives under v0.22.0 |

## Architecture rules

1. Product documents define why; architecture defines how.
2. Current and target diagrams must never be combined without labels.
3. Every authority boundary names its owner and failure behavior.
4. Public contracts and internal implementation details are documented separately.
5. Major changes require a durable decision record and explicit supersession.
6. Experimental architecture must remain visibly default-off until validated and activated.
