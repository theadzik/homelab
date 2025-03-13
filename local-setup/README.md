# Steps to bootstrap Ubuntu

1. Create user `adzik`.
1. Copy contents of `local-setup/0-set-git.sh` to a file and run it with `bash 0-set-git.sh`
    * Add the output to [GitHub](https://github.com/settings/ssh/new)
      > Add as both, authentication and signing keys.
1. `git clone git@github.com:theadzik/homelab.git`
1. `bash local-setup/1-bootstrap-ansible.sh`
1. Restart shell.
1. `ansible-playbook playbooks/local-setup.yaml --ask-become-pass`
1. Download git-crypt key and put it in `~/git`
1. `git-crypt unlock ../git-crypt-key`
1. Add new ssh keys to servers.
    * Get master key from vaultwarden.
    * `ssh-copy-id -i ~/.ssh/id_ed25519 -o 'IdentityFile id_ed25519' -f adzik@server-1.internal`
    * `ssh-copy-id -i ~/.ssh/id_ed25519 -o 'IdentityFile id_ed25519' -f adzik@server-2.internal`
    * Delete master key.
1. `ansible-playbook playbooks/servers-setup.yaml` (To get .kube/config file)
