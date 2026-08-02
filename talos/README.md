# Talos configuration

Node config for the `homelab-prod` cluster. The machine configs are **generated**,
not hand-maintained — the files tracked here are the inputs.

| File | Purpose |
| --- | --- |
| `generate.sh` | Regenerates everything below from the inputs above. |
| `schematic.yaml` | Image Factory schematic (system extensions). Its ID is embedded in `machine.install.image`. |
| `patch-all.yaml` | Config patch applied to all node types. |
| `secret-nut-client.yaml` | Config patch holding the NUT credentials. git-crypt encrypted. |
| `secret-certs.yaml` | Cluster secrets bundle (PKI, tokens). git-crypt encrypted. Not generated — see below. |
| `controlplane.yaml`, `worker.yaml`, `talosconfig` | Generator output. **git-ignored** — it contains the full cluster PKI in plaintext. |

## Regenerating

```sh
./generate.sh
```

That wraps `talosctl gen config` with the two patches and the secrets bundle,
sets the talosconfig endpoint, and validates the result.

`--with-secrets` is what makes this reproducible. Without it every run mints a
new PKI and new join tokens, so the output cannot be applied to the running
cluster. The bundle is not derived from the patches — it is cluster state, and
`secret-certs.yaml` is the only irreplaceable file in this directory.
Everything else here can be regenerated from it.

It can be rebuilt from a running control plane node, but only while you still
have a working `talosconfig` to authenticate with — so this is a repair path,
not a backup:

```sh
talosctl -n 192.168.0.2 get machineconfig v1alpha1 -o jsonpath='{.spec}' > /tmp/cp.yaml
talosctl gen secrets --from-controlplane-config /tmp/cp.yaml -o secret-certs.yaml
```

`--with-docs=false --with-examples=false` just strips the inline comments so the
output is diffable against what is running.

### One thing the generator cannot set

`talosctl gen config` always writes `talosconfig` with `endpoints: []`, and
there is no flag or config-patch field that changes this. The `https://…:6443`
argument it takes is the *Kubernetes* API endpoint — it lands in
`cluster.controlPlane.endpoint` in the machine config. The talosconfig
`endpoints` are the *Talos* API (port 50000), which the generator has no way to
infer, so it leaves them empty. `generate.sh` fills them in afterwards with:

```sh
talosctl --talosconfig talosconfig config endpoint 192.168.0.2
```

If you ever run `gen config` by hand, remember this step — without it every
`talosctl` call needs an explicit `-e`.

**Only control plane nodes belong in `endpoints`.** An endpoint is the machine
`talosctl` connects to; `-n/--nodes` is what the command acts on, and the
endpoint proxies to it. Workers serve requests for themselves but refuse to
forward:

```console
$ talosctl -e <worker> -n <any other node> version
error getting version: rpc error: code = PermissionDenied desc = no request forwarding
```

Since the client spreads calls across the configured endpoints, adding a worker
produces intermittent rather than consistent failures. Add control plane IPs
here as the cluster grows; that gives `talosctl` failover. It does nothing for
`kubectl`, which reads its own server URL from the kubeconfig — HA there needs
a VIP or load balancer in front of the Kubernetes API.

Its admin client certificate is also re-minted on every run with a fresh
one-year validity. It is signed by the CA from the secrets bundle, so it works
against the running cluster, but `talosconfig` will never be byte-identical
between runs the way the machine configs are.

## Version pinning

`talosctl gen config` defaults the Kubernetes version to whatever the local
`talosctl` binary ships with, which silently drifts the generated config every
time the CLI is upgraded. The Kubernetes version is therefore pinned explicitly
in `patch-all.yaml`:

- `machine.kubelet.image`
- `cluster.apiServer.image`, `cluster.controllerManager.image`,
  `cluster.scheduler.image`, `cluster.proxy.image`

Bump all five together. Note that `talosctl upgrade-k8s` rewrites these fields
on the nodes directly — after running it, update `patch-all.yaml` to match or
the next `apply-config` will roll Kubernetes back.

The Talos version is separate and lives in the `machine.install.image` tag. It
is a Talos version (`v1.13.7`), not a Kubernetes one — the schematic ID in that
same tag comes from `schematic.yaml`.

## Verifying a change

```sh
talosctl validate -c controlplane.yaml -m metal
talosctl validate -c worker.yaml -m metal
```

Generated worker configs carry the `cluster.apiServer`/`controllerManager`/
`scheduler` image pins because `--config-patch` applies to every node type.
Workers ignore those fields; it is the only divergence from the live worker
config.
