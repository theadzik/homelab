# My home lab monorepo

This repository contains a full configuration of my k3s cluster.

## `/ansible`

A full automation for provisioning my local wsl environment and k3s cluster.

## `/apps`

Containerized applications:

* `custom-argocd` - ArgoCD image that enabled git-crypt.
* `vaultwarden` - Backup and restore scripts made for vaultwarden,
  running as initContainer and CronJob

## `/manifests`

* `/applications` - contains ArgoCD applications deploying all other manifests
* `/base` - contains kustomizations to deploy all applications
