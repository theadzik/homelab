# Bootstraping local cluster

## Install ArgoCD

```bash
# from repo root
helm repo add argo https://argoproj.github.io/argo-helm
helm install argocd argo/argo-cd --version 9.5.4 -f kubernetes/helm/argocd/values.yaml -f kubernetes/helm/argocd/values-secret.yaml -n argocd
kubectl apply -k kubernetes/kustomizations/argocd
```

## Change bootstrap

To change how cluster is bootstrap, edit `kubernetes/kustomizations/argocd/argocd-bootstrap.yaml`
