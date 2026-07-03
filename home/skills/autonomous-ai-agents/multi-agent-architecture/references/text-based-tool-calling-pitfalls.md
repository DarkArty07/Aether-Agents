# Text-Based Tool Calling — Critical Pitfalls

When building custom agents that use text-based JSON tool calling (no native function-calling API), these bugs WILL surface during integration testing. All were found during a 2-hour end-to-end test of Requiem Agents.

## Pitfall 1: json.loads() rejects literal newlines in string values

**Symptom:** The model outputs a perfectly structured tool call with correct JSON, but `parse_tool_calls()` returns an empty list. Debug logging shows "0 tool calls found" even though the JSON is visible in the output.

**Root cause:** Models generate JSON with LITERAL newline characters inside string values (especially in the `content` field of `write_file` calls). Python's `json.loads()` with the default `strict=True` rejects literal control characters inside strings.

```python
# Model outputs this (with actual newlines, not \n escape sequences):
{"tool_call": {"name": "write_file", "args": {"path": "/tmp/test.py", "content": "import csv
from pathlib import Path

def csv_to_json(path):
    ...
"}}}

# json.loads(content, strict=True)  → JSONDecodeError
# json.loads(content, strict=False) → parses correctly
```

**Fix:** Always use `strict=False` when parsing model-generated JSON:
```python
parsed = json.loads(json_str, strict=False)
```

This is a one-line fix but it's the difference between the system working and not working. Without it, NO tool calls will ever be parsed if the tool arguments contain multi-line strings.

## Pitfall 2: .format() brace escaping in template strings

**Symptom:** `_build_tool_instructions()` crashes with `KeyError: '"tool_call"'` when trying to format the tool instructions template.

**Root cause:** If you use Python `.format()` on a template string that contains JSON examples (like `{"tool_call": ...}`), the `{` and `}` are interpreted as format placeholders, not literal braces.

```python
# BROKEN — .format() tries to substitute {"tool_call": ...} as a key
TOOL_INSTRUCTIONS_TEMPLATE = """
Output tool calls as: {"tool_call": {"name": "...", "args": {...}}}
Available tools: {tool_descriptions}
"""
return TOOL_INSTRUCTIONS_TEMPLATE.format(tool_descriptions="...")  # KeyError!

# FIXED — double all literal braces
TOOL_INSTRUCTIONS_TEMPLATE = """
Output tool calls as: {{"tool_call": {{"name": "...", "args": {{...}}}}}}
Available tools: {tool_descriptions}
"""
return TOOL_INSTRUCTIONS_TEMPLATE.format(tool_descriptions="...")  # OK
```

**Rule:** In any string that will be passed to `.format()`, escape ALL literal `{` as `{{` and `}` as `}}`. Only intentional placeholders like `{tool_descriptions}` remain single-braced.

**Alternative:** Use f-strings or string concatenation instead of `.format()` to avoid this class of bug entirely.

## Pitfall 3: Infinite loop in custom JSON parser with unbalanced braces

**Symptom:** The agentic loop hangs at 100% CPU, never advancing past the first iteration. The process runs for minutes with no output.

**Root cause:** When parsing for `{"tool_call":` patterns, if the model outputs a malformed/truncated JSON block with unbalanced braces, the brace-counting loop never reaches `brace_count == 0`. The `end` variable stays at `start`, and `search_start = end` doesn't advance — the while loop finds `{"tool_call":` at the same position forever.

**Fix:** Ensure `search_start` ALWAYS advances, even when braces are unbalanced:
```python
if brace_count == 0:
    # Normal path: parse the JSON, advance past it
    json_str = content[start:end]
    parsed = json.loads(json_str, strict=False)
    # ... append to results ...
    search_start = end
else:
    # Unbalanced braces: skip past this match to avoid infinite loop
    search_start = idx + len('{"tool_call":')
```

**Rule:** Any parser that searches for patterns in a loop must guarantee the search position advances on EVERY iteration, regardless of parse success/failure.

## Pitfall 4: Context explosion in agentic loops

**Symptom:** A Shade's input tokens spike to 90K+ in a single API call, making the system unusably expensive.

**Root cause:** Each tool execution appends its result to the `messages` list. Tool results (especially `read_file` of large files or `search_files` of large directories) can be thousands of characters. Over 15 iterations, the messages array grows unboundedly.

**Fix:** Two measures:
1. **Truncate tool results** before appending:
```python
if len(tool_output) > 2000:
    tool_output = tool_output[:2000] + f"\n... (truncated, full output was {len(tool_output)} chars)"
```

2. **Context budget check** — stop the loop if total input tokens exceed a threshold:
```python
if total_input_tokens > 50000:
    break  # Stop to prevent context explosion
```

## Pitfall 5: Auditor approves output with no artifacts

**Symptom:** The Revenant (auditor) returns PASS for a Shade output that created zero files — a 300-token text summary with no actual code.

**Root cause:** The auditor only sees the Shade's final text output. If the Shade didn't write any files (just described what it would do), the auditor has no way to know — it's auditing text, not code.

**Fix — two layers:**

1. **Pre-check in auditor:** If the task contains creation keywords ("create", "write", "implement", "build") AND no file paths were found by `extract_file_paths()`, auto-fail WITHOUT calling the model:
```python
creation_words = ['create', 'write', 'implement', 'build', 'add', 'generate']
is_creation_task = any(w in task_spec.lower() for w in creation_words)
if is_creation_task and not file_paths:
    return {"verdict": "fail", "feedback": "No files were created. USE write_file NOW."}
```

This saves tokens (no model call needed) and prevents false passes.

2. **File verification:** The auditor should read actual files from disk and compile `.py` files before making a verdict:
```python
for fp in file_paths:
    if os.path.isfile(fp):
        content = read_file(fp)
        file_contents += f"### {fp}\n{content}\n"
        if fp.endswith('.py'):
            compile_results += compile_py_file(fp)  # python -m py_compile
```

## Pitfall 6: Worker's final summary doesn't contain file paths

**Symptom:** The auditor's `extract_file_paths()` finds no paths even though files WERE created — because the paths are in tool call arguments, not in the worker's final text summary.

**Root cause:** The agentic loop returns only the LAST assistant message (the summary). Tool call arguments from earlier iterations are lost.

**Fix:** Track all `write_file` paths during the loop and append them to the final output:
```python
files_written = []
for tc in tool_calls:
    if tc["name"] == "write_file" and "path" in tc["args"]:
        files_written.append(tc["args"]["path"])
    # ... execute tool ...

# After loop, before returning:
if files_written:
    final_content += "\n\n## Files Created/Modified\n"
    for fp in files_written:
        final_content += f"- File written: {fp}\n"
```

The `"File written:"` prefix matches the pattern the auditor's `extract_file_paths()` searches for. This is already documented in the main patterns file as "Artifact Metadata Passing" but is listed here as a pitfall because it manifests as "auditor can't find files" rather than "missing metadata."

## Pitfall 7: Model outputs incomplete JSON (missing closing braces)

**Symptom:** The Shade outputs a valid-looking `write_file` tool call with long content, but `parse_tool_calls()` finds 0 tool calls. The file is never written. The auditor auto-fails. Telemetry shows high input tokens (40-50K) but 0 files created.

**Root cause:** Flash models sometimes truncate their output before closing all JSON braces. A `write_file` call with a 200-line file as content needs three closing braces (`"}}}`), but the model may output only two (`"}}`). The brace-counting parser never reaches `brace_count == 0`, so the JSON is never extracted.

**Fix:** When braces are unbalanced, REPAIR the JSON by counting the deficit and appending missing `}` characters:
```python
if brace_count == 0:
    # Normal path
    json_str = content[start:end]
    parsed = json.loads(json_str, strict=False)
else:
    # Unbalanced — try to repair
    json_str = content[start:]
    open_count = count_braces(json_str, '{')
    close_count = count_braces(json_str, '}')
    missing = open_count - close_count
    if missing > 0:
        json_str += '}' * missing
        try:
            parsed = json.loads(json_str, strict=False)
            # If it parses, use it!
        except:
            pass  # Fall back to skip
```

This fix recovered ~60% of previously-failed tool calls in testing. The LinkedList task went from 3 Revenant rejections to first-try success.

## Pitfall 8: Model uses \' (backslash-single-quote) in JSON strings

**Symptom:** `json.loads()` rejects model output even when braces are balanced. The error is cryptic — just "Expecting ',' delimiter".

**Root cause:** Some models escape single quotes as `\'` inside JSON strings. This is NOT valid JSON — JSON only defines `\"`, `\\`, `\/`, `\b`, `\f`, `\n`, `\r`, `\t`, and `\uXXXX`. Python's `json.loads()` with `strict=False` allows control characters but still rejects `\'`.

**Fix:** Strip `\'` → `'` before parsing:
```python
json_str = json_str.replace("\\'", "'")
parsed = json.loads(json_str, strict=False)
```

Apply this in BOTH the balanced-brace path and the repair path.

## Pitfall 9: Research-only agent loops forever making tool calls

**Symptom:** The research Shade runs all 15 iterations, each making 1+ tool calls (read_file, search_files), and never produces a tool-call-free summary. The loop hits the iteration limit with no final report.

**Root cause:** Research shades have read-only tools and no natural "done" signal. Unlike programming shades that stop after writing files, research shades keep exploring indefinitely — there's always more to read.

**Fix:** Inject a "wrap up" message at a midpoint iteration:
```python
if shade_name == "research" and iteration >= 10:
    messages.append({
        "role": "user",
        "content": "You have done enough research. Please write your findings summary now WITHOUT any tool_call JSON."
    })
```

This forces the research shade to produce a summary on the next iteration (which will have 0 tool calls, breaking the loop).

## Pitfall 10: Auditor's path extraction matches directories

**Symptom:** `extract_file_paths()` returns paths like `/home/user/project/` (a directory) instead of actual files. The auditor then tries to read a directory as a file, gets garbage, and may make incorrect verdicts.

**Root cause:** Using `os.path.exists()` to validate paths — this returns True for both files AND directories. If the model output contains the project root path (e.g., in a "Project Root: /home/user/project" line), it gets added as a "file path".

**Fix:** Always use `os.path.isfile()`:
```python
# BAD — matches directories too
if os.path.exists(candidate):
    paths.add(candidate)

# GOOD — only matches actual files
if os.path.isfile(candidate):
    paths.add(candidate)
```

## Performance Characteristics (Observed)

Metrics from two 2-hour testing sessions of Requiem Agents (8 tasks total, 110+ tests, all passing):

| Metric | Simple tasks (CSV, Stack, Set) | Complex tasks (LinkedList, ORM) | Execution tasks (pytest, find) |
|--------|-------------------------------|--------------------------------|--------------------------------|
| Total tokens per task | 4K-15K | 40K-60K (before fixes) → 14K (after) | 8K-12K |
| Completion time via Raven | 1-3 minutes | 3-7 minutes | 1-2 minutes (after fix) |
| Shade iterations | 2-4 | 6-12 (before fixes) → 3-4 (after) | 2-3 (after fix) |
| Revenant retries | 0-1 | 1-3 (before fixes) → 0-1 (after) | 0 (after fix) |
| Escalations to Raven | 0 | 1 (ORM task: Shade API errors) | 0 (after fix) |

Execution-task fix comparison (before → after combined A+B+C fix):
- Revenant verdict time: 0.0003s (auto-fail, no LLM) → 6.5s (LLM evaluation, correct verdict)
- Revenant result: FAIL (no files found) → PASS (command was run, output faithfully reported)
- Consecutive failures: 6 → 0 (PASS on first attempt)
- Shade routing: Programming Shade (wrong, tried write_file) → Execution Shade (correct, used terminal)

Key observations:
- **Flash model JSON truncation:** deepseek-v4-flash truncates JSON output when file content exceeds ~100 lines. ~40% of `write_file` calls with large content had missing closing braces before the repair fix. After repair, recovery rate was ~60% (some JSON is too damaged to salvage).
- **Research shade token cost:** Without forced summary injection, research shades consume 30-60K tokens hitting the 15-iteration limit every time. With the iteration-10 summary injection, they stop at iteration 10-12 with 10-20K tokens.
- **MCP timeout:** Default 600s is insufficient for complex multi-file tasks. LinkedList took 7 minutes end-to-end. Increase to 900s or implement streaming progress.
- **Auto-fail savings:** Revenant auto-fail (no model call for missing files) saves ~2K tokens per rejected iteration. Over 3 retries, that's 6K tokens saved per failed task.
- **Escalation absorption:** When Shades fail 3 times, the task doesn't fail — Raven absorbs it. The ORM task escalated but Raven fixed it directly, resulting in 19/19 passing tests. This is the system's key resilience property.
- **Multi-layer fix necessity:** The system-prompt-dominance problem (Pitfall 13) required fixes at THREE layers simultaneously — conditional prompts (A), auditor dual-path (B), and dedicated execution shade (C). Applying only one layer left the other two as failure points. This pattern likely generalizes: when a failure chain spans prompt + auditor + routing, fix all three layers in one commit, not incrementally.
- **Routing rules must be in the SOUL, not the decomposition prompt:** Adding Shade of Execution to the decomposition prompt's "Available Shades" list was insufficient — Necromancer kept routing to Programming. Adding explicit "Shade Routing Rules" to necromancer/soul.md (the system prompt loaded every time) fixed routing immediately. Confirmates Pitfall 16.

## Pitfall 11: Assistant agent has code tools despite SOUL saying NEVER

**Symptom:** The assistant agent (Raven) has a SOUL that says NEVER reads code, NEVER executes implementation commands, NEVER bypasses the Necromancer — but it reads files, runs pytest, and creates bridge modules directly after delegation.

**Root cause:** The SOUL is just a prompt. It tells the model what to do, but doesnt prevent it from using tools that are technically available. If the agent framework gives the assistant read_file, write_file, and terminal tools, the model WILL use them — especially when it sees an escalation and wants to help.

**Fix:** Restrict tools at the CONFIG level, not just the prompt level. In hermes-agent v0.17.0+, use `toolsets` (NOT `platform_toolsets`) in config.yaml:
```yaml
toolsets:
  - memory
  - skills
  - todo
  - requiem-mcp  # MCP server name counts as a toolset
```

**IMPORTANT — config key is `toolsets`, NOT `platform_toolsets`:** In hermes-agent v0.17.0, the config key for restricting tools is `toolsets` (a top-level array of toolset names). The key `platform_toolsets` (with a `cli:` sub-key) was used in earlier sessions based on incorrect assumptions and was SILENTLY IGNORED — the agent got all 30 tools instead of the restricted set.

**CLI LIMITATION — `toolsets` config only restricts messaging platform sessions, NOT the interactive CLI:** The interactive CLI (`hermes` in a terminal) ALWAYS loads the `hermes-cli` toolset (all 30 tools) regardless of what `toolsets:` says in config.yaml. The `toolsets` config key controls tool availability for messaging platform sessions (Telegram, Discord, Slack, etc.), not the interactive CLI session. To verify: run `hermes` in terminal, type `/tools` — if you see 30 tools despite `toolsets: [memory, skills, todo]` in config, the CLI is ignoring the restriction. This is BY DESIGN — the CLI is the full-power interactive surface. To enforce tool restrictions on an assistant agent, either: (a) run the agent via a messaging platform (Telegram/Discord) where `toolsets` IS respected, (b) run via the gateway API, or (c) accept that CLI sessions have full tools and rely on the SOUL prompt to prevent direct work (weaker but functional — the model generally follows SOUL instructions even with tools available). Verify with `hermes tools` or `/tools` in the TUI: if you see terminal, file, web tools despite the config, your restriction key is wrong. Check `hermes_cli/dump.py` and `hermes_cli/config.py` in the venv for the actual key name — `config.get("toolsets", ["hermes-cli"])`.

**Config format:** `toolsets` is a top-level flat list of toolset names. MCP server names in the list count as toolsets. Example:
```yaml
toolsets:
  - memory
  - skills
  - todo
  - requiem-mcp
```

**Restart required:** The agent must be restarted (kill tmux session, relaunch `hermes`) for toolset changes to take effect. The running process keeps its loaded toolset — config changes are only read at startup.

This physically removes terminal, file, web, browser, and code_execution tools from the assistant. The model can try to use them, but they dont exist — it falls back to MCP delegation.

**Measurable impact (from A/B comparison on Requiem Agents):**
- Revenant pass rate: 37% to 47% (+10%)
- Escalation rate: 73% to 50% (-23%)
- Shade input tokens: 888K to 459K (-48%)
- Shade output tokens: 176K to 61K (-65%)
- Direct work by assistant: completely eliminated

The token reduction comes from the Necromancer including run tests as a subtask (Shades verify before reporting), so fewer Revenant rejections and retry cycles.

## Pitfall 12: Necromancer doesnt include test-running in decomposition

**Symptom:** Shades write code and tests, but the Necromancer never instructs them to RUN the tests. The Revenant audits the code but cant verify runtime behavior. Tests may exist but have import errors or logic bugs that only surface at execution time.

**Root cause:** The Necromancers decomposition only includes write code and write tests subtasks. Running tests (pytest) is a separate step that the Shade of Programming can do with its terminal tool, but its never explicitly assigned.

**Fix:** Update the Necromancer SOUL to always include a final subtask for the Shade of Programming to run tests. This ensures test output is part of the result returned to Raven. Without this, Raven would need to run tests itself (violating role separation) or the user would have to verify manually.

## Pitfall 13: System prompt dominance suppresses non-dominant tools

**Symptom:** The executor agent (Shade of Programming) has `terminal` as an available tool, but when the task is "run `find` and `pytest` and report results" (no file creation needed), the agent never uses `terminal`. Instead it tries `read_file` on random paths or `write_file` on non-existent paths. The Revenant rejects 3 times, escalation to user. Telemetry shows 6 consecutive failures across 2 attempts.

**Root cause:** The executor's system prompt contains aggressive imperatives biased toward ONE tool category:

```
"Your first action should ALWAYS be to create the requested files"
"Do NOT spend more than 2 iterations on reconnaissance — START WRITING"
"NEVER explain what you're going to do — just DO it with write_file immediately"
"ALWAYS write files FIRST, then verify"
```

When the task is "execute a command and report output" (not "create code"), the flash model (deepseek-v4-flash) cannot resolve the tension between task and identity. It defaults to the dominant behavior (write/read files) and never uses `terminal`. This is NOT a code bug — it's a prompt design gap.

**Three connected failures that form the full chain:**

1. **Prompt dominance:** The executor's system prompt is optimized for code-writing tasks. When the task is command-execution, the prompt's imperatives ("ALWAYS write files FIRST") actively suppress the correct tool (`terminal`). Flash models are especially vulnerable — they follow prompt defaults more rigidly than larger models.

2. **Auditor can't verify command output:** The Revenant's `audit()` function only verifies FILES:
   - `extract_file_paths()` scans for file paths in agent output
   - `compile_py_file()` compiles .py files
   - If no files found → `file_contents = "(No files found to verify)"`
   - The pre-check auto-fails if creation keywords are present AND no files exist
   
   When the task is "run `pytest` and report results," there are no files to verify. The auditor has no mechanism to check command output quality.

3. **No role for "execute and report" tasks:** The orchestrator (Necromancer) only has two Shades:
   - Programming: write code + terminal (but prompt biased toward writing)
   - Research: read + search (no terminal)
   
   There is no Shade or mode for "execute commands and report results." When the assistant asks for "read the code, run tests, detect problems" — a diagnostic task — the orchestrator routes it to Programming (the only one with terminal), but that Shade is optimized for writing, not diagnosing.

**Fix — three options (pick based on your system):**

A. **Soften the executor prompt** — add conditional language:
   ```
   If the task asks you to RUN COMMANDS (not create files), use the terminal tool directly.
   Do not create files unless the task explicitly asks for them.
   ```

B. **Add an auditor path for command output** — when no file paths are found but the task contains "run", "execute", "test", "find", the auditor should pass the Shade's text output to the model for review (not auto-fail).

C. **Add a "Diagnostics" Shade** — a third executor role with `terminal` + `read_file` + `search_files` but NO `write_file`, optimized for "run commands, read code, report findings." Its prompt says "run commands and report results, do NOT create files."

Option C is the cleanest — it solves all three failures at once by creating a role whose identity matches the task type. The prompt dominance problem disappears because the Diagnostics Shade's identity IS "execute and report."

**Combined fix validation (A+B+C all applied):** In practice, the most robust solution is applying ALL THREE options simultaneously:
- **A (conditional prompts):** Programming Shade's prompt now detects CREATION vs EXECUTION vs MODIFICATION tasks and switches imperatives — for EXECUTION tasks: "run the command FIRST, capture output, report" instead of "ALWAYS write files FIRST."
- **B (auditor dual-path):** Revenant's auto-fail pre-check now exempts execution tasks (checks `has_terminal_output`), and its soul has explicit "Auditing Execution Tasks" rules: PASS if command was run and output is faithfully reported, DO NOT fail because tests have failures.
- **C (dedicated execution shade):** Shade of Execution created with only `terminal` + `process` (no `write_file`), prompt says "run terminal FIRST, NEVER write files." Necromancer routes command-only tasks to this Shade via explicit routing rules in its soul.

Results after combined fix: execution tasks went from 6 consecutive failures to PASS on first attempt. Revenant LLM evaluation: 6.5s with correct verdict (vs 0.0003s auto-fail before). Set class task: 30/30 tests, 2/2 subtasks passed, 0 retries. Necromancer correctly routed execution subtasks to Shade of Execution instead of Shade of Programming.

**Key lesson:** An executor agent's system prompt creates a behavioral gravity well. If the prompt says "ALWAYS write files," the model will try to write files even when the task requires running commands. This is especially true for flash/cheap models. Either match the prompt to the task type (dedicated roles), or add explicit conditional language for non-dominant tool usage. When the problem spans prompt + auditor + routing, apply fixes at ALL three layers — a single-layer fix leaves the other two as failure points.

## Pitfall 14: Auditor auto-fail must be execution-task-aware

**Symptom:** The auditor (Revenant) auto-fails in 0.0003s (no LLM call) when the Shade ran terminal commands but didn't create files — even after adding an Execution Shade specifically for command-running tasks. The auto-fail pre-check fires because it sees creation keywords in the task spec and no file paths, ignoring that the Shade did useful execution work.

**Root cause:** The auto-fail logic in `audit()` checks:
```python
if is_creation_task and not file_paths:
    return {"verdict": "fail", ...}  # Auto-fail without LLM call
```

This doesn't account for:
1. Tasks that have BOTH creation AND execution words (e.g., "create module and run tests") — `is_creation_task` is True, auto-fail fires
2. Shades that ran terminal commands (output contains "Tool result (terminal):") but didn't write files — the auto-fail doesn't check for terminal output

**Fix — three conditions must ALL be true for auto-fail:**
```python
has_terminal_output = "Tool result (terminal):" in shade_output
if is_creation_task and not is_execution_task and not file_paths and not has_terminal_output:
    return {"verdict": "fail", ...}
```

Additionally, the `task_context` note (telling the Revenant LLM to judge execution quality) must be set whenever `is_execution_task` is True — NOT gated on `not file_paths`:
```python
# BAD — task_context only when no files (misses execution tasks that also created files)
task_context = "...execution task..." if is_execution_task and not file_paths else ""

# GOOD — task_context whenever execution task, regardless of files
task_context = "...DO NOT fail because tests have failures..." if is_execution_task else ""
```

**Key lesson:** Auto-fail logic must distinguish between "no files because Shade failed" and "no files because this is an execution task." Check for terminal output in the Shade's response and exempt execution tasks from the file-presence requirement.

## Pitfall 15: Auditor must judge execution quality, not test results

**Symptom:** The Revenant rejects the Execution Shade's output 3 consecutive times even though the Shade correctly ran `pytest` and faithfully reported the results (including which tests failed). The Revenant sees test failures in the output and fails the audit — but the Shade's job was to RUN and REPORT, not to make tests pass.

**Root cause:** The Revenant's review criteria say "Correctness — Does it do what was asked?" Without explicit guidance, the LLM interprets "correctness" as "do the tests pass?" rather than "did the Shade run the command and report accurately?"

**Fix — add execution-task auditing rules to the auditor's soul:**
```
## Auditing Execution Tasks

When the task was an execution task (running commands, tests, diagnostics — NOT creating code):
- The Shade's job is to RUN the command and REPORT results accurately
- PASS if: the command was executed and output is faithfully reported
- FAIL if: the command was not run, output is incomplete, or the report is misleading
- DO NOT fail because the tests themselves have failures — that is a code quality issue for the Programming Shade
- You audit the EXECUTION quality, not the test results
```

Also place the `task_context` note at the TOP of the auditor's user message (before the task spec), not at the bottom — the LLM processes it as framing context, not an afterthought.

**Key lesson:** An auditor's review criteria must differentiate between "did the worker do its job correctly" and "is the output of the task successful." For execution tasks, the worker's job is to run and report — test failures are the code's problem, not the executor's.

## Pitfall 16: New agent roles need explicit routing rules in orchestrator's soul

**Symptom:** After adding a new Shade of Execution (specialized for running commands), the Necromancer continues routing all tasks to Shade of Programming — even when the task is "run pytest and report results." The new Shade is listed in the decomposition prompt's available agents, but the LLM ignores it.

**Root cause:** Listing a new agent in the "Available Shades" section of the decomposition prompt is insufficient. The LLM defaults to the most familiar agent (Programming) unless given explicit routing rules. The decomposition prompt says "Available Shades: Programming, Research, Execution" but doesn't say WHEN to use each.

**Fix — add explicit routing rules to the orchestrator's soul:**
```
## Shade Routing Rules

- Task involves RUNNING commands (pytest, find, lint, check, audit, diagnose) → Shade of Execution
- Task involves WRITING code (create, implement, build, add features) → Shade of Programming
- Task involves READING/SEARCHING (investigate, understand, analyze codebase) → Shade of Research
- Task involves BOTH writing code AND running tests → Decompose into 2 subtasks: Programming (write) + Execution (run tests)
- When in doubt: does the task create files? If yes → Programming. If no → Execution or Research.
```

Without explicit rules, the LLM will use the most general-purpose agent for everything. The routing rules must be in the SOUL (system prompt), not just in the decomposition prompt — the SOUL is loaded every time, the decomposition prompt is generated per task.

**Key lesson:** Adding a new agent role to a multi-agent system requires updating the orchestrator's routing logic, not just registering the agent. The orchestrator LLM needs explicit rules for WHEN to use each agent, not just a list of available agents.

## Pitfall 17: Prompt-based routing insufficient — add code-level override

**Symptom:** Even with explicit routing rules in the orchestrator's SOUL (Pitfall 16), the LLM still misroutes tasks. "Run pytest" gets sent to Programming Shade instead of Execution Shade. The SOUL says "use Execution Shade for running commands" but the LLM ignores it.

**Root cause:** LLMs don't reliably follow routing instructions in system prompts, especially medium-tier models (GLM-5.2). The SOUL is a suggestion, not a constraint.

**Fix:** Implement a `_override_shade()` function in the orchestrator code that pattern-matches the subtask text and deterministically overrides the LLM's shade selection. Check execution keywords FIRST (pytest, run tests, execute), then creation (create, write, implement), then research (investigate, analyze). Only override when keywords from ONE category are present — mixed tasks keep the LLM's choice. Log overrides with `[Routing Override] original -> new (pattern match)` for debugging.

**Key insight:** Only override when keywords from exactly ONE category match. If a task mentions both "create" and "pytest" (e.g., "create a class and run tests"), keep the LLM's choice — the task spans multiple shades and the LLM's decomposition is probably correct.

---

## Pitfall 18: Shade output doesn't include tool results — auditor can't verify execution

**Symptom:** The Revenant's auto-pass checks shade_output for "passed" but never triggers, even when the Shade of Execution ran pytest and got "11 passed". The Revenant LLM is called instead, and often returns FAIL.

**Root cause:** `shade_output` is `final_content` — the Shade's LAST assistant message. Tool results (terminal output containing "11 passed") are in conversation messages with role "user", not in the final assistant message. The auditor never sees the actual command output.

**Fix:** In `run_shade()`, append terminal tool results to `final_content` for execution shades:
```python
if shade_name == "execution":
    for msg in messages:
        if msg["role"] == "user" and "Tool result (terminal):" in msg["content"]:
            final_content += "\n" + msg["content"]
```

This ensures the auditor receives the full terminal output, not just the Shade's summary. Without this fix, the auto-pass (Pitfall 19) will never trigger because "passed" never appears in shade_output.

---

## Pitfall 19: Revenant false-negatives on execution tasks — add auto-pass

**Symptom:** Even with the auditor's soul saying "DO NOT fail because tests have failures", the LLM returns FAIL for execution tasks where all tests pass. This causes 3 unnecessary retries (14s × 1000+ tokens each) and escalation to the assistant.

**Root cause:** The auditor LLM (GLM-5.2) doesn't reliably follow negative instructions ("DO NOT fail because..."). It sees test output and applies its own judgment, which often conflicts with the instruction.

**Fix:** Add an auto-pass pre-check in the audit function, BEFORE calling the LLM:
```python
if shade_name == "execution" and is_execution_task:
    output_lower = shade_output.lower()
    has_pass_marker = "passed" in output_lower or "all checks passed" in output_lower
    has_fail_marker = "failed" in output_lower or "traceback" in output_lower
    if "0 errors" in output_lower or "no errors" in output_lower:
        has_fail_marker = False
    if "0 failed" in output_lower:
        has_fail_marker = False
    if has_pass_marker and not has_fail_marker:
        return {'verdict': 'pass', 'feedback': 'Auto-passed', 'input_tokens': 0, 'output_tokens': 0}
```

**Impact:** Eliminates 3 retries × 14s × 1000+ tokens per false-negative. Auto-pass takes 0ms and 0 tokens.

**Dependency chain:** This auto-pass REQUIRES Pitfall 18's fix (tool results appended to shade_output). Without it, "passed" never appears in shade_output and the auto-pass never triggers. The chain is: routing override (Pitfall 17) → execution shade gets the task → tool results in output (Pitfall 18) → auto-pass triggers (Pitfall 19). All three fixes must be present for execution tasks to work correctly.

---

## Debugging Methodology for Custom Agent Systems

A structured approach to diagnosing why a custom multi-agent system isn't producing expected outputs:

### Phase 1: Telemetry triage
Query the SQLite telemetry DB to see what's happening at each stage:
```
SELECT id, agent_name, action, result, input_tokens, output_tokens, duration_seconds
FROM agent_calls ORDER BY id DESC LIMIT 20;
```
Look for:
- `result='error'` rows → API failures (check error metadata)
- `result='fail'` with `input_tokens=0` → auto-fail logic triggered (no model call)
- `duration_seconds` near 0 with `result='fail'` → auto-fail, not model-based rejection
- High `input_tokens` (40K+) → context explosion or research shade looping

### Phase 2: Debug prints in critical functions
Add targeted print statements (flush=True) to:
- `run_shade()`: print `files_written` list and last 200 chars of `final_content` before return
- `audit()`: print `file_paths` list after `extract_file_paths()` and `shade_name`
- `parse_tool_calls()`: print number of tool calls found per iteration
- The agentic loop: print iteration count and tool call count per iteration

Run with `python -u` (unbuffered) so prints appear immediately. Pipe through `grep` to filter noise:
```bash
python -u test_script.py 2>&1 | grep -E 'DEBUG|Shade|ESCALATED|Audit|PASS|FAIL|Iteration|tool calls'
```

### Phase 3: Verify filesystem state
Never trust the agent's claim that files were created. Check the disk:
```bash
ls -la /path/to/output/
python3 -m pytest tests/ -v  # Run the tests the agent claims pass
```
If files exist but tests fail, the code quality issue is in the Shade's output, not the pipeline.
If files don't exist but the Shade claims success, the `write_file` tool call wasn't parsed/executed — go back to Phase 2 and check `parse_tool_calls()` output.

### Phase 4: Root cause identification
Correlate the debug output with the telemetry:
- `files_written count=0` but file exists on disk → `parse_tool_calls()` isn't finding the `write_file` call (check JSON completeness)
- `files_written count=0` and file doesn't exist → Shade never made a `write_file` call (check system prompt, shade soul instructions)
- `file_paths count=0` but `files_written count>0` → `extract_file_paths()` regex isn't matching the "File written:" prefix (check the appended section format)
- `file_paths` contains directories → using `os.path.exists()` instead of `os.path.isfile()`
- `result='error'` in telemetry → API call failed (check API key, rate limits, model availability)

### Phase 5: Fix and retest
Apply the fix, remove debug prints, recompile with `py_compile`, and rerun the test script. The fix is confirmed when:
- `files_written count > 0` in debug output
- `file_paths` matches `files_written` 
- Revenant returns `pass` on first attempt (not after retries)
- Tests created by the agent pass with `python -m pytest`
