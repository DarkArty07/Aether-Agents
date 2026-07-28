# Operations Documentation

> **Status:** STRUCTURE CURRENT; runbooks pending

Operations documentation explains how to run, observe, maintain, recover, and safely update an Aether Agents installation.

## Planned runbook set

| Document | Purpose |
|---|---|
| `HEALTH_CHECK.md` | Installation and runtime health verification |
| `GATEWAY.md` | Gateway start, stop, status, logs, and safe restart boundaries |
| `UPDATING.md` | Update process, configuration preservation, verification, and rollback |
| `BACKUP_AND_RECOVERY.md` | Runtime state, Hermes-native memories, `.aether`, configuration, and credential-safe recovery |
| `TROUBLESHOOTING.md` | Symptom → evidence → diagnosis → safe correction |
| `HONCHO_RETIREMENT.md` | Removal of legacy Honcho configuration, data, services, docs, and hidden dependencies |
| `INCIDENTS.md` | Incident evidence, issue tracking, containment, and closeout |
| `MULTI_INSTANCE.md` | Concurrent projects, sessions, gateways, and identity correlation |

## Runbook rules

1. Commands must be executable and scoped to the intended project/profile.
2. Destructive commands require explicit warnings and recovery prerequisites.
3. Diagnose process and project identity before stopping shared services.
4. Preserve configuration, credentials, continuity, and persistent data by default.
5. Separate deterministic checks from live external-effect gates.
6. Record confirmed framework faults as issues with reproducible evidence.
