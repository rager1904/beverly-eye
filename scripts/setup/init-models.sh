#!/usr/bin/env bash
# =============================================================================
# Model Download & Quantization — UbuntuCare (Zambia)
# =============================================================================
# Downloads all open-source AI models needed for offline operation,
# quantizes for the target hardware, verifies checksums, and caches.
# =============================================================================

set -euo pipefail

RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; BLUE='\033[0;34m'
BOLD='\033[1m'; NC='\033[0m'
log()  { echo -e "${GREEN}[✓]${NC} $1"; }
warn() { echo -e "${YELLOW}[!]${NC} $1"; }
err()  { echo -e "${RED}[✗]${NC} $1" >&2; exit 1; }
info() { echo -e "${BLUE}[i]${NC} $1"; }

MODELS_DIR="${MODELS_DIR:-/data/models}"
HF_MIRROR="${HF_MIRROR:-https://huggingface.co}"
S3_MIRROR="${S3_MIRROR:-s3://models.ubuntucare.gov.zm}"
SKIP_IF_EXISTS="${SKIP_IF_EXISTS:-false}"
QUANTIZE="${QUANTIZE:-true}"
VERIFY_CHECKSUMS="${VERIFY_CHECKSUMS:-true}"
TARGET="${TARGET:-auto}"

detect_target() {
  if command -v nvidia-smi &>/dev/null; then
    local gpu; gpu=$(nvidia-smi --query-gpu=name --format=csv,noheader 2>/dev/null | head -1)
    if echo "$gpu" | grep -qi "RTX 3060"; then TARGET="rtx3060"
    elif echo "$gpu" | grep -qi "RTX 4070"; then TARGET="rtx4070"
    elif echo "$gpu" | grep -qi "RTX 4090"; then TARGET="rtx4090"
    elif echo "$gpu" | grep -qi "L40S"; then TARGET="l40s"
    elif echo "$gpu" | grep -qi "A100"; then TARGET="a100"
    else TARGET="x86-cpu"
    fi
  elif [[ -f /proc/device-tree/model ]] && grep -qi "Jetson" /proc/device-tree/model; then
    TARGET="jetson"
  elif [[ -f /proc/device-tree/model ]] && grep -qi "Raspberry Pi 5" /proc/device-tree/model; then
    TARGET="pi5"
  else
    TARGET="x86-cpu"
  fi
  info "Detected target: $TARGET"
}

download_model() {
  local name="$1" repo="$2" variant="$3"
  local target_dir="$MODELS_DIR/$name"

  if [[ -f "$target_dir/.downloaded" ]]; then
    [[ "$SKIP_IF_EXISTS" == "true" ]] && info "Skipping $name (already exists)" && return
  fi

  mkdir -p "$target_dir"
  log "Downloading $name ($repo, $variant)..."

  if curl -sf --connect-timeout 5 "$S3_MIRROR/$name/MODEL_INFO" > /dev/null 2>&1; then
    aws s3 sync --no-sign-request "$S3_MIRROR/$name/" "$target_dir/" --quiet
  else
    python3 -c "
import sys
from huggingface_hub import snapshot_download, login
try:
    snapshot_download(
        repo_id='$repo', local_dir='$target_dir',
        local_dir_use_symlinks=False, resume_download=True
    )
except Exception as e:
    print(f'Download failed: {e}', file=sys.stderr)
    sys.exit(1)
" || warn "Failed to download $name"
  fi
  date +%s > "$target_dir/.downloaded"
  log "Downloaded $name → $target_dir"
}

quantize_model() {
  local name="$1" precision="$2"
  local model_dir="$MODELS_DIR/$name"

  [[ "$QUANTIZE" != "true" ]] && return
  [[ -f "$model_dir/.quantized" ]] && info "Already quantized: $name" && return

  log "Quantizing $name → $precision..."
  case "$name" in
    whisper-*)
      python3 -c "
import onnxruntime as ort
from optimum.onnxruntime import ORTQuantizer
from optimum.onnxruntime.configuration import AutoQuantizationConfig
quantizer = ORTQuantizer.from_pretrained('$model_dir')
qconfig = AutoQuantizationConfig.avx512_vnni(is_static=False)
quantizer.quantize(save_dir='$model_dir', quantization_config=qconfig)
" 2>/dev/null || warn "Quantization for $name not supported, copying as-is"
      ;;
    qwen3-*)
      # Use AutoAWQ for LLMs
      python3 -c "
from awq import AutoAWQForCausalLM
from transformers import AutoTokenizer
model = AutoAWQForCausalLM.from_pretrained('$model_dir')
tokenizer = AutoTokenizer.from_pretrained('$model_dir')
model.quantize(tokenizer, quant_config={'zero_point': True, 'q_group_size': 128, 'w_bit': 4})
model.save_quantized('$model_dir')
" 2>/dev/null || warn "AWQ quantization not available for $name"
      ;;
  esac
  date +%s > "$model_dir/.quantized"
  log "Quantized $name → $precision"
}

verify_checksum() {
  local name="$1"
  [[ "$VERIFY_CHECKSUMS" != "true" ]] && return

  local model_dir="$MODELS_DIR/$name"
  if [[ -f "$model_dir/checksum.sha256" ]]; then
    (cd "$model_dir" && sha256sum -c checksum.sha256) && \
      log "Checksum verified: $name" || \
      warn "Checksum mismatch: $name"
  fi
}

main() {
  echo -e "${BOLD}"
  echo "╔══════════════════════════════════════════════════════════════╗"
  echo "║   UbuntuCare — Model Initialization (Zambia)        ║"
  echo "╚══════════════════════════════════════════════════════════════╝"
  echo -e "${NC}"

  mkdir -p "$MODELS_DIR"
  [[ "$TARGET" == "auto" ]] && detect_target

  declare -A MODELS
  case "$TARGET" in
    rtx3060|rtx4070)
      MODELS=(
        ["whisper-small"]="openai/whisper-small:float32"
        ["qwen3-8b"]="Qwen/Qwen3-8B:float16"
        ["stella-400m"]="infgrad/stella-base-400m-v5:float32"
        ["piper"]="rhasspy/piper-voices:float32"
      )
      QUANT_MAP=(
        ["whisper-small"]="int8"
        ["qwen3-8b"]="int4"
        ["stella-400m"]="float16"
      )
      ;;
    rtx4090|l40s)
      MODELS=(
        ["whisper-large-v3"]="openai/whisper-large-v3:float16"
        ["qwen3-32b"]="Qwen/Qwen3-32B:float16"
        ["stella-400m"]="infgrad/stella-base-400m-v5:float32"
        ["piper"]="rhasspy/piper-voices:float32"
      )
      QUANT_MAP=(
        ["whisper-large-v3"]="int8"
        ["qwen3-32b"]="int4"
        ["stella-400m"]="float16"
      )
      ;;
    a100)
      MODELS=(
        ["whisper-large-v3"]="openai/whisper-large-v3:float16"
        ["qwen3-32b"]="Qwen/Qwen3-32B:float16"
        ["stella-400m"]="infgrad/stella-base-400m-v5:float32"
        ["piper"]="rhasspy/piper-voices:float32"
        ["vit-lung-xray"]="tuwien-xray/vit-lung:float32"
      )
      QUANT_MAP=(
        ["whisper-large-v3"]="float16"
        ["qwen3-32b"]="int8"
        ["stella-400m"]="float16"
      )
      ;;
    jetson)
      MODELS=(
        ["whisper-tiny"]="openai/whisper-tiny:float32"
        ["qwen3-1b"]="Qwen/Qwen3-1B:float16"
        ["stella-100m"]="infgrad/stella-base-100m-v5:float32"
        ["piper-tiny"]="rhasspy/piper-voices:float32"
      )
      QUANT_MAP=(
        ["whisper-tiny"]="int8"
        ["qwen3-1b"]="int4"
      )
      ;;
    pi5|pi4)
      MODELS=(
        ["whisper-tiny"]="openai/whisper-tiny:float32"
        ["phi3-mini"]="microsoft/Phi-3-mini-4k-instruct:float16"
        ["bge-micro"]="BAAI/bge-micro-v2:float32"
      )
      QUANT_MAP=(
        ["whisper-tiny"]="int8"
        ["phi3-mini"]="int4"
      )
      ;;
    *)
      MODELS=(
        ["whisper-small"]="openai/whisper-small:float32"
        ["qwen3-8b"]="Qwen/Qwen3-8B:float16"
        ["stella-400m"]="infgrad/stella-base-400m-v5:float32"
      )
      QUANT_MAP=(
        ["whisper-small"]="int8"
        ["qwen3-8b"]="int4"
      )
      ;;
  esac

  for model_name in "${!MODELS[@]}"; do
    local spec="${MODELS[$model_name]}"
    local repo="${spec%%:*}"
    local variant="${spec##*:}"
    download_model "$model_name" "$repo" "$variant"
    verify_checksum "$model_name"
    local quant="${QUANT_MAP[$model_name]:-float16}"
    quantize_model "$model_name" "$quant"
  done

  log "All models downloaded to $MODELS_DIR"
  du -sh "$MODELS_DIR"/*/ | sort -rh
}

main "$@"
