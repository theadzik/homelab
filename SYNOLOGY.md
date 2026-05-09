# Synology DS923+ Notes

## Overview

These notes show the configuration for the Synology DS923+ used in this homelab. These changes are mostly manually deployed,
either through DMS webportal, or by SSH.

## Docker

### PiHole

PiHole runs as a container on Synology. <https://pihole.zmuda.pro:8443/admin/>

### Garage

S3 compatible storage. <https://garagehq.deuxfleurs.fr/documentation/quick-start/>

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
systemctl restart pkg-dhcpserver
```

#### Persistance

To persist the above changes after system updates and reboots: **Control panel** -> **Task scheduler** -> **Create** -> **Triggered task**

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
