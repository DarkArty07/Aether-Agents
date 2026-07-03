# Port Conflict Resolution

## When your server fails with "[Errno 98] Address already in use"

**Symptom:** You start a server, `process(action='poll')` shows it exited with `[Errno 98] Address already in use`.

## Step 1: Identify what's on the port

```bash
ss -tlnp | grep <PORT>
# Example output:
# LISTEN 11     511    127.0.0.1:3001    0.0.0.0:*    users:((\"node-MainThread\",pid=727567,fd=25))
```

Fields: protocol, recv-q, send-q, local-address, peer-address, process-info (name, PID, fd).

Alternative (if `ss` not available):
```bash
lsof -i :<PORT>
```

## Step 2: Verify it's safe to kill

Check the process name and PID:
- `node-MainThread` → likely Vite/Next.js dev server
- `python` → could be another Python server
- Process with no name or zombie → safe to kill

If unsure, check the PID:
```bash
ps -p <PID> -o pid,comm,args
```

## Step 3: Kill the occupying process

```bash
kill <PID>
```

Then verify port is free:
```bash
ss -tlnp | grep <PORT>
# No output = port free
```

If `kill` doesn't work (SIGTERM ignored):
```bash
kill -9 <PID>   # SIGKILL — last resort, process can't catch this
```

## Step 4: Start your server

Use `background=true` in terminal():
```bash
cd /path/to/project && python3 server.py
```

## Step 5: Verify it started

Check the process is running:
```python
process(action='poll')
# → status: "running"
```

Then hit the endpoint:
```bash
curl -s --max-time 5 http://localhost:<PORT>/<endpoint>
```

## Common patterns

| Tool | Port | Usual culprit |
|------|------|---------------|
| FastAPI / uvicorn | 3001 | Node.js dev server (Vite, Next.js) |
| React/Vite | 5173 | Another Vite instance |
| Flask | 5000 | Another Flask app |
| debugpy | 5678 | Leftover debug session |
| PostgreSQL | 5432 | Another postgres instance |

## Prevention

Always check port availability before starting:
```bash
ss -tlnp | grep -q ":<PORT> " && echo "PORT IN USE" || echo "PORT FREE"
```

Or start with a different port as fallback:
```bash
PORT=3001
while ss -tlnp | grep -q ":$PORT "; do PORT=$((PORT + 1)); done
echo "Using port $PORT"
```
