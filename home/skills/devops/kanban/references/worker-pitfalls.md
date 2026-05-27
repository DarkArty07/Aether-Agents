# Kanban Worker — Full Pitfalls and Examples

> This is the complete pre-consolidation kanban-worker skill, preserved as a reference. The condensed version lives in the parent `kanban` SKILL.md under "Worker — Pitfalls and Examples".

## Workspace handling

| Kind | What it is | How to work |
|---|---|---|
| `scratch` | Fresh tmp dir, yours alone | Read/write freely; GC'd when archived |
| `dir:<path>` | Shared persistent directory | Others read what you write |
| `worktree` | Git worktree at resolved path | Run `git worktree add` first if needed |

## Tenant isolation

If `$HERMES_TENANT` is set, prefix memory entries with the tenant so context doesn't leak.

- Good: `business-a: Acme is our biggest customer`
- Bad: `Acme is our biggest customer`

## Good summary + metadata shapes

### Coding task
```python
kanban_complete(
    summary="shipped rate limiter — token bucket, 14 tests pass",
    metadata={
        "changed_files": ["rate_limiter.py", "tests/test_rate_limiter.py"],
        "tests_run": 14, "tests_passed": 14,
        "decisions": ["user_id primary, IP fallback for unauthenticated requests"],
    },
)
```

### Research task
```python
kanban_complete(
    summary="3 competing libraries reviewed; vLLM wins on throughput",
    metadata={
        "sources_read": 12, "recommendation": "vLLM",
        "benchmarks": {"vllm": 1.0, "sglang": 0.87, "trtllm": 0.72},
    },
)
```

### Review task
```python
kanban_complete(
    summary="reviewed PR #123; 2 blocking issues found (SQL injection, missing CSRF)",
    metadata={
        "pr_number": 123, "approved": False,
        "findings": [
            {"severity": "critical", "file": "api/search.py", "line": 42, "issue": "raw SQL concat"},
            {"severity": "high", "file": "api/settings.py", "issue": "missing CSRF middleware"},
        ],
    },
)
```

## Claiming cards you actually created

Only list ids you captured from a successful `kanban_create` return value:

```python
# GOOD
c1 = kanban_create(title="remediate SQL injection", assignee="security-worker")
c2 = kanban_create(title="fix CSRF middleware", assignee="web-worker")
kanban_complete(summary="...", created_cards=[c1["task_id"], c2["task_id"]])

# BAD — hallucinated ids
kanban_complete(summary="...", created_cards=["t_a1b2c3d4", "t_deadbeef"])  # → gate rejects
```

## Block reasons

Good: one sentence naming the specific decision needed. Leave context as a comment.

```python
kanban_comment(task_id=..., body="Full context: ...")
kanban_block(reason="Rate limit key choice: IP (simple, NAT-unsafe) or user_id (requires auth)?")
```

## Heartbeats

Good: `"epoch 12/50, loss 0.31"`, `"scanned 1.2M/2.4M rows"`.
Bad: `"still working"`, empty notes, sub-second intervals.

## Retry scenarios

- `timed_out` — hit max runtime. Chunk the work.
- `crashed` — OOM or segfault. Reduce memory.
- `spawn_failed` — profile config issue. Block for human.
- `reclaimed` — operator archived it. Check status.
- `blocked` — unblock comment should be in the thread.

## Do NOT

- Call `delegate_task` as a substitute for `kanban_create`.
- Modify files outside `$HERMES_KANBAN_WORKSPACE`.
- Create follow-up tasks assigned to yourself.
- Complete a task you didn't finish. Block it instead.

## CLI fallback

- `kanban_show` ↔ `hermes kanban show <id> --json`
- `kanban_complete` ↔ `hermes kanban complete <id> --summary "..." --metadata '{}'`
- `kanban_block` ↔ `hermes kanban block <id> "reason"`
- `kanban_create` ↔ `hermes kanban create "title" --assignee <profile> [--parent <id>]`