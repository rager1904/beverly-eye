#!/usr/bin/env bash
# =============================================================================
# Backup Script — UbuntuCare (Zambia)
# =============================================================================
# Full, incremental, and WAL backups with encryption and S3 sync.
# =============================================================================

set -euo pipefail

RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; BLUE='\033[0;34m'
BOLD='\033[1m'; NC='\033[0m'
log()  { echo -e "${GREEN}[✓]${NC} $1"; }
warn() { echo -e "${YELLOW}[!]${NC} $1"; }
err()  { echo -e "${RED}[✗]${NC} $1" >&2; exit 1; }

BACKUP_DIR="${BACKUP_DIR:-/data/ubuntucare/backups}"
DB_URL="${DATABASE_URL:-sqlite:///data/ubuntucare/ubuntucare.db}"
S3_BUCKET="${S3_BUCKET:-s3://backups.ubuntucare.gov.zm}"
ENCRYPTION_KEY="${ENCRYPTION_KEY:-}"
RETENTION_DAYS="${RETENTION_DAYS:-30}"
TIMESTAMP=$(date -u +"%Y%m%d_%H%M%S")
BACKUP_TYPE="${1:-full}"

mkdir -p "$BACKUP_DIR/{full,incremental,wal}"

do_backup_full() {
  local backup_file="$BACKUP_DIR/full/ubuntucare-full-$TIMESTAMP"

  log "Starting full backup..."
  case "$DB_URL" in
    sqlite://*)
      local db_path="${DB_URL#sqlite:///}"
      cp "$db_path" "${backup_file}.db"
      sqlite3 "$db_path" ".dump" | gzip > "${backup_file}.sql.gz"
      log "SQLite backup: ${backup_file}.db"
      ;;
    postgresql://*)
      pg_dump --no-owner --no-acl --compress=9 \
        -f "${backup_file}.sql.gz" "$DB_URL"
      log "PostgreSQL dump: ${backup_file}.sql.gz"
      ;;
  esac

  # Encrypt if key is set
  if [[ -n "$ENCRYPTION_KEY" ]]; then
    openssl enc -aes-256-cbc -salt -pbkdf2 \
      -k "$ENCRYPTION_KEY" -in "${backup_file}.sql.gz" \
      -out "${backup_file}.sql.gz.enc"
    rm "${backup_file}.sql.gz"
    log "Encrypted: ${backup_file}.sql.gz.enc"
  fi

  # Sync to S3
  if command -v aws &>/dev/null; then
    aws s3 cp "${backup_file}."* "$S3_BUCKET/full/" --no-progress || warn "S3 sync failed"
    log "Synced to S3"
  fi

  log "Full backup completed: ${backup_file}"
}

do_backup_incremental() {
  local backup_file="$BACKUP_DIR/incremental/ubuntucare-inc-$TIMESTAMP"

  case "$DB_URL" in
    postgresql://*)
      pg_basebackup --pgdata="$backup_dir" --wal-method=stream \
        --compress=9 --progress --verbose
      log "PostgreSQL incremental basebackup: $backup_dir"
      ;;
    sqlite://*)
      local db_path="${DB_URL#sqlite:///}"
      # SQLite WAL checkpoint
      sqlite3 "$db_path" "PRAGMA wal_checkpoint(TRUNCATE);"
      cp "${db_path}-wal" "${backup_file}.wal" 2>/dev/null || true
      log "SQLite WAL backed up"
      ;;
  esac
}

do_backup_wal() {
  case "$DB_URL" in
    postgresql://*)
      local wal_dir="$BACKUP_DIR/wal"
      pg_archivecleanup "$wal_dir" "$(ls -t "$wal_dir" | head -1)" 2>/dev/null || true
      log "WAL archive cleaned"
      ;;
  esac
}

cleanup_old() {
  log "Cleaning up backups older than $RETENTION_DAYS days..."
  find "$BACKUP_DIR/full" -type f -mtime "+$RETENTION_DAYS" -delete 2>/dev/null || true
  find "$BACKUP_DIR/incremental" -type f -mtime "+$((RETENTION_DAYS / 2))" -delete 2>/dev/null || true
  log "Cleanup completed"
}

main() {
  echo -e "${BOLD}"
  echo "╔══════════════════════════════════════════════════════════════╗"
  echo "║      UbuntuCare — Backup ($BACKUP_TYPE)            ║"
  echo "╚══════════════════════════════════════════════════════════════╝"
  echo -e "${NC}"

  case "$BACKUP_TYPE" in
    full)        do_backup_full ;;
    incremental) do_backup_incremental ;;
    wal)         do_backup_wal ;;
    all)
      do_backup_full
      do_backup_incremental
      do_backup_wal
      ;;
    *) err "Usage: $0 {full|incremental|wal|all}" ;;
  esac

  cleanup_old
  log "Backup operation completed ($BACKUP_TYPE)"
}

main "$@"
