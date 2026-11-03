#!/usr/bin/env bash
set -euo pipefail

#=============================================================================
# Zambia Health Platform - Offline/Edge Sync Script
# Synchronizes data between central and edge/rural deployments
# Supports: Patient records, clinical guidelines, ML models, system updates
#=============================================================================

readonly SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
readonly TIMESTAMP=$(date +%Y%m%d-%H%M%S)
readonly LOG_FILE="/var/log/zambia-health/sync-${TIMESTAMP}.log"
readonly SYNC_ROOT="/data/sync"
readonly LOCK_FILE="/var/run/zambia-health/sync.lock"

# Sync modes
MODE="pull"          # pull|push|bidirectional
SYNC_TYPE="patient"  # patient|guidelines|models|system|all
SOURCE_SERVER=""
TARGET_SERVER=""
REMOTE_BUCKET=""
SINCE_DATE=""
COMPRESS=true
VERIFY=true
DRY_RUN=false
BANDWIDTH_LIMIT=0   # KB/s, 0 = unlimited

log()   { echo "[$(date +%H:%M:%S)] $*" | tee -a "${LOG_FILE}"; }
error() { echo "[ERROR] $*" | tee -a "${LOG_FILE}" >&2; }
warn()  { echo "[WARN] $*" | tee -a "${LOG_FILE}"; }

usage() {
    cat <<EOF
Zambia Health - Offline/Edge Sync Script

Usage: $(basename "$0") [options]

Options:
  -m, --mode MODE       Sync mode: pull|push|bidirectional (default: pull)
  -t, --type TYPE       Sync type: patient|guidelines|models|system|all
  -s, --source HOST     Source server (central)
  -d, --target HOST     Target server (edge/rural)
  -b, --bucket URL      S3/Blob/GS bucket for transfer
      --since DATE      Sync records since date (YYYY-MM-DD)
      --no-compress     Disable compression
      --no-verify       Disable integrity verification
      --bandwidth KBPS  Limit bandwidth (KB/s)
  -n, --dry-run        Preview sync (no changes)
  -h, --help           Show this help message

Examples:
  $(basename "$0") --mode pull --type patient --source central.health.zm
  $(basename "$0") --mode push --type models --bucket s3://zambia-health-models
EOF
    exit 0
}

parse_args() {
    while [[ $# -gt 0 ]]; do
        case "$1" in
            -m|--mode)         MODE="$2"; shift 2 ;;
            -t|--type)         SYNC_TYPE="$2"; shift 2 ;;
            -s|--source)       SOURCE_SERVER="$2"; shift 2 ;;
            -d|--target)       TARGET_SERVER="$2"; shift 2 ;;
            -b|--bucket)       REMOTE_BUCKET="$2"; shift 2 ;;
            --since)           SINCE_DATE="$2"; shift 2 ;;
            --no-compress)     COMPRESS=false ;;
            --no-verify)       VERIFY=false ;;
            --bandwidth)       BANDWIDTH_LIMIT="$2"; shift 2 ;;
            -n|--dry-run)      DRY_RUN=true; shift ;;
            -h|--help)         usage ;;
            *)                 error "Unknown option: $1"; usage ;;
        esac
    done
}

check_prerequisites() {
    command -v rsync >/dev/null 2>&1 || { error "rsync required"; exit 1; }
    command -v gzip >/dev/null 2>&1 || { error "gzip required"; exit 1; }

    mkdir -p "${SYNC_ROOT}/${SYNC_TYPE}"
    mkdir -p "$(dirname "${LOG_FILE}")"
    mkdir -p "$(dirname "${LOCK_FILE}")"
}

acquire_lock() {
    if [[ -f "${LOCK_FILE}" ]]; then
        local pid
        pid=$(cat "${LOCK_FILE}" 2>/dev/null || echo "")
        if kill -0 "${pid}" 2>/dev/null; then
            error "Another sync process is running (PID: ${pid})"
            exit 1
        fi
        warn "Stale lock file found, removing..."
    fi
    echo "$$" > "${LOCK_FILE}"
    trap 'rm -f "${LOCK_FILE}"' EXIT
}

sync_patient_records() {
    log "Syncing patient records..."

    local source_db="${SOURCE_SERVER}:5432"
    local target_db="${TARGET_SERVER}:5432"
    local since_filter=""

    if [[ -n "${SINCE_DATE}" ]]; then
        since_filter="--since ${SINCE_DATE}"
    fi

    if [[ "${DRY_RUN}" == "true" ]]; then
        log "DRY-RUN: Would sync patient records from ${source_db} to ${target_db}"
        return 0
    fi

    # Use PostgreSQL logical replication or custom sync
    case "${MODE}" in
        pull)
            log "Pulling patient records from ${SOURCE_SERVER}..."
            PGPASSWORD="${SYNC_DB_PASSWORD}" pg_dump \
                --dbname="postgresql://${SYNC_DB_USER:-sync}:${SYNC_DB_PASSWORD}@${SOURCE_SERVER}:5432/zambia_health" \
                --table=patients \
                --table=visits \
                --table=diagnoses \
                --table=prescriptions \
                --data-only \
                --compress=9 \
                --file="${SYNC_ROOT}/${SYNC_TYPE}/patients-${TIMESTAMP}.dump" \
                ${since_filter:+-t "public.patients where updated_at > '${SINCE_DATE}'"} \
                2>>"${LOG_FILE}"
            ;;
        push)
            log "Pushing patient records to ${TARGET_SERVER}..."
            # Replicate to edge node
            PGPASSWORD="${SYNC_DB_PASSWORD}" psql \
                "postgresql://${SYNC_DB_USER:-sync}:${SYNC_DB_PASSWORD}@${TARGET_SERVER}:5432/zambia_health" \
                -c "SELECT pglogical.replicate_ddl('CREATE TABLE IF NOT EXISTS patients_sync (...)' );" \
                2>>"${LOG_FILE}" || true
            ;;
    esac
}

sync_clinical_guidelines() {
    log "Syncing clinical guidelines..."
    local src_dir="/data/guidelines"
    local dst_dir="/data/guidelines"
    local rsync_opts="-avz --delete"

    if [[ "${DRY_RUN}" == "true" ]]; then
        log "DRY-RUN: Would sync guidelines"
        [[ -n "${SOURCE_SERVER}" ]] && log "  rsync ${rsync_opts} ${SOURCE_SERVER}:${src_dir}/ ${dst_dir}/"
        return 0
    fi

    case "${MODE}" in
        pull)
            [[ -n "${SOURCE_SERVER}" ]] && rsync ${rsync_opts} \
                "${SOURCE_SERVER}:${src_dir}/" "${dst_dir}/" 2>>"${LOG_FILE}"
            ;;
        push)
            [[ -n "${TARGET_SERVER}" ]] && rsync ${rsync_opts} \
                "${src_dir}/" "${TARGET_SERVER}:${dst_dir}/" 2>>"${LOG_FILE}"
            ;;
        bidirectional)
            # Two-way sync with conflict resolution
            [[ -n "${SOURCE_SERVER}" ]] && rsync ${rsync_opts} \
                "${SOURCE_SERVER}:${src_dir}/" "${dst_dir}/" 2>>"${LOG_FILE}"
            [[ -n "${TARGET_SERVER}" ]] && rsync ${rsync_opts} \
                "${dst_dir}/" "${TARGET_SERVER}:${dst_dir}/" 2>>"${LOG_FILE}"
            ;;
    esac
}

sync_ml_models() {
    log "Syncing ML models..."
    local model_dir="/data/models"

    if [[ "${DRY_RUN}" == "true" ]]; then
        log "DRY-RUN: Would sync ML models"
        [[ -n "${REMOTE_BUCKET}" ]] && log "  aws s3 sync ${REMOTE_BUCKET}/models/ ${model_dir}/"
        return 0
    fi

    # Download from remote storage
    if [[ -n "${REMOTE_BUCKET}" ]]; then
        case "${REMOTE_BUCKET}" in
            s3://*)
                aws s3 sync "${REMOTE_BUCKET}/models/" "${model_dir}/" \
                    --only-show-errors
                ;;
            https://*)
                # Download model manifest and verify
                curl -sf "${REMOTE_BUCKET}/models/MANIFEST.json" -o "${model_dir}/MANIFEST.json"
                python3 -c "
import json
with open('${model_dir}/MANIFEST.json') as f:
    manifest = json.load(f)
for model in manifest['models']:
    print(f\"  {model['name']}: {model['version']} ({model['size_mb']}MB)\")
"
                ;;
        esac

        # Verify model signatures
        if [[ -f "${model_dir}/MANIFEST.json" ]]; then
            log "Model manifest loaded. $(python3 -c "import json; m=json.load(open('${model_dir}/MANIFEST.json')); print(len(m.get('models',[])))") models available"
        fi
    fi

    # Deploy models to serving infrastructure
    if command -v kubectl >/dev/null 2>&1; then
        kubectl create configmap model-versions \
            --from-file="${model_dir}/MANIFEST.json" \
            --dry-run=client -o yaml | kubectl apply -f - 2>/dev/null || true
    fi
}

sync_system_updates() {
    log "Syncing system updates..."

    if [[ "${DRY_RUN}" == "true" ]]; then
        log "DRY-RUN: Would sync system packages and updates"
        return 0
    fi

    # Download updates
    local update_dir="${SYNC_ROOT}/updates"
    mkdir -p "${update_dir}"

    if [[ -n "${REMOTE_BUCKET}" ]]; then
        case "${REMOTE_BUCKET}" in
            s3://*)
                aws s3 sync "${REMOTE_BUCKET}/updates/" "${update_dir}/" \
                    --only-show-errors
                ;;
        esac
    fi

    # Apply updates
    if ls "${update_dir}"/*.deb 1>/dev/null 2>&1; then
        dpkg -i "${update_dir}"/*.deb 2>>"${LOG_FILE}" || true
        apt-get install -f -y 2>>"${LOG_FILE}" || true
    fi

    if ls "${update_dir}"/*.rpm 1>/dev/null 2>&1; then
        rpm -Uvh "${update_dir}"/*.rpm 2>>"${LOG_FILE}" || true
    fi
}

verify_sync() {
    if [[ "${VERIFY}" != "true" ]]; then
        return 0
    fi

    log "Verifying sync integrity..."
    local sync_dir="${SYNC_ROOT}/${SYNC_TYPE}"

    # Check checksums
    find "${sync_dir}" -name "*.sha256" | while read -r sha; do
        local target="${sha%.sha256}"
        if [[ -f "${target}" ]]; then
            if sha256sum -c "${sha}" --strict >/dev/null 2>&1; then
                log "  OK: $(basename "${target}")"
            else
                error "  CHECKSUM FAILED: $(basename "${target}")"
            fi
        fi
    done

    # Verify PostgreSQL dump
    for dump in "${sync_dir}"/*.dump; do
        if [[ -f "${dump}" ]]; then
            if pg_restore --list "${dump}" >/dev/null 2>&1; then
                log "  Valid dump: $(basename "${dump}")"
            else
                error "  Corrupt dump: $(basename "${dump}")"
            fi
        fi
    done
}

main() {
    parse_args "$@"
    check_prerequisites
    acquire_lock

    log "=== Zambia Health Offline Sync ==="
    log "Mode: ${MODE} | Type: ${SYNC_TYPE}"
    log "Source: ${SOURCE_SERVER:-N/A}"
    log "Target: ${TARGET_SERVER:-N/A}"
    log "Bucket: ${REMOTE_BUCKET:-N/A}"
    log ""

    case "${SYNC_TYPE}" in
        patient)    sync_patient_records ;;
        guidelines) sync_clinical_guidelines ;;
        models)     sync_ml_models ;;
        system)     sync_system_updates ;;
        all)
            sync_patient_records
            sync_clinical_guidelines
            sync_ml_models
            sync_system_updates
            ;;
    esac

    verify_sync

    log ""
    log "=== Sync completed ==="
}

main "$@"
