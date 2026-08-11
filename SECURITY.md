# Security policy

## Supported line

Security fixes target the current `0.23.x` source line. Older tags and retired Olympus/Honcho paths are unsupported.

## Runtime boundary

Aether MCP is a local stdio service. It does not grant authority merely because a tool is visible. Every mutable request must carry admitted project identity, explicit operation metadata, the expected effect and an authority reference. Provider, model, budget, publication and external side effects require their own authority.

The local runtime must preserve these controls:

- credentials remain in ignored `.env` or machine-local config files;
- `home/.aether-mcp-state` is owner-only and never committed;
- project, Run, Task, Dispatch and operation identities are not interchangeable;
- unknown mutable outcomes are inspected or reconciled before retry;
- cancellation is followed by status and survivor verification;
- closure may remove only resources proven to belong to the admitted attempt;
- trace records are secret-safe references, not raw prompts, tokens or transcripts;
- no retired Olympus/ACP/Harmonia command may serve as fallback.

`scripts/aether_mcp/doctor.py` inventories owned and provider resources. A failed stale-resource check must be investigated; it must not be hidden by deleting state or weakening the check.

## Reporting

Report a vulnerability privately to the repository owner with reproduction steps, affected version, impact and any known mitigation. Do not include real credentials, private prompts or user data in an issue, test fixture or commit.
