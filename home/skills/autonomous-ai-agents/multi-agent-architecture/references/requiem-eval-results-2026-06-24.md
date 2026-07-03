# Requiem vs OpenCode — Comparative Eval Results (2026-06-24)

First end-to-end comparative eval of Requiem Agents vs OpenCode CLI.
Same model (glm-5.2), same 3 bugs, same project, isolated working directories.

## Results

| Metric | OpenCode | Requiem |
|--------|----------|---------|
| Issues fixed | 3/3 | 0/3 (did not finish) |
| Time | 8m48s | 18m+ (interrupted) |
| Context used | ~43K tokens | 98K/128K (77%) |
| Tests created | 53 | 0 |
| LLM calls per bug | 4-6 | 17-28 |
| Tool calls per iteration | 2-3 (parallel) | 1 (serial) |

## OpenCode Summary

OpenCode resolved all 3 bugs autonomously in 8m48s:
- Issue #1 (parse_verdict logic): rfind() fix, 24 tests
- Issue #2 (connection leak + JSON crash): own-connection fix, try/except JSONDecodeError, .bak backup, 9 tests
- Issue #3 (_summarize_tool_result info loss): last-3-lines fallback, narrowed exception, error flagging, 20 tests
- 381 total tests passed, 0 failed (excluding pre-existing broken test)
- All files compile

## Requiem Summary

Raven could not complete a single issue in 18 minutes:
- Loaded all 3 issues via delegate_task (gh issue view)
- Used read_file_simple to read revenant.py and server.py
- Loaded necromancer-delegation skill
- Delegated all 3 issues to Necromancer with detailed templates
- Necromancer decomposed Issues #2 and #3 into subtasks
- Shades were still in early iterations (research reading files, programming doing grep) when interrupted
- 77% of context consumed by polling (check_progress + execute_code time.sleep)

## 8 Architectural Failure Modes Identified

### F1: Shades make 1 tool call per iteration (CRITICAL)

Shade programming did 1 read_file → LLM response → 1 grep → LLM response → 1 read_file → ...
OpenCode does 3+ tool calls per turn (read_file + grep + read_file in one response).

Root cause: TOOL_INSTRUCTIONS_TEMPLATE says "output a JSON block on its own line" (singular).
The LLM follows this literally, generating 1 tool call per response.
Fix: instruct the LLM it CAN output MULTIPLE tool calls in a single response.

Impact: 2.5x more tokens, 2.5x more time per task.

### F2: Too many hops for simple tasks (CRITICAL)

Pipeline for a 10-line bug: Raven reads issue (2-3 calls) → Necromancer decomposes (1 call) →
Shade research investigates (3-6 calls) → Shade programming writes (5-10 calls) →
Revenant audits (1-3 calls) → Shade execution runs tests (2-4 calls) → Revenant audits (1 call) →
Raven presents (1 call) = 17-28 LLM calls.

OpenCode: 4-6 calls for the same bug.

Fix: Fast path — classify simple tasks heuristically, skip decomposition + research,
go directly to programming + execution with lightweight Revenant (py_compile + pytest only, no LLM).

### F3: check_progress wastes Raven's context (HIGH)

Raven spent ~15 LLM calls on execute_code(time.sleep(30)) + check_progress.
Each sleep is a full LLM turn that produces nothing. 98K/128K tokens (77%) were
consumed by polling, not by work.

Fix: check_progress with wait=true parameter — blocks internally (3s poll loop)
until task completes or timeout. Raven makes 1 call instead of 15.

### F4: Revenant rejects has_files=False, Shade restarts from scratch (HIGH)

Shade finishes without writing files (ran out of iterations or context).
Revenant rejects. Shade restarts from zero — re-reads the same files,
burns the same tokens. No context carried forward from the failed attempt.

Fix: (1) Pass feedback context in retry ("Do NOT re-read files you already know").
(2) Guard at iteration 15: if no files written, force "write NOW" message.

### F5: Raven gives the answer to the Necromancer (MEDIUM)

Raven's delegation prompt for Issue #1 was ~800 words and included:
"The fix should use str.rfind() to find the last position of each token"
Raven solved the bug in its reasoning, then told the Shade exactly how to fix it.
This defeats the purpose of delegation — Raven should route, not solve.

Fix: SOUL.md rule — paste issue verbatim, do NOT analyze the fix. The template
fields should be filled with information FROM THE ISSUE, not Raven's analysis.

### F6: No fast path for simple tasks (covered by F2)

Same pipeline for 10-line bug and 500-line feature. No task classification.

### F7: Shade research is useless for bugs with sufficient context (MEDIUM)

Shade research did 7 iterations of read_file on the same file that Shade programming
was going to read anyway. 7 wasted LLM calls producing information the programming
Shade rediscovers independently.

Fix: Skip research for specific bug fixes. Research only for vague tasks
("improve performance", "refactor module").

### F8: _summarize_tool_result loses critical context (MEDIUM)

When read_file results are pruned to 1-line summaries, the Shade loses file content
it needs. Shades re-read the same file in iterations 1, 3, 4, 10, 14, 18 —
6 reads of the same file because the summary lost the content.

Fix: (1) Preserve first 5 lines of read_file in the summary (not just first_line).
(2) Increase _PROTECT_LAST_N from 5 to 8 (protect more recent turns).

## Optimization Plan (PLAN-OPTIMIZATION.md)

3-phase plan to fix all 8 failure modes:

Phase A (high impact, small change): F1 (parallel tool calls), F3 (wait=true), F5 (SOUL.md rule)
Phase B (structural changes): F2+F6+F7 (fast path), F4 (retry context), F8 (summarize fix)
Phase C (verification): Re-eval with same 3 bugs

Expected post-optimization: 3/3 bugs, 6-10m, <60K tokens, 6-10 LLM calls per bug.

## Optimization Implementation (commit b3d7c03)

All 8 fixes were implemented in a single autonomous session:

### Phase A (applied)
- F1: TOOL_INSTRUCTIONS_TEMPLATE updated with "You CAN output MULTIPLE tool calls in a single response"
- F3: handle_check_progress now accepts wait=true (blocks internally with 3s poll loop, wait_timeout param). CHECK_PROGRESS_SCHEMA updated with wait and wait_timeout fields.
- F5: SOUL.md appended with "DELEGATION RULES" section — Raven must paste issue verbatim, not analyze the fix

### Phase B (applied)
- F2+F6+F7: _is_simple_task() classifier added. process_task() fast path: simple tasks skip LLM decomposition + Shade of Research, go directly to programming + execution (2 subtasks). Decompose prompt updated to skip research for specific bug fixes.
- F4: Retry in _execute_subtask now passes "Do NOT re-read files you already know. Go directly to writing the fix." Guard at iteration 15: if no files written, force "write NOW" message.
- F8: _PROTECT_LAST_N increased from 6 to 8. _summarize_tool_result read_file branch now preserves first 5 lines (preview = " | ".join(lines)[:200]) instead of just first_line.

### Phase C (re-eval environment prepared)
Clones created at /home/prometeo/eval-requiem and /home/prometeo/eval-opencode
with optimized code (commit b3d7c03). Config.yaml paths updated to point to
eval-requiem. venv and .env copied from original. Prompts prepared for both
agents with explicit autonomous instructions. Awaiting user to configure models
and launch.

### Key implementation note
Hefesto's patch tool had recurring "Escape-drift detected" errors when patching f-strings with escape sequences in necromancer.py. The workaround was to re-delegate with simpler old_string/new_string pairs that avoided backslash-heavy content. This is the same "Patch-generated f-strings with escape sequences break silently" pitfall already documented in the SKILL.md.

## Key Insight

The eval revealed that the multi-agent overhead (decomposition, research, audit,
retry loops) is LARGER than the work itself for simple tasks. The architecture
designed for complex, multi-file, ambiguous tasks is being applied to 10-line
bug fixes. A task-complexity classifier at the entry point is the single most
impactful change — it determines whether the full pipeline runs or a fast path
bypasses most of it.

This is NOT a failure of the multi-agent concept. It's a failure of task routing.
The architecture works for complex tasks; it just needs to NOT apply itself to
simple ones. The fix is a gate, not a redesign.

## Bug Selection for Future Evals

The 3 bugs used in this eval were well-suited:
- Bug #1 (parse_verdict logic): single function, clear fix — tests fast path
- Bug #2 (API connection leak + JSON crash): cross-file understanding — tests decomposition
- Bug #3 (_summarize_tool_result info loss): information flow — tests auditor quality

For future evals, keep this mix: 1 simple (fast path candidate), 1 medium (decomposition), 1 hard (audit quality).
