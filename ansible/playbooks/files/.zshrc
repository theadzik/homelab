export ZSH="$HOME/.oh-my-zsh"
ZSH_THEME="agnoster"

zstyle ':omz:update' mode auto      # update automatically without asking

ENABLE_CORRECTION="true"
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
precmd() { eval "echo -ne '\e]2;${USER}@${HOST}\a'" }

export PATH="$HOME/.local/bin:$PATH"
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

function k9s-update() {
  local_version=$(k9s version -s | grep -oE "v[0-9]+\.[0-9]+\.[0-9]+")
  echo "Local version: $local_version"
  latest_version=$(curl -s "https://api.github.com/repos/derailed/k9s/releases/latest" | jq -r '.name')
  echo "Latest version: $latest_version"

  if [[ local_version == latest_version ]]; then
    echo "Downloading..."
    url=$(curl -s "https://api.github.com/repos/derailed/k9s/releases/latest" | jq -r '.assets[].browser_download_url' | grep -E "k9s_Linux_amd64.tar.gz$")
    curl -s -L $url > k9s.tgz
    tar -zxvf k9s.tgz k9s >> /dev/null
    rm k9s.tgz

    k9s_location=$(which k9s)
    sudo mv k9s $k9s_location
    new_version=$(k9s version -s | grep -oE "v[0-9]+\.[0-9]+\.[0-9]+")
    echo "New local version: $new_version"
  else
    echo "Already at newest version."
  fi
}

alias vi="vim"
alias gg="git status"
alias gca="git commit -am"
alias k="kubectl"
alias kx="kubectx"
alias kns="kubens"
alias tf="terraform"

source <(kubectl completion zsh)

export NVM_DIR="$HOME/.nvm"
[ -s "$NVM_DIR/nvm.sh" ] && \. "$NVM_DIR/nvm.sh"  # This loads nvm
[ -s "$NVM_DIR/bash_completion" ] && \. "$NVM_DIR/bash_completion"  # This loads nvm bash_completion

# Vagrant config
export VAGRANT_WSL_ENABLE_WINDOWS_ACCESS="1"
export PATH="$PATH:/mnt/c/Program Files/Oracle/VirtualBox"

# Don't save commands starting with a space to history
export HISTCONTROL=ignoreboth
