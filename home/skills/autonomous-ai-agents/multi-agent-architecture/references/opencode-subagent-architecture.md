# OpenCode Subagent Architecture — Source Code Analysis

Cloned from https://github.com/anomalyco/opencode (TypeScript/Bun monorepo, 2306 files).
Analyzed: packages/opencode/src/agent/agent.ts, tool/task.ts, agent/subagent-permissions.ts,
session/compaction.ts, session/overflow.ts, tool/truncate.ts, session/prompt/default.txt,
agent/prompt/explore.txt, agent/prompt/compaction.txt.

## Core Architecture: Single-Tool Flat Delegation

OpenCode uses ONE tool (`task`) for all subagent delegation. It has 3 key parameters:

- `subagent_type`: "general" (full permissions), "explore" (read-only), or custom
- `prompt`: text describing the task
- `background`: boolean (experimental, async mode)

That's it. No structured protocol, no JSON template, no multi-part response format.

## Key Design Decisions (from source code)

### 1. Flat Hierarchy — 1 Level Only

Subagents CANNOT spawn further subagents. By default, `task` and `todowrite`
permissions are DENIED in subagent sessions (subagent-permissions.ts):

```typescript
export function deriveSubagentSessionPermission(input) {
  const canTask = input.subagent.permission.some(r => r.permission === "task")
  const canTodo = input.subagent.permission.some(r => r.permission === "todowrite")
  return [
    ...input.parentSessionPermission.filter(r => 
      r.permission === "external_directory" || r.action === "deny"
    ),
    ...(canTodo ? [] : [{ permission: "todowrite", pattern: "*", action: "deny" }]),
    ...(canTask ? [] : [{ permission: "task", pattern: "*", action: "deny" }]),
  ]
}
```

This structurally prevents nesting. No middleman orchestrator, no 3-level chain.

### 2. Permission-Based Specialization (not role-based)

Instead of separate agents with different SOULs (Necromancer, Shades, Revenant),
OpenCode has 2 built-in subagent types defined by PERMISSION RULES:

- `explore`: read-only — grep, glob, list, bash, webfetch, websearch, read.
  System prompt: "You are a file search specialist..." (explore.txt, ~20 lines)
- `general`: full permissions minus todowrite.
  No special system prompt — uses the default provider-specific prompt.

Custom agents can be defined in `.opencode/agent/*.md` with frontmatter:
```yaml
---
mode: primary          # or "subagent" or "all"
model: opencode/gpt-5.4-mini
tools:
  "*": false
  "github-triage": true
---
```

### 3. Fresh Context — No Transfer

Each subagent starts with a CLEAN context. The parent sends a `prompt` (text string).
The subagent returns its last text message. No context packaging, no file-change
tracking, no structured result format.

The task tool description says:
> "Each agent invocation starts with a fresh context unless you provide task_id
> to resume the same subagent session."

### 4. Background Mode at Framework Level

`background: true` launches the subagent asynchronously. The framework:
1. Creates a child session with `parentID: ctx.sessionID`
2. Runs the task in a BackgroundJob
3. Notifies the parent when done by injecting a synthetic message

The tool description explicitly tells the LLM:
> "DO NOT sleep, poll for progress, ask the task for status, or duplicate
> this task's work — avoid working with the same files or topics it is using."

This is enforced structurally — the background job handles notification,
the LLM doesn't need to poll.

### 5. Context Management: Truncate + Prune + Compaction (no custom summarization)

Three automatic mechanisms, none custom:

**a) Truncate (tool/truncate.ts):**
- MAX_LINES = 2000, MAX_BYTES = 50KB per tool output
- If exceeded: save full output to file, return preview + hint to read the file
- Agents with `task` tool permission can read the saved full output later

**b) Prune (session/compaction.ts → prune function):**
- After each turn, walks backward through tool results
- Protects last 2 turns (DEFAULT_TAIL_TURNS = 2)
- Protects tools in PRUNE_PROTECTED_TOOLS (["skill"])
- If total tool output exceeds PRUNE_PROTECT (40K tokens), marks old results as compacted
- Only prunes if prunable amount > PRUNE_MINIMUM (20K tokens)

**c) Compaction (session/compaction.ts → processCompaction):**
- Triggered when `isOverflow()` detects context window is full
- Uses a dedicated "compaction" agent (hidden, mode: primary)
- Summarizes old conversation, preserves recent turns verbatim
- Replaces old messages with summary, keeps working context fresh
- Preserves recent budget: 25% of usable context (configurable)

### 6. Same Model for Parent and Subagent

No model-tier split. Subagent defaults to parent's model:
```typescript
const model = next.model ?? {
  modelID: msg.info.modelID,
  providerID: msg.info.providerID,
}
```

Can override per-agent in config, but it's not the architectural pattern.

### 7. Provider-Specific System Prompts

Different system prompts for different model families (system.ts):
- GPT-4/o1/o3: PROMPT_BEAST
- GPT (non-codex): PROMPT_GPT
- Codex: PROMPT_CODEX
- Gemini: PROMPT_GEMINI
- Claude: PROMPT_ANTHROPIC
- Default: PROMPT_DEFAULT

All are concise, focused on: tool usage policy, code style, verbosity control
("fewer than 4 lines"), proactiveness boundaries, and following conventions.

### 8. AGENTS.md for Project Context

Instead of complex context injection (.aether/CONTEXT.md curation), OpenCode
uses AGENTS.md files automatically loaded as system context (instruction.ts).
Simple, file-based, no runtime curation needed. Also reads CLAUDE.md and
CONTEXT.md (deprecated) for backward compatibility.

## Architecture Comparison: OpenCode vs Requiem

| Aspect | OpenCode | Requiem | Overhead Impact |
|--------|----------|---------|-----------------|
| Delegation levels | 1 (Primary→Subagent) | 3 (Raven→Necro→Shades) | 3x LLM calls per task |
| Subagent nesting | Blocked (task denied) | Allowed (Necro delegates to Shades) | Unbounded depth risk |
| Specialization | By permissions (2 types) | By role/SOUL (4+ agents) | More agents = more routing overhead |
| Context transfer | None (fresh start) | Packaged between levels | Token cost + info loss |
| Result format | Last text message | Structured/summarized | Parsing + format overhead |
| Background mode | Framework-level | check_progress(wait=true) | Still some coordination overhead |
| Context mgmt | Truncate+Prune+Compaction | _summarize_tool_result (custom, buggy) | Custom summary longer than original |
| Model split | Same model default | Expensive Raven + cheap Shades | Extra API calls, different behaviors |
| Tool count | 1 (task) | Multiple (delegate, progress, read_simple) | Schema confusion for LLM |

## Design Lessons for Multi-Agent Systems

1. **Flatten hierarchy**: 2 levels (Primary→Worker) is enough. A middleman
   orchestrator (Necromancer) adds a full LLM call per task without adding value
   that the primary agent couldn't provide directly.

2. **Block subagent nesting**: Subagents should do work, not delegate further.
   Deny the `task` tool in subagent sessions. This is structural, not prompt-based.

3. **Specialize by permissions, not by SOUL**: Two subagent types (read-only
   explorer, full-power worker) cover 90% of use cases. Custom SOULs for each
   agent create routing complexity and context bloat.

4. **Fresh context per subagent**: Don't transfer parent context. Send a
   well-crafted prompt. The subagent has its own tools and can explore as needed.

5. **Background mode is framework responsibility**: The LLM should not poll.
   The framework should launch, notify, and inject results.

6. **Truncate, don't summarize**: Cutting at 2000 lines / 50KB and saving the
   full output to a file is simpler and more reliable than LLM-based summarization.
   No summary can be longer than the original. The full output is always recoverable.

7. **One tool beats many**: A single `task` tool with a clear prompt is better
   than 3-4 tools (investigate/execute/implement/check_progress). Fewer schemas
   = less LLM confusion. The prompt carries the intent, not the tool name.

8. **System prompt brevity**: OpenCode's default prompt is ~2000 chars focused
   on verbosity control and tool policy. No pipeline phases, no role catalogs,
   no delegation templates. The LLM's behavior is shaped by the system prompt +
   tool schema descriptions, not by a 30K-token SOUL.
