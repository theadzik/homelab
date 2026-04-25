---
name: validate-k8s-change
description: "Validate Kubernetes changes before commit by auto-detecting changed kustomizations and Helm values/charts, then running kustomize build and helm template/lint with a pass/fail report. Use for pre-commit checks, PR prep, and GitOps safety checks."
argument-hint: "Optional scope: staged (default), all, or a path prefix like kubernetes/helm/external-dns"
---

# Validate Kubernetes Change

Run one command workflow that inspects changed files and validates only impacted Kubernetes targets.

## When To Use

- Before commit for changes under kubernetes/, charts/, or app-of-apps templates.
- Before opening a PR that modifies Helm values, charts, or kustomizations.
- After rebasing when change scope may have shifted.

## Inputs

- Optional argument:
- staged: validate staged files only (default)
- all: validate all working-tree changes vs HEAD
- <path-prefix>: validate only changes under that prefix

## Procedure

1. Discover changed files.
- Use staged scope by default: git diff --name-only --cached
- If argument is all: git diff --name-only HEAD
- If argument is a path prefix, filter to that prefix.
- If no files match kubernetes/, charts/, or app-of-apps templates, stop with a no-op message.

2. Resolve impacted kustomize targets.
- Find unique directories matching kubernetes/kustomizations/<app>/ from changed files.
- Keep only directories that contain kustomization.yaml.
- Validate each target with:
- kustomize build kubernetes/kustomizations/<app>

3. Resolve impacted Helm targets from changed values files.
- For each changed file under kubernetes/helm/<app>/, locate matching app-of-apps template references in kubernetes/bootstrap/charts/app-of-apps/templates/.
- Support these source styles:
- chart + repoURL: helm template <release> <chart> --repo <repoURL> -f <values-file>
- OCI repoURL with path ".": helm template <release> <oci-repo> -f <values-file>
- Local path charts/<chart>: helm lint charts/<chart> and helm template <release> charts/<chart> -f <values-file>
- If multiple valueFiles are defined for one app (for example external-dns), validate each changed values file and also run one combined render when both files are changed.

4. Resolve impacted Helm chart targets from local chart edits.
- For each changed path under charts/<chart>/:
- helm lint charts/<chart>
- If kubernetes/helm/<chart>/values.yaml exists, also run:
- helm template <chart> charts/<chart> -f kubernetes/helm/<chart>/values.yaml

5. Track results and continue on failure.
- Run all discovered validations and collect pass/fail per command.
- Do not stop at the first failure; finish the full impacted set.

6. Report concise outcome.
- Print a summary table with: target, command, status, key error line.
- Exit with failure if any validation failed.
- Include next actions that are specific (for example fix schema/key mismatch in values file, or invalid field in rendered manifest).

## Required Guardrails

- Never edit sync-waves-inventory.md directly.
- For kustomize apps, check kustomization.yaml for patches/transformers/images before assuming base manifest edits are sufficient.
- Keep temporary artifacts under .tmp/ if files are needed.

## Quick Command Pattern

Use this shell pattern during execution to gather candidates quickly:

```bash
changed_files() {
  case "$1" in
    all) git diff --name-only HEAD ;;
    "") git diff --name-only --cached ;;
    *) git diff --name-only --cached | rg "^$1" || true ;;
  esac
}
```

Then derive targets with rg/cut/sort -u and run kustomize/helm validations on the resulting unique sets.
