#!/bin/bash
# https://github.com/dani-garcia/vaultwarden/wiki/Backing-up-your-vault
# https://github.com/rclone/rclone/issues/3655

DATADIR=/data
DATABASE="$DATADIR/db.sqlite3"
if [ -f "$DATABASE" ]; then
  echo "$(date "+%F-%H:%M:%S") Database exists"
else
  echo "$(date "+%F-%H:%M:%S") Database missing"
  backup_name=$(rclone lsf gdrive:backup | tail -1 | grep "vaultwarden-[0-9\-]*\.tar\.gz")
  echo "$(date "+%F-%H:%M:%S") Newest backup: $backup_name"
  rclone copy -v gdrive:backup/"$backup_name" /tmp
  openssl enc -d -aes256 -salt -pbkdf2 -pass pass:"$BACKUP_ENCRYPTION_KEY" \
  -in /tmp/"$backup_name" \
  | tar xz --strip-components=1 --directory=$DATADIR
  echo "$(date "+%F-%H:%M:%S") Database extracted"
fi
