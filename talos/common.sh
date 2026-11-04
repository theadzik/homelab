# shellcheck shell=bash disable=SC2034 # each consumer uses a different subset
# Sourced by generate.sh and upgrade.sh, never run directly. The version pins
# here are the record of what the cluster runs: bump them in a pull request,
# merge it, then run ./upgrade.sh from main to move the nodes to match.
#
# Both scripts read the same pins so they cannot disagree. When they could,
# `talosctl upgrade-k8s` would move the nodes, the generator would still hold
# the old version, and the next `apply-config` would roll the cluster back.

CLUSTER_NAME="homelab-prod"
CONTROLPLANE_IP="192.168.0.2"
KUBERNETES_VERSION="1.37.2"
TALOS_VERSION="v1.14.5"

# The machine config schema `gen config --talos-version` renders against, kept
# apart from TALOS_VERSION on purpose. From 1.14, gen config emits the new
# multi-document config (KubeNetworkConfig, KubeProxyConfig,
# UnattendedInstallConfig, ...) next to v1alpha1, and the v1alpha1 fields
# patch-all.yaml sets (`cluster.network`, `cluster.proxy`, `machine.install`,
# `machine.kubelet`) conflict with those documents, so `talosctl validate`
# rejects the result. Nodes on a newer Talos accept the older schema, so this
# stays at v1.13 until patch-all.yaml is migrated to the new documents.
TALOS_CONFIG_SCHEMA="v1.13"

# Derived from schematic.yaml's actual content rather than trusted as a
# hardcoded copy, so a schematic change can't leave the install image pointing
# at stale extensions.
install_image() {
    local schematic_id
    schematic_id="$(curl -sS -X POST --data-binary "@${REPO_ROOT}/talos/schematic.yaml" \
        https://factory.talos.dev/schematics | jq -er '.id')"
    echo "factory.talos.dev/metal-installer/${schematic_id}:${TALOS_VERSION}"
}
