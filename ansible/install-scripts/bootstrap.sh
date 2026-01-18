#!/usr/bin/env bash
set -e

key_path="$HOME/.ssh/id_ed25519"
key_path_pub="$key_path.pub"
git_config="$HOME/.config/git"

email="adam@zmuda.pro"
name="Adam Żmuda"

ssh-keygen -t ed25519 -C "$email" -f "$key_path"
eval "$(ssh-agent -s)"
ssh-add "$key_path"

sudo apt-get update && sudo apt-get install git -y

git config --global user.name "$name"
git config --global user.email "$email"
git config --global core.editor "vim"
git config --global --add --bool push.autoSetupRemote true

mkdir -p "$git_config"
echo "$email $(cat "$key_path_pub")" > "$git_config/allowed-signers"
git config --global commit.gpgsign true
git config --global gpg.format ssh
git config --global user.signingkey "$key_path_pub"

mkdir -p "$HOME/git"

echo "======== PUBLIC KEY ========"
cat "$key_path_pub"
echo "======== PUBLIC KEY END ========"

echo "Add keys to GitHub: https://github.com/settings/ssh/new"
read -rp "Press [Enter] after adding the SSH key to GitHub..."

git clone "git@github.com:theadzik/homelab.git" "$HOME/git/homelab"

/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
eval "$(/home/linuxbrew/.linuxbrew/bin/brew shellenv bash)"

brew install pipx
sudo /home/linuxbrew/.linuxbrew/bin/pipx install pip --global
pipx install --include-deps ansible
