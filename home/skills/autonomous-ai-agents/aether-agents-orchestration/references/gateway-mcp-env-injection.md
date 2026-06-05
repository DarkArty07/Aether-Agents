# Gateway MCP Environment Variable Injection

**Date discovered:** 2026-06-05
**Severity:** High — silent failure, breaks any MCP server that requires API keys
**Status:** Fixed in Aether-Agents main via drop-in override

## The Problem

`hermes-gateway.service` runs as a systemd user service. By default, the unit file in `home/` only injects three environment variables:
- `PATH` (for finding executables)
- `VIRTUAL_ENV` (for the Python venv)
- `HERMES_HOME` (for finding Aether config)

It does NOT load `home/.env`. Therefore:
- `OPENCODE_API_KEY` — unavailable to MCP servers
- `OPENCODE_GO_API_URL` — unavailable
- Any future API key added to `.env` — unavailable

The gateway runs, MCP servers start, but any LLM-dependent operation fails with 401/403 or auth errors. **The failure is silent** — the MCP server doesn't crash, it just returns empty/garbage data.

## The Diagnostic Chain (3 steps)

When a tool that worked from shell suddenly fails from the gateway:

1. **Verify the env var IS in the shell:**
   ```bash
   grep -E "OPENCODE_API_KEY" home/.env
   ```
   Should show a real key (or `***` placeholder if terminal redacts it).

2. **Verify it's NOT in the gateway process env:**
   ```bash
   GW_PID=$(systemctl --user show -p MainPID hermes-gateway.service | cut -d= -f2)
   cat /proc/$GW_PID/environ | tr '\0' '\n' | grep -E "OPENCODE|GRAPHIFY"
   ```
   Empty = bug confirmed.

3. **Shell smoke test passes, gateway smoke test fails =** this is the bug. Fix it.

## The Fix (Drop-in Override)

The cleanest, repo-update-proof fix:

```bash
mkdir -p ~/.config/systemd/user/hermes-gateway.service.d
cat > ~/.config/systemd/user/hermes-gateway.service.d/override.conf <<'EOF'
[Service]
EnvironmentFile=/home/prometeo/Aether-Agents/home/.env
EOF
systemctl --user daemon-reload
systemctl --user restart hermes-gateway.service
```

Verify:
```bash
GW_PID=$(systemctl --user show -p MainPID hermes-gateway.service | cut -d= -f2)
cat /proc/$GW_PID/environ | tr '\0' '\n' | grep OPENCODE
```

Should now show `OPENCODE_API_KEY=...` and `OPENCODE_GO_API_KEY=...`.

## Why Drop-in Instead of Editing the Unit File

- **Survives `git pull`** — the override lives in `~/.config/systemd/user/`, not in the repo
- **Survives `setup.sh` re-runs** — the override is not touched by repo scripts
- **Idempotent** — re-running the fix is harmless
- **Convention** — this is the standard systemd pattern for local customizations

If you edit the unit file directly (`hermes-gateway.service` in `home/`), your fix gets wiped on the next release that touches that file.

## Why NOT Hardcode Keys in the Unit File

```ini
# DO NOT DO THIS:
[Service]
Environment=OPENCODE_API_KEY=sk-agI7iwG73HxhsKPpcc8HDVp1sxNlpyYmwYopVdsgL6AuNNoKBk589LNUSMoVRlgf
```

Problems:
- Key is in `git log` forever (if committed)
- Rotation requires editing the unit file
- Insecure for multi-user systems
- Aether-Agents convention is single source of truth at `home/.env` (gitignored)

## Alternative Fix (If Drop-in Is Not Available)

Add to `scripts/start-gateway.sh` before the `exec`:

```bash
if [ -f /home/prometeo/Aether-Agents/home/.env ]; then
    set -a
    source /home/prometeo/Aether-Agents/home/.env
    set +a
fi
```

This is slightly less clean because it requires modifying the repo script, but it works when drop-in isn't an option (e.g., containerized environments where `~/.config/systemd/user/` doesn't persist).

## Related Issues

- **Graphify semantic retrieval failed** with this bug — the `--backend aether-openai` flag worked from shell (because shell had `OPENCODE_API_KEY`), failed from gateway (because gateway didn't)
- **Any future MCP server that needs LLM** will hit this same bug until the fix is applied
- **The fix is permanent** — once the drop-in is in place, all future MCP servers automatically inherit `.env`

## Time Cost of Diagnosis

Approx. 10-15 minutes to:
- Notice the failure (2 min)
- Run the 3-step diagnostic chain (3 min)
- Apply the fix and restart (2 min)
- Verify the smoke test passes (3 min)

Faster if you remember the diagnostic chain.
