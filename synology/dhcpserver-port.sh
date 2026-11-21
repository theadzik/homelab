#!/usr/bin/env bash
# Keeps DSM's DHCP server (dnsmasq) off port 53 so PiHole can bind it.
# Idempotent: the service is restarted only when the unit file had to be fixed.
# See docs/synology.md.
set -euo pipefail

SERVICE="pkg-dhcpserver"
FILE="/usr/local/lib/systemd/system/$SERVICE.service"
PORT="0"

if grep -qE "^ExecStart=.* --port=${PORT}( |$)" "$FILE"; then
    exit 0
fi

if grep -qE '^ExecStart=.*--port=' "$FILE"; then
    sed -i -E "s/^(ExecStart=.*)(--port=[^ ]*)(.*)/\1--port=${PORT}\3/" "$FILE"
else
    sed -i -E "s/^(ExecStart=.*)/\1 --port=${PORT}/" "$FILE"
fi

echo "$FILE: set --port=${PORT}, restarting $SERVICE"
systemctl daemon-reload
systemctl restart "$SERVICE"
