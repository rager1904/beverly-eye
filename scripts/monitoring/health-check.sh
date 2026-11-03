#!/usr/bin/env bash
# =============================================================================
# Health Check — UbuntuCare (Zambia)
# =============================================================================
# Comprehensive health check for the platform, suitable for both online
# and offline/edge deployments.
# =============================================================================

set -euo pipefail

RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; BLUE='\033[0;34m'
BOLD='\033[1m'; NC='\033[0m'
PASS=0; FAIL=0; WARN=0

check() {
  local status="$1" message="$2"
  case "$status" in
    pass) echo -e "  ${GREEN}✓${NC} $message"; ((PASS++)) ;;
    fail) echo -e "  ${RED}✗${NC} $message"; ((FAIL++)) ;;
    warn) echo -e "  ${YELLOW}⚠${NC} $message"; ((WARN++)) ;;
  esac
}

header() { echo -e "\n${BOLD}$1${NC}"; }

# ── System Checks ──────────────────────────────────────────────────────────
header "System"
check pass "Host: $(hostname)"
check pass "Uptime: $(uptime -p)"
check pass "Kernel: $(uname -r)"
check pass "Date: $(date -u)"

# ── CPU & Memory ───────────────────────────────────────────────────────────
header "CPU & Memory"
cpu_load=$(awk '{print $1}' /proc/loadavg 2>/dev/null || echo "N/A")
cpu_cores=$(nproc 2>/dev/null || echo "N/A")
mem_total=$(free -m | awk '/Mem:/{print $2}' 2>/dev/null || echo "N/A")
mem_avail=$(free -m | awk '/Mem:/{print $7}' 2>/dev/null || echo "N/A")
check pass "CPU: load=$cpu_load cores=$cpu_cores"
check pass "Memory: ${mem_avail}MB available / ${mem_total}MB total"

# ── Disk ────────────────────────────────────────────────────────────────────
header "Disk"
for mount in "/data" "/" "/var/lib/docker"; do
  if df "$mount" &>/dev/null; then
    usage=$(df -h "$mount" | awk 'NR==2{print $5}' | sed 's/%//')
    avail=$(df -h "$mount" | awk 'NR==2{print $4}')
    total=$(df -h "$mount" | awk 'NR==2{print $2}')
    if [[ "$usage" -gt 90 ]]; then
      check fail "DISK $mount: ${usage}% used (${avail} avail / ${total} total)"
    elif [[ "$usage" -gt 75 ]]; then
      check warn "DISK $mount: ${usage}% used (${avail} avail / ${total} total)"
    else
      check pass "DISK $mount: ${usage}% used (${avail} avail / ${total} total)"
    fi
  fi
done

# ── GPU ──────────────────────────────────────────────────────────────────────
header "GPU"
if command -v nvidia-smi &>/dev/null; then
  gpu_info=$(nvidia-smi --query-gpu=name,temperature.gpu,utilization.gpu,memory.used,memory.total \
    --format=csv,noheader 2>/dev/null | head -1)
  if [[ -n "$gpu_info" ]]; then
    check pass "NVIDIA GPU: $gpu_info"
  fi
  temp=$(nvidia-smi --query-gpu=temperature.gpu --format=csv,noheader 2>/dev/null | head -1)
  if [[ -n "$temp" && "$temp" -gt 85 ]]; then
    check fail "GPU temperature critical: ${temp}°C"
  elif [[ -n "$temp" && "$temp" -gt 75 ]]; then
    check warn "GPU temperature high: ${temp}°C"
  fi
else
  check warn "No NVIDIA GPU detected"
fi

# Check Jetson
if [[ -f /proc/device-tree/model ]] && grep -qi "Jetson" /proc/device-tree/model; then
  jetpack=$(head -1 /etc/nv_tegra_release 2>/dev/null || echo "unknown")
  check pass "Jetson detected: JetPack $jetpack"
fi

# ── Docker ──────────────────────────────────────────────────────────────────
header "Docker"
if command -v docker &>/dev/null; then
  if docker info &>/dev/null; then
    containers=$(docker ps -q | wc -l)
    images=$(docker images -q | sort -u | wc -l)
    check pass "Docker running: $containers containers, $images images"
  else
    check fail "Docker daemon not responding"
  fi
else
  check warn "Docker not installed"
fi

# ── Application ─────────────────────────────────────────────────────────────
header "Application"
if curl -sf http://localhost:8000/health &>/dev/null; then
  health_json=$(curl -sf http://localhost:8000/health 2>/dev/null)
  check pass "Application health endpoint: OK"
  echo "$health_json" | python3 -m json.tool 2>/dev/null | head -10
else
  check fail "Application health endpoint: NOT REACHABLE"
fi

# Check service ports
for port_tuple in "8000:App" "9090:Prometheus" "4222:NATS" "5432:PostgreSQL"; do
  port="${port_tuple%%:*}"
  name="${port_tuple##*:}"
  if ss -tlnp "sport = :$port" 2>/dev/null | grep -q ":$port" || \
     netstat -tlnp 2>/dev/null | grep -q ":$port" || true; then
    :
  else
    check warn "Port $port ($name): not listening"
  fi
done

# ── Models ──────────────────────────────────────────────────────────────────
header "AI Models"
models_dir="${MODELS_DIR:-/data/models}"
if [[ -d "$models_dir" ]]; then
  for model_dir in "$models_dir"/*/; do
    if [[ -f "${model_dir}.downloaded" ]]; then
      name=$(basename "$model_dir")
      size=$(du -sh "$model_dir" 2>/dev/null | cut -f1)
      check pass "Model: $name ($size)"
    fi
  done
else
  check warn "Models directory not found: $models_dir"
fi

# ── Sync Agent ─────────────────────────────────────────────────────────────
header "Sync Agent"
if systemctl is-active --quiet ubuntucare-sync 2>/dev/null; then
  check pass "Sync agent: running"
elif docker ps --format '{{.Names}}' 2>/dev/null | grep -q sync; then
  check pass "Sync agent (Docker): running"
else
  check warn "Sync agent: not running"
fi

# ── Database ────────────────────────────────────────────────────────────────
header "Database"
db_path="${DB_PATH:-/data/ubuntucare/ubuntucare.db}"
if [[ -f "$db_path" ]]; then
  db_size=$(stat -c%s "$db_path" 2>/dev/null)
  db_size_mb=$((db_size / 1048576))
  check pass "SQLite database: ${db_size_mb}MB"
  # Basic integrity check
  if sqlite3 "$db_path" "PRAGMA integrity_check;" 2>/dev/null | grep -q "ok"; then
    check pass "Database integrity: OK"
  else
    check fail "Database integrity: FAILED"
  fi
else
  check warn "SQLite database not found at $db_path"
fi

# ── Backup ──────────────────────────────────────────────────────────────────
header "Backup"
backup_dir="${BACKUP_DIR:-/data/ubuntucare/backups}"
if [[ -d "$backup_dir/full" ]]; then
  latest=$(ls -t "$backup_dir/full/" 2>/dev/null | head -1)
  if [[ -n "$latest" ]]; then
    age=$((($(date +%s) - $(stat -c%Y "$backup_dir/full/$latest")) / 86400))
    check pass "Latest backup: $latest (${age}d old)"
  else
    check warn "No backups found"
  fi
else
  check warn "Backup directory not found"
fi

# ── Summary ─────────────────────────────────────────────────────────────────
header "Summary"
total=$((PASS + FAIL + WARN))
echo -e "  ${GREEN}${PASS} passed${NC}, ${RED}${FAIL} failed${NC}, ${YELLOW}${WARN} warnings${NC} (${total} total)"

if [[ "$FAIL" -gt 0 ]]; then
  exit 1
fi
