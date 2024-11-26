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
* [k3s_bootstrap](ansible/playbooks/roles/k3s_bootstrap) - Installs ArgoCD and
  bootstraps it to this repository.

### Roles copied from other repositories

Roles `k3s_agent`, `k3s_server`, `k3s_upgrade`, `prereq`, and `raspberry`
were originally copied from [k3s-ansible](https://github.com/k3s-io/k3s-ansible).
I modified code of those roles to fit my needs.

## `/apps`

Containerized applications:

* `cv` - My resume built with Ruby and Jekyll
* `reddit-meaningofwords` - A useful (or annoying, depends on your views)
  bot that fixes most common language mistakes on reddit.com/r/Polska.
  It uses `openai` api to recognize context, fix mistakes and generate explanation.
* `bullying-detector` - helper for the Reddit bot to filter bullying responses
* `vaultwarden` - Backup and restore scripts made for vaultwarden,
  running as initContainer and CronJob

## `/manifests`

* `/applications` - contains ArgoCD applications deploying all other manifests
* `/base` - contains kustomizations to deploy all applications
* `/overlay` - so far it is unused, but left as the reference for future changes
  needed to deploy to dev cluster
