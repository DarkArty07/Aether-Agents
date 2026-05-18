# Hermes Auxiliary Models Configuration Reference

Auxiliary models handle side tasks: vision, compression, web extraction, STT, TTS, delegation, and session search. Each has its own provider + model pair so you can mix providers.

## Current Config Check

```bash
# View full config including auxiliary section
hermes config | grep -A5 "auxiliary\|vision\|compression\|web_extract"

# Or edit directly
hermes config edit
# Look for the `auxiliary:` section
```

## Auxiliary Section in config.yaml

```yaml
auxiliary:
  vision:
    provider: auto        # auto | openrouter | google | anthropic | openai | custom
    model: ''             # e.g. "google/gemini-2.5-flash", "openai/gpt-4o"
    base_url: ''          # custom endpoint
    api_key: ''           # or use env var reference: ${GOOGLE_API_KEY}
    timeout: 120
    extra_body: {}
    download_timeout: 30
  web_extract:
    provider: auto
    model: ''
    base_url: ''
    api_key: ''
    timeout: 360
    extra_body: {}
  compression:
    provider: auto
    model: ''
    base_url: ''
    api_key: ''
    # delegation:
  #   provider: auto
  #   model: ''          # e.g. "qwen3.6-plus"
  #   base_url: ''
  #   api_key: ''
  # stt:
  #   provider: local    # local | groq | openai | mistral
  #   local:
  #     model: base      # tiny | base | small | medium | large-v3 | turbo
  # tts:
  #   provider: edge     # edge | elevenlabs | openai | minimax | mistral | neutts
```

## Quick Setup Commands

```bash
# Vision — most common auxiliary to configure
hermes config set auxiliary.vision.provider google
hermes config set auxiliary.vision.model gemini-2.5-flash
# Or with OpenRouter
hermes config set auxiliary.vision.provider openrouter
hermes config set auxiliary.vision.model google/gemini-2.5-flash

# Using env var reference in config.yaml for API keys
# In config.yaml: api_key: ${GOOGLE_API_KEY}
# In .env: GOOGLE_API_KEY=AIza...
```

## Provider/Model Pairs for Vision

| Provider | Model | API Key Env Var | Notes |
|----------|-------|-----------------|-------|
| google | gemini-2.5-flash | GOOGLE_API_KEY or GEMINI_API_KEY | Free tier, excellent vision |
| google | gemini-2.5-pro | Same | Better quality, paid |
| openrouter | google/gemini-2.5-flash | OPENROUTER_API_KEY | Via OpenRouter |
| openrouter | openai/gpt-4o | OPENROUTER_API_KEY | Strong vision |
| openai | gpt-4o | OPENAI_API_KEY | Direct |
| anthropic | claude-sonnet-4 | ANTHROPIC_API_KEY | Direct |
| opencode-go | kimi-k2.5 | OPENCODE_GO_API_KEY | **Best vision value on Go plan**. Native multimodal (image+video). Chat completions format |
| opencode-go | qwen3.6-plus | OPENCODE_GO_API_KEY | Vision+video. 1M ctx. Uses @ai-sdk/alibaba format |
| opencode-go | qwen3.5-plus | OPENCODE_GO_API_KEY | Vision+video. 1M ctx. More requests/mo than 3.6 |
| opencode-go | mimo-v2-omni | OPENCODE_GO_API_KEY | Vision+video+audio. Most complete multimodal on Go |
| opencode-go | minimax-m2.7 | OPENCODE_GO_API_KEY | Vision+video+audio. Uses messages (Anthropic) format |
| opencode-go | minimax-m2.5 | OPENCODE_GO_API_KEY | Vision+video. More requests/mo than M2.7 |
| z.ai | glm-4v | GLM_API_KEY | ZhipuAI vision model, mixed results |

## OpenCode Go Full Model Reference

All models below share the same endpoint (`https://opencode.ai/zen/go/v1`) and API key (OPENCODE_GO_API_KEY or GLM_API_KEY).

### Choosing Auxiliary Models — Key Principle

**Vision tasks need a multimodal model. Text-only tasks (web_extract, compression, session_search) should use the cheapest high-throughput text-only model.** This maximizes your Go plan budget by not wasting multimodal model quota on tasks that don't process images.

- **vision**: Must be multimodal. Use qwen3.6-plus or kimi-k2.5.
- **web_extract**: Extracts text from web pages. Text-only task. Use deepseek-v4-flash (31,650 req/5h) or qwen3.5-plus (10,200 req/5h).
- **compression**: Summarizes context. Text-only task. Use deepseek-v4-flash or qwen3.5-plus.
- **delegation**: Subagent tasks. Text-only in most cases. Use qwen3.6-plus or kimi-k2.5 for coding quality.

### Multimodal Models (Support Vision)

| Model | ID | Vision | Video | Audio | Context | API Format | Requests/5h | Requests/mo |
|-------|----|--------|-------|-------|---------|------------|-------------|-------------|
| Kimi K2.5 | kimi-k2.5 | YES | YES | — | 128K+ | chat/completions | 1,850 | 9,250 |
| Kimi K2.6 | kimi-k2.6 | YES | YES | — | — | chat/completions | 1,150 | 5,750 |
| MiMo-V2-Omni | mimo-v2-omni | YES | YES | YES | 262K | chat/completions | 2,150 | 10,900 |
| Qwen3.6 Plus | qwen3.6-plus | YES | YES | — | 1M | ai-sdk/alibaba | 3,300 | 16,300 |
| Qwen3.5 Plus | qwen3.5-plus | YES | YES | — | 1M | ai-sdk/alibaba | 10,200 | 50,500 |
| MiniMax M2.7 | minimax-m2.7 | YES | YES | YES | 197K | messages (Anthropic) | 3,400 | 17,000 |
| MiniMax M2.5 | minimax-m2.5 | YES | YES | — | 197K | messages (Anthropic) | 6,300 | 31,800 |

### Text-Only Models (NO Vision)

| Model | ID | Context | Requests/5h | Requests/mo | Notes |
|-------|----|---------|-------------|-------------|-------|
| GLM-5.1 | glm-5.1 | 200K | 880 | 4,300 | Flagship coding/reasoning |
| GLM-5 | glm-5 | 200K | 1,150 | 5,750 | Previous flagship |
| MiMo-V2-Pro | mimo-v2-pro | 1M | 1,290 | 6,450 | Reasoning/coding only |
| MiMo-V2.5-Pro | mimo-v2.5-pro | 1M | 1,290 | 6,450 | Latest MiMo reasoning model |
| MiMo-V2.5 (≤256K) | mimo-v2.5 | 256K | 2,150 | 10,900 | Smaller context variant |
| DeepSeek V4 Pro | deepseek-v4-pro | 1M | 3,450 | 17,150 | Text ONLY. Not multimodal |
| DeepSeek V4 Flash | deepseek-v4-flash | 1M | 31,650 | 158,150 | Text ONLY. Best for cheap aux tasks |

### Choosing a Vision Model on OpenCode Go

- **Best overall**: kimi-k2.5 — native multimodal, strong coding+vision, chat/completions format, good value
- **Best context**: qwen3.6-plus — 1M context window, strong vision
- **Most multimodal**: mimo-v2-omni — audio+video+image in a single model
- **Most requests**: qwen3.5-plus — 10,200 requests/5h for high-volume use
- **Best for audio+vision**: mimo-v2-omni or minimax-m2.7 — both support audio input

### Configuring OpenCode Go Auxiliary Models

Two recommended setups depending on priorities:

**Option A — Value-optimized (recommended):** Uses deepseek-v4-flash for text-only tasks (31,650 req/5h, practically unlimited) and a vision model only for vision:

```yaml
# In config.yaml — all use the same endpoint and key
auxiliary:
  vision:
    provider: opencode-go
    model: qwen3.6-plus          # Multimodal (vision+video), 1M ctx
    base_url: https://opencode.ai/zen/go/v1
    api_key: ${OPENCODE_GO_API_KEY}
    timeout: 120
    extra_body: {}
    download_timeout: 30
  web_extract:
    provider: opencode-go
    model: deepseek-v4-flash     # Text-only, 31,650 req/5h — nearly unlimited
    base_url: https://opencode.ai/zen/go/v1
    api_key: ${OPENCODE_GO_API_KEY}
    timeout: 360
    extra_body: {}
  compression:
    provider: opencode-go
    model: deepseek-v4-flash     # Text-only, cheap summarization at scale
    base_url: https://opencode.ai/zen/go/v1
    api_key: ${OPENCODE_GO_API_KEY}
    timeout: 120
    extra_body: {}
```

Rationale:
- **vision**: qwen3.6-plus for strong multimodal understanding (vision+video)
- **web_extract**: deepseek-v4-flash — text extraction is a text-only task, and flash gives 31,650 req/5h vs 10,200 for qwen3.5-plus
- **compression**: deepseek-v4-flash — context summarization is text-only, high volume at near-zero cost
- **Key insight**: web_extract and compression never need vision. Use a text-only high-throughput model for these tasks, and reserve the multimodal model budget for actual vision.

**Option B — Single-model simplicity:** Uses qwen3.5-plus for all auxiliary tasks:

```yaml
auxiliary:
  vision:
    provider: opencode-go
    model: qwen3.6-plus
    base_url: https://opencode.ai/zen/go/v1
    api_key: ${OPENCODE_GO_API_KEY}
  web_extract:
    provider: opencode-go
    model: qwen3.5-plus
    base_url: https://opencode.ai/zen/go/v1
    api_key: ${OPENCODE_GO_API_KEY}
  compression:
    provider: opencode-go
    model: qwen3.5-plus
    base_url: https://opencode.ai/zen/go/v1
    api_key: ${OPENCODE_GO_API_KEY}
```

**\*Note:\*** MiniMax M2.7/M2.5 use the Anthropic `messages` format, NOT `chat/completions`. This may cause issues if the Hermes auxiliary model handler expects OpenAI format. Test before relying on these for auxiliary tasks.

## Common Pitfalls

### 0. `hermes config set` converts string "off" to boolean false
`hermes config set approvals.mode off` writes `mode: false` in YAML (a boolean) instead of `mode: 'off'` (the string Hermes expects). This silently breaks the approvals configuration — Hermes treats `false` differently from the string `'off'`. **Fix:** manually edit config.yaml and write `mode: 'off'` (with quotes), or use `hermes config set` and then verify with `grep`. This pitfall affects any YAML value that YAML interprets as boolean/null: `off`, `on`, `yes`, `no`, `true`, `false`, `null`, `~`.

### 0a. WSL faster-whisper falls back to CPU (libcublas.so.12 missing)
On WSL2 without CUDA toolkit installed, CTranslate2 detects the GPU (`get_cuda_device_count() = 1`) and loads the model with `device='auto'` → CUDA, but **transcription fails at runtime** with `RuntimeError: Library libcublas.so.12 is not found or cannot be loaded`. Hermes's `_load_local_whisper_model()` catches this and falls back to `device='cpu'`, `compute_type='int8'`. The model works but is significantly slower than GPU.

**Diagnosis:**
```bash
# Quick check — CTranslate2 shows CUDA device=1 but dlopen fails at first transcribe()
# The model LOADS successfully with device='auto' (no error at load time!)
# But transcribe() crashes with RuntimeError: Library libcublas.so.12 is not found
python3 -c "
from faster_whisper import WhisperModel
m = WhisperModel('base', device='auto', compute_type='auto')
print('Loaded OK')  # This prints OK even if CUDA libs are missing!
"
# Real test: create a silent WAV and transcribe it. RuntimeError = missing CUDA libs.
```

**Fix (recommended — pip CUDA runtime libs):**
This is the most reliable fix for WSL. Install the CUDA runtime libraries as pip packages into Hermes's venv, then configure LD_LIBRARY_PATH so CTranslate2 finds them at runtime. This avoids needing sudo, system-wide packages, or Windows CUDA interop — which often doesn't expose libcublas anyway.

```bash
# 1. Install CUDA runtime libs via pip into Hermes's venv
VENVBIN=/home/prometeo/.hermes/hermes-agent/venv/bin/python3
$VENVBIN -m pip install nvidia-cublas-cu12 nvidia-cudnn-cu12 nvidia-cufft-cu12 \
  nvidia-curand-cu12 nvidia-cusolver-cu12 nvidia-cusparse-cu12 \
  nvidia-cuda-runtime-cu12 nvidia-cuda-nvrtc-cu12 nvidia-nvjitlink-cu12

# 2. Add LD_LIBRARY_PATH to Hermes profile .env (so the daemon picks it up on restart)
#    Adjust the site-packages path for your Python version if different
NVIDIA_LIBS="/home/prometeo/.hermes/hermes-agent/venv/lib/python3.11/site-packages"
cat >> ~/.hermes/profiles/hermes/.env << 'ENVEOF'
# CUDA runtime libs for faster-whisper GPU (ctranslate2)
LD_LIBRARY_PATH=/home/prometeo/.hermes/hermes-agent/venv/lib/python3.11/site-packages/nvidia/cublas/lib:/home/prometeo/.hermes/hermes-agent/venv/lib/python3.11/site-packages/nvidia/cudnn/lib:/home/prometeo/.hermes/hermes-agent/venv/lib/python3.11/site-packages/nvidia/cufft/lib:/home/prometeo/.hermes/hermes-agent/venv/lib/python3.11/site-packages/nvidia/curand/lib:/home/prometeo/.hermes/hermes-agent/venv/lib/python3.11/site-packages/nvidia/cusolver/lib:/home/prometeo/.hermes/hermes-agent/venv/lib/python3.11/site-packages/nvidia/cusparse/lib:/home/prometeo/.hermes/hermes-agent/venv/lib/python3.11/site-packages/nvidia/cuda_runtime/lib:/home/prometeo/.hermes/hermes-agent/venv/lib/python3.11/site-packages/nvidia/cuda_nvrtc/lib:/home/prometeo/.hermes/hermes-agent/venv/lib/python3.11/site-packages/nvidia/nvjitlink/lib:/usr/lib/wsl/lib:${LD_LIBRARY_PATH}
ENVEOF

# 3. Also add to ~/.bashrc for interactive shells (so hermes CLI picks it up)
#    Same LD_LIBRARY_PATH line but with shell variable expansion

# 4. Verify GPU transcription works
export LD_LIBRARY_PATH="..." # paste from the .env line above
$VENVBIN -c "
from faster_whisper import WhisperModel
import time, tempfile, wave, struct, os
m = WhisperModel('medium', device='auto', compute_type='auto')
with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as f: tmp = f.name
with wave.open(tmp, 'w') as w:
    w.setnchannels(1); w.setsampwidth(2); w.setframerate(16000)
    for i in range(8000): w.writeframes(struct.pack('<h', 0))
segments, info = m.transcribe(tmp, language='es')
list(segments)
os.unlink(tmp)
print('GPU TRANSCRIPTION OK')
"
```

**Important:** Hermes reads `.env` via python-dotenv AFTER process start. But `LD_LIBRARY_PATH` must be set BEFORE the process starts for `dlopen()` to find CUDA libs. So the `.bashrc` export is critical for CLI sessions, and for the gateway daemon you may need to set it in the systemd service file or restart the gateway from a shell that has the variable.

**Alternative fix options (less reliable):**
1. **Enable mirrored networking + WSL CUDA interop** — `.wslconfig` with `networkingMode=mirrored` + `wsl --shutdown` + restart. In theory, Windows CUDA libs become available at `/usr/lib/wsl/lib/`. In practice, libcublas is often still missing — the pip approach above is more reliable.
2. **Install CUDA toolkit in WSL** — `sudo apt install libcublas12 libcudnn9-cuda12`. May not have packages for CUDA 13.x; the pip approach handles version matching automatically.
3. **Accept CPU mode** — `medium` model on CPU with int8 is still usable for short voice messages; ~10-30s for a 1-min clip. Set `stt.local.model` to `small` or `base` for faster CPU transcription.

### 0b. GLM-5.1 reasoning_effort is NOT applicable via OpenCode Go
GLM-5.1 has native thinking mode (`thinking: { "type": "enabled" }`) enabled by default. It does NOT support `reasoning_effort` levels like OpenAI models. When using GLM-5.1 through OpenCode Go with `chat_completions` API:
- `delegation.reasoning_effort: ''` (empty/default) → GLM-5.1 thinks deeply by default ✅
- `delegation.reasoning_effort: 'high'` → likely ignored or passed as an unsupported parameter ⚠️
- `delegation.reasoning_effort: 'none'` → might not map to GLM's `thinking: { "type": "disabled" }` ⚠️

**Recommendation:** Leave `reasoning_effort` empty for GLM-5.1. The model already uses deep thinking by default. Only configure `reasoning_effort` for models that support it (Claude, o1/o3, DeepSeek R1).

### Configuring multiple auxiliary models at once
When setting auxiliary models (session_search, skills_hub, title_generation, approval, mcp, curator, flush_memories), each needs four fields configured together as a unit. Use `hermes config set` for each, or edit config.yaml directly. The full set for OpenCode Go:

**CRITICAL: Use `${OPENCODE_GO_API_KEY}`, not `${GLM_API_KEY}`!** The `GLM_API_KEY` is for Z.AI's direct API (`api.z.ai`) only. It returns HTTP 401 on the OpenCode Go endpoint (`opencode.ai/zen/go/v1`). Always use `${OPENCODE_GO_API_KEY}` for OpenCode Go auxiliary models.
```bash
for AUX in session_search skills_hub title_generation approval mcp curator flush_memories; do
  hermes config set auxiliary.$AUX.provider opencode-go
  hermes config set auxiliary.$AUX.model deepseek-v4-flash  # or deepseek-v4-pro
  hermes config set auxiliary.$AUX.base_url https://opencode.ai/zen/go/v1
  hermes config set auxiliary.$AUX.api_key '${OPENCODE_GO_API_KEY}'  # NOT GLM_API_KEY!
done
```

**Quick verification:** After setting all auxiliary models, test the API key works:
```bash
source ~/.hermes/profiles/hermes/.env  # or wherever your .env is
curl -s -o /dev/null -w "%{http_code}" \
  -H "Authorization: Bearer $OPENCODE_GO_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"model":"deepseek-v4-flash","messages":[{"role":"user","content":"hi"}],"max_tokens":5}' \
  https://opencode.ai/zen/go/v1/chat/completions
# Expected: 200 (not 401)
```

### What the Curator does
The Curator (`auxiliary.curator`) runs automated memory maintenance periodically (default: every 7 days, `curator.interval_hours: 168`). It:
1. Detects stale memories (>30 days unused)
2. Archives old entries (>90 days)
3. Consolidates duplicate/redundant memories into single entries
4. Prunes irrelevant content to keep MEMORY.md within limits
It runs when the system is idle (`curator.min_idle_hours: 2`). It uses the configured auxiliary model — a cheap model like deepseek-v4-flash is ideal since it's just text summarization/deduplication.

### 1. Vision silent failure
If `auxiliary.vision.provider` is "auto" and no multimodal-capable provider has an API key, `vision_analyze` tool may not appear or will fail silently. **Fix:** explicitly set provider and model.

### 2. API key in wrong place
`hermes config set auxiliary.vision.api_key ...` puts it in config.yaml. For secrets, prefer `.env` + `${VAR}` references.

### 3. Model format mismatch
When using OpenRouter, model names must include provider prefix (e.g., `google/gemini-2.5-flash`). When using a direct provider, omit the prefix (just `gemini-2.5-flash`). For opencode-go, use plain model IDs (e.g., `qwen3.6-plus`, not `opencode-go/qwen3.6-plus`).

### 4. Platform toolset differences
The `vision` toolset must be enabled for the current platform. Check with `hermes tools list` and enable with `hermes tools enable vision` if needed. Changes require `/reset` or session restart.

### 5. CHECK ALL MODELS WHEN RESEARCHING VISION CAPABILITIES
When a user asks "which models support vision" or "configure vision", **check every model in their plan**, not just the obvious or well-known ones. Several counter-intuitive cases:
- **DeepSeek V4 Pro AND V4 Flash are text-only.** Despite some blog posts and marketing material claiming "multimodal native" or "understands images," the actual API release is **text input and output only**. The "multimodal" claims refer to planned future capabilities or self-hosted model weights — NOT the API you access through OpenCode Go or the DeepSeek API. Do NOT configure these for vision.
- **GLM-5 and GLM-5.1 are text-only.** ZhipuAI has separate vision models (GLM-4V series, GLM-5V-Turbo) not available on the Go plan.
- **Kimi K2.6 IS multimodal** (vision+video). Per the OpenCode Go docs updated May 2026, K2.6 supports image and video input natively. It is NOT text-only — earlier assumptions that K2.6 was text-only were incorrect.
- **MiMo-V2-Pro and MiMo-V2.5-Pro are text-only.** Only the "Omni" variant (MiMo-V2-Omni) has multimodal capabilities.

### 6. MiniMax format difference
MiniMax M2.7 and M2.5 use Anthropic's `/v1/messages` format, NOT OpenAI's `/v1/chat/completions`. If Hermes auxiliary model handler sends OpenAI-format requests to these models, it may fail. Prefer models that use `chat/completions` format for auxiliary tasks.

### 7. DeepSeek V4 Flash for text-only auxiliary tasks
DeepSeek V4 Flash (deepseek-v4-flash) has 31,650 requests per 5 hours on the Go plan — an order of magnitude more than any other model. Since web_extract and compression are text-only tasks, DeepSeek V4 Flash is the best choice for them. Do NOT use it for vision (it has no vision capability).

### 8. Auxiliary tasks fail with HTTP 401 when using OpenCode Go as main provider

When your main model uses OpenCode Go (`model.base_url: https://opencode.ai/zen/go/v1`) and auxiliary tasks are left on `provider: "auto"`, the auto-detection chain tries OpenRouter **first**. If `OPENROUTER_API_KEY` is not set in `.env`, the request reaches OpenRouter's API and returns `HTTP 401: Invalid API key`. This produces visible errors like:

```
Auxiliary title generation failed: HTTP 401: Invalid API key
```

**Root cause:** The `provider: "auto"` resolution chain for text auxiliary tasks is: `OpenRouter → Nous Portal → Custom endpoint → Codex OAuth → API-key providers → give up`. It does NOT check whether you have an API key for OpenRouter before attempting the call. If your main model routes through OpenCode Go (custom endpoint), "auto" never reaches your Go endpoint for these tasks — it tries OpenRouter first and fails.

**Fix:** Explicitly set each auxiliary task's provider and model instead of relying on "auto":

```bash
# Set all text-only auxiliary tasks to opencode-go with a cheap model
for slot in compression web_extract session_search skills_hub title_generation approval mcp; do\n  hermes config set auxiliary.$slot.provider opencode-go\n  hermes config set auxiliary.$slot.model deepseek-v4-flash\n  hermes config set auxiliary.$slot.base_url https://opencode.ai/zen/go/v1\n  hermes config set auxiliary.$slot.api_key '${OPENCODE_GO_API_KEY}'\ndone

# Vision needs a multimodal model
hermes config set auxiliary.vision.provider opencode-go
hermes config set auxiliary.vision.model qwen3.6-plus
hermes config set auxiliary.vision.base_url https://opencode.ai/zen/go/v1
hermes config set auxiliary.vision.api_key '${OPENCODE_GO_API_KEY}'
```

This is also more cost-efficient: DeepSeek V4 Flash has 31,650 req/5h vs whatever OpenRouter charges per request.

### 8a. Delegation api_key hardcoded instead of env var reference

When configuring delegation via `hermes config set`, the `api_key` parameter writes the raw key value directly into `config.yaml` (e.g., `api_key: sk-0UA...8W97`). This is a security risk (key in plaintext in config) and breaks env var rotation. Always use the `${OPENCODE_GO_API_KEY}` reference instead:

```bash
# BUG: hermes config set writes the raw key into config.yaml
hermes config set delegation.api_key sk-0UA...8W97   # WRONG — hardcoded key

# FIX: Edit config.yaml directly to use env var reference
# delegation:
#   api_key: ${OPENCODE_GO_API_KEY}
```

After any `hermes config set delegation.api_key` call, verify the result with `grep api_key config.yaml` and replace any hardcoded keys with `${OPENCODE_GO_API_KEY}` references.

### 9. WSL gateway systemd service missing LD_LIBRARY_PATH for CUDA

When faster-whisper is configured for GPU on WSL, the `LD_LIBRARY_PATH` must be set **before** the process starts (not just in `.env`, which is read via python-dotenv after startup). The systemd user service for the Hermes gateway must include the CUDA library paths:

```bash
# Check current gateway service
cat ~/.config/systemd/user/hermes-gateway-hermes.service

# Add LD_LIBRARY_PATH if missing
VENV_LIB=~/.hermes/hermes-agent/venv/lib/python3.11/site-packages
NVIDIA_PATH="${VENV_LIB}/nvidia/cublas/lib:${VENV_LIB}/nvidia/cudnn/lib:${VENV_LIB}/nvidia/cufft/lib:${VENV_LIB}/nvidia/curand/lib:${VENV_LIB}/nvidia/cusolver/lib:${VENV_LIB}/nvidia/cusparse/lib:${VENV_LIB}/nvidia/cuda_runtime/lib:${VENV_LIB}/nvidia/cuda_nvrtc/lib:${VENV_LIB}/nvidia/nvjitlink/lib:/usr/lib/wsl/lib"

# Add Environment line after [Service]
sed -i "/^\[Service\]$/a Environment=\"LD_LIBRARY_PATH=${NVIDIA_PATH}\"" \
  ~/.config/systemd/user/hermes-gateway-hermes.service

systemctl --user daemon-reload
hermes gateway restart
```

Also add `LD_LIBRARY_PATH` to `~/.bashrc` for CLI sessions. After adding, restart the gateway for changes to take effect.

### 10. STT language configuration for non-English users

Setting `stt.local.language` to the user's primary language (e.g., `'es'` for Spanish) improves transcription accuracy compared to `''` (auto-detect). Auto-detect adds latency and can misidentify short utterances. For users who primarily speak one language:

```bash
hermes config set stt.local.language es    # Spanish
hermes config set stt.local.language fr    # French
hermes config set stt.local.language de    # German
# etc.
```

## "auto" Provider Behavior

When `provider: auto` (default), Hermes tries:
1. The main model's provider (if it supports multimodal)
2. OpenRouter (if OPENROUTER_API_KEY is set)
3. Falls back silently — vision tools simply won't appear or will fail

**Important:** For TEXT auxiliary tasks (compression, web_extract, title_generation, etc.), the chain is: `OpenRouter → Nous Portal → Custom endpoint → Codex OAuth → API-key providers → give up`. If `OPENROUTER_API_KEY` is not set but OpenRouter is tried first, you get HTTP 401 — not a silent fallback. Always explicitly set auxiliary providers when using a custom endpoint as your main model.

If vision is not working, check:
```bash
hermes config | grep -i "vision\|auxiliary"
hermes tools list | grep vision
```

If `vision_analyze` tool is missing, either:
- No multimodal model is configured, OR
- The `vision` toolset is disabled for the current platform

## Memory Configuration

Hermes has built-in persistent memory (MEMORY.md + USER.md) plus optional external providers for deeper recall.

### Built-in Memory

```yaml
# In config.yaml
memory:
  memory_enabled: true           # Agent's personal notes
  user_profile_enabled: true      # User profile
  memory_char_limit: 2200         # ~800 tokens
  user_char_limit: 1375           # ~500 tokens
  provider: ''                    # External provider (empty = built-in only)
```

### External Memory Providers

```bash
hermes memory status   # Check current provider
hermes memory setup    # Interactive picker
hermes memory off      # Disable external provider
```

| Provider | Type | Key Feature | Requires | Best For |
|----------|------|-------------|----------|----------|
| **Mem0** | API/local | Auto fact extraction + semantic search | API key or local (ChromaDB) | Agents that learn from user over time |
| **Holographic** | Local | Local knowledge graph | Nothing (zero config) | Privacy-first, no external deps |
| **Honcho** | API/local | Cross-session user modeling, dialectic reasoning | API key or self-hosted | Multi-agent context sharing |
| **Hindsight** | API/local | Search past sessions by topic | API key or local | Remembering what happened in old conversations |
| **OpenViking** | API/local | Vector database memory | API key or local | High-performance semantic recall |
| **ByteRover** | API | Cloud semantic search | API key | Simple managed memory |
| **RetainDB** | API/local | Structured persistent storage | API key or local | Structured data persistence |
| **Supermemory** | API | Unified multi-agent memory | API key | Multiple agents sharing memory |

### Choosing a Memory Provider

Only **one external provider** can be active at a time (`memory.provider` in config.yaml). Built-in MEMORY.md/USER.md always runs alongside it.

**Decision guide by use case:**

| If you want... | Choose... | Why |
|----------------|-----------|-----|
| Cero config, cero dependencies, max privacy | **Holographic** | SQLite only, no LLM/embeddings/API needed. FTS5 search, trust scoring. Simplest setup. |
| Hands-off auto extraction, set-and-forget | **Mem0** | Pre-installed, auto-extracts facts, semantic search. Needs Qdrant + LLM + embeddings for local. |
| Structured navigation, filesystem hierarchy | **OpenViking** | 6 memory categories, tiered retrieval (abstract/overview/full), URL/doc ingestion. Needs server + LLM + embeddings. |
| Knowledge graph, cross-session connections, `reflect` reasoning | **Hindsight** ★ | Knowledge graph connects facts across sessions. `reflect` synthesizes insights from multiple memories. Stale detection. Best for programming/long sessions. |
| Deep user modeling, multi-agent user alignment | **Honcho** | Dialectic reasoning about the user. 5 tools. Best for multi-agent setups sharing user context. Needs PostgreSQL + Redis + LLM + embeddings. |

**★ Recommendation for multi-agent orchestration:** **Honcho**. Provides dialectic reasoning about users and peers, structured conclusions (`honcho_conclude`), and cross-session user modeling. 5 tools: `honcho_profile`, `honcho_search`, `honcho_context`, `honcho_reasoning`, `honcho_conclude`. Self-hosted via Docker (PostgreSQL + Redis). See `mlops/honcho` skill for setup. Also see the detailed Hindsight configuration section below.

### Recommended: Hindsight (for programming/long sessions)

Hindsight is recommended for users who prioritize quality over cost and work on long programming sessions across multiple conversations. Key advantages:
1. **Knowledge graph** — connects decisions and facts across sessions (e.g., "changed ORM from X to Y" + "bug with SQLAlchemy" → links them)
2. **`reflect` tool** — synthesizes answers from stored memories instead of just returning raw facts
3. **Stale detection** — marks observations as outdated and verifies against current facts
4. **Three retrieval levels** — mental models (curated summaries), observations (consolidated knowledge), raw facts (ground truth)
5. **Auto-inject** — relevant memories are automatically injected before each turn

```bash
# Setup
hermes memory setup   # Select "hindsight"

# Or manually:
hermes config set memory.provider hindsight
```

#### Hindsight Configuration (Local Embedded Mode)

For users with an OpenCode Go plan or local LLM (Ollama), Hindsight can run entirely locally with no additional API keys beyond your main LLM:

Config file: `~/.hermes/hindsight/config.json`

```json
{
  "mode": "local_embedded",
  "llm_provider": "openai_compatible",
  "llm_base_url": "https://opencode.ai/zen/go/v1",
  "llm_model": "deepseek-v4-flash",
  "bank_id": "hermes",
  "recall_budget": "high",
  "recall_prefetch_method": "reflect",
  "memory_mode": "hybrid",
  "auto_retain": true,
  "auto_recall": true,
  "retain_async": true,
  "retain_every_n_turns": 1
}
```

Key settings explained:
- `mode: local_embedded` — Hindsight runs a local PostgreSQL server automatically. No Docker or separate setup needed.
- `llm_provider: openai_compatible` — Use any OpenAI-compatible endpoint (OpenCode Go, Ollama, vLLM, etc.)
- `llm_model: deepseek-v4-flash` — Cheap, high-throughput model for Hindsight's internal LLM calls (fact extraction, reflect synthesis). Since Hindsight needs many LLM calls per turn, a cost-effective model is recommended.
- `recall_prefetch_method: reflect` — Inject an LLM-synthesized summary before each turn (slower but more coherent than raw facts). Use `"recall"` for faster, cheaper operation.
- `recall_budget: high` — Deep search across all memory levels. Use `"mid"` or `"low"` for faster/cheaper operation.
- `memory_mode: hybrid` — Auto-inject context AND expose tools (hindsight_retain, hindsight_recall, hindsight_reflect) to the LLM. Use `"context"` for inject-only or `"tools"` for tools-only.

For Ollama-based setups:
```json
{
  "mode": "local_embedded",
  "llm_provider": "ollama",
  "llm_model": "qwen3:8b",
  ...
}
```

#### Hindsight Critical Pitfall: `llm_provider` Valid Values

The `llm_provider` field in `~/.hermes/hindsight/config.json` and `~/.hindsight/profiles/<name>.env` does **NOT** accept `openai_compatible`. The daemon will fail with:

```
ValueError: Invalid LLM provider: openai_compatible. Must be one of: openai, groq, ollama, gemini, anthropic, lmstudio, llamacpp, vertexai, openai-codex, claude-code, mock, none, minimax, deepseek, litellm, bedrock, volcano, openrouter
```

**To use an OpenAI-compatible endpoint** (like OpenCode Go, vLLM, LiteLLM, etc.):
- Set `llm_provider: "openai"` (NOT `openai_compatible`)
- Set `llm_base_url` to your custom endpoint
- Set `llm_api_key` (or `HINDSIGHT_API_LLM_API_KEY` in the profile `.env`) to your API key

Example for OpenCode Go:
```json
{
  "llm_provider": "openai",
  "llm_base_url": "https://opencode.ai/zen/go/v1",
  "llm_api_key": "your-key-here",
  "llm_model": "deepseek-v4-flash"
}
```

The profile `.env` variables use the prefix `HINDSIGHT_API_`:
```bash
HINDSIGHT_API_LLM_PROVIDER=openai
HINDSIGHT_API_LLM_BASE_URL=https://opencode.ai/zen/go/v1
HINDSIGHT_API_LLM_API_KEY=your-key
HINDSIGHT_API_LLM_MODEL=deepseek-v4-flash
```

#### Hindsight Embedded Mode Installation

Hindsight in `local_embedded` mode runs its own PostgreSQL, embeddings model, and reranker locally — no Docker needed.

```bash
# 1. Install the packages
uv pip install --system --break-system-packages hindsight-client hindsight-embed

# 2. Create the profile
hindsight-embed configure \
  --profile hermes \
  --port 9100 \
  --env HINDSIGHT_API_LLM_PROVIDER=openai \
  --env HINDSIGHT_API_LLM_BASE_URL=https://opencode.ai/zen/go/v1 \
  --env HINDSIGHT_API_LLM_MODEL=deepseek-v4-flash

# 3. Edit the profile .env to add the API key
# The configure command may warn about env var naming — the correct prefix is HINDSIGHT_API_
# File: ~/.hindsight/profiles/hermes.env
echo 'HINDSIGHT_API_LLM_API_KEY=your-api-key-here' >> ~/.hindsight/profiles/hermes.env

# 4. Create config directory
mkdir -p ~/.hermes/hindsight

# 5. Create the config file
cat > ~/.hermes/hindsight/config.json << 'EOF'
{
  "mode": "local_embedded",
  "llm_provider": "openai",
  "llm_base_url": "https://opencode.ai/zen/go/v1",
  "llm_model": "deepseek-v4-flash",
  "bank_id": "hermes",
  "recall_budget": "high",
  "recall_prefetch_method": "reflect",
  "memory_mode": "hybrid",
  "auto_retain": true,
  "auto_recall": true,
  "retain_async": true,
  "retain_every_n_turns": 1
}
EOF

# 6. Set the Hermes config to use Hindsight
hermes config set memory.provider hindsight

# 7. Start the daemon
hindsight-embed -p hermes daemon start

# 8. Verify it's running
curl -s http://localhost:9100/health
# Expected: {"status":"healthy","database":"connected"}
```

**What Hindsight downloads automatically (local_embedded mode):**
- **Embeddings**: BAAI/bge-small-en-v1.5 (33M params, 384 dims, ~130MB) — runs on CPU, 2-5ms per text
- **Reranker**: cross-encoder/ms-marco-MiniLM-L-6-v2 (22.7M params, ~80MB) — runs on CPU, 5-10ms per batch
- **PostgreSQL**: Embedded instance, port 5433, stores vectors + knowledge graph

**First startup takes 1-2 minutes** to download models and initialize PostgreSQL. Subsequent starts are faster (~20s).

#### Hindsight's `reflect` Tool — How It Differs from `recall`

| Aspect | `recall` | `reflect` |
|--------|----------|-----------|
| **Output** | Raw memory facts | LLM-synthesized reasoned answer |
| **Processing** | Search only | Agentic loop (up to 10 iterations) |
| **Best for** | Getting context | Answering questions, forming insights |
| **Token usage** | Low | Higher (multiple LLM calls) |
| **Sources** | The result IS the sources | Sources cited separately with confidence |

When you call `hindsight_reflect("What patterns do I see in my debugging approach?")`, Hindsight:
1. Analyzes your question
2. Searches mental models (curated summaries) → observations (consolidated knowledge) → raw facts
3. If an observation is stale, verifies it against current facts
4. LLM reasons across all gathered evidence
5. Returns a synthesized answer with cited sources

#### Hindsight vs Other Providers — Feature Comparison

| Feature | Holographic | Mem0 | OpenViking | Hindsight | Honcho |
|---------|-------------|------|-----------|-----------|--------|
| Setup complexity | Zero | Medium | High | Medium | High |
| External deps | None | Qdrant + LLM + emb | Server + LLM + emb | Bundled PG + LLM + emb | PG + Redis + LLM + emb |
| Semantic search | No (FTS5 only) | Yes | Yes | Yes | Yes |
| Knowledge graph | No | No | No | **Yes** | No |
| `reflect` synthesis | No | No | No | **Yes** | Dialectic reasoning |
| Stale detection | No | No | No | **Yes** | No |
| Auto fact extraction | No | Yes | Yes | Yes | Yes |
| Tiered retrieval | No | No | Yes (abstract/overview/full) | Yes (mental models/observations/facts) | Yes (base layer/dialectic) |
| Local mode | Always | Yes (Qdrant) | Yes (Ollama) | Yes (embedded PG) | Yes (Docker/self-host) |
| Free tier | Yes | Yes (local) | Yes (AGPL) | Yes (local) | Yes (self-host) |
| Tools count | 2 | 3 | 5 | 3 | 5 |
| Best for | Privacy-first simplicity | Auto memory mgmt | Structured navigation | Programming / cross-session | Multi-agent user modeling |

### Memory Limits Are Tight

Default limits are 2,200 chars (MEMORY.md) and 1,375 chars (USER.md). These fill up fast. Options:
1. **Increase limits** in config.yaml — `memory_char_limit: 4000`, `user_char_limit: 2500`
2. **Add an external provider** — Provider storage has no effective limit on stored memories
3. **Both** — increase built-in limits AND add external provider for depth

### Important: Only One External Provider

The config only accepts one provider:
```yaml
memory:
  provider: hindsight   # Only ONE at a time: honcho, mem0, hindsight, holographic, etc.
```

Built-in MEMORY.md/USER.md always runs alongside the external provider. Use USER.md for explicit preferences the agent manages manually, and the external provider for automatic cross-session knowledge.

## Context Compression Tuning

Compression settings control how Hermes handles long conversations before they exceed the model's context window. Two systems operate independently:

1. **Gateway Session Hygiene** (85% threshold, not configurable) — safety net that runs before the agent processes a message in gateway sessions (Telegram, Discord, etc.)
2. **Agent ContextCompressor** (configurable threshold) — primary compression that runs inside the agent loop with accurate token counts

### How Compression Works

```
0K ───────── threshold ───────────────── context_length
     │              │                         │
  Head (intact)  Middle (summarized)    Tail (intact)
  system prompt   by auxiliary model     last N messages
  + first 3        → compressed summary   always preserved
```

### Default Config (good for general chat)

```yaml
compression:
  enabled: true
  threshold: 0.50           # Compress at 50% of context
  target_ratio: 0.20         # 20% of threshold budget → tail protection
  protect_last_n: 20         # Last 20 messages always preserved
  hygiene_hard_message_limit: 400  # Gateway safety net
```

### Orchestration-Optimized Config (recommended for multi-agent/delegation workflows)

When using `delegate_task`, `run_workflow`, or long coding sessions, each delegation generates 5-10+ messages. The defaults lose context too aggressively.

```yaml
compression:
  enabled: true
  threshold: 0.65           # Compress at 65% — later but with more precise summaries
  target_ratio: 0.30        # 30% of threshold → larger tail protection budget
  protect_last_n: 30        # Protect 30 messages (~3-5 full delegations)
  hygiene_hard_message_limit: 300  # Earlier safety net for gateway
```

**Why these values:**
- `threshold: 0.65` — With GLM-5.1 (128K context), compresses at ~83K tokens instead of ~64K. More context preserved, but when it compresses, the summary is shorter and more precise (summarizing ~58K instead of ~80K).
- `target_ratio: 0.30` — 30% of the threshold budget goes to preserving recent messages (25K tokens instead of 20K).
- `protect_last_n: 30` — Each delegation produces 5-10 messages. 30 protected messages ≈ 3-5 complete delegations intact.
- `hygiene_hard_message_limit: 300` — Gateway safety net triggers earlier for very long sessions.

### Context Engine (Pluggable)

The context engine is responsible for deciding when and how to compact. Configured via:

```yaml
context:
  engine: compressor    # default — built-in lossy summarization
  # engine: lcm        # alternative — lossless context management (requires plugin)
```

- **compressor** (default): Lossy compression — summarizes old messages via the auxiliary model. Best for limited context (128K).
- **lcm** (plugin): Lossless — stores and retrieves intelligently without summarizing. Best for very large contexts (1M+). Does not lose information but may use more tokens over time.

For 128K context models like GLM-5.1, stick with `compressor`. LCM makes more sense for Qwen3.6 (1M context) where you want to preserve everything.

## STT/TTS Configuration

### STT (Speech-to-Text)

```yaml
stt:
  enabled: true
  provider: local    # local | groq | openai | mistral
  local:
    model: medium    # tiny | base | small | medium | large-v3
    language: ''     # empty = auto-detect, or set 'es', 'en', etc.
```

Local STT uses faster-whisper (CTranslate2). Model sizes:

| Model | Size | VRAM needed | Speed | Accuracy |
|-------|------|-------------|-------|----------|
| tiny | ~150MB | ~1GB | Very fast | Low |
| base | ~250MB | ~1.5GB | Fast | Basic |
| small | ~500MB | ~2GB | Good | Decent |
| **medium** | ~1.5GB | ~5GB | Medium | Very good |
| large-v3 | ~3GB | ~10GB | Slow | Excellent |

**Recommendation for RTX 4070 Ti Super 16GB:** `medium` is the sweet spot — very good Spanish accuracy, still fast on GPU. `large-v3` is better but noticeably slower.

**WSL caveat:** On WSL2 without CUDA toolkit, faster-whisper falls back to CPU with int8 quantization. It still works but is slower. See Pitfall #0a above.

**GPU check:**
```bash
# Verify GPU is being used (not CPU fallback)
python3 -c "
from faster_whisper import WhisperModel
m = WhisperModel('base', device='auto', compute_type='auto')
print('Loaded OK')
" && echo "GPU OK" || echo "FELL BACK TO CPU"
```

### TTS (Text-to-Speech)

```yaml
tts:
  provider: edge    # edge (free) | elevenlabs | openai | minimax | mistral | neutts | piper
  edge:
    voice: es-MX-JorgeNeural    # Spanish (Mexico) male voice
```

**Voice toolset must be enabled separately:**
```bash
hermes tools enable tts    # Required for /voice on to work
```

Common voice commands: `/voice on` (voice-to-voice), `/voice tts` (always voice), `/voice off`.

**Edge TTS voices for Spanish:**
- Male: `es-MX-JorgeNeural`, `es-ES-AlvaroNeural`
- Female: `es-MX-DaliaNeural`, `es-ES-ElviraNeural`

### STT/TTS Model Download

STT models auto-download from Hugging Face on first use. For `medium` (~1.5GB), first transcription will take a few seconds extra for download. Set `HF_TOKEN` in `.env` for higher rate limits.

## Delegation and Orchestration

### Delegation Config

```yaml
delegation:
  model: deepseek-v4-flash       # Model for subagent tasks
  provider: opencode-go
  base_url: https://opencode.ai/zen/go/v1
  api_key: ${OPENCODE_GO_API_KEY}
  inherit_mcp_toolsets: true      # Subagents inherit parent's MCP servers
  max_iterations: 50             # Max tool-calling iterations per subagent
  child_timeout_seconds: 600      # Timeout per subagent
  max_spawn_depth: 2             # 1=flat, 2=orchestrator can delegate further
  max_concurrent_children: 5      # Parallel subagents
  orchestrator_enabled: true      # Enable run_workflow orchestration
  subagent_auto_approve: true    # Skip approval prompts for subagent commands
  reasoning_effort: ''            # Only applies to models with native reasoning (Claude, o1/o3)
```

**Key settings:**
- `max_spawn_depth: 1` — Subagents cannot delegate further. Use for simple tasks.
- `max_spawn_depth: 2` — Subagents can delegate to other subagents. Required for full Aether Agents orchestration (Hermes → Daimon → specialist).
- `subagent_auto_approve: true` — Eliminates approval prompts for every subagent command. Set `false` for security-sensitive environments.
- `reasoning_effort` — Leave empty for GLM-5.1 (thinking is on by default). See Pitfall #0b.

### Approvals

```yaml
approvals:
  mode: 'off'          # 'manual' (default) | 'smart' | 'off'
  timeout: 60          # Seconds before auto-deny
  cron_mode: deny      # Cron jobs always denied approval
  mcp_reload_confirm: true  # Confirm MCP server reloads
```

**`approvals.mode` values:**
- `manual` — Prompt before every destructive command (default, safe)
- `smart` — LLM decides: auto-approve low-risk, prompt for high-risk
- `off` — No approval prompts at all (convenient for autonomous agents, less safe)

**Pitfall:** `hermes config set approvals.mode off` writes `mode: false` (YAML boolean) instead of `mode: 'off'` (string). Always verify with `grep approvals config.yaml` after setting. See Pitfall #0.

## Timezone

```yaml
# In config.yaml
timezone: 'America/Mexico_City'   # IANA timezone string
# Common examples: 'America/New_York', 'Europe/Madrid', 'America/Bogota'
# Leave empty for server-local timezone
```

Set via: `hermes config set timezone 'America/Mexico_City'`

### 11. Profile path is NOT always ~/.hermes/

When using Hermes profiles (the `-p` flag, e.g., `hermes -p hermes`), all profile-specific files live in a separate directory tree, NOT in `~/.hermes/`. The exact location depends on how the profile was created:

```bash
# Check where YOUR profile actually lives
hermes config path    # e.g., ~/Aether-Agents/home/config.yaml

# The profile directory contains:
# config.yaml, .env, SOUL.md, memories/, skills/, sessions/, cron/, logs/, state.db

# Common mistake: editing ~/.hermes/config.yaml instead of the profile config
# This edits the DEFAULT profile, not the active one!
```

**Profile directory mapping:**
- Config/Env/SOUL.md/Memories/Skills/Sessions/Cron/Logs/State DB: `~/Aether-Agents/home/`
- Aether shared skills: `~/Aether-Agents/home/skills/`
- Installation/Venv: `~/.hermes/hermes-agent/` (shared, NOT in profile)
- Binary: `~/.hermes/hermes-agent/venv/bin/hermes`
- Systemd service: `~/.config/systemd/user/hermes-gateway-<profile>.service`

**Rule:** Always run `hermes config path` first to find the active profile directory before editing config files. The `.env` file is in the SAME directory as `config.yaml`, NOT in `~/.hermes/.env`.

This is especially important when:
- The user says "edit my config" — use the profile path, not ~/.hermes/
- Setting up CUDA LD_LIBRARY_PATH in .env — it goes in the profile .env, not ~/.hermes/.env
- Editing SOUL.md, USER.md, MEMORY.md — they're in the profile's memories/ directory
- The systemd service file — it's `hermes-gateway-<profile>.service`, where `<profile>` is the profile name

### 12. Gateway systemd service must include LD_LIBRARY_PATH for CUDA

This is covered in detail in Pitfall #9 and Pitfall #0a, but the key point: the systemd service for the gateway (`~/.config/systemd/user/hermes-gateway-<profile>.service`) does NOT inherit `.bashrc` or shell environment variables. If you add `LD_LIBRARY_PATH` to `.bashrc` or `.env`, the gateway still won't have it. You MUST add it as an `Environment=` line in the systemd service file.

## Env Var Substitution in config.yaml

Use `${VAR_NAME}` syntax (not `$VAR`):
```yaml
auxiliary:
  vision:
    api_key: ${GOOGLE_API_KEY}
    base_url: ${CUSTOM_VISION_URL}
```
Multiple references work: `url: "${HOST}:${PORT}"`
Undefined vars are kept verbatim as `${UNDEFINED_VAR}`.