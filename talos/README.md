# Talos configuration

Inputs for the `homelab-prod` machine configs. The configs themselves are generated and are
not committed.

```sh
./generate.sh
```

| File | Purpose |
| --- | --- |
| `generate.sh` | Regenerates the machine configs and `talosconfig` from the inputs below |
| `schematic.yaml` | Image Factory schematic (system extensions), posted fresh to the Factory API on every run to derive the install image |
| `patch-all.yaml` | Config patch applied to all node types, in both environments |
| `patch-prod.yaml` | Config patch for the bare-metal cluster only: install disk, containerd CDI directories, kubelet serving-cert rotation |
| `dev.sh` | Creates and destroys the Docker dev cluster - see [docs/dev-cluster.md](../docs/dev-cluster.md) |
| `bootstrap/prod/`, `bootstrap/dev/` | Kustomizations rendering Cilium and ArgoCD into each cluster's control plane inline manifest |
| `secret-nut-client.yaml` | Config patch holding the NUT credentials, git-crypt encrypted |
| `secret-certs.yaml` | Cluster secrets bundle (PKI, tokens), git-crypt encrypted. Not generated |
| `controlplane.yaml`, `worker.yaml`, `talosconfig` | Generator output, git-ignored, contains the full cluster PKI in plaintext |

`secret-certs.yaml` is the only irreplaceable file here. Everything else can be regenerated
from it.

Full documentation is in [docs/talos.md](../docs/talos.md): the regeneration procedure, the
version pins and how they interact with `talosctl upgrade-k8s`, and how Cilium and ArgoCD
get onto a fresh cluster with nothing applied by hand.
