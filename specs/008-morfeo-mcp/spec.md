# Morfeo MCP

## Status

Issue: #515.

Owner-authorized objective. `1.0.0rc9` reads schema 4 and schema 5. The local
rc11/rc12 bridges keep that reader and the role-aware profile inventory check.
`1.0.0rc13` is the source candidate that emits schema 5 and serves Morfeo MCP.
Source alone is not activation.

## Decision

An MCP-capable external model may enact the Morfeo role through the canonical
managed Morfeo profile. This does not create a fourth Aether role, a second
Morfeo profile, or a new inter-role transport. The external model is an
execution host for Morfeo's role context and tool surface; authority remains
the Morfeo role's authority.

Kanban remains the inter-role transport. MCP remains an outward integration
surface. Context7 and other configured MCP servers are not federated.

Native Morfeo chat delegation may return asynchronously into its conversation;
external MCP delegation returns synchronously because the external host has no
Hermes conversation injection channel.

## Bridge requirement

- Schema 4 stays valid and means `hermes_extras = ()`.
- Schema 5 requires `hermes.extras` with the closed allowlist `["mcp"]`.
- RC9 reads both schemas and still emits schema 4.
- A schema 5 target is installed with `uv export --frozen --no-dev --extra mcp --no-emit-project`.
- The manager does not depend on the MCP SDK.
- The Hermes fork pin stays `aed6591a69f453a1867b73628603e7b53ba40ffc`.
## RC10 and RC13

`1.0.0rc10` emits schema 5 with `hermes.extras: [mcp]` and implements `aether mcp morfeo serve`.
`1.0.0rc13` carries that surface forward onto the rc12 reader lineage.
Native Morfeo chat delegation may return asynchronously into its conversation; external MCP delegation returns synchronously because the external host has no Hermes conversation injection channel.
