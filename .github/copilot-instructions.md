# Homelab Agent Instructions

> This file is the shared instruction source for AI coding agents in this repo.
> `CLAUDE.md` at the repository root is a symlink to this file — edit only this
> one; both Claude Code and GitHub Copilot read the same content.

## Scope

This repository defines:

1. GitOps-managed Kubernetes workloads for a homelab cluster.
2. Local developer machine bootstrap via Ansible roles/playbooks.
3. Talos Linux node configuration (machine config schematic + patches).
4. Supporting app images/scripts (for example custom ArgoCD with git-crypt).

Use declarative changes in git. Avoid one-off manual cluster changes.

## Canonical Docs

Prefer linking to and following these files instead of duplicating guidance:

- [Repository overview](../README.md)
- [Sync-wave inventory (auto-generated)](../sync-waves-inventory.md)
- [Synology/storage notes](../SYNOLOGY.md)
- [Helm charts notes](../charts/README.md)
- [Talos config](../talos/) — `schematic.yaml` and `patch-all.yaml` generate Talos machine config/patches.

## Supplementary, More Specific Agent Instructions

Beyond this file, the repo has narrower-scope agent guidance. GitHub Copilot
applies some of these automatically by path; Claude Code does not auto-load
them, so check the relevant one manually before touching matching paths:

- [.github/instructions/ansible-playbook-conventions.instructions.md](instructions/ansible-playbook-conventions.instructions.md) —
  role/task structure, idempotency, and variable-placement rules for anything
  under `ansible/`. Applies automatically for Copilot (`applyTo: ansible/**/*.y*ml`).
- [.github/agents/homelab-release-reviewer.agent.md](agents/homelab-release-reviewer.agent.md) —
  pre-merge reviewer persona for Kubernetes changes (sync-wave ordering, secret
  filename policy, app-of-apps registration). Use its checklist when reviewing
  or self-checking a release-affecting change, even outside Copilot's agent UI.
- [.github/skills/validate-k8s-change/SKILL.md](skills/validate-k8s-change/SKILL.md) —
  procedure to auto-detect changed kustomizations/Helm values and run
  `kustomize build` / `helm template` / `helm lint` before commit.

## Core Rules For Agents

1. Do not manually edit `sync-waves-inventory.md`; update app-of-apps templates under `kubernetes/bootstrap/charts/app-of-apps/templates/` instead.
2. Never commit plaintext secrets. Secret manifests should include `secret` in filename and remain git-crypt compatible (see `.gitattributes`).
3. For kustomize-based apps, inspect `kustomization.yaml` for patches/transformers/images before editing base manifests.
4. Keep new app resources declarative and organized under either `kubernetes/helm/` or `kubernetes/kustomizations/`.
5. Place temporary files only under `.tmp/` at repository root.
6. When editing anything under `ansible/`, follow [ansible-playbook-conventions.instructions.md](instructions/ansible-playbook-conventions.instructions.md).

## Kubernetes Change Workflow

1. Choose deployment style:

- Helm-based app: add/update `kubernetes/helm/<app>/values.yaml`.
- Kustomize-based app: add/update `kubernetes/kustomizations/<app>/` resources plus `kustomization.yaml`.

1. Ensure app registration and sync wave in app-of-apps templates.
2. Validate before finishing:

- `kustomize build kubernetes/kustomizations/<app>`
- `helm template <chart> -f kubernetes/helm/<app>/values.yaml`
- Or run the [validate-k8s-change](skills/validate-k8s-change/SKILL.md) procedure, which auto-detects and runs both.

1. If ordering/dependencies are involved (for example cert-manager before dependents), verify sync-wave placement.

## Local Dev (Ansible) Workflow

1. Fresh machine bootstrap (before Ansible is available): `ansible/install-scripts/bootstrap.sh`.
2. Primary playbook: `ansible/playbooks/local-setup.yaml`.
3. Roles live in `ansible/playbooks/roles/` (general, wsl, oh-my-zsh, git, k8s-tools, docker, node, vscode).
4. Shared variables are in `ansible/playbooks/vars/local-common.yaml`.
5. Typical run command:

- `ansible-playbook ansible/playbooks/local-setup.yaml -K`

## Validation And Quality Gates

Follow repo linting and checks before finalizing changes — all are wired into `.pre-commit-config.yaml`, so `pre-commit run --all-files` covers them in one pass:

- YAML formatting: `.yamlfmt.yaml` (via the `yamlfmt` hook)
- Markdown: `.markdownlint.yaml`
- Dockerfiles: `.hadolint.yaml`
- Python style/imports: `setup.cfg` (isort, black, flake8)
- Shell scripts: shellcheck
- Security baseline: `.sec.baseline` (detect-secrets)

When changing Helm chart sources in `charts/`, also run `helm lint` for impacted charts.
