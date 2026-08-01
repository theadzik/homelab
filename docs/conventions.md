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
| [`talos/`](../talos/) | Node configuration | Schematic plus one patch applied to every node |
| [`ansible/`](../ansible/) | Workstation setup | Not cluster configuration |
| [`docs/`](.) | These pages | Reasoning that outlives any single manifest |
| `.tmp/` | Scratch | The only place temporary files go, and it is ignored |

## Rules that are not linted

Three, and each has a failure mode that no tool catches:

1. **A file containing a Secret has `secret` in its filename.** That pattern is the entire
   git-crypt selector in [`.gitattributes`](../.gitattributes). Get the name wrong and the
   file is committed in plaintext, with no error anywhere.
2. **[`sync-waves-inventory.md`](../sync-waves-inventory.md) is never edited by hand.** It is
   generated from the app-of-apps templates. A manual edit is overwritten on the next push
   to `main`, and misleads everyone until then.
3. **Sync waves express dependencies, not preferences.** A new app that needs cert-manager
   or the CSI driver must be ordered after them, and nothing else should be reordered to
   make room.

All three are on the [release reviewer's](../.github/agents/homelab-release-reviewer.agent.md)
checklist for that reason.

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

The [`validate-k8s-change`](../.github/skills/validate-k8s-change/SKILL.md) skill does the
tedious part. It reads the diff and resolves which kustomizations and values files are
affected. Each values file is then mapped back to the app-of-apps template that consumes it,
which is what tells the skill the chart, repo and release name to render with. It runs every
impacted target and continues past failures, so one broken app does not hide the next.

### Merge gates

`main` is deployed, so it is protected: squash merges only, linear history, no force-push,
code-owner review, review threads resolved, and CodeQL scanning as a required check.
Details in [Security](security.md#repository-controls).

Commit subjects follow [Conventional Commits](https://www.conventionalcommits.org/)
(`feat:`, `fix:`, `ci:`, `build:`, `docs:`, `chore:`), with an optional scope. Automated
image bumps use `build:`, which keeps them distinguishable from human changes at a glance.

## Instructions as repository artifacts

AI coding agents are used on this repository, and their instructions are versioned like any
other configuration: one source of truth, reviewed in pull requests, and kept in sync with
what the linters enforce.

| File | Scope | Applies to |
| --- | --- | --- |
| [`.github/copilot-instructions.md`](../.github/copilot-instructions.md) | Repository-wide conventions | Everything. `CLAUDE.md` at the root is a **symlink** to it, so two tools read one file |
| [`ansible-playbook-conventions`](../.github/instructions/ansible-playbook-conventions.instructions.md) | `ansible/**` | Module choice, idempotency guards, variable placement, pinned downloads with checksum asserts |
| [`homelab-release-reviewer`](../.github/agents/homelab-release-reviewer.agent.md) | Review | A reviewer persona that audits sync-wave ordering, secret filenames and app-of-apps registration, and reports instead of editing |
| [`validate-k8s-change`](../.github/skills/validate-k8s-change/SKILL.md) | Pre-commit | The rendering procedure above, as an executable skill |

The symlink is what keeps this maintainable. Two separate instruction files would drift
within a month, and one file under two names cannot. The checklists follow the same
reasoning. Anything an agent is told to check is something a human reviewer should check
too, so both read the same list.

## Comments

The repository has a house style for comments, and it is applied to YAML as much as to code:
a comment earns its place by saying something the manifest cannot.

```yaml
# Without this the webhook is consulted for every pod in the cluster and
# passes each one without checking anything, since .all() over no images is true.
matchConditions:
  - name: only-our-images
```

Keep that one. Delete `# timeout in seconds` above `timeoutSeconds`, and delete narration of
which approach was tried first. That belongs in the commit message, or on one of these
pages.

Findings and measurements age badly in a manifest. `# takes 20-30s` is stale as soon as
anything changes. `# verification is slow enough to matter near the webhook timeout` stays
true.

## See also

- [Operations](operations.md#adding-an-application): these conventions applied end to end
- [Supply chain](supply-chain.md#dependencies): the dependency automation these pins feed
