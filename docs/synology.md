# Synology DS923+

Everything else in this repository is reconciled by ArgoCD. The NAS is the exception: DSM
has no declarative interface worth automating against, and the cluster that would run the
automation PXE boots from this machine anyway. These notes exist so the manual configuration
is at least written down.

Everything below is applied through the DSM web interface or over SSH.

## What it does

| Role | Used by |
| --- | --- |
| iSCSI and NFS targets | The [Synology CSI driver](storage-and-backups.md#storage-classes) — every PersistentVolume in the cluster |
| S3 object storage ([Garage](https://garagehq.deuxfleurs.fr/documentation/quick-start/)) | Velero backups |
| DNS ([PiHole](https://pi-hole.net/)) | The LAN, and external-dns for internal records |
| DHCP and TFTP | PXE booting the Talos nodes |
| ACME client (`acme.sh`) | DSM's own certificate, since it is not in the cluster |

PiHole is reachable at <https://pihole.zmuda.pro:8443/admin/>, and the NAS itself at
`synology.zmuda.pro` — an A record created from a pair of `ExternalName` services in the
[CSI kustomization](../kubernetes/kustomizations/synology-csi/external-service.yaml), purely
so that external-dns publishes the name.

The dependency is worth stating plainly: the NAS is a single point of failure for storage,
DNS, DHCP and node boot. The cluster survives losing any node; it does not survive losing
this.

## Running PiHole and DSM's DHCP server together

PiHole needs port 53. DSM's DHCP server package runs `dnsmasq`, which binds port 53 for DNS
whether or not anyone asked it to. The fix is to keep the DHCP half and switch the DNS half
off, using [dnsmasq](https://linux.die.net/man/8/dnsmasq)'s own escape hatch:

```text
-p, --port=<port>
    Listen on <port> instead of the standard DNS port (53). Setting this to zero
    completely disables DNS function, leaving only DHCP and/or TFTP.
```

The service is `pkg-dhcpserver`, defined in
`/usr/local/lib/systemd/system/pkg-dhcpserver.service`. Adding `--port=0` to its
`ExecStart` frees the port:

```text
ExecStart=/var/packages/DhcpServer/target/dnsmasq-2.x-virtual-dhcpserver/usr/syno/sbin/dnsmasq \
  --user=DhcpServer --group=DhcpServer --cache-size=200 \
  --conf-file=/etc/dhcpd/dhcpd.conf --dhcp-lease-max=2147483648 --port=0
```

```bash
systemctl restart pkg-dhcpserver
```

### Making it survive an update

DSM rewrites that unit file on package updates and reboots, silently taking DNS down for
the whole LAN. **Control Panel → Task Scheduler → Create → Triggered task** puts it back:

```bash
#!/usr/bin/env bash
set -euo pipefail

SERVICE="pkg-dhcpserver"
FILE="/usr/local/lib/systemd/system/$SERVICE.service"
PORT="0"

if grep -qP '^ExecStart=.*--port=' "$FILE"; then
    sed -i -E "s/(ExecStart=.*)(--port=[^ ]*)(.*)/\1--port=${PORT}\3/" "$FILE"
else
    sed -i -E "s/(ExecStart=.*)/\1 --port=${PORT}/" "$FILE"
fi

systemctl daemon-reload
systemctl restart "$SERVICE"
exit 0
```

The script rewrites an existing `--port=` flag rather than appending a second one, so it is
safe on every boot and not only the ones that follow an update.

## Storage tiers

Two volumes back the storage classes: HDD by default, and `/volume2` (SSD) for anything
selected by a `-ssd` class. The mapping is a `location` parameter on the StorageClass, so
choosing a tier is a one-line change in a PVC. See
[Storage and backups](storage-and-backups.md#storage-classes).

## PXE boot

The NAS serves DHCP and TFTP for the Talos nodes, which is what lets a replacement node join
with no installation media. The full setup — static IP, TFTP share, DHCP options and the
Talos Factory image — is written up in
[PXE Booting Talos Linux from Synology NAS](https://zmuda.pro/talos-linux-using-pxe).

An earlier post covers the storage side: [Synology DS923+ as a Storage Server for
Kubernetes](https://zmuda.pro/synology-nas-setup).
