# Architecture

The current architecture has three authorities:

1. **Hermes product layer** — intent, scope, routing, direct work and semantic acceptance.
2. **Aether MCP** — project admission, typed control operations, protocol validation and trace.
3. **Qualified provider** — Run/Task/Dispatch execution resources and cleanup.

Read [Aether MCP](AETHER_MCP.md), [Orchestration](ORCHESTRATION.md) and [Profiles](DAIMONS.md). Exact request schemas live in `schemas/aether-mcp/v1alpha2/bundle.json`; executable behavior lives in `src/aether_mcp`.

The named local runtime is installed and registered with 15 tools. Model-backed production entry remains a separate acceptance gate. The repository itself has one persistent checkout; provider-owned temporary isolation is a runtime resource, not another source-of-truth tree.
