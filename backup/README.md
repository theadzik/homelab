# Setup

1. Schedule vaultwarden.sh (using cronjob in k8s)
2. Install `rclone` on rpi
3. Add `gdrive` drive with `rclone config`
4. Run `crontab -e` on rpi and add `5 */6 * * * /home/adzik/git/homelab/gdrive-upload.sh &>> /var/log/cron.log`

## Restore

1. Stop vaultwarden `kubectl scale deployment -n vaultwarden --replicas=0 vaultwarden`
2. Find newest (and correct) backup `rclone ls gdrive:/backup`
3. ```bash
   BACKUP_ENCRYPTION_KEY='<the_password>'
   BACKUP_NAME='<newest backup name>'
   mv /home/adzik/docker/vw-data /home/adzik/docker/vw-data-old > /dev/null 2>&1
   mkdir /home/adzik/docker/vw-data
   cd /home/adzik/docker/vw-data
   rclone copy gdrive:backup/$BACKUP_NAME /home/adzik/docker/vw-data
   openssl enc -d -aes256 -salt -pbkdf2 -pass pass:$BACKUP_ENCRYPTION_KEY -in /home/adzik/docker/vw-data/$BACKUP_NAME | tar xz -C /home/adzik/docker/vw-data
   mv data/attachments/ attachments
   mv tmp/db.sqlite3 db.sqlite3
   rm $BACKUP_NAME tmp data -r
   ```
4. Start vaultwarden `kubectl scale deployment -n vaultwarden --replicas=1 vaultwarden`
