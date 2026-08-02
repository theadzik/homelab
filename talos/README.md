# Talos configuration

Inputs for the `homelab-prod` machine configs. The configs themselves are generated and are
not committed.

```sh
./generate.sh
```

| File | Purpose |
| --- | --- |
| `generate.sh` | Regenerates the machine configs and `talosconfig` from the inputs below |
| `schematic.yaml` | Image Factory schematic (system extensions). Its ID is embedded in `machine.install.image` |
| `patch-all.yaml` | Config patch applied to all node types |
| `secret-nut-client.yaml` | Config patch holding the NUT credentials, git-crypt encrypted |
| `secret-certs.yaml` | Cluster secrets bundle (PKI, tokens), git-crypt encrypted. Not generated |
| `controlplane.yaml`, `worker.yaml`, `talosconfig` | Generator output, git-ignored, contains the full cluster PKI in plaintext |

`secret-certs.yaml` is the only irreplaceable file here. Everything else can be regenerated
from it.

Full documentation is in [docs/talos.md](../docs/talos.md): the regeneration procedure, the
Kubernetes version pins and how they interact with `talosctl upgrade-k8s`, and the manual
Cilium install a fresh cluster needs before ArgoCD can start.
