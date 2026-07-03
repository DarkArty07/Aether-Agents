# Toolset Dependency Audit

When adding or removing a toolset from an agent — especially the orchestrator — you must audit ALL references to that toolset's individual tools across the system. A toolset removal from `config.yaml` is only half the change; the SOUL.md and platform configuration will still reference the removed tools by name.

## What to scan after removing a toolset

After removing a toolset from an agent's `config.yaml:toolsets` list, check these locations for references to any tool from that toolset:

### 1. config.yaml — platform_toolsets

The `platform_toolsets.<platform>` entries each list every available toolset independently. Removing from `toolsets:` does NOT remove from `platform_toolsets:` — you must remove from BOTH.

```yaml
platform_toolsets:
  cli:
  - file-read     ← must be removed here too
  - web
  ...
  telegram:
  - file-read     ← and here
  - web
  ...
```

### 2. Orchestrator SOUL.md — routing rules that assume the tool is available

These sections typically reference tools by capability (e.g., `web_search`, `read_file`) even though the capability was provided by the now-removed toolset:

| Section | What to check | Example finding |
|---------|---------------|-----------------|
| Routing and delegation rules | Rules that assume tool is available | `Quick fact? (<2 web searches) → Do it yourself` |
| Routing table | Rows that route to orchestrator's own tools | `Quick fact (< 2 links) \| Orchestrator \| web_search` |
| Economy / delegation rules | Rules that define when orchestrator uses tool directly vs delegates | `Use web_search yourself only for quick facts` |
| Anti-patterns table | Anti-patterns that reference now-removed tool | `Using talk_to for simple quick facts \| Use web_search yourself` |
| Code examples | Snippets showing tool calls | `{tool_name: "read_file", ...}` |

### 3. Other agent SOULs that reference orchestator capabilities

Check if other agents' SOUL.md assumes the orchestrator handles certain tasks. If you're removing `web` from the orchestrator, update anything that says "ask orchestrator for a quick fact."

### 4. Target agent readiness (if delegating to another agent)

When a capability moves from one agent to another, verify:
- The target agent's `config.yaml` has the needed toolset
- The target agent's SOUL.md explicitly lists the capability as a core responsibility
- The target agent has appropriate action budgets for the expected workload

## Audit pattern

For each toolset being removed:

1. **List every tool in that toolset** (e.g., `file-read` → `read_file`, `search_files`, `write_file`, `patch`)
2. **Grep SOUL.md** for each tool name (case-insensitive)
3. **Classify each match**: (a) orchestrator using it → must change, (b) agent output example → stays, (c) descriptive text about who has the tool → update if needed
4. **Update routing table + economy rules + anti-patterns** in SOUL.md
5. **Update `platform_toolsets`** in config.yaml
6. **Document the change scope** before implementing

## Example

Removing `file-read` from an orchestrator required changes to:
- **config.yaml**: `toolsets:` (remove `file-read`), `platform_toolsets.cli` and `.telegram` (remove `file-read`)
- **SOUL.md**: Delegation rules, Routing table, Economy rule, Code research rule
- **SOUL.md §Anti-Patterns**: Anti-patterns table

Scope: ~1 line in config.yaml + ~5 lines in SOUL.md = ~6 lines total. Feasible, low risk.
