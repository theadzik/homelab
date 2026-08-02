# Operations

Day-0 to day-2: how the cluster is created from nothing, how a change gets into it, and
what to check when something does not settle.

## Bootstrapping from nothing

The only manual steps are the ones that must exist before GitOps can. Everything after step
five happens on its own.

### 1. Nodes

Talos machines PXE boot from the NAS, so a replacement node needs no installation media. The
machine configs are generated from the inputs in [talos/](../talos/), never hand-written:

```bash
./talos/generate.sh                        # writes controlplane.yaml, worker.yaml, talosconfig

talosctl apply-config --insecure -n 192.168.0.2 --file talos/controlplane.yaml
talosctl bootstrap -n 192.168.0.2
talosctl health -n 192.168.0.2
talosctl kubeconfig
```

That script needs `secret-certs.yaml` decrypted, so on a machine that has never held the
git-crypt key, do step 3 first. What the script does and why it exists is in
[Talos](talos.md#regenerating).

The cluster comes up with no CNI and no kube-proxy, by design. Nothing can be scheduled
until the next step, and Talos reboots a node that has waited about ten minutes for a CNI,
so do not stop here.

The full PXE and DHCP setup is written up in
[PXE Booting Talos Linux from Synology NAS](https://zmuda.pro/talos-linux-using-pxe).

### 2. Install Cilium by hand, once

ArgoCD installs everything in this cluster except the thing that lets ArgoCD run at all. A
cluster with no CNI schedules no pods, so Cilium goes on manually and its Application adopts
the release later, at sync wave -80.

From the repository root, because the values path is relative to it:

```bash
helm template cilium --version 1.20.0 oci://quay.io/cilium/charts/cilium \
  -f kubernetes/helm/cilium/values.yaml -n kube-system \
  | sed -n '/^---$/,$p' | kubectl apply -f -

kubectl get nodes                                # Ready, not NotReady
kubectl -n kube-system rollout status ds/cilium
```

That `sed` is doing real work. Helm 4.2.1 prints `Pulled:` and `Digest:` lines to **stdout**
before the rendered YAML when templating straight from an `oci://` reference
([helm#32215](https://github.com/helm/helm/issues/32215)), which is enough to break
`kubectl apply -f -`. Both lines go to stdout, so redirecting stderr does not help.
Discarding everything before the first `---` does. Pulling the chart first with
`helm pull … --untar` and templating the local directory avoids it too.

### 3. Unlock the repository

Either path works: an exported key file, or the GPG key registered as a git-crypt
collaborator.

```bash
git-crypt unlock /path/to/homelab-git-crypt.key   # symmetric key held elsewhere
git-crypt unlock                                  # GPG key already in the local keyring
```

Without one of them, the Talos secrets bundle, the ArgoCD values and the git-crypt Secret
applied in step 5 are all ciphertext. That Secret is in this repository but encrypted with
the key it carries, so it cannot bootstrap itself. See
[GitOps](gitops.md#secrets-in-a-public-repository).

### 4. Install ArgoCD by hand, once

```bash
helm repo add argo https://argoproj.github.io/argo-helm
helm install argocd argo/argo-cd \
  -f kubernetes/helm/argocd/values.yaml \
  -f kubernetes/helm/argocd/values-secret.yaml \
  -n argocd --create-namespace
```

This is the last `helm install` anyone runs against this cluster.

### 5. Hand over

```bash
kubectl apply -k kubernetes/kustomizations/argocd
```

That applies the git-crypt key secret and the
[`argocd-bootstrap` Application](../kubernetes/kustomizations/argocd/argocd-bootstrap.yaml),
which points at the app-of-apps chart. ArgoCD works through the sync waves from there,
adopting the Cilium release from step 2 and its own release along the way.

Expect Cilium's CA to change once when that adoption happens. The chart marks `cilium-ca`,
`hubble-server-certs` and `hubble-relay-client-certs` as non-idempotent and generates them
fresh on every render, so the certificates ArgoCD renders are not the ones installed by
hand. Hubble rotates its certificates on the first sync and carries on.

To bootstrap from a branch instead of `main`, change `targetRevision` in that one file. The
revision is inherited by every child application, so the whole cluster follows.

## Adding an application

1. **Choose a delivery style**: upstream chart with values, kustomize, or a local chart.
   The [comparison is in GitOps](gitops.md#upstream-charts-local-values).
2. **Write the manifests**, under `kubernetes/helm/<app>/` or
   `kubernetes/kustomizations/<app>/`. Any file containing a Secret must have `secret` in
   its filename, or it will be committed in plaintext.
3. **Register it** in [`kubernetes/bootstrap/charts/app-of-apps/templates/`](../kubernetes/bootstrap/charts/app-of-apps/templates/).
   An app that is not registered here does not exist. Give it a sync wave if it has
   dependencies. Workloads with none can leave the default.
4. **Decide its exposure** with a `dns-type` label, `internal` for PiHole or `external` for
   Cloudflare, and add a `CiliumNetworkPolicy`. See
   [Networking](networking.md#dns-one-cluster-two-providers).
5. **Validate before committing** (below).
6. **Open a pull request.** Merging is what deploys it. The sync-wave inventory regenerates
   itself afterwards.

## Validating a change

Never edit [`sync-waves-inventory.md`](../sync-waves-inventory.md). It is generated.

```bash
# everything the repository lints, in one pass
pre-commit run --all-files

# render what you changed
kustomize build kubernetes/kustomizations/<app>
helm template <release> <chart> -f kubernetes/helm/<app>/values.yaml
helm lint charts/<chart>          # local charts only
```

A changed values file has to be rendered with the chart the app-of-apps template names, so
start there when working out what to run. [Conventions](conventions.md#kubernetes-rendering)
has the details.

## Trying a change without merging it

Point the bootstrap Application at a branch and the entire cluster follows it, because
`targetRevision` is passed down to every child. That makes a whole-cluster change reviewable
in the real cluster, and revertible by editing one line back.

For a single application, ArgoCD's UI can target a branch for that app alone.

## Day-2 runbook

| Symptom | First check | Usual cause |
| --- | --- | --- |
| App stuck `OutOfSync` on the same field forever | `argocd app diff <app>` | A field written by another controller. Needs an `ignoreDifferences` entry, as metrics-server has |
| App `Progressing` on a fresh cluster | Sync wave of what it depends on | Something in an earlier wave has not gone healthy. Waves do not advance until they do |
| New image not deploying | Image Updater logs, then the tag filter | The tag does not match `allowTags`. Usually that is correct behaviour, see the [filters](gitops.md#image-updates-that-leave-a-trail) |
| Certificate not issued | `kubectl describe certificate`, then the Challenge | DNS-01 propagation, or the Cloudflare token secret |
| Ingress returns 404 | Ingress `ingressClassName` and the `dns-type` label | Record created in the wrong zone, or no record at all |
| Pod cannot reach something | Hubble UI, filter to drops | A `CiliumNetworkPolicy` doing exactly what it says |
| Kyverno reports a verification failure | The image's tags in GHCR | An image published before the current attestation format, or one built by a workflow the policy does not trust |
| PVC will not bind | Storage class name, then the CSI controller logs | Wrong protocol for the access mode. `ReadWriteMany` needs NFS |
| Kubernetes version rolls back after `apply-config` | The image pins in `talos/patch-all.yaml` | `talosctl upgrade-k8s` writes the new version to the nodes but not to the patch. See [Talos](talos.md#version-pinning) |

### Restoring a volume

Velero holds CSI snapshots for labelled PVCs, 12-hourly, for 7 days:

```bash
velero backup get
velero restore create --from-backup <backup> \
  --include-namespaces <ns> \
  --include-resources persistentvolumeclaims,persistentvolumes
```

What is and is not covered is in
[Storage and backups](storage-and-backups.md#what-is-actually-recoverable).

### Rebooting or replacing a node

Traefik and cloudflared each run two replicas with `DoNotSchedule` topology spread and a
PodDisruptionBudget, so a single node can go away without taking ingress with it. Drain,
reboot, and the descheduler rebalances afterwards.

A replacement node is a PXE boot and a `talosctl apply-config`. No data lives on it.

## The local machine

[`ansible/`](../ansible/) sets up a workstation to work on this repository. It is not cluster
configuration.

```bash
./ansible/install-scripts/bootstrap.sh              # fresh machine: git identity, brew, pipx, ansible
ansible-playbook ansible/playbooks/local-setup.yaml -K
```

Roles: `general`, `wsl`, `oh-my-zsh`, `git`, `k8s-tools`, `docker`, `node`, `vscode`. The
playbook asserts a supported distribution (Ubuntu or Fedora) before it changes anything, and
`k8s-tools` installs the toolchain these docs assume: `kubectl`, `helm`, `kustomize`, `k9s`,
`kubectx`, `talosctl`, `velero`, `argocd`.

The `git` role downloads `git-crypt`, asserts its SHA256 against a pinned value, and fails
the play on a mismatch instead of installing whatever arrived. Anything added under
`ansible/` should follow the same pattern: fully qualified module names, an idempotency
guard on every `command` or `shell` task, and pinned artifact URLs with an expected
checksum.

## See also

- [GitOps](gitops.md): why merging is deployment
- [Conventions](conventions.md): the checks that run before a merge is possible
- [Bootstrap notes](../kubernetes/bootstrap/README.md): the chart the bootstrap points at
