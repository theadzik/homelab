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
SQLITE_TIMEOUT="${SQLITE_TIMEOUT:-300}"
BACKUP_FILE="vaultwarden-$(date "+%F--%H%M")"

# Validate prerequisites
[ -n "$BACKUP_ENCRYPTION_KEY" ] || { log "ERROR: BACKUP_ENCRYPTION_KEY not set"; exit 1; }
[ -f "$DATADIR/db.sqlite3" ] || { log "ERROR: Database not found at $DATADIR/db.sqlite3"; exit 1; }
[ -d "$BACKUP_LOCAL_DIR" ] || { log "ERROR: BACKUP_LOCAL_DIR $BACKUP_LOCAL_DIR does not exist"; exit 1; }

mkdir -p "$TEMP_DIR"

log "Backing up SQLite database..."
# .backup restarts its copy whenever it sees the source change. If this pod is not
# on the same host as vaultwarden, WAL's -shm mmap is not coherent between them, the
# source never looks settled, and the restart loop spins on a full core forever. Cap
# it so the job fails visibly rather than wedging every later backup.
timeout "$SQLITE_TIMEOUT" sqlite3 "$DATADIR/db.sqlite3" ".backup '$TEMP_DIR/db.sqlite3'" || {
  log "ERROR: sqlite3 .backup failed or exceeded ${SQLITE_TIMEOUT}s (exit $?)"
  exit 1
}
log "SQLite DB backup complete"

log "Compressing and encrypting..."
# rsa_key.pem signs the session JWTs. It is not part of the vault's own encryption
# - losing it exposes nothing and decrypts nothing - but restoring without it makes
# Vaultwarden mint a new one, which invalidates every active session and every 2FA
# "remember this device" token. Restoring the vault and then logging every client
# out is a poor recovery, so the key travels with the data.
#
# Held in the positional parameters so the member list stays a single tar call:
# archives written before this change restore fine, and a data directory without
# the key still backs up rather than failing.
set -- --directory="$TEMP_DIR" db.sqlite3 --directory="$DATADIR" attachments
if [ -f "$DATADIR/rsa_key.pem" ]; then
  set -- "$@" rsa_key.pem
else
  log "WARNING: rsa_key.pem not found in $DATADIR; a restore from this backup will log every client out"
fi

tar -czf - "$@" 2>/dev/null \
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
