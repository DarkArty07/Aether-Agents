---
name: custom-mcp-server
description: "Build custom MCP servers in Python (FastMCP/stdio) for project-specific hermes-agent instances. Covers server structure, SQLite tool pattern, external API tool pattern, config.yaml registration, and verification workflow."
version: 1.0.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [mcp, python, sqlite, hermes-agent, tools, custom-server]
    related_skills: [native-mcp, hermes-agent, chatbot-prototyping]
---

# Custom MCP Server for Hermes Agent

## When to Use This

Build a custom MCP server when a hermes-agent instance needs project-specific tools that aren't covered by existing MCP servers. Common patterns:

- **Local database queries** — SQLite with domain data (doctors, products, catalog)
- **External API integration** — Google Maps, weather, payment gateways
- **Domain-specific computation** — medical triage logic, financial calculations
- **Multi-tool bundling** — several related tools in one server (e.g., "asclepio" server with both doctor search and nearby places)

## When NOT to Use This

- An existing MCP server already does what you need (check `hermes mcp list` and the MCP marketplace first)
- You just need filesystem access → use the built-in `file` toolset
- You just need web search → use the built-in `web` toolset
- The tool is a one-off script, not a recurring capability → run it via `terminal`

## Architecture

```
hermes-agent (HERMES_HOME)
  ├── config.yaml          # registers MCP server
  ├── SOUL.md              # agent identity + tool usage instructions
  ├── .env                 # API keys
  └── (runtime files)

project/mcp/               # MCP server lives here (outside HERMES_HOME)
  ├── server.py            # FastMCP server with tools
  ├── data.db              # SQLite database (auto-created from JSON)
  ├── data.json            # Source data (used to init DB)
  └── requirements.txt     # just: mcp>=1.0.0
```

The MCP server is a separate directory from the HERMES_HOME. The `config.yaml` points to it via `command` + `args`.

## Building a Custom MCP Server

### Prerequisites

- Python 3.11+ with `mcp` package installed (part of `hermes-agent[mcp]` extra)
- The venv that runs hermes-agent must have the `mcp` SDK: `pip install 'hermes-agent[mcp]'`
- Verify: `python -c 'import mcp; print(mcp.__version__)'`

### Server Template (FastMCP)

Use FastMCP (the modern API from mcp SDK v1.26+). It's simpler than the low-level `Server`/`stdio_server` pattern:

```python
#!/usr/bin/env python3
"""Project MCP Server — provides domain-specific tools."""

import json
import os
import sqlite3
import urllib.request
import urllib.parse
from mcp.server import FastMCP

DB_PATH = os.path.join(os.path.dirname(__file__), "data.db")
JSON_PATH = os.path.join(os.path.dirname(__file__), "data.json")

server = FastMCP("project-name")


def init_db():
    """Create SQLite DB from JSON source if DB doesn't exist."""
    if os.path.exists(DB_PATH):
        return
    if not os.path.exists(JSON_PATH):
        return
    with open(JSON_PATH, encoding="utf-8") as f:
        records = json.load(f)
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""CREATE TABLE records (...)""")
    for r in records:
        c.execute("INSERT INTO records VALUES (...)", (...))
    conn.commit()
    conn.close()


@server.tool()
def search_records(query: str, filter: str = "") -> str:
    """
    Search records in the database.
    
    Args:
        query: Search term
        filter: Optional filter field
    """
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    # Use LIKE for case-insensitive search
    c.execute(
        "SELECT * FROM records WHERE name LIKE ? ORDER BY rating DESC",
        (f"%{query}%",)
    )
    rows = c.fetchall()
    conn.close()
    
    if not rows:
        return json.dumps({"success": True, "records": []}, ensure_ascii=False)
    
    results = [dict(r) for r in rows]
    return json.dumps({"success": True, "records": results}, ensure_ascii=False)


@server.tool()
def search_nearby(lat: float, lng: float, tipo: str) -> str:
    """
    Search nearby places using Google Maps Places API.
    
    Args:
        lat: Latitude
        lng: Longitude
        tipo: Place type (farmacia, hospital, etc.)
    """
    api_key = os.environ.get("GOOGLE_MAPS_API_KEY", "")
    if not api_key or api_key == "TU_API_KEY_AQUI":
        return json.dumps({
            "success": False,
            "error": "Google Maps API key not configured"
        }, ensure_ascii=False)
    
    # Map domain terms to Google place types
    type_map = {
        "farmacia": "pharmacy",
        "hospital": "hospital",
        "clinica": "doctor",
        "doctor": "doctor",
    }
    place_type = type_map.get(tipo.lower(), tipo.lower())
    
    params = {
        "location": f"{lat},{lng}",
        "radius": 5000,
        "type": place_type,
        "key": api_key,
        "language": "es",
    }
    url = f"https://maps.googleapis.com/maps/api/place/nearbysearch/json?{urllib.parse.urlencode(params)}"
    
    try:
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req, timeout=10) as response:
            data = json.loads(response.read().decode("utf-8"))
        
        if data.get("status") != "OK":
            return json.dumps({"success": False, "error": data.get("status")}, ensure_ascii=False)
        
        places = []
        for place in data.get("results", [])[:10]:
            places.append({
                "name": place.get("name", "Sin nombre"),
                "address": place.get("vicinity", "Sin dirección"),
                "rating": place.get("rating", "N/A"),
                "lat": place["geometry"]["location"]["lat"],
                "lng": place["geometry"]["location"]["lng"],
            })
        return json.dumps({"success": True, "places": places}, ensure_ascii=False)
    
    except Exception as e:
        return json.dumps({"success": False, "error": str(e)}, ensure_ascii=False)


if __name__ == "__main__":
    init_db()
    server.run(transport="stdio")
```

### Key Patterns

**1. FastMCP tool registration:** Use `@server.tool()` decorator. The function's docstring becomes the tool description. Type hints become the input schema. No need for manual `inputSchema` dicts.

**2. SQLite initialization:** `init_db()` runs on startup. If the DB file exists, it returns immediately. If not, it creates the DB from a JSON source file. This makes the server self-contained — no separate migration step needed.

**3. Return strings, not dicts:** MCP tools must return strings. Use `json.dumps(result, ensure_ascii=False)` to return structured data. `ensure_ascii=False` preserves Spanish characters.

**4. Environment variables:** Read API keys from `os.environ`. The hermes-agent config.yaml `env:` block passes them to the subprocess. Do NOT hardcode keys in the server.

**5. External HTTP requests:** Use `urllib.request` from the stdlib. Do NOT use `requests` or `httpx` — they add unnecessary dependencies that may not be in the venv.

**6. Error handling:** Return error as JSON with `{"success": false, "error": "..."}`. The agent can read and communicate the error to the user.

## Configuring Hermes Agent to Use the Server

### config.yaml

```yaml
model:
  provider: custom:llmgateway   # custom_providers need "custom:" prefix
  default: deepseek-v4-flash    # "default", NOT "name" — hermes-agent uses model.default
  base_url: https://api.llmgateway.io/v1
  api_mode: chat_completions
  context_length: 128000

custom_providers:               # MUST declare the provider here too
- name: llmgateway              # name without "custom:" prefix
  base_url: https://api.llmgateway.io/v1
  key_env: LLMGATEWAY_API_KEY   # use key_env, NOT api_key: ${VAR} (no expansion)
  api_mode: chat_completions
  models:
    deepseek-v4-flash:
      context_length: 128000

mcp_servers:
  project-name:                 # server name (tools prefixed with mcp_project-name_)
    command: /path/to/venv/bin/python3.11
    args:
      - /path/to/project/mcp/server.py
    enabled: true
    timeout: 60
    env:                        # CRITICAL: pass env vars to subprocess (filtered by default)
      GOOGLE_MAPS_API_KEY: ${GOOGLE_MAPS_API_KEY}

agent:
  disabled_toolsets:
    - code_execution            # if the agent doesn't need it
```

**Three critical config gotchas (all caused real failures):**

1. **`model.default`, not `model.name`.** hermes-agent reads `model.default` (alias: `model.model`). Using `model.name` silently produces an empty model name at runtime → "Requested model  not supported" (HTTP 400).

2. **`provider: custom:<name>`, not `provider: <name>`.** When using a custom_provider, the `model.provider` field must be prefixed with `custom:`. Without it, `hermes doctor` reports "not a recognised provider" and the runtime can't resolve the API key → HTTP 401.

3. **`key_env: VAR_NAME`, not `api_key: ${VAR_NAME}`.** hermes-agent does NOT expand `${...}` in the `api_key` field. Use `key_env` to point at an environment variable name. The runtime calls `os.getenv(key_env)` to resolve it. Using `api_key: ${LLMGATEWAY_API_KEY}` sends the literal string `${LLMGATEWAY_API_KEY}` as the API key → HTTP 401.

**Critical:** The `command` must be the ABSOLUTE path to the Python binary in the venv that has the `mcp` package installed. Do NOT use `python3` or `python` — use the full venv path.

### .env

```
LLMGATEWAY_API_KEY=llmgtw...
GOOGLE_MAPS_API_KEY=your_key_here
```

API keys in `.env` are loaded by `hermes_cli.env_loader.load_hermes_dotenv()` at startup from `HERMES_HOME/.env`. They become available as environment variables via `os.environ` in the main hermes-agent process. The `key_env` field in `custom_providers` reads from there.

**CRITICAL: MCP subprocesses do NOT inherit all .env variables.** hermes-agent passes a FILTERED environment to MCP server subprocesses. Only safe system vars pass through by default. To pass API keys (like `GOOGLE_MAPS_API_KEY`) to your MCP server, you MUST explicitly declare them in the `env:` block of `mcp_servers` in config.yaml:

```yaml
mcp_servers:
  project-name:
    command: /path/to/venv/bin/python3.11
    args:
      - /path/to/project/mcp/server.py
    enabled: true
    timeout: 60
    env:
      GOOGLE_MAPS_API_KEY: ${GOOGLE_MAPS_API_KEY}   # resolved at spawn from .env
      EXTERNAL_API_KEY: ${EXTERNAL_API_KEY}          # add one per needed var
```

The `${VAR_NAME}` syntax IS expanded here (unlike in `custom_providers.api_key`) — hermes-agent resolves `${...}` placeholders in the `env:` block at server spawn time, reading from the loaded .env variables. Without this `env:` block, `os.environ.get("GOOGLE_MAPS_API_KEY")` in your server.py returns `None` even though the key is in `.env`.

### SOUL.md Tool References

The SOUL.md should tell the agent about its tools:

```markdown
## HERRAMIENTAS DISPONIBLES
Tienes dos herramientas MCP:

1. **buscar_doctores**: Busca doctores por ciudad y/o especialidad.
   Úsala cuando el usuario pida ver un doctor.

2. **buscar_cerca**: Busca lugares cercanos (farmacias, hospitales).
   Úsala cuando el usuario necesite encontrar atención cercana.
   Requiere latitud y longitud del usuario.
```

## Verification Workflow

After creating the server and config:

```bash
# 1. Verify server.py is valid Python
python -c "import ast; ast.parse(open('server.py').read())"

# 2. Verify DB initialization works
cd /path/to/mcp && /path/to/venv/bin/python -c "import server; server.init_db(); print('DB OK')"

# 3. Test MCP connection from hermes-agent
HERMES_HOME=/path/to/agent hermes mcp test project-name

# 4. Verify config loads correctly
HERMES_HOME=/path/to/agent hermes config show

# 5. Full integration test
HERMES_HOME=/path/to/agent hermes chat
# Then ask the agent to use a tool
```

### `hermes mcp test` output (successful):
```
Testing 'project-name'...
  Transport: stdio → /path/to/python3.11
  Auth: none
  ✓ Connected (654ms)
  ✓ Tools discovered: 2

    buscar_doctores
    Busca doctores en la base de datos por ciudad y/o ...
    buscar_cerca
    Busca lugares cercanos usando Google Maps Places A...
```

## Reference Files

- `references/standalone-hermes-home.md` — Directory layout for project-specific hermes-agent instances with their own HERMES_HOME. Includes config.yaml template and verification checklist.
- `references/asclepio-mcp-migration.md` — Session notes from the Asclepio migration (Next.js → hermes-agent + custom MCP). Includes implementation details and verification results.
- `references/mcp-env-filtering.md` — MCP subprocess env filtering: why .env vars don't reach MCP servers and how to fix with the `env:` config block. Includes debugging steps and the key distinction between `env:` and `key_env:`.
- `references/tmux-e2e-testing.md` — E2E testing pattern for conversational agents via tmux: spawn agent, send test messages, capture output, design 5-7 scenario suites covering normal cases, multi-turn, edge cases, and context retention.
- `references/clio-fca-mcp.md` — Full development guide for Clio FCA, a real-world document-generation MCP server (FastMCP, python-docx, preset system, fca_generate_task). Covers architecture, tools, known pitfalls, and the PDF conversion bug pattern.
- `references/pdf-conversion-bug.md` — Document pipeline diagnostic pattern: how to avoid saving intermediate formats to the final output path. Generalized from the Clio FCA bug, applicable to any docx→pdf conversion workflow.
- `templates/server.py.template` — Copy-and-adapt template for a FastMCP server with SQLite + external API tools. Replace `project-name`, schema, and API endpoints.

## Config Debugging (custom_providers)

When a standalone hermes-agent fails to start, run `HERMES_HOME=/path/to/agent hermes doctor` first. Common failures, in order of likelihood:

| Symptom | Root Cause | Fix |
|---------|-----------|-----|
| `hermes doctor`: "model.provider 'X' is not a recognised provider" | Missing `custom:` prefix on provider name | Change `provider: llmgateway` to `provider: custom:llmgateway` |
| HTTP 400 "Requested model  not supported" (empty model name) | Used `model.name` instead of `model.default` | Change `name:` to `default:` in config.yaml |
| HTTP 401 "Invalid API token" | `api_key: ${VAR}` sent literally (no env expansion) | Change to `key_env: VAR_NAME` (points to env var) |
| HTTP 401 "Invalid API token" | API key in .env is wrong (e.g., typo from copy) | Verify with curl: `curl -s https://api.llmgateway.io/v1/models -H "Authorization: Bearer $KEY" \| head -c 100` |
| HTTP 403 "Direct provider routing is not available on coding plans" | Model name has provider prefix (e.g., `openai/gpt-5.4-mini`) | Remove the prefix — use `gpt-5.4-mini` (bare model id). llmgateway coding plans route automatically; the `openai/` prefix triggers direct routing which is blocked. Affects `model.default` AND `custom_providers.models` key |
| MCP tool returns "API key not configured" but .env has the key | MCP subprocesses receive filtered env — .env vars not forwarded | Add `env:` block to mcp_servers in config.yaml: `GOOGLE_MAPS_API_KEY: ${GOOGLE_MAPS_API_KEY}` |
| MCP tools not discovered | Wrong Python path or missing `mcp` package | Use absolute venv path: `/path/to/.venv-hermes/bin/python3.11` |

### How custom_providers resolve the API key

The runtime (`hermes_cli/runtime_provider.py`) resolves the API key by checking these candidates in order:

1. `explicit_api_key` (from CLI args, rarely set)
2. `custom_provider["api_key"]` (literal string — NOT expanded)
3. `os.getenv(custom_provider["key_env"])` (environment variable lookup)
4. Host-derived `<VENDOR>_API_KEY` (e.g., `LLMGATEWAY_API_KEY` from hostname)

Using `key_env` is the reliable path. The `.env` file is loaded by `hermes_cli/env_loader.py` from `HERMES_HOME/.env` at startup.

### How the model name resolves

`hermes_cli/runtime_provider.py` reads `model.default` from config.yaml. The alias `model.model` also works. `model.name` does NOT work — it's silently ignored, producing an empty model string.

## Pitfalls

- **Use the venv Python, not system Python.** The `mcp` package is installed in the hermes-agent venv. The `command` in config.yaml must be the absolute path to that venv's Python binary (e.g., `/home/user/Aether-Agents/home/.venv-hermes/bin/python3.11`). Using `python3` will fail with `ModuleNotFoundError: No module named 'mcp'`.

- **FastMCP vs low-level Server API.** FastMCP (`from mcp.server import FastMCP`) is the recommended modern API. The low-level pattern (`from mcp.server import Server` + `from mcp.server.stdio import stdio_server` + `@server.list_tools()` + `@server.call_tool()`) works but is significantly more verbose. FastMCP handles protocol details automatically.

- **DB path must be absolute or relative to server.py.** Use `os.path.join(os.path.dirname(__file__), "data.db")` — NOT `process.cwd()` or a bare filename. The MCP server's CWD may differ from what you expect when launched by hermes-agent.

- **MCP tools return strings.** A common mistake is returning a dict directly. MCP tools must return strings. Wrap with `json.dumps()`.

- **`ensure_ascii=False` in json.dumps.** Without this, Spanish characters (á, é, ñ, ¿) become `\uXXXX` escape sequences. The agent can still read them, but it wastes tokens and is harder to debug.

- **Google Maps API key placeholder.** Use a clear placeholder like `TU_API_KEY_AQUI` in `.env`. The tool should check for this and return a clear error message if the key isn't configured. This lets the server run (and other tools work) even without the API key.

- **init_db() is idempotent.** It checks `os.path.exists(DB_PATH)` and returns early. This means it's safe to call on every startup — but it also means changes to the JSON source won't propagate to an existing DB. Delete the DB file to force recreation.

- **SQLite LIKE is case-insensitive by default for ASCII.** For proper Unicode case-insensitive search in Spanish, use `LOWER(column) LIKE LOWER(?)` or enable SQLite's ICU extension. For prototypes, `LIKE` with `%query%` is usually sufficient.

- **Standalone HERMES_HOME per project.** Each project-specific agent should have its own HERMES_HOME directory (e.g., `project/agent/`) with its own `config.yaml`, `SOUL.md`, and `.env`. Do NOT mix project configs into the Aether-Agents home or any other instance's home. See `references/standalone-hermes-home.md` for the directory layout.

- **API key typos: verify with xxd, not visual diff.** When copying API keys between .env files, a single missing character produces HTTP 401 that looks identical to a config problem. `diff` may report "DIFFERENT" but the visual output looks the same. Use `xxd /path/to/.env | grep KEYNAME` on both files and compare byte-by-byte. Also verify the key works directly: `curl -s https://api.example.com/v1/models -H "Authorization: Bearer $(grep KEY /path/to/.env | cut -d= -f2)" | head -c 100`.

- **Hefesto corrupts .env files with sanitized values.** When delegating .env edits to Hefesto (e.g., updating an API key), Hefesto may use `execute_code` or `write_file` which receives the `***`-redacted version of API keys that hermes-agent shows in `read_file`/`cat` output. Hefesto then writes the literal string `***` or a truncated key (e.g., `llmgtw...ly0T` instead of `llmgtwy_rWzSyyEFxd5k2EEQQEcNt1QjVe4mMlb2bSDMly0T`) to the .env file, corrupting it. This produces HTTP 401 on the next agent start. Prevention: (1) Tell Hefesto to use `xxd` to read the real key bytes from the source .env BEFORE writing, (2) Tell Hefesto to use `patch` (not `execute_code` or `write_file`) to modify .env, (3) After Hefesto finishes, verify the key with `xxd /path/to/.env | grep KEYNAME` — the hex dump bypasses hermes-agent's sanitization and shows the real bytes. (4) If Hefesto times out or fails, cancel the session and retry with more specific instructions — Hefesto may loop on execute_code attempts.

- **`hermes doctor` as first diagnostic.** When a standalone agent fails to start, always run `HERMES_HOME=/path/to/agent hermes doctor` first. It immediately reveals unrecognised providers, missing API keys, and config version issues. See the "Config Debugging" section above for the symptom-to-fix mapping.

- **MCP subprocess env filtering — the #1 cause of "API key not configured" errors.** hermes-agent passes a FILTERED environment to MCP subprocesses. Variables in `.env` are loaded into the main process's `os.environ`, but NOT automatically forwarded to MCP server subprocesses. Symptom: your server.py calls `os.environ.get("GOOGLE_MAPS_API_KEY")` and gets `None`, even though the key is correctly set in `.env`. Fix: add an `env:` block to the mcp_servers entry in config.yaml with `GOOGLE_MAPS_API_KEY: ${GOOGLE_MAPS_API_KEY}`. The `${VAR}` syntax IS expanded in the `env:` block (unlike in `custom_providers.api_key`). This is different from `key_env` in custom_providers — that mechanism is specific to provider auth, not MCP subprocess env.

- **llmgateway coding plans reject provider-prefixed model names.** When using llmgateway as a custom_provider, model names must NOT include the vendor prefix (e.g., use `gpt-5.4-mini`, NOT `openai/gpt-5.4-mini`). The prefixed form triggers "direct provider routing" which is blocked on coding plans, producing HTTP 403: "Direct provider routing is not available on coding plans. Use the root model id without a provider prefix." This affects both `model.default` and the key in `custom_providers.models`. The gateway handles routing automatically — just use the bare model id.
