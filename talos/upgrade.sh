#!/usr/bin/env bash
# Move the cluster to the versions pinned in common.sh.
#
#   ./upgrade.sh talos [--dry-run]        Talos OS, one node at a time
#   ./upgrade.sh kubernetes [--dry-run]   Kubernetes, through talosctl upgrade-k8s
#
# Bump the pin in a pull request first; this script only moves the nodes to
# what main already says. --dry-run reads cluster state and prints the plan
# without changing anything. See docs/talos.md#upgrading for the procedure.
#
# Set TALOS_CONTEXT to the talosconfig context holding this cluster's
# credentials if it is not the current one. The endpoint is always forced to
# the control plane, so a context for some other cluster fails the TLS
# handshake instead of upgrading the wrong machines.
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"

# shellcheck source=/dev/null # common.sh is checked on its own; the hook runs without -x
source "$REPO_ROOT/talos/common.sh"

# etcd snapshots hold every Kubernetes Secret, so they go outside the repo.
SNAPSHOT_DIR="${HOME}/.local/state/homelab/etcd-snapshots"

usage() {
    echo "usage: $0 talos|kubernetes [--dry-run]" >&2
    exit 2
}

die() {
    echo "error: $*" >&2
    exit 1
}

[[ $# -ge 1 && $# -le 2 ]] || usage
MODE="$1"
DRY_RUN=false
case "${2:-}" in
    "") ;;
    --dry-run) DRY_RUN=true ;;
    *) usage ;;
esac

talos() {
    talosctl ${TALOS_CONTEXT:+--context "$TALOS_CONTEXT"} -e "$CONTROLPLANE_IP" "$@"
}

# kubectl's own current context may be another cluster, so fetch a kubeconfig
# for this one through the Talos API and use only that.
KUBECONFIG="$(mktemp)"
export KUBECONFIG
trap 'rm -f "$KUBECONFIG"' EXIT

# One line per node, control plane first: "<type> <hostname> <ip> <talos version>".
# `sort` puts "controlplane" before "worker", which is the order Talos wants.
list_nodes() {
    talos -n "$CONTROLPLANE_IP" get members -o json |
        jq -r '[.spec.machineType, .spec.hostname, .spec.addresses[0],
                (.spec.operatingSystem | capture("\\((?<v>v[^)]+)\\)").v)] | @tsv' |
        sort
}

ips_of() {
    awk -v t="$1" '$1 == t { print $3 }' <<<"$NODES" | paste -sd, -
}

check_health() {
    echo "==> talosctl health"
    talos -n "$CONTROLPLANE_IP" health \
        --control-plane-nodes "$(ips_of controlplane)" \
        --worker-nodes "$(ips_of worker)" \
        --wait-timeout 10m
    # talosctl health skips node readiness when Talos does not manage the CNI,
    # so it would pass with Cilium down on a node that just rebooted.
    echo "==> waiting for all nodes to be Ready"
    kubectl wait --for=condition=Ready nodes --all --timeout=10m
}

snapshot_etcd() {
    local file
    file="${SNAPSHOT_DIR}/etcd-$(date -u +%Y%m%dT%H%M%SZ).db"
    mkdir -p "$SNAPSHOT_DIR"
    chmod 700 "$SNAPSHOT_DIR"
    echo "==> etcd snapshot to $file"
    talos -n "$CONTROLPLANE_IP" etcd snapshot "$file"
}

confirm() {
    local answer
    read -r -p "$1 Type 'yes' to continue: " answer
    [[ "$answer" == "yes" ]] || die "aborted"
}

# "v1.13.7" -> "1 13"
major_minor() {
    local v="${1#v}"
    echo "${v%%.*} $(cut -d. -f2 <<<"$v")"
}

# "1 13" -> "v1.13.12", the newest stable release of that minor.
latest_patch() {
    curl -sSf "https://api.github.com/repos/siderolabs/talos/releases?per_page=100" |
        jq -r --arg prefix "v$1.$2." '.[] | select(.prerelease | not) | .tag_name | select(startswith($prefix))' |
        sort -V | tail -1
}

# Upgrades are only tested between adjacent minors, through the latest patch of
# each one, so refuse anything that skips a minor, leaves a minor before its
# last patch, or goes backwards.
check_talos_path() {
    local from="$1" to="$2" from_major from_minor to_major to_minor latest
    read -r from_major from_minor <<<"$(major_minor "$from")"
    read -r to_major to_minor <<<"$(major_minor "$to")"
    if [[ "$(printf '%s\n' "${from#v}" "${to#v}" | sort -V | head -1)" != "${from#v}" ]]; then
        die "$from -> $to is a downgrade; use talosctl rollback instead"
    fi
    if [[ "$from_major" != "$to_major" ]] || ((to_minor - from_minor > 1)); then
        die "$from -> $to skips a minor release; upgrade to the latest patch of each minor in between first"
    fi
    if ((to_minor > from_minor)); then
        latest="$(latest_patch "$from_major" "$from_minor")"
        [[ "$from" == "$latest" ]] ||
            die "$from -> $to leaves $from_major.$from_minor before its latest patch; set TALOS_VERSION to $latest and upgrade to that first"
    fi
}

upgrade_talos() {
    local client image pending=() type host ip version client_major client_minor target_major target_minor

    client="$(talosctl version --client --short | awk '/^Talos/ { print $2 }')"
    read -r client_major client_minor <<<"$(major_minor "$client")"
    read -r target_major target_minor <<<"$(major_minor "$TALOS_VERSION")"
    if ((client_major < target_major || (client_major == target_major && client_minor < target_minor))); then
        die "talosctl $client is older than the target $TALOS_VERSION; update it first"
    fi

    image="$(install_image)"
    # The Image Factory builds an installer the first time it is asked for, so
    # this also warms it up instead of making the first node wait.
    curl -sfI -o /dev/null -H 'Accept: application/vnd.oci.image.index.v1+json' \
        "https://factory.talos.dev/v2/metal-installer/$(basename "${image%:*}")/manifests/${TALOS_VERSION}" ||
        die "installer $image is not available"

    echo "Target: Talos $TALOS_VERSION"
    echo "Installer: $image"
    echo
    while read -r type host ip version; do
        if [[ "$version" == "$TALOS_VERSION" ]]; then
            echo "  $host ($type, $ip): $version, already at target"
            continue
        fi
        check_talos_path "$version" "$TALOS_VERSION"
        echo "  $host ($type, $ip): $version -> $TALOS_VERSION"
        pending+=("$host $ip")
    done <<<"$NODES"
    echo

    if ((${#pending[@]} == 0)); then
        echo "Nothing to upgrade."
        return
    fi

    check_health
    if $DRY_RUN; then
        echo "Dry run: would snapshot etcd, then upgrade ${#pending[@]} node(s) in the order above."
        return
    fi

    confirm "Upgrade ${#pending[@]} node(s)? Each one drains and reboots; the control plane API is down while it does."
    snapshot_etcd

    for entry in "${pending[@]}"; do
        read -r host ip <<<"$entry"
        echo "==> $host: talosctl upgrade"
        talos -n "$ip" upgrade --image "$image"
        check_health
        version="$(talos -n "$ip" version --short | awk '/^\tTag:/ { print $2 }' | tail -1)"
        [[ "$version" == "$TALOS_VERSION" ]] ||
            die "$host reports $version after upgrade, expected $TALOS_VERSION. A failed boot rolls back on its own; stopping before the next node"
    done
    echo "Done: all nodes on Talos $TALOS_VERSION."
}

# Read through the Talos API rather than kubectl, whose current context may be
# another cluster. The control plane kubelet is the last thing upgrade-k8s
# moves on that node, so it tracks the version a finished upgrade left behind.
kubernetes_version() {
    talos -n "$CONTROLPLANE_IP" get kubeletspecs -o json | jq -r '.spec.image | split(":")[-1]'
}

upgrade_kubernetes() {
    local current
    current="$(kubernetes_version)"
    echo "Kubernetes: $current -> v$KUBERNETES_VERSION"
    if [[ "$current" == "v$KUBERNETES_VERSION" ]]; then
        echo "Nothing to upgrade."
        return
    fi

    check_health

    # upgrade-k8s rewrites every node's machine config. The doc and example
    # flags default to true, which would add the comments generate.sh leaves
    # out on purpose.
    local args=(-n "$CONTROLPLANE_IP" upgrade-k8s --to "$KUBERNETES_VERSION"
        --with-docs=false --with-examples=false)

    # The plan lists the APIs the new version deprecates or removes and every
    # manifest it would re-apply; read it before going further. Pre-pulling is
    # not skipped by --dry-run, so turn it off to keep this read-only.
    echo "==> upgrade-k8s --dry-run"
    talos "${args[@]}" --dry-run --pre-pull-images=false
    if $DRY_RUN; then
        return
    fi

    confirm "Upgrade Kubernetes to $KUBERNETES_VERSION? Control plane components restart, then kubelet on every node."
    snapshot_etcd
    echo "==> upgrade-k8s"
    talos "${args[@]}"
    check_health
    echo "Done: Kubernetes $(kubernetes_version)."
}

NODES="$(list_nodes)"
[[ -n "$NODES" ]] || die "no cluster members found through $CONTROLPLANE_IP"
talos -n "$CONTROLPLANE_IP" kubeconfig "$KUBECONFIG" --force >/dev/null

case "$MODE" in
    talos) upgrade_talos ;;
    kubernetes) upgrade_kubernetes ;;
    *) usage ;;
esac
