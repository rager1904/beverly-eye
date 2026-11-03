#!/usr/bin/env bash
set -euo pipefail

#=============================================================================
# Zambia Health Platform - Database Restore Script
# Restores PostgreSQL and Redis from backup files
#=============================================================================

readonly SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
readonly TIMESTAMP=$(date +%Y%m%d-%H%M%S)
readonly LOG_FILE="/var/log/zambia-health/restore-${TIMESTAMP}.log"

RESTORE_FILE=""
BACKUP_DIR="/data/backups/zambia-health"
TARGET_DATABASE_URL=""
TARGET_REDIS_URL=""
DECRYPT_KEY=""
DRY_RUN=false
FORCE=false

log()   { echo "[$(date +%H:%M:%S)] $*" | tee -a "${LOG_FILE}"; }
error() { echo "[ERROR] $*" | tee -a "${LOG_FILE}" >&2; }
warn()  { echo "[WARN] $*" | tee -a "${LOG_FILE}"; }

usage() {
    cat <<EOF
Zambia Health - Database Restore Script

Usage: $(basename "$0") [options]

Options:
  -f, --file PATH       Backup file to restore (dump file)
  -d, --db-url URL      Target PostgreSQL database URL
  -r, --redis-url URL   Target Redis URL
  -b, --backup-dir DIR  Backup directory (default: /data/backups/zambia-health)
  -k, --key PATH        Decryption key file
  -l, --list           List available backups
  -n, --dry-run        Preview restore (no changes)
      --force          Force restore (skip confirmations)
  -h, --help           Show this help message

Examples:
  $(basename "$0") --file /data/backups/zambia-health/db-20240101.dump --db-url postgresql://...
  $(basename "$0") --list
EOF
    exit 0
}

parse_args() {
    ACTION="restore"
    while [[ $# -gt 0 ]]; do
        case "$1" in
            -f|--file)         RESTORE_FILE="$2"; shift 2 ;;
            -d|--db-url)       TARGET_DATABASE_URL="$2"; shift 2 ;;
            -r|--redis-url)    TARGET_REDIS_URL="$2"; shift 2 ;;
            -b|--backup-dir)   BACKUP_DIR="$2"; shift 2 ;;
            -k|--key)          DECRYPT_KEY="$2"; shift 2 ;;
            -l|--list)         ACTION="list"; shift ;;
            -n|--dry-run)      DRY_RUN=true; shift ;;
            --force)           FORCE=true; shift ;;
            -h|--help)         usage ;;
            *)                 error "Unknown option: $1"; usage ;;
        esac
    done
}

check_prerequisites() {
    command -v pg_restore >/dev/null 2>&1 || { error "pg_restore required"; exit 1; }
    command -v redis-cli >/dev/null 2>&1 || { error "redis-cli required"; exit 1; }
    mkdir -p "$(dirname "${LOG_FILE}")"
}

list_backups() {
    log "Available backups in ${BACKUP_DIR}:"
    echo ""

    find "${BACKUP_DIR}" -maxdepth 2 -type f \( -name "*.dump" -o -name "*.dump.gz" -o -name "*.dump.gpg" \) | sort -r | while read -r f; do
        local size=$(du -h "${f}" 2>/dev/null | cut -f1)
        local date=$(date -r "${f}" "+%Y-%m-%d %H:%M:%S" 2>/dev/null || echo "unknown")
        printf "  %-70s %10s  %s\n" "$(basename "${f}")" "${size}" "${date}"
    done
    exit 0
}

decrypt_backup() {
    local input_file="$1"
    local output_file="${input_file%.gpg}"

    if [[ ! "${input_file}" =~ \.gpg$ ]]; then
        echo "${input_file}"
        return 0
    fi

    local key_file="${DECRYPT_KEY:-/etc/zambia-health/backup-key.gpg}"
    if [[ ! -f "${key_file}" ]]; then
        error "Decryption key not found: ${key_file}"
        exit 1
    fi

    log "Decrypting ${input_file}..."
    gpg --batch --yes \
        --decrypt \
        --passphrase-file "${key_file}" \
        --output "${output_file}" \
        "${input_file}" 2>>"${LOG_FILE}"

    echo "${output_file}"
}

confirm_restore() {
    if [[ "${FORCE}" == "true" ]]; then
        return 0
    fi

    echo ""
    warn "!!! DANGER: This will overwrite data in the target database !!!"
    echo ""
    read -rp "Type 'RESTORE' to confirm: " confirmation
    if [[ "${confirmation}" != "RESTORE" ]]; then
        log "Restore cancelled"
        exit 0
    fi
}

restore_postgres() {
    if [[ -z "${TARGET_DATABASE_URL}" ]]; then
        error "Target database URL required (--db-url)"
        exit 1
    fi

    local restore_file="${RESTORE_FILE}"

    # Decrypt if needed
    restore_file=$(decrypt_backup "${restore_file}")

    # Decompress if needed
    case "${restore_file}" in
        *.gz) gunzip -kf "${restore_file}"; restore_file="${restore_file%.gz}" ;;
    esac

    log "Restoring PostgreSQL from ${restore_file}..."

    if [[ "${DRY_RUN}" == "true" ]]; then
        log "DRY-RUN: Would run pg_restore with:"
        log "  pg_restore --dbname=${TARGET_DATABASE_URL} --clean --if-exists ${restore_file}"
        return 0
    fi

    # Terminate active connections
    PGPASSWORD="${DB_PASSWORD}" psql "${TARGET_DATABASE_URL}" \
        -c "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname = current_database() AND pid <> pg_backend_pid();" \
        2>>"${LOG_FILE}" || true

    # Restore
    if PGPASSWORD="${DB_PASSWORD}" pg_restore \
        --dbname="${TARGET_DATABASE_URL}" \
        --clean \
        --if-exists \
        --no-owner \
        --no-privileges \
        --verbose \
        --exit-on-error \
        "${restore_file}" 2>>"${LOG_FILE}"; then
        log "PostgreSQL restore completed successfully"
    else
        error "PostgreSQL restore failed"
        return 1
    fi

    # Verify
    log "Verifying restore..."
    PGPASSWORD="${DB_PASSWORD}" psql "${TARGET_DATABASE_URL}" \
        -c "SELECT count(*) FROM pg_stat_user_tables;" \
        2>>"${LOG_FILE}" || true
    PGPASSWORD="${DB_PASSWORD}" psql "${TARGET_DATABASE_URL}" \
        -c "SELECT extname FROM pg_extension;" \
        2>>"${LOG_FILE}" || true
}

restore_redis() {
    if [[ -z "${TARGET_REDIS_URL}" ]]; then
        error "Target Redis URL required (--redis-url)"
        exit 1
    fi

    local restore_file="${RESTORE_FILE}"

    # Decrypt if needed
    restore_file=$(decrypt_backup "${restore_file}")

    # Decompress if needed
    case "${restore_file}" in
        *.gz) gunzip -kf "${restore_file}"; restore_file="${restore_file%.gz}" ;;
    esac

    log "Restoring Redis from ${restore_file}..."

    if [[ "${DRY_RUN}" == "true" ]]; then
        log "DRY-RUN: Would restore RDB file and restart Redis"
        return 0
    fi

    confirm_restore

    # Copy RDB file to Redis data directory
    local redis_dir
    redis_dir=$(redis-cli -u "${TARGET_REDIS_URL}" CONFIG GET dir | tail -1)
    local redis_dbfilename
    redis_dbfilename=$(redis-cli -u "${TARGET_REDIS_URL}" CONFIG GET dbfilename | tail -1)

    # Stop Redis, replace RDB, start Redis
    systemctl stop redis 2>/dev/null || service redis stop 2>/dev/null || true
    cp "${restore_file}" "${redis_dir}/${redis_dbfilename}"
    chown redis:redis "${redis_dir}/${redis_dbfilename}"
    systemctl start redis 2>/dev/null || service redis start 2>/dev/null || true

    sleep 2

    # Verify
    if redis-cli -u "${TARGET_REDIS_URL}" PING >/dev/null 2>&1; then
        log "Redis restore completed successfully"
    else
        error "Redis restore failed - service may not have started"
    fi
}

validate_backup_file() {
    if [[ ! -f "${RESTORE_FILE}" ]]; then
        error "Backup file not found: ${RESTORE_FILE}"
        exit 1
    fi

    # Check checksum
    local sha_file="${RESTORE_FILE}.sha256"
    if [[ -f "${sha_file}" ]]; then
        if sha256sum -c "${sha_file}" --strict >/dev/null 2>&1; then
            log "Checksum verification passed"
        else
            error "Checksum verification FAILED"
            exit 1
        fi
    else
        warn "No checksum file found for ${RESTORE_FILE}"
    fi

    # Validate dump format
    case "${RESTORE_FILE}" in
        *.dump|*.dump.gz|*.dump.gpg)
            local temp_file="${RESTORE_FILE}"
            case "${temp_file}" in
                *.gz) gunzip -c "${temp_file}" | pg_restore --list >/dev/null 2>&1 || {
                    warn "Not a valid PostgreSQL dump format (may be encrypted)"
                } ;;
                *) pg_restore --list "${temp_file}" >/dev/null 2>&1 || {
                    warn "Not a valid PostgreSQL dump format (may be encrypted)"
                } ;;
            esac
            ;;
    esac
}

main() {
    parse_args "$@"
    check_prerequisites

    if [[ "${ACTION}" == "list" ]]; then
        list_backups
    fi

    log "=== Zambia Health Restore ==="
    log "File: ${RESTORE_FILE}"
    log "Timestamp: ${TIMESTAMP}"
    log ""

    if [[ -z "${RESTORE_FILE}" ]]; then
        error "No restore file specified"
        usage
    fi

    validate_backup_file

    confirm_restore

    case "${RESTORE_FILE}" in
        *.rdb|*.rdb.gz|*.rdb.gpg) restore_redis ;;
        *.dump|*.dump.gz|*.dump.gpg) restore_postgres ;;
        *)
            # Try to detect type
            if [[ -n "${TARGET_DATABASE_URL}" ]]; then
                restore_postgres
            elif [[ -n "${TARGET_REDIS_URL}" ]]; then
                restore_redis
            else
                error "Cannot determine restore type. Use --db-url or --redis-url"
                exit 1
            fi
            ;;
    esac

    log ""
    log "=== Restore completed ==="
}

main "$@"
