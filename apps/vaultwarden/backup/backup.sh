#!/bin/sh
set -e

# https://github.com/dani-garcia/vaultwarden/wiki/Backing-up-your-vault
# https://github.com/rclone/rclone/issues/3655

log() {
  echo "[$(date '+%F-%H:%M:%S')] $1"
}

DATADIR="${DATADIR:-/data}"
BACKUP_DIR="${BACKUP_DIR:-/backup}"
TEMP_DIR="${TEMP_DIR:-/tmp/vaultwarden-backup}"
BACKUP_FILE="vaultwarden-$(date "+%F--%H%M")"

# Validate prerequisites
[ -n "$BACKUP_ENCRYPTION_KEY" ] || { log "ERROR: BACKUP_ENCRYPTION_KEY not set"; exit 1; }
[ -f "$DATADIR/db.sqlite3" ] || { log "ERROR: Database not found at $DATADIR/db.sqlite3"; exit 1; }
[ -d "$BACKUP_DIR" ] || { log "ERROR: BACKUP_DIR $BACKUP_DIR does not exist"; exit 1; }

mkdir -p "$TEMP_DIR"

log "Backing up SQLite database..."
sqlite3 "$DATADIR/db.sqlite3" ".backup '$TEMP_DIR/db.sqlite3'"
log "SQLite DB backup complete"

log "Compressing and encrypting..."
tar -czf - -C "$TEMP_DIR" db.sqlite3 --directory="$DATADIR" attachments 2>/dev/null \
  | openssl enc -e -aes256 -salt -pbkdf2 \
  -pass "env:BACKUP_ENCRYPTION_KEY" \
  -out "$BACKUP_DIR/$BACKUP_FILE.tar.gz"

[ -f "$BACKUP_DIR/$BACKUP_FILE.tar.gz" ] || { log "ERROR: Backup file not created"; exit 1; }
log "Files compressed and encrypted"

log "Uploading to remote storage..."
rclone move -v "$BACKUP_DIR" gdrive:backup
log "Backup uploaded successfully"
