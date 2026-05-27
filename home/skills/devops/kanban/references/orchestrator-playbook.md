# Kanban Orchestrator — Full Decomposition Playbook

> This is the complete pre-consolidation kanban-orchestrator skill, preserved as a reference. The condensed version lives in the parent `kanban` SKILL.md under "Orchestrator — Decomposition Playbook".

## When to use the board (vs. just doing the work)

Create Kanban tasks when any of these are true:
1. **Multiple specialists are needed.** Research + analysis + writing is three profiles.
2. **The work should survive a crash or restart.** Long-running, recurring, or important.
3. **The user might want to interject.** Human-in-the-loop at any step.
4. **Multiple subtasks can run in parallel.** Fan-out for speed.
5. **Review / iteration is expected.** A reviewer profile loops on drafter output.
6. **The audit trail matters.** Board rows persist in SQLite forever.

## The anti-temptation rules

- **Do not execute the work yourself.**
- **For any concrete task, create a Kanban task and assign it.**
- **If no specialist fits, ask the user which profile to create.**
- **Decompose, route, and summarize — that's the whole job.**

## Standard specialist roster

| Profile | Does | Typical workspace |
|---|---|---|
| `researcher` | Reads sources, gathers facts | `scratch` |
| `analyst` | Synthesizes, ranks, de-dupes | `scratch` |
| `writer` | Drafts prose in the user's voice | `scratch` or `dir:` |
| `reviewer` | Reads output, gates approval | `scratch` |
| `backend-eng` | Writes server-side code | `worktree` |
| `frontend-eng` | Writes client-side code | `worktree` |
| `ops` | Runs scripts, manages services | `dir:` |
| `pm` | Writes specs, acceptance criteria | `scratch` |

## Decomposition steps

### Step 1 — Understand the goal
Ask clarifying questions if the goal is ambiguous.

### Step 2 — Sketch the task graph
Show the user before creating anything. Example:
```
T1  researcher        research: Postgres cost vs current
T2  researcher        research: Postgres performance vs current
T3  analyst           synthesize migration recommendation       parents: T1, T2
T4  writer            draft decision memo                       parents: T3
```

### Step 3 — Create tasks and link

```python
t1 = kanban_create(title="research: Postgres cost vs current", assignee="researcher")["task_id"]
t2 = kanban_create(title="research: Postgres performance vs current", assignee="researcher")["task_id"]
t3 = kanban_create(title="synthesize migration recommendation", assignee="analyst", parents=[t1, t2])["task_id"]
t4 = kanban_create(title="draft decision memo", assignee="writer", parents=[t3])["task_id"]
```

`parents=[...]` gates promotion — children stay in `todo` until every parent is `done`.

### Step 4 — Complete your own task

```python
kanban_complete(
    summary="decomposed into T1-T4: 2 researchers parallel, 1 analyst on their outputs, 1 writer on the recommendation",
    metadata={"task_graph": {"T1": {"assignee": "researcher", "parents": []}, ...}},
)
```

### Step 5 — Report back
Tell the user what you created in plain prose.

## Common patterns

**Fan-out + fan-in:** N researchers parallel, one analyst with all as parents.
**Pipeline with gates:** `pm → backend-eng → reviewer`. Each stage gates the next.
**Same-profile queue:** 50 tasks, same assignee, no dependencies.
**Human-in-the-loop:** `kanban_block()` to wait for input.

## Recovering stuck workers

1. **Reclaim** or `hermes kanban reclaim <task_id>` — abort and reset to `ready`.
2. **Reassign** or `hermes kanban reassign <task_id> <profile> --reclaim`.
3. **Change profile model** — edit profile config on disk, then Reclaim.

Hallucination warnings appear when a worker claims cards it didn't create or references phantom `t_<hex>` ids in summaries.