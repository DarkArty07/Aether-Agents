# Morfeo MCP

`aether mcp morfeo serve` lets an external MCP client enact the canonical Morfeo role. The client keeps its own model. Aether supplies Morfeo's profile, project binding, memory, Kanban, plugins and tool policy. This is not a fourth role, a second Morfeo profile, or a transport between Supervisor and Implementer. Kanban remains that transport.

The manager command does not import Hermes or the MCP SDK. `serve` resolves one exact project and executes the active runtime Python.

```bash
aether mcp morfeo serve --mode harness --project /path/to/project
aether mcp morfeo serve --mode chatbot --transport streamable-http --project /path/to/project --port 8765
```

Harness mode is stdio and does not publish `terminal`, `process`, `read_file`, `write_file`, `patch`, `search_files` or `execute_code`, because the coding host already has those tools. Chatbot mode can publish them when the Morfeo profile enables them. Neither mode publishes external MCP tools such as Context7.

Call `morfeo_bootstrap` before any other tool. A second call on the same connection returns the same context revision. HTTP binds only `127.0.0.1`. The command does not open tunnels or accept provider credentials.

Source and a local tag do not prove that a live installation is serving Morfeo MCP. Activation still requires the managed rc9-then-rc10 update path.
