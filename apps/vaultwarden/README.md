# Vaultwarden Backup & Restore

This directory contains automated backup and restore scripts for Vaultwarden with AES-256 encryption, supporting both local Synology NFS storage and remote Google Drive backup.

## Architecture

- **Backup**: CronJob runs `backup.sh` to encrypt database + attachments, stores on Synology NFS, optionally syncs to Google Drive
- **Restore**: InitContainer (`restore.sh`) automatically restores database on pod startup if missing, tries Synology first, then Google Drive
- **Encryption**: AES-256 with PBKDF2, password passed securely via environment variable
- **Storage**: Synology NFS (primary) + Google Drive (remote backup)

## Files

- `backup/backup.sh` - Backs up SQLite DB + attachments, encrypts, stores on Synology, optionally syncs to Google Drive
- `restore/restore.sh` - Tries local Synology restore first, falls back to Google Drive
- `backup/Dockerfile` - Alpine image with sqlite3, openssl, rclone
- `restore/Dockerfile` - Alpine image with openssl, rclone

## Kubernetes Deployment

### StatefulSet (vaultwarden.yaml)

Mounts both data and backup PVCs:

```yaml
initContainers:
  - name: restore
    image: theadzik/vw-restore:2025.5.1
    volumeMounts:
      - mountPath: /data           # Main data volume
        name: data
      - mountPath: /backup         # Backup volume (Synology NFS)
        name: backup
      - mountPath: /home/vaultwarden
        name: rclone-conf
```

### CronJob Backup (backup.yaml)

Runs every 12 hours:

```yaml
volumes:
  - name: backup
    persistentVolumeClaim:
      claimName: vaultwarden-backup  # Synology NFS PVC
  - name: data
    persistentVolumeClaim:
      claimName: vaultwarden         # Main data PVC
```

Configures backup with:

```yaml
env:
  - name: BACKUP_LOCAL_DIR
    value: "/backup"                 # Synology mount
  - name: BACKUP_REMOTE_DIR
    value: "gdrive:backup"           # Google Drive (optional)
```

### Persistent Volume Claims

- `vaultwarden`: Main data (10GB iSCSI)
- `vaultwarden-backup`: Backup storage (10GB NFS)

Both use Synology storage with `retain` reclaim policy.

## Restore Behavior

**Automatic restore on pod startup:**

1. Checks if `/data/db.sqlite3` exists
2. If exists → Pod starts normally
3. If missing:
   - Looks for backups in `/backup` (Synology NFS)
   - If found → Restores from local backup
   - If not found → Downloads from `gdrive:backup` (Google Drive)
   - If both fail → Pod fails to start (prevents data loss)

**Priority order:**

1. Local Synology backup (fast, direct)
2. Remote Google Drive backup (fallback, slower)

## Secrets Required

1. **backup-encryption-secret** - Contains `BACKUP_ENCRYPTION_KEY` (AES-256 password)
2. **rclone-secret** - Contains rclone config for Google Drive access (optional for remote sync)

### rclone.conf Format (for Google Drive)

```text
[gdrive]
type = drive
scope = drive.file
token = {...}
team_drive =

```

## Backup Storage Locations

**Local Synology NFS** (`/backup`):

- Primary backup location
- Mounted via `vaultwarden-backup` PVC
- Fast, reliable, local network access
- Retains all backups (no automatic cleanup)

**Remote Google Drive** (`gdrive:backup`):

- Optional secondary location
- Synced via rclone after local backup
- Provides off-site redundancy
- Backup continues locally even if remote sync fails

## Environment Variables

### backup.sh

- `DATADIR` - Source data directory (default: `/data`)
- `BACKUP_LOCAL_DIR` - Local staging directory (default: `/backup`)
- `BACKUP_REMOTE_DIR` - Remote storage path (default: `gdrive:backup`)
- `TEMP_DIR` - Temporary working directory (default: `/tmp/vaultwarden-backup`)
- `BACKUP_ENCRYPTION_KEY` - **Required** AES-256 password

### restore.sh

- `DATADIR` - Restore destination (default: `/data`)
- `BACKUP_LOCAL_DIR` - Local backup directory (default: `/backup`)
- `BACKUP_REMOTE_DIR` - Remote backup location (default: `gdrive:backup`)
- `TEMP_DIR` - Temporary download directory (default: `/tmp/vaultwarden-restore`)
- `BACKUP_ENCRYPTION_KEY` - **Required** AES-256 password

## Security

- Scripts run as unprivileged user (UID 1000)
- Read-only root filesystem in containers
- Password passed via environment variable (not command line)
- AES-256-CBC with PBKDF2 key derivation
- All backups encrypted before storage or upload
- Network policies restrict traffic
