#!/usr/bin/env bash
set -e

key_path="$HOME/.ssh/id_ed25519"
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

mkdir "$HOME/git"

echo "======== PUBLIC KEY ========"
cat "$key_path.pub"
echo "======== PUBLIC KEY END ========"
