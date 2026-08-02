# Conventions

The rules this repository actually enforces, and where each one is enforced. Most are
mechanical. The few that are not get checked in review, because those are the ones that fail
silently.

## Layout

| Path | Contains | Rule |
| --- | --- | --- |
| [`kubernetes/bootstrap/`](../kubernetes/bootstrap/) | The app-of-apps chart | Every application is registered here or it does not exist |
| [`kubernetes/helm/<app>/`](../kubernetes/helm/) | Values for upstream charts | Chart stays upstream, only values live here |
| [`kubernetes/kustomizations/<app>/`](../kubernetes/kustomizations/) | Manifests for apps without a chart worth using | `kustomization.yaml` is the entry point, including for plain manifests |
| [`charts/`](../charts/) | Helm charts written here | Publishable on their own, SemVer in `Chart.yaml` |
| [`apps/`](../apps/) | Dockerfiles and the scripts they package | One directory per image, matching a build workflow |
| [`talos/`](../talos/) | Node config inputs | The machine configs are generated from these and never committed |
| [`ansible/`](../ansible/) | Workstation setup | Not cluster configuration |
| [`docs/`](.) | These pages | Reasoning that outlives any single manifest |

## Quality gates

[`pre-commit`](../.pre-commit-config.yaml) runs everything in one pass:

| Hook | Covers | Notes |
| --- | --- | --- |
| `yamlfmt` | Every YAML file | Excludes `templates/` and Image Updater's generated files, which are not ours to format |
| `markdownlint` | Every Markdown file | `MD013` (line length) is off, so prose wraps by meaning and not by column |
| `hadolint` | Dockerfiles | |
| `shellcheck` | Shell scripts | The backup and restore scripts are POSIX `sh`, and this is what keeps them so |
| `isort`, `black`, `flake8` | The one Python script | 120 columns, single-line imports |
| `detect-secrets` | Everything | Against a [baseline](../.sec.baseline). `*secret*` files are excluded, since git-crypt ciphertext is high-entropy by construction |
| `pretty-format-json`, `end-of-file-fixer`, `trailing-whitespace`, `check-added-large-files`, `check-merge-conflict`, `mixed-line-ending` | Everything | The cheap ones that keep diffs about content |

Hook versions are pinned and updated by Dependabot's `pre-commit` ecosystem. An unpinned
hook stops gaining rules the moment nobody looks at it.

```bash
pre-commit run --all-files
```

### Kubernetes rendering

Passing the linters above says nothing about whether a manifest still renders. Before
committing anything under `kubernetes/` or `charts/`:

```bash
kustomize build kubernetes/kustomizations/<app>
helm template <release> <chart> -f kubernetes/helm/<app>/values.yaml
helm lint charts/<chart>
```

Working out what to render is most of the effort. A changed values file only makes sense
together with the app-of-apps template that consumes it, since that template holds the
chart, the repo and the release name to render with. For a kustomize app, check
`kustomization.yaml` for patches, transformers and `images:` entries before assuming an edit
to a base manifest is enough.

### Merge gates

`main` is deployed, so it is protected: squash merges only, linear history, no force-push,
code-owner review, review threads resolved, and CodeQL scanning as a required check.
Details in [Security](security.md#repository-controls).

Commit subjects follow [Conventional Commits](https://www.conventionalcommits.org/)
(`feat:`, `fix:`, `ci:`, `build:`, `docs:`, `chore:`), with an optional scope. Automated
image bumps use `build:`, which keeps them distinguishable from human changes at a glance.

## Charts

Charts under [`charts/`](../charts/) are written here instead of consumed from upstream,
which means keeping them independent of this homelab's configuration so anyone could use
them: no hardcoded storage classes, no assumed ingress controller, no cluster-specific
values. Cluster-specific configuration stays in `kubernetes/helm/<chart>/values.yaml`, same
as an upstream chart; see [GitOps](gitops.md#upstream-charts-local-values).

SemVer in `Chart.yaml` is bumped in the same commit as the change, because ArgoCD tracks
this repository's revision and not a chart release. A few conventions beyond that:
template helpers in `_helpers.tpl`, recommended Kubernetes labels on every object, every
optional feature behind a value that defaults to off, and a README that states which
cluster capability each option requires. Linting and rendering a chart follow the same
commands as any other Kubernetes change, in
[Kubernetes rendering](#kubernetes-rendering) above.

## Ansible

Roles under [`ansible/`](../ansible/) configure a workstation, not the cluster, but they
follow their own rules:

- Fully qualified module names (`ansible.builtin.*`, `community.general.*`), and a module in
  preference to `command` or `shell` wherever one exists.
- Every `command` or `shell` task carries an idempotency guard: `creates`, `removes`, or an
  explicit `changed_when`.
- No downloads of "latest". Pin the artifact URL to a version and assert its SHA256, the way
  the `git` role does for `git-crypt`, so a changed binary fails the play instead of being
  installed.
- Cross-role values in `playbooks/vars/local-common.yaml`, role-owned defaults in
  `roles/<role>/defaults/main.yaml`.

```bash
ansible-playbook ansible/playbooks/local-setup.yaml --syntax-check
ansible-playbook ansible/playbooks/local-setup.yaml --check
```

## See also

- [Operations](operations.md#adding-an-application): these conventions applied end to end
- [Supply chain](supply-chain.md#dependencies): the dependency automation these pins feed
