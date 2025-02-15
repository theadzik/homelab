# Steps to config WSL / Ubuntu

## Windows

1. Install WSL on Windows: https://docs.microsoft.com/en-us/windows/wsl/install
1. Install Windows Terminal: https://apps.microsoft.com/store/detail/windows-terminal/9N0DX20HK701

1. Run:

    ```cmd
    wsl --install -d Ubuntu-24.04
    ```

1. Download and install `Cascadia Code PL` font from the pack: https://github.com/microsoft/cascadia-code/releases

1. Edit Windows terminal profile settings:
    * Startup -> Default Profile -> "Ubuntu-24.04"
    * Profiles -> Ubuntu-24.04 -> Appearance -> Font Face -> "Cascadia Code PL"

## Ubuntu

1. Create user `adzik`, password in vaultwarden.
1. Copy contents of `local-setup/0-generate-ssh-key.sh` to a file and run it with `bash 0-generate-ssh-key.sh`
   * Add the output to [GitHub](https://github.com/settings/ssh/new)
1. `git clone git@github.com:theadzik/homelab.git`
1. `bash local-setup/1-bootstrap-ansible.sh`
1. `ansible-playbook playbooks/local-setup.yaml --ask-become-pass`
1. Download git-crypt key and put it in `~/git`
1. Add new ssh keys to servers.
1. Run ansible pipeline from `homelab`
