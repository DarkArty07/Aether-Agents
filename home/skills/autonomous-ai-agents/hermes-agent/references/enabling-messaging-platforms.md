# Enabling Messaging Platforms on the Gateway

How to enable a messaging platform (Telegram, Discord, etc.) on an already-running Hermes gateway.

## Prerequisites

- Gateway service installed and running: `systemctl --user status hermes-gateway.service`
- `.env` file at `$HERMES_HOME/.env` (loaded via `EnvironmentFile=` in the systemd override)
- `config.yaml` has a platform section (e.g., `telegram:`) — it usually exists by default

## Step-by-Step (Telegram Example)

### 1. Verify the bot token is valid BEFORE configuring

```bash
curl -s "https://api.telegram.org/bot<TOKEN>/getMe" | python3 -m json.tool
# Must return {"ok": true, "result": {"id": ..., "username": "...", ...}}
```

If this fails, the token is wrong — don't proceed. Get a fresh token from @BotFather.

### 2. Check for webhook conflicts

```bash
curl -s "https://api.telegram.org/bot<TOKEN>/getWebhookInfo" | python3 -m json.tool
# If "url" is non-empty, clear it:
curl -s "https://api.telegram.org/bot<TOKEN>/deleteWebhook"
```

Telegram can't do both polling and webhook. If a webhook is set, the gateway's polling will silently receive zero updates.

### 3. Add the token to `.env` (NOT config.yaml)

Append to `$HERMES_HOME/.env`:
```
TELEGRAM_BOT_TOKEN=<full-token>
```

**Never use `hermes config set`** — it rewrites the entire config.yaml and can destroy custom blocks. Edit `.env` manually.

### 4. Configure user access

For initial setup / testing, allow all users:
```
GATEWAY_ALLOW_ALL_USERS=true
```

Once you have the user's Chat ID (see step 6), lock it down:
```
TELEGRAM_ALLOWED_USERS=<chat_id>
```

And remove `GATEWAY_ALLOW_ALL_USERS=true` (or set to `false`).

### 5. Restart the gateway

```bash
systemctl --user restart hermes-gateway.service
```

### 6. Verify connection — use gateway.log, NOT journalctl

**Critical diagnostic insight:** After a gateway restart, the NEW process's logs may NOT appear in `journalctl` immediately. The old process's shutdown logs dominate the journal output. Instead, check the file-based log:

```bash
tail -20 $HERMES_HOME/logs/gateway.log
```

Look for these confirmation lines:
```
INFO gateway.platforms.telegram: [Telegram] Connected to Telegram (polling mode)
INFO gateway.run: ✓ telegram connected
INFO gateway.run: Gateway running with 1 platform(s)
```

If you see `WARNING gateway.run: No messaging platforms enabled`, the token wasn't loaded. Check:
- `.env` actually has `TELEGRAM_BOT_TOKEN=` (verify with `grep TELEGRAM $HERMES_HOME/.env`)
- The systemd override has `EnvironmentFile=$HERMES_HOME/.env` (check `~/.config/systemd/user/hermes-gateway.service.d/override.conf`)
- The gateway process was restarted AFTER adding the token (PID must have changed)

### 7. Discover the user's Chat ID

Two methods:

**Method A — from Telegram API (before gateway is running):**
```bash
# User sends a message to the bot first, then:
curl -s "https://api.telegram.org/bot<TOKEN>/getUpdates" | python3 -m json.tool
# Look for result[].message.chat.id
```

**Method B — from gateway.log (after gateway is running):**
```bash
# User sends a message to the bot, then:
grep "inbound message" $HERMES_HOME/logs/gateway.log | tail -1
# Example: "inbound message: platform=telegram user=Arty chat=5275738997 msg='hola'"
# Chat ID is the number after chat=
```

### 8. Lock down access (replace open mode)

Once you have the Chat ID, edit `.env`:
```
# Remove or comment out:
# GATEWAY_ALLOW_ALL_USERS=true

# Add:
TELEGRAM_ALLOWED_USERS=<chat_id>
```

Restart the gateway again.

## Platform-Specific Environment Variables

| Platform | Env Var | Notes |
|----------|---------|-------|
| Telegram | `TELEGRAM_BOT_TOKEN` | From @BotFather |
| Telegram | `TELEGRAM_ALLOWED_USERS` | Comma-separated Chat IDs |
| Discord | `DISCORD_BOT_TOKEN` | From Discord Developer Portal |
| WhatsApp | `WHATSAPP_*` | Depends on backend (Baileys, etc.) |

## Common Failure: "No messaging platforms enabled"

This warning in the startup log means the gateway didn't find any platform credentials. The cause is almost always one of:

1. **Token not in `.env`** — the `telegram:` section in config.yaml exists but is just settings (reactions, allowed_chats), not the token. The token MUST be in `.env`.
2. **`.env` not loaded by systemd** — the gateway service needs `EnvironmentFile=` in its override.conf pointing to the `.env` file. Without it, env vars work in shell tests but not under systemd.
3. **Gateway not restarted** — the old process still has the old (tokenless) environment. The PID must change.

## Delegation Pattern

This task is straightforward enough to delegate to Hefesto:
- CONTEXT: gateway running, platform section exists in config.yaml, no token in .env
- TASK: add token + GATEWAY_ALLOW_ALL_USERS to .env, restart gateway, verify
- CONSTRAINTS: do NOT touch config.yaml, do NOT use `hermes config set`
- VERIFY: check gateway.log for "Connected to Telegram (polling mode)"
