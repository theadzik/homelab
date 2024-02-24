# Manual restore from backup

1. Stop vaultwarden `kubectl scale statefulset -n vaultwarden --replicas=0 vaultwarden`
1. Find a correct backup `rclone ls gdrive:/backup` from the list.
   > Last one with a removed password, or non-corrupted file.
1. Run the below script:

   ```bash
   BACKUP_ENCRYPTION_KEY='<the_password>'
   BACKUP_NAME='<newest_working_backup>'
   mv /mnt/kubernetes-disks/vaultwarden/main /tmp/vaultwarden > /dev/null 2>&1
   mkdir /mnt/kubernetes-disks/vaultwarden/main
   rclone copy gdrive:backup/"$BACKUP_NAME" /tmp
   openssl enc -d -aes256 -salt -pbkdf2 -pass pass:"$BACKUP_ENCRYPTION_KEY" \
   -in /tmp/"$BACKUP_NAME" \
   | tar xz --strip-components=1 --owner=10001 --group=20002 \
   --directory=/mnt/kubernetes-disks/vaultwarden/main
   ```

1. Start vaultwarden `kubectl scale statefulset -n vaultwarden --replicas=1 vaultwarden`
