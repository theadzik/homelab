#!/usr/bin/env bash
# Create or destroy the dev cluster: three Talos nodes as Docker containers,
# running the same charts and values as the bare-metal cluster. The one thing
# that differs is when the bootstrap bundle is applied, and why - see the
# comment above the kubectl calls below, and ../docs/dev-cluster.md.
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

    # This is the one place dev cannot mirror prod. Prod embeds the whole
    # Cilium + ArgoCD bundle in the machine config as an inlineManifest, but
    # the Docker provisioner hands the machine config to the node in the
    # USERDATA environment variable, and Linux caps a single environment
    # variable at MAX_ARG_STRLEN - 32 pages, 128 KiB - for the whole
    # "USERDATA=<base64>" string. That is roughly 98 KiB of YAML against a
    # bundle of 2 MB, 90% of which is ArgoCD's three CRDs. Exceeding it does
    # not warn; the container exits 255 with "exec /sbin/init: argument list
    # too long" and the create panics afterwards on the node that never got
    # an address.
    #
    # So dev applies the same bundle with kubectl once the API server is up,
    # from the same kustomization prod renders into its machine config. The
    # cluster still boots with no CNI and no kube-proxy, and everything from
    # the bootstrap Application onwards is identical.
    local rendered bootstrap_manifest crds
    rendered="$(mktemp)"
    bootstrap_manifest="$(mktemp)"
    crds="$(mktemp)"
    # shellcheck disable=SC2064  # expand now, the temp file names are fixed
    trap "rm -f '$rendered' '$bootstrap_manifest' '$crds'" EXIT

    kustomize build --enable-helm --load-restrictor LoadRestrictionsNone \
        "${REPO_ROOT}/talos/bootstrap/dev" > "$rendered"

    # ArgoCD's chart renders a cert-manager Certificate for its own ingress,
    # and cert-manager is many sync waves away from existing - so its CRD is
    # not installed and the object cannot be created yet. Prod embeds the same
    # premature resource and Talos logs the failure and carries on; kubectl
    # would abort the script instead, so it is dropped here and left to the
    # `argocd` Application, which creates it once cert-manager is up.
    yq 'select(.apiVersion != "cert-manager.io/v1")' "$rendered" > "$bootstrap_manifest"
    yq 'select(.kind == "CustomResourceDefinition")' "$bootstrap_manifest" > "$crds"

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
        --config-patch "@${REPO_ROOT}/talos/patch-all.yaml"

    # Nothing can be scheduled yet - that is the point of applying Cilium
    # here - but the API server is a static pod on the host network, so it
    # answers regardless.
    local kube=(kubectl --context "admin@${CLUSTER_NAME}")

    # CRDs first and established before the rest, because the bundle contains
    # the argocd-bootstrap Application and kubectl will not create a custom
    # resource whose kind the API server does not know yet. kustomize sorts
    # CRDs to the front of its output, which is enough for Talos but not for
    # kubectl, which does not wait between objects.
    #
    # Server-side apply is not optional: the applicationsets CRD is 1.4 MB,
    # and a client-side apply would try to store all of it in the
    # last-applied-configuration annotation and be rejected as too long.
    "${kube[@]}" apply --server-side --force-conflicts -f "$crds"
    "${kube[@]}" wait --for=condition=established --timeout=120s -f "$crds"
    "${kube[@]}" apply --server-side --force-conflicts -f "$bootstrap_manifest"

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
