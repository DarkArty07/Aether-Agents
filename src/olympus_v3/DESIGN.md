# Olympus v3 -- Design Document

## 1. Problem Statement

Olympus v2 (Pi Agent RPC) tiene dos problemas estructurales:

1. **Visibilidad rota**: `agent_end` no garantiza texto de salida. Agentes terminan sin sintetizar. El `event_translator.py` es fragil y requiere parches constantes. El buffer de streaming no delimita turnos -- solo acumula fragmentos sin estructura.

2. **Acoplamiento innecesario**: Pi Agent es una caja negra. Su loop de agente decide cuando parar, sin control externo. Los perfiles de Daimon en `.pi/` son configs paralelas a los perfiles de hermes-agent, duplicando estado.

Olympus v1 (ACP puro) intento resolver visibilidad con streaming (`AgentThoughtChunk`, `AgentMessageChunk`), pero los fragmentos no delimitan turnos -- no hay forma de saber cuando un pensamiento termina y empieza el siguiente.

**v3 resuelve ambos problemas** separando transporte de observabilidad: ACP para ciclo de vida de sesiones, Plugin hooks para datos estructurados por turno, SQLite como canal de comunicacion entre Daimon y orquestador.

## 2. Architecture

```
+------------------------------------------------------------+
|                        Hermes (Orchestrator)                |
|                                                             |
|  MCP Tools: talk_to, discover, consult                     |
|  Reads SQLite: turns, tools, sessions                       |
|  Writes SQLite: steering, consult state                     |
+---------------+--------------------------------------------+
                       | ACP (HTTP, localhost)
                       | open / message / poll / close / delegate
+--------------------+---------------------------------------------+
|                    Daimon (hermes-agent -p <daimon>)         |
|                                                              |
|  Plugin: olympus_v3_hooks                                   |
|  +-- post_llm_call  -> INSERT.turn + tools (cada turno)      |
|  +-- post_tool_call  -> INSERT.tool_call (cada tool)        |
|  +-- on_session_end  -> UPDATE.session status=completed   |
|  +-- pre_llm_call    -> READ.steering (inject directives)    |
|                                                              |
|  Env vars: OLYMPUS_SESSION_ID, OLYMPUS_DB_PATH             |
|  ACP Server: hermes acp --profile <daimon>                  |
+-----------------------------------------------------------------+
```

**Flujo por turno:**
1. Hermes envia mensaje via ACP (`message` action)
2. Daimon procesa con LLM -> plugin `post_llm_call` escribe turno completo + reasoning en SQLite
3. Si el Daimon usa tools -> plugin `post_tool_call` escribe cada tool_call en SQLite
4. Hermes hace poll via ACP (`poll` action) -> lee datos de SQLite, no de streaming
5. Antes del siguiente turno del Daimon -> plugin `pre_llm_call` lee steering de SQLite

**Separacion de responsabilidades:**
- ACP: spawn, prompt, close, cancel -- ciclo de vida de sesiones
- Plugin hooks: datos estructurados por turno -- observabilidad sin streaming fragil
- SQLite: canal de datos entre procesos -- sin buffers en memoria, sin traduccion de eventos

## 3. Component Specifications

### 3.1 acp_manager.py

Base: `src/olympus/acp_client.py` (commit 732f60f).

```python
class ACPManager:
    """Manages ACP connections to Daimon processes."""

    def spawn_agent(self, profile: str, session_id: str | None = None) -> str:
        """Spawn hermes-agent process with -p <profile> as ACP server.
        Returns session_id."""

    def send_message(self, session_id: str, message: str) -> None:
        """Send prompt to running Daimon session."""

    def poll(self, session_id: str) -> dict:
        """Read latest state from SQLite, not ACP streaming.
        Returns {thoughts, messages, tool_calls, status}."""

    def close(self, session_id: str) -> None:
        """Terminate Daimon process and mark session completed."""

    def cancel(self, session_id: str) -> None:
        """Force-terminate a stuck Daimon."""

    def discover(self) -> list[str]:
        """List available Daimon profiles from ~/.hermes/profiles/"""
```

Cambios vs v1:
- Eliminar `session_update` (streaming con callbacks) -- reemplazado por SQLite + hooks
- Agregar `OLYMPUS_SESSION_ID` y `OLYMPUS_DB_PATH` como env vars al spawn
- `poll()` lee de SQLite, no de ACP events
- `discover()` usa `profiles.get_profile_dir()` en vez de `.pi/` configs

### 3.2 db.py -- SQLite Database

```python
DB_PATH = os.environ.get(
    "OLYMPUS_DB_PATH",
    os.path.join(get_hermes_home(), ".olympus", "olympus_v3.db")
)

SCHEMA = """
CREATE TABLE IF NOT EXISTS sessions (
    session_id  TEXT PRIMARY KEY,
    agent       TEXT NOT NULL,          -- profile name
    status      TEXT DEFAULT 'active',   -- active | completed | error | cancelled
    started_at  REAL NOT NULL,           -- time.time()
    completed_at REAL,
    metadata    TEXT                      -- JSON: model, provider, etc.
);

CREATE TABLE IF NOT EXISTS turns (
    turn_id    INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT NOT NULL REFERENCES sessions(session_id),
    turn_num   INTEGER NOT NULL,          -- 1-indexed per session
    role       TEXT NOT NULL,             -- 'assistant' | 'tool_result'
    content    TEXT,                       -- full text of the turn
    reasoning  TEXT,                       -- thinking/reasoning content
    timestamp  REAL NOT NULL,
    metadata   TEXT                        -- JSON: model, tokens, etc.
);

CREATE TABLE IF NOT EXISTS tool_calls (
    call_id    TEXT PRIMARY KEY,           -- from ACP tool_call id
    session_id TEXT NOT NULL REFERENCES sessions(session_id),
    turn_id    INTEGER REFERENCES turns(turn_id),
    tool_name  TEXT NOT NULL,
    arguments  TEXT,                        -- JSON
    result     TEXT,                        -- JSON
    status     TEXT DEFAULT 'pending',      -- pending | completed | error
    timestamp  REAL NOT NULL
);

CREATE TABLE IF NOT EXISTS steering (
    session_id TEXT NOT NULL REFERENCES sessions(session_id),
    directive  TEXT NOT NULL,              -- text to inject
    priority   INTEGER DEFAULT 0,          -- higher = more urgent
    consumed   INTEGER DEFAULT 0,           -- 0 = new, 1 = read by Daimon
    timestamp  REAL NOT NULL
);

-- Indexes for poll performance
CREATE INDEX IF NOT EXISTS idx_turns_session_turn ON turns(session_id, turn_num);
CREATE INDEX IF NOT EXISTS idx_tool_calls_session ON tool_calls(session_id);
CREATE INDEX IF NOT EXISTS idx_steering_session_consumed ON steering(session_id, consumed);
"""
```

- WAL mode para acceso concurrente sin locks
- path configurable via `OLYMPUS_DB_PATH`
- default: `AETHER_HOME/.olympus/olympus_v3.db`

### 3.3 server.py -- MCP Server

Tools expuestas al orquestador (Hermes):

```python
@mcp_tool
def talk_to(agent: str, action: str, session_id: str | None,
            prompt: str | None, poll_interval: int = 15,
            timeout: int = 300) -> dict:
    """
    Actions: open, message, poll, close, cancel, delegate.

    delegate = open + message + auto-poll until done or timeout.
    Returns final result with {timed_out, elapsed_seconds, poll_iterations}.
    """

@mcp_tool
def discover() -> list[dict]:
    """List available Daimon agents and their capabilities."""

@mcp_tool
def consult(action: str, session_id: str | None, plan: str | None,
            agents: list[str] | None, ...) -> dict:
    """Consulting workflow migrated from v2. Reads SQLite instead of Pi Agent buffers."""
```

La tool `talk_to` delega a `ACPManager` para interaccion con procesos Daimon.
La tool `consult` migra la logica de `consult_action.py` de v2 pero lee de SQLite.

### 3.4 olympus_v3_hooks/ -- Plugin

Se registra en cada profile de Daimon (`~/.hermes/profiles/<daimon>/plugins/olympus_v3/`):

```python
def register(ctx):
    """Register Olympus v3 hooks into hermes-agent plugin system."""

    ctx.register_hook("post_llm_call", on_post_llm_call)
    ctx.register_hook("post_tool_call", on_post_tool_call)
    ctx.register_hook("on_session_end", on_session_end)
    ctx.register_hook("pre_llm_call", on_pre_llm_call)
```

**Hook behaviors:**

| Hook | Input | SQLite Action | Purpose |
|------|-------|---------------|---------|
| `post_llm_call` | response, reasoning, tokens | `INSERT INTO turns` | Visibilidad por turno (texto completo, no fragmentos) |
| `post_tool_call` | tool_name, arguments, result | `INSERT INTO tool_calls` | Auditoria de herramientas |
| `on_session_end` | session_id, final_status | `UPDATE sessions SET status=completed` y `completed_at` | Finalizacion confiable (reemplaza agent_end de Pi Agent) |
| `pre_llm_call` | session_id | `SELECT FROM steering WHERE consumed=0` -> inject directive | Steering del orquestador hacia el Daimon (redirigir, cancelar, priorizar) |

**Env vars inyectadas al spawn:**
- `OLYMPUS_SESSION_ID`: ID de la sesion para todas las escrituras SQLite
- `OLYMPUS_DB_PATH`: Path a la base de datos compartida

## 4. Data Flow

```
1. HERMES -> ACPManager.spawn_agent("hefesto")
   -> hermes-agent -p hefesto --acp-server (subprocess)
   -> env: OLYMPUS_SESSION_ID=abc123, OLYMPUS_DB_PATH=~/.olympus/olympus_v3.db
   -> INSERT INTO sessions (session_id='abc123', agent='hefesto', status='active')

2. HERMES -> ACPManager.send_message("abc123", "Implementa X")
   -> ACP prompt enviado al proceso Daimon

3. DAIMON procesa -> LLM genera response
   -> Plugin post_llm_call INSERT INTO turns (session_id='abc123', turn_num=1, content='...', reasoning='...')

4. DAIMON usa tool -> Plugin post_tool_call INSERT INTO tool_calls (call_id='tool_1', ...)

5. HERMES -> ACPManager.poll("abc123")
   -> SELECT * FROM turns WHERE session_id='abc123' ORDER BY turn_num
   -> SELECT * FROM tool_calls WHERE session_id='abc123'
   -> Retorna {thoughts: N, messages: N, tool_calls: N, status: 'active'}

6. HERMES decide: necesita mas informacion o direccionar
   -> INSERT INTO steering (session_id='abc123', directive='Enfocate en la BD')

7. DAIMON -> Plugin pre_llm_call
   -> SELECT * FROM steering WHERE session_id='abc123' AND consumed=0
   -> Inject directive como system message
   -> UPDATE steering SET consumed=1

8. DAIMON termina -> Plugin on_session_end
   -> UPDATE sessions SET status='completed', completed_at=CURRENT WHERE session_id='abc123'

9. HERMES -> ACPManager.poll("abc123")
   -> Lee status='completed' -> retorna resultado final
```

## 5. API Reference -- MCP Tools

### talk_to

```json
{
  "name": "talk_to",
  "parameters": {
    "agent": "string -- Daimon profile name or '?' to discover",
    "action": "string -- open|message|poll|close|cancel|delegate",
    "session_id": "string? -- required for message/poll/close/cancel",
    "prompt": "string? -- required for message/delegate",
    "poll_interval": "int -- seconds between polls (default 15)",
    "timeout": "int -- max seconds for delegate (default 300)"
  },
  "returns": {
    "session_id": "string",
    "status": "string -- active|completed|error|cancelled",
    "thoughts": "int",
    "messages": "int",
    "tool_calls": "int",
    "response": "string? -- final text if completed",
    "elapsed_seconds": "float",
    "poll_iterations": "int"
  }
}
```

### discover

```json
{
  "name": "discover",
  "returns": [
    {
      "name": "hefesto",
      "description": "Code implementer",
      "model": "glm-5.1",
      "tools": ["read", "write", "edit", "bash", "grep", "find", "ls"]
    }
  ]
}
```

### consult

```json
{
  "name": "consult",
  "parameters": {
    "action": "string -- start|run|sign|add_agent|status|complete",
    "session_id": "string? -- required for run/sign/status/complete",
    "plan": "string? -- required for start",
    "agents": "list[str]? -- required for start",
    "agent": "string? -- required for run/sign",
    "context": "string? -- optional for start"
  }
}
```

## 6. Plugin API -- Hooks

```python
# post_llm_call
def on_post_llm_call(agent_name: str, session_id: str,
                     response: str, reasoning: str | None,
                     tokens_in: int, tokens_out: int) -> None:
    db.insert_turn(session_id, role="assistant",
                   content=response, reasoning=reasoning,
                   metadata={"tokens_in": tokens_in, "tokens_out": tokens_out})

# post_tool_call
def on_post_tool_call(agent_name: str, session_id: str,
                      call_id: str, tool_name: str,
                      arguments: dict, result: dict) -> None:
    db.insert_tool_call(call_id, session_id, tool_name,
                        arguments=json.dumps(arguments),
                        result=json.dumps(result))

# on_session_end
def on_session_end(agent_name: str, session_id: str,
                   final_status: str) -> None:
    db.update_session(session_id, status=final_status, completed_at=time.time())

# pre_llm_call
def on_pre_llm_call(agent_name: str, session_id: str) -> str | None:
    directives = db.consume_steering(session_id)
    if directives:
        return "\n".join(directives)
    return None
```

## 7. Migration Plan (v2 -> v3)

### Eliminar
- `pi_adapter.py` -- Pi Agent Server spawn, sin uso
- `event_translator.py` -- traduccion de eventos Pi Agent, reemplazado por hooks
- `soul_to_system.py` -- conversion .pi/ configs, los perfiles hermes-agent ya tienen SOUL.md
- `SessionBuffer` -- buffer en memoria, reemplazado por SQLite
- `.pi/` configs por profile -- duplicados de perfiles hermes-agent

### Modificar
- `server.py` -- herramientas MCP cambian de Pi Agent RPC a ACP + SQLite
- `consult_action.py` -- cambiar de leer buffers Pi Agent a leer SQLite
- `discovery.py` -- cambiar de `.pi/` configs a `profiles.get_profile_dir()`

### Crear
- `acp_manager.py` -- basado en v1 `acp_client.py`, sin session_update
- `db.py` -- SQLite con 4 tablas, WAL mode
- `olympus_v3_hooks/` -- plugin con 4 hooks

### Migrar perfiles Daimon
Los 7 perfiles en `~/.hermes/profiles/` ya existen (`ariadna`, `athena`, `daedalus`, `etalides`, `hefesto`, `hermes`, `ictinus`). Solo necesitan:
1. Agregar `plugins/olympus_v3/` con el plugin registrado
2. Eliminar cualquier referencia a `.pi/` configs
3. Verificar que `config.yaml` no tenga dependencias de Pi Agent


## 8. Differences from v1 (ACP puro) and v2 (Pi Agent RPC)

| Aspecto | v1 (ACP streaming) | v2 (Pi Agent RPC) | v3 (ACP + SQLite) |
|---------|---------------------|-------------------|-------------------|
| Transporte | ACP | Pi Agent RPC | ACP |
| Observabilidad | Streaming fragments | event_translator + buffer | Plugin hooks -> SQLite |
| Delimitacion de turnos | No (fragmentos) | Parcial (buffer) | Si (post_llm_call por turno) |
| Finalizacion | Callback fragil | agent_end sin texto | on_session_end confiable |
| Steering | No posible | No posible | pre_llm_call -> SQLite steering |
| Auditoria de tools | No | No | post_tool_call -> SQLite |
| Estado compartido | En memoria | En memoria | SQLite WAL (persistente, concurrente) |
| Perfiles | .pi/ configs separados | .pi/ configs separados | Perfiles hermes-agent existentes |
