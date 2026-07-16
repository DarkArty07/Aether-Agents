# Daimon Reliability Benchmark — v0.18.0

This directory is the static benchmark package for **v0.18.0 “Daimon Reliability”**. It evaluates prompt behavior without changing runtime `SOUL.md`, configuration, templates, or baseline v0.17 prompts.

## Contents

- `cases.json` — versioned case contract for the six GPT-5.6-Terra Daimons.
- `validate_cases.py` — dependency-free structural validator.
- `results/` — reserved for baseline and post-prompt artifacts; only `.gitkeep` is versioned.

## Safety and execution rules

All cases are read-only or explicitly synthetic/disposable fixtures. Do not supply real credentials, call network services, mutate production systems, or reuse a case session for another case. Capture the complete response plus full tool/function trace; summaries are not sufficient evidence.

## Validation

```bash
python3 evaluations/daimon-reliability-v0.18.0/validate_cases.py
```

The validator checks JSON parsing, required evidence fields, unique IDs, safe execution declarations, the 18-case minimum, all-agent minimums, Athena’s four gate semantics, and the required positive/boundary/failure coverage.

## Baseline/post comparison

1. Record a **baseline** against untouched v0.17 prompts.
2. Change only the approved role-specific prompt text in a later implementation task.
3. Re-run the same case IDs, model route, fixture, and evaluator protocol as **post**.
4. Store full transcripts, invocation traces, deterministic assertion results, manual rubrics, and a score summary under `results/baseline/` or `results/post/` (untracked unless a later release decision says otherwise).
5. Compare safety/release gates first, then score dimensions. A post run cannot claim improvement when a required evidence artifact is absent.

Do not average away a release-blocking gate failure. Operational failures are distinct from security or behavioral failures and must be evaluated with their current evidence.
