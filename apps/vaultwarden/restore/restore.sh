#!/bin/bash
# https://github.com/dani-garcia/vaultwarden/wiki/Backing-up-your-vault

DATADIR=/data
DATABASE="$DATADIR/db.sqlite3"
if [ -f "$DATABASE" ]; then
  echo "Database exists"
else
  echo "Database missing"
  backup_name=$(rclone lsf gdrive:backup | tail -1 | grep "vaultwarden-[0-9\-]*\.tar\.gz")
  echo "Newest backup: $backup_name"
  rclone copy -v gdrive:backup/"$backup_name" /tmp
  openssl enc -d -aes256 -salt -pbkdf2 -pass pass:"$BACKUP_ENCRYPTION_KEY" \
  -in /tmp/"$backup_name" \
  | tar xz --strip-components=1 --directory=$DATADIR
fi
