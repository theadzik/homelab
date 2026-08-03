# The bootstrap chart

[`kubernetes/charts/app-of-apps/`](../kubernetes/charts/app-of-apps/) is
a Helm chart, and its templates are the whole of the app-of-apps pattern: every
`Application` and `ApplicationSet` in the cluster is one file in that directory. An
application that has no template here is not deployed, no matter what else exists under
`kubernetes/helm/` or `kubernetes/kustomizations/`.

[GitOps](gitops.md#one-entry-point-and-one-thing-before-it) covers why the cluster is wired
this way. This page is about the chart itself: how it's reached, and what to know before
adding a template to it.

## Getting ArgoCD running in the first place

The chart is useless without ArgoCD to read it, and ArgoCD is not itself deployed by
GitOps, since nothing can bootstrap the thing that does the bootstrapping. Talos gets it
running instead: `talos/bootstrap/` renders ArgoCD's chart and adds the three
plain manifests that get things moving, and the
whole bundle is applied automatically the moment `talosctl bootstrap` runs. See
[Talos](talos.md#bootstrapping-cilium-and-argocd) for exactly what goes in and why.

One of those three files is
[`argocd-bootstrap.yaml`](../kubernetes/kustomizations/argocd/argocd-bootstrap.yaml), an
`Application` object pointing at `kubernetes/charts/app-of-apps` - this chart.
`Application` is a custom resource, and its CRD comes from the ArgoCD chart rendered
alongside it in the same bundle, so it exists by the time this file is applied.

`argocd-bootstrap` passes its own git revision to every template it renders, as a Helm
parameter:

```yaml
# values.yaml
spec:
  sources:
    repoURL: "https://github.com/theadzik/homelab"
    targetRevision: HEAD
```

Change `targetRevision` on that one Application and the entire cluster follows, since every
child inherits the value. That is the whole mechanism behind trying a branch-wide change
without touching `main`.

## Adding a template

A new application needs one file here, following the same shape as its neighbours:

- A sync wave, if it depends on something earlier. The bands are in
  [Architecture](architecture.md#layers).
- Sources: an upstream chart with `valueFiles` under `$repo/kubernetes/helm/<app>/`, or a
  `path` into `kubernetes/kustomizations/<app>/`. See
  [GitOps](gitops.md#upstream-charts-local-values) for the `ref: repo` indirection both
  styles use.
- An `ImageUpdater` resource, if the app's image should track upstream releases on its own.

The [step-by-step version](operations.md#adding-an-application), including where the
manifests themselves go and how to expose the app, is in Operations.

One thing has no home anywhere else: a template whose filename starts with `_` is skipped by
Helm. That is how an application gets parked, kept in the repository but not rendered,
without deleting its definition and losing the history of why it looked the way it did.

## See also

- [GitOps](gitops.md) — why this pattern exists, and what it buys
- [Operations](operations.md#bootstrapping-from-nothing) — the full bootstrap sequence this
  page is one part of
- [Architecture](architecture.md#layers) — the sync-wave bands
