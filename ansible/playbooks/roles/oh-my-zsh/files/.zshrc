#!/bin/zsh

export ZSH="$HOME/.oh-my-zsh"
ZSH_THEME="agnoster"

zstyle ':omz:update' mode auto      # update automatically without asking

HIST_STAMPS="yyyy-mm-dd"

plugins=(
    git
    fzf
    zsh-syntax-highlighting
    zsh-autosuggestions
    docker
    kubectl
    )

source $ZSH/oh-my-zsh.sh

export ZSH_HIGHLIGHT_MAXLENGTH=119
export DISABLE_AUTO_TITLE="true"
precmd() { eval "echo -ne '\e]2;${USER}@${HOST}\a'"; }

export PATH="$HOME/.local/bin:/home/linuxbrew/.linuxbrew/bin/:$PATH"
export KUBECONFIG="$HOME/.kube/config"

export DEFAULT_USER=adzik
prompt_context() {
if [[ "$USER" != "$DEFAULT_USER" || -n "$SSH_CLIENT" ]]; then
    prompt_segment black default "%(!.%{%F{yellow}%}.)$USER"
fi
}

source $ZSH/oh-my-zsh.sh

autoload -U colors; colors
source "${ZSH_CUSTOM}/plugins/zsh-kubectl-prompt/kubectl.zsh"
function right_prompt() {
  local color="green"

  if [[ "$ZSH_KUBECTL_CONTEXT" =~ "prod" && ! "$ZSH_KUBECTL_CONTEXT" =~ "nonprod" ]]; then
    color=red
  fi

  echo "%{$fg[$color]%}($ZSH_KUBECTL_PROMPT)%{$reset_color%}"
}
RPROMPT='$(right_prompt)'

alias vi="vim"
alias gg="git status"
alias gca="git commit -am"
alias k="kubectl"
alias kx="kubectx"
alias kns="kubens"
alias t="talosctl"
alias tf="terraform"

source <(kubectl completion zsh)

export NVM_DIR="$HOME/.nvm"
[ -s "$NVM_DIR/nvm.sh" ] && \. "$NVM_DIR/nvm.sh"  # This loads nvm
[ -s "$NVM_DIR/bash_completion" ] && \. "$NVM_DIR/bash_completion"  # This loads nvm bash_completion

eval "$(/home/linuxbrew/.linuxbrew/bin/brew shellenv zsh)"

# Don't save commands starting with a space to history
export HISTCONTROL=ignoreboth
