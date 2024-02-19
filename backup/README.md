# Manual restore from backup

1. Stop vaultwarden `kubectl scale deployment -n vaultwarden --replicas=0 vaultwarden`
1. Find newest (and correct) backup `rclone ls gdrive:/backup`
1. Run the below script:

   ```bash
   BACKUP_ENCRYPTION_KEY='<the_password>'
   BACKUP_NAME='<newest backup name>'
   mv /home/adzik/docker/vw-data /home/adzik/docker/vw-data-old > /dev/null 2>&1
   mkdir /home/adzik/docker/vw-data
   cd /home/adzik/docker/vw-data
   rclone copy gdrive:backup/"$BACKUP_NAME" /home/adzik/docker/vw-data
   openssl enc -d -aes256 -salt -pbkdf2 -pass pass:"$BACKUP_ENCRYPTION_KEY" \
    -in /home/adzik/docker/vw-data/"$BACKUP_NAME" \
    | tar xz -C /home/adzik/docker/vw-data
   mv data/attachments/ attachments
   mv tmp/db.sqlite3 db.sqlite3
   rm "$BACKUP_NAME" tmp data -r
   ```

1. Start vaultwarden `kubectl scale deployment -n vaultwarden --replicas=1 vaultwarden`
