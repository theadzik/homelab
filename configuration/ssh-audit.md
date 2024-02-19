# Hardening SSH

1. Generate new ssh keys on client:
   `ssh-keygen -t ed25519 -f .ssh/raspberry_strong -N "" -C "adzik007@gmail.com"`
1. Remote into server
1. Paste public key into `/home/<user>/.ssh/authorized_keys` in a new line
1. Verify you can connect
1. Go to [ssh-audit](https://www.sshaudit.com/hardening_guides.html)
   hardening guides and run commands for server system
   > Note: `sudo -i` to switch to root before running commands
1. Remove the server from `known_hosts` on client: `ssh-keygen -R <hostname>`
1. Connect to the server again
