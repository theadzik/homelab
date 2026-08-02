#!/usr/bin/env bash
# Regenerate the Talos machine configs and talosconfig from the inputs in this
# directory. Output is git-ignored; it contains the full cluster PKI.
set -euo pipefail

cd "$(dirname "$0")"

CLUSTER_NAME="homelab-prod"
CONTROLPLANE_IP="192.168.0.2"

talosctl gen config \
    "$CLUSTER_NAME" "https://${CONTROLPLANE_IP}:6443" \
    --with-secrets secret-certs.yaml \
    --config-patch @patch-all.yaml \
    --config-patch @secret-nut-client.yaml \
    --with-docs=false --with-examples=false \
    --force

# gen config always writes `endpoints: []`; there is no flag for it. The
# positional argument above is the Kubernetes API endpoint, which is a
# different thing from the Talos API endpoint set here.
#
# Endpoints must be control plane nodes only. Workers refuse to proxy
# ("PermissionDenied: no request forwarding"), so listing one here causes
# intermittent failures depending on which endpoint the client picks.
talosctl --talosconfig talosconfig config endpoint "$CONTROLPLANE_IP"

talosctl validate -c controlplane.yaml -m metal
talosctl validate -c worker.yaml -m metal
