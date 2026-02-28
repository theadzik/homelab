# Media Stack - Homelab Values

This directory contains homelab-specific values for the Media Stack Helm chart.

## Chart Location

The chart definition is located in `/charts/media-stack/`.

## Usage with Helm

```bash
# Install using local chart with homelab values
helm install media-stack ../../../charts/media-stack \
  -f values.yaml \
  -n media \
  --create-namespace
```

## Usage with ArgoCD

Reference the chart and values in your ArgoCD Application:

```yaml
apiVersion: argoproj.io/v1alpha1
kind: Application
metadata:
  name: media-stack
  namespace: argocd
spec:
  source:
    repoURL: <your-repo>
    targetRevision: HEAD
    path: charts/media-stack
    helm:
      valueFiles:
        - ../../kubernetes/helm/media/values.yaml
  destination:
    server: https://kubernetes.default.svc
    namespace: media
```

## Values

This `values.yaml` file contains environment-specific configuration:

- Custom domain names
- Storage class names
- Resource allocations
- ArgoCD sync options
- Priority classes
