# My home lab monorepo

This repository contains a full configuration of my k3s cluster.

## `/ansible`

A full automation for provisioning my local wsl environment and k3s cluster.

## `/apps`

Containerized applications:

* `reddit-meaningofwords` - A useful (or annoying, depends on your views)
  bot that fixes most common language mistakes on reddit.com/r/Polska.
  It uses `openai` api to recognize context, fix mistakes and generate explanation.
* `bullying-detector` - helper for the Reddit bot to filter bullying responses
* `custom-argocd` - ArgoCD image that enabled git-crypt.
* `vaultwarden` - Backup and restore scripts made for vaultwarden,
  running as initContainer and CronJob

## `/manifests`

* `/applications` - contains ArgoCD applications deploying all other manifests
* `/base` - contains kustomizations to deploy all applications
* `/overlay` - so far it is unused, but left as the reference for future changes
  needed to deploy to dev cluster
