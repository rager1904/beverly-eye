#!/usr/bin/env bash
# =============================================================================
# Restore Script — UbuntuCare (Zambia)
# =============================================================================
# Restores from full, incremental, or point-in-time backups.
# =============================================================================

set -euo pipefail

RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; BLUE='\033[0;34m'
BOLD='\033[1m'; NC='\033[0m'
log()  { echo -e "${GREEN}[✓]${NC} $1"; }
warn() { echo -e "${YELLOW}[!]${NC} $1"; }
err()  { echo -e "${RED}[✗]${NC} $1" >&2; exit 1; }

BACKUP_DIR="${BACKUP_DIR:-/data/ubuntucare/backups}"
DB_URL="${DATABASE_URL:-sqlite:///data/ubuntucare/ubuntucare.db}"
ENCRYPTION_KEY="${ENCRYPTION_KEY:-}"
RESTORE_FILE="${1:-}"
RESTORE_TYPE="${2:-latest}"

find_latest_backup() {
  local type="${1:-full}"
  local pattern="$BACKUP_DIR/$type/ubuntucare-$type-*"
  ls -t $pattern 2>/dev/null | head -1
}

do_restore_full() {
  local backup_file
  if [[ -n "$RESTORE_FILE" ]]; then
    backup_file="$RESTORE_FILE"
  else
    backup_file=$(find_latest_backup "full")
  fi

  [[ -z "$backup_file" ]] && err "No backup file found to restore"

  log "Restoring from: $backup_file"
  local restore_path="$backup_file"

  # Decrypt if encrypted
  if [[ "$backup_file" == *.enc && -n "$ENCRYPTION_KEY" ]]; then
    restore_path="${backup_file%.enc}"
    openssl enc -d -aes-256-cbc -pbkdf2 \
      -k "$ENCRYPTION_KEY" -in "$backup_file" -out "$restore_path"
    log "Decrypted: $restore_path"
  fi

  case "$DB_URL" in
    sqlite://*)
      local db_path="${DB_URL#sqlite:///}"
      # Stop app, restore, restart
      if [[ "$restore_path" == *.db ]]; then
        cp "$restore_path" "$db_path"
      elif [[ "$restore_path" == *.sql.gz ]]; then
        gunzip -c "$restore_path" | sqlite3 "$db_path"
      fi
      log "Restored SQLite database"
      ;;
    postgresql://*)
      if [[ "$restore_path" == *.sql.gz ]]; then
        gunzip -c "$restore_path" | psql "$DB_URL"
      fi
      log "Restored PostgreSQL database"
      ;;
  esac

  log "Restore completed successfully"
}

do_restore_point_in_time() {
  local target_time="${1:-$(date -u -d '1 hour ago' +'%Y-%m-%d %H:%M:%S')}"
  log "Restoring to point in time: $target_time"

  case "$DB_URL" in
    postgresql://*)
      pg_restore --dbname="$DB_URL" --time-target="$target_time" \
        --use-set-session-authorization --jobs=4 \
        "$BACKUP_DIR/wal" || warn "PITR restore had issues"
      log "Point-in-time recovery initiated"
      ;;
    sqlite://*)
      warn "Point-in-time recovery not available for SQLite"
      ;;
  esac
}

main() {
  echo -e "${BOLD}"
  echo "╔══════════════════════════════════════════════════════════════╗"
  echo "║     UbuntuCare — Database Restore (Zambia)          ║"
  echo "╚══════════════════════════════════════════════════════════════╝"
  echo -e "${NC}"

  local restore_type="${RESTORE_TYPE:-full}"
  case "$restore_type" in
    full|latest)   do_restore_full ;;
    pitr)          do_restore_point_in_time "${2:-}" ;;
    list)          log "Available backups:"; ls -lh "$BACKUP_DIR/full/" 2>/dev/null || info "No backups found" ;;
    *) err "Usage: $0 [file] {full|pitr|list}" ;;
  esac
}

main "$@"
