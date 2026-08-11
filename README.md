# Aether Agents

Aether is a local software-production runtime built around Hermes Agent. Hermes is the user-facing technical lead; `aether-mcp` provides the admitted control and trace boundary; an exact qualified Orca provider supplies Run, Task, Dispatch, worker, message and cleanup mechanics.

Current source version: `0.23.0.dev0`. The named local runtime is installed, registered and exposes exactly 15 MCP tools. Olympus, ACPManager, Harmonia, `talk_to`, Honcho and the former native coordination kernel are not supported runtime paths.

## Current layout

```text
User
  └─ Hermes (home/SOUL.md)
       ├─ direct single-owner work
       └─ Aether MCP (15 tools)
            └─ qualified Orca provider
                 └─ admitted Runs, Tasks and workers
```

The repository is maintained from one persistent checkout on local `main`. Source, templates and canonical documentation live here; machine-local runtime state stays under `home/` and is ignored by Git. No auxiliary development worktree is required.

## Active roster

| Profile | Purpose | Policy |
|---|---|---|
| Hefesto | implementation, integration and debugging | allowed |
| Daedalus | UX, interaction and prototyping | allowed |
| Ictinus | backend, data and architecture review | allowed |

Research, security review and continuity remain Hermes responsibilities unless the owner later approves a new bounded role. The retired Ariadna, Athena and Etalides profiles are not part of the current runtime.

## Install Hermes assets

```bash
bash scripts/setup.sh
make doctor
```

`setup.sh` creates machine-local configuration from the tracked templates without overwriting existing secrets or live configuration. Aether MCP installation additionally requires the exact provider paths and identities documented in [Installation](docs/guides/INSTALLATION.md).

## Runtime checks

```bash
python scripts/aether_mcp/status.py --hermes-home "$PWD/home"
python scripts/aether_mcp/doctor.py --hermes-home "$PWD/home"
PYTHONPATH=src python -m pytest tests/aether_mcp -q
```

`status.py` is read-only. `doctor.py` also inventories owned processes/resources and fails when it finds stale survivors. Activation, rollback and provider qualification are explicit operations, not side effects of `make doctor`.

## Documentation

Start at [docs/README.md](docs/README.md). Runtime truth comes from source, schemas, tests and executed status evidence; historical decision records never override the current runtime contract.

## License

MIT. Hermes Agent and the qualified provider retain their own upstream licenses.
