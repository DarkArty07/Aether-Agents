# MCP → Native Plugin Migration Pitfalls

Case study: Requiem Agents v2 regression when migrating from MCP server to hermes-agent native plugin.

## Context

Requiem Agents started as a custom MCP server (`requiem_mcp`) exposing 4 granular async tools to the user-facing assistant (Raven):

- `decompose` — synchronous, returns the subtask plan immediately
- `execute` — async, launches the pipeline in background, returns immediately
- `progress` — reads in-memory state, returns current subtask/phase/iteration/audit result
- `result` — returns final results if completed, or "still_running"

This pattern (documented in `mcp-visibility-pattern.md`) worked well. Tasks completed in ~1 minute with full visibility.

The system was then migrated to a native hermes-agent plugin (`requiem_tools`) with 3 blocking tools:

- `investigate` — synchronous, runs Shade of Research to completion, returns result
- `execute` — synchronous, runs Shade of Execution to completion, returns result
- `implement` — synchronous, runs Shade of Programming + Revenant audit loop, returns result

After migration, tasks took 5 minutes, quality dropped, and the assistant lost all visibility during execution.

## 5 Regression Patterns

### 1. Blocking Tools Replace Granular Async Tools

**Before (MCP):** Raven calls `decompose` → gets plan → calls `execute` → returns immediately → polls `progress` every few seconds → narrates each phase to user → calls `result` when done.

**After (plugin):** Raven calls `investigate` → blocks for entire Shade run (5+ minutes) → no polling, no narration, no user visibility.

**Root cause:** The plugin tools are synchronous `_run_async()` wrappers that block until the entire Shade + Revenant pipeline completes. The 4-tool granular split was collapsed into 3 blocking calls.

**Fix:** Preserve the decompose-delegate-poll-result granularity in the plugin. Even native plugins can use background execution + in-memory state for polling. The tool surface must mirror the async lifecycle, not collapse it.

### 2. `disabled_toolsets` Contradicts SOUL.md

**Before (MCP):** Raven had `terminal`, `file`, `search_files` — it could read code directly for simple tasks.

**After (plugin):** Config has:
```yaml
agent:
  disabled_toolsets:
    - terminal
    - file
```

But Raven's SOUL.md says: "READ the codebase — explore files using `read_file`, `search_files`, and `terminal` tools" and "Simple (1 file, <50 lines): Raven writes directly using `write_file`".

**Result:** Raven tries to follow its SOUL, can't find the tools, silently degrades — produces vague responses instead of reading code.

**Key distinction:**
- `toolsets:` key — only restricts which tools are loaded on MESSAGING platforms (Telegram, Discord). CLI always loads all tools.
- `agent.disabled_toolsets:` — disables tools for ALL interfaces including CLI. This is a HARD block.

**Fix:** Audit `disabled_toolsets` against every instruction in SOUL.md. If the SOUL says "use read_file," the tool must NOT be in `disabled_toolsets`. Or update the SOUL to reflect the reduced toolset.

### 3. Result Summarization Strips Decision Signal

**Before (MCP):** `necromancer_result` returned full Shade output. Raven (expensive model) could read actual code, file paths, and detailed findings to make routing decisions.

**After (plugin):** `_summarize_result()` in tools.py:
- Results > 15K chars are summarized by DeepSeek V4 Flash (cheap model)
- Results truncated to 30K max
- Full result saved to disk, but only summary enters Raven's context

**Result:** Raven never sees the actual work — it gets a lossy summary from a cheaper model. The orchestrator's ability to make quality decisions is degraded because the decision-relevant signal (actual code, specific errors, file contents) is compressed away.

**Anti-pattern logic:** The expensive model was chosen for the orchestrator role BECAUSE it makes better decisions with full context. Summarizing the input with a cheap model before the expensive model sees it defeats the entire cost-alignment strategy. You're paying for a smart model and then feeding it dumbed-down input.

**Fix:** Never summarize between worker and orchestrator. Use character-budget truncation (head + tail with omission notice) if size is a concern, but never LLM summarization. Save full results to disk for audit, but pass raw (truncated-by-budget, not summarized) content to the orchestrator.

### 4. Process Routing Regression — Skip Decomposition

**Before (MCP):** All tasks went through the Necromancer: decompose → route to appropriate Shade → audit with Revenant → retry loop.

**After (plugin):** `investigate` and `execute` bypass the Necromancer entirely:
```python
async def process_investigate(prompt, project_root, session_id):
    shade_result = await run_shade("research", prompt, ...)  # raw prompt to Shade
    return {"findings": shade_result["output"]}
```

No decomposition. No routing decision. The raw user prompt goes directly to a single Shade. Only `implement` preserves the decompose → shade → audit → retry loop.

**Result:** Complex investigations that needed multiple Shade invocations or cross-referencing are handled by a single Shade with no orchestration. Quality drops on anything non-trivial.

**Fix:** All tool entry points must route through the orchestrator (Necromancer), even for research/execution tasks. The orchestrator's decomposition and routing value applies to all task types, not just implementation.

### 5. Plugin Never Enabled — Missing `plugins:` Section in config.yaml

**Symptom:** Plugin files exist on disk (plugin.yaml, __init__.py, tools.py, schemas.py all present in plugins/requiem_tools/). The plugin toolset name is listed in `toolsets:`. But the agent reports "I don't have tool X" and none of the plugin's tools are available.

**Root cause:** hermes-agent requires BOTH `toolsets: [..., plugin_toolset_name]` AND a top-level `plugins:` section in config.yaml:
```yaml
plugins:
  enabled:
    - requiem_tools    # directory name under plugins/
```
Without the `plugins:` section, the framework never discovers or loads the plugin. The toolset name (registered by the plugin via `ctx.register_tool(toolset="name")`) and the plugin directory name may differ — both must be correctly referenced.

**Detection:** `hermes config show` or checking available tools from the agent's perspective. If the plugin's tools don't appear, the `plugins:` section is the first thing to check.

**Fix:** Add the `plugins:` section to config.yaml. Then restart the gateway. Verify tools are visible by asking the agent to list its tools.

**Why this is insidious:** Unlike MCP server blocks (which produce a visible error if the server can't start), a missing `plugins:` section produces NO error — the plugin simply doesn't exist from the agent's perspective. There's no log message saying "plugin requiem_tools not enabled." The agent just silently lacks the tools.

## General Migration Checklist

When migrating a multi-agent system from MCP to native plugin (or any tool surface change):

1. **Tool granularity:** Map each MCP tool to a plugin equivalent. If an MCP tool was async with polling, the plugin must also support async + polling. Blocking = regression.
2. **Config vs SOUL audit:** After any config change that affects toolsets (`disabled_toolsets`, `toolsets`), read the SOUL.md line by line and verify every tool mention is actually available.
3. **Plugin enablement:** Verify config.yaml has the `plugins: enabled: [plugin_dir_name]` section. The plugin existing on disk is NOT enough. Check this FIRST when a plugin's tools are invisible.
4. **Skill file audit:** After any tool interface migration, audit ALL agent skills (SKILL.md files) that reference the old tool names. Rewrite skills to describe ONLY the current tools. A 523-line skill describing non-existent tools is worse than no skill — the LLM tries to call tools that don't exist.
5. **Data flow fidelity:** Trace what data the calling agent received in the MCP version. Ensure the plugin version delivers the same data (not summarized, not truncated by model — only by character budget).
6. **Routing preservation:** Verify that all entry points still route through the orchestrator. Don't create "shortcut" paths that bypass decomposition/routing for certain task types.
7. **Timeout alignment:** MCP tools had their own timeout (600s in config). Plugin tools inherit the handler timeout (`_HANDLER_TIMEOUT`). Ensure these are compatible with expected task durations.
8. **Git-track config changes:** Manually-added config sections (MCP blocks, plugins sections, custom env vars) must be committed to git immediately. Any subsequent Daimon delegation that rewrites config.yaml will use the git version as base, silently dropping uncommitted additions.
