# Ad-Hoc Verification Patterns

Beyond TDD's RED-GREEN-REFACTOR cycle, you will often be asked to run
verification tests on existing systems — one-off smoke tests, API health
checks, or integration probes. These patterns make those reliable.

## Temp-File for Complex Python Snippets

### The Problem

The user provides `python -c "..."` with Python code containing single
quotes, f-string braces, triple-quoted strings, or backslashes — all of
which conflict with shell quoting. Nested quoting multiplies the failure
surface:

```bash
# Fragile — quoting breaks on any ' or { or "
python3 -c "
import sys
sys.path.insert(0, '/some/path')
from mod import chat_completion
result = await chat_completion(
    messages=[{'role': 'user', 'content': 'hello'}],  # ← single quotes inside double-quoted shell string
    model='glm-5.2'
)
print(f'Result: {result}')   # ← f-string braces inside double-quoted shell string
"
```

Commands like this reliably break. Fixing the quoting takes more time
than using the right approach.

### The Fix — Write a Temp File

```python
# 1. Write the Python script to /tmp (no quoting issues inside heredoc)
terminal("cat > /tmp/test_verify.py << 'PYEOF'"
"import asyncio, sys, os"
"sys.path.insert(0, '/home/prometeo/Requiem')"
"from shared.opencode_client import chat_completion"
""
"os.environ['OPENCODE_GO_API_KEY'] = 'sk-...'"
""
"async def test():"
"    result = await chat_completion("
"        messages=[{'role': 'user', 'content': 'hello'}],"
"        model='glm-5.2'"
"    )"
"    print(f'Response: {result}')"
""
"asyncio.run(test())"
"PYEOF")

# 2. Execute it
terminal("/path/to/venv/bin/python /tmp/test_verify.py")
```

Key points:
- Use `<< 'PYEOF'` (quoted delimiter) — prevents shell variable expansion
- `cat >` overwrites (use `cat >>` to append)
- Every line is quoted in Python already — escaping is symmetric
- The script persists at `/tmp/test_verify.py` for debugging if it fails

### Reading Secrets from .env (Python-side)

Avoid shell-level grep/awk/sed for extracting env vars — it creates quoting
nesting that breaks. Read the file from Python instead:

```python
terminal("cat > /tmp/test_verify.py << 'PYEOF'"
"import os"
"with open('/path/to/.env') as f:"
"    for line in f:"
"        line = line.strip()"
"        if line.startswith('API_KEY='):"
"            os.environ['API_KEY'] = line.split('=', 1)[1]"
"            break"
"PYEOF")
```

## Background Server Test Lifecycle

When testing API endpoints that require a running server (FastAPI, uvicorn):

### 1. Check for Stale Instances First

A port still occupied from a prior session causes the new server to fail
binding. Crucially, curls may **still return data** from the stale server,
producing false positives:

```bash
# Kill anything on the port before starting fresh
kill -9 $(lsof -t -i:3001) 2>/dev/null; echo "port freed"
```

### 2. Start Server in Background

```python
terminal(
    command="cd /path/to/app && uvicorn server:app --host 127.0.0.1 --port 3001",
    background=True,
)
```

### 3. Wait for Readiness

```python
import time
time.sleep(2)  # crude but sufficient for uvicorn
# Or poll a health endpoint
```

### 4. Run Tests

```python
terminal("curl -s http://127.0.0.1:3001/api/health")
terminal("curl -s http://127.0.0.1:3001/api/data")
```

### 5. Clean Up

```python
# Kill the server
process(action='kill', session_id='proc_xxx')

# Verify it actually started (check for bind errors)
process(action='log', session_id='proc_xxx')
# Look for: "Application startup complete." — success
# Look for: "address already in use" — stale instance was hit
```

### Pitfall: Silent Bind Failure

If `process(action='log')` shows `address already in use`, the test
results came from a **stale** server, not the one you just started.
Mark the test results as suspect and retry after killing the stale
process.

## Async Client Verification

When testing async API clients (httpx/aiohttp), the client must be called
with `asyncio.run()`:

```python
async def test():
    result = await client.chat_completion(...)
    print(f'Response: {result}')

asyncio.run(test())
```

**Pitfall:** Top-level `await` only works in the Python REPL or Jupyter.
In scripts, wrap the async call in a coroutine and pass it to
`asyncio.run()`.
