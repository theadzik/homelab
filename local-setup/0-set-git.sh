#!/usr/bin/env bash
set -e

key_path="$HOME/.ssh/id_ed25519"
key_path_pub="$key_path.pub"
git_config="$HOME/.config/git"

email="adam@zmuda.pro"
name="Adam Żmuda"

ssh-keygen -t ed25519 -C "$email" -N "" -f "$key_path"
eval "$(ssh-agent -s)"
ssh-add "$key_path"

sudo apt-get update && sudo apt-get install git -y

git config --global user.name "$name"
git config --global user.email "$email"
git config --global core.editor "vim"
git config --global --add --bool push.autoSetupRemote true

mkdir "$git_config"
echo "$email $(cat "$key_path_pub")" > "$git_config/allowed-signers"
git config --global commit.gpgsign true
git config --global gpg.format ssh
git config --global user.signingkey "$key_path_pub"

mkdir "$HOME/git"

echo "======== PUBLIC KEY ========"
cat "$key_path_pub"
echo "======== PUBLIC KEY END ========"
