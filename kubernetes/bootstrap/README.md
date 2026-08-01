# Bootstrap

The chart in [`charts/app-of-apps/`](charts/app-of-apps/) is the root of the entire cluster.
Its templates are the ArgoCD `Application` and `ApplicationSet` definitions for every
component; an application that is not registered here does not exist.

## How it is reached

One `Application` is applied by hand,
[`argocd-bootstrap`](../kustomizations/argocd/argocd-bootstrap.yaml), and it points at this
chart. It passes its own git revision down as a Helm parameter, which every template
inherits:

```yaml
# values.yaml
spec:
  sources:
    repoURL: "https://github.com/theadzik/homelab"
    targetRevision: HEAD
```

So changing `targetRevision` in that one Application moves the whole cluster to another
branch. To change how the cluster is bootstrapped at all, edit that file.

The full bootstrap sequence — Talos, git-crypt, ArgoCD, hand-over — is in
[Operations](../../docs/operations.md#bootstrapping-from-nothing).

## Adding an application

Add one template here. It needs:

- A sync wave, if it has dependencies. The bands are described in
  [Architecture](../../docs/architecture.md#layers).
- Sources: an upstream chart with `valueFiles` pointing at `$repo/kubernetes/helm/<app>/`,
  or a `path` into `kubernetes/kustomizations/<app>/`. The
  [multi-source pattern](../../docs/gitops.md#upstream-charts-local-values) explains the
  `ref: repo` indirection.
- An `ImageUpdater` resource, if its image should track upstream releases.

Do not edit [`sync-waves-inventory.md`](../../sync-waves-inventory.md); it is regenerated
from these templates on every push to `main`.

A template whose filename starts with `_` is not rendered by Helm — that is how an
application is parked without deleting its definition.
