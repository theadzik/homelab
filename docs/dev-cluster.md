# Dev cluster

Three Talos nodes as Docker containers on the workstation, running the same charts, the same
values and the same GitOps chain as the bare-metal cluster. It exists so that a change to
Cilium, to ArgoCD, or to an application can be tried somewhere that is not the cluster
serving the vault and the media library.

One step differs, and only one: how the bootstrap bundle reaches the cluster. That is
[below](#the-one-mechanism-that-does-not-survive), with the reason it cannot be otherwise.

```sh
./talos/dev.sh create
./talos/dev.sh destroy
```

## What it actually is

`talosctl cluster create docker` runs each node as a privileged container on a Docker
bridge network, sharing the host kernel. That is a smaller lie than it sounds: the parts
this repository cares most about behave identically.

| | Prod | Dev |
| --- | --- | --- |
| Nodes | 3 bare metal, PXE booted | 3 containers, one control plane and two workers |
| Talos | `v1.13.7` from the Image Factory, with system extensions | `v1.13.7` stock image, no extensions possible |
| Kubernetes | `1.36.3` | `1.36.3` |
| Machine config | `patch-all.yaml` + `patch-prod.yaml` + secrets bundle | `patch-all.yaml` alone |
| Kubelet serving certs | rotated, signed by the cluster CA | self-signed |
| CNI | Cilium, kube-proxy replacement, L2 announcements | the same, from the same values file |
| Bootstrap | `talos/bootstrap/prod` as an inline manifest | `talos/bootstrap/dev`, applied by `dev.sh` - see below |
| Cluster PKI | `secret-certs.yaml`, reproducible across runs | minted fresh per cluster, thrown away with it |
| LoadBalancer pool | `192.168.0.210-220` on the LAN | `10.5.0.210-220` on the Docker bridge |

## The one mechanism that does not survive

Prod embeds Cilium, ArgoCD and the bootstrap `Application` in the control plane's machine
config as a [Talos inline manifest](talos.md#bootstrapping-cilium-and-argocd), so
`talosctl bootstrap` alone gets from bare metal to GitOps with nothing applied by hand.
Dev renders the same bundle from the same kustomization, but `dev.sh` applies it with
`kubectl` once the API server answers.

That is not a stylistic choice. `talosctl cluster create docker` hands each node its machine
config in the `USERDATA` environment variable, and Linux caps a single environment variable
at `MAX_ARG_STRLEN` - 32 pages, 128 KiB - for the whole `USERDATA=<base64>` string. About
98 KiB of YAML, against this:

| Part of the bundle | Size |
| --- | --- |
| `applicationsets.argoproj.io` CRD | 1.39 MB |
| `applications.argoproj.io` CRD | 397 KB |
| everything Cilium | 64 KB |
| `appprojects.argoproj.io` CRD | 17 KB |
| everything else | 116 KB |

Cilium on its own would fit, with about 9 KB to spare once the control plane config itself
is accounted for. That margin is one chart bump wide, and going over it does not produce a
warning - the container exits 255 with `exec /sbin/init: argument list too long`, and
`talosctl` then panics parsing the address of a node that never started. A bootstrap that
breaks that way on a Cilium upgrade is worse than one that never used the mechanism, so dev
does not use it at all.

What survives is everything that matters downstream: the cluster still boots with
`cni: none` and no kube-proxy, Cilium still comes from the same chart and values, and from
the bootstrap `Application` onwards dev and prod are the same cluster.

### The one thing that follows from it

`rotate-server-certificates` is in `patch-prod.yaml` rather than `patch-all.yaml` for the
same reason, and this is worth understanding before moving it back.

The setting makes the kubelet request a serving certificate from the cluster CA, and
something in-cluster has to approve that CSR - `kubelet-serving-cert-approver`, an ordinary
Deployment, which needs a CNI. Prod resolves the circularity because Talos applies Cilium
from the machine config *during* bootstrap. Dev cannot: it applies the bundle after
`talosctl cluster create` returns, and create does not return while the kubelet is
unhealthy. The kubelet is unhealthy precisely because its serving certificate is unsigned.

The failure is a quiet one. `cluster create` simply never finishes, and the reason is only
visible in the node's own log:

```console
$ docker logs homelab-dev-controlplane-1
[talos] diagnostic still active {"id": "kubelet-csr",
  "message": "kubelet server certificate rotation is enabled, but CSR is not approved",
  "details": ["pending CSRs: csr-srd82"]}
```

So dev kubelets keep their self-signed serving certificates, `kubelet-serving-cert-approver`
is not in `enabledApps` because it would have nothing to approve, and metrics-server is
given `--kubelet-insecure-tls` in
[`values-dev.yaml`](../kubernetes/helm/metrics-server/values-dev.yaml) so its scrapes still
complete. That flag is the narrowest available: it covers metrics-server's connection out to
the kubelets and nothing else, so the API server still verifies metrics-server itself.

Three details in `dev.sh` follow from applying by hand rather than through Talos. CRDs go on
first and are waited for, because `kubectl` will not create the bootstrap `Application`
before the API server knows its kind, and unlike Talos it does not wait between objects. The
apply is server-side, because a client-side apply would try to record that 1.39 MB CRD in a
`last-applied-configuration` annotation and be rejected. And the cert-manager `Certificate`
ArgoCD's chart renders for its own ingress is filtered out, because cert-manager's CRD does
not exist this early - prod embeds the same premature object and Talos logs the failure and
moves on, where `kubectl` would abort the script. The `argocd` Application creates it later,
once cert-manager is up.

The PKI is the one place where dev is deliberately *less* reproducible.
`talosctl cluster create docker` has no `--with-secrets`, and a dev cluster has no reason to
be re-creatable with the same certificates: it is destroyed and rebuilt, never
`apply-config`ed in place.

## What Docker cannot do

The absent items are not oversights, and each one is why the matching component is missing
from `enabledApps` in
[`values-dev.yaml`](../kubernetes/charts/app-of-apps/values-dev.yaml).

- **System extensions.** A schematic builds an *installer* image for a real machine. Docker
  runs the stock `ghcr.io/siderolabs/talos` image, so `i915`, `iscsi-tools`, `nut-client`,
  `btrfs` and `util-linux-tools` are all unavailable. That removes the GPU and the Synology
  CSI driver, and with them every application that needs a PersistentVolume.
- **An install disk.** Nothing is installed; the container *is* the running system. This is
  what `patch-prod.yaml` exists to keep out of the dev config.
- **Anything that has to be approved from inside the cluster before the cluster works.**
  See [the one thing that follows from it](#the-one-thing-that-follows-from-it) below.
- **The things that would touch something real.** external-dns would write into the live
  PiHole and Cloudflare zones, cloudflared would publish the dev cluster on the internet,
  Velero would write to the NAS, and Image Updater would commit image bumps back to the
  branch. None of these fail in dev - they succeed, which is worse.

## Networking, which works better than expected

Cilium runs unmodified, from the same
[`values.yaml`](../kubernetes/helm/cilium/values.yaml) prod uses: kube-proxy replacement,
eBPF host routing, and KubePrism on `localhost:7445` all behave the same in a container.

L2 announcements work too, and this is the useful part. The Docker bridge is attached to the
workstation, so an address Cilium announces on it is reachable from the host directly, with
no port forwarding and no `kubectl port-forward`:

```console
$ kubectl -n traefik get svc traefik -o jsonpath='{.status.loadBalancer.ingress[0].ip}'
10.5.0.210
$ curl -k https://10.5.0.210/
```

Which means Traefik, Ingress and cert-manager can all be exercised for real. Add the address
to `/etc/hosts` for `argocd.dev.zmuda.pro` and `hubble.dev.zmuda.pro` and the ingress path is
end to end.

Certificates are self-signed. The dev
[ClusterIssuers](../kubernetes/kustomizations/cert-manager/overlays/dev/cluster-issuer.yaml)
keep prod's two names, `lets-encrypt-prod` and `lets-encrypt-staging`, so no manifest needs
an overlay just to name a different issuer - but they issue locally rather than through ACME,
because the DNS-01 solver needs the Cloudflare token and burning the rate limit on the real
zone for a throwaway hostname would be a poor trade. Hence `curl -k`.

## The branch is the environment

`dev.sh` refuses to create a cluster whose tracked branch does not exist on `origin`:

```console
error: branch 'feat/dev-env' does not exist on origin. Push it first
```

This is worth stating plainly, because it is the one thing about the dev cluster that
surprises people. ArgoCD fetches from GitHub. It does not read the working tree the script
runs in. An uncommitted change is not in the dev cluster, and neither is a committed one that
has not been pushed. The edit-test loop is commit, push, sync - not save and re-run.

The branch itself is set in
[`overlays/dev/argocd-bootstrap.yaml`](../kubernetes/kustomizations/argocd/overlays/dev/argocd-bootstrap.yaml),
and every child Application inherits it through `$ARGOCD_APP_SOURCE_TARGET_REVISION`. It has
to match the branch that file is read from: the `argocd` Application syncs
`kubernetes/kustomizations/argocd/overlays/dev`, so a mismatch means ArgoCD reconciles the
value back to whatever is committed and the cluster walks away from the branch under test.

## Logging in

There is no Dex and no GitHub SSO -
[`values-dev.yaml`](../kubernetes/helm/argocd/values-dev.yaml) does not load
`values-secret.yaml`, because those are prod's own credentials. The local admin account is
the way in:

```sh
kubectl -n argocd get secret argocd-initial-admin-secret \
  -o jsonpath='{.data.password}' | base64 -d
```

git-crypt still matters: the branch dev tracks carries the same encrypted files `main` does,
so the repo-server still needs the key, and `argocd-gitcrypt-secret.yaml` is in the dev
bootstrap bundle for exactly that reason. `dev.sh` checks the working tree is unlocked before
rendering, because kustomize would otherwise embed the ciphertext as if it were the key and
every unlock would fail silently.

## Cold starts, and the one that had to be designed around

Everything converges at once on a cluster this fast, so races that hardware timing hides
show up here reliably. One is worth knowing in detail, because it does not resolve itself.

metrics-server sits one sync wave behind cert-manager, and asks cert-manager for its own
serving certificate. On a fresh dev cluster the webhook is routinely still coming up when
that `Certificate` is applied:

```text
Certificate/metrics-server  SyncFailed  Internal error occurred: failed calling webhook
  "webhook.cert-manager.io": ... connect: no route to host
```

A failed sync retries. This one does not, because the same sync also applied the Deployment,
so the operation sits in `Running` waiting for a pod that is itself waiting for the secret
the failed `Certificate` would have produced. Nothing times out. The cluster stays wedged
until someone deletes the Application.

Rather than leave that in the boot path,
[`values-dev.yaml`](../kubernetes/helm/metrics-server/values-dev.yaml) has metrics-server
generate its own certificate, which takes cert-manager out of the picture; the API server
then cannot verify it, so `apiService.insecureSkipTLSVerify` is true here and false in prod.
Dev gives up testing that one integration in exchange for booting unattended.

The same shape can appear elsewhere - a custom resource applied alongside the workload that
needs it, one wave after the controller that admits it. The symptom is an Application stuck
`Running` with a `SyncFailed` resource in its sync result, and the recovery is to delete it
and let `argocd-bootstrap` recreate it once the webhook answers:

```sh
kubectl -n argocd get application <app> \
  -o jsonpath='{.status.operationState.phase}{"\n"}'
kubectl -n argocd delete application <app>
```

## Adding a component to dev

1. Add its template stem to `enabledApps` in
   [`values-dev.yaml`](../kubernetes/charts/app-of-apps/values-dev.yaml).
2. If it is a chart with values, add a `values-dev.yaml` beside its `values.yaml`. The
   template reads `values-{{ .Values.env }}.yaml`, so the file has to exist even when it
   overrides nothing - `{}` and a comment saying why is the honest form.
3. If it is a kustomization that differs, give it `base/` and `overlays/{dev,prod}/` and
   point the template at `overlays/{{ .Values.env }}`.

Components with no dev overlay are not half-configured, they are switched off: for a
prod-only component, `enabled: false` *is* the dev overlay.

## See also

- [Talos](talos.md) — machine config generation, version pinning, the inline manifest
- [GitOps](gitops.md#one-entry-point-and-one-thing-before-it) — what the bootstrap
  Application starts
- [Operations](operations.md#bootstrapping) — the bare-metal equivalent of this page
