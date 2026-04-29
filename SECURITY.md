# Security Model — Aether Agents

## Permission Auto-Approve (MVP)

Olympus currently **auto-approves all permission requests** from Daimons. This means:

- Any Daimon can execute any terminal command, write to any file, or access any network resource that hermes-agent grants
- There is no human-in-the-loop for permission decisions
- All auto-approvals are logged with WARNING level: agent name, permission type, description, and session ID

### Risk Assessment

| Permission Type | Risk Level | Current Mitigation |
|----------------|------------|-------------------|
| Terminal commands | High | Logged only |
| File writes | Medium | Logged only |
| Network requests | Medium | Logged only |
| Environment access | Low | Logged only |

### Production Recommendations

Before deploying Aether Agents in production:

1. **Replace auto-approve with allowlist:** Define which permissions each Daimon role can receive without approval (e.g., Hefesto can write to project directories but not ~/.bashrc)
2. **Add HITL for dangerous permissions:** Terminal commands, file writes outside project root, and network requests to unknown domains should require explicit approval
3. **Rate-limit permissions:** Prevent Daimons from flooding the permission system
4. **Audit log:** Store all permission decisions (approved/denied) in a persistent log file

### Architecture Note

Permission requests flow through the ACP protocol. When a Daimon (running as a hermes-agent process) encounters an action requiring permission, it sends a request through the ACP connection. Olympus (the MCP server) receives this request and currently responds with "approved" automatically.

The permission system is designed to be extended with:
- Per-Daimon permission policies
- Allowlist/denylist configurations
- Human approval workflows (similar to workflow HITL)

## Daimon Process Isolation

Daimons run as separate hermes-agent processes. Each Daimon:
- Has its own HERMES_HOME pointing to its profile directory
- Has its own .env file with API keys
- Has its own set of toolsets (defined in config.yaml)
- Cannot access other Daimons' environments

However, all Daimons share the same:
- System Python and pip packages
- Network access
- Filesystem access (within HERMES_HOME boundaries)
