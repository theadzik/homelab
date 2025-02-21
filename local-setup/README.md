# Steps to config WSL / Ubuntu

## Windows

1. Install WSL on Windows: <https://docs.microsoft.com/en-us/windows/wsl/install>
1. Install Windows Terminal: <https://apps.microsoft.com/store/detail/windows-terminal/9N0DX20HK701>

1. Run:

    ```cmd
    wsl --install -d Ubuntu-24.04
    ```

1. Download and install `Cascadia Code PL` font from the pack: <https://github.com/microsoft/cascadia-code/releases>

1. Edit Windows terminal profile settings:
    * Startup -> Default Profile -> "Ubuntu-24.04"
    * Profiles -> Ubuntu-24.04 -> Appearance -> Font Face -> "Cascadia Code PL"

1. Edit json and add `"suppressApplicationTitle": false` to New profile config.

## Ubuntu

1. Create user `adzik`, password in vaultwarden.
1. Copy contents of `local-setup/0-set-git.sh` to a file and run it with `bash 0-set-git.sh`
    * Add the output to [GitHub](https://github.com/settings/ssh/new)
1. `git clone git@github.com:theadzik/homelab.git`
1. `bash local-setup/1-bootstrap-ansible.sh`
1. Restart shell.
1. `ansible-playbook playbooks/local-setup.yaml --ask-become-pass`
1. Download git-crypt key and put it in `~/git`
1. `git-crypt unlock ../git-crypt-key`
1. Add new ssh keys to servers.
    * Get master key from vaultwarden.
    * `ssh-copy-id -i ~/.ssh/id_ed25519 -o 'IdentityFile id_ed25519' -f adzik@server-1.internal`
    * Delete master key.
1. `ansible-playbook playbooks/servers-setup.yaml` (To get .kube/config file)
