#!/usr/bin/env bash
set -e

# The least that has to happen before `ansible-playbook` will run: brew, pipx,
# ansible. Git identity, signing and the allowed-signers file used to be here
# too - the git role owns them now, so they are applied on every run instead of
# once on a machine's first day, and this script is only about getting ansible.
#
# Two things stay manual: generating this machine's ~/.ssh/id_ed25519 and
# registering its public half with GitHub, and importing the GPG key that
# git-crypt unlocks with - which a public repository cannot hold for you.
# See docs/operations.md.

/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
echo >> ~/.bashrc
# shellcheck disable=SC2016
echo 'eval "$(/home/linuxbrew/.linuxbrew/bin/brew shellenv bash)"' >> ~/.bashrc
eval "$(/home/linuxbrew/.linuxbrew/bin/brew shellenv bash)"

brew install pipx
/home/linuxbrew/.linuxbrew/bin/pipx ensurepath
pipx install --include-deps ansible
