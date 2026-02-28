# Helm Charts

This directory contains public Helm charts that can be released independently.

## Available Charts

### media-stack

A comprehensive media automation stack for Kubernetes, including:

- Jellyfin (media server with GPU transcoding)
- Radarr (movie management)
- Sonarr (TV series management)
- Bazarr (subtitle management)
- NZBGet (Usenet downloader)

**Chart Location:** `charts/media-stack/`

**Documentation:** See [charts/media-stack/README.md](media-stack/README.md)

## Using Charts

### Local Installation

```bash
# Install with default values
helm install media-stack ./charts/media-stack -n media --create-namespace

# Install with custom values
helm install media-stack ./charts/media-stack -f my-values.yaml -n media
```

### With GitOps (ArgoCD)

Reference the chart in your ArgoCD Application:

```yaml
apiVersion: argoproj.io/v1alpha1
kind: Application
metadata:
  name: media-stack
spec:
  source:
    repoURL: <your-repo-url>
    targetRevision: HEAD
    path: charts/media-stack
    helm:
      valueFiles:
        - ../../kubernetes/helm/media/values.yaml  # Optional: homelab-specific values
  destination:
    server: https://kubernetes.default.svc
    namespace: media
```

## Chart Development

Each chart follows Helm best practices:

- Template helpers in `_helpers.tpl`
- Recommended Kubernetes labels
- Configurable via `values.yaml`
- Comprehensive README documentation

## Homelab-Specific Values

Environment-specific values are stored in `kubernetes/helm/<chart-name>/values.yaml` and override the chart defaults.
