# Eigent Multi-Agent Architecture — Source Code Analysis

Cloned from https://github.com/eigent-ai/eigent (Python backend + TypeScript Electron frontend).
Built on CAMEL-AI framework. 491 Python files in backend.

## Architecture Overview

Eigent has TWO multi-agent modes:

### Mode 1: Single Agent + Delegation (primary mode)

A single CAMEL ChatAgent with toolkits. Can delegate to subagents via
`DepthLimitedAgentToolkit` — a wrapper over CAMEL's native `AgentToolkit`
that prevents recursive delegation.

```python
class DepthLimitedAgentToolkit(AgentToolkit):
    def __init__(self, current_depth=0, max_depth=1):
        self.current_depth = current_depth
        self.max_depth = max_depth

    @property
    def can_delegate(self) -> bool:
        return self.depth < self.max_depth

    def _resolve_child_tools(self, parent):
        # Filters out AgentToolkit tools from children
        tools = [t for t in tools if not _is_agent_tool(t)]
        toolkits = [tk for tk in toolkits if not isinstance(tk, AgentToolkit)]

    def _build_system_message(self, subagent_type, description):
        base = super()._build_system_message(subagent_type, description)
        return base + "\nYou are a child sub-agent. Complete the assigned task "
               "directly and do not create or delegate to any further sub-agents."
```

Same pattern as OpenCode and hermes-agent: 1 level, no recursion, fresh context.

### Mode 2: Workforce (CAMEL Workforce engine)

Multi-agent teamwork with a shared task channel:

- **Coordinator Agent**: routes tasks to workers by role/skills
- **Task Planner Agent**: decomposes big tasks into subtasks
- **Worker Nodes**: specialized agents (Developer, Browser, Document, Multi-Modal)
- **Shared Task Channel**: all tasks posted to a shared channel; workers pick up
  assigned tasks; results posted back for dependent steps
- **Failure recovery**: if a worker fails, coordinator decomposes further or
  creates a new worker. Max 3 failures before auto-halt.

All workers run IN THE SAME PROCESS. No subprocesses. Agents are ChatAgent
objects communicating via the shared task channel.

### Mode 3: Remote Sub-Agent (sandbox)

Optional remote sandbox execution via Gemini Agents API. Sends work to an
isolated cloud environment. Not relevant for local multi-agent architecture.

## Toolkit Assembly Pattern

Eigent's `toolkit_assembler.py` is notable — it dynamically assembles agent
toolkits from a config dict, enabling per-agent specialization:

```python
DEFAULT_SINGLE_AGENT_TOOLKIT_CONFIG = {
    "human": {"enabled": True},
    "file": {"enabled": True},
    "terminal": {"enabled": True},
    "browser": {"enabled": True},
    "search": {"enabled": True},
    "skill": {"enabled": True},
    "todo": {"enabled": True},
    "agent": {"enabled": True},  # delegation capability
    # ...
}
```

The `agent` toolkit (delegation) is conditionally added based on depth:

```python
if _enabled(config, "agent") and can_delegate:
    toolkit = DepthLimitedAgentToolkit(
        current_depth=current_depth,
        max_depth=max_depth,
    )
    assembly.add_tools(toolkit.get_tools(), toolkit.toolkit_name())
```

This is the SAME pattern as OpenCode's permission-based specialization and
hermes-agent's toolset-based restriction — just expressed differently.

## Brain / Hands Architecture

Eigent separates concerns into:
- **Brain**: central runtime (task orchestration, agent coordination, tool/file/MCP APIs)
- **Clients**: Desktop (Electron), Web — presentation only
- **Hands**: what the Brain can operate in its environment (terminal, browser,
  filesystem, MCP). Determined by deployment environment, not client type.

This "Hands" abstraction is interesting: capability = environment, not agent type.
A Web client connected to a full Brain has the same capabilities as Desktop.
The Brain environment determines what's possible, not the connection method.

## Pre-configured Worker Types (Workforce mode)

| Worker | Toolkits |
|--------|----------|
| DeveloperAgent | Terminal, WebDeploy, NoteTaking, Skill, Human |
| BrowserAgent | Search, HybridBrowser, Terminal, NoteTaking, Skill, Human |
| DocumentAgent | File, PPTX, Excel, MarkItDown, Search, GoogleDrive, Skill, Human |
| Multi-ModalAgent | VideoDownloader, AudioAnalysis, OpenAIImage, Search, Skill, Human |

## What's Relevant for Requiem/Aether

| Concept | Eigent Pattern | Applicability |
|---------|---------------|---------------|
| Depth-limited delegation | DepthLimitedAgentToolkit | Already in hermes-agent delegate_task |
| Toolkit assembly from config | Dynamic toolkit assembler | Interesting for per-subagent toolset config |
| NoteTakingToolkit for inter-agent comm | .md notes shared between agents | Lightweight inter-agent communication without overhead |
| Hands abstraction | Capability = environment | Per-subagent toolsets, not per-SOUL |
| Skills (SKILL.md) | Same concept as hermes-agent | Already have this |

## What's NOT Relevant

- CAMEL framework: academic, heavy, 491 Python files — too much overhead
- Electron desktop app: not needed
- Workforce coordinator/planner: another LLM call layer we don't need
- Remote Sub-Agent: cloud sandbox unnecessary

## Cross-System Convergence

All three systems analyzed (OpenCode, hermes-agent delegate_task, Eigent)
converge on the same architecture:

```
OpenCode:      1 agent → task tool → subagent (same process, depth=1)
hermes-agent:  1 agent → delegate_task → AIAgent child (same process, depth=1)
Eigent:        1 agent → DepthLimitedAgentToolkit → ChatAgent child (same process, depth=1)
```

None uses subprocesses for subagents. None uses 3+ levels. None has a middleman
that only routes. The market has converged: flat 1-level delegation with
permission/toolset-based specialization is the correct pattern.
