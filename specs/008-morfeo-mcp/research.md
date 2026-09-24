# Research

Hermes `0.20.1` at `aed6591a69f453a1867b73628603e7b53ba40ffc` already exposes
FastMCP integration points, tool definitions, the plugin manager, SessionDB,
AIAgent, and `invoke_tool`. The Morfeo MCP server can stay Aether-side.

RC8 installs Hermes with `uv export --frozen --no-dev --no-emit-project` and
does not pass `--extra mcp`. The runtime therefore has no `mcp` distribution.
RC9 teaches the reader to accept a future schema 5 lock and to export that
extra from the authenticated `uv.lock`. RC9 itself remains schema 4 so RC8 can
install it.
