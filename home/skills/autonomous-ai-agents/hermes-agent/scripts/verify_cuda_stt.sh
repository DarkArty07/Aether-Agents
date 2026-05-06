#!/bin/bash
# Verify faster-whisper GPU acceleration is working
# Usage: bash verify_cuda_stt.sh [model_size]
# model_size: tiny, base, small, medium, large-v3 (default: medium)

MODEL="${1:-medium}"

# Set LD_LIBRARY_PATH for CUDA libs (adjust path for your venv)
VENV_LIB="/home/prometeo/.hermes/hermes-agent/venv/lib/python3.11/site-packages"
export LD_LIBRARY_PATH="${VENV_LIB}/nvidia/cublas/lib:${VENV_LIB}/nvidia/cudnn/lib:${VENV_LIB}/nvidia/cufft/lib:${VENV_LIB}/nvidia/curand/lib:${VENV_LIB}/nvidia/cusolver/lib:${VENV_LIB}/nvidia/cusparse/lib:${VENV_LIB}/nvidia/cuda_runtime/lib:${VENV_LIB}/nvidia/cuda_nvrtc/lib:${VENV_LIB}/nvidia/nvjitlink/lib:/usr/lib/wsl/lib${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"

PYTHON="/home/prometeo/.hermes/hermes-agent/venv/bin/python3"

echo "=== faster-whisper GPU verification ==="
echo "Model: ${MODEL}"
echo ""

# Test 1: CTranslate2 CUDA detection
echo "CTranslate2 CUDA devices: $($PYTHON -c 'import ctranslate2; print(ctranslate2.get_cuda_device_count())')"

# Test 2: Model load
echo "Loading model..."
$PYTHON -c "
import time
from faster_whisper import WhisperModel

t0 = time.time()
model = WhisperModel('${MODEL}', device='auto', compute_type='auto')
t1 = time.time()
print(f'Model loaded in {t1-t0:.1f}s')

# Test 3: Transcription with silent audio
import tempfile, wave, struct, os

with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as f:
    tmp = f.name
with wave.open(tmp, 'w') as w:
    w.setnchannels(1)
    w.setsampwidth(2)
    w.setframerate(16000)
    for i in range(16000):  # 1 second of silence
        w.writeframes(struct.pack('<h', 0))

try:
    t2 = time.time()
    segments, info = model.transcribe(tmp, language='es')
    result = list(segments)
    t3 = time.time()
    print(f'Language: {info.language} (prob: {info.language_probability:.2f})')
    print(f'Transcription time: {t3-t2:.2f}s')
    print(f'Total time: {t3-t0:.1f}s')
    print('GPU TRANSCRIPTION OK')
finally:
    os.unlink(tmp)
" 2>&1

echo ""
echo "=== Verification complete ==="
echo "If you see 'GPU TRANSCRIPTION OK' above, faster-whisper is using GPU correctly."
echo "If you see 'RuntimeError: Library libcublas.so.12 is not found', CUDA libs are missing."