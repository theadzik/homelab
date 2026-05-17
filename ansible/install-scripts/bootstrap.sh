#!/usr/bin/env bash
set -e

key_path="$HOME/.ssh/id_ed25519"
key_path_pub="$key_path.pub"
git_config="$HOME/.config/git"

email="adam@zmuda.pro"
name="Adam Żmuda"

git config --global user.name "$name"
git config --global user.email "$email"
git config --global core.editor "vim"
git config --global --add --bool push.autoSetupRemote true

mkdir -p "$git_config"
echo "$email $(cat "$key_path_pub")" > "$git_config/allowed-signers"
git config --global commit.gpgsign true
git config --global gpg.format ssh
git config --global user.signingkey "$key_path_pub"

/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
echo >> ~/.bashrc
# shellcheck disable=SC2016
echo 'eval "$(/home/linuxbrew/.linuxbrew/bin/brew shellenv bash)"' >> ~/.bashrc
eval "$(/home/linuxbrew/.linuxbrew/bin/brew shellenv bash)"

brew install pipx
/home/linuxbrew/.linuxbrew/bin/pipx ensurepath
pipx install --include-deps ansible
