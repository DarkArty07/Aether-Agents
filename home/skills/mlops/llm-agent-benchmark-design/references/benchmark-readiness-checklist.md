# Benchmark Readiness Checklist

Derived from the failed Asclepio benchmark (2026-07-01) where the user said
"lo hice mal desde el inicio borra todo el benchmark" and all data was deleted.

Run through EVERY item before starting a single model run. If any item is
unchecked, the benchmark is not ready.

---

## Pre-Flight (MUST be complete before any model runs)

### Test Cases
- [ ] Cases have expected outcomes defined (diagnosis, specialist, OTC, alarms)
- [ ] Expected outcomes validated by a domain expert or clinical guidelines
  (NOT by the LLM that designed the benchmark)
- [ ] Patient turns are vague but information-dense (1 key fact per turn)
- [ ] By turn 3-4, the model has enough info to start orienting
  (if no model converges by turn 5, prompts are too vague, not models too slow)
- [ ] User has approved cases AND turn-level vagueness

### Scoring Rubric
- [ ] D1-D6 (or equivalent) dimensions defined with weights
- [ ] Penalties defined (e.g., -100 for missing a cardiac alarm)
- [ ] Safety factor multiplier defined (0.50, 0.75, 0.90, 1.00)
- [ ] Gate criteria defined (which cases are pass/fail safety gates)
- [ ] Rubric is ready to apply IMMEDIATELY after each run (not deferred)

### Transcript Capture
- [ ] Mechanism to save FULL verbatim transcripts to disk after EVERY turn
  (tmux capture-pane -S -200, or tee from session start)
- [ ] NOT relying on context window to hold responses (it WILL be compacted)
- [ ] NOT capturing only tail -20 or summaries (fragments are useless for D1-D6)
- [ ] Transcript files named: results/raw/{model}_{case}.log

### Model Setup
- [ ] All model IDs verified against gateway /v1/models endpoint
- [ ] Model IDs use hyphens not dots (claude-sonnet-4-6, not claude-sonnet-4.6)
- [ ] All models registered in config.yaml custom_providers
- [ ] Designer model is NOT in the evaluated set (no conflict of interest)
- [ ] API key exported in environment before starting tmux

### Session Isolation
- [ ] Plan to /reset between cases (not just between models)
- [ ] Plan to verify tokens=0 after each /reset
- [ ] Plan to kill+restart tmux between models

### Metrics Capture
- [ ] Plan to run /status after EVERY turn (not just at case end)
- [ ] Plan to record per-turn: tokens, time_s, tool_calls, response text
- [ ] Plan to record convergence milestones: T_orient, T_otc, T_tools

## Red Flags (STOP if any of these are true)

- You're capturing tmux output into your context but NOT writing to disk
- You designed the rubric with a model that's also being evaluated
- You plan to "do qualitative evaluation after all runs finish"
  (you'll be evaluating from memory/summaries, not transcripts)
- You have no domain expert validating the expected clinical outcomes
- Your test prompts are so vague that no model converges by turn 5
- You're only measuring tokens/time/tools (efficiency) with no quality metrics
- You haven't defined what "better" means (which dimensions matter most?)

## Post-Mortem: Asclepio Benchmark Failure (2026-07-01)

**What happened:** Benchmark of 12 models for Asclepio (health triage agent).
2 models completed (claude-sonnet-4-6, claude-opus-4-8) across 5 cases each.
User asked "cual es la conclusion" — no answer available because:
1. Full transcripts were NOT saved (only summaries and fragments)
2. D1-D6 qualitative evaluation was NEVER applied
3. Opus designed the rubric AND was evaluated (conflict of interest)
4. Only efficiency metrics existed (tokens, time, tool calls)
5. No domain expert validated expected clinical outcomes

**User's verdict:** "No me sirve este benchmark lo hice mal desde el inicio"

**Data recovered:** Nothing. All benchmark files deleted. tmux sessions killed.
The 2 completed models' conversation transcripts are permanently lost.

**Lesson:** The benchmark isn't the numbers. The benchmark is the QUALITATIVE
EVALUATION of full transcripts against a validated rubric. Without transcripts,
there is no benchmark — just a token counter.
