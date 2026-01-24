# Homelab Copilot Instructions

## Architecture Overview

This is a **GitOps-driven Kubernetes homelab** with three primary components:

1. **Kubernetes Cluster** (Talos Linux on bare metal) - Managed via ArgoCD with git-crypt encrypted secrets
2. **Local Development Setup** (Ansible playbooks) - Configures WSL/Linux dev environment with Docker, K8s tools
3. **Custom Applications** (Dockerfiles + Helm/Kustomize manifests) - ArgoCD-deployed apps with sync-wave ordering

**Key Principle**: Everything declarative, version-controlled, and automatically synced via ArgoCD. No manual kubectl applies.

## Critical Workflows

### Deploying Applications to Kubernetes

1. **Chart-based apps** → Add values file to `kubernetes/helm/<app-name>/values.yaml`
2. **Non-chart apps** → Create Kustomization in `kubernetes/kustomizations/<app-name>/`
   - Must include `kustomization.yaml` with resources list
   - Reference shared overlays like `image-pull-secret` via `../image-pull-secret`
3. **Register in App-of-Apps** → Bootstrap chart auto-discovers from `kubernetes/kustomizations/` and `kubernetes/helm/`
4. **Check sync-wave ordering** → Review `sync-waves-inventory.md` (auto-generated); sync-waves prevent dependency failures

Example: Blog app uses Kustomization with `deployment.yaml`, `ingress.yaml`, `netpol.yaml`, `service.yaml`, `vpa.yaml`.

### Secrets Management

- **Encrypted with git-crypt** - Never commit plaintext secrets
- Custom ArgoCD image (`apps/custom-argocd/`) includes git-crypt binary to decrypt during sync
- Bootstrap configuration in `kubernetes/bootstrap/argocd-bootstrap.yaml` handles ArgoCD setup

### Local Development Changes

- Modify Ansible playbooks in `ansible/playbooks/local-setup.yaml` and role tasks
- Roles directory: `ansible/playbooks/roles/{wsl,oh-my-zsh,git,k8s-tools,docker}`
- Run: `ansible-playbook ansible/playbooks/local-setup.yaml` (uses `ansible.cfg` with `inventory.yaml`)

## Project-Specific Patterns

### Kustomization Structure

Each app follows this pattern:

```text
kubernetes/kustomizations/<app-name>/
├── kustomization.yaml (declares resources)
├── namespace.yaml
├── deployment.yaml / statefulset.yaml
├── service.yaml
├── ingress.yaml
├── vpa.yaml (Vertical Pod Autoscaler - common pattern)
├── netpol.yaml (Network Policy - security pattern)
└── pvc.yaml (if needed)
```

### Helm Values Organization

- Shared values in `values-shared.yaml` (e.g., external-dns, crowdsec)
- Provider-specific overrides in `values-pihole.yaml`, `values-cloudflare.yaml`
- Database values separate in `database-values.yaml` (e.g., tandoor)

### High-Availability Patterns (Traefik Example)

```yaml
deployment:
  replicas: 2  # Minimum HA
podDisruptionBudget:
  minAvailable: 1  # Cluster can handle one pod disruption
priorityClassName: "system-cluster-critical"
topologySpreadConstraints:  # Spread across nodes
  whenUnsatisfiable: DoNotSchedule
```

## Code Organization

| Directory | Purpose |
| --------- | ------- |
| `kubernetes/bootstrap/` | ArgoCD bootstrap, app-of-apps chart, sync-wave inventory |
| `kubernetes/helm/` | Helm values for chart-based deployments |
| `kubernetes/kustomizations/` | Kustomizations for non-chart apps |
| `ansible/playbooks/` | Local dev environment setup via roles |
| `apps/custom-argocd/` | Custom ArgoCD image with git-crypt support |
| `apps/vaultwarden/` | Backup/restore scripts (initContainer + CronJob pattern) |
| `talos/` | Talos Linux OS schematic and patches |

## Integration Points

- **ArgoCD Sync Waves**: Defined by `argocd.argoproj.io/sync-wave` annotation; negative values run first
- **External-DNS**: Updates DNS (Pihole/Cloudflare) automatically based on Ingress resources
- **Traefik Plugins**: CrowdSec bouncer and Cloudflare integration via experimental plugins
- **Synology CSI**: Storage provisioning via Synology NAS
- **git-crypt**: Handles secret decryption during ArgoCD sync

## Common Commands

- **ArgoCD App Status**: `argocd app list` / `argocd app get <app-name>`
- **Validate Kustomization**: `kustomize build kubernetes/kustomizations/<app-name>`
- **Validate YAML**: Use yamllint (config: `.yamllint.yaml`)
- **Check Helm Values**: `helm template <chart> -f kubernetes/helm/<app>/values.yaml`

## Linting & Quality Standards

- **YAML**: `.yamllint.yaml` (strict formatting)
- **Markdown**: `.markdownlint.yaml`
- **Docker**: `.hadolint.yaml` (Hadolint rules)
- **Python**: `setup.cfg` (flake8 max 120 chars, isort single-line)
- **Security**: `.sec.baseline` (baseline for security scans)
- **Pre-commit**: `.pre-commit-config.yaml` (runs automated checks)

## When Modifying This Codebase

1. **Adding an app**: Create `kubernetes/kustomizations/<app-name>/` or `kubernetes/helm/<app-name>/values.yaml`
2. **Fixing deployment issues**: Check sync-waves first (order matters), then validate with kustomize/helm template
3. **Updating secrets**: Use git-crypt; never commit unencrypted; secrets should always include "secret" in the file name
4. **Talos changes**: Edit `talos/schematic.yaml` or `talos/patch-all.yaml`, regenerate config
5. **Local dev changes**: Update Ansible roles and playbooks, commit to git
6. **Modifying Kubernetes resources**: Before adding fields to base resources (e.g., `deployment.yaml`, `service.yaml`), check the `kustomization.yaml` for patches, transformers, and overlays. Fields may be added dynamically via kustomize mechanisms rather than directly in base files. Run `kustomize build kubernetes/kustomizations/<app-name>` to verify final output.
