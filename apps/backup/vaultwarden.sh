#!/bin/sh
# https://github.com/dani-garcia/vaultwarden/wiki/Backing-up-your-vault

set -e
BACKUP_FILE="vaultwarden-$(date "+%F--%H%M")"

sqlite3 /data/db.sqlite3 ".backup '/tmp/db.sqlite3'"
echo "$(date "+%F-%H:%M:%S") SQLite DB done"
tar -czf - tmp/db.sqlite3 data/attachments \
  | openssl enc -e -aes256 -salt -pbkdf2 -pass pass:"${BACKUP_ENCRYPTION_KEY}" -out /backup/"${BACKUP_FILE}".tar.gz
echo "$(date "+%F-%H:%M:%S") Files compressed and encrypted"

/usr/local/bin/rclone move -v /backup gdrive:backup
echo "$(date "+%F-%H:%M:%S") Files uploaded"
