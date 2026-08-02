# Networking

Two ways in, one way out, and no port forward anywhere. This page traces both request
paths end to end and explains the pieces they pass through.

## The two paths

```mermaid
flowchart LR
    subgraph ext[From the internet]
        u1[visitor] --> cfe[Cloudflare edge]
        cfe --> tun["cloudflared pod<br/>(outbound tunnel)"]
    end

    subgraph int[From the LAN]
        u2[laptop] --> ph["PiHole<br/>internal DNS"]
        ph --> vip["LoadBalancer IP<br/>192.168.0.50-100"]
    end

    tun --> tsvc[Traefik]
    vip --> tsvc
    tsvc --> app[application pod]
```

**Externally**, `zmuda.pro` resolves to a Cloudflare-proxied CNAME pointing at
`<tunnel-id>.cfargotunnel.com`. Cloudflare terminates the visitor's TLS and hands the
request to a `cloudflared` pod over a connection that pod opened outbound. Nothing listens
on the router, so there is no NAT rule to get wrong.

**Internally**, PiHole on the NAS resolves hostnames like `argocd.zmuda.pro` to an address
from the Cilium load-balancer pool, announced on the LAN by ARP. Those addresses are RFC 1918
and the tunnel only forwards to Traefik. There is no route from the internet to them at all,
so no rule has to deny one.

Both paths terminate at the same Traefik service, so an application is configured once and
its exposure is decided entirely by which DNS record points at it.

## Cilium

Cilium is the CNI, and it replaces kube-proxy outright. Talos ships with
`cluster.network.cni.name: none` and `cluster.proxy.disabled: true`, so there is no CNI or
proxy to remove first. The cluster has no networking at all until Cilium is installed.

That last part has a consequence at bootstrap. ArgoCD cannot be the thing that installs
Cilium, because ArgoCD is a pod and pods need a CNI. Talos creates it directly instead, and
the `cilium` Application adopts the release afterwards at sync wave -80, before any workload
or platform component that will depend on it. See
[Talos](talos.md#bootstrapping-cilium-and-argocd) for how.

```yaml
kubeProxyReplacement: true
k8sServiceHost: localhost
k8sServicePort: 7445
```

`localhost:7445` is [KubePrism](https://docs.siderolabs.com/talos/latest/kubernetes-guides/configuration/kubeprism),
Talos's node-local API server proxy. Pointing Cilium at it solves a chicken-and-egg problem.
The agent needs the API server, and reaching the API server through a Service needs the
agent. It also survives a control-plane restart without the agents noticing.

The `cgroup` and `securityContext.capabilities` blocks in
[values.yaml](../kubernetes/helm/cilium/values.yaml) exist because Talos mounts cgroups
itself and grants no capability the workload has not asked for. Both blocks are copied
straight from Cilium's Talos guidance.

`bpf.hostLegacyRouting: true` comes from the same guidance and fixes a specific collision.
Talos forwards kube-dns to the host resolver by default from 1.8 onwards, and that does not
work with Cilium's eBPF host-routing. Cilium's
[Talos prerequisites](https://docs.cilium.io/en/stable/installation/k8s-install-helm/) are
blunt about the consequence: set it, or DNS does not work. It routes host traffic through
the kernel's normal path instead of the eBPF shortcut, which costs some throughput.

### Load balancing without a load balancer

There is no cloud provider here, so `type: LoadBalancer` needs an answer. Cilium provides
one in two objects:

```yaml
# CiliumLoadBalancerIPPool
blocks:
  - start: "192.168.0.50"
    stop: "192.168.0.100"
```

```yaml
# CiliumL2AnnouncementPolicy
externalIPs: true
loadBalancerIPs: true
```

A Service gets an address from the pool, and a node answers ARP for it. Traefik names
`loadBalancerClass: io.cilium/l2-announcer` explicitly, so the Service says which
implementation it expects instead of taking whatever controller happens to be watching.

Failover is a lease. The values shorten it deliberately:

```yaml
l2announcements:
  leaseDuration: 3s
  leaseRenewDeadline: 1s
  leaseRetryPeriod: 200ms
```

The defaults are measured in tens of seconds, which is a long outage for a node reboot on a
three-node cluster where reboots are routine. The cost is more traffic to the API server,
which this cluster has room for.

### Observability

Hubble relay and UI are enabled and published at `hubble.zmuda.pro` (internal only). Seeing
the flows is what makes the network policies below maintainable. A denied flow shows up as a
drop with both identities named, instead of an application that hangs for reasons nobody can
reconstruct.

## Traefik

Traefik is the only ingress controller, deployed from the upstream OCI chart with
[local values](../kubernetes/helm/traefik/values.yaml).

Since everything else in the cluster is reachable only through it, its values look more like
a control-plane component's than an application's:

| Setting | Effect |
| --- | --- |
| `replicas: 2` + `topologySpreadConstraints` with `DoNotSchedule` | The two replicas cannot land on the same node, so a node reboot never takes ingress with it |
| `podDisruptionBudget: minAvailable: 1` | Voluntary eviction cannot drain both |
| `priorityClassName: system-cluster-critical` | Under memory pressure, something else is evicted first |
| `minReadySeconds: 10` | A rollout that crash-loops slowly is still caught before both replicas are gone |

### Getting the real client IP back

A request that arrives through Cloudflare has Cloudflare's address as its source. Two
mechanisms restore the original, and both are needed:

- `forwardedHeaders.trustedIPs` and `proxyProtocol.trustedIPs` list every Cloudflare
  address range, so `X-Forwarded-For` from those sources is believed and from anywhere else
  is not.
- The [`cloudflare` plugin middleware](../kubernetes/kustomizations/traefik/cloudflare-middleware.yaml)
  rewrites the request header from `CF-Connecting-IP`, trusting only `10.0.0.0/8`. That is
  the pod network, which is where `cloudflared` sits.

Ingresses that are exposed externally opt into the middleware by annotation. Trusting a
forwarded header from anywhere is how access logs, rate limits and IP-based rules all stop
meaning anything at once, so the trust boundary is written down in both places.

HTTP is redirected to HTTPS permanently at the entry point, and access logs are JSON with
`User-Agent` retained.

## Cloudflare Tunnel

[`cloudflared`](../kubernetes/kustomizations/cloudflared/) runs two replicas, spread across
nodes, at `high-priority`, with a single ingress rule:

```yaml
ingress:
  - service: https://traefik.traefik.svc.cluster.local:443
```

The tunnel is a dumb pipe. It does not know about applications, and adding a public hostname
is a DNS change plus an ingress label, never a tunnel config change. Its liveness probe hits
`/ready` on the metrics port, so a tunnel that is running but not connected gets restarted
instead of looking healthy.

Credentials come from a git-crypt encrypted secret, and the image tag is pinned by
kustomize and moved by [Image Updater](gitops.md#image-updates-that-leave-a-trail).

## DNS: one cluster, two providers

Both DNS zones are managed by external-dns, from the same `Ingress` and `Service` objects.
The same chart is installed twice, and a label decides which release owns a record:

| Release | Provider | Selector | Policy |
| --- | --- | --- | --- |
| pihole | PiHole on the NAS | `dns-type in (internal)` | `upsert-only`, `registry: noop` |
| cloudflare | Cloudflare | `dns-type in (external)` | default |

```yaml
# both releases
domainFilters:
  - zmuda.pro
sources:
  - service
  - ingress
```

Split-horizon DNS usually means maintaining two zone files that disagree. Here it means one
label on one manifest, and the record appears in the right place. The blog demonstrates the
whole mechanism in two overlays of the same base. Prod is `dns-type: external` with a
Cloudflare-proxied CNAME to the tunnel. Dev is `dns-type: internal` and exists only on the
LAN.

PiHole gets `registry: noop` and `upsert-only` because it has no TXT registry to track
record ownership, so external-dns must not be allowed to conclude that a record it cannot
account for should be deleted.

## Certificates

cert-manager issues from Let's Encrypt using a **DNS-01** solver with a Cloudflare API
token, and both a staging and a production
[ClusterIssuer](../kubernetes/kustomizations/cert-manager/cluster-issuer.yaml) exist.

DNS-01 is the only option that works here, and it is also the better one. HTTP-01 requires
the validation server to reach the host, which is impossible for a name that resolves only
on the LAN. With DNS-01, internal-only services still get publicly trusted certificates.
`argocd.zmuda.pro`, `hubble.zmuda.pro` and the rest are real HTTPS, with no click-through
warning and no private CA that every device has to be taught about.

Applications request a certificate with a single annotation:

```yaml
annotations:
  cert-manager.io/cluster-issuer: lets-encrypt-prod
```

## Network policy

Every exposed application namespace carries a `CiliumNetworkPolicy`, and the default shape
is: ingress from the Traefik namespace only, egress nothing.

```yaml
# blog
ingress:
  - fromEndpoints:
      - matchLabels:
          k8s:io.kubernetes.pod.namespace: traefik
egress: []
```

A static site has no reason to originate a connection, so it cannot. Where egress is really
needed it gets enumerated in the narrowest form Cilium supports.
[Vaultwarden](../kubernetes/kustomizations/vaultwarden/netpol.yaml) may reach kube-dns,
`smtp.protonmail.ch` on 587, `*.bitwarden.com` on 443 for push notifications, and the NAS on
the Garage S3 port. Nothing else, including the rest of the LAN.

Writing those rules against `smtp.protonmail.ch` and the `traefik` namespace, instead of
against IP ranges, is what makes them readable a year later. A CIDR stops meaning what it
meant as soon as the pod behind it moves.

Name-based rules have one requirement that is easy to miss. Cilium learns which IP a name
resolves to by watching the pod's DNS answers, so the DNS rule has to route them through its
proxy:

```yaml
- toEndpoints:
    - matchLabels:
        k8s:io.kubernetes.pod.namespace: kube-system
        k8s-app: kube-dns
  toPorts:
    - ports: [{ port: "53", protocol: UDP }, { port: "53", protocol: TCP }]
      rules:
        dns:
          - matchPattern: "*"
```

Without that `rules.dns` block, DNS still works and every `toFQDNs` rule silently matches
nothing, because Cilium never saw the answer that would have told it which IP to allow.

## See also

- [Architecture](architecture.md): where these components sit in the boot order
- [Security](security.md): what watches the traffic these policies allow
- [Operations](operations.md): exposing a new application on either path
