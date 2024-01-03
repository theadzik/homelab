# Setup

1. Schedule vaultwarden.sh (using cronjob in k8s)
2. Install `rclone` on rpi
3. Add `gdrive` drive with `rclone config`
4. Run `crontab -e` on rpi and add `5 */1 * * * /home/adzik/git/homelab/gdrive-upload.sh &>> /var/log/cron.log`

## Restore

1. Download the tar
2. ```bash
   BACKUP_ENCRYPTION_KEY='<the_password>'
   BACKUP_NAME='<name of the downloaded file>'
   openssl enc -d -aes256 -salt -pbkdf2 -pass pass:$BACKUP_ENCRYPTION_KEY -in /backup/$BACKUP_NAME | tar xz -C /backup
   ```
3. Stop vaultwarden
4. Replace `db.sqlite3` and `attachements`
5. Start vaultwarden
