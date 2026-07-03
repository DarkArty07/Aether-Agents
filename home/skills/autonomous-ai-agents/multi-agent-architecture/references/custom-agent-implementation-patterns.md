# Custom Agent Implementation Patterns — From Requiem Agents Phase 3

Concrete code patterns for building custom multi-agent systems WITHOUT an agent framework (no hermes-agent, no LangChain, no crewAI). These patterns emerged from implementing Requiem Agents Phase 3 (Necromancer + Revenant + Shades).

## Project Layout

```
project-root/
├── necromancer/
│   ├── tools.py                 # Tool registry with role-based subsets
│   ├── soul.md                  # Orchestrator system prompt
│   ├── revenant_soul.md         # Auditor system prompt
│   ├── revenant.py              # Auditor module (peer of orchestrator)
│   ├── necromancer.py           # Orchestrator with decompose-delegate-audit loop
│   └── shades/
│       ├── programming.md       # Programming executor system prompt
│       └── research.md          # Research executor system prompt
├── requiem-mcp/
│   └── server.py                # MCP server bridging assistant → orchestrator
└── shared/
    ├── opencode_client.py       # LLM API client
    └── eval.py                  # Telemetry/logging
```

Key principle: system prompts live in `.md` files (soul files), loaded at runtime. This separates prompt engineering from application logic.

## Pattern 1: Tool Registry with Role-Based Subsets

**File:** `tools.py`

Define all tools as pure functions, then group them into role-based registries (dicts). An `execute_tool()` dispatcher routes calls.

```python
# 1. Define tools as pure functions
def read_file(path: str, max_lines: int = 500) -> str:
    ...

def write_file(path: str, content: str) -> str:
    ...

def search_files(directory: str, pattern: str, max_results: int = 20) -> str:
    ...

def run_terminal(command: str, cwd=None, timeout: int = 30) -> str:
    ...

# 2. Create role-based registries
ALL_TOOLS = {
    "read_file": read_file,
    "write_file": write_file,
    "search_files": search_files,
    "terminal": run_terminal,
}

READ_ONLY_TOOLS = {
    "read_file": read_file,
    "search_files": search_files,
}

WRITE_TOOLS = {
    "read_file": read_file,
    "write_file": write_file,
    "search_files": search_files,
    "terminal": run_terminal,
}

# 3. Dispatcher
def execute_tool(tool_name: str, tool_registry: dict, **kwargs) -> str:
    func = tool_registry.get(tool_name)
    if not func:
        return f"Error: Tool '{tool_name}' not available"
    try:
        return func(**kwargs)
    except Exception as e:
        return f"Error executing {tool_name}: {e}"
```

**Advantages:**
- No framework dependency — pure Python, works anywhere
- Role-based access is transparent and auditable (one dict per role)
- Dispatcher handles errors uniformly
- Easy to add new tools: write function + add to dict

## Pattern 2: Soul-Based System Prompts

Each agent gets a `.md` file loaded at runtime:

```python
def load_soul(path: str) -> str:
    with open(path, "r") as f:
        return f.read()

# Usage
system_prompt = load_soul("necromancer/shades/programming.md")
result = await chat_completion(
    messages=[...],
    model=model,
    system_prompt=system_prompt,
    max_tokens=16384,
)
```

**Soul file structure** (target 40-120 lines per agent):
1. **Identity** — name, role, theme, framework
2. **What You Do** — numbered list of responsibilities
3. **What You NEVER Do** — hard limits (critical for safety)
4. **Output Format** — mandatory response structure
5. **Principles** — quality guidelines

**Avoid in soul files:** few-shot examples, detailed protocols, checklists, workflow context. These belong in skills loaded on-demand.

## Pattern 3: Decompose → Delegate → Audit → Retry → Escalate

### Critical Sub-Pattern: Artifact Metadata Passing

The auditor (Revenant) needs to inspect the worker's outputs to verify them. But the worker's final message (its summary) often doesn't include the file paths it created — those are in the tool call arguments, not the final text. This causes the auditor to fail because it can't find what the worker produced.

**Solution:** Before passing worker output to the auditor, the orchestrator collects all `write_file` tool call paths from the agentic loop and appends them to the output in a format the auditor can parse:

```python
async def run_shade(shade_name, task, project_root, session_id, task_id):
    files_written = []  # ← Track across all iterations

    for iteration in range(15):
        result = await chat_completion(messages=messages, ...)
        final_content = result["content"]

        tool_calls = parse_tool_calls(content)
        if not tool_calls:
            break

        messages.append({"role": "assistant", "content": content})

        for tc in tool_calls:
            # ← Track write_file calls before executing
            if tc["name"] == "write_file" and "path" in tc["args"]:
                files_written.append(tc["args"]["path"])

            tool_output = execute_tool(tc["name"], tools, **tc["args"])
            messages.append({"role": "user", "content": f"Tool result ({tc['name']}):\n{tool_output}"})

    # ← Append artifact metadata to final output
    if files_written:
        final_content += "\n\n## Files Created/Modified\n"
        for fp in files_written:
            final_content += f"- File written: {fp}\n"

    return {"output": final_content, ...}
```

The auditor then searches for the `"File written:"` pattern to discover artifact paths:

```python
def extract_file_paths(shade_output: str) -> list[str]:
    paths = []
    for line in shade_output.split("\n"):
        if line.startswith("- File written:"):
            path = line.split(":", 1)[1].strip()
            paths.append(path)
    return paths
```

**Why this works:**
- The worker's final summary is human-readable (what it did)
- The appended file list is machine-parseable (what it created)
- The auditor can read both: the summary tells the story, the paths let it check the files
- Both travel together in `shade_result["output"]`, so no separate metadata channel is needed

**Alternative considered — and why it's worse:** Having the orchestrator maintain a side-channel (separate dict of files per subtask) adds complexity without value. The auditor already receives the full output string — embedding metadata there keeps the interface simple and the audit call unchanged.

The core orchestrator loop:

```python
MAX_REVENANT_RETRIES = 3

async def process_task(project_root, project_name, formal_task, session_id):
    # 1. Decompose: orchestrator splits task into subtasks
    decomposition = await chat_completion(
        system_prompt=necro_soul,  # loaded from soul.md
        messages=[decompose_prompt],
    )
    subtasks = json.loads(extract_json(decomposition["content"]))

    # 2. For each subtask: delegate → audit → retry or escalate
    for subtask in subtasks:
        shade_name = subtask.get("shade", "programming")
        shade_task = subtask.get("task", "")

        retries = 0
        while retries < MAX_REVENANT_RETRIES:
            # Delegate to shade
            shade_result = await run_shade(shade_name, shade_task, ...)

            # Audit with revenant (peer, not subordinate)
            audit_result = await audit(shade_result["output"], shade_task, ...)

            if audit_result["verdict"] == "pass":
                results.append({"shade": shade_name, "audit": "pass"})
                break
            elif retries >= MAX_REVENANT_RETRIES - 1:
                results.append({"shade": shade_name, "audit": "escalated", "escalated": True})
                break
            else:
                retries += 1
                # Retry with revenant's feedback
                shade_task = f"""Original: {shade_task}
Revenant feedback: {audit_result['feedback']}
Fix and redo."""
```

**Key rules enforced by code:**
- Revenant is a peer — orchestrator calls audit, cannot override verdict
- Escalation is bounded — 3 retries max, then escalate to assistant layer
- Each retry includes the previous feedback — prevents infinite loops

## Pattern 4: MCP Server Integration

The assistant (Raven) communicates with the orchestrator (Necromancer) via MCP tools. The orchestrator and its sub-agents never expose MCP — they're invoked programmatically within the same process.

```python
# MCP tool that bridges assistant → orchestrator
@server.call_tool()
async def call_tool(name, arguments):
    if name == "activate_necromancer":
        result = await process_task(
            project_root=arguments["project_root"],
            project_name=arguments["project_name"],
            formal_task=arguments["formal_task"],
            session_id=str(uuid.uuid4()),
        )
        return [TextContent(text=format_results(result))]
```

**Architecture boundary:**
- MCP layer: Raven (assistant, user-facing) ↔ Necromancer
- In-process: Necromancer → Revenant (audit function call)
- In-process: Necromancer → Shades (async LLM calls with different system prompts)

**⚠ Pitfall — blocking MCP tool kills user visibility:** The `activate_necromancer` pattern shown above blocks the calling agent for the full pipeline duration (2-10 minutes). The assistant has zero visibility during execution and cannot narrate progress to the user. For interactive vibecoding, split into granular tools (decompose/execute/progress/result) with async background execution and polling. The assistant's SOUL must define the polling loop explicitly. The orchestrator (not the assistant) should get the more expensive model when decomposition is more cognitively demanding than formalizing intent. See `references/mcp-visibility-pattern.md` for the full pattern including code structure, state tracking, and SOUL template.

## Verification Pattern

After creating Python files, verify syntax immediately:

```bash
python3 -m py_compile /path/to/file.py
```

This catches syntax errors, undefined names, and import resolution issues before runtime. Run it for EVERY `.py` file created or modified.

## Directory Preparation

Before writing files, ensure directories exist:

```python
import os
os.makedirs("necromancer/shades", exist_ok=True)
# or in shell:
# mkdir -p necromancer/shades requiem-mcp shared
```

This prevents "No such file or directory" errors from file writes.

## Common Pitfalls

- **sys.path manipulation:** Relying on `sys.path.insert(0, ...)` at module import time. Better to set `PYTHONPATH` or `REQUIEM_PROJECT_ROOT` env var, or use proper package structure with `__init__.py`.
- **Imports that depend on modules that don't exist yet:** `from shared.opencode_client import chat_completion` will fail at import time if `shared/opencode_client.py` doesn't exist. Make sure shared modules are implemented before importing them in orchestrator/auditor modules.
- **JSON parsing from LLM output:** The LLM may not output clean JSON. The Requiem implementer handles this by first trying to extract a `{...}` block from the response, then falling back to a default (single subtask to programming shade). Always have a fallback.
- **Tool output truncated in reports:** In MCP responses, Shade output can be thousands of lines. Truncate to ~2000 chars in the response to Raven, with a note that full output is available.
- **Asyncio in MCP:** All MCP tool handlers must be async. Orchestrator and audit functions must use `async def` and `await` for LLM calls.
- **Directory name vs Python import name:** If your MCP server directory uses a hyphen (e.g., `requiem-mcp/`), but `config.yaml` references it as a Python module (e.g., `command: python3.11 -m requiem_mcp.server`), the import will fail — Python module names cannot contain hyphens. Check this BEFORE running `hermes mcp test` — the error message is cryptic (`ModuleNotFoundError: No module named 'requiem_mcp'`).

  **Fix options (in order of preference):**
  1. **Name the directory with underscores from the start** (`requiem_mcp/` not `requiem-mcp/`). Prevention is cheaper than cure.
  2. **Symlink:** `ln -s /path/to/requiem-mcp /path/to/requiem_mcp`. Works because Python resolves the symlink to a valid package name. Add the symlink to `.gitignore`.
  3. **PYTHONPATH in config.yaml env:** hermes-agent spawns MCP servers as subprocesses. The `env:` section in `config.yaml` is passed to that subprocess. If the MCP server imports from sibling directories (e.g., `shared/`, `necromancer/`), add `PYTHONPATH: /path/to/project-root` to the env section:

  ```yaml
  mcp_servers:
    requiem-mcp:
      command: /path/to/venv/bin/python3.11
      args:
        - -m
        - requiem_mcp.server
      env:
        REQUIEM_PROJECT_ROOT: /path/to/project-root
        PYTHONPATH: /path/to/project-root  # critical: subprocess needs this to find the package
  ```

  **Subtle trap:** `sys.path.insert(0, project_root)` inside `server.py` CANNOT fix the `-m` module import. Python resolves the module name (`requiem_mcp.server`) BEFORE executing server.py, so the sys.path manipulation runs too late. The PYTHONPATH env var (or symlink) must be in place BEFORE the subprocess starts. `sys.path.insert` inside server.py IS still useful for importing sibling packages (`shared/`, `necromancer/`) — it just can't fix the initial `-m` resolution.

  **Symptom:** hermes-agent shows "requiem-mcp (stdio) — connecting" in the startup banner and never transitions to "connected". The assistant reports it has no MCP tools. No error is printed to the console because the subprocess fails silently on import.

## Pattern 5: Text-Based Tool Calling Protocol (Agentic Loop)

Custom agents (no framework) need a way to call tools. Native function-calling API features are provider-specific and not always available. The solution: a **text-based JSON protocol** where the model outputs tool calls as JSON blocks, and the orchestrator parses and executes them.

### The Protocol

The system prompt teaches the model to emit tool calls as JSON on their own lines:

```
## Available Tools
To use a tool, output a JSON block on its own line:
{"tool_call": {"name": "tool_name", "args": {"arg1": "value1", "arg2": "value2"}}

Available tools:
- read_file(path): Read a file
- write_file(path, content): Write a file
```

### The Agentic Loop

```python
async def run_shade(shade_name, task, project_root, session_id, task_id):
    system_prompt = load_shade_soul(shade_name) + tool_instructions
    tools = WRITE_TOOLS if shade_name == "programming" else RESEARCH_TOOLS

    messages = [{"role": "user", "content": f"## Task\n{task}\n\nExecute using your tools."}]

    for iteration in range(15):  # max iterations — prevent infinite loops
        result = await chat_completion(messages=messages, model=model, system_prompt=system_prompt)
        content = result["content"]

        tool_calls = parse_tool_calls(content)
        if not tool_calls:
            break  # no more tool calls — agent is done

        messages.append({"role": "assistant", "content": content})
        for tc in tool_calls:
            tool_output = execute_tool(tc["name"], tools, **tc["args"])
            # Truncate long outputs to prevent context explosion
            if len(tool_output) > 2000:
                tool_output = tool_output[:2000] + f"\n... (truncated, {len(tool_output)} chars total)"
            messages.append({"role": "user", "content": f"Tool result ({tc['name']}):\n{tool_output}"})

        # Context budget — stop if consuming too many tokens
        if total_input_tokens > 50000:
            break
```

### Critical Bugs Found During Testing (and their fixes)

**Bug 1 — `json.loads(strict=False)`: Model outputs JSON with LITERAL NEWLINES inside string values (e.g., the `content` field of a `write_file` call contains actual newline characters, not `\\n` escape sequences). Python's `json.loads()` with default `strict=True` rejects literal control characters inside strings. The parser finds the JSON block but `json.loads()` silently fails, returning 0 tool calls. The model appears to "not use tools" when actually the parser is rejecting valid JSON.

```python
# WRONG — silently fails on model output with literal newlines
parsed = json.loads(json_str)

# CORRECT — strict=False accepts literal control characters per RFC 7159
parsed = json.loads(json_str, strict=False)
```

**Symptom:** Debug log shows `Iteration 1: 0 tool calls found` but the model output clearly contains `{"tool_call": {"name": "write_file", "args": {"content": "import csv\n..."}}}`. The JSON is structurally valid but has literal newlines.

**Bug 2 — Brace escaping in `.format()` templates:** If you use Python `.format()` to build tool instructions (e.g., inserting tool descriptions), ALL literal JSON braces in the example must be doubled (`{{` produces `{`, `}}` produces `}`). Otherwise `.format()` interprets `{"tool_call":` as a format placeholder and crashes with `KeyError`.

```python
# WRONG — .format() treats {"tool_call": ...} as a placeholder
TOOL_TEMPLATE = '{"tool_call": {"name": "tool_name", "args": {"arg1": "value1"}}}\n{tool_descriptions}'

# CORRECT — literal braces doubled, only {tool_descriptions} is a real placeholder
TOOL_TEMPLATE = '{{"tool_call": {{"name": "tool_name", "args": {{"arg1": "value1"}}}}}}\n{tool_descriptions}'
```

**Bug 3 — Infinite loop in brace-counting parser:** When parsing tool calls by counting `{` and `}` to find JSON boundaries, if the JSON is malformed (unbalanced braces), `brace_count` never reaches 0. The parser stays at the same position and `search_start` never advances — infinite loop consuming 100% CPU.

```python
# WRONG — search_start only advances on success
if brace_count == 0:
    search_start = end  # never set if unbalanced → infinite loop

# CORRECT — always advance past the match
if brace_count == 0:
    search_start = end
else:
    search_start = idx + len('{"tool_call":')  # skip malformed match
```

**Bug 4 — Context explosion:** Without a budget, tool results accumulate in the messages array. A Shade reading a large file can consume the entire context window in one call. Two mitigations:
- Truncate tool outputs to 2000 chars before appending to messages
- Break the loop if total_input_tokens exceeds 50000

**Bug 5 — Auditor auto-fail for creation tasks:** An LLM-based auditor can "PASS" a task where no files were actually created — it reads the worker's summary text and thinks the work is done. For tasks containing creation keywords ("create", "write", "implement", "build"), if `extract_file_paths()` returns empty, skip the model call and return FAIL immediately. This saves tokens AND prevents false passes.

```python
creation_words = ['create', 'write', 'implement', 'build', 'add', 'generate']
if any(w in task_spec.lower() for w in creation_words) and not file_paths:
    return {"verdict": "fail", "feedback": "No files were created. Use write_file NOW."}
```

### Debugging Multi-Agent Systems via Telemetry

When testing a multi-agent system, you often can't see what's happening inside subprocesses. The SQLite telemetry DB is your observability layer.

**Technique:** While a task is running, poll the DB every 30-60 seconds:

```bash
sqlite3 shared/state.db "SELECT id, agent_name, action, result, input_tokens, output_tokens, duration_seconds FROM agent_calls WHERE session_id='test-001' ORDER BY id;"
```

This tells you:
- Which agent is currently running (last row without a terminal result)
- Whether tokens are being consumed (non-zero input/output tokens)
- Whether the auditor is rejecting (result=fail) or approving (result=pass)
- Whether retries are happening (same agent_name appears multiple times)
- Whether escalation occurred (result=escalated)
- Duration per call — if a Shade takes under 5s, it's probably not doing real work

**Process inspection:** If the DB shows no progress for minutes, check the process:
```bash
pgrep -P <parent_pid> | xargs ps -o pid,stat,time,cmd -p
# Rl state + high CPU time = infinite loop (see Bug 3 above)
# S state + low CPU time = waiting on API call (normal)
```
