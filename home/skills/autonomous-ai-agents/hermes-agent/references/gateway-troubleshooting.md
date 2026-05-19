# Gateway Troubleshooting Reference

## Case Study: Bot Connected but Not Processing Messages (May 2026)

### Symptom
Gateway logs show `[Telegram] Connected to Telegram (polling mode)` and `gateway_state.json` reports `state: "connected"`, but zero inbound messages are processed. `active_agents: 0`. No errors in any log file.

### Root Cause
**Secret redaction corrupted the `.env` token.** Hermes-agent's `security.redact_secrets: true` feature writes the display format (`869628...YFCo` with literal `...`) back to the `.env` file, replacing the real 46-character token `8696283156:AAGeI6yOKJhsxENjW6Yi4nARSB18CGrYFCo` with a 13-character truncated version.

The profile `.env` (`~/.prometeo/profiles/prometeo/.env`) had the correct token, but the root `.env` (`~/.prometeo/.env`) had the corrupted value. When both exist, the root `.env` is loaded first and the profile `.env` may not override it fully.

### Diagnostic Methodology (in order)

1. **`hermes -p <profile> gateway status`** — revealed "Telegram startup failed: The token `869628...YFCo` was rejected by the server" on the DEFAULT profile service. First indication the token was wrong.

2. **`hermes -p <profile> doctor`** — revealed config version mismatch (v14 → v23, 9 versions behind) and missing auth providers.

3. **`xxd` verification** — Confirmed corruption:
   - Root `.env` line 40: `EN=869628...YFCo` (hex `2e2e2e` = literal dots, 13 bytes real token data)
   - Profile `.env` line 44: `EN=8696283156:AAGeI6yOKJhsxENjW6Yi4nARSB18CGrYFCo` (full 46-char token)

4. **Telegram API direct verification** — Confirmed the real token works:
   ```
   curl https://api.telegram.org/bot<TOKEN>/getMe  → {"ok":true,...}
   curl https://api.telegram.org/bot<TOKEN>/getWebhookInfo  → url:"" (no webhook conflict)
   curl https://api.telegram.org/bot<TOKEN>/getUpdates?offset=-1&limit=1  → {"ok":true,"result":[]}
   ```

5. **Log inspection** (last resort) — `gateway.log`, `agent.log`, `errors.log` showed no errors, which was misleading. The gateway connected but polling returned zero updates because the token used at runtime was corrupted.

### Fix
1. Restore the full token in root `.env` from the profile `.env` (or from BotFather)
2. Run `hermes -p <profile> config migrate` to update config version
3. Restart: `systemctl --user restart hermes-gateway-<profile>.service`
4. Verify: check `gateway.log` for "Connected" and send a test message

### Prevention
- **Never edit `.env` while `security.redact_secrets: true`** — the agent may write redacted output back to the file. If you must edit `.env`, temporarily set `security.redact_secrets: false` in `config.yaml`, restart, edit, then re-enable.
- **Keep a backup of `.env`** — the real token is available from `@BotFather` on Telegram if lost.
- **Check both `.env` files** — hermes-agent has a root `.env` and profile `.env`. Both are loaded. A corrupted root value can shadow a correct profile value.
- **Use `hermes gateway status`** as your first diagnostic — it reveals token rejection and connection state that logs may not show.

## Other Gateway Failure Patterns

### Systemd PATH Pitfall
MCP servers using `npx` fail with `ENOENT spawn sh` because systemd doesn't inherit the user's shell PATH. Fix: add standard Linux directories (`/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin`) at the start of the `Environment="PATH=..."` in the service file.

### Config Version Mismatch
After a pip upgrade, `config.yaml` may be several versions behind. Run `hermes config migrate` to update. The `hermes doctor` command reports the version gap.

### Multiple Bots / Multiple Services
When running more than one Telegram bot on the same machine (e.g., a personal assistant on `-p prometeo` and the orchestrator on the default profile), each gets its own systemd service: `hermes-gateway.service` (default profile, no `-p`) and `hermes-gateway-<profile>.service` (named profiles). Always check the correct service:

```bash
hermes gateway status           # Default profile
hermes -p prometeo gateway status  # Named profile
```

**Reserved profile name `hermes`:** A service file named `hermes-gateway-hermes.service` that uses `-p hermes` will fail because `hermes` is a reserved profile name (`hermes profile alias hermes` errors with "reserved name"). Use the default profile (no `-p` flag) instead. If a stale `-p hermes` service exists, delete it and create/enable the default service:
```bash
systemctl --user disable hermes-gateway-hermes.service
systemctl --user enable hermes-gateway.service
systemctl --user start hermes-gateway.service
```

**Token shadowing across `.env` files:** Each profile has its own `.env` (root `$HERMES_HOME/.env` and `$HERMES_HOME/profiles/<name>/.env`). The root `.env` is loaded first. If the same variable exists in both, the root value may shadow the profile value. This means a corrupted token in the root `.env` breaks ALL profiles, even if their profile-specific `.env` has the correct token. Always check both files when diagnosing token issues.

### Webhook Conflict
If `getWebhookInfo` returns a non-empty `url`, Telegram sends updates to that webhook instead of long-polling. Clear with:
```bash
curl -s "https://api.telegram.org/bot<TOKEN>/deleteWebhook"
```

### Session Reset Causing Unwanted Messages on Restart
By default, `session_reset.mode: both` causes the gateway to auto-resume the last session AND send a "new session" greeting message to the user every time the gateway process restarts. On Telegram, this means the bot sends an unsolicited message on every `systemctl restart`, server reboot, or process restart.

**Symptom:** User receives a "New session" or greeting message from the bot after a system restart, cron job restart, or manual `systemctl --user restart hermes-gateway`.

**Root cause:** `session_reset.mode: both` resumes the last session and sends a session-start message. This is useful for CLI but noisy for always-on messaging platforms.

**Fix:** Set `session_reset.mode: none` for messaging platforms:
```bash
hermes config set session_reset.mode none
systemctl --user restart hermes-gateway-<profile>.service
```

**Mode reference:**
- `none` — no auto-resume, no greeting (recommended for Telegram/Discord/Slack)
- `idle` — resume only if last message was > `idle_minutes` ago (default 1440 min)
- `daily` — resume once per day at `at_hour` (default 4 AM)
- `both` — always resume on restart (default, noisy on messaging platforms)