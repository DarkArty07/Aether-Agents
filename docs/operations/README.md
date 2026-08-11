# Operations

## Read-only status

```bash
make runtime-status
```

Expected current identity: `0.23.0.dev0`, enabled registration, provider ready and 15 tool names.

## Installed-runtime doctor

```bash
make runtime-doctor
```

The doctor checks installation hashes, provider readiness, state permissions and resource inventory. Run it when Aether MCP sessions are quiescent. An active owned process is returned as a stale-resource finding; do not kill an unknown process or delete state merely to obtain a green result.

## Source checks

```bash
make doctor
PYTHONPATH=src python -m pytest tests/aether_mcp -q
python -m ruff check src scripts tests
python -m compileall -q src scripts
```

## Disable and rollback

Disable registration without deleting installation state:

```bash
python scripts/aether_mcp/activate.py --hermes-home "$PWD/home" --disable
```

Restore the recorded pre-installation boundary:

```bash
python scripts/aether_mcp/rollback.py --hermes-home "$PWD/home"
```

These are mutable operations. Preserve current status and confirm the exact Hermes home first.

## Incident rules

1. Capture the typed error and exact operation/Run identities without secrets.
2. Inspect status before retrying a mutable operation.
3. Reconcile only the supported uncertain `swarm_start` boundary.
4. Cancel/fence owned work when authorized, then verify survivors.
5. Roll back when the installed boundary is inconsistent and repair cannot be proven.
6. Never use a retired private handler or delete databases as a shortcut.

## Backups

Back up live config and state with owner-only permissions. Do not add runtime archives to the repository. Test restore procedures against a separate target, never over the active state root.
