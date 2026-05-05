# Compression Tuning for Orchestration Workloads

## Default vs Orchestration-Optimized

| Parameter | Default | Orchestration | Why |
|-----------|---------|---------------|-----|
| `threshold` | 0.50 | **0.65** | Compress later = more context preserved, but not so late that summaries are imprecise |
| `target_ratio` | 0.20 | **0.30** | 30% tail protection keeps more recent messages intact |
| `protect_last_n` | 20 | **30** | Each delegation = 5-10 messages. 30 protects 3-5 full delegations |
| `hygiene_hard_message_limit` | — (400) | **300** | Gateway safety net triggers earlier |

## Why orchestration needs different settings

Delegation/subagent workflows generate much more context per exchange than simple chat:
- `delegate_task` produces 5-10+ messages per call (context + task assignment + result)
- `run_workflow` with HITL interrupts adds user confirmation exchanges
- 20 protected messages = only 2-3 delegations, losing thread on complex pipelines
- Higher threshold (0.65) lets context grow more before compressing, but 0.80 is too aggressive (summaries become imprecise)

## How it works (GLM-5.1, 128K context)

```
0K ──────────── 83K (65%) ────────────── 108K (85%) ─── 128K
    head           ↑ compress here         gateway hygiene     limit
    (protected)    │                       safety net
                   ├── 70% → summarized (old context)
                   └── 30% → tail protected (recent messages)
```

## Commands

```bash
hermes config set compression.threshold 0.65
hermes config set compression.target_ratio 0.30
hermes config set compression.protect_last_n 30
hermes config set compression.hygiene_hard_message_limit 300
```

## Context Engines

- `compressor` (default) — lossy: summarizes old context, preserves recent. Best for 128K contexts.
- `lcm` (lossless) — preserves everything, selects what to show. Better for 1M+ contexts.

For orchestration on 128K context, `compressor` with the above tuning is recommended.