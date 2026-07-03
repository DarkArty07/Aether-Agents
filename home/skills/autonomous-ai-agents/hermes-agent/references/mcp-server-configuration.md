# MCP Server Configuration in hermes-agent

## Prerequisites — MCP Python SDK (REQUIRED)

**`pip install hermes-agent` does NOT install the MCP Python SDK.** The `mcp`
package is an optional dependency. Without it, ALL MCP servers fail silently:
no errors in `journalctl`, no errors in `gateway.log`, and `hermes mcp list`
misleadingly shows every server as "✓ enabled" (it only checks config syntax,
not runtime capability).

**Install the MCP extra immediately after base install:**

```bash
# Option A: MCP extras only (recommended — adds mcp SDK + dependencies)
pip install 'hermes-agent[mcp]'

# Option B: All extras (MCP + browser + other optional features)
pip install 'hermes-agent[all]'
```

**How to verify the SDK is installed:**

```bash
python -c 'import mcp; print(mcp.__version__)'
# Expected: 1.26.0 or similar
# If "ModuleNotFoundError: No module named 'mcp'" → install the extra

hermes mcp test <name>
# This is the REAL diagnostic — it attempts connection + tool discovery
# "requires the 'mcp' Python SDK" in the error = SDK missing
```

**Critical diagnostic pattern:** When ALL MCPs show as `failed` after a fresh
install or migration, check the SDK FIRST — before debugging individual MCP
configs, PATH issues, or OAuth tokens. The symptom is identical regardless of
MCP type (stdio or http): every server fails because the framework can't
initialize the MCP subsystem at all.

| Check | Command | If fails |
|-------|---------|----------|
| SDK installed | `python -c 'import mcp'` | `pip install 'hermes-agent[mcp]'` |
| MCP test works | `hermes mcp test context7` | Check error message — SDK vs network vs auth |
| List shows servers | `hermes mcp list` | Config parsing issue (check YAML syntax) |

## How to verify framework support (do not speculate)

The block `mcp_servers:` in `config.yaml` is parsed by the installed framework — not by what other configs in the repo happen to use. Before claiming "X is not supported" or "X is supported", read the actual installed code:

```bash
# Locate the mcp_tool module in the active venv
~/.prometeo/.venv-hermes/bin/python3 -c "import importlib.util, sys; \
  spec=importlib.util.find_spec('tools.mcp_tool'); \
  print(spec.origin if spec else 'NOT FOUND')"

# Or grep directly
grep -rln "mcp_servers\|streamable_http\|sse_client" \
  ~/.prometeo/.venv-hermes/lib/python*/site-packages/hermes_agent/ 2>/dev/null
```

**Pitfall (Chris's 2026-06-05 correction):** If you find 3 stdio MCPs in a config and conclude "the framework only supports stdio", you are pattern-matching instead of verifying. The `tools/mcp_tool.py:_is_http()` check is literally `"url" in self._config` — a single key decides transport. Read the code.

## Three supported transports

Confirmed in `tools/mcp_tool.py` v0.14.0 (hermes-agent) using mcp SDK v1.27.1:

### 1. Stdio (local subprocess)

```yaml
mcp_servers:
  context7:
    command: npx
    args: ["-y", "@upstash/context7-mcp"]
    enabled: true
```

### 2. HTTP / Streamable HTTP (remote, default when `url:` present)

```yaml
mcp_servers:
  magnific:
    url: "https://mcp.magnific.com/mcp"
    auth: oauth                # or omit for anonymous, or use headers: Authorization for Bearer
    enabled: true
    timeout: 180
    connect_timeout: 30
    ssl_verify: true           # default true, set false only for self-signed dev
```

**Detection:** `_is_http()` returns true iff `"url" in config`. Any `transport:` value other than `sse` is treated as Streamable HTTP.

### 3. SSE (legacy)

```yaml
mcp_servers:
  searxng:
    url: "http://localhost:8000/sse"
    transport: sse             # explicit, otherwise default is Streamable HTTP
```

## OAuth 2.1 with PKCE

For remote servers that require browser sign-in (Magnific, Notion, Linear, etc.):

```yaml
mcp_servers:
  magnific:
    url: "https://mcp.magnific.com/mcp"
    auth: oauth
    oauth:
      client_id: "pre-registered-id"   # optional, server may auto-discover
      scope: "read write"
      redirect_port: 0                  # 0 = pick free port, 8085 = fixed
```

The flow is in `tools/mcp_oauth.py` (hermes-agent). Provider cache is keyed by server name and survives gateway restart (see `mcp_oauth_manager.get_or_build_provider`).

**Headless caveat (systemd gateway):** OAuth requires opening a local browser for the PKCE redirect. If the gateway runs as `systemctl --user hermes-gateway-*.service` without a `$DISPLAY`, do the OAuth dance **once from an interactive shell** (use `hermes mcp login <name>` or `hermes mcp add`). The token is cached to disk; subsequent restarts reuse it.

### Cross-WSL OAuth flow (gateway in WSL, browser on Windows)

When hermes-agent runs inside WSL (no `$DISPLAY`, headless gateway) and you need to authorize an MCP server whose OAuth page must be opened in Chrome on Windows, the following constraints and workarounds apply:

**How the callback server works (from `tools/mcp_oauth.py`):**

1. `_configure_callback_port()` (l.512): `redirect_port: 0` → picks a random free port. Set `redirect_port: 8085` for a predictable URL.
2. `_build_client_metadata()` (l.533): redirect URI is ALWAYS `http://127.0.0.1:{port}/callback` — hardcoded, NOT configurable.
3. `_wait_for_callback()` (l.443): callback server binds to `127.0.0.1` only — NOT `0.0.0.0`. This is the WSL loopback.
4. `_redirect_handler()` (l.391): prints URL to stderr, tries `webbrowser.open()` only if `_can_open_browser()` returns True (needs `$DISPLAY` or `$WAYLAND_DISPLAY`). In WSL headless: URL goes to stderr only.
5. `_get_token_dir()` (l.101): tokens stored in `HERMES_HOME/mcp-tools/<server_name>.json`, `<server_name>.client.json`, `<server_name>.meta.json`.

**Why it still works from Windows Chrome:**

WSL2 sets up automatic localhost forwarding. When Magnific's auth server redirects the browser to `http://127.0.0.1:8085/callback`, Windows Chrome connects to this URL. WSL2 proxies the connection from Windows' `127.0.0.1:8085` to WSL2's `127.0.0.1:8085` — the callback server receives the code. This works without `netsh portproxy` or admin privileges.

**Required config fields for `hermes mcp login` to work:**

The CLI command `hermes mcp login magnific` has a guard at `mcp_config.py:614`:
```python
if server_config.get("auth") != "oauth":
    _error("Server is not configured for OAuth")
```
You MUST add `auth: oauth` to the server config even though the framework auto-detects OAuth via 401. Without it, `hermes mcp login` refuses to run.

**Complete config for a predictable, scriptable OAuth flow:**

```yaml
mcp_servers:
  magnific:
    url: "https://mcp.magnific.com/mcp"
    enabled: true
    auth: oauth
    oauth:
      redirect_port: 8085
      client_name: "My Setup (WSL)"
```

**One-time authorization procedure (do this from an interactive WSL shell, not from the agent):**

1. Run `hermes mcp login magnific` (this starts the callback server on `:8085`, prints the Magnific authorization URL).
2. Open Chrome on Windows and paste the URL, OR automate with:
   ```bash
   /mnt/c/WINDOWS/system32/cmd.exe /c start chrome "http://127.0.0.1:8085/callback"
   ```
3. Complete the authorization in Chrome — Magnific redirects back to the WSL callback server.
4. `hermes mcp login` completes, token saved to disk.
5. Verify: `ls ~/.prometeo/mcp-tools/magnific*.json` and `hermes mcp test magnific`.

**Token lifecycle:** The refresh token is saved automatically. Subsequent gateway restarts reload it. If the token expires (or the server revokes it), run `hermes mcp login magnific` again to force re-auth (it wipes the disk cache first).

**Pitfall — Cross-instance token copy does NOT work (tested 2026-06-05):** Copying the three token files (`magnific.json`, `magnific.client.json`, `magnific.meta.json`) from one WSL distro to another — even with identical `client_id`, identical `redirect_uri`, and a non-expired `access_token` — results in `hermes mcp test` rejecting the token with "MCP OAuth: authorization required". The framework's `mcp_oauth_manager` keys the provider cache by something beyond the file contents (likely session state or a server-side revocation triggered by the failed OAuth attempt on the target instance). **Do not waste time debugging copied tokens — always run fresh OAuth login per instance.**

**OAuth token debugging checklist (when `hermes mcp test` fails with "authorization required"):**

1. Check token expiry — `grep expires_at ~/.prometeo/mcp-tools/magnific.json` (Unix epoch). If expired → re-login.
2. Verify `client.json` matches between instances — `diff <source> <target>`. Mismatch → re-login on target.
3. Check TCP reachability — `timeout 3 bash -c "echo >/dev/tcp/mcp.magnific.com/443" && echo reachable || echo unreachable`. Unreachable = network issue, not token issue.
4. If 1-3 all pass but test still fails → token rejected by framework. Run fresh OAuth login. Do NOT spend more time debugging the copied token.
5. If `hermes mcp login` generates a new OAuth URL with different `code_challenge` each run → that's expected (PKCE generates fresh challenge per session). The URL is single-use; if the browser callback doesn't complete within ~40s, the attempt times out and you need a new URL.

**Script pattern (create at `~/.prometeo/bin/magnific-oauth.sh`):**

```bash
#!/usr/bin/env bash
set -euo pipefail
SERVER="${1:-magnific}"   # pass server name as arg, default "magnific"
CMD="/mnt/c/WINDOWS/system32/cmd.exe"

source "$HOME/Aether-Agents/home/.venv-hermes/bin/activate"

# Run login, capture URL from stderr, open Chrome
TEMP_LOG=$(mktemp); trap "rm -f $TEMP_LOG" EXIT
hermes mcp login "$SERVER" > "$TEMP_LOG" 2>&1 &
PID=$!

# Wait for the URL to appear in output
URL=""
for i in $(seq 1 60); do
    sleep 1
    URL=$(grep -oP 'https?://[^\s]+' "$TEMP_LOG" 2>/dev/null | head -1)
    [ -n "$URL" ] && break
done

if [ -n "$URL" ]; then
    echo "Opening: $URL"
    $CMD /c start chrome "$URL" 2>/dev/null || true
fi
wait $PID
cat "$TEMP_LOG"
```

**Verification:**

```bash
hermes mcp test magnific                          # smoke test
ls -la ~/.prometeo/mcp-tools/magnific*            # token files (NOT mcp-tokens/)
journalctl --user -u hermes-gateway-prometeo.service \
  --since "5 minutes ago" | grep -i magnific       # gateway logs
```

**⚠️ Token directory name:** The code uses `mcp-tools/` (from `_get_token_dir()` in `mcp_oauth.py`). Some docs and older setups reference `mcp-tokens/` — this is WRONG. If you create `mcp-tokens/` manually, the SDK won't find it. Always verify with `grep '_get_token_dir\|mcp-tools' $HERMES_HOME/venv/lib/python*/site-packages/hermes_agent/tools/mcp_oauth.py`.

## Bearer / header auth (alternative to OAuth)

For servers that use a static API key:

```yaml
mcp_servers:
  some_api:
    url: "https://api.example.com/mcp"
    headers:
      Authorization: "Bearer ${MY_API_KEY}"
    timeout: 180
```

Env-var interpolation (`${VAR}`) works inside string values. Define the var in the profile's `.env` (e.g. `~/.prometeo/profiles/prometeo/.env` for Prometeo, `~/Aether-Agents/home/.env` for Aether).

**Gateway env-loading pitfall:** systemd units do NOT source the profile `.env` automatically. If a smoke test from a shell works but the gateway fails with auth errors, check `/proc/$(pidof hermes-gateway)/environ` for the expected vars. If they're missing, the fix is a drop-in override:

```ini
# ~/.config/systemd/user/hermes-gateway.service.d/override.conf
[Service]
EnvironmentFile=/home/prometeo/Aether-Agents/home/.env
```

(For the `-prometeo` gateway, the override points to the Prometeo `.env`.)

## npx-based MCP cold start (context7, etc.)

MCP servers launched via `npx` (like `context7`) have a 2-5 second cold start on first invocation — `npx` must download the package if not cached. During gateway startup, the MCP health check may fire before `npx` completes, showing "context7 (stdio) — failed" in the startup output. This is **transient and self-resolving**: subsequent connection attempts succeed.

**Diagnostic pattern:**
```bash
# If context7 shows "failed" at startup but works in practice:
hermes mcp test context7  # should show ✓ Connected if the server is up
grep "context7" $HERMES_HOME/logs/mcp-stderr.log | tail -5
# Look for: "Context7 Documentation MCP Server v2.x running on stdio"
```

If `hermes mcp test context7` succeeds but the startup log shows a failure, it was a cold start timeout — no action needed.

**Mitigation options:**
1. Accept the ~3s cold start (simplest — context7 reconnects automatically on next tool call)
2. Pre-cache npx: run `npx -y @upstash/context7-mcp` once manually so the package is cached
3. Install globally: `npm install -g @upstash/context7-mcp` and change `command: context7-mcp` in config (eliminates cold start entirely, but requires manual `npm update -g` for upgrades)

## Smoke tests

```bash
# List all configured servers and their transport
hermes mcp list

# Test a single server (initialize + list tools, no LLM call)
hermes mcp test <name>

# Force tool discovery in a session
hermes mcp refresh <name>
```

If `hermes mcp` subcommand does not exist in your version, use:

```bash
~/.prometeo/.venv-hermes/bin/python3 -c "
import asyncio
from tools.mcp_tool import _load_mcp_config
cfg = _load_mcp_config()
for name, c in cfg.items():
    print(name, '->', c.get('url') or c.get('command'))
"
```

## Common URL mistakes

- Trailing slash: `https://mcp.magnific.com/` may 301; `https://mcp.magnific.com/mcp` is the real endpoint.
- Forgetting `/mcp` path: many servers expose the MCP protocol at `/mcp` on the host, not at root.
- Using `transport: sse` on a server that only speaks Streamable HTTP: results in 405 with a hint to switch transport.

## Cross-instance note

Prometeo (`~/.prometeo/`, gateway `hermes-gateway-prometeo.service`) and Aether-Agents (`~/Aether-Agents/home/`, gateway `hermes-gateway.service`) are independent hermes-agent instances with separate `config.yaml` and `.env` files. An MCP added to one is invisible to the other. The framework code is shared (same venv) but the configs are not. **Before editing a config, confirm which instance you are modifying.**
