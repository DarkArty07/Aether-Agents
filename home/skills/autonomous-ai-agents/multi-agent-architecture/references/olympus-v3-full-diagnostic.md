# Olympus V3 MCP — Full Health Diagnostic

Checklist for "is the entire olympus_v3 MCP healthy?" — systematically test all 5 MCP actions, verify DB integrity, and detect zombie processes.

## When to Run

- User asks "is everything working?" / "diagnostica el MCP"
- After gateway restart or config changes
- After applying fixes to olympus_v3/server.py
- After monthly quota resets or provider changes
- Before starting a heavy multi-Daimon workflow

## Diagnostic Steps (in order)

### 1. Discover — agent registry

```
talk_to(action="discover")
```

Expected: returns all 6 Daimons (hefesto, etalides, athena, daedalus, ictinus, ariadna) with `has_config: true` and `has_soul: true`.

**If missing Daimons:** check profile paths in `home/profiles/`, verify `config.yaml` and `SOUL.md` exist.

### 2. aether_status — continuity DB

```
aether_status(project_root="/path", detail="summary")
```

Expected: returns `hot_state` with `current_phase`, `current_task`, `sessions_count`, `issues_count`, `decisions_count`.

**If empty/null hot_state:** aether.db may be missing or corrupted. Check `.aether/aether.db` exists.

### 3. aether_curate — context regeneration

```
aether_curate(project_root="/path", focus="recent")
```

Expected: `"Curated context written to /path/.aether/CONTEXT.md"`. Verify with `wc -l .aether/CONTEXT.md` — should be non-empty.

### 4. aether_update — write test

```
aether_update(action="set_task", project_root="/path", task="Diagnostic test — <timestamp>")
```

Expected: `"Task updated to: Diagnostic test — <timestamp>"`.

### 5. talk_to (delegate) — full round-trip

```
talk_to(action="delegate", daimon="hefesto", project_root="/path",
  prompt="PROJECT_ROOT: /path\n\nTASK:\nEjecuta: echo 'OK' y repórtalo.\n\nCONSTRAINTS:\nSolo esa línea.",
  timeout=120)
```

Expected: `status: "completed"`, `tool_calls >= 1`, `last_turn` is NOT null, `elapsed_seconds < 60`.

**If `tool_calls: 0` and `last_turn: null`:** see `references/olympus-acp-debugging.md` Diagnostic Decision Tree.

**If `elapsed_seconds > 60`:** Daimon may be slow or stuck. Check `agent.log` for 429 errors.

### 6. talk_to (close) — session cleanup

```
talk_to(action="close", session_id="<from step 5>")
```

Expected: `status: "completed"`, session data returned. No errors.

### 7. Zombie Process Detection

```bash
pgrep -af 'olympus_v3.server'
# OR
for pid in $(pgrep -f 'olympus_v3.server'); do
  echo "PID $pid: $(ps -o etime= -p $pid | xargs)"
  ls -la /proc/$pid/fd 2>/dev/null | grep olympus_v3.db
done
```

Expected: **EXACTLY 1** process. If >1, zombie processes exist — see Pitfall #24 in `references/olympus-acp-debugging.md`.

**Fix:** `pkill -f olympus_v3.server && sleep 1 && systemctl --user restart hermes-gateway.service`

### 8. DB Path Verification

The actual olympus_v3.db path is:
```
/home/prometeo/Aether-Agents/home/.olympus/olympus_v3.db
```
NOT `.olympus_v3/`. Verify with:
```bash
ls -la /home/prometeo/Aether-Agents/home/.olympus/olympus_v3.db
sqlite3 <path> "SELECT COUNT(*) FROM sessions; SELECT COUNT(*) FROM turns;"
```

### 9. Gateway Process Check

```bash
systemctl --user status hermes-gateway.service --no-pager
```

No errors in `journalctl --user -u hermes-gateway.service --since "5 minutes ago"`.

## Quick One-Shot Diagnostic

For CLI use, this single command chain tests everything:

```bash
echo "=== 1. Zombie check ===" && pgrep -af 'olympus_v3.server' | wc -l && \
echo "=== 2. DB check ===" && sqlite3 ~/Aether-Agents/home/.olympus/olympus_v3.db "SELECT 'sessions:', COUNT(*) FROM sessions; SELECT 'turns:', COUNT(*) FROM turns;" && \
echo "=== 3. Gateway ===" && systemctl --user is-active hermes-gateway.service && \
echo "=== Done ==="
```

## Common Failure Patterns

| Symptom | First Check | Reference |
|---------|-------------|-----------|
| delegate returns tool_calls=0, last_turn=null | agent.log for 429 | olympus-acp-debugging.md §Issue B |
| delegate returns "Error: 'daimon' is required" | server.py `required` array | olympus-acp-debugging.md §Pitfall #27 |
| Multiple olympus processes | Zombie after restart | olympus-acp-debugging.md §Pitfall #24 |
| write_file denied, terminal works | ACP client policy | acp-client-file-operations.md |
| File-mutation verifier false positive | Terminal used instead of write_file | olympus-acp-debugging.md §Pitfall #26 |
| poll returns stale data | Zombie processes routing requests | olympus-acp-debugging.md §Pitfall #24 |
