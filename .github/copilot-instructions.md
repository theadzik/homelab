# Homelab Copilot Instructions

## Scope

This repository defines:

1. GitOps-managed Kubernetes workloads for a homelab cluster.
2. Local developer machine bootstrap via Ansible roles/playbooks.
3. Supporting app images/scripts (for example custom ArgoCD with git-crypt).

Use declarative changes in git. Avoid one-off manual cluster changes.

## Canonical Docs

Prefer linking to and following these files instead of duplicating guidance:

- [Repository overview](../README.md)
- [Sync-wave inventory (auto-generated)](../sync-waves-inventory.md)
- [Synology/storage notes](../SYNOLOGY.md)
- [Helm charts notes](../charts/README.md)
- [Ansible bootstrap helper docs](../ansible/install-scripts/README.md)

## Core Rules For Agents

1. Do not manually edit `sync-waves-inventory.md`; update app-of-apps templates under `kubernetes/bootstrap/charts/app-of-apps/templates/` instead.
2. Never commit plaintext secrets. Secret manifests should include `secret` in filename and remain git-crypt compatible.
3. For kustomize-based apps, inspect `kustomization.yaml` for patches/transformers/images before editing base manifests.
4. Keep new app resources declarative and organized under either `kubernetes/helm/` or `kubernetes/kustomizations/`.
5. Place temporary files only under `.tmp/` at repository root.

## Kubernetes Change Workflow

1. Choose deployment style:

- Helm-based app: add/update `kubernetes/helm/<app>/values.yaml`.
- Kustomize-based app: add/update `kubernetes/kustomizations/<app>/` resources plus `kustomization.yaml`.

1. Ensure app registration and sync wave in app-of-apps templates.
2. Validate before finishing:

- `kustomize build kubernetes/kustomizations/<app>`
- `helm template <chart> -f kubernetes/helm/<app>/values.yaml`

1. If ordering/dependencies are involved (for example cert-manager before dependents), verify sync-wave placement.

## Local Dev (Ansible) Workflow

1. Primary playbook: `ansible/playbooks/local-setup.yaml`.
2. Roles live in `ansible/playbooks/roles/` (general, wsl, oh-my-zsh, git, k8s-tools, docker, node).
3. Shared variables are in `ansible/playbooks/vars/local-common.yaml`.
4. Typical run command:

- `ansible-playbook ansible/playbooks/local-setup.yaml`

## Validation And Quality Gates

Follow repo linting and checks before finalizing changes:

- YAML: `.yamllint.yaml`
- Markdown: `.markdownlint.yaml`
- Dockerfiles: `.hadolint.yaml`
- Python style/imports: `setup.cfg`
- Security baseline: `.sec.baseline`
- Pre-commit hooks: `.pre-commit-config.yaml`

When changing Helm chart sources in `charts/`, also run `helm lint` for impacted charts.
