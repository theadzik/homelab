# Talos node configuration

The nodes run [Talos Linux](https://www.talos.dev/), which has no shell and no package
manager. A node is configured entirely by a machine config file pushed over the Talos API,
so this directory holds the inputs that produce that file.

The configs themselves are **generated**. Nothing in `controlplane.yaml` or `worker.yaml` is
hand-edited, and neither file is committed.

| File | What it is |
| --- | --- |
| [`common.sh`](../talos/common.sh) | Version pins and the install image, sourced by both scripts |
| [`generate.sh`](../talos/generate.sh) | Regenerates the machine configs and `talosconfig` |
| [`upgrade.sh`](../talos/upgrade.sh) | Upgrades the nodes to the pinned Talos or Kubernetes version |
| [`schematic.yaml`](../talos/schematic.yaml) | Image Factory schematic listing the system extensions |
| [`patch-all.yaml`](../talos/patch-all.yaml) | Config patch applied to every node type |
| [`bootstrap/`](../talos/bootstrap/) | Kustomization rendering Cilium and ArgoCD for the control plane's inline manifest |
| `secret-nut-client.yaml` | Patch holding the UPS monitoring credentials, git-crypt encrypted |
| `secret-certs.yaml` | Cluster PKI and join tokens, git-crypt encrypted |
| `controlplane.yaml`, `worker.yaml`, `talosconfig` | Generator output, git-ignored, contains the PKI in plaintext |

## Regenerating

```sh
./talos/generate.sh
```

Besides `talosctl`, the script needs `kustomize`, `helm`, `yq` and `jq` on the path - all
part of the [workstation setup](operations.md#the-local-machine).

It wraps `talosctl gen config` with both patches and the secrets bundle, adds the rendered
Cilium/ArgoCD manifest as a third, control-plane-only patch, fills in the talosconfig
endpoint, and validates what came out.

`--with-secrets` is what makes the output reproducible. Without it, every run mints a fresh
PKI and new join tokens, and the result cannot be applied to a running cluster. That bundle
is not derived from anything else in the directory. It is cluster state, which makes
`secret-certs.yaml` the one file here that cannot be recreated from the others.

It can be pulled back out of a running control plane node, but only while a working
`talosconfig` still exists to authenticate with. Treat that as a repair path and not as a
backup:

```sh
talosctl -n 192.168.0.2 get machineconfig v1alpha1 -o jsonpath='{.spec}' > /tmp/cp.yaml
talosctl gen secrets --from-controlplane-config /tmp/cp.yaml -o secret-certs.yaml
```

### The endpoint the generator will not set

`talosctl gen config` always writes `talosconfig` with `endpoints: []`, and no flag or patch
field changes that. The `https://…:6443` argument it takes is the **Kubernetes** API
endpoint, which ends up in `cluster.controlPlane.endpoint` inside the machine config. The
talosconfig endpoints are the **Talos** API on port 50000, which the generator cannot infer.
So `generate.sh` sets them afterwards:

```sh
talosctl --talosconfig talosconfig config endpoint 192.168.0.2
```

Run `gen config` by hand and skip this, and every later `talosctl` call needs an explicit
`-e`.

Only control plane nodes belong in that list. An endpoint is the machine `talosctl` connects
to, `-n/--nodes` is what the command acts on, and the endpoint forwards between the two.
Workers answer for themselves and refuse to forward:

```console
$ talosctl -e <worker> -n <any other node> version
error getting version: rpc error: code = PermissionDenied desc = no request forwarding
```

Because the client spreads calls across every configured endpoint, a worker in the list
fails intermittently instead of consistently, which is the harder version of that bug to
find. Adding more control plane IPs as the cluster grows gives `talosctl` failover. It does
nothing for `kubectl`, which reads one server URL from the kubeconfig, so HA there needs a
VIP or a load balancer in front of the Kubernetes API.

One thing does change between runs. The admin client certificate in `talosconfig` is
re-minted each time with a fresh one-year validity. It is signed by the CA from the secrets
bundle so it works against the running cluster, but `talosconfig` will never be
byte-identical the way the machine configs are.

## Version pinning

`talosctl gen config` defaults the Kubernetes version to whatever the local `talosctl`
binary was built with, and the Talos version affects which config fields it even knows how
to generate. Leaving either unset means the output quietly changes every time someone's CLI
gets upgraded. The pins live in [`common.sh`](../talos/common.sh), which both `generate.sh`
and `upgrade.sh` source, and `generate.sh` passes them explicitly as flags:

```sh
talosctl gen config ... --kubernetes-version 1.36.3 --talos-version v1.13
```

`--kubernetes-version` sets every image this cluster needs for that version in one place -
`machine.kubelet.image` on every node, and `apiServer`/`controllerManager`/`scheduler`
images on control plane nodes only, since workers do not run those. Bump the one variable
rather than five fields in a patch.

Watch out for `talosctl upgrade-k8s`, which rewrites those images on the nodes directly.
Run by hand, it leaves `KUBERNETES_VERSION` behind, and the next `apply-config` rolls the
cluster back to the old pin. [Upgrading](#upgrading) avoids that by bumping the pin first
and having `upgrade.sh` read it.

`--talos-version` is the schema `gen config` renders against, and it has its own pin,
`TALOS_CONFIG_SCHEMA`, rather than following `TALOS_VERSION`. From 1.14, `gen config` splits
the config into dedicated documents - `KubeNetworkConfig`, `KubeProxyConfig`,
`UnattendedInstallConfig` and more - and the `v1alpha1` fields
[`patch-all.yaml`](../talos/patch-all.yaml) sets (`cluster.network`, `cluster.proxy`,
`machine.install`, `machine.kubelet`) conflict with them:

```console
$ talosctl validate -c controlplane.yaml -m metal
5 errors occurred:
    * UnattendedInstallConfig config is incompatible with v1alpha1 config (.machine.install)
    * kubelet config is already set in v1alpha1 config (.machine.kubelet)
    * cluster network config is already set in the v1alpha1 config (.machine.cluster.network). ...
    * cluster proxy config in v1alpha1 config (.machine.cluster.proxy) can't be used with KubeProxyConfig document, ...
    * cluster network config in v1alpha1 config (.machine.cluster.network) can't be used with KubeFlannelCNIConfig document, ...
```

Forced through anyway, that config would also bring back Flannel and kube-proxy and point the
installer at `/dev/sda`. Nodes on a newer Talos accept a config in an older schema, so
`TALOS_CONFIG_SCHEMA` stays at `v1.13` until `patch-all.yaml` is rewritten in the new
documents. Bump it only together with that rewrite, and only once `talosctl validate`
passes.

`--install-image` is built from the schematic and the release: the schematic ID and
`TALOS_VERSION`
combine into `factory.talos.dev/metal-installer/<schematic-id>:<talos-version>`. The
schematic ID itself is not a value copied into the script - it is fetched fresh from the
Image Factory on every run, by posting [`schematic.yaml`](../talos/schematic.yaml) to
`https://factory.talos.dev/schematics`:

```sh
curl -sS -X POST --data-binary @schematic.yaml https://factory.talos.dev/schematics | jq -r .id
```

Deriving it this way means editing the system extensions in `schematic.yaml` can never leave
a stale ID behind for someone to notice later.

## Upgrading

Talos and Kubernetes upgrade separately, each by bumping its pin in
[`common.sh`](../talos/common.sh) and then running [`upgrade.sh`](../talos/upgrade.sh)
from `main`:

```sh
TALOS_CONTEXT=<context> ./talos/upgrade.sh talos --dry-run
TALOS_CONTEXT=<context> ./talos/upgrade.sh talos
TALOS_CONTEXT=<context> ./talos/upgrade.sh kubernetes --dry-run
TALOS_CONTEXT=<context> ./talos/upgrade.sh kubernetes
```

`TALOS_CONTEXT` names the talosconfig context that holds this cluster's credentials. It can
be left out when that context is already the current one. The script always sends requests to
`CONTROLPLANE_IP`, so a context for another cluster fails the TLS handshake rather than
reaching the wrong machines. For the same reason it fetches a kubeconfig through the Talos
API into a temporary file instead of using kubectl's current context.

`--dry-run` only reads. It prints the plan, checks the installer image exists, and runs
the health checks, then stops. Without it the script asks for a typed `yes`, takes an
etcd snapshot to `~/.local/state/homelab/etcd-snapshots/`, and then starts.

### Order

1. **Talos first, Kubernetes second.** Each Talos release supports a range of Kubernetes
   versions (the [support matrix](https://docs.siderolabs.com/talos/v1.14/getting-started/support-matrix)),
   and a newer Kubernetes usually needs the newer Talos. `upgrade-k8s` refuses a version the
   running Talos does not support.
2. **One Talos minor at a time, through its latest patch.** Talos only tests config
   migration between adjacent minors, so going from v1.13.7 to v1.14.x means v1.13.7 →
   v1.13.12 → v1.14.x, with a pull request and a run for each step. The script refuses a
   path that skips a minor, leaves a minor before its latest patch, or goes backwards.
3. **One Kubernetes minor at a time.** Patch releases of the current minor can be taken
   whenever the running Talos supports them.

### Before bumping a pin

- Read the release notes of every version in between, for both Talos and Kubernetes. The
  Talos upgrade guide for the target minor has a "Before upgrade" section that lists
  migrations needed in advance.
- Check that the target Talos still supports the Kubernetes version that is running.
- For a new Kubernetes minor, check that the cluster's components support it before the
  control plane does: Cilium above all, then ArgoCD, cert-manager, Kyverno, CloudNativePG,
  Velero, descheduler (its minor follows Kubernetes') and the Intel GPU DRA driver. The
  `kubernetes --dry-run` output lists deprecated APIs still in use.

### What happens during a Talos upgrade

The control plane goes first, then each worker. For every node, `talosctl upgrade` cordons
and drains it, installs the new image to the inactive boot slot, and reboots. After each
node, the script waits for `talosctl health` and for every node to be `Ready`, checks that
the node reports the target version, and only then moves to the next one.

- **The Kubernetes API is down while the control plane reboots.** There is one control
  plane node and one etcd member. Running workloads keep running, but nothing can be
  scheduled, ArgoCD cannot sync, and `kubectl` does not respond until the node is back.
- **A drain that cannot finish stops the upgrade before anything is installed.** The usual
  cause is a PodDisruptionBudget allowing no disruptions. CloudNativePG's
  `database-cluster-primary` PDB always shows 0 allowed, but the operator switches the
  primary over to a replica when its node is drained, so it does not block the drain.
- **`talosctl health` skips node readiness here**, because Talos does not manage the CNI.
  The script waits for `kubectl wait --for=condition=Ready nodes --all` as well, so a node
  whose Cilium agent did not come back stops the run.

### What happens during a Kubernetes upgrade

`talosctl upgrade-k8s` pre-pulls the images, updates the control plane static pods, then
the kubelet on every node, then re-applies the bootstrap manifests Talos manages (CoreDNS and
some RBAC). Workloads restart as their node's kubelet restarts. The script passes
`--with-docs=false --with-examples=false`, because `upgrade-k8s` rewrites every node's
machine config, and its defaults would add the comments `generate.sh` leaves out.

The manifest step uses server-side apply with forced ownership, and prunes. It applies
whatever is in the control plane's `cluster.inlineManifests`. The live config has none
today, so it only touches Talos's own objects. If the bootstrap inline manifest from
`generate.sh` is ever applied to the running control plane, the next `upgrade-k8s` would
apply the Cilium and ArgoCD it was rendered with over the versions ArgoCD deployed since.
Check the `updating manifests` section of the dry run before running it for real.

### Recovering

- **A node that fails to boot the new image** falls back to the previous boot slot on its
  own. `talosctl -n <ip> rollback` does the same for a node that booted but misbehaves.
- **etcd** moves to a new minor with some Talos minors (3.6 to 3.7 with Talos 1.14), and
  etcd does not downgrade by itself. Rolling the control plane back across that boundary
  means restoring the snapshot the script took, through Talos'
  [disaster recovery](https://docs.siderolabs.com/talos/v1.14/build-and-extend-talos/cluster-operations-and-maintenance/disaster-recovery)
  procedure, which ends in `talosctl bootstrap --recover-from=<snapshot.db>`.
- **The pins must match the cluster afterwards.** If a run stops halfway, finish it, or
  revert the pin, before anything is regenerated or applied.

## Validating

```sh
talosctl validate -c controlplane.yaml -m metal
talosctl validate -c worker.yaml -m metal
```

## Bootstrapping Cilium and ArgoCD

[`patch-all.yaml`](../talos/patch-all.yaml) sets `cluster.network.cni.name: none` and
disables kube-proxy, because Cilium provides both. See [Networking](networking.md#cilium).
That leaves a real gap: with no CNI nothing can be scheduled, ArgoCD included, so the tool
that installs everything else in this cluster cannot install itself.

Talos has a mechanism built for exactly this -
[`cluster.inlineManifests`](https://docs.siderolabs.com/talos/v1.13/reference/configuration/v1alpha1/config#inlinemanifests):
manifests embedded directly in the machine config, applied automatically as part of
`talosctl bootstrap`, before anything else. `generate.sh` builds one from
[`talos/bootstrap/`](../talos/bootstrap/), a kustomization that renders Cilium and ArgoCD via
Helm and adds the three files that get ArgoCD's own bootstrap `Application` running:

```sh
kustomize build --enable-helm --load-restrictor LoadRestrictionsNone talos/bootstrap
```

`--load-restrictor LoadRestrictionsNone` is needed because that kustomization reaches into
`kubernetes/helm/` and `kubernetes/kustomizations/argocd/` for its values and resources,
outside its own directory tree - the default restriction exists to stop a kustomization
pulled from somewhere untrusted reading arbitrary local files, which does not apply to one
we wrote ourselves.

Two things about what goes in are worth knowing:

- **`argocd-server-transport.yaml` is left out.** It is a Traefik `ServersTransport`, and
  Traefik's CRD does not exist at boot - Traefik itself is still several sync waves away.
  The `argocd` Application's second source is
  [`kubernetes/kustomizations/argocd`](../kubernetes/kustomizations/argocd/), so it picks
  that file up on its own, later, once Traefik is running.
- **The CRDs are included, and nothing is trimmed to save space.** ArgoCD's three CRDs alone
  render to roughly 1.8 MB, so `controlplane.yaml` ends up around 2.4 MB against
  `worker.yaml`'s few kilobytes. Rendered output like this is never committed regardless of
  size, so there is no diff to keep readable and no reason to hand-edit it down.

Ordering matters here, because ArgoCD's own bootstrap `Application` is a custom resource
that needs its CRD to already exist. `kustomize build` sorts by kind before anything else,
so every `CustomResourceDefinition` in the combined output lands before any resource that
might use one - verified directly against this exact kustomization: all three ArgoCD CRDs
sit in the first 30 KB of a 2 MB file, the bootstrap `Application` many thousands of lines
later. What is not independently verified is how Talos's own apply step walks that stream
internally - inline manifests exist specifically to solve CRD-then-CR bootstrap ordering
(CNI installs are the canonical use case), so this is very likely handled, but it has not
been watched happen on real hardware. If `argocd-bootstrap` is missing after a fresh
`talosctl bootstrap`, the fallback is the same command a human would have run before this
existed: `kubectl apply -k kubernetes/kustomizations/argocd`.

Once Cilium is up, a node stops waiting - Talos applies inline manifests itself as part of
its own bootstrap sequence.

## See also

- [Architecture](architecture.md#why-talos) — what Talos buys and what it costs
- [Operations](operations.md#bootstrapping-from-nothing) — where these commands sit in the
  full bootstrap
- [Networking](networking.md) — Cilium, and why kube-proxy is gone
