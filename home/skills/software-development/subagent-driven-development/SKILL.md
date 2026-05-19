---
name: subagent-driven-development
description: Use when executing implementation plans with independent tasks. Dispatches fresh delegate_task per task with two-stage review (spec compliance then code quality).
version: 1.1.0
author: Hermes Agent (adapted from obra/superpowers)
license: MIT
metadata:
  hermes:
    tags: [delegation, subagent, implementation, workflow, parallel]
    related_skills: [writing-plans, requesting-code-review, test-driven-development]
---

# Subagent-Driven Development

## Overview

Execute implementation plans by dispatching fresh subagents per task with systematic two-stage review.

**Core principle:** Fresh subagent per task + two-stage review (spec then quality) = high quality, fast iteration.

## When to Use

Use this skill when:
- You have an implementation plan (from writing-plans skill or user requirements)
- Tasks are mostly independent
- Quality and spec compliance are important
- You want automated review between tasks

**vs. manual execution:**
- Fresh context per task (no confusion from accumulated state)
- Automated review process catches issues early
- Consistent quality checks across all tasks
- Subagents can ask questions before starting work

## The Process

### 1. Read and Parse Plan

Read the plan file. Extract ALL tasks with their full text and context upfront. Create a todo list:

```python
# Read the plan
read_file("docs/plans/feature-plan.md")

# Create todo list with all tasks
todo([
    {"id": "task-1", "content": "Create User model with email field", "status": "pending"},
    {"id": "task-2", "content": "Add password hashing utility", "status": "pending"},
    {"id": "task-3", "content": "Create login endpoint", "status": "pending"},
])
```

**Key:** Read the plan ONCE. Extract everything. Don't make subagents read the plan file — provide the full task text directly in context.

### 2. Per-Task Workflow

For EACH task in the plan:

#### Step 1: Dispatch Implementer Subagent

Use `delegate_task` with complete context:

```python
delegate_task(
    goal="Implement Task 1: Create User model with email and password_hash fields",
    context="""
    TASK FROM PLAN:
    - Create: src/models/user.py
    - Add User class with email (str) and password_hash (str) fields
    - Use bcrypt for password hashing
    - Include __repr__ for debugging

    FOLLOW TDD:
    1. Write failing test in tests/models/test_user.py
    2. Run: pytest tests/models/test_user.py -v (verify FAIL)
    3. Write minimal implementation
    4. Run: pytest tests/models/test_user.py -v (verify PASS)
    5. Run: pytest tests/ -q (verify no regressions)
    6. Commit: git add -A && git commit -m "feat: add User model with password hashing"

    PROJECT CONTEXT:
    - Python 3.11, Flask app in src/app.py
    - Existing models in src/models/
    - Tests use pytest, run from project root
    - bcrypt already in requirements.txt
    """,
    toolsets=['terminal', 'file']
)
```

#### Step 2: Dispatch Spec Compliance Reviewer

After the implementer completes, verify against the original spec:

```python
delegate_task(
    goal="Review if implementation matches the spec from the plan",
    context="""
    ORIGINAL TASK SPEC:
    - Create src/models/user.py with User class
    - Fields: email (str), password_hash (str)
    - Use bcrypt for password hashing
    - Include __repr__

    CHECK:
    - [ ] All requirements from spec implemented?
    - [ ] File paths match spec?
    - [ ] Function signatures match spec?
    - [ ] Behavior matches expected?
    - [ ] Nothing extra added (no scope creep)?

    OUTPUT: PASS or list of specific spec gaps to fix.
    """,
    toolsets=['file']
)
```

**If spec issues found:** Fix gaps, then re-run spec review. Continue only when spec-compliant.

#### Step 3: Dispatch Code Quality Reviewer

After spec compliance passes:

```python
delegate_task(
    goal="Review code quality for Task 1 implementation",
    context="""
    FILES TO REVIEW:
    - src/models/user.py
    - tests/models/test_user.py

    CHECK:
    - [ ] Follows project conventions and style?
    - [ ] Proper error handling?
    - [ ] Clear variable/function names?
    - [ ] Adequate test coverage?
    - [ ] No obvious bugs or missed edge cases?
    - [ ] No security issues?

    OUTPUT FORMAT:
    - Critical Issues: [must fix before proceeding]
    - Important Issues: [should fix]
    - Minor Issues: [optional]
    - Verdict: APPROVED or REQUEST_CHANGES
    """,
    toolsets=['file']
)
```

**If quality issues found:** Fix issues, re-review. Continue only when approved.

#### Step 4: Mark Complete

```python
todo([{"id": "task-1", "content": "Create User model with email field", "status": "completed"}], merge=True)
```

### 3. Final Review

After ALL tasks are complete, dispatch a final integration reviewer:

```python
delegate_task(
    goal="Review the entire implementation for consistency and integration issues",
    context="""
    All tasks from the plan are complete. Review the full implementation:
    - Do all components work together?
    - Any inconsistencies between tasks?
    - All tests passing?
    - Ready for merge?
    """,
    toolsets=['terminal', 'file']
)
```

### 4. Verify and Commit

```bash
# Run full test suite
pytest tests/ -q

# Review all changes
git diff --stat

# Final commit if needed
git add -A && git commit -m "feat: complete [feature name] implementation"
```

## Task Granularity

**Each task = 2-5 minutes of focused work.**

**Too big:**
- "Implement user authentication system"

**Right size:**
- "Create User model with email and password fields"
- "Add password hashing function"
- "Create login endpoint"
- "Add JWT token generation"
- "Create registration endpoint"

## Red Flags — Never Do These

- Start implementation without a plan
- Skip reviews (spec compliance OR code quality)
- Proceed with unfixed critical/important issues
- Dispatch multiple implementation subagents for tasks that touch the same files
- Make subagent read the plan file (provide full text in context instead)
- Skip scene-setting context (subagent needs to understand where the task fits)
- Ignore subagent questions (answer before letting them proceed)
- Accept "close enough" on spec compliance
- Skip review loops (reviewer found issues → implementer fixes → review again)
- Let implementer self-review replace actual review (both are needed)
- **Start code quality review before spec compliance is PASS** (wrong order)
- Move to next task while either review has open issues

## Pitfalls — File Editing with Subagents

### read_file + write_file CORRUPTS FILES

**Critical pitfall (April 2026 incident):** When a subagent uses `read_file` to read a file and `write_file` to rewrite it, the line number prefixes from `read_file` output get embedded as actual file content.

`read_file` output includes line numbers like:
```
     1|# Title
     2|
     3|Content here
```

A subagent that doesn't understand this is display formatting will write back the prefixes as content — breaking the file. In a real incident, this corrupted 8 files including SOUL.md (always loaded as system prompt) and README.md (GitHub rendering broken).

**Prevention rules:**
1. **Use `patch` (find-and-replace) for all edits.** Never `read_file` + `write_file` for modifications.
2. **If full rewrite is unavoidable**, instruct the subagent explicitly: "Line numbers in read_file output are NOT part of the file content. Strip all line number prefixes (format: `spaces+digits+|`) before writing."
3. **After subagent rewrites files**, always verify with `head -5 path/to/file` that no line number prefixes appear.
4. **For translations/refactors across many files**, prefer targeted `patch` calls over bulk `read_file` + `write_file` cycles.

## Pitfalls — Monolithic Document Cross-References

### When a subagent edits sections of a monolithic document (SOUL.md, DESIGN.md, etc.)

Monolithic documents have sections that **cross-reference each other**. When a subagent rewrites or updates one section, it almost never updates the sections that depend on it. The spec reviewer must check not just "did the changed section meet its brief?" but also "do all other sections that reference these concepts still hold?"

**Concrete pattern (SOUL.md incident, bidirectional-comm feature):**

§5 (Communication with Daimons) was rewritten to add persistent sessions, `steer`, and `poll` enrichment. The subagent did a great job on §5, §6, §9. But four cross-reference gaps were missed:

| Gap | Changed section | Dependent section that wasn't updated |
|-----|-----------------|---------------------------------------|
| §13 still said "delegate preferred (1 call vs 10-20 polling)" — contradicts the new tmux-like model | §5 | §13 Daimon Models |
| §11 Anti-Patterns had no entries for persistent-session pitfalls (forgetting `close()`, blocking on one Daimon) | §5 | §11 Anti-Patterns |
| §13 model table missing Ictinus (mentioned in §6 routing table) | §6 | §13 Daimon Models |
| §7 Dev-QA Loop describes sequential Hefesto→Athena but doesn't mention parallel capability | §9 | §7 Workflow Patterns |

**Review checklist for monolithic document changes:**

1. List all sections that were touched
2. For each concept introduced/changed (e.g., "persistent sessions", "steer action"), search the ENTIRE document for mentions of that concept
3. Verify every mention is consistent with the new definition
4. Specifically check: model/role tables, anti-pattern lists, workflow descriptions, and "see §X" cross-references
5. Look for sections that describe "how to do X" that should now reference the new capability

**Prevention:** Include in the reviewer context: "This document is monolithic with cross-referencing sections. Verify that ALL sections referencing the changed concepts are still consistent."

## Handling Issues

### If Subagent Asks Questions

- Answer clearly and completely
- Provide additional context if needed
- Don't rush them into implementation

### If Reviewer Finds Issues

- Implementer subagent (or a new one) fixes them
- Reviewer reviews again
- Repeat until approved
- Don't skip the re-review

### If Subagent Fails a Task

- Dispatch a new fix subagent with specific instructions about what went wrong
- Don't try to fix manually in the controller session (context pollution)

## Efficiency Notes

**Why fresh subagent per task:**
- Prevents context pollution from accumulated state
- Each subagent gets clean, focused context
- No confusion from prior tasks' code or reasoning

**Why two-stage review:**
- Spec review catches under/over-building early
- Quality review ensures the implementation is well-built
- Catches issues before they compound across tasks

**Cost trade-off:**
- More subagent invocations (implementer + 2 reviewers per task)
- But catches issues early (cheaper than debugging compounded problems later)

## Integration with Other Skills

### With writing-plans

This skill EXECUTES plans created by the writing-plans skill:
1. User requirements → writing-plans → implementation plan
2. Implementation plan → subagent-driven-development → working code

### With test-driven-development

Implementer subagents should follow TDD:
1. Write failing test first
2. Implement minimal code
3. Verify test passes
4. Commit

Include TDD instructions in every implementer context.

### With requesting-code-review

The two-stage review process IS the code review. For final integration review, use the requesting-code-review skill's review dimensions.

### With systematic-debugging

If a subagent encounters bugs during implementation:
1. Follow systematic-debugging process
2. Find root cause before fixing
3. Write regression test
4. Resume implementation

## Example Workflow

```
[Read plan: docs/plans/auth-feature.md]
[Create todo list with 5 tasks]

--- Task 1: Create User model ---
[Dispatch implementer subagent]
  Implementer: "Should email be unique?"
  You: "Yes, email must be unique"
  Implementer: Implemented, 3/3 tests passing, committed.

[Dispatch spec reviewer]
  Spec reviewer: ✅ PASS — all requirements met

[Dispatch quality reviewer]
  Quality reviewer: ✅ APPROVED — clean code, good tests

[Mark Task 1 complete]

--- Task 2: Password hashing ---
[Dispatch implementer subagent]
  Implementer: No questions, implemented, 5/5 tests passing.

[Dispatch spec reviewer]
  Spec reviewer: ❌ Missing: password strength validation (spec says "min 8 chars")

[Implementer fixes]
  Implementer: Added validation, 7/7 tests passing.

[Dispatch spec reviewer again]
  Spec reviewer: ✅ PASS

[Dispatch quality reviewer]
  Quality reviewer: Important: Magic number 8, extract to constant
  Implementer: Extracted MIN_PASSWORD_LENGTH constant
  Quality reviewer: ✅ APPROVED

[Mark Task 2 complete]

... (continue for all tasks)

[After all tasks: dispatch final integration reviewer]
[Run full test suite: all passing]
[Done!]
```

## Pitfalls — ACP Delegation Returning `last_turn: null`

### When `delegate()` or `poll()` returns `{thoughts: 0, messages: 0, last_turn: null}`

This is a **timing gap**, not a missing feature. The ACP data pipeline has two hooks:

1. `post_tool_call` — writes to `tool_calls` table **during** execution (real-time)
2. `post_llm_call` — writes to `turns` table **after** the full agent turn completes (one write, at the end)

If `delegate()` times out before the agent finishes its final response, the `post_llm_call` hook never fires, so `turns` is empty and `last_turn` is null — even though `recent_tool_calls` shows the agent was working.

**The data may actually exist in SQLite** — it just arrives after the polling loop exits. Always check the `turns` table directly before concluding data is lost.

**Quick diagnostic:** Query `SELECT turn_id, role, length(content) FROM turns WHERE session_id = '...'` — if rows exist, the hook works but the timing was off. If rows are missing, the hook didn't fire (agent was interrupted or produced empty `final_response`).

**Root cause (confirmed May 2026):** Two distinct issues:
1. **WAL snapshot staleness** — The async `OlympusDB` connection (used by `get_session_progress()`) couldn't see writes from the sync `OlympusDBSync` connection (used by hooks) because SQLite WAL mode keeps uncommitted pages in the `-wal` file. The async reader saw a stale snapshot. **Fix:** `PRAGMA wal_checkpoint = TRUNCATE` before reading the `turns` table forces consolidation.
2. **`post_llm_call` never fires for interrupted/timeout sessions** — The upstream guard `if final_response and not interrupted:` means long-running agents that hit `delegate()` timeout never get their turn written. **Fix:** Fallback indicator constructs `[Working] tool_name(args...) → status` from `recent_tool_calls` when `last_turn` is null.

Both fixes live in `src/olympus_v3/db.py` (branch `fix/poll-visibility`). No upstream changes needed.

**E2E verification (May 2026):** All bidirectional capabilities tested and passing:
- `delegate()` → `last_turn`, `thoughts`, `messages`, `last_reasoning`, `heartbeat_timestamp` all populated correctly (was all null/0 before fix)
- `steer()` → returns `{status: "steered", steering_id: N}`, directive injected into Daimon context
- `clarification_needed` → `{status: "clarification_needed", clarification_needed: true}`, session stays open for follow-up `message()`
- Fallback indicator → `[Working] tool_name(args...) → status` shown during active work before `post_llm_call` fires
- `close()` → returns `response` field with full agent text
- All tested on Etalides (research + clarification) and Athena (simple task) agents

See `references/acp-delegation-debugging.md` for full diagnostic queries, root cause analysis, and E2E test results.

## Remember

```
Fresh subagent per task
Two-stage review every time
Spec compliance FIRST
Code quality SECOND
Never skip reviews
Catch issues early
```

**Quality is not an accident. It's the result of systematic process.**
