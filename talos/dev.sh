#!/usr/bin/env bash
# Create or destroy the dev cluster: three Talos nodes as Docker containers,
# bootstrapped the same way the bare-metal cluster is. See ../docs/dev-cluster.md.
#
#   ./talos/dev.sh create    (default)
#   ./talos/dev.sh destroy
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"

CLUSTER_NAME="homelab-dev"
# Both pinned to the values generate.sh uses, so dev and prod run the same
# Kubernetes and the same Talos. The image cannot be the Image Factory one prod
# installs: schematics build installer images for real machines, and a Docker
# node runs the stock image with no system extensions at all.
KUBERNETES_VERSION="1.36.3"
TALOS_VERSION="v1.13.7"
TALOS_IMAGE="ghcr.io/siderolabs/talos:${TALOS_VERSION}"

# One control plane and two workers, the same split as prod. talosctl always
# creates exactly one control plane in Docker mode, so only the workers count
# is a flag.
WORKERS=2

# The dev CiliumLoadBalancerIPPool hands out 10.5.0.210-220, so this subnet and
# that pool have to agree. See
# kubernetes/kustomizations/cilium/overlays/dev/loadbalancerippool.yaml.
SUBNET="10.5.0.0/24"

# Nodes are containers on a workstation, not 32 GiB machines.
CPUS_CONTROLPLANE="4.0"
CPUS_WORKER="4.0"
MEMORY_CONTROLPLANE="4096"
MEMORY_WORKER="4096"

BOOTSTRAP_APP="${REPO_ROOT}/kubernetes/kustomizations/argocd/overlays/dev/argocd-bootstrap.yaml"

die() { echo "error: $*" >&2; exit 1; }

destroy() {
    talosctl cluster destroy --name "$CLUSTER_NAME" || true
    # cluster create merged these in; leaving them behind makes `kubectl
    # config get-contexts` lie about what exists.
    kubectl config delete-context "admin@${CLUSTER_NAME}" 2>/dev/null || true
    kubectl config delete-cluster "$CLUSTER_NAME" 2>/dev/null || true
    kubectl config delete-user "admin@${CLUSTER_NAME}" 2>/dev/null || true
    echo "destroyed ${CLUSTER_NAME}"
}

create() {
    for binary in talosctl kustomize helm yq docker kubectl; do
        command -v "$binary" >/dev/null || die "$binary is not on PATH"
    done

    # ArgoCD fetches from GitHub, never from this working tree, so an unpushed
    # branch produces a cluster that boots and then syncs nothing.
    local revision
    revision="$(yq -er '.spec.source.targetRevision' "$BOOTSTRAP_APP")"
    git -C "$REPO_ROOT" ls-remote --exit-code --heads origin "$revision" >/dev/null \
        || die "branch '${revision}' does not exist on origin. Push it first, or change targetRevision in ${BOOTSTRAP_APP#"$REPO_ROOT"/}"

    local branch
    branch="$(git -C "$REPO_ROOT" rev-parse --abbrev-ref HEAD)"
    if [ "$branch" != "$revision" ]; then
        echo "warning: checked out '${branch}', but the dev cluster will track '${revision}'" >&2
    fi

    # kustomize would otherwise embed the git-crypt ciphertext as if it were
    # the key, and the repo-server would fail every unlock without saying why.
    head -c 11 "${REPO_ROOT}/kubernetes/kustomizations/argocd/base/argocd-gitcrypt-secret.yaml" \
        | grep -q '^apiVersion:' \
        || die "repository is git-crypt locked; run 'git-crypt unlock' first"

    # Same mechanism as generate.sh: everything Talos must apply before ArgoCD
    # exists goes in as one inlineManifest, because Talos replaces that list
    # per patch file rather than appending to it.
    local inline_patch bootstrap_manifest
    inline_patch="$(mktemp)"
    # shellcheck disable=SC2064  # expand now, the temp file name is fixed
    trap "rm -f '$inline_patch'" EXIT

    bootstrap_manifest="$(mktemp)"
    kustomize build --enable-helm --load-restrictor LoadRestrictionsNone \
        "${REPO_ROOT}/talos/bootstrap/dev" > "$bootstrap_manifest"
    BOOTSTRAP_MANIFEST="$bootstrap_manifest" yq -n \
        '.cluster.inlineManifests = [{"name": "bootstrap", "contents": load_str(strenv(BOOTSTRAP_MANIFEST))}]' \
        > "$inline_patch"
    rm -f "$bootstrap_manifest"

    talosctl cluster create docker \
        --name "$CLUSTER_NAME" \
        --image "$TALOS_IMAGE" \
        --kubernetes-version "$KUBERNETES_VERSION" \
        --workers "$WORKERS" \
        --subnet "$SUBNET" \
        --cpus-controlplanes "$CPUS_CONTROLPLANE" \
        --cpus-workers "$CPUS_WORKER" \
        --memory-controlplanes "$MEMORY_CONTROLPLANE" \
        --memory-workers "$MEMORY_WORKER" \
        --config-patch "@${REPO_ROOT}/talos/patch-all.yaml" \
        --config-patch-controlplanes "@${inline_patch}"

    cat <<EOF

${CLUSTER_NAME} is up, tracking '${revision}'.

talosctl and kubectl now both point at it - prod is the 'admin@homelab-prod'
context in each. ArgoCD works through the sync waves on its own from here.

  kubectl config use-context admin@${CLUSTER_NAME}
  kubectl -n argocd get applications -w

ArgoCD's admin password, once the argocd Application has synced:

  kubectl -n argocd get secret argocd-initial-admin-secret \\
    -o jsonpath='{.data.password}' | base64 -d

Reach it through Traefik once traefik has an address:

  kubectl -n traefik get svc traefik -o jsonpath='{.status.loadBalancer.ingress[0].ip}'

then add that address to /etc/hosts for argocd.dev.zmuda.pro and
hubble.dev.zmuda.pro. The certificates are self-signed, so use curl -k.

  ./talos/dev.sh destroy
EOF
}

case "${1:-create}" in
    create) create ;;
    destroy) destroy ;;
    *) die "usage: $0 [create|destroy]" ;;
esac
