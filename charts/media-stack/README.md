# Media Stack Helm Chart

A comprehensive Helm chart for deploying media services in Kubernetes, including Jellyfin, Radarr, Sonarr, Bazarr, and NZBGet.

## Overview

This chart provides a complete media automation stack, consolidating multiple services into a single, manageable deployment. Perfect for home lab environments and private media servers.

## Services Included

- **Jellyfin** - Media server with GPU transcoding support (8096)
- **Radarr** - Movie management and automation (7878)
- **Sonarr** - TV series management and automation (8989)
- **Bazarr** - Subtitle management and automation (6767)
- **NZBGet** - High-performance Usenet downloader (6789)

## Requirements

### Kubernetes Version

- **Minimum:** Kubernetes 1.28+
- **Recommended:** Kubernetes 1.30+ for best compatibility
- **GPU Support:** Kubernetes 1.34+ required for stable Dynamic Resource Allocation API

### Required Dependencies

These components must be present in your cluster:

1. **Storage Provisioner**
   - For PersistentVolumeClaims (PVCs)
   - Examples: Longhorn, Ceph, NFS provisioner, cloud provider storage classes

### Optional Dependencies

These components are optional but enable additional features:

1. **Ingress Controller** (if `ingress.enabled: true`)
   - Examples: Traefik, NGINX Ingress, Istio
   - Required for external HTTP/HTTPS access
   - Chart supports any ingress controller compatible with `networking.k8s.io/v1`

2. **Network Policy Support**
   - Standard NetworkPolicy: Built into most CNI plugins (Calico, Cilium, Weave)
   - CiliumNetworkPolicy: Requires Cilium CNI (`networkPolicy.type: CiliumNetworkPolicy`)
   - Optional but recommended for network segmentation

3. **Vertical Pod Autoscaler (VPA)** (if `vpa.enabled: true`)
   - Requires VPA controller installed in cluster
   - API: `autoscaling.k8s.io/v1`
   - Automatically adjusts resource requests/limits

4. **GPU Support** (if `resourceClaimTemplate.enabled: true`)
   - **Kubernetes 1.34+** with Dynamic Resource Allocation (DRA)
   - API: `resource.k8s.io/v1` (stable)
   - Required for Jellyfin hardware transcoding
   - Note: Consider alternative GPU passthrough methods (device plugins, RuntimeClass) for older clusters

5. **Cert-Manager** (optional)
   - For automatic TLS certificate provisioning
   - Use with `ingressAnnotations: cert-manager.io/cluster-issuer`

### API Compatibility

| Resource              | API Version               | Kubernetes Version              |
| --------------------- | ------------------------- | ------------------------------- |
| StatefulSet           | apps/v1                   | 1.9+ (GA)                       |
| Service               | v1                        | All versions                    |
| Ingress               | networking.k8s.io/v1      | 1.19+ (GA)                      |
| NetworkPolicy         | networking.k8s.io/v1      | 1.7+ (GA)                       |
| CiliumNetworkPolicy   | cilium.io/v2              | Requires Cilium CNI             |
| VPA                   | autoscaling.k8s.io/v1     | 1.28+ (requires VPA controller) |
| ResourceClaimTemplate | resource.k8s.io/v1        | 1.34+ (GA)                      |

## Installation

### From local chart

```bash
helm install media-stack ./charts/media-stack -f values.yaml -n media --create-namespace
```

### Using custom values

```bash
helm install media-stack ./charts/media-stack -f my-values.yaml -n media --create-namespace
```

## Configuration

The chart is configured via `values.yaml` with the following main sections:

### Global Settings

```yaml
common:
  timezone: UTC  # Set your timezone
  puid: 1000     # User ID for LinuxServer.io containers
  pgid: 1000     # Group ID for LinuxServer.io containers
  imagePullPolicy: IfNotPresent
```

### Persistent Volumes

Configure shared and per-service PVCs:

```yaml
persistentVolumeClaims:
  downloads:
    enabled: true
    storage: 1Ti
    storageClassName: ""  # Use your cluster's storage class

services:
  jellyfin:
    pvc:
      config:
        name: jellyfin-config
        storage: 10Gi
        storageClassName: ""  # Use your cluster's storage class
```

### Per-Service Configuration

Each service can be individually configured:

```yaml
services:
  jellyfin:
    enabled: true
    tag: "latest"          # Image tag (repository is global)
    replicas: 1
    port: 8096
    resources:
      requests:
        cpu: 1000m
        memory: 2Gi
    useGPU: true           # Enable GPU resource claim
    env:                   # Custom environment variables
      HOSTNAME: jellyfin.example.com
    ingress:
      enabled: true
      host: jellyfin.example.com
      tls:
        enabled: true
        secretName: jellyfin-tls
```

### VPA Configuration

```yaml
vpa:
  enabled: true
  minReplicas: 1
```

### Ingress Configuration

Configure global annotations applied to all ingresses:

```yaml
ingressAnnotations:
  cert-manager.io/cluster-issuer: letsencrypt-prod
  traefik.ingress.kubernetes.io/router.entrypoints: websecure
```

Or set per-service annotations:

```yaml
services:
  jellyfin:
    ingress:
      enabled: true
      host: jellyfin.example.com
      annotations:
        traefik.ingress.kubernetes.io/router.middlewares: default-crowdsec@kubernetescrd
      tls:
        enabled: true
        secretName: jellyfin-tls
```

Service-specific annotations are merged with global annotations. Service annotations take precedence if there are conflicts.

### Service-Specific Options

- **Security Context** - Define security policies per service
- **Liveness Probes** - Configure health checks (httpGet, tcpSocket)
- **Environment Variables** - Set custom env vars per service
- **Ingress** - Configure external access with TLS and custom annotations

## Features

### Network Policy

- **Ingress**: Allows pod-to-pod communication within namespace and traffic from Traefik
- **Egress**: Allows all outbound traffic by default (configurable)
- **Type**: Standard Kubernetes NetworkPolicy or CiliumNetworkPolicy
- **Configuration**: Set via `networkPolicy.ingress` and `networkPolicy.egress` lists
- **Disable**: Set `networkPolicy.enabled: false` to remove network segmentation
- **Selector**: Uses component labels (`app.kubernetes.io/component`)

### Storage

- Shared downloads PVC for all services
- Per-service configuration storage (SSD)
- Special storage for NZBGet intermediate files
- ArgoCD sync options to prevent deletion

### Resource Management

- **Per-service requests/limits**: Fine-grained control for each service
- **Vertical Pod Autoscaler (VPA)**:
  - Enable with `vpa.enabled: true`
  - Uses `Initial` update mode (apply recommendations on pod creation, no restarts)
  - Optional `minReplicas` setting for pod disruption budget protection
  - Requires VPA controller in cluster
- **Priority Classes**: Per-service or global priority class assignment

### GPU Support

- Optional GPU resource claim template for Jellyfin
- Configurable via `resourceClaimTemplate.enabled`
- Using i915 resource claim template

## Example: Disabling a Service

To disable a service, set `enabled: false`:

```yaml
services:
  bazarr:
    enabled: false
```

## Example: Custom Image Tag

Override the image tag for a service:

```yaml
services:
  radarr:
    tag: "5.0.4"  # Uses global imageRepository by default
```

Or override both repository and tag:

```yaml
services:
  radarr:
    repository: my-registry.com/radarr  # Optional per-service override
    tag: "5.0.4"
```

## Helm Values Organization

This chart can be used with a single `values.yaml` file or split into:

- Chart defaults in `values.yaml`
- Environment-specific overrides in a separate values file

Example deployment with overrides:

```bash
helm install media-stack ./charts/media-stack \
  -f charts/media-stack/values.yaml \
  -f my-environment-values.yaml
```

## Chart Structure

```text
media/
├── Chart.yaml              # Chart metadata
├── values.yaml             # Default values
├── templates/
│   ├── _helpers.tpl        # Template helpers for labels and names
│   ├── namespace.yaml      # Namespace and annotations
│   ├── networkpolicy.yaml  # NetworkPolicy or CiliumNetworkPolicy
│   ├── pvc.yaml            # All PersistentVolumeClaims
│   ├── secrets.yaml        # Service secrets
│   ├── statefulset.yaml    # All StatefulSets
│   ├── service.yaml        # All Services
│   ├── ingress.yaml        # All Ingresses
│   ├── vpa.yaml            # VerticalPodAutoscalers
│   └── resourceclaimtemplate.yaml  # GPU resource claim
└── README.md               # This file
```

### Template Helpers

The chart uses template helpers defined in `_helpers.tpl` following Helm best practices:

- **`media-stack.name`** - Chart name with override support
- **`media-stack.fullname`** - Fully qualified app name
- **`media-stack.chart`** - Chart name and version for labeling
- **`media-stack.labels`** - Common labels for all resources
- **`media-stack.selectorLabels`** - Selector labels for a component
- **`media-stack.componentLabels`** - Combined common + component labels

### Helm Recommended Labels

All resources are labeled following [Helm best practices](https://helm.sh/docs/chart_best_practices/labels/):

**Common labels** (applied to all resources):

- `helm.sh/chart: media-stack-1.0.0` - Chart name and version
- `app.kubernetes.io/name: media-stack` - Application name
- `app.kubernetes.io/instance: <release-name>` - Release identifier
- `app.kubernetes.io/version: "1.0.0"` - Application version
- `app.kubernetes.io/part-of: media-stack` - Logical application grouping
- `app.kubernetes.io/managed-by: Helm` - Management tool

**Component labels** (per-service):

- `app.kubernetes.io/component: <service-name>` - Component (jellyfin, radarr, etc.)

**Selector labels** (used by Services, Ingress, NetworkPolicy):

- `app.kubernetes.io/name: media-stack`
- `app.kubernetes.io/instance: <release-name>`
- `app.kubernetes.io/component: <service-name>`

**Label helpers**: Use template helpers from `_helpers.tpl`:

- `media-stack.componentLabels` - Full label set for a service
- `media-stack.selectorLabels` - Subset for matching pods

## Notes

- **StatefulSets**: Used for persistent ordering and stable hostnames
- **Shared storage**: All services mount `/downloads` PVC for accessible media library
- **Per-service config**: Each service gets its own PVC
- **Secrets**: NZBGet credentials loaded via `envFrom` from Secret resource
- **GPU support**: Optional via ResourceClaimTemplate (Kubernetes 1.34+)
- **TLS certificates**: Managed via cert-manager (optional)
- **Image management**: Flexible global repository with per-service tag overrides

## Troubleshooting

### Dependency Issues

**PVCs stuck in Pending?**

- Check if storage provisioner is installed: `kubectl get storageclass`
- Verify PVC events: `kubectl describe pvc -n media`
- Ensure `storageClassName` in values.yaml matches available storage classes

**Ingress not working?**

- Verify ingress controller is running: `kubectl get pods -n ingress-nginx` (or your ingress namespace)
- Check ingress resource: `kubectl describe ingress -n media`
- Ensure DNS points to your ingress controller's external IP

**NetworkPolicy not enforcing?**

- Verify CNI supports NetworkPolicy: Check your CNI plugin documentation
- For CiliumNetworkPolicy: Ensure Cilium CNI is installed and running
- Test with `networkPolicy.enabled: false` to isolate the issue

**VPA not adjusting resources?**

- Check if VPA controller is installed: `kubectl get pods -n kube-system | grep vpa`
- Verify VPA CRDs exist: `kubectl get crd | grep verticalpodautoscaler`
- View VPA recommendations: `kubectl describe vpa -n media`

**GPU/ResourceClaimTemplate errors?**

- Kubernetes 1.34+ required for Dynamic Resource Allocation (stable API)
- Uses `resource.k8s.io/v1` stable API
- Check feature gate: `DynamicResourceAllocation` must be enabled
- For older clusters (1.31-1.33), consider alternative GPU methods (device plugins, RuntimeClass)

### Service Issues

**Service not starting?**

- Check PVC availability: `kubectl get pvc -n media`
- Verify image availability: `kubectl logs -n media <pod-name>`
- Check resource requests: `kubectl describe statefulset -n media <service-name>`

**Jellyfin GPU transcoding not working?**

- Verify `resourceClaimTemplate.enabled: true` and `useGPU: true` for Jellyfin
- Check GPU resource allocation in your cluster
- Consider alternative GPU passthrough methods (device plugins, RuntimeClass)
- Disable GPU with `useGPU: false` if not needed

**Permission errors in pods?**

- Verify `puid` and `pgid` match your storage permissions
- LinuxServer.io containers require proper UID/GID mapping
- Check security context settings for each service
