# Synology DS923+

Everything else in this repository is reconciled by ArgoCD. The NAS is the exception. DSM
has no declarative interface worth automating against, and the cluster that would run the
automation PXE boots from this machine anyway. These notes exist so the manual configuration
is at least written down.

Everything below is applied through the DSM web interface or over SSH.

## What it does

| Role | Used by |
| --- | --- |
| iSCSI and NFS targets | The [Synology CSI driver](storage-and-backups.md#storage-classes), so every PersistentVolume in the cluster |
| S3 object storage ([Garage](https://garagehq.deuxfleurs.fr/documentation/quick-start/)) | Velero backups |
| DNS ([PiHole](https://pi-hole.net/)) | The LAN, and external-dns for internal records |
| DHCP and TFTP | PXE booting the Talos nodes |
| ACME client (`acme.sh`) | DSM's own certificate, since it is not in the cluster |

PiHole is reachable at <https://pihole.zmuda.pro/admin/>, through a DSM reverse proxy rule
(**Control Panel → Login Portal → Advanced → Reverse Proxy**) from HTTPS
`pihole.zmuda.pro:443` to HTTP `127.0.0.1:8080`, a port PiHole serves on loopback only. Its own
HTTPS on 8443 stays up until external-dns is confirmed working through the proxy. The NAS
itself is at
`synology.zmuda.pro`. That A record comes from a pair of `ExternalName` services in the
[CSI kustomization](../kubernetes/kustomizations/synology-csi/external-service.yaml), which
exist purely so external-dns publishes the name.

The dependency is worth stating plainly. The NAS is a single point of failure for storage,
DNS, DHCP and node boot. The cluster survives losing any node. It does not survive losing
this.

## Containers

PiHole, Garage and `acme.sh` run as one Container Manager project, `infrastructure`, from
[`synology/docker-compose.yaml`](../synology/docker-compose.yaml). Their passwords and keys,
and Garage's `garage.toml`, are in the `*.secret.*` files beside it, which git-crypt encrypts.

To change a container, edit the files here, copy `docker-compose.yaml` and the `*.secret.*`
files to `/volume1/docker-compose/` on the NAS, then open **Container Manager → Project → infrastructure → Action → Build**.
Recreating `pihole` takes LAN DNS down for a few seconds, and recreating `garage` interrupts
any Velero backup that is running.

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
the whole LAN. [`synology/dhcpserver-port.sh`](../synology/dhcpserver-port.sh) puts the flag
back. It is idempotent: it does nothing if `--port=0` is already there, and only reloads and
restarts the service when it had to fix the file.

Run it as root from two tasks in **Control Panel → Task Scheduler**, pasting the script into
each:

- **Triggered task**, event *Boot-up*, so a reboot is fixed straight away.
- **Scheduled task**, every hour, to catch package updates, which do not reboot.

## Storage tiers

Two volumes back the storage classes: HDD by default, and `/volume2` (SSD) for anything
selected by a `-ssd` class. The mapping is a `location` parameter on the StorageClass, so
choosing a tier is a one-line change in a PVC. See
[Storage and backups](storage-and-backups.md#storage-classes).

## PXE boot

The NAS serves DHCP and TFTP for the Talos nodes, which is what lets a replacement node join
with no installation media. The full setup, covering static IP, TFTP share, DHCP options and
the Talos Factory image, is written up in
[PXE Booting Talos Linux from Synology NAS](https://zmuda.pro/talos-linux-using-pxe).

An earlier post covers the storage side: [Synology DS923+ as a Storage Server for
Kubernetes](https://zmuda.pro/synology-nas-setup).
