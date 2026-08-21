# Reproducible Aether policy hooks

`aether_pre_tool_policy.py` is the canonical, sanitized source for the fail-closed
pre-tool policy installed in the Morfeo, Supervisor, and Implementer Hermes
profiles. The script derives its role from its installed path, so the same bytes
must be installed for all three profiles.

The canonical source contains policy only. It contains no credentials, sessions,
memories, profile configuration, databases, logs, or other runtime state.

## Verify an installation

```bash
python3 scripts/sync_policy_hooks.py check --home "$HERMES_HOME"
```

The command exits `0` only when all three installed files match the canonical
bytes and executable mode. It exits `1` and reports per-profile hashes when a
copy is missing or has drifted.

## Install or update

Choose a new, non-existent backup directory and run:

```bash
backup="$PWD/.aether/backups/policy-hooks-$(date +%Y%m%d-%H%M%S)"
python3 scripts/sync_policy_hooks.py install \
  --home "$HERMES_HOME" \
  --backup-dir "$backup"
python3 scripts/sync_policy_hooks.py check --home "$HERMES_HOME"
```

Installation performs these bounded operations only:

1. validates that every destination remains beneath the selected Hermes home;
2. backs up all existing hook bytes, modes, and hashes;
3. atomically writes the canonical bytes to the three hook targets;
4. sets executable mode `0755` and verifies parity.

It does **not** edit profile configuration, accept hooks, activate profiles,
start or stop services, reload a gateway, or make network calls. Those are
separate effects and require their own authority when needed.

Do not edit installed copies. Update the canonical source, run the tests, then
install it explicitly:

```bash
python3 -m unittest discover -s tests -p 'test_policy_hooks.py' -v
```

## Roll back

Use the same backup directory produced by installation:

```bash
python3 scripts/sync_policy_hooks.py restore \
  --home "$HERMES_HOME" \
  --backup-dir "$backup"
```

Rollback restores the exact previous bytes and file modes, or removes a hook
that did not exist before installation. It refuses to overwrite an installed
copy whose hash changed after the backup, preventing silent loss of later work.
The backup remains available for audit after restoration.

## Clean-clone reconstruction

A clean clone needs only Python 3.11 or newer:

```bash
python3 -m unittest discover -s tests -p 'test_policy_hooks.py' -v
python3 scripts/sync_policy_hooks.py install \
  --home "/path/to/aether-hermes-home" \
  --backup-dir "/path/to/new-backup-directory"
```

No local `home/` content is required to reconstruct the approved hook policy.
