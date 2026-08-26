# Talos node configuration

The nodes run [Talos Linux](https://www.talos.dev/), which has no shell and no package
manager. A node is configured entirely by a machine config file pushed over the Talos API,
so this directory holds the inputs that produce that file.

The configs themselves are **generated**. Nothing in `controlplane.yaml` or `worker.yaml` is
hand-edited, and neither file is committed.

| File | What it is |
| --- | --- |
| [`generate.sh`](../talos/generate.sh) | Regenerates the machine configs and `talosconfig` |
| [`schematic.yaml`](../talos/schematic.yaml) | Image Factory schematic listing the system extensions |
| [`patch-all.yaml`](../talos/patch-all.yaml) | Config patch applied to every node type, in both environments |
| [`patch-prod.yaml`](../talos/patch-prod.yaml) | The parts that only apply to real hardware: install disk, containerd CDI directories |
| [`bootstrap/prod/`](../talos/bootstrap/prod/) | Kustomization rendering Cilium and ArgoCD for the control plane's inline manifest |
| [`bootstrap/dev/`](../talos/bootstrap/dev/) | The same, for the Docker cluster - see [Dev cluster](dev-cluster.md) |
| [`dev.sh`](../talos/dev.sh) | Creates and destroys the Docker cluster |
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
gets upgraded. `generate.sh` pins both explicitly as flags:

```sh
talosctl gen config ... --kubernetes-version 1.36.3 --talos-version v1.13.7
```

`--kubernetes-version` sets every image this cluster needs for that version in one place -
`machine.kubelet.image` on every node, and `apiServer`/`controllerManager`/`scheduler`
images on control plane nodes only, since workers do not run those. Bump the one variable in
the script rather than five fields in a patch.

Watch out for `talosctl upgrade-k8s`, which rewrites those images on the nodes directly.
After running it, update `KUBERNETES_VERSION` in the script to match, or the next
`apply-config` rolls the cluster back to the old pin.

`--talos-version` is the schema contract `gen config` renders against, kept in step with the
actual Talos release running on the nodes.

`--install-image` is built from the two together: the schematic ID and `TALOS_VERSION`
combine into `factory.talos.dev/metal-installer/<schematic-id>:<talos-version>`. The
schematic ID itself is not a value copied into the script - it is fetched fresh from the
Image Factory on every run, by posting [`schematic.yaml`](../talos/schematic.yaml) to
`https://factory.talos.dev/schematics`:

```sh
curl -sS -X POST --data-binary @schematic.yaml https://factory.talos.dev/schematics | jq -r .id
```

Deriving it this way means editing the system extensions in `schematic.yaml` can never leave
a stale ID behind for someone to notice later.

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
[`talos/bootstrap/prod/`](../talos/bootstrap/prod/), a kustomization that renders Cilium and ArgoCD via
Helm and adds the three files that get ArgoCD's own bootstrap `Application` running:

```sh
kustomize build --enable-helm --load-restrictor LoadRestrictionsNone talos/bootstrap/prod
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
  [`kubernetes/kustomizations/argocd/overlays/prod`](../kubernetes/kustomizations/argocd/overlays/prod/), so it picks
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
existed: `kubectl apply -k kubernetes/kustomizations/argocd/overlays/prod`.

Once Cilium is up, a node stops waiting - Talos applies inline manifests itself as part of
its own bootstrap sequence.

## See also

- [Architecture](architecture.md#why-talos) — what Talos buys and what it costs
- [Operations](operations.md#bootstrapping-from-nothing) — where these commands sit in the
  full bootstrap
- [Networking](networking.md) — Cilium, and why kube-proxy is gone
