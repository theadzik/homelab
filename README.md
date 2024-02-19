# My home lab monorepo

This repository contains a full configuration of my k3s cluster.

## `/ansible`

A full automation for provisioning k3s cluster.

### My own roles

* [fail2ban](ansible/playbooks/roles/fail2ban) - Installs and configures
  [fail2ban](https://github.com/fail2ban/fail2ban)
* [ssh_hardening](ansible/playbooks/roles/ssh_hardening) -
  Applies more secure ssh configuration from
  [sshaudit.com](https://www.sshaudit.com/hardening_guides.html#debian_12) guide.
* [vaultwarden](ansible/playbooks/roles/vaultwarden) -
  Sets up environment required for
  [vaultwarden](https://github.com/dani-garcia/vaultwarden).
  It restores data and enables backup scripts.
* [local_storage](ansible/playbooks/roles/local_storage) - Creates directories
  for persistent local volumes used later by kubernetes.

### Roles copied from other repositories

Roles `k3s_agent`, `k3s_server`, `k3s_upgrade`, `prereq`, and `raspberry`
were copied from [k3s-ansible](https://github.com/k3s-io/k3s-ansible) repo.

## `/apps`

Containerized applications:

* `backups` - Running backups for VaultWarden and uploading to Google Drive
* `cv` - My resume built with Jekyll
* `dns` - Dynamic DNS updater working with `no-ip`

## `/manifests`

Kubernetes manifests deploying all configuration.
