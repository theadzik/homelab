# Storage and backups

Nodes hold nothing worth keeping. Every byte that matters is on the Synology DS923+ or in
this repository, which is what makes a node a disposable PXE boot instead of a machine
anyone has to be careful with.

## Storage classes

The [Synology CSI driver](../kubernetes/kustomizations/synology-csi/) provisions both iSCSI
LUNs and NFS shares from the NAS. Nine storage classes exist, and their names are a grammar
more than a list to memorise:

```text
synology-<protocol>-<reclaim>[-<tier>][-<purpose>]
```

| Axis | Values | Chosen by |
| --- | --- | --- |
| protocol | `iscsi`, `nfs` | Block for single-writer databases and config, NFS for anything `ReadWriteMany` |
| reclaim | `retain`, `delete` | Whether losing the PVC should be survivable |
| tier | *(none)* = HDD, `ssd` = `/volume2` | Latency vs. capacity |

`synology-nfs-delete` is the cluster default. The safe thing to get by accident is a volume
that goes away with its claim, not one that quietly accumulates on the NAS forever.

Two of the parameters took some working out:

- **iSCSI volumes are btrfs, formatted `--nodiscard`.** Discard during format on a
  thin-provisioned LUN issues a very large number of UNMAPs to the NAS for no benefit,
  because the LUN is empty by definition.
- **PostgreSQL gets a class of its own**, `synology-nfs-retain-ssd-postgres`, mounted `hard`
  with `0750` permissions. A soft NFS mount returns I/O errors on interruption, and a
  database that receives an I/O error where it expected a pause can corrupt its data files.
  Everywhere else the mount options are a preference. Here they are a correctness
  requirement.

All classes allow volume expansion, so growing a volume is an edit to a PVC.

## Snapshots

The [external-snapshotter](https://github.com/kubernetes-csi/external-snapshotter) CRDs are
pulled straight into the kustomization from a pinned upstream tag, and a default
`VolumeSnapshotClass` points at the Synology driver. That makes CSI snapshots available to
anything that asks for one, Velero above all.

## Velero

[Velero](../kubernetes/helm/velero/values.yaml) runs two schedules with different jobs.

| Schedule | Cadence | Retention | Scope |
| --- | --- | --- | --- |
| `cluster-full` | daily | 30 days | Every Kubernetes object |
| `csi-opt-in-pvc-snapshots` | every 12 hours | 7 days | Only PVCs labelled `backup.velero.io/csi-snapshot: "true"` |

They are split because the two things cost wildly different amounts. Every Kubernetes object
in the cluster fits in a few megabytes, so there is no reason to be selective. Volume
snapshots are the opposite, and a 7 TiB media library has no business in a backup rotation
when it is reconstructible and its contents already sit on the NAS.

Volume backup is therefore **opt-in by label**, and each PVC that carries the label carries
it for a reason:

```yaml
labels:
  backup.velero.io/csi-snapshot: "true"
```

Backups land in a [Garage](https://garagehq.deuxfleurs.fr/) S3 bucket on the NAS. The
location is deliberately **not** marked default. A backup should be sent somewhere on
purpose, not by omission.

Object-level backups matter less here than they would elsewhere, because the manifests are
all in git. Velero's real value in this cluster is the volume data and the objects nobody
declared: generated secrets, CRD state, whatever ArgoCD would recreate but not repopulate.

## Application-level backup: Vaultwarden

A password manager gets a third layer. The recovery story for everything else, rebuilding
the cluster from git, is far too slow for the thing that holds every credential. The
[backup and restore images](../apps/vaultwarden/) built in this repository do it:

```mermaid
flowchart TD
    cron["CronJob, every 12h"] --> enc["sqlite3 .backup, tar<br/>AES-256, PBKDF2"]
    enc --> nfs[(NFS PVC on NAS)]
    nfs -->|rclone copy| gd[(Google Drive)]

    start["Pod starts"] --> init{"/data/db.sqlite3<br/>exists?"}
    init -->|yes| run[Vaultwarden starts]
    init -->|no| tryl{"backup on NFS?"}
    tryl -->|yes| rest[restore, then start]
    tryl -->|no| tryr{"backup on Drive?"}
    tryr -->|yes| rest
    tryr -->|no| fail["init fails, pod does not start"]
```

What makes it hold up:

- **The restore runs as an init container.** Nobody has to notice that a volume came up
  empty and go looking for a runbook. It is repaired before Vaultwarden opens it.
- **Failing to restore fails the pod.** Starting empty would present a working but empty
  vault, and the first client to sync would overwrite its own copy with nothing. Refusing to
  start is the safer failure, and it was chosen on purpose.
- **The remote copy is off-site and encrypted before it leaves the cluster**, with a key
  Google Drive never sees.

Both images run as UID 1000, non-root, read-only root filesystem, all capabilities dropped,
and they are built from [Docker Hardened Images](supply-chain.md#base-images) and signed
like everything else published here.

## Protecting data from GitOps itself

Automated `prune` is what makes GitOps trustworthy, and also what makes it dangerous near
storage. Deleting a manifest deletes the object, and for a PVC that can mean deleting the
volume.

Data claims opt out explicitly:

```yaml
annotations:
  argocd.argoproj.io/sync-options: Delete=false,Prune=false
```

The media namespace, its 7 TiB downloads claim and both Vaultwarden PVCs carry it. Combined
with `reclaimPolicy: Retain` on the storage class, removing an application from git tears
down its workloads and leaves its data on the NAS.

## What is actually recoverable

Coverage is uneven, so it is worth setting out case by case:

| Loss | Recovery | Time to restore |
| --- | --- | --- |
| A node | PXE boot a replacement, it rejoins | Minutes, no data involved |
| The whole cluster | [Bootstrap from this repository](operations.md#bootstrapping-from-nothing) | Everything declarative returns unattended |
| A PVC | Velero CSI snapshot, if it was labelled | Up to 12 hours of data |
| Vaultwarden data | Local backup, then Google Drive, automatically | Up to 12 hours, and the only path that survives losing the NAS |
| The NAS | Vaultwarden restores from Drive. Everything else was on it. | Media is re-acquirable, other volumes are not |

That last row is the standing gap, and a known one. Velero's bucket lives on the same NAS as
the volumes it backs up, so it protects against deletion and corruption but not against
hardware loss. Fixing it means paying for an off-site S3 target, which is the only thing
stopping it.

The other unrecoverable case is losing every way to unlock the repository. The git-crypt key
is committed here as the Secret ArgoCD mounts, encrypted with itself, so it is no use for
bootstrapping. That needs either the exported key file kept elsewhere or the GPG key
registered under [`.git-crypt/keys/`](../.git-crypt/). Two independent paths, both held
outside this repository. Lose both and nothing here decrypts, backups included. See
[GitOps](gitops.md#secrets-in-a-public-repository).

## See also

- [Synology notes](synology.md): what is configured on the NAS itself, by hand
- [Architecture](architecture.md#where-the-state-lives): how storage fits the whole
- [Operations](operations.md): restore procedures and bootstrap
