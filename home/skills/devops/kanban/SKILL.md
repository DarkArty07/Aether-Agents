---
name: kanban
description: Kanban multi-agent orchestration — decomposition playbook for orchestrators, pitfalls and handoff shapes for workers, and the full task lifecycle.
version: 1.0.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [kanban, multi-agent, orchestration, routing, workflow, automation]
    related_skills: []
---

# Kanban — Multi-Agent Orchestration

> The core worker lifecycle (including the `kanban_create` fan-out pattern and the "decompose, don't execute" rule) is auto-injected into every kanban process via the `KANBAN_GUIDANCE` system-prompt block. This skill is the deeper playbook split into two perspectives: the **orchestrator** who routes work and the **worker** who executes it.

## Overview

The Hermes Kanban system is a SQLite-backed task board for multi-agent workflows. Tasks are created by orchestrators, claimed by dispatchers, executed by workers, and blocked/completed with metadata-rich summaries. Dependencies between tasks are expressed via parent links.

## Orchestrator — Decomposition Playbook

Use this section when you are playing the **orchestrator** role: receiving a complex goal and decomposing it into assignable kanban tasks.

### When to use the board (vs. just doing the work)

Create Kanban tasks when any of these are true:
1. **Multiple specialists are needed.** Research + analysis + writing is three profiles.
2. **The work should survive a crash or restart.** Long-running, recurring, or important.
3. **The user might want to interject.** Human-in-the-loop at any step.
4. **Multiple subtasks can run in parallel.** Fan-out for speed.
5. **Review / iteration is expected.** A reviewer profile loops on drafter output.
6. **The audit trail matters.** Board rows persist in SQLite forever.

If *none* of those apply — use `delegate_task` instead or answer the user directly.

### Anti-temptation rules

- **Do not execute the work yourself.** Your restricted toolset usually doesn't even include terminal/file/code/web for implementation.
- **For any concrete task, create a Kanban task and assign it.** Every single time.
- **If no specialist fits, ask the user which profile to create.** Do not default to doing it yourself.
- **Decompose, route, and summarize — that's the whole job.**

### Standard specialist roster

| Profile | Does | Typical workspace |
|---|---|---|
| `researcher` | Reads sources, gathers facts, writes findings | `scratch` |
| `analyst` | Synthesizes, ranks, de-dupes | `scratch` |
| `writer` | Drafts prose in the user's voice | `scratch` or `dir:` |
| `reviewer` | Reads output, leaves findings, gates approval | `scratch` |
| `backend-eng` | Writes server-side code | `worktree` |
| `frontend-eng` | Writes client-side code | `worktree` |
| `ops` | Runs scripts, manages services | `dir:` |
| `pm` | Writes specs, acceptance criteria | `scratch` |

### Decomposition steps

1. **Understand the goal** — ask clarifying questions if ambiguous.
2. **Sketch the task graph** — show the user before creating anything.
3. **Create tasks with links** — use `kanban_create` with parents.
4. **Complete your own task** — `kanban_complete` with a summary.
5. **Report back** — tell the user what was created in plain prose.

See `references/orchestrator-playbook.md` for the full detailed workflow with code examples.

## Worker — Pitfalls and Examples

Use this section when you are a **worker** spawned by the dispatcher to execute a single task.

### Workspace handling

| Kind | What it is | How to work |
|---|---|---|
| `scratch` | Fresh tmp dir, yours alone | Read/write freely; GC'd when archived |
| `dir:<path>` | Shared persistent directory | Others read what you write |
| `worktree` | Git worktree at resolved path | Run `git worktree add` first if needed |

### Good summary + metadata shapes

**Coding task:**
```python
kanban_complete(
    summary="shipped rate limiter — token bucket, 14 tests pass",
    metadata={
        "changed_files": ["rate_limiter.py", "tests/test_rate_limiter.py"],
        "tests_run": 14, "tests_passed": 14,
    },
)
```

**Research task:**
```python
kanban_complete(
    summary="3 competing libraries reviewed; vLLM wins on throughput",
    metadata={
        "sources_read": 12, "recommendation": "vLLM",
        "benchmarks": {"vllm": 1.0, "sglang": 0.87, "trtllm": 0.72},
    },
)
```

**Review task:**
```python
kanban_complete(
    summary="reviewed PR #123; 2 blocking issues found",
    metadata={
        "pr_number": 123, "approved": False,
        "findings": [{"severity": "critical", "file": "api/search.py", "line": 42, "issue": "raw SQL concat"}],
    },
)
```

### Retry scenarios

- `timed_out` — previous attempt hit max runtime; chunk the work.
- `crashed` — OOM or segfault; reduce memory footprint.
- `spawn_failed` — profile config issue; block for human help.
- `reclaimed` — operator archived it; check status carefully.
- `blocked` — previous attempt blocked; read the thread.

### Do NOT

- Call `delegate_task` as a substitute for `kanban_create`.
- Modify files outside `$HERMES_KANBAN_WORKSPACE` unless the task body says to.
- Complete a task you didn't actually finish. Block it instead.
- Claim cards you didn't create. Always capture return values from `kanban_create`.

### Pitfalls

- **Task state can change between dispatch and startup.** Always `kanban_show` first.
- **Workspace may have stale artifacts.** Read the comment thread.
- **Don't rely on the CLI when the guidance is available.** Use tools, not `hermes kanban`.
- **Argument order for links.** `kanban_link(parent_id=..., child_id=...)` — parent first.
- **Reassignment vs. new task.** Create a NEW task for rework; don't re-run the same one.
- **Tenant inheritance.** Pass `tenant=os.environ.get("HERMES_TENANT")` on `kanban_create`.
- **Don't pre-create the whole graph if shape depends on findings.** Let intermediate tasks spawn downstream.
- **Heartbeats worth sending:** `"epoch 12/50, loss 0.31"` — not `"still working"`.
- **Block reasons that get answered fast:** one sentence naming the specific decision needed.
- **CLI fallback exists** (`hermes kanban show <id> --json`) but tools are preferred.

See `references/worker-pitfalls.md` for extended edge cases and `references/orchestrator-playbook.md` for complete decomposition workflow.