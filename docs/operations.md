# Operations

Day-0 to day-2: how the cluster is created from nothing, how a change gets into it, and
what to check when something does not settle.

## Bootstrapping

Cilium and ArgoCD both come up on their own, embedded in the control plane's machine
config and applied by Talos itself as part of `talosctl apply-config`. See
[Talos](talos.md#bootstrapping-cilium-and-argocd) for how. What is left is getting that
machine config generated and onto the node.

### 1. Unlock the repository

Either path works: an exported key file, or the GPG key registered as a git-crypt
collaborator.

```bash
git-crypt unlock /path/to/homelab-git-crypt.key   # symmetric key held elsewhere
git-crypt unlock                                  # GPG key already in the local keyring
```

Do this before the next step. `talos/generate.sh` reads `secret-certs.yaml` and
`secret-nut-client.yaml`, both git-crypt encrypted, and renders ArgoCD from
`kubernetes/helm/argocd/values.yaml` alongside them. See
[GitOps](gitops.md#secrets-in-a-public-repository).

### 2. Nodes

Talos machines PXE boot from the NAS, so a replacement node needs no installation media. The
machine configs are generated from the inputs in [talos/](../talos/), never hand-written:

```bash
./talos/generate.sh                        # writes controlplane.yaml, worker.yaml, talosconfig

talosctl apply-config --insecure -n 192.168.0.2 --file talos/controlplane.yaml
talosctl bootstrap -n 192.168.0.2
talosctl health -n 192.168.0.2
talosctl kubeconfig
```

`talosctl bootstrap` is where Cilium and ArgoCD actually get created, along with the
[`argocd-bootstrap` Application](../kubernetes/kustomizations/argocd/argocd-bootstrap.yaml)
that points ArgoCD at the app-of-apps chart. From there ArgoCD works through the sync waves
on its own, adopting the Cilium and ArgoCD releases Talos just created and reconfiguring
itself with the full values, secrets included, the moment its own `argocd` Application
syncs.

Expect Cilium's CA to change once when that adoption happens. The chart marks `cilium-ca`,
`hubble-server-certs` and `hubble-relay-client-certs` as non-idempotent and generates them
fresh on every render, so the certificates ArgoCD renders differ from the ones Talos
installed at boot. Hubble rotates its certificates on the first sync and carries on.

```bash
kubectl get nodes                                    # Ready, not NotReady
kubectl -n argocd get application argocd-bootstrap    # exists, then Synced
```

The full PXE and DHCP setup is written up in
[PXE Booting Talos Linux from Synology NAS](https://zmuda.pro/talos-linux-using-pxe).

To bootstrap from a branch instead of `main`, change `targetRevision` in
`argocd-bootstrap.yaml` before running `generate.sh`. The revision is inherited by every
child application, so the whole cluster follows.

## Adding an application

1. **Choose a delivery style**: upstream chart with values, kustomize, or a local chart.
   The [comparison is in GitOps](gitops.md#upstream-charts-local-values).
2. **Write the manifests**, under `kubernetes/helm/<app>/` or
   `kubernetes/kustomizations/<app>/`. Any file containing a Secret must have `secret` in
   its filename, or it will be committed in plaintext.
3. **Register it** in [`kubernetes/charts/app-of-apps/templates/`](../kubernetes/charts/app-of-apps/templates/).
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
helm lint kubernetes/charts/<chart>    # local charts only
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
| Kubernetes version rolls back after `apply-config` | `KUBERNETES_VERSION` in `talos/generate.sh` | `talosctl upgrade-k8s` writes the new version to the nodes but not to the script. See [Talos](talos.md#version-pinning) |

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
`kubectx`, `talosctl`, `velero`, `argocd`, `yq`, `jq`.

The `git` role downloads `git-crypt`, asserts its SHA256 against a pinned value, and fails
the play on a mismatch instead of installing whatever arrived. Anything added under
`ansible/` should follow the same pattern: fully qualified module names, an idempotency
guard on every `command` or `shell` task, and pinned artifact URLs with an expected
checksum.

## See also

- [GitOps](gitops.md): why merging is deployment
- [Conventions](conventions.md): the checks that run before a merge is possible
- [Bootstrap chart](bootstrap.md): the app-of-apps chart `argocd-bootstrap` points at, and
  how to add to it
