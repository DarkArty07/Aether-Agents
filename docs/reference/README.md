# Technical Reference

> **Status:** STRUCTURE CURRENT; factual refresh pending

Reference documentation is exact and lookup-oriented. It should mirror executable contracts and be validated against source or runtime output.

## Current and planned reference set

| Document | Purpose |
|---|---|
| [`AETHER_MCP_CONTRACT.md`](./AETHER_MCP_CONTRACT.md) | Approved `aether.mcp/v1alpha2` 15-tool successor contract; implemented schemas remain default-off with zero callable tools |
| [`AETHER_TRACE_SCHEMA.md`](./AETHER_TRACE_SCHEMA.md) | Proposed compact append-only semantic event index, receipts, integrity, reconciliation, privacy and learning-content references; not implemented |
| [`AETHER_LEARNING_EPISODE_SCHEMA.md`](./AETHER_LEARNING_EPISODE_SCHEMA.md) | Proposed protected replayable episodes, content fidelity/redaction, labels, dataset curation, lineage and local export contract for system refinement and future fine-tuning; not implemented |
| `RUNTIME_CONTRACTS.md` | Public execution contracts, actions, outputs, and errors after a replacement runtime is accepted |
| `CONFIGURATION.md` | Supported configuration keys and resolution behavior |
| `ENVIRONMENT.md` | Environment variables, scope, and secret-handling rules |
| `COMMANDS.md` | Wrappers, scripts, Make targets, and CLI entry points |
| `PROJECT_LAYOUT.md` | Repository and runtime directory layout |
| `DAIMON_PROFILES.md` | Profile names, role metadata, and invocation mode |
| `COMPATIBILITY.md` | Python, Hermes Agent, MCP, platform, and provider compatibility |

## Reference rules

- Generate or verify contracts from source where possible.
- Include version applicability.
- Prefer tables and schemas over narrative tutorials.
- Never publish real credentials, tokens, account labels, or private runtime paths.
- Mark experimental tools and actions explicitly.
