#!/bin/sh
set -e

# https://github.com/dani-garcia/vaultwarden/wiki/Backing-up-your-vault
# https://github.com/rclone/rclone/issues/3655

log() {
  echo "[$(date '+%F-%H:%M:%S')] $1"
}

verify_restore() {
  [ -f "$DATABASE" ] || { log "ERROR: Database not found after extraction"; exit 1; }
}

restore_archive() {
  archive_path="$1"
  source_name="$2"

  log "Decrypting and extracting from $source_name backup..."
  openssl enc -d -aes256 -salt -pbkdf2 \
    -pass "env:BACKUP_ENCRYPTION_KEY" \
    -in "$archive_path" | tar xz --directory="$DATADIR"

  verify_restore
  log "Database restored successfully from $source_name backup"
}

find_latest_local_backup() {
  find "$BACKUP_LOCAL_DIR" -name 'vaultwarden-*.tar.gz' -type f 2>/dev/null | tail -1
}

find_latest_remote_backup() {
  rclone lsf "$BACKUP_REMOTE_DIR" 2>/dev/null | grep -E '^vaultwarden-[0-9-]+\.tar\.gz$' | tail -1
}

DATADIR="${DATADIR:-/data}"
DATABASE="$DATADIR/db.sqlite3"
BACKUP_LOCAL_DIR="${BACKUP_LOCAL_DIR:-/backup}"
BACKUP_REMOTE_DIR="${BACKUP_REMOTE_DIR:-gdrive:backup}"
TEMP_DIR="/tmp/vaultwarden-restore"

# Validate prerequisites
[ -n "$BACKUP_ENCRYPTION_KEY" ] || { log "ERROR: BACKUP_ENCRYPTION_KEY not set"; exit 1; }
[ -d "$DATADIR" ] || { log "ERROR: DATADIR $DATADIR does not exist"; exit 1; }

if [ -f "$DATABASE" ]; then
  log "Database already exists at $DATABASE"
  exit 0
fi

log "Database missing, attempting restore..."
mkdir -p "$TEMP_DIR"

# Try to find and restore from local backup first
if [ -d "$BACKUP_LOCAL_DIR" ]; then
  local_backup=$(find_latest_local_backup)

  if [ -n "$local_backup" ]; then
  log "Found local backups in $BACKUP_LOCAL_DIR, attempting local restore..."
    log "Found backup: ${local_backup##*/}"

    if restore_archive "$local_backup" "local"; then
      exit 0
    fi

    log "WARNING: Local restore failed, will try remote storage..."
  fi
fi

# Fall back to remote storage (Google Drive, etc.)
log "Searching for backups in remote storage: $BACKUP_REMOTE_DIR..."
backup_name=$(find_latest_remote_backup)

[ -n "$backup_name" ] || { log "ERROR: No valid backups found locally or remotely"; exit 1; }
log "Found backup: $backup_name"

log "Downloading backup from remote storage..."
rclone copy -v "$BACKUP_REMOTE_DIR/$backup_name" "$TEMP_DIR"

restore_archive "$TEMP_DIR/$backup_name" "remote"
