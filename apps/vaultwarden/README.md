# Vaultwarden backup and restore

Two small images that give Vaultwarden an encrypted, off-site backup and an unattended
restore. The Kubernetes manifests that use them are in
[`kubernetes/kustomizations/vaultwarden/`](../../kubernetes/kustomizations/vaultwarden/).
The wider backup story is in
[Storage and backups](../../docs/storage-and-backups.md#application-level-backup-vaultwarden).

| Image | Runs as | Entry point |
| --- | --- | --- |
| `ghcr.io/theadzik/vw-backup` | CronJob, every 12 hours | [`backup/backup.sh`](backup/backup.sh) |
| `ghcr.io/theadzik/vw-restore` | initContainer on every pod start | [`restore/restore.sh`](restore/restore.sh) |

## Backup

```text
sqlite3 .backup  →  tar -czf (db + attachments)  →  openssl aes256, PBKDF2  →  /backup
                                                                            →  rclone copy → gdrive:backup
```

`sqlite3 .backup` instead of copying the file. A live SQLite database copied byte-for-byte
can be mid-transaction, and the backup API produces a consistent snapshot without stopping
Vaultwarden.

The archive is encrypted before it is written anywhere, so neither the NAS nor Google Drive
ever holds plaintext. The key arrives as `BACKUP_ENCRYPTION_KEY` from a git-crypt encrypted
secret, passed to OpenSSL as `-pass env:` so it never appears in a process argument list.

A failed upload to the remote is a warning, not a failure. The local copy already exists,
and failing the job would mean a red CronJob for a condition that has not lost anything.
Every other step is fatal, and `backoffLimit: 0` means a failed run stays visible instead of
being retried into a loop.

## Restore

The init container decides on its own, and the order encodes what is cheapest and most
trustworthy:

1. `/data/db.sqlite3` exists → do nothing, let Vaultwarden start.
2. Newest archive on the NAS → decrypt and extract.
3. Newest archive on Google Drive → download, decrypt and extract.
4. Nothing found, or extraction produced no database → **exit non-zero, so the pod does not
   start.**

Step 4 is why the script exists in this shape. A Vaultwarden that starts on an empty volume
looks healthy, serves an empty vault, and lets the first client to sync overwrite the only
remaining copy of the data. That is also why the restore checks for the database after
extraction instead of trusting the exit code of `tar`.

## Configuration

Both scripts read the same environment:

| Variable | Default | |
| --- | --- | --- |
| `BACKUP_ENCRYPTION_KEY` | *required* | AES-256 passphrase |
| `DATADIR` | `/data` | Vaultwarden's data directory |
| `BACKUP_LOCAL_DIR` | `/backup` | NFS-backed PVC on the NAS |
| `BACKUP_REMOTE_DIR` | `gdrive:backup` | Any rclone remote. Skipped if it equals the local directory |

Two secrets are mounted: `backup-encryption-secret` for the key, and `rclone-secret`
carrying an `rclone.conf` for the remote. Both are git-crypt encrypted in this repository.

## The images

Both build `FROM dhi.io/alpine-base`, a [Docker Hardened
Image](https://www.docker.com/products/hardened-images/), with a `-dev` stage that has a
package manager and a final stage that does not. `openssl`, `tar`, `sqlite3` and `rclone`
are copied in, and nothing that installed them is kept.

That leaves a scanner blind spot, which is documented in the
[Dockerfile](backup/Dockerfile) itself. Binaries that arrive by `COPY` have no package
record, and neither `sqlite3` nor `tar` has a syft classifier, so they appear in no SBOM and
no scan. It is an accepted gap, with the alternatives that were tried and rejected written
next to it. See [Supply chain](../../docs/supply-chain.md#base-images).

Runtime posture is the same for both: `USER nonroot`, read-only root filesystem, all
capabilities dropped, `RuntimeDefault` seccomp, and `/tmp` as the only writable path.

## Releasing

Both images are tagged from git tags, `vw-backup-<CalVer>` and `vw-restore-<CalVer>`, and
built by the [shared workflow](https://github.com/theadzik/github-workflows), which scans
before pushing, signs the digest and attaches an SBOM and provenance attestation. They also
rebuild weekly, so base image fixes land without a source change.
