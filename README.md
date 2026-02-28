# homelab

This repository contains most of the code I use to manage my homelab environment.
I use Kubernetes running on Talos Linux and Synology DS923+ for storage.
GitOps is done using ArgoCD. I keep all the code in this repository, including
secrets encrypted with git-crypt.

## `/ansible`

Ansible (duh!) playbook to configure dev environment on my local machine.

## `/apps`

Dockerfiles and scripts used to build images.

* `/apps/custom-argocd` - ArgoCD with enabled git-crypt support.
* `/apps/vaultwarden` - Backup and restore scripts made for Vaultwarden. Designed to be
  running as initContainer (restore) and a CronJob (backup).

## `/charts`

Public Helm charts that can be released independently of the homelab configuration.

* `/charts/media-stack` - Comprehensive media automation stack (Jellyfin, Radarr, Sonarr, Bazarr, NZBGet).
  See [charts/README.md](charts/README.md) for details.

## `/kubernetes`

Kubernetes manifests, helm values, and bootstrap configurations for my homelab cluster.

* `/kubernetes/bootstrap` - Cluster bootstrap configurations,
  including ArgoCD helm version, bootstrap app-of-apps chart,
  and sync wave inventory. Custom ArgoCD image is built using AppVersion from selected chart.
* `/kubernetes/helm` - Helm values for applications deployed in my cluster.
  Chart definitions may be in `/charts` (for public charts) or inline.
* `/kubernetes/kustomziations` - Kustomizations
  (and sometimes just plain manifests with a `kustomization.yaml` file to look fancy)
  for applications that don't have helm charts, or I don't want to use them for some reason.

[Sync-wave inventory](./sync-waves-inventory.md) is
automatically generated when applications change in the app-of-apps chart.

## `/talos`

Talos Linux configuration. Schematic files are used to generate Talos config and patches.
