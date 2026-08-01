# custom-argocd

Upstream ArgoCD with `git-crypt` added, because every secret in this repository is committed
encrypted and the repo-server has to be able to read them.

## How it works

The image installs the `git-crypt` binary, downloaded in a build stage and verified against
a pinned SHA256. It then renames ArgoCD's `git` and puts a wrapper in its place:

```sh
#!/bin/sh
$(dirname $0)/git.bin "$@"
ec=$?
[ "$1" = fetch ] || exit $ec
git-crypt unlock "$GITCRYPT_KEY_PATH" 2>/dev/null
exit $ec
```

Every `git fetch` the repo-server performs is followed by an unlock. Decryption happens
where it is needed, on every refresh, with nobody in the loop. The wrapper is deliberately
inert for every other git subcommand, and the unlock's failure is swallowed so that a
repository with nothing encrypted still works.

`GITCRYPT_KEY_PATH` and the volume behind it are set in
[the ArgoCD values](../../kubernetes/helm/argocd/values.yaml). The Secret itself is
[committed](../../kubernetes/kustomizations/argocd/argocd-gitcrypt-secret.yaml), encrypted
by git-crypt with the key it contains. That is harmless, since reading it already requires
being able to read the repository, and it keeps the cluster's access declarative.

## Versioning

The image is built `FROM quay.io/argoproj/argocd:$TAG`, and the tag is not chosen by hand.
[`custom-argocd.yaml`](../../.github/workflows/custom-argocd.yaml) reads the chart version
out of the [ArgoCD Application](../../kubernetes/bootstrap/charts/app-of-apps/templates/argocd.yaml),
resolves that chart's `appVersion` with `helm search`, and builds and tags with it.

So the patched image cannot drift from the ArgoCD the cluster is actually running. Bumping
the chart version in git is the only way to move it, and doing so builds a matching image on
merge.

See [GitOps](../../docs/gitops.md#secrets-in-a-public-repository) for why this exists, and
[Supply chain](../../docs/supply-chain.md) for how it is built and verified.
