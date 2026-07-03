# Dashboard and Testing Patterns — From Requiem Agents Phases 4-6

Concrete implementation patterns for the telemetry dashboard and test suite of a multi-agent system. These emerged from building Requiem Agents Phases 4-6 (FastAPI + React + Gothic Horror CSS + 35 pytest tests).

## Dashboard Architecture

### Backend: FastAPI reading from shared SQLite

The dashboard backend reads from the SAME SQLite database that the agents write to. No separate data store, no ETL, no message queue. The SQLite file is the single source of truth.

```
agents (write) ──► shared/state.db ──◄── FastAPI (read)
                                         │
                                    React frontend (polls every 5s)
```

**File:** `dashboard-api/server.py`

Key patterns:
- `sys.path.insert(0, project_root)` to import shared modules (same as MCP server)
- `REQUIEM_PROJECT_ROOT` env var for DB path resolution
- CORS enabled for the frontend origin (localhost:3000)
- All endpoints under `/api/` prefix to avoid conflicts
- Config endpoint: GET returns defaults from a dict, POST writes to `shared/config.json`

```python
project_root = os.environ.get("REQUIEM_PROJECT_ROOT", "/path/to/project")
sys.path.insert(0, project_root)

from shared.eval import get_eval_report, DB_PATH
from shared.session_monitor import MODEL_CONTEXT_LIMITS

app = FastAPI(title="Project Dashboard")
app.add_middleware(CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_methods=["*"], allow_headers=["*"])

@app.get("/api/sessions")
def get_sessions():
    # Query agent_calls grouped by agent_name
    # Return: agent_name, model, total_tokens, context_pct, duration
    ...

@app.get("/api/stats")
def get_stats():
    return get_eval_report()  # reuse existing telemetry function
```

**Endpoint inventory (minimum viable dashboard):**

| Endpoint | Purpose | Data source |
|----------|---------|-------------|
| GET /api/sessions | Active agents with token usage | SQLite GROUP BY agent_name |
| GET /api/stats | Consolidated metrics (cost, pass rate) | shared/eval.py get_eval_report() |
| GET /api/activity | Recent agent calls (last 50) | SQLite ORDER BY id DESC LIMIT 50 |
| GET /api/config | Agent-to-model mapping | shared/config.json or defaults dict |
| POST /api/config | Update agent config | Writes to shared/config.json |

### Frontend: React + Vite + Themed CSS

**No CSS frameworks.** The theme IS the project identity. For Requiem Agents (Gothic Horror):
- Background: `#0a0a0a` (near black)
- Text: `#c0c0c0` (silver)
- Accents: `#8b0000` (dark blood red)
- Cards: `#1a1a1a` bg, 1px solid `#333`, NO border-radius (angular, cold)
- Headings: Cinzel serif (Google Fonts), uppercase, letter-spacing
- Data/numbers: JetBrains Mono (Google Fonts)
- Hover: subtle red glow `box-shadow: 0 0 10px rgba(139,0,0,0.3)`

**Component structure (5 components minimum):**

| Component | Props | What it shows |
|-----------|-------|---------------|
| SessionStatus | sessions[] | Agent name, model, token bar (color: green/amber/red by context %), duration |
| Stats | stats{} | Total calls, cost, audit pass rate, escalations — large mono numbers |
| Config | config{}, onSave | Agent-to-model table, editable dropdowns, save button POSTs |
| ActivityLog | activity[] | Scrollable feed: timestamp (mono), agent (color-coded), action, result badge |
| ProjectInfo | static | Project name, description, GitHub link, architecture summary |

**Polling pattern:**
```jsx
useEffect(() => {
  const poll = async () => {
    const [sess, stat, act] = await Promise.all([
      fetch('/api/sessions').then(r => r.json()),
      fetch('/api/stats').then(r => r.json()),
      fetch('/api/activity').then(r => r.json()),
    ]);
    setSessions(sess.agents);
    setStats(stat);
    setActivity(act.activity);
  };
  poll();
  const interval = setInterval(poll, 5000);
  return () => clearInterval(interval);
}, []);
```

### Vite config: proxy /api to backend

```javascript
export default defineConfig({
  plugins: [react()],
  server: {
    proxy: { '/api': 'http://localhost:3001' }
  }
});
```

This avoids CORS in development (the proxy forwards /api/* to the FastAPI backend on port 3001).

## Testing Multi-Agent Systems Without API Keys

The core challenge: multi-agent systems make LLM API calls, but tests must run without API keys. Solution: test everything EXCEPT the LLM calls.

### Four test categories

**1. Telemetry tests (test_eval.py)** — test the SQLite logging layer
- `test_init_db`: table creation
- `test_log_agent_call`: row insertion with all columns
- `test_get_eval_report_empty`: returns `{"total_calls": 0}` when no data
- `test_get_eval_report_with_data`: log 3 calls (2 pass, 1 fail), verify pass_rate = 66.7
- `test_get_eval_report_cost`: verify cost_usd summation

Critical: use a `temp_db` fixture that sets `REQUIEM_PROJECT_ROOT` to `tmp_path` and purges cached modules:

```python
@pytest.fixture
def temp_db(tmp_path, monkeypatch):
    monkeypatch.setenv("REQUIEM_PROJECT_ROOT", str(tmp_path))
    tmp_path.mkdir("shared", exist_ok=True)
    # Purge cached shared modules so DB_PATH re-evaluates
    for mod in list(sys.modules.keys()):
        if mod.startswith("shared."):
            del sys.modules[mod]
    yield tmp_path
```

**2. Tool tests (test_tools.py)** — test custom tools (no API needed)
- read_file, write_file, search_files, terminal: all testable with temp files
- Tool registry verification: ALL_TOOLS has expected keys, READ_ONLY_TOOLS excludes write tools
- execute_tool dispatcher: returns error for unknown tools

**3. API tests (test_dashboard_api.py)** — test FastAPI endpoints
- Use `TestClient` from `fastapi.testclient`
- Set `REQUIEM_PROJECT_ROOT` to tmp_path before importing server
- If the API directory has a hyphen (e.g., `dashboard-api/`), use `importlib.util.spec_from_file_location` to import:

```python
spec = importlib.util.spec_from_file_location(
    "dashboard_server",
    os.path.join(os.path.dirname(__file__), "..", "dashboard-api", "server.py")
)
server_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(server_module)
client = TestClient(server_module.app)
```

**4. Structural tests (test_necromancer_logic.py)** — verify project structure
- Module syntax: `py_compile` check via import
- Tool registry constants exist and have correct membership
- Soul/prompt files (.md) exist and are non-empty
- No API calls, pure filesystem checks

### Test environment: which Python to use

System Python may not have all dependencies. If tests need `fastapi`, `httpx`, etc., use a venv that has them:

```bash
# If system Python lacks fastapi:
/home/prometeo/Aether-Agents/home/.venv-hermes/bin/python -m pytest tests/ -v
```

Check which Python has the needed packages before running tests. PEP 668 may block `pip install` on Homebrew or system Python — use `--user`, `--break-system-packages`, or a venv. On WSL with system Python, `pip3 install --break-system-packages` is the pragmatic choice for dev environments.

## Verification Checklist for Multi-Agent Projects

Before declaring a multi-agent system "done":

1. **Python compilation**: `python3 -m py_compile` on every `.py` file
2. **Test suite**: `pytest tests/ -v` — all green, no API keys needed
3. **MCP server**: import test — server object created, tools registered with correct names
4. **Dashboard API**: start backend, curl each endpoint, verify JSON response
5. **Frontend build**: `npx vite build` — 0 errors, modules transformed
6. **Git hygiene**: `git ls-files | grep -E '\.env|\.db'` returns nothing (no secrets/db in git)
7. **Gitignore coverage**: `.env`, `*.db`, `.venv/`, `node_modules/`, `__pycache__/`, `.aether/` all ignored

## Common Pitfalls

- **Testing with real API keys**: Never require OPENCODE_GO_API_KEY (or equivalent) for tests. Mock or skip LLM-dependent code. Test the plumbing, not the intelligence.
- **Tests touching real state.db**: Always use a temp_db fixture. If tests create a real `shared/state.db`, it pollutes the project and may cause flaky tests.
- **Dashboard API not sharing DB path**: The FastAPI server must use the same `DB_PATH` as the agents. If it creates its own DB, the dashboard shows empty data forever.
- **Hyphenated directory names in Python imports**: `dashboard-api/` cannot be imported as a Python module. Use `importlib.util.spec_from_file_location` or rename to `dashboard_api/`.
- **CORS in development:** The Vite proxy handles `/api/*` forwarding, but the FastAPI server still needs CORS middleware for production or non-proxied access.
- **Dashboard frontend running without backend:** The #1 user-facing dashboard error. Symptom: "Connection error: HTTP 500" or blank panels. The Vite dev server serves the frontend but proxies `/api/*` to the FastAPI backend (e.g., `localhost:3001`). If the backend isn't running, every API call fails. Fix: start BOTH processes — `npx vite` (frontend) AND `python3 dashboard-api/server.py` (backend). The backend is a separate process with its own dependency set (fastapi, uvicorn, httpx) that is NOT installed in the agent venv. On externally-managed Python (PEP 668), install with `pip3 install --break-system-packages -r dashboard-api/requirements.txt`. Verification: `curl -s http://localhost:3001/api/stats` must return JSON before opening the frontend.

## Vibecoding Test Approach

When the user asks you to "test" or "try" a multi-agent system, do NOT create a structured test plan with phases and checkpoints. Instead:

1. **Start the assistant in tmux** — `tmux new-session -d -s raven "cd /project && HERMES_HOME=raven/ raven/.venv/bin/hermes"`
2. **Talk to it like a real user** — give it real coding tasks via `tmux send-keys`
3. **Monitor the SQLite telemetry DB** — poll every 30-60s to see which agents are running, whether tokens are being consumed, whether audits pass or fail
4. **When something breaks, fix it** — diagnose via DB + process inspection, delegate the fix, re-test
5. **Iterate for the allotted time** — if one task succeeds, try a harder one. If it fails, fix the bug and retry. Continuous polishing.

Key monitoring commands:

```bash
# See what agents are doing right now
sqlite3 shared/state.db "SELECT id, agent_name, action, result, input_tokens, output_tokens, duration_seconds FROM agent_calls ORDER BY id DESC LIMIT 10;"

# Check if files were actually created
find /project -name "*.py" -newer /project/PLAN.md -not -path '*/.venv/*' -not -path '*/__pycache__/*'

# Check process state (infinite loop vs waiting on API)
pgrep -P <parent_pid> | xargs ps -o pid,stat,time,cmd -p
```

**Why not structured test plans:** The user wants to know if the system works for real vibecoding, not if individual components pass isolated tests. A phased plan (smoke test, integration, end-to-end) tests components in isolation — but the bugs that matter (JSON parsing, context explosion, infinite loops, false-positive audits) only surface during real multi-agent execution. Test the system by USING the system.

**Tmux for interactive agents:** Running the assistant in tmux lets you send input and capture output without blocking your own session. Use `tmux send-keys -t raven "message" Enter` to send, `tmux capture-pane -t raven -p | tail -20` to read.

**Time awareness:** Use `date '+%H:%M:%S'` to track real elapsed time, not your own iteration count. The user may ask for a 2-hour session — track against the wall clock, not turns.
