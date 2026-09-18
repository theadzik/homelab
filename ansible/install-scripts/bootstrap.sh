#!/usr/bin/env bash
set -e

# The least that has to happen before `ansible-playbook` will run: an SSH key,
# then brew, pipx and ansible itself. Git identity, signing and the
# allowed-signers file used to be here too - the git role owns those now, so
# they are applied on every run rather than once on a machine's first day.
#
# The key stays here because the git role reads its public half during the play
# and fails without it. It is this machine's own, generated fresh rather than
# carried over from the last one. Registering it with GitHub and importing the
# GPG key git-crypt unlocks with are post-install.sh's, since both need tools
# the playbook installs. See docs/operations.md.

key_path="$HOME/.ssh/id_ed25519"
if [[ ! -f "$key_path" ]]; then
  ssh-keygen -t ed25519 -C "adam@zmuda.pro" -f "$key_path"
fi

/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
echo >> ~/.bashrc
# shellcheck disable=SC2016
echo 'eval "$(/home/linuxbrew/.linuxbrew/bin/brew shellenv bash)"' >> ~/.bashrc
eval "$(/home/linuxbrew/.linuxbrew/bin/brew shellenv bash)"

brew install pipx
/home/linuxbrew/.linuxbrew/bin/pipx ensurepath
pipx install --include-deps ansible
