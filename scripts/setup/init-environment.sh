#!/usr/bin/env bash
# =============================================================================
# Environment Initialization — UbuntuCare (Zambia)
# =============================================================================
# Sets up the complete development/production environment including:
#   - Python virtual environment & dependencies
#   - Node.js setup
#   - Docker & GPU driver checks
#   - Model downloads
#   - Database setup
#   - Keycloak setup (config)
#   - Secret generation
# =============================================================================

set -euo pipefail

RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; BLUE='\033[0;34m'
BOLD='\033[1m'; NC='\033[0m'
log()  { echo -e "${GREEN}[✓]${NC} $1"; }
warn() { echo -e "${YELLOW}[!]${NC} $1"; }
err()  { echo -e "${RED}[✗]${NC} $1" >&2; exit 1; }
info() { echo -e "${BLUE}[i]${NC} $1"; }

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/../.." && pwd)"
VENV_DIR="${VENV_DIR:-$PROJECT_DIR/.venv}"
NODE_VERSION="${NODE_VERSION:-18}"
ENV_FILE="${ENV_FILE:-$PROJECT_DIR/.env}"

header() { echo -e "\n${BOLD}━━━ $1 ━━━${NC}\n"; }

# ── Python Setup ───────────────────────────────────────────────────────────
setup_python() {
  header "Python Virtual Environment"

  if [[ -d "$VENV_DIR" ]]; then
    info "Virtual environment already exists at $VENV_DIR"
  else
    log "Creating virtual environment at $VENV_DIR..."
    python3 -m venv "$VENV_DIR"
  fi

  source "$VENV_DIR/bin/activate"
  pip install --upgrade pip setuptools wheel

  if [[ -f "$PROJECT_DIR/requirements.txt" ]]; then
    pip install -r "$PROJECT_DIR/requirements.txt"
    log "Installed Python dependencies from requirements.txt"
  fi

  if [[ -f "$PROJECT_DIR/requirements-dev.txt" ]]; then
    pip install -r "$PROJECT_DIR/requirements-dev.txt" 2>/dev/null && \
      log "Installed dev dependencies" || true
  fi

  # Install common ML/database packages
  pip install --quiet \
    "alembic" "psycopg2-binary" "sqlalchemy" "asyncpg" \
    "httpx" "aiohttp" "pydantic" "python-dotenv" \
    "huggingface-hub" "sentencepiece" "transformers" \
    "onnxruntime" "onnxruntime-gpu" 2>/dev/null || warn "Some ML packages not available"

  log "Python environment ready"
}

# ── Node.js Setup ──────────────────────────────────────────────────────────
setup_nodejs() {
  header "Node.js Setup"

  if command -v node &>/dev/null; then
    local node_ver; node_ver=$(node --version)
    log "Node.js $node_ver already installed"
  else
    warn "Node.js not found. Install via nvm or package manager:"
    info "  curl -fsSL https://deb.nodesource.com/setup_${NODE_VERSION}.x | bash -"
    info "  apt-get install -y nodejs"
  fi

  if [[ -f "$PROJECT_DIR/package.json" ]]; then
    cd "$PROJECT_DIR"
    npm install --quiet 2>/dev/null && log "npm dependencies installed" || warn "npm install failed"
    cd "$SCRIPT_DIR"
  fi
}

# ── Docker Setup ───────────────────────────────────────────────────────────
setup_docker() {
  header "Docker Setup"

  if ! command -v docker &>/dev/null; then
    warn "Docker not found. Install Docker first:"
    warn "  curl -fsSL https://get.docker.com | sh"
    return
  fi
  log "Docker installed: $(docker --version)"

  if ! docker info &>/dev/null; then
    warn "Docker daemon not running or permission denied"
    return
  fi

  # Check Docker Compose
  if docker compose version &>/dev/null; then
    log "Docker Compose: $(docker compose version)"
  elif command -v docker-compose &>/dev/null; then
    log "Docker Compose: $(docker-compose --version)"
  else
    warn "Docker Compose not found"
  fi
}

# ── GPU Driver Check ───────────────────────────────────────────────────────
check_gpu() {
  header "GPU Driver Check"

  if command -v nvidia-smi &>/dev/null; then
    log "NVIDIA drivers found"
    nvidia-smi --query-gpu=name,driver_version,memory.total --format=csv,noheader

    if command -v nvidia-container-toolkit &>/dev/null; then
      log "NVIDIA container toolkit available"
    else
      warn "Install nvidia-container-toolkit for GPU Docker support:"
      warn "  https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/install-guide.html"
    fi
  else
    warn "No NVIDIA GPU detected (CPU-only mode)"
  fi
}

# ── Model Download ─────────────────────────────────────────────────────────
setup_models() {
  header "Model Download"

  if [[ -f "$SCRIPT_DIR/init-models.sh" ]]; then
    bash "$SCRIPT_DIR/init-models.sh" --skip-if-exists
  else
    warn "Model script not found at $SCRIPT_DIR/init-models.sh"
  fi
}

# ── Database Setup ─────────────────────────────────────────────────────────
setup_database() {
  header "Database Setup"

  local db_url="${DATABASE_URL:-sqlite:///$PROJECT_DIR/data/ubuntucare_dev.db}"

  if [[ "$db_url" == sqlite* ]]; then
    log "Using SQLite — no setup required"
    mkdir -p "$PROJECT_DIR/data"
  elif [[ "$db_url" == postgresql* ]]; then
    log "PostgreSQL configured — applying migrations"
    if command -v alembic &>/dev/null; then
      cd "$PROJECT_DIR"
      alembic upgrade head
      cd "$SCRIPT_DIR"
    else
      warn "Alembic not available, cannot run migrations"
    fi
  fi

  log "Database ready"
}

# ── Keycloak Setup ─────────────────────────────────────────────────────────
setup_keycloak() {
  header "Keycloak Setup"

  if [[ -f "$PROJECT_DIR/docker-compose.yml" ]]; then
    if grep -qi "keycloak" "$PROJECT_DIR/docker-compose.yml" 2>/dev/null; then
      info "Keycloak configured in docker-compose.yml"
      info "Start with: docker compose -f $PROJECT_DIR/docker-compose.yml up -d keycloak"
    fi
  fi

  # Create Keycloak realm config if not exists
  local realm_dir="$PROJECT_DIR/config/keycloak"
  if [[ ! -d "$realm_dir" ]]; then
    mkdir -p "$realm_dir"
    cat > "$realm_dir/ubuntucare-realm.json" << 'EOF'
{
  "realm": "ubuntucare",
  "enabled": true,
  "sslRequired": "external",
  "registrationAllowed": false,
  "loginWithEmailAllowed": true,
  "clients": [
    {
      "clientId": "ubuntucare-api",
      "enabled": true,
      "publicClient": false,
      "secret": "CHANGE-ME-IN-PRODUCTION",
      "serviceAccountsEnabled": true,
      "directAccessGrantsEnabled": true
    }
  ]
}
EOF
    log "Keycloak realm config created"
  else
    info "Keycloak config already exists"
  fi
}

# ── Secret Generation ──────────────────────────────────────────────────────
generate_secrets() {
  header "Secret Generation"

  if [[ -f "$ENV_FILE" ]]; then
    warn "$ENV_FILE already exists — skipping"
    info "Delete it and re-run to regenerate"
    return
  fi

  cat > "$ENV_FILE" << EOF
# UbuntuCare — Environment Variables
# Generated: $(date -u +"%Y-%m-%d %H:%M:%S UTC")
# WARNING: Keep this file secret! Never commit it to version control.

# Database
DATABASE_URL=sqlite:///data/ubuntucare.db
DB_PASSWORD=$(openssl rand -base64 24)

# Redis
REDIS_PASSWORD=$(openssl rand -base64 24)

# Auth
JWT_SECRET=$(openssl rand -base64 48)
ENCRYPTION_KEY=$(openssl rand -hex 32)

# Device
DEVICE_KEY=$(openssl rand -base64 32)

# API Keys
AFRICASTALKING_API_KEY=
AFRICASTALKING_USERNAME=

# CDN
CDN_API_TOKEN=

# Monitoring
SENTRY_DSN=

# Features
OFFLINE_MODE=true
LANGUAGE_PACK=en
EOF

  log "Secrets generated in $ENV_FILE"
  chmod 600 "$ENV_FILE"
}

# ── Main ───────────────────────────────────────────────────────────────────
main() {
  echo -e "${BOLD}"
  echo "╔══════════════════════════════════════════════════════════════╗"
  echo "║      UbuntuCare — Environment Setup (Zambia)        ║"
  echo "╚══════════════════════════════════════════════════════════════╝"
  echo -e "${NC}"

  cd "$PROJECT_DIR"

  setup_python
  setup_nodejs
  setup_docker
  check_gpu
  setup_models
  setup_database
  setup_keycloak
  generate_secrets

  echo -e "\n${GREEN}${BOLD}✅ Environment setup completed!${NC}"
  echo -e "  Virtual env: ${BLUE}source $VENV_DIR/bin/activate${NC}"
  echo -e "  Config:       ${BLUE}$ENV_FILE${NC}"
  echo -e "  Start dev:    ${BLUE}uvicorn app.main:app --reload${NC}"
}

main "$@"
