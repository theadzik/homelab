# The bootstrap chart

[`kubernetes/bootstrap/charts/app-of-apps/`](../kubernetes/bootstrap/charts/app-of-apps/) is
a Helm chart, and its templates are the whole of the app-of-apps pattern: every
`Application` and `ApplicationSet` in the cluster is one file in that directory. An
application that has no template here is not deployed, no matter what else exists under
`kubernetes/helm/` or `kubernetes/kustomizations/`.

[GitOps](gitops.md#one-entry-point-and-one-thing-before-it) covers why the cluster is wired
this way. This page is about the chart itself: how it's reached, and what to know before
adding a template to it.

## Getting ArgoCD running in the first place

The chart is useless without ArgoCD to read it, and ArgoCD is not itself deployed by
GitOps, since nothing can bootstrap the thing that does the bootstrapping. It goes on by
hand, and the sequence is two commands, not one:

```bash
kubectl create namespace argocd

helm template argocd argo/argo-cd --version 10.2.2 \
  -f kubernetes/helm/argocd/values.yaml \
  -f kubernetes/helm/argocd/values-secret.yaml \
  -n argocd | kubectl apply -f -
```

`helm template`, not `helm install`. The chart renders no `Namespace` object of its own,
which is why the namespace is created first, but it does render everything else the
`argocd` namespace needs. There is no Helm release to track afterwards, because ArgoCD
manages its own chart as soon as it exists. See
[GitOps](gitops.md#one-entry-point-and-one-thing-before-it) for how that self-management
works.

Only once ArgoCD's CRDs exist can the second command run:

```bash
kubectl apply -k kubernetes/kustomizations/argocd
```

That kustomization is what actually reaches this chart. It creates the git-crypt secret and
the [`argocd-bootstrap` Application](../kubernetes/kustomizations/argocd/argocd-bootstrap.yaml),
an `Application` object pointing at `kubernetes/bootstrap/charts/app-of-apps`. Trying to
apply it before ArgoCD exists fails outright: `Application` is a custom resource, and its
CRD is one of the things the first command installs.

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
