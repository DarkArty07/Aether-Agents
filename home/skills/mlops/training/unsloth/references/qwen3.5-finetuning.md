# Qwen3.5 Fine-Tuning & Orchestrator Dataset Design

## Qwen3.5 Training Data Format

Qwen3.5 uses a standard conversation JSON format. Training data must be a JSON file containing a list of conversation samples:

```json
[
  {
    "id": "identity_0",
    "conversations": [
      {"from": "user", "value": "Hello"},
      {"from": "assistant", "value": "Hi! How can I help you?"}
    ]
  }
]
```

### LoRA Fine-Tuning (Single GPU)

```bash
export CUDA_VISIBLE_DEVICES=0
python finetune.py \
    --model_name_or_path "Qwen/Qwen3.5-9B" \
    --data_path "orchestration_data.json" \
    --bf16 True \
    --output_dir "output_hermes_orchestrator" \
    --num_train_epochs 5 \
    --per_device_train_batch_size 1 \
    --per_device_eval_batch_size 1 \
    --gradient_accumulation_steps 16 \
    --evaluation_strategy "no" \
    --save_strategy "steps" \
    --save_steps 1000 \
    --save_total_limit 10 \
    --learning_rate 1e-5 \
    --weight_decay 0.1 \
    --adam_beta2 0.95 \
    --warmup_ratio 0.01 \
    --lr_scheduler_type "cosine" \
    --logging_steps 1 \
    --report_to "none" \
    --model_max_length 512 \
    --gradient_checkpointing True \
    --lazy_preprocess True \
    --use_lora
```

### Key Notes

- **GGUF is for inference only.** Fine-tuning requires the original weights from `Qwen/Qwen3.5-9B` on HuggingFace, NOT the GGUF quantized versions (e.g., `lmstudio-community/Qwen3.5-9B-GGUF`). The GGUF format has quantized weights baked in — LoRA adapters can't be applied to them. Always use the full HF model ID `Qwen/Qwen3.5-9B` in training scripts.
- **Qwen3.5-9B is dense, not MoE.** Total params = active params = 9B. Only the larger Qwen3.5 models (30B-A3B, 35B-A3B) use MoE. QLoRA 4-bit works well for the dense 9B on 16GB VRAM (RTX 4070 Ti Super).
- **Unsloth supports Qwen.** Use Unsloth for 2-5x faster LoRA/QLoRA training with less VRAM.
- **Data format alternatives.** For SFT with TRL's SFTTrainer, JSONL with `instruction/completion` pairs also works:
  ```jsonl
  {"instruction": "necesito implementar auth", "completion": "[decomposition + routing + synthesis]"}
  ```
- **Context7 MCP for Qwen docs.** When researching Qwen fine-tuning specifics, use `mcp_context7_resolve_library_id` with `libraryName: "Qwen"` then `mcp_context7_query_docs` with the resolved ID. The official Qwen repo has LoRA training scripts in `recipes/finetune/` and the docs site has detailed data format specs.

## Qwen3.5-VL-9B vs Qwen3.5-9B: Critical Distinction

**The HuggingFace pages look similar, but the models are fundamentally different.** Downloading the wrong one wastes ~10 GB and adds unnecessary complexity.

### How to Identify Which Model You Have

Check `config.json` in the model directory:

| Signal | Qwen3.5-9B (text-only) | Qwen3.5-VL-9B (multimodal) |
|--------|----------------------|--------------------------|
| `architectures` | `["Qwen3_5ForCausalLM"]` | `["Qwen3_5ForConditionalGeneration"]` |
| `vision_config` | **Absent** | Present (27-layer encoder) |
| `image_token_id` | **Absent** | Present (e.g., 151655) |
| `video_token_id` | **Absent** | Present (e.g., 151656) |
| `model_type` | `"qwen3_5"` | `"qwen3_5"` (same!) |
| Disk size | ~9 GB (4 safetensors shards) | ~19 GB (4 safetensors, larger shards) |
| Attention | Full self-attention only | Hybrid: `linear_attention` + `full_attention` |

**Warning:** `model_type` is `"qwen3_5"` for BOTH — it's not a reliable differentiator. Always check `architectures` and `vision_config`.

### Implications for Fine-Tuning

1. **Text-only fine-tuning on the VL model works but wastes resources.** The vision encoder (~3 GB of parameters) loads into VRAM but is never trained or used. QLoRA 4-bit mitigates this, but you're still paying ~30% more VRAM for dead weight.

2. **Target modules differ.** The VL model has `linear_attention` layers with SSM-style parameters (no `q_proj`/`k_proj`/`v_proj`). Unsloth's `get_peft_model` filters target modules to only those that exist — LoRA is correctly attached only to modules present in the model. No manual filtering needed.

3. **Architecture: `Qwen3_5ForConditionalGeneration`** uses Mamba-style SSM in linear attention layers (`mamba_ssm_dtype: float32`). This is NOT MoE — it's a hybrid attention architecture. QLoRA 4-bit should work, but if it fails, fallback to BF16 LoRA.

4. **Recommendation:** For orchestration (text-only), download `Qwen/Qwen3.5-9B` instead of `Qwen/Qwen3.5-VL-9B`. Smaller, simpler, and all training capacity goes to text understanding.

### Model Download Commands

```bash
# Text-only (recommended for Hermes/orchestration)
huggingface-cli download Qwen/Qwen3.5-9B --local-dir models/Qwen3.5-9B

# VL/multimodal (only if you need vision)
huggingface-cli download Qwen/Qwen3.5-VL-9B --local-dir models/Qwen3.5-VL-9B
```

### WSL2 Performance Note

Model weights on Windows filesystem (`/mnt/c/`) are served via 9P protocol — extremely slow for training I/O. Always copy to Linux native filesystem (`/home/` or a separate ext4 partition) before training. Symlinks from `models/` to the actual location are fine.

## Orchestrator Role Dataset Design

Fine-tuning a model to act as an orchestrator (like Hermes) requires specialized dataset types beyond standard chat data.

### 5 Dataset Types for Orchestrator Fine-Tuning

| Type | Captures | Input → Output |
|------|----------|----------------|
| **A) Orchestration Decisions** | How the model decomposes and routes | user_request → [task, agent, constraints] |
| **B) Delegation Prompts** | Prompt engineering as skill | context + task → crafted structured prompt |
| **C) Synthesis** | Filtering/combining agent responses | [agent_outputs] → user_facing_response |
| **D) Error Recovery** | Resilience patterns | error_context → recovery_strategy |
| **E) Communication Style** | Voice and tone | raw_agent_output → polished response |

### 3 Data Layers

1. **Extractive** — Parse existing `aether.db` sessions, `session_search` transcripts, Honcho observations. Immediate but requires curation. ~50-100 examples from 17 existing sessions.
2. **Instrumented** — Modify Olympus MCP to auto-emit JSONL per `delegate()` call. Structured, clean, accumulates over time. Target: `~/Aether-Agents/home/datasets/orchestration.jsonl`.
3. **Synthetic** — Generate variations with a large model (DeepSeek V4 Pro). Adds diversity and edge cases. Medium-high quality.

### Data Estimates

| Source | Examples | Quality | Timeline |
|--------|----------|---------|----------|
| Extractive only | ~50-100 | High but limited | Immediate |
| + Instrumented (1 month) | ~300-500 | High, diverse | 1 month |
| + Synthetic | ~1,000-3,000 | Medium-high | 2-3 months |

For a 9B model with LoRA, **500 high-quality examples** show measurable difference. **1,000+** enables robust generalization.

### Recommended Training Pipeline

1. **Unsloth** (first choice) — 2-5x faster, QLoRA 4-bit, native Qwen support
2. **Axolotl** (advanced) — YAML config, GRPO/DPO for RL experiments later
3. **TRL SFTTrainer** (alternative) — flexible, native HF, well-documented

### Hardware Target

- RTX 4070 Ti Super (16GB VRAM)
- QLoRA 4-bit via Unsloth
- Batch size 1-2, gradient accumulation 8-16
- Expected training time: ~30min-2hr for 500-1000 examples