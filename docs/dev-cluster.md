# Dev cluster

Three Talos nodes as Docker containers on the workstation, bootstrapped the same way the
bare-metal cluster is, from the same repository and the same charts. It exists so that a
change to Cilium, to ArgoCD, or to the bootstrap path itself can be tried somewhere that is
not the cluster serving the vault and the media library.

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
| CNI | Cilium, kube-proxy replacement, L2 announcements | the same, from the same values file |
| Bootstrap | `talos/bootstrap/prod` as an inline manifest | `talos/bootstrap/dev`, same mechanism |
| Cluster PKI | `secret-certs.yaml`, reproducible across runs | minted fresh per cluster, thrown away with it |
| LoadBalancer pool | `192.168.0.210-220` on the LAN | `10.5.0.210-220` on the Docker bridge |

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
