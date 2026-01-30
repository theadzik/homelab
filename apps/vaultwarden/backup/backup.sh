#!/bin/sh
set -e

# https://github.com/dani-garcia/vaultwarden/wiki/Backing-up-your-vault
# https://github.com/rclone/rclone/issues/3655

log() {
  echo "[$(date '+%F-%H:%M:%S')] $1"
}

DATADIR="${DATADIR:-/data}"
BACKUP_LOCAL_DIR="${BACKUP_LOCAL_DIR:-/backup}"
BACKUP_REMOTE_DIR="${BACKUP_REMOTE_DIR:-gdrive:backup}"
TEMP_DIR="${TEMP_DIR:-/tmp/vaultwarden-backup}"
BACKUP_FILE="vaultwarden-$(date "+%F--%H%M")"

# Validate prerequisites
[ -n "$BACKUP_ENCRYPTION_KEY" ] || { log "ERROR: BACKUP_ENCRYPTION_KEY not set"; exit 1; }
[ -f "$DATADIR/db.sqlite3" ] || { log "ERROR: Database not found at $DATADIR/db.sqlite3"; exit 1; }
[ -d "$BACKUP_LOCAL_DIR" ] || { log "ERROR: BACKUP_LOCAL_DIR $BACKUP_LOCAL_DIR does not exist"; exit 1; }

mkdir -p "$TEMP_DIR"

log "Backing up SQLite database..."
sqlite3 "$DATADIR/db.sqlite3" ".backup '$TEMP_DIR/db.sqlite3'"
log "SQLite DB backup complete"

log "Compressing and encrypting..."
tar -czf - -C "$TEMP_DIR" db.sqlite3 --directory="$DATADIR" attachments 2>/dev/null \
  | openssl enc -e -aes256 -salt -pbkdf2 \
  -pass "env:BACKUP_ENCRYPTION_KEY" \
  -out "$BACKUP_LOCAL_DIR/$BACKUP_FILE.tar.gz"

[ -f "$BACKUP_LOCAL_DIR/$BACKUP_FILE.tar.gz" ] || { log "ERROR: Backup file not created"; exit 1; }
log "Files compressed and encrypted"

log "Backup stored locally at $BACKUP_LOCAL_DIR"

# Try to sync to remote storage if configured
if [ -n "$BACKUP_REMOTE_DIR" ] && [ "$BACKUP_REMOTE_DIR" != "$BACKUP_LOCAL_DIR" ]; then
  log "Uploading to remote storage: $BACKUP_REMOTE_DIR..."
  if rclone copy -v "$BACKUP_LOCAL_DIR/$BACKUP_FILE.tar.gz" "$BACKUP_REMOTE_DIR" 2>&1; then
    log "Backup uploaded successfully"
  else
    log "WARNING: Remote upload failed, backup exists locally at $BACKUP_LOCAL_DIR"
  fi
else
  log "Remote storage not configured, backup stored locally only"
fi
