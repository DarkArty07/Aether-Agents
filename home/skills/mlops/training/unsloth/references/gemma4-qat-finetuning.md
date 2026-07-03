# Gemma 4 QAT Fine-Tuning with Unsloth

Practical guide to fine-tuning Google DeepMind's Gemma 4 QAT models with Unsloth. Focused on VRAM-constrained setups (16 GB consumer GPUs).

## Model Family Overview

| Model | Total Params | Active Params | Architecture | QAT | VRAM (q4 loaded) | Min GPU |
|-------|-------------|---------------|-------------|-----|------------------|---------|
| Gemma 4 12B QAT | 12B | 12B | Dense | Yes | ~6 GB | RTX 4060 Ti (16 GB) |
| Gemma 4 26B A4B QAT | 26B | 4B | MoE (Unified) | Yes | ~13 GB | RTX 3090 (24 GB) |
| Gemma 4 E2B | 2B | 2B | Dense | No | ~1 GB | Any |
| Gemma 4 E4B | 4B | 4B | Dense | No | ~2 GB | Any |

## What is QAT (Quantization-Aware Training)?

QAT models are trained with **simulated quantization during pre-training**. The model "knows" it will be quantized, so it learns to compensate for precision loss.

**Result:** q4 quality is nearly identical to bfloat16 (<1% quality loss, vs 2-5% for standard post-training quantization).

**Key implication for fine-tuning:** QAT models are ALREADY stored in q4 format. When loading with Unsloth, `load_in_4bit=True` loads the model in its native quantization — no extra quantization step, no conversion overhead.

### QAT vs Regular Quantized Models

| Aspect | Standard q4 (post-training) | QAT q4 |
|--------|---------------------------|--------|
| Quality vs bf16 | 2-5% degradation | <1% degradation |
| Loading process | Quantize during load | Already quantized, direct load |
| MoE 4-bit support | Generally unsupported | **Supported** (pre-quantized) |
| Training stability | Standard | Better (model expects quantization noise) |

## VRAM Estimation — Detailed Breakdown

### Gemma 4 12B QAT (Dense, 12B)

| Component | Memory |
|-----------|--------|
| Weights (q4) | ~6.0 GB |
| Quantization metadata | ~0.5 GB |
| LoRA adapters — r=16 (~150M params × 2B) | ~0.3 GB |
| Optimizer (AdamW 8-bit, 4B/param) | ~0.6 GB |
| Gradients (bf16) | ~0.3 GB |
| Activations (seq=2048, bs=1, grad ckpt) | ~2.0 GB |
| CUDA overhead (kernels, buffers) | ~1.0 GB |
| **Total** | **~10.7 GB** |

✅ **Fits on:** RTX 4070 Ti (16 GB), RTX 4080 (16 GB), RTX 3090 (24 GB), RTX 4090 (24 GB), A6000 (48 GB)

### Gemma 4 26B A4B QAT (MoE, 26B total, 4B active)

| Component | Memory |
|-----------|--------|
| Weights (q4, all 26B experts loaded) | ~13.0 GB |
| Quantization metadata | ~1.5 GB |
| LoRA adapters — r=16 (~200M params × 2B) | ~0.4 GB |
| Optimizer (AdamW 8-bit) | ~0.8 GB |
| Gradients (bf16) | ~0.4 GB |
| Activations (MoE: only 4B active/token) | ~1.5 GB |
| CUDA overhead | ~1.0 GB |
| **Total** | **~18.6 GB** |

✅ **Fits on:** RTX 3090/4090 (24 GB) with tight settings — use `max_seq_length=2048`, `r=8` if needed.
❌ **Does NOT fit on:** 16 GB GPUs (RTX 4070 Ti, RTX 4080) — OOM at ~18.6 GB minimum.

### Why QAT MoE is Different

Standard MoE models (Qwen3-30B-A3B, Qwen3.6-35B-A3B) require bf16 loading because 4-bit quantization of MoE routing layers causes instability. Gemma 4 QAT MoE models are an **exception**: the QAT process pre-quantizes all layers — including MoE routers — with quality guarantees baked in during pre-training. This makes QLoRA viable on MoE models for the first time, dropping VRAM from 63+ GB to ~18.6 GB.

## Recommended Configuration: 16 GB GPU (RTX 4070 Ti / 4080)

For 16 GB VRAM, the **Gemma 4 12B QAT is the right choice**. The 26B does not fit.

```python
from unsloth import FastLanguageModel
import torch

model, tokenizer = FastLanguageModel.from_pretrained(
    model_name="google/gemma-4-12B-QAT",
    max_seq_length=2048,                       # 1024 if OOM
    load_in_4bit=True,
    dtype=torch.bfloat16,
    use_gradient_checkpointing="unsloth",      # Critical for VRAM
)

model = FastLanguageModel.get_peft_model(
    model,
    r=16,                                      # 8 for even less VRAM
    lora_alpha=16,
    target_modules="all-linear",               # Unsloth auto-selects correct modules
    use_gradient_checkpointing="unsloth",
)

# Training
from trl import SFTTrainer, SFTConfig

trainer = SFTTrainer(
    model=model,
    tokenizer=tokenizer,
    train_dataset=dataset,
    args=SFTConfig(
        per_device_train_batch_size=1,
        gradient_accumulation_steps=4,         # Effective batch = 4
        num_train_epochs=3,
        learning_rate=2e-4,
        bf16=True,
        optim="adamw_8bit",
        max_seq_length=2048,
        output_dir="./gemma-4-12b-lora",
    ),
)
trainer.train()

# Save adapter only (16-64 MB)
model.save_pretrained("./gemma-4-12b-lora-adapter")
```

## Recommended Configuration: 24 GB GPU (RTX 3090/4090)

The **Gemma 4 26B A4B QAT fits** with tight settings:

```python
model, tokenizer = FastLanguageModel.from_pretrained(
    model_name="google/gemma-4-26B-A4B-QAT",
    max_seq_length=2048,
    load_in_4bit=True,
    dtype=torch.bfloat16,
    use_gradient_checkpointing="unsloth",
)

model = FastLanguageModel.get_peft_model(
    model,
    r=16,                # Reduce to 8 if OOM during training
    lora_alpha=16,
    target_modules="all-linear",
)
# Same SFTConfig as above, batch_size=1, grad_accum=4
```

## Training Time Estimates

Benchmarks on Unsloth, QLoRA r=16, bf16, batch_size=1, grad_accum=4, seq_len=2048:

| GPU | Model | 500 samples (3 ep) | 2,000 samples (3 ep) | 10,000 samples (2 ep) |
|-----|-------|--------------------|--------------------|--------------------|
| RTX 4080 (16 GB) | 12B QAT | ~20 min | ~1.5 hrs | ~5 hrs |
| RTX 4060 Ti (16 GB) | 12B QAT | ~40 min | ~3 hrs | ~10 hrs |
| RTX 4090 (24 GB) | 26B QAT | ~30 min | ~2 hrs | ~7 hrs |
| A100 80 GB | 26B QAT | ~15 min | ~1 hr | ~3.5 hrs |

**Unsloth is ~2.5× faster than native Hugging Face + TRL.** If using HF without Unsloth, multiply times by 2-3×.

## Data Preparation Pipeline

Gemma 4 uses the standard Gemma chat template:

```
<start_of_turn>user
{prompt}<end_of_turn>
<start_of_turn>model
{response}<end_of_turn>
```

### From Raw Documents to Training Dataset

1. **Chunk documents** into segments of 512–2048 tokens each
2. **Generate instruction-response pairs** — convert each chunk into question/answer format. Use another LLM if needed (e.g., "Given this text, generate 5 diverse questions with answers")
3. **Clean and deduplicate** — remove low-quality pairs, near-duplicates, formatting artifacts
4. **Format with chat template** using `tokenizer.apply_chat_template()`
5. **Create HuggingFace Dataset** with a `"text"` column containing formatted conversations

```python
def format_conversation(context: str, response: str) -> str:
    """Convert a context/response pair to Gemma chat format."""
    messages = [
        {"role": "user", "content": context},
        {"role": "assistant", "content": response},
    ]
    text = tokenizer.apply_chat_template(
        messages, tokenize=False, add_generation_prompt=False
    )
    return text

# Apply to dataset
dataset = dataset.map(
    lambda ex: {"text": format_conversation(ex["context"], ex["response"])}
)
```

### Training Data Strategies by Goal

| Goal | Data Strategy |
|------|--------------|
| Factual knowledge (docs, manuals) | Instruction-response pairs covering domain facts |
| Style or format | Examples demonstrating target output style |
| Reasoning | Step-by-step chain-of-thought examples |
| Tool use | Native tool-use formatted conversation trajectories |
| Multimodal (image input) | Text+image pairs with Gemma's Unified format |

### What NOT to Feed the Model

- Raw unprocessed documents (the model doesn't learn from continuous text)
- Duplicate or near-duplicate examples (causes overfitting)
- Unbalanced datasets (all short or all long examples)
- Examples without clear instruction-response structure

## Gemma 4 Architecture Notes

### Unified Design

Gemma 4 routes multimodal inputs into a decoder-only LLM backbone through **lightweight projection layers** (no separate encoders). For text-only fine-tuning:
- LoRA adapters only affect the text backbone
- Vision projection layers remain frozen
- No VRAM wasted on unused vision components

### MoE (A4B variant)

The "A4B" designation means **Mixture of Experts with 4B active parameters per token** out of 26B total. During training:
- All 26B parameters are loaded in VRAM
- Only 4B participate in each forward pass
- Activations are proportional to active params, not total — this is why the 26B model's activation memory (~1.5 GB) is similar to a dense 4B model

## Common Pitfalls

### "I tried loading the 26B QAT on my 16 GB card and got OOM"

This is expected. The 26B model needs ~18.6 GB minimum. Use the 12B QAT instead, or upgrade to a 24 GB GPU (RTX 3090/4090).

### "Training was going fine then OOM at epoch 2"

Likely a sequence length spike in your dataset. Set `max_seq_length` to truncate long examples, or add `packing=False` to avoid memory fragmentation from sequence packing.

### "My dataset is just raw PDFs converted to text — why is the model worse after training?"

Raw text is not training data. The model needs **instruction-response pairs**. Feeding it continuous prose teaches it to continue prose, not to answer questions. See Data Preparation Pipeline above.

## Cost Comparison: Local vs Cloud

| GPU | Model | 2,000 samples (3 ep) | RunPod spot $/hr | Total cost |
|-----|-------|--------------------|--------------------|-------------|
| Local RTX 4080 (16 GB) | 12B QAT | ~1.5 hrs | — | $0 (electricity only) |
| Local RTX 4090 (24 GB) | 26B QAT | ~2 hrs | — | $0 |
| RunPod RTX 4090 | 26B QAT | ~2 hrs | ~$0.40 | ~$0.80 |
| RunPod A100 80 GB | 26B QAT | ~1 hr | ~$1.00 | ~$1.00 |

For datasets under 5,000 samples, local training is essentially free and fast enough. Cloud only makes sense for 10,000+ samples or if you lack a compatible GPU.
