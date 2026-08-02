# Bootstraping local cluster

## Install the CNI first

Nothing below works until a CNI is running. The Talos config sets
`cluster.network.cni.name: none` and disables kube-proxy because Cilium
provides both, so on a fresh cluster no pod can be scheduled — Argo CD
included. Cilium therefore cannot be installed by the GitOps that installs
everything else; it goes on once by hand, and the `cilium` Application
(sync-wave `-80`) adopts it afterwards.

See [CNI installation](../../talos/README.md#cni-installation) in the Talos
README for the command and the Helm OCI caveat. Talos reboots the node about
ten minutes after `talosctl bootstrap` if no CNI appears, so do not leave a
long gap.

Confirm before continuing:

```bash
kubectl get nodes                        # Ready, not NotReady
kubectl -n kube-system rollout status ds/cilium
```

## Install ArgoCD

```bash
# from repo root
helm repo add argo https://argoproj.github.io/argo-helm
helm install argocd argo/argo-cd -f kubernetes/helm/argocd/values.yaml -f kubernetes/helm/argocd/values-secret.yaml -n argocd
kubectl apply -k kubernetes/kustomizations/argocd
```

## Change bootstrap

To change how cluster is bootstrap, edit `kubernetes/kustomizations/argocd/argocd-bootstrap.yaml`
