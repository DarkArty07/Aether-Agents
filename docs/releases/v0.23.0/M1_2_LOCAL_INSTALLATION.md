# M1.2 local installation

`scripts/aether_mcp/setup.py` creates one named, local Aether MCP installation
under `HERMES_HOME/.aether-mcp` and preserves state/evidence under the separate
`HERMES_HOME/.aether-mcp-state` root. It verifies the frozen Orca AppImage digest,
uses a non-editable `uv` virtual environment, extracts the versioned public CLI,
and registers only `mcp_servers.aether_mcp` with `enabled: false`.

```bash
python scripts/aether_mcp/setup.py \
  --project-root "$PROJECT_ROOT" --hermes-home "$HERMES_HOME" \
  --appimage /absolute/path/Orca-1.4.167.AppImage \
  --profile-root /absolute/path/orca-profile --profile-id default \
  --repo-selector "path:$PROJECT_ROOT" --base-ref main \
  --coordinator-handle term-example
python scripts/aether_mcp/status.py --hermes-home "$HERMES_HOME"
python scripts/aether_mcp/doctor.py --hermes-home "$HERMES_HOME"
python scripts/aether_mcp/activate.py --hermes-home "$HERMES_HOME"
```

The qualified provider layout is `<profile-root>/hermes-home` plus
`<profile-root>/xdg/{config,cache,data,state}`. Setup never enables the
registration or starts a worker; activation is a separate atomic toggle.

Rollback restores the original
configuration byte-for-byte when it remains unchanged, or removes only the
attempt-owned entry if unrelated configuration changed; it removes only the
registration, wrapper, venv and extraction payload, preserving the separate
state/evidence root, project data and historical `.aether` evidence. It first
disables future launches, inventories exact installation-path processes, then
uses TERM followed by bounded KILL only for those owned processes; shared Orca
provider processes and foreign processes are never terminated. Doctor reports
an inventory failure as `UNKNOWN` and does not return an OK result in that case.

Active Aether registration, activation, reload, and production worker execution
remain outside this local installation procedure.

## Acceptance evidence

`M1_2_ACCEPTANCE.md` accepts exact technical candidate
`0debf07db3601a14c88262d741727e5a527f3444`. The detached, non-editable
candidate passed 204 subsystem tests, Ruff, compileall and the complete isolated
sequence against Orca `1.4.167`. The active Aether runtime configuration remained
byte-for-byte unchanged, the active parser found no `aether_mcp` registration,
and exact-path inventory found no residual installation-owned process or
payload.
