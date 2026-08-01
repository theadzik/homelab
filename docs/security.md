# Security

A homelab is a strange security context: the blast radius is small, but the repository is
public, the blog is on the internet, and one of the workloads is a password vault. This
page describes the layers, and is explicit about where they stop.

## Assumptions

- **This repository is readable by anyone.** Everything in it is written on that basis,
  including the secrets, which are encrypted here instead of kept somewhere else.
- **The published images are public**, and so are their SBOMs and provenance attestations.
- **The LAN is not a trust boundary.** Nothing is protected by being "inside", and network
  policy is written between namespaces, not at the perimeter.
- **The maintainer's GitHub account is in scope** for repository controls, but a
  compromise of it is out of scope for the cluster's controls. If an attacker can merge to
  `main`, ArgoCD will deploy it.

## The layers

| Layer | Control | Where |
| --- | --- | --- |
| Perimeter | No inbound ports, outbound-only Cloudflare Tunnel | [Networking](networking.md#the-two-paths) |
| Identity | OIDC groups, deny-by-default ArgoCD RBAC | Below |
| Admission | Pod Security Admission per namespace | Below |
| Admission | Kyverno signature and attestation verification | [Supply chain](supply-chain.md#admission-the-cluster-checks-the-work) |
| Workload | Non-root, read-only root filesystem, no capabilities | Below |
| Network | Default-deny CiliumNetworkPolicy per namespace | [Networking](networking.md#network-policy) |
| Runtime | Falco syscall detection with alert routing | Below |
| Build | Scan before push, sign, attest, daily rescan | [Supply chain](supply-chain.md) |
| Repository | Encrypted secrets, pinned actions, protected `main` | Below |

Each layer assumes the one in front of it has already failed. The tunnel keeps an attacker
off the cluster from outside. The network policies stop a foothold in one pod becoming a
foothold in the next. The hardening leaves a compromised process nothing to escalate with.
And Falco makes the attempt visible whether or not any of that held.

## Access to the cluster

ArgoCD is the only interface to the cluster that anyone uses, so its authorisation is the
one that matters:

```yaml
rbac:
  policy.csv: |
    p, role:authenticated, *, *, *, deny
    g, zmuda-pro:argocd-admins, role:admin
  policy.default: role:authenticated
```

Being authenticated grants nothing at all. The default role is explicitly denied every
action, and access comes from group membership in the identity provider. Adding a person is
an IdP change, and removing them takes effect immediately, without touching this
repository.

The server does not run insecure (`server.insecure: false`, TLS end to end, with Traefik
configured for an HTTPS backend), and its chart creates a network policy with
`defaultDenyIngress`.

## Pod Security Admission

Namespaces are labelled with a Pod Security Standard, and ArgoCD applies the labels itself
through `managedNamespaceMetadata`. The enforcement level is part of the application
definition, not a step someone has to remember:

| Level | Namespaces | Why |
| --- | --- | --- |
| `restricted` | blog, kyverno | The workload can meet it, so it must |
| `baseline` | descheduler | Needs more than restricted allows, but nothing privileged |
| `privileged` | falco, intel-gpu-resource-driver | Reading syscalls and driving a GPU require it |

It is **not** applied to every namespace. The media stack's LinuxServer.io images start as
root to apply `PUID`/`PGID` before dropping privileges, which `restricted` forbids
outright. Labelling those namespaces `privileged` would make the label present everywhere
while granting more than they need, so they carry no label at all and the omission is listed
under the gaps below.

## Workload hardening

Applications written here share one security context, and it is close to the maximum a pod
can assert about itself:

```yaml
securityContext:
  runAsNonRoot: true
  runAsUser: 10003
  runAsGroup: 20003
  fsGroup: 20003
  seccompProfile:
    type: RuntimeDefault
# per container
  readOnlyRootFilesystem: true
  allowPrivilegeEscalation: false
  capabilities:
    drop: [ALL]
```

`readOnlyRootFilesystem` is the one that takes work. Everything the process needs to write
becomes an explicit `emptyDir`, so the writable surface ends up enumerated in the manifest.
For the blog that is nginx's cache and run directories, and nothing else.

Container images built here follow the same rule from the other side. They are non-root by
default, minimal, and carry no shell to inherit. See
[Supply chain](supply-chain.md#base-images).

## Runtime detection

[Falco](../kubernetes/helm/falco/values.yaml) watches syscalls on every node and is
deployed at sync wave -50, ahead of everything it might need to observe. Alerts go through
falcosidekick to a web UI and to email above `error` priority, so a detection has somewhere
to arrive instead of sitting in a pod log.

Most of the effort went into tuning. Cilium legitimately does things that Falco's default
rules consider hostile, like executing a freshly written binary in a container or creating a
packet socket. Disabling those rules would have been the easy way out:

```yaml
- rule: Drop and execute new binary in container
  exceptions:
    - name: cilium_cni_exec
      fields: [proc.exepath, proc.name]
      comps: [=, =]
      values:
        - [/opt/cni/bin/cilium-cni, cilium-cni]
  override:
    exceptions: append
```

The exception names the exact binary at the exact path, and appends to the rule instead of
replacing it. Everything else that drops and executes a binary in a container still trips
the alarm, which is the whole reason to tune an alert instead of switching it off.

## Secrets

Secrets live in this repository, encrypted with git-crypt and selected by a filename
pattern, and are decrypted by a patched ArgoCD at fetch time. The mechanism is described in
[GitOps](gitops.md#secrets-in-a-public-repository).

Two controls sit around that arrangement:

- **[detect-secrets](../.pre-commit-config.yaml) runs on every commit** against a
  [baseline](../.sec.baseline), so a credential pasted into a file that is *not* covered by
  the encryption pattern is caught before it is pushed. Files matching `*secret*` are
  excluded from the scan itself, because a git-crypt blob is high-entropy by construction
  and would otherwise produce a permanent false positive.
- **The naming rule is reviewed, not just linted.** A secret in a file without `secret` in
  its name is committed in plaintext, silently. The
  [release reviewer](../.github/agents/homelab-release-reviewer.agent.md) checks it as a
  policy violation on every release-affecting change.

The git-crypt key is here too, as the Secret ArgoCD mounts, encrypted with itself. Only
someone who can already read the repository can read it, so it adds no exposure, and it
cannot unlock anything either. Bootstrapping needs a copy the repository does not hold: the
exported key file, or the GPG key registered under `.git-crypt/keys/`. Those two are the
material an attacker would actually need, and the only thing whose loss is unrecoverable.

## Repository controls

`main` is what ArgoCD deploys, so the controls that matter most are the ones on the way into
it. A repository ruleset requires every change to arrive as a squash-merged pull request
with [code-owner](../.github/CODEOWNERS) review, on a linear history that cannot be
force-pushed or deleted, with review threads resolved and stale approvals dismissed on
push. CodeQL scanning and an automated review run as merge gates.

Around that:

| Control | What it prevents |
| --- | --- |
| Secret scanning with push protection | A credential reaching GitHub at all, encrypted or not |
| Actions pinned by commit SHA | A moved tag silently changing what runs in CI |
| Least-privilege workflow `permissions` | A compromised step writing where it has no business writing |
| GitHub App token for the inventory bot | A long-lived personal token with broad scope living in repository secrets |

The last two are easy to skip and hard to retrofit. The inventory workflow needs to push to
`main`, which is exactly the permission an attacker would want. It gets a short-lived token
scoped to one app instead of a PAT.

## Known gaps

Anyone copying something from here should know where it stops:

- **Kyverno audits, it does not deny.** Signature and attestation failures are recorded and
  re-checked every six hours, but an unsigned image would still run. The reason and the
  path out are in [Supply chain](supply-chain.md#currently-audit-not-deny).
- **Pod Security Admission is not on every namespace**, because some upstream images cannot
  satisfy any standard above `privileged` without being rebuilt.
- **Two copied binaries are invisible to every scanner**, documented in the
  [Dockerfile](../apps/vaultwarden/backup/Dockerfile) that copies them.
- **Backups share hardware with the data they protect**, except Vaultwarden's. See
  [Storage and backups](storage-and-backups.md#what-is-actually-recoverable).
- **There is no centralised audit log.** Falco alerts and ArgoCD history cover most of what
  would be wanted, but they are not correlated anywhere.

## Reporting a vulnerability

Please report privately, **not** as a public issue or pull request:
[GitHub private vulnerability reporting](https://github.com/theadzik/homelab/security/advisories/new)
notifies the maintainer directly and keeps the report confidential until there is a fix.

Expect an acknowledgement within 7 days. This is a homelab maintained in spare time, so
treat that as best effort and not a commitment.

**In scope:**

- The manifests, Helm values and charts in this repository, meaning anything that would run
  in a cluster built from them
- The container images published from here: `vw-backup`, `vw-restore`, `custom-argocd`
- The GitHub Actions workflows under `.github/workflows/`
- The admission policy and the secret-handling arrangement, including cases where the
  git-crypt pattern can be made to miss a file

**Out of scope:**

- The cluster itself, its hostnames and its network. It is a private homelab, not a service
  offered to anyone
- Anything requiring an already-compromised maintainer account
- The gaps listed above, which are known and documented

Reports about the shared build workflow belong in
[theadzik/github-workflows](https://github.com/theadzik/github-workflows), since fixing them
there fixes every image at once.

## See also

- [Supply chain](supply-chain.md): everything that happens to an image before it is allowed
  to run
- [Networking](networking.md#network-policy): the policies that decide what a compromised
  pod could reach
- [Conventions](conventions.md): the checks a change passes before it can be merged
