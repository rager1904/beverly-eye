#!/usr/bin/env bash
set -euo pipefail

#=============================================================================
# Zambia Health Platform - Database Backup Script
# Backs up PostgreSQL (RDS/Cloud SQL/Azure DB) and Redis
#=============================================================================

readonly SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
readonly TIMESTAMP=$(date +%Y%m%d-%H%M%S)
readonly BACKUP_ROOT="/data/backups/zambia-health"
readonly BACKUP_DIR="${BACKUP_ROOT}/${TIMESTAMP}"
readonly LOG_FILE="/var/log/zambia-health/backup-${TIMESTAMP}.log"

# Retention periods (in days)
readonly DAILY_RETENTION=7
readonly WEEKLY_RETENTION=30
readonly MONTHLY_RETENTION=365
readonly YEARLY_RETENTION=2555

# S3/Blob/GCS bucket for remote backups
REMOTE_BUCKET=""
REMOTE_PROVIDER="s3"  # s3, azblob, gs
ENCRYPTION_KEY=""
SKIP_REMOTE=false
SKIP_LOCAL=false

log()   { echo "[$(date +%H:%M:%S)] $*" | tee -a "${LOG_FILE}"; }
error() { echo "[ERROR] $*" | tee -a "${LOG_FILE}" >&2; }
warn()  { echo "[WARN] $*" | tee -a "${LOG_FILE}"; }

usage() {
    cat <<EOF
Zambia Health - Database Backup Script

Usage: $(basename "$0") [options]

Options:
  -t, --type TYPE       Backup type: full|incremental|wal|redis (default: full)
  -d, --db-url URL      PostgreSQL database URL
  -r, --redis-url URL   Redis connection URL
  -b, --bucket URL      Remote backup bucket (s3://, azblob://, gs://)
  -p, --provider PROV   Remote storage provider: s3|azblob|gs (default: s3)
  -k, --key PATH        Encryption key file
  -e, --encrypt         Enable encryption
      --skip-remote     Skip remote upload
      --skip-local      Skip local backup
  -h, --help           Show this help message

Examples:
  $(basename "$0") --type full --db-url postgresql://user:pass@host:5432/db
  $(basename "$0") --type redis --redis-url redis://user:pass@host:6379
EOF
    exit 0
}

parse_args() {
    BACKUP_TYPE="full"
    while [[ $# -gt 0 ]]; do
        case "$1" in
            -t|--type)         BACKUP_TYPE="$2"; shift 2 ;;
            -d|--db-url)       DATABASE_URL="$2"; shift 2 ;;
            -r|--redis-url)    REDIS_URL="$2"; shift 2 ;;
            -b|--bucket)       REMOTE_BUCKET="$2"; shift 2 ;;
            -p|--provider)     REMOTE_PROVIDER="$2"; shift 2 ;;
            -k|--key)          ENCRYPTION_KEY="$2"; shift 2 ;;
            -e|--encrypt)      ENCRYPT=true ;;
            --skip-remote)     SKIP_REMOTE=true ;;
            --skip-local)      SKIP_LOCAL=true ;;
            -h|--help)         usage ;;
            *)                 error "Unknown option: $1"; usage ;;
        esac
    done

    case "${BACKUP_TYPE}" in
        full|incremental|wal|redis) ;;
        *) error "Invalid backup type: ${BACKUP_TYPE}"; exit 1 ;;
    esac
}

check_prerequisites() {
    mkdir -p "${BACKUP_DIR}"
    mkdir -p "$(dirname "${LOG_FILE}")"

    command -v pg_dump >/dev/null 2>&1 || { error "pg_dump required (install postgresql-client)"; exit 1; }
    command -v redis-cli >/dev/null 2>&1 || { error "redis-cli required"; exit 1; }
    command -v gzip >/dev/null 2>&1 || { error "gzip required"; exit 1; }
}

backup_postgres_full() {
    log "Starting full PostgreSQL backup..."

    local output_file="${BACKUP_DIR}/zambia-health-postgres-full-${TIMESTAMP}.dump"

    PGPASSWORD="${DB_PASSWORD}" pg_dump \
        --dbname="${DATABASE_URL}" \
        --format=custom \
        --compress=9 \
        --verbose \
        --no-owner \
        --no-privileges \
        --file="${output_file}" \
        2>>"${LOG_FILE}"

    if [[ $? -eq 0 ]]; then
        local size
        size=$(du -h "${output_file}" | cut -f1)
        log "Full backup complete: ${output_file} (${size})"

        # Generate checksum
        sha256sum "${output_file}" > "${output_file}.sha256"

        # Create global objects backup
        PGPASSWORD="${DB_PASSWORD}" pg_dumpall \
            --dbname="${DATABASE_URL}" \
            --globals-only \
            --file="${BACKUP_DIR}/zambia-health-globals-${TIMESTAMP}.sql" \
            2>>"${LOG_FILE}"
    else
        error "Full backup failed"
        return 1
    fi

    # Backup pgvector extensions metadata
    PGPASSWORD="${DB_PASSWORD}" psql \
        "${DATABASE_URL}" \
        -c "SELECT * FROM pg_extension WHERE extname = 'vector';" \
        > "${BACKUP_DIR}/pgvector-extensions-${TIMESTAMP}.txt" \
        2>>"${LOG_FILE}"
}

backup_postgres_wal() {
    log "Starting WAL archive backup..."

    local wal_dir="${BACKUP_ROOT}/wal"
    mkdir -p "${wal_dir}"

    # Archive current WAL segments
    PGPASSWORD="${DB_PASSWORD}" psql \
        "${DATABASE_URL}" \
        -c "SELECT pg_switch_wal();" \
        2>>"${LOG_FILE}"

    local wal_count
    wal_count=$(find "${PGDATA:-/var/lib/postgresql/data}/pg_wal" -name "*.gz" -type f 2>/dev/null | wc -l)
    log "WAL segments archived: ${wal_count}"
}

backup_redis() {
    log "Starting Redis backup..."

    local output_file="${BACKUP_DIR}/zambia-health-redis-${TIMESTAMP}.rdb"
    local redis_cmd="redis-cli"

    if [[ -n "${REDIS_URL:-}" ]]; then
        redis_cmd="redis-cli -u \"${REDIS_URL}\""
    fi

    # Trigger Redis save
    eval "${redis_cmd} SAVE" 2>>"${LOG_FILE}"

    # Get Redis config for dump file location
    local dump_dir
    dump_dir=$(eval "${redis_cmd} CONFIG GET dir" | tail -1)
    local dump_file="${dump_dir}/dump.rdb"

    if [[ -f "${dump_file}" ]]; then
        cp "${dump_file}" "${output_file}"
        gzip "${output_file}"
        sha256sum "${output_file}.gz" > "${output_file}.gz.sha256"
        log "Redis backup complete: ${output_file}.gz ($(du -h ${output_file}.gz | cut -f1))"
    else
        warn "Redis dump file not found at ${dump_file}"
        # Attempt backup via --rdb
        eval "${redis_cmd} --rdb ${output_file}" 2>>"${LOG_FILE}"
        gzip "${output_file}"
        log "Redis backup via --rdb complete"
    fi
}

encrypt_backup() {
    if [[ "${ENCRYPT:-false}" != "true" ]]; then
        return 0
    fi

    log "Encrypting backup files..."

    local key_file="${ENCRYPTION_KEY:-/etc/zambia-health/backup-key.gpg}"

    if [[ ! -f "${key_file}" ]]; then
        # Generate encryption key
        openssl rand -base64 32 > "${key_file}"
        chmod 600 "${key_file}"
        log "Generated new encryption key: ${key_file}"
    fi

    # Encrypt all backup files
    find "${BACKUP_DIR}" -type f ! -name "*.gpg" ! -name "*.sha256" | while read -r f; do
        gpg --batch --yes \
            --symmetric \
            --cipher-algo AES256 \
            --passphrase-file "${key_file}" \
            --output "${f}.gpg" \
            "${f}" 2>>"${LOG_FILE}"
        rm "${f}"
        log "Encrypted: ${f}.gpg"
    done
}

upload_remote() {
    if [[ "${SKIP_REMOTE}" == "true" ]]; then
        log "Skipping remote upload"
        return 0
    fi

    if [[ -z "${REMOTE_BUCKET}" ]]; then
        warn "No remote bucket configured, skipping upload"
        return 0
    fi

    log "Uploading to remote storage (${REMOTE_PROVIDER})..."
    log "  Bucket: ${REMOTE_BUCKET}"

    case "${REMOTE_PROVIDER}" in
        s3)
            aws s3 sync "${BACKUP_DIR}" "${REMOTE_BUCKET}/$(date +%Y/%m/%d)/" \
                --sse aws:kms \
                --storage-class STANDARD_IA \
                --only-show-errors
            ;;
        azblob)
            az storage blob upload-batch \
                --destination "${REMOTE_BUCKET}/$(date +%Y/%m/%d)" \
                --source "${BACKUP_DIR}" \
                --no-progress
            ;;
        gs)
            gsutil -m rsync -r "${BACKUP_DIR}" "${REMOTE_BUCKET}/$(date +%Y/%m/%d)/"
            ;;
    esac

    log "Remote upload complete"
}

cleanup_old_backups() {
    log "Cleaning up old backups..."

    # Daily: keep 7 days
    find "${BACKUP_ROOT}" -maxdepth 1 -type d -name "20*" -mtime +"${DAILY_RETENTION}" -exec rm -rf {} + 2>/dev/null || true

    # WAL cleanup
    find "${BACKUP_ROOT}/wal" -type f -mtime +${WEEKLY_RETENTION} -delete 2>/dev/null || true

    log "Cleanup complete"
}

validate_backup() {
    log "Validating backup integrity..."
    local failed=0

    # Verify checksums
    find "${BACKUP_DIR}" -name "*.sha256" | while read -r sha; do
        local target="${sha%.sha256}"
        if [[ -f "${target}" ]]; then
            if sha256sum -c "${sha}" --strict >/dev/null 2>&1; then
                log "  OK: ${target}"
            else
                error "  CHECKSUM MISMATCH: ${target}"
                failed=1
            fi
        fi
    done

    # Test dump file validity
    for dump in "${BACKUP_DIR}"/*.dump; do
        if [[ -f "${dump}" ]]; then
            if pg_restore --list "${dump}" >/dev/null 2>&1; then
                log "  Valid dump: ${dump}"
            else
                error "  CORRUPT DUMP: ${dump}"
                failed=1
            fi
        fi
    done

    if [[ ${failed} -eq 0 ]]; then
        log "Backup validation passed"
    else
        error "Backup validation found errors"
    fi
}

main() {
    parse_args "$@"
    check_prerequisites

    log "=== Zambia Health Backup ==="
    log "Type: ${BACKUP_TYPE}"
    log "Timestamp: ${TIMESTAMP}"
    log ""

    case "${BACKUP_TYPE}" in
        full) backup_postgres_full ;;
        wal) backup_postgres_wal ;;
        redis) backup_redis ;;
        incremental) backup_postgres_full ;;  # For simplicity, full backup as base
    esac

    encrypt_backup
    upload_remote
    validate_backup
    cleanup_old_backups

    log ""
    log "=== Backup completed ==="
    log "Location: ${BACKUP_DIR}"
}

main "$@"
