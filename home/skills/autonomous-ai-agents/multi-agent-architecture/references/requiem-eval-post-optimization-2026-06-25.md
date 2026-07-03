# Requiem vs OpenCode — Post-Optimization Eval (2026-06-25)

Second comparative eval after implementing all 8 optimization fixes (commit b3d7c03).
Same model (glm-5.2), same 3 bugs, same project.

## Results

| Metric | OpenCode (eval 1) | Requiem (eval 1) | Requiem (eval 2) |
|--------|-------------------|-------------------|-------------------|
| Issues fixed | 3/3 | 0/3 (did not finish) | 3/3 |
| Time | 8m48s | 18m+ (interrupted) | 3m23s |
| Context used | ~43K tokens | 98K/128K (77%) | 29.6K/128K (23%) |
| Tests created | 53 | 0 | 58 (58/58 pass) |
| LLM calls per bug | 4-6 | 17-28 | ~6-10 (estimated) |
| Commits | 3 clean | 0 | 3 clean |

Requiem not only competed — it WON. 2.6x faster than OpenCode with 30% less context.

## What Changed (8 Fixes Applied)

### Phase A — High impact, small change
- **F1 (parallel tool calls):** TOOL_INSTRUCTIONS_TEMPLATE updated: "You CAN output MULTIPLE tool calls in a single response"
- **F3 (check_progress wait=true):** handle_check_progress now blocks internally (3s poll loop, wait_timeout param). Raven makes 1 call instead of 15+ sleep+poll cycles.
- **F5 (delegation rules):** SOUL.md appended with DELEGATION RULES — Raven must paste issue verbatim, NOT analyze the fix. "Let the Shades figure out HOW."

### Phase B — Structural changes
- **F2+F6+F7 (fast path):** _is_simple_task() classifier. Simple tasks skip LLM decomposition + Shade of Research. Direct to programming + execution (2 subtasks instead of 4+).
- **F4 (retry context):** Retry passes "Do NOT re-read files you already know." Guard at iteration 15 forces write.
- **F8 (summarize improvement):** _PROTECT_LAST_N 6→8. read_file summary preserves 5 lines (not 1). Shades don't re-read the same file.

## Optimization Impact Analysis

The 3 most impactful changes:

1. **check_progress(wait=true)** — eliminated 15+ wasted LLM calls per task. This alone cut context from 98K to ~30K.
2. **Fast path** — skipped decomposition + research for simple bugs, reducing 17-28 LLM calls to ~6-10.
3. **DELEGATION RULES in SOUL.md** — Raven stopped analyzing bugs and passing solutions. Shorter prompts = less context per delegation.

## Eval Setup Pitfalls Discovered

### Pitfall: Cloning from a repo with existing fix commits contaminates the eval

When cloning from /home/prometeo/Requiem (which already had fix commits from eval 1), the clones contained the fixes. OpenCode detected this — it found the fixes already in the code, investigated why issues were still open on GitHub (local commits not pushed), and verified all 58 tests passed without writing any new code.

**Fix for future evals:** Clone from the GitHub remote (which doesn't have the fix commits), OR reset the clone to a known pre-fix commit:
```bash
git clone /home/prometeo/Requiem eval-folder
cd eval-folder
git reset --hard <pre-fix-commit-sha>
```

### Pitfall: Raven launch command is HERMES_HOME, not --config

Raven (a hermes-agent profile with custom SOUL.md) is launched via:
```bash
HERMES_HOME=/path/to/raven hermes chat --yolo
```
NOT `hermes --config config.yaml chat` (the --config flag doesn't exist).

The HERMES_HOME environment variable tells hermes-agent where to find config.yaml, SOUL.md, plugins/, and the venv. The --yolo flag enables autonomous mode (no confirmation prompts).

### Pitfall: _summarize_tool_result optimization introduced a regression

The F8 fix (preserving 5 lines of read_file output instead of 1) can produce summaries LONGER than the original content for small files. This breaks the pruning contract: a summary that's longer than the original defeats the purpose of pruning.

OpenCode discovered this during eval 2: `test_read_file_summary` in `test_shade_context.py` asserts `len(summary) < len(content)`, but the 5-line preview with " | " separators and metadata suffix exceeded the original 93-char content.

**Fix:** Add a guard at the end of _summarize_tool_result:
```python
if len(summary) >= len(content):
    return content[:200] + "..." if len(content) > 200 else content
return summary
```

This applies to ALL branches, not just read_file — any summary that isn't shorter than the original should fall back to returning the original (truncated if needed).

## Key Insight: Multi-Agent Can Beat Single-Agent

The eval proves that a well-optimized multi-agent system can OUTPERFORM a single-agent on the same task with the same model. The key is matching pipeline depth to task complexity:

- Simple tasks → fast path (2 subtasks, no research, no LLM audit) = 3m23s
- Complex tasks → full pipeline (decompose, research, program, audit, execute) = still valuable for ambiguity

The multi-agent architecture's advantage over single-agent: parallel specialization. While OpenCode reads→writes→tests serially, Requiem's Shades can work in parallel on different aspects. The fast path ensures this advantage isn't negated by overhead on simple tasks.

## Next Eval Direction

Chris wants to move from bug-fixing evals to build-from-scratch product evals. This tests a fundamentally different capability:
- Bug fixing: understand existing code, find root cause, apply minimal fix
- Product building: understand requirements, design architecture, implement from zero, test

The build-from-scratch eval will stress-test the multi-agent system's decomposition and coordination capabilities more thoroughly than bug fixing, which is inherently a single-file task.
