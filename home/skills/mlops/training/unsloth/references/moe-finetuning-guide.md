# MoE Fine-Tuning Guide with Unsloth

## Model Sizes and Disk Space

| Model | Total Params | Active Params | BF16 Size (disk) | GGUF Q4_K_M | Context |
|-------|-------------|---------------|-------------------|-------------|---------|
| Qwen3-8B | 8B | 8B | ~16 GB | ~5 GB | 128K |
| Qwen3-30B-A3B | 30B | 3B | ~60 GB | ~17 GB | 128K |
| Qwen3.6-35B-A3B | 35B | 3B | ~70 GB | ~20.5 GB | 262K |
| Qwen3.5-27B | 27B | 27B | ~54 GB | ~15 GB | 128K |
| Qwen3.5-397B-A17B | 397B | 17B | ~794 GB | — | 128K |
| DeepSeek-V3 | 671B | 37B | ~1.3 TB | — | 128K |

## VRAM Requirements for Fine-Tuning

### Dense Models (bf16 LoRA, r=16)

| Model | VRAM (LoRA r=16) | VRAM (QLoRA 4-bit) | Min GPU |
|-------|-------------------|---------------------|----------|
| Qwen3-4B | ~10 GB | ~4 GB | RTX 3060 (12GB) |
| Qwen3-8B | ~18 GB | ~7 GB | RTX 4090 (24GB) |
| Qwen3.5-27B | ~56 GB | ~16 GB | A100 80GB |
| Llama-3.1-70B | ~56 GB | ~20 GB | A100 80GB |

### MoE Models (bf16 LoRA only — QLoRA NOT supported for standard MoE)

**Exception: QAT MoE models (Gemma 4 26B A4B QAT)** support 4-bit loading because the QAT process pre-quantizes all layers including MoE routers. This drops VRAM from 63+ GB (bf16) to ~18.6 GB (q4). See `references/gemma4-qat-finetuning.md` for full details.

| Model | VRAM (bf16 LoRA) | VRAM (4-bit QAT) | Min GPU | Notes |
|-------|-----------------|---------|-------|
| Qwen3-30B-A3B | 63 GB | — | 1× A100 80GB | Loading spike to 43GB, settles to ~17GB |
| Qwen3.6-35B-A3B | 63-74 GB | — | 1× A100 80GB | Most common MoE for agents |
| Qwen3.5-397B-A17B | ~256 GB | — | 4× A100 80GB | Requires multi-GPU |
| Gemma 4 26B A4B QAT | — | ~18.6 GB | RTX 3090 (24 GB) | QAT pre-quantized. See gemma4-qat-finetuning.md |

**Critical:** During model loading, VRAM spikes to ~43GB+ for Qwen3-30B/35B-A3B, then drops after sharding completes. Your GPU must handle the peak.

## RunPod GPU Selection Guide

### By Model Size

| Model | Recommended GPU | RunPod $/hr (spot) | Notes |
|-------|----------------|---------------------|-------|
| ≤8B dense | RTX 4090 (24GB) | ~$0.40 | Local or spot |
| 8B dense (bf16) | A6000 (48GB) | ~$0.36 | Headroom for longer context |
| 27B dense | A100 80GB | ~$1.00 | bf16 LoRA |
| 30B/35B MoE | A100 80GB | ~$1.00 | bf16 LoRA, no QLoRA |
| 70B+ | 2× A100 80GB | ~$2.00 | Multi-GPU |

### Cost Calculator

For SFT training on RunPod (A100 80GB, ~$1.00/hr spot):

| Dataset Size | Epochs | Seq Length | Est. Time | Est. Cost |
|-------------|--------|------------|-----------|-----------|
| 1K samples | 3 | 2048 | 0.5-1 hr | $0.50-1.00 |
| 5K samples | 3 | 2048 | 2-4 hrs | $2-4 |
| 10K samples | 5 | 4096 | 6-12 hrs | $6-12 |
| 50K samples | 5 | 4096 | 1-2 days | $24-48 |
| 100K samples | 5 | 8192 | 3-5 days | $72-120 |

These estimates assume r=16 LoRA with gradient checkpointing on Qwen3.6-35B-A3B.

## SFT vs RL Training — Cost Comparison

### SFT (Supervised Fine-Tuning)

- **Where:** RunPod, Colab, or local GPU
- **Cost:** $0-48 depending on dataset and GPU
- **Time:** 1-24 hours
- **Tool:** Unsloth + TRL
- **Data:** ShareGPT trajectories (from Hermes `save_trajectories` or manual curation)
- **Best for:** Teaching new behaviors, tool use, style

### RL (GRPO with Tinker)

- **Where:** Tinker cloud (thinkingmachines.ai)
- **Cost:** $310-31,000+ depending on steps
- **Time:** 1-12+ hours
- **Tool:** Tinker API + Atropos
- **Data:** Environment + reward function (not trajectories)
- **Best for:** Refining existing behavior, optimizing for specific metrics

### Recommended Pipeline

1. **Generate SFT data** — Use Hermes `save_trajectories: true` or batch_runner
2. **SFT locally** — Unsloth on RunPod A100 or local GPU ($0-48)
3. **Evaluate** — Test the LoRA adapter
4. **Optional: RL refinement** — Tinker for 100-300 steps ($600-1,900)
5. **Export** — GGUF for local inference, or merged for vLLM

## Unsloth MoE Training Code Template

```python
from unsloth import FastLanguageModel
from trl import SFTTrainer
from transformers import TrainingArguments

# Load MoE model in bf16 (NOT 4-bit)
model, tokenizer = FastLanguageModel.from_pretrained(
    model_name="unsloth/Qwen3.6-35B-A3B",
    max_seq_length=2048,
    load_in_4bit=False,        # MoE: always bf16
    load_in_16bit=True,         # bf16 LoRA
    full_finetuning=False,
)

# Attach LoRA with MoE-aware target modules
model = FastLanguageModel.get_peft_model(
    model,
    r=32,                        # LoRA rank (16, 32, 64)
    target_modules=[
        "q_proj", "k_proj", "v_proj", "o_proj",
        "gate_up_proj", "down_proj",  # MoE layers
    ],
    lora_alpha=64,               # 2x rank for faster convergence
    lora_dropout=0,
    bias="none",
    use_gradient_checkpointing="unsloth",  # Reduces VRAM
    random_state=3407,
    max_seq_length=2048,
)

# Train
trainer = SFTTrainer(
    model=model,
    tokenizer=tokenizer,
    train_dataset=dataset,
    dataset_text_field="text",
    max_seq_length=2048,
    args=TrainingArguments(
        per_device_train_batch_size=1,
        gradient_accumulation_steps=8,
        warmup_steps=10,
        num_train_epochs=3,
        learning_rate=2e-4,
        bf16=True,
        logging_steps=10,
        save_steps=100,
        output_dir="outputs",
    ),
)
trainer.train()

# Save LoRA adapter
model.save_pretrained("qwen3.6-35b-agent-lora")
tokenizer.save_pretrained("qwen3.6-35b-agent-lora")

# Export to GGUF
model.save_pretrained_gguf("qwen3.6-35b-agent-lora", tokenizer)
```

## Common Errors and Fixes

### RuntimeError: CUDA out of memory during loading

Unsloth loads all model shards simultaneously. VRAM spikes to 2x the final training size. If you OOM during loading:

1. Set `max_seq_length=1024` (reduces activation memory)
2. Use `use_gradient_checkpointing="unsloth"` (already default)
3. Reduce `per_device_train_batch_size` to 1 with `gradient_accumulation_steps=8`
4. Use a GPU with more VRAM

### ValueError: Some modules dispatched to CPU or disk

Your GPU doesn't have enough VRAM even for the quantized model. Solutions:
- Use a smaller model (8B instead of 35B)
- Rent a bigger GPU (A100 80GB)
- Use multi-GPU with `device_map="balanced"`

### Very slow MoE training

Ensure `UNSLOTH_MOE_BACKEND=grouped_mm` (default). This uses PyTorch's `torch._grouped_mm` for 12x speedup. On A100+, Unsloth auto-enables Triton kernels for additional 2x speedup.

### Loss is NaN or exploding

- Reduce learning rate (try 1e-5 or 5e-6 for MoE)
- Use `lora_alpha=2*r`
- Ensure bf16 is enabled (`bf16=True` in TrainingArguments)
- Check that training data doesn't have extremely long sequences