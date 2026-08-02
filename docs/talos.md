# Talos node configuration

The nodes run [Talos Linux](https://www.talos.dev/), which has no shell and no package
manager. A node is configured entirely by a machine config file pushed over the Talos API,
so this directory holds the inputs that produce that file.

The configs themselves are **generated**. Nothing in `controlplane.yaml` or `worker.yaml` is
hand-edited, and neither file is committed.

| File | What it is |
| --- | --- |
| [`generate.sh`](../talos/generate.sh) | Regenerates the machine configs and `talosconfig` |
| [`schematic.yaml`](../talos/schematic.yaml) | Image Factory schematic listing the system extensions. Its ID appears in `machine.install.image` |
| [`patch-all.yaml`](../talos/patch-all.yaml) | Config patch applied to every node type |
| `secret-nut-client.yaml` | Patch holding the UPS monitoring credentials, git-crypt encrypted |
| `secret-certs.yaml` | Cluster PKI and join tokens, git-crypt encrypted |
| `controlplane.yaml`, `worker.yaml`, `talosconfig` | Generator output, git-ignored, contains the PKI in plaintext |

## Regenerating

```sh
./talos/generate.sh
```

The script wraps `talosctl gen config` with both patches and the secrets bundle, fills in
the talosconfig endpoint, and validates what came out.

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
binary was built with. That quietly changes the generated config every time the CLI is
upgraded, so the version is pinned in [`patch-all.yaml`](../talos/patch-all.yaml) instead,
across five fields:

- `machine.kubelet.image`
- `cluster.apiServer.image`
- `cluster.controllerManager.image`
- `cluster.scheduler.image`
- `cluster.proxy.image`

Bump all five together. Watch out for `talosctl upgrade-k8s`, which rewrites these fields on
the nodes directly. After running it, update the patch to match or the next `apply-config`
rolls Kubernetes back to the pinned version.

The Talos version is separate and lives in the tag on `machine.install.image`. That tag is a
Talos version and not a Kubernetes one, and the schematic ID in front of it comes from
`schematic.yaml`.

## Validating

```sh
talosctl validate -c controlplane.yaml -m metal
talosctl validate -c worker.yaml -m metal
```

`--config-patch` applies to every node type, so generated worker configs carry the
`apiServer`, `controllerManager` and `scheduler` image pins as well. Workers ignore those
fields. It is the only place the generated worker config differs from the live one.

## Why the CNI is missing on purpose

`patch-all.yaml` sets `cluster.network.cni.name: none` and disables kube-proxy, because
Cilium provides both. See [Networking](networking.md#cilium).

That leaves a gap at bootstrap. With no CNI nothing can be scheduled, ArgoCD included, so
the tool that installs everything else cannot install Cilium. Cilium goes on by hand once,
and the `cilium` Application adopts it at sync wave -80. Talos holds a node at phase 18/19
while it waits for a CNI and reboots it after roughly ten minutes, so the window is short.
The commands are in
[Operations](operations.md#2-install-cilium-by-hand-once).

## See also

- [Architecture](architecture.md#why-talos) — what Talos buys and what it costs
- [Operations](operations.md#bootstrapping-from-nothing) — where these commands sit in the
  full bootstrap
- [Networking](networking.md) — Cilium, and why kube-proxy is gone
