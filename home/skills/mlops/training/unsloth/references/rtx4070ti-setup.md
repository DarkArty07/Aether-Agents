# RTX 4070 Ti Super Environment Setup (16GB VRAM)

Concrete setup recipe for QLoRA fine-tuning with Unsloth on RTX 4070 Ti Super.
Tested: CUDA 13.2 driver, WSL2 Ubuntu, Python 3.11.15, PyTorch 2.12.0+cu126.

## Hardware Profile

| Component | Value |
|-----------|-------|
| GPU | RTX 4070 Ti SUPER (Compute 8.9) |
| VRAM | 16 GB (16376 MiB) |
| QLoRA 4-bit fit | ✅ Qwen3.5-9B fits with batch_size=2, seq=2048 |
| BF16 support | ✅ Available |

## Full Install Recipe

```bash
# 1. Create venv (Python 3.11 specifically — avoid 3.12+ for Unsloth compat)
python3.11 -m venv venv
source venv/bin/activate

# 2. PyTorch with CUDA 12.6 (compatible with CUDA 13.x drivers)
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu126

# 3. Core dependencies BEFORE Unsloth (Unsloth will downgrade some)
pip install transformers peft bitsandbytes trl accelerate datasets scipy

# 4. Optional: xformers (attention), wandb (logging)
pip install xformers wandb

# 5. Unsloth from git (MUST install last — it pins compatible versions)
pip install "unsloth[colab-new] @ git+https://github.com/unslothai/unsloth.git"
```

**Order matters.** Step 3 installs latest versions, step 5 downgrades them to Unsloth-compatible pins. Installing Unsloth first then other packages will break the pinning.

## CUDA Driver Compatibility

PyTorch wheels use CUDA toolkit versions (e.g., `cu126` = CUDA 12.6). The CUDA version shown in `nvidia-smi` (e.g., 13.2) is the **driver's maximum supported CUDA version**. CUDA toolkits are backward-compatible — a CUDA 12.6 PyTorch build works fine on CUDA 13.2 drivers.

**Rule:** match PyTorch's CUDA version ≤ driver's CUDA version. PyTorch cu126 works on drivers ≥ 12.6.

## PyTorch 2.12 API Changes

### `CudaDeviceProperties.total_mem` → `total_memory`

```python
# ❌ Removed in PyTorch 2.12
props = torch.cuda.get_device_properties(0)
vram = props.total_mem  # AttributeError

# ✅ Current API
vram = props.total_memory  # Returns bytes
vram_gb = vram / (1024 ** 3)
```

### Enum warnings (benign)

```
WARNING: <enum 'KernelPreference'> is an Enum subclass and is now natively supported
by torch.compile as an opaque value type. Calling register_constant() on Enum subclasses
is deprecated and will be an error in a future release.
```

These are from Unsloth's torch.compile integration. Harmless — filter them or ignore.

## nvidia-smi Query Compatibility

The `--query-gpu` field names differ across driver versions. Known-safe fields:

```bash
# ✅ Always works
nvidia-smi --query-gpu=name,memory.total,driver_version --format=csv,noheader,nounits

# ❌ May fail on some versions
nvidia-smi --query-gpu=cuda_version ...   # Not a valid field
nvidia-smi --query-gpu=compute_cap ...    # Works but only returns compute capability

# ✅ Reliable: parse CUDA version from top-level output
nvidia-smi | grep -oP 'CUDA Version:\s*\K[\d.]+'
```

## Unsloth Compatibility Downgrades

Installing Unsloth 2026.5.7 downgrades these packages to tested versions:
- `transformers`: 5.9.0 → 5.5.0
- `trl`: 1.5.0 → 0.24.0
- `datasets`: 4.8.5 → 4.3.0
- `dill`: 0.4.1 → 0.4.0
- `multiprocess`: 0.70.19 → 0.70.16

This is **expected** — Unsloth pins specific versions for compatibility. Do not re-upgrade these manually.

## Verification Script Pattern

```python
# Minimal verification after install:
import torch
assert torch.cuda.is_available(), "CUDA not available"
print(f"GPU: {torch.cuda.get_device_name(0)}")
print(f"VRAM: {torch.cuda.get_device_properties(0).total_memory / 1024**3:.1f} GB")

import unsloth
from unsloth import FastLanguageModel, is_bfloat16_supported
print(f"Unsloth: {unsloth.__version__}, BF16: {is_bfloat16_supported()}")

import bitsandbytes as bnb
print(f"bitsandbytes: {bnb.__version__}")
```

## Flash Attention 2 vs Xformers

Unsloth prefers Flash Attention 2 but auto-falls back to xformers. The message:

```
Unsloth: Your Flash Attention 2 installation seems to be broken.
Using Xformers instead. No performance changes will be seen.
```

is informational only — no action needed. xformers provides equivalent performance for LoRA training.

## Qwen3.5-9B Specifics

- **Architecture:** Dense (not MoE). Total params = active params = 9B.
- **QLoRA support:** ✅ 4-bit quantization works. Fits in 16GB VRAM.
- **Target modules:** `q_proj, k_proj, v_proj, o_proj, gate_proj, up_proj, down_proj`
- **MoE models** (Qwen3-30B-A3B, Qwen3.6-35B-A3B) do NOT support QLoRA 4-bit — use BF16 LoRA only.
- **Chat template:** Qwen3.5 native `<|im_start|>` / `<|im_end|>` format. Unsloth's tokenizer handles this automatically.

### Pitfall: Qwen3.5-VL-9B vs Qwen3.5-9B

The HuggingFace hub hosts both `Qwen/Qwen3.5-9B` (text-only) and `Qwen/Qwen3.5-VL-9B` (multimodal). They have the same `model_type: "qwen3_5"` — check `config.json`:

- **Text-only** (`Qwen3.5-9B`): `architectures: ["Qwen3_5ForCausalLM"]`, no `vision_config`, ~9 GB
- **VL** (`Qwen3.5-VL-9B`): `architectures: ["Qwen3_5ForConditionalGeneration"]`, has `vision_config` + `image_token_id`/`video_token_id`, ~19 GB

The VL variant has hybrid attention (`linear_attention` + `full_attention` layers) and a vision encoder. For text-only fine-tuning, prefer the text model — it's half the size and all parameters contribute to text quality. VL model works but wastes VRAM on the unused vision encoder.

See `references/qwen3.5-finetuning.md` → "Qwen3.5-VL-9B vs Qwen3.5-9B" for full details.

## Estimated Training Throughput

On RTX 4070 Ti Super (16GB), Qwen3.5-9B, QLoRA 4-bit, seq=2048:
- Batch size 2, grad accum 4 → effective batch 8
- ~30-60 min for 500-1000 samples, 3 epochs
- ~1-2 tokens/sec/GPU (depends on sequence packing)
