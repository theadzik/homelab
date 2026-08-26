#!/usr/bin/env bash
# Regenerate the Talos machine configs and talosconfig from the inputs in this
# directory. Output is git-ignored; it contains the full cluster PKI, and the
# control plane config carries Cilium and ArgoCD's rendered manifests too.
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$REPO_ROOT/talos"

CLUSTER_NAME="homelab-prod"
CONTROLPLANE_IP="192.168.0.2"
KUBERNETES_VERSION="1.36.3"
TALOS_VERSION="v1.13.7"

# Derived from schematic.yaml's actual content rather than trusted as a
# hardcoded copy, so a schematic change can't leave install-image pointing at
# stale extensions.
SCHEMATIC_ID="$(curl -sS -X POST --data-binary @schematic.yaml https://factory.talos.dev/schematics | jq -er '.id')"
INSTALL_IMAGE="factory.talos.dev/metal-installer/${SCHEMATIC_ID}:${TALOS_VERSION}"

# Cilium and ArgoCD get rendered from talos/bootstrap/prod and embedded as
# one inlineManifest, control-plane only. Talos merges the inlineManifests
# list from separate --config-patch files by replacing it, not appending, so
# everything has to go in through one patch or the second would silently drop
# the first.
INLINE_MANIFESTS_PATCH="$(mktemp)"
trap 'rm -f "$INLINE_MANIFESTS_PATCH"' EXIT

BOOTSTRAP_MANIFEST="$(mktemp)"
kustomize build --enable-helm --load-restrictor LoadRestrictionsNone \
    "$REPO_ROOT/talos/bootstrap/prod" > "$BOOTSTRAP_MANIFEST"
BOOTSTRAP_MANIFEST="$BOOTSTRAP_MANIFEST" yq -n \
    '.cluster.inlineManifests = [{"name": "bootstrap", "contents": load_str(strenv(BOOTSTRAP_MANIFEST))}]' \
    > "$INLINE_MANIFESTS_PATCH"
rm -f "$BOOTSTRAP_MANIFEST"

talosctl gen config \
    "$CLUSTER_NAME" "https://${CONTROLPLANE_IP}:6443" \
    --with-secrets secret-certs.yaml \
    --kubernetes-version "$KUBERNETES_VERSION" \
    --talos-version "$TALOS_VERSION" \
    --install-image "$INSTALL_IMAGE" \
    --config-patch @patch-all.yaml \
    --config-patch @patch-prod.yaml \
    --config-patch @secret-nut-client.yaml \
    --config-patch-control-plane "@${INLINE_MANIFESTS_PATCH}" \
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
