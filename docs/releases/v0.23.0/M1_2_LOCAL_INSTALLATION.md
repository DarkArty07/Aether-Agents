# M1.2 local installation

`scripts/aether_mcp/setup.py` creates one named, local Aether MCP installation
under `HERMES_HOME/.aether-mcp`. It verifies the frozen Orca AppImage digest,
uses a non-editable `uv` virtual environment, extracts the versioned public CLI,
and registers only `mcp_servers.aether_mcp` with `enabled: false`.

```bash
python scripts/aether_mcp/setup.py \
  --project-root "$PROJECT_ROOT" --hermes-home "$HERMES_HOME" \
  --appimage /absolute/path/Orca-1.4.167.AppImage \
  --profile-root /absolute/path/orca-profile \
  --repo-selector "path:$PROJECT_ROOT" --base-ref main \
  --coordinator-handle term-example
python scripts/aether_mcp/status.py --hermes-home "$HERMES_HOME"
python scripts/aether_mcp/doctor.py --hermes-home "$HERMES_HOME"
```

The commands never enable the registration. `rollback.py` restores the original
configuration byte-for-byte when it remains unchanged, or removes only the
attempt-owned entry if unrelated configuration changed; it leaves project data
and historical `.aether` evidence untouched.
