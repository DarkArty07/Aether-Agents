# Daimon Configuration Changes — What Hermes Can and Cannot Do

## Golden Rule

**Only change EXACTLY what the user authorizes.** If they say "change the API key", change ONLY the API key. Do not touch model, provider, base_url, or any other field. If a broader change seems necessary, explain and ask — never decide for them.

## What Works (Hermes can do directly)

### `hermes config set` — config.yaml changes
```bash
HERMES_HOME=/home/prometeo/Aether-Agents/home/profiles/<daimon> hermes config set <key> <value>
```
This works because it's a CLI command, not a file write. Examples:
```bash
HERMES_HOME=.../profiles/hefesto hermes config set model.provider openrouter
HERMES_HOME=.../profiles/hefesto hermes config set model.default deepseek-v4-flash
HERMES_HOME=.../profiles/hefesto hermes config set model.base_url https://openrouter.ai/api/v1
```

### Read-only verification (not blocked)
```bash
grep -A6 "^model:" /path/to/profiles/<daimon>/config.yaml
awk -F= '/OPENCODE_GO_API_KEY/{print "prefix=" substr($2,1,8) " len=" length($2)}' /path/to/<daimon>/.env
```

## What Does NOT Work (blocked by Pure Orchestrator)

All of these are blocked with "Delegate. You are an orchestrator, not an implementer":
- `python -c "..."` — blocked if it writes files
- `sed -i` — blocked (writes files)
- `cat > file << EOF` — blocked (redirect writes)
- `tee file` — blocked (writes files)

## The Chicken-and-Egg Problem

When a Daimon is down (e.g., API key expired) AND Hermes can't write files:

1. Hermes can use `hermes config set` for config.yaml (CLI, not blocked)
2. Hermes CANNOT update `.env` files (all write methods blocked)
3. The Daimon itself can't be delegated to because it's down

**Solution:** Give the user a self-contained prompt for another agent (or the user) to execute:
```
TASK: Replace ONE value in <daimon>'s .env file.
FILE: /exact/path/to/.env
CURRENT CONTENT: <show it>
WHAT TO CHANGE: <exact line, exact new value>
DO NOT touch any other line. DO NOT touch config.yaml.
VERIFICATION: <exact command to verify>
```

## Reverting Unauthorized Changes

If you made config changes without permission:
1. Revert each one with `hermes config set` (same CLI, works fine)
2. Verify the revert with `grep` or `awk`
3. Apologize — do not justify or minimize
4. Only proceed with the originally requested change

## Log Locations (for diagnostics)

Logs are at `/home/prometeo/Aether-Agents/home/logs/`:
- `agent.log` — LLM calls, API errors, conversation loop
- `mcp-stderr.log` — ACP session spawns, cancellations, reuse
- `errors.log` — tool errors, plugin failures
- `gateway.log` — gateway service events

NOT at `.venv-hermes/var/log/olympus/` (that path does not exist on this setup).
