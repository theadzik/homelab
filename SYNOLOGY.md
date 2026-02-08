# Synology DS923+ Notes

## Overview

These notes show the configuration for the Synology DS923+ used in this homelab. These changes are mostly manually deployed,
either through DMS webportal, or by SSH.

## Docker

### PiHole

### Minio

### acme.sh

## Services Configuration

### dnsmasq

* Service name: pkg-dhcpserver
* Config File: /usr/local/lib/systemd/system/pkg-dhcpserver.service

#### Changes

To allow running PiHole in a container with port 53 I had to disable DNS in dnsmasq.

```text
# https://linux.die.net/man/8/dnsmasq
-p, --port=<port>
    Listen on <port> instead of the standard DNS port (53). Setting this to zero completely disables DNS function, leaving only DHCP and/or TFTP.
```

```text
# /usr/local/lib/systemd/system/pkg-dhcpserver.service
...
ExecStart=/var/packages/DhcpServer/target/dnsmasq-2.x-virtual-dhcpserver/usr/syno/sbin/dnsmasq --user=DhcpServer --group=DhcpServer --cache-size=200 --conf-file=/etc/dhcpd/dhcpd.conf --dhcp-lease-max=2147483648 --port=0
...
```

```bash
systemctl stop pkg-dhcpserver
systemctl start pkg-dhcpserver
```

> 🚧 **TODO:** Verify dnsmasq port change persists after reboot/update.
