#!/usr/bin/env bash
set -e

sudo apt-get update
sudo apt-get install pipx -y
pipx ensurepath

pipx install --include-deps ansible
