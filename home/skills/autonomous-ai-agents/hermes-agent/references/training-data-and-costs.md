# Hermes Training Data & Fine-Tuning Cost Reference

## Generating SFT Data with save_trajectories

Enable in `config.yaml`:
```yaml
agent:
  save_trajectories: true   # default: false
```

Output: `trajectory_samples.jsonl` (completed conversations) and `failed_trajectories.jsonl` (incomplete/errored conversations) in the working directory.

### Trajectory Format (ShareGPT-compatible JSONL)

Each line:
```json
{
  "conversations": [
    {"from": "system", "value": "You are a function calling AI model..."},
    {"from": "human", "value": "What Python version?"},
    {"from": "gpt", "value": "\u00abthink\u00bb\nI should check...\n\u00bb/think\u00bb\n\u00absched\u00bb\n{\"name\": \"terminal\", \"arguments\": {\"command\": \"python3 --version\"}}\n\u00bb/sched\u00bb"},
    {"from": "tool", "value": "\u00abresult\u00bb\n{\"name\": \"terminal\", \"content\": \"Python 3.11.6\"}\n\u00bb/result\u00bb"},
    {"from": "gpt", "value": "Python 3.11.6 is installed."}
  ],
  "timestamp": "2026-03-30T14:22:31",
  "model": "anthropic/claude-sonnet-4.6",
  "completed": true
}
```

### Normalizations
- **Reasoning**: All formats (native thinking tokens, REASONING_SCRATCHPAD XML) normalized to `\u00abthink\u00bb...\u00bb/think\u00bb` tags. Empty think blocks inserted for turns without reasoning.
- **Tool calls**: Normalized to XML `\u00absched\u00bb{JSON}\u00bb/sched\u00bb` with parsed arguments (not double-encoded).
- **Tool responses**: Grouped into single `\u00abtool\u00bb` message with `\u00abresult\u00bb{JSON}\u00bb/result\u00bb`.
- **System prompt**: Regenerated at save time, not preserved from conversation.

### Batch Processing (large-scale generation)
```bash
python batch_runner.py \
    --dataset_file=data/prompts.jsonl \
    --batch_size=20 \
    --run_name=my_run \
    --model=anthropic/claude-sonnet-4.6 \
    --num_workers=4 \
    --max_turns=15
```

Adds extra fields: `tool_stats`, `tool_error_counts`, `toolsets_used`, `api_calls`, `prompt_index`. Output in `data/<run_name>/trajectories.jsonl`.

### Privacy: ephemeral_system_prompt
Set a system prompt that guides behavior but is NOT saved to trajectory files:
```python
agent = AIAgent(
    model="...",
    save_trajectories=True,
    ephemeral_system_prompt="You are a SQL expert. Only answer database questions.",
)
```

## Tinker RL Training (Cloud)

Tinker is a **training-as-a-service** platform by Thinking Machines. Charges per million tokens (prefill/sample/train).

### Pricing for Qwen3.6-35B-A3B (MoE, 3B active params)
| Operation | Per M tokens | Notes |
|-----------|-------------|-------|
| Prefill | $0.36 | Forward pass only |
| Sample | $0.89 | Forward + sampling |
| Train | $1.07 | Forward + backward (LoRA) |
| Storage | $0.031/GB/month | Checkpoint storage |

### Cost Estimates with Hermes Defaults (batch_size=128, group_size=16)
| Steps | Cost Range | Use Case |
|-------|-----------|-----------|
| 50-100 | $300-600 | PoC / validation |
| 300-500 | $1,850-3,100 | Basic tool-calling |
| 1,000-2,000 | $6,200-12,400 | Functional agent |
| 3,000-5,000 | $18,600-31,000 | Production-quality agent |

**Important:** RL training on Tinker requires SFT first. A base model cannot do RL — it doesn't generate useful completions. Budget SFT locally, then consider Tinker only for RL refinement.

### Tinker Requirements
- `TINKER_API_KEY` + `WANDB_API_KEY`
- Python >= 3.11
- `tinker-atropos/` submodule in Hermes root
- Hercules Hermes tools: `rl_list_environments`, `rl_select_environment`, `rl_edit_config`, `rl_start_training`, `rl_check_status`, `rl_stop_training`, `rl_get_results`, `rl_test_inference`

## SFT Fine-Tuning (Local or RunPod)

### Recommended: Unsloth on RunPod

| GPU | VRAM | Qwen3.6-35B-A3B bf16 LoRA | $/hr |
|-----|------|----------------------------|------|
| RTX 4090 | 24 GB | Does NOT fit (needs 63-74 GB) | — |
| A6000 | 48 GB | Does NOT fit | ~$0.60 |
| 2×A6000 | 96 GB | Fits comfortably | ~$1.20 |
| A100 80GB | 80 GB | Fits | ~$1.40-2.00 |
| 2×A100 40GB | 80 GB | Fits (tensor parallel) | ~$1.40 |
| H100 80GB | 80 GB | Fits, fastest | ~$2.50-3.50 |

**Critical:** QLoRA (4-bit) is NOT recommended for MoE models (Qwen3.6-35B-A3B, Qwen3-30B-A3B, etc.) — BitsandBytes doesn't support MoE quantization properly. Use bf16 LoRA only.

### Smaller models that fit on consumer GPUs
| Model | Params | QLoRA VRAM | bf16 LoRA VRAM |
|-------|--------|------------|----------------|
| Qwen3-8B | 8B dense | ~6 GB | ~22 GB |
| Qwen3-4B | 4B dense | ~4 GB | ~10 GB |
| Qwen3-30B-A3B | 30B MoE | Not recommended | ~63 GB |
| Qwen3.6-35B-A3B | 35B MoE | Not recommended | ~63-74 GB |

### Typical SFT Costs on RunPod (1× A100 80GB, $1.40/hr)
| Dataset Size | Steps | Time | Cost |
|-------------|-------|------|------|
| 1K-5K samples | 500-1,000 | 2-7 hrs | $3-10 |
| 10K-50K samples | 1,000-3,000 | 7-20 hrs | $10-28 |
| 50K-200K samples | 3,000-8,000 | 1-3 days | $34-100 |

### Practical Pipeline
1. **Generate data** with Hermes `save_trajectories: true` or `batch_runner.py` — $0 (uses your normal API)
2. **Filter for quality** — discard samples with no reasoning, hallucinated tools, failed tool calls
3. **SFT locally** with Unsloth on RunPod A100 — $3-28 typically
4. **Evaluate** the fine-tuned model
5. **Optional: RL refinement** on Tinker — only if SFT results need improvement (costs $3K+)

This pipeline (SFT only) gives 80% of the result for 1-5% of the cost of a full RL pipeline on Tinker.