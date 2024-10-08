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
* [local_storage](ansible/playbooks/roles/local_storage) - Creates directories
  for persistent local volumes used later by kubernetes.

### Roles copied from other repositories

Roles `k3s_agent`, `k3s_server`, `k3s_upgrade`, `prereq`, and `raspberry`
were originally copied from [k3s-ansible](https://github.com/k3s-io/k3s-ansible).
I modified code of those roles to fit my needs.

## `/apps`

Containerized applications:

* `vaultwarden` - Backup and restore scripts made for vaultwarden,
  running as initContainer and CronJob
* `cv` - My resume built with Jekyll
* `wedding-website` - A site I made for my wedding
* `dns` - Dynamic DNS updater working with `no-ip`
* `reddit-meaningofwords` - A useful (or annoying, depends on your views)
  bot that fixes most common language mistakes on reddit.com/r/Polska.
  It uses `openai` api to recognize context, fix mistakes and generate explanation.

## `/manifests`

Kubernetes manifests deploying all resources.
`dev` overlay is used mostly for vagrant vms, while `prod` runs
on raspberry.
