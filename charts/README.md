# Helm charts

Charts written here rather than consumed from upstream. They are kept independent of this
homelab's configuration so they can be used by anyone: no hardcoded storage classes, no
assumed ingress controller, no cluster-specific values.

Charts for upstream software live upstream — this directory is only for the ones that do not
exist elsewhere. See [GitOps](../docs/gitops.md#upstream-charts-local-values) for how the
two are combined.

## media-stack

A complete media automation stack: Jellyfin, Radarr, Sonarr, Bazarr and NZBGet, with
optional GPU transcoding through Dynamic Resource Allocation, VPA, network policies and
per-service persistence.

Full reference, including every value and the API versions each optional feature needs:
[`media-stack/README.md`](media-stack/README.md).

```bash
helm install media-stack ./media-stack -n media --create-namespace
helm install media-stack ./media-stack -f my-values.yaml -n media
```

## How this repository consumes them

The chart is one source of an ArgoCD Application and the homelab's values are another, so
the chart stays generic while the cluster-specific configuration lives in
`kubernetes/helm/<chart>/values.yaml`:

```yaml
sources:
  - path: charts/media-stack
    repoURL: "{{ .Values.spec.sources.repoURL }}"
    targetRevision: "{{ .Values.spec.sources.targetRevision }}"
    helm:
      releaseName: media
      valueFiles:
        - $repo/kubernetes/helm/media/values.yaml
```

## Contributing to a chart

Charts are versioned with SemVer in `Chart.yaml`; bump it in the same commit as the change,
because ArgoCD tracks this repository's revision rather than a chart release.

```bash
helm lint media-stack
helm template media-stack ./media-stack -f ../kubernetes/helm/media/values.yaml
```

Conventions: template helpers in `_helpers.tpl`, recommended Kubernetes labels on every
object, every optional feature behind a value that defaults to off, and a README that states
which cluster capability each option requires.
