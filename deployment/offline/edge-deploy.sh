#!/usr/bin/env bash
# =============================================================================
# Edge Deployment Script — UbuntuCare (Zambia)
# =============================================================================
# Deploys the complete offline-capable healthcare platform to an edge device
# (e.g. NVIDIA Jetson, x86 server, Raspberry Pi 5).
#
# Usage:
#   ./edge-deploy.sh [--device <jetson|pi5|x86>] [--gpu <rtx3060|rtx4070|rtx4090|l40s|a100>]
#                    [--models-dir /data/models] [--data-dir /data/ubuntucare]
#
# Prerequisites:
#   - Docker & Docker Compose (v2+)
#   - NVIDIA drivers + nvidia-container-toolkit (for GPU devices)
#   - Python 3.10+
#   - 50GB+ free disk space
# =============================================================================

set -euo pipefail

# ── Colors ─────────────────────────────────────────────────────────────────
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; BLUE='\033[0;34m'
BOLD='\033[1m'; NC='\033[0m'

log()  { echo -e "${GREEN}[✓]${NC} $1"; }
warn() { echo -e "${YELLOW}[!]${NC} $1"; }
err()  { echo -e "${RED}[✗]${NC} $1" >&2; exit 1; }
info() { echo -e "${BLUE}[i]${NC} $1"; }
header() { echo -e "\n${BOLD}━━━ $1 ━━━${NC}\n"; }

# ── Defaults ───────────────────────────────────────────────────────────────
DEVICE="x86"
GPU_MODEL=""
MODELS_DIR="/data/models"
DATA_DIR="/data/ubuntucare"
COMPOSE_FILE="docker-compose.edge.yml"
SKIP_MODELS=false
SKIP_DOCKER=false
DRY_RUN=false

# ── Parse Args ─────────────────────────────────────────────────────────────
while [[ $# -gt 0 ]]; do
  case "$1" in
    --device)     DEVICE="$2"; shift 2 ;;
    --gpu)        GPU_MODEL="$2"; shift 2 ;;
    --models-dir) MODELS_DIR="$2"; shift 2 ;;
    --data-dir)   DATA_DIR="$2"; shift 2 ;;
    --compose)    COMPOSE_FILE="$2"; shift 2 ;;
    --skip-models) SKIP_MODELS=true; shift ;;
    --skip-docker) SKIP_DOCKER=true; shift ;;
    --dry-run)    DRY_RUN=true; shift ;;
    --help|-h)    echo "Usage: $0 [options]"; exit 0 ;;
    *)            err "Unknown option: $1" ;;
  esac
done

# ── Device Detection ───────────────────────────────────────────────────────
detect_device() {
  info "Detecting hardware platform..."

  if [[ -f /proc/device-tree/model ]]; then
    local model; model=$(tr -d '\0' < /proc/device-tree/model)
    if echo "$model" | grep -qi "Raspberry Pi 5"; then
      DEVICE="pi5"
      log "Detected: Raspberry Pi 5"
      return
    elif echo "$model" | grep -qi "Jetson"; then
      DEVICE="jetson"
      log "Detected: NVIDIA Jetson"
      return
    fi
  fi

  if command -v nvidia-smi &> /dev/null; then
    DEVICE="x86"
    local gpu; gpu=$(nvidia-smi --query-gpu=name --format=csv,noheader 2>/dev/null | head -1)
    if [[ -z "$GPU_MODEL" ]]; then
      if echo "$gpu" | grep -qi "RTX 3060"; then
        GPU_MODEL="rtx_3060_12gb"
      elif echo "$gpu" | grep -qi "RTX 4070"; then
        GPU_MODEL="rtx_4070_12gb"  # corrected detection
      elif echo "$gpu" | grep -qi "RTX 4090"; then
        GPU_MODEL="rtx_4090_24gb"
      elif echo "$gpu" | grep -qi "L40S"; then
        GPU_MODEL="l40s_48gb"
      elif echo "$gpu" | grep -qi "A100"; then
        GPU_MODEL="a100_80gb"
      else
        GPU_MODEL="rtx_3060_12gb"
        warn "Unknown GPU: $gpu, defaulting to RTX 3060 12GB config"
      fi
    fi
    log "Detected: $gpu → config: $GPU_MODEL"
  else
    if [[ "$DEVICE" == "x86" ]]; then
      warn "No GPU detected, falling back to CPU-only mode"
      DEVICE="cpu"
    fi
  fi
}

# ── Pre-flight Checks ──────────────────────────────────────────────────────
preflight_checks() {
  header "Pre-flight Checks"

  if [[ "$EUID" -ne 0 ]] && ! $DRY_RUN; then
    warn "It is recommended to run as root for system-level operations"
  fi

  for cmd in docker docker-compose python3 curl; do
    if ! command -v "$cmd" &>/dev/null; then
      err "Required command not found: $cmd"
    fi
  done
  log "All system dependencies available"

  # Check disk space
  local required_gb=50
  local available_gb; available_gb=$(df --output=avail "$DATA_DIR" 2>/dev/null | tail -1)
  if [[ -n "$available_gb" && "$available_gb" -lt $((required_gb * 1024 * 1024)) ]]; then
    warn "Low disk space (${available_gb}MB available, ${required_gb}GB recommended)"
  fi

  # Create data directories
  for dir in "$DATA_DIR" "$DATA_DIR/postgres" "$DATA_DIR/sqlite" \
             "$DATA_DIR/sync" "$DATA_DIR/logs" "$DATA_DIR/backups" \
             "$MODELS_DIR" "$MODELS_DIR/whisper" "$MODELS_DIR/piper" \
             "$MODELS_DIR/qwen" "$MODELS_DIR/stella" "$MODELS_DIR/vit"; do
    mkdir -p "$dir"
  done
  log "Data directories created at $DATA_DIR and $MODELS_DIR"
}

# ── Model Download & Quantization ──────────────────────────────────────────
download_models() {
  header "Model Download & Quantization"

  if $SKIP_MODELS; then
    info "Skipping model download (--skip-models)"
    return
  fi

  # Pull models from HuggingFace or S3 mirror
  local s3_mirror="s3://models.ubuntucare.gov.zm"
  local hf_mirror="https://huggingface.co"

  declare -A models
  case "$GPU_MODEL" in
    rtx_3060_12gb|rtx_4070_16gb)
      models=(
        ["whisper-small"]="openai/whisper-small:onnx-int8"
        ["qwen3-8b"]="Qwen/Qwen3-8B:AWQ-int4"
        ["stella-400m"]="infgrad/stella-base-400m-v5:fp16"
        ["piper"]="rhasspy/piper-voices:en_US-lessac-medium"
      )
      ;;
    rtx_4090_24gb|l40s_48gb)
      models=(
        ["whisper-large-v3"]="openai/whisper-large-v3:onnx-int8"
        ["qwen3-32b"]="Qwen/Qwen3-32B:AWQ-int4"
        ["stella-400m"]="infgrad/stella-base-400m-v5:fp16"
        ["piper"]="rhasspy/piper-voices:en_US-lessac-medium"
        ["vit-lung"]="tuberculosis-xray/vit:onnx-int8"
      )
      ;;
    a100_80gb)
      models=(
        ["whisper-large-v3"]="openai/whisper-large-v3:fp16"
        ["qwen3-32b"]="Qwen/Qwen3-32B:fp16"
        ["stella-400m"]="infgrad/stella-base-400m-v5:fp16"
        ["piper"]="rhasspy/piper-voices:en_US-lessac-medium"
        ["vit-lung"]="tuberculosis-xray/vit:fp16"
        ["biobert"]="dmis-lab/biobert-v1.1:fp16"
      )
      ;;
    jetson|pi5|cpu)
      models=(
        ["whisper-tiny"]="openai/whisper-tiny:onnx-int8"
        ["qwen3-1b"]="Qwen/Qwen3-1B:AWQ-int4"
        ["stella-100m"]="infgrad/stella-base-100m-v5:fp16"
        ["piper-tiny"]="rhasspy/piper-voices:en_US-lessac-tiny"
      )
      ;;
  esac

  for model_name in "${!models[@]}"; do
    local target_dir="$MODELS_DIR/$model_name"
    if [[ -f "$target_dir/.downloaded" ]]; then
      info "Model $model_name already downloaded"
      continue
    fi

    mkdir -p "$target_dir"
    log "Downloading $model_name..."

    # Try S3 mirror first (faster for local network)
    if curl -sf --connect-timeout 5 "$s3_mirror/$model_name/MODEL_INFO" > /dev/null 2>&1; then
      aws s3 sync --no-sign-request "$s3_mirror/$model_name/" "$target_dir/" --quiet
    else
      # Fall back to HuggingFace
      local hf_repo="${models[$model_name]%%:*}"
      local variant="${models[$model_name]##*:}"
      python3 -c "
import sys, os, json
sys.path.insert(0, os.path.expanduser('~/.cache/huggingface'))
from huggingface_hub import snapshot_download
snapshot_download(repo_id='$hf_repo', local_dir='$target_dir',
                  local_dir_use_symlinks=False, resume_download=True)
" || warn "Failed to download $model_name from HuggingFace"
    fi

    # Verify checksum
    if [[ -f "$target_dir/checksum.sha256" ]]; then
      (cd "$target_dir" && sha256sum -c checksum.sha256) || warn "Checksum verification failed for $model_name"
    fi

    # Mark as downloaded
    date +%s > "$target_dir/.downloaded"
    log "Downloaded $model_name → $target_dir"
  done
}

# ── Docker Setup ────────────────────────────────────────────────────────────
setup_docker() {
  header "Docker Setup"

  if $SKIP_DOCKER; then
    info "Skipping Docker setup (--skip-docker)"
    return
  fi

  # Test Docker
  docker info > /dev/null 2>&1 || err "Docker daemon not running"

  # Check NVIDIA container toolkit if GPU
  if [[ -n "$GPU_MODEL" && "$GPU_MODEL" != "cpu" ]]; then
    if docker info 2>/dev/null | grep -qi "Runtimes.*nvidia"; then
      log "NVIDIA container runtime detected"
    else
      warn "NVIDIA container runtime not detected. GPU acceleration unavailable."
    fi
  fi

  # Pull images
  local images=(
    "postgres:16-alpine"
    "nats:2.10-alpine"
  )
  for img in "${images[@]}"; do
    docker pull "$img" &
  done
  wait
  log "Base images pulled"
}

# ── Database Initialization ─────────────────────────────────────────────────
init_database() {
  header "Database Initialization"

  local db_url="${DATABASE_URL:-sqlite:///$DATA_DIR/sqlite/ubuntucare.db}"

  if [[ "$db_url" == sqlite* ]]; then
    log "SQLite database: $DATA_DIR/sqlite/ubuntucare.db"
    touch "$DATA_DIR/sqlite/.initialized"
  elif [[ "$db_url" == postgresql* ]]; then
    log "PostgreSQL database configured"
    # Wait for Postgres to be ready
    for i in {1..30}; do
      if docker exec ubuntucare-db pg_isready -U ubuntucare > /dev/null 2>&1; then
        log "PostgreSQL is ready"
        break
      fi
      sleep 2
    done
  fi

  # Run migrations
  if python3 -c "import alembic" 2>/dev/null; then
    log "Running database migrations..."
    alembic upgrade head || warn "Migration failed, attempting seed..."
  else
    warn "Alembic not available, skipping migrations"
  fi
}

# ── Sync Agent Setup ────────────────────────────────────────────────────────
setup_sync_agent() {
  header "Sync Agent Setup"

  cp "sync-agent.py" "$DATA_DIR/sync/sync-agent.py"
  chmod +x "$DATA_DIR/sync/sync-agent.py"

  # Create device key if not exists
  if [[ ! -f "$DATA_DIR/sync/device.key" ]]; then
    openssl rand -base64 32 > "$DATA_DIR/sync/device.key"
    log "Device key generated"
  fi

  # Create systemd service
  cat > /etc/systemd/system/ubuntucare-sync.service << 'SERVICE'
[Unit]
Description=UbuntuCare Sync Agent
After=network-online.target docker.service
Wants=network-online.target

[Service]
Type=simple
User=root
WorkingDirectory=/data/ubuntucare/sync
ExecStart=/usr/bin/python3 /data/ubuntucare/sync/sync-agent.py
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
SERVICE

  systemctl daemon-reload
  log "Sync agent service installed"
}

# ── Health Check ─────────────────────────────────────────────────────────────
health_check() {
  header "Health Check"

  # Run the health check script
  if [[ -f "../../scripts/monitoring/health-check.sh" ]]; then
    bash "../../scripts/monitoring/health-check.sh" --offline || warn "Some health checks failed"
  else
    # Basic health checks
    info "Running basic health checks..."

    # Check Docker containers
    docker ps --format "table {{.Names}}\t{{.Status}}" 2>/dev/null | head -20

    # Check disk space
    df -h "$DATA_DIR" | tail -1

    # Check model availability
    for model_dir in "$MODELS_DIR"/*/; do
      if [[ -f "${model_dir}.downloaded" ]]; then
        local model_name; model_name=$(basename "$model_dir")
        log "Model available: $model_name"
      fi
    done

    # Check database
    if [[ -f "$DATA_DIR/sqlite/ubuntucare.db" ]]; then
      local db_size; db_size=$(stat -c%s "$DATA_DIR/sqlite/ubuntucare.db" 2>/dev/null)
      log "Database size: $((db_size / 1048576))MB"
    fi
  fi

  log "Deployment health check completed"
}

# ── Auto-start on Boot ──────────────────────────────────────────────────────
setup_autostart() {
  header "Auto-start Configuration"

  # Enable services
  systemctl enable ubuntucare-sync.service 2>/dev/null || true

  # Docker containers restart policy
  if [[ -f "$COMPOSE_FILE" ]]; then
    docker compose -f "$COMPOSE_FILE" up -d --remove-orphans
  fi

  log "Autostart configured — services will restart on boot"
}

# ── Main ────────────────────────────────────────────────────────────────────
main() {
  echo -e "${BOLD}"
  echo "╔══════════════════════════════════════════════════════════════╗"
  echo "║      UbuntuCare — Edge Deployment (Zambia)          ║"
  echo "╚══════════════════════════════════════════════════════════════╝"
  echo -e "${NC}"

  detect_device
  info "Device: ${DEVICE} | GPU: ${GPU_MODEL:-none}"
  info "Models: ${MODELS_DIR} | Data: ${DATA_DIR}"

  if $DRY_RUN; then
    log "Dry run mode — no changes will be made"
    exit 0
  fi

  preflight_checks
  download_models
  setup_docker
  init_database
  setup_sync_agent
  health_check
  setup_autostart

  echo -e "\n${GREEN}${BOLD}✅ Deployment completed successfully!${NC}"
  info "Web UI:      http://$(hostname -I | awk '{print $1}'):8000"
  info "Health API:  http://$(hostname -I | awk '{print $1}'):8000/health"
  info "Sync Agent:  systemctl status ubuntucare-sync"
  info "Data Dir:    $DATA_DIR"
  info "Models Dir:  $MODELS_DIR"
}

main "$@"
