#!/usr/bin/env bash
set -euo pipefail

# What can only happen after the playbook, because it installs the tools each
# step needs: gh to register this machine's SSH key, git-crypt and gpg to
# decrypt the working tree. Every step checks before it acts, so a run that
# failed half way through can simply be run again.
#
#     ./ansible/install-scripts/post-install.sh [exported git-crypt GPG key]
#
# Without the argument the GPG key is assumed to be in your keyring already.

cd "$(git rev-parse --show-toplevel)"

key_path_pub="$HOME/.ssh/id_ed25519.pub"
key_body="$(awk '{print $2}' "$key_path_pub")"

# Adding keys needs two scopes a plain login does not ask for, and GitHub holds
# authentication and signing keys separately: the first is what lets you push,
# the second is what marks your commits Verified.
gh auth status >/dev/null 2>&1 || gh auth login
if ! gh auth status 2>&1 | grep -q "admin:ssh_signing_key"; then
  gh auth refresh --hostname github.com --scopes admin:public_key,admin:ssh_signing_key
fi

for key_type in authentication signing; do
  if gh ssh-key list | grep -F "$key_body" | grep -q "$key_type"; then
    echo "SSH key already registered for $key_type."
  else
    gh ssh-key add "$key_path_pub" --type "$key_type" --title "$(hostname)"
  fi
done

# The one secret a new machine cannot generate for itself: git-crypt's symmetric
# key is encrypted to a GPG key, and lands in .git/git-crypt/keys/default once
# unlocked, which is what makes this skippable on a second run.
if [[ -f .git/git-crypt/keys/default ]]; then
  echo "git-crypt already unlocked."
else
  if [[ -n "${1:-}" ]]; then
    gpg --import "$1"
  fi
  git-crypt unlock
fi
