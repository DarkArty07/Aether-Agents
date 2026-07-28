# Technical Reference

> **Status:** STRUCTURE CURRENT; factual refresh pending

Reference documentation is exact and lookup-oriented. It should mirror executable contracts and be validated against source or runtime output.

## Planned reference set

| Document | Purpose |
|---|---|
| `OLYMPUS_TOOLS.md` | Public MCP tools, actions, parameters, outputs, and errors |
| `CONFIGURATION.md` | Supported configuration keys and resolution behavior |
| `ENVIRONMENT.md` | Environment variables, scope, and secret-handling rules |
| `COMMANDS.md` | Wrappers, scripts, Make targets, and CLI entry points |
| `PROJECT_LAYOUT.md` | Repository and runtime directory layout |
| `DAIMON_PROFILES.md` | Profile names, role metadata, and invocation mode |
| `COMPATIBILITY.md` | Python, hermes-agent, ACP/MCP, platform, and provider compatibility |

## Reference rules

- Generate or verify contracts from source where possible.
- Include version applicability.
- Prefer tables and schemas over narrative tutorials.
- Never publish real credentials, tokens, account labels, or private runtime paths.
- Mark experimental tools and actions explicitly.
