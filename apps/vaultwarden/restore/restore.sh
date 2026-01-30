#!/bin/sh
set -e

# https://github.com/dani-garcia/vaultwarden/wiki/Backing-up-your-vault
# https://github.com/rclone/rclone/issues/3655

log() {
  echo "[$(date '+%F-%H:%M:%S')] $1"
}

DATADIR="${DATADIR:-/data}"
DATABASE="$DATADIR/db.sqlite3"
BACKUP_DIR="${BACKUP_DIR:-gdrive:backup}"
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

log "Searching for backups in $BACKUP_DIR..."
backup_name=$(rclone lsf "$BACKUP_DIR" 2>/dev/null | grep -E '^vaultwarden-[0-9-]+\.tar\.gz$' | tail -1)

[ -n "$backup_name" ] || { log "ERROR: No valid backups found"; exit 1; }
log "Found backup: $backup_name"

log "Downloading backup..."
rclone copy -v "$BACKUP_DIR/$backup_name" "$TEMP_DIR"

log "Decrypting and extracting..."
openssl enc -d -aes256 -salt -pbkdf2 \
  -pass "env:BACKUP_ENCRYPTION_KEY" \
  -in "$TEMP_DIR/$backup_name" | tar xz --directory="$DATADIR" --strip-components=1

[ -f "$DATABASE" ] || { log "ERROR: Database not found after extraction"; exit 1; }
log "Database restored successfully"
